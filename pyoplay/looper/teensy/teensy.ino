#include <CmdMessenger.h>
#include <Bounce2.h>

#define LOOP_START_BUTTON 2
#define RECORDING_LED 3
#define LOOP_START_LED 4
#define FSR_PIN A0

Bounce startRecording = Bounce();
CmdMessenger serialClient = CmdMessenger(Serial, ',', ';', '/');

// State variables
int recordingState = 0;
long loopStartTime = 0;
long loopStartLightDur = 600;

// Command constants
enum command : int {
  error,
  start_recording,
  recording,
  loop_start
};

// CmdMessenger callbacks
void on_recording(void) {
  recordingState = serialClient.readBinArg<int>();
  digitalWrite(RECORDING_LED, recordingState);
}

void on_loop_start(void) {
  digitalWrite(LOOP_START_LED, HIGH);
  loopStartTime = millis();
}

void on_unknown_command(void) {
  serialClient.sendCmd(error, "Command without callback.");
}

void setup() {
  Serial.begin(9600);
  pinMode(RECORDING_LED, OUTPUT);
  pinMode(LOOP_START_LED, OUTPUT);
  pinMode(FSR_PIN, INPUT);

  startRecording.attach(LOOP_START_BUTTON, INPUT);
  startRecording.interval(25);

  serialClient.attach(recording, on_recording);
  serialClient.attach(loop_start, on_loop_start);
  serialClient.attach(on_unknown_command);
}

void loop() {
  startRecording.update();
  serialClient.feedinSerialData();

  if (millis() - loopStartTime > loopStartLightDur) {
    digitalWrite(LOOP_START_LED, LOW);
  }

  if (startRecording.rose()) {
    serialClient.sendBinCmd(start_recording, 1);
  } else if (startRecording.fell()) {

  }
}
