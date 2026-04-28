#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


FAILURE_ENVIRONMENT = "환경 문제"
FAILURE_FETCH = "데이터 수집 실패"
FAILURE_STORAGE = "저장소 실패"
FAILURE_ANALYZE = "분석 실패"
FAILURE_RECOMMEND = "추천 실패"
FAILURE_OUTPUT = "출력 포맷 실패"


@dataclass
class CheckResult:
    slice_name: str
    status: str
    failure_type: str | None
    details: str


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def run_shell_command(command: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def append_result(
    results: list[CheckResult],
    slice_name: str,
    status: str,
    details: str,
    failure_type: str | None = None,
) -> None:
    results.append(
        CheckResult(
            slice_name=slice_name,
            status=status,
            failure_type=failure_type,
            details=details,
        )
    )


def validate_path_target(path_value: str | None, label: str, results: list[CheckResult]) -> None:
    if not path_value:
        append_result(results, label, "FAIL", f"{label}가 지정되지 않았습니다.", FAILURE_ENVIRONMENT)
        return

    path = Path(path_value)
    if path.exists():
        append_result(results, label, "PASS", f"{label} 경로를 확인했습니다: {path}")
        return

    parent = path.parent
    existing_ancestor = parent
    while not existing_ancestor.exists() and existing_ancestor != existing_ancestor.parent:
        existing_ancestor = existing_ancestor.parent
    if existing_ancestor.exists():
        append_result(
            results,
            label,
            "PASS",
            f"{label} 상위 경로를 생성할 수 있습니다: {path} (기준 경로: {existing_ancestor})",
        )
        return

    append_result(
        results,
        label,
        "FAIL",
        f"{label} 상위 경로가 존재하지 않습니다: {parent}",
        FAILURE_ENVIRONMENT,
    )


def contains_any(text: str, tokens: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def preflight_checks(args: argparse.Namespace) -> list[CheckResult]:
    results: list[CheckResult] = []

    for label, command in (
        ("fetch 명령", args.fetch_cmd),
        ("analyze 명령", args.analyze_cmd),
        ("recommend 명령", args.recommend_cmd),
    ):
        if command:
            append_result(results, label, "PASS", f"{label}이 정의되었습니다: {command}")
        else:
            append_result(results, label, "FAIL", f"{label}이 정의되지 않았습니다.", FAILURE_ENVIRONMENT)

    validate_path_target(args.cache_path, "캐시 경로", results)
    validate_path_target(args.report_json, "JSON 보고서 경로", results)
    validate_path_target(args.report_markdown, "Markdown 보고서 경로", results)
    return results


def module_contract_checks(args: argparse.Namespace) -> list[CheckResult]:
    results: list[CheckResult] = []
    command_specs = (
        ("fetch", args.fetch_cmd, FAILURE_FETCH, ("회차", "건", "저장", "cache")),
        ("analyze", args.analyze_cmd, FAILURE_ANALYZE, ("빈도", "통계", "분석", "pair", "cooccurrence")),
        ("recommend", args.recommend_cmd, FAILURE_RECOMMEND, ("조합", "추천", "weight", "score")),
    )

    for name, command, failure_type, expected_tokens in command_specs:
        if not command:
            append_result(results, f"{name} 계약", "FAIL", f"{name} 명령이 없어 계약 검증을 수행할 수 없습니다.", FAILURE_ENVIRONMENT)
            continue

        code, stdout, stderr = run_shell_command(command)
        merged = "\n".join(part for part in (stdout, stderr) if part)
        if code != 0:
            append_result(results, f"{name} 계약", "FAIL", f"종료 코드 {code}\n{merged}".strip(), failure_type)
            continue

        if not merged:
            append_result(results, f"{name} 계약", "FAIL", "표준 출력 또는 오류 출력이 비어 있습니다.", FAILURE_OUTPUT)
            continue

        if name == "recommend":
            if len(extract_number_sets(merged)) < 5:
                append_result(results, f"{name} 계약", "FAIL", "5개 조합을 확인하지 못했습니다.", failure_type)
                continue
            if not all(len(set(number_set)) == 6 for number_set in extract_number_sets(merged)[:5]):
                append_result(results, f"{name} 계약", "FAIL", "추천 조합 내부에 중복 번호가 있습니다.", failure_type)
                continue

        if contains_any(merged, expected_tokens):
            append_result(results, f"{name} 계약", "PASS", merged[:500])
        else:
            append_result(
                results,
                f"{name} 계약",
                "FAIL",
                f"기대 키워드를 찾지 못했습니다. 출력:\n{merged[:500]}",
                FAILURE_OUTPUT,
            )

    return results


def extract_number_sets(text: str) -> list[list[int]]:
    sets: list[list[int]] = []
    for line in text.splitlines():
        numbers = []
        for token in line.replace(",", " ").split():
            stripped = token.strip("[]()")
            if stripped.isdigit():
                number = int(stripped)
                if 1 <= number <= 45:
                    numbers.append(number)
        if len(numbers) >= 6:
            sets.append(numbers[:6])
    return sets


def end_to_end_check(args: argparse.Namespace) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not all((args.fetch_cmd, args.analyze_cmd, args.recommend_cmd)):
        append_result(results, "종단간 회귀", "FAIL", "세 개의 명령이 모두 정의되어야 합니다.", FAILURE_ENVIRONMENT)
        return results

    history: list[str] = []
    for name, command, failure_type in (
        ("fetch", args.fetch_cmd, FAILURE_FETCH),
        ("analyze", args.analyze_cmd, FAILURE_ANALYZE),
        ("recommend", args.recommend_cmd, FAILURE_RECOMMEND),
    ):
        code, stdout, stderr = run_shell_command(command)
        merged = "\n".join(part for part in (stdout, stderr) if part).strip()
        history.append(f"[{name}] code={code}\n{merged}")
        if code != 0:
            append_result(results, "종단간 회귀", "FAIL", "\n\n".join(history), failure_type)
            return results

    append_result(results, "종단간 회귀", "PASS", "\n\n".join(history)[:1500])
    return results


def write_json_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# QA 실행 결과",
        "",
        f"- 실행 시각: {payload['generated_at']}",
        f"- 전체 상태: {payload['summary']['status']}",
        "",
        "| 항목 | 상태 | 실패 분류 | 상세 |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["results"]:
        failure_type = item["failure_type"] or "-"
        detail = item["details"].replace("\n", "<br>")
        lines.append(f"| {item['slice_name']} | {item['status']} | {failure_type} | {detail} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize(results: list[CheckResult]) -> dict:
    status = "PASS" if results and all(item.status == "PASS" for item in results) else "FAIL"
    return {
        "status": status,
        "passed": sum(1 for item in results if item.status == "PASS"),
        "failed": sum(1 for item in results if item.status == "FAIL"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="핵심 플로우와 회귀 시나리오를 검증한다.")
    parser.add_argument("--fetch-cmd", help="fetch 검증에 사용할 실제 실행 명령")
    parser.add_argument("--analyze-cmd", help="analyze 검증에 사용할 실제 실행 명령")
    parser.add_argument("--recommend-cmd", help="recommend 검증에 사용할 실제 실행 명령")
    parser.add_argument("--cache-path", default="artifacts/qa/cache.db", help="캐시 경로 또는 예상 캐시 파일 경로")
    parser.add_argument("--report-json", default="artifacts/qa/qa-report.json", help="JSON 보고서 출력 경로")
    parser.add_argument(
        "--report-markdown",
        default="artifacts/qa/qa-report.md",
        help="Markdown 보고서 출력 경로",
    )
    parser.add_argument(
        "--skip-e2e",
        action="store_true",
        help="종단간 회귀 검증을 생략한다.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results: list[CheckResult] = []
    results.extend(preflight_checks(args))
    results.extend(module_contract_checks(args))
    if not args.skip_e2e:
        results.extend(end_to_end_check(args))

    payload = {
        "generated_at": now_iso(),
        "commands": {
            "fetch": args.fetch_cmd,
            "analyze": args.analyze_cmd,
            "recommend": args.recommend_cmd,
        },
        "cache_path": args.cache_path,
        "results": [asdict(item) for item in results],
        "summary": summarize(results),
    }

    write_json_report(Path(args.report_json), payload)
    write_markdown_report(Path(args.report_markdown), payload)

    return 0 if payload["summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
