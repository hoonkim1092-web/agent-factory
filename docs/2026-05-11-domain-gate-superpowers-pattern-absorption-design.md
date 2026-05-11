# Domain Gate + Superpowers 패턴 자체 흡수 — 통합 설계

> **상태**: Draft (af-cross-review 대기)
> **작성일**: 2026-05-11 KST
> **작성자**: Claude Opus 4.7 (대화 세션, 사용자 hoon.kim)
> **모델 권장 (구현 단계)**: Sonnet 4.6
> **영향 범위**: `docs/`, `core/approval_gate.py`, `docs/work-items/_template/`, (Phase C 시) 신규 `core/skills/` 또는 `skills/` 항목
> **선행 의사결정 문서**: `docs/codex/2026-05-06-agent-factory-3-phase-workflow-review.md`, `docs/archive/2026-04-17-AF_Phase_A_Requirements.md`, `docs/archive/resolved/2026-04-22-phase-a-decisions-required.md`

---

## §0 Executive Summary (1단락)

`Agent Factory(이하 AF)`에 **Phase 2 Domain Gate**를 신설하고, **Superpowers 14개 스킬 중 AF가 부족한 패턴만 자체 구현으로 흡수**한다. 외부 코드 import / 외부 패키지 자동 설치 / GStack 부트스트랩은 **명시적으로 폐기**한다. 본 설계의 출발점은 5/6 Codex 워크플로우 리뷰의 권고 (Phase 2 domain gate 신설 + 기존 primitive 매핑)와, 점수표 보정 후 도출된 사용자 통찰("외부 가치 흡수는 자체 구현으로도 가능하므로 외부 import의 진짜 우위는 흡수 속도 3~5일뿐")이다.

---

## §1 배경 (왜 지금 이 설계가 필요한가)

### §1.1 현재 격차

AF는 다음을 이미 갖추고 있다:
- **인프라 5/5 슈퍼파워** 자체 구현 (`core/skill_loader.py`, `skill_metadata.py`, `hooks/context_fork.py`, `skill_eval_harness.py`, `skill_preflight.py`, `semantic_embedder.py`)
- **38개 자체 스킬** (`skills/` directory)
- **워크플로우 게이트** (`core/approval_gate.py`, `scripts/review_gate.py`, `core/review_runner.py`, 3-tier cross-review)

그러나 다음이 부족하다:
- **도메인 거버넌스 부재** — 기존 결정/용어와 silent하게 충돌하는 변경을 막을 메커니즘 없음
- **단일 진실원 부재** — domain glossary, decision rationale이 `Master_Blueprint.md` / work-items / reviews에 산재
- **기획 단계 챌린지 부재** — Superpowers의 `brainstorming` (Socratic 검증) 같은 사전 비판 단계 없음

### §1.2 외부 도구 검토 결과 (요약)

| 후보 | 검증 결과 | 결정 |
|---|---|---|
| **GStack 자동 설치** (4/22 Q8 Phase B 결정) | `core/skill_pack_bootstrapper.py` 48 LOC 존재하나 dead code, 프로덕션 호출자 0건. 어댑터 3종 (~450 LOC) 추가 가치 < 비용 | **폐기** |
| **Superpowers 패키지 import** | claude_cli 종속, 외부 변경 추적 부담, AF 자체 인프라/콘텐츠와 layer 충돌 | **폐기** |
| **Superpowers 패턴 자체 흡수** | 14개 중 AF에 없거나 부족한 패턴(특히 `brainstorming`, `systematic-debugging`)을 자체 구현 — 외부 의존 0 | **채택** |

### §1.3 점수표 (10차원, 100점 만점, double-count 보정 후)

| 차원 | 직전 권장안 단독 | 사용자 요구안 (외부 통합) | **통합안** |
|---|---|---|---|
| AF 약점 보강 | 9 | 6 | **9** |
| 외부 가치 흡수 (자체 구현 포함) | 3 | 9 | **9** |
| 흡수 속도 | 3 | 9 | **7** |
| 장기 효과 | 9 | 5 | **9** |
| 비용 | 9 | 4 | **7** |
| 리스크 | 9 | 5 | **9** |
| 유지보수 부담 | 9 | 4 | **9** |
| 품질 측정 가능성 | 8 | 5 | **8** |
| AF 정체성 부합 | 9 | 5 | **9** |
| 환경 의존 | 9 | 6 | **9** |
| **합계** | **77** | **58** | **85** |

