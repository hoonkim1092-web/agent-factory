# Code Review: work_item_generator

> Source: core/work_item_generator.py
> Date: 2026-05-08 14:52
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

At least one Critical finding confirmed by both independent reviewers. Must fix before merge.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Critical] `exc` UnboundLocalError — 예외 경로 100% 크래시

- **Critic**: "`return`이 `except` 블록 바깥에 있어 Python 3 PEP 3110 스코프 규칙에 의해 `exc`가 이미 삭제됨 → NameError 확실"
- **Cross**: "`RuntimeError('boom')` 패치로 실제 `UnboundLocalError` 재현 확인 (line 587)"
- **Judgment**: 두 리뷰어 모두 동일 지점 지적, 직접 재현까지 완료. diff에서 indent 레벨 확인 — `return DocGenerationResult(... errors=[f"{type(exc).__name__}:{exc}"] ...)` 가 `except` 블록과 같은 레벨에 위치. 예외 발생 시 100% 재현.
- **Action Required**: `return DocGenerationResult(...)` 전체를 `except` 블록 **안**으로 4칸 들여쓰기.

```python
except Exception as exc:
    _LOGGER.warning("LLM 문서 생성 예외 — 폴백 사용: %s", exc)
    return DocGenerationResult(          # ← 여기로 이동
        doc_type=doc_type,
        content=fallback_fn(),
        provider_id="fallback",
        model="static",
        used_fallback=True,
        errors=[f"{type(exc).__name__}:{exc}"],
        run_id=run_id,
    )
```

---

#### 2. [HOLD] [Medium] 반환 타입 `str` → `DocGenerationResult` — 호출자 전수 확인 미완료

- **Critic**: "diff에 호출자 업데이트가 없음. `plan = _generate_feature_plan(...)` 이후 문자열로 사용하면 `AttributeError` 또는 오염"
- **Cross**: "직접 다루지 않았으나, `generate_work_items()` line 853이 `DocGenerationResult`를 처리하고, `_generate_and_refine()` lines 870/888/906 호출부도 올바른 키워드 방식 확인"
- **Judgment**: Cross가 확인한 주요 호출 지점(853, 870, 888, 906)에서는 문제 없음. 그러나 diff 외부에 `_generate_feature_plan` / `_generate_feature_spec`를 직접 호출하는 추가 지점이 있는지 여부가 불명확. 전수 `grep`이 필요.
- **Question for Author**: `grep -n "_generate_feature_plan\|_generate_feature_spec" core/work_item_generator.py` 결과에 diff에 포함되지 않은 호출자가 있는가? 없다면 PASS, 있다면 `.content` 추출 또는 어댑터 추가 필요.

---

#### 3. [ACCEPT] [Low] `timeout_fallback` 필드 — 항상 `False`, dead field

- **Critic**: "`DocGenerationResult.timeout_fallback`이 정의되어 있으나 이번 diff 어디서도 `True`로 설정되지 않음"
- **Cross**: "not flagged"
- **Judgment**: Critic 단독 지적이지만 diff에서 직접 확인 가능 — `timeout_fallback: bool = False`가 dataclass에 있고 할당 코드가 없음. 미완성 구현 신호.
- **Action Required**: 타임아웃 감지 로직 추가 (`elapsed_sec >= timeout_sec` 체크) 또는 구현 계획이 없다면 필드 제거. 현재 상태로 merge 시 API surface를 오염시킴.

---

#### 4. [HOLD] [Low] 텔레메트리 필드 소비 경로 미연결

- **Critic**: "not flagged"
- **Cross**: "`placeholder_refine_attempts`, `t1_refine_attempts`, `usage_tokens` 추가됐으나 집계/저장 경로 미확인. `work_item_telemetry.py:update_t1_refine_attempts()` 호출자 없음"
- **Judgment**: 후속 커밋으로 연결 예정이면 정당하나, 현재 dead code 상태. 범위 미명시 시 코드베이스 노이즈.
- **Question for Author**: 텔레메트리 연결이 후속 PR에 예정되어 있는가? 있다면 TODO 주석 또는 work-item 링크 추가. 없다면 필드 연결 또는 제거.

---

### Finding 3 (`*` keyword-only 호환성) — REJECTED

Cross reviewer가 `_generate_and_refine()` lines 960/967과 호출부 870/888/906에서 `prev_kwargs`로 키워드 명시 전달을 직접 확인. Critic의 우려는 타당했으나 실제 호출 코드에서 이미 처리됨. 수정 불필요.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `exc` UnboundLocalError — 예외 경로 크래시 | Critical | ACCEPT | Both |
| 2 | 반환 타입 변경 호출자 전수 확인 | Medium | HOLD | Critic (Cross 부분 검증) |
| 3 | `timeout_fallback` dead field | Low | ACCEPT | Critic |
| 4 | 텔레메트리 소비 경로 미연결 | Low | HOLD | Cross |
| — | `*` keyword-only 호환성 | High | REJECTED | Cross가 반증 |

---

### Recommendations

- **즉시 수정 (merge blocker)**: Finding 1 — `return DocGenerationResult(...)` indent 수정으로 `except` 블록 안으로 이동
- **merge 전 확인**: Finding 2 — `grep -n "_generate_feature_plan\|_generate_feature_spec" core/work_item_generator.py` 실행 후 모든 호출자가 `.content`를 올바르게 추출하는지 검증
- **단기 정리**: Finding 3 — `timeout_fallback` 필드에 타임아웃 감지 로직 추가 또는 제거
- **후속 PR 범위 명시**: Finding 4 — `work_item_telemetry.py` 연결 계획을 NEXT_STEPS.md에 등록하거나 TODO 주석으로 추적