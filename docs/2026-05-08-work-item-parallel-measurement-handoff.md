# Work-Item 병렬화 — 사전 측정 핸드오프 (Sonnet 진입용)

> **목적**: Option C-3stages 병렬화 설계의 Stage budget 산정에 필요한 sequential 실측 데이터 수집.
> **세션 진입 방법**: `/clear` 후 `/model sonnet` → 이 파일을 먼저 읽고 시작.
> **수명**: 임시 패치 — 측정 끝나면 `git restore`로 원복, **커밋 안 함**.

---

## 1. 컨텍스트 (왜 측정이 필요한지)

직전 cross-review에서 설계문서 v1 (`docs/2026-05-08-work-item-parallel-option-c-design.md`)이 BLOCK 판정을 받음. 11건 ACCEPT 중 핵심:

- **Critical #1**: Stage budget(180s) vs refine timeout(360s worst-case) **산술 모순**
- **High #7**: Stage budget 값(`{1:90, 2:180, 3:90}`)이 **실측 근거 없는 임의값**

→ sequential 실행에서 plan/spec/design/tasks 각 단계의 **실측 elapsed_sec**을 확보해야 budget 재산정이 가능. 그래서 본 측정.

---

## 2. 측정 대상

각 단계당:
| 항목 | 의미 | 수집 방법 |
|------|------|----------|
| `doc_type` | plan / spec / design / tasks | 파라미터 직접 |
| `elapsed_sec` | `_generate_and_refine` 진입 ~ 반환 wall-clock | `time.time()` 차이 |
| `refine_attempts` | 금지 토큰 보강 루프 발동 횟수 (0~2) | `refine_count` 카운터 |
| `output_chars` | 생성된 문서 글자 수 | `len(content)` |
| `ts` | 측정 시각 (unix) | `int(t0)` |

> **제외 항목**: `provider_id`, `model`, `used_fallback`은 `_generate_doc_with_llm()`이 generator 함수 내부에서 `content, _ = ...`로 메타데이터를 버리기 때문에 `_generate_and_refine` 패치 지점에서 수집 불가. elapsed_sec + refine_attempts가 Stage budget 산정의 핵심이므로 이것으로 충분.

---

## 3. 측정 방법 — 임시 패치 (커밋 X)

### 패치 위치 (1곳)

`core/work_item_generator.py:834-873` `_generate_and_refine` 함수에:
1. 진입 시 `t0 = time.time()`
2. 반환 직전 `elapsed = time.time() - t0`
3. 결과를 `runtime/timing/{slug}_baseline.jsonl`에 1줄 append (jsonl)
4. 이미 import된 `time`, `json`, `os` 활용 (추가 import 최소화)

### 예시 패치 스케치

실제 `_generate_and_refine` 함수(`core/work_item_generator.py:834-886`) 기준 diff:

```python
def _generate_and_refine(doc_type, generator_fn, work_item_id, project_brief, *extra_args, _prev_doc=""):
    """문서 생성 후 금지 토큰 스캔, 발견 시 LLM 보강 루프(최대 2회)를 수행한다."""
    import inspect as _inspect
    import os as _os
    import time as _time_m, json as _json_m  # === TIMING: 추가 ===
    _t0 = _time_m.time()                      # === TIMING: 추가 ===
    _refine_count = 0                          # === TIMING: 추가 ===
    placeholder_refine = _os.environ.get("AF_PLACEHOLDER_REFINE", "1") != "0"

    # ... (마지막 파라미터 검사, content 생성 — 기존 로직 그대로) ...

    if not placeholder_refine:
        return content

    exempt = parse_frontmatter_exempt(content)
    for attempt in range(_PLACEHOLDER_REFINE_MAX):
        found = scan_forbidden_tokens(content, exempt=exempt)
        if not found:
            break
        _refine_count += 1                     # === TIMING: 추가 ===
        # ... (기존 refine 로직 그대로) ...

    # ... (remaining 처리 — 기존 로직 그대로) ...

    # === TIMING DUMP (측정 끝나면 삭제) ===
    try:
        _os.makedirs("runtime/timing", exist_ok=True)
        _record = {
            "doc_type": doc_type,
            "work_item": work_item_id,
            "elapsed_sec": round(_time_m.time() - _t0, 3),
            "refine_attempts": _refine_count,
            "output_chars": len(content) if content else 0,
            "ts": int(_t0),
        }
        with open(f"runtime/timing/{work_item_id}_baseline.jsonl", "a") as _f:
            _f.write(_json_m.dumps(_record, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # === END TIMING DUMP ===

    return content
```

> **주의**: `provider_id`, `model`, `used_fallback`은 이 레벨에서 수집 불가 — generator 함수가 `content, _ = _generate_doc_with_llm(...)` 패턴으로 메타데이터를 버림. 해당 필드는 패치에서 제거.

### 별도 브랜치 (권장)

```bash
git checkout -b measure/work-item-baseline
# 패치 적용
# 측정 실행
git checkout 2026-05-07-memory-gitignore-cleanup  # 또는 현재 작업 브랜치
git branch -D measure/work-item-baseline  # 측정 끝나면 폐기
```

