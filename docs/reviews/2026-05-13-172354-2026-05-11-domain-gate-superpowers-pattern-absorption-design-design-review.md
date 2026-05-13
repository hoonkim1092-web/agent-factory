# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:23
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

> Critic verdict was WARN (0 Critical, 5 High, 5 Medium, 1 Low). Cross-review provider errored out mid-execution (Codex stdin read aborted) so single-reviewer findings are evaluated against the original document directly. All 5 High findings have verifiable evidence in the design text or code references — proceed with caution, fix accepted items before Phase A implementation. Re-run cross-review after corrections to upgrade confidence.

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [High] Migration §10.2 stage 1을 코드로 강제할 수단 부재
- **Critic**: `require_domain_review(blast_radius)` 시그니처에 활성화 스위치 없음. stage 1↔stage 2 전환을 코드 commit으로만 표현 가능, policy 위치 미정.
- **Cross**: not flagged (provider error).
- **Judgment**: 설계 §3.3은 `blast_radius=="system_wide"`만 본다. stage 1(전 work-item False)을 켤 인프라가 없으면 stage 1과 stage 2는 동일 코드 = 1단계 무의미. 본문 §10.2와 §3.3 사이에 누락된 메커니즘이 분명히 있다.
- **Action Required**: §3.3에 `policy.yaml: domain_gate.enabled: false` 키 추가 또는 `require_domain_review(blast_radius, *, enabled: bool)` 시그니처 명시. stage 전환 절차를 §10.2에 한 줄로 (e.g., "yaml commit 1회").

#### 2. [ACCEPT] [High] §12 Q4가 §6.1/§7.3/§10.3과 정면 충돌
- **Critic**: §6.1·§7.3·§10.3은 "옵션 A 채택" 명시, §12 Q4 잠정 답은 "옵션 B". 이전 라운드(5/13-164931, 164952, 165049) 동일 finding 반복.
- **Cross**: not flagged (provider error).
- **Judgment**: 문서 내부 모순. memory `feedback_design_review_rounds_stop_rule.md`의 "finding 즉시 정정" 항목에 직접 해당. 구현자가 §12를 truth로 읽으면 옵션 B로 진행.
- **Action Required**: §12 Q4 행을 취소선 처리 + CLOSED 2026-05-13 → 옵션 A로 통일, 또는 표에서 행 삭제.

#### 3. [ACCEPT] [High] `domain-review.md` 템플릿 default verdict 미정
- **Critic**: §3.4는 허용값(`PASS`|`NEEDS_ADR`|`BLOCK`)만 명시. default 값 미정. PASS면 silent 통과(theater), BLOCK면 매번 수정 필요, 빈 값이면 system_wide work-item 전체 즉시 fail-closed.
- **Cross**: not flagged.
- **Judgment**: §3.2의 fail-closed 정책과 §7.1 템플릿 신설 사이에 명세 갭. Phase A 구현 직전 결정 강제됨.
- **Action Required**: §3.4 또는 §7.1에 "신규 work-item 자동 생성 시 verdict default = (빈 값, fail-closed 권장)" 한 줄 추가.

#### 4. [ACCEPT] [High] `ApprovalGate._render()` 변경 누락
- **Critic**: §3.2/§7.2가 `_parse()` 변경만 명시. `_render()`는 `## Metadata`를 직렬화하므로 `work_kind`/`blast_radius` emit도 필수. 미수정 시 신규 work-item Metadata에 두 필드 누락 → `_parse()`가 `missing_domain_frontmatter` BLOCK.
- **Cross**: not flagged.
- **Judgment**: parse/render 비대칭은 직후 자기검증 실패로 직결. memory `feedback_post_edit_checklist.md`의 양방향 변경 의무에 부합.
- **Action Required**: §3.2와 §7.2에 `_render()` 변경 항목 추가, LOC를 +15~25 상향(§7.5도 함께 정정 — 7번 finding과 묶음).

#### 5. [ACCEPT] [High] `domain-review.md` 변경 감지 메커니즘 미정 — 승인 후 verdict 위조 경로
- **Critic**: §3.2가 명시적으로 snapshot에서 격리. 그러면 `_DOC_FILES` 4개 파일과 달리 hash invalidation을 받지 못함. "approve 시점 PASS → 실행 직전 BLOCK" 또는 "PASS → 실행 중 NEEDS_ADR" 검출 불가.
- **Cross**: not flagged.
- **Judgment**: 게이트 보안 정의에 직결되는 구조적 누락. 설계가 격리를 선택한 사유(기존 work-item 일괄 무효화 회피)는 합리적이나 대체 invalidation이 없음.
- **Action Required**: 둘 중 하나 — (a) `domain-review.md`를 별도 snapshot entry로 hash 추적, 또는 (b) `approve()` 시점 verdict를 gate state에 영구 기록 후 `is_execution_open()`에서 재검증. §3.5에 회귀 케이스 추가.

#### 6. [ACCEPT] [Medium] `last_block_reason` 리셋 시맨틱 미정
- **Critic**: 동일 인스턴스 `approve()` N회 호출 시 stale 사유 누출 가능. §3.5 검증 #4는 default=="" 만 확인.
- **Cross**: not flagged.
- **Judgment**: 흔한 stateful instance 버그 패턴. `approve()` 진입 시 리셋만 추가하면 해결.
- **Action Required**: §3.2에 "`approve()` 진입 직후 `self.last_block_reason=""` 리셋" 한 줄, §3.5에 2회 연속 호출 회귀 케이스 추가.

