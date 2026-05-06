# Design Review: 2026-05-04-af-research-quality-gate-design

> Source: docs/2026-05-04-af-research-quality-gate-design.md
> Date: 2026-05-04 23:44
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

Cross Review가 provider 오류로 실패했으므로 Critic Review 단독 기반으로 집계합니다.

---

## Final Design Review

### Verdict: BLOCK

**근거**: Critical 2건 포함. Cross Review는 provider 오류(OpenAI Codex 세션 초기화 실패)로 응답 없음 — Critic Review 단독 적용. Critical 1건 이상 → BLOCK.

---

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Critical] §5.3 C1 pseudocode — `prepare_documents()` 시그니처와 충돌

- **Critic**: `prepare_documents()`는 `prepared_brief: PreparedBrief`를 인자로 받는다(L750-755). 문서 pseudocode는 내부에서 `research_project_brief()`를 재호출 — 구현 즉시 실패.
- **Cross**: provider 오류로 미확인
- **Judgment**: Critic이 L750-755 코드 직접 인용. 이전 BLOCK의 Action Required도 미반영. 증거 충분 → ACCEPT.
- **Action Required**: §5.3 C1 pseudocode를 `prepare_brief()` 반환 직전(L722~734 블록) 또는 `prepare()` 래퍼 레벨로 재배치. `brief` → `project_brief = prepared_brief.project_brief`로 접근 수정. §11.4에 `prepare_brief (L591 또는 현재 실제 위치)` 행 추가.

---

#### 2. [ACCEPT] [Critical] §5.1 A5 — `external_stack_score` 접근 경로 미명시 (AttributeError 위험)

- **Critic**: `external_stack_score`는 `ResearchPlan` 필드가 아닌 `scores["external_stack_score"]` dict 키. 구현자가 `research_plan.external_stack_score`로 접근하면 `AttributeError`.
- **Cross**: provider 오류로 미확인
- **Judgment**: Critic이 L78-88 `ResearchPlan` dataclass 구조 확인 후 판정. 잘못된 접근 경로는 런타임 오류 보장 → ACCEPT.
- **Action Required**: §5.1 A5 파생 로직을 `plan()` 내부 `_select_mode(scores)` 반환 직후로 명시. 예시: `requires_research = primary in (...) or scores.get("external_stack_score", 0) >= 2`. `scores` dict 접근 경로를 pseudocode에 명시.

---

#### 3. [ACCEPT] [High] §5.2 B1 — `unmet` 변수 미초기화 (NameError)

- **Critic**: 첫 회차에서 `sufficient=True`로 즉시 break 시 `unmet`가 정의된 적 없어 반환문에서 `NameError`.
- **Cross**: provider 오류로 미확인
- **Judgment**: 표준 Python 스코프 오류. pseudocode lines 359-376 인용으로 충분한 증거 → ACCEPT.
- **Action Required**: 루프 진입 전 `unmet: list[str] = []` 초기화 추가. §5.2 B1 pseudocode에 반영.

---

#### 4. [ACCEPT] [High] §5.1 A4 — `_is_sufficient` 호출처 목록 누락

- **Critic**: `domain_checklist` 매개변수 추가는 후방 호환이나, `collect_project_evidence()` 내 호출처 및 기타 경로 목록이 없어 구현자가 누락 위험.
- **Cross**: provider 오류로 미확인
- **Judgment**: 시그니처 변경 시 호출처 전수 확인은 표준 절차. §5.1 A4에 목록 부재 → ACCEPT.
- **Action Required**: §5.1 A4에 "`_is_sufficient` 호출처 전체 목록" 항목 추가. grep: `_is_sufficient` 검색 결과를 문서에 명시.

---

#### 5. [ACCEPT] [High] §5.3 C1 — `ResearchGateBlocked` 예외 정의 위치·frozen 빌드 미명시

- **Critic**: 예외 클래스 정의 파일 미명시. `af.spec hiddenimports` 업데이트 계획 없음. 호출 스택에서 catch 지점 없으면 raw traceback 노출.
- **Cross**: provider 오류로 미확인
- **Judgment**: CLAUDE.md 빌드 규칙("새 core/*.py 파일은 af.spec hiddenimports에 추가 필수") 위반. 증거 명확 → ACCEPT.
- **Action Required**: `ResearchGateBlocked` 정의 파일(신규 `core/exceptions.py` 또는 기존 위치) 명시. `af.spec hiddenimports` 업데이트 계획을 §5 또는 §8에 추가. caller 레벨 catch 지점과 사용자 노출 메시지 명세.

---

