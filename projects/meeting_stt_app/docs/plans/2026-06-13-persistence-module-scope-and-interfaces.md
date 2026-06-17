# WAV, transcript, and session metadata persistence scope

## Baseline check requirement

Before implementation, grep the existing baseline:

```powershell
rg -n "class |def |Path\(|open\(|wave|transcript|session|metadata|\.wav|\.txt|\.md|\.json" app/io app scripts/synthetic_audio_headless_selftest.py
```

The implementation may proceed only when this check confirms the following:

- `app/io/recorder.py`, `app/io/transcript_writer.py`, and `app/io/session.py` are the single persistence boundary for WAV, transcript, and session metadata writes.
- No other module directly opens the final session `.wav`, `.txt`, `.md`, or session metadata `.json` outputs except through these modules.
- Any existing direct write path found in UI, STT, or selftest code is treated as a wiring gap and must be replaced by these interfaces in the implementation slice.

## Scope

This slice defines the persistence contract only. It fixes module ownership, API shape, write order, and acceptance checks so later implementation can be verified without UI or microphone dependencies.

In scope:

- `app/io/session.py`: create and name a session directory under an injected output root, expose canonical artifact paths, and write final session metadata.
- `app/io/recorder.py`: append PCM audio frames to one WAV file, support explicit `flush()`, and close the file exactly once.
- `app/io/transcript_writer.py`: append transcript segments to `.txt` and `.md`, then finalize both files.
- `scripts/synthetic_audio_headless_selftest.py`: run one headless persistence flow that creates a session, writes synthetic audio, appends transcript text, finalizes metadata, and validates artifacts.

Out of scope:

- Microphone capture, WASAPI loopback capture, and audio mixing behavior.
- STT model quality, segmentation strategy, diarization, translation, or UI display behavior.
- Cloud sync or database storage.
- Runtime cleanup or retention policy.

## Path hygiene contract

- No persistence module may hardcode an absolute path such as `C:\`, `/Users/`, `/home/`, or `/root/`.
- The output root is injected by caller configuration or function parameter.
- All session artifact paths are derived from the injected output root and generated session directory name.
- Directory names are sanitized to filesystem-safe ASCII characters.
- Persistence modules must not infer the project root from the current working directory for production output.

## `app/io/session.py` contract

### Responsibilities

- Own session directory creation.
- Own deterministic artifact path layout.
- Own session metadata schema and final metadata write.

### Proposed API

```python
@dataclass(frozen=True)
class SessionPaths:
    session_id: str
    session_dir: Path
    wav_path: Path
    txt_path: Path
    md_path: Path
    metadata_path: Path


def create_session(output_root: Path, started_at: datetime | None = None, title: str | None = None) -> SessionPaths:
    ...


def write_metadata(paths: SessionPaths, metadata: Mapping[str, Any]) -> None:
    ...
```

### Directory naming

Session directory name:

```text
YYYYMMDD-HHMMSS-{slug-or-session}
```

Example:

```text
20260613-143020-synthetic-selftest
```

If `title` is omitted, use `session`. If a directory already exists, append a short numeric suffix such as `-002`.

### Artifact layout

```text
{output_root}/
  {session_dir}/
    audio.wav
    transcript.txt
    transcript.md
    session.json
```

### Metadata schema

Required top-level fields:

- `schema_version`: integer, initially `1`.
- `session_id`: string matching `SessionPaths.session_id`.
- `started_at`: ISO-8601 string.
- `ended_at`: ISO-8601 string written at finalize time.
- `artifacts`: object containing relative artifact names: `audio.wav`, `transcript.txt`, `transcript.md`.
- `audio`: object with `sample_rate`, `channels`, `sample_width_bytes`, and `frames_written`.
- `transcript`: object with `segments_written`, `txt_bytes`, and `md_bytes`.
- `status`: string, `completed` for a successful finalize.

Optional fields:

- `title`
- `duration_seconds`
- `source`
- `warnings`

## `app/io/recorder.py` contract

### Responsibilities

- Own WAV file creation and incremental PCM frame writes.
- Keep frame count for metadata.
- Provide explicit `flush()` and idempotent `close()`.

### Proposed API

```python
class WavRecorder:
    def __init__(self, wav_path: Path, sample_rate: int, channels: int, sample_width_bytes: int) -> None:
        ...

    @property
    def frames_written(self) -> int:
        ...

    def write_frames(self, pcm_bytes: bytes) -> int:
        ...

    def flush(self) -> None:
        ...

    def close(self) -> None:
        ...
