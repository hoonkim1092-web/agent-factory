# 통합 교차검증 QA 파이프라인 설계

> 날짜: 2026-04-09
> 상태: Draft → Rev.1 (교차검증 피드백 반영)
> 브랜치: `agent-factory_harness_Claude_Setup_and_Pipeline_v1`

---

## 1. 문제 정의

현재 교차검증이 **런타임 코드 실행**에만 적용되어 있고, 3개 영역이 비어 있다.

| 영역 | 현재 | 목표 |
|------|------|------|
| 런타임 코드 실행 | ✅ CrossVerificationLoop | 유지 |
| 런타임 문서 생성 (work-items) | ❌ 구조 검증만 | ✅ 교차검증 + QA |
| 개발환경 설계 문서 | ✅ design_review_watcher | 유지 |
| 개발환경 코드 변경 | ❌ 기록만 (code_review_updater) | ✅ 교차검증 + QA |

**추가 문제**: 교차검증 결과가 **최종 판정만 저장**되거나 **파일로 저장되지 않는** 경우가 있어, 검증자별 의견 추적이 불완전하다.

---

## 2. 설계 원칙

1. **검증 투명성**: 모든 검증자의 개별 의견 + 판정자의 근거를 보고서로 남긴다
2. **기존 인프라 재사용**: design_review_watcher, CrossVerificationLoop, pipeline_quality를 확장한다
3. **레벨별 분기**: starter/dynamic/enterprise에서 검증 깊이를 다르게 적용한다
4. **비용 제어**: quiet period, 최소 변경량, 세션 횟수 제한으로 불필요한 호출을 방지한다

---

## 3. 통합 보고서 체계

### 3.1 보고서 형식 (모든 교차검증 공통)

모든 교차검증은 동일한 보고서 형식으로 결과를 남긴다.

```markdown
# {review_type} Review: {target_name}

> Source: {file_path 또는 work-item slug}
> Date: {YYYY-MM-DD HH:MM}
> Type: {design | code | document}
> Providers: critic={name}, cross={name}, judge={name}
> Mode: {single-provider | cross-review}
> Trigger: {hook | pipeline | manual}
> Round: {N}/{max_rounds}

---

## 검증자 A (Critic): {provider_name}

### 역할
독립적 비평 — 문제 발견이 임무

### 발견 사항

1. **[High] 제목**
   - 대상: `파일:라인` 또는 "섹션 인용"
   - 문제: 구체적 설명
   - 근거: 코드/문서 참조
   - 제안: 수정 방향

2. **[Medium] 제목**
   ...

### Critic 소결
- 발견: N개 (Critical: 0, High: 2, Medium: 1, Low: 0)
- 판정: BLOCK / WARN / PASS

---

## 검증자 B (Cross): {provider_name}

### 역할
교차 관점 리뷰 — 원저자가 놓친 시각 제공

### 발견 사항

1. **[ACCEPT] 제목**
   - 대상: `파일:라인` 또는 "섹션 인용"
   - 문제: 설명
   - 근거: 코드/문서 참조
   - 제안: 수정 방향

2. **[HOLD] 제목**
   - 대상: ...
   - 관심사항: ...
   - 부족 정보: 판단에 필요한 추가 정보

### Cross 소결
- 발견: N개 (ACCEPT: X, REJECT: Y, HOLD: Z)

---

## 최종 판정 (Judge): {provider_name}

### 종합 판정: BLOCK / WARN / PASS

### 통합 발견 사항

| # | 제목 | 심각도 | 판정 | Critic | Cross | 근거 |
|---|------|--------|------|--------|-------|------|
| 1 | ... | High | ACCEPT | ✅ 지적 | ✅ 동의 | 양쪽 일치 |
| 2 | ... | Medium | ACCEPT | ✅ 지적 | — 미지적 | 코드 근거 강함 |
| 3 | ... | Low | REJECT | — | ✅ 지적 | AF 아키텍처상 의도적 설계 |
| 4 | ... | Medium | HOLD | ✅ 지적 | — | 추가 컨텍스트 필요 |

### 판정 근거
- ACCEPT 항목: 수정 필요한 이유 + 우선순위
- REJECT 항목: 기각 이유 (코드 인용)
- HOLD 항목: 판단 보류 사유 + 필요 정보

### 수정 지시 (BLOCK/WARN 시)
1. [필수] 항목 1 수정 방향
2. [필수] 항목 2 수정 방향
3. [권장] 항목 4 확인 후 판단

---

## 메타데이터

- 총 토큰: {critic_tokens + cross_tokens + judge_tokens}
- 소요 시간: {seconds}
- 이전 라운드: {있으면 링크}
```

### 3.2 저장 위치

| review_type | 저장 경로 | 파일명 패턴 |
|-------------|----------|------------|
| design | `docs/reviews/` | `{ts}-{stem}-design-review.md` |
| code | `docs/reviews/` | `{ts}-{branch}-code-review.md` |
| document | `docs/work-items/{slug}/` | `verification-report.md` (라운드별 누적 append) |

**document 타입**은 work-item 디렉토리 안에 직접 저장한다 — 문서와 검증 결과가 같은 위치에 있어야 승인 게이트에서 참조 가능.

> **Rev.1 수정**: 덮어쓰기 → 라운드별 누적 append 방식으로 변경. 각 라운드의 검증자 의견이 보존되어야 재실행 시 이전 라운드 대비 개선 추적이 가능하다. 파일 내부에 `## Round {N}` 섹션으로 구분한다.

