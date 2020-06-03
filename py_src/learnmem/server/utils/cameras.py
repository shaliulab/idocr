import logging
import os.path
import time

logger = logging.getLogger('pylon_camera')

def reset_pylon_camera():
    logger.warning('Running reset_pylon_camera.sh')
    script_path = './reset_pylon_camera.sh'
    os.system("bash {}".format(script_path))
    time.sleep(5)
