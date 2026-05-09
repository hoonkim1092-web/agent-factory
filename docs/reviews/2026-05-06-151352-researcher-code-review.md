# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 15:13
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

BLOCK 사유: Critical 2건 (non-atomic write, `__file__` frozen 경로) + High 1건. 병합 전 필수 수정.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [Critical] Non-atomic file writes — 3곳 신규 추가 (M10)
- **Critic**: `write_text()` 직접 호출 L661, L712, L723 — 저장 중 프로세스 종료 시 truncated 파일 잔존. code-review.md §3.3 M10 목록과 동일 패턴 3건 신규 추가.
- **Cross**: not flagged
- **Judgment**: diff에서 `write_text(...)` 직접 호출 3곳 확인. 프로젝트 내 이미 알려진 M10 패턴 — 신규 메서드가 이를 따르지 않아 잔존 목록을 늘렸다. Evidence 명확.
- **Action Required**:
  ```python
  tmp = out_dir / f"{slug}-evidence.json.tmp"
  tmp.write_text(json.dumps(...), encoding="utf-8")
  tmp.replace(out_dir / f"{slug}-evidence.json")
  ```
  L661, L712, L723 모두 동일 패턴 적용.

---

#### 2. [ACCEPT] [Critical] `__file__` 경로 — frozen 빌드에서 manifest 무음 누락
- **Critic**: L604, L680에서 `Path(__file__).parent.parent / "config" / ...` 사용. PyInstaller 빌드에서 해당 경로가 존재하지 않으면 `None`/빈 dict 반환하며 에러 없음.
- **Cross**: not flagged
- **Judgment**: 신규 추가된 `_load_domain_manifest`(L604)와 `_emit_coverage_report`(L680) 두 곳 모두 동일 패턴. CLAUDE.md 체크리스트 명시 항목. `config_paths.py`의 `PROJECT_ROOT` 상수가 이미 존재하며 이를 쓰지 않은 것은 명백한 누락.
- **Action Required**:
  ```python
  from core.config_paths import PROJECT_ROOT
  path = PROJECT_ROOT / "config" / "coverage_manifests" / f"{domain}.yaml"
  ```
  L604, L680 양쪽 수정.

---

#### 3. [ACCEPT] [High] Recovery loop — web refs 추가 후 sufficiency gate 재평가 불가
- **Critic**: `_is_sufficient(local_refs, ...)` 시그니처가 `web_refs`를 받지 않아, loop 내에서 `web_refs` 추가 후에도 탈출 조건이 사실상 `_identify_unmet_gaps` 결과에만 의존.
- **Cross**: 동일. `sufficiency_gate_passed`가 웹 복구 성공을 반영하지 못해 `ResearchVerifier.verify()` 호출자의 품질 점수 하락.
- **Judgment**: 양쪽 독립 검토자 동의. diff L927 루프 구조 확인: `_is_sufficient(local_refs, task_input, ...)` — `web_refs` 미전달. 불필요한 API 호출 발생 + 복구 성공도 실패로 기록.
- **Action Required**:
  ```python
  while _recovery_rounds < _max_rounds:
      _unmet = self._identify_unmet_gaps(local_refs, web_refs, _domain_checklist)
      if not _unmet:
          sufficient = True
          break
      ...
  ```
  또는 `_is_sufficient`에 `web_refs` 인자 추가.

---

#### 4. [ACCEPT] [Medium] `_identify_unmet_gaps` — mixed-case checklist 항목 매칭 실패
- **Critic**: L626 `item.replace("_", " ") not in joined` — `joined`은 `.lower()` 처리되나 `item.replace(...)` 결과는 아님. `"API_Rate_Limit"` 같은 항목은 매칭 실패.
- **Cross**: not flagged
- **Judgment**: diff L626 코드 직접 확인. `joined` 소문자화 + `item.replace` 비소문자화 불일치는 코드에서 명백.
- **Action Required**: `item.replace("_", " ").lower() not in joined and item.lower() not in joined`

---