### 3.3 보고서 생성 모듈 (신규)

```
core/review_report.py (~120줄)
```

```python
@dataclass
class ReviewerResult:
    """개별 검증자의 리뷰 결과."""
    provider: str           # "claude" | "codex" | "gemini"
    role: str               # "critic" | "cross"
    raw_output: str         # LLM 원문 출력
    findings_count: int
    verdict: str            # "BLOCK" | "WARN" | "PASS" (critic) / "ACCEPT" | "REJECT" | "HOLD" (cross)
    elapsed_seconds: float
    token_count: int

@dataclass
class JudgeResult:
    """판정자의 최종 판정 결과."""
    provider: str
    verdict: str            # "BLOCK" | "WARN" | "PASS"
    aggregated_output: str  # 통합 마크다운
    accept_count: int
    reject_count: int
    hold_count: int
    elapsed_seconds: float
    token_count: int

@dataclass
class ReviewReport:
    """교차검증 전체 보고서."""
    review_type: str        # "design" | "code" | "document"
    target: str             # 파일 경로 또는 work-item slug
    trigger: str            # "hook" | "pipeline" | "manual"
    round_num: int
    max_rounds: int
    critic: ReviewerResult
    cross: ReviewerResult | None  # 단일 프로바이더일 때 None
    judge: JudgeResult
    timestamp: str

    def to_markdown(self) -> str:
        """§3.1 형식의 마크다운 보고서 생성."""
        ...

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리."""
        ...

    def save(self, workspace: str) -> str:
        """§3.2 규칙에 따라 파일 저장. 저장 경로 반환."""
        ...
```

기존 `design_review_watcher._write_result()`와 `CrossVerificationLoop`의 결과 저장을 이 모듈로 통일한다.

---

## 4. Part A: 개발환경 코드 교차검증

### 4.1 흐름 (6단계)

```
단계 1: 감지 (PostToolUse hook)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Claude가 .py 파일 Edit/Write
    ↓
  code_review_trigger.py 실행
    ↓
  트리거 조건 판정:
    ✅ core/**/*.py, scripts/**/*.py, skills/**/*.py
    ❌ tests/**, build/**, dist/**, __pycache__/**
    ❌ diff 5줄 미만 (import만, docstring만)
    ❌ 세션 내 이미 5회 실행됨
    ↓
  .af_review_queue/pending/code/code_{pathhash}.json 큐잉
  (design과 code 큐 디렉토리 분리: pending/design/, pending/code/)

단계 2: 배치 (quiet period 15초)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  연속 편집 대기 — 15초간 추가 편집 없으면 배치 확정
  같은 파일 연속 편집 → 하나로 묶음
  다른 파일이라도 같은 quiet period 내면 → 하나의 리뷰 요청으로 통합
    ↓
  watcher 자동 기동 (ensure_watcher)
  (단일 watcher가 pending/design/ + pending/code/ 양쪽 폴링)

단계 3: 교차검증 (병렬)
━━━━━━━━━━━━━━━━━━━━━━
  프로바이더 감지: detect_providers()
    ↓
  ┌─ Critic (프로바이더 A) ─────────────────────
  │  code_critic.txt 프롬프트 + git diff + code-review.md
  │  체크리스트: 버그, 안전성, 성능, 설계, 엣지케이스
  │  → ReviewerResult(role="critic")
  │
  └─ Cross (프로바이더 B, 자율 탐색) ───────────
     code_cross_review.txt 프롬프트
     codex exec: 변경 파일 + 호출자/피호출자 직접 탐색
     → ReviewerResult(role="cross")

단계 4: 판정 (Aggregation)
━━━━━━━━━━━━━━━━━━━━━━━━━
  Judge (우선순위: claude > codex > gemini)
  code_aggregation.txt 프롬프트
    ↓
  양쪽 리뷰 통합 → 항목별 ACCEPT/REJECT/HOLD
    ↓
  JudgeResult(verdict="BLOCK" | "WARN" | "PASS")

단계 5: 보고서 생성 + 피드백
━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ReviewReport.save() → docs/reviews/{ts}-{branch}-code-review.md
    ↓
  .af_review_queue/notifications/code_{hash}.txt
    → 다음 PostToolUse 때 Claude 대화에 자동 삽입
    → "[교차검증] WARN — 2 ACCEPT, 1 HOLD. docs/reviews/... 참조"

단계 6: 수정 + QA
━━━━━━━━━━━━━━━━━
  Claude가 ACCEPT 항목 수정
    ↓
  pytest 실행
    ↓
  통과 → 완료
  실패 → 단계 3부터 재실행 (최대 2회)
```

### 4.2 트리거 조건

```python
# core/design_review_utils.py 확장 (또는 별도 code_review_utils.py)

CODE_INCLUDE_PATTERNS = [
    "core/**/*.py",
    "scripts/**/*.py",
    "skills/**/*.py",
]

CODE_EXCLUDE_PATTERNS = [
    "tests/**",
    "build/**",
    "dist/**",
    "**/__pycache__/**",
    "**/*.pyc",
]

# 최소 변경량 필터
MIN_DIFF_LINES = 5

# 무의미 변경 스킵
SKIP_PATTERNS = [
    r"^[\+\-]\s*(import |from .+ import )",   # import만 변경
    r"^[\+\-]\s*(\"\"\"|\'\'\').*",            # docstring만 변경
    r"^[\+\-]\s*#",                             # 주석만 변경
]
```

