import pandas as pd
import wradlib as wrl
import numpy as np
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime, timedelta
import tarfile
import sys
import calendar

# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 3, 5, 7, 9)
# Folder to download the data (they will be removed 
# but it needs some space to start with)
folder = "/Users/guidocioni/Downloads/"
# URL for the radar forecast, may change in the future
url_radar = "https://opendata.dwd.de/weather/radar/composit/fx/FX_LATEST.tar.bz2"

######## Import file with the track #####################
# It should have at least 3 variables with the time (df.time),
# longitude (df.X) and latitude (df.Y) of the track.
# You can easily convert GPX tracks to CSV online 
#
if not sys.argv[1:]:
    print('Track file not defined, falling back to default')
    track_file = ['track_points_return.csv']
else:    
    track_file = sys.argv[1:]

df          = pd.read_csv(track_file[0])
time_bike   = pd.to_datetime(df.time.values)
dtime_bike  = time_bike - time_bike[0]
# dtime_bike is a timedelta object!
lon_bike    = df.X.values
lat_bike    = df.Y.values
########################################################

######## Download radar data ###########################
response = requests.get(url_radar)
# If file is not found raise an exception
response.raise_for_status()

# Write the file in the specified folder
with open(folder+'FX_LATEST.tar.bz2', 'wb') as f:
    f.write(response.content)

# Extract tar file
tar = tarfile.open(folder+'FX_LATEST.tar.bz2', "r:bz2")
files=tar.getnames()
tar.extractall(folder)
tar.close()
os.remove(folder+'FX_LATEST.tar.bz2')
#... and get the name of the extracted files
fnames=[folder + str(file) for file in files]
########################################################

######## Read/process the data using wradlib ###########
data = []
datestring = []

for fname in fnames:
    rxdata, rxattrs = wrl.io.read_radolan_composite(fname)
    data.append(np.ma.masked_equal(rxdata, -9999))
    minute = int(fname[fname.find("_MF002")-3:fname.find("_MF002")])
    datestring.append((rxattrs['datetime']+timedelta(minutes=minute)))

# Remove the files since we don't need them anymore
for fname in fnames:
    os.remove(fname)
    
# Convert to a masked array and use the right units
data = np.ma.array(data)
dbz  = data/2. - 32.5 # Conversion from DWD RADOLAN
rr   = wrl.zr.z_to_r(wrl.trafo.idecibel(dbz), a=256, b=1.42) #mm/h

# Get coordinates (space/time)
radolan_grid_ll = wrl.georef.get_radolan_grid(900, 900, wgs84=True)
lon_radar       = radolan_grid_ll[:,:,0]
lat_radar       = radolan_grid_ll[:,:,1]
dtime_radar     = pd.to_datetime(datestring)-pd.to_datetime(datestring[0])
# dtime_radar is a timedelta object! 

# Convert UTC time to local time
def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt  = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

for i in range(0, np.size(datestring)):
    datestring[i]=utc_to_local(datestring[i])

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

########################################################

######## Plot the results  #############################
fig = plt.figure(figsize=(12,5))
ax = plt.gca()

# Create the labels including the original datetime and a sum of the rain
deltas_string   = [delta.strftime('%H:%M') for delta in np.array(datestring)[np.array(shifts)]]
sums_string     = ['%4.2f mm' % value for value in rain_bike.sum(axis=1)*(5./60.)]
labels          = ['start '+m+', tot. '+n for m,n in zip(deltas_string, sums_string)]
# Since timedelta objects are not correctly handled by matplotlib
# we need to do this converstion manually
x = dtime_bike.values.astype(float) / (60e9)

ax.plot(x, rain_bike.T, '-')
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.xaxis.grid(True, ls='dashed')
ax.set_title("Radar forecast | Basetime "+datestring[0].strftime("%Y%m%d %H:%M"))
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

plt.show(block=True)

#######################################################
