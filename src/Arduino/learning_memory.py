from pyfirmata import ArduinoMega as Arduino # import the right board but always call it Arduino
from pyfirmata import Pin
from pyfirmata import util
import numpy as np
import warnings
from tqdm import tqdm
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


def check_do_run(d, max_sleep):
    stop = False 
    start_sleeping = datetime.datetime.now()
    while ((datetime.datetime.now() - start_sleeping).total_seconds() < max_sleep):
        if getattr(d, "do_run", True):
            time.sleep(0.001)

            #print(getattr(d, "do_run"))
        else:
            print("I need to die!")
            stop = True
            break
    return stop 

class MyThread(threading.Thread):
    def start(self, program_start, total_time):
        """
        Extend the start method in threading.Thread() to receive 2 more args, program_start and total_time

        """
        self._kwargs["program_start"] = program_start
        self._kwargs["total_time"] = total_time 
        super(MyThread, self).start()


class LearningMemoryDevice():
    def __init__(self, mapping, program, port, log_dir, communicate=True):
        self.mapping = mapping
        self.program = program 
        self.port = port
        pin_names = mapping.pin_id
        pin_state = {p: 0 for p in pin_names}

        self.pin_state = pin_state

        self.board = Arduino(port)
        #filehandler = open(os.path.join(log_dir, "pin_state.obj"),"wb")
        #pickle.dump(pin_state,filehandler)
        #filehandler.close()    
        self.exit = threading.Event()
        self.communicate = communicate

        self.log_dir = log_dir
        log_files = glob.glob(os.path.join(self.log_dir, 'log*'))
        for f in log_files + [os.path.join(self.log_dir, e) for e in "pin_state.txt"]:
            try:
                os.remove(f)
            except OSError:
                pass


    def off(self):
        [self.board.digital[pin_number].write(0) for pin_number in self.mapping.pin_number]

    def prepare(self):
 
        # They are not run throughout the lifetime of the program, just at some interval and without intermitency
        daemons = {}
        
        count = {p: 0 for p in self.program.pin_id}
        for p in self.program.pin_id:
            d_pin_number = np.asscalar(self.mapping.query('pin_id == "{}"'.format(p))["pin_number"])
            d_start = np.asscalar(self.program.query('pin_id == "{}"'.format(p))["start"].iloc[count[p]])
            d_end =   np.asscalar(self.program.query('pin_id == "{}"'.format(p))["end"].iloc[count[p]])
            d_on =   np.asscalar(self.program.query('pin_id == "{}"'.format(p))["on"].iloc[count[p]])
            d_off =   np.asscalar(self.program.query('pin_id == "{}"'.format(p))["off"].iloc[count[p]])
            d_name = 'daemon-{}_{}'.format(p, count[p])

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
                         target=self.pin_daemon,
                         kwargs = kwargs)
            d.setDaemon(True)
            d.do_run = True
            daemons[d_name]=d
            count[p] += 1
        
        
        ## Signal start
#        for i in range(2):
#            for pin_number in self.mapping.pin_number:
#                self.board.digital[pin_number].write(1)
#                time.sleep(0.05)
#                self.board.digital[pin_number].write(0)
#                time.sleep(0.05)
                
        self.program_start = datetime.datetime.now()

        # Make the main thread run quit when signaled to stop
        # This will stop all the daemons in a controlled fashion,
        # which means all the pins are turned of before the thread
        # peacefully dies
        quit = self.thread_off()
        for sig in ('TERM', 'HUP', 'INT'):
            signal.signal(getattr(signal, 'SIG'+sig), quit)


        self.daemons = daemons
        return daemons

    def toggle_pin(self, pin_number, value, message=None):
        # global self.pin_state

        self.board.digital[pin_number].write(value)

        #if self.communicate:
            #filehandler = open(os.path.join(self.log_dir, "pin_state.obj"),"rb")
            #pin_state = pickle.load(filehandler)
            #filehandler.close()

            #pin_state[self.mapping.query('pin_number == "{}"'.format(pin_number))["pin_id"].iloc[0]]=value
            ##print(self.pin_state["RIGHT_ODOUR_2"])

            #filehandler = open(os.path.join(self.log_dir, "pin_state.obj"),"wb")
            #pickle.dump(pin_state,filehandler)
            #filehandler.close()
    
        self.show_circuit(
                    #pin_state,
                    message
                    )
 
 

    def pin_daemon(self, pin_number, total_time, program_start, start, end, on, off, n_iters=np.nan, d_name="", board=None):
        """
        pin_number: integer declaring the number of the pin on the Arduino board
        
        total_time: time in seconds that the whole program is supposed to last.
                     After total_time, all pins should go off, no matter what their program is
        
        program_start: datetime object declaring the exact moment when run()
        (the function that calls pin_daemon when defining the threads) is executed. Only makes sense in scheduled pins.
        
        start: timepoint in seconds when the pin should go on for the first time. Only makes sense in scheduled pins.
        
        end: timepoint in seconds when the pin should be turned off for good
        
        on: duration of the on time in a cycle. Only makes sense in intermitent pins.
        
        off: duration of the off time in a cycle. Only makes sense in intermitent pins.
        
        n_iters: By default is None, but it will be asigned a value equal to the number of cycles
                 required by intermitent pins (as instructed in the program). If the pin does not have a cycle,
                 then it will still be None        
        """
        sync_time = 1
        #global self.pin_state
        d = threading.currentThread()


        # this is true for pins of type: CI, SI (intermitent)
        if n_iters != n_iters and on == on:
            n_iters = min(end, total_time) // (on + off) # check if total time is accessible
            
        
        # halt all threads until program_start + sync_time is reached
        sleep1 = (program_start + datetime.timedelta(seconds=sync_time) - datetime.datetime.now()).total_seconds()
        stop = check_do_run(d, sleep1)
        if stop:
            self.board.digital[pin_number].write(0)
            return 0

    
        thread_start = datetime.datetime.now()    
        self.write_start_time(pin_number, "Pin {}-{} starts at {}\n", start)
        
        
        logging.debug("Running program on pin {}".format(pin_number))  
    
        # halt the thread until program_start + time sleep in the syncing + start is reached
        sleep2 = (thread_start + datetime.timedelta(seconds=start) - datetime.datetime.now()).total_seconds()
        if sleep2 > 0:
            stop = check_do_run(d, sleep2)
            if stop:
                self.board.digital[pin_number].write(0)
                return 0
        else:
            pass
    #         print(d_name.format(pin_number))
    #         print(sleep2)      
            
    #     self.write_start_time(pin_number, "Pin {}-{} executes at {}\n", start)
    
        
        p = self.mapping.query('pin_number == "{}"'.format(pin_number))["pin_id"].iloc[0]
    
        if n_iters == n_iters:    
    #         for _ in tqdm(range(int(n_iters))):
            for _ in range(int(n_iters)):

                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 1)
                
                runtime = datetime.datetime.now() - start_time
                sleep_time = on - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))

                else:
                    time.sleep(sleep_time)
    
                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 0)
                runtime = datetime.datetime.now() - start_time
                sleep_time = off - runtime.total_seconds()
                if sleep_time < 0:
                    warnings.warn("Runtime: {}".format(runtime))
                else:
                    time.sleep(sleep_time)
        else:
            # pins without cycle
            start_time = datetime.datetime.now()
            self.toggle_pin(pin_number, 1)
            sleep_time = min(end - start, total_time - start)
            if sleep2 < 0:
                sleep_time += sleep2
   
            #time.sleep(sleep_time)
            stop = check_do_run(d, sleep_time)
            #if stop:
            #    self.board.digital[pin_number].write(0)
            #    return 0



            #time.sleep(sleep_time)
