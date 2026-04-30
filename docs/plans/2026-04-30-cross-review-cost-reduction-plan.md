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

### Phase 1 — blast_tier / verdict / routing_state 개념 분리 (correctness)

**목적**: routing 신뢰 회복. 모든 후속 최적화의 전제.

#### 자기참조 검증 위험 (핵심 인식)

Phase 1이 바꾸는 코드(`scripts/review_gate.py`, `scripts/hook_runner.py`)는 **3-tier 검증 시스템 자체를 구성**한다. 즉:
- `pre_bash_review_gate` hook이 `is_gate_blocked()` 사용
- `post_agent_record` hook이 `_apply_test_gap_verdict()`, `record_review_done()` 사용

이를 수정한 직후 3-tier 검증을 돌리면, **검증자가 막 수정한 코드 위에서 동작**한다. 따라서:
- 3-tier PASS는 자기참조적이며 단독으로는 신뢰 가능한 보증이 아니다
- 진짜 보증은 hook을 우회하는 **deterministic 테스트**에서 와야 한다
- 3-tier는 의식(ceremony)이고, 신뢰 layer는 단위/통합/회귀/dry-run

#### 3-tier 비용을 줄이는 진짜 방법

**잘못된 framing**: "3-tier를 돌릴까 말까"
**옳은 framing**: "3-tier를 **한 번**만 돌리도록 한다"

→ 사전 deterministic 검증을 두텁게 → 3-tier에서 BLOCK 발견 확률 최소화 → retry cycle 회피.

#### 3-개념 분리 (Phase 1 종료 후 invariant)

| 개념 | 정의 | 결정 주체 | 변경 가능성 |
|------|------|---------|------------|
| `blast_tier` | 변경 영향 범위 (측정값) | `blast_radius.py` + `enqueue_agent_review.py:109`의 `max(existing, new)` 머징만 | **enqueue 외 변경 금지** |
| `verdict` | 각 agent 검증 결과 | 해당 agent | 자기 verdict만 변경 |
| `routing_state` | 현재 필요한 tier 집합 | `_required_tiers_for(state)` 순수 함수 | derived only, 저장 X |

**`enqueue_agent_review.py:109`의 max-merge가 "blast_tier 불변" invariant를 이미 지원하는 핵심**이다. 깨는 것은 `downgrade_blast_tier`만이며 이를 무력화하면 invariant이 자동 성립.

#### Phase 1 acceptance criteria — 4-question test

Phase 1 완료 시 코드만 보고 다음 4개에 명확히 답할 수 있어야 한다 (docstring으로 못 박음):

| 질문 | 답 | 검증 위치 |
|------|-----|-----------|
| blast_tier는 누가 결정하는가 | `blast_radius.classify_with_content()` + `enqueue_agent_review.py:109` max-merge **만** | `_required_tiers_for()` docstring + invariant test |
| test_gap FAIL은 어디에 기록되는가 | af-test-runner verdict + `.af_review_queue/test_gap_report.json` | `_apply_test_gap_verdict` docstring |
| gate는 어떤 상태를 보고 block하는가 | `state.reviews[]` (verdict) + `state.blast_tier` (불변) + `state.updated_at` (stale) | `is_gate_blocked()` docstring |
| 다음 tier 요구는 어디서 계산되는가 | `_required_tiers_for(state)` 순수 함수, 부작용 없음 | 함수명 + docstring |

이 4개를 docstring으로 명문화하면 architectural enforcement가 코드 자체에서 가능.

#### Scope discipline

**허용**:
- `_apply_test_gap_verdict()`에서 `downgrade_blast_tier()` 호출 제거
- `downgrade_blast_tier()` 본문을 `raise NotImplementedError(...)` + deprecation docstring으로 교체 (함수 정의는 보존)
- 4개 함수에 acceptance criteria docstring 명문화
- 단위/통합/회귀/dry-run 테스트 추가

