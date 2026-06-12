# 배선 단선 검증 게이트 설계 (Wiring Parity Gate)

- 작성일: 2026-06-12
- 작성자: Opus (설계)
- 상태: af-cross-review PASS (BLOCK 0, single-vendor — codex 비활성) → 구현 대기. Advisory 3건 반영(W-HUNK-SPLIT/W-INIT-PARAM 테스트 + §8 tests/ 제외 명시).
- 관련 메모리: `project_wiring_parity_gate_design`, `feedback_pipeline_deploy_parity`, `project_af_gate_efficiency_debate`
- 관련 규칙: CLAUDE.md "파이프라인 배포 동등성 규칙"

---

## §0 문제 정의

**반복 결함**: 새 함수를 만들거나 기존 함수에 새 파라미터를 추가했지만, **production 호출 경로에 배선하지 않아 dead code가 된다.** 테스트 픽스처가 직접 그 함수/파라미터를 주입하면 단위 테스트는 PASS하지만, 실제 배포 사용자 경로에는 아무 효과가 없다.

CLAUDE.md "파이프라인 배포 동등성 규칙"이 이미 이를 사람-규칙으로 명문화했으나, **자동 검출 장치가 없다.** 실사례: `blast_radius.py`의 함수들, `git_configure_and_push`/`run_cross_verification`이 production에서 미사용으로 남았던 PoC 검증(메모리 §실측 baseline).

**목표**: 신규 게이트를 만들지 않고, **기존 3-Tier 검증에 배선 검증을 통합**한다 (사용자 지시: "이 문제는 AF 전체를 해야 한다").

---

## §1 동결된 설계 원칙 (재분석 금지 — 메모리에서 인용)

1. **함수 = 배선 + 통합테스트 한 세트 = 완료** (CLAUDE.md 배포 동등성). 배선 없으면 미완료. unit test만으로는 leaf만 검증.
2. **dead-symbol보다 dead-parameter에 집중**. 기존 함수에 새 파라미터를 추가했는데 **어떤 caller도 그 파라미터를 안 넘김** = 핵심 단선 신호. (신규 함수는 다음 커밋에서 배선될 수 있어 약한 신호.)
3. **순수 유틸(`utils.py`의 통계 함수류) 면제** — test-only가 정상. 슬라이스 분할 의도는 `# wiring: deferred` 마커로 명시 → 통과.
4. **WARN로 시작 → false-positive 실측 후에만 BLOCK 승격.** **단일 커밋 BLOCK 금지** (함수 추가 → 다음 커밋 배선이 정상 워크플로인데 이를 방해하면 안 됨).

---

## §2 Baseline (실제 코드 좌표 — 2026-06-12 확인)

### Layer ① 대상: `scripts/test_gap_analyzer.py`
- `analyze_diff(*, workspace, changed_files, diff_text) -> TestGapReport` (라인 303–359): 메인 루프. 각 `changed_file`에 대해 `diff_excerpt = _file_diff_excerpt(diff_text, changed_file)` 추출 → risk 함수 적용.
- 기존 risk 함수 패턴: `_is_subprocess_quoting_risk(diff_excerpt, file_text) -> bool` (279), `_is_packaging_runtime_path_risk` (298). 매칭 시 `gaps.append(TestGap(...))` (severity=`"FAIL"`) 또는 `warnings.append(...)`.
- `TestGap` dataclass (61): `risk_id, severity, changed_file, reason, expected_test_evidence, related_tests`.
- verdict: `"FAIL" if gaps else "PASS"`. warnings는 verdict에 영향 없음(WARN 채널).
- `find_related_tests(workspace, changed_file)` (246): 모듈 import / stem 기반 관련 테스트 수집 → 이미 보유.

### Layer ② 대상: `.claude/agents/af-critic.md`
- Step 3 "High (잘못된 동작)" 체크리스트 (114–118): 여기에 항목 1개 추가.
- 입력: bundle 존재 시 `.af_review_queue/review_bundle.md` §5 Direct Callers가 **이미 입력에 포함됨** (대조 지시만 부재).

