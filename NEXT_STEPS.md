# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: 2026-05-09 KST — **Phase F 검증 완료. 병렬화 효과 확정**. 브랜치: `2026-05-07-memory-gitignore-cleanup`.
>
> ## ✅ Phase F 검증 완료 — 다음 세션: PR 머지 또는 다음 피처
>
> ### Phase F Step 0~5 결과 (2026-05-09)
>
> **Step 0~1**: smoke 3회 실행 + elapsed_sec 수집 완료
>   - 진입점: `/tmp/smoke_v2.py <run_number>` (generate_work_items 직접 호출, projects/minesweeper-smoke-v2-{01~03})
>
> **Step 2**: v1 vs v2 비교표
>
> | run | version | plan(s) | spec(s) | design(s) | tasks(s) | wall-clock(s) | tasks완료? |
> |-----|---------|---------|---------|-----------|----------|--------------|----------|
> | v1-1 | sequential | 62.9 | 84.9 | 267.4 | fallback | ~415 | ❌ |
> | v2-1 | C-3stages  | 52.3 | 104.2 | 82.6 | 126.1 | **285.4** | ✅ |
> | v2-2 | C-3stages  | 56.7 | 108.5 | 97.0 | 129.8 | **297.9** | ✅ |
> | v2-3 | C-3stages  | 60.6 | 78.8  | 101.1 | 118.2 | **283.6** | ✅ |
> | **v2 avg** | | 56.5 | 97.2 | 93.6 | 124.7 | **289.0** | ✅ |
>
> **Step 3**: frozen build `dist/af-1.2.22.zip` (46.5 MB) 생성 확인 ✅
>
> **Step 4~5 의사결정**:
> - 임계: v2 wall-clock ≤ v1 × (1/1.2) = 415 × 0.833 = **345.8s**
> - v2 avg = **289.0s ≤ 345.8s** → **병렬화 효과 확정 ✅**
> - Stage 2 (spec+design) 병렬 speedup: 352.3s → 97.2+93.6=병렬max≈100.4s = **3.5x**
> - 추가: v2는 tasks까지 완주 (v1은 doc_gen_deadline 300s 초과로 tasks fallback)
>
> ### 다음 작업 후보
> 1. **PR 머지**: `2026-05-07-memory-gitignore-cleanup` → `main` (Phase A~F 전체 완료)
> 2. **doc_gen_deadline 조정**: 현재 300s → 500s+ (design 2 refine에도 tasks가 fallback 안 되게)
>
> ### 최근 커밋 요약 (참고용)
> - `d72b0509` refactor(simplify): _make_usage 헬퍼, write_initial_record, dead var 삭제, 모듈레벨 import
> - `99cb58e5` feat(phase-e): generate_work_items C-3stages 병렬화
> - `49ed755c` feat(phase-d): session_adapter locked_file wrap
> - `b8fd768f` feat(phase-c): requirement_llm elapsed_sec+usage_tokens
>
> ✅ **이번 세션 (2026-05-08 저녁 3) 완료 작업**:
> - **simplify 완료** (`d72b0509`): Phase C~E /simplify 후처리. `_make_usage` 헬퍼, `write_initial_record`, 모듈레벨 import 이동, dead vars 삭제. 3-tier PASS (16 tests).
>
> ✅ **이번 세션 (2026-05-08 저녁 2) 완료 작업**:
> - **Phase E 완료** (`99cb58e5`): C-3stages 병렬화 핵심 구현. `generate_work_items` sequential→C-3stages. `_exec_stage2` ThreadPoolExecutor×2. `_build_full_run_id` §3 격리. spec_outline→tasks. 텔레메트리 dump. 3-tier BLOCK→PASS.
> - **Phase D 완료** (`49ed755c`): `core/providers/session_adapter.py` — `_write_claude_settings` locked_file wrap, `TimeoutError` catch. finding #11 해소. 3-tier BLOCK→WARN.
> - **Phase C 완료** (`b8fd768f`): `core/requirement_llm.py` — `_call_*_api(return_usage=False)` 옵션, `execute_document_prompt`에 `elapsed_sec`+`usage_tokens`. finding #6 해소. 3-tier PASS.
>
> ✅ **이번 세션 (2026-05-08 저녁) 완료 작업**:
> - **v2 설계 작성 완료**: `docs/2026-05-08-work-item-parallel-option-c-design-v2.md`
>   - v1 BLOCK 14건 + Critic Missing 5건 모두 흡수 (자기보고 19/19 정합)
>   - Stage budget 실측 재산정: Stage1 90s + Stage2 400s + Stage3 110s = TOTAL 600s (v1 360s 대비 +240s)
>   - 핵심 변경 19건 §0 표 명시 (Critical 2건/High 6건/Medium 5건/Low 6건)
> - **cross-review 1라운드 → WARN** (BLOCK 0건):
>   - codex Critical 5건 + High 4건은 "설계=미구현=결함" 메타 오해로 REJECTED
>   - 진짜 결함 1건 ACCEPT Medium: §9 import 경로 (`core.workspace_paths` → `core.continuity.runtime_paths`) — 수정 완료
>   - advisory 3건 (마진 표현 / placeholder 컬럼 주석 / R6 cascade 위험) — 수정 완료
>   - WARN-only no-fire 규칙으로 추가 라운드 자동 발화 안 함 (`max_rounds=2` 캡)
> - 리뷰 리포트: `docs/reviews/...-work-item-parallel-option-c-design-v2-design-review.md` (cross-review agent 출력)
>
> ### 📊 측정 결과 (2026-05-08 minesweeper baseline, 1회 실측)
> | 단계 | elapsed_sec | refine_attempts | output_chars |
> |------|-------------|-----------------|-------------|
> | plan | **62.9s** | 0 | 202 |
> | spec | **84.9s** | 0 | 6,539 |
> | design | **267.4s** | **2** | 5,277 |
> | tasks | — (fallback) | — | — |
>
> **핵심 발견**:
> - `doc_gen_deadline = time.time() + 300` (`core/work_item_generator.py:766`) — plan+spec+design 합계 415.2s가 300s를 초과 → tasks는 `_fallback_impl_tasks` 경로 (`_generate_and_refine` 미경유, 측정 불가)
> - **v1 설계 BLOCK #1 실증**: design 단독 267s가 v1 Stage 2 budget(180s) 90s 초과 → 산술 모순 확정
> - refine_attempts 합계: 2건 (전량 design)
> - timeout 발생: 없음 (개별 stage는 stage budget이 아닌 전체 deadline에서 fallback 트리거)
>
> ### v2 Stage budget 재산정 참고치
> - **Stage 1 (plan)**: 65s 실측 → budget **90s** 적정
> - **Stage 2 (spec+design)**: 85+267=352s → budget **400s** 또는 spec/design 분리 후 각각 130s/300s
> - **doc_gen_deadline**: 현재 300s → 최소 **500s+**로 조정 필요 (design 2 refine만으로도 초과)
>
> ### 📌 추가 작업 백로그 (우선순위 낮음)
> - **에스컬레이션 Level 3→4 최적화** (`core/fsa_loop.py:417-424`):
>   - 현재: `is_fundamental` 시 무조건 재설계(Level 3) 후 skill 진화(Level 4)
>   - 개선 제안: `is_fundamental && has_skill_failure()` 동시 충족 시 Level 4 직행
>   - 선행 조건: Level 3→4 전이 비율, skill false-positive 비율 측정 후 결정
>
> ✅ **이번 세션 (2026-05-08 오후) 완료 작업**:
> - **Sonnet baseline 측정 1회 완료** — 위 표 + 파이프라인은 build phase 진입 후 Lilith 오케스트레이션 진행 중
> - **타이밍 패치 원복 완료** (`git restore core/work_item_generator.py` — 측정 코드 미커밋)
> - 측정 raw 파일 보존: `runtime/timing/...minesweeper..._baseline.jsonl` (gitignore 안됨, untracked 상태로 유지)
>
> ✅ **이번 세션 (2026-05-08 오전) 완료 작업**:
> - **핸드오프 문서 cross-review BLOCK 2건 수정** (`docs/2026-05-08-work-item-parallel-measurement-handoff.md`):
>   - #1 High: Entry Point 명령어 수정 (`core.project_pipeline` 없음 → `run_factory_cli.py --task/--project`)
>   - #2 High: 수집 불가 필드 제거 (`provider_id/model/used_fallback` — generator가 메타데이터 버림)
>   - 측정 스키마 확정: `elapsed_sec`, `refine_attempts`, `output_chars`, `ts` 4개
>
> ⚠️ 본 세션 결정 사항:
> - **Stage 구조**: C-3stages (`plan → [spec, design] → tasks`) — finding #4 흡수
> - **run_id 격리**: (D) `{base}_{doc_type}_{pid}_{ts}`
> - **prev_doc 합성**: B3 (tasks가 spec 섹션 목차만 받음)
> - **deadline**: C3 (Stage별 + carry-over)
> - **executor**: D3 (per-future timeout + 폴백)
> - **state cleanup**: 30일 TTL
> - **설계 v1 BLOCK**: 11건 ACCEPT, 측정 완료 후 v2 작성 → cross-review 2라운드 (Opus)
>
> 📁 관련 파일:
> - `docs/2026-05-08-work-item-parallel-measurement-handoff.md` ← 측정 핸드오프 (Sonnet 진입용)
> - `docs/2026-05-08-work-item-parallel-option-c-design.md` ← v1 (BLOCK, v2로 수정 예정)
> - `docs/2026-05-08-work-item-parallel-generation-investigation.md` ← 최초 조사
> - `docs/reviews/2026-05-08-012548-...-design-review.md` ← 직전 BLOCK 리포트 (10건 ACCEPT)
>
> ## 🔑 진입 시 무조건 첫 동작 (PC 바꾼 경우 / 시간 공백 4h+ / 직전 세션이 hook 발화 후 종료된 경우 모두 해당)
>
> ```bash
> git pull --ff-only                       # origin 흡수
> python start_db.py agent-factory         # Supabase 메모리 pull
> ```
>
> `--ff-only`가 reject되면 `git fetch && git status`로 분기 확인 후 결정.
>
> ✅ **이번 세션 (2026-05-08) 완료 작업**:
> - **포커 게임 전체 파이프라인 실행 성공**: `projects/poker-game-test/` 완전 생성
>   - ADR 1개, 도메인 스펙 5개(client-view/event-protocol/rules-spec/server-arch/state-machine)
>   - work-item 5종 문서 (feature-plan/feature-spec/implementation-design/implementation-tasks/approval-gate)
>   - claude_cli 120s/300s 타임아웃 → codex_cli 자동 failover 확인 (CLI 순차 호출 동작 검증)
> - **3-Tier Gate 설계 문서 교차검증 결과** 2건 추가 (`docs/reviews/2026-05-07-*`)
> - **미완료**: §5 테스트 9개 (Provider 0/1/2+, AUTH_EXPIRED, T1 retry)
>
✅ **이번 세션 (2026-05-07) 추가 완료 작업**:
> - **3-Tier Quality Gate 구현**: 설계 → 구현 완료 (7개 파일 + 1개 신규 yaml)
>   - `core/review_runner.py`: detect_providers → provider_detect 위임 + detect_blocked_providers 추가
>   - `core/review_report.py`: AUTH_EXPIRED 선행 BLOCK, SKIP verdict, enterprise 게이팅 제거
>   - `core/project_pipeline.py`: T1 QA gate(_load_doc_contents + run_structural_gate("work_item_doc_set") + 1회 retry), SKIP 통과 처리
>   - `core/rubric_compiler.py`: rule 핸들러 5종(doc_set_present/covers_deliverables/keyword_count_min/phase_count_match/task_section_ref_ratio)
>   - `core/pipeline_quality.py`: SKIP=1.0 매핑
>   - `rubrics/work_item_doc_set.yaml`: 신규 (pass=4.0/warn=3.0)
>   - `skills/evaluator/doc_qa/skill.py`: SKIP 패치
>   - **미완료**: §5 테스트 9개 (Provider 0/1/2+, AUTH_EXPIRED, T1 retry 등)
>
✅ **이번 세션 (2026-05-07) 완료 작업**:
> - **research_router.py WARN 해결** (`1227fbb2`): domain 필드 의미론 정합성 + false-positive 방지
>   - Finding 1 (High): domain = hard gate 의미 명확화 (project_pipeline spec generation 조건)
>   - Finding 2 (Medium): 하이브리드 매칭 — CJK substring + 영문 word-boundary
>   - False-positive 방지: "delivery" → "river" 미감지, "antecedent" → "ante" 미감지
>   - 132 테스트 PASS (102 research_router + 30 quality_contract)
> - **P4 Phase 4 WorkSpecExtractor 검증** (`--research-only "8인 네트워크 포커게임"`): 실제 LLM 추출 정확도 확인
>   - WorkSpecExtractor: goal/constraints/skills/tech-stack/data-model/user-flows 46개 필드 추출 성공
>   - Domain detection: "포커게임" 복합어 정확히 "poker" 도메인 식별
>   - Quality contract integration: D3 위험 식별 + 검증 전략 포함
>   - Source backing: Manus AI 시뮬레이션 + codex 설계문서 자동 추적 완료
> - **메모리 push 페이로드 폭주 근본 fix** (`d848439f`): `scripts/project_context_sync.py`
>   - DEFAULT_EXCLUDE_GLOBS에 chat 폴더 추가: `data/memory/general/claude_chat/**`, `codex_chat/**`
>   - 효과: 19k 파일 / 93MB → 17MB payload 축소, 5xx timeout 해결
> - **P4 QualityContract 구현** (`10c5879b`): core/research/ 서브패키지 + 6 YAML 팩 + 30 tests PASS
>   - WorkSpec, WorkSpecExtractor, QualityContractBuilder, ChecklistMerger
>   - frozen build guard, path traversal 방지, recovery loop 8개/라운드 캡
> - **codex_cli ping fix** (`6b062bf9`/`206c3c1d`): `exec -s read-only ok` → `--version` (stdin hang 수정)
>   - 결과: `codex_cli AVAILABLE` 정상 감지 → 다음 커밋부터 실제 2-provider 크로스 리뷰 동작
> - **review-gate stale 판정 강화** (`2e4598d3`): pre_commit_review.py
>   - Verdict 인식: BLOCK 리뷰만 카운트, WARN/PASS는 0 (advisory 정책 일관)
>   - 본문 참조 파일 mtime 검사: 옛 리뷰가 다른 파일 결함 지적해도 그 파일들이 모두 fix되면 stale 처리
> - **.gitignore 정리** (`1a1387c2`): `.a/`, `.tmp_af_fsa_publish/`, `dist/`, `*.egg-info/` 제외
> - **docs/skills 동기화 완료**: docs/Manus, docs/참고, docs/research, docs/reviews 46건, skills/dp/, dp/skill-spec.yaml
>
> 📋 **다음 세션 작업 후보**:
> 1. **review_gate.py referenced file 감지 강화** (중간 복잡도):
>    - 현황: review_gate.py는 직접 수정 파일만 체크 (line 211). pre_commit_review.py는 referenced file 모두 완성
>    - 계획: `_extract_referenced_files()` + mtime 체크를 review_gate.py로 이식 (pre_commit_review.py 로직 참고)
>    - 이점: review_gate.py의 stale 판정이 complete해짐
> 2. **chat 폴더 자동 TTL 추가** (선택사항): 로컬 머신 chat 파일 자동 정리 (7일 후 삭제 또는 압축)
>    - DEFAULT_EXCLUDE_GLOBS 제외만으로 우선 안정화, 필요시 later phase에서 구현
> 3. **TestB1MaxRoundsCapPreventsInfiniteLoop 근본 원인 추적** (디버깅):
>    - 증상: recovery loop 웹 호출 148 vs expected ≤16
>    - 의심처: quality contract 경로 / recovery escalation 루프
>    - 우선순위: 중간 (cross-review에서 별도 추적 권장)
>
> ⚠️ **운영 메모**:
> - `codex_cli` 인증됨 (이번 세션에서 ping 명령 fix 후 AVAILABLE 확인). gemini는 여전히 AUTH_EXPIRED
> - `tests/test_*` 4개 (Sprint 1 F4~F7) **로컬 보존, 커밋 안 함** — 1개 production 미구현으로 fail
> - `docs/KakaoTalk_*.mp4` 사용자 직접 삭제 대기
> - `AF_PRE_COMMIT_REVIEW=0` 우회 사용 이력 있음 (P4 커밋 시) — review-gate fix로 다음부터 자동 통과 기대
> - **Supabase 메모리 push 성공 확인 (2026-05-07 19:25)**: chat 정리 후 17MB payload로 정상 동기화 완료. Mac 진입 시 `start_db.py agent-factory` 정상 동작 예상

