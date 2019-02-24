import cv2
import numpy as np
#import matplotlib.pyplot as plt
import time
import argparse
import datetime
from pyfirmata import Arduino, util


# Setup video recording parameters
# duration =1200
fps = 2
ROTATE_DEG = 180
VIBRATE_REPEAT = 10
VIBRATE_DURATION = 0.1 # second
# Setup PIN numbers
# Main Pins
PIN_VACUUM = 1
PIN_MAIN_VALVE = 2
PIN_IRLED = 3
PIN_VIBRATOR = 4
# Left Stimulus
PIN_LEFT_ORDOR_1 = 5
PIN_LEFT_ORDOR_2 = 6
PIN_LEFT_ESHOCK = 7
PIN_LEFT_LED_R = 8
# Right Stimulus
PIN_RIGHT_ORDOR_1 = 9
PIN_RIGHT_ORDOR_2 = 10
PIN_RIGHT_ESHOCK = 11
PIN_RIGHT_LED_R = 12

# Setup Time events in min

EVENT_TIME = [1, 5, 7, 10, 12, 18]
EVENT_DURA = [2, 1, 1,  1,  1,  2]
EVENT_PINS = [[PIN_LEFT_ORDOR_1, PIN_RIGHT_ORDOR_2],
              [PIN_LEFT_ORDOR_1, PIN_RIGHT_ORDOR_1, PIN_LEFT_ESHOCK, PIN_RIGHT_ESHOCK],
              [PIN_LEFT_ORDOR_2, PIN_RIGHT_ORDOR_2],
              [PIN_LEFT_ORDOR_1, PIN_RIGHT_ORDOR_1, PIN_LEFT_ESHOCK, PIN_RIGHT_ESHOCK],
              [PIN_LEFT_ORDOR_2, PIN_RIGHT_ORDOR_2],
              [PIN_LEFT_ORDOR_2, PIN_RIGHT_ORDOR_1]
                ]

EVENT_TIME_ON = EVENT_TIME * 60 * fps
EVENT_TIME_OFF = (EVENT_TIME + EVENT_DURA) * 60 * fps


# Initial setups, start main_valve, vacuum, IR LED, and shake of vibrator.
ARDUINO_COM = '/dev/ttyACM0'
board = Arduino(ARDUINO_COM)
# Turn on IR LED, MAIN VALVE and VACUUM 
board.digital[PIN_IRLED].write(1)
board.digital[PIN_MAIN_VALVE].write(1)
board.digital[PIN_VACUUM].write(1)
# Turn on vibrator to vibrate
for i in range(0,VIBRATE_REPEAT+1):
    board.digital[PIN_VIBRATOR].write(1)
    time.sleep(VIBRATE_DURATION)
    board.digital[PIN_VIBRATOR].write(0)
    time.sleep(VIBRATE_DURATION)


# Arguments to follow the command, adding video, etc options
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", type = str, help="location to the video file")
ap.add_argument("-a", "--author", type = str, help="Add name of the operator")
args = vars(ap.parse_args())

if not args.get("video", False):
    print("[INFO] starting video stream...")
    cap = cv2.VideoCapture(0)
    time.sleep(0.1)
    VIDEO_POS = cap.get(0)
    VIDEO_FRAME = cap.get(1)
    VIDEO_WIDTH = cap.get(3)
    VIDEO_HEIGHT = cap.get(4)
    VIDEO_FPS = cap.get(5)
    VIDEO_RGB = cap.get(16)

    if VIDEO_WIDTH != 1280:
        cap.set(3, 1280)
    if VIDEO_HEIGHT != 1024:
        cap.set(4, 1024)
    cap.set(5, fps)
    time.sleep(0.1)

    
# otherwise, grab a reference to the video file
else:
    cap = cv2.VideoCapture(args["video"])
# Set up general settings

print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
print('FPS is: {}'.format(int(cap.get(5))))

# time.sleep(1)
cam_fps = cap.get(5)
RangeLow = 50
RangeUp = 90    
RangeLow1 = 0
RangeUp1 = 255  
kernel_factor = 5
kernel = np.ones((kernel_factor,kernel_factor), np.uint8)



# dst = cv2.warpAffine(img,M,(VIDEO_WIDTH,VIDEO_HEIGHT))

N =10
first_frames = []
record_to_save_header = ['Operator', 'Date_Time', 'Experiment', '', 'Arena', 'Object', 'frame', 'time_point', 'CoordinateX', 'CoordinateY', 'RelativePosX', 'RelativePosY']
Operator = args["author"]
now = datetime.datetime.now()
Date_time = now.strftime("%Y_%m_%dT%H_%M_%S")

record_to_save =["Frame\tTimePos\tArena\tFlyNo\tFlyPosX\tFlyPosY\tArenaCenterX\tArenaCenterY\tRelativePosX\tRelativePosY\n"]

frame_counter = 0
min_arena_area = 1000
max_object_area = 200
min_object_area = 15
min_object_length = 10
min_obj_arena_dist = 5


missing_fly = 0

accuImage = np.zeros((int(cap.get(4)), int(cap.get(3)), N), np.uint8)
# cam_fps = cap.get(cv2.CAP_PROP_FPS)

input_totaltime = input("Do you want to start tracking now? (y/n)")

