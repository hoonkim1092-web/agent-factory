# 리포트 + CLI 인터페이스 계약

## 개요
`src/lotto/report.py`와 `src/lotto/cli.py`는 추천기 파이프라인을 사용자 대상 터미널 리포트로 출력하는 최종 레이어다. `src/lotto_predictor/__main__.py`가 PyInstaller onefile 진입점으로 고정되며, 내부에서 `lotto.cli.main()`을 호출한다.

## 공개 API

```python
# lotto.cli
def main(argv: list[str] | None = None) -> int: ...
def run(
    *,
    n_combinations: int = 5,
    draw_count: int = 500,
    cache_path: str | None = None,
    offline: bool = False,
    pause_on_exit: bool = False,
) -> int: ...

# lotto.report
def format_report(
    combinations: Sequence[Combination],
    stats: PatternStats,
    *,
    draw_count: int,
    latest_draw_no: int | None = None,
    latest_draw_date: str | None = None,
    generated_at: datetime | None = None,
    data_source: str = "api",       # "api" | "cache"
    status: str = "success",         # "success" | "degraded-success"
) -> str: ...
def write_report(report_text: str, stream: IO | None = None) -> None: ...
```

## 계약 라인 (PyInstaller e2e 테스트 준수)

리포트 출력에 반드시 포함되는 정규식 매칭 가능 라인:

| 계약 라인 | 조건 |
|---|---|
| `동행복권 API 호출 완료: {N}회차` | `data_source="api"` |
| `통계 분석 완료: 빈도/홀짝/구간/트렌드` | `data_source="api"` |
| `캐시 fallback 사용: 최근 저장 회차 {N}` | `data_source="cache"` |
| `통계 분석 완료: cache_source=local` | `data_source="cache"` |
| `추천 조합 {N}: a, b, c, d, e, f` | 각 조합당 1라인 |
| `실행 상태: success` / `실행 상태: degraded-success` | 마지막 |

정규식: `r"추천 조합\s+\d+\s*:\s*([0-9,\s]+)"`

## 실행 경로

1. **정상 온라인**: `data_source="api"`, `status="success"`
2. **네트워크 실패 자동 fallback**: 캐시에 데이터 있으면 `data_source="cache"`, `status="degraded-success"`
3. **`--offline` 명시**: 네트워크 시도 없이 `data_source="cache"`

## CLI 옵션

| 플래그 | 기본 | 의미 |
|---|---|---|
| `-n, --count N` | 5 | 추천 조합 개수 |
| `-d, --draws N` | 500 | 분석 회차 수 (최대 `MAX_DRAWS`) |
| `--cache PATH` | `~/.lotto_cache/draws.json` | 캐시 JSON 경로 |
| `--offline` | False | 네트워크 스킵 |
| `--pause` | False | 실행 끝에 Enter 대기 (frozen 실행 시 자동 활성화) |

## PyInstaller 빌드

```bash
pyinstaller --clean --noconfirm lotto-predictor.spec
# 산출물: dist/lotto-predictor (macOS/Linux), dist/lotto-predictor.exe (Windows)
```

`lotto-predictor.spec`는 `src/lotto`와 `src/lotto_predictor`를 모두 수집하며, `requests` / `charset_normalizer` / `urllib3` / `idna` / `certifi` 를 hiddenimports에 고정한다.

## 테스트 커버리지

- `tests/test_report.py` (6종): 계약 라인 + 정규식 매칭 + 입력 검증
- `tests/test_pyinstaller_e2e.py` (기존): subprocess 목 기반 계약 freeze

## 남은 리스크

1. 실제 PyInstaller 빌드 산출물의 macOS ad-hoc 서명 — 배포 시 `codesign`으로 별도 서명 필요
2. Windows에서 한글 콘솔 출력 — `chcp 65001` 필요할 수 있음 (사용자 가이드에 기재)
3. 동행복권 API 리다이렉션 또는 스키마 변경 감지 — 지금은 `detect_latest_draw_no`의 probe 전략에 의존
