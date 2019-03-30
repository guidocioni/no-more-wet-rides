import pandas as pd 
from datetime import datetime, timedelta
import re
import radolan as radar
import tarfile
import requests
import os
import numpy as np
import sys

# URL for the radar forecast, may change in the future
URL_RADAR = "https://opendata.dwd.de/weather/radar/composit/fx/FX_LATEST.tar.bz2"

RADAR_FILENAME_REGEX = re.compile("FX\d{10}_(?P<minutes>\d{3})_MF002")

def read_input(track_file):
    """
    Read track from an external source. Only latitude, longitude and time need
    to be extracted from the file. Currently csv and gpx files are supported. 
    The csv file needs to have 3 variables named exactly time, X and Y. In the
    future this track will be taken from different sources or API.
    """
    if track_file.endswith('.csv'):
        df = pd.read_csv(track_file)
        time_bike = pd.to_datetime(df.time.values)
        lon_bike, lat_bike = df.X.values, df.Y.values
    elif track_file.endswith('.gpx'):
        lon_bike, lat_bike, time_bike = gpx_parser(track_file)
    else:
        sys.exit("Only .csv and .gpx files are supported")

    # TODO, filter the track to have points that have a distance
    # comparable to the radar grid spacing, because that's anyway
    # the maximum resolution that we can achieve... 
    dtime_bike = time_bike - time_bike[0]

    return lon_bike, lat_bike, dtime_bike

def gpx_parser(track_file):
    """
    Parse lat, lon and time from a gpx file.
    We'll have to check whether multiple segments/
    tracks are a problem while reading. 
    Requires the gpxpy library.
    Returns 3 array of longitude, latitude and time.
    """
    import gpxpy
    lat=[]
    lon=[]
    time=[]
    gpx = gpxpy.parse(open(track_file))
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lat.append(point.latitude)
                lon.append(point.longitude)
                time.append(point.time.replace(tzinfo=None))
    return np.array(lon), np.array(lat), pd.to_datetime(time)

def gmaps_parser(start_point="Feuerbergstrasse 6, Hamburg",
                 end_point="Bundesstrasse 53, Hamburg", mode="bicycling"):
    """
    Obtain the track using the google maps api
    """
    from googlemaps import Client
    api_key = os.environ['MAPS_API_KEY']
    gmaps = Client(api_key)
    directions = gmaps.directions(start_point, end_point, mode=mode)

    lat_bike = np.array([step['start_location']['lat'] for step in directions[0]['legs'][0]['steps']])
    lon_bike = np.array([step['start_location']['lng'] for step in directions[0]['legs'][0]['steps']])
    time = np.array([step['duration']['value'] for step in directions[0]['legs'][0]['steps']])
    dtime_bike = np.cumsum(pd.to_timedelta(time, unit='s'))

    return lon_bike, lat_bike, dtime_bike


def distance_km(lon1, lon2, lat1, lat2):
	'''Returns the distance (in km) between two array of points'''
	radius = 6371 # km

	dlat = np.deg2rad(lat2-lat1)
	dlon = np.deg2rad(lon2-lon1)
	a = np.sin(dlat/2) * np.sin(dlat/2) + np.cos(np.deg2rad(lat1)) \
	    * np.cos(np.deg2rad(lat2)) * np.sin(dlon/2) * np.sin(dlon/2)
	c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
	d = radius * c

	return d

def distance_bike(lon_bike, lat_bike):
	'''Finds the distance (in km) from the starting point of the bike
	track.'''
	lon_bike_shift = np.roll(lon_bike, -1)[:-2] # Avoid taking the last point
	lat_bike_shift = np.roll(lat_bike, -1)[:-2]

	return distance_km(lon_bike_shift, lon_bike[:-2], lat_bike_shift, lat_bike[:-2]).cumsum()

def convert_timezone(dt_from, from_tz='utc', to_tz='Europe/Berlin'):
    """
    Convert between two timezones. dt_from needs to be a Timestamp 
    object, don't know if it works otherwise.
    """
    dt_to = dt_from.tz_localize(from_tz).tz_convert(to_tz)
    # remove again the timezone information
    return dt_to.tz_localize(None)

def download_unpack_file(radar_fn, data_path):
    """
    Download the latest data from the server and unpack it,
    returning the list of the  extracted files. 
    """

    response = requests.get(URL_RADAR)
    # If file is not found raise an exception
    response.raise_for_status()

    # Write the file in the specified folder
    with open(radar_fn, 'wb') as f:
        f.write(response.content)

    # Extract tar file
    tar = tarfile.open(radar_fn, "r:bz2")
    files = tar.getnames()
    tar.extractall(data_path)
    tar.close()

    return sorted(files)

