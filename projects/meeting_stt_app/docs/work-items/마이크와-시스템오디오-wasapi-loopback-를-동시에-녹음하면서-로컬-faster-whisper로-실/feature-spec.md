# Feature Spec

## Metadata

| 항목 | 값 |
|------|-----|
| work_item | 마이크와-시스템오디오-wasapi-loopback-를-동시에-녹음하면서-로컬-faster-whisper로-실 |
| source_plan | Feature Plan (Draft, 2026-06-13) · role plan 3역할·10모듈·30태스크 |
| status | Draft — 승인 대기 |
| last_updated | 2026-06-13 |
| goal | 마이크와 시스템오디오(WASAPI loopback)를 동시에 녹음하면서 로컬 faster-whisper로 실시간 한국어 자막을 출력하고 종료 시 WAV와 전사 텍스트를 자동 저장하는 PySide6 Windows 데스크톱 앱을 만든다. |
| route | project 파이프라인 / blast_radius=isolated / risk=normal |
| target_path | `D:\warkSpaces\agent-factory\projects\meeting_stt_app` |

---

## Feature Overview

회의 음성을 **외부 클라우드로 전송하지 않고** 오프라인·무료·프라이버시 보장 방식으로 처리하는 Windows 데스크톱 STT 앱이다. 다음 네 가지를 하나의 PySide6 GUI 안에서 제공한다.

- **이중 소스 캡처**: 마이크 입력과 시스템 출력 오디오(WASAPI loopback)를 `pyaudiowpatch`로 각각 스레드 캡처하여, 회의 참석자(마이크)와 원격 화자(스피커 출력)를 모두 녹음한다. 두 소스를 16kHz mono로 리샘플·믹싱하고, 고품질 원본 WAV도 별도 저장한다.
- **실시간 청크 전사**: 롤링 버퍼에 오디오를 누적하고, faster-whisper 내장 `vad_filter`(무음 감지) 또는 최대 길이(10~15초) 도달 시 청크를 **워커 스레드**에서 전사하여 자막 패널에 append한다. UI는 어떤 경우에도 블로킹하지 않는다.
- **로컬 STT 엔진**: faster-whisper 고정. CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`. 모델 크기는 tiny/base/small/medium 중 선택하며 기본값은 `small`. 전사 언어 기본 `ko`, `auto` 옵션 제공.
- **자동 영속화**: 정지 시 원본 WAV·전사 텍스트(.txt/.md)·세션 메타데이터(JSON)를 `meetings/<session>/` 아래에 자동 저장한다. 저장 경로에 절대경로 하드코딩을 금지한다.

마이크 없는 헤드리스/CI 환경에서도 합성 사인파/샘플 WAV로 STT 파이프라인을 1회 통과시키는 셀프테스트를 제공하고, PyInstaller onedir로 ctranslate2 DLL/모델을 포함해 `dist/`에 배포본을 생성한다.

---

## User Scenarios

1. **앱 실행과 장치 인식** — 사용자가 앱을 실행하면 시스템이 오디오 장치를 enumerate하여 마이크·시스템출력 드롭다운을 채운다. loopback 후보가 여럿이면 사용자가 명시적으로 선택할 수 있다.
2. **녹음 시작** — 사용자가 모델 크기·언어를 선택하고 녹음 시작을 클릭하면, 시스템이 마이크+loopback 캡처 스레드를 기동하고 타이머·오디오 레벨 미터 갱신을 시작한다.
3. **실시간 자막** — 롤링 버퍼가 VAD 무음 또는 최대 길이에 도달하면 워커 스레드가 청크를 전사하고, 결과를 TranscriptChunk 단위로 자막 패널에 append한다. 전사 중에도 버튼·미터·타이머 등 UI는 즉시 반응한다.
4. **정지와 저장** — 사용자가 정지를 클릭하면 캡처가 종료되고, `meetings/<session>/`에 WAV·전사 `.txt`/`.md`·세션 JSON이 저장된 뒤 저장 경로가 화면에 표시된다.
5. **헤드리스 셀프테스트** — CI/헤드리스 환경에서 셀프테스트 스크립트를 실행하면, 합성 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는 것으로 장치 비의존 검증이 끝난다.
6. **GPU 부재 fallback** — CUDA/cuDNN이 없거나 버전이 불일치하는 PC에서 앱을 실행하면, device 자동감지가 CPU `int8` 경로로 fallback하여 전사가 계속 동작한다.

---

## Functional Requirements

### FR-1. 이중 소스 오디오 캡처 (`dual_source_audio_capture`, `wasapi_loopback_audio_capture`)
- 마이크 입력과 기본 스피커의 WASAPI loopback을 `pyaudiowpatch`로 **각각 별도 스레드**에서 캡처한다.
- 사용 가능한 마이크·시스템출력 장치를 enumerate하여 선택 가능하게 노출한다.
- loopback 캡처 실패 시 마이크 단독 캡처로 degrade하며, 그 사실을 UI에 표시한다.

### FR-2. 실시간 리샘플·믹싱 (`realtime_resample_and_mix`)
- 두 소스를 모두 16kHz mono로 리샘플(`scipy`)한 뒤 `mix_gain` 기준으로 믹싱한다.
- 고품질 원본 WAV를 믹싱 경로와 별개로 저장한다.
- 버퍼/샘플레이트 드리프트를 보정하여 두 소스의 동기를 유지한다.

### FR-3. STT 엔진 구성 (`faster_whisper_streaming_transcription`, `cuda_cpu_device_autodetect`)
- CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`로 모델을 로드한다.
- 모델 크기는 tiny/base/small/medium 중 선택 가능하며 기본값은 `small`이다.
- GPU 경로 로드 실패 시 CPU `int8`로 자동 fallback한다.

