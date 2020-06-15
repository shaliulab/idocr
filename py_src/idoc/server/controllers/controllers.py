import datetime
import logging
import time
import traceback

import pandas as pd

from idoc.server.hardware.interfaces.interfaces import DefaultInterface
from idoc.server.programmers.programmers import Programmer
from idoc.server.core.base import Base, Root
from idoc.helpers import hours_minutes_seconds, iso_format, MachineDatetime
from idoc.server.controllers.threads import DefaultArduinoThread, WaveArduinoThread
from idoc.server.controllers.threads import DefaultDummyThread, WaveDummyThread
from idoc.debug import IDOCException



# Tell pylint everything here is abstract classes
# pylint: disable=undefined-loop-variable

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Controller(DefaultInterface, Base, Root):
    r"""
    Interface between a programmer, its threads and the control_thread.
    Reports the state of the controller functionality.
    It tipically drives an Arduino board in the real world.
    """

    _programmerClass = Programmer
    valid_actions = ["start", "stop", "reset"]
    _always_on_hardware = ["TARGETS", "MAIN_VALVE", "VACUUM", "IRLED"]
    _threads = {
        "ArduinoDummy": {"DEFAULT": DefaultDummyThread, "WAVE": WaveDummyThread},
        "ArduinoBoard": {"DEFAULT": DefaultArduinoThread, "WAVE": WaveArduinoThread},
        "ArduinoMegaBoard": {"DEFAULT": DefaultArduinoThread, "WAVE": WaveArduinoThread}
    }


    def __init__(
            self, mapping_path, paradigm_path, result_writer, board_class, *args,
            arduino_port='/dev/ttyACM0', sampling_rate=10.0, **kwargs):
        """
        :param mapping_path: Path to a .csv showing which hardware is phisically wired to which pin.
        :type mapping_path: str

        :param paradigm_path: Path to .csv listing a sequence of pin trigger.
        Read and processed by the programmer class.
        :type paradigm_path: str

        :param args: Extra positional arguments for the threading.Thread constructor.

        :param board_class: # TODO
        :type board: str

        :param arduino_port: Path to device file representing the board in the OS.
        :type arduino_port: str

        :param sampling_rate: Frequency in Hertz with which the pins are updated.
        :type sampling_rate: float

        :param kwargs: Extra keyword arguments for the threading.Thread constructor.
        """

        DefaultInterface.__init__(self)

        self._use_wall_clock = kwargs.pop("use_wall_clock")
        super().__init__(*args, **kwargs)

        self._mapping_path = mapping_path or self._config.content["controller"]["mapping_path"]
        self._loaded = False
        self._locked = False
        self._paradigm = []

        # Build a dictionary mapping hardware to pin number
        self._mapping = self._load_mapping(self._mapping_path)
        #Store the state of each pin of the controller
        self._pin_state = {hardware: 0 for hardware in self._mapping}

        # Board instance compatible with the threads classes
        self._board_class = board_class
        self._result_writer = result_writer
        self._sampling_rate = sampling_rate
        self.adaptation_offset = 0
        self._arduino_port = arduino_port
        self._board = None
        self._pins = {}

        # Programmer instance that processes user input
        # into a 'program', an organized sequence of events
        # that turn on and off the pins in the board

        self._submodules['programmer'] = self._programmerClass()

        self.paradigm_path = paradigm_path or self._config.content["controller"]["paradigm_path"]

        self._settings['programmer'] = self._submodules['programmer'].settings
        self._progress = 0
        self._last_t = 0



    @property
    def last_t(self):
        return self._last_t

    @last_t.setter
    def last_t(self, last_t):
        self._last_t = last_t

    def toggle(self, hardware, value):

        try:
            for thread in self._paradigm:
                if thread.hardware == hardware:

                    if value == 0:
                        logging.info("Toggling %s --> off", hardware)
                        thread.turn_off()
                    else:
                        logging.info("Toggling %s --> %s", hardware, str(value))
                        thread.turn_on(value)

                    return {"status": "success"}

            logger.warning("Hardware %s not found in loaded thread paradigm.")
            return None

        except Exception as error:
            logger.warning(error)
            return

    @property
    def programmer(self):
        return self._submodules["programmer"]


    @property
    def duration(self):
        """
        Return maximum value of end stored in the table
        used to generate the paradigm
        This is considered as the duration of the paradigm
        The value is returned in seconds, assumming the user input was in seconds
        """
        ends = [row["end"] for row in self.programmer.table]
        try:
            duration = max(ends)
            return duration

        except ValueError:
            return None


    @property
    def progress(self):
        """
        Return a float from 0 to 100 indicating how many of the
        self.paradigm_duration seconds have passed since
        the controller started running
        """

        if self._time_zero is None:
            self._progress = 0
            return self._progress

        elif self.stopped:
            return self._progress

        else:
            diff = max((datetime.datetime.now() - self._time_zero).total_seconds(), 0)

        try:
            progress = diff / self.duration
        except TypeError: #programmer.duration is not defined
            progress = 0

        self._progress = progress * 100

        return self._progress

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
        # logging.debug('Requesting Controller.info')
        self._info.update({
            "status": self.status,
            "paradigms": self.programmer.list(),
            # "paradigm_path": self.programmer.paradigm_path,
            "pin_state": self.pin_state,
            "mapping": self.mapping,
            "progress": self.progress,
            "board": self._board.__class__.__name__,
            "duration": self.duration
        })
        # logging.debug('Controller.info OK')

        return self._info


    def populate_pins(self, table):
        """
        Take a table produced by programmer._load_table
        (a list of dicts with keys equal to the arguments
        of the thread classes init functions)
        Read which mode is used in each pin and get them from the
        board with the right mode.
        Save these pins under the dictionary self._pins with keys
        equal to the name of the hardware connected to that pin
        """

        seen_hardware = []
        print(table)
        for row in table:
            hardware = row['hardware']
            if hardware not in seen_hardware:
                pin_number = self._mapping[hardware]
                mode = row['mode']
                pin_definition = '%s:%s:%s' % ('d', pin_number, mode)
                pin = self._board.get_pin(pin_definition)
                logger.warning(pin_definition)
                self._pins[hardware] = pin
                seen_hardware.append(hardware)

            else:
                pass

        print("PINS")
        print(self._pins)

    @property
    def paradigm_path(self):
        return self._programmer.paradigm_path

    @paradigm_path.setter
    def paradigm_path(self, paradigm_path):

        # don't load again if the program has the same filename
        # this is done to avoid a superfluous update resetting the self.paradigm object
        if paradigm_path != self.programmer._settings["paradigm_path"]:

            # if there already is an initialized board, close it
            # so we can open it again
            # a fresh board is always needed because otherwise a
            # pyfirmata.pyfirmata.PinAlreadyTakenError is raised
            # when the Thread classes attempt to retrieve their pin
            self._loaded = False
            if self._board is not None:
                self._board.exit()

            logger.warning("Initalizing %s", self._board_class.__name__)
            self._board = self._board_class(self._arduino_port)
            try:
                self.programmer.paradigm_path = paradigm_path
            except IDOCException as error:
                logger.warning(error)
                self._paradigm.clear()
                return

            logger.warning("Loading pins")
            self.populate_pins(self.programmer.table)
            logger.warning("Loaded pins: ")
            logger.warning(self._pins)
            self._prepare()


    @property
    def pin_state(self):
        r"""
        A getter so more high level classes can access _pin_state
        without being able to write (set) to it
        """
        return self._pin_state

    def list(self):
        return self.programmer.list()

    def _load_mapping(self, mapping_path):
        r"""
        Read a mapping.csv file and return a dictionary of key-value pairs
        where keys are hardware names and values the pin number they are
        physically wired to.
        """
        mapping_df = pd.read_csv(mapping_path, comment='#')
        required_columns = ['hardware', 'pin_number']

        if not all([e in mapping_df.columns for e in required_columns]):
            logger.warning("Provided mapping is not valid")
            logger.warning("mapping_path: %s", mapping_path)
            logger.warning("Required columns %s", ' '.join(required_columns))
            logger.warning("Provided columns %s", ' '.join(mapping_df.columns))
            return

        mapping = {}
        for row_tuple in mapping_df.iterrows():
            row = row_tuple[1].to_dict()
            mapping[row["hardware"]] = row["pin_number"]

        # TODO additional processing steps to guarantee standard mapping format
        return mapping

    @property
    def columns(self):
        """
        Returns a list with the hardware in use
        Useful to prepare the header of the output .csv.
        """
        return list(self._mapping.keys())

    def load_paradigm(self, paradigm_path):
        if paradigm_path is not None:
            logger.info('Loading paradigm: %s', paradigm_path)
            self.programmer.paradigm_path = paradigm_path

    @property
    def ready(self):
        return self.programmer.paradigm_path is not None

    @ready.setter
    def ready(self, value): # pylint: disable=unused-argument
        return None

    @property
    def wait(self):
        return max(0, self.adaptation_offset - self.init_elapsed_seconds)

    @property
    def adaptation_left(self):
        return max(0, self.adaptation_offset - self.wait)

    def run_minimal(self):
        """
        Start executing the threads whose hardware matches the names listed in
        self._always_on_hardware.
        """

        for hardware in self._always_on_hardware:
            for thread in self._paradigm:
                if thread.hardware == hardware:
                    logger.info('Turning on %s', thread.hardware)
                    thread.pin.write(1)
                    # TODO what happens with the time_zero?
        time.sleep(2)

    def tick(self, last_t):
        """
        Update the time in the threads
        """

        self.last_t = last_t
        if self._loaded:
            if self.running:
                for thread in self._paradigm:
                    thread.last_t = self.last_t

    def _prepare(self):
        """
        Given a paradigm_table, parse it
        to produce a paradigm by storing instances of
        ControllerThread in the self._paradigm list.
        A paradigm is a list of ControllerThread instances
        """

        if self._locked:
            return

        self._paradigm.clear()
        logger.warning("Clearing paradigm")

        for i, row in enumerate(self.programmer.table):

            thread, kwargs = self.programmer.parse(row, i)
            kwargs["result_writer"] = self._result_writer
            kwargs["sampling_rate"] = self._sampling_rate
            kwargs["pin"] = self._pins[kwargs['hardware']]

            logger.debug(kwargs)

            ThreadClass = self._threads[self._board_class.__name__][thread]

            logger.debug("Selecting %s", ThreadClass.__name__)
            thread = ThreadClass(
                **kwargs, pin_state=self._pin_state, use_wall_clock=self._use_wall_clock
            )

            self._paradigm.append(thread)

        barriers = self.programmer.make_barriers(self.programmer.table)
        self._paradigm = self.programmer.add_barriers(self._paradigm, barriers)
        logger.debug(self._paradigm)
        print("self._paradigm")
        print(self._paradigm)
        self._loaded = True


    def lock(self):
        self.programmer.lock()
        self._locked = True

    def run(self):
        r"""
        Start executing the threads in self._submodules['programmer'].paradigm.
        """

        logger.debug("Controller has elapsed %3.f seconds since init", self.init_elapsed_seconds)

        while self.wait > 0:
            self._end_event.wait(0.1)

        self.ready = True
        self.lock()
        super().run()
        for thread in self._paradigm:
            try:
                thread.time_zero = self.time_zero

                # catch if the thread is already started because it is listed on the always_on_hardware
                if thread.is_alive() and thread.hardware in self._always_on_hardware:
                    pass
                else:
                    thread.start()

            except Exception as error:
                logger.info(thread)
                logger.error(error)
                logger.error(traceback.print_exc())
                self.reset()

    def stop(self):

        super().stop()

        for thread in self._paradigm:
            thread.stop()

        for thread in self._paradigm:
            if thread.is_alive():
                thread.join()
                logger.debug("Joined %s", thread.name)

        logger.debug("Done joining!")

    # TODO Implement a warmup routine so th user can check the hardware
    def warm_up(self):
        pass


if __name__ == "__main__":

    from idoc.configuration import IDOCConfiguration
    from idoc.server.io.result_writer import CSVResultWriter

    config = IDOCConfiguration()

    controller = Controller(
        mapping_path=config.content["controller"]["mapping_path"],
        paradigm_path=config.content["controller"]["paradigm_path"],
        result_writer=CSVResultWriter(
            start_datetime="2000-01-01_00-00-00",
            max_n_rows_to_insert=2
        ),
        board_class=config.content['default_class']["board"],
        arduino_port=config.content["controller"]["arduino_port"]
    )

    controller.start()
    controller.join()
