import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
import time
import mido
import math
from pretty_midi import hz_to_note_number

from midi.mido_client import MidoClient
from utils.utils import quantize, linear_interpolate

class Midifier:
    """Midifier receives segments created by a VoiceCapture object and converts them to MIDI for external synthesis."""
    def __init__(self, output_device=""):
        self.output_device = output_device
        self.mido_client = MidoClient(output_devices=[self.output_device])
        self.port = self.mido_client.output_ports[self.output_device]
        self.sampling_interval = 0.1

    def send_segment(self, segment):
        times = [t[0] for t in segment]
        freqs = [t[1] for t in segment]

        start = time.time()
        end = segment[-1][0]

        t = 0
        prev_midi_note = None
        while t < end:
            t = time.time() - start
            i, t0 = quantize(t, times, with_index=True)
            y0 = freqs[i]

            if i < 0:
                j = i + 1
            elif i == len(times) - 1:
                j = i - 1
            else:
                j = i + 1 if t > t0 else i - 1

            f = linear_interpolate(t, t0, y0, times[j], freqs[j])
            
            midi_note = 0
            if f > 0: 
                midi_note = math.floor(hz_to_note_number(f))

            if midi_note != prev_midi_note:
                if midi_note == 0:
                    # end old note
                    if prev_midi_note is not None:
                        old_off = mido.Message('note_off', note=prev_midi_note, velocity=32)
                        self.port.send(old_off)
                else:
                    # start new note
                    new_on = mido.Message('note_on', note=midi_note, velocity=32)
                    print(f"Sending {midi_note}")
                    self.port.send(new_on)

                    # end old note
                    if prev_midi_note is not None:
                        old_off = mido.Message('note_off', note=prev_midi_note, velocity=32)
                        self.port.send(old_off)

            prev_midi_note = midi_note
            time.sleep(self.sampling_interval)

        # end last note
        last_off = mido.Message('note_off', note=prev_midi_note, velocity=32)
        self.port.send(last_off)
