import os.path
from pathlib import Path
import sys

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = Path(PROJECT_DIR, 'LeMDT').__str__()
UTILS_DIR = Path(ROOT_DIR, 'utils').__str__()

STATIC_DIR = Path(PROJECT_DIR, 'static').__str__()
sys.path.append(Path(ROOT_DIR).__str__())

