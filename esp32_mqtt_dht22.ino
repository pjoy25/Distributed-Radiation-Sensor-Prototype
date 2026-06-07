/*
  ESP32 + DHT22 MQTT telemetry publisher.

  Purpose:
  - Stand-in edge node for the distributed radiation sensing network.
  - Publishes the same general JSON contract used by the backend prototype.

  Arduino Library Manager dependencies:
  - PubSubClient by Nick O'Leary
  - DHT sensor library by Adafruit
  - ArduinoJson by Benoit Blanchon

  Wiring example:
  - DHT22 VCC  -> ESP32 3V3
  - DHT22 GND  -> ESP32 GND
  - DHT22 DATA -> ESP32 GPIO 4
  - 10k resistor between DATA and VCC is recommended.
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <time.h>

#define DHT_PIN 4
#define DHT_TYPE DHT22

const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* MQTT_HOST = "YOUR_MQTT_BROKER_IP";  // Example: laptop IP running Docker Mosquitto
const int MQTT_PORT = 1883;

const char* SITE_ID = "utd-test-lab";
const char* NODE_ID = "esp32-dht22-001";
const char* SENSOR_TYPE = "dht22-simulation";
const char* FIRMWARE_VERSION = "esp32-dht22-0.1.0";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
DHT dht(DHT_PIN, DHT_TYPE);

unsigned long sequenceNumber = 0;
const unsigned long publishIntervalMs = 5000;
unsigned long lastPublishMs = 0;

String isoTimestampUtc() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "1970-01-01T00:00:00Z";
  }
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi connected. IP: ");
  Serial.println(WiFi.localIP());

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void connectMQTT() {
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  while (!mqttClient.connected()) {
    Serial.print("Connecting to MQTT...");
    if (mqttClient.connect(NODE_ID)) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" retrying in 2 seconds");
      delay(2000);
    }
  }
}

void publishTelemetry() {
  float temperatureC = dht.readTemperature();
  float humidityPct = dht.readHumidity();

  if (isnan(temperatureC) || isnan(humidityPct)) {
    Serial.println("DHT22 read failed; skipping publish");
    return;
  }

  sequenceNumber++;

  StaticJsonDocument<768> doc;
  doc["node_id"] = NODE_ID;
  doc["site_id"] = SITE_ID;
  doc["timestamp"] = isoTimestampUtc();
  doc["sensor_type"] = SENSOR_TYPE;

  JsonObject reading = doc.createNestedObject("reading");
  reading["temperature_c"] = temperatureC;
  reading["humidity_pct"] = humidityPct;

  doc["battery_pct"] = nullptr;  // Replace later if battery measurement is available.
  doc["rssi"] = WiFi.RSSI();
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["status"] = "ok";
  doc["sequence"] = sequenceNumber;

  char payload[768];
  serializeJson(doc, payload, sizeof(payload));

  char topic[128];
  snprintf(topic, sizeof(topic), "radiation/%s/%s/telemetry", SITE_ID, NODE_ID);

  bool ok = mqttClient.publish(topic, payload, false);
  Serial.print("Published to ");
  Serial.print(topic);
  Serial.print(" ok=");
  Serial.println(ok ? "true" : "false");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  dht.begin();
  connectWiFi();
  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }
  if (!mqttClient.connected()) {
    connectMQTT();
  }

  mqttClient.loop();

  unsigned long nowMs = millis();
  if (nowMs - lastPublishMs >= publishIntervalMs) {
    lastPublishMs = nowMs;
    publishTelemetry();
  }
}