---

## ✅ 완료 (2026-05-06 세션 5회차) — P2 C3+C4 ADR + Traceability

| 커밋 | 내용 |
|------|------|
| `965f9aba` | feat(pipeline+spec_generator): P2 C3+C4 — AdrGenerator + TraceabilityGenerator. BLOCK 6건 수정. 19 tests PASS. |

## ✅ 완료 (2026-05-06 세션 4회차) — P2 C1+C2 Domain Spec Gate + SpecGenerator

| 커밋 | 내용 |
|------|------|
| `7b0e188d` | feat(pipeline+spec_generator): P2 C1+C2 — Domain Spec Gate + SpecGenerator. 12 tests PASS. 3-tier WARN-only. |

## ✅ 완료 (2026-05-06 세션 3회차) — P1 H3 하드 가드 + 14 tests 완전 PASS

| 커밋 | 내용 |
|------|------|
| `90c23761` | feat(researcher): P1 H3 — sources=[] 하드 가드 + test_no_sources_yields_no_claims. 3-tier PASS. 14 tests. |

## ✅ 완료 (2026-05-06 세션 2회차) — P1 B1~B5 Quality Gate + Evidence

| 커밋 | 내용 |
|------|------|
| `808d072d` | feat(researcher): P1 B1~B5 — RecoverySearchLoop + poker.yaml + coverage report. 3-tier PASS. 151 tests. |

## ✅ 완료 (2026-05-06 세션) — P0 _detect_domain BLOCK 최종 수정

| 커밋 | 내용 |
|------|------|
| `8046bc67` | fix(research_router): `_detect_domain` word-boundary fix (`re.findall`). false-positive 제거 + compound 토큰 보존. 139 tests PASS. |

## ✅ 완료 (2026-05-05 세션) — P0 전체 (A1~A6)

| 커밋 | 내용 |
|------|------|
| `9d06bfef` | feat(researcher+pipeline): P0 A1+A6 — `original_request` verbatim 보존 + brief 추적 저장. 3-tier PASS. |
| `deb9195d` | feat(researcher+router): P0 A2+A3+A4+A5 — 도메인 필터+trust_score+checklist+ResearchPlan 3종. BLOCK 2건 수정. 140 tests PASS. |

## ✅ 완료 (2026-05-04 세션) — Master_Blueprint §12 deprecation + P5 G4 병렬화

| 커밋 | 내용 |
|------|------|
| `25bff994` | docs(blueprint): `AF_RESEARCH_LLM_FALLBACK` 환경변수 폐기 §12 entry 추가 |
| `31057abf` | feat(researcher): P5 G4 — ThreadPoolExecutor(max_workers=2) local+secondary 병렬 수집. 7/7 PASS. 3-tier WARN-only |

---

## 🔧 별도 spec — hook auto-amend 분기 이슈

**증상**: `.py` 파일 commit 후 hook 체인 (review-gate / blueprint_updater / code_review_updater / skill_promotion 등)이 워킹트리에 chore 변경을 만들면서 commit을 자동 amend → 로컬 SHA가 변경되는데, 동시에 별도 hook flow가 origin에 push해 origin SHA가 따로 결정 → 분기 발생.

**관찰**: 본 세션에서 2회 발생 (`8db561f3 → 4d057fdd vs origin f47e3c35`, `_ → 7ee6cf3a` 패턴). rebase 시 hook chore 라인(38줄)이 충돌 영역을 점유해 의도된 entry 손실 위험.

**root cause 후보**:
- post-commit hook이 `git commit --amend`를 무조건 실행
- push 직후 별도 chore commit + auto-push가 race condition 유발
- blueprint_updater가 워킹트리 변경 후 `--amend` 사용

**진단 진입점**: `scripts/blueprint_updater.py`, `scripts/code_review_updater.py`, `core/hooks/event_bus.py`. `hook_events.log`에서 `auto_amend` / `auto_commit` 이벤트 카운트 측정.

**임시 우회**: hook이 다 끝난 후 `git status --short`로 chore 변경 보이면 전체 정리 후 push. 또는 `AF_SKIP_REVIEW_GATE=1`로 hook 우회.

---

## 📁 정정 완료 (2026-05-04 오후) — 참고용 보존

### 결함 #1 (Critical) — G3 메타데이터 오염 ✅

**위치**: `core/researcher.py:710-712, 719-720`

**증상**: G3 fallback이 `_collect_llm_prior_knowledge()` 결과를 `web_refs` 슬롯에 넣음. 그러나:
- `_build_source_pack:356-370`이 web_refs를 무조건 `source_type="web"`, `authority_level="secondary"`, `retrieval_method="tavily_search"`로 처리
- virtual chunk 인덱싱 `:730-738`이 web_refs를 무조건 `source_type="web"`, `weight=0.9`, `verified=True`로 처리
- LLM prior 메타데이터(`source_type="llm_prior"`, `verified=False`, `weight=0.4`) 전부 덮어씌워짐
- source_id가 `web_001`로 부착 → synthesizer가 LLM 추측을 검증된 웹 출처로 오인

**수정안**:
```python
# Option A (권장): web_refs 대신 llm_prior_refs 슬롯 사용
elif os.getenv("AF_RESEARCH_LLM_FALLBACK") == "1":
    llm_prior_refs = self._collect_llm_prior_knowledge(task_input)
```
+ 테스트 `test_g3_tavily_unset_fallback_path` assertion을 `result["web_references"]` → `result["llm_prior_references"]`로 변경

**대안**: `_build_source_pack`이 ref dict의 `source_type` 필드를 우선 검사하도록 수정 (더 큰 변경, 권장 X)

### 결함 #2 (High) — G5 retry 예외 포착 비대칭 ✅

**위치**: `core/researcher.py:476-500`

**증상**: retry 호출이 외부 try/except 안에 있어서 retry 도중 예외 시 1차로 얻은 `data`(claims=0이지만 다른 필드 채워짐)도 통째로 잃고 빈 `_FALLBACK` 반환. 원본 보존 의도와 모순.

