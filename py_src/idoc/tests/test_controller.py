import unittest
from idoc.server.controllers.controllers import Controller



class TestController(unittest.TestCase):

    _mapping_path = "/1TB/Cloud/Lab/Gitlab/idoc/py_src/mappings/mega.csv"

    def setUp(self):

        self.controller = Controller(mapping_path=self._mapping_path, program_path=None, board="ArduinoDummy", port="")

    def test_load_mapping(self):

        self.controller.load_mapping(self._mapping_path)
        self.assertTrue(len(self.controller._mapping) > 1)
