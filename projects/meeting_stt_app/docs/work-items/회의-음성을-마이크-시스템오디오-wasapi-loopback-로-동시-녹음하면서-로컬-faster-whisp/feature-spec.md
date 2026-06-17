# Feature Spec

## Metadata

- **work_item**: 회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp
- **source_plan**: docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/feature-plan.md
- **status**: draft
- **last_updated**: 2026-06-13

## Feature Overview

회의 음성을 **마이크 입력과 시스템 출력(WASAPI loopback)을 동시에 캡처**하여 고품질 원본 WAV로 녹음하면서, 동시에 **로컬 faster-whisper**로 실시간 한국어 자막(전사)을 화면에 출력하고, 녹음 종료 시 WAV와 전사 텍스트(.txt/.md)를 자동 저장하는 **PySide6 Windows 데스크톱 애플리케이션**이다.

핵심 가치는 **오프라인·무료·프라이버시**다. 클라우드 STT를 일절 사용하지 않고 모든 추론을 로컬에서 수행하므로 민감한 회의 내용이 외부로 전송되지 않는다. 마이크 단일 채널만 받는 기존 도구와 달리 상대방 음성(시스템 출력 loopback)까지 함께 담아 양방향 대화를 누락 없이 기록한다.

아키텍처는 다음과 같이 확정되어 있다(변경 금지):

- **STT 엔진**: 로컬 faster-whisper(ctranslate2 백엔드). CUDA 감지 시 `device=cuda`/`compute_type=float16`, 미감지 시 CPU `int8` 자동 폴백. 모델 크기 `tiny/base/small/medium` 선택 가능, 기본 `small`.
- **오디오 캡처**: pyaudiowpatch로 마이크와 기본 스피커 loopback을 각각 별도 스레드로 받아 16kHz mono로 리샘플 후 믹싱.
- **전사 언어**: 한국어 우선(`language="ko"`), `auto` 자동감지 옵션 제공.
- **UI**: PySide6 GUI. 전사는 워커 스레드/큐로 분리해 UI를 절대 블로킹하지 않는다.
- **실시간 청크화**: 롤링 버퍼에 오디오를 누적하고, faster-whisper 내장 VAD(무음 감지) 또는 최대 길이(10~15초) 도달 시 청크를 워커 스레드에서 전사하여 자막 패널에 append.

## User Scenarios

1. **앱 실행 및 장치 선택**
   사용자가 앱을 실행하면 시스템이 마이크/시스템출력 장치 목록을 enumerate하여 드롭다운에 채운다. 사용자는 마이크 장치, 시스템출력(loopback) 장치, 모델 크기, 전사 언어(ko/auto)를 선택한다.

2. **녹음 시작 및 실시간 자막**
   사용자가 "녹음 시작"을 클릭하면 캡처 스레드 2개(마이크/loopback)가 기동되고, 녹음 타이머와 오디오 레벨 미터가 동작한다. 롤링 버퍼가 VAD 무음 또는 최대 길이에 도달하면 워커 스레드가 청크를 전사하여 자막 패널에 청크 단위로 append한다. 이 과정에서 UI는 블로킹되지 않는다.

3. **녹음 종료 및 자동 저장**
   사용자가 "정지"를 클릭하면 캡처/워커 스레드가 안전하게 종료되고, `meetings/` 하위에 원본 WAV와 전사(.txt/.md)가 자동 저장된 뒤 저장 경로가 화면에 표시된다.

4. **CPU 전용 환경 폴백**
   CUDA/cuDNN을 사용할 수 없는 PC에서 앱을 실행하면 자동으로 CPU `int8` 경로로 폴백되어 동일한 흐름으로 동작한다(속도만 저하).

5. **헤드리스 셀프테스트(개발자/CI)**
   개발자가 셀프테스트 스크립트를 실행하면 마이크 없이도 합성 사인파/샘플 WAV가 faster-whisper STT 파이프라인을 1회 통과하여 전사 결과를 반환하는지 검증한다.

## Functional Requirements

