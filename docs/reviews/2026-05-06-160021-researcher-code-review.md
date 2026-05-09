# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 16:00
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

`core/researcher.py` 변경에 대한 두 리뷰를 읽고 집계 판정을 내립니다.

---

## Final Code Review

### Verdict: BLOCK

최소 2개의 High 결함이 존재합니다. 머지 전 수정이 필요합니다.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] 아티팩트가 target_workspace가 아닌 process cwd에 저장됨

- **Critic**: 제안 Fix 2에서 `.write_text()` 패턴 교체를 언급했으나, 경로 문제 자체는 미식별
- **Cross**: `_emit_evidence_files()`와 `_emit_coverage_report()`가 `Path(os.getcwd()) / "docs" / "research"`에 쓰는데, 호출자(`core/project_pipeline.py:696-699`)는 `workspace=target_workspace`를 전달함. 프로젝트 실행 시 레포 루트에 아티팩트 누출 발생.
- **Judgment**: 코드 증거가 명확. `os.getcwd()`는 두 emit 함수 내부(diff line +636, +684)에 하드코딩되어 있고, 실제 workspace 경로는 전달되지 않음. Cross만 식별했으나 증거가 강함.
- **Action Required**: 두 emit 헬퍼에 `workspace: Path | str` 파라미터 추가. `os.getcwd()` 대신 `Path(workspace) / "docs" / "research"` 사용.

---

#### 2. [ACCEPT] [High] `_identify_unmet_gaps`와 `_emit_coverage_report`의 커버리지 매칭 불일치

- **Critic**: 미식별
- **Cross**: `_identify_unmet_gaps()`는 필드명 raw/underscore-space 변환만 체크하지만, `_emit_coverage_report()`는 manifest의 `match_keywords`를 사용. `hand_ranking` 필드가 `royal flush`/`kicker` 키워드로 커버된 경우, 전자는 gap으로 판정, 후자는 matched로 판정. recovery loop이 불필요한 추가 Tavily 검색을 트리거하고 호출자에게 잘못된 `unmet_gaps`를 반환함.
- **Judgment**: `config/coverage_manifests/poker.yaml`의 `match_keywords` 구조와 두 함수의 매칭 로직을 비교하면 불일치가 명확. Cross만 식별했으나 증거가 강함.
- **Action Required**: `_field_is_covered(field, refs, keywords)` 단일 헬퍼를 추출하고, `_identify_unmet_gaps`, `_is_sufficient`, `_emit_coverage_report` 세 곳에서 공유 사용. manifest를 한 번만 로드.

---

#### 3. [ACCEPT] [Medium] RecoverySearchLoop 종료 후 `sufficient` 플래그 미갱신

- **Critic**: Fix 1로 명시적 제안. 루프 종료 후 `web_refs`가 갭을 채운 경우 `sufficient`를 재평가하지 않음.
- **Cross**: 미식별
- **Judgment**: diff를 직접 확인. while 루프 상단에서 `sufficient = self._is_sufficient(local_refs, ...)` 평가 → 루프 하단에서 `web_refs.extend(...)` 수집 → 루프 재진입 또는 max_rounds 초과로 탈출. 탈출 시점의 `sufficient`는 web_refs 수집 *전* 값이므로, 갭이 실제로 해소됐어도 `sufficient=False`로 남음. Critic만 식별했으나 코드 증거가 명확.
- **Action Required**: while 루프 직후 `if web_refs and _domain_checklist: if not self._identify_unmet_gaps(...): sufficient = True` 추가. 단, finding #2 수정(통합 헬퍼) 후 적용해야 일관성 보장.

---

#### 4. [ACCEPT] [Medium] Evidence JSON에서 구조화된 claim citation 손실

- **Critic**: 미식별
- **Cross**: `_emit_evidence_files()`가 `source_backed_claims` 항목을 `str(claim_text)`로 강제 변환하고, `source_id`를 위치 기반(`S{min(i, len(sources)):03d}`)으로 할당. dict claim의 기존 `source_ids` 필드가 폐기됨. `core/research_verifier.py:15-16` 및 `tests/test_research_router_phase1b.py`의 구조화 claim 계약과 불일치.
- **Judgment**: diff의 `str(claim_text)` 패턴과 `source_id: f"S{min(i, len(sources)):03d}"` 할당이 직접 증거. Cross만 식별했으나 테스트 계약 위반으로 증거 강함.
- **Action Required**: dict claim은 `claim`/`source_ids` 필드를 보존. string claim만 fallback shape으로 wrap. `source_id`는 `source_pack`의 실제 URL 매핑 기반으로 할당.

---

#### 5. [HOLD] [Low] 비원자적 파일 쓰기 (`.write_text()`)

- **Critic**: Fix 2로 `tempfile + os.replace` 패턴 교체를 제안
- **Cross**: 미식별
- **Judgment**: finding #1(경로 수정)이 선행되어야 하며, 실제 중단 가능성(프로세스 kill, 디스크 full)은 낮은 빈도. 단독 BLOCK 근거로는 약함. Finding #1 수정 시 경로를 함께 수정하면서 원자적 패턴도 적용하면 cost-free.
- **Question for Author**: Finding #1 수정 시 함께 적용할지 여부. 별도 작업으로 분리할 이유가 있는가?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 아티팩트 cwd 누출 | High | ACCEPT | Cross |
| 2 | 커버리지 매칭 불일치 | High | ACCEPT | Cross |
| 3 | sufficient 플래그 미갱신 | Medium | ACCEPT | Critic |
| 4 | claim citation 손실 | Medium | ACCEPT | Cross |
| 5 | 비원자적 파일 쓰기 | Low | HOLD | Critic |

---

### Recommendations

1. **Finding #2 먼저 수정** — `_field_is_covered()` 통합 헬퍼가 Finding #3의 fix를 단순화하기 때문에 선행
2. **Finding #1** — emit 헬퍼에 `workspace` 파라미터 추가 시 Finding #5(tempfile 패턴)도 함께 적용
3. **Finding #3** — Finding #2 헬퍼 통합 후 적용 (`_identify_unmet_gaps` 호출 결과 기반으로 sufficient 재평가)
4. **Finding #4** — dict claim 보존 로직은 독립적으로 수정 가능, Finding #1~3과 병렬 진행 가능
5. Cross Review의 Finding #4(파라미터 변경)는 테스트 49개 통과 확인으로 **REJECT 유효** — 추가 조치 불필요