# ASTEngine 부활 시 효과 분석 (코덱스 논의용)

- 작성일: 2026-05-11
- 작성자: Claude Opus 4.7 세션 (`7691900e-3d22-4a26-a89c-4afeb0b9e804`)
- 선행 문서: `docs/2026-05-11-pipeline-order-and-astengine-review.md` (ASTEngine dead code 진단)
- 본 문서 위치: **분석 결과물**. 설계 결정·수용기준·테스트 계획은 포함하지 않으며, 코덱스 회신 후 `docs/work-items/ast-engine-revival/{feature-plan,spec,tasks,checklist}.md` 4종으로 분리 예정
- 검증 상태: **정적 분석 + 가설적 추론**. 런타임 실측 미수행

---

## 0. 본 문서의 범위와 한계

선행 문서(`pipeline-order-and-astengine-review.md`)에서 ASTEngine 모듈군 3가지 결함을 진단했고, §4.4에서 4건의 권장 조치를 한 줄 스케치로만 제시했음. 본 문서는 그 4건이 *만약 적용된다면* 어떤 효과/위험이 있는지를 가설적으로 분석한 것.

**본 문서가 아닌 것**:
- 설계 결정문 (수정 채택 여부 결정 안 됨)
- 구현 계획 (LOC/테스트 추정은 가설)
- work-item (수용 기준·테스트 케이스·deadline 부재)

**본 문서의 목적**:
- 코덱스에 "ROI가 큰 수정이 무엇인가" 토의 자료 제공
- "이 작업을 work-item으로 승격할 가치가 있는가" 판단 근거

**대상 4건의 수정**:
1. `ast_engine`을 `AgentRunner` 컨트랙트에 도구로 노출
2. `ast_memory_hub.update_ast_state` filepath를 실제 git diff 결과로 교체
3. `subscribe()` 호출처 추가 (pub/sub 활성화)
4. `parsed_ast_data` 실제 파싱 결과 전달

---

## 1. 수정 1 — `ast_engine`을 에이전트 도구로 노출

### 1.1 변경 내용

`AgentRunner` 컨트랙트 주입 단계에 `ast_engine.search/replace/search_file/replace_file`을 도구로 노출. 현재는 `documentation_policy`/`destructive_guard`/`implementation_language` 3종만 주입.

대상 파일:
- `core/agent_runner.py` (컨트랙트 주입 + 도구 노출)
- `core/ast_engine.py` (도구 메타데이터 추가)
- `af.spec` hiddenimports (ast-grep-py 추가 필요 여부 확인)

### 1.2 직접 효과

**(a) 구조적 코드 검색 — regex보다 정확도 1~2 order 높음**
- 예: "모든 `print($A)` 호출 찾기"가 regex `print\(.*\)`처럼 false positive(주석·문자열) 안 맞음
- ast-grep-py는 tree-sitter 기반이라 Python/JS/TS/Go/Rust/Java/C++ 17개 언어에 동일 API
- 에이전트 프롬프트에서 `# Find all calls of foo(x, y) where x is int literal` 같은 의도를 정확히 표현 가능

**(b) 구조적 치환 — 리팩터링 안전성↑**
- 예: `print($A)` → `logger.info($A)` 일괄 치환이 변수명 충돌 없이 수행
- 현재는 에이전트 CLI가 sed/grep으로 치환 → 종종 들여쓰기 깨짐, 문자열 내 매칭 실수

**(c) 다국어 코드 통합 검색**
- `search_dir(pattern, directory, ext=".py")` → 디렉토리 전체 구조 검색 단일 호출
- 현재 에이전트는 `Glob` + 개별 `Read` + 텍스트 매칭으로 처리 (호출 횟수 5~10배)

### 1.3 간접 효과

**Skill 진화 품질 향상**
- `evolve_skill` LLM 프롬프트가 "기존 코드의 구조 패턴" 정보를 받음 → 더 좁은 변경 가능
- `SkillForge`의 Critic 단계가 ast_engine으로 코드 구조 비교 → "이 변경이 정말 의도한 부분만 바꿨는지" 검증 가능

**Cross-verification keep_parts 정확도**
- Opus 판정이 "provider A의 코드와 B의 코드가 구조적으로 동등한가"를 ast_engine으로 비교 가능
- 현재는 텍스트 유사도(Jaccard 등)에만 의존

### 1.4 파이프라인 영향

