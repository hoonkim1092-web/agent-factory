# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir 스펙(M9).

faster-whisper 백엔드인 ctranslate2의 네이티브 DLL과 PySide6 Qt 플러그인,
faster-whisper 데이터 파일을 번들에 포함시킨다. CUDA 가속을 쓰는 경우
ctranslate2/cublas/cudnn DLL이 추가로 필요할 수 있다.

빌드:  pyinstaller meeting_stt.spec
산출:  dist/MeetingSTT/MeetingSTT.exe (onedir)
"""
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

block_cipher = None

# ctranslate2 네이티브 DLL(전사 백엔드) — 누락 시 런타임에 모델 로드 실패
binaries = collect_dynamic_libs("ctranslate2")

# faster-whisper / ctranslate2 데이터 파일(모델 메타·assets 등)
datas = collect_data_files("faster_whisper") + collect_data_files("ctranslate2")

# 동적 import 모듈 명시(onedir 누락 방지)
hiddenimports = (
    collect_submodules("faster_whisper")
    + collect_submodules("ctranslate2")
    + ["pyaudiowpatch"]
)

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MeetingSTT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI 앱 — 콘솔 창 숨김
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="MeetingSTT",
)
