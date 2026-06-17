# Feature Spec

## Metadata
- **work_item**: 마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시
- **source_plan**: feature-plan.md (회의록 STT 데스크톱 앱)
- **status**: draft
- **last_updated**: 2026-06-13

## Feature Overview

마이크와 시스템오디오(WASAPI loopback)를 **동시에 녹음**하면서, 로컬 faster-whisper로 **실시간 한국어 자막**을 화면에 출력하고, 종료 시 **원본 WAV와 전사 텍스트(.txt/.md)를 자동 저장**하는 PySide6 Windows 데스크톱 애플리케이션이다.

원격·대면 회의에서 화자 본인의 마이크 음성과 상대방의 시스템 출력 음성(스피커로 재생되는 원격 참석자 발화)을 모두 담아 회의록을 남기려는 수요를 충족한다. 클라우드 STT의 프라이버시 노출·사용량 기반 비용·오프라인 불가 제약을 피하기 위해 **로컬 오프라인 STT(faster-whisper)** 를 채택한다.

핵심 아키텍처는 다음과 같이 확정(변경 금지)되어 있다.

- **STT 엔진**: 로컬 faster-whisper. CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`. 모델 기본 `small`(tiny/base/small/medium 선택 가능).
- **오디오 캡처**: pyaudiowpatch WASAPI loopback + 마이크를 각각 별도 스레드로 받아 16kHz mono로 리샘플 후 믹싱. 고품질 원본 WAV도 별도 저장.
- **전사 언어**: 기본 `ko`, `auto` 자동감지 옵션 제공.
- **UI**: PySide6 GUI. 전사는 워커 스레드/큐로 분리해 UI를 절대 블로킹하지 않는다.
- **실시간 청크화**: 롤링 버퍼에 오디오를 누적하고, faster-whisper 내장 VAD(무음 감지) 또는 최대 길이(10~15초) 도달 시 청크를 워커 스레드에서 전사하여 자막 패널에 append.
- **저장 경로**: 절대경로 하드코딩 금지 — 사용자 홈/문서 폴더 또는 앱 실행 폴더 하위 `meetings/`.

## User Scenarios

1. **앱 기동 및 장치 선택**
   사용자가 앱을 실행하면 시스템이 마이크·시스템출력 장치를 enumerate해 드롭다운을 채우고, 기본 `small` 모델을 로드한다. 사용자는 마이크/시스템출력 장치, 모델 크기(tiny/base/small/medium), 전사 언어(ko/auto)를 선택한다.

2. **녹음 시작 및 실시간 전사**
   사용자가 녹음 시작을 클릭하면 시스템이 마이크와 시스템오디오 두 스트림 캡처·믹싱을 시작하고, 타이머와 오디오 레벨 미터를 갱신한다. 롤링 버퍼가 VAD 무음 또는 최대 길이에 도달하면 워커 스레드가 청크를 전사해 자막 패널에 append한다. 이 동안 UI는 블로킹되지 않는다.

3. **녹음 정지 및 저장**
   사용자가 정지를 클릭하면 시스템이 캡처를 종료하고, 원본 WAV + 전사 `.txt/.md` + 세션 메타 JSON(RecordingSession)을 `meetings/<session>/`에 저장한 뒤 저장 경로를 화면에 표시한다.

4. **헤드리스/CI 셀프테스트**
   마이크·오디오 장치가 없는 CI/헤드리스 환경에서 셀프테스트 스크립트를 실행하면, 시스템이 합성 사인파/샘플 WAV를 faster-whisper 파이프라인에 1회 통과시켜 전사 성공을 확인한다.

## Functional Requirements

### FR-1. 이중 스트림 동시 오디오 캡처 (`concurrent_dual_stream_audio_capture`)
- 마이크 입력 스트림과 시스템 출력 WASAPI loopback 스트림을 각각 별도 스레드로 동시 캡처한다.
- 활성 스피커가 없거나 loopback 장치를 열 수 없는 경우 캡처를 graceful하게 실패 처리하고, 마이크 단독 모드 또는 명시적 오류 안내로 분기한다.

### FR-2. 실시간 리샘플·믹싱 (`realtime_audio_resample_and_mix`)
- 두 스트림을 공통 16kHz mono로 리샘플한 뒤 믹싱한다.
- 샘플레이트·채널·타이밍 차이로 인한 드리프트를 완화하기 위해 버퍼 정렬 전략을 적용한다.
- 믹싱 결과와 별도로 고품질 원본 WAV를 저장한다.

### FR-3. 논블로킹 워커 큐 전사 (`nonblocking_worker_queue_transcription`)
- 전사는 UI 스레드와 분리된 워커 스레드/큐에서 수행한다.
- UI 스레드는 어떤 경우에도 전사 연산으로 블로킹되지 않는다.

### FR-4. VAD 기반 청크 스트리밍 STT (`vad_chunked_streaming_stt`)
- 롤링 버퍼에 오디오를 누적하고, faster-whisper 내장 `vad_filter`(무음 감지) 또는 최대 길이(10~15초) 도달 시 청크를 전사한다.
- 전사 결과를 TranscriptChunk 단위로 자막 패널에 append한다.
- 전사 언어는 기본 `ko`, `auto` 옵션을 제공한다.

### FR-5. STT 엔진 구성
- CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`로 모델을 로드한다.
- 모델 크기는 tiny/base/small/medium 중 선택 가능하며 기본값은 `small`이다.

