# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-13 21:44
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High findings exist that leave the domain gate non-functional in production, but no critical (security/crash) issues are introduced.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] 유일한 호출자 미갱신 — 도메인 게이트 프로덕션에서 영구 비활성

- **Critic**: `project_pipeline.py:963-970`이 `work_kind`/`blast_radius`를 전달하지 않아 두 파라미터가 `""` 기본값으로 고정 → `approval_gate.py:233` 도메인 게이트 조건 절대 활성화 불가.
- **Cross**: `generate_work_items()`가 `work_kind`/`blast_radius`를 forward하지만 실제 호출부가 여전히 omit. `ControlPlaneIntake.normalize()`가 `NormalizedRequest.work_kind` / `change_impact.blast_radius`를 `core/control/intake.py:69-132`에서 생성하나, `prepare_documents()`가 이를 호출하지 않음.
- **Judgment**: 양쪽이 동일 결함을 독립적으로 확인. 파라미터 추가는 완료됐으나 연결 경로가 없어 dead feature 상태. diff 자체는 회귀를 추가하지 않지만, 기능이 "추가됐다"고 간주되면 즉시 broken.
- **Action Required**: `ProjectPipeline.prepare_documents()` 또는 `PreparedBrief`에서 `work_kind`/`blast_radius`를 추출해 `generate_work_items()` 호출부에 전달. 파이프라인 레벨 테스트에서 생성된 `approval-gate.md`에 `blast_radius: system_wide`가 포함되는지 검증.

---

#### 2. [ACCEPT] [High] `system_wide` 경로에서 `domain-review.md` 미생성

- **Critic**: 미지적.
- **Cross**: `blast_radius="system_wide"` 경로가 활성화되면 `approval_gate.py:233-239`가 `domain-review.md` 부재 시 approve를 block하나, `generate_work_items()`는 `_copy_extra_templates()`에서 해당 파일을 복사하지 않음. 기존 테스트들은 `domain-review.md`를 수동 생성해 우회하므로 generated path 미커버.
- **Judgment**: Finding #1이 수정되어 `blast_radius="system_wide"`가 실제로 전달되면 즉시 approve block 발생. 단일 reviewer지만 `approval_gate.py:233-239` 코드 증거가 명확하고 Finding #1과 동일 end-to-end 경로의 후속 결함.
- **Action Required**: `_copy_extra_templates()` 또는 gate 초기화 경로에서 `blast_radius == "system_wide"` 시 `domain-review.md` 템플릿 포함. `generate_work_items(..., blast_radius="system_wide")` 호출 테스트 추가.

---

#### 3. [ACCEPT] [Medium] `blast_radius` 값 미검증 — silent pass 가능

- **Critic**: `"SYSTEM_WIDE"`, `"system wide"` 등 오타·대소문자 차이 시 `approval_gate.py:233`의 완전 일치 조건을 통과하지 못해 silent miss 발생.
- **Cross**: 미지적.
- **Judgment**: Finding #1·#2 수정 후 실제 값이 전달되는 시점에 surface. `_clean()` 결과가 lower-case 보장 여부 불명확. 단일 reviewer지만 silent failure 패턴으로 증거 충분.
- **Action Required**: `gate.initialize()` 진입 시 `blast_radius`를 허용 값 집합(`{"", "module", "system_wide", ...}`)으로 검증하거나, `_clean()` 내에 `.lower()` 추가.

---

### Confirmed Non-Issues

| Finding | Verdict |
|---------|---------|
| Keyword-only signature extension (`*` 구분자) | PASS — 양쪽 모두 하위 호환성 이상 없음 확인 |
| `ApprovalGate.initialize()` 시그니처 미스매치 우려 | PASS — Cross가 `approval_gate.py:156-175` 및 `603-607` 코드로 반증, 34 tests passed |

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 유일한 호출자 미갱신 (도메인 게이트 비활성) | High | ACCEPT | Both |
| 2 | system_wide 경로 domain-review.md 미생성 | High | ACCEPT | Cross |
| 3 | blast_radius 값 미검증 (silent pass) | Medium | ACCEPT | Critic |

---

### Recommendations

- **Finding #1 우선**: `project_pipeline.py:963-970` 호출부에 `work_kind`/`blast_radius` 전달 경로 추가 — 이게 없으면 #2·#3 수정은 모두 dead code.
- **Finding #2 연동**: #1 수정과 같은 PR에서 `_copy_extra_templates()` 수정 및 `blast_radius="system_wide"` 통합 테스트 추가.
- **Finding #3 방어**: `gate.initialize()` 또는 `_clean()` 에 입력값 정규화(`lower()`) 추가 — #1·#2 수정과 묶어 한 커밋으로 처리 권장.
- 기존 잔존 이슈(`approval_gate.py:108-113` checked 분기 fallback, `last_block_reason` 리셋 위치 오류)는 이번 diff 범위 밖이나, 도메인 게이트 end-to-end 복원 시 함께 검토 권장.