### 4.3 비용 제어

| 제어 장치 | 값 | 근거 |
|----------|-----|------|
| quiet period | 15초 | 코드는 연속 편집 빈번 (설계 문서 8초보다 김) |
| 최소 diff | 5줄 | 타이포/import 수정 제외 |
| 세션 최대 | 5회/세션 | codex 비용 제한 |
| 배치 통합 | quiet period 내 모든 편집 → 1회 리뷰 | 파일 3개 동시 편집해도 1회 |
| 스킵 패턴 | import/docstring/주석만 변경 | 무의미한 리뷰 방지 |

> **세션 카운터 구현**: `.af_review_queue/.code_review_count` 파일에 `{"count": N, "date": "YYYY-MM-DD"}` 저장. 날짜가 바뀌면 자동 리셋. watcher가 코드 리뷰 실행 전 카운터를 확인하고, 5회 초과 시 스킵 + notification으로 "일일 한도 도달" 알림.

### 4.4 프롬프트 (신규 3개)

```
scripts/prompts/
├── code_critic.txt         # 코드 변경 Critic 리뷰
├── code_cross_review.txt   # 코드 변경 Cross 리뷰
└── code_aggregation.txt    # 코드 변경 최종 판정
```

**code_critic.txt** 핵심 구조:
```
입력: git diff + docs/code_review/code-review.md (기존 이슈 참조)

체크리스트:
  Critical: Non-atomic 파일 쓰기, Shell injection, 스레드 종료 미처리
  High: asyncio Lock 누락, 캐시 무한 증가, 스레드 안전성, Silent fallback
  Medium: 매직넘버, Dead code, af.spec 누락
  
AF 특화:
  - frozen build (dist/af/af.exe) 호환성
  - Windows/Unix 경로 처리
  - 멀티 프로바이더 CLI 환경

출력: §3.1 보고서의 "검증자 A (Critic)" 섹션 형식
```

**code_cross_review.txt** 핵심 구조:
```
입력: 변경 파일 경로 (자율 탐색 — codex/gemini는 직접 읽음)

포커스:
  - 변경 코드의 호출자/피호출자 영향 분석
  - 기존 code-review.md의 이슈와 비교
  - 테스트 커버리지 확인
  - 대체 구현 방안 제시

출력: §3.1 보고서의 "검증자 B (Cross)" 섹션 형식
```

### 4.5 변경 파일 목록

| 파일 | 변경 | 규모 |
|------|------|------|
| `core/review_report.py` | **신규** | ~120줄 |
| `core/design_review_utils.py` | 수정 — CODE 패턴 + 큐 디렉토리 분리 + 세션 카운터 + 배치 통합 | ~60줄 |
| `scripts/design_review_watcher.py` | 수정 — review_type 분기, ReviewReport 사용, 듀얼 큐 폴링, 배치 처리 | ~120줄 |
| `scripts/design_review_trigger.py` | 수정 — 코드 파일 감지 분기 | ~20줄 |
| `.claude/settings.local.json` | 수정 — hook에 코드 트리거 조건 추가 | ~5줄 |
| `scripts/prompts/code_critic.txt` | **신규** | ~80줄 |
| `scripts/prompts/code_cross_review.txt` | **신규** | ~80줄 |
| `scripts/prompts/code_aggregation.txt` | **신규** | ~70줄 |

---

## 5. Part B: 런타임 문서 교차검증 QA

### 5.1 흐름 (8단계)

