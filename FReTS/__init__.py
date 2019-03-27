import os.path
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
import sys
from pathlib import Path
sys.path.append(Path(ROOT_DIR, 'src').__str__())
