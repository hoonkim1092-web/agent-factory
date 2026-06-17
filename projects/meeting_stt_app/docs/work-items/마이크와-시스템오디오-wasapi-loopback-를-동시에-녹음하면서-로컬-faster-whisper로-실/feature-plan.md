# Feature Plan

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | 마이크와-시스템오디오-wasapi-loopback-를-동시에-녹음하면서-로컬-faster-whisper로-실 |
| owner | Frontend Dev (주관) · Backend Dev · QA Engineer |
| status | Draft — 승인 대기 |
| last_updated | 2026-06-13 |
| route | project 파이프라인 / blast_radius=isolated / risk=normal |
| target_path | `D:\warkSpaces\agent-factory\projects\meeting_stt_app` |

---

## Background

회의 음성을 외부 클라우드 STT로 전송하지 않고 **오프라인·무료·프라이버시 보장** 방식으로 처리하려는 수요가 있다. 기존 회의 녹취 도구는 마이크 한쪽만 잡거나, 클라우드 전송이 필수이거나, 실시간 자막이 UI를 블로킹하는 한계를 가진다.

워크스페이스에는 이미 요구사항 골격이 확정되어 있다 — `feature-spec.md`(FR-4~FR-7), `project_board_state.json`, 3개의 work-item, `.todo.md`가 존재한다. 본 계획은 그 골격을 실행 가능한 PySide6 데스크톱 앱으로 구현하는 단계를 정의한다.

이 work item이 요구하는 핵심 역량(required_capabilities)은 다음과 같으며, 각 역량이 모듈/산출물로 1:1 매핑되어 Scope에 반영된다:
- `dual_source_audio_capture` — 마이크 + WASAPI loopback 동시 캡처
- `realtime_resample_and_mix` — 16kHz mono 리샘플 후 믹싱
- `vad_chunked_streaming_stt` — VAD/최대길이 기반 청크 전사
- `non_blocking_ui_worker_queue` — 워커 스레드/큐로 UI 무블로킹
- `session_persistence` — WAV·전사·세션 JSON 영속화
- `cuda_cpu_device_autodetect` — GPU/CPU 자동 분기
- `onedir_packaging_with_native_dll` — ctranslate2 DLL/모델 포함 패키징
- `headless_synthetic_audio_verification` — 합성 오디오 셀프테스트

---

## Problem Statement

마이크 입력과 시스템 출력 오디오(WASAPI loopback)를 **동시에** 캡처하면서, 워커 스레드 기반 청크 전사로 **UI를 절대 블로킹하지 않는** 실시간 한국어 자막을 **로컬에서** 구현하는 것이 핵심 난제다.

세부 난점:
- 두 오디오 소스 간 샘플레이트·버퍼 드리프트로 믹싱 동기가 어긋날 수 있다.
- CPU int8 환경에서 small 모델 전사가 청크 길이보다 느리면 자막이 누적 지연된다.
- 일부 드라이버/장치 구성에서 loopback이 기본 스피커를 잡지 못할 수 있다.
- 헤드리스/CI 환경에는 물리 오디오 장치가 없어 장치 의존 코드가 검증 경로를 막는다.

---

## Goals

1. 마이크와 시스템오디오(WASAPI loopback)를 동시에 녹음하면서 로컬 faster-whisper로 실시간 한국어 자막을 출력하고, 종료 시 WAV와 전사 텍스트를 자동 저장하는 PySide6 Windows 데스크톱 앱을 만든다.
2. 전사를 별도 워커 스레드/큐로 분리해 PySide6 UI를 어떤 경우에도 블로킹하지 않는다.
3. CUDA 감지 시 GPU(float16), 미감지 시 CPU(int8)로 자동 분기하고 모델 크기(tiny/base/small/medium, 기본 small)를 선택 가능하게 한다.
4. 마이크 없는 헤드리스/CI 환경에서도 합성 사인파/샘플 WAV로 STT 파이프라인을 1회 통과시키는 셀프테스트를 제공한다.
5. PyInstaller onedir로 ctranslate2 DLL/모델을 포함해 `dist/`에 배포본을 생성하고, 패키징 절차를 문서화한다.

