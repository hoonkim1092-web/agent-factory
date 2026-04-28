# Code Review — frontend_dev_module_2 (회차 데이터 로컬 캐시 저장소)

- 작성 시각: 2026-04-17
- 리뷰어 역할: `frontend_dev_code_reviewer`
- 대상 작업: `frontend_dev_module_2_build_2`
- 리뷰 범위: `src/lotto_predictor/cache/**`, `tests/cache/**`
- 결론 판정: **WARN** (BLOCK 없음. 동작·계약 적합. 성능·tz 안전성 권고만 남김)

## 리뷰 대상 파일
| 경로 | 역할 | 비고 |
| --- | --- | --- |
| `src/lotto_predictor/cache/__init__.py` | 공개 심볼 재노출 | `__all__` 정상, 내부 모듈 직접 import 차단 의도 |
| `src/lotto_predictor/cache/models.py` | 데이터 계약(Config·Status·ReadyResult·GapReport) | frozen + `__post_init__` 불변식 검증 |
| `src/lotto_predictor/cache/core.py` | `LottoDrawCache` 정책 계층 | status / ensure_ready / 읽기 API / continuity |
| `tests/cache/_fakes.py` | `FakeStorage`, `FakeCollector`, `fixed_clock` | Backend·Collector 계약 준수 |
| `tests/cache/test_cache_status.py` | 상태 판정 9 케이스 | parametrize 포함 |
| `tests/cache/test_cache_ensure_ready.py` | 분기 6 케이스 | offline/never/skip/synced/aborted |
| `tests/cache/test_cache_reads.py` | 읽기 API 7 케이스 | n<=0 차단 포함 |
| `tests/cache/test_cache_continuity.py` | 누락 구간 5 케이스 | 빈 저장소·중간 누락·offset |

## 검증 결과
- `python -m pytest tests/cache -v` → **27 passed** (0.31s).
- `python -m py_compile src/lotto_predictor/cache/*.py` → OK.
- Scope 문서(`docs/plans/2026-04-17-회차-로컬-캐시-저장소-범위.md`)의 공개 인터페이스·구현 순서·완료 기준과 모두 일치.

## 보안 (OWASP)
- 본 모듈은 HTTP/SQL/역직렬화를 직접 수행하지 않음(저장소·수집기 위임). 인젝션 표면 없음. ✓
- 로깅은 `%s` 포맷터를 통한 lazy formatting 사용 → 로그 인젝션·KeyError 위험 없음. ✓
- 외부 입력은 `n: int`, `draw_no: int` 두 개뿐이며 양수 검증으로 조기 차단. ✓
- `runtime_checkable Protocol` 사용. duck typing 신뢰 의존이지만 컴파일 타임 isinstance 호출 부재 → 악용 표면 없음. ✓
- 민감 정보 로깅 없음(회차 번호와 reason 라벨만). ✓
- **보안 이슈: 없음.**

## 버그 / 엣지 케이스

### B1. `ensure_ready()` 가 `status()` 를 두 번 호출 — 전체 회차 I/O 2배 (WARN-Med)
`core.py:105, 130`
```python
current = self.status()             # get_checkpoint + get_draws()  ← 1차
...
sync_result = self._collector.sync_incremental()
refreshed = self.status()           # get_checkpoint + get_draws()  ← 2차
```
- `status()` 는 `LottoStorage.get_draws()` 를 limit 없이 호출하므로(`core.py:85`) 보유 회차 전부를 메모리로 끌어온다. 기본 `required_draws=500` 기준 매 호출 500행.
- stale → synced 경로에서 **500행 × 2회** I/O. 단일 스레드 SQLite 환경에선 실측 영향이 작지만, 의도와 다르게 매 회차 전부를 두 번 직렬화·역직렬화하는 구조이므로 정리 여지가 분명하다.
- 부수 효과: 1차 `status()` 결과는 `current.is_stale` 판정용으로만 쓰이고 폐기됨.
- **권고 (택1)**
  1. 1차 호출에서 받은 `current` 와 `sync_result` 를 합쳐 `_compute_status` 를 한 번 더 돌리는 대신, **동일 인메모리 결과로 재계산**(stale 분기 진입 시 한 번만 SQL).
  2. Backend Dev 와 협의해 `count_draws()` 또는 `get_draw_summary()` (count/min/max/last_no) 를 추가, `status()` 가 회차 전체를 끌어오지 않도록 변경.
- 현재 규모(500회차)에서는 "기능 결함" 이 아니므로 BLOCK 은 아니나, 본 모듈이 통계 엔진(`module_3`) 호출 직전 매번 실행될 가능성이 있어 사전 정리 권고.

