# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 15:59
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

BLOCK 트리거: Critical 1건 (non-atomic write × 3) + High 4건. 최소 1~4번을 수정해야 merge 가능.

---

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Critical] Non-atomic 파일 쓰기 — M10 패턴 3회 신규 추가
- **Critic**: "`_emit_evidence_files` / `_emit_coverage_report` 에서 `.write_text()` 직접 사용 3회. 크래시 시 파일 손상. M10 안티패턴."
- **Cross**: "not flagged"
- **Judgment**: 코드 증거 명확. L646/700/723 세 군데 모두 최종 경로에 직접 쓴다. 기존 `code-review.md` M10에 이미 등재된 anti-pattern이 신규 코드에서 반복됨.
- **Action Required**: `tempfile.NamedTemporaryFile` → `os.replace()` 패턴으로 교체. `core/file_io.py`에 atomic write 헬퍼가 있으면 재사용.

---

#### 2. [ACCEPT] [High] `sufficient` 플래그가 웹 복구를 반영하지 못함
- **Critic**: "`_is_sufficient(local_refs, ...)` 호출 시 `web_refs` 누락 → recovery loop 후에도 `sufficient` 영원히 `False`."
- **Cross**: "not flagged (Cross #1/2와 관련 영역이지만 이 구체적 버그는 독립적으로 식별 안 됨)"
- **Judgment**: `_is_sufficient` 시그니처 (`L726-731`)에 `web_refs` 파라미터 없음을 diff에서 확인. `web_refs.extend(...)` 후에도 다음 iteration에서 `local_refs` 만 평가 → `sufficient = True` 불가. 증거 강함.
- **Action Required**: `_is_sufficient(local_refs + web_refs, task_input, domain_checklist=_domain_checklist)` 로 변경, 또는 루프 탈출 조건을 `_identify_unmet_gaps(...)` 결과 기반으로 교체.

---

#### 3. [ACCEPT] [High] `_domain_checklist`가 `requires_web` 경로에서 로드되지 않음
- **Critic**: "not flagged"
- **Cross**: "`_domain_checklist`는 `else` 분기(L923)에서만 할당. `deep_source_research` / `fresh_lookup` / `live_project_analysis`는 `requires_web=True` → `else` 진입 안 함 → manifest 항상 `None`. poker.yaml 커버리지 기능 완전 무력화."
- **Judgment**: diff 에서 `_domain_checklist` 초기화가 `else:` 블록 안 `L923` 에만 있음을 확인. `ResearchRouter._select_mode()` 가 deep 모드에서 `requires_web=True` 를 설정한다는 Cross의 지적도 코드에서 검증 가능. 증거 강함.
- **Action Required**: `research_plan` 확정 직후, 분기 dispatch 이전에 `_domain_checklist = self._load_domain_manifest(research_plan.domain)` 를 이동. 모든 경로에서 동일하게 사용.

---

#### 4. [ACCEPT] [High] `_identify_unmet_gaps` — 대소문자 처리 불완전 → 거짓 양성
- **Critic**: "`item.replace('_', ' ')` 에 `.lower()` 누락 → `joined`(소문자)와 불일치 → 항상 'unmet' 판정."
- **Cross**: "not flagged"
- **Judgment**: `joined = ...lower()` 인데 첫 번째 비교 `item.replace("_", " ")` 은 원본 대소문자 유지. `item = "Source_Quality"` → `"Source Quality" not in joined` = True (소문자 `joined`에 대문자 없음). 두 번째 조건 `item.lower() = "source_quality"` 도 underscore 미제거로 매칭 실패. AND 조건이므로 두 조건 모두 True → 항상 unmet. 증거 명확.
- **Action Required**: `item.lower().replace("_", " ") not in joined` 단일 조건으로 교체.

---

#### 5. [ACCEPT] [High] 에스컬레이션 재귀 호출 시 도메인 정보 유실
- **Critic**: "not flagged"
- **Cross**: "`collect_project_evidence()` 의 recursive retry (L1031)에 `research_plan` 미전달 → 재시도 경로에서 `prev_domain = ''` → manifest 로드 불가."
- **Judgment**: Cross가 `core/research_router.py:216`, `core/researcher.py:1031-1037`, `core/research_verifier.py:344` 세 곳의 경계를 명시. 재귀 호출 시 `research_plan` 파라미터가 없으면 `ResearchPlan.for_mode()` 가 새 plan 생성 → domain 소실. 단일 리뷰어지만 구체적 line 증거 강함.
- **Action Required**: 재귀 호출에 현재 `research_plan` 전달, 또는 `for_mode()` 이후 domain 재탐지 추가.

