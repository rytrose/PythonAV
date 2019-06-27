import pickle
from communication.osc_client import OSCClient

def on_segment(address, args):
    print("got:", address, args)

osc_client = OSCClient(local_address="Ryans-MacBook-Pro.local", 
                       remote_address="rytrose-pi-zero-w.local")

osc_client.map("/segment", on_segment)
osc_client.begin()