### FR-4. VAD 기반 청크 스트리밍 STT (`vad_chunked_streaming_stt`, `non_blocking_ui_worker_queue`)
- 롤링 버퍼에 오디오를 누적하고, faster-whisper 내장 `vad_filter`(무음 감지) 또는 최대 길이(10~15초) 도달 시 청크를 전사한다.
- 전사는 **별도 워커 스레드/큐**에서 수행하여 PySide6 UI를 절대 블로킹하지 않는다.
- 전사 결과를 TranscriptChunk 단위로 자막 패널에 append한다.
- 전사 언어는 기본 `ko`, `auto` 옵션을 제공한다.

### FR-5. UI 레이어 (`pyside6_gui_development`)
- 녹음 시작/정지 버튼, 마이크·시스템출력 장치 선택 드롭다운, 모델 크기 선택, 언어 선택, 실시간 자막 패널(청크 단위 append), 녹음 타이머, 오디오 레벨 미터, 저장 경로 표시를 제공한다.
- 모든 장시간 작업(캡처·전사)은 메인 스레드 밖에서 처리하여 UI 응답성을 유지한다.

### FR-6. WAV + 전사 영속화 (`session_persistence`, `wav_and_transcript_persistence`)
- 정지 시 원본 녹음 WAV(`meetings/<session>/...wav`)와 전사 텍스트(`.txt` 및/또는 `.md`)를 자동 저장한다.
- 세션 메타데이터(RecordingSession)를 JSON으로 저장한다.
- 저장 경로는 사용자 홈/문서 폴더 또는 앱 실행 폴더 하위 `meetings/`를 사용하며, **절대경로 하드코딩을 금지**한다.

### FR-7. 헤드리스 셀프테스트 (`headless_synthetic_audio_verification`)
- 합성 사인파/샘플 WAV를 STT 파이프라인에 직접 주입하여 장치 enumerate를 우회하는 검증 경로를 제공한다.
- 마이크 없는 CI/헤드리스 환경에서도 1회 전사 성공을 확인할 수 있어야 한다.

### FR-8. 패키징 (`pyinstaller_onedir_packaging`, `onedir_packaging_with_native_dll`)
- PyInstaller onedir spec/스크립트를 제공하고, ctranslate2 DLL과 whisper 모델 가중치를 `binaries`/`datas`에 포함한다.
- 빌드로 `dist/`에 실행 파일을 생성한다.

### FR-9. 의존성·문서 산출물
- `requirements.txt`에 faster-whisper, pyaudiowpatch, PySide6, numpy, soundfile, scipy 등 의존성을 명세한다.
- README에 설치/실행/사용법과 시스템오디오 캡처 주의사항, 패키징 절차를 문서화한다.

**스킬 조달 신호**: required_capabilities 8개(`dual_source_audio_capture`, `realtime_resample_and_mix`, `vad_chunked_streaming_stt`, `non_blocking_ui_worker_queue`, `session_persistence`, `cuda_cpu_device_autodetect`, `onedir_packaging_with_native_dll`, `headless_synthetic_audio_verification`)와 required_skills 8개는 모두 위 FR에 1:1로 매핑된다. skill_gap_hypotheses는 비어 있어 신규 forge 대상 갭은 없다(상세는 Evidence 참조).

---

## Non-Functional Requirements

