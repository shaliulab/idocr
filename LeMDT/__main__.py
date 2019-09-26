############################
### Main callable script
############################

import argparse
import logging
import coloredlogs
import sys
from pathlib import Path
from .lmdt_utils import setup_logging
from .interface import Interface
from . import PROJECT_DIR

# Arguments to follow the command, adding video, etc options
ap = argparse.ArgumentParser()
ap.add_argument("-a", "--arduino", action = 'store_true',                 help="Shall I run Arduino?")
ap.add_argument("-c", "--camera", type = str, default = "webcam", choices = ["webcam", "pylon"], help="Stream source")
ap.add_argument("--config", default = Path(PROJECT_DIR, 'config.yaml').__str__(), type = str, help="Path to config.yaml file")
ap.add_argument("-d", "--duration", type = float, default = 200,          help="How long should it last? (minutes)")
ap.add_argument("-e", "--experimenter", type = str, default="Sayed",      help="Add name of the experimenter/operator")
ap.add_argument("-f", "--fps", type = int, help="Frames per second in the opened stream. Default as stated in the __init__ method in Tracker, is set to 2")
ap.add_argument("-g", "--gui_name",       type = str,  choices=['opencv', 'tkinter', 'cli'], help="tkinter/opencv")
ap.add_argument("-l", "--log_dir",  type = str, default = ".",            help="Absolute path to directory where log files will be stored")
ap.add_argument("-o", "--output_path",  type = str, default = ".",            help="Absolute path to directory where output files will be stored")
ap.add_argument("-m", "--mapping", type = str,                            help="Absolute path to csv providing pin number-pin name mapping", )
ap.add_argument("-p", "--port",     type = str, default = "/dev/ttyACM0", help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows")
ap.add_argument("--program", type = str,                                  help="Absolute path to csv providing the Arduino top level program")
ap.add_argument("-r", "--reporting", action = 'store_true')
ap.add_argument("-t", "--track", action = 'store_true',                   help="Shall I track flies?")
ap.add_argument("-u", "--time",     type = str, default = "m",            help="Time unit to be used")
ap.add_argument("-v", "--video",    type = str, default = None,           help="location to the video file")
args = vars(ap.parse_args())

DURATION = args["duration"] * 60
coloredlogs.install()

# Set up general settings

#print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
#print('FPS is: {}'.format(int(cap.get(5))))

setup_logging()
log = logging.getLogger(__name__)

interface = Interface(
    arduino = args["arduino"], track = args["track"],
    mapping_path = args["mapping"], program_path = args["program"], port = args["port"],
    camera = args["camera"], video = args["video"], config = args["config"],
    reporting = args["reporting"], output_path = args["output_path"],
    duration = DURATION, gui_name = args["gui_name"]
)

interface.start()
