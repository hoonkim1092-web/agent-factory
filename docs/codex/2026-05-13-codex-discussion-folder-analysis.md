# codex_논의 문서군 심층 분석과 판단

작성일: 2026-05-13
분석 대상: `docs/codex_논의/` 6개 문서
작성 목적: `codex_논의` 문서군의 핵심 주장, 코드 대조 결과, 논리적 판단, 구현 시 효과를 정리한다.

---

## 1. 분석 대상 문서

분석한 문서는 다음 6개다.

| 문서 | 핵심 주제 |
| --- | --- |
| `2026-05-11-pipeline-order-and-astengine-review.md` | 파이프라인 순서 평가, ASTEngine dead code 진단 |
| `2026-05-11-astengine-revival-impact-analysis.md` | ASTEngine을 실제 실행 경로에 연결할 때의 효과 분석 |
| `2026-05-12-graph-memory-evolution-discussion.md` | 메모리 자기진화 루프와 코드 그래프 도입 논의 |
| `2026-05-12-graphifyy-apply.md` | Graphify 적용 실패 원인 raw log |
| `2026-05-12-agent-factory-deep-analysis-and-competitor-comparison.md` | AF 심층 분석, 경쟁사 비교, 시장성 판단 |
| `2026-05-13-af_provider_neutral_knowledge_layer_design.md` | provider-neutral Knowledge Operating Layer 전체 설계 |

전체 흐름은 다음으로 요약된다.

```text
ASTEngine 복원
  -> 메모리/그래프 wire-up
  -> Graphify/Git Nexus 선택
  -> 경쟁사 대비 포지셔닝
  -> provider-neutral Knowledge Layer 설계
```

---

## 2. 단계별 판단

### 2.1 현재 구조 파악

문서들은 Agent Factory를 단순 코드 생성기가 아니라 다음 흐름을 가진 AI 개발 운영 시스템으로 본다.

```text
기획 -> 명세 -> 설계 -> 구현 -> 검증 -> 리뷰 -> 기억 -> 자가진화
```

이 관점은 타당하다. 실제 코드에도 orchestrator, memory, review gate, provider bridge, skill evolution 구조가 존재한다.

다만 현재 문제는 기능 부재보다 연결 부족이다.

```text
부품이 없다
  보다
부품은 있는데 실행 시점 의사결정으로 충분히 연결되지 않는다
```

이것이 문서군 전체의 가장 중요한 진단이다.

### 2.2 ASTEngine 진단

문서의 ASTEngine 진단은 방향성상 맞다.

검증 결과:

- `core/ast_engine.py`는 일반 에이전트 실행 도구로 노출되어 있지 않다.
- 검색된 production path에서는 `core/review_bundle.py`의 위험 패턴 검사 보조 수단에 가깝다.
- `core/ast_memory_hub.py`에는 `subscribe()`와 `publish()`가 있지만, 실제 `AstMemoryHub.subscribe(...)` consumer는 확인되지 않았다.
- `update_ast_state()`는 여전히 `parsed_ast_data`가 없으면 `"AST_TREE_MOCK"`을 저장한다.

단, 문서 작성 당시의 일부 진단은 현재 코드 기준으로 수정되어 있다.

- `dynamic_orchestrator.py`는 현재 `_git.diff_files_since(_pre_task_sha)`를 통해 실제 변경 파일 경로를 `update_ast_state()`에 넘긴다.
- 따라서 "filepath가 완전히 가짜"라는 진단은 현재 기준으로는 일부 해소됐다.

정확한 현재 판단:

```text
파일 경로 추적은 일부 현실화됐다.
하지만 AST 의미 정보와 consumer 연결은 아직 약하다.
```

### 2.3 메모리 자기진화 진단

문서의 "AF는 메모리가 없는 게 아니라 있는데 안 돈다"는 판단은 설득력 있다.

자가진화 루프는 다음 5단계다.

```text
1. Act
2. Observe
3. Score
4. Consolidate
5. Retrieve at decision time
```

현재 AF에는 다음 기반이 있다.

- `NormalizedRequest.memory_context`
- Codex / Claude / Gemini session bridge
- memory system adapters
- review reports
- StrategyLedger / FSA / ISE 관련 구조

