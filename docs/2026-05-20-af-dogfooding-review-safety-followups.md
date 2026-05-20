# AF Dogfooding Review Safety — Follow-ups

Date: 2026-05-20
Parent design: [docs/2026-05-20-af-dogfooding-review-safety.md](2026-05-20-af-dogfooding-review-safety.md)
Status: **DONE (2026-05-20)** — #1+#2 `89559a8d`, #3+#4 `d3734717`. 전체 후속 4건 흡수 완료.

## 검증 시점 사실

- `python -m py_compile scripts/{blast_radius,t3_classifier,t3_skip_report,enqueue_agent_review,review_gate,check_pending_review,hook_runner}.py` 통과
- `python -m pytest tests/{test_t3_classifier,test_t3_skip_report,test_review_gate,test_pending_review,test_hook_runner_builtins}.py -q` — 106 passed
- 설계 §1~§7 모두 코드에 반영. 핵심 정책 함수(`_deterministic_t3_skip_candidate`, `_allows_t3_skip`, `_required_tiers_for`)가 설계 §"Policy Summary" 의사코드와 1:1.

## 문제 1 — 모듈 docstring 사실 오류 (P1, 텍스트 수정)

**파일**: `scripts/t3_classifier.py:7-9`

```
- only Python changes that are AST-equivalent after removing docstrings and
  annotations may skip Tier 3.
```

설계문서 137행은 정반대를 명시한다:
```
Annotation-only changes are intentionally not treated as cosmetic because
Python annotations are runtime-observable through __annotations__ and
framework/schema integrations.
```

실제 구현(`_CosmeticAstNormalizer`, line 62-96)은 `_strip_docstring`만 호출하며 annotation에는 손대지 않는다. 클래스 docstring(line 64-68)은 올바름.
회귀 테스트 `tests/test_t3_classifier.py::test_annotation_change_requires_t3` (line 41-52)가 annotation 변경 → `require_t3` 정책을 못박는다.

**영향**: 안전 구멍 없음. 다음 사람이 docstring만 보고 "annotation도 cosmetic"으로 오해할 위험.

**제안 패치**:
```diff
 """Deterministic Tier-3 review classifier.

 The classifier is intentionally conservative:
 - hard-guard paths always require Tier 3;
 - risk tokens in added or deleted diff lines always require Tier 3;
-- only Python changes that are AST-equivalent after removing docstrings and
-  annotations may skip Tier 3.
+- only Python changes that are AST-equivalent after removing docstrings
+  may skip Tier 3 (annotations are preserved as semantic — see
+  `_CosmeticAstNormalizer`).
 """
```

**블래스트**: `scripts/t3_classifier.py`는 `blast_radius._TIER3_PATHS`에 hard-guard 등록(blast_radius.py:56). 텍스트만 바뀌어도 commit 시 af-test-runner + af-critic + af-cross-review 한 라운드 필요.

## 문제 2 — af-critic 프롬프트가 deterministic 정책과 어긋남 (P2, 텍스트 수정)

**파일**: `scripts/prompts/code_critic.txt:48`

```
- Use `no` only when the change is clearly cosmetic/documentation/annotation-only
  and does not affect execution behavior.
```

프롬프트는 "annotation-only이면 no"를 허용하지만, deterministic classifier는 annotation 변경을 `semantic-python-change`로 분류한다(`t3_classifier.py:215-241` + 회귀 테스트). 게이트는 `deterministic AND critic` 양쪽 합의로만 skip을 허가(`review_gate.py:122-124`)하므로 critic이 "no"를 찍어도 deterministic이 차단한다.

**영향**: 안전 구멍 없음(fail-closed). LLM이 잘못된 "no"를 출력하면 디버그 로그에서 가짜 시그널이 늘어 혼란 유발.

**제안 패치**:
```diff
- Use `no` only when the change is clearly cosmetic/documentation/annotation-only and does not affect execution behavior.
+ Use `no` only when the change is clearly comment/docstring/whitespace-only and does not affect execution behavior. Type-annotation changes count as semantic because Python annotations are runtime-observable.
```

**블래스트**: 프롬프트 파일은 `.py`가 아니어서 review-gate 우회. 단순 텍스트 PR.

## 문제 3 — `review_gate.py` CLI에 `--t3-required` 부재 (P3, 코드 수정)

**파일**: `scripts/review_gate.py` `_cli` (line 501-540)

`record_review_done`은 `t3_required` kwarg를 받지만(line 295-302) CLI 파서는 노출 안 함. `python scripts/review_gate.py --record af-critic --verdict pass`는 advisory를 항상 None으로 통과시키고, `record_review_done` 내부에서 `str(None or "unknown").lower() == "unknown"`(line 339-342)으로 정규화 → fail-closed로 T3 요구.

