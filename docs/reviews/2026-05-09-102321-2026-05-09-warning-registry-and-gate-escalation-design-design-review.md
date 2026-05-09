# Design Review: 2026-05-09-warning-registry-and-gate-escalation-design

> Source: docs/2026-05-09-warning-registry-and-gate-escalation-design.md
> Date: 2026-05-09 10:23
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

설계 v4는 두 리뷰어가 공통으로 지적한 **Critical 1건(§6.3 path/link baseline 충돌)** 과 **High 다수**가 미해결입니다. 적어도 #1·#2·#6은 구현 직전 회귀를 일으키므로 v5로 갱신 후 진입을 권장합니다.

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [Critical] §6.3 ApprovalGate 링크/경로 baseline 충돌
- **Critic**: target_path 모드에서 `ApprovalGate(doc_root, slug)` (work_item_generator.py:1061)와 `_decision.md`의 workspace 위치가 서로 다른 루트 → "workspace-relative" plain text 링크가 깨짐.
- **Cross**: 동일 — `ApprovalGate.__init__` (approval_gate.py:78)이 받는 root와 registry가 요구하는 workspace를 분리할 implementation contract 부재.
- **Judgment**: 두 리뷰가 동일한 코드 라인(958, 1061, 78-84)을 인용하며 일치. v4 §6.3 전제("approval-gate.md가 workspace 하위에 위치")가 baseline에서 거짓.
- **Action Required**: §6.3 두 옵션 중 하나로 명세 수정 — (a) `_decision.md`를 `<doc_root>/docs/work-items/<slug>/` 로 이동(상대 링크 작동) 또는 (b) `review_notes`에 `os.path.abspath` 절대경로 기록. 또한 `ApprovalGate` 시그니처에 `runtime_workspace` 별도 인자 도입을 §3.x에 명시.

#### 2. [ACCEPT] [High] CLI invocability — `--workspace` 누락
- **Critic**: Acceptance #2가 `--slug`만 받지만 §4.0이 cwd fallback 금지. 또한 frozen build에서 `python -m` 미동작 → `af.exe` subcommand 라우팅 명세 필요.
- **Cross**: 동일 지적 — `--workspace <ws> --slug <slug>` 강제 필요.
- **Judgment**: 양 리뷰 일치. 현 acceptance로는 CLI 검증 자체가 불가.
- **Action Required**: §10 #2를 `python -m core.warning_registry summary --workspace <ws> --slug <slug>`로 정정. §7.3에 `argparse --workspace` (required) + frozen 빌드 subcommand 명시.

#### 3. [ACCEPT] [High] `_summary.json` 비원자적 쓰기 + lock 비대칭
- **Critic**: jsonl path lock(`<rule_id>.jsonl.lock`)이 `_summary.json` 동시성을 보호하지 못함. 비원자적 dump는 M10 회귀.
- **Cross**: 동일 — code-review M10 부채 인용. `core/work_item_telemetry.py:62`의 tempfile + `os.replace()` 패턴 적용 요구.
- **Judgment**: 양 리뷰 일치. 기존 코드 베이스에 동일 부채 사례 존재 → 회귀 위험 명백.
- **Action Required**: §4.4에 (a) `_summary.json` 전용 lock 또는 jsonl과 동일 키 lock 정책 + (b) tempfile + `os.replace()` 의무화. acceptance #6에 lock 동시성 + corruption 테스트 추가.

#### 4. [ACCEPT] [High] `affected_phase` 입력 검증 누락
- **Critic**: 비표준 phase("design", "test")가 silent 통과 시 §5.1 정책 매칭에서 escalation 영구 미발화 위험. baseline `_PHASE_ORDER` 외 값 처리 미정.
- **Cross**: 별도 지적 없음.
- **Judgment**: Critic 단독이지만 baseline 인용(`_make_checklist` fallback 패턴)이 강하고, 실제 LLM 출력에서 비표준 phase 관찰 가능. 채택.
- **Action Required**: §2.1/§3.3에 `record()`의 phase 정규화 정책 1줄 — 비표준은 `"build"`로 정규화 + `extra.original_phase` 보존 OR `ValueError` 거부. acceptance에 unit test 1건.

