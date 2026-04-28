# Implementation Design

## Metadata

- work_item: 동행복권-api에서-최근-500회차-로또-당첨번호를-수집-통계-분석하여-가중-랜덤-기반-1등-후보-5조합을
- spec_type: feature
- source_spec: feature-spec.md
- status: draft
- last_updated: 2026-04-16T20:43:37

## Design Summary

동행복권 API에서 최근 500회차 로또 당첨번호를 수집·통계 분석하여 가중 랜덤 기반 1등 후보 5조합을 추천하는 macOS CLI 도구를 개발한다.

아키텍처: cli

기술 스택: Python 3.11+, sqlite3 (stdlib), requests 2.31+, argparse (stdlib), rich (터미널 테이블/컬러 출력)

실행 전략: parallel

## Planned Modules

### 동행복권 API 데이터 수집 모듈
- owner: backend_dev
- objective: 동행복권 API 데이터 수집 모듈을(를) 구현한다.
- deliverables: 동행복권 API 데이터 수집 모듈
- feature_slices: 동행복권 API 데이터 수집 모듈을(를) 구현한다.

### SQLite 기반 당첨번호 캐시 저장소
- owner: backend_dev
- objective: SQLite 기반 당첨번호 캐시 저장소을(를) 구현한다.
- deliverables: SQLite 기반 당첨번호 캐시 저장소
- feature_slices: SQLite 기반 당첨번호 캐시 저장소을(를) 구현한다.

### 번호별 출현빈도·동시출현·구간 통계 분석 엔진
- owner: backend_dev
- objective: 번호별 출현빈도·동시출현·구간 통계 분석 엔진을(를) 구현한다.
- deliverables: 번호별 출현빈도·동시출현·구간 통계 분석 엔진
- feature_slices: 번호별 출현빈도·동시출현·구간 통계 분석 엔진을(를) 구현한다.

### 가중 랜덤 기반 5조합 추천 생성기
- owner: backend_dev
- objective: 가중 랜덤 기반 5조합 추천 생성기을(를) 구현한다.
- deliverables: 가중 랜덤 기반 5조합 추천 생성기
- feature_slices: 가중 랜덤 기반 5조합 추천 생성기을(를) 구현한다.

### 터미널 통계 요약 출력 포맷터
- owner: backend_dev
- objective: 터미널 통계 요약 출력 포맷터을(를) 구현한다.
- deliverables: 터미널 통계 요약 출력 포맷터
- feature_slices: 터미널 통계 요약 출력 포맷터을(를) 구현한다.

### CLI 엔트리포인트
- owner: backend_dev
- objective: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)을(를) 구현한다.
- deliverables: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)
- feature_slices: CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)을(를) 구현한다.

### QA Engineer 검증
- owner: qa_engineer
- objective: 핵심 플로우와 회귀 시나리오를 검증한다.
- deliverables: 동행복권 API 데이터 수집 모듈
- feature_slices: 핵심 플로우와 회귀 시나리오를 검증한다.


## Data Flow

- (시작) → **동행복권 API 데이터 수집 모듈**
- (시작) → **SQLite 기반 당첨번호 캐시 저장소**
- (시작) → **번호별 출현빈도·동시출현·구간 통계 분석 엔진**
- (시작) → **가중 랜덤 기반 5조합 추천 생성기**
- (시작) → **터미널 통계 요약 출력 포맷터**
- (시작) → **CLI 엔트리포인트**
- (시작) → **QA Engineer 검증**

## Interface Impact

- (edit required)

## State And Data Model

- **Draw** (sqlite): draw_no, draw_date, num1, num2, num3, num4, num5, num6, bonus, total_sell_amount, first_prize_amount, first_prize_winners, fetched_at
- **NumberFrequency** (memory): number, count, last_appeared_draw, avg_gap
- **PairCooccurrence** (memory): num_a, num_b, count
- **Recommendation** (memory): set_id, numbers, weight_score, generated_at

## Compatibility Considerations

- (edit required)

## Migration Requirement

- none

## Risks

- 동행복권 API 응답 형식이 문서화되지 않아 변경 시 파서 깨질 수 있음
- 500회차 일괄 수집 시 API 서버 차단 가능성
- 통계 기반 가중치가 실제 당첨 확률 향상을 보장하지 않음 — 사용자 오해 방지 고지 필요
- API 엔드포인트 URL이 비공식이므로 검증 필요
- 인터넷 미연결 시 캐시된 데이터로 분석·추천 가능해야 함

## Alternatives Considered

- (edit required)

## Design Evidence

- LLM prior knowledge (unverified): HTTP GET to the 동행복권 (dhlottery.co.kr) public API endpoint that returns winning numbers by draw round as JSON
- LLM prior knowledge (unverified): Frequency analysis of individual numbers and pair/triplet co-occurrence across historical draws
- NotebookLM synthesis: Conversation ID: a6e109cb-b12e-4120-97e8-aabdbafb2b3e Use --conversation-id for follow-up questions

## References

- (no additional references)

## Test Strategy

- Unit tests per module
- Integration tests for cross-module flows
