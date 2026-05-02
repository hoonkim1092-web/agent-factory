# oh-my-openagent의 AST/LSP — 코드 기반 분석 + Agent Factory와 비교

작성일: 2026-05-02
작성자: Claude (Agent Factory 세션)
대상: `code-yeongyu/oh-my-openagent` (이전 명: `oh-my-opencode`, 별명: `omo`)
범위: AST-Grep + LSP 통합 동작 + Agent Factory 현재 정적 진단 인프라와의 비교
방법: GitHub raw fetch + 우리 저장소 코드/로그 실측. **확인 범위 내에서 추정 사용 없음**. fetch가 닿지 않은 코드/문서는 §2.3·§3.3·§4에 "본 fetch 범위 내에서 미확인"으로 별도 표기.

문서 성격: **분석 전용**. 권고/plan은 별도 문서.

---

## 1. 분석 동기

본 세션에서 NEXT_STEPS.md "AST/LSP 인벤토리 재분석" 작업을 수행 중, 처음에는 **SST OpenCode**(`github.com/sst/opencode`)를 비교 대상으로 잡고 있었다. 사용자가 비교 대상이 **oh-my-openagent**(`code-yeongyu/oh-my-openagent`)임을 정정. 두 프로젝트는 다음과 같이 분리된다:

- **SST OpenCode**: AI coding agent의 메인 코어 (TypeScript/Bun)
- **oh-my-openagent**: OpenCode 위에 올라가는 community plugin/harness. specialized agent + 자체 tool 추가 (Sisyphus, Hephaestus, Prometheus, Oracle, Librarian, Explore)

`docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md`는 SST OpenCode 분석 결과이며, 본 문서는 그것과 별개로 oh-my-openagent를 다룬다.

---

## 2. oh-my-openagent의 LSP — 6개 AI tool (Pull 모델)

소스: `src/tools/lsp/tools.ts`, `src/tools/lsp/AGENTS.md`

### 2.1 노출 tool 목록

| Tool | AGENTS.md 발췌 |
|------|--------------|
| `lsp_goto_definition` | "Jump to symbol definition" |
| `lsp_find_references` | "All usages of a symbol" |
| `lsp_symbols` | "Document outline or workspace symbol search" |
| `lsp_diagnostics` | "Errors/warnings from language server" |
| `lsp_prepare_rename` | "Validate rename before applying" |
| `lsp_rename` | "Apply safe rename across workspace" |

`lsp_servers` tool은 제거됨 (OpenCode 네이티브 capability와 중복).

### 2.2 동작 메커니즘 (AGENTS.md 직접 인용)

- "File must be opened via `didOpen` before any LSP request" — `LSPClient.openFile()`가 자동 수행
- "1s delay after `didOpen` for server initialization before sending requests" — 강제 대기
- 서버 discovery: 파일 확장자 기반. user config (`.opencode/lsp.json`) → builtin server fallback

### 2.3 모델 구분

6개 tool 모두 **AI agent가 명시 호출하는 pull 모델**. 본 문서가 fetch한 범위 내에서 "edit tool 후 자동 진단 push"에 해당하는 코드/문서는 확인되지 않았다 (SST OpenCode의 `tool/edit.ts` 패턴이 oh-my-openagent에서 별도 노출 tool로 분리되는지 본 fetch 범위 내에서 미확인).

---

## 3. oh-my-openagent의 AST-Grep — 2개 AI tool

소스: `src/tools/ast-grep/cli.ts`, `src/tools/ast-grep/tool-descriptions.ts`, `src/tools/ast-grep/{downloader,sg-cli-path,pattern-hints,environment-check}.ts`

### 3.1 노출 tool 목록

| AI-facing tool 이름 | tool-descriptions.ts 직접 인용 |
|--------------------|-----------------------------|
| `ast_grep_search` | "Search code by AST structure (25 languages). This is NOT regex." |
| `ast_grep_replace` | "Rewrite code by AST pattern (25 languages). Dry-run by default." |

(코드 내부 상수 식별자는 SCREAMING_SNAKE 형식 — `AST_GREP_SEARCH` / `AST_GREP_REPLACE`. AI agent에 노출되는 tool 이름은 lowercase snake.)

