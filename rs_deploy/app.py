#######################################################################
#             Flask web server that works with RConnect               #
#######################################################################

import sys
import psycopg2
from mobilitydb.psycopg import register
from geojson import Feature, FeatureCollection, dumps

from flask import Flask, render_template, request

sys.path.append('copied')  # stupid git/sharing  work-around
import get_tracks
import web_logging

# --------------------------------------------------------------------

app = Flask(__name__)

# --------------------------------------------------------------------

lgr = web_logging.setup_logger("show_geosjon", "helpme")

lgr.info("web app starting")

#######################################################################
#                     get request handlers                            #
#######################################################################

@app.route('/')

def home():
    return render_template('index.html')

# -------------------------------------------------------------------

# let the_query = "get_geojsn?fn="  + filename;
# return GeoJson

@app.route('/get_geojson', methods=['GET'])

def do_something():

    filename = request.args['fn']

    gj_str = open(filename, 'r').read()

    return gj_str

# --------------------------------------------------------------------

@app.route('/get_kml', methods=['GET'])

def do_kml():
    filename = request.args['fn']
    kml_str = open(filename, 'r').read()
    return kml_str

# --------------------------------------------------------------------

@app.route('/get_asdex', methods=['GET'])

def do_asdex():

    lgr.info("get_asdex - in")

    bogus = request.args['apt']  # TODO! use this somehow

    asdex_gj = get_tracks.query_asdex(lgr, bogus )

    lgr.info("get_asdex - out")

    return asdex_gj

#######################################################################
#                            main                                     #
#######################################################################

if __name__ == '__main__':
    app.run()