### B2. `_is_checkpoint_expired` — naive ↔ aware datetime 비교 시 `TypeError` 가능 (WARN-Low)
`core.py:231-236`
```python
now = self._clock()
...
elapsed = now - checkpoint.fetched_at
return elapsed >= timedelta(hours=self._config.freshness_hours)
```
- 기본 `clock=datetime.now` 는 **naive** datetime 을 반환한다.
- `FetchCheckpoint.fetched_at` 의 tzinfo 정책은 Backend Dev 직렬화 계약에 의존한다(현재 Backend 가 ISO 문자열로 저장하고 fromisoformat 으로 복원 시 tz 가 들어 있으면 aware, 없으면 naive). 둘 중 하나가 aware 라면 `TypeError: can't subtract offset-naive and offset-aware datetimes` 가 발생해 `_is_checkpoint_expired` 가 그대로 전파(B3 의 broad except 는 `clock()` 만 감싸므로 잡히지 않음).
- 단위 테스트는 naive vs naive 만 검증하므로 회귀를 잡지 못함.
- **권고**
  1. `_compute_status` 진입 직전에 두 시각을 동일 정책으로 정규화(예: 둘 다 naive 로 캐스팅 또는 둘 다 `astimezone(timezone.utc)`).
  2. 또는 docstring 에 "`clock()` 과 `FetchCheckpoint.fetched_at` 은 동일 tzinfo 정책이어야 한다" 명시.

### B3. `_is_checkpoint_expired` — clock 예외 시 만료 판정 우회 (WARN-Low)
`core.py:230-234`
```python
try:
    now = self._clock()
except Exception:
    self._logger.exception("clock 호출 실패 — 체크포인트 만료 판정을 건너뛴다")
    return False
```
- clock 호출 실패시 "만료 아님" 으로 폴백 → 캐시가 실제로 오래되었는데도 sync 가 발생하지 않을 수 있다. **신선도 판정의 안전 기본값은 보통 "보수적으로 만료"** 가 자연스럽다.
- 또한 표준 `datetime.now` 는 일반적으로 예외를 내지 않으므로 이 try/except 는 fake clock 의 회귀를 숨기는 역할만 한다.
- **권고**: `return True`(만료로 보수 처리)로 바꾸거나 broad except 자체를 제거하고 호출자에게 전파.

### B4. `_compute_status` — `ensure_ready` 결과 재계산이 status() 의 성공 분기 누락 가능성 (WARN-Low)
- `ensure_ready` 가 sync 직후 `self.status()` 만 다시 호출하므로 `sync_result.failures` 정보가 `CacheStatus` 에는 반영되지 않는다.
- 호출자는 `result.sync_result.failures` 를 별도로 읽어야 부분 실패를 인지할 수 있다(스코프 문서의 의도와 일치).
- 해당 동작이 의도라면 `CacheReadyResult` 의 docstring 에 "`status` 는 부분 실패 정보를 포함하지 않는다 — `sync_result.failures` 를 함께 점검하라" 한 줄 추가 권고.

### B5. `CacheGapReport.__post_init__` — `missing=()` 인데 `is_continuous=False` 허용 (WARN-Low)
`models.py:145-147`
```python
if self.missing_draws and self.is_continuous:
    raise ValueError(...)
```
- 검증은 한쪽 방향만 수행. 반대 케이스(누락 없음 + `is_continuous=False`)는 통과한다.
- 호출자 프로그래밍 오류로만 발생 가능하므로 위험은 낮으나, 불변식이 비대칭이다.
- **권고**: 대칭으로 검증 추가.
  ```python
  if (not self.missing_draws) and (not self.is_continuous):
      raise ValueError("missing_draws 가 비었는데 is_continuous=False — 정합성 어긋남")
  ```

### B6. `validate_continuity` — `latest - earliest` 가 매우 클 때 range 비용 (PASS)
`core.py:182`
```python
missing = tuple(no for no in range(earliest, latest + 1) if no not in stored)
```
- 현실 회차 규모(~1100)에서는 무시 가능. 백필 시나리오에서도 안전.
- 향후 서비스 범위가 확장되더라도 회차 정의상 단조 증가 정수이므로 추가 안전망 불필요.

### B7. `_fakes.FakeStorage.get_draws(limit=0)` 동작과 캐시 계약 일관성 (PASS-info)
- Backend Dev `LottoStorage.get_draws(limit=0)` 는 빈 리스트를 반환(SQL `LIMIT 0`).
- 캐시의 `get_recent_draws(0)` 는 `ValueError` (조기 차단). Scope 문서 명시 결정과 일치하므로 계약 일관됨. ✓

## 설계 품질

### D1. 단일 스레드 사용 가정 미명시 (info)
- `LottoDrawCache` 는 락 없이 `status()` → `ensure_ready()` 흐름을 가진다. 멀티 스레드(예: GUI 메인 스레드 + 백그라운드 워커)에서 동시에 호출되면 `current` 와 `refreshed` 사이에 다른 스레드가 데이터를 갱신해 race condition 가능.
- **권고**: 클래스 docstring 에 "단일 스레드 사용 가정. 동시 호출이 필요하면 외부에서 직렬화하라" 명시.

### D2. `_CollectorLike` Protocol — 좋은 분리 (PASS)
- `runtime_checkable` 프로토콜로 LottoCollector 구체에 강결합되지 않음. 테스트 fake 주입 용이. 의존성 방향(상위 정책 → 하위 인터페이스) 적절.

