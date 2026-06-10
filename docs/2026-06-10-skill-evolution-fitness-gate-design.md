# 스킬 자가진화 Fitness 게이트 설계 — (1+1) 단조 개선

- 작성일: 2026-06-10 (KST)
- 작성 모델: Opus
- 상태: Draft — 교차검증 1라운드 BLOCK 반영 완료 (af-cross-review, single-vendor[Claude]: codex quota 소진·gemini auth 만료. High 1건 수정 + advisory 2건 반영)
- 관련 코드: `core/skill_evolution_controller.py`, `core/skill_quality_gate.py`, `core/skill_eval_harness.py`
- 관련 메모리: `feedback_design_review_mandatory`, `feedback_analysis_doc_baseline_must_be_real_code`

---

## 1. 문제 (현재 진화 검증 = "안 망가지면 통과")

진화된 스킬은 `SelfEvolutionController.submit()`에서 두 게이트를 통과해야 publish된다:

1. **Sandbox** (`_verify_sandbox`) — quick_guard(보안 AST) + run_isolated(15초 실행). = 크래시/보안 검사
2. **Quality gate** (`_run_quality_gate` → `SkillQualityGate.validate`) — contract pass_rate ≥ 0.8

문제는 **selection 압력이 없다는 것**:

- `SkillQualityGate.validate`는 `contract_eval.pass_rate`만 보고 결정한다 (`skill_quality_gate.py:80-89`).
- `SkillEvalReport.shadow_eval`(진화 전 baseline vs 진화 후 candidate의 A/B 비교)은 **계산되지만 게이트 결정에 안 쓰인다** (`skill_eval_harness.py:90`, `ShadowEvalSummary.delta` `:74-76`).
- `SelfEvolutionController._run_quality_gate`는 `gate.validate(candidate_dir, auto_register=False)`만 호출 — **baseline을 안 넘긴다** (`skill_evolution_controller.py:301`). 따라서 shadow 비교 자체가 baseline 없이 돈다.
- contract 케이스가 0개면 `static_gate.ok`(import/형식)만으로 pass_rate=1.0 간주 (`skill_quality_gate.py:85-87`).

> 결론: 현재는 "import 되고 contract 안 깨지면 publish". **진화 전보다 실제로 나아졌는지는 묻지 않는다. 퇴화한 스킬도 올라갈 수 있다.**

## 2. Baseline (실제 코드, 라인 좌표)

| 위치 | 현재 동작 |
|------|----------|
| `skill_quality_gate.py:18-26` | `GateResult` — `quality_delta: float \| None = None` 필드 존재, 미사용 |
| `skill_quality_gate.py:32` | `PASS_RATE_THRESHOLD = 0.8` |
| `skill_quality_gate.py:40-46` | `validate(...)` 정의 (본체 40), `baseline_skill_path: str \| None = None` 파라미터 :43-44 |
| `skill_quality_gate.py:48` | `skill_py = os.path.join(skill_path, "skill.py")` — candidate만 파일 경로화, baseline은 미변환 |
| `skill_quality_gate.py:66-69` | `harness.evaluate(skill_py, baseline_skill_path=baseline_skill_path)` — baseline 전달은 됨 |
| `skill_quality_gate.py:80-89` | 결정 = `contract pass_rate >= 0.8` (shadow/hidden 미반영) |
| `skill_quality_gate.py:104-111` | `GateResult` 반환 시 `quality_delta` **안 채움** |
| `skill_eval_harness.py:60-76` | `ShadowEvalSummary` — `wins/losses/ties/delta`, `delta=(wins-losses)/total_cases` |
| `skill_eval_harness.py:82-93` | `SkillEvalReport` — contract/hidden/shadow 3종 모두 보유 |
| `skill_eval_harness.py:154-160` | contract·hidden은 candidate만 평가, **shadow만 baseline 비교** |
| `skill_evolution_controller.py:106` | `old_version = _read_live_version(skill_dir)` — `skill_dir`이 곧 live(baseline) |
| `skill_evolution_controller.py:109` | `candidate_dir = _create_candidate(skill_dir)` |
| `skill_evolution_controller.py:176` | `_run_quality_gate(candidate_dir, skill_id)` — baseline 미전달 |
| `skill_evolution_controller.py:296-304` | `_run_quality_gate` → `gate.validate(candidate_dir, auto_register=False)` |

