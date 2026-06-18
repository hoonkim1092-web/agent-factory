# 리뷰 합의 게이트 — 증거 기반 finding 판정 + 수렴 가드 설계

**날짜**: 2026-06-19
**상태**: Draft
**작성자**: Claude Opus 4.8
**연관**: `.claude/agents/af-cross-review.md`(Tier 3), `docs/2026-05-03-phase2-verdict-label-spec.md`(verdict 매핑), `INSTRUCTIONS.md`(멀티프로바이더 SSOT)

---

## §1 배경 및 동기

### §1.1 두 개의 서로 다른 실패

2026-06-19 설계문서 1건(`docs/2026-06-18-user-perspective-qa-pipeline-design.md`)에 대한 cross-review가 **5라운드 연속 BLOCK** 후 캡으로 종료됐다. 복기 결과 **두 개의 독립적 실패**가 드러났다.

**실패 B — 자기유발 수렴 실패 (이번 루프의 직접 원인)**

| 라운드 | BLOCK | 누가 유발 |
|---|---|---|
| 1 | §2.5 사실오류 + INV-Q4 enforcement 미명시 | 원본 |
| 2 | §10 Q-S1 의존 누락 + snapshot 경로 미정의 | 원본 + R1 수정 |
| 3 | §10 goal_contract.json 배정 누락 | **R2 수정** |
| 4 | 저장 시점 모호 + AcceptanceGate가 REVIEW 단절 | **R3 수정** |
| 5 | §3↔§10 정면 모순 + pipeline.run() 분해 미명시 | **R4 수정** |

각 라운드 지적은 **전부 실재하는 모순**이었고, 그 모순을 **직전 라운드의 내 수정이 만들었다.** 미래 구현 슬라이스(Q-S4)의 *구현 방법(HOW)*을 *설계문서(WHAT)* 안에서 완전 명세하려다 발생한 자기유발 진동. **팩트 검증으로는 못 막는다 — 모순이 진짜였으므로 합의기가 돌았어도 전부 ACCEPT로 확증했을 것이다.**

**실패 A — 증거 미수집 (코드 리뷰의 구조적 결함)**

cross-review가 finding을 낼 때 연결된 코드(caller/callee/test)를 충분히 보지 않고 판정 → 가짜 BLOCK + 사이드이펙트 놓침. 지침(`af-cross-review.md`)에 "§5 Direct Callers를 1차 근거로 삼아라"가 이미 있으나 **LLM이 건너뛴다 — 지침은 강제가 아니다.**

### §1.2 핵심 통찰 (사용자, 2026-06-19)

1. **합의 LLM이 근거를 팩트로 합의해야 한다** — finding이 사실인지 검증하는 단계가 게이트에 없다.
2. **코드 기능 구현에도 적용** — 설계문서만이 아니다.
3. **수정된 부분만 보면 안 된다. 연결된 부분을 모두 봐야 사이드이펙트가 안 난다.**
4. **지침만으로는 LLM이 안 따른다** — 강제는 코드여야 한다.
5. **멀티프로바이더(Claude/Codex/Gemini) 전부 적용** — `.claude` 전용 금지.

> **통찰 4+5의 수렴**: 합의 로직을 `INSTRUCTIONS.md` 산문에 두면 프로바이더마다 다르게 해석한다. **Python 코드에 두면 어느 프로바이더가 게이트를 돌리든 같은 코드가 실행 = 프로바이더 중립이 구조적으로 보장된다.** 멀티프로바이더 제약 자체가 "산문 말고 코드로"를 강제한다.

### §1.3 두 해법의 분리

- 실패 B → **수렴 가드 + 스코프 게이트** (싸고 즉효, §4)
- 실패 A → **증거수집 합의기** (코드 리뷰 한정, §5)

서로 다른 문제이므로 해법도 분리한다. 합의기는 실패 B를 못 막고, 수렴 가드는 실패 A를 못 막는다.

---

## §2 현재 코드 진단 (grep 확정)

### §2.1 라운드 발화 — 코드 리뷰엔 캡, 설계문서엔 없음

**코드 리뷰 경로** (`scripts/check_pending_review.py`):
- 상태 파일: `.af_review_queue/pending_agent_review.json`, 필드 `round_count`/`round_started_at`/`last_round_summary`/`fired_at`
- `MAX_ROUNDS = 5` (`:30`) 강제 (`:160-173`):
  ```python
  if round_count >= MAX_ROUNDS:
      if not data.get("capped_notified_at"):
          print(f"[af-review-capped] round_count={round_count} >= MAX_ROUNDS={MAX_ROUNDS}. ...")
          ...
      return
  ```
