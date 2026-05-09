# OpenCode LSP 아키텍처 분석

작성일: 2026-05-02
대상: SST OpenCode (`github.com/sst/opencode`, `dev` 브랜치)
분석 범위: LSP 통합 + AI tool 노출 패턴 + ast-grep 사용 여부
방법: WebFetch로 실제 소스 파일 직접 확인 (문서 추정 아님)

---

## 1. 분석 동기

Agent Factory의 `core/review_bundle.py`는 ast-grep 기반 구조 분석을 수행한다.
사용자가 "OpenCode가 LSP+AST-Grep 조합을 핵심 차별점으로 내세운다"고 언급해
실제 OpenCode 코드베이스를 검증해, 우리가 따라잡거나 차별화할 지점이 무엇인지 확정.

---

## 2. 확인된 사실

### 2.1 LSP 모듈 구조

| 파일 | 역할 |
|------|------|
| `packages/opencode/src/lsp/server.ts` | LSP 서버 spawn + lifecycle (Info/Handle 인터페이스) |
| `packages/opencode/src/lsp/client.ts` | JSON-RPC 클라이언트 |
| `packages/opencode/src/lsp/lsp.ts` | coordination (touchFile/diagnostics/references 등 외부 API) |
| `packages/opencode/src/lsp/diagnostic.ts` | 진단 처리 |
| `packages/opencode/src/lsp/launch.ts` | 서버 시작 |
| `packages/opencode/src/lsp/language.ts` | 언어별 매칭 |
| `packages/opencode/src/tool/lsp.ts` | **AI에게 노출되는 LSP tool 구현** |
| `packages/opencode/src/tool/lsp.txt` | AI tool 설명 prompt |

### 2.2 LSP 서버 lifecycle

- **Long-lived pool**: 활성 LSP 클라이언트들을 `State`에 풀로 유지
- **Lazy spawn**: 파일 접근(`touchFile`) 시점에 확장자 매칭으로 필요한 서버만 시작
- **자동 설치**: 바이너리가 PATH에 없으면 GitHub Releases / NPM에서 다운로드
  (`Flag.OPENCODE_DISABLE_LSP_DOWNLOAD`로 비활성화 가능)
- **빌트인 14개 서버**: TypeScript, Python, Go, Rust, Ruby, C/C++, C#, Elixir, Zig, Java, Vue, Svelte 등
- **150ms debounce**: 진단 처리에서 성능 최적화

### 2.3 AI에게 노출되는 9개 LSP operation (`tool/lsp.ts`)

```
goToDefinition          | 정의 이동
findReferences          | 참조 찾기
hover                   | 타입/문서 정보
documentSymbol          | 파일 내 심볼 트리
workspaceSymbol         | 프로젝트 전체 심볼 검색
goToImplementation      | 구현 이동 (인터페이스 → 구현)
prepareCallHierarchy    | 호출 계층 준비
incomingCalls           | 호출자 트리
outgoingCalls           | 피호출자 트리
```

- 필수 파라미터: `operation`, `filePath`, `line`(1-based), `character`(1-based)
- workspaceSymbol만 `query` 추가
- 응답: `{title, metadata: {result[]}, output: JSON | "검색 결과 없음"}`

### 2.4 LSP 사용 — **두 모드** 동시 운영

#### 모드 A: edit.ts 자동 호출 (push 모델)

`tool/edit.ts`의 `execute` 마지막 부분:

```typescript
yield* lsp.touchFile(filePath, "document")
const diagnostics = yield* lsp.diagnostics()
LSP.Diagnostic.report(filePath, diagnostics...)
// 출력에 "LSP errors detected" 메시지 자동 첨부
```

→ **AI가 파일을 수정한 직후, 자기 응답에 LSP 진단 결과가 자동으로 따라붙음**.
AI는 별도 호출 없이 자기 실수(타입 에러, lint, syntax)를 즉시 인지하고 수정 가능.

#### 모드 B: tool/lsp.ts 명시적 호출 (pull 모델)

AI가 필요 시 능동적으로 호출:
- caller 추적이 필요할 때 → `findReferences`
- 정의 위치 확인이 필요할 때 → `goToDefinition`
- 인터페이스 구현체 탐색 → `goToImplementation`
- 콜 그래프 탐색 → `incomingCalls` / `outgoingCalls`

### 2.5 ast-grep 통합 여부

- **OpenCode 코어에는 ast-grep 사용처 없음** (코드 그렙 결과)
- ast-grep은 별도 Claude Code plugin marketplace의 skill로 제공
- 즉 사용자가 "OpenCode = LSP + ast-grep" 으로 인식했던 자료는 **plugin/skill 기준**이지 OpenCode 본체의 핵심 기능이 아님

---

## 3. Agent Factory와 비교

### 3.1 Agent Factory의 두 진단/구조 경로 (실측)

Agent Factory는 OpenCode와 1:1 대응이 아니라 **두 개의 분리된 경로**를 운영한다:

