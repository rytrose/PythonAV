from multiprocessing import Process, Pipe
from threading import Thread, Lock
from gpiozero import MCP3008, PWMLED, Button
import time
import math

class GetValue:
    def __init__(self, key):
        self.key = key


class SetValue:
    def __init__(self, key, value):
        self.key = key
        self.value = value


class PiGPIOConfig:
    def __init__(self, key, input_type, **kwargs):
        self.key = key
        self.input_type = input_type

        if input_type == "button":
            self.setup_button(kwargs)
        elif input_type == "led":
            self.setup_led(kwargs)
        elif input_type == "analog":
            self.setup_analog(kwargs)

    def setup_analog(self, kwargs):
        self.channel = kwargs["channel"]

    def setup_led(self, kwargs):
        self.pin = kwargs["pin"]

    def setup_button(self, kwargs):
        self.pin = kwargs["pin"]
        self.on_pressed = None
        self.on_released = None

        if "on_pressed" in kwargs.keys():
            self.on_pressed = kwargs["on_pressed"]

        if "on_released" in kwargs.keys():
            self.on_released = kwargs["on_released"]
        


class PiGPIO:
    def __init__(self, check_rate=0.05):
        self.client_send_connection, self.server_recv_connection = Pipe()
        self.client_recv_connection, self.server_send_connection = Pipe()
        self.configs = []
        self.button_callbacks = {}
        self.get_value_responses = []
        self.server = None
        self.started = False
        self.check_rate = check_rate

    def add_gpio(self, config):
        self.configs.append(config)

        if config.input_type == "button":
            self.button_callbacks[config.pin] = {
                "on_pressed": config.on_pressed,
                "on_released": config.on_released
            }

    def start(self):
        self.started = True
        self.server = PiGPIOServer(self.server_send_connection, self.server_recv_connection, self.configs)
        self.server.start()
        self.listen_thread = Thread(target=self.listener)
        self.listen_thread.start()

    def stop(self):
        self.server.terminate()

    def listener(self):
        while True:
            res = self.client_recv_connection.recv()
            if res["type"] == "get_value":
                self.get_value_responses.append(res)
            elif res["type"] == "button_state_change":
                if res["action"] == "pressed":
                    callback = self.button_callbacks[res["pin"]]["on_pressed"]
                else:
                    callback = self.button_callbacks[res["pin"]]["on_released"]

                if callback is not None:
                    callback()

    def get_value(self, key):
        if not self.started:
            raise Exception("You must run start() before getting or setting GPIO devices.")
        self.client_send_connection.send(GetValue(key))
        res = None
        while not res: 
            if len(self.get_value_responses) > 0:
                res = self.get_value_responses.pop(0)
            time.sleep(0.005)  # <-- breaks without this
        return res["value"]

    def set_value(self, key, value):
        if not self.started:
            raise Exception("You must run start() before getting or setting GPIO devices.")
        self.client_send_connection.send(SetValue(key, value))


class PiGPIOServer(Process):
    def __init__(self, send_connection, recv_connection, configs, check_rate=0.05):
        super(PiGPIOServer, self).__init__()
        self._send = send_connection
        self._recv = recv_connection
        self.check_rate = check_rate
        self.io_map = {}

        for config in configs:
            if config.input_type == "button":
                self.io_map[config.key] = Button(config.pin)
                self.io_map[config.key].when_pressed = self.on_pressed
                self.io_map[config.key].when_released = self.on_released
            elif config.input_type == "led":
                self.io_map[config.key] = PWMLED(config.pin)
            elif config.input_type == "analog":
                self.io_map[config.key] = MCP3008(channel=config.channel)

    def run(self):
        while True:
            if self._recv.poll(self.check_rate):
                req = self._recv.recv()
                if isinstance(req, GetValue):
                    self._send.send({
                        "type": "get_value",
                        "value": self.io_map[req.key].value
                    })
                elif isinstance(req, SetValue):
                    self.io_map[req.key].value = req.value
                else:
                    print("Don't understand type:", type(req))

    def on_pressed(self, button):
        self._send.send({
            "type": "button_state_change",
            "action": "pressed",
            "pin": button.pin
        })

    def on_released(self, button):
        self._send.send({
            "type": "button_state_change",
            "action": "released",
            "pin": button.pin
        })