# Feature Plan

## Metadata

- work_item: windows-데스크톱-실시간-회의록-stt-앱을-개발한다-목표-회의-음성을-고품질로-녹음하면서-동
- owner: (edit required)
- status: draft
- last_updated: 2026-06-13T06:21:51

## Background

Windows 데스크톱 실시간 회의록 STT 앱을 개발한다.

## 목표
회의 음성을 고품질로 녹음하면서 동시에 실시간으로 한국어 자막(전사)을 화면에 출력하고, 종료 시 음성(WAV)과 전사 텍스트(.txt/.md)를 자동 저장하는 Windows 데스크톱 애플리케이션.

## 확정된 아키텍처 결정 (변경 금지)
1. STT 엔진: 로컬 faster-whisper (오프라인, 무료, 프라이버시). CUDA 감지 시 device=cuda/compute_type=float16, 없으면 CPU int8. 모델 크기 선택 가능(tiny/base/small/medium), 기본 small.
2. 오디오 캡처: 마이크 + 시스템오디오(WASAPI loopback)를 동시에 캡처한다. pyaudiowpatch 라이브러리로 마이크 입력과 기본 스피커의 loopback을 각각 스레드로 받아 16kHz mono로 리샘플 후 믹싱한다. 고품질 원본 WAV도 저장한다.
3. 전사 언어: 한국어 우선 + 자동감지(language="ko" 기본, auto 옵션 제공).
4. UI: PySide6 데스크톱 GUI. 녹음 시작/정지 버튼, 마이크/시스템출력 장치 선택 드롭다운, 모델 크기 선택, 실시간 자막 패널(청크 단위 append), 녹음 타이머, 오디오 레벨 미터, 저장 경로 표시.

## 실시간 전사 방식
오디오를 롤링 버퍼에 누적하고, VAD(무음 감지) 또는 최대 길이(예: 10~15초)에 도달하면 청크를 워커 스레드에서 faster-whisper로 전사하여 자막 패널에 append한다. faster-whisper 내장 VAD 필터 사용. UI는 절대 블로킹하지 않는다(전사는 별도 스레드/큐).

## 산출물
- 실행 가능한 PySide6 앱 (예: app/main.py 또는 패키지 구조)
- requirements.txt (faster-whisper, pyaudiowpatch, PySide6, numpy, soundfile/scipy 등)
- README.md (설치/실행/사용법, 시스템오디오 캡처 주의사항)
- PyInstaller 패키징 스펙/스크립트 (단일 폴더 onedir 배포 — ctranslate2 DLL/모델 포함). 빌드로 dist/ 에 실행 파일 생성.

## 완료 기준
- 앱이 import 오류 없이 기동된다 (헤드리스 검증: 모듈 import + 오디오 장치 enumerate + 합성 오디오로 STT 파이프라인 1회 전사 성공).
- 녹음 시작 → 실시간 자막 출력 → 정지 → WAV + 전사 파일 저장의 전체 흐름이 코드상 연결되어 있다.
- PyInstaller 빌드 스크립트가 존재하고 패키징 절차가 문서화되어 있다.

## 비고
- 마이크가 없는 CI/헤드리스 환경에서도 검증 가능하도록, 합성 사인파/샘플 WAV를 STT에 통과시키는 셀프테스트 스크립트를 포함한다.
- 절대경로 하드코딩 금지. 저장 경로는 사용자 홈/문서 폴더 또는 앱 실행 폴더 하위 meetings/ 로 한다.

## Problem Statement

(edit required)

## Goals

- working implementation output

## Non-Goals

- (edit required)

## Scope

- **working implementation output**: working implementation output을(를) 구현한다.
- **Backend Dev 구현**: 서버, 데이터, 외부 연동 레이어를 구현한다.
- **QA Engineer 검증**: 핵심 플로우와 회귀 시나리오를 검증한다.

## Stakeholders

- Frontend Dev: 사용자 화면과 상호작용 레이어를 구현한다.
- Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다.
- QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다.

## Success Metrics

- working implementation output — 완성 및 동작 검증됨

## Risks and Assumptions

- data model integrity

## Evidence

- Local reference: docs/change_history.md -> # Change History Append one new entry per design, architecture, workflow, or implementation-strategy update.
- Local reference: docs/change_history.md -> ### 2026-06-13T06:21:39 - Summary: Documentation contract initialized. - Reason: Preserve architecture and workflow changes in a stable project history. - Affected files: `docs/architecture.md`, `docs/change_history.md` - Follow-up: Keep this file append-on...
- Local reference: docs/architecture.md -> ## Documentation Rule - When the design changes, update this file in the same task. - Append the matching entry to `docs/change_history.md` before closing the task. - All generated or updated documents in this repository must use the language that matches O...

## References

- Local: docs/change_history.md | # Change History
- Local: docs/change_history.md | ### 2026-06-13T06:21:39
- Local: docs/architecture.md | ## Documentation Rule

## Approval Request

- Review this scope and confirm approval-gate.md when ready.


<!-- af:status=needs_human_review -->

## Episode Hints

_과거 유사 프로젝트에서 학습된 주의사항:_

- stub-only 테스트는 실제 기능 존재를 보장하지 않는다 — e2e_command 필수
- e2e_command가 `needs_backfill`인 태스크는 PASS 처리 불가
- 테스트 작성 시 최소 1개의 실제 실행 경로(비mock)를 포함해야 한다
- approval-gate `status=completed` = 파일 존재 + 금지토큰 0 + e2e exit 0 모두 충족
