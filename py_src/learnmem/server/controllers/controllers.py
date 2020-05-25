import logging
from threading import Event, Thread
import traceback

import pandas as pd

from learnmem.server.controllers.boards import ArduinoDummy, ArduinoBoard, ArduinoMegaBoard
from learnmem.server.programmers.programmers import Programmer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
BOARDS = {'ArduinoUno': ArduinoBoard, 'ArduinoMega': ArduinoMegaBoard, 'ArduinoDummy': ArduinoDummy}

class Controller(Thread):
    r"""
    Orchestrate
    """

    _port = None
    _mapping = {}
    _board = None

    _programmerClass = Programmer
    # _monitorClass = Monitor
    pin_state = {}
    daemon = True

    def __init__(self, mapping_path, program_path, *args, board='ArduinoMega', devport='/dev/ttyACM0', sampling_rate=10.0, **kwargs):

        self.mapping = mapping_path
        self.pin_state = {hardware: 0 for hardware in self._mapping}
        self._board_name = board
        self.start_event = Event()
        self.end_event = Event()
        self._devport = devport
        self._board = BOARDS[self._board_name](self._devport)
        self.programmer = self._programmerClass(
            self._board, self.pin_state, sampling_rate, self._mapping, program_path=program_path
        )
        self._t0 = 0

        super(Controller, self).__init__(*args, **kwargs)

    @property
    def mapping(self):
        return self._mapping

    # populate the mapping slot
    @mapping.setter
    def mapping(self, mapping_path):
        r"""
        Read a mapping.csv file and return a dictionary of key-value pairs
        where keys are hardware names and values the pin number they are
        physically wired to
        """
        mapping_df = pd.read_csv(mapping_path)

        mapping = {}
        logger.debug("mapping_df")
        logger.debug(mapping_df)

        for row in mapping_df.iterrows():
            r = row[1].to_dict()
            mapping[r["pin_id"]] = r["pin_number"]

        logger.debug("mapping")
        logger.debug(mapping)

        # catch columns called odour_x and make sure they are called odor_x
        # and make all keys the same length by padding spaces
        mapping_formatted = {}
        for k in mapping:
            k_american = k.replace("ODOUR", "ODOR")
            k_american = k_american.ljust(16)
            mapping_formatted[k_american] = mapping[k]

        logger.debug("list of keys in mapping_formatted")
        logger.debug(list(mapping_formatted.keys()))

        self._mapping = mapping_formatted

        # TODO additional processing steps to guarantee standard mapping format

    @property
    def columns(self):
        return list(self._mapping.keys())

    @property
    def running(self):
        r"""
        Return True if the run method has been called at least once, False otherwise
        """
        return self.start_event.is_set()

    @running.setter
    def running(self, value):
        if value is True:
            self.start_event.set()

    @property
    def t0(self):
        return self._t0

    @t0.setter
    def t0(self, t0):
        self._t0 = t0

    def run(self):
        r"""
        Start executing the threads in self._program
        The start of this method signals the start of an experiment
        """

        if self.programmer.program is None:
            logger.warning("Please load a program before recording")
            logger.info(self.programmer.list())
            return

        self.running = True

        for thread in self.programmer.program:
            thread.set_t0(self._t0)
            try:
                thread.start()
            except Exception as e:
                logger.info(thread)
                logger.warning(traceback.print_exc())
                raise e

        for thread in self.programmer.program:
            thread.join()

        self.end_event.set()
        logger.info("All done!")