**수정안**:
```python
try:
    result = execute_requirement_prompt(prompt)
    if not result.get("ok"):
        raise RuntimeError("structured_evidence_llm_unavailable")
    data = safe_json_load(result.get("text") or "{}")
    if not isinstance(data, dict):
        raise ValueError("structured_evidence_not_dict")
    for k, v in _FALLBACK.items():
        data.setdefault(k, v)
except Exception:
    return dict(_FALLBACK)

# G5 retry — 외부 try/except 밖. 실패 시 원본 data 보존
if len(sources) >= 3 and not data.get("source_backed_claims"):
    try:
        retry_result = execute_requirement_prompt(retry_prompt)
        if retry_result.get("ok"):
            retry_data = safe_json_load(retry_result.get("text") or "{}")
            if isinstance(retry_data, dict) and retry_data.get("source_backed_claims"):
                for k, v in _FALLBACK.items():
                    retry_data.setdefault(k, v)
                return retry_data
    except Exception:
        pass  # retry 실패 시 원본 data 유지
return data
```

### 진입 순서

1. 결함 #1 정정 → `pytest tests/test_research_system_regression.py tests/test_research_router_modes.py tests/test_research_router_phase1b.py -q`
2. 결함 #2 정정 → 동일 테스트
3. Master_Blueprint.md §0 + §12 갱신
4. 단일 commit: `fix(researcher): P3+P4 결함 정정 — G3 메타데이터 오염 + G5 retry 예외 포착`
5. af-test-runner + af-critic 자동 발화 → PASS 시 P5(G4 병렬화) 진입

### 후속 갭 (정정 후 별도 처리 검토)

| 갭 | 위치 | 비고 |
|----|------|------|
| G3 코드 중복 | researcher.py 706-722 — `requires_web` ↔ `not sufficient` 두 분기 동일 if/elif/else 복제 | refactor 후보 (helper method) |
| G3 `not sufficient` 테스트 미커버 | 동일 분기에 `AF_RESEARCH_LLM_FALLBACK` 경로 테스트 0건 | 회귀 테스트 추가 |
| G5 retry 예외 경로 미커버 | 결함 #2 정정 후 회귀 테스트 추가 필요 | retry throw 시 원본 data 반환 검증 |
| settings.local.template.json 구 패턴 | 10건 `sh scripts/hookpy.sh` 잔존 — 새 PC 부트스트랩 시 hook 에러 재발 | `python3 scripts/run.py`로 일괄 교체 |
| 토큰셋 substring 중복 | `FRESHNESS ∩ DATA_PIPELINE = {"회차"}`, `EXTERNAL_STACK ∩ OPERATIONAL_RISK = {"풀네트워크", "멀티플레이어"}` | 기존 문제, 분류 과민성. 별도 spec |

---

## ✅ 본 세션 완료 작업 (2026-05-04)

| 커밋 | 내용 |
|------|------|
| `25bff994` | docs(blueprint): `AF_RESEARCH_LLM_FALLBACK` 환경변수 폐기 §12 entry 추가 |
| `31057abf` | feat(researcher): P5 G4 — ThreadPoolExecutor(max_workers=2) 병렬화. 7/7 PASS. |
| `17c38ea7` | feat(research-router): P2 G1 — 한국어 토큰 보강 (`"최근"`, `"동시 접속"`, `"8인"`, `"다인용"`, `"멀티유저"`, `"공신력"`, `"권위 있는"`) |
| `9cefae9c` | refactor(research-router): P2 G1 후속 — `"8인"` 제거 (af-critic W1 수용, false positive 위험) |
| `470e8d10` | feat(researcher): P3 G3 — TAVILY 미설정 + `AF_RESEARCH_LLM_FALLBACK=1` fallback 토글 ⚠️ 결함 #1 잔존 |
| `06d3ac3d` | feat(researcher): P4 G5 — sources>=3 시 source_backed_claims 1회 retry ⚠️ 결함 #2 잔존 |
| `a8314d15` | fix(hooks): `sh scripts/hookpy.sh` → `python scripts/run.py` (Windows `/usr/bin/sh` ELF 실행 불가 해결) |
| `5991f00d` | fix(hooks): `python` → `python3` (macOS 호환) |

**검증**: af-test-runner PASS (138 tests) / af-critic WARN-4/BLOCK-0 — WARN 4건 중 W1+W2가 결함 #1, W3가 결함 #2.

---

## 🔥 백그라운드 — Phase 2 v7 baseline (codex 가용성 분리)

**현재 상태**: commit `ac8d4455` 적용 + push 완료. 자동 3-tier 미발화 (부트스트랩 우회). §9.1 baseline 시작: **2026-05-04 09:00 KST** / 종료 목표: **2026-05-11 09:00 KST**.

### Baseline 시작점 (2026-05-04 09:00 KST 캡처)

- **review_metrics.jsonl**: 6 레코드 (모두 ac8d4455 이전 commit_sha — `f66c5353`/`d4cfa9c2`/`81eb2a7d`)
  - T2 (af-critic): pass:2 / T3 (af-cross-review): pass:2, block:2
  - 전체 findings: T1=0, T2=0, T3=9 (T3-only 100%) / T3 BLOCK-only: 1/3 / 평균 ext-log: 0.0건
- **hook_events.log**: 3,311 lines / `verdict_fallback`: **0** / `warn_only_suppressed`: **0**
- 채택: **롤링 baseline** — `commit_sha`로 ac8d4455 전/후 분리 가능, 별도 컷오프 불필요

### 오늘 가능 (Claude 단독 — codex 미의존)

1. **부트스트랩 사후 sanity** (선택) — Claude 단독 af-cross-review 1회 수동 발화로 v7 fence/헤더 형식 LLM 출력 검증. fan-out 정합 재확인 가치는 부분만 (multi-provider 비교는 codex 회복 후로 이관)
2. **schedule 등록** (선택) — 2026-05-11 09:00 KST `python3 -m scripts.review_metrics_logger` 자동 호출
3. **비-검증 작업 일반** — 코드/문서 작업 가능. `.py` 편집 시 자동 3-tier는 Claude 단독으로 발화

### codex 회복 후 (2026-05-05 15:37 KST↑) — 날짜별 진입 가이드

| 날짜 | 작업 | 진입 명령 / 산출물 |
|------|------|------------------|
| **2026-05-05 (화)** 15:37 KST 이후 | ① codex 가용성 sanity check<br>② fan-out 포함 af-cross-review **1회** 수동 발화 (target: NEXT_STEPS.md 또는 임의 docs) → v7 fence/finding 헤더 multi-provider 정합 1차 검증 | `python3 core/provider_detect.py` 로 codex 인증 확인 → Agent 호출 (af-cross-review) |
| **2026-05-06 (수)** | ① 어제 fan-out 결과 review 파일 분석 (codex/claude/gemini 간 verdict 분포 차이)<br>② §9.2 트리거 #2 `verdict_fallback` 빈도 중간 측정<br>③ 차이 발견 시 v7 prompt/fence 정정안 작성 (필요 시 v8) | `grep -c verdict_fallback .af_review_queue/hook_events.log`<br>`python3 -m scripts.review_metrics_logger` |
| **2026-05-11 (월)** 09:00 KST | §9.1 1주 baseline **종료** — compute_report 수동 호출 후 결과를 docs/2026-05-11-phase2-baseline-report.md로 저장 | `python3 -m scripts.review_metrics_logger > /tmp/baseline.txt` → 분석 + 신규 docs 작성 |

**진입 시 cold-start 절차** (PC 변경 시):
1. `git pull && python start_db.py agent-factory`
2. 본 §🔥 § "Baseline 시작점 캡처" 표와 현재 상태 diff 확인 (`python3 -m scripts.review_metrics_logger`)
3. 위 표의 해당 날짜 행 진입 명령 실행

### §9.2 트리거 모니터링 (baseline 1주 기간 내)

- **#1 single sink** — WARN 라운드당 정확히 1건 `warn_only_suppressed` 정합 (현재 0/0 → 비율 정의 불가)
- **#2 verdict_fallback 빈도** — 형식 위반 LLM 출력 detection (현재 0)
- **#4 false-positive** — `_FINDING_RE` noise 측정. 정책: 1주 후 fence 한정 재평가
- **주기 호출**: `python3 -m scripts.review_metrics_logger` (수동 — append는 hook_runner 자동)

### 적용된 변경 요약 (commit `ac8d4455`)

| # | 파일 | 변경 내역 | spec 참조 |
|---|------|----------|----------|
| 1 | `.claude/agents/af-cross-review.md` Step 5 | §4.3 10행 매핑 + §4.4 집계 + finding 헤더 형식 + verdict fence + WARN/PASS 케이스 + HOLD 금지 | §5.1 |
| 2 | `scripts/review_gate.py` | `_VERDICT_FENCE_RE` + `_extract_verdict_from_content` wrapper | §5.3 |
| 3 | `scripts/hook_runner.py` | wrapper 단일 호출자 + `verdict_fallback` 4-arg log | §5.5 |
| 4 | `scripts/check_pending_review.py` | `warn_only_suppressed` 4-arg log + project root sys.path 보정 | §5.4 |
| 5 | `scripts/review_metrics_logger.py` | `_FINDING_RE` 확장 + scope-creep 책임 분리 주석 | §5.6 |
| 6 | `tests/test_review_metrics_logger.py` | finding 라벨 6건 + false-positive 시나리오 5/6 + post_agent_record stub 갱신 | §5.6 / §7.6 |
| 7 | `tests/test_review_gate.py` | C1~C7 collision 회귀 (v7: C7 trailing 한계) | §7.2 |
| 8 | `tests/test_hook_runner.py` (신규) | `test_log_hook_event_split_invariant()` — line 5-segment split 회귀 보호 | §5.4 v7 정정 |

### 알려진 limitation (운영 트리거)

- **C7 trailing body quote**: fence 부재 시 last-position이 trailing 인용을 캡처 → fence 의무화로 차단. 운영 시 fence 미사용 출력 발견 시 §5.5 `verdict_fallback`로 가시화.
- **false-positive `[ACCEPT-ADV]`/`[BONUS]` markdown fence/prose 인용**: 단순성 우선 정책으로 카운트. 1주 후 빈도 측정 → §10 F4와 함께 fence 한정 정책 재검토.

---

## 📦 보존 — Phase 2 v5 advisory 사유 (참고)

**대상 문서**: `docs/2026-05-03-phase2-verdict-label-spec.md` (v5, 826줄, commit `81eb2a7d`)
**v5 검증 상태**: 본 세션 v4 cross-review BLOCK 8건 발견 (Critical 1 + High 4 + Medium 3, 모두 ACCEPT, Critic 단독 — codex provider error). 사용자 결정으로 Claude 단독 검증 진행 후 v5 작성.

### v5 정정 사항 요약 (v4 cross-review BLOCK 8건)

| # | Severity | 영역 | v5 정정 위치 |
|---|---------|------|-------------|
| 1 | **Critical** | §5.4 `_log_hook_event` 시그니처 모순 (v3 BLOCK 재도입) | 4-arg + JSON 직렬화 + helper 시그니처 설명 통일 |
| 2 | High | §5.3 prose vs 의사 코드 우선 패턴 반대 | 두 정규식 disjoint 단언 + stable sort 정규 채택 |
| 3 | High | §5.5 wrong line reference (line 64 → 100) | `hook_runner.py:100` 정정 + 인용 무결성 audit |
| 4 | High | §5.4 import 전략 미지정 + 부작용 미평가 | `from scripts.hook_runner import` 결정 + workspace path 일관성 단언 + try/except fallback |
| 5 | High | §5.4 sink 폭발 (1회-알림 분기 외부) | 1회-알림 분기 안으로 이동 — WARN 라운드당 1건 + §9.2 트리거 #1 단순화 |
| 6 | Medium | §8.2 단일-commit 자기 모순 | staged 코드 + reviewer 동시 활성화 prose 정확화 + agent definition cache grace period |
| 7 | Medium | §11 history table 미갱신 (3·6·7 충돌) | 7파일로 통일 + §9.3 "7개 파일" |
| 8 | Medium | §7.6 false-positive 회귀 미검증 | 시나리오 5/6 추가 (markdown fence + prose 인용) + 정책 명시 |

