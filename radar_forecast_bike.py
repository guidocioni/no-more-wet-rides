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

json = True

def extract_rain_rate_from_radar(lon_bike, lat_bike, dtime_bike, lon_radar, lat_radar, dtime_radar, rr):
    # Compute the rain at the bike position
    rain_bike=np.empty(shape=(0, len(dtime_bike))) # Initialize the array

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
                    
    # convert to mm/h now on the smaller array, this was previously done in
    # utils.py but was causing more memory usage
    rain_bike = rain_bike/2. -32.5 #dbz
    rain_bike = radar.z_to_r(radar.idecibel(rain_bike), a=256, b=1.42) # mm/h

    return rain_bike


def main(track_file, plot_filename=None):
    lon_bike, lat_bike, dtime_bike = utils.read_input(track_file)

    lon_radar, lat_radar, time_radar, dtime_radar, rr = utils.get_radar_data(data_path)

    rain_bike = extract_rain_rate_from_radar(lon_bike=lon_bike, lat_bike=lat_bike,
                    dtime_bike=dtime_bike, dtime_radar=dtime_radar, lat_radar=lat_radar,
                    lon_radar=lon_radar, rr=rr)

    # convert to JSON
    if json:
        deltas_string   = [delta.strftime('%H:%M') for delta in time_radar[np.array(shifts)]]
        utils.convert_to_json(rain_bike, dtime_bike, deltas_string, url='data.json')

    if plot_filename: # we go to matplotlib
    	return(time_radar, rain_bike, dtime_bike, plot_filename)
    else: # we go to Bokeh 
    	return(pd.DataFrame(data=rain_bike.T, index=dtime_bike, columns=deltas_string))

if __name__ == "__main__":
    if not sys.argv[1:]:
        print('Track file not defined, falling back to default')
        track_file = 'track_points_return.csv'
    else:
        track_file = sys.argv[1]

    main(track_file)