### §1.4 5/6 Codex 권고 핵심 (인용)

> "Phase 1 maps to work-item planning and approval. **Phase 2 should become a new domain/ADR gate.** Phase 3 maps to the existing task board, review gate, and multi-provider review system. The most valuable next development task is Phase 2 standardization, because Phase 1 and Phase 3 already have partial implementations while domain fit is still weakly enforced."
> — `docs/codex/2026-05-06-agent-factory-3-phase-workflow-review.md` line 153–159

본 설계는 위 권고를 **그대로 구현**하면서 사용자 통찰(자체 구현 흡수)을 결합한다.

---

## §2 결정 (Decision)

### §2.1 채택 사항

1. **Phase 2 Domain Gate 신설** — `PROJECT_CONTEXT.md` + ADR 디렉토리 + `domain-review.md` 템플릿 + `approval_gate` 정책 확장
2. **Superpowers 14개와 AF 자체 구현의 1:1 비교 매트릭스** — 데이터 기반 흡수 우선순위 결정
3. **선별 패턴 자체 흡수** — 비교 결과 우수한 외부 패턴만 AF 자체 코드로 흡수 (외부 import 0건)

### §2.2 명시적 폐기

1. **GStack 자동 설치 (4/22 Q8 Phase B)** — `core/skill_pack_bootstrapper.py` 보강 또는 어댑터 3종 추가 모두 미진행
2. **Superpowers 패키지/콘텐츠 직접 import** — `claude_cli` 또는 marketplace 호출 코드 추가 금지
3. **4/17 §0.4 외부 위임 전략의 "암묵적 의존"** — 명시적 폐기 표기 (외부 도구는 "있으면 보너스, 없어도 AF 정상 작동")

---

## §3 Phase A 설계 — Domain Gate 신설 (3.5일)

### §3.1 산출물

| 신규 파일 | 역할 | 형식 | 예상 크기 |
|---|---|---|---|
| `docs/PROJECT_CONTEXT.md` | 프로젝트 도메인 글로서리·시스템 경계·관습 단일 진실원 | Markdown | ~80 lines |
| `docs/decisions/ADR-template.md` | ADR 표준 템플릿 (Title / Context / Decision / Consequences / Status) | Markdown | ~30 lines |
| `docs/decisions/ADR-0001-blueprint-vs-context-separation.md` | 첫 번째 ADR — Blueprint(구조)와 PROJECT_CONTEXT(개념) 책임 분리 결정 | Markdown | ~40 lines |
| `docs/work-items/_template/domain-review.md` | Work-item별 도메인 합치 검토 템플릿 | Markdown | ~40 lines |

### §3.2 코드 변경

| 수정 파일 | 변경 내용 | 예상 LOC |
|---|---|---|
| `core/approval_gate.py` | `requires_domain_review: bool` 정책 추가, work-item kind 분기, `domain-review.md` verdict 검사 (verdict ∈ {`PASS`, `NEEDS_ADR`, `BLOCK`}) | ~30 |

### §3.3 정책 분기 정의

```python
# core/approval_gate.py 신설 메서드 시그니처 (개념)
def require_domain_review(work_item_kind: str) -> bool:
    """non-trivial work-item에서만 domain-review 요구. 점진적 활성화."""
    NON_TRIVIAL_KINDS = {"feature", "refactor", "architecture-change"}
    return work_item_kind in NON_TRIVIAL_KINDS
```

**기본값 정책 (점진 활성화)**:
- 단계 1: `requires_domain_review = False` (전 work-item) — 정책 인프라만 배치, 게이트 발화 X
- 단계 2: `requires_domain_review = True` for `feature` only — 신규 기능부터 적용
- 단계 3: `requires_domain_review = True` for `{feature, refactor}` — 점진 확대
- 단계 4: 회귀 측정 후 `architecture-change` 추가 또는 정책 동결

### §3.4 domain-review.md 템플릿 구조 (제안)