하지만 이 정보가 실행 직전 prompt/context에 안정적으로 주입되는 경로는 아직 완성도가 낮다.

즉 핵심 갭은 저장이 아니라 회상이다.

```text
저장된다
  보다
결정 시점에 올바르게 회상된다
가 중요하다.
```

### 2.4 Graphify와 Git Nexus

Graphify에 대한 진단은 보수적으로 보는 것이 맞다.

확인된 상태:

- wrapper skill은 존재한다.
- `skills/graphify/meta.yaml`에는 `last_test_ok: false`가 남아 있다.
- `python_constraint: ">=3.10,<3.14"` 제약이 있다.
- 현재 AF 환경은 Python 3.14 계열이므로 격리 실행이 필요하다.

따라서 Graphify를 바로 핵심 경로에 넣는 것은 위험하다.

권장 판단:

```text
Graphify는 보류 또는 격리 PoC
Git Nexus 또는 경량 subprocess 기반 그래프 분석을 먼저 적용
```

이유는 단순하다.

- Graphify는 설치/환경 리스크가 있다.
- Git Nexus 또는 경량 그래프 분석은 blast radius, 변경 영향, 파일 관계 추적을 더 빠르게 검증할 수 있다.

### 2.5 Provider-neutral Knowledge Layer

2026-05-13 문서는 문서군 중 가장 중요한 방향성을 제시한다.

핵심 전환은 다음이다.

```text
Claude memory 중심
  -> AF Global Profile 중심

provider-specific memory
  -> provider-neutral ContextPack

수동 Master_Blueprint / code-review
  -> generated snapshot
```

이 방향은 맞다.

하지만 설계 범위가 매우 크므로 하나의 기능으로 구현하면 위험하다. 반드시 좁은 phase로 잘라야 한다.

권장 구현 순서:

1. Local-first `.af/` 저장 구조 정의
2. AF Global Profile 최소 스키마 정의
3. ContextPack 최소 버전 구현
4. AgentRunner 또는 provider 실행 prompt에 ContextPack 주입
5. provider session ingest를 Global Profile로 요약 import
6. LLM Wiki / Git Nexus / Obsidian은 generated view로 후속 연결

---

## 3. 최종 의견

내 판단은 다음과 같다.

```text
AF의 다음 과제는 새 기능을 더 붙이는 것이 아니다.
이미 있는 실행, 리뷰, 메모리, 그래프, provider bridge를
결정 시점 ContextPack으로 묶는 것이다.
```

가장 중요한 제품적 방향은 provider-neutral Knowledge Layer다.

다만 구현 시작점은 거창한 wiki나 graph가 아니라 ContextPack이어야 한다.

```text
ContextPack이 먼저다.
그래프, 위키, Obsidian, generated blueprint는 그 다음이다.
```

이유:

- ContextPack은 Claude / Codex / Gemini 모두에게 바로 주입할 수 있다.
- 구현 범위가 작다.
- 효과 측정이 쉽다.
- provider-neutral memory 전환의 중심축이다.

---

## 4. 권장 우선순위

### 1순위. ContextPack 최소 구현

목표:

```text
AF Global Profile + recent review + open risks + changed files + session summary
-> .af/context/context_pack.md / context_pack.json
-> provider 실행 prompt에 주입
```

효과:

- Claude, Codex, Gemini가 같은 기억을 공유한다.
- 이전 실패와 리뷰 결과가 다음 작업에 반영된다.
- provider별 memory 차이를 줄인다.

### 2순위. AstMemoryHub 의미 정보 보강

현재 `filepath`는 일부 실제 경로로 들어가지만, `parsed_ast_data`는 비어 있다.

권장:

```text
전체 AST tree 저장 금지
함수명 / 클래스명 / 변경 파일 / role / task_id / summary만 저장
```

효과:

- Lilith 판단 품질 상승
- QA 테스트 범위 추정 개선
- session resume 시 "어떤 파일이 왜 바뀌었는가" 복원 가능

### 3순위. AstMemoryHub consumer 1개만 먼저 연결

처음부터 모든 agent에 pub/sub를 붙이면 복잡해진다.

