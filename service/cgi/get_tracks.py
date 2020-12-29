#!/usr/bin/python3.7

# imported from either SwimService.py or app.py
# to perform queries to PostGIS on asdi-db

# -------------------------------------------------------
# to run on asdi-db using the server's python:
#   /cygdrive/c/Users/wturner/Python37/python.exe get_tracks.py

# to run on rserver:
#  /usr/bin/python3.7 get_tracks.py
# -------------------------------------------------------

import os
import pytz
import datetime
import psycopg2
import pandas as pd
import geojson
from sqlalchemy import create_engine
from shapely.geometry import LineString

# ------------------------------------------------------------------

go_back = 3   # search back this many minutes

#==========================================================

# HELP: on asdi-db, this runs as a windows Service, i.e. runs under
# windows' python.exe, which I didn't get around to installing geopandas
# (which requires gdal, which requires proj6, which requires gosh knows what)
# So, we do the best we can without geopandas...

# also, need to get postgresql credentials...
# postgresql+psycopg2://user:passwd@asdi-db.cssiinc.com/ciwsdb

try:
    import geopandas as gpd
    # we're on Linux, under RConnect, with Flask
    HAVE_gpd = True

    # ISSUE: in RConnect deployment: use Settings panel to configure these
    connect_alchemy = "postgresql+psycopg2://"            + \
                    os.environ.get('CSSI_USER')     + ':' + \
                    os.environ.get('CSSI_PASSWORD') + '@' + \
                    os.environ.get('CSSI_HOST')     + '/' + \
                    os.environ.get('CSSI_DATABASE')
except:
    HAVE_gpd = False
    # we're on Windows, under Service, with CherryPy

    conf_file = os.path.dirname(os.path.realpath(__file__)) + os.path.sep + '.winsvc.toml'

    # $ /cygdrive/c/Users/wturner/Python37/python.exe -m pip install toml
    import toml

    with open(conf_file) as fd:
        raw_config = fd.read()
    cfg = toml.loads(raw_config)

    # ISSUE: on asdi-db: use .winsvc.toml config file
    connect_alchemy = "postgresql+psycopg2://"            + \
                    cfg['CSSI_USER']     + ':' + \
                    cfg['CSSI_PASSWORD'] + '@' + \
                    cfg['CSSI_HOST']     + '/' + \
                    cfg['CSSI_DATABASE']


engine = create_engine(connect_alchemy)

# ======================================================================

# on Linux (rserver), we have geopandas, so do a simple query and do the
# rest of the processing in GeoPandas

def query_using_geopandas(lgr, then):

    # when 'select ptime ' is included:
    # TypeError: Object of type Timestamp is not JSON serializable

    sql = "select track, position as geometry " + \
          "from asdex " + \
          "where lon is not null and lat is not null " + \
          "and ptime is not null " +  \
          "and ptime > '" + then.isoformat() + "' " + \
          "order by track, ptime;"  # limit 5

    lgr.info("calling get - asdex")
    lgr.debug(sql)

    # read postgis directly into GeoPandas, with position as geom
    #    (but geom column is just a column of points)
    points_gf = gpd.read_postgis(sql,con=engine, geom_col='geometry')

    # the lambda LineString operation below barfs if less than 2 points
    not_single_gf = points_gf.groupby('track').filter(
                                                lambda x : len(x)>1)

    # group the tracks together and make a linestring of the points
    linestrings_gf = not_single_gf.groupby(['track'])['geometry']        \
                                .apply(lambda x: LineString(x.tolist()))

    # and force the linestring column to be the geometry column:
    tracks_gf = gpd.GeoDataFrame(linestrings_gf, geometry='geometry')

    lgr.info("num points returning:%d" % len(tracks_gf))  # works

    if len(tracks_gf) == 0:
        return None   # fail???, but what about json encoding???

    fc = tracks_gf.to_json()

    return(fc)

# ======================================================================

# on windows (asdi-db, without geopandas), do everything in PostGIS

def query_using_postgis(lgr, then):

    sql = """ set time zone UTC;
SELECT ST_AsGeoJSON(t.*)
FROM (
    select track, ST_MakeLine(position)::geometry
    FROM (
        select track, ptime, position
        from asdex
        where ptime > to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS')
                          at time zone 'Etc/UTC'
        order by track, ptime
        ) as foo
    group by track
    )
AS t(id, geom);""" % then

    # nope for all variants: group by track, ptime order by ptime, track
    #group by track
    #group by track
    #nope: order by ptime

    lgr.info("calling get - asdex")
    lgr.debug(sql)

    results = engine.execute(sql)

    res = [ geojson.loads(row[0]) for row in results]

    #fc = { "type": "FeatureCollection", "features": res }

    fc = { "type": "FeatureCollection",
           "features": res,
           "crs": { "type": "name",
                    "properties": { "name": "urn:ogc:def:crs:EPSG::4326"
                   }
               }
     }

    return(fc)

# #######################################################################

# entry point from Flask    / app.py         (via '/get_asdex' get request)
# entry point from CherryPy / SwimService.py (via '/get_asdex' get request)

def query_asdex( lgr, location ):

    lgr.info("inside query_asdex")

    # search for ptime > this many minutes back from "right now"
    then = datetime.datetime.now( tz=pytz.utc ) \
           - datetime.timedelta( minutes=go_back )

    # ----------------------
    if HAVE_gpd:
        fc = query_using_geopandas(lgr, then)
    else:
        fc = query_using_postgis(lgr, then)
    # ----------------------

    return(fc)

# ##############################################################

if __name__ == "__main__NOT":

    features = query_asdex( None, "KIAD" )

    print(features)

