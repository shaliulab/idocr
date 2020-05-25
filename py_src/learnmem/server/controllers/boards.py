import logging

from pyfirmata import Arduino, ArduinoMega

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ArduinoDummy:
    r"""
    A dummy class to be passed to a Controller class for debugging purposes
    """

    board_compatible = "ArduinoDummy"

    def __init__(self, devport):
        self._devport = devport
        logger.info("Initialized dummy Arduino on port %s", self._devport)


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
