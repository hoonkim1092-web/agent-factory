# Design Review: 2026-05-13-domain-gate-residual-risks-adr

> Source: docs/2026-05-13-domain-gate-residual-risks-adr.md
> Date: 2026-05-13 23:25
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

High findings exist across ADR correctness, code/spec alignment, and gate enforcement gaps. Implementation can proceed, but 3 items require action before Phase B entry metrics are relied upon.

---

### Aggregated Findings (11 total → 9 ACCEPT, 1 HOLD, 1 REJECT)

#### 1. [ACCEPT] [High] F6 `last_block_reason` 문자열 — ADR vs 실제 코드 불일치
- **Critic**: ADR F6는 `"missing_domain_review_file"` 명시, 실제 `core/approval_gate.py:238`은 `"missing_domain_frontmatter"` 사용. 테스트 fixture·운영 로그·대시보드 분류가 ADR을 canonical로 믿으면 파싱 실패.
- **Cross**: not flagged
- **Judgment**: Critic이 코드 라인 직접 인용. 소비자 영향(로그 파서, Phase B 메트릭 집계)이 명확하여 단독 플래그임에도 ACCEPT.
- **Action Required**: `core/approval_gate.py:238`의 `"missing_domain_frontmatter"`를 canonical로 확정하고, ADR F6 표를 동일 문자열로 정정.

---