| 단계 | 변화 |
|------|------|
| Cat O (단일 에이전트 실행) | 도구 호출 횟수 ↓ (5~10배), 정확도 ↑ |
| Cat Q (실패 처리) | FSA L1 retry 시 "변경된 함수만 정확히 식별" 가능 |
| Cat W (CodeReviewDocHook) | git diff 후 변경 함수 시그니처 정확 추출 → 리뷰 품질↑ |

### 1.5 위험

- **에이전트 프롬프트 길이 증가** — 도구 사용법 설명에 ~300토큰 추가 → AdaptiveSkillLoader 12개 스킬 + 컨트랙트 4종이면 컨텍스트 부담
- **ast-grep-py 버전 의존** — frozen exe에서 platform별 휠 필요. 현재 `requirements.txt`에 명시되어 있으나 PyInstaller `af.spec`에 hiddenimports 추가 검증 필요
- **에이전트 LLM이 익숙하지 않음** — Claude/Gemini/Codex 모델이 ast-grep 패턴 문법(`$A`, `$$$ARGS`)을 정확히 생성할 확률이 grep보다 낮음. 초기 적응 비용 + fallback 안내 필수

---

## 2. 수정 2 — `update_ast_state` filepath 실제 경로 사용

### 2.1 변경 내용

`dynamic_orchestrator.py:782, 885`:

```python
# 현재 (가짜)
filepath=f"Project_Scope_{role}"

# 수정 후 (실제)
changed_files = git_manager.diff_files_since(snapshot_sha)
for fp in changed_files:
    await self.memory_hub.update_ast_state(
        filepath=fp,
        author_role=role,
        changes_summary=f"Modified by {role} in task {task_id}: {subtask[:50]}",
    )
```

대상 파일:
- `core/dynamic_orchestrator.py` (호출처 2곳)
- `core/git_manager.py` (`diff_files_since(sha)` 헬퍼 신규 또는 기존 활용)

### 2.2 직접 효과

**(a) `get_file_history(filepath)` 의미 회복**
- 현재 `ast_history["Project_Scope_role"]`만 누적 → 의미 없음
- 수정 후 `ast_history["src/foo/bar.py"]`에 시간순 변경자 누적 → "이 파일을 누가 언제 어떤 이유로 만졌는가"가 단일 쿼리

**(b) `ast_state` 영속 스냅샷 의미 회복**
- `adapters/ast_hub.py`가 `.system_generated/cache/ast_hub_snapshot.json`에 저장하는 데이터가 실제 파일 변경 히스토리가 됨
- 다음 세션 resume 시 "지난 세션이 어느 파일들을 만졌나" 즉시 파악

**(c) 파일 단위 충돌 감지 가능**
- 두 에이전트가 같은 파일 동시 수정 → ast_state 덮어쓰기 직전 락 충돌 감지 가능
- 현재는 모두 `Project_Scope_{role}` 다른 키로 저장되어 충돌 자체가 안 보임

### 2.3 간접 효과

**Lilith LLM 프롬프트 품질**

`dynamic_orchestrator.py:391` "Global Context (Shared AST Memory)" 섹션이 실제 파일 목록으로 채워짐.

현재 (예시):
```
- Project_Scope_coder: [coder] Completed subtask: implement parser
- Project_Scope_qa: [qa] Completed subtask: add tests
```

수정 후 (예시):
```
- src/parser/lexer.py: [coder] add tokenizer for nested brackets
- src/parser/lexer.py: [qa] add 12 tests for tokenizer edge cases
- src/parser/__init__.py: [coder] export Lexer
- tests/test_lexer.py: [qa] new file
```

Lilith가 다음 태스크 결정 시 "어느 파일이 hot path인가" 정보 활용 가능 → blocker 감지 정확도↑

**Episodic 메모리 복원 정확도**
- `EpisodeMatcher`가 "지난 유사 프로젝트에서 어느 파일을 어느 순서로 만졌나"를 학습 가능
- 현재는 mock 데이터라 학습 불가

### 2.4 파이프라인 영향

| 단계 | 변화 |
|------|------|
| Cat N (DynamicOrchestrator) | Lilith 프롬프트 정보 밀도↑, blocker 감지↑ |
| Cat T (Continuity) | resume 시 "어느 파일 작업 중이었는지" 복원 가능 |
| Cat P (메모리 시스템) | UnifiedMemoryFacade WORKING 메모리가 실제 의미 회복 |

### 2.5 위험

