# https://stackoverflow.com/a/4761058
import sys
sys.path.append('../src')
import unittest
from pathlib import Path
import logging
from tests import test_generic
from src.interface.main import Interface
from src.camera.main import Tracker



class TestCamera(test_generic.TestGeneric, Interface):

    def __init__(self, *args, **kwargs):

        super(TestCamera, self).__init__(*args, **kwargs)
        Interface.__init__(self,
            arduino=False, track=True,
            camera='pylon', gui="tkinter",
            reporting=False, config="config.yml", duration=120
        )
        self.store = self.data_saver.store
    
    # def test_camera_exists(self):
    #     test_result = False:
        
    #     try:
    #         Tracker(self, self.canera, self.video)
    #         test_result = True
    #     except Exception:

        
