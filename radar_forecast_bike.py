import pandas as pd
import numpy as np
import sys
import utils

from pathlib import Path

# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 3, 5, 7, 9)
# Folder to download the data (they will be removed 
# but it needs some space to start with)
data_path = Path("/Users/guidocioni/Downloads")
json = True 

def make_plot(time_radar, rain_bike, dtime_bike, out_filename=None):
    if out_filename:
        import matplotlib
        matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12,5))
    ax = plt.gca()

    # Create the labels including the original datetime and a sum of the rain
    deltas_string   = [delta.strftime('%H:%M') for delta in np.array(time_radar)[np.array(shifts)]]
    sums_string     = ['%4.2f mm' % value for value in rain_bike.sum(axis=1)*(5./60.)]
    labels          = ['start '+m+', tot. '+n for m,n in zip(deltas_string, sums_string)]
    # Since timedelta objects are not correctly handled by matplotlib
    # we need to do this converstion manually
    x = dtime_bike.values.astype(float) / (60e9)

    ax.plot(x, rain_bike.T, '-')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.xaxis.grid(True, ls='dashed')
    ax.set_title("Radar forecast | Basetime "+time_radar[0].strftime("%Y%m%d %H:%M"))
    ax.set_ylabel("$P$ [mm h$^{-1}$]")
    ax.set_xlabel("Time from start [minutes]")
    ax.fill_between(x, y1=0, y2=2.5, alpha=0.4, color="paleturquoise")
    ax.fill_between(x, y1=2.5, y2=7.6, alpha=0.3, color="lightseagreen")
    ax.fill_between(x, y1=7.6, y2=ax.get_ylim()[-1], alpha=0.3, color="teal")
    ax.set_xlim(left=x[0], right=x[-1])
    ax.set_ylim(bottom=0, top=rain_bike.max())
    ax.annotate("Light", xy=(x[-20], .1), alpha=0.6)
    ax.annotate("Moderate", xy=(x[-20], 2.6), alpha=0.6)
    ax.annotate("Heavy", xy=(x[-20], 7.7), alpha=0.5)
    plt.legend(labels, fontsize=7)

    if out_filename:
        plt.savefig(out_filename)
        print("Wrote plot to `{}`".format(out_filename))
    else:
        plt.show(block=True)


def extract_rain_rate_from_radar(time_radar, dtime_radar, lon_bike, lat_bike, time_bike, dtime_bike, lon_radar, lat_radar, rr):
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
            # track from the bike
            dist = np.sqrt((lon_radar-lon_b)**2+(lat_radar-lat_b)**2)
            indx, indy=np.unravel_index(np.argmin(dist, axis=None), dist.shape)
            # Finally append the subsetted value to the array
            temp.append(rr[ind_time+shift, indx, indy])
        # iterate over all the shifts
        rain_bike=np.append(rain_bike, [temp], axis=0)

    return rain_bike


def main(track_file, plot_filename='plot.png'):
    lon_bike, lat_bike, time_bike, dtime_bike = utils.read_input(track_file)

    lon_radar, lat_radar, time_radar, dtime_radar, rr = utils.get_radar_data(data_path)

    rain_bike = extract_rain_rate_from_radar(time_radar=time_radar,
            lon_bike=lon_bike, lat_bike=lat_bike, dtime_bike=dtime_bike,
            time_bike=time_bike, dtime_radar=dtime_radar, lat_radar=lat_radar,
            lon_radar=lon_radar, rr=rr)

    # convert to JSON
    if json:
        deltas_string   = [delta.strftime('%H:%M') for delta in np.array(time_radar)[np.array(shifts)]]
        utils.convert_to_json(rain_bike, dtime_bike, deltas_string, url='data.json')

    make_plot(time_radar=time_radar, rain_bike=rain_bike, dtime_bike=dtime_bike,
              out_filename=plot_filename)


if __name__ == "__main__":
    if not sys.argv[1:]:
        print('Track file not defined, falling back to default')
        track_file = 'track_points_return.csv'
    else:
        track_file = sys.argv[1]

    main(track_file)