#### 7. [ACCEPT] [Medium] `_copy_extra_templates` 무조건 복사 — non-system_wide 노이즈
- **Critic**: `extra` 무조건 4파일 복사가 되면 isolated/module 변경에도 빈 domain-review.md 생성 → diff 노이즈.
- **Cross**: not flagged.
- **Judgment**: 기능적으로 무해하나 "왜 이게 있어?" 혼란 + git diff 누적. memory `feedback_temp_test_cleanup.md`의 git 노이즈 회피 정신과 정합.
- **Action Required**: §3.2에 "Phase A는 무조건 복사 (인프라 검증), Phase stage 3+에서 `blast_radius=="system_wide"`로 좁힘" 명시. 또는 `_copy_extra_templates(..., blast_radius=None)` 시그니처 확장.

#### 8. [ACCEPT] [Medium] Phase A LOC 추정 불일치
- **Critic**: §7.5 Python ~140 vs §7.2 표 합계 ~200 vs §3.2 행별 합계 ~195. ±50%로도 커버 어려운 갭.
- **Cross**: not flagged.
- **Judgment**: 단순 산술 정합. finding #4(`_render` +15~25)와 함께 정정 필요.
- **Action Required**: §7.5 Phase A Python ~140 → ~200~220로 정정, ±50% bound 재계산.

#### 9. [ACCEPT] [Medium] §13 base path가 §3.2와 모순 (`workspace/` vs `doc_root/`)
- **Critic**: §3.2는 `doc_root/docs/work-items/<slug>`, §13 체크리스트는 `workspace/docs/...`. 외부 target_path 환경에서 path mismatch.
- **Cross**: not flagged.
- **Judgment**: 5/13 review Medium #5의 해소 항목과 §13이 어긋남. memory `feedback_design_doc_grep_before_write.md`의 4번째 회귀 후보.
- **Action Required**: §13 해당 줄을 "base path = `doc_root/docs/work-items/<slug>` (doc_root = abs target_path or workspace fallback)"로 정정.

#### 10. [ACCEPT] [Medium] §3.5 #12 검증 항목이 §12 Q5 잠정 답과 충돌
- **Critic**: Q5가 "후자(텍스트 통합, LOC 절약)"면 `core/brainstorm_prompts.py`는 생성 안 됨 → §3.5 row 12는 vacuous PASS.
- **Cross**: not flagged.
- **Judgment**: 검증 항목으로서 실질 가치 0. Phase A vs Phase C 항목 분류 오류.
- **Action Required**: §3.5 row 12를 Phase C 검증으로 이동하거나 "Phase C 결과 의존" 표기 추가.

#### 11. [ACCEPT] [Low] §4.4 "우선순위" 컬럼이 §4.3 정성 규칙과 불일치
- **Critic**: §4.3은 산술 공식 폐기, §4.4는 9/8/3/-1/0 숫자 잔존. Phase B 진행자가 산술 부활 우려.
- **Cross**: not flagged.
- **Judgment**: 잔재 표기로 추정. 의미가 있으면 명시, 없으면 정성 라벨로 교체.
- **Action Required**: §4.4 컬럼을 "분류(즉시/선택적/보류)"로 교체 또는 §4.3에 "참고용 정렬 키" 한 줄 첨부.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Migration stage 1 enforcement gap | High | ACCEPT | Critic |
| 2 | §12 Q4 vs §6.1/§7.3/§10.3 모순 | High | ACCEPT | Critic |
| 3 | domain-review.md default verdict 미정 | High | ACCEPT | Critic |
| 4 | `_render()` 변경 누락 (parse/render 비대칭) | High | ACCEPT | Critic |
| 5 | domain-review.md 변경 감지 부재 | High | ACCEPT | Critic |
| 6 | `last_block_reason` 리셋 누락 | Medium | ACCEPT | Critic |
| 7 | `_copy_extra_templates` 무조건 복사 | Medium | ACCEPT | Critic |
| 8 | Phase A LOC 추정 불일치 | Medium | ACCEPT | Critic |
| 9 | §13 base path 모순 | Medium | ACCEPT | Critic |
| 10 | §3.5 #12 ↔ §12 Q5 충돌 | Medium | ACCEPT | Critic |
| 11 | §4.4 우선순위 숫자 잔재 | Low | ACCEPT | Critic |

### Recommendations

1. **즉시 정정 (5 High, 문서 편집만으로 가능)**:
   - §12 Q4 행 정정 (finding #2)
   - §13 base path 정정 (finding #9)
   - §3.4에 verdict default 값 한 줄 추가 (finding #3)
   - §3.2/§7.2에 `_render()` 변경 항목 명시 (finding #4) + §7.5 LOC 정정 (finding #8)
   - §3.2에 stage 1 활성화 스위치(policy.yaml 또는 시그니처) 명시 (finding #1)
2. **보안 갭 결정**: §3.2 또는 §3.5에 domain-review.md post-approval invalidation 정책 명시 (finding #5) — 옵션 (a) snapshot entry vs (b) gate state 영구 기록 중 택일.
3. **Medium 정리**: finding #6, #7, #10, #11은 한 commit으로 묶어 정정.
4. **재검증**: 위 정정 후 **af-cross-review 재실행** — 이번 라운드는 cross-review 결과 부재(provider error)로 단일 시각. memory `feedback_design_review_rounds_stop_rule.md`의 3라운드 cap 카운트는 이번 부분 응답을 1라운드로 산입할지 다음 세션에서 판단.
5. **사전 grep 의무 재확인**: finding #2(`local` 회귀)와 #9(base path) 모두 memory `feedback_design_doc_grep_before_write.md`의 4·5번째 회귀 후보 — 정정 후 `grep -n 'blast_radius\|work_item_dir' core/` 결과를 §3.2에 인용하여 회귀 차단.