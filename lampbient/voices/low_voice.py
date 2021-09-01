from pyo.lib.effects import Chorus
from pyo.lib.generators import LFO, Phasor, Sine
from pyo.lib.triggers import Thresh, Timer, Trig, TrigChoice, TrigFunc, TrigRand
from pyo.lib.utils import MToF

from util import clamp


class LowVoice:

    def __init__(self, lux, pitch_classes):
        self.lux = lux
        self.pitch_classes = pitch_classes
        self.OCTAVE = 4
        self.pitches = [(12 * self.OCTAVE) + p for p in self.pitch_classes]

        self._setup_note_triggering()

        self.VOLUME_LFO_MAX_FREQ = 10
        # Type 3 - triangle
        self.volume = LFO(freq=self.VOLUME_LFO_MAX_FREQ *
                          lux, mul=0.5, add=0.5, type=3)
        self.sine = Sine(freq=self.note_freq, mul=self.volume)
        self.chorus = Chorus(self.sine, depth=2, feedback=0.01)
        self.master = self.chorus

        # Pitch
        # + Pitch classes provided
        # + Pitch selection stochastic
        # + Pitch transition moment based threshold of light (with maximum time between notes)
        # + Pitch portamento based on time between notes
        # Volume
        # - LFO with frequency based off of moving average of lux

    def _setup_note_triggering(self):
        # The signal that will trigger a new note
        self.note_trigger = Trig()

        # The note chosen at any time
        self.note_midi = TrigChoice(
            self.note_trigger, self.pitches, port=0.1, init=self.pitches[0])
        self.note_freq = MToF(self.note_midi)

        # Measure time between triggers to influence portamento
        self.time_between_notes = Timer(self.note_trigger, self.note_trigger)
        self.time_between_notes_buffer = []
        self.TIME_BETWEEN_NOTES_MOVING_AVG_LEN = 5
        self.PORT_DEC_FACTOR = 0.9
        self.PORT_INC_FACTOR = 1.25
        self.MIN_PORT = 0.0
        self.MAX_PORT = 0.5

        def _set_port():
            # Capture time since last note
            time_between_notes = self.time_between_notes.get()

            # Calculate moving average of time between notes
            self.time_between_notes_buffer.append(time_between_notes)
            if len(self.time_between_notes_buffer) > self.TIME_BETWEEN_NOTES_MOVING_AVG_LEN:
                self.time_between_notes_buffer.pop(0)
            time_between_notes_mvg_avg = sum(self.time_between_notes_buffer) / len(
                self.time_between_notes_buffer) if len(self.time_between_notes_buffer) > 0 else 0.0

            # Decrease portamento time if notes are speeding up,
            # increase portamento time if notes are slowing down
            port_change = self.PORT_DEC_FACTOR if time_between_notes_mvg_avg > time_between_notes else self.PORT_INC_FACTOR
            new_port = self.note_midi.port * port_change
            clamped_new_port = clamp(new_port, self.MIN_PORT, self.MAX_PORT)
            self.note_midi.setPort(clamped_new_port)
        self.set_note_portamento = TrigFunc(
            self.note_trigger, _set_port)

        # LUX-BASED NOTE TRIGGERING
        self.LUX_TRIGGER_THRESHOLD = 0.5
        self.lux_trigger = TrigFunc(
            Thresh(self.lux, dir=0, threshold=self.LUX_TRIGGER_THRESHOLD),
            self.note_trigger.play
        )

        # TIMEOUT-BASED NOTE TRIGGERING
        # Every time a note is triggered, compute a new timeout threshold between min/max
        self.TIMEOUT_TRIGGER_THRESHOLD_MIN_SECONDS = 8
        self.TIMEOUT_TRIGGER_THRESHOLD_MAX_SECONDS = 10
        self.TIMEOUT_TRIGGER_THRESHOLD_INIT_SECONDS = self.TIMEOUT_TRIGGER_THRESHOLD_MIN_SECONDS
        self.note_trigger_threshold_seconds = TrigRand(
            self.note_trigger,
            min=self.TIMEOUT_TRIGGER_THRESHOLD_MIN_SECONDS,
            max=self.TIMEOUT_TRIGGER_THRESHOLD_MAX_SECONDS,
            init=self.TIMEOUT_TRIGGER_THRESHOLD_INIT_SECONDS)
        # Phasor goes from 0 to 1 over the duration of the threshold
        # Add a tiny offset so we can trigger off of it (does not reliably "equal" 0 or 1 to cross the threshold)
        self.since_last_note_phasor = Phasor(
            freq=1 / self.note_trigger_threshold_seconds, add=0.00001)
        # Trigger a new note when the phasor hits 1
        self.timeout_trigger = TrigFunc(
            Thresh(self.since_last_note_phasor, dir=0, threshold=1),
            self.note_trigger.play
        )
        # Whenever a note is triggered, reset the phasor
        self.trigger_phasor_reset = TrigFunc(
            self.note_trigger, self.since_last_note_phasor.reset)

    def out(self):
        # Start playing the master audio
        self.master.out()

        # Trigger the first note
        self.note_trigger.play()
