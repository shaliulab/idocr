import sys
import os.path
from pathlib import Path

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR, STATIC_DIR, UTILS_DIR = [Path(PROJECT_DIR, *folder).__str__() for folder in [["LeMDT"], ["static"], ["LeMDT", "utils"]]]
sys.path.append(ROOT_DIR)