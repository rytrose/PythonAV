import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
import time
import math
from pyo import *
import matplotlib.pyplot as plt
import threading
import atexit
import pickle
# from scipy.interpolate import UnivariateSpline

from pyo_extensions.audio_recorder import AudioRecorder
from pyo_extensions.pyo_client import PyoClient
from pyo_extensions.sample import Sample
from utils.utils import quantize


class VoiceCapture:
    """VoiceCapture captures input, expecting voice, and creates sound objects that follow the pitch contour of the speech."""

    def __init__(self, server_sr, length):
        self.server_sr = server_sr
        self.input = Input()
        self.minfreq = 50  # Used to high pass Yin detection
        self.pitch_detect = Yin(self.input, minfreq=self.minfreq, maxfreq=600)
        self.follower = Follower(self.input)
        self.length = length
        self.pitch_detect_pattern = Pattern(self.get_pitch_amplitude, time=0.02)
        self.recorder = AudioRecorder(
            self.input, self.server_sr, self.length,
            on_stop=self.stop_receiving_attacks, pattern=self.pitch_detect_pattern)

        self.attack_detector = AttackDetector(self.input)
        self.receive_attacks = False
        self.attack_func = TrigFunc(self.attack_detector, self.receive_attack)

        self.ctr_trig = Trig()
        self.ctr = Count(self.ctr_trig)

        self.pitch_tolerance = 30  # Freq used to determine what constitues a jump in in pitch detection
        self.sound_object_tolerance = 50  # Freq used to determine what constitute a jump in attack translation
        self.sound_object_lookahead = 10  # Number of samples to lookahead for start of sound object from detected attack
        self.length_req = 2  # Length of Yin detection samples for minimum sound object length
        self.amp_avg_buffer = 0.5  # Floor of avergage amplitude used to determine silence
        self.amplitudes = []
        self.pitches = []
        self.pitch_timestamps = []
        self.attacks = []
        self.attack_timestamps = []
        self.sound_objects = []
        self.pitch_contour = None
        self.playback = None
        self.playing = False

    def receive_attack(self):
        if self.receive_attacks:
            self.attacks.append(self.pitch_detect.get())
            self.attack_timestamps.append(self.ctr.get() / self.server_sr)

    def stop_receiving_attacks(self):
        self.receive_attacks = False

        # Filter Yin pitch detection
        self.pitch_processing()

        # Apply detected attacks to detected pitched
        self.attack_translation()

        # Mask recording with detected sound objects
        self.process_for_playback()

        # Play back masked sample and basic synthesized sound objects
        self.play()

    def pitch_processing(self):
        """Cleans up the raw Yin pitch detection."""
        self.processed_pitches = [0]
        amp_avg = sum(self.amplitudes) / len(self.amplitudes)

        i = 0
        pitches_dropped = 0
        silence_dropped = 0
        current_length = 1
        current_start = 1
        t = 0
        for pitch, timestamp in zip(self.pitches, self.pitch_timestamps):
            if 0 < i < len(self.pitches):
                # Drop if not silent or super low
                if pitch > self.minfreq + 40 and self.amplitudes[i] > self.amp_avg_buffer * amp_avg:
                    diff = abs(self.pitches[i - 1] - pitch)
                    if diff > self.pitch_tolerance:  # Drop if a big jump
                        self.processed_pitches.append(0)
                        pitches_dropped += 1
                    else:
                        self.processed_pitches.append(pitch)
                else:
                    self.processed_pitches.append(0)
                    silence_dropped += 1
            i += 1

        self.processed_pitches = [2 * p for p in self.processed_pitches]
        
        # Debug logging
        # print("Dropped %d estimates out of %d." % (pitches_dropped + silence_dropped, len(self.pitches)))
        # print("\t%d pitch" % pitches_dropped)
        # print("\t%d amplitude" % silence_dropped)

    def attack_translation(self):
        """Creates sound objects based on pitch detection and attack detection."""
        self.sound_objects = []
        for attack in self.attack_timestamps:
            closest_timestamp = quantize(attack, self.pitch_timestamps)
            closest_timestamp_index = self.pitch_timestamps.index(
                closest_timestamp)

            # Look ahead to see where pitches start in relation to detected attack
            for _ in range(self.sound_object_lookahead):
                if closest_timestamp_index < len(self.processed_pitches) \
                        and self.processed_pitches[closest_timestamp_index] == 0:
                    closest_timestamp_index += 1
                else:
                    break

            i = closest_timestamp_index
            sound_object = []

            while i < len(self.pitch_timestamps) - 1:
                diff = abs(self.processed_pitches[i + 1] - self.processed_pitches[i])
                # End sound object if a big jump
                if diff > self.sound_object_tolerance or self.processed_pitches[i + 1] == 0:
                    break
                else:
                    sound_object.append((self.pitch_timestamps[i], self.processed_pitches[i]))
                i += 1

            # Reject sound objects shorter than determined length
            if sound_object and len(sound_object) > self.length_req:
                self.sound_objects.append(sound_object)

        self.segment = [(0, 0)]
        for so in self.sound_objects:
            self.segment += ([(so[0][0], 0)] + so + [(so[-1][0], 0)])
        self.segment += [(self.recorder.record_table.getSize() /
                          self.server_sr, 0)]

    def process_for_playback(self):
        """Applies the sound objects as a mask to the recording and plays recording and synthesized sound objects."""
        self.pitch_timestamps[0] = 0
        self.playback = Sample(table=self.recorder.record_table,
                               processing=[(Harmonizer, {"transpo": 0})], parallel_processing=False, play_original=False, loop=1)

        for i in range(len(self.segment)):  # apply all silence in the segement to the recording
            if i > 0:
                if self.segment[i - 1][1] == 0:  # if the previous segment freq is 0
                    start_sample = math.floor(self.segment[i - 1][0] * self.playback.sr)
                    end_sample = math.floor(self.segment[i][0] * self.playback.sr)
                    for sample in range(start_sample, end_sample):
                        self.playback.table.put(0.0, pos=sample)

        self.ls = Linseg(self.segment, loop=True)
        self.saw = SuperSaw(freq=self.ls).mix(2).out()
        
    def get_pitch_amplitude(self):
        """Saves a current pitch detection and amplitude value."""
        self.pitch_timestamps.append(self.ctr.get() / self.server_sr)
        self.pitches.append(self.pitch_detect.get())
        self.amplitudes.append(self.follower.get())

    def play(self):
        """Plays back the recorded sample and basic synthesized sound object."""
        self.playing = True
        self.ls.play()
        self.playback.play()

    def stop(self):
        """Stops playback of the recorded sample and basic synthesized sound object."""
        self.playing = False
        self.pitch_contour.stop()
        self.playback.stop()

    def record(self, length=None):
        """Start recording and detecting pitch and attacks."""
        if self.playing:
            self.stop()
        self.pitches = []
        self.pitch_timestamps = []
        self.attacks = []
        self.attack_timestamps = []
        self.receive_attacks = True
        self.ctr_trig.play()
        if length:
            self.recorder.record(length=length)
        else:
            self.recorder.record()

    def plot(self):
        """Plot processed pitches and sound objects."""
        plt.scatter(self.pitch_timestamps,
                    self.processed_pitches, s=1, color="blue")
        plt.scatter(self.attack_timestamps, self.attacks,
                    s=12, marker='^', color="green")
        for so in self.sound_objects:
            plt.scatter([s[0] for s in so], [s[1] for s in so],
                        s=8, marker='X', color="orange")
        plt.savefig('plt.pdf')


if __name__ == "__main__":
    c = PyoClient(default_audio_device="built-in")
    v = VoiceCapture(c.audio_server.getSamplingRate(), 4.0)

    def shutdown():
        c.audio_server.stop()
