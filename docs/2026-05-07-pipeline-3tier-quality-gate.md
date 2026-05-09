# 프로덕션 파이프라인 3-Tier Quality Gate 통합

> Status: DESIGN v2 (af-cross-review BLOCK 9건 반영)
> Date: 2026-05-07
> Author: Claude (Opus 4.7) — design phase
> Review: docs/reviews/ 의 latest pipeline-3tier-quality-gate-design-review.md
> Implementation: 별도 작업 (Sonnet 4.6)

## §0 한 줄 요약

개발 환경 3-Tier 교차검증을 **프로덕션 파이프라인의 work-item 산출물**에도 적용한다. 신규 컴포넌트 추가가 아니라 **기존 인프라 3개**(`run_structural_gate` / `DocumentReviewSession` / `provider_detect`)를 통합하는 작업이다.

## §1 배경 및 문제 정의

### §1.1 현재 상태 (코드 기반 사실)

**개발 환경 3-Tier** (git pre-commit + Claude Code hook):
- Tier 1: `af-test-runner` — pytest 실행
- Tier 2: `af-critic` — Claude Sonnet 코드 비평
- Tier 3: `af-cross-review` — `provider_detect.py`로 외부 CLI fan-out (codex/gemini)
- Provider 감지: `core/provider_detect.py` (3-state: AVAILABLE / AUTH_EXPIRED / NOT_INSTALLED, 1h 캐시, auth ping)

**프로덕션 파이프라인 현재 품질 단계** (`core/project_pipeline.py:937-1046`):
1. `PlanVerifier.verify` (947-973) — plan-critique-verify, 2회 retry
2. `run_structural_gate(project_brief, "work_item")` (977) — RubricCompiler 구조 검사
3. `DocumentReviewSession.run_review` (985-1044) — critic + (선택) cross + judge

### §1.2 결함

| ID | 결함 | 위치 | 영향 |
|---|---|---|---|
| D1 | Provider 감지 중복 | `core/review_runner.py:37` | `shutil.which`만 사용. auth ping 없음 → 인증 만료 CLI를 AVAILABLE로 오판. |
| D2 | 레벨 게이팅 | `core/review_report.py:293,304` | cross/judge가 `level == "enterprise"`일 때만 실행. dynamic 사용자는 critic 1개뿐 — 사용자 구독 LLM이 2개 이상이어도 cross 미실행. |
| D3 | Tier 1 QA 미적용 | `project_pipeline.py:977` | `run_structural_gate`가 `project_brief`만 평가, work-item 문서 자체에 대한 구조 검사 없음. |
| D4 | 빈 fallback 의미 모호 | `review_report.py:268` | provider 0개 → "PASS" 반환. 미검증 상태인데 통과로 기록 — 메트릭 오염. |

### §1.3 사용자 요구사항 (2026-05-07 세션)

> "프로덕션도 CLI 설치 및 인증 여부로 판단해야 한다. 3티어는 QA에이전트 → 코드리뷰 → 타모델 교차검증."
> "사용자가 어떤 LLM CLI를 구독·인증했느냐에 따라 cross 활성화 여부가 결정되어야 한다."

## §2 목표 / 비목표

### §2.1 목표 (G)

- **G1** 프로덕션 파이프라인에서도 `provider_detect.py`의 3-state 감지(installed + auth ping + 1h 캐시) 사용
- **G2** Cross-validation 활성화 조건을 `enterprise` 레벨이 아니라 **AVAILABLE 외부 CLI 2개 이상**으로 변경
- **G3** Tier 1 QA에 work-item 문서 자체의 rubric 평가를 명시적으로 포함
- **G4** Provider 0개일 때 verdict를 `SKIP`으로 분리 (PASS와 구분 — 메트릭 보존)
- **G5** AUTH_EXPIRED provider 1개 이상 → 즉시 BLOCK + 재인증 안내 (부분 만료 포함)

### §2.2 비목표 (NG)

- **NG1** 개발 환경 3-Tier(`af-test-runner` 등)는 변경하지 않음
- **NG2** PlanVerifier 로직은 변경하지 않음
- **NG3** EXE 배포 결정과 무관하게 작동 (둘 다 동작해야 함)
- **NG4** 새 컴포넌트 추가 금지 — 기존 3개를 통합만. 환경변수도 기존 `AF_SKIP_PROVIDER` 재사용 (신규 변수 도입 X).