#### 6. [ACCEPT] [Medium] §5.2 B3 — `yaml` frozen 빌드 의존성 누락

- **Critic**: `requirements.txt`에만 추가해도 PyInstaller frozen 빌드에서 `af.spec hiddenimports`에 없으면 런타임 `ModuleNotFoundError`.
- **Cross**: provider 오류로 미확인
- **Judgment**: CLAUDE.md 빌드 규칙과 직결. R6가 "grep 검증 후 결정"이라 했으나 spec 업데이트 의무는 조건 없음 → ACCEPT.
- **Action Required**: R6에 `af.spec hiddenimports += ["yaml"]` 명시. 또는 stdlib `json` 대체로 의존성 제거(Simplicity First 원칙 부합 — 권장).

---

#### 7. [ACCEPT] [Medium] §5.1 A6 — 이미 구현 완료된 항목을 변경 항목으로 기술

- **Critic**: `project_pipeline.py` L726-733에 `slug_from_brief()` 호출 이미 존재. 구현자가 중복 코드를 추가할 위험.
- **Cross**: provider 오류로 미확인
- **Judgment**: Critic이 L728 직접 확인. 혼란 방지 관점에서 문서 정정 필요 → ACCEPT.
- **Action Required**: §5.1 A6를 "이미 `project_pipeline.py` L726-733 구현 완료 — 검증만 필요" 항목으로 격하. P0 체크리스트에서 구현 항목 제거.

---

#### 8. [ACCEPT] [Medium] §11.4 — `prepare_brief` 진입점 누락 (이전 BLOCK 미반영)

- **Critic**: 이전 BLOCK Action Required(`prepare_brief (L591)` §11.4 추가)가 여전히 미반영.
- **Cross**: provider 오류로 미확인
- **Judgment**: C1 게이트 재배치와 직결. §11.4 없으면 구현자가 틀린 함수를 수정할 위험 → Finding 1과 묶어 ACCEPT.
- **Action Required**: Finding 1의 Action Required와 통합 — `prepare_brief` 실제 위치 grep 후 §11.4에 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §5.3 C1 pseudocode — `prepare_documents()` 시그니처 충돌 | Critical | ACCEPT | Critic |
| 2 | §5.1 A5 — `external_stack_score` AttributeError 위험 | Critical | ACCEPT | Critic |
| 3 | §5.2 B1 — `unmet` 미초기화 NameError | High | ACCEPT | Critic |
| 4 | §5.1 A4 — `_is_sufficient` 호출처 목록 누락 | High | ACCEPT | Critic |
| 5 | §5.3 C1 — `ResearchGateBlocked` 정의 위치·frozen 빌드 미명시 | High | ACCEPT | Critic |
| 6 | §5.2 B3 — `yaml` frozen 빌드 의존성 누락 | Medium | ACCEPT | Critic |
| 7 | §5.1 A6 — 이미 구현된 항목을 변경 항목으로 기술 | Medium | ACCEPT | Critic |
| 8 | §11.4 — `prepare_brief` 진입점 누락 | Medium | ACCEPT | Critic |

---

### Recommendations

구현 착수 전 문서에서 수정할 사항:

1. **§5.3 C1 pseudocode 재배치** (Critical) — `prepare_documents()` 내부 → `prepare_brief()` L722~734 블록 또는 `prepare()` 래퍼로 이동. `brief` 접근 경로 수정.
2. **§5.1 A5 파생 로직 경로 명시** (Critical) — `plan()` 내부에서 `scores.get("external_stack_score", 0)` 형태로 접근함을 pseudocode에 표기.
3. **§5.2 B1 `unmet` 초기화 추가** (High) — 루프 진입 전 `unmet: list[str] = []` 한 줄.
4. **`ResearchGateBlocked` 정의 파일 및 `af.spec` 계획 추가** (High) — §5 또는 §8에 빌드 영향 섹션 신설.
5. **§5.1 A4 호출처 목록 추가** (High) — grep 결과 인라인 표기.
6. **`yaml` 의존성 처리 방침 확정** (Medium) — stdlib 대체 또는 `af.spec` 업데이트 명시.
7. **§5.1 A6 상태 정정** (Medium) — "구현 완료, 검증만" 으로 격하.
8. **§11.4 `prepare_brief` 행 추가** (Medium) — Finding 1과 동시 처리.

**Cross Review 재실행**: codex 회복 후(§0 참조: 2026-05-05 15:37 KST↑) 반드시 cross-review fan-out 1회 추가 실행. 현재 Critic 단독 판정은 단일 관점 리스크 있음.