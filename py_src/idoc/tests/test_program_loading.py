# https://stackoverflow.com/a/4761058
import copy
import logging
from pathlib import Path
import sys
import unittest

from . import test_generic
from LeMDT import PROJECT_DIR
from LeMDT.LeMDT.interface import Interface
from LeMDT.LeMDT.interface import Tracker
from pypylon import pylon, genicam


class TestProgramLoading(unittest.TestCase, Interface):

    def __init__(self, *args, **kwargs):

        interface = Interface(
             arduino = True, port = '/dev/ttyACM0',
             track = True, camera = 'pylon',
             duration = 1, gui = 'tkinter'
        )
        
        interface.init_components()
        self.interface = interface
        unittest.TestCase.__init__(self, *args, **kwargs)


    def test_loading_program_updates_threads(self):
        """
        Make sure that selecting a new file
        regenerates the threads i.e. we dont stay
        with the defaults
        """
        program_path = Path(PROJECT_DIR, 'programs', 'test_28_march.csv').as_posix()
        self.interface.device.program_path = program_path

        before_threads = {**self.interface.device.threads}
        after_threads = self.interface.gui.load_program(program_path)       
        self.assertNotEqual(before_threads, after_threads)
