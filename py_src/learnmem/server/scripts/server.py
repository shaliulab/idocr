############################
### Main callable script
############################

import argparse
import json
import logging
import signal
import sys

import coloredlogs
from learnmem.decorators import warning_decorator, error_decorator
from learnmem.server.core.control_thread import ControlThread
from learnmem.helpers import get_machine_id, get_git_version
from learnmem.configuration import LearnMemConfiguration
import bottle

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = bottle.Bottle()
STATIC_DIR = "../static"

@app.post("/update")
@warning_decorator
def update():

    data = bottle.request.body.read()
    data = json.loads(data)
    control.update(**data)

@app.get("/camera_settings")
@warning_decorator
def get_device_info():
    return {""}


@app.get("/data")
@warning_decorator
def info():
    return control.info


@app.post("/close")
@warning_decorator
def close():

    data = bottle.request.body.read()
    data = json.loads(data)

    status = control.close(answer=data["answer"])
    return status

@app.post('/load_program')
@warning_decorator
def load_program():

    data = bottle.request.body.read()
    data = json.loads(data)
    control.load_program(program_path=data["program_path"])


@app.get('/list_programs')
@warning_decorator
def list_programs():

    return control.list_programs()

@app.get('/mapping')
@warning_decorator
def mapping():

    return control.mapping


@app.get('/pin_state')
@warning_decorator
def pin_state():

    return control.pin_state


@app.get("/controls/<action>")
@warning_decorator
def control(action):

    if action == "play":
        control.play()

    if action == "ok_arena":
        control.ok_arena()

    elif action == "record":
        control.record()

# Arguments to follow the command, adding video, etc options
ap = argparse.ArgumentParser()
ap.add_argument("--control", action='store_true', dest='control', help="Shall I run Arduino?")
ap.add_argument("--no-control", action='store_false', dest='control')
ap.add_argument("--track", action='store_true', dest='track', help="Shall I track flies?")
ap.add_argument("--no-track", action='store_false', dest='track', help="Shall I track flies?")
ap.add_argument("-r", "--reporting", action='store_true')
ap.add_argument("-c", "--camera",      type=str, help="Stream source", choices=["webcam", "pylon"], default='pylon')
# ap.add_argument("--config",            type=str, help="Path to config.yaml file")
ap.add_argument("-e", "--experimenter",type=str, help="Add name of the experimenter/operator")
ap.add_argument("-f", "--fps",         type=int, help="Frames per second in the opened stream. Default as stated in the __init__ method in Tracker, is set to 2")
ap.add_argument("-g", "--gui_name",    type=str, help="tkinter/opencv", choices=['opencv', 'tkinter', 'cli'])
ap.add_argument("-l", "--log_dir",     type=str, help="Absolute path to directory where log files will be stored")
ap.add_argument("-o", "--output_path", type=str, help="Absolute path to directory where output files will be stored")
ap.add_argument("-m", "--mapping_path",     type=str, help="Absolute path to csv providing pin number-pin name mapping", )
ap.add_argument("-p", "--port",        type=int)
ap.add_argument("--arduino_port",      type=str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows")
ap.add_argument("--program_path",           type=str, help="Absolute path to csv providing the Arduino top level program")
ap.add_argument("-u", "--time",        type=str, help="Time unit to be used", default="m")
ap.add_argument("-v", "--video",       type=str, help="location to the video file", default=None)
ap.add_argument("-b", "--board",       type=str, help="Name of Arduino board in use", choices=["ArduinoUno", "ArduinoMega", "ArduinoDummy"])
ap.add_argument("-D", "--debug",       action='store_true', dest="debug")
ap.set_defaults(
    control=False, track=False, output_path="lemdt_results",
    gui_name='cli', log_dir='.', port=9000, arduino_port="/dev/ttyACM0", camera='pylon', experimenter="Sayed", board='ArduinoDummy'

)

CFG = LearnMemConfiguration()


data = vars(ap.parse_args())

machine_id = get_machine_id()
version = get_git_version()
result_dir = CFG.content["folders"]["results"]["path"]


PORT = data.pop("port") or CFG.content["network"]["port"]

logger.info("Running server on port %d", PORT)

# DEBUG = data.pop("debug") or CFG.content["network"]["port"]
data.pop("debug")
DEBUG = CFG.content["network"]["port"]

control = ControlThread(
    machine_id=machine_id,
    version=version,
    result_dir=result_dir,
    experiment_data=data,
)

control.start()

logger.info("Started ControlThread")

def stop(signo=None, _frame=None):
    global control
    logging.info("Received signal %s", signo)
    control.close()
    sys.exit(0)

signals = ('TERM', 'HUP', 'INT')
for sig in signals:
    signal.signal(getattr(signal, 'SIG' + sig), stop)

class CherootServer(bottle.ServerAdapter):
    def run(self, handler): # pragma: no cover
        from cheroot import wsgi
        from cheroot.ssl import builtin
        self.options['bind_addr'] = (self.host, self.port)
        self.options['wsgi_app'] = handler
        certfile = self.options.pop('certfile', None)
        keyfile = self.options.pop('keyfile', None)
        chainfile = self.options.pop('chainfile', None)
        server = wsgi.Server(**self.options)
        if certfile and keyfile:
            server.ssl_adapter = builtin.BuiltinSSLAdapter(
                    certfile, keyfile, chainfile)
        try:
            server.start()
        finally:
            server.stop()

SERVER = "cheroot"
try:
    #This checks if the patch has to be applied or not. We check if bottle has declared cherootserver
    #we assume that we are using cherrypy > 9
    from bottle import CherootServer
except Exception as e:
    #Trick bottle to think that cheroot is actulay cherrypy server, modifies the server_names allowed in bottle
    #so we use cheroot in background.
    SERVER="cherrypy"
    bottle.server_names["cherrypy"]=CherootServer(host='0.0.0.0', port=PORT)
    logger.warning("Cherrypy version is bigger than 9, we have to change to cheroot server")
    logger.warning(e)
#########

bottle.run(app, host='0.0.0.0', port=PORT, debug=DEBUG, server=SERVER)