- **git_manager.diff_files_since 비용** — 매 태스크 완료마다 git diff 호출. 큰 레포에서 100ms+ 누적
  - 완화: orchestrator가 task 시작 시점 SHA를 저장하고, 완료 시점에 한 번만 diff
- **권한 문제** — 워크스페이스가 git 레포 아닐 수도 있음 (DynamicOrchestrator 워크스페이스는 사용자 프로젝트 dir, 항상 git이라는 보장 없음)
  - 완화: `git rev-parse --git-dir` 체크 후 fallback to file mtime scan

---

## 3. 수정 3 — `subscribe()` 호출처 추가 (pub/sub 활성화)

### 3.1 변경 내용

(a) `AgentSpecializer.specialize()`에서 다른 에이전트의 AST 변경을 받기 위해 subscribe:

```python
# core/agent_specializer.py
def specialize(self, base_agent, task_meta, workspace):
    ...
    if self._memory_hub:
        self._memory_hub.subscribe("ast_updates", self._on_peer_ast_update)
    ...

def _on_peer_ast_update(self, event):
    # event = {"type": "AST_UPDATE", "file": "...", "author": "...", "summary": "..."}
    self._peer_changes_buffer.append(event)
```

(b) 에이전트 종료 시 `unsubscribe`로 누수 방지 (이미 구현됨, `ast_memory_hub.py:58`)

대상 파일:
- `core/agent_specializer.py` (subscribe + buffer + 프롬프트 주입)
- `core/dynamic_orchestrator.py` (에이전트 종료 시 unsubscribe 보장)

### 3.2 직접 효과

**(a) 동시 작업 에이전트 간 변경 인지**
- coder가 `src/parser/lexer.py`를 수정한 순간, 같은 모듈을 만지는 qa 에이전트가 즉시 알림 받음
- qa 프롬프트에 "방금 coder가 lexer.py에 tokenizer 추가함 — 너의 테스트가 이 변경을 cover해야 함" 자동 주입 가능

**(b) Stale read 방지**
- 현재: 에이전트 A가 파일 읽고 → B가 같은 파일 수정 → A의 결과물이 stale state 기반
- 수정 후: A가 자기 작업 중 publish 이벤트 받으면 "재로드 필요" flag 설정 가능

**(c) 글로벌 progress visualization**
- TerminalVisualizer가 "지금 어느 파일이 핫스팟인가" 실시간 표시 가능

### 3.3 간접 효과

**ConversationRoom 합의 품질**
- ConsensusEngine이 "두 에이전트가 동일 파일에 대한 상충 변경을 제안" 자동 감지 → 합의 라운드 시작
- 현재는 두 에이전트가 독립 파일에 변경했다고 가정하고 합의 없이 진행

**FSA L5 decompose 시 충돌 방지**
- `_decompose_and_execute`가 서브태스크 분할 시, AST 변경 이력 참조해서 같은 파일 동시 변경 서브태스크 생성 방지

### 3.4 파이프라인 영향

| 단계 | 변화 |
|------|------|
| Cat N (Orchestrator) | 동시 실행 에이전트 간 stale state 방지 |
| Cat O (AgentSpecializer) | 페르소나 프롬프트에 "peer changes" 섹션 신설 |
| Cat Q L5 | 충돌 회피 분해 가능 |

### 3.5 위험

- **callback 폭주** — N개 에이전트가 모두 subscribe → 한 update가 N회 콜백 → asyncio gather가 N개 병렬 실행
  - 현재 `publish()` 코드(`ast_memory_hub.py:87`): `asyncio.gather(*[_invoke(cb) for cb in callbacks])` — N=10이면 한 update마다 10개 코루틴
  - 완화: callback 내부에서 buffer만 append (heavy work 금지). 이미 timeout 10s 있음
- **무한 루프 위험** — 에이전트가 update 받고 → 자기 파일 수정 → 다시 publish → 자기가 다시 받음
  - 완화: callback에서 `if event["author"] == self.role: return` early-exit

---

## 4. 수정 4 — `parsed_ast_data` 실제 파싱 결과 전달

### 4.1 변경 내용

```python
# core/dynamic_orchestrator.py 또는 호출처
import ast
parsed = None
if filepath.endswith(".py"):
    try:
        with open(filepath) as f:
            parsed = ast.dump(ast.parse(f.read()))[:5000]  # 길이 제한
    except SyntaxError:
        parsed = "PARSE_ERROR"

await self.memory_hub.update_ast_state(
    filepath=fp, author_role=role, changes_summary=..., parsed_ast_data=parsed,
)
```

