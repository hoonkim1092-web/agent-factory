# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:11
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

두 리뷰어가 동일한 Critical 1건(`blast_radius == "system"`)을 독립 발견했고, 구현 진입 전 결정/명세가 필요한 High 항목이 6건입니다. 게다가 cross 리뷰가 발견한 통합 경로 미배선(Cross #2), 템플릿 복사 미명세(Cross #5)는 설계대로 구현해도 게이트가 발화하지 않게 만드는 구조적 결함입니다.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] `blast_radius` enum 불일치 — 게이트 영구 false negative
- **Critic**: §3.3 `return blast_radius == "system"` / §10.2 / §3.2 모두 `"system"` 사용. `core/control/change_impact.py:16,35` 실제 enum은 `"isolated" | "module" | "cross_module" | "system_wide"`. `execution_policy.py:168,177`, `regression_gate.py:67` 모두 `"system_wide"`.
- **Cross**: 동일. `is_system_wide_blast_radius(value)` 헬퍼/상수화 제안.
- **Judgment**: 두 리뷰어가 같은 코드 증거(3개 파일)로 독립 도달. 폐기한 `architecture-change`와 같은 종류의 식별자 불일치가 트리거에서 재발. 1줄 수정으로 해결 가능하지만 미수정 시 단계 2/3 활성화에도 게이트가 영원히 발화하지 않음.
- **Action Required**: 문서 전체 `"system"` → `"system_wide"`로 통일. §3.3 시그니처, §10.2 단계 2 텍스트, §3.5 검증 #4 회귀 테스트 케이스. `core/control/change_impact.py`에 `is_system_wide_blast_radius()` 헬퍼 신설 고려.

#### 2. [ACCEPT] [Critical] frontmatter 마이그레이션·통합 경로 누락 — §10.1 vs §3.2 자기모순 + 호출 미배선
- **Critic** (Critical #2): §10.1 "기존 work-item 자동 통과" ↔ §3.2 "frontmatter 누락 시 `BlockedExecutionError`"가 충돌. 기존 1,404 LOC `work_item_generator.py`에 frontmatter 생성 코드 0건.
- **Cross** (#2): `agent_launcher.py` → `ProjectPipeline.prepare_brief()/prepare_documents()` 경로에서 `ControlPlaneIntake.normalize()`가 호출되지 않음. `core/project_pipeline.py:709`은 `_recall_from_memory()`만 호출. `generate_work_items()` 시그니처에 `work_kind`/`blast_radius` 인자 없음.
- **Judgment**: critic은 fallback 정책 부재를 지적했고 cross는 호출 경로 자체가 wired되지 않았음을 발견. 두 결함이 합쳐지면 단계 1에서도 모든 기존 work-item이 BLOCK되고, 신규 work-item도 frontmatter가 비어 있음. 설계 진입 전 해결 필수.
- **Action Required**: (a) `ProjectPipeline.prepare_brief()` 또는 `prepare_documents()`에서 `ControlPlaneIntake.normalize()` 호출 추가, `PreparedBrief`에 결과 저장. (b) `generate_work_items(workspace, slug, project_brief, role_plan, task_board, run_id, normalized: NormalizedRequest | None)` 시그니처 확장. (c) 기존 work-item 마이그레이션 정책 명세: `scripts/migrate_work_item_frontmatter.py` 산출물 추가 또는 `work_kind="unknown"` fallback 명시.

#### 3. [ACCEPT] [High] verdict 파싱 미명세
- **Critic** (#4): 체크박스 0개/다중/대소문자 변형/섹션 헤더 변형 미정의. `_DOC_FILES` 확장만으로 의미 추출 불가.
- **Cross** (#4): 동일 — `ApprovalGate._parse()`는 bullet key/value만 이해. 체크박스 verdict 파서 없음.
- **Judgment**: 두 리뷰어가 같은 결론. 권고도 일치: 단일 머신필드(`- verdict: PASS` 또는 frontmatter `verdict: PASS`)로 전환 + fail-closed.
- **Action Required**: §3.4 템플릿을 `## 4. Verdict\n- verdict: PASS|NEEDS_ADR|BLOCK` 단일 라인으로 변경. §3.2에 `_parse_domain_review_verdict(path) -> Literal[...]` 시그니처 추가, invalid → `BlockedExecutionError("invalid domain-review verdict")`. §3.5 검증 #4에 0개/다중/대소문자/section-missing 4종 케이스 추가.

#### 4. [ACCEPT] [High] `domain-review.md` 템플릿이 현재 generator로 복사되지 않음
- **Critic**: not flagged
- **Cross** (#5): `core/work_item_generator.py` `_copy_extra_templates()`는 `verification-report.md`, `change-request.md`, `bug-fix-spec.md` 고정 `extra` 세트만 복사. 와일드카드 경로 없음.
- **Judgment**: 코드 증거 명확. 템플릿 파일만 추가하면 신규 work-item에 절대 포함되지 않아 단계 2 진입 시 `_DOC_FILES` 확장이 모든 work-item을 BLOCK시킴.
- **Action Required**: §7.1 또는 §3.2에 `_copy_extra_templates()`의 `extra` 세트에 `domain-review.md` 추가 명시. §3.5 검증에 "system_wide 더미 work-item 생성 시 `domain-review.md` 존재 확인" 케이스 추가.

#### 5. [ACCEPT] [High] frontmatter 포맷·파서 미명세
- **Critic** (#2와 일부 중첩, Missing #3): `policy.yaml` 연동 여부 미평가.
- **Cross** (#3): 기존 work-item docs는 `## Metadata` bullet 사용. 현재 frontmatter 파서는 `parse_frontmatter_exempt()` 단일 boolean뿐. 일반 파서 부재.
- **Judgment**: cross 증거가 강함. critic도 LOC 비현실성(#7)으로 같은 영역 지적. YAML 직렬화/파싱이 ad-hoc하게 4곳에 흩어지면 회귀 위험.
- **Action Required**: §7.1에 신규 `core/document_frontmatter.py` (YAML safe_load, 결손 시 `BlockedExecutionError`) 산출물 추가. §3.2에 정확한 YAML 스키마 명시 — `---\nwork_kind: feature_update\nblast_radius: system_wide\n---`.

#### 6. [ACCEPT] [High] bypass 메커니즘이 "Phase A 구현 시 결정"으로 미루어짐
- **Critic** (#5): 두 후보(env vs 자동 면제) 의미·감사 추적성 차이 큼. cross-review 시점에 결정해야 Phase A 중간 재리뷰 회피.
- **Cross**: not flagged
- **Judgment**: critic 단독이나 증거 강함. CLAUDE.md의 `AF_SKIP_REVIEW_GATE=1` 선례와 정합 필요.
- **Action Required**: §3.3에 `AF_SKIP_DOMAIN_REVIEW=1` env 우회 명시 + `hook_events.log` 기록. 자동 면제(`issue_kind=="incident" AND risk_level=="critical"`)는 폐기.

#### 7. [ACCEPT] [High] enforcement가 `approve()`에만 있어 우회 경로 존재
- **Critic**: not flagged
- **Cross** (#7): `ProjectPipeline.execute()` → `is_execution_open()` + `read_block_decision()` 별도 호출. `MaintenancePipeline._check_approval_gate()` → `is_execution_open()`만. `scripts/verify_handoff_checker.py` → `apply_verification_verdict()`.
- **Judgment**: cross 단독이나 코드 증거 4개 경로로 명확. `approve()`만 막으면 resume/maintenance/handoff는 우회됨.
- **Action Required**: `ApprovalGate.check_validity()` 또는 `is_execution_open()`에 domain-review 검증 내장. `approve()`는 UX precheck 유지.

#### 8. [ACCEPT] [Medium] 도메인 소스 경로 ambiguous (target_path vs workspace)
- **Critic**: not flagged
- **Cross** (#6): `core/work_item_generator.py`가 `doc_root`(절대 target_path) 사용 vs `ApprovalGate(doc_root, slug, runtime_workspace=workspace)`로 분리. `PROJECT_CONTEXT.md` / ADR 위치 미명세.
- **Judgment**: cross 단독이나 split 경로는 기존 회귀 발생 영역. `target_path` 사용자 환경(외부 프로젝트 자동화 시)에서 깨질 위험.
- **Action Required**: §3.1에 `PROJECT_CONTEXT.md`·`docs/decisions/` 경로 결정 — AF-owned (`workspace/docs/`) vs project-owned (`doc_root/docs/`) 명시. `target_path` 회귀 테스트 1건 추가.

#### 9. [ACCEPT] [Medium] `requires_domain_review` 정체성 모호
- **Critic** (#6): 속성/함수/정책 플래그 3개 혼재. ApprovalGate 인스턴스화 시 단계 정보 주입 경로 불명.
- **Cross**: not flagged
- **Judgment**: critic 단독이나 단일 소스 부재가 명확. cross의 #7 enforcement centralization과 결합 시 더 큰 일관성 이슈.
- **Action Required**: `policy.yaml` `domain_review.enforcement_stage: 1|2|3` 추가. `ApprovalGate`가 부팅 시 읽어 `_should_enforce(blast_radius) -> bool`로 단일화. §3.2·§3.3·§10.2 모두 이 단일 메커니즘 참조.

#### 10. [ACCEPT] [Medium] 신규 `core/brainstorm_prompts.py` af.spec hiddenimports 누락
- **Critic** (#3): CLAUDE.md "새 `core/*.py`는 `af.spec` `hiddenimports`에 반드시 추가". §7.3은 `skill_pack_bootstrapper` 제거만 명시.
- **Cross**: not flagged
- **Judgment**: critic 단독이나 frozen 빌드 ImportError 위험. CLAUDE.md 규칙 명시적.
- **Action Required**: §7.3에 "`core.brainstorm_prompts` 추가 (Phase B 결과로 도입 결정 시)" 명시. 도입 여부 Phase B에서 확정 + 도입 시 af.spec 동기 변경 강제.

#### 11. [HOLD] [Medium] `work_item_generator.py` ~20 LOC 추정의 현실성
- **Critic** (#7): 1,404 LOC 파일에 frontmatter 직렬화 + `NormalizedRequest` 객체 추출 + 호환성 + 테스트가 20 LOC는 비현실적. ~60으로 상향 제안.
- **Cross** (#2): 통합 경로 자체가 wired되지 않아 시그니처 변경 필요 — LOC 산정의 전제가 달라짐.
- **Judgment**: Finding #2 해결 방안에 따라 LOC 크게 변동. 두 LOC 추정 모두 #2 해소 후 재계산 필요.
- **Question for Author**: Finding #2에서 `prepare_brief()` 변경 + `PreparedBrief` 필드 추가 + `generate_work_items()` 시그니처 확장을 모두 합친 후 LOC를 재산정해 §3.2 표 갱신할 것.

#### 12. [REJECT] [Low] §11 #5 LOC 정확도 (48 vs 49)
- **Source**: Critic (#10)
- **Original Finding**: `skill_pack_bootstrapper.py` 실제 48 vs 49 LOC, "0 callers" 표현 정확성.
- **Rejection Reason**: 본 설계의 결정(GStack 폐기)에 영향 없음. 표현 다듬기 수준이며 설계 진입 차단 사유 아님. 후속 commit에서 자연스럽게 수정 가능. critic도 sosil 수준이라 표기.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `blast_radius == "system"` enum 불일치 | Critical | ACCEPT | Both |
| 2 | frontmatter 마이그레이션·통합 경로 누락 | Critical | ACCEPT | Both |
| 3 | verdict 파싱 미명세 | High | ACCEPT | Both |
| 4 | `domain-review.md` 템플릿 미복사 | High | ACCEPT | Cross |
| 5 | frontmatter 포맷·파서 미명세 | High | ACCEPT | Cross |
| 6 | bypass 메커니즘 미결정 | High | ACCEPT | Critic |
| 7 | enforcement 중앙화 부재 | High | ACCEPT | Cross |
| 8 | 도메인 소스 경로 ambiguous | Medium | ACCEPT | Cross |
| 9 | `requires_domain_review` 정체성 | Medium | ACCEPT | Critic |
| 10 | af.spec hiddenimports 누락 | Medium | ACCEPT | Critic |
| 11 | `work_item_generator.py` LOC 추정 | Medium | HOLD | Critic/Cross |
| 12 | §11 #5 LOC 정확도 | Low | REJECT | Critic |

### Recommendations

1. **§3.2/§3.3/§10.2 전체 `"system"` → `"system_wide"` 일괄 치환** + `core/control/change_impact.py`에 `is_system_wide_blast_radius()` 헬퍼 신설(Finding #1).
2. **통합 경로 명시화** — `ProjectPipeline.prepare_brief()`에서 `ControlPlaneIntake.normalize()` 호출, `PreparedBrief.normalized: NormalizedRequest`, `generate_work_items()` 시그니처 확장. 기존 work-item fallback 정책(`work_kind="unknown"`) 명시(Finding #2).
3. **verdict 형식 변경** — 체크박스 → 단일 라인 `- verdict: PASS|NEEDS_ADR|BLOCK`. `_parse_domain_review_verdict()` 시그니처 + fail-closed 명시. 회귀 테스트 4종(0/다중/대소문자/section-missing)(Finding #3).
4. **`_copy_extra_templates()` 확장** — `domain-review.md` 추가. 회귀 테스트 추가(Finding #4).
5. **`core/document_frontmatter.py` 신설** — YAML safe_load + 결손 시 `BlockedExecutionError`. §7.1에 산출물로 등록(Finding #5).
6. **bypass 결정** — `AF_SKIP_DOMAIN_REVIEW=1` env 우회 채택, `hook_events.log` 기록. §3.3에 명시(Finding #6).
7. **enforcement 중앙화** — `ApprovalGate.check_validity()`에 도입, 모든 호출 경로(`approve`/`is_execution_open`/`read_block_decision`/`apply_verification_verdict`) 공유(Finding #7).
8. **도메인 소스 경로 결정** — `PROJECT_CONTEXT.md`/ADR 경로를 AF-owned vs project-owned 중 택일, `target_path` 회귀 테스트 추가(Finding #8).
9. **`policy.yaml` 정책 단일화** — `domain_review.enforcement_stage` 도입, ApprovalGate 부팅 시 read(Finding #9).
10. **`core/brainstorm_prompts.py` af.spec hiddenimports** — Phase B 도입 결정 시 동기 변경 강제(Finding #10).
11. **LOC 재산정** — Finding #2 해소 후 §3.2 LOC 표 전체 갱신(Finding #11).

위 11건 반영한 v2 설계 commit 후 재-cross-review가 필요합니다.