파라미터:
- pattern: "AST pattern - valid, parseable code using $VAR (one node) and $$$ (many nodes)"
- (replace) rewrite: "Target code structure reusing captured variables"
- regex 금지: `|`, `.*`, `\w`, `[a-z]` 입력 시 거부

### 3.2 실행 모델

- **Bun subprocess**: `spawn()`으로 `ast-grep` 바이너리 실행
- **고정 인자**: `["run", "-p", pattern, "--lang", lang, "--json=compact"]` + 옵션 (`-r`, `-C`, `--globs`)
- **결과 파싱**: `--json=compact` stdout → `createSgResultFromStdout()` → `SgResult` 구조체
- **Two-pass rewrites**: `--update-all`은 JSON 출력과 동시 사용 불가. 따라서 (1) JSON으로 매치 수집 (2) `--update-all`로 적용
- **에러 처리**: spawn 실패 / timeout / 바이너리 누락 / non-zero exit code 모두 결과 객체로 회수

### 3.3 모델 구분

2개 tool 모두 **AI agent가 명시 호출하는 pull 모델**. push (자동 호출) 코드는 본 fetch 범위에서 확인되지 않음.

---

## 4. SST OpenCode와의 비교

| 항목 | SST OpenCode | oh-my-openagent |
|------|--------------|-----------------|
| LSP tool 수 | 9개 (goToDef, findRef, hover, docSym, wsSym, goToImpl, prepCallHier, in/outCalls) | 6개 (goto_def, find_ref, symbols, diagnostics, prepare_rename, rename) |
| Diagnostics push | edit tool 끝에서 `lsp.diagnostics()` 자동 호출 (확인됨) | 본 fetch 범위에서 확인 안 됨 (lsp_diagnostics는 pull tool로 노출) |
| Rename | 직접 노출 안 됨 | **2단계 safe rename** (prepare → apply) |
| Hover/Call hierarchy | 노출 | 노출 안 됨 |
| AST-Grep | **본체에 없음** (plugin/skill에만) | **AI tool 1급 시민** (search + replace) |

핵심 관찰: oh-my-openagent는 SST OpenCode 대비 hover/callHierarchy 같은 보조 탐색을 제거하고, **rename safe workflow + AST-Grep 노출**을 추가. "탐색은 줄이고 안전한 변경에 무게".

---

## 5. Agent Factory의 현재 상태 (실측)

본 세션 인벤토리 + 효과 측정 결과를 사실 그대로 정리.

### 5.1 정적 진단 3종 인벤토리

| 시스템 | 위치 | 상태 |
|--------|------|------|
| `core/review_bundle.py` | risk_id 최대 7종 추출(engine별 차이, §5.2 참고), `.af_review_queue/review_bundle.md` 저장 | 코드 OK, 형식은 단순 헤더+per-file 블록 |
| `scripts/test_gap_analyzer.py` | diff에서 risky pattern + 관련 테스트 부재 검출 | 코드 OK |
| `core/hooks/lsp_check.py` | `LSPCheckHook(ContinuationHook)` — pyright 실행 | `core/agent_runner.py:972-973`에서 self-hosted agent의 hook bus에만 등록 |

> ⚠️ **`_WRITE_TOOLS` 하드코딩 갭**: `core/hooks/lsp_check.py:29` `_WRITE_TOOLS`에는 `write_file`·`edit_file` 등 7종만 포함. `apply_edit`(`skills/hash_edit/skill.py:23`)·`apply_block_edit`(`skills/hash_edit/skill.py:43`) 누락 — 이 두 tool로 파일 편집 시 LSPCheckHook 발화 안 함.

### 5.2 review_bundle.py 실제 출력 schema (`core/review_bundle.py:107-115`)

```
# review_bundle (engine={ast|grep})

## {file_path}
- L{line} `{risk_id}`: `{text}`
_(no risks detected)_  ← risks 0개일 때만
```

**risk_id (engine별 차이)**:
- `engine=grep`: 7종 — `subprocess_usage`, `shell_true`, `shlex_split`, `os_system`, `eval_usage`, `exec_usage`, `dynamic_import` (`core/review_bundle.py:36-44` `_RISK_PATTERNS`)
- `engine=ast`: 6종 — `dynamic_import` 제외 (`core/review_bundle.py:66-73` `_ast_risks` 패턴 누락. ast-grep-py 설치 시 grep fallback보다 검출 종류가 *적다*)
- production engine은 `core/review_bundle.py:_ast_available()` 결과에 따라 결정 — 즉 ast-grep-py 설치 환경에서는 `dynamic_import` 검출 안 됨.

