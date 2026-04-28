"""동행복권 API 수집기 회귀 테스트용 목 응답 모음.

각 응답은 실제 동행복권 API에서 기대하는 형태를 축약해 표현한다.
한국어 주석으로 각 fixture 의 의도와 실패 조건을 함께 남긴다.
"""

from __future__ import annotations

from copy import deepcopy

# 정상 회차 응답 예시. 파서가 drwNo, 날짜, 본 번호 6개, 보너스 번호를
# 안정적으로 읽어 LottoDraw 로 변환하는지 검증할 때 사용한다.
SUCCESS_DRAW_1120 = {
    "returnValue": "success",
    "drwNo": 1120,
    "drwNoDate": "2024-06-01",
    "drwtNo1": 2,
    "drwtNo2": 19,
    "drwtNo3": 26,
    "drwtNo4": 31,
    "drwtNo5": 38,
    "drwtNo6": 41,
    "bnusNo": 34,
    "totSellamnt": 112233445566,
    "firstWinamnt": 2134567890,
}

# HTML 오류 페이지 예시. 서버가 JSON 대신 HTML 을 반환했을 때
# response.json() 단계에서 ValueError 로 처리되는지 확인할 때 사용한다.
HTML_ERROR_PAGE = """\
<!doctype html>
<html lang="ko">
  <head><title>500 서버 오류</title></head>
  <body>
    <h1>일시적인 서버 오류</h1>
    <p>잠시 후 다시 시도해 주세요.</p>
  </body>
</html>
"""

# 스키마 변경 예시. 핵심 키 drwtNo6 을 제거해 파서가 조용히 통과하지 않고
# 구조 이상을 unknown 실패로 기록하는지 검증할 때 사용한다.
SCHEMA_CHANGED_DRAW_1120 = {
    "returnValue": "success",
    "drwNo": 1120,
    "drwNoDate": "2024-06-01",
    "drwtNo1": 2,
    "drwtNo2": 19,
    "drwtNo3": 26,
    "drwtNo4": 31,
    "drwtNo5": 38,
    "bnusNo": 34,
}


def clone_payload(payload: dict[str, object]) -> dict[str, object]:
    """테스트 간 fixture 오염을 막기 위한 깊은 복사 헬퍼."""
    return deepcopy(payload)
