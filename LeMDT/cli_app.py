# Standard library imports
import logging
import math
import os
import subprocess
import threading
import tempfile
import time
from tqdm import tqdm

# Local application imports
import cv2
import numpy as np
from .lmdt_utils import _toggle_pin
from . import PROJECT_DIR
import ipdb


def RepresentsInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False


class CLIGui():

    def __init__(self, interface):

        self.interface = interface
        self.answer = None
        self.log = self.interface.getLogger(__name__)
        self.live_feed_path = '/tmp/last_img.jpg'
        programs = os.listdir(os.path.join(PROJECT_DIR, "programs"))
        # print(programs)
        self.menus = {
            "general": ['open camera, start tracker and run main valve', 'camera settings and adaptation time', 'load program', 'name odors', 'confirm', 'record', 'analyze with R', 'quit'],
            "settings" : ['change fps', 'change acquisition_time', 'change adaptation_time (minutes)', 'return'],
            "programs" : programs + ['return'],
            "Rsettings": ['run', 'experiment_folder', 'decision_zone_mm', 'min_exits_required', 'max_time_minutes', 'return']
            }
        self.effects = {
            "general": ['tracker starting', 'settings confirmed', 'paradigm loaded', 'saving odor names', 'confirmed' , None, 'launching R', 'quitting'],
            "settings": [None, None, None, None],
            "programs" : ['Loaded {}'.format(e) for e in self.menus['programs']] + [None]

        }

        self.menu_name = "general"
        self.answer = self.let_user_pick(self.menu_name)
        self.shall_I_stop = False


        self.Rsession = None
            
    def let_user_pick(self, menu_name):
        print("Please choose:")
        options = self.menus[menu_name]
        for idx, element in enumerate(options):
            print("{}: {}".format(idx+1,element))
        i = input("Enter number: ")
        if i == '':
            i = self.let_user_pick(menu_name)
        
        while not RepresentsInt(i):
            self.log.warning('You entered answer: {}'.format(i))
            self.log.warning('This is not valid. Try again!')
            i = self.let_user_pick(menu_name)
        
        result = int(i)
        return result

    def create(self):
        """
        """
        
        pass
 
    def run(self):
        '''
        '''
       
        try:
            menu_name = self.menu_name

            success = self.proceed(menu_name, self.answer)
            self.display_log(success, menu_name)

            
            key_too_large = self.answer > len(self.menus[menu_name])

            if self.answer == 2 and menu_name == "general":
                menu_name = "settings"

            elif self.answer == 3 and menu_name == "general":
                menu_name = "programs"

            elif self.answer == 7 and menu_name == "general":
                menu_name = "Rsettings"


            elif not success:
                menu_name = "general"

            elif success and menu_name == 'programs':
                menu_name = "general"
            
            elif key_too_large:
                self.log.warning('Sorry, the number you entered does not match any option. Please enter a valid number!')


            self.answer = self.let_user_pick(menu_name)
            print(self.answer)
            self.menu_name = menu_name


            self.shall_I_stop = (menu_name == "general" and self.answer == len(self.menus["general"]))
            print(self.shall_I_stop)

        except Exception as e:
            self.log.warning("answer = {}".format(self.answer))
            self.log.warning('I do not understand that answer')
            self.log.exception(e)
            self.shall_I_stop = True
            
        if self.shall_I_stop:
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
        
        while len(self.menus[menu_name]) < answer-1:
            self.log.warning('You entered answer: {}'.format(answer))
            self.log.warning('This is not valid. Try again!')
            answer = self.let_user_pick(menu_name)
            
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
                self.log.info('Adaptation time: {}'.format(settings[4]))
                confirm  = input('Press N if there is something wrong in the live feed or the settings above: ')
                if confirm != 'N':
                    self.interface.ok_arena()
                    return True
                else:
                    return False

            elif not self.interface.record_event.is_set() and answer == 6:
                self.interface.record()
                return True

            # elif answer >= len(self.menus[menu_name]) or answer is None:
            #     self.log.warning("Invalid answer entered")
            #     return False

        elif menu_name == 'programs':

        # new_program_path = input('Please enter a path to a programs csv file: ')
            try:
                self.interface.program_path = self.menus['programs'][self.answer-1]
            except IndexError:
                pass

            self.interface.load_and_apply_config()
            self.interface.device.prepare('exit')
            self.interface.device.get_paradigm_human_readable()
            return True


        elif menu_name == 'Rsettings':

            if answer == 1:
                self.interface.Rsession.run()
                return True
            
            elif answer < len(self.menus[menu_name]):

                try:
                    
                    param_name = self.menus[menu_name][answer-1]
                except IndexError:
                    pass

                param_value = int(input("Enter new {}: ".format(param_name)))
                setattr(self.inteface, param_name, param_value)
                setattr(self.interface.Rsession, param_name, param_value)
                


                # if param_value is str:
                    # if param_value.replace('.', 1).isdigit(): param_value = float(param_value)
                    # {
                    #     "experiment_folder" : self.interface.tracker.saver.output_dir,
                    #     "decision_zone_mm" : self.interface.decision_zone_mm,
                    #     "min_exits_required" : self.interface.min_exits_required,
                    #     "max_time_minutes" : self.inteface.max_time_minutes
                    # }

         
                return True


        elif menu_name == "settings":

            settings_options = [e.split('(')[0] if len(e.split('(')) > 1 else e for e in self.menus[menu_name]]
            settings_options = [e.split(' ')[1] if len(e.split(' ')) > 1 else e for e in settings_options]

            if answer == settings_options.index('fps')+1:
                new_fps = self.prompt_new_value(self.interface.tracker.stream, 'fps')
                while new_fps <= 2:
                    self.log.warning('Please provide a new value > 2')
                    success = False
                    new_fps = self.prompt_new_value(self.interface.tracker.stream, 'fps')
                return True

            elif answer == settings_options.index('acquisition_time')+1:
                self.prompt_new_value(self.interface.tracker.stream, 'acquisition_time')
                return True

            elif answer == settings_options.index('adaptation_time')+1:
                self.prompt_new_value(self.interface, 'adaptation_time')
                

    def display_log(self, success, menu_name):
        if success:
            try:
                effect = self.effects[menu_name][self.answer-1]
                    
                if not effect is None:    
                    self.log.info(effect.format(""))
                # else:
                #     self.log.info(effect)
                
                time.sleep(2)
            except IndexError:
                pass
            except Exception as e:
                self.log.warning(e)

    
    def prompt_new_value(self, instance, param_name):
        old_value = getattr(instance, 'get_' +param_name)()
        self.log.info('{} is set to {}'.format(param_name, old_value))
        value = float(input("Enter new {}: ".format(param_name)))
        # print(param_name)
        getattr(instance, 'set_' +param_name)(value)
        self.log.info('{} is now changed to {}'.format(param_name, value))
        time.sleep(1)
        return value


    def progress_bar(self, seconds, background=True, until_event=None, name = ''):

        event_done = threading.Event()
        if background:
            progress_bar_thread = threading.Thread(
                    name='progress_bar_main',
                    target=self.progress_bar_main,
                    kwargs={
                        "seconds": seconds,
                        "until_event": until_event,
                        "event_done": event_done,
                        "name": name

                        }
                )

            self.log.debug('Background progress bar')          
            progress_bar_thread.start()
        

        else:
            self.log.debug('Foreground progress bar')          
            self.progress_bar_main(seconds, until_event = until_event, event_done = event_done, name = name)

        return event_done




    def progress_bar_main(self, seconds, until_event=None, event_done=None, name=''):


        refresh_every_n_seconds = 1
        niters = max(math.ceil(seconds / refresh_every_n_seconds),0)
        
        if not until_event is None:
            while not until_event.is_set():
                self.interface.exit.wait(.5)

        self.log.info('Running {}...'.format(name))

        for i in tqdm(range(int(niters))):
            self.interface.exit.wait(refresh_every_n_seconds)
            if self.interface.exit.is_set():
                break
        
        event_done.set()
        


        
        


    

CLIGui.toggle_pin = _toggle_pin