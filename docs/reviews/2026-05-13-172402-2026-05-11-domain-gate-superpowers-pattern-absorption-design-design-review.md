# Design Review: 2026-05-11-domain-gate-superpowers-pattern-absorption-design

> Source: docs/2026-05-11-domain-gate-superpowers-pattern-absorption-design.md
> Date: 2026-05-13 17:24
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: **BLOCK**

Critic flagged 1 Critical (identifier regression — same class of bug the design itself claims to have fixed) + 3 High. Cross review **failed to execute** (provider error mid-stdin read — Codex CLI shown but no review content returned). Aggregation proceeds on critic-only evidence; all critic findings reference concrete file:line citations, so evidence is strong despite single source.

> ⚠️ **Cross-review unavailable** — Codex provider returned only its session header, no findings. This is a Tier-3 fan-out failure (CLAUDE.md "Tier 3 … 1개 이상 인증 만료가 있으면 BLOCK + 재인증 안내"). Domain-gate design **cannot be unblocked by this judgment alone** until cross-review actually runs.

---

### Aggregated Findings (9 total + 4 gaps)

#### 1. [ACCEPT] [Critical] `"local"` 토큰 — `blast_radius` enum에 부재 (§3.3 line 178 / 호출 스택 line 149)
- **Critic**: 코드 enum은 `{"isolated","module","cross_module","system_wide"}` (`core/control/change_impact.py:35`, `:243` `return "isolated"`). 본 설계가 "5/13 review Critical #1 해소 (`system`→`system_wide`)"를 자랑하면서 동일 종류의 회귀 발생 — 식별자 회귀 #4.
- **Cross**: not executed.
- **Judgment**: 코드 직접 인용 + 메모리 `feedback_design_doc_grep_before_write.md` 3회 선례와 일치. 반박 불가.
- **Action Required**: `"local"` → `"isolated"` 일괄 치환(§3.3 line 178, §10.2 단계 4, 호출 스택 line 149). §3.5 검증 #6에 토큰 화이트리스트 `{"isolated","module","cross_module","system_wide"}` 명시 + fail-closed 정책 추가.