### FR-1. 오디오 캡처·믹싱 엔진
- FR-1.1 pyaudiowpatch로 마이크 입력과 기본 스피커의 WASAPI loopback을 **각각 별도 스레드**로 캡처한다.
- FR-1.2 두 스트림을 **16kHz mono**로 리샘플한 뒤 믹싱하여 STT 입력 스트림을 생성한다.
- FR-1.3 고품질 원본 WAV를 별도로 저장한다.
- FR-1.4 장치 enumerate는 PyAudio host API 순회로 마이크/loopback 후보를 수집하며, **빈 목록도 예외 없이 안전 처리**한다.
- (skill 조달 신호: `concurrent_dual_stream_audio_capture`, `wasapi_loopback_access`, `audio_resampling_mixing`)

### FR-2. 실시간 청크 전사 워커
- FR-2.1 오디오를 롤링 버퍼에 누적하고, faster-whisper 내장 VAD 무음 감지 **또는** 최대 길이(10~15초) 도달 시 청크를 확정한다.
- FR-2.2 확정된 청크를 **워커 스레드**에서 `transcribe(vad_filter=True, language="ko")`로 전사한다.
- FR-2.3 전사 결과를 자막 패널에 청크 단위로 append하며, UI 스레드와는 `queue.Queue`로 분리한다.
- FR-2.4 모델 로드는 CUDA 감지 시 `device=cuda`/`float16`, 미감지 시 CPU `int8`로 결정한다.
- (skill 조달 신호: `local_offline_stt_inference`, `audio_buffer_vad_chunking`, `non_blocking_gui_threading`)

### FR-3. PySide6 GUI
- FR-3.1 녹음 시작/정지 버튼, 마이크/시스템출력 장치 선택 드롭다운, 모델 크기 선택, 언어 선택을 제공한다.
- FR-3.2 실시간 자막 패널(청크 append), 녹음 타이머, 오디오 레벨 미터, 저장 경로 표시를 제공한다.
- FR-3.3 전사·캡처 작업은 워커 스레드/큐로 분리하여 **UI를 절대 블로킹하지 않는다**.
- (skill 조달 신호: `pyside6_gui_development`)

### FR-4. WAV + 전사 자동 저장
- FR-4.1 정지 시 원본 WAV와 전사 텍스트(.txt/.md)를 `meetings/` 하위에 자동 저장한다.
- FR-4.2 저장 경로는 **사용자 홈/문서 폴더 또는 앱 실행 폴더 하위 `meetings/`**로 해석하며 절대경로 하드코딩을 금지한다.
- FR-4.3 세션 메타데이터(`RecordingSession`)를 JSON으로 기록한다.
- (skill 조달 신호: `wav_and_transcript_persistence`)

### FR-5. 패키징·배포
- FR-5.1 PyInstaller **onedir** 빌드 스크립트/스펙을 제공하며 ctranslate2/onnxruntime 네이티브 DLL과 모델을 포함한다.
- FR-5.2 빌드 실행 시 `dist/`에 실행 파일이 생성된다.
- (skill 조달 신호: `pyinstaller_packaging`, `onedir_native_dll_packaging`)

### FR-6. 헤드리스 셀프테스트
- FR-6.1 numpy 합성 사인파 → 16kHz mono WAV → `model.transcribe`로 1회 통과시키는 셀프테스트 스크립트를 제공한다.
- FR-6.2 마이크가 없는 CI/헤드리스 환경에서도 모듈 import + 장치 enumerate + STT 파이프라인 1회 전사를 검증할 수 있다.
- (skill 조달 신호: `headless_self_test_scripting`, `headless_synthetic_audio_verification`)

### FR-7. 데이터 모델
- FR-7.1 `RecordingSession`(session_id, start_time, end_time, wav_path, transcript_path, model_size, language, device) — JSON 저장.
- FR-7.2 `TranscriptChunk`(chunk_index, start_ts, end_ts, text, language, avg_logprob) — 메모리 보관.
- FR-7.3 `AudioConfig`(mic_device_index, loopback_device_index, sample_rate, channels, model_size, language, save_dir) — JSON 저장.

## Non-Functional Requirements

