# Design Review: 2026-05-02-opencode-lsp-architecture-analysis

> Source: docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md
> Date: 2026-05-02 16:24
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

문서 §3.1·§3.3·§5.1의 핵심 비교 baseline이 실제 코드와 어긋나 있고(2개 Critical), 권고의 운영 파라미터가 0개여서 채택 가부 판정 자체가 불가. 본 분석은 baseline 정정 + 권고 분리 후 재제출 필요.

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Critical] §3.1의 review_bundle 구조가 실제 코드와 불일치 — 비교의 기반이 허구
- **Critic**: §3.1 박스의 `§1 Pending Files / §2 Git Diff / §4 Related Tests / §5 Direct Callers` 섹션은 `core/review_bundle.py:107-117 save()`에 존재하지 않음. risk 라인만 출력.
- **Cross**: 동일. `build()`/`save()`는 `engine` + per-file risk bullets만 emit (`core/review_bundle.py:86,102`).
- **Judgment**: 두 reviewer 모두 같은 코드 라인을 근거로 일치. baseline이 허구라면 §5.1 "§8 추가" 권고 자체가 잘못된 baseline 위에 얹어진 것.
- **Action Required**: §3.1을 실제 출력 포맷(헤더 + `## {path}` + risk 라인)으로 재작성. 결론을 "§8 추가"가 아닌 "현재 bundle은 risk만 담고 있어 callers/tests/diagnostics 전체를 함께 설계해야 한다"로 확장. 실제 `.af_review_queue/review_bundle.md` 샘플 첨부.

#### 2. [ACCEPT] [Critical] §3.3 "본질적으로 같은 패턴" 주장이 실행 모델 차이를 은폐
- **Critic**: OpenCode 모드 A는 **편집한 같은 AI가 같은 turn 안에서** diagnostics를 받는 self-feedback (`tool/edit.ts execute` 끝). Agent Factory의 review_bundle은 **다른 reviewer 에이전트가 별도 세션에서** 읽는 hand-off. pyright 결과를 bundle에 넣어도 **편집한 에이전트는 보지 못한다**.
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 `tool/edit.ts:412-420` (yield* lsp.diagnostics)와 Agent Factory의 PostToolUse → 후속 reviewer 흐름 비교가 강력. 이 차이는 §5.1의 ROI 평가를 뒤집는다(reviewer는 이미 자기 도구로 pyright 실행 가능).
- **Action Required**: §3.3을 "트리거 시점은 비슷하나 정보 소비자가 다름(self-correction vs hand-off)"으로 정정. §5.1 ROI를 "진단 비용 1회 선결제 캐시" 수준으로 축소.

#### 3. [ACCEPT] [High] §5.1 권고의 운영 파라미터가 0개 — feasibility 판정 불가
- **Critic**: 실행시점/범위/포맷/실패처리/frozen build 호환성/Multi-PC 6항목 미정의. pyright cold start 3-5s × hook 트리거 = latency 5배+.
- **Cross**: 명령 invocation/JSON shape/severity mapping/line numbering(0-vs-1 based)/timeout/missing-tool 동작 미정. `LSPCheckHook._run_pyright()`는 미설치/timeout/parse fail/no-diagnostics 모두 `[]` 반환 (`core/hooks/lsp_check.py:103`) — "clean"과 "not run" 구분 불가.
- **Judgment**: 두 reviewer가 별도 측면(비용 vs 계약)에서 동일 결론 도달.
- **Action Required**: 정규화 계약 정의 — `{tool, status: ok|skipped|error|timeout, elapsed_ms, diagnostics:[{path,line,character,severity,code,message}]}`, 1-based line/character. tool 실패를 bundle에 보존. 권고를 별도 설계문서(`docs/2026-05-02-static-diagnostics-bundle-recommendation.md`)로 분리해 6항목 결정 후 재리뷰.

#### 4. [ACCEPT] [High] PostToolUse hook 파이프라인이 실제로 wired 되어 있지 않음
- **Critic**: not flagged
- **Cross**: `.claude/settings.local.json:207` 및 template은 `post_edit_code_review` + `post_edit_design_review`만 wire. `post_edit_enqueue`는 `scripts/hook_runner.py:132`에만 존재 — 문서가 전제하는 "PostToolUse → enqueue → build_review_bundle.py" 흐름이 현재 동작하지 않음.
- **Judgment**: Cross 단독이지만 settings 파일 라인 직접 인용으로 검증 가능. 문서가 분석하는 baseline이 사실상 미작동 상태라는 추가 결함.
- **Action Required**: settings에 `post_edit_enqueue` 추가 또는 `post_edit_code_review`에 bundle 생성 합치기. Write/Edit 이벤트가 `.af_review_queue/review_bundle.md`를 갱신하는지 검증하는 hook wiring 테스트 추가.

#### 5. [ACCEPT] [High] §4 자체 모순 + §2.5 ast-grep 부재 검증 불가
- **Critic**: line 6 "WebFetch로 직접 확인"과 §4 "OPENCODE_EXPERIMENTAL_LSP_TOOL은 ... 가능성" hedging 충돌. §2.5 "ast-grep 사용처 없음"은 grep 명령·검색 경로 미첨부 → `node_modules`/plugin 디렉토리 포함 여부 미상.
- **Cross**: not flagged
- **Judgment**: Critic 단독. 신뢰도와 재현성 두 측면 모두 타격 — "직접 봤다"와 "모르겠다"가 같은 문서에 공존하면 다른 결론도 의심받음.
- **Action Required**: (a) 코드/PR 검색으로 플래그 직접 확인 → §2 통합, hedging 제거. (b) ast-grep 부재 검증의 grep 명령 + 검색 경로 명기.

