#!/usr/bin/python3.7

# ############################################################## #
#           web server postgis retrieval procedures              #
# ############################################################## #

# imported from either SwimService.py or app.py
# to perform queries to PostGIS on asdi-db

# -------------------------------------------------------
# to run on asdi-db using the server's python:
#   /cygdrive/c/Users/wturner/Python37/python.exe get_tracks.py

# to run on faa laptop:
#  /usr/bin/python3.7 get_tracks.py

# to run on rserver:
#  python3.7 get_tracks.py
# -------------------------------------------------------------------------
# ISSUE: it was too hard to install GeoPandas (and GEOS and Proj and ...)
# on the Windows Python (cygwin python was fine).  Also, it was better
# to have just one set of procedures (rather than a GeoPandas (rserver)
# one and a Python/Sahpely one (asdi-db)
# -------------------------------------------------------------------------

import os
import sys
import pytz
import datetime
import psycopg2
import pandas as pd
import geojson
import socket

from sqlalchemy import create_engine
from shapely.wkt import dumps, loads
from shapely.geometry import LineString, mapping, shape

# ------------------------------------------------------------------

go_back = 1    # search back this many minutes
off = 900000   # offset from target id to linestring id

#==========================================================

# HELP: on asdi-db, this runs as a windows Service, i.e. runs under
# windows' python.exe, which I didn't get around to installing geopandas
# (which requires gdal, which requires proj6, which requires gosh knows what)
# So, we do the best we can without geopandas...

# also, need to get postgresql credentials...
# postgresql+psycopg2://user:passwd@asdi-db.cssiinc.com/ciwsdb

# ------------------- rserver  ( production under Flask and RConnect)

if socket.gethostname() == 'acy_test_app_vm_rserver':

    # we're on Linux, under RConnect, with Flask

    # ISSUE: in RConnect deployment: use Settings panel to configure these
    connect_alchemy = "postgresql+psycopg2://"            + \
                    os.environ.get('CSSI_USER')     + ':' + \
                    os.environ.get('CSSI_PASSWORD') + '@' + \
                    os.environ.get('CSSI_HOST')     + '/' + \
                    os.environ.get('CSSI_DATABASE')

# ------------------- my faa laptop   (local debugging)

if socket.gethostname() == 'JAWAXFL00172839':

    connect_alchemy = "postgresql+psycopg2://"            + \
                    os.environ.get('CSSI_USER')     + ':' + \
                    os.environ.get('CSSI_PASSWORD') + '@' + \
                    os.environ.get('CSSI_HOST')     + '/' + \
                    os.environ.get('CSSI_DATABASE')

# ------------------- asdi-db    (production under CherryPy)

if socket.gethostname() == 'ASDI-DB':

    # we're on Windows, under Service, with CherryPy

    conf_file = os.path.dirname(os.path.realpath(__file__)) + \
                                 os.path.sep + '.winsvc.toml'

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

# ------------------- common

engine = create_engine(connect_alchemy)

# ########################################################################## #
#                         everything but without geopandas                   #
# ########################################################################## #

# ---- 1. query for all position points (as text) ordered by ptime

# >>> jan 10: added ST_DWithin on IAD to make result set smaller
# >>> jan 10: NO navaids or fixes on asdi-db, FIXED to kiad loc
# >>> jan 10: made IAD dist really small: 0.3

def query_for_points(lgr, then):

    sql = """ set time zone UTC;
SELECT track, acid, actype, ptime, ST_AsText(position) as position
FROM asdex
WHERE ptime > to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS')
                          AT TIME ZONE 'Etc/UTC'
AND acid != 'unk'
AND ST_DWithin(position, ST_SetSRID(ST_MakePoint(-77.4599444, 38.9474444),4326),0.3)
ORDER BY ptime ; """ % then

    lgr.info("calling get - asdex")
    lgr.debug(sql)

    # ---- a. make text points into shapely points

    points_df = pd.read_sql(sql, con=engine)

    lgr.info(points_df)

    # ---- b. make text points into shapely points

    points_df['shp'] = points_df.apply( lambda row: loads(row['position']),
                                       axis=1)

    # ---- c. clean up

    # However, groupby for track position doesn't like shapely's Point column
    # so let's leave the text one here for now...
    #points_df.drop('position', axis=1, inplace=True)

    return(points_df)

# -----------------------------------------------------------------------

# ---- 2. find point where to draw a/c target symbol

