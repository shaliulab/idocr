# Standard library imports
import logging
import cv2
# Local application imports
from .lmdt_utils import setup_logging, _toggle_pin
import threading
import numpy as np
import tempfile
setup_logging()
import ipdb
import time
log = logging.getLogger(__name__)

class CLIGui():

    def __init__(self, interface):

        self.interface = interface
        self.result = None
        self.log = log
        self.live_feed_path = '/tmp/last_img.jpg'
            

    def create(self):
        """
        """
        
        pass
 
    def run(self):
        '''
        '''
        while not self.interface.exit.is_set() and self.result != 0:
            self.result = input('Proceed?: ')
            if not self.result in ['n', 'no','N', 'no']:
                try:
                    self.result = self.proceed()
                except Exception as e:
                    self.log.warning("result = ".format(self.result))
                    self.log.warning('Could not proceed')
                    self.log.exception(e)
                    break
            else:
                self.log.info('Not proceeding')
                self.result = 0
        
        self.close()
 

    def apply_updates(self):
        pass         

    def close(self):
        """
        Quit the GUI and run the interface.close() method
        This is the callback function of the X button in the window
        Note: this is the only method that closes the GUI
        """
        self.interface.answer = input('Save results? Y/n')
        if not self.interface.answer is None:
            self.interface.close()

    def display_feed(self):
        while not self.interface.exit.is_set() and type(self.interface.frame_color) is np.ndarray:
            # cv2.imshow('feed', self.interface.frame_color)
            # cv2.waitKey(1)
            
            try:
                cv2.imwrite(self.live_feed_path, self.interface.frame_color)
                time.sleep(1)
            except Exception as e:
                self.log.exception(e)
                print(self.interface.frame_color)


             

    def proceed(self):
        if not self.interface.play_event.is_set():
            self.interface.play()
            display_feed_thread = threading.Thread(target = self.display_feed)
            display_feed_thread.start()
            self.log.info('Play pressed')
            return 1
        elif not self.interface.arena_ok_event.is_set():
            self.interface.ok_arena()
            self.log.info('Arena ok pressed')
            return 1

        elif not self.interface.record_event.is_set():
            self.log.info('Record pressed')
            self.interface.record()
            return 1
        else:
            return 0
    

CLIGui.toggle_pin = _toggle_pin