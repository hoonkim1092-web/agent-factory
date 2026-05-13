# Agent Factory Knowledge Operating Layer 전체 설계 문서

## 0. 문서 목적

이 문서는 Agent Factory(AF)를 **provider-neutral AI 개발 운영 플랫폼**으로 확장하기 위한 전체 설계안이다.

지금까지 논의한 핵심은 다음 하나로 압축된다.

```text
AF는 단순 코드 생성기가 아니라,
기획 → 명세 → 설계 → 구현 → 검증 → 리뷰 → 기억 → 자가진화까지 이어지는
AI 개발팀 운영 시스템이다.
```

현재 AF는 이미 강력한 내부 구조를 가지고 있다.

- `Master_Blueprint.md`를 통한 시스템 구조 기록
- `code-review.md`를 통한 품질/리스크 기록
- `start_db / end_db`, `start_git / end_git` 기반 메모리/컨텍스트 동기화
- Claude / Codex / Gemini 등 여러 provider 실행 구조
- FSA / ISE / Skill Evolution 등 자가진화 구조
- AF Global Profile, Claude Code memory, project context, Git context 등 여러 기억 계층

하지만 현재 구조에는 중요한 문제가 있다.

```text
실행 provider는 여러 개인데,
메모리와 세션 연속성은 Claude Code auto-memory에 치우쳐 있다.
```

따라서 이 문서의 목표는 다음과 같다.

1. 개발 환경과 사용자 환경을 명확히 분리한다.
2. 사용자 환경은 Local-first를 기본값으로 둔다.
3. 개발 환경은 Git + Supabase + Obsidian + Git Nexus + LLM Wiki 전체 기능을 사용한다.
4. Claude Code memory 중심 구조를 AF Global Profile 중심 구조로 전환한다.
5. Claude / Codex / Gemini 어느 provider를 쓰더라도 같은 AF 기억을 주입받게 한다.
6. Obsidian, Git Nexus, LLM Wiki를 각각 사람용 그래프, 변경 추적 그래프, AI용 지식 위키로 분리한다.
7. `Master_Blueprint`와 `code-review`는 수동 원본 문서가 아니라, Knowledge Layer에서 자동 생성되는 최신 상태 스냅샷으로 전환한다.
8. 개발 시 필요한 정보, 자가진화 기록, 메모리, 리뷰, 결정, 검증 결과를 Knowledge Layer에서 끌어와 ContextPack으로 조립한다.

---

# 1. 현재 AF 구조 요약

## 1.1 현재 AF의 기본 개발 흐름

AF의 기본 개발 흐름은 다음과 같다.

```text
사용자 요청
  ↓
리서치 / 자료 수집
  ↓
project_brief.json
  ↓
role_plan.json
  ↓
feature-plan.md
  ↓
feature-spec.md
  ↓
implementation-design.md
  ↓
implementation-tasks.md
  ↓
approval-gate.md
  ↓
에이전트 실행
  ↓
테스트 / 검증
  ↓
code-review.md
  ↓
Master_Blueprint.md 업데이트
  ↓
메모리 / 위키 / 변경 이력 업데이트
```

이 흐름은 단순히 코드를 생성하는 구조가 아니다. AF는 사용자의 요청을 여러 단계의 문서와 의사결정으로 분해한 뒤 실행한다.

## 1.2 현재 핵심 문서 2개

현재 AF에는 두 개의 강한 문서 축이 있다.

```text
Master_Blueprint.md
= AF 시스템 구조, 실행 흐름, 핵심 모듈, 품질 게이트, 업데이트 규칙을 담은 시스템 지도

code-review.md
= AF 코드 품질, 리스크, 기술부채, dead code, provider 연동 상태를 담은 건강검진표
```

초기에는 이 두 문서가 사람이 직접 읽고 직접 업데이트하는 문서로 기능했다.

하지만 Obsidian / Git Nexus / LLM Wiki / ContextPack 구조를 도입하면, 이 두 문서는 다음처럼 역할이 바뀌어야 한다.

```text
기존:
수동 작성·수동 갱신하는 거대한 문서

목표:
Knowledge Layer에서 자동 생성되는 canonical summary / current snapshot
```