- WARN-only 억제 (`:176-204`): `round_count >= 1 and not last_summary.get("has_block")` → 재발화 보류
- round_count 증가: `review_gate.py:503` `state["round_count"] = int(state.get("round_count", 0)) + 1`
- verdict 파싱: `review_gate.py:57-78` `_extract_verdict_from_content()` (fence 우선 + last-position)

**설계 문서 경로** (`scripts/check_design_pending.py` + `check_staged_design_review.py`):
- **라운드 카운트 메커니즘 없음.** timestamp debounce(`:128-140`)만 — `ts > last_fired_at`면 재발화.
- BLOCK 차단은 `check_staged_design_review.py:201-213` 단일 지점, "최신 리뷰가 BLOCK 덮음" 방식(`:66-70`).
- **캡 없음 + 수렴 가드 없음 = 무한 재수정 가능.** ← 실패 B의 근본원인.

### §2.2 증거 수집 — finding 단위 API 부재

**`core/review_bundle.py`**:
- `_find_direct_callers()` (`:252-293`): **grep 기반 1-hop**, `core/`+`scripts/`만, `symbol(` 패턴
  ```python
  r = subprocess.run(["grep", "-rn", "--include=*.py", f"{sym}(", d], ...)  # :266-269
  ```
- **callee(피호출자) 미수집** — `grep callee` 0건 확인
- `_find_related_tests()` (`:203-238`): `tests/test_*.py`에서 모듈명/심볼 grep
- **입력 = `pending_files` 전체 리스트** (`build_full(workspace, pending_files)` `:362`). **특정 finding의 file:line을 받아 그 주변 증거를 뽑는 API는 없다.**

### §2.3 finding 형식 — 산문, 기계 비가독

- finding = **마크다운 산문**: `#### N. [라벨] [Severity] 제목` + `**대상 코드**: file:line` (산문)
- 라벨 5종(`[ACCEPT]`/`[ACCEPT★]`/`[ACCEPT-ADV]`/`[REJECTED]`/`[BONUS]`), severity 4종 (`phase2-verdict-label-spec.md:164-176`)
- **소비되는 건 fence 안 verdict 1줄뿐** (`review_gate.py:57-78`). 개별 finding의 ACCEPT/REJECT·file:line을 구조적으로 추출하는 코드는 **없다.**

> **설계 함의**: 합의기가 finding 단위로 동작하려면 (1) cross-review가 **구조화 사이드카(JSON)** 를 추가 출력하거나 (2) 합의기가 산문에서 `**대상 코드**: file:line`을 파싱해야 한다. §5.2에서 (1)을 택한다(파싱 취약성 회피).

### §2.4 멀티프로바이더 지침 SSOT

- `INSTRUCTIONS.md` = 공통 SSOT → `sync_provider_instructions.py` → `CLAUDE.md`/`AGENTS.md`/`GEMINI.md` 마커 주입(pre-commit 강제)
- 에이전트 정의: `.claude/agents/*.md` ↔ `.codex/agents/*.toml` (병행 — Gemini는 `GEMINI.md` 본문 의존)

---

## §3 설계 원칙 (불변식)

**INV-1 (강제는 코드, 판단은 LLM)**
증거 수집·라운드 카운트·스코프 분류는 **코드**가 강제한다(LLM이 건너뛸 수 없음). ACCEPT/REJECT *판정*만 LLM이 한다. 지침 산문에 "검증하라"고 적고 LLM 자율에 맡기지 않는다.

**INV-2 (프로바이더 중립)**
합의·수렴 로직은 Python 스크립트에 둔다. 어느 프로바이더가 게이트를 돌려도 동일 코드가 실행된다. 프로바이더별 분기 금지(필요 시 `provider_detect` SSOT 경유).

**INV-3 (수렴 안전 — 자기유발 진동 차단)**
같은 산출물에 대한 자동 재발화는 **유한 캡**을 가진다. 캡 도달 또는 "직전 수정이 유발한 BLOCK" 감지 시 **자동 재수정 중단 + 사람 에스컬레이션**. 설계문서도 코드와 동일하게 캡을 가진다(현재 부재).

**INV-4 (스코프 = WHAT vs HOW)**
설계문서 리뷰에서 *구현 방법(HOW)* 의 미명세·모순은 BLOCK이 아니라 **"구현 슬라이스에서 결정" advisory**로 강등한다. BLOCK은 *문서가 내린 결정 자체*의 사실오류·논리모순에만 부여한다.

