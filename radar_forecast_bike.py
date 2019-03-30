debug = False
import pandas as pd
import numpy as np
import sys
import utils
import radolan as radar

from pathlib import Path

# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 3, 5, 7, 9)
# Folder to download the data (they will be removed 
# but it needs some space to start with)
data_path = Path("/tmp")
data_path.mkdir(exist_ok=True)

json = False

def main(track_file=None, start_point=None, end_point=None, mode=None):
    """
    Download and process the data. 
    """
    if not debug:
        if track_file:
            lon_bike,  lat_bike,  dtime_bike = utils.read_input(track_file)
            lon_radar, lat_radar, time_radar, dtime_radar, rr = utils.get_radar_data(data_path)

            rain_bike = utils.extract_rain_rate_from_radar(lon_bike=lon_bike, lat_bike=lat_bike,
                            dtime_bike=dtime_bike, dtime_radar=dtime_radar, lat_radar=lat_radar,
                            lon_radar=lon_radar, rr=rr)

        elif (start_point and end_point):
            lon_bike,  lat_bike,  dtime_bike = utils.gmaps_parser(start_point=start_point, end_point=end_point, mode=mode)
            lon_radar, lat_radar, time_radar, dtime_radar, rr = utils.get_radar_data(data_path)

            rain_bike = utils.extract_rain_rate_from_radar(lon_bike=lon_bike, lat_bike=lat_bike,
                            dtime_bike=dtime_bike, dtime_radar=dtime_radar, lat_radar=lat_radar,
                            lon_radar=lon_radar, rr=rr)

        df = utils.convert_to_dataframe(rain_bike, dtime_bike, time_radar)
    else:
        df = utils.create_dummy_dataframe()

    # convert to JSON
    if json:
        df.to_json('data.json')

    return df 

if __name__ == "__main__":
    if not sys.argv[1:]:
        print('Track file not defined, falling back to default')
        track_file = 'track_points_return.csv'
    else:
        track_file = sys.argv[1]

    main(track_file)
