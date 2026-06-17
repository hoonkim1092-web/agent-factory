"""앱 설정 타입 SSOT 및 저장 경로 해석.

``AppSettings``는 이 파일에서만 선언한다(타입 SSOT 규칙). 저장 경로는
절대경로 하드코딩 없이 홈/문서/현재 폴더를 기준으로 해석한다(CLAUDE.md
절대경로 하드코딩 금지 규칙).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# 전사·믹싱 공용 타깃 샘플레이트(16kHz mono) — 단일 출처
TARGET_SAMPLE_RATE = 16000

# 기본값 명명 상수 (매직 스트링/넘버 금지)
DEFAULT_MODEL_SIZE = "small"
DEFAULT_LANGUAGE = "ko"
DEFAULT_MAX_CHUNK_SEC = 12.0
DEFAULT_USE_VAD = True

# 설정 파일·산출물 폴더 이름
_CONFIG_DIR_NAME = ".meeting_stt_app"
_CONFIG_FILE_NAME = "settings.json"
_MEETINGS_DIR_NAME = "meetings"
_DOCUMENTS_DIR_NAME = "Documents"


@dataclass
class AppSettings:
    """사용자 조정 가능한 앱 설정."""

    model_size: str = DEFAULT_MODEL_SIZE          # "tiny"|"base"|"small"|"medium"
    language: str = DEFAULT_LANGUAGE              # "ko"|"auto"
    mic_device_index: Optional[int] = None
    loopback_device_index: Optional[int] = None
    save_root: Optional[str] = None               # None이면 홈/문서/앱폴더 기준 해석
    max_chunk_sec: float = DEFAULT_MAX_CHUNK_SEC  # 10~15
    use_vad: bool = DEFAULT_USE_VAD

    @classmethod
    def load(cls) -> "AppSettings":
        """설정 파일에서 로드한다. 없거나 손상되면 기본값을 반환한다."""
        path = _config_path()
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except (OSError, ValueError):
            return cls()
        # 알려진 필드만 채택 — 미래 버전의 추가 키에 견고하게 대응
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def save(self) -> None:
        """설정을 UTF-8 JSON으로 저장한다."""
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(asdict(self), fp, ensure_ascii=False, indent=2)


def _config_path() -> Path:
    """설정 파일 경로(홈 디렉터리 하위). 절대경로 리터럴을 쓰지 않는다."""
    return Path.home() / _CONFIG_DIR_NAME / _CONFIG_FILE_NAME


def resolve_save_root(settings: "AppSettings") -> Path:
    """녹음 산출물 저장 루트를 해석한다.

    우선순위:
    1. ``settings.save_root``가 지정되면 그 경로.
    2. 사용자 홈의 ``Documents``가 존재하면 ``Documents/meetings``.
    3. 그 외에는 홈의 ``meetings``.

    절대경로 리터럴을 코드에 쓰지 않고 ``Path.home()`` 기준으로 파생한다.
    """
    if settings.save_root:
        return Path(settings.save_root)
    home = Path.home()
    documents = home / _DOCUMENTS_DIR_NAME
    base = documents if documents.exists() else home
    return base / _MEETINGS_DIR_NAME
