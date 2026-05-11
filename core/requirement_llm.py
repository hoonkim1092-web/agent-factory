from __future__ import annotations

import concurrent.futures as _cf
import json
import os
import time
import urllib.request
from dataclasses import dataclass

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from core.providers.cli import CliChatRequest, execute_cli_chat
from core.providers.registry import (
    default_chat_model_for_provider,
    get_configured_engine_api_key,
    get_engine_api_key,
    get_requested_cli_providers,
)
from model_utils import (
    _pick_anthropic_model,
    _pick_openai_model,
    generate_content_with_self_heal,
    get_best_model,
    normalize_model_name,
)


_REQUIREMENT_SYSTEM_PROMPT = (
    "You are the internal requirement-stage analyzer. "
    "Return JSON only. Do not inspect files, call tools, or modify the workspace."
)

_DOCUMENT_SYSTEM_PROMPT = (
    "You are a technical document generator. "
    "Return well-structured markdown only. Do not return JSON. "
    "Do not inspect files, call tools, or modify the workspace."
)


@dataclass(frozen=True)
class RequirementCandidate:
    provider_id: str
    model: str
    transport: str


def _workspace_path(workspace: str | None = None) -> str:
    raw = str(workspace or os.getenv("AGENT_PROJECT_ROOT") or os.getcwd()).strip()
    return os.path.abspath(raw or os.getcwd())


def _effective_requirement_prompt(prompt: str) -> str:
    return f"{_REQUIREMENT_SYSTEM_PROMPT}\n\n{str(prompt or '').strip()}".strip()


def _extract_openai_text(response) -> str:
    text = str(getattr(response, "output_text", "") or "").strip()
    if text:
        return text
    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", "") != "message":
            continue
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", "") in {"output_text", "text"}:
                value = str(getattr(content, "text", "") or "").strip()
                if value:
                    parts.append(value)
    return "\n".join(parts).strip()


def _make_usage(prompt_t: int, completion_t: int) -> dict:
    return {"prompt": prompt_t, "completion": completion_t, "total": prompt_t + completion_t}


def _call_google_api(model: str, prompt: str, *, timeout_sec: int = 120, return_usage: bool = False):
    api_key = get_engine_api_key("google") or get_configured_engine_api_key("google")
    if not api_key:
        raise RuntimeError("missing_google_api_key")
    from google import genai

    client = genai.Client(api_key=api_key)
    executor = _cf.ThreadPoolExecutor(max_workers=1)
    fut = executor.submit(generate_content_with_self_heal, client, normalize_model_name(model), prompt)
    try:
        response = fut.result(timeout=float(timeout_sec))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    text = str(getattr(response, "text", "") or "").strip()
    if not return_usage:
        return text
    meta = getattr(response, "usage_metadata", None)
    usage: dict = {}
    if meta:
        prompt_t = getattr(meta, "prompt_token_count", 0) or 0
        completion_t = getattr(meta, "candidates_token_count", 0) or 0
        usage = _make_usage(prompt_t, completion_t)
    return text, usage


def _call_openai_api(model: str, prompt: str, *, timeout_sec: int = 120, return_usage: bool = False):
    api_key = get_engine_api_key("openai") or get_configured_engine_api_key("openai")
    if not api_key:
        raise RuntimeError("missing_openai_api_key")
    if OpenAI is None:
        raise RuntimeError("openai_package_unavailable")
    client = OpenAI(api_key=api_key)
    response = client.with_options(timeout=float(timeout_sec)).responses.create(model=model, input=prompt)
    text = _extract_openai_text(response)
    if not return_usage:
        return text
    raw = getattr(response, "usage", None)
    usage: dict = {}
    if raw:
        prompt_t = getattr(raw, "input_tokens", 0) or 0
        completion_t = getattr(raw, "output_tokens", 0) or 0
        usage = _make_usage(prompt_t, completion_t)
    return text, usage