#### 경로 A: review_bundle (구조 정보, reviewer용)

`core/review_bundle.py:86-117`의 실제 출력 형식:

```
# review_bundle (engine=ast)

## core/researcher.py
- L526 `subprocess_usage`: `subprocess.run`
- L631 `shell_true`: `shell=True`

## core/research_router.py
_(no risks detected)_
```

`build()` 반환 schema:
```python
{
  "engine": "ast" | "grep",
  "files": [
    {"path": "core/...", "risks": [{"line": int, "risk_id": str, "text": str}]}
  ]
}
```

`_RISK_PATTERNS` 7종 정규식만 추출 (subprocess_usage / shell_true / shlex_split / os_system / eval_usage / exec_usage / dynamic_import). caller·test·diff 등 § 섹션은 코드에 없음.

트리거: `scripts/hook_runner.py:148-156` `_post_edit_enqueue` → `subprocess` 로 `build_review_bundle.py` 호출.
소비자: af-critic / af-cross-review 진입 시 `.af_review_queue/review_bundle.md` 읽음.

#### 경로 B: LSPCheckHook (진단 정보, 메인 에이전트용, 휴면 상태)

`core/hooks/lsp_check.py:151-213`에 OpenCode 모드 A와 거의 동일한 구현 존재:

```python
class LSPCheckHook(ContinuationHook):
    PRIORITY = 8
    def post_tool_call(self, agent_state, tool_name, result):
        if not _is_enabled():  # AGENT_LSP_CHECK=1 게이트
            return result
        if tool_name not in _WRITE_TOOLS:
            return result
        # ... pyright --outputjson <file> 실행
        result["lsp_diagnostics"] = diags
        result["lsp_summary"] = "..."
```

트리거: `_WRITE_TOOLS` 호출 직후 (`write_file`, `edit_file` 등). 실제 활성화는 `AGENT_LSP_CHECK=1` 환경변수 필요.
현재 상태: **휴면**. 환경변수 없으면 no-op.

### 3.2 OpenCode와 매핑표

| 개념 | OpenCode | Agent Factory |
|------|----------|---------------|
| Push 모델 — 진단 정보 | LSP `publishDiagnostics` (자동) | LSPCheckHook (휴면, env-gated) |
| Push 모델 — 구조 정보 | (없음) | review_bundle (활성) |
| 정보 흐름 트리거 | `edit` tool execute 끝 | `_WRITE_TOOLS` post_tool_call (LSPCheckHook) / PostToolUse hook (bundle) |
| 영속성 | LSP 서버 long-lived | hook 1회성 (LSPCheckHook 캐시는 pyright 경로만) |
| Pull 모델 도구 | 9개 LSP operation | Read/grep/Glob (Claude Code 기본) |
| 코어 분석 엔진 | LSP (14 서버) | ast-grep (review_bundle) + pyright (LSPCheckHook) |
| 대상 사용자 | 사용자 + AI | review_bundle = reviewer / LSPCheckHook = 메인 에이전트 |

### 3.3 핵심 인사이트 (정정)

**LSPCheckHook은 OpenCode 모드 A와 같은 패턴이 이미 구현된 코드**다 (`core/hooks/lsp_check.py:151`, 2026-04-09 작성).

다른 점:
- OpenCode: edit tool 안에 hardcoded, 항상 활성
- Agent Factory: hook bus의 한 hook으로 분리, `AGENT_LSP_CHECK=1` 게이트

**review_bundle**은 OpenCode 모드 A의 "정보 종류"와는 상보적 (구조 vs 진단).
**review_bundle은 OpenCode 모드 A의 "구조 정보 사전 주입"과는 동일 패턴이지만, 정보 종류가 다르므로 직접 매칭이 아니라 별도 카테고리**.

세 가지가 각자 자기 일을 한다:
1. review_bundle: reviewer에게 위험 패턴 사전 주입 (활성)
2. LSPCheckHook: 메인 에이전트에게 타입 진단 사전 주입 (휴면)
3. (없음): reviewer에게 진단 사전 주입 — 이게 진짜 갭

### 3.4 진짜 갭

reviewer agent (af-critic / af-cross-review)가 받는 컨텍스트는 review_bundle.md (위험 패턴 7종)뿐.
LSPCheckHook은 **메인 에이전트 (사용자 대화하는 Claude)** 의 tool 결과에 진단을 첨부하지만, **reviewer subagent가 호출되는 시점에는 hook이 발화하지 않음** (subagent는 별도 컨텍스트).

따라서 OpenCode와 비교한 실제 갭:
- OpenCode: 한 AI가 편집 + 진단 동시 수신
- AF: 메인 AI = 편집 + (휴면) LSPCheckHook 진단 / reviewer AI = review_bundle만 (진단 없음)

---

## 4. 잘못 이해되었던 점

조사 과정에서 추정으로 진술했던 내용 중 코드 확인으로 정정된 사항:

