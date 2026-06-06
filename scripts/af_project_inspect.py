"""af project inspect — Python 프로젝트 컨텍스트 팩 생성.

LLM/네트워크/랜덤 없음. deterministic.
doctor 결과 재사용 — 새 진단 로직 금지.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_AF_ROOT = Path(__file__).resolve().parent.parent
# af_doctor는 scripts/ 내 동위 모듈 — AF root가 sys.path에 있어야 import 가능
if str(_AF_ROOT) not in sys.path:
    sys.path.insert(0, str(_AF_ROOT))

# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def _git_info(root: Path) -> dict:
    def _run(cmd: list[str]) -> str | None:
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5, cwd=str(root)
            )
            return r.stdout.strip() if r.returncode == 0 else None
        except Exception:
            return None

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    dirty_out = _run(["git", "status", "--porcelain"])
    dirty_count = len([ln for ln in (dirty_out or "").splitlines() if ln.strip()])
    return {"is_repo": branch is not None, "branch": branch, "dirty_count": dirty_count}


# ---------------------------------------------------------------------------
# Project structure detection
# ---------------------------------------------------------------------------

def _detect_manifests(root: Path) -> list[str]:
    candidates = ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"]
    return [c for c in candidates if (root / c).exists()]


def _detect_test_indicators(root: Path) -> list[str]:
    found = []
    for name in ["tests", "test", "pytest.ini", "pyproject.toml"]:
        if (root / name).exists():
            found.append(name)
    return found


_MAIN_GUARDS = ('__name__ == "__main__"', "__name__ == '__main__'")


def _detect_entrypoint_candidates(root: Path) -> list[dict]:
    candidates: list[dict] = []

    if (root / "__main__.py").exists():
        candidates.append({
            "path": "__main__.py",
            "kind": "__main__.py",
            "confidence": "candidate",
            "evidence": "__main__.py 파일 존재",
        })

    ppt = root / "pyproject.toml"
    if ppt.exists():
        try:
            text = ppt.read_text(encoding="utf-8", errors="ignore")
            if "[project.scripts]" in text:
                candidates.append({
                    "path": "pyproject.toml",
                    "kind": "pyproject.scripts",
                    "confidence": "candidate",
                    "evidence": "[project.scripts] 섹션 감지",
                })
        except Exception:
            pass

    for py_file in sorted(root.glob("*.py")):
        if py_file.name == "__main__.py":
            continue  # 이미 위에서 별도 처리
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if any(guard in text for guard in _MAIN_GUARDS):
                candidates.append({
                    "path": py_file.name,
                    "kind": "__main__ guard",
                    "confidence": "candidate",
                    "evidence": 'if __name__ == "__main__"',
                })
        except Exception:
            pass

    return candidates


def _detect_docs(root: Path) -> dict:
    readme = next(
        (n for n in ["README.md", "README.rst", "README.txt", "README"] if (root / n).exists()),
        None,
    )
    docs_dir = next(
        (n for n in ["docs", "doc", "documentation"] if (root / n).is_dir()),
        None,
    )
    llm_wiki_dir = None
    for candidate in [root / "docs" / "generated" / "llm_wiki", root / "llm_wiki"]:
        if candidate.is_dir():
            llm_wiki_dir = str(candidate.relative_to(root))
            break
    return {"readme": readme, "docs_dir": docs_dir, "llm_wiki_dir": llm_wiki_dir}


# ---------------------------------------------------------------------------
# Risks
# ---------------------------------------------------------------------------

def _build_risks(
    doctor_checks: list[dict],
    git: dict,
    test_indicators: list[str],
    docs: dict,
) -> list[dict]:
    risks: list[dict] = []

    # git_dirty는 target의 git 섹션에서 직접 생성 — doctor cwd와 무관
    if git.get("dirty_count", 0) > 0:
        risks.append({
            "kind": "git_dirty",
            "severity": "warn",
            "message": f"uncommitted changes: {git['dirty_count']}개",
            "source": "project",
        })

    # doctor = AF 실행환경 진단 (provider/hook/pytest). git 관련 항목은 위에서 처리했으므로 제외
    for c in doctor_checks:
        if c["name"] in ("git_repo", "git_dirty"):
            continue  # target git 상태는 git 섹션에서 처리
        if c["status"] == "fail":
            risks.append({
                "kind": "doctor_fail",
                "severity": "fail",
                "message": f"{c['name']}: {c['detail']}",
                "source": "doctor",
            })
        elif c["status"] == "warn":
            risks.append({
                "kind": "doctor_warn",
                "severity": "warn",
                "message": f"{c['name']}: {c['detail']}",
                "source": "doctor",
            })

    if not test_indicators:
        risks.append({
            "kind": "no_tests",
            "severity": "warn",
            "message": "테스트 디렉터리/설정 미감지",
            "source": "project",
        })

    if not docs["readme"]:
        risks.append({
            "kind": "no_readme",
            "severity": "info",
            "message": "README 없음",
            "source": "project",
        })

    return risks


# ---------------------------------------------------------------------------
# File scale
# ---------------------------------------------------------------------------

_EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "dist", "build"}


def _count_py_files(root: Path) -> int:
    # os.walk(followlinks=False) — symlink 순환 루프 방지
    try:
        count = 0
        for dirpath, dirnames, filenames in os.walk(str(root), followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
            count += sum(1 for f in filenames if f.endswith(".py"))
        return count
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# Main inspector
# ---------------------------------------------------------------------------

def inspect_project(root: Path) -> dict:
    """컨텍스트 팩 생성. LLM/네트워크 없음.

    주의: doctor 섹션은 프로세스 cwd를 진단한다(af_doctor가 cwd 고정).
    root != cwd인 경우 git/python/docs 섹션은 root를, doctor 섹션은 cwd를 가리킨다.
    """
    root = root.resolve()

    # doctor 재사용 — 새 진단 로직 금지
    doctor_data: dict = {"checks": [], "ok_count": 0, "warn_count": 0, "fail_count": 0}
    try:
        from scripts.af_doctor import run_checks, format_json  # type: ignore[import]
        doctor_data = json.loads(format_json(run_checks(fast=True)))
    except Exception as exc:
        doctor_data["error"] = str(exc)

    git = _git_info(root)
    manifests = _detect_manifests(root)
    test_indicators = _detect_test_indicators(root)
    entrypoint_candidates = _detect_entrypoint_candidates(root)
    docs = _detect_docs(root)
    risks = _build_risks(doctor_data["checks"], git, test_indicators, docs)

    return {
        "schema_version": 1,
        "project": {"root": str(root), "name": root.name, "language": "python"},
        "git": git,
        "doctor": {
            "ok_count": doctor_data["ok_count"],
            "warn_count": doctor_data["warn_count"],
            "fail_count": doctor_data["fail_count"],
            "checks": doctor_data["checks"],
        },
        "python": {
            "manifests": manifests,
            "test_indicators": test_indicators,
            "entrypoint_candidates": entrypoint_candidates,
            "py_file_count": _count_py_files(root),
        },
        "docs": docs,
        "risks": risks,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

_STATUS_ICON = {"ok": "✓", "warn": "!", "fail": "✗"}
_RISK_ICON = {"fail": "✗", "warn": "!", "info": "i"}


def format_markdown(ctx: dict) -> str:
    p, g, doc, py = ctx["project"], ctx["git"], ctx["docs"], ctx["python"]
    risks, d = ctx["risks"], ctx["doctor"]
    fail_n = sum(1 for r in risks if r["severity"] == "fail")
    warn_n = sum(1 for r in risks if r["severity"] == "warn")

    lines: list[str] = [f"# AF Project Context — {p['name']}", ""]
    if fail_n:
        lines.append(f"> ✗ {fail_n} fail, {warn_n} warn — 작업 착수 전 확인 필요")
    elif warn_n:
        lines.append(f"> ! {warn_n} warn — 참고 후 착수 가능")
    else:
        lines.append("> ✓ 착수 가능 — 주요 위험 없음")

    lines += ["", "## Git"]
    if g["is_repo"]:
        lines += [f"- branch: `{g['branch']}`", f"- dirty: {g['dirty_count']}개"]
    else:
        lines.append("- git repo 아님")

    lines += ["", f"## af doctor  ({d['fail_count']} fail / {d['warn_count']} warn / {d['ok_count']} ok)"]
    for c in d["checks"]:
        lines.append(f"- [{_STATUS_ICON.get(c['status'], '?')}] {c['name']}: {c['detail']}")

    lines += [
        "", "## Python 프로젝트",
        f"- .py 파일: {py['py_file_count']}개",
        f"- manifest: {', '.join(py['manifests']) or '없음'}",
        f"- 테스트: {', '.join(py['test_indicators']) or '미감지'}",
    ]
    if py["entrypoint_candidates"]:
        lines.append("- 진입점 후보:")
        for ep in py["entrypoint_candidates"]:
            lines.append(f"  - `{ep['path']}` ({ep['kind']})")

    lines += [
        "", "## 문서",
        f"- README: {doc['readme'] or '없음'}",
        f"- docs 디렉터리: {doc['docs_dir'] or '없음'}",
        f"- LLM Wiki: {doc['llm_wiki_dir'] or '없음'}",
        "", "## 위험 신호",
    ]
    if risks:
        for r in risks:
            lines.append(f"- [{_RISK_ICON.get(r['severity'], '?')}] **{r['kind']}**: {r['message']}")
    else:
        lines.append("- 없음")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="af project inspect",
        description="Python 프로젝트 컨텍스트 팩 생성 (LLM/네트워크 없음)",
    )
    parser.add_argument("path", nargs="?", default=".", help="대상 경로 (기본: 현재 디렉터리)")
    parser.add_argument("--json", dest="json_out", action="store_true", help="JSON 출력")
    parser.add_argument(
        "--out", metavar="DIR", default=None,
        help="MD+JSON 파일 저장 디렉터리 (미지정 시 stdout)",
    )
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"[af project inspect] 경로 없음: {root}", file=sys.stderr)
        return 1

    ctx = inspect_project(root)

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        md_path = out_dir / "af_project_context.md"
        json_path = out_dir / "af_project_context.json"
        md_path.write_text(format_markdown(ctx), encoding="utf-8")
        json_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[af project inspect] 저장됨: {md_path}")
        print(f"[af project inspect] 저장됨: {json_path}")
    elif args.json_out:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(format_markdown(ctx))

    return 0


if __name__ == "__main__":
    sys.exit(main())
