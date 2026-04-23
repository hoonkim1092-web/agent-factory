# Code Review: lineage_ledger

> Source: core/lineage_ledger.py
> Date: 2026-04-20 00:11
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

Finding #1 is a Critical-class safety regression: quietly resetting the `attempts` counter reopens the runaway-retry path that `_MAX_ATTEMPTS=20` was designed to close. Both reviewers flagged it independently with reproducing evidence, so it must be fixed before merge.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Critical] Legacy map-shape 백업이 attempts 카운터를 유실 → FSA 재시도 게이트 우회
- **Critic**: legacy `{lineage_id: {level, attempts}}` 데이터에 실제 attempts 카운터가 있는데 통째 백업 후 빈 원장으로 재시작 → 18/20 lineage가 0/20으로 리셋 → 추가 20회 재시도 허용. "is_maxed 오판정 방지" 주석이 사실상 false negative를 만듦.
- **Cross**: `{"Lmax":{"level":6,"attempts":20}}`를 로드했을 때 `is_maxed()`가 False를 반환함을 로컬 재현. `dynamic_orchestrator.py:759`와 `fsa_loop.py:132`가 유일한 게이팅 지점이고 watchdog 측 대체 소스는 grep 결과 없음.
- **Judgment**: 두 리뷰어가 독립적으로 동일 결론 + Cross가 로컬 재현까지 완료. 코드 증거(`core/lineage_ledger.py:70-84`에서 `os.replace` 후 `return`, `_entries` 비어있음)가 명확. 심각도는 두 리뷰 모두 High였으나, 런어웨이 루프 방지라는 안전장치 무력화이므로 **Critical로 상향**.
- **Action Required**: `os.replace` 전에 map-shape을 순회하여 `LineageEntry(lineage_id=k, level=v.get("level",0), attempts=v.get("attempts",0), history=[])`로 마이그레이트 → `self._entries`에 적재 → `_save()`로 canonical 포맷 재작성. 백업은 그대로 남기되 원장 상태는 보존.

#### 2. [ACCEPT] [High] 재귀 복구 경로에 회귀 테스트 없음
- **Critic**: 언급 없음
- **Cross**: `LineageLedger`/`get_lineage_ledger()` 참조 테스트 repo 전체에 없음. `tests/e2e/conftest.py:18`는 `save_state()`만 seed하고 `tick_simulator.py:18`는 lineage 복구 미검증. `code-review.md`가 이미 `core/lineage_ledger.py` 미커버리지로 플래그함.
- **Judgment**: Cross만 플래그했지만 grep 증거가 구체적이고 diff가 load-time에 destructive FS mutation(파일 rename)을 추가한다는 점에서 근거 강함. Finding #1 수정 시 함께 테스트 확장 필수.
- **Action Required**: tmp-path 기반 3-케이스 회귀 테스트 추가 — (a) canonical entries 정상 로드, (b) legacy map-shape 마이그레이션 후 `is_maxed(maxed_lineage) == True` 유지, (c) `entries` 내부 불량 레코드는 skip되고 정상 레코드는 로드.

#### 3. [ACCEPT] [Medium] Backup 파일명 초 단위 타임스탬프 충돌
- **Critic**: `backup = f"{self._path}.corrupt.{int(time.time())}.json"` — 같은 초에 두 번 호출되면 `os.replace`가 이전 백업을 silently overwrite. 포렌식 유실.
- **Cross**: 언급 없음
- **Judgment**: Critic만 플래그했으나 코드 증거가 명확(`core/lineage_ledger.py:74-75`). 단일 프로세스 단일 호출 시나리오에서는 덜 긴박하나 `reset_lineage_ledger()` 후 재생성 조합에서 재현 가능.
- **Action Required**: `time.time_ns()` 또는 `f".corrupt.{int(time.time())}.{os.getpid()}.json"`로 unique화.

#### 4. [ACCEPT] [Medium] `print`로 데이터 손실 이벤트 로깅 — frozen/daemon 환경에서 관찰성 저하
- **Critic**: `af.exe` frozen 빌드/daemon에서 stdout 소실 가능. legacy 파일 백업은 감사 가치 높음.
- **Cross**: 언급 없음
- **Judgment**: Critic만 플래그. AF가 `print(flush=True)` 패턴을 쓰지만 이 이벤트는 백업 경로까지 포함한 데이터 손실 감사 로그이므로 `logging`이 적절.
- **Action Required**: `logging.getLogger(__name__).warning("legacy map-shape detected, backed up to %s", backup)`.

#### 5. [ACCEPT] [Low] `OSError` silent pass — 백업 실패 시 다음 save가 원본 덮어쓰기
- **Critic**: `except OSError: pass` 후 `return`. 다음 `_save()`가 `{"entries":[]}`로 덮어쓰면 백업 없이 원본 손실.
- **Cross**: 언급 없음
- **Judgment**: Critic만 플래그. Finding #1 수정으로 마이그레이션이 성공하면 빈 원장 저장 경로는 사라지지만, 복구 실패 경로 자체는 여전히 존재. 로깅 + 읽기 전용 플래그로 방어 필요.
- **Action Required**: `except OSError as e: logging.error("legacy backup failed: %s", e)` + 마이그레이션/save 중단 플래그 고려.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Legacy attempts 카운터 유실 → FSA 게이트 우회 | Critical | ACCEPT | Both |
| 2 | 복구 경로 회귀 테스트 없음 | High | ACCEPT | Cross |
| 3 | Backup 파일명 초 단위 충돌 | Medium | ACCEPT | Critic |
| 4 | `print` 사용 — 관찰성 저하 | Medium | ACCEPT | Critic |
| 5 | `OSError` silent pass → 원본 손실 위험 | Low | ACCEPT | Critic |

### Recommendations
- **BLOCK 해소 조건**: Finding #1 (데이터 마이그레이션) + Finding #2 (회귀 테스트) 동시 수정.
- Finding #1 구현 스켈레톤: legacy 감지 블록 내부에서 `migrated = [LineageEntry(lineage_id=k, level=int(v.get("level",0)), attempts=int(v.get("attempts",0)), history=[]) for k,v in data.items() if isinstance(v, dict)]` → `self._entries = {e.lineage_id: e for e in migrated if e.lineage_id}` → backup rename → `self._save()` 호출로 canonical 재작성.
- Finding #2 테스트 위치: `tests/unit/test_lineage_ledger.py` 신설 (현재 부재). 최소 3 케이스 (canonical/legacy migration/malformed tolerance).
- Finding #3+#4+#5는 동일 함수 내 일괄 수정 가능 — `import time`을 top-level로 올리고(Critic #5) `logging` import 추가 + `time.time_ns()` + `except OSError as e: logging.error(...)` 한 패치로 묶어 처리.
- 머지 후 `Master_Blueprint.md` §3 lineage_ledger 섹션 + §11 에러 코드(legacy map-shape 복구) + §12 변경 이력 동시 업데이트 필수 (CLAUDE.md 규약).