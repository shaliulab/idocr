#!  /home/vibflysleep/anaconda3/envs/idoc/bin/python

############################
### Main callable script
############################

import argparse
import json
import logging
import logging.handlers
import os
import signal
import sys
from threading import Thread
import time
import urllib.parse

import bottle
import coloredlogs

from idoc.decorators import warning_decorator, error_decorator, wrong_id
from idoc.server.core.control_thread import ControlThread
from idoc.helpers import get_machine_id, get_git_version, get_server
from idoc.configuration import IDOCConfiguration

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename='IDOC.log',
                    filemode='w')

logger = logging.getLogger('')
coloredlogs.install()

socket_handler = logging.handlers.SocketHandler(
    'localhost',
    logging.handlers.DEFAULT_TCP_LOGGING_PORT
)
logger.addHandler(socket_handler)


app = bottle.Bottle()
STATIC_DIR = "../static"

@app.route('/static/<filepath:path>')
def server_static(filepath):
    return bottle.static_file(filepath, root="/")

@app.post("/settings/<id>")
@warning_decorator
@wrong_id
def update():
    r"""
    Receive the new settings passed by the user
    via a POST request in JSON format.
    A partial update is ok i.e. not all parameters
    need to be supplied, only those changing.
    A dictionary with the current values is returned
    upong GETting to this same URL.
    """

    post_data = bottle.request.body.read() # pylint: disable=no-member

    if isinstance(post_data, bytes):
        data_decoded = post_data.decode()
    else:
        data_decoded = post_data

    try:
        data_parsed = json.loads(data_decoded)
    except json.decoder.JSONDecodeError:
        data_parsed = urllib.parse.parse_qs(data_decoded)

    settings = data_parsed['settings']
    submodule = data_parsed['submodule']
    if submodule == "control_thread":
        control.settings = settings
    else:
        target = control
        for module in submodule:
            target = getattr(target, module)

        if target is not None:
            target.settings = settings
        else:
            logger.warning("Module %s is not initialized yet.", module)

    return {"status": "success"}


@app.get("/settings/<id>")
@wrong_id
@warning_decorator
def report():
    r"""
    Return current value of the settings to the user
    Settings can be updated by POSTing to the same URL.
    """
    settings = control.settings
    return settings


@app.get("/info/<id>")
@warning_decorator
@wrong_id
def inform():
    r"""
    Return information about the control thread to the user,
    contained in the info property.
    """
    return control.info

@app.get('/id')
@error_decorator
def get_id():
    r"""
    Return the content of /etc/machine-id to the user.
    URLs are suffixed in the API to check the supplied id
    with the id of the machine.
    A mismatch is interpreted as a user mistake and a
    WrongMachineID expception is raised.
    """
    return {"id": control.info["id"]}


@app.post('/load_paradigm/<id>')
@warning_decorator
@wrong_id
def load_paradigm():
    r"""
    Update the hardware paradigm loaded in IDOC.
    Do this by posting an object with key paradigm_path
    and value the filename of one of the csv files in the
    paradigms_dir.
    paradigms_dir is defined in the config file under
    folders > paradigms > path.
    A list of the paradigms can be retrieved by GETting to /list_paradigms/.
    """
    post_data = bottle.request.body.read() # pylint: disable=no-member
    if isinstance(post_data, bytes):
        data_decoded = post_data.decode()
    else:
        data_decoded = post_data

    try:
        data_parsed = json.loads(data_decoded)
    except json.decoder.JSONDecodeError:
        data_parsed = urllib.parse.parse_qs(data_decoded)

    paradigm_path = data_parsed["paradigm_path"][0]
    control.load_paradigm(paradigm_path=paradigm_path)
    return {"status": "success"}


@app.post('/description/<id>')
@warning_decorator
@wrong_id
def description():
    r"""
    Set a description of the experiment
    """
    post_data = bottle.request.body.read() # pylint: disable=no-member
    if isinstance(post_data, bytes):
        data_decoded = post_data.decode()
    else:
        data_decoded = post_data

    data_parsed = json.loads(data_decoded)
    control.description = data_parsed["description"]

    return {"status": "success"}


