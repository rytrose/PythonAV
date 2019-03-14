from pyo import *
from multiprocessing import Pipe
import threading

from pyo_client import PyoClient
from metronome import Metronome
from serial_client import SerialClient
from recorder import Recorder


class Looper:
    """Implements live loop recording and playback."""

    def __init__(self):
        self.tempo = 100
        self.tempo_seconds = 1 / (self.tempo / 60)
        self.num_beats = 4
        self.beat_counter = self.num_beats

        self.start_recording = False
        self.recording = False
        self.saved_recordings = []
        self.playing_recording = None

        (self.main_pipe, self.metro_pipe) = Pipe()
        self.metronome_output_device = 1
        self.metronome = Metronome(self.metro_pipe, self.metronome_output_device, self.tempo).start()
        threading.Thread(target=self.on_metro).start()

        self.pyo = PyoClient()
        self.input = Input(0)
        self.recording_object = Recorder(self.input, self.tempo_seconds * self.num_beats)

        self.serial_client = SerialClient()
        self.serial_client.add_command("start_loop", "i", self.start_loop)
        self.serial_client.add_command("recording", "i")
        self.serial_client.start()

    def change_metro_tempo(self, new_tempo):
        self.tempo = new_tempo
        self.tempo_seconds = 1 / (new_tempo / 60)
        self.main_pipe.send(new_tempo)

    def on_metro(self):
        while True:
            self.main_pipe.recv()  # Do something on metronome
            self.beat_counter = (self.beat_counter - 1) % self.num_beats

            if self.beat_counter == 0:
                if self.recording:  # stop recording
                    self.recording = False
                    self.saved_recordings.append(self.recording_object.get_table())
                    self.playing_recording = TableRead(self.saved_recordings[-1], freq=1 / self.saved_recordings[-1].length).out()
                    self.serial_client.send("recording", 0)
                if self.start_recording:  # start recording
                    self.start_recording = False
                    self.recording = True
                    self.recording_object.record()
                    self.serial_client.send("recording", 1)

    def start_loop(self, _, __):
        self.start_recording = True


if __name__ == '__main__':
    l = Looper()