또는 동일 브랜치에서 `git restore core/work_item_generator.py`로 원복.

### 검증

패치 적용 후 `python3 -c "import core.work_item_generator"`로 임포트 동작 확인.

---

## 4. 측정 실행

### Brief 선택: **minesweeper** (가벼움)

직전 세션 "포커 게임 live run" 보다 가벼운 케이스 선택. Web 미요구, 단순 게임 로직.

### Entry Point

실제 진입점은 `run_factory_cli.py` (`core/project_pipeline.py`에는 `__main__` 블록 없음):

```bash
# 방법 A: 직접 실행
python3 run_factory_cli.py --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa

# 방법 B: af CLI alias (설치된 경우)
af --task "8x8 minesweeper game with mines" --project minesweeper-baseline --mode fsa
```

> **주의**: `--brief`, `--target-path` 플래그는 존재하지 않음. 파서 파라미터: `--task/-t`, `--project/-p`, `--mode`, `--pipeline` 등 (`run_factory_cli.py:556-578` 확인).

### 회차

- **1회 실측** 시작
- 결과 보고 시 refine 발동 케이스 0건이면 → 1회 추가 (refine 데이터 확보 위해)

---

## 5. 결과 형식

`runtime/timing/minesweeper-baseline_baseline.jsonl` 예상 출력:

```jsonl
{"doc_type":"plan","work_item":"minesweeper-baseline","elapsed_sec":58.2,"refine_attempts":0,"output_chars":3200,"ts":1746700000}
{"doc_type":"spec","work_item":"minesweeper-baseline","elapsed_sec":74.5,"refine_attempts":1,"output_chars":5100,"ts":1746700058}
{"doc_type":"design","work_item":"minesweeper-baseline","elapsed_sec":89.1,"refine_attempts":0,"output_chars":4800,"ts":1746700133}
{"doc_type":"tasks","work_item":"minesweeper-baseline","elapsed_sec":102.3,"refine_attempts":2,"output_chars":6200,"ts":1746700222}
```

### 결과 보고 시 포함할 것

- 4단계 elapsed_sec 표
- refine_attempts 합계
- timeout 발생 여부 (120s 초과 시 codex failover는 로그로 확인)
- 총 wall-clock 시간 (4개 elapsed_sec 합산 + 오버헤드)

---

## 6. 측정 후 다음 단계 (현재 세션엔 해당 X — Opus로 다시 전환)

1. 임시 패치 `git restore` (또는 브랜치 폐기)
2. **모델 전환 안내** — 사용자에게 `/model opus-4-7-1m` 권장 (설계 단계는 Opus)
3. 측정값 기반 설계문서 v2 작성:
   - Stage budget 재산정 (예: spec p95 + design p95 + 마진)
   - 11건 finding 정정 (코드 경로/라인 오류, frozen build, elapsed_sec 부재 등)
4. af-cross-review 2라운드 (max_rounds=2 정책 안)
5. PASS 시 본 구현(C-3stages 병렬화) 진입 — 다시 Sonnet

---

## 7. 본 세션에서 절대 하지 말 것

- 측정 패치를 **커밋하지 말 것** (임시 코드)
- 본 병렬화 코드는 **건드리지 말 것** (다음 라운드)
- 설계문서 v2도 **이 세션에서 쓰지 말 것** (Opus 단계)
- `runtime/timing/*.jsonl`은 `.gitignore`에 이미 `runtime/` 계열이 처리되는지 확인. 안 되어 있으면 `runtime/timing/` 추가 (단 이건 측정 끝나면 같이 원복)

---

## 8. 트러블슈팅

| 증상 | 대응 |
|------|------|
| `runtime/timing/` 디렉토리 만들기 실패 | `os.makedirs(..., exist_ok=True)` 사용 (예시 코드 그대로) |
| jsonl 파일 권한 오류 | workspace 루트에서 실행됐는지 확인 |
| claude_cli timeout 120s 초과 → codex_cli failover | 정상 동작. record에 provider_id 변화 기록 |
| refine_attempts가 모두 0 | minesweeper가 너무 단순할 수 있음. 다른 brief(예: 4-player chess)로 1회 추가 |
| 패치 import 에러 | `python3 -c "import core.work_item_generator"` 로 사전 검증 |

---

## 9. 참고 문서

- `docs/2026-05-08-work-item-parallel-option-c-design.md` — BLOCK된 설계 v1 (수정 대상)
- `docs/2026-05-08-work-item-parallel-generation-investigation.md` — 최초 핸드오프 (조사)
- `docs/reviews/2026-05-08-012548-...-design-review.md` — 직전 BLOCK 리포트 (10건 ACCEPT)
- `core/work_item_generator.py:740-870` — 수정 대상 함수
- `core/requirement_llm.py:173-230` — `execute_document_prompt` (현재 elapsed_sec 부재)
- `rubrics/work_item_doc_set.yaml` — 5개 차원 (consistency / traceability 등)
