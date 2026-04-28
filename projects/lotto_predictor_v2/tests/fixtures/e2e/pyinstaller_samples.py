"""PyInstaller e2e 회귀 테스트에서 재사용하는 목 시나리오 모음.

실제 빌드 스크립트와 단일 실행 파일이 아직 고정되지 않았기 때문에,
QA 단계에서는 subprocess/stdout 계약을 먼저 테스트로 얼린다.
"""

from __future__ import annotations

BUILD_DRY_RUN_CASE = {
    "command": [
        "pyinstaller",
        "--onefile",
        "--noconfirm",
        "src/lotto_predictor/__main__.py",
        "--name",
        "lotto-predictor",
    ],
    "stdout": "\n".join(
        [
            "[dry-run] PyInstaller onefile build planned",
            "entry_script=src/lotto_predictor/__main__.py",
            "artifact=dist/lotto-predictor",
            "status=success",
        ]
    ),
}

# 단일 실행 파일이 전체 파이프라인을 끝냈을 때 기대하는 표준 출력 예시다.
PIPELINE_SUCCESS_STDOUT = "\n".join(
    [
        "동행복권 API 호출 완료: 500회차",
        "통계 분석 완료: 빈도/홀짝/구간/트렌드",
        "추천 조합 1: 3, 11, 19, 27, 35, 42",
        "추천 조합 2: 1, 9, 14, 28, 33, 45",
        "추천 조합 3: 5, 12, 18, 24, 37, 44",
        "추천 조합 4: 2, 8, 21, 29, 34, 41",
        "추천 조합 5: 7, 13, 20, 26, 32, 39",
        "실행 상태: success",
    ]
)

# 네트워크 차단 상태에서 로컬 캐시로 후퇴하는 stdout 예시다.
OFFLINE_CACHE_FALLBACK_STDOUT = "\n".join(
    [
        "네트워크 연결 실패: offline mode",
        "캐시 fallback 사용: 최근 저장 회차 500",
        "통계 분석 완료: cache_source=local",
        "추천 조합 1: 3, 11, 19, 27, 35, 42",
        "추천 조합 2: 1, 9, 14, 28, 33, 45",
        "추천 조합 3: 5, 12, 18, 24, 37, 44",
        "추천 조합 4: 2, 8, 21, 29, 34, 41",
        "추천 조합 5: 7, 13, 20, 26, 32, 39",
        "실행 상태: degraded-success",
    ]
)

HIDDENIMPORTS_CASES = {
    "windows": {
        "command": [
            "pyinstaller",
            "--onefile",
            "--log-level",
            "INFO",
            "--hidden-import",
            "requests",
            "--hidden-import",
            "charset_normalizer",
            "src/lotto_predictor/__main__.py",
        ],
        "stdout": "\n".join(
            [
                "target_os=windows",
                "hiddenimports=requests,charset_normalizer",
                "missing_hiddenimports=0",
                "status=success",
            ]
        ),
    },
    "macos": {
        "command": [
            "pyinstaller",
            "--onefile",
            "--log-level",
            "INFO",
            "--hidden-import",
            "requests",
            "--hidden-import",
            "charset_normalizer",
            "src/lotto_predictor/__main__.py",
        ],
        "stdout": "\n".join(
            [
                "target_os=macos",
                "hiddenimports=requests,charset_normalizer",
                "missing_hiddenimports=0",
                "status=success",
            ]
        ),
    },
}
