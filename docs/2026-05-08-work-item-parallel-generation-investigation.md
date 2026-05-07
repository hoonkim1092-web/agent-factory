# Work-Item 5종 문서 병렬 생성 가능성 조사

> **목적**: feature-plan / feature-spec / implementation-design / implementation-tasks / approval-gate 5종을 현재 순차 생성에서 병렬 생성으로 전환할 수 있는지 검증.
>
> **세션 진입 방법**: `/clear` 후 이 파일을 먼저 읽고 시작.

---

## 1. 현재 구조 (sequential, work_item_generator.py:760-829)

```
Step 5a: feature-plan          ← project_brief + role_plan만 사용 (no prev)
Step 5b: feature-spec          ← _prev_doc=plan_content 의존
Step 5c: implementation-design ← _prev_doc=spec_content 의존
Step 5d: implementation-tasks  ← _prev_doc=design_content 의존
Step 5e: approval-gate         ← 독립 (gate.initialize() 호출만)
```

**의존성 체인**: `plan → spec → design → tasks` (4단계)
**독립 문서**: `approval-gate` (parallelize 가능)

---

## 2. 핵심 검증 질문

### Q1. `_prev_doc` 의존이 실제로 필수인가?

각 generator 프롬프트에 `_prev_doc`이 어떻게 주입되는지 확인 필요:

- `core/work_item_generator.py:537` `_generate_feature_plan`
- `core/work_item_generator.py:576` `_generate_feature_spec` (uses `prev_plan`)
- `core/work_item_generator.py:614` `_generate_implementation_design` (uses `prev_spec`)
- `core/work_item_generator.py:654` `_generate_implementation_tasks` (uses `prev_design`)

**확인할 것**:
- prev_doc이 **요약/제약 추출용**인가? (대체 가능)
- prev_doc이 **구조 일치용**인가? (대체 어려움 — 같은 phase 수, 같은 section ID 등)
- prev_doc 없을 때 fallback이 얼마나 나쁜가?

### Q2. 동일한 LLM 호출 구조에서 병렬 호출 시 충돌 발생하는가?

`execute_document_prompt()` (`core/requirement_llm.py:173`)는 CLI provider를 사용:
- claude_cli 단일 프로세스 → 동시 4개 호출 시 상호 간섭/세션 충돌 가능성
- codex_cli도 동일

**확인할 것**:
- `core/control_plane_llm.py` 또는 CLI 호출부에서 동시성 안전성 점검
- 이미 병렬 패턴이 있는 곳: `core/researcher.py:958` `ThreadPoolExecutor(max_workers=2)` (local + secondary 병렬)

### Q3. work-item 생성 평균 소요 시간이 병렬화 가치가 있는가?

현재 순차 5단계, claude_cli timeout 120s/300s. 포커 게임 실측:
- 각 문서당 평균 60~180s 추정
- 4개 순차 = 4~12분
- 병렬 (1단계로 압축 시) = 1~3분 → **3~4배 단축 가능**

---

## 3. 병렬화 옵션 (3가지)

### Option A: approval-gate만 분리 (안전)
```
[plan → spec → design → tasks] 순차 + approval-gate 병렬
```
효과: 거의 없음 (approval-gate는 파일 생성만, LLM 호출 없음)
**기각** — 병렬화 실익 없음

### Option B: prev_doc 의존 제거 + 4개 완전 병렬 (공격적)
```
[plan, spec, design, tasks] 모두 project_brief만 보고 생성
```
- 장점: 4배 시간 단축
- 단점: spec이 plan의 phase 구조를 못 따라감 → consistency 채점 떨어질 위험
- **검증 필요**: rubric `consistency` 차원 (phase_count_match) 스코어 비교

### Option C: 2단계 그룹 병렬 (절충)
```
Stage 1: [plan, design] 병렬 (둘 다 high-level — spec/tasks 없이도 작성 가능)
Stage 2: [spec, tasks] 병렬 (Stage 1 결과 양쪽을 prev_doc으로 주입)
```
- 장점: 2배 시간 단축, 의존성 일부 보존
- 단점: 구현 복잡, design이 spec 없이 작성되면 acceptance criteria 누락 위험

---

## 4. 검증 절차 (다음 세션에서 실행)

### Step 1: prev_doc 사용 패턴 확인
```bash
# 각 generator의 프롬프트에서 prev_doc이 어떻게 인용되는지
sed -n '537,720p' core/work_item_generator.py
```

### Step 2: CLI 동시 호출 안전성 확인
```bash
# claude_cli 동시 호출 테스트 (간단 스모크)
python3 -c "
from concurrent.futures import ThreadPoolExecutor
from core.requirement_llm import execute_document_prompt
prompts = ['1+1=?', '2+2=?', '3+3=?', '4+4=?']
with ThreadPoolExecutor(max_workers=4) as ex:
    results = list(ex.map(execute_document_prompt, prompts))
for r in results: print(r.get('ok'), r.get('text', '')[:30])
"
```

### Step 3: 작은 task로 Option B 시범 구현
- `_generate_*` 함수 4개를 `ThreadPoolExecutor(max_workers=4)`로 묶어 호출
- prev_doc 주입을 모두 빈 문자열로 통일
- minesweeper 같은 단순 프로젝트로 실행 후 5종 문서 품질 비교
  - rubric `consistency` 차원 점수
  - rubric `traceability` 차원 점수 (§N 참조 비율)

### Step 4: 결과 비교
| 메트릭 | Sequential | Option B (Parallel) |
|--------|------------|---------------------|
| 총 소요 시간 | ? | ? |
| consistency 점수 | ? | ? |
| traceability 점수 | ? | ? |
| 토큰 사용량 | ? | ? |

---

## 5. 예상 결정 기준

- 시간 단축 ≥ 3배 + rubric 점수 하락 < 0.5 → **Option B 채택**
- 시간 단축 ≥ 2배 + rubric 점수 유지 → **Option C 채택**
- 시간 단축 미미하거나 점수 하락 큼 → **현행 유지**

---

## 6. 관련 파일 (이 세션에서 이미 확인됨)

| 파일 | 역할 |
|------|------|
| `core/work_item_generator.py:760-829` | 메인 순차 생성 루프 |
| `core/work_item_generator.py:537-720` | 4개 generator 함수 |
| `core/work_item_generator.py:834-870` | `_generate_and_refine` 헬퍼 (placeholder refine 루프) |
| `core/requirement_llm.py:173` | `execute_document_prompt` (병렬 호출 진입점) |
| `core/researcher.py:958` | 기존 ThreadPoolExecutor 사용 예시 (참고) |
| `rubrics/work_item_doc_set.yaml` | 채점 기준 (consistency, traceability 차원) |

---

## 7. 컨텍스트 메모

- 이번 세션에서 확인한 사실:
  - `requires_web` 모드(포커 같은 신규 프로젝트)에선 claims=[] 정상
  - traceability 미생성도 정상 (claims 없으면 빈 문자열 반환)
  - CLI는 순차 fallover (claude_cli → codex_cli) — 병렬 호출 검증 필요
- **다음 결정**: Option B vs C — Step 1~3 검증 후 사용자에게 의견 묻기
