import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import pickle
from communication.osc_client import OSCClient

osc_client = OSCClient(local_address="Ryans-MacBook-Pro.local", local_port=5001, 
                       remote_address="rytrose-pi-zero-w.local", remote_port=5000)

def on_segment(address, segment_bytes):
    segment = pickle.loads(segment_bytes)
    print("Server got segment:", segment)
    osc_client.send("/segment", segment_bytes)

osc_client.map("/segment", on_segment)
osc_client.begin()
