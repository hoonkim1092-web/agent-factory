# Design Review: 2026-05-12-graph-memory-evolution-discussion

> Source: docs/codex_논의/2026-05-12-graph-memory-evolution-discussion.md
> Date: 2026-05-12 12:17
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

2건 Critical + 4건 High가 모두 코드 실측·문서 직접 인용으로 뒷받침됨. Cross 리뷰는 provider error로 무산되어 단일 소스(Critic) 기반 판정이지만, 각 finding의 증거 강도가 충분함.

> **Note**: Cross Review는 Codex provider error(`gpt-5.5`로 잘못된 모델 ID 지정으로 추정)로 본문 미생성. 단일 리뷰 단점은 인지하되, Critic이 코드 라인 인용(`core/control/intake.py:40`, `core/memory_system/facade.py` 346 LOC, `core/memory_system/strategy_ledger.py:136`)을 다수 포함해 rule 2(single-flag + strong evidence → ACCEPT) 적용.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] Git Nexus 도구 식별 정보 부재 — 결정 트리 루트가 미검증
- **Critic**: §3-1·§6 Step 0가 "npx git nexus" 하나에 매달려 있는데 npm 패키지 ID·리포·라이선스·홈페이지 어느 것도 문서에 없음. 동명 패키지 충돌 가능.
- **Cross**: not flagged (provider error)
- **Judgment**: 문서 본문(line 99~105) 확인 결과 실제로 1차 출처 식별자 0건. 후속 Step 1~5가 전부 이 도구 위에 쌓여 있어 도구 부재 시 권장안 전체가 무효.
- **Action Required**: §3-1 표에 npm 패키지 식별자(`@scope/name`), 1차 URL, 라이선스, Windows 지원 명시. 미충족 시 §6 Step 0를 "도구 식별 + 사양 검증"으로 격하.

#### 2. [ACCEPT] [Critical] Step 1 "Intake 회상 wire-up 50 LOC" 비현실적
- **Critic**: `intake.py:40` memory_context dict 자리는 빔. 실제 wire-up은 facade/router 선택, 진입점 결정, run_budget 충돌, fallback, compaction 상호작용 동반. facade.py만 346 LOC → 50 LOC는 호출 한 줄 수준.
- **Cross**: not flagged
- **Judgment**: 코드 라인 인용 강함. 50 LOC vs 실제 200~400 LOC 추정의 갭이 후속 모든 Step의 일정 신뢰도 무너뜨림.
- **Action Required**: Step 1을 (a) 회상 진입점 후보 비교(Plan) + (b) 최소 wire-up(Implement) 2단계로 분리. 의존 모듈을 본 문서에서 확정 후 LOC 산정.

#### 3. [ACCEPT] [High] §1-3·§6 LOC 견적 전반 검증 미흡
- **Critic**: §1-1에서 "wire-up 갭이 핵심"이라 인정하면서도 30~100 LOC로 산정. Step 2의 verdict 파서·JSONL·dedupe·정규화 포함 시 60 LOC 의심.
- **Cross**: not flagged
- **Judgment**: #2와 같은 결함의 확장. §3-2가 호출처 5건을 정확히 인용한 수준의 검증을 §1-3·§6에 적용하지 않음.
- **Action Required**: LOC 컬럼을 "변경 대상 파일 + 호출 사이트 N개"로 교체. 각 Step의 대상 파일 목록 명시.

#### 4. [ACCEPT] [High] graphify `auto_invocable=true` 잔존이 Step 5까지 미루어짐
- **Critic**: `skills/graphify/meta.yaml` `status: active`, `last_test_ok: false`. 본 결정과 무관하게 현재도 잘못된 라우팅 trigger 가능. Step 5(마지막)로 미루면 PoC 기간 내내 오발화.
- **Cross**: not flagged
- **Judgment**: 안전 작업이며 PoC 결과와 독립적. 우선순위 잘못됨이 명백.
- **Action Required**: §6에 "Step −1: graphify auto_invocable 즉시 disable + Q1~Q11 종결/폐기 결정" 추가.

#### 5. [ACCEPT] [High] Frozen 빌드 + Windows에서 npx 호출 경로 미검증
- **Critic**: `blast_radius.py`는 review-gate hook chain에서 호출됨. (a) hook subprocess PATH에 npx 존재 여부, (b) `dist/af/af.exe` frozen 빌드에서 외부 Node 의존 안내, (c) Volta/NVM/시스템 설치본 충돌 미고려.
- **Cross**: not flagged
- **Judgment**: CLAUDE.md "frozen build 호환성" 명시 체크리스트인데 통과 시도 자체가 없음. Step 0 "Node v24.13.1 확인"만으론 hook 컨텍스트 검증 불가.
- **Action Required**: §6 Step 0에 "Windows + frozen 빌드(`dist/af/af.exe`) 경로에서 npx 가용성 검증" 항목 추가. 미충족 시 Step 1 wrapper는 source-only 게이트 한정.

