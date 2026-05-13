# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 16:49
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: WARN

### Findings

1. [High] `approve()`에만 붙이면 실행 경로에서 우회된다
   - Section: "`read 시점: ApprovalGate.approve() 진입 직후`"
   - Issue: 실제 실행 차단은 `approve()`가 아니라 `is_execution_open()` 경로가 담당한다. `ProjectPipeline.execute()`는 [core/project_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/project_pipeline.py:1262), `run_factory_cli.py resume`은 [run_factory_cli.py](D:/hoonProJect/worktrees/agent-factory/run_factory_cli.py:568), maintenance는 [core/control/maintenance_pipeline.py](D:/hoonProJect/worktrees/agent-factory/core/control/maintenance_pipeline.py:307)에서 모두 `gate.is_execution_open()`만 확인한다. 이미 승인된 gate나 resume 경로는 `approve()` 검증을 다시 타지 않는다.
   - Suggestion: domain-review 필수 여부와 verdict 검증을 `is_execution_open()` 또는 `check_validity()`에 넣어라. `approve()`는 UX precheck로만 유지하고, project execute/resume/maintenance 3경로 회귀 테스트를 추가해야 한다.

2. [High] 점진 활성 정책이 서로 충돌한다
   - Section: "`단계 1: requires_domain_review = False`", "`단계 2: requires_domain_review = True for blast_radius == \"system_wide\"`", "`정책 단계 1~2에서는 advisory만, 단계 3에서 enforce`"
   - Issue: §3.3은 단계 2부터 enforce처럼 쓰고, §9 위험 대응은 단계 2까지 advisory라고 쓴다. §3.5 검증 #5도 `domain-review.md` 누락 시 `approve()=False`를 요구한다. 구현자가 어떤 단계에서 차단해야 하는지 결정할 수 없다.
   - Suggestion: `AF_DOMAIN_REVIEW_MODE=off|advisory|enforce` 같은 단일 정책 소스를 정의하고, 각 모드에서 `missing file`, `NEEDS_ADR`, `BLOCK`의 반환 동작을 표로 고정해라.

3. [Medium] `blast_radius` enum 문서가 실제 코드와 다르다
   - Section: "`blast_radius ∈ {\"local\",\"module\",\"cross_module\",\"system_wide\"}`"
   - Issue: 실제 `ChangeImpactProfiler` 기본/반환값은 `"isolated" | "module" | "cross_module" | "system_wide"`다. [core/control/change_impact.py](D:/hoonProJect/worktrees/agent-factory/core/control/change_impact.py:238)는 마지막 fallback으로 `"isolated"`를 반환한다. 문서의 `"local"`은 존재하지 않는다.
   - Suggestion: 모든 `"local"` 표기를 `"isolated"`로 바꾸고, 테스트 #6의 정적 grep 조건도 실제 enum 전체를 허용하도록 고쳐라.

4. [Medium] 문서/스킬 변경은 현재 review gate를 통과하지 않는다
   - Section: "`verification-before-completion | review_gate verdict 강제 | scripts/review_gate.py 또는 core/approval_gate.py`"
   - Issue: `scripts/review_gate.py`는 staged 파일 중 `.py`가 없으면 `"no-py-files"`로 통과한다. [scripts/review_gate.py](D:/hoonProJect/worktrees/agent-factory/scripts/review_gate.py:187). pre-commit의 LLM review 대상도 `core/*.py`, `skills/*/skill.py` 등으로 제한되어 `skills/**/SKILL.md`, `docs/work-items/_template/**`는 빠진다. [.githooks/pre-commit](D:/hoonProJect/worktrees/agent-factory/.githooks/pre-commit:69)
   - Suggestion: Phase C가 `SKILL.md`와 template을 바꾼다면 gate 대상에 `skills/**/SKILL.md`와 `docs/work-items/_template/**`를 추가하거나, 이 변경은 자동 gate 밖이라 수동 design review가 필요하다고 명시해라.

5. [Medium] `SkillPackBootstrapper` 처분 결정이 문서 안에서 모순된다
   - Section: "`옵션 A — 즉시 제거`" vs "`Q4 ... 옵션 B (영향 범위 최소)`"
   - Issue: §6.1/§7.3/§10.3은 즉시 제거를 채택했다고 쓰지만, §12 Q4는 여전히 옵션 B를 선택안으로 둔다. 실제 참조는 [tests/test_compact_step2.py](D:/hoonProJect/worktrees/agent-factory/tests/test_compact_step2.py:21)와 [af.spec](D:/hoonProJect/worktrees/agent-factory/af.spec:122)에 남아 있어 구현 범위가 달라진다.
   - Suggestion: Q4를 닫고 옵션 A로 통일하라. 제거 commit 범위에 `core/skill_pack_bootstrapper.py`, `tests/test_compact_step2.py`, `af.spec`, `Master_Blueprint.md`를 명시하면 된다.

### Missing from Design

- `domain-review.md` 검증을 `check_validity()`에 넣을 때 snapshot 대상에 포함할지, 별도 optional validation으로 둘지 명확하지 않다.
- 동시 접근/부분 write 대응이 없다. `ApprovalGate`는 현재 [core/file_io.py](D:/hoonProJect/worktrees/agent-factory/core/file_io.py:117)의 non-atomic `write_text()`를 사용한다.
- frozen build에서 domain-review enforcement 경로를 실제 `dist/af/af.exe`로 smoke test하는 항목이 부족하다.

### Positive Observations

- `domain-review.md`를 `_DOC_FILES`에 넣지 않고 별도 상수로 분리하려는 결정은 기존 work-item 일괄 무효화를 피하는 방향이다.
- `blast_radius=="system_wide"` 단독 트리거로 정리한 점은 `work_kind` 오분류에 덜 취약하다.