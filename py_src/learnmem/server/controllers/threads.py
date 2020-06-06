r"""
Control each pin separately and concurrently by providing it with
start and end times and the value it should exhibit when on
These classes are instantiated by a Programmer instance
taking the user input and the information from a Controller instance
"""
# Standard library imports
import logging
from threading import Thread, Event, BrokenBarrierError
import time

from learnmem.server.core.base import Base, Root
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#pylint: disable=W0223

class BaseControllerThread(Base, Root):
    r"""
    Abstract class for parallel execution of pins in a Dummy or Pyfirmata board
    This implementation requires each event is driven by a separate thread.
    """

    _modes = {"output": "o", "pwm": "p"}
    _board = None
    pin_state = None

    def __init__(
            self, i, hardware, board, pin_state, pin_number, mode, start, end, *args,
            value=1, sampling_rate=10.0, result_writer=None, **kwargs
        ):
        """

        :param i: A unique identifier for each instance
        :type i: int

        :param hardware:
        Identify hardware component a thread instance will be in charge of
        Not used in the code other than for logging. The variable that tells an instance which pin
        to control is pin_number.
        :type hardware: ``str`

        :param board:
        An object of type pyfirmata board that is shared across threads
        and contains handlers for the physical board pins.
        It needs to provide get_pin and write methods.

        :param pin_state:
        A dictionary storing pairs of pin numbers and their corresponding state
        i.e. turned on or off.
        It is updated live and shared by all the threads in run in the same Controller class
        This way, it can be used to query the state of the whole Controller.

        :param pin_number:
        Select a pin from a microcontroller board i.e. Arduino.
        :type pin_number: ``int``

        :param mode:
        A valid mode for the get_pin function.
        Eiher i (input), o (output) or p (pwm).
        :type pin_number: ``str``

        :param start:
        Time in seconds when the thread should turn on a pin.
        :type start: ``float``

        :param end:
        Time in seconds when the thread should turn off a pin.
        :type end: ``float``

        :param value:
        Value to which a pin is set to. If equal to 0.0 or 1.0,
        it will be coerced to 0 or 1 and the pin will open in digital mode.
        If it is a float between 0 and 1,
        it is not coerced and the pin is opened in pwm mode with that intensity
        (max intensity is 1).

        :type value: ``float``

        :param sampling_rate:
        Frequency in Hertz (s-1) with which the thread will check
        if it should move on in the target function. Default 10.
        :type sampling_rate: ``float``

        :param args:
        Extra positional arguments for the Thread class.
        :type args: ``tuple``

        :param kwargs:
        Extra keyword arguments for the Thread class.
        :type kwargs: ``dictionary``
        """
        super().__init__(*args, **kwargs)

        self.index = i
        self._hardware = hardware
        self._board = board
        self.pin_state = pin_state
        self._barriers = {}
        self._result_writer = result_writer
        self._mode = mode

        logger.debug(
            "Address from class %s of pin_state in memory %s",
            self.__class__.__name__, id(self.pin_state)
        )

        self._pin_number = pin_number
        self.start_seconds = start
        self.end_seconds = end
        self._value = value
        self.sampling_rate = sampling_rate

        string = 'd:%d:%s' % (self._pin_number, self._mode)
        logger.warning(string)
        self._pin = self._board.get_pin(string)

    @property
    def hardware(self):
        return self._hardware

    @property
    def pin(self):
        return self._pin

    @property
    def name(self):
        r"""
        Unique thread identifier
        with format HARDWARE@PIN_NUMBER-i
        """
        return "%s@%s-%s" % (self._hardware, str(self._pin_number).zfill(3), self.index)

    @property
    def duration(self):
        r"""
        Seconds since the thread will first turn on the pin
        until it turns it off for the last time.
        """
        return self.end_seconds - self.start_seconds

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):

        if 0 <= value <= 1:
            self._value = value
        else:
            logger.warning('Passed value not valid: %s', str(value))

    @property
    def mode(self):
        return self._mode

    def add_barrier(self, barrier, name):
        r"""
        Set barrier as a blocking element during execution of the thread
        in the name position
        name = start -> before turning the pin on for the first time
        name = end -> after turning the pin off for the last time
        (right before self.run() is over).
        """
        self._barriers[name] = barrier

    def is_wave(self):
        r"""
        If True, the thread implements a duty cycle
        during the execution of self.turn_on()
        This is currently determined by the name of the class
        starting with Wave
        """
        value = self.__class__.__name__[:4] == "Wave"
        return value

    def turn_on(self):
        # TODO This will set the value of the pin in the convenience monitor
        # 'pin_state' to self.value for the whole period from start to end
        # even if the pin is controlled with a wave
        # Shall I change this so the monitor displays the wave?

        logger.debug("Turning %s on (%s)", self._hardware, self.value)
        self._notify(self.value)
        return self._turn_on()

    def turn_off(self):

        logger.debug("Turning %s  off (0)", self._hardware)
        self._notify(0)
        return self._turn_off()

    def _turn_on(self):
        # implemented in a subclass
        raise NotImplementedError

    def _turn_off(self):
        # implemented in a subclass
        raise NotImplementedError


    def _notify(self, value):
        self.pin_state[self._hardware] = value
        self._result_writer.process_row(
            data={"t": self.elapsed_seconds, **self.pin_state},
            table_name="CONTROLLER_EVENTS"
        )

    def run(self):

        self.running = True

        logger.debug(
            "%s (class %s) is starting to run",
            self.name, self.__class__.__name__
        )

        while self.elapsed_seconds < self.start_seconds:
            time.sleep(1/self.sampling_rate)
            if self.stopped:
                logger.info('%s is stopping early', self.name)
                self.turn_off()
                return


        # make sure all contemporaneous threads start as close to each other as possible
        # this call locks the thread until the contemporaneous threads reach the same state
        logger.debug(
            "%s (class %s) reached the start barrier",
            self.name, self.__class__.__name__
        )

        try:
            self._barriers["start"].wait()
        except (KeyError, BrokenBarrierError):
            logger.info('%s is stopping early', self.name)
            return

        # turn on
        self.turn_on()

        # wait until you should turn off
        while self.elapsed_seconds < self.end_seconds:
            time.sleep(1/self.sampling_rate)
            if self.stopped:
                logger.info('%s is stopping early', self.name)
                self.turn_off()
                return

        # turn off
        self.turn_off()

        # signal to other threads ending simultaneously
        # and those that should start right afterwards
        logger.debug(
            "%s (class %s) reached the end barrier",
            self.name, self.__class__.__name__
        )

        try:
            self._barriers["end"].wait()
        except (KeyError, BrokenBarrierError):
            logger.info('%s is stopping early', self.name)
            return

    def abort(self):
        r"""
        Stop execution by setting the end_event and aborting barriers.
        This invalidates the barriers, which means the threads won't block
        when they reach them.
        """
        for barrier in self._barriers.values():
            barrier.abort()

    def stop(self):
        super().stop()
        self.abort()
        self.turn_off()

