from flask import Flask, send_file, request, render_template, Markup
from werkzeug import secure_filename
import radar_forecast_bike
import plot_bokeh
import plot_matplotlib

server = Flask(__name__)

@server.route('/')
def home():
    return """
    <html>
    <head>
        <title>No More Wet Rides Example</title>
    </head>
    <body>
        <h1>No More Wet Rides Example</h1>
        <h2>GPX/CSV reader</h2>
        <form action = "/make_plot_file" method = "POST" 
           enctype = "multipart/form-data">
           <input type = "file" name = "file" />
           <input type = "submit"/>
        </form>
        <h2>Google maps itinerary</h2>
        <form class="Selection" method="POST" action="/make_plot_gmaps">  
           <input name="start_point" placeholder="Type your starting point">
           <input name="end_point" placeholder="Type your end point">
           <select class="selectMean" id="DropdownSelector" type="text" name="selectMean" placeholder="Select a means of transportation">
                <option disabled selected>Select a means of transportation</option>
                <option selected id="bicycling" value="bicycling">Bicycle</option>
                <option id="driving" value="driving">Car</option>
                <option id="walking" value="walking">By foot</option>
           </select>
           <input class="btn" type="submit" value="submit">
        </form>
    </body>
    </html>
    """

@server.route('/make_plot', methods = ['GET', 'POST'])
def make_plot():
  if request.method == 'POST':
    if request.files['file']:
      f = request.files['file']
      track_filename = secure_filename(f.filename)
      f.save(track_filename)
    else:
      track_filename = 'track_points.csv'

    # obviously we should use a temporary file instead, otherwise multiple
    # parallel requests will overwrite the file from eachother...
    plot_filename = 'plot_example.png'

    df = radar_forecast_bike.main(track_file=track_filename)

    fig = plot_matplotlib.make_plot(df, out_filename=plot_filename)

    return send_file(plot_filename)

@server.route('/make_plot_gmaps', methods = ['GET', 'POST'])
def make_plot_gmaps():
  if request.method == 'POST':
    if (request.form.get("start_point") and request.form.get("end_point")):
      start_point = request.form.get("start_point")
      end_point = request.form.get("end_point")
      mode = request.form.get("selectMean")

      df = radar_forecast_bike.main(start_point=start_point, end_point=end_point, mode=mode)

      return plot_bokeh.create_plot(df)

@server.route('/make_plot_file', methods = ['GET', 'POST'])
def make_plot_file():
  if request.method == 'POST':
    if request.files['file']:
      f = request.files['file']
      track_filename = secure_filename(f.filename)
      f.save(track_filename)
    else:
      track_filename = 'track_points.csv'

    df = radar_forecast_bike.main(track_file=track_filename)

    return plot_bokeh.create_plot(df)
        
if __name__ == '__main__':
  server.run(debug=True, use_reloader=True)

