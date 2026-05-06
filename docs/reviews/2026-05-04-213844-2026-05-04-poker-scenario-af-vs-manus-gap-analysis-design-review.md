# Design Review: 2026-05-04-poker-scenario-af-vs-manus-gap-analysis

> Source: docs/2026-05-04-poker-scenario-af-vs-manus-gap-analysis.md
> Date: 2026-05-04 21:38
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Cross review failed with a provider error (Codex stdin readback / model `gpt-5.5` invalid response). Only the critic review is available, so all findings come from a single source. Two Critical findings exist in the critic review — verdict is BLOCK regardless.

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [Critical] 권고 ⑥ `deep_synthesis` 신규 모드가 기존 5-mode 라우터와 중복
- **Critic**: `core/research_router.py:39-71, 100-111, 254-283`에 이미 `fast_synthesis / fresh_lookup / deep_source_research / archive_research / live_project_analysis` 5개 모드와 v1.2 잠금 주석. 진단이 빠뜨린 것은 "포커 시뮬 요청이 왜 기존 `deep_source_research`(MULTI_CLIENT_MISSING gap)로 안 갔는가"의 router 휴리스틱 결함.
- **Cross**: not flagged (provider error).
- **Judgment**: Critic이 인용한 코드 위치가 실제 코드와 일치하며 (memory `Research Router v1.4.1 PASS` 와도 정합 — 5-mode 잠금이 사실), 신규 모드 추가는 잠금 정책 위반. 진단의 핵심도 router 분류 결함이지 모드 부재가 아님.
- **Action Required**: §4 ⑥을 폐기하고 `_classify_primary_mode()` / `_compute_signal_scores()`의 multi-client·simulation·protocol 신호 가중치 보정으로 재작성. 신규 모드는 `ResearchGap` enum + `gap_to_mode` precedence와 함께만 변경 가능함을 명시.

#### 2. [ACCEPT] [Critical] 권고 ② brief schema 변경 다운스트림 영향 미평가 + Non-Goal 차단 규칙 too strict
- **Critic**: (a) "v1엔 AI 봇 없음" 같은 정당한 inferred non-goal까지 차단됨. (b) `goals: list → dict` 변경은 `work_item_generator.py:528,568,605,642`, `_fallback_brief()` (researcher.py:908-917), `_build_task_profile()` (plan_verifier.py:200), 모든 `project_brief.get("goals")` 호출처에서 KeyError 유발.
- **Cross**: not flagged (provider error).
- **Judgment**: schema 변경 영향 범위는 검증 가능한 사실 — `core/`에 `project_brief` 구조 의존 코드가 다수 있으면 fallback path까지 동시 변경하지 않으면 frozen build에서 런타임 실패.
- **Action Required**: (a) "추론 Non-Goal은 별도 섹션 `## Inferred Non-Goals (review required)` + 기본 collapsed"로 완화. (b) PR 전 `grep -rn 'project_brief\[.goals.\]\|brief\.get..goals.' core/` 결과 첨부 + `_fallback_brief()` 동시 변경 필수 명시.

#### 3. [ACCEPT] [High] 단기 ① original_request 4번 주입 — 토큰·중복·언어혼재 영향 미평가
- **Critic**: 4개 generator prompt에 이미 `project_brief` 전체 JSON 주입 중. 추가로 `original_request` 전문 주입 시 (1) 중복 토큰, (2) `RunBudget` 80%/100% gate 충돌 가능, (3) 한글 prompt 본문이 영문 prompt에 혼재 → LLM 일관성 저하.
- **Cross**: not flagged (provider error).
- **Judgment**: code reference 정확. CLAUDE.md "Simplicity First"와도 정합 — 같은 텍스트 4중 주입은 과설계.
- **Action Required**: project_brief에 `original_request` 한 곳만 추가 → generator는 brief 필드 reference만. 토큰 영향 추정값 명시. 한·영 혼재 prompt 동작 검증 evidence 첨부.

#### 4. [ACCEPT] [High] §4 권고 5 도메인 화이트리스트 — 일반화 불가 + 유지보수 부채
- **Critic**: 화이트리스트는 좁은 도메인(포커=wsop/tda)에만 효과. 다른 task(로또·암호화폐 등)마다 운영자 추가 필요. LLM relevance scoring이 더 일반적.
- **Cross**: not flagged (provider error).
- **Judgment**: 화이트리스트 hard-coding은 Master_Blueprint 잠금 정책과 staging 다양성에서 부채 명확. `_collect_llm_prior_knowledge` (researcher.py:579) 패턴 재사용 가능성도 합리적.
- **Action Required**: (a) Tavily query에 "official rules"/specification boost, (b) LLM 1-shot relevance scoring 도입, (c) `_is_sufficient` threshold 0.25 → 0.4. 화이트리스트는 옵트인 `policy.yaml`로만.

