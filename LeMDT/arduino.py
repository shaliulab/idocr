# Standard library imports
import argparse
import sys
import threading
import logging
import datetime
import warnings
import time
import glob
import os

# Third party imports
import numpy as np
import pandas as pd
import serial
import yaml

# Local application imports
from pyfirmata import ArduinoMega, Arduino
from pdloader import PDLoader
from lmdt_utils import setup_logging
from arduino_threading import ArduinoThread

# Set up package configurations
setup_logging()

BOARDS = {"Arduino": Arduino, "ArduinoMega": ArduinoMega}

class LearningMemoryDevice(PDLoader):

    def __init__(self, interface, mapping_path, program_path):

        ## Initialization
        self.mapping = None
        self.program = None
        self.pin_state = None
        self.stop_event_name = None
        self.threads_finished = None


        self.reporting = None

        self.log = None
             
        ## Assignment
        self.interface = interface

        self.interface.arduino_stopped = False


        self.mapping_path = mapping_path
        self.program_path = program_path

        # Inherited from interface
        self.reporting = self.interface.reporting

        self.log = logging.getLogger(__name__)
        self.log.debug('Loaded paradigm in {}'.format(self.program))

        self.threads = {"exit_or_record": {}, "exit" : {}}
        self.threads_finished = {}


    def connect_arduino_board(self, port):
        """
        Try loading the Arduino board with pyfirmata
        Could fail if Arduino is not connected under port
        """

        if port is None:
            self.log.error('No port has been assigned')
            self.log.error('I dont know where is Arduino')
            sys.exit(1)

        try:
            self.board = BOARDS[self.interface.cfg["arduino"]["board"]](port)
            self.log.info("Loaded {} board".format(self.interface.cfg["arduino"]["board"]))
        except serial.serialutil.SerialException as e:
            self.log.error('Please provide the correct port')
            self.log.error(e)
            sys.exit(1)

    def load_program(self, mapping_path=None, program_path=None):
        """
        Update the mapping_path and program_path
        This function runs the __init__ method of the PDLoader
        (Pandas Loader) class
        """

        mapping_path = self.interface.default_mapping_path if mapping_path is None else mapping_path
        program_path = self.interface.default_program_path if program_path is None else program_path


        PDLoader.__init__(self, mapping_path, program_path)


    def init_pin_state(self):
        """
        Initialize a dictionary storing the state of each pin. Default False
        """
        self.pin_state = {k: 0 for k in self.mapping.index}



    def prepare(self, stop_event_name):
        """
        Load the Arduino paradigm into LeMFT
        Power off all pins
        Create the threads dictionary
        """

        self.log.debug('Loading program')
        self.load_program(mapping_path=self.mapping_path, program_path=self.program_path)

        # power off any pins if any
        self.power_pins_off(shutdown=False, ir=True)
        # prepare the arduino parallel threads
        threads = self.create_threads(self.threads, stop_event_name=stop_event_name)
        self.init_pin_state()
        return threads


    def create_threads(self, threads, stop_event_name='exit'):
        """
        Take the loaded paradigm and create a dictionary of parallel threads
        Each thread will be an instance of ArduinoThread, based on threading.Thread()
        """

        if self.program is None:
            self.log.error("No program loaded. Exiting")
            sys.exit(1)

        self.stop_event_name = stop_event_name
        threads_subgroup = {}
        print('Upon initialization')
        print(id(threads_subgroup))
        threads_subgroup[stop_event_name] = threads[stop_event_name]
        print('After sharing threads')
        print(id(threads_subgroup))

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

            d_start =      np.asscalar(self.program.loc[[ev]].iloc[x0:x1, :]["start"])
            d_end =        np.asscalar(self.program.loc[[ev]].iloc[x0:x1, :]["end"])

            if d_end <= d_start:
                continue
            d_on =         np.asscalar(self.program.loc[[ev]].iloc[x0:x1, :]["on"])
            d_off =        np.asscalar(self.program.loc[[ev]].iloc[x0:x1, :]["off"])
            block =        np.asscalar(self.program.loc[[ev]].iloc[x0:x1, :].index)

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
            threads_subgroup[d_name] = d
            self.threads_finished[d_name] = False
            count[ev] += 1

        #################################################
        ## Finished preparing/configuring the threads
        #################################################
        threads[stop_event_name] = threads_subgroup
        return threads

    
    def run(self, threads):
        """
        Set the arduino_start time
        Start each of the threads that was prepared in device.prepare()
        """

        t = threading.currentThread()
        self.log.info('start()ing arduino threads')
        self.interface.arduino_start = datetime.datetime.now()

        for process in threads.values():
            if not process.is_alive():
                process.start(start_time=self.interface.arduino_start, duration=self.interface.duration)
            else:
                self.log.info("thread % already started", process.name)
        
        self.log.debug('% waiting for slave threads', t.name)

        # wait until all parallel threads are finished               
        self.interface.exit.wait()
        self.close()
        
    def toprun(self, threads):
        """
        Create an intermediate thread between main thread
        and all parallel threads and start it
        """

        arduino_thread = threading.Thread(
            name='SUPER_ARDUINO',
            target=self.run,
            kwargs={
                "threads": threads
                }
        )

        self.interface.arduino_thread = arduino_thread
        arduino_thread.start()
        return None

    def close(self):
        """
        Power off the arduino pins, save metadata cache to a file and
        signal the end of Arduino parallel threads
        """
            
        t = threading.currentThread()

        # power off every pin
        self.power_pins_off()

        self.interface.arduino_done.set()
        # NEEDED?
        # if the exit event is not set yet and this is the stop event of the threads, activate the interface close method
        if not self.interface.exit.is_set() and self.stop_event_name == 'exit': self.interface.close()
        return True
 

    def pin_id2n(self, pin_id):
        return str(self.mapping.loc[[pin_id]]["pin_number"].iloc[0]).zfill(2)
    
    def left_pair(self, p, pin_state_g):
        return [self.pin_id2n(p), pin_state_g[p]]


    def power_pins_off(self, shutdown=True, ir=False):
        """
        Sets every pin mentioned in the mapping file to OFF except the if infrared (ir) is True.
        In that case, the IR stays ON
        """

        # power everything off except if ir is False.
        # In that case the IR light is kept
        for p in self.mapping.pin_number:
            if self.mapping.loc[self.mapping.index.values == 'IRLED', 'pin_number'].values != p or ir:
                self.board.digital[p].write(0)
    
        if shutdown:
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
        
    interface = Interface(arduino=True, mapping=args["mapping"], program=args["sequence"], port=args["port"], duration=duration)
    interface.prepare()
    interface.start()
