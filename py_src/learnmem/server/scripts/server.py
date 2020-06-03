############################
### Main callable script
############################

import argparse
import json
import logging
import logging.handlers
import signal
from threading import Thread

import bottle
import coloredlogs
import urllib.parse

from learnmem.decorators import warning_decorator, error_decorator, wrong_id
from learnmem.server.core.control_thread import ControlThread
from learnmem.helpers import get_machine_id, get_git_version, get_server
from learnmem.configuration import LearnMemConfiguration

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
    settings_json = bottle.request.body.read() # pylint: disable=no-member
    settings = json.loads(settings_json)
    control.settings = settings
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


@app.post('/load_program/<id>')
@warning_decorator
@wrong_id
def load_program():
    r"""
    Update the hardware program loaded in IDOC.
    Do this by posting an object with key program_path
    and value the filename of one of the csv files in the
    programs_dir.
    programs_dir is defined in the config file under
    folders > programs > path.
    A list of the programs can be retrieved by GETting to /list_programs/.
    """
    post_data = bottle.request.body.read() # pylint: disable=no-member
    data_decoded = urllib.parse.parse_qs(post_data.decode())
    print(data_decoded)
    program_path = data_decoded["program_path"][0]
    control.load_program(program_path=program_path)
    return {"status": "success"}


@app.get('/list_programs/<id>')
@warning_decorator
@wrong_id
def list_programs():
    r"""
    Get a list of the available programs that the user
    can select via POSTing to /load_program.
    This is also available in info["controller"]["programs"].
    """
    return control.list_programs()

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

@app.get('/logs/<id>')
@warning_decorator
@wrong_id
def get_logs():
    r"""
    Return the last 10 logs generated in the control thread.
    """
    # return the last 10 logs
    logs = control.logs()
    logs["logs"] = logs["logs"][::-1][:10][::-1]
    return logs


# Arguments to follow the command, adding video, etc options
parser = argparse.ArgumentParser(
    prog="IDOC - The Individual Drosophila Optogenetic Conditioner",
    description="A modular package to monitor flies\
        while running a preset paradigm of hardware events controlled by an Arduino board."
)

# Control module
parser.add_argument(
    "--control", action='store_true', dest='control',
    help="Shall %(prog)s run Arduino?"
)
parser.add_argument("--no-control", action='store_false', dest='control')
parser.add_argument(
    "-m", "--mapping_path", type=str,
    help="Absolute path to csv providing pin number-pin name mapping"
)
parser.add_argument(
    "--program_path", type=str,
    help="Absolute path to csv providing the Arduino top level program"
)
parser.add_argument(
    "-b", "--board_name", type=str,
    help="Name of Arduino board in use", choices=["ArduinoUno", "ArduinoMega", "ArduinoDummy"]
)
parser.add_argument(
    "--arduino_port", type=str,
    help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows"
)

# Track module
parser.add_argument(
    "--recognize", action='store_true', dest='recognize',
    help="Shall %(prog)s track flies?"
)
parser.add_argument(
    "--no-recognize", action='store_false', dest='recognize',
    help="Shall %(prog)s track flies?"
)

parser.add_argument("-c", "--camera", type=str, help="Stream source", choices=["webcam", "pylon"])
parser.add_argument(
    "-f", "--framerate", type=int,
    help="Frames per second in the opened stream, overrides config."
)
parser.add_argument(
    "-v", "--video-path", type=str, dest='video_path',
    help="location to the video file"
)

# Save module
parser.add_argument(
    "--save", action='store_true', dest='save',
    help="Shall %(prog)s save the results? You can decide not to save later"
)
parser.add_argument(
    "--no-save", action='store_false', dest='save',
    help="Shall %(prog)s save the results? You can decide not to save later"
)
parser.add_argument(
    "-o", "--output_path", type=str,
    help="Absolute path to directory where output files will be stored"
    )

# General application module
parser.add_argument("-e", "--experimenter", type=str, help="Add name of the experimenter/operator")
parser.add_argument(
    "-l", "--log_dir", type=str,
    help="Absolute path to directory where log files will be stored"
)

parser.add_argument("-p", "--port", type=int)

parser.add_argument("-D", "--debug", action='store_true', dest="debug")



parser.set_defaults(
    # TODO Change output_path
    control=False, recognize=False, output_path="lemdt_results", save=True,
    log_dir='.', port=9000, arduino_port="/dev/ttyACM0", camera='pylon',
    experimenter="Sayed"
)

config = LearnMemConfiguration()
data = vars(parser.parse_args())

machine_id = get_machine_id()
version = get_git_version()
RESULT_DIR = config.content["folders"]["results"]["path"]
PORT = data.pop("port") or config.content["network"]["port"]

DEBUG = data.pop("debug") or config.content["network"]["port"]

if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)



control = ControlThread(
    machine_id=machine_id,
    version=version,
    result_dir=RESULT_DIR,
    experiment_data=data,
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
    logger.info("Received signal %s", signo)
    control.stop()
    # if 'cherrypy' in bottle.server_names:
    logger.info("Executing cherrypy server stop")
    bottle.server_names['cherrypy'].stop() # pylint: disable=no-member
    return


signals = ('TERM', 'HUP', 'INT')
for sig in signals:
    signal.signal(getattr(signal, 'SIG' + sig), stop)

def main():
    control.start()
    server_thread.start()

main()