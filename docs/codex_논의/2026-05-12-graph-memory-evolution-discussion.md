# 메모리 자기진화 + 코드 그래프 도입 논의

> 날짜: 2026-05-12
> 워크스페이스: `D:\hoonProJect\worktrees\agent-factory`
> 세션 ID: `5e1c20a6-2b6a-4eb6-8c2e-e70e5adf2fe4`
> 관련 문서: `docs/codex_논의/2026-05-12-graphifyy-apply.md` (graphify 진단 raw log)
> 사용자 메모리: `project_saas_strategy_position.md` (Manus 패턴 opt-in 흡수 정책)

---

## 0. 논의 흐름 요약

1. 사용자: 채팅 sync 메커니즘 질문 → 답: sync ≠ 자동 컨텍스트 주입 (memory/*.md만 sync, transcript는 별개)
2. 사용자: 단기기억/FTS/자동회수 키워드 → "헤르메스 에이전트와 차이" 질문
3. 사용자: 자기진화 5단계 루프 진단 던짐 → AF 매핑 + 의견 요청
4. Claude: 진단 검증 — 방향 맞음, 강도 과장. AF는 코드 있는데 wire-up 미완.
5. 사용자: "Graphify도 적용되어 있지 않나?" → 진단: 4중 차단
6. 사용자: Git Nexus 소개 → 비교/충돌/단계 요청
7. 사용자: "MCP를 사용하는 게 좋을까?" → 회의 분석
8. 사용자: "대형 프로젝트면 이거 있어야" → AF 규모 측정 후 그래프 필요성 정당화

---

## 1. 자기 진화 5단계 루프 (사용자 진단)

```
1. Act → 2. Observe → 3. Score → 4. Consolidate → 5. Retrieve at decision time
```

- 단계 한 곳이라도 끊기면 메모리 = 단순 로그 저장소
- AF는 단계 3·4·5에서 끊김 (사용자 주장)

### 1-1. AF 매핑 검증 결과 (코드 실측)

| 단계 | 사용자 진단 | Claude 검증 |
|---|---|---|
| **5. Retrieve** | "runner hook으로만, intake에 안 들어감" | **부분 정확** — `core/control/intake.py:40 NormalizedRequest.memory_context: dict` 자리는 있음. 채워서 prompt에 prepend하는 흐름이 빠짐 |
| **3. Score** | "Quality Plane 정의됐지만 live path 미연결" | **부분 정확** — `core/ise_*.py` 5개 모듈 + `strategy_ledger.record_episode_outcome()` 존재. `agent_runner` 결정 경로에서 호출 X |
| **4. Consolidate** | "raw 노드만 쌓고 있다" | **틀림** — `episode_extractor`/`graph_builder`/`knowledge_forger`/`strategy_ledger`/`decay` 6개 모듈 분리 설계 존재. MemOS L1~L3 매핑 의도적 |

**핵심 정정**: AF는 "메모리가 없다"가 아니라 "있는데 안 돈다". wire-up 갭이 핵심 (8개 모듈, 213 파일 사이의 연결 단선).

### 1-2. AF에 이미 있는 부분 진화 자산

- `skills/` + `data/skill-usage.jsonl` (FSA 평가 → 진화)
- `docs/reviews/` (cross-review verdict = 자연적 점수 신호)
- `MEMORY.md` 인덱스 (fast loop 자동 회수, 200줄 truncate)
- `core/memory_system/graph_*` (L1~L3 모듈)
- `core/ise_*` (Quality Plane 5종)

### 1-3. 권장 단계 (재정렬)

| Step | 내용 | LOC | 의존 |
|---|---|---|---|
| **0** | 두 그래프 endpoint 통합 (`_collect_memory_context`) | 30 | 없음 |
| **1** | Intake 회상 wire-up — memory_context를 prompt prepend | 50 | Step 0 |
| **2** | 점수 라벨 자동 연결 (cross-review verdict → episode outcome) | 60 | Step 1 |
| **3** | Quality Plane 결정 시점 주입 (ISE stall signals) | 100 | Step 2 |
| **4** | Crystallization 트리거 (5 episode → strategy_ledger) | 50 | Step 2 |

---

## 2. Graphify 적용 진단

### 2-1. 4중 차단 (확정)

| # | 차단 | 증거 |
|---|---|---|
| 1 | Python 3.14 환경 vs graphifyy `<3.14` 제약 | `python --version` → `3.14.3`; `pyproject.toml` python_constraint `<3.14` |
| 2 | graphify CLI 미설치 | `where graphify` → not found |
| 3 | graphifyy 패키지 미설치 | `import graphifyy` → ModuleNotFoundError |
| 4 | 그래프 빌드 0회 | `*.kg` 0개, `runtime/graphify/` 부재, `graphify-out/` 부재 |
| 5 | 통합 자체가 Phase 0 | `docs/features/2026-04-22-graphify-integration.md:4` "Phase 0 사용자 답변 대기 (Q1~Q11)" |

### 2-2. 타임라인

- **2026-04-22**: 통합 설계 문서 작성. Python 3.14 미지원 = blocking 명시.
- **2026-04-23**: skill wrapper 구현 (`skills/graphify/skill.py`). af-critic 3라운드 + Codex P2~P5 fix.
- **이후 ~3주**: Q1~Q11 답변 없이 표류. `last_test_ok: false`.
- **현재**: skill registry에 `auto_invocable=true` 마킹만, 호출 시 즉시 missing_dependency.

### 2-3. 해결 옵션

| 옵션 | 비용 | 위험 |
|---|---|---|
| A. Python 3.13 격리 | 낮음 (`install-af.ps1 -WithGraphify` 1회) | CLI 호출 방식만 가능 (in-process import X) |
| B. Python 3.14 호환 대체 도구 | 중간 (tree-sitter/pyan/code2flow) | 71.5× 토큰 절감 효과 미보장 |
| C. graphifyy fork + 3.14 패치 | 높음 | upstream divergence 유지보수 |
| D. 보류 | 0 | 효과 0 |

---

## 3. Git Nexus 비교

### 3-1. 3개 도구 매트릭스

| 차원 | Graphify | Git Nexus | AF 현재 |
|---|---|---|---|
| 언어/런타임 | Python `<3.14` | Node.js (npx) | Python 3.14 |
| DB | NetworkX 인메모리 + HTML/JSON | Ladybug 로컬 DB | 룰베이스 grep |
| MCP 네이티브 | 부분 (옵션) | ✅ 직접 | ❌ |
| 분석 단위 | 코드+문서+이미지+영상 | 코드 (함수/import/상속/실행흐름) | 변경 파일 → Tier |
| 도구 수 | 슬래시 6개 | 11개 (Impact/Context/Query/Rename/Detect/Cipher 등) | 1개 (`blast_radius.py`) |
| 인덱스 갱신 | `graphify .` 또는 watch | `git nexus analyze` 30~60초 | 즉시 (grep) |
| **AF 환경 작동성** | ❌ Python 3.14 차단 | ✅ 즉시 (Node v24.13.1 확인) | ✅ 동작 중 |

### 3-2. 충돌 영역 (코드 검증)

`blast_radius.py` 호출처 (review-gate 핵심 의존성):
- `scripts/review_gate.py`
- `scripts/hook_runner.py`
- `scripts/enqueue_agent_review.py`
- `tests/test_review_gate_phase0.py`
- `tests/test_phase1_blast_tier_invariant.py` (Tier 분류 invariant)

직접 충돌 3건:
1. `scripts/blast_radius.py` ↔ Git Nexus Impact (같은 일, 후자 더 정밀)
2. `skills/graphify/` ↔ Git Nexus (동일 카테고리, 역할 분리 또는 폐기)
3. `core/hooks/lsp_check.py` ↔ Git Nexus Cipher (영역 다름, 충돌 아님)

보완 영역:
- `core/memory_system/graph_*` (동적 episode) + Git Nexus (정적 코드) = 시너지

---

## 4. MCP 회의 (정직한 평가)

### 4-1. 한 줄 진단

MCP는 LLM 자율 호출 모델, AF는 명시 게이트 모델. 두 패러다임이 충돌.
사용자 정책 "Manus 패턴 opt-in 흡수, default 게이트 강제 유지"에 따라 MCP는 default-off + opt-in으로만.

### 4-2. MCP 약점 (AF 정책과 충돌)

1. **default 게이트 정면 충돌** — LLM이 사용자 모르게 호출. commit `603dd702` auto-approve BLOCK 5건과 동일 패턴
2. **토큰 비용 통제 역설** — 절감 목적인데 사용자 모르게 매번 트리거 위험
3. **권한 sandbox** — MCP 서버는 별도 프로세스 (hook subprocess 격리 이슈 전례)
4. **회귀 테스트 어려움** — 자율 호출은 pytest mocking 복잡
5. **벤더 락인 역설** — Codex/Gemini는 MCP 미지원 또는 부분. 멀티 프로바이더 전제와 부분 충돌
6. **PC 간 일관성** — MCP 서버는 PC별 별도. AF 메모리 sync 모델과 다른 영역

### 4-3. 대안 매트릭스

| 방식 | 자율도 | 통제 | AF 정책 부합 |
|---|---|---|---|
| A. MCP 풀스택 | 높음 | 낮음 | ❌ default 게이트 위반 |
| B. CLI subprocess + 명시 호출 | 낮음 | 높음 | ✅ |
| C. 하이브리드 (subprocess + Intake prepend) | 중간 | 높음 | ✅ |
| D. MCP 사용자 채널 분리 | 높음 (사용자만) | 높음 (자동흐름) | ✅ |

**권장**: C(자동 흐름) + D(사용자 즉석 채팅) 분리 운영.

---

## 5. 대형 프로젝트 관점 (사용자 보강)

### 5-1. AF 규모 측정 (2026-05-12 03:10 실측)

| 항목 | 수치 |
|---|---|
| `core/*.py` 파일 | **213개** |
| `core/` 총 LOC | **59,376줄** |
| `tests/*.py` 파일 | **153개** |
| Master_Blueprint.md | 845줄 |

→ **대형 프로젝트 임계점 초과**. Blueprint 845줄로 213 파일 의존성 추적 비현실적.

### 5-2. 핵심 정정 (이전 답변 자기 수정)

이전 답변은 두 가지를 한 묶음으로 다룸 — 분리해야 정직.

| 질문 | 답 |
|---|---|
| A. 코드 그래프 자체가 AF에 필요한가? | ✅ 강력 필요 |
| B. MCP 채널로 도입해야 하는가? | ⚠️ 분리 결정 |

사용자가 강조한 건 A. MCP 회의가 그래프 자체 회의로 비친 게 잘못된 인상.

### 5-3. 유지보수에서 그래프가 도와주는 구체 시나리오

#### AF 자체

1. 함수 시그니처 변경 시 caller 식별 (매 PR ~1회)
2. `blast_radius.py` 룰베이스 정확도 ↑
3. 죽은 코드 식별 (incoming edge 0 노드)
4. 영역별 SKILL 라우팅 정확도 ↑ (Tier 2 Phase 3 단계 1 직결)
5. 새 기능 추가 위치 결정

#### AF가 도와주는 사용자 프로젝트 (AI Software Delivery OS 정책)

6. 100k+ LOC 프로젝트 work-item 정확도 ↑
7. 회귀 테스트 영향 범위 자동 선택

### 5-4. 시나리오별 MCP 필요성

| 시나리오 | subprocess + intake prepend로 충분? | MCP 우위 |
|---|---|---|
| 1~4, 6~7 | ✅ 충분 | — |
| 5 (사용자 즉석 채팅) | — | ✅ MCP 우위 |

→ 7개 중 6개가 subprocess로 충분. MCP는 사용자 채팅 채널로만 우위.

---

## 6. 최종 권장 (정리)

### 결정 흐름

```
Step 0 PoC (10~20분, 비용 0)
  → npx git nexus analyze 1회
  → 인덱싱 시간/품질 측정
  → 성공? → Step 1 / 실패? → graphify Python 3.13 회귀

Step 1: subprocess wrapper (~50 LOC, default off)
  → scripts/blast_radius_nexus.py
  → 회귀 테스트 무손상

Step 2: review-gate slow path 통합 (환경변수 opt-in)
  → AF_NEXUS_IMPACT=1일 때만 Impact 호출
  → 1주 운영 후 정확도 측정

Step 3: 자동 흐름 wire-up (intake _collect_memory_context)
  → 측정 결과 만족 → default on 전환 검토
  → 만족 못 함 → opt-in 유지

Step 4 (선택): MCP 사용자 채널 추가
  → 자동 흐름은 그대로 subprocess
  → MCP는 사용자 채팅 즉석 질문용으로만
  → 두 채널 명확히 분리

Step 5 (graphify 결정):
  → 옵션 A: graphify Phase 0 닫고 폐기 (Git Nexus가 흡수)
  → 옵션 B: graphify는 문서+이미지+영상 전담, Git Nexus는 코드 전담
  → 옵션 C: graphify 보류, Git Nexus만 적용
```

### 정책 한 줄 (메모리화 후보)

> **MCP/외부 도구 통합 정책**: AF 자동 흐름은 subprocess + intake prepend (명시 게이트 유지). MCP는 사용자 직접 채팅 채널로만 분리. 두 채널을 같은 도구라도 분리 운영. `default 게이트 강제` 정책의 확장.

---

## 7. 미해결 / 후속 결정 필요

1. **Step 0 PoC 실행 시점** — 즉시 vs 별도 세션
2. **graphify Phase 0 Q1~Q11 처리** — 답변 후 graphify 운명 결정 vs 미답변 폐기
3. **review-gate 회귀 테스트 invariant 갱신 정책** — Git Nexus 신호로 Tier 산출이 바뀌면 `test_phase1_blast_tier_invariant.py` 갱신 기준
4. **MCP namespace 충돌 검증** — Step 4 진입 시 settings.json diff 확인
5. **사용자 프로젝트 PC 간 일관성** — Git Nexus DB는 PC 로컬. 사용자 멀티 PC 운영 시 인덱싱 정책
6. **Codex와 별도 토론 항목** — 이 문서를 Codex에게 전달해 별도 검증 요청 (현재 Codex 한도 도달, 2026-05-13 01:00 KST+ 가능)

---

## 8. 참고 자료

- `memory/project_saas_strategy_position.md` — Manus 패턴 opt-in 흡수 정책
- `memory/project_3tier_cost_reduction_plan.md` — 토큰 절감 플랜
- `memory/project_auto_approve_block_followup.md` — auto-approve BLOCK 5건 흡수 (2026-05-11 v2)
- `memory/feedback_analysis_doc_baseline_must_be_real_code.md` — 분석 문서 baseline은 실제 코드
- `docs/features/2026-04-22-graphify-integration.md` — graphify Phase 0 설계
- `docs/features/2026-04-23-graphify-skill-implementation.md` — graphify skill 구현
- `docs/codex_논의/2026-05-12-graphifyy-apply.md` — graphify 진단 raw log (이번 세션 직전)

---

**작성**: Claude Opus 4.7, 2026-05-12 03:13 KST
**상태**: 논의 보존용, 구현 의사결정 대기
