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
from sqlalchemy import create_engine
from shapely.geometry import LineString
import socket

# ------------------------------------------------------------------

go_back = 1   # search back this many minutes

#==========================================================

# HELP: on asdi-db, this runs as a windows Service, i.e. runs under
# windows' python.exe, which I didn't get around to installing geopandas
# (which requires gdal, which requires proj6, which requires gosh knows what)
# So, we do the best we can without geopandas...

# also, need to get postgresql credentials...
# postgresql+psycopg2://user:passwd@asdi-db.cssiinc.com/ciwsdb

# ------------------- rserver  ( production under Flask and RConnect)

if socket.gethostname() == 'acy_test_app_vm_rserver':

    import geopandas as gpd
    # we're on Linux, under RConnect, with Flask

    # ISSUE: need GeoPandas' to_json to put id adjacent to properites, not
    # within it; hence this:
    # SOULD BE: HAVE_gpd = True
    HAVE_gpd = False

    # ISSUE: in RConnect deployment: use Settings panel to configure these
    connect_alchemy = "postgresql+psycopg2://"            + \
                    os.environ.get('CSSI_USER')     + ':' + \
                    os.environ.get('CSSI_PASSWORD') + '@' + \
                    os.environ.get('CSSI_HOST')     + '/' + \
                    os.environ.get('CSSI_DATABASE')

# ------------------- my faa laptop   (local debugging)

if socket.gethostname() == 'JAWAXFL00172839':

    HAVE_gpd = False

    connect_alchemy = "postgresql+psycopg2://"            + \
                    os.environ.get('CSSI_USER')     + ':' + \
                    os.environ.get('CSSI_PASSWORD') + '@' + \
                    os.environ.get('CSSI_HOST')     + '/' + \
                    os.environ.get('CSSI_DATABASE')

# ------------------- asdi-db    (production under CherryPy)

if socket.gethostname() == 'ASDI-DB':

    HAVE_gpd = False

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

def get_path_lines(lgr, then):

    # =========================== 1/3: id equal to properties
    #   (for vuelayers fast load)

    # https://gis.stackexchange.com/questions/14514/exporting-feature-geojson-from-postgis
    #'properties', to_jsonb(row) - 'position'

    sql = """ set time zone UTC;
SELECT jsonb_build_object(
    'type',       'Feature',
    'id',         track,
    'geometry',   ST_AsGeoJSON(linest)::jsonb,
    'properties', to_jsonb(row) - 'linest'
  ) AS feature
  FROM (
 select track, acid, actype, ST_MakeLine(position)::geometry as linest
    FROM (
        select track, acid, actype, ptime, position
        from asdex
        where ptime > to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS')
                          at time zone 'Etc/UTC'
        and acid != 'unk'
        order by track, ptime
        ) as foo
    group by track, acid, actype
) row; """ % then

    # ==========================================================

    lgr.info("calling get - asdex")
    lgr.debug(sql)

    results = engine.execute(sql)
    lgr.debug("done")

    # ---- results is an interable QueryObject

    #old: res = [ geojson.loads(row[0]) for row in results]
    # new:
    res_lines = [ row[0] for row in results]

    return(res_lines)

# ----------------------------------------------------------------------

def get_path_points(lgr, then):

    # =========================== 1/4: get last Point for a/c symbol
    # 'id',         track,

    sql = """ set time zone UTC;

SELECT jsonb_build_object(
    'type',       'Feature',
    'geometry',   ST_AsGeoJSON(acpoint)::jsonb,
    'properties', to_jsonb(row) - 'mtime' - 'acpoint'
  ) AS feature
  FROM ( select distinct a.track, a.acid, maxt.mtime, a.actype, a.position::geometry as acpoint
FROM
( select distinct track, acid, actype, max(ptime) as mtime
     from asdex
      where ptime > to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS')
                          at time zone 'Etc/UTC'
     and acid != 'unk'
     group by track, acid, actype
) maxt,
asdex a
WHERE a.track  = maxt.track
AND   a.acid   = maxt.acid
AND   a.actype = maxt.actype
AND   a.ptime  = maxt.mtime
ORDER BY a.track
) row;

    ; """ % then

    lgr.info("calling get - asdex")
    lgr.debug(sql)

    results = engine.execute(sql)
    lgr.debug("done")

    # ---- results is an interable QueryObject

    res_points = [ row[0] for row in results]

    return(res_points)

