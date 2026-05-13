---
id: git_worktrees
name: Using Git Worktrees
version: 0.1.0
inspired_by: superpowers/using-git-worktrees
description: 4단계 워크스페이스 격리 가이드 — 용도 판단 → worktree 생성 → 격리 작업 → 정리. 큰 기능·병렬 구현·Phase 단위 작업을 별도 디렉토리에서 수행해 main workspace 오염을 방지한다.
when_to_use: 큰 기능 브랜치, 병렬 구현 실험, 리뷰/분석은 main에 유지하면서 구현은 격리할 때, Phase 단위 작업.
when_NOT_to_use: 소규모 1~2 파일 변경. 단일 버그 수정. 빠른 문서 업데이트.
when_to_use_keywords:
  - worktree
  - 격리
  - 병렬구현
  - isolation
  - parallel
  - 큰기능
  - 기능브랜치
  - 충돌방지
  - 오염방지
  - baseline분리
category: git-workflow
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags:
  - git
  - worktree
  - isolation
  - parallel
  - workflow
---

# Using Git Worktrees 가이드

## 언제 worktree가 필요한가

다음 중 하나라도 해당하면 worktree 격리를 고려한다:

| 상황 | 이유 |
|------|------|
| 큰 기능 브랜치 (>5 파일 변경) | main workspace 상태 오염 방지 |
| 병렬 구현 실험 A/B | 두 구현이 같은 파일을 건드리면 충돌 |
| Phase 단위 작업 | 직전 Phase baseline 유지하며 비교 테스트 가능 |
| 리뷰 + 구현 동시 진행 | 리뷰는 main, 구현은 worktree에서 독립 |

---

## Step 1 — 용도 판단

격리 필요 여부 판단:

```bash
# 변경 영향 파일 수 확인
git diff --stat HEAD

# blast radius 확인
python3 scripts/blast_radius.py
```

- **Tier 3 파일** (`core/`, `scripts/`) 다수 변경 → worktree 권장
- **단일 SKILL.md·문서** 변경 → worktree 불필요

---

## Step 2 — Worktree 생성

```bash
# 기존 브랜치로 worktree 생성
git worktree add ../agent-factory-<feature> <branch-name>

# 새 브랜치로 worktree 생성
git worktree add -b <new-branch> ../agent-factory-<feature> main

# 현재 worktree 목록 확인
git worktree list
```

**명명 규칙**: `../agent-factory-<feature>` — 레포 이름 접두어 유지, 기능명 접미어.

예시:
```bash
git worktree add -b feature/domain-gate ../agent-factory-domain-gate main
git worktree add -b phase-c-option-c ../agent-factory-phase-c main
```

---

## Step 3 — 격리 작업

worktree 안에서 작업:

```bash
cd ../agent-factory-<feature>

# 이 worktree는 독립 working directory
# main workspace와 HEAD가 다를 수 있음
git branch  # 현재 브랜치 확인
```

**격리 보장 사항**:
- 인덱스(staging area)는 worktree마다 독립
- 브랜치 체크아웃은 독립 (단, 같은 브랜치를 두 worktree에서 동시 체크아웃 불가)
- `.git` 오브젝트 DB는 공유 — push/fetch는 어느 worktree에서든 동일

**주의**: `core/*.py` 수정 시 review gate는 각 worktree에서 독립 실행된다.

---

## Step 4 — 정리

작업 완료 후:

```bash
# 1. worktree에서 브랜치를 main으로 merge/push 먼저
cd ../agent-factory-<feature>
git push origin <branch>

# 2. main workspace로 복귀
cd ../agent-factory

# 3. worktree 제거
git worktree remove ../agent-factory-<feature>

# 4. 로컬 브랜치 정리 (merge 완료 후)
git branch -d <branch>

# 5. 불필요한 worktree 참조 정리
git worktree prune
```

> `git worktree remove`는 미커밋 변경이 있으면 거부한다. 강제 제거: `--force` (데이터 손실 주의).

---

## AF 프로젝트 특화 패턴

**Claude Code `EnterWorktree` 툴 활용** (에이전트 워크트리):

```
Agent(isolation="worktree") → 에이전트가 독립 worktree에서 작업 → 변경 없으면 자동 정리
```

이 패턴은 `af-cross-review`, `af-critic` 등 리뷰 에이전트가 내부적으로 사용한다.

**baseline 테스트 비교**:
```bash
# main에서 baseline 실행
pytest --tb=no -q > /tmp/baseline.txt

# worktree에서 변경 후 실행
cd ../agent-factory-<feature>
pytest --tb=no -q > /tmp/changed.txt

diff /tmp/baseline.txt /tmp/changed.txt
```

---

## 체크리스트

- [ ] Step 1: 격리 필요 여부 판단 완료
- [ ] Step 2: `git worktree add`로 독립 디렉토리 생성
- [ ] Step 3: worktree 안에서 작업 + 테스트
- [ ] Step 4: push/merge 후 `git worktree remove` + `prune`