**영향**: 안전 구멍 없음. 디버그 시 advisory를 수동 주입할 수 없어 재현이 불편.

**제안 패치**:
```diff
     parser.add_argument("--tier", type=int, choices=[1, 2, 3])
     parser.add_argument("--verdict", choices=["pass", "warn", "block", "fail"])
+    parser.add_argument("--t3-required", choices=["yes", "no", "unknown"], default=None,
+                        help="af-critic advisory (af-critic 레코드 시에만 의미 있음)")
     parser.add_argument("--files", default="", help="쉼표 구분 파일 목록")
@@
     if args.record:
         ...
-        record_review_done(ws, agent, tier, verdict, files)
+        record_review_done(ws, agent, tier, verdict, files, t3_required=args.t3_required)
```

**블래스트**: `review_gate.py`는 `_TIER3_PATHS` hard-guard. af-cross-review 라운드 1회.
기존 테스트 영향 없음(CLI 회귀 테스트는 `--check`/`--debug` 중심).

## 문제 4 — classifier_version 문자열 이중 정의 (P3, 코드 수정)

**파일**:
- `scripts/t3_classifier.py:27` — `CLASSIFIER_VERSION = "t3-deterministic-v1"`
- `scripts/review_gate.py:90` — `_T3_SKIP_CLASSIFIER_VERSION = "t3-deterministic-v1"`

두 곳이 일치해야 skip이 허가된다(`_deterministic_t3_skip_candidate`, line 108).
의도적 fail-closed 커플링이지만 한쪽만 bump 시 silent BLOCK 회귀 위험.

**영향**: 현재 일치 → 안전 구멍 없음. 운영 시간 경과에 따라 동기화 누락 위험 누적.

**제안 패치**:
```diff
-_T3_SKIP_CLASSIFIER_VERSION = "t3-deterministic-v1"
+try:
+    from scripts.t3_classifier import CLASSIFIER_VERSION as _T3_SKIP_CLASSIFIER_VERSION
+except ImportError:
+    from t3_classifier import CLASSIFIER_VERSION as _T3_SKIP_CLASSIFIER_VERSION  # type: ignore
```

**대안**: import 결합이 싫다면, review_gate가 version mismatch를 hook_events.log에 명시 기록만 추가(`_log_event(workspace, f"[t3-skip-version-mismatch] expected={...} actual={...}")`)하는 식의 detection-only 라우트도 있음. 운영 신호만 확보하고 결합은 안 한다.

**블래스트**: `review_gate.py` Tier 3 hard-guard. af-cross-review 라운드 1회.

## 우선순위 및 묶음 권장

| 우선 | 항목 | 위험 종류 | 추천 묶음 |
|------|------|----------|----------|
| P1 | #1 docstring | 문서 거짓 정보 (운영자 혼선) | 단독 또는 #2와 묶기 |
| P2 | #2 critic 프롬프트 | LLM 시그널 오염 (안전 구멍 아님) | #1과 묶기(둘 다 텍스트) |
| P3 | #3 CLI 옵션 | 디버그 UX | #4와 묶기(`review_gate.py` 동일 파일) |
| P3 | #4 version 단일소스 | 장기 회귀 위험 | #3과 묶기 |

#1+#2는 `.py` 1개(`t3_classifier.py`) + 프롬프트 1개. `t3_classifier.py`는 hard-guard라 어차피 T3 한 라운드 필요.
#3+#4는 둘 다 `review_gate.py` 수정 → 같은 커밋이 자연스러움.

## 진입 시 체크리스트

1. 이 문서 grep으로 좌표 재캡처 (라인 stale 방지)
2. 패치 적용 → `python -m pytest tests/test_t3_classifier.py tests/test_review_gate.py tests/test_pending_review.py tests/test_hook_runner_builtins.py tests/test_t3_skip_report.py -q`
3. 3-Tier 라운드 (af-test-runner → af-critic → af-cross-review)
4. Blueprint §12 갱신
5. 본 문서 status를 DONE으로 갱신 + 커밋 해시 기록

## 비목표

- T2 advisory를 `review_metrics_report.py`에 노출하는 작업(parent doc §"Remaining Work" 마지막 항목)은 본 후속에 포함하지 않음. 메트릭 데이터 1주 수집 후 별도 진입.
- AF 자기 수정 루프 실측(parent doc §"Remaining Work" 첫 항목)은 운영 작업이지 코드 패치가 아님.
