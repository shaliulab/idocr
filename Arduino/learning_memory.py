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
import pickle # share pin state across threads
import glob
import os # file removal and we cleaning


class MyThread(threading.Thread):
    def start(self, program_start, total_time):
        self._kwargs["program_start"] = program_start
        self._kwargs["total_time"] = total_time 
        super(MyThread, self).start()


class LearningMemoryDevice():
    def __init__(self, mapping, program, port):
        self.mapping = mapping
        self.program = program 
        self.port = port
        pin_names = mapping.pin_id
        self.pin_state = {p: 0 for p in pin_names}
        self.board = Arduino(port)
        filehandler = open("pin_state.obj","wb")
        pickle.dump(self.pin_state,filehandler)
        filehandler.close()    

    def off(self):
        [self.board.digital[pin_number].write(0) for pin_number in self.mapping.pin_number]

    def prepare(self):
 
        # They are not run throughout the lifetime of the program, just at some interval and without intermitency
        daemons = {}
        
        count = {p: 0 for p in program.pin_id}
        for p in program.pin_id:
            d_pin_number = np.asscalar(mapping.query('pin_id == "{}"'.format(p))["pin_number"])
            d_start = np.asscalar(program.query('pin_id == "{}"'.format(p))["start"].iloc[count[p]])
            d_end =   np.asscalar(program.query('pin_id == "{}"'.format(p))["end"].iloc[count[p]])
            d_on =   np.asscalar(program.query('pin_id == "{}"'.format(p))["on"].iloc[count[p]])
            d_off =   np.asscalar(program.query('pin_id == "{}"'.format(p))["off"].iloc[count[p]])
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

            }
            d = MyThread(name=d_name,
                         target=self.pin_daemon,
                         kwargs = kwargs)
            d.setDaemon(True)
            daemons[d_name]=d
            count[p] += 1
            
        
        
        ## Signal start
        for i in range(2):
            for pin_number in mapping.pin_number:
                self.board.digital[pin_number].write(1)
                time.sleep(0.05)
                self.board.digital[pin_number].write(0)
                time.sleep(0.05)
                
        self.program_start = datetime.datetime.now()

        return daemons

    def toggle_pin(self, pin_number, value, message=None):
        # global self.pin_state
        self.board.digital[pin_number].write(value)
        filehandler = open("pin_state.obj","rb")
        pickle.load(filehandler)
        filehandler.close()
        self.pin_state[mapping.query('pin_number == "{}"'.format(pin_number))["pin_id"].iloc[0]]=value
        #print(self.pin_state["RIGHT_ODOUR_2"])
        filehandler = open("pin_state.obj","wb")
        pickle.dump(self.pin_state,filehandler)
        filehandler.close()
    
        self.show_circuit(mapping,#pin_state,
                    message)
 


    def pin_daemon(self, pin_number, total_time, program_start, start, end, on, off, n_iters=np.nan, d_name=""):
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
        
        # this is true for pins of type: CI, SI (intermitent)
        if n_iters != n_iters and on == on:
            n_iters = total_time // (on + off) # check if total time is accessible
            
        
        # halt all threads until program_start + sync_time is reached
        sleep1 = (program_start + datetime.timedelta(seconds=sync_time) - datetime.datetime.now()).total_seconds()
        time.sleep(sleep1)
    
        thread_start = datetime.datetime.now()    
        write_start_time(pin_number, "Pin {}-{} starts at {}\n", start)
        
        
        logging.debug("Running program on pin {}".format(pin_number))  
    
        # halt the thread until program_start + time sleep in the syncing + start is reached
        sleep2 = (thread_start + datetime.timedelta(seconds=start) - datetime.datetime.now()).total_seconds()
        if sleep2 > 0:
            time.sleep(sleep2)
        else:
            pass
    #         print(d_name.format(pin_number))
    #         print(sleep2)      
            
    #     write_start_time(pin_number, "Pin {}-{} executes at {}\n", start)
    
        
        p = mapping.query('pin_number == "{}"'.format(pin_number))["pin_id"].iloc[0]
    
        if n_iters == n_iters:    
    #         for _ in tqdm(range(int(n_iters))):
            for _ in range(int(n_iters)):
    
                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 1)
                
                runtime = datetime.datetime.now() - start_time
                if runtime.total_seconds() > 1.1*on:
                    warnings.warn("Runtime: {}".format(runtime))
                else:
                    sleep_time = on - runtime.total_seconds()
                    
                    time.sleep(sleep_time)
    
                start_time = datetime.datetime.now()
                self.toggle_pin(pin_number, 0)
                runtime = datetime.datetime.now() - start_time
                if runtime.total_seconds() > 1.1*off:
                    warnings.warn("Runtime: {}".format(runtime))
                else:
                    sleep_time = off - runtime.total_seconds()
                    time.sleep(sleep_time)
        else:
            # constitutive pins
            start_time = datetime.datetime.now()
            self.toggle_pin(pin_number, 1)
            sleep_time = end - start
            if sleep2 < 0:
                sleep_time += sleep2
    
            time.sleep(sleep_time)
            self.toggle_pin(pin_number, 0)
    
 
    def run(self, total_time, daemons):
        [d.start(self.program_start, total_time) for d in daemons.values()]


 
    def show_circuit(self, mapping,
                    #pin_state,
                    message=None, flush=True):
       #global pin_state
       
       pin_state_g = {p: "x" if v == 1 else "0" for p, v in self.pin_state.items()}
       #print(pin_state_g["RIGHT_ODOUR_2"])

       main_pins = mapping.query('pin_group == "main"')["pin_id"].values[1:]
       left_pins = mapping.query('pin_group == "left"')["pin_id"].values
       right_pins = mapping.query('pin_group == "right"')["pin_id"].values
       
       show_data = [pin_id2n(p) for p in main_pins] + [pin_state_g[p] for p in main_pins]
       show_data2 = [left_pair(p, pin_state_g) for p in left_pins] 
       show_data3 = [left_pair(p, pin_state_g)[::-1] for p in right_pins] 
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
           #clear line
       handle = open("pin_state.txt", "a+")
       handle.write(output)
       handle.close()


def pin_id2n(pin_id):
    return str(mapping.query('pin_id  == "'+pin_id+'"')["pin_number"].iloc[0]).zfill(2)

def left_pair(p, pin_state_g):
    return [pin_id2n(p), pin_state_g[p]]


def write_start_time(pin_number, message, start):
    
    handle = open("log_{}.txt".format(pin_number), "a+")
    handle.write(message.format(pin_number, start, datetime.datetime.now()))
    handle.close()

        

if __name__ == "__main__":

    mapping_file = "pins_mapping_breadboard.csv"
    program_file = "simplified_program3.csv"
    port = "/dev/ttyACM1"
    total_time = 30
    mapping=pd.read_csv(mapping_file)
    program=pd.read_csv(program_file, skip_blank_lines=True)
    device = LearningMemoryDevice(mapping, program, port)
    log_files = glob.glob('log*')
    for f in log_files + ["pin_state.txt"]:
        try:
            os.remove(f)
        except OSError:
            pass

    device.off()
    daemons = device.prepare()
    device.run(total_time=total_time, daemons=daemons)

    time.sleep(total_time)

