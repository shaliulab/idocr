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
        self.menus = {
            "general": ['change settings', 'open camera and start tracker', 'confirm', 'record', 'quit'],
            "settings" : ['name odors', 'change fps', 'change acquisition time', 'return']
            }
        self.effects = {
            "general": [None, 'tracker starting', 'settings confirmed', 'recording starting', 'saving odor names', 'quitting'],
            "settings": ['renaming odors', None, None, None]
        }
            
    def let_user_pick(self, menu_name):
        print("Please choose:")
        options = self.menus[menu_name]
        for idx, element in enumerate(options):
            print("{}: {}".format(idx+1,element))
        i = input("Enter number: ")

        try:
            if 0 < int(i) <= len(options):
                effect = self.effects[menu_name][int(i)-1]
                if not effect is None:
                    self.log.info(effect.format(""))
                return int(i)
        except Exception as e:
            self.log.warning(e)
        return None


    def create(self):
        """
        """
        
        pass
 
    def run(self):
        '''
        '''

        menu_name = "general"
        self.answer = self.let_user_pick(menu_name)
        while not self.interface.exit.is_set() and not (menu_name == "general" and self.answer == len(self.menus["general"])):

            try:

                self.proceed(menu_name, self.answer)

                if self.answer == 1 and menu_name == "general":
                    menu_name = "settings"
                elif self.answer == len(self.menus["settings"]) and menu_name == "settings":
                    menu_name = "general"

                self.answer = self.let_user_pick(menu_name)
                

            except Exception as e:
                self.log.warning("answer = {}".format(self.answer))
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

    
    def name_odors(self):
        self.interface.odor_A = input('Name of odor A: ')
        self.interface.odor_B = input('Name of odor B: ')
             

    def proceed(self, menu_name, answer):
        
        if menu_name == "general":
            if not self.interface.play_event.is_set() and answer == 2:
                self.interface.play()
                display_feed_thread = threading.Thread(target = self.display_feed)
                display_feed_thread.start()
                return 1
            elif not self.interface.arena_ok_event.is_set() and answer == 3:
                self.interface.ok_arena()
                return 1

            elif not self.interface.record_event.is_set() and answer == 4:
                self.interface.record()
                return 1

            elif answer >= len(self.menus[menu_name]) or answer is None:
                self.log.warning("Invalid answer entered")
                pass

        elif menu_name == "settings":
            if answer == 1:
                self.name_odors()
                return 1
            
            elif answer == 2:
                new_fps = int(input("Enter new FPS: "))
                self.interface.tracker.stream.set_fps(new_fps)
                self.log.warning("Change of fps not implemented")
                return 1

            elif answer == 3:
                new_acquisition_time = int(input("Enter new acquisition time: "))
                self.interface.tracker.stream.set_acquisition_time(new_acquisition_time)
                return 1

            elif answer == 4:
                return 1

            elif answer >= len(self.menus[menu_name]):
                pass
    

CLIGui.toggle_pin = _toggle_pin