| 추정 | 사실 |
|------|------|
| "OpenCode의 LSP tool은 실험적 단계" | dev 브랜치에 `tool/lsp.ts`로 정식 노출. 9개 operation. |
| "OpenCode는 LSP를 진단 피드용으로만 사용" | 두 모드 모두 활용 (자동 진단 + 명시적 caller/definition 등) |
| "AI가 능동적으로 LSP 호출하는 패턴은 정착 안 됨" | edit.ts 모드 A + tool/lsp.ts 모드 B 둘 다 정식 운영 |

`OPENCODE_EXPERIMENTAL_LSP_TOOL` 플래그는 일부 서브 기능이거나 과거 명칭일 가능성 — 현재 dev 브랜치에서는 LSP tool이 기본 노출.

---

## 5. 후속 작업 후보

본 문서는 분석에 한정한다. 구체 구현 권고는 별도 plan 문서에서 다룬다.
다만 분석 과정에서 드러난 후속 작업 후보 3개를 기록한다.

### 5.1 LSPCheckHook 활성화/통합 진단 (별도 트랙)

확인 필요한 항목:
- `AGENT_LSP_CHECK` 가 어떤 환경에서 켜지는가? (현재 settings.local.json / .env에 없으면 항상 no-op)
- LSPCheckHook이 `core/hooks/event_bus.py` 또는 `agent_runner.py`에 등록되어 있는가?
- 메인 에이전트(사용자와 대화하는 Claude)가 진단을 실제로 받고 있는가?
- pyright가 PATH에 있는가? frozen build에서는?

활성화 결정은 위 4가지 확인 후 별도 plan에서 진행.

### 5.2 reviewer에게도 진단 정보 주입 (별도 트랙)

§3.4에서 확인한 진짜 갭. 옵션:
- review_bundle 생성 시 pyright/ruff도 호출해 추가 섹션 (LSPCheckHook과 중복 검토 필요)
- 또는 hook chain 재구성으로 LSPCheckHook 결과를 reviewer subagent에 전파

이 결정은 §5.1 진단 결과 + 1주 메트릭 수집 데이터(`review_metrics.jsonl`) 본 후.

### 5.3 모드 B (명시적 LSP tool) — 보류

OpenCode가 노출하는 9개 LSP operation을 우리 reviewer에게 직접 노출하는 것은 우선순위 낮음:
- reviewer는 Claude Code 자체 = 이미 grep/Read/Glob 풍부
- 별도 LSP tool 추가해도 reviewer가 그걸 우선 쓸 architectural reason 약함
- LSP 영속 데몬 lifecycle 관리 비용이 큼

frozen build에서 외부 LSP 서버 동봉도 architectural mismatch.

---

## 6. 데이터 출처

- `https://github.com/sst/opencode/blob/dev/packages/opencode/src/lsp/server.ts`
- `https://github.com/sst/opencode/blob/dev/packages/opencode/src/lsp/lsp.ts`
- `https://github.com/sst/opencode/blob/dev/packages/opencode/src/tool/lsp.ts`
- `https://github.com/sst/opencode/blob/dev/packages/opencode/src/tool/lsp.txt`
- `https://github.com/sst/opencode/blob/dev/packages/opencode/src/tool/edit.ts`
- `https://opencode.ai/docs/lsp/`
- `https://opencode.ai/docs/tools/`
- `https://deepwiki.com/sst/opencode/5.4-language-server-integration`

---

## 7. 결론 요약

OpenCode 코어는 **LSP를 push(자동 진단) + pull(명시적 9개 operation) 두 모드로 동시 운영**.
ast-grep은 OpenCode 본체에 없음.

Agent Factory에는 OpenCode 모드 A 등가 구현 (`core/hooks/lsp_check.py`)이 **이미 존재**한다.
다만 `AGENT_LSP_CHECK=1` 환경변수 게이트로 휴면 상태이며, hook bus 등록·메인 에이전트 컨텍스트 통합 여부도 확인되지 않음.

별개로 운영 중인 `core/review_bundle.py`는 위험 패턴 7종 정규식 추출만 수행 (caller·test·diff 섹션 없음).
이는 reviewer 전용 사전 주입이며 OpenCode와 정보 종류가 다름 (구조 vs 진단).

진짜 갭은 **reviewer subagent가 진단 정보를 받지 못한다**는 점. 메인 에이전트의 LSPCheckHook 결과는 subagent로 전파되지 않음.

후속 작업은 본 문서가 아닌 별도 plan에서 다룬다 (§5).

## 8. 변경 이력

- 2026-05-02 초안: WebFetch + DeepWiki 조사 결과 기반 작성
- 2026-05-02 정정 (cross-review BLOCK 후): §3.1 review_bundle 실제 구조 반영, §3.3 "본질적으로 같은 패턴" 표현 정정, §3.4 진짜 갭 신설, `core/hooks/lsp_check.py` 발견 반영, §5 권고 → 후속 작업 후보로 톤 다운, §7 결론 정정. 잘못된 "review_bundle §8 추가" 권고 제거.
