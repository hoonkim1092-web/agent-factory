# Tier 2 Domain Expert Panel — 설계 (Draft v1)

> **상태**: Draft (af-cross-review 대기, Codex 5/13 01:00 KST 이후)
> **작성일**: 2026-05-11 KST
> **작성자**: Claude Opus 4.7 (대화 세션)
> **선행 commit**: `a397b9cd` (Tier 2 Phase 1 정직화)
> **영향 범위**: `.claude/agents/af-critic*.md`, `core/skill_loader.py` 호출 메커니즘, (옵션 A 시) judge 로직
> **타겟 효과**: detection 향상 50~70% (옵션 B 단독) / 70~90% (A+B 결합)

---

## §0 Executive Summary

`af-critic`은 현재 단일 페르소나로 모든 영역(프론트엔드/백엔드/아키텍처/보안/분산)을 같은 일반 휴리스틱으로 검토 → 어느 영역도 깊이 있게 못 잡음. 이를 **영역별 전문가 패널** 구조로 진화시켜 detection 향상.

본 설계는 두 옵션을 **단계 진입**으로 결합: 1단계 옵션 B(점진), 2단계 옵션 A(완전 패널).

---

## §1 배경 (Phase 1 한계)

Phase 1 완료 commit `a397b9cd`에서 명칭 정직화로 사용자 인지 개선 ✅. 그러나 **실제 detection 능력은 그대로**. 즉 Critic이 PASS 한다고 해서 진짜 결함이 없다는 보장은 여전히 없음.

근본 원인: 단일 일반 비평가는 모든 영역을 평균적으로 검토 → 영역별 깊이 부재.

---

## §2 두 옵션 비교

### 옵션 A — 영역별 sub-agent 분기 (전문가 패널)

```
변경 분석 (영역 감지)
    ├─→ af-critic-frontend  (React/CSS/접근성/브라우저 호환성)
    ├─→ af-critic-backend   (동시성/트랜잭션/캐싱/I/O)
    ├─→ af-critic-architecture (경계/의존성/확장성/트레이드오프)
    ├─→ af-critic-security  (OWASP/인증/암호학)
    └─→ af-critic-distributed (race condition/eventual consistency)
                ↓
        결과 합의 (judge)
```

- **비용**: ~400 LOC (sub-agent 5+개 SKILL.md + 영역 감지 + judge 합의 로직)
- **효과**: 매우 큼 — 각 영역 깊이 확보 + 패널 합의로 cross-validation 효과
- **한계**: sub-agent 정의/유지보수 부담, judge 로직 복잡

### 옵션 B — 단일 critic이 영역별 스킬 동적 로드

```
af-critic 호출
    ↓
skill_loader가 변경 영역 감지 (semantic_embedder + 12-cap)
    ↓
적절한 SKILL.md 동적 로드:
    - skills/code_review_guide (기본)
    - skills/react_coding (프론트엔드 변경 감지 시)
    - skills/domain/langchain (LangChain 코드 감지 시)
    - skills/state_machine_exception_planning (상태 머신 감지 시)
    ...
    ↓
영역별 체크리스트 적용 (단일 페르소나)
```

- **비용**: ~150 LOC (critic이 skill_loader 호출하도록 SKILL.md/Bash 보강)
- **효과**: 중간 — 페르소나 1개지만 휴리스틱이 영역별로 풍부해짐
- **장점**: AF 인프라(skill_loader, semantic_embedder, 12-cap) 그대로 재사용
- **한계**: 단일 페르소나라 패널 합의 효과 없음, 같은 모델이 N개 SKILL을 한 번에 적용

---

## §3 결정 — 단계 진입 (B 먼저, A는 검증 후)

### 단계 1: 옵션 B 채택 (즉시 가치)
- AF 기존 38개 스킬 활용 = 신규 작성 없음
- skill_loader 인프라 재사용 = 위험 낮음
- 효과 60~70% 확보

### 단계 2: 옵션 A 검토 (단계 1 검증 후)
- 단계 1로 detection 향상이 측정되면 옵션 A 추가
- 효과 부족 시 옵션 A로 진행 (예: 패널 합의 효과가 진짜 필요하면)
- 효과 충분 시 옵션 A 보류 (over-engineering 방지)

---

## §4 단계 1 (옵션 B) 설계 명세

### §4.1 변경 파일

| 경로 | 변경 | 예상 LOC |
|---|---|---|
| `.claude/agents/af-critic.md` | "Step 0.5: 변경 영역 감지 + SKILL 로드" 신설 | +60 |
| `core/skill_loader.py` (또는 헬퍼) | critic 진입점에서 호출 가능한 도메인 매핑 함수 추가 | +30 |
| `core/critic_skill_router.py` (신규) | 변경 파일 → 영역 → 추천 SKILL ID 매핑 | +60 |
| 회귀 테스트 (`tests/test_critic_skill_router.py`) | 영역 매핑 정확도 | +50 |

### §4.2 영역 매핑 규칙 (잠정)

| 변경 파일 패턴 | 추천 SKILL |
|---|---|
| `.tsx`, `.jsx`, `.css`, `frontend/**` | `code_review_guide` + `react_coding` + `frontend_ui_ux` |
| `core/agents/**`, `core/orchestr*.py`, `core/dynamic_*` | `code_review_guide` + `state_machine_exception_planning` |
| `core/skill_*.py`, `core/semantic_*.py` | `code_review_guide` + AF skill system 자체 SKILL |
| `langchain/`, `langgraph/`, deep_agents | `code_review_guide` + `domain/langchain` |
| `core/memory_system/**` | `code_review_guide` + `core_memory` |
| 기타 일반 `core/*.py` | `code_review_guide` |

### §4.3 critic SKILL.md 변경