```
단계 1: 문서 생성 (기존)
━━━━━━━━━━━━━━━━━━━━━━
  ProjectPipeline.prepare()
    → work_item_generator.generate_work_items()
      → feature-plan.md
      → feature-spec.md
      → implementation-design.md
      → implementation-tasks.md

단계 2: 구조 검증 (신규 연결 — prepare()에 통합 필요)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ※ run_structural_gate()는 정의되어있으나 prepare()에서 미호출 상태.
     이 단계에서 prepare() 내부에 호출을 연결한다.

  prepare() 내부에서:
    gate_result = self.run_structural_gate(artifact, artifact_type)
    if gate_result.errors:
        → 단계 1 재생성 (기존 RubricCompiler 평가)
    gate_scores = gate_result.dimension_scores

단계 3: 문서 교차검증 (NEW)
━━━━━━━━━━━━━━━━━━━━━━━━━━
  레벨별 분기:
    starter    → 스킵 (구조 검증만)
    dynamic    → Critic 1회 (단일 프로바이더)
    enterprise → Critic + Cross + Judge (풀 교차검증)

  CLI 2개 이상:
  ┌─ Critic (프로바이더 A) ─────────────────────
  │  doc_critic.txt + 4개 문서 전체
  │  개별 문서 품질 + 문서 간 정합성 검증
  │  → ReviewerResult(role="critic")
  │
  └─ Cross (프로바이더 B) ──────────────────────
     doc_cross_review.txt + 4개 문서 + 프로젝트 컨텍스트
     구현자 관점 리뷰 + 대체 방안
     → ReviewerResult(role="cross")

  CLI 1개:
  └─ Critic만 실행

단계 4: 판정 (NEW)
━━━━━━━━━━━━━━━━━
  Judge가 Critic + Cross 통합 판정
    → BLOCK: 문서 재생성 필요 (단계 5로)
    → WARN: 경고와 함께 진행 (단계 7로)
    → PASS: 통과 (단계 7로)

단계 5: 문서 수정 (NEW, BLOCK/WARN 시)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  제어 흐름 (prepare() 내부 의사코드):

    review_session = DocumentReviewSession(workspace, slug, level)
    for round_num in range(1, max_rounds + 1):
        # 교차검증 실행 (단계 3-4)
        report = review_session.run_review(documents, round_num)

        if report.judge.verdict == "PASS":
            break
        if report.judge.verdict == "WARN" or round_num == max_rounds:
            # WARN이거나 마지막 라운드 → 경고와 함께 진행
            break

        # BLOCK → 문서 수정 후 재시도
        for doc_type, instructions in report.judge.fix_instructions.items():
            documents[doc_type] = work_item_generator._refine_document(
                original=documents[doc_type],
                feedback=instructions,
                project_brief=project_brief,
            )

    호출자: ProjectPipeline.prepare() → 교차검증 블록
    수정자: work_item_generator._refine_document()
    재진입: 위 for 루프의 다음 iteration으로 자동 재진입

  ※ _refine_document()는 원천 데이터(project_brief)도 함께 참조하여
     문서 수정 후에도 원천↔파생물 정합성을 유지한다.
  ※ 교차검증에 의한 문서 수정은 ApprovalGate.initialize() 이전에 완료된다.
     따라서 ApprovalGate 해시는 교차검증 완료 후의 최종 문서 기준으로 계산된다.

단계 6: 재검증 (단계 5의 for 루프에 포함)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  수정된 문서만 교차검증 재실행
    → 최대 2라운드 (무한 루프 방지)
    → 2라운드 후에도 BLOCK → WARN으로 강제 전환 + 경고 기록

단계 7: 보고서 저장 (NEW)
━━━━━━━━━━━━━━━━━━━━━━━━
  ReviewReport.save()
    → docs/work-items/{slug}/verification-report.md (라운드별 누적 append)
    → 검증자별 의견 + 판정자 결론 + 수정 이력 전부 기록
    → 각 라운드는 "## Round {N}" 섹션으로 구분

단계 8: 파이프라인 품질 + 승인 게이트 (기존 강화)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  AggregatedVerdict.evaluate()
    → 기존 5차원 + cross_verification 차원 추가
    → 6차원 가중 모델

  ApprovalGate.initialize()
    → verification-report.md 요약 첨부
    → 교차검증 PASS 문서는 승인 부담 감소
```

### 5.2 문서 간 정합성 검증 (핵심 차별점)

런타임 문서는 4개가 **한 세트**이므로, 개별 품질 + 문서 간 교차 일관성을 검증한다.

```python
CROSS_CONSISTENCY_CHECKS = [
    # feature-plan ↔ feature-spec
    "feature-plan의 '위험 사항'이 feature-spec의 '비기능 요구사항'에 대응책으로 존재하는가?",
    "feature-plan의 '이해관계자'가 feature-spec의 '사용자 시나리오'에 반영되었는가?",
    
    # feature-spec ↔ implementation-tasks
    "feature-spec의 '수락 기준' 각각이 implementation-tasks에 검증 항목으로 존재하는가?",
    "feature-spec에서 정의한 모든 API 엔드포인트가 implementation-tasks에 구현 항목으로 있는가?",
    
    # feature-spec ↔ implementation-design
    "implementation-design의 '데이터 모델'이 feature-spec의 '사용자 시나리오'를 지원하는가?",
    "implementation-design의 기술 스택이 feature-plan의 제약 조건과 일치하는가?",
    
    # implementation-design ↔ implementation-tasks
    "implementation-design에서 정의한 모듈 각각이 implementation-tasks에 작업으로 분해되었는가?",
    "implementation-tasks의 '전제조건'이 implementation-design의 의존성 순서와 일치하는가?",
    
    # 전체
    "4개 문서에서 동일 개념을 지칭하는 용어/명칭이 일관적인가?",
]
```

### 5.3 프롬프트 (신규 3개)

```
scripts/prompts/
├── doc_critic.txt           # 런타임 문서 Critic 리뷰
├── doc_cross_review.txt     # 런타임 문서 Cross 리뷰
└── doc_aggregation.txt      # 런타임 문서 최종 판정
```

**doc_critic.txt** 핵심 구조:
```
입력: feature-plan.md + feature-spec.md + implementation-design.md + implementation-tasks.md

검증 항목:
  [개별 문서 품질]
  - 각 문서가 자체적으로 완전한가? (필수 섹션, 구체성, 모호함 없음)
  - 수락 기준이 측정 가능한가? ("빠르게" → ❌, "200ms 이내" → ✅)
  - 구현 작업이 검증 가능한가? (완료 정의가 명확한가?)

  [문서 간 정합성] ← 핵심
  - CROSS_CONSISTENCY_CHECKS 9개 항목 전부 검증
  - 용어 불일치, 누락된 매핑, 모순되는 제약 조건 발견

  [실현 가능성]
  - 기술 스택/라이브러리가 실재하는가?
  - 예상 작업량이 현실적인가?
  - 외부 의존성 리스크가 고려되었는가?

출력: §3.1 보고서의 "검증자 A (Critic)" 섹션 형식
  + 문서 간 정합성 매트릭스 테이블
```

