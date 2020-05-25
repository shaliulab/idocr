r"""
Control each pin separately and concurrently by providing it with
start and end times and the value it should exhibit when on
These classes are instantiated by a Programmer instance
taking the user input and the information from a Controller instance
"""
# Standard library imports
import time
import logging
from threading import Thread, Event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#pylint: disable=W0223

class BaseControllerThread(Thread):

    _stop_event = 'exit'
    _t0 = 0
    _modes = {"output": "o", "pwm": "p"}
    _board = None
    pin_state = None
    board_name = "ArduinoDummy"

    def __init__(self, i, hardware, board, pin_state, pin_number, start, end, *args, value=1, sampling_rate=10.0, **kwargs):
        r"""

        :param i: A unique identifier for each instance
        :type i: int

        :param hardware:
        Identify hardware component a thread instance will be in charge of
        Not used in the code other than for logging. The variable that tells an instance which pin
        to control is pin_number.
        :type hardware: ``str`

        :param board:
        An object of type pyfirmata board that is shared across threads and contains handlers for the physical board pins
        It needs to provide get_pin and write methods.

        :param pin_state:
        A dictionary storing pairs of pin numbers and their corresponding state i.e. turned on or off.
        It is updated live and shared by all the threads in run in the same Controller class
        This way, it can be used to query the state of the whole Controller.

        :param pin_number:
        Select a pin from a microcontroller board i.e. Arduino.
        :type pin_number: ``int``

        :param start:
        Time in seconds when the thread should turn on a pin.
        :type start: ``float``

        :param end:
        Time in seconds when the thread should turn off a pin.
        :type end: ``float``

        :param value:
        Value to which a pin is set to. If equal to 0.0 or 1.0, it will be coerced to 0 or 1 and the pin will open in digital mode
        If it is a float between 0 and 1, it is not coerced and the pin is opened in pwm mode with that intensity (max intensity is 1).

        :type value ``float``

        :param sampling_rate:
        Frequency in Hertz (s-1) with which the thread will check if it should move on in the target function. Default 10.
        :type sampling_rate: ``float``

        :param args:
        Extra positional arguments for the Thread class.
        :type args: ``tuple``

        :param kwargs:
        Extra keyword arguments for the Thread class.
        :type kwargs: ``dictionary``
        """

        self.index = i
        self._hardware = hardware
        self._board = board
        self.pin_state = pin_state
        self._barriers = {}
        self._pin = None


        logger.debug("Address from class %s of pin_state in memory %s", self.__class__.__name__, id(self.pin_state))

        self.pin_number = pin_number
        self.start_time = start
        self.end_time = end
        self._value = value
        self.sampling_rate = sampling_rate
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return f"{self._hardware}@{str(self.pin_number).zfill(3)}-{self.index}"

    @property
    def duration(self):
        return self.end_time - self.start_time

    @property
    def value(self):
        if self._value in [0.0, 1.0]:
            return int(self._value)
        else:
            return self._value

    @property
    def mode(self):

        if self.value is int:
            return self._modes["output"]
        else:
            return self._modes["pwm"]

        #TODO Support input mode too

    @property
    def t0(self):
        return self._t0

    def set_t0(self, t0):
        self._t0 = t0

    def add_barrier(self, barrier, name):
        self._barriers[name] = barrier

    def turn_on(self):
        # TODO This will set the value of the pin in the convenience monitor
        # 'pin_state' to self.value for the whole period from start to end
        # even if the pin is controlled with a wave
        # Shall I change this so the monitor displays the wave?

        logger.debug("Turning %s on (%s)", self._hardware, self.value)
        return self._turn_on()

    def turn_off(self):

        logger.debug("Turning %s  off (0)", self._hardware)
        return self._turn_off()

    def _turn_on(self):
        # implemented in a subclass
        raise NotImplementedError

    def _turn_off(self):
        # implemented in a subclass
        raise NotImplementedError

    @property
    def time_passed(self):
        return time.time() - self._t0

    def run(self):

        logger.debug(
            "%s (class %s) is starting to run",
            self.name, self.__class__.__name__
        )

        while self.time_passed < self.start_time:

            # if self._hardware == "ODOR_A_RIGHT".ljust(16):
            #     logger.info(self.time_passed)

            time.sleep(1/self.sampling_rate)

        # make sure all contemporaneous threads start as close to each other as possible
        # this call locks the thread until the contemporaneous threads reach the same state
        try:
            self._barriers["start"].wait()
        except KeyError:
            pass

        # turn on
        self.turn_on()

        # wait until you should turn off
        while self.time_passed < self.end_time:
            time.sleep(1/self.sampling_rate)

        # turn off
        self.turn_off()

        # signal to other threads ending simultaneously
        # and those that should start right afterwards
        try:
            self._barriers["end"].wait()
        except KeyError:
            pass