**금지** (Phase 1 scope 위반):
- smart routing 추가 (Phase 4)
- Tier 3 skip 추가 (Phase 4)
- bundle 추가 (Phase 2)
- agent prompt 대규모 변경 (Phase 3)
- `downgrade_blast_tier()` 함수 정의 자체 삭제 (별도 cleanup commit으로 분리 — Phase 1 scope 외)

#### 6-Layer 검증 (3-tier 외 deterministic 검증)

| Layer | 작업 | 자기참조 회피 |
|-------|------|--------------|
| 1. 단위 테스트 | `_apply_test_gap_verdict` 직접 호출, blast_tier 불변 검증 | hook 우회, 함수 직접 호출 |
| 2. 통합 (정상) | af-test-runner FAIL → gate가 `verdict-block:af-test-runner` 반환 | tmp_path fixture, hook 미발화 |
| 3. 통합 (회복) | 테스트 보강 → blast_tier 불변 → 다음 tier 풀 진행 | tmp_path fixture |
| 4. 회귀 테스트 | 기존 pass/warn/block 판정 보존 | 기존 fixture 재사용 |
| 5. dry-run | 실제 pending JSON fixture로 `check_pending_review.py` 동작 검증 | 실제 시스템 미터치 |
| **6. state matrix** | `is_gate_blocked()` 4가지 상태 조합 (blast_tier × review × edit_after_review × verdict) parametrize | 순수 함수 테스트 |

**Layer 6 핵심** — `is_gate_blocked()`가 모든 routing 결정의 진실의 원천이므로, 이 함수가 4가지 상태 조합에서 정확히 동작하면 hook 체인 무관하게 routing은 신뢰 가능:

```python
@pytest.mark.parametrize("scenario,expected", [
    ({"blast_tier": 3, "all_reviews_pass": True, "edit_after_review": False},
     (False, "no-block")),
    ({"blast_tier": 3, "t1_verdict": "fail"},
     (True, "verdict-block:af-test-runner")),
    ({"blast_tier": 3, "t1_verdict": "pass", "edit_after_review": True},
     (True, "stale-review")),
    ({"blast_tier": 1, "t1_verdict": "pass"},
     (False, "no-block")),
])
def test_gate_blocks_correctly_for_state_matrix(...):
    ...
```

#### 안전한 실행 순서

| 순서 | 작업 | 자기참조 회피 |
|------|------|--------------|
| 1 | `git diff HEAD` baseline + 관련 파일 grep으로 영향 범위 확인 | 변경 전 상태 |
| 2 | 관련 테스트 baseline 실행 (`pytest tests/test_hook_runner_builtins.py tests/test_review_gate*.py -v`) | 현재 PASS 확인 |
| 3 | **실패 테스트 작성 (Layer 1~6)** — 변경 전에 TDD | 새 invariant 명시 |
| 4 | 최소 수정 (호출 제거 + `NotImplementedError` + 4 docstring) | 단일 concern |
| 5 | Layer 1~6 테스트 실행 → 모두 PASS | deterministic |
| 6 | dry-run: 실제 `pending_agent_review.json` fixture로 `check_pending_review.py` 동작 검증 | 실제 시스템 미터치 |
| 7 | **풀 3-tier 1회 (의식)** — Layer 1~6이 다 PASS면 BLOCK 확률 < 10% 추정 | self-ref 위험 인정 |
| 8 | 3-tier 결과를 "self-referential ceremony, primary trust from 6-layer deterministic tests"로 commit message에 명시 | 신뢰 한계 투명 |

#### `downgrade_blast_tier()` 처리 — `NotImplementedError`

Function definition 완전 삭제(scope creep) vs 호출만 제거(architectural intent implicit) 사이 절충:

