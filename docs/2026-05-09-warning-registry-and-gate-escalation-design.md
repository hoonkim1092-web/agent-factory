# Warning Registry & Gate Escalation 설계 (P1 패키지)

- 작성일: 2026-05-09 KST
- 작성 모델: Claude Opus 4.7 (1M context)
- 브랜치: `2026-05-07-memory-gitignore-cleanup`
- 분류: 단일 설계문서 (CLAUDE.md 규칙 → af-cross-review 1라운드 자동 발화)
- 상태: **Draft v5 — v4 통합 cross-review (102321, claude+codex+judge) 11 finding 중 ACCEPT 9 / HOLD 1 / 반박 2 모두 처리 완료**
- 선행 분석: `docs/codex/2026-05-08-af-productization-application-guide.md`
- v1 리뷰 리포트: `docs/reviews/2026-05-09-094340-2026-05-09-warning-registry-and-gate-escalation-design-review.md`
- v2 리뷰 리포트: `docs/reviews/2026-05-09-095135-2026-05-09-warning-registry-and-gate-escalation-design-design-review.md`
- v3 리뷰 리포트 (2건): `docs/reviews/2026-05-09-100406-...-design-review.md`, `docs/reviews/2026-05-09-100614-...-design-review.md`
- v4 리뷰 리포트 (최신 통합): `docs/reviews/2026-05-09-102321-2026-05-09-warning-registry-and-gate-escalation-design-design-review.md` — claude critic + codex cross + judge=claude, BLOCK, 11 finding

---

## §0 한 줄 요약

AF의 메타 결함은 "WARN을 못 찾는다"가 아니라 **"WARN이 BLOCK으로 승격되지 않는다"**. 본 P1 패키지는 (a) WarningRecord schema, (b) 기존 산발 WARN 4종 마이그레이션, (c) 표준 저장 위치, (d) escalation policy v0, (e) decision report 포맷, (f) P2~P6 의존성 다이어그램을 한 PR에 묶어 출시한다. **BLOCK 활성화 rollout 정책 (확정)**: P1은 schema/저장/policy 데이터만 수립하고 실제 차단은 일으키지 않는다(severity는 `warn`만). **P2에서 e2e_command_missing 한 rule만 phase-aware BLOCK으로 활성**한다(build/integrate/code_review/cross_validate/verify phase에서 발생 시 — §5.1 정책과 정합, baseline `_PHASE_ORDER` 6개 중 scope만 exempt). **P4에서 P2/P3 측정 데이터를 근거로 owner_role_mismatch / evidence_quality_warn 등 다른 rule을 BLOCK으로 점진 확장**한다. P3/P5는 record만 누적, BLOCK 활성화 없음.

---

## §1 배경 및 문제 정의

### 1.1 메타 결함의 실증 (minesweeper-baseline 1회 실측)

| 측정 항목 | 결과 | 출처 |
|----------|------|------|
| `e2e_command` 결측 task | **21/21** 전수 결측 | `core/work_item_generator.py:1056` |
| owner_role 미스배정 module | **3/7** | `core/project_task_board.py:227` `detect_owner_drift` |
| 파이프라인 verdict | PASS | approval-gate.md status: approved |
| 사용자 노출된 차단 신호 | **없음** | hook log, gate 모두 BLOCK 미발화 |

**해석**: WARN은 정상적으로 발화되었으나, 누구도 (1) 누적 횟수를 추적하지 않고 (2) 임계 초과 시 BLOCK으로 승격하지 않는다. 결과적으로 "WARN 21건 = WARN 0건"과 동일한 통과 신호가 생성된다.

### 1.2 P1이 P2~P6보다 먼저 와야 하는 이유

- P2(phase-aware BLOCK)는 "어떤 WARN을 BLOCK으로 강제할지" 판단을 위해 P1의 record schema가 선행되어야 함.
- P3(Owner Lint measurement) / P5(contract drift 측정기)는 record 형식이 통일되어야 누적 비교 가능.
- P4(escalation v1) / P6(domain-specific)는 P1의 schema를 기준으로 분기.
- 따라서 P1은 **시멘틱 라이브러리 + 저장소** 역할이고, 실제 BLOCK 동작은 P2에서 e2e_command_missing 한 rule만 활성, P4에서 다른 rule로 점진 확장한다 (§0과 §7.2 일관).

### 1.3 거부된 대안 (재논의 시에만 검토)

- 포커 도메인 키 하드코딩(`starting_stack`, `SB/BB`)을 코어 config에 박는 안 — domain-specific gate는 P6 활성화 조건으로만 허용.
- Event Protocol 필수 이벤트(`join_room` 등)를 코어 게이트로 강제 — 도메인 결합 과잉.
- simulation.md 자동 생성 강제 — 모든 프로젝트에 부적합.
- 한 단계에서 SSOT+protocol+owner+AC+simulation 일괄 처리 — 측정 데이터 없이 추진 시 P3 false-positive 분포를 모르고 BLOCK 승격하는 위험.

---

## §2 WarningRecord schema (Acceptance #1)

### 2.1 필드 정의

```python
# core/warning_registry.py (P1에서 신설)
@dataclass
class WarningRecord:
    # ─── Identity (필수) ───
    rule_id: str            # 예: "e2e_command_missing"
    severity: str           # "warn" | "block_candidate" | "block"
    project_slug: str       # 예: "minesweeper-smoke-v2-01"
    ts: str                 # ISO 8601, now_iso() 사용
    record_id: str          # v4 — idempotency key. f"{slug}:{rule_id}:{ts}:{hash6(payload)}" (Finding 100614 #3)
    schema_version: int = 1 # v5 — open schema (Finding 102321 #10). P4 schema 변경 시 bump.

    # ─── Localization (필수) ───
    # baseline taxonomy: core/project_task_board.py:17 _PHASE_ORDER
    # 다른 phase 값(설계 단계의 "design" 등)은 P1 단계에서 인정하지 않음 — 새 phase 도입은 baseline 확장 PR 선행.
    affected_phase: str     # "scope" | "build" | "integrate" | "code_review" | "cross_validate" | "verify"
    count: int = 1          # 이 record에서 측정한 위반 건수 (예: e2e_command 누락 21건 중 build phase 16건)

    # ─── Escalation 입력 (선택) ───
    repeat_count: int = 1            # 동일 rule_id가 동일 slug에서 발화된 누적 횟수
    baseline_delta: float = 0.0      # 직전 baseline 대비 증가율 (없으면 0.0)
    false_positive_override: bool = False  # 사용자가 명시 OK한 경우 True
    rationale: str = ""              # "왜 이게 WARN인지" 한 줄 설명

    # ─── Diagnostic payload (선택) ───
    affected_ids: list[str] = field(default_factory=list)  # task_id, module_id 등
    source_path: str = ""            # 발화 위치 (file:line)
    extra: dict = field(default_factory=dict)
```

### 2.2 필수 vs 선택 정당화

