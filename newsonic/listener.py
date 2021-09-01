import time
from pyo import Input, savefileFromTable
from pyo_client import PyoClient
from audio_recorder import AudioRecorder
from vad import VoiceActivityDetector
from pydub import AudioSegment
from pydub.playback import play

class Listener:
    def __init__(self):
        self.pyo_client = PyoClient(default_audio_device='newsonic')
        self.input = Input(0)
        self.sr = 44100
        self.recorder = AudioRecorder(self.input, self.sr)

    def listen(self, length=4, callback=lambda: print("no callback")):
        def cb():
            timestamps, detections = self.detect_vad()
            callback(timestamps, detections)
        self.recorder.on_stop = cb
        print(f"Recording for {length}s...")
        self.recorder.record(length=length)
        
    def detect_vad(self):
        self.recorder.record_table.save("audio.wav")
        v = VoiceActivityDetector("audio.wav")
        timestamps, detections = list(zip(*[(d[0] / self.sr, bool(d[1]))
                                 for d in v.detect_speech()]))
        return timestamps, detections

    def extract_voice(self, timestamps, detections):
        master = AudioSegment.from_file("audio.wav", format="wav")
        output = AudioSegment.empty()
        speech_segments = []

        prev_detection = False
        segment_start = 0
        for i in range(len(timestamps)):
            if not prev_detection and detections[i]:
                segment_start = timestamps[i]
            
            if prev_detection and not detections[i]:
                speech_segment = master[int(segment_start * 1000):int(timestamps[i] * 1000)]
                speech_segments.append(speech_segment)
            
            prev_detection = detections[i]

        for s in speech_segments:
            output += s
            output += AudioSegment.silent(duration=1000, frame_rate=44100)

        output.export("output.wav", format="wav")