---

## Non-Goals

- 클라우드/온라인 STT API 연동 (오프라인 로컬 전용)
- macOS/Linux 지원 (Windows WASAPI loopback 전용)
- 화자 분리(speaker diarization)
- 회의 요약·번역 등 후처리 NLP 기능
- 실시간 스트리밍 자막의 단어 단위 부분 결과(partial token) 표시

---

## Scope

역할 계획(role plan)에 따라 3개 역할 · 10개 모듈 · 30개 태스크(scope→build→verify)로 분해된다. 각 모듈은 산출물 단위로 분리되며 모든 태스크가 `owner_role`과 `depends_on`을 가진다.

### 포함 범위 (모듈 → 산출물)

| 모듈 | 산출물 | owner |
|------|--------|-------|
| frontend_dev_module_1 | 실행 가능한 PySide6 회의록 STT 데스크톱 앱 (예: `app/main.py` 또는 패키지 구조) | Frontend Dev |
| frontend_dev_module_2 | 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진 (`dual_source_audio_capture`, `realtime_resample_and_mix`) | Frontend Dev |
| frontend_dev_module_3 | faster-whisper 실시간 청크 전사 워커 (`vad_chunked_streaming_stt`, `non_blocking_ui_worker_queue`) | Frontend Dev |
| frontend_dev_module_4 | 실시간 자막 패널·장치 선택·레벨 미터 UI (`pyside6_gui_development`) | Frontend Dev |
| frontend_dev_module_5 | WAV + 전사 텍스트(.txt/.md) + 세션 메타데이터 영속화 모듈 (`session_persistence`) | Frontend Dev |
| qa_engineer_module_6 | 합성 오디오 헤드리스 셀프테스트 스크립트 (`headless_synthetic_audio_verification`) | QA Engineer |
| frontend_dev_module_7 | requirements.txt 의존성 명세 | Frontend Dev |
| frontend_dev_module_8 | PyInstaller onedir 빌드 스펙/스크립트 (`onedir_packaging_with_native_dll`) | Frontend Dev |
| frontend_dev_module_9 | 설치·실행·시스템오디오 캡처 주의사항 README | Frontend Dev |
| backend_dev_module_10 | 오디오/디바이스 외부 연동 레이어 (`wasapi_loopback_audio_capture`, `cuda_cpu_device_autodetect`) | Backend Dev |

### 데이터 모델 (계약 고정)

- **RecordingSession** (json): `session_id, started_at, ended_at, wav_path, transcript_path, model_size, language, mic_device, loopback_device`
- **TranscriptChunk** (json): `chunk_index, start_time, end_time, text, language, avg_logprob`
- **AudioDeviceConfig** (memory): `mic_index, loopback_index, sample_rate, channels, mix_gain`

### 제약 (변경 금지)

