# no-more-wet-rides 

> A simple Python script to save your bike rides from the crappy german weather

[![Output](https://i.imgur.com/hWGzUY4.jpeg)]()

This handy Python script uses the `RADOLAN` forecast product from DWD (https://www.dwd.de/DE/leistungen/radolan/radolan.html) to evaluate how much rain you would get in a typical ride going from home to work or vice versa. 

**The `RADOLAN` data only covers Germany and neighbouring countries.**

> How does it work? 

- First of all the script reads the track contained in an external file (`track_points.csv`) where space and time information is saved. This could be a specific ride that you already did (I usually save all my rides over a garmin device and then export the `GPX` file to `CSV`) or a file that you create. 
- Second, the script downloads the latest forecast from the opendata server of the DWD (https://opendata.dwd.de/). The archive is extracted and the individual files are opened using the fantastic library `wradlib` (https://github.com/wradlib/wradlib). The individual time steps are merged into a single `numpy` array and processed to obtain mm/h units. 
- The time information in both phases is converted to `timedelta` objects so that the resulting arrays can be easily compared to see how much rain is forecast in every point of the track at the time that you would reach that point starting now. An additional parameter `shifts` is included to understand what is the best time to start your ride avoiding as much as possible any forecast rain. 
- Results are presented in a convenient `matplotlib` plot which shows all the forecast rain as a function of the time from the start of your ride.

---

## Example of usage 

```shell
python radar_forecast_bike.py track_points.csv 
```

---

## Installation
The script should work fine with both Python2 and Python3. You need the following packages

- pandas
- wradlib
- numpy
- matplotlib
- requests

All the other packages should already be installed in your Python distribution. 

Make sure to provide your own `csv` file with the track. This needs to have at least 3 columns with time (`time`) and space (longitude, `X`, latitude, `Y`) informations. If you use different names/formats make sure to change them in the script.

The read-in of the `RADOLAN` files should work out-of-the-box. 

You need to set the following variables before running

```python
# Here set the shifts (in units of 5 minutes per shift) for the final forecast
shifts = (1, 3, 5, 7, 9)
# Folder to download the data (they will be removed 
# but it needs some space to start with)
folder = "/Users/guidocioni/Downloads/"
```

---