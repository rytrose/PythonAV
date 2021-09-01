import math
import sys
import threading
import signal
import platform
from pyo.lib.analysis import Scope
from pyo.lib.filters import Average

from pyo.lib.randoms import Xnoise
from voices.low_voice import LowVoice

from pyo_extensions.pyo_client import PyoClient
from pyo_extensions.lux import Lux


# Integration time of light sensor, ~period of new value
lux_T = 0.100

# Platform-specific setup
if platform.system() == "Darwin":
    # On Mac OS
    # Setup the pyo server (coreaudio backend)
    pyo_client = PyoClient(audio_duplex=False, audio_output_device_id=1)

    # Stubbed lux sensor
    lux = Xnoise(freq=1 / lux_T, dist=12, x1=1, x2=0.1)

elif platform.system() == "Linux":
    # Expected to be on setup raspberry pi
    pyo_client = PyoClient(audio_backend="jack", audio_duplex=False)

    # Real lux sensor
    lux = Lux()

    # Start reading from lux sensor
    lux.play()
else:
    raise NotImplementedError("Platform unsupported")


avg_lux = Average(lux, size=math.floor(200 * (1 / lux_T)))

# Create low voice
pitch_classes = [0, 2, 3, 4, 6, 8, 9]
low_voice = LowVoice(avg_lux, pitch_classes)

# Start voices
low_voice.out()

if platform.system() == "Darwin":
    scope_lux = Scope(lux, length=1, wintitle="Lux")
    scope_avg = Scope(avg_lux, length=1, wintitle="Average Lux")
    scope_low_since_last_trigger = Scope(
        low_voice.since_last_note_phasor, length=0.2, wintitle="Since Last Note Phasor")
    scope_low_note = Scope((low_voice.note_midi - 48) / 12,
                           length=0.2, wintitle="Note")
    scope_volume = Scope(low_voice.volume,
                         length=0.2, wintitle="Volume")

    pyo_client.audio_server.gui(locals())


def on_interrupt(signal, frame):
    """Clean up and exit on SIGINT."""
    print("Exiting...")
    pyo_client.stop()
    sys.exit(0)


# Set exit on SIGINT
signal.signal(signal.SIGINT, on_interrupt)

# Block untill SIGINT
threading.Event().wait()
