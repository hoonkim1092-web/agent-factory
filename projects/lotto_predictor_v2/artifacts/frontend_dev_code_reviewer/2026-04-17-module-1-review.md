# Code Review — frontend_dev_module_1 (동행복권 회차 수집기)

- 작성 시각: 2026-04-17
- 리뷰어 역할: `frontend_dev_code_reviewer`
- 대상 작업: `frontend_dev_module_1_build_2`
- 리뷰 범위: `src/lotto_predictor/collector/**`, `tests/collector/**`
- 결론 판정: **WARN** (BLOCK 없음, 동작 가능. 데이터 정합성·분류 정밀도 개선 권고 다수)

## 리뷰 대상 파일
| 경로 | 역할 | 비고 |
| --- | --- | --- |
| `src/lotto_predictor/collector/__init__.py` | 공개 심볼 재노출 | `__all__` 정상 |
| `src/lotto_predictor/collector/models.py` | 데이터 계약(Config·Failure·Result) | frozen + `__post_init__` 검증 |
| `src/lotto_predictor/collector/core.py` | `LottoCollector` 오케스트레이션 | detect / sync_range / sync_incremental |
| `tests/collector/_fakes.py` | `FakeClient`, `FakeStorage` | Backend Dev 계약 준수 |
| `tests/collector/test_collector_sync.py` | 증분 수집 플로우 | 5개 테스트 |
| `tests/collector/test_collector_detect.py` | 최신 회차 탐색 | 7개 테스트 |
| `tests/collector/test_collector_failures.py` | 실패/연속 실패 중단 | 3개 테스트 |

## 검증 결과
- `python -m pytest tests/collector -q` → **19 passed** (0.12s).
- `python -m py_compile src/lotto_predictor/collector/*.py` → OK.

## 보안 (OWASP)
- 모듈은 HTTP/SQL/역직렬화 자체를 수행하지 않음(Backend Dev 위임). 인젝션 표면 없음. ✓
- `_SOURCE_URL`은 상수 문자열(쿼리 파라미터 없음), 사용자 입력이 주입되지 않음. ✓
- 외부 응답은 `parse_draw` 계약에 의해 타입·범위 검증 후 도메인 타입 진입. ✓
- 로그에 회차 번호/예외 메시지만 기록(민감정보 없음). ✓
- 브로드 캐치(`except Exception`)가 있으나 `KeyboardInterrupt`/`SystemExit`은 `BaseException`이라 포획되지 않음. ✓
- **보안 이슈: 없음.**

## 버그 / 엣지 케이스

### C1. `sync_incremental` — 일시 실패 시 체크포인트가 갭을 넘어 전진 (데이터 정합성, WARN-Hi)
`core.py:248-257`
```python
if outcome.reason in ("transient", "rate_limited"):
    consecutive_transient += 1
    if consecutive_transient >= self._config.abort_on_consecutive_failures:
        stopped_reason = "aborted"
        break
    # 같은 회차를 재시도하지 않고 다음 회차로 전진
    draw_no += 1
```
- 시퀀스: 1→2→3(transient)→4(성공) 로 진행되면 `last_success=4`, 이어서 checkpoint가 4로 갱신된다(`core.py:263-266`).
- 다음 `sync_incremental` 실행 시 start=5로 시작하므로 **회차 3은 영구적으로 저장소에 누락**되며, 재호출로 복구되지 않는다. 오직 `sync_range(3,3)`로 수동 백필해야 채워진다.
- `SyncResult.failures`에는 기록되지만, 호출자가 이를 반드시 재시도한다는 보장이 없고 기본 사용 시나리오(main에서 `sync_incremental` 반복 호출)에서 조용히 갭이 누적된다.
- 연관 테스트 `test_성공_사이의_일시_실패는_연속_카운터를_초기화한다`가 이 동작을 명시적으로 수용하므로 설계 의도는 확인된다. 다만 운영 관점에서 위험하다.
- **권고 (택1)**
  1. `last_success`를 "최초 실패 이전까지의 최대 성공 회차"로 정의 → 갭 이전 값으로만 체크포인트 전진.
  2. 별도 `missing_draws` 테이블을 두고 다음 주기에 우선 재시도.
  3. 최소 대응: docstring과 `change_history`에 "sync_incremental은 실패 회차를 건너뛰며 체크포인트를 전진시킴. 갭 복구는 `sync_range`로 수동 처리 필요" 명시.