**INV-5 (연결 코드 의무 — 사이드이펙트)**
코드 리뷰 finding은 caller(1-hop 이상)·callee·관련 테스트 증거가 **수집된 상태로** 판정된다. 증거 미수집 finding은 ACCEPT 불가(UNVERIFIED 처리).

**INV-6 (메타-재귀 경계)**
합의기는 **코드 리뷰에만** 적용한다. 합의기 자체를 합의기로 검증하는 무한 재귀, 내부 파이프라인 배관의 끝없는 확장을 금지한다(메모리 `project_dev_workflow_paradigm_shift`, 게이트 효율 논의 결론: 일상은 표적검증, core/보안만 풀 3-Tier).

---

## §4 실패 B 해법 — 수렴 가드 + 스코프 게이트

### §4.1 설계문서 라운드 캡 (코드 경로와 동형화)

`check_design_pending.py`에 라운드 카운트를 도입한다. 현재 `.design_review_fired.json`(`:29`)을 확장:

```
.af_review_queue/.design_review_fired.json
{
  "<review_doc_basename>": {
    "fired_at": <float>,
    "round_count": <int>,        # 신규
    "last_verdict": "block|warn|pass"  # 신규 — check_staged_design_review가 기록
  }
}
```

- `MAX_DESIGN_ROUNDS = 3` (설계는 코드보다 낮게 — HOW 진동 조기 차단)
- `round_count >= MAX_DESIGN_ROUNDS` → 자동 재발화 중단 + `[af-design-review-capped]` 안내(코드 경로 `:160-173` 미러)

> **결정**: 코드 5 / 설계 3. 설계문서는 "사용자 안내" 정책(CLAUDE.md)이 이미 있으므로 캡을 낮춰 사람 의사결정을 더 일찍 부른다.

### §4.2 수렴 감지 — "직전 수정이 유발한 BLOCK"

완전 자동 판정은 어렵다(텍스트 의미 비교 필요). **근사 신호**를 쓴다:

- 라운드 N의 BLOCK verdict + 라운드 N-1도 BLOCK + 두 리뷰의 **대상 섹션(§N)이 겹침** → 진동 의심
- 신호 발생 시 `round_count`와 무관하게 즉시 `[af-design-review-oscillation]` 안내:
  ```
  직전 라운드 수정이 같은 섹션에 새 BLOCK을 유발했습니다(진동 의심).
  자동 재수정을 중단합니다. 다음 중 택일:
    - HOW 디테일이면: 해당 항목을 "구현 시 결정"으로 강등(§4.3)
    - 진짜 논리결함이면: 사용자가 직접 결정
  ```
- 섹션 겹침 추출: 리뷰 verdict 사유 줄에서 `§\d+` 토큰 집합 교집합(코드, 휴리스틱). 빈 교집합이면 진동 아님으로 간주(false-positive 회피).

### §4.3 스코프 게이트 — HOW 강등 (INV-4)

cross-review 지시문(`af-cross-review.md` + 멀티프로바이더 프롬프트)에 **설계문서 한정 분류 규칙** 추가:

- 대상이 설계문서(`docs/*.md` 설계)일 때, finding이 *미래 구현 슬라이스의 방법론*(저장 경로 선택, 함수 분해 순서, 직렬화 포맷 등)이면 → `[ACCEPT-ADV]`(WARN) 강등, BLOCK 금지.
- *문서가 내린 결정의 사실오류·논리모순*(존재하지 않는 코드 참조, 섹션 간 정면 모순, 잘못된 커밋/라인)이면 → BLOCK 유지.

> 이 분류는 지침이지만, §4.1 캡이 **백스톱**이므로 LLM이 분류를 틀려도 무한 진동은 코드가 막는다(INV-1 정신: 코드가 안전망).

---

## §5 실패 A 해법 — 증거수집 합의기 (코드 리뷰 한정)

### §5.1 흐름

```
cross-review (Discovery)
   ├─ 산문 리포트 (사람용, 기존 유지)
   └─ findings.json (기계용, 신규 사이드카)     ← §5.2
        ↓
scripts/review_consensus.py (코드)              ← §5.3
   각 finding의 file:line →
     _collect_evidence(file, line):
        callers (1-hop, 기존 _find_direct_callers 재사용)
        callees (신규 — §5.4)
        related tests (기존 _find_related_tests 재사용)
        surrounding code (±N줄)
   → evidence_pack.json
        ↓
합의 LLM (consensus judge)                       ← §5.5
   evidence_pack만 입력 → 각 finding ACCEPT/REJECT/UNVERIFIED
   증거에 없는 근거로 판정 금지 (INV-5)
        ↓
verdict 집계 (기존 phase2-spec §4.4 재사용)
   ACCEPT만 BLOCK 기여. REJECT/UNVERIFIED 제외.
```