### 재사용 자산
- `core/review_bundle.py:252 _find_direct_callers(workspace, changed_symbols, max_per_symbol=3)`: grep 기반(`{sym}(`), core/+scripts/만, self-def 제외. **부정확**(grep false-positive 가능, kwargs 추출 불가).
- `core/ast_engine.py:203 search_dir(pattern, directory, extensions, lang)`: ast-grep-py 기반, **정확**. `search(pattern, code, lang)` (69)도 단일 코드용. 함수 호출/kwargs 패턴 매칭 가능.
- `scripts/codebase_symbols.py`: 정의 인덱스(top-level class/func). caller 추적 X.
- `scripts/blast_radius.py`: **Tier 분류만** — caller 추적 아님(오해 주의).

### 실측 baseline (메모리)
- 공개 top-level 심볼 2,610 중 순수 dead-symbol 후보 2,004(77%). **전수 dead-symbol 스캔은 노이즈 77%라 게이트 부적합 → diff 기반이 본체.** 이번 diff에서 추가/변경된 심볼만 검사한다.

---

## §3 Layer ① — `test_gap_analyzer.py` `wiring_parity` 룰 (구조적·자동)

`af-test-runner`가 전 경로에서 이 analyzer를 호출하므로, 여기에 룰을 넣으면 "AF 전체" 자동 검사가 달성된다.

### §3.1 탐지 알고리즘 (diff 기반, deterministic)

`analyze_diff` 루프 안에서 각 `changed_file`(test 파일 제외, 이미 `_is_test_file` 가드 있음)에 대해:

**Step A — diff에서 신규/변경 심볼 추출**
`diff_excerpt`의 `+`/`-` 라인을 파싱:
- **신규 함수/클래스**: `+def NAME(` 또는 `+class NAME` 라인이 있고, 대응되는 `-def NAME(`/`-class NAME`이 **없음** → `added_symbols`.
- **파라미터 추가**: `+def NAME(...)` 와 `-def NAME(...)`가 **둘 다** 있고, 시그니처 파라미터 집합이 늘어남 → `(NAME, new_params)` 쌍을 `param_added`에 기록. new_params = 신규 시그니처 파라미터 − 구 시그니처 파라미터 (`self`/`cls`/`*`/`**`/`/` 제외, 기본값·타입어노테이션 제거 후 이름만).

> 시그니처 파싱은 단순 정규식이 한 줄 def에 충분하나, 여러 줄 def는 diff hunk에서 닫는 `)`까지 이어붙여 파싱한다. ast-grep 또는 `ast.parse`를 file_text 전체에 적용해 정확도를 올릴 수 있다(구현 재량). **파싱 실패 시 그 심볼은 skip**(false-positive보다 누락을 택함 — WARN-only 단계 정합).

**Step B — production caller 검사**
각 후보 심볼에 대해 `ast_engine.search_dir`(우선) 또는 grep fallback으로 **production 호출자**를 찾는다:
- 검색 범위: `core/`, `scripts/`, `skills/`, 워크스페이스 루트 top-level `*.py` (= `_is_candidate_python_file`의 production 부분). **`tests/` 제외** — 테스트만 호출하는 건 배선이 아니다.
- 정의 파일 자신의 self-def 라인 제외.

판정:
- **dead-parameter (핵심 신호)**: `param_added`의 함수에 대해, production caller가 1개 이상 존재하지만 **그중 어떤 caller도 `new_params` 중 하나를 키워드/위치로 넘기지 않음** → `wiring_parity` WARN.
  - kwargs 추출: ast-grep `NAME($$$ARGS)` 매칭 후 호출 노드의 keyword 이름 집합을 구함. 새 파라미터 이름이 모든 caller의 호출 인자에 전혀 안 나타나면 단선.
  - caller가 0개면 → 신규 함수와 동일 처리(아래).
- **dead-symbol (약한 신호)**: `added_symbols` 중 production caller 0개 + 관련 테스트에만 등장 → `wiring_parity` WARN. 단 **신규 함수는 다음 커밋 배선이 정상**이므로 reason에 "다음 커밋에서 배선 예정이면 `# wiring: deferred` 마커를 다세요"를 명시.