### 다음 단계 옵션

**(A) v5 cross-review 재실행** (codex 회복 후 권장):
- codex usage limit 회복: 2026-05-05 15:37 KST 이후
- 단일 설계문서 → af-cross-review 1개만 (CLAUDE.md 정책)
- BLOCK 발생 시 v6 작성 후 재실행

**(B) v5 → 코드 적용 (Claude 단독 검증 신뢰 시)**:
- §8.2 7파일 단일 commit + blast_radius.py 사전 출력 첨부
- 자동 3-tier 검증 발화 후 BLOCK 시 정정

### v5 → 코드 적용 7개 파일 (변경 spec)

| # | 파일 | 변경 내역 | spec 참조 |
|---|------|----------|----------|
| 1 | `.claude/agents/af-cross-review.md` Step 5 | 6개 변경 (§5.1 변경 1~8) | §5.1 |
| 2 | `scripts/review_gate.py` | `_VERDICT_FENCE_RE` 정규식 + `_extract_verdict_from_content` wrapper (last-position stable sort) | §5.3 |
| 3 | `scripts/hook_runner.py` | wrapper 호출 + `_log_hook_event("verdict_fallback", subagent_type, 0/1, error=...)` 4-arg | §5.5 |
| 4 | `scripts/check_pending_review.py` | `from scripts.hook_runner import _log_hook_event` + 1회-알림 분기 안 + `_log_hook_event("warn_only_suppressed", str(round_count), 0, error=json.dumps({...}))` 4-arg | §5.4 |
| 5 | `scripts/review_metrics_logger.py` | `_FINDING_RE` 확장 + scope-creep 주석 (fence 외부 유지) | §5.6 |
| 6 | `tests/test_review_metrics_logger.py` | finding 라벨 케이스 + false-positive 회귀 (시나리오 5/6) | §5.6 / §7.6 |
| 7 | `tests/test_review_gate.py` | C1~C6 collision 회귀 + workspace path 단위 테스트 | §7.2 |

---

## 📦 보존 — Phase 2 v4 BLOCK 사유 (참고)

**review 파일**: `docs/reviews/2026-05-03-231445-2026-05-03-phase2-verdict-label-spec-design-review.md` (PC-local untracked)

**Critic 8건** (모두 ACCEPT, Cross-review 미실행):
- Critical 1: §5.4 v3 BLOCK 재도입 (`_log_hook_event` 3-arg 호출, 4-arg 시그니처와 불일치)
- High 4: §5.3 prose vs 의사 코드 모순 / §5.5 line 64 wrong reference / §5.4 import 전략 미결정 / §5.4 sink 폭발
- Medium 3: §8.2 자기모순 / §11 history table / §7.6 false-positive

→ v5에서 모두 정정 완료.

---

## 📦 보존 — Phase 2 v3 BLOCK 사유 (참고)

**대상 문서**: `docs/2026-05-03-phase2-verdict-label-spec.md` (v3, 573줄, commit `d9cc3304`)

### v3 BLOCK 사유 (Critic 8건, 모두 ACCEPT)

review 파일 (PC 로컬, untracked): `docs/reviews/2026-05-03-224512-2026-05-03-phase2-verdict-label-spec-design-review.md`

#### High 3건 — BLOCK 해제 필수

**#1 [High] §5.3 last-match 폴백 패턴 우선순위 미정의 — G7 회귀 가능**
- 결함: 두 정규식(`_VERDICT_RE` + `_VERDICT_HEADER_RE`)의 last-match 결합 알고리즘 미명세. 본문 BLOCK 인용 + 마지막 줄 PASS 헤더 충돌 시 §7.2 C3가 PASS로 풀린다고 단정하지만 보장 불가.
- v4 정정: §5.3에 결합 알고리즘 명시. **권장**: "`_VERDICT_RE`/`_VERDICT_HEADER_RE` 두 패턴의 모든 매칭을 위치 기준으로 합쳐 last-position 선택" (단일 패스, ambiguity 0). 또는 "`_VERDICT_RE` last-match 우선, 미매칭 시 `_VERDICT_HEADER_RE` last-match" 둘 중 하나 확정. §7.2 C3에 두 정규식 매칭 위치 동시 표기 케이스 추가.

**#2 [High] §4.3 severity-missing fail-safe와 `[REJECTED]` verdict-neutral 충돌**
- 결함: severity 누락 → BLOCK fail-safe 룰과 `[REJECTED]` verdict-neutral 룰이 동시 채택되면, severity 없는 정상 REJECTED 항목이 BLOCK으로 카운트됨. Codex가 false positive로 인정한 항목 때문에 BLOCK 발생 — 의도와 정반대.
- v4 정정: §4.3 fail-safe 행에 단서 추가 — "`[REJECTED]` 라벨 finding은 verdict-neutral 우선; severity 누락이어도 BLOCK 카운트하지 않는다." §5.1 변경 6에 "REJECTED는 severity 생략 허용, 그 외 5종 라벨은 severity 의무" 명시. §7.1에 회귀 케이스 추가 (예: `#### 1. [REJECTED] 제목` severity 누락 → PASS 기여).

**#3 [High] §5.5 silent fallback "G4 해소" 주장 불완전 — gate에 여전히 silent pass 흐름**
- 결함: fallback 시 `verdict="pass"`가 `record_review_done()`/`has_block=False`로 전파되어, **gate 결정 자체는 형식 위반 LLM 출력 시 여전히 silent PASS**. 로그는 사후 감사용일 뿐 현재 라운드 gate를 fail-safe로 보호하지 않음. "G4 해소"는 과장.
- v4 정정 (택일): **권장 (b)** — §5.5/§6에 "G4는 detection-only 해소, gate-level 차단은 Phase 3로 이관" 명시. §4.6의 "fail-safe" 표현도 "detection fail-safe"로 강등. 또는 (a) — fallback 시 `verdict="warn"` 또는 sentinel(`"unparseable"`)로 강등 + `is_gate_blocked` 분기 추가 (진짜 fail-safe, 단 §6 O5 "WARN → gate 차단" 비목표와 모순 → 실질 Phase 3 영역).

#### Medium 3건 — BLOCK 해제 후 보강

**#4 [Medium] §9.2 롤백 트리거 #1 측정 방법 미정의**
- 결함: `verdict_fallback` 이벤트와 no-fire 오작동은 직접 인과 관계 없음. "재발화 빈도 측정"의 metric/jsonl/스크립트 불명. `check_pending_review.py:126`의 no-fire 분기에 telemetry sink 미존재.
- v4 정정: §5.4를 "변경 없음" 대신 `check_pending_review.py:128`에 `_log_hook_event("warn_only_suppressed", {...})` 1줄 추가로 변경. §9.2 트리거 #1을 "warn_only_suppressed 빈도 vs WARN verdict 빈도"로 정의. 코드 변경 파일이 6개 → 7개로 확장됨.

**#5 [Medium] §8 구현 순서 — Tier 분류와 실행 에이전트 셋 자기모순**
- 결함: 같은 step에서 "af-test-runner만"과 "scripts/*.py는 Tier 2~3 발화"를 동시 선언. `scripts/review_gate.py`/`hook_runner.py`는 자동 Tier 3.
- v4 정정: §8 step 3을 2-commit 전략 또는 "단일 commit + 3-tier 전체 + blast_radius 사전 출력 첨부"로 명시. 새 라벨 시스템 적용 후 다음 라운드부터 검증 가능한 부트스트랩 순서도 명시 (chicken-and-egg: 새 fence가 적용되기 전 commit이 fence 없는 형식으로 검증됨).

**#6 [Medium] §5.3/§5.5 통합 계약 — wrapper 호출자 미명시**
- 결함: §5.3 wrapper는 `review_gate.py`에 신설되지만 실제 verdict 파싱은 `hook_runner.py:339-344`에서 일어남. §5.5 변경 코드는 여전히 `_VERDICT_HEADER_RE`를 직접 호출. `record_review_done()`은 본문 파싱 안 함 — wrapper와 무관.
- v4 정정: §5.3에 wrapper 단일 호출자(=`hook_runner.py`) 명시. §5.5 변경 코드를 "wrapper 호출 + None일 때만 fallback log + verdict='pass'"로 다시 작성. `record_review_done()`/`is_gate_blocked()`가 wrapper와 무관함을 정정. (이건 v3 §5.3과 §5.5의 구조적 결손 — 가장 중요한 정정.)

#### Low 1건 + HOLD 1건

**#7 [Low] §5.1 변경 5 fence-내부 한정 vs `_SCOPE_CREEP_RE` 전역 검색 — 메트릭 손상**
- 결함: `_SCOPE_CREEP_RE`는 전체 content 검색. fence 내부 한정 정책 도입 시 메트릭 손상 또는 정책 모호성 발생.
- v4 정정: §5.6에 1줄 추가 — "scope-creep는 verdict 라벨이 아니므로 fence 외부 검색 유지" 또는 "fence 내부 한정으로 변경 — 메트릭도 fence 추출 후 검색" 둘 중 하나. **권장**: 전자 (단순성).

**#8 [HOLD] [Low] frozen build 영향 미검토**
- 결함 (약한 evidence): hooks가 frozen 컨텍스트에서 호출되는 경로 확인 없음. `_log_hook_event`가 새 키(`verdict_fallback`)를 쓸 때 workspace 경로 해석이 source build와 동일한지 미확인.
- v4 정정: §8에 "Windows PC 빌드 시 frozen `dist/af/af.exe`로 hook 1회 sanity 호출 검증 의무" 1줄. Mac에서는 검증 불가 → Windows PC 빌드 단계로 이관.

### Missing 4건 (Critic 별도 권장 — v4에 반영 검토)

