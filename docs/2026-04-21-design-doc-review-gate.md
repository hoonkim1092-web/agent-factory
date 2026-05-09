# 설계문서 교차검증 파이프라인 강제 — Design (v2)

<!-- created: 2026-04-21 | v2: af-doc-qa 역할 불일치 해소 — 단일 설계문서는 af-critic + af-cross-review 2개로 축소 | purpose: CLAUDE.md 텍스트 규칙만으로는 교차검증이 누락되는 문제를 hook 기반 강제로 해결 | author: Claude (design), handoff to Sonnet (implementation) -->

## 변경 이력

- **v1 → v2 (2026-04-21, 교차검증 BLOCK 반영)**:
  - [Critical] af-doc-qa 역할 불일치 해소 — `.claude/agents/af-doc-qa.md`는 work-item 4-문서 세트 전용이므로 단일 설계문서 게이트에서 제외. `design` 타입 요구 에이전트를 **af-critic + af-cross-review 2개**로 축소 (3→2)
  - [Critical] `record_review_done` 시그니처를 "tier optional화 (기본값 0)"로 **확정** — 제거 시 hook_runner 호출부 파손
  - [High] af-critic 공유 가정 I4를 불변식에서 **한계(L)로 재분류** + v1에서도 `files_snapshot` 기반 최소 보호 추가 (혼합 commit 시 각 타입 파일이 어느 리뷰 snapshot에 포함됐는지 검증)
  - [High] verdict 체크를 `required_agents` 집합으로 **제한** — 이전 실행의 stale BLOCK verdict가 현재 commit을 오탐 차단하는 문제 해소
  - [High] 레거시 큐 경로 형식 — enqueue 시점에 workspace 상대 경로로 **정규화**하는 규약 명시
  - [Medium] `af-doc-qa` tier 파라미터 관련 결정 삭제 (더 이상 tracked agents 아님)
  - [Medium] `clear_committed_files`는 확장자 무관하게 `files_set.intersection` 기반 동작 확인 — 별도 변경 불필요
  - [Medium] `docs/patterns/*.md`는 **design 분류에서 제외** 확정 (짧은 참조성 패턴 노트)
  - [Medium] `docs/features/`, `docs/reviews/`, `docs/plans/`, `docs/standards/` 서브디렉토리는 **design 분류 포함** (§1.1 명시)

---

## 0. 배경 & 목표

### 현재 상태
- `.py` 파일: `.githooks/pre-commit` + `scripts/review_gate.py`가 af-test-runner → af-critic → af-cross-review 3-tier를 강제
- `.md` 설계문서: CLAUDE.md에 "af-doc-qa + af-critic + af-cross-review 3개 병렬" 텍스트 규칙만 있음
- **문제:** 텍스트 규칙은 에이전트가 깜빡하거나 일부만 실행해도 commit이 통과됨 (B2-6 설계 과정에서 실제로 발생)

### 목표
`.md` 설계문서 commit 시도 시, 3-agent 교차검증 완료 없으면 pre-commit hook에서 차단. 기존 `.py` review-gate와 동일한 수준의 강제력.

---

## 1. 범위 정의

### 1.1 대상 파일

**차단 대상 (설계문서):**
- `docs/*.md` 및 다음 서브디렉토리:
  - `docs/features/*.md`
  - `docs/reviews/*.md`
  - `docs/plans/*.md`
  - `docs/standards/*.md`
- **제외 경로** (design 아님):
  - `docs/code_review/code-review.md` (살아있는 단일 문서, 날짜 없음 — CLAUDE.md 규칙)
  - `docs/work-items/**/*.md` (자동 생성 work-item, LLM이 작성·편집. af-doc-qa가 전용으로 처리)
  - `docs/patterns/*.md` (짧은 참조성 패턴 노트, 단일 설계문서 엄격도 불요)
- 확장자는 `.md`만 (설계문서 규칙: `YYYY-MM-DD-제목.md`)

