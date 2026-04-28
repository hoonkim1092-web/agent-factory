---
모듈: 번호별 출현빈도·동시출현·구간 통계 분석 엔진
작성일: 2026-04-16
작성자: backend_dev
상태: 검증 완료
---

# Handoff — 번호별 출현빈도·동시출현·구간 통계 분석 엔진

## 검증 결과 요약

| 항목 | 결과 |
|------|------|
| `py_compile` | 통과 (analysis.py, models.py, exceptions.py) |
| 단위 테스트 (38건) | 전체 통과 (0.17s) |
| 모듈 임포트 | 정상 |
| 공개 인터페이스 (6 메서드) | 전부 존재 |
| 엣지 케이스 (빈 입력, 단일 회차, 경계값) | 통과 |
| 가중치 0~1 정규화 | 통과 |

## 산출물

| 파일 | 역할 |
|------|------|
| `src/lotto/analysis.py` | 통계 분석 엔진 구현 (227줄) |
| `src/lotto/exceptions.py` | `AnalysisError` 예외 클래스 |
| `tests/test_analysis.py` | 단위 테스트 26건 (개발자 작성) |
| `tests/test_analyzer.py` | 단위 테스트 12건 (QA 작성) |

## 공개 인터페이스

```python
class AnalysisEngine:
    def __init__(draws: list[DrawResult], windows: dict[str, int] | None = None) -> None
    def analyze() -> AnalysisResult                          # 전체 분석 한 번에 실행
    def compute_frequencies() -> dict[int, NumberFrequency]  # 번호별 출현 빈도
    def compute_bonus_frequencies() -> dict[int, int]        # 보너스 번호 빈도
    def compute_pair_cooccurrences() -> dict[tuple[int, int], PairCooccurrence]  # 번호 쌍 동시 출현
    def compute_window_frequencies() -> dict[str, dict[int, int]]  # 구간별 빈도
    def compute_weights(frequencies, window_frequencies) -> dict[int, float]  # 가중치 (0~1)
```

### 데이터 모델

```python
@dataclass(frozen=True)
class NumberFrequency:
    number: int           # 1~45
    count: int            # 출현 횟수
    last_appeared_draw: int  # 마지막 출현 회차
    avg_gap: float        # 평균 출현 간격

@dataclass(frozen=True)
class PairCooccurrence:
    num_a: int            # 작은 번호
    num_b: int            # 큰 번호 (num_a < num_b)
    count: int            # 동시 출현 횟수

@dataclass(frozen=True)
class AnalysisResult:
    total_draws: int
    frequencies: dict[int, NumberFrequency]
    bonus_frequencies: dict[int, int]
    pair_cooccurrences: dict[tuple[int, int], PairCooccurrence]
    window_frequencies: dict[str, dict[int, int]]
    weights: dict[int, float]  # 0.0~1.0 정규화
```

## 설계 특징

- **가중치 산출 전략**: 전체 빈도 40% + 최근 구간 빈도 40% + 출현 간격 역수 20% → 0~1 정규화
- **기본 윈도우**: 최근 50회, 100회, 200회 (커스텀 윈도우 지원)
- **자동 정렬**: 입력 데이터가 비순서여도 내부적으로 회차 오름차순 정렬
- **1~45 전체 범위**: 미출현 번호도 count=0으로 포함 (누락 없음)
- **동시출현 쌍**: `itertools.combinations`로 정렬된 번호 쌍 키 보장 `(a < b)`

## 잔여 리스크

1. **대량 데이터 성능**: 동시출현 계산이 O(N × C(6,2)) = O(15N). 500회차에서 7,500회 연산이므로 문제 없으나, 회차가 크게 늘어나면 성능 확인 필요.
2. **가중치 전략 튜닝**: 40/40/20 비율은 초기 설정. 실제 예측 정확도에 따라 조정이 필요할 수 있음.
3. **보너스 번호 미사용**: `bonus_frequencies`는 계산되지만 현재 가중치 산출에 반영되지 않음. 추후 추천 엔진에서 활용 여부 결정 필요.

## 후속 작업자 안내

- **추천 엔진 구현 시**: `AnalysisEngine(draws).analyze()` 호출 → `AnalysisResult.weights`를 가중 랜덤 선택의 확률 분포로 사용.
- **CacheStore 연동**: `CacheStore.get_all()` → `AnalysisEngine(draws)` 순으로 파이프라인 연결.
- **윈도우 커스터마이징**: `AnalysisEngine(draws, windows={"최근_30회": 30})` 형태로 원하는 구간 지정 가능.
- **동시출현 활용**: `pair_cooccurrences`를 사용해 자주 함께 나오는 번호 쌍 기반 조합 생성 가능.
