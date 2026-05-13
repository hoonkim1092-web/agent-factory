---
id: finishing_branch
name: Finishing a Development Branch
version: 0.1.0
inspired_by: superpowers/finishing-a-development-branch
description: 6단계 브랜치 마무리 가이드 — 테스트 → 검증 보고서 → review gate → 문서 동기화 → 브랜치/worktree 정리 → PR/merge 결정. Phase 종료 또는 PR 제출 전 체계적으로 완료하는 절차.
when_to_use: 피처 브랜치 작업이 완료되어 merge/PR을 준비할 때, Phase 종료 시, worktree 정리가 필요할 때.
when_NOT_to_use: 작업 중간 커밋. 일상적인 스냅샷 커밋에는 과도함.
when_to_use_keywords:
  - PR
  - merge
  - 브랜치마무리
  - 브랜치정리
  - finishing
  - complete
  - 완료
  - phase종료
  - 세션종료
  - worktree정리
  - 릴리즈
  - release
category: git-workflow
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags:
  - git
  - branch
  - pr
  - workflow
  - cleanup
---

# Finishing a Development Branch 가이드

브랜치를 닫기 전 필수 6단계. 순서를 지키지 않으면 리뷰어에게 미완성 상태를 노출한다.

## Step 1 — 전체 테스트 실행

```bash
pytest --tb=short -q
```

- 모든 테스트 PASS가 확인될 때까지 다음 단계로 진행하지 않는다.
- 실패가 있으면 **이 브랜치에서 수정**한다. 다음 PR로 미루지 않는다.
- 테스트가 없는 변경은 최소 smoke test를 추가한다.

> **금지**: "나중에 고치지"로 실패 무시. 실패 테스트를 `skip` 처리하고 PR 제출.

---

## Step 2 — 변경 검증 보고서

```bash
git diff main...HEAD --stat
git log main..HEAD --oneline
```

확인 항목:

1. **미스테이지 파일 없음** — `git status`가 clean
2. **의도치 않은 파일 없음** — `.env`, 바이너리, `dist/*.zip` 포함 여부
3. **Blueprint 동기화** — `Master_Blueprint.md` §0·§12가 이 브랜치 변경을 반영했는지
4. **NEXT_STEPS.md 갱신** — 다음 세션 재개 정보가 최신인지

---

## Step 3 — Review Gate 완주

`.py` 파일이 변경된 경우:

```bash
# review gate 상태 확인
python3 scripts/review_gate.py --debug
```

- **Tier 2~3 파일** (core/, scripts/): af-critic → af-cross-review → af-test-runner 순서 완주
- **BLOCK 판정**이 있으면 수정 후 재실행
- **WARN-only**면 advisory 기록 후 진행 가능

`.py` 없는 변경(문서·설정·SKILL.md)은 이 단계 자동 통과.

---

## Step 4 — 생성 문서 동기화

변경으로 인해 갱신이 필요한 문서 확인:

- `docs/code_review/code-review.md` — 수정된 파일 행 업데이트
- `Master_Blueprint.md` §0 빠른 참조 테이블
- `Master_Blueprint.md` §12 변경 이력
- `NEXT_STEPS.md` — 완료 내용 + 다음 후보 기록

---

## Step 5 — 브랜치/Worktree 정리

**Worktree를 사용했다면**:

```bash
# worktree 작업 완료 후 merge
git worktree remove <worktree-path>

# 브랜치 로컬 삭제 (remote push 후)
git branch -d <feature-branch>
```

**Worktree 없이 작업했다면**:

```bash
# 병합된 로컬 브랜치 정리
git branch --merged main | grep -v main | xargs git branch -d
```

> remote에 push하기 전에 브랜치 이름과 커밋 메시지를 최종 검토한다.

---

## Step 6 — PR/Merge 결정

| 상황 | 행동 |
|------|------|
| 혼자 작업, main 직접 push 가능 | `git push origin <branch>` 후 merge |
| 팀 리뷰 필요 | `gh pr create` + 리뷰어 지정 |
| 릴리즈 태그 필요 | `gh release create af-fsa_v{version} dist/af-{version}.zip` |

PR 본문 포함 필수 항목:
- 변경 요약 (3줄 이내)
- 테스트 실행 결과
- 연관 이슈/ADR 번호

---

## 체크리스트

브랜치 닫기 전 확인:

- [ ] Step 1: `pytest` 전체 PASS
- [ ] Step 2: `git status` clean, 민감 파일 없음
- [ ] Step 2: Blueprint §0·§12 동기화 완료
- [ ] Step 3: review gate PASS (`.py` 변경 시)
- [ ] Step 4: code-review.md + NEXT_STEPS.md 갱신
- [ ] Step 5: worktree/브랜치 정리
- [ ] Step 6: PR/merge 방식 결정 후 실행