- **UI 무블로킹**: 전사·캡처 등 장시간 작업은 워커 스레드/큐로 분리하여 메인 UI 스레드를 어떤 경우에도 블로킹하지 않는다.
- **오프라인·프라이버시**: 모든 STT는 로컬에서 수행하며 외부 네트워크로 오디오/전사를 전송하지 않는다.
- **이식성**: 저장 경로·리소스 경로에 절대경로 하드코딩을 금지하고 상대 경로/홈·문서 폴더 기반으로 동작한다.
- **헤드리스 검증성**: 물리 오디오 장치 없이도 import + enumerate + 합성 오디오 1회 전사로 기동·동작을 검증할 수 있다.
- **성능/처리량**: CPU `int8` 환경에서 전사가 청크 길이를 초과해 자막이 누적 지연되지 않도록, 모델 크기 선택(tiny/base)과 청크 길이·vad_filter·워커 큐 backpressure로 조절한다.
- **플랫폼 한정**: Windows 11 / Python 3.11 / WASAPI loopback 전용 (macOS/Linux 비대상).
- **회복력**: loopback 캡처 실패·GPU 로드 실패 시 각각 마이크 단독·CPU int8로 degrade하며 앱이 중단되지 않는다.

---

## Inputs and Outputs

### Inputs
- 오디오 장치 선택(마이크 인덱스, loopback 인덱스), 모델 크기(tiny/base/small/medium), 전사 언어(ko/auto), 녹음 시작/정지 사용자 조작.
- 마이크 PCM 스트림 + WASAPI loopback PCM 스트림(실시간).
- 셀프테스트 입력: 합성 사인파 또는 샘플 WAV.

### Outputs
- 실시간 자막 패널의 청크 단위 전사 텍스트(TranscriptChunk).
- 원본 녹음 WAV 파일(`meetings/<session>/...wav`).
- 전사 텍스트 파일(`.txt` 및/또는 `.md`).
- 세션 메타데이터 JSON(RecordingSession).
- 오디오 레벨 미터·타이머·저장 경로 등 UI 상태 표시.
- `dist/` PyInstaller onedir 배포본.

### Data Model (계약 고정)
- **RecordingSession** (json): `session_id, started_at, ended_at, wav_path, transcript_path, model_size, language, mic_device, loopback_device`
- **TranscriptChunk** (json): `chunk_index, start_time, end_time, text, language, avg_logprob`
- **AudioDeviceConfig** (memory): `mic_index, loopback_index, sample_rate, channels, mix_gain`

---

## Exceptions and Failure Scenarios

| ID | 상황 | 처리 방식 |
|----|------|----------|
| E1 | WASAPI loopback이 기본 스피커를 못 잡음 | loopback 후보를 드롭다운으로 명시 선택, 실패 시 마이크 단독 fallback + UI 알림 |
| E2 | 마이크·시스템오디오 간 샘플레이트·버퍼 드리프트 | 양쪽 16kHz mono 리샘플 통일, 버퍼 큐 길이 보정 + mix_gain 적용 |
| E3 | CPU int8 전사가 청크 길이보다 느려 자막 누적 지연 | tiny/base 모델 선택 제공, 청크 길이·vad_filter 조절, 워커 큐 backpressure |
| E4 | PyInstaller가 ctranslate2 DLL·모델 누락 → 배포본 기동 실패 | spec에 binaries/datas 명시 포함, 빌드 후 dist 스모크 검증 절차 문서화 |
| E5 | CUDA/cuDNN 버전 불일치로 GPU 경로 로드 실패 | device 자동감지 + 예외 시 CPU int8 자동 fallback |
| E6 | 헤드리스 환경에서 장치 enumerate가 빈 목록 반환 | 셀프테스트는 합성 WAV를 STT에 직접 주입, 장치 enumerate 우회 경로 확보 |
| E7 | 저장 디렉터리 부재/권한 문제 | `meetings/<session>/` 생성 시 부모 경로 보장, 실패 시 사용자에게 경로·원인 표시 |

---

## Existing Behavior To Preserve

- 워크스페이스에 이미 존재하는 `feature-spec.md`(FR-4~FR-7), `project_board_state.json`, 3개의 work-item, `.todo.md`와 **충돌 없이 동일 디렉터리에서 확장**한다. 기존 요구사항 골격(FR-4~FR-7)을 단일 출처(SSOT)로 본 spec과 정합하게 유지한다.
- 데이터 모델(RecordingSession / TranscriptChunk / AudioDeviceConfig)과 확정 아키텍처 결정(로컬 faster-whisper 고정, UI 무블로킹, 절대경로 금지, onedir 패키징)을 변경하지 않는다.

---

## Acceptance Criteria

