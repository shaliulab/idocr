r"""
Control each pin separately and concurrently by providing it with
start and end times and the value it should exhibit when on
These classes are instantiated by a Programmer instance
taking the user input and the information from a Controller instance
"""
# Standard library imports
import logging
from threading import Event, BrokenBarrierError
import time

import numpy as np

from idoc.debug import IDOCException
from idoc.server.core.base import Base, Root, StatusThread

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#pylint: disable=W0223

class BaseControllerThread(Base, Root):
    r"""
    Abstract class for parallel execution of pins in a Dummy or Pyfirmata board
    This implementation requires each event is driven by a separate thread.
    """

    _modes = {"output": "o", "pwm": "p"}
    pin_state = None

    def __init__(
            self, i: int, hardware: str, pin, pin_state: dict, mode: str, start, end, value: float, *args,
            sampling_rate=10.0, result_writer=None, use_wall_clock=False, **kwargs
        ):
        """

        :param i: A unique identifier for each instance
        :type i: int

        :param hardware:
        Identify hardware component a thread instance will be in charge of
        Not used in the code other than for logging. The variable that tells an instance which pin
        to control is pin_number.
        :type hardware: ``str`

        :param pin_state:
        A dictionary storing pairs of pin numbers and their corresponding state
        i.e. turned on or off.
        It is updated live and shared by all the threads in run in the same Controller class
        This way, it can be used to query the state of the whole Controller.

        :param mode:
        A valid mode for the get_pin function.
        Eiher i (input), o (output) or p (pwm).

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
        self._pin = pin
        self.pin_state = pin_state
        self._barriers = {}
        self._result_writer = result_writer
        self._mode = mode

        logger.debug(
            "Address from class %s of pin_state in memory %s",
            self.__class__.__name__, id(self.pin_state)
        )

        self._start = start
        self._end = end
        self._value = value
        self.sampling_rate = sampling_rate
        self._last_t = 0
        self._use_wall_clock = use_wall_clock



    @property
    def start_seconds(self):
        return self._start

    @property
    def end_seconds(self):
        return self._end

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
        with format HARDWARE-i
        """
        return "%s-%s" % (self._hardware, self.index)

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

        try:
            assert 0 <= value <= 1
        except AssertionError:
            raise IDOCException('Passed value not valid: %s' % str(value))

        self._value = value

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

    def turn_on(self, value=None):
        # TODO This will set the value of the pin in the convenience monitor
        # 'pin_state' to self.value for the whole period from start to end
        # even if the pin is controlled with a wave
        # Shall I change this so the monitor displays the wave?

        logger.info("%s: Turning %s on (%s)", self.last_t, self._hardware, value or self.value)
        self._notify(value or self.value)

        return self._turn_on(value or self.value)

    def turn_off(self):

        logger.debug("%s: Turning %s  off (0)", self.last_t, self._hardware)
        self._notify(0)
        return self._turn_off()

    def _turn_on(self, value=None):
        # implemented in a subclass
        raise NotImplementedError

    def _turn_off(self, value=None):
        # implemented in a subclass
        raise NotImplementedError


    def _notify(self, value):
        self.pin_state[self._hardware] = value
        logger.warning("%s notifying %s", self.hardware, str(value))

        self._result_writer.process_row(
            self.pin_state,
            table_name="CONTROLLER_EVENTS"
        )

    @property
    def last_t(self):
        return self._last_t

    @last_t.setter
    def last_t(self, last_t):
        # print("Receiving in LED_R_RIGHT last_t = %s" % last_t)
        self._last_t = last_t

    @last_t.getter
    def last_t(self):
        if self._use_wall_clock:
            return self.elapsed_seconds
        else:
            # Use the clock of the recognizer
            # Very useful when analyzing a video offline
            # so the video and the controller get aligned
            # Need to use --no-wall-clock-time
            return self._last_t

    def run(self):


        super().run()

        # print("Hardware %s is running" % self._hardware)


        logger.debug(
            "%s (class %s) is starting to run",
            self.name, self.__class__.__name__
        )

        while self.last_t < self.start_seconds:
            # print("%s - %s", self._hardware, self.last_t)

            time.sleep(1 / self.sampling_rate)

            if self.stopped:
                logger.info('%s: %s is stopping before reaching the start barrier', self.last_t, self.name)
                self.turn_off()
                return


        # make sure all contemporaneous threads start as close to each other as possible
        # this call locks the thread until the contemporaneous threads reach the same state
        logger.debug(
            "%s: %s (class %s) reached the start barrier",
            self.last_t, self.name, self.__class__.__name__
        )

        # print("Hardware %s reached the start barrier with id %s. Already %d waiting" % (self._hardware, id(self._barriers["start"]), self._barriers["start"].n_waiting))

        try:
            self._barriers["start"].wait()
        except (KeyError, BrokenBarrierError):
            logger.info('%s: %s is stopping before turning on', self.last_t, self.name)
            return None

        self.turn_on()

        # wait until you should turn off
        if np.isnan(self.end_seconds):
            self._end_event.wait()
        else:
            while self.last_t < self.end_seconds:
                time.sleep(1 / self.sampling_rate)
                if self.stopped:
                    logger.info('%s: %s is stopping before turning off', self.last_t, self.name)
                    self.turn_off()
                    return

        # turn off
        self.turn_off()

        # signal to other threads ending simultaneously
        # and those that should start right afterwards
        logger.debug(
            "%s: %s (class %s) reached the end barrier",
            self.last_t, self.name, self.__class__.__name__
        )

        try:
            self._barriers["end"].wait()
        except (KeyError, BrokenBarrierError):
            logger.info('%s: The end barrier in %s was aborted', self.last_t, self.name)
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
        logger.debug("Stopping thread")
        super().stop()
        logger.debug("Aborting barriers")
        self.abort()
        logger.debug("Turning off")
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
        self._thread_wave = StatusThread(target=self.wave)
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

    def reset(self):
        super().reset()
        self._shore.clear()


    def get_thread_wave(self, value=None):
        if self._thread_wave.stopped:
            self.reset()
            self._thread_wave = StatusThread(target=self.wave, kwargs={"value": value})

        return self._thread_wave


    def wave(self, value=None):
        """
        Turn on the pin, wait on seconds, turn off the pin, wait off seconds and start over
        as long as the _shore event is not set
        """


        while not self._shore.is_set():
            self._turn_on(value or self.value)
            self._shore.wait(self._seconds_on)
            self._turn_off()
            self._shore.wait(self._seconds_off)


    def turn_on(self, value=None):

        if value is not None:
            self.value = value
            self.get_thread_wave(value or self.value)


        # if self._hardware == "LED_R_RIGHT":
            # print("TURN ON")

        if not self._thread_wave.running:
            logger.info("%s: Turning %s on (%s)", self.last_t, self._hardware, value or self.value)

            # print("Starting thread")
            self._notify(value or self.value)
            self._thread_wave.start()

    def turn_off(self):

        logger.info("%s: Turning %s off (0)", self.last_t, self._hardware)
        self._thread_wave.stop()
        self._notify(0)
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
    _value = 1
    mode = None

    def _turn_on(self, value=None):
        self.pin.write(value or self.value)

    def _turn_off(self):
        self.pin.write(0)

class DummyMixin():
    r"""
    Mixin encapsulating dummy functionality
    Add it to classes BaseControllerThread or WaveBaseControllerThread to
    show them how to just log to the terminal and do nothing
    for dev/debugging purposes
    """

    def _turn_on(self, value=None):
        if not self.stopped:
            self.pin.write(value or self.value)
            # logger.info(
            #     "%s (class %s) is setting %s to %.8f @ %.4f",
            #     self.name, self.__class__.__name__, self._hardware, value or self._value, self.elapsed_seconds or 0
            # )


    def _turn_off(self):
        self.pin.write(0)

        if not self.stopped:
            pass
            # logger.info(
            #     "%s (class %s) is setting %s to %.8f @ %.4f",
            #     self.name, self.__class__.__name__, self._hardware, 0, self.elapsed_seconds or 0
            # )

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