class WaveBaseControllerThread(BaseControllerThread):
    r"""
    A Thread implementing a duty cycle pin as opposed to a
    continuously on pin
    The pin "blinks" when it is signalled to run
    Instead of being set to on for the whole duration of the period
    until turn_off is called,
    it turns on for on seconds and off for off seconds.
    """

    def __init__(self, on, off, *args, **kwargs):
        r"""
        :param on: Time in seconds the pin should stay on in each cycle.
        :type on: ``float``

        :param off: Time in seconds the pin should stay off in each cycle.
        :type off: ``float``
        """

        self.on = on
        self.off = off
        self._shore = Event()

        self._on_thread = Thread(target=self.wave)
        super().__init__(*args, **kwargs)

    def wave(self):
        r"""
        Turn on the pin, wait on seconds, turn off the pin, wait off seconds and start over
        as long as the _shore event is not set
        """

        while not self._shore.is_set():
            self._turn_on()
            self._shore.wait(self.on)
            self._turn_off()
            self._shore.wait(self.off)
        logger.info(
            "%s (class %s) has reached the shore",
            self.name, self.__class__.__name__
        )


    def turn_on(self):
        self._on_thread.start()

    def turn_off(self):
        logger.info(
            "%s (class %s) is setting the shore",
            self.name, self.__class__.__name__
        )

        self._shore.set()


class ArduinoMixin():

    r"""
    Mixin encapsulating all the Arduino/Pyfirmata functionality
    Add it to classes BaseControllerThread or WaveBaseControllerThread to
    'teach' them how to interact with Arduino boards using pyfirmata.

    * Selection of pins
    * Turn on and off a pin
    """

    # supplied in the classes where ArduinoMixin is mixed in
    _board = None
    pin_number = None
    _value = 1
    mode = None
    board_name = "ArduinoX"

    @property
    def pin(self):
        return self._pin

    @pin.getter
    def pin(self):
        r"""
        get_pin needs a string with three parts
        a/o for analog or digital pin
        pin number
        i,o,p for mode in input, output, pwm
        They will be fetched from the class' attributes
        """
        return self._board.get_pin('d:{self.pin_number}:{self.mode}')

    def _turn_on(self):
        self.pin_state[self._hardware] = self.value
        self.pin.write(self.value)

    def _turn_off(self):
        self.pin_state[self._hardware] = 0
        self.pin.write(0)

class DummyMixin():
    r"""
    Mixin encapsulating dummy functionality
    Add it to classes BaseControllerThread or WaveBaseControllerThread to
    show them how to just log to the terminal and do nothing
    for dev/debugging purposes
    """

    def _turn_on(self):
        self.pin_state[self._hardware] = self.value

        if self._hardware != "ONBOARD_LED".ljust(16):
            logger.info(
                "%s (class %s) is setting %s to %.8f @ %.4f",
                self.name, self.__class__.__name__, self._hardware, self.value, self.time_passed
            )

    def _turn_off(self):
        self.pin_state[self._hardware] = 0
        if self._hardware != "ONBOARD_LED".ljust(16):
            logger.info(
                "%s (class %s) is setting %s to %.8f @ %.4f",
                self.name, self.__class__.__name__, self._hardware, 0, self.time_passed
            )

class DefaultDummyThread(DummyMixin, BaseControllerThread):
    r"""
    A dummy thread that just logs without actually activating any hardware
    Useful for debugging
    """

class WaveDummyThread(DummyMixin, WaveBaseControllerThread):
    r"""
    A dummy thread that just logs without actually activating any hardware
    Useful for debugging
    """

class DefaultArduinoThread(ArduinoMixin, BaseControllerThread):
    r"""
    A thread using an Arduino board without wave
    """

class WaveArduinoThread(ArduinoMixin, WaveBaseControllerThread):
    r"""
    A thread using an Arduino board with wave
    """
