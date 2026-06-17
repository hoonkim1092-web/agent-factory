# Feature Plan

## Metadata
- **work_item**: 마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시
- **owner**: Frontend Dev (주관), Backend Dev / QA Engineer (협업)
- **status**: draft
- **last_updated**: 2026-06-13

## Background

원격·대면 회의에서 화자 본인의 마이크 음성과 상대방의 시스템 출력 음성(스피커로 재생되는 원격 참석자 발화)을 모두 담아 회의록을 남기려는 수요가 분명하다. 그러나 클라우드 STT는 프라이버시 노출, 사용량 기반 비용, 오프라인 불가라는 제약이 크다. 이를 해소하기 위해 **로컬 faster-whisper 기반 오프라인 STT**를 채택하고, 마이크와 시스템오디오를 동시에 캡처하여 실시간으로 한국어 자막을 출력하는 Windows 데스크톱 앱을 구현한다.

워크스페이스에는 이미 `feature-spec.md` / `feature-plan.md` / `implementation-tasks.md` 초안과 `task_execution_plan.md`(role 4 · module 11 · task 33), `.todo.md`, `project_board_state.json`, work_item 2건이 존재한다. 따라서 본 작업은 **재설계가 아니라 확정된 아키텍처 위에서 실제 동작하는 앱으로 진입하는 구현 단계**다.

구현이 충족해야 할 핵심 역량(required_capabilities)은 다음과 같다: 마이크+시스템오디오 동시 이중 스트림 캡처, 실시간 리샘플·믹싱, 워커 큐 기반 논블로킹 전사, VAD 기반 청크 스트리밍 STT, WAV·전사 영속화, 헤드리스 합성 오디오 셀프테스트, native DLL 포함 PyInstaller onedir 번들링.

## Problem Statement

마이크 입력과 시스템 출력(WASAPI loopback)을 **동시에 캡처해 16kHz mono로 믹싱**하면서도, **UI를 절대 블로킹하지 않고** 청크 단위 전사를 실시간으로 화면에 흘려보내는 파이프라인이 부재하다. 또한 마이크·오디오 장치가 없는 **헤드리스/CI 환경에서 STT 파이프라인의 동작을 검증할 수단**이 없어, 자동화된 완료 확인 자체가 불가능한 상태다.

## Goals

- 마이크와 시스템오디오(WASAPI loopback)를 동시 녹음하면서 로컬 faster-whisper로 실시간 한국어 자막을 출력하고 종료 시 WAV와 전사 텍스트를 자동 저장하는 PySide6 Windows 데스크톱 앱을 만든다.
- 실행 가능한 PySide6 회의록 STT 데스크톱 앱을 제공한다.
- 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진을 구현한다.
- faster-whisper 실시간 청크 전사 워커를 구현한다.
- 실시간 자막 패널·장치 선택·레벨 미터·타이머 UI를 구현한다.
- WAV + 전사(.txt/.md) 자동 저장 모듈을 구현한다.
- 세션 메타데이터 JSON 저장을 구현한다.
- requirements.txt 의존성 명세를 작성한다.
- 설치/실행/시스템오디오 주의사항 README를 작성한다.
- PyInstaller onedir 빌드 스크립트/스펙을 제공한다.
- 합성 오디오 헤드리스 셀프테스트 스크립트를 제공한다.

## Non-Goals

- 클라우드/온라인 STT API 연동 (로컬 전용)
- 화자 분리(diarization)
- 회의 요약·번역·키워드 추출 등 후처리 기능
- macOS/Linux 지원 (Windows WASAPI 전용)
- 실시간 자막의 사후 편집기/타임라인 에디터
- 모델 파인튜닝·학습

## Scope

### In Scope (모듈 단위)

| 모듈 | 산출물 | 담당 |
|------|--------|------|
| M1 | 실행 가능한 PySide6 앱 (엔트리/패키지 구조) | Frontend Dev |
| M2 | 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진 | Frontend Dev / Backend Dev |
| M3 | faster-whisper 실시간 청크 전사 워커 | Frontend Dev |
| M4 | 실시간 자막 패널·장치 선택·레벨 미터·타이머 UI | Frontend Dev |
| M5 | WAV + 전사(.txt/.md) 자동 저장 모듈 | Frontend Dev |
| M6 | 세션 메타데이터 JSON 저장 (RecordingSession) | Frontend Dev |
| M7 | requirements.txt 의존성 명세 | Frontend Dev |
| M8 | 설치/실행/시스템오디오 주의사항 README | Frontend Dev |
| M9 | PyInstaller onedir 빌드 스크립트/스펙 | Frontend Dev |
| M10 | 합성 오디오 헤드리스 셀프테스트 스크립트 | QA Engineer |
| M11 | 오디오/데이터/외부 연동 백엔드 레이어 | Backend Dev |

