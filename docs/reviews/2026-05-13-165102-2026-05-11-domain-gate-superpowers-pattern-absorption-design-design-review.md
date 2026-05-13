# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:51
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] `normalized` 데이터 흐름이 실제 호출 구조에 없음
   - Section: "`project_pipeline.py:963`은 `generate_work_items()` 호출 시 `work_kind`/`blast_radius`를 전달하지 않으므로 시그니처 확장 필수"
   - Issue: 문서는 `normalized.work_kind`, `normalized.change_impact["blast_radius"]`를 `project_pipeline.py:963`에서 넘긴다고 설계하지만, 현재 `core/project_pipeline.py:959-966` 호출부에는 `normalized`가 존재하지 않습니다. `ControlPlaneIntake.normalize()`도 현재 repo에서 정의만 있고 호출자는 없습니다. `prepare_brief()`는 `ControlPlaneIntake()._recall_from_memory()`만 직접 호출합니다.
   - Suggestion: `ProjectPipeline.prepare_brief()` 또는 `prepare_documents()`에 `ControlPlaneIntake.normalize(task_input, workspace, route, board)` 호출을 명시적으로 추가하고, 결과를 `PreparedProject` 또는 `project_brief`에 저장한 뒤 `generate_work_items(..., work_kind=..., blast_radius=...)`로 전달하도록 설계를 수정해야 합니다.

2. [High] `ApprovalGate.approve()` 실패 계약 변경이 호출자까지 반영되지 않음
   - Section: "`approve()` False 반환 + `self.last_block_reason` 속성에 사유 기록"
   - Issue: 현재 `core/approval_gate.py:144-165`의 `approve()`는 파일 없음만 `False`로 반환하는 계약입니다. `agent_launcher.py:437-441`은 `approve()`가 `False`면 무조건 "`approval-gate.md`를 찾을 수 없습니다"로 처리합니다. domain-review 차단이 추가되면 사용자에게 잘못된 오류가 표시되고 실행 결과도 `gate_file_missing`으로 오염됩니다.
   - Suggestion: `ApprovalGate.__init__`에 `last_block_reason: str = ""` 초기화를 명시하고, `agent_launcher.py`, `core/project_pipeline.py:1509-1516`, 테스트의 `approve()` 호출부가 `domain_review_blocked`, `missing_verdict`, `multiple_verdicts` 등을 구분하도록 설계에 포함해야 합니다.

3. [High] `SkillPackBootstrapper` 처분 결정이 문서 내부에서 충돌함
   - Section: "`dead code 처분: 옵션 A — 즉시 제거`"
   - Section: "Q4 | `core/skill_pack_bootstrapper.py` 처분 ... | 옵션 B (영향 범위 최소)"
   - Issue: 본문 §6.1/§7.3/§10.3은 즉시 삭제를 채택했다고 쓰지만, §12 Open Questions는 옵션 B를 기본안으로 둡니다. 실제 repo에는 `core/skill_pack_bootstrapper.py`, `tests/test_compact_step2.py:21`, `af.spec:122`, `Master_Blueprint.md:858` 참조가 남아 있어 삭제는 최소 4파일 동기 수정이 필요합니다.
   - Suggestion: Q4를 닫으세요. 즉시 삭제가 맞다면 §12도 옵션 A로 바꾸고, 테스트/hiddenimports/Blueprint 수정 범위를 필수 작업으로 고정해야 합니다. 별도 commit이면 §7.3의 “동일 PR” 표현도 정리해야 합니다.

4. [Medium] `blast_radius` enum이 실제 코드와 다름
   - Section: "`change_impact.blast_radius` enum: `{\"local\", \"module\", \"cross_module\", \"system_wide\"}`"
   - Issue: 실제 `core/control/change_impact.py:16,35,238-239`와 `core/control/execution_policy.py:109,177`는 `local`이 아니라 `isolated`를 사용합니다. 문서의 정적 grep 기준도 `"system_wide" 외 blast_radius 토큰 0건`이라고 되어 있어, 실제 필요한 `isolated/module/cross_module` 참조까지 잘못 차단할 위험이 있습니다.
   - Suggestion: enum을 `{"isolated", "module", "cross_module", "system_wide"}`로 수정하고, 테스트 기준은 “잘못된 토큰 `system`/`local` 금지”처럼 정확히 좁히세요.

5. [Medium] `domain-review.md` 위치 기준이 `workspace`와 `doc_root` 사이에서 모호함
   - Section: "base path: `workspace/docs/work-items/<slug>` (= `ApprovalGate.work_item_dir`)"
   - Issue: 실제 `generate_work_items()`는 `project_brief.target_path`가 절대경로면 `doc_root = target_path`로 바꾸고, `ApprovalGate(doc_root, slug, runtime_workspace=workspace)`를 생성합니다 (`core/work_item_generator.py:1079-1084`, `1230`). 즉 work-item 문서는 항상 `workspace/docs/...`가 아닙니다.
   - Suggestion: domain-review 경로를 `ApprovalGate.work_item_dir / _DOMAIN_REVIEW_FILE`로 정의하고, `workspace`가 아니라 effective `doc_root` 기준이라고 문서화하세요. multi-PC/외부 target_path 환경에서 중요합니다.

### Missing from Design

- `ControlPlaneIntake.normalize()`를 어느 계층에서 호출하고 `PreparedProject`에 어떻게 보존할지 명확하지 않습니다.
- `approve()` 실패 사유를 CLI/UI/자동 실행 경로가 어떻게 표시할지 없습니다.
- 기존 `tests/test_approval_gate_auto_approve.py`의 `approve()` 호환성 영향 분석이 없습니다.
- `SkillPackBootstrapper` 삭제 여부가 최종 결정되어 있지 않습니다.
- `isolated` blast radius에 대한 마이그레이션/검증 기준이 빠져 있습니다.

### Positive Observations

- `_DOMAIN_REVIEW_FILE`을 `_DOC_FILES`와 분리하려는 결정은 현재 `compute_snapshots()`/`check_validity()` 구조와 맞습니다. 기존 work-item snapshot invalidation을 피할 수 있습니다.
- `domain-review.md`의 `- verdict: PASS|NEEDS_ADR|BLOCK` 1줄 파서 설계는 자동 게이트에 적합하고, 체크박스보다 구현 리스크가 낮습니다.