즉 두 문서는 없어지는 것이 아니라, **자동 생성되는 최신 시스템 요약본**으로 바뀐다.

---

# 2. 핵심 문제 정의

## 2.1 Provider는 여러 개인데 Memory는 Claude 중심

현재 AF는 여러 provider를 사용할 수 있다.

```text
- Claude Code
- Codex CLI
- Gemini CLI
- 향후 다른 provider
```

하지만 메모리 동기화는 Claude Code 중심으로 설계되어 있다.

```text
Claude Code auto-memory
= ~/.claude/projects/.../memory/*.md
= sync_claude_memory.py로 Supabase claude_memory 테이블에 동기화
```

반면 Codex의 경우:

```text
~/.codex/sessions/rollout-*.jsonl
→ session_bridge를 통해 AF data/memory/codex_chat/으로 일부 흡수 가능

하지만 ~/.codex/memories/ 또는 ~/.codex/rules/는 현재 공식 sync 대상이 아님
```

즉 구조적으로 다음 문제가 발생한다.

```text
Claude 사용자는 memory/*.md 양방향 동기화 가능
Codex 사용자는 Claude memory를 못 씀
Gemini 사용자는 별도 memory track이 없음
```

이 상태에서는 AF가 provider-neutral 플랫폼이라고 보기 어렵다.

## 2.2 사용자가 Git/Supabase를 직접 설정하면 제품성이 낮아짐

개발자인 사용자는 여러 PC를 옮겨가며 개발하기 때문에 Git과 Supabase sync가 필요하다.

하지만 일반 사용자에게 다음을 요구하면 안 된다.

```text
- Supabase 계정 생성
- 테이블 생성
- API Key 입력
- Git 저장소 생성
- Git remote 설정
- start_db / end_db 직접 실행
```

이건 제품 UX가 아니라 개발환경 세팅이다.

따라서 사용자 환경은 Local-first여야 한다.

```text
기본값:
☑ 로컬에 저장
☐ Git으로 백업/버전 관리
☐ AF Cloud Sync 사용
☐ 자체 데이터베이스 연결
```

---

# 3. 개발 환경과 사용자 환경 분리

## 3.1 개발 환경

개발 환경은 AF를 만들고, 디버깅하고, 고도화하는 환경이다.

```text
개발 환경
= Git + Supabase + start/end sync + Obsidian + LLM Wiki + Git Nexus 전체 사용
```

개발자/운영자는 다음 기능을 직접 사용한다.

```text
- Git 사용
- Supabase 사용
- start_db / end_db 사용
- start_git / end_git 사용
- Claude/Codex/Gemini memory adapter 테스트
- Master_Blueprint / code-review 직접 확인 또는 재생성
- Obsidian / LLM Wiki / Git Nexus 전체 사용
- sync status / payload / trace / debug log 확인
```

개발 환경은 복잡해도 된다. AF 자체를 만드는 환경이기 때문이다.

## 3.2 사용자 환경

사용자 환경은 AF를 이용해 프로젝트를 만들거나 수정하는 환경이다.

```text
사용자 환경
= Local-first 기본값
= Git/Supabase는 선택 옵션
```

사용자는 처음에 이것만 보게 한다.

```text
☑ 로컬에 저장
☐ Git으로 백업/버전 관리
☐ AF Cloud Sync 사용
☐ 자체 데이터베이스 연결
```

사용자 기본 저장 구조는 다음과 같다.

```text
my-project/
  .af/
    memory/
    context/
    wiki/generated/
    reviews/
    nexus/
    versions/
    runs/
    settings.json
```

사용자는 Git이나 Supabase를 몰라도 AF를 사용할 수 있어야 한다.

## 3.3 선택 옵션 UI

### Git 체크 시

사용자가 Git을 선택할 때만 아래 UI가 열린다.

```text
Git URL
브랜치
인증 방식
연결 테스트
동기화 대상 선택
```

Git 기본 sync 대상:

```text
- docs/
- Master_Blueprint generated summary
- code-review generated summary
- verification-report
- ADR / decision-record
- LLM Wiki generated pages
- Git Nexus index
```

Git 기본 제외 대상:

```text
- raw transcript
- provider auth file
- .env
- secret
- 개인 global profile
```

### Supabase / 자체 DB 체크 시

사용자가 자체 DB를 선택할 때만 아래 UI가 열린다.

```text
Supabase URL
Key
Table
User Key
연결 테스트
테이블 확인
```

기본 사용자는 이 UI를 보지 않는다.

---

# 4. 메모리 계층 재정의

AF의 메모리는 단순히 하나가 아니다. 다음 계층으로 구분한다.

## 4.1 Project Context Memory

```text
저장 위치:
로컬 .af/memory/ 또는 Supabase project_context_sync

project_id:
<project>

역할:
프로젝트별 문서, 실행 이력, 작업 컨텍스트 저장
```

## 4.2 AF Global Profile

```text
저장 위치:
로컬 .af/memory/global_profile.json 또는 Supabase project_context_sync

project_id:
user:<safe_key>

역할:
사용자/팀/멀티 프로젝트 공유 기억
```

이 계층이 AF의 중앙 기억이다.

```text
Canonical Memory = AF Global Profile
Provider Native Memory = 보조 캐시 / import-export 대상
```

## 4.3 Claude Code Auto-Memory

```text
로컬:
~/.claude/projects/.../memory/*.md

원격:
Supabase claude_memory table
project_id = <project>
files = JSONB
```

이것은 Claude Code 전용 외부 memory track이다.

## 4.4 Codex Session Memory

```text
로컬:
~/.codex/sessions/rollout-*.jsonl
~/.codex/memories/
~/.codex/rules/

현재:
session_bridge를 통해 일부를 AF data/memory/codex_chat/으로 흡수
```

Codex는 Claude memory track을 직접 쓰지 못한다.

따라서 Codex memory는 provider adapter를 통해 AF Global Profile로 import해야 한다.

## 4.5 Git Document Memory

Git으로 관리되는 선언적 문서 기억이다.

```text
CLAUDE.md
AGENTS.md
NEXT_STEPS.md
Master_Blueprint.generated.md
code-review.generated.md
ADR
verification-report
LLM Wiki generated pages
```

---

# 5. Provider-neutral Memory 설계

## 5.1 핵심 원칙

```text
Claude memory를 중앙에 두지 않는다.
AF Global Profile을 중앙에 둔다.
모든 provider는 AF Global Profile에서 생성된 ContextPack을 받는다.
```

## 5.2 목표 구조

```text
Claude Memory
Codex Sessions
Gemini Context
        ↓
Provider Memory Adapter
        ↓
AF Global Profile
        ↓
LLM Wiki
        ↓
ContextPack
        ↓
Claude / Codex / Gemini 실행
```

## 5.3 Provider Memory Adapter

기존 `sync_claude_memory.py`는 Claude 전용이다. 이를 일반화한다.

```text
sync_claude_memory.py
→ sync_provider_memory.py
```

모듈 구조:

```text
core/provider_memory/
  base.py
  registry.py
  claude_adapter.py
  codex_adapter.py
  gemini_adapter.py
```

기본 인터페이스:

```python
class ProviderMemoryAdapter:
    provider_id: str

    def detect(self) -> bool:
        pass

    def pull_native(self, project_id: str):
        pass

    def push_native(self, project_id: str):
        pass

    def import_to_af_global(self, project_id: str, user_key: str):
        pass

    def export_from_af_global(self, project_id: str, user_key: str):
        pass
```

## 5.4 Claude Adapter

```text
입력:
~/.claude/projects/.../memory/*.md

기능:
- 기존 claude_memory sync 유지
- memory/*.md를 AF Global Profile로 요약 import
- AF Global Profile 핵심 지식을 Claude memory에 export 가능
```

## 5.5 Codex Adapter

Codex는 2단계로 접근한다.

### Phase 1 — Session ingest

```text
~/.codex/sessions/rollout-*.jsonl
→ parse
→ summarize
→ .af/memory/provider/codex/
→ AF Global Profile
```

### Phase 2 — Context export

Codex가 안정적으로 읽을 수 있는 위치가 확인되면 export한다.

후보:

```text
AGENTS.md
.codex/context.md
.codex/rules/af.rules
```

