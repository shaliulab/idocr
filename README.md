# FReTS
Developing Fly Real-time Transcription Scope


## Introduction
**FReTS** (**F**ly **Re**al-time **T**ranscription **S**cope) is an interdisciplinary platform which utilizes the real-time tracking system to interact with the animals' transcription activity hence possible behaviors via closed-loop control system, combined with external interferences, such as laser/light stimulation, odour delivery, electric shock, etc.

## METHODS

* `python Camera/live_tracking.py`: Makes use of an Arduino to provide a turn on/off sequence for 12 different pins and processes the image data collected from the resulting closed-loop experiment. The user can at any time visualize the state of all the pins being used in the output of the program:

This output shows that pins 11, 09, 07, 26, and 27 are ON, and all others OFF.

* `python Arduino/learning_memory.py`: Standalone program that, provided mapping and program files, controls the Arduino pins accordingly using multithreading. This way, image processing can still occur independently of the Arduino run i.e. one can have the same computer sending instructions to Arduino while still being able to do other processes without having to worry about time collisions. 
The software in this program is provided as a class. It can be imported in a separate script, which could carry out image processing.


```
2019-02-25 15:57:50.294773: Running
       11-VA 09-MA 07-IR 05-VI
        [x]   [x]   [x]   [ ]
22-LO1  [ ]               [ ] RO1-23
26-LO2  [x]               [x] RO2-27
30-LES  [ ]               [ ] RES-31
34-LL   [ ]               [ ]  RL-35
```