```python
# scripts/review_gate.py
def downgrade_blast_tier(workspace: str, tier: int) -> None:
    """DEPRECATED (2026-04-30): blast_tier는 blast_radius.py + enqueue의
    max-merge만 결정한다. 이 함수는 verdict가 routing을 mutate하던 잘못된
    모델의 잔재이며, 호출되지 않는다.

    이 함수가 다시 호출되면 해당 호출은 architectural invariant 위반이다.
    향후 별도 cleanup commit에서 함수 정의 자체 삭제 예정.
    """
    raise NotImplementedError(
        "downgrade_blast_tier is deprecated — blast_tier is immutable through verdict cycle. "
        "See docs/plans/2026-04-30-cross-review-cost-reduction-plan.md Phase 1."
    )
```

장점:
- 향후 누군가 다시 호출하면 즉시 실패 (명시적 차단)
- 함수 grep 가능 (architectural intent 검색 가능)
- scope 최소 (함수 본문 ~12줄 → 4줄)
- 별도 cleanup commit으로 차후 깔끔히 제거 가능 (그땐 변경 작아서 3-tier 비용 작음)

#### 비용 영향

- **Phase 1 자체 검증 비용**: 풀 3-tier 1회 ≈ 195K 토큰, ~28분 (자기참조 ceremony)
- **Phase 1 이후 정상 운영**: test-gap FAIL 발생 시 평균 토큰 +30K (Tier 2/3 자연 회귀). 사용자가 테스트 충분히 추가하면 다음 사이클 PASS.
- **장기 amortize**: routing 신뢰 회복으로 Phase 2~4 안정 진행 가능. 1×195K는 향후 100×commit에서 13.5M 토큰 절감의 전제.

#### 소요 시간

- 코드 변경: 30~45분
- 6-layer 테스트 작성: 1~1.5시간
- dry-run + 풀 3-tier: ~30분
- **총**: 2~2.5시간

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

**핵심 메트릭** (Phase 4 routing 조건 fine-tune의 ground truth):
- **T3-only accepted finding rate** = (T3에서만 발견된 accepted findings) / (전체 accepted findings)
  - >30%: T3 고유 가치 큼 → skip 보수적
  - 10~30%: 중간 → 위험군 외 검토
  - <10%: T3 대체로 중복 → 공격적 skip 가능
- **T3-only finding의 severity 분포**: Critical/High만 보면 비율 < 10%여도 skip하면 안 됨
- **bundle hit rate**: 에이전트가 bundle 안에서 답을 찾은 비율 vs extension log 빈도

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
| 1 | blast_tier/verdict/routing_state 3-개념 분리 (호출 제거 + NotImplementedError + 6-layer 검증) | **즉시** | 2~2.5시간 |
| 2 | review_bundle.md 생성기 + bundle 자체 항상-Tier-3 등록 | 1순위 | 4~6시간 |
| 2.5 | tool call cap (안전망) | Phase 2와 병행 | 30분 |
| 3 | bundle-first scope + extension log enforcement | 2순위 | 1시간 |
| 3.5 | 1주 데이터 수집 (review_metrics.jsonl + T3-only finding rate) | 의무 | 1시간 + 1주 |
| 4 | Smart routing + Tier 3 조건부 발화 | 3순위 (데이터 후) | 2시간 |

---

## 진행 시 주의사항

