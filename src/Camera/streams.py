class PylonStream():
    def __init__(self, video=None):
        print("[INFO] Starting a pylon camera!")

        # The exit code of the sample application.
        exitCode = 0
        ## TODO
        ## Check camera is visible!
        cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        # Print the model name of the camera.
        print("Using device ", cap.GetDeviceInfo().GetModelName())
    
        # The parameter MaxNumBuffer can be used to control the count of buffers
        # allocated for grabbing. The default value of this parameter is 10.
        cap.MaxNumBuffer = 5
    
        countOfImagesToGrab = 100
        # Start the grabbing of c_countOfImagesToGrab images.
        # The camera device is parameterized with a default configuration which
        # sets up free-running continuous acquisition.
        cap.StartGrabbingMax(countOfImagesToGrab)
        self.cap = cap 

    def get_fps(self):
        fps = self.cap.AcquisitionFrameRateAbs.GetValue()
        return fps

    def get_width(self):
        width = self.cap.Width.GetValue()
        return width

    def get_height(self):
        height = self.cap.Height.GetValue()
        return height 


    def get_time_position(self, frame_count):
        t = frame_count / self.get_fps()
        return t

    def set_fps(self, fps):
        self.stream.AcquisitionFrameRateAbs.SetValue(fps)

    def read_frame(self):
        # Wait for an image and then retrieve it. A timeout of 5000 ms is used.
        grabResult = self.cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        self.grabResult = grabResult
        # Image grabbed successfully?
        ret = grabResult.GrabSucceeded()
        if ret:
            # Access the image data.
            #print("SizeX: ", grabResult.Width)
            #print("SizeY: ", grabResult.Height)
            img = grabResult.Array
            return ret, img
        return False, None

    def release(self):
        self.grabResult.Release()

class StandardStream():

    def __init__(self, video=None):
        s = 0 if video is None else video
        if s == 0: print("[INFO] Capturing stream!")
        if s != 0: print("[INFO] Opening {}!".format(s))
        self.cap = cv2.VideoCapture(s)

    def get_fps(self):
        fps = self.cap.get(5)
        if fps == 0:
            return 2
        return fps

    def get_time_position(self, frame_count):
        t = frame_count / self.get_fps()
        return t

    def get_width(self):
        width = int(self.cap.get(3))
        return width

    def get_height(self):
        height = int(self.cap.get(4))
        return height 

    def set_fps(self, fps):
        if self.get_fps() != fps:
            print("[INFO] Setting fps to {}".format(fps))
            self.cap.set(5, fps)

 #   def set_width(self, width):
 #       if self.stream.get_width() != width:
 #           self.stream.set(3, width)
 #   def set_height(self, height):
 #       if self.stream.get_height() != height:
 #           self.stream.set(4, height)

    def read_frame(self):
        ret, img = self.cap.read()
        return ret, img
   
    def release(self):
        self.cap.release()
