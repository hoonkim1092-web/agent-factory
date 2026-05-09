# Design Review: 2026-05-03-phase2-verdict-label-spec

> Source: docs/2026-05-03-phase2-verdict-label-spec.md
> Date: 2026-05-03 23:28
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

2 Critical findings from Critic with strong evidence (Cross-review failed with provider error — codex usage limit, recovery 2026-05-05 15:37 KST). Per §10 of the original document, BLOCK is mandatory: do not implement until §5.4 code block + line 370 are fixed.

> Note on aggregation: Cross review returned a provider error (codex transcript only, no findings). Aggregation operates on Critic findings alone, but evidence is strong (exact line/file references for every Critical/High), so ACCEPT applies per Rule 2.

### Aggregated Findings (11 total + 4 Missing)

#### 1. [ACCEPT] [Critical] §5.4 코드 블록이 v3 BLOCK #1 (3-arg `_log_hook_event` 호출)을 그대로 유지 — 문서 제목 주장과 모순
- **Critic**: 라인 357-360에 `_log_hook_event(workspace, "warn_only_suppressed", {dict})` 3-arg 형식 잔존. 실제 시그니처는 `(builtin, file, exit_code: int, error="")` 4-arg. dict가 `exit_code: int` 슬롯에 들어가 `repr(dict)` 직렬화로 hook_events.log 파이프 컬럼 오염. §5.5는 4-arg로 정정됐는데 §5.4는 안 됨 — 제목이 명시한 "v3 BLOCK 재도입 해제"가 실제로 미적용.
- **Cross**: not flagged (provider error).
- **Judgment**: hook_runner.py:100 시그니처 + 28개 기존 콜사이트 전수 4-arg 사용을 Critic이 검증. §11 audit-trail 표(line 744-760)에도 "§5.4 코드 블록 4-arg 정정" 행 누락 — 계획만 됐고 패치 미반영. v5는 자기 제목과 자기 코드가 모순.
- **Action Required**: §5.4 line 357-360을 4-arg 형식으로 재작성하거나, Critic 권장 (a) 새 helper `log_hook_event_structured(workspace, event_type, payload)` 도입 + 별도 `hook_structured.jsonl` sink. (b) 현 sink 재사용 시: `_log_hook_event("warn_only_suppressed", "af-cross-review", round_count, error=json.dumps({...}))`. §11 v4→v5 표에 본 행 추가.

