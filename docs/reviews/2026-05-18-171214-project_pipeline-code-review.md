# Code Review: project_pipeline

> Source: core/project_pipeline.py
> Date: 2026-05-18 17:12
> Type: code
> Providers: critic=af-cross-review (Codex deliberation round 2)
> Mode: challenge-defense
> Trigger: B-3 capability-gap fix

---

## Code Critic Review

### Verdict: PASS

### Findings

No blocking issues. Prior [High] finding (exact-match skills bypass capability-gap) was reviewed via af-cross-review 4-round deliberation and **REJECTED**:

- **[REJECTED] Exact-match skill bypass** — B-3 diff (`project_pipeline.py:643-644` +2 lines) adds `required_capabilities`/`skill_gap_hypotheses` to `reqs` for the `unresolved_targets` path. The `exact_match` branch (`skill_procurer.py:909-941`) skipping gap analysis is pre-existing design, not introduced by B-3. Codex confirmed: "B-3의 project_pipeline.py +2라인이 exact-match 경로의 gap 스킵을 직접 악화시킨 코드 경로는 제시할 수 없습니다."

### Positive Observations

- Change is narrowly scoped: only 2 keys added to existing `reqs` dict.
- Downstream `skill_gap_hypotheses` consumed by `researcher._skill_gap_capabilities_map()` (new helper).
- `required_capabilities` normalization: input is researcher-generated list (already safe_id normalized at source).
