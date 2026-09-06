#!/usr/bin/env python3
"""Stream microphone audio as unsigned 8-bit mono samples to SerialAudio."""

import argparse
import subprocess
import time

import numpy as np
import serial


def parse_device(value):
    try:
        return int(value)
    except ValueError:
        return value


def to_unsigned_samples(samples):
    return np.clip((samples.astype(np.int32) >> 8) + 128, 0, 255).astype(np.uint8)


def stream_microphone(connection, args):
    import sounddevice as sd

    with sd.InputStream(
        samplerate=args.rate,
        blocksize=args.blocksize,
        device=args.device,
        channels=1,
        dtype="int16",
    ) as microphone:
        while True:
            samples, _ = microphone.read(args.blocksize)
            connection.write(to_unsigned_samples(samples[:, 0]).tobytes())


def stream_file(connection, args):
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        args.file,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(args.rate),
        "-",
    ]
    decoder = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        while True:
            raw_samples = decoder.stdout.read(args.blocksize * 2)
            if not raw_samples:
                break
            samples = np.frombuffer(raw_samples, dtype="<i2")
            connection.write(to_unsigned_samples(samples).tobytes())
    finally:
        decoder.stdout.close()
        result = decoder.wait()
        if result != 0:
            raise RuntimeError("ffmpeg could not decode the audio file")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Serial port, e.g. /dev/ttyUSB0")
    parser.add_argument("--file", help="Audio file to stream, decoded by ffmpeg")
    parser.add_argument("--baud", type=int, default=500000)
    parser.add_argument("--rate", type=int, default=8000, help="Mono sample rate in Hz")
    parser.add_argument("--blocksize", type=int, default=1024)
    parser.add_argument("--device", type=parse_device, help="Input device name or index")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return

    if not args.port:
        parser.error("--port is required unless --list-devices is used")

    with serial.Serial(args.port, args.baud, timeout=1) as connection:
        time.sleep(2)  # Allow boards that reset when the serial port opens.
        source = args.file or "microphone"
        print(f"Streaming {source} at {args.rate} Hz to {args.port}; press Ctrl+C to stop.")
        try:
            if args.file:
                stream_file(connection, args)
            else:
                stream_microphone(connection, args)
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()