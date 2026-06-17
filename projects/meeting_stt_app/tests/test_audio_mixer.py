"""오디오 엔진(M2) 믹서 회귀 테스트.

audio-engine work-item의 build 슬라이스 B1(as-built 회귀)·B2(믹싱 결함 재현)·
B3(수정 검증)을 고정한다. feature-spec.md §7 인수 기준(A3~A7)을 헤드리스에서
검증한다. 오디오 장치·PySide6·faster-whisper 없이 numpy + qt_compat 스텁만으로
실행된다.

핵심 게이트는 A4(믹싱 정합) — 별도 스레드가 ``push_mic``/``push_loopback``을
번갈아 호출하는 정상 패턴에서, 믹서가 두 스트림을 연결(concatenate)하지 않고
시간 정렬 평균 믹싱하는지 단언한다(결함 핸드오프
``docs/plans/2026-06-13-backend-build-handoff-and-mixer-finding.md`` §2).

실행: ``python -m tests.test_audio_mixer`` 또는 ``pytest tests/test_audio_mixer.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 프로젝트 루트를 import 경로에 추가(직접 실행 대비)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.audio.mixer import (  # noqa: E402
    AudioMixer,
    resample_to_16k,
    rms,
    to_mono_float32,
)
from app.config import TARGET_SAMPLE_RATE  # noqa: E402


def _block(sec: float, value: float) -> np.ndarray:
    """``sec``초 길이의 상수 16kHz mono float32 블록."""
    return np.full(int(sec * TARGET_SAMPLE_RATE), value, dtype=np.float32)


def _sine(sec: float, freq: float, amp: float = 0.3) -> np.ndarray:
    """``sec``초 길이의 16kHz mono float32 사인파(헤드리스 합성 신호)."""
    n = int(sec * TARGET_SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / TARGET_SAMPLE_RATE
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# ── A3: 정규화 헬퍼 정합 ──────────────────────────────────────────────────
def test_to_mono_float32_int16_정규화() -> None:
    """int16 PCM이 [-1,1] float32 mono로 정규화된다."""
    pcm = np.array([0, 16384, -16384, 32767], dtype=np.int16)
    out = to_mono_float32(pcm, channels=1)
    assert out.dtype == np.float32
    assert out.ndim == 1
    assert -1.0 <= out.min() and out.max() <= 1.0
    assert abs(out[1] - 0.5) < 1e-3


def test_to_mono_float32_다채널_평균() -> None:
    """다채널 입력이 채널 평균으로 mono화된다."""
    # 2채널 인터리브: L=1.0, R=0.0 → 평균 0.5
    stereo = np.array([1.0, 0.0, 1.0, 0.0], dtype=np.float32)
    out = to_mono_float32(stereo, channels=2)
    assert out.shape == (2,)
    assert np.allclose(out, 0.5)


def test_resample_to_16k_shape_rate() -> None:
    """48kHz → 16kHz 리샘플 시 길이가 1/3로 줄고 dtype/범위가 유지된다."""
    src = _block(1.0, 0.3)  # 길이는 16000이지만 src_rate 48000으로 간주
    out = resample_to_16k(src, src_rate=48000)
    assert out.dtype == np.float32
    assert abs(out.size - src.size * TARGET_SAMPLE_RATE / 48000) <= 1
    # 16kHz 입력은 그대로 통과
    same = resample_to_16k(src, src_rate=TARGET_SAMPLE_RATE)
    assert same.size == src.size


def test_rms_값() -> None:
    """RMS가 진폭에 비례한다(상수 0.5 → 0.5)."""
    assert abs(rms(_block(0.1, 0.5)) - 0.5) < 1e-4
    assert rms(np.zeros(0, dtype=np.float32)) == 0.0


# ── A4: 믹싱 정합 (결함 회귀 — 임계 게이트) ───────────────────────────────
#
# 결함 신호는 "연결(concatenate)"로 인한 **타임라인 2배(길이)** 이다(handoff §2).
# 믹싱 의미는 feature-spec §1대로 **평균 믹싱** ``(mic+loop)*0.5`` 이므로,
# 서로 다른 값(mic≠loop)으로 push해 길이 + 결합값을 함께 단언한다:
#   - 정상(평균 믹싱):  길이 N, 값 (mic+loop)/2
#   - 결함(연결):       길이 2N
#   - 한쪽 누락:        길이 N, 값이 한쪽 값과 동일
MIC_VAL = 0.6
LOOP_VAL = 0.2
MIX_VAL = (MIC_VAL + LOOP_VAL) * 0.5  # 0.4 — 두 스트림이 실제 결합됐을 때의 값


def test_믹싱_번갈아_push_정렬() -> None:
    """별도 스레드 번갈아 push 패턴에서 두 스트림이 정렬 평균 믹싱된다.

    결함(연결)이면 길이 2N, 정상(평균 믹싱)이면 길이 N·값 0.4.
    """
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=2)
    # 1024 샘플 단위로 mic→loop 번갈아 push (실제 캡처 스레드 교차 패턴 모사)
    step = 1024
    n_steps = (3 * TARGET_SAMPLE_RATE) // step  # ~3초 분량
    for _ in range(n_steps):
        mixer.push_mic(np.full(step, MIC_VAL, dtype=np.float32))
        mixer.push_loopback(np.full(step, LOOP_VAL, dtype=np.float32))
    out = mixer.flush()
    assert out is not None
    # 출력 총 길이 == 입력 길이(연결 아님)
    assert out.size == n_steps * step, f"기대 {n_steps * step}, 실제 {out.size}"
    # 두 스트림이 실제 평균 결합됨((0.6+0.2)/2=0.4)
    assert abs(float(out.mean()) - MIX_VAL) < 1e-3, f"mean={out.mean()} (믹싱이면 {MIX_VAL})"


def test_믹싱_bulk_push_정렬() -> None:
    """한쪽을 통째로 push한 뒤 상대를 push해도 정렬 믹싱된다(핸드오프 §2 재현)."""
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=2)
    mixer.push_mic(_block(3.0, MIC_VAL))
    mixer.push_loopback(_block(3.0, LOOP_VAL))
    out = mixer.flush()
    assert out is not None
    assert out.size == int(3.0 * TARGET_SAMPLE_RATE)  # 결함이면 96000
    assert abs(float(out.mean()) - MIX_VAL) < 1e-3


def test_믹싱_부분_겹침() -> None:
    """겹치는 구간만 평균 믹싱되고, 한쪽 잔여는 단독으로 보존되어 flush된다."""
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=2)
    mixer.push_mic(_block(1.0, MIC_VAL))        # mic 1.0s
    mixer.push_loopback(_block(0.4, LOOP_VAL))  # loop 0.4s (겹침 0.4s, mic 0.6s 잔여)
    out = mixer.flush()
    assert out is not None
    # 총 길이 = mic 길이(1.0s) — loop는 겹침 구간에서 소진
    assert out.size == int(1.0 * TARGET_SAMPLE_RATE)
    overlap = int(0.4 * TARGET_SAMPLE_RATE)
    # 겹침 구간은 평균 믹싱(0.4), 잔여는 단독(0.6)
    assert abs(float(out[:overlap].mean()) - MIX_VAL) < 1e-3
    assert abs(float(out[overlap:].mean()) - MIC_VAL) < 1e-3


def test_합성_사인파_이중스트림_헤드리스() -> None:
    """장치 없이 합성 사인파 두 개를 믹싱해 16kHz mono 청크가 나오는지 검증.

    마이크(440Hz)·loopback(880Hz) 사인파를 번갈아 push → read_chunk가
    16kHz mono float32 청크를 반환하고, 믹싱 결과 진폭이 두 단독 신호의
    평균 수준(개별 진폭보다 작음)임을 확인한다.
    """
    mixer = AudioMixer(max_chunk_sec=1.0, use_vad=False, active_sources=2)
    step = 1024
    n_steps = (2 * TARGET_SAMPLE_RATE) // step
    mic = _sine(2.0, freq=440.0, amp=0.3)
    loop = _sine(2.0, freq=880.0, amp=0.3)
    for i in range(n_steps):
        s, e = i * step, (i + 1) * step
        mixer.push_mic(mic[s:e])
        mixer.push_loopback(loop[s:e])
    chunk = mixer.read_chunk()
    assert chunk is not None
    assert chunk.ndim == 1 and chunk.dtype == np.float32
    assert chunk.size == TARGET_SAMPLE_RATE  # max_chunk_sec=1.0 상한
    # 다른 주파수 사인파 평균 믹싱 → RMS는 단독 RMS(~0.212)보다 작거나 같다
    assert 0.0 < rms(chunk) <= 0.3


# ── A5: 청크 경계 ────────────────────────────────────────────────────────
def test_max_chunk_sec_컷() -> None:
    """max_chunk_sec 도달 시 read_chunk가 상한 길이 청크를 컷한다."""
    mixer = AudioMixer(max_chunk_sec=1.0, use_vad=False, active_sources=2)
    mixer.push_mic(_block(1.5, 0.3))
    mixer.push_loopback(_block(1.5, 0.3))
    chunk = mixer.read_chunk()
    assert chunk is not None
    assert chunk.size == TARGET_SAMPLE_RATE  # 1.0s 상한


def test_vad_무음_tail_컷() -> None:
    """VAD 활성 시 말미 무음 구간에서 조기 컷된다."""
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=True, active_sources=1)
    # 1.0s 유성 + 0.5s 무음 → tail(0.4s) 무음 검출로 컷
    voiced = _block(1.0, 0.3)
    silence = _block(0.5, 0.0)
    mixer.push_mic(np.concatenate([voiced, silence]))
    chunk = mixer.read_chunk()
    assert chunk is not None
    assert chunk.size >= int(1.0 * TARGET_SAMPLE_RATE)


def test_flush_잔여_반환() -> None:
    """flush가 청크 경계 미달 잔여를 마지막 청크로 반환한다."""
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=1)
    mixer.push_mic(_block(0.5, 0.3))
    assert mixer.read_chunk() is None  # 상한 미달
    out = mixer.flush()
    assert out is not None
    assert out.size == int(0.5 * TARGET_SAMPLE_RATE)
    assert mixer.flush() is None  # 두 번째 flush는 비어있음


# ── A6: 단일 소스 graceful ───────────────────────────────────────────────
def test_단일_소스_마이크_단독() -> None:
    """active_sources=1(마이크 단독)에서 마이크 스트림이 그대로 발행된다."""
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=1)
    mixer.push_mic(_block(2.0, 0.4))
    out = mixer.flush()
    assert out is not None
    assert out.size == int(2.0 * TARGET_SAMPLE_RATE)
    assert abs(float(out.mean()) - 0.4) < 1e-3  # 단독이므로 합산 없음


def test_단일_소스_loopback_단독() -> None:
    """active_sources=1(loopback 단독)에서 loopback 스트림이 그대로 발행된다."""
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=1)
    mixer.push_loopback(_block(2.0, 0.4))
    out = mixer.flush()
    assert out is not None
    assert out.size == int(2.0 * TARGET_SAMPLE_RATE)


def test_2소스_파트너_영구부재_holdoff_통과() -> None:
    """2-소스 세션에서 한쪽이 영구 부재(장치 실패)면 holdoff 후 단독 통과한다.

    holdoff 임계를 내부적으로 0으로 낮춰 즉시 통과 동작을 결정적으로 검증한다
    (실제 기본값은 벽시계 ``MIXER_HOLDOFF_SEC``이며 정상 번갈아 push는 건드리지 않음).
    """
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=2)
    mixer._holdoff_sec = 0.0  # 파트너 부재를 즉시 단독 통과로 판정(테스트 결정성)
    mixer.push_mic(_block(1.0, 0.3))  # loop는 끝내 도착하지 않음
    out = mixer.flush()
    assert out is not None
    assert out.size == int(1.0 * TARGET_SAMPLE_RATE)


# ── A7: 캡처 생명주기 ────────────────────────────────────────────────────
def test_capture_device_none_무동작() -> None:
    """device_index=None이면 start/stop이 예외 없이 무동작한다."""
    from app.audio.capture import CaptureThread

    received: list = []
    cap = CaptureThread(None, received.append, loopback=False)
    cap.start()
    cap.stop()
    assert received == []


def test_level_changed_시그널() -> None:
    """push 시 level_changed 시그널이 RMS 값으로 발화한다."""
    mixer = AudioMixer(max_chunk_sec=30.0, use_vad=False, active_sources=1)
    levels: list = []
    mixer.level_changed.connect(levels.append)
    mixer.push_mic(_block(0.2, 0.5))
    assert len(levels) >= 1
    assert abs(levels[-1] - 0.5) < 1e-3


# ── 직접 실행 진입점 ─────────────────────────────────────────────────────
def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"[FAIL] {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[ERROR] {fn.__name__}: {exc!r}")
    print(f"--- 결과: {len(tests) - failed}/{len(tests)} 통과 ---")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_run_all())