- `record_review_done()` 인자 신뢰 관계 명시 (변경 #6과 연결 — §5.3에서 다룰 수 있음)
- `AF_GATE_ALLOW_VERDICT_BLOCK` 우회 환경 변수 + fence 외부 잔존 인용 처리 (Phase 3 후보로 §10 등록)
- 마이그레이션 윈도우: v2 라벨 PR과 v3 라벨 PR 공존 시 `compute_report()` 일관성 (§11 또는 §10 F7 보강)
- 다중/중첩 fence 케이스 wrapper 동작 정의 (§5.3에 "fence 1쌍만 인식, 첫 쌍 내부만 매칭" 명시)

### v4 작성 후 단계

1. v4 commit (Tier 1 — design only).
2. **af-cross-review 재실행** (codex usage limit 회복: 2026-05-05 15:37 KST). v2/v3 모두 provider error로 미수행 — v4에서 회수 필수.
3. PASS 시 코드+에이전트 변경 7개 파일 일괄 적용 (v3보다 #4 추가로 +1):
   - `.claude/agents/af-cross-review.md` Step 5 (§5.1 변경 1~8)
   - `scripts/review_gate.py` (§5.3 wrapper)
   - `scripts/hook_runner.py` (§5.5 wrapper 호출 + verdict_fallback log)
   - `scripts/check_pending_review.py` (§5.4 — **v4 신규**: warn_only_suppressed log)
   - `scripts/review_metrics_logger.py` (§5.6 정규식)
   - `tests/test_review_metrics_logger.py` (§5.6 신규 케이스)
   - `tests/test_review_gate.py` (§7.2 collision C1~C5)
4. Tier 2~3 검증 (§8 부트스트랩 순서 적용) 후 commit.

---

---

## ✅ 23:25 BLOCK 인계 — 완료 (v4 PASS)

### WARN 6건 잔존 (advisory, 수정 의무 없음)
**Medium (3건)**:
- §5.2 line 131: "plan에서 single contract 고정 **권고**" — 분석 문서 원칙 위반 잔존 (v2 이후 미수정)
- §5.2 line 136: "plan에서 workspace-relative로 고정 **권고**" — 동일 원칙 위반
- §5.4 Q-F line 217: `hook_runner.py:347-365` silent failure → 실제는 `:362-374` (metrics try/except)

**Low (3건)**:
- §5.3 line 142: settings.local.json PostToolUse `line 191-212` → 실제는 `line 204-226`
- §5.4 Q-D line 199: `hook_runner.py:347-348` post_agent_record → 실제는 `:483` 등록 / `:354` 이벤트 로그
- §7.2 line 178: `af-test-runner.md:41-43` test_gap_analyzer → 실제는 `:46`

**review 파일**: `docs/reviews/2026-05-02-232500-2026-05-02-oh-my-openagent-ast-lsp-comparison-design-review.md`

### Timeline
- 23:24:22 — v2 정정 commit `9d25956c` (정정 13건 모두 반영)
- 23:25:00 — cross-review 2라운드 trigger → BLOCK 12건 verdict 작성 시작

### BLOCK 12건 분류 (실측 검증 완료)

**거짓 BLOCK 6건** (cross-review가 정정 전 파일을 본 것 — timing race / cache):
- #1 §10 changelog over-promises — 검증: §9.4 line 307 ✓, line 167 부근 188-208 잔존 X ✓
- #2 Q-D 98% PASS caveat 부재 — 검증: 제목에 sink 한정 + 본문에 caveat 박스 ✓
- #3 §9.4 reproducibility commands missing — 검증: line 307~ Q-A~Q-F grep 명령 ✓
- #5 §5.3 line-range contradiction (188-208 잔존) — 검증: 잔존 안 함 ✓
- #6 §5.2 1-based vs 0-based missing — 검증: 본문에 명시 ✓
- #7 §5.2 file_path absolute missing — 검증: 본문에 명시 ✓

→ 다음 세션: cross-review가 본 파일이 stale인지 재검증. cross-review 재실행 시 같은 결과면 prompt/cache issue 별도 조사.

**진짜 추가 작업 6건** (다음 세션 정정):
- #4 [High] §9.1 URL을 `/dev/` → commit SHA permalink로 직접 교체 (현 정정안은 SHA pin **안내**만 추가, URL 교체는 안 함 — cross-review 요구는 URL 자체 교체)
- #8 [Medium] §2.3 line 49 "분리된 것으로 보이지만 단정 불가" → "본 fetch 범위 내에서 미확인"으로 톤다운 (§1 "추정 사용 없음" 원칙과 모순)
- #9 [Medium] §7.3/§8 AST tool language scope 명시 (`build_review_bundle.py:53` `.py` 필터, `ast_engine.py:29,53` 미지원 lang은 python default — v1 Python-only 명시 또는 lang enum)
- #10 [Medium] §7.3 rename-safe gap 정정 — `lsp_check.py:103`은 pyright shell-out, JSON-RPC 클라이언트 없음 → LSPCheckHook 활성화로 rename-safe 불가 명시
- #11 [Medium] `core/hooks/lsp_check.py:29` `_WRITE_TOOLS` hardcoded — `apply_edit` / `apply_block_edit` 누락 (`skills/hash_edit/skill.py:23`, `skills/hashline_edit/skill.py:20`). §5.1 / §8 footnote
- #12 [Medium] §8 #4/#5 "비용" 차원 사용 시 sizing 또는 event 이름 정의 (`lsp_check_skipped`, `lsp_check_result`, `ast_tool_search`) 추가

→ 6건 모두 분석 문서 baseline 신뢰도와 v1 plan 입력에 영향. Spike 1+2 진입 전 정정 권장.

---

---

## 🔥 현재 진행 중 — Research Router Phase 1a 코드 진입 직전

**대상 문서**: `docs/2026-04-29-research-router-structured-evidence-design.md` (v1.4.1, ~1349줄, 5라운드 PASS)

### 진행 흐름 (최근 → 과거)
1. v1.0 (2026-04-29) — 최초 설계
2. v1.1 (2026-05-01) — 7라운드 deliberation 합의 반영
3. v1.2 (2026-05-02) — 1라운드 BLOCK 4건 반영
4. v1.2 2라운드 → BLOCK 3건 잔존 (이전 세션)
5. v1.3 (2026-05-02) — 2라운드 BLOCK 3건 (R2-1/R2-2/R2-3) 반영
6. v1.3 3라운드 → BLOCK 4건 발견 (자기참조 실패 + 정합 누락)
7. v1.4 (2026-05-02) — 3라운드 BLOCK 4건 모두 처리 (token-trace 기반 §10.1 정정 + §4.4.5 코드 분기 통합 + §6.5 unclassified 제거 + §11/§4.2.1 fixture schema 두 라벨)
8. v1.4 4라운드 → BLOCK 1건 (§12.5 라벨 가이드 후속 정합 누락)
9. v1.4.1 (2026-05-02) — 4라운드 BLOCK 1건 정정 (§12.5 라벨 가이드 단일 라인)
10. **v1.4.1 5라운드 → PASS ✅** ← 현재 위치
11. Phase 1a 코드 진입 ← **다음**

### 5라운드 검증 통과 사실
- 자기참조 검증 4종 모두 token-trace 정합:
  - 8인 포커: `fast_synthesis` → §4.4.5 detector emit → `deep_source_research` ✓
  - 로또: `fresh_lookup` → escalation 없음 → `fresh_lookup` ✓
  - 단순 CRUD: `fast_synthesis` → escalation 없음 ✓
  - fixture schema 라벨 키 4곳 일관 (§4.2.1 / §10 / §11 / §12.5) ✓
- 핵심 spec(§4.2/§4.2.1/§4.4.5) 정합 확정.

### Phase 1a 완료 ✅ (2026-05-02)
1. `core/research_router.py` 신규 (ResearchGap 9종, ResearchPlan, ResearchRouter.plan/detect_complexity_gaps, gap_to_mode)
2. `core/researcher.py` 시그니처 확장 (research_plan/hint_gaps/**_kwargs, mode-aware gating, router escalation 연결)
3. `core/project_pipeline.py` `_evidence_fn(**kwargs)` + TypeError 분리
4. `core/research_verifier.py` max_retries=1, gap emit enum 값 교체, DeprecationWarning
5. `af.spec` core.research_router 외 3개 hiddenimports 추가
6. `tests/test_research_router_modes.py` 18케이스 107 tests PASS (initial/final mode 각 100%)

---

---

## 세션 시작 체크리스트

```bash
cd D:\hoonProJect\worktrees\agent-factory
git pull
python start_db.py agent-factory   # Claude Code 메모리 + DB 동기화
```

---

## 현재 브랜치 상태

| 항목 | 상태 |
|------|------|
| 브랜치 | `2026-04-14-build-diet` |
| 마지막 커밋 | `5f24283e` feat(P1+cross-review): blast_tier downgrade + 4-round deliberation upgrade |
| origin 푸시 | ✅ 완료 (origin/2026-04-14-build-diet 동기화됨) |
| Review-Gate | 활성화 (`.githooks/pre-commit`) |

---

## 완료된 작업

| # | 작업 | 커밋 | 날짜 |
|---|------|------|------|
| 1 | Graphify 크로스 프로바이더 스킬 통합 Phase 1+2 | `28ae5477` | 2026-04-23 |
| 2 | Graphify COMPACT 연동 (Phase A Step 2) | `5f42ccba` | 2026-04-23 |
| 3 | LLM 기반 work-item 문서 생성 파이프라인 P1+P2 | `af1bd81e` | 2026-04-23 |
| 4 | Phase A Step 2 COMPACT (RunBudget, FSA guard, PlanVerifier.gate, SkillPackBootstrapper) | `3b42cb06` | 2026-04-23 |
| 5 | LLM 문서 생성 P3~P6 (prepare 3분할, Clarification UI) | `a12f4493` | 2026-04-24 |
| 6 | gitignore 보안 정리 (.system_generated/logs+cache untrack) | `0defdfba` | 2026-04-24 |
| 7 | Cross-PC 메모리 동기화 — Supabase claude_memory 테이블 생성 + push/pull 검증 | — | 2026-04-24 |
| 8 | P3: PostToolUse hook 연결 — `.py` 편집 시 code-review.md 자동 갱신 | — | 2026-04-24 |
| 9 | Phase A Step 3+4: EVOLUTION(quality_delta+테스트) + MEMORY(semantic_scores, MemoryScope.PROJECT, M8 에피소드 주입) | `ffc9eaf5` | 2026-04-24 |
| 10 | version bump 1.2.21→1.2.22 + install-af.ps1 | `63990a71` | 2026-04-25 |
| 11 | B2-6 C0+C1+C2: write_project_board atomic write, strategy ledger 모듈별 granularity, nightly summary 모듈 섹션 | `63990a71` | 2026-04-25 |
| 12 | 3순위: CheckpointHook 등록, EpisodeRecord 필드 확장, DynamicOrchestrator record_episode | `63990a71` | 2026-04-25 |
| 13 | 통합 결함 10건 일괄 수정 — Sonnet/Codex 5.5/af-critic 3-Tier 검증 통과 (audit 4건 + Codex 신규 1건 + critic 2건 P0/P1 + cross-review 후속 5건) | `d809e72f` | 2026-04-25 |
| 14 | P0-C: event_bus.py W2 per-hook exception handling | `d809e72f` | 2026-04-25 |
| 15 | T1-1: canonical Checkpoint + RunEvent + af resume 서브커맨드 — 3-Tier 검증 통과 | `7b546ca0` | 2026-04-26 |
| 16 | T1-2: Atomic Task idempotency + RunEvent per-step — 3-Tier 검증 통과 | `0320d311` | 2026-04-26 |
| 17 | T2-5: 벡터 영속화 — similarity 전파 + project_id 동적화 + dedup tiebreaker — 3-Tier 검증 통과 | `2c1eb81a` | 2026-04-26 |
| 18 | T2-4: search_all_backends() memory_type/scope 필터 + cross-project 격리 수정 + cortex apply() project_id — 3-Tier 검증 통과 | `cb5adfcd` | 2026-04-26 |
| 19 | T3-7: Audit/Cost/Approval → RunEvent 통합 — COST_INCURRED + APPROVAL_REQUESTED/GRANTED + W3 fix + check_validity 신규 문서 감지 — 3-Tier 검증 통과 | `a4965cf1` | 2026-04-27 |
| 20 | T3-7 ACCEPT 2 후속: CLI --budget → set_run_budget run_id 연결 + approve() run_id 전달 + consumed_tokens 역기록 + 즉시 중단 가드 — 3-Tier 검증 통과 | `59b89f72` | 2026-04-27 |
| 21 | Stage-0 Hotfix C1~C7: self-evolution silent failure 7종 봉쇄 — 3-Tier 검증 통과 | `3145c224` | 2026-04-28 |
| 22 | Stage-1 설계: `docs/2026-04-28-self-evolution-stage1-design.md` v3 (14섹션, 3-라운드 교차검증 통과) + Blueprint §12 C1~C5 동기화 | `32c42196` | 2026-04-28 |
| 23 | Stage-1 Sprint 1: `core/evolution_types.py`(EvolutionDecision/EvolutionResult) + RunEventType 4종 + `_METADATA_TRIGGERS`/`_CODE_EVOLUTION_TRIGGERS` whitelist + SkillSelfEvolutionHook `run_id=` + decision 체인(bus→event_bus→hook) + memory_consolidation Lock + agent_runner 연결 — 3-Tier 검증 통과 | `6235ad9d` | 2026-04-28 |
| 27 | T1: knowledge skill SKILL.md description fallback — `_fill_missing_description()` 신규, frontmatter 우선+body fallback, 5개 테스트 — 3-Tier 검증 통과 | `cf461e01` | 2026-04-29 |
| 28 | T2: fsa_loop per-skill 에스컬레이션 가드 — `_apply_evolution_guard()` 신규, 탐지 실패 Level 5 강제, 이중 탐색 제거, 26개 테스트 — 3-Tier 검증 통과 | `33000436` | 2026-04-29 |
| 24 | Stage-1 Sprint 2: `core/skill_evolution_controller.py`(SelfEvolutionController 7단계 파이프라인) + `core/evolution_ledger.py`(EvolutionLedger JSONL) + EVOLUTION_ROLLED_BACK RunEvent 직접 기록 + _publish() live-snapshot rollback + .bak 배포 방지 + get_default_store() thread-safe 싱글톤 + conftest AF_CHECKPOINT_DIR 픽스처 — 60 테스트 3-Tier 검증 통과 | (커밋 예정) | 2026-04-28 |
| 25 | Stage-1 Sprint 3: 호출사이트 3개(fsa_loop._try_evolve_failed_skill, cross_verification._trigger_evolution, dynamic_orchestrator._try_evolve_from_patterns) → SelfEvolutionController.submit() 교체, 3메서드 제거(_verify_evolved_skill/_rollback_skill/_cleanup_skill_baks), CANDIDATES_DIR 절대경로(config_paths.py), knowledge skill 지원(_is_knowledge_skill + SkillQualityGate early-return), skill_creator meta.yaml.bak 제거, GateResult 필수 필드 추가 — 70 테스트 3-Tier 검증 통과 | `0778ed42` | 2026-04-29 |
| 26 | Sprint 3 WARN 클리어 (9-라운드 3-Tier): fsa_loop DEFERRED/ERROR/REJECTED→None+_evolution_failed_skills 차단, Level 4 apply_pivot 조건 정리, gate_result is None 단순화, Level 4→5 강제에스컬레이션, run_mission 초기화, skill_quality_gate knowledge skill auto_register+_register_knowledge_skill, skill_creator update_skill knowledge type 보존(setdefault), skill_evolution_safety DEPRECATED 마커, fixture 모듈 속성 복원, 테스트 4종 신규 추가 — 81 테스트 통과 | `875d5081` | 2026-04-29 |
| 29 | P1 설계문서 + hook 인프라 수정: `docs/2026-04-29-multi-provider-cross-review.md` (350줄, 13섹션) + `scripts/check_design_pending.py` (design 큐 폴링, JSON timestamp debounce, fired pruning) + `core/design_review_utils.py` (날짜패턴·work-items·patterns INCLUDE/EXCLUDE) + `settings.local.json` (PostToolUse 복원, check_design_pending 등록) + `CLAUDE.md` (af-design-review-pending 룰) — 3-Tier 검증 통과 | `6566c459` | 2026-04-29 |
| 30 | Phase 0 Proof-Carrying Review: `scripts/blast_radius.py` (결정적 Tier 분류기, path/regex, LLM 없음) + `review_gate.py` (round_started_at 토큰 모델, claim_id AF-RG format, clear 리셋, BLOCK fall-through) + `enqueue_agent_review.py` (_state_lock RMW + classify_with_content 락 밖 선계산) + `check_pending_review.py` (_state_lock RMW + cap/warn-only 1회 알림) + `af-critic.md` (BLOCK 기준 명시, 0 findings valid) + `tests/test_review_gate_phase0.py` (20 tests, 20 passed) — 모든 High 이슈 해소 | `24be4ace` | 2026-04-30 |
| 31 | P1 Sprint A: `core/provider_detect.py` 신규 — ProviderState(3-state) + 1h 디스크 캐시 + AF_SKIP_PROVIDER 마스킹(캐시 오염 방지) + AGENT_*_CLI_COMMAND env var override + ThreadPoolExecutor 병렬 ping + CLI entry `--json --exclude-self` + `tests/test_provider_detect.py` (20 tests) + `af.spec` hiddenimport — af-critic BLOCK 2건 + af-cross-review ACCEPT 3건 모두 해소 | `3e956d7f` | 2026-04-30 |
| 32 | P1 Sprint B: `af-cross-review.md` 동적 fan-out 재작성 — Step 0(3-gate: BLOCK/SKIP/CONTINUE) + Step 2(timeout 180s, python3 치환 macOS 호환, 오류파일 추적) + Step 3([ACCEPT★] 합의 가중치) + CLAUDE.md Tier 3 fan-out 설명 — af-critic WARN 3건 수정 완료 | `74dfa3c5` | 2026-04-30 |
| 33 | test-gap gate: `scripts/test_gap_analyzer.py`(신규) + `hook_runner._apply_test_gap_verdict()` + `.claude/agents/af-test-runner.md` Step 2.5 + `tests/test_test_gap_analyzer.py` (11 tests) + `tests/test_hook_runner_builtins.py` (21 tests) + 설계문서 | `3612cc11` | 2026-04-30 |
| 34 | P1 blast_tier downgrade: `review_gate.downgrade_blast_tier()` API + `hook_runner._apply_test_gap_verdict()` FAIL 시 blast_tier=1 다운그레이드 + blast_tier 검증 테스트 (33 tests) | `5f24283e` | 2026-04-30 |
| 35 | af-cross-review 4-round deliberation 전면 재작성: Round1 Discovery(`mcp__codex__codex`+threadId 저장) → Round2 Challenge(Claude 직접 코드 확인) → Round3 Defense(`mcp__codex__codex-reply` 동일 thread+`[보강]`/`[철회]` 마커) → Round4 Verdict(ACCEPT★/REJECTED/ACCEPT) | `5f24283e` | 2026-04-30 |
| 36 | Phase 3.5 메트릭 수집 인프라: `scripts/review_metrics_logger.py`(신규 — append_metric/parse_findings_count/parse_extension_log_count/compute_report) + `scripts/review_metrics_report.py`(CLI) + `hook_runner._post_agent_record` Phase 3.5 연동 + `tests/test_review_metrics_logger.py` (28 tests) | (커밋) | 2026-05-01 |
| 37 | Research Router Phase 1a 구현 — `core/research_router.py`(신규, ResearchGap 9종 enum + ResearchPlan + ResearchRouter.plan/detect_complexity_gaps + gap_to_mode) + `core/researcher.py` 시그니처 확장(research_plan/hint_gaps + mode-aware gating + auto escalation max retry=1) + `core/project_pipeline.py` `_evidence_fn(**kwargs)` + `core/research_verifier.py` max_retries=2→1 + DeprecationWarning + tests/test_research_router_modes.py (101 tests) — 3-Tier 검증 통과 | `8654ce2a` | 2026-05-02 |
| 38 | hotfix(test): `tests/test_review_metrics_logger.py` sys.modules 오염 수정 — `sys.modules[X]=Y` 3곳 → `monkeypatch.setitem(sys.modules,X,Y)`. test_phase1_blast_tier_invariant.py 9건 flaky FAIL 해결, 자기참조 검증 primary trust 회복. test-only 변경, 게이트 우회. | `5a4491f9` | 2026-05-02 |
| 39 | docs(참고): OpenCode LSP 아키텍처 분석 1차 작성 — 단, cross-review BLOCK 3회 후 §5.1·§5.3 내부 모순 잔존 상태로 종료. 다음 세션에서 처음부터 재분석 필요. | `042d0386` | 2026-05-02 |
| 40 | docs: oh-my-openagent 분석문서 WARN 6건 정정 (M1/M2 권고어 교체, M3/L1/L2/L3 라인범위 수정) | `e71a24cf` | 2026-05-03 |
| 41 | docs(plan): Static Evidence Injection v1 플랜 작성 + 2라운드 cross-review PASS (BLOCK 2건 수정) | `aac4a784` | 2026-05-03 |
| 42 | feat(v1): Static Evidence Injection v1 구현 — 배선 복구(PostToolUse Agent 매처) + review_bundle 형식 개선(_RISK_DESC) + review_metrics schema 확장(evidence_present/items/cited) + evidence_cited 측정 — 3-Tier PASS, review_metrics.jsonl 기록 확인 | `f66c5353` | 2026-05-03 |
| 43 | feat(phase1b-research-router): Research Router Phase 1b — `core/web_search.py` content_full+excerpt 분리 + tavily_extract() 신규 + `core/researcher.py` _build_source_pack() §6.2 정규화 + `core/research_verifier.py` 4-metric(citation_validity/claim_source_ratio/primary_source_ratio/source_pack_chars) + quality-tier gap 3종 + tests/test_research_router_phase1b.py (137 tests) — af-critic PASS / af-cross-review PASS (AF_SKIP_PROVIDER=codex, codex usage limit) | `b605db22` | 2026-05-03 |
| 44 | docs(phase2-design): v1 작성 — verdict 라벨 명시화 설계 (BLOCK/WARN/PASS 매핑 + [HOLD] 처리 + [ACCEPT-ADV] 분리). Critic 4건+Cross-review WARN 산출 (provider error로 critic 단독 집계의 ACCEPT 처리). | `5c77af16` | 2026-05-03 |
| 45 | docs(phase2-design): v2 재설계 — Cross-review WARN 2건 수용(§4.2/§4.3/§5.1 모순 통합 + §7.3 실제 no-fire 경로 재추적) + deep-think 6건(G3 HOLD 입구→Phase 3 이관, G4 parser silent fallback, §4.6 labeling-only 명시, §5.1 severity·scope-creep 호환·HOLD 템플릿, §7.2 parser collision 불변, §9 롤백 계획). Critic 단독 BLOCK 1건 (review_metrics_logger 회귀) — v3 정정 대기. | `f8be0794` | 2026-05-03 |
| 46 | docs(phase2-design): v3 — Critic 8건 전수 반영 (§5.6 review_metrics_logger _FINDING_RE 확장 / §5.5 hook_runner verdict_fallback 가시화 / §5.3 review_gate verdict fence + last-match wrapper / §4.3 severity 누락 BLOCK fail-safe / §4.5 HOLD 라벨 Phase 3 완전 이관 / §5.1 변경 6 BONUS 헤더 형식 / §7.5 round 전환 R3~R6 / §11 라벨 마이그레이션). design-only → design+code 6개 파일로 범위 확장. cross-review 재실행 대기 (codex 회복 후). | (커밋) | 2026-05-03 |

### 🔍 검증 중 발견 (별도 트랙)

- **pytest 전체 실행 hang** — `pytest tests/ -q` 6분+ 멈춤. 어제 작업과 직접 관계 없을 가능성. 원인 파일 격리 필요 (langsmith/anyio/langgraph 의존성 의심).

---

## ✅ AST/LSP 인벤토리 재분석 완료 (2026-05-02 본 세션)

### 결과
- **분석 대상 정정**: SST OpenCode → **oh-my-openagent** (`code-yeongyu/oh-my-openagent`, 이전 oh-my-opencode)
- **신규 문서**: `docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md` (10개 섹션, 권고 0개, 분석/권고 분리)
- **인벤토리 6개 질문 답변 완료** + **효과 측정 6개 데이터 수집** (Q-A~Q-F)
- **cross-review verdict=WARN** (BLOCK 0건, advisory 10건)

### 핵심 사실 (실측 기반)
1. review_bundle risk_id 인용률: 1/46 review (~2%)
2. test_gap_analyzer 호출: hook_events.log 0건
3. LSPCheckHook 호출: 0건 (pyright 미설치 + AGENT_LSP_CHECK 미설정)
4. 3-tier verdict: 51 PASS / 1 BLOCK ≈ 98% PASS
5. review_metrics.jsonl 부재 (Phase 3.5 미작동)
6. oh-my-openagent: AST 2개 + LSP 6개 모두 AI tool로 직접 노출 (pull 모델, push는 본 fetch 범위에서 미확인)

### ✅ 다음 세션 인계 항목 — 분석 문서 v2 정정 완료 (2026-05-02 밤)

cross-review 12건 + 재분석 추가 1건 = 13건 모두 분석 문서에 반영:
- §5.2 schema 계약 명시 (line 1-based vs 0-based, file_path 절대/상대 모호성, engine별 6/7종 차이)
- §5.3 PostToolUse 블록 라인 범위 정정 (188-208 → 191-212)
- §5.4 Q-A 메타 표기, Q-B/Q-E 측정 sink 한계, Q-D 표본 편향 caveat, Q-F silent failure 후보 (a)/(b)/(c) 분리
- §6 SST 권원 표시, §8 #5 plan-tone 톤다운
- §9.4 신설: Q-A~Q-F 추출 명령 + §9.1 commit SHA pin 안내

본 정정은 advisory 처리. **남은 작업은 Spike 1+2 → v1 plan 작성** (변동 없음).

### ✅ 본 세션 추가 — 합의 사항 (2026-05-02 저녁, deliberation 결과)

**아키텍처 두 plane 분리 합의** (Codex + Claude Opus 4.7 합의):

1. **Capability Plane** — agent가 직접 쓰는 도구 (AST search/replace, LSP diagnostics/rename 등)
2. **Assurance Plane** — 산출물 검증/품질 게이트 (review_bundle, test_gap, cross-review, metrics, commit gate)

→ 두 plane은 분리 설계, 각자 KPI로 측정. 핵심 원칙: **"도구 사용 흔적이 반드시 검증 루프에 들어가야"** closed loop 성립.

### 📋 Phase 로드맵 — v1만 plan, v2~v5는 후보

| Phase | 작업 | 상태 |
|-------|------|------|
| **v1** | **Static Evidence Injection v1** — 배선 복구 + review_bundle 형식 변경 + test_gap_analyzer gate + review_metrics.jsonl schema 확장 | plan 작성 대기 (spike 선행) |
| v2 | Read-only `ast_search` tool (Capability Plane 진입) | 후보, v1 KPI 측정 후 |
| v3 | `lsp_diagnostics` optional tool | 후보 |
| v4 | `ast_replace` dry-run | 후보 |
| v5 | safe rename / apply (LSP 의존) | **optional/conditional** — pyright 동봉 비용 vs 사용 빈도 검증 후 |

### 🔬 다음 세션 — Spike 2건 (v1 plan 작성 전 필수)

**Spike 1**: subagent 내부 tool trace 가능성
- Claude Code Task로 호출되는 subagent(af-critic, af-cross-review)의 tool 사용을 메인이 추적 가능한지
- 불가능하면 v1 KPI는 final output self-report 기반으로 한정 (subagent reasoning 텍스트 + verdict)
- 결론: v1 plan은 내부 tool trace에 의존하지 않도록 확정

**Spike 2**: `review_metrics.jsonl` silent failure 원인 분리
- 후보 (a): `post_agent_record` hook 미배선 (settings.local.json:188-208에 직접 등록 부재 확인됨)
- 후보 (b): `_post_agent_record()` 호출되지만 `append_metric()`이 try/except: pass로 삼킴
- 후보 (c): workspace path가 달라 다른 위치에 작성됨
- 부산물: post_edit_enqueue 552건 fake/effective 비중 분리도 자연 도출

### 🎯 v1 Scope (Spike 후 plan 확정)

**IN**:
- 배선 복구 (Spike 결과 반영)
- review_bundle 형식 변경: raw risk_id → "file:line + 위험 설명 + 왜 review해야 하는지 + 확인할 테스트/호출자"
- review_metrics.jsonl schema 확장: `evidence_present`, `evidence_items`, `evidence_risk_ids`, `evidence_cited`, `findings_count`
- `evidence_cited` 측정 메커니즘: **(b) `file:line` grep baseline** + 옵션 (c) prompt 강제 인용 검토
- test_gap_analyzer 실제 gate 호출 복구

**OUT (v2 이후)**:
- AST tool AI 노출 (read/write 모두)
- LSPCheckHook 활성화
- Rename safe workflow

**KPI** (v1 효과 검증):
- 인용률 (현재 ~2% → 목표 30%+)
- test_gap_analyzer 호출률 (현재 0% → 목표 100%)
- review_metrics.jsonl 작성 성공률 (현재 0 → 100%)
- 정적 진단 기반 BLOCK 발생률 (baseline 측정 후 결정)

### 매개체 운영 합의

| 파일 | 역할 |
|------|------|
| `review_bundle.md` | evidence snapshot |
| `review_metrics.jsonl` | 소비/효과 메트릭 (스키마 확장) |
| `hook_events.log` | 저수준 hook debug |
| ~~static_evidence.jsonl~~ | **신규 생성 X** (운영 매개체 추가 비용 회피) |

### 다음 행동 순서 (다음 세션)
1. Spike 1 + Spike 2 수행 (병렬 가능)
2. Spike 결과 위에서 v1 plan 작성 (`docs/plans/2026-05-XX-static-evidence-injection-v1.md`)
3. cross-review (af-cross-review만, design 큐 자동 발화)
4. PASS 시 v1 구현 진입

---

## 📦 보존: SST OpenCode 분석 (이전 세션)

### 다음 세션 시작 시 — 분석 전에 반드시 먼저 읽을 파일 (가정 금지, 실측만)

```bash
# 1. AST/구조 분석 경로
cat core/review_bundle.py            # 실제 build/save 출력 형식 (headers + per-file ## + risk lines)
cat core/ast_engine.py               # ast-grep-py wrapper
cat scripts/build_review_bundle.py   # hook 진입점

# 2. 진단 분석 경로 (휴면 가능성 있음)
cat core/hooks/lsp_check.py          # OpenCode 모드 A 등가, AGENT_LSP_CHECK 게이트
grep -n "LSPCheckHook\|lsp_check" core/hooks/event_bus.py core/agent_runner.py scripts/hook_runner.py
grep -rn "AGENT_LSP_CHECK" .claude/ .env 2>/dev/null

# 3. test gap (별도 경로)
cat scripts/test_gap_analyzer.py
grep -n "test_gap_analyzer" scripts/hook_runner.py core/review_bundle.py
```

### 답해야 할 질문 (가정 검증 후 답)

1. `core/review_bundle.py`의 실제 출력 schema는 정확히 무엇인가? `.af_review_queue/review_bundle.md` 샘플 파일을 직접 읽어서 확인.
2. `core/hooks/lsp_check.py`가 hook bus에 등록되어 있는가? 실제 호출되는 경로가 있는가?
3. `AGENT_LSP_CHECK` 환경변수가 어디서 설정되는가? 현재 활성/비활성?
4. `pyright`가 PATH에 있는가? `which pyright` 또는 `pyright --version` 결과는?
5. reviewer subagent (af-critic, af-cross-review)가 메인 에이전트의 `lsp_diagnostics` 결과를 받는가? (post_tool_call hook이 subagent까지 전파되는가?)
6. `scripts/test_gap_analyzer.py`는 어디서 호출되는가? `core/review_bundle.py`와 연결되어 있는가? (cross-review에 따르면 호출되지 않음 — 검증 필요)

### 절대 하지 말 것 (이번 세션의 BLOCK 사유)

1. ❌ "review_bundle.md에 §1~§7 섹션이 있다고 가정" — 실제로 헤더+per-file 블록만 있음
2. ❌ "LSPCheckHook을 모르고 신규 §8 추가 제안" — 이미 OpenCode 모드 A 등가 구현 존재
3. ❌ "pyright frozen build 폐기 권고와 동시에 pyright 채택" — 자기 모순
4. ❌ "OpenCode와 본질적으로 같은 패턴" 단정 — 실행 모델(메인 AI 단일 turn vs 2-stage hook+subagent) 다름
5. ❌ 분석문서에 운영 파라미터(timeout, source_hash, 임계값) 동시에 넣기 — 분석/권고 분리

### 권장 분석 흐름

1. **인벤토리 단계** (1~2시간): 위 6개 질문 답을 코드/설정/실행 결과로 수집. 가정 0개. 실측만.
2. **갭 식별 단계** (30분): OpenCode 코어와 우리 코어를 같은 좌표계(누가/언제/무엇을/어디로)로 정렬. 진짜 갭 1~2개만 추림.
3. **plan 작성 단계** (별도 세션): docs/plans/YYYY-MM-DD-*.md로 운영 파라미터 포함 plan. 분석 문서와 분리.

### 참고 자료

- `docs/참고/2026-05-02-opencode-lsp-architecture-analysis.md` — 본 세션 결과물 (정정 1회 후 commit, 그러나 §5에 잔존 결함 있음). **다음 세션은 이 문서를 reset 시점으로 두고 처음부터.**
- 본 세션 cross-review BLOCK 로그: `.af_review_queue/notifications/` 또는 hook_events.log
- OpenCode 실제 코드: `https://github.com/sst/opencode/tree/dev/packages/opencode/src/lsp` 및 `tool/lsp.ts`

---

## 미완료 작업 (우선순위순)

> **2026-04-30 정리**: T4(ensure_watcher TOCTOU) 완료 (`b76a6652`). BLOCK-prep 완료 (`630942c7`). test-gap-gate + P1 blast_tier downgrade + af-cross-review 4-round deliberation 완료 (`3612cc11`, `5f24283e`). 남은 작업: T3(exe 빌드) 1건.

### 🔥 다음 작업 — 3-Tier 비용 감축 플랜 (Phase 1부터)

**전체 플랜**: `docs/plans/2026-04-30-cross-review-cost-reduction-plan.md` (사용자+Claude Opus 4.7 합의)

**배경**: 이번 commit 검증 비용 195K 토큰 / 28분 — WARN-only인데 과도. af-critic 46 tool call의 대부분이 반복 탐색.

**진행 순서** (Phase 1~4):

| Phase | 작업 | 상태 | 시간 |
|-------|------|------|------|
| **1** | blast_tier/verdict/routing_state **3-개념 분리** (자기참조 검증 위험 인식 + 6-layer deterministic 검증) | ✅ 완료 (commit fa41575d, 2026-05-01) | — |
| **2-prep A** | `ast-grep-py>=0.35.0` → requirements.txt | ✅ 완료 (commit 23be1886, 2026-05-01) | — |
| **2-prep B** | `pyinstaller_hooks/hook-ast_grep_py.py` + af.spec hookspath 활성화 | ✅ 완료 (commit 23be1886, 2026-05-01) | — |
| **2-prep C** | exe 빌드 검증 (ast-grep-py pip install → smoke test, Windows 빌드는 Windows PC에서) | ✅ 완료 (Mac venv 0.42.1 설치·AST 스모크 테스트 통과, 2026-05-01) | — |
| **2-prep D** | `core/review_bundle.py` thin wrapper (build/save/load) | ✅ 완료 (commit 23be1886, 2026-05-01) | — |
| **2** | `scripts/build_review_bundle.py` + `hook_runner._post_edit_enqueue` 연동 | ✅ 완료 (2026-05-01) | — |
| **2.5** | tool call cap (af-test-runner:10 / af-critic:20 / af-cross-review:30) | ✅ 완료 (commit adf32175, 2026-05-01) | — |
| 3 | bundle-first scope + extension log enforcement | ✅ 완료 (2026-05-01) | — |
| 3.5 | 1주 데이터 수집 (T3-only accepted finding rate 핵심 메트릭) | ✅ 완료 (2026-05-01) | — |
| 4 | Smart routing + Tier 3 조건부 발화 | 대기 | 2시간 |

**예상 효과**: 토큰 195K → 60K, 시간 28분 → 6~10분.

**Phase 1 핵심 인식**: 자기참조 검증 — 3-tier가 막 수정한 코드(`scripts/review_gate.py`, `scripts/hook_runner.py`) 위에서 동작하므로 단독 신뢰 가능한 보증이 아님. **Primary trust는 hook을 우회하는 6-layer deterministic 테스트**, 3-tier는 secondary ceremony.

**Phase 1 즉시 진입 명령** (집 Mac에서):
```bash
git pull
python start_db.py agent-factory
# 자세한 8-step 실행 순서: docs/plans/2026-04-30-cross-review-cost-reduction-plan.md "다른 PC에서 재개 시 첫 단계"
```

---

### Sprint 4 — 다음 작업 (우선순위순)

| 우선순위 | 작업 | 파일 | 상세 |
|---------|------|------|------|
| ~~**T1**~~ ✅ | ~~knowledge skill SKILL.md fallback~~ | ~~`core/skill_metadata_adapter.py`~~ | 완료 `cf461e01` — _fill_missing_description + frontmatter 우선, 5개 테스트 |
| ~~**T2**~~ ✅ | ~~`_evolution_failed_skills` per-skill 조건 좁히기~~ | ~~`core/fsa_loop.py`~~ | 완료 `33000436` — _apply_evolution_guard 메서드, 탐지 실패 Level 5 강제, 26개 테스트 |
| **T3** (다음) | exe 빌드 + GitHub Release | `build_exe.py`, `af.spec` | `python build_exe.py` → `dist/af-1.2.22.zip`, `gh release create af-fsa_v1.2.22`. macOS 빌드 환경 확인 필요. |
| ~~**T4**~~ ✅ | ~~ensure_watcher() 동시 스폰 race 수정~~ | ~~`core/design_review_utils.py`~~ | 완료 `b76a6652` — O_CREAT\|O_EXCL spawn lock + double-check 패턴. 3-Tier PASS |

---

## 후순위 작업 (Sprint 4 완료 후)

### P0 — 설계문서 리뷰 정책 배포 에이전트 동기화

**배경**: 2026-05-01 CLAUDE.md 변경 — 단일 설계문서 리뷰를 `af-critic + af-cross-review` → `af-cross-review만`으로 변경. Work-item 세트도 `af-doc-qa + af-critic + af-cross-review` → `af-doc-qa + af-cross-review`로 축소.

**배포 빌드 동기화 필요 항목**:
- `scripts/check_design_pending.py`: 현재 주석/로그에 "af-critic + af-cross-review" 언급이 있으면 제거
- 배포된 Agent Factory 내부에서 설계문서 리뷰를 트리거하는 경로가 있다면 동일 정책 적용
- `docs/code-review.md` 정책 섹션 갱신 (있다면)

**소요 시간**: 30분 내외

---

### P1 — Multi-Provider Cross-Review 동적 fan-out

**목적**: 3-Tier 검증 파이프라인의 Tier 3(af-cross-review)을 구독 중인 AI 프로바이더에 따라 자동으로 확장·축소.

**핵심 동작**:
- 프로바이더 1개(Claude만) → Tier 3 skip
- 프로바이더 2개 이상 → 가용 외부 프로바이더 전부에 병렬 리뷰 요청 → 결과 합산 판정

**감지 3-state**:
| 상태 | 조건 | 동작 |
|------|------|------|
| `available` | CLI 설치 + ping 성공 | cross-check 포함 |
| `auth_expired` | CLI 설치 + ping 실패 | **블로킹** — 재인증 명령어 안내 (`AF_SKIP_PROVIDER=codex`로 1회 우회 가능) |
| `not_installed` | CLI PATH에 없음 | 조용히 skip |

**변경 파일**:
| 파일 | 작업 |
|------|------|
| `core/provider_detect.py` (신규) | CLI 설치·인증 감지, TTL 1h 캐시(`~/.af/provider_cache.json`) |
| `af.spec` | `hiddenimports`에 `core.provider_detect` 추가 |
| `.claude/agents/af-cross-review.md` | Step 0에서 감지 → 동적 fan-out (codex/gemini 병렬 호출) |
| `CLAUDE.md` | "교차검증 자동 실행" 룰: "Codex 호출" → "가용 외부 프로바이더 모두 호출 (없으면 skip)" |

**진행 순서**: ~~설계문서(`docs/2026-04-29-multi-provider-cross-review.md`)~~ ✅ → ~~af-critic+af-cross-review 2-agent 검증~~ ✅ → ~~Sprint A: `core/provider_detect.py`~~ ✅ (커밋 `3e956d7f`) → **Sprint B** (`af-cross-review.md` fan-out)

~~**Sprint B**~~ ✅ (커밋 `74dfa3c5`): `.claude/agents/af-cross-review.md` Step 0(3-gate) + Step 2(병렬 fan-out, timeout 180s, macOS 호환) + Step 3([ACCEPT★] 합의 가중치) + CLAUDE.md Tier 3 fan-out 설명 추가

---

### P2 — Cross-Review 정확도·범용성 개선 (2026-04-30 합의)

**배경**: P1 Sprint B로 동적 fan-out 인프라 완성. 그 위에서 ① 외부 LLM 입력 quality, ② Tier 3 출력 표준화, ③ provider-agnostic 일반화 3개 축으로 5단계 로드맵.

**진행 순서**: BLOCK-prep → 1a → (1b dry-run) → 1a 운영 1주 관찰 → 2 → 3 → β2 (수요 신호 시)

- [x] **BLOCK-prep** ✅ `630942c7` — `core/provider_detect.py` ThreadPool race condition 수정
      수정: `_probe_one(provider_id, installed: frozenset)` 시그니처 변경, installed_set을 ThreadPool 전 main thread 1회 계산 후 전달
      추가: `registry.py` double-checked locking + `tests/test_provider_detect.py` T12/T13/T14 — 22/22 PASS
      af-critic WARN (BLOCK 없음), af-cross-review PASS

- [x] **Phase 1a** ✅ `a8025d25` — `.claude/agents/af-cross-review.md` Step 1+2+3 프롬프트 개선
      Step 1: diff 추출 + 50KB 폴백 / Step 2: PRIMARY/BONUS 분리 + 메타 인식 + No-BLOCK 명시 + 자기검증 + [출력 형식] / Step 3: BONUS 분리 처리 + No-BLOCK 무시
      다음: dry-run 1회 (§10.2) — 별도 세션에서 실제 커밋에 cross-review 적용 후 측정

- [x] **af-critic BLOCK 픽스** ✅ `b0f74ad9` + `610c1aa3` — `core/provider_detect.py` Windows shell=True 안전성
      BLOCK1(`b0f74ad9`): `shutil`/`shlex` top import, `list2cmdline` 명시 변환, `stdin=DEVNULL`, timeout 5→30
      BLOCK2(`610c1aa3`): `_resolve_ping_cmd()` backslash 2중화 후 `shlex.split(posix=True)` — 따옴표 포함 경로 완전 파싱
      af-critic 최종 판정: **PASS** (WARN 2건 — 잘못된 env var 입력 시만 발생, advisory)

- [ ] **Phase 1b** — `codex review` 빌트인 통합 (위험: 中)
      목적: Codex 0.125.0의 `codex review` 전용 빌트인이 `codex exec` 대비 결함 탐지율이 좋은지 데이터 검증
      산출물: dry-run 보고서 → 긍정 시 codex 호출 라인 교체
      **선행 조건**: `gemini auth login` 실행 (현재 AUTH_EXPIRED 상태) — gemini 합의★ 가중치 회복 필요
      결정 대기: 측정 시점, known-bug 샘플 출처(`docs/code_review/code-review.md` 활용 검토)
      의존: Phase 1a 완료 후

- [~] **Phase 2** — 최종 판정 라벨 명시화 BLOCK/WARN/PASS (위험: 中) — **설계 v3 작성 완료, cross-review 재실행 대기**
      v1 (`5c77af16`, 2026-05-03): Critic 4건 + Cross-review WARN 산출
      v2 (`f8be0794`, 2026-05-03): v1 BLOCK 2건 정정 + deep-think 6건 추가 — Critic 단독 BLOCK (cross-review provider error)
      v3 (커밋 대기, 2026-05-03): Critic 8건 전수 반영 — design+코드 변경 6개 파일로 범위 확장
      목적: CLAUDE.md 정책 3개(BLOCK 정책, WARN-only no-fire, max_rounds=2)가 의지하는 라벨 안정화
      결정 사항 (v3):
        - 단독 [ACCEPT] Critical → BLOCK 유지 (§4.7)
        - [HOLD] 라벨은 finding-level에서도 제거, Phase 3 완전 이관 (§4.5)
        - [BONUS] finding 라벨로 승격, 헤더 = `#### N. [BONUS] [Severity] 제목` (§5.1 변경 6)
        - Medium → WARN (BLOCK 임계 없음, §4.8)
        - severity 누락 → BLOCK fail-safe default (§4.3)
        - Phase 2 = labeling + 측정/파서 정합 (§4.6) — 메트릭/파서 fail-safe 포함
      v3 commit 후 단계: cross-review 재실행 (codex 회복 후) → PASS 시 코드+에이전트 6개 파일 일괄 적용

- [ ] **Phase 3** — Peer verification (외부 CLI 상호 fact-check) (위험: 中~高)
      목적: dedup 한계 보완 (다른 표현의 같은 결함, 한쪽만 본 거짓 양성)
      산출물: Step 2.5 신설 + 비용 측정 보고서
      결정 대기: 비용 2배 수용, 외부 LLM 형식 강제 가능성, fan_out=1 폴백 로직
      의존: Phase 1a + Phase 2 완료 후

- [ ] **β2** — Provider-agnostic orchestrator (위험: 高)
      목적: Claude lock-in 해제, SaaS 전략(`project_saas_strategy_position.md`) 정합
      산출물: `core/cross_review_runner.py` + 판정 프롬프트 3종(Claude/Codex/Gemini) + thin wrapper
      결정 대기: 외부 사용자 수요 검증(현재 0건), Codex plugin marketplace 진입점, 판정 quality 차이 감수
      의존: Phase 1a + 1b + 2 완료, 외부 사용자 수요 ≥ 1건

---

## 세션 종료 체크리스트

1. 완료된 작업을 이 파일 "완료된 작업" 테이블에 추가
2. 미완료 작업의 상태 업데이트
3. `git add NEXT_STEPS.md && git commit -m "chore: NEXT_STEPS 업데이트"`
4. `git push`
5. `python end_db.py agent-factory`  ← Claude Code 메모리 Supabase 동기화