- STT 엔진은 로컬 faster-whisper 고정 — CUDA 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`.
- 모델 크기 tiny/base/small/medium 선택, 기본 `small`.
- pyaudiowpatch로 마이크·loopback 각각 스레드 캡처 → 16kHz mono 리샘플·믹싱, 고품질 원본 WAV 별도 저장.
- 전사는 별도 워커 스레드/큐 — PySide6 UI 절대 블로킹 금지.
- 전사 언어 기본 `ko`, `auto` 옵션 제공, faster-whisper 내장 `vad_filter` 사용.
- 절대경로 하드코딩 금지 — 저장 경로는 사용자 홈/문서 폴더 또는 앱 실행 폴더 하위 `meetings/`.
- 헤드리스/CI에서 합성 사인파/샘플 WAV로 셀프테스트 가능해야 함.
- PyInstaller onedir로 ctranslate2 DLL/모델 포함, `dist/`에 실행 파일 생성.

### 실행 전략

`parallel` — 모듈 간 의존이 낮아 병렬 진행하되, 각 모듈 내부는 `scope → build → verify` 순서를 유지한다. 통합 시점에 오디오 엔진(모듈2)·전사 워커(모듈3)·영속화(모듈5)가 UI(모듈4)에 합류하고, 셀프테스트(모듈6)가 end-to-end 연결을 검증한다.

---

## Stakeholders

| 역할 | 책임 | 소유 모듈 |
|------|------|----------|
| Frontend Dev | 앱 셸·오디오 엔진·전사 워커·UI·영속화·의존성·패키징·README 구현 | module 1·2·3·4·5·7·8·9 |
| Backend Dev | 디바이스/네이티브 연동 레이어 (WASAPI loopback 캡처, 디바이스 자동감지) | module 10 |
| QA Engineer | 헤드리스 합성 오디오 셀프테스트 및 회귀 시나리오 검증 | module 6 |
| PD (Lilith Bootstrap) | 계획 승인·핸드오프 조율 | — |

---

## Success Metrics

완료 기준(완료 시 모두 충족):

1. **헤드리스 기동**: 앱이 import 오류 없이 기동된다 — 모듈 import + 오디오 장치 enumerate + 합성 오디오로 STT 파이프라인 1회 전사 성공.
2. **end-to-end 흐름 연결**: 녹음 시작 → 실시간 자막 출력 → 정지 → WAV + 전사 파일 저장 전체 흐름이 코드상 연결되어 있다.
3. **패키징 문서화**: PyInstaller onedir 빌드 스크립트가 존재하고 패키징 절차가 README에 문서화되어 있다.
4. **장치 비의존 검증**: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환한다 (마이크 없는 환경에서도 통과).
5. **경로 위생**: 저장 경로에 절대경로 하드코딩이 없다 — `meetings/` 상대 경로 사용.

---

## Risks and Assumptions

### Risks

| ID | 리스크 | 완화책 |
|----|--------|--------|
| R1 | pyaudiowpatch WASAPI loopback이 일부 드라이버/장치 구성에서 기본 스피커를 못 잡음 | 장치 enumerate 시 loopback 후보 명시 선택 드롭다운 제공, 실패 시 마이크 단독 fallback |
| R2 | 마이크·시스템오디오 간 샘플레이트·버퍼 드리프트로 믹싱 동기 어긋남 | 양쪽 16kHz mono로 리샘플 통일, 버퍼 큐 길이 보정·믹싱 게인(mix_gain) 적용 |
| R3 | small 모델 CPU int8 전사가 청크 길이보다 느려 자막 누적 지연 | 모델 크기 선택(tiny/base) 제공, 청크 길이 10~15초 + vad_filter로 처리량 조절, 워커 큐 backpressure |
| R4 | PyInstaller가 ctranslate2 DLL·모델 가중치를 누락해 배포본 기동 실패 | spec에 binaries/datas 명시 포함, 빌드 후 dist 기동 스모크 검증 절차 문서화 |
| R5 | CUDA/cuDNN 버전 불일치로 GPU 경로 로드 실패 | device 자동감지 + 예외 시 CPU int8 자동 fallback 검증 |
| R6 | 헤드리스 환경에서 장치 enumerate가 빈 목록 반환 → 셀프테스트가 장치 의존 코드에서 실패 | 셀프테스트는 합성 WAV를 STT에 직접 주입, 장치 enumerate 우회 경로 확보 |

### Assumptions

- 대상 OS는 Windows 11, Python 3.11 환경이다.
- faster-whisper 모델 가중치는 최초 실행/빌드 시 확보 가능하다(다운로드 또는 동봉).
- `feature-spec.md` FR-4~FR-7이 요구사항의 단일 출처(SSOT)이며 본 계획과 정합한다.
- 워크스페이스 기존 산출물(`.todo.md`, `project_board_state.json`, 3 work-items)과 충돌 없이 동일 디렉터리에서 확장한다.

---

## Evidence

### 근거 (source-backed claims)

- **FR-5 STT 엔진**: CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`, 기본 모델 `small` — `feature-spec.md`.
- **FR-7 영속화**: 정지 시 `meetings/<session>/...wav`와 전사 `.txt`/`.md` 자동 저장 — `feature-spec.md`.
- **FR-6 UI**: 시작/정지·장치 드롭다운·모델·언어 선택·실시간 자막 패널·타이머·레벨 미터·저장 경로 표시 — `feature-spec.md`.
- **FR-4 VAD 청크 스트리밍**: 롤링 버퍼 + `vad_filter` 또는 10~15초 최대 길이로 청크 전사, 기본 `ko`/`auto` 옵션 — `feature-spec.md`.

