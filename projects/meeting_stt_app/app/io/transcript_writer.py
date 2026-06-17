"""전사 텍스트 기록기(M5).

전사 청크를 누적했다가 종료 시 ``.txt``(순수 텍스트)와 ``.md``(타임스탬프
표 형식)로 한 번에 flush 한다.
"""
from __future__ import annotations

from pathlib import Path

from ..stt.types import TranscriptChunk


def _fmt_ts(seconds: float) -> str:
    """초를 mm:ss 형식 문자열로 변환한다."""
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


class TranscriptWriter:
    """전사 청크를 모아 txt/md로 출력한다."""

    def __init__(self) -> None:
        self._chunks: list[TranscriptChunk] = []

    def append(self, chunk: TranscriptChunk) -> None:
        """전사 청크를 누적한다."""
        self._chunks.append(chunk)

    def flush(self, txt_path: Path, md_path: Path) -> None:
        """누적된 청크를 ``.txt``와 ``.md`` 파일로 기록한다."""
        txt_path = Path(txt_path)
        md_path = Path(md_path)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.parent.mkdir(parents=True, exist_ok=True)

        with open(txt_path, "w", encoding="utf-8") as fp:
            for c in self._chunks:
                fp.write(c.text.strip() + "\n")

        with open(md_path, "w", encoding="utf-8") as fp:
            fp.write("# 회의록 전사\n\n")
            fp.write("| 시작 | 종료 | 내용 |\n")
            fp.write("| --- | --- | --- |\n")
            for c in self._chunks:
                text = c.text.strip().replace("|", "\\|")
                fp.write(f"| {_fmt_ts(c.start_ts)} | {_fmt_ts(c.end_ts)} | {text} |\n")
