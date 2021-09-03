from pyo import SndTable
from pyo.lib.generators import Sine
from pyo.lib.randoms import Randh, Randi, Choice
from pyo.lib.tableprocess import Granulator, Particle
from pyo.lib.tables import HannTable


class HighVoice:

    def __init__(self, lux, pitch_classes, path="voices/audio/ClaireDeLune-Selection-1.wav"):
        self.lux = lux
        self.pitch_classes = pitch_classes
        self.table = SndTable(path)
        self.env = HannTable()
        self.grains_per_second = Randi(min=1, max=10, freq=1 / 0.05)
        self.grain_pitch = Choice([0.5 + (pc / 24) for pc in self.pitch_classes] + [
                                  1 + (pc / 12) for pc in self.pitch_classes], freq=0.2)
        self.grain_dur_seconds = Randh(min=0.2, max=1.0, freq=1 / 0.05)
        self.grain_pos_samples = Randh(min=0, max=self.table.getSize(
        ) - self.grain_dur_seconds * self.table.getSamplingRate(), freq=1 / self.grain_dur_seconds)
        self.grain_dur_relative_deviation = Randh(
            min=0.0, max=1.0, freq=1 / 0.05)
        self.granulator = Particle(self.table, self.env,
                                   dens=self.grains_per_second,
                                   pitch=self.grain_pitch,
                                   pos=self.grain_pos_samples,
                                   dur=self.grain_dur_seconds,
                                   dev=self.grain_dur_relative_deviation)

    def out(self):
        self.granulator.out()
