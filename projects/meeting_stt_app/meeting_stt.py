"""배포 엔트리포인트 — ``app`` 패키지로 기동해 상대 import를 보존한다.

PyInstaller가 ``app/main.py``를 직접 진입점으로 분석하면, 런타임에 그 파일이
``__main__``으로 실행되어 ``from .audio ... import`` 상대 import가
"attempted relative import with no known parent package"로 깨진다. 이 루트
런처는 ``app``을 정상 패키지 import 경로로 들여오므로, 소스 실행과 frozen
빌드 양쪽에서 동일하게 동작한다.

소스 실행:  python meeting_stt.py
frozen:     dist/MeetingSTT/MeetingSTT.exe (meeting_stt.spec 진입점)
"""
import sys


def _check_devices() -> int:
    """``--check-devices`` 진단 — 오디오 장치 열거 결과를 출력하고 종료한다.

    frozen 빌드에서 ``_portaudiowpatch``/``ctranslate2`` 네이티브가 제대로
    번들됐는지(= 장치가 보이는지)를 GUI 없이 확인하는 용도. 장치 문제가
    보고될 때 1차 진단으로 쓴다.
    """
    from app.audio.devices import detect_compute_device, enumerate_devices

    device, compute = detect_compute_device()
    mics, loopbacks = enumerate_devices()
    print(f"compute device: {device} / {compute}")
    print(f"마이크 {len(mics)}개:")
    for d in mics:
        print(f"   [{d.index}] {d.name}")
    print(f"시스템오디오(loopback) {len(loopbacks)}개:")
    for d in loopbacks:
        print(f"   [{d.index}] {d.name}")
    return 0


def main() -> int:
    if "--check-devices" in sys.argv[1:]:
        return _check_devices()
    from app.main import main as app_main

    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())
