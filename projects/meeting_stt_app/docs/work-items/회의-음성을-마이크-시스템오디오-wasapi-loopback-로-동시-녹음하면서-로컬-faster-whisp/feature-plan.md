# Feature Plan

## Metadata

- work_item: 회의-음성을-마이크-시스템오디오-wasapi-loopback-로-동시-녹음하면서-로컬-faster-whisp
- owner: (edit required)
- status: draft
- last_updated: 2026-06-13T06:24:42

## Background

원격·대면 회의가 일상화되면서 음성을 텍스트로 남기는 수요는 크지만, 클라우드 STT는 프라이버시·비용·인터넷 의존성 문제가 있다. 워크스페이스에는 이미 feature-spec/implementation-design/task_execution_plan 등 work-item 문서 세트가 준비되어 있어 아키텍처 결정(로컬 faster-whisper, pyaudiowpatch loopback, PySide6)이 확정된 상태에서 구현 단계로 진입한다.

## Problem Statement

기존 STT 도구는 마이크 단일 채널만 받아 상대방(시스템 출력) 음성을 놓치거나, 클라우드 전송으로 민감한 회의 내용이 외부로 나가며, 실시간 자막과 고품질 원본 녹음을 동시에 제공하지 못한다. 마이크와 시스템 스피커 loopback을 동시에 캡처해 오프라인으로 실시간 전사하면서 UI를 블로킹하지 않는 구현이 핵심 난제다.

## Goals

- 실행 가능한 PySide6 회의록 STT 데스크톱 앱
- 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진
- faster-whisper 실시간 청크 전사 워커
- 실시간 자막 패널·장치 선택·레벨 미터 UI
- WAV + 전사(.txt/.md) 자동 저장 모듈
- requirements.txt 의존성 명세
- 설치/실행/시스템오디오 주의사항 README
- PyInstaller onedir 빌드 스크립트/스펙
- 합성 오디오 헤드리스 셀프테스트 스크립트

## Non-Goals

- 클라우드 STT API 연동(OpenAI Whisper API 등) 미지원
- 화자 분리(diarization) 미구현
- macOS/Linux 크로스플랫폼 시스템오디오 캡처 미지원 (Windows WASAPI 전용)
- 실시간 번역·요약·회의록 자동 정리 미포함
- 클라우드 동기화·계정·다중 사용자 협업 미포함

## Scope

- **실행 가능한 PySide6 회의록 STT 데스크톱 앱**: 실행 가능한 PySide6 회의록 STT 데스크톱 앱을(를) 구현한다.
- **마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진**: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진을(를) 구현한다.
- **faster-whisper 실시간 청크 전사 워커**: faster-whisper 실시간 청크 전사 워커을(를) 구현한다.
- **실시간 자막 패널·장치 선택·레벨 미터 UI**: 실시간 자막 패널·장치 선택·레벨 미터 UI을(를) 구현한다.
- **WAV + 전사 자동 저장 모듈**: WAV + 전사(.txt/.md) 자동 저장 모듈을(를) 구현한다.
- **requirements.txt 의존성 명세**: requirements.txt 의존성 명세을(를) 구현한다.
- **시스템오디오 주의사항 README**: 설치/실행/시스템오디오 주의사항 README을(를) 구현한다.
- **스펙**: PyInstaller onedir 빌드 스크립트/스펙을(를) 구현한다.
- **합성 오디오 헤드리스 셀프테스트 스크립트**: 합성 오디오 헤드리스 셀프테스트 스크립트을(를) 구현한다.
- **Backend Dev 구현**: 서버, 데이터, 외부 연동 레이어를 구현한다.
- **Product Designer 구현**: 정보 구조와 화면 흐름, 비주얼 방향을 설계한다.

## Stakeholders

- Frontend Dev: 사용자 화면과 상호작용 레이어를 구현한다.
- Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다.
- Product Designer: 정보 구조와 화면 흐름, 비주얼 방향을 설계한다.
- QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다.

## Success Metrics

