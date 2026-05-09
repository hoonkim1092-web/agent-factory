# Design Review: 2026-04-08-canonical-projection-document-architecture

> Source: docs/features/2026-04-08-canonical-projection-document-architecture.md
> Date: 2026-04-08 16:07
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (3 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

Cross Review가 타임아웃으로 결과를 산출하지 못했으므로, Critic Review의 근거 품질만으로 판정한다. Critic이 제시한 코드 참조와 증거가 구체적이고 검증 가능하므로, 강한 근거의 발견은 ACCEPT 처리한다.

핵심 설계 원칙(canonical 유지 + projection 파생)은 건전하나, **설계 문서 내 사실 오류 3건(High)**을 수정하지 않으면 구현 시 혼란이 발생한다. Critical(차단 수준)은 아니지만 구현 착수 전 문서 정정이 필요하다.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] `locked_file()` 원자성 주장이 실제 코드와 불일치
- **Critic**: `write_project_board()`는 단순 `write_text()` 호출이며 `locked_file()`이나 어떠한 락도 사용하지 않음. code-review.md M10에서도 non-atomic 쓰기 잔존 지적.
- **Cross**: (타임아웃 — 미확인)
- **Judgment**: Critic이 `project_task_board.py:474-477` 및 code-review.md M10을 구체적으로 인용. 설계 문서 line 29의 "locked_file() 원자성 유지"는 사실과 다른 전제이며, 이 위에 projection 쓰기 패턴을 설계하면 같은 문제를 상속한다.
- **Action Required**: line 29를 "기존 `write_text()` 기반 (원자성 미확보)"로 정정. projection 쓰기 시 atomic write 적용 여부를 명시.

#### 2. [ACCEPT] [High] `skill_manifest.json`과 기존 `skill-usage.jsonl`의 역할 중복
- **Critic**: `_record_selection_feedback()`가 이미 11개소에서 호출되어 `decision_mode`, `status`, `confidence`, `score`를 `data/skill-usage.jsonl`에 기록 중. 설계의 "조달 경로 정보 미보존"(line 192) 주장이 부정확.
- **Cross**: (타임아웃 — 미확인)
- **Judgment**: 11개 호출 지점이 구체적으로 열거됨. 설계 원칙 §2-3 "별도 source of truth를 만들지 않는다"와 자체 모순 위험. `skill_manifest.json`이 시계열 로그(jsonl)와 어떻게 다른지 차별화가 필요.
- **Action Required**: line 189-192를 정정. `skill-usage.jsonl`(시계열 로그)과 `skill_manifest.json`(해당 run의 최종 스냅샷)의 관계를 명시적으로 정의.

#### 3. [ACCEPT] [High] P3 구현 시 `PreparedProject.work_item_slug` 단일 값 → 다중 값 변경 누락
- **Critic**: `PreparedProject`에 `work_item_slug=slug`로 단일 값 저장(line 681). 모듈 단위 재편 시 리스트화 또는 루프 호출이 필요하며 `sync_board_from_work_items()` 변경도 연쇄됨. 영향 범위(line 5)에 `project_task_board.py` 누락.
- **Cross**: (타임아웃 — 미확인)
- **Judgment**: `project_pipeline.py:657, 681, 744`의 구체적 참조로 근거 충분. P3의 실제 난이도가 설계보다 높을 수 있음.
- **Action Required**: §5에 `PreparedProject` 스키마 변경 명시. 영향 범위(line 5)에 `project_task_board.py` 추가.

#### 4. [ACCEPT] [Medium] `task_view.json` 생성 시 비동기 핫 패스에서의 동기 I/O
- **Critic**: `_lilith_decide_next()`는 async 메서드로 매 턴 호출됨. 동기 파일 쓰기는 이벤트 루프를 블로킹. 5-concurrent 에이전트 시 매 턴 최대 5회 파일 쓰기.
- **Cross**: (타임아웃 — 미확인)
- **Judgment**: 설계 자체가 캐시 전략 미결정을 인정(line 248). 비동기 환경에서의 I/O 패턴은 구현 품질에 직접 영향.
- **Action Required**: §4-2에 캐시 전략 옵션(lazy write vs. eager write) trade-off와 `asyncio.to_thread()` 사용 여부를 추가.

