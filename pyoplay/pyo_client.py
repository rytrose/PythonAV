from pyo import *


class PyoClient:
    def __init__(self, audio=True, midi=False):
        self.default_audio_device = "audiobox"

        self.audio_server = None
        self.midi_server = None
        self.midi_device_ids = None

        if audio:
            self.setup_audio()
            if midi:
                self.setup_midi()
            else:
                self.audio_server.deactivateMidi()
            self.audio_server.boot().start()

        else:
            if midi:
                self.setup_midi()

    def setup_audio(self, prompt_for_devices=False):
        self.audio_server = Server()
        input_devices, output_devices = pa_get_devices_infos()
        input_device_id = None
        output_device_id = None

        if not prompt_for_devices:  # attempt to set up default device
            default_input_found = False
            default_output_found = False

            for input_device, input_device_info in input_devices.items():  # check input devices
                if self.default_audio_device in input_device_info['name'].lower():
                    default_input_found = True
                    input_device_id = input_device
                    self.audio_server.setInputDevice(input_device_id)
                    break

            if default_input_found:
                for output_device, output_device_info in output_devices.items():  # check output devices
                    if self.default_audio_device in output_device_info['name'].lower():
                        default_output_found = True
                        output_device_id = output_device
                        self.audio_server.setOutputDevice(output_device_id)
                        break

            if not (default_input_found and default_output_found):
                print("Unable to attach to default audio device, prompting for selection.")
                prompt_for_devices = True
            else:
                print("Audio input device %s connected." % input_devices[input_device_id]['name'])
                print("Audio output device %s connected." % output_devices[output_device_id]['name'])

        if prompt_for_devices:
            pa_list_devices()

            input_device_id = int(input("Input device: "))
            output_device_id = int(input("Output device: "))

            self.audio_server.setInputDevice(input_device_id)
            self.audio_server.setOutputDevice(output_device_id)

            print("Audio input device %s connected." % input_devices[input_device_id]['name'])
            print("Audio output device %s connected." % output_devices[output_device_id]['name'])

    def setup_midi(self, prompt_for_device=True):
        if prompt_for_device:
            pm_list_devices()

            midi_devices_raw = input("Enter desired device ids, separated by spaces: ")
            self.midi_device_ids = [int(midi_device_id) for midi_device_id in midi_devices_raw.split(" ")]

        try:
            self.midi_server = MidiListener(self.on_midi, mididev=self.midi_device_ids, reportdevice=True)
            self.midi_server.start()
        except Exception as e:
            print("Unable to setup MIDI.", e)

    def on_midi(self, status, note, velocity, device_id):
        pass


if __name__ == '__main__':
    p = PyoClient()
