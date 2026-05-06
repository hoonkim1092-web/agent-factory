# Design Review: 2026-05-02-opencode-lsp-architecture-analysis

> Source: docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md
> Date: 2026-05-02 20:28
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

Critic이 §5.1 채택 결정문 자체에 3건의 Critical(베이스라인 가짜 §1~§7, §5.1↔§5.3 자기모순, timeout 산수)을 제기했고, Cross도 외부 provider 경로·LSPCheckHook 활성화 매트릭스·메트릭 필드 부재를 ACCEPT로 굳혔다. 분석 부분은 견고하지만 §5(채택 평가)는 구현 진입 즉시 깨지는 결함을 포함하므로 v2 수정 후 재발화.

### Aggregated Findings (9 total)

#### 1. [ACCEPT] [Critical] §5.1 다이어그램의 "§1~§7"은 실제 review_bundle.md에 존재하지 않음
- **Critic**: `core/review_bundle.py:107-117` save() 출력은 헤더 + per-file `## <path>` 블록 + risk 라인뿐. `§1·§2·…·§7` 번호 섹션은 없음. §3.1은 정확히 인정하면서 §5.1 채택 제안은 동일 결함을 잔존시킴 (이전 라운드 §2.1 BLOCK과 동형).
- **Cross**: not flagged
- **Judgment**: Critic 단독이지만 `core/review_bundle.py:86-117` 직접 인용 + 본문 §3.1과의 자기모순으로 강한 증거. ACCEPT.
- **Action Required**: §5.1 다이어그램을 실제 per-file 레이아웃으로 재작성. 예: `## core/foo.py` 블록 안 `### Static Diagnostics` 서브섹션 vs 파일 목록 끝 글로벌 진단 섹션 — 둘 중 하나 명시. "§8" 명칭 폐기.

#### 2. [ACCEPT] [Critical] §5.1(pyright 채택)과 §5.3(LSP 폐기 사유)의 자기 모순
- **Critic**: §5.3은 LSP 폐기 핵심 근거로 pyright의 cross-platform 동봉 비용·사용자 부담을 인용. §5.1은 같은 pyright를 채택. pyright는 Node 런타임 + npm 패키지 필요 → frozen `af.exe`에 동봉 불가, 사용자가 `npm install -g pyright` 별도 수행 — §5.3이 거부한 "사용자 부담" 자체.
- **Cross**: not flagged
- **Judgment**: 문서 §5.1 vs §5.3 직접 충돌, 반박 불가. ACCEPT.
- **Action Required**: 둘 중 택1 — (a) pyright 의존성 부담 명시 수용 + §5.3 모순 문장 수정, (b) §5.1을 stdlib·기존 자산만으로 좁히고 pyright는 옵션 게이트(`AF_REVIEW_LSP=1`)로 격하.

#### 3. [ACCEPT] [Critical] hook_runner.py timeout=10s 안에 pyright 다중 파일 못 돌림
- **Critic**: `scripts/hook_runner.py:152-155` `subprocess.run([..., bundle_script, root], timeout=10)` vs `core/hooks/lsp_check.py:40` `_PYRIGHT_TIMEOUT=15` (파일 1개 기준, cold-start 포함). 변경 파일 1개여도 timeout 위반 위험, 다파일이면 확정 실패. 문서가 인용·해소 안 함.
- **Cross**: not flagged
- **Judgment**: 두 코드 라인 직접 인용으로 산수 검증 가능. 강한 증거. ACCEPT.
- **Action Required**: §5.1 본문에 (a) `_post_edit_enqueue` timeout 상한 결정(커밋 레이턴시 영향 포함), (b) 진단을 background로 분리 시 race 정책 — 둘 중 하나 명시.

#### 4. [ACCEPT] [High] LSPCheckHook 자산 공유 무명세 + 활성화 매트릭스 부재
- **Critic**: §3.1은 `_find_pyright()` 캐시(L51), `_run_pyright()` JSON 파싱(L103), `_validate_file_path()` 가드(L88) 존재를 인정하면서도 §5.1이 build_review_bundle.py의 재사용/재구현 결정을 미룸 → 평행 구현 위험.
- **Cross**: `core/agent_runner.py:963-974`에서 HookEventBus 생성 + LSPCheckHook 등록. `.claude/settings.local.json:208-225` Claude Code PostToolUse는 별도 경로(post_edit_code_review/post_edit_design_review)로 HookEventBus 미통과. 즉 등록 여부보다 "어떤 실행 경로가 HookEventBus를 통과하는가"가 진짜 미확인.
- **Judgment**: 두 리뷰가 같은 영역의 다른 측면을 짚음(자산 공유 + 활성화 경로). 병합. ACCEPT.
- **Action Required**: §5.1에 (a) `build_review_bundle.py`가 `core.hooks.lsp_check`의 `_find_pyright`/`_run_pyright`를 import 재사용하고 게이트는 `AF_REVIEW_LSP`로 분리한다는 명시, (b) activation matrix 추가 — `AgentRunner 내부 = registered+env-gated` / `Claude Code native PostToolUse = HookEventBus 미통과` / `reviewer/external provider = no propagation`.

