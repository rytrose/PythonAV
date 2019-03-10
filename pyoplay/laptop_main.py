from websocket import WS

if __name__ == '__main__':
    ws_client = WS(uri="ws://rytrose-pi-zero-w.local:8000")
    ws_client.start()