def get_radar_data(data_path, remove_file=False):
    """
    Get the file from the server, if it's not already downloaded.
    In order to decide whether we need to download the file or not we
    have to check (1) if the file exists (2) if it exists, whether it's the
    most recent one. The check (2) for now only compares the size of
    the local and remote file. This should work in most of the cases
    but it's not 100% correct. In theory one should extract the timestamp
    from both files. 
    """
    radar_fn = data_path/'FX_LATEST.tar.bz2'

    if not radar_fn.exists():
        files = download_unpack_file(radar_fn, data_path)

    else: # the file exists 
        # we have to get the remote size
        # The size request will be honored on the 
        # DWD website (hopefully also in the future)
        response = requests.get(URL_RADAR)
        remote_size = int(response.headers['Content-Length'])
        local_size  = int(radar_fn.stat().st_size)

        if local_size != remote_size: # it means
            # that the remote file changed so the local one is not 
            # updated: we need to download the file again!
            #
            # First remove old files to make space for the new ones...
            radar_fn.unlink()
            for file in data_path.glob("*_MF002"):
                if file.exists():
                    file.unlink()
            # ...and then download
            files = download_unpack_file(radar_fn, data_path)
            
        else: # it means that the file exists and is the most recent version
            files = sorted(data_path.glob("*_MF002"))
            # we need sorted to make sure that the files are ordered in time

    # If required remove the tar file, but that means that it will need to be
    # downloaded next time....
    if remove_file:
        radar_fn.unlink()

    # finally get the name of the extracted files
    fnames=[data_path/str(file) for file in files]

    return process_radar_data(fnames, remove_file)

def process_radar_data(fnames, remove_file):
    """
    Take the list of files fnames and extract the data using 
    the radolan module, which was extracted from wradlib.
    It also concatenates the files in time and returns
    a numpy array.
     """
    data = []
    time_radar = []

    for fname in fnames:
        rxdata, rxattrs = radar.read_radolan_composite(fname)
        data.append(rxdata)
        minute = int(RADAR_FILENAME_REGEX.match(fname.name)['minutes'])
        time_radar.append((rxattrs['datetime']+timedelta(minutes=minute)))

    if remove_file:
        for fname in fnames:
            os.remove(fname)

    # Conversion to numpy array 
    # !!! The conversion to mm/h is done afterwards to avoid memory usage !!! 
    data = np.array(data)

    # Get rid of masking value, we have to check whether this cause problem
    # In this case missing data is treated as 0 (no precip.). Masked arrays
    # cause too many problems. 
    data[data==-9999] = 0.
    rr = data

    # Get coordinates (space/time)
    lon_radar, lat_radar = radar.get_latlon_radar()
    time_radar  = convert_timezone(pd.to_datetime(time_radar))
    dtime_radar = time_radar - time_radar[0]

    return lon_radar, lat_radar, time_radar, dtime_radar, rr

def extract_rain_rate_from_radar(lon_bike, lat_bike, dtime_bike, lon_radar, lat_radar, dtime_radar, rr):
    from radar_forecast_bike import shifts
    """
    Given the longitude, latitude and timedelta objects of the radar and of the bike iterate through 
    every point of the bike track and find closest point (in time/space) of the radar data. Then 
    construct the rain_bike array by subsetting the rr array, that is the data from the radar.

    Returns a numpy array with the rain forecast over the bike track.
    """
    rain_bike=np.empty(shape=(0, len(dtime_bike))) # Initialize the array

    ######## We need to speed up this LOOP !!! #################################
    for shift in shifts:
        temp = []
        for lat_b, lon_b, dtime_b in zip(lat_bike, lon_bike, dtime_bike):
            # Find the index where the two timedeltas object are the same,
            # note that we can use this as both time from the radar
            # and the bike are already converted to timedelta, which makes
            # the comparison quite easy!
            ind_time = np.argmin(np.abs(dtime_radar - dtime_b))
            # Find also the closest point in space between radar and the
            # track from the bike. Would be nice to compute the distance in km
            # using utils.distance_km but this would be too slow!
            dist = np.sqrt((lon_radar-lon_b)**2+(lat_radar-lat_b)**2)
            indx, indy = np.unravel_index(np.argmin(dist, axis=None), dist.shape)
            # Finally append the subsetted value to the array
            temp.append(rr[ind_time+shift, indx, indy])
        # iterate over all the shifts
        rain_bike = np.append(rain_bike, [temp], axis=0)
    ############################################################################

    # convert to mm/h now on the smaller array, this was previously done in
    # utils.py but was causing more memory usage
    rain_bike = rain_bike/2. - 32.5 # to dbz 
    rain_bike = radar.z_to_r(radar.idecibel(rain_bike), a=256, b=1.42) # to mm/h

    return rain_bike

def convert_to_dataframe(rain_bike, dtime_bike, time_radar):
    from radar_forecast_bike import shifts
    """
    Convert the forecast in a well-formatted dataframe which can then be plotted or converted 
    to another format.
    """
    df = pd.DataFrame(data=rain_bike.T, index=dtime_bike, columns=time_radar[np.array(shifts)]) 

    return df 

def create_dummy_dataframe():
    from radar_forecast_bike import shifts
    """
    Create a dummy dataframe useful for testing the app and the plot.
    """
    columns = pd.date_range(start='2019-01-01 12:00', periods=len(shifts), freq='15min')
    dtime_bike = pd.timedelta_range(start='00:00:00', end='00:25:00', freq='0.5min')
    rain_bike = np.empty(shape=(len(dtime_bike), len(columns)))

    for i, column in enumerate(rain_bike.T):
        rain_bike[:,i] = linear_random_increase(column) 

    df = pd.DataFrame(index=dtime_bike, data=rain_bike, columns=columns)

    return df

def linear_random_increase(x):
    endpoint = np.random.randint(low=4, high=10)
    startpoint = np.random.randint(low=0, high=3)
    return np.linspace(startpoint, endpoint, len(x))

