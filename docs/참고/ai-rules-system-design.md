# Universal AI Rules System 설계 문서

> **목적**: Karpathy의 LLM 코딩 4원칙을 Claude, ChatGPT, Gemini에서 일관되게 적용하기 위한 단일 규칙 관리 시스템
> **작성일**: 2026-05-04
> **버전**: v1.0

---

## 1. 개요 (Overview)

### 1.1 문제 정의
AI 코딩/작업 도구가 늘어나면서 동일한 행동 규칙을 각 도구에 따로 등록해야 하는 비효율이 발생한다. 현재 사용자는 다음과 같은 페인 포인트를 가진다.

- 같은 규칙을 Claude, ChatGPT, Gemini에 **중복 입력** 필요
- 규칙을 수정할 때마다 **3곳 이상에서 수동 동기화**
- 도구별 메커니즘이 달라 (`Skill` / `Custom Instructions` / `Gem`) **개념 혼란**
- 새 도구 도입 시 **온보딩 비용** 증가

### 1.2 목표 (Goals)
- **G1.** 단일 마스터 파일에서 모든 AI 도구의 규칙을 관리한다.
- **G2.** 코딩 환경(Claude Code, Cursor 등)은 **자동 동기화**된다.
- **G3.** 채팅 환경(웹 UI)은 **반자동 배포 절차**를 표준화한다.
- **G4.** 규칙은 **도구 중립적인 마크다운**으로 작성한다.
- **G5.** 새 도구가 추가되어도 **마스터 파일 수정 없이** 어댑터만 추가하면 된다.

### 1.3 비목표 (Non-goals)
- 도구 간 응답 품질의 완전한 동일화 (모델 차이는 수용)
- 모든 도구의 모든 기능을 추상화 (Tool 호출, MCP 등은 도구별로 다름)
- 실시간 양방향 동기화 (단방향 push만 지원)

---

## 2. 배경 (Background)

### 2.1 Karpathy 4원칙 요약
forrestchang/andrej-karpathy-skills 저장소에서 정리된 LLM 코딩 행동 규칙.

| # | 원칙 | 핵심 |
|---|------|------|
| 1 | Think Before Coding | 가정하지 말고 모호하면 묻기 |
| 2 | Simplicity First | 요청하지 않은 기능/추상화 금지 |
| 3 | Surgical Changes | 요청한 라인만 수정, 인접 코드 건드리지 않기 |
| 4 | Goal-Driven Execution | 명령형 → 검증 가능한 목표로 변환 |

### 2.2 도구별 메커니즘 비교

| 도구 | 슬롯 이름 | 위치 | 자동 로딩 |
|------|----------|------|----------|
| Claude Code | `CLAUDE.md` / Skill | 프로젝트 루트 / `~/.claude/skills/` | ✅ |
| Claude.ai | Project Instructions | 웹 UI | ✅ (프로젝트 내) |
| ChatGPT | Custom Instructions / Project Instructions | 웹 UI | ✅ |
| Gemini | Gem System Instructions / Saved Info | 웹 UI | ✅ (Gem 내) |
| Cursor | `.cursor/rules/*.mdc` | 프로젝트 | ✅ |
| 공통 표준 | `AGENTS.md` | 프로젝트 루트 | 도구별 상이 |

### 2.3 핵심 통찰
도구마다 슬롯의 **이름과 등록 방식**은 다르지만, **콘텐츠는 평문 마크다운**이다. 따라서 중앙 집중식 콘텐츠 관리 + 도구별 배포 어댑터 구조가 가능하다.

---

## 3. 아키텍처 (Architecture)

### 3.1 전체 구조

```
                    ┌─────────────────────────────────┐
                    │   Master Source of Truth        │
                    │   ~/ai-rules/principles.md      │
                    └─────────────┬───────────────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
        [자동 배포 영역]    [반자동 배포 영역]   [수동 등록 영역]
                │                 │                 │
        ┌───────┴───────┐    ┌────┴─────┐    ┌──────┴──────┐
        │ AGENTS.md     │    │ 동기화    │    │ 웹 UI       │
        │ CLAUDE.md     │    │ 스크립트  │    │ Project/Gem │
        │ .cursor/rules │    │          │    │ 등록        │
        └───────────────┘    └──────────┘    └─────────────┘
                │                 │                 │
                ▼                 ▼                 ▼
        Claude Code,        ChatGPT/Gemini    Claude.ai,
        Cursor, Aider       Project 갱신       ChatGPT, Gemini
```

### 3.2 핵심 컴포넌트

**(a) 마스터 파일** (`principles.md`)
- 단일 진실 공급원(Single Source of Truth)
- 도구 중립적 마크다운
- 섹션별 태그로 도구별 필터링 가능

**(b) 어댑터 레이어**
- 코딩용: 심볼릭 링크 또는 빌드 스크립트
- 채팅용: 클립보드 복사 헬퍼 + 등록 체크리스트

