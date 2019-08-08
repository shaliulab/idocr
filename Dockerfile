FROM python:3
#RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY LeMDT /usr/src/app

RUN pip install opencv-contrib-python
RUN pip install pyfirmata
RUN wget https://github.com/basler/pypylon/releases/download/1.4.0/pypylon-1.4.0-cp37-cp37m-linux_x86_64.whl
RUN pip install pypylon-1.4.0-cp37-cp37m-linux_x86_64.whl
RUN pip install coloredlogs
RUN pip install imutils

#CMD ["python", "main.py·", "--track", "--camera", "pylon", "--arduino", "--mappings", "Arduino/mappings/main.csv", "--sequence", "Arduino/programs/main.csv", "--fps", "2"]
CMD ["sleep" "1000"]

