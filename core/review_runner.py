"""
core/review_runner.py
======================
교차검증 리뷰 실행 유틸리티 — core/ 레이어에서 안전하게 import 가능.

scripts/design_review_watcher.py와 core/review_report.py 양쪽에서 사용.
frozen build(af.exe)에서도 동작한다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ── 상수 ──────────────────────────────────────────────────────────────────────

PROMPTS_DIR = os.path.join("scripts", "prompts")
REVIEW_TIMEOUT = 600
JUDGE_PRIORITY = ["claude", "codex", "gemini"]

CLI_COMMANDS = {
    "claude": "claude",
    "codex": "codex",
    "gemini": "gemini",
}

_AUTONOMOUS_PROVIDERS = {"codex", "gemini"}


# ── 프로바이더 탐지 ──────────────────────────────────────────────────────────

def detect_providers() -> list[str]:
    """AVAILABLE 상태 provider만 반환. 반환 순서는 CLI_COMMANDS 순서(claude→codex→gemini) 보존."""
    try:
        from core.provider_detect import detect_provider_states, ProviderState
        states = detect_provider_states()
        id_to_key = {"claude_cli": "claude", "codex_cli": "codex", "gemini_cli": "gemini"}
        avail = {id_to_key[pid] for pid, r in states.items()
                 if r.state == ProviderState.AVAILABLE and pid in id_to_key}
        return [k for k in ("claude", "codex", "gemini") if k in avail]
    except Exception:
        # provider_detect 사용 불가 시 기존 shutil.which fallback
        available = []
        for name, cmd in CLI_COMMANDS.items():
            if shutil.which(cmd):
                available.append(name)
        return available


def detect_blocked_providers() -> list[str]:
    """AUTH_EXPIRED 상태 provider 목록 반환 — DocumentReviewSession BLOCK 메시지용."""
    try:
        from core.provider_detect import detect_provider_states, ProviderState
        states = detect_provider_states()
        id_to_key = {"claude_cli": "claude", "codex_cli": "codex", "gemini_cli": "gemini"}
        blocked = {id_to_key[pid] for pid, r in states.items()
                   if r.state == ProviderState.AUTH_EXPIRED and pid in id_to_key}
        return [k for k in ("claude", "codex", "gemini") if k in blocked]
    except Exception:
        return []


def select_review_pair(providers: list[str]) -> tuple[str, str]:
    """critic과 cross에 서로 다른 프로바이더 배정."""
    if len(providers) >= 2:
        return providers[0], providers[1]
    return providers[0], providers[0]


def select_judge(providers: list[str]) -> str:
    """취합 판정자 선택. claude > codex > gemini 우선순위."""
    for p in JUDGE_PRIORITY:
        if p in providers:
            return p
    return providers[0]


# ── 프롬프트 로드 ────────────────────────────────────────────────────────────

def _load_prompt(workspace: str, name: str) -> str:
    """scripts/prompts/<name>.txt 로드."""
    path = os.path.join(workspace, PROMPTS_DIR, f"{name}.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── CLI 실행 ─────────────────────────────────────────────────────────────────

def _resolve_cli(name: str) -> str:
    resolved = shutil.which(name)
    return resolved if resolved else name


def _build_exec_command(provider: str) -> list[str]:
    if provider == "codex":
        return [_resolve_cli("codex"), "exec", "-s", "danger-full-access"]
    elif provider == "claude":
        return [_resolve_cli("claude"), "-p", "--output-format", "text"]
    elif provider == "gemini":
        return [_resolve_cli("gemini"), "-p"]
    else:
        return [_resolve_cli("codex"), "exec", "-s", "danger-full-access"]


def _run_provider(provider: str, prompt: str, workspace: str) -> str:
    """프로바이더 CLI 실행. 프롬프트는 stdin으로 전달."""
    cmd = _build_exec_command(provider)
    try:
        result = subprocess.run(
            cmd,
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=REVIEW_TIMEOUT,
            cwd=workspace,
        )
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        if not stdout and stderr:
            return f"(provider error: {stderr[:500]})"
        return stdout or "(empty response)"
    except subprocess.TimeoutExpired:
        return f"(timeout: {REVIEW_TIMEOUT}s)"
    except FileNotFoundError:
        return f"(provider not found: {provider})"
    except Exception as e:
        return f"(execution error: {e})"


def _build_review_prompt(
    template: str,
    provider: str,
    doc_content: str,
    context: str,
    rel_path: str,
    context_path: str,
) -> str:
    """프로바이더 특성에 맞는 프롬프트 구성."""
    if provider in _AUTONOMOUS_PROVIDERS:
        return (
            f"{template}\n\n---\n\n"
            f"## 지시사항\n\n"
            f"1. 먼저 `{context_path}` 파일을 읽어 프로젝트 컨텍스트를 파악하라.\n"
            f"2. 그 다음 `{rel_path}` 파일을 읽고 리뷰하라.\n"
            f"3. 변경 파일의 호출자/피호출자도 직접 찾아서 읽어라.\n"
        )
    return (
        f"{template}\n\n---\n\n"
        f"## Project Context\n\n{context}\n\n---\n\n"
        f"## Document to Review\n\n{doc_content}"
    )


# ── 리뷰 실행 (raw string 반환) ──────────────────────────────────────────────

def run_critic(
    provider: str, doc_content: str, context: str, workspace: str,
    *, rel_path: str = "", context_path: str = "",
    prompt_name: str = "design_critic",
) -> str:
    """critic 리뷰 실행. raw string 반환."""
    template = _load_prompt(workspace, prompt_name)
    prompt = _build_review_prompt(template, provider, doc_content, context, rel_path, context_path)
    return _run_provider(provider, prompt, workspace)


def run_cross(
    provider: str, doc_content: str, context: str, workspace: str,
    *, rel_path: str = "", context_path: str = "",
    prompt_name: str = "design_cross_review",
) -> str:
    """cross 리뷰 실행. raw string 반환."""
    template = _load_prompt(workspace, prompt_name)
    prompt = _build_review_prompt(template, provider, doc_content, context, rel_path, context_path)
    return _run_provider(provider, prompt, workspace)


def run_aggregation(
    judge: str,
    critic_result: str,
    cross_result: str,
    doc_content: str,
    workspace: str,
    prompt_name: str = "design_aggregation",
) -> str:
    """취합 판정 실행. raw string 반환."""
    template = _load_prompt(workspace, prompt_name)
    prompt = (
        f"{template}\n\n---\n\n"
        f"## Critic Review\n\n{critic_result}\n\n---\n\n"
        f"## Cross Review\n\n{cross_result}\n\n---\n\n"
        f"## Original Document (for reference)\n\n{doc_content[:10000]}"
    )
    return _run_provider(judge, prompt, workspace)


# ── ReviewerResult 래퍼 (core/review_report.py에서 사용) ─────────────────────

def _parse_verdict(raw: str) -> str:
    """LLM 출력에서 verdict 파싱. BLOCK > WARN > PASS 우선순위."""
    upper = raw.upper()
    if "BLOCK" in upper:
        return "BLOCK"
    if "PASS" in upper and "WARN" not in upper:
        return "PASS"
    return "WARN"


def run_critic_review(
    provider: str, doc_content: str, context: str = "",
    prompt_file: str = "design_critic",
    workspace: str = "",
):
    """DocumentReviewSession에서 호출하는 critic 래퍼. ReviewerResult 반환."""
    from core.review_report import ReviewerResult

    t0 = time.time()
    raw = run_critic(provider, doc_content, context, workspace or ".", prompt_name=prompt_file)
    return ReviewerResult(
        provider=provider, role="critic", raw_output=raw,
        findings_count=raw.count("[") // 2,
        verdict=_parse_verdict(raw),
        elapsed_seconds=time.time() - t0,
    )


def run_cross_review(
    provider: str, doc_content: str, context: str = "",
    prompt_file: str = "design_cross_review",
    workspace: str = "",
):
    """DocumentReviewSession에서 호출하는 cross 래퍼. ReviewerResult 반환."""
    from core.review_report import ReviewerResult

    t0 = time.time()
    raw = run_cross(provider, doc_content, context, workspace or ".", prompt_name=prompt_file)
    return ReviewerResult(
        provider=provider, role="cross", raw_output=raw,
        findings_count=raw.count("ACCEPT"),
        elapsed_seconds=time.time() - t0,
    )
