# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:25
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

> **Note**: Cross Review failed with a provider error (`gpt-5.5` model unavailable / Codex stdin read failure). Aggregation is based on Critic Review only. Per memory `feedback_design_review_rounds_stop_rule.md`, this is **round 4** of the design — 3-round cap reached. Recommend either (a) re-run Tier 3 cross-review with a valid model (e.g. `gpt-5` or `gpt-5-codex`) before final sign-off, or (b) freeze remaining findings as ADRs and proceed.

### Aggregated Findings (12 total + 4 missing)

#### 1. [ACCEPT] [Critical] ApprovalGate ↔ work_item_generator LOC 분담이 `_render()`/`initialize()` 구조와 모순
- **Critic**: §3.2 표가 `approval-gate.md ## Metadata` 쓰기를 work_item_generator(~40 LOC)에 할당하나, 실제로 `ApprovalGate._render()` (core/approval_gate.py:496-540)가 하드코딩된 4필드만 emit. work_kind/blast_radius 기재는 (a) `initialize()` 시그니처 확장 (b) `_render()` 확장 (c) `_parse()` 확장 (d) `approve()`/`invalidate()` 호출부 보존 — 전부 `core/approval_gate.py` 내 변경.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 코드 라인 번호 직접 인용 + 4단계 변경 경로 명시. 메모리 `feedback_design_doc_grep_before_write.md`가 강조한 grep 의무를 통과한 실측 근거.
- **Action Required**: §3.2 두 행을 **approval_gate.py ~120 LOC** (`_render`/`_parse`/`initialize` 확장 + verdict 파서 + `last_block_reason` + `_DOMAIN_REVIEW_FILE`) / **work_item_generator.py ~10 LOC** (시그니처 + 호출 전달) 로 재배분. §3.5 #8에 `_render()` 라운드트립 보존 회귀 fixture 추가.

#### 2. [ACCEPT] [High] `last_block_reason` 리셋 미정의 — 멱등 분기에서 stale 위험
- **Critic**: §3.2가 `__init__` 초기화만 명시, `approve()` entry 리셋 의무 누락. 멱등 가드(approval_gate.py:184-191) 통과 시 직전 실패의 stale "blocked" 값이 노출됨.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 멱등 분기 코드 라인 인용 + stale 시나리오 구체.
- **Action Required**: §3.2 verdict 파서 절에 "`approve()` entry: `self.last_block_reason = ""` 무조건 리셋 (멱등 True 분기 직전 포함)" 1줄 + §3.5 #4에 차단→재호출 정상화 검증 추가.

#### 3. [ACCEPT] [High] verdict 누락 사유 enum이 파일 부재 vs frontmatter 누락 혼동
- **Critic**: `"missing_domain_frontmatter"`는 명칭상 YAML frontmatter를 의미하나 본 설계는 frontmatter 폐기 결정. 파일 부재와 verdict 라인 0건이 같은 코드로 묶이면 "템플릿 미복사" vs "리뷰 미완성" 구분 불가.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 명칭-의미 불일치는 명확한 결함.
- **Action Required**: enum 재명명 — `"domain_review_file_missing"` | `"missing_verdict"` | `"multiple_verdicts"` | `"domain_review_blocked"` | `"domain_review_needs_adr"`. `"missing_domain_frontmatter"` 폐기. §3.4에 3-way 분기 의사코드.

#### 4. [ACCEPT] [High] `requires_domain_review` 정책 저장 위치 미명세 — frozen build 회귀 위험
- **Critic**: §3.3 단계 1/2 전환 결정자는 사용자 commit이라 했으나 저장 위치(상수/policy.yaml/env) 미명시. 하드코딩 상수면 dist/af 재빌드 필수.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 배포 모델(frozen build)에 직접 영향.
- **Action Required**: §3.3에 "정책 저장: `policy.yaml` `domain_gate.enabled_for_blast_radius: ["system_wide"]` 키 신설, `core/policy.py` 로더 재사용. `AF_SKIP_DOMAIN_REVIEW=1` 환경변수 우회만 유지" 명시.

