#!/usr/bin/env python3
"""lotto seed_draws.json 갱신 스크립트 — 월 1회 실행 권장.

동행복권 공식 API에서 최신 100회차를 조회해 seed_draws.json을 덮어쓴다.
네트워크 불가 시 기존 파일을 유지하고 경고를 출력한다.

사용법:
    python scripts/refresh_lotto_seed.py [--project lotto_predictor_v2]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_LOGGER = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent
_ENDPOINT = "https://www.dhlottery.co.kr/common.do"
_DEFAULT_PROJECT = "lotto_predictor_v2"
_SEED_COUNT = 100


def _fetch_draw(session, draw_no: int) -> dict | None:
    try:
        import requests
        resp = session.get(
            _ENDPOINT,
            params={"method": "getLottoNumber", "drwNo": draw_no},
            timeout=5.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("returnValue") != "success":
            return None
        return data
    except Exception as exc:
        _LOGGER.debug("회차 %d 조회 실패: %s", draw_no, exc)
        return None


def _detect_latest(session) -> int | None:
    """이진 탐색으로 최신 회차를 탐지한다."""
    lo, hi = 1100, 1200
    # hi 상향: 최신 회차를 찾을 때까지
    while _fetch_draw(session, hi) is not None:
        hi += 50
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _fetch_draw(session, mid) is not None:
            lo = mid
        else:
            hi = mid - 1
    return lo if lo >= 1 else None


def main() -> int:
    parser = argparse.ArgumentParser(description="lotto seed 갱신")
    parser.add_argument("--project", default=_DEFAULT_PROJECT)
    parser.add_argument("--count", type=int, default=_SEED_COUNT)
    args = parser.parse_args()

    seed_path = _REPO_ROOT / "projects" / args.project / "seed_draws.json"
    if not seed_path.parent.exists():
        _LOGGER.error("프로젝트 디렉토리가 없음: %s", seed_path.parent)
        return 1

    try:
        import requests
    except ImportError:
        _LOGGER.error("`pip install requests` 필요")
        return 1

    with requests.Session() as session:
        session.headers["User-Agent"] = "af-seed-refresh/1.0"
        _LOGGER.info("최신 회차 탐지 중...")
        latest = _detect_latest(session)
        if latest is None:
            _LOGGER.error("최신 회차 탐지 실패 — 네트워크 확인 요망. 기존 seed 유지.")
            return 1

        _LOGGER.info("최신 회차: %d. 최근 %d회차 수집 중...", latest, args.count)
        start = max(1, latest - args.count + 1)
        draws: list[dict] = []
        for drw_no in range(start, latest + 1):
            data = _fetch_draw(session, drw_no)
            if data is None:
                _LOGGER.warning("drw_no=%d 조회 실패, 건너뜀", drw_no)
                continue
            draws.append({
                "drw_no": data["drwNo"],
                "drw_date": data.get("drwNoDate", ""),
                "numbers": [
                    data["drwtNo1"], data["drwtNo2"], data["drwtNo3"],
                    data["drwtNo4"], data["drwtNo5"], data["drwtNo6"],
                ],
                "bonus_no": data["bnusNo"],
            })

    if not draws:
        _LOGGER.error("수집된 회차 없음. 기존 seed 유지.")
        return 1

    existing_age = 0
    if seed_path.exists():
        try:
            old = json.loads(seed_path.read_text(encoding="utf-8"))
            old_ts = old.get("_meta", {}).get("generated_at", "")
            if old_ts:
                old_dt = datetime.fromisoformat(old_ts)
                existing_age = (datetime.now(timezone.utc) - old_dt.replace(tzinfo=timezone.utc)).days
        except Exception:
            pass

    payload = {
        "_meta": {
            "source": "동행복권 공공 발표 결과 (https://www.dhlottery.co.kr)",
            "license": "공공 정보 재사용 허용 — 출처 명시 조건",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "draw_count": len(draws),
            "draw_range": [draws[0]["drw_no"], draws[-1]["drw_no"]],
            "age_days": 0,
            "previous_age_days": existing_age,
        },
        "draws": draws,
    }
    seed_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _LOGGER.info("seed 갱신 완료: %s (%d회차)", seed_path, len(draws))
    return 0


if __name__ == "__main__":
    sys.exit(main())