class WaveBaseControllerThread(BaseControllerThread):
    r"""
    A Thread implementing a duty cycle pin as opposed to a
    continuously on pin
    The pin "blinks" when it is signalled to run
    Instead of being set to on for the whole duration of the period
    until turn_off is called,
    it turns on for on seconds and off for off seconds.
    """

    def __init__(self, seconds_on, seconds_off, *args, **kwargs):
        r"""
        :param seconds_on: Time in seconds the pin should stay on in each cycle.
        :type seconds_on: ``float``

        :param seconds_off: Time in seconds the pin should stay off in each cycle.
        :type seconds_off: ``float``
        """
        self._seconds_on = seconds_on
        self._seconds_off = seconds_off
        self._shore = Event()
        self._on_thread = Thread(target=self.wave)
        super().__init__(*args, **kwargs)


    @property
    def shore(self):
        return self._shore.is_set()

    @shore.setter
    def shore(self, value):
        if not self._shore.is_set():
            if value is True:
                self._shore.set()

    def stop(self):
        self.shore = True
        super().stop()

    def wave(self):
        r"""
        Turn on the pin, wait on seconds, turn off the pin, wait off seconds and start over
        as long as the _shore event is not set
        """

        self._notify(self.value)
        while not self._shore.is_set():
            self._turn_on()
            self._shore.wait(self._seconds_on)
            self._turn_off()
            self._shore.wait(self._seconds_off)

        logger.info(
            "%s (class %s) has reached the shore",
            self.name, self.__class__.__name__
        )
        self._notify(0)


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

    def _turn_on(self):
        self.pin.write(self.value)

    def _turn_off(self):
        self.pin.write(0)

class DummyMixin():
    r"""
    Mixin encapsulating dummy functionality
    Add it to classes BaseControllerThread or WaveBaseControllerThread to
    show them how to just log to the terminal and do nothing
    for dev/debugging purposes
    """

    def _turn_on(self):
        # if self._hardware != "ONBOARD_LED".ljust(16):
        logger.info(
            "%s (class %s) is setting %s to %.8f @ %.4f",
            self.name, self.__class__.__name__, self._hardware, self.value, self.elapsed_seconds
        )
        self.pin.write(self.value)

    def _turn_off(self):
        # if self._hardware != "ONBOARD_LED".ljust(16):
        logger.info(
            "%s (class %s) is setting %s to %.8f @ %.4f",
            self.name, self.__class__.__name__, self._hardware, 0, self.elapsed_seconds
        )
        self.pin.write(0)

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