**`{line}` 인덱스 계약 차이 (schema bug)**:
- grep fallback (`core/review_bundle.py:55`): `text[: m.start()].count("\n") + 1` → **1-based**
- AST (`core/ast_engine.py:91`): `rng.start.line` 그대로 (ast-grep-py / Tree-sitter 표준 → **0-based**)
- 같은 `L{line}` 출력 토큰이 engine에 따라 1-based vs 0-based로 갈림. plan에서 single contract 고정 권고 (예: `core/ast_engine.py.search()` 반환 1-based 정규화 또는 `review_bundle.save()` 직전 +1 보정 + `tests/test_review_bundle.py`에 동일 line 계약 테스트).

**`{file_path}` 절대/상대 모호성 (schema bug)**:
- `scripts/build_review_bundle.py:47-56` `_resolve_paths()`가 `Path(workspace) / f`로 **절대경로 변환** 후 `core/review_bundle.py:build()`에 전달.
- `core/review_bundle.py:save()`는 받은 경로를 그대로 `## {file_path}` 헤더로 출력 → bundle은 절대경로 수록.
- reviewer prompt(`.claude/agents/af-critic.md:33`)와 queue state(`pending_agent_review.json`)는 workspace-relative 가정 — schema 계약 모호. plan에서 workspace-relative로 고정 권고 (필요 시 `abs_path` sidecar 분리).

"§1~§7 섹션 구조"는 **존재하지 않음** (이전 분석 시도에서 가정했던 부분).

### 5.3 Hook 배선 실측 (`.claude/settings.local.json`)

PostToolUse Write|Edit matcher에 등록된 hook은 (line 191-212 `PostToolUse` 블록):
- `sh scripts/hookpy.sh scripts/run.py post_edit_code_review`
- `sh scripts/hookpy.sh scripts/run.py post_edit_design_review`

`post_edit_enqueue`는 settings.local.json에 직접 등록되어 있지 않다. `scripts/hook_runner.py:476`에 builtin dispatch는 있지만, 현재 hook 설정에서 이를 부르는 항목은 본 분석 범위에서 확인 안 됨.

`post_agent_record`도 settings.local.json hook 설정에 직접 없으며, hook_runner.py:483 builtin dispatch로 등록.

### 5.4 효과 측정 (누적 데이터)

> 추출 명령은 §9.4 참고. 모든 측정은 명시된 sink 한정 — 다른 sink(stdout, chat trace, manual subagent 경로)는 별도 표기.

#### Q-A: review_bundle risk_id 인용 (`docs/reviews/*.md` 46개 review 기준 / engine별 risk_id 정의는 §5.2)

> 참고: 표의 인용 1건은 메타 리뷰. 메타 제외 시 7종 모두 0/46.

| risk_id | 인용 review 수 |
|---------|-------------|
| subprocess_usage | 0 |
| shell_true | 0 |
| shlex_split | 0 |
| os_system | 0 |
| eval_usage | 0 |
| exec_usage | 0 |
| dynamic_import | 1 (메타: `2026-05-01-113842-review_bundle-code-review.md` — review_bundle.py 자체 리뷰) |

review_bundle을 언급한 7개 review를 별도 분류한 결과: 7건 모두 review_bundle 관련 코드/plan/분석 문서 자체에 대한 메타 review. 일반 코드 리뷰에서 review_bundle을 evidence로 인용한 흔적은 본 분석 범위에서 0건. 또한 `dynamic_import`는 grep fallback에서만 검출되므로 production engine이 ast 모드일 때 인용률은 7종 모두 0.

#### Q-B: hook-enforced test_gap_analyzer 호출 (`.af_review_queue/hook_events.log` sink 한정)

| event | count |
|-------|-------|
| test_gap_analyzer (forced-fail) | 0 |
| test_gap_analyzer (skipped) | 0 |
| test_gap_analyzer (success) | 0 |

코드는 `scripts/hook_runner.py:387` builtin dispatch에 있으나 본 sink 범위에서 호출 0건. 단, `af-test-runner` subagent가 `.claude/agents/af-test-runner.md:41-43`에서 직접 `python scripts/test_gap_analyzer.py --workspace .`를 실행하는 **manual 경로는 hook_events.log에 기록되지 않으며 본 측정 범위 외**다. manual 경로 호출 횟수는 별도 sink (Claude Code transcript, Bash tool log) 필요 — 본 분석 범위에서 미측정.

