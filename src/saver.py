# Standard library imports
import logging
import os.path
import datetime

# Third party imports
import pandas as pd

# Local application imports
from frets_utils import setup_logging

# Set up package configurations
setup_logging()

# https://stackoverflow.com/questions/16740887/how-to-handle-incoming-real-time-data-with-python-pandas/17056022
CACHE = {}
STORE = 'store'   # Note: another option is to keep the actual file open
max_len = 5000


class Saver():

    def __init__(self, store=STORE, cache = CACHE, init_time = None, name = None):


        self.store = None
        self.cache = None
        self.name = None
        self.init_time = None
        self.cache = cache
        self.name = name
        self.init_time = init_time
        self.store = "{}_{}".format(store, init_time.strftime("%H%M%S-%d%m%Y"))
        self.log = logging.getLogger(__name__)
        
    def process_row(self, d, key, max_len = 5000):
        """
        Append row d to the store 'key'.
    
        When the number of items in the key's cache reaches max_len,
        append the list of rows to the HDF5 store and clear the list.
    
        """
        # keep the rows for each key separate.
        lst = self.cache.setdefault(key, [])
        if len(lst) >= max_len:
            self.store_and_clear(lst, key)
        lst.append(d)
        self.log.debug("Adding new datapoint to cache")
    
    def store_and_clear(self, lst, key):
        """
        Convert key's cache list to a DataFrame and append that to HDF5.
        """
        self.log.info("Cleaning cache")
        df = pd.DataFrame(lst)

        # try saving to hdf5
        try:
            with pd.HDFStore(self.store + ".h5") as store:
                store.append(key, df)
        except Exception as e:
            self.log.info(key)
            import ipdb; ipdb.set_trace()
            self.log.error("{} could not save cache to h5 file. Please investigate traceback".format(self.name))
            self.log.exception(e)
            
        # save to csv
        with open(self.store + ".csv", 'a') as store:
            df.to_csv(store)

        lst.clear()
