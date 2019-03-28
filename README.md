# FReTS
Developing Fly Real-time Transcription Scope


## Introduction
**FReTS** (**F**ly **Re**al-time **T**ranscription **S**cope) is an interdisciplinary platform which utilizes the real-time tracking system to interact with the animals' transcription activity hence possible behaviors via closed-loop control system, combined with external interferences, such as laser/light stimulation, odour delivery, electric shock, etc.


## Run the program
Please make sure the environment is using

* Python3.6 (ideally python3.6.3)
* Opencv 4.0.0 

A python environment containing this and al the required packages is available under:
```
/home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python
```

If you have not downloaded the software yet:

1- Open a terminal and run
```
git clone https://github.com/VIBFlySleepLab/FReTS
```
this will download the Python code

Enter the downloaded folder and run

```
/home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python -m FReTS --track --camera pylon --arduino --mapping mappings/main.csv --program programs/test_28_march.csv --duration 120
```
This will trigger the opening of the following window

![](static/readme/startup.png) 

loaded with the following settings:

* Use the pylon camera to track flies
* Run the program contained in test_28_march.csv
* Close in 2 hours (120 minutes)

Pressing the play button will start the tracking and the arduino events
You can pause and play it again for whatever reason.
The program can be closed by clicking on the top right x or pressing Control C on the terminal window that was used to launch the program 

## Use the output data

By default tracking and arduino events data are recorded to .csv files `data/` and `metadata/` respectively. The filenames are the same and follow the pattern:

*prefix* _ *date* _ *time*

* prefix is set in the config.yaml file (look at the **store** subentry in the arduino and tracker entries. Default is **store** for both. It can be changed at will!
* date follows the format year-month-day.
* time follows the format hour-minute-second.

