from pyo import *


class AudioRecorder:
    def __init__(self, input_object, sr, length=4, processing=None, on_stop=None, pattern=None):
        """Wraps the recording of an input stream.

        Args:
            input: the input PyoObject to record
            length: the length of the recording to be done
            processing: a function that takes an input PyoObject, and returns a processed PyoObject to record
            on_stop:
        """
        self.input = input_object
        self.sr = sr
        self.length = length
        self.processing = processing
        self.on_stop = on_stop
        self.ctr_trig = Trig()
        self.ctr = Count(self.ctr_trig)
        self.record_table = NewTable(self.length)
        self.pattern = pattern
        self.recording_object = None
        self.stopper = None
        self.max_length = 15

    def set_length(self, new_length):
        self.record_table.setSize(new_length)

    def get_table(self):
        return self.record_table.getTable()

    def get_table_copy(self):
        return self.record_table.copy()

    def on_recording_end(self):
        if self.pattern:
            self.pattern.stop()
        if self.on_stop:
            self.on_stop()

    def record(self, processing=None, length=None):
        if length:
            if length <= self.max_length:
                self.record_table = NewTable(length)
            else:
                print("Truncating length to maximum of {} seconds.".format(
                    self.max_length))
                self.record_table = NewTable(self.max_length)
        else:
            self.record_table.reset()
    
        if processing:
            self.recording_object = TableRec(
                processing(self.input), self.record_table).play()
        elif self.processing:
            self.recording_object = TableRec(
                self.processing(self.input), self.record_table).play()
        else:
            self.recording_object = TableRec(
                self.input, self.record_table).play()

        if self.pattern:
            self.pattern.play()

        self.ctr_trig.play()

        self.stopper = TrigFunc(
            self.recording_object['trig'], self.on_recording_end)

    def stop(self):
        self.recording_object.stop()
        num_samples_recorded = self.ctr.get()
        trimmed_table = NewTable(num_samples_recorded / self.sr)
        trimmed_table.copyData(self.record_table)
        self.record_table = trimmed_table
        self.on_recording_end()
