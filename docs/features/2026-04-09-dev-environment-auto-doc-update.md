# 개발환경 문서 자동 업데이트 파이프라인

> 날짜: 2026-04-09
> 상태: 설계 Draft
> 대상 파일: `scripts/blueprint_updater.py` (신규), `scripts/code_review_updater.py` (개선)
> 연관 파일: `.githooks/post-commit`, `.claude/settings.local.json`, `core/hooks/code_review_doc.py`

---

## 1. 문제 정의

### 현재 상태

| 문서 | 자동화 수준 | 누락된 부분 |
|------|-----------|-----------|
| `code-review.md` | PostToolUse hook 연결됨 | `--no-llm`으로만 동작 → 파일목록만 기록, LLM 리뷰 없음 |
| `Master_Blueprint.md` | pre-commit hook이 **차단만** 함 | §12 이력, §0 참조 테이블, §3 서브시스템 **자동 업데이트 없음** |

### 결과

- Blueprint §12를 매번 사람이 수동으로 작성해야 함
- code-review.md에 "Review skipped" 엔트리만 쌓임
- 리팩토링/기능변경 후 문서가 코드와 괴리됨

### 설계 원칙

1. **범용** — Claude Code, git hook, af.exe, CLI 수동 실행 모두 동일한 스크립트
2. **LLM 기반** — git diff를 분석해 변경 의미를 이해하고 적절한 섹션 업데이트
3. **graceful degradation** — LLM 없으면 최소 정보(파일 목록, 타임스탬프)만 기록
4. **기존 인프라 재사용** — `ControlPlaneLLM`, `design_review_utils.py`, `.af_review_queue`

---

## 2. 아키텍처

### 2.1 트리거 3경로 (범용)

```
경로 1: Claude Code PostToolUse hook
  Write|Edit → *.py 파일 감지
  → python scripts/code_review_updater.py    (기존, LLM 활성화)
  → python scripts/blueprint_updater.py      (신규)

경로 2: git post-commit hook
  커밋 완료
  → python scripts/code_review_updater.py --context "$(git log -1 --format=%s)"
  → python scripts/blueprint_updater.py --context "$(git log -1 --format=%s)"

경로 3: af.exe 런타임
  HookEventBus → CodeReviewDocHook (기존)
  HookEventBus → BlueprintUpdateHook (신규, 선택)

경로 4: CLI 수동 실행
  python scripts/blueprint_updater.py [workspace] --context "feat: 새 기능"
  python scripts/code_review_updater.py [workspace] --context "feat: 새 기능"
```

### 2.2 전체 흐름

```
[트리거] → git diff HEAD 수집
           ↓
         변경 파일 필터링 (core/**/*.py, scripts/**/*.py 등)
           ↓
         ┌────────────────┬──────────────────┐
         │                │                  │
    code_review_updater   │    blueprint_updater
    (기존 개선)           │    (신규)
         │                │                  │
    git diff → LLM        │    git diff → LLM
    코드 리뷰 생성         │    §12 행 생성 + §0/§3 패치 판단
         │                │                  │
    code-review.md        │    Master_Blueprint.md
    append                │    §12 행 prepend + §0/§3 in-place 수정
         └────────────────┴──────────────────┘
                    ↓
              항상 exit 0 (hook 차단 방지)
```

---

## 3. 상세 설계

### 3.1 `scripts/blueprint_updater.py` (신규)

#### 역할
git diff를 분석하여 Master_Blueprint.md의 해당 섹션을 자동 업데이트

#### 호출 인터페이스

```bash
python scripts/blueprint_updater.py [workspace] [--no-llm] [--context "..."]
```

| 인자 | 설명 | 기본값 |
|------|------|-------|
| `workspace` | git root 디렉토리 | 자동 감지 (git rev-parse) |
| `--no-llm` | LLM 없이 최소 업데이트만 | False |
| `--context` | 변경 설명 (commit message 등) | "" |

#### 업데이트 대상 판정

```python
# git diff --name-only HEAD~1..HEAD (post-commit) 또는
# git diff --name-only HEAD (pre-commit/hook)

BLUEPRINT_TRIGGERS = {
    "§0": lambda files: any(f.startswith("core/") and f.endswith(".py") for f in files),
    "§12": lambda files: any(
        f.startswith(("core/", "scripts/", "skills/"))
        or f in ("af.spec", "version.py", "run_factory_cli.py", "model_utils.py")
        for f in files
    ),
    "§3": lambda files: any(f.startswith("core/") and f.endswith(".py") for f in files),
    "§8": lambda files: any(f in ("af.spec", "build_exe.py", "version.py") for f in files),
    "§10": lambda files: any(f in ("requirements.txt", "af.spec") for f in files),
}
```