#### 6. [ACCEPT] [Medium] §6 출처 URL이 mutable target — 재현 불가
- **Critic**: `dev` 브랜치 URL 8개. force-push 가능, 라인 번호 변동.
- **Cross**: not flagged
- **Judgment**: 분석문서로서의 신뢰성 표준 결함. 인용 스니펫(`yield* lsp.touchFile(...)`)의 출처 commit 추적 불가.
- **Action Required**: 모든 URL을 `/blob/{sha}/...` 형식으로 pin, 인용 라인 범위(`tool/edit.ts#L412-L420`) 명기.

#### 7. [ACCEPT] [Medium] §3.2 매핑표가 능력 비대칭을 은폐
- **Critic**: "Pull 모델 도구: 9개 LSP operation | Read/grep/Glob"는 semantic operation(goToDefinition, callHierarchy)과 텍스트 기반 도구를 등가 매핑. §5.2 "별도 LSP tool 추가 architectural reason 약함" 결론을 부당히 강화.
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 표 자체가 evidence — semantic vs textual을 한 셀에 묶은 것 명백.
- **Action Required**: 행을 semantic/textual 두 줄로 분리하거나 "능력 동등성: 부분/없음" 컬럼 추가.

#### 8. [HOLD] [Medium] reviewer가 "이미 grep/Read/Glob 풍부"라는 §5.2 전제의 적용 범위 미정
- **Critic**: not flagged (단, §3.3 비판이 부분적으로 같은 영역 건드림)
- **Cross**: af-critic/af-cross-review가 multi-provider(claude_cli/codex_cli/gemini_cli)에서 실행될 수 있는데 §5.2는 Claude Code reviewer 가정. 비-Claude reviewer는 이 전제가 깨질 수 있음.
- **Judgment**: 단일 reviewer 지적이지만 Agent Factory의 multi-provider 정책과 충돌 가능성 있음. 작성자가 권고 범위를 명시해야 결정 가능.
- **Question for Author**: §5.1·§5.2 권고는 (a) Claude Code reviewer만 대상인가, (b) 모든 provider reviewer 대상인가? (b)라면 codex_cli/gemini_cli reviewer가 grep/Read/Glob 보유 여부를 명시.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §3.1 review_bundle 구조 허구 | Critical | ACCEPT | Both |
| 2 | §3.3 self-feedback vs hand-off 은폐 | Critical | ACCEPT | Critic |
| 3 | §5.1 운영 파라미터/계약 미정 | High | ACCEPT | Both |
| 4 | PostToolUse hook 미연결 | High | ACCEPT | Cross |
| 5 | §4 자체 모순 + §2.5 검증 불가 | High | ACCEPT | Critic |
| 6 | §6 mutable URL | Medium | ACCEPT | Critic |
| 7 | §3.2 능력 비대칭 은폐 | Medium | ACCEPT | Critic |
| 8 | multi-provider reviewer 범위 | Medium | HOLD | Cross |

(Cross #5 "Full LSP 폐기"는 Cross 자체가 REJECT — `core/agent_runner.py:971`의 `LSPCheckHook` env-gated 사용이 OpenCode-style 풀과 다른 prior art임을 인정. 본 final review에서도 §5.3 "LSP 통째 통합 폐기" 결정은 유효로 본다.)

### Recommendations

구현 진입 전 다음 순서로 본 문서 정정:

1. **§3.1 재작성**: 실제 `review_bundle.md` 출력 샘플(`# review_bundle (engine=...)` + `## {path}` + risk 라인)로 baseline 고정. 현재 bundle이 risk만 담고 있다는 사실을 결론에 반영.
2. **§3.3 정정**: 정보 소비자가 self vs reviewer로 다름을 명시. §5.1 ROI를 "진단 캐시 선결제" 수준으로 재산정.
3. **권고 분리**: §5.1 본문을 별도 설계문서 `docs/2026-05-02-static-diagnostics-bundle-recommendation.md`로 이전. 본 분석문서(`docs/참고/`)는 §5를 한 줄("후속 설계 문서 참고")로 축소.
4. **새 설계문서에 6항목 결정**: 실행시점/범위/JSON 계약(1-based line, status 필드)/실패처리/frozen build 동봉 경로/Multi-PC 결정성. 정규화 계약: `{tool, status, elapsed_ms, diagnostics:[...]}`.
5. **Hook wiring 선결**: settings에 `post_edit_enqueue` 추가하고 Write/Edit → bundle 갱신 테스트 작성. 이게 안 되면 §8 추가 의미 없음.
6. **§4 hedging 제거**: `OPENCODE_EXPERIMENTAL_LSP_TOOL` 직접 검색 결과로 §2 갱신. §2.5 grep 명령·경로 §6에 명기.
7. **§6 URL pin**: 모든 출처를 commit SHA + 라인 범위로 교체.
8. **§3.2 표 보강**: semantic vs textual 분리 또는 능력 동등성 컬럼.
9. **§5.1·§5.2 권고 범위 명시**: Claude Code reviewer 한정 또는 multi-provider 전체 적용 — Agent Factory의 `provider_detect.py` 정책과 정합.

본 정정 완료 후 새 설계문서 단독으로 af-cross-review 재실행 권장.