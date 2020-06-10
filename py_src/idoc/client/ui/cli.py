# Standard library imports
import logging
import math
import os
import subprocess
from threading import Thread, Event
import tempfile
import time
import urllib.request, urllib.error, urllib.parse

# Local application imports
import cv2
import numpy as np
from learnmem import PROJECT_DIR
from learnmem.configuration import LearnMemConfiguration
from learnmem.client.analysis.analysis import RSession
from learnmem.client.utils.device_scanner import DeviceScanner
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


class CLIGui():

    _exit_event = Event()
    _error_event = Event()

    def __init__(self):

        CFG = LearnMemConfiguration()

        self.odor_A = CFG.content["experiment"]["odor_A"]
        self.odor_B = CFG.content["experiment"]["odor_B"]
        self.answer = None

        # print(programs)
        self.menus = {
            "general": ['open camera, start tracker and run main valve', 'camera settings and adaptation time', 'load program', 'name odors', 'confirm', 'record', 'analyze with R', 'quit'],
            "settings" : ['change fps', 'change acquisition_time', 'change adaptation_time (minutes)', 'return'],
            "programs" : list(self.programs.values()) + ['return'],
            "Rsettings": ['run', 'experiment_folder', 'decision_zone_mm', 'min_exits_required', 'max_time_minutes', 'return']
            }
        self.effects = {
            "general": ['tracker starting', 'settings confirmed', 'paradigm loaded', 'saving odor names', 'confirmed' , None, 'launching R', 'quitting'],
            "settings": [None, None, None, None],
            "programs" : ['Loaded {}'.format(e) for e in self.menus['programs']] + [None]

        }

        self.menu_name = "general"
        self.answer = self.let_user_pick(self.menu_name)
        self.r_session = RSession()

    @property
    def programs(self):
        return self._device.info["programs"]

    def let_user_pick(self, menu_name):
        print("Please choose:")
        options = self.menus[menu_name]
        for idx, element in enumerate(options):
            print("{}: {}".format(idx+1,element))
        i = input("Enter number: ")
        if i == '':
            i = self.let_user_pick(menu_name)

        while not RepresentsInt(i):
            logger.warning('You entered answer: {}'.format(i))
            logger.warning('This is not valid. Try again!')
            i = self.let_user_pick(menu_name)

        result = int(i)
        return result

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
                logger.warning('Sorry, the number you entered does not match any option. Please enter a valid number!')

            self.answer = self.let_user_pick(menu_name)
            #print(self.answer)
            self.menu_name = menu_name

            if not menu_name == "general" and self.answer == len(self.menus["general"]):
                self._error_event.set()

        except Exception as e:
            logger.warning("answer = %s", self.answer)
            logger.warning('I do not understand that answer')
            logger.warning(e)
            # self._error_event.set()

        if self._error_event.is_set():
            self.close()

    def close(self):
        """
        Quit the GUI and close the remote control thread
        This is the callback function of the X button in the window
        Note: this is the only method that closes the GUI
        """
        answer = input('Save results (Y/N): ')
        self._device.close(answer)
        if answer == "Y":
            self.r_session.run()

        self._exit_event.set()



    def name_odors(self):
        self.odor_A = input('Name of odor A: ')
        self.odor_B = input('Name of odor B: ')


    def proceed(self, menu_name, answer):

        while len(self.menus[menu_name]) < answer-1:
            logger.warning('You entered answer: {}'.format(answer))
            logger.warning('This is not valid. Try again!')
            answer = self.let_user_pick(menu_name)

        options = self.menus[menu_name][answer-1]
        switch_menu = self.answer == len(self.menus[menu_name])
        if switch_menu:
            return False


        if menu_name == "general":
            if not self._device.info["play_event"] and answer == 1 and self._device.info["track"]:
                self._device.control("play")

                subprocess.call(['python',  '-m',  'webbrowser',  "file:///tmp/last_img.jpg"])
                return True

            elif answer == 3:
                pass
                # handled by its submenu

            elif answer == 4:
                self.name_odors()
                return True

            elif not self._device.info["arena_ok_event"] and answer == 5:

                logger.info(f'Acquistion time: {self._device.info["acquistion_time"]}')
                logger.info(f'FPS: {self._device.info["fps"]}')
                odors = " ".join([self._device.info["odor_A"], self._device.info["odor_B"]])

                logger.info(f'Odors: {odors}')

                logger.info(f'Program path: {self._device.info["program_path"]}')
                logger.info(f'Adaptation time: {self._device.info["adaptation_time"]}')
                confirm  = input('Press N if there is something wrong in the live feed or the settings above: ')
                if confirm != 'N':
                    self._device.control("ok_arena")
                    return True
                else:
                    return False

            elif not self._device.info["record_event"] and answer == 6:
                self._device.control("record")
                self.progress_bar(seconds=self._device.info["adaptation_seconds"], background=False, name='adaptation time', until_event="_exit_event")

                return True

            # elif answer >= len(self.menus[menu_name]) or answer is None:
            #     logger.warning("Invalid answer entered")
            #     return False

        elif menu_name == 'programs':

        # new_program_path = input('Please enter a path to a programs csv file: ')
            try:
                self._device.load_program(self.menus['programs'][self.answer-1])
            except IndexError:
                pass
            return True


        elif menu_name == 'Rsettings':

            if answer == 1:
                self.r_session.run()
                return True

            elif answer < len(self.menus[menu_name]):

                try:

                    param_name = self.menus[menu_name][answer-1]
                except IndexError:
                    pass

                param_value = int(input("Enter new {}: ".format(param_name)))
                # TODO Send settings to the r_session
                return True


        elif menu_name == "settings":

            settings_options = [e.split('(')[0] if len(e.split('(')) > 1 else e for e in self.menus[menu_name]]
            settings_options = [e.split(' ')[1] if len(e.split(' ')) > 1 else e for e in settings_options]

            if answer == settings_options.index('fps')+1:
                self.update_setting("fps")

            elif answer == settings_options.index('acquisition_time')+1:
                self.update_setting("acquisition_time")

            elif answer == settings_options.index('adaptation_time')+1:
                self.update_setting("adaptation_time")


    def prompt_new_value(self, info, param_name):

        old_value = info[param_name]
        logger.info('{} is set to {}'.format(param_name, old_value))
        value = float(input("Enter new {}: ".format(param_name)))
        # print(param_name)
        time.sleep(.2)
        return value

    def push_new_value(self, value, param_name):

        self._device.push(value, param_name)

    def update_setting(self, param_name, min=0, max=9999999999):

        new_value = self.prompt_new_value(self._device.info, param_name)
        while new_value < min or new_value > max:
            logger.warning(f'Please provide a value between {min} and {max}')
            new_value = self.prompt_new_value(self._device.info, param_name)

            self.push_new_value(new_value, param_name)


    def display_log(self, success, menu_name):
        if success:
            try:
                effect = self.effects[menu_name][self.answer-1]

                if not effect is None:
                    logger.info(effect.format(""))
                # else:
                #     logger.info(effect)

                time.sleep(2)
            except IndexError:
                pass
            except Exception as e:
                logger.warning(e)

    def progress_bar(self, seconds, background=True, until_event=None, name=''):

        event_done = Event()
        if background:
            progress_bar_thread = Thread(
                    name='progress_bar_main',
                    target=self.progress_bar_main,
                    kwargs={
                        "seconds": seconds,
                        "until_event": until_event,
                        "name": name

                        }
                )

            logger.debug('Background progress bar')
            progress_bar_thread.start()

        else:
            logger.debug('Foreground progress bar')
            self.progress_bar_main(seconds, until_event=until_event, name=name)

        return event_done

    def progress_bar_main(self, seconds, until_event=None, name=''):

        refresh_every_n_seconds = 1
        niters = max(math.ceil(seconds / refresh_every_n_seconds),0)

        if not until_event is None:
            while not until_event:
                time.sleep(0.5)

        logger.info('Running {}...'.format(name))

        try:
            from tqdm import tqdm
            iterator = tqdm(range(int(niters)))

        except ModuleNotFoundError:
            iterator = range(int(niters))

        for i in iterator:
            time.sleep(refresh_every_n_seconds)
            if getattr(self, until_event).is_set():
                break
