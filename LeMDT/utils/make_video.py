import cv2
import numpy as np
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video")
args = vars(ap.parse_args())

# Define the codec and create VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'MJPG')

frame = cv2.imread("image_0001.tiff")

out = cv2.VideoWriter(args["video"], fourcc, 2, (frame.shape[1], frame.shape[0]))
n=77
for i in range(1, n+1):
    filename = "image_"+str(i).zfill(4) + ".tiff"
    print(filename)
    frame = cv2.imread(filename)
    print(frame)
    if not frame is None:
#        frame = cv2.flip(frame,0)

        # write the flipped frame
        out.write(frame)

        cv2.imshow('frame',frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        break

# Release everything if job is finished
out.release()
cv2.destroyAllWindows()
