import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import pickle
from pyo import *
from communication.osc_client import OSCClient
from pyo_extensions.pyo_client import PyoClient


class VoiceManipulationServer:
    def __init__(self):        
        self.osc_client = OSCClient(local_address="Ryans-MacBook-Pro.local", local_port=5001, 
                            remote_address="rytrose-pi-zero-w.local", remote_port=5000)
        self.osc_client.map("/segment", self.on_segment)
        self.osc_client.begin()

    def on_segment(self, address, segment_bytes):
        self.segment = pickle.loads(segment_bytes)
        print("Server got segment:", self.segment)
        self.osc_client.send("/segment", segment_bytes)

        self.ls = Linseg(self.segment, loop=True)
        self.saw = SuperSaw(freq=self.ls).mix(2).out()
        self.ls.play()

if __name__ == "__main__":
    c = PyoClient(default_audio_device="built-in")
    v = VoiceManipulationServer()