#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>

#define ESP8266_LED 5
#define BUTTON 12

int currentTime = 0;

int tempButton = 0;
int buttonPrev = 0;
int button = 0;
int buttonTime = 0;
int buttonTimeout = 50;  // ms

int tempPot = 0;
int pot = 0;
int potTime = 0;
int potTimeout = 100;  // ms
int beats = 4;
int numBeats = 4;

int socketNum;

WebSocketsServer webSocket = WebSocketsServer(81);

const int capacity = JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(2);
String message;

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {

  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[%u] Disconnected!\n", num);
      break;
    case WStype_CONNECTED:
      {
        IPAddress ip = webSocket.remoteIP(num);
        Serial.printf("[%u] Connected from %d.%d.%d.%d url: %s\n", num, ip[0], ip[1], ip[2], ip[3], payload);
        socketNum = num;

        StaticJsonDocument<capacity> doc;
        doc["address"] = "connected";
        JsonArray args = doc.createNestedArray("args");
        args.add(0);

        String message;
        serializeJson(doc, message);
        webSocket.sendTXT(num, message);
      }
      break;
    case WStype_TEXT:
      Serial.printf("[%u] get Text: %s\n", num, payload);
      break;
  }

}

void setup()
{
  Serial.begin(115200);
  pinMode(ESP8266_LED, OUTPUT);
  pinMode(BUTTON, INPUT);

  Serial.println();
  Serial.println();
  Serial.print("Connecting... ");

  WiFi.hostname("rytrose_thing");
  WiFi.mode(WIFI_STA);
  WiFi.begin();

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
  Serial.println("RSSI: ");
  Serial.println(WiFi.RSSI());

  if (!MDNS.begin("rytrose_thing")) {
    Serial.println("Error setting up mDNS responder.");
  }
  Serial.println("mDNS responder started");

  webSocket.begin();
  webSocket.onEvent(webSocketEvent);
}

void loop()
{
  webSocket.loop();

  currentTime = millis();

  tempButton = digitalRead(BUTTON);
  if (currentTime - buttonTime >= buttonTimeout) {
    if (buttonPrev == 0 && tempButton == 1) {
      button = 1;

      StaticJsonDocument<capacity> doc;
      doc["address"] = "pressed";
      JsonArray args = doc.createNestedArray("args");
      args.add(0);

      String message;
      serializeJson(doc, message);
      webSocket.sendTXT(socketNum, message);
    }
    else if (buttonPrev == 1 && tempButton == 0) {
      button = 0;

      StaticJsonDocument<capacity> doc;
      doc["address"] = "released";
      JsonArray args = doc.createNestedArray("args");
      args.add(0);

      String message;
      serializeJson(doc, message);
      webSocket.sendTXT(socketNum, message);
    }
    buttonTime = currentTime;
    buttonPrev = button;
  }

  if (millis() % 50 == 0) {
    pot = analogRead(A0);
    if (currentTime - potTime >= potTimeout) {
      beats = 4 + ((8 * pot) / 1023);

      if (numBeats != beats) {
        numBeats = beats;

        StaticJsonDocument<capacity> doc;
        doc["address"] = "numBeats";
        JsonArray args = doc.createNestedArray("args");
        args.add(numBeats);

        String message;
        serializeJson(doc, message);
        webSocket.sendTXT(socketNum, message);
      }
      potTime = currentTime;
    }
  }
}

