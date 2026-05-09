# Game Logic Dev Handoff

## 목적
이 문서는 `Game Logic Dev` 구현 결과를 검증한 뒤, 후속 `frontend_dev` 작업자가 통계 분석 엔진과 추천기 모듈을 즉시 연결할 수 있도록 현재 인터페이스 계약과 잔여 리스크를 고정한다.

## 검증 결과
- 검증 일자: 2026-04-17
- 검증 대상:
  - `src/lotto_predictor/game_logic/models.py`
  - `src/lotto_predictor/game_logic/engine.py`
  - `src/lotto_predictor/game_logic/errors.py`
  - `tests/game_logic/test_engine.py`
- 실행 명령:
  - `PYTHONPATH=src python -m unittest tests.game_logic.test_engine`
- 실행 결과:
  - 단위 테스트 4건 통과
  - 정상 추천 배치 생성 1건
  - 예외 경로 검증 3건
    - 빈 회차 이력 → `InvalidRequestError`
    - 충돌 규칙 → `RuleConflictError`
    - 후보 부족 → `InsufficientCandidateError`
- 코드 리뷰 상태:
  - `artifacts/game_logic_dev_code_reviewer/2026-04-17-module-9-review.md`
  - 판정: `WARN`
  - 치명적 BLOCK 없음, 다만 후속 통계 엔진과 연결할 때 명시해야 할 계약상 리스크가 남아 있음

## 구현 책임 경계
- `RecommendationEngine`은 순수 도메인 로직만 담당한다.
- 외부 API 호출, 저장소 조회, 캐시 갱신, 통계 산출, CLI 렌더링은 담당하지 않는다.
- 후속 `frontend_dev`는 통계 엔진에서 계산한 값을 `StatisticsSummary`로 정규화해 `RecommendationRequest`에 넣어야 한다.

## 공개 인터페이스 계약
### 입력 형식
```python
RecommendationRequest(
    draw_history=list[LottoDraw],
    statistics_summary=StatisticsSummary,
    config=RecommendationConfig,
)
```

```python
LottoDraw(
    draw_no=int,
    numbers=tuple[int, int, int, int, int, int],
    bonus_number=int | None,
)

StatisticsSummary(
    number_frequency=dict[int, int],
    recent_frequency=dict[int, int] = {},
    number_last_seen=dict[int, int] = {},
    sum_range=tuple[int, int] = (100, 175),
)

RecommendationConfig(
    target_count=int = 5,
    candidate_pool_size=int = 12,
    min_odd_count=int = 2,
    max_odd_count=int = 4,
    min_sum=int = 100,
    max_sum=int = 175,
    max_consecutive_pairs=int = 1,
    excluded_numbers=tuple[int, ...] = (),
    fixed_numbers=tuple[int, ...] = (),
)
```

### 출력 형식
```python
RecommendationBatch(
    recommendations=list[RecommendationResult],
    rejected_candidates=list[RejectionReasonSummary],
    evaluation_summary=EvaluationSummary,
)
```

```python
RecommendationResult(
    numbers=tuple[int, int, int, int, int, int],
    score=float,
    odd_even_ratio=str,
    sum_total=int,
    matched_fixed_numbers=tuple[int, ...],
    stage=CandidateStage.SELECTED,
)

RejectionReasonSummary(
    reason=str,
    count=int,
)

EvaluationSummary(
    requested_count=int,
    generated_candidates=int,
    validated_candidates=int,
    scored_candidates=int,
    selected_candidates=int,
    candidate_pool=tuple[int, ...],
)
```

## 상태 전이 계약
- 엔진의 논리 단계는 `초기화 -> 생성 -> 규칙 검증 -> 점수화 -> 정렬 -> 최종 선택`이다.
- 현재 구현에서 외부로 노출되는 최종 상태는 다음 두 종류다.
  - 추천 성공 후보: `CandidateStage.SELECTED`
  - 탈락 후보 요약: `rejected_candidates[].reason`
- 중간 단계(`INITIALIZED`, `GENERATED`, `VALIDATED`, `SCORED`, `RANKED`)는 설계상 enum으로 존재하지만, 현재 배치 결과에 개별 이력으로 기록되지는 않는다.
- `frontend_dev`가 단계별 UI 또는 리포트를 만들려면 현재 구현만으로는 후보별 중간 이력을 얻을 수 없고, `RecommendationBatch` 수준 집계만 사용할 수 있다.

