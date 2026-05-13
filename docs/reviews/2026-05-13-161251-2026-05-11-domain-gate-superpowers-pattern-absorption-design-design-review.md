# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:12
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Critical 식별자 mismatch (`"system"` vs `"system_wide"`)와 `_DOC_FILES` 확장으로 인한 기존 work-item 일괄 무효화 위험이 양쪽 리뷰에서 확인됨. 추가로 통합 경로·frontmatter 포맷·예외 클래스 정의가 모두 미정의 상태로 구현 진입 불가.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] `blast_radius` 식별자가 실제 코드 산출값과 불일치
- **Critic** (#1): `change_impact.py:35, 211-243`의 실제 산출값은 `"system_wide"`. `"system"` 단독 토큰은 어디서도 산출되지 않아 `require_domain_review()`가 영원히 False 반환.
- **Cross** (#1): 동일 — `core/control/change_impact.py:16, 217` 모두 `"system_wide"` 사용. Phase A 시행 시 silently never trigger.
- **Judgment**: 두 리뷰 강하게 일치. 5/11 review에서 work_kind 식별자(`feature` → `feature_update`)를 정정한 것과 같은 부류의 회귀.
- **Action Required**: §3.3 `"system"` → `"system_wide"` 일괄 교체 (§3.2 트리거 분기 설명, §3.3 정책 분기 코드, §10.2 단계 2/4 표기, §13 체크리스트 #13, §3.3 "잡히는 케이스" 표). `system_wide` 회귀 테스트 추가.

#### 2. [ACCEPT] [Critical] `_DOC_FILES`에 `domain-review.md` 추가가 기존 work-item 일괄 무효화 유발
- **Critic** (#2): `_DOC_FILES`는 `compute_snapshots()` (L378-384), `check_validity()` (L364-376) 등에서 참조. 기존 승인된 work-item이 `snapshots["domain_review"]=""` 상태에서 새 파일 생성 순간 "변경" 분류되어 `is_execution_open()`이 False로 강제됨. `_copy_extra_templates()` (work_item_generator.py:1394)는 3개 파일만 복사 → 새 work-item에도 propagate되지 않음.
- **Cross**: not flagged
- **Judgment**: Critic만 발견했으나 코드 라인 직접 인용으로 evidence 매우 강함. 단계 1(False) 출시여도 `_DOC_FILES`에 등재되면 snapshot 비교가 발화되므로 영향 실제 발생.
- **Action Required**: (a) `_DOC_FILES`에 추가하지 말고 `_OPTIONAL_DOC_FILES` 또는 `_DOMAIN_REVIEW_FILE` 별도 상수 신설, (b) §7.2에 `_copy_extra_templates()` `extra` 집합에 `domain-review.md` 추가, (c) 단계 1 출시에서 기존 work-item 회귀 0건 마이그레이션 테스트 명세 추가.

#### 3. [ACCEPT] [High] `generate_work_items()` 호출부에 `NormalizedRequest`가 도달하지 않음
- **Critic** (#3): `generate_work_items()` (work_item_generator.py:1072-1079)는 `workspace, slug, project_brief, role_plan, task_board, run_id`만 받음. `core/project_pipeline.py:963` 호출부에도 `work_kind`/`change_impact` 전달 없음. "호출부 회귀 0" 주장과 모순.
- **Cross** (#2): 동일 — `prepare_documents()`는 `_recall_from_memory()`만 호출. 옵션 (iii) frontmatter 경로 미연결.
- **Judgment**: 두 리뷰 일치, 코드 라인 인용도 일치.
- **Action Required**: §3.2에 두 가지 중 택1 명시 — (i) `generate_work_items(..., work_kind: str = "", blast_radius: str = "")` 키워드 추가 + "호출부 회귀 0" 주장 철회, (ii) `project_brief["control_plane"]` 예약 키 첨부 경로 명시.

#### 4. [ACCEPT] [High] 기존 work-item 템플릿은 YAML frontmatter 없음 — read 형식 미정의
- **Critic** (#4): `docs/work-items/_template/feature-plan.md` 등 5개 템플릿에 YAML frontmatter 없음. `ApprovalGate._parse()` (L437-490)는 `approval-gate.md` 1개만 파싱. frontmatter 위치(YAML 블록 vs `## Metadata` 섹션 vs 신규 metadata.json) 미정.
- **Cross**: not flagged directly (그러나 #3과 부분 중첩)
- **Judgment**: Critic 단독이나 evidence 명확. read 형식 미정의 상태에서 구현 불가.
- **Action Required**: §3.2에 (a) frontmatter 위치를 `approval-gate.md ## Metadata` 섹션 확장 vs feature-plan.md YAML frontmatter 중 택1 명시, (b) `_parse()` 또는 신규 `_read_work_kind()` 메서드 시그니처/예외 정책 명시, (c) §7.2 LOC 예산에 반영.

#### 5. [ACCEPT] [High] `domain-review.md` verdict 파싱 계약 미정의
- **Critic**: not flagged
- **Cross** (#3): 체크박스 prose만 있고 파싱 규칙 미정 — 다중 체크, 대소문자, 누락 처리 방식 모두 미정. `approval_gate.py:366`에 재사용 가능한 markdown verdict parser 없음.
- **Judgment**: Cross 단독이나 구현 시 즉시 막히는 부분. evidence 강함.
- **Action Required**: 한 줄 machine-readable line 정의 (예: `- verdict: PASS|NEEDS_ADR|BLOCK`). `_read_domain_review_verdict(path) -> Literal[...]` 구현. 누락/무효/다중은 fail-closed + distinct reason.

#### 6. [ACCEPT] [High] `BlockedExecutionError` 클래스가 존재하지 않음
- **Critic**: not flagged
- **Cross** (#4): `rg`로 `BlockedExecutionError` 검색 결과 0건. `approve()`는 `bool` 반환 (approval_gate.py:144). 구현자가 새 예외 클래스를 임의로 정의하거나 기존 caller 흐름과 충돌.
- **Judgment**: Cross 단독이나 코드 grep 결과로 확정. 예외 vs bool 반환 분기는 caller 전체에 영향.
- **Action Required**: 두 가지 중 택1 — (a) `core/approval_gate.py`에 `BlockedExecutionError` 정의 + callers/tests 갱신, (b) `approve()` False 반환 + `last_block_reason="missing_domain_frontmatter"` 노출.

#### 7. [ACCEPT] [High] §4.3 우선순위 공식과 §4.4 표가 산술적으로 불일치
- **Critic** (#5): D 난이도 가중치 수치 미정의. 표의 (9, 8, 3) 세 값이 어떤 가중치 조합으로도 동시에 성립하지 않음. brainstorming Medium=10이면 verification (7-5)×(10/10)=2 ≠ 표의 3.
- **Cross** (#7) HOLD: rubric이 정성 평가에 의존, evidence threshold 미정. 두 구현자가 다른 후보 도출 가능.
- **Judgment**: Critic 수학 검증이 더 강한 evidence. Cross의 HOLD를 ACCEPT로 격상.
- **Action Required**: §4.3 공식 폐기 후 §4.4를 정성 판단으로 표기 OR D 가중치 표 + 4종 모두 계산 과정 1줄씩 첨부. Phase C 후보 결정 근거 재정립.

#### 8. [ACCEPT] [Medium] `af.spec` hiddenimports 갱신 누락
- **Critic**: not flagged
- **Cross** (#5): 새 `core/*.py` 생성 시 `af.spec`에 hiddenimports 추가 의무. §7.3에 `core/brainstorm_prompts.py` 신설하지만 `af.spec` 미언급.
- **Judgment**: CLAUDE.md 규칙과 직접 충돌. evidence 명확.
- **Action Required**: §7.3 배포 체크리스트에 `core.brainstorm_prompts` hiddenimports 추가 + `version.py` bump + 설치 스크립트 갱신 명시.

#### 9. [ACCEPT] [Medium] bypass 메커니즘 결정을 Phase A 구현 시점으로 연기
- **Critic** (#6): 본 설계가 Phase A 진입 전 검토용인데 결정 연기. `AF_SKIP_DOMAIN_REVIEW=1` env vs `risk_level=="critical"` 자동 면제는 보안 함의 다름.
- **Cross**: not flagged
- **Judgment**: Critic 단독이나 5/11 review에서 동일 패턴 지적된 결정 부채 누적.
- **Action Required**: §3.3에 `AF_SKIP_DOMAIN_REVIEW=1`로 못박고 (CLAUDE.md `AF_SKIP_REVIEW_GATE` 선례 정합), hook_events.log 기록 의무 §7.2 추가. 자동 면제 후보는 폐기 명시.

#### 10. [ACCEPT] [Medium] §5.3 "12-cap 라우팅" 검증 기준 측정 불가
- **Critic** (#7): 12-cap 라우팅 기준이 본 doc과 `core/skill_registry.py`/`policy.yaml` 어디에도 정의되지 않음. 흡수 검증을 통과시킬 수도 차단할 수도 없는 모호한 게이트.
- **Cross**: not flagged
- **Judgment**: 측정 기준 부재는 검증 게이트 자체를 무효화.
- **Action Required**: "`core/skill_loader.py` 자동 발견 + `data/skill-usage.jsonl` 최소 1회 호출 기록" 같은 측정 가능 신호로 교체. 또는 "12-cap" 정의를 §5.3 또는 ADR로 사전 정의.

#### 11. [ACCEPT] [Medium] §3.5 회귀 테스트가 단계 1(False)만 검증 → True 분기 production 검증 0
- **Critic** (#9): #5는 단계 1 출시에서 기본값 False. #4 회귀 테스트가 통과해도 production 동작 검증 안 됨. 단계 2 활성 시점 회귀 테스트 진입 절차 §10.2에 없음.
- **Cross**: not flagged
- **Judgment**: Critic 단독이나 게이트 효과 검증 누락은 본 설계 핵심 목적 무력화.
- **Action Required**: `tests/test_approval_gate_domain_review.py`가 `requires_domain_review=True` 강제 fixture로 True 분기 항상 검증. 단계 2 활성 commit 전 dummy work-item end-to-end fail/recover 시나리오 추가.

#### 12. [ACCEPT] [Medium] §10.3 dead code 옵션 B 잔존이 §1.2 결정과 충돌
- **Critic** (#8): `af.spec:122` 1줄 + `tests/test_compact_step2.py` + `Master_Blueprint.md` §3.8.4/§0 — 4파일 정정으로 처분 가능. 5/11 review에서 ACCEPT High로 반박된 사안. `core/skill_pack_bootstrapper.py` 잔존 시 §1.2 GStack 폐기 결정 무효.
- **Cross**: not flagged
- **Judgment**: 결정 부채 — 본 설계 채택 commit과 같은 PR에 처분 필요.
- **Action Required**: §10.3을 옵션 A(즉시 제거)로 뒤집고 §7.3 동기 변경 대상 4파일 명시.

#### 13. [REJECT] [Low] `runtime_workspace` 사용 우려
- **Source**: Cross (#6)
- **Original Finding**: doc-root/runtime-root split 과거 버그 이력으로 `runtime_workspace` 미사용이 위험.
- **Rejection Reason**: Cross 본인이 self-reject — work-item 문서는 doc root 사용이 정확함 (`ApprovalGate(workspace=doc_root, runtime_workspace=workspace)` 패턴 일치). 현재 generator도 동일 split 따름.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `blast_radius == "system"` 식별자 mismatch | Critical | ACCEPT | Both |
| 2 | `_DOC_FILES` 추가로 기존 work-item 무효화 | Critical | ACCEPT | Critic |
| 3 | `NormalizedRequest` 호출 경로 단절 | High | ACCEPT | Both |
| 4 | frontmatter 포맷·위치 미정의 | High | ACCEPT | Critic |
| 5 | domain-review verdict 파싱 계약 미정 | High | ACCEPT | Cross |
| 6 | `BlockedExecutionError` 미존재 | High | ACCEPT | Cross |
| 7 | §4.3 우선순위 공식 산술 불일치 | High | ACCEPT | Both |
| 8 | `af.spec` hiddenimports 누락 | Medium | ACCEPT | Cross |
| 9 | bypass 메커니즘 결정 연기 | Medium | ACCEPT | Critic |
| 10 | "12-cap 라우팅" 측정 불가 | Medium | ACCEPT | Critic |
| 11 | True 분기 production 검증 0 | Medium | ACCEPT | Critic |
| 12 | dead code 옵션 B 잔존 | Medium | ACCEPT | Critic |
| 13 | `runtime_workspace` 우려 | Low | REJECT | Cross |

### Recommendations

구현 진입 전 **Critical 2건 + High 5건은 반드시 해소**. 권장 처리 순서:

1. **식별자/계약 정정** (즉시): #1 `system` → `system_wide` 일괄 치환, #6 예외 vs bool 반환 결정, #5 verdict 파싱 한 줄 명세
2. **데이터 흐름 명시**: #3 `generate_work_items()` 시그니처 확장 결정, #4 frontmatter 위치(YAML vs `## Metadata`) 결정
3. **회귀 영향 차단**: #2 `_DOC_FILES` 대신 별도 상수 + `_copy_extra_templates()` 갱신 명시 + 마이그레이션 테스트
4. **공식/측정 정정**: #7 §4.3 폐기 또는 가중치 명시, #10 "12-cap" 측정 신호 교체
5. **부수 정리**: #8 `af.spec` 갱신, #9 `AF_SKIP_DOMAIN_REVIEW=1` 못박기, #11 True 분기 fixture, #12 dead code 즉시 제거

위 항목 반영 후 본 doc은 단일 PR로 재리뷰 가능. Phase A 진입 전 `architecture-change` work_kind 도입을 폐기한 §3.3 결정 자체는 양 리뷰 모두 명시적 이의 없음 — 식별자만 정정하면 핵심 트리거 설계는 유효.