# Feature Spec

## Metadata

- work_item: 동행복권-api에서-최근-500회차-로또-당첨번호를-수집-통계-분석하여-가중-랜덤-기반-1등-후보-5조합을
- source_plan: feature-plan.md
- status: draft
- last_updated: 2026-04-16T20:43:37

## Feature Overview

동행복권 API에서 최근 500회차 로또 당첨번호를 수집·통계 분석하여 가중 랜덤 기반 1등 후보 5조합을 추천하는 macOS CLI 도구를 개발한다.

## User Scenarios

- 사용자: `lotto fetch` 실행 -> 시스템: 최신 회차 확인 후 미수집 회차만 API로 가져와 SQLite에 저장, 수집 결과 요약 출력
- 사용자: `lotto analyze` 실행 -> 시스템: 캐시된 500회차 데이터로 번호별 빈도, 쌍 동시출현, 홀짝/고저 분포 통계를 터미널 테이블로 출력
- 사용자: `lotto recommend` 실행 -> 시스템: 분석 통계 기반 가중 랜덤으로 5조합 생성하여 번호·가중치 점수와 함께 출력
- 사용자: `lotto recommend --count 10` 실행 -> 시스템: 10조합으로 확장 생성
- 사용자: 오프라인 상태에서 `lotto analyze` 실행 -> 시스템: 캐시 데이터로 정상 분석 수행

## Functional Requirements

- [동행복권 API 데이터 수집 모듈] 동행복권 API 데이터 수집 모듈을(를) 구현한다.
- [SQLite 기반 당첨번호 캐시 저장소] SQLite 기반 당첨번호 캐시 저장소을(를) 구현한다.
- [번호별 출현빈도·동시출현·구간 통계 분석 엔진] 번호별 출현빈도·동시출현·구간 통계 분석 엔진을(를) 구현한다.
- [가중 랜덤 기반 5조합 추천 생성기] 가중 랜덤 기반 5조합 추천 생성기을(를) 구현한다.
- [터미널 통계 요약 출력 포맷터] 터미널 통계 요약 출력 포맷터을(를) 구현한다.
- [CLI 엔트리포인트] CLI 엔트리포인트 (fetch / analyze / recommend 서브커맨드)을(를) 구현한다.
- [QA Engineer 검증] 핵심 플로우와 회귀 시나리오를 검증한다.

## Non-Functional Requirements

- macOS CLI 환경에서 Python 단독 실행 (외부 바이너리 의존 없음)
- 인터넷 미연결 시 캐시된 데이터로 분석·추천 가능해야 함

## Inputs and Outputs

- **Draw** [sqlite]: draw_no, draw_date, num1, num2, num3, num4
- **NumberFrequency** [memory]: number, count, last_appeared_draw, avg_gap
- **PairCooccurrence** [memory]: num_a, num_b, count
- **Recommendation** [memory]: set_id, numbers, weight_score, generated_at

## Exceptions and Failure Scenarios

- (edit required)

## Existing Behavior To Preserve

- (edit required)

## Acceptance Criteria

- 동행복권 API 데이터 수집 모듈의 핵심 기능이 구현된다.
- 관련 파일과 산출물이 갱신된다.
- 검증 결과가 정리된다.
- 잔여 리스크와 후속 작업이 기록된다.
- SQLite 기반 당첨번호 캐시 저장소의 핵심 기능이 구현된다.
- 번호별 출현빈도·동시출현·구간 통계 분석 엔진의 핵심 기능이 구현된다.
- 가중 랜덤 기반 5조합 추천 생성기의 핵심 기능이 구현된다.
- 터미널 통계 요약 출력 포맷터의 핵심 기능이 구현된다.
- CLI 엔트리포인트의 핵심 기능이 구현된다.
- QA Engineer 검증의 핵심 기능이 구현된다.

## Evidence

- LLM prior knowledge (unverified): HTTP GET to the 동행복권 (dhlottery.co.kr) public API endpoint that returns winning numbers by draw round as JSON
- LLM prior knowledge (unverified): Frequency analysis of individual numbers and pair/triplet co-occurrence across historical draws
- NotebookLM synthesis: Conversation ID: a6e109cb-b12e-4120-97e8-aabdbafb2b3e Use --conversation-id for follow-up questions

## References

- (no additional references)

## Out Of Scope

- 당첨 확률 향상 보장 또는 예측 정확도 주장
- GUI 또는 웹 인터페이스 제공
- 자동 로또 구매 연동
- Windows/Linux 크로스플랫폼 지원 (macOS CLI 전용)
- 딥러닝/머신러닝 기반 번호 예측
- 과거 전체 회차(1~현재) 수집 — 최근 500회차로 한정