### C2. `_fetch_one` — 파서 `ValueError`가 `unknown`으로 분류되어 연속 실패 중단을 우회 (WARN-Med)
`core.py:298-301`, `core.py:248`
```python
except ValueError as exc:
    self._logger.error("payload 파싱 실패: drw_no=%s error=%s", draw_no, exc)
    return _FetchOutcome(draw=None, reason="unknown", detail=str(exc))
```
- `sync_incremental`/`sync_range` 공통: `reason == "unknown"`인 실패는 `consecutive_transient`를 0으로 리셋한다(`core.py:158-159`, `core.py:255-257`).
- 동행복권 응답 포맷이 전면적으로 변경되거나, Backend Dev `parse_draw`에 스키마 드리프트가 생기면 500회차 전부 `ValueError` → 모두 `unknown`으로 수집되고 `stopped_reason="caught_up"`으로 정상 종료된 것처럼 보인다. 대량 침묵 실패 시나리오.
- **권고**: 파서 `ValueError`는 `reason="schema_error"`(새로 도입)로 별도 분류하거나, 적어도 `transient`와 동일하게 연속 실패 카운터에 집계. 또는 N회 연속 `unknown` 발생 시 중단하는 보조 임계값 추가.

### C3. `_fetch_one` — 응답 `drwNo` 불일치 시 서버 값을 그대로 저장 (데이터 정합성, WARN-Med)
`core.py:304-310`
```python
if draw.drw_no != draw_no:
    self._logger.warning(
        "회차 번호 불일치: 요청=%s 응답=%s — 응답 기준으로 저장",
        draw_no, draw.drw_no,
    )
return _FetchOutcome(draw=draw, reason="unknown", detail="")
```
- 요청 `drw_no=5`에 서버가 `drwNo=3`로 응답하면 기존 회차 3 행을 덮어쓰는 upsert가 발생. 저장소 PK 충돌은 없어도 논리적 정합성 훼손.
- `sync_incremental` 루프에서는 `last_success = outcome.draw.drw_no`가 3이 되어 체크포인트가 역행할 수 있다(다행히 `_update_checkpoint`는 `last_success > checkpoint.last_fetched_drw_no` 가드 덕분에 되돌지 않음 — `core.py:263-266`). 하지만 `sync_range` 에서는 가드가 없고 `last_success`가 3으로 남아 반환된다.
- **권고**: 불일치를 `reason="unknown"`(또는 `schema_error`)로 분류하고 저장 생략. 신뢰할 수 없는 응답을 침묵 upsert하지 않는다.

### C4. `sync_incremental` — `start > target` 조건에서 `target_reached`가 아니라 `caught_up` 반환 (시멘틱, WARN-Lo)
`core.py:206-215`
```python
if start > target:
    return SyncResult(..., stopped_reason="caught_up")
```
- `target_draw_no`가 명시된 호출에서도 "이미 최신"이면 `caught_up`을 반환한다. 호출자는 타겟 지정 시 모든 종료 사유가 `target_reached` 계열이길 기대할 수 있다.
- 영향 낮음이지만 문서와 런타임이 어긋남. docstring의 `stopped_reason="target_reached"` 정의와 일관되게 조정 권고.

### C5. `sync_incremental` — 중복 분기(`probe_start` 계산)가 동일 결과 생성 (가독성, WARN-Lo)
`core.py:181-185`
```python
start = (checkpoint.last_fetched_drw_no + 1) if checkpoint is not None else 1
...
probe_start = start if checkpoint is None else checkpoint.last_fetched_drw_no + 1
```
- 두 분기의 값은 항상 같다(`start` 자체가 이미 `last_fetched_drw_no + 1`). `probe_start = start` 한 줄이면 충분.
- **권고**: 단순화(`probe_start = start`).

### C6. `_FetchOutcome.reason="unknown"`이 성공 경로에서도 설정됨 (가독성, WARN-Lo)
`core.py:310`, `core.py:338-350`
- 성공 시 `reason="unknown"`으로 채워진다. 호출자는 `outcome.draw is not None`만 본다는 계약이지만, 자기 문서(docstring)에 "reason/detail 은 의미 없음"이라고 쓰여 있음에도 디버깅 로그에 찍히면 혼동 가능.
- **권고**: `reason: Optional[str] = None` 디폴트 또는 별도 success 플래그.