# ----------------------------------------------------------------------
from pprint import pprint

# on windows (asdi-db, without geopandas), do everything in PostGIS

def query_using_postgis(lgr, then):

    res_lines = get_path_lines(lgr, then)

    res_points = get_path_points(lgr, then)

    #pprint(res_lines[:2])
    #print()
    #pprint(res_points[:2])
    #print()

    #pprint(res_lines[:2] + res_points[:2])

    # ==========================================================
    # ---- add in a crs
    fc = { "type": "FeatureCollection",
          "features": res_points + res_lines,
           "crs": { "type": "name",
                    "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                                     # old: "urn:ogc:def:crs:EPSG::4326"
                   }
               }
     }

    return(fc)

# #######################################################################

def make_props(row_track, row_acid, row_actype):

    #p = { 'track':track, 'acid': acid, 'actype':actype}
    #p = { 'track':'t', 'acid': 'a', 'actype':'y'}
    #p = { 'track':row, 'acid':'a', 'actype':'y' }
    #p = { 'acid':row_acid, 'actype':'y' }
    p = { 'track':row_track, 'acid':row_acid, 'actype':row_actype }
    return(json.dumps(p))

# -----------------------------------------------------------------------

def make_feat(row_id, row_props, row_geom):

    # HELP: seems like going back & forth on the dumps/loads !!!

    f = { "type": "Feature",
          "properties": json.loads(row_props),
          "geometry": json.loads(row_geom),
          "id": row_id
        }

    return(f)
    #return(json.dumps(f))

# ############################################################## #
#                 everything but without geopandas               #
# ############################################################## #

from shapely.geometry import mapping, shape
from shapely.wkt import dumps, loads

# ----------------------------------------------------------------

def query_for_points(lgr, then):
    # ---- 1. query for all position points (as text) ordered by ptime

    sql = """ set time zone UTC;
SELECT track, acid, actype, ptime, ST_AsText(position) as position
FROM asdex
WHERE ptime > to_timestamp('%s', 'YYYY-MM-DD HH24:MI:SS')
                          AT TIME ZONE 'Etc/UTC'
AND acid != 'unk'
ORDER BY ptime ; """ % then

    lgr.info("calling get - asdex")
    lgr.debug(sql)

    points_df = pd.read_sql(sql, con=engine)

    lgr.info(points_df)

    # ---- 2. make text points into shapely points

    points_df['shp'] = points_df.apply( lambda row: loads(row['position']), axis=1)

    # groupby for track position doesn't like shapely's Point column
    # so leaf this one here for now...
    #points_df.drop('position', axis=1, inplace=True)

    return(points_df)
# ------------------------------------------------------------------------

# ---- 3. make linestring (ptime order is preserved, correct?)

# -- 3a: (as_index WORKS on faa laptop, NEEDS REMOVED # on asdi-db!!!)

def make_path_linestrings(lgr, points_df):

    # aggregate these Points with the GroupBy and make them into LineString
    # it may be a Series (_sr)

    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    # @                     HELP!!! WHY is this necessary????              @
    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    if socket.gethostname() == 'acy_test_app_vm_rserver':
        lstring_sr = points_df.groupby(['track', 'acid', 'actype'],as_index=False)['shp'].apply(lambda x: x.tolist())
    else:
        lstring_sr = points_df.groupby(['track', 'acid', 'actype']               )['shp'].apply(lambda x: x.tolist())
    # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    lstring_df = lstring_sr.to_frame().reset_index()

    lstring_df.columns = ['track', 'acid', 'actype', 'shp']  # shp column was '0'

    # -- 3b: make sure strings have at least 2 points

    lstring_df.drop(lstring_df[lstring_df['shp'].map(len) < 2].index, inplace = True)

    # -- 3c: finally, make them into Shapely LineStrings

    lstring_df['path_ls'] = lstring_df.apply( lambda x: LineString(x['shp']), axis=1 )

    lstring_df.drop('shp', axis=1, inplace=True)

    # ---- btw, clean up (sometimes track is None/na/empty!!!)
    clean_df = lstring_df.dropna()

    return(clean_df)

# ----------------------------------------------------------------

# ---- 5. make GeoJson column of linestring