### Phase 1 작업 시
- 자기참조 검증 위험: 3-tier가 막 수정한 코드 위에서 동작 → primary trust는 6-layer deterministic 테스트
- `downgrade_blast_tier()` 함수 정의는 보존하되 본문을 `raise NotImplementedError(...)` + deprecation docstring으로 교체
- 4개 함수(`_required_tiers_for`, `_apply_test_gap_verdict`, `is_gate_blocked`, `_required_tiers_for`)에 acceptance criteria docstring 명문화 (4-question 답)
- `Master_Blueprint.md §9` 업데이트: "test-gap FAIL → blast_tier=1 다운그레이드" 제거. 대신 3-개념 분리 invariant 명시
- 6-layer 검증 모두 PASS 후에만 풀 3-tier 발화 (의식적 1회)
- BLOCK 발생 시: 첫 retry는 의식 통과로 간주. 2회 BLOCK 시 사용자에게 escalate (옵션 C: manual brief 후퇴)
- 함수 정의 자체 삭제는 별도 cleanup commit (Phase 1 scope 외)
- 기존 메모리 `feedback_codex_reply_for_deliberation.md`와 무관 (별개 주제)

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
```

### Phase 1 8-step 실행 순서

1. **Baseline 확인**:
   ```bash
   git diff HEAD
   grep -rn "downgrade_blast_tier" scripts/ tests/  # 영향 범위
   pytest tests/test_hook_runner_builtins.py tests/test_review_gate*.py -v  # 현재 PASS
   ```

2. **6-layer 테스트 작성 (변경 전 TDD)**:
   - Layer 1 단위: `test_apply_test_gap_verdict_does_not_modify_blast_tier`
   - Layer 2 통합: `test_gate_blocks_when_test_gap_fail_recorded`
   - Layer 3 통합: `test_blast_tier_preserved_through_test_recovery_cycle`
   - Layer 4 회귀: 기존 테스트 검증 그대로 PASS
   - Layer 5 dry-run: `test_check_pending_review_against_real_fixture`
   - Layer 6 state matrix: `test_gate_blocks_correctly_for_state_matrix` (parametrize 4 scenarios)

3. **최소 수정**:
   - `scripts/hook_runner.py`: `_apply_test_gap_verdict()`에서 `from scripts.review_gate import downgrade_blast_tier` + `downgrade_blast_tier(workspace, 1)` 제거
   - `scripts/review_gate.py`: `downgrade_blast_tier()` 본문을 `raise NotImplementedError(...)` + deprecation docstring 교체
   - 4개 함수(`_required_tiers_for`, `_apply_test_gap_verdict`, `is_gate_blocked`, `_required_tiers_for`)에 acceptance criteria docstring 명문화

4. **6-layer 테스트 실행 → 모두 PASS 확인**

5. **dry-run**:
   ```bash
   # 실제 fixture로 check_pending_review.py 동작 검증
   cp <real_pending.json> tests/fixtures/pending_t3_with_test_gap_fail.json
   python scripts/check_pending_review.py --workspace tests/fixtures
   ```

6. **`Master_Blueprint.md §9` 업데이트**: "test-gap FAIL → blast_tier=1 다운그레이드" 제거. 3-개념 분리 invariant 명시.

7. **풀 3-tier 발화 (의식)**:
   - af-test-runner → af-critic → af-cross-review
   - 6-layer가 다 PASS이므로 BLOCK 확률 < 10% 추정
   - BLOCK 시 1회 retry. 2회 BLOCK 시 사용자에게 escalate.

8. **Commit message에 self-ref 한계 명시**:
   ```
   feat(phase1): blast_tier/verdict/routing_state 3-concept separation

   Primary trust: 6-layer deterministic tests (unit/integration/regression/dry-run/state-matrix)
   3-tier verification: self-referential ceremony, secondary trust only
   ```

9. **Push + memory sync**:
   ```bash
   git push
   python end_db.py agent-factory
   ```

---

## 변경 이력

- 2026-04-30 초안: 사용자 + Claude(Sonnet 4.6→Opus 4.7) deliberation 합의.
  - 핵심 reordering: B2-1(routing 신뢰) → B1(bundle) → A1수정(scope) → A3(cap) → smart routing
  - 4가지 운영 보강: bundle 무효화, 크기 cap, extension log enforcement, 1주 데이터 수집
- 2026-04-30 정정: Phase 1을 자기참조 검증 framing으로 재정의.
  - "downgrade_blast_tier 호출 제거"에서 "blast_tier/verdict/routing_state 3-개념 분리"로 확장
  - 6-layer deterministic 검증을 primary trust로, 3-tier를 secondary ceremony로 명문화
  - Phase 1 acceptance criteria 4-question test 추가
  - 함수 처리 정정: 완전 삭제 → `NotImplementedError` + deprecation
  - T3-only accepted finding rate를 Phase 3.5 핵심 메트릭으로 명시
