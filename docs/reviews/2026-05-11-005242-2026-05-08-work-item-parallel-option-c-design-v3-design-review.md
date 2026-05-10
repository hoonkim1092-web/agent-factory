# Design Review: 2026-05-08-work-item-parallel-option-c-design-v3

> Source: docs/2026-05-08-work-item-parallel-option-c-design-v3.md
> Date: 2026-05-11 00:52
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Critic supplied 1 Critical + 3 High + 3 Medium findings with concrete `file:line` evidence (verified via baseline grep references). Cross-review failed with a provider error (`provider error: Reading prompt from stdin... session id: 019e...`) and produced **zero findings** — so this aggregation rests on Critic alone, but Critic's evidence is strong enough to BLOCK independently.

> **Cross-review status**: Codex provider error mid-stream. Per CLAUDE.md, missing external CLI providers ⇒ Tier 3 SKIP allowed. But because Critic alone produced a Critical, we BLOCK regardless.

### Aggregated Findings (7 total + 4 gaps)

#### 1. [ACCEPT] [Critical] §6 Stage 2 budget arithmetic self-contradiction
- **Critic**: 라인 384 says "design 267.4s **refine 2회 포함**" while 라인 449-452 says "design 1차 267s + refine 2×120s = 507s". 두 진술 양립 불가 — 267s가 already-refined total인지 first-call only인지 결정 불가. F1 budget guard와 §14 Step 5 검증 모두 이 모호한 base 위에 서 있음.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Evidence는 동일 문서 내부 두 문장의 직접 비교로 자명하다. 본 PR 머지 차단 사유로 충분.
- **Action Required**: (a) 라인 384를 "refine 0회 (1차 호출만)"로 정정 후 worst-case = "267 + 50~120 + α"로 분포 기반 재산정, 또는 (b) §14 Step 1에서 N≥5 측정 후 budget 산정으로 정책 자체 후행화. 둘 중 명시.

#### 2. [ACCEPT] [High] §11 라인 1233 "76라인" 본문 vs v3.1 흡수표 충돌
- **Critic**: §11 옛 표(1218-1234)는 "`core.file_lock`은 이미 76라인", v3.1 변경표(1240-1259)는 "82, 83"으로 정정. baseline은 `core.file_lock = af.spec:81`, `core.cli_session_cleanup = :82`, `core.work_item_telemetry = :83`. 두 표가 공존하면 후속 코드 PR이 어느 표를 참조할지 결정 불가.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. Critic이 grep으로 baseline 라인 번호 검증 완료. 메모리 `feedback_cross_review_stale_baseline_repeat.md` 패턴을 v3.1 본문이 자체적으로 만들고 있음.
- **Action Required**: §11 옛 표 1218-1234를 v3.1 변경표로 완전 대체하든지, "v3.1에서 라인 1240의 표로 대체됨" 헤더 명시 추가.

#### 3. [ACCEPT] [High] §9 cleanup 디렉토리 mtime — POSIX semantic 미해결
- **Critic**: §0a v3.1 row 10이 "자식 max(mtime) 기반 판정으로 변경 명시"로 흡수했다고 표기했으나, §9 라인 941-945와 baseline `core/cli_session_cleanup.py:39-46`는 그대로 `entry.stat().st_mtime` 단순 검사. POSIX상 dir mtime은 자식 add/remove에만 갱신 → 활성 codex 세션이 30일 후 통째로 삭제될 위험.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. "흡수했다"는 표기와 본문/baseline 코드 사이 명백한 불일치. 후속 코드 PR이 §9를 그대로 구현하면 활성 세션 cutoff 발생.
- **Action Required**: §9 코드를 `dir_mtime = max(rglob mtime)` 기반으로 변경하거나, 디렉토리 전용 TTL=60일+ 분리 명시.

#### 4. [ACCEPT] [High] §6 grace wait의 무조건 5s — 정상 흐름에서 idle 누적
- **Critic**: §6 라인 547-553이 not_done 검사 없이 무조건 `time.sleep(5)`. 정상 완료 시(refine 0회, ALL_COMPLETED 정시) subprocess는 이미 종료되어 race 위험 없음. dynamic_orchestrator 5-concurrent에서 25s pure idle 누적. §14 Step 2 측정도 평균 elapsed에 5s 추가 포함되어 비교 왜곡.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. 정당화(subprocess fd flush)는 timeout-fallback 경로에만 해당.
- **Action Required**: `if any(not f.done() for f in (fut_spec, fut_design)): time.sleep(_GRACE_SEC)` 조건부로 변경.

