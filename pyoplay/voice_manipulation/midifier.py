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
        self.sampling_interval = 0.05
        self.metro = Metro(time=self.sampling_interval)
        self.send_trig_func = None

    def process_segment(self, segment):
        times = [tf[0] for tf in segment]
        freqs = [tf[1] for tf in segment]
        return times, freqs

    def midi_note_at_t(self, t, times, freqs):
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

        return midi_note

    def send_segment(self, segment, loop=False):
        if type(segment) == tuple:
            segment = segment[0]

        self.times, self.freqs = self.process_segment(segment)

        self.start = time.time()
        self.end = segment[-1][0]

        self.t = 0
        self.prev_midi_note = None

        self.send_trig_func = TrigFunc(self.metro, self.send_midi, loop)
        self.metro.play()

    def send_midi(self, loop):
        if self.t < self.end:
            self.t = time.time() - self.start
            midi_note = self.midi_note_at_t(self.t, self.times, self.freqs)

            if midi_note != self.prev_midi_note:
                if midi_note == 0:
                    # end old note
                    if self.prev_midi_note is not None:
                        old_off = mido.Message('note_off', note=self.prev_midi_note, velocity=32)
                        self.port.send(old_off)
                    self.prev_midi_note = None
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

    def midify(self, segment):
        times, freqs = self.process_segment(segment)
        length = segment[-1][0]

        midi_notes = []

        t = 0
        prev_midi_note = self.midi_note_at_t(t, times, freqs)
        note_on_time = 0.0
        while t < length:
            midi_note = self.midi_note_at_t(t, times, freqs)
            if midi_note != prev_midi_note:
                # end prev note
                midi_notes.append((prev_midi_note, note_on_time, t))
                note_on_time = t
                prev_midi_note = midi_note
            t += self.sampling_interval

        midi_notes = list(filter(lambda note: note[0] != 0, midi_notes))