핵심: **A/B 비교 엔진(shadow + replay + delta)은 이미 완성돼 있고, 끊긴 곳은 (a) Controller가 baseline을 안 넘김 (b) Gate가 delta를 결정에 안 씀 — 두 군데의 배선뿐이다.**

## 3. 알고리즘 — (1+1) hill climbing + 단조 개선

사용자 확정안:

1. **제안 (variation)**: 한 라운드에 개선안 **딱 1개**만 생성 (현행 `evolve_skill` 그대로 — 후보 1개)
2. **검증 (evaluation)**: 진화 전(baseline)·후(candidate)를 **같은 골든셋**으로 채점
3. **합치기 (selection)**: **점수가 올라갔을 때만(delta > 0)** publish

이는 (1+1) evolution strategy다. 채택 근거(분석 결과):

- 진화 트리거가 드물고(실패 시) 실시간성이 불필요 → 직렬로 충분
- LLM 호출이 비싸다 → "1개"는 평가 1회/라운드로 비용 최소
- "딱 1개만 바꾼다" → **인과 귀속(attribution) 명확** — 어떤 변경이 점수를 올렸는지 확정 가능. N-후보 병렬은 빠르나 효과 귀속이 흐려지고 비용 N배 (기각, §9)

## 4. 설계 — 두 가드를 얹어 함정 보강

분석에서 식별한 함정(§8)을 막기 위해 단순 `delta >= 0` 컷이 아니라 다음을 적용한다.

### C1. Controller → Gate baseline 배선 (+ 경로 타입 정규화)

`SelfEvolutionController._run_quality_gate`에 baseline 디렉터리를 받아 전달.

```
# submit() :176
gate_result = self._run_quality_gate(candidate_dir, skill_id, baseline_dir=skill_dir)

# _run_quality_gate :296
def _run_quality_gate(self, candidate_dir, skill_id, *, baseline_dir=None):
    ...
    return gate.validate(
        candidate_dir,
        baseline_skill_path=baseline_dir,   # ← live(진화 전) 스킬 디렉터리
        auto_register=False,
    )
```

`skill_dir`은 live(진화 전) 스킬이므로 그대로 baseline이 된다 (`:106` 참조). LLM 미사용 — 추가 비용 0.

**⚠️ 경로 타입 정규화 (교차검증 BLOCK 반영, 2026-06-10)**:
`validate()`는 candidate에 대해 `skill_py = os.path.join(skill_path, "skill.py")`로 **파일 경로**를 만든다(`skill_quality_gate.py:48`). 그러나 `baseline_skill_path`(디렉터리)는 변환 없이 `harness.evaluate(skill_py, baseline_skill_path=baseline_dir)`로 전달되고(`:66-69`), harness `_run_shadow`는 `os.path.exists(baseline_dir)`=True로 통과하지만 `_load_skill_callable(baseline_dir)`에서 `importlib.util.spec_from_file_location(name, 디렉터리)` → `spec=None` → `baseline_callable=None`(`skill_eval_harness.py:587-590`)이 되어 shadow 비교가 **조용히 스킵**된다(`:228` 루프 미진입 → `total_cases=0`). 즉 C1만으론 배선해도 비교가 무성 실패한다.

**수정**: `validate()` 내부에서 baseline을 candidate와 **대칭으로** 파일 경로 정규화한다.

```
# skill_quality_gate.py validate() 내부 (harness.evaluate 호출 전)
baseline_py = None
if baseline_skill_path:
    _cand = os.path.join(baseline_skill_path, "skill.py")
    baseline_py = _cand if os.path.exists(_cand) else None   # knowledge 스킬은 None → 기존 동작
report = self.harness.evaluate(skill_py, baseline_skill_path=baseline_py)
```

baseline에 `skill.py`가 없으면(knowledge 스킬) `None` → harness에서 `baseline_callable=None` → `total_cases=0` → §5 하위호환 경로로 떨어진다.

### C2. Gate 결정에 shadow delta 반영 + quality_delta 반환

`SkillQualityGate.validate`의 결정 규칙을 확장(상향 게이트):

```
passed = (contract pass_rate >= PASS_RATE_THRESHOLD)
         AND _shadow_not_regressed(report.shadow_eval)

GateResult.quality_delta = report.shadow_eval.delta   # 반환 채우기
```

`_shadow_not_regressed(shadow)` 판정 (보수적·하위호환):

