from websocket import WS

if __name__ == '__main__':
    ws_client = WS(is_client=True, uri="ws://rytrose-pi-zero-w.local:8000")
    ws_client.start()