### 아키텍처 제약 (변경 금지)

- **STT 엔진**: 로컬 faster-whisper 고정. CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`. 모델 기본 `small`(tiny/base/small/medium 선택).
- **오디오 캡처**: pyaudiowpatch WASAPI loopback + 마이크를 각각 스레드로 받아 16kHz mono로 리샘플 후 믹싱. 고품질 원본 WAV도 별도 저장.
- **전사 언어**: 기본 `ko`, `auto` 옵션 제공.
- **UI**: PySide6. 전사는 워커 스레드/큐로 분리해 절대 블로킹하지 않음.
- **실시간 청크화**: faster-whisper 내장 VAD 또는 최대 길이(10~15초) 도달 시 전사.
- **저장 경로**: 절대경로 하드코딩 금지 — 사용자 홈/문서 폴더 또는 앱 실행 폴더 하위 `meetings/`.
- **셀프테스트**: 마이크 없는 헤드리스/CI 환경에서 합성 사인파/샘플 WAV로 검증 가능.
- **패키징**: PyInstaller onedir로 ctranslate2 DLL/모델 포함.

### 데이터 모델

- **RecordingSession** (json): session_id, started_at, ended_at, wav_path, transcript_txt_path, transcript_md_path, model_size, language, mic_device, loopback_device, duration_sec
- **TranscriptChunk** (memory): chunk_index, start_ts, end_ts, text, language, no_speech_prob
- **AppSettings** (json): model_size, language, mic_device_index, loopback_device_index, save_root, max_chunk_sec, use_vad

### Out of Scope

Non-Goals 항목 전체.

## Stakeholders

- **Frontend Dev**: UI·앱 셸·전사 워커·저장 모듈 등 9개 모듈 주관 (사용자 화면/상호작용 레이어)
- **Backend Dev**: 오디오 캡처·데이터·외부 연동 레이어 (WASAPI loopback 캡처)
- **QA Engineer**: 핵심 플로우·회귀 시나리오 검증, 합성 오디오 헤드리스 셀프테스트
- **요청자(End User)**: 회의록을 오프라인·프라이버시 보장 환경에서 남기려는 사용자

## Success Metrics

- 앱이 import 오류 없이 기동된다 (헤드리스 검증: 모듈 import + 오디오 장치 enumerate + 합성 오디오로 STT 파이프라인 1회 전사 성공).
- 녹음 시작 → 실시간 자막 출력 → 정지 → WAV + 전사 파일 저장의 전체 흐름이 코드상 end-to-end로 연결되어 있다.
- 전사 워커가 UI 스레드를 블로킹하지 않는다 (큐/스레드 분리 확인).
- 저장 경로에 절대경로 하드코딩이 없고 `meetings/` 하위로 생성된다.
- PyInstaller 빌드 스크립트가 존재하고 패키징 절차가 문서화되어 있다.

## Risks and Assumptions

### Risks

- **WASAPI loopback 캡처 실패**: pyaudiowpatch loopback이 장치/드라이버에 따라 활성 스피커가 없으면 캡처 실패할 수 있음 → 장치 부재 시 graceful degradation 분기 필요.
- **믹싱 드리프트/싱크 어긋남**: 마이크와 시스템오디오의 샘플레이트·채널·타이밍 차이로 믹싱 시 드리프트 발생 가능 → 공통 16kHz mono 리샘플 + 버퍼 정렬 전략 필요.
- **전사 백로그**: faster-whisper small CPU int8 전사가 실시간보다 느려 청크 백로그가 쌓일 수 있음 → 큐 길이 모니터링 + 모델 크기 다운그레이드 옵션.
- **번들 누락**: ctranslate2 DLL과 whisper 모델 가중치를 PyInstaller onedir에 누락 없이 포함하기 어려움 → hidden imports / binaries / datas 명시 + 빌드 후 검증.
- **헤드리스 장치 부재**: CI 환경에 오디오 장치가 없어 enumerate·캡처 경로가 실패할 수 있음 → mock/우회 분기 필수.
- **모델 다운로드 지연/부재**: 최초 실행 시 모델 다운로드 지연 또는 오프라인 환경에서 모델 부재 → 모델 사전 번들 또는 명시적 안내.

### Assumptions

- 워크스페이스의 기존 feature-spec/feature-plan/implementation-tasks/task_execution_plan 초안과 work_item 2건의 진행 상태를 이어받아 구현 단계로 진입한다.
- VAD는 외부 webrtcvad 대신 faster-whisper 내장 `vad_filter`를 사용해 의존성을 최소화한다.
- 오디오·STT 엔진은 Frontend Dev의 UI 레이어와 분리해 별도 엔지니어 역할(Backend Dev)로 다루는 것이 권장된다.
- blast_radius는 `isolated`이며, 본 work item은 외부 프로젝트(meeting_stt_app) 내부에 격리되어 있다.

## Evidence

### Verification Focus (검증 기준)

- 모듈 import가 오류 없이 성공하는지 (헤드리스).
- 오디오 장치 enumerate가 장치 없는 환경에서도 graceful하게 동작하는지.
- 합성 사인파/샘플 WAV가 faster-whisper 파이프라인을 1회 전사 성공하는지.
- 녹음 시작 → 실시간 자막 append → 정지 → WAV+전사 저장 흐름이 코드상 end-to-end 연결되는지.
- 전사 워커가 UI 스레드를 블로킹하지 않는지 (큐/스레드 분리 확인).
- 저장 경로에 절대경로 하드코딩이 없고 `meetings/` 하위로 생성되는지.
- PyInstaller 빌드 스크립트가 존재하고 패키징 절차가 문서화되어 있는지.

### Required Capabilities (스킬 조달 신호)

concurrent_dual_stream_audio_capture, realtime_audio_resample_and_mix, nonblocking_worker_queue_transcription, vad_chunked_streaming_stt, wav_and_transcript_persistence, headless_synthetic_audio_selftest, pyinstaller_onedir_bundling_with_native_dll — 모두 기존 기술 스택(PySide6, faster-whisper, pyaudiowpatch, numpy, soundfile, PyInstaller) 내에서 충족 가능.

### Skill Gap Hypotheses (reuse/enhance/forge 계획)

- skill_gap_hypotheses는 비어 있음 — 신규 스킬 forge 신호 없음. required_skills(pyside6_gui_development, wasapi_loopback_audio_capture, faster_whisper_transcription, multithreaded_audio_pipeline, numpy_audio_resampling_mixing, wav_file_io, pyinstaller_packaging, headless_synthetic_audio_testing)는 **reuse** 전제로 진행한다.

### Workspace Evidence

- 기존 초안 문서가 존재하므로 재작성이 아닌 구현 진입이 타당함 (feature-spec/feature-plan/implementation-tasks/task_execution_plan).
- `feature-spec.md` Outputs 섹션은 실시간 자막 패널 텍스트, 원본 WAV(`meetings/<session>/...wav`), 전사 텍스트(.txt/.md), 세션 메타 JSON(RecordingSession), UI 상태 표시를 산출물로 명시 — 본 plan의 Deliverables와 일치.

## References

- `docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/feature-spec.md` — Outputs / Feature Overview / Inputs (확정 산출물·아키텍처·입력 정의)
- `docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/feature-plan.md` — Goals (기존 목표 초안)
- `docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/implementation-tasks.md` — Metadata (work item / source_design)
- `docs/task_execution_plan.md` — Overview (role 4 · module 11 · task 33 실행 계획)
- 워크스페이스 산출물: `.todo.md`, `project_board_state.json`, work_item 2건

## Approval Request

본 Feature Plan은 확정된 아키텍처(STT=로컬 faster-whisper, 오디오=pyaudiowpatch WASAPI loopback+마이크 믹싱, UI=PySide6 논블로킹 워커, 패키징=PyInstaller onedir) 위에서 11개 모듈·33개 작업으로 구현 단계에 진입하는 계획입니다.

다음 사항에 대한 승인을 요청합니다.

1. **Scope·Non-Goals 동결**: 위에 정의된 In Scope 11개 모듈과 Non-Goals(클라우드 STT·diarization·요약/번역·macOS/Linux·편집기·파인튜닝 제외)를 이번 구현 범위로 확정.
2. **데이터 모델 확정**: RecordingSession / TranscriptChunk / AppSettings 3개 엔티티 스키마.
3. **완료 기준 채택**: Success Metrics와 Verification Focus를 검수 게이트로 사용 (헤드리스 합성 오디오 셀프테스트 1회 전사 성공 = 핵심 통과 조건).
4. **역할 배분 확인**: Frontend Dev 주관 + Backend Dev(오디오 엔진)·QA Engineer(셀프테스트) 협업 구조.

승인 시 `scope_contracts → vertical_slice_build → integration_handoff → verification_closeout` 순으로 구현을 진행합니다.