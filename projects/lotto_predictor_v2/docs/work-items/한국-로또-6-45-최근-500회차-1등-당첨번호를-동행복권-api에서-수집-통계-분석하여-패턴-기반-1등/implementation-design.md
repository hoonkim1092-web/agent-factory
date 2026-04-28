# Implementation Design

## Metadata

- work_item: 한국-로또-6-45-최근-500회차-1등-당첨번호를-동행복권-api에서-수집-통계-분석하여-패턴-기반-1등
- spec_type: feature
- source_spec: feature-spec.md
- status: draft
- last_updated: 2026-04-17T01:24:58

## Design Summary

한국 로또 6/45 최근 500회차 1등 당첨번호를 동행복권 API에서 수집·통계 분석하여 패턴 기반 1등 번호 5개 조합을 추천하고 PyInstaller로 더블클릭 실행 가능한 단일 실행 파일로 배포하는 데스크톱 도구를 구축한다.

아키텍처: cli

기술 스택: Python 3.11, requests, SQLite (stdlib sqlite3), rich (터미널 포맷 출력), statistics/collections (stdlib), PyInstaller 6.x, pytest (검증)

실행 전략: parallel

## Planned Modules

### 동행복권 회차 수집기 모듈
- owner: frontend_dev
- objective: 동행복권 회차 수집기 모듈을(를) 구현한다.
- deliverables: 동행복권 회차 수집기 모듈
- feature_slices: 동행복권 회차 수집기 모듈을(를) 구현한다.

### 회차 데이터 로컬 캐시 저장소
- owner: frontend_dev
- objective: 회차 데이터 로컬 캐시 저장소을(를) 구현한다.
- deliverables: 회차 데이터 로컬 캐시 저장소
- feature_slices: 회차 데이터 로컬 캐시 저장소을(를) 구현한다.

### 통계 분석 엔진
- owner: frontend_dev
- objective: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)을(를) 구현한다.
- deliverables: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)
- feature_slices: 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)을(를) 구현한다.

### 패턴 기반 번호 조합 추천기
- owner: frontend_dev
- objective: 패턴 기반 번호 조합 추천기을(를) 구현한다.
- deliverables: 패턴 기반 번호 조합 추천기
- feature_slices: 패턴 기반 번호 조합 추천기을(를) 구현한다.

### 터미널 포맷 출력 리포트
- owner: frontend_dev
- objective: 터미널 포맷 출력 리포트을(를) 구현한다.
- deliverables: 터미널 포맷 출력 리포트
- feature_slices: 터미널 포맷 출력 리포트을(를) 구현한다.

### PyInstaller 빌드 스펙 및 산출물
- owner: frontend_dev
- objective: PyInstaller 빌드 스펙 및 산출물을(를) 구현한다.
- deliverables: PyInstaller 빌드 스펙 및 산출물
- feature_slices: PyInstaller 빌드 스펙 및 산출물을(를) 구현한다.

### 사용자 실행 가이드 문서
- owner: frontend_dev
- objective: 사용자 실행 가이드 문서을(를) 구현한다.
- deliverables: 사용자 실행 가이드 문서
- feature_slices: 사용자 실행 가이드 문서을(를) 구현한다.

### Backend Dev 구현
- owner: backend_dev
- objective: 서버, 데이터, 외부 연동 레이어를 구현한다.
- deliverables: 동행복권 회차 수집기 모듈
- feature_slices: 서버, 데이터, 외부 연동 레이어를 구현한다.

### Game Logic Dev 구현
- owner: game_logic_dev
- objective: 핵심 규칙과 상태 전이를 구현한다.
- deliverables: 동행복권 회차 수집기 모듈
- feature_slices: 핵심 규칙과 상태 전이를 구현한다.

### QA Engineer 검증
- owner: qa_engineer
- objective: 핵심 플로우와 회귀 시나리오를 검증한다.
- deliverables: 동행복권 회차 수집기 모듈
- feature_slices: 핵심 플로우와 회귀 시나리오를 검증한다.


## Data Flow

- (시작) → **동행복권 회차 수집기 모듈**
- (시작) → **회차 데이터 로컬 캐시 저장소**
- (시작) → **통계 분석 엔진**
- (시작) → **패턴 기반 번호 조합 추천기**
- (시작) → **터미널 포맷 출력 리포트**
- (시작) → **PyInstaller 빌드 스펙 및 산출물**
- (시작) → **사용자 실행 가이드 문서**
- (시작) → **Backend Dev 구현**
- (시작) → **Game Logic Dev 구현**
- (시작) → **QA Engineer 검증**

## Interface Impact

- (edit required)

## State And Data Model

- **LottoDraw** (sqlite): drwNo, drwNoDate, drwtNo1, drwtNo2, drwtNo3, drwtNo4, drwtNo5, drwtNo6, bnusNo, totSellamnt, firstWinamnt
- **NumberFrequency** (sqlite): number, count, last_seen_drwNo, recent_50_count
- **Recommendation** (json): generated_at, seed, numbers, strategy_tag, odd_even_ratio, range_distribution
- **FetchCheckpoint** (sqlite): last_fetched_drwNo, fetched_at, source_url

## Compatibility Considerations

- (edit required)

## Migration Requirement

- none

## Risks

- 동행복권 API 스키마 또는 엔드포인트 변경 시 수집 실패
- 과도한 요청으로 IP 차단 또는 rate limit 발생
- 작은 표본(500회차) 통계의 과적합·편향 위험
- macOS PyInstaller .app이 Gatekeeper 서명 미적용으로 실행 경고 발생
- 번호 추천을 보장된 당첨으로 오해할 소지(면책 고지 필요)
- 교차 OS 빌드(Windows↔macOS) 제약으로 단일 머신에서 양쪽 산출물 생성 불가
- 네트워크 장애 시 로컬 캐시(SQLite 또는 JSON)로 재시도·복구

## Alternatives Considered

- (edit required)

## Design Evidence

- Local reference: docs/architecture.md -> ## 문서 규칙 - 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다. - 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다. - 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다. - 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
- LLM prior knowledge (unverified): Frequency analysis of historical draws to identify hot and cold numbers
- LLM prior knowledge (unverified): Combinatorial filtering (odd/even ratio, low/high split, sum range, consecutive runs)
- NotebookLM synthesis: Conversation ID: d68298d4-d15b-4e78-9caf-c342f528fc0c Use --conversation-id for follow-up questions

## References

- Local: docs/architecture.md | ## 문서 규칙

## Test Strategy

- Unit tests per module
- Integration tests for cross-module flows
