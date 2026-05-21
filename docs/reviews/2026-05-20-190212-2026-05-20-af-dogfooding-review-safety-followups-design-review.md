# Design Review: 2026-05-20-af-dogfooding-review-safety-followups

> Source: docs/2026-05-20-af-dogfooding-review-safety-followups.md
> Date: 2026-05-20 19:02
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

근거: Critical 없음, High 2건 + Medium 4건 + Low 2건. Cross Review는 provider error로 산출물 없음 (Codex 부팅 배너만 출력 후 잘림 — AF 정책상 가용 프로바이더 0건 = SKIP 통과). 따라서 모든 판정은 Critic 단독 근거의 강도로 결정.

### Aggregated Findings (8 total)

#### 1. [ACCEPT] [High] Problem 4의 단일소스 패치가 enqueue_agent_review.py 두 사이트(`:122`, `:131`)를 누락
- **Critic**: 패치는 review_gate ↔ t3_classifier만 커플링, enqueue_agent_review.py의 v1 리터럴 2곳은 그대로. v2 bump 시 텔레메트리 행 일부가 v1로 태깅되어 `t3_skip_report.py` 집계 손상.
- **Cross**: not flagged (provider error)
- **Judgment**: enqueue_agent_review.py:122/131 리터럴 위치 명시 + 두 경로 모두 `decision=="require_t3"` 이므로 현재는 forensic-only라는 분석까지 정확. 텔레메트리 정합성 회귀 위험은 실재.
- **Action Required**: 본 문서 §"문제 4 제안 패치"를 (a) enqueue_agent_review.py import 추가까지 확장하거나, (b) "두 사이트는 require_t3 전용이라 게이트 영향 없음 — 텔레메트리 v1/v2 혼재만 발생" 을 명시적 비목표로 기재.

#### 2. [ACCEPT] [High] Problem 4가 두 보호 모드를 하나의 "대안"으로 융합 — 운영 kill-switch 상실
- **Critic**: import 커플링은 `_T3_SKIP_CLASSIFIER_VERSION`을 "classifier 재학습 없이 in-flight skip만 무효화" 하는 운영 레버로 쓸 수 있는 길을 막는다. 의도적 듀얼 스트링이라면 detection-logging만 채택해야 함. 문서가 이를 평가 안 함.
- **Cross**: not flagged
- **Judgment**: 위협 모델 진술 없이 두 보호를 alternatives로 제시한 것은 설계 결함. import vs detection 선택이 운영 절차(stuck queue 해소법)에 직결됨.
- **Action Required**: §"문제 4"에 threat-model 단락 추가 — "skip 무효화가 classifier 재배포 없이 필요한가?" 질문에 Y/N 답을 먼저 정하고, Y면 detection-only, N이면 import 커플링 채택. 결정 근거 1~2줄.

#### 3. [ACCEPT] [Medium] Problem 2 "단순 텍스트 PR" 블래스트 진단 과소평가
- **Critic**: `scripts/prompts/code_critic.txt`는 hook_runner가 af-critic에 주입하는 LLM 권한 프롬프트. `review_gate.py:124`의 `_critic_t3_advisory(state) == "no"` 분기를 직접 흔든다. .py 비대상으로 게이트 우회 = **검증을 더 강화할 사유**.
- **Cross**: not flagged
- **Judgment**: 정확. T3 advisory 권한 라인을 바꾸는 변경을 "단순 텍스트"로 마킹하는 것은 위험.
- **Action Required**: §"진입 시 체크리스트"에 단계 추가 — annotation-only diff와 comment-only diff에 대해 수동 af-critic dry-run을 돌려 t3_required가 각각 `yes/unknown`, `no` 인지 확인.

#### 4. [ACCEPT] [Medium] Problem 3 패치가 af-critic 외 agent에 `--t3-required` 묵음 무시
- **Critic**: `record_review_done`은 `agent == "af-critic"`일 때만 t3_required를 읽음(`review_gate.py:338`). CLI는 무조건 전달 → 잘못 쓰는 운영자가 에러도 효과도 없이 헤맴.
- **Cross**: not flagged
- **Judgment**: 라인 인용 정확. 2줄 가드로 충분.
- **Action Required**: `_cli`에서 `args.t3_required is not None and agent != "af-critic"` 분기 — stderr 경고 또는 `sys.exit(2)`. 둘 중 어느 쪽이든 명시.

