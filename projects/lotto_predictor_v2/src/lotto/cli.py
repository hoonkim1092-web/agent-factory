"""로또 추천 CLI 진입점.

실행하면 캐시에서 최근 500회차를 읽어 통계 분석 → 패턴 기반 6숫자 조합 5개를 추천하고
터미널 리포트로 출력한다. 캐시가 비어 있으면 동행복권 API에서 수집한다.

더블클릭 실행(PyInstaller onefile)과 `python -m lotto` 양쪽에서 동작하도록 설계됐다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analytics.patterns import MAX_DRAWS, analyze_patterns
from .cache.store import LottoCacheStore
from .collector import CollectorAdapter, DrawResult
from .recommender import DEFAULT_COMBINATION_COUNT, recommend_combinations
from .report import format_report, write_report


def run(
    *,
    n_combinations: int = DEFAULT_COMBINATION_COUNT,
    draw_count: int = MAX_DRAWS,
    cache_path: str | None = None,
    offline: bool = False,
    pause_on_exit: bool = False,
) -> int:
    """추천 파이프라인 실행. 성공 시 0, 실패 시 1."""
    data_source = "cache" if offline else "api"
    status = "success"

    try:
        draws, data_source, status = _load_draws(
            cache_path=cache_path,
            draw_count=draw_count,
            offline=offline,
        )
    except Exception as exc:
        print(f"[오류] 회차 데이터 준비 실패: {exc}", file=sys.stderr)
        if pause_on_exit:
            _pause()
        return 1

    if not draws:
        print("[오류] 분석할 회차 데이터가 없습니다.", file=sys.stderr)
        if pause_on_exit:
            _pause()
        return 1

    try:
        stats = analyze_patterns(list(reversed(draws)))  # analyze는 최신→과거 순
        combinations = recommend_combinations(stats, n_combinations=n_combinations)
        latest = draws[-1]  # load_draws는 오름차순 반환 → 마지막이 최신
        report = format_report(
            combinations,
            stats,
            draw_count=len(draws),
            latest_draw_no=getattr(latest, "drw_no", None),
            latest_draw_date=getattr(latest, "drw_no_date", None),
            data_source=data_source,
            status=status,
        )
        write_report(report)
    except Exception as exc:
        print(f"[오류] 추천 계산 실패: {exc}", file=sys.stderr)
        if pause_on_exit:
            _pause()
        return 1

    if pause_on_exit:
        _pause()
    return 0


def _load_draws(
    *, cache_path: str | None, draw_count: int, offline: bool
) -> tuple[list[DrawResult], str, str]:
    """캐시/수집기에서 회차 로드.

    Returns: (draws, data_source, status)
    - draws: 오름차순 DrawResult 리스트
    - data_source: "api" | "cache"
    - status: "success" | "degraded-success"
    """
    if offline:
        return _load_offline(cache_path=cache_path, draw_count=draw_count)

    try:
        store, latest = _build_online_store(cache_path=cache_path)
    except Exception as exc:
        # 네트워크/수집기 실패 → 캐시 fallback 시도
        print(f"네트워크 연결 실패: {exc}", file=sys.stderr)
        return _load_offline(cache_path=cache_path, draw_count=draw_count)

    start = max(1, latest - draw_count + 1)
    draws = store.load_draws((start, latest))
    return draws, "api", "success"


def _build_online_store(*, cache_path: str | None) -> tuple[LottoCacheStore, int]:
    """온라인 수집기를 실제 API 클라이언트로 구성하고 최신 회차 번호를 감지한다."""
    from lotto_predictor.backend import LottoHttpClient, LottoStorage, sqlite_storage_factory
    from lotto_predictor.collector import CollectorConfig, LottoCollector

    client = LottoHttpClient()
    storage: LottoStorage = sqlite_storage_factory()
    predictor_collector = LottoCollector(client=client, storage=storage, config=CollectorConfig())
    latest = predictor_collector.detect_latest_draw_no(probe_start=1200)

    adapter = CollectorAdapter(predictor_collector)
    store = LottoCacheStore(cache_path=cache_path, collector=adapter)
    return store, latest


def _load_offline(
    *, cache_path: str | None, draw_count: int
) -> tuple[list[DrawResult], str, str]:
    """캐시 전용 로드 — 네트워크 실패 또는 --offline 플래그."""
    store = LottoCacheStore(cache_path=cache_path)
    # 캐시에 저장된 전체 payload 읽기 (공개 API가 round_range 요구 → 넓게 조회)
    try:
        draws = store.load_draws((1, 9999))
    except Exception:
        draws = []
    if not draws:
        return [], "cache", "degraded-success"
    draws = draws[-draw_count:]
    return draws, "cache", "degraded-success"


def _pause() -> None:
    """더블클릭 실행 시 창이 바로 닫히지 않도록 대기."""
    try:
        input("\n(Enter 키를 누르면 종료됩니다) ")
    except (EOFError, KeyboardInterrupt):
        pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lotto",
        description="한국 로또 6/45 패턴 기반 번호 추천기",
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=DEFAULT_COMBINATION_COUNT,
        help=f"추천 조합 개수 (기본 {DEFAULT_COMBINATION_COUNT})",
    )
    parser.add_argument(
        "-d", "--draws",
        type=int,
        default=MAX_DRAWS,
        help=f"분석에 사용할 최근 회차 수 (기본 {MAX_DRAWS})",
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=None,
        help="캐시 JSON 파일 경로 (기본: ~/.lotto_cache/draws.json)",
    )
    parser.add_argument(
        "--pause",
        action="store_true",
        help="실행 끝에 Enter 대기 (PyInstaller 더블클릭 실행용)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="네트워크 호출 없이 로컬 캐시만 사용",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # frozen(PyInstaller) 환경에서는 argv가 없으므로 항상 pause
    pause_on_exit = args.pause or _is_frozen_double_click(argv)

    return run(
        n_combinations=max(1, args.count),
        draw_count=max(1, args.draws),
        cache_path=args.cache,
        offline=args.offline,
        pause_on_exit=pause_on_exit,
    )


def _is_frozen_double_click(argv: list[str] | None) -> bool:
    """PyInstaller 더블클릭 실행 감지: frozen + argv 추가 인자 없음."""
    if not getattr(sys, "frozen", False):
        return False
    if argv is not None:
        return len(argv) == 0
    return len(sys.argv) <= 1


if __name__ == "__main__":
    raise SystemExit(main())