#### 5. [ACCEPT] [Medium] `_materialize_roles()` 라인 참조 오류
- **Critic**: line 197의 "`_materialize_roles():498-502`"는 실제로 `elif required_skills:`/`else:` 분기이며, manifest 경로 추가와 무관. 실제 삽입 지점은 line 482(write_yaml 전후)와 line 498-504(procure_multiple 호출 후).
- **Cross**: (타임아웃 — 미확인)
- **Judgment**: 코드 라인 참조 오류는 구현자를 잘못된 위치로 유도. 사실 확인 가능한 오류.
- **Action Required**: line 197의 라인 참조를 정확한 삽입 지점으로 수정. `procure_multiple()` 반환 타입 변경이 필요하면 그 영향도 명시.

#### 6. [ACCEPT] [Medium] `agents/{role_id}/` 디렉토리와 기존 에이전트 YAML 혼재
- **Critic**: `_role_agent_path()`가 이미 `agents/` 하위에 YAML을 저장. projection JSON이 같은 경로에 들어가면 YAML과 JSON이 혼재. 의도적인지 불분명.
- **Cross**: (타임아웃 — 미확인)
- **Judgment**: §3 디렉토리 구조(line 55)에서 `agents/{role_id}/`를 "신규"라 표기하지만, 기존 YAML 파일과의 관계가 정의되지 않음. 구현자가 경로 충돌에 부딪힐 수 있음.
- **Action Required**: §3 또는 §4-1에 기존 `_role_agent_path()`와의 관계를 명시. YAML(설정)과 JSON(projection)의 공존 규칙 정의.

#### 7. [ACCEPT] [Low] `ApprovalGate` 모듈별 전략 미결
- **Critic**: "추후 결정"으로 남기면 P3 착수 시점에 설계 공백. `execute()` 로직 변경까지 연쇄.
- **Cross**: (타임아웃 — 미확인)
- **Judgment**: P3는 "높음" 난이도로 이미 후순위. 다만 결정 기한 없이 미결로 두면 P3 자체가 indefinite postpone될 위험.
- **Action Required**: P3 체크리스트(line 271)에 "v1: 프로젝트 레벨 1개 유지"를 기본값으로 명시.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `locked_file()` 원자성 주장 불일치 | High | ACCEPT | Critic |
| 2 | `skill_manifest.json` vs `skill-usage.jsonl` 중복 | High | ACCEPT | Critic |
| 3 | `PreparedProject.work_item_slug` 스키마 변경 누락 | High | ACCEPT | Critic |
| 4 | 비동기 핫 패스에서 동기 I/O | Medium | ACCEPT | Critic |
| 5 | `_materialize_roles()` 라인 참조 오류 | Medium | ACCEPT | Critic |
| 6 | `agents/{role_id}/` 기존 YAML과 혼재 | Medium | ACCEPT | Critic |
| 7 | `ApprovalGate` 전략 미결 | Low | ACCEPT | Critic |

---

### Recommendations

구현 착수 전 설계 문서에 다음 정정을 반영:

1. **line 29**: "locked_file() 원자성 유지" → "기존 write_text() 기반 (원자성 미확보)" 정정
2. **line 189-192**: "조달 경로 정보 미보존" → `skill-usage.jsonl`과 `skill_manifest.json`의 역할 차이 명시
3. **line 197**: `_materialize_roles():498-502` 라인 참조를 실제 삽입 지점으로 수정
4. **line 5 영향 범위**: `project_task_board.py` 추가
5. **§3**: `agents/{role_id}/`에 기존 agent YAML과 projection JSON의 공존 규칙 추가
6. **§4-2**: 캐시 전략 옵션(lazy vs. eager)과 async I/O 패턴 trade-off 기술
7. **§5/line 238**: ApprovalGate v1 기본값을 "프로젝트 레벨 1개 유지"로 확정

> **참고**: Cross Review가 타임아웃으로 교차 검증이 불가했다. Critic의 근거가 모두 구체적 코드 참조를 포함하므로 단독으로 ACCEPT 처리했으나, 문서 정정 후 Cross Review 재실행을 권장한다.