"""pytest 세션 초기화: 서버 앱/서비스 경로를 QA 테스트에 주입한다."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_WORKSPACE_ROOT = Path(__file__).resolve().parent
_workspace_str = str(_WORKSPACE_ROOT)
if _workspace_str not in sys.path:
    sys.path.insert(0, _workspace_str)

os.environ.setdefault("QA_API_APP_TARGET", "server.app:app")
os.environ.setdefault(
    "QA_API_PREDICTOR_DEPENDENCY",
    "server.dependencies:get_recommendation_service",
)
