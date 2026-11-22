#include <WiFi.h>
#include <HTTPClient.h>

const int LED_PIN = 2;

const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

const char* CSV_URL =
  "https://raw.githubusercontent.com/imannajihahzainol/IOT-WEATHER-PROJECT/refs/heads/main/data/forecasts.csv";

const int RAIN_THRESHOLD = 60;


void setup() {

  pinMode(LED_PIN, OUTPUT);

  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== WEATHER RAIN ALERT ===");

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}


void loop() {

  if (WiFi.status() == WL_CONNECTED) {

    HTTPClient http;

    Serial.println();
    Serial.println("Fetching forecast data...");

    http.begin(CSV_URL);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {

      Serial.println("GitHub data retrieved successfully.");

      int rainProbability = getForecastProbability(http);

      if (rainProbability >= 0) {

        Serial.print("Rain Probability: ");
        Serial.print(rainProbability);
        Serial.println("%");

        if (rainProbability >= RAIN_THRESHOLD) {

          digitalWrite(LED_PIN, HIGH);

          Serial.println("RAIN ALERT - LED ON");

        } else {

          digitalWrite(LED_PIN, LOW);

          Serial.println("NO RAIN ALERT - LED OFF");
        }

      } else {

        Serial.println("Could not find forecast probability.");

        digitalWrite(LED_PIN, LOW);
      }

    } else {

      Serial.print("HTTP Error: ");
      Serial.println(httpCode);

      digitalWrite(LED_PIN, LOW);
    }

    http.end();

  } else {

    Serial.println("WiFi disconnected.");
    digitalWrite(LED_PIN, LOW);
  }

  delay(30000);
}


// Read the CSV line-by-line
// get the first future forecast.
int getForecastProbability(HTTPClient &http) {

  WiFiClient* stream = http.getStreamPtr();

  // Read and ignore the CSV header
  String header = stream->readStringUntil('\n');

  Serial.println("Reading forecast rows...");

  while (http.connected() && stream->available()) {

    String row = stream->readStringUntil('\n');

    row.trim();

    if (row.length() == 0) {
      continue;
    }

    // CSV columns:
    //
    // 0 fetched_at
    // 1 target_time
    // 2 lead_hours
    // 3 temperature
    // 4 humidity
    // 5 precipitation
    // 6 precip_prob
    // 7 wind_speed

    int comma1 = row.indexOf(',');
    int comma2 = row.indexOf(',', comma1 + 1);
    int comma3 = row.indexOf(',', comma2 + 1);
    int comma4 = row.indexOf(',', comma3 + 1);
    int comma5 = row.indexOf(',', comma4 + 1);
    int comma6 = row.indexOf(',', comma5 + 1);
    int comma7 = row.indexOf(',', comma6 + 1);

    if (comma7 == -1) {
      continue;
    }

    String leadHours =
      row.substring(comma2 + 1, comma3);

    String probability =
      row.substring(comma6 + 1, comma7);

    int lead = leadHours.toInt();
    int rainProbability = probability.toFloat();

    // Use the first future forecast
    if (lead >= 1) {

      Serial.print("Forecast lead time: ");
      Serial.print(lead);
      Serial.println(" hour(s)");

      Serial.print("Rain probability found: ");
      Serial.print(rainProbability);
      Serial.println("%");

      return rainProbability;
    }
  }

  Serial.println("No future forecast found.");

  return -1;
}
