from pyo import *


class PVSample:
    """Used to play an audio file with real-time pitch shifting and time stretching."""

    def __init__(self, path=None, table=None, balance=None, attack=0.005, release=0.05):
        """Initializes pyo objects.
        Args:
            path (str): A path to the audio file to play.
            balance (pyo.Balance, optional): A pyo object to balance the RMS of this sample player with.
            attack (float): The time in seconds of the envelope attack when play() is called.
            release (float): The time in seconds of the envelope release when stop() is called.
        """
        PVSIZE = 1024
        PVOLAPS = 4

        if path:
            self.info = sndinfo(path)
            self.samples, self.duration, self.sr = sndinfo(path)[:3]
            self.table = SndTable(path)
        else:
            self.table = table
            self.samples = self.table.getSize()
            self.duration = self.table.getDur()
            self.sr = self.table.getRate()

        self.table_reader = TableRead(
            self.table, freq=1.0 / self.duration, loop=1).play()
        self.pv_analysis = PVAnal(
            self.table_reader, size=PVSIZE, overlaps=PVOLAPS)
        self.pointer = Phasor(freq=1.0 / self.duration)
        self.trans_value = SigTo(1, time=0.005)
        self.pv_buffer = PVBuffer(
            self.pv_analysis, self.pointer, pitch=self.trans_value, length=self.duration)
        self.adsr = Adsr(attack=attack, release=release)

        if balance is None:
            self.pv_synth = PVSynth(self.pv_buffer, mul=self.adsr)
            self.output = self.pv_synth
        else:
            self.pv_synth = PVSynth(self.pv_buffer)
            self.output = Balance(self.pv_synth, balance, mul=self.adsr)

        self.output.out()

    def play(self):
        """Starts playback via the envelope generator and adds the playback to the audio server graph."""
        self.adsr.play()

    def stop(self):
        """Stops playback via the envelope generator and removes the playback object from the audio server graph."""
        self.adsr.stop()

    def set_transposition(self, val):
        """Changes the transposition of playback.
        Args:
            val: The factor of transposition, where 1 is original pitch, 2 is an octave higher, 0.5 is an octave lower, etc.
        """
        self.trans_value.setValue(val)

    def set_speed(self, val):
        """Sets playback speed.
        Args:
            val (float): The speed in Hz to playback the sample at. Does not change pitch.
        """
        self.pointer.setFreq(val)

    def set_phase(self, val):
        """Sets the playback position of the sample.
        Args:
            val (float): A location between 0.0 and 1.0 where 0.0 is the beginning of the sample, and 1.0 is the end.
        """
        self.pointer.reset()
        self.pointer.setPhase(val)

    def set_balance(self, val):
        """Sets a pyo.Balance object to balance sample output with.
        Args:
            val (pyo.Balance): An audio signal to balance energy output of this sample with.
        """
        self.output = Balance(self.pv_synth, val, mul=self.adsr)
