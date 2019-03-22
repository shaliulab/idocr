# Standard library imports
import argparse
import numpy as np
import pandas as pd
import sys
import threading
import logging
import datetime
import warnings
import time
import glob
import os

# Third party imports
import serial
import yaml

# Local application imports
from pyfirmata import ArduinoMega as Arduino # import the right board but always call it Arduino
from src.utils.frets_utils import PDReader, setup_logging
from .arduino_thread import ArduinoThread

# Set up package configurations
setup_logging()

class LearningMemoryDevice(PDReader):

    def __init__(self, interface, mapping, program, port):

        ## Initialization
        self.mapping = None
        self.program = None
        self.port = None


        self.init_time = None
        self.saver = None
        self.reporting = None

        self.log = None
    
             
        ## Assignment
        self.interface = interface

        self.interface.arduino_done = False
        self.interface.arduino_stopped = False


        self.mapping = mapping
        self.program = program
        self.port = port

        # Inherited from interface
        self.init_time = self.interface.init_time
        self.saver = self.interface.metadata_saver
        self.reporting = self.interface.reporting

        self.log = logging.getLogger(__name__)

        ###############################
        PDReader.__init__(self, mapping, program)

        # pin_names = self.mapping.index
        # self.pin_state = {p: 0 for p in pin_names}

        # Try loading the Arduino board with pyfirmata
        # Could fail if Arduino is not connected under port
        try:
            self.board = Arduino(port)
        except serial.serialutil.SerialException:
            self.log.error('Please provide the correct port')
            sys.exit(1)
    


    # def check_do_run(self, d, max_sleep):
    #     stop = False 
    #     start_sleeping = datetime.datetime.now()
    #     while ((datetime.datetime.now() - start_sleeping).total_seconds() < max_sleep):
    #         stop_arduino = self.interface.exit.is_set()
    #         stop_gui = getattr(self.interface.tracker, "stop", False)
    #         if not stop_arduino and not stop_gui:
    #             time.sleep(0.001)
    #             if getattr(self.interface.tracker, "stop", False):
    #                 self.log.info("Tracker signaled stop")
    #         else:
    #             stop = True
    #             break
    #     return stop 

    def prepare(self):


        threads = self.interface.threads
 
        # They are not run throughout the lifetime of the program, just at some interval and without intermitency
        
        count = {p: 0 for p in self.program.index}
        for p in self.program.index:
            d_pin_number = np.asscalar(self.mapping.loc[p]["pin_number"])
            x0 = count[p]
            x1 = count[p]+1

            d_start =      np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["start"])
            d_end =        np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["end"])
            d_on =         np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["on"])
            d_off =        np.asscalar(self.program.loc[[p]].iloc[x0:x1,:]["off"])
            d_name = 'thread-{}_{}'.format(p, count[p])

            kwargs = {
                "pin_number"   : d_pin_number,
                "start"        : d_start,
                "end"          : d_end,
                "on"           : d_on,
                "off"          : d_off,
                "duration"   : None,
                "start_time": None,
                "d_name"         : d_name, 
                "board":         self.board

            }
            d = ArduinoThread(
                lmd = self,
                name=d_name,
                kwargs = kwargs
            )

            d.setDaemon(False)
            d.do_run = True
            threads[d_name]=d
            self.interface.threads_finished[d_name] = False
            count[p] += 1

        ################################
        ## Finished preparing/configuring the threads
        ################################
        
         
        self.interface.threads = threads
        return threads

    
    def _run(self, threads):

        t = threading.currentThread()
        self.log.info('Starting slave threads')
        self.interface.arduino_start = datetime.datetime.now()

        for process in threads.values():
            process.start(start_time = self.interface.arduino_start, duration = self.interface.duration)
        self.log.debug('{} waiting for slave threads'.format(t.name))

        # wait until all threads are finished               
        self.interface.exit.wait()

        self.onClose()

        return None

    def run(self, threads):

        arduino_thread = threading.Thread(
            name = 'SUPER_ARDUINO',
            target = self._run,
            kwargs = {
                "threads": threads
                }
        )

        self.interface.arduino_thread = arduino_thread.start()
        return None

    def onClose(self):
            
        t = threading.currentThread()

        self.power_off_arduino()
        self.log.info('{} storing and cleaning cache'.format(t.name))
        for k, lst in self.saver.cache.items():
            self.saver.store_and_clear(lst, k)

        self.interface.arduino_done = True
        if not self.interface.exit.is_set(): self.interface.onClose()
        return True
 

    def pin_id2n(self, pin_id):
        return str(self.mapping.loc[[pin_id]]["pin_number"].iloc[0]).zfill(2)
    
    def left_pair(self, p, pin_state_g):
        return [self.pin_id2n(p), pin_state_g[p]]


    def power_off_arduino(self, exit=True):
        # stop all the threads
        if self.interface.threads:
            self.log.info("Quitting program")

        for p in self.mapping.pin_number:
            self.board.digital[p].write(0)
    
        if exit:
            return False



    ######################
    ## Enf of LearningMemoryDevice class


#class LearningMemoryDevice(ReadConfigMixin, BaseDevice):
#    pass

if __name__ == "__main__":
    
    import signal
    from src.interface.main import Interface
    
    # Arguments to follow the command, adding video, etc options
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port",     type = str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows", default = "/dev/ttyACM0")
    ap.add_argument("-m", "--mapping", type = str, help="Absolute path to csv providing pin number-pin name mappings", required=True)
    ap.add_argument("-s", "--sequence", type = str, help="Absolute path to csv providing the sequence of instructions to be sent to Arduino", required=True)
    ap.add_argument("-d", "--duration",  type = int, required=True)
    args = vars(ap.parse_args())
 
    mapping = args["mapping"]
    program = args["sequence"]
        
    interface = Interface(arduino = True)
    interface.control_c_handler()
    device = LearningMemoryDevice(interface, mapping, program, args["port"])
    device.power_off_arduino(exit=False)

    threads = device.prepare()
    duration = 60 * args["duration"]
    device.run(threads=threads)
    time.sleep(duration)
    #device.exit.wait(args["duration"])
