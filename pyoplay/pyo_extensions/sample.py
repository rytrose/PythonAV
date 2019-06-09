from pyo import *


class Sample:
    def __init__(self, path=None, table=None, processing=None, parallel_processing=True, loop=0):
        """Controls playback and processing for a sound file or table.
        
        Args:
            path (str, optional): Path to a sound file to play. Defaults to None.
            table (pyo.PyoTableObject, optional): A table of audio data to play. Defaults to None.
            processing (List, optional): A list of tuples of (pyo.PyoObject, kwargs) which define
            a signal processing effects to apply to the audio data. Defaults to None.
            parallel_processing (bool, optional): Determines whether or not effects are applied to 
            the original audio (True), or to the output of the previous effect (False). Defaults to True.
            loop (int, optional): Determines whether playback should be looped. Defaults to 0.
        """
        if path:
            self.table = SndTable(path)
            self.samples, self.duration, self.sr = sndinfo(path)[:3]
        else:
            self.table = table
            self.samples = self.table.getSize()
            self.duration = self.table.getDur()
            self.sr = self.table.getRate()

        self.table_reader = TableRead(self.table, freq=1 / self.duration)
        self.table_reader.setLoop(loop)

        if processing:
            self.signal_chain = []
            for i, (effect, kwargs) in enumerate(processing):
                if i > 0:
                    if parallel_processing:
                        node = effect(self.table_reader, **kwargs).out()
                    else:
                        node = effect(self.signal_chain[i - 1], **kwargs).out()
                    self.signal_chain.append(node)
                else:
                    node = effect(self.table_reader, **kwargs).out()
                    self.signal_chain.append(node)

    def play(self, num_channels=2, channel=0):
        if num_channels == 1:
            self.table_reader = self.table_reader.out(channel)
        else:
            self.table_reader.out()

    def stop(self):
        self.table_reader.stop()

    def set_loop(self, loop):
        self.table_reader.setLoop(loop)