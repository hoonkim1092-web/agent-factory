# Code Review: strategy_ledger

> Source: core/memory_system/strategy_ledger.py
> Date: 2026-04-19 08:44
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: **BLOCK**

Critic Review의 High 4건이 미해결 상태이며, Cross Review가 strategy_ledger.py 변경에서 추가 ACCEPT 2건을 발견. 수정 후 머지 필수.

---

### Aggregated Findings (6 total)

#### [ACCEPT] [High] `_LEDGER_CACHE` thread-unsafe
- **Critic**: `lineage_ledger.py:126-134` — check-then-write 패턴에 Lock 없음. 동시 실패 시 인스턴스 덮어씀
- **Cross**: "not flagged"
- **Judgment**: 단일 리뷰어이지만 증거 명확. asyncio.to_thread 병렬 실행 경로에서 실제 경합 발생 가능.
- **Action**: `_CACHE_LOCK = threading.Lock()` 추가, `get_lineage_ledger()` 내부 `with _CACHE_LOCK:` 감싸기

#### [ACCEPT] [High] `LineageEntry.history` 무한 증가
- **Critic**: `lineage_ledger.py:100-107` — append만 있고 크기 제한 없음. strategy_ledger `_MAX_ENTRIES=1000` + evict와 대조적
- **Cross**: "not flagged"
- **Judgment**: 단일 리뷰어이지만 같은 파일의 evict 패턴과 일관성 불일치가 명확한 설계 결함.
- **Action**: `_MAX_HISTORY = 50`, append 후 `entry.history = entry.history[-_MAX_HISTORY:]`

#### [ACCEPT] [High] `_use_initial_failure=True` 경로 rollback이 이전 성공 결과 훼손
- **Critic**: `fsa_loop.py:187-236` — pre-commit 없이 rollback 실행 → dynamic_orchestrator 선행 성공 결과물 손실
- **Cross**: "not flagged"
- **Judgment**: 단일 리뷰어이지만 코드 흐름상 손실 경로가 명백.
- **Action**: `_use_initial_failure=True` 분기에서 rollback 전 `git.commit(f"AEE Pre-FSA: {run_id} snapshot")` 삽입

#### [ACCEPT] [High] `is_maxed` 분기에서 `on_task_failure()` 미호출
- **Critic**: `dynamic_orchestrator.py:761-772` — attempts 카운터 갱신 누락
- **Cross**: "not flagged"
- **Judgment**: lineage 정확성 직접 훼손. 카운터 불일치로 is_maxed 이후 attempts 과소 기록.
- **Action**: `is_maxed` 분기 직후 `_ll.on_task_failure(_lineage_id, new_level=6, reason="lineage_maxed")` 추가

#### [ACCEPT] [Medium] `StrategyLedger` write-side 미연결 (이번 diff 대상)
- **Critic**: "not flagged"
- **Cross**: `strategy_ledger.py:204` — `record_episode_outcome()` 등 mutating API가 production 코드 어디서도 호출 안 됨. read-side(`lookup_best_role`)만 연결.
- **Judgment**: eviction 로직을 추가했으나 write-side 자체가 dead code. Blueprint §283-287 문서와 실제 동작 불일치.
- **Action**: `dynamic_orchestrator` 또는 `project_pipeline` task 완료 경로에 `record_role_success/failure` 연결, 또는 scaffolding임을 명시 주석 추가

#### [ACCEPT] [Medium] eviction 신규 분기 테스트 없음 (이번 diff 대상)
- **Critic**: "not flagged"
- **Cross**: `strategy_ledger.py:204` — `record_failure_pattern()`, `get_warnings_for()` 테스트 전무. eviction 후 persistence 검증 없음.
- **Judgment**: 이번 diff의 핵심 변경(evict 호출 추가)이 직접 검증 안 됨.
- **Action**: `_MAX_ENTRIES+1` 패턴 삽입 → 1000건 cap 확인 → occurrence_count 기준 생존 검증 → reload 후 `get_warnings_for()` 반환값 확인하는 테스트 추가

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_LEDGER_CACHE` thread-unsafe | High | ACCEPT | Critic |
| 2 | `LineageEntry.history` 무한 증가 | High | ACCEPT | Critic |
| 3 | rollback이 이전 성공 결과 훼손 | High | ACCEPT | Critic |
| 4 | `is_maxed` 분기 `on_task_failure()` 누락 | High | ACCEPT | Critic |
| 5 | StrategyLedger write-side 미연결 | Medium | ACCEPT | Cross |
| 6 | eviction 분기 테스트 없음 | Medium | ACCEPT | Cross |

---

### Recommendations

1. **즉시 수정** (BLOCK 해소): `lineage_ledger.py` Lock + history cap → `fsa_loop.py` pre-commit → `dynamic_orchestrator.py` on_task_failure 호출
2. **이번 diff 보완**: `StrategyLedger` write-side를 실제 task 완료 경로에 연결하거나 scaffolding 주석 명시
3. **테스트 추가**: `strategy_ledger.py` eviction 경로 unit test 4케이스
4. **REJECT 확정**: `_save()` atomic write 패턴 유지 (Cross Review REJECT 타당 — file_io.py helpers보다 안전)