**doc_cross_review.txt** 핵심 구조:
```
입력: 4개 문서 + planning/project_brief.json + planning/research_evidence.json

포커스:
  - 구현자 관점: "이 문서대로 구현할 수 있는가?"
  - 연구 증거와의 괴리: project_brief의 증거가 문서에 반영되었는가?
  - 누락된 실패 시나리오: 부분 실패, 동시 접근, 롤백 경로
  - 대체 방안: 더 간단한 설계 가능성

출력: §3.1 보고서의 "검증자 B (Cross)" 섹션 형식
```

### 5.4 pipeline_quality.py 확장

> **참고**: `AggregatedVerdict.evaluate()`는 현재 정의만 되어있고 어디에서도 호출되지 않는다 (교차검증 확인 완료). 따라서 시그니처 변경은 하위호환성 문제 없이 안전하다.

```python
# 기존 5차원 → 6차원
_WEIGHTS = {
    "evidence_quality":      0.12,   # 0.15 → 0.12
    "semantic_quality":      0.22,   # 0.25 → 0.22
    "structural_quality":    0.18,   # 0.20 → 0.18
    "execution_quality":     0.22,   # 0.25 → 0.22
    "grounding_ratio":       0.12,   # 0.15 → 0.12
    "cross_verification":    0.14,   # NEW
}

# evaluate() 시그니처 변경
def evaluate(
    self,
    evidence_v: dict,
    critique_v: dict,
    gate_v: dict,
    qa_v: dict | None = None,
    rewrite_v: dict | None = None,
    cross_v: dict | None = None,      # ← NEW: 교차검증 결과
) -> VerdictResult:
    # ... 기존 5차원 계산 ...
    
    # 6번째 차원: 교차검증 점수
    if cross_v:
        cv_confidence = cross_v.get("confidence", 0.0)
        cv_verdict = cross_v.get("verdict", "")
        # verdict 보정: PASS=1.0, WARN=0.6, BLOCK=0.2
        cv_score = {"PASS": 1.0, "WARN": 0.6, "BLOCK": 0.2}.get(cv_verdict, 0.0)
        dimensions["cross_verification"] = cv_score * 0.6 + cv_confidence * 0.4
    else:
        # 교차검증 미실행 시 (starter 레벨): 가중치 재분배
        dimensions["cross_verification"] = 0.0
        # cross_verification 가중치 0.14를 나머지 5개에 비례 배분

# VerdictResult 확장
@dataclass
class VerdictResult:
    # ... 기존 필드 ...
    cross_review_verdict: str = ""          # "PASS" | "WARN" | "BLOCK"
    cross_review_confidence: float = 0.0    # 0.0~1.0
    cross_review_report_path: str = ""      # verification-report.md 경로
```

### 5.5 변경 파일 목록

| 파일 | 변경 | 규모 |
|------|------|------|
| `core/review_report.py` | **신규** (Part A와 공유) + `DocumentReviewSession` 클래스 | ~180줄 |
| `core/project_pipeline.py` | 수정 — `prepare()`에 구조검증 연결 + 교차검증 단계 삽입 | ~80줄 |
| `core/work_item_generator.py` | 수정 — `_refine_document(original, feedback, project_brief)` 추가 | ~40줄 |
| `core/pipeline_quality.py` | 수정 — 6차원 가중, evaluate() 시그니처 변경, VerdictResult 확장 | ~35줄 |
| `scripts/prompts/doc_critic.txt` | **신규** | ~100줄 |
| `scripts/prompts/doc_cross_review.txt` | **신규** | ~90줄 |
| `scripts/prompts/doc_aggregation.txt` | **신규** | ~80줄 |

---

## 6. Part C: 문서 QA 에이전트

### 6.1 런타임 에이전트 (af.exe 내장)

기존 에이전트 시스템에 `doc-qa` 역할을 추가한다.

**위치**: `skills/evaluator/doc_qa/skill.py` (신규)

```python
"""
skills/evaluator/doc_qa/skill.py
=================================
문서 품질 QA 스킬 — 프로젝트 파이프라인에서 자동 호출.

역할:
  1. work-item 문서 4개의 개별 품질 검증
  2. 문서 간 교차 일관성 검증 (9개 체크)
  3. 연구 증거와의 정합성 검증
  4. verification-report.md 생성

호출:
  - ProjectPipeline.prepare() → needs_doc_qa() 판정 후 자동
  - CLI: af eval doc-qa --workspace <path> --slug <work-item-slug>
"""

@skill_metadata(SkillMetadata(
    skill_id="doc-qa",
    name="doc-qa",
    category=SkillCategory.EVAL,
    skill_type=SkillType.TOOL,
    description="Work-item 문서 세트의 품질 + 정합성 QA",
    tags=["qa", "document", "cross-verification", "pipeline"],
))
class DocQASkill:
    def execute(self, context: dict) -> dict:
        """
        context:
          workspace: str
          slug: str
          level: "starter" | "dynamic" | "enterprise"
          documents: dict[str, str]  # {doc_type: content}
          project_brief: dict
          research_evidence: dict

        returns:
          verdict: "PASS" | "WARN" | "BLOCK"
          report_path: str
          findings: list[dict]
          confidence: float
        """
        ...
```

### 6.2 Claude Code 에이전트 (개발환경)

**위치**: `.claude/agents/af-doc-qa.md` (신규)

