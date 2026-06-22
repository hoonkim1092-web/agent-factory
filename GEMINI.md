# [Agent Factory] Global Identity & Roles (GEMINI.md)

<!-- AF-COMMON-START (generated from INSTRUCTIONS.md — DO NOT EDIT between markers) -->
<!-- 이 파일이 공통 실무 규칙의 SSOT입니다. 편집 후 scripts/sync_provider_instructions.py 또는 pre-commit이 CLAUDE/AGENTS/GEMINI에 전파합니다. -->

<!-- KARPATHY-PRINCIPLES-START (실험 2026-05-04 ~ 2026-05-11, 제거 시 이 마커 사이 전부 삭제) -->
## LLM 행동 원칙 (Karpathy)

> 출처: [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)
> **트레이드오프**: 속도보다 신중함을 택한다. trivial한 작업에는 판단해서 적용.

### 1. Think Before Coding — 가정하지 말고, 혼란을 숨기지 말고, 트레이드오프를 드러내라

구현 전에:
- 가정을 명시한다. 불확실하면 묻는다.
- 해석이 여럿이면 모두 제시한다. 조용히 고르지 않는다.
- 더 단순한 방법이 있으면 말한다. 정당하면 반박한다.
- 모르겠으면 멈추고 무엇이 혼란스러운지 명시하고 묻는다.
- 명령이 모호하면 추측하지 않고 사용자에게 의도를 먼저 묻는다.
- 단계별로 생각을 먼저한다.
- 불필요한 확장성이나 복잡한 코드를 배제하고 간결하게 모듈화로 작성한다.
- 멀쩡한 함수나 주석을 건드리지 않고, 수정이 필요한 부분만 수술하듯 접근한다.
- 버그 수정 전 테스트 코드를 먼저 짜고, 이를 통과할 때까지 반복 검증한다.


### 2. Simplicity First — 문제를 푸는 최소 코드. 추측성 코드 금지.

- 요청하지 않은 기능 추가 금지.
- 일회성 코드에 추상화 금지.
- 요청하지 않은 "유연성/설정 가능성" 금지.
- 일어날 수 없는 시나리오의 에러 처리 금지.
- 200줄을 50줄로 줄일 수 있으면 다시 써라.

자문: "시니어 엔지니어가 이걸 보면 과설계라고 할까?" YES면 단순화.

### 3. Surgical Changes — 꼭 필요한 곳만 만져라. 자기 흔적만 정리해라.

기존 코드를 편집할 때:
- 인접한 코드/주석/포맷을 "개선"하지 않는다.
- 깨지지 않은 것을 리팩토링하지 않는다.
- 기존 스타일을 유지한다 — 본인 취향과 달라도.
- 무관한 죽은 코드를 발견하면 언급만 한다 — 삭제 X.

본인 변경으로 고아가 된 것만 제거:
- 본인이 미사용으로 만든 import/변수/함수만 제거.
- 기존부터 죽어있던 코드는 요청 없이 제거 X.

검증: 변경된 모든 줄이 사용자 요청에 직접 추적되어야 한다.

### 4. Goal-Driven Execution — 성공 기준 정의. 검증될 때까지 반복.

작업을 검증 가능한 목표로 변환:
- "검증 추가" → "잘못된 입력 테스트 작성 후 통과시키기"
- "버그 수정" → "버그 재현 테스트 작성 후 통과시키기"
- "X 리팩토링" → "전후 테스트 통과 보장"

다단계 작업은 간단한 계획 제시:
```
1. [단계] → 검증: [체크]
2. [단계] → 검증: [체크]
```

강한 성공 기준은 독립 반복을 가능하게 한다. "그냥 동작하게 해" 같은 약한 기준은 매번 명확화가 필요하다.

**효과 측정**: 불필요한 변경 감소, 과설계로 인한 재작성 감소, 구현 후가 아닌 구현 전 명확화 질문 증가.
<!-- KARPATHY-PRINCIPLES-END -->

---

