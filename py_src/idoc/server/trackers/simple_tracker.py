# Standard library imports
import logging

# Third party imports
import cv2
import imutils
import numpy as np
from sklearn.cluster import KMeans

# Local application imports

from idoc.server.trackers.features import Arena, Fly
from idoc.server.io.cameras import CAMERAS
from idoc.configuration import IDOCConfiguration
from idoc.server.core.base import Base, Root

# Set up package configurations

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

cv2_version = cv2.__version__ # pylint: disable=no-member

def crop_camera(img, crop):
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

class SimpleTracker(Base, Root):

    _live_feed_path = '/tmp/last_img.jpg'
    row_all_flies = {}
    _info = {}

    frame_color = None
    frame_original = None
    _columns = ["frame_count", "arena", "x", "y"]

    def __init__(self, *args, camera_name="opencv", video_path=None, **kwargs):
        r"""
        Setup video recording parameters.

        :param camera_name: Codename of the camera selected by the user.
        Must match one of the keys in CAMERAS
        :type camera_name: str

        :param video: Path to video file for offline tracking. If None, live tracking is performed.
        :type video: str
        """
        super().__init__(*args, **kwargs)

        # Load a camera
        self._camera_name = camera_name
        self.video_path = video_path
        self.load_camera(self.video_path)

        # tracking framerate
        # if we are reading from a video
        # it will be limited by the processing capacity of the PC
        # if we are reading from a live feed
        # unless the feed has very high FPS,
        # the tracking framerate is given by the camera framerate
        self._framerate = 0

        # Config variables
        config = IDOCConfiguration()
        self.targets = config.content["arena"]["targets"]
        self.sampled_framerate = 0
        self.block_size = config.content["arena"]["block_size"]
        self.param1 = config.content["arena"]["param1"]
        self.crop = config.content["tracker"]["crop"]
        self.kernel_factor = config.content["arena"]["kernel_factor"]
        self.kernel = np.ones((self.kernel_factor, self.kernel_factor), np.uint8)
        self.N = config.content["tracker"]["N"]
        self._delta_t = 2

        # Results variables
        # how many flies are found in the whole experiment
        # in a perfect recording, it should be nframes x nflies/frame
        self.found_flies = 0
        # frames recorded since pressing play
        self.frame_count = 0
        # flies detected in the last frame
        self.old_found = 0
        # number of arenas where no fly was detected
        self.missing_fly = 0

        self.stacked_arenas = []
        self.arena_contours = []
        self.fraction_area = 1

        self.arenas = {}
        self.masks = {}


    @property
    def columns(self):
        return self._columns

    @property
    def camera(self):
        return self._submodules["camera"]

    @camera.setter
    def camera(self, camera):
        self._submodules["camera"] = camera
        self._settings.update(camera.settings)

    # @if_not_self_camera
    def load_camera(self, video_path=None):
        """
        Populate the camera attribute of the Tracker class
        Make it an instance of the classes in CAMERAS.py
        """

        config = IDOCConfiguration()
        self._CameraClass = CAMERAS[self._camera_name] # pylint: disable=invalid-name

        self.camera = self._CameraClass(video_path=video_path)

        # TODO What happens when we are reading a video?
        self.camera.framerate = config.content["tracker"]["framerate"]
        self.receive()

        logger.info("camera has shape w: %d h:%d", *self.camera.resolution)

    def init_image_arrays(self):
        """
        Initialize containers for the images that will be produced by the device
        These are required for the GUI to display something before start
        """

        # TODO Sort this mess

        # Make accu_image an array of size heightxwidthxnframes that will
        # store in the :, :, i element the result of the tracking for frame i
        self.accu_image = np.zeros((*self.camera.shape, self.N), np.uint8)

        # self.img = np.zeros((self.video_height, self.video_width, 3), np.uint8)
        self.transform = np.zeros(*self.camera.shape, np.uint8)
        self.gray_masked = np.zeros(self.camera.shape, np.uint8)
        self.frame_color = np.zeros(self.camera.shape, np.uint8)
        self.gray_color = np.zeros(self.camera.shape, np.uint8)
        self.gray_gui = np.zeros(self.camera.shape, np.uint8)

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
        # cv2.putText(img, 'Frame: '+ str(self.record_frame_count), (25, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        # cv2.putText(img, 'Time since tracker running: '+  str(int(self.timestamp_seconds)), (1000, 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        cv2.putText(img, 'LEFT', (25, 525), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        cv2.putText(img, 'RIGHT', (1100, 525), cv2.FONT_HERSHEY_SIMPLEX, 1, (40, 170, 0), 2)
        return img

    def find_arenas(self, gray, range_low_1=0, range_up_1=255):
        """
        Performs Otsu thresholding followed by morphological transformations to improve the signal/noise.
        Input image is the average image
        Output is a tuple of length 2, where every elemnt is either a list of contours or None (if no contours were found)

        More info on Otsu thresholding: https://docs.opencv.org/3.4/d7/d4d/tutorial_py_thresholding.html

        gray: Gray frame as output of read_frame()
        range_low_1: value assigned to pixels below the Otsu threshold
        range_up_1: value assigned to pixels above the Otsu threshold
        kernel_factor: size of the square kernel used in blurring and openings
        """

        # assign the grayscale to the ith frame in accu_image
        self.accu_image[:, :, self.frame_count % self.N] = gray
        if self.frame_count > 1:
            average = np.average(self.accu_image[:, :, :self.frame_count], 2).astype('uint8')
        else:
            average = self.accu_image[:, :, self.frame_count].astype('uint8')

        image_blur = cv2.GaussianBlur(average, (self.kernel_factor, self.kernel_factor), 0)
        _, thresholded = cv2.threshold(image_blur, range_low_1, range_up_1, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        #arena_opening = cv2.morphologyEx(image1, cv2.MORPH_OPEN, self.kernel, iterations = 2)

        if cv2_version[0] == '4':
            arena_contours, _ = cv2.findContours(thresholded, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        else:
            _, arena_contours, _ = cv2.findContours(thresholded, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


        # to merge contours belonging to the same chamber
        # specially on ROI 10
        contour_mask = np.zeros_like(gray)

        for contour in arena_contours:
            cv2.fillPoly(contour_mask, pts=[contour], color=(255, 255, 255))



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
        # TODO  Either rewrite the whole thing
        # ditch for an already existing Tracker class
        # that we can integrate here

        config = IDOCConfiguration()
        targets = config.content["arena"]["targets"]

        if not self.stopped:

            # Read a new frame
            _, frame = self.camera.read_frame()
            frame = crop_camera(frame, self.crop)

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
            if self.frame_count < self.N and self.frame_count > 0 or not self.ready:
                self.arena_contours = self.find_arenas(gray)

            if self.arena_contours is None:
                found_targets = 0
            else:
                found_targets = len(self.arena_contours)

            if found_targets < int(targets):
                self.frame_count += 1
                self.frame_color = gray_color
                raise LessArenasThanTargetError("Number of putative arenas found less than target. Discarding frame")


            if not self.ready:
                return True


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

                if id_arena <= targets:
                    arenas_list[id_arena-1] = arena
                    # Update the id_arena to account for one more arena detected
                    id_arena += 1
                else:
                    break

            found_arenas = np.sum([a is not None for a in arenas_list])

            if found_arenas != self.targets:
                self.frame_count += 1
                raise LessArenasThanTargetError("Number of arenas found not equal to target. Discarding frame")


            columns = config.content['arena']['columns']
            x_coord = np.array([a.corners[1][0] for a in arenas_list])
            kmeans = KMeans(n_clusters=columns).fit(x_coord.reshape(len(x_coord), 1))

            cluster_mean_x = [0, ] * columns
            cluster_centers = list(range(columns))
            for i, col in enumerate(range(columns)):
                cluster_mean_x[i] = np.mean(x_coord[kmeans.labels_ == col])

            indices = sorted(range(len(cluster_mean_x)), key=lambda k: cluster_mean_x[k])
            labels = np.array(cluster_centers)[indices][kmeans.labels_]
            #print(labels)

            for i, arena in enumerate(arenas_list):
                arena.set_column(labels[i])


            # sort the arenas_list using the br corner attribute (.corners[1])
            # the corner is a tuple showing (x, y)
            # we want to sort first on y ([1]) and then on x ([0])
            # both in decreasing order because the
            sorted_arenas_br_to_tl_horizontally = sorted(arenas_list, key=lambda arena: (arena.column, arena.corners[1][1]))

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
                    logger.debug("Arena %d in frame #%d. Multiple flies found", arena.identity, self.frame_count)
                    fly = sorted(putative_flies, key=lambda f: f.area, reverse=True)[0]
                else:
                    fly = putative_flies[0]


                logger.debug("Fly %d in arena %d validated with area %3.f and length %3.f", fly.identity, fly.arena.identity, fly.area, fly.diagonal)

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
            for i, arena in enumerate(sorted_arenas_br_to_tl_horizontally):
                arena_crop = arena.crop(frame_color)
                self.stacked_arenas[i] = imutils.resize(arena_crop, width=arena_crop.shape[1]*3)

            # TODO: Make into utils function
            #self.control_thread.stacked_arenas = self.stack_arenas(arenas_dict)

            # Print warning if number of flies in new frame is not the same as in previous
            if self.old_found != self.found_flies:
                logger.debug("Found %d flies in frame %d", self.found_flies, self.frame_count)
            self.old_found = self.found_flies
            self.found_flies = 0

            self.frame_count += 1


            return True

        #########################
        ## End if
        ##

        else:
            #self.save_prompt()
            return None


    @property
    def frame_count(self):
        return self._frame_count

    @frame_count.setter
    def frame_count(self, value):
        self._frame_count = value
        if self._frame_count % 100 == 0:
            logger.info("Frame #%s", (str(self._frame_count).zfill(5)))

    @property
    def ready(self):
        return self._ready_event.is_set()

    @ready.setter
    def ready(self, value):
        r"""
        Set me from an owning class so the behavior of track changes.
        """
        if value is True:
            self._ready_event.set()


    @property
    def framerate(self):
        return self._framerate

    @framerate.getter
    def framerate(self):

        # if not even started yet!
        if not self.running:
            framerate = 0

        # elif live feed
        elif self.video_path is None:
            framerate = self.camera.framerate

        # if video
        elif self.running and not self.stopped:
            before = self.frame_count
            self._end_event.wait(self._delta_t)
            after = self.frame_count
            framerate = (after - before) / self._delta_t


        self._framerate = framerate
        return self._framerate


    @property
    def info(self):
        return self._info

    @info.getter
    def info(self):
        logging.debug('Requesting SimpleTracker.info')
        self._info.update({
            "more_info": "more_info"
        })
        return self._info

    def run(self):
        """
        Start tracking in a while loop
        Munge processed frames and masks
        When while is finished, run self.close()
        Signal the exit event has been set if not yet
        This is the target function of the intermediate thread
        and it runs self.track an indefinite amount of time.
        """

        super().run()

        while not self.stopped:

            try:
                if self.track() is not True:
                    break

            except (LessArenasThanTargetError, CouldNotReadFrameError):
                self.fraction_area *= 0.99

        logger.debug("SimpleTracker.run detected stopped signal")

    def stop(self):
        """
        Release thre camera
        Save the cached data
        """
        super().stop()
        self.camera.stop()
        # TODO Move this to the control thread
        # self.control_thread.saver.store_and_clear()



if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video")
    ap.add_argument("-c", "--camera_name", type=str, default="opencv", help="camera source")
    ap.add_argument("-g", "--gui", type=str, help="tkinter/opencv")
    ARGS = vars(ap.parse_args())

    # TODO Implement a main function for testing or independent running
