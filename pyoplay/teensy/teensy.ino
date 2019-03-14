#include <CmdMessenger.h>
#include <Bounce2.h>

#define LOOP_START_PIN 2
#define RECORDING_LED 3

Bounce loopStart = Bounce();
CmdMessenger serialClient = CmdMessenger(Serial, ',', ';', '/');

// State variables
int recordingState = 0;

// Command constants
enum command : int {
  error,
  start_loop,
  recording
};

// CmdMessenger callbacks
void on_recording(void) {
  recordingState = serialClient.readBinArg<int>();
  digitalWrite(RECORDING_LED, recordingState);
}

void on_unknown_command(void) {
  serialClient.sendCmd(error, "Command without callback.");
}

void setup() {
  Serial.begin(9600);
  pinMode(RECORDING_LED, OUTPUT);

  loopStart.attach(LOOP_START_PIN, INPUT);
  loopStart.interval(25);

  serialClient.attach(recording, on_recording);
  serialClient.attach(on_unknown_command);
}

void loop() {
  loopStart.update();
  serialClient.feedinSerialData();

  if (loopStart.rose()) {
    serialClient.sendBinCmd(start_loop, 1);
  } else if (loopStart.fell()) {

  }
}