### FR-6. UI 레이어 (`pyside6_gui_development`)
- 녹음 시작/정지 버튼, 마이크·시스템출력 장치 선택 드롭다운, 모델 크기 선택, 언어 선택, 실시간 자막 패널(청크 단위 append), 녹음 타이머, 오디오 레벨 미터, 저장 경로 표시를 제공한다.

### FR-7. WAV + 전사 영속화 (`wav_and_transcript_persistence`)
- 정지 시 원본 녹음 WAV(`meetings/<session>/...wav`)와 전사 텍스트(`.txt` 및/또는 `.md`)를 자동 저장한다.

### FR-8. 세션 메타데이터 저장
- 세션 메타데이터(RecordingSession)를 JSON으로 저장한다.

### FR-9. 헤드리스 합성 오디오 셀프테스트 (`headless_synthetic_audio_selftest`)
- 마이크 없는 헤드리스/CI 환경에서 합성 사인파/샘플 WAV를 16kHz mono로 만들어 STT 파이프라인을 장치 없이 1회 통과시키는 셀프테스트 스크립트를 제공한다.
- 오디오 장치 enumerate가 장치 부재 환경에서도 graceful하게 동작한다.

### FR-10. 패키징 (`pyinstaller_onedir_bundling_with_native_dll`)
- PyInstaller onedir로 ctranslate2 native DLL과 whisper 모델 가중치를 누락 없이 번들하는 빌드 스크립트/스펙을 제공한다.
- requirements.txt 의존성 명세와 설치/실행/시스템오디오 주의사항 README를 제공한다.

> **스킬 조달 신호**: 위 required_capabilities는 모두 기존 기술 스택(PySide6, faster-whisper, pyaudiowpatch, numpy, soundfile, PyInstaller) 내에서 충족 가능하며, 신규 스킬 forge 없이 **reuse** 전제로 구현한다.

## Non-Functional Requirements

- **프라이버시/오프라인**: STT는 로컬 전용. 외부 네트워크로 오디오·전사 데이터를 전송하지 않는다.
- **반응성**: 전사 워커는 UI를 블로킹하지 않으며, 청크 백로그가 쌓이면 큐 길이 모니터링과 모델 크기 다운그레이드로 완화할 수 있다.
- **이식성**: 절대경로 하드코딩 금지. 저장 경로는 사용자 홈/문서 폴더 또는 앱 실행 폴더 하위 `meetings/`로 한정한다.
- **검증 가능성**: 마이크·오디오 장치가 없는 헤드리스/CI 환경에서도 import·enumerate·STT 1회 전사 경로가 검증 가능해야 한다.
- **플랫폼**: Windows WASAPI 전용(macOS/Linux 미지원).
- **의존성 최소화**: VAD는 외부 webrtcvad 대신 faster-whisper 내장 `vad_filter`를 사용한다.

