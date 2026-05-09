# Design Review: 2026-05-02-static-diagnostics-bundle-recommendation

> Source: docs/2026-05-02-static-diagnostics-bundle-recommendation.md
> Date: 2026-05-02 16:31
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

§2.1 baseline 표가 실제 코드와 불일치하고, 기존 `core/hooks/lsp_check.py` 자산을 무시한 평행 통합 제안이라는 **2건의 Critical**이 양 리뷰어로부터 독립 확인되었다. 추가로 timeout 산수 모순·source_hash 부작용 등 구현 시점에서 즉시 실패할 결함이 다수.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] §2.1 baseline 표가 실제 review_bundle 출력과 불일치
- **Critic**: `core/review_bundle.py:86-99 build()` + `:102-117 save()` 실측 결과는 헤더+per-file 섹션+위험 라인뿐. §1·§2·§3·§4·§5·§7는 코드에 부재. `test_gap_analyzer`는 review_bundle에서 호출되지 않음(grep 검증).
- **Cross**: 현 schema는 `engine` + per-file `risks`만 반환. `StaticDiagnosticsSection` 자체가 미정의 타입.
- **Judgment**: 양 리뷰어가 동일 코드 라인을 인용하며 합치. 어제 동일 사유로 BLOCK된 분석 문서의 결함이 그대로 복제됨.
- **Action Required**: §2.1 표를 실제 출력 포맷으로 재작성. 실제 `.af_review_queue/review_bundle.md` 샘플 첨부. 결론도 "§8 단독 추가는 reviewer 기대 베이스라인을 만족시키지 못함"으로 수정.

#### 2. [ACCEPT] [Critical] 기존 `core/hooks/lsp_check.py` 무시한 평행 통합
- **Critic**: `core/hooks/lsp_check.py:46-77`이 `AGENT_LSP_CHECK=1` + `_find_pyright()` 캐시 + timeout=15 + MAX_DIAG=10으로 이미 pyright 통합 완료. `core/agent_runner.py:972-973`에 등록됨. 권고는 이를 일언반구 언급 없이 평행 호출 추가.
- **Cross**: `_find_pyright()`·`_run_pyright()` 헬퍼가 이미 존재. 공통 코드를 `core/static_diagnostics.py`로 추출하고 LSPCheckHook과 review_bundle이 공유해야.
- **Judgment**: 양쪽 모두 동일 파일·동일 함수를 지목. 중복 호출 시 timeout/필터 정책 충돌 불가피.
- **Action Required**: §3에 "기존 lsp_check.py와의 관계" 절 신설. 택1 — (a) hook을 bundle 단계로 이전, (b) bundle은 lsp_check가 기록한 결과를 읽는 thin reader, (c) `core/static_diagnostics.py`로 공통화. 어느 쪽이든 헬퍼·timeout·MAX_DIAG 재사용.

#### 3. [ACCEPT] [Critical] §4.1 pyright 시간 추정 비현실적, §3.3 timeout과 모순
- **Critic**: cold pyright는 본 코드베이스(175파일·46K LOC)에서 5~15초가 통상. `docs/code_review/code-review.md` M3가 이미 `_PYRIGHT_TIMEOUT=15`를 "에이전트 블로킹"으로 등재. §3.3 timeout=5s는 cold 호출에서 거의 매번 SIGTERM.
- **Cross**: 이 환경에서 pyright/ruff가 PATH에 부재. baseline 측정 없이 "1.5~2h 즉시 가능"은 판단 불가.
- **Judgment**: 양 리뷰어가 baseline 측정 부재를 지적. 추정치는 측정 후에야 신뢰 가능.
- **Action Required**: §9 결정 포인트(스모크 테스트)를 Stage 1보다 먼저 수행. 5개 파일 cold/warm pyright 실측·project-wide vs file-list 비교 후 §3.3 timeout과 §4.1 추정 재작성. cold start ≥5s 전제로 fallback("(timed out)") 명시.

#### 4. [ACCEPT] [High] hook outer timeout=10s와 §3.3 sequence 산수 충돌
- **Critic**: `scripts/hook_runner.py:152-155` `subprocess.run(..., timeout=10)`. pyright 5s + ruff 2s **순차** + 기존 작업 → 10s cap 초과 시 SIGKILL → bundle 통째로 사라짐. §3.2에 hook_runner.py 누락.
- **Cross**: not flagged
- **Judgment**: critic이 라인 인용·산수까지 제시. 도입 결과가 현 상태보다 악화된다는 구체적 시나리오.
- **Action Required**: §4.1에 timeout 분해표 추가. (a) hook_runner timeout 상향, (b) fire-and-forget 다음 라운드 흡수, (c) 변경 파일 수 N에 따른 동적 조정 중 택1. §3.2 변경 파일 표에 `scripts/hook_runner.py` 추가.

