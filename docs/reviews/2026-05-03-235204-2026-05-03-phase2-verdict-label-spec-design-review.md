# Design Review: 2026-05-03-phase2-verdict-label-spec

> Source: docs/2026-05-03-phase2-verdict-label-spec.md
> Date: 2026-05-03 23:52
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

**메타 노트**: Cross Review는 provider error로 미수행 (codex usage limit, v6 헤더 line 11에 명시된 회복 시점 = 2026-05-05 15:37 KST). 따라서 본 판정은 Critic Review 단독에 근거하며, 각 항목은 원문 증거 강도로 ACCEPT/HOLD/REJECT를 개별 판정한다.

핵심: 1 Critical (§11 자기참조 audit 결함) + 2 High (§10 F10 dead reference, payload split invariant 미보호) → BLOCK 확정.

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [Critical] §11 v5 → v6 audit row 부재
- **Critic**: 문서가 자신이 v5에서 정한 §11 audit 규칙(line 825 "§11 history table 미갱신" 정정 사례)을 v6에서 자기 자신에 적용하지 않음. v5 Critic #7 BLOCK이 v6에서 동형 재발.
- **Cross**: 미수행
- **Judgment**: 원문 line 1 "v6", line 776 audit 테이블 = "v2→v3→v4→v5"에서 멈춤이 1차 증거. v5에서 동일 결함을 명시 BLOCK으로 처리한 선례가 2차 증거. 자기참조 결함이 객관적으로 성립.
- **Action Required**: §11 끝에 "v5 → v6" 헤더 + 4-row 표 추가 (advisory #1·#2 정정 + #3·#4 비채택 결정 trace).

#### 2. [ACCEPT] [High] §10 F10 dead forward-reference
- **Critic**: line 394가 §10 F10을 forward-reference하나 §10 미결 표(line 762-773)에는 F1~F9까지만 존재. v5 패턴(같은 라운드에서 §10 F-row 동시 신설)을 v6은 따르지 않음.
- **Cross**: 미수행
- **Judgment**: 원문 grep으로 직접 검증 가능한 명백한 dead reference. v5 Missing #2/#3에서 같은 패턴(F8/F9 동시 신설) 선례 존재.
- **Action Required**: §10 표에 `F10 (v6 신규 — Medium #2)` 행 추가 — payload `\|` escape 또는 JSON-only line format 전환 트리거.

#### 3. [ACCEPT] [High] §5.4 line 394 payload 안전성 단언의 falsifiable 회귀 보호 부재
- **Critic**: "hardcoded 페이로드만 사용하므로 안전" 단언만 있음. §7.2/§7.6 어느 테스트도 "hook_events.log line이 정확히 5개 `|`-segment로 split되는가" 회귀 보호 없음. 미래 caller가 무심코 `|` 포함 데이터 넣을 시 silent breakage.
- **Cross**: 미수행
- **Judgment**: 단언 = 현재 페이로드 모양에 우연히 의존. spec-level 보장이 falsifiable해야 한다는 v3~v5 라운드의 일관 원칙(예: G11 measurable 재정의)에 부합. 회귀 보호 1건이 추가 비용 대비 강한 보호.
- **Action Required**: `tests/test_hook_runner.py`에 `test_log_hook_event_split_invariant()` 신설 + §8.2 적용 파일 표를 7→8파일로 확장.

#### 4. [ACCEPT] [Medium] v6 헤더 "advisory 4건 정정" vs 실제 처리 범위 불일치
- **Critic**: 실제 정정은 #1·#2 (2건). #3(§11 hybrid audit 옵션 A/B 선택), #4(§9.2 silent skip 명시) 누락. line 3 "4건 정정"이 다음 라운드 reviewer를 오도.
- **Cross**: 미수행
- **Judgment**: §11/§9.2 본문 직접 검증으로 #3·#4 비채택 확인 가능. 명시적 단언과 실제의 불일치는 metric-level 결함.
- **Action Required**: line 3을 "advisory 2건 정정 (#1·#2), #3·#4 의도적 비채택 — 사유 §11"로 정정 + §11 v5→v6 row에 비채택 사유 명시.

#### 5. [ACCEPT] [Medium] §5.3 last-position 휴리스틱 trailing prose 회귀 보호 부재
- **Critic**: v6은 prose만 보정("disjoint" → "last-position 안전"). §7.2 C3는 "위쪽 _VERDICT_RE + 아래쪽 _VERDICT_HEADER_RE"만 검증. "정상 verdict 라인 + 더 아래 trailing 본문에 verdict 키워드"의 LLM drift 케이스 미검증.
- **Cross**: 미수행
- **Judgment**: last-position이 휴리스틱(LLM 출력 형식 가정)임은 §5.3 line 298 prose 자체가 인정. 휴리스틱을 정규로 채택하는 만큼 한계 케이스 회귀 보호가 정합. C7 1건 추가 비용 낮음.
- **Action Required**: §7.2에 C7 신설 — "fence 부재 + 정상 `## PASS` + 그 아래 trailing 본문에 BLOCK 키워드 → last-position이 trailing 캡처(알려진 한계, fence 사용 권장)".

#### 6. [ACCEPT] [Medium] CLAUDE.md "WARN은 advisory" 정책과 v6 spec churn 비용
- **Critic**: v5 = WARN (BLOCK 0건). CLAUDE.md "WARN은 advisory — 자동 수정 의무 없음 (무한루프 방지)". v6은 의무 없는 advisory를 또 다른 spec churn으로 처리, 다음 라운드 cross-review까지 권장. v2→v6 5라운드는 max_rounds=2 캡 spec-level 정신과 충돌.
- **Cross**: 미수행
- **Judgment**: CLAUDE.md 정책은 본 worktree 진입 시 시스템 reminder로 명시 인용된 정규 정책. v6 작성 자체가 정책 위반 위험 — 단, 이미 작성된 만큼 minimal 정리 후 진입(option a) 또는 v6 철회·v5 commit 진입(option b) 중 명시 결정 필요.
- **Action Required**: 둘 중 하나 명시 결정 — (a) 본 BLOCK Findings 1·2·3·4·5·7 정리 후 cross-review 재실행 없이 §8.2 코드 commit, 또는 (b) v6 철회 + v5 그대로 commit + advisory를 commit message inline note로 처리.

#### 7. [ACCEPT] [Low] §1 line 36 narrative가 v6에서 미갱신
- **Critic**: §1 line 36이 여전히 "v5는 v4 §5.4의 ..." 시점 서술. v6 정정 사실(line 298, 394)이 §1에 미반영.
- **Cross**: 미수행
- **Judgment**: 원문 직접 검증. §11/§1 비대칭은 Finding #1과 한 묶음으로 처리.
- **Action Required**: line 36 끝에 "v6은 v5 cross-review WARN advisory 중 #1·#2를 prose 정정으로 흡수(코드 변경 없음, 7파일 commit 범위 불변)" 1줄 추가. (Finding #3 채택 시 "8파일"로 정정.)

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §11 v5→v6 audit row 부재 (자기참조 결함) | Critical | ACCEPT | Critic |
| 2 | §10 F10 dead forward-reference | High | ACCEPT | Critic |
| 3 | payload split invariant 회귀 보호 부재 | High | ACCEPT | Critic |
| 4 | 헤더 "4건 정정" vs 실제 2건 불일치 | Medium | ACCEPT | Critic |
| 5 | §5.3 last-position trailing prose C7 부재 | Medium | ACCEPT | Critic |
| 6 | CLAUDE.md WARN-advisory 정책과 v6 churn 충돌 | Medium | ACCEPT | Critic |
| 7 | §1 line 36 narrative v5→v6 미갱신 | Low | ACCEPT | Critic |

### Recommendations

**우선 결정 (Finding #6 — 메타 분기)**: v6 진행 경로를 명시 선택.

- **경로 (a) — v6 minimal 정리 후 진입** (권장): Findings #1·#2·#3·#4·#5·#7을 v7으로 흡수하되 cross-review 재실행 없이 §8.2 코드 commit 진입. v7에 이르러도 코드 변경 7→8파일로만 확장(테스트 1건 추가).
- **경로 (b) — v6 철회**: v5 그대로 §8.2 코드 commit + advisory 4건은 commit message에 inline note. 5라운드 spec churn 종결.

**경로 (a) 채택 시 v7 작업 목록**:
1. §1 line 36 narrative 갱신 (Finding #7).
2. §10 표에 F10 행 신설 (Finding #2).
3. §11에 "v5 → v6 → v7" audit row 신설 + 비채택 사유 명시 (Finding #1·#4).
4. §5.4 line 394 단언 보강 + `tests/test_hook_runner.py` split invariant 테스트 신설 (Finding #3).
5. §7.2 C7 케이스 신설 (Finding #5).
6. §8.2 적용 파일 표를 7→8파일로 확장 (Finding #3 종속).
7. line 3 헤더를 "advisory 2건 정정, #3·#4 의도적 비채택"으로 정정 (Finding #4).

**경로 (b) 채택 시**: 본 라운드 작업 종결, NEXT_STEPS.md에 advisory 4건을 P3 후보로 인덱싱 후 v5(`81eb2a7d`) 기준 §8.2 코드 commit 진입.

**Cross-review 재실행**: 어느 경로든 codex 회복(2026-05-05 15:37 KST) 후 추가 라운드는 권장하지 않음 — Finding #6의 churn 비용 우려 일관 적용.