#### 2. [ACCEPT] [High] `blast_radius=="system_wide"` 단독 트리거가 너무 넓음
- **Critic**: `change_impact.py:58` `_SYSTEM_WIDE_PATTERNS = ["core/", "core\\"]` + `:222-227`로 인해 `core/*.py` 1줄 typo도 즉시 `system_wide` → 도메인 리뷰 강제. AF 자체 진화(거의 모든 core/*)가 매번 게이트 진입 → 사용자가 `AF_SKIP_DOMAIN_REVIEW` 우회 학습 → 게이트 시어터화.
- **Cross**: not executed.
- **Judgment**: 코드 패턴이 너무 광범위하다는 점 정확. CLAUDE.md `AF_SKIP_REVIEW_GATE` 우회 학습 사례 있음.
- **Action Required**: 단계 2 발효 시 트리거 협소화 조건 §10.2에 명시 — `affected_files ≥ N` AND `work_kind != "bugfix"` 같은 보조 조건 또는 단계 1 측정 후 의무적 재조정.

#### 3. [ACCEPT] [High] `project_brief["route"]` dict 키 의존 — 시그니처 안정성 부재
- **Critic**: `project_pipeline.py:819` `project_brief["route"] = route or {}` 는 prepare_brief 내부 규약일 뿐. `PreparedBrief` dataclass(`:41-56`)는 `route` 필드 없음. 향후 이름변경 시 `.get()` 패턴이 `{}` → work_kind 무음 오분류.
- **Cross**: not executed.
- **Judgment**: dataclass 1차 필드 vs dict 키 의존 위험은 일반론적으로 정확. 코드 인용 검증됨.
- **Action Required**: `PreparedBrief`에 `route: dict = field(default_factory=dict)` 추가 + `prepare_brief()` 양쪽 채움 + `prepare_documents()`는 `prepared.route` 사용. §3.2 표에 한 줄 추가.

#### 4. [ACCEPT] [High] `_DOMAIN_REVIEW_FILE` 격리로 사후 verdict 변조 검출 불가
- **Critic**: `_DOC_FILES`(`:81-87`)에서 격리하면 `check_validity()`(`:338`)/`compute_snapshots()`(`:378`)가 verdict 변경 감지 못함. 승인 후 PASS↔BLOCK 변조 가능 — race window.
- **Cross**: not executed.
- **Judgment**: 격리 결정의 부작용을 정확히 식별. 둘 중 하나 채택 필요 — (A) 별도 snapshot 키 또는 (B) approval-gate.md에 verdict stamp.
- **Action Required**: §3.2 (B)안 권장 — `approve()` 시점 verdict를 `## Metadata - approved_verdict: PASS`로 stamp, 이후 게이트는 stamp만 신뢰. 명세 1단락 §3.2에 추가.

#### 5. [ACCEPT] [Medium] verdict 파서 에러 메시지 채널 미명세
- **Critic**: `last_block_reason` 분기는 정의됐으나 `agent_launcher.py:437-441`에 사용자 가시 메시지 매핑 부재. `- verdict: pass` (소문자) 입력 시 "approval-gate.md를 찾을 수 없습니다" 같은 오해 메시지로 차단.
- **Cross**: not executed.
- **Judgment**: §3.2가 "메시지 분리" 약속했으나 구체 문구 명세 없음 — Phase A 구현자 임의 결정 위험.
- **Action Required**: §3.2에 `last_block_reason` → 사용자 메시지 4행 매핑표 추가.

#### 6. [ACCEPT] [Medium] §4.4 "우선순위" 숫자 컬럼 잔재
- **Critic**: §4.3은 우선순위 공식 폐기 선언, §4.4 표는 숫자(-3, -1, 8, 9 등) 그대로 → 검토자가 정렬 기준으로 오해.
- **Cross**: not executed.
- **Judgment**: 문서 내부 일관성 문제. 트리비얼하게 검증/수정 가능.
- **Action Required**: §4.4 "우선순위" 컬럼 삭제 또는 "[retracted]" 표기. Phase B 진입 전 §4.3 적용 결과(즉시/선택적/보류) 단일 컬럼으로 합치기.

#### 7. [ACCEPT] [Medium] §3.5 검증 5 부수효과 격리 미명세
- **Critic**: `intake.py:262` `UnifiedMemoryFacade.get_instance()` 전역 singleton + `:126` `_open_ledger_run`이 실파일 append → 멀티 PC 회귀 위험 + pytest 병렬 차단.
- **Cross**: not executed.
- **Judgment**: 코드 부수효과 정확. 테스트 격리 명세 1줄로 해소 가능.
- **Action Required**: §3.5 검증 5에 (a) `normalize()` monkey-patch 또는 (b) `tmp_path` ledger 격리 명시.

#### 8. [ACCEPT] [Medium] `inspired_by` 메타 키가 SKILL.md 스키마 미존재
- **Critic**: 기존 frontmatter 키 13종에 `inspired_by` 부재. `core/skill_metadata.py` / `skill_loader.py`의 미지 키 처리 미검증 — drop 시 attribution 손실, validation error 시 Phase C 흡수 스킬 로드 실패.
- **Cross**: not executed.
- **Judgment**: Phase C 종속성 정확. Phase A에선 비차단이나 Phase C 진입 조건으로 명시 필요.
- **Action Required**: Phase C 진입 전 `core/skill_metadata.py`에 `inspired_by: str = ""` 추가 + 회귀 테스트. §7.2 수정 파일 표에 한 줄 추가.

#### 9. [HOLD] [Low] "38개 자체 스킬" 수치 검증
- **Critic**: 실측 `skills/` 33 항목 (registry 제외 시 더 적음).
- **Cross**: not executed.
- **Judgment**: 카운트 기준이 외부 캐시 포함인지 등 불명확. 차단 사유 아님. Phase B 매트릭스 작성 시 실측 갱신으로 충분.
- **Question for Author**: §1.1의 "38"이 어떤 카운트 기준인가? (`skills/` 디렉터리 vs `registry.yaml` vs 외부 캐시 포함)

#### 10. [ACCEPT] [Medium] Missing: Frozen build env var 동작 명세 부재
- **Critic**: `AF_SKIP_DOMAIN_REVIEW`가 PyInstaller frozen 환경 `os.environ` lookup에서 정상 동작하는지 명세 없음. 회귀 위험은 낮으나 §3.5 검증 항목 추가 권장.
- **Action Required**: §3.5에 frozen 빌드 환경변수 검증 1행 추가.

#### 11. [ACCEPT] [Medium] Missing: ADR 충돌 해소 자동화 부재
- **Critic**: §3.4 "동일 분 내 2건 시 git merge에서 수동 정정" — pre-commit 자동 검증 없음.
- **Action Required**: Phase A 산출에 `scripts/check_adr_id_uniqueness.py` 1회용 동봉 또는 pre-commit hook 추가.

#### 12. [ACCEPT] [Medium] Missing: `architecture-change` 거부 결정의 영속성
- **Critic**: §3.3 합의 노트만 존재, ADR로 stamp 안 됨 → 6개월 뒤 재논의 비용.
- **Action Required**: Phase A 산출에 ADR-0002 (또는 별 번호)로 거부 결정 박제.

#### 13. [ACCEPT] [Medium] Missing: 단계 전환 측정 데이터 추출 스크립트
- **Critic**: §10.2 측정 데이터 첨부 의무 명시, 추출 스크립트 부재.
- **Action Required**: Phase A에 `scripts/domain_gate_stats.py` (`data/skill-usage.jsonl` 또는 `.af_runtime/control/run_ledger.jsonl` 집계) 동봉.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `"local"` 식별자 회귀 #4 | Critical | ACCEPT | Critic |
| 2 | `system_wide` 트리거 과광역 | High | ACCEPT | Critic |
| 3 | `project_brief["route"]` dict 키 의존 | High | ACCEPT | Critic |
| 4 | `_DOMAIN_REVIEW_FILE` 격리 → verdict 변조 race | High | ACCEPT | Critic |
| 5 | verdict 파서 에러 메시지 미명세 | Medium | ACCEPT | Critic |
| 6 | §4.4 "우선순위" 잔재 | Medium | ACCEPT | Critic |
| 7 | §3.5 검증 5 부수효과 격리 미명세 | Medium | ACCEPT | Critic |
| 8 | `inspired_by` 스키마 부재 | Medium | ACCEPT | Critic |
| 9 | "38 스킬" 수치 | Low | HOLD | Critic |
| 10 | Frozen 빌드 env var 명세 | Medium | ACCEPT | Critic (gap) |
| 11 | ADR ID 유일성 자동화 부재 | Medium | ACCEPT | Critic (gap) |
| 12 | `architecture-change` 거부 ADR 박제 | Medium | ACCEPT | Critic (gap) |
| 13 | 단계 전환 측정 스크립트 부재 | Medium | ACCEPT | Critic (gap) |

---

### Recommendations

**구현 차단 — 다음 항목 해소 후 재리뷰 필수**:

1. **Finding #1 (Critical)** — `"local"` → `"isolated"` 일괄 치환 + §3.5 검증 #6에 토큰 화이트리스트 4개 못 박기. `grep -n 'blast_radius' core/control/change_impact.py` 결과 본문에 인용으로 박제.
2. **Cross-review 재실행 의무** — Codex 프로바이더 인증/세션 상태 확인 후 `af-cross-review` 재발화. CLAUDE.md Tier 3 정책상 외부 프로바이더 실패는 BLOCK + 재인증 안내가 정답. 본 judgment 단독으로는 게이트 통과 부적격.
3. **Finding #2, #3, #4 (High 3건)** — Phase A 산출에 포함 (트리거 협소화 조건, `PreparedBrief.route` 승격, verdict stamp 또는 별도 snapshot 키).
4. **Finding #5~#8, #10~#13 (Medium 8건)** — Phase A 시작 전 본 설계 문서 자체 보강(§3.2, §3.5, §4.4, §7.2, §10.2).
5. **Finding #9** — 저자가 카운트 기준 명시. 비차단.

**규칙 강화 권장 (메모리 갱신)**:

- `feedback_design_doc_grep_before_write.md` 메모리에 회귀 #4 사례 1줄 추가 — 3회 → 4회. `feedback_design_review_rounds_stop_rule.md`의 3라운드 cap 도달 임박.
- 본 설계는 3차 정정에 진입했으므로 **4차 freeze 임계**에 근접. Finding #1, #4 제외 항목은 ADR로 이월 검토.