- **NFR-1 (응답성)**: UI는 어떤 상황에서도 블로킹되지 않는다. 모든 캡처·추론은 별도 스레드/큐에서 수행한다.
- **NFR-2 (프라이버시)**: 모든 STT 추론은 로컬에서 수행하며 오디오/전사 데이터를 외부로 전송하지 않는다.
- **NFR-3 (이식성)**: 절대경로 하드코딩 금지. 저장 경로는 환경에 따라 동적으로 해석한다.
- **NFR-4 (하드웨어 적응성)**: CUDA 가용 여부에 따라 GPU/CPU 경로를 자동 선택하며 두 경로 모두 동작한다.
- **NFR-5 (헤드리스 검증성)**: 오디오 장치가 없는 환경에서도 import·enumerate·합성 STT 검증이 가능해야 한다.
- **NFR-6 (오프라인 동작)**: 모델이 캐시된 후에는 인터넷 없이 전사가 동작한다.
- **NFR-7 (플랫폼)**: Windows WASAPI 전용. macOS/Linux 시스템오디오 캡처는 대상 외.

## Inputs and Outputs

### Inputs
- 마이크 오디오 스트림(선택된 입력 장치)
- 시스템 출력 WASAPI loopback 스트림(선택된 기본 스피커)
- 사용자 설정: 모델 크기(tiny/base/small/medium), 전사 언어(ko/auto), 장치 선택, 저장 경로
- (셀프테스트) 합성 사인파 또는 샘플 WAV

### Outputs
- 실시간 자막 패널의 청크 단위 전사 텍스트
- 원본 녹음 WAV 파일(`meetings/<session>/...wav`)
- 전사 텍스트 파일(`.txt` 및/또는 `.md`)
- 세션 메타데이터 JSON(`RecordingSession`)
- 오디오 레벨 미터·타이머·저장 경로 등 UI 상태 표시

## Exceptions and Failure Scenarios

- **EX-1 loopback 장치 부재/변경**: 기본 스피커가 없거나 변경되어 WASAPI loopback 획득 실패 → 명확한 오류 메시지 표시, 마이크 단독 진행 가능 여부 안내.
- **EX-2 모델 미캐시·다운로드 지연**: small 모델(~500MB) 첫 실행 다운로드 지연 또는 오프라인 캐시 부재 → 진행 상태/오류를 사용자에게 표시.
- **EX-3 스트림 드리프트**: 마이크/시스템 두 스트림의 샘플레이트·버퍼 드리프트로 믹싱 동기 어긋남 → 리샘플·버퍼 정렬로 완화.
- **EX-4 CUDA/cuDNN 불일치**: GPU 경로 로드 실패 → CPU int8 경로로 자동 폴백.
- **EX-5 PyInstaller DLL/모델 누락**: ctranslate2/onnxruntime DLL 또는 모델 미포함으로 빌드 실행 실패 → spec hiddenimports/datas에 포함, 문서화.
- **EX-6 청크 경계 단어 절단**: 실시간 청크 경계에서 단어가 잘려 정확도 저하 → VAD 우선 분할로 완화.
- **EX-7 장치 enumerate 빈 목록**: CI/헤드리스 환경에 오디오 장치 부재 → 빈 목록을 예외 없이 안전 처리.

## Existing Behavior To Preserve

- 본 work-item은 신규 프로젝트(`projects/meeting_stt_app`)로, 보존해야 할 기존 런타임 동작은 없다.
- 단, 워크스페이스에 이미 존재하는 work-item 문서 세트(feature-spec/implementation-design/feature-plan/task_execution_plan)의 **인터페이스 정의를 baseline으로 사용**하며, 확정된 아키텍처 결정(로컬 faster-whisper, pyaudiowpatch loopback, PySide6)은 변경하지 않는다.
- 기존 `.todo.md`, `project_board_state.json`을 존중하여 모듈/작업 구조를 깨지 않는다.

## Acceptance Criteria

