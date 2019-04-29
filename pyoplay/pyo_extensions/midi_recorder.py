import mido
from pretty_midi import PrettyMIDI
import time
import threading


class MIDIRecorder:
    def __init__(self, port, length):
        self.input = port
        self.length = length
        self.mido_recording = None

    def set_length(self, new_length):
        self.length = new_length

    def get_mido_recording(self):
        return self.mido_recording

    def get_pretty_midi_recording(self):
        pm = PrettyMIDI(midi_data=self.mido_recording)
        return pm

    def record(self):
        def record_in_thread(self):
            self.mido_recording = mido.MidiFile()
            track = mido.MidiTrack()
            self.mido_recording.tracks.append(track)

            start_time = time.time()
            last_msg_time = start_time

            while time.time() - start_time <= self.length:
                for msg in self.input.iter_pending():
                    now_time = time.time()
                    msg.time = int(960 * (now_time - last_msg_time))
                    last_msg_time = now_time
                    track.append(msg)
                time.sleep(0.005)

        record_thread = threading.Thread(target=record_in_thread, args=(self,))
        record_thread.start()
