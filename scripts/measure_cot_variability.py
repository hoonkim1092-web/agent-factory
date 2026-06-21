"""
CoT 프롬프트 변동성 측정 스크립트.

검증 목표 (NEXT_STEPS §▶▶ 잔여 검증 2건):
  1. task 종류 다양화 — 기존 단순/복잡 외 3종 추가
  2. 멀티프로바이더 — codex 군집 위치 측정 (gemini는 인증 필요 시 SKIP)

실행:
  python scripts/measure_cot_variability.py
  python scripts/measure_cot_variability.py --provider codex_cli
  python scripts/measure_cot_variability.py --runs 5   (빠른 측정)

출력: 각 task × provider 조합의 confidence 통계 + routing 결과
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from typing import Callable

# 프로젝트 루트를 sys.path에 추가
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import core.right_sized_router as _router

# ---------------------------------------------------------------------------
# CoT 프롬프트 (monkeypatch 대상)
# ---------------------------------------------------------------------------

def _build_empty_scope_prompt_cot(task: str) -> str:
    """CoT 버전 — 규칙 단계별 추론 후 JSON."""
    stage_list = ", ".join(_router.STAGE_VOCAB)
    light_list = ", ".join(sorted(_router.LIGHT_STAGES))
    return f"""You are a task-complexity classifier for the Agent Factory codebase.

## Task
{task}

## Intended scope files
(미확정) — the task did not specify explicit file paths. Infer complexity from the task description alone.

## Step-by-step reasoning (follow these steps before outputting JSON)

Step 1 — Leaf check:
  Is this a PURE LEAF implementation? Criteria: adds/changes a single function with NO API
  or contract changes, affects at most 1–2 files, no design decisions needed.
  Answer: YES or NO

Step 2 — Stage necessity:
  Which stages are GENUINELY needed?
  - research: only if external knowledge or API discovery is needed
  - design: only if architecture or interface decisions must be made first
  - plan: almost always needed before implementation
  - implement: needed if any code changes
  - test: needed if any code changes
  - review: needed if Tier-2+ files or non-trivial logic
  - cross_review: needed if Tier-3 files or cross-cutting concerns

Step 3 — Scope uncertainty:
  Without explicit file paths, how certain are you?
  If the task description is vague or covers multiple systems, confidence MUST be < 0.5.

Step 4 — Decision:
  Based on steps 1–3, assign confidence (0.0–1.0).
  A pure-leaf task with clear scope → confidence ≥ 0.80.
  Ambiguous or multi-system task → confidence < 0.60.

## Output (JSON only — no text before or after the JSON block)
```json
{{
  "isolation": <one of {list(_router.ISOLATION_LEVELS)}>,
  "required_stages": [<subset of [{stage_list}] in execution order>],
  "review_depth": <"none" | "standard" | "deep">,
  "confidence": <float 0.0–1.0>,
  "reason": "<1-2 sentences summarizing your step-by-step conclusion>"
}}
```

## Additional rules
- Pure leaf (YES in Step 1): required_stages = [{light_list}] only.
- Multi-system or design-heavy: include design/review/cross_review as needed.
"""


def _build_empty_scope_prompt_original(task: str) -> str:
    """원본 프롬프트 (비교용 — 실제 함수 복사)."""
    stage_list = ", ".join(_router.STAGE_VOCAB)
    light_list = ", ".join(sorted(_router.LIGHT_STAGES))
    return f"""You are a task-complexity classifier for the Agent Factory codebase.

## Task
{task}

## Intended scope files
(미확정) — the task did not specify explicit file paths. Infer complexity from the task description alone.

## Output (JSON only, no explanation outside JSON)
Return a JSON object with exactly these keys:
  isolation       : one of {list(_router.ISOLATION_LEVELS)}
  required_stages : subset of [{stage_list}] in execution order
  review_depth    : one of ["none", "standard", "deep"]
  confidence      : float 0.0–1.0 (your certainty)
  reason          : brief explanation (1–2 sentences)

## Rules
- Pure leaf implementation (add a single function, no API/contract changes):
    required_stages should be [{light_list}] only.
