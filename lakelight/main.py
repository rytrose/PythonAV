import cv2
import math
import multiprocessing
import queue
import bisect
import numpy as np


def quantize(value, quant):
    """Quantizes a value to the closest value in a list of quantized values.
    Args:
        value (float): Value to be quantized
        quant (List[float]): Quantized value options.
    Returns:
        float: Quantized input value.
    """
    mids = [(quant[i] + quant[i + 1]) / 2.0
            for i in range(len(quant) - 1)]
    ind = bisect.bisect_right(mids, value)
    return quant[ind]


class Audio(multiprocessing.Process):
    def __init__(self):
        super(Audio, self).__init__()
        self.q = multiprocessing.Queue()
        self.ready = False
        self._terminate = False

    def stop(self):
        self.q.put(False)

    def run(self):
        # keep imports in this process
        import pyo
        import numpy as np
        from statistics import mode
        from pyo_client import PyoClient
        from sample import Sample

        self.pc = PyoClient(default_audio_device="built-in")
        self.beep = Sample("./sound.wav")
        self.env = pyo.HannTable()
        FPS = 60
        self.num_grains = pyo.SigTo(0, time=1/FPS)
        self.grain_pos = pyo.SigTo(0, time=1/FPS)
        self.grain_dur = pyo.SigTo(0.1, time=1/FPS)
        self.grain_dev = pyo.SigTo(0.01, time=1/FPS)
        self.grain_pitch = pyo.SigTo(1, time=1/FPS)
        self.granular = pyo.Particle2(self.beep.table, self.env, 
                                      dens=self.num_grains, pos=self.grain_pos,
                                      dur=self.grain_dur, dev=self.grain_dev,
                                      pitch=self.grain_pitch).out()

        # signal ready
        self.q.put(True)

        while not self._terminate:
            try:
                contour_info = self.q.get(timeout=1)
                if type(contour_info) == bool:
                    self.pc.audio_server.shutdown()
                    break
            except queue.Empty:
                continue

            # convert to numpy for reasons
            contour_info = np.array(contour_info)

            # grain density from light density
            self.num_grains.setValue(len(contour_info) // 3)

            # grain deviation from mode of quanitized x positions
            xs = contour_info[:,0].tolist()
            bins = np.linspace(0, 1080, num=51).tolist()
            quantized_xs = [quantize(x, bins) for x in xs]
            x_mode = int(mode(quantized_xs))
            dev = x_mode / 1080
            self.grain_dev.setValue(dev)

            # grain duration from average area
            avg_area = np.mean(contour_info, axis=0)[2]
            dur = float(avg_area / 400)
            self.grain_dur.setValue(dur)

            # grain pitch from average y position
            avg_y = np.mean(contour_info, axis=0)[1]
            pitch = float(avg_y / 1920) * 10 - 4.5
            self.grain_pitch.setValue(pitch)


def resize(img, scale_percent):
    width = int(img.shape[1] * scale_percent)
    height = int(img.shape[0] * scale_percent)
    return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)


if __name__ == "__main__":
    # load and start audio
    audio = Audio()
    audio.start()

    # wait for audio to be ready
    audio.q.get()

    # load video
    cap = cv2.VideoCapture("./video.mp4")

    # create mask of dock
    # points taken from 0.4 resized image
    points = [[0, 710], [242, 627], [242, 625], [250, 616], [283, 584], [301, 565], [313, 548], [370, 530], [431, 259], [431, 0], [0, 0]]

    # resize points to full image
    points_resized = [[math.floor(p[0] * 2.5), math.floor(p[1] * 2.5)] for p in points]

    # create mask
    pts = np.array(points_resized)
    mask = np.zeros((1920, 1080), dtype=np.uint8)
    cv2.fillConvexPoly(mask, pts, 1)

    AUDIO_SAMPLING = 1
    ctr = 0
    while cap.isOpened():
        #

        # read video frame
        ret, frame = cap.read()
        if not ret:
            break    

        # apply mask to remove dock
        filtered_frame = cv2.bitwise_and(frame, frame, mask=mask)

        # find bright spots
        MIN_BRIGHTNESS = 210
        frame_gray = cv2.cvtColor(filtered_frame, cv2.COLOR_BGR2GRAY)
        frame_blurred = cv2.GaussianBlur(frame_gray, (11, 11), 0)
        _, frame_threshold = cv2.threshold(frame_blurred, MIN_BRIGHTNESS, 255, cv2.THRESH_BINARY)

        # find contours of bright spots
        contours, _ = cv2.findContours(frame_threshold, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # filter bright spots by size and save off coordinates and area for music
        filtered_contours = []
        contour_info = []
        MIN_AREA = 30
        for c in contours:
            # find area of contour
            area = cv2.contourArea(c)
            if area > MIN_AREA:
                # use moments to find center
                m = cv2.moments(c)
                cX = math.floor(m["m10"] / m["m00"])
                cY = math.floor(m["m01"] / m["m00"])

                # draw contour center
                # cv2.circle(frame, (cX, cY), 2, (0, 0, 0), -1)

                # save information
                contour_info.append([cX, cY, area])
                filtered_contours.append(c) 
        
        # draw contours on frame
        contour_drawing = np.zeros((frame.shape[0], frame.shape[1], 3), np.uint8)
        cv2.drawContours(contour_drawing, filtered_contours, -1, (255, 255, 255), 1)

        if True: # if ctr % AUDIO_SAMPLING == 0:
            # send contour info to audio
            audio.q.put_nowait(contour_info)
        ctr += 1

        cv2.imshow('out', resize(frame, 0.4))  # show original video
        cv2.imshow('contours', resize(contour_drawing, 0.4))  # show contours
        cv2.imshow('threshold', resize(frame_threshold, 0.4)) # show frame white spots

        if cv2.waitKey(16) & 0xFF == ord('q'):
            break

    audio.stop()
    cap.release()
    cv2.destroyAllWindows()
