#!/usr/local/bin/python3

import cv2
import argparse
import os
import glob

# Construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--pattern", required=False, default='*', help="pattern to be matched to select images.")
ap.add_argument("-o", "--output", required=False, default='output.mp4', help="output video file")
ap.add_argument("-f", "--fps", type=float, default=2.0, help="frames per second")
args = vars(ap.parse_args())

# Arguments
dir_path = '.'
pattern = args['pattern']
output = args['output']
fps = args['fps']

images = glob.glob(os.path.join(dir_path, pattern))
images = sorted(images)
#print(images)

# Determine the width and height from the first image
image_path = os.path.join(dir_path, images[0])
frame = cv2.imread(image_path)
cv2.imshow('video',frame)
height, width, channels = frame.shape
print('{} channels available'.format(channels))

# Define the codec and create VideoWriter object
avi = cv2.VideoWriter_fourcc(*'MJPG') # Be sure to use lower case
mp4 = cv2.VideoWriter_fourcc('f','m','p','4') # Be sure to use lower case
avi_out = cv2.VideoWriter(output + ".avi", avi, fps, (width, height))
mp4_out = cv2.VideoWriter(output + ".mp4", avi, fps, (width, height))

for image in images:

    image_path = os.path.join(dir_path, image)
    frame = cv2.imread(image_path)

    avi_out.write(frame) # Write out frame to video
    mp4_out.write(frame) # Write out frame to video

    cv2.imshow('video',frame)
    if (cv2.waitKey(1) & 0xFF) == ord('q'): # Hit `q` to exit
        break

# Release everything if job is finished
avi_out.release()
mp4_out.release()
cv2.destroyAllWindows()

print("The output video is {}.avi".format(output))
print("The output video is {}.mp4".format(output))
