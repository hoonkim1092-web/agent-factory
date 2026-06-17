"""헤드리스 파이프라인 셀프테스트(M10, S8).

오디오 장치·PySide6·faster-whisper가 없는 환경에서도 실행되도록 설계되었다.
가짜(fake) 전사기를 주입해 캡처→믹싱→펌프→전사워커→자막/저장의 배선이
end-to-end로 단선 없이 이어지는지 검증한다.

검증 항목:
- S0: 전 모듈 import 성공(헤드리스).
- S1: ``resolve_save_root``가 절대경로 리터럴 없이 동작.
- S3: 믹서가 합성 프레임을 16kHz mono 청크로 반환.
- S7/S8: 컨트롤러 start→push→stop 흐름이 WAV/txt/md/session.json을
  ``meetings/<session_id>/``에 생성하고, 주입한 전사 결과가 transcript에 반영.

실제 faster-whisper 전사(S2)는 모델 다운로드/무거운 연산이 필요하므로
환경변수 ``MEETING_STT_RUN_WHISPER=1``일 때만 추가로 시도한다.

실행: ``python -m tests.selftest_pipeline`` (프로젝트 루트에서)
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

# 프로젝트 루트를 import 경로에 추가(직접 실행 대비)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import TARGET_SAMPLE_RATE, AppSettings, resolve_save_root  # noqa: E402
from app.io.session import RecordingSession  # noqa: E402
from app.stt.types import TranscriptChunk  # noqa: E402


class FakeTranscriber:
    """faster-whisper 없이 배선을 검증하기 위한 가짜 전사기."""

    def __init__(self) -> None:
        self._i = 0

    def transcribe_chunk(self, audio: np.ndarray) -> list[TranscriptChunk]:
        dur = len(audio) / float(TARGET_SAMPLE_RATE)
        chunk = TranscriptChunk(
            chunk_index=self._i,
            start_ts=float(self._i) * dur,
            end_ts=float(self._i + 1) * dur,
            text=f"테스트 자막 {self._i} ({dur:.2f}초)",
            language="ko",
            no_speech_prob=0.0,
        )
        self._i += 1
        return [chunk]


def _sine(seconds: float, freq: float = 220.0, amp: float = 0.3) -> np.ndarray:
    n = int(seconds * TARGET_SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / TARGET_SAMPLE_RATE
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _check(name: str, cond: bool) -> bool:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return cond


def test_imports() -> bool:
    """S0 — 전 모듈 import 성공(헤드리스)."""
    import app.audio.capture  # noqa: F401
    import app.audio.devices  # noqa: F401
    import app.audio.mixer  # noqa: F401
    import app.io.recorder  # noqa: F401
    import app.io.transcript_writer  # noqa: F401
    import app.main  # noqa: F401
    import app.stt.transcriber  # noqa: F401
    import app.stt.worker  # noqa: F401
    import app.ui.main_window  # noqa: F401
    import app.ui.widgets  # noqa: F401

    return _check("S0 전 모듈 import 성공", True)


def test_resolve_save_root() -> bool:
    """S1 — resolve_save_root 절대경로 리터럴 없음·예외 없음."""
    settings = AppSettings()
    root = resolve_save_root(settings)
    return _check("S1 resolve_save_root 동작", root is not None and root.name == "meetings")


def test_mixer_chunk() -> bool:
    """S3 — 믹서가 합성 프레임을 16kHz mono 청크로 반환."""
    from app.audio.mixer import AudioMixer

    mixer = AudioMixer(max_chunk_sec=1.0, use_vad=False)
    frames = _sine(1.5)
    mixer.push_mic(frames)
    mixer.push_loopback(frames)
    chunk = mixer.read_chunk()
    ok = (
        chunk is not None
        and chunk.ndim == 1
        and chunk.dtype == np.float32
        and chunk.size == TARGET_SAMPLE_RATE  # max_chunk_sec=1.0 → 16000 샘플
    )
    return _check("S3 믹서 16kHz mono 청크 반환", ok)


def test_pipeline_e2e() -> bool:
    """S7/S8 — 컨트롤러 start→push→stop이 산출물을 생성하고 전사 반영."""
    from app.main import STATE_SAVED, PipelineController

    with tempfile.TemporaryDirectory() as tmp:
        settings = AppSettings(
            save_root=tmp,
            max_chunk_sec=1.0,
            use_vad=False,
            mic_device_index=None,
            loopback_device_index=None,
        )
        controller = PipelineController(settings)

        received: list[TranscriptChunk] = []
        controller.chunk_ready.connect(received.append)

        controller.start(transcriber=FakeTranscriber())
        if controller.state != "RECORDING":
            return _check("S7 컨트롤러 RECORDING 진입", False)

        # 합성 오디오 3초를 두 스트림에 주입 → 펌프가 청크로 분배
        audio = _sine(3.0)
        controller.mixer.push_mic(audio)
        controller.mixer.push_loopback(audio)
        time.sleep(0.4)  # 펌프가 청크를 소진할 시간

        session = controller.stop()

        if not _check("S7 stop()이 RecordingSession 반환", isinstance(session, RecordingSession)):
            return False
        if not _check("S7 상태 SAVED 전이", controller.state == STATE_SAVED):
            return False

        session_dir = Path(tmp) / session.session_id
        wav = session_dir / "recording.wav"
        txt = session_dir / "transcript.txt"
        md = session_dir / "transcript.md"
        meta = session_dir / "session.json"

        files_ok = wav.exists() and txt.exists() and md.exists() and meta.exists()
        if not _check("S8 산출물(WAV/txt/md/json) 생성", files_ok):
            return False

        wav_ok = wav.stat().st_size > 44  # WAV 헤더(44B) 이상
        txt_ok = txt.read_text(encoding="utf-8").strip() != ""
        chunks_ok = len(received) >= 1
        return _check(
            "S8 전사 결과가 transcript/시그널에 반영",
            wav_ok and txt_ok and chunks_ok,
        )


def test_real_whisper_optional() -> bool:
    """S2(선택) — 실제 faster-whisper 1회 전사. 환경변수로만 활성화."""
    if os.environ.get("MEETING_STT_RUN_WHISPER") != "1":
        print("[SKIP] S2 실제 faster-whisper 전사 (MEETING_STT_RUN_WHISPER!=1)")
        return True
    try:
        from app.stt.transcriber import Transcriber
    except Exception as exc:
        return _check(f"S2 Transcriber import ({exc})", False)
    tr = Transcriber(model_size="tiny", language="ko")
    chunks = tr.transcribe_chunk(_sine(2.0))
    return _check("S2 transcribe_chunk 호출 성공(>=0 청크)", isinstance(chunks, list))


def main() -> int:
    print("=== Meeting STT 헤드리스 셀프테스트 ===")
    results = [
        test_imports(),
        test_resolve_save_root(),
        test_mixer_chunk(),
        test_pipeline_e2e(),
        test_real_whisper_optional(),
    ]
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"--- 결과: {passed}/{total} 통과 ---")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
