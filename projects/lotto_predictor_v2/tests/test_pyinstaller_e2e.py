from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.e2e.pyinstaller_samples import (
    BUILD_DRY_RUN_CASE,
    HIDDENIMPORTS_CASES,
    OFFLINE_CACHE_FALLBACK_STDOUT,
    PIPELINE_SUCCESS_STDOUT,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _completed_process(
    cmd: list[str],
    *,
    stdout: str,
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    """문자열 기반 subprocess 결과를 빠르게 조립한다."""
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _parse_recommendations(stdout: str) -> list[tuple[int, ...]]:
    """표준 출력에서 추천 조합 5줄을 정규식으로 추출한다."""
    matches = re.findall(r"추천 조합\s+\d+\s*:\s*([0-9,\s]+)", stdout)
    combinations: list[tuple[int, ...]] = []
    for chunk in matches:
        numbers = tuple(int(number.strip()) for number in chunk.split(","))
        combinations.append(numbers)
    return combinations


@pytest.fixture
def fake_subprocess_run(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """subprocess.run 호출 이력을 기록하고 원하는 결과를 주입할 수 있게 한다."""
    calls: list[dict[str, object]] = []
    results: list[subprocess.CompletedProcess[str]] = []

    def _run(
        cmd: list[str],
        *,
        cwd: Path | None = None,
        check: bool = False,
        capture_output: bool = False,
        text: bool = False,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(
            {
                "cmd": cmd,
                "cwd": cwd,
                "check": check,
                "capture_output": capture_output,
                "text": text,
                "env": env,
            }
        )
        if not results:
            raise AssertionError("테스트가 준비한 subprocess 결과가 없다.")
        result = results.pop(0)
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                cmd,
                output=result.stdout,
                stderr=result.stderr,
            )
        return result

    monkeypatch.setattr(subprocess, "run", _run)
    calls.append({"results": results})
    return calls


def test_pyinstaller_onefile_빌드_dry_run_성공_검증(
    fake_subprocess_run: list[dict[str, object]],
) -> None:
    results = fake_subprocess_run[0]["results"]
    assert isinstance(results, list)
    results.append(
        _completed_process(
            BUILD_DRY_RUN_CASE["command"],
            stdout=BUILD_DRY_RUN_CASE["stdout"],
        )
    )

    completed = subprocess.run(
        BUILD_DRY_RUN_CASE["command"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    call = fake_subprocess_run[1]
    assert call["cwd"] == PROJECT_ROOT
    assert call["capture_output"] is True
    assert call["text"] is True
    assert "--onefile" in call["cmd"]
    assert "status=success" in completed.stdout
    assert "artifact=dist/lotto-predictor" in completed.stdout


def test_단일_실행_파일이_전체_파이프라인을_완료한다(
    fake_subprocess_run: list[dict[str, object]],
) -> None:
    executable = PROJECT_ROOT / "dist" / "lotto-predictor"
    results = fake_subprocess_run[0]["results"]
    assert isinstance(results, list)
    results.append(_completed_process([str(executable)], stdout=PIPELINE_SUCCESS_STDOUT))

    completed = subprocess.run(
        [str(executable)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    combinations = _parse_recommendations(completed.stdout)

    assert "동행복권 API 호출 완료" in completed.stdout
    assert "통계 분석 완료" in completed.stdout
    assert "실행 상태: success" in completed.stdout
    assert len(combinations) == 5
    assert all(len(numbers) == 6 for numbers in combinations)
    assert all(all(1 <= number <= 45 for number in numbers) for numbers in combinations)


def test_네트워크_차단_환경에서_캐시_fallback_동작을_검증한다(
    fake_subprocess_run: list[dict[str, object]],
) -> None:
    executable = PROJECT_ROOT / "dist" / "lotto-predictor"
    results = fake_subprocess_run[0]["results"]
    assert isinstance(results, list)
    results.append(
        _completed_process(
            [str(executable), "--offline"],
            stdout=OFFLINE_CACHE_FALLBACK_STDOUT,
        )
    )

    completed = subprocess.run(
        [str(executable), "--offline"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={"LOTTO_PREDICTOR_NETWORK": "blocked"},
    )

    combinations = _parse_recommendations(completed.stdout)

    assert "네트워크 연결 실패" in completed.stdout
    assert "캐시 fallback 사용" in completed.stdout
    assert "cache_source=local" in completed.stdout
    assert "실행 상태: degraded-success" in completed.stdout
    assert len(combinations) == 5


@pytest.mark.parametrize(("target_os", "case"), tuple(HIDDENIMPORTS_CASES.items()))
def test_windows_macos_hiddenimports_누락을_체크한다(
    target_os: str,
    case: dict[str, object],
    fake_subprocess_run: list[dict[str, object]],
) -> None:
    results = fake_subprocess_run[0]["results"]
    assert isinstance(results, list)
    command = case["command"]
    stdout = case["stdout"]
    assert isinstance(command, list)
    assert isinstance(stdout, str)
    results.append(_completed_process(command, stdout=stdout))

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert f"target_os={target_os}" in completed.stdout
    assert "missing_hiddenimports=0" in completed.stdout
    assert "hiddenimports=requests,charset_normalizer" in completed.stdout
    assert "--hidden-import" in command
