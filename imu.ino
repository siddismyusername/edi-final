#include <Wire.h>
#include <MPU6050.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

// Replace with your WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Replace with your FastAPI server IP and port
const char* serverUrl = "http://192.168.1.100:8000/imu";

// NTP Server configurations
const char* ntpServer = "pool.ntp.org";
// Send Unix epoch timestamps in UTC. The mobile app also uses UTC epoch
// seconds, so do not apply a local timezone offset here.
const long  gmtOffset_sec = 0;
const int   daylightOffset_sec = 0;

// Variables to calculate high-precision sub-second epoch timestamps
unsigned long syncMillis = 0;
time_t syncEpoch = 0;

// ── Retry buffer for failed HTTP POSTs ──────────────────────
// Circular buffer holds payloads that failed to send so they can
// be retried on the next loop iteration instead of being lost.
#define RETRY_BUFFER_SIZE 16
String retryBuffer[RETRY_BUFFER_SIZE];
int retryHead = 0;   // next write position
int retryCount = 0;  // number of buffered payloads

void retryEnqueue(const String& payload) {
  if (retryCount < RETRY_BUFFER_SIZE) {
    retryBuffer[(retryHead + retryCount) % RETRY_BUFFER_SIZE] = payload;
    retryCount++;
  }
  // If buffer is full, the oldest packet is implicitly dropped.
}

String retryDequeue() {
  String payload = retryBuffer[retryHead];
  retryBuffer[retryHead] = "";  // free memory
  retryHead = (retryHead + 1) % RETRY_BUFFER_SIZE;
  retryCount--;
  return payload;
}

MPU6050 imu;

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");

  // Initialize and Sync Time with NTP
  Serial.println("Syncing time with NTP...");
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.println("Waiting for NTP time sync...");
    delay(1000);
  }
  
  // Establish baseline time sync
  time(&syncEpoch);
  syncMillis = millis();
  Serial.println("Time synced successfully!");

  // Initialize MPU6050
  // NOTE: Default config is ±2g accel (16384 LSB/g) and ±250°/s gyro
  // (131 LSB/(°/s)).  If you change the MPU6050 full-scale range,
  // update the conversion factors below accordingly.
  imu.initialize();
  if (imu.testConnection()) {
    Serial.println("MPU6050 connected successfully.");
  } else {
    Serial.println("MPU6050 connection failed!");
  }
}

// ── Helper: send one JSON payload via HTTP POST ─────────────
// Returns true on success (HTTP 2xx), false otherwise.
bool sendPayload(const String& payload) {
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(2000);  // 2-second timeout to avoid long stalls
  
  int httpResponseCode = http.POST(payload);
  
  bool ok = (httpResponseCode >= 200 && httpResponseCode < 300);
  if (ok) {
    String response = http.getString();
    Serial.print("HTTP ");
    Serial.print(httpResponseCode);
    Serial.print(" | ");
    Serial.println(response);
  } else {
    Serial.print("POST Error: ");
    Serial.println(httpResponseCode);
  }
  
  http.end();
  return ok;
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {

    // ── Drain retry buffer first (one per loop to stay responsive) ──
    if (retryCount > 0) {
      String queued = retryDequeue();
      if (!sendPayload(queued)) {
        // Still failing — re-enqueue for next attempt
        retryEnqueue(queued);
      } else {
        Serial.print("Retry success. Remaining retries: ");
        Serial.println(retryCount);
      }
    }

    // Read accelerometer and gyro raw data
    int16_t rawAx, rawAy, rawAz;
    int16_t rawGx, rawGy, rawGz;
    imu.getMotion6(&rawAx, &rawAy, &rawAz, &rawGx, &rawGy, &rawGz);

    // Convert MPU6050 defaults to backend units:
    // accel: +/-2g => 16384 LSB/g, output m/s^2
    // gyro: +/-250 deg/s => 131 LSB/(deg/s), output rad/s
    double ax = ((double)rawAx / 16384.0) * 9.80665;
    double ay = ((double)rawAy / 16384.0) * 9.80665;
    double az = ((double)rawAz / 16384.0) * 9.80665;
    double gx = ((double)rawGx / 131.0) * 0.017453292519943295;
    double gy = ((double)rawGy / 131.0) * 0.017453292519943295;
    double gz = ((double)rawGz / 131.0) * 0.017453292519943295;

    // Calculate current high-precision epoch timestamp (seconds with decimals)
    unsigned long currentMillis = millis();
    double timestamp = (double)syncEpoch + (double)(currentMillis - syncMillis) / 1000.0;

    // Build JSON payload. Use "sync" when camera frames come from the mobile app.
    String payload = "{";
    payload += "\"timestamp\":" + String(timestamp, 3) + ",";
    payload += "\"ax\":" + String(ax, 6) + ",";
    payload += "\"ay\":" + String(ay, 6) + ",";
    payload += "\"az\":" + String(az, 6) + ",";
    payload += "\"gx\":" + String(gx, 6) + ",";
    payload += "\"gy\":" + String(gy, 6) + ",";
    payload += "\"gz\":" + String(gz, 6) + ",";
    payload += "\"mode\":\"sync\"";
    payload += "}";

    // Send HTTP POST — enqueue on failure for retry
    if (!sendPayload(payload)) {
      retryEnqueue(payload);
      Serial.print("Buffered for retry. Queue size: ");
      Serial.println(retryCount);
    }

  } else {
    Serial.println("WiFi Disconnected. Reconnecting...");
    WiFi.begin(ssid, password);
    delay(5000);
  }

  // Delay between readings (20 Hz)
  delay(50);
}
