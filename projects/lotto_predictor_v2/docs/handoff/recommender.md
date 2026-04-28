# 추천기 인터페이스 계약

## 목적
이 문서는 `src/lotto/recommender.py`의 공개 인터페이스와 제약을 후속 작업자가 바로 연결할 수 있도록 고정한다.

## 공개 API
```python
recommend_combinations(
    stats: PatternStats,
    n_combinations: int = 5,
) -> list[Combination]
```

## 입력 계약
- `stats`는 `src/lotto/analytics/patterns.py`의 `PatternStats` 인스턴스여야 한다.
- `PatternStats`는 아래 5개 필드를 모두 포함한다.
  - `number_frequency`: `1..45` 번호별 출현 빈도
  - `consecutive_gaps`: 번호별 연속 등장 간격 요약
  - `odd_even_ratio`: 홀짝 비율 분포와 대표 비율
  - `section_distribution`: `1-10`, `11-20`, `21-30`, `31-40`, `41-45` 구간 누적 분포
  - `trend_weights`: 최근 회차 우선 가중치가 반영된 번호별 점수
- `n_combinations`는 1 이상의 정수여야 한다.

## 출력 계약
`Combination`은 아래 필드를 가진다.

```python
Combination(
    numbers=tuple[int, int, int, int, int, int],
    score=float,
    odd_even_ratio=str,
    section_distribution=dict[str, int],
)
```

- `numbers`는 오름차순 정렬된 6개 번호 튜플이다.
- `score`는 빈도, 최근 트렌드, 연속 등장 간격, 구간 균형 패널티를 합산한 최종 점수다.
- `odd_even_ratio`는 `홀수:짝수` 문자열이다.
- `section_distribution`은 조합 내부 번호의 구간별 개수다.

## 필수 제약
추천 결과에 포함되는 모든 조합은 아래 제약을 만족해야 한다.

1. 번호는 빈도 상위 70% 풀에서만 선택한다.
2. 홀짝 비율은 `3:3`, `4:2`, `2:4` 중 하나여야 한다.
3. 구간 분포는 최소 4개 구간에 걸쳐 퍼지고, 어떤 구간도 2개를 초과하지 않는다.
4. 최근 트렌드 가중치는 최종 스코어에 반영된다.

## 스코어링 방침
- 기본 점수:
  - 번호 빈도 합
  - 최근 트렌드 가중치 합
  - 번호별 평균 간격/마지막 간격 기반 보정치
- 보정:
  - `3:3` 비율에 소폭 가산점
  - 구간 분포가 과도하게 몰리면 패널티

## 오류 계약
- `ValueError`
  - `n_combinations <= 0` 인 경우 발생한다.

## 연결 메모
- 현재 구현은 결정적 정렬 기반으로 결과를 반환하므로 같은 `PatternStats` 입력에 대해 같은 결과를 돌려준다.
- 후보 조합 수가 요청 개수보다 적으면 가능한 개수만큼만 반환한다.
