from pyo import *


class Recorder:
    def __init__(self, input, length, processing=None, on_stop=None):
        """Wraps the recording of an input stream.

        Args:
            input: the input PyoObject to record
            length: the length of the recording to be done
            processing: a function that takes an input PyoObject, and returns a processed PyoObject to record
            on_stop:
        """
        self.input = input
        self.length = length
        self.processing = processing
        self.on_stop = on_stop
        self.record_table = NewTable(self.length)
        self.recording_object = None
        self.stopper = None

    def set_length(self, new_length):
        self.record_table.setSize(new_length)

    def get_table(self):
        return self.record_table.copy()

    def record(self, processing=None):
        if processing:
            self.recording_object = TableRec(processing(self.input), self.record_table).play()
        elif self.processing:
            self.recording_object = TableRec(self.processing(self.input), self.record_table).play()
        else:
            self.recording_object = TableRec(self.input, self.record_table).play()

        if self.on_stop:
            self.stopper = TrigFunc(self.recording_object['trig'], self.on_stop)