1. **헤드리스 기동**: 앱 모듈을 import할 때 import 오류가 발생하지 않는다. (verification_focus: 모듈 import 성공)
2. **장치 enumerate**: 오디오 장치 enumerate가 예외 없이 동작하며, 장치가 없는 환경에서도 빈 목록을 정상 반환하고 앱이 죽지 않는다. (verification_focus: enumerate 무예외)
3. **합성 오디오 전사**: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과하여 전사 텍스트(빈 문자열이 아닌 결과 객체)를 반환한다. (verification_focus: 합성 WAV 1회 전사 성공)
4. **end-to-end 연결**: 녹음 시작 → 청크 전사 → 정지 → WAV + 전사 파일 저장의 흐름이 코드상 end-to-end로 연결되어 있다(시작 핸들러 → 캡처 스레드 → 워커 큐 → 자막 append → 정지 핸들러 → 영속화 호출까지 추적 가능). (verification_focus: end-to-end 코드 연결)
5. **경로 위생**: 저장 경로에 `C:\`, `/Users/`, `/home/` 등 절대경로 하드코딩이 없고, `meetings/` 상대 경로(또는 홈/문서 폴더 기반)를 사용한다. (verification_focus: 절대경로 하드코딩 부재)
6. **패키징 구성**: PyInstaller spec이 ctranslate2 DLL과 whisper 모델을 `binaries`/`datas`에 포함하도록 구성되어 있고, 빌드로 `dist/`에 실행 파일이 생성된다. 패키징 절차가 README에 문서화되어 있다. (verification_focus: 패키징 spec DLL·모델 포함)
7. **UI 무블로킹**: 전사 워커가 별도 스레드/큐로 분리되어 있어, 전사 수행 중에도 메인 UI 스레드가 블로킹되지 않음이 코드 구조상 보장된다.
8. **device 자동분기**: CUDA 감지 시 GPU(float16), 미감지 또는 GPU 로드 실패 시 CPU int8로 분기/​fallback하는 코드 경로가 존재한다.

---

## Evidence

### 근거 (source-backed claims)
- **FR-5 STT 엔진**: CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`, 기본 모델 `small` — `feature-spec.md`.
- **FR-7 영속화**: 정지 시 `meetings/<session>/...wav`와 전사 `.txt`/`.md` 자동 저장 — `feature-spec.md`.
- **FR-6 UI**: 시작/정지·장치 드롭다운·모델·언어 선택·실시간 자막 패널·타이머·레벨 미터·저장 경로 표시 — `feature-spec.md`.
- **FR-4 VAD 청크 스트리밍**: 롤링 버퍼 + `vad_filter` 또는 10~15초 최대 길이로 청크 전사, 기본 `ko`/`auto` 옵션 — `feature-spec.md`.

### 검증 기준 (verification_focus)
구현 검증 시 다음 6개 항목을 명시적으로 통과시킨다 (Acceptance Criteria 1~6에 직접 매핑):
1. 모듈 import가 오류 없이 성공하는지 (헤드리스 기동).
2. 오디오 장치 enumerate가 예외 없이 동작하는지.
3. 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지.
4. 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지.
5. 저장 경로에 절대경로 하드코딩이 없는지 (`meetings/` 상대 경로 사용).
6. PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지.

### 스킬 조달 신호 (reuse/enhance/forge)
- **skill_gap_hypotheses는 비어 있음** — 신규 forge 대상 갭은 식별되지 않았다.
- required_skills 8개(`pyside6_gui_development`, `wasapi_loopback_audio_capture`, `realtime_audio_buffering_and_resampling`, `faster_whisper_streaming_transcription`, `thread_safe_worker_queue`, `wav_and_transcript_persistence`, `pyinstaller_onedir_packaging`, `headless_synthetic_audio_selftest`)는 모두 기존 역량 **reuse/enhance** 범위로 처리하며, 별도 forge 절차 없이 모듈 구현(FR-1~FR-9)으로 흡수한다.
- required_capabilities 8개는 각 FR에 1:1 매핑되어 누락 없이 커버된다.

---

## References

- `docs/work-items/마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시/feature-spec.md` — FR-4(VAD 청크 스트리밍), FR-5(STT 엔진), FR-6(UI 레이어), FR-7(영속화), Feature Overview, Outputs
- `project_board_state.json` — 기존 프로젝트 보드 상태
- `.todo.md` — 기존 todo
- 기존 work-items 3건 — 요구사항 골격
- Feature Plan (Draft, 2026-06-13) — 본 spec의 상위 계획(3역할·10모듈·30태스크)
- Tech stack: Python 3.11 · PySide6(Qt6) · faster-whisper(ctranslate2) · pyaudiowpatch(WASAPI loopback) · numpy · soundfile · scipy(resample) · PyInstaller(onedir)

---

## Out Of Scope

- 클라우드/온라인 STT API 연동 (오프라인 로컬 전용)
- macOS/Linux 지원 (Windows WASAPI loopback 전용)
- 화자 분리(speaker diarization)
- 회의 요약·번역 등 후처리 NLP 기능
- 실시간 스트리밍 자막의 단어 단위 부분 결과(partial token) 표시