if input_totaltime in ['Y', 'yes', 'y', 'Yes', 'YES', 'OK']:
    while 1:
        # Read one frame
        #frameNo = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        # time_position = int(cap.get(cv2.CAP_PROP_POS_MSEC))/1000
        frame_counter +=1
        cam_fps = fps
        time_position = frame_counter/cam_fps
        time_position_int = round(time_position * fps)
        print(time_position)
        
        if time_position_int in EVENT_TIME_ON:
            for pins in EVENT_PINS[EVENT_TIME_ON.index(time_position_int)]:
                board.digital[pins].write(1)
        elif time_position_int in EVENT_TIME_OFF:
            for pins in EVENT_PINS[EVENT_TIME_ON.index(time_position_int)]:
                board.digital[pins].write(0)

        # Rotate the image by certan angles, 0, 90, 180, 270, etc.
        ret, img_180 = cap.read()
        
        rows, cols = img_180.shape[:2]
        M = cv2.getRotationMatrix2D((cols/2,rows/2),ROTATE_DEG,1)
        img = cv2.warpAffine(img_180,M,(cols,rows))
        

        if ret == True:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            image_range = cv2.inRange(gray, RangeLow, RangeUp)
            #first_frames.append(gray)
            
            cv2.putText(img,'Frame: '+str(frame_counter), (25,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
            cv2.putText(img,'Time: '+str(time_position), (1000,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
            cv2.putText(img,'LEFT', (25,525),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
            cv2.putText(img,'RIGHT', (1100,525),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)


            id_arena = 0
            
            if frame_counter < N:
                accuImage[:,:,frame_counter] = gray
                avgImage = np.average(accuImage, 2).astype('uint8')

                image_blur = cv2.GaussianBlur(avgImage, (kernel_factor, kernel_factor), 0)
                _, image1 = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 

                image1_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, kernel, interations = 2)

                (_,contours0,_) = cv2.findContours(image1_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            img3 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)
            img3_opening = cv2.morphologyEx(img3, cv2.MORPH_OPEN, kernel)
            (im1, contours1, hierarchy1) = cv2.findContours(img3_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            print('There are {} objects found in contours1'.format(len(contours1)))

            for c in contours0:
                if cv2.contourArea(c) < min_arena_area:
                    continue
                id_object = 0
                id_arena +=1
                cnt = c
                area_contour = cv2.contourArea(c)
                (X,Y,W,H) = cv2.boundingRect(c)
                M0 = cv2.moments(cnt)
                if M0['m00'] != 0 and M0['m10']:
                    CX1 = int(M0['m10']/M0['m00'])
                    CY1 = int(M0['m01']/M0['m00'])

                print('Contour {} has an area of {}'.format(id_arena, area_contour))
                cv2.putText(img, 'Arena '+str(id_arena), (X-50,Y-50),cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
                cv2.drawContours(img, [c], 0, (255,255,0), 1)
                cv2.rectangle(img, (X,Y), (X+W,Y+H), (0,255,255), 2)
                cv2.circle(img, (CX1, CY1), 2, (255,0,0), -1)
                
                for c1 in contours1:
                    if cv2.contourArea(c1)>max_object_area or cv2.contourArea(c1)< min_object_area:
                        # print('Contour not found')
                        continue

                    cnt1 = c1
                    (x, y, w, h) = cv2.boundingRect(c1)

                    if np.sqrt(w**2+h**2) > min_object_length and gray[x,y] < 80:

                        M1 = cv2.moments(cnt1)
                        if M1['m00'] != 0 and M1['m10']:
                            cx1 = int(M1['m10']/M1['m00'])
                            cy1 = int(M1['m01']/M1['m00'])
                        if cv2.pointPolygonTest(c, (cx1,cy1), True) < min_obj_arena_dist:
                            continue
                        id_object += 1
                        print('Find contour'+str(id_object))
                        if id_object > 1:
                            cv2.putText(img, 'Error: more than one object found per arena', (25,40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        elif id_object == 0:
                            missing_fly+=1
                            
                        record = str(frame_counter) +"\t"+ str(time_position) +"\t"+ str(id_arena) +"\t"+ str(id_object) +"\t"+ str(cx1) +"\t"+ str(cy1) +"\t"+ str(CX1) +"\t" + str(CY1) +"\t"+ str(cx1-CX1) +"\t"+ str(cy1-CY1)+"\n"
                        record_to_save.append(record)
                        # cv2.drawContours(img, [cnt1], -1, [0,255,0], 1)
                        cv2.rectangle(img, (x,y), (x+w, y+h), (255,0,0),2)
                        print("Frame count is {}".format(frame_counter))

                    
                    
            
            cv2.imshow('image', img)
            # time.sleep(1)

            if cv2.waitKey(1) & 0xFF in [27, ord('q')] :
                input_save = input("Do you want to save the file? (y/n) ")
                if input_save in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
                    input_save1 = input("Do you want to add file name to the default one? (y/n) ")
                    if input_save1 in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
                        input_save_name = input("Please write your own filename: ")
                        filename = "{}_{}.txt".format(input_save_name, Date_time)
                        with open(filename, 'w') as f:
                            for rowrecord in record_to_save:
                                f.write(rowrecord)
                        break
                    else:
                        filename = "{}.txt".format(Date_time)
                        with open(filename, 'w') as f:
                            for rowrecord in record_to_save:
                                f.write(rowrecord)
                        break
                else:
                    break
            elif time_position > duration*60:
                filename = "{}.txt".format(Date_time)
                with open(filename, 'w') as f:
                    for rowrecord in record_to_save:
                        f.write(rowrecord)
                break
        else:
            break
    print("Number of frames that fly is not detected in is {}".format(missing_fly))
    print("FPS is {}".format(cap.get(5)))

            
cap.release()
cv2.destroyAllWindows