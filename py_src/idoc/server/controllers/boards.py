r"""
Boards that a Controller class can drive with the program generated
in a Programmer class.
For now, only a dummy board that just logs to the screen and adaptor classes
from pyfirmata are available.
"""
import logging


from pyfirmata import Arduino, ArduinoMega

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# pylint: disable=too-few-public-methods

class PIN():

    def __init__(self, signal, number, mode):
        r"""
        """
        self._signal = signal
        self._number = number
        self._mode = mode

    @staticmethod
    def write(value):
        logger.debug(value)

class ArduinoDummy:
    """
    A dummy class to be passed to a Controller class for debugging purposes
    """

    board_compatible = "ArduinoDummy"

    def __init__(self, devport):
        self._devport = devport
        logger.info("Initialized dummy Arduino on port %s", self._devport)


    def get_pin(self, string):

        signal = string.split(":")[0]
        number = int(string.split(":")[1])
        mode = string.split(":")[2]

        pin = PIN(signal, number, mode)
        return pin

    def exit(self):
        pass


class ArduinoBoard(Arduino):
    r"""
    A pyfirmata class with a convenience attribute
    to select the right ControllerThreads
    """
    board_compatible = "ArduinoX"


class ArduinoMegaBoard(ArduinoMega):
    r"""
    A pyfirmata class with a convenience attribute
    to select the right ControllerThreads
    """
    board_compatible = "ArduinoX"
