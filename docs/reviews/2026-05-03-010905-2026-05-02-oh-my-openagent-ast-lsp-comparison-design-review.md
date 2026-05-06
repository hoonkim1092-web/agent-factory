# Design Review: 2026-05-02-oh-my-openagent-ast-lsp-comparison

> Source: docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md
> Date: 2026-05-03 01:09
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

두 리뷰 모두 완료되었습니다. 이제 집계합니다.

---

## Final Design Review

### Verdict: WARN

BLOCK 사유 없음. Medium 2건 + Low 다수 — 구현 전 수정 권고이나 blocking 수준은 아님.

---

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [Medium] §5.2 처방형 언어 혼재 (L131, L136)
- **Critic**: `"고정 필요"`, `"결정 필요"` 등 action item이 분석 전용 문서에 잔존. plan 문서에 속하는 내용.
- **Cross**: F4로 독립 확인. 추가로 §10 변경 이력에서 "권고"라는 단어 사용이 문서 선언("분석 전용")과 직접 충돌함을 지적.
- **Judgment**: 양측 동일 위치 지목, 증거 명확. §10 이력의 "권고" 단어 충돌은 Cross가 추가 발견.
- **Action Required**:
  - L131: `(예: core/ast_engine.py.search() ... 테스트)` 괄호 전체 삭제 → `"— engine에 따라 1-based vs 0-based로 갈림 (동일 L{line} 토큰, engine별 계약 비일관)."` 로 교체
  - L136: `(plan 진입 시 workspace-relative 고정 또는 abs_path sidecar 분리 결정 필요)` 삭제 → `"schema 계약 모호 — workspace-relative 가정과 절대경로 저장 사이 불일치."` 로 교체
  - §10 v2 이력의 "권고" 단어를 "schema 계약 기술"로 교체

#### 2. [ACCEPT] [Low] `settings.local.json` PostToolUse 블록 라인 범위 오기 (2곳)
- **Critic**: §5.3 L142 "204-226", §5.4 Q-C "191-212" — 두 곳이 서로도 불일치.
- **Cross**: F1/F8로 독립 확인. 실측 결과 `"PostToolUse":` 키는 205에서 시작, 블록 끝은 226. §10 v2 이력 "191-212"와 본문 "204-226" 불일치도 추가 지적.
- **Judgment**: 양측 동일 파일 동일 위치 지목. Critic이 §5.3을 "204-226"으로 잘못 인용했는데, Cross가 실측해 "205-226"이 정확함을 확인.
- **Action Required**: §5.3 L142 및 §5.4 Q-C "191-212"/"204-226" 전부를 `205-226`으로 통일. §10 v2 이력에 현재 실제값 반영.

#### 3. [ACCEPT] [Low] `hook_runner.py:347-365` 라인 범위 오기 (§5.4 Q-F bullet b)
- **Critic**: M3. 실측: 347–348은 af-test-runner 분기, silent failure `except Exception: pass`는 359–374.
- **Cross**: F5로 독립 확인. try 블록 시작은 359, except는 373-374.
- **Judgment**: 양측 동일 파일 검증, 시작 라인 불일치 확인. Critic 제안(`359-374`)이 Cross(`362-374` → try는 359)와 미세 차이 있으나 양측 모두 "347-365는 틀림"에 동의. 정확한 범위는 `359-374`.
- **Action Required**: `hook_runner.py:347-365` → `hook_runner.py:359-374`로 교체.

#### 4. [ACCEPT] [Low] `af-test-runner.md:41-43` 라인 참조 오기
- **Critic**: L3. `python scripts/test_gap_analyzer.py --workspace .` 실제 위치는 line 46.
- **Cross**: 실측에서 라인 46 정확 확인 (F1 검증 테이블 내).
- **Judgment**: 양측 코드 실측 일치. 명백한 오기.
- **Action Required**: `:41-43` → `:46` 으로 교체.

