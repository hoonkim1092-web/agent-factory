"""
tests/test_gemini_smoke.py — Slow smoke test for Gemini SDK paths.

Phase B 빌드 다이어트(af.spec discovery_cache 제거 + langchain-community 제거)
이후 회귀 감지. af-critic BLOCK 3 해소.

CI 주기 실행: `pytest -m slow tests/test_gemini_smoke.py`

검증 경로:
1. 신 SDK (google.genai) — agent_runner/llm_engine 주 경로
2. 구 SDK (google.generativeai) — skills/core/cortex.py embedding 전용
"""
from __future__ import annotations

import importlib.util
import os

import pytest


_HAS_GENAI_NEW = importlib.util.find_spec("google.genai") is not None
_HAS_GENAI_OLD = importlib.util.find_spec("google.generativeai") is not None

# conftest.py가 GOOGLE_API_KEY를 "test-key" 더미로 채우므로 단순 truthy 검사로는
# 항상 True가 되어 skip이 발화하지 않는다. 실제 키 prefix("AIza...") 또는 명시적
# 화이트리스트가 아닌 dummy/placeholder 값은 "미설정"으로 간주해 skip.
_DUMMY_API_KEY_SENTINELS = {"", "test-key", "dummy", "fake", "placeholder", "none", "null"}
_RAW_API_KEY = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
_HAS_API_KEY = bool(_RAW_API_KEY) and _RAW_API_KEY.lower() not in _DUMMY_API_KEY_SENTINELS

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not _HAS_API_KEY,
        reason="GOOGLE_API_KEY/GEMINI_API_KEY 미설정(또는 conftest 더미값) — Gemini smoke 스킵",
    ),
]


@pytest.mark.skipif(not _HAS_GENAI_NEW, reason="google.genai (신 SDK) 미설치")
def test_gemini_new_sdk_list_models():
    """신 SDK — models.list()가 최소 1개 모델을 반환해야 한다.

    googleapiclient 의존 경로 미사용을 회귀 감지. 실패 시 REST 엔드포인트
    또는 gapic 코드가 discovery_cache/documents/*.json 을 참조했을 가능성.
    """
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    models = list(client.models.list())
    assert len(models) > 0, "Gemini 모델 목록이 비어 있음 — REST 경로 이상"


@pytest.mark.skipif(not _HAS_GENAI_OLD, reason="google.generativeai (구 SDK) 미설치")
def test_gemini_old_sdk_embedding():
    """구 SDK — embed_content()가 768차원 벡터를 반환해야 한다.

    skills/core/cortex.py의 CortexClient.embed() 경로 회귀 감지.
    googleapiclient.discovery 호출이 없는지 (discovery_cache 제거 후) 확인.
    """
    import google.generativeai as genai

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content="smoke test",
        task_type="retrieval_document",
        output_dimensionality=768,
    )
    embedding = result["embedding"]
    assert isinstance(embedding, list) and len(embedding) == 768


def test_discovery_cache_not_required_by_import():
    """import 시점에 discovery_cache/documents/를 강제로 읽지 않아야 한다.

    googleapiclient 가 존재해도, 우리 import 경로에서 `build()` 를 호출하지
    않는 한 580개 JSON 접근 없이도 동작해야 함 (B1 필터 근거).
    """
    import google.generativeai  # noqa: F401 — import만으로 크래시 없어야 함
    from google import genai  # noqa: F401