#### 5. [ACCEPT] [Medium] §10 `_call_anthropic_api` default timeout silent doubling
- **Critic**: baseline은 `urlopen(request, timeout=60)`, v3.1 default는 120s. 호출자가 timeout_sec 미전달 시 effective timeout이 silent하게 60s→120s. 라인 1210의 "무영향" 주장은 잘못. supervisor stall=120s 임계와도 충돌.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. baseline 보존이 최소 침습 원칙(CLAUDE.md "Surgical Changes")과 일치.
- **Action Required**: `timeout_sec: int = 60`으로 baseline 보존, 또는 모든 기존 호출자 grep + 영향 분석 첨부.

#### 6. [ACCEPT] [Medium] §6 STAGE_BUDGET[3] 변수값(110s) vs 효과 deadline(105s) 이중 표기
- **Critic**: 라인 395는 110s, 라인 559-564는 deadline_3 = 105s, §14 Step 4.1 trigger는 110s 기준. 후속 코드 PR이 grace 차감 누락 시 effective budget 110s로 코드화될 위험.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. 단일 진실원이 부재하면 구현 시 산술 누락 발생 high probability.
- **Action Required**: `STAGE_3_EFFECTIVE = STAGE_BUDGET[3] - _GRACE_SEC` 명시 상수로 분리, §14 trigger도 effective 기준으로 통일.

#### 7. [ACCEPT] [Medium] §14 Step 2 본 PR 머지 시점에 실행 불가
- **Critic**: F1 guard가 (c) 미구현 상태인데 §14 Step 2의 "Stage 2 wall-clock ≤ 405s" 검증은 baseline에 Stage 개념 자체 부재 → 머지 후 즉시 실행 불가. 그럼에도 본 PR PASS 기준으로 인용됨.
- **Cross**: not flagged (provider error)
- **Judgment**: ACCEPT. 메타-검증 가능성 결여는 v3.1 status 컬럼이 해소하려던 모순의 잔존.
- **Action Required**: §14 상단에 "본 절차는 후속 코드 PR 머지 후에만 실행 가능. 본 PR(설계 PR) PASS 기준은 §0a v3.1 11건 흡수 검증으로 한정" 명시.

#### Gaps (Missing from Design — Critic only, lighter severity)

- 후속 코드 PR 링크/일정 부재 — (c) 행 13개가 영구 미구현 시 stale baseline BLOCK 반복.
- `_extract_section_outline` 다른 호출자 영향 미열거 (단일 호출 — `_exec_stage3`).
- Frozen build에서 `_write_claude_settings` 우회 시 hook bridge 동작 미검증, §15 위험 등록 누락.
- `time.sleep(5)`의 testing/CI mock 경로 미명시.

이 4건은 정식 finding은 아니지만 BLOCK 해제 전에 함께 답변/명시 권장.

#### Positive Observations

- F11 REJECT 근거 정확 (af.spec:81-83 grep 검증). `feedback_reverse_sycophancy_balance.md` 패턴 모범 사례.
- Implementation Status (a)/(b)/(c) 컬럼 도입으로 "설계 명세 흡수" vs "코드 변경 흡수" 분리한 것 자체는 v3.1의 합당한 진전.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §6 Stage 2 budget 267s 산술 모순 | Critical | ACCEPT | Critic |
| 2 | §11 라인 1233 "76라인" vs v3.1 흡수표 충돌 | High | ACCEPT | Critic |
| 3 | §9 cleanup 디렉토리 mtime semantic 미해결 | High | ACCEPT | Critic |
| 4 | §6 grace wait 5s 무조건 적용 | High | ACCEPT | Critic |
| 5 | §10 anthropic timeout 60s→120s silent doubling | Medium | ACCEPT | Critic |
| 6 | §6 STAGE_BUDGET[3] 110s vs 105s 이중 표기 | Medium | ACCEPT | Critic |
| 7 | §14 Step 2 머지 시점 실행 불가능 | Medium | ACCEPT | Critic |

> Cross-review provider error로 cross-source 검증 0건. 모든 ACCEPT는 Critic 단독이지만 file:line+grep 근거로 evidence 강도 충분.

### Recommendations

1. **선결 (BLOCK 해제 필수)**: Finding #1 — §6 라인 384 "refine 2회 포함" 정정 또는 budget 산정 정책 후행화.
2. **선결**: Finding #2,#3 — §11/§9 본문을 v3.1 흡수 표기와 정합화 (옛 표 대체 + cleanup 코드 mtime semantic 수정).
3. **선결**: Finding #4 — grace wait 조건부 적용으로 정상 흐름 idle 제거.
4. **권장**: Finding #5,#6,#7 — timeout default 보존, effective budget 상수 분리, §14 메타-검증 가능 시점 명시.
5. **권장**: 후속 코드 PR 링크/머지 일정을 §0a 또는 §11 헤더에 명시 (stale baseline 반복 방지).
6. **재발화**: 위 7건 수정 후 cross-review 2라운드 재실행 (codex provider 인증 회복 필요). v3.1 11번째 흡수 항목 "Cross provider 인증 후 재실행"은 여전히 미해소.