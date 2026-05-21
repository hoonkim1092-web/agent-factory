# AF Dogfooding 인프라 격차 분석 (2026-05-21)

> 작성: 2026-05-21 KST
> 작성자: Claude(Opus 4.7) 1차 → Codex 반박 → Claude 2차/3차 grep 검증
> 목적: "AF로 AF를 dogfooding 개발하기 위한 인프라가 충분한가" 결정
> 후속: 본 문서 채택 시 Step 0(a)+(b) 정합화부터 진입

---

## 0. 배경

사용자 질문: **"AF로 AF를 dogfooding 개발하기 위한 인프라 작업이 부족한게 있는지 분석"**

분석 흐름:
1. Claude 1차 분석 — 격차 카탈로그 작성 (G1~G6, R1~R9)
2. Codex 반박 — "이미 해결된 항목을 미해결로 남긴 게 섞여 있음"
3. Claude 2차 grep 검증 — Codex 주장 6/7 정확, Claude 원안 5/7 stale
4. Codex 추가 주장 2건 — `round_count<2`, agent 순서
5. Claude 3차 grep 검증 — round_count<2는 stale, agent 순서는 진짜 충돌

**메타 결론**: 양측(Claude/Codex) 모두 NEXT_STEPS/메모리/round*-friction.md 같은 시간경과 문서를 무비판 인용하는 stale baseline 함정에 한 번씩 빠짐. 분석 단계에서 grep 1차 반증 의무는 양측 모두에 적용.

---

## 1. 프레임 — G/R 축 분리

"dogfooding 개발 인프라"는 두 축이 섞여 있어 진단을 흐림. 분리 필요:

| 축 | 의미 | 진입점 |
|---|---|---|
| **G — 거버넌스 dogfooding** | AF 자신의 `.py` 변경을 AF의 거버넌스(3-tier review, hook, gate)가 검증 | `git commit` → `.githooks/pre-commit` → `review_gate.py` |
| **R — 자기-실행 dogfooding** | AF의 agent pipeline이 자기 `.py`를 작성/수정 | `agent_launcher.py "<task>" --workspace .` |

---

## 2. 격차 카탈로그 — 최종 판정 (grep 검증 기반)

### G축

| ID | 항목 | 현재 사실 (grep 증거) | 판정 |
|----|------|-----------------------|------|
| **G1** | `max_rounds` 코드/CLAUDE.md 불일치 + 리터럴 하드코드 | `check_pending_review.py:30` `MAX_ROUNDS = 2` + L9 주석 "Phase 0 정책 (2026-04-30 — Proof-Carrying Review 도입 전 단계)" vs CLAUDE.md:129 "max_rounds=5 캡". **추가**: `review_gate.py:282` `if int(state.get("round_count", 0)) < 2:` — 동일 의미를 리터럴 `2`로 하드코드 (MAX_ROUNDS 상수 미참조). G1 수정 시 함께 변경 필수 | **유효** — Step 0(a) |
| **G2** | `.codex/hooks.json` cli_hook_bridge 2중 등록 | NEXT_STEPS P2-F memory | 유효 (낮음) |
| **G3** | pytest registry mutate | `tests/conftest.py:18` setdefault + `:50` `monkeypatch.setenv("AF_DISABLE_REGISTRY_WRITE","1")` autouse + L41 주석 "F16 차단" | **이미 해결됨** |
| **G4** | `skill_manifest` capability_gap 보존 | `core/skill_retrieval_engine.py:39-44` `ReuseDecision.capability_gap` + `to_dict()` 직렬화 + `skill_procurer.py:814` 활용 + `project_pipeline.py:152` `_write_skill_manifest` 존재 | **부분 해결** (entries 주입 경로 추가 확인) |
| **G5** | `review_metrics_logger.span_days` 파일순서 의존 | `scripts/review_metrics_logger.py:279` `records[0]/records[-1]` | 유효 (낮음) — backlog |
| **G6** | CRLF/LF 영구 modified 6파일 | `projects/agent_factory/*.yaml` 이번 세션 직접 확인 (내용 동일) | 유효 — Step 1 |
| **G7 (NEW)** | **agent 실행 순서 정합** — test-first vs review-first | 핵심 충돌: `check_pending_review.py:60` `"af-test-runner → af-critic → af-cross-review"` (정상 Tier 2~3) vs CLAUDE.md L127 "**af-critic → af-cross-review → af-test-runner** 순서 (review-first pattern)". 부수 케이스: L51 (Tier 1 단독, 순서 무관), L56 (t3_skip 특수 분기 — `"af-test-runner → af-critic"`, 순서 일관성 동일 적용 필요) | **1급 결함** — Step 0(b). Codex 발견. |
| **G8 (NEW)** | **`check_design_pending.py` 안내 문구 정책 충돌** | `check_design_pending.py:9` 주석 + `:153` 실제 print `"af-critic + af-cross-review 에이전트를 병렬 실행해주세요."` vs CLAUDE.md L118 "**반드시** af-cross-review **1개만** 실행" + L119 "단일 설계문서 → af-cross-review만 (2026-05-01 변경: af-critic은 설계문서에서 소스 중복 탐색 비용만 발생, 효과 없음)" | **1급 결함** — 본 문서 작성 직후 자동 발화한 hook 메시지가 바로 이 코드의 산출물. cross-review가 발견. Step 0(d). |

