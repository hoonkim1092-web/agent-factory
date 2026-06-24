"""af_ponytail: full|ultra|lite|off|status 모드 설정."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.af_ponytail import _VALID_MODES, main


def _write_config(tmp_path: Path, mode: str) -> Path:
    cfg = tmp_path / "ponytail" / "config.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"defaultMode": mode}), encoding="utf-8")
    return cfg


def _read_mode(cfg: Path) -> str:
    return json.loads(cfg.read_text(encoding="utf-8")).get("defaultMode", "")


def test_off_writes_off_not_auto(tmp_path):
    cfg = tmp_path / "ponytail" / "config.json"
    with patch("scripts.af_ponytail._get_config_path", return_value=cfg):
        ret = main(["off"])
    assert ret == 0
    assert _read_mode(cfg) == "off"


@pytest.mark.parametrize("mode", _VALID_MODES)
def test_set_mode_writes_correct_value(tmp_path, mode):
    cfg = tmp_path / "ponytail" / "config.json"
    with patch("scripts.af_ponytail._get_config_path", return_value=cfg):
        ret = main([mode])
    assert ret == 0
    assert _read_mode(cfg) == mode


def test_on_is_invalid(tmp_path, capsys):
    cfg = tmp_path / "ponytail" / "config.json"
    with patch("scripts.af_ponytail._get_config_path", return_value=cfg):
        ret = main(["on"])
    assert ret == 1
    assert not cfg.exists()


@pytest.mark.parametrize("mode", _VALID_MODES)
def test_set_message_mentions_multi_provider(tmp_path, capsys, mode):
    cfg = tmp_path / "ponytail" / "config.json"
    with patch("scripts.af_ponytail._get_config_path", return_value=cfg):
        main([mode])
    out = capsys.readouterr().out
    assert "Codex" in out and "Gemini" in out and "프로바이더" in out


def test_status_shows_provider_note_when_config_exists(tmp_path, capsys):
    cfg = _write_config(tmp_path, "full")
    with patch("scripts.af_ponytail._get_config_path", return_value=cfg):
        ret = main(["status"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Ponytail" in out and "프로바이더" in out and "설치" in out


def test_status_shows_provider_note_when_no_config(tmp_path, capsys):
    cfg = tmp_path / "ponytail" / "config.json"
    with patch("scripts.af_ponytail._get_config_path", return_value=cfg):
        ret = main(["status"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "미설치" in out or "설치" in out


def test_no_args_prints_usage(capsys):
    ret = main([])
    assert ret == 1
    err = capsys.readouterr().err
    assert "full" in err and "off" in err