#### §12 자동 업데이트 (핵심)

**LLM 모드:**

```python
def _generate_changelog_entry(diff_text: str, changed_files: list, context: str) -> str:
    """LLM에게 git diff를 주고 §12 형식의 변경 이력 1행을 생성."""
    prompt = f"""Analyze the git diff below and generate a single changelog entry.

[Changed Files]
{', '.join(changed_files[:20])}

[Diff]
{diff_text[:6000]}

[Context]
{context or 'development session'}

## Output Format (Korean, single line)
type(scope): 한줄 요약 — 세부 변경 목록

## Rules
- type: feat, fix, refactor, chore, docs 중 하나
- scope: 변경된 주요 모듈명 (예: fsa_loop, pipeline, control)
- 한줄 요약 뒤에 em dash(—)로 구분하여 핵심 변경 3-5개 나열
- 기존 §12 이력 스타일과 동일하게 작성
- 새 파일이면 "신규" 표시, 메서드 변경이면 메서드명 포함

## Example
feat(3-plane): 3-Plane 통합 구현 — skill_quality_gate.py 신규, fsa_loop gate 삽입, intake memory_context 필드 추가
"""
    return llm.generate(prompt)
```

**no-llm 모드:**

```python
def _fallback_changelog_entry(changed_files: list, context: str) -> str:
    """LLM 없이 최소 이력 행 생성."""
    scope = changed_files[0].split("/")[1] if "/" in changed_files[0] else "root"
    files_str = ", ".join(f.split("/")[-1] for f in changed_files[:5])
    return f"chore({scope}): {context or 'code update'} — {files_str}"
```

**삽입 방식:**

```python
def _prepend_to_section_12(blueprint_path: str, entry: str, version: str):
    """§12 테이블의 헤더 행 바로 다음에 새 행을 삽입."""
    content = read(blueprint_path)
    date = datetime.now().strftime("%Y-%m-%d")
    new_row = f"| {date} | {version} | {entry} |"
    
    # "|------|------|----------|" 행 바로 다음에 삽입
    marker = "|------|------|----------|"
    idx = content.index(marker) + len(marker)
    updated = content[:idx] + "\n" + new_row + content[idx:]
    atomic_write(blueprint_path, updated)
```

#### §0 자동 업데이트 (새 파일 감지)

```python
def _update_section_0(blueprint_path: str, new_files: list, diff_text: str):
    """새로 생성된 core/*.py 파일을 §0 테이블에 추가."""
    # git diff --diff-filter=A --name-only 로 신규 파일만 추출
    # 각 파일에서 주요 클래스/함수를 AST로 추출 (LLM 불필요)
    for f in new_files:
        if not f.startswith("core/") or not f.endswith(".py"):
            continue
        classes, funcs = _extract_ast_symbols(f)
        role = _infer_role_from_path(f)  # 파일명/디렉토리로 역할 추론
        # §0 core/ 테이블에 행 추가
```

**AST 기반 심볼 추출 (LLM 불필요):**

```python
import ast

def _extract_ast_symbols(filepath: str) -> tuple[list[str], list[str]]:
    """파일에서 top-level 클래스와 함수를 추출."""
    with open(filepath, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    funcs = [node.name for node in ast.walk(tree) 
             if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")]
    return classes[:3], funcs[:3]
```

#### §3 자동 업데이트 (LLM 모드 전용)