```markdown
# Domain Review — <work-item-slug>

## 1. 도메인 용어 합치
- 본 work-item이 사용하는 용어 목록
- PROJECT_CONTEXT.md에 이미 정의된 용어 매칭
- 신규 용어 (있다면) → ADR 후보로 분리

## 2. 기존 ADR 충돌 검토
- 관련 ADR ID 목록
- 충돌 여부 (PASS / 새 ADR 필요)

## 3. 새 ADR 후보 (있다면)
- 결정 요약 / Context / Consequences

## 4. Verdict
- [ ] PASS — 기존 도메인/결정과 합치
- [ ] NEEDS_ADR — 새 ADR 작성 후 진입 필요
- [ ] BLOCK — 도메인 충돌, 재설계 요구

## 5. Reviewer
- 이름 / 일자 / 모델
```

### §3.5 검증 기준 (Phase A)

| # | 검증 항목 | 방법 | 통과 조건 |
|---|---|---|---|
| 1 | `PROJECT_CONTEXT.md` 신설 | Read 검증 | 파일 존재 + 핵심 섹션 4개 (Glossary, Boundaries, Conventions, Source of Truth) |
| 2 | `ADR-0001` 첫 결정 기록 | Read 검증 | 5필드 모두 채워짐 |
| 3 | `domain-review.md` 템플릿 적용 | 더미 work-item 1개 작성 | 4섹션 + verdict 포함 |
| 4 | `approval_gate` 게이트 동작 | 회귀 테스트 (`tests/test_approval_gate_domain_review.py` 신설) | non-trivial work-item에서 domain-review 누락 시 `BlockedExecutionError` |
| 5 | 정책 점진 활성 | `requires_domain_review` 기본값 False 배포 | 기존 work-item은 자동 통과 |
| 6 | Master_Blueprint.md 동기 | §3 approval_gate 섹션 갱신 + §12 이력 | 같은 commit에 포함 |

---

## §4 Phase B 설계 — 비교 매트릭스 (1일)

### §4.1 산출물

`docs/2026-05-12-superpowers-vs-af-comparison-matrix.md` (Markdown 비교 보고서)

### §4.2 비교 차원 정의

각 Superpowers 14개 스킬에 대해 다음 4축 평가:

| 축 | 측정 방법 | 점수 |
|---|---|---|
| **A. AF 자체 구현 여부** | `core/`, `skills/`, `scripts/` grep + 기능 명세 비교 | 0 (없음) / 1 (부분) / 2 (완전) |
| **B. AF 구현 품질** | LOC 비교, 테스트 커버리지, 호출 빈도 (`data/skill-usage.jsonl`), 기능 완전성 | 0–10 |
| **C. Superpowers 패턴의 차별 가치** | AF가 가지지 못한 고유 메커니즘 (예: Socratic 대화 형식, 4-phase 디버깅 절차) | 0–10 |
| **D. 흡수 비용** | 자체 구현 시 예상 LOC + 통합 난이도 | Low / Medium / High |

### §4.3 흡수 우선순위 결정 매트릭스

```
흡수 우선순위 = (C - B) × (10 / D 난이도 가중치)

- 우선순위 ≥ 5: 즉시 흡수 (Phase C 1순위)
- 우선순위 2~4: 선택적 흡수 (Phase C 2순위)
- 우선순위 < 2: 흡수 보류 (AF 자체 구현이 충분)
```

### §4.4 14개 잠정 평가 (Phase B 진행 전 사전 추정)

| Superpowers 스킬 | A | B | C | D | 우선순위 | 잠정 결정 |
|---|---|---|---|---|---|---|
| using-superpowers | 1 | 7 | 2 | Low | -1 | 보류 |
| **brainstorming** | 0 | 0 | 9 | Medium | **9** | **즉시 흡수** |
| writing-plans | 2 | 8 | 3 | High | -1 | 보류 |
| using-git-worktrees | 1 | 5 | 4 | Medium | 1 | 선택적 |
| test-driven-development | 1 | 6 | 5 | Medium | 1 | 선택적 |
| subagent-driven-development | 2 | 8 | 4 | High | -1 | 보류 |
| executing-plans | 2 | 8 | 2 | High | -2 | 보류 |
| requesting-code-review | 2 | 9 | 1 | High | -3 | 보류 (AF 우수) |
| receiving-code-review | 2 | 9 | 1 | High | -3 | 보류 (AF 우수) |
| **systematic-debugging** | 0 | 0 | 8 | Low | **8** | **즉시 흡수** |
| **verification-before-completion** | 1 | 5 | 7 | Low | **3** | **선택적 흡수** |
| finishing-a-development-branch | 1 | 6 | 4 | Medium | 0 | 보류 |
| dispatching-parallel-agents | 2 | 8 | 3 | High | -2 | 보류 |
| writing-skills | 1 | 7 | 5 | Medium | 0 | 보류 |