def _call_anthropic_api(model: str, prompt: str, *, timeout_sec: int = 120, return_usage: bool = False):
    api_key = get_engine_api_key("anthropic") or get_configured_engine_api_key("anthropic")
    if not api_key:
        raise RuntimeError("missing_anthropic_api_key")
    payload = json.dumps(
        {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        data = json.loads(response.read().decode("utf-8"))
    parts = []
    for item in data.get("content", []) or []:
        if str(item.get("type", "")).strip() == "text":
            value = str(item.get("text", "") or "").strip()
            if value:
                parts.append(value)
    text = "\n".join(parts).strip()
    if not return_usage:
        return text
    raw = data.get("usage") or {}
    prompt_t = raw.get("input_tokens", 0) or 0
    completion_t = raw.get("output_tokens", 0) or 0
    usage = _make_usage(prompt_t, completion_t)
    return text, usage


def _cli_model_for_provider(provider_id: str, cli_providers: list[str]) -> str:
    forced = str(os.getenv("AGENT_CHAT_MODEL", "") or "").strip()
    if forced and len(cli_providers) == 1:
        return forced
    return default_chat_model_for_provider(provider_id)


def list_requirement_candidates() -> list[RequirementCandidate]:
    cli_providers = get_requested_cli_providers()
    candidates: list[RequirementCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    def add(provider_id: str, model: str, transport: str) -> None:
        normalized_model = str(model or "").strip()
        if not normalized_model:
            return
        key = (str(provider_id).strip(), normalized_model, str(transport).strip())
        if key in seen:
            return
        seen.add(key)
        candidates.append(
            RequirementCandidate(
                provider_id=str(provider_id).strip(),
                model=normalized_model,
                transport=str(transport).strip(),
            )
        )

    for provider_id in cli_providers:
        add(provider_id, _cli_model_for_provider(provider_id, cli_providers), "cli")

    if get_engine_api_key("anthropic") or get_configured_engine_api_key("anthropic"):
        add("anthropic_api", _pick_anthropic_model("sonnet") or "claude", "api")
    if get_engine_api_key("openai") or get_configured_engine_api_key("openai"):
        add("openai_api", _pick_openai_model(prefer_reasoning=False) or "gpt-5", "api")
    if get_engine_api_key("google") or get_configured_engine_api_key("google"):
        add("google_api", get_best_model(["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-pro"]), "api")

    return candidates


def pick_requirement_candidate() -> RequirementCandidate | None:
    candidates = list_requirement_candidates()
    return candidates[0] if candidates else None


def execute_document_prompt(
    prompt: str,
    *,
    workspace: str | None = None,
    run_id: str = "",
    timeout_sec: int = 120,
) -> dict:
    """Markdown 문서 생성 전용. execute_requirement_prompt()와 동일한 provider 순회,
    단 시스템 프롬프트만 다름 — JSON 계약과 분리."""
    target_workspace = _workspace_path(workspace)
    errors: list[str] = []

    for candidate in list_requirement_candidates():
        t_start = time.monotonic()
        try:
            if candidate.transport == "cli":
                result = execute_cli_chat(
                    CliChatRequest(
                        provider_id=candidate.provider_id,
                        model=candidate.model,
                        system_prompt=_DOCUMENT_SYSTEM_PROMPT,
                        task_input=prompt,
                        workspace=target_workspace,
                        run_id=run_id,
                        timeout_sec=timeout_sec,
                    )
                )
                text = str(result.get("text") or result.get("stdout") or "").strip()
                usage: dict = result.get("usage") or {}
                if not result.get("ok"):
                    raise RuntimeError(str(result.get("reason") or "cli_document_failed"))
            else:
                effective_prompt = f"{_DOCUMENT_SYSTEM_PROMPT}\n\n{str(prompt or '').strip()}".strip()
                if candidate.provider_id == "anthropic_api":
                    text, usage = _call_anthropic_api(candidate.model, effective_prompt, timeout_sec=timeout_sec, return_usage=True)
                elif candidate.provider_id == "openai_api":
                    text, usage = _call_openai_api(candidate.model, effective_prompt, timeout_sec=timeout_sec, return_usage=True)
                else:
                    text, usage = _call_google_api(candidate.model, effective_prompt, timeout_sec=timeout_sec, return_usage=True)
        except Exception as exc:
            errors.append(f"{candidate.provider_id}:{candidate.model}:{type(exc).__name__}:{exc}")
            continue

        elapsed = time.monotonic() - t_start

        if text:
            return {
                "ok": True,
                "provider_id": candidate.provider_id,
                "model": candidate.model,
                "text": text,
                "elapsed_sec": elapsed,
                "usage_tokens": usage,
                "errors": errors,
            }
        errors.append(f"{candidate.provider_id}:{candidate.model}:empty_response")

    return {
        "ok": False,
        "provider_id": "",
        "model": "",
        "text": "",
        "elapsed_sec": 0.0,
        "usage_tokens": {},
        "errors": errors,
    }


def execute_requirement_prompt(
    prompt: str,
    *,
    workspace: str | None = None,
    run_id: str = "",
    timeout_sec: int = 120,
) -> dict:
    target_workspace = _workspace_path(workspace)
    errors: list[str] = []

    for candidate in list_requirement_candidates():
        try:
            if candidate.transport == "cli":
                result = execute_cli_chat(
                    CliChatRequest(
                        provider_id=candidate.provider_id,
                        model=candidate.model,
                        system_prompt=_REQUIREMENT_SYSTEM_PROMPT,
                        task_input=prompt,
                        workspace=target_workspace,
                        run_id=run_id,
                        timeout_sec=timeout_sec,
                    )
                )
                text = str(result.get("text") or result.get("stdout") or "").strip()
                if not result.get("ok"):
                    raise RuntimeError(str(result.get("reason") or "cli_requirement_failed"))
            else:
                effective_prompt = _effective_requirement_prompt(prompt)
                if candidate.provider_id == "anthropic_api":
                    text = _call_anthropic_api(candidate.model, effective_prompt)
                elif candidate.provider_id == "openai_api":
                    text = _call_openai_api(candidate.model, effective_prompt)
                else:
                    text = _call_google_api(candidate.model, effective_prompt)
        except Exception as exc:
            errors.append(f"{candidate.provider_id}:{candidate.model}:{type(exc).__name__}:{exc}")
            continue

        if text:
            return {
                "ok": True,
                "provider_id": candidate.provider_id,
                "model": candidate.model,
                "text": text,
                "errors": errors,
            }
        errors.append(f"{candidate.provider_id}:{candidate.model}:empty_response")

    return {
        "ok": False,
        "provider_id": "",
        "model": "",
        "text": "",
        "errors": errors,
    }
