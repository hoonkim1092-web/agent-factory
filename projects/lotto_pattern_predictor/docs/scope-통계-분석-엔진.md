# 번호별 출현빈도·동시출현·구간 통계 분석 엔진 — 범위 및 인터페이스 정의

## 메타데이터
- 작업 ID: `backend_dev_module_3_scope_1`
- 작성자: backend_dev
- 작성일: 2026-04-16
- 상태: 확정

---

## 1. 모듈 목적

`CacheStore`에서 로드한 `DrawResult` 리스트를 입력으로 받아,
번호별 출현 빈도, 번호 쌍 동시 출현 행렬, 구간별(최근 N회차) 트렌드 통계를 산출한다.
분석 결과는 하위 모듈(`recommender.py`)이 가중치 기반 추천에 사용할 구조화된 데이터로 반환한다.

---

## 2. 범위

### 포함
| 항목 | 설명 |
|------|------|
| 번호별 출현 빈도 | 1~45 각 번호가 당첨 번호로 출현한 횟수, 마지막 출현 회차, 평균 출현 간격 |
| 번호 쌍 동시 출현 | 같은 회차에 함께 당첨된 번호 쌍(C(45,2) = 990쌍)별 출현 횟수 |
| 구간 통계 | 최근 N회차(기본 50, 100, 전체) 윈도우별 출현 빈도 집계 |
| 보너스 번호 빈도 | 보너스 번호의 출현 빈도 (별도 집계) |
| 번호별 가중치 점수 | 출현 빈도 + 구간 트렌드를 결합한 정규화된 가중치 (0.0~1.0) |

### 제외
| 항목 | 사유 |
|------|------|
| 데이터 수집 | `fetcher` 모듈 책임 |
| 데이터 저장/조회 | `cache_store` 모듈 책임 |
| 조합 추천 | `recommender` 모듈 책임 |
| 출력 포맷 | `formatter` 모듈 책임 |
| 3개 이상 동시 출현 | 990쌍으로 충분. 트리플릿 분석은 향후 확장 시 별도 추가 |

---

## 3. 데이터 모델

### 3.1 NumberFrequency (번호별 빈도)

```python
@dataclass(frozen=True)
class NumberFrequency:
    """개별 번호의 출현 통계."""
    number: int              # 1~45
    count: int               # 출현 횟수
    last_appeared_draw: int  # 마지막 출현 회차
    avg_gap: float           # 평균 출현 간격 (회차 수)
```

### 3.2 PairCooccurrence (쌍 동시출현)

```python
@dataclass(frozen=True)
class PairCooccurrence:
    """번호 쌍의 동시 출현 통계."""
    num_a: int   # 작은 번호
    num_b: int   # 큰 번호 (num_a < num_b 보장)
    count: int   # 동시 출현 횟수
```

### 3.3 AnalysisResult (분석 결과 묶음)

```python
@dataclass(frozen=True)
class AnalysisResult:
    """통계 분석 전체 결과."""
    total_draws: int                           # 분석에 사용된 총 회차 수
    frequencies: dict[int, NumberFrequency]     # {번호: NumberFrequency}
    bonus_frequencies: dict[int, int]           # {번호: 보너스 출현 횟수}
    pair_cooccurrences: dict[tuple[int, int], PairCooccurrence]  # {(a,b): PairCooccurrence}
    window_frequencies: dict[str, dict[int, int]]  # {"recent_50": {번호: 횟수}, ...}
    weights: dict[int, float]                  # {번호: 정규화 가중치 0.0~1.0}
```

---

## 4. 인터페이스 정의

### 4.1 분석 엔진 클래스

```python
# src/lotto/analysis.py

from .models import DrawResult

class AnalysisEngine:
    """번호별 출현빈도·동시출현·구간 통계 분석 엔진."""

    DEFAULT_WINDOWS: tuple[int, ...] = (50, 100)

    def __init__(
        self,
        draws: list[DrawResult],
        windows: tuple[int, ...] | None = None,
    ) -> None:
        """분석 엔진을 초기화한다.

        Args:
            draws: 분석 대상 DrawResult 리스트 (회차 오름차순 권장).
                   비어 있으면 AnalysisError 발생.
            windows: 구간 통계에 사용할 최근 N회차 윈도우 목록.
                     None이면 DEFAULT_WINDOWS 사용.

        Raises:
            AnalysisError: draws가 비어 있을 때
        """
        ...

    def analyze(self) -> AnalysisResult:
        """전체 통계 분석을 수행하고 결과를 반환한다.

        Returns:
            AnalysisResult 데이터클래스

        Raises:
            AnalysisError: 분석 중 오류 발생 시
        """
        ...

    def compute_frequencies(self) -> dict[int, NumberFrequency]:
        """1~45 각 번호의 출현 빈도를 계산한다.

        Returns:
            {번호: NumberFrequency} 딕셔너리
        """
        ...

    def compute_bonus_frequencies(self) -> dict[int, int]:
        """보너스 번호의 출현 빈도를 계산한다.

        Returns:
            {번호: 보너스 출현 횟수} 딕셔너리
        """
        ...

    def compute_pair_cooccurrences(self) -> dict[tuple[int, int], PairCooccurrence]:
        """번호 쌍의 동시 출현 횟수를 계산한다.

        Returns:
            {(num_a, num_b): PairCooccurrence} 딕셔너리 (num_a < num_b)
        """
        ...

    def compute_window_frequencies(self) -> dict[str, dict[int, int]]:
        """구간별(최근 N회차) 출현 빈도를 계산한다.

        Returns:
            {"recent_50": {번호: 횟수}, "recent_100": {번호: 횟수}, "all": {번호: 횟수}}
        """
        ...

    def compute_weights(
        self,
        frequencies: dict[int, NumberFrequency],
        window_frequencies: dict[str, dict[int, int]],
    ) -> dict[int, float]:
        """출현 빈도와 구간 트렌드를 결합한 정규화 가중치를 계산한다.

        가중치 공식:
            raw_weight = 0.4 * 전체_빈도_비율 + 0.6 * 최근_50회차_빈도_비율
            weight = raw_weight / max(raw_weights)  → 0.0~1.0 정규화

        Args:
            frequencies: compute_frequencies() 결과
            window_frequencies: compute_window_frequencies() 결과

        Returns:
            {번호: 정규화 가중치} (0.0 ~ 1.0)
        """
        ...
```

