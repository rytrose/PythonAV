import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
import time
import mido
import math
from pretty_midi import hz_to_note_number
from pyo import *

from midi.mido_client import MidoClient
from utils.utils import quantize, linear_interpolate, delay_func

class Midifier:
    """Midifier receives segments created by a VoiceCapture object and converts them to MIDI for external synthesis."""
    def __init__(self, output_device=""):
        self.output_device = output_device
        self.mido_client = MidoClient(output_devices=[self.output_device])
        self.port = self.mido_client.output_ports[self.output_device]
        self.sampling_interval = 0.05
        self.delays = []


    def process_segment(self, segment):
        """Returns a list of times and a list of frequencies at those times from a segment."""
        times = [tf[0] for tf in segment]
        freqs = [tf[1] for tf in segment]
        return times, freqs


    def midi_note_at_t(self, t, times, freqs):
        """Given a time t and lists of times and freqs, return a quantized MIDI note number at t."""
        # Find sampled time/index closest to t
        i, t0 = quantize(t, times, with_index=True)
        
        # Get frequency at sampled time closest to t
        y0 = freqs[i]

        # Get the next closest sampled index
        j = i + 1 if t > t0 and i < len(times) - 1 else i - 1

        # Get the interpolated f from sampled points
        f = linear_interpolate(t, t0, y0, times[j], freqs[j])

        # Convert frequency to MIDI
        midi_note = 0
        if f > 0:
            midi_note = math.floor(hz_to_note_number(f))

        return midi_note


    def midify(self, segment):
        """Get MIDI notes and times from a segment, and send them in time to external synthesis..
        
        Args:
            segment (list(tuple(float, float))): A list of (time, freq) tuples of extracted pitch contour from vocal recording.
                The pitch contour is realized by linearly interpolating the frequency between samples.

        Returns:
            list(tuple(int, float, float)): A list of (MIDI note, start_time, end_time) tuples of MIDI notes
        """
        if type(segment) == tuple:
            segment = segment[0]

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

        for note in midi_notes:
            def on(n): 
                return lambda: self.port.send(mido.Message('note_on', note=n, velocity=32))
            def off(n):
                return lambda: self.port.send(mido.Message('note_off', note=n, velocity=32))
            self.delays.append(delay_func(note[1], on(note[0])))
            self.delays.append(delay_func(note[2], off(note[0])))
        
        return midi_notes