#### 5. [ACCEPT] [High] `_summary.json` lazy update 트리거 부재
- **Critic**: "10건마다 또는 run 종료 시점" 트리거 호출처 미정. minesweeper 1건 record case에선 stale → acceptance #2/#11 부정확.
- **Cross**: 별도 지적 없음.
- **Judgment**: Critic 단독. 그러나 acceptance 검증 자체가 의존하는 데이터 정합성이라 HIGH로 채택.
- **Action Required**: §4.4/§8.1에서 `summarize()`를 read-on-demand(jsonl 풀스캔)로 단일화 OR `record()`마다 즉시 갱신으로 일관화. 2개 모드 공존 금지.

#### 6. [ACCEPT] [High] `repeat_count` 소유권 모호 (P1 vs P4)
- **Critic**: §8(Schema 진화 정책 부재)에서 부분적으로만 다룸.
- **Cross**: 정확히 짚음 — schema에 `repeat_count` 존재, policy에서 `repeat_count_min` 사용, 그러나 P4가 계산한다는 모순. `evaluate(record)` 시그니처가 단일 record만 받음 → history 스캔 불가능.
- **Judgment**: Cross 단독이지만 §2.2/§5.1/§5.4 cross-reference 인용 강함. P2 활성화가 e2e_command_missing이므로 즉시 영향.
- **Action Required**: §5.4 `evaluate()` 시그니처를 `evaluate(record, registry)` 또는 `evaluate(record, history)`로 수정 OR `record()`가 prior count 계산 후 persist. 한 가지 컨트랙트로 §2.2와 §5.x를 단일화.

#### 7. [ACCEPT] [High] `_global/` 디렉토리 producer API 부재
- **Critic**: §4.1에 `_global/<rule_id>.jsonl` 명시되지만 §4.0 API에는 record(slug별)만 존재. 어느 코드가 _global을 작성하는지 불명. P1 PR scope 누락.
- **Cross**: 별도 지적 없음(.gitignore 명세에서만 언급).
- **Judgment**: Critic 단독. P1 scope 정합성 측면에서 명확한 누락.
- **Action Required**: §4.0에 `rebuild_global(*, rule_id)` 추가 OR §4.1에서 `_global/`을 P4로 미루고 P1 디렉토리 구조에서 제거(권장 — scope 단순화).

#### 8. [ACCEPT] [Medium] `.gitignore` exception semantics 미명세
- **Critic**: Missing-from-Design에서 multi-PC 동기화 한계로만 언급.
- **Cross**: 정확히 지적 — `runtime/warnings/*` 패턴 + `!_index.json` 예외 순서 + `projects/*/runtime/warnings/` 다중 워크스페이스 경로.
- **Judgment**: Cross 단독이지만 구체적 패턴 제안 포함. 채택.
- **Action Required**: §4.1에 명시적 .gitignore 규칙 추가 (Cross 제안 패턴 또는 동등 명세).

#### 9. [ACCEPT] [Medium] `escalation_policy.yaml` 로더/frozen path 명세 부재
- **Critic**: P1 stub이 yaml을 읽지 않더라도 P2 진입 시 즉시 필요. frozen `_MEIPASS` 경로 해석 미정.
- **Cross**: 별도 지적 없음.
- **Judgment**: Critic 단독. baseline `core/policy.py:40` 패턴 인용 강함.
- **Action Required**: §5.4 또는 §8.3에 (a) loader 헬퍼, (b) `core/config_paths.py` frozen-aware path resolution 추가. P1 scope에 loader stub만이라도 포함.

#### 10. [ACCEPT] [Medium] Schema 진화 정책 부재
- **Critic**: P4 신규 severity/필드 추가 시 P1 jsonl deserialize 정책 미정.
- **Cross**: #5와 부분 중첩.
- **Judgment**: Critic 주도. 채택.
- **Action Required**: §2.x에 "open schema, unknown 필드 무시 + 누락 필드 default 채움" 1절 추가 + round-trip 테스트.

