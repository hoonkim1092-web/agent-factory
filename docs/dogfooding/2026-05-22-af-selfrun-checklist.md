# AF Self-Run 체크리스트 (2026-05-22)

> **목적**: AF 파이프라인이 자기 `.py` 파일을 수정할 때 안전하게 실행하기 위한 반복 가능한 절차.  
> **근거**: [Round 4 마찰 로그](round4-af-cli-friction.md) + [R1 Self-Run 결과](2026-05-21-r1-selfrun-result.md)

---

## 0. 선행 조건 확인

| 항목 | 확인 방법 | 문제 시 |
|------|-----------|---------|
| 작업 브랜치 | `git branch --show-current` | main이면 feature 브랜치 생성 후 진행 |
| Worktree 격리 | `git worktree list` | 기존 worktree 없으면 Step 1에서 생성 |
| Provider 가용 | `claude_cli --version` | claude_cli 없으면 AF가 gemini(실패) → codex로 fallback — 낭비 발생 |
| 기존 레지스트리 상태 | `git status skills/registry.yaml` | modified면 stash 또는 reset 후 진행 (F9 scope-leak 방지) |

---

## 1. Worktree 격리 생성

```powershell
# 실험 브랜치명: r<번호>-selfrun-<설명>
$BRANCH = "r2-selfrun-exp"
$WT_PATH = "D:\hoonProJect\worktrees\$BRANCH"

git worktree add $WT_PATH -b $BRANCH
```

- 격리 이유: AF가 `projects/default/` scaffolding, `skills/registry.yaml` 부작용 변경을 일으킬 수 있음 (F9)
- worktree 내에서 `_maybe_isolate_project_root_for_self_run()`이 `AGENT_PROJECT_ROOT`를 임시 경로로 격리

---

## 2. 태스크 실행

```powershell
cd $WT_PATH
python agent_launcher.py --fsa
# 프롬프트에 태스크 입력
```

**핵심 플래그**:
- `--fsa`: FSA 모드 (5 cycle 자동 완료, interactive 없음)
- `AF_DISABLE_REGISTRY_WRITE=1`: 레지스트리 write 차단 (격리가 자동 설정하나, 명시도 가능)

**태스크 입력 형식 권고**:
```
<대상 파일 경로> 파일에서 <변경 내용>. 오직 <대상 파일>만 수정하고 다른 파일은 절대 변경하지 말 것.
```

- 명시적 단일-파일 제약을 태스크 문자열에 포함 (R3 scope guard 미구현 상태 — AF 자체 allowlist 없음)
- ContextSchema 오류가 발생하면 `projects/agent_factory/context_schema.yaml` 확인 (F8)

---

## 3. 실행 중 관찰 포인트

| 관찰 항목 | 기대값 | 경고 신호 |
|-----------|--------|-----------|
| Provider 감지 | `claude_cli` 1순위 (R4 fix 이후) | `gemini_cli` 1순위면 3초 낭비 — R4 재확인 |
| FSA 사이클 수 | 1~2 (단순 변경 기준) | 5 도달 시 태스크 설명 재작성 필요 |
| Skill 로드 수 | 57개는 정상 (노이즈) | "Skill source not found: skill" 경고는 무해 |
| ContextSchema | validation pass | `missing context key` → F8 발생 |

---

## 4. 완료 후 Scope 검증 (필수)

```powershell
# worktree 내에서 실행
git diff --name-only
```

**기대값**: 지시한 파일 1개(또는 명시한 파일들)만 표시

**스코프 누수 발생 시**:
```powershell
# 의도하지 않은 변경 확인
git diff <unexpected-file>

# 레지스트리 등 부작용 파일 reset (F9)
git checkout skills/registry.yaml
git checkout projects/default/
```

---

## 5. 변경 내용 검토 및 반영

```powershell
# diff 확인
git diff <target-file>

# 정상이면 main worktree에 cherry-pick 또는 patch apply
git format-patch HEAD~1 --stdout | git -C D:\warkSpaces\agent-factory apply
```

또는 worktree 브랜치를 PR로 올려 3-Tier 리뷰 통과 후 머지.

---

## 6. Worktree 정리

```powershell
cd D:\warkSpaces\agent-factory
git worktree remove --force D:\hoonProJect\worktrees\r2-selfrun-exp
git branch -D r2-selfrun-exp  # 브랜치 불필요 시
```

---

## 알려진 마찰 포인트 (2026-05-22 기준)

| ID | 현상 | 상태 | 우회법 |
|----|------|------|--------|
| F3 | `agent_launcher.py "<task>"` cmdline 불가 (argparse subcommand 충돌) | 미수정 | `--fsa` 플래그 + interactive 입력 사용 |
| F8 | ContextSchema `missing_key` → 태스크 실행 중단 | 미수정 | `projects/agent_factory/context_schema.yaml` 키 사전 확인 |
| F9 | 태스크 실패에도 `projects/default/`, `skills/registry.yaml` 부작용 생성 | 미수정 | worktree 격리 후 실행, 완료 후 `git diff` 필수 |
| R4 | `GOOGLE_API_KEY` 없어도 gemini_cli 1순위 시도 → 3초 낭비 | ✅ fix (`cf4754b9`) | — |
| — | `skills/` 57개 로드 — 단순 작업에 불필요 | 미수정 | 노이즈. 결과에 영향 없음 |

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-22 | 최초 작성 (R1 PASS 기반, round4 friction 정리) |
