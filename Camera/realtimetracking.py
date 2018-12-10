# USAGE
# python opencv_object_tracking.py
# python opencv_object_tracking.py --video dashcam_boston.mp4

# import the necessary packages
#from imutils.video import VideoStream
#from imutils.video import FPS
import argparse
#import imutils
import time
import cv2


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", type=str,
	help="path to input video file")

args = vars(ap.parse_args())

# extract the OpenCV version info
(major, minor) = cv2.__version__.split(".")[:2]

#check opencv version
if major == '2' :
	fgbg = cv2.BackgroundSubtractorMOG2()
if major == '3': 
	fgbg  = cv2.createBackgroundSubtractorMOG2()
	



# if a video path was not supplied, grab the reference to the web cam
if not args.get("video", False):
	print("[INFO] starting video stream...")
	vs = cv2.VideoCapture(2)
	time.sleep(1.0)
	VIDEO_WIDTH = vs.get(3)
	VIDEO_HEIGHT = vs.get(4)
	if VIDEO_WIDTH != 1280.0:
		vs.set(3, 1280.0)
	if VIDEO_HEIGHT != 1024.0:
		vs.set(4, 1024.0)
	time.sleep(0.5)
	print('Video resolution is %d by %d' %(vs.get(3), vs.get(4)))

# otherwise, grab a reference to the video file
else:
	vs = cv2.VideoCapture(args["video"])

coordinates = ["X", "Y"]
cx = []
cx1 = 0
cy = []
cy1 = 0

while True:
	# grab the current frame, then handle if we are using a
	# VideoStream or VideoCapture object

	_,frame = vs.read()
	#frame = frame[1] if args.get("video", False) else frame
	_, frame1 = cv2.threshold(frame, 90, 255, cv2.THRESH_BINARY_INV)
	# check to see if we are currently tracking an object
	if True:
		#apply background substraction
		fgmask = fgbg.apply(frame)
		fgmask1 = fgbg.apply(frame1)
		#fgmask = cv2.cvtColor(fgmask, cv2.COLOR_BGR2GRAY)
		# resize the frame (so we can process it faster) and grab the
		# frame dimensions
		#frame = imutils.resize(frame, width=600)

		#check opencv version
		if major == '2' : 
			(contours, hierarchy) = cv2.findContours(fgmask.copy(), cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
		if major == '3' : 
			(im2, contours, hierarchy) = cv2.findContours(fgmask.copy(), cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
		print("I found %d contours" % (len(contours)))
		#looping for contours

		(im3, contours1, hierarchy1) = cv2.findContours(fgmask1.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE) 
		

		for c in contours1:
			if cv2.contourArea(c) < 1000:
				continue
			cnt = c
			M = cv2.moments(cnt)
			print(M)
			if M['m00']!= 0 and M['m10']:
				#cx = cx.append(int(M['m10']/M['m00']))
				cx1 = int(M['m10']/M['m00'])
				#cy = cy.append(str(int(M['m01']/M['m00'])))
				cy1 = int(M['m01']/M['m00'])
				print("X: %d Y: %d" % (cx1, cy1))


				#coordinates = coordinates.append(cxy)

				
			print("Area of contour is %d" %(cv2.contourArea(c)))
			#get bounding box from countour
			#(x, y, w, h) = cv2.boundingRect(c)

			cv2.putText(frame1, "X: " +str(cx1), (100,40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50,170,50), 2)
			cv2.putText(frame1, "Y: " +str(cy1), (100,60), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50,170,50), 2)
			cv2.drawContours(frame1, [c], -1, (255,0,0),1)


			#cv2.drawContours(frame, [c], -1, (0,255,0), 3)
			#draw bounding box
			#cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
	

	cv2.imshow('foreground and background',frame1)
	#cv2.imshow('rgb',frame)

	if cv2.waitKey(1) & 0xFF == ord("q"):
		break

# if we are using a webcam, release the pointer
vs.release()

# close all windows
cv2.destroyAllWindows()


