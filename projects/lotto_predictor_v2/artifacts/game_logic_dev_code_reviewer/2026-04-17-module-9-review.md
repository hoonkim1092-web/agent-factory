# Code Review — game_logic_dev_module_9

- 작성 시각: 2026-04-17
- 리뷰어 역할: `game_logic_dev_code_reviewer`
- 대상 작업: `game_logic_dev_module_9_build_2`
- 리뷰 범위: `src/lotto_predictor/game_logic/**`, `tests/game_logic/test_engine.py`
- 결론 판정: **WARN** (BLOCK 없음, 개선 권고 다수)

## 리뷰 대상 파일
| 경로 | 역할 | 비고 |
| --- | --- | --- |
| `src/lotto_predictor/game_logic/engine.py` | 추천 엔진 상태 전이 구현 | 225 라인 |
| `src/lotto_predictor/game_logic/models.py` | 도메인 dataclass/Enum | frozen dataclass 기반 |
| `src/lotto_predictor/game_logic/errors.py` | 세 가지 예외 정의 | 의미 구분 명확 |
| `src/lotto_predictor/game_logic/__init__.py` | 공개 심볼 | `__all__`까지 포함 |
| `tests/game_logic/test_engine.py` | 단위 테스트 4개 | 정상 + 3종 예외 커버 |

## 보안 (OWASP)
- 네트워크·파일·DB·셸·역직렬화 없음. 순수 도메인 로직.
- 외부 입력은 `RecommendationRequest` 내부에서 전량 검증된 후 사용.
- **보안 이슈: 없음.**

## 버그 / 엣지 케이스
### B1. 연속 번호 검사는 정렬 전제에 묵시적으로 의존 — engine.py:190
```python
consecutive_pairs = sum(1 for left, right in zip(candidate, candidate[1:]) if right - left == 1)
```
- 현재는 `combinations(sorted_pool, 6)`이 lex 정렬된 튜플을 생성하므로 정확하다.
- 향후 `_build_candidate_pool` 반환 순서가 바뀌면 결과가 조용히 잘못될 수 있다.
- **권고**: `candidate_sorted = tuple(sorted(candidate))`로 명시 정렬하거나 docstring에 전제 기록.

### B2. `statistics_summary.sum_range`와 `config.min_sum/max_sum` 교차 불가 시 조용한 실패 — engine.py:186-189
```python
min_sum = max(config.min_sum, statistics_summary.sum_range[0])
max_sum = min(config.max_sum, statistics_summary.sum_range[1])
```
- 두 범위가 교차하지 않으면 `min_sum > max_sum`이 되어 모든 후보가 "합계 범위 위반"으로 탈락.
- 결과적으로 `InsufficientCandidateError`만 뜨고 원인이 드러나지 않는다.
- **권고**: `_validate_request`에 교차 불가 검출과 `RuleConflictError` 변환 추가.

### B3. `candidate_pool_size` 상한이 없음 — engine.py:78
- `candidate_pool_size < 6`만 검증. 상한이 없으므로 `45` 등 큰 값이 들어오면 `C(45,6)=8,145,060` 조합이 생성되어 O(n^6) 메모리·시간 폭증.
- 외부 호출자(Frontend)에서 값이 고정되기 전에는 방어가 약하다.
- **권고**: 안전 상한(예: `candidate_pool_size <= 20`)과 오류 계약 추가, 또는 문서에 명시적 상한 고정.

### B4. `number_last_seen` 의미론 모호 — engine.py:121 vs engine.py:207-209
- `_build_candidate_pool`은 `number_last_seen` 값이 **작을수록** 우선순위 상위로 취급.
- `_score_candidates`는 같은 값을 **클수록** 점수 상승으로 취급.
- 두 해석이 정반대이므로 동일 필드가 풀 구성과 점수화에서 반대로 작용할 수 있다.
- **권고**: `architecture.md`와 `StatisticsSummary` docstring에 "마지막 출현 이후 경과 회차 수" 같은 정의를 명시하고 두 함수를 같은 정의로 재정렬.