### D3. 모델 검증 일관성 (PASS)
- `CacheConfig`/`CacheStatus`/`CacheReadyResult` 가 `__post_init__` 으로 자기 일관성을 강제. 호출자가 `frozen=True` 덕분에 사후 변형이 불가능 → 도메인 객체로서 안정.

### D4. 의존성 방향 (PASS)
- `cache → backend` (LottoStorage), `cache → collector` 단방향. 역방향 import 없음. SQL 발행 0회. Scope 의 책임 경계 그대로 구현됨.

## 에러 처리

### E1. 수집기 예외 비포착 (PASS)
- `collector.sync_incremental()` 이 예외를 던지면 그대로 전파. Scope 의 "저장소 예외는 캐시에서 잡지 않고 호출자에게 전파" 정책과 일관.
- `aborted` 인 정상 종료는 `CacheReadyResult.sync_result` 로 보존. 테스트로도 검증됨(`test_ensure_ready_preserves_sync_result_even_on_aborted`).

### E2. `get_recent_draws/get_draw` 입력 검증 (PASS)
- `n<=0`, `draw_no<=0` 모두 `ValueError` 로 조기 차단. 메시지 한국어. 한국어 메시지 정책 준수.

## 성능
- B1·P1: `status()` 가 회차 전부를 두 번 로드하는 구조가 유일한 "정리 권고" 항목.
- `validate_continuity` 의 set 멤버십 검사: `O(n)`. 안전.
- `get_recent_draws` 는 `LottoStorage.get_draws(limit=n)` 를 그대로 위임 → SQL `LIMIT n`. 효율적.

## 한국어/문서 정책 준수
- 모든 docstring·로그·예외 메시지 한국어. ✓
- `docs/architecture.md` 에 캐시 모듈 섹션 추가됨. ✓
- `docs/change_history.md` 에 `frontend_dev_module_2_build_2` 항목 추가됨. ✓
- Scope 문서의 공개 인터페이스·구현 순서·완료 기준 모두 충족. ✓

## 종합 판정
- **WARN** — BLOCK 사유 없음. 27/27 테스트 통과, 계약 준수, 보안 표면 없음.
- 후속 모듈(`frontend_dev_module_3` 통계 분석 엔진) 진행 가능.
- 후속 처리 권고 (BLOCK 아님, 다음 사이클 또는 별도 task 로):
  1. **B1 / P1**: `ensure_ready` 가 `status()` 를 두 번 호출하는 구조 정리. 단일 호출 + sync 후 재계산 한 번으로 축소.
  2. **B2**: tz-aware/naive datetime 정규화 또는 docstring 명시.
  3. **B3**: `_is_checkpoint_expired` 의 clock broad-except 제거 또는 보수적 만료(`return True`) 처리.
  4. **B5**: `CacheGapReport` 의 정합성 검증 대칭 보강.
  5. **D1**: 단일 스레드 사용 가정 docstring 명시.

## JSON 요약
```json
{
  "verdict": "WARN",
  "issues": [
    {
      "id": "B1",
      "severity": "WARN-Med",
      "title": "ensure_ready 가 status() 두 번 호출하여 회차 전체 I/O 가 2배",
      "file": "src/lotto_predictor/cache/core.py",
      "lines": "105,130"
    },
    {
      "id": "B2",
      "severity": "WARN-Low",
      "title": "naive/aware datetime 혼용 시 TypeError 가능",
      "file": "src/lotto_predictor/cache/core.py",
      "lines": "231-236"
    },
    {
      "id": "B3",
      "severity": "WARN-Low",
      "title": "clock 예외 시 만료 판정 우회 — 보수적 처리 권고",
      "file": "src/lotto_predictor/cache/core.py",
      "lines": "230-234"
    },
    {
      "id": "B4",
      "severity": "WARN-Low",
      "title": "ensure_ready.status 는 sync_result.failures 를 반영하지 않음 — docstring 보강 권고",
      "file": "src/lotto_predictor/cache/models.py",
      "lines": "97-118"
    },
    {
      "id": "B5",
      "severity": "WARN-Low",
      "title": "CacheGapReport 정합성 검증이 한쪽 방향만 수행",
      "file": "src/lotto_predictor/cache/models.py",
      "lines": "145-147"
    },
    {
      "id": "D1",
      "severity": "info",
      "title": "단일 스레드 사용 가정이 docstring 에 명시되지 않음",
      "file": "src/lotto_predictor/cache/core.py",
      "lines": "46-55"
    }
  ],
  "summary": "27/27 단위 테스트 통과, 보안 이슈 없음, 스코프 계약 일치. 성능(B1)과 tz 안전성(B2), 보수적 폴백(B3), 모델 검증 대칭(B5), 스레드 가정(D1)에 대한 권고만 남기고 PASS-with-WARN 으로 판정. 다음 모듈 진행 가능."
}
```

[frontend_dev_code_reviewer] 작업 결과를 파일로 남깁니다.
