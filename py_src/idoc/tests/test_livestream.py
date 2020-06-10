# https://stackoverflow.com/a/4761058
import sys
import unittest
from pathlib import Path
import logging
import os
import threading
import time
import signal
from tests import test_generic
from src.interface.main import Interface
sys.path.append('../src')
from definitions import ROOT_DIR

class TestLiveStream(unittest.TestCase, Interface):

    def __init__(self, *args, **kwargs):


        super().__init__(*args, **kwargs)
        Interface.__init__(self,
        #arduino=True,
        #mapping=Path(ROOT_DIR, "mappings/main.csv"), program=Path(ROOT_DIR, "programs/simplified_program5.csv"), port="/dev/ttyACM0",
        track=True,
        camera='opencv', gui="tkinter", video = None,
        reporting=False, config=Path(ROOT_DIR, "config.yml"), duration=120
        )
        self.prepare()

    def send_signal(self, pid):
        time.sleep(.5)
        os.kill(pid, signal.SIGINT)

    def launch_and_send_exit(self):

        pid = os.getpid()
        press_control_c_thread = threading.Thread(
            name='press_control_c',
            target=self.send_signal,
            args=([pid]),
        )
        
        press_control_c_thread.start()
        self.start()

    
    def test_exit_signal(self):
        self.launch_and_send_exit()
        self.exit.wait()
        # give time to stop once signal is received
        time.sleep(.2)

        #self.assertFalse(self.arduino_thread.is_alive())
        self.assertFalse(self.tracker_thread.is_alive())

        
    # def test_camera_exists(self):
    #     test_result = False:
        
    #     try:
    #         Tracker(self, self.canera, self.video)
    #         test_result = True
    #