### §3.2 면제 규칙
다음 경우 WARN을 발화하지 않는다:
1. **순수 유틸 면제**: `changed_file`이 `core/utils.py`이거나, 심볼 정의에 부수효과 없는 순수 함수(판정 비용 큼 → MVP에서는 **경로 기반 allowlist**: `core/utils.py`). 통계 함수류(`weighted_mean`, `skewness` 등)는 test-only가 정상.
2. **`# wiring: deferred` 마커**: 심볼 정의 라인 또는 바로 위/아래 줄에 `# wiring: deferred` 주석이 있으면 통과. 슬라이스 분할(설계상 다음 슬라이스에서 배선) 의도를 명시.
3. **dunder/private 진입점**: `__init__`, `main`, `_`로 시작하는 내부 헬퍼 중 호출이 동적인 경우는 noise가 크므로 MVP에서 dead-symbol(약한 신호)만 skip하고 dead-parameter(강한 신호)는 유지.

### §3.3 출력
- 채널: **`warnings` 리스트** (severity FAIL 아님 → verdict에 영향 없음 = 단일 커밋 BLOCK 금지 원칙 준수).
- 형식: `f"{changed_file}: '{sym}'에 추가된 파라미터 {new_params}를 production caller({caller_files})가 넘기지 않습니다 — 배선 누락 또는 # wiring: deferred 마커 필요."`
- (승격 후) dead-parameter를 BLOCK으로 올릴 때만 `TestGap(severity="FAIL", risk_id="wiring_parity_dead_parameter", ...)`로 채널 전환. §6 참조.

---

## §4 Layer ② — `af-critic.md` Step 3 High 항목 (의미적·LLM)

review_bundle §5 Direct Callers가 이미 입력에 있으나 **대조 지시가 없어** critic이 활용하지 않는다. Step 3 "High (잘못된 동작)" 체크리스트에 1줄 추가:

```
- [ ] 배선 단선 (wiring parity): 신규 함수/새 파라미터가 review_bundle §5 Direct Callers에
      실제 production 호출로 나타나는가? 테스트에서만 호출되면 dead code 의심 —
      `# wiring: deferred` 마커가 없는 한 WARN. (CLAUDE.md 배포 동등성 규칙)
```

- Layer ②는 §5가 채워진 경우(번들 정상 생성 + changed_symbols 추출됨)에만 효과. 비어 있으면 critic이 자체 grep으로 보강하되 강제 아님(advisory).
- Layer ①(구조적)과 Layer ②(의미적)는 **상보적**: ①은 전 경로 자동·기계적, ②는 동적 호출/간접 배선 등 ①이 놓치는 의미적 케이스.

---

## §5 WARN → BLOCK 승격 기준 (§6 통합)

> ## §6 승격 정책
> 1. **시작: 전부 WARN.** dead-parameter·dead-symbol 모두 `warnings` 채널.
> 2. **실측 수집**: N회(권장 ≥10 자연 발화 run) 동안 false-positive율 측정. 메모리/NEXT_STEPS에 기록.
> 3. **승격 대상은 dead-parameter만**: false-positive율이 낮으면(<10%) `wiring_parity_dead_parameter`를 `TestGap(severity="FAIL")`로 승격. **dead-symbol은 WARN 영구 유지**(신규 함수의 다음-커밋 배선이 정상이므로 BLOCK은 워크플로 방해).
> 4. **단일 커밋 BLOCK 금지 보장**: 승격 후에도 신규 함수(caller 0)는 BLOCK 아님 — 오직 "기존 함수 + 새 파라미터 + 모든 caller가 안 넘김"만 BLOCK.

---

## §7 테스트 전략 (Layer ① — deterministic)

`tests/test_test_gap_analyzer.py`(또는 신규 `tests/test_wiring_parity.py`)에 합성 diff 픽스처로:

| ID | 케이스 | 기대 |
|----|--------|------|
| W-PARAM-DEAD | 기존 함수에 새 파라미터, production caller가 안 넘김 | WARN 발화 |
| W-PARAM-WIRED | 새 파라미터, caller가 키워드로 넘김 | WARN 없음 |
| W-NEW-DEAD | 신규 함수, caller 0 | WARN(dead-symbol) + deferred 안내 문구 |
| W-DEFERRED | 신규 함수 + `# wiring: deferred` 마커 | WARN 없음 |
| W-UTIL-EXEMPT | `core/utils.py` 신규 순수 함수 | WARN 없음 |
| W-TESTONLY | production caller 0, test caller만 | WARN(dead-symbol) |
| W-MULTILINE | 여러 줄 def 시그니처 파라미터 추가 | 정확히 파싱 → 판정 |
| W-PARSE-FAIL | 파싱 불가 시그니처 | skip(WARN 없음, no crash) |
| W-HUNK-SPLIT | 리팩토링으로 `-def`/`+def`가 다른 hunk에 분산 | 신규 함수로 오분류 허용(WARN-only) — crash 없음 |
| W-INIT-PARAM | `__init__`에 파라미터 추가(caller는 `ClassName(...)`) | `__init__(` 검색 0결과 ≠ dead-parameter, `ClassName(` 호출도 조회 |

