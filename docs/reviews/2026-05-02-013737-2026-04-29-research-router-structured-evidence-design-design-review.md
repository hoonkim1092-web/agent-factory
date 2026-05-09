# Design Review: 2026-04-29-research-router-structured-evidence-design

> Source: docs/2026-04-29-research-router-structured-evidence-design.md
> Date: 2026-05-02 01:37
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

5 Critical/High findings overlap or independently confirm structural inconsistencies in v1.3. Both reviewers found enough hard evidence (line numbers, code refs) to require revision before Phase 1a implementation.

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] §4.4.5 detector 코드 분기 누락 + 8인 포커 시나리오 실현 불가
- **Critic** (#1): §4.4.4 prose는 `op>=3 OR deep>=2 OR external_stack>=3` 3분기인데 §4.4.5 코드는 `op>=3` 단일 분기. 포커 시나리오는 `op=1, ext=6` — 코드상 어떤 deep gap도 emit 못 함. §10.1이 "두 gap emit"인데 코드는 한 gap만 추가 후 return. `final_mode` 인자명도 의미 모순.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 코드 예시 자체가 prose/escalation 시나리오와 직접 모순 — 구현자가 코드 그대로 쓰면 §10.1 흐름 불가능. evidence 명확.
- **Action Required**: §4.4.5 코드에 `external_stack>=3`/`deep>=2` 분기 추가, gap emit 매핑 표 신설(`op>=3→MULTI`, `deep>=2→ARCHITECTURE_LOW`, `ext>=3→MULTI+HIGH_RISK_CAPABILITY`), 인자명 `final_mode`→`current_mode`로 §0/§4.4.5/§10.1 일괄 변경.

#### 2. [ACCEPT] [Critical] Fixture 라벨 schema vs 본문 충돌 + 포커 라벨 알고리즘 모순
- **Critic** (#2): §11 항목 7은 `expected_mode` (옛 단일 라벨), §12.5는 `expected_initial_mode`/`expected_final_mode` (R2-1 신규). §4.2.1 calibration 기준도 `expected_mode`. 구현자가 §11 따르면 §12.5 두 라벨 정확도 평가 불가.
- **Cross** (#1): §4.2.1 알고리즘은 포커 → primary `fast_synthesis` + secondary `fresh_lookup`이지만, §12.5 fixture 라벨은 `expected_initial_mode = "fresh_lookup"`. 라벨이 알고리즘과 직접 모순.
- **Judgment**: ACCEPT (두 발견 합쳐서 동일 영역). schema 누락 + 값 모순 둘 다 확인. evidence 모두 line 단위.
- **Action Required**: §11 line 1088 `expected_mode` → `expected_initial_mode, expected_final_mode`. §4.2.1 line 269 동일 교체. §12.5 포커 fixture를 `expected_initial_mode="fast_synthesis"`, `expected_secondary_modes=["fresh_lookup"]`로 정정 또는 "initial_mode = effective fetch mode (Tavily 호출 여부 기준)"로 재정의. fixture JSON 스키마 예시 1줄 §11에 추가.

#### 3. [ACCEPT] [High] §6.5 quality-tier 용어 충돌 (unclassified vs no-op)
- **Critic** (#3): R2-2가 §4.4.2/§4.4.3에 `no-op`/`unmapped` 용어 분리를 도입했지만 §6.5 line 695, 704는 옛 `unclassified` 그대로. v1.3 정식 용어 vs §6.5 직접 충돌.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 같은 PR 안에서 §4.4.3과 §6.5가 직접 모순 — 구현자가 §6.5 보면 잘못된 분류 적용.
- **Action Required**: §6.5 line 695 `quality/unclassified` → `quality/no-op/unmapped`. line 704 `unclassified` → `no-op` + "(§4.4.3 'no-op' 분류)" 명시.

#### 4. [ACCEPT] [High] Verifier gap 문자열이 enum value와 일치하지 않음
- **Critic**: not flagged
- **Cross** (#3): 현 verifier는 `"no_external_evidence (web or llm_prior)"` 같은 free-form 출력. ResearchGap.value 매핑 직접 키 매칭 실패 — gap-driven escalation 코드 경로 불가능.
- **Judgment**: ACCEPT. 코드 evidence(`core/research_verifier.py:84, :246`) 명확. 단일 reviewer지만 실재 코드 스냅샷.
- **Action Required**: `VerificationResult.gaps` 출력 형식을 `ResearchGap.value` exact string으로 통일. 인간 가독 메시지는 `gap_details`/`diagnostics` 분리. §5/§9에 schema contract 1줄 추가.

#### 5. [ACCEPT] [High] §9.2 verifier 4-metric ↔ §6.5 quality-tier 3-gap 누락
- **Critic** (#5): §9.2의 4 metric 중 `primary_source_ratio`만 emit할 quality-tier enum 없음. v1.2 changelog는 "Phase 1b enum 추가 PR 불필요"라 했지만 4번째 metric이 빠져 합의 위반.
- **Cross**: not flagged
- **Judgment**: ACCEPT. metric 정의(§9.2)와 enum 사전등록(§6.5) 직접 카운트 불일치 — 산수상 명확한 누락.
- **Action Required**: §6.5 enum에 `PRIMARY_SOURCE_AUTHORITY_LOW = "primary_source_authority_low"` 추가, §4.4.2 매핑 표에도 추가. 또는 §9.2에서 `primary_source_ratio`를 `SOURCE_PACK_TOO_SHALLOW` 가중합 component로 흡수하는 정의 명시.

#### 6. [ACCEPT] [High] ResearchPlan 컨트랙트 underspecified
- **Critic**: not flagged (단, #10에서 시그니처 모호성 일부 언급)
- **Cross** (#2): pseudocode는 `mode/secondary/scores`만 반환, §6.1 JSON은 `requires_web/requires_tavily_extract/requires_notebooklm/risk_level` 추가 요구. 저장 필드인지, computed인지, evidence-only인지 미정의.
- **Judgment**: ACCEPT. design 내부 inconsistency. evidence 명확(line 248 vs 573).
- **Action Required**: §0 또는 §4.4에 `ResearchPlan` dataclass 전체 필드 정의 + mode→tool-gate 단일 표(`requires_web/requires_tavily_extract/requires_notebooklm/requires_deep_source_pack/deep_capability_level` 도출 규칙) 추가.

#### 7. [ACCEPT] [High] content_full 크기 cap + prompt 경계 정의 누락
- **Critic**: not flagged (단, "Missing from Design — Cost/latency 추정"과 인접)
- **Cross** (#4): `content[:500]` 제거가 cap 없이 들어가면 work_item_generator가 brief 전체를 prompt에 직렬화하는 현 경로(line 516)에서 컨텍스트 폭주. compaction 미구현(code-review.md M10).
- **Judgment**: ACCEPT. 실제 prompt 직렬화 경로 코드 evidence 있음. 운영 위험 명확.
- **Action Required**: `source_pack`은 full text 보존, `content_full`은 source당/pack당 cap 명시(예: source당 8KB, pack당 32KB). `project_brief`로는 selected excerpt + source_id만 전달. `source_pack_chars`를 "정규화 후 실제 prompt 가용 길이"로 재정의.

#### 8. [ACCEPT] [High] research_log.jsonl 경로/append semantics 모호 + 동시성
- **Critic** ("Missing"): Multi-PC/Windows 경로 처리, file_lock, atomic write 미정의 — code-review M10 답습.
- **Cross** (#5): `projects/<workspace>` 경로가 이미 absolute root인 `target_workspace`와 결합 시 nested 오류 가능. JSONL schema/locking 미정의.
- **Judgment**: ACCEPT (두 발견 합쳐서 동일). 경로 + 동시성 둘 다 미정의.
- **Action Required**: §6.6에 `os.path.join(target_workspace, "data", "research_log.jsonl")` 명시. 1줄 JSON schema 정의(`run_id, generated_at, initial_mode, final_mode, gaps, tool_calls`). append는 `core.file_lock.locked_file()` 사용 명시. frozen 빌드 + multi-PC 경로 결정 규칙 1줄 추가.

#### 9. [ACCEPT] [Medium] §10.1 token-level OR 매칭 substring 중복 규칙 모호
- **Critic** (#4): "풀네트워크" 토큰이 "네트워크"+"풀네트워크" 두 키워드 substring → 카테고리 +2 vs +1 모호. R2-1 changelog는 "boolean OR"만 명시. ext_stack=6 vs 5 차이.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 포커 시나리오 점수가 토큰화 규칙에 따라 변하는데 fixture calibration이 이 모호성 위에서 진행될 위험.
- **Action Required**: §4.2 line 207에 1줄 보강 — "각 키워드 K는 substring 1회 이상 발견 시 카테고리 +1; 동일 토큰이 같은 카테고리의 여러 키워드 substring일 경우 키워드별로 각각 +1" 또는 "키워드 set은 prefix-free" 중 한쪽 채택.

#### 10. [ACCEPT] [Medium] skill_evolution 부착 시점/주체 미정의
- **Critic** (#6): "후속 단계"가 어느 컴포넌트, 어느 시점인지 미정의. fixture `expected_secondary_modes` 비교 시점도 모호.
- **Cross** (#7 — HOLD): 같은 영역. _select_mode는 부착 안 함, capability gap 생산자 미정의.
- **Judgment**: ACCEPT (양쪽 동일 영역, evidence 충분). HOLD가 아닌 ACCEPT — 부착 주체/시점이 결정되지 않으면 fixture 라벨링 불가.
- **Action Required**: §4.2.1 또는 §11 Phase 1a에 1줄 — "skill_evolution은 router에서 부착 안 함. `Himari.research_project_brief()`가 capability gap detect 시 brief 출력 `secondary_modes`에만 append. fixture `expected_secondary_modes`는 router 직후 시점만 비교, skill_evolution 제외."

#### 11. [ACCEPT] [Medium] §11 항목 4 fallback "유지" vs 항목 5 시그니처 변경 충돌
- **Critic** (#8): 같은 PR에서 항목 5가 `_evidence_fn(**kwargs)`로 확장되면 항목 4의 TypeError fallback이 dead code.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 같은 Phase 1a PR 내 자기모순.
- **Action Required**: 둘 중 하나 선택 — (a) 항목 5와 항목 4 fallback을 같은 PR에서 동시 제거 (clean slate), 또는 (b) 항목 5 차기 PR로 분리. v1.2 의도가 (a)면 항목 4 문구를 "fallback 제거 + deprecation 로그"로 명시.

#### 12. [ACCEPT] [Medium] §6.6 mode_distance 정의 누락
- **Critic** (#7): mode가 ordering 없는 enum인데 distance 측정. §12.4 임계 "≥2"는 단일 retry 정책에서 영원히 0%.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 정의 없는 metric은 측정 불가.
- **Action Required**: §6.6/§4.4에 정의 1단락 — "mode_distance: 0 if initial==final else 1 (단일 retry 한정). multi-hop 도입 시 ordered tier(fast=0, fresh/archive=1, deep/live=2)로 재정의." §12.4 ≥2 임계는 Phase 3 multi-hop 시점 기준임을 명시.

#### 13. [HOLD] [Medium] §11 frozen 빌드 import smoke 검증 누락
- **Critic** (#9): hiddenimports 등록만으로 cyclic import/모듈 부작용 검증 안 됨.
- **Cross**: not flagged
- **Judgment**: HOLD. 합리적 우려이나 v1.4 design BLOCK 결정에 필수는 아님. "구현 단계 체크리스트" 항목으로 흡수 가능.
- **Question for Author**: 이 검증을 §11 항목 6에 1줄 추가할지, 아니면 별도 PR-체크리스트 문서로 분리할지.

#### 14. [REJECT] [Low] §4.4.5 클래스/메서드 시그니처 모호
- **Source**: Critic (#10)
- **Original Finding**: `self._compute_signal_scores`인데 `self` 인자 누락.
- **Rejection Reason**: 의사코드 관행 (self 생략) — 구현자에게 혼동 야기 가능성 낮음. ACCEPT #6의 ResearchPlan 컨트랙트 정의에 클래스 형태가 자연 흡수됨.

#### 15. [REJECT] [Low] Optional project_brief fields 호환성 우려
- **Source**: Cross (#6) — Cross 자체가 REJECT
- **Original Finding**: 신규 필드(`required_capabilities` 등)가 downstream 깨뜨릴 수 있음.
- **Rejection Reason**: Cross가 직접 코드 검증해 reject. `data = dict(brief or {})` extras 보존 + downstream known field 읽기로 호환성 확보. 본 reviewer도 동일 evidence 확인.

### Summary Table

| #  | Title | Severity | Verdict | Source |
|----|-------|----------|---------|--------|
| 1  | §4.4.5 detector 분기 누락 | Critical | ACCEPT | Critic |
| 2  | Fixture 라벨 schema + 포커 모순 | Critical | ACCEPT | Both |
| 3  | §6.5 unclassified vs no-op | High | ACCEPT | Critic |
| 4  | Verifier gap free-form vs enum | High | ACCEPT | Cross |
| 5  | §9.2 4-metric ↔ §6.5 3-gap | High | ACCEPT | Critic |
| 6  | ResearchPlan 컨트랙트 underspec | High | ACCEPT | Cross |
| 7  | content_full cap/prompt 경계 | High | ACCEPT | Cross |
| 8  | research_log.jsonl 경로+동시성 | High | ACCEPT | Both |
| 9  | Substring 중복 매칭 규칙 | Medium | ACCEPT | Critic |
| 10 | skill_evolution 부착 시점 | Medium | ACCEPT | Both |
| 11 | §11 항목 4/5 충돌 | Medium | ACCEPT | Critic |
| 12 | mode_distance 정의 | Medium | ACCEPT | Critic |
| 13 | frozen import smoke | Medium | HOLD   | Critic |
| 14 | §4.4.5 시그니처 self 누락 | Low | REJECT | Critic |
| 15 | Optional brief fields | Low | REJECT | Cross |

### Recommendations
- **v1.4 BLOCK 해소 우선순위 (Phase 1a 진입 전 필수)**: #1, #2 (Critical 2건) 먼저 정정 — 설계 자체가 코드/fixture 레벨에서 모순.
- **High 5건 동시 정정**: #3 (§6.5 용어), #4 (verifier gap schema), #5 (4번째 enum), #6 (ResearchPlan dataclass), #7 (content_full cap), #8 (research_log 경로/lock).
- **Medium 4건 1줄씩 보강**: #9 substring 규칙, #10 skill_evolution 부착, #11 fallback/시그니처 정리, #12 mode_distance 정의.
- **HOLD 1건 답변 후 확정**: #13 frozen smoke를 §11 항목 6에 통합할지 분리할지 author 선택.
- **v1.4 changelog**: R3 BLOCK ID(#1, #2)와 R3 신규 발견(#3~#12) 분리 표시. 정정 후 단일 설계문서 정책상 af-cross-review만 재트리거 (max_rounds=2 cap 도달 — R4가 마지막 자동 라운드, 이후 사용자 수동 결정).
- **메모리 업데이트**: `project_research_router_v12_block_pending.md`를 v1.3 BLOCK 4건 → v1.3 R3 결과(#1~#8 ACCEPT)로 갱신 권장.