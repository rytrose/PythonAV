import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
import time
import math
from pyo import *
import matplotlib.pyplot as plt
import threading
import atexit
# from scipy.interpolate import UnivariateSpline

from pyo_extensions.audio_recorder import AudioRecorder
from pyo_extensions.pyo_client import PyoClient
from pyo_extensions.sample import Sample
from communication.osc_client import OSCClient

ON_PI = True

if ON_PI:
    from pi_gpio.pi_gpio import PiGPIO, PiGPIOConfig
from utils.stoppable_thread import StoppableThread
from utils.utils import quantize

class GPIOThread(StoppableThread):
    def __init__(self, pi_gpio, playback):
        self.pi_gpio = pi_gpio
        self.playback = playback

        StoppableThread.__init__(self, target=self.listen)

    def listen(self):
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
        self.follower = Follower(self.input)
        self.length = length
        self.pitch_detect_pattern = Pattern(self.get_pitch, time=0.02)
        self.recorder = AudioRecorder(
            self.input, self.server_sr, self.length, 
            on_stop=self.stop_receiving_attacks, pattern=self.pitch_detect_pattern)

        self.attack_detector = AttackDetector(self.input)
        self.receive_attacks = False
        self.attack_func = TrigFunc(self.attack_detector, self.receive_attack)

        self.ctr_trig = Trig()
        self.ctr = Count(self.ctr_trig)

        self.pitch_tolerance = 30
        self.sound_object_tolerance = 50
        self.length_req = 2
        self.amp_avg_buffer = 0.5
        self.amplitudes = []
        self.pitches = []
        self.pitch_timestamps = []
        self.attacks = []
        self.attack_timestamps = []
        self.sound_objects = []
        self.pitch_contour = None
        self.playback = None
        self.playing = False

        if ON_PI:
            self.pi_gpio = PiGPIO()
            self.pi_gpio.add_gpio(PiGPIOConfig("pot_0", "analog", channel=0))
            self.pi_gpio.add_gpio(PiGPIOConfig("pot_1", "analog", channel=1))
            self.pi_gpio.add_gpio(PiGPIOConfig("led_0", "led", pin=3))
            self.pi_gpio.add_gpio(PiGPIOConfig("button_0", "button", pin=2,
                on_pressed=self.button_0_pressed, 
                on_released=self.button_0_released))
            self.pi_gpio.start()

    def button_0_pressed(self):
        self.pi_gpio.set_value("led_0", 1)
        self.record(length=10)

    def button_0_released(self):
        self.pi_gpio.set_value("led_0", 0)
        self.recorder.stop()

    def receive_attack(self):
        if self.receive_attacks:
            self.attacks.append(self.pitch_detect.get())
            self.attack_timestamps.append(self.ctr.get() / self.server_sr)

    def stop_receiving_attacks(self):
        self.receive_attacks = False
        self.processed_pitches = [0]
        amp_avg = sum(self.amplitudes) / len(self.amplitudes)

        i = 0
        pitches_dropped = 0
        current_length = 1
        current_start = 1
        t = 0
        for pitch, timestamp in zip(self.pitches, self.pitch_timestamps):
            if 0 < i < len(self.pitches):
                if pitch > self.minfreq + 40 and self.amplitudes[i] > self.amp_avg_buffer * amp_avg:  # If not silent
                    diff = abs(self.pitches[i - 1] - pitch)  
                    if diff > self.pitch_tolerance:  # If a big jump
                        self.processed_pitches.append(0)
                        pitches_dropped += 1
                    else:
                        self.processed_pitches.append(pitch)
                else:
                    self.processed_pitches.append(0)
                    pitches_dropped += 1
            i += 1

        self.processed_pitches = [2 * p for p in self.processed_pitches]
        print("Dropped %d estimates." % pitches_dropped)

        self.attack_translation()
        self.pitch_timestamps[0] = 0
        # self.pitch_contour = Linseg(list(zip(self.pitch_timestamps, self.processed_pitches)), loop=True)
        # self.sine = Sine(freq=self.pitch_contour, mul=0.5).out()
        self.playback = Sample(table=self.recorder.record_table, 
            processing=[(Harmonizer, {"transpo": 0}), (Harmonizer, {"transpo": 0})], loop=1)
        self.play()

    def get_pitch(self):
        self.pitch_timestamps.append(self.ctr.get() / self.server_sr)
        self.pitches.append(self.pitch_detect.get())
        self.amplitudes.append(self.follower.get())

    def play(self):
        self.playing = True
        # self.pitch_contour.play()
        self.playback.play()

        if ON_PI:
            self.gpio_listen_thread = GPIOThread(self.pi_gpio, self.playback)
            self.gpio_listen_thread.start()

    def stop(self):
        self.playing = False
        # self.pitch_contour.stop()
        self.playback.stop()

        if ON_PI:
            self.gpio_listen_thread.stop(wait=False)

    def record(self, length=None):
        if self.playing:
            self.stop()
        self.speed = 1 / self.recorder.length
        self.transposition = 1
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

    def attack_translation(self):
        self.sound_objects = []
        for attack in self.attack_timestamps:
            closest_timestamp = quantize(attack, self.pitch_timestamps)
            closest_timestamp_index = self.pitch_timestamps.index(closest_timestamp)

            for _ in range(5):
                if closest_timestamp_index < len(self.processed_pitches) \
                    and self.processed_pitches[closest_timestamp_index] == 0:
                    closest_timestamp_index += 1
                else:
                    break

            i = closest_timestamp_index
            sound_object = []

            while i < len(self.pitch_timestamps) - 1:
                diff = abs(self.processed_pitches[i + 1] - self.processed_pitches[i])  
                if diff > self.sound_object_tolerance or self.processed_pitches[i + 1] == 0:  # If a big jump
                    break
                else:
                    sound_object.append((self.pitch_timestamps[i], self.processed_pitches[i]))
                i += 1

            if sound_object and len(sound_object) > 2:
                self.sound_objects.append(sound_object)

        self.segment = [(0, 0)]
        for so in self.sound_objects:
            self.segment += ([(so[0][0], 0)] + so + [(so[-1][0], 0)])
        self.segment += [(self.recorder.record_table.getSize() / self.server_sr, 0)]
        self.ls = Linseg(self.segment, loop=True)
        self.saw = SuperSaw(freq=self.ls).out()
        self.ls.play()


    def plot(self):
        # spl_obj = UnivariateSpline(self.pitch_timestamps, self.processed_pitches)
        # spl = spl_obj(self.pitch_timestamps)
        # plt.scatter(self.pitch_timestamps, self.pitches, s=1, color="blue")
        plt.scatter(self.pitch_timestamps,
                    self.processed_pitches, s=1, color="blue")
        plt.scatter(self.attack_timestamps, self.attacks,
                    s=12, marker='^', color="green")
        for so in self.sound_objects:
            plt.scatter([s[0] for s in so], [s[1] for s in so], 
            s=8, marker='X', color="orange")
        # plt.plot(self.pitch_timestamps, spl, color="orange")
        # plt.show()
        plt.savefig('plt.pdf')


if __name__ == "__main__":
    if ON_PI:
        c = PyoClient(audio_backend="jack", default_audio_device="usb")
    else:
        c = PyoClient(default_audio_device="usb")
    v = VoiceManipulation(c.audio_server.getSamplingRate(), 4.0)
    
    def shutdown():
        c.audio_server.stop()

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
