from bokeh.embed import file_html
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.models import Band, ColumnDataSource

from flask import Markup
import numpy as np 
import pandas as pd 

def create_plot(df):
	plot = figure(plot_width=1000, plot_height=500)

	deltas_string = [delta.strftime('%H:%M') for delta in df.columns]

	x = df.index.values.astype(float)/(60e9)
	y = df.T.values

	colors = ('LightSteelBlue', 'SkyBlue', 'DodgerBlue',
				 'RoyalBlue', 'DarkBlue', 'Navy', 'MidnightBlue')

	sums_string     = ['%4.2f mm' % value for value in df.sum(axis=1)*(5./60.)]
	labels        	= ['start '+m+', tot. '+n for m,n in zip(deltas_string, sums_string)]

	plot.y_range.start = 0.
	plot.y_range.end = y.max()
	plot.x_range.start = x.min()
	plot.x_range.end   = x.max()
	plot.yaxis.axis_label = 'Precipitation [mm/h]'
	plot.xaxis.axis_label = 'Time from departure [min]'

	for i, ydata in enumerate(y):
		plot.line(x, ydata, legend=labels[i], color=colors[i], line_width=3)

	plot.legend.label_text_font_size = '8pt'
	plot.legend.location = "top_left"
	plot.legend.click_policy="hide"
	plot.title.text = 'Click on legend entries to hide the corresponding lines'

	# Bands
	band = add_band(x, y, 0., 2.5, plot, alpha=0.1)
	band2 = add_band(x, y, 2.5, 7.6, plot, alpha=0.3)
	band2 = add_band(x, y, 7.6, y.max(), plot, alpha=0.5)

	return Markup(file_html(plot, CDN, "Rain forecast for your ride"))

def add_band(x,y, minimum, maximum, plot, alpha, color='lightsteelblue'):
	dftemp = pd.DataFrame(data=dict(x=x, y=y[0])).sort_values(by="x")
	dftemp['upper'] = minimum
	dftemp['lower'] = maximum 
	source = ColumnDataSource(dftemp.reset_index())

	band = Band(base='x', lower='lower', upper='upper', source=source, level='underlay',
            	fill_alpha=alpha, line_width=0.3, line_color='black', fill_color=color, line_dash='dashed')
	plot.add_layout(band)