### C7. `sync_range`와 `sync_incremental` 간 실패 분류 일관성 (WARN-Lo)
- `sync_range`: `reason == "transient" or reason == "rate_limited"` (`core.py:152`).
- `sync_incremental`: `reason in ("transient", "rate_limited")` (`core.py:248`).
- 동작 동일. 가독성 측면에서 한 가지 패턴으로 통일 권고(후자 권장).

### C8. 타입 안전성 — `stopped_reason` 재할당 (WARN-Lo)
`core.py:134, 223`
```python
stopped_reason = "caught_up"        # 타입: str (Literal 추론 가능성 낮음)
```
- mypy strict 모드에서 `SyncResult`에 넣을 때 경고 가능. `sync_incremental`에는 `# type: ignore[arg-type]`을 달았고(`core.py:272`) `sync_range`에는 없음.
- **권고**: `stopped_reason: StoppedReason = "caught_up"`로 변수 주석 또는 두 함수 모두 동일한 처리.

## 설계 품질
- **단일 책임**: 수집기는 오케스트레이션만, HTTP/SQL/파싱은 Backend Dev 위임. scope 문서와 일치. ✓
- **의존 방향**: `collector → backend` 단방향. 순환 없음. ✓
- **의존성 주입**: `client`, `storage`, `config`, `logger` 모두 생성자 주입. 테스트 fake 대체 용이. ✓
- **Protocol 사용**: `DrawFetcher`가 `runtime_checkable Protocol`. 덕 타이핑 + isinstance 검증 둘 다 가능. ✓
- **불변성**: `CollectorConfig`, `FetchFailure`, `SyncResult` 전부 `frozen=True`. ✓
- **공개 API**: `__init__.py` `__all__`이 scope 계약 7종과 정확히 일치. ✓
- **개선**: `_FetchOutcome`은 dataclass/NamedTuple로 바꾸면 가독성 향상.

## 에러 처리
- 예외 분기가 명확: `DrawNotFoundError`(not_yet_drawn) / `TransientFetchError`(transient) / `Exception`(unknown) / `parse_draw` `ValueError`(unknown, 재검토 대상 — C2).
- `sync_incremental`의 detect 단계 실패는 aborted 기록 후 체크포인트 보전(테스트로 증명).
- `__post_init__` 검증: `CollectorConfig`·`FetchFailure`에서 비정상 입력 즉시 거절. ✓
- 개선점은 C1~C3 참조.

## 성능
- 회차당 1회 HTTP 호출, 기본 간격 0.2s → 500회차 수집 시 ~100초(네트워크 지배). ✓
- `_sleep_between_calls`는 `time.monotonic` 기반으로 월타임 역행에도 안전. ✓
- `upsert_draws([draw])`를 회차당 호출 — Backend Dev의 WAL + `BEGIN IMMEDIATE` 덕분에 500회 호출 오버헤드는 허용 범위. 대량 백필 시 묶음 upsert로 튜닝 여지는 있으나 선택적.
- O(n²) 없음. 반복은 선형. ✓

## scope 계약 준수도
| 계약 항목 | 결과 |
| --- | --- |
| 파일 구조 (`__init__.py`, `models.py`, `core.py`) | ✓ |
| 공개 심볼 (`LottoCollector`, `DrawFetcher`, `CollectorConfig`, `FailureReason`, `FetchFailure`, `StoppedReason`, `SyncResult`) | ✓ |
| 공개 메서드 (`detect_latest_draw_no`, `sync_incremental`, `sync_range`) | ✓ |
| Backend Dev 도메인 타입 재사용(`LottoDraw`, `FetchCheckpoint`, `DrawNotFoundError`, `TransientFetchError`, `parse_draw`) | ✓ |
| 구현 순서 (models → rate-limit 헬퍼 → detect → sync_range → sync_incremental → `__init__`) | ✓ |
| 비소유 범위 침범 없음 (HTTP 세션 직접 구성/SQLite 직접 접근 없음) | ✓ |
| 한국어 주석/로그/오류 메시지 | ✓ |

