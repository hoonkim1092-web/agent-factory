# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-15 KST** — NEXT_STEPS.md 분리 직후. 본 파일은 현재 진행 중인 작업과 다음 진입점만 유지한다.

---

## 🔥 현재 진행 중 — P5 commit + main 머지 결정 대기

**상태**: P5 DomainVerdict 매트릭스, Round 1/2/3 dogfooding, P4.5a model routing defaults 모두 구현 완료. 3-tier review 완주 후 커밋·main 머지 결정만 남아 있다.

### 즉시 다음 작업
1. **commit** — 워킹트리의 modified/untracked 변경 일괄 커밋
   - 핵심: `core/approval_gate.py` (DomainVerdict 매트릭스), `core/project_pipeline.py` (blast_radius 배포 동등성), `tests/test_approval_gate_domain_gate.py` (34 tests)
   - Round 1/2/3 산출물: `.githooks/post-commit` 큐 클리어, `skills/writing_skills/SKILL.md`
   - P4.5a: 에이전트 frontmatter `model:` 기본값 명시 (CLAUDE.md "Agent Model Routing" 표 참고)
2. **main 머지 결정** — `af-on-af/round1-hook-fix` 브랜치를 main으로 통합할지 사용자 결정 필요
3. (옵션) P4.5b 진입 — runtime escalation 강제 (`select_model()` 헬퍼 + review_gate/hook 연결 + 테스트)

### 진입 명령
```bash
cd D:\hoonProJect\worktrees\agent-factory
git pull
python start_db.py agent-factory
git status   # 변경 검토
```

---

## 📜 과거 이력

세션별 누적 이력은 [docs/session-log/2026-05-15-rounds-1-2-3.md](docs/session-log/2026-05-15-rounds-1-2-3.md) 참고.

- Round 1·2·3 dogfooding 종료 (2026-05-14~05-15)
- P5 DomainVerdict 매트릭스 완료 (2026-05-15)
- P4.5a model routing defaults (2026-05-15)
- Phase A/B/C, ADR M1~M5, P1~P4, Question Router Stage 0, Work-Item 병렬화 v3.1, Phase 2 verdict-label spec, Research Router v1.4.1, AST/LSP 분석 — 전부 위 session-log 파일로 이동.

---

## 세션 종료 체크리스트

1. 완료 작업 / 다음 진입점 갱신
2. `git commit` → `git push`
3. `python end_db.py agent-factory`
