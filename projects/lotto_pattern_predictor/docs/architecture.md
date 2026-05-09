# 아키텍처

이 문서는 현재 아키텍처와 워크플로를 설명하는 살아 있는 기준 문서다.
설계, 워크플로, 인터페이스, 데이터 흐름, 구현 전략이 바뀌면 같은 작업 안에서 갱신한다.

## 메타데이터
- 마지막 업데이트: 2026-04-16T23:30:00
- 상태: active
- 문서 언어: 한국어 (OS: `ko-KR`)

## 현재 설계
- 요약:
  QA Engineer 모듈은 동행복권 로또 CLI의 핵심 흐름과 회귀 시나리오를 검증하는 역할만 담당한다. 구현 대상 자체를 변경하지 않고, 다른 모듈이 제공한 실행 인터페이스와 산출물을 입력으로 받아 검증 결과를 기록한다.
- 핵심 구성 요소:
  1. 검증 범위 정의
     데이터 수집, 캐시 저장, 통계 분석, 추천 생성, CLI 출력까지의 핵심 흐름을 검증 대상으로 삼는다.
  2. 검증 입력 인터페이스
     QA는 구현 모듈의 코드 내부 계약을 새로 정의하지 않고, 실행 가능한 CLI 진입점과 모듈 산출물을 입력 계약으로 사용한다.
  3. 검증 산출물
     테스트 케이스 문서, 실행 절차, 검증 로그 또는 결과 요약, handoff 메모를 남긴다.
  4. 실패 분류 기준
     환경 문제, 데이터 수집 실패, 저장소 실패, 분석 실패, 추천 실패, 출력 포맷 실패로 구분해 후속 역할이 바로 이어받을 수 있게 한다.
- 데이터 흐름:
  1. Backend Dev가 데이터 수집 모듈, SQLite 캐시 저장소, 분석 엔진, 추천 생성기, 출력 포맷터, CLI 엔트리포인트를 구현한다.
  2. QA Engineer는 CLI 실행 인터페이스와 각 모듈의 기대 산출물을 입력으로 받는다.
  3. QA Engineer는 모듈별 검증과 종단간 회귀 시나리오를 순서대로 실행한다.
  4. 검증 결과는 성공/실패, 재현 절차, 영향 범위, 잔여 리스크를 포함한 문서 산출물로 기록된다.
- 제약 사항:
  1. QA 범위는 검증 전략과 인터페이스 정의에 한정하며, 다른 모듈 구현에는 개입하지 않는다.
  2. 네트워크 의존 검증은 API 응답 변동 가능성을 고려해 실패 분류와 재시도 기준을 별도로 둔다.
  3. 검증은 최소한 다음 두 층위로 나뉜다: 모듈 계약 검증, 종단간 CLI 회귀 검증.
  4. QA 시작 조건은 각 Backend Dev 모듈이 실행 가능한 상태로 전달되는 것이다.
- 열린 질문:
  1. CLI 진입 명령의 최종 파일 경로와 실행 옵션은 Backend Dev build 산출물에서 확정되어야 한다.
  2. API 실시간 호출을 기본 검증으로 할지, 고정 fixture 기반 검증을 병행할지는 build 단계에서 결정한다.

## Backend Dev 모듈 구조

### 전체 파이프라인
```
동행복권 API ──→ LottoFetcher ──→ DrawResult[] ──→ CacheStore (SQLite)
                                                        │
                                                        ▼
                                      AnalysisEngine ──→ 통계 결과
                                                        │
                                                        ▼
                                      Recommender ──→ 5조합 추천
                                                        │
                                                        ▼
                                      Formatter ──→ 터미널 출력
```

### 모듈 파일 맵
| 파일 | 역할 | 상태 |
|------|------|------|
| `src/lotto/models.py` | 공유 데이터 모델 (`DrawResult`) | 구현 완료 |
| `src/lotto/exceptions.py` | 예외 계층 (`LottoError` → `DrawNotFoundError`, `FetchError`) | 구현 완료 |
| `src/lotto/fetcher.py` | 동행복권 API 수집기 (`LottoFetcher`) | 구현 완료 |
| `src/lotto/cache_store.py` | SQLite 캐시 저장소 (`CacheStore`) | 구현 완료 |
| `src/lotto/analysis.py` | 빈도·동시출현·구간 통계 엔진 (`AnalysisEngine`) | 구현 완료 |
| `src/lotto/recommender.py` | 가중 랜덤 5조합 추천 | 예정 |
| `src/lotto/formatter.py` | 터미널 출력 포맷터 | 예정 |
| `src/lotto/cli.py` | CLI 엔트리포인트 | 예정 |

### 핵심 데이터 모델
```python
@dataclass(frozen=True)
class DrawResult:
    draw_no: int                # 회차 번호
    draw_date: date             # 추첨일
    numbers: tuple[int, ...]    # 당첨 번호 6개 (오름차순)
    bonus: int                  # 보너스 번호
    total_sell_amount: int      # 총 판매금액
    first_prize_amount: int     # 1등 당첨금액
    first_prize_winners: int    # 1등 당첨자 수
```

### CacheStore 인터페이스 요약
```
CacheStore(db_path?)
  .save(DrawResult)           → None
  .save_many(list[DrawResult]) → int (신규 저장 건수)
  .get(draw_no)               → DrawResult | None
  .get_range(start, end)      → list[DrawResult]
  .get_all()                  → list[DrawResult]
  .get_cached_draw_numbers()  → set[int]
  .count()                    → int
  .close()                    → None
  __enter__ / __exit__        → 컨텍스트 매니저
```