#### 5. [ACCEPT] [Medium] `ControlPlaneIntake.normalize()` 자체 작동 검증 누락
- **Critic**: 호출자 0건 = production trace 미실행. 6개 서브시스템 silent except (intake.py:158/182/191/205/223/233 `except: print`)로 `change_impact={}` 빈 dict 반환 가능.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. silent except 라인 직접 인용. Phase A 도입 직전 회귀 차단 가치 큼.
- **Action Required**: §3.5에 `tests/test_control_plane_intake_e2e.py` 신설 — `NormalizedRequest.change_impact.blast_radius` non-empty 검증.

#### 6. [ACCEPT] [Medium] ADR 파일명 `ADR-YYYYMMDD-HHMM-...`이 CLAUDE.md 문서 규칙과 충돌
- **Critic**: CLAUDE.md는 `YYYY-MM-DD-제목.md` 강제. dash 없는 `YYYYMMDD`는 docs 인덱스/codex 회고 파서 정규식에 미매칭.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. CLAUDE.md 규칙(프로젝트 instructions OVERRIDE)과 정면 충돌.
- **Action Required**: `ADR-2026-05-13-1640-<slug>.md` 형식 채택 또는 `decisions/` 예외를 CLAUDE.md에 명시.

#### 7. [ACCEPT] [Medium] §3.5 #10 "기본값 False 배포" vs §3.5 #5 "True 분기 검증" 충돌
- **Critic**: Phase A 검증이 "False 배포 + True 분기 작동 측정"을 동시 요구. fixture 강제 활성 명시 없음.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 검증 절차 모호성.
- **Action Required**: §3.5 #5에 "fixture: `monkeypatch.setenv('AF_FORCE_DOMAIN_REVIEW', '1')` 또는 `policy.yaml` override로 강제 활성한 상태 측정" 1줄.

#### 8. [HOLD] [Medium] Phase C brainstorming 흡수 형식(.py vs markdown) 미결정 → 일정 불확정
- **Critic**: (a) `.py` 신설이면 af.spec hiddenimports + version bump + 재배포 의무. (b) markdown만이면 X. Phase B 결과 대기지만 일정 추정에 if-분기 발생.
- **Cross**: not flagged (review failed)
- **Judgment**: HOLD. Phase B 결과(2026-05-14 예정)에 의존하므로 지금 결정 불가. 단, §5.1 표에 default 가정만 명시하면 unblock 가능.
- **Question for Author**: Phase B 결과 도출 시점에 형식 결정 트리거가 무엇인가? §5.1 표에 "default: markdown only, .py 채택 시 +1일" 명시 의사 있는지.

#### 9. [ACCEPT] [Medium] §5.3 #3 "skill-usage.jsonl 호출 ledger" — guide-style 스킬의 "호출" 정의 부재
- **Critic**: `systematic_debugging`은 .py 없는 markdown-only. `data/skill-usage.jsonl`은 .py invocation 시점 기록. 측정 신호 정의 불가.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 측정 기준 부재.
- **Action Required**: §5.3 #3을 "`skill_loader.discover()` 결과에 `systematic_debugging` 등장 + retrieval 키워드 매칭 1건"으로 교체, 또는 통합 검증으로 일원화.

#### 10. [ACCEPT] [Low] §3.4 verdict 정규식 모드/주석 처리 모호
- **Critic**: `^...$`이 MULTILINE인지, 인라인 주석 허용 여부 미명시.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 작성자 혼란 방지용 명시 필요.
- **Action Required**: `re.compile(r'^- verdict:\s*(PASS|NEEDS_ADR|BLOCK)\s*$', re.MULTILINE)` 명시 + 인라인 주석/추가 텍스트 금지 1줄.

#### 11. [ACCEPT] [Low] §10.3(옵션 A 채택) vs §12 Q4(옵션 B 잠정 답) 내부 모순
- **Critic**: 동일 문서 내 결정 상태 불일치.
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT. 단순 일관성 결함.
- **Action Required**: §12 Q4 잠정 답을 "옵션 A (§10.3 확정)"로 갱신, Q4를 §11 Decision Trail로 이동.