| 조건 | 판정 | 이유 |
|------|------|------|
| baseline 없음 (`shadow.total_cases == 0`) | **통과** | 비교 불가 → 기존 동작 유지 |
| `shadow.total_cases < MIN_SHADOW_CASES` | **통과** | 소표본 노이즈 → 차단 안 함 (§8 함정2) |
| `shadow.delta > 0` | **통과** | 개선 → 채택 |
| `shadow.delta <= 0` (케이스 충분) | **차단** | 퇴화/무변화 → REJECTED |

차단 시 `failure_reasons`에 `"shadow regression: delta={x} over {n} cases"` 추가.

**`_recommend_stage`와의 정합성 (교차검증 advisory 반영)**: harness `_recommend_stage`는 `shadow.delta >= 0`이면 `"canary"`를 추천한다(`skill_eval_harness.py:313`, 동점 포함). 반면 본 게이트는 `delta > 0`(동점 차단)이다. 이는 **충돌이 아니다** — `recommended_stage`는 "통과 시 어느 stage로 등재할지"의 추천값이고, `gate.passed=False`면 애초에 등재되지 않는다(REJECTED). 즉 `delta == 0`이면 gate가 REJECTED를 내리므로 `recommended_stage="canary"` 값은 소비되지 않는다. selection 압력의 정의상 "무변화(delta=0)는 채택하지 않는다"가 의도이며(§9, 사용자 확정 "올라갔을 때만"), `_recommend_stage`는 본 슬라이스에서 **수정하지 않는다**(범위 밖, surgical). 단 이 비대칭을 인지하고 INV에 delta=0 케이스를 명시한다.

### C3. 소표본 노이즈 가드

`MIN_SHADOW_CASES`(명명 상수, SSOT). `delta=(wins-losses)/total_cases`라 N이 작으면 1케이스로 부호가 뒤집힌다(예: N=4 → 1 win = delta 0.25). 케이스가 하한 미만이면 **delta 게이트를 적용하지 않는다**(통과를 막지 않음). 즉 "확실한 퇴화"만 차단하고, 통계적으로 못 믿을 신호로는 publish를 막지 않는다.

> 초기값 제안: `MIN_SHADOW_CASES = 3`. 단 이 수치 자체는 골든셋 규모에 따라 조정 대상 — 설계 시점에 못 박기보다 상수로 분리해 운영 중 튜닝.

## 5. 하위호환 / 안전

- **상향 게이트만**: 새 차단 경로는 "baseline 있음 + shadow 케이스 충분 + delta ≤ 0" 조합뿐. 기존에 통과하던 경로(baseline 없음 / 케이스 0 / knowledge 스킬)는 **전부 그대로 통과**.
- **knowledge 스킬(skill.py 없음)**: shadow 비교 callable 자체가 없어 `total_cases=0` → "통과"로 떨어짐. 기존 동작 유지.
- **fail-closed 유지**: gate 예외 → DEFERRED, sandbox 실패 → REJECTED (변경 없음).

## 6. 비목표 (이번 슬라이스에서 안 함)

- **N-후보 병렬 variation** — (1+1) 직렬 유지 (§9 기각)
- **simulated annealing / random restart** — local optimum 대비는 YAGNI (§8 함정4: AF 맥락에선 경감됨)
- **hidden 과적합 탐지** — baseline의 hidden 평가가 현재 구조에 없음(`:154-160`, candidate만). 구조 변경 필요 → 슬라이스2
- **프롬프트/규칙 스킬 채점** — 현재 harness는 코드 스킬(callable + 결정적 assertion)만 채점(`skill_eval_harness.py:632-665`). 프롬프트 채점은 LLM-as-judge 별도 epic → §8 함정3

## 7. 슬라이싱

| 슬라이스 | 내용 | 비용 | 상태 |
|---------|------|------|------|
| **S1 (본 설계)** | C1+C2+C3 — shadow delta 게이트 배선 | 낮음 (배선 + 상수) | 구현 대상 |
| S2 | hidden 과적합 탐지 (baseline의 hidden 평가 → hidden delta) | 중간 (harness 구조 변경) | 후속 |
| S3 | fitness 연료 — 진화 트리거(실패) 입력을 `evals.yml` 케이스로 축적 | 중간 | 후속 |
| S4 | 프롬프트/규칙 스킬 LLM-as-judge 채점기 | 높음 | 별도 epic |

