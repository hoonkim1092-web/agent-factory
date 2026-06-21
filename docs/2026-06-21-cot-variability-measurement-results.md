# CoT 프롬프트 변동성 측정 결과

날짜: 2026-06-21  
스크립트: `scripts/measure_cot_variability.py`  
목적: 빈-scope 라우터 CoT 프롬프트 정식 채택 전 잔여 검증 2건

---

## 검증 1 — task 종류 다양화 (claude_cli)

이전 세션은 단순(README) / 복잡(인증) 각 1종만 측정. 5종으로 확대.

### 원본 프롬프트 vs CoT 프롬프트 비교

| task | expected | ORIG light/N | CoT light/N | ORIG conf±std | CoT conf±std |
|------|----------|-------------|-------------|---------------|--------------|
| simple_readme | light | 0/3 ❌ | 3/3 ✅ | 0.907±0.012 | 0.940±0.017 |
| simple_leaf_fn | light | 3/3 ✅ | 3/3 ✅ | 0.957±0.012 | 0.930±0.017 |
| medium_2files | borderline | 5/5 (light) | 5/5 (light) | 0.966±0.009 | 0.938±0.022 |
| large_refactor | full | 0/3 ✅ | 0/3 ✅ | 0.720±0.000 | 0.720±0.000 |
| complex_auth | full | 0/5 ✅ | 0/5 ✅ | 0.758±0.043 | 0.732±0.016 |

### 핵심 발견

**simple_readme ORIG 버그**: ORIG 프롬프트가 `['research', 'implement']` stages를 반환.
- `research ∉ LIGHT_STAGES` → `is_light()=False` → 잘못된 full 라우팅
- CoT는 `['implement']` 또는 `['plan','implement']`만 → 올바른 light 라우팅

**medium_2files 분류 재판**: 상수 1개 변경 + 테스트 sync → LLM이 light로 판단.
- 태스크 설명에 파일 경로 명시했음에도 changed_files=[]이라 blast_radius 미적용
- LLM 판단 자체는 합리적 (기계적 변경, 설계 불필요)
- 이 task는 expected="full"이 아닌 "borderline/light" 재분류

**complex_auth ORIG vs CoT stdev**: 0.043 → 0.016 (62% 감소)

**군집 분리 (claude_cli CoT)**:
- light min: 0.920 (simple_readme 최솟값)
- full max: 0.750 (complex_auth 최댓값)  
- gap = 0.920 - 0.750 = **0.170** (충분한 안전 마진)

---

## 검증 2 — 멀티프로바이더 (codex_cli CoT)

| task | light/N | conf±std | min | max |
|------|---------|----------|-----|-----|
| simple_readme | 3/3 ✅ | 0.873±0.023 | 0.860 | 0.900 |
| simple_leaf_fn | 3/3 ✅ | 0.873±0.023 | 0.860 | 0.900 |
| complex_auth | 0/3 ✅ | 0.693±0.023 | 0.680 | 0.720 |

**군집 분리 (codex_cli CoT)**:
- light min: 0.860
- full max: 0.720
- gap = **0.140** (양쪽 임계 0.82로부터 대칭: 0.04 / 0.10)

---

## 임계값 분석

| 임계 | claude light (min 0.92) | codex light (min 0.86) | claude full (max 0.75) | codex full (max 0.72) |
|------|------------------------|------------------------|------------------------|------------------------|
| 0.85 (현재) | ✅ margin 0.07 | ⚠️ margin 0.01 | ✅ | ✅ |
| **0.82 (확정)** | ✅ margin 0.10 | ✅ margin 0.04 | ✅ margin 0.07 | ✅ margin 0.10 |
| 0.80 | ✅ | ✅ margin 0.06 | ✅ | ✅ |

**결론: 임계 0.82 채택**
- codex min=0.86 → 0.85 임계에서 margin 0.01로 위험
- 0.82에서는 양 프로바이더 모두 안전 (margin ≥ 0.04)
- 단일 임계로 claude+codex 양쪽 커버 (프로바이더별 별도 임계 불필요)

---

## 설계문서 입력 사항

1. **프롬프트 변경 대상**: `_build_empty_scope_prompt` + `_build_prompt` CoT화
2. **상수 변경**: `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 0.85 → 0.82
3. **프로바이더 별도 임계 불필요**: 단일 상수로 충분
4. **기대 효과 실증**:
   - simple_readme research 오염 제거 (ORIG 0/3 → CoT 3/3)
   - complex_auth stdev 62% 감소 (0.043 → 0.016)
   - 군집 gap 0.14-0.17 유지 (충분한 분리)
5. **`medium_2files` 주의**: 기계적 변경 task는 LLM이 light로 판단 — 허용 동작 (blast_radius floor가 실제 Tier 파일에 별도 적용)

---

## 다음 단계

- 설계문서 작성 (Opus) — `docs/2026-06-21-cot-prompt-variability-fix-design.md`
- 교차검증 (af-cross-review)
- 코드+테스트 구현 (Sonnet):
  - `core/right_sized_router.py`: `_build_empty_scope_prompt` CoT화 + `_build_prompt` CoT화 + `_EMPTY_SCOPE_LIGHT_CONFIDENCE_THRESHOLD` 0.85→0.82
  - `tests/test_right_sized_router.py`: 임계 상수 참조 업데이트
