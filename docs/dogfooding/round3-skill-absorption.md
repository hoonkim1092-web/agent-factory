# Round 3 Dogfooding — Skill Absorption

> Date: 2026-05-15 KST
> Scope: Tier 1 docs/skills-only change
> Branch: af-on-af/round1-hook-fix
> Purpose: Round 1·2 review-gate 100% selection bias 해소 — 비-hook 도메인 마찰 측정.

## 배경

Round 1·2는 hook 버그 fix 작업이라 마찰이 100% review-gate 도메인에 집중됐다.
Round 3은 스킬 흡수(Tier 1 docs-only)로 비-hook 도메인 마찰 패턴을 측정한다.

## 작업

`superpowers/writing-skills` 패턴을 AF knowledge skill로 흡수:

- `skills/writing_skills/SKILL.md` — SKILL.md 작성 가이드 (4단계 흡수 워크플로)
- `inspired_by: superpowers/writing-skills`
- `core/`, hook 변경 없음.

## 마찰 로그

| # | 도메인 | 설명 |
|---|--------|------|
| F1 | Codex 오작동 | 이전 세션 Codex가 사용자 질문을 지시로 오해, Round 3 작업을 무단 수행 → `git revert` + 재시작 필요 |
| F2 | context | `NEXT_STEPS.md` 대용량(~56k tokens) — 상단 100줄 targeted read로 대응 |
| F3 | expertise | `skill_type: action` SKILL.md 예시 없음 (기존 6개 전부 knowledge) — research_assistant 흡수 후보에서 제외 |
| F4 | tooling | 첫 번째 `Write` 호출: "File created successfully" 반환했지만 파일 미생성 (이전 세션 시도) |

## 검증

```bash
.venv/bin/python -m pytest tests/test_skill_metadata_adapter.py \
  tests/test_cross_cli_skill_discovery.py \
  tests/test_external_skill_candidate_importer.py -q
# → 36 passed

.venv/bin/python -c "
from core.utils import resolve_knowledge_skill_path
print(resolve_knowledge_skill_path('writing_skills'))
"
# → skills/writing_skills/skill.md
```

## 결과

| 도메인 | Round 1·2 | Round 3 |
|--------|:---------:|:-------:|
| review-gate | 7건 | 0건 |
| context | 0건 | 1건 |
| expertise | 0건 | 1건 |
| tooling | 0건 | 1건 |
| Codex 오작동 | 0건 | 1건 |

**결론**: Tier 1 docs-only 작업에서 review-gate 마찰 0건 확인. Round 1·2 selection bias 가설 검증됨.
주요 신규 마찰은 context 비용(NEXT_STEPS.md 크기)과 툴링 신뢰성(Write false-success)이다.
