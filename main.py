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
from Camera.live_tracking_analyzing import Tracker
from Arduino.learning_memory import LearningMemoryDevice

# Arguments to follow the command, adding video, etc options
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--port",     type = str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows")
ap.add_argument("-m", "--mappings", type = str, help="Absolute path to csv providing pin number-pin name mappings")
ap.add_argument("-s", "--sequence", type = str, help="Absolute path to csv providing the sequence of instructions to be sent to Arduino")
ap.add_argument("-l", "--log_dir",  type = str, help="Absolute path to directory where log files will be stored")
ap.add_argument("-v", "--video",    type = str, help="location to the video file", default = "Camera/outpy04.avi")
ap.add_argument("-d", "--duration", type = str, help="How long should it last?", default = 1200)
ap.add_argument("-t", "--time",     type = str, help="Time unit to be used", default = "m")
ap.add_argument("-a", "--author",   type = str, help="Add name of the operator", default="Sayed")
args = vars(ap.parse_args())

exit = threading.Event()

# Define tf as a time factor to scale time units to seconds or minutes
# according to user input

tu = args["time"]
try:
  assert(tu != "m" or tu != "s")
except AssertionError as error:
    print("Please enter a valid time unit: accepted m (minutes) or s (seconds)")
    exit(1)

tf = np.where(tu == "m", 60, 1)


# Setup Arduino controls
##########################
total_time = 30
mapping=pd.read_csv(args["mappings"])
program=pd.read_csv(args["sequence"], skip_blank_lines=True)
device = LearningMemoryDevice(mapping, program, args["port"], args["log_dir"])


# Set up general settings

#print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
#print('FPS is: {}'.format(int(cap.get(5))))

tracker = Tracker(author=args["author"], duration=args["duration"], video=args["video"], tf=tf)
#input_totaltime = input("Do you want to start tracking now? (y/n)")
#if input_totaltime in ['Y', 'yes', 'y', 'Yes', 'YES', 'OK']:

device.off()
daemons = device.prepare()
device.run(total_time=total_time, daemons=daemons)
tracker.track()
device.total_off()
