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
from src.frets_utils import setup_logging
from src.interface.main import Interface

# Arguments to follow the command, adding video, etc options
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--port",     type = str, default = "/dev/ttyACM0", help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows")
ap.add_argument("-m", "--mapping", type = str,                           help="Absolute path to csv providing pin number-pin name mapping", )
ap.add_argument("-s", "--sequence", type = str,                           help="Absolute path to csv providing the sequence of instructions to be sent to Arduino")
ap.add_argument("-v", "--video",    type = str, default = None,           help="location to the video file")
ap.add_argument("-l", "--log_dir",  type = str, default = ".",            help="Absolute path to directory where log files will be stored")
ap.add_argument("-d", "--duration", type = float, default = 200,          help="How long should it last? (minutes)")
ap.add_argument("-u", "--time",     type = str, default = "m",            help="Time unit to be used")
ap.add_argument("-e", "--experimenter", type = str, default="Sayed",      help="Add name of the experimenter/operator")
ap.add_argument("-a", "--arduino", action = 'store_true',                 help="Shall I run Arduino?")
ap.add_argument("-t", "--track", action = 'store_true',                   help="Shall I track flies?")
ap.add_argument("-r", "--reporting", action = 'store_true')
ap.add_argument("-g", "--gui",       type = str,  default = "tkinter", help="tkinter/opencv")
ap.add_argument("-c", "--camera", type = str, default = "opencv", help="Stream source")
ap.add_argument("--config", type = str, default = "config.yml", help="Path to config file")
ap.add_argument("-f", "--fps", type = int, help="Frames per second in the opened stream. Default as stated in the __init__ method in Tracker, is set to 2")
args = vars(ap.parse_args())

duration = args["duration"] * 60
coloredlogs.install()

# Set up general settings

#print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
#print('FPS is: {}'.format(int(cap.get(5))))

setup_logging()
log = logging.getLogger(__name__)


interface = Interface(arduino = args["arduino"], track = args["track"], reporting = args["reporting"], config = args["config"], gui = args["gui"])


if args["track"]:
    from src.camera.main import Tracker
    tracker = Tracker(interface = interface, camera = args["camera"], video = args["video"])
else:
    tracker = None

# Setup Arduino controls
##########################
if args["arduino"]:
    from src.arduino.main import LearningMemoryDevice

    device = LearningMemoryDevice(interface = interface, mapping = args["mapping"], program = args["sequence"], port = args["port"])
    device.power_off_arduino(exit=False)
    threads = device.prepare()
    if args["track"]:
        tracker.device = device


#input_totaltime = input("Do you want to start tracking now? (y/n)")
#if input_totaltime in ['Y', 'yes', 'y', 'Yes', 'YES', 'OK']:

try:
    if args["arduino"]:
        device.run(duration=duration, threads=threads)
        
    if args["track"]:
        log.info("Starting tracking")
        _ = tracker.run()

except Exception as e:
    log.exception(e)

if args["gui"]:
    interface.run()          


if not args["track"] and args["arduino"]:
    log.debug("Sleeping for the duration of the experiment. This makes sense if we are checking Arduino")

    interface.exit.wait(duration)

if args["arduino"]:
    log.info("Quitting arguino")
    interface.onClose()
