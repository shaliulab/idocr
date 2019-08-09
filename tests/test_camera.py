# https://stackoverflow.com/a/4761058
import logging
from pathlib import Path
import sys
import unittest

from . import test_generic
from LeMDT.LeMDT.interface import Interface
from LeMDT.LeMDT.interface import Tracker
from pypylon import pylon, genicam


class TestCamera(unittest.TestCase, Interface):

    def __init__(self, *args, **kwargs):

        interface = Interface(
             arduino = False, track = True,
             camera = 'pylon', duration = 10
        )
        
        self.tracker = Tracker(interface=interface, camera=interface.camera)
        unittest.TestCase.__init__(self, *args, **kwargs)

    def test_camera_can_be_loaded(self):
        """
        Make sure that the camera can be loaded
        """
        self.tracker.load_camera()
    
    def test_camera_can_read_frames(self):

        self.tracker.load_camera()
        self.tracker.stream.read_frame()
