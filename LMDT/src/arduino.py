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
from pyfirmata import ArduinoMega, Arduino
from pdloader import PDLoader
from lmdt_utils import setup_logging
from arduino_threading import ArduinoThread

# Set up package configurations
setup_logging()

boards = {"Arduino": Arduino, "ArduinoMega": ArduinoMega}

class LearningMemoryDevice(PDLoader):

    def __init__(self, interface, mapping, program, port):

        ## Initialization
        self.mapping = None
        self.program = None
        self.port = None
        self.pin_state = None


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
        PDLoader.__init__(self, mapping, program)
        
        self.pin_state = {k: False for k in self.mapping.index}


        self.program.to_csv(self.saver.store + "_compiled.csv")

        # pin_names = self.mapping.index
        # self.pin_state = {p: 0 for p in pin_names}

        # Try loading the Arduino board with pyfirmata
        # Could fail if Arduino is not connected under port
        try:
            self.board = boards[self.interface.cfg["arduino"]["board"]](port)
            self.log.info("Loaded {} board".format(self.interface.cfg["arduino"]["board"]))
        except serial.serialutil.SerialException:
            self.log.error('Please provide the correct port')
            sys.exit(1)
    
    def prepare(self):

        threads = self.interface.threads
        self.program["active"] = False
        self.program["thread_name"] = None

        self.active_block = {k: False for k in self.overview.index}
 
        # They are not run throughout the lifetime of the program, just at some interval and without intermitency
        
        events = self.program.index.get_level_values('pin_id')
        count = {ev: 0 for ev in events}
        for i, ev in enumerate(events):
            d_pin_number = np.asscalar(self.mapping.loc[ev]["pin_number"])
            x0 = count[ev]
            x1 = count[ev]+1

            d_start =      np.asscalar(self.program.loc[[ev]].iloc[x0:x1,:]["start"])
            d_end =        np.asscalar(self.program.loc[[ev]].iloc[x0:x1,:]["end"])

            if d_end <= d_start:
                continue
            d_on =         np.asscalar(self.program.loc[[ev]].iloc[x0:x1,:]["on"])
            d_off =        np.asscalar(self.program.loc[[ev]].iloc[x0:x1,:]["off"])
            block =        np.asscalar(self.program.loc[[ev]].iloc[x0:x1,:].index)

            d_name = 'thread-{}-{}'.format(ev, count[ev])

            self.program[i,"thread_name"] = d_name

            kwargs = {
                "pin_number"   : d_pin_number,
                "start"        : d_start,
                "end"          : d_end,
                "on"           : d_on,
                "off"          : d_off,
                "duration"   : None,
                "start_time": None,
                "d_name"         : d_name, 
                "board":         self.board,
                "block"         : block,
                "i"             : i
            }

            d = ArduinoThread(
                device = self,
                name=d_name,
                kwargs = kwargs
            )

            d.setDaemon(False)
            d.do_run = True
            threads[d_name] = d
            self.interface.threads_finished[d_name] = False
            count[ev] += 1

        ################################
        ## Finished preparing/configuring the threads
        ################################
        
         
        self.interface.threads = threads
        return threads

    
    def _run(self, threads):

        t = threading.currentThread()
        self.log.info('start()ing arduino threads')
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

        self.interface.arduino_thread = arduino_thread
        arduino_thread.start()
        return None

    def onClose(self):
            
        t = threading.currentThread()

        self.power_off_arduino()
        self.log.info('{} storing and cleaning cache'.format(t.name))
        self.saver.store_and_clear(self.saver.lst, 'metadata')

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
    from interface import Interface
    
    # Arguments to follow the command, adding video, etc options
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port",     type = str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows", default = "/dev/ttyACM0")
    ap.add_argument("-m", "--mapping", type = str, help="Absolute path to csv providing pin number-pin name mappings", required=True)
    ap.add_argument("-s", "--sequence", type = str, help="Absolute path to csv providing the sequence of instructions to be sent to Arduino", required=True)
    ap.add_argument("-d", "--duration",  type = int, required=True)
    ap.add_argument("-g", "--gui",       type = str,  default = "tkinter", choices=['opencv', 'tkinter'], help="tkinter/opencv")

    args = vars(ap.parse_args())
 
    duration = 60 * args["duration"]
        
    interface = Interface(arduino = True, mapping = args["mapping"], program = args["sequence"], port = args["port"], duration = duration)
    interface.prepare()
    interface.start()
