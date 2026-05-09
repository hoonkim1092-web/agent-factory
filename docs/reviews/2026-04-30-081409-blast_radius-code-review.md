# Code Review: blast_radius

> Source: scripts/blast_radius.py
> Date: 2026-04-30 08:14
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

`scripts/blast_radius.py`는 Phase 0 게이트의 결정적 분류기로 도입되지만, 두 리뷰가 합쳐서 보면 **분류기→게이트 연결 자체가 끊어진 상태**(Cross #3, Critic #1)와 **path 핀의 실재 파일 미스매치**(Cross #1), **regex 양방향 결함**(Critic #3 + Cross #2)이 동시에 존재함. 분류기의 신뢰성이 게이트 효력을 결정하므로 BLOCK.

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Critical] Tier 1 분류 결과와 review_gate가 정합성 충돌 — Tier 1 commit이 영구 차단
- **Critic**: "Tier 3가 Tier 2와 같은 셋을 반환 — 분류 결과가 게이트 동작에 차이를 만들지 못함" (Finding 1)
- **Cross**: "`required_agents(1)`은 `af-test-runner`만 반환하지만 `review_gate.py:146`은 `[1,2,3]`을 무조건 순회 → `missing-tier-2`/`missing-tier-3`로 차단" (Finding 3)
- **Judgment**: Cross의 코드 증거가 결정적. `scripts/review_gate.py:146`이 unconditional loop이고 `check_pending_review.py:48`은 Tier 1에 단일 에이전트만 안내한다면 **Tier 1로 분류된 모든 PR이 영원히 commit되지 않음** — Phase 0 출혈 봉합 효과의 정반대. Critic의 Tier 3 무력화도 같은 축의 문제(분류 결과 → 게이트 행동 미연결).
- **Action Required**:
  - `is_gate_blocked()`에 `state["blast_tier"]`를 읽어 `required_agents(tier)` 결과만 검증하도록 수정, 또는
  - Phase 0에서는 일관성을 우선해 `required_agents(1)`도 3-agent를 반환(설계의 단계적 도입 의도 보존).
  - Tier 3에 `"af-human-anchor"` sentinel을 추가하거나 `requires_human_anchor(tier) -> bool`을 노출해 Tier 2/3 차이 부여.
  - `blast_tier=1 + af-test-runner only` 케이스의 통합 테스트 추가.

#### 2. [ACCEPT] [High] `_TIER3_PATHS`가 실재 파일 경로와 불일치 — start_db/end_db Tier 3 보호 무효
- **Critic**: not flagged
- **Cross**: "`scripts/start_db.py`/`scripts/end_db.py`로 핀되어 있지만 실제 파일은 루트(`start_db.py`, `end_db.py`)" + grep 증거 (Finding 1)
- **Judgment**: Cross의 직접 검증(`classify_path("start_db.py") == 2`)이 결정적. Phase 0의 핵심 보호 대상이 분류기에서 누락. CLAUDE.md도 `python end_db.py`로 루트 호출을 명시.
- **Action Required**: `_TIER3_PATHS`에서 `scripts/start_db.py` → `start_db.py`, `scripts/end_db.py` → `end_db.py`로 수정. 모든 핀에 대해 `assert os.path.exists(path)` 단위 테스트 추가.

#### 3. [ACCEPT] [High] Tier 3 regex가 양방향 결함 — false-positive 폭증 + literal `exec("...")` 누락
- **Critic**: "`re.search`가 docstring/comment/string literal까지 매칭 → 일반 `core/*.py`가 무차별 Tier 3로" (Finding 3)
- **Cross**: "후행 `\b` 때문에 `exec("cmd")`/`eval("1+1")`은 매칭 실패" + regex 테스트 증거 (Finding 2)
- **Judgment**: 두 결함이 동시에 존재 — 코드 본문은 못 잡고(false-negative on literal calls), 주석/docstring은 잡힘(false-positive). AF 코드베이스에 token/secret/credential 식별자 산재 + 동적 코드 실행은 literal 형태가 흔함.
- **Action Required**:
  - 키워드 매칭을 호출 패턴으로 한정: `\bsubprocess\.(run|Popen|call|check_output)\b`, `\b(exec|eval)\s*\(`.
  - 후행 `\b` 제거하고 `(?=\W|$)` lookahead로 대체.
  - `password`/`token`/`secret`은 `["']` 인접조건으로 string assignment에 한정.
  - 여력 있으면 `tokenize`/`ast`로 comment·string 영역 제외.
  - 테스트 케이스: `exec("cmd")`, `# password = "..."`, `"""token counting"""`, `subprocess.run(...)`.

#### 4. [ACCEPT] [High] 경로 정규화 부족 — `./`, 절대경로, 중복 슬래시에서 Tier 3 핀 빗나감
- **Critic**: "`./scripts/run.py`, `scripts//run.py`, 절대경로 형태에서 `_TIER3_PATHS` 매칭 실패 → Tier 2로 격하" (Finding 2)
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 코드 증거가 강함 — `git diff --name-only`/hook 입력 형태가 환경별로 다양하고, 분류기가 commit 게이트의 진입점이라 우회 시 게이트 자체 무력화. ACCEPT.
- **Action Required**: `os.path.normpath(rel_path).replace("\\","/")` 적용, `./` prefix 제거, 절대경로는 workspace 기준 `os.path.relpath` 변환. Cross #1의 핀 수정과 함께 정규화 테스트 추가.