#### 5. [ACCEPT] [High] Claim-source 연결 구조적 손상 (두 리뷰어 다른 각도에서 동일 문제)
- **Critic**: L654 `min(i, len(sources))` — claims > sources일 때 초과 claims 전부 마지막 source에 매핑. 거짓 출처 연결 생성.
- **Cross**: LLM 응답의 `source_ids` (`web_001` 형식)가 L653에서 `str(claim_text)` 변환 시 폐기됨. `ResearchVerifier`가 검증하는 source pack ID와 artifact ID 불일치.
- **Judgment**: 두 리뷰어가 같은 `_emit_evidence_files` 내 서로 다른 결함을 발견. diff L648-665 확인: `source_backed_claims`가 raw text로 처리되어 LLM 응답의 `source_ids` 필드가 실제로 폐기된다. `min(i, len(sources))` overflow도 동시에 존재.
- **Action Required**:
  ```python
  # claim_text가 dict임을 전제
  claim = item.get("claim", str(item)) if isinstance(item, dict) else str(item)
  source_ids = item.get("source_ids", []) if isinstance(item, dict) else []
  # source_id overflow: 범위 초과 시 빈 문자열
  "source_id": f"S{i:03d}" if i <= len(sources) else ""
  ```

---

#### 6. [ACCEPT] [Medium] `_is_sufficient` — manifest match_keywords 미사용으로 sufficiency gate 기준 불일치
- **Critic**: not flagged
- **Cross**: `_emit_coverage_report()`는 manifest의 `match_keywords`를 사용해 필드 커버리지를 평가하지만, `_is_sufficient()`와 `_identify_unmet_gaps()`는 raw field name만 텍스트 검색. 동일 증거가 두 함수에서 다르게 판정됨.
- **Judgment**: diff L693-696에서 `match_keywords` 사용 확인. L764의 `_is_sufficient`는 manifest 없이 단순 substring. 설계 불일치로 "통과"/"미통과" 판정이 다른 로직으로 분기되는 것은 실제 결함.
- **Action Required**: `_identify_unmet_gaps`에 `match_keywords` 로직 공유 — manifest 로드 후 동일 keyword 리스트로 검사하는 내부 helper 추출.

---

#### 7. [ACCEPT] [Medium] `coverage_report.block` — 계산되지만 어떤 caller도 gate로 사용하지 않음
- **Critic**: not flagged
- **Cross**: `_emit_coverage_report()`가 `block=True`를 반환해도 `collect_project_evidence()`는 `initial_evidence["coverage_report"]`에만 첨부. `ProjectPipeline`과 `ResearchVerifier` 모두 이 필드를 gate로 소비하지 않음.
- **Judgment**: diff L1052 확인. `block` 값이 JSON/MD 파일에 기록되지만 런타임 흐름에 영향 없음. 기능이 완성되지 않은 상태.
- **Action Required**: `collect_project_evidence` 내에서 `coverage_report.get("block")` 시 `sufficiency_gate_passed=False` 설정 또는 `ResearchVerifier`에 `coverage_blocked` gap 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Non-atomic file writes (M10) | Critical | ACCEPT | Critic |
| 2 | `__file__` frozen 빌드 경로 | Critical | ACCEPT | Critic |
| 3 | Recovery loop sufficiency gate | High | ACCEPT | Both |
| 4 | `_identify_unmet_gaps` lowercase | Medium | ACCEPT | Critic |
| 5 | Claim-source 연결 손상 | High | ACCEPT | Both |
| 6 | `_is_sufficient` match_keywords 미사용 | Medium | ACCEPT | Cross |
| 7 | `coverage_report.block` 미집행 | Medium | ACCEPT | Cross |

---

### Recommendations

- **즉시 수정 (BLOCK 해제 필수)**: #1 (atomic write), #2 (`config_paths.PROJECT_ROOT`), #3 (recovery loop gate), #5 (claim-source 매핑)
- #4 는 1줄 수정이므로 같은 PR에 포함 권장
- #6, #7은 설계 범위 변경 — 별도 이슈/PR로 분리 가능하나, `block` 미집행(#7)은 현재 B5 기능이 사실상 dead code임을 의미하므로 이번 PR 범위 내에서 명확히 할 것