### 검증 기준 (verification_focus)

구현 검증 시 다음 항목을 명시적으로 통과시킨다:
1. 모듈 import가 오류 없이 성공하는지 (헤드리스 기동).
2. 오디오 장치 enumerate가 예외 없이 동작하는지.
3. 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지.
4. 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지.
5. 저장 경로에 절대경로 하드코딩이 없는지 (`meetings/` 상대 경로 사용).
6. PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지.

### 스킬 조달 신호 (skill_gap_hypotheses)

- skill_gap_hypotheses는 비어 있음 — 신규 forge 대상 갭은 식별되지 않았다.
- required_skills(pyside6_gui_development, wasapi_loopback_audio_capture, realtime_audio_buffering_and_resampling, faster_whisper_streaming_transcription, thread_safe_worker_queue, wav_and_transcript_persistence, pyinstaller_onedir_packaging, headless_synthetic_audio_selftest)은 모두 기존 역량 **reuse/enhance** 범위로 처리하며, 별도 forge 절차 없이 모듈 구현으로 흡수한다.

---

## References

- `docs/work-items/마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시/feature-spec.md` — FR-4(VAD 청크 스트리밍), FR-5(STT 엔진), FR-6(UI 레이어), FR-7(영속화), Feature Overview, Outputs
- `project_board_state.json` — 기존 프로젝트 보드 상태
- `.todo.md` — 기존 todo
- 기존 work-items 3건 — 요구사항 골격
- Tech stack: Python 3.11 · PySide6(Qt6) · faster-whisper(ctranslate2) · pyaudiowpatch(WASAPI loopback) · numpy · soundfile · scipy(resample) · PyInstaller(onedir)

---

## Approval Request

본 Feature Plan은 `feature-spec.md`(FR-4~FR-7)와 확정 아키텍처 결정을 그대로 반영했으며, 3개 역할 · 10개 모듈 · 30개 태스크로 분해된 병렬 실행 계획입니다. 데이터 모델(RecordingSession / TranscriptChunk / AudioDeviceConfig)과 제약(로컬 faster-whisper 고정, UI 무블로킹, 절대경로 금지, onedir 패키징)을 계약으로 동결했습니다.

다음 사항에 대한 승인을 요청합니다:

1. **Scope 확정** — 위 10개 모듈/산출물 경계와 Non-Goals(클라우드 STT·타 OS·화자분리·후처리 NLP·partial token 제외).
2. **Success Metrics 채택** — 5개 완료 기준(헤드리스 기동·end-to-end 연결·패키징 문서화·장치 비의존 셀프테스트·경로 위생)을 done 정의로 사용.
3. **실행 전략** — 모듈 병렬 진행, 각 모듈 내부 scope→build→verify 순서, 통합 후 셀프테스트로 end-to-end 검증.

승인 시 `scope` 단계 태스크부터 착수하며, 미승인 항목이 있으면 해당 모듈 경계 또는 완료 기준을 조정한 뒤 재제출합니다.