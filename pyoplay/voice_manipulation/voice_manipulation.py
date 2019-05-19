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
from pyo_extensions.pvsample import PVSample
from communication.osc_client import OSCClient


class VoiceManipulation:
    def __init__(self, server_sr, length):
        self.server_sr = server_sr
        self.input = Input()
        self.minfreq = 50
        self.pitch_detect = Yin(self.input, minfreq=self.minfreq, maxfreq=600)
        self.length = length
        self.pattern = Pattern(self.get_pitch, time=0.01)
        self.recorder = AudioRecorder(
            self.input, self.length, on_stop=self.stop_receiving_attacks, pattern=self.pattern)

        self.attack_detector = AttackDetector(self.input)
        self.receive_attacks = False
        self.attack_func = TrigFunc(self.attack_detector, self.receive_attack)

        self.ctr_trig = Trig()
        self.ctr = Count(self.ctr_trig)

        self.pitches = []
        self.pitch_timestamps = []
        self.attacks = []
        self.attack_timestamps = []
        self.pitch_contour = None
        self.playback = None

    def receive_attack(self):
        if self.receive_attacks:
            self.attacks.append(self.pitch_detect.get())
            self.attack_timestamps.append(self.ctr.get() / self.server_sr)

    def stop_receiving_attacks(self):
        self.receive_attacks = False

        self.processed_pitches = [0]
        self.tolerance = 1.1
        self.pitch_tolerance = 50
        self.length_req = 8

        i = 0
        pitches_dropped = 0
        current_length = 1
        current_start = 1
        t = 0
        for pitch, timestamp in zip(self.pitches, self.pitch_timestamps):
            if 0 < i < len(self.pitches):
                if pitch > self.minfreq + 40:
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

        self.pitch_timestamps[0] = 0
        self.pitch_contour = Linseg(
            list(zip(self.pitch_timestamps, [2 * p for p in self.processed_pitches])), loop=True)
        self.sine = Sine(freq=self.pitch_contour).mix(2).out()
        self.playback = PVSample(table=self.recorder.record_table)

    def get_pitch(self):
        self.pitch_timestamps.append(self.ctr.get() / self.server_sr)
        self.pitches.append(self.pitch_detect.get())

    def play(self):
        self.pitch_contour.play()
        self.playback.set_phase(0)
        self.playback.play()

    def stop(self):
        self.pitch_contour.stop()
        self.playback.stop()

    def record(self):
        self.speed = 1 / self.recorder.length
        self.transposition = 1
        self.pitches = []
        self.pitch_timestamps = []
        self.attacks = []
        self.attack_timestamps = []
        self.receive_attacks = True
        self.ctr_trig.play()
        self.recorder.record()

    def change_pitch_contour(self, speed=None, transposition=None):
        if self.playback:
            if speed:
                self.speed = speed
            if transposition:
                self.transposition = transposition
            factor = self.speed / self.recorder.length
            new_timestamps = [t * (1 / factor) for t in self.pitch_timestamps]
            new_pitches = [p * self.transposition
                           for p in self.processed_pitches]
            self.pitch_contour.setList(
                list(zip(new_timestamps, [2 * p for p in new_pitches])))
            self.playback.set_speed(self.speed)
            self.playback.set_transposition(self.transposition)

    def plot(self):
        plt.scatter(self.pitch_timestamps, self.pitches, s=1, color="blue")
        plt.scatter(self.pitch_timestamps,
                    self.processed_pitches, s=1, color="red")
        plt.scatter(self.attack_timestamps, self.attacks,
                    s=12, marker='^', color="green")
        plt.show()


if __name__ == "__main__":
    c = PyoClient(default_audio_device="built-in")
    v = VoiceManipulation(c.audio_server.getSamplingRate(), 4.0)

    def on_record(addess, args):
        print("Recording...")
        v.record()

    def on_set_speed(address, speed):
        v.change_pitch_contour(speed=speed)

    def on_set_transposition(address, transposition):
        v.change_pitch_contour(transposition=transposition)

    def on_play(addess, args):
        v.play()

    def on_stop(address, args):
        v.stop()

    osc_client = OSCClient()
    osc_client.map("/record", on_record)
    osc_client.map("/set_speed", on_set_speed)
    osc_client.map("/set_transposition", on_set_transposition)
    osc_client.map("/play", on_play)
    osc_client.map("/stop", on_stop)
    osc_client.begin()
