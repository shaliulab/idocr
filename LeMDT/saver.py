# Standard library imports
import logging
import os.path
import datetime
from pathlib import Path

# Third party imports
import pandas as pd

# Local application imports
from lmdt_utils import setup_logging
from LeMDT import PROJECT_DIR
# Set up package configurations
setup_logging()

# https://stackoverflow.com/questions/16740887/how-to-handle-incoming-real-time-data-with-python-pandas/17056022
max_len = 1000


class Saver():

    def __init__(self, cache = {}, init_time = None, record_event = None):


        self.init_time = None
        self.cache = cache
        self.init_time = init_time
        
        self.log = logging.getLogger(__name__)
        self.lst = []
        self.record_event = record_event
        self.columns = [
            "frame", "arena", "cx", "cy", "datetime", "t", \
            "oct_left", "oct_right", "mch_left", "mch_right", \
            "eshock_left", "eshock_right"
            ]

    def set_store(self, cfg):
        """
        Set the absolute path to the output file (without extension)
        """
        now = self.init_time.strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = Path(PROJECT_DIR, cfg["saver"]["path"], now)
        filename = now+"_"+cfg["interface"]["machine_id"]
        self.store = Path(output_dir, filename).__str__()
        # create the directory structure, if it does not exist yet
        output_dir.mkdir(parents=True, exist_ok=True) 



        
    def process_row(self, d, max_len = max_len):
        """
        Append row d to the store
    
        When the number of items in the cache reaches max_len,
        append the list of rows to the HDF5 store and clear the list.
    
        """
        
        if len(self.lst) >= max_len:
            self.store_and_clear()
        if self.record_event.is_set():
            self.lst.append(d)
            self.log.debug("Adding new datapoint to cache")      


    def store_and_clear(self):
        """
        Convert the cache list to a DataFrame and append that to HDF5.
        """
        try:
            df = pd.DataFrame.from_records(self.lst)[self.columns]
        except Exception as e:
            self.log.error('There was an error saving the data')
            print(self.lst)
            self.log.error(e)
            return 0 
        else:
            self.lst.clear()


        # check the dataframe is not empty
        # could be empty if user closes before recording anything
           
        self.log.info("Saving cache to {}".format(self.store))

        # save to csv
        with open(self.store + ".csv", 'a') as store:
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
            


