# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 16:40
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

High 결함 5개 확인. BLOCK 해제 전 모두 수정 필요.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] `os.getcwd()` 하드코딩 — workspace 무시
- **Critic**: `_emit_evidence_files`/`_emit_coverage_report` 두 함수 모두 `Path(os.getcwd()) / "docs" / "research"` 사용. `workspace` 파라미터 없음.
- **Cross**: `ProjectPipeline`이 `collect_project_evidence(task_input, workspace=target_workspace)`로 호출하지만, 아티팩트는 프로세스 cwd에 기록됨. 증거: `core/project_pipeline.py:641-656`.
- **Judgment**: 양쪽 모두 코드 증거와 함께 ACCEPT. 두 함수 시그니처에 `workspace` 파라미터가 없는 것이 diff에서 명확히 확인됨.
- **Action Required**: `_emit_evidence_files(self, slug, web_refs, structured_evidence, workspace)` 및 `_emit_coverage_report(..., workspace)` 추가. 내부 `out_dir = Path(workspace) / "docs" / "research"` 로 변경. 호출부 `collect_project_evidence()` 에서 `workspace` 전달.

---

#### 2. [ACCEPT] [High] 클레임 source_id 불일치 — `web_001` vs `S001`
- **Critic**: 미감지.
- **Cross**: `_build_source_pack()`은 `web_001` ID를 생성하고 프롬프트도 이 ID 사용. `_emit_evidence_files()`는 `S001`로 재명명. LLM이 `{"source_ids": ["web_001"]}`을 반환하면 persist된 `sources` 배열에 매칭 source가 없음. 증거: `core/researcher.py:407`, `505`, `640`, `655`.
- **Judgment**: 단일 리뷰어지만 코드 증거가 명확. diff에서 `:640` 라인 `S{i:03d}` 와 `:655` 라인의 `llm_source_ids[0]` 보존이 충돌함.
- **Action Required**: persist 시 `source_pack`의 원본 ID(`web_001`)를 그대로 사용하거나, emit 전에 claim의 `source_ids`를 `web_001 → S001` 매핑으로 재작성.

---

#### 3. [ACCEPT] [High] `_identify_unmet_gaps` vs `_emit_coverage_report` 매칭 불일치
- **Critic**: `_identify_unmet_gaps`는 `item.replace("_", " ")` 단순 문자열 매칭; `_emit_coverage_report`는 `match_keywords` dict 동의어 매칭. 동일 필드가 gap 판단에서는 "미충족"이고 coverage report에서는 "matched"가 되는 불일치 발생. 이전 라운드 BLOCK #2 — 미수정.
- **Cross**: 미감지.
- **Judgment**: 단일 리뷰어지만 diff에서 두 함수의 로직 차이가 명확히 드러남. RecoveryLoop 트리거 오발화 → 불필요한 Tavily 호출 → 최종 report는 matched 기록. 기능적 버그.
- **Action Required**: 공유 헬퍼 `_is_field_matched(field, match_keywords, joined) -> bool` 추출. 두 함수 모두 이 헬퍼 사용.

---

#### 4. [ACCEPT] [High] `Path(__file__)` — frozen 빌드 호환성 파괴
- **Critic**: `dist/af.exe` 실행 시 `__file__ = _MEIPASS/core/researcher.pyc`. `parent.parent = _MEIPASS/`. `config/coverage_manifests/`는 `af.spec` `datas`에 미등록 → 매니페스트 항상 `None` 반환 → coverage gate 전부 묵음. AF checklist 항목.
- **Cross**: 미감지.
- **Judgment**: AF-specific 빌드 환경 지식이 필요한 결함. `af.spec`에 `datas` 미등록 사실은 diff 밖에서 검증 가능. 빌드 환경 특수성으로 단일 리뷰어 ACCEPT 처리.
- **Action Required**: `config_paths.py`의 `PROJECT_ROOT` 상수 사용 (이미 frozen/source 분기 처리됨). 또는 `af.spec` `datas`에 `("config/coverage_manifests", "config/coverage_manifests")` 추가. 두 수정 모두 적용 권장.