**(c) 버전 관리**
- Git으로 마스터 파일 추적
- 변경 시 CHANGELOG에 기록
- 채팅 환경 동기화 일자 기록

---

## 4. 상세 설계 (Detailed Design)

### 4.1 마스터 파일 구조

```markdown
# AI Behavior Rules
<!-- version: 1.0.0 | last-updated: 2026-05-04 -->

## [CORE] 핵심 원칙 (모든 도구 공통)
1. Think Before Coding
2. Simplicity First
3. Surgical Changes
4. Goal-Driven Execution

## [CODING] 코딩 환경 전용 규칙
- 테스트 우선 작성
- 기존 패턴 따르기
- ...

## [CHAT] 채팅 환경 전용 규칙
- 길이 제한 가이드
- 답변 톤 ...

## [PROJECT-X] 프로젝트별 규칙
- 이 섹션은 프로젝트마다 다르게 추가
```

**섹션 태그 규칙**: `[CORE]`, `[CODING]`, `[CHAT]`, `[PROJECT-*]`로 구분하여 어댑터가 필요한 섹션만 추출 가능.

### 4.2 파일 시스템 레이아웃

```
~/ai-rules/
├── principles.md              # 마스터 파일
├── CHANGELOG.md               # 변경 이력
├── adapters/
│   ├── codeing-deploy.sh      # 코딩 환경 자동 배포
│   ├── chat-clipboard.sh      # 채팅 환경 클립보드 복사
│   └── extract-section.py     # 섹션별 추출 스크립트
└── sync-log/
    ├── chatgpt.log            # 마지막 동기화 일자
    ├── claude-web.log
    └── gemini.log
```

### 4.3 어댑터 동작 명세

**(a) 코딩용 자동 배포** (`coding-deploy.sh`)
```
입력: 프로젝트 경로
처리:
  1. principles.md에서 [CORE] + [CODING] 섹션 추출
  2. 프로젝트 루트에 AGENTS.md 심볼릭 링크 생성
  3. CLAUDE.md, .cursor/rules/karpathy.mdc도 동일하게 링크
출력: 프로젝트가 마스터 파일을 참조하도록 설정 완료
```

**(b) 채팅용 클립보드 헬퍼** (`chat-clipboard.sh`)
```
입력: 도구 이름 (claude-web | chatgpt | gemini)
처리:
  1. principles.md에서 [CORE] + [CHAT] 섹션 추출
  2. 도구별 헤더/포맷 변환 (예: ChatGPT는 마크다운 그대로, Gemini는 인스트럭션 형식)
  3. 시스템 클립보드에 복사
  4. sync-log에 타임스탬프 기록
출력: 사용자가 해당 도구의 등록 화면에 붙여넣기만 하면 됨
```

### 4.4 도구별 등록 위치

| 도구 | 등록 경로 | 자동화 가능? |
|------|----------|------------|
| Claude Code | `<project>/CLAUDE.md` (심볼릭 링크) | ✅ 자동 |
| Claude.ai | Projects → 우측 패널 → Project Instructions | ❌ 수동 (UI) |
| ChatGPT | Settings → Personalization → Custom Instructions | ❌ 수동 (UI) |
| ChatGPT Project | Project → Instructions 필드 | ❌ 수동 (UI) |
| Gemini | Gems → 새 Gem → System Instructions | ❌ 수동 (UI) |
| Cursor | `<project>/.cursor/rules/karpathy.mdc` (심볼릭 링크) | ✅ 자동 |

---

## 5. 구현 단계 (Implementation Phases)

### Phase 1 — MVP (1일 작업)
**목표**: 마스터 파일 + 코딩 환경 자동 배포만 우선 구축

- [ ] `~/ai-rules/` 디렉토리 생성
- [ ] `principles.md` 작성 (Karpathy 4원칙 + 개인 추가 규칙)
- [ ] Git 저장소로 초기화
- [ ] 1개 프로젝트에서 심볼릭 링크 테스트 (`AGENTS.md`)
- [ ] Claude Code에서 의도대로 작동하는지 검증

**검증 기준**: Claude Code 세션에서 모호한 요청을 했을 때 가정 대신 질문이 돌아오는지 확인.

### Phase 2 — 채팅 환경 통합 (반나절)
**목표**: 3개 채팅 도구에 1회 등록

- [ ] Claude.ai에 "AI Rules" Project 생성 후 등록
- [ ] ChatGPT에 동일 Project 또는 Custom Instructions 등록
- [ ] Gemini에 "AI Rules" Gem 생성 후 등록
- [ ] 각 도구에서 동일한 테스트 프롬프트로 응답 비교
- [ ] sync-log에 등록 일자 기록

**검증 기준**: 동일한 모호한 질문에 대해 세 도구 모두 가정 대신 질문하는지 확인.

### Phase 3 — 자동화 강화 (선택적)
**목표**: 동기화 비용 최소화