## Inputs and Outputs

### Inputs
- 마이크 오디오 스트림(선택된 입력 장치)
- 시스템 출력 WASAPI loopback 스트림(선택된 기본 스피커)
- 사용자 설정: 모델 크기(tiny/base/small/medium), 전사 언어(ko/auto), 장치 선택, 저장 경로, 최대 청크 길이, VAD 사용 여부
- (셀프테스트) 합성 사인파 또는 샘플 WAV

### Outputs
- 실시간 자막 패널의 청크 단위 전사 텍스트
- 원본 녹음 WAV 파일(`meetings/<session>/...wav`)
- 전사 텍스트 파일(`.txt` 및/또는 `.md`)
- 세션 메타데이터 JSON(RecordingSession)
- 오디오 레벨 미터·타이머·저장 경로 등 UI 상태 표시

### 데이터 모델
| 엔티티 | 저장 | 주요 필드 |
|--------|------|-----------|
| RecordingSession | json | session_id, started_at, ended_at, wav_path, transcript_txt_path, transcript_md_path, model_size, language, mic_device, loopback_device, duration_sec |
| TranscriptChunk | memory | chunk_index, start_ts, end_ts, text, language, no_speech_prob |
| AppSettings | json | model_size, language, mic_device_index, loopback_device_index, save_root, max_chunk_sec, use_vad |

## Exceptions and Failure Scenarios

- **WASAPI loopback 캡처 실패**: 활성 스피커/드라이버 부재 시 loopback 캡처가 실패할 수 있다 → 장치 부재 시 graceful degradation(마이크 단독 또는 명시적 오류 안내) 분기.
- **믹싱 드리프트/싱크 어긋남**: 마이크와 시스템오디오의 샘플레이트·채널·타이밍 차이로 드리프트 발생 가능 → 공통 16kHz mono 리샘플 + 버퍼 정렬.
- **전사 백로그**: faster-whisper small CPU int8 전사가 실시간보다 느려 청크 백로그가 쌓일 수 있다 → 큐 길이 모니터링 + 모델 크기 다운그레이드 옵션.
- **번들 누락**: ctranslate2 DLL·whisper 모델 가중치가 PyInstaller onedir에 누락될 수 있다 → hidden imports/binaries/datas 명시 + 빌드 후 검증.
- **헤드리스 장치 부재**: CI 환경에 오디오 장치가 없어 enumerate·캡처 경로가 실패할 수 있다 → mock/우회 분기 + 셀프테스트 경로 보장.
- **모델 다운로드 지연/부재**: 최초 실행 시 모델 다운로드 지연 또는 오프라인 환경에서 모델 부재 가능 → 모델 사전 번들 또는 명시적 안내.

## Existing Behavior To Preserve

- 워크스페이스의 기존 초안(`feature-spec.md`/`feature-plan.md`/`implementation-tasks.md`/`task_execution_plan.md`)이 정의한 산출물·아키텍처·입력/출력 정의를 유지한다. 본 작업은 재설계가 아니라 확정된 아키텍처 위에서의 구현 진입이다.
- 기존 `.todo.md`, `project_board_state.json`, work_item 2건의 진행 상태를 이어받는다.
- 확정 아키텍처 결정(STT=로컬 faster-whisper, 오디오=pyaudiowpatch WASAPI loopback+마이크 믹싱, UI=PySide6 논블로킹 워커, 패키징=PyInstaller onedir)은 변경하지 않는다.

## Acceptance Criteria