## 8. 한계 / 미해결 (정직한 명시)

1. **케이스 0개 스킬엔 진화 압력이 여전히 없음.** S1은 골든셋이 있는 코드 스킬에만 작동한다. 케이스가 비면 static-only 통과가 그대로 남는다 → S3(케이스 축적)가 풀어야 함. **S1만으로 "모든 스킬이 진화한다"고 주장하지 않는다.**
2. **Goodhart / 과적합** — 점수를 contract(공개셋)로만 정의하면 그 셋에만 맞는 변경이 쌓인다. S1은 shadow(실사용 replay 포함)를 쓰므로 부분 완화되나, 완전한 과적합 탐지는 hidden delta(S2) 필요.
3. **프롬프트 스킬 채점 부재** — 정작 "최종 레시피(프롬프트/규칙)" 개선은 현재 채점기가 없어 S1 적용 불가. S4 전까지 프롬프트 스킬은 기존 static 통과.
4. **local optimum** — (1+1) greedy는 더 높은 봉우리로 가는 일시적 하강 경로를 못 넘는다. AF 맥락(드문 트리거 + LLM 변이의 약한 무작위성)에선 경감되나 이론적 한계는 존재.

## 9. 기각한 대안

- **N-후보 병렬 (1+λ)**: 탐색은 빠르나 비용 λ배 + attribution 흐려짐. AF는 비용 민감·트리거 드묾·단순성 우선(CLAUDE.md) → 직렬 (1+1)이 우월. 기각.
- **단순 `delta >= 0` 컷**: delta=0(무변화)도 통과시켜 selection 압력이 약함. 또 소표본 노이즈 무방비. C2의 `delta > 0` + C3 가드로 대체.
- **케이스 0개 스킬 publish 전면 차단(엄격)**: 진화하려면 골든셋 강제 → 기존 스킬 대량 차단(하위호환 파괴). 기각, S3로 점진 해결.

## 10. 테스트 불변식 (구현 시 RED-first)

| ID | 불변식 |
|----|--------|
| INV-1 | baseline 有 + shadow 케이스 ≥ MIN + delta>0 → PASS (개선 채택) |
| INV-2 | baseline 有 + shadow 케이스 ≥ MIN + delta<0 → REJECTED (퇴화 차단) |
| INV-2b | baseline 有 + shadow 케이스 ≥ MIN + **delta==0** → REJECTED (무변화 비채택, selection 압력) |
| INV-3 | baseline 無(total_cases=0) → 기존 동작(contract만), 하위호환 |
| INV-4 | shadow 케이스 < MIN → delta 무관 차단 안 함 (소표본 무차단) |
| INV-5 | `GateResult.quality_delta == report.shadow_eval.delta` (반환 채워짐) |
| INV-6 | Controller가 baseline 전달 시 **`report.shadow_eval.total_cases > 0`** — 즉 경로 정규화가 실제로 baseline_callable을 로드해 비교가 작동함을 검증 (단순 파라미터 전달이 아니라 silent-fail 검출, 교차검증 BLOCK 반영) |
| INV-7 | knowledge 스킬(skill.py 없음) → 기존 통과 (shadow 무효, total_cases=0) |

각 INV는 contract pass_rate는 통과(≥0.8)로 고정한 상태에서 shadow만 변주해 검증 — contract와 shadow 게이트의 독립성 확인. **INV-6은 특히 C1 경로 타입 정규화의 회귀 가드**: baseline 디렉터리를 넘겼을 때 `total_cases > 0`이 아니면(=비교 무성 실패) FAIL이어야 한다. 이 assertion이 없으면 디렉터리/파일 경로 혼동이 INV-1/INV-2를 "소표본 무차단(INV-4)" 경로로 우회해 버그를 통과시킨다.

## 11. 영향 범위

- 수정 파일: `core/skill_quality_gate.py`(validate 결정 규칙 + **baseline 경로 정규화** + quality_delta 반환 + MIN_SHADOW_CASES), `core/skill_evolution_controller.py`(_run_quality_gate 시그니처 + submit 호출)
- 신규 타입 없음 (기존 `GateResult.quality_delta`, `ShadowEvalSummary.delta` 재사용)
- Blueprint §4(자가진화 루프) + §3 해당 서브시스템 갱신 필요 (별도: §4 그림이 이미 stale — evolve_skill 직접호출로 그려짐, 실제는 SelfEvolutionController 경유)