#### 5. [ACCEPT] [High] 비-`.py` 파일은 내용 검사 비활성 — CI workflow·shell·Dockerfile이 Tier 2로 격하
- **Critic**: "`.github/workflows/*.yml`, `.sh`, `.ps1`, `Dockerfile`, `policy.yaml`, `af.spec`, `version.py`가 path 핀에 없으면 Tier 2" (Findings 4 + 5)
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 Blueprint가 `af.spec`을 "hiddenimports 누락 시 frozen 빌드 크래시"로 명시 — Tier 3 path 핀 누락은 명백한 결함. ACCEPT.
- **Action Required**:
  - `_TIER3_PATHS`에 `af.spec`, `policy.yaml`, `version.py`, `.githooks/pre-commit`, `.githooks/post-commit` 추가.
  - `_TIER3_PREFIXES = (".github/workflows/", ".githooks/")` 추가하고 분류 로직에서 prefix 매칭 처리.
  - `.py/.sh/.ps1/.yml/.yaml/Dockerfile`에 대해서도 내용 검사 수행.

#### 6. [ACCEPT] [Medium] 64KB 읽기 제한 → 대형 파일에서 Tier 3 지표 누락
- **Critic**: "`agent_runner.py`(1,419줄), `skill_procurer.py`(1,146줄)에서 64KB 이상 위치의 지표가 잘림" (Finding 6)
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 AF 코드베이스 실측치(1000줄+ 파일 다수)에 비추어 합리적. 결정적 분류기에서 truncation은 디버깅 악몽. ACCEPT.
- **Action Required**: 청크 스캔(`while chunk := f.read(64*1024)`)으로 메모리 한계는 유지하되 전체 파일 검사. 또는 한도를 `512 * 1024`로 상향.

#### 7. [ACCEPT] [Medium] Tier 1 패턴이 자동 생성 메모리 산출물을 Tier 2로 분류
- **Critic**: "`projects/global_hoon_main/data/memory/general/claude_chat/*.json`이 PR마다 대량 stage되지만 위험도는 0" (Finding 7)
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 현재 `git status`에 정확히 그 패턴(`projects/global_hoon_main/data/memory/general/claude_chat/*.json` 다수)이 보임 — 실재하는 운영 부담. ACCEPT.
- **Action Required**: `_TIER1_PATTERNS`에 `^projects/.*/data/memory/.*\.(json|jsonl)$`, `^.*\.lock$` 추가.

#### 8. [ACCEPT] [Low] 런타임 tier 검증 부재 + 중복 `import sys`
- **Critic**: "`required_agents(0)`이 silent fallback으로 3-agent 반환; `_cli`와 `__main__`에서 `import sys` 중복" (Findings 8, 9)
- **Cross**: not flagged
- **Judgment**: 코드 위생 사항. ACCEPT (low priority).
- **Action Required**: `if tier not in (1,2,3): raise ValueError(...)` 한 줄 추가, `import sys`를 모듈 상단으로 이동.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Tier 1 분류 vs review_gate 충돌 (Tier 1 영구차단) | Critical | ACCEPT | Both |
| 2 | start_db/end_db 핀 경로 오류 | High | ACCEPT | Cross |
| 3 | Tier 3 regex 양방향 결함 (FP + FN) | High | ACCEPT | Both |
| 4 | 경로 정규화 부족 | High | ACCEPT | Critic |
| 5 | 비-.py 파일 내용검사 비활성 + 핀 누락 | High | ACCEPT | Critic |
| 6 | 64KB 읽기 제한 | Medium | ACCEPT | Critic |
| 7 | 메모리 산출물 Tier 1 패턴 누락 | Medium | ACCEPT | Critic |
| 8 | tier 검증 + import 정리 | Low | ACCEPT | Critic |

### Recommendations

**Phase 0 진입 전 필수 (#1~#5):**
1. `review_gate.is_gate_blocked()`가 `blast_tier`를 읽어 `required_agents(tier)`로만 검증하도록 통일 — Tier 1 영구차단 즉시 해소.
2. `_TIER3_PATHS`에서 `scripts/start_db.py` → `start_db.py`, `scripts/end_db.py` → `end_db.py` 수정 + `af.spec`/`policy.yaml`/`version.py`/`.githooks/pre-commit`/`.githooks/post-commit` 추가, `_TIER3_PREFIXES = (".github/workflows/", ".githooks/")` 도입.
3. Regex 재설계: 호출 패턴(`\bsubprocess\.(run|Popen|call|check_output)\b`, `\b(exec|eval)\s*\(`) 한정 + 후행 `\b` 제거 + `password`/`token`/`secret`은 `["']` 인접조건.
4. 경로 정규화: `os.path.normpath` + `./` prefix 제거 + 절대경로→상대경로 변환.
5. 비-.py 확장자 화이트리스트(`.sh/.ps1/.yml/.yaml/Dockerfile`)에 대해 내용 검사 수행.

**Phase 0 운영 1주차 후 보강 (#6~#8):**
6. 청크 스캔으로 전체 파일 검사 또는 한도 512KB 상향.
7. 메모리 산출물 Tier 1 패턴 추가.
8. 런타임 tier 검증 + import 정리.

**테스트 추가 필수:**
- 모든 `_TIER3_PATHS` 항목에 대한 `os.path.exists()` 검증.
- `classify_path` 입력 변형(`./`, 절대경로, 중복 슬래시).
- Regex: `exec("cmd")`, `# password = ...`, `"""token counting"""`, `subprocess.run(...)`.
- 통합 테스트: `blast_tier=1 + af-test-runner only`로 게이트 통과.