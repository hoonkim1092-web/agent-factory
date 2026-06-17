# Synthetic Audio Headless Selftest

## Design intent

Add a small headless QA script that can run without microphone, speaker, GUI, or external services. The script generates a deterministic synthetic audio fixture, validates the WAV container and signal properties, and writes a machine-readable report.

## Impact scope

- Adds `scripts/synthetic_audio_headless_selftest.py`.
- Adds documentation for the QA workflow in `docs/architecture.md`.
- Appends the change to `docs/change_history.md`.

## Alternatives considered

- Use an external audio synthesis package: rejected for the first slice because the Python standard library is enough for a deterministic WAV sanity check.
- Exercise the full STT pipeline: deferred because this slice is for a headless audio fixture and signal validation only.
- Play audio through the OS device: rejected because CI and remote environments may not expose an audio device.

## Verification

Run:

```powershell
python scripts/synthetic_audio_headless_selftest.py
```

Expected result: exit code `0`, a generated WAV file, and a JSON report under `.selftest/synthetic_audio/`.
