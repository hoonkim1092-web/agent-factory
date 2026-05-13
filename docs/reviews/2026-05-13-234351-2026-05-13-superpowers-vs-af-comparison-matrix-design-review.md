# Design Review: 2026-05-13-superpowers-vs-af-comparison-matrix

> Source: docs/2026-05-13-superpowers-vs-af-comparison-matrix.md
> Date: 2026-05-13 23:43
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

High findings exist across both reviews. Can proceed to Phase C implementation with specific document corrections required first.

---

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [High] `skills/` root not in skill discovery path
- **Critic**: `get_external_skill_roots()` (core/utils.py:275–283) scans `~/.claude/skills`, `PROJECT_ROOT/.claude/skills`, `~/.codex/skills` but NOT `PROJECT_ROOT/skills/`. Phase C SKILL.md files will not be auto-discovered.
- **Cross**: Not flagged independently, but Cross #1 (metadata contract) is predicated on the same discovery pipeline — both issues block the same path.
- **Judgment**: Critic provides line-level code evidence. Phase C Step 5 ("core/skill_loader.py 자동 발견") is underspecified as a fix — `core/utils.py` or `skill_autodiscover.py` must be explicitly named as a Tier 2 change.
- **Action Required**: §7 Step 5를 "core/utils.py `get_external_skill_roots()`에 `PROJECT_ROOT/skills/` 추가 (Tier 2 리뷰 게이트 대상)" 로 구체화. 기존 `skills/git_master/` 로드 경로 선확인 필요.

---

#### 2. [ACCEPT] [High] brainstorming → `domain-review.md` 통합 목적 불일치
- **Critic**: `domain-review.md`는 ADR 충돌 검사 게이트 문서 (verdict: PASS/NEEDS_ADR/BLOCK). Socratic 9단계는 설계 전 발산·수렴 프로세스 — 목적이 이질적. `approval_gate.py`의 `verdict:` 파싱 정합성 불명확.
- **Cross**: 동일 섹션 지적 — 현재 domain-review.md (docs/work-items/_template/domain-review.md:26)에 checklist/status 필드 없음. Socratic 완료 검증 불가.
- **Judgment**: 양측 동일 파일·섹션을 각각 다른 각도에서 지적. Critic은 구조적 충돌, Cross는 실행 불가능성. 합산 신뢰도 High.
- **Action Required**: §4.1 흡수 형태 수정 — brainstorming을 `domain-review.md` 통합 대신 `skills/brainstorming/SKILL.md` 독립 신설로 변경. `domain-review.md`는 게이트 문서로 유지.

---

#### 3. [ACCEPT] [Medium] `verification-before-completion` 구현 경로 미확정
- **Critic**: `scripts/review_gate.py` 수정 = Tier 2 파이프라인 유발 (D=Medium 이상). SKILL.md 신설 = 문서 전용 (D=Low). §4.2의 "또는" 표기로 LOC 추정(~50 LOC)이 최대 5배 차이 가능.
- **Cross**: 동일 이분법 지적 — review_gate.py는 commit blocker, SKILL.md는 advisory. 구현자가 둘 중 하나를 선택할 수 없는 상태 (scripts/review_gate.py:166, core/agent_runner.py:681 증거).
- **Judgment**: 양측 독립 코드 증거로 동일 문제 확인.
- **Action Required**: §4.2에서 "또는" 표기 제거. "Iron Law를 AF 자동화 커밋 차단으로 강제할 것인가, 에이전트 가이드라인으로 족한가"를 Phase C 착수 전 확정하고 단일 경로 기재.

---

#### 4. [ACCEPT] [Medium] 신설 SKILL.md 메타데이터 계약 미명시
- **Critic**: not flagged
- **Cross**: `skill_metadata_adapter.py:403`이 frontmatter 파싱, `skill_loader.py:252`가 메타데이터 점수 기반 자동 선택. `description`, `when_to_use`, `when_to_use_keywords`, `category`, `skill_type`, `auto_invocable` 필드 요구.
- **Judgment**: 코드 라인 레벨 증거 강함. §4.1~4.2 SKILL.md 신설 항목에 frontmatter 스키마 미기재 — 구현자가 임의로 작성할 경우 런타임 자동 선택 실패 가능.
- **Action Required**: §4.1, §4.2 각 SKILL.md 항목에 필수 frontmatter 스키마 예시 추가 (`category`, `skill_type: knowledge`, `inspired_by` 포함).

---