> ⚠️ 위 점수는 **사전 추정**이며 Phase B 실측 후 확정. Phase C는 실측 결과 기준.

### §4.5 검증 기준 (Phase B)

| # | 검증 항목 | 방법 | 통과 조건 |
|---|---|---|---|
| 1 | 14개 모두 평가 완료 | 매트릭스 행 카운트 | 정확히 14행 |
| 2 | A점수 근거 명시 | 각 행에 grep 결과/AF 파일 경로 | 모든 행에 출처 |
| 3 | 우선순위 ≥ 5 후보 식별 | 매트릭스 정렬 | 최소 1개 |
| 4 | Phase C 후보 확정 | 매트릭스 → Phase C plan 변환 | Phase C 후보 명단 산출 |

---

## §5 Phase C 설계 — 선별 자체 흡수 (3~5일)

### §5.1 잠정 흡수 후보 (Phase B로 확정)

| Superpowers 스킬 | 흡수 형태 | AF 신규/수정 위치 | 예상 LOC |
|---|---|---|---|
| **brainstorming** | Socratic 검증 패턴 → Phase 2 domain gate에 직접 통합 | `docs/work-items/_template/domain-review.md` §1.5 (Socratic Questions 섹션 추가) + `core/brainstorm_prompts.py` (선택) | ~80 |
| **systematic-debugging** | 4-phase 디버깅 가이드 스킬 | `skills/systematic_debugging/SKILL.md` 신설 (AF 자체 형식) | ~120 |
| **verification-before-completion** | review_gate verdict 강제 | `scripts/review_gate.py` 또는 `core/approval_gate.py`에 verdict 검증 강화 | ~50 |

### §5.2 외부 코드 import 0건 원칙 (강제)

- `from superpowers ...` import **금지**
- `https://github.com/obra/superpowers` 직접 fetch **금지**
- `.claude/plugins/` 디렉토리 직접 참조 **금지**
- 패턴/아이디어만 학습해서 AF 자체 형식으로 재구현
- (참고) Superpowers 라이선스: MIT. 패턴 차용은 자유.

### §5.3 검증 기준 (Phase C)

| # | 검증 항목 | 방법 | 통과 조건 |
|---|---|---|---|
| 1 | 외부 import 0건 | grep `from superpowers`, `obra/superpowers` | 0건 |
| 2 | 흡수 패턴 동작 검증 | 회귀 테스트 (`tests/test_systematic_debugging.py` 등) | 핵심 시나리오 PASS |
| 3 | AF 자체 스킬 등록 | `core/skill_loader.py` 자동 발견 | `skills/systematic_debugging/`이 12-cap 라우팅에 등장 |
| 4 | domain-review.md 강화 | brainstorming 패턴 통합 후 Socratic 섹션 동작 | 더미 work-item에서 Socratic 질문 출력 |

---

## §6 의도적으로 제외한 항목 (명시)

본 설계는 다음을 **명시적으로 폐기**한다. 향후 같은 결정을 재론할 경우 본 §6를 참조해야 한다.

### §6.1 GStack 자동 설치 (4/22 Q8 Phase B)

- **폐기 이유**: `core/skill_pack_bootstrapper.py` 48 LOC가 이미 dead code (프로덕션 호출자 0건). 어댑터 3종 추가(~450 LOC)는 외부 위임 전략의 가치 < 비용.
- **대체 방향**: 사용자가 필요 시 `claude /plugins install gstack` 같은 수동 명령으로 설치. AF는 무관.
- **dead code 처분**: 별도 결정. (옵션 A) 본 설계 commit과 함께 제거 / (옵션 B) 남겨두되 `# DEPRECATED` 주석 추가. 본 설계는 옵션 B를 잠정 권장 (영향 범위 최소).

