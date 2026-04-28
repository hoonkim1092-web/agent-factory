# Feature Plan

## Metadata

- work_item: 동행복권-api에서-최근-500회차-로또-당첨번호를-수집-통계-분석하여-가중-랜덤-기반-1등-후보-5조합을
- owner: (edit required)
- status: draft
- last_updated: 2026-04-16T20:43:37

## Background

로또 6/45는 매주 1회 추첨되며 수동 번호 선택 시 과거 통계를 참고하려는 수요가 크지만, 동행복권 사이트에서 회차별로 일일이 확인하는 것은 비효율적이다. 개별 번호 출현 빈도뿐 아니라 쌍·삼중 동시 출현 패턴까지 분석하면 단순 랜덤보다 통계적으로 편향된 조합 생성이 가능하다.

## Problem Statement

과거 당첨 데이터를 체계적으로 수집·캐싱하고, 빈도·동시출현·구간 편향 등 다차원 통계를 한 번에 산출하여 가중치 기반 추천까지 자동화하는 로컬 도구가 없다.

## Goals

- 동행복권 API 데이터 수집 모듈
- SQLite 기반 당첨번호 캐시 저장소
- 번호별 출현빈도·동시출현·구간 통계 분석 엔진
- 가중 랜덤 기반 5조합 추천 생성기
- 터미널 통계 요약 출력 포맷터
- CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)

## Non-Goals

- 당첨 확률 향상 보장 또는 예측 정확도 주장
- GUI 또는 웹 인터페이스 제공
- 자동 로또 구매 연동
- Windows/Linux 크로스플랫폼 지원 (macOS CLI 전용)
- 딥러닝/머신러닝 기반 번호 예측
- 과거 전체 회차(1~현재) 수집 — 최근 500회차로 한정

## Scope

- **동행복권 API 데이터 수집 모듈**: 동행복권 API 데이터 수집 모듈을(를) 구현한다.
- **SQLite 기반 당첨번호 캐시 저장소**: SQLite 기반 당첨번호 캐시 저장소을(를) 구현한다.
- **번호별 출현빈도·동시출현·구간 통계 분석 엔진**: 번호별 출현빈도·동시출현·구간 통계 분석 엔진을(를) 구현한다.
- **가중 랜덤 기반 5조합 추천 생성기**: 가중 랜덤 기반 5조합 추천 생성기을(를) 구현한다.
- **터미널 통계 요약 출력 포맷터**: 터미널 통계 요약 출력 포맷터을(를) 구현한다.
- **CLI 엔트리포인트**: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)을(를) 구현한다.
- **QA Engineer 검증**: 핵심 플로우와 회귀 시나리오를 검증한다.

## Stakeholders

- Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다.
- QA Engineer: 핵심 플로우와 회귀 시나리오를 검증한다.

## Success Metrics

- 동행복권 API 데이터 수집 모듈 — 완성 및 동작 검증됨
- SQLite 기반 당첨번호 캐시 저장소 — 완성 및 동작 검증됨
- 번호별 출현빈도·동시출현·구간 통계 분석 엔진 — 완성 및 동작 검증됨
- 가중 랜덤 기반 5조합 추천 생성기 — 완성 및 동작 검증됨
- 터미널 통계 요약 출력 포맷터 — 완성 및 동작 검증됨
- CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드) — 완성 및 동작 검증됨

## Risks and Assumptions

- 동행복권 API 응답 형식이 문서화되지 않아 변경 시 파서 깨질 수 있음
- 500회차 일괄 수집 시 API 서버 차단 가능성
- 통계 기반 가중치가 실제 당첨 확률 향상을 보장하지 않음 — 사용자 오해 방지 고지 필요
- API 엔드포인트 URL이 비공식이므로 검증 필요
- 인터넷 미연결 시 캐시된 데이터로 분석·추천 가능해야 함

## Evidence

- LLM prior knowledge (unverified): HTTP GET to the 동행복권 (dhlottery.co.kr) public API endpoint that returns winning numbers by draw round as JSON
- LLM prior knowledge (unverified): Frequency analysis of individual numbers and pair/triplet co-occurrence across historical draws
- NotebookLM synthesis: Conversation ID: a6e109cb-b12e-4120-97e8-aabdbafb2b3e Use --conversation-id for follow-up questions

## References

- (no additional references)

## Approval Request

- Review this scope and confirm approval-gate.md when ready.
