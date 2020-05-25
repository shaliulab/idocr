

from collections import Counter
import logging
import os.path
from threading import Barrier

import numpy as np
import pandas as pd

from learnmem.server.controllers.threads import DefaultArduinoThread, WaveArduinoThread, DefaultDummyThread, WaveDummyThread
from learnmem.configuration import LearnMemConfiguration

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
CFG = LearnMemConfiguration()


THREADS = {
    "ArduinoDummy": {"default": DefaultDummyThread, "wave": WaveDummyThread},
    "ArduinoX": {"default": DefaultArduinoThread, "wave": WaveArduinoThread}
    }


class Programmer:
    r"""
    Load user programs and prepare threads for concurrent control of an Arduino or Dummy board
    """

    table = None
    program = None
    _program_path = None
    _programs_dir = None

    def __init__(self, board, pin_state, sampling_rate, mapping, program_path=None):

        self._programs_dir = CFG.content["folders"]["programs"]["path"]
        self._board = board
        self._sampling_rate = sampling_rate
        self._mapping = mapping
        self.pin_state = pin_state
        self._barriers = {}

        if program_path is not None:
            self._program_path = program_path
            self.load(self._program_path)

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

    def load(self, program_path):
        r"""
        Load the user provided program in csv format into Python
        and prepare the corresponding threads so the Controller
        can run them.
        """
        # load the data in program_path into Python
        self.load_table(program_path)

        if self.table is None:
            return

        # actually generate the threads that this program dictates
        self.prepare()

    def load_table(self, program_path):
        r"""
        Load a csv into python in list format
        Each row becomes a dictionary inside the list
        and the columns and their values are encoded
        as key-value pairs of the dictionary.
        """

        if program_path is None:

            self.table = None
            self.program = None
            return

        elif program_path not in self.list(dict_format=False):
            self.table = None
            self.program = None
            logger.warning("The passed program does not exist!")
            return

        table_df = pd.read_csv(os.path.join(self._programs_dir, program_path))
        table = []
        for row in table_df.iterrows():

            r = row[1].to_dict()
            table.append(r)

        self.table = table
        logger.debug(self.table)


    def parse(self, row):
        r"""
        Process the content of the row inside prepare() and return a
        kwargs dictionary that can be unpacked upon BaseControllerThead
        initializations.
        """

        # XOR (signals invalid user input in the loaded program)
        if np.isnan(row['on']) ^ np.isnan(row['off']):
            logger.warning("Row number %d in program %s is malformed", i+1, self._program_path)
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
            logger.warning(hardware)
            raise Exception("The hardware passed is not available in the mapping")

        # get what value is needed (check for pwm configuration)
        # value is 1 by default.
        # If the user wishes to run a pwm cycle on a pin, it must be explicitly declared
        # in the config file, together with a fraction between 0 and 1
        if hardware in CFG.content["pwm"].keys():
            value = CFG.content["pwm"][hardware]
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
            kwargs.update({"on": row["on"], "off": row["off"]})

        return kwargs


    @property
    def barriers(self):
        self._barriers


    @barriers.getter
    def barriers(self):
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

        # should be called only once!
        if len(self._barriers) != 0:
            return self._barriers


        switch_times = {
            "start": Counter([e["start"] for e in self.table]),
            "end": Counter([e["end"] for e in self.table]),
            "total": Counter([v[e] for e in ["start", "end"] for v in self.table])
        }
        logger.warning(switch_times)

        self._barriers = {k: Barrier(v) for k, v in switch_times["total"].items()}

        for t in self._barriers:
            logging.warning(
                "Barrier at time %d with id %s will wait for %d parties",
                t, id(self._barriers[t]), self._barriers[t].parties
            )

        return self._barriers


    def add_barriers(self, program):
        r"""
        Add the barriers to the threads in the right position.
        """

        # provide the threads with barriers for improved synchronization
        # at the expense of slightly increased waiting times
        for thread in program:

            start_barrier = self.barriers[thread.start_time]
            thread.add_barrier(start_barrier, "start")

            end_barrier = self.barriers[thread.end_time]
            thread.add_barrier(end_barrier, "end")

    def prepare(self):
        r"""
        Given a program_table, parse it
        to produce a program by storing instances of
        ControllerThread in the self.program list.
        A program is a list of ControllerThread instances
        """

        self.program = []

        for i, row in enumerate(self.table):

            kwargs = {"i": str(i).zfill(3)}
            kwargs.update(self.parse(row))
            logger.debug(kwargs)

            board_name = kwargs["board"].board_compatible

            if all([e in kwargs for e in ["on", "off"]]):
                ThreadClass = THREADS[board_name]["wave"]
            else:
                ThreadClass = THREADS[board_name]["default"]

            logger.debug("Selecting %s", ThreadClass.__name__)
            thread = ThreadClass(
                **kwargs
            )

            self.program.append(thread)

        self.add_barriers(self.program)
        logger.debug(self.program)
