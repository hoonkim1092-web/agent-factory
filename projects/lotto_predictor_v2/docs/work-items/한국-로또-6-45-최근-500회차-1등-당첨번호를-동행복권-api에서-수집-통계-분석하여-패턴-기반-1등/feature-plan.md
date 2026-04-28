# Feature Plan

## Metadata

- work_item: 한국-로또-6-45-최근-500회차-1등-당첨번호를-동행복권-api에서-수집-통계-분석하여-패턴-기반-1등
- owner: (edit required)
- status: draft
- last_updated: 2026-04-17T01:24:58

## Background

개인 사용자가 로또 번호 추천을 받기 위해 매번 웹사이트를 방문하거나 수작업으로 통계를 계산하는 불편이 존재한다. 동행복권이 공식적으로 제공하는 회차별 당첨번호 JSON 엔드포인트(`lottery.go.kr/common.do?method=getLottoNumber&drwNo=N`)를 활용하면 공인된 데이터로 통계 분석이 가능하다. 또한 Python 환경이 없는 사용자도 쓸 수 있도록 PyInstaller onefile 번들이 요구된다.

## Problem Statement

공식 회차 데이터의 산재성과 Python 런타임 미설치 환경이라는 두 장벽 때문에, 비개발자 사용자가 최근 500회차 통계에 근거한 번호 조합을 즉시 얻지 못하는 접근성 공백이 있다.

## Goals

- 동행복권 회차 수집기 모듈
- 회차 데이터 로컬 캐시 저장소
- 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)
- 패턴 기반 번호 조합 추천기
- 터미널 포맷 출력 리포트
- PyInstaller 빌드 스펙 및 산출물
- 사용자 실행 가이드 문서

## Non-Goals

- 2등 이하 등수 예측 및 보너스 번호 예측
- 머신러닝/딥러닝 기반 시계열 예측 모델 도입
- GUI(윈도우 창) 인터페이스 제공
- 웹 서비스·모바일 앱 배포
- 실시간 구매 자동화 또는 결제 연동
- 당첨 보장성 주장 또는 확률 조작

## Scope

- **동행복권 회차 수집기 모듈**: 동행복권 회차 수집기 모듈을(를) 구현한다.
- **회차 데이터 로컬 캐시 저장소**: 회차 데이터 로컬 캐시 저장소을(를) 구현한다.
- **통계 분석 엔진**: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)을(를) 구현한다.
- **패턴 기반 번호 조합 추천기**: 패턴 기반 번호 조합 추천기을(를) 구현한다.
- **터미널 포맷 출력 리포트**: 터미널 포맷 출력 리포트을(를) 구현한다.
- **PyInstaller 빌드 스펙 및 산출물**: PyInstaller 빌드 스펙 및 산출물을(를) 구현한다.
- **사용자 실행 가이드 문서**: 사용자 실행 가이드 문서을(를) 구현한다.
- **Backend Dev 구현**: 서버, 데이터, 외부 연동 레이어를 구현한다.
- **Game Logic Dev 구현**: 핵심 규칙과 상태 전이를 구현한다.
- **QA Engineer 검증**: 핵심 플로우와 회귀 시나리오를 검증한다.

## Stakeholders

- Frontend Dev: 사용자 화면과 상호작용 레이어를 구현한다.
- Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다.
- Game Logic Dev: 핵심 규칙과 상태 전이를 구현한다.
- QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다.

## Success Metrics

- 동행복권 회차 수집기 모듈 — 완성 및 동작 검증됨
- 회차 데이터 로컬 캐시 저장소 — 완성 및 동작 검증됨
- 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드) — 완성 및 동작 검증됨
- 패턴 기반 번호 조합 추천기 — 완성 및 동작 검증됨
- 터미널 포맷 출력 리포트 — 완성 및 동작 검증됨
- PyInstaller 빌드 스펙 및 산출물 — 완성 및 동작 검증됨
- 사용자 실행 가이드 문서 — 완성 및 동작 검증됨

## Risks and Assumptions

- 동행복권 API 스키마 또는 엔드포인트 변경 시 수집 실패
- 과도한 요청으로 IP 차단 또는 rate limit 발생
- 작은 표본(500회차) 통계의 과적합·편향 위험
- macOS PyInstaller .app이 Gatekeeper 서명 미적용으로 실행 경고 발생
- 번호 추천을 보장된 당첨으로 오해할 소지(면책 고지 필요)
- 교차 OS 빌드(Windows↔macOS) 제약으로 단일 머신에서 양쪽 산출물 생성 불가
- 네트워크 장애 시 로컬 캐시(SQLite 또는 JSON)로 재시도·복구

## Evidence

- Local reference: docs/architecture.md -> ## 문서 규칙 - 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다. - 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다. - 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다. - 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
- LLM prior knowledge (unverified): Frequency analysis of historical draws to identify hot and cold numbers
- LLM prior knowledge (unverified): Combinatorial filtering (odd/even ratio, low/high split, sum range, consecutive runs)
- NotebookLM synthesis: Conversation ID: d68298d4-d15b-4e78-9caf-c342f528fc0c Use --conversation-id for follow-up questions

## References

- Local: docs/architecture.md | ## 문서 규칙

## Approval Request

- Review this scope and confirm approval-gate.md when ready.