#### 5. [ACCEPT] [Medium] 신규 `intent_classifier.py` / `document_templates/` 도입 — 기존 `IntentGate` 매핑 + frozen build 영향 미언급
- **Critic**: `core/intent.py:6` `IntentGate`에 이미 5분류(`trivial/question/refactoring/greenfield/debugging`)가 존재. 새 5분류(`build/simulate/walkthrough/analyze/architect`)와 carrier 다름 → 구현 단계 재판단 비용. `af.spec hiddenimports` 누락 시 frozen build ImportError. `core/document_templates/` 디렉토리는 PyInstaller `datas` 등록 필요.
- **Cross**: not flagged (provider error).
- **Judgment**: code-review.md M9 (af.spec hiddenimports) 규칙은 CLAUDE.md에도 명시된 구속력 있는 빌드 규칙. 누락 시 zip 배포 실패.
- **Action Required**: (a) `IntentGate` 확장 vs 신규 파일 결정 + 기존/신규 5분류 매핑 테이블, (b) `af.spec` 갱신 체크리스트, (c) 단일 file 확장 권장.

#### 6. [ACCEPT] [Medium] 단기 ③ 도메인 가드 — 한국어 stopword·동의어·fallback 무한 churn 미명시
- **Critic**: (a) 한·영 혼합 stopword 부재(외부 NLP 의존성 필요), (b) exact match면 "포커" vs "poker" 동의어 누락, (c) 임계값 0.35 상향 시 `_is_sufficient` 빈 결과 → `_collect_llm_prior_knowledge` fallback이 또 도메인 무관이면 churn.
- **Cross**: not flagged (provider error).
- **Judgment**: code 인용 정확. memory `cross-review stale baseline false positive` 와 정합 — fallback path에 동일 가드 없으면 churn 패턴 재발 가능.
- **Action Required**: (a) 의존성 없이 lowercase split + len≥3 필터, (b) 임계값은 A/B 결정(단일 잠금 금지), (c) fallback path 동일 가드 통합 + 통과율 메트릭.

#### 7. [ACCEPT] [Medium] 검증 기준 "근접" — Goal-Driven Execution 위반
- **Critic**: §6 "Manus 산출 수준에 근접" 정의 부재 → PASS/FAIL 불가. §2 표 8개 누락 항목을 정량 체크리스트로.
- **Cross**: not flagged (provider error).
- **Judgment**: CLAUDE.md "Goal-Driven Execution" 명시 위반. §2 표는 이미 grep 가능한 항목으로 구성됨(critic의 Positive Observation에서도 인정).
- **Action Required**: `__verification__`: §2 표 8개 누락 항목 중 ≥6개 충족 = PASS. grep keyword set ("8명/8 player", "WebSocket/socket.io", "WSOP|TDA", "responsive", "JSON message" 등) 정의.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 권고 ⑥ deep_synthesis 모드 중복 | Critical | ACCEPT | Critic |
| 2 | brief schema 변경 다운스트림 미평가 | Critical | ACCEPT | Critic |
| 3 | original_request 4중 주입 비용 미평가 | High | ACCEPT | Critic |
| 4 | 도메인 화이트리스트 일반화 불가 | High | ACCEPT | Critic |
| 5 | IntentGate 매핑·af.spec 미언급 | Medium | ACCEPT | Critic |
| 6 | 도메인 가드 stopword·fallback churn | Medium | ACCEPT | Critic |
| 7 | 검증 기준 "근접" 정성적 | Medium | ACCEPT | Critic |

### Recommendations

구현 진입 전 본 설계문서에 다음을 반영:

1. **§4 ⑥ 폐기·재작성** — `research_router._classify_primary_mode()` 신호 가중치 보정으로 변경. 5-mode 잠금 정책 명시.
2. **§4 ② schema 영향 범위 첨부** — `grep -rn` 결과 + `_fallback_brief()`/`_build_task_profile()` 동시 변경 체크리스트. 추론 Non-Goal은 별도 섹션 + collapsed.
3. **§4 ① 단일 주입화** — `project_brief.original_request` 한 곳만 추가, generator는 reference. 토큰 추정 + 한·영 혼재 evidence.
4. **§4 ⑤ 화이트리스트 → LLM relevance scoring** 전환. 화이트리스트는 옵트인 정책 파일로만.
5. **§4 ④ 결정 명시** — `IntentGate` 확장 권장(frozen build 부채 최소화) + 5+5 분류 매핑 테이블 + `af.spec hiddenimports`/`datas` 체크리스트.
6. **§4 ③ fallback 통합** — `_collect_llm_prior_knowledge`도 동일 도메인 가드 통과 의무.
7. **§6 검증 기준 정량화** — §2 표 8개 누락 항목 grep 체크리스트로 변환, ≥6 충족 = PASS.
8. **(보강) 롤백 게이트** — ① 주입은 env var (`AF_INJECT_ORIGINAL_REQUEST=1`) 가드 추가, 품질 회귀 시 즉시 무력화.
9. **(보강) churn loop 진단** — `plan_verifier.max_rounds`, `_llm_refine` 루프 위치를 §3에 grep으로 명시.
10. **(메타) Cross review 재실행 의무** — 본 round는 critic 단일 source. provider error 해결 후 재실행 권장(특히 권고 ④의 IntentGate 매핑 결정은 cross 의견 필요).