#### 11. [HOLD] [Medium] RunEvent observability placeholder 모호
- **Critic**: 별도 지적 없음.
- **Cross**: "placeholder" 표현이 구현/테스트 기준으로 미흡.
- **Judgment**: 정보 부족 — `core.events.run_event` 기존 event type 존재 여부 + warning record 호출처가 `run_id`에 접근 가능한지 미확인.
- **Question for Author**: `core/events.py`에 warning 적합 event type이 있는가? `WarningRegistry.record()` 호출처에서 `run_id`가 가용한가? 둘 다 NO면 P1에서 event는 명시적 미발행으로 못박는 게 안전.

#### REJECTED Findings

- **[Cross#6] `detect_owner_drift` 시그니처 변경 회귀 우려**: REJECT. 호출처(`core/project_pipeline.py:1401`)가 truthiness만 사용하고 빈 리스트는 falsy → 회귀 없음. Critic도 Positive Observation #2에서 동일 결론.
- **[Critic#9] phase 분포 "1~5건" 추정**: ACCEPT (위 항목으로 흡수 — Acceptance 정확성). 단 별도 finding으로는 우선순위 낮음.
- **[Critic#10] Blueprint §3 placement**: ACCEPT — PR scope 작업이지만 설계 정합성 BLOCK 사유는 아님 → recommendation으로 격하.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §6.3 path/link baseline 충돌 | Critical | ACCEPT | Both |
| 2 | CLI `--workspace` 누락 | High | ACCEPT | Both |
| 3 | `_summary.json` 원자성·lock 비대칭 | High | ACCEPT | Both |
| 4 | `affected_phase` 검증 누락 | High | ACCEPT | Critic |
| 5 | lazy `_summary.json` 트리거 부재 | High | ACCEPT | Critic |
| 6 | `repeat_count` 소유권 모호 | High | ACCEPT | Cross |
| 7 | `_global/` producer API 부재 | High | ACCEPT | Critic |
| 8 | `.gitignore` exception semantics | Medium | ACCEPT | Cross |
| 9 | `escalation_policy.yaml` loader/frozen | Medium | ACCEPT | Critic |
| 10 | Schema 진화 deserializer 정책 | Medium | ACCEPT | Critic |
| 11 | RunEvent placeholder 모호 | Medium | HOLD | Cross |
| — | `detect_owner_drift` 회귀 우려 | — | REJECT | Cross |

### Recommendations (구현 진입 전 v5에서 처리)

1. **§6.3 재작성** — `ApprovalGate` 시그니처에 `runtime_workspace` 분리 인자 도입, `_decision.md` 위치를 doc_root 또는 절대경로로 명시 (Critical, #1)
2. **§4.0/§10 acceptance #2 정정** — `--workspace`/`--slug` 양쪽 required, frozen `af.exe warning-summary` subcommand 추가 (#2)
3. **§4.4 강화** — tempfile + `os.replace()` 의무화, `_summary.json`/`jsonl` lock 일관화, lazy 트리거 단일화(read-on-demand 권장) (#3, #5)
4. **§2.1/§3.3 phase 정규화** — baseline 외 phase 처리 명시 + unit test (#4)
5. **§5.4 `evaluate()` 시그니처 확정** — registry/history 접근 권한 컨트랙트 명시 (#6)
6. **§4.1 P1 scope 단순화** — `_global/`을 P4로 이연 (또는 `rebuild_global` API 추가) (#7)
7. **§4.1 .gitignore 규칙 명세** — Cross 제안 패턴 채택 (#8)
8. **§5.4/§8.3 loader 헬퍼** — frozen-aware path resolution + PyYAML 로딩 1줄 명시 (#9)
9. **§2.x 신규 절** — open schema deserializer 정책 + round-trip 테스트 (#10)
10. **RunEvent 결정** — `core/events.py` 적합 type 존재 + `run_id` 가용성 확인 후 P1 발행 여부 못박기 (#11)
11. **§7.3 PR scope 보강** — Master_Blueprint §3.x 신설 위치, §0 빠른 참조, §10 Blast Radius 4개 호출처 명시 (Critic#10 recommendation)