#            while ((datetime.datetime.now() - start_sleeping).total_seconds() < sleep_time):
#                if getattr(d, "do_run", True):
#                    pass
#                    #print(getattr(d, "do_run"))
#                else:
#                    break

        self.toggle_pin(pin_number, 0)



 
    def run(self, total_time, daemons):
        [d.start(self.program_start, total_time) for d in daemons.values()]


 
    def show_circuit(self, 
                    #pin_state,
                    message=None, flush=True):
       #global pin_state
       pin_state_g = {p: "x" if v == 1 else "0" for p, v in self.pin_state.items()}
       #print(pin_state_g["RIGHT_ODOUR_2"])

       main_pins = self.mapping.query('pin_group == "main"')["pin_id"].values[1:]
       left_pins = self.mapping.query('pin_group == "left"')["pin_id"].values
       right_pins = self.mapping.query('pin_group == "right"')["pin_id"].values
       
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
        return str(self.mapping.query('pin_id  == "'+pin_id+'"')["pin_number"].iloc[0]).zfill(2)
    
    def left_pair(self, p, pin_state_g):
        return [self.pin_id2n(p), pin_state_g[p]]


    def write_start_time(self, pin_number, message, start):
        
        handle = open(os.path.join(self.log_dir, "log_{}.txt".format(pin_number)), "a+")
        handle.write(message.format(pin_number, start, datetime.datetime.now()))
        handle.close()


    def total_off(self):
        # stop all the threads
        for d in self.daemons.values():
            d.do_run = False
            #print("Thread {} stopped".format(d._kwargs["d_name"]))
            print("Stopping thread")
            d.join()
    
        for p in self.mapping.pin_number:
            self.board.digital[p].write(0)
    
        print("Quitting")


    def thread_off(self):
        def quit(signo, _frame=None):
           self.total_off()
           self.exit.set()
    
        return quit
    
if __name__ == "__main__":

    # Arguments to follow the command, adding video, etc options
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port",     type = str, help="Absolute path to the Arduino port. Usually '/dev/ttyACM0' in Linux and COM in Windows", default = "/dev/ttyACM0")
    ap.add_argument("-m", "--mappings", type = str, help="Absolute path to csv providing pin number-pin name mappings", default = "Arduino/pins_mapping_breadboard.csv")
    ap.add_argument("-s", "--sequence", type = str, help="Absolute path to csv providing the sequence of instructions to be sent to Arduino", default="Arduino/simplified_program2.csv")
    ap.add_argument("-l", "--log_dir",  type = str, help="Absolute path to directory where log files will be stored", default = "Arduino")
    args = vars(ap.parse_args())


    mapping_file = args["mappings"]
    program_file = args["sequence"]
    total_time = 30

    mapping=pd.read_csv(mapping_file)
    program=pd.read_csv(program_file, skip_blank_lines=True)

    device = LearningMemoryDevice(mapping, program, args["port"], args["log_dir"])
    device.off()

    daemons = device.prepare()
    device.run(total_time=total_time, daemons=daemons)
    device.exit.wait(total_time)
    device.total_off()