단, 우선순위는 Codex native memory가 아니라 ContextPack 주입이다.

## 5.6 Gemini Adapter

초기 Gemini Adapter는 최소 기능으로 시작한다.

```text
- session log 감지
- provider-specific memory 위치 확인
- 없으면 ContextPack 주입만 수행
```

---

# 6. ContextPack 설계

## 6.1 역할

ContextPack은 개발 또는 실행에 필요한 지식을 여러 source에서 끌어와 조립한 provider-neutral 실행 컨텍스트다.

```text
Knowledge Sources
→ Retrieval / Filtering
→ ContextPack
→ Claude / Codex / Gemini / AF Agent
```

## 6.2 입력 source

ContextPackBuilder는 다음 source를 검색한다.

```text
1. 코드 인덱스
2. Obsidian graph links
3. Git Nexus change graph
4. LLM Wiki generated pages
5. ADR / decision-record
6. verification-report
7. review findings
8. warning registry
9. self-evolution logs
10. AF Global Profile
11. provider session summaries
12. resume brief
```

## 6.3 출력 파일

```text
.af/context/context_pack.md
.af/context/context_pack.json
```

## 6.4 context_pack.json 예시

```json
{
  "project_id": "agent-factory",
  "provider": "codex_cli",
  "task": "Implement provider-neutral memory adapter",
  "source_refs": {
    "llm_wiki": [
      "Provider-Neutral-Memory.md",
      "ContextPack-Injection.md"
    ],
    "git_nexus": [
      "commit:abc123"
    ],
    "reviews": [
      "code-review.generated.md#provider-layer"
    ],
    "self_evolution": [
      "FSA-Level-Model.md"
    ]
  },
  "open_risks": [
    "Claude memory dependency",
    "Codex native memory not synced"
  ],
  "rules": [
    "AF Global Profile is canonical memory",
    "Provider native memory is adapter cache"
  ]
}
```

---

# 7. Obsidian 적용 설계

## 7.1 역할

Obsidian은 사람이 보는 AF 지식 그래프다.

```text
Obsidian = Human Knowledge Graph
```

Obsidian은 원본을 대체하지 않는다. 사람이 구조를 탐색하고 이해하는 뷰다.

## 7.2 Obsidian이 보여줄 노드

```text
AF System
Provider Memory
AF Global Profile
ContextPack
Execution Self-Evolution
Skill Self-Evolution
Master Blueprint Snapshot
Code Review Snapshot
Git Nexus
LLM Wiki
```

## 7.3 Vault 구조

```text
AF-Vault/
  00_Index/
  01_System/
  02_Memory/
  03_Provider/
  04_SelfEvolution/
  05_Reviews/
  06_Decisions/
  07_LLMWiki/
  08_GitNexus/
```

## 7.4 사용자 환경에서는 옵션

사용자에게 Obsidian 설치를 요구하지 않는다.

```text
기본:
AF 내부 웹/로컬 UI에서 지식 그래프 보기

옵션:
Obsidian Vault로 내보내기
```

---

# 8. Git Nexus 설계

## 8.1 역할

Git Nexus는 변경 이력과 근거를 연결하는 그래프다.

```text
요구사항
→ 결정
→ 코드 변경
→ 문서 변경
→ 검증
→ 메모리 업데이트
→ 다음 ContextPack
```

## 8.2 저장 위치

로컬 사용자 환경:

```text
.af/nexus/git_nexus.jsonl
```

개발 환경:

```text
.af_knowledge/git_nexus.jsonl
또는 Supabase/Git 연동
```

## 8.3 이벤트 예시

```json
{
  "event_type": "change_commit",
  "project_id": "agent-factory",
  "provider": "codex_cli",
  "changed_code": [
    "core/provider_memory/codex_adapter.py"
  ],
  "changed_docs": [
    "docs/generated/master_blueprint.md",
    "docs/generated/code_review_summary.md"
  ],
  "decisions": [
    "DEC-provider-neutral-memory"
  ],
  "verification": {
    "verdict": "PASS",
    "report": "verification-report.md"
  },
  "memory": {
    "context_pack_used": ".af/context/context_pack.json",
    "global_profile_updated": true,
    "provider_memory_imported": ["codex_session"]
  }
}
```