**차단 비대상:**
- `Master_Blueprint.md` (기존 Blueprint 스테이징 체크로 이미 다룸)
- `README.md`, `CLAUDE.md`, 그 외 루트 `.md` (설정·메타 문서)

### 1.2 판정 규칙

한 commit에 차단 대상 `.md`가 하나라도 포함되면 교차검증 필요. 각 대상 파일에 대해:
- **af-critic + af-cross-review 2개 모두** 리뷰 완료 기록 존재 (af-doc-qa는 work-item 전용, 단일 설계문서에는 부적합 — §변경이력 v1→v2 참조)
- 리뷰 이후 해당 파일 재편집 없음 (stale 방지)
- 모든 verdict ≠ BLOCK/FAIL

하나라도 미완 → commit 차단. 우회: `AF_SKIP_REVIEW_GATE=1 git commit ...` (기존 .py 게이트와 공유).

---

## 2. 아키텍처 — 기존 인프라 재사용

### 2.1 단일 큐 vs 분리 큐

**선택: 단일 큐 + 타입 마커**

기존 `.af_review_queue/pending_agent_review.json`을 확장하여 `.md` 파일도 같은 큐에 저장. 파일별 타입으로 요구 에이전트 세트 결정.

```json
{
  "files": ["core/foo.py", "docs/2026-04-21-foo.md"],
  "file_types": {
    "core/foo.py": "code",
    "docs/2026-04-21-foo.md": "design"
  },
  "reviews": {
    "af-test-runner": {...},      // code 전용 tier 1
    "af-doc-qa": {...},           // design 전용 tier 1
    "af-critic": {...},           // 공통 tier 2
    "af-cross-review": {...}      // 공통 tier 3
  },
  "updated_at": 1234567890.0
}
```

**이유:**
- 단일 파일 = 동시성 락 로직 재사용
- 같은 commit에 `.py` + `.md`가 섞이는 경우(설계 + 구현 동시) 단일 판정 경로
- `af-critic`, `af-cross-review`가 양쪽에서 공유되므로 중복 저장 불필요

### 2.2 요구 에이전트 세트

```python
# scripts/review_gate.py 신규 상수
_REQUIRED_AGENTS_BY_TYPE: dict[str, list[str]] = {
    "code": ["af-test-runner", "af-critic", "af-cross-review"],
    "design": ["af-critic", "af-cross-review"],  # v2: af-doc-qa 제외 (work-item 전용)
}
```

**af-doc-qa 제외 사유:** `.claude/agents/af-doc-qa.md:11-32`에 따르면 af-doc-qa는 work-item 4-문서 세트(feature-plan + feature-spec + implementation-design + implementation-tasks)의 "개별 품질 + 문서 간 정합성"을 검증하는 전용 에이전트. Step 1이 `ls -t docs/work-items/ | head -1`로 4-문서 디렉토리를 수집하므로 단일 설계문서(`docs/YYYY-MM-DD-*.md`)에 적용하면 엉뚱한 work-item을 검증하거나 상관없는 체크리스트를 적용. 단일 설계문서는 af-critic의 독립 비평 + af-cross-review의 Codex 기반 독립 교차검증 2축으로 충분.

### 2.3 판정 로직 확장

`is_gate_blocked(workspace)` 로직 변경:

```python
def is_gate_blocked(workspace: str) -> tuple[bool, str]:
    # ... (env bypass, load state, no-queue — 기존 동일)

    files = state.get("files", [])
    file_types = state.get("file_types") or {}

    # 파일이 없으면 PASS (기존 no-py-files 로직 확장)
    if not files:
        return False, "no-files"

    # 각 파일 타입에 대해 요구 에이전트 계산
    required_agents: set[str] = set()
    for f in files:
        ftype = file_types.get(f, _infer_type(f))  # fallback: 경로 기반 추론
        required_agents.update(_REQUIRED_AGENTS_BY_TYPE.get(ftype, []))

    if not required_agents:
        return False, "no-reviewable-files"

    reviews = state.get("reviews") or {}
    updated_at = float(state.get("updated_at") or 0.0)

    # 요구 에이전트 전부 존재 확인
    for agent in required_agents:
        if agent not in reviews:
            return True, f"missing-agent-{agent}"

    # stale 체크 (기존 동일)
    min_completed = min(
        float(reviews[a].get("completed_at") or 0)
        for a in required_agents
    )
    if updated_at > min_completed:
        return True, "stale-review"

    # files_snapshot 기반 커버리지 체크 (v2 High 2 대응 — 단, 실효성은 L1 참조)
    # 규약: record_review_done 호출자(hook_runner._post_agent_record)는 agent가 실제로
    # 검토한 파일 집합을 files_snapshot 파라미터로 명시 전달해야 한다.
    # files_snapshot=None이면 review_gate.py:194가 state["files"] 전체를 자동 채움 —
    # 이 경우 커버리지 체크는 통과하지만 실제 리뷰 여부는 미보장 (v2.1 후속 강화 대상).
    for agent in required_agents:
        snap = set(reviews[agent].get("files_snapshot") or [])
        for f in files:
            ftype = file_types.get(f, _infer_type(f))
            if agent in _REQUIRED_AGENTS_BY_TYPE.get(ftype, []) and f not in snap:
                return True, f"coverage-gap:{agent}:{f}"

    # verdict 체크 — required_agents로 범위 제한 (v2 High 3 대응)
    # 이전 실행의 stale BLOCK 레코드가 현재 commit을 오탐 차단하는 문제 해소
    if not os.environ.get("AF_GATE_ALLOW_VERDICT_BLOCK"):
        for agent in required_agents:
            if reviews[agent].get("verdict") in ("block", "fail"):
                return True, f"verdict-block:{agent}"

    return False, "all-agents-passed"


def _infer_type(path: str) -> str:
    """파일 경로에서 타입 추론 (file_types 누락 시 fallback).

    path는 workspace 상대 경로 규약 (enqueue 시점에 정규화).
    """
    # 혹시 절대 경로가 들어온 경우 workspace-relative로 변환
    # basename 단순화는 docs/features/ 등 서브디렉토리 분류를 파괴하므로 사용 금지.
    norm = path
    if os.path.isabs(norm):
        # enqueue_agent_review._normalize_workspace_path와 동일 로직 재사용
        from scripts.enqueue_agent_review import _normalize_workspace_path
        norm = _normalize_workspace_path(norm)

    if norm.endswith(".py"):
        return "code"
    if not norm.endswith(".md"):
        return "other"

    # 제외 경로 (work-items, code-review, patterns, 루트 메타문서)
    if "/work-items/" in norm:
        return "other"
    if norm.endswith("/code-review.md"):
        return "other"
    if norm.startswith("docs/patterns/"):
        return "other"
    if not norm.startswith("docs/"):
        # 루트 .md (README, CLAUDE 등)
        return "other"

    # docs/ 직하 또는 features/reviews/plans/standards 서브
    return "design"
```

---

## 3. 수정 파일 목록

### 3.1 `scripts/enqueue_agent_review.py`

**현재 로직** (`scripts/enqueue_agent_review.py:26-37` `_is_review_target`):
```python
# 현재: .py + core/ prefix 또는 model_utils.py/run_factory_cli.py 정확 일치 allowlist
```

**변경:** `.md` 설계문서도 enqueue + `file_types` 맵 업데이트. 기존 `.py` allowlist 유지.