배선 동등성 확인: `af-test-runner`가 호출하는 production 경로(`hook_runner.py` → `test_gap_analyzer.py`)에서 새 룰이 실제 실행되는지 grep 검증.

---

## §8 구현 단계 (test-first, /model sonnet)

1. **Step 0 (RED)**: §7 테스트 케이스 작성 → 전부 실패 확인.
2. **Step 1**: `test_gap_analyzer.py`에 `_extract_wiring_candidates(diff_excerpt, file_text)`(신규/파라미터 추출) + `_find_production_callers(workspace, sym)` (ast_engine.search_dir 우선, grep fallback) + `_check_wiring_parity(...)` 추가.
   - `_find_production_callers`는 `search_dir`를 `core/`/`scripts/`/`skills/`에만 호출하고, 루트 top-level `*.py`는 파일 목록 필터로 처리한다. **`search_dir` 자체는 `tests/`를 skip하지 않으므로**(`.git`/`__pycache__`/`node_modules`/`venv`만 skip — `ast_engine.py:227`), 호출 측에서 `tests/` 경로를 명시 제외해 INV-3을 보장한다.
   - `__init__` 파라미터 추가는 caller가 `ClassName(...)` 형태이므로 `__init__(` 호출 검색이 0결과여도 dead-parameter로 단정하지 않는다(W-INIT-PARAM).
3. **Step 2**: `analyze_diff` 루프에 §3.2 면제 가드 적용 후 `warnings.append(...)` 배선. **면제 allowlist는 명명 상수**(`_WIRING_EXEMPT_PATHS`, `_WIRING_DEFERRED_MARKER`) — 하드코딩 금지(메모리 `feedback_no_hardcode_single_type_source`).
4. **Step 3**: `af-critic.md` Step 3에 §4 1줄 추가(`.md`만 → review-gate 자동통과).
5. **Step 4**: GREEN 확인 + 전체 회귀.
6. **Step 5**: 3-Tier 완주(af-critic → af-cross-review → af-test-runner) → 커밋. Blueprint §0/§3 해당 섹션 + §12 이력 동일 커밋.

---

## §9 불변식 (INV — 구현이 반드시 만족)

- **INV-1**: wiring_parity는 `warnings` 채널로만 발화(승격 전). verdict는 PASS 유지(다른 FAIL gap 없을 시).
- **INV-2**: `# wiring: deferred` 마커가 심볼 정의 ±1줄에 있으면 항상 통과.
- **INV-3**: `tests/` 경로 호출은 production caller로 집계하지 않는다.
- **INV-4**: 시그니처 파싱 실패 시 crash 없이 skip(누락 > false-positive).
- **INV-5**: `core/utils.py` 신규 함수는 면제(allowlist).
- **INV-6**: dead-symbol(신규 함수 caller 0)은 영구 WARN — 절대 BLOCK 승격 대상 아님.
- **INV-7**: ast-grep-py 미설치 환경에서 grep fallback으로 degrade(crash 금지).

---

## §10 비대상 / 트레이드오프

- **비대상**: 전수 dead-symbol 스캔(노이즈 77%), 동적/리플렉션 호출 완전 추적, 다중 hop 배선 추적(1-hop 직접 caller만), 부수효과 기반 순수성 자동 판정(MVP는 경로 allowlist).
- **트레이드오프**: AST 정확도 ↔ 비용. ast_engine 우선·grep fallback으로 절충. 1-hop만 보므로 "A→B→C에서 B만 추가" 같은 중간 단선은 §4 critic의 의미적 판단에 위임.
- **메타-재귀 주의**: 이 게이트는 내부 파이프라인 검증 도구다. 사용자 지시("AF 전체")로 정당화됨 — 단 Layer ① WARN-only 시작으로 워크플로 비침습 보장.