### §6.2 Superpowers 패키지 직접 import

- **폐기 이유**: 외부 변경 추적 부담, AF 자체 인프라(skill_loader, skill_metadata)와 layer 충돌, claude_cli 종속.
- **대체 방향**: §5의 자체 흡수 (외부 코드 0건 원칙).

### §6.3 14개 일괄 통합

- **폐기 이유**: §4.4 사전 추정에 따르면 14개 중 9개는 AF가 동등하거나 우수 (보류 판정). 일괄 통합은 중복 노력.
- **대체 방향**: §5의 선별 흡수 (3개 잠정 + Phase B 실측 후 가감).

### §6.4 4/17 §0.4 외부 위임 전략 (암묵적 의존)

- **폐기 이유**: 본 설계 채택 시 AF는 외부 도구에 어떠한 의존도 갖지 않음. "있으면 보너스" 위임은 모호함을 만듦.
- **대체 방향**: 명시적 폐기 표기. AF는 자급자족 + 사용자가 외부 도구를 추가 사용하는 것은 사용자 자유.

---

## §7 변경 파일 명세 (전체 통합)

### §7.1 신규 파일

| 경로 | Phase | 역할 | 형식 | 예상 LOC |
|---|---|---|---|---|
| `docs/PROJECT_CONTEXT.md` | A | 도메인 글로서리·경계·관습 | Markdown | ~80 |
| `docs/decisions/ADR-template.md` | A | ADR 표준 템플릿 | Markdown | ~30 |
| `docs/decisions/ADR-0001-blueprint-vs-context-separation.md` | A | 첫 ADR | Markdown | ~40 |
| `docs/work-items/_template/domain-review.md` | A | 도메인 검토 템플릿 | Markdown | ~40 |
| `tests/test_approval_gate_domain_review.py` | A | 정책 회귀 테스트 | Python | ~80 |
| `docs/2026-05-12-superpowers-vs-af-comparison-matrix.md` | B | 비교 매트릭스 보고서 | Markdown | ~200 |
| `skills/systematic_debugging/SKILL.md` | C | 4-phase 디버깅 스킬 | Markdown + (선택) `.py` | ~120 |
| `core/brainstorm_prompts.py` (선택) | C | Socratic 패턴 헬퍼 | Python | ~80 |
| `tests/test_systematic_debugging.py` | C | 흡수 패턴 회귀 테스트 | Python | ~50 |

### §7.2 수정 파일

| 경로 | Phase | 변경 내용 | 예상 LOC |
|---|---|---|---|
| `core/approval_gate.py` | A | `requires_domain_review` 정책 + verdict 검사 | ~30 |
| `scripts/review_gate.py` 또는 `core/approval_gate.py` | C | verification-before-completion verdict 강화 | ~50 |
| `Master_Blueprint.md` | A, C | §3 approval_gate / §0 빠른 참조 / §12 이력 갱신 | ~40 |
| `docs/work-items/_template/feature-plan.md` (옵션) | C | brainstorming Socratic 섹션 통합 | ~30 |

### §7.3 제거/폐기 후보

| 경로 | 처분 | 사유 |
|---|---|---|
| `core/skill_pack_bootstrapper.py` | DEPRECATED 주석 (잠정) 또는 제거 | 프로덕션 호출자 0건, dead code |
| `tests/test_compact_step2.py` 내 `TestSkillPackBootstrapper` | (위 처분에 따라) skip 또는 제거 | 위와 동기 |
| `af.spec` line 122 `core.skill_pack_bootstrapper` | 위 결정에 따라 hiddenimports에서 제거 | 위와 동기 |

### §7.4 LOC 총합 추정

- Phase A: 신규 markdown ~190 + Python ~110 = **~300 LOC**
- Phase B: markdown ~200 = **~200 LOC**
- Phase C: 신규 markdown ~150 + Python ~180 + 수정 ~80 = **~410 LOC** (잠정, Phase B 후 확정)
- **총합 ~910 LOC** (외부 import 0)

---

## §8 작업량 / 일정 / 모델

