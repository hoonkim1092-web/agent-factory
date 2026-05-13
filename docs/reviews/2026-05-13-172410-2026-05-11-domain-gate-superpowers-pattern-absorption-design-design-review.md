# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:24
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

Cross-review provider 호출이 실패(stdout truncated)했으므로 critic 단독 근거를 기준으로 판정합니다. 식별자/경로 회귀 finding은 critic이 file:line + grep 결과를 인용했으므로 그대로 신뢰합니다.

## Final Design Review

### Verdict: BLOCK

근거: critic이 보고한 Critical 2건이 모두 강력한 코드 증거를 가지며, 그 중 #1은 본 설계가 §13에서 명문화한 "grep-before-write" 규칙과 memory `feedback_design_doc_grep_before_write.md`("5/11~5/13 식별자 회귀 3회")를 직접 위반한 4회차 회귀.

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] `blast_radius` enum에 존재하지 않는 `"local"` 식별자
- **Critic**: §3.2 line 157이 `{"local","module","cross_module","system_wide"}`로 표기. 실제 코드 `core/control/change_impact.py:35`/`:211-243`은 `{"isolated","module","cross_module","system_wide"}`이고 `"local"`은 코드에 0건.
- **Cross**: not flagged (provider error).
- **Judgment**: ACCEPT — 5/13 review에서 `"system"` 회귀(Critical #1)로 차단된 부류와 동일. memory `feedback_design_doc_grep_before_write.md`가 명시한 grep 의무를 §13 체크리스트 작성 본인이 위반.
- **Action Required**: §3.2 호출 스택 다이어그램과 §1.3 차원 설명을 `{"isolated","module","cross_module","system_wide"}`로 치환. §3.5 row 6 grep 대상에 `"local"` 추가.

#### 2. [ACCEPT] [Critical] `ControlPlaneIntake().normalize()` 삽입 지점 미결정
- **Critic**: §3.2 line 98이 `prepare_documents()`만 명시하지만 `prepare_brief()` (line 676)에 이미 `ControlPlaneIntake()._recall_from_memory()` 호출(line 710)이 존재. 양 dataclass 모두에 `normalized` 필드 carry 지시 → 한쪽은 dead field. 동일 인스턴스에서 `_recall_from_memory()` + `normalize()` 2회 호출 시 `_open_ledger_run()`가 다른 run_id로 기록될 위험(intake.py:92,126).
- **Cross**: not flagged.
- **Judgment**: ACCEPT — Phase A 첫날 호출자 결정이 분기점. dataclass carry/ledger run_id 정합 모두에 영향.
- **Action Required**: §3.2에 (a) 호출 위치를 `prepare_brief()` 단일로 고정, (b) `PreparedBrief.normalized`만 carry, (c) `_recall_from_memory` 별도 호출 폐기하고 `normalize()` 내부 `memory_context` 채움 — 셋 중 하나 선택을 명문화.

#### 3. [ACCEPT] [High] Phase A Python LOC 추정 ~140 — 실측 ~275의 절반
- **Critic**: §3.2 표 합산 = 80+40+25+20+30 = 195, §7.1 신규 테스트 80 LOC 합쳐 ~275. §7.5 line 442 ~140은 ±50% 캐비엇으로도 흡수 불가.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — 표 합 산수 검증 가능. 추정치 불일치는 일정 산정 신뢰성 직접 훼손.
- **Action Required**: §7.5 Phase A Python을 `~275 LOC`로 정정, 총합 ~330 → ~470 갱신. 또는 §3.2 표 어떤 항목이 빠지는지 명시.

#### 4. [ACCEPT] [High] `require_domain_review` vs `requires_domain_review` 표기 혼용
- **Critic**: §3.2 line 96, §3.3 line 177, §3.5 row 4, §10.2에서 's' 유무가 섞임. 구현자가 `requires_domain_review()` 호출 시 NameError.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — grep-able 식별자 결함 부류. Finding #1과 동질.
- **Action Required**: 함수=`require_domain_review`, 정책 플래그=`require_domain_review`로 통일하거나 `should_require_domain_review()`로 명시 분리. §3.2에 결정 명문화.

#### 5. [ACCEPT] [High] §5.3 row 3의 자동 발견 책임 모듈 오기재
- **Critic**: §5.3은 `core/skill_loader.py`가 자동 발견을 한다고 적었으나, 실제로는 `core/skill_registry.py:298-307 ensure_skills_loaded()` + `registry.auto_load_from_directories()`가 담당. `skill_loader.py`는 `SkillDependencyGraph` 헬퍼.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — 모듈 책임 misattribution은 5/13 Critical #1 부류의 회귀.
- **Action Required**: §5.3 row 3 검증 대상을 `core/skill_registry.ensure_skills_loaded()`로 정정. §7.4 hiddenimports 검증에 `core.skill_registry` 추가.

#### 6. [ACCEPT] [High] `project_pipeline.py:1516` 자동 승인 경로 — 반환값 무시 + `run()` dict 시그니처 미결정
- **Critic**: 실측 line 1516은 `_gate.approve(approver="auto", run_id=...)` 결과를 변수에 받지 않고 line 1518 `return self.execute(...)`로 진행. False가 와도 분기 없음. `BlockedExecutionError` 신설 폐기(§3.2 line 131)했으므로 dict 반환 스키마 결정 필요. "갱신"이 아닌 **신규 가드 추가**.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — LOC 추정 0으로 잡혀있으나 실제 ~10 LOC + 호출 시그니처 변경.
- **Action Required**: §3.2 caller 표에 line 1516을 별도 항목으로 분리하고 LOC 갱신. `run()` 헬퍼가 차단 시 반환할 dict 스키마 (`{"ok": False, "reason": gate.last_block_reason, ...}`) 명시.

#### 7. [ACCEPT] [Medium] §5.1과 §4.3 분류 규칙 불일치 — Phase C 1/2 순위 소실
- **Critic**: §4.3 규칙(즉시 흡수 vs 선택적 흡수)으로 분류하면 `verification-before-completion`은 선택적, 나머지 2개는 즉시. §5.1 표는 3개 모두 "잠정 흡수 후보"로 묶어 우선순위 정보 소실.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — 우선순위 결손은 Phase C 진입 시 충돌 유발.
- **Action Required**: §5.1 표에 "Phase C 순위" 열 추가, §4.3 분류 결과를 carry.

#### 8. [ACCEPT] [Medium] §3.5 row 4가 신규 정책 0% 검증
- **Critic**: `requires_domain_review=False` 시 통과 검증은 코드 무변경 상태 검증과 동치. 신규 로직 검증은 row 5 전담.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — 검증 기준 라벨이 baseline vs feature를 혼동시킴.
- **Action Required**: row 4 → "기존 work-item 회귀 baseline"으로 정정, row 5 "Domain Gate 발화 production"을 Phase A 진입 must-have로 격상.

#### 9. [ACCEPT] [Medium] `system_wide` 단독 트리거가 AF self-work에서 폭주 위험
- **Critic**: `change_impact.py:58` `_SYSTEM_WIDE_PATTERNS = ["core/", "core\\"]`, `_SYSTEM_WIDE_MIN_FILES = 10`. AF는 대부분 `core/` 손댐 → 단계 2 활성 시 거의 모든 self-work이 system_wide 발화 → `AF_SKIP_DOMAIN_REVIEW=1` default화 압력 (5/13 `AF_SKIP_REVIEW_GATE` 선례, memory `feedback_review_gate_hook.md`).
- **Cross**: not flagged.
- **Judgment**: ACCEPT — 비용/이득 역전 시나리오가 구체적이며 선례 있음.
- **Action Required**: §10.2에 단계 2 활성 전 1주 advisory 모드 발화율 sampling 추가. 20%↑이면 트리거 narrow(`core/control/` + `core/approval_gate.py`만) 검토. 메트릭 임계값에 발화율 포함.

#### 10. [ACCEPT] [Medium] `_DOMAIN_REVIEW_FILE` 격리 — verdict 사람 수정 시 재승인 메커니즘 미정의
- **Critic**: `_DOMAIN_REVIEW_FILE`를 `_DOC_FILES`에서 분리해 invalidate 회피는 OK. 그러나 verdict가 PASS→BLOCK으로 사람이 수정해도 `check_validity()` 미감지. 의도면 명시, 아니면 별도 hash tracking 필요.
- **Cross**: not flagged.
- **Judgment**: ACCEPT — verdict 변경 정책 부재는 Phase A 첫 1주 실사용 시 즉시 표면화.
- **Action Required**: §3.4에 1줄 추가 — (a) hash 추적 제외(한 번 PASS면 끝) 또는 (b) `_DOMAIN_REVIEW_FILE` 별도 snapshot 저장 중 명시.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `blast_radius` enum `"local"` 회귀 | Critical | ACCEPT | Critic |
| 2 | `normalize()` 삽입 지점 미결정 | Critical | ACCEPT | Critic |
| 3 | Phase A LOC 추정 ~140 vs 실측 ~275 | High | ACCEPT | Critic |
| 4 | `require/requires_domain_review` 혼용 | High | ACCEPT | Critic |
| 5 | §5.3 row 3 모듈 책임 오기재 | High | ACCEPT | Critic |
| 6 | `project_pipeline.py:1516` 가드 누락 + dict 시그니처 | High | ACCEPT | Critic |
| 7 | §5.1/§4.3 분류 불일치 | Medium | ACCEPT | Critic |
| 8 | §3.5 row 4 검증 라벨 오류 | Medium | ACCEPT | Critic |
| 9 | `system_wide` 폭주 위험 | Medium | ACCEPT | Critic |
| 10 | verdict 사람 수정 시 재승인 정책 부재 | Medium | ACCEPT | Critic |

### Recommendations

구현 진입 전 다음을 모두 처리:

1. **식별자 회귀 일괄 정정** (Finding #1, #4, #5) — 한 커밋에 묶어 grep으로 0건 확인 후 §13 체크리스트에 grep 명령 실행 로그 첨부.
2. **`normalize()` 호출자/dataclass 단일화** (Finding #2) — `prepare_brief()` + `PreparedBrief.normalized` 단일 경로 결정을 §3.2에 명문화. `_recall_from_memory` 통합 여부 결정.
3. **LOC 추정 정정** (Finding #3) — §7.5 Phase A Python `~275`, 총 `~470`으로 갱신. Phase A 일정이 3.5일 그대로인지 재검토.
4. **caller dict 스키마 결정** (Finding #6) — `_gate.approve()` False 시 `run()`이 반환할 dict 키와 호출자 분기 명시. line 1516을 §3.2 표에 신규 항목으로 추가.
5. **system_wide 발화율 advisory 측정** (Finding #9) — §10.2 단계 1→2 사이에 1주 sampling 게이트 추가.
6. **verdict 사람 수정 정책 + §5.1 Phase C 순위 + §3.5 row 4 라벨** (Finding #7, #8, #10) — 각 1~2줄 명시.
7. **재리뷰** — 위 7항목 반영 후 cross-review provider 정상 응답을 확보한 상태에서 1라운드 더 (memory `feedback_design_review_rounds_stop_rule.md` 3라운드 cap 카운터 진입).