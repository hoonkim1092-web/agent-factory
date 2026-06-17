"""실행 가능한 PySide6 회의록 STT 데스크톱 앱 패키지.

마이크와 시스템오디오(WASAPI loopback)를 동시에 캡처·믹싱하면서
로컬 faster-whisper로 실시간 한국어 자막을 출력하고, 종료 시 원본 WAV·
전사 텍스트(.txt/.md)·세션 메타데이터(JSON)를 ``meetings/<session_id>/``에
자동 저장한다.

설계·인터페이스 계약은 ``docs/scope/2026-06-13-runnable-pyside6-stt-app-scope.md``로
고정되어 있다. 본 패키지의 모든 모듈은 그 계약의 시그니처를 변경하지 않는다.
"""

__app_name__ = "Meeting STT"
__version__ = "0.1.0"
