#ifndef CC1101_ANALOG_FM_H
#define CC1101_ANALOG_FM_H

#include <Arduino.h>
#include <SPI.h>

class CC1101_AnalogFM {
public:
  explicit CC1101_AnalogFM(uint8_t csnPin, SPIClass &spi = SPI);

  bool begin(float frequencyMHz = 433.92f);
  void startTransmit();
  void stopTransmit();

  bool setFrequency(float frequencyMHz);
  float frequency() const;

  // Gain is the percentage of the maximum configured frequency deviation.
  void setGain(uint8_t gainPercent);
  uint8_t gain() const;

  void writeAudio(uint8_t sample);
  size_t stream(Stream &source, size_t maximumBytes = SIZE_MAX);

private:
  void writeRegister(uint8_t address, uint8_t value);
  void writeBurst(uint8_t address, const uint8_t *values, size_t length);
  void sendStrobe(uint8_t command);
  void reset();
  uint8_t audioToFrequencyByte(uint8_t sample) const;

  uint8_t _csnPin;
  SPIClass &_spi;
  SPISettings _spiSettings;
  float _frequencyMHz;
  uint8_t _gainPercent;
  bool _transmitting;
};

#endif