#### 5. [ACCEPT] [High] §5.1 ruff 통합 계획 0줄
- **Critic**: ruff는 §5.1에서 처음 등장 후 무언급. 설치 경로(전역? `pyproject.toml`?), 설정 우선순위, 출력 schema(JSON?), 실패 폴백, frozen 동봉 — 전부 미정. pyright와 달리 LSPCheckHook precedent 없음.
- **Cross**: not flagged
- **Judgment**: Critic 단독이나 본문 단어 카운트로 검증 가능. ACCEPT.
- **Action Required**: ruff를 §5.1에서 빼거나, 별도 단락에 `ruff --output-format=json` + 프로젝트 루트 `ruff.toml` 우선 등 최소 사양 추가.

#### 6. [ACCEPT] [High] 사이드카 파일 분리(80% 솔루션) 미검토
- **Critic**: 가장 작은 패치는 review_bundle.md schema 무변경 + `.af_review_queue/lsp_diagnostics.json` 사이드카로 reviewer 프롬프트에서 같이 읽기. schema 변경 없음 → save/load 호출자 영향 없음 → 롤백 1줄. §5.1은 이 옵션 검토 없이 schema 확장으로 직행.
- **Cross**: not flagged
- **Judgment**: 설계 단계에서 trade-off 비교 누락은 명백한 결함. ACCEPT.
- **Action Required**: §5.1에 alt-A(사이드카 분리) vs alt-B(schema 확장) 두 옵션 trade-off 제시 후 결정.

#### 7. [ACCEPT] [High] "1주 메트릭 수집 후 결정"에 필요한 측정 필드 부재
- **Critic**: not flagged
- **Cross**: `scripts/review_metrics_logger.py:144-168` `append_metric()`은 `agent`, `tier`, `verdict`, `findings_count`, `extension_log_count`, `duration_ms`, `tokens`, `tool_calls`만 저장. bundle 존재/stale, diagnostics_count, pyright/ruff status, provider 미기록 → 효과 판단 불가.
- **Judgment**: Cross 단독이나 코드 라인 직접 인용으로 강한 증거. ACCEPT.
- **Action Required**: §5.2에 측정 계약 추가 — 최소 필드: `bundle_present`, `bundle_stale`, `provider_id`, `diagnostics_tool`, `diagnostics_status`, `diagnostics_count`, `diagnostics_elapsed_ms`, `blocking_findings_from_diagnostics`.

#### 8. [ACCEPT] [High] af-cross-review 외부 provider 경로는 review_bundle.md 미수신
- **Critic**: not flagged
- **Cross**: `.claude/agents/af-cross-review.md:120-160` Round 1 외부 provider 프롬프트는 `REVIEW_DOC_PLACEHOLDER`/`CHANGED_FILES_PLACEHOLDER`/`DIFF_CONTENT_PLACEHOLDER`만. bundle 정책은 `:316-341`에 별도. 즉 §3.1의 "소비자: af-critic / af-cross-review 진입 시 bundle 읽음" 진술이 외부 provider에는 거짓.
- **Judgment**: Cross 단독이나 agent 정의 파일 직접 인용. ACCEPT.
- **Action Required**: §3.1/§3.4에 consumer matrix 추가 — `af-critic`, `af-cross-review coordinator`, `codex_cli`, `gemini_cli fallback` 별 bundle 전달 여부 분리. 외부 provider에 bundle 주입 필요 시 `/tmp/af-review-prompt.txt`에 명시 삽입 정책 결정.

#### 9. [ACCEPT] [Medium] frozen build에서 build_review_bundle.py 호출 경로 무명세
- **Critic**: `scripts/build_review_bundle.py:71-72`는 `sys.path.insert(0, workspace); from core import review_bundle`로 워크스페이스에 core/ 소스 풀려 있어야 작동. frozen `af.exe`에서 호출 시점·동작 미명세.
- **Cross**: REJECT — "현재 문서는 구현 추가 안 함, 기존 모듈은 `af.spec:40` `core.review_bundle` + `:154` `core.hooks.lsp_check`로 이미 포함됨, 신규 모듈 추가 시점에만 spec 명시하면 됨".
- **Judgment**: Cross의 REJECT는 "신규 모듈 추가 시"에만 spec 의무를 거는 좁은 논리. Critic은 "frozen 환경에서 build_review_bundle.py 자체가 어떻게 호출되는가"를 묻는 다른 층위 — 한 줄 명시(예: "frozen에서는 no-op")로 해소 가능. Medium 유지하여 ACCEPT.
- **Action Required**: §5.1 끝에 한 줄 — "frozen build 경로: hook_runner.py가 `bundle_script` 호출을 source 체크아웃 환경에서만 수행. frozen에서는 no-op".

