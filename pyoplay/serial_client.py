from PyCmdMessenger import ArduinoBoard, CmdMessenger
import threading
from glob import glob
from serial.serialutil import SerialException
import time
import os.path as op


class SerialClient:
    """Handles communication an Arduino(s).
    Uses the CmdMessenger protocol to send labeled arguments to the connected Arduinos. This object defines
    the callback functions for all of the expected messages coming from the Arduninos.
    """

    def __init__(self, device_paths=None, baud_rate=9600):
        """Initializes a SerialClient.
        Args:
            device_paths: A list of device paths of Arduino(s) to attach to.
            baud_rate: An int specifying the baud rate at which to connect to the Arduino(s).
        """
        self.device_paths = device_paths
        self.baud_rate = baud_rate
        self._commands = [  # The order of this array **MUST** be the same as the enum in the Arduino code.
            ["error", "s"]  # Refers to the type signature of the message, i is for integer, f float, etc.
        ]

        self._callbacks = {
            "error": print
        }

        self._arduinos = []

    def send(self, address, args, device_path=None, device_index=0):
        """Sends arguments to a specified address at an Arduino.
        Args:
            address: The address of the message to send.
            args: One, or a list of arguments to send.
            device_path: The device path of the Arduino to send to.
            device_index: The index of Arduino to send to, in order of device_paths connected to.
        """
        if device_path:
            for arduino in self._arduinos:
                if device_path == arduino.device_path:
                    arduino.send(address, args)
                    break
            print("No connected Arduino with device path %s" % device_path)
        else:
            assert device_index < len(self._arduinos)
            self._arduinos[device_index].send(address, args)

    def add_command(self, command_name, type_signature, callback=None):
        """Registers a command for CmdMessenger communication with an Arduino.

        Args:
            command_name: A string name of the new command.
            type_signature: A string type signature of the new command.
            callback: An optional callback function to receive command messages from the Arduino.
        """
        self._commands.append([command_name, type_signature])
        if callback:
            self._callbacks[command_name] = callback

    def start(self):
        """Connects to the Arduinos."""
        if self.device_paths is None:
            arduino_paths = glob("/dev/cu.usbmodem*")
            device_path = arduino_paths[0]
            print("No device path specified, defaulting to %s" % device_path)
            self._arduinos.append(ArduinoClient(device_path, self._commands, self._callbacks, baud_rate=self.baud_rate))
        else:
            for device_path in self.device_paths:
                if not op.exists(device_path):
                    print("Device path %s not found" % device_path)
                    continue
                self._arduinos.append(ArduinoClient(device_path, self._commands, self._callbacks, baud_rate=self.baud_rate))

    # def _on_command(self, arduino, args):
    #     """Callback for handling the "command" message.
    #     Args:
    #         arduino: The ArduinoClient sent the message.
    #         args: A list of arguments.
    #     """
    #     pass


class ArduinoClient:
    """Handles the direct reading and sending to an Arduino via the CmdMessender protocol.
    Reading of the serial connection happens as fast as possible on its own thread.
    """

    def __init__(self, device_path, commands, callbacks, baud_rate=9600):
        """Initializes an ArduinoClient."""
        self.device_path = device_path
        self.commands = commands
        self.callbacks = callbacks
        self.baud_rate = baud_rate
        self._device = ArduinoBoard(self.device_path, baud_rate=self.baud_rate)
        self._client = CmdMessenger(self._device, self.commands)
        self._connected = True
        self._read_thread = threading.Thread(target=self._read).start()  # Read from the connection on a new thread.

    def send(self, address, args):
        """
        Sends a message through the serial connection.
        Args:
            address: The address of the message to send.
            args: One, or a list of arguments to send.
        """
        if isinstance(args, list):
            send_args = tuple(args)
        else:
            send_args = (args,)

        if self._connected:
            try:
                self._client.send(address, *send_args)
            except SerialException as e:
                print("Arduino error (Device: %s):" % self.device_path, e)
                threading.Thread(target=self._reconnect_serial).start()

    def _read(self):
        """Reads from the serial connection forever.
        Also calls callbacks in their own thread as to not block further reading.
        """
        while self._connected:
            try:
                message = self._client.receive()
                if message is not None:
                    address = message[0]
                    args = message[1]

                    if address in self.callbacks.keys():
                        threading.Thread(target=self.callbacks[address], args=(self, args)).start()
                    else:
                        print("Address not understood: %s from device %s" % (address, self.device_path))
            except SerialException as e:
                print("Arduino error (Device: %s):" % self.device_path, e)
                threading.Thread(target=self._reconnect_serial).start()

    def _reconnect_serial(self):
        """Continually attempts to connect to the previously connected Arduino."""
        self._connected = False
        print("Reconnecting Arduino (Device: %s)..." % self.device_path)

        def _reconnect(arduino_obj):
            try:
                arduino_obj._device = ArduinoBoard(arduino_obj.device_path, baud_rate=arduino_obj._baud_rate)
                arduino_obj._client = CmdMessenger(arduino_obj._device, arduino_obj._commands)
                arduino_obj._connected = True
                arduino_obj._read_thread = threading.Thread(target=arduino_obj._read).start()
            except:
                pass  # No idea how long it may take to reconnect, so don't want to print anything

        while not self._connected:
            _reconnect(self)
            time.sleep(0.5)