### §5.2 구조화 finding 사이드카

cross-review가 산문 리포트와 **함께** `.af_review_queue/cr_findings.json`을 출력:

```json
{
  "round": 3,
  "findings": [
    {"id": "F1", "label": "ACCEPT", "severity": "High",
     "title": "...", "file": "core/xxx.py", "line": 123,
     "claim": "왜 결함인가 한 줄"}
  ]
}
```

- 산문은 사람·감사용으로 유지(기존 형식 불변). JSON은 합의기 입력.
- cross-review가 JSON 미출력 시(구형/실패) → 합의기 SKIP + 산문 verdict 그대로 사용(하위호환, fail-open 아님 — 기존 게이트 동작 유지).

### §5.3 `scripts/review_consensus.py` (신규)

- 입력: `cr_findings.json`
- finding마다 `_collect_evidence(file, line)` 호출 → `cr_evidence.json` 생성
- `core/review_bundle.py`의 `_find_direct_callers`/`_find_related_tests`를 **finding 단위로 재사용** (현재 전체-파일 단위 → file:line 단위 래퍼 추가, §2.2 갭 메움)
- LLM 미호출(코드만). 합의 *판정*은 §5.5 LLM이 별도 수행.

### §5.4 callee 수집 (신규, INV-5)

`_find_direct_callers`의 역방향. finding의 file:line 함수 본문에서 호출하는 심볼을 AST로 추출 → 정의 위치 grep. callee가 변경 영향권이면 사이드이펙트 후보.

> **범위 제한(메타-재귀·비용)**: 1-hop callee만. core/+scripts/만. 재귀 금지.

### §5.5 합의 판정 (LLM)

- 입력: `cr_evidence.json` (증거만). **원 finding의 산문 추론은 제외** — 증거 위에서 독립 재판정(reporter-worker 격리 정신).
- 각 finding → `ACCEPT`(증거가 결함 확증) / `REJECT`(증거가 반증) / `UNVERIFIED`(증거 불충분)
- 출력: `cr_consensus.json` + 산문 요약. UNVERIFIED는 BLOCK 기여 안 함(INV-5).
- 프로바이더 중립: 이 판정은 현재 활성 프로바이더(detect SSOT)로 실행. 같은 입력 → 같은 절차.

### §5.6 verdict 집계 재사용

`cr_consensus.json`의 ACCEPT만 `phase2-verdict-label-spec.md §4.4` 매핑에 투입.

**연결 경로(결정)**: 합의 판정 후 **합의 LLM이 verdict fence(`<!-- final-verdict-start -->`)를 포함한 최종 산문을 재생성**하여 기존 에이전트 응답 채널로 흘려보낸다. 따라서 `review_gate.py:57-78`의 verdict 파싱 파이프(`_extract_verdict_from_content`)는 **변경 없음** — 이는 "review_gate가 `cr_consensus.json`을 직접 읽지 않는다"는 **설계 결정**이며, 합의기 출력이 산문 verdict로 환원되는 조건에서만 성립한다. (S6 구현 시 이 환원 코드를 배선.)

---

## §6 멀티프로바이더 배선 (INV-2)

| 산출물 | 위치 | 프로바이더 적용 |
|---|---|---|
| 수렴 가드·캡 | `check_design_pending.py`/`check_pending_review.py` (코드) | 자동 — hook이 프로바이더 무관 실행 |
| 증거수집 | `review_consensus.py` + `review_bundle.py` (코드) | 자동 — 코드 |
| 구조화 finding 지시 | `INSTRUCTIONS.md` 공통 블록 → sync → CLAUDE/AGENTS/GEMINI | sync 강제 |
| cross-review 분류 규칙(§4.3) | `af-cross-review.md` + `.codex/agents/af-cross-review.toml` + 공통 프롬프트(`/tmp/af-review-prompt.txt`) | 3채널 동시 |

- **금지**: 프로바이더별 합의 로직 분기. 신규 프로바이더 추가 시 공통 프롬프트·공통 코드만 재사용(§ `af-cross-review.md:30` 기존 원칙 계승).
- cross-review 산문 프롬프트(`af-review-prompt.txt`)에 "findings.json도 출력하라" 지시 추가 → MCP/CLI fallback 양 경로 공통.

---

## §7 메타-재귀 경계 (INV-6)

