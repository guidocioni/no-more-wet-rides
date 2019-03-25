from flask import Flask, send_file, request
from werkzeug import secure_filename

import radar_forecast_bike

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <h1>No more wet rides web app example :)</h1>
    <p>Upload your track CSV below</p>
    <html>
       <body>
          <form action = "/make_plot" method = "POST" 
             enctype = "multipart/form-data">
             <input type = "file" name = "file" />
             <input type = "submit"/>
          </form>
       </body>
    </html>
    """


@app.route('/make_plot', methods = ['GET', 'POST'])
def make_plot():
    if request.method == 'POST':
        f = request.files['file']
        track_filename = secure_filename(f.filename)
        f.save(track_filename)

        # obviously we should use a temporary file instead, otherwise multiple
        # parallel requests will overwrite the file from eachother...
        plot_filename = 'plot_example.png'
        radar_forecast_bike.main(track_file=track_filename, plot_filename=plot_filename)
        return send_file(plot_filename)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