## §3 설계

### §3.1 3-Tier 매핑 (프로덕션)

| Tier | 역할 | 구현 (재사용) | 검증 대상 |
|---|---|---|---|
| **T1 QA** | 구조/완결성 정적 검사 | `run_structural_gate` 확장 | work-item .md 4종 + project_brief |
| **T2 Critic** | 자가 비평 (구독 모델로 self-review) | `DocumentReviewSession.critic` | work-item 문서 합본 |
| **T3 Cross** | 타모델 독립 검증 | `DocumentReviewSession.cross + judge` | work-item 문서 합본 |

### §3.2 데이터 흐름

```
generate_work_items()  →  work_item_files (dict[name, path])
    ↓
[T1 QA] run_structural_gate( _load_doc_contents(work_item_files), "work_item_doc_set" )
    ↓ FAIL → fix_instructions 생성 → _refine_document → 재시도 (max 1회)
    ↓ PASS
[T2 Critic / T3 Cross] DocumentReviewSession.run_review(...)
    ├─ 진입 즉시: detect_provider_states()로 전체 상태 확인
    │     AUTH_EXPIRED ≥ 1                  → BLOCK + 재인증 메시지 (G5)
    │     AVAILABLE = 0                     → SKIP (G4, 메트릭 분리)
    │     AVAILABLE ≥ 2                     → critic + cross + judge 실행 (G2)
    │     AVAILABLE = 1                     → critic만, T3 SKIP (judge=critic verdict)
    └─ retry 정책: max_rounds(dynamic=1, enterprise=2) 회 _refine_document 루프
    ↓ PASS / SKIP
Implementer (Phase 2 execute)
```

### §3.3 코드 변경 (4개 파일 + 1개 신규 yaml + 3개 다운스트림 패치)

> **High issue #1, #2, #3 (af-cross-review BLOCK)** 모두 본 절에서 해결.

#### §3.3.1 `core/review_runner.py:detect_providers` — provider_detect 위임

```python
# Before
def detect_providers() -> list[str]:
    available = []
    for name, cmd in CLI_COMMANDS.items():
        if shutil.which(cmd):
            available.append(name)
    return available

# After — provider_detect.py에 위임 + 기존 순서 보존(BLOCK #9 fix)
def detect_providers() -> list[str]:
    """AVAILABLE 상태의 provider만 반환. AUTH_EXPIRED 제외.
    반환 순서는 기존(claude, codex, gemini)을 보존해 critic/cross 선택 변동 방지."""
    from core.provider_detect import detect_provider_states, ProviderState
    states = detect_provider_states()
    id_to_key = {"claude_cli": "claude", "codex_cli": "codex", "gemini_cli": "gemini"}
    avail = {id_to_key[pid] for pid, r in states.items()
             if r.state == ProviderState.AVAILABLE and pid in id_to_key}
    # 기존 review_runner CLI_COMMANDS 순서 보존
    return [k for k in ("claude", "codex", "gemini") if k in avail]


def detect_blocked_providers() -> list[str]:
    """AUTH_EXPIRED 목록 — DocumentReviewSession이 BLOCK 메시지에 사용."""
    from core.provider_detect import detect_provider_states, ProviderState
    states = detect_provider_states()
    id_to_key = {"claude_cli": "claude", "codex_cli": "codex", "gemini_cli": "gemini"}
    blocked = {id_to_key[pid] for pid, r in states.items()
               if r.state == ProviderState.AUTH_EXPIRED and pid in id_to_key}
    return [k for k in ("claude", "codex", "gemini") if k in blocked]
```

#### §3.3.2 `core/review_report.py:DocumentReviewSession.run_review`

