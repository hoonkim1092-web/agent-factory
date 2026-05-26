# Code Review: dogfood

> Source: core/dogfood.py
> Date: 2026-05-26 17:54
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

근거: Critical 없음. Cross의 ACCEPT 2건(actual_changed 누락, plan_allowlist 드리프트)은 dogfood 정확성에 영향을 주는 Medium 결함이고, Critic의 Finding 2/3은 정책·테스트 갭으로 documented risk 수준. Block 사유 부재.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [Medium] `_run_implement_phase().actual_changed`가 untracked 파일을 누락
- **Critic**: not flagged
- **Cross**: `git diff <pre>..HEAD` + `git diff HEAD`만 본다. 신규 파일이 빠진다.
- **Judgment**: 코드 증거 명확. `finalize_dogfood_result()`는 `core/dogfood.py:599`에서 `git ls-files --others --exclude-standard`로 untracked를 별도 수집하지만 IMPLEMENT 텔레메트리는 동일 처리가 없음. dogfood가 가장 흔히 만드는 산출물(신규 파일) 경로가 actual_changed에서 과소 보고됨.
- **Action Required**: `_run_implement_phase()`에 `git ls-files --others --exclude-standard` 결과 union. 회귀 테스트(executor가 untracked 생성 → actual_changed 포함) 추가.

#### 2. [ACCEPT] [Medium] `plan_allowlist`가 빈집합이 되면 dirty 전체 staging 폴백
- **Critic**: not flagged
- **Cross**: artifacts + tests_required만으로 allowlist 구성. Triad 아키텍트가 step.target만 채우면 allowlist=∅ → fallback이 전부 stage.
- **Judgment**: `core/planner.py:31`에서 `target`이 일급 필드이고 `_build_ai_task()`도 target을 인정하는데 finalize만 무시 → 실재 스키마 드리프트. scope 위반 게이트가 무력화될 수 있음.
- **Action Required**: step.target이 파일 경로일 때 allowlist에 포함 + `result.final_plan` 쓰기 전 `artifacts/tests_required/target` 중 최소 1개 보장 검증.

#### 3. [ACCEPT] [Medium] dogfood FINALIZE가 review-gate를 영구 자동 우회 — 정책 행위 변화 미문서화
- **Critic**: `AF_SKIP_REVIEW_GATE=1`을 모든 dogfood 자동 commit에 박는다. CLAUDE.md는 "긴급·부트스트랩"만 허용.
- **Cross**: not flagged
- **Judgment**: dogfood worktree는 격리되므로 main 오염 위험은 낮으나, **자동 파이프라인이 게이트를 우회하는 첫 사례**. `scripts/review_gate.py:298-300`에서 `[gate-skipped-env]` 로깅으로 감사 추적은 유지(positive). 다만 정책 근거가 ADR/Blueprint에 없음.
- **Action Required**: (a) commit 메시지에 `[dogfood-auto, gate-skipped]` 마커 추가, (b) `docs/decisions/ADR-*.md`에 "FINALIZE는 격리 worktree + dogfood 자체가 검증 대상이므로 게이트 우회" 한 줄 근거 추가.

#### 4. [ACCEPT] [Medium] 우회 동작에 대한 테스트 갭
- **Critic**: `tests/test_dogfood_isolation.py`에 `extra_env`/`AF_SKIP_REVIEW_GATE` assertion 0건. `.githooks/pre-commit` 미설치 fixture에서 우연히 PASS.
- **Cross**: not flagged (다른 갭은 지적했으나 이 경로는 미언급)
- **Judgment**: 코드 증거(검색 결과)로 갭 실재 확인. 회귀 보호 약함.
- **Action Required**: `subprocess.run` monkeypatch로 `env["AF_SKIP_REVIEW_GATE"] == "1"` 직접 assert하는 단위 테스트 추가. 또는 강제 실패 hook을 임시 설치한 통합 테스트.

#### 5. [HOLD] [Low] `extra_env` 머지 우선순위가 locale 키를 silently override 가능
- **Critic**: 현재 호출자는 안전하나 시그니처가 locale 보호를 강제하지 않음.
- **Cross**: not flagged
- **Judgment**: 가설적 위험. 현재 유일 호출자는 `{"AF_SKIP_REVIEW_GATE": "1"}`만 전달. YAGNI 관점에서 보호 추가는 정당화 어려움.
- **Question for Author**: `extra_env` 사용처 확장 계획이 있는가? 1개로 유지될 거면 보호는 over-engineering.

### REJECTED (cross-review가 자체 철회)

- **Source-drift f-string 깨짐 우려**: cross가 직접 바이트 재확인 후 철회. py_compile PASS, 165 tests PASS. 무시.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | actual_changed가 untracked 누락 | Medium | ACCEPT | Cross |
| 2 | plan_allowlist 빈집합 → 전체 staging | Medium | ACCEPT | Cross |
| 3 | review-gate 자동 우회 미문서화 | Medium | ACCEPT | Critic |
| 4 | extra_env 전파 테스트 갭 | Medium | ACCEPT | Critic |
| 5 | extra_env locale override 위험 | Low | HOLD | Critic |

### Recommendations

1. **#1, #2 우선 수정** — dogfood 자체의 정확성/scope 게이트 무력화 위험. 단일 PR로 묶어 회귀 테스트 동봉.
2. **#3 ADR 작성** — `docs/decisions/ADR-YYYYMMDD-HHMMSS-dogfood-finalize-gate-bypass.md`에 정책 근거 1줄. commit 메시지 마커도 같은 PR에서 추가.
3. **#4 테스트** — monkeypatch 기반 단위 테스트가 비용 대비 가장 명확. `.githooks` 통합 테스트는 Windows fixture 비용 큼.
4. **#5 보류** — `extra_env` 호출자 확장 시점에 화이트리스트 가드 검토.
5. **T3 Advisory 채택** — Critic이 t3_required=yes 표시. Hook/gate/policy 영역이므로 본 머지 전 af-cross-review 1회 fan-out 권장.