@app.get('/list_paradigms/<id>')
@warning_decorator
@wrong_id
def list_paradigms():
    r"""
    Get a list of the available paradigms that the user
    can select via POSTing to /load_paradigm.
    This is also available in info["controller"]["paradigms"].
    """
    return control.list_paradigms()

@app.get('/mapping/<id>')
@warning_decorator
@wrong_id
def mapping():
    r"""
    Tell the user that is the hardware-board pin mapping loaded in IDOC
    This is also available in info["controller"]["mapping"].
    """
    return control.mapping

@app.get('/pin_state/<id>')
@warning_decorator
@wrong_id
def pin_state():
    r"""
    Return the status of the board pins
    This is also available in info["controller"]["pin_state"]
    """
    return control.pin_state


@app.get('/controls/<submodule>/<action>/<id>')
@warning_decorator
@wrong_id
def control(submodule, action):
    r"""
    Command the IDOC modules.
    Set a submodule as ready, start or stop it by supplying
    ready, start and stop as action
    Actions are available for the recognizer and controller modules
    as well as the control thread.
    """
    if submodule == "control_thread" and action == "stop":
        # exit the application completely
        stop()

    return control.command(submodule, action)


@app.post("/controls/toggle/<id>")
@warning_decorator
@wrong_id
def toggle():

    post_data = bottle.request.body.read() # pylint: disable=no-member
    if isinstance(post_data, bytes):
        data_decoded = post_data.decode()
    else:
        data_decoded = post_data

    logger.debug(data_decoded)

    data_parsed = json.loads(data_decoded)
    hardware = data_parsed["hardware"]
    value = float(data_parsed["value"])
    return control.toggle(hardware, value)

# @app.get('/logs/<id>')
# @warning_decorator
# @wrong_id
# def get_logs():
#     r"""
#     Return the last 10 logs generated in the control thread.
#     """
#     # return the last 10 logs
#     logs = control.logs()
#     logs["logs"] = logs["logs"][::-1][:10][::-1]
#     return json.dumps(logs).encode()


def list_options(category):
    """
    Return a list of str with the names of the classes that can be passed
    for a given category.
    """
    return [cls.__name__ for cls in ControlThread._option_dict[category]['possible_classes']]


@app.get('/choices/<category>/<id>')
@warning_decorator
@wrong_id
def list_choices(category):
    return list_options(category)


# Arguments to follow the command, adding video, etc options
parser = argparse.ArgumentParser(
    prog="IDOC - The Individual Drosophila Optogenetic Conditioner",
    description=(
        """
        A modular package to monitor and store the position of flies in separate chambers
        while running a preset paradigm of hardware events controlled by an Arduino board.
        A GUI is available by running the client.py script in the same computer.
        """
    ),
    epilog="Developed at the Liu Lab @ VIB-KU Leuven Center for Brain and Disease Research.",
    fromfile_prefix_chars='@', allow_abbrev=False
)

# General settings
parser.add_argument("-D", "--debug", action='store_true', dest="debug")


# Boolean flags
## Controller module
parser.add_argument(
    "--control", action='store_true', dest='control',
    help="Turn on controller module"
)
parser.add_argument(
    "--no-control", action='store_false', dest='control',
    help="Turn off controller module"
)

## Recognizer module
parser.add_argument(
    "--recognize", action='store_true', dest='recognize',
    help="Turn on recognizer module"
)

parser.add_argument(
    "--no-recognize", action='store_false', dest='recognize',
    help="Turn off recognizer module"
)
parser.add_argument(
    "--wrap", action='store_true', dest="wrap",
    help="If pasased a video, play it in a loop. Useful for debugging"
)
parser.add_argument(
    "--no-wrap", action='store_false', dest="wrap",
    help="If pasased a video, DO NOT play it in a loop. Useful for analysis"
)

