import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
import time
import math
from pyo import *
import matplotlib.pyplot as plt

from pyo_extensions.audio_recorder import AudioRecorder
from pyo_extensions.pyo_client import PyoClient
from pyo_extensions.sample import Sample


class VoiceManipulation:
    def __init__(self, server_sr, length):
        self.server_sr = server_sr
        self.input = Input()
        self.minfreq = 80
        self.pitch_detect = Yin(self.input, minfreq=self.minfreq, maxfreq=600)
        self.length = length
        self.pattern = Pattern(self.get_pitch, time=0.01)
        self.recorder = AudioRecorder(
            self.input, self.length, on_stop=self.stop_receiving_attacks, pattern=self.pattern)

        # self.sample = Sample(path="voice.wav")
        # self.pitch_detect = Yin(self.sample.table_reader,
        #                         minfreq=80, maxfreq=600)

        # self.granule_length = int(0.05 * self.server_sr)
        # self.granule_table = None
        # self.attack_detector = AttackDetector(self.input)
        # self.receive_attacks = False
        # self.attack_func = TrigFunc(self.attack_detector, self.receive_attack)

        self.ctr_trig = Trig()
        self.ctr = Count(self.ctr_trig)

        self.pitches = []
        self.pitch_timestamps = []
        self.attacks = []
        self.pitch_contour = None

    def receive_attack(self):
        if self.receive_attacks:
            self.attacks.append(self.ctr.get() / self.server_sr)

    def stop_receiving_attacks(self):
        self.receive_attacks = False

        self.processed_pitches = [0]
        self.tolerance = 1.1
        self.pitch_tolerance = 20
        self.length_req = 10

        i = 0
        pitches_dropped = 0
        current_length = 1
        current_start = 1
        t = 0
        for pitch, timestamp in zip(self.pitches, self.pitch_timestamps):
            if 0 < i < len(self.pitches):
                if pitch > self.minfreq:
                    diff = abs(self.pitches[i - 1] - pitch)
                    if diff > self.pitch_tolerance:
                        if current_length > self.length_req:
                            if current_start == i:
                                t += 1
                            for j in range(current_start, i):
                                self.processed_pitches.append(self.pitches[j])
                            current_length = 1
                            current_start = i
                        else:
                            if current_start == i:
                                t += 1
                            for j in range(current_start, i):
                                self.processed_pitches.append(0)
                                pitches_dropped += 1
                            current_length = 1
                            current_start = i
                    else:
                        current_length += 1
                else:
                    for j in range(current_start, i):
                        self.processed_pitches.append(0)
                        pitches_dropped += 1
                    current_length = 1
                    current_start = i
            i += 1

        for i in range(current_start, len(self.pitches)):
            self.processed_pitches.append(0)

        # print("Dropped %d estimates." % pitches_dropped)

        self.pitch_contour = Linseg(
            list(zip(self.pitch_timestamps, [2 * p for p in self.processed_pitches])), loop=True)
        self.sine = Sine(freq=self.pitch_contour).mix(2).out()

    def get_pitch(self):
        self.pitch_timestamps.append(self.ctr.get() / self.server_sr)
        self.pitches.append(self.pitch_detect.get())

    def play(self):
        self.pitch_contour.play()

    def stop(self):
        self.pitch_contour.stop()

    def record(self):
        self.pitches = []
        self.attacks = []
        self.receive_attacks = True
        self.ctr_trig.play()
        self.recorder.record()

        # self.pattern.play()
        # self.sample.play()
        # time.sleep(4)
        # self.pattern.stop()
        # self.stop_receiving_attacks()
        # # self.plot()

    def plot(self):
        plt.scatter(self.pitch_timestamps, self.pitches, s=1, color="blue")
        plt.scatter(self.pitch_timestamps,
                    self.processed_pitches, s=1, color="red")
        plt.show()


if __name__ == "__main__":
    c = PyoClient()
    v = VoiceManipulation(c.audio_server.getSamplingRate(), 4.0)
    v.record()