---

#### 5. [ACCEPT] [High] Router 재귀 호출 시 domain 유실
- **Critic**: 미감지.
- **Cross**: `detect_complexity_gaps()` 트리거 시 재귀 호출이 `research_plan=research_plan` 생략. `prev_domain = ""` fallback → `_domain_checklist = None` → coverage manifest 비활성화. 증거: `core/researcher.py:1037-1043`, `886`, `1049-1052`.
- **Judgment**: 단일 리뷰어지만 호출 경로가 diff 내에서 확인 가능. domain이 유실되면 B3~B5 전체가 무력화됨.
- **Action Required**: 재귀 호출에 `research_plan=research_plan` 전달. 또는 재귀 진입 전 `prev_domain = research_plan.domain if research_plan else ""` 보존.

---

#### 6. [ACCEPT] [Medium] RecoveryLoop 무제한 Tavily API 호출
- **Critic**: checklist N개 항목 전부 unmet 시 N × `_max_rounds` 회 호출. 예: `poker.yaml` 8항목 deep = 24회. 예산 캡 없음.
- **Cross**: 미감지.
- **Judgment**: 단일 리뷰어. diff에서 `for gap in _unmet:` 루프가 캡 없이 전체 unmet을 순회하는 것이 명확.
- **Action Required**: `_unmet[:3]` 또는 누적 `web_refs` 크기 상한 설정 (예: `len(web_refs) >= 12` 시 탈출).

---

#### 7. [ACCEPT] [Medium] Non-atomic 파일 쓰기 — coverage report는 block gate 신호
- **Critic**: `block: true/false` 값이 work-item 생성 게이트 신호. 부분 쓰기 후 크래시 시 잘못된 gate 통과 가능. M10 패턴 반복.
- **Cross**: 미감지.
- **Judgment**: 단일 리뷰어. code-review.md M10 패턴으로 문서화된 기존 알려진 위험. coverage report가 게이트 신호라는 점에서 Medium 유지.
- **Action Required**: `tempfile.NamedTemporaryFile` + `os.replace()` 패턴 적용 (`_emit_coverage_report` / `_emit_evidence_files` 모두).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `os.getcwd()` workspace 무시 | High | ACCEPT | Both |
| 2 | 클레임 source_id 불일치 (`web_001` vs `S001`) | High | ACCEPT | Cross |
| 3 | gap 매칭 로직 불일치 | High | ACCEPT | Critic |
| 4 | `Path(__file__)` frozen 빌드 파괴 | High | ACCEPT | Critic |
| 5 | 재귀 호출 시 domain 유실 | High | ACCEPT | Cross |
| 6 | RecoveryLoop 무제한 Tavily 호출 | Medium | ACCEPT | Critic |
| 7 | Non-atomic 파일 쓰기 (M10) | Medium | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 (BLOCK 해제 조건, #1~5)**:
  - `_emit_evidence_files` / `_emit_coverage_report`에 `workspace` 파라미터 추가 (#1)
  - claim source_id persist 전 `web_001 → S{i:03d}` 재매핑 또는 원본 ID 유지 (#2)
  - `_is_field_matched()` 공유 헬퍼 추출로 gap/coverage 매칭 일원화 (#3)
  - `config_paths.PROJECT_ROOT` 사용 + `af.spec` datas 등록 (#4)
  - 재귀 호출에 `research_plan=research_plan` 전달 (#5)
- **권장 수정 (WARN, 별도 커밋 허용)**:
  - RecoveryLoop per-round 호출 상한 추가 (#6)
  - coverage report/evidence 쓰기 atomic 처리 (#7)
- **테스트 갭**: 현재 테스트는 artifact 생성만 검증. workspace 배치 정합성 및 claim↔source ID 참조 무결성 assertion 추가 필요 (Cross Review 확인).