#### 2. [ACCEPT] [High] ADR 파일 자체가 M2 저장 위치 규칙 위반
- **Critic**: M2 결정 `docs/decisions/` 저장 규칙이 CLAUDE.md에 추가됐지만, 본 ADR은 `docs/2026-05-13-domain-gate-residual-risks-adr.md`에 위치. `docs/decisions/`는 현재 0개 파일.
- **Cross**: not flagged (단, `docs/decisions/` ADR 위치를 Cross finding #1 근거로 간접 참조)
- **Judgment**: M2 규칙의 도입 ADR이 그 규칙을 스스로 위반한다는 역설. Glob 증거 명확.
- **Action Required**: 본 파일을 `docs/decisions/ADR-20260513-225500-domain-gate-residual-risks.md`로 이동. 또는 CLAUDE.md에 "M2 도입 이전 ADR 예외" 주석 추가 (소급 이동이 비용 대비 가치 없다고 판단될 경우).

---

#### 3. [ACCEPT] [High] `NEEDS_ADR` 판정이 ADR 파일 존재 없이 승인 통과
- **Critic**: not flagged
- **Cross**: `core/approval_gate.py:250` `PASS or NEEDS_ADR → 진행` 분기에서 `docs/decisions/` 내 실제 ADR 파일 존재 여부를 검증하지 않음. `NEEDS_ADR` advisory vs enforceable 계약 미정의.
- **Judgment**: 코드 라인 직접 인용. `NEEDS_ADR`이 "곧 ADR을 쓰겠다"는 의도인지 "이미 ADR이 있다"는 전제인지 ADR 어디에도 명시 없음. ACCEPT.
- **Action Required**: ADR에 `NEEDS_ADR` 계약 명시 — (a) advisory-only (현행 유지, 문서화만) 또는 (b) enforceable (domain-review.md에 ADR filename 포함 + 파일 존재 검증 + `last_block_reason="missing_required_adr"` 추가). 어느 쪽이든 선택 명시.

---

#### 4. [ACCEPT] [High] Phase B 진입 지표 1 — metadata 기록이지 gate 실행 증거 아님
- **Critic**: Phase B CI 기록 수집 인프라 미기술 (Missing from Design 항목)
- **Cross**: `approval-gate.md blast_radius: system_wide` 확인은 `_render()`가 호출됐다는 증거일 뿐. `approve()` 실제 enforce/block/bypass 여부를 `_emit_approval_event()`가 포함하지 않음 (`core/approval_gate.py:232` 증거).
- **Judgment**: 두 리뷰어가 같은 영역(Phase B 측정 신뢰성)을 다른 각도로 플래그. 함께 ACCEPT. 지표 1의 현재 측정법으로는 Phase B 진입 판단 불가.
- **Action Required**: 지표 1 측정 방법을 `hook_events.log` 또는 `_emit_approval_event()` 에 `{verdict, outcome, last_block_reason, bypass}` 포함하는 domain-gate 전용 이벤트로 교체. 또는 지표 1을 "≥1건 테스트 PASS (CI 기록)"으로 대체 정의.

---

#### 5. [ACCEPT] [High] `domain-review.md` 전체 복사되지만 `system_wide` 아니면 gate 무시
- **Critic**: not flagged
- **Cross**: `core/work_item_generator.py:1397` 무조건 복사 + `core/approval_gate.py:233` `system_wide`만 읽음. module-level 작업에서 리뷰어 BLOCK 판정이 무시됨.
- **Judgment**: 코드 두 군데 직접 인용. 리뷰어 입장에서 "BLOCK을 눌렀는데 통과됐다"는 신뢰 손상 패턴. ACCEPT.
- **Action Required**: ADR에 설계 의도 명시 — (a) `system_wide`만 복사, 나머지는 생성 안 함, 또는 (b) 어느 blast_radius든 `verdict: BLOCK`이 있으면 gate 차단, 또는 (c) 현행 유지하되 template에 "advisory only (non-system_wide)" 명기.

---

#### 6. [ACCEPT] [High] 게이트 상태 파일 비원자적 쓰기 (safety-critical 파일)
- **Critic**: not flagged
- **Cross**: `core/approval_gate.py:281` `write_text()` + `core/file_io.py:117` `open(..., "w")`. 승인/무효화/검증 차단 중 크래시 시 게이트 파일 손상. 프로젝트 코드리뷰 체크리스트에 non-atomic write = critical pattern 등록됨.
- **Judgment**: 증거 명확. 안전 임계 상태 파일에 직접 쓰기는 구현 결함. ACCEPT.
- **Action Required**: `core/file_io.py`에 temp file + `os.replace()` 원자 쓰기 헬퍼 추가. `approval-gate.md` 및 게이트 관련 상태 파일에 적용. (Phase A 완료 커밋 전 또는 독립 PR로 처리)

---

#### 7. [ACCEPT] [Medium] F1·F2 해결됐지만 ADR 상태 미갱신
- **Critic**: Phase A ef82acc4 완료로 F1(`"local"/"system"` 회귀 없음 확인), F2(`_render()` 시그니처 확장 + carry 확인) 모두 실제 코드에서 해결됨. ADR에 반영 안 됨.
- **Cross**: not flagged
- **Judgment**: Critic이 코드 라인(L233, L580-582, L277-279, L302-303, L488-489) 직접 확인. 다음 리뷰어가 이미 해결된 항목을 재검증하는 비용 발생 방지 필요. ACCEPT.
- **Action Required**: F1·F2 행에 "✅ Phase A ef82acc4 해결" 주석 추가.

---

#### 8. [ACCEPT] [Medium] F3·F4 암묵적 구현 결정 ADR 미기록
- **Critic**: F3 option-a(`domain_review_version` sha256 스냅샷, L251·L279)와 F4 option-b(체크박스 fallback, L92-119) 구현됐지만 M1~M5 표에 미기재. 의도적 선택인지 우연인지 불명확.
- **Cross**: not flagged (finding #6이 관련 부분 HOLD로 처리)
- **Judgment**: Critic이 코드 라인 직접 인용. "암묵적 결정"은 ADR의 존재 이유를 역행. ACCEPT.
- **Action Required**: M1~M5에 M6: F3→option-a (sha256 스냅샷), M7: F4→option-b (체크박스 fallback) 추가.

---

#### 9. [ACCEPT] [Medium] ADR Status `Resolved` 미갱신
- **Critic**: §후속 책임 3 "Phase A 완료 시 Resolved 갱신" 조건이 이미 충족됐으나 `Partially Resolved` 유지.
- **Cross**: not flagged
- **Judgment**: ADR 자체 텍스트("Phase A 완료 + M1~M5 결정 완료")로 조건 충족 명확. ACCEPT.
- **Action Required**: `Status: Resolved` 또는 `Status: Superseded by implementation — commit ef82acc4`로 갱신. 미완료 항목(F5, F7~F10, G1~G6 잔존 건)은 별도 follow-up ADR로 분리하거나 별도 섹션으로 명기.

---

#### 10. [HOLD] [Medium] `work_kind`/`blast_radius` canonical 출처 불명확
- **Critic**: not flagged
- **Cross**: `core/control/intake.py:94,115`에서 계산되지만 `core/project_pipeline.py:970`은 `project_brief`에서 읽음. Phase A 완료 전 연결이 완성됐는지 불명확.
- **Judgment**: Cross가 두 파일 라인 인용. `project_brief`가 `intake.normalize()` 결과로 enriched되는 경로가 검증되지 않으면 게이트가 잘못된 값을 볼 수 있음. 코드 추적 없이 판단 불가.
- **Question for Author**: `project_pipeline.py:970`에서 읽는 `project_brief`의 `work_kind`·`blast_radius`가 `ControlPlaneIntake.normalize()` 호출 이후 enriched된 값임을 confirm할 수 있는가? Phase A 완료 커밋(ef82acc4) diff에서 이 연결이 포함됐는가?

---

#### 11. [REJECT] [Low] `_DOMAIN_REVIEW_FILE` 상수가 `af.spec` hiddenimport 필요
- **Source**: Cross (G5 재검토)
- **Original Finding**: `_DOMAIN_REVIEW_FILE` 신규 상수가 PyInstaller hiddenimport 처리 필요할 수 있음.
- **Rejection Reason**: Cross 리뷰어 자신이 REJECT 판정. `_DOMAIN_REVIEW_FILE`은 새 import 가능 모듈이 아닌 기존 `core.approval_gate` 내 문자열 상수. Hiddenimport는 정적 탐색 불가 모듈에 적용, 상수에는 해당 없음. Frozen 경로 smoke test는 여전히 권장되나 `af.spec` 수정은 불필요.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | F6 `last_block_reason` ADR vs 코드 불일치 | High | ACCEPT | Critic |
| 2 | ADR 파일 M2 저장 위치 위반 | High | ACCEPT | Critic |
| 3 | `NEEDS_ADR` ADR 존재 미검증 승인 통과 | High | ACCEPT | Cross |
| 4 | Phase B 지표 1 — metadata 기록 ≠ gate 실행 증거 | High | ACCEPT | Both |
| 5 | `domain-review.md` 전체 복사 + non-`system_wide` 무시 | High | ACCEPT | Cross |
| 6 | 게이트 상태 파일 비원자적 쓰기 | High | ACCEPT | Cross |
| 7 | F1·F2 해결 상태 ADR 미기록 | Medium | ACCEPT | Critic |
| 8 | F3·F4 암묵적 결정 ADR 미기록 | Medium | ACCEPT | Critic |
| 9 | ADR Status `Resolved` 미갱신 | Medium | ACCEPT | Critic |
| 10 | `work_kind`/`blast_radius` canonical 출처 불명 | Medium | HOLD | Cross |
| 11 | `_DOMAIN_REVIEW_FILE` hiddenimport 필요 | Low | REJECT | Cross |

---

### Recommendations

구현 전 필수 (High):
- **F6 정정**: `core/approval_gate.py:238` 또는 ADR F6 표 중 하나를 canonical로 확정하고 둘을 일치시킬 것
- **`NEEDS_ADR` 계약 명시**: advisory vs enforceable 중 선택 후 ADR에 기록
- **Phase B 지표 1 교체**: `_emit_approval_event()`에 domain-gate 전용 필드(`verdict`, `outcome`, `last_block_reason`, `bypass`) 추가
- **`domain-review.md` 스코핑 정책 결정**: 현행 `system_wide`-only 의도라면 ADR + template에 명기
- **원자적 쓰기**: `core/file_io.py`에 temp+replace 헬퍼 추가 후 `approval-gate.md` 적용

ADR 문서 정정 (Medium):
- ADR 파일을 `docs/decisions/` 로 이동 (M2 소급 적용) 또는 CLAUDE.md 예외 주석 추가
- F1·F2 행에 "✅ ef82acc4 해결" 추가
- M1~M5에 M6(F3→option-a), M7(F4→option-b) 추가
- `Status: Resolved` 갱신

명확화 필요 (HOLD 해소 전 Phase B 진입 전):
- `project_pipeline.py:970`의 `project_brief`가 `ControlPlaneIntake.normalize()` 이후 enriched된 값인지 코드 경로 확인