---

#### 6. [ACCEPT] [Medium] 테스트가 실제 프로덕션 호출 경로를 커버하지 않음
- **Critic**: "not flagged"
- **Cross**: "`test_research_p1_quality_gate.py:122-137` 는 실제 `collect_project_evidence()` 대신 simplified mock 루프 사용. L221 `domain=''` → manifest loss 탐지 불가."
- **Judgment**: 테스트가 위 1~5번 버그를 회귀로 잡지 못한다는 의미. Cross의 테스트 라인 지목이 구체적이고 검증 가능.
- **Action Required**: `ResearchPlan(domain="poker", requires_web=True, mode="deep_source_research")` 로 `collect_project_evidence()` 를 직접 호출하는 통합 테스트 추가. escalation 후 `research_plan.domain` 유지 여부 assertion 포함.

---

#### 7. [ACCEPT] [Medium] `Path(__file__)` — frozen 빌드 비호환
- **Critic**: "`_load_domain_manifest` (L598) + `_emit_coverage_report` (L674) 에서 `Path(__file__)` 사용. PyInstaller frozen 빌드에서 경로 불일치. `af.spec datas` 에 `config/coverage_manifests` 미등록 시 manifest 항상 `None`."
- **Cross**: "not flagged"
- **Judgment**: `code-review.md §2.12` 에 이미 기재된 known pattern. diff에서 두 곳 신규 도입 확인. 단일 리뷰어지만 기존 문서 근거로 ACCEPT.
- **Action Required**: `config_paths.py` 의 `PROJECT_ROOT` 상수 사용 또는 `sys._MEIPASS` fallback 추가. `af.spec datas` 에 `("config/coverage_manifests", "config/coverage_manifests")` 등록.

---

#### 8. [ACCEPT] [Medium] `_emit_*` 메서드의 `os.getcwd()` 불일치
- **Critic**: "`_emit_evidence_files`/`_emit_coverage_report` 가 `os.getcwd()` 직접 사용. 다른 경로(L889)는 `AGENT_PROJECT_ROOT` 환경변수 우선 사용."
- **Cross**: "not flagged"
- **Judgment**: diff L889 `os.getenv("AGENT_PROJECT_ROOT") or os.getcwd()` vs L638/697 `os.getcwd()` 직접 사용 — 동일 클래스 내 불일치. 단일 리뷰어지만 코드 내 모순으로 증거 충분.
- **Action Required**: `out_dir = Path(os.getenv("AGENT_PROJECT_ROOT") or os.getcwd()) / "docs" / "research"` 로 일관화.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Non-atomic 파일 쓰기 × 3 | Critical | ACCEPT | Critic |
| 2 | `sufficient` 웹 복구 반영 안 됨 | High | ACCEPT | Critic |
| 3 | `_domain_checklist` web 경로 미로드 | High | ACCEPT | Cross |
| 4 | `_identify_unmet_gaps` 대소문자 버그 | High | ACCEPT | Critic |
| 5 | 재귀 retry 도메인 유실 | High | ACCEPT | Cross |
| 6 | 테스트 프로덕션 경로 미커버 | Medium | ACCEPT | Cross |
| 7 | `Path(__file__)` frozen 빌드 불호환 | Medium | ACCEPT | Critic |
| 8 | `os.getcwd()` 불일치 | Medium | ACCEPT | Critic |

---

### Recommendations

**Merge 전 필수 (BLOCK 해소):**
1. `_emit_evidence_files` / `_emit_coverage_report` — `.write_text()` 3곳을 `.tmp` → `os.replace()` 로 교체 (#1)
2. Recovery loop — `_is_sufficient(local_refs + web_refs, ...)` 로 수정 (#2)
3. `_domain_checklist` 로드를 분기 이전으로 이동 (#3)
4. `_identify_unmet_gaps` — `item.lower().replace("_", " ") not in joined` 단일 조건으로 수정 (#4)
5. 재귀 `collect_project_evidence()` 호출 시 `research_plan` 전달 (#5)

**Merge 후 권장 (WARN):**
6. poker 도메인 통합 테스트 추가 — `collect_project_evidence()` 직접 호출, escalation 후 domain 유지 assertion (#6)
7. `Path(__file__)` → `PROJECT_ROOT` 상수 + `af.spec datas` 등록 (#7)
8. `os.getcwd()` → `AGENT_PROJECT_ROOT` 우선 사용으로 일관화 (#8)