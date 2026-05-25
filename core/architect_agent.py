"""Architect Agent: Triad 合(Synthesis) — resolve Critic findings against Blueprint+ADR context.

§17 Step 19 — Architect mediator for the 正反合 Triad pipeline.

Role:
  合 (Architect) receives the initial plan (正) and Critic findings (反), then makes
  ACCEPT / REJECT / HOLD decisions grounded in Master_Blueprint.md sections and
  accepted ADR documents.  No LLM call — decisions are rule-based and deterministic,
  derived from authoritative architecture references.

Decision rules:
  REJECT  — Blueprint section or accepted ADR explicitly contradicts the finding
             (the existing architecture already handles the concern).
  ACCEPT  — Finding is valid; required_fix is appended to final_plan unresolved_risks
             so the implementer acts on it.
  (HOLD decisions can be injected by callers via custom architect_fn replacements;
   this implementation produces only ACCEPT / REJECT.)

Install as Triad architect executor:

    import core.architect_agent as architect_mod
    import core.triad as triad_mod
    triad_mod._architect_executor = architect_mod.architect_fn
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Tuple

from core.triad import TriadCriticFinding, TriadCriticReport, TriadDecision

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_BLUEPRINT_PATH = _REPO_ROOT / "Master_Blueprint.md"
_ADR_DIR = _REPO_ROOT / "docs" / "decisions"

# ---------------------------------------------------------------------------
# Blueprint loader
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^#{1,3}\s+(§\d+[\w.]*.*?)$", re.MULTILINE)
_STOP_WORDS = frozenset({"with", "that", "from", "this", "have", "will", "step", "plan", "core"})


def _load_blueprint_text(blueprint_path: Path | None = None) -> str:
    path = blueprint_path or _BLUEPRINT_PATH
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _extract_section(text: str, section_ref: str) -> str:
    """Return the text block for the first heading matching section_ref (e.g. '§3').

    Returns empty string when not found.
    """
    # (?![\d.]) prevents §3 from matching §3.1 headings (prefix false match)
    pattern = re.compile(
        r"(^#{1,3}\s+" + re.escape(section_ref) + r"(?![\d.]).*?$)(.*?)(?=^#{1,3}\s+§|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return ""
    return (m.group(1) + m.group(2)).strip()


def _section_for_step(affected_step: str, blueprint_text: str) -> Tuple[str, str]:
    """Map an affected_plan_step or evidence snippet to a Blueprint section.

    Returns (section_ref, section_text).  Falls back to ('', '') when no
    match is found.
    """
    # Direct §N reference in the step string
    m = re.search(r"(§\d+[\w.]*)", affected_step)
    if m:
        ref = m.group(1)
        text = _extract_section(blueprint_text, ref)
        if text:
            return ref, text

    # Heuristic: look for step keywords in blueprint section headings
    keywords = [w for w in re.findall(r"[A-Za-z]{4,}", affected_step) if w.lower() not in _STOP_WORDS]
    for heading_m in _SECTION_RE.finditer(blueprint_text):
        heading = heading_m.group(1)
        if any(kw.lower() in heading.lower() for kw in keywords):
            ref_m = re.search(r"(§\d+[\w.]*)", heading)
            ref = ref_m.group(1) if ref_m else heading[:20]
            text = _extract_section(blueprint_text, ref) if ref_m else heading
            return ref, text

    return "", ""


# ---------------------------------------------------------------------------
# ADR loader
# ---------------------------------------------------------------------------

def _load_accepted_adrs(adr_dir: Path | None = None) -> list[dict[str, str]]:
    """Return list of {filename, title, body} for ADRs with Status: Accepted."""
    directory = adr_dir or _ADR_DIR
    results: list[dict[str, str]] = []
    if not directory.is_dir():
        return results
    for path in sorted(directory.glob("ADR-*.md")):
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Only include Accepted ADRs
        status_m = re.search(r"^Status:\s*(\w+)", body, re.MULTILINE | re.IGNORECASE)
        if not status_m or status_m.group(1).lower() != "accepted":
            continue
        title_m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else path.stem
        results.append({"filename": path.name, "title": title, "body": body})
    return results


def _adr_matches(adr: dict[str, str], finding: TriadCriticFinding) -> bool:
    """Return True when an ADR body references the same concern as the finding."""
    keywords = re.findall(r"[A-Za-z]{4,}", finding.title + " " + finding.evidence)
    body_lower = adr["body"].lower()
    # Use set to deduplicate repeated keywords — only count distinct matches
    hits = len({kw.lower() for kw in keywords if kw.lower() in body_lower and kw.lower() not in _STOP_WORDS})
    return hits >= 2


# ---------------------------------------------------------------------------
# Finding resolution
# ---------------------------------------------------------------------------

def _resolve_finding(
    finding: TriadCriticFinding,
    blueprint_text: str,
    accepted_adrs: list[dict[str, str]],
) -> TriadDecision:
    """Produce a TriadDecision for a single finding.

    Priority:
    1. If evidence_type == 'blueprint' and the Blueprint section explicitly
       contradicts the concern → REJECT (architecture already handles it).
    2. If an accepted ADR addresses the concern → REJECT with adr_ref.
    3. Otherwise ACCEPT — finding is valid; required_fix surfaces to implementer.
    """
    blueprint_ref, blueprint_excerpt = _section_for_step(
        finding.affected_plan_step + " " + finding.evidence,
        blueprint_text,
    )

    # Check for ADR match
    matched_adr: dict[str, str] | None = None
    for adr in accepted_adrs:
        if _adr_matches(adr, finding):
            matched_adr = adr
            break

    # REJECT: Critic cited Blueprint as evidence AND we found the matching section.
    # Intentionally requires evidence_type == 'blueprint' so that only findings the
    # Critic itself grounded in the Blueprint are refuted by the Blueprint.
    # file_line / test_gap findings with a coincidentally related section are not
    # auto-rejected — they go through ADR matching or surface as ACCEPT.
    if blueprint_ref and finding.evidence_type == "blueprint":
        return TriadDecision(
            finding_title=finding.title,
            verdict="REJECT",
            reason=(
                f"Blueprint {blueprint_ref} already addresses this concern. "
                f"Existing architecture: {blueprint_excerpt[:200].strip()!r}"
            ),
            blueprint_section=blueprint_ref,
            adr_ref=matched_adr["filename"] if matched_adr else "",
        )

    # REJECT: accepted ADR overrides the finding
    if matched_adr:
        return TriadDecision(
            finding_title=finding.title,
            verdict="REJECT",
            reason=(
                f"Accepted ADR '{matched_adr['title']}' ({matched_adr['filename']}) "
                f"already captures this decision. No plan change required."
            ),
            blueprint_section=blueprint_ref,
            adr_ref=matched_adr["filename"],
        )

    # ACCEPT: valid finding — surface required_fix so the implementer acts on it
    return TriadDecision(
        finding_title=finding.title,
        verdict="ACCEPT",
        reason=(
            f"Finding is valid (severity={finding.severity}). "
            f"Required fix: {finding.required_fix}"
        ),
        blueprint_section=blueprint_ref,
        adr_ref="",
    )


# ---------------------------------------------------------------------------
# Final-plan patching
# ---------------------------------------------------------------------------

def _patch_final_plan(
    plan_dict: dict[str, Any],
    findings: list[TriadCriticFinding],
    decisions: list[TriadDecision],
) -> dict[str, Any]:
    """Return a copy of plan_dict with ACCEPT-ed required_fixes appended to
    unresolved_risks so implementers see them.

    REJECT-ed findings are omitted (architecture handles them).
    HOLD-ed findings are noted as needing human review.
    """
    import copy
    final = copy.deepcopy(plan_dict)
    unresolved: list[str] = list(final.get("unresolved_risks", []))

    decision_map = {d.finding_title: d for d in decisions}
    for f in findings:
        d = decision_map.get(f.title)
        if d is None:
            continue
        if d.verdict == "ACCEPT":
            entry = f"[ACCEPT/{f.severity}] {f.title}: {f.required_fix}"
            if entry not in unresolved:
                unresolved.append(entry)
        elif d.verdict == "HOLD":
            entry = f"[HOLD/{f.severity}] {f.title} — needs human review"
            if entry not in unresolved:
                unresolved.append(entry)
        # REJECT: architect explicitly overrides — no action needed in plan

    final["unresolved_risks"] = unresolved
    return final


# ---------------------------------------------------------------------------
# Public executor
# ---------------------------------------------------------------------------

def architect_fn(
    plan_dict: dict[str, Any],
    critic_report: TriadCriticReport,
    context: dict[str, Any],
    *,
    _blueprint_path: Path | None = None,
    _adr_dir: Path | None = None,
) -> Tuple[dict[str, Any], list[TriadDecision]]:
    """Triad 合 executor — resolve Critic findings and produce a final plan.

    Parameters
    ----------
    plan_dict:
        Initial plan from the Planner (正).
    critic_report:
        Findings from the Critic (反).
    context:
        Run context (workspace, spec, premortem).
    _blueprint_path, _adr_dir:
        Override paths for testing.

    Returns
    -------
    (final_plan_dict, decisions)
    """
    blueprint_text = _load_blueprint_text(_blueprint_path)
    accepted_adrs = _load_accepted_adrs(_adr_dir)

    decisions: list[TriadDecision] = []
    for finding in critic_report.findings:
        decision = _resolve_finding(finding, blueprint_text, accepted_adrs)
        decisions.append(decision)

    final_plan = _patch_final_plan(plan_dict, critic_report.findings, decisions)
    return final_plan, decisions