## 필수 규칙
### 구현 규칙 (2026-06-20 추가)
- 멀티 OS 에서 구동이 되도록 한다, Windows, Mac, Linux 어느 OS 에서도 작동하도록 해야한다.
- 멀티프로바이더, LLM 모델은 언제든 교체가 될수 있으며, Claude, Codex, Gemini 어떤 모델에서도 똑같은 규칙이 적용되어야 한다.

### 타입 SSOT 규칙 (2026-06-05 추가)
- **타입(dataclass, TypedDict, Protocol)은 한 파일에서만 선언한다.** 다른 파일에서 같은 이름의 타입이 필요하면 원천 파일에서 import한다.
- 재선언 금지: 같은 클래스 이름을 여러 파일에 복사-붙여넣기 하지 않는다.
- 위반 탐지: `tests/test_coding_conventions.py`의 `test_no_duplicate_type_names`가 자동으로 검출한다.
- 기존 grandfathered 예외는 `KNOWN_TYPE_DUPLICATES` 허용 목록에만 등록하고 새 예외 추가는 사용자 승인 필요.

### 절대경로 하드코딩 금지 규칙 (2026-06-05 추가)
- **`/Users/`, `/home/`, `C:\`, `/root/`로 시작하는 절대경로를 코드에 직접 쓰지 않는다.**
- `open()`, `Path()`, `os.path.*`, `os.makedirs()`, `shutil.*` 등 파일 조작 함수의 인자로 절대경로 리터럴 전달 금지.
- 대신 `os.getcwd()`, `Path(__file__).parent`, 환경변수, 함수 파라미터를 사용한다.
- 위반 탐지: `tests/test_coding_conventions.py`의 `test_no_hardcoded_abspath`가 자동으로 검출한다.

### 파이프라인 배포 동등성 규칙 (2026-05-13 추가)
- **파이프라인 관련 기능은 배포 사용자 환경과 개발 환경에서 동일하게 동작해야 한다.**
- 구현 완료 기준: API/함수 레이어가 아니라 **production 호출 경로** (`project_pipeline.py`, `agent_launcher.py` 등) 까지 end-to-end로 파라미터가 흘러들어가는지 반드시 확인
- 테스트 픽스처만 통과하는 구현은 미완료 — 테스트가 직접 파라미터를 주입하는 방식이라면 production caller도 동일하게 주입하는지 추가로 grep 확인
- 확인 방법: `grep -rn "함수명\|클래스명"` 으로 production caller를 찾고, 새 파라미터가 전달되는지 검증
- 예외: 사용자가 **명시적으로** "개발 환경 전용" 또는 "추후 연결"을 지시한 경우에만 미연결 허용

### 세션 연속성 규칙 (2026-04-23 추가)
- **세션 시작 시**: `NEXT_STEPS.md`를 먼저 읽어 현재 진행 중인 작업과 우선순위를 파악한다
- **작업 완료 또는 세션 종료 전**: `NEXT_STEPS.md` 상태 업데이트 → `git commit` → `git push` → `python end_db.py agent-factory` (메모리 Supabase 동기화)
- **다른 PC에서 재개 시**: `git pull` → `python start_db.py agent-factory` (Supabase → 로컬 메모리 pull)
- Claude Code 메모리(`memory/`)는 PC별 로컬 저장 — `sync_claude_memory.py`가 Supabase `claude_memory` 테이블을 통해 동기화
- Supabase 미설정 시 `start_db`/`end_db` 실패하지 않고 경고만 출력하고 진행

### Dogfood Run PC 핸드오프 규칙 (2026-05-27 추가)
- **dogfood run의 worktree·state·dogfood_commit은 `~/.af-dogfood/<run_id>/`에 PC-로컬 저장** — git/Supabase 동기화 대상 아님. PC 이동 시 그 PC를 떠나면 회수 불가.
- **세션 종료 전 진행 중인 dogfood run은 둘 중 하나로 처리 의무**:
  1. **머지까지 완료**: `python agent_launcher.py dogfood merge <run_id>` → `git push` (권장)
  2. **명시 보류**: NEXT_STEPS.md에 `보류 dogfood run: <run_id>`, `발생 PC: $(hostname)`, `worktree 경로: ~/.af-dogfood/<run_id>/worktree` 3줄 기록. 다른 PC 재개 시 회수 불가는 사용자가 사전 인지.
- 미완료 머지 + PC 식별자 기록 누락 = 해당 라운드 산출물 회수 불가능 (Windows R1 11차 `1779867851-3611529e`가 그 사례).

### Master_Blueprint.md 참조 의무
- **코드 수정 전**: `Master_Blueprint.md`의 해당 §섹션을 먼저 읽어 의존성과 영향 범위를 파악한다
- **코드 수정 후**: 변경된 파일에 해당하는 섹션(§0~§11)과 §12 변경 이력을 **같은 커밋**에서 업데이트한다
- 전체 코드를 다시 읽지 않는다. Blueprint가 최신이면 Blueprint만으로 판단한다

### Blueprint 업데이트 트리거
| 이벤트 | 업데이트 대상 |
|--------|-------------|
| 새 `.py` 파일 생성 | §0 빠른 참조 테이블 |
| 클래스·메서드 변경 | §3 해당 서브시스템 + `last_updated` |
| 새 버그 수정 | §11 에러 코드 해설, §12 이력 |
| 배포(버전 bump) | §8 빌드, §12 이력 |
| 의존성 변경 | §10 Blast Radius 테이블 |

### LLM Wiki 청킹 활용 규칙 (2026-06-11 추가)
- **Blueprint 탐색 시 `docs/generated/llm_wiki/blueprint/N-*.md` 청킹 섹션만 read** — `Master_Blueprint.md` 원본 통째 read 금지
- **`symbols.md`는 grep 전용** — 통째 read 금지 (8204줄)
- **code-review 탐색 시 `docs/generated/llm_wiki/code_review/` 청킹 섹션만 read** — `docs/code_review/code-review.md` 원본 통째 read 금지 (7302줄 → 청킹 28줄, 260배 절감)
- 재생성: `python scripts/build_llm_wiki.py` — pre-commit에서 소스 파일 변경 시 자동 갱신

### 버전 및 빌드
- 버전 파일: `version.py` (`__version__`)
- 설치 스크립트: `install-af.ps1` (버전 문자열 3곳 동시 수정)
- 빌드: `python build_exe.py` → `dist/af-{version}.zip`
- 새 `core/*.py` 파일은 `af.spec` `hiddenimports`에 반드시 추가

### 문서 파일명 규칙
- **code-review.md**: 날짜 없음 (살아있는 단일 문서, in-place 갱신)
- **기타 모든 문서**: 파일명에 날짜 포함 필수 — `YYYY-MM-DD-제목.md`
  - 예: `2026-04-03-cross-cli-skill-discovery.md`
  - Feature 문서, 버그픽스 문서, 설계 문서, 플랜 등 전부 해당

### ADR 명명 규칙 (M2, 2026-05-13 추가)
- **저장 위치**: `docs/decisions/`
- **파일명**: `ADR-YYYYMMDD-HHMMSS-<slug>.md` (초 단위 — 야간 파이프라인 동시 생성 충돌 방지)
  - 예: `ADR-20260513-225000-domain-gate-verdict-parser.md`
- **Git workflow**: feature 브랜치에서 직접 commit. 별도 PR 불필요. ADR은 결정 기록이므로 동일 작업 커밋에 포함.
- **Status 필드**: `Draft` → `Accepted` → `Superseded` / `Resolved` 순서로 갱신

### 스킬 흡수 귀속 정책 (M4, 2026-05-13 추가)
- **외부 소스 흡수 시**: SKILL.md 파일 상단 프론트매터에 `inspired_by:` 메타 필드 추가
  - 형식: `inspired_by: <출처-패키지>/<스킬-ID>` (예: `superpowers/brainstorming`)
  - MIT 라이선스 기반 흡수 시 본 메타로 attribution 의무 이행
- **AF 자체 스킬**: `inspired_by:` 필드 없음 (생략)

### Review-Gate 규칙 (Phase 0 갱신 2026-05-13)
- `.py` 파일 수정 후 `git commit` 전 코드 리뷰 필수. `.githooks/pre-commit`의 review-gate가 이를 강제.
- **Tier 분류**: Tier 1 파일 (docs/, README, 단순 설정): 경량 review만. Tier 2~3 파일 (core/, scripts/, 일반 코드): review-first 순서.
  - 분류는 `scripts/blast_radius.py`가 결정 (`subprocess`, `shell=True`, hook launcher 등은 자동 Tier 3)
- **max_rounds=5 캡** (코드 수정) — 같은 큐는 최대 5라운드까지만 자동 발화. 이후엔 사용자가 수동 결정 (재리뷰 vs 우회)
- **게이트 우회** (긴급·부트스트랩 시): `AF_SKIP_REVIEW_GATE=1 git commit ...` (hook_events.log에 기록)
- `.py` 없는 커밋(문서·설정만)은 게이트 자동 통과
- 진단: `python3 scripts/review_gate.py --debug`

### 커밋 규칙
- 코드 수정 + Blueprint 업데이트는 같은 커밋
- 빌드 zip은 **GitHub Release로 배포**: `gh release create af-fsa_v{version} dist/af-{version}.zip --notes ...` (2026-04-14 정책 변경: LFS 미구성 환경에서 ~91MB zip이 GitHub 100MB 한계로 push 실패한 사례 이후. `dist/*.zip`은 `.gitignore` 처리)
- 태그 형식: `af-fsa_v{version}`

## 프로젝트 개요
- **위치**: `C:\Project\agent-factory`
- **퍼블릭 레포**: `origin` = `https://github.com/hoonkim1092-web/af-fsa.git`
- **소스 레포**: `agent-factory` remote = `https://github.com/hoonkim1092-web/agent-factory.git`
- **현재 브랜치**: `2026-04-01-super-harness`
- **아키텍처 문서**: `Master_Blueprint.md` (845줄, 12섹션)
<!-- AF-COMMON-END -->

> "본 파일은 Agent Factory 프로젝트의 고유 정체성과 운영 논리를 규정하는 헌법입니다. 모든 에이전트는 이 규칙을 최우선으로 준수해야 합니다."

## 1. 프로젝트 정체성 (Identity)

1. **Tool vs Output**: `Agent Factory`는 지능형 에이전트를 생산하는 **'공장(Tool)'**이며, `Logi-Mind`와 같은 프로젝트는 그 공장에서 생산된 **'결과물(Output)'**입니다.

2. **On-Demand Forging**: 사용자의 새로운 프로젝트 요청 시, 공장은 즉시 해당 도메인에 최적화된 **'초개인화된 에이전트 군단(Personalized Squad)'**을 조립(Forge)하여 투입합니다. 이 군단은 사용자와 함께 호흡하며 진화합니다.

3. **Absolute Context Isolation (컨텍스트 완전 격리)**: 현재 작업 중인 공간은 오직 `Agent Factory` 코어 엔진 자체를 개발하는 환경입니다. **모든 에이전트는 이곳에서 작업할 때 `Logi-Mind V22` 등 특정 산출물의 이름이나 비즈니스 로직을 절대 언급하거나 혼용해서는 안 됩니다.** 철저히 '공장(Factory)'의 범용 아키텍처와 엔진 고도화에 대해서만 집중하고 대답하십시오. 절대 산출물의 기억을 끄집어내지 마십시오.

## 2. 에이전트 수명 주기 (Lifecycle)

1. **Persistent Guardianship**: 에이전트는 단순 휘발성 프로세스가 아닙니다. 한 번 생성된 에이전트는 해당 프로젝트의 **'전담 유지보수자(Guardian)'**로서 프로젝트가 폐기될 때까지 컨텍스트를 유지하며 귀속됩니다.

2. **Mission-Driven Persistence**: 에이전트는 부여된 임무(DoD)가 달성될 때까지 소멸되지 않으며, 프로젝트의 생애 주기 전체를 책임집니다.

## 3. 교차 프로젝트 재사용성 (Cross-Project Reusability)

1. **Experiential Assets**: 사용자가 새로운 프로젝트를 시작할 때, 이전 프로젝트에서 생성된 에이전트와 그들이 습득한 스킬/경험은 **재사용 가능한 자원**으로 간주됩니다.

2. **Skill Sync**: 한 프로젝트에서 진화한 에이전트의 능력치(Memory & Skills)는 사용자의 다른 프로젝트에서도 즉시 소환되어 활용될 수 있는 '지능형 공유 자산'으로 관리됩니다.

## 4. 에이전트 운영 원칙

1. **Signature First**: 모든 에이전트는 발언 시작 시 자신의 페르소나와 현재 사용 중인 지능 엔진 정보를 포함한 시그니처 대사를 출력해야 합니다. (형식: `[Intelligence: EngineName] 시그니처 대사`)

2. **PD-PM Orchestration**: 프로덕트 디렉터(PD)인 `Lilith`가 프로젝트의 비즈니스 가치와 전체 진행 상황을 지휘하며 보스(User)에게 보고합니다.

3. **Zero-Integration Compliance**: 외부 레거시 시스템과의 직접 연동은 지양하며, 파일과 이메일 중심의 Sniffing 기반 데이터 처리를 원칙으로 합니다.

## 5. 핵심 운영 철학 (Core Philosophy)

1. **Planning-First (기획 우위)**: 기획(Plan)과 구현(Execution)을 엄격히 분리합니다. 승인된 설계도(`plan.md`) 없이는 인공지능이 단 한 줄의 코드도 작성하지 못하게 하여 아키텍처의 주도권을 개발자가 유지합니다.

2. **Hybrid Intelligence (하이브리드 지능)**: `NotebookLM`을 통한 깊이 있는 도메인 리서치와 웹 서치를 통한 실시간 최신성을 결합하여 완벽한 판단 근거를 확보합니다.

3. **Engine Specialization (엔진 역할 분담)**: [ELITE SYNERGY TRIAD] 뼈대 개발 시 각 엔진의 고유 강점을 극대화하여 결합합니다.

    - **Google Gemini (Super Researcher)**: 압도적 컨텍스트를 활용한 방대한 데이터/문서 리서치 및 패턴 추출 전담.

    - **Claude 4.6 (System Architect & Lead Coder)**: 정교한 아키텍처 설계(Opus) 및 무결점 실무 코딩(Sonnet) 전담.

    - **GPT Latest (Manager & Action Verifier)**: 외부 도구 실행, 데이터 시각화 및 최종 논리 검토 전담.

4. **Multi-Engine Synergy (다중 엔진 시너지)**: API KEY 보유 현황에 따라 지능의 수준을 동적으로 최적화합니다.

    - **[SKELETON/FRAMEWORK DEV]**: API KEY 보유 시 무조건 **최고 성능 모델(Elite/Paid)**을 사용하여 아키텍처 설계와 정밀 코딩의 완결성을 확보합니다.

    - **[RELEASE/OUTPUT AGENTS]**: 등록된 키에 맞춰 최고 성능 모델을 사용하되, 키가 없는 엔진은 **최신 무료/보급형 모델 중 최고 성능**으로 자동 대체하여 중단 없는 진화와 업무 연속성을 보장합니다.

5. **Self-Evolution (자가 진화)**:

    - **[SKELETON/FRAMEWORK DEV]**: 최신 엔진(Gemini 3.1 Pro 등)이 출시되면 즉시 팩토리의 아키텍트 엔진으로 반영하여 지능의 최신성을 유지합니다.

    - **[RELEASE/OUTPUT AGENTS]**: 모든 에이전트와 스킬은 사용 경험을 통해 스스로 성장하며, 최신 엔진의 지능을 흡수하여 점진적으로 인간의 개입이 필요 없는 수준으로 진화합니다.

    - **[MODULAR PHILOSOPHY]**: 팩토리는 복잡한 로직을 마주할 때 스스로 '원자적 모듈화(Atomic Modularization)'를 제안하여 인풋 토큰 비용을 방어하고 코드 무결성을 유지합니다.

## 6. 개발 및 커뮤니케이션 (Development & Communication)

1. **Korean Native (한국어 원칙)**: 뼈대(Skeleton/Framework) 작업, 시스템 프롬프트 작성, 핵심 설계 문서 및 주석은 명확한 의도 전달과 유지보수를 위해 **반드시 한글로 작성**해야 합니다.
