#!/usr/bin/env python3
"""Stream microphone audio as unsigned 8-bit mono samples to SerialAudio."""

import argparse
import time

import numpy as np
import serial
import sounddevice as sd


def parse_device(value):
    try:
        return int(value)
    except ValueError:
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Serial port, e.g. /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=500000)
    parser.add_argument("--rate", type=int, default=8000, help="Mono sample rate in Hz")
    parser.add_argument("--blocksize", type=int, default=1024)
    parser.add_argument("--device", type=parse_device, help="Input device name or index")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    if not args.port:
        parser.error("--port is required unless --list-devices is used")

    with serial.Serial(args.port, args.baud, timeout=1) as connection:
        time.sleep(2)  # Allow boards that reset when the serial port opens.
        print(f"Streaming {args.rate} Hz audio to {args.port}; press Ctrl+C to stop.")
        try:
            with sd.InputStream(
                samplerate=args.rate,
                blocksize=args.blocksize,
                device=args.device,
                channels=1,
                dtype="int16",
            ) as microphone:
                while True:
                    samples, _ = microphone.read(args.blocksize)
                    unsigned_samples = np.clip(
                        (samples[:, 0].astype(np.int32) >> 8) + 128, 0, 255
                    ).astype(np.uint8)
                    connection.write(unsigned_samples.tobytes())
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()