- 실행 가능한 PySide6 회의록 STT 데스크톱 앱 — 완성 및 동작 검증됨
- 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진 — 완성 및 동작 검증됨
- faster-whisper 실시간 청크 전사 워커 — 완성 및 동작 검증됨
- 실시간 자막 패널·장치 선택·레벨 미터 UI — 완성 및 동작 검증됨
- WAV + 전사(.txt/.md) 자동 저장 모듈 — 완성 및 동작 검증됨
- requirements.txt 의존성 명세 — 완성 및 동작 검증됨
- 설치/실행/시스템오디오 주의사항 README — 완성 및 동작 검증됨
- PyInstaller onedir 빌드 스크립트/스펙 — 완성 및 동작 검증됨
- 합성 오디오 헤드리스 셀프테스트 스크립트 — 완성 및 동작 검증됨

## Risks and Assumptions

- pyaudiowpatch WASAPI loopback이 기본 스피커 변경·장치 미존재 시 실패할 수 있음
- faster-whisper 모델 다운로드(small ~500MB) 첫 실행 지연 및 오프라인 환경 캐시 부재
- 마이크/시스템 두 스트림의 샘플레이트·버퍼 드리프트로 믹싱 동기 어긋남
- CUDA/cuDNN 버전 불일치로 GPU 경로 로드 실패 → CPU 폴백 검증 필요
- PyInstaller가 ctranslate2/onnxruntime 네이티브 DLL과 모델을 누락하면 빌드 실행 실패
- 실시간 청크 경계에서 단어가 잘려 전사 정확도 저하
- CI/헤드리스 환경에 오디오 장치가 없어 enumerate가 빈 목록 반환

## Evidence

- Workspace note: existing_todo=.todo.md
- Workspace note: existing_project_board=project_board_state.json
- Workspace note: existing_work_items=1
- Local reference: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/feature-spec.md -> ## Feature Overview Windows 데스크톱 실시간 회의록 STT 앱을 개발한다.
- Local reference: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/implementation-design.md -> ## Design Summary Windows 데스크톱 실시간 회의록 STT 앱을 개발한다.
- Local reference: docs/task_execution_plan.md -> ## Overview - project_goal: Windows 데스크톱 실시간 회의록 STT 앱을 개발한다.
- Skill procurement signals (not acceptance criteria):
  - concurrent_dual_stream_audio_capture
  - wasapi_loopback_access
  - local_offline_stt_inference
  - non_blocking_gui_threading
  - audio_buffer_vad_chunking
  - wav_and_transcript_persistence
- Verification focus (also injected into task acceptance):
  - 모듈 import가 오류 없이 성공하는지(헤드리스)
  - 오디오 장치 enumerate가 예외 없이 동작하고 빈 목록도 안전 처리하는지
  - 합성 사인파 WAV가 faster-whisper STT 파이프라인을 1회 통과해 전사 결과를 반환하는지
  - 녹음 시작→청크 전사→정지→WAV+전사 저장의 호출 경로가 코드상 end-to-end 연결되는지
  - CUDA 미감지 시 CPU int8 경로로 폴백되는지
  - 저장 경로에 절대경로 하드코딩이 없고 meetings/ 하위로 해석되는지
  - PyInstaller 빌드 스크립트가 존재하고 패키징 절차가 문서화되어 있는지

## References

- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/feature-spec.md | ## Feature Overview
- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/implementation-design.md | ## Design Summary
- Local: docs/task_execution_plan.md | ## Overview
- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/feature-plan.md | ## 목표
- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/feature-spec.md | ## 목표
- Local: docs/work-items/windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동/implementation-design.md | ## 목표

## Approval Request

- Review this scope and confirm approval-gate.md when ready.


<!-- af:status=needs_human_review -->

## Episode Hints

_과거 유사 프로젝트에서 학습된 주의사항:_

- stub-only 테스트는 실제 기능 존재를 보장하지 않는다 — e2e_command 필수
- e2e_command가 `needs_backfill`인 태스크는 PASS 처리 불가
- 테스트 작성 시 최소 1개의 실제 실행 경로(비mock)를 포함해야 한다
- approval-gate `status=completed` = 파일 존재 + 금지토큰 0 + e2e exit 0 모두 충족
