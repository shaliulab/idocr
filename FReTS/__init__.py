import os.path
import sys
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(Path(ROOT_DIR, 'src').__str__())
STATIC_DIR = 'static'
