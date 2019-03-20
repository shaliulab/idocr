from pyfirmata import ArduinoMega as Arduino # import the right board but always call it Arduino
from src.frets_utils import *
from pyfirmata import Pin
from pyfirmata import util
import numpy as np
import pandas as pd
import sys
import threading
import logging
import datetime
# import ipdb
import time
#import pickle # share pin state across threads
import glob
import os # file removal and we cleaning
import argparse
import timeit
import signal
import serial
import logging, coloredlogs
import warnings
import yaml
from src.saver.main import Saver
coloredlogs.install()

class PDReader():

    def __init__(self, mapping, program):
        mapping = pd.read_csv(mapping, skip_blank_lines=True, comment="#")
        program = pd.read_csv(program, skip_blank_lines=True, comment="#")
        mapping = mapping.set_index('pin_id')
        program = program.set_index('pin_id')
        program['start'] = program['start'].apply(convert)
        program['end'] = program['end'].apply(convert)
        program['on'] = program['on'].apply(convert)
        program['off'] = program['off'].apply(convert)
        
        program = program * 60

        self.mapping = mapping
        self.program = program 



@mixedomatic
class LearningMemoryDevice(ReadConfigMixin, PDReader):

    def __init__(self, mapping, program, port, config = "config.yaml", communicate=True, tracker = None, start_time = None):

        self.start_time = start_time 
        self.tracker = tracker
        self.log = logging.getLogger(__name__)
        self.saver = Saver(store = self.cfg["arduino"]["store"], cache = {})
        self.saver.update_parent(self)
        PDReader.__init__(self, mapping, program)

        self.port = port
        pin_names = mapping.index
        self.pin_state = {p: 0 for p in pin_names}

        try:
            self.board = Arduino(port)
        except serial.serialutil.SerialException:
            self.log.error('Please provide the correct port')
            sys.exit(1)
    
        self.exit = threading.Event()
        self.finished = False
        self.communicate = communicate
        self.quit = self.thread_off()


    def check_do_run(self, d, max_sleep):
        stop = False 
        start_sleeping = datetime.datetime.now()
        while ((datetime.datetime.now() - start_sleeping).total_seconds() < max_sleep):
            stop_arduino = self.exit.is_set()
            stop_gui = getattr(self.tracker, "stop", False)
            if not stop_arduino and not stop_gui:
                time.sleep(0.001)
                if getattr(self.tracker, "stop", False):
                    self.log.info("Tracker signaled stop")
            else:
                stop = True
                break
        return stop 

    def prepare(self):
 
        # They are not run throughout the lifetime of the program, just at some interval and without intermitency
        threads = {}
        
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
                "total_time"   : None,
                "program_start": None,
                "d_name"         : d_name, 
                "board":         self.board

            }
            d = MyThread(name=d_name,
                         target=self.pin_thread,
                         kwargs = kwargs)

            d.setDaemon(False)
            d.do_run = True
            threads[d_name]=d
            count[p] += 1

        ################################
        ## Finished preparing/configuring the threads
        ################################
        
        self.threads = threads
        self.threads_finished = {k: False for k in threads.keys()}

        
        program_start = datetime.datetime.now()
        self.program_start = program_start
        #if getattr(self, "tracker", False):
        #    self.tracker.program_start = program_start
         

        return threads

    def toggle_pin(self, pin_number, value, message=None):
        """
        Updates the state of pin pin_number with value, while logging and caching this
        so user can confirm it. TODO. Finish show_circuit and use message
        """

        d = threading.currentThread()
        
        # Update state of pin (value = 1 or value = 0)
        self.board.digital[pin_number].write(value)


        # Update log with info severity level unless
        # on pin13, then use severity debug
        f = self.log.info
        # if pin_number == 13: f = self.log.debug
        f("{} - {}".format(
            d._kwargs["d_name"],
            value
        ))

        # Create a new row in the metadata
        self.saver.process_row(
                d = {
                    "pin_number": pin_number, "value": value, "thread": d._kwargs["d_name"], 
                    "time_position": getattr(self.tracker, "time_position", None),
                    "datetime": datetime.datetime.now()
                    },
                key = "df"

        )
  
        #self.show_circuit(
        #            #pin_state,
        #            message
        #            )
 
 

    def pin_thread(self, pin_number, total_time, program_start, start, end, on, off, n_iters=np.nan, d_name="", board=None):
        """
        Run by every thread independently, this function replicates the program specified in the corresponding row
        of the program dataframe. Turns on a pin at a specific timepoint and after some waiting time, it turns it off
        If on and off are not none, it can implement a cycle during this waiting time i.e. the pin can be turned on and off
        between start and end for on and off seconds respectively.

        Keywords
          pin_number: integer declaring the number of the pin on the Arduino board
          
          total_time: time in seconds that the whole program is supposed to last.
                       After total_time, all pins should go off, no matter what their program is
          
          program_start: datetime object declaring the exact moment when run()
          (the function that calls pin_thread when defining the threads) is executed. Only makes sense in scheduled pins.
          
          start: timepoint in seconds when the pin should go on for the first time. Only makes sense in scheduled pins.
          
          end: timepoint in seconds when the pin should be turned off for good
          
          on: duration of the on time in a cycle. Only makes sense in intermitent pins.
          
          off: duration of the off time in a cycle. Only makes sense in intermitent pins.
          
          n_iters: By default is None, but it will be asigned a value equal to the number of cycles
                   required by intermitent pins (as instructed in the program). If the pin does not have a cycle,
                   then it will still be None        
        """
        sync_time = 1
        d = threading.currentThread()


        # this is true for pins of type: CI, SI (intermitent)
        # i.e. threads where on is not NaN
        if n_iters != n_iters and on == on:
            n_iters = max(0, (min(end, total_time) - start) // (on + off)) # check if total time is accessible
        if n_iters > 0:
            self.log.info("{} will cycle {} times: start {} end {} tt {}".format(d_name, n_iters, start, end, total_time))
            
        
        # halt all threads until program_start + sync_time is reached
        # wait until all threads are ready to begin
        sleep1 = (program_start + datetime.timedelta(seconds=sync_time) - datetime.datetime.now()).total_seconds()
        stop = self.check_do_run(d, sleep1)
        self.log.info('{} running'.format(d_name))
        if stop:
            self.toggle_pin(pin_number, 0)
            return 0
    
        thread_start = datetime.datetime.now()    
        
        # halt the thread until program_start + time sleep in the syncing + start is reached
        # i.e. wait until it is time to turn on a pin
        sleep2 = (thread_start + datetime.timedelta(seconds=start) - datetime.datetime.now()).total_seconds()
        if sleep2 > 0:
            stop = self.check_do_run(d, sleep2)
            if stop:
                self.log.debug("{} received exit".format(d_name))
                self.toggle_pin(pin_number, 0)
                return 0
        else:
             self.log.warning("{} delayed {} seconds".format(d_name, -sleep2))
    
        
        # pin_id = self.mapping.query('pin_number == "{}"'.format(pin_number)).index[0]
    
        if n_iters == n_iters:    
            for _ in range(int(n_iters)):

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 1)
                
                runtime = datetime.datetime.now() - start_time
                sleep_time = on - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))

                else:
                    stop = self.check_do_run(d, sleep_time)
                    if stop:
                        self.toggle_pin(pin_number, 0)
                        return 0

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 0)
                runtime = datetime.datetime.now() - start_time
                sleep_time = off - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))
                else:
                    stop = self.check_do_run(d, sleep_time)
                if stop:
                    self.toggle_pin(pin_number, 0)
                    return 0
       

        else:
            # pins without cycle
            start_time = datetime.datetime.now()
            self.toggle_pin(pin_number, 1)
            sleep_time = min(end - start, total_time - start)
            if sleep2 < 0:
                sleep_time += sleep2
   
            #time.sleep(sleep_time)
            stop = self.check_do_run(d, sleep_time)
            if stop:
                self.toggle_pin(pin_number, 0)
                return 0

        self.toggle_pin(pin_number, 0)
        return 1

    def _run(self, total_time, threads):

        t = threading.currentThread()
        self.log.info('Starting slave threads')
        for process in threads.values():
            process.start(self.program_start, total_time)
        self.log.debug('{} waiting for slave threads'.format(t.name))
        
        while not self.exit.is_set() and not np.bitwise_and.reduce(list(self.threads_finished.values())) and not getattr(self.tracker, "stop", False):
            time.sleep(0.001)

        
        time.sleep(.1)
        self.total_off()
        self.log.info('{} storing and cleaning cache'.format(t.name))
        for k, lst in self.saver.cache.items():
            self.saver.store_and_clear(lst, k)

        self.finished = True

        return None

    def run(self, total_time, threads):

        # Make the main thread run quit when signaled to stop
        # This will stop all the threads in a controlled fashion,
        # which means all the pins are turned of before the thread
        # peacefully dies
        signals = ('TERM', 'HUP', 'INT')
        for sig in signals:
            signal.signal(getattr(signal, 'SIG' + sig), self.quit)

        t = threading.Thread(
            name = 'SUPER_ARDUINO',
            target = self._run,
            kwargs = {
                "total_time": total_time,
                "threads": threads
                }
        )

        t.start()
        return None


 
    def show_circuit(self, 
                    #pin_state,
                    message=None, flush=True):
       #global pin_state
       pin_state_g = {p: "x" if v == 1 else "0" for p, v in self.pin_state.items()}

       main_pins = self.mapping.query('pin_group == "main"').index.values[1:]
       left_pins = self.mapping.query('pin_group == "left"').index.values
       right_pins = self.mapping.query('pin_group == "right"').index.values
       
       show_data = [self.pin_id2n(p) for p in main_pins] + [pin_state_g[p] for p in main_pins]
       show_data2 = [self.left_pair(p, pin_state_g) for p in left_pins] 
       show_data3 = [self.left_pair(p, pin_state_g)[::-1] for p in right_pins] 
       show_data4 = list(zip(show_data2, show_data3))
       flatten = lambda l: [item for sublist in l for item in sublist]
       show_data4 = flatten(flatten(show_data4))
       show_data += show_data4
       n=4
       n2=18
       circuit = " " * 8 + "{}-VA  {}-MA  {}-IR  {}-VI   \n" +    " " * 8 + "[{}]" + " " * n + "[{}]" + " " * n + "[{}]" + " " * n + "[{}]\n" +    "{}-LO1  [{}]" + " " * n2 + "[{}] RO1-{}\n" +    "{}-LO2  [{}]" + " " * n2 + "[{}] RO2-{}\n" +    "{}-LES  [{}]" + " " * n2 + "[{}] RES-{}\n" +    "{}-LL   [{}]" + " " * n2 + "[{}]  RL-{}\n"
       filled_circuit = circuit.format(*show_data)        
           
           
       if not message is None:
           output = "{}: {}\n{}".format(datetime.datetime.now(), message, filled_circuit)
       else:
           output = "{}: \n{}".format(datetime.datetime.now(), filled_circuit)
       if flush:
           nlines = len(filled_circuit.split('\n'))
           output = nlines * "\033[F\033[K" + output

       handle = open("pin_state.txt", "a+")
       handle.write(output)
       handle.close()


    def pin_id2n(self, pin_id):
        return str(self.mapping.loc[[pin_id]]["pin_number"].iloc[0]).zfill(2)
    
    def left_pair(self, p, pin_state_g):
        return [self.pin_id2n(p), pin_state_g[p]]


    def total_off(self, exit=True):
        # stop all the threads
        if getattr(self, "threads", False):
            self.log.info("Quitting program")
            for d in self.threads.values():
                #d.do_run = False
                try:
                    self.log.info("{} stopped".format(d._kwargs["d_name"]))
                except AttributeError:
                    pass
        else:
            self.log.info("Completely turning off Arduino")
    
        for p in self.mapping.pin_number:
            self.board.digital[p].write(0)
    
        if exit:
            return False


    def thread_off(self):
        def quit(signo=None, _frame=None):
           self.log.info("Received {}".format(signo))
           self.exit.set()
        #    sys.exit(1)
    
        return quit
    ######################
    ## Enf of BaseDevice class


#class LearningMemoryDevice(ReadConfigMixin, BaseDevice):
#    pass

if __name__ == "__main__":

    # Arguments to follow the command, adding video, etc options
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port",     type = str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows", default = "/dev/ttyACM0")
    ap.add_argument("-m", "--mappings", type = str, help="Absolute path to csv providing pin number-pin name mappings", required=True)
    ap.add_argument("-s", "--sequence", type = str, help="Absolute path to csv providing the sequence of instructions to be sent to Arduino", required=True)
    ap.add_argument("-d", "--duration",  type = int, required=True)
    args = vars(ap.parse_args())


    mapping = args["mappings"]
    program = args["sequence"]

    device = LearningMemoryDevice(mapping, program, args["port"])
    device.total_off(exit=False)

    threads = device.prepare()
    total_time = 60 * args["duration"]
    device.run(total_time=total_time, threads=threads)
    time.sleep(total_time)
    #device.exit.wait(args["duration"])
