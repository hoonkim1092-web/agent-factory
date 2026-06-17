# Change History

## 2026-06-13

- Added a synthetic audio headless selftest workflow.
- Added `scripts/synthetic_audio_headless_selftest.py` to generate a deterministic WAV fixture, validate signal properties, and write a JSON report.

### Backend build (backend_dev_module_10_build_2)

- `app/audio/devices.py`에 `detect_compute_device() -> tuple[str, str]`를 추가했다(CUDA 감지 시 `("cuda","float16")`, 아니면 `("cpu","int8")`). compute device 감지 로직의 단일 출처(SSOT)이며, `app/stt/transcriber.py`가 모델 로드 시 이 함수를 import해 소비한다(중복 선언 제거 — 전사기 내부의 로컬 `_detect_device`를 대체).
- 헤드리스 검증 수행: 전 backend 모듈 import 성공, `enumerate_devices()` 장치 0개에서 예외 없이 `([],[])`, `WavRecorder`/`TranscriptWriter`/`RecordingSession.save_json` 산출 정상, `TranscribeWorker` enqueue→`chunk_ready` 배선(워커 스레드 경유) 정상. `transcriber.py`는 모듈 import-safe이며 실제 모델 전사는 faster-whisper 설치 배포 머신/QA 셀프테스트에서 검증한다.
- 발견(M2 오디오 엔진 work-item 핸드오프): `app/audio/mixer.py`의 단일 소스 폴백이 정상 이중 스트림에서 mic·loopback을 믹싱하지 않고 연결(concatenate)해 타임라인이 2배가 되는 결함. 상세는 `docs/plans/2026-06-13-backend-build-handoff-and-mixer-finding.md` 참조.
