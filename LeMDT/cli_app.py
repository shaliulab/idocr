# Standard library imports
import logging
import cv2
# Local application imports
from .lmdt_utils import _toggle_pin
import threading
import numpy as np
import tempfile
import ipdb
import time

class CLIGui():

    def __init__(self, interface):

        self.interface = interface
        self.answer = None
        self.log = self.interface.getLogger(__name__)
        self.live_feed_path = '/tmp/last_img.jpg'
        self.options = ['open camera and start tracker', 'confirm settings', 'record', 'name odors', 'quit']
            
    def let_user_pick(self):
        print("Please choose:")
        for idx, element in enumerate(self.options):
            print("{}: {}".format(idx+1,element))
        i = input("Enter number: ")
        try:
            if 0 < int(i) <= len(self.options):
                return int(i)
        except:
            pass
        return None


    def create(self):
        """
        """
        
        pass
 
    def run(self):
        '''
        '''

        self.answer = self.let_user_pick()
        while not self.interface.exit.is_set() and self.answer != len(self.options):

            try:
                self.proceed(self.answer)
                self.answer = self.let_user_pick()
            except Exception as e:
                self.log.warning("answer = ".format(self.answer))
                self.log.warning('I do not understand that answer')
                self.log.exception(e)
                break
    
        self.close()
 

    def apply_updates(self):
        pass         

    def close(self):
        """
        Quit the GUI and run the interface.close() method
        This is the callback function of the X button in the window
        Note: this is the only method that closes the GUI
        """
        self.interface.save_results_answer = input('Press N to discard results, any other key will keep them: ')
        if not self.interface.save_results_answer is None:
            self.interface.close()

    def display_feed(self):
        while not self.interface.exit.is_set() and type(self.interface.frame_color) is np.ndarray:
            # cv2.imshow('feed', self.interface.frame_color)
            # cv2.waitKey(1)
            
            try:
                cv2.imwrite(self.live_feed_path, self.interface.frame_color)
                time.sleep(.2)
            except Exception as e:
                self.log.exception(e)
                print(self.interface.frame_color)


    
    def name_odors(self):
        self.interface.odor_A = input('Name of odor A: ')
        self.interface.odor_B = input('Name of odor B: ')
             

    def proceed(self, answer):
        if not self.interface.play_event.is_set() and answer == 1:
            self.interface.play()
            display_feed_thread = threading.Thread(target = self.display_feed)
            display_feed_thread.start()
            self.log.info('Play pressed')
            return 1
        elif not self.interface.arena_ok_event.is_set() and answer == 2:
            self.interface.ok_arena()
            self.log.info('Arena ok pressed')
            return 1

        elif not self.interface.record_event.is_set() and answer == 3:
            self.log.info('Record pressed')
            self.interface.record()
            return 1

        elif answer == 4:
            self.name_odors()
            return 1

        elif answer == len(self.options):
            pass
    

CLIGui.toggle_pin = _toggle_pin