#### 5. [ACCEPT] [Medium] `finishing-a-development-branch` B=3 하락 근거 미기재
- **Critic**: B=6→3 (50% 하락)으로 결정이 보류→선택적으로 변경됐으나 `core/git_manager.py`(152줄) + `skills/git_master/` 기존 스킬과의 gap이 구체적으로 명시되지 않음.
- **Cross**: not flagged
- **Judgment**: Critic 단독이나 코드 파일명·줄 수 인용으로 근거가 명확. "6단계 중 어느 단계가 미구현"인지 공백은 Phase C 범위 결정에 직접 영향.
- **Action Required**: §3 비교표 `finishing-a-development-branch` 변경 사유 셀에 "6단계 중 [단계명]이 `core/git_manager.py` 미구현" 수준으로 구체화. `skills/git_master/`와 신설 `skills/finishing_branch/SKILL.md`의 관계(확장 vs 독립) 결정 기재.

---

#### 6. [ACCEPT] [Medium] knowledge 스킬 usage logging 미연결
- **Critic**: not flagged
- **Cross**: `agent_runner.py:1131` loaded skill ids 수집, but `used_skill_ids_runtime`은 tool 실행 시(`agent_runner.py:1475`)만 업데이트. 멀티스킬 로드 시 feedback target resolution 스킵(`agent_runner.py:728`). knowledge SKILL.md 호출이 `data/skill-usage.jsonl`에 기록되지 않을 가능성.
- **Judgment**: 코드 3개 라인 증거. §7 Step 5의 "호출 기록" 목표가 현 구현으로는 달성 불가.
- **Action Required**: §7 Step 5에 "knowledge skill 자동 선택 시 `SkillFeedbackLoop.record_selection()` 명시적 호출" 추가 또는 별도 Step으로 분리.

---

#### 7. [HOLD] [Low] 점수 산출 재현 불가 — 외부 소스 고정 필요
- **Critic**: LOC 추정치 출처(Superpowers 소스 실독 vs Explore 추정) 불명확.
- **Cross**: Superpowers 저장소 commit SHA, 파일 경로, 발췌 없음. 소스 변경 시 점수 재산정 필요.
- **Judgment**: 양측 동일 우려. 단, Phase B 완료 보고서 성격상 재현 가능성보다 의사결정 추적이 주목적. 구현 시작 후 소스가 바뀌어도 이미 내려진 결정은 유효. 그러나 Phase C LOC 추정이 의존하는 경우 실측 차이 발생 가능.
- **Question for Author**: Superpowers 소스가 공개 저장소에 고정 버전이 있는가? 있다면 commit SHA/tag를 §1 "방법" 행에 1줄만 추가하면 충분.

---

#### 8. [REJECT] [Low] 대문자 `SKILL.md` 디스커버리 불가 우려
- **Source**: Cross #5
- **Original Finding**: AF가 `SKILL.md`를 인식 못할 수 있다는 초기 우려.
- **Rejection Reason**: `core/skill_metadata_adapter.py:403`이 `SKILL.md`와 `skill.md` 모두 명시적 스캔. `core/agent_runner.py:681`의 `resolve_knowledge_skill_path()`가 대소문자 구분 없이 처리. Cross 리뷰어 본인이 코드 근거로 REJECT 처리함.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `skills/` root excluded from discovery | High | ACCEPT | Critic |
| 2 | brainstorming → domain-review.md 목적 불일치 | High | ACCEPT | Both |
| 3 | verification-before-completion 구현 경로 미확정 | Medium | ACCEPT | Both |
| 4 | SKILL.md frontmatter 계약 미명시 | Medium | ACCEPT | Cross |
| 5 | finishing-branch B=3 하락 근거 미기재 | Medium | ACCEPT | Critic |
| 6 | knowledge 스킬 usage logging 미연결 | Medium | ACCEPT | Cross |
| 7 | 점수 산출 외부 소스 고정 미기재 | Low | HOLD | Both |
| 8 | 대문자 SKILL.md 디스커버리 | Low | REJECT | Cross |

---

### Recommendations

Phase C 착수 전 문서에서 해결 필요:

1. **§7 Step 5 구체화** — `core/utils.py get_external_skill_roots()`에 `PROJECT_ROOT/skills/` 추가를 명시적 Tier 2 변경 항목으로 기재.
2. **§4.1 brainstorming 흡수 경로 변경** — `domain-review.md` 통합 → `skills/brainstorming/SKILL.md` 독립 신설로 수정.
3. **§4.2 verification-before-completion 경로 단일화** — "또는" 제거, `review_gate.py` vs SKILL.md 중 하나로 확정.
4. **§4.1~4.2 SKILL.md 항목에 frontmatter 스키마 추가** — 최소 `category`, `skill_type`, `when_to_use_keywords`, `inspired_by` 명시.
5. **§3 finishing-branch 변경 사유 보강** — "6단계 중 미구현 단계" 및 `git_master` 관계 1~2줄 기재.
6. **§7 usage logging 항목 추가** — knowledge 스킬 `record_selection()` 연결을 별도 Step으로 분리.