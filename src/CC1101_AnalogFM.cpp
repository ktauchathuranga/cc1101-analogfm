#include "CC1101_AnalogFM.h"

namespace {
constexpr uint8_t kFrequency2 = 0x0D;
constexpr uint8_t kFrequency1 = 0x0E;
constexpr uint8_t kFrequency0 = 0x0F;
constexpr uint8_t kStx = 0x35;
constexpr uint8_t kSres = 0x30;
constexpr uint32_t kCrystalHz = 26000000UL;
constexpr int16_t kCenterFrequencyByte = 128;
constexpr int16_t kMaximumDeviationBytes = 32;

const uint8_t kInitRegisters[][2] = {
  {0x0B, 0x06}, {0x0C, 0x00}, {0x10, 0xF8}, {0x11, 0x32},
  {0x12, 0x00}, {0x15, 0x15}, {0x18, 0x18}, {0x19, 0x16},
  {0x1A, 0x6C}, {0x1B, 0x43}, {0x1C, 0x40}, {0x1D, 0x91},
  {0x21, 0x56}, {0x22, 0x10}, {0x23, 0xE9}, {0x24, 0x2A},
  {0x25, 0x00}, {0x26, 0x1F}, {0x3E, 0x12}
};
}

CC1101_AnalogFM::CC1101_AnalogFM(uint8_t csnPin, SPIClass &spi)
  : _csnPin(csnPin), _spi(spi), _spiSettings(8000000, MSBFIRST, SPI_MODE0),
    _frequencyMHz(433.92f), _gainPercent(100), _transmitting(false) {}

bool CC1101_AnalogFM::begin(float frequencyMHz) {
  pinMode(_csnPin, OUTPUT);
  digitalWrite(_csnPin, HIGH);
  _spi.begin();
  reset();

  for (size_t index = 0; index < sizeof(kInitRegisters) / sizeof(kInitRegisters[0]); ++index) {
    writeRegister(kInitRegisters[index][0], kInitRegisters[index][1]);
  }

  if (!setFrequency(frequencyMHz)) {
    return false;
  }
  startTransmit();
  return true;
}

bool CC1101_AnalogFM::setFrequency(float frequencyMHz) {
  if (frequencyMHz <= 0.0f || frequencyMHz >= 800.0f) {
    return false;
  }

  const uint32_t word = static_cast<uint32_t>((frequencyMHz * 1000000.0f * 65536.0f) / kCrystalHz);
  const uint8_t values[] = {
    static_cast<uint8_t>((word >> 16) & 0xFF),
    static_cast<uint8_t>((word >> 8) & 0xFF),
    static_cast<uint8_t>(word & 0xFF)
  };
  writeBurst(kFrequency2, values, sizeof(values));
  _frequencyMHz = frequencyMHz;
  return true;
}

float CC1101_AnalogFM::frequency() const { return _frequencyMHz; }

void CC1101_AnalogFM::setGain(uint8_t gainPercent) {
  _gainPercent = gainPercent > 100 ? 100 : gainPercent;
}

uint8_t CC1101_AnalogFM::gain() const { return _gainPercent; }

void CC1101_AnalogFM::startTransmit() {
  sendStrobe(kStx);
  _transmitting = true;
}

void CC1101_AnalogFM::stopTransmit() {
  sendStrobe(0x36);
  _transmitting = false;
}

void CC1101_AnalogFM::writeAudio(uint8_t sample) {
  const uint8_t frequencyByte = audioToFrequencyByte(sample);
  writeRegister(kFrequency0, frequencyByte);
}

size_t CC1101_AnalogFM::stream(Stream &source, size_t maximumBytes) {
  size_t count = 0;
  while (source.available() > 0 && count < maximumBytes) {
    writeAudio(static_cast<uint8_t>(source.read()));
    ++count;
  }
  return count;
}

uint8_t CC1101_AnalogFM::audioToFrequencyByte(uint8_t sample) const {
  const int16_t centered = static_cast<int16_t>(sample) - 128;
  const int16_t offset = (centered * kMaximumDeviationBytes * _gainPercent) / (127 * 100);
  return static_cast<uint8_t>(constrain(kCenterFrequencyByte + offset, 96, 160));
}

void CC1101_AnalogFM::writeRegister(uint8_t address, uint8_t value) {
  _spi.beginTransaction(_spiSettings);
  digitalWrite(_csnPin, LOW);
  _spi.transfer(address);
  _spi.transfer(value);
  digitalWrite(_csnPin, HIGH);
  _spi.endTransaction();
}

void CC1101_AnalogFM::writeBurst(uint8_t address, const uint8_t *values, size_t length) {
  _spi.beginTransaction(_spiSettings);
  digitalWrite(_csnPin, LOW);
  _spi.transfer(address | 0x40);
  for (size_t index = 0; index < length; ++index) {
    _spi.transfer(values[index]);
  }
  digitalWrite(_csnPin, HIGH);
  _spi.endTransaction();
}

void CC1101_AnalogFM::sendStrobe(uint8_t command) {
  _spi.beginTransaction(_spiSettings);
  digitalWrite(_csnPin, LOW);
  _spi.transfer(command);
  digitalWrite(_csnPin, HIGH);
  _spi.endTransaction();
}

void CC1101_AnalogFM::reset() {
  sendStrobe(kSres);
  delay(1);
}