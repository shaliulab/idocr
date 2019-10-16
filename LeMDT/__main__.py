############################
### Main callable script
############################

import argparse
import logging
import coloredlogs
import sys
from pathlib import Path
from .interface import Interface
from . import PROJECT_DIR

# Arguments to follow the command, adding video, etc options
ap = argparse.ArgumentParser()
ap.add_argument("--arduino", action = 'store_true', dest = 'arduino', help="Shall I run Arduino?")
ap.add_argument("--no-arduino", action = 'store_false', dest = 'arduino')
ap.add_argument("--track", action = 'store_true', dest = 'track' ,  help="Shall I track flies?")
ap.add_argument("--no-track", action = 'store_false', dest = 'track', help="Shall I track flies?")
ap.add_argument("-r", "--reporting", action = 'store_true')


ap.add_argument("-c", "--camera",      type = str, help="Stream source", choices = ["webcam", "pylon"], default = 'pylon')
ap.add_argument("--config",            type = str, help="Path to config.yaml file")
ap.add_argument("-e", "--experimenter",type = str, help="Add name of the experimenter/operator")
ap.add_argument("-f", "--fps",         type = int, help="Frames per second in the opened stream. Default as stated in the __init__ method in Tracker, is set to 2")
ap.add_argument("-g", "--gui_name",    type = str, help="tkinter/opencv", choices=['opencv', 'tkinter', 'cli'])
ap.add_argument("-l", "--log_dir",     type = str, help="Absolute path to directory where log files will be stored")
ap.add_argument("-o", "--output_path", type = str, help="Absolute path to directory where output files will be stored")
ap.add_argument("-m", "--mapping",     type = str, help="Absolute path to csv providing pin number-pin name mapping", )
ap.add_argument("-p", "--port",        type = str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows")
ap.add_argument("--program",           type = str, help="Absolute path to csv providing the Arduino top level program")
ap.add_argument("-u", "--time",        type = str, help="Time unit to be used",  default = "m")
ap.add_argument("-v", "--video",       type = str, help="location to the video file", default = None)
ap.set_defaults(
    arduino=True, track=True, config=Path(PROJECT_DIR, 'config.yaml').__str__(), output_path="lemdt_results",
    gui_name = 'cli', log_dir = '.', port="/dev/ttyACM0", camera = 'pylon', experimenter="Sayed"

)

args = vars(ap.parse_args())

#print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
#print('FPS is: {}'.format(int(cap.get(5))))

interface = Interface(
    arduino = args["arduino"], track = args["track"],
    mapping_path = args["mapping"], program_path = args["program"], port = args["port"],
    camera = args["camera"], video = args["video"], config_file = args["config"],
    reporting = args["reporting"], output_path = args["output_path"],
    # duration = DURATION,
    gui_name = args["gui_name"]
)

interface.start()