#### 6. [ACCEPT] [High] §7 미해결 6건 중 3건이 Step 1 진입 차단 조건
- **Critic**: §7-3 review-gate invariant 갱신 정책(Step 2 차단), §7-4 MCP namespace 충돌(Step 4 전제), §7-5 PC 간 일관성(본 결정에 직접 묶임)을 "미해결" 표로 미룸.
- **Cross**: not flagged
- **Judgment**: `tests/test_phase1_blast_tier_invariant.py` 갱신 기준이 없으면 Step 2 PR 닫지 못함이 코드 사실.
- **Action Required**: §7의 1·3·4·5번을 §6 Step 0 의존조건으로 격상. 각 항목에 결정 책임자/기한 명시.

#### 7. [ACCEPT] [Medium] §2-1 헤더 "4중 차단" vs 표 5개 항목 불일치
- **Critic**: 5번 "통합 자체가 Phase 0"는 "차단"이 아니라 "상태". 후속 인용에서 카운트 어긋남.
- **Cross**: not flagged
- **Judgment**: 문서 일관성 결함, 수정 사소함.
- **Action Required**: 헤더를 "4중 차단 + 1 메타 상태" 또는 "5중 상태"로 수정.

#### 8. [ACCEPT] [Medium] §4-3 D안과 §6 Step 4의 정합성 모호
- **Critic**: 두 곳 모두 "MCP 사용자 채널 분리" 표현 사용. 정책 옵션 vs 구현 단계 정의 정합성 미보장. §238 "정책 한 줄"의 범위 모호.
- **Cross**: not flagged
- **Judgment**: 메모리화 후보 한 줄이 모호하면 후속 인용에서 의미 변질.
- **Action Required**: §6 Step 4 본문에 "(§4-3 D안 구체화)" 명시. 정책 한 줄을 "subprocess 기본 + MCP 사용자 채널 옵션, 두 채널 명시 분리"로 단일화.

#### 9. [ACCEPT] [Medium] §1-3 Step 4 Crystallization 의존성 표기 오류
- **Critic**: Crystallization은 episode가 라이브로 기록·점수화돼야 의미. "Step 2 의존"만으론 부족, 실제론 Step 3 동시 wire-up 필요.
- **Cross**: not flagged
- **Judgment**: 의존 그래프 자체가 틀림.
- **Action Required**: Step 4 의존을 "Step 2 + Step 3"로 수정 또는 Step 3/4 묶음 처리.

#### 10. [ACCEPT] [Medium] strategy_ledger 동명 모듈 2개 — §1-1 식별 모호
- **Critic**: `core/ise_strategy_ledger.py`(241 LOC)와 `core/memory_system/strategy_ledger.py`(record_episode_outcome 보유) 2개 존재. 표기 어느 것인지 불명.
- **Cross**: not flagged
- **Judgment**: 코드 실측 사실. Step 2/4 표기에 모호성 상속.
- **Action Required**: 문서 전체에서 `memory_system/strategy_ledger`로 일관 표기.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Git Nexus 식별 정보 부재 | Critical | ACCEPT | Critic |
| 2 | Step 1 LOC 비현실 | Critical | ACCEPT | Critic |
| 3 | LOC 견적 전반 미검증 | High | ACCEPT | Critic |
| 4 | graphify auto_invocable 잔존 | High | ACCEPT | Critic |
| 5 | Frozen+Windows npx 미검증 | High | ACCEPT | Critic |
| 6 | §7 미해결 3건 Step 1 차단 | High | ACCEPT | Critic |
| 7 | §2-1 헤더/표 불일치 | Medium | ACCEPT | Critic |
| 8 | §4-3 D안 ↔ §6 Step 4 정합성 | Medium | ACCEPT | Critic |
| 9 | Step 4 Crystallization 의존 표기 | Medium | ACCEPT | Critic |
| 10 | strategy_ledger 동명 모듈 모호 | Medium | ACCEPT | Critic |

### Recommendations

1. **Cross Review 재실행** — Codex provider error 원인(model ID `gpt-5.5` 추정) 확인 후 본 문서 재검증. 단일 리뷰 단점 보완 필수.
2. **선결 조치(BLOCK 해제 전 필수)**:
   - §3-1에 Git Nexus npm 패키지 ID·1차 URL·라이선스 추가, 또는 §6 Step 0를 "도구 식별" 단계로 격하
   - §1-3 Step 1을 Plan/Implement 2단계로 분리, LOC 컬럼 → 호출 사이트 + 변경 파일 목록으로 교체
   - §6에 "Step −1: graphify auto_invocable 즉시 disable" 추가
   - §6 Step 0에 frozen 빌드(`dist/af/af.exe`) + Windows npx 가용성 검증 항목 추가
   - §7의 1·3·4·5번을 Step 0 의존조건으로 격상
3. **문서 일관성 수정**:
   - §2-1 헤더/표 카운트 일치
   - §6 Step 4 → "(§4-3 D안 구체화)" 명시
   - §1-3 Step 4 의존을 "Step 2 + Step 3"로
   - 전체 문서에서 `memory_system/strategy_ledger` 일관 표기
4. **Missing from Design 보강**: 토큰 절감 측정 방법론, Step 2 verdict→outcome 스키마, Step 0 성공/실패 기준 수치화, §7 항목별 책임자·기한.
5. **구현 진입은 위 1~4 완료 후**. 현 상태로 Step 0 PoC 실행은 가능하나, Step 1 이후 진입은 BLOCK.