# 3-Tier 교차검증 비용 감축 플랜

작성일: 2026-04-30
대상 브랜치: `2026-04-14-build-diet`
선행 합의: 사용자 + Claude(Sonnet 4.6 → Opus 4.7) deliberation

---

## 배경

이번 commit (`d28c3948` 이전 3개 작업) 검증 시 실측 비용:

| Tier | 토큰 | 시간 | tool calls |
|------|------|------|------------|
| T1 af-test-runner | 14,191 | 24초 | 4 |
| T2 af-critic | 43,639 | **22분** | **46** |
| T3 af-cross-review | 137,292 | 6분 | 30 |
| 합계 | 195,122 | ~28분 | 80 |

WARN-only 결과 — BLOCK 0건. 발견 가치는 있었음(WARN-1: blast_tier 책임 경계 문제), 하지만 비용 비율이 과도함.

**핵심 진단**:
- af-critic 46 tool call의 대부분이 같은 파일 반복 Read (탐색 비용 폭주)
- af-cross-review 137K 토큰 — 가장 가치 있는 발견은 여기서 나왔지만 절약 여지 큼
- 모두 같은 코드를 처음부터 다시 탐색 (context 재구축 비용)

---

## 설계 원칙

1. **"행동 제한"이 아닌 "탐색 비용 제거"**: scope cut은 reframing 발견(WARN-1 같은)을 놓친다. 같은 정보를 싸게 제공하는 게 정답.
2. **routing 의사결정과 비용 최적화 분리**: `downgrade_blast_tier`처럼 둘이 섞이면 신뢰 무너짐. blast_tier는 `blast_radius.py`만 결정.
3. **에이전트 독립성 유지**: af-critic + af-cross-review 통합은 reframing 가치 손실. bundle만 공유, 판단은 독립.
4. **Tier 3 발화 조건은 "위험군" 기준**: finding-count는 cross-review의 가치를 정량 환원하는 실수.
5. **Phase 4 진입 전 1주 데이터 수집**: 추정 기반 routing 변경 금지.

---

## 단계별 진행 (Phase 1 → 4)

### Phase 1 — blast_tier/verdict 분리 (correctness)

**목적**: routing 신뢰 회복. 모든 후속 최적화의 전제.

**현 문제**:
- `scripts/hook_runner.py:359` `_apply_test_gap_verdict()`이 test-gap FAIL 시 `downgrade_blast_tier(workspace, 1)` 호출
- 결과: blast_tier가 영구 1로 낮아져 다음 사이클에서 af-critic/af-cross-review가 routing에서 제외
- WARN-1 (af-cross-review): "blast_tier 결정권은 `blast_radius.py`에 있어야 하는데 test-gap FAIL이 이를 덮어쓴다"

**수정**:
1. `scripts/hook_runner.py`: `_apply_test_gap_verdict()`에서 `downgrade_blast_tier()` 호출 제거
2. `scripts/review_gate.py`: `downgrade_blast_tier()` 함수 자체는 보존 (다른 합법적 사용처 가능). 단 deprecation 주석 추가
3. test-gap FAIL → af-test-runner verdict=fail 전파만으로 충분 → gate가 missing-tier-2/3로 BLOCK → 사용자 테스트 보강 → 풀 3-tier 자연 회귀

**회귀 테스트**:
- `tests/test_hook_runner_builtins.py`:
  - 기존 `test_apply_test_gap_verdict_downgrades_blast_tier_on_fail` → `test_apply_test_gap_verdict_does_not_modify_blast_tier_on_fail`로 변경
  - blast_tier=3 인 상태에서 test-gap FAIL → blast_tier 그대로 3 유지 확인
- `tests/test_review_gate_phase0.py`에 추가:
  - test-gap FAIL 후 풀 3-tier 발화 시나리오

**비용 영향**: test-gap FAIL 발생 시 평균 토큰 +30K (Tier 2/3 회귀). 단, 이는 정상 동작이며 사용자가 테스트를 충분히 추가하면 다음 사이클에서 PASS.

**소요 시간**: 30~45분

---

### Phase 2 — review_bundle.md 생성기 (탐색 비용 제거 핵심)

**목적**: 각 에이전트가 같은 파일을 반복 탐색하지 않도록 사전 번들 생성.

**산출물**:
- `scripts/build_review_bundle.py` (신규)
- `tests/test_build_review_bundle.py` (신규)
- `.af_review_queue/review_bundle.md` (자동 생성)

**bundle 내용** (사전 합의):
```
# Review Bundle (generated_at: ISO8601, source_hash: <sha256 of inputs>)

## 1. Pending Files
- core/foo.py (blast_tier=3, risk_flags=[subprocess, shell])
- tests/test_foo.py (blast_tier=1)

## 2. Git Diff
<full git diff HEAD -- pending_files>
<untracked synthetic added diff>

## 3. Test Gap Analysis
<test_gap_report.json 내용 또는 "PASS">

## 4. Related Tests
- tests/test_foo.py:
  <import 라인 + test 함수명 목록>

## 5. Direct Callers (1-step)
- core/bar.py:42 imports core.foo.do_something
  <call site ±5 lines>
- (max 3 callers per changed symbol)

## 6. Risk Flags
- subprocess/shell change in core/foo.py:_run_one
- platform branch in core/foo.py:_resolve_path

## 7. Prior Findings (if any)
<직전 라운드 last_round_summary>

## 8. Bundle Stats
- caller files included: 3/8 (5 truncated due to cap)
- size: 47KB / 100KB cap
```