#### 5. [ACCEPT] [Medium] Blueprint 갱신 계획이 §12만 — CLAUDE.md "§0~§11 + §12" 규칙 위반
- **Critic**: review_gate.py CLI surface 변경 → §0 파일 표 + §3.x Control Plane 행 갱신 필요. import topology 변경 → 동일. §12만 기재 시 다음 구현자가 구조 갱신을 누락하는 패턴 재현.
- **Cross**: not flagged
- **Judgment**: CLAUDE.md "Blueprint 업데이트 트리거" 표(클래스·메서드 변경 → §3) 정확히 적용. memory `feedback_blueprint_section3_manual.md` 정책과 일치.
- **Action Required**: §"진입 시 체크리스트" step 4 교체 — "Blueprint §0 (review_gate.py 라인 수·역할), §3.x (Control Plane / review_gate CLI 신규 옵션 + classifier_version single-source), §12 이력".

#### 6. [ACCEPT] [Medium] Problem 1 "안전 구멍 없음" 주장이 회귀 테스트 존속에 암묵 의존
- **Critic**: 모듈 docstring 오류를 고치더라도 다음 엔지니어가 `visit_AnnAssign`를 docstring 근거로 추가 + `test_annotation_change_requires_t3`를 같이 수정하면 안전 구멍 열림. 인라인 가드 코멘트가 더 견고.
- **Cross**: not flagged
- **Judgment**: 합리적 — 동일 클래스 회귀가 code-review.md 이력에 존재한다는 지적도 타당.
- **Action Required**: `_strip_docstring` 옆에 `# DO NOT also strip annotations — annotations are runtime-observable via __annotations__ (see 2026-05-20-af-dogfooding-review-safety.md §137)` 코멘트 추가를 패치에 포함.

#### 7. [ACCEPT] [Low] "1주 수집 후 재진입"의 절대 날짜 부재
- **Critic**: parent doc에 1주 근거 없음, 게이팅 조건 만료 시점 불명.
- **Cross**: not flagged
- **Judgment**: 미세 결함이나 미래 reader 디스앰비뮤에이션에 유용.
- **Action Required**: §"비목표" 첫 문장에 "최단 재진입: 2026-05-27 (telemetry 시작 2026-05-20 + 7일)" 명시.

#### 8. [ACCEPT] [Low] 검증 pytest 목록에 `tests/test_text_integrity.py` 누락
- **Critic**: parent 설계가 `core/text_integrity.py`+`tests/test_text_integrity.py`를 같은 safety-layer로 묶었지만 후속 체크리스트는 빠뜨림. 4패치가 직접 안 건드려도 silent 회귀 시 감지 불가.
- **Cross**: not flagged
- **Judgment**: 비용 0 추가, 안전 마진 확보.
- **Action Required**: §"진입 시 체크리스트" step 2의 pytest 호출에 `tests/test_text_integrity.py` 추가.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Problem 4 enqueue_agent_review.py 누락 | High | ACCEPT | Critic |
| 2 | Problem 4 detection vs coupling threat-model 누락 | High | ACCEPT | Critic |
| 3 | Problem 2 prompt 블래스트 과소평가 | Medium | ACCEPT | Critic |
| 4 | Problem 3 `--t3-required` 비-critic agent 묵음 무시 | Medium | ACCEPT | Critic |
| 5 | Blueprint §0/§3 갱신 누락 | Medium | ACCEPT | Critic |
| 6 | Problem 1 인라인 가드 코멘트 부재 | Medium | ACCEPT | Critic |
| 7 | 1주 날짜 anchoring | Low | ACCEPT | Critic |
| 8 | test_text_integrity.py 누락 | Low | ACCEPT | Critic |

### Recommendations

구현 진입 전, **본 문서를 다음 순서로 패치**:

1. **§"문제 4"에 위협 모델 단락 추가** — kill-switch 운영 필요성 Y/N 결정 → import vs detection-only 확정.
2. **결정 결과에 따라 §"문제 4 제안 패치" 재작성**:
   - import 채택 시 → enqueue_agent_review.py:122, :131도 패치 범위에 포함 (또는 비목표로 명시).
   - detection-only 채택 시 → review_gate에 mismatch 로깅, 듀얼 스트링 유지를 명문화.
3. **§"문제 1 제안 패치"에 인라인 코멘트 추가** (`_strip_docstring` 옆 한 줄).
4. **§"문제 2"에 블래스트 재평가** + **§"진입 시 체크리스트"에 dry-run step** 추가.
5. **§"문제 3 제안 패치"에 agent ≠ af-critic 가드 2줄** 추가.
6. **§"진입 시 체크리스트"**:
   - step 2 pytest 목록에 `tests/test_text_integrity.py` 추가.
   - step 4를 "Blueprint §0 + §3.x + §12 갱신"으로 교체.
7. **§"비목표"에 절대 날짜** (2026-05-27) 추가.

문서 보정 후 본 follow-ups 문서에 다시 `af-cross-review`만 1회 — Cross Review provider 정상 응답 확인 후 진행. 코드 구현은 그 다음.