import signal
from queue import Empty, Full
from multiprocessing import Process, Queue, Event
from pyo import PyoObject, Sig, Pattern, Clip


class Lux(PyoObject):
    """
    A PyoObject that reads from an Adafruit VEML7700 Lux Sensor.

    See https://www.adafruit.com/product/4162 for more sensor details.
    """

    def __init__(self, mul=1, add=0):
        """Creates a new Lux object.

        Args:
            mul (float or PyoObject, optional): Multiplication factor. Defaults to 1.
            add (float or PyoObject, optional): Addition factor. Defaults to 0.
        """
        # Properly initialize PyoObject's basic attributes
        PyoObject.__init__(self)

        # Setup continuous sensor reading
        self._setup_sensor_reading(mul, add)

        # Specify base object of output signal
        self._base_objs = self._clipped_sig.getBaseObjects()

        # DOES NOT START READING, REQUIRES A CALL TO .play()

    def _setup_sensor_reading(self, mul, add):
        # Read the sensor every period of the integration time
        self._period_seconds = 0.1 # Based on default 100ms integration time

        # Create the signal that will be the output
        # All values above LUX_NORMALIZATION_RATIO will be clipped
        LUX_NORMALIZATION_RATIO = 500
        self._sig = Sig(0, mul=mul / LUX_NORMALIZATION_RATIO, add=add)

        # Ensure the Sig is between 0.0-1.0
        self._clipped_sig = Clip(self._sig, min=0.0, max=1.0)

        # Create Pattern that will continuously read from the sensor
        self._pattern = Pattern(self._read_sensor, self._period_seconds)

    def _read_sensor(self):
        # Read lux value from sensor reading process
        try:
            lux = self._sensor_process_queue.get_nowait()
        except Empty:
            # If there was not a new value, do not update the signal
            return

        # Set output signal
        self._sig.setValue(lux)

    def play(self, dur=0, delay=0):
        # Setup reading from the sensor in a new process
        # Must do so to avoid stuttering of audio
        self._sensor_process_queue = Queue(1) # Only allow one value at a time
        self._sensor_read_process = SensorReader(self._sensor_process_queue)
        self._sensor_read_process.start()

        # Start the repeated querying of sensor value
        self._pattern.play()

        return PyoObject.play(self, dur, delay)

    def stop(self):
        # Stop the repeated querying of sensor value
        self._pattern.stop()

        # Stop the sensor reading process
        self._sensor_read_process.stop()
        self._sensor_read_process.join()
        self._sensor_process_queue.close()

        return PyoObject.stop(self)


class SensorReader(Process):
    def __init__(self, q):
        super(SensorReader, self).__init__()
        self._stop = Event()
        self._q = q

        # Stop self on interrupt
        signal.signal(signal.SIGINT, lambda signal, frame: self.stop())

    def _setup_vemll7700(self):
        # Don't import dependencies until initialized otherwise importing this
        # module will fail on unsupported hardware.
        import board
        import adafruit_veml7700

        # Setup the I2C bus
        i2c = board.I2C()

        # Create and return the sensor interface
        return adafruit_veml7700.VEML7700(i2c)

    def run(self):
        self._sensor = self._setup_vemll7700()

        while not self._stop.is_set():
            # Read lux value from sensor
            lux = self._sensor.lux

            # Put lux value on queue
            try:
                self._q.put(lux, timeout=0.1)
            except Full:
                continue

    def stop(self):
        self._stop.set()
