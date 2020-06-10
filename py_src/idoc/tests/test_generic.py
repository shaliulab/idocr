# # https://stackoverflow.com/a/4761058
# import sys
# sys.path.append('../src')
# import unittest
# from pathlib import Path
# import logging
# from src.interface.main import Interface


# class TestGeneric(unittest.TestCase):

#     def __init__(self, *args, **kwargs):

#         super(TestGeneric, self).__init__(*args, **kwargs)
#         self.store = None

#     def test_writable_store(self):
        
#         # Check dir exists
#         directory = Path(self.store).parents[0]
#         self.assertTrue(directory.is_dir())

#         # Check dir is writable
#         # https://stackoverflow.com/questions/2113427/determining-whether-a-directory-is-writeable
#         writable = False
#         try:
#             p = Path(directory, '.tmp.py')
#             p.touch()
#             p.unlink()
#             writable = True
#         except Exception:
#             logging.error("Trying to write the cache to a non writable dir")
        
#         self.assertTrue(writable)
