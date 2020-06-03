import logging
import traceback

import pandas as pd

from learnmem.server.controllers.boards import BOARDS
from learnmem.server.programmers.programmers import Programmer
from learnmem.server.core.base import Base, Root

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Controller(Base, Root):
    r"""
    Interface between a programmer, its threads and the control_thread.
    Reports the state of the controller functionality.
    It tipically drives an Arduino board in the real world.
    """

    _programmerClass = Programmer

    def __init__(self, mapping_path, program_path, *args, board_name='ArduinoDumy', arduino_port='/dev/ttyACM0', sampling_rate=10.0, **kwargs): # pylint: disable=line-too-long

        r"""
        :param mapping_path: Path to a .csv showing which hardware is phisically wired to which pin.
        :type mapping_path: str

        :param program_path: Path to .csv listing a sequence of pin trigger.
        Read and processed by the programmer class.
        :type program_path: str

        :param args: Extra positional arguments for the threading.Thread constructor.

        :param board: Codename of the board selected by the user.
        It must match one of the keys in BOARDS.
        :type board: str

        :param arduino_port: Path to device file representing the board in the OS.
        :type arduino_port: str

        :param sampling_rate: Frequency in Hertz with which the pins are updated.
        :type sampling_rate: float

        :param kwargs: Extra keyword arguments for the threading.Thread constructor.
        """

        super().__init__(*args, **kwargs)



        # Build a dictionary mapping hardware to pin number
        self._mapping = self._load_mapping(mapping_path)
        #Store the state of each pin of the controller
        self._pin_state = {hardware: 0 for hardware in self._mapping}

        # Board instance compatible with the threads classes
        self._board_name = board_name
        self._arduino_port = arduino_port
        self._board = BOARDS[self._board_name](self._arduino_port)

        # Programmer instance that processes user input
        # into a 'program', an organized sequence of events
        # that turn on and off the pins in the board
        self._submodules['programmer'] = self._programmerClass(
            self._board, self._pin_state, sampling_rate,
            self._mapping, program_path=program_path
        )
        self._settings.update(self._submodules['programmer'].settings)

    # @property
    # def settings(self):
    #     return super()._settings

    @property
    def mapping(self):
        return self._mapping

    @mapping.setter
    def mapping(self, mapping_path):
        self._mapping = self._load_mapping(mapping_path)

    @property
    def info(self):
        return self._info

    @info.getter
    def info(self):
        r"""
        Add to the default info dictionary (status and time_zero)
        the following controller specific properties
        """
        logging.debug('Requesting Controller.info')
        self._info.update({
            "programs": self._submodules['programmer'].list(),
            "pin_state": self.pin_state,
            "mapping": self.mapping,
        })
        logging.debug('Controller.info OK')

        return self._info

    def load(self, program_path):
        self._submodules['programmer'].program_path = program_path

    @property
    def pin_state(self):
        r"""
        A getter so more high level classes can access _pin_state
        without being able to write (set) to it
        """
        return self._pin_state

    def list(self):
        return self._submodules['programmer'].list()

    def _load_mapping(self, mapping_path):
        r"""
        Read a mapping.csv file and return a dictionary of key-value pairs
        where keys are hardware names and values the pin number they are
        physically wired to.
        """
        mapping_df = pd.read_csv(mapping_path, comment='#')
        required_columns = ['pin_id', 'pin_number']

        if not all([e in mapping_df.columns for e in required_columns]):
            logging.warning("Provided mapping is not valid")
            logging.warning("mapping_path: %s", mapping_path)
            logging.warning("Required columns %s", ' '.join(required_columns))
            logging.warning("Provided columns %s", ' '.join(mapping_df.columns))


            return


        mapping = {}
        logger.debug("mapping_df")
        logger.debug(mapping_df)

        for row_tuple in mapping_df.iterrows():
            row = row_tuple[1].to_dict()
            mapping[row["pin_id"]] = row["pin_number"]

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

        return mapping_formatted
        # TODO additional processing steps to guarantee standard mapping format

    def stop(self):

        super().stop()

        for thread in self._submodules['programmer'].program:
            thread.stop()

        for thread in self._submodules['programmer'].program:
            if thread.is_alive():
                thread.join()
                logger.info("Joined %s", thread.name)
                # print({t.name: t.is_alive() for t in self._submodules['programmer'].program})

        logger.debug("Done joining!")


    @property
    def columns(self):
        r"""
        Returns a list with the hardware in use
        Useful to prepare the header of the output .csv.
        """
        return list(self._mapping.keys())

    def load_program(self, program_path):
        self._submodules['programmer'].program_path = program_path


    def run(self):
        r"""
        Start executing the threads in self._submodules['programmer'].program.
        """

        super().run()

        if not self._submodules['programmer'].loaded:
            logger.warning("Please load a program before recording")
            logger.info(self._submodules['programmer'].list())
            return

        for thread in self._submodules['programmer'].program:
            try:
                thread.start()
            except Exception as error:
                logger.info(thread)
                logger.warning(traceback.print_exc())
                raise error
