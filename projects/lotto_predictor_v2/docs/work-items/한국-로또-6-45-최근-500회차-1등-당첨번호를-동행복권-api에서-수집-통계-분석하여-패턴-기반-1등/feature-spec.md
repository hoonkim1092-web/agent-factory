# Feature Spec

## Metadata

- work_item: 한국-로또-6-45-최근-500회차-1등-당첨번호를-동행복권-api에서-수집-통계-분석하여-패턴-기반-1등
- source_plan: feature-plan.md
- status: draft
- last_updated: 2026-04-17T01:24:58

## Feature Overview

한국 로또 6/45 최근 500회차 1등 당첨번호를 동행복권 API에서 수집·통계 분석하여 패턴 기반 1등 번호 5개 조합을 추천하고 PyInstaller로 더블클릭 실행 가능한 단일 실행 파일로 배포하는 데스크톱 도구를 구축한다.

## User Scenarios

- 사용자: 실행파일 더블클릭 -> 시스템: 로컬 캐시 확인 후 최신 회차까지 증분 수집
- 사용자: 분석 실행 선택 -> 시스템: 최근 500회차 통계 리포트를 터미널에 출력
- 사용자: 추천 요청 -> 시스템: 패턴 기반 1등 후보 5조합과 근거 지표 출력
- 사용자: 재현용 seed 입력 -> 시스템: 동일 seed로 동일 조합 재생성
- 개발자: pyinstaller 빌드 스크립트 실행 -> 시스템: dist/ 하위에 더블클릭 실행 산출물 생성

## Functional Requirements

- [동행복권 회차 수집기 모듈] 동행복권 회차 수집기 모듈을(를) 구현한다.
- [회차 데이터 로컬 캐시 저장소] 회차 데이터 로컬 캐시 저장소을(를) 구현한다.
- [통계 분석 엔진] 통계 분석 엔진(빈도·연속·홀짝·구간·트렌드)을(를) 구현한다.
- [패턴 기반 번호 조합 추천기] 패턴 기반 번호 조합 추천기을(를) 구현한다.
- [터미널 포맷 출력 리포트] 터미널 포맷 출력 리포트을(를) 구현한다.
- [PyInstaller 빌드 스펙 및 산출물] PyInstaller 빌드 스펙 및 산출물을(를) 구현한다.
- [사용자 실행 가이드 문서] 사용자 실행 가이드 문서을(를) 구현한다.
- [Backend Dev 구현] 서버, 데이터, 외부 연동 레이어를 구현한다.
- [Game Logic Dev 구현] 핵심 규칙과 상태 전이를 구현한다.
- [QA Engineer 검증] 핵심 플로우와 회귀 시나리오를 검증한다.

## Non-Functional Requirements

- 네트워크 장애 시 로컬 캐시(SQLite 또는 JSON)로 재시도·복구

## Inputs and Outputs

- **LottoDraw** [sqlite]: drwNo, drwNoDate, drwtNo1, drwtNo2, drwtNo3, drwtNo4
- **NumberFrequency** [sqlite]: number, count, last_seen_drwNo, recent_50_count
- **Recommendation** [json]: generated_at, seed, numbers, strategy_tag, odd_even_ratio, range_distribution
- **FetchCheckpoint** [sqlite]: last_fetched_drwNo, fetched_at, source_url

## Exceptions and Failure Scenarios

- (edit required)

## Existing Behavior To Preserve

- (edit required)

## Acceptance Criteria

- 동행복권 회차 수집기 모듈의 핵심 기능이 구현된다.
- 관련 파일과 산출물이 갱신된다.
- 검증 결과가 정리된다.
- 잔여 리스크와 후속 작업이 기록된다.
- 회차 데이터 로컬 캐시 저장소의 핵심 기능이 구현된다.
- 통계 분석 엔진의 핵심 기능이 구현된다.
- 패턴 기반 번호 조합 추천기의 핵심 기능이 구현된다.
- 터미널 포맷 출력 리포트의 핵심 기능이 구현된다.
- PyInstaller 빌드 스펙 및 산출물의 핵심 기능이 구현된다.
- 사용자 실행 가이드 문서의 핵심 기능이 구현된다.
- Backend Dev 구현의 핵심 기능이 구현된다.
- Game Logic Dev 구현의 핵심 기능이 구현된다.
- QA Engineer 검증의 핵심 기능이 구현된다.

## Evidence

- Local reference: docs/architecture.md -> ## 문서 규칙 - 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다. - 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다. - 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다. - 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
- LLM prior knowledge (unverified): Frequency analysis of historical draws to identify hot and cold numbers
- LLM prior knowledge (unverified): Combinatorial filtering (odd/even ratio, low/high split, sum range, consecutive runs)
- NotebookLM synthesis: Conversation ID: d68298d4-d15b-4e78-9caf-c342f528fc0c Use --conversation-id for follow-up questions

## References

- Local: docs/architecture.md | ## 문서 규칙

## Out Of Scope

- 2등 이하 등수 예측 및 보너스 번호 예측
- 머신러닝/딥러닝 기반 시계열 예측 모델 도입
- GUI(윈도우 창) 인터페이스 제공
- 웹 서비스·모바일 앱 배포
- 실시간 구매 자동화 또는 결제 연동
- 당첨 보장성 주장 또는 확률 조작
