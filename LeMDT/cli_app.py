# Standard library imports
import logging
import os
import subprocess
import threading
import tempfile
import time


# Local application imports
import cv2
import numpy as np
from .lmdt_utils import _toggle_pin
from . import PROJECT_DIR


class CLIGui():

    def __init__(self, interface):

        self.interface = interface
        self.answer = None
        self.log = self.interface.getLogger(__name__)
        self.live_feed_path = '/tmp/last_img.jpg'
        programs = os.listdir(os.path.join(PROJECT_DIR, "programs"))
        # print(programs)
        self.menus = {
            "general": ['open camera and start tracker', 'camera settings', 'load program', 'name odors', 'confirm', 'record', 'analyze with R', 'quit'],
            "settings" : ['change fps', 'change acquisition time', 'return'],
            "programs" : programs + ['return']
            }
        self.effects = {
            "general": ['tracker starting', 'settings confirmed', 'paradigm loaded', 'saving odor names', 'confirmed' , 'recording starting', 'launching R', 'quitting'],
            "settings": [None, None, None],
            "programs" : ['Loaded {}'.format(e) for e in self.menus['programs']] + [None]
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

                success = self.proceed(menu_name, self.answer)
                self.display_log(success, menu_name)

                
                key_too_large = self.answer > len(self.menus[menu_name])

                if self.answer == 2 and menu_name == "general":
                    menu_name = "settings"

                elif self.answer == 3 and menu_name == "general":
                    menu_name = "programs"

                elif not success:
                    menu_name = "general"

                elif success and menu_name == 'programs':
                    menu_name = "general"
                
                elif key_too_large:
                    self.log.warning('Sorry, the number you entered does not match any option. Please enter a valid number!')


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
        self.interface.save_results_answer = input('Save results (Y/N): ')
        if not self.interface.save_results_answer == '':
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
        switch_menu = self.answer == len(self.menus[menu_name])
        if switch_menu:
            return False
                
                
        if menu_name == "general":
            if not self.interface.play_event.is_set() and answer == 1:
                self.interface.play()
                display_feed_thread = threading.Thread(target = self.display_feed)
                display_feed_thread.start()
                subprocess.call(['python',  '-m',  'webbrowser',  "file:///tmp/last_img.jpg"])
                return True
            
            elif answer == 3:
                pass
                # handled by its submenu

            elif answer == 4:
                self.name_odors()
                return True

            elif not self.interface.arena_ok_event.is_set() and answer == 5:

                settings = self.interface.get_settings()
                self.log.info('Acquistion time: {}'.format(settings[0]))
                self.log.info('FPS: {}'.format(settings[1]))
                self.log.info('Odors: {}'.format(' and '.join(settings[2])))
                self.log.info('Program path: {}'.format(settings[3]))
                confirm  = input('Press N if there is something wrong in the live feed or the settings above: ')
                if confirm != 'N':
                    self.interface.ok_arena()
                    return True
                else:
                    return False

            elif not self.interface.record_event.is_set() and answer == 6:
                self.interface.record()
                return True

            elif not self.interface.record_event.is_set() and answer == 7:
                self.log.warning('Not implemented')
                return False


            elif answer >= len(self.menus[menu_name]) or answer is None:
                self.log.warning("Invalid answer entered")
                return False

        elif menu_name == 'programs':

        # new_program_path = input('Please enter a path to a programs csv file: ')
            self.interface.program_path = self.menus['programs'][self.answer-1]
            self.interface.load_and_apply_config()
            self.interface.device.prepare('exit')
            self.interface.device.get_paradigm_human_readable()
            return True



        elif menu_name == "settings":

            if answer == 1:
                new_fps = int(input("Enter new FPS: "))
                while new_fps <= 2:
                    self.log.warning('Please provide a new value > 2')
                    success = False
                    new_fps = int(input("Enter new FPS: "))

                self.interface.tracker.stream.set_fps(new_fps)
                # self.log.warning("Change of fps not implemented")
                return True

            elif answer == 2:
                new_acquisition_time = int(input("Enter new acquisition time: "))
                self.interface.tracker.stream.set_acquisition_time(new_acquisition_time)
                return True


    def display_log(self, success, menu_name):
        if success:
            try:
                    effect = self.effects[menu_name][self.answer-1]
                    if not effect is None:
                        self.log.info(effect.format(""))
                    else:
                        self.log.info(effect)
                    
                    time.sleep(2)
            except Exception as e:
                self.log.warning(e)


    

CLIGui.toggle_pin = _toggle_pin