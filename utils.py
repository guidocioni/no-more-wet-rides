import pandas as pd 
import calendar 
from datetime import datetime, timedelta
import re
import radolan as radar
import tarfile
import requests
import os
import numpy as np

# URL for the radar forecast, may change in the future
URL_RADAR = "https://opendata.dwd.de/weather/radar/composit/fx/FX_LATEST.tar.bz2"

RADAR_FILENAME_REGEX = re.compile("FX\d{10}_(?P<minutes>\d{3})_MF002")

def read_input(track_file):
    """
    It should have at least 3 variables with the time (df.time),
    longitude (df.X) and latitude (df.Y) of the track.
    You can easily convert GPX tracks to CSV online 
    """
    df = pd.read_csv(track_file)
    time_bike = pd.to_datetime(df.time.values)
    dtime_bike = time_bike - time_bike[0]
    # dtime_bike is a timedelta object!
    lon_bike = df.X.values
    lat_bike = df.Y.values

    return lon_bike, lat_bike, time_bike, dtime_bike

def _utc_to_local(utc_dt):
    """Convert UTC time to local time"""
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt  = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

def get_radar_data(data_path, remove_file=False):
    data_path.mkdir(exist_ok=True)

    radar_fn = data_path/'FX_LATEST.tar.bz2'

    if not radar_fn.exists():
        response = requests.get(URL_RADAR)
        # If file is not found raise an exception
        response.raise_for_status()

        # Write the file in the specified folder
        with open(radar_fn, 'wb') as f:
            f.write(response.content)

        # Extract tar file
        tar = tarfile.open(radar_fn, "r:bz2")
        files = sorted(tar.getnames())
        tar.extractall(data_path)
        tar.close()

        if remove_file:
            os.remove(radar_fn)
    else:
        # We have to make sure that the files are sorted in time
        files = sorted(data_path.glob("*_MF002"))

    #... and get the name of the extracted files
    fnames=[data_path/str(file) for file in files]
    ########################################################

    ######## Read/process the data ###########
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

    # Convert to a masked array and use the right units
    data = np.ma.array(data)
    dbz  = data/2. - 32.5 
    rr   = radar.z_to_r(radar.idecibel(dbz), a=256, b=1.42) #mm/h

    # Get coordinates (space/time)
    lon_radar, lat_radar = radar.get_latlon_radar()
    dtime_radar          = pd.to_datetime(datestring)-pd.to_datetime(datestring[0])
    # dtime_radar is a timedelta object! 

    time_radar = np.array([_utc_to_local(s) for s in  datestring])

    return lon_radar, lat_radar, time_radar, dtime_radar, rr