```markdown
---
name: af-doc-qa
description: "Work-item 문서 세트의 품질 + 문서 간 정합성을 교차검증하는 QA 에이전트."
tools:
  - Read
  - Glob
  - Grep
  - Bash
---

# 역할: 문서 QA 에이전트

Work-item 문서 4개(feature-plan, feature-spec, implementation-design,
implementation-tasks)의 **개별 품질** + **문서 간 정합성**을 검증합니다.

## 실행 절차

### Step 1: 문서 세트 수집

slug는 **사용자가 지정**하거나, 가장 최근 수정된 디렉토리를 사용한다:

```bash
# 사용자 지정 slug가 없으면 최근 수정 기준 선택
SLUG=${1:-$(ls -t docs/work-items/ | grep -v _template | head -1)}
echo "[doc-qa] target slug: $SLUG"
ls docs/work-items/$SLUG/
```

4개 문서를 모두 읽는다:
- feature-plan.md
- feature-spec.md
- implementation-design.md
- implementation-tasks.md

존재하면 함께 읽는다:
- planning/project_brief.json
- planning/research_evidence.json

### Step 2: 개별 문서 품질 검증

각 문서에 대해:

**feature-plan.md**
- [ ] 목표가 구체적이고 측정 가능한가?
- [ ] 위험 사항이 3개 이상 식별되었는가?
- [ ] 이해관계자가 명확한가?
- [ ] 연구 증거가 참조되었는가?

**feature-spec.md**
- [ ] 수락 기준이 **모두** 측정 가능한가? ("빠르게" → ❌)
- [ ] 사용자 시나리오가 정상/예외 경로를 포함하는가?
- [ ] API 인터페이스가 입력/출력/에러를 명시하는가?

**implementation-design.md**
- [ ] 데이터 모델이 구체적인가? (필드명, 타입, 제약 조건)
- [ ] 모듈 간 의존성 방향이 명확한가?
- [ ] 기술 선택의 근거가 있는가?

**implementation-tasks.md**
- [ ] 각 작업의 완료 정의가 검증 가능한가?
- [ ] 전제조건과 순서가 논리적인가?
- [ ] 예상 작업량이 현실적인가?

### Step 3: 문서 간 정합성 검증 (핵심)

**9개 교차 체크:**

| # | 원본 | 대상 | 체크 |
|---|------|------|------|
| 1 | plan.위험사항 | spec.비기능요구사항 | 대응책 존재? |
| 2 | plan.이해관계자 | spec.사용자시나리오 | 반영됨? |
| 3 | spec.수락기준 | tasks.검증항목 | 1:1 매핑? |
| 4 | spec.API엔드포인트 | tasks.구현항목 | 누락 없음? |
| 5 | spec.사용자시나리오 | design.데이터모델 | 지원 가능? |
| 6 | plan.제약조건 | design.기술스택 | 일치? |
| 7 | design.모듈 | tasks.작업 | 분해됨? |
| 8 | design.의존성순서 | tasks.전제조건 | 일치? |
| 9 | 전체 | 전체 | 용어 일관성? |

누락/불일치 발견 시 구체적으로 "plan §3에서 'Redis 캐시'를 위험으로 지적했으나,
design §2의 기술 스택에 Redis 대응책이 없음" 형태로 보고한다.

### Step 4: Codex 교차검증 (복수 프로바이더 시)

```bash
PROVIDERS=$(claude --version 2>/dev/null && echo claude; codex --version 2>/dev/null && echo codex; gemini --version 2>/dev/null && echo gemini)
```

프로바이더가 2개 이상이면 codex에 교차 리뷰 요청:

```bash
codex exec -s danger-full-access -o /tmp/doc-qa-cross.txt "
이 프로젝트의 docs/work-items/{slug}/ 에 4개 문서가 있다.
1. 4개 문서를 모두 읽어라.
2. 문서 간 정합성을 검증하라:
   - feature-spec의 수락 기준이 implementation-tasks에 빠짐없이 매핑되는가?
   - implementation-design의 기술 선택이 feature-plan의 제약 조건과 일치하는가?
   - 4개 문서에서 같은 개념을 다른 이름으로 부르는 곳은?
3. 각 발견에 심각도(Critical/High/Medium/Low), 문서명:섹션, 인용을 포함하라.
" 2>&1
```

### Step 5: 보고서 생성

아래 형식으로 verification-report.md를 생성한다:

```
# Verification Report: {slug}

> Date: {YYYY-MM-DD HH:MM}
> Providers: critic={name}, cross={name}
> Documents: 4/4

---

## 검증자 A (Critic): {provider}
### 개별 문서 품질
| 문서 | 점수 | 주요 이슈 |
|------|------|----------|
| feature-plan | 85/100 | 위험 사항 2개만 식별 |
| feature-spec | 72/100 | 수락 기준 3개 측정 불가 |
| impl-design | 90/100 | 양호 |
| impl-tasks | 68/100 | 완료 정의 모호 |

### 문서 간 정합성
| # | 체크 | 결과 | 상세 |
|---|------|------|------|
| 1 | plan.위험→spec.비기능 | ❌ FAIL | "보안" 위험에 대응 없음 |
| 3 | spec.수락기준→tasks.검증 | ⚠️ PARTIAL | 5개 중 3개만 매핑 |
| 9 | 용어 일관성 | ❌ FAIL | "사용자"/"유저"/"user" 혼용 |

---

## 검증자 B (Cross): {provider}
...

---