def find_target_point(lgr, points_df):

    # HEY, maybe this is how to do a '.groupby' and retain the datafraem
    # (without it becoming a Series)
    # NOPE, sometimed DUPLICATE TRACKs appear!!! :-(
    # not sure: position_sr = points_df[ points_df.groupby(['track']) \
    #    ['ptime'].transform(max) == points_df['ptime'] ]

    # ---- a. get the point of each track with the largest(latest) time

    position_df = points_df.sort_values('ptime', ascending=False)  \
                           .drop_duplicates(['track'])

    # ---- b. while we're here, lets go ahead and make the GeoJson feature...

    #position_df['target_geom'] = position_df.apply(
    position_df['geom'] = position_df.apply(
        lambda x: mapping(x['shp']), axis=1 )

    # ---- c. make propertie stanza of geojson

    position_df['props'] = position_df.apply(lambda row: make_props(row),axis=1)

    # ---- d. make full features stanza of geojson

    position_df['feat'] = position_df.apply(lambda row: make_feat(row),axis=1 )

    # ---- clean up
    position_df.drop(['acid','actype', 'props', 'ptime',
                      'position', 'shp', 'geom'], axis=1, inplace=True)

    return(position_df)

# -----------------------------------------------------------------------

# ---- 3. make linestring (ptime order is preserved, correct?)

def make_path_linestrings(lgr, points_df):

    # aggregate these Points with the GroupBy and make them into LineString
    # it may be a Series (_sr)

    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    # @                     HELP!!! WHY is this necessary????              @
    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    if socket.gethostname() == 'acy_test_app_vm_rserver':

        lstring_sr= points_df.groupby(['track','acid','actype'],as_index=False)\
                                  ['shp'].apply(lambda x: x.tolist())
    else:
        lstring_sr= points_df.groupby(['track', 'acid', 'actype']) \
                                   ['shp'].apply(lambda x: x.tolist())
    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    lstring_df = lstring_sr.to_frame().reset_index()

    lstring_df.columns = ['track','acid','actype', 'shp']  # shp column was '0'

    # ---- b. make sure strings have at least 2 points

    lstring_df.drop(lstring_df[lstring_df['shp'].map(len) < 2].index,
                                                                 inplace=True)

    # ---- c. finally, make them into Shapely LineStrings

    lstring_df['path_ls'] = lstring_df.apply( lambda x: LineString(x['shp']),
                                                                 axis=1 )

    # ---- d.  clean up (btw, sometimes track is None/na/empty!!!)

    lstring_df.drop('shp', axis=1, inplace=True)
    clean_df = lstring_df.dropna()

    return(clean_df)

# -----------------------------------------------------------------------

def make_props(row):

    return( { 'track':row['track'], 'acid':row['acid'], 'actype':row['actype']})

def make_feat(row):

    return( geojson.Feature( geometry=row['geom'], properties=row['props'],
                            id=row['track']))

                            #help:id=str(row['track'])))

# -----------------------------------------------------------------------

# ---- 4. make GeoJson column of Feature

def make_features(lgr, linest_df):

    # ---- a. make geometry stanza of geojson

    linest_df['geom'] = linest_df.apply( lambda x: mapping(x['path_ls']),axis=1)

    # ---- b. make property stanza of geojson

    linest_df['track'] = linest_df['track'] + off

    linest_df['props'] = linest_df.apply( lambda row: make_props(row), axis=1)

    # ---- c. make full features stanza of geojson

    linest_df['feat'] = linest_df.apply( lambda row: make_feat(row), axis=1)

    # ---- d. clean up

    linest_df.drop(['acid','actype', 'props',
                    'geom', 'path_ls'], axis=1, inplace=True)

    return(linest_df)

# =========================================================================

def using_postgis_and_pandas(lgr, then):

    points_df = query_for_points(lgr, then)

    target_df = find_target_point(lgr, points_df)

    linest_df = make_path_linestrings(lgr, points_df)

    features_df = make_features(lgr, linest_df)

    # ---- make into FeatureColl
    # (geojson lint said our crs was the default and thus redundant)

    fc = geojson.FeatureCollection( \
          features_df['feat'].tolist() +  target_df['feat'].tolist() )

    lgr.debug("done")

    return(fc)

# #######################################################################

# entry point from Flask    / app.py         (via '/get_asdex' get request)
# entry point from CherryPy / SwimService.py (via '/get_asdex' get request)

def query_asdex( lgr, location ):

    lgr.info("inside query_asdex")

    # search for ptime > this many minutes back from "right now"
    then = datetime.datetime.now( tz=pytz.utc ) \
           - datetime.timedelta( minutes=go_back )

    fc = using_postgis_and_pandas(lgr, then)

    return(fc)

# ######################################################################## #
#                              standalone main                             #
# ######################################################################## #

import json
from pprint import pprint

class NotLgr:  # pretend class to let lgr.info() work when not logging
    def info(self, s):
        print(s)
    def debug(self, s):
        print(s)

# ==========================================================================

if __name__ == "__main__NOT":

    lgr = NotLgr()
    print("hello sailor")

    fc = query_asdex( lgr, "KIAD" )

    print("+++++++")
    print(json.dumps(fc))
    print(">>>>>>>")
    pprint(fc)

