import cv2
import numpy as np
#import matplotlib.pyplot as plt
import time
import argparse
import datetime
import serial
from serial.tools import list_ports


ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video",        type = str, help="location to the video file")
ap.add_argument("-a", "--author",       type = str, help="Add name of the operator")
ap.add_argument("-s", "--save",         type = str, help="Save the file with a prefix")
ap.add_argument("-F", "--fps",          type = int, help="Set FPS for camera")
ap.add_argument("-T", "--duration",     type = int, help="Set total duration of tracking in seconds")
ap.add_argument("-NA", "--arenaNo",     type = int, help="Set total arena number")


args = vars(ap.parse_args())

if not args.get("fps", False):
    fps = 30
else:
    fps = args["fps"]
if not args.get("duration", False):
    duration = 100
else:
    duration = args["duration"]
if not args.get("author", False):
    author_name = None
else:
    author_name = args["author"]
if not args.get("arenaNo", False):
    arenaNo = 3
else:
    arenaNo = args["arenaNo"]

if not args.get("video", False):
    print("[INFO] starting video stream...")
    cap = cv2.VideoCapture(0)
    time.sleep(1)
  
    if VIDEO_WIDTH != 1280.0:
        cap.set(3, 1280.0)
    if VIDEO_HEIGHT != 1024.0:
        cap.set(4, 1024.0)
    cap.set(5, fps)
    time.sleep(1)
    print('VIDEO resolution is %d by %d !' % (cap.get(3), cap.get(4)))
# otherwise, grab a reference to the video file
else:
    cap = cv2.VideoCapture(args["video"])

VIDEO_POS = cap.get(0)
VIDEO_FRAME = cap.get(1)
VIDEO_WIDTH = cap.get(3)
VIDEO_HEIGHT = cap.get(4)
VIDEO_FPS = cap.get(5)
VIDEO_RGB = cap.get(16)

ImageCenter= (VIDEO_WIDTH/2, VIDEO_HEIGHT/2)
M = cv2.getRotationMatrix2D(ImageCenter, 180, 1.0)


# cam_fps = cap.get(5)

RangeLow = 50
RangeUp = 90    
RangeLow1 = 0
RangeUp1 = 255  

kernel_factor = 5
kernel = np.ones((kernel_factor,kernel_factor), np.uint8)

rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))

N =5

frame_counter = 0
min_arena_area = 1000
max_object_area = 200
min_object_area = 15

min_object_length = 15
min_obj_arena_dist = 5

gap_ratio = 0.1


# record_to_save_header = ['Operator', 'Date_Time', 'Experiment', '', 'Arena', 'Object', 'frame', 'time_point', 'CoordinateX', 'CoordinateY', 'RelativePosX', 'RelativePosY']
Operator = args["author"]
now = datetime.datetime.now()
Date_time = now.strftime("%Y_%m_%dT%H_%M_%S")

# record_to_save =["Frame\tTimePos\tArena\tFlyNo\tFlyPosX\tFlyPosY\tArenaCenterX\tArenaCenterY\tRelativePosX\tRelativePosY\n"]

record_to_save = []
record_to_save_list = []
contours_arena = []
arena_centroid = []

Stimulus_0 = 'MO'
Stimulus_1 = 'OCT'
Stimulus_2 = 'MCH'
Stimulus_3 = 'ESHOCK'
Stimulus_4 = 'RLIGHT'

dict_to_save ={ 'Frame'                     : 'Frame', 
                'TimePos'                   : 'TimePos', 
                'Arena'                     : 'Arena', 
                'FlyNo'                     : 'FlyNo', 
                'FlyPosX'                   : 'FlyPosX', 
                'FlyPosY'                   : 'FlyPosY', 
                'ArenaCenterX'              : 'ArenaCenterX', 
                'ArenaCenterY'              : 'ArenaCenterY', 
                'FlyRelPosX'                : 'FlyRelPosX', 
                'FlyRelPosY'                : 'FlyRelPosY',
                'ArenaLeftBoundaryX'        : 'ArenaLeftBoundaryX', 
                'ArenaRightBoundaryX'       : 'ArenaRightBoundaryX', 
                'ArenaLeftBoundaryY'        : 'ArenaLeftBoundaryY', 
                'ArenaRightBoundaryY'       : 'ArenaRightBoundaryY', 
                'L0'                        : Stimulus_0+'_L', 
                'R0'                        : Stimulus_0+'_R', 
                'L1'                        : Stimulus_1+'_L',
                'R1'                        : Stimulus_1+'_R', 
                'L2'                        : Stimulus_2+'_L', 
                'R2'                        : Stimulus_2+'_R', 
                'L3'                        : Stimulus_3+'_L',
                'R3'                        : Stimulus_3+'_R',
                'L4'                        : Stimulus_4+'_L',
                'R4'                        : Stimulus_4+'_R'
                }