parser.add_argument(
    "--use-wall-clock", action='store_true', dest='use_wall_clock',
    help="""
    Default. If passed, the time is computed using the output of time.time()
    """
)
parser.add_argument(
    "--no-use-wall-clock", action='store_false', dest='use_wall_clock',
    help="""
    If passed, the time is computed using the CAP_PROP_POS_MSEC property
    of the OpenCV capture class. This is only compatible with the
    OpenCV camera and when analyzing a video offline.
    """
)

# # Module settings
parser.add_argument(
    "-m", "--mapping-path", type=str, dest="mapping_path",
    help="Absolute path to csv providing pin number-pin name mapping"
)
parser.add_argument(
    "--paradigm-path", type=str, dest="paradigm_path",
    help="Absolute path to csv providing the Arduino top level paradigm"
)

parser.add_argument(
    "--arduino_port", type=str,
    help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows"
)

parser.add_argument(
    "-f", "--framerate", type=int,
    help="Frames per second in the opened stream, overrides config."
)
parser.add_argument(
    "-v", "--video-path", type=str, dest='video_path',
    help=
    """
    If offline tracking is desired, location of the input video file.
    Only possible if OpenCVCamera class is passed in --camera.
    """
)


parser.add_argument(
    "-a", "--adaptation-time", type=int, dest="adaptation_time",
    help=
    """
    Number of seconds to wait before starting paradigm and saving tracking data
    from the moment this script is started. If not provided, it is taken from config.
    """
)

parser.add_argument(
    "-d", "--duration", type=int, dest="max_duration",
    help=
    """
    Maximum number of seconds the software will run. If not provided, it is taken from config.
    """
)

parser.add_argument(
    "--run", action='store_true', dest='run',
    help="Batch run"
)
parser.add_argument(
    "--no-run", action='store_false', dest='run',
    help="Batch run"
)

parser.add_argument(
    "--start-datetime", type=str, dest='start_datetime',
    help=""
)

# User input for classes
parser.add_argument("--board", type=str, choices=list_options("board"))
parser.add_argument("--camera", type=str, help="Stream source", choices=list_options("camera"))
parser.add_argument("--drawer", type=str, choices=list_options("drawer"))
parser.add_argument("--roi-builder", type=str, dest="roi_builder", choices=list_options("roi_builder"))
parser.add_argument("--result-writer", type=str, dest="result_writer", choices=list_options("result_writer"))
parser.add_argument("--tracker", type=str, choices=list_options("tracker"))


# General application module
parser.add_argument("-e", "--experimenter", type=str, help="Add name of the experimenter/operator")

# Bottle settings
parser.add_argument("-p", "--port", type=int)


parser.set_defaults(
    control=False, recognize=False,
    port=9000,
    arduino_port="/dev/ttyACM0",
    wrap=None,
    default=True,
    max_duration=None
)

config = IDOCConfiguration()
ARGS = vars(parser.parse_args())

machine_id = get_machine_id()
version = get_git_version()
RESULT_DIR = config.content["folders"]["results"]["path"]
PORT = ARGS.pop("port") or config.content["network"]["port"]
DEBUG = ARGS.pop("debug") or config.content["network"]["port"]

if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

logger.info("You have passed arguments:")
logger.info(ARGS)

control = ControlThread(
    machine_id=machine_id,
    version=version,
    result_dir=RESULT_DIR,
    user_data=ARGS,
)

def run(port):
    server = get_server(port)
    logger.info("Running bottle on server %s, port %d", server, port)
    bottle.run(app, host='0.0.0.0', port=port, debug=DEBUG, server=server)

server_thread = Thread(target=run, name="bottle", args=(PORT,))

def stop(signo=None, _frame=None):
    r"""
    A function to bind the arrival of specific signals to an action.
    """
    logger.debug("Received signal %s", signo)
    try:
        control.stop()
        logger.info('Quitting')
        os._exit(0) # pylint: disable=protected-access
        # sys.exit(0)
    except Exception as error:
        logger.warning(error)

    return


signals = ('TERM', 'HUP', 'INT')
for sig in signals:
    signal.signal(getattr(signal, 'SIG' + sig), stop)

def main():
    control.start()
    server_thread.start()
    control.join()
    # while not control.stopped:
    #     time.sleep(1)

    stop()

main()
