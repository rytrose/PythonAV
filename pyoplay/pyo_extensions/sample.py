from pyo import *


class Sample:
    def __init__(self, path=None, table=None):
        if path:
            self.table = SndTable(path)
            self.samples, self.duration, self.sr = sndinfo(path)[:3]
        else:
            self.table = table
            self.samples = self.table.getSize()
            self.duration = self.table.getDur()
            self.sr = self.table.getRate()

        self.table_reader = TableRead(self.table, freq=1 / self.duration)

    def play(self):
        self.table_reader.out()