def make_features(lgr, linest_df):

    # 5a. make geometry stanza of geojson

    linest_df['geom'] = linest_df.apply( lambda x: json.dumps(mapping(x['path_ls'])), axis=1 )
    linest_df.drop('path_ls', axis=1, inplace=True)

    # 5b. make propertie stanza of geojson

    linest_df['props'] = linest_df.apply( lambda row: make_props(row['track'], row['acid'], row['actype']), axis=1 )

    # 5c. make full features stanza of geojson

    linest_df['feat'] = linest_df.apply( lambda row: make_feat(row['track'], row['props'], row['geom']), axis=1 )

    # clean up
    linest_df.drop(['acid','actype', 'props','geom'], axis=1, inplace=True)

    return(linest_df)

# ----------------------------------------------------------------

def find_latest_point(lgr, points_df):

    #position_sr = points_df.groupby(['track', 'acid', 'actype', 'position'])['ptime'].apply(lambda x: x.max())
    #position_sr = points_df.groupby(['track', 'acid', 'actype', 'position'])['ptime'].max()

    #In [3]: idx = df.groupby(['Mt'])['count'].transform(max) == df['count']

    # HEY, maybe this is how to do a '.groupby' and retain the datafraem
    # (without it becoming a Series)
    # NOPE, sometimed DUPLICATE TRACKs appear!!! :-(
    # not sure: position_sr = points_df[ points_df.groupby(['track'])['ptime'].transform(max) == points_df['ptime'] ]

    # seems ok: print(points_df.sort_values('ptime', ascending=False).drop_duplicates(['track']))
    position_df = points_df.sort_values('ptime', ascending=False).drop_duplicates(['track'])

    lgr.debug("position_df")
    lgr.debug(position_df)
    lgr.debug(type(position_df))
    lgr.debug(position_df.columns)
    lgr.debug("+++++++++")

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # while we're here, lets go ahead and make the GeoJson feature...

    position_df['target_geom'] = position_df.apply( lambda x: json.dumps(mapping(x['shp'])), axis=1 )

    lgr.debug("position_df")
    lgr.debug(position_df)
    lgr.debug(type(position_df))
    lgr.debug(position_df.columns)

    # +5b. make propertie stanza of geojson

    position_df['props'] = position_df.apply( lambda row: make_props(row['track']+990000, row['acid'], row['actype']), axis=1 )

    # +5c. make full features stanza of geojson

    position_df['feat'] = position_df.apply( lambda row: make_feat(row['track']+90000, row['props'], row['target_geom']), axis=1 )

    lgr.debug("====================")
    lgr.debug("position_df")
    lgr.debug(position_df)
    lgr.debug(type(position_df))
    lgr.debug(position_df.columns)

    # clean up
    position_df.drop(['acid','actype', 'props', 'ptime', 'position', 'shp', 'target_geom'], axis=1, inplace=True)

    lgr.debug("%%%%%%%%%%%%%%%%%%%%")
    lgr.debug("position_df")
    lgr.debug(position_df)
    lgr.debug(type(position_df))
    lgr.debug(position_df.columns)

    return(position_df)

# =========================================================================

def using_postgis_and_pandas(lgr, then):

    points_df = query_for_points(lgr, then)

    target_df = find_latest_point(lgr, points_df)

    linest_df = make_path_linestrings(lgr, points_df)

    features_df = make_features(lgr, linest_df)

    # ---- make into FeatureColl
    # geojson lint said our crs was the default and thus redundant

    fc = { "type": "FeatureCollection",
            "features": features_df['feat'].tolist() + \
                        target_df['feat'].tolist()
         }

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
    # ----------------------
    if socket.gethostname() == 'JAWAXFL00172839':

        fc = using_postgis_and_pandas(lgr, then)

    # ---------------------- regular (i.e., old)
    else:
        if HAVE_gpd:
            fc = query_using_geopandas(lgr, then)
        else:
            fc = query_using_postgis(lgr, then)
    ### ----------------------

    return(fc)

# ############################################################## #
#                        standalone main                         #
# ############################################################## #

import json

class NotLgr:  # pretend class to let lgr.info() work when not logging
    def info(self, s):
        print(s)
    def debug(self, s):
        print(s)

if __name__ == "__main__NOT":

    lgr = NotLgr()
    print("hello sailor")

    fc = query_asdex( lgr, "KIAD" )

    print("+++++++")
    print(json.dumps(fc))

