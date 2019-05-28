# Standard library imports
import logging
import os.path
import datetime

# Third party imports
import pandas as pd

# Local application imports
from lmdt_utils import setup_logging

# Set up package configurations
setup_logging()

# https://stackoverflow.com/questions/16740887/how-to-handle-incoming-real-time-data-with-python-pandas/17056022
max_len = 5000


class Saver():

    def __init__(self, store="store", cache = {}, init_time = None, name = None, record_event = None):


        self.store = None
        self.cache = None
        self.name = None
        self.init_time = None
        self.cache = cache
        self.name = name
        self.init_time = init_time
        self.store = "{}_{}".format(store, init_time.strftime("%Y%m%d-%H%M%S"))
        self.log = logging.getLogger(__name__)
        self.lst = []
        self.record_event = record_event
        
    def process_row(self, d, key, max_len = 5):
        """
        Append row d to the store 'key'.
    
        When the number of items in the key's cache reaches max_len,
        append the list of rows to the HDF5 store and clear the list.
    
        """
        # keep the rows for each key separate.
        # lst = self.cache.setdefault(key, [])
        
        if len(self.lst) >= max_len:
            self.store_and_clear(self.lst, key)
        if self.record_event.is_set():
            self.lst.append(d)
            self.log.debug("Adding new datapoint to cache")      


    def store_and_clear(self, lst, key):
        """
        Convert key's cache list to a DataFrame and append that to HDF5.
        """
        try:
            df = pd.DataFrame(lst)
        except Exception as e:
            self.log.error('There was an error saving the {}'.format(key))
            print(lst)
            self.log.error(e) 

        # check the dataframe is not empty
        # could be empty if user closes before recording anything
           
        self.log.info("Saving cache to {}".format(self.store))

        # try saving to hdf5
        try:
            with pd.HDFStore(self.store + ".h5") as store:
                store.append(key, df)
        except Exception as e:
            self.log.info(key)
            self.log.error("{} could not save cache to h5 file. Please investigate traceback. Is pytables available?".format(self.name))

            self.log.info(df)
            self.log.exception(e)
            
        # save to csv
        with open(self.store + ".csv", 'a') as store:
            df.to_csv(store)

        lst.clear()
