#include <CC1101_AnalogFM.h>

CC1101_AnalogFM radio(15); // ESP8266 D8 / GPIO15

void setup() {
  Serial.begin(500000);
  radio.begin(433.92f);
  radio.setGain(75);
}

void loop() {
  radio.stream(Serial);
}