---
name: Phase A+B 완료 / Phase C 대기
description: Domain Gate Phase A + ADR M1~M5 + Superpowers Phase B 매트릭스 완료. Phase C = SKILL.md 3개 신설 + core/utils.py 1줄 수정.
type: project
originSessionId: c14a9728-8776-4889-9877-c4b81eb0aca7
---
Phase A(Domain Gate) + ADR M1~M5 + Phase B(비교 매트릭스 실측) 완료. 2026-05-13.

**완료 커밋:**
- `ef82acc4` — Phase A (approval_gate.py domain gate)
- `483cce38` — ADR M1~M5 결정 (CLAUDE.md 정책 추가, docs/decisions/ 생성)
- `c6fd08d3` — Phase B 비교 매트릭스 (`docs/2026-05-13-superpowers-vs-af-comparison-matrix.md`)

**Phase B 실측 결과:**
- 즉시 흡수: brainstorming (C=9,B=0,D=Med), systematic-debugging (C=10,B=0,D=Low)
- 선택적: verification-before-completion (C=8,B=4,D=Low), finishing-branch, using-git-worktrees
- 사용자 선택: Option B(권장) = 즉시 2개 + verification-before-completion

**Phase C 구현 목록 (Option B, ~250 LOC):**
1. `skills/systematic_debugging/SKILL.md` 신설 (~120 LOC, inspired_by: superpowers/systematic-debugging)
2. `docs/work-items/_template/domain-review.md` Socratic 섹션 추가 (~80 LOC, inspired_by: superpowers/brainstorming)
3. `skills/verification_before_completion/SKILL.md` 신설 (~50 LOC, inspired_by: superpowers/verification-before-completion)
4. `core/utils.py` `get_external_skill_roots()` L275~283에 `PROJECT_ROOT/skills/` 경로 추가 (Tier 2 review-gate 필수)

**Why (핵심 발견):**
- Phase B cross-review WARN 판정. 주요 발견: `core/utils.py:275~283`의 `get_external_skill_roots()`가 `PROJECT_ROOT/skills/`를 스캔 안 함 → Phase C SKILL.md 자동발견 불가. 구현 시 반드시 수정.
- 외부 import 0건 원칙 (§5.2): SKILL.md는 패턴만 흡수, `inspired_by:` 메타 필수 (CLAUDE.md §스킬흡수귀속정책)

**How to apply:**
- Phase C 시작 전 `core/utils.py:275~283` 확인 후 `skills/` 경로 추가 먼저 구현
- Tier 2 파일(core/utils.py)이므로 af-critic → af-cross-review → af-test-runner 순서
- SKILL.md는 문서 전용, review-gate 자동 통과

## 관련
- [[code/symbols]]