또는 ast-grep-py로:
```python
from core import ast_engine
matches = ast_engine.search_file("def $NAME($$$ARGS): $$$BODY", filepath)
parsed = [{"name": m["text"][:80], "line": m["line"]} for m in matches]
```

### 4.2 직접 효과

**(a) 함수/클래스 시그니처 인덱스 자동 구축**
- 매 변경마다 파일의 모든 함수 시그니처가 ast_state에 저장됨
- `get_file_ast(filepath)` → "이 파일에 어떤 함수가 있는가" 즉시 조회

**(b) AdaptiveSkillLoader 점수 개선**
- 스킬 관련성 점수 = keyword(0.35)×semantic(0.40)×category(0.25) 외에, "현재 작업 중인 파일의 AST 패턴과 스킬 capability 매칭" 추가 가능
- 예: 파일에 `async def` 다수 존재 → "async testing skill" 우선 로드

### 4.3 간접 효과

**Skill 진화 정확도**
- `evolve_skill` 시 "이 스킬이 어떤 코드 구조를 만지는가" 학습 데이터로 ast_data 활용
- StrategyLedger가 "이 도메인(=AST 패턴) 작업에는 X 스킬이 잘 동작" 패턴 축적

### 4.4 파이프라인 영향

| 단계 | 변화 |
|------|------|
| Cat O (스킬 로더) | 점수 정확도 향상 |
| Cat V (SkillSelfEvolutionHook) | 진화 트리거 정밀화 |

### 4.5 위험

- **메모리 폭증** — 모든 파일의 AST tree 저장. 큰 프로젝트에서 ast_state JSON이 MB 단위
  - 완화: tree 전체 저장 X, 시그니처 요약(함수/클래스 이름 + line)만 저장
- **성능** — `ast.parse()` 동기 호출. 대용량 파일에서 10ms~100ms
  - 완화: ThreadPoolExecutor로 비동기 파싱, 또는 file size cap (>500KB skip)

---

## 5. 종합 효과 시나리오 (현재 vs 수정 후)

### 시나리오: "lexer.py에 새 토크나이저 추가" 작업

#### 현재 (수정 전)

```
T1 (coder): lexer.py 수정
  → memory_hub.update_ast_state("Project_Scope_coder", "Completed: implement tokenizer")
  → ast_state["Project_Scope_coder"] = {summary: "Completed: implement tokenizer", ast_tree: "AST_TREE_MOCK"}
  → publish("ast_updates", event)  → 콜백 0개, no-op

T2 (qa): test_lexer.py 작성
  → AgentSpecializer 프롬프트에 "Global Context: Project_Scope_coder가 tokenizer 구현"
  → qa는 어느 함수가 추가됐는지 모름. 자체 file read로 처음부터 읽음
  → 새 토크나이저 함수 시그니처 추론 실패 → 잘못된 mock test 작성

T3 (Lilith next decision):
  → "Project_Scope_coder, Project_Scope_qa 두 모듈이 활동 중" 정도만 인지
  → 다음 태스크가 lexer 모듈인지 파악 못함
```

#### 수정 후

```
T1 (coder): lexer.py 수정
  → git diff → ["src/parser/lexer.py"]
  → ast.parse → {functions: [tokenize_brackets, _is_open_paren, ...]}
  → memory_hub.update_ast_state("src/parser/lexer.py", "coder", "add bracket tokenizer", parsed_ast_data=...)
  → publish("ast_updates", {file: "src/parser/lexer.py", author: "coder", new_funcs: [...]})
  → qa 에이전트 callback 즉시 발화

T2 (qa): test_lexer.py 작성
  → peer_changes_buffer에 "coder added tokenize_brackets in lexer.py" 자동 주입
  → AgentSpecializer 프롬프트에 정확한 함수 시그니처 포함
  → qa가 정확히 tokenize_brackets 대상 테스트 작성

T3 (Lilith next decision):
  → "src/parser/lexer.py가 hot path. coder + qa 모두 작업"
  → 다음 태스크는 lexer 모듈 의존하는 parser/__init__.py 통합 작업으로 정확히 라우팅

T4 (Continuity): 세션 종료
  → ast_hub_snapshot.json에 실제 파일 변경 히스토리 영속화
  → 다음 세션 resume 시 "지난 세션 lexer.py에 tokenizer 추가했음" 즉시 복원
```

---

## 6. 솔직한 한계 (Karpathy 트레이드오프)

### 6.1 효과를 과대 평가하지 말 것