- If design, review, or cross-review is genuinely needed, include them.
- If the scope is unclear or the task involves multiple files/systems, set confidence < 0.5.
- Tier hint is unavailable — rely on task semantics only.
"""


# ---------------------------------------------------------------------------
# 측정 task 목록
# ---------------------------------------------------------------------------

TASKS = {
    "simple_readme": "README.md에 설치 방법 섹션을 추가한다.",
    "simple_leaf_fn": "core/utils.py에 두 리스트의 공통 원소를 반환하는 순수 함수 `common_elements(a, b)`를 추가한다.",
    "medium_2files": (
        "core/right_sized_router.py의 `_LIGHT_CONFIDENCE_THRESHOLD`를 0.7에서 0.75로 올리고 "
        "tests/test_right_sized_router.py의 관련 assert를 동기화한다."
    ),
    "large_refactor": (
        "core/bootstrap_roles.py의 `plan()` 함수를 리팩토링하여 역할 분해 강도(standard/minimal)를 "
        "`required_stages` 신호에서 자동 유도하고, 모든 호출자에 배선 확인 및 회귀 테스트를 업데이트한다."
    ),
    "complex_auth": (
        "AF CLI가 Gemini 인증 갱신이 필요할 때 사용자에게 명확한 안내 메시지를 표시하도록 "
        "core/providers/cli.py와 core/failure_classifier.py를 수정한다. "
        "Windows cp949, Linux UTF-8 양쪽에서 동작해야 한다."
    ),
}

# 기대 군집: "light" (simple_readme, simple_leaf_fn) vs "full" (나머지)
EXPECTED = {
    "simple_readme": "light",
    "simple_leaf_fn": "light",
    "medium_2files": "full",
    "large_refactor": "full",
    "complex_auth": "full",
}


# ---------------------------------------------------------------------------
# 단일 측정
# ---------------------------------------------------------------------------

def _run_once(task: str, workspace: str) -> tuple[float, list[str], bool]:
    """classify 1회 실행. (confidence, required_stages, is_light) 반환."""
    decision = _router.classify(task, workspace, changed_files=[])
    return decision.confidence, list(decision.required_stages), decision.is_light()


def _measure_task(
    name: str,
    task: str,
    prompt_fn: Callable[[str], str],
    workspace: str,
    n: int,
    provider: str | None,
) -> dict:
    """task × prompt × provider 조합 n회 측정 → 통계 dict."""
    # monkeypatch
    original = _router._build_empty_scope_prompt
    _router._build_empty_scope_prompt = prompt_fn  # type: ignore[attr-defined]

    # provider override
    orig_providers = None
    if provider:
        llm = _router._get_router_llm()
        orig_providers = list(llm._cli_providers)
        if provider in orig_providers:
            llm._cli_providers = [provider]
        else:
            print(f"  [SKIP] provider={provider} not available. 사용가능: {orig_providers}")
            _router._build_empty_scope_prompt = original
            return {"skip": True, "reason": f"{provider} not available"}

    results = []
    for i in range(n):
        try:
            conf, stages, is_lt = _run_once(task, workspace)
            results.append({"conf": conf, "stages": stages, "is_light": is_lt})
            mark = "L" if is_lt else "F"
            print(f"  [{i+1:2d}/{n}] conf={conf:.3f} {mark}  stages={stages}")
        except Exception as e:
            print(f"  [{i+1:2d}/{n}] ERROR: {e}")
            results.append({"conf": 0.0, "stages": [], "is_light": False, "error": str(e)})

    # 복원
    _router._build_empty_scope_prompt = original
    if orig_providers is not None:
        _router._get_router_llm()._cli_providers = orig_providers

    confs = [r["conf"] for r in results if "error" not in r]
    light_count = sum(1 for r in results if r.get("is_light"))
    heavy_stages_count = sum(
        1 for r in results if not r.get("is_light") and
        any(s in r.get("stages", []) for s in ["research", "design", "cross_review"])
    )

    stat = {
        "n": n,
        "confs": confs,
        "mean": statistics.mean(confs) if confs else 0.0,
        "stdev": statistics.stdev(confs) if len(confs) >= 2 else 0.0,
        "min": min(confs) if confs else 0.0,
        "max": max(confs) if confs else 0.0,
        "light_count": light_count,
        "full_count": n - light_count,
        "heavy_stages_contamination": heavy_stages_count,
    }
    return stat


# ---------------------------------------------------------------------------
# 비교 출력
# ---------------------------------------------------------------------------

def _print_comparison(name: str, expected: str, orig: dict, cot: dict) -> None:
    if orig.get("skip") or cot.get("skip"):
        print(f"  → SKIP")
        return

    def _fmt(s: dict) -> str:
        return (
            f"conf {s['mean']:.3f}±{s['stdev']:.3f} [{s['min']:.2f}~{s['max']:.2f}]"
            f"  light={s['light_count']}/{s['n']}"
            f"  contam={s['heavy_stages_contamination']}"
        )

    print(f"  expected={expected}")
    print(f"  ORIG: {_fmt(orig)}")
    print(f"  CoT : {_fmt(cot)}")

    # 판정
    if expected == "light":
        orig_ok = orig["light_count"] >= orig["n"] * 0.8
        cot_ok = cot["light_count"] >= cot["n"] * 0.8
        stdev_improved = cot["stdev"] < orig["stdev"]
        print(
            f"  → light-hit:orig={orig_ok} cot={cot_ok}  stdev 개선={stdev_improved}"
        )
    else:
        orig_full = orig["full_count"] >= orig["n"] * 0.8
        cot_full = cot["full_count"] >= cot["n"] * 0.8
        orig_clean = orig["heavy_stages_contamination"] == 0
        cot_clean = cot["heavy_stages_contamination"] == 0
        print(
            f"  → full-hit:orig={orig_full} cot={cot_full}  "
            f"contam-clean:orig={orig_clean} cot={cot_clean}"
        )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="CoT 프롬프트 변동성 측정")
    ap.add_argument("--runs", type=int, default=5, help="task당 반복 횟수 (기본 5)")
    ap.add_argument("--provider", default=None, help="강제 CLI 프로바이더 (예: codex_cli)")
    ap.add_argument(
        "--tasks",
        nargs="+",
        choices=list(TASKS.keys()),
        default=list(TASKS.keys()),
        help="측정할 task 목록 (기본: 전체)",
    )
    ap.add_argument("--cot-only", action="store_true", help="CoT만 측정 (원본 생략)")
    args = ap.parse_args()

    workspace = _ROOT
    n = args.runs
    provider = args.provider

    print("=" * 70)
    print(f"CoT 변동성 측정  runs={n}  provider={provider or 'auto'}")
    print("=" * 70)

    # 사전 확인: LLM 사용가능 여부
    llm = _router._get_router_llm()
    print(f"사용 가능 CLI providers: {llm._cli_providers}")
    if not llm._cli_providers:
        print("ERROR: CLI 프로바이더 없음. claude/codex/gemini 중 하나 필요.")
        sys.exit(1)

    all_results = {}

    for task_name in args.tasks:
        task = TASKS[task_name]
        expected = EXPECTED[task_name]
        print(f"\n{'─'*60}")
        print(f"[{task_name}]  expected={expected}")
        print(f"  task: {task[:80]}{'...' if len(task) > 80 else ''}")

        orig_stat = {}
        if not args.cot_only:
            print(f"  --- 원본 프롬프트 ({n}회) ---")
            orig_stat = _measure_task(task_name, task, _build_empty_scope_prompt_original, workspace, n, provider)

        print(f"  --- CoT 프롬프트 ({n}회) ---")
        cot_stat = _measure_task(task_name, task, _build_empty_scope_prompt_cot, workspace, n, provider)

        if not args.cot_only:
            print()
            _print_comparison(task_name, expected, orig_stat, cot_stat)

        all_results[task_name] = {"orig": orig_stat, "cot": cot_stat, "expected": expected}

    # 요약
    print(f"\n{'='*70}")
    print("요약")
    print(f"{'='*70}")
    for task_name, res in all_results.items():
        cot = res["cot"]
        exp = res["expected"]
        if cot.get("skip"):
            print(f"  {task_name}: SKIP")
            continue
        hit = cot["light_count"] if exp == "light" else cot["full_count"]
        print(
            f"  {task_name} ({exp}): CoT conf {cot['mean']:.3f}±{cot['stdev']:.3f}  "
            f"hit={hit}/{cot['n']}  contam={cot['heavy_stages_contamination']}"
        )

    print()
    print("결론 체크리스트:")
    print("  □ 단순 task: CoT conf 0.82+ AND stdev<0.05 AND light 8/10+")
    print("  □ 복잡/대형 task: CoT conf <0.60 AND full 8/10+ AND contam=0")
    print("  □ 군집 간격 ≥0.30 (단순 min - 복잡 max > 0)")


if __name__ == "__main__":
    main()
