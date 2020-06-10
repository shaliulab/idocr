# https://stackoverflow.com/a/4761058
import sys
sys.path.append('../src')
from pathlib import Path
import logging
from tests import test_generic


from src.interface.main import Interface



class TestArduino(test_generic.TestGeneric, Interface):

    def __init__(self, *args, **kwargs):

        super(TestArduino, self).__init__(*args, **kwargs)
        Interface.__init__(self,
            arduino=True, track=False,
            mapping="mappings/main.csv", program="program/simplified_program5.csv",
            port="/dev/ttyACM0",
            reporting=False, config="config.yml", duration=120
        )
        self.store = self.metadata_saver.store

    def test_(self):
        pass
