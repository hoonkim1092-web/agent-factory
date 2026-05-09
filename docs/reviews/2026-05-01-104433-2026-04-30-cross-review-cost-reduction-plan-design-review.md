# Design Review: 2026-04-30-cross-review-cost-reduction-plan

> Source: docs/plans/2026-04-30-cross-review-cost-reduction-plan.md
> Date: 2026-05-01 10:44
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Critic Finding #1이 Critical로 분류됨 — Phase 4 code-as-spec이 기존 routing 의미론을 silent하게 변경한다. 구현 진입 전 해결 필수.

---

### Aggregated Findings (13 total)

#### 1. [ACCEPT] [Critical] Phase 4 code 예시가 `_required_tiers_for()` routing 의미론을 silent하게 변경한다
- **Critic**: "Phase 4 예시 `if blast_tier == 2: return [1, 2]`가 현재 `[1,2,3]` 반환을 `[1,2]`로 축소. 함수명도 `_required_tiers_for` → `required_tiers`로 변경. 문서에 명시 없음."
- **Cross**: "Cross #6과 부분 중복 — `_required_tiers_for()`가 현재 blast_tier만으로 tiers를 계산하는데 Phase 4 두 단계 라우팅은 이를 바꾸면서 명세 없음." (separately flagged)
- **Judgment**: Critic의 코드 인용이 구체적 (`review_gate.py:121-128` vs 문서 Phase 4 라인 362-379). blast_tier=2의 기본값 `[1,2,3]` → `[1,2]`는 Phase 1 invariant 정신과 별개라도, 문서 어디에도 "기존 blast_tier=2 의미가 바뀐다"고 적혀 있지 않다. 명시적 breaking change가 무고지 상태로 code example에 박혀 있다.
- **Action Required**: Phase 4 섹션에 ① "기존 `_required_tiers_for` 이름/시그니처 유지" 명시, ② blast_tier=2 routing 변경이 의도적이라면 별도 하위 섹션으로 분리 + Phase 3.5 데이터 기반 진입 가드 추가.

#### 2. [ACCEPT] [High] Bundle invalidation 이중 메커니즘 — race window + 타입 불일치
- **Critic**: "source_hash 비교 + updated_at 비교 동시 도입. atomic-replace 시 mtime/updated_at 불일치로 ground truth 모호. 에이전트 진입 후 추가 편집도 감지 불가."
- **Cross**: "`updated_at`은 float epoch, bundle 헤더는 ISO8601 — 구현자가 두 형식을 직접 비교하게 됨. `check_pending_review.py:100`, `review_gate.py:154` 모두 `float()` 강제 변환 사용 확인."
- **Judgment**: 두 리뷰어 모두 동일 섹션(라인 234-237)을 독립적으로 플래그. Cross는 코드 레벨 증거로 강화. race window + 타입 불일치는 동일 결함의 두 면.
- **Action Required**: invalidation 기준을 `source_hash` 단일 소스로 통일. bundle 헤더에 `generated_at_epoch: <float>` 추가 또는 `source_hash`를 canonical bytes(sorted JSON + git diff binary + st_mtime_ns)로 정의.

#### 3. [ACCEPT] [High] Phase 1 acceptance criteria — "4개 함수" 중복 표기
- **Critic**: "라인 420: `_required_tiers_for`가 두 번 등장. unique 이름은 3개. `enqueue_agent_review.py:109` max-merge가 invariant 핵심이라 했으나 docstring 대상에서 누락."
- **Cross**: not flagged
- **Judgment**: 단일 리뷰어이나 증거가 구체적(라인 번호 + 함수명 열거). 구현자가 "4개"라는 숫자를 신뢰할 수 없게 만드는 자기불일치.
- **Action Required**: 4-question test 표와 docstring 대상 함수를 1:1 매핑 표로 재정리. max-merge 함수(`enqueue_agent_review.py:109`)를 4번째 docstring 대상으로 추가.