#### 10. [REJECT] [Medium] §2.4 "150ms debounce" 수치 출처 부정확
- **Source**: Critic
- **Original Finding**: deepwiki는 LLM-요약 출처라 정확도 보증 불가. "150ms" 같은 정확 수치는 OpenCode 원본 line 인용이 더 적절.
- **Rejection Reason**: 본 문서는 분석문서이고, 채택 결정 §5에 "150ms" 수치가 영향을 주지 않음. 분석 신뢰성 향상은 advisory. 정확도 개선 권고는 v2 수정 시 같이 처리하면 충분 — BLOCK 사유 아님.

#### 11. [REJECT] [Low] core/file_io.write_text() 재사용 권고
- **Source**: Cross (자기 REJECT)
- **Original Finding**: 후속 구현에서 bundle/diagnostics 저장 시 `core/file_io.py` 유틸 재사용 권고.
- **Rejection Reason**: Cross 본인이 REJECT — `core/file_io.write_text()`는 직접 쓰기, review queue는 동시 reader 있어 `scripts/review_gate.py:92-100` `tempfile.mkstemp()` + `os.replace()` atomic 패턴이 더 적합. 본 문서 BLOCK 사유 아님(후속 plan 사항).

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §5.1 §1~§7 가짜 베이스라인 | Critical | ACCEPT | Critic |
| 2 | §5.1↔§5.3 pyright 자기모순 | Critical | ACCEPT | Critic |
| 3 | hook_runner timeout=10s 산수 | Critical | ACCEPT | Critic |
| 4 | LSPCheckHook 자산공유+활성화 매트릭스 | High | ACCEPT | Both |
| 5 | §5.1 ruff 통합 0줄 | High | ACCEPT | Critic |
| 6 | 사이드카 alt 미검토 | High | ACCEPT | Critic |
| 7 | 메트릭 필드 부재 | High | ACCEPT | Cross |
| 8 | 외부 provider bundle 미수신 | High | ACCEPT | Cross |
| 9 | frozen build 호출경로 무명세 | Medium | ACCEPT | Critic |
| 10 | 150ms 출처 정확도 | Medium | REJECT | Critic |
| 11 | file_io 재사용 권고 | Low | REJECT | Cross |

### Recommendations

구현 진입 전 §5를 다음 순서로 v2 수정:

1. **§5.1을 채택 결정문에서 "추가 검토 옵션"으로 격하**하거나, Critical #1·#2·#3을 본문에 흡수해 다이어그램·모순·timeout 산수를 동시에 정리.
2. **다이어그램을 실제 per-file 레이아웃으로 재작성** — `## <path>` 블록 안 `### Static Diagnostics` 서브섹션 vs 글로벌 진단 섹션 중 택1, "§8" 명칭 폐기.
3. **pyright 채택 사유 vs §5.3 폐기 사유 정합** — frozen 동봉 부담 명시 수용 또는 옵션 게이트(`AF_REVIEW_LSP=1`)로 격하.
4. **timeout 정책 결정** — `_post_edit_enqueue` 상한을 어디까지 올릴지, 또는 background 분리 시 race 정책.
5. **자산 공유 명시** — `build_review_bundle.py`가 `core.hooks.lsp_check`의 `_find_pyright`/`_run_pyright` import 재사용, 게이트 분리(`AF_REVIEW_LSP`).
6. **activation matrix 추가** — AgentRunner 내부 / Claude Code PostToolUse / reviewer 외부 provider 별 hook propagation 매트릭스.
7. **consumer matrix 추가** — af-critic / af-cross-review coordinator / codex_cli / gemini_cli 별 bundle 전달 여부.
8. **alt-A(사이드카) vs alt-B(schema) trade-off 결정** — 80% 솔루션 비교 후 채택.
9. **§5.2 측정 계약** — `bundle_present`, `bundle_stale`, `provider_id`, `diagnostics_tool/status/count/elapsed_ms`, `blocking_findings_from_diagnostics` 필드 명시.
10. **ruff 최소 사양** — `--output-format=json` + `ruff.toml` 우선 등 한 단락 추가, 또는 §5.1에서 제거.
11. **frozen build no-op 한 줄 명시**.