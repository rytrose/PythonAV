from pythonosc import osc_server, dispatcher, udp_client
import threading


class OSCClient:
    def __init__(self, local_address="127.0.0.1", local_port=5000, remote_address="127.0.0.1", remote_port=5001):
        self.local_address = local_address
        self.local_port = local_port
        self.remote_address = remote_address
        self.remote_port = remote_port
        self.dispatcher = dispatcher.Dispatcher()
        self.osc_server = None
        self.osc_client = udp_client.SimpleUDPClient(
            self.remote_address, self.remote_port)

    def begin(self):
        self.osc_server = osc_server.ThreadingOSCUDPServer(
            (self.local_address, self.local_port), self.dispatcher)
        threading.Thread(target=self.osc_server.serve_forever).start()
        print("Listening on %s:%d, sending to %s:%d" % (self.local_address,
                                                     self.local_port, self.remote_address, self.remote_port))

    def map(self, address, func):
        self.dispatcher.map(address, func)

    def send(self, address, args):
        self.osc_client.send_message(address, args)