#### 5. [ACCEPT] [Low] `hook_runner.py:387` "builtin dispatch" 표현 부정확 (§5.4 Q-B)
- **Critic**: 미지적.
- **Cross**: F2 단독 발견. 387은 `_apply_test_gap_verdict()` 내부 import 줄 — builtin dispatch(`_BUILTINS` 딕셔너리 474-485)가 아님.
- **Judgment**: Cross 단독이나 코드 실측 기반 증거 명확. "builtin dispatch에 있으나"라는 표현이 독자에게 잘못된 코드 위치 인상을 줌.
- **Action Required**: `scripts/hook_runner.py:387 builtin dispatch에 있으나` → `scripts/hook_runner.py의 _apply_test_gap_verdict()를 통한 간접 경로(L387)에 있으나` 로 교체.

#### 6. [ACCEPT] [Low] §10 변경 이력 v3 라인 값 무효화 미정리
- **Critic**: 미지적.
- **Cross**: F7 단독 발견. v3 이력에 구값(`:53`, `:29`)이 v4 정정(`:51`, `:56`) 이후에도 남아 있어 이력 섹션 내 자기모순.
- **Judgment**: Cross 단독이나 이력 섹션 내부 일관성 위반으로 실측 명확.
- **Action Required**: §10 v3 이력에서 `:53` → `:51`, `:29` → `:56` 으로 교체 또는 "v4에서 정정됨" 각주 추가.

#### 7. [REJECT] [Low] `af-critic.md:33` 라인 근거 정밀도 (Cross F3)
- **Source**: Cross 단독
- **Original Finding**: 33이 변수 할당 줄이라 "workspace-relative 가정" 근거로 약함, 34-38이 더 명확.
- **Rejection Reason**: 문서 기술 의미("af-critic이 bundle 경로를 workspace-relative로 처리")는 정확하다. `:33`은 그 변수가 정의되는 위치로 식별 가능한 앵커이며, 독자가 오해할 수준의 오류가 아님. 분석 문서의 라인 참조 정밀도 기준 내.

#### 8. [REJECT] [Low] Q-D caveat 측정 시점 pin 미흡 (Cross F6)
- **Source**: Cross 단독
- **Original Finding**: docs/reviews/*.md 별도 sink 수치의 측정 시점이 이력에 pin되지 않음.
- **Rejection Reason**: 문서 §5.4 서두에 "모든 측정은 명시된 sink 한정"을 선언하고, Q-D 헤더에 "hook_events.log review-recorded sink 한정"이 명시되어 있다. caveat 박스에서 별도 sink를 설명용으로만 언급한 것이며, 이를 pin해야 할 독립 측정값으로 보기 어려움.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §5.2 처방형 언어 혼재 (L131, L136, §10 이력) | Medium | ACCEPT | Both |
| 2 | settings.local.json PostToolUse 라인 범위 오기 | Low | ACCEPT | Both |
| 3 | hook_runner.py:347-365 라인 범위 오기 | Low | ACCEPT | Both |
| 4 | af-test-runner.md:41-43 라인 참조 오기 | Low | ACCEPT | Both |
| 5 | hook_runner.py:387 "builtin dispatch" 표현 부정확 | Low | ACCEPT | Cross |
| 6 | §10 v3 이력 구 라인값 미정리 | Low | ACCEPT | Cross |
| 7 | af-critic.md:33 라인 근거 정밀도 | Low | REJECT | Cross |
| 8 | Q-D caveat 측정 시점 pin 미흡 | Low | REJECT | Cross |

---

### Recommendations

수정 필요 항목 6건 모두 문서 편집으로 해결 가능합니다. 우선순위 순:

1. **[Medium, #1]** §5.2 L131·L136 처방형 괄호 제거, §10 v2 이력 "권고" 단어 교체
2. **[Low, #3]** `hook_runner.py:347-365` → `359-374` (Q-F bullet b)
3. **[Low, #4]** `af-test-runner.md:41-43` → `:46` (Q-B)
4. **[Low, #2]** settings.local.json 라인 범위 `205-226`으로 통일 (§5.3, §5.4 Q-C, §10 v2 이력)
5. **[Low, #5]** `hook_runner.py:387` "builtin dispatch" → `_apply_test_gap_verdict() 내부 경로` 표현 교체
6. **[Low, #6]** §10 v3 이력 구 라인값 정정