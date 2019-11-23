import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

from pyo_extensions.pyo_client import PyoClient
from voice_manipulation.capture import VoiceCapture
from voice_manipulation.midifier import Midifier

c = PyoClient(default_audio_device="built-in")
v = VoiceCapture(c.audio_server.getSamplingRate(), 4.0)
m = Midifier("IAC Driver VoiceCapture")