```python
# scripts/enqueue_agent_review.py 확장

def _classify(path: str) -> str:
    """return "code" | "design" | "ignore".

    - code: 기존 _is_review_target 통과 .py 파일
    - design: _infer_type()이 design 반환하는 .md 파일
    - ignore: 그 외
    """
    # 경로 정규화 (workspace 상대 경로로)
    norm = _normalize_workspace_path(path)

    if norm.endswith(".py"):
        return "code" if _is_review_target(norm) else "ignore"
    if norm.endswith(".md"):
        from scripts.review_gate import _infer_type
        t = _infer_type(norm)
        return "design" if t == "design" else "ignore"
    return "ignore"


def _normalize_workspace_path(path: str) -> str:
    """절대 경로면 workspace 기준 상대 경로로 변환. workspace 외부면 basename fallback."""
    if not os.path.isabs(path):
        return path
    ws = os.path.abspath(_detect_workspace())
    abs_path = os.path.abspath(path)
    if abs_path.startswith(ws + os.sep):
        return os.path.relpath(abs_path, ws).replace(os.sep, "/")
    return os.path.basename(path)


def enqueue_file(workspace: str, file_path: str) -> None:
    ftype = _classify(file_path)
    if ftype == "ignore":
        return
    norm = _normalize_workspace_path(file_path)
    # files 리스트에 norm 추가 + file_types[norm] = ftype 저장 (atomic write)
```

**규약 (v2 High 4 대응):** 큐에 저장되는 파일 경로는 **항상 workspace 상대 경로** (예: `docs/2026-04-21-foo.md`, `core/foo.py`). 절대 경로는 `_normalize_workspace_path`가 변환. 이 규약은 `_infer_type` fallback과도 일치.

### 3.2 `scripts/hook_runner.py`

**현재:** `_post_edit_enqueue`가 `.py`만 처리. `_AGENT_TIER_MAP`은 tier 번호 매핑.
**변경:**
- 설계문서 `.md`도 enqueue 대상 (`_classify` 경유)
- `_AGENT_TIER_MAP` 유지 (기존 tier 번호는 정보성 필드로 보존). **af-doc-qa는 추가하지 않음** (v2 결정: work-item 전용)

```python
# 기존 유지 + design 에이전트는 tier 번호 없이 tracked만
_AGENT_TIER_MAP: dict[str, int] = {
    "af-test-runner": 1,   # code tier 1
    "af-critic": 2,        # code tier 2, design 공통
    "af-cross-review": 3,  # code tier 3, design 공통
}
# design은 tier 번호 매핑 없이 _REQUIRED_AGENTS_BY_TYPE["design"]로 게이트 결정

def _post_edit_enqueue(payload):
    fp = _extract_file_path(payload)
    if not fp:
        return 0
    # .py 또는 .md 허용 (설계문서 + 코드 양쪽)
    if not (fp.endswith(".py") or fp.endswith(".md")):
        return 0
    # 이후 기존 subprocess 호출 유지 (enqueue_agent_review.py가 분류 처리)
    ...

def _post_agent_record(payload):
    subagent_type = (payload.get("tool_input") or {}).get("subagent_type", "")
    if subagent_type not in _AGENT_TIER_MAP:
        return 0
    tier = _AGENT_TIER_MAP[subagent_type]
    # tier는 정보성 유지 (기존 로그 형식 호환)
    record_review_done(workspace, subagent_type, tier=tier, verdict=verdict)
```

### 3.3 `scripts/review_gate.py`

**변경:**
- `_REQUIRED_AGENTS_BY_TYPE` 상수 추가 (§2.2)
- `_infer_type(path)` 함수 추가 (§2.3)
- `is_gate_blocked` 로직을 §2.3로 교체 (required_agents 동적 계산 + files_snapshot 커버리지 + verdict 범위 제한)
- `record_review_done` 시그니처: **`tier: int = 0` optional화로 확정** (제거 금지 — hook_runner 호출부 파손). 기존 호출자는 tier를 명시적으로 전달, 미전달 시 0 fallback
- 상태에 `file_types: dict[str, str]` 맵 저장 (enqueue 시점에 업데이트)
- 신규 파일 추가 체크(기존 line 160-164)는 code 전용 스냅샷(`af-cross-review`)에 의존하므로 그대로 유지. design 파일은 `files_snapshot` 커버리지 체크로 이미 보호됨

