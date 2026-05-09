# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onefile build spec for lotto-predictor.

빌드:
    pyinstaller --clean --noconfirm lotto-predictor.spec

산출물:
    dist/lotto-predictor         (macOS/Linux)
    dist/lotto-predictor.exe     (Windows)

hidden imports는 `requests`(HTTP 클라이언트)와 `charset_normalizer`(requests 런타임 의존)를
고정한다. `lotto`와 `lotto_predictor` 양 패키지를 모두 수집한다.
"""
from __future__ import annotations

from pathlib import Path

import PyInstaller  # noqa: F401 — spec 실행 시점에 import되어야 함

BLOCK_CIPHER = None
PROJECT_ROOT = Path(SPECPATH).resolve()
SRC_ROOT = PROJECT_ROOT / "src"
ENTRY_SCRIPT = SRC_ROOT / "lotto_predictor" / "__main__.py"

HIDDEN_IMPORTS = [
    "requests",
    "charset_normalizer",
    "urllib3",
    "idna",
    "certifi",
    "lotto",
    "lotto.cli",
    "lotto.report",
    "lotto.analytics.patterns",
    "lotto.cache.store",
    "lotto.collector",
    "lotto.recommender",
    "lotto_predictor",
    "lotto_predictor.backend",
    "lotto_predictor.cache",
    "lotto_predictor.collector",
    "lotto_predictor.analytics",
    "lotto_predictor.game_logic",
]


a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(SRC_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest", "pydoc"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=BLOCK_CIPHER,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="lotto-predictor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 터미널 리포트 출력 필요
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
