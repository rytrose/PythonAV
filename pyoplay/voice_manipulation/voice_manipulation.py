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
from communication.osc_client import OSCClient
from pi_gpio.pi_gpio import PiGPIO, PiGPIOConfig
from utils.stoppable_thread import StoppableThread

class GPIOThread(StoppableThread):
    def __init__(self, pi_gpio, playback):
        self.pi_gpio = pi_gpio
        self.playback = playback

        StoppableThread.__init__(self,
                                 setup=self.setup,
                                 target=self.run,
                                 teardown=self.teardown)

    def run(self):
        while not self.should_stop():
            pot_0_val = abs(1 - self.pi_gpio.get_value("pot_0"))
            pot_1_val = abs(1 - self.pi_gpio.get_value("pot_1"))

            transpo_0 = math.floor((pot_0_val * 24) - 12)
            transpo_1 = math.floor((pot_1_val * 24) - 12)

            if abs(self.playback.signal_chain[0].transpo - transpo_0) > 0.1:
                print("Setting voice 0 to %f" % transpo_0)
                self.playback.signal_chain[0].setTranspo(transpo_0)

            if abs(self.playback.signal_chain[1].transpo - transpo_1) > 0.1:
                print("Setting voice 1 to %f" % transpo_1)
                self.playback.signal_chain[1].setTranspo(transpo_1)


class VoiceManipulation:
    def __init__(self, server_sr, length):
        self.server_sr = server_sr
        self.input = Input()
        self.minfreq = 50
        self.pitch_detect = Yin(self.input, minfreq=self.minfreq, maxfreq=600)
        self.length = length
        self.pitch_detect_pattern = Pattern(self.get_pitch, time=0.05)
        self.recorder = AudioRecorder(
            self.input, self.length, on_stop=self.stop_receiving_attacks, pattern=self.pitch_detect_pattern)

        # self.attack_detector = AttackDetector(self.input)
        self.receive_attacks = False
        # self.attack_func = TrigFunc(self.attack_detector, self.receive_attack)

        self.ctr_trig = Trig()
        self.ctr = Count(self.ctr_trig)

        self.pitches = []
        self.pitch_timestamps = []
        self.attacks = []
        self.attack_timestamps = []
        self.pitch_contour = None
        self.playback = None

        self.pi_gpio = PiGPIO()
        self.pi_gpio.add_gpio(PiGPIOConfig("pot_0", "analog", channel=0))
        self.pi_gpio.add_gpio(PiGPIOConfig("pot_1", "analog", channel=1))
        self.pi_gpio.start()


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

        print("Dropped %d estimates." % pitches_dropped)

        self.pitch_timestamps[0] = 0
        self.pitch_contour = Linseg(
            list(zip(self.pitch_timestamps, [2 * p for p in self.pitches])), loop=True)
        self.sine = Sine(freq=self.pitch_contour).out()
        self.playback = Sample(table=self.recorder.record_table, 
            processing=[(Harmonizer, {"transpo": 0}), (Harmonizer, {"transpo": 0})], loop=1)
        self.play()

    def get_pitch(self):
        self.pitch_timestamps.append(self.ctr.get() / self.server_sr)
        self.pitches.append(self.pitch_detect.get())

    def play(self):
        # self.pitch_contour.play()
        self.playback.play()
        self.gpio_listen_thread = GPIOThread(self.pi_gpio, self.playback)
        self.gpio_listen_thread.start()

    def stop(self):
        # self.pitch_contour.stop()
        self.playback.stop()
        self.gpio_listen_thread.stop()

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
            factor = self.speed * self.recorder.length
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
    c = PyoClient(audio_backend="jack", default_audio_device="built-in")
    v = VoiceManipulation(c.audio_server.getSamplingRate(), 4.0)

    # def on_record(addess, args):
    #     print("Recording...")
    #     v.record()

    # def on_set_speed(address, speed):
    #     v.change_pitch_contour(speed=speed)

    # def on_set_transposition(address, transposition):
    #     v.change_pitch_contour(transposition=transposition)

    # def on_play(addess, args):
    #     v.play()

    # def on_stop(address, args):
    #     v.stop()

    # osc_client = OSCClient()
    # osc_client.map("/record", on_record)
    # osc_client.map("/set_speed", on_set_speed)
    # osc_client.map("/set_transposition", on_set_transposition)
    # osc_client.map("/play", on_play)
    # osc_client.map("/stop", on_stop)
    # osc_client.begin()
