"""KnowledgeNote — 내구성 지식 노트의 단일 타입 (frontmatter 계약, SSOT).

설계: docs/2026-06-23-knowledge-library-evolution-design.md §5 STAGE1 / §12.4·12.6 / §13.1

이 모듈은 STAGE 1 산출물이다:
- KnowledgeNote 데이터클래스 (타입 SSOT — 이 파일에서만 선언, CLAUDE.md 규칙)
- to_md / from_md (frontmatter 직렬화, round-trip)
- new_note (작성 헬퍼 — author/source_machine/created_commit/created_at/id 자동 스탬프)

식별·접근은 *seam만* 둔다 (INV-K6): `visibility`/`scope`/`author` 는 데이터 필드일
뿐, 읽기/쓰기 제한 enforcement 코드는 이 모듈에 없다 (git/GitHub이 나중에 제공).

id 네임스페이스 (§12.4, 멀티작성자 무충돌):
    {type}/{source_machine}-{micro시각}-{rand}-{slug}.md
- micro시각: 마이크로초 해상도 + Windows 파일명 안전 (ISO ':' 금지,
  sync_claude_memory.py:70 _path_to_claude_key 치환 선례 따름)
- rand: 6자 무작위 suffix — 동일 마이크로초 충돌 시 자동 회피
두 작성자가 같은 파일을 만들 확률 무시가능 → git 머지 무충돌 (INV-K11).
"""
from __future__ import annotations

import re
import secrets
import socket
import subprocess
import json as _json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path
from typing import Any, Literal

# 내구성 노트의 타입 (§4.1 vault 레이아웃). id prefix 이자 분류 축.
NoteType = Literal["decision", "concept", "pattern", "session"]
# §13.1 D12 — (a) 프로젝트 vault 우선, personal 은 연기된 seam (기본 project).
NoteScope = Literal["project", "personal"]
# §12.6 D11 — Allen 사례 흡수 seam (기본 private). enforcement 코드 금지(INV-K6).
NoteVisibility = Literal["private", "shared"]

_VALID_TYPES: frozenset[str] = frozenset(("decision", "concept", "pattern", "session"))

# frontmatter 직렬화 필드 순서 (links/body 제외 — 별도 처리)
_SCALAR_FIELDS: tuple[str, ...] = (
    "id",
    "type",
    "scope",
    "title",
    "author",
    "source_machine",
    "created_commit",
    "created_at",
    "visibility",
)

# Windows 파일명 부적합 문자 (제어문자 포함) → '-' 치환
_UNSAFE_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
_SLUG_STRIP = re.compile(r"[^\w]+", re.UNICODE)
_MAX_SLUG_LEN = 40

# frontmatter 블록 추출 (CRLF 정규화 후) — build_knowledge_wiki._get_memory_type 패턴.
# 닫는 펜스 '\n---\n' 까지 lazy 매치 → group(2)는 본문(선행 구분 개행 1개 포함 가능).
_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


# ---------------------------------------------------------------------------
# git / 환경 헬퍼 (build_llm_wiki._git 패턴 재사용)
# ---------------------------------------------------------------------------
def _git(args: list[str], cwd: str, timeout: int = 10) -> str:
    try:
        # stdin=DEVNULL: hook/detached 컨텍스트(콘솔 stdin 핸들 NULL)에서 Windows
        # WinError 6("핸들이 잘못되었습니다")로 죽는 것 방지 → created_commit 실제 캡처(INV-K1).
        r = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _short_commit(workspace: str) -> str:
    """현재 HEAD 짧은 커밋 (build_llm_wiki:52 재사용)."""
    return _git(["rev-parse", "--short", "HEAD"], cwd=workspace).strip() or "unknown"


def _git_author(workspace: str) -> str:
    """git config user.name → 없으면 OS 사용자명 (frontmatter 조회용 보강, §3.4)."""
    name = _git(["config", "user.name"], cwd=workspace).strip()
    if name:
        return name
    try:
        return getuser()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# id 네임스페이스 헬퍼 (§12.4)
# ---------------------------------------------------------------------------
def _filename_safe(s: str) -> str:
    """Windows 포함 모든 OS 파일명 안전 문자열로 치환."""
    return _UNSAFE_FILENAME.sub("-", s).strip("-") or "x"


def _slugify(title: str) -> str:
    """제목 → 파일명 안전 slug (unicode 단어문자 보존, 한글 허용)."""
    slug = _SLUG_STRIP.sub("-", title.strip().lower()).strip("-")
    if len(slug) > _MAX_SLUG_LEN:
        slug = slug[:_MAX_SLUG_LEN].rstrip("-")
    return slug or "note"


def _micro_stamp(now: datetime) -> str:
    """마이크로초 해상도 + Windows 안전 타임스탬프 (예: 20260623T141530-482193Z)."""
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S-%fZ")


def make_id(
    note_type: str,
    source_machine: str,
    title: str,
    now: datetime,
    rand: str | None = None,
) -> str:
    """{type}/{source_machine}-{micro시각}-{rand}-{slug}.md (§12.4 무충돌 id)."""
    machine = _filename_safe(source_machine)
    micro = _micro_stamp(now)
    suffix = rand if rand is not None else secrets.token_hex(3)
    slug = _slugify(title)
    return f"{note_type}/{machine}-{micro}-{suffix}-{slug}.md"


