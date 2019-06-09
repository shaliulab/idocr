# Standard library imports
import glob
import logging
import os
import os.path
import datetime
from pathlib import Path

# Third party imports
import cv2
import pandas as pd


# Local application imports
from lmdt_utils import setup_logging
from decorators import if_record_event
from LeMDT import PROJECT_DIR

# Set up package configurations
setup_logging()

# https://stackoverflow.com/questions/16740887/how-to-handle-incoming-real-time-data-with-python-pandas/17056022
max_len = 1000


class Saver():

    def __init__(self, tracker, cache={}, record_event=None):


        self.cache = cache
        self.tracker = tracker
        self.log = logging.getLogger(__name__)
        self.lst = []
        self.record_event = record_event
        self.columns = [
            "frame", "arena", "cx", "cy", "datetime", "t", \
            "oct_left", "oct_right", "mch_left", "mch_right", \
            "eshock_left", "eshock_right"
            ]
        self.path = None
        self.output_dir = None
        self.store = None
        self.store_video = None
        self.store_img = None
        self.out = None

    def set_store(self, cfg):
        """
        Set the absolute path to the output file (without extension)
        """

        self.log.info("Setting the store path")
        
        
        self.path = cfg["saver"]["path"]
        record_start = self.tracker.interface.record_start.strftime("%Y-%m-%d_%H-%M-%S")
        
        
        self.output_dir = Path(PROJECT_DIR, self.path, record_start)
        filename = record_start+"_"+cfg["interface"]["machine_id"]
        self.store = Path(self.output_dir, filename)

        video_format = "mp4"
        self.store_video = self.store.as_posix() + "." + video_format
        self.store_video2 = self.store.as_posix() + "2." + ".avi"


        self.store_img = Path(self.output_dir, "frames")
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        fourcc2 = cv2.VideoWriter_fourcc(*'XVID')

        self.out = cv2.VideoWriter(self.store_video, fourcc, 2, (500, 500))
        self.out2 = cv2.VideoWriter(self.store_video2, fourcc, 2, (500, 500))

        self.log.info("Creating dirs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.store_img.mkdir(parents=True, exist_ok=False)


        return True



    def process_row(self, d, max_len=max_len):
        """
        Append row d to the store
    
        When the number of items in the cache reaches max_len,
        append the list of rows to the HDF5 store and clear the list.
    
        """
        
        if not self.tracker.interface.record_event.is_set():
            return True
        
        if len(self.lst) >= max_len:
            self.store_and_clear()
        if self.record_event.is_set():
            self.lst.append(d)
            self.log.debug("Adding new datapoint to cache")      

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
           
        self.log.info("Saving cache to {}".format(self.store.as_posix()))

        # save to csv
        with open(self.store.as_posix() + ".csv", 'a') as store:
            df.to_csv(store)


        # try saving to hdf5
        # try:
        #     with pd.HDFStore(self.store + ".h5") as store:
        #         store.append(key, df)
        # except Exception as e:
        #     self.log.info(key)
        #     self.log.error("{} could not save cache to h5 file. Please investigate traceback. Is pytables available?".format(self.name))

        #     self.log.info(df)
        #     self.log.exception(e)

    def save_img(self, filename, frame):

        if not self.tracker.interface.record_event.is_set():
            return True

        full_path = Path(self.store_img, filename).as_posix()
        cv2.imwrite(full_path, frame)


    def images_to_video(self, clear_images=False):

        if not self.tracker.interface.record_event.is_set():
            return True
  
        image_list = glob.glob(f"{self.store_img.as_posix()}/*.jpg")
        sorted_images = sorted(image_list, key=os.path.getmtime)
        for file in sorted_images:
            print("Adding image")
            print(self.store_video)
            image_frame = cv2.imread(file)
            self.out.write(image_frame)
            self.out2.write(image_frame)
        if clear_images:
            for file in image_list:
                os.remove(file)