#### 2. [ACCEPT] [Critical] §5.4 line 370이 시그니처를 잘못 문서화 — 동일 v3 BLOCK 패턴 재발
- **Critic**: line 370 "`_log_hook_event()` 시그니처는 `(workspace, event_name, payload)`로 hook_runner.py helper와 일관" — 양 절 모두 거짓. 실제 시그니처 `(builtin, file, exit_code, error="")`. §5.5 line 422("4-arg")와 동일 문서 내 모순. v3 BLOCK #1이 v4에서 한 번 잡혔다가 v5에서 다시 산문에 누설.
- **Cross**: not flagged (provider error).
- **Judgment**: 산문 라인이 코드 블록과 같은 메시지를 잘못 전달 — 구현자가 어느 쪽을 따라야 할지 모호. 코드 블록(#1)+산문(#2)이 함께 BLOCK이어야 일관 수정됨.
- **Action Required**: line 370 삭제 후 §5.5 line 422 시그니처 표현으로 통일하거나 (#1 권장 helper 신설 시) 새 helper 시그니처로 대체.

#### 3. [ACCEPT] [High] §5.5 line 422가 hook_runner.py 라인 번호+파라미터 명을 잘못 인용
- **Critic**: "본 파일 line 64 정의된 helper" — 실제 정의는 line 100 (line 64는 `_find_venv_python` 후보 리스트). "event/target/exit_code/error" — 실제 명은 `(builtin, file, exit_code, error)`. 소스 cross-check 시 즉시 불일치 발견됨.
- **Cross**: not flagged (provider error).
- **Judgment**: 사실관계 정확성 문제. drift된 라인 번호와 잘못된 파라미터 명은 verifier가 source-truth와 대조할 때 false-positive trigger.
- **Action Required**: "line 100, signature `(builtin, file, exit_code, error="")`"로 정정.

#### 4. [ACCEPT] [High] §4.3 매핑 표에 `[ACCEPT-ADV] [Critical/High]` 콤보 파서 동작 미정의 — silent drop 위험
- **Critic**: line 187 "(해당 없음 — Critical/High은 ACCEPT/ACCEPT★ 경로)"는 정책 의도 표기일 뿐 파서 행위 미정의. line 192 fail-safe는 severity 누락 시에만 발화. LLM이 `[ACCEPT-ADV] [Critical] 제목` 발화하면 어느 행도 적중 안 함 → BLOCK/WARN/PASS 어느 쪽으로도 기여하지 않고 silent drop. fail-safe가 설계된 이유와 정확히 동일한 실패 모드.
- **Cross**: not flagged.
- **Judgment**: §4.3은 매핑 정규 출처(THE source of truth)인데 정의 누락이 silent miscategorization을 만든다. parser-level 안전망 설계 미비.
- **Action Required**: §4.3에 행 추가 — "라벨/severity 콤보 정의되지 않음 → BLOCK fail-safe" (`[REJECTED]` 예외 유지). 또는 Step 5 프롬프트에 "ACCEPT-ADV는 Medium/Low only" 강제 + Critical/High 발화 시 ACCEPT/ACCEPT★ 강제 변환 명시.

#### 5. [ACCEPT] [High] `_log_hook_event` private 함수의 cross-module 임포트 — 컨벤션 위반 + 테스트 미커버
- **Critic**: §5.4 line 370 "import 또는 inline 재정의" 양쪽 다 문제. import path는 underscore-prefix private 심볼 의존 → 향후 hook_runner 리팩터링이 check_pending_review.py 침묵 파괴. inline path는 helper drift. `tests/test_hook_runner_builtins.py:177-195`는 hook_runner 사본만 테스트, check_pending_review 사용처 미커버.
- **Cross**: not flagged.
- **Judgment**: 설계 결정 단계에서 두 경로 모두 부작용 보유. 공유 모듈 추출이 가장 낮은-위험 경로.
- **Action Required**: `scripts/_hook_log.py`에 `log_hook_event` 공개 함수로 승격 + 양쪽 사이트 import 통일 + 테스트 갱신. 핀딩 #1의 structured-helper 권장과 통합 처리.

#### 6. [ACCEPT] [Medium] §5.3 fence body 비어 있을 때 silent "pass" 가능
- **Critic**: line 314-315 — `<!-- final-verdict-start --><!-- final-verdict-end -->` (빈 펜스) + 외부 verdict 라인 존재 시: `target=""` → 매치 0 → None → caller가 fallback "pass". 외부 라인은 절대 스캔 안 됨. §7.2 C1-C6에 미커버.
- **Cross**: not flagged.
- **Judgment**: 정당한 엣지 케이스. v5는 fence 전용으로 의식적 1순위 분기를 만들었으므로 빈 fence 정책이 missing.
- **Action Required**: §7.2에 C7 추가 (입력: 빈 fence body + 외부 verdict 라인 / 기대 동작 결정 — 빈 fence를 fence 부재처럼 취급 vs `verdict_fallback` 시 sub-error code `empty-fence-body` 분리). 정책 명시.

#### 7. [ACCEPT] [Medium] §5.4 "import 또는 inline" 모순 두 지시 — 스펙 단계 결정 필요
- **Critic**: line 370 한 문장 안에 "import 또는 inline 재정의" + "(하나의 정의를 import)" — 후자는 import 강제처럼 읽힘. 구현자별 분기 발생.
- **Cross**: not flagged.
- **Judgment**: 핀딩 #5와 통합 — 공유 모듈 + import 강제로 결정.
- **Action Required**: 핀딩 #5의 `scripts/_hook_log.py` 추출 + import 단일 경로로 통일 명시.

#### 8. [ACCEPT] [Medium] §10 F8 — `AF_GATE_ALLOW_VERDICT_BLOCK`은 이미 존재하는 변수
- **Critic**: F8(line 720)이 "Phase 3에 도입"으로 명시. 실제는 `review_gate.py:196` `if not os.environ.get("AF_GATE_ALLOW_VERDICT_BLOCK"):`로 이미 shipping. 구현자가 "추가할 변수"로 오해 → 시간 낭비.
- **Cross**: not flagged.
- **Judgment**: 사실관계 오류 — 검증 가능.
- **Action Required**: F8을 "기존 `AF_GATE_ALLOW_VERDICT_BLOCK` (review_gate.py:196) 동작을 fence-aware verdict 추출 기준으로 재정의"로 재기술. "도입" 표현 삭제.

#### 9. [ACCEPT] [Medium] §5.5의 `subagent_type`이 `file` 슬롯에 들어가는 시맨틱 불일치
- **Critic**: line 411-416/419 — `_log_hook_event("verdict_fallback", subagent_type, 0, ...)`의 2번째 파라미터는 `file`. hook_runner.py 28개 콜 중 file/cmd 일관 사용. 이미 line 355에 `post_agent_record` 사례가 있어 v5가 precedent 계승하지만, hook_events.log column 2가 "file 또는 agent 또는 cmd-prefix" 다중 의미 → §9.2 grep 메트릭의 column 동치성 깨짐.
- **Cross**: not flagged.
- **Judgment**: 정당한 정합성 지적. precedent와 호환하려면 §9.1에 column 의미를 "context-key (file/agent/cmd-prefix)"로 문서화하든지 핀딩 #1 structured sink로 분리.
- **Action Required**: (a) §9.1에 column 다중 의미 명시 + 메트릭 식별자(첫 column = event-name)로만 grep 의존 명시, 또는 (b) 핀딩 #1과 통합해 structured sink로 이전.

#### 10. [ACCEPT] [Medium] §9.4 사전 검증 스니펫이 신규 wrapper를 테스트하지 않음
- **Critic**: §8.2 row 7이 추가하기로 한 "collision/fence" 테스트가 `tests/test_review_gate.py`에 아직 없음. §9.4가 `pytest -k "collision or fence"` 실행 → "no tests selected" 침묵 통과 → 구현자가 사전 검증 통과로 오해.
- **Cross**: not flagged.
- **Judgment**: 순서 의존성 + silent-pass 위험 정당.
- **Action Required**: §9.4에 명시적 순서 노트 — "§9.4는 §8.2 row 7 테스트 추가 이후에만 실행. 그 이전엔 smoke `python -c "from scripts.review_gate import _extract_verdict_from_content; print(...)"`로 대체".

#### 11. [HOLD] [Low] §8.2 단일 commit + 3-tier bootstrap의 미세 race
- **Critic**: 본 commit이 `.claude/agents/af-cross-review.md` (fence 강제 Step 5) + `scripts/*.py` (fence 파서)를 같이 commit. Tier 3 검증 라운드가 commit과 동시에 실행되며 agent runtime이 파일을 호출 시 다시 읽는 경우 새 prompt 즉시 활성, 그러나 verifier host의 파서는 commit 적용 시점에 따라 신/구 분기. v5의 "본 commit은 이전 형식"이라는 framing이 정확한지 agent runtime 동작에 의존.
- **Cross**: not flagged.
- **Judgment**: HOLD — `.claude/agents/*.md` 로딩 메커니즘(매 호출 디스크 재독 vs 세션 캐시)이 본 문서/리뷰에서 검증되지 않음. 사용자 또는 구현자 추가 조사 필요.
- **Question for Author**: agent runtime이 `.claude/agents/*.md`를 (a) 매 호출마다 디스크에서 다시 읽는가, (b) 세션 시작 시 캐시하는가? 답에 따라 §8.2 framing 정/오 결정.

### Missing from Design (Critic 단독 4건 — 모두 ACCEPT)

| # | 항목 | Action |
|---|------|--------|
| M1 | frozen-build (PyInstaller dist/af) sanity for `from scripts.review_gate import ...` | §8.3에 frozen import 검증 추가, 필요 시 `af.spec hiddenimports` 갱신 |
| M2 | 롤아웃 중 기존 `pending_agent_review.json`의 old `last_round_summary` 호환성 | §9.4에 "기존 marker 파일 입력 회귀 테스트" 추가 |
| M3 | 변형 펜스 (`<!-- final-verdict-start --><!-- final-verdict-start -->...`) lazy quantifier 동작 | §7.2에 malformed singleton 케이스 추가 |
| M4 | hook_events.log 회전/크기 정책 — 새 이벤트 추가로 볼륨 증가 | §9.2에 rotation 정책 또는 grep 대안 (jq+jsonl) 명시 |

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §5.4 코드 블록 3-arg 잔존 (제목과 모순) | Critical | ACCEPT | Critic |
| 2 | §5.4 line 370 시그니처 오기재 | Critical | ACCEPT | Critic |
| 3 | §5.5 line 422 라인번호+파라미터 오기 | High | ACCEPT | Critic |
| 4 | §4.3 [ACCEPT-ADV][Critical/High] 콤보 silent drop | High | ACCEPT | Critic |
| 5 | `_log_hook_event` private 함수 cross-module import | High | ACCEPT | Critic |
| 6 | §5.3 빈 펜스 body silent "pass" | Medium | ACCEPT | Critic |
| 7 | §5.4 "import 또는 inline" 모호 | Medium | ACCEPT | Critic |
| 8 | §10 F8 — `AF_GATE_ALLOW_VERDICT_BLOCK` 이미 존재 | Medium | ACCEPT | Critic |
| 9 | §5.5 `subagent_type`/file 슬롯 시맨틱 충돌 | Medium | ACCEPT | Critic |
| 10 | §9.4 pre-validation 신규 wrapper 미테스트 | Medium | ACCEPT | Critic |
| 11 | §8.2 single-commit bootstrap race | Low | HOLD | Critic |
| M1 | PyInstaller frozen import 검증 누락 | Medium | ACCEPT | Critic |
| M2 | 롤아웃 중 기존 marker 호환성 테스트 누락 | Medium | ACCEPT | Critic |
| M3 | malformed fence singleton 테스트 누락 | Low | ACCEPT | Critic |
| M4 | hook_events.log rotation 정책 누락 | Low | ACCEPT | Critic |

### Recommendations

1. **즉시(BLOCK 해제 필수)**: §5.4 line 357-360 코드 블록 4-arg 정정, §5.4 line 370 산문 정정 — 둘 다 적용한 v6 작성. §11 v5→v6 audit 표에 두 행 명시.
2. **High 동시 처리**: 핀딩 #5 + #7 통합 — `scripts/_hook_log.py` 공유 모듈 추출 + `log_hook_event` 공개 + import 단일 경로 결정 + `tests/test_hook_runner_builtins.py` 확장. 핀딩 #1과 결합해 structured sink 도입 검토.
3. **§4.3 매핑 보강**: 핀딩 #4의 ACCEPT-ADV/Critical-High silent-drop 안전망 추가. §4.3은 정규 매핑 출처이므로 정의 누락 자체가 spec 결함.
4. **사실관계 일괄 정정**: 핀딩 #3 (line 64→100, 파라미터 명), 핀딩 #8 (F8 framing) — 두 곳 모두 코드 직접 grep으로 검증 가능.
5. **테스트 갭 보강**: §7.2 C7(빈 fence body), Missing M3(malformed singleton), §9.4 pre-validation 순서/스모크 테스트.
6. **HOLD #11 해소**: agent runtime의 `.claude/agents/*.md` 로딩 동작 1회 확인 후 §8.2 framing 정/오 판정.
7. **v6 작성 + cross-review 재실행**: codex usage limit 회복 시점(2026-05-05 15:37 KST) 이후 cross-review 재실행 후 v6 ACCEPT 시도. 그 전에는 사용자 결정에 따라 Claude 단독 검증 진행 가능 (단 BLOCK 해제 책임은 사용자).