### R축

| ID | 항목 | 현재 사실 (grep 증거) | 판정 |
|----|------|-----------------------|------|
| **R1** | self-run이 `.py` 수정 검증 한 적 없음 | Round 4 series(`docs/dogfooding/round4-*.md`) 전부 `.md` only | **핵심 미증명** — Step 3 |
| **R2** | git context "adherence" (산출물 반영) | `core/providers/cli.py:598-637` `_collect_git_context()` HEAD/branch/log -5/status 주입 ✅ 그러나 F10 staleness 산출물 발현 | 재분류: injection→adherence backlog |
| **R3** | scope guard (allowlist) | 명확한 파일 allowlist 컨트랙트 없음 | 유효 — Step 3과 묶음 |
| **R4** | gemini_cli race 매 run 2~4s 낭비 | F11/F6 | 유효 (낮음) |
| **R5** | skill 식별 LLM cost 누수 | F13 | 유효 (낮음) |
| **R6** | `prompt_mission_template` NameError | `agent_launcher.py:883` `from core.template_input import prompt_mission_template` (lazy import, L880-882 주석으로 의도 명시) | **이미 해결됨** |
| **R7** | telemetry 자동 수집 | 수동 friction log | 유효 — R1 이후 |
| **R8** | frozen `af.exe` self-run 미검증 | dev only | 유효 — R1 이후 |
| **R9** | sandbox 격리 환경 없음 | real repo + real provider | 유효 — R1 이후 |

### 폐기 항목 (분석 과정에서 발견)

| ID | 폐기 사유 |
|----|----------|
| ~~`review_gate.py:214 round_count<2`~~ | grep `No matches found`. NEXT_STEPS Round 2 메모에서 stale 인용. 진짜 구현은 `check_pending_review.py:135` `round_count >= 1 and not has_block` (이미 CLAUDE.md L131과 정합) |

---

## 3. 진단 (사실 기반)

**G축은 "충분히 작동"이 아니라 "정합화 1건 필요" + "noise cleanup 2건"**:
- G7 (agent 순서 모순) — 매 commit hook이 출력하는 `[af-review-pending] 실행 에이전트:` 라인이 사용자/Claude에게 직접 명령하는데, 그 명령이 CLAUDE.md 정책과 반대 방향. 1급
- G1 (max_rounds 2 vs 5) — 두 진실. 정책 단계 boundary 결정 필요
- G6 (CRLF) — renormalize 1회로 영구 해결

**R축은 "인프라 부족"이 아니라 "사명 미증명"**:
- Round 4 series 전부 `.md` only. AF가 자기 `.py`를 수정하는 self-run이 한 번도 통과한 적 없음
- R7/R8/R9 (telemetry/frozen/sandbox) 인프라 투자는 R1 가치 증명 없이 정당화 불가
- 메모리 `project_dev_workflow_paradigm_shift`에 사용자가 이미 명시: "AF dogfooding — 실패/마찰 지점 기록만" — R축 ROI를 낮게 평가한 결정 기록 있음