### draws 테이블 스키마
```sql
CREATE TABLE IF NOT EXISTS draws (
    draw_no        INTEGER PRIMARY KEY,
    draw_date      TEXT NOT NULL,
    num1..num6     INTEGER NOT NULL,
    bonus          INTEGER NOT NULL,
    total_sell_amount    INTEGER NOT NULL DEFAULT 0,
    first_prize_amount   INTEGER NOT NULL DEFAULT 0,
    first_prize_winners  INTEGER NOT NULL DEFAULT 0,
    fetched_at     TEXT NOT NULL
);
```

### AnalysisEngine 인터페이스 요약
```
AnalysisEngine(draws, windows?)
  .analyze()                    → AnalysisResult
  .compute_frequencies()        → dict[int, NumberFrequency]
  .compute_bonus_frequencies()  → dict[int, int]
  .compute_pair_cooccurrences() → dict[tuple[int,int], PairCooccurrence]
  .compute_window_frequencies() → dict[str, dict[int, int]]
  .compute_weights(freq, win)   → dict[int, float]
```

### 분석 데이터 모델
```python
@dataclass(frozen=True)
class NumberFrequency:
    number: int              # 1~45
    count: int               # 출현 횟수
    last_appeared_draw: int  # 마지막 출현 회차
    avg_gap: float           # 평균 출현 간격

@dataclass(frozen=True)
class PairCooccurrence:
    num_a: int   # 작은 번호
    num_b: int   # 큰 번호 (num_a < num_b)
    count: int   # 동시 출현 횟수

@dataclass(frozen=True)
class AnalysisResult:
    total_draws: int
    frequencies: dict[int, NumberFrequency]
    bonus_frequencies: dict[int, int]
    pair_cooccurrences: dict[tuple[int, int], PairCooccurrence]
    window_frequencies: dict[str, dict[int, int]]
    weights: dict[int, float]                   # 0.0~1.0 정규화
```

### 외부 의존성
- `requests` ≥2.31 — HTTP 요청
- `rich` — 터미널 테이블/컬러 출력
- Python 3.11+ 표준 라이브러리: `sqlite3`, `argparse`, `json`, `dataclasses`

## QA Engineer 검증 모듈 계약

### 검증 범위
- 데이터 수집 검증: 최근 회차 범위를 받아 API 또는 대체 입력에서 당첨번호 데이터를 수집할 수 있는지 확인한다.
- 저장소 검증: 수집 결과가 SQLite 캐시에 저장되고 재조회 가능한지 확인한다.
- 분석 검증: 출현 빈도, 동시 출현, 구간 통계가 기대 형식으로 계산되는지 확인한다.
- 추천 검증: 가중 랜덤 기반 5조합이 제약 조건을 만족하는 형식으로 생성되는지 확인한다.
- CLI 회귀 검증: `fetch`, `analyze`, `recommend` 흐름이 사용 가능한 명령 인터페이스로 연결되는지 확인한다.
- 비범위:
  성능 최적화, 장기 통계 정확성 고도화, 배포 자동화, UI 디자인 검토는 이번 QA 모듈 scope에 포함하지 않는다.

### 입력 인터페이스
- 실행 인터페이스:
  - CLI 명령: `fetch`, `analyze`, `recommend`
  - 실행 전제: 로컬 실행 가능한 엔트리포인트와 필요한 환경 설정이 제공되어야 한다.
- 의존 산출물:
  - 동행복권 API 데이터 수집 모듈
  - SQLite 기반 당첨번호 캐시 저장소
  - 번호별 출현빈도·동시출현·구간 통계 분석 엔진
  - 가중 랜덤 기반 5조합 추천 생성기
  - 터미널 통계 요약 출력 포맷터
  - CLI 엔트리포인트
- 입력 계약:
  - 회차 범위 또는 최근 500회차 기본값이 지정 가능해야 한다.
  - 캐시 저장 경로가 결정되어야 한다.
  - 분석 결과와 추천 결과가 사람이 검토 가능한 구조화된 출력 또는 텍스트 요약으로 노출되어야 한다.

### QA 산출물
- 범위/계약 문서: 현재 문서와 설계 계획 문서
- 구현 단계 산출물:
  - 검증 시나리오 목록
  - 테스트 실행 스크립트 또는 명령 모음
  - 검증 결과 기록 문서
- 마감 단계 산출물:
  - handoff 메모
  - 잔여 리스크 목록

### 구현 순서
1. 의존 모듈 산출물과 QA 시작 조건을 확정한다.
2. 모듈별 기대 입력/출력 형식을 기준으로 검증 시나리오를 정의한다.
3. `fetch -> analyze -> recommend` 종단간 회귀 시나리오를 고정한다.
4. 실패 분류 기준과 재현 절차 템플릿을 마련한다.
5. build 단계에서 검증 자산을 구현하고 verify 단계에서 결과와 handoff를 남긴다.

## 문서 규칙
- 설계가 바뀌면 같은 작업 안에서 이 파일을 갱신한다.
- 작업을 닫기 전에 `docs/change_history.md`에 대응되는 항목을 추가한다.
- 이 저장소에서 생성하거나 수정하는 모든 문서는 운영체제 언어 코드 `ko-KR`에 맞는 언어인 한국어로 작성한다.
- 코드, 경로, 명령어, API 식별자는 필요한 경우 원문 그대로 유지한다.
