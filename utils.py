import pandas as pd 
import calendar 
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
    It should have at least 3 variables with the time (df.time),
    longitude (df.X) and latitude (df.Y) of the track.
    You can easily convert GPX tracks to CSV online 
    """
    if track_file.endswith('.csv'):
        df = pd.read_csv(track_file)
        time_bike = pd.to_datetime(df.time.values)
        # dtime_bike is a timedelta object!
        lon_bike = df.X.values
        lat_bike = df.Y.values
    elif track_file.endswith('.gpx'):
        lon_bike, lat_bike, time_bike = gpx_parser(track_file)
    else:
        sys.exit("Only .csv and .gpx files are supported")

    # TODO, filter the track to have points that have a distance
    # comparable to the radar grid spacing, because that's anyway
    # the maximum resolution that we can achieve... 
    dtime_bike = time_bike - time_bike[0]

    return lon_bike, lat_bike, time_bike, dtime_bike

def gpx_parser(track_file):
    '''Parse lat, lon and time from a gpx file.
    We'll have to check whether multiple segments/
    tracks are a problem'''
    lat=[]
    lon=[]
    time=[]
    import gpxpy
    gpx = gpxpy.parse(open(track_file))
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lat.append(point.latitude)
                lon.append(point.longitude)
                time.append(point.time.replace(tzinfo=None))
    return(np.array(lon), np.array(lat), pd.to_datetime(time))

def _utc_to_local(utc_dt):
    """Convert UTC time to local time"""
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt  = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def convert_to_json(rain_bike, dtime_bike, deltas_string, url):
    df = pd.DataFrame(data=rain_bike.T, index=dtime_bike, columns=deltas_string)
    df.to_json(url, orient='split')

def download_unpack_file(radar_fn, data_path):
    ''' Download the latest data from the server
    and unpack it, returning the list of the 
    extracted files.'''

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
    ''' Get the file from the server, if it's not already downloaded.
    In order to decide whether we need to download the file or not we
    have to check (1) if the file exists (2) if it exists, is it the
    most recent one. The check (2) for now only compares the size of
    the local and remote file. This should work in most of the cases
    but it's not 100% correct.'''

    radar_fn = data_path/'FX_LATEST.tar.bz2'

    if not radar_fn.exists():
        files = download_unpack_file(radar_fn, data_path)

    else: # the file exists 
        # we have to get the remote size
        # the request will be honored on the 
        # DWD website (hopefully also in the future)
        response = requests.get(URL_RADAR)
        remote_size = int(response.headers['Content-Length'])
        local_size  = int(radar_fn.stat().st_size)

        if local_size != remote_size: # it means
            # that the remote file changed so the local one is not 
            # updated: we need to download the file again!
            #
            # First remove old files to make space for the new ones
            radar_fn.unlink()
            for file in data_path.glob("*_MF002"):
                if file.exists():
                    file.unlink()

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
    '''From the names of the files return arrays where the data is 
    concatenated. '''
    data = []
    datestring = []

    for fname in fnames:
        rxdata, rxattrs = radar.read_radolan_composite(fname)
        data.append(np.ma.masked_equal(rxdata, -9999))
        minute = int(RADAR_FILENAME_REGEX.match(fname.name)['minutes'])
        datestring.append((rxattrs['datetime']+timedelta(minutes=minute)))

    if remove_file:
        # Remove the files since we don't need them anymore
        for fname in fnames:
            os.remove(fname)

    # Convert to a masked array
    # The conversion for mm/h is done afterwards to avoid memory usage
    data = np.ma.array(data)
    # dbz  = data/2. - 32.5 
    # rr   = radar.z_to_r(radar.idecibel(dbz), a=256, b=1.42) #mm/h THIS IS CAUSING THE MEMORY LEAK <----------
    rr = data

    # Get coordinates (space/time)
    lon_radar, lat_radar = radar.get_latlon_radar()
    dtime_radar          = pd.to_datetime(datestring)-pd.to_datetime(datestring[0])
    # dtime_radar is a timedelta object! 

    time_radar = np.array([_utc_to_local(s) for s in  datestring])

    return lon_radar, lat_radar, time_radar, dtime_radar, rr