### 4.2 예외 클래스 (추가)

```python
# src/lotto/exceptions.py (기존 파일에 추가)

class AnalysisError(LottoError):
    """통계 분석 처리 오류."""
```

---

## 5. 가중치 산출 공식

| 구성 요소 | 비중 | 설명 |
|-----------|------|------|
| 전체 출현 빈도 비율 | 40% | `count / total_draws` — 장기 경향 |
| 최근 50회차 빈도 비율 | 60% | `recent_count / 50` — 단기 트렌드 |

- 최종 가중치는 전체 번호의 raw_weight 중 최대값으로 나눠 0.0~1.0으로 정규화한다.
- 출현 기록이 없는 번호는 weight = 0.0이 된다.

---

## 6. 의존성

### 외부 패키지
- 없음 (순수 Python 연산)

### 표준 라이브러리
- `itertools` (combinations), `dataclasses`, `collections`

### 내부 의존성
| 모듈 | 사용 항목 |
|------|-----------|
| `models.py` | `DrawResult` (읽기 전용 소비) |
| `exceptions.py` | `LottoError` (상속), `AnalysisError` (신규 정의) |

---

## 7. 산출물

| 파일 경로 | 설명 |
|-----------|------|
| `src/lotto/analysis.py` | `AnalysisEngine`, `NumberFrequency`, `PairCooccurrence`, `AnalysisResult` |
| `src/lotto/exceptions.py` | `AnalysisError` 예외 추가 |
| `tests/test_analysis.py` | 단위 테스트 |

---

## 8. 구현 순서

| 순서 | 슬라이스 | 설명 |
|------|----------|------|
| 1 | `exceptions.py` — `AnalysisError` | 예외 클래스 1개 추가 |
| 2 | `analysis.py` — 데이터 모델 | `NumberFrequency`, `PairCooccurrence`, `AnalysisResult` 데이터클래스 |
| 3 | `analysis.py` — `__init__` + 유효성 검증 | draws 검증, windows 초기화 |
| 4 | `analysis.py` — `compute_frequencies()` | 번호별 출현 빈도 계산 |
| 5 | `analysis.py` — `compute_bonus_frequencies()` | 보너스 번호 빈도 계산 |
| 6 | `analysis.py` — `compute_pair_cooccurrences()` | 쌍 동시 출현 계산 |
| 7 | `analysis.py` — `compute_window_frequencies()` | 구간별 빈도 계산 |
| 8 | `analysis.py` — `compute_weights()` | 가중치 산출 |
| 9 | `analysis.py` — `analyze()` | 전체 분석 오케스트레이션 |
| 10 | `tests/test_analysis.py` | 고정 fixture 기반 단위 테스트 |

---

## 9. 상위/하위 모듈 연동 계약

### 이 모듈이 소비하는 데이터
| 제공 모듈 | 데이터 | 사용 방식 |
|-----------|--------|-----------|
| `cache_store.py` | `list[DrawResult]` | `get_all()` 또는 `get_range()`로 로드 후 `AnalysisEngine(draws)` 전달 |

### 이 모듈을 소비하는 모듈
| 소비 모듈 | 사용 방식 |
|-----------|-----------|
| `recommender.py` | `AnalysisResult.weights`로 가중 랜덤 추천 |
| `recommender.py` | `AnalysisResult.pair_cooccurrences`로 쌍 보정 (선택) |
| `formatter.py` | `AnalysisResult`를 터미널 테이블로 출력 |
| `cli.py` | `analyze` 서브커맨드에서 `AnalysisEngine` 호출 |

### 연동 패턴
```python
# cli.py 또는 상위 오케스트레이션에서 사용할 패턴
with CacheStore() as cache:
    draws = cache.get_all()
    engine = AnalysisEngine(draws)
    result = engine.analyze()
    # result.weights → recommender에 전달
    # result.frequencies → formatter에 전달
```

---

## 10. 리스크 및 완화 전략

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 데이터 부족 (캐시 0건) | 분석 불가 | `__init__`에서 빈 리스트 검증, `AnalysisError` 발생 |
| 쌍 동시출현 메모리 사용 | 990쌍 × 데이터클래스 ≈ 수십 KB 수준 | 500회차 규모에서는 무시 가능 |
| 가중치 공식 편향 | 특정 번호 과대 추천 | 정규화(0~1)로 극단적 편향 방지, 공식 조정 가능하게 파라미터 분리 |
| 회차 순서 미정렬 입력 | 구간 통계 오류 | 생성자에서 draw_no 기준 정렬 적용 |