### 3.4 `.githooks/pre-commit`

**변경 불필요.** `review_gate.py --check`만 호출하므로 내부 로직이 확장되어도 그대로 동작.

### 3.5 `scripts/pre_commit_review.py`

**검토 필요.** 현재 `.py` 타겟만 처리. `.md`가 섞인 commit에서 예기치 않은 동작이 있는지 확인.

### 3.6 `clear_committed_files` — 확장자 무관 동작 확인

현재 구현(`scripts/review_gate.py:207-230`)은 `committed_set = set(committed_files)` 후 `files` 리스트에서 이 집합 기반 필터링 — **확장자 무관**. `.md`가 `files`에 추가되어도 commit 후 정상 정리됨. **별도 변경 불필요**, 다만 D5 통합 테스트에 "design commit 후 queue 정리 확인" 케이스 추가 필요.

---

## 4. 데이터 스키마 마이그레이션

**문제:** 기존 `pending_agent_review.json`에는 `file_types` 필드 없음. 배포 시점 기존 큐가 존재하면 `_infer_type` fallback 경로로 동작.

**전략:**
- `file_types` 누락 파일은 `_infer_type(path)`로 추론 (확장자 기반)
- `reviews[agent]`의 기존 `tier` 필드는 유지 (정보 가치 있음)
- 신규 필드 `reviews[agent]["for_types"]`: 이 리뷰가 어떤 파일 타입을 커버하는지 (선택적, 현재 판정에는 사용 안 함)

**Sonnet 구현 시 확인:** 기존 `.af_review_queue/pending_agent_review.json` fixture로 단위 테스트 추가 (downgrade 방어).

---

## 5. 엣지 케이스 & 불변식

### 5.1 불변식

- **I1.** `docs/work-items/**`, `docs/code_review/code-review.md`는 design 분류 외 → 게이트 통과
- **I2.** `Master_Blueprint.md`는 기존 Blueprint 스테이징 체크로 처리, design 분류 아님
- **I3.** 한 commit에 `.py` + `.md`(design) 혼합 시 `code ∪ design = {af-test-runner, af-critic, af-cross-review}` **3개** 필요 (v2: af-doc-qa는 제외됨)
- **I4.** ~~af-critic 공유 불변식~~ (v2 제거 — L1 한계로 재분류). 다만 **`files_snapshot` 기반 커버리지 체크**가 최소 보호를 제공: 혼합 commit(`.py` + `.md`) 시 af-critic이 실행될 때 `files_snapshot`에 해당 파일이 포함되지 않으면 `coverage-gap` BLOCK
- **I5.** stale 체크는 "요구 에이전트의 최소 completed_at" 기준. 기존 로직 그대로
- **I6.** BLOCK/FAIL verdict 차단 범위는 **required_agents로 제한** (v2 High 3 대응) — 이전 실행의 stale BLOCK 레코드가 현재 commit 오탐 차단하지 않음
- **I7.** 환경변수 `AF_SKIP_REVIEW_GATE=1`은 모든 타입에 적용 (기존 동작)
- **I8. (v2 신설)** 큐에 저장되는 파일 경로는 **workspace 상대 경로**로 정규화. `_normalize_workspace_path`가 보장

### 5.3 알려진 한계 (v2)