**무효화 규칙** (필수 명시):
- bundle 헤더에 `generated_at`, `source_hash` 기록
- `source_hash` = sha256(pending_agent_review.json + 변경 파일 mtime + diff 본문)
- 에이전트 진입 시 bundle.md 첫 줄 읽고 `pending_agent_review.json.updated_at` > `bundle.generated_at`이면 무효 → 재생성 요청
- 재생성 비용 ~1초 (deterministic, hook으로 자동 트리거)

**크기 cap**:
- 총 100KB
- caller 추출: 변경 심볼당 최대 3개 (직접 호출 라인 ±5줄, 전체 파일 X)
- 50KB 초과 시 caller 부분부터 잘라냄
- bundle 헤더에 "포함된 caller K/N, M개 생략" 명시

**bundle 생성기 자체는 항상 Tier 3 검증**:
- bundle 생성 버그 시 모든 검토가 잘못된 정보 위에서 돌아감
- `scripts/build_review_bundle.py`는 Phase 4의 항상-Tier-3 리스트에 추가

**소요 시간**: 4~6시간 (테스트 포함)

---

### Phase 2.5 — tool call cap (안전망)

**목적**: bundle 안정화 전까지 폭주 방지.

**프롬프트 추가** (각 에이전트):
```
## Tool Call 상한
- 본 에이전트의 tool call 상한은 N회.
- 80% (N×0.8) 소진 시 다음 사항을 응답에 명시하고 종결:
  1. 지금까지 확인한 파일 목록
  2. 확인하지 못한 리스크 가설
  3. 추가 검증이 필요한지 여부
- "추가 검증 필요"로 종결한 경우 verdict 라인에 `[INCOMPLETE]` 마커 추가.
```

**초기 cap**:
- af-test-runner: 10
- af-critic: **20** (15는 bundle 미배포 상태에서 너무 빡빡)
- af-cross-review: 30

**Phase 3 도입 후** (bundle 안정화):
- af-critic: 20 → 15
- af-cross-review: 30 → 25

**소요 시간**: 30분 (3개 에이전트 프롬프트 수정)

---

### Phase 3 — bundle-first scope + extension log enforcement

**목적**: 에이전트가 bundle 외 탐색 시 근거 강제.

**`.claude/agents/af-critic.md` 및 `af-cross-review.md` 추가**:

```markdown
## 입력 정책

1. 진입 시 `.af_review_queue/review_bundle.md`를 먼저 읽는다.
2. bundle 안의 파일은 자유 검토.
3. bundle 밖 추가 Read는 다음 형식의 extension log에 사전 기록:
   ```
   ### Extension #N
   - target: file:line
   - hypothesis: <왜 필요한가, 어떤 risk 검증>
   - result: <verified | rejected | hold>
   ```
4. 최종 응답 끝에 extension log 전체 출력.
5. extension log 항목 5개 초과 시 verdict 라인에 `[scope-creep]` 마커 자동 추가.
6. bundle stale 감지 시 즉시 종결 + `bundle-stale` 이유 보고.
```

**post-hoc 감사 가능**:
- extension log = 정량 지표 (개수)
- 비효율 자동 추적 (이번 af-critic 46 tool call 중 41개가 무근거였는지 검증 가능)

**소요 시간**: 1시간

---

### Phase 3.5 — 1주 데이터 수집

**Phase 3 완료 후 Phase 4 진입 전 의무 단계**.

**측정 항목** (자동 로그):
- `.af_review_queue/review_metrics.jsonl`
  - `commit_sha`, `tier`, `agent`, `tokens`, `duration_ms`, `tool_calls`, `extension_log_count`, `verdict`, `findings_count`
- `.af_review_queue/skip_audit.jsonl`
  - 항상-Tier-3 외에서 skip된 변경의 사후 BLOCK 발견 (다음 라운드 또는 PR 리뷰)

**판단 기준** (1주 후):
- Tier 3 발화/skip별 BLOCK 비율 차이 < 5% → skip 안전
- 항상-Tier-3 리스트 외에서 BLOCK 발견 0건 → 리스트 확정
- 데이터 부족 시 추가 1주 연장

**소요 시간**: 측정 인프라 1시간 + 1주 대기

---

### Phase 4 — Smart routing + Tier 3 조건부 발화

**진입 전제**: Phase 3.5 데이터 수집 완료.

**routing 로직** (`scripts/check_pending_review.py` 또는 `review_gate.py`):

