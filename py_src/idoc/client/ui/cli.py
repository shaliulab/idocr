#! /home/vibflysleep/anaconda3/envs/idoc/bin/python

# Standard library imports
import logging
import math
import os
import sys
import signal
import subprocess
from threading import Thread, Event
import tempfile
import time
import traceback
import urllib.request, urllib.error, urllib.parse
import warnings
import webbrowser

# Local application imports
import cv2
import numpy as np

from idoc.configuration import IDOCConfiguration
from idoc.client.analysis.analysis import RSession
from idoc.client.utils.device_scanner import DeviceScanner
from idoc.debug import IDOCException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CliUI():
    """
    Control IDOC interactively with a command line interface
    sending HTTP requests to the server API on behalf of the user.
    """

    _last_img_annot = "/tmp/last_img_annot.png"

    def __init__(self, device_id):

        self._config = IDOCConfiguration()
        self._device_id = device_id
        self._ds = DeviceScanner()
        self._ds.start()
        self._answer = 0
        # self._func = None
        self.running = False
        self.stopped = False

        self._menus = {
            "root": [
                ('WARM UP', self.warm_up, "root"),
                ('CHANGE CONFIGURATION', None, "settings"),
                ('LOAD PARADIGM', None, "paradigms"),
                ('CHECK', self.check, "root"),
                ('START', self.start_experiment, "root"),
                ('ANALYZE', self.analyze, "root"),
                ('STOP', self.stop, "root"),
                ('CLEAR', self.clear, "root"),
                ('PROMPT', self.prompt, "root"),
                ('STOP', self.stop, "root"),
                ('RESTART', self.restart, "root"),
                # ('RESET', self.reset, "root"),
                ('QUIT', self.quit, "root"),

            ],

            "settings" : [
                ['recognizer', 'camera', 'framerate'],
                ['recognizer', 'camera', 'exposure_time'],
                ['adaptation_time'],
                []
            ]
        }

        self._pick_dict = {"root": self._pick_menu, "settings": self._pick_setting, "paradigms": self._pick_paradigm}

        # give time for the device scanner to find the device
        time.sleep(2)
        self.initialise_device()


    def initialise_device(self):
        try:
           self._device = self._ds.get_device_by_id(self._device_id)
        except Exception as error:
            logger.error(error)
            time.sleep(1)
            self.initialise_device()


    @property
    def paradigms(self):
        try:
            paradigms = self._device.info["controller"]["paradigms"]
            paradigms = [e for e in paradigms.values()]
            paradigms.append(None)
            return paradigms

        except AttributeError:
            return [None]

    @staticmethod
    def represents_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False


    # Core functionality
    ## Methods needed to run the CliUI
    ## * _pick_menu: ask the user to perform an action
    ## * _pick_setting: ask the user to enter an option or some input
    ## * _apply: apply or execute the input provided by the user
    ## * run: iterate a new question and execution


    def _user_input(self, max_index, prompt="Enter number: "):
        answer = input(prompt)
        fail = False
        fail = not self.represents_int(answer)
        if not fail:
            answer = int(answer)
            fail = answer > max_index

        if fail:
            print('You entered answer: %s' % answer)
            print('This is not valid. Try again!')

            answer = self._user_input(prompt, max_index)

        return answer

    def _pick_menu(self):
        """
        Present the user with a list of menus
        """

        print("Please choose:")
        options = self._menus["root"]
        for idx, opt in enumerate(options):
            print("{}: {}".format(idx + 1, opt[0]))

        self._answer = self._user_input(len(options))
        return self._answer


    def _pick_setting(self):

        print("Please choose:")
        options = self._menus["settings"]
        for idx, opt in enumerate(options):
            print("{}: {}".format(idx + 1, '/'.join(opt)))

        self._answer = self._user_input(len(options))
        return self._answer

    def _pick_paradigm(self):
        print("Please choose:")
        options = self.paradigms
        for idx, opt in enumerate(options):
            print("{}: {}".format(idx + 1, opt))

        self._answer = self._user_input(len(options))
        return self._answer


    def _apply(self, menu_name, answer):
        """
        Apply the selected option and achieve a side-effect.
        """


        # answer is 0 when an error happpened in the previous pick operation
        if answer == 0:
            return "root"


        # FIXME Weird handling when we are loading a paradigm
        if menu_name == "paradigms":
            options = self.paradigms
        else:
            options = self._menus[menu_name]

        opt = options[answer - 1]

        # the last option is always reserved for a return/stop operation
        # that has no side effects (only effects within the core CLI)
        # handled by self.run
        if answer == len(options) and menu_name != "root":
            new_menu = "root"

        elif menu_name == "root":
            name, func, new_menu = opt
            # import ipdb; ipdb.set_trace()
            if new_menu == "root":
                new_menu = func(answer)

            else:
                if new_menu == "settings":
                    # ignore opt and just get a new answer
                    answer = self._pick_setting()
                elif new_menu == "paradigms":
                    answer = self._pick_paradigm()

                new_menu = self._apply(new_menu, answer)
                # open the new menu

        else:

            if menu_name == "settings":
                self._change_setting(answer)
                answer = self._pick_setting()

            elif menu_name == "paradigms":
                self._load_paradigm(answer)
                answer = self._pick_paradigm()

            else:
                # TODO Warn the user
                pass

            new_menu = self._apply(menu_name, answer)

        return new_menu


    def run(self, menu_name="root"):
        """
        Everytime this method is called
        * the user picks an option from the current menu
        * the option is applied (we get a side-effect)
        * a new menu is chosen automatically
        """

        self.running = True

        answer = self._pick_menu()

        while not self.stopped:
            try:
                new_menu = self._apply(menu_name, answer)
                func = self._pick_dict[new_menu]
                answer = func()

            except Exception as error:
                warnings.warn('I do not understand %s' % self._answer)
                print(error)
                print(traceback.print_exc())
                new_menu = "root"
                answer = 0



    # Side effect functionality
    ## Methods needed to apply the wishes of the user

    def _load_paradigm(self, answer):
        """
        Receive an answer and post the corresponding paradigm_path to the device
        """

        paradigm_path = self.paradigms[answer - 1]
        data = {"paradigm_path": paradigm_path}
        self._device.post_paradigm(data)

        return "paradigms"

    def warm_up(self, answer):
        """
        Communicate with the device to warm_up.

        Start the recognizer and the always_on_hardware
        without saving data.
        Open a broser tab to view the flies
        """
        self._device.warm_up()
        webbrowser.open_new_tab("file://%s" % self._last_img_annot)

        return "root"


    def start_experiment(self, answer):
        """
        Communicate with the device to start an experiment.
        """
        self._device.start_experiment()

        return "root"

    def check(self, answer):
        """
        View the status of IDOC
        """
        warnings.warn("Not implemented")
        return "root"

    def analyze(self, answer):
        warnings.warn("Not implemented")
        return "root"

    @staticmethod
    def clear(self, answer):
        for i in range(30):
            print(" ")

        return "root"

    def prompt(self, answer):
        self._pick_menu()
        return "root"

    def stop(self, answer):
        """
        "Ask the user if output should be saved
        and quit the program
        """
        # TODO Ask functionality
        self._device.stop_experiment()
        return "root"


    def restart(self, answer):
        logger.info("Restarting idoc_server systemd service. Please give a few seconds...")
        subprocess.call(["systemctl", "restart", "idoc_server.service"])
        return "root"

    def reset(self, answer):

        self._device.reset_experiment()
        return "root"

    def quit(self, answer):
        print("Quitting IDOC")
        self._ds.stop()
        self.stopped = True
        time.sleep(1)
        sys.exit(0)

    def _change_setting(self, answer):
        """
        Update the IDOC setting the user has selected with the answer
        Answer is an integer from 1 to length of self_menus['settings']
        """
        settings = self._menus["settings"].copy()

        selected_setting = settings[answer - 1]

        try:
            new_value = self.prompt_new_setting(selected_setting)
        except IDOCException:
            return

        print("Setting %s to %s" % ('/'.join(selected_setting), new_value))

        if len(selected_setting) == 1:
            setting_name = selected_setting[0]
            submodule = "control_thread"

        else:
            setting_name = selected_setting[::-1][0]
            submodule = selected_setting[:len(selected_setting) - 1]

        settings = {"settings": {setting_name: new_value}, "submodule": submodule}
        self._device.post_settings(settings)

        return "settings"

    def prompt_new_setting(self, setting_name):
        """
        Ask the user to enter a new value for setting setting_name
        """

        device_settings = self._device.info['settings']

        # if the setting name is a list, it means it is a submodule setting
        # and we need to dig in the device_settings dict until a match is found
        if isinstance(setting_name, str):
            pass

        elif isinstance(setting_name, list):
            submodule_setting = dict(device_settings)
            for level in setting_name:
                if level in submodule_setting:
                    submodule_setting = submodule_setting[level]
                    if not isinstance(submodule_setting, dict):
                        break
                else:
                    warnings.warn("%s is not configurable yet." % level)
                    warnings.warn("Hint: Did you start the module this setting controls?.")
                    raise IDOCException("Setting %s is not implemented" % level)

            device_settings = submodule_setting
            setting_name = level

        else:
            # TODO Ellaborate more info for the user here
            warnings.warn("Setting is not valid")
            warnings.warn(setting_name)
            return

        # Pick the value of the old setting and report it to the user
        print('%s is set to %s', setting_name, device_settings)
        # Ask the user to enter a new value
        value = float(input("Enter new %s: " % setting_name))

        # TODO Validation here

        return value

if __name__ == "__main__":

    from idoc.helpers import get_machine_id

    device_id = get_machine_id()
    cli = CliUI(device_id=device_id)
    time.sleep(5)

    signals = ('TERM', 'HUP', 'INT')
    for sig in signals:
        signal.signal(getattr(signal, 'SIG' + sig), cli.stop)


    cli.run()