right_sequence = ''

record_to_save_list.append(list(dict_to_save.values()))

missing_fly = 0

accuImage = np.zeros((int(cap.get(4)), int(cap.get(3)), N), np.uint8)
cam_fps = cap.get(cv2.CAP_PROP_FPS)

#start_to_tracking = input("Would you like to start tracking now? (y/n)")

while True:
    start_to_tracking = input("Would you like to start tracking now? (y/n)")
    if start_to_tracking in ['n', 'no', 'No', 'NO']:
        break
    elif start_to_tracking not in ['y', 'Y', 'Yes', 'YES', 'yes', 'OK', 'ok']:
        continue
    else:
        print("Starting tracking with fps: {} for duration of {} seconds".format(cam_fps, duration))
        # print('Initiating training system')
        time_zero = datetime.datetime.now()
        while True:
            # cam_pos_time = int(cap.get(cv2.CAP_PROP_POS_MSEC))/1000
            # cam_pos_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            frame_counter +=1
            
            # print(time_position)
            ret, img = cap.read()
            time_relative = (datetime.datetime.now()-time_zero)/1000
            
            # cam_fps = fps
            # time_position = frame_counter/cam_fps

            while    ret == True:
                gray_org = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                gray = cv2.warpAffine(gray_org, M, (VIDEO_WIDTH, VIDEO_HEIGHT))
                image_range = cv2.inRange(gray, RangeLow, RangeUp)
                #first_frames.append(gray)
                
                cv2.putText(img,'Frame: '+str(frame_counter), (25,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
                cv2.putText(img,'Time: '+str(time_relative), (1000,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
                
                id_arena = 0
                
                if frame_counter < N:
                    accuImage[:,:,frame_counter] = gray
                    # Calculte first N frames to get averaged image to avoid possible erros caused by fly contacting edges
                    avgImage = np.average(accuImage, 2).astype('uint8')


                    image_blur = cv2.GaussianBlur(avgImage, (kernel_factor, kernel_factor), 0)
                    _, image1 = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 
                    image1_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, kernel)
                    (_,contours_org,_) = cv2.findContours(image1_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for c_org in contours_org:
                        if cv2.contourArea(c_org) < min_arena_area:
                            continue
                        contours_arena.append(c_org)
                        M0 = cv2.moments(c_org)
                        if M0['m00'] != 0 and M0['m10']:
                            CX1 = int(M0['m10']/M0['m00'])
                            CY1 = int(M0['m01']/M0['m00'])
                        contours0_centroid = [CX1, CY1]
                        arena_centroid.append(contours0_centroid)
##################################################################################################################################################
                    contours0 = [x for _, x in sorted(zip(arena_order, contours_arena))]

                    ArenaNo_raw = len(contours_org)
                    if ArenaNo_raw > arenaNo:
                            print("Extra arena found! Try to combined arena separated by inner separator!")

                    elif ArenaNo_raw < arenaNo:
                        print("Detected less arena as expected! Check setup configuration and restart")
                        break


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
                                
                            record = str(frame_counter) +"\t"+ str(time_relative) +"\t"+ str(id_arena) +"\t"+ str(id_object) +"\t"+ str(cx1) +"\t"+ str(cy1) +"\t"+ str(CX1) +"\t" + str(CY1) +"\t"+ str(cx1-CX1) +"\t"+ str(cy1-CY1)+"\n"
                            record_to_save.append(record)
                            # cv2.drawContours(img, [cnt1], -1, [0,255,0], 1)
                            cv2.rectangle(img, (x,y), (x+w, y+h), (255,0,0),2)
                            print("Frame count is {}".format(frame_counter))

                        
                        
                #img_rotated = cv2.warpAffine(img, M, (VIDEO_WIDTH, VIDEO_HEIGHT))
                cv2.imshow('image', img)
                # time.sleep(1)

                if cv2.waitKey(1) & 0xFF in [27, ord('q')] :
                    input_save = input("Do you want to save the file? (yes/no) ")
                    if input_save in ['Y', 'Yes', 'YES', 'OK', 'yes']:
                        input_save1 = input("Do you want to add file name to the default one? (yes/no) ")
                        if input_save1 in ['Y', 'Yes', 'YES', 'OK', 'yes']:
                            input_save_name = input("Please write your own filename: ")
                            filename = "{}_{}.txt".format(input_save_name, Date_time)
                            with open(filename, 'w') as f:
                                for rowrecord in record_to_save:
                                    f.write(rowrecord)
                    break
                elif time_relative > duration:
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