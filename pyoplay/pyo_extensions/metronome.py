from pyo import *
from multiprocessing import Process

import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from pyo_extensions.pyo_client import PyoClient


class Metronome(Process):
    def __init__(self, connection, output_device_id, initial_tempo, sound_path="sounds/wood_block.wav"):
        super(Metronome, self).__init__()
        self._connection = connection
        self.output_device_id = output_device_id
        self.daemon = True
        self._terminated = False
        self.tempo = 1 / (initial_tempo / 60)
        self.sound_path = sound_path

    def run(self):
        self.pyo_client = PyoClient(
            audio_duplex=False, audio_output_device_id=self.output_device_id)
        self.player = SfPlayer(self.sound_path)
        self.metro = Pattern(self.tick, time=self.tempo)
        self.metro.play()

        while not self._terminated:
            self.tempo = self._connection.recv()
            self.metro.setTime(1 / (self.tempo / 60))

        self.pyo_client.audio_server.stop()

    def tick(self):
        self._connection.send(True)
        self.player.play()
        self.player.out()

    def stop(self):
        self._terminated = True