## 통계 엔진과의 연결 계약
후속 `frontend_dev` 통계 엔진은 아래 5개 규칙 입력을 `StatisticsSummary`와 `RecommendationConfig`에 나눠 공급해야 한다.

### 1. 빈도 패턴 연결
- 공급 위치:
  - `StatisticsSummary.number_frequency`
- 의미:
  - 최근 500회차 전체에서 번호별 출현 횟수
- 사용 방식:
  - 후보 풀 우선순위 산정
  - 최종 점수 계산의 기본 가중치
- 형식 제약:
  - key: `1..45`
  - value: `0` 이상 정수
  - 누락 key는 `0`으로 처리된다

### 2. 트렌드 패턴 연결
- 공급 위치:
  - `StatisticsSummary.recent_frequency`
  - `StatisticsSummary.number_last_seen`
- 의미:
  - `recent_frequency`: 최근 N회차 가중 빈도 또는 최근 구간 출현 횟수
  - `number_last_seen`: 번호의 최근성 지표
- 사용 방식:
  - 후보 풀 정렬 보조 키
  - 최종 점수 가산
- 중요 계약:
  - `number_last_seen` 의미를 `frontend_dev`에서 먼저 고정해야 한다.
  - 현재 엔진은 후보 풀 구성에서는 값이 작을수록 우선, 점수화에서는 값이 클수록 가산한다.
  - 즉, 이 필드는 "최근 출현 회차 번호"인지 "마지막 출현 이후 경과 회차 수"인지 해석이 충돌할 수 있다.
  - 후속 작업자는 통계 엔진 문서와 구현에서 이 의미를 하나로 고정하고, 필요하면 엔진 보정 작업을 별도 이슈로 분리해야 한다.

### 3. 홀짝 패턴 연결
- 공급 위치:
  - `RecommendationConfig.min_odd_count`
  - `RecommendationConfig.max_odd_count`
- 의미:
  - 한 조합의 홀수 개수 허용 범위
- 사용 방식:
  - 후보 검증 단계에서 즉시 필터
- 실패 사유:
  - `홀짝 비율 위반`

### 4. 연속 패턴 연결
- 공급 위치:
  - `RecommendationConfig.max_consecutive_pairs`
- 의미:
  - 한 조합 안에서 허용되는 연속 번호 쌍의 최대 개수
- 사용 방식:
  - 정렬된 후보 튜플 기준으로 인접 차이가 `1`인 쌍의 수를 계산
- 실패 사유:
  - `연속 번호 위반`
- 주의:
  - 현재 구현은 `candidate`가 정렬된 튜플이라는 전제에 기대고 있다.
  - 조합 생성 경로가 바뀌지 않는 한 동작하지만, 다른 후보 생성기를 붙일 경우 정렬 보장이 필요하다.

### 5. 구간 패턴 연결
- 공급 위치:
  - 직접적인 `range_distribution` 입력 필드는 없음
  - 현재 엔진은 구간 패턴을 `sum_range`와 후보 spread 점수로 간접 반영한다
- 의미:
  - 통계 엔진이 계산하는 1-10 / 11-20 / 21-30 / 31-40 / 41-45 분포는 현재 추천 엔진의 직접 필터 조건이 아니다
- 현재 연결 방식:
  - `StatisticsSummary.sum_range`
  - 점수화 시 `candidate[-1] - candidate[0]` spread 가산
- 영향:
  - 후속 `frontend_dev`는 구간 분포를 리포트용 지표로 먼저 제공할 수 있지만, 추천 엔진이 그 분포를 직접 강제하지는 않는다
  - 구간 분포를 직접 필터링하려면 `RecommendationConfig` 확장이 필요하며, 이는 이번 handoff 범위 밖이다

## 추천기 호출 순서
`frontend_dev`가 통계 엔진과 연결할 때의 권장 순서는 아래와 같다.

1. 저장소 또는 캐시에서 최근 500회차 `LottoDraw` 목록을 확보한다.
2. 통계 엔진이 빈도, 최근 빈도, 마지막 출현 관련 값, 합계 범위를 계산한다.
3. 계산 결과를 `StatisticsSummary`로 정규화한다.
4. 사용자 기본 정책 또는 화면 입력을 `RecommendationConfig`로 정규화한다.
5. `RecommendationRequest(draw_history, statistics_summary, config)`를 생성한다.
6. `RecommendationEngine.generate(request)`를 호출한다.
7. 성공 시 `RecommendationBatch`를 소비하고, 실패 시 예외 유형에 따라 사용자 메시지 또는 fallback을 결정한다.