#### 4. [ACCEPT] [High] `_apply_test_gap_verdict()` 호출 사이트의 `try/except`가 `NotImplementedError`를 삼킨다
- **Critic**: "`hook_runner.py:362-366`의 `try: from scripts.review_gate import downgrade_blast_tier … except Exception: pass` — Phase 1 step 3가 import만 제거하면 `ImportError → except → silent pass`. tripwire가 무의미."
- **Cross**: not flagged
- **Judgment**: 단일 리뷰어이나 실제 코드 경로(`hook_runner.py:362-366`)를 직접 인용. Phase 1의 핵심 invariant enforcement가 호출 사이트 cleanup 없이는 작동하지 않음.
- **Action Required**: Phase 1 step 3에 "downgrade_blast_tier import + 호출 + 둘러싼 `try/except` 블록 전체 제거" 명시.

#### 5. [ACCEPT] [High] Always-Tier-3 path 패턴 — fragile + bundle generator 미등록
- **Critic**: "`r'core/.*provider.*\.py'`가 무관 파일 매칭(위양). `.claude/skills/.*`는 개인 테스트 skill에도 T3 강제. blast_tier=1 + ALWAYS_TIER_3 매칭 시 우선순위 불명."
- **Cross**: "`scripts/build_review_bundle.py`가 Phase 4까지 T3 미등록. `blast_radius.py:48`에 해당 경로 없음."
- **Judgment**: 두 리뷰어가 동일 메커니즘(ALWAYS_TIER_3_PATTERNS)의 다른 결함을 독립 발견. Cross는 코드 레벨 증거 제시.
- **Action Required**: ① path-pattern 대신 `blast_radius.py`의 risk_flags에 "self-referential infrastructure" flag 추가. ② `scripts/build_review_bundle.py`와 `core/review_bundle.py`를 **생성 커밋과 동일 커밋**에 `_TIER3_PATHS`에 등록.

#### 6. [ACCEPT] [High] Bundle regeneration hook이 settings에 미연결
- **Critic**: not flagged (Phase 0 통합 명세 부재로 간접 언급)
- **Cross**: "`.claude/settings.local.template.json:88`에 `post_edit_enqueue`, `pre_bash_review_gate`, `post_agent_record`, `post_commit_clear` 미연결. `post_edit_enqueue`는 `hook_runner.py:132`에만 존재."
- **Judgment**: Cross가 실제 파일(settings.local.template.json:88, hook_runner.py:132) 직접 인용. "bundle 무효화 hook을 `post_edit_enqueue` 다음에 추가"라는 설계가 hook 자체가 미연결이면 전체 invaliation 체인 붕괴.
- **Action Required**: Phase 2 deliverables에 "settings.local.template.json hook chain 명시적 추가 + smoke test 스크립트(required hooks 연결 여부 검증)" 포함.

