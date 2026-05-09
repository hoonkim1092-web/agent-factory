# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 15:21
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

> Cross Review timed out (600s). Aggregation is based solely on the Critic Review. Single-source findings with strong code evidence are ACCEPT; weak-evidence findings are HOLD.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `sufficient` 플래그가 웹 복구 성공을 반영하지 못함

- **Critic**: `_is_sufficient(local_refs, ...)` 가 `web_refs` 를 인자로 받지 않아, loop 내에서 web_refs 에 갭이 채워져도 `sufficient` 는 절대 `True` 전환 불가
- **Cross**: timed out — not flagged
- **Judgment**: 코드 증거가 명확하다. `researcher.py:926` 의 루프에서 `web_refs.extend(...)` 로 결과를 쌓지만, 다음 iteration 의 `self._is_sufficient(local_refs, task_input, ...)` 는 `local_refs` 만 검사한다. 웹 복구가 성공해도 `sufficient` 는 `False` 유지 → `initial_evidence["sufficiency_gate_passed"]` 항상 `False`.
- **Action Required**: `_is_sufficient` 시그니처에 `web_refs` 추가 또는 루프 탈출 조건을 `len(self._identify_unmet_gaps(local_refs, web_refs, _domain_checklist)) == 0` 으로 교체.

---

#### 2. [ACCEPT] [High] Non-atomic 파일 쓰기 — 기존 M10 패턴 반복

- **Critic**: `_emit_evidence_files` (line 661) 와 `_emit_coverage_report` (line 712–723) 에서 `write_text()` 직접 호출. 쓰기 도중 프로세스 종료 시 파일 부분 기록 가능. `_emit_coverage_report` 는 JSON + MD 두 파일을 비원자적으로 연속 쓰기 — 두 파일 간 불일치 발생 가능.
- **Cross**: timed out — not flagged
- **Judgment**: `code-review.md §3.3 M10` 에 동일 패턴이 이미 등재된 알려진 결함이며, 이 변경이 새 코드 경로에 동일 패턴을 추가한다. 코드 증거 명확.
- **Action Required**:
  ```python
  import tempfile, os
  with tempfile.NamedTemporaryFile("w", dir=out_dir, delete=False,
                                   suffix=".tmp", encoding="utf-8") as f:
      f.write(json.dumps(report, indent=2, ensure_ascii=False))
      tmp = f.name
  os.replace(tmp, out_dir / f"{slug}-coverage.json")
  ```
  `_emit_coverage_report` 의 JSON → MD 쓰기 순서도 동일하게 원자적으로 처리.

---

#### 3. [ACCEPT] [High] `__file__` 사용 — frozen 빌드 비호환

- **Critic**: `_load_domain_manifest` (line 604) 와 `_emit_coverage_report` (line 680) 에서 `Path(__file__).parent.parent / "config" / "coverage_manifests"` 사용. `af.spec` `datas` 에 해당 경로 미포함 → frozen 빌드에서 경로가 존재하지 않아 `path.exists()` 체크에서 `None` 반환, B3/B5 기능 전체 무음 비활성화.
- **Cross**: timed out — not flagged
- **Judgment**: `dynamic_orchestrator.py:567-571` 에 동일 유형 v3 미해결 이슈가 이미 존재하며, 이 변경이 `researcher.py` 에 같은 클래스의 문제를 추가한다. frozen 빌드 경로는 `_MEIPASS` 기반이므로 `__file__` 직접 사용은 항상 위험.
- **Action Required** (둘 중 하나 선택):
  - `config_paths.py` 의 `PROJECT_ROOT` 상수 사용 + `af.spec` 에 `datas=[("config/coverage_manifests", "config/coverage_manifests")]` 추가
  - 또는 manifest 경로를 생성자 주입으로 처리하여 `__file__` 의존 제거

---

#### 4. [ACCEPT] [Medium] `_identify_unmet_gaps` 대소문자 처리 버그

- **Critic**: `joined` 는 `.lower()` 처리된 소문자인데 `item.replace("_", " ")` 는 원본 대소문자 유지. `"API_Rate_Limit"` 같은 항목이 커버됐어도 항상 unmet 판정.
- **Cross**: timed out — not flagged
- **Judgment**: 코드 증거 명확. `item.replace("_", " ") not in joined` 에서 joined 가 소문자이므로 대문자 포함 항목은 항상 `True`. 동작 버그로 단독 판정 ACCEPT.
- **Action Required**: `researcher.py:626` 조건을 단일 조건으로 교체:
  ```python
  return [item for item in checklist if item.replace("_", " ").lower() not in joined]
  ```

---

#### 5. [ACCEPT] [Low] 동일 YAML manifest 3회 파일 I/O

- **Critic**: `collect_project_evidence()` 단일 호출 내 `_load_domain_manifest` 2회 + `_emit_coverage_report` 내부 1회 = 최대 3회 파일 읽기+파싱, 캐싱 없음.
- **Cross**: timed out — not flagged
- **Judgment**: Finding 3 (`__file__` 이슈) 가 해결되면 자연스럽게 캐싱도 함께 처리할 수 있는 Low 우선순위 사항. 코드 증거 명확, 단독 ACCEPT.
- **Action Required**: `_load_domain_manifest` 에 `@functools.lru_cache(maxsize=8)` 추가 또는 `_domain_checklist` 와 `match_keywords` 를 상위 스코프에서 한 번만 로드해 `_emit_coverage_report` 에 인자로 전달.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `sufficient` 플래그 웹 복구 미반영 | High | ACCEPT | Critic |
| 2 | Non-atomic 파일 쓰기 (M10 반복) | High | ACCEPT | Critic |
| 3 | `__file__` frozen 빌드 비호환 | High | ACCEPT | Critic |
| 4 | `_identify_unmet_gaps` 대소문자 버그 | Medium | ACCEPT | Critic |
| 5 | YAML manifest 3회 중복 로드 | Low | ACCEPT | Critic |

---

### Recommendations

- **즉시 필수** (BLOCK 해제 전):
  - Finding 1: `_is_sufficient` 에 `web_refs` 전달 또는 루프 탈출 조건 교체
  - Finding 2: `write_text()` → `tempfile + os.replace()` 원자적 쓰기로 교체 (`_emit_evidence_files`, `_emit_coverage_report` 양쪽)
  - Finding 3: `__file__` 제거 → `config_paths.PROJECT_ROOT` 사용 + `af.spec` datas 항목 추가
  - Finding 4: `_identify_unmet_gaps:626` 대소문자 조건 수정

- **선택적 (Low)**:
  - Finding 5: `_load_domain_manifest` 에 `lru_cache` 추가

- **Cross Review 재실행 권장**: 이번 리뷰는 timeout 으로 단일 소스 기반이므로 Fix 후 af-cross-review 재실행.