#### 12. [ACCEPT] [Info] `agent_launcher.py` 2벌 존재 → 변경 대상 명확화
- **Critic**: `./agent_launcher.py` (canonical) vs `./.a/agent_launcher.py` (다른 코드, L437-441 내용 다름).
- **Cross**: not flagged (review failed)
- **Judgment**: ACCEPT.
- **Action Required**: §3.2에 "변경 대상: 레포 루트 `agent_launcher.py` only. `.a/agent_launcher.py`는 백업 사본, 범위 외" 1줄.

### Missing from Design (Critic, ACCEPT all 4)

- **frozen build 회귀 시나리오** — Finding #4와 연결, policy.yaml 변경만으로 단계 전환 가능 여부 명시 의무.
- **multi-PC ADR 번호 경합** — 야간 자율 파이프라인 동시 실행 시 ADR-2026-05-13-1640-* 충돌 빈도. `start_db`/`end_db` 동기화 범위 명시 필요.
- **`hook_events.log` 기록 포맷** — bypass 발동 시 필드/형식 미정. `scripts/hook_runner.py:121` 기존 포맷 정합성 확인.
- **`PROJECT_CONTEXT.md` 손상/누락 시 동작** — fail-open vs fail-closed 미정 (§9 리스크 #1은 stale만 다룸).

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | ApprovalGate LOC 분담 모순 | Critical | ACCEPT | Critic |
| 2 | `last_block_reason` 멱등 stale | High | ACCEPT | Critic |
| 3 | verdict reason enum 명칭 오류 | High | ACCEPT | Critic |
| 4 | 정책 저장 위치 미명세 | High | ACCEPT | Critic |
| 5 | ControlPlaneIntake e2e 검증 누락 | Medium | ACCEPT | Critic |
| 6 | ADR 파일명 CLAUDE.md 충돌 | Medium | ACCEPT | Critic |
| 7 | 배포 default vs 검증 fixture 충돌 | Medium | ACCEPT | Critic |
| 8 | Phase C 형식 미정 | Medium | HOLD | Critic |
| 9 | skill-usage.jsonl "호출" 정의 부재 | Medium | ACCEPT | Critic |
| 10 | verdict 정규식 모호 | Low | ACCEPT | Critic |
| 11 | §10.3 vs §12 Q4 모순 | Low | ACCEPT | Critic |
| 12 | agent_launcher.py 2벌 | Info | ACCEPT | Critic |
| M1 | frozen build 회귀 | High | ACCEPT | Critic |
| M2 | multi-PC ADR 경합 | Medium | ACCEPT | Critic |
| M3 | hook_events.log 포맷 | Low | ACCEPT | Critic |
| M4 | PROJECT_CONTEXT 누락 동작 | Medium | ACCEPT | Critic |

### Recommendations

**Before Phase A implementation begins:**

1. **[Critical, BLOCK]** Finding #1 — §3.2 표의 LOC 분담을 `approval_gate.py ~120 / work_item_generator.py ~10`으로 재배분. `_render()`/`_parse()`/`initialize()` 확장 + `_render()` 라운드트립 회귀 fixture (§3.5 #8) 추가.
2. Finding #2~#4 (High) 일괄 정정 — last_block_reason 리셋 의무, reason enum 재명명, policy.yaml 저장 위치 명시.
3. Missing #1 (frozen build) + Finding #4 묶음 처리 — `policy.yaml`로 통일하면 둘 다 해소.
4. Finding #5 — ControlPlaneIntake e2e 테스트를 Phase A 진입 직전 필수 게이트로 추가.
5. Finding #8 (HOLD) — §5.1 표에 "default: markdown only" 가정 명시하면 unblock. Phase B 결과 변경 시 +1일 패널티만 적용.
6. Finding #6, #7, #9~#12 + Missing #2~#4 — 짧은 정정 (총 ~30 LOC of doc).
7. **Tier 3 cross-review 재실행** — Codex 프로바이더 모델을 `gpt-5` / `gpt-5-codex`로 교체 후 재발화 (현재 `gpt-5.5` unavailable).
8. 메모리 `feedback_design_review_rounds_stop_rule.md` 적용 — 4라운드째 도달. 잔여 finding 중 즉시정정 불가한 것은 ADR로 이월 후 Phase A 진입.