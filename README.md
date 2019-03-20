# FReTS
Developing Fly Real-time Transcription Scope


## Introduction
**FReTS** (**F**ly **Re**al-time **T**ranscription **S**cope) is an interdisciplinary platform which utilizes the real-time tracking system to interact with the animals' transcription activity hence possible behaviors via closed-loop control system, combined with external interferences, such as laser/light stimulation, odour delivery, electric shock, etc.

## Instructions

1 **Connect the camera to the computer via LAN** 
2 **Run the open_camera.sh script to put it under the IP address that pylon expects**
 

```
bash /home/luna.kuleuven.be/u0127714/VIBFlySleepLab/FReTS/src/open_camera.sh
```
3 Run the python program to track flies and control the Arduino board


  3.1 **Go to the directory where the software is**
 
For now you will access Antonio's version of the program
and also Antonio's python environment, which has all required libraries installed :)

Do that by opening a terminal (Control + Alt + T *at the same time*) and paste the command below
```
cd /home/luna.kuleuven.be/u0127714/VIBFlySleepLab/FReTS
```

   3.2** Run the program!!**

## How to run

In the same terminal, paste the commands below:

### Without Arduino

Usually for debugging purposes

* Open the pylon camera and track flies (does not run Arduino)
```
cd /home/luna.kuleuven.be/u0127714/VIBFlySleepLab/FReTS # repeat of the command before
/home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python main.py --track --camera pylon 
```

### With Arduino

Before running with Arduino, we need to double check where is the Arduino board mounted (kind of similar to what happened with the IP camera). Make sure it is actually connected!
By default it is mounted in `/dev/` with name `ttyACM0`. However, it could have another name, like `ttyACM1`. You can easily check by running

```
ls /dev/ttyACM0
```

if the output you get is a green line that says `/dev/ttyACM0`, good to go! Otherwise, write it down and pass it with the `--port` flag in the commands below i.e. put at the end of  the command the following: `--port theOutputOfLs`


* Open the pylon camera, track flies and run the Arduino program encoded in program.csv assuming the pin mappings in pins_mapping.csv
```
/home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python main.py --track --camera pylon --arduino --mappings Arduino/mappings/main.csv --sequence Arduino/program/main.csv
```

* Open the pylon camera, track flies and run the Arduino program encoded in program.csv assuming the pin mappings in pins_mapping.csv and set the fps to 10
```
/home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python main.py --track --camera pylon --arduino--mappings Arduino/mappings/main.csv --sequence Arduino/program/main.csv --fps 10
```

## Troubleshooting

Please make sure the environment is using

* Python3.6 (ideally python3.6.3)
* Opencv 3.4.5 or Opencv 4.0.0

Otherwise, it might not work.

### Check OpenCV works properly

If OpenCV is capable of making videos, running the command below will create `test_video.mp4` and `test_video.avi` under `videos/`
```
 /home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python tests/tk-img2video.py -p "images/frame*tiff" -o videos/test_video
```

If OpenCV is capable of reading this videos, running any of this commands should return:
```
/home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python tests/check_video.py -v videos/test_video.avi
/home/luna.kuleuven.be/u0127714/anaconda3/envs/CV/bin/python tests/check_video.py -v videos/test_video.mp4
```
```
True
(1024, 1280, 3)
```

If instead you get:
```
False
None
```

your OpenCV installation is broken