### B5. `_ScoredCandidate` 내부 클래스가 dataclass가 아님 — engine.py:220-224
- 프로젝트 전반이 `@dataclass(frozen=True)` 스타일인데 이 한 클래스만 수동 `__init__`이라 일관성이 깨짐.
- **권고**: `@dataclass(frozen=True, slots=True)` 사용 또는 `RecommendationResult` 사전 단계형으로 통일.

### B6. 사용되지 않는 `CandidateStage` 값 — models.py:11-17
- `INITIALIZED`, `GENERATED`, `VALIDATED`, `SCORED`가 코드 경로에서 한 번도 사용되지 않음.
- 실제 기록에 쓰이는 건 `RANKED`, `SELECTED`, `REJECTED` 세 개뿐.
- **권고**: 상태 전이 이력을 실제로 남기거나, 사용하지 않는 값은 제거하여 죽은 계약을 없앤다.

### B7. `fixed_numbers`/`excluded_numbers`는 `list` 우회 불가하지만 빈 컨테이너 엣지 — engine.py:86-87
- 기본값이 빈 tuple이므로 현재 테스트에서 문제 없음.
- 추가로 `number_frequency`/`recent_frequency`/`number_last_seen`가 빈 dict인 경우 `_build_candidate_pool`에서 모든 번호가 동점 → `number` 오름차순으로 풀이 구성된다. 동작은 일관적이지만 "통계 없음" 케이스에 대한 테스트가 없다. **권고**: 빈 통계 회귀 테스트 1건 추가.

## 설계 품질
- **단일 책임**: `RecommendationEngine.generate`는 검증 → 풀 → 생성 → 필터 → 점수 → 정렬 → 선택 파이프라인을 그대로 구현. private 메서드 분해가 잘 되어 있어 각 단계가 독립 테스트 가능하다. OK.
- **의존성 방향**: 순수 도메인 계층이며 외부 I/O 없음. `architecture.md §Game Logic Dev 구현 계약`의 "네트워크·저장·출력 금지" 제약을 충족. OK.
- **인터페이스 일관성**: frozen dataclass로 입출력 계약이 고정되어 있고 `__all__`도 정리되어 있다. 단 B5/B6의 잔여 일관성 결함 존재.
- **상태 전이 추적성**: architecture.md의 상태 전이(`초기화 → 생성 → 규칙 검증 → 점수화 → 정렬 → 최종 선택`)가 코드 실행 경로로는 관찰 불가. 설명적 enum이므로 테스트/로그에서의 가치가 제한적이다.

## 에러 처리
- 세 가지 예외 유형 모두 적절한 지점에서 발생시키고 테스트에서 검증된다.
- `InsufficientCandidateError` 발생 시 탈락 사유 통계(`rejected_candidates`)가 호출자에게 전파되지 않는다. 진단 편의상 예외에 rejection summary를 싣거나, 실패 시에도 `RecommendationBatch`(빈 recommendations)를 반환하고 호출자가 판단하도록 계약을 재고할 여지 있음. **WARN**.

## 성능
- `_generate_candidates`에서 `set(config.fixed_numbers)`를 매 후보마다 재생성. 후보 수가 커지면 불필요한 반복 비용. **권고**: 루프 외부에서 `fixed_set = frozenset(config.fixed_numbers)` 캐시.
- `_find_rejection_reason`에서 `any(number in config.excluded_numbers for number in candidate)` 호출. `excluded_numbers`가 tuple일 때 O(n*m). **권고**: `excluded_set = frozenset(config.excluded_numbers)`로 치환.
- `_score_candidates` 루프 내부 dict `.get()`은 상수 시간으로 OK.
- 기본값(`candidate_pool_size=12`)에서는 조합 수 924로 실무 부담 없음. 다만 B3의 상한 부재는 남아 있음.

