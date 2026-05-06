# Design Review: 2026-05-04-af-research-quality-gate-design

> Source: docs/2026-05-04-af-research-quality-gate-design.md
> Date: 2026-05-04 23:38
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

Cross Review는 provider 오류(Codex 세션 실패)로 결과 없음. Critic Review 단독 판정 기준 적용: Critical 2건이 존재하므로 BLOCK.

---

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [Critical] C1 게이트 위치 오류 — `prepare_documents()`는 brief를 생성하지 않음
- **Critic**: `prepare_documents()` (L741)는 `prepared_brief: PreparedBrief`를 인자로 받으며, brief는 `prepare_brief()` L723에서 이미 완료됨. §5.3 C1 pseudocode를 그대로 구현하면 이중 생성 또는 누락.
- **Cross**: 미검토 (provider 오류)
- **Judgment**: Critic의 코드 라인 인용 정확 (§2.1 `prepare_documents:741` HEAD 검증 완료). 구현 시 즉시 실패하는 사실 오류.
- **Action Required**: §5.3 C1 게이트 위치를 `prepare_brief()` L723 직후 또는 caller(`prepare()` 래퍼)로 이동. §11.4 진입점 표에 `prepare_brief` (L591) 추가.

#### 2. [ACCEPT] [Critical] A1 unconditional override가 fallback 경로를 누락
- **Critic**: `research_project_brief()`는 L1009(성공)·L1011(실패) 두 경로. `_fallback_project_brief()` (L877–917)는 `original_request` 미설정. §5.1 A1 pseudocode는 성공 경로만 커버.
- **Cross**: 미검토 (provider 오류)
- **Judgment**: 두 return path 모두 `_merge_project_brief_evidence`를 통과하므로 해당 함수 내부 단일 지점이 가장 안전한 삽입처. G1 1번 차원("사용자 원본 보존")의 단일 실패 경로.
- **Action Required**: §5.1 A1 pseudocode를 두 경로 커버로 재작성. 권장: `_merge_project_brief_evidence` 내부 또는 `finally`-equivalent 단일 종단점에서 `data["original_request"] = task_input`.

#### 3. [ACCEPT] [High] A6 산출물 위치 이중화 — `planning_dir/project_brief.json` vs `docs/research/`
- **Critic**: L722 기존 저장과 §5.1 A6 신규 저장이 동일 brief를 두 위치에 생성. `PreparedBrief.project_brief_path` 후속 참조(L761–763) 소유권 모호. `docs/research/` base path 정책 미정의.
- **Cross**: 미검토
- **Judgment**: 강한 증거. 코드 라인 2곳 직접 인용, 후속 참조자까지 추적.
- **Action Required**: 둘 중 하나로 정리. base path 결정 로직(workspace 기준 vs `target_path` vs CWD) 명시. multi-PC/frozen-build 일관성 보장 방법 추가.

#### 4. [ACCEPT] [High] frozen build 호환성 미확인 — `config/coverage_manifests/` af.spec datas 누락
- **Critic**: PyInstaller frozen build에서 `config/coverage_manifests/poker.yaml`이 `datas`에 없으면 `path.exists() == False` → 매니페스트 게이트 영구 SKIP. `af.spec:30 ('policy.yaml', '.')` 패턴이 이미 존재하나 본 문서 어디에도 언급 없음.
- **Cross**: 미검토
- **Judgment**: CLAUDE.md의 "새 core/*.py 파일은 af.spec hiddenimports에 추가" 규칙의 data 파일 equivalent. 시스템 정책 위반.
- **Action Required**: §5.2 B3에 `af.spec datas += ('config/coverage_manifests/*.yaml', 'config/coverage_manifests')` 추가 명시. R6의 "PyYAML 추가" 문장 삭제(이미 의존성).

#### 5. [ACCEPT] [High] §4 비목표 #5와 §5.1 A5 워딩 충돌
- **Critic**: "mode 분류 알고리즘 재설계 안 함"이 A5의 `_detect_domain` + derivation 3종 추가와 충돌 해석 가능.
- **Cross**: 미검토
- **Judgment**: cross-review BLOCK 유발 위험이 있는 해석 모호성. `feedback_cross_review_stale_baseline_repeat` 메모리 패턴과 일치.
- **Action Required**: §4 비목표 #5를 "`_compute_signal_scores` 7-신호 계산식과 `_select_mode` 임계값 불변. `ResearchPlan`에 derivation flag 3종 추가는 mode 분류 재설계 아님"으로 구체화.

#### 6. [ACCEPT] [High] B1 unmet_gaps 루프 종료조건 — pseudocode와 R1 mitigation 불일치
- **Critic**: pseudocode는 `unmet`이 빈 경우만 break. R1 mitigation은 "변화 없으면" break. Tavily 캐시 반환 시 pseudocode 기준으로 max_rounds 전부 소진.
- **Cross**: 미검토
- **Judgment**: 두 조건의 차이가 명시적으로 존재하며 비용 영향 있음. pseudocode가 문서 내 R1 mitigation보다 우선 해석될 위험.
- **Action Required**: pseudocode에 `prev_unmet` 비교 로직 추가. `if not unmet or unmet == prev_unmet: break`.