| Phase | 작업량 | 권장 모델 | 누적 |
|---|---|---|---|
| A | 3.5일 | Sonnet 4.6 (구현) | 3.5일 |
| B | 1일 | Sonnet 4.6 또는 Opus (분석) | 4.5일 |
| C | 3~5일 | Sonnet 4.6 (구현) | 7.5~9.5일 |
| **총합** | **7.5~9.5일** | — | — |

각 Phase 완료 시 cross-review (CLAUDE.md Review-Gate 규칙). 본 설계 자체는 작성 직후 af-cross-review 1회 (Tier 3, multi-provider fan-out).

---

## §9 리스크 및 대응

| # | 리스크 | 발생 가능성 | 영향 | 대응 |
|---|---|---|---|---|
| 1 | `PROJECT_CONTEXT.md`가 stale될 위험 | 중간 | 중간 | Phase D (별도) — context-linter 추가 권장. 본 설계 범위 외 |
| 2 | `domain-review.md`가 형식적으로 작성될 위험 | 중간 | 높음 | 정책 단계 1~2에서는 advisory만, 단계 3에서 enforce. cross-review 시 verdict 검증 |
| 3 | Phase C 흡수 패턴이 AF 자체 구현과 충돌 | 낮음 | 중간 | Phase B 매트릭스에서 미리 식별. Phase C 진입 전 충돌 명세 확정 |
| 4 | `requires_domain_review` 점진 활성이 더 빨리 enforce되어 기존 work-item이 차단됨 | 낮음 | 높음 | 기본값 False 유지, 명시적 commit으로만 단계 전환. 회귀 테스트로 보장 |
| 5 | ADR 작성 부담이 사용자 워크플로우를 느리게 함 | 중간 | 중간 | ADR은 "필요할 때만" 정책 (NEEDS_ADR verdict 시에만 강제) |
| 6 | Phase B 사전 추정 (§4.4)이 실측과 크게 다르면 Phase C 범위 변경 | 중간 | 낮음 | Phase B 종료 시 Phase C 범위 재확정 (본 설계 §5.1을 갱신) |
| 7 | brainstorming 패턴 흡수가 AI 의존이라 매번 비용 발생 | 중간 | 낮음 | Socratic 질문 템플릿화 (LLM 호출 X, prompt 헬퍼만) |

---

## §10 마이그레이션 전략

### §10.1 기존 work-item

- 기본값 `requires_domain_review = False` 유지
- 기존 work-item은 자동 통과
- 신규 work-item에만 정책 적용 (단계 2부터)

### §10.2 점진 활성 일정 (잠정)

| 단계 | 시점 | 정책 | 기준 |
|---|---|---|---|
| 1 | Phase A 완료 직후 | False (전 work-item) | 인프라 검증만 |
| 2 | Phase A 완료 + 1주 | True (`feature` only) | 신규 기능부터 적용 |
| 3 | 단계 2 + 2주 | True (`{feature, refactor}`) | 회귀 측정 후 확대 |
| 4 | 단계 3 + 1개월 | True (`architecture-change` 추가) 또는 동결 | 데이터 기반 결정 |

### §10.3 dead code (`SkillPackBootstrapper`) 처분

- 본 설계 채택 시 별도 commit으로 처분 (옵션 B: DEPRECATED 주석)
- 옵션 A (즉시 제거)는 본 설계 §7.3에서 제외 — `af.spec` / `tests/test_compact_step2.py` 동기 변경 필요해 영향 범위 큼

---

## §11 의사결정 근거 (Decision Trail)

본 설계는 다음 일련의 의사결정 누적 결과:

1. **2026-04-08** `docs/2026-04-08-agent_factory_harness_gsd_superpowers_analysis.md` — Superpowers 5 슈퍼파워 분석. AF가 5/5 자체 구현됨 확인.
2. **2026-04-09** `docs/archive/code_review/26_0409_gsd_superpowers_analysis_review.md` — Claude+Codex 교차 리뷰. "기존 자산 위에 얹는 게 맞다" 결론.
3. **2026-04-17** `docs/archive/2026-04-17-AF_Phase_A_Requirements.md` §0.4 — 외부 위임 전략 결정 (이번 설계로 폐기).
4. **2026-04-22** `docs/archive/resolved/2026-04-22-phase-a-decisions-required.md` Q8 — Phase A: (a) 탐지만 + Phase B: (d) 자동 부트스트랩 결정. 이번 설계로 Phase B 폐기.
5. **2026-04-22** Phase A (a) 구현 → `core/skill_pack_bootstrapper.py` 48 LOC. dead code 확인.
6. **2026-05-06** `docs/codex/2026-05-06-agent-factory-3-phase-workflow-review.md` — Phase 2 domain gate 권고. 본 설계의 직접 출발점.
7. **2026-05-11** 본 세션 — 사용자 통찰 반영 (외부 가치 흡수는 자체 구현으로 가능). 통합안 도출 + 점수표 85/77/58 검증.

