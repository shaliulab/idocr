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

import datetime
import logging
from threading import Thread, Event
import traceback

from learnmem.helpers import hours_minutes_seconds, iso_format, MachineDatetime
from learnmem.configuration import LearnMemConfiguration
from learnmem.server.utils.debug import IDOCException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Root:
    """
    Most abstract class, designed to implement defensive programming
    as instructed in https://rhettinger.wordpress.com/2011/05/26/super-considered-super/
    """
    _config = LearnMemConfiguration()


# TODO Implement it in a way so that settings from a submodule are not mixed with those
# of another submodule in the parent module self._settings
# i.e. instead of self._settings(update(submodule.settings))
# one could do self._settings[submodule.name] = submodule.settings
# and then update it using only the subdictionary
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


    def _add_submodule(self, name, submodule):
        self._submodules[name] = submodule
        self._settings[name] = submodule.settings

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
        r"""
        Update the existing settings without extending them.
        """
        # only update pairs with key under self._settings_keys
        new_settings = {k: settings[k] for k in self._settings if k in settings}
        self._settings.update(new_settings)

        # notify submodules
        self.send()

        logger.warning("Module %s with settings %s", self.__class__.__name__, self._settings)

    @settings.getter
    def settings(self):
        r"""
        Return updated settings of current class as well as all other
        instances listed in self._submodules.
        """
        # ask the dependent modules
        self.receive()
        self.update()
        return self._settings


    def send_recursive(self, module, settings):

        for submodule in module._submodules:
            for k in self._settings:
                print(self._settings)
                if k in module._submodules[submodule]._submodules:
                    print("===============")
                    print(self._submodules)
                    print(self.__class__.__name__)
                    print(module._submodules[submodule].__class__.__name__)
                    self.send_recursive(module._submodules[submodule], settings)
                else:
                    module._submodules[submodule]._settings = settings

    def send(self):
        r"""
        Send to depending modules the new settings sent by the user.
        """
        for name, submodule in self._submodules.items():
            if submodule is None:
                continue

            logger.warning("%s sending to %s", self.__class__.__name__, submodule.__class__.__name__)
            logger.warning(self._settings)
            self.send_recursive(self, self._settings)

    def receive(self):
        r"""
        Receive from depending modules settings that the user could change
        """
        for name, submodule in self._submodules.items():
            if submodule is None:
                continue

            logger.debug(
                "%s receiving from %s",
                self.__class__.__name__, submodule.__class__.__name__
            )
            logger.debug(submodule.settings)
            self._settings[name] = submodule.settings

    def update(self):
        """
        Update the properties using the values in the settings
        """
        for k in self._settings:
            if k in self._submodules:
                pass
            else:
                logger.debug("Updating self.%s to %s", k, self._settings[k])
                try:
                    setattr(self, k, self._settings[k])
                except AttributeError as error:
                    logger.warning("Cannot update self.%s to %s in class %s", k, self._settings[k], self.__class__.__name__)
                    logger.warning(error)
                    logger.warning(traceback.print_exc())



class Status(Root):
    """
    Report useful data and methods to learn and change the state of a class.
    Three state flags are available: ready, running and stopped.

    * reset()
    * run()
    * stop()
    * status
    * elapsed_time
    * elapsed_seconds
    * start_datetime
    * time_zero

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.running = False
        self.ready = False
        self.stopped = False
        self._time_zero = None
        self._time_init = MachineDatetime.now()
        self._start_datetime = None
        self.experiment_start = None

        self._status = "idle"

        self._info = {}
        self._info.update({
            "status": self._status,
            "elapsed_time": self.elapsed_time
        })


    def reset(self):
        """
        Set all state flags to False i.e. like at __init__
        """
        self.running = False
        self.ready = False
        self.stopped = False

    @property
    def elapsed_time(self):
        """
        Compute the number of seconds since running was set to True
        Return it in format HH:MM:SS.
        """

        if self._time_zero is None:
            return None

        time_diff = iso_format(
            hours_minutes_seconds(
                (datetime.datetime.now() - self._time_zero).seconds
            )
        )
        return time_diff

    @property
    def init_elapsed_seconds(self):
        if self._time_init is None:
            return None

        time_diff = (datetime.datetime.now() - self._time_init).total_seconds()
        return time_diff




    @property
    def elapsed_seconds(self):
        """
        Compute the number of seconds since running was set to True
        Return a float
        """
        if self._time_zero is None:
            return None

        time_diff = (datetime.datetime.now() - self._time_zero).total_seconds()
        return time_diff

    @property
    def experiment_elapsed_seconds(self):

        if self.experiment_start is None:
            return None

        time_diff = (datetime.datetime.now() - self.experiment_start).total_seconds()
        return time_diff



    @property
    def start_datetime(self):
        return self._start_datetime

    @property
    def time_zero(self):
        """
        Return a datetime.datetime object storing the timestamp
        when running was set to True.
        """

        try:
            return self._time_zero
        except KeyError:
            return None

    @time_zero.setter
    def time_zero(self, time_zero):
        self._time_zero = time_zero

    @property
    def status(self):
        return self._status

    @status.getter
    def status(self):
        """
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

        logger.debug('%s status undefined', self.__class__.__name__)
        self._status = 'undefined'
        return self._status

    def run(self):
        """
        Set running to True
        Populate _time_zero (datetime.datetime) and _start_datetime (str)
        Should be called from a subclass run method.
        """
        if self.running is True:
            logger.warning("%s is already running. Skipping", self.__class__.__name__)
            return

        self.running = True
        self._set_start_datetime()


    def _set_start_datetime(self):
        """
        Store a timestamp of the moment when running was set to True
        in type str with format YYYY-MM-DD_HH:MM:SS
        """
        start_date_time = MachineDatetime.now()
        self._start_datetime = start_date_time.machineformat()
        self._time_zero = start_date_time


    def stop(self):
        """
        Set the stopped flagged to True.
        All concurrently running methods should listen to this flag
        and react accordingly, tipically interrupting execution.
        Should be called from a subclass run method.
        """
        if self.stopped is True:
            logger.warning("%s is already stopped. Skipping", self.__class__.__name__)
            return

        self.stopped = True

class StatusThread(Status, Thread, Root):
    r"""
    Make use of threading.Event instances to report status of subclasses
    and alter their behaviour accordingly.
    """

    def __init__(self, *args, **kwargs):
        self._start_event = Event()
        self._ready_event = Event()
        self._end_event = Event()
        super().__init__(*args, **kwargs)

    def reset(self):

        self.stop()
        self._start_event.clear()
        self._ready_event.clear()
        self._end_event.clear()


    def run(self):
        super().run()
        Thread.run(self)


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
            self._ready_event.set()

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

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

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
        self._validate()


    def _validate(self):
        """
        Make sure the _valid_actions have a corresponding method
        """

        valid_actions = getattr(self, "_valid_actions", None)
        if valid_actions is not None:
            for action in valid_actions:
                if not getattr(self, action, False):
                    raise IDOCException("Action %s of class %s does not have a matching method" % (action, self.__class__.__name__))