---

## 4. 정합화된 실행안

```
Step 0 — 정책 정합 (네 항목 동시, dogfooding R축 진입 전 필수)
  세 항목 모두 "코드 vs CLAUDE.md" 정합 갭. 동일 sprint(2026-05-13) 갱신 누락 패턴.

  (a) G1 max_rounds 단계 boundary 추적
      cmd: git log -p --follow CLAUDE.md | grep -B5 -A3 "max_rounds=5"
      판정 1 (Phase 1 의도): MAX_ROUNDS=5로 + review_gate.py:282 `< 5`로
                            + check_pending_review.py 테스트 갱신
                            + WARN-only no-fire 조건 재검토
      판정 2 (drift): CLAUDE.md L129를 2로 정정
      추정: 코드 주석이 "Phase 0 정책"으로 명시 → 판정 2 확률 ↑
      필수 동반: review_gate.py:282 리터럴도 함께 정합 (상수 참조로 개선 권고)

  (b) G7 agent 순서 정합 ← 1급 결함, 우선순위 (a)와 동등
      cmd: git log -p scripts/check_pending_review.py | grep -B3 "af-test-runner.*af-critic"
      cmd: git log -p CLAUDE.md | grep -B5 "review-first pattern"
      판정 1 (review-first 정책): check_pending_review.py:60 순서 뒤집기
                                  + L56 t3_skip 분기도 동일 순서로 정합
                                  + _agents_for_tier 시그니처 갱신
                                  + 회귀 테스트
      판정 2 (test-first 운영): CLAUDE.md L127 정정 (+ pattern 이름 변경)
      추정: review-first가 정책 의도일 가능성 ↑
            (test가 review를 막아 cycle 늘림 — Phase 0 cost 감축 정신과 충돌)
            단 이건 추정 — git history로 확정 필요

  (c) check_pending_review.py:56 t3_skip 분기 — (b) 채택 시 함께 적용
      현재: "af-test-runner → af-critic"
      review-first 채택 시: "af-critic → af-test-runner"

  (d) G8 check_design_pending.py 안내 문구 정합 ← 1급 결함
      현재 코드(2 군데):
        :9   주석   "af-critic + af-cross-review를 병렬 실행"
        :153 print "af-critic + af-cross-review 에이전트를 병렬 실행해주세요."
      정책(CLAUDE.md L118/119): "af-cross-review 1개만"
      판정 (단일 진실): 정책이 2026-05-01 변경으로 af-critic 제거를 명시 → 코드 정정
      cmd 수정 후 검증: hook output에서 "af-cross-review 1개만" 안내 확인

Step 1 — G6 dirty YAML renormalize
  diff 줄바꿈뿐 확인 (이번 세션 이미 검증)
  git add --renormalize projects/agent_factory/   # 1회로 영구
  검증: 다음 세션 git status 깨끗

Step 2 — R2/G2/G4/G5는 backlog 분리
  R2: "git context adherence" 이름 + 산출물 검증 테스트 contract 명확화
  G2/G4/G5: 영향도 낮음, 본 sprint 외

Step 3 — R1 .py self-run 실험 설계 (Step 0/1 후)
  조건:
   - 대상: trivial .py 1개 (예: core/utils.py docstring 1줄 추가)
   - 별도 worktree (현재 worktree 오염 차단)
   - AF_DISABLE_REGISTRY_WRITE=1
   - runtime_workspace 분리 확인
   - R3 scope guard 동시 — allowed_paths=["core/utils.py"] report-only
   - 실행 후 git diff --name-only로 scope leak 측정
  비목표: 큰 .py 변경, multi-file, 실제 기능 변경

Step 4 — R7/R8/R9 결정
  R1 결과가 "AF가 .py 쓸만함" 신호를 줄 때만 telemetry/frozen/sandbox 투자
  신호 없으면 사용자 정책(메모: "실패/마찰 지점 기록만") 유지
```