#### 7. [ACCEPT] [Medium] A3 poker bias 시그니처 — P1 B3에서 변경 불가피
- **Critic**: P0에서 `_AUTHORITY_DOMAINS_POKER` 상수로 고정하면 P1 B3 도메인 매개변수 추가 시 caller 다중 수정 발생.
- **Cross**: 미검토
- **Judgment**: 증거 타당. "Simplicity First" 원칙과 충돌하나 미래 변경 예측이 확실함(P1 B3 이미 계획됨). 예외적으로 선행 설계 권장.
- **Action Required**: P0 A3에서 `authority_domains: tuple[str, ...] = ()` 시그니처로 시작. dispatcher dict를 `collect_project_evidence` 레벨에서 lookup.

#### 8. [ACCEPT] [Medium] Coverage Gate BLOCK 후 사용자 회복 경로 없음
- **Critic**: Tavily 키 없는 환경 / 매니페스트 false negative 시 `raise` 외 탈출구 없음. `AF_SKIP_REVIEW_GATE=1` 패턴과 불일치.
- **Cross**: 미검토
- **Judgment**: CLAUDE.md Review-Gate 우회 패턴과 일관성 필요. §4 비목표 #3("자동 wing-it 금지") 조건이지만 강제 종료와 사용자 선택은 다름.
- **Action Required**: `AF_SKIP_COVERAGE_GATE=1` 환경변수 우회 + hook_events.log 기록 추가. 또는 `WARN-with-confirmation` 패턴 명시.

#### 9. [ACCEPT] [Medium] C4 traceability 매핑 휴리스틱 미정의
- **Critic**: `applies_to` (snake_case 매니페스트 라벨) ↔ task description (자연어, 한국어) 매칭 알고리즘 미정의. 한국어 task vs 영어 라벨 매칭 시 0 매칭 가능성.
- **Cross**: 미검토
- **Judgment**: §7 `match_keywords`가 한·영 병렬 정의로 이미 존재하지만 C4가 이를 명시적으로 참조하지 않음.
- **Action Required**: 두 옵션 중 하나 선택 명시. (a) §7 `match_keywords` substring 매칭. (b) LLM 1회 호출. 선택 근거를 D9에 기록.

#### 10. [ACCEPT] [Medium] G3 측정 정의 불완전
- **Critic**: "최근 10건"에 도메인 필터 없음 → 비포커 빌드 포함 노이즈. `assistant_score` 산출 함수 위치 미정의.
- **Cross**: 미검토
- **Judgment**: 측정 정의가 모호하면 P3 D1 게이트가 무력화됨. 증거 충분.
- **Action Required**: G3을 도메인 필터("포커 빌드만") + `assistant_score` 함수 위치 명시로 수정. 또는 G3을 informative로 강등.

#### 11. [ACCEPT] [Medium] §2.3 "1줄 수정" 주장이 실제 작업량과 불일치
- **Critic**: A1 실제 수정은 schema/override/fallback/테스트 최소 5–6곳. "1줄"이라는 표현이 cold-start 진입자의 기대를 잘못 설정.
- **Cross**: 미검토
- **Judgment**: Finding #2(fallback 누락)가 이미 증명. 문서 내 이 표현이 구현자 판단 오류를 유도.
- **Action Required**: §2.3 워딩을 "schema/override/fallback 3곳을 다뤄야 함"으로 수정.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | C1 게이트 위치 오류 | Critical | ACCEPT | Critic |
| 2 | A1 fallback 경로 누락 | Critical | ACCEPT | Critic |
| 3 | A6 저장 위치 이중화 | High | ACCEPT | Critic |
| 4 | frozen build af.spec 누락 | High | ACCEPT | Critic |
| 5 | 비목표 #5 워딩 충돌 | High | ACCEPT | Critic |
| 6 | B1 루프 종료조건 불일치 | High | ACCEPT | Critic |
| 7 | A3 poker bias 시그니처 | Medium | ACCEPT | Critic |
| 8 | Coverage Gate 회복 경로 없음 | Medium | ACCEPT | Critic |
| 9 | C4 매핑 알고리즘 미정의 | Medium | ACCEPT | Critic |
| 10 | G3 측정 정의 불완전 | Medium | ACCEPT | Critic |
| 11 | §2.3 "1줄 수정" 과소 기술 | Medium | ACCEPT | Critic |

---

### Recommendations

구현 착수 전 문서에서 수정할 사항:

1. **§5.3 C1 재작성**: 게이트 위치를 `prepare_brief()` L723 이후로 이동. §11.4에 `prepare_brief (L591)` 진입점 추가.
2. **§5.1 A1 pseudocode 재작성**: 성공/실패 두 경로 모두 커버. `_merge_project_brief_evidence` 내부 또는 단일 종단점 명시.
3. **A6 저장 위치 정리**: `planning_dir/project_brief.json`과 `docs/research/` 중 하나로 통일. base path 정책 명시.
4. **§5.2 B3에 af.spec datas 추가**: `('config/coverage_manifests/*.yaml', 'config/coverage_manifests')`.
5. **§4 비목표 #5 구체화**: `_compute_signal_scores` 불변 범위 명확화.
6. **B1 pseudocode에 `prev_unmet` 비교 추가**: R1 mitigation과 정합.
7. **Coverage Gate 우회 경로 추가**: `AF_SKIP_COVERAGE_GATE=1` 환경변수 또는 `WARN-with-confirmation`.
8. **C4 매핑 알고리즘 선택 명시**: §7 `match_keywords` 활용 여부 결정.
9. **§2.3 워딩 수정**: "1줄"을 "schema/override/fallback 3곳" 으로 교체.

> Cross Review 미수행 상태. Codex 회복 후(§0 `2026-05-05 15:37 KST↑`) 재발화 권장.