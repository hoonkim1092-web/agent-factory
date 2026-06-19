#!/usr/bin/env python3
"""scripts/check_staged_design_review.py

커밋 직전, staged 설계문서에 대해 docs/reviews/ 의 최신 자동 리뷰 verdict 를 확인한다.
최신 리뷰가 BLOCK 이면 exit 1 로 커밋을 차단하고 해당 리뷰 파일 경로를 출력한다.

배경 — surface 단절 해소 (2026-06-18):
  자동 설계리뷰 watcher(scripts/design_review_watcher.py)는 리뷰 결과를
  docs/reviews/*.md 에 산출하지만, 그 결과를 작업자에게 노출하던 채널
  (UserPromptSubmit hook 의 check_design_pending.py)이 제거되면서 끊겼다.
  그 탓에 watcher 가 Critical BLOCK 판정한 설계문서가 안 보인 채 그대로
  커밋된 사례(d1022ecd)가 있었다. 이 스크립트는 그 surface 를 git-native
  pre-commit(프로바이더 무관·사람입력 무관) 에 복원한다.

프로바이더 무관: pre-commit 에서 호출되므로 Claude/Codex/IDE/shell 어디서
  커밋하든 발화한다. CLAUDE.md 등 특정 프로바이더 지침에 의존하지 않는다.
우회: AF_SKIP_REVIEW_GATE=1 git commit ...  (pre-commit 이 호출 전 분기).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

# docs/reviews/{ts}-{stem}-design-review.md  (ts = YYYY-MM-DD-HHMMSS, 정렬 가능)
_DESIGN_REVIEW_SUFFIX = "-design-review.md"
_REVIEWS_REL = os.path.join("docs", "reviews")

# 헤더 `> Source: <rel>` / 본문 `### Verdict: <VERDICT>` 파싱 (watcher _write_result 포맷).
# 볼드체 `### Verdict: **BLOCK**` 도 흡수 — 실측 19개 리뷰가 emphasis markdown 사용(누락 시
# silent false-negative → d1022ecd 재현). `\*{0,2}` 가 선행 `**` 를 건너뛴다.
_SOURCE_RE = re.compile(r"^>\s*Source:\s*(.+?)\s*$", re.MULTILINE)
_VERDICT_RE = re.compile(r"^#+\s*Verdict:\s*\*{0,2}([A-Za-z_]+)", re.MULTILINE)

_BLOCK = "BLOCK"
_BLOCK_SECTION_RE = re.compile(r"§\d+(?:\.\d+)*")


def _extract_block_sections(text: str) -> list[str]:
    """BLOCK 리뷰 텍스트에서 §섹션 ID 목록을 순서 보존·중복 제거하여 반환."""
    return list(dict.fromkeys(_BLOCK_SECTION_RE.findall(text)))


def _map_doc_to_queue_fname(workspace: str, doc_norm: str) -> "str | None":
    """정규화된 문서 rel 경로 → 큐 JSON 파일명 (없으면 None)."""
    import json as _json
    queue_dir = os.path.join(workspace, ".af_review_queue", "pending", "design")
    if not os.path.isdir(queue_dir):
        return None
    ws_prefix = workspace.replace("\\", "/").rstrip("/") + "/"
    try:
        for fname in os.listdir(queue_dir):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(queue_dir, fname), encoding="utf-8") as f:
                    data = _json.load(f)
                if not isinstance(data, dict):
                    continue
                fp = str(data.get("file_path", "") or "").replace("\\", "/")
                if fp.startswith(ws_prefix):
                    fp = fp[len(ws_prefix):]
                if fp == doc_norm:
                    return fname
            except Exception:
                continue
    except OSError:
        pass
    return None


def _record_verdicts_to_fired_marker(
    workspace: str, blocked: "list[tuple[str, str]]"
) -> None:
    """BLOCK verdict + §섹션을 fired marker에 기록하고 oscillation_detected를 갱신한다.

    pre-commit 게이트가 호출 — 실패해도 커밋을 막지 않는다.
    check_design_pending.py 헬퍼를 동적 로드해 SSOT 재사용.
    """
    try:
        import importlib.util
        cdp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_design_pending.py")
        spec = importlib.util.spec_from_file_location("check_design_pending", cdp_path)
        if spec is None or spec.loader is None:
            return
        cdp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cdp)  # type: ignore[union-attr]
    except Exception as _e:
        print(f"[check-staged-design-review] verdict 기록 스킵(로드 실패, 커밋 비차단): {_e}", file=sys.stderr)
        return

    try:
        fired = cdp._load_fired(workspace)
        dirty = False
        for doc_norm, review_rel in blocked:
            fname = _map_doc_to_queue_fname(workspace, doc_norm)
            if fname is None:
                continue
            review_path = os.path.join(workspace, review_rel)
            try:
                with open(review_path, encoding="utf-8", errors="replace") as f:
                    review_text = f.read()
            except OSError:
                review_text = ""
            new_sections = _extract_block_sections(review_text)
            entry = cdp._normalize_entry(fired.get(fname, 0))
            prev_sections = entry["last_block_sections"]
            if entry["last_verdict"] == _BLOCK and set(prev_sections) & set(new_sections):
                entry["oscillation_detected"] = True
            entry["last_verdict"] = _BLOCK
            entry["last_block_sections"] = new_sections
            fired[fname] = entry
            dirty = True
        if dirty:
            cdp._save_fired(workspace, fired)
    except Exception:
        pass


def _reset_verdict_in_fired_marker(workspace: str, doc_norms: "list[str]") -> None:
    """PASS/WARN verdict 산출 시 fired marker의 last_verdict를 초기화한다.

    이전 라운드가 BLOCK이었어도 PASS가 나온 뒤 새 BLOCK이 오면 oscillation이 아니다.
    last_verdict 초기화로 false-positive 방지 (S2 fix).
    """
    if not doc_norms:
        return
    try:
        import importlib.util
        cdp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_design_pending.py")
        spec = importlib.util.spec_from_file_location("check_design_pending", cdp_path)
        if spec is None or spec.loader is None:
            return
        cdp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cdp)  # type: ignore[union-attr]
    except Exception as _e:
        print(f"[check-staged-design-review] verdict 초기화 스킵(로드 실패): {_e}", file=sys.stderr)
        return

    try:
        fired = cdp._load_fired(workspace)
        dirty = False
        for doc_norm in doc_norms:
            fname = _map_doc_to_queue_fname(workspace, doc_norm)
            if fname is None:
                continue
            entry = cdp._normalize_entry(fired.get(fname, 0))
            entry["last_verdict"] = ""
            entry["oscillation_detected"] = False
            fired[fname] = entry
            dirty = True
        if dirty:
            cdp._save_fired(workspace, fired)
    except Exception:
        pass


def _repo_root() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return os.getcwd()


def _staged_files(workspace: str) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True, text=True, timeout=10, cwd=workspace,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return [ln.strip().replace("\\", "/") for ln in r.stdout.splitlines() if ln.strip()]


def load_latest_design_verdicts(workspace: str) -> dict[str, tuple[str, str]]:
    """source(정규화 rel) → (verdict, review_rel_path) 의 최신 설계리뷰 맵.

    '최신' = 파일명 ts prefix 가 가장 큰 리뷰. 같은 source 에 새 PASS/WARN 리뷰가
    나중에 산출되면 그것이 최신이 되어 이전 BLOCK 을 덮는다(false-block 방지).
    """
    reviews_dir = os.path.join(workspace, _REVIEWS_REL)
    if not os.path.isdir(reviews_dir):
        return {}

    # source → (review_filename, verdict)  — filename 으로 최신성 비교.
    latest: dict[str, tuple[str, str]] = {}
    for name in sorted(os.listdir(reviews_dir)):
        if not name.endswith(_DESIGN_REVIEW_SUFFIX):
            continue
        try:
            with open(os.path.join(reviews_dir, name), "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        m_src = _SOURCE_RE.search(text)
        m_ver = _VERDICT_RE.search(text)
        if not m_src or not m_ver:
            continue
        source = m_src.group(1).replace("\\", "/")
        verdict = m_ver.group(1).upper()
        prev = latest.get(source)
        if prev is None or name > prev[0]:
            latest[source] = (name, verdict)

    return {
        src: (verdict, os.path.join(_REVIEWS_REL, fname).replace("\\", "/"))
        for src, (fname, verdict) in latest.items()
    }


def find_blocked(workspace: str, staged: list[str]) -> list[tuple[str, str]]:
    """staged 설계문서 중 최신 리뷰가 BLOCK 인 것 → (문서 rel, 리뷰 rel) 목록."""
    # SSOT: is_design_doc / normalize_path 는 core.design_review_utils 재사용.
    if workspace not in sys.path:
        sys.path.insert(0, workspace)
    from core.design_review_utils import is_design_doc, normalize_path

    verdicts = load_latest_design_verdicts(workspace)
    blocked: list[tuple[str, str]] = []
    for rel in staged:
        abspath = os.path.join(workspace, rel)
        if not is_design_doc(abspath, workspace):
            continue
        norm = normalize_path(abspath, workspace)
        info = verdicts.get(norm)
        if info and info[0] == _BLOCK:
            blocked.append((norm, info[1]))
    return blocked


def find_unreviewed(workspace: str, staged: list[str]) -> list[str]:
    """staged 설계문서 중 최신 리뷰 자체가 없는 것 → 문서 norm 목록.

    verdict 가 있지만 BLOCK/PASS/WARN 인 것은 포함하지 않는다.
    리뷰가 전혀 없을 때만 fail-closed 분기 대상이 된다.
    """
    if workspace not in sys.path:
        sys.path.insert(0, workspace)
    from core.design_review_utils import is_design_doc, normalize_path

    verdicts = load_latest_design_verdicts(workspace)
    unreviewed: list[str] = []
    for rel in staged:
        abspath = os.path.join(workspace, rel)
        if not is_design_doc(abspath, workspace):
            continue
        norm = normalize_path(abspath, workspace)
        if norm not in verdicts:
            unreviewed.append(norm)
    return unreviewed


def _external_provider_status(workspace: str) -> str:
    """외부 프로바이더(non-claude_cli) 가용 상태를 반환한다.

    Returns:
        "skip"         — 전부 NOT_INSTALLED | RATE_LIMITED (커밋 허용, 노티만)
        "auth_expired" — 하나 이상 AUTH_EXPIRED (BLOCK + 재인증 안내)
        "available"    — 가용 프로바이더 있음 (verdict 부재 = watcher 미실행 → BLOCK)

    예외 발생 시 "skip" 반환 — 게이트 오작동으로 정상 커밋을 막지 않는다.
    provider_detect SSOT 재사용: _all_external_providers_unavailable 와 동일한
    NOT_INSTALLED | RATE_LIMITED skip 기준, AUTH_EXPIRED는 skip 제외.
    """
    try:
        if workspace not in sys.path:
            sys.path.insert(0, workspace)
        from core.provider_detect import (  # type: ignore
            detect_provider_states, ProviderState, CLI_PROVIDER_IDS,
        )
        ext_ids = [p for p in CLI_PROVIDER_IDS if p != "claude_cli"]
        if not ext_ids:
            return "skip"
        states = detect_provider_states(providers=ext_ids, use_cache=True)
        results = list(states.values())
        # AVAILABLE 우선: 하나라도 가용이면 watcher 가 리뷰를 산출할 수 있었다 → "available".
        # AUTH_EXPIRED 는 모든 외부 프로바이더가 unavailable 일 때만 의미있다.
        if any(r.state == ProviderState.AVAILABLE for r in results):
            return "available"
        if any(r.state == ProviderState.AUTH_EXPIRED for r in results):
            return "auth_expired"
        return "skip"
    except Exception:
        return "skip"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="staged 설계문서의 최신 자동 리뷰 verdict 확인 (BLOCK → 커밋 차단)."
    )
    parser.add_argument("--workspace", "-w", default=None)
    args = parser.parse_args(argv)
    workspace = args.workspace or _repo_root()

    staged = _staged_files(workspace)
    try:
        blocked = find_blocked(workspace, staged)
        unreviewed = find_unreviewed(workspace, staged)
    except Exception as exc:
        # 게이트 자체 오작동으로 정상 커밋을 막지 않는다 (surface 는 보조 안전망).
        # 단, 오작동을 silent 로 묻지 않고 stderr 로 가시화한다(import/파싱 버그 조기 발견).
        print(f"[check-staged-design-review] 게이트 비활성(예외, 커밋 비차단): {exc}", file=sys.stderr)
        return 0

    if not blocked and not unreviewed:
        return 0

    exit_code = 0

    if blocked:
        exit_code = 1
        print("")
        print("🛑 [pre-commit] 설계리뷰 BLOCK 미해결 — 자동 리뷰가 차단 판정한 설계문서가 staged 상태입니다:")
        for doc, review in blocked:
            print(f"   • {doc}")
            print(f"     ↳ 리뷰: {review}")
        print("")
        print("   조치:")
        print("     - 리뷰 BLOCK findings 반영 후 재커밋 (watcher 새 리뷰가 최신 PASS/WARN 이면 BLOCK 을 덮음)")
        print("     - 즉시 재검토: python scripts/design_review_watcher.py . --sync <문서경로>")
        print("     - 우회: AF_SKIP_REVIEW_GATE=1 git commit ...")
        print("")

    if unreviewed:
        status = _external_provider_status(workspace)
        if status == "skip":
            # 프로바이더 미설치/rate-limited → 커밋 허용, 노티만
            print("")
            print("ℹ️  [pre-commit] 설계리뷰 없음 — 외부 프로바이더 미설치/rate-limited, 스킵합니다:")
            for doc in unreviewed:
                print(f"   • {doc}")
            print("")
        elif status == "auth_expired":
            exit_code = 1
            print("")
            print("🛑 [pre-commit] 설계리뷰 없음 — 프로바이더 인증 만료, 재인증 후 watcher 재실행:")
            for doc in unreviewed:
                print(f"   • {doc}")
            print("")
            print("   조치: codex/gemini 재인증 후 python scripts/design_review_watcher.py . --sync <문서경로>")
            print("   우회: AF_SKIP_REVIEW_GATE=1 git commit ...")
            print("")
        else:  # "available" — watcher 미실행/죽음
            exit_code = 1
            print("")
            print("🛑 [pre-commit] 설계리뷰 없음 — 프로바이더 가용하나 리뷰 미산출 (watcher 미실행 의심):")
            for doc in unreviewed:
                print(f"   • {doc}")
            print("")
            print("   조치:")
            print("     - 수동 실행: python scripts/design_review_watcher.py . --sync <문서경로>")
            print("     - 우회: AF_SKIP_REVIEW_GATE=1 git commit ...")
            print("")

    # verdict fired marker 기록 — oscillation_detected 갱신 (S2)
    # try/except 래핑: 기록 실패가 커밋을 막지 않도록
    try:
        if blocked:
            _record_verdicts_to_fired_marker(workspace, blocked)
        # PASS/WARN 문서: last_verdict 초기화 → PASS 이후 새 BLOCK이 oscillation으로 오판되는 것 방지
        verdicts_map = load_latest_design_verdicts(workspace)
        blocked_norms = {d for d, _ in blocked}
        unreviewed_set = set(unreviewed)
        pass_docs = [
            doc_norm
            for doc_norm, (verdict, _) in verdicts_map.items()
            if doc_norm not in blocked_norms
            and doc_norm not in unreviewed_set
            and verdict != _BLOCK
        ]
        if pass_docs:
            _reset_verdict_in_fired_marker(workspace, pass_docs)
    except Exception:
        pass

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