---

## §12 Open Questions (cross-review 시 결정)

| # | 질문 | 잠정 답 | 결정자 |
|---|---|---|---|
| Q1 | `requires_domain_review` 기본값 False / True 중 어느 쪽으로 단계 1 출발? | False (점진 활성) | cross-review 검토 |
| Q2 | ADR 작성을 강제(enforce)할지 권장(advisory)만 할지? | NEEDS_ADR verdict 시에만 강제 | cross-review 검토 |
| Q3 | Phase B 비교 평가에 외부 의견(Codex/Gemini) 동원 여부? | 동원 권장 (객관성 확보) | cross-review 검토 |
| Q4 | `core/skill_pack_bootstrapper.py` 처분: 옵션 A (즉시 제거) vs 옵션 B (DEPRECATED 주석)? | 옵션 B (영향 범위 최소) | 본 설계 + 별도 commit |
| Q5 | Phase C `core/brainstorm_prompts.py` 신설 vs `domain-review.md` 텍스트 통합? | 후자 (LOC 절약) | Phase B 결과 반영 |
| Q6 | `systematic_debugging` 흡수 형식: SKILL.md only vs SKILL.md + .py? | SKILL.md only (markdown 우선) | Phase B 결과 반영 |
| Q7 | brainstorming 패턴이 LLM 호출을 발생시키는가? | NO (prompt 템플릿만) | §9 리스크 7 참조 |

---

## §13 Cross-Review 체크리스트 (검토자용)

본 설계 검토 시 다음을 확인:

1. ✅ §1.2 외부 도구 검토 결과의 사실 정확성 (`core/skill_pack_bootstrapper.py` dead code 확인, Superpowers 14개 목록)
2. ✅ §1.3 점수표의 차원 정의 명확성 (특히 외부 가치 흡수 vs 흡수 속도 분리)
3. ✅ §2 결정 사항이 §1 배경과 일관
4. ✅ §3 Phase A 산출물 4개가 5/6 Codex 권고와 매칭
5. ✅ §4.4 사전 추정의 보수성 (Phase B 실측에서 크게 어긋나지 않을 만큼)
6. ✅ §5.2 외부 코드 import 0건 원칙의 강제력
7. ✅ §6 폐기 항목의 근거 명시
8. ✅ §7 LOC 추정의 합리성
9. ✅ §9 리스크 cover 완전성
10. ✅ §10 마이그레이션의 안전성 (기존 work-item 영향 0)
11. ✅ §12 Open Questions가 결정 가능한 형태로 제시됨

---

## §14 참조

- 5/6 Codex 권고: `docs/codex/2026-05-06-agent-factory-3-phase-workflow-review.md`
- 4/17 Phase A 요구사항: `docs/archive/2026-04-17-AF_Phase_A_Requirements.md` §0.4
- 4/22 Q8 결정: `docs/archive/resolved/2026-04-22-phase-a-decisions-required.md`
- 4/8 GSD/Superpowers 분석: `docs/2026-04-08-agent_factory_harness_gsd_superpowers_analysis.md`
- 4/9 교차 리뷰: `docs/archive/code_review/26_0409_gsd_superpowers_analysis_review.md`
- Superpowers 14개 공식 목록: `https://github.com/obra/superpowers` (라이선스 MIT)
- AF 자체 인프라 검증 (5/11 본 세션): `core/skill_loader.py`, `core/skill_metadata.py`, `core/hooks/context_fork.py`, `core/skill_eval_harness.py`, `core/skill_preflight.py`, `core/semantic_embedder.py`

---

**End of design document. Awaiting af-cross-review.**