- **L1. af-critic 공유 취약점 + files_snapshot 자동 fill 문제** — `record_review_done`이 `files_snapshot=None`으로 호출되면 `review_gate.py:194`가 큐의 모든 파일을 자동으로 snapshot에 포함시킨다(`snapshot = list(state.get("files") or [])`). 이 경우 커버리지 체크(§2.3)는 항상 통과하므로 "af-critic이 실제로 해당 파일을 검토했는지"는 강제되지 않는다. v2.1에서 해결 방안:
  1. `_post_agent_record` hook이 agent 응답에서 "검토한 파일 목록"을 파싱하여 명시적 `files_snapshot` 전달
  2. 또는 agent prompt에 "응답 메타데이터에 리뷰 대상 파일 명시" 규약 도입
  현재 v2는 **"각 리뷰어의 prompt에 대상 파일을 명시적으로 전달하는 운영 관례"** 로 완화. hook-based 강제는 v2.1.

### 5.2 엣지 케이스

- **E1.** CLAUDE.md / README.md 편집 → `_classify`에서 `ignore` → 큐에 안 들어감 → 통과
- **E2.** `docs/2026-04-21-foo.md` 신규 작성 후 af-doc-qa만 돌리고 commit 시도 → `missing-agent-af-critic` BLOCK
- **E3.** af-cross-review 실행 후 `docs/2026-04-21-foo.md` 재편집 → `stale-review` BLOCK
- **E4.** 기존 `.py` commit 플로우에 영향 없음 (code 파일은 기존 에이전트 요구 그대로)

---

## 6. 구현 순서 (Sonnet Handoff)

### D0. 테스트 fixture
- [ ] `tests/test_review_gate.py`에 design 시나리오 fixture 추가:
  - `test_design_doc_requires_two_agents` — af-critic + af-cross-review 누락 상태 BLOCK (v2: 3개 → 2개)
  - `test_design_doc_all_agents_pass` — 2개 완료 시 PASS
  - `test_mixed_code_and_design_commit` — `.py` + `.md` 혼합 시 3개 에이전트 필요 (code 3 ∪ design 2, af-critic/af-cross-review 공유)
  - `test_design_doc_stale_after_edit` — 리뷰 후 재편집 시 BLOCK
  - `test_infer_type_edge_cases` — work-items, code-review.md, patterns, 루트 .md 제외 검증
  - `test_infer_type_subdirs` — `docs/features/`, `docs/reviews/`, `docs/plans/`, `docs/standards/` 하위 .md가 design 분류 확인
  - `test_legacy_queue_without_file_types` — 기존 큐 호환성 (`_infer_type` fallback)
  - `test_absolute_path_normalization` — 절대 경로 큐 항목이 workspace 상대로 정규화되는지
  - `test_files_snapshot_coverage_check` — af-critic이 `.py`만 snapshot에 포함하고 `.md` 누락 시 `coverage-gap` BLOCK (v2 High 2 대응)
  - `test_verdict_scope_limited_to_required` — 이전 실행의 `af-doc-qa` BLOCK verdict가 현재 commit을 오탐 차단하지 않는지 (v2 High 3)
  - `test_clear_committed_md_files` — design commit 성공 후 `clear_committed_files`가 `.md`를 queue에서 제거하는지

### D1. `scripts/review_gate.py`
- [ ] `_REQUIRED_AGENTS_BY_TYPE`, `_infer_type` 추가
- [ ] `is_gate_blocked` 로직 교체
- [ ] `record_review_done`에서 tier 파라미터 optional화 (하위 호환)
- [ ] 상태 파일에 `file_types` 맵 기록

### D2. `scripts/enqueue_agent_review.py`
- [ ] `.md` 설계문서 분류 로직 추가
- [ ] enqueue 시 `file_types` 동시 기록

### D3. `scripts/hook_runner.py`
- [ ] `_post_edit_enqueue`가 `.md`도 처리 (`.py` 또는 `.md` 허용)
- [ ] `_post_agent_record`의 `_AGENT_TIER_MAP`은 **기존 3개(af-test-runner, af-critic, af-cross-review) 유지** — af-doc-qa는 v2에서 design gate 대상 아니므로 tracking 불필요
- [ ] (v2.1 선택) agent 응답에서 명시적 `files_snapshot` 추출 → `record_review_done`에 전달

