#!/bin/bash -x

YESTERDAY=$(date --utc --date='1 day ago' '+%Y-%m-%d %H:%M:%S')

psql << EOF
set time zone UTC;
delete from asdex where ptime < to_timestamp('$YESTERDAY', 'YYYY-MM-DD HH24:MI:ss')::timestamp without time zone at time zone 'Etc/UTC';
EOF


