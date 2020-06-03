r"""
Provide abstract classes with functionality used in:
learnmem.server.core.control_thread.ControlThread
learnmem.server.controllers.controllers.Controller
learnmem.server.programmers.programmers.Programmer
learnmem.server.io.cameras.StandardStream
learnmem.server.io.cameras.PylonStream
learnmem.server.io.cameras.WebCamStream
learnmem.server.io.saver.SimpleSaver
learnmem.server.trackers.trackers.SimpleTracker
"""

import logging
from threading import Thread, Event
import datetime

from learnmem.helpers import hours_minutes_seconds, iso_format, MachineDatetime


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Root:
    r"""
    Most abstract class, designed to implement defensive programming
    as instructed in https://rhettinger.wordpress.com/2011/05/26/super-considered-super/
    """

    def __init__(self):
        pass


class Settings(Root):
    r"""
    Communication bridge between modules in IDOC.
    Each module needs to define a dictionary self._settings to be updated
    and a dictioanry of submodules in self._submodules to communicate with.
    Submodules are notified with the send() and their updates are received with receive()
    """

    def __init__(self, *args, **kwargs):
        self._settings = {}
        self._submodules = {}
        super().__init__(*args, **kwargs)

    @property
    def settings(self):
        r"""
        _settings will only ever contain the keys declared in the
        constructor of the classes inheriting from Settings,
        AND also the _settings of instances listed in _submodules.
        """
        return self._settings

    @settings.setter
    def settings(self, settings):
    # def update_settings(self, settings):
        r"""
        Update the existing settings without extending them.
        """
        # only update pairs with key under self._settings_keys
        new_settings = {k: settings[k] for k in self._settings if k in settings}
        self._settings.update(new_settings)

        # notify submodules
        self.send()

    @settings.getter
    def settings(self):
        r"""
        Return updated settings of current class as well as all other
        instances listed in self._submodules.
        """
        # ask the dependent modules
        self.receive()
        return self._settings

    def send(self):
        r"""
        Send to depending modules the new settings sent by the user.
        """
        for submodule in self._submodules.values():
            logger.debug("%s sending to %s", self.__class__.__name__, submodule.__class__.__name__)
            logger.debug(self._settings)

            submodule.settings = self._settings

    def receive(self):
        r"""
        Receive from depending modules settings that the user could change
        """
        for submodule in self._submodules.values():
            logger.debug(
                "%s receiving from %s",
                self.__class__.__name__, submodule.__class__.__name__
            )
            logger.debug(submodule.settings)
            self._settings.update(submodule.settings)


class Status(Root):
    r"""
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.running = False
        self.ready = False
        self.stopped = False
        self._time_zero = None
        self._status = "idle"

        self._info = {}
        self._info.update({
            "status": self._status,
            "elapsed_time": self.elapsed_time
        })

    @property
    def elapsed_time(self):
        r"""
        Compute the number of seconds since the class is running
        and return it in format HH:MM:SS.
        """

        if self._time_zero is None:
            return None

        time_diff = iso_format(
            hours_minutes_seconds(
                datetime.datetime.now() - self._time_zero
            )
        )
        return time_diff


    @property
    def elapsed_seconds(self):
        r"""
        Compute the number of seconds since the class is running
        and return it in format HH:MM:SS.
        """
        if self._time_zero is None:
            return None

        time_diff = (datetime.datetime.now() - self._time_zero).microseconds / 1000000
        logging.warning(self._time_zero)
        return time_diff

    @property
    def start_datetime(self):
        return self._start_datetime

    @property
    def time_zero(self):
        try:
            return self._info['time_zero']
        except KeyError:
            return None

    @property
    def status(self):
        return self._status

    @status.getter
    def status(self):
        r"""
        Return
        - idle if the the thread has not started yet
        - running if the thread has started and has not been stopped
        - stopped if it has been stopped
        """
        if not self.running:
            self._status = "idle"
            return self._status

        if self.ready and not self.running:
            self._status = 'ready'
            return self._status

        if self.running and not self.stopped:
            self._status = "running"
            return self._status

        if self.stopped:
            self._status = "stopped"
            return self._status

        else:
            logger.debug('%s status undefined', self.__class__.__name__)
            self._status = 'undefined'
            return self._status

    def run(self):
        self.running = True
        self._time_zero = datetime.datetime.now()
        self._start_datetime = MachineDatetime.now().machineformat()

    def stop(self):
        self.stopped = True



class StatusThread(Status, Thread, Root):
    r"""
    Make use of threading.Event instances to report status of subclasses
    and alter their behaviour accordingly.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_event = Event()
        self._ready_event = Event()
        self._end_event = Event()

    def reset(self):

        self._start_event.clear()
        self._ready_event.clear()
        self._end_event.clear()

    @property
    def running(self):
        return self._start_event.is_set()

    @running.setter
    def running(self, value):
        if value is True:
            self._start_event.set()

    @property
    def ready(self):
        return self._ready_event.is_set()

    @ready.setter
    def ready(self, value):
        if value is True:
            self._start_event.set()

    @property
    def stopped(self):
        return self._end_event.is_set()

    @stopped.setter
    def stopped(self, value):
        if value is True:
            self._end_event.set()

class DescribedObject(Root):
    r"""
    An object that contains a ``description`` attribute.
    This is used to parse user option for the web interface.
    This way, users can send option to the different objects used.
    ``description`` is a dictionary with the fields "overview" and "arguments".
    "overview" is simply a string. "arguments" is a list of dictionaries. Each has the field:

     * name: The name of the argument as it is in "__init__"
     * description: "A user friendly description of the argument"
     * type: "number", "datetime", "daterange" and "string".
     * min, max and step: only for type "number",
       defines the accepted limits of the arguments
       as well as the increment in the user interface
     * default: the default value

    Each argument must match a argument in `__init__`.
    """
    _description = None

    def __init__(sef, *args, **kwargs):
        print(args)
        super().__init__(*args, **kwargs)

    @property
    def description(self): # pylint: disable=missing-function-docstring
        return self._description


class Base(Settings, StatusThread, Root):
    r"""
    Provide the functionality in Settings and Status simultaneously,
    which is the standard in IDOC.
    """
    def __init__(self, *args, **kwargs): # pylint: disable=useless-super-delegation
        super().__init__(*args, **kwargs)

