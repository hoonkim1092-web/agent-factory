# Backend Dev — module_10 검증 결과 및 핸드오프 (2026-06-13)

- 작업: `backend_dev_module_10_verify_3` (verify 단계)
- 선행: `backend_dev_module_10_build_2` [completed]
- 검증 환경: Windows 11 / Python 3.12.8 / numpy 2.4.6 / **헤드리스(무거운 런타임 의존성 전부 미설치)**

## 1. 검증 결과 요약 — 전 항목 PASS

| # | 검증 초점 | 결과 | 근거 |
|---|----------|------|------|
| 1 | 모듈 import 무오류(헤드리스 기동) | **PASS** | `selftest_pipeline` S0, `py_compile` 전 파일 OK |
| 2 | 오디오 장치 enumerate 예외 없음 | **PASS** | `enumerate_devices() -> ([],[])` 무예외, `detect_compute_device() -> ('cpu','int8')` |
| 3 | 합성 사인파/WAV가 STT 파이프라인 1회 통과 | **PASS(가짜 전사기)** / 실모델은 QA로 이관 | `selftest_pipeline` S7/S8, 별도 synthetic WAV selftest PASS |
| 4 | 녹음 시작→청크 전사→정지→WAV+전사 저장 end-to-end 배선 | **PASS** | `PipelineController.start/stop` 코드 + S7/S8 산출물 4종 생성 확인 |
| 5 | 저장 경로 절대경로 하드코딩 없음(meetings/ 상대) | **PASS** | `app/**/*.py` 절대경로 리터럴 0건, `resolve_save_root`가 `Path.home()` 파생 |
| 6 | PyInstaller 스펙이 ctranslate2 DLL·모델 포함 | **PARTIAL PASS** | DLL·패키지 데이터는 포함, 모델 **가중치는 런타임 다운로드**(아래 R2) |
| 7 | module_10 심볼이 production 경로에 연결(dead symbol 아님) | **PASS** | 전 심볼 production caller 존재(아래 §3) |

### 실행한 검증 명령과 출력
```
$ python -m tests.selftest_pipeline
[PASS] S0 전 모듈 import 성공
[PASS] S1 resolve_save_root 동작
[PASS] S3 믹서 16kHz mono 청크 반환
[PASS] S7 stop()이 RecordingSession 반환
[PASS] S7 상태 SAVED 전이
[PASS] S8 산출물(WAV/txt/md/json) 생성
[PASS] S8 전사 결과가 transcript/시그널에 반영
[SKIP] S2 실제 faster-whisper 전사 (MEETING_STT_RUN_WHISPER!=1)
--- 결과: 5/5 통과 ---

$ python scripts/synthetic_audio_headless_selftest.py
PASS synthetic audio selftest: .selftest\synthetic_audio\synthetic_selftest_report.json

$ python -m py_compile app/*.py app/audio/*.py app/io/*.py app/stt/*.py app/ui/*.py scripts/*.py tests/*.py
py_compile ALL OK
```

## 2. dead symbol 검증 (focus 3) — 전부 연결됨, BLOCK 없음

`grep`으로 module_10 핵심 심볼의 production caller를 전수 확인했다.

| 심볼 | 정의 | production caller |
|------|------|-------------------|
| `PipelineController` | `app/main.py:58` | `main()` `app/main.py:265`, `MainWindow(controller)` `app/main.py:266` |
| `enumerate_devices` | `app/audio/devices.py:49` | `MainWindow._populate_devices` `app/ui/main_window.py:111` (장치 콤보) |
| `detect_compute_device` | `app/audio/devices.py:25` | `Transcriber.__init__` `app/stt/transcriber.py:30` (모델 로드) |
| `resolve_save_root` | `app/config.py:71` | `PipelineController.start` `app/main.py:112` (저장 루트) |

UI↔컨트롤러 양방향 배선도 확인: `_connect_controller`(`main_window.py:123`)가 `state_changed/level_changed/chunk_ready/saved/error` 5개 시그널을 위젯 핸들러에 연결하고, 시작/정지 버튼이 `controller.start/stop`을 호출한다. **고아(dead) 심볼 없음.**

## 3. 정지 시 저장 흐름 (focus 4) — 코드상 단선 없음

