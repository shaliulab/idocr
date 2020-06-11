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
from idoc.server.controllers.threads import DefaultArduinoThread, WaveArduinoThread
from idoc.server.controllers.threads import DefaultDummyThread, WaveDummyThread
from idoc.configuration import IDOCConfiguration
from idoc.debug import IDOCException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


THREADS = {
    "ArduinoDummy": {"default": DefaultDummyThread, "wave": WaveDummyThread},
    "ArduinoX": {"default": DefaultArduinoThread, "wave": WaveArduinoThread}
    }


class Programmer(Settings, Root):
    r"""
    Load user paradigms and prepare threads for concurrent control of an Arduino or Dummy board
    """

    table = None
    _paradigms_dir = None

    def __init__(
            self, result_writer, board_class, pin_state, sampling_rate, mapping, paradigm_path, *args,
            use_wall_clock=True, arduino_port="/dev/ttyACM0", **kwargs
        ):

        super().__init__(*args, **kwargs)

        self._use_wall_clock = use_wall_clock
        self._result_writer = result_writer
        self._paradigms_dir = self._config.content["folders"]["paradigms"]["path"]
        self._arduino_port = arduino_port
        self._board_class = board_class
        self._board = None
        self._sampling_rate = sampling_rate
        self._mapping = mapping
        self.pin_state = pin_state
        self._barriers = {}
        self._paradigm = []
        self.table = []
        self._submodules = {}
        self._settings.update({
            'paradigm_path': None,
        })

        self._loaded = False
        self._locked = False
        self.paradigm_path = paradigm_path


    @property
    def board(self):
        return self._board

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
    def paradigm(self):
        return self._paradigm

    @property
    def ready(self):
        return self._paradigm is not None


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

        # logger.warning("Updating paradigm_path")

        if paradigm_path is None:
            return

        if paradigm_path == self._settings['paradigm_path']:
            return

        # if there already is an initialized board, close it
        # so we can open it again
        # a fresh board is always needed because otherwise a
        # pyfirmata.pyfirmata.PinAlreadyTakenError is raised
        # when the Thread classes attempt to retrieve their pin
        self._loaded = False
        if self._board is not None:
            self._board.exit()

        self._board = self._board_class(self._arduino_port)
        self._settings['paradigm_path'] = paradigm_path

        # load the data in paradigm_path into Python

        try:
            self._load_table(paradigm_path)
        except Exception as error:
            logger.warning("Error reading your paradigm into IDOC")
            logger.debug(error)
            logger.debug(traceback.print_exc())
            return

        if self.table == []:
            logger.warning("Error reading your paradigm into IDOC")
            return

        # actually generate the threads that this paradigm dictates
        try:
            self._prepare()
            self._loaded = True
        except Exception as error:
            logger.warning("Error loading your paradigm into IDOC")
            logger.debug(error)
            logger.debug(traceback.print_exc())
            return


    @property
    def duration(self):
        r"""
        Return maximum value of end stored in the table
        used to generate the paradigm
        This is considered as the duration of the paradigm
        The value is returned in seconds, assumming the user input was in seconds
        """
        ends = [row["end"] for row in self.table]
        try:
            duration = max(ends)
            return duration

        except ValueError:
            return None

    @property
    def absolute_paradigm_path(self):
        if self._settings["paradigm_path"] is None:
            return None

        return os.path.join(self._paradigms_dir, self._settings["paradigm_path"])


    def _load_table(self, paradigm_path):
        r"""
        Load a csv into python in list format
        Each row becomes a dictionary inside the list
        and the columns and their values are encoded
        as key-value pairs of the dictionary.
        """

        # make sure the old table is removed, if any
        self.table = []

        if paradigm_path is None:

            self.table = None
            self._paradigm = None
            return

        elif paradigm_path not in self.list(dict_format=False):
            self.table = None
            self._paradigm = None
            logger.warning("The passed paradigm does not exist!")
            return


        table_df = pd.read_csv(self.absolute_paradigm_path)

        required_columns = ["start", "end", "on"]
        missing_index = [not e in table_df.columns for e in required_columns]

        if "off" not in table_df.columns:

            if "hertz" in table_df.columns:
                off = (1000  - table_df["on"] * table_df["hertz"]) / table_df["hertz"]
                table_df["off"] = off
                table_df.drop(["hertz"], axis=1)

            else:
                missing_index.append(True)


        missing_columns = list(compress(required_columns, missing_index))
        synonym_available = sum([e in table_df.columns for e in ["hardware", "pin_id"]])

        if len(missing_columns) != 0:
            logger.warning("Provided paradigm is not valid. Please provide columns %s", ' '.join(missing_columns))
            return

        if synonym_available != 1:
            logger.warning("Please provide a column called hardware on your paradigm")
            return

        if synonym_available == 2:
            table_df.drop(["pin_id"], index=1)

        # convert on and off from ms to seconds
        table_df["on"] /= 1000
        table_df["off"] /= 1000

        for row_tuple in table_df.iterrows():
            row = row_tuple[1].to_dict()
            self.table.append(row)

        logger.debug(self.table)


    def _parse(self, row, i):
        r"""
        Process the content of the row inside prepare() and return a
        kwargs dictionary that can be unpacked upon BaseControllerThead
        initializations.
        """

        # XOR (signals invalid user input in the loaded paradigm)
        if np.isnan(row['on']) ^ np.isnan(row['off']):
            logger.warning(
                "Row number %d in paradigm %s is malformed",
                i+1, self._settings['paradigm_path']
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
            hardware = hardware.replace("ODOUR", "ODOR")

        # get the pin number from the mapping using the hardware name
        try:
            pin_number = self._mapping[hardware]
        except KeyError:
            raise Exception("%s is not available in the mapping" % hardware)

        # Deduce a mode and a value from user input and the config file
        value = None
        mode = None

        # if a mode is provided in the user input, use that
        # otherwise set mode to undefined
        if "mode" in row:
            mode = row["mode"]


        # if the hardware is listed in the config as using pwm
        # and mode is p or undefined (i.e. not provided)
        # assume pwm and use the value from the config
        if hardware in self._config.content["controller"]['pwm']:
            if mode == "p" or mode is None:
                mode = "p"
                value = self._config.content["controller"]['pwm'][hardware]
            # if it is listed but the user provided a defined mode
            # and is not pwm, then use it and set the value to 1
            else:
                value = 1

        # otherwise, if the hardware is not listed in the config as pwm
        # but the user provided a value and the mode is p
        # just take that value
        elif mode == "p":
            if "value" in row:
                value = row["value"]
            else:
                logger.warning(
                    'User requested %s in p mode but a pwm value is not available in the config or the input',
                    hardware
                )
                mode = "o"
        else:
            mode = "o"
            value = 1

        try:
            assert mode is not None and value is not None
        except AssertionError:
            template = "%s has invalid configuration: mode %s and value %s"
            message = template % (hardware, mode, value)
            logger.warning(message)
            raise IDOCException


        # push these 3 values to kwargs
        kwargs.update({
            "hardware": hardware,
            "pin_number": pin_number,
            "value": float(value),
            "mode": mode
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

        self._barriers = {}

        switch_times = {
            "start": Counter([e["start"] for e in self.table]),
            "end": Counter([e["end"] for e in self.table]),
            "total": Counter([v[e] for e in ["start", "end"] for v in self.table])
        }

        self._barriers = {k: Barrier(v) for k, v in switch_times["total"].items()}

        for switch_time in self._barriers:
            logger.debug(
                "Barrier at time %d with id %s will wait for %d parties",
                switch_time,
                id(self._barriers[switch_time]),
                self._barriers[switch_time].parties
            )

        return self._barriers


    def _add_barriers(self, paradigm):
        r"""
        Add the barriers to the threads in the right position.
        """

        # provide the threads with barriers for improved synchronization
        # at the expense of slightly increased waiting times
        for thread in paradigm:

            start_barrier = self._barriers[thread.start_seconds]
            thread.add_barrier(start_barrier, "start")

            end_barrier = self._barriers[thread.end_seconds]
            thread.add_barrier(end_barrier, "end")

    def _prepare(self):
        r"""
        Given a paradigm_table, parse it
        to produce a paradigm by storing instances of
        ControllerThread in the self._paradigm list.
        A paradigm is a list of ControllerThread instances
        """

        if self._locked:
            return

        self._paradigm.clear()
        logger.warning("Clearing paradigm")

        for i, row in enumerate(self.table):

            kwargs = {"i": str(i).zfill(3)}
            # import ipdb; ipdb.set_trace()
            extra_kwargs = self._parse(row, i)
            kwargs.update(extra_kwargs)
            kwargs["result_writer"] = self._result_writer
            kwargs["use_wall_clock"] = self._use_wall_clock
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

            self._paradigm.append(thread)

        self._make_barriers()
        self._add_barriers(self._paradigm)
        logger.debug(self._paradigm)