```python
# §3.3.2.A — 진입 즉시 AUTH_EXPIRED 검사 (BLOCK #1 fix)
def run_review(self, documents, round_num=1, project_brief=None) -> ReviewReport:
    from core.review_runner import (
        detect_providers, detect_blocked_providers,
        run_aggregation, run_critic_review, run_cross_review,
        select_judge, select_review_pair,
    )

    # ── G5: 부분 만료 포함 BLOCK 우선 검사 (전체 상태 기준) ──
    blocked = detect_blocked_providers()
    if blocked:
        return self._empty_report(
            round_num, "BLOCK",
            f"인증 만료 provider: {', '.join(blocked)} — `<cli> login` 후 재시도",
        )

    providers = detect_providers()
    if not providers:
        # ── G4: SKIP은 PASS와 구분 (verdict 메트릭 보존) ──
        return self._empty_report(round_num, "SKIP", "사용 가능한 provider 없음 — T2/T3 검증 생략")

    # ── 이하 기존 로직 ──
    # §3.3.2.B — enterprise 게이팅 제거 (BLOCK #2/#3 → 다운스트림 §3.3.4 보강과 함께)
    # Before:  if self.level == "enterprise" and len(providers) >= 2:
    # After:
    cross_result = None
    if len(providers) >= 2:
        _, cross_provider = select_review_pair(providers)
        cross_result = run_cross_review(...)

    # Before:  if self.level == "enterprise" and critic_result:
    # After:   cross 있을 때만 judge 필요
    judge_result = None
    if cross_result and critic_result:
        raw_agg = run_aggregation(...)
        ...

    # dynamic + provider 1개 → critic만, judge=critic verdict (기존 fallback 유지)
```

> `level`은 이제 **`max_rounds` 산정에만 사용** (dynamic=1 / enterprise=2). cross 활성화는 provider 수로만 결정.

#### §3.3.3 `core/project_pipeline.py:977` — T1 QA work-item 문서 검사 추가

```python
# 헬퍼 추가 (BLOCK #6 fix — work_item_files는 path dict이므로 본문 로드 필요)
def _load_doc_contents(self, work_item_files: dict[str, str]) -> dict[str, str]:
    """{name: path} → {name: content} 변환. 읽기 실패는 빈 문자열."""
    out: dict[str, str] = {}
    for name, path in work_item_files.items():
        try:
            with open(path, encoding="utf-8") as f:
                out[name] = f.read()
        except OSError:
            out[name] = ""
    return out

# Before — line 977
gate_result = self.run_structural_gate(project_brief, "work_item")

# After — 기존 + work-item 문서 세트 추가 검사
gate_result = self.run_structural_gate(project_brief, "work_item")  # 기존 유지
work_item_doc_gate = self.run_structural_gate(
    {
        "documents": self._load_doc_contents(work_item_files),
        "project_brief": project_brief,
    },
    "work_item_doc_set",
)
if not work_item_doc_gate.get("pass"):
    _safe_print(f"[Pipeline] T1 QA work-item gate failed: {work_item_doc_gate.get('errors')}")
    # T1 retry: 1회만, _refine_document 재사용 (자세한 호출 패턴은 implementation 단계)
```

#### §3.3.4 SKIP verdict 다운스트림 처리 (BLOCK #2, #3, #10 fix)

SKIP을 PASS와 동일하게 통과 처리하도록 **3개 다운스트림 동시 패치**:

##### A. `core/project_pipeline.py:1011-1029` (호출자 분기)

```python
# Before:
_verdict = (_report.judge.verdict if _report.judge else "PASS")
if _verdict == "PASS":
    _rpath = _report.save(target_workspace)
    cross_review_result = {"verdict": "PASS", "confidence": 1.0, ...}
    break
if _verdict == "WARN" or _round == _session.max_rounds:
    cross_review_result = {"verdict": "WARN", "confidence": 0.6, ...}
    break

# After:
_verdict = (_report.judge.verdict if _report.judge else "PASS")
if _verdict in ("PASS", "SKIP"):
    _rpath = _report.save(target_workspace)
    cross_review_result = {
        "verdict": _verdict,
        "confidence": 1.0,    # SKIP도 통과 처리, pipeline_quality에서 별도 매핑 (§3.3.4.C)
        "report_path": _rpath if _verdict == "PASS" else "",
    }
    break
if _verdict == "WARN" or _round == _session.max_rounds:
    cross_review_result = {"verdict": _verdict, "confidence": 0.6, ...}
    break
# BLOCK은 retry 진입 (기존 fix_instructions 흐름 유지)
```

##### B. `skills/evaluator/doc_qa/skill.py:99-132` (Skill 레이어 동일 패치)

```python
# Before line 99-104:
verdict = report.judge.verdict if report.judge else "PASS"
if verdict == "PASS":
    break
if verdict == "WARN" or round_num == session.max_rounds:
    break

# After:
verdict = report.judge.verdict if report.judge else "PASS"
if verdict in ("PASS", "SKIP"):
    break
if verdict == "WARN" or round_num == session.max_rounds:
    break

# Before line 132:
"confidence": 1.0 if final_report.judge.verdict == "PASS" else 0.6,

# After:
"confidence": 1.0 if final_report.judge.verdict in ("PASS", "SKIP") else 0.6,
```