`PipelineController.stop`(`app/main.py:181`)의 순서:
캡처 stop → 펌프 정지 → 믹서 잔여 read+flush → 워커 `stop_and_drain` →
WavRecorder `close` → TranscriptWriter `flush`(txt/md) → `RecordingSession.save_json`(session.json) → `SAVED` 전이 + `saved` 시그널.
S8 테스트가 `recording.wav`/`transcript.txt`/`transcript.md`/`session.json` 4종 생성과 비어있지 않은 transcript를 실제로 확인.

## 4. 잔여 리스크 (후속 작업자 필독)

### R1 — 실모델/실장치/UI 미검증 (환경 한계, 차단 아님)
- 본 검증 환경에는 `PySide6`/`faster_whisper`/`ctranslate2`/`pyaudiowpatch`가 **전부 미설치**. 설계상 lazy-import + Qt 셰임 스텁 + 가짜 전사기로 헤드리스에서 배선만 검증한 것이다.
- **미검증 항목**: (a) 실제 faster-whisper 한국어 전사 품질/지연(S2), (b) WASAPI loopback 실캡처, (c) PySide6 UI 실렌더링·스레드 친화성.
- **후속(QA)**: 의존성 설치된 Windows 머신에서 `MEETING_STT_RUN_WHISPER=1 python -m tests.selftest_pipeline`로 S2 활성화 + 실제 마이크/시스템오디오 동시 녹음 수동 검증.

### R2 — PyInstaller 스펙: 모델 가중치 미번들 (focus 6 단서)
- `meeting_stt.spec`는 `collect_dynamic_libs("ctranslate2")`(네이티브 DLL)와 `collect_data_files("faster_whisper"|"ctranslate2")`(패키지 데이터), `pyaudiowpatch` hiddenimport를 포함한다. **이 부분은 적정.**
- 그러나 whisper **모델 가중치(.bin)는 faster-whisper가 첫 실행 시 HuggingFace 캐시로 다운로드**하는 구조라 번들에 들어가지 않는다. 오프라인 배포 시 첫 실행이 실패할 수 있다.
- **후속(QA/배포)**: 모델을 사전 다운로드해 번들 동봉(`datas`에 모델 캐시 경로 추가)할지, 첫 실행 시 네트워크 다운로드를 허용할지 정책 결정 필요. CUDA 배포 시 `cublas`/`cudnn` DLL 추가 동봉도 함께 검토.

### R3 — 믹서 이중 스트림 concatenate 결함 (재현 확인, M2 work-item 소유)
- `app/audio/mixer.py`의 `_drain_into_pending_locked` 단일 소스 폴백이 **정상 이중 스트림에서도** 한쪽 버퍼가 빈 순간(스트림 시작·정지·스톨 경계)에 greedy하게 한 스트림만 소진해 믹싱이 아니라 연결(concatenate)된다.
- **재현(본 검증에서 실측)**: 1.0초 mic + 1.0초 loopback 주입 → 출력 **2.0초(32000 샘플)**. 기대(평균 믹싱)는 1.0초(16000 샘플). 타임라인 2배 + 음성 중첩 손실.
- 단, 실캡처에서 두 CaptureThread가 작은 프레임을 교차로 밀어 넣으면 `min(len(mic),len(loop))>0`이라 대부분 정상 믹싱된다. 경계(시작/스톨/종료)에서만 발현하는 **부분 심각도** 결함.
- **소유권**: 이 파일은 module_10이 아니라 **M2(마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진) work-item** 소관이며, build 단계(`backend_dev_module_10_build_2`)가 이미 핸드오프 문서(`docs/plans/2026-06-13-backend-build-handoff-and-mixer-finding.md`)로 이관했다. **module_10 verify 범위에서는 기록만 하고 수정하지 않는다.**
- **후속(frontend_dev / M2)**: 도착 정렬을 기다리는 워터마크(파트너 스트림 미도착 시 단독 소진 보류) 또는 단일 소스 폴백을 `_active_sources==1`일 때만 허용하도록 수정 + 이중 스트림 타임라인 길이 단언 테스트 추가.

## 5. 다음 작업자 핸드오프

- **module_10(backend) 검증 종료**: 헤드리스 배선·import·enumerate·저장 흐름·경로 위생·dead symbol·스펙 구성 모두 통과. **추가 backend 수정 불필요.**
- **QA로 이관**: R1(실모델·실장치·UI 실검증), R2(모델 번들 정책).
- **frontend_dev / M2로 이관**: R3(믹서 concatenate 결함).
- 본 검증은 코드 변경 없음(verify only) — `docs/architecture.md` 설계 변경 없어 미수정.
