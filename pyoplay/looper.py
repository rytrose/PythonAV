from pyo import *
from multiprocessing import Pipe

from websocket import WS
from pyo_client import PyoClient
from metronome import Metronome
import asyncio
import threading
import copy


class Looper:
    def __init__(self):
        self.ws = WS(is_client=True, uri="ws://rytrose_thing.local:81")

        self.tempo = 100
        self.tempo_seconds = 1 / (self.tempo / 60)
        self.num_beats = 4

        self.recording = False
        self.current_recording = None
        self.stopper = None
        self.saved_recordings = []
        self.playing_recordings = []
        self.playing = None

        (self.main_pipe, self.metro_pipe) = Pipe()
        self.metronome_output_device = 1
        self.metronome = Metronome(self.metro_pipe, self.metronome_output_device, self.tempo).start()
        threading.Thread(target=self.on_metro).start()

        self.pyo = PyoClient()

        self.record_table = NewTable(self.tempo_seconds * self.num_beats)
        self.mic_input = Input(0)

        self.ws.map("numBeats", self.num_beats_handler)
        self.ws.map("pressed", self.pressed_handler)
        self.ws.map("released", self.released_handler)
        self.ws.start()

    def change_metro_tempo(self, new_tempo):
        self.tempo = new_tempo
        self.tempo_seconds = 1 / (new_tempo / 60)
        self.main_pipe.send(new_tempo)

    def on_metro(self):
        while True:
            self.main_pipe.recv()
            for recording in self.saved_recordings:
                if not recording["playing"]:
                    recording["player"].reset()
                    recording["player"].out()
                    recording["playing"] = True

    async def num_beats_handler(self, _, args):
        self.num_beats = args[0]

        while self.recording:
            asyncio.sleep(0.1)

        self.record_table = NewTable(self.tempo_seconds * self.num_beats)

    async def pressed_handler(self, _, __):
        self.recording = True
        print("Starting to record...")
        self.current_recording = TableRec(self.mic_input, self.record_table).play()
        self.stopper = TrigFunc(self.current_recording['trig'], self.stop_recording)

    async def released_handler(self, _, __):
        if self.recording:
            self.stop_recording()

    def stop_recording(self):
        print("Stopping recording...")
        self.current_recording.stop()
        recorded_table = self.record_table.copy()
        self.saved_recordings.append({
            "player": TableRead(recorded_table, freq=1/recorded_table.length, loop=1),
            "playing": False
        })
        self.record_table = NewTable(self.tempo_seconds * self.num_beats)
        self.recording = False


if __name__ == '__main__':
    l = Looper()
