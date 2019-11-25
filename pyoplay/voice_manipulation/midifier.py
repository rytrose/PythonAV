import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
import time
import mido
import math
from pretty_midi import hz_to_note_number
from pyo import *

from midi.mido_client import MidoClient
from utils.utils import quantize, linear_interpolate

class Midifier:
    """Midifier receives segments created by a VoiceCapture object and converts them to MIDI for external synthesis."""
    def __init__(self, output_device=""):
        self.output_device = output_device
        self.mido_client = MidoClient(output_devices=[self.output_device])
        self.port = self.mido_client.output_ports[self.output_device]
        self.sampling_interval = 0.1
        self.metro = Metro(time=self.sampling_interval)
        self.send_trig_func = None

    def send_segment(self, segment, loop=False):
        if type(segment) == tuple:
            segment = segment[0]

        self.times = [self.t[0] for self.t in segment]
        self.freqs = [self.t[1] for self.t in segment]

        self.start = time.time()
        self.end = segment[-1][0]

        self.t = 0
        self.prev_midi_note = None

        self.send_trig_func = TrigFunc(self.metro, self.send_midi, loop)
        self.metro.play()

    def send_midi(self, loop):
        if self.t < self.end:
            self.t = time.time() - self.start
            i, t0 = quantize(self.t, self.times, with_index=True)
            y0 = self.freqs[i]

            if i < 0:
                j = i + 1
            elif i == len(self.times) - 1:
                j = i - 1
            else:
                j = i + 1 if self.t > t0 else i - 1

            f = linear_interpolate(self.t, t0, y0, self.times[j], self.freqs[j])
            
            midi_note = 0
            if f > 0: 
                midi_note = math.floor(hz_to_note_number(f))

            if midi_note != self.prev_midi_note:
                if midi_note == 0:
                    # end old note
                    if self.prev_midi_note is not None:
                        old_off = mido.Message('note_off', note=self.prev_midi_note, velocity=32)
                        self.port.send(old_off)
                else:
                    # self.start new note
                    new_on = mido.Message('note_on', note=midi_note, velocity=32)
                    self.port.send(new_on)

                    # end old note
                    if self.prev_midi_note is not None:
                        old_off = mido.Message('note_off', note=self.prev_midi_note, velocity=32)
                        self.port.send(old_off)

            self.prev_midi_note = midi_note
        else:
            # end last note
            last_off = mido.Message('note_off', note=self.prev_midi_note, velocity=32)
            self.port.send(last_off)

            if loop:
                # restart
                self.t = 0
                self.prev_midi_note = None
                self.start = time.time()
            else:
                self.stop_sending()

    def stop_sending(self):
        self.metro.stop()