- 합의기는 **코드 리뷰 finding에만** 적용. 설계문서는 §4(수렴 가드)만 — 합의기 미적용(설계는 증거=코드가 아직 없을 수 있음).
- 합의기 자체 코드(`review_consensus.py`)의 리뷰는 **일반 3-Tier**로 처리하되, "합의기를 합의기로" 재귀 금지.
- 이 설계는 게이트 *정확도* 개선(가짜 BLOCK↓, 사이드이펙트↑)이지 게이트 *무게* 증가가 목적이 아니다. 일상 작업은 여전히 표적검증(게이트 효율 논의 결론 유지).

---

## §8 구현 슬라이스

| 슬라이스 | 내용 | Tier |
|---|---|---|
| **S1** | §4.1 설계문서 라운드 캡 (`MAX_DESIGN_ROUNDS=3` + `.design_review_fired.json` 확장 + capped 안내) | Tier 2~3 (hook 경로) → 풀 3-Tier |
| **S2** | §4.2 수렴 감지(섹션 겹침 휴리스틱) + §4.3 스코프 게이트 지시(멀티프로바이더 3채널) | Tier 2~3 |
| **S3** | §5.2 구조화 finding 사이드카 + cross-review 지시(3채널) | Tier 2 (지시문·.md/.toml) |
| **S4** | §5.3 `review_consensus.py` + finding 단위 증거 래퍼(callers/tests 재사용) | Tier 3 (subprocess) → 풀 3-Tier |
| **S5** | §5.4 callee 수집 (AST 1-hop) | Tier 2~3 |
| **S6** | §5.5 합의 판정 LLM 배선 + §5.6 verdict 집계 연결 | Tier 3 → 풀 3-Tier |

> **선행 순서**: S1·S2(실패 B)는 S3~S6(실패 A)와 독립 — **병렬 가능**. S1이 즉효(이번 루프 재발 차단)이므로 **S1 먼저** 권장. S4는 S3(사이드카) 선행 필요.

---

## §9 불변식 + 테스트 요구사항

| ID | 내용 | 테스트 |
|---|---|---|
| INV-1 | 증거수집·라운드카운트는 코드 강제 (LLM 자율 아님) | `test_consensus_collects_without_llm` |
| INV-2 | 합의/수렴 로직 프로바이더 분기 없음 | `test_no_provider_branch_in_consensus` |
| INV-3 | 설계문서 `round_count >= MAX_DESIGN_ROUNDS` → 자동발화 중단 | `test_design_round_cap`, `test_oscillation_detect` |
| INV-4 | 설계문서 HOW 미명세 → ACCEPT-ADV 강등 (분류 지시 + 캡 백스톱) | `test_how_downgrade_or_capped` |
| INV-5 | 증거 미수집 finding → UNVERIFIED (BLOCK 기여 안 함) | `test_unverified_no_block` |
| INV-6 | 합의기 코드리뷰 한정, 설계문서 미적용 | `test_consensus_skips_design_docs` |
| INV-7 | finding 사이드카 부재 시 합의기 SKIP + 기존 verdict 유지 (하위호환) | `test_consensus_skip_no_sidecar` |

---

## §10 미결 / 의도적 제외

| 항목 | 결정 | 이유 |
|---|---|---|
| 수렴 감지 의미 비교(NLP) | 섹션 겹침 휴리스틱으로 대체 | 완전 의미비교는 과설계. 캡이 백스톱(INV-3) |
| callee 다중 hop | 1-hop만 | 비용·메타-재귀. 1-hop이 사이드이펙트 대부분 커버 |
| 설계문서 합의기 적용 | 제외 | 설계는 증거=코드가 미존재 가능. §4만 적용(INV-6) |
| 합의 판정 모델 고정 | detect SSOT 활성 프로바이더 | 프로바이더 중립(INV-2). 특정 모델 하드코딩 금지 |
| cr_findings.json 스키마 버전 | S3에서 동결 | baseline 캡처 후 결정(메모리 `analysis_doc_baseline_must_be_real_code`) |

---

## §11 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-06-19 | Draft (Opus 4.8). 5라운드 BLOCK 루프 복기 → 실패 B(자기유발 진동: 설계문서 라운드캡·수렴가드 부재 `check_design_pending.py`) + 실패 A(증거 미수집: finding 단위 API 부재 `review_bundle.py:362`, finding 산문 비가독). 해법 분리: §4 수렴가드 + §5 증거수집 합의기(코드리뷰 한정). 멀티프로바이더=코드로 중립 보장(INV-2). baseline grep 확정(`check_pending_review.py:30/160-173`, `review_bundle.py:252-293`, `review_gate.py:57-78`, `phase2-verdict-label-spec.md:164-176`). |