## 테스트 품질
- 19개 테스트가 핵심 경로를 커버: 체크포인트 유무, target 지정, 미발표 조기 종료, 연속 실패 중단, 최신 회차 탐색, 일시 실패 탐색 중단, 예상치 못한 예외.
- 누락된 커버리지(후속 권장):
  - C3 시나리오: 응답 `drwNo`가 요청값과 다른 경우의 동작.
  - C2 시나리오: `parse_draw`가 `ValueError`를 던지는 케이스(현재 없음).
  - `sync_incremental` 갭 뒤 재실행 누락 확인(C1 고의적 동작 증거).
  - `sync_range` 성공 다수 중 `rate_limited`만 섞인 시나리오(현재 `transient`만 테스트).
- fake 설계 깔끔. `custom` 훅으로 임의 시나리오 주입 가능. ✓

## 권고 우선순위
1. **WARN-Hi (다음 build에서 처리 권장)**: C1(체크포인트 갭 전진), C2(ValueError → unknown 분류), C3(drwNo 불일치 저장).
2. **WARN-Lo (문서/가독성)**: C4, C5, C6, C7, C8.

## 결론
- **PASS 항목**: 보안, scope 준수, 의존 방향, 테스트 신뢰도, 기본 성능.
- **WARN 항목**: 위 C1~C8. 동작에는 영향 없거나 경계 조건에서만 문제. C1은 운영 관점에서 반드시 문서화/가이드 필요.
- **BLOCK 항목**: 없음.
- 다음 단계(`frontend_dev_module_1_verify_*`)로 진행 가능. Backend Dev C-review의 B3(naive datetime) 적용 시 본 모듈 `_update_checkpoint`의 `datetime.now()`(`core.py:320`)도 동일하게 UTC-aware로 통일 권고.

## JSON 결과
```json
{
  "verdict": "WARN",
  "issues": [
    {"id": "C1", "severity": "warn-hi", "file": "src/lotto_predictor/collector/core.py", "line_range": "248-266", "summary": "sync_incremental에서 일시 실패 회차를 건너뛰고 체크포인트가 전진해 영구적 갭이 발생"},
    {"id": "C2", "severity": "warn-med", "file": "src/lotto_predictor/collector/core.py", "line_range": "298-301", "summary": "parse_draw의 ValueError를 unknown으로 분류해 연속 실패 중단 로직을 우회"},
    {"id": "C3", "severity": "warn-med", "file": "src/lotto_predictor/collector/core.py", "line_range": "304-310", "summary": "요청 drw_no와 응답 drwNo 불일치 시 서버 값을 그대로 저장·반환"},
    {"id": "C4", "severity": "warn-lo", "file": "src/lotto_predictor/collector/core.py", "line_range": "206-215", "summary": "target_draw_no 지정 상태에서 이미 최신이면 target_reached가 아닌 caught_up 반환"},
    {"id": "C5", "severity": "warn-lo", "file": "src/lotto_predictor/collector/core.py", "line_range": "181-185", "summary": "probe_start 계산 분기가 중복 — 항상 start와 같으므로 단순화"},
    {"id": "C6", "severity": "warn-lo", "file": "src/lotto_predictor/collector/core.py", "line_range": "310,338-350", "summary": "_FetchOutcome 성공 경로에서도 reason=unknown이 설정되어 의미 모호"},
    {"id": "C7", "severity": "warn-lo", "file": "src/lotto_predictor/collector/core.py", "line_range": "152,248", "summary": "transient/rate_limited 판정 스타일이 두 메서드에서 다름(가독성)"},
    {"id": "C8", "severity": "warn-lo", "file": "src/lotto_predictor/collector/core.py", "line_range": "134,223,272", "summary": "stopped_reason 변수에 Literal 타입 주석 없음 — sync_range에는 type: ignore도 누락"}
  ],
  "summary": "보안·설계·scope 준수·테스트 신뢰도 모두 통과. 다만 sync_incremental이 일시 실패 회차를 건너뛰며 체크포인트를 전진시켜 영구 갭이 생기는 동작(C1)과 파서 오류·응답 회차 불일치가 silent로 저장되는 경로(C2,C3)는 다음 build에서 분류·저장 정책을 보강 권고. BLOCK 없음."
}
```

## Signature
[frontend_dev_code_reviewer] 작업 결과를 파일로 남깁니다.
