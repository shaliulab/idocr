import cv2
import numpy as np
import matplotlib.pyplot as plt
import time
import argparse
import datetime
import sys
import pandas as pd
import glob
import os
import threading
import logging, logging.config, coloredlogs
import yaml

# Arguments to follow the command, adding video, etc options
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--port",     type = str, default = "/dev/ttyACM0", help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows")
ap.add_argument("-m", "--mappings", type = str,                           help="Absolute path to csv providing pin number-pin name mappings", )
ap.add_argument("-s", "--sequence", type = str,                           help="Absolute path to csv providing the sequence of instructions to be sent to Arduino")
ap.add_argument("-v", "--video",    type = str, default = None,           help="location to the video file")
ap.add_argument("-l", "--log_dir",  type = str, default = ".",            help="Absolute path to directory where log files will be stored")
ap.add_argument("-d", "--duration", type = int, default = 1200,           help="How long should it last?")
ap.add_argument("-u", "--time",     type = str, default = "m",            help="Time unit to be used")
ap.add_argument("-e", "--experimenter", type = str, default="Sayed", help="Add name of the experimenter/operator")
ap.add_argument("-a", "--arduino", action = 'store_true',        help="Shall I run Arduino?")
ap.add_argument("-t", "--track", action = 'store_true',          help="Shall I track flies?")
ap.add_argument("--verbose", action = 'store_true')
ap.add_argument("--gui", action = 'store_true')
ap.add_argument("-c", "--camera", type = str, default = "opencv", help="Stream source")
ap.add_argument("--config", type = str, default = "config.yml", help="Path to config file")
ap.add_argument("-f", "--fps", type = int, help="Frames per second in the opened stream. Default as stated in the __init__ method in Tracker, is set to 2")
args = vars(ap.parse_args())

total_time = args["duration"] * 60
coloredlogs.install()

# Set up general settings

#print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
#print('FPS is: {}'.format(int(cap.get(5))))

def setup_logging(
    default_path='logging.yaml',
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    """Setup logging configuration

    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

setup_logging()
log = logging.getLogger(__name__)

start_time = datetime.datetime.now()
log.info("Start time: {}".format(start_time.strftime("%H%M%S-%d%m%Y")))

if args["track"]:
    from src.camera.main import Tracker
    tracker = Tracker(camera = args["camera"], video = args["video"], config = args["config"], gui=args["gui"], start_time = start_time, total_time = total_time)
else:
    tracker = None

# Setup Arduino controls
##########################
if args["arduino"]:
    from src.arduino.main import LearningMemoryDevice

    device = LearningMemoryDevice(args["mappings"], args["sequence"], args["port"], communicate=args["verbose"], tracker = tracker, start_time = start_time)
    device.total_off(exit=False)
    threads = device.prepare()


#input_totaltime = input("Do you want to start tracking now? (y/n)")
#if input_totaltime in ['Y', 'yes', 'y', 'Yes', 'YES', 'OK']:

try:
    if args["arduino"]:
        device.run(total_time=total_time, threads=threads)

    if args["track"]:
        log.info("Starting tracking")
        _ = tracker.run(init=True)
except Exception as e:
    log.exception(e)

if not args["track"]:
    log.debug("Sleeping for the duration of the experiment. This makes sense if we are checking Arduino")
    time.sleep(total_time)
if args["arduino"]:
    log.info("Quitting arguino")
    device.quit()
