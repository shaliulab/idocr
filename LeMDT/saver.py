# Standard library imports
import glob
import logging
import os
import os.path
import datetime
from pathlib import Path

# Third party imports
import cv2
import numpy
import pandas as pd
import subprocess
# from skvideo.io import VideoWriter

# Local application imports
from lmdt_utils import setup_logging
from decorators import if_record_event
from LeMDT import PROJECT_DIR
import threading

# Set up package configurations
setup_logging()

# https://stackoverflow.com/questions/16740887/how-to-handle-incoming-real-time-data-with-python-pandas/17056022
max_len = 50


class Saver():

    def __init__(self, tracker, cfg, cache={}, record_event=None):


        self.cache = cache
        self.tracker = tracker
        self.log = logging.getLogger(__name__)
        self.lst = []
        self.record_event = record_event
        self.columns = [
            "frame", "arena", "cx", "cy", "datetime", "t", \
            "ODOUR_A_LEFT", "ODOUR_A_RIGHT", "ODOUR_B_LEFT", "ODOUR_B_RIGHT", \
            "eshock_left", "eshock_right"
            ]
        self.path = None
        self.output_dir = None
        self.store = None
        self.store_video = None
        self.store_img = None
        self.out = None

        self.path = cfg["saver"]["path"]
        self.video_format = cfg["saver"]["video_format"]
        self.video_out_fps = cfg["saver"]["fps"]
        print(type(self.video_out_fps))
        print(self.video_out_fps)
        
        self.machine_id = cfg["interface"]["machine_id"]
        self.t = None

    def init_record_start(self):
        """
        Set absolute paths to output (depend on what time the record button is pressed)
        and create directory structure if needed.
        """
        record_start_formatted = self.tracker.interface.record_start.strftime("%Y-%m-%d_%H-%M-%S")
        filename = record_start_formatted + "_" + self.machine_id
        self.output_dir = Path(PROJECT_DIR, self.path, record_start_formatted)
        self.store = Path(self.output_dir, filename)
        self.store_video = self.store.as_posix()
        self.store_img = Path(self.output_dir, "frames")
        self.log.info("Creating output directory structures")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.store_img.mkdir(parents=True, exist_ok=False)

    def init_output_files(self):
        """Initialize csv and avi files."""
        video_out_fourcc = ['H264', 'XVID', 'MJPG', 'DIVX', 'FMP4', 'MP4V']
        vifc = video_out_fourcc[3]
        self.output_video_shape = (1000, 1000)
        self.video_writers = [
            cv2.VideoWriter(
                self.store_video + suffix + self.video_format,
                cv2.VideoWriter_fourcc(*vifc),
                self.video_out_fps, self.output_video_shape
            ) for suffix in ["_original.", "_annotated."]]


        store_header = pd.DataFrame(columns=self.columns)
        with open(self.store.as_posix() + ".csv", 'w') as store:
            store_header.to_csv(store)

        return True

    def save_paradigm(self):
        """Save a copy of the paradigm for future reference"""
        self.tracker.interface.device.paradigm.to_csv(os.path.join(self.output_dir, "paradigm.csv"), header=True)


    @if_record_event
    def process_row(self, d, max_len=max_len):
        """
        Append row d to the store
    
        When the number of items in the cache reaches max_len,
        append the list of rows to the HDF5 store and clear the list.
    
        """
        
        # if not self.tracker.interface.record_event.is_set():
        #     return True
        
        if len(self.lst) >= max_len:
            self.store_and_clear()
        if self.record_event.is_set():
            self.lst.append(d)
            self.log.debug("Adding new datapoint to cache")      

    @if_record_event
    def store_and_clear(self):
        """
        Convert the cache list to a DataFrame and append that to HDF5.
        """
        
        if not self.tracker.interface.record_event.is_set():
            return True

        try:
            df = pd.DataFrame.from_records(self.lst)[self.columns]
        
        except KeyError as e:
            self.log.info("No data was collected. Did you press the record button?")
            return 1
        except Exception as e:
            self.log.error('There was an error saving the data')
            print(self.lst)
            self.log.exception(e)
            return 0 
        else:
            self.lst.clear()


        # check the dataframe is not empty
        # could be empty if user closes before recording anything
           
        self.log.debug("Saving cache to {}".format(self.store.as_posix()))

        # save to csv
        with open(self.store.as_posix() + ".csv", 'a') as store:
            df.to_csv(store, header=False)

    @if_record_event
    def save_img(self, filename, frame):

        # if not self.tracker.interface.record_event.is_set():
            # return True

        full_path = Path(self.store_img, filename).as_posix()
        cv2.imwrite(full_path, frame)

    @if_record_event
    def save_video(self):

        # if not self.tracker.interface.record_event.is_set():
            # return True

        # self.video_writer.open()
        # print(self.tracker.interface.original_frame)

        # self.video_writer.write(self.tracker.interface.original_frame)
        # self.video_writer.release()
        imgs = [cv2.cvtColor(self.tracker.interface.original_frame, cv2.COLOR_GRAY2BGR), self.tracker.interface.frame_color]

        for img, vw in zip(imgs, self.video_writers):
            saved_frame = cv2.resize(img, self.output_video_shape)
            vw.write(saved_frame)

    @if_record_event
    def stop_video(self):
        [vw.release() for vw in self.video_writers]

    def refresh_trace_plot(self):
        print('Calling rscript')
        self.t = threading.Thread(target=self.plot, name='trace_plot')
        self.t.setDaemon(False)
        self.t.run()
        print('Finished calling rscript')

    def plot(self):
        print(self.output_dir)
        print(os.path.join(PROJECT_DIR, "Rscripts/main.R")) 

        subprocess.call([os.path.join(PROJECT_DIR, "Rscripts/main.R"), "-e", self.output_dir])
        # p <- LeMDTr::preprocess_and_plot(experiment_folder = opt$experiment_folder)
        # output_plot_path <- file.path(opt$experiment_folder, "trace_plot.png")
        # ggplot2::ggsave(filename = output_plot_path, plot = p)