기존 코드의 클래스/메서드가 변경되면 §3 해당 서브시스템 설명을 LLM이 패치.
- **트리거**: 기존 core/*.py 파일의 클래스/메서드 시그니처 변경 감지
- **방식**: `git diff`에서 `class ` 또는 `def ` 행의 변경을 감지
- **업데이트**: §3에서 해당 파일명이 언급된 블록을 찾아 LLM이 수정안 생성
- **비용 제어**: 시그니처 변경이 아닌 내부 로직만 바뀐 경우 스킵

```python
def _detect_signature_changes(diff_text: str) -> list[dict]:
    """diff에서 클래스/메서드 시그니처 변경을 감지."""
    changes = []
    for line in diff_text.splitlines():
        if line.startswith(("+class ", "+    def ", "-class ", "-    def ")):
            # 추가/삭제된 시그니처 수집
            changes.append({"type": "class" if "class" in line else "method", "line": line})
    return changes
```

#### 중복 방지

```python
def _already_logged(blueprint_path: str, commit_hash: str) -> bool:
    """동일 커밋이 이미 §12에 기록되었는지 확인."""
    content = read(blueprint_path)
    return commit_hash in content
```

#### 헤더 메타데이터 갱신

```python
def _update_header_metadata(blueprint_path: str, version: str):
    """<!-- last_updated: ... | version: ... --> 행 갱신."""
    # 기존 last_updated 날짜와 version을 현재 값으로 교체
```

### 3.2 `scripts/code_review_updater.py` (기존 개선)

#### 변경 사항

| 항목 | 현재 | 변경 후 |
|------|------|--------|
| PostToolUse 호출 모드 | `--no-llm` (파일목록만) | LLM 활성화 (기본) |
| 호출 빈도 제어 | 없음 (매 Edit마다) | quiet period 15초 debounce |
| 일일 한도 | 없음 | 최대 10회/일 (design_review_utils 연동) |

#### debounce 구현

PostToolUse hook은 매 Edit마다 호출되므로, 빈번한 LLM 호출을 방지해야 함:

```python
DEBOUNCE_FILE = ".af_review_queue/.code_review_debounce"
QUIET_PERIOD_SEC = 15

def _should_run(workspace: str) -> bool:
    """마지막 실행 후 quiet period가 지났는지 확인."""
    debounce_path = os.path.join(workspace, DEBOUNCE_FILE)
    if os.path.exists(debounce_path):
        try:
            mtime = os.path.getmtime(debounce_path)
            if time.time() - mtime < QUIET_PERIOD_SEC:
                return False
        except Exception:
            pass
    # 타임스탬프 갱신
    os.makedirs(os.path.dirname(debounce_path), exist_ok=True)
    Path(debounce_path).touch()
    return True
```

**PostToolUse hook에서는 debounce 적용, git post-commit에서는 즉시 실행.**

#### LLM 활성화 조건

```python
def _should_use_llm(workspace: str, no_llm: bool) -> bool:
    """LLM 리뷰 실행 여부 판정."""
    if no_llm:
        return False
    # 일일 한도 확인
    if not check_code_review_budget(workspace):
        return False
    # diff 최소량 확인 (5줄 미만이면 스킵)
    diff = _diff_content(workspace)
    if len(diff.splitlines()) < MIN_DIFF_LINES:
        return False
    return True
```

### 3.3 `.githooks/post-commit` 확장

현재 `post-commit`은 git-lfs만 처리. 여기에 Blueprint + code-review 업데이트 추가:

```bash
#!/bin/sh
# 기존: git lfs
command -v git-lfs >/dev/null 2>&1 && git lfs post-commit "$@"

# 신규: Blueprint + code-review 자동 업데이트
# 변경된 파일 중 코드 파일이 있을 때만 실행
CHANGED=$(git diff --name-only HEAD~1..HEAD 2>/dev/null)
CODE_CHANGED=$(echo "$CHANGED" | grep -E "^(core/|scripts/|skills/|run_factory_cli\.py|model_utils\.py|version\.py|af\.spec)" | head -1)

if [ -n "$CODE_CHANGED" ]; then
    COMMIT_MSG=$(git log -1 --format=%s)
    
    # Blueprint 자동 업데이트
    python scripts/blueprint_updater.py --context "$COMMIT_MSG" 2>/dev/null &
    
    # Code review 자동 업데이트 (LLM 사용)
    python scripts/code_review_updater.py --context "$COMMIT_MSG" 2>/dev/null &
    
    wait
    
    # Blueprint가 변경되었으면 자동 amend (선택적)
    if git diff --name-only | grep -q "Master_Blueprint.md"; then
        git add Master_Blueprint.md
        git commit --amend --no-edit 2>/dev/null
    fi
fi
```

### 3.4 PostToolUse hook 수정

`.claude/settings.local.json`의 PostToolUse hook 변경:

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "fp=$TOOL_INPUT_file_path; case \"$fp\" in *.py) python -m py_compile \"$fp\" 2>&1 || echo \"[af-hook] syntax error in $fp\" ;; esac",
      "timeout": 10,
      "statusMessage": "Python syntax check..."
    },
    {
      "type": "command",
      "command": "fp=$TOOL_INPUT_file_path; case \"$fp\" in *.py) python scripts/code_review_updater.py --context \"edit: $fp\" 2>/dev/null ;; esac",
      "timeout": 30,
      "statusMessage": "Code review update..."
    },
    {
      "type": "command",
      "command": "fp=$TOOL_INPUT_file_path; case \"$fp\" in *.py) python scripts/blueprint_updater.py --context \"edit: $fp\" 2>/dev/null ;; esac",
      "timeout": 30,
      "statusMessage": "Blueprint update..."
    },
    {
      "type": "command",
      "command": "fp=$TOOL_INPUT_file_path; python scripts/design_review_trigger.py \"$fp\" 2>/dev/null || true",
      "timeout": 5,
      "statusMessage": "Design review check..."
    },
    {
      "type": "command",
      "command": "for f in .af_review_queue/notifications/*.txt; do [ -f \"$f\" ] && cat \"$f\" && rm -f \"$f\"; done 2>/dev/null || true",
      "timeout": 3
    }
  ]
}
```

**핵심 변경**: `--no-llm` 제거 → LLM 리뷰 활성화 (debounce + 일일 한도로 비용 제어)

---

## 4. 비용 제어

| 제어 수단 | 적용 대상 | 값 |
|----------|----------|-----|
| quiet period (debounce) | PostToolUse | 15초 |
| 일일 한도 | LLM 코드 리뷰 | 10회/일 |
| 최소 diff 줄 수 | 전체 | 5줄 미만 스킵 |
| 중복 커밋 감지 | §12, code-review | 동일 commit hash 스킵 |
| import/주석 전용 변경 | code-review | 스킵 (SKIP_DIFF_PATTERNS) |

### LLM 호출 예산

| 트리거 | Blueprint LLM 호출 | Code Review LLM 호출 | 합계 |
|--------|-------------------|---------------------|------|
| PostToolUse (debounce 15초) | 1회 (§12 생성) | 1회 (리뷰 생성) | 2회 |
| git post-commit | 1회 | 1회 | 2회 |
| 하루 최대 (10회 한도) | 10회 | 10회 | 20회 |

---

## 5. 관련 파일 변경 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `scripts/blueprint_updater.py` | **신규** | Blueprint §12/§0/§3 자동 업데이트 |
| `scripts/code_review_updater.py` | 수정 | debounce 추가, `--no-llm` 기본값 해제 가능하게 |
| `.githooks/post-commit` | 수정 | Blueprint + code-review 업데이트 호출 추가 |
| `.claude/settings.local.json` | 수정 | PostToolUse hook에서 `--no-llm` 제거, blueprint_updater 추가 |
| `core/hooks/blueprint_update_hook.py` | **신규** (선택) | af.exe 런타임용 HookEventBus 훅 |
| `af.spec` | 수정 (선택) | `core.hooks.blueprint_update_hook` hiddenimports |

---

## 6. 검증 방법

```bash
# 1. blueprint_updater 단독 테스트
python scripts/blueprint_updater.py --context "test: 자동 업데이트 검증"
# → Master_Blueprint.md §12에 새 행 추가 확인

# 2. code_review_updater LLM 모드 테스트
python scripts/code_review_updater.py --context "test: LLM 리뷰 검증"
# → code-review.md에 LLM 리뷰 포함 확인 (Review skipped 아님)

# 3. git post-commit 통합 테스트
git commit -m "test: auto-doc hook"
# → Master_Blueprint.md §12 자동 추가 + code-review.md 업데이트 확인
# → 자동 amend로 Blueprint 변경이 같은 커밋에 포함 확인

# 4. debounce 테스트
# 15초 내 연속 Edit 3회 → LLM 호출 1회만 발생 확인

# 5. graceful degradation 테스트
python scripts/blueprint_updater.py --no-llm --context "test: no-llm mode"
# → 최소 정보만 기록 (파일 목록 + context)
```

---

## 7. 향후 확장

- **§3 deep update**: AST diff로 클래스/메서드 변경을 감지하고 §3 해당 블록을 LLM이 재작성
- **교차검증 연동**: blueprint_updater가 생성한 §12 행을 교차검증 파이프라인에 통과시켜 정확성 검증
- **version.py 자동 bump**: 변경 유형(feat/fix)에 따라 patch/minor 자동 증가

---

## 8. 미해결 결정 사항

1. **post-commit amend**: Blueprint 변경을 자동 amend할 것인가? → amend는 위험(진행 중 rebase 충돌). 대안: 별도 "docs: auto-update" 커밋
2. **§3 업데이트 범위**: 시그니처 변경만? 내부 로직 변경도? → 초기엔 시그니처만, 이후 확장
3. **Blueprint 일일 한도**: code-review와 별도 카운터? 공유? → 별도 카운터 권장
