FROM python:3
ADD Camera/live_tracking.py /
RUN pip install numpy
RUN pip install pandas
RUN pip install matplotlib
RUN pip install pyfirmata
RUN pip install datetime 
RUN pip install opencv-contrib-python
CMD ["python", "live_tracking.py"]
