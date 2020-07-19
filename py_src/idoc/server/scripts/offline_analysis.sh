#! /bin/bash

find  /home/vibflysleep/VIBFlySleep/LeMDT/lemdt_results/2020-06-10*/   -maxdepth 1 -name *original.avi > videos.txt

IFS=$'\r\n' GLOBIGNORE='*' command eval  'VIDEOS=($(cat videos.txt))'