---

## 5. 메타 교훈 — 분석 도구의 stale baseline 함정

본 분석 과정에서 양측 모두 동일 함정에 빠짐:

| 분석자 | stale 항목 | 원인 |
|--------|-----------|------|
| Claude 1차 | G3/G4/R6 "미해결" 주장 / G1 방향 / R2 진단 | NEXT_STEPS와 메모리만 읽고 grep 안 함 |
| Codex 2차 | `review_gate.py:214 round_count<2` 주장 | NEXT_STEPS Round 2 메모 무비판 인용, grep 없음 |

→ **공통 패턴**: 시간 경과한 문서(NEXT_STEPS, round*-friction.md, 메모리)를 인용할 때 그 시점 코드가 현재 코드와 같다고 가정.

**예방책**:
1. 메모리/NEXT_STEPS 인용 시 grep 1차 반증 의무를 양쪽 분석자 모두에 적용
2. 문서에 인용하는 라인 좌표는 같은 turn에서 grep으로 재캡처
3. "이미 해결됨/미해결" 판정은 반드시 현재 코드 발췌와 함께 제시
4. **"코드 vs 정책 문서" 정합 갭 별도 점검** — 본 문서 G1/G7/G8이 모두 동일 패턴: 코드는 grep으로 검증되지만, 그 코드가 *현재 정책 문서(CLAUDE.md)와 일관되게 정합*된 상태인지는 별도 dimension. stale baseline 함정이 "과거 문서 vs 현재 코드"만이 아니라 "현재 코드 vs 현재 정책 문서" 간 불일치에서도 발생함

이 교훈은 메모리 `feedback_cross_review_stale_baseline_repeat`(spec churn 4라운드+에서 cross-review가 §11 row 부재 등 잘못 BLOCK 보고)와 같은 패턴. **단순 cross-review 한정이 아니라 "메모/NEXT_STEPS 인용 전반 + 코드-정책 정합"으로 일반화 필요.**

**경험적 관찰** (본 문서 라운드에서): 동일 sprint(2026-05-13)에서 CLAUDE.md를 갱신했지만 `scripts/check_pending_review.py`와 `scripts/check_design_pending.py`의 안내 문구는 갱신 누락 — G7과 G8이 같은 누락 패턴. **CLAUDE.md 정책 변경 시 영향 받는 hook 안내 문구 파일들을 체크리스트화**할 가치 있음 (별도 backlog).

---

## 6. 후속 행동

본 문서 채택 시:

1. **Step 0(d) 즉시** — G8 `check_design_pending.py` 안내 문구 정합 (1줄 fix, 현재 hook이 잘못된 안내를 송출 중. 영향 즉발)
2. **Step 0(b)** — agent 순서 정합 결정 (G7, 매 commit hook이 사용자에게 명령)
3. **Step 0(a)** — max_rounds 단계 boundary 결정 (G1, review_gate.py:282 영향 범위 동반)
4. **Step 1** — CRLF renormalize (G6)
5. **사용자 결정 게이트** — Step 3(R1 .py self-run 실험) 진입 여부

> 우선순위 근거: G8 > G7 > G1
> - G8은 **본 문서 작성 자체로 이미 잘못된 hook 안내가 발화**한 결함 (사용자가 직접 목격)
> - G7은 매 .py commit 후 자동 발화하는 안내 — 빈도는 높지만 G8보다 사용자 인지 어려움
> - G1은 정책 결정 동반 (boundary 추적 시간 필요)

본 문서 자체는 분석 문서 → CLAUDE.md "단일 설계문서" 룰상 작성 후 `af-cross-review` 1회 자동 발화 대상. **실제 발화 결과(BLOCK 1건 + WARN 2건)는 본 문서에 이미 흡수됨**: G8 신규 추가 (BLOCK F2), G1 영향 범위 확장 (WARN F3), G7 라인 좌표 정확화 (WARN F1), §4·§6 일관성 통일 (ADVISORY F7), §5 메타 교훈 보강 (ADVISORY F8).