docstring(line 48 `verdict: "PASS" | "WARN" | "BLOCK"`)에 `| "SKIP"` 추가.

##### C. `core/pipeline_quality.py:62` (verdict 점수 매핑 — BONUS #10 fix)

```python
# Before:
_VERDICT_SCORE_MAP = {"PASS": 1.0, "WARN": 0.6, "BLOCK": 0.2}

# After:
_VERDICT_SCORE_MAP = {"PASS": 1.0, "SKIP": 1.0, "WARN": 0.6, "BLOCK": 0.2}
# SKIP → 1.0으로 매핑: 미검증이지만 통과 간주 (§3.5 상태 행렬과 정합).
# evaluate()에서 cross_v["verdict"] == "SKIP"일 때 cv_score 계산이 PASS와 동일.
```

> **이유**: §1.2 D4 "메트릭 오염 방지"가 SKIP 도입의 명분이지만, `pipeline_quality.py:62`를 안 건드리면 SKIP 산출물이 `_VERDICT_SCORE_MAP.get("SKIP", 0.0)`으로 BLOCK(0.2)보다 낮게 평가됨 — 의도와 정반대. 본 변경으로 일관성 확보.

### §3.4 RubricCompiler 신규 artifact_type — `work_item_doc_set`

> **위치 정정 (BLOCK #5)**: rubric 정의는 `core/rubric_compiler.py`가 아니라 **`rubrics/work_item_doc_set.yaml` 신규 파일**에 작성. `_load_rubric_for_type` 이 `rubrics/` 디렉토리를 자동 스캔하므로 코드 변경 없이 인식됨.

#### §3.4.1 `rubrics/work_item_doc_set.yaml` (신규 파일)

```yaml
name: "Work-Item Document Set Quality"
artifact_types:
  - work_item_doc_set

dimensions:
  - name: completeness
    weight: 0.25
    levels:
      5: "feature-plan, feature-spec, implementation-tasks, approval-gate 4종 모두 존재 + 본문 ≥ 200자"
      3: "4종 중 1개 빠짐 또는 본문 < 200자 1건"
      1: "4종 중 2개 이상 빠짐"
    evidence_checks:
      - field: "documents"
        rule: "doc_set_present"     # 신규 rule (rubric_compiler.py에 핸들러 추가)
        value: ["feature-plan.md", "feature-spec.md", "implementation-tasks.md", "approval-gate.md"]

  - name: requirements_mapping
    weight: 0.30
    levels:
      5: "feature-spec.acceptance_criteria가 project_brief.deliverables를 100% 커버"
      3: "≥ 60% 커버"
      1: "< 60% 커버"
    evidence_checks:
      - field: "documents.feature-spec.md"
        rule: "covers_deliverables"
        description: "project_brief.deliverables의 키워드가 feature-spec 본문에 등장하는 비율"

  - name: edge_cases
    weight: 0.20
    levels:
      5: "feature-spec 본문에 '엣지|예외|실패|edge|error|risk' 키워드 ≥ 3건 또는 명시적 risks 섹션"
      3: "1~2건"
      1: "0건"
    evidence_checks:
      - field: "documents.feature-spec.md"
        rule: "keyword_count_min"
        value: 3
        keywords: ["엣지", "예외", "실패", "edge", "error", "risk"]

  - name: consistency
    weight: 0.15
    levels:
      5: "feature-plan과 feature-spec의 phase/task 수 ±1 이내 일치"
      3: "±3 이내"
      1: "차이 ≥ 4"
    evidence_checks:
      - field: "documents"
        rule: "phase_count_match"
        tolerance: 1

  - name: traceability
    weight: 0.10
    levels:
      5: "implementation-tasks의 모든 task가 feature-spec 섹션 번호(§N)를 참조"
      3: "≥ 60%"
      1: "< 60%"
    evidence_checks:
      - field: "documents.implementation-tasks.md"
        rule: "task_section_ref_ratio"
        threshold: 0.6

# §3.4.2 임계값 정정 (BLOCK #4 fix — raw 1~5 스케일이 표준)
thresholds:
  pass: 4.0                  # weighted_avg ≥ 4.0 → status = "pass"
  pass_with_warnings: 3.0    # weighted_avg ≥ 3.0 → status = "pass_with_warnings"
                             # < 3.0 → status = "fail"
```

> **rubric_compiler.py 변경**: `evidence_check.rule` 값으로 `doc_set_present`, `covers_deliverables`, `keyword_count_min`, `phase_count_match`, `task_section_ref_ratio` 5종 핸들러를 추가해야 함. 기존 `all_have_owner`, `min_count` 패턴 따라 dispatch table 확장.

### §3.5 Verdict 상태 행렬

| 상황 | T1 | T2 | T3 | 종합 verdict | confidence | quality_score 매핑 |
|---|---|---|---|---|---|---|
| 모든 provider AVAILABLE 2+, 모두 통과 | PASS | PASS | PASS | PASS | 1.0 | 1.0 |
| Critic만 가능 (provider 1개) | PASS | PASS | SKIP | PASS | 1.0 | 1.0 |
| AVAILABLE 0개 (T2/T3 모두 SKIP) | PASS | SKIP | SKIP | SKIP | 1.0 | 1.0 |
| AUTH_EXPIRED 1개 이상 (부분 만료 포함) | * | * | BLOCK | BLOCK | 0.0 | 0.2 |
| T1 FAIL → retry → 여전히 FAIL | FAIL | - | - | BLOCK | 0.0 | 0.2 |
| T2 BLOCK → retry → 여전히 BLOCK | PASS | BLOCK | * | BLOCK | 0.0 | 0.2 |

### §3.6 Retry 범위

| 옵션 | 범위 | 비용 | 채택 |
|---|---|---|---|
| A | T1/T2 BLOCK → WorkItemGenerator만 재실행 | 작음 | ✅ |
| B | A + Brief 재생성 | 큼 (LLM 호출 2~3배) | ❌ |
| C | retry 없음 | 가장 작음 | ❌ — UX 저하 |

**채택: A** — `_refine_document` (이미 review_report.py 호출 흐름에 존재) 재사용. max 1회 (T1) + max_rounds (T2/T3 — dynamic=1, enterprise=2).

### §3.7 환경변수 정책 (BLOCK #7 fix)

**신규 환경변수 도입 X (NG4 정합).** 기존 `AF_SKIP_PROVIDER` 재사용:

```bash
# 전체 비활성화 (T2/T3 모두 SKIP, T1만 작동)
AF_SKIP_PROVIDER=claude_cli,codex_cli,gemini_cli

# Cross만 비활성화 (claude는 critic용으로 살림)
AF_SKIP_PROVIDER=codex_cli,gemini_cli
```

`AF_SKIP_PROVIDER`는 `provider_detect.py:_parse_skip_providers`에서 이미 처리됨 — 마스킹된 provider는 `NOT_INSTALLED`로 반환되어 `detect_providers()` 결과에서 자연 제외.

### §3.8 Dynamic 사용자 비용 영향 (advisory ACCEPT-ADV #8)

| level | 변경 전 (critic 1회) | 변경 후 (critic + cross + judge) | latency 증가 (estimated) |
|---|---|---|---|
| dynamic | 1× LLM call (~30~60s) | 최대 3× LLM call | ~+60s 평균, 최악 +120s |
| enterprise | 3× LLM call × 2 rounds | 동일 (변경 없음) | 0 |

> dynamic 사용자가 latency 늘어남을 원치 않으면 `AF_SKIP_PROVIDER`로 cross provider만 마스킹 가능 (§3.7).

## §4 영향 범위 (Blast Radius)

| 파일 | 변경 종류 | 위험도 |
|---|---|---|
| `core/review_runner.py:37` | `detect_providers` 위임 + `detect_blocked_providers` 추가 | 중 — 기존 호출자 동작 변경 |
| `core/review_report.py:241+` | AUTH_EXPIRED 진입 검사, enterprise 게이팅 제거, SKIP verdict 추가 | 중 — verdict 분기 영향 |
| `core/project_pipeline.py:977,1011` | T1 work-item gate 추가, SKIP verdict 분기 | 중 — 핵심 흐름 |
| `core/rubric_compiler.py:124+` | evidence_check rule 5종 핸들러 추가 | 중 — dispatch 확장 |
| `rubrics/work_item_doc_set.yaml` | **신규 파일** | 저 |
| `skills/evaluator/doc_qa/skill.py:99,132` | SKIP verdict 분기 동기화 | 중 — Skill 레이어 |
| `core/pipeline_quality.py:62` | `_VERDICT_SCORE_MAP`에 SKIP 추가 | 저 — 단순 dict |
| `.claude/agents/af-doc-qa.md` | SKIP verdict 명세 추가 (문서) | 저 — 문서만 |
| Master_Blueprint.md | §3 ProjectPipeline + §11 verdict 코드 | 필수 동시 갱신 |
| 테스트 | 신규 7건 (§5 참고) | 저 |

## §5 테스트 계획

| # | 케이스 | 검증 항목 |
|---|---|---|
| 1 | T1 PASS 경로 | work_item_doc_set rubric ≥ 4.0 → T2 진입 |
| 2 | T1 FAIL → retry → PASS | `_refine_document` 1회 호출 후 재평가 통과 |
| 3 | T1 FAIL → retry → FAIL | BLOCK verdict, exception 안전 처리 |
| 4 | Provider 0개 | T2/T3 SKIP, 종합 PASS, `cross_review_result.verdict == "SKIP"` |
| 5 | AUTH_EXPIRED 1개 (부분 만료) | T2 진입 즉시 BLOCK, 메시지에 `<cli> login` 안내 (G5) |
| 6 | Provider 1개 (AVAILABLE) | critic 실행, cross SKIP, 종합 PASS |
| 7 | Provider 2+ AVAILABLE | critic + cross + judge 실행, dynamic 레벨에서도 동작 (G2) |
| 8 | SKIP downstream | `pipeline_quality.evaluate()`가 SKIP을 1.0으로 매핑하는지 |
| 9 | doc_qa skill SKIP 처리 | `skill.py` 결과 dict의 `confidence == 1.0` |

## §6 마이그레이션 / 롤백

- 환경변수 가드: `AF_SKIP_PROVIDER`로 전체/부분 비활성화 (§3.7)
- 롤백: 본 설계의 변경 7개 파일 git revert만으로 원복 — 스키마/DB 변경 없음
- 신규 파일 `rubrics/work_item_doc_set.yaml` 삭제하면 `_load_rubric_for_type`이 None 반환 → `RubricCompiler.evaluate()`가 warning만 남기고 계속 진행 (graceful degrade)

## §7 미해결 / 후속 작업

- **F1** Tier 2/3 prompt 파일(`scripts/prompts/doc_critic.txt` / `doc_cross_review.txt` / `doc_aggregation.txt`)이 work-item rubric과 정합한지 검토 — 별도 작업
- **F2** `work_item_doc_set` rubric 임계값(pass=4.0)은 잠정. 실제 work-item 5개로 보정 필요
- **F3** EXE 배포 결정 후 `af.spec` `hiddenimports`에 `core.provider_detect` 등록 여부 재확인
- **F4** `pipeline_quality.py:62` SKIP=1.0 매핑이 long-term 메트릭(quality drift 추적)에 미치는 영향 — 6개월 운영 후 재평가

## §8 변경 이력

- 2026-05-07 v1 — 초안 (Opus 4.7)
- 2026-05-07 v2 — af-cross-review BLOCK 9건 반영 (Opus 4.7):
  - High #1: AUTH_EXPIRED 검사 위치 → `run_review()` 진입 즉시 (§3.3.2.A)
  - High #2: SKIP verdict 다운스트림 — `project_pipeline.py:1011` 분기 보강 (§3.3.4.A)
  - High #3: SKIP verdict 다운스트림 — `doc_qa/skill.py:99,132` Blast radius 추가 (§3.3.4.B)
  - Med #4: rubric 임계값 0.7/0.5 → 4.0/3.0 (raw scale, §3.4.2)
  - Med #5: rubric 정의 위치 → `rubrics/work_item_doc_set.yaml` (§3.4.1)
  - Med #6: `_load_doc_contents` 헬퍼 시그니처 명시 (§3.3.3)
  - Med #7: `AF_LLM_JUDGE` 제거, `AF_SKIP_PROVIDER` 재사용 (§3.7)
  - Med-ADV #8: dynamic 사용자 비용 영향 추정 (§3.8)
  - Low-ADV #9: cross provider 순서 보존 명시 (§3.3.1)
  - Bonus #10: `pipeline_quality.py:62` SKIP=1.0 매핑 (§3.3.4.C)