| 필드 | 필수 여부 | 이유 |
|------|---------|------|
| `rule_id`, `severity`, `project_slug`, `ts` | 필수 | jsonl append 시 식별·정렬 키 |
| `affected_phase`, `count` | 필수 | P2 phase-aware BLOCK과 P4 escalation 임계 판정 입력 |
| `repeat_count` | 필수 (v5) | **`record()` 내부에서 계산 후 persist** (v5 — Finding 102321 #6 ACCEPT). 새 record append 직전 SoT(`<slug>/<rule>.jsonl`)를 풀스캔해 `count(rule_id == 자기) + 1`로 채움. P4 `evaluate(record)`는 `record.repeat_count`만 보면 됨 (history 인자 불필요). 첫 record는 1. |
| `baseline_delta` | 선택 | P5 contract drift 측정기에서만 채움 |
| `false_positive_override` | 선택 | 사용자 승인 후 BLOCK escalation 차단용 |
| `rationale` | 선택 권장 | decision report 자동 생성 시 사용 |
| `affected_ids`, `source_path`, `extra` | 선택 | 디버깅/리포트 가독성 |

### 2.2a phase 정규화 정책 (v5 — Finding 102321 #4 ACCEPT, High)

`affected_phase`는 baseline `_PHASE_ORDER` (`core/project_task_board.py:17`) 6개 (`scope`, `build`, `integrate`, `code_review`, `cross_validate`, `verify`) 중 하나여야 한다. LLM 출력이 비표준 값(`"design"`, `"test"`, `"integration"` 등)을 반환할 수 있으므로 `record()`는 다음 정규화 정책을 적용한다:

```python
_PHASE_ALIAS = {
    "design": "scope",        # 설계는 scope phase에 흡수
    "test": "verify",         # test는 verify phase에 흡수
    "integration": "integrate",
}

def _normalize_phase(raw: str) -> tuple[str, str | None]:
    """returns (canonical_phase, original_if_aliased)"""
    if raw in _PHASE_ORDER:
        return raw, None
    if raw in _PHASE_ALIAS:
        return _PHASE_ALIAS[raw], raw
    return "build", raw  # unknown은 build로 fallback + extra.original_phase 보존
```

`record()` 내부에서 `affected_phase`를 정규화하고, alias/unknown 변환이 발생하면 `extra["original_phase"]`에 원본 보존. 이 정책이 §5.1 `affected_phase_in: [...]` 매칭에서 silent skip을 방지한다 (baseline 외 phase가 record에 들어가도 정책이 인식 가능한 6개 중 하나로 매핑됨).

### 2.4 open schema 정책 (v5 — Finding 102321 #10 ACCEPT, Medium)

P4에서 신규 severity / 필드가 추가되어도 P1 jsonl이 깨지지 않도록 다음 정책을 명시:

1. **append-only**: 기존 record는 절대 mutate하지 않음. 새 정보는 새 record로 append.
2. **unknown field tolerance**: deserialize 시 dataclass에 없는 키는 `extra` 딕셔너리로 흡수 (silent ignore 금지 — 보존).
3. **missing field default**: 신버전이 추가한 필드가 구버전 record에 없으면 `dataclass.field(default_factory=...)` 또는 `Optional` default로 채움.
4. **schema_version**: `WarningRecord`에 `schema_version: int = 1` 추가 (v5 신규). P4가 schema 변경 시 bump하고 deserializer가 분기.

테스트: `tests/test_warning_registry_schema_evolution.py` (1 케이스): v0.1 record에 v0.2 신규 필드를 추가한 후 round-trip 성공.

### 2.3 severity 값의 의미

| severity | 의미 | 진입 조건 |
|----------|------|---------|
| `warn` | 단순 경고, 차단 없음 | 기본값 (모든 신규 record) |
| `block_candidate` | escalation policy v0를 통과해 BLOCK 후보로 마킹됨 | P4가 자동 부여 |
| `block` | gate가 실제 차단 (approval-gate에 반영) | P4가 부여하고 approval_gate.apply_verification_verdict 호출 |

P1 단계에서는 `warn`만 발화하고, `block_candidate`/`block` 분기는 P4가 추가한다 (코드 구조는 P1에서 미리 마련).

---

## §3 기존 WARN → registry 매핑 표 (Acceptance #2)

### 3.1 1차 마이그레이션 대상 4건

| # | rule_id | 현재 발화 위치 (파일:줄) | 현재 동작 | P1 동작 (마이그레이션 후) |
|---|---------|------------------------|---------|------------------------|
| 1 | `e2e_command_missing` | `core/work_item_generator.py:1048-1056` | `_LOGGER.warning(...)` 단발 로그 (task list 전체 집계) | task별 `phase` 필드(`core/work_item_generator.py:166` `_clean(item.get("phase") or "build")` 참조)로 그룹화한 뒤, **phase 그룹별 record 분할 발화**: 예) build phase 결측 16건 → 1 record (`affected_phase="build"`, `count=16`), scope phase 결측 5건 → 1 record (`affected_phase="scope"`, `count=5`). 기존 `_LOGGER.warning` 단일 로그는 유지. 정책의 phase-exempt가 정상 분기되도록 record 단위가 phase별로 분리되어야 한다. |
| 2 | `owner_role_mismatch` | `core/project_task_board.py:227-249` `detect_owner_drift` | `bool` 반환만 (호출처 `core/project_pipeline.py:1402` `logger.warning("strategy ledger skip — owner drift 감지 ...")`) | **v4 시그니처 (Finding 100614 #5 ACCEPT — expected_owner 보존)**: `detect_owner_drift(...) -> list[tuple[str, str, str]]`로 변경. 각 tuple은 `(task_id, expected_owner, actual_owner)` (baseline에서 이미 `mod_owner` / `task_owner` 분리 — `core/project_task_board.py:230,244` 참조 → 둘 다 그대로 노출). 빈 리스트는 falsy → 기존 `if detect_owner_drift(...):` 호출처 회귀 없음. 호출처(`core/project_pipeline.py:1401-1406`)에서 `mismatches = detect_owner_drift(...); if mismatches: WarningRegistry(workspace=target_workspace).record(project_slug=slug, rule_id="owner_role_mismatch", count=len(mismatches), affected_phase="build", affected_ids=[mid] + [tid for tid, _, _ in mismatches], extra={"mismatches": [{"task_id": tid, "expected": exp, "actual": act} for tid, exp, act in mismatches]})`. phase 값은 baseline taxonomy 중 `build`(module 실행 phase). |
| 3 | `evidence_quality_warn` | **호출처: `core/project_pipeline.py:756-774`** (verifier 자체는 `core/research_verifier.py:362-366`에서 `_warnings` append만 유지) | `evidence._warnings.append("evidence_quality_warn: score=%s, gaps=%s")` (현재 동작 유지) | **v3 변경 (Finding #5 ACCEPT)**: `core/research_verifier.py`에는 record 호출을 넣지 **않는다** (`ResearchVerifier()`는 slug/workspace를 모름 — `core/project_pipeline.py:725` 인스턴스화 시 인자 없음, `core/project_pipeline.py:756`의 `verify_with_retry(evidence_fn, task_input)`도 workspace 미수신). 대신 호출처(`core/project_pipeline.py`)에서 `_vr` 반환 직후 `if _vr.status != "pass": WarningRegistry(workspace=target_workspace).record(project_slug=slug, rule_id="evidence_quality_warn", affected_phase="scope", count=len(_vr.gaps), severity="warn", extra={"score": _vr.score, "gaps": _vr.gaps})`. 이 위치는 `slug` (메서드 인자), `target_workspace` (이미 지역변수, `core/project_pipeline.py:725` 위 `_collect_kwargs`)이 모두 가용. 기존 `_warnings` append와 병행 (이중 기록). |
| 4 | `plan_verifier_warn` | `core/plan_verifier.py:42-80` `PlanVerifyResult.passed=False` 흐름 | gate에서 `passed=False` 시 advisory만 (파이프라인 통과) | 호출처(`core/project_pipeline.py:959-` `from core.plan_verifier import PlanVerifier`)에서 `passed=False`면 `WarningRegistry.record(rule_id="plan_verifier_warn", affected_phase="scope", count=len(result.issues), extra={"score": result.score})` (plan 검증은 scope phase). |

### 3.2 P5 자리 (현재 측정기 없음 — 신설)

| # | rule_id | 발화 위치 (P5에서 신설) | 동작 |
|---|---------|---------------------|------|
| 5 | `doc_consistency_drift` | `core/doc_consistency_meter.py` (신설, P5) | brief의 기존 필드(data_model/tech_stack/non_goals)를 후속 문서에서 grep해 보존율 측정. 임계 미달 시 record |

P1에서는 **rule_id 예약**만 하고, 실제 발화 코드는 P5에서 추가한다 (registry는 모르는 rule_id도 기록 가능 — open schema).

### 3.3 마이그레이션 원칙

1. **기존 WARN 코드는 삭제하지 않는다** — 이중 기록 (logger + registry) 방식. 사용자 가시 로그는 그대로 유지.
2. **rule_id는 snake_case 명사** — `<noun>_<state>` 패턴 (e.g., `e2e_command_missing`, `owner_role_mismatch`).
3. **affected_phase는 baseline `_PHASE_ORDER` 6개로 고정** (§2.1). 이는 P2 phase-aware BLOCK이 분기할 키. 새 phase 도입은 baseline 확장 PR 선행 필수.
4. **registry record 호출은 try/except로 감싸 fire-and-forget** — registry 실패가 본 흐름을 깨면 안 됨.
5. **phase 그룹별 분할 record 원칙**: 한 발화 지점에서 여러 phase의 위반이 섞여 있으면 phase별로 record를 나눠 기록 (§3.1 row 1 참조). 이 원칙이 §5.1 `exempt_when affected_phase_in: [scope]` 등 정책 분기를 작동 가능하게 만든다.

---

## §4 표준 저장 위치 명세 (Acceptance #3)

### 4.0 path ownership 계약 (v4 — workspace/doc_root 분리 정직 모델링, v3 100614 #1 + 100406 #3 ACCEPT)

**근본 원칙**: baseline은 이미 `workspace` (AF 운영 데이터 루트)와 `doc_root` (사용자 산출물 루트)를 분리한다. v4는 이걸 **무시하지 않고 정직하게 모델링**한다.

baseline 분리 사실 (코드 인용 — 검증됨):
- `core/work_item_generator.py:948` — `doc_root = abspath(target_path) if (target_path and abs) else workspace` — 사용자 산출물 (implementation-tasks.md, approval-gate.md 등)은 target_path가 있으면 doc_root에 쓴다.
- `core/work_item_generator.py:1042` — `write_initial_record(workspace, slug, ...)` — telemetry는 항상 workspace에 쓴다.
- `core/work_item_generator.py:1061` — `gate = ApprovalGate(doc_root, slug)` — **gate는 doc_root에 위치** (사용자 산출물).
- `core/project_pipeline.py:87-95` — `gate() -> ApprovalGate(self._effective_doc_root(), ...)` — pipeline도 동일.
- `core/approval_gate.py:78` — `def __init__(self, workspace: str, slug: str)` — **인자명이 `workspace`이지만 실제 전달값은 `doc_root`** (네이밍 혼란 — v4에서 별도 명시).

**결정 (4가지 path 정책)**:

| 데이터 | 위치 | 이유 |
|--------|------|------|
| `runtime/warnings/<slug>/<rule>.jsonl` (record SoT) | **workspace** 하위 | 운영 메타데이터, telemetry와 동급, multi-PC sync 대상 통일 |
| `runtime/warnings/_summary.json`, `_global/` (cache) | **workspace** 하위 | record로부터 재생성 가능, 동일 storage root |
| `runtime/warnings/<slug>/_decision.md` (사용자 노출) | **workspace** 하위 | _summary와 같은 위치 (재생성 가능) |
| `approval-gate.md` (사용자 산출물) | **doc_root** 하위 (baseline 그대로) | 사용자 PR review 영역, 변경 없음 |

**핵심 wiring**: gate(doc_root)에서 _decision.md(workspace)로 가는 링크는 **두 path가 다를 수 있으므로** ApprovalGate가 양쪽 path를 모두 알아야 한다 → §6.3 `ApprovalGate(doc_root, slug, runtime_workspace=...)` 시그니처 확장 (Finding 100614 #1 옵션 A 채택).

API 시그니처:

```python
class WarningRegistry:
    def __init__(self, workspace: str) -> None:
        """workspace는 AF 운영 데이터 루트 (doc_root 아님). 절대경로로 정규화."""
        if not workspace:
            raise ValueError("WarningRegistry requires explicit workspace; cwd/doc_root fallback forbidden")
        self.workspace = os.path.abspath(workspace)
        self.warnings_root = os.path.join(self.workspace, "runtime", "warnings")

    def record(self, *, project_slug: str, rule_id: str, **fields) -> None:
        """jsonl append. workspace는 생성자 인자, project_slug+rule_id만 record-level."""

    def summarize(self, *, project_slug: str) -> dict:
        """<workspace>/runtime/warnings/<slug>/_summary.json 갱신·반환 (rebuild 가능 cache)."""

    def load_global(self, *, rule_id: str) -> list[dict]:
        """v5 — P1에서는 stub. P4 활성 시 _global/<rule>.jsonl 로드 (Finding 102321 #7)."""
        raise NotImplementedError("global aggregation activates at P4")

    def rebuild_caches(self, *, project_slug: str) -> None:
        """SoT(<slug>/<rule>.jsonl)로부터 _summary.json 재생성 (v5 — _global P4 이연, Finding 102321 #7).
           실질적으로 summarize(project_slug=...)와 동일 (read-on-demand 단일화, §4.4 Finding 102321 #5)."""
```

**호출처는 항상 `WarningRegistry(workspace=target_workspace)` 패턴**. cwd / doc_root / env fallback 모두 금지 (`ValueError` 즉시 발생).

### 4.0a SoT vs cache 분리 (Finding 100614 #3 ACCEPT — partial-write recovery)

| 파일 | 역할 | rebuild 가능 | record_id 필요 |
|------|------|------------|-------------|
| `<slug>/<rule_id>.jsonl` | **SoT (source of truth)** — append-only | ❌ (원본) | ✅ idempotency key |
| `_summary.json` | cache (by_rule + by_phase 집계) | ✅ SoT 재스캔으로 재생성 | — |
| `_global/<rule_id>.jsonl` | cache (프로젝트 간 누적) | ✅ 모든 SoT를 union해 재생성 | — |
| `_index.json` | 등록된 rule_id 목록 (commit) | 수동 갱신 (코드 변경과 동기) | — |

**partial-write 복구 절차**:
- record() 호출은 `<slug>/<rule>.jsonl` append → `_summary` 갱신 → `_global/<rule>` append 순. 중간 단계 실패 시 SoT만 일관 보장.
- 사용자가 `python -m core.warning_registry repair --workspace=<path> --slug=<slug>` 실행하면 SoT로부터 `_summary` + `_global` 전부 재생성.
- 신규 record는 `record_id = f"{slug}:{rule_id}:{ts}:{hash6}"` (idempotency key) — repair 또는 retry 시 중복 append 검출.

### 4.1 디렉토리 구조 (v5 — Finding 102321 #7 ACCEPT, _global P4 이연)

```
<workspace>/runtime/                 # ← workspace 하위로 고정 (§4.0)
├── timing/                          # 기존 (Phase F)
└── warnings/                        # 신설 (P1)
    ├── _index.json                  # 등록된 rule_id 목록 + 메타 (commit 대상)
    └── <project_slug>/
        ├── <rule_id>.jsonl          # SoT — append-only (lock + tempfile 의무, §4.4)
        ├── _summary.json            # cache — read-on-demand 재생성 (§4.4)
        └── _decision.md             # WARN→BLOCK 승격 시 markdown 보고서 (P4부터 채움)
```

**v5 변경 (Finding 102321 #7 ACCEPT — P1 scope 단순화)**: `_global/<rule_id>.jsonl` 디렉토리는 **P4로 이연**. 이유: (1) P1 acceptance 검증에 _global이 필요 없음 (모든 phase-aware BLOCK은 단일 slug 내 record로 결정), (2) producer API가 §4.0 `record(slug별)` 외에 별도 wiring이 필요해 scope 비대화. P4가 활성될 때 `WarningRegistry.rebuild_global(*, rule_id)` 추가 + 모든 SoT를 union 해 재생성. P1에서는 `_global/` 디렉토리 자체를 만들지 않음.

`load_global(rule_id)` API도 P4로 이연 (P1 stub은 `NotImplementedError("global 누적은 P4에서 활성")`)— §4.0 코드 블록 갱신.

### 4.2 jsonl 레코드 1줄 예시

```json
{"rule_id":"e2e_command_missing","severity":"warn","project_slug":"minesweeper-smoke-v2-01","ts":"2026-05-09T01:23:45+09:00","affected_phase":"build","count":21,"repeat_count":1,"baseline_delta":0.0,"false_positive_override":false,"rationale":"work_item_generator: tasks without e2e_command","affected_ids":["T-001","T-002","..."],"source_path":"core/work_item_generator.py:1056","extra":{}}
```

### 4.3 _summary.json 포맷 (v3 — by_phase 추가, Finding #3 ACCEPT)

```json
{
  "project_slug": "minesweeper-smoke-v2-01",
  "last_updated": "2026-05-09T01:23:45+09:00",
  "by_rule": {
    "e2e_command_missing": {
      "count": 21,
      "first_ts": "2026-05-09T01:23:45+09:00",
      "last_ts":  "2026-05-09T01:23:45+09:00",
      "severity": "warn",
      "by_phase": {"scope": 5, "build": 16}
    },
    "owner_role_mismatch": {
      "count": 3,
      "first_ts": "2026-05-09T01:23:45+09:00",
      "last_ts":  "2026-05-09T01:23:45+09:00",
      "severity": "warn",
      "by_phase": {"build": 3}
    }
  },
  "by_severity": {"warn": 24, "block_candidate": 0, "block": 0}
}
```

**`by_phase` 필드**: 해당 rule의 record들을 `affected_phase`별로 합산한 `{phase: count}` 딕셔너리. acceptance #2 (`python -m core.warning_registry summary --slug=<slug>`이 `by_rule.<rule>.by_phase` 분포 출력)와 정합. CLI 출력은 이 필드를 그대로 dump하면 된다. P2의 phase-aware BLOCK 평가도 이 분포로 빠르게 의사결정 가능.

### 4.4 동시성 / 원자성 / lazy 트리거 단일화 (v5 — Finding 102321 #3 + #5 ACCEPT, High)

**jsonl append (SoT)**:
- `core/file_lock.locked_file` 사용 (실제 위치: `core/file_lock.py:38`. 이미 `core/project_task_board.py:12`, `core/project_mailbox.py:9`, `core/work_item_telemetry.py:9`, `core/providers/session_adapter.py:21`에서 동일 import). multi-thread 안전.
- lock 키는 **rule_id 단위가 아닌 slug 단위 통일**: `<workspace>/runtime/warnings/<slug>/.lock` 단일 파일. 이유: 같은 slug 내 다른 rule도 _summary.json을 공유하므로 rule별 lock은 비대칭 → race 위험 (#3).

**`_summary.json` 갱신 — atomic write 의무화 (Finding #3)**:
`core/work_item_telemetry.py:55-65` 패턴을 그대로 차용:

```python
# WarningRegistry._write_summary 내부
payload = json.dumps(summary, ensure_ascii=False, indent=2)
with locked_file(str(slug_lock_path), timeout=5):
    fd, tmp = tempfile.mkstemp(dir=str(slug_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, str(summary_path))   # atomic
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
```

이 패턴은 mid-write crash 시 `_summary.json`이 이전 정상본을 보존 (M10 회귀 방지).

**lazy 트리거 단일화 (Finding #5)**:

v3/v4의 "10건마다 또는 run 종료 시 갱신" 명세는 **폐기**. v5는 **`summarize()`를 read-on-demand로 단일화**:

- `record()`는 jsonl append만 수행 (SoT 갱신). `_summary.json`은 건드리지 않음.
- `summarize(*, project_slug)` 호출 시점에 jsonl 풀스캔으로 by_rule + by_phase 재계산 → atomic write.
- CLI `summary` / acceptance 검증 / approval-gate _decision.md 생성 모두 `summarize()` 호출 → SoT와 항상 정합.

이 단일화로 (a) "10건마다" 트리거 호출처를 wiring할 필요 없음, (b) 1건 record 케이스에서도 stale 없음 (acceptance #2/#11 정합), (c) `repair`는 사실상 `summarize()` 호출과 동일.

**동시 다른 프로젝트 record는 다른 디렉토리 → lock 충돌 없음.**

### 4.5 .gitignore 정책 (v4 — Finding 100614 #4 ACCEPT, 정확한 글로브 패턴)

기존 `.gitignore`에는 `**/.af_runtime/`만 있고 `runtime/` 룰 없음 (v3에서 누락 — 동적 slug는 nested glob으로 작성 불가). v4 P1 PR에서 다음 5줄 추가:

```gitignore
# Warning registry — workspace 운영 데이터 (record SoT + cache)
/runtime/warnings/*
!/runtime/warnings/
!/runtime/warnings/.gitkeep
!/runtime/warnings/_index.json
/runtime/warnings/_global/
```

**해석**:
- 1행 `*`: 기본은 `runtime/warnings/` 직속 모든 것 ignore (모든 `<slug>/` 디렉토리 포함).
- 2-4행 `!`: 디렉토리 자체 / `.gitkeep` / `_index.json`은 trackable로 unignore.
- 5행 `_global/`: `_global/` 하위 (cache) 별도 ignore (1행만으로는 unignore된 디렉토리 안의 cache 파일이 다시 잡힐 수 있어 명시).

P1 PR 머지 후 검증: `git check-ignore -v runtime/warnings/<slug>/<rule>.jsonl` → 1행 매치, `git check-ignore -v runtime/warnings/_index.json` → 매치 없음 (trackable).

**v5 (Finding 102321 #8 — Medium, REBUTTAL)**: 102321 리뷰가 "exception semantics 미명세"로 지적했으나, v4 §4.5는 이미 정확한 5줄 패턴(unignore 3개 명시)을 제공하고 `git check-ignore` 검증 의무까지 포함. 추가 액션 없음 — 단 v5 §4.1에서 `_global/`을 P4로 이연했으므로 `.gitignore`의 `/runtime/warnings/_global/` 라인은 **P1에서는 제거** (디렉토리 자체가 없음 → 불필요). P4가 활성될 때 다시 추가.

---

## §5 escalation policy v0 (Acceptance #4)

### 5.1 P1에서 정의할 것 (P4가 이걸 기반으로 동작)

P1은 escalation policy를 **선언적 데이터로 명시**만 한다 (실제 적용은 P4).

```yaml
# config/escalation_policy.yaml (P1에서 신설)
# phase 키는 core/project_task_board.py:17 _PHASE_ORDER와 정확히 일치해야 함.
# 허용 값: scope, build, integrate, code_review, cross_validate, verify
version: 0
rules:
  - rule_id: e2e_command_missing
    activate_at: P2                                            # P2에서 BLOCK 활성 시작
    block_when:
      affected_phase_in: [build, integrate, code_review, cross_validate, verify]
      count_per_run_min: 1                                     # 위 phase에서 1건이라도 BLOCK 후보
    exempt_when:
      affected_phase_in: [scope]                               # scope 단계는 placeholder 허용 → WARN 유지
    rationale: "build 이후 단계에서는 e2e 검증 명령이 필수. scope phase는 task가 placeholder 상태일 수 있어 exempt."

  - rule_id: owner_role_mismatch
    activate_at: P4                                            # P3 measurement 후 P4에서 BLOCK 평가
    block_when:
      repeat_count_min: 3        # 같은 프로젝트에서 3회 이상 발생
    rationale: "P3 measurement 기간 후 임계 결정 — 초기엔 보수적. P4에서 활성."

  - rule_id: evidence_quality_warn
    activate_at: P4
    block_when:
      count_per_run_min: 5       # 단일 run에서 5개 이상 gap
    rationale: "근거 부족이 일정 수준 누적되면 후속 문서 신뢰도 붕괴. P4에서 활성."

  - rule_id: plan_verifier_warn
    activate_at: never           # 항상 advisory
    block_when: never
    rationale: "plan_verifier score는 refine 루프로 보정 가능 — escalation 보류"
```

**`activate_at` 필드 의미**: 이 rule의 BLOCK 평가가 어느 Phase에서 활성화되는지 명시. P1에선 `escalation_evaluator.py`가 stub이므로 모든 rule이 사실상 비활성. P2 진입 시 `activate_at: P2`인 rule만 평가, P4 진입 시 `activate_at: P2|P4`인 rule 모두 평가.

### 5.2 임계값 결정 원칙 (왜 위 숫자인가)

- **Phase 기반 (e2e_command_missing)**: build 이후 phase(build/integrate/code_review/cross_validate/verify)에서 1건이라도 발견되면 즉시 차단 — 코덱스 문서 §3 결론과 정합. scope phase는 의도된 placeholder가 있을 수 있어 exempt (work_item_generator가 task를 생성하는 시점에는 e2e_command가 비어 있고 후속 phase에서 채워짐).
- **Repeat 기반 (owner_role_mismatch)**: P3 measurement 기간(약 4주) 데이터 수집 후 재조정 예정. 초기 3회는 "한 프로젝트에서 3번 같은 owner 미스배정 = 패턴".
- **Count 기반 (evidence_quality_warn)**: 단일 run 5개 이상은 baseline 측정값(minesweeper에서 평균 1~2개) 대비 명확한 이상.
- **Never**: plan_verifier는 score가 refine 루프에서 회복되므로 BLOCK으로 직행하면 false positive 위험.

### 5.3 false_positive_override 처리

사용자가 `_decision.md`에서 "이건 OK"라고 명시하면, 이후 동일 record는 escalation 평가에서 제외 (`false_positive_override=true`로 신규 record 생성). P4에서 구현.

### 5.4 P1에서 코드에 들어갈 minimum

- `core/warning_registry.py`: `WarningRegistry(workspace)` 클래스 + `record()`, `summarize(slug)`, `load_global(rule_id)`
- `config/escalation_policy.yaml`: 위 v0 정책
- `core/escalation_evaluator.py` **stub** (v3, Finding #2 ACCEPT): `evaluate(record) -> EscalationDecision`은 항상 비활성 반환:

  ```python
  # core/escalation_evaluator.py (P1)
  from dataclasses import dataclass
  from core.warning_registry import WarningRecord

  @dataclass
  class EscalationDecision:
      block: bool                 # P1에서는 항상 False
      severity: str               # "warn" | "block_candidate" | "block"
      reason: str                 # 결정 근거 한 줄
      rule_id: str = ""           # decision report에 표시
      activate_at: str = ""       # 정책 yaml의 activate_at 인용

  def evaluate(record: WarningRecord) -> EscalationDecision:
      """P1 stub — 모든 rule이 inactive (P2/P4에서 점진 활성)."""
      return EscalationDecision(
          block=False,
          severity="warn",
          reason="inactive_phase",      # P2 활성 후엔 "phase_exempt" / "below_threshold" 등으로 분기
          rule_id=record.rule_id,
          activate_at="P2_or_later",
      )
  ```

  **이유 (Finding #2)**: body가 `pass`면 None 반환 → caller가 `.block`/`.severity` 접근 시 AttributeError. P1 stub도 반드시 `EscalationDecision` 인스턴스를 반환해야 P2 진입 시 시그니처 회귀 없이 body만 교체 가능. acceptance #8 (P2 stub은 모두 False)과 정합.

  **v5 보강 (Finding 102321 #6 ACCEPT — `evaluate()` 시그니처 확정)**: `evaluate()`는 단일 record만 받는다. `repeat_count` 같은 history 의존 정보는 §2.2 정책에 따라 **`record()` 내부에서 계산되어 record 자체에 persist**되므로, `evaluate(record)`가 `record.repeat_count`만 보면 history 스캔 없이 정책 매칭 가능. registry/history 인자 없음 — 시그니처 단순화 + P4가 P2/P3 데이터로 분기 시에도 record 자체로 self-contained.

### 5.5 escalation_policy.yaml loader (v5 — Finding 102321 #9 ACCEPT, Medium)

P1 단계에서 yaml은 stub이 읽지 않지만, P2 진입 시 즉시 필요. baseline `core/config_paths.py:38-41`의 frozen-aware 패턴을 차용:

```python
# core/escalation_evaluator.py (P1 stub)
import yaml
from core.config_paths import BASE_DIR     # frozen-aware (sys.frozen 분기 포함)

_POLICY_PATH = os.path.join(BASE_DIR, "config", "escalation_policy.yaml")

def _load_policy() -> dict:
    """P1: yaml 존재 검증만. P2가 정책 매칭 사용."""
    if not os.path.isfile(_POLICY_PATH):
        return {"version": 0, "rules": []}     # missing은 inactive와 동치
    with open(_POLICY_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {"version": 0, "rules": []}
```

`BASE_DIR`은 `core/config_paths.py:38-41`에서 frozen 시 `sys.executable` 기반, 소스 시 레포 루트 기반으로 자동 분기. PyInstaller `_MEIPASS` 경로 해석을 별도로 할 필요 없음 (이미 baseline이 처리).

**P1 acceptance**: `_load_policy()`가 yaml 파일을 읽어 dict 반환 (frozen build와 source mode 모두). 실제 정책 매칭은 P2.

---

## §6 Gate Decision Report 포맷 (Acceptance #5)

### 6.1 위치와 노출 경로

- **파일 경로**: `runtime/warnings/<project_slug>/_decision.md`
- **사용자 노출**: approval-gate.md의 `## Review Notes` 섹션에 자동 링크 추가 (P1에서 wiring).

### 6.2 _decision.md 포맷

```markdown
# Gate Decision Report — <project_slug>

- 생성: 2026-05-09T01:30:00+09:00
- 마지막 갱신: 2026-05-09T01:35:12+09:00
- 정책 버전: escalation_policy.yaml v0

## Active Decisions

### [BLOCK] e2e_command_missing — 2026-05-09T01:35:12

**상태**: block_candidate → block (자동 승격)
**임계**: build phase에서 발생, count=21
**근거**: escalation_policy.yaml > rules > e2e_command_missing > block_when (phase=build, count_per_run_min=1)
**관련 record**: runtime/warnings/<slug>/e2e_command_missing.jsonl (line 1)
**affected_ids**: T-001, T-002, ..., T-021
**해소 방법**: 각 task의 e2e_command 필드를 채우거나, 명시적으로 false_positive_override를 설정하세요.

---

### [WARN] owner_role_mismatch — 2026-05-09T01:35:12

**상태**: warn (block 미승격)
**현재 누적**: 1회 (block 임계 3회 미만)
**근거**: escalation_policy.yaml v0 — repeat_count_min=3 미충족
**관련 record**: runtime/warnings/<slug>/owner_role_mismatch.jsonl

---

## False Positive Overrides

(없음 — 사용자가 OK 표시한 record가 여기 누적)

## History

- 2026-05-09T01:35:12: e2e_command_missing → BLOCK
- 2026-05-09T01:23:45: e2e_command_missing → WARN (initial)
```

### 6.3 approval-gate.md와의 통합 (v4 — Finding 100614 #1 + 100406 #3 ACCEPT)

**근본 결함 (v3에서 잘못 가정)**: v3는 "approval-gate.md가 workspace 하위에 있으니 링크는 workspace 기준 상대경로"라고 단정했다. 그러나 baseline은 `core/work_item_generator.py:1061` `gate = ApprovalGate(doc_root, slug)` — gate는 **doc_root 하위**에 위치한다 (target_path 분리 모드에서 workspace ≠ doc_root). v3의 상대경로 링크는 `<doc_root>/runtime/warnings/<slug>/_decision.md`로 해석되어 깨진다.

**v4 해소 (옵션 A 채택)**: `ApprovalGate` 시그니처 확장 + 링크는 절대경로.

ApprovalGate API 변경:

```python
# core/approval_gate.py:78 (P1 PR에서 변경)
class ApprovalGate:
    def __init__(self, doc_root: str, slug: str, *, runtime_workspace: str | None = None):
        """
        doc_root: gate 파일 자체가 위치할 루트 (사용자 산출물 영역, baseline 그대로).
        runtime_workspace: warning registry / decision report가 위치한 운영 데이터 루트.
                            None이면 doc_root와 동일하게 가정 (단일 workspace 모드).
        """
        self.doc_root = os.path.abspath(doc_root)
        self.slug = slug
        self.runtime_workspace = os.path.abspath(runtime_workspace) if runtime_workspace else self.doc_root
```

**기존 인자명 정정**: 현 baseline의 `__init__(self, workspace: str, slug: str)`은 실제로는 doc_root를 받지만 인자명이 `workspace`로 혼란을 유발 — v4에서 `doc_root`로 rename (호출처 2곳: `core/work_item_generator.py:1061`, `core/project_pipeline.py:91`).

**호출처 수정** (target_workspace를 명시 전달):

```python
# core/work_item_generator.py:1061 (변경 후)
gate = ApprovalGate(doc_root, slug, runtime_workspace=workspace)

# core/project_pipeline.py:87-95 (변경 후)
def gate(self) -> ApprovalGate:
    return ApprovalGate(self._effective_doc_root(), self.work_item_slug,
                         runtime_workspace=self.workspace)
```

**Review Notes 링크 (절대경로 정책)**:

```
- gate_decision_report: <runtime_workspace>/runtime/warnings/<slug>/_decision.md
```

링크 렌더링 시 `_render()`에서 `runtime_workspace`로 절대경로 expand. 이유:
1. workspace ≠ doc_root인 경우 상대경로 계산 부담 + 사용자 가독성 저하 (`../../../../runtime/warnings/...`).
2. 절대경로는 multi-PC 동기화 시 path가 달라져도 _decision.md 자체가 workspace에 있으니 해당 PC 환경에서 그대로 클릭 가능 (사용자가 PC 옮길 때 git pull → start_db.py로 workspace 정합 보장).
3. baseline `_render()` / `_parse()` 정규식은 `## Review Notes` 본문의 plain text 라인이므로 절대경로 추가가 회귀 유발 없음 (`core/approval_gate.py:42-50` 5섹션 정규식 무관).

**통합 여부 결정**: 본문 통합 아닌 **링크 참조** 방식 유지 (v3 결정 그대로).

**v5 보강 (Finding 102321 #1 — Critical, REBUTTAL)**: 102321 리뷰는 v4 §6.3 본문 ("v3 가정 정정 + 절대경로 정책 채택")을 못 보고 v3 가정을 다시 비판. v4가 이미 채택한 fix:
- ApprovalGate 시그니처 확장 ✅ (위 코드 블록)
- `runtime_workspace` 별도 인자 도입 ✅ (`*, runtime_workspace=None`)
- 절대경로 정책 ✅ (`gate_decision_report: <abs_path>`)
- 호출처 2곳 명시 ✅ (work_item_generator:1061, project_pipeline:87-95)

리뷰가 요구한 Action(`os.path.abspath` 절대경로 또는 `_decision.md` doc_root 이동)은 v4가 전자(`os.path.abspath`)를 명시 채택한 상태. 따라서 ACCEPT는 유지하되 **fix는 v4에서 이미 완료**임을 명시. acceptance #18 추가로 §6.3 본문이 baseline 코드와 정합한지 grep 검증 의무화 (다음 라운드 sycophancy 방지).

이유:
1. approval-gate.md는 `_render()`/`_parse()`가 정해진 5섹션 포맷 (`core/approval_gate.py:42-50`)에 강하게 의존 — 본문 통합 시 파싱 정규식 수정 필요 (회귀 위험 큼).
2. _decision.md는 자주 갱신되는 누적 로그 성격, approval-gate는 승인 스냅샷 성격 (수명주기 다름).
3. 사용자는 approval-gate.md 한 곳만 보면 "추가로 봐야 할 곳"이 명시됨 (UX 동일).

P1에서 `core/approval_gate.py`에 추가할 변경 (최소):
- `_render()`의 `## Review Notes` 본문에 `decision_report_link`가 있으면 한 줄 추가.
- `initialize()` / `apply_verification_verdict()` 시 link 자동 주입.

---

## §7 P2~P6 의존성 다이어그램 (Acceptance #6)

### 7.1 의존 관계

```
                    ┌──────────────────────────────────┐
                    │  P1 (이 문서) — Warning Registry │
                    │  + Migration + Storage + Decision │
                    └────────────────┬─────────────────┘
                                     │ schema 의존
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
    ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────┐
    │  P2 phase-aware   │  │  P3 Owner Lint    │  │  P5 contract     │
    │  BLOCK (e2e only) │  │  measurement      │  │  drift 측정기   │
    │  build/integrate/ │  │  (BLOCK 없음)     │  │  (record만)     │
    │  code_review/     │  │                   │  │                  │
    │  cross_validate/  │  │                   │  │                  │
    │  verify           │  │                   │  │                  │
    └─────────┬─────────┘  └─────────┬─────────┘  └────────┬─────────┘
              │                      │                     │
              └──────────────────────┼─────────────────────┘
                                     ▼
                    ┌──────────────────────────────────┐
                    │  P4 escalation v1                │
                    │  P2/P3 데이터로 일부 rule을      │
                    │  block_candidate → block 승격    │
                    │  decision report 자동 갱신       │
                    └────────────────┬─────────────────┘
                                     │ activation 조건만
                                     ▼
                    ┌──────────────────────────────────┐
                    │  P6 (조건부) domain-specific gates│
                    │  기존 _domain 분기에 1줄 활성화 │
                    │  (포커, 카드 게임 등)            │
                    └──────────────────────────────────┘
```

### 7.2 단계별 산출물

| Phase | 핵심 산출물 | 코어 파일 (예상) | 의존 |
|-------|----------|--------------|------|
| **P1** (이 문서) | `WarningRecord`, registry, escalation_policy.yaml v0, _decision.md, 4건 마이그레이션 (BLOCK 활성화 없음) | `core/warning_registry.py`, `core/escalation_evaluator.py` (stub), `config/escalation_policy.yaml` | — |
| **P2** | phase-aware BLOCK (e2e_command_missing 한 rule만, baseline phase `build/integrate/code_review/cross_validate/verify`에서 발생 시 BLOCK) | `core/escalation_evaluator.py` (body), `core/project_pipeline.py` 호출 추가 | P1 |
| **P3** | Owner Lint measurement (BLOCK 없음, jsonl 누적만, false positive 분포 측정) | `core/project_pipeline.py:1401` 변경, 신규 측정 헬퍼 | P1 |
| **P4** | escalation v1 (P2/P3 데이터로 owner_role_mismatch / evidence_quality_warn 등 다른 rule을 BLOCK으로 점진 확장, false positive override 기능 추가) | `core/escalation_evaluator.py` (full), approval_gate 링크 wiring | P1, P2, P3 |
| **P5** | contract drift 측정기 (brief 보존율 grep, doc_consistency_drift record만 누적, BLOCK 없음) | `core/doc_consistency_meter.py` (신설) | P1 |
| **P6** | (조건부) domain-specific gates (포커 등) | 기존 `_domain` 분기에 activation 1줄, pack 추상화 미도입 | P1, P4 |

### 7.3 P1 PR scope (v4 갱신 — 한 PR로 출시)

- [ ] `core/warning_registry.py` 신설 — `WarningRegistry(workspace: str)` 클래스(§4.0). 메서드: `record(*, project_slug, rule_id, **fields)` / `summarize(*, project_slug)` / `load_global(*, rule_id)` / `rebuild_caches(*, project_slug)`. `WarningRecord` dataclass에 **`record_id` 필수 필드** (§2.1, idempotency).
- [ ] `core/escalation_evaluator.py` stub 신설 — `EscalationDecision` dataclass(§5.4: `block, severity, reason, rule_id, activate_at`) + `evaluate(record) -> EscalationDecision`이 항상 `EscalationDecision(block=False, severity="warn", reason="inactive_phase")` 반환 (v3 Finding #2 ACCEPT 유지).
- [ ] `config/escalation_policy.yaml` v0 작성 (§5.1, `activate_at` 필드 포함).
- [ ] **`core/approval_gate.py` 시그니처 확장 (v4 신규 — Finding 100614 #1)** — `ApprovalGate(doc_root, slug, *, runtime_workspace=None)`. 기존 `workspace` 인자명을 `doc_root`로 rename (실제 전달값과 정합). `_render()`에서 `runtime_workspace`가 있으면 `## Review Notes`에 `gate_decision_report: <abs_path>` 절대경로 라인 추가. 호출처 2곳 수정: `core/work_item_generator.py:1061` `ApprovalGate(doc_root, slug, runtime_workspace=workspace)`, `core/project_pipeline.py:87-95` `ApprovalGate(self._effective_doc_root(), self.work_item_slug, runtime_workspace=self.workspace)`.
- [ ] 4건 WARN 마이그레이션 (§3.1):
  - row 1 e2e_command_missing — phase 그룹별 분할 record
  - row 2 owner_role_mismatch — `detect_owner_drift -> list[tuple[task_id, expected, actual]]` (v4 — Finding 100614 #5)
  - row 3 evidence_quality_warn — `project_pipeline.py:756-774` 호출처에서 record (v3 ACCEPT 유지)
  - row 4 plan_verifier_warn — `project_pipeline.py:959-` 호출처에서 record
- [ ] `runtime/warnings/.gitkeep` + `runtime/warnings/_index.json` 초기 커밋 (workspace 하위, §4.0)
- [ ] **`.gitignore` 갱신 (v4 — Finding 100614 #4)** — §4.5의 정확한 5줄 패턴 추가. `git check-ignore` 검증 acceptance 포함.
- [ ] **`af.spec` hiddenimports 갱신 (v3 ACCEPT 유지)** — `af.spec:33-` 블록에 `'core.warning_registry'`, `'core.escalation_evaluator'` 추가. `config/escalation_policy.yaml`은 `af.spec:29` `('config', 'config')` data 매핑으로 자동 포함.
- [ ] **CLI 명령 (v4 — Finding 100614 #2)** — `python -m core.warning_registry summary --workspace=<path> --slug=<slug>` + `python -m core.warning_registry repair --workspace=<path> --slug=<slug>` (§8.3). `--workspace` 필수 (argparse error on missing).
- [ ] **`run_factory_cli.py` argparse subcommand 추가 (v5 — Finding 102321 #2)** — `warning-summary`, `warning-repair` 두 subcommand. handler는 `core.warning_registry.cli` 모듈 호출. frozen `af.exe <subcmd>` 동작 검증.
- [ ] **`_summary.json` atomic write 의무화 (v5 — Finding 102321 #3)** — `core/work_item_telemetry.py:55-65` 패턴(`tempfile.mkstemp + locked_file + os.replace`) 그대로 차용. lock 키는 slug 단위 (`<slug>/.lock`)로 통일.
- [ ] **summarize() read-on-demand 단일화 (v5 — Finding 102321 #5)** — `record()`는 jsonl append만, `_summary.json` 갱신은 `summarize()` 호출 시점 풀스캔. "10건마다 lazy 트리거" 명세 폐기.
- [ ] **phase 정규화 (v5 — Finding 102321 #4)** — `_PHASE_ALIAS` 딕셔너리 + `_normalize_phase()` 함수 (§2.2a). `record()` 진입 시 정규화 + `extra.original_phase` 보존.
- [ ] **repeat_count persist (v5 — Finding 102321 #6)** — `record()`가 SoT 풀스캔으로 prior count 계산 후 record에 채워 append. `evaluate(record)`는 history 인자 없음.
- [ ] **`_global/` P1 scope에서 제거 (v5 — Finding 102321 #7)** — 디렉토리 미생성. `load_global()` `NotImplementedError`. `.gitignore`의 `_global/` 라인 제거. P4가 활성 시 추가.
- [ ] **escalation_policy.yaml loader (v5 — Finding 102321 #9)** — `core/escalation_evaluator._load_policy()` 헬퍼 + `core/config_paths.BASE_DIR` 사용 (frozen-aware).
- [ ] **open schema deserializer (v5 — Finding 102321 #10)** — `WarningRecord.schema_version` 필드 + unknown field → `extra` 흡수 + missing field default.
- [ ] tests (v5 갱신):
  - `tests/test_warning_registry.py` (8 케이스): record / summarize (by_phase 포함, read-on-demand) / lock 동시성 / IOError 격리 / record_id idempotency / phase 정규화 (alias + unknown fallback) / repeat_count persist 정확 / atomic write (mid-write crash 시 이전 본 보존)
  - `tests/test_warning_registry_migration_callsites.py` (4 케이스): 4건 호출처 record 호출 검증 (mock). owner_role_mismatch는 3-tuple 시그니처.
  - `tests/test_approval_gate_runtime_workspace.py` (3 케이스, v4 신규 — v5 유지): single mode / 분리 mode 절대경로 / `_render`/`_parse` 회귀.
  - `tests/test_warning_registry_cli.py` (4 케이스, v5 갱신): summary --workspace 미지정 시 argparse error / repair가 cache 재생성 정확 / **frozen subcommand wiring (af.exe warning-summary 동작)** / repair record_id 중복 시 idempotent.
  - `tests/test_warning_registry_schema_evolution.py` (1 케이스, v5 신규): v0.1 record + v0.2 신규 필드 round-trip.
- [ ] Master_Blueprint.md §3 (warning_registry 신규 섹션) + §12 변경 이력 갱신.

---

## §8 비기능 요구사항

### 8.1 성능

- jsonl append 1회당 < 5ms (디스크 fsync 포함). 측정 후 v1.1에서 batch 옵션 검토.
- registry record 실패 시 본 흐름 영향 0 — try/except + 로그만.
- _summary.json 갱신은 lazy (10건마다 1회 또는 run 종료 시점) — record 단계에서 매번 갱신하지 않음.

### 8.2 backward compatibility

- 기존 `_LOGGER.warning(...)` 호출 모두 유지 (사용자 가시 로그 회귀 없음).
- 기존 `evidence._warnings` 리스트 유지.
- approval-gate.md `_render`/`_parse` 정규식 수정 없음 (링크는 review_notes 본문에 plain text로).

### 8.3 관측 가능성 (v5 — Finding 102321 #2 + #11 보강)

**RunEvent 결정 (Finding 102321 #11 HOLD → DECIDE)**: P1에서 RunEvent **미발행** 못박음. 이유:
- baseline에 `core/events.py` 또는 `RunEvent` 클래스 부재 (grep 검증: `grep -rln "class RunEvent\|run_event" core/*.py` → 0 매치).
- P1 record 호출처 (`work_item_generator.py:1056`, `project_pipeline.py:1402,759,966` 등)에서 `run_id` 가용성도 일관 보장 안 됨 (일부 경로는 run_id 없는 boot phase).
- 따라서 P1은 jsonl + summary cache만 → 충분한 관측성. RunEvent 통합은 P4에서 escalation 활성 시 함께 검토 (별도 PR scope).

**CLI 명령** (P1, `--workspace` 필수, source + frozen 양쪽 지원):

| 환경 | 명령어 |
|------|-------|
| 소스 모드 (개발) | `python -m core.warning_registry summary --workspace <path> --slug <slug>` |
| 소스 모드 (개발) | `python -m core.warning_registry repair --workspace <path> --slug <slug>` |
| frozen build | `af.exe warning-summary --workspace <path> --slug <slug>` (v5 추가 — Finding 102321 #2) |
| frozen build | `af.exe warning-repair --workspace <path> --slug <slug>` (v5 추가) |

**frozen build subcommand wiring (v5 — Finding 102321 #2 ACCEPT)**: `run_factory_cli.py`의 argparse subcommand 트리에 `warning-summary`, `warning-repair` 두 subcommand 추가. handler는 `core.warning_registry.cli.summary_cmd(args)` / `repair_cmd(args)`를 호출. PyInstaller frozen에서 `python -m`이 동작하지 않으므로 `af.exe <subcmd>` 진입점이 필수.

**`--workspace` 미지정 동작**: `argparse`가 즉시 `error: the following arguments are required: --workspace` 출력 + exit 2. cwd / `AF_WORKSPACE` env / doc_root fallback 모두 금지 (§4.0과 정합).

v0.1+에서 사용자 요청 있으면 `AF_WORKSPACE` env fallback 추가 검토 (현재는 over-design 회피 — CLAUDE.md "Simplicity First").

---

## §9 거부된 설계 결정 (이유 명시)

| 안 | 거부 이유 |
|----|--------|
| WarningRecord에 `severity_score: float` 필드 | 0.0~1.0 임계는 escalation_policy.yaml로 외화 가능 — schema 비대 회피 |
| `runtime/warnings/<slug>/<rule_id>/<ts>.json` 파일당 1 record | inode 폭발 + 통계 어려움. jsonl append가 정합 |
| approval-gate.md 본문에 _decision.md 통째로 inline | `_render`/`_parse` 정규식 회귀 위험 (§6.3) |
| escalation_policy를 Python 코드로 하드코딩 | 정책 변경마다 재배포 필요. yaml 외화로 운영 분리 |
| P1에서 BLOCK 승격 즉시 활성화 | 데이터 0건 상태에서 임계 결정 시 false positive 다발. P4까지 stub |
| `affected_phase`에 `design`/`test`/`integration` 신설 | baseline `_PHASE_ORDER` (`core/project_task_board.py:17`)에 존재하지 않는 phase. work_item_generator가 task에 부여하지 않는 값으로 정책을 만들면 silent skip. baseline 확장은 별도 PR로 분리. |
| owner_role_mismatch record를 `detect_owner_drift` 내부에서 호출 (옵션 b) | helper의 단일 책임 원칙 위배 + import 사이클 위험. 호출처에 책임을 두는 것이 정합. |

---

## §10 측정 가능 acceptance (다음 세션 검증용)

P1 머지 후 다음이 모두 충족되어야 다음 단계(P2) 진입:

1. `runtime/warnings/<slug>/e2e_command_missing.jsonl`이 minesweeper baseline 재실행 시 **phase 그룹별로 분할 record**로 기록된다 (총 count 합계 = 21, phase별 record는 baseline의 task phase 분포에 따라 1~5건). 단일 record로 21을 모두 묶지 않는다 (§3.1 row 1 원칙).
2. `python -m core.warning_registry summary --slug=<slug>`이 by_rule 딕셔너리를 출력하고, by_rule.e2e_command_missing.by_phase 분포가 표시된다.
3. approval-gate.md `## Review Notes`에 `gate_decision_report:` 라인이 자동 추가된다.
4. 기존 `_LOGGER.warning("e2e_command 누락 task ...")` 로그 메시지가 동일하게 출력된다 (회귀 없음).
5. `detect_owner_drift()`의 새 시그니처(`-> list[tuple[str,str]]`)가 기존 호출처(`core/project_pipeline.py:1401-1406`)에서 truthy 분기를 깨지 않는다 (빈 리스트는 falsy → if 분기 회귀 없음).
6. tests/test_warning_registry.py 4 케이스 PASS, tests/test_warning_registry_migration_callsites.py 4 케이스 PASS.
7. registry record 호출이 본 흐름을 깨지 않는다 (모의 IOError 주입 시에도 work_item 생성 성공).
8. P1 단계에서 `escalation_evaluator.evaluate(record)`가 모든 record에 대해 `EscalationDecision(block=False, severity="warn", reason="inactive_phase")` 인스턴스를 반환한다 (None 아님 — Finding #2). P2 진입 후엔 동일 시그니처에서 body만 교체되어 `affected_phase="scope"`는 `block=False`, `affected_phase="build"`는 `block=True`로 분기.
9. **registry 인스턴스화는 항상 `WarningRegistry(workspace=target_workspace)`** 패턴 (Finding #1). cwd 또는 doc_root fallback 사용 호출처가 발견되면 acceptance 미충족.
10. **`af.spec` hiddenimports에 `core.warning_registry`, `core.escalation_evaluator`가 등록되어 있고**, `python build_exe.py`로 frozen build (`dist/af-{version}/af.exe`) 생성 후 work_item 생성 시 ImportError 없음 (Finding #4).
11. `_summary.json`의 `by_rule.<rule>.by_phase` 필드가 phase별 count 분포를 정확히 dump한다 (v3 Finding #3 — acceptance #2와 정합).
12. **(v4 Finding 100614 #1)** target_path 분리 모드(`workspace ≠ doc_root`)에서 approval-gate.md `## Review Notes`의 `gate_decision_report:` 라인이 **절대경로**로 렌더링되고, 클릭 시 `<runtime_workspace>/runtime/warnings/<slug>/_decision.md`를 정확히 가리킨다.
13. **(v4 Finding 100614 #2)** `python -m core.warning_registry summary --slug=<slug>`이 `--workspace` 인자 없으면 `argparse error: the following arguments are required: --workspace` exit 2로 실패한다.
14. **(v4 Finding 100614 #3)** `<slug>/<rule>.jsonl` SoT만 보존하고 `_summary.json` + `_global/` 삭제 후 `repair --workspace=... --slug=...` 실행 시 두 cache가 SoT와 정합하게 재생성된다. record_id 중복 시 append 1회로 idempotent.
15. **(v4 Finding 100614 #4)** `.gitignore` 갱신 후 `git check-ignore -v runtime/warnings/<slug>/<rule>.jsonl`은 매치, `git check-ignore -v runtime/warnings/_index.json`은 매치 없음 (trackable).
16. **(v4 Finding 100614 #5)** `detect_owner_drift()`가 `list[tuple[task_id, expected_owner, actual_owner]]`를 반환하고, `extra["mismatches"]`에 dict 구조도 보존된다.
17. **(v4 Finding 100406 #5)** `_PHASE_ORDER` 6개 phase 중 `scope`만 exempt — §0 / §5.1 / §7.2의 phase 리스트가 모두 `build/integrate/code_review/cross_validate/verify` 5개로 일치한다 (텍스트 grep 검증).
18. **(v5 Finding 102321 #1 REBUTTAL 검증)** §6.3 본문이 baseline 코드와 정합한지 grep 검증: `grep -n "ApprovalGate(doc_root, slug" core/work_item_generator.py core/project_pipeline.py` → 양쪽 모두 매치, `grep "runtime_workspace" docs/2026-05-09-warning-registry-and-gate-escalation-design.md` → 본문에 시그니처/호출처 모두 명시.
19. **(v5 Finding 102321 #2)** frozen build에서 `af.exe warning-summary --workspace <path> --slug <slug>`이 동작하고 `--workspace` 미지정 시 argparse error로 exit 2.
20. **(v5 Finding 102321 #3)** `_summary.json` mid-write에 의도적 crash 주입(예: `os.replace` 직전 sigkill mock) 후에도 이전 정상본이 손상되지 않는다 (`tempfile.mkstemp + os.replace` atomic 패턴 검증).
21. **(v5 Finding 102321 #4)** `record(affected_phase="design")` 호출 시 jsonl에는 `affected_phase=scope` + `extra.original_phase=design` 저장. `record(affected_phase="unknown_x")` → `affected_phase=build` + `extra.original_phase=unknown_x` fallback.
22. **(v5 Finding 102321 #5)** `summarize()` 호출이 jsonl SoT 풀스캔을 수행하고 `_summary.json`을 atomic write로 갱신. record 1건 케이스에서도 stale 없음 (read-on-demand).
23. **(v5 Finding 102321 #6)** 동일 slug + rule_id로 3회 record 호출 시 마지막 record의 `repeat_count == 3`. `evaluate(record)`는 record.repeat_count만 보고 `repeat_count_min: 3` 정책 매칭.
24. **(v5 Finding 102321 #7)** P1 머지 후 `<workspace>/runtime/warnings/_global/` 디렉토리가 생성되지 않는다. `WarningRegistry.load_global(rule_id="x")` 호출 시 `NotImplementedError`.
25. **(v5 Finding 102321 #9)** `_load_policy()` 호출이 source mode와 frozen build (`af.exe`) 양쪽에서 `config/escalation_policy.yaml`을 읽어 dict 반환. `core.config_paths.BASE_DIR` 사용 검증.
26. **(v5 Finding 102321 #10)** `WarningRecord.schema_version=1` 인스턴스 jsonl 직렬화 후, schema_version=2 + 신규 필드를 가진 record와 같은 jsonl 파일에 공존하고 deserializer가 둘 다 정상 로드 (round-trip).
27. **(v5 Finding 102321 #11)** P1 record 호출에서 RunEvent 미발행 — `grep -rn "RunEvent\|run_event" core/warning_registry.py` → 0 매치.

---

## §11 다음 단계

P1 PR 작성 시:
1. 이 설계문서가 cross-review 통과 (BLOCK 0건) 확인.
2. Sonnet으로 모델 전환 (메모리 규칙: 코드 구현은 Sonnet).
3. `core/warning_registry.py` 부터 시작. 4건 마이그레이션은 위 §3.1 표 순서대로.
4. 머지 전 3-tier (af-test-runner / af-critic / af-cross-review) 모두 PASS 또는 WARN-only.

---

## §12 변경 이력

- 2026-05-09 v1: 초안 작성 (Opus 4.7). codex 문서 §3/§6/§8 분석 결론 반영. minesweeper baseline 21/21 결측 + 3/7 owner 미스배정 데이터 인용. acceptance 6개 항목 충족.
- 2026-05-09 v2: af-cross-review Round 1 BLOCK 4건 + Medium 1 + Low 1 모두 반영 (Opus 4.7).
  - §0 / §1.2 / §7.2: BLOCK 활성화 시점 3-way 모순 해소 → "P1 stub, P2 e2e_command만 활성, P4에서 다른 rule 확장"으로 일관화 (#3 ACCEPT).
  - §2.1 affected_phase enum: `scope/design/build/test/verify/integration` → baseline `_PHASE_ORDER` 6개(`scope/build/integrate/code_review/cross_validate/verify`)로 통일 (#1 ACCEPT).
  - §3.1 row 1: e2e_command record를 task별 `phase` 필드로 그룹화한 phase별 분할 발화로 변경, exempt 분기 가능하게 정정 (#2 ACCEPT).
  - §3.1 row 2: `detect_owner_drift()` 시그니처를 `bool` → `list[tuple[str,str]]`로 확장(옵션 a 채택), 호출처 회귀 없음 보장. `affected_phase="design"` → `"build"`로 정정. "logger.info" → "logger.warning" 정정 (#4 ACCEPT, #6 ACCEPT-ADV).
  - §4.4: `core/file_io.locked_file` → `core/file_lock.locked_file` 모듈 경로 정정 (#5 ACCEPT).
  - §5.1: `escalation_policy.yaml`에 `activate_at` 필드 추가, phase 키를 baseline taxonomy로 정정.
  - §10 acceptance: phase 분할 검증 + detect_owner_drift 시그니처 회귀 검증 + escalation_evaluator P2 케이스 추가 (3건 → 8건).
- 2026-05-09 v3: v2 자동 cross-review BLOCK 5건 (High 2 / Medium 3) 모두 반영 (Opus 4.7). 리뷰 리포트: `docs/reviews/2026-05-09-095135-...-design-review.md`.
  - **§4.0 신설 (Finding #1, High ACCEPT)**: `runtime/warnings/`의 path ownership을 **workspace 하위로 고정**. baseline 인용 (`core/work_item_generator.py:948,1042` / `core/project_pipeline.py:946`) 명시. `WarningRegistry(workspace: str)` 생성자 시그니처 강제. `record()`는 `project_slug`만 받고 workspace는 인스턴스 상태로. cwd/doc_root fallback 금지.
  - **§5.4 (Finding #2, High ACCEPT)**: `escalation_evaluator.py` stub의 body가 `pass`(None 반환) → `EscalationDecision(block=False, severity="warn", reason="inactive_phase", rule_id=record.rule_id, activate_at="P2_or_later")` 인스턴스 반환으로 변경. dataclass 필드 5개(`block`/`severity`/`reason`/`rule_id`/`activate_at`)를 §5.4 코드 블록에 명시. caller(`approval_gate`/`project_pipeline`)가 `.block`/`.severity` 접근 시 AttributeError 방지.
  - **§4.3 (Finding #3, Medium ACCEPT)**: `_summary.json.by_rule.<rule>`에 `by_phase: {<phase>: <count>}` 필드 추가. CLI `python -m core.warning_registry summary --slug=<slug>`이 acceptance #2의 `by_rule.e2e_command_missing.by_phase` 출력 요구를 충족하도록 schema 정합성 확보.
  - **§7.3 (Finding #4, Medium ACCEPT)**: `af.spec:33-` hiddenimports 블록에 `core.warning_registry` / `core.escalation_evaluator` 추가 항목을 PR scope 체크리스트에 명시. 기존 `core.work_item_telemetry`(line 78) / `core.plan_verifier`(line 148)와 동일 패턴. `config/escalation_policy.yaml`은 `af.spec:29` `('config', 'config')` data 매핑으로 자동 포함 — yaml 경로는 `config/` 하위 유지.
  - **§3.1 row 3 (Finding #5, Medium ACCEPT)**: `evidence_quality_warn` record 호출 위치를 `core/research_verifier.py` → 호출처 `core/project_pipeline.py:756-774` (`_vr` 반환 직후)로 이동. 이유: `ResearchVerifier()` 인스턴스화(`core/project_pipeline.py:725`)가 slug/workspace 인자 없음, `verify_with_retry(evidence_fn, task_input)`도 workspace 미수신 → verifier 내부에서는 record 호출 시 path 결정 불가. 호출처는 `slug`(메서드 인자) + `target_workspace`(지역변수) 모두 가용.
  - **§7.3 PR scope 갱신**: `WarningRegistry(workspace)` 명시 / EscalationDecision dataclass 필드 명시 / af.spec 항목 추가 / approval-gate 링크의 workspace 기준 명시.
  - **§6.3 (Finding #1 보강)**: `gate_decision_report:` 링크의 의미를 "workspace 기준 상대 경로"로 명시. doc_root는 사용자 산출물용이므로 _decision.md가 그쪽에 가지 않는다는 결정 근거 추가.
  - **§10 acceptance**: 8건 → 11건. #8을 P1 stub 시맨틱(EscalationDecision 인스턴스 반환)으로 명확화. #9(workspace 인자 강제) / #10(af.spec hiddenimports + frozen build smoke) / #11(by_phase 분포 dump) 추가.
- 2026-05-09 v4: v3 자동 cross-review 2건(100406, 100614) BLOCK 6건 (High 3 / Medium 3) 모두 반영 (Opus 4.7). **근본 원칙 재정립: baseline의 workspace/doc_root 분리를 정직하게 모델링**.
  - **§4.0 재작성 (Finding 100614 #1 + 100406 #3 ACCEPT, High)**: v3가 "warnings는 workspace, gate도 workspace"로 단정한 것을 정정. baseline은 `core/work_item_generator.py:1061` `gate = ApprovalGate(doc_root, slug)` — gate는 doc_root에 위치. v4는 4가지 path 정책표 명시: warnings(SoT+cache+_decision.md)는 workspace / approval-gate.md는 doc_root / 둘이 다를 수 있으므로 ApprovalGate가 양쪽 path 모두 인지. baseline 분리 의도 (workspace=AF 운영 / doc_root=사용자 산출물) 보존.
  - **§4.0a 신설 (Finding 100614 #3 ACCEPT, High — partial-write recovery)**: SoT vs cache 분리 명시. `<slug>/<rule>.jsonl` SoT, `_summary.json` / `_global/<rule>.jsonl` rebuildable cache. record_id idempotency key + `rebuild_caches()` API + `repair` CLI 추가.
  - **§2.1 (Finding 100614 #3 ACCEPT)**: `WarningRecord`에 `record_id` 필수 필드 추가 (`f"{slug}:{rule_id}:{ts}:{hash6}"`).
  - **§3.1 row 2 (Finding 100614 #5 ACCEPT, Medium)**: `detect_owner_drift -> list[tuple[str,str]]` → `list[tuple[str, str, str]]` ((task_id, expected_owner, actual_owner)). baseline의 `mod_owner` / `task_owner` 분리(`core/project_task_board.py:230,244`) 보존. `extra["mismatches"]`에 dict 구조도 동시 기록.
  - **§4.5 재작성 (Finding 100614 #4 ACCEPT, Medium)**: `.gitignore` 패턴을 동적 slug에 작동 가능한 정확한 5줄 글로브로 명시 (`/runtime/warnings/*` + 3개 `!` unignore + `/runtime/warnings/_global/`). `git check-ignore` 검증 추가.
  - **§6.3 재작성 (Finding 100614 #1 ACCEPT, High)**: `ApprovalGate(doc_root, slug, *, runtime_workspace=None)` 시그니처 확장. 기존 인자명 `workspace`를 `doc_root`로 rename (실제 전달값과 일치). `_render()`에서 `gate_decision_report:` 라인을 절대경로로 렌더링. 호출처 2곳(work_item_generator:1061, project_pipeline:87-95) 수정 명시.
  - **§8.3 재작성 (Finding 100614 #2 ACCEPT, High)**: CLI 시그니처에 `--workspace` 필수 인자 강제. `summary` + `repair` 두 명령. cwd / env / doc_root fallback 모두 금지.
  - **§0 (Finding 100406 #5 ACCEPT, Medium)**: P2 활성 phase 리스트가 §0(`build/verify/code_review/cross_validate` 4개)과 §5.1(`build/integrate/code_review/cross_validate/verify` 5개) 사이 불일치 → `integrate` 추가해 5개로 통일.
  - **§7.3 PR scope**: `core/approval_gate.py` 시그니처 확장 항목 추가 / `repair` CLI 추가 / `record_id` 필드 추가 / 정확한 .gitignore 패턴 / 신규 테스트 2개 (`test_approval_gate_runtime_workspace.py`, `test_warning_registry_cli.py`) 추가.
  - **§10 acceptance**: 11건 → 17건. #12-17은 v4 6건 finding의 검증 케이스 (절대경로 링크 / CLI argparse error / repair idempotency / git check-ignore / drift 3-tuple / phase enum 텍스트 일치).
  - **OBSOLETE finding (v3가 이미 fix)**: 100406 #1 (evidence_quality_warn 호출처 이동, v3 §3.1 row 3) / 100406 #2 (af.spec hiddenimports, v3 §7.3) / 100406 #4 (by_phase 추가, v3 §4.3 — 100406 제안한 nested schema {scope: {count, severity}}는 advisory로 분류, v4는 v3의 평면 schema {scope: 5} 유지 — acceptance #2 충족 가능).
- 2026-05-09 v5: v4 통합 cross-review (102321, claude critic + codex cross + judge=claude) 11 finding 중 ACCEPT 9 / REBUTTAL 2 / HOLD→DECIDE 1 모두 처리 (Opus 4.7).
  - **§2.2a 신설 (Finding 102321 #4 ACCEPT, High — phase 정규화)**: `_PHASE_ALIAS` 딕셔너리 + `_normalize_phase()` 함수. 비표준 phase(`"design"`/`"test"`/`"integration"`)는 baseline의 `scope`/`verify`/`integrate`로 alias. unknown은 `build` fallback + `extra.original_phase` 보존 → §5.1 정책 silent skip 방지.
  - **§2.4 신설 (Finding 102321 #10 ACCEPT, Medium — open schema)**: append-only / unknown field tolerance / missing field default / `schema_version: int = 1` 필드 추가. P4 schema 변경 시 deserializer 분기 가능.
  - **§2.2 (Finding 102321 #6 ACCEPT, High — repeat_count 소유권)**: "P4가 계산" → **"`record()` 내부에서 SoT 풀스캔으로 prior count 계산 후 persist"**. `evaluate(record)`는 history 인자 없이 `record.repeat_count`만 보면 됨.
  - **§4.1 (Finding 102321 #7 ACCEPT, High — _global P4 이연)**: `_global/<rule>.jsonl` 디렉토리를 P1 scope에서 제거. `load_global()`은 `NotImplementedError`. `.gitignore`의 `_global/` 라인도 P1에서 제거. P4 활성 시 `rebuild_global()` API 추가.
  - **§4.4 재작성 (Finding 102321 #3 + #5 ACCEPT, High)**: (a) `_summary.json` 갱신을 `tempfile.mkstemp + locked_file + os.replace` atomic 패턴 의무화 (`core/work_item_telemetry.py:55-65` 인용). (b) lock 키를 slug 단위(`<slug>/.lock`)로 통일해 rule별 lock 비대칭 race 제거. (c) "10건마다 lazy 트리거" 명세 폐기 → `summarize()` read-on-demand 단일화로 stale 제거.
  - **§5.4 보강 (Finding 102321 #6)**: `evaluate()` 시그니처 확정 — 단일 record 인자, history 인자 없음. record가 self-contained (#6과 §2.2 정합).
  - **§5.5 신설 (Finding 102321 #9 ACCEPT, Medium — yaml loader)**: `_load_policy()` 헬퍼 + `core.config_paths.BASE_DIR` 사용. frozen-aware (baseline `core/config_paths.py:38-41` 패턴 차용 — `_MEIPASS` 직접 분기 불필요).
  - **§8.3 재작성 (Finding 102321 #2 + #11)**: (a) frozen `af.exe warning-summary`/`warning-repair` subcommand 추가 (PyInstaller에서 `python -m` 미동작 → `run_factory_cli.py` argparse subcommand wiring). (b) RunEvent **P1 미발행 못박음** — baseline `core/events.py` 부재 + record 호출처 일부에서 `run_id` 미가용. P4 escalation 활성 시 함께 검토.
  - **§4.5 보강 (Finding 102321 #8 REBUTTAL)**: v4 §4.5의 5줄 글로브 패턴이 이미 정확. 단 §4.1 `_global/` 이연에 따라 P1에서는 `/runtime/warnings/_global/` 라인 제거.
  - **§6.3 보강 (Finding 102321 #1 REBUTTAL — Critical)**: 102321 리뷰가 v4 §6.3 본문(이미 ApprovalGate 시그니처 확장 + 절대경로 정책 채택)을 못 보고 v3 가정을 다시 비판. v4 fix 4건(시그니처 확장 / runtime_workspace 인자 / 절대경로 / 호출처 2곳)이 리뷰 Action Required와 정합 → 추가 변경 없음. acceptance #18 (grep 검증) 추가로 다음 라운드 sycophancy 방지.
  - **§7.3 PR scope**: subcommand wiring / atomic write / read-on-demand / phase 정규화 / repeat_count persist / _global 제거 / yaml loader / open schema 등 8개 항목 신규 추가. 테스트 6 → 8 케이스 + 신규 schema_evolution + cli 4 케이스.
  - **§10 acceptance**: 17건 → 27건. #18-27이 v5 9개 ACCEPT + 2 REBUTTAL 검증.
  - **REJECTED 관리**: detect_owner_drift 회귀 우려 (v4 검증 완료) / phase 분포 추정 정확성 (acceptance #1로 흡수) / Blueprint §3 placement (PR scope에 이미 포함, recommendation으로 격하).
