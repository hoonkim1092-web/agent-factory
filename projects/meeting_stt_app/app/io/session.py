"""세션 메타데이터 타입 SSOT.

``RecordingSession``은 이 파일에서만 선언한다(타입 SSOT 규칙). 다른 모듈은
여기서 import 한다. 재선언 금지.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RecordingSession:
    """한 녹음 세션의 메타데이터.

    종료 시 ``session.json``으로 직렬화되어 산출물(WAV/transcript)과 함께
    ``meetings/<session_id>/``에 저장된다.
    """

    session_id: str
    started_at: str
    ended_at: str
    wav_path: str
    transcript_txt_path: str
    transcript_md_path: str
    model_size: str
    language: str
    mic_device: str
    loopback_device: str
    duration_sec: float

    def save_json(self, path: Path) -> None:
        """세션 메타데이터를 UTF-8 JSON으로 저장한다."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(asdict(self), fp, ensure_ascii=False, indent=2)
