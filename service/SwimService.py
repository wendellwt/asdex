# cherry py service

# =========================== to run manually:

# cd ~/realab/asdex/service
# /cygdrive/c/Users/wturner/Python37/python.exe SwimService.py  start
# ... Starting service CherryPyService

# =========================== in production:

# start the "CherryPy Service" using the "Services(Local)" tab in Services

# =========================== to view logs:

#  tail -f /cygdrive/c/temp/cherrypy_access.log
#  tail -f /cygdrive/c/temp/cherrypy_error.log
#  tail -f /cygdrive/c/temp/swimservice.log

# =========================== to install extra stuff:

# /cygdrive/c/Users/wturner/Python37/python.exe -m pip install cherrypy_cors

#===================================================================

"""
this code was taken from example here:
The most basic (working) CherryPy 3.1 Windows service possible.
Requires Mark Hammond's pywin32 package.
"""

import cherrypy
import win32serviceutil
import win32service

import sys
import os

# jan 10: cors attempt

import cherrypy_cors
cherrypy_cors.install()

#===================================================================

# get path (either cygwin or dos) to _this_ file
our_path = os.path.abspath( os.path.dirname(__file__))

# make (either cygwin or dos) path to cgi and code dirs
cgi_path  = os.path.join( our_path, 'cgi' )
code_path = os.path.join( our_path, 'code' )

# and append that to the pythonpath
sys.path.append(cgi_path)

# now with pythonpath set to _this_ dir (either cygwin or dos), do the import
# import causes postgis connection (sqlalc - engine)
import get_tracks

# and for complete path to config file and include it
config_file = os.path.join( our_path, 'srv.conf' )
cherrypy.config.update( config_file )

####################################################################
import time
import logging

#----------------------------
this_module_name = "swimservice"
#loglevel = logging.INFO     # <<<<<<<< change to INFO or WARNING if it works
loglevel = logging.DEBUG     # <<<<<<<< change to INFO or WARNING if it works
#----------------------------

from logging.handlers import TimedRotatingFileHandler

class UTCFormatter(logging.Formatter):
    converter = time.gmtime

# form logging filename
tempdir = "C:\\temp\\"

# since this is using Rotate, date & time don't make sense in filename (?)
log_fn = tempdir + this_module_name + ".log"

# create a ------ file handler
handler = TimedRotatingFileHandler( log_fn,
                         when = 'd',       # 'd' for normal operations
                         interval = 1,     # rotate every day
                         backupCount = 10 )

handler.setLevel(loglevel)

# create a logging format
uformatter = UTCFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(uformatter)

# ----- possibly put this into Swim __init__ :::::
lgr = logging.getLogger(__name__)
lgr.setLevel(loglevel)

# add the handlers to the logger
lgr.addHandler(handler)

lgr.info('starting...dec23, cmdline')
lgr.info('cwd:' + os.getcwd() )
lgr.info('name:' + __name__ )

####################################################################

class HelloWorld:
    """ Sample request handler class. """

    @cherrypy.expose
    def index(self):
        return "Hello world!"

####################################################################

class Swim(object):
    """ My own swim request handler class. """

    #---------------- # setup d.b. access and log file (ONCE!)
    def __init__(self):
        self.lgr = lgr
        self.lgr.warning("Swim(): __init__")
        # BAD: DEC23!!! self.db = get_tracks.MyPostGIS( )

    #---------------- the one and only ajax access
    @cherrypy.expose
    @cherrypy.tools.json_out()

    #old: def get_tracks_ajax( self, apt, random):
    def get_asdex( self, apt, rand):

        self.lgr.info("Swim(): get_tracks_ajax")

        # stdds: where src_airport='PCT'
        gjson = get_tracks.query_asdex( self.lgr, "stdds")
        #old:gjson = get_tracks.ajax( self.lgr, "stdds", "PCT" )

        # asdex: where src='KIAD'
        #gjson = get_tracks.ajax( self.db, self.lgr, "asdex", "KIAD" )

        # fdps: where arr_apt='KIAD'
        #gjson = get_tracks.ajax( self.db, self.lgr, "fdps", "KIAD" )

        self.lgr.info("Swim(): return")

        return gjson

    #---------------- new: march forth, 2019
    def __del__(self):
        self.db.close()
        # Q: and close logger's handler here?

    get_asdex.exposed = True    # does this duplicate the @ decorator?

####################################################################

class SwimService(win32serviceutil.ServiceFramework):
    """NT Service."""

    _svc_name_         = "CherryPyService"
    _svc_display_name_ = "CherryPy Service"
    _svc_description_  = "Wendell's SWIM service using Python's " + \
                         "CherryPy and pywin32"

    def SvcDoRun(self):

        cherrypy.tree.mount( Swim(), '/', config={
            '/': {
                # --- all of this moved to srv.conf ---
                # --- which waas BAD, Swim() NEEDS these here!
                'tools.staticdir.on': True,
                'tools.staticdir.root': code_path,
                'tools.staticdir.dir':  code_path,

                # BAD! enabling this works for an index, but MESSES UP ajax!!
                #'tools.staticdir.index': os.path.join(code_path,'index.html')

                # jan10:
                'cors.expose.on': True,
            },
        })

        # left over from the example:
        cherrypy.tree.mount(HelloWorld(), '/hello')

        cherrypy.engine.start()
        cherrypy.engine.block()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        cherrypy.engine.exit()

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)
        # very important for use with py2exe
        # otherwise the Service Controller never knows that it is stopped !

####################################################################

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SwimService)