- **AC-1**: 앱 모듈을 import할 때 오류가 발생하지 않는다(헤드리스 검증 포함).
- **AC-2**: 오디오 장치 enumerate가 예외 없이 동작하고, 장치가 없는 빈 목록 상황도 안전하게 처리된다.
- **AC-3**: 합성 사인파 WAV가 faster-whisper STT 파이프라인을 **1회 통과해 전사 결과를 반환**한다.
- **AC-4**: 녹음 시작 → 실시간 청크 전사 → 정지 → WAV + 전사 파일 저장의 호출 경로가 **코드상 end-to-end로 연결**되어 있다.
- **AC-5**: CUDA 미감지 시 CPU int8 경로로 폴백되며 동일 흐름으로 전사가 동작한다.
- **AC-6**: 저장 경로에 절대경로 하드코딩이 없고 `meetings/` 하위(사용자 홈/문서 또는 앱 폴더 기준)로 해석된다.
- **AC-7**: PyInstaller onedir 빌드 스크립트/스펙이 존재하고 패키징 절차가 문서화되어 있다.
- **AC-8**: 마이크/시스템출력 장치 선택, 모델 크기 선택, 언어 선택, 실시간 자막 패널, 타이머, 레벨 미터, 저장 경로 표시가 UI에 제공된다.
- **AC-9**: 전사·캡처 작업이 워커 스레드/큐로 분리되어 UI 블로킹이 구조적으로 차단된다(코드상 분리 확인).
- **AC-10**: requirements.txt(faster-whisper, pyaudiowpatch, PySide6, numpy, soundfile/scipy 등)와 README(설치/실행/시스템오디오 주의사항)가 존재한다.
- **AC-11**: 각 검증 가능한 작업은 stub-only가 아닌 최소 1개의 실제 실행 경로(비mock) e2e_command를 가진다.

## Evidence

- **verification_focus(완료 검증 기준으로 반영)**:
  - 모듈 import가 오류 없이 성공하는지(헤드리스) → AC-1
  - 오디오 장치 enumerate가 예외 없이 동작하고 빈 목록도 안전 처리하는지 → AC-2
  - 합성 사인파 WAV가 faster-whisper STT 파이프라인을 1회 통과해 전사 결과를 반환하는지 → AC-3
  - 녹음 시작→청크 전사→정지→WAV+전사 저장의 호출 경로가 코드상 end-to-end 연결되는지 → AC-4
  - CUDA 미감지 시 CPU int8 경로로 폴백되는지 → AC-5
  - 저장 경로에 절대경로 하드코딩이 없고 meetings/ 하위로 해석되는지 → AC-6
  - PyInstaller 빌드 스크립트가 존재하고 패키징 절차가 문서화되어 있는지 → AC-7
- **required_capabilities(스킬 조달 신호)**: concurrent_dual_stream_audio_capture, wasapi_loopback_access, local_offline_stt_inference, non_blocking_gui_threading, audio_buffer_vad_chunking, wav_and_transcript_persistence, onedir_native_dll_packaging, headless_synthetic_audio_verification → 위 FR-1~FR-6에 매핑.
- **skill_gap_hypotheses**: 비어 있음 — 신규 스킬 forge 신호 없음. 기존 스킬 reuse/enhance로 충분하다고 판단(추가 검증 시 task_execution_plan에서 확정).
- **research_notes 근거**:
  - pyaudiowpatch는 PyAudio 포크로 WASAPI loopback 공식 지원(`get_default_wasapi_loopback()` 패턴).
  - faster-whisper `transcribe(vad_filter=True, language="ko")`로 내장 Silero VAD 활용.
  - 헤드리스 검증은 numpy 사인파 → 16kHz mono WAV → `model.transcribe` 1회 통과가 표준.
  - 오디오 I/O와 STT 추론을 `queue.Queue`로 분리해 GUI 블로킹 구조적 차단.
- **워크스페이스 신호**: existing_todo=.todo.md, existing_project_board=project_board_state.json, existing_work_items=1.

## References

- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/feature-spec.md | ## Feature Overview
- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/implementation-design.md | ## Design Summary
- Local: docs/task_execution_plan.md | ## Overview
- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/feature-plan.md | ## 목표
- Local: docs/work-items/회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp/feature-plan.md (source plan)

## Out Of Scope

- 클라우드 STT API 연동(OpenAI Whisper API 등) 미지원
- 화자 분리(diarization) 미구현
- macOS/Linux 크로스플랫폼 시스템오디오 캡처 미지원(Windows WASAPI 전용)
- 실시간 번역·요약·회의록 자동 정리 미포함
- 클라우드 동기화·계정·다중 사용자 협업 미포함