- [ ] 모든 모듈이 헤드리스 환경에서 **import 오류 없이** 성공한다.
- [ ] 오디오 장치 enumerate가 **장치 없는 환경에서도 graceful하게** 동작한다(예외로 중단되지 않음).
- [ ] 합성 사인파/샘플 WAV가 faster-whisper 파이프라인을 **1회 전사 성공**한다(셀프테스트 통과 = 핵심 통과 조건).
- [ ] 녹음 시작 → 실시간 자막 append → 정지 → WAV + 전사(.txt/.md) + 세션 메타 JSON 저장의 전체 흐름이 **코드상 end-to-end로 연결**되어 있다.
- [ ] 전사 워커가 **UI 스레드를 블로킹하지 않는다**(전사 연산이 워커 스레드/큐로 분리되어 있음을 코드상 확인).
- [ ] 저장 경로에 **절대경로 하드코딩이 없고**, 산출물이 `meetings/<session>/` 하위에 생성된다.
- [ ] CUDA 감지 분기(`cuda`/`float16` vs CPU `int8`)와 모델 크기 기본 `small` 선택이 동작한다.
- [ ] 전사 언어 기본 `ko`와 `auto` 옵션이 선택 가능하다.
- [ ] **PyInstaller 빌드 스크립트가 존재**하고, ctranslate2 DLL/모델 포함 패키징 절차가 README에 문서화되어 있다.
- [ ] requirements.txt가 faster-whisper, pyaudiowpatch, PySide6, numpy, soundfile/scipy 등 필수 의존성을 명세한다.

## Evidence

### Verification Focus (검수 게이트)
- 모듈 import가 오류 없이 성공하는지(헤드리스)
- 오디오 장치 enumerate가 장치 없는 환경에서도 graceful하게 동작하는지
- 합성 사인파/샘플 WAV가 faster-whisper 파이프라인을 1회 전사 성공하는지
- 녹음 시작 → 실시간 자막 append → 정지 → WAV+전사 저장 흐름이 코드상 end-to-end 연결되는지
- 전사 워커가 UI 스레드를 블로킹하지 않는지(큐/스레드 분리 확인)
- 저장 경로에 절대경로 하드코딩이 없고 `meetings/` 하위로 생성되는지
- PyInstaller 빌드 스크립트가 존재하고 패키징 절차가 문서화되어 있는지

### Skill Gap / 조달 계획
- `skill_gap_hypotheses`는 비어 있어 신규 스킬 forge 신호가 없다. required_skills(pyside6_gui_development, wasapi_loopback_audio_capture, faster_whisper_transcription, multithreaded_audio_pipeline, numpy_audio_resampling_mixing, wav_file_io, pyinstaller_packaging, headless_synthetic_audio_testing)는 모두 **reuse** 전제로 진행한다.
- required_capabilities(이중 스트림 캡처, 실시간 리샘플·믹싱, 논블로킹 워커 큐 전사, VAD 청크 스트리밍 STT, WAV·전사 영속화, 헤드리스 셀프테스트, native DLL onedir 번들링)는 기존 기술 스택 내에서 충족 가능하다.

### Workspace Evidence
- 기존 초안 문서가 존재하므로 재작성이 아닌 구현 진입이 타당하다.
- 기존 `feature-spec.md`의 Outputs/Inputs/Feature Overview가 본 스펙의 산출물·입력·아키텍처 정의와 일치한다(자막 텍스트, 원본 WAV, 전사 .txt/.md, 세션 메타 JSON, UI 상태 표시).

## References

- `docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/feature-spec.md` — Outputs / Feature Overview / Inputs (확정 산출물·아키텍처·입력 정의)
- `docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/feature-plan.md` — Goals
- `docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/implementation-tasks.md` — Metadata (work item / source_design)
- `docs/task_execution_plan.md` — Overview (role 4 · module 11 · task 33)
- 워크스페이스 산출물: `.todo.md`, `project_board_state.json`, work_item 2건

## Out Of Scope

- 클라우드/온라인 STT API 연동 (로컬 전용)
- 화자 분리(diarization)
- 회의 요약·번역·키워드 추출 등 후처리 기능
- macOS/Linux 지원 (Windows WASAPI 전용)
- 실시간 자막의 사후 편집기/타임라인 에디터
- 모델 파인튜닝·학습