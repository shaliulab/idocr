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
import subprocess

class CLIGui():

    def __init__(self, interface):

        self.interface = interface
        self.answer = None
        self.log = self.interface.getLogger(__name__)
        self.live_feed_path = '/tmp/last_img.jpg'
        self.menus = {
            "general": ['open camera and start tracker', 'change settings', 'load program', 'name odors', 'confirm', 'record', 'quit'],
            "settings" : ['change fps', 'change acquisition time', 'return']
            }
        self.effects = {
            "general": ['tracker starting', 'settings confirmed', 'paradigm loaded', 'saving odor names', 'confirmed' , 'recording starting', 'quitting'],
            "settings": [None, None, None]
        }
            
    def let_user_pick(self, menu_name):
        print("Please choose:")
        options = self.menus[menu_name]
        for idx, element in enumerate(options):
            print("{}: {}".format(idx+1,element))
        i = input("Enter number: ")
        return int(i)

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

                if self.answer == 2 and menu_name == "general":
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
        
        options = self.menus[menu_name][answer-1]
        sucess = False

        if menu_name == "general":
            if not self.interface.play_event.is_set() and answer == 1:
                self.interface.play()
                display_feed_thread = threading.Thread(target = self.display_feed)
                display_feed_thread.start()
                subprocess.call(['python',  '-m',  'webbrowser',  "file:///tmp/last_img.jpg"])
                success = True
            
            elif answer == 3:
                
                new_program_path = input('Please enter a path to a programs csv file: ')
                self.interface.program_path = new_program_path
                self.interface.load_and_apply_config()
                self.interface.device.prepare('exit')
                self.interface.device.get_paradigm_human_readable()
                success = True

            elif answer == 4:
                self.name_odors()
                success = True

            elif not self.interface.arena_ok_event.is_set() and answer == 5:

                settings = self.interface.get_settings()
                self.log.info('Acquistion time: {}'.format(settings[0]))
                self.log.info('FPS: {}'.format(settings[1]))
                self.log.info('Odors: {}'.format(' and '.join(settings[2])))
                self.log.info('Program path: {}'.format(settings[3]))
                confirm  = input('Press N if there is something wrong in the live feed or the settings above: ')
                if confirm != 'N':
                    self.interface.ok_arena()

                success = True

            elif not self.interface.record_event.is_set() and answer == 6:
                self.interface.record()
                success = True

            elif answer >= len(self.menus[menu_name]) or answer is None:
                self.log.warning("Invalid answer entered")
                success = False


        elif menu_name == "settings":

            if answer == 1:
                new_fps = int(input("Enter new FPS: "))
                while new_fps <= 2:
                    self.log.warning('Please provide a new value > 2')
                    success = False
                    new_fps = int(input("Enter new FPS: "))

                self.interface.tracker.stream.set_fps(new_fps)
                # self.log.warning("Change of fps not implemented")
                success = True

            elif answer == 2:
                new_acquisition_time = int(input("Enter new acquisition time: "))
                self.interface.tracker.stream.set_acquisition_time(new_acquisition_time)
                success = True
            
            elif answer >= len(self.menus[menu_name]):
                self.log.warning('Sorry, the number you entered does not match any option. Please enter a valid number!')
                success = False
        

        if success:
            try:
                    effect = self.effects[menu_name][int(answer)-1]
                    if not effect is None:
                        self.log.info(effect.format(""))
                    return 1
            except Exception as e:
                self.log.warning(e)
        else:
            return 0

    

CLIGui.toggle_pin = _toggle_pin