#### 5. [ACCEPT] [High] §3.4 source_hash에 도구 버전 포함 시 멀티-PC 캐시 무력화
- **Critic**: 멀티-PC 환경(git push/pull로 상태 이동)에서 PC별 pyright/ruff patch 버전 차이 → 같은 commit에서도 hash mismatch → 매 commit bundle 재생성. §6.2 측정 노이즈로 매장됨.
- **Cross**: not flagged
- **Judgment**: critic이 CLAUDE.md 세션 연속성 규칙과 결합한 부작용을 명시. 캐시 적중률 0%는 §6 측정 자체를 무력화.
- **Action Required**: source_hash에서 도구 버전 제외. §8 헤더 본문에만 기록. 또는 메이저·마이너만 hash 포함(patch 제외).

#### 6. [ACCEPT] [High] frozen build 가드의 dev/배포 격차
- **Critic**: §5.3 `sys._MEIPASS` 분기 시 frozen 사용자는 §8 영구 미수신. §6.2 측정도 dev에 한정 → §6.3 1주 데이터가 통계적으로 편향.
- **Cross**: REJECTED (af.spec hiddenimport 관점에서) — 다른 각도이므로 critic 지적과 별개
- **Judgment**: cross의 reject는 hiddenimport 한정. critic의 측정 갭/정책 분기 우려는 별도 유효 이슈.
- **Action Required**: frozen 정책 명시 — (a) frozen 사용자도 host pyright/ruff PATH 의존 요구(lsp_check.py 선례), (b) dev-only 명시 + frozen 측정 갭을 §6 disclosed limitation에 추가.

#### 7. [ACCEPT] [High] 도구 exit-code semantics 미정의
- **Critic**: not flagged
- **Cross**: pyright/ruff는 진단 발견 시 non-zero. 이를 "tool crash"와 구분 안 하면 유효 진단을 silently drop. `scripts/build_review_bundle.py:70`은 모든 예외를 generic error로 묶어 흘림.
- **Judgment**: cross가 코드 라인까지 인용. 명세 누락은 구현 시 즉시 사고 유발.
- **Action Required**: stdout JSON 파싱 성공 = success(return code 무관). `status=error`는 timeout/exec 부재/JSON invalid/launch failure에 한정. stderr는 capped `error_detail`에 보존.

#### 8. [ACCEPT] [High] CLI 인터페이스 설계 vs 실제 불일치
- **Critic**: not flagged
- **Cross**: 현 `scripts/build_review_bundle.py:86 main()`은 `sys.argv[1]`을 workspace로 처리. files는 `.af_review_queue/pending_agent_review.json`에서 로드. 권고의 `[files...]` 시그니처는 존재하지 않음.
- **Judgment**: cross가 라인까지 명시. 설계 단계 자체가 호출 시퀀스(§3.3) 그림과 다름.
- **Action Required**: `[workspace]` 인터페이스로 정정하거나 `argparse`로 `--workspace` + 옵션 file args 추가, 양 모드 테스트.

#### 9. [ACCEPT] [High] 메트릭 필드의 데이터 경로 부재
- **Critic**: not flagged
- **Cross**: `append_metric()`은 agent metadata + parsed agent response만 받음(`scripts/review_metrics_logger.py:144`). bundle을 읽지 않음. `_post_agent_record()`도 parsed content count만 전달(`scripts/hook_runner.py:358`).
- **Judgment**: cross가 라인 인용. §6.1 JSON 필드는 데이터 경로가 없으면 항상 null.
- **Action Required**: `append_metric()`에 `extra: dict|None` 추가 + `_post_agent_record()`가 `.af_review_queue/review_bundle.json` sidecar를 로드. `blocking_findings_in_diagnostics_only`는 reviewer가 진단 ID 태깅하거나 offline report로 분리.

#### 10. [ACCEPT] [Medium] §3.2 변경 파일 표 다수 누락 + 사실 오류
- **Critic**: 누락분 — `scripts/hook_runner.py`(timeout 조정), `pyrightconfig.json`(§5.2 본문엔 있으나 표 없음), `core/hooks/lsp_check.py`(중복 제거 시), 기존 `tests/test_build_review_bundle.py`, `Master_Blueprint.md` §3, `docs/code_review/code-review.md`. 사실 오류 — `requirements.txt`에 pyright/ruff "이미 있을 가능성 큼" 적었으나 grep 결과 둘 다 **없음**.
- **Cross**: not flagged (직접) — 다만 #4·#9에서 hook_runner / metrics_logger 변경 필요성을 별도 확인
- **Judgment**: critic이 grep 검증으로 사실 오류까지 입증.
- **Action Required**: §3.2 표 갱신. 각 파일 변경 종류(add/modify/test) 명시. requirements.txt 항목은 "추가 필요(현재 미수록 확인됨)"로 정정.

