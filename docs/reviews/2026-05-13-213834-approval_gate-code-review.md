# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-13 21:38
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

4개 High 발견 사항 — 그 중 1개는 양쪽 리뷰어가 독립 확인. Critic Finding #1은 이전 BLOCK 사이클 미반영 반복.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] 체크박스 fallback — 설계 명세 위반 + 이전 BLOCK 미반영

- **Critic**: "`checked` 분기(108-113)가 설계 명세의 `fallback 없음` 정책 위반. `re.I` 플래그가 strict 대소문자 규칙 추가 위반. 이전 BLOCK Action Required 미반영."
- **Cross**: not flagged
- **Judgment**: 코드 자체 docstring이 "없으면 `- [x] CHECKBOX` 체크박스 fallback"이라 명시해 설계와의 모순을 자증함. 설계 명세 `docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md:239-242`와 diff의 `re.M | re.I` 플래그가 직접 증거. 단일 리뷰어지만 코드+명세+이전 BLOCK 3박자 근거로 ACCEPT.
- **Action Required**: `core/approval_gate.py:108-113` (`checked` 분기 전체) 제거. `explicit` 매치 0건이면 즉시 `""` 반환.

---

#### 2. [ACCEPT] [High] `last_block_reason` 리셋 위치 오류 — 멱등 분기에서 stale 누출

- **Critic**: "멱등 auto-approve 분기(line 227 `return True`)가 실행되면 line 230의 리셋이 건너뛰어짐. 이전 차단 사유가 stale로 잔존."
- **Cross**: not flagged (도메인 게이트 활성화 경로 자체가 미연결임을 Finding #4에서 별도 지적)
- **Judgment**: diff의 `return True`(line 227)와 `self.last_block_reason = ""`(line 230) 순서가 코드에서 직접 확인됨. 이전 설계 리뷰(`docs/reviews/2026-05-13-172505-*.md:26-30`)에서 이미 Accept됐으나 미수정 — 반복 위반.
- **Action Required**: `self.last_block_reason = ""`을 `approve()` 진입 직후(line 201 이전)로 이동.

---

#### 3. [ACCEPT] [High] CLI 진입점이 도메인 게이트 차단 사유를 묵살

- **Critic**: "`agent_launcher.py:438-441`이 모든 `False` 케이스를 `"gate_file_missing"`으로 처리. `project_pipeline.py:1516`은 반환값 자체를 버림."
- **Cross**: "`agent_launcher.py:438`이 `approve()` 확장에도 불구 `last_block_reason` 미사용. 도메인 차단이 파일 미존재 오류로 오보."
- **Judgment**: 양쪽 독립 확인. diff에서 `last_block_reason` 5종 (missing_domain_frontmatter, missing_verdict, multiple_verdicts, domain_review_blocked)이 추가됐으나 production 2개 진입점 모두 이 diff 범위에서 갱신되지 않음. 설계 명세 line 99도 두 파일 갱신을 명시.
- **Action Required**: (a) `agent_launcher.py:438-441` — `os.path.exists` 분기 추가 후 `reason: gate.last_block_reason` 전달 + 도메인 경로 출력; (b) `project_pipeline.py:1516` — 반환값 체크, 도메인 차단 시 실행 중단.

---

#### 4. [ACCEPT] [High] 실제 prepare 경로가 `blast_radius` 미기록 — 도메인 게이트 비활성

- **Critic**: not flagged
- **Cross**: "`core/work_item_generator.py:1235`의 `gate.initialize()` 호출이 `work_kind`/`blast_radius` 미전달. 신규 테스트는 직접 `initialize(blast_radius='system_wide')` 호출이라 실제 prepare 경로를 커버 안 함."
- **Judgment**: cross reviewer가 `generate_work_items()` → `ProjectPipeline.prepare_documents()` 호출 체인을 구체적 파일+라인으로 추적. 실제 운영에서 도메인 게이트가 무조건 건너뛰이는 구조적 결함. 단일 리뷰어지만 증거 강도 High.
- **Action Required**: `generate_work_items()` 또는 `project_brief` 경유로 `work_kind`/`blast_radius` 전파 후 `gate.initialize(..., work_kind=..., blast_radius=...)` 호출. `generate_work_items()` 통합 테스트 추가.

---

#### 5. [ACCEPT] [Medium] `domain_review_version` 스냅샷이 `check_validity()`에서 미검증

- **Critic**: not flagged
- **Cross**: "`check_validity()`가 `_DOC_FILES`만 순회. `domain-review.md`가 승인 후 `BLOCK`으로 변경돼도 `is_execution_open()`이 True 반환."
- **Judgment**: `core/approval_gate.py:431`의 `_DOC_FILES.items()` 순회 범위가 도메인 리뷰를 미포함함을 diff에서 확인 가능. 보안적으로 승인 후 변조 탐지 목적의 해시 저장을 실행 시점에 재검증하지 않으면 감사 추적 기능이 사실상 무효.
- **Action Required**: `check_validity()` 또는 `is_execution_open()`에서 `blast_radius == "system_wide"` 시 `domain-review.md` 해시 재검증 + verdict 재파싱 추가.

---

#### 6. [ACCEPT] [Medium] `"MULTIPLE"` 반환값이 설계 명세 타입 계약 위반

- **Critic**: "설계 명세는 `Literal['PASS','NEEDS_ADR','BLOCK','']`. `"MULTIPLE"` 노출이 호출자 결합도 증가."
- **Cross**: not flagged (Cross Finding #4 reject는 `_parse()` 내 `domain_review_version` 파싱 문제로 별개)
- **Judgment**: diff line 106 `return "MULTIPLE"`, line 112 `return "MULTIPLE"` 직접 확인. 설계 명세 타입과 불일치. 단, `approve()`에 이미 `if verdict == "MULTIPLE"` 분기가 존재해 현재는 기능적으로 처리됨 — 타입 계약 문제는 실 장애 아닌 설계 오염. Medium 유지.
- **Action Required**: `_read_domain_review_verdict` docstring 반환 타입을 `str`(no Literal)로 수정 **또는** `"MULTIPLE"` 케이스를 `""` + `last_block_reason` 세팅으로 합쳐 설계 명세와 정합.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 체크박스 fallback 설계 명세 위반 | High | ACCEPT | Critic |
| 2 | `last_block_reason` 리셋 위치 오류 | High | ACCEPT | Critic |
| 3 | CLI 진입점 도메인 차단 사유 묵살 | High | ACCEPT | Both |
| 4 | prepare 경로 `blast_radius` 미기록 | High | ACCEPT | Cross |
| 5 | `domain_review_version` 미검증 | Medium | ACCEPT | Cross |
| 6 | `"MULTIPLE"` 타입 계약 위반 | Medium | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 필수 (merge 전)**:
  1. `core/approval_gate.py:108-113` `checked` 분기 전체 제거
  2. `self.last_block_reason = ""` 리셋을 `approve()` 진입 직후로 이동
  3. `agent_launcher.py:438-441` — `last_block_reason` 분기 + 도메인 경로 출력
  4. `core/project_pipeline.py:1516` — `approve()` 반환값 체크 + 차단 시 중단
  5. `core/work_item_generator.py:1235` — `work_kind`/`blast_radius` 전파
- **후속 수정 권고**:
  - `check_validity()` 도메인 해시 재검증 추가 (Finding #5)
  - `_read_domain_review_verdict` 타입 계약 정리 (Finding #6)
- **테스트 갭**: `generate_work_items()` → `prepare_documents()` 통합 경로 테스트, 멱등 분기 후 `last_block_reason` 시퀀스 테스트 추가 필요.