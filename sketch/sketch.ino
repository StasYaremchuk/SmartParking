 #include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include "DHT.h"

const char* ssid = "ASUS_10Kulp";
const char* password = "i_love_your_mom";
const char* serverUrl = "http://192.168.1.127:5001/update"; 

// Модуль 1
const int red1 = 13;    const int green1 = 12;
const int trig1 = 5;     const int echo1 = 18;

// Модуль 2
const int red2 = 14;    const int green2 = 27;
const int trig2 = 19;    const int echo2 = 21;

// В'їзд та Погода
const int trigIn = 33;   const int echoIn = 32;
const int servoPin = 25;
#define DHTPIN 4
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);
Servo barrier;

const int parkThreshold = 15; 
const int entryThreshold = 10; 
const unsigned long waitTime = 5000; 

unsigned long barrierTimer = 0;
bool isBarrierOpen = false;

int lastState1 = -1;
int lastState2 = -1;
unsigned long lastServerSync = 0;
const unsigned long syncInterval = 15000; 


long getDistance(int trig, int echo) {
  digitalWrite(trig, LOW); delayMicroseconds(2);
  digitalWrite(trig, HIGH); delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long duration = pulseIn(echo, HIGH, 25000);
  if (duration == 0) return 999;
  return duration * 0.034 / 2;
}

void sendUpdate(int slotId, int status, float t, float h) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<200> doc;
    doc["id"] = slotId;
    doc["status"] = status;
    doc["temp"] = isnan(t) ? 0 : t;
    doc["hum"] = isnan(h) ? 0 : h;

    String json;
    serializeJson(doc, json);
    
    int httpCode = http.POST(json);
    Serial.printf("[HTTP] Slot %d, Code: %d\n", slotId, httpCode);
    http.end();
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  
  pinMode(red1, OUTPUT); pinMode(green1, OUTPUT);
  pinMode(trig1, OUTPUT); pinMode(echo1, INPUT);
  
  pinMode(red2, OUTPUT); pinMode(green2, OUTPUT);
  pinMode(trig2, OUTPUT); pinMode(echo2, INPUT);
  
  pinMode(trigIn, OUTPUT); pinMode(echoIn, INPUT);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");

  ESP32PWM::allocateTimer(0);
  barrier.setPeriodHertz(50);
  barrier.attach(servoPin, 500, 2400); 
  barrier.write(0); 
}

void loop() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  long d1 = getDistance(trig1, echo1);
  long d2 = getDistance(trig2, echo2);
  long dIn = getDistance(trigIn, echoIn);

  int currentState1 = (d1 < parkThreshold) ? 1 : 0;
  int currentState2 = (d2 < parkThreshold) ? 1 : 0;

  digitalWrite(red1, currentState1); digitalWrite(green1, !currentState1);
  digitalWrite(red2, currentState2); digitalWrite(green2, !currentState2);

  bool timeToSync = (millis() - lastServerSync > syncInterval);
  
  if (currentState1 != lastState1 || timeToSync) {
    sendUpdate(1, currentState1, t, h);
    lastState1 = currentState1;
    if (timeToSync) lastServerSync = millis();
  }
  
  if (currentState2 != lastState2 || timeToSync) {
    sendUpdate(2, currentState2, t, h);
    lastState2 = currentState2;
    if (timeToSync) lastServerSync = millis();
  }

  if (dIn < entryThreshold) {
    if (!isBarrierOpen) {
      Serial.println("ENTRY: OPEN");
      barrier.write(90);
      isBarrierOpen = true;
    }
    barrierTimer = millis(); 
  } else {
    if (isBarrierOpen && (millis() - barrierTimer >= waitTime)) {
      Serial.println("ENTRY: CLOSE");
      barrier.write(0);
      isBarrierOpen = false;
    }
  }

  delay(200); 
}