## 예외 케이스 계약
### `InvalidRequestError`
- 발생 조건:
  - `draw_history`가 비어 있음
  - `target_count <= 0`
  - `candidate_pool_size < 6`
  - 번호 범위가 `1..45`를 벗어남
  - 회차 번호가 1 미만
  - 회차 번호 튜플이 중복 포함 또는 6개 미만/초과
  - `fixed_numbers` 또는 `excluded_numbers` 내부 중복
- 후속 작업자 대응:
  - 통계 엔진/추천기 통합 레이어에서 호출 전 검증 가능
  - 사용자 입력 오류와 데이터 정규화 오류를 분리해 노출하는 편이 좋다

### `RuleConflictError`
- 발생 조건:
  - `min_odd_count > max_odd_count`
  - `min_sum > max_sum`
  - `fixed_numbers`와 `excluded_numbers`가 충돌
  - `fixed_numbers`가 6개 초과
  - 제외 규칙 때문에 후보 풀 6개를 채울 수 없음
  - 고정 번호 조건을 만족하는 조합 생성 불가
- 후속 작업자 대응:
  - 정책 충돌로 간주하고 재설정 유도
  - 사용자가 지정한 필터 조합을 그대로 다시 보여주는 것이 좋다

### `InsufficientCandidateError`
- 발생 조건:
  - 생성된 후보 중 규칙을 모두 통과한 개수가 `target_count`보다 적음
- 현재 한계:
  - 예외 발생 시 `rejected_candidates` 요약이 함께 전달되지 않는다
  - 즉, 어떤 규칙 때문에 부족해졌는지 호출자가 직접 알 수 없다
- 후속 작업자 대응:
  - 일단 "조건을 완화하라"는 메시지로 처리 가능
  - 진단 상세가 필요하면 Game Logic Dev 후속 개선이 필요하다

## frontend_dev 즉시 작업 기준
다음 작업자는 아래 항목을 기준으로 바로 통계 엔진을 구현하면 된다.

### 반드시 맞춰야 하는 것
- `draw_history`는 정렬 여부와 무관하지만 각 `numbers`는 중복 없는 6개여야 한다.
- `StatisticsSummary.number_frequency`는 최소한 채워야 한다.
- `StatisticsSummary.recent_frequency`, `number_last_seen`는 비어 있어도 엔진은 동작한다.
- `sum_range`는 통계 엔진이 산출한 합계 허용 범위를 넣되, `RecommendationConfig.min_sum/max_sum`와의 교집합을 고려해야 한다.
- `candidate_pool_size`는 조합 폭증을 피하기 위해 호출부에서 보수적으로 제한해야 한다. 현재 기본값 `12` 유지가 안전하다.

### 바로 이어서 해야 할 일
- `number_last_seen`의 의미를 통계 엔진 문서에서 하나로 고정한다.
- `sum_range`와 `config.min_sum/max_sum`의 충돌 시 정책을 통합 레이어에서 선검증한다.
- 구간 분포 지표는 우선 리포트/시각화용으로 산출하고, 추천 엔진 직접 필터는 별도 변경으로 분리한다.
- 실패 시 사용자에게 보여줄 메시지를 예외 타입별로 분기한다.

## 잔여 리스크
- `number_last_seen` 의미가 아직 단일 정의로 고정되지 않았다.
- `candidate_pool_size` 상한이 코드상 강제되지 않아 큰 값 입력 시 조합 수가 급증할 수 있다.
- `statistics_summary.sum_range`와 `config.min_sum/max_sum`가 교차하지 않으면 원인 설명 없이 후보 부족으로 끝날 수 있다.
- `rejected_candidates`는 성공 시에만 반환되므로 실패 진단성이 제한된다.
- 구간 패턴은 현재 직접 규칙이 아니라 간접 지표 수준이다.

## 후속 작업 메모
- 이번 단계에서는 설계 수준 변경 없이 기존 구현 검증과 handoff 문서화만 수행했다.
- 따라서 `docs/architecture.md`, `docs/change_history.md`는 갱신하지 않았다.
- 런타임에 `read_mailbox`/`send_mailbox_message` 도구가 노출되지 않아 메일박스 기반 handoff는 수행하지 못했고, 파일 handoff로 대체한다.
