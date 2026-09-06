#include <CC1101_AnalogFM.h>

CC1101_AnalogFM radio(15);
uint8_t phase = 0;

void setup() {
  radio.begin(433.92f);
  radio.setGain(50);
}

void loop() {
  radio.writeAudio(phase < 128 ? 255 : 0);
  phase += 8;
  delayMicroseconds(125);
}