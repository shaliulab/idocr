r"""
Inform the user of the different program.csv available,
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

from learnmem.server.core.base import Root, Settings
from learnmem.server.controllers.threads import DefaultArduinoThread, WaveArduinoThread
from learnmem.server.controllers.threads import DefaultDummyThread, WaveDummyThread
from learnmem.configuration import LearnMemConfiguration

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
config = LearnMemConfiguration()


THREADS = {
    "ArduinoDummy": {"default": DefaultDummyThread, "wave": WaveDummyThread},
    "ArduinoX": {"default": DefaultArduinoThread, "wave": WaveArduinoThread}
    }


class Programmer(Settings, Root):
    r"""
    Load user programs and prepare threads for concurrent control of an Arduino or Dummy board
    """

    table = None
    _programs_dir = None

    def __init__(self, board, pin_state, sampling_rate, mapping, program_path, *args, **kwargs): # pylint: disable=line-too-long

        super().__init__(*args, **kwargs)

        self._programs_dir = config.content["folders"]["programs"]["path"]
        self._board = board
        self._sampling_rate = sampling_rate
        self._mapping = mapping
        self.pin_state = pin_state
        self._barriers = {}
        self._program = []
        self._submodules = {}
        self._settings = {'program_path': None}

        if self._mapping is not None:
            self._settings['program_path'] = program_path


    def list(self, dict_format=True):
        r"""
        Fetch a list of the programs available in the program directory
        set in the config file
        This information is designed to be sent to the user.
        """
        files = os.listdir(self._programs_dir)

        if dict_format:
            return {i: f for i, f in enumerate(files) if f[::-1][:4][::-1] == ".csv"}
        else:
            return files


    @property
    def program(self):
        return self._program

    @property
    def loaded(self):
        return self.ready

    @loaded.setter
    def loaded(self, value):
        if value is True:
            self.ready = True

    @property
    def program_path(self):
        if self._settings['program_path'] is None:
            return None
        else:
            return os.path.join(self._programs_dir, self._settings["program_path"])

    @program_path.setter
    def program_path(self, program_path):
        r"""
        Load the user provided program in csv format into Python
        and prepare the corresponding threads so the Controller
        can run them.
        """

        if program_path is None:
            return

        self._settings['program_path'] = program_path

        # load the data in program_path into Python

        try:
            self._load_table(program_path)
        except Exception as error:
            logger.warning("Error reading your program into IDOC")
            logger.debug(error)
            logger.debug(traceback.print_exc())
            return

        if self.table is None:
            logger.warning("Error reading your program into IDOC")
            return

        # actually generate the threads that this program dictates
        try:
            self._prepare()
        except Exception as error:
            logger.warning("Error loading your program into IDOC")
            logger.debug(error)
            logger.debug(traceback.print_exc())
            return

        self.loaded = True

    @property
    def absolute_program_path(self):
        if self._settings["program_path"] is None:
            return None

        return os.path.join(self._programs_dir, self._settings["program_path"])


    def _load_table(self, program_path):
        r"""
        Load a csv into python in list format
        Each row becomes a dictionary inside the list
        and the columns and their values are encoded
        as key-value pairs of the dictionary.
        """

        if program_path is None:

            self.table = None
            self._program = None
            return

        elif program_path not in self.list(dict_format=False):
            self.table = None
            self._program = None
            logger.warning("The passed program does not exist!")
            return


        table_df = pd.read_csv(self.absolute_program_path)
        required_columns = ["start", "end", "on", "off"]
        missing_index = [not e in table_df.columns for e in required_columns]

        missing_columns = list(compress(required_columns, missing_index))
        synonym_available = sum([e in table_df.columns for e in ["hardware", "pin_id"]])

        if len(missing_columns) != 0:
            logger.warning("Provided program is not valid. Please provide columns %s", ' '.join(missing_columns))
            return

        if synonym_available != 1:
            logger.warning("Please provide a column called hardware on your program")
            return

        if synonym_available == 2:
            table_df.drop(["pin_id"], index=1)

        table = []
        for row_tuple in table_df.iterrows():
            row = row_tuple[1].to_dict()
            row["start"] *= 60 # convert user input to seconds
            row["end"] *= 60 # convert user input to seconds
            table.append(row)

        self.table = table
        logger.debug(self.table)


    def _parse(self, row, i):
        r"""
        Process the content of the row inside prepare() and return a
        kwargs dictionary that can be unpacked upon BaseControllerThead
        initializations.
        """

        # XOR (signals invalid user input in the loaded program)
        if np.isnan(row['on']) ^ np.isnan(row['off']):
            logger.warning(
                "Row number %d in program %s is malformed",
                i+1, self._settings['program_path']
            )
            logger.warning("You have defined either on or off but not the other")
            logger.warning("Ignoring row")
            return {}


        kwargs = {
            "start": row["start"], "end": row["end"],
            "board": self._board,
            "sampling_rate": self._sampling_rate,
            "pin_state": self.pin_state
        }

        # get the hardware name
        try:
            # expect column with hardware name to be called hardware
            # but accept pin_id too
            hardware = row["hardware"]
        except KeyError:
            hardware = row["pin_id"]
            logger.debug(hardware)
        finally:
            # handle US-UK spelling
            hardware = hardware.replace("ODOUR", "ODOR").ljust(16)

        # get the pin number from the mapping using the hardware name
        try:
            pin_number = self._mapping[hardware]
        except KeyError:
            raise Exception("%s is not available in the mapping" % hardware)

        # get what value is needed (check for pwm configuration)
        # value is 1 by default.
        # If the user wishes to run a pwm cycle on a pin, it must be explicitly declared
        # in the config file, together with a fraction between 0 and 1
        if hardware in config.content["pwm"].keys():
            value = config.content["pwm"][hardware]
        else:
            value = 1

        # push these 3 values to kwargs
        kwargs.update({
            "hardware": hardware,
            "pin_number": pin_number,
            "value": value,
        })

        # check if on AND off times are NOT defined (is.nan)
        # in that case do nothing
        if np.isnan(row['on']) and np.isnan(row['off']):
            pass

        # otherwise add them (a XOR above was already checked above)
        else:
            kwargs.update({"seconds_on": row["on"], "seconds_off": row["off"]})

        return kwargs

    def _make_barriers(self):
        r"""
        Generate barriers for perfect on-off alternation between threads
        using the start and stop times of the threads in the program
        Make them so there is one and only one for every timepoint
        where at least one thread either stops or starts
        The barrier will expect as many threads
        as the sum of starting and stopping threads
        The threads are given a start and a stop barrier
        which is given so its shared across threads
        with equal endpoint (sharing the end barrier)
        or starting right after (the end barrier is the same as the start barrier of those).
        """

        self._barriers = {}

        switch_times = {
            "start": Counter([e["start"] for e in self.table]),
            "end": Counter([e["end"] for e in self.table]),
            "total": Counter([v[e] for e in ["start", "end"] for v in self.table])
        }

        logger.debug(switch_times)

        self._barriers = {k: Barrier(v) for k, v in switch_times["total"].items()}

        for swtich_time in self._barriers:
            logging.debug(
                "Barrier at time %d with id %s will wait for %d parties",
                swtich_time,
                id(self._barriers[swtich_time]),
                self._barriers[swtich_time].parties
            )

        return self._barriers


    def _add_barriers(self, program):
        r"""
        Add the barriers to the threads in the right position.
        """

        # provide the threads with barriers for improved synchronization
        # at the expense of slightly increased waiting times
        for thread in program:

            start_barrier = self._barriers[thread.start_seconds]
            thread.add_barrier(start_barrier, "start")

            end_barrier = self._barriers[thread.end_seconds]
            thread.add_barrier(end_barrier, "end")

    def _prepare(self):
        r"""
        Given a program_table, parse it
        to produce a program by storing instances of
        ControllerThread in the self._program list.
        A program is a list of ControllerThread instances
        """

        self._program = []

        for i, row in enumerate(self.table):

            kwargs = {"i": str(i).zfill(3)}
            kwargs.update(self._parse(row, i))
            logger.debug(kwargs)

            board_name = kwargs["board"].board_compatible

            if all([e in kwargs for e in ["seconds_on", "seconds_off"]]):
                ThreadClass = THREADS[board_name]["wave"] # pylint: disable=invalid-name
            else:
                ThreadClass = THREADS[board_name]["default"] # pylint: disable=invalid-name

            logger.debug("Selecting %s", ThreadClass.__name__)
            thread = ThreadClass(
                **kwargs
            )

            self._program.append(thread)

        self._make_barriers()
        self._add_barriers(self._program)
        logger.debug(self._program)