- [ ] `coding-deploy.sh` 작성 (모든 프로젝트에 일괄 적용)
- [ ] `chat-clipboard.sh` 작성 (도구별 클립보드 복사)
- [ ] Git pre-commit hook으로 CHANGELOG 자동 업데이트
- [ ] (옵션) ChatGPT/Gemini API 사용 시 자동 주입 래퍼 구현

### Phase 4 — 운영 (지속)
- 분기별로 마스터 파일 검토 및 업데이트
- 새 AI 도구 출시 시 어댑터 추가
- 실제 사용에서 발견한 페인 포인트를 규칙에 반영

---

## 6. 운영 및 유지보수 (Operations)

### 6.1 업데이트 워크플로우
```
1. principles.md 수정
2. CHANGELOG.md에 변경 사항 기록
3. git commit & push
4. (자동) 코딩 환경: 다음 세션부터 새 규칙 적용
5. (수동) 채팅 환경: chat-clipboard.sh 실행 → 각 도구 UI에 붙여넣기
6. sync-log 업데이트
```

### 6.2 모니터링 지표
- 마지막 채팅 환경 동기화 일자 (도구별)
- 마스터 파일 변경 후 동기화까지 걸린 시간
- 도구별 규칙 위반 사례 (주관적 기록)

### 6.3 장애 대응
| 증상 | 원인 후보 | 조치 |
|------|---------|------|
| Claude Code가 규칙 무시 | 심볼릭 링크 깨짐 | `ls -la AGENTS.md`로 확인 후 재생성 |
| ChatGPT가 다른 답변 | 동기화 누락 | sync-log 확인, 재등록 |
| Gemini Gem이 비활성화 | 세션에서 Gem 미선택 | 매 세션 Gem 선택 확인 |

---

## 7. 리스크 및 대응 (Risks)

| 리스크 | 영향도 | 대응 |
|--------|-------|------|
| 도구별 시스템 프롬프트 길이 제한 | 중 | 섹션별 추출로 핵심만 전달, [CORE] 우선 |
| 채팅 환경 수동 동기화 누락 | 중 | sync-log + 분기별 리마인더 |
| Karpathy 원칙이 비코딩 작업에 부적합 | 낮 | [CHAT] 섹션에 별도 규칙으로 분리 |
| 도구 UI 변경으로 등록 위치 이동 | 낮 | 분기별 매뉴얼 업데이트 |
| 마스터 파일 손실 | 높 | Git remote + 클라우드 백업 |

---

## 8. 향후 확장 (Future Work)

- **(F1)** Anthropic API / OpenAI API / Gemini API 사용 시 시스템 프롬프트 자동 주입 라이브러리
- **(F2)** 프로젝트 컨텍스트 자동 감지 (예: Python 프로젝트면 PEP 규칙 자동 추가)
- **(F3)** 팀 단위 공유 — 마스터 파일을 팀 Git 저장소에 두고 멤버들이 fork
- **(F4)** A/B 테스트 — 규칙 버전 변경 시 응답 품질 비교
- **(F5)** MCP 서버화 — AI가 스스로 규칙을 조회/제안하는 구조

---

## 9. 결정 사항 요약 (Decisions)

| ID | 결정 | 근거 |
|----|------|------|
| D1 | "Skill"이 아닌 "마크다운 + 어댑터" 구조 채택 | Skill은 Claude 전용, 이식성 0 |
| D2 | 코딩은 자동, 채팅은 반자동 분리 | 채팅 도구는 API 자동화 어려움 |
| D3 | AGENTS.md를 코딩 환경 표준으로 사용 | 다도구 호환성 가장 높음 |
| D4 | 단일 마스터 파일 + 섹션 태그 | 다중 파일은 동기화 복잡도 증가 |
| D5 | Git 기반 버전 관리 | 변경 추적 + 백업 동시 해결 |

---

## 10. 부록 (Appendix)

### A. 참고 자료
- forrestchang/andrej-karpathy-skills GitHub 저장소
- Andrej Karpathy의 X 게시물 (2026-01-26)
- AGENTS.md 표준 (다양한 코딩 에이전트 공통 컨벤션)

### B. 용어집
- **Single Source of Truth (SSoT)**: 단일 진실 공급원, 데이터/규칙의 정본이 한 곳에만 존재
- **Adapter**: 마스터 파일을 도구별 형식으로 변환하는 계층
- **Symbolic Link**: 다른 파일을 가리키는 가상 파일 (변경이 자동 반영됨)

### C. 다음 액션
이 설계 문서를 승인하면 다음 산출물을 순서대로 생성한다.
1. `principles.md` 마스터 파일 (한국어 / 영문 버전)
2. `coding-deploy.sh` 스크립트
3. `chat-clipboard.sh` 스크립트
4. 각 채팅 도구 등록 가이드 (스크린샷 포함)
