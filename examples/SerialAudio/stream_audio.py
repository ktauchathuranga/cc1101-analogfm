#!/usr/bin/env python3
"""Stream microphone audio as unsigned 8-bit mono samples to SerialAudio."""

import argparse
import os
import subprocess
import tempfile
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


def write_samples_realtime(connection, samples, rate):
    next_sample_time = time.perf_counter()
    sample_period = 1.0 / rate
    for sample in samples:
        connection.write(bytes((int(sample),)))
        next_sample_time += sample_period
        wait_time = next_sample_time - time.perf_counter()
        if wait_time > 0:
            time.sleep(wait_time)


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
            write_samples_realtime(connection, to_unsigned_samples(samples[:, 0]), args.rate)


def convert_to_raw(input_file, output_file, rate):
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        input_file,
        "-f",
        "u8",
        "-ac",
        "1",
        "-ar",
        str(rate),
        output_file,
    ]
    subprocess.run(command, check=True)


def stream_raw_file(connection, filename, rate, blocksize):
    with open(filename, "rb") as raw_file:
        while True:
            samples = raw_file.read(blocksize)
            if not samples:
                break
            write_samples_realtime(connection, samples, rate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Serial port, e.g. /dev/ttyUSB0")
    parser.add_argument("--file", help="Audio file to stream, decoded by ffmpeg")
    parser.add_argument(
        "--raw-output",
        help="Convert --file to unsigned 8-bit raw audio here before streaming",
    )
    parser.add_argument(
        "--raw-file",
        help="Stream an existing unsigned 8-bit raw audio file",
    )
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
    if args.raw_file and args.file:
        parser.error("--file and --raw-file cannot be used together")
    if args.raw_output and not args.file:
        parser.error("--raw-output requires --file")

    with serial.Serial(args.port, args.baud, timeout=1) as connection:
        time.sleep(2)  # Allow boards that reset when the serial port opens.
        temporary_raw = None
        try:
            if args.file:
                raw_file = args.raw_output
                if not raw_file:
                    temporary = tempfile.NamedTemporaryFile(suffix=".raw", delete=False)
                    raw_file = temporary.name
                    temporary.close()
                    temporary_raw = raw_file
                print(f"Converting {args.file} to suitable raw audio...")
                convert_to_raw(args.file, raw_file, args.rate)
                print(f"Streaming converted audio at {args.rate} Hz to {args.port}; press Ctrl+C to stop.")
                stream_raw_file(connection, raw_file, args.rate, args.blocksize)
            elif args.raw_file:
                print(f"Streaming raw audio at {args.rate} Hz to {args.port}; press Ctrl+C to stop.")
                stream_raw_file(
                    connection,
                    args.raw_file,
                    args.rate,
                    args.blocksize,
                )
            else:
                print(f"Streaming microphone audio at {args.rate} Hz to {args.port}; press Ctrl+C to stop.")
                stream_microphone(connection, args)
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            if temporary_raw:
                os.unlink(temporary_raw)


if __name__ == "__main__":
    main()