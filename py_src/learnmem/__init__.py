#import sys
import os.path
from pathlib import Path

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
STATIC_DIR, UTILS_DIR = [Path(PROJECT_DIR, *folder).__str__() for folder in [["static"], ["utils"]]]
#sys.path.append(ROOT_DIR)
name = 'LeMDT'

