import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from midi.mido_client import MidoClient

class Midifier:
    """Midifier receives segments created by a VoiceCapture object and converts them to MIDI for external synthesis."""
    def __init__(self, output_device=""):
        self.output_device = output_device
        self.mido_client = MidoClient(output_devices=[self.output_device])
        self.port = self.mido_client.output_ports[self.output_device]