권장:

```text
Lilith prompt builder 또는 AgentSpecializer 중 하나만 consumer로 연결
```

효과:

- dead pub/sub가 실제 의사결정 입력으로 바뀐다.
- stale context 위험을 줄인다.
- 멀티 에이전트 협업 정확도가 올라간다.

### 4순위. Git Nexus 또는 경량 그래프 PoC

Graphify는 의존성 리스크가 있으므로 후순위다.

권장:

```text
Git Nexus / subprocess / blast-radius 보강
-> review-gate slow path에 opt-in
-> 효과 측정 후 확대
```

효과:

- 변경 영향 범위 자동 추적
- 테스트 범위 추천
- 코드 구조 이해 강화

### 5순위. Master_Blueprint / code-review generated 전환

수동 문서를 원본으로 두지 말고 snapshot으로 전환한다.

진짜 source of truth는 다음이어야 한다.

```text
코드 구조 = 실제 코드 + AST/index
변경 이력 = Git + Git Nexus
결정 = ADR / decision-record
검증 = verification-report / test logs
리스크 = review findings / warning registry
메모리 = AF Global Profile + provider session summaries
요약본 = generated Master_Blueprint / generated code-review / LLM Wiki
```

효과:

- 거대 문서 수동 유지 부담 감소
- stale 문서 위험 감소
- AI가 읽는 요약과 실제 코드 상태의 괴리 감소

---

## 5. 예상 효과

### 5.1 기술적 효과

1. 컨텍스트 품질 상승
   - 에이전트가 현재 작업의 변경 파일, 최근 리뷰, 과거 실패를 더 정확히 본다.

2. 반복 실패 감소
   - 실패 패턴이 다음 작업 입력으로 들어가 같은 실수를 줄인다.

3. provider 종속성 감소
   - Claude memory에 의존하지 않고 Codex/Gemini도 동일한 AF 지식을 받는다.

4. 리뷰와 실행의 연결 강화
   - code-review가 별도 문서로 끝나지 않고 다음 실행의 조건으로 들어간다.

5. 세션 연속성 개선
   - resume 시 "무슨 일이 있었는가"를 문서가 아니라 ContextPack에서 복원한다.

### 5.2 운영 효과

1. 문서 유지 비용 감소
   - `Master_Blueprint.md`와 `code-review.md`를 수동 원본이 아니라 자동 요약본으로 전환할 수 있다.

2. 작업 추적성 증가
   - 요구사항, 결정, 코드 변경, 검증, 리뷰, 메모리가 하나의 흐름으로 연결된다.

3. Local-first 제품성 강화
   - 사용자는 Git/Supabase를 몰라도 `.af/` 로컬 구조만으로 시작할 수 있다.

4. 고급 sync는 옵션화
   - Git, Supabase, Obsidian, Cloud Sync는 사용자가 선택할 때만 노출한다.

### 5.3 제품 효과

AF의 차별점은 "자율 에이전트" 그 자체가 아니다.

진짜 차별점은 다음 조합이다.

```text
자가진화
+ 3-Tier 품질 게이트
+ Local-first
+ provider-neutral memory
+ generated knowledge snapshot
```

이 조합은 Manus / Devin / Cursor / Claude Code와 다른 포지션을 만든다.

```text
AI에게 일을 맡기는 도구
  보다
AI 개발팀의 작업 품질을 운영하고 검증하는 시스템
```

이것이 AF의 더 강한 시장 포지션이다.

---

## 6. 결론

`codex_논의` 문서군의 큰 방향은 맞다.

하지만 실행 순서는 조정해야 한다.

최종 권장 순서:

```text
1. ContextPack 최소 구현
2. AF Global Profile 최소 스키마
3. AstMemoryHub metadata 보강
4. consumer 1개 연결
5. Git Nexus / 경량 그래프 PoC
6. generated Master_Blueprint / code-review 전환
7. Obsidian / LLM Wiki / Graphify 확장
```

한 줄 결론:

```text
AF는 기능을 더 붙이기보다,
이미 가진 기능들을 provider-neutral ContextPack으로 묶어
결정 시점에 회상시키는 방향으로 가야 한다.
```
