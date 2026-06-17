"""오디오 장치 열거(M11).

pyaudiowpatch(WASAPI)를 통해 마이크 입력 장치와 시스템오디오 loopback
장치를 각각 열거한다. pyaudiowpatch가 없거나 장치가 0개인 환경에서도
**예외 없이 빈 리스트**를 반환한다(헤드리스 기동 보장).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Device:
    """오디오 장치 식별 정보.

    Attributes:
        index: PyAudio 장치 인덱스.
        name: 사람이 읽는 장치 이름.
    """

    index: int
    name: str


def detect_compute_device() -> tuple[str, str]:
    """faster-whisper용 (device, compute_type)를 감지한다.

    ctranslate2가 CUDA 장치를 보고하면 ``("cuda", "float16")``, 그 외에는
    ``("cpu", "int8")``을 반환한다. ctranslate2 미설치·CUDA 미가용 등 어떤
    실패에서도 예외 없이 CPU 기본값으로 안전 종료한다(헤드리스 기동 보장).

    전사 코어(``app/stt/transcriber.py``)가 모델 로드 시 이 함수를 호출한다 —
    compute device 감지 로직의 단일 출처(SSOT)다.
    """
    try:
        import ctranslate2

        try:
            cuda_count = ctranslate2.get_cuda_device_count()
        except Exception:
            cuda_count = 0
        if cuda_count and cuda_count > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def enumerate_devices() -> tuple[list[Device], list[Device]]:
    """(마이크 목록, loopback 목록)을 반환한다.

    pyaudiowpatch 미설치·장치 0개·WASAPI 미지원 환경에서는 빈 리스트를
    반환하며 예외를 던지지 않는다.
    """
    try:
        import pyaudiowpatch as pyaudio
    except Exception:
        # pyaudiowpatch 미설치(비-Windows 또는 헤드리스) — 빈 목록으로 안전 종료
        return [], []

    mics: list[Device] = []
    loopbacks: list[Device] = []
    pa = None
    try:
        pa = pyaudio.PyAudio()
        try:
            wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        except Exception:
            return [], []
        host_api_index = wasapi_info["index"]

        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
            except Exception:
                continue
            if info.get("hostApi") != host_api_index:
                continue
            name = str(info.get("name", f"device {i}"))
            max_in = int(info.get("maxInputChannels", 0) or 0)
            is_loopback = bool(info.get("isLoopbackDevice", False))
            if is_loopback:
                loopbacks.append(Device(index=i, name=name))
            elif max_in > 0:
                mics.append(Device(index=i, name=name))
    except Exception:
        # 어떤 단계에서 실패해도 빈/부분 목록으로 안전 종료
        return mics, loopbacks
    finally:
        if pa is not None:
            try:
                pa.terminate()
            except Exception:
                pass
    return mics, loopbacks
