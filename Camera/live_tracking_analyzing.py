import numpy as np
import argparse
import datetime
import cv2
import time

class Tracker():

    def __init__(self, author, path_to_video=None):
        """
        Setup video recording parameters.

        rotation:
        fps: how many frames are fit in 1 second. This is different for very stream/video
             common values are powers of 10: 10, 30, 100...
        duration: in seconds
        """


        # maybe it should be possible to change these params at initialization
        self.rotation = 180
        self.duration = 1200 
        self.RangeLow1 = 0
        self.RangeUp1 = 255  
        kernel_factor = 5
        self.kernel = np.ones((kernel_factor,kernel_factor), np.uint8)
        self.kernel_factor = kernel_factor
        self.N = 10
        self.frame_count = 0
        self.min_arena_area = 1000
        self.max_object_area = 200
        self.min_object_area = 15
        self.min_object_length = 10
        self.min_obj_arena_dist = 5
        self.missing_fly = 0


        # dst = cv2.warpAffine(img, M, (VIDEO_WIDTH,VIDEO_HEIGHT))
        self.record_to_save_header = ['Operator', 'Date_Time', 'Experiment', '', 'Arena', 'Object', 'frame', 'time_point', 'CoordinateX', 'CoordinateY', 'RelativePosX', 'RelativePosY']
        Operator = author

        now = datetime.datetime.now()
        self.Date_time = now.strftime("%Y_%m_%dT%H_%M_%S")
        
        self.record_to_save = ["Frame\tTimePos\tArena\tFlyNo\tFlyPosX\tFlyPosY\tArenaCenterX\tArenaCenterY\tRelativePosX\tRelativePosY\n"]
        
        if path_to_video is None:
            print("[INFO] starting video stream...")
            cap = cv2.VideoCapture(0)
            fps = cap.get(cv2.CAP_PROP_FPS)
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
            cap.set(5, 2)
            time.sleep(0.1)
        
        
        # otherwise, grab a reference to the video file
        else:
            cap = cv2.VideoCapture(path_to_video)

        self.cap = cap
        self.cam_fps = cap.get(5)
        print(self.cam_fps)
        self.accuImage = np.zeros((int(cap.get(4)), int(cap.get(3)), self.N), np.uint8)
        


    
    def track(self):
        frame_count = 0
        
        while 1:
            # Read one frame
            #frameNo = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    
            # time_position = int(cap.get(cv2.CAP_PROP_POS_MSEC))/1000
            frame_count +=1
            time_position = frame_count/self.cam_fps
            #time_position_int = round(time_position * self.fps)
            #print(time_position)
            #print(frame_count)
    
            ret, img_180 = self.cap.read()
            if not ret:
                break
    
            cv2.imshow("stream", img_180)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
            #if args["v"]:
    
            # Rotate the image by certan angles, 0, 90, 180, 270, etc.
            
            rows, cols = img_180.shape[:2]
            M = cv2.getRotationMatrix2D((cols/2,rows/2), self.rotation, 1)
            img = cv2.warpAffine(img_180,M,(cols,rows))
            
        
            if ret == True:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                cv2.putText(img,'Frame: '+str(frame_count), (25,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
                cv2.putText(img,'Time: '+str(time_position), (1000,25),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
                cv2.putText(img,'LEFT', (25,525),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
                cv2.putText(img,'RIGHT', (1100,525),  cv2.FONT_HERSHEY_SIMPLEX, 1, (40,170,0), 2)
        
        
                id_arena = 0
                
                if frame_count < self.N:
                    self.accuImage[:,:,frame_count] = gray
                    avgImage = np.average(self.accuImage, 2).astype('uint8')
        
                    image_blur = cv2.GaussianBlur(avgImage, (self.kernel_factor, self.kernel_factor), 0)
                    _, image1 = cv2.threshold(image_blur, self.RangeLow1, self.RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU) 
        
                    image1_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, self.kernel, iterations = 2)
        
                    (_,contours0,_) = cv2.findContours(image1_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                img3 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10)
                img3_opening = cv2.morphologyEx(img3, cv2.MORPH_OPEN, self.kernel)
                (im1, contours1, hierarchy1) = cv2.findContours(img3_opening, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
                print('There are {} objects found in contours1'.format(len(contours1)))
        
                for c in contours0:
                    if cv2.contourArea(c) < self.min_arena_area:
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
                        if cv2.contourArea(c1)>self.max_object_area or cv2.contourArea(c1)< self.min_object_area:
                            # print('Contour not found')
                            continue
        
                        cnt1 = c1
                        (x, y, w, h) = cv2.boundingRect(c1)
        
                        if np.sqrt(w**2+h**2) > self.min_object_length and gray[x,y] < 80:
        
                            M1 = cv2.moments(cnt1)
                            if M1['m00'] != 0 and M1['m10']:
                                cx1 = int(M1['m10']/M1['m00'])
                                cy1 = int(M1['m01']/M1['m00'])
                            if cv2.pointPolygonTest(c, (cx1,cy1), True) < self.min_obj_arena_dist:
                                continue
                            id_object += 1
                            print('Find contour'+str(id_object))
                            if id_object > 1:
                                cv2.putText(img, 'Error: more than one object found per arena', (25,40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                            elif id_object == 0:
                                self.missing_fly+=1
                                
                            record = str(frame_count) +"\t"+ str(time_position) +"\t"+ str(id_arena) +"\t"+ str(id_object) +"\t"+ str(cx1) +"\t"+ str(cy1) +"\t"+ str(CX1) +"\t" + str(CY1) +"\t"+ str(cx1-CX1) +"\t"+ str(cy1-CY1)+"\n"
                            self.record_to_save.append(record)
                            # cv2.drawContours(img, [cnt1], -1, [0,255,0], 1)
                            cv2.rectangle(img, (x,y), (x+w, y+h), (255,0,0),2)
                            print("Frame count is {}".format(frame_count))
        
                        
                        
                
                cv2.imshow('image', img)
    
        
                if cv2.waitKey(1) & 0xFF in [27, ord('q')] :
                    input_save = input("Do you want to save the file? (y/n) ")
                    if input_save in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
                        input_save1 = input("Do you want to add file name to the default one? (y/n) ")
                        if input_save1 in ['Y', 'Yes', 'YES', 'OK', 'yes', 'y']:
                            input_save_name = input("Please write your own filename: ")
                            filename = "{}_{}.txt".format(input_save_name, self.Date_time)
                            with open(filename, 'w') as f:
                                for rowrecord in self.record_to_save:
                                    f.write(rowrecord)
                            break
                        else:
                            filename = "{}.txt".format(self.Date_time)
                            with open(filename, 'w') as f:
                                for rowrecord in self.record_to_save:
                                    f.write(rowrecord)
                            break
                    else:
                        break
                elif time_position > self.duration:
                    filename = "{}.txt".format(self.Date_time)
                    with open(filename, 'w') as f:
                        for rowrecord in self.record_to_save:
                            f.write(rowrecord)
                    break
            else:
                break
            print("Number of frames that fly is not detected in is {}".format(self.missing_fly))
    
        #print("FPS is {}".format(self.cap.get(5)))
    
        self.cap.release()
        cv2.destroyAllWindows()
