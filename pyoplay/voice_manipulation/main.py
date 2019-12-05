import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from pyo import *

from pyo_extensions.pyo_client import PyoClient
from voice_manipulation.capture import VoiceCapture
from voice_manipulation.midifier import Midifier

# c = PyoClient(default_audio_device="built-in")
c = PyoClient(audio_input_device_id=3, audio_output_device_id=1)
length = 4.0
v = VoiceCapture(c.audio_server.getSamplingRate(), length)
m = Midifier("IAC Driver VoiceCapture")

trig = None
trig_func = None

def do():
    global trig, trig_func
    trig = v.playback.table_reader['trig']
    trig_func = TrigFunc(trig, m.midify, arg=(v.segment,))
    v.play()
    m.midify(v.segment)

v.record(record_callback=do)
