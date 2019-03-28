from bokeh.embed import file_html
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.models import Band

from flask import Markup
import numpy as np 
import pandas as pd 

def create_plot(df):
	plot = figure(plot_width=1000, plot_height=500)

	x = np.tile(df.index.values.astype(float)/(60e9), (df.columns.shape[0], 1)).tolist()
	y = df.T.values.tolist()

	colors = ('LightSteelBlue', 'SkyBlue', 'DodgerBlue', 'RoyalBlue', 'DarkBlue', 'Navy', 'MidnightBlue')

	deltas_string = df.columns.values.tolist()
	sums_string     = ['%4.2f mm' % value for value in df.sum(axis=1)*(5./60.)]
	labels        = ['start '+m+', tot. '+n for m,n in zip(deltas_string, sums_string)]

	plot.y_range.start = 0.
	plot.yaxis.axis_label = 'Precipitation [mm/h]'
	plot.xaxis.axis_label = 'Time from departure [min]'

	for i, xdata in enumerate(x):
		plot.line(xdata, y[i], legend=labels[i], color=colors[i])

	plot.legend.label_text_font_size = '8pt'
	return Markup(file_html(plot, CDN, "Rain forecast for your ride"))