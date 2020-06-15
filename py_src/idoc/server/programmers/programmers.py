r"""
Inform the user of the different paradigm.csv available,
load one of them into memory,
generate the parallel threads required to implement it in practice
"""

from collections import Counter
import logging
from itertools import compress
import os.path
from threading import Barrier
import traceback

import numpy as np
import pandas as pd

from idoc.server.core.base import Root, Settings
from idoc.configuration import IDOCConfiguration
from idoc.debug import IDOCException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Programmer(Settings, Root):
    r"""
    Load user paradigms and prepare threads for concurrent control of an Arduino or Dummy board
    """

    table = None
    _paradigms_dir = None
    _required_columns = ["hardware", "start", "end", "on", "off", "mode", "value"]

    def __init__(
            self, *args, **kwargs
        ):

        super().__init__(*args, **kwargs)

        self._paradigms_dir = self._config.content["folders"]["paradigms"]["path"]
        self._barriers = {}
        self.table = []
        self._submodules = {}
        self._settings.update({
            'paradigm_path': None,
        })
        self._locked = False

    def list(self, dict_format=True):
        r"""
        Fetch a list of the paradigms available in the paradigm directory
        set in the config file
        This information is designed to be sent to the user.
        """
        files = os.listdir(self._paradigms_dir)

        if dict_format:
            return {i: f for i, f in enumerate(files) if f[::-1][:4][::-1] == ".csv"}
        else:
            return files

    @property
    def paradigm_name(self):
        return self._settings["paradigm_path"]

    @property
    def paradigm_path(self):
        if self._settings['paradigm_path'] is None:
            return None
        else:
            return os.path.join(self._paradigms_dir, self._settings["paradigm_path"])

    @paradigm_path.setter
    def paradigm_path(self, paradigm_path):
        r"""
        Load the user provided paradigm in csv format into Python
        and prepare the corresponding threads so the Controller
        can run them.
        """
        # load the data in paradigm_path into Python
        self._settings['paradigm_path'] = paradigm_path

        if not self._load_table(paradigm_path):
            self._settings['paradigm_path'] = self._config.content['controller']['paradigm_path']
            raise IDOCException('The provided paradigm could not be loaded. See more details below')


    @property
    def absolute_paradigm_path(self):
        if self._settings["paradigm_path"] is None:
            return None

        absolute_path = os.path.join(self._paradigms_dir, self._settings["paradigm_path"])
        if os.path.exists(absolute_path) and os.path.isfile(absolute_path):
            pass
        else:
            logger.warning('The passed paradigm does not exist. Check it is correct!!:')
            logger.warning(absolute_path)

        return absolute_path

    def _validate_paradigm_df(self, df):
        """
        Check the data frame provided in the paradigm_path .csv file
        fulfills the IDOC requirements

        * It should contain the columns in self._required_columns
        """
        # TODO Add more checks

        missing_columns = []
        for column in self._required_columns:
            if column not in df.columns:
                missing_columns.append(column)

        if len(missing_columns) != 0:
            logger.warning("%s are missing in the paradigm. Please add them", ' '.join(missing_columns))
            return False

        return True

    def _validate_paradigm_path(self, paradigm_path):
        """
        Check the paradigm path is valid. It should:

        * Not be None
        * Be within the list of available paradigms
        """
        if paradigm_path is None:

            self.table = None
            return False

        elif paradigm_path not in self.list(dict_format=False):
            self.table = None
            logger.warning("The passed paradigm does not exist!")
            return False

        else:
            return True

    def _load_table(self, paradigm_path):
        """
        Load a csv into python in list format
        Each row becomes a dictionary inside the list
        and the columns and their values are encoded
        as key-value pairs of the dictionary.
        """

        # make sure the old table is reset, if populated at all
        self.table.clear()

        # series of checks to make sure the provided paradigm is valid
        if not self._validate_paradigm_path(paradigm_path):
            logger.warning("Error reading your paradigm into IDOC. Paradigm path is invalid")
            return False

        table_df = pd.read_csv(self.absolute_paradigm_path, comment='#')
        if not self._validate_paradigm_df(table_df):
            logger.warning("Error reading your paradigm into IDOC. Paradigm is invalid")
            return False


        # convert on and off from ms to seconds
        # we assume the user enters this in ms because its more convenient for him/her
        table_df["start"] *= 60
        table_df["end"] *= 60
        table_df["on"] /= 1000
        table_df["off"] /= 1000

        i = 0
        # coerce to a dictionary
        for row_tuple in table_df.iterrows():
            row = row_tuple[1].to_dict()
            self.table.append(row)
            i += 1

        if self.table == []:
            logger.warning("Error reading your paradigm into IDOC. Table is empty")
            return False

        return True

    @staticmethod
    def parse(row, i):
        """
        Process the content of the row inside prepare() and return a
        kwargs dictionary that can be unpacked upon BaseControllerThead
        initializations.
        """

        kwargs = {
            "i": str(i).zfill(3),
            "hardware": row['hardware'],
            "start": row["start"],
            "end": row["end"],
            "value": float(row['value']),
            "mode": row['mode']
        }

        # Decide here which thread to use
        # Either a thread that leaves the pin on constitutively
        if np.isnan(row['on']) and np.isnan(row['off']):
            thread = "DEFAULT"

        # or a thread that implements a duty cycle with some frequency
        # and phase given by on and off
        elif not np.isnan(row['on']) and not np.isnan(row['off']):
            thread = "WAVE"
            kwargs["seconds_on"] = row["on"]
            kwargs["seconds_off"] = row["off"]

        else:
            raise IDOCException('Row %d: one of on or off is defined, but not both. Please fix this' % i)

        return thread, kwargs

    @staticmethod
    def make_barriers(table):
        r"""
        Generate barriers for perfect on-off alternation between threads
        using the start and stop times of the threads in the paradigm
        Make them so there is one and only one for every timepoint
        where at least one thread either stops or starts
        The barrier will expect as many threads
        as the sum of starting and stopping threads
        The threads are given a start and a stop barrier
        which is given so its shared across threads
        with equal endpoint (sharing the end barrier)
        or starting right after (the end barrier is the same as the start barrier of those).
        """

        barriers = {}

        switch_times = {
            "start": Counter([e["start"] for e in table]),
            "end": Counter([e["end"] for e in table]),
            "total": Counter([v[e] for e in ["start", "end"] for v in table])
        }

        barriers = {k: Barrier(v) for k, v in switch_times["total"].items()}

        for switch_time in barriers:
            logger.debug(
                "Barrier at time %d with id %s will wait for %d parties",
                switch_time,
                id(barriers[switch_time]),
                barriers[switch_time].parties
            )

        return barriers

    @staticmethod
    def add_barriers(paradigm, barriers):
        r"""
        Add the barriers to the threads in the right position.
        """

        # provide the threads with barriers for improved synchronization
        # at the expense of slightly increased waiting times
        for thread in paradigm:

            start_barrier = barriers[thread.start_seconds]
            thread.add_barrier(start_barrier, "start")

            end_barrier = barriers[thread.end_seconds]
            thread.add_barrier(end_barrier, "end")

        return paradigm

    def lock(self):
        self._locked = True
