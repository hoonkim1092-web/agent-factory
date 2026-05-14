"""LightContextScanner — LLM 0회, 정적 분석으로 컨텍스트 스캔 (설계 §7.1).

existing_tests / relevant_files / affected_modules / risk_signals 산출.
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
from pathlib import Path

from core.control.stage_artifacts import ContextScanArtifact

_SCHEMA_VERSION = 1
_TEST_PATTERNS = ("test_*.py", "*_test.py")
_RISK_EXTENSIONS = {".sql", ".sh", ".ps1", ".yml", ".yaml", ".json", ".toml", ".cfg", ".ini"}
_RISK_KEYWORDS = ("delete", "drop", "remove", "wipe", "reset", "truncate", "force", "override")


class LightContextScanner:
    """work_dir 기준 정적 스캔 — 0 LLM calls."""

    def scan(
        self,
        work_dir: str,
        work_kind: str,
        blast_radius: str,
        schema_hash: str = "",
    ) -> ContextScanArtifact:
        root = Path(work_dir)
        relevant_files = self._find_relevant_files(root)
        affected_modules = self._infer_affected_modules(relevant_files, root)
        existing_tests = self._find_existing_tests(root, affected_modules)
        risk_signals = self._detect_risk_signals(relevant_files, root)

        return ContextScanArtifact(
            artifact_type="context_scan",
            schema_version=_SCHEMA_VERSION,
            schema_hash=schema_hash or _dir_hash(root),
            work_dir=str(work_dir),
            work_kind=work_kind,
            blast_radius=blast_radius,
            relevant_files=[str(p) for p in relevant_files],
            affected_modules=affected_modules,
            existing_tests=[str(p) for p in existing_tests],
            risk_signals=risk_signals,
        )

    # ------------------------------------------------------------------

    def _find_relevant_files(self, root: Path) -> list[Path]:
        """work_dir 하위 소스 파일 목록 (최대 200개)."""
        files: list[Path] = []
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            if any(part.startswith(".") for part in p.parts):
                continue
            if p.suffix in {".py", ".yaml", ".yml", ".json", ".toml", ".md"}:
                files.append(p.relative_to(root))
            if len(files) >= 200:
                break
        return files

    def _infer_affected_modules(self, files: list[Path], root: Path) -> list[str]:
        """Python 파일 기준 최상위 패키지 디렉토리 추출."""
        modules: set[str] = set()
        for p in files:
            if p.suffix == ".py":
                parts = p.parts
                if len(parts) > 1:
                    modules.add(parts[0])
        return sorted(modules)

    def _find_existing_tests(self, root: Path, affected_modules: list[str]) -> list[Path]:
        """tests/ 하위 또는 패키지 내 test 파일 중 affected_modules 매칭."""
        test_files: list[Path] = []
        search_roots = [root / "tests", root]
        for sr in search_roots:
            if not sr.exists():
                continue
            for p in sr.rglob("*.py"):
                name = p.name
                if any(fnmatch.fnmatch(name, pat) for pat in _TEST_PATTERNS):
                    rel = p.relative_to(root)
                    # affected_modules 연관 필터 (또는 tests/ 직속)
                    if not affected_modules or any(m in str(rel) for m in affected_modules):
                        if rel not in test_files:
                            test_files.append(rel)
        return sorted(test_files)[:100]

    def _detect_risk_signals(self, files: list[Path], root: Path) -> list[str]:
        """파일 확장자 및 이름 기반 위험 신호 감지."""
        signals: list[str] = []
        for p in files:
            if p.suffix in _RISK_EXTENSIONS:
                signals.append(f"sensitive_ext:{p}")
            name_lower = p.name.lower()
            for kw in _RISK_KEYWORDS:
                if kw in name_lower:
                    signals.append(f"risk_keyword:{kw}:{p}")
                    break
        return signals[:50]


def _dir_hash(root: Path) -> str:
    """디렉토리 내 파일 경로 목록 기반 간단 해시 (변경 감지용)."""
    paths = sorted(str(p) for p in root.rglob("*") if p.is_file())
    return hashlib.sha256("\n".join(paths).encode()).hexdigest()[:16]