```

### Behavior

- `write_frames()` appends bytes to the WAV stream and returns the number of audio frames written.
- `flush()` flushes the underlying file handle without closing it.
- `close()` finalizes the WAV header and may be called multiple times safely.
- Calls to `write_frames()` after `close()` raise `ValueError`.
- PCM byte length must be divisible by `channels * sample_width_bytes`; invalid chunks raise `ValueError`.

## `app/io/transcript_writer.py` contract

### Responsibilities

- Own transcript text file append.
- Own Markdown transcript append.
- Keep segment count and byte sizes for metadata.
- Provide finalization boundary.

### Proposed API

```python
@dataclass(frozen=True)
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str


class TranscriptWriter:
    def __init__(self, txt_path: Path, md_path: Path, title: str | None = None) -> None:
        ...

    @property
    def segments_written(self) -> int:
        ...

    def append_segment(self, segment: TranscriptSegment) -> None:
        ...

    def flush(self) -> None:
        ...

    def finalize(self) -> None:
        ...
```

### Text format

`transcript.txt` appends one line per segment:

```text
[00:00.000 - 00:01.500] hello world
```

`transcript.md` writes an optional heading and a table:

```markdown
# {title}

| Start | End | Text |
| --- | --- | --- |
| 00:00.000 | 00:01.500 | hello world |
```

Markdown cell text must escape `|` characters.

## Fixed implementation order

1. Baseline grep and duplication check.
   - Verification: grep output confirms only `app/io` owns final persistence writes, or records the direct-write callers to rewire.
2. Implement `SessionPaths`, `create_session()`, and `write_metadata()` in `app/io/session.py`.
   - Verification: creating a session under a temporary injected root produces only relative child artifacts.
3. Implement `WavRecorder` in `app/io/recorder.py`.
   - Verification: writing synthetic PCM bytes creates a readable WAV with expected channels, sample rate, sample width, and frame count.
4. Implement `TranscriptSegment` and `TranscriptWriter` in `app/io/transcript_writer.py`.
   - Verification: appending one segment writes both `.txt` and `.md`, flushes, and finalizes without losing content.
5. Wire `scripts/synthetic_audio_headless_selftest.py` through the new APIs.
   - Verification: the selftest completes one full persistence flow without UI, microphone, or STT model dependency.
6. Run path hygiene and import checks.
   - Verification: no hardcoded absolute output path is introduced, and the modules compile.

## Headless selftest acceptance criteria

`scripts/synthetic_audio_headless_selftest.py` must verify one persistence flow:

- It accepts or derives an injected output root for test artifacts, such as `.selftest/synthetic_audio`.
- It creates one session directory through `app/io/session.py`.
- It writes a non-empty `audio.wav` through `WavRecorder`.
- It appends at least one transcript segment through `TranscriptWriter`.
- It writes `session.json` through `write_metadata()`.
- It validates that all four artifacts exist in the session directory.
- It validates the WAV header with Python `wave`: sample rate, channel count, sample width, and non-zero frame count.
- It validates `transcript.txt` contains the segment text.
- It validates `transcript.md` contains a Markdown table row for the segment.
- It validates `session.json` has `schema_version == 1`, `status == "completed"`, matching `session_id`, and artifact names for WAV, TXT, and MD.
- It fails non-zero if any validation fails.

Suggested command:

```powershell
python scripts/synthetic_audio_headless_selftest.py
```

## Dependencies and outputs

Dependencies:

- Python standard library: `dataclasses`, `datetime`, `json`, `pathlib`, `re`, `wave`.
- No UI, audio device, or STT model dependency for the persistence selftest.

Outputs:

- `audio.wav`
- `transcript.txt`
- `transcript.md`
- `session.json`
- selftest report JSON may remain separate from the session directory if the existing script already owns that report path.

## Design impact

The persistence boundary becomes explicit and testable. Capture, STT, UI, and selftest code depend on `app/io` contracts instead of writing session artifacts directly. This reduces duplicate file layout decisions and makes headless validation possible before full application wiring.

## Alternatives considered

- Single `SessionWriter` facade: rejected for this slice because it hides the individual contracts the current task asks to define.
- Writing metadata continuously during capture: deferred because the acceptance target only requires one completed headless flow.
- JSONL transcript storage: deferred because the requested durable user artifacts are `.txt` and `.md`.