#### 7. [ACCEPT] [High] Phase 4 두 단계 Tier 3 라우팅 — state machine 미명세
- **Critic**: (Finding #1과 다른 측면 — 두 단계 아키텍처 자체가 아닌 semantic 변경에 초점)
- **Cross**: "현재 `check_pending_review.py:47`는 `af-test-runner` or 3개 전부만 반환. `review_gate.py:121`은 `[1]` or `[1,2,3]`만. T2 severity를 저장하는 계약과 'T2 high → T3 required' parser 규칙 미명세."
- **Judgment**: Cross가 현재 코드 상태를 직접 인용. 두 단계 라우팅은 현재 구조에서 구현 불가능한 상태.
- **Action Required**: Phase 4에 두 단계 state machine 명세: `[1,2]` 실행 → af-critic severity 파싱/저장 계약 → `T2 no-high → no T3` / `T2 high → T3 required` gate test 3종 추가.

#### 8. [HOLD] [Medium] ASTEngine — prep work 미포함 vs 과도한 의존성
- **Critic**: "Phase 2 본문에 ASTEngine prep work 없음. `_ensure_available()` 실패 시 caller 섹션 silent 비어있음."
- **Cross**: "ast-grep-py는 Rust native 의존성 + PyInstaller 작업 필요. v1에서는 Python `ast` + `rg`로 충분할 수 있음."
- **Judgment**: 두 리뷰어가 같은 영역을 반대 방향에서 플래그. Critic은 "준비 없이 진행하면 silent fail", Cross는 "그냥 안 써도 되는 거 아닌가". 어느 쪽이 옳은지는 설계 의도에 달림.
- **Question for Author**: Phase 2 v1 bundle에서 direct caller 추출의 **정밀도 요건**이 무엇인가? Python `ast` + ripgrep으로 충분하면 ASTEngine을 Phase 2 scope 외로 이동하고 Phase 2 prep을 제거. 필수라면 silent fail 방지를 위한 explicit error bundle section 명세 필요.

#### 9. [ACCEPT] [Medium] 메트릭 프레임워크 전체 미명세 — 수집 기간, 정의, 생산자 계약
- **Critic #7**: "1주 데이터 수집이 commit volume과 무관. 5개 미만이면 통계적 의미 없음."
- **Critic #8**: "'accepted finding' 정의 없음 — BLOCK 한정인지 WARN 포함인지 모호."
- **Cross #5**: "`review_metrics.jsonl` schema 명세하나 생산자 없음. `record_review_done()`는 tier/verdict/snapshot만 저장(review_gate.py:224)."
- **Judgment**: 3개 독립 플래그, 동일 메트릭 시스템의 다른 계층(기간, 정의, 구현). Phase 3.5 진입 조건 전체가 무의미해질 수 있음.
- **Action Required**: ① 진입 조건 "1주 OR commit ≥ N 중 늦은 쪽", ② `AcceptedFinding` 정의 dataclass, ③ `record_review_metrics()` with JSONL schema + 명시적 nullable 필드.

#### 10. [ACCEPT] [Medium] Bundle 잘라내기 우선순위 알고리즘 미명세
- **Critic**: "50KB 초과 시 'caller 부분부터 잘라냄'만 명시. 50개 심볼 × 3 caller = 150 caller block에서 어떤 게 살아남는지 알고리즘 없음. diff 50KB cap과 bundle 100KB cap 우선순위 불명."
- **Cross**: not flagged
- **Judgment**: 단일 리뷰어이나 구체적 계산 예시로 근거 충분.
- **Action Required**: bundle generator priority list 명시: ① diff(필수, 50KB cap) ② test gap ③ risk flags ④ direct callers(hunk 라인 수 큰 심볼 우선) ⑤ prior findings.

#### 11. [ACCEPT] [Medium] Phase 1 BLOCK 시 무한루프 출구 — max_rounds cap 중복
- **Critic**: "'10% 추정' 근거 없음. CLAUDE.md max_rounds=2와 'Phase 1 2회 BLOCK → escalate'가 같은 메커니즘인지 별개인지 불명."
- **Cross**: not flagged
- **Judgment**: CLAUDE.md의 기존 정책과 Phase 1 명세의 충돌 가능성. 둘 중 어느 쪽이 먼저 발화하는지 정의 없음.
- **Action Required**: "Phase 1 self-ref 발화는 max_rounds=2 cap에 위임" 또는 "Phase 1만 max_rounds=1 강제" 중 하나로 단일화.

#### 12. [ACCEPT] [Medium] Tool-call cap / extension log — 프롬프트 지시로만 존재, 집행 불가
- **Critic**: not flagged
- **Cross**: "`hook_runner.py:303`은 최종 Task 응답만 읽고 `record_review_done()` 호출. tool call 수 카운트, cap 집행, extension log 파싱, `[INCOMPLETE]`/`[scope-creep]` → gate 동작 변환 모두 없음."
- **Judgment**: Cross가 실제 코드 경로 인용. 현재 구현에서는 프롬프트 지시이므로 에이전트가 준수하지 않으면 감지 불가.
- **Action Required**: cap을 advisory로 명시하거나, 집행할 경우 `post_agent_record`에서 `incomplete`/`scope_creep`/`extension_log_count` 추출 + `is_gate_blocked()` 반영 명세.

#### 13. [ACCEPT] [Medium] Bundle 파일 write/lock 계약 누락
- **Critic**: (race window로 간접 언급)
- **Cross**: "기존 queue state는 `review_gate.py:52,92`에서 lock + temp file replace 사용. `review_bundle.md`에는 동일 보호 명세 없음."
- **Judgment**: Cross가 기존 패턴(코드 참조)과의 불일치를 직접 지적. bundle은 여러 hook/agent가 동시 접근할 수 있음.
- **Action Required**: `review_bundle.md.tmp` → `os.replace` 패턴 + `_state_lock` 재사용 또는 `review_bundle.md.lock` 명세. 에이전트는 헤더 파싱 실패 시 stale 처리.

---

#### R1. [REJECT] [Low] Frozen build 패키징 우려
- **Source**: Critic #11
- **Original Finding**: "scripts/build_review_bundle.py가 PyInstaller에 포함될지 미확인"
- **Rejection Reason**: 원본 문서 라인 36-40 설계 원칙 #6에 명시: "af.spec hiddenimports에 core.review_bundle 추가", "PyInstaller hook path 등록", "frozen smoke validation". Cross #8도 동일 이유로 REJECT. 우려가 이미 설계에 반영됨.

#### R2. [REJECT] [Low] `feedback_codex_reply_for_deliberation.md` 무관 단언
- **Source**: Critic #12
- **Original Finding**: "본문의 단언이 근거 없다"
- **Rejection Reason**: 해당 라인은 scope 명확화 주석. 내용 자체가 문서 설계 결함을 만들지 않음. 삭제는 선택 사항이지 필수 조건 아님.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Phase 4 routing 의미론 silent 변경 | Critical | ACCEPT | Critic |
| 2 | Bundle invalidation race window + 타입 불일치 | High | ACCEPT | Both |
| 3 | Acceptance criteria "4개 함수" 불일치 | High | ACCEPT | Critic |
| 4 | try/except가 NotImplementedError 삼킴 | High | ACCEPT | Critic |
| 5 | ALWAYS_TIER_3 패턴 fragile + bundle 미등록 | High | ACCEPT | Both |
| 6 | Bundle regen hook settings 미연결 | High | ACCEPT | Cross |
| 7 | Phase 4 두 단계 라우팅 state machine 미명세 | High | ACCEPT | Cross |
| 8 | ASTEngine — prep 미포함 vs 과도한 의존성 | Medium | HOLD | Both |
| 9 | 메트릭 프레임워크 전체 미명세 | Medium | ACCEPT | Both |
| 10 | Bundle 잘라내기 priority 알고리즘 없음 | Medium | ACCEPT | Critic |
| 11 | BLOCK 무한루프 — max_rounds cap 중복 | Medium | ACCEPT | Critic |
| 12 | Tool-call cap/extension log 집행 불가 | Medium | ACCEPT | Cross |
| 13 | Bundle 파일 write/lock 계약 누락 | Medium | ACCEPT | Cross |
| R1 | Frozen build 패키징 우려 | Low | REJECT | Critic |
| R2 | codex-reply 무관 단언 | Low | REJECT | Critic |

---

### Recommendations

구현 진입 전 반드시 해결:

1. **Phase 4 code example 수정** — `_required_tiers_for` 이름/시그니처 유지 명시. blast_tier=2 routing 변경이 의도적이면 별도 하위 섹션으로 분리 + 진입 가드.
2. **Bundle invalidation 단일화** — `source_hash` canonical bytes만 ground truth. 타입 혼용 제거.
3. **Bundle hook chain 복원** — `settings.local.template.json`에 필요 hook 명시 + smoke test 스크립트.
4. **Phase 4 두 단계 state machine 명세** — T2 severity 저장 계약 + parser 규칙 + gate test 3종.
5. **try/except 블록 전체 제거** — Phase 1 step 3에 명시.
6. **ALWAYS_TIER_3 패턴 재설계** — risk_flag 기반으로 대체, `build_review_bundle.py` 생성 커밋에 즉시 등록.

구현 중 처리:

7. **Acceptance criteria 표 재정리** — 4-question:function 1:1 매핑 + max-merge 함수 추가.
8. **메트릭 프레임워크** — `AcceptedFinding` 정의 + `record_review_metrics()` schema + 수집 기간 조건.
9. **Bundle truncation priority list** 명문화.
10. **max_rounds cap 단일화** — Phase 1 self-ref 발화 정책 CLAUDE.md cap으로 위임.
11. **Tool-call cap 정책 명시** — advisory vs enforced 중 결정.
12. **Bundle write lock** — `os.replace` + lock 패턴 명세.

저자 판단 필요 (HOLD):

13. **ASTEngine scope 결정** — Phase 2 v1에 Python `ast` + rg로 충분한지 확인 후 ASTEngine 포함 여부 결정. silent fail 방지 명세는 어느 쪽이든 필수.