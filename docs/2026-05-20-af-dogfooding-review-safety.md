# AF Dogfooding Review Safety Layer

Date: 2026-05-20

## Purpose

AF가 AF 자신을 개발하려면, 자기 수정 코드가 검토 없이 커밋되는 경로를 막아야 한다.
이번 변경은 사소한 Python cosmetic 변경은 빠르게 통과시키되, 보안/정책/실행/배포 주변 변경은 강한 리뷰를 유지하는 1차 dogfooding 안전장치다.

## What Changed

### 1. Deterministic T3 classifier

Added `scripts/t3_classifier.py`.

It decides whether Tier 3 can be skipped using deterministic checks:

- hard-guard paths always require Tier 3
- changed added/deleted diff lines are scanned for risk tokens
- Python files are compared with AST after removing docstrings
- only comment/formatting/docstring-only AST-equivalent changes become T3 skip candidates

Why:

LLM review is useful for context, but it is not deterministic enough to own a skip decision alone. The deterministic classifier gives a stable baseline.

### 2. Hard guard expansion

Updated `scripts/blast_radius.py` so review-policy files are themselves Tier 3:

- `scripts/enqueue_agent_review.py`
- `scripts/check_pending_review.py`
- `scripts/t3_classifier.py`
- `scripts/t3_skip_report.py`

Why:

The files that decide review routing must not be able to skip the strongest review path.

### 3. Review queue integration

Updated `scripts/enqueue_agent_review.py`.

The pending review queue now stores:

- `t3_required`
- `t3_decision`
- classifier version
- skip reason
- diff summary
- file list

If the classifier fails or the file set changes between classification and queue write, enqueue fails closed and keeps Tier 3 required.

Why:

The queue is the handoff point between hooks and the gate. It must preserve enough evidence to explain a skip decision later.

### 4. Gate-level fail-closed validation

Updated `scripts/review_gate.py`.

Tier 3 is skipped only when all of these are true:

- `blast_tier == 2`
- deterministic classifier says `skip_t3`
- reason is `cosmetic-only-python-ast`
- classifier version matches
- classifier file list exactly matches queue file list
- af-critic records `t3_required: no`

If af-critic says `yes` or `unknown`, or does not provide the field after it has run, Tier 3 remains required.

Why:

The gate is the final enforcement point. It must not trust a stale or malformed skip flag.

### 5. af-critic advisory

Updated:

- `scripts/prompts/code_critic.txt`
- `scripts/hook_runner.py`
- `scripts/review_gate.py`

af-critic is now asked to emit:

```text
t3_required: yes / no / unknown
```

This is advisory, not authoritative. It can only confirm a deterministic skip candidate with `no`.

Why:

This adds context-aware judgment on top of deterministic classification without giving the LLM unilateral skip authority.

### 6. User guidance alignment

Updated `scripts/check_pending_review.py`.

The pending-review message now follows the same required-tier calculation as `review_gate.py`. If the gate would require Tier 3, the prompt tells the user to run af-cross-review.

Why:

The user-facing instruction and the commit gate must not disagree.

### 7. Skip telemetry report

Added `scripts/t3_skip_report.py`.

It summarizes `.af_review_queue/t3_skip_telemetry.jsonl` by:

- skip reason
- classifier version
- top files

Why:

If a skipped case later turns out to be unsafe, we need to know which rule allowed it.

## Policy Summary

The effective policy is:

```text
if hard_guard_path_or_tier3_content:
    require T3
elif deterministic_classifier != cosmetic_only:
    require T3
elif af_critic_t3_required == "no":
    skip T3
else:
    require T3
```

Annotation-only changes are intentionally not treated as cosmetic because Python annotations are runtime-observable through `__annotations__` and framework/schema integrations.

Before af-critic runs, a deterministic skip candidate only reduces the immediate required set to Tier 1 + Tier 2. After af-critic runs, `yes` or `unknown` escalates back to Tier 3.

## Verification

Focused verification commands:

```bash
python -m py_compile scripts/blast_radius.py scripts/t3_classifier.py scripts/t3_skip_report.py scripts/enqueue_agent_review.py scripts/review_gate.py scripts/check_pending_review.py scripts/hook_runner.py
python -m pytest tests/test_t3_classifier.py tests/test_t3_skip_report.py tests/test_review_gate.py tests/test_pending_review.py tests/test_hook_runner_builtins.py -q
python scripts/test_gap_analyzer.py --workspace .
```

Additional review was run with separate QA and code-review subagents. Earlier findings caused hard guard, staged diff, gate fail-closed, guidance alignment, and risk token fixes.

## Follow-up: Project YAML Control Characters

The five `projects/agent_factory/...` YAML files were not meaningful config changes. Their committed baseline contained literal carriage-return control characters at line ends, so cleaning them produced a whole-file-looking diff with identical YAML values.

Root cause:

- `.gitattributes` already pins YAML/Markdown/Python/JSON to LF, but repeated `\r` characters can survive as file content, not as normal CRLF line endings.
- `projects/*/runs/`, `dashboard.json`, `skill-lock.yaml`, and `resume_brief.md` are already ignored, but a small baseline set under `projects/agent_factory/` is tracked and can expose old committed line-ending pollution.
- Prior review history shows repeated `projects/agent_factory` line-ending churn, so this is a repository hygiene issue rather than a new semantic change.

Mitigation added:

- `core/text_integrity.py` now flags `repeated_carriage_return` and `bare_carriage_return` as suspicious text markers while allowing normal CRLF.
- `tests/test_text_integrity.py` covers normal CRLF, repeated trailing CR, and changed-file detection against a clean baseline.
- The cleaned YAML files remain as an intentional control-character cleanup.

## Remaining Work

- Run the full AF self-edit loop several times: edit AF code → enqueue → review agents → gate → commit.
- Aggregate skip telemetry over time and review suspicious repeat files.
- Decide whether T2 advisory should also be displayed in `review_metrics_report.py`.