```python
# 항상 Tier 3 발화 (변경 위험군)
ALWAYS_TIER_3_PATTERNS = [
    r"scripts/hook_runner\.py",
    r"scripts/review_gate\.py",
    r"scripts/check_pending_review\.py",
    r"scripts/check_design_pending\.py",
    r"scripts/enqueue_agent_review\.py",
    r"scripts/blast_radius\.py",
    r"scripts/build_review_bundle\.py",
    r"\.claude/agents/.*\.md",
    r"\.claude/skills/.*",
    # subprocess/shell/path/frozen build core 변경
    r"core/.*provider.*\.py",
    r"core/providers/.*",
]

def required_tiers(state) -> list[int]:
    files = state.get("files", [])
    blast_tier = int(state.get("blast_tier", 2))

    # 1. 항상 Tier 3
    if any(re.search(p, f) for p in ALWAYS_TIER_3_PATTERNS for f in files):
        return [1, 2, 3]

    # 2. blast_tier 1 (단순 변경)
    if blast_tier == 1:
        return [1]

    # 3. 기본 Tier 2 (Tier 3는 조건부)
    if blast_tier == 2:
        return [1, 2]

    # 4. Tier 3 (blast_tier=3)
    return [1, 2, 3]
```

**Tier 3 조건부 발화** (Phase 2 완료 후 별도):
- af-critic verdict가 BLOCK/FAIL → Tier 3 강제
- af-critic Medium 2개 이상 또는 High 1개 이상 → Tier 3 발화
- 외 → Tier 3 skip 가능

**소요 시간**: 2시간 (구현 + 회귀 테스트)

---

## 예상 최종 목표

| 지표 | 현재 | Phase 1~3 후 | Phase 4 후 |
|------|------|-------------|------------|
| 평균 토큰 | 195K | 70~90K | 60K |
| 평균 시간 | 28분 | 8~12분 | 6~10분 |
| af-critic tool calls | 46 | <20 | <15 |
| 품질 손실 | — | 낮음 | 낮음 (데이터 검증) |

---

## 진행 순서 요약

| Phase | 작업 | 우선순위 | 예상 시간 |
|-------|------|---------|----------|
| 1 | blast_tier/verdict 분리 (downgrade_blast_tier 호출 제거) | **즉시** | 30~45분 |
| 2 | review_bundle.md 생성기 + bundle 자체 항상-Tier-3 등록 | 1순위 | 4~6시간 |
| 2.5 | tool call cap (안전망) | Phase 2와 병행 | 30분 |
| 3 | bundle-first scope + extension log enforcement | 2순위 | 1시간 |
| 3.5 | 1주 데이터 수집 (review_metrics.jsonl) | 의무 | 1시간 + 1주 |
| 4 | Smart routing + Tier 3 조건부 발화 | 3순위 (데이터 후) | 2시간 |

---

## 진행 시 주의사항

### Phase 1 작업 시
- `downgrade_blast_tier` 함수 자체는 보존 (다른 합법적 사용처 가능). 호출만 제거.
- `Master_Blueprint.md §9` 업데이트 필요: "test-gap FAIL → blast_tier=1 다운그레이드" 설명 제거 또는 deprecated 표시.
- 기존 메모리 `feedback_codex_reply_for_deliberation.md`와 무관 (별개 주제).

### Phase 2 작업 시
- `scripts/build_review_bundle.py`는 항상-Tier-3 리스트에 사전 등록 (Phase 4 patterns에 추가)
- bundle 무효화 hook은 `post_edit_enqueue` 다음 단계에 추가 (자동 재생성)
- 50KB diff cap은 기존 `af-cross-review.md` Step 1 로직과 정합성 유지

### Phase 3 작업 시
- extension log 형식은 ML 후처리 가능하도록 일관 유지 (`### Extension #N` 헤더 고정)
- 두 에이전트(af-critic, af-cross-review)에 동일 정책 적용

### Mac/Windows 호환성
- 모든 새 스크립트는 `pathlib.Path` 사용, 절대경로 하드코딩 금지
- `.claude/settings.local.json`은 이미 `sh scripts/hookpy.sh` 패턴으로 통일됨 (2026-04-30 마이그레이션 완료)

---

## 다른 PC에서 재개 시 첫 단계

```bash
git pull
python start_db.py agent-factory  # 메모리 동기화

# Phase 1 시작
# 1. scripts/hook_runner.py 의 _apply_test_gap_verdict() 에서
#    "from scripts.review_gate import downgrade_blast_tier" 와
#    "downgrade_blast_tier(workspace, 1)" 호출 제거
# 2. 기존 테스트 test_apply_test_gap_verdict_downgrades_blast_tier_on_fail 를
#    test_apply_test_gap_verdict_does_not_modify_blast_tier_on_fail 로 변경 + 검증 로직 수정
# 3. py_compile + pytest 실행
# 4. 풀 3-tier 검증 (단, Phase 1은 routing 영향이 크므로 항상-Tier-3 적용)
# 5. commit + push
```

---

## 변경 이력

- 2026-04-30: 초안 작성. 사용자 + Claude(Sonnet→Opus) deliberation 합의.
- 핵심 reordering: B2-1(routing 신뢰) → B1(bundle) → A1수정(scope) → A3(cap) → smart routing
- 4가지 운영 보강: bundle 무효화, 크기 cap, extension log enforcement, 1주 데이터 수집