1. **에이전트 CLI가 자체 도구를 우선 사용** — Claude Code/Gemini/Codex는 자체 Read/Grep/Edit 도구가 있고, ast_engine을 줘도 LLM이 "이미 익숙한 grep으로 해결"할 가능성 높음. 도구를 노출해도 사용률이 30%일 수 있음

2. **subscribe 콜백의 실효성은 에이전트 비동기성에 의존** — 에이전트들이 진정으로 병렬 실행 중일 때만 효과. 현재 DynamicOrchestrator는 `_dispatch_from_board`로 한 번에 idle 에이전트에게만 dispatch — 동시 실행 빈도가 낮으면 pub/sub 가치 제한적

3. **mock data를 real data로 바꿔도 consumer가 없으면 무용** — `get_file_history()` 호출자도 0건임을 추가 확인 필요. consumer를 함께 구현하지 않으면 또 다른 dead code 증식

### 6.2 작업량 추정 (가설)

| 수정 | LOC | 테스트 | 위험 |
|------|-----|--------|------|
| 1 (ast_engine 도구 노출) | ~150 | 5~10 | 중 |
| 2 (filepath 실제 경로) | ~50 | 3~5 | 저 |
| 3 (subscribe 활성화) | ~80 | 5~8 | 중 |
| 4 (parsed_ast_data 실제 파싱) | ~40 | 3~5 | 저 |

**총: ~320 LOC + ~20 테스트, 1~2일 작업** (가설값. 실측 미수행)

### 6.3 우선순위 권장 (가설)

수정 2 → 수정 4 → 수정 3 → 수정 1 순서를 권장:

- 2+4는 데이터 품질 회복 (consumer 없어도 영속화 가치)
- 3은 consumer 등장 시 즉시 활성화
- 1은 가장 큰 효과지만 에이전트 LLM 적응 비용으로 ROI가 가장 불확실

---

## 7. 코덱스에게 묻고 싶은 것 (4개 질문)

### Q1. 효과 추정의 사실 검증

§1~§4의 직접 효과/간접 효과 주장 중 과장 또는 사실 오인이 있는가? 특히:
- §1.2 "도구 호출 횟수 5~10배 감소" — 근거 없는 추정. 코덱스 경험상 실제 감소율은?
- §2.3 "Lilith 프롬프트 정보 밀도↑" — Lilith 결정 품질 개선이 실측 가능한 지표인가?
- §6.1 "사용률 30%" — Claude/Codex/Gemini가 ast-grep을 선택하는 빈도 추정 근거?

### Q2. consumer 부재 문제

§6.1 #3에서 지적한 "mock → real data 바꿔도 consumer 없으면 무용"이 가장 큰 함정. `get_file_history()` 호출자가 0건이라면 수정 2의 가치도 절반 — 동시에 consumer(Lilith 프롬프트 빌더, EpisodeMatcher) 코드도 함께 구현해야 한다.

코덱스 의견: 4개 수정 + N개 consumer를 한 work-item으로 묶을지, 수정 2(데이터 회복) → 측정 → consumer 추가 단계로 분리할지?

### Q3. 우선순위 동의 여부

§6.3의 "수정 2 → 4 → 3 → 1" 순서에 동의하는가? 반론이 있다면:
- ROI 가장 큰 수정은 무엇인가
- "1을 먼저"가 가능한 시나리오는?

### Q4. work-item 승격 가치

본 분석을 토대로 ASTEngine 부활을 work-item으로 승격할 가치가 있는가? 또는:
- (a) ast_engine doctring 교정 + ast_memory_hub 삭제로 단순화
- (b) 수정 2만 단독 적용 (가장 안전, ROI 미지수)
- (c) 4건 모두 단계적 work-item으로 분리

세 옵션 중 추천?

---

## 8. 결론 (잠정)

수정 4건 모두 적용 시 — **"에이전트들이 같은 코드베이스를 공유한다"는 것이 처음으로 실제 의미를 갖게 되며**, Lilith 의사결정 / qa 페르소나 정확도 / continuity 복원이 모두 한 단계 향상될 것으로 *예상*.

다만 ROI 가장 큰 건 수정 2(filepath 실경로) — **이것만 단독 적용해도 Lilith 프롬프트 품질이 즉시 개선**될 가능성이 높음. 1·3은 consumer 측 코드를 함께 짜야 가치가 보임.

**최종 결정은 코덱스 회신 + work-item 분리 후로 보류**.