## 최종 판정 (Judge): {provider}
### 종합: WARN
| # | 제목 | 심각도 | 판정 | Critic | Cross |
...

### 수정 지시
1. [필수] feature-spec 수락 기준 3개를 측정 가능하게 수정
2. [필수] spec↔tasks 매핑 누락 2개 보완
3. [권장] 용어 통일 ("사용자"로 통일)
```

### Step 6: 결과 반환

- PASS: "문서 QA 통과 — verification-report.md 참조"
- WARN: ACCEPT 항목 목록 + 수정 제안 요약
- BLOCK: 즉시 수정 필요 항목 강조
```

### 6.3 에이전트 호출 시점

| 시점 | 호출 방식 | 에이전트 |
|------|----------|---------|
| 런타임 `prepare()` | 자동 — `needs_doc_qa()` 판정 | `skills/evaluator/doc_qa/` |
| Claude Code 수동 | 사용자가 에이전트 호출 | `.claude/agents/af-doc-qa.md` |
| Claude Code 자동 | PostToolUse hook (work-items/*.md 수정 시) | design_review_watcher 경유 |

---

## 7. 통합 아키텍처

### 7.1 전체 그림

```
┌──────────────────────────────────────────────────────────────┐
│                    Unified Review Engine                       │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Critic      │  │  Cross      │  │  Judge              │  │
│  │  (독립 비평)  │  │  (교차 검증) │  │  (최종 판정)         │  │
│  │  프로바이더 A │  │  프로바이더 B │  │  우선순위 선택       │  │
│  └──────┬───────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                  │                     │             │
│         └──────────────────┼─────────────────────┘             │
│                            ↓                                   │
│                    ┌──────────────┐                            │
│                    │ ReviewReport │ ← 통합 보고서 생성          │
│                    │ (§3.1 형식)  │                            │
│                    └──────┬───────┘                            │
│                           │                                    │
│         ┌─────────────────┼─────────────────┐                 │
│         ↓                 ↓                 ↓                  │
│  docs/reviews/    work-items/{slug}/   notification           │
│  *-review.md     verification-report.md  → Claude 대화        │
│  (설계/코드)      (런타임 문서)           (피드백 주입)         │
└──────────────────────────────────────────────────────────────┘

호출자:
  ① design_review_watcher  → review_type="design"  (기존, pending/design/ 폴링)
  ② design_review_watcher  → review_type="code"    (확장, pending/code/ 폴링)
     ※ 단일 watcher가 양쪽 큐를 교대 폴링. 별도 프로세스 아님.
  ③ ProjectPipeline        → DocumentReviewSession (NEW, 별도 클래스)
  ④ af-doc-qa 에이전트     → DocumentReviewSession (NEW)
```

### 7.2 프롬프트 체계 (최종)

```
scripts/prompts/
├── design_critic.txt          (기존 — 설계 문서)
├── design_cross_review.txt    (기존)
├── design_aggregation.txt     (기존)
├── code_critic.txt            (NEW — 코드 변경)
├── code_cross_review.txt      (NEW)
├── code_aggregation.txt       (NEW)
├── doc_critic.txt             (NEW — 런타임 문서 세트)
├── doc_cross_review.txt       (NEW)
└── doc_aggregation.txt        (NEW)
```

### 7.3 레벨별 적용 범위

| 레벨 | 설계 리뷰 | 코드 리뷰 | 문서 QA |
|------|----------|----------|---------|
| **starter** | — | — | 구조 검증만 |
| **dynamic** | Critic 1회 | Critic 1회 | Critic 1회 |
| **enterprise** | Critic+Cross+Judge | Critic+Cross+Judge | Critic+Cross+Judge (2라운드) |

---

## 8. 구현 순서

| 순서 | 작업 | 의존성 | 예상 규모 |
|:---:|------|--------|----------|
| **1** | `core/review_report.py` — 통합 보고서 모듈 + `DocumentReviewSession` 클래스 | 없음 | ~180줄 |
| **2** | `scripts/prompts/doc_*.txt` 3개 — 문서 QA 프롬프트 | 없음 | ~270줄 |
| **3** | `scripts/prompts/code_*.txt` 3개 — 코드 리뷰 프롬프트 | 없음 | ~230줄 |
| **4** | `.claude/agents/af-doc-qa.md` — Claude Code 에이전트 | 없음 | ~200줄 |
| **5** | `design_review_watcher.py` 리팩토링 — ReviewReport 사용 + 듀얼 큐 폴링 + 배치 처리 | 1 | ~120줄 수정 |
| **6** | `design_review_utils.py` 확장 — CODE 패턴 + 큐 분리 + 세션 카운터 | 없음 | ~60줄 |
| **7** | `design_review_trigger.py` 확장 — 코드 파일 감지 | 6 | ~20줄 |
| **8** | `core/project_pipeline.py` — `prepare()`에 구조검증 연결 + 교차검증 삽입 | 1 | ~80줄 |
| **9** | `core/pipeline_quality.py` — 6차원 가중 + evaluate() 시그니처 + VerdictResult 확장 | 없음 | ~35줄 |
| **10** | `core/work_item_generator.py` — `_refine_document(original, feedback, project_brief)` 추가 | 없음 | ~40줄 |
| **11** | `skills/evaluator/doc_qa/skill.py` — 런타임 스킬 | 1 | ~80줄 |
| **12** | `.claude/settings.local.json` — hook 업데이트 | 7 | ~5줄 |
| **13** | `af.spec` — hiddenimports 추가 | 11 | ~3줄 |
| **14** | `Master_Blueprint.md` — §3, §12 업데이트 | 전체 | — |

> **Rev.1 변경**: `run_document_review()`를 `CrossVerificationLoop`에 추가하는 대신, `DocumentReviewSession` 별도 클래스를 `core/review_report.py`에 배치. CrossVerificationLoop은 런타임 코드 실행 검증 전용으로 유지.

---

## 9. 검증 방법

```bash
# 1. 코드 교차검증 테스트 (개발환경)
#    core/*.py 파일 편집 후 15초 대기 → 자동 리뷰 실행 확인
#    docs/reviews/ 에 code-review.md 생성 확인
#    notification 텍스트 확인

# 2. 문서 QA 테스트 (런타임)
af -p test_doc_qa -t "간단한 TODO 앱 구현" --mode fsa --pipeline project
#    docs/work-items/{slug}/verification-report.md 생성 확인
#    검증자별 의견 분리 확인
#    문서 간 정합성 매트릭스 확인

# 3. 레벨별 분기 테스트
#    starter: 교차검증 스킵 확인
#    dynamic: Critic 1회만 실행 확인
#    enterprise: 풀 교차검증 + 2라운드 확인

# 4. 보고서 형식 검증
#    §3.1 형식 준수 확인
#    Critic/Cross/Judge 섹션 분리 확인
#    통합 테이블 + 수정 지시 존재 확인

# 5. 기존 기능 회귀 테스트
python -m pytest tests/ -v
#    기존 테스트 전체 통과 확인
```

---

## 10. 변경 파일 총 목록

| 파일 | 상태 | 규모 |
|------|------|------|
| `core/review_report.py` | **신규** — ReviewReport + DocumentReviewSession | ~180줄 |
| `skills/evaluator/doc_qa/skill.py` | **신규** | ~80줄 |
| `.claude/agents/af-doc-qa.md` | **신규** | ~200줄 |
| `scripts/prompts/code_critic.txt` | **신규** | ~80줄 |
| `scripts/prompts/code_cross_review.txt` | **신규** | ~80줄 |
| `scripts/prompts/code_aggregation.txt` | **신규** | ~70줄 |
| `scripts/prompts/doc_critic.txt` | **신규** | ~100줄 |
| `scripts/prompts/doc_cross_review.txt` | **신규** | ~90줄 |
| `scripts/prompts/doc_aggregation.txt` | **신규** | ~80줄 |
| `scripts/design_review_watcher.py` | 수정 — 듀얼 큐 폴링 + 배치 처리 | ~120줄 |
| `scripts/design_review_trigger.py` | 수정 | ~20줄 |
| `core/design_review_utils.py` | 수정 — 큐 분리 + 세션 카운터 | ~60줄 |
| `core/project_pipeline.py` | 수정 — 구조검증 연결 + 교차검증 삽입 | ~80줄 |
| `core/pipeline_quality.py` | 수정 — 6차원 + evaluate() 시그니처 | ~35줄 |
| `core/work_item_generator.py` | 수정 — `_refine_document()` | ~40줄 |
| `.claude/settings.local.json` | 수정 | ~5줄 |
| `af.spec` | 수정 | ~3줄 |
| `Master_Blueprint.md` | 수정 | — |
| **합계** | 신규 9 + 수정 9 | ~1,403줄 |

---

## 11. 교차검증 결과 (Rev.1 근거)

본 설계서는 af-critic + codex af-cross-review 교차검증을 거쳐 Rev.1로 개정되었다.

### 반영된 피드백 (ACCEPT 11개)

| # | 항목 | 심각도 | 출처 | 반영 위치 |
|---|------|--------|------|----------|
| 1 | prepare()에 run_structural_gate() 미연결 | High | Cross | §5.1 단계 2 |
| 2 | evaluate() 시그니처 — cross_v 인자 누락 | High | Critic | §5.4 |
| 3 | _refine_document() 호출 제어 흐름 미완 | High | 양쪽 | §5.1 단계 5 의사코드 |
| 4 | watcher 단일/분리 결정 미정 | High | Critic | §4.1 큐 디렉토리 분리 |
| 5 | 문서 수정 후 ApprovalGate 정합성 | High | Cross | §5.1 단계 5 주석 |
| 6 | 세션 카운터 저장 방법 미정 | Medium | Critic | §4.3 |
| 7 | verification-report.md 덮어쓰기 이력 파괴 | Medium | Critic | §3.2 → append 방식 |
| 8 | skill_metadata 데코레이터 시그니처 | Medium | Cross | §6.1 |
| 9 | 큐 포맷 변경 규모 과소 산정 | Medium | Cross | §4.5, §10 규모 재산정 |
| 10 | af-doc-qa slug 자동 탐지 오류 | Medium | Critic | §6.2 Step 1 |
| 11 | run_document_review() 책임 위반 | Medium | Critic | §8 DocumentReviewSession 분리 |

### 기각된 피드백 (REJECT 2개)

| # | 항목 | 이유 |
|---|------|------|
| 12 | pipeline_quality 호출자 영향 | evaluate()는 정의만 되어있고 호출 코드 없음 (검증 완료) |
| 13 | docs/reviews/ 소비자 영향 | 프로그래밍적 파싱 코드 없음, 사람용 문서 |