af-critic.md에 Step 0.5 추가:
```markdown
### Step 0.5: 변경 영역 감지 + SKILL 동적 로드 (단계 1 — Phase 3)

```bash
# critic_skill_router.py로 추천 SKILL ID 추출
RECOMMENDED_SKILLS=$(python -m core.critic_skill_router --diff-paths "$CHANGED_FILES")
echo "추천 SKILL: $RECOMMENDED_SKILLS"

# 각 SKILL.md를 Read하여 체크리스트 컨텍스트 확보
for SKILL_ID in $RECOMMENDED_SKILLS; do
  SKILL_PATH="skills/$SKILL_ID/SKILL.md"
  if [ -f "$SKILL_PATH" ]; then
    cat "$SKILL_PATH"
  fi
done
```

이후 Step 1~4의 체크리스트는 추천 SKILL의 영역별 항목을 우선 적용한다.
```

### §4.4 검증 기준 (단계 1)

1. `critic_skill_router.py` 영역 매핑 회귀 테스트 PASS
2. 더미 work-item 3개로 검증:
   - frontend 변경 → react_coding SKILL 로드 확인
   - LangChain 변경 → domain/langchain SKILL 로드 확인
   - 일반 core/*.py → code_review_guide만 로드 확인
3. critic 출력에 "적용된 영역 SKILL: <목록>" 한 줄 표기

---

## §5 단계 2 (옵션 A) 설계 잠정

단계 1 검증 후 detection 향상이 부족하다면:

| 신규 sub-agent | 영역 | 예상 LOC |
|---|---|---|
| `.claude/agents/af-critic-frontend.md` | UI/UX/접근성 | ~100 |
| `.claude/agents/af-critic-backend.md` | 동시성/트랜잭션 | ~100 |
| `.claude/agents/af-critic-architecture.md` | 시스템 경계 | ~100 |
| `.claude/agents/af-critic-security.md` | OWASP/인증 | ~100 |
| `.claude/agents/af-critic-distributed.md` | race/consistency | ~100 |
| `core/critic_panel_judge.py` (신규) | 5개 결과 합의 로직 | ~80 |

총 ~580 LOC + judge 로직 + 영역 감지 보강.

**진입 조건**: 단계 1 데이터 수집 후 사용자 결정.

---

## §6 의도적으로 제외한 항목

1. **외부 LLM 호출 추가** — Tier 3 영역. Tier 2는 same-vendor 유지.
2. **sub-agent 5개를 즉시 모두 신설** — over-engineering 방지. 단계 1 검증 우선.
3. **영역 자동 감지 LLM** — `critic_skill_router.py`는 룰 기반 (정규식 + 경로 매칭). LLM은 비용 큼.

---

## §7 작업량 / 일정

| 단계 | 작업 | 예상 LOC | 시간 |
|---|---|---|---|
| 단계 1 (옵션 B) | critic SKILL.md + skill_router + 회귀 테스트 | ~200 | 1.5~2일 |
| 단계 1 검증 | 더미 work-item 3개로 영역 라우팅 확인 | — | 0.5일 |
| **단계 1 합** | — | **~200** | **2~2.5일** |
| 단계 2 (옵션 A, 조건부) | sub-agent 5개 + judge | ~580 | 3~5일 |

---

## §8 리스크

| # | 리스크 | 대응 |
|---|---|---|
| 1 | 영역 매핑 룰이 잘못된 SKILL 로드 | 회귀 테스트 + critic 출력에 적용 SKILL 표기 (사용자 검증 가능) |
| 2 | 여러 SKILL 로드 시 critic context 부담 증가 | 최대 3개 SKILL로 제한 (12-cap 정책 활용) |
| 3 | 단계 1 효과 측정 불가 → 단계 2 결정 근거 부재 | 단계 1 후 4주간 critic finding 카테고리별 통계 수집 |
| 4 | sub-agent 패널 합의 로직 복잡도 (단계 2) | majority vote + 명시적 disagreement 표기 (judge가 미해결 분쟁 BLOCK) |

---

## §9 의사결정 근거

- 사용자 통찰 (2026-05-11 본 세션): "비평가가 프론트엔드/백엔드/아키텍처 등 롤에 따라 스킬 다르게 장착한 별도 에이전트가 리뷰해야 하는 거 아닌가?"
- AF 38개 스킬 자산 (`skills/`) 활용 가능
- AF skill_loader / semantic_embedder 인프라 재사용 가능
- Tier 2 Phase 1 정직화의 후속 — 진짜 detection 향상

---

## §10 Open Questions (cross-review 시 결정)

1. 영역 매핑이 룰 기반 vs semantic embedding 기반 어느 쪽이 robust? (잠정 룰 기반)
2. 한 work-item에 여러 영역 변경 시 SKILL 우선순위? (잠정 12-cap 적용)
3. 단계 2 진입 임계 — detection 향상 측정 어떻게? (잠정 4주 데이터 수집)
4. sub-agent 5개가 적정인지, 더 세분 필요한지 (예: af-critic-data-pipeline)
5. Tier 2 Phase 2 (코드 측 single-vendor 자동 라벨) 작업과 어느 게 우선?

---

## §11 cross-review 체크리스트

- [ ] §4.2 영역 매핑 규칙의 robustness (오탐/누락 가능성)
- [ ] critic SKILL.md Step 0.5 추가가 기존 워크플로우(bundle 정책 등)와 충돌 없는지
- [ ] core/critic_skill_router.py 신규 모듈이 AF 인프라(skill_loader)와 통합 정합
- [ ] 단계 2 sub-agent 패널의 judge 합의 알고리즘 명세 깊이
- [ ] §10 Open Questions가 결정 가능한 형태로 제시됨

---

**End of design document. Awaiting af-cross-review (5/13 01:00 KST 이후).**