### D4. `.claude/settings.local.json` (검토만)
- [ ] PostToolUse hook이 af-critic, af-cross-review를 trigger하도록 이미 설정돼 있는지 확인. af-doc-qa는 v2에서 design gate 대상 외이므로 별도 설정 **불필요**

### D5. 통합 테스트
- [ ] 실제 design doc 생성 → af-doc-qa만 실행 → `git commit` 시도 → BLOCK 확인
- [ ] 3개 모두 실행 → commit 성공 확인

### D6. Blueprint
- [ ] §9 설정 레퍼런스 또는 신규 섹션에 design doc review-gate 추가
- [ ] §12 이력: `2026-04-21 | feat(review-gate): 설계문서 .md 교차검증 강제`

---

## 7. 위험 & 완화

### 7.1 False Positive (과도 차단)

- **위험:** `README.md`, 사소한 패치 문서가 실수로 design 분류되어 3-agent 요구
- **완화:** `_classify`의 예외 경로 엄격히 검증 (루트 `.md`, work-items/, code-review.md 모두 제외)
- **완화 2:** `AF_SKIP_REVIEW_GATE=1` 우회 유지

### 7.2 False Negative (우회 가능)

- **위험:** `docs/` 외부에 설계문서 작성 시 우회
- **완화:** CLAUDE.md에 "설계문서는 반드시 `docs/` 하위에 작성" 규칙 추가 (문서 파일명 규칙에 포함)

### 7.3 레거시 큐 호환성

- **위험:** 기존 `.af_review_queue/pending_agent_review.json`이 `file_types` 없이 존재 → 업그레이드 직후 판정 오류
- **완화:** `_infer_type` fallback + 테스트 fixture (D0 `test_legacy_queue_without_file_types`)

### 7.4 af-critic 공유 이슈

- **위험:** 같은 commit에 code + design 혼재 시, af-critic이 둘 다 리뷰했는지 검증 안 함. 한 쪽만 리뷰해도 공유 카운트로 통과 가능
- **완화 (v1):** 운영 관례로 "af-critic 호출 시 code+design 모두 언급" 문서화. 자동 검증은 v2에서 `files_snapshot` 기반으로 강화
- **완화 (v2 후속):** 각 에이전트 리뷰가 어떤 파일을 대상으로 했는지 `for_files` 필드에 저장, 판정 시 "이 파일을 커버한 리뷰 존재 여부" 체크

---

## 8. 롤백

config 한 줄 토글:
- `AF_DESIGN_GATE_DISABLED=1` 환경변수 추가 → `is_gate_blocked`에서 design 검사만 비활성화 (code 게이트는 유지)
- 또는 pre-commit hook에서 `AF_SKIP_REVIEW_GATE=1`로 전체 우회 (기존 동작)

---

## 8.5 v2 재검증 권장

이 문서(v2)가 구현되기 전에, v1→v2 변경사항(특히 단일 에이전트 수 축소 2개 + files_snapshot 커버리지 체크)에 대해 af-critic + af-cross-review 2-agent 병렬 재검증 수행 권고. v2 확정 후 D0~D6 진행.

---

## 9. 참조

- `.githooks/pre-commit:27-42` — review-gate fast-path
- `scripts/review_gate.py:121-172` — `is_gate_blocked`
- `scripts/review_gate.py:175-205` — `record_review_done`
- `scripts/hook_runner.py:252-342` — review-gate builtins
- `scripts/hook_runner.py:132-148` — `_post_edit_enqueue`
- `scripts/enqueue_agent_review.py` — 큐 추가 로직
- CLAUDE.md:31-34 — 교차검증 자동 실행 규칙 (2026-04-21 강화됨)
- `docs/2026-04-19-review-gate-enforcement.md` — 기존 `.py` 게이트 설계 (참조)