# ---------------------------------------------------------------------------
# KnowledgeNote — 타입 SSOT (이 파일에서만 선언)
# ---------------------------------------------------------------------------
@dataclass
class KnowledgeNote:
    """내구성 지식 노트 (frontmatter 계약). INV-K3: author/source_machine/created_commit 필수."""

    id: str                      # {type}/{source_machine}-{micro}-{rand}-{slug}.md (vault 상대 경로)
    type: NoteType               # decision | concept | pattern | session
    title: str                   # 사람이 읽는 제목 (slug 원천 + Obsidian 헤딩)
    body: str = ""               # 마크다운 본문
    author: str = "unknown"      # git author (frontmatter 조회용 보강, §3.4)
    source_machine: str = "unknown"   # socket.gethostname() — 어느 PC에서 작성됐나 (P1)
    created_commit: str = "unknown"   # git rev-parse --short HEAD (commit핀, INV-K1)
    created_at: str = ""         # ISO8601 (frontmatter, Obsidian)
    scope: NoteScope = "project"        # §13.1 D12 seam (기본 project)
    visibility: NoteVisibility = "private"   # §12.6 D11 seam (기본 private)
    links: list[str] = field(default_factory=list)   # [[wikilink]] 목록

    # -- 직렬화 --------------------------------------------------------------
    def to_md(self) -> str:
        """frontmatter + 본문 마크다운으로 직렬화.

        스칼라/links 값은 json.dumps 로 인코딩 (콜론·따옴표 안전, JSON⊂YAML →
        Obsidian 호환). build_llm_wiki._make_frontmatter 의 json.dumps 선례 따름.
        """
        lines = ["---"]
        for fld in _SCALAR_FIELDS:
            value = getattr(self, fld)
            lines.append(f"{fld}: {_json.dumps(value, ensure_ascii=False)}")
        lines.append(f"links: {_json.dumps(self.links, ensure_ascii=False)}")
        lines.append("---")
        # 닫는 펜스 뒤 빈 줄 1개(구분자) + 본문 verbatim. 본문은 일절 변형하지 않는다.
        return "\n".join(lines) + "\n\n" + self.body

    @classmethod
    def from_md(cls, text: str) -> "KnowledgeNote":
        """to_md 출력을 KnowledgeNote 로 복원 (round-trip)."""
        normalized = text.replace("\r\n", "\n")
        m = _FRONTMATTER.match(normalized)
        if not m:
            raise ValueError("KnowledgeNote.from_md: frontmatter 블록(---)을 찾을 수 없음")
        fm_block, body = m.group(1), m.group(2)

        parsed: dict[str, Any] = {}
        for line in fm_block.split("\n"):
            if not line.strip() or ":" not in line:
                continue
            key, _, raw = line.partition(":")
            key, raw = key.strip(), raw.strip()
            try:
                parsed[key] = _json.loads(raw)
            except (ValueError, _json.JSONDecodeError):
                parsed[key] = raw  # 비-JSON 값 하위호환 (평문)

        # to_md 가 닫는 펜스 뒤에 넣은 구분 빈 줄 1개만 제거 → 본문 verbatim 복원
        if body.startswith("\n"):
            body = body[1:]

        return cls(
            id=parsed.get("id", ""),
            type=parsed.get("type", "session"),
            title=parsed.get("title", ""),
            body=body,
            author=parsed.get("author", "unknown"),
            source_machine=parsed.get("source_machine", "unknown"),
            created_commit=parsed.get("created_commit", "unknown"),
            created_at=parsed.get("created_at", ""),
            scope=parsed.get("scope", "project"),
            visibility=parsed.get("visibility", "private"),
            links=list(parsed.get("links", []) or []),
        )

    # -- 파일 경로 -----------------------------------------------------------
    def write_to(self, knowledge_root: str | Path) -> Path:
        """vault 의 knowledge_root 아래 self.id 경로로 노트를 쓴다. 작성 경로 반환.

        id 가 곧 vault 상대 경로이므로 {knowledge_root}/{id} 로 안착한다.
        (절대경로 하드코딩 금지 — 호출자가 root 를 준다.)
        """
        target = Path(knowledge_root) / self.id
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_md(), encoding="utf-8")
        return target


# ---------------------------------------------------------------------------
# 작성 헬퍼 (STAGE1 산출물) — author/source_machine/created_commit/created_at/id 자동 스탬프
# ---------------------------------------------------------------------------
def new_note(
    title: str,
    body: str = "",
    note_type: NoteType = "session",
    *,
    scope: NoteScope = "project",
    visibility: NoteVisibility = "private",
    links: list[str] | None = None,
    workspace: str = ".",
    rand: str | None = None,
) -> KnowledgeNote:
    """스탬프된 KnowledgeNote 를 만든다.

    자동 스탬프:
      - source_machine = socket.gethostname()
      - created_commit = git rev-parse --short HEAD (workspace 기준, INV-K1)
      - author         = git config user.name (없으면 OS 사용자)
      - created_at     = 현재 시각 ISO8601
      - id             = {type}/{machine}-{micro}-{rand}-{slug}.md (§12.4)
    """
    if note_type not in _VALID_TYPES:
        raise ValueError(
            f"new_note: type 은 {sorted(_VALID_TYPES)} 중 하나여야 함 (받음: {note_type!r})"
        )

    now = datetime.now(timezone.utc)
    # git author/commit 과 동일한 graceful "unknown" fallback 일관성 (gethostname 은 드물게 socket.error)
    try:
        machine = socket.gethostname() or "unknown"
    except Exception:
        machine = "unknown"
    return KnowledgeNote(
        id=make_id(note_type, machine, title, now, rand=rand),
        type=note_type,
        title=title,
        body=body,
        author=_git_author(workspace),
        source_machine=machine,
        created_commit=_short_commit(workspace),
        created_at=now.astimezone().isoformat(timespec="seconds"),
        scope=scope,
        visibility=visibility,
        links=list(links or []),
    )
