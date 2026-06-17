"""Headless synthetic audio selftest.

This script does not use microphone, speaker, GUI, network, or STT services.
It creates a deterministic PCM WAV fixture and validates basic signal health.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_DURATION_SECONDS = 1.0
DEFAULT_FREQUENCY_HZ = 440.0
DEFAULT_AMPLITUDE = 0.45
DEFAULT_OUTPUT_DIR = Path(".selftest") / "synthetic_audio"


@dataclass(frozen=True)
class AudioSpec:
    sample_rate: int
    duration_seconds: float
    frequency_hz: float
    amplitude: float


@dataclass(frozen=True)
class ValidationResult:
    name: str
    passed: bool
    details: str


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and validate a deterministic synthetic WAV fixture."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION_SECONDS)
    parser.add_argument("--frequency", type=float, default=DEFAULT_FREQUENCY_HZ)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    return parser.parse_args(list(argv))


def validate_spec(spec: AudioSpec) -> list[ValidationResult]:
    checks = [
        ValidationResult(
            "sample_rate",
            spec.sample_rate > 0,
            f"sample_rate={spec.sample_rate}",
        ),
        ValidationResult(
            "duration",
            spec.duration_seconds > 0,
            f"duration_seconds={spec.duration_seconds}",
        ),
        ValidationResult(
            "frequency",
            0 < spec.frequency_hz < spec.sample_rate / 2,
            f"frequency_hz={spec.frequency_hz}, nyquist={spec.sample_rate / 2}",
        ),
        ValidationResult(
            "amplitude",
            0 < spec.amplitude <= 1,
            f"amplitude={spec.amplitude}",
        ),
    ]
    return checks


def synthesize_samples(spec: AudioSpec) -> list[int]:
    sample_count = round(spec.sample_rate * spec.duration_seconds)
    peak = int(32767 * spec.amplitude)
    return [
        int(peak * math.sin(2 * math.pi * spec.frequency_hz * index / spec.sample_rate))
        for index in range(sample_count)
    ]


def write_wav(path: Path, spec: AudioSpec, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"".join(struct.pack("<h", sample) for sample in samples)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(spec.sample_rate)
        wav_file.writeframes(frames)


def read_wav_samples(path: Path) -> tuple[wave._wave_params, list[int]]:
    with wave.open(str(path), "rb") as wav_file:
        params = wav_file.getparams()
        frames = wav_file.readframes(params.nframes)
    samples = [
        value[0]
        for value in struct.iter_unpack("<h", frames)
    ]
    return params, samples


def rms(samples: list[int]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def estimate_frequency(samples: list[int], sample_rate: int) -> float:
    if len(samples) < 2:
        return 0.0
    crossings = 0
    previous = samples[0]
    for current in samples[1:]:
        if previous <= 0 < current:
            crossings += 1
        previous = current
    duration_seconds = len(samples) / sample_rate
    if duration_seconds <= 0:
        return 0.0
    return crossings / duration_seconds


def validate_wav(path: Path, spec: AudioSpec) -> tuple[list[ValidationResult], dict[str, object]]:
    params, samples = read_wav_samples(path)
    measured_duration = params.nframes / params.framerate if params.framerate else 0.0
    measured_rms = rms(samples)
    measured_frequency = estimate_frequency(samples, params.framerate)
    expected_rms = 32767 * spec.amplitude / math.sqrt(2)

    metadata = {
        "path": str(path),
        "channels": params.nchannels,
        "sample_width_bytes": params.sampwidth,
        "sample_rate": params.framerate,
        "frame_count": params.nframes,
        "duration_seconds": measured_duration,
        "rms": measured_rms,
        "estimated_frequency_hz": measured_frequency,
    }

    checks = [
        ValidationResult("file_exists", path.exists(), f"path={path}"),
        ValidationResult("channels", params.nchannels == 1, f"channels={params.nchannels}"),
        ValidationResult("sample_width", params.sampwidth == 2, f"sample_width={params.sampwidth}"),
        ValidationResult(
            "sample_rate",
            params.framerate == spec.sample_rate,
            f"sample_rate={params.framerate}, expected={spec.sample_rate}",
        ),
        ValidationResult(
            "duration",
            abs(measured_duration - spec.duration_seconds) <= 1 / spec.sample_rate,
            f"duration={measured_duration:.6f}, expected={spec.duration_seconds:.6f}",
        ),
        ValidationResult(
            "rms",
            expected_rms * 0.95 <= measured_rms <= expected_rms * 1.05,
            f"rms={measured_rms:.2f}, expected={expected_rms:.2f}",
        ),
        ValidationResult(
            "frequency",
            abs(measured_frequency - spec.frequency_hz) <= 2.0,
            f"estimated={measured_frequency:.2f}, expected={spec.frequency_hz:.2f}",
        ),
    ]
    return checks, metadata


def write_report(path: Path, spec: AudioSpec, metadata: dict[str, object], checks: list[ValidationResult]) -> None:
    report = {
        "ok": all(check.passed for check in checks),
        "spec": asdict(spec),
        "metadata": metadata,
        "checks": [asdict(check) for check in checks],
    }
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    spec = AudioSpec(
        sample_rate=args.sample_rate,
        duration_seconds=args.duration,
        frequency_hz=args.frequency,
        amplitude=args.amplitude,
    )

    spec_checks = validate_spec(spec)
    if not all(check.passed for check in spec_checks):
        for check in spec_checks:
            if not check.passed:
                print(f"FAIL {check.name}: {check.details}", file=sys.stderr)
        return 2

    output_dir = args.output_dir
    wav_path = output_dir / "synthetic_selftest.wav"
    report_path = output_dir / "synthetic_selftest_report.json"

    samples = synthesize_samples(spec)
    write_wav(wav_path, spec, samples)
    wav_checks, metadata = validate_wav(wav_path, spec)
    checks = spec_checks + wav_checks
    write_report(report_path, spec, metadata, checks)

    if all(check.passed for check in checks):
        print(f"PASS synthetic audio selftest: {report_path}")
        return 0

    for check in checks:
        if not check.passed:
            print(f"FAIL {check.name}: {check.details}", file=sys.stderr)
    print(f"Report written: {report_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
