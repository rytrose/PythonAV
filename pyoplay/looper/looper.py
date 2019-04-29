from pyo import *
from multiprocessing import Pipe
import threading

import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from pyo_extensions.pyo_client import PyoClient
from pyo_extensions.metronome import Metronome
from pyo_extensions.audio_recorder import AudioRecorder
from communication.serial_client import SerialClient


class Looper:
    """Implements live loop recording and playback."""

    def __init__(self):
        self.tempo = 100
        self.tempo_seconds = 1 / (self.tempo / 60)
        self.num_beats = 8
        self.beat_counter = self.num_beats

        self.start_recording = False
        self.recording = False
        self.saved_recordings = []
        self.playing_recording = None

        self.serial_client = None

        (self.main_pipe, self.metro_pipe) = Pipe()
        self.metronome_output_device = 1
        self.metronome = Metronome(
            self.metro_pipe, self.metronome_output_device, self.tempo).start()
        threading.Thread(target=self.on_metro).start()

        self.pyo = PyoClient(prompt_for_audio_devices=True)
        self.input = Input(0)
        self.audio_recording_object = AudioRecorder(
            self.input, self.tempo_seconds * self.num_beats)

        # self.serial_client = SerialClient(arduino_params={"int_bytes": 4})  # Teensy int is 32-bit
        # self.serial_client.add_command("start_recording", "i", self.start_loop)
        # self.serial_client.add_command("recording", "i")
        # self.serial_client.add_command("loop_start", "i")
        # self.serial_client.start()

        self.i = 0

    def test(self):
        self.audio_recording_object.record()

    def save(self):
        self.audio_recording_object.get_table().save("test%d.wav" % self.i)
        self.i += 1

    def change_metro_tempo(self, new_tempo):
        self.tempo = new_tempo
        self.tempo_seconds = 1 / (new_tempo / 60)
        self.main_pipe.send(new_tempo)

    def on_metro(self):
        while True:
            self.main_pipe.recv()  # do something on metronome
            self.beat_counter = (self.beat_counter - 1) % self.num_beats

            if self.serial_client:  # wait until serial connection exists
                if self.beat_counter == 0:
                    self.serial_client.send("loop_start", 1)

                    if self.recording:  # stop recording
                        self.recording = False
                        self.saved_recordings.append(
                            self.audio_recording_object.get_table())
                        if self.playing_recording:
                            self.playing_recording.stop()
                        self.playing_recording = TableRead(self.saved_recordings[-1],
                                                           freq=1 / self.saved_recordings[-1].length).out()
                        self.serial_client.send("recording", 0)
                    if self.start_recording:  # start recording
                        self.start_recording = False
                        self.recording = True
                        self.audio_recording_object.record()
                        self.serial_client.send("recording", 1)

    def start_loop(self, _, __):
        self.start_recording = True


if __name__ == '__main__':
    l = Looper()