## 테스트 품질
- `test_engine.py`의 4개 케이스가 정상 경로 + 세 종류 예외를 커버한다.
- 누락:
  - 빈 `number_frequency`/`recent_frequency` 입력.
  - `config.min_sum`과 `statistics_summary.sum_range`가 겹치지 않는 경우(현재는 `InsufficientCandidateError`가 뜨지만 계약이 모호).
  - `max_consecutive_pairs=0`인 타이트 제약.
- **권고**: 상기 3건을 추후 `game_logic` 회귀 테스트에 보강.

## 판정 요약 (JSON)
```json
{
  "verdict": "WARN",
  "issues": [
    {
      "id": "B1",
      "severity": "low",
      "file": "src/lotto_predictor/game_logic/engine.py",
      "line": 190,
      "title": "연속 번호 검사가 정렬 전제에 묵시적으로 의존",
      "recommendation": "candidate를 명시적으로 sorted로 처리하거나 전제를 docstring에 기록"
    },
    {
      "id": "B2",
      "severity": "medium",
      "file": "src/lotto_predictor/game_logic/engine.py",
      "line": 186,
      "title": "config와 statistics_summary의 sum_range가 교차하지 않으면 원인 불명 실패",
      "recommendation": "_validate_request에 교차 불가 검출과 RuleConflictError 변환 추가"
    },
    {
      "id": "B3",
      "severity": "medium",
      "file": "src/lotto_predictor/game_logic/engine.py",
      "line": 78,
      "title": "candidate_pool_size 상한 부재로 조합 폭증 가능",
      "recommendation": "안전 상한(예: 20) 또는 호출자 계약 명시"
    },
    {
      "id": "B4",
      "severity": "medium",
      "file": "src/lotto_predictor/game_logic/engine.py",
      "line": 121,
      "title": "number_last_seen 의미론이 풀 구성과 점수화에서 반대로 해석",
      "recommendation": "필드 정의를 architecture.md에 명시하고 두 함수에서 동일 의미로 사용"
    },
    {
      "id": "B5",
      "severity": "low",
      "file": "src/lotto_predictor/game_logic/engine.py",
      "line": 220,
      "title": "_ScoredCandidate가 dataclass가 아니어서 일관성 저하",
      "recommendation": "@dataclass(frozen=True, slots=True) 적용"
    },
    {
      "id": "B6",
      "severity": "low",
      "file": "src/lotto_predictor/game_logic/models.py",
      "line": 11,
      "title": "사용되지 않는 CandidateStage 값 다수",
      "recommendation": "상태 추적을 실제 기록하거나 미사용 값을 제거"
    },
    {
      "id": "P1",
      "severity": "low",
      "file": "src/lotto_predictor/game_logic/engine.py",
      "line": 140,
      "title": "combinations 루프 내 set(fixed_numbers) 재생성",
      "recommendation": "루프 외부에서 frozenset으로 캐시"
    },
    {
      "id": "P2",
      "severity": "low",
      "file": "src/lotto_predictor/game_logic/engine.py",
      "line": 180,
      "title": "excluded_numbers tuple 포함 검사 O(n*m)",
      "recommendation": "frozenset으로 치환"
    },
    {
      "id": "T1",
      "severity": "info",
      "file": "tests/game_logic/test_engine.py",
      "line": 0,
      "title": "빈 통계, sum_range 교차 불가, max_consecutive_pairs=0 케이스 누락",
      "recommendation": "회귀 테스트 3건 보강"
    }
  ],
  "summary": "보안 이슈 없음. 명백한 치명 버그도 없음. 다만 sum_range 교차 불가 시 원인 불명 실패(B2), candidate_pool_size 상한 부재(B3), number_last_seen의 반대 해석(B4)은 실사용 시 잘못된 추천을 초래하거나 성능 장애를 유발할 수 있다. 설계·성능 권고 사항과 테스트 보강을 다음 작업 싸이클에 반영할 것을 권장한다. 현 상태 그대로 진행 가능(PASS가 아닌 WARN)."
}
```

[game_logic_dev_code_reviewer] 작업 결과를 파일로 남깁니다.