#### 11. [HOLD] [Medium] §6.3 성공 기준 — 1주 표본·노이즈 통제 부족
- **Critic**: 1주 측정 동안 commit 빈도·변경 종류·reviewer 호출 횟수 미통제. ≥10% 임계 통계 근거 없음. §2.2 인용 사례는 N=1.
- **Cross**: not flagged
- **Judgment**: critic 지적은 합리적이나 다른 Critical 해결 후 재평가가 효율적. 측정 설계는 Stage 2 시점에 다시 다듬어도 늦지 않음.
- **Question for Author**: baseline 1주(§8 없이) 수집을 Stage 2 전에 둘 의사가 있는가? BLOCK 카테고리별 분해(타입·lint·구조·로직)를 메트릭에 포함할 것인가?

#### 12. [HOLD] [Medium] "즉시 가능" vs §9 prerequisite 자기모순
- **Critic**: §9가 prerequisite 3건(pyright 스모크·ruff 설정·frozen 정책) 인정. 그런데 Stage 1을 prerequisite 충족 전 진행으로 표기.
- **Cross**: 현 환경에 pyright/ruff PATH 부재. baseline 결정 전 Stage 1 범위(둘 다 vs ruff-only vs skip) 미정.
- **Judgment**: 두 리뷰어 합치. Critical #3 해결과 함께 자연 해소되므로 별도 HOLD로 표시(중복 액션 회피).
- **Question for Author**: §9 prerequisite를 Stage 0(=baseline 측정)로 격상 후 Stage 1 진입할 것인가?

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §2.1 baseline 표 허구 | Critical | ACCEPT | Both |
| 2 | lsp_check.py 무시한 평행 통합 | Critical | ACCEPT | Both |
| 3 | pyright 시간 추정 비현실 + timeout 모순 | Critical | ACCEPT | Both |
| 4 | hook outer timeout=10s 산수 충돌 | High | ACCEPT | Critic |
| 5 | source_hash 도구 버전 → 멀티-PC 캐시 무력화 | High | ACCEPT | Critic |
| 6 | frozen 가드 dev/배포 격차 | High | ACCEPT | Critic |
| 7 | 도구 exit-code semantics 미정의 | High | ACCEPT | Cross |
| 8 | CLI 인터페이스 불일치 | High | ACCEPT | Cross |
| 9 | 메트릭 데이터 경로 부재 | High | ACCEPT | Cross |
| 10 | §3.2 변경 파일 표 누락 + 사실 오류 | Medium | ACCEPT | Critic |
| 11 | §6.3 성공 기준 표본·노이즈 | Medium | HOLD | Critic |
| 12 | "즉시 가능" vs prerequisite 자기모순 | Medium | HOLD | Both |

### Recommendations

구현 진입 전 다음을 순서대로 처리:

1. **Stage 0 신설 — baseline 측정** (Critical #3, #12 해결): 변경 파일 5개에 대해 cold/warm pyright 실측, project-wide vs file-list 호출 비교, ruff 설정 현황, requirements.txt 실제 상태(pyright/ruff 미수록 확인), 본 환경 PATH 가용성을 **숫자로** 기록.
2. **§2.1 표 + 결론 재작성** (Critical #1): 실제 review_bundle.md 샘플 첨부. "베이스라인 자체가 §1~§7 부재"를 인정한 위에 §8 권고가 의미있는 조건을 다시 도출.
3. **기존 lsp_check.py와의 관계 절 신설** (Critical #2): `core/static_diagnostics.py` 공통화 또는 hook 이전 또는 thin reader 중 택1을 명시. `_find_pyright()`·timeout·MAX_DIAG 재사용 의무화.
4. **timeout 산수 분해표 + hook_runner 변경 명시** (High #4): outer 10s 분해 + 동적/비동기/상향 중 택1. §3.2 변경 파일 표에 `scripts/hook_runner.py` 추가.
5. **source_hash 정책 수정** (High #5): 도구 버전 제외 또는 major/minor만 포함.
6. **frozen 정책 결정** (High #6): host PATH 의존 vs dev-only + §6 disclosed limitation.
7. **exit-code/CLI/메트릭 명세 보강** (High #7~#9): JSON parse 성공=success, `[workspace]` 또는 argparse 양 모드, `extra: dict|None` + sidecar 경로.
8. **§3.2 변경 파일 표 정합** (Medium #10): 누락 파일 추가, requirements.txt 정정.
9. **roll-back 경로 명시** — env var(`AF_DISABLE_DIAGNOSTICS=1`)? config? code revert? 절차를 §7에 절차로 등재.

위 1~8 처리 후 재리뷰 진입. HOLD 2건은 Critical 해결과 함께 자연 해소되거나 §6 측정 설계 절에서 답변.