---

# 9. LLM Wiki 설계

## 9.1 역할

LLM Wiki는 AI가 읽기 좋은 provider-neutral 지식 위키다.

```text
LLM Wiki = AI-readable generated knowledge base
```

## 9.2 입력

```text
- 코드 인덱스
- Git Nexus
- review findings
- verification-report
- ADR
- AF Global Profile
- provider session summaries
- self-evolution logs
- old Master_Blueprint / code-review
```

## 9.3 출력

```text
.af/wiki/generated/
  system/
  memory/
  provider/
  self-evolution/
  risks/
  flows/
```

## 9.4 필수 페이지

```text
memory/Provider-Neutral-Memory.md
memory/AF-Global-Profile.md
memory/Claude-Code-Memory.md
memory/Codex-Session-Ingest.md
memory/ContextPack-Injection.md

self-evolution/Execution-Self-Evolution.md
self-evolution/Skill-Self-Evolution.md
self-evolution/FSA-Level-Model.md

risks/Provider-Memory-Asymmetry.md
risks/Memory-Payload-Bloat.md
risks/Plaintext-Memory-Storage.md

system/ProjectPipeline.md
system/DynamicOrchestrator.md
system/ProviderMemoryAdapter.md
```

## 9.5 원칙

```text
LLM Wiki는 원본이 아니다.
LLM Wiki는 generated summary다.
모든 페이지는 source_refs를 가진다.
ContextPackBuilder가 LLM Wiki를 검색해서 사용한다.
```

---

# 10. Master_Blueprint / code-review 재정의

## 10.1 기존 역할

```text
Master_Blueprint.md
= 사람이 직접 업데이트하는 시스템 지도

code-review.md
= 사람이 직접 누적하는 코드 리뷰 문서
```

## 10.2 목표 역할

```text
Master_Blueprint.generated.md
= Knowledge Layer에서 땡겨온 최신 시스템 구조 요약

code-review.generated.md
= review logs / warning registry / verification / Git Nexus에서 땡겨온 최신 리스크 요약
```

즉 두 문서는 없어지는 것이 아니라 자동 생성 snapshot이 된다.

## 10.3 진짜 Source of Truth 재정의

```text
코드 구조의 진실
= 실제 코드 + AST/index + module metadata

변경 이력의 진실
= Git commit + Git Nexus

결정의 진실
= ADR / decision-record

검증의 진실
= verification-report / test logs / cross-review result

리스크의 진실
= code-review findings / warning registry / review reports

메모리의 진실
= AF Global Profile + provider session summaries

요약본
= Master_Blueprint.generated.md / code-review.generated.md / LLM Wiki
```

---

# 11. 자가진화 정보 적용

AF의 자가진화는 두 가지로 나눈다.

## 11.1 실행 전략 자가진화

```text
Execution Self-Evolution
= 실패한 태스크를 어떻게 다시 풀 것인가
```

구성 요소:

```text
FSA Loop
ISE Loop
FailureClassifier
StallDetector
LineageLedger
StrategyLedger
retry / pivot / redesign / decompose
```

## 11.2 스킬 능력 자가진화

```text
Skill Self-Evolution
= AF가 어떤 능력을 새로 얻고, 평가하고, 승격할 것인가
```

구성 요소:

```text
Skill Forge
Skill Creator
Skill Eval Harness
Skill Quality Gate
Skill Promotion
Skill Registry
Skill Evolution Bus
```

## 11.3 개발 시 활용 방식

개발 요청이 들어오면 ContextPackBuilder는 자가진화 정보를 검색한다.

예:

```text
요청:
Codex provider memory adapter 만들어줘

ContextPack에 포함:
- provider memory 관련 과거 실패
- FSA에서 반복된 sync 실패 패턴
- StrategyLedger의 성공 provider/role 기록
- Skill Evolution에서 provider adapter 관련 변경 이력
- code-review의 provider/hook risk
- LLM Wiki의 Provider-Neutral-Memory 페이지
```

---

# 12. start/end Lifecycle 재설계

## 12.1 개발 환경 start

