# Standard library imports
import datetime
import logging
import sys
import threading
import time

# Third party imports
import coloredlogs
import cv2
import imutils
import numpy as np
from pathlib import Path
from sklearn.cluster import KMeans

# Local application imports

from learnmem.server.trackers.features import Arena, Fly
from learnmem.server.io.cameras import CAMERAS
from learnmem.decorators import export, if_not_self_stream
from learnmem.configuration import LearnMemConfiguration
from learnmem import PROJECT_DIR

# Set up package configurations

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cv2_version = cv2.__version__
coloredlogs.install()

def crop_stream(img, crop):
    width = img.shape[1]
    fw = width//crop
    y0 = fw * (crop // 2)
    if len(img.shape) == 3:
        img = img[:, y0:(y0+fw), :]
    else:
        img = img[:, y0:(y0+fw)]
    return img


class CouldNotReadFrameError(Exception):
    """
    Used to signal that no more frames are coming from the camera
    """

class LessArenasThanTargetError(Exception):
    """
    Used to signal the target number of arenas (usually 20) was not detected in a frame
    """

@export
class SimpleTracker():

    _live_feed_path = '/tmp/last_img.jpg'
    row_all_flies = None
    frame_color = None
    frame_original = None

    columns = ["frame_count", "arena", "x", "y"]

    def __init__(self, control_thread, camera="opencv", video=None):
        """
        Setup video recording parameters.
        """

        self.recursive_calls = 0

        # Assignment
        self.control_thread = control_thread
        self.camera = camera
        self.video = video
        self.failed_read_frame = 0


        # Results variables
        # how many flies are found in the whole experiment
        # in a perfect recording, it should be nframes x nflies/frame
        self.found_flies = 0
        # frames recorded since pressing play
        self.frame_count = 0
        # frames recorded since pressing record
        self.record_frame_count = 0
        # flies detected in the last frame
        self.old_found = 0
        # number of arenas where no fly was detected
        self.missing_fly = 0

        CFG = LearnMemConfiguration()
        # Config variables
        self.fps = CFG.content["tracker"]["fps"]
        self.targets = CFG.content["arena"]["targets"]
        self.sampled_fps = 0
        self.block_size = CFG.content["arena"]["block_size"]
        self.param1 = CFG.content["arena"]["param1"]
        self.crop = CFG.content["tracker"]["crop"]
        self.kernel_factor = CFG.content["arena"]["kernel_factor"]
        self.kernel = np.ones((self.kernel_factor, self.kernel_factor), np.uint8)
        self.N = CFG.content["tracker"]["N"]


        self.failed_arena_path = Path(PROJECT_DIR, CFG.content['tracker']['fail'])
        self.failed_arena_path.mkdir(parents=True, exist_ok=True)


        ## TODO
        ## Find a way to get camera.Width.SetValue(whatever) to work
        ## Currently returns error: the node is not writable
        # if VIDEO_WIDTH != 1280:
        #     cap.set(3, 1280)
        # if VIDEO_HEIGHT != 1024:
        #     cap.set(4, 1024)


        self.status = True

        self.arenas = {}
        self.masks = {}


        display_feed_thread = threading.Thread(target=self.display_feed)
        display_feed_thread.start()


    def display_feed(self):
        #while not self.control_thread.exit.is_set() and type(self.control_thread.frame_color) is np.ndarray:
        while not self.control_thread.exit.is_set():

            try:
                cv2.imwrite(self._live_feed_path, self.control_thread.frame_color)
                time.sleep(.2)
            except Exception as e:
                logger.exception(e)


    # @if_not_self_stream
    def load_camera(self):
        """
        Populate the stream attribute of the Tracker class
        Make it an instance of the classes in CAMERAS.py
        """

        if self.video is not None:
            self.video = Path(self.video)

            if self.video.is_file():
                self.stream = CAMERAS[self.camera](self, self.video.__str__())
            else:
                logger.error("Video under provided path not found. Check for typos")
        else:
            self.stream = CAMERAS[self.camera](self, 0)

        if self.fps and self.video:
            # Set the FPS of the camera
            self.stream.set_fps(self.fps)

        self.video_width, self.video_height = self.stream.get_dimensions()
        logger.info("Stream has shape w: %d h:%d", self.video_width, self.video_height)

    def init_image_arrays(self):
        """
        Initialize containers for the images that will be produced by the device
        These are required for the GUI to display something before start
        """

        # Make accu_image an array of size heightxwidthxnframes that will
        # store in the :, :, i element the result of the tracking for frame i
        self.accu_image = np.zeros((self.video_height, self.video_width, self.N), np.uint8)

        # self.img = np.zeros((self.video_height, self.video_width, 3), np.uint8)
        self.transform = np.zeros((self.video_height, self.video_width), np.uint8)
        self.gray_masked = np.zeros((self.video_height, self.video_width), np.uint8)
        self.frame_color = np.zeros((self.video_height, self.video_width, 3), np.uint8)
        self.gray_color = np.zeros((self.video_height, self.video_width, 3), np.uint8)
        self.gray_gui = np.zeros((self.video_height, self.video_width), np.uint8)

    def rotate_frame(self, img, rotation=180):
        # Rotate the image by certan angles, 0, 90, 180, 270, etc.
        rows, cols = img.shape[:2]
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), rotation, 1)
        img_rot = cv2.warpAffine(img, M, (cols, rows))
        return img_rot

    def annotate_frame(self, img):
        """
        Take a np.array and annotate it to provide info about frame number and time
        """

        ## TODO Dont make coordinates of text hardcoded
        ###################################################
        cv2.putText(img, 'Frame: '+ str(self.record_frame_count), (25, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        cv2.putText(img, 'Time: '+  str(int(self.control_thread.timestamp_seconds)), (1000, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        cv2.putText(img, 'LEFT', (25, 525), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        cv2.putText(img, 'RIGHT', (1100, 525), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        return img

    def find_arenas(self, gray, RangeLow1 = 0, RangeUp1 = 255):
        """
        Performs Otsu thresholding followed by morphological transformations to improve the signal/noise.
        Input image is the average image
        Output is a tuple of length 2, where every elemnt is either a list of contours or None (if no contours were found)

        More info on Otsu thresholding: https://docs.opencv.org/3.4/d7/d4d/tutorial_py_thresholding.html

        gray: Gray frame as output of read_frame()
        RangeLow1: value assigned to pixels below the Otsu threshold
        RangeUp1: value assigned to pixels above the Otsu threshold
        kernel_factor: size of the square kernel used in blurring and openings
        """

        # assign the grayscale to the ith frame in accu_image
        self.accu_image[:, :, self.frame_count % self.N] = gray
        if self.frame_count > 1:
            average = np.average(self.accu_image[:, :, :self.frame_count], 2).astype('uint8')
        else:
            average = self.accu_image[:, :, self.frame_count].astype('uint8')

        image_blur = cv2.GaussianBlur(average, (self.kernel_factor, self.kernel_factor), 0)
        _, thresholded = cv2.threshold(image_blur, RangeLow1, RangeUp1, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        #arena_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, self.kernel, iterations = 2)

        if cv2_version[0] == '4':
            arena_contours, _ = cv2.findContours(thresholded, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, arena_contours, _ = cv2.findContours(thresholded, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


        # to merge contours belonging to the same chamber
        # specially on ROI 10
        contour_mask = np.zeros_like(gray)

        for c in arena_contours:
            cv2.fillPoly(contour_mask, pts = [c], color=(255, 255, 255))



        dilation = cv2.dilate(contour_mask, (5, 5), 10)
        erosion = cv2.erode(dilation, (5, 5), 10)

        # cv2.imshow('thr', image1)
        # cv2.imshow('erosion', erosion)
        # cv2.imshow('contour mask', contour_mask)
        # if cv2.waitKey(33) == ord('q'):
        #     self.close()

        if cv2_version[0] == '4':
            arena_contours, _ = cv2.findContours(erosion, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, arena_contours, _ = cv2.findContours(erosion, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        return arena_contours

    def track(self):

        CFG = LearnMemConfiguration()

        targets = CFG.content["arena"]["targets"]

    # THIS FUNCTION NEEDS TO BE SPLIT INTO AT LEAST 2

        if not self.control_thread.exit.is_set():
            # # Check if experiment is over
            # if self.control_thread.timestamp_seconds > self.control_thread.duration:
            #     logger.info("Experiment duration is reached. Closing")
            #     #self.save_record()
            #     return False

            # How much time has passed since we started tracking?
            if self.control_thread.record_event.is_set():
                self.control_thread.timestamp_datetime = datetime.datetime.now() - self.control_thread.record_start
                self.control_thread.timestamp_seconds = self.control_thread.timestamp_datetime.total_seconds()

            # Read a new frame
            success, frame = self.stream.read_frame()
            self.frame_original

            # If ret is False, a new frame could not be read
            # Exit
            if not success:
                if self.control_thread.video is None:
                    print(success)
                    print("Closing")
                    self.failed_read_frame =+ 1
                    logger.warning('Recursive call to track() {}'.format(self.recursive_calls))
                    raise CouldNotReadFrameError("Could not read frame")
                else:
                    logger.info("Stream or video is finished. Closing")
                    self.close()
                    self.control_thread.stream_finished = True
                    return False


            frame = crop_stream(frame, self.crop)

            # Make single channel i.e. grayscale
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_color = frame
            else:
                gray = frame.copy()
                gray_color = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

            # Annotate frame
            frame_color = self.annotate_frame(gray_color)

            # Find arenas for the first N frames
            if self.frame_count < self.N and self.frame_count > 0 or not self.control_thread.arena_ok_event.is_set():
                self.arena_contours = self.find_arenas(gray)

            if self.arena_contours is None:
                found_targets = 0
            else:
                found_targets = len(self.arena_contours)

            if found_targets < int(targets):
                self.frame_count += 1
                self.control_thread.frame_color = gray_color
                raise LessArenasThanTargetError("Number of putative arenas found less than target. Discarding frame")


            transform = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, self.block_size, self.param1)
            self.transform = transform

            arenas_list = [None] * targets


            # Initialize an arena identity that will be increased with 1
            # for every validated arena i.e. not on every loop iteration!
            id_arena = 1
            # For every arena contour detected

            for arena_contour in self.arena_contours:

                # Initialize an Arena object
                arena = Arena(tracker = self, contour = arena_contour)
                # and compute parameters used in validation and drawing
                arena.corners = arena.compute()
                # Validate the arena
                # If not validated, move on the next arena contour
                # i.e. ignore the current arena
                if not arena.validate():
                    # move on to next i.e. continue to the next iteration
                    # continue means we actually WON'T continue with the current arena
                    continue

                elif id_arena <= targets:
                    arenas_list[id_arena-1] = arena
                    # Update the id_arena to account for one more arena detected
                    id_arena += 1
                else:
                    break

            found_arenas = np.sum([a is not None for a in arenas_list])

            if found_arenas != self.targets:
                self.frame_count += 1
                self.control_thread.frame_color = gray_color
                self.control_thread.fraction_area *= 0.99
                raise LessArenasThanTargetError("Number of arenas found not equal to target. Discarding frame")


            columns = CFG.content['arena']['columns']
            x_coord = np.array([a.corners[1][0] for a in arenas_list])
            kmeans = KMeans(n_clusters=columns).fit(x_coord.reshape(len(x_coord), 1))

            cluster_mean_x = [0, ] * columns
            cluster_centers = list(range(columns))
            for i, c in enumerate(range(columns)):
                cluster_mean_x[i] = np.mean(x_coord[kmeans.labels_ == c])

            indices = sorted(range(len(cluster_mean_x)), key=lambda k: cluster_mean_x[k])
            labels = np.array(cluster_centers)[indices][kmeans.labels_]
            #print(labels)

            for i, a in enumerate(arenas_list):
                a.set_column(labels[i])


            # sort arenas by position!!
            sorted_arenas_list = []
            # sort the arenas_list using the br corner attribute (.corners[1])
            # the corner is a tuple showing (x, y)
            # we want to sort first on y ([1]) and then on x ([0])
            # both in decreasing order because the



            sorted_arenas_br_to_tl_horizontally = sorted(arenas_list, key=lambda a: (a.column, a.corners[1][1]))

            self.row_all_flies = {}

            for identity, arena in enumerate(sorted_arenas_br_to_tl_horizontally):

                arena.set_id(identity+1)

                # If validated, keep analyzing the current arena
                frame_color = arena.draw(frame_color)

                # Make a mask for this arena
                ## TODO Right now the masking module does not work
                ## and is not required either
                mask = arena.make_mask(gray.shape[:2])

                ## DEBUG
                ## Add the arena to the dictionary
                self.arenas[arena.identity] = arena
                self.masks[arena.identity] = mask

                ## Find flies in this arena
                gray_masked = cv2.bitwise_and(self.transform, mask)
                fly_contours = arena.find_flies(gray_masked, self.kernel)

                #print('There are {} potential flies found in arena {}'.format(len(fly_contours), arena.identity))

                # Initialize a fly identity that will be increased with 1
                # for every validated fly i.e. not on every loop iteration!
                id_fly = 1

                putative_flies = []

                # For every arena contour detected
                for fly_contour in fly_contours:
                    # Initialize a Fly object
                    fly = Fly(tracker=self, arena=arena, contour=fly_contour, identity=id_fly)
                    # and compute parameters used in validation and drawing
                    fly.compute()


                    # If not validated, move on the next fly contour
                    # i.e. ignore the current fly
                    if not fly.validate(gray):
                        logger.debug("Fly not validated")
                        continue

                    putative_flies.append(fly)

                if len(putative_flies) == 0:
                    self.missing_fly += 1
                    # fname = str(self.record_frame_count) + "_" + str(arena.identity) + ".tiff"
                    # gray_crop = gray[arena.tl_corner[1]:arena.br_corner[1], arena.tl_corner[0]:arena.br_corner[0]]
                    # cv2.imwrite(Path(self.failed_arena_path, fname).__str__(), gray_crop)
                    continue
                elif len(putative_flies) > 1:
                    logger.debug("Arena {} in frame {}. Multiple flies found".format(arena.identity, self.frame_count))
                    fly = sorted(putative_flies, key = lambda f: f.area, reverse=True)[0]
                else:
                    fly = putative_flies[0]


                logger.debug("Fly {} in arena {} validated with area {} and length {}".format(fly.identity, fly.arena.identity, fly.area, fly.diagonal))

                row = {
                    "frame": self.frame_count,
                    "arena": arena.identity,
                    #"fly": fly.identity,
                    "x": fly.x_corrected,
                    "y": fly.y_corrected,
                    }

                self.row_all_flies[arena.identity] = row

                self.found_flies += 1

                # Draw the fly
                frame_color = fly.draw(frame_color, self.frame_count)

                # Add the fly to the arena
                arena.fly = fly

            ########################################
            ## End for loop over all putative arenas

            self.frame_color = frame_color


            # Update GUI graphics
            self.control_thread.frame_color = frame_color
            for i, arena in enumerate(sorted_arenas_br_to_tl_horizontally):
                arena_crop = arena.crop(frame_color)
                self.control_thread.stacked_arenas[i] = imutils.resize(arena_crop, width=arena_crop.shape[1]*3)

            # TODO: Make into utils function
            #self.control_thread.stacked_arenas = self.stack_arenas(arenas_dict)

            # Print warning if number of flies in new frame is not the same as in previous
            if self.old_found != self.found_flies:
                logger.debug("Found {} flies in frame {}".format(self.found_flies, self.frame_count))
            self.old_found = self.found_flies
            self.found_flies = 0

            self.update_counts()


            return True

        #########################
        ## End if
        ##

        else:
            #self.save_prompt()
            return None

    def update_counts(self):
        self.frame_count += 1
        if self.control_thread.record_event.is_set():
                self.record_frame_count += 1

        if self.frame_count % 100 == 0:
            logger.info("Frame #{}".format(self.frame_count))



    def sample_fps(self, interval_duration=2):

        while not self.control_thread.exit.is_set():
            before = self.frame_count
            self.control_thread.exit.wait(interval_duration)
            after = self.frame_count
            sampled_fps = (after - before) / interval_duration
            self.sampled_fps = sampled_fps

    def _sample_fps(self):

        sample_fps_thread = threading.Thread(
            name = "sample_fps",
            target = self.sample_fps,
            kwargs={"interval_duration": 2}
        )
        sample_fps_thread.start()


    def run(self):
        """
        Start tracking in a while loop
        Munge processed frames and masks
        When while is finished, run self.close()
        Signal the exit event has been set if not yet
        This is the target function of the intermediate thread
        and it runs self.track an indefinite amount of time
        """
        error_counts = {LessArenasThanTargetError: 0, CouldNotReadFrameError: 0}
        self.status = True
        while self.status and not self.control_thread.exit.is_set():
            try:
                self.status = self.track()
                self._sample_fps()
                self.merge_masks()
                self.control_thread.gray_gui = cv2.bitwise_and(self.transform, self.main_mask)
                self.recursive_calls += 1

            except (LessArenasThanTargetError, CouldNotReadFrameError) as e:
                # status is one of the errors that track can return
                # increase the counter accordingly
                error_counts[type(e)] += 1
                for error, count in error_counts.items():
                    if count > 99999999999999999999999:
                        print(error_counts)
                        raise error

                self.status = True

        self.close()

    def toprun(self):
        """
        Create an intermediate thread between the main
        and the tracker thread, and start it
        """

        tracker_thread = threading.Thread(
            name = "tracker_thread",
            target = self.run
        )

        tracker_thread.start()
        self.control_thread.tracker_thread = tracker_thread
        return None

    def close(self):
        """
        Release thre stream
        Save the cached data
        If the exit event is not yet set, call control_thread.close()
        """
        self.stream.release()
        self.control_thread.saver.stop_video()
        logger.info("Tracking stopped")
        logger.info("{} arenas in {} frames analyzed".format(20 * self.frame_count, self.frame_count))
        logger.info("Number of arenas that fly is not detected in is {}".format(self.missing_fly))
        self.control_thread.saver.store_and_clear()

        # if not self.control_thread.exit.is_set(): self.control_thread.close()

    def merge_masks(self):

        masks = self.masks.values()
        if len(masks) != 0:
            masks = np.array(list(masks))
            main_mask = np.bitwise_or.reduce(masks)
        else:
            main_mask = np.full((self.video_height, self.video_width, 3), 255, dtype=np.uint8)

        self.main_mask = main_mask

if __name__ == "__main__":
    import argparse
    from .control_thread import control_thread

    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video")
    ap.add_argument("-c", "--camera", type = str, default = "opencv", help="Stream source")
    ap.add_argument("-g", "--gui", type = str, help="tkinter/opencv")
    args = vars(ap.parse_args())

    control_thread = ControlThread(track = True, camera = args["camera"], video = args["video"], gui = args["gui"])
    control_thread.start()


