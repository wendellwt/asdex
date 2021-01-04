#!/bin/bash -x

# I think this is what shows up on the Connect intro page:
APP_TITLE="show_geojson"

# problem 1: npm build put files in static dir, rs deploy (or flask) want them in
# template dir
# works: cp static/index.html  templates/
# HELP:
sed 's%cssi_star.png%/content/188/static/cssi_star.png%' static/index.html > templates/index.html

# problem 2: can't figure out how to let git share this file, so
# _manually_ copy it around
cp ../service/cgi/get_tracks.py copied/

STATIC_FILES=`find static/ -type f | grep -v index.html`

#nope:     templates/cssi_star.png \

rsconnect deploy api --title $APP_TITLE --server http://172.26.21.40:3939 --api-key OV9jvi1YVE6WPYnSi09tX6i4UJvlciJc . \
     copied/get_tracks.py \
     templates/index.html  $STATIC_FILES