#### Q-C: post_edit_enqueue 시계열

- 시작: 2026-04-17T22:30
- 최후: 2026-05-02T14:25
- 총 552건
- 가장 최근 2건은 `core/foo.py` — **테스트 fixture 경로**. `tests/test_hook_runner_builtins.py`가 만든 fake event 포함 가능성 (정확 비율은 §7.2 #1 spike에서 측정 예정 — 현 시점 분리 미확보)

본 552건 카운트는 "현재 hook 배선의 실제 effective 호출 수"로 직접 환산 불가. **현재 `.claude/settings.local.json` PostToolUse 블록 (line 191-212)에는 `post_edit_code_review` / `post_edit_design_review`만 등록되어 있고 `post_edit_enqueue`는 직접 등록 안 됨**. 552건은 "과거 어느 시점의 호출 누적 + 테스트 fake event"이며 **현재 배선의 효과 증거가 아님**. fake/effective 분리 측정은 다음 세션 spike에서 수행.

#### Q-D: 3-tier verdict 분포 (`hook_events.log` review-recorded sink 한정 — 별도 sink와 분리 측정 필요)

| agent | pass | block |
|-------|------|-------|
| af-test-runner | 14 | 0 |
| af-critic | 21 | 1 |
| af-cross-review | 16 | 0 |

총 51 PASS / 1 BLOCK.

> ⚠️ **표본 편향 caveat**: 이 수치는 `hook_events.log`의 `review-recorded` 라인 52건만 카운트한 결과이며, **별도 sink인 `docs/reviews/*.md` Verdict 헤더 분포 (실측: 16 BLOCK + 25 WARN)와 통합되지 않는다**. `post_agent_record`가 `scripts/hook_runner.py:347-348`에서 호출되지만 모든 review 작성 경로에서 발화하지 않아 hook log는 부분 sink로 동작한다. "98% PASS" 같은 비율은 본 sink 외 분포를 누락하므로 §6 비교 매트릭스에서 직접 인용 금지.

#### Q-E: LSPCheckHook 호출 흔적 (`hook_events.log` sink 한정)

`grep "LSPCheckHook\|\[LSP\]" .af_review_queue/hook_events.log` 결과 0건.

> ⚠️ **측정 sink 한계**: `core/hooks/lsp_check.py:205-206`은 `print(f"[LSPCheckHook] ...")`만 호출하고 `_log_hook_event()`를 호출하지 않는다. 따라서 hook_events.log 0건은 **"호출 0회"가 아니라 "log sink 부재"** 의미. 실제 호출 여부는 별도 sink (Claude Code chat transcript / stdout 캡처 / 신규 lsp_check event 추가) 중 하나 필요 — 본 분석 범위에서 분리 미수행.

원인 후보 (휴면 상태 자체에 대한 실측): pyright 미설치 (`which pyright` → not found) + `AGENT_LSP_CHECK` 환경변수 미설정 (settings.local.json / .env / *.cmd / *.ps1 / *.sh 모두에서 미발견).

#### Q-F: Phase 3.5 메트릭 — `review_metrics.jsonl` 부재

`scripts/review_metrics_logger.py`가 작성하는 `review_metrics.jsonl`:
- 위치 정의: `_queue_dir(workspace)/review_metrics.jsonl`
- `find . -name "review_metrics.jsonl"` 결과: **파일 부재**

→ 0건 원인 후보 (실측 분리는 §7.2 spike, 본 문서는 후보 나열만):
- (a) `_post_agent_record()` 호출 경로 미배선 — settings.local.json:191-212 PostToolUse에 직접 등록 부재
- (b) 호출되지만 `scripts/hook_runner.py:347-365`의 try/except로 silent failure (예외 삼킴)
- (c) workspace path mismatch로 다른 위치에 작성됨 — 본 분석 범위에서 다른 path 탐색 미수행

---

## 6. 비교 매트릭스

| 측면 | SST OpenCode | oh-my-openagent | Agent Factory (실측) |
|------|--------------|-----------------|---------------------|
| AST-Grep 노출 | 본체 없음 | AI tool 2개 (search/replace, pull) | review_bundle.md 파일 매개 (push, 1회성) |
| LSP 노출 | 9개 AI tool + edit 자동 push (확인됨; `docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md` 기준, §5 잔존 모순은 별도 인계) | 6개 AI tool (pull) | LSPCheckHook (push, AgentRunner self-hosted bus만, 휴면) |
| Rename safe | ❌ 직접 노출 X | ✅ prepare → apply 2단계 | ❌ |
| 정적 진단 효과 측정 | 본 문서 범위 외 | 본 문서 범위 외 | risk_id 인용 ~2% (Q-A, 메타 리뷰 제외 시 0/46), hook-enforced test_gap 호출 0건 (Q-B, manual subagent 경로 제외), LSPCheckHook hook_events.log 0건 (Q-E, sink 한정) |
| Subagent 컨텍스트 통합 | 메인 AI 단일 | 메인 AI + specialized agent (Sisyphus 등) | 메인 AI + Claude Code subagent (af-critic 등) — 메인의 LSPCheckHook 결과는 subagent로 자동 전파 안 됨 |

---

## 7. 갭 식별 (분석으로만, 결정 보류)

### 7.1 측정으로 답을 얻은 부분

- review_bundle의 raw risk_id 형식은 subagent reasoning에 거의 인용되지 않는다 (1/46)
- LSPCheckHook은 의도된 휴면 상태이며, pyright/환경변수 양쪽 미설정
- test_gap_analyzer는 hook_events.log 기준 호출 0건

### 7.2 측정으로 답을 못 얻은 부분 (배선 검증 미완료)

- post_edit_enqueue 552건 중 fake (테스트) vs 실 사용 비율
- post_agent_record 52건이 어떤 호출 경로로 발생했는가
- review_metrics.jsonl 부재가 "Phase 3.5가 한 번도 안 돈 것"인지 "다른 위치에 저장되는 것"인지

### 7.3 architectural gap (oh-my-openagent 모델 대비)

- AF는 ast-grep 기반 분석을 가지고 있으나 AI tool로 노출하지 않음 (파일 매개만; **Python-only** — `scripts/build_review_bundle.py:51` `.py` 확장자 필터, `core/ast_engine.py:56` `detect_lang()` 미지원 확장자 → python default)
- AF는 LSP를 가지고 있으나 메인 self-hosted agent에만 등록 + 휴면
- AF는 rename safe workflow 같은 pre-hoc validation 메커니즘 없음 — post-hoc 3-tier review만 (`LSPCheckHook` 활성화해도 rename-safe 불가: `core/hooks/lsp_check.py:103`은 pyright shell-out이며, `core/lsp_bridge.py`의 JSON-RPC `LSPBridge`가 존재하나 `lsp_check.py`에 미연결)

본 갭들은 **분석 결과**이며 권고가 아니다. 비용/효과 정량화 후 plan에서 별도 결정.

---

## 8. 후속 작업 후보 (권고 아님)

이 섹션은 plan이 아니라 **본 분석에서 자연 도출되는 후보 목록**이다. 우선순위 부여 / 일정 / 실행 결정은 별도 plan 문서에서 다룬다.

1. **post_edit_enqueue / post_agent_record 호출 경로 정확한 추적**
   - 552건 / 52건이 어떤 호출 경로로 발생하는지 settings.local.json에 등록되지 않은 경로 포함 전수 조사
   - `tests/test_hook_runner_builtins.py` fake event 비중 분리

2. **review_metrics.jsonl 작성 흐름 재확인**
   - 0건의 원인 (실제 미작성 vs 다른 위치)

3. **review_bundle 형식 재검토**
   - 현재 raw risk_id 리스트 형식의 subagent 인용률 ~2% 사실 위에서 형식 변경의 효과 가설

4. **AST tool AI 노출 가능성 평가** (oh-my-openagent 모델)
   - 우리는 `core/ast_engine.py`에 search/replace/search_dir/replace_file 이미 존재
   - 현재 pipeline 진입 언어: **Python-only** (`scripts/build_review_bundle.py:51` `.py` 필터; `core/ast_engine.py:56` `detect_lang()` 미지원 확장자 → python default)
   - AI tool wrapper 신설 시 비용(event 이름 제안: `ast_tool_search`) + 효과(subagent reasoning 인용률 측정, Q-A 기준) 가설

5. **LSPCheckHook 활성화/유지/제거 후보**
   - 결정 입력 후보: pyright 동봉 비용 (frozen build) vs subagent 전파 경로 신설 비용
   - 비용 측정 후보: `lsp_check_skipped` / `lsp_check_result` event 추가 시 1주 수집 가능 (현재 print() 전용 sink, Q-E 참고)
   - ⚠️ `_WRITE_TOOLS` 하드코딩 갭: 활성화 시 `apply_edit`/`apply_block_edit` 편집 시 발화 안 함이 전제 조건 (`core/hooks/lsp_check.py:29`)
   - 결정 시점은 plan 단계. 입력 자료로 #1, #2 결과 + 1주 메트릭 수집 결과를 사용 가능

6. **Rename safe workflow 도입 가능성 평가**
   - LSP 서버 전제. 비용 큼. AF use case에 정당화되는지 별도 분석

위 6개는 **후보**. 본 문서는 결정 권한을 주장하지 않으며 우선순위·일정·실행 결정은 별도 plan에서 다룬다.

---

## 9. 데이터 출처

### 9.1 oh-my-openagent (raw GitHub fetch — commit SHA 고정, 본 분석은 해당 SHA 코드 기준)
- fetch 시점: 2026-05-02. 고정 SHA: `e17850cbab3e3a609444c1a0cec26afb244c3fc5` (GitHub API `GET /repos/code-yeongyu/oh-my-openagent/commits/dev` 응답, 2026-05-02 조회)
- `https://github.com/code-yeongyu/oh-my-openagent/blob/e17850cbab3e3a609444c1a0cec26afb244c3fc5/README.md`
- `https://github.com/code-yeongyu/oh-my-openagent/blob/e17850cbab3e3a609444c1a0cec26afb244c3fc5/docs/guide/overview.md`
- `https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/e17850cbab3e3a609444c1a0cec26afb244c3fc5/src/tools/lsp/AGENTS.md`
- `https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/e17850cbab3e3a609444c1a0cec26afb244c3fc5/src/tools/lsp/tools.ts`
- `https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/e17850cbab3e3a609444c1a0cec26afb244c3fc5/src/tools/ast-grep/tool-descriptions.ts`
- `https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/e17850cbab3e3a609444c1a0cec26afb244c3fc5/src/tools/ast-grep/cli.ts`
- `https://ohmyopenagent.com/`
- 관련 fork: `https://github.com/opensoft/oh-my-opencode`

### 9.2 SST OpenCode (이전 세션 분석 자료 — 본 문서에서는 비교 컨텍스트만)
- `docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md` (§5에 잔존 모순 있음, NEXT_STEPS.md에 인계)

### 9.3 Agent Factory (저장소 실측)
- `core/review_bundle.py`, `core/ast_engine.py`, `core/hooks/lsp_check.py`, `core/agent_runner.py`
- `scripts/hook_runner.py`, `scripts/test_gap_analyzer.py`, `scripts/review_metrics_logger.py`
- `.claude/settings.local.json`, `.claude/agents/af-{critic,cross-review,test-runner}.md`
- `.af_review_queue/hook_events.log`, `docs/reviews/*.md`

### 9.4 추출 명령 (재현 가능성)

본 세션 측정에 사용한 명령. 다음 세션에서 동일 수치 재현 시 이 명령을 그대로 실행.

```bash
# Q-A: review_bundle risk_id 인용 (docs/reviews/ 46개 review)
ls docs/reviews/*.md | wc -l                                       # 표본 크기
for risk in subprocess_usage shell_true shlex_split os_system eval_usage exec_usage dynamic_import; do
  c=$(grep -lE "\b${risk}\b" docs/reviews/*.md 2>/dev/null | wc -l)
  echo "${risk} | ${c}"
done

# Q-B: hook-enforced test_gap_analyzer 호출 (hook_events.log 한정 — manual subagent 경로 제외)
grep -cE 'test_gap_analyzer.*forced-fail' .af_review_queue/hook_events.log
grep -cE 'test_gap_analyzer.*skipped'     .af_review_queue/hook_events.log
grep -cE 'test_gap_analyzer.*[^-]rc=0'    .af_review_queue/hook_events.log

# Q-C: post_edit_enqueue 시계열
grep -E 'post_edit_enqueue' .af_review_queue/hook_events.log | head -1   # 시작
grep -E 'post_edit_enqueue' .af_review_queue/hook_events.log | tail -1   # 최후
grep -cE 'post_edit_enqueue' .af_review_queue/hook_events.log            # 총 건수

# Q-D: 3-tier verdict 분포 (review-recorded sink 한정)
grep -cE 'review-recorded' .af_review_queue/hook_events.log
grep 'review-recorded' .af_review_queue/hook_events.log | grep -oE 'verdict=[a-z]+' | sort | uniq -c
# (별도 sink) docs/reviews/*.md Verdict 헤더 분포:
grep -hE '^### Verdict:' docs/reviews/*.md | sort | uniq -c

# Q-E: LSPCheckHook 호출 흔적 (hook_events.log sink 한정 — print() 직접 출력은 미포함)
grep -cE 'LSPCheckHook|\[LSP\]' .af_review_queue/hook_events.log
which pyright 2>/dev/null || echo "pyright not found"
grep -rE 'AGENT_LSP_CHECK' .claude/ .env 2>/dev/null

# Q-F: review_metrics.jsonl 부재 확인
find . -name "review_metrics.jsonl" 2>/dev/null
grep -cE 'append_metric|review_metrics' .af_review_queue/hook_events.log
```

---

## 10. 변경 이력

- 2026-05-02 초안: 본 세션 인벤토리 + 효과 측정 + oh-my-openagent raw fetch 결과 통합 작성. 권고 0개 (분석/권고 분리 원칙).
- 2026-05-02 v2: 23:07 cross-review 13건(자가-reject 1건 제외 ACCEPT 11건 + 재분석 추가 발견 1건 + Low #10 실측 정정 1건) 반영. 정정 범위:
  - §5.2 schema 계약 명시 (line 1-based 정규화 권고, file_path 절대/상대 모호성, engine별 6종/7종 차이)
  - §5.3 PostToolUse 블록 라인 범위 정정 (188-208 → 191-212)
  - §5.4 Q-A~Q-F 측정 범위·표본 편향·silent failure 후보 정정
  - §6 SST OpenCode "확인됨" 권원 표시
  - §8 #5 plan-tone 톤다운 ("결정" → "결정 입력 후보")
  - §9.4 신설: Q-A~Q-F 추출 명령 + §9.1 oh-my-openagent commit SHA pin
- 2026-05-02 v3: 2라운드 cross-review BLOCK 6건(진짜) 반영. 정정 범위:
  - §9.1 `/dev/` URL → commit SHA `e17850cbab3e3a609444c1a0cec26afb244c3fc5` permalink 직접 교체 (#4)
  - §2.3 "분리된 것으로 보이지만 단정 불가" → "본 fetch 범위 내에서 미확인" 톤다운 (#8)
  - §7.3 AST tool Python-only 언어 scope 명시 (`build_review_bundle.py:53` 필터, `ast_engine.py:29` default) (#9)
  - §8 #4 동일 언어 scope + `ast_tool_search` event 이름 추가 (#9/#12)
  - §7.3 rename-safe: `LSPCheckHook` 활성화해도 불가 이유 명시 (pyright shell-out, JSON-RPC 없음) (#10)
  - §5.1 `_WRITE_TOOLS` 하드코딩 갭 footnote 추가 (`apply_edit`/`apply_block_edit` 누락) (#11)
  - §8 #5 `_WRITE_TOOLS` 갭 footnote + `lsp_check_skipped`/`lsp_check_result` event 이름 추가 (#11/#12)
- 2026-05-02 v4: 3라운드 cross-review BLOCK 2건(High) + 정정 2건(Medium/Low) 반영. 정정 범위:
  - §7.3 "JSON-RPC LSP 클라이언트 없음" → `core/lsp_bridge.py` 존재 명시 + lsp_check.py 미연결 사실 기술로 교체 (High)
  - §8 #5 "활성화 전 선행 수정 필요" / "추가 후 1주 수집" → 조건·가능성 기술로 톤다운 (High, 분석 문서 원칙 적용)
  - §7.3/§8 라인 번호 정정: build_review_bundle.py:51 (←53), ast_engine.py:56 (←29) (Medium)
  - §5.1 표 "7종 추출" → "최대 7종(engine별 차이, §5.2 참고)" (Low)
