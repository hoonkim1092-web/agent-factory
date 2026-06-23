"""Knowledge Library — 자가진화 지식 도서관 (STAGE 1+).

설계: docs/2026-06-23-knowledge-library-evolution-design.md
"""
from __future__ import annotations

from core.knowledge.note import (
    KnowledgeNote,
    NoteScope,
    NoteType,
    NoteVisibility,
    make_id,
    new_note,
)

__all__ = [
    "KnowledgeNote",
    "NoteScope",
    "NoteType",
    "NoteVisibility",
    "make_id",
    "new_note",
]