```text
start_sync
  ↓
start_db
  - Supabase project context pull
  - Supabase global profile pull
  - provider memory pull/import
  ↓
start_git
  - Git context pull
  ↓
LLM Wiki load/update check
  ↓
Git Nexus load
  ↓
ContextPack build
  ↓
개발 시작
```

## 12.2 개발 환경 end

```text
검증 / 리뷰 완료
  ↓
resume brief 생성
  ↓
provider session ingest
  ↓
self-evolution logs 저장
  ↓
Git Nexus 갱신
  ↓
LLM Wiki 갱신
  ↓
Obsidian links 갱신
  ↓
Master_Blueprint.generated.md 재생성
  ↓
code-review.generated.md 재생성
  ↓
end_db
  - project/global memory push
  - provider memory push/export
  ↓
end_git
  - Git context push
```

## 12.3 사용자 환경 start

```text
로컬 .af/ 로드
  ↓
선택 옵션 확인
  ├─ Git enabled → Git pull
  ├─ Cloud enabled → Cloud pull
  └─ DB enabled → DB pull
  ↓
로컬 memory merge
  ↓
LLM Wiki 로드
  ↓
ContextPack 생성
  ↓
실행 시작
```

## 12.4 사용자 환경 end

```text
실행 완료
  ↓
verification-report 저장
  ↓
review summary 저장
  ↓
local .af/memory 저장
  ↓
LLM Wiki 갱신
  ↓
Git Nexus local index 갱신
  ↓
선택 옵션 확인
  ├─ Git enabled → Git push
  ├─ Cloud enabled → Cloud push
  └─ DB enabled → DB push
```

---

# 13. 단계별 적용 계획

## Phase 1. 환경 분리와 Local-first 저장 구조

목표:

```text
개발 환경과 사용자 환경을 분리한다.
사용자 기본 저장 구조를 .af/ 로컬 폴더로 정의한다.
```

작업:

```text
1. .af/settings.json 스키마 정의
2. .af/memory/ 구조 정의
3. .af/context/ 구조 정의
4. .af/wiki/generated/ 구조 정의
5. .af/nexus/ 구조 정의
6. Git/Supabase 옵션을 체크박스로 분리
```

## Phase 2. AF Global Profile을 canonical memory로 선언

목표:

```text
Claude memory 중심 구조에서 AF Global Profile 중심 구조로 이동한다.
```

작업:

```text
1. global_profile.json 스키마 정의
2. provider session summary 스키마 정의
3. project memory와 global memory 분리
4. ContextPackBuilder가 global_profile을 우선 참조하게 변경
```

## Phase 3. Provider Memory Adapter 도입

목표:

```text
sync_claude_memory.py를 provider-neutral adapter 구조로 일반화한다.
```

작업:

```text
1. ProviderMemoryAdapter base 정의
2. ClaudeAdapter 구현
3. CodexAdapter 구현
4. GeminiAdapter stub 구현
5. sync_provider_memory.py 추가
6. start_db/end_db에서 provider adapter 호출
```

## Phase 4. ContextPackBuilder 구현

목표:

```text
개발 또는 실행에 필요한 정보를 여러 source에서 끌어와 provider-neutral ContextPack을 만든다.
```

작업:

```text
1. context_pack.json/md 생성
2. source_refs 구조 정의
3. open risks 포함
4. self-evolution logs 포함
5. provider session summary 포함
6. AgentRunner가 provider별 prompt에 ContextPack 주입
```

## Phase 5. LLM Wiki 생성

목표:

```text
AI가 재사용할 수 있는 generated knowledge base를 만든다.
```

작업:

```text
1. llm_wiki_adapter.py 구현
2. memory/provider/self-evolution/system/risk 페이지 생성
3. source_refs 포함
4. ContextPackBuilder에서 LLM Wiki 검색
```

## Phase 6. Git Nexus 도입

목표:

```text
변경 이력, 문서, 코드, 검증, 메모리를 연결한다.
```

작업:

```text
1. git_nexus.jsonl 스키마 정의
2. commit/change event 기록
3. verification 연결
4. memory update 연결
5. ContextPack에서 관련 Git Nexus event 검색
```

## Phase 7. Obsidian Export / Graph 적용

목표:

```text
사람이 AF의 지식 구조를 탐색할 수 있게 한다.
```

작업:

```text
1. Obsidian vault export 구조 정의
2. wikilink 자동 생성
3. graph node 문서 생성
4. 사용자 환경에서는 옵션으로 제공
```

## Phase 8. Master_Blueprint / code-review generated 전환

목표:

```text
수동 관리 문서를 자동 생성 snapshot으로 전환한다.
```

작업:

```text
1. master_blueprint_generator.py 구현
2. code_review_summary_generator.py 구현
3. LLM Wiki / Git Nexus / review logs / code index에서 pull
4. generated 문서를 ContextPack source로 사용
```

## Phase 9. 사용자 UI 정리

목표:

```text
사용자는 복잡한 인프라를 모르고 Local-first로 시작하게 한다.
```

작업:

```text
1. 저장 방식 체크박스 UI
2. Git 체크 시 Git URL/branch/auth/test UI
3. Supabase 체크 시 URL/key/table/test UI
4. Obsidian export UI
5. LLM Wiki update mode UI
6. Sync status UI
```

---

# 14. 리스크와 대응

## Risk 1. Source of Truth 혼란

문제:

```text
Master_Blueprint, LLM Wiki, Obsidian, Git Nexus, memory가 서로 다른 내용을 가질 수 있음
```

대응:

```text
- 코드/ADR/verification/review/memory를 실제 source로 둔다.
- generated 문서는 source_refs를 가진다.
- LLM Wiki는 원본이 아니라 요약본으로 표시한다.
```

## Risk 2. Payload bloat

문제:

```text
chat/session 누적으로 Supabase payload가 커질 수 있음
```

대응:

```text
- raw transcript 기본 OFF
- 최근 N개만 sync
- TTL
- summary-first 저장
- 대용량 raw는 object storage 분리
```

## Risk 3. 평문 저장 보안

문제:

```text
대화, 코드, memory, trace가 평문으로 저장될 수 있음
```

대응:

```text
- .env 제외
- secret scanner
- symlink 제외
- RLS
- user/project access control
- optional encryption
```

## Risk 4. ContextPack 과대화

문제:

```text
너무 많은 정보를 넣으면 토큰 비용이 증가한다.
```

대응:

```text
- relevance scoring
- token budget
- Fast / Standard / Deep mode
- summary-first
```

## Risk 5. Provider local format 변화

문제:

```text
Claude/Codex/Gemini 로컬 파일 구조가 바뀌면 adapter가 깨진다.
```

대응:

```text
- adapter detect/version guard
- 실패 시 ContextPack fallback
- provider native memory를 canonical source로 보지 않음
```

---

# 15. 최종 결론

AF의 다음 단계는 단순히 Obsidian, Git Nexus, LLM Wiki를 붙이는 것이 아니다.

핵심은 다음 전환이다.

```text
문서 중심 개발
→ 지식 그래프 기반 개발

Claude memory 중심
→ AF Global Profile 중심

수동 Master_Blueprint / code-review
→ 자동 생성 canonical snapshot

provider-specific memory
→ provider-neutral ContextPack

개발자용 sync 구조
→ 사용자용 Local-first 구조
```

최종 목표 구조는 다음과 같다.

```text
개발 환경:
Git + Supabase + start/end sync + Obsidian + Git Nexus + LLM Wiki 전체 사용

사용자 환경:
Local-first 기본값
Git/Supabase/Cloud/Obsidian은 선택 옵션

중앙 기억:
AF Global Profile

AI 실행 컨텍스트:
ContextPack

사람용 그래프:
Obsidian

변경 추적:
Git Nexus

AI용 지식 위키:
LLM Wiki
```

한 줄로 정리하면 다음과 같다.

> AF는 앞으로 긴 문서를 사람이 계속 업데이트하는 구조가 아니라, Obsidian / Git Nexus / LLM Wiki / Memory / Self-Evolution에서 필요한 지식을 검색·압축해 ContextPack으로 만들고, 그 ContextPack을 기반으로 Claude, Codex, Gemini 어느 provider든 동일한 개발 품질을 낼 수 있게 하는 provider-neutral AI 개발 운영체제로 가야 한다.
