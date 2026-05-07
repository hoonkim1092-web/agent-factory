# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-06 17:16
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

3건의 High 결함이 확인됨. 모두 수정 후 재게이트 필요.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] Fallback `source_id` — `S001` vs `web_001` 불일치
- **Critic**: `_emit_evidence_files` line 672/675에서 LLM이 `source_ids`를 생략하거나 plain string claim인 경우 `S001` 형식 생성. 소스 리스트의 `web_001`과 cross-reference 파괴.
- **Cross**: 동일 경로 확인. `tests/test_research_p1_quality_gate.py:154-159`가 string claim을 테스트하여 실제 재현 가능함을 입증.
- **Judgment**: 양쪽 모두 동일 라인·동일 메커니즘 지목. `sources[0]["source_id"]`는 `web_001`인데 fallback은 `S001`을 생성 — cross-reference가 구조적으로 깨짐.
- **Action Required**: `core/researcher.py:672,675` — fallback을 `sources[min(i, len(sources)) - 1]["source_id"]`로 교체.

---

#### 2. [ACCEPT] [High] 비-web 소스 ID(`local_001`, `llm_001`)가 claim에는 포함되지만 emitted sources에서 누락
- **Critic**: 미탐지.
- **Cross**: `_build_source_pack()`이 `web_*`, `local_*`, `llm_*` 세 타입 ID를 생성(line 405/421/437). `_synthesize_structured_evidence()`는 모든 ID를 LLM에 노출(line 466-471). 그러나 `_emit_evidence_files()`는 `source_type == "web"` 필터만 통과시켜 `local_001` 등을 참조하는 claim은 dangling 상태가 됨.
- **Judgment**: Critic이 놓친 독립 발견. 코드 경로 추적으로 재현 경로 명확. Finding 1과 별개의 구조적 결함.
- **Action Required**: `_emit_evidence_files()`의 `sources` 구성을 web 전용 필터에서 전체 `source_pack["sources"]`로 확장하거나, emit 전 claim `source_id`를 sources 리스트 대비 검증 후 invalid ID 제거.

---

#### 3. [ACCEPT] [High] 증거 파일 쓰기 실패 전체 무음 처리
- **Critic**: `core/researcher.py:1082-1083` — `except Exception: pass` (변수 바인딩조차 없어 `e` 참조 불가). `_emit_evidence_files` + `_emit_coverage_report` 두 호출이 단일 블록에 묶여 어느 쪽 실패인지도 구분 불가.
- **Cross**: 미탐지.
- **Judgment**: 단독 발견이지만 코드 증거가 명확. 호출자(`project_pipeline.py:641-656`)는 아티팩트 저장 실패를 감지할 수단이 없어 silent data loss 발생.
- **Action Required**: `except Exception as e:` 로 변경 + `print(f"[Himari][WARN] evidence emit failed: {e}", file=sys.stderr)` 최소 로깅 추가.

---

#### 4. [ACCEPT] [Medium] `_router.classify()` 이중 호출
- **Critic**: `core/researcher.py:1280`의 `plan`은 print에만, `1407`의 `retrieval_plan`은 `evidence_pack`에 사용됨. RetrievalRouter가 non-deterministic이면 로그와 실제 값 불일치.
- **Cross**: 미탐지.
- **Judgment**: 단독 발견. 그러나 두 호출이 동일 인자로 다른 변수에 저장되는 패턴이 diff에서 명확히 확인됨. deterministic 구현이더라도 불필요한 이중 계산.
- **Action Required**: `plan` 변수를 제거하고 `retrieval_plan` 단일 호출로 통합. print 시 `retrieval_plan` 참조.

---

#### 5. [ACCEPT] [Low] `import subprocess` dead import
- **Critic**: `core/researcher.py:3` — 파일 전체에 `subprocess` 실제 사용처 없음.
- **Cross**: 미탐지.
- **Judgment**: 코드 레벨 명백한 dead import. af.spec `hiddenimports` 맥락에서 의도치 않은 모듈 로딩 유발 가능.
- **Action Required**: `import subprocess` 제거.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Fallback source_id S001 vs web_001 불일치 | High | ACCEPT | Both |
| 2 | non-web source ID dangling claim | High | ACCEPT | Cross only |
| 3 | 증거 파일 쓰기 실패 무음 처리 | High | ACCEPT | Critic only |
| 4 | `_router.classify()` 이중 호출 | Medium | ACCEPT | Critic only |
| 5 | `import subprocess` dead import | Low | ACCEPT | Critic only |

---

### Recommendations

- **Finding 1 (필수)**: `core/researcher.py:672,675` fallback을 `sources[min(i, len(sources)) - 1]["source_id"]`로 교체. plain string claim 경로도 동일하게 적용.
- **Finding 2 (필수)**: `_emit_evidence_files()` sources 구성 시 web 필터 제거 또는 emit 전 claim `source_id` 유효성 검증 추가.
- **Finding 3 (필수)**: `except Exception as e:` + stderr 경고 로깅으로 교체. silent pass 금지.
- **Finding 4 (권장)**: `plan` 제거, `retrieval_plan` 단일 호출로 통합.
- **Finding 5 (권장)**: `import subprocess` 제거.
- **확인됨 (FIXED)**: `os.getcwd()` workspace 파라미터 추가 및 호출부 연결 — 이전 BLOCK 항목 해소.
- **확인됨 (PASS)**: 새 optional 파라미터 하위 호환성 — 42개 테스트 통과.