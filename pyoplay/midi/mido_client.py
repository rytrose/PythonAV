import mido

class MidoClient:
    def __init__(self, prompt_for_devices=False, input_devices=None, output_devices=None):
        self.prompt_for_devices = prompt_for_devices
        self.input_devices = input_devices
        self.output_devices = output_devices

        self.input_ports = {}
        self.output_ports = {}

        self.setup_devices()

    def setup_devices(self):
        if self.input_devices:
            for device_name in self.input_devices:
                try:
                    port = mido.open_input(device_name)
                    self.input_ports[device_name] = port
                    print("Connected to input device %s" % device_name)
                except Exception as e:
                    print("Unable to open input device %s: %s" % (device_name, e))

        if self.output_devices:
            for device_name in self.output_devices:
                try:
                    port = mido.open_output(device_name)
                    self.output_ports[device_name] = port
                    print("Connected to output device %s" % device_name)
                except Exception as e:
                    print("Unable to open input device %s: %s" % (device_name, e))

        if self.prompt_for_devices:
            inputs = mido.get_input_names()

            print("Input devices:")
            for i, input_name in enumerate(inputs):
                print("%d:\t%s" % (i, input_name))

            input_device_ids = input("Please enter input device IDs separated with spaces: ")
            input_device_ids = [int(device_id) for device_id in input_device_ids.split(" ")]

            for device_id in input_device_ids:
                try:
                    port = mido.open_input(inputs[device_id])
                    self.input_ports[inputs[device_id]] = port
                    print("Connected to input device %s" % inputs[device_id])
                except Exception as e:
                    print("Unable to open input device %s: %s" % (inputs[device_id], e))

            outputs = mido.get_output_names()

            print("\nOutput devices:")
            for i, output_name in enumerate(outputs):
                print("%d:\t%s" % (i, output_name))

            output_device_ids = input("Please enter out device IDs separated with spaces: ")
            output_device_ids = [int(device_id) for device_id in output_device_ids.split(" ")]

            for device_id in output_device_ids:
                try:
                    port = mido.open_output(outputs[device_id])
                    self.input_ports[outputs[device_id]] = port
                    print("Connected to output device %s" % outputs[device_id])
                except Exception as e:
                    print("Unable to open output device %s: %s" % (outputs[device_id], e))

if __name__ == '__main__':
    m = MidoClient(prompt_for_devices=True)
