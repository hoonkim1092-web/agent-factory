---
title: Graphify 크로스 프로바이더 스킬 통합
date: 2026-04-22
status: Phase 0 — 사용자 답변 대기 (Q1~Q11)
owner: HOON-KIM
blocking: Python 3.14 미지원 (Graphify requires <3.14)
priority: 중 (토큰 비용 절감 목표)
cross_review_pending: true  # af-critic + af-cross-review 2병렬 실행 필요
---

# Graphify 크로스 프로바이더 스킬 통합

## 0. 한 줄 요약

폴더(코드+문서+이미지)를 지식그래프로 변환해 LLM 토큰을 최대 71.5× 절감한다는 오픈소스 스킬 **Graphify** (pip 패키지 `graphifyy`, MIT, GitHub ⭐32,604) 를 agent-factory에 통합. Claude Code·Codex·Gemini·Antigravity 등 14개 CLI 프로바이더를 이미 지원하므로 기능 복제 없이 **래퍼 스킬 + 운영 규약**만 추가하면 됨. 단, **Python 3.14 미지원**이라 별도 Python 3.13 환경 필요.

---

## 1. 목적

- **주요 목적**: 대화당 토큰 소모를 `/graphify` 슬래시 커맨드로 장기 절감
- **부차 목적**: Claude·Codex·Antigravity 공통 스킬 설치 경로 확립 (향후 다른 스킬 도입 시 참조 모델)
- **비목적**: agent-factory 내부 `core_memory`·`hound_librarian`·`warehouse/context-*` 교체 (공존 방침)

---

## 2. Graphify 실체 (v4 코드 실측)

| 항목 | 내용 | 출처 |
|------|------|------|
| **정체** | 폴더 → 지식그래프 변환기 (코드 AST + 문서·PDF·이미지 개념 추출 → NetworkX 그래프 + Leiden 클러스터링) | README.md |
| **PyPI 패키지** | `graphifyy` (더블 y) v0.4.27 | pyproject.toml |
| **설치** | `uv tool install graphifyy && graphify install` (권장)  / `pipx install graphifyy && graphify install` / `pip install graphifyy && graphify install` | README.md |
| **호출** | `/graphify .` (Claude Code), `$graphify .` (Codex) 슬래시 커맨드 | README.md |
| **출력** | `graphify-out/{graph.html, GRAPH_REPORT.md, graph.json, cache/}` | README.md |
| **토큰 효율** | 혼합 코퍼스 **71.5× 절감** (공식 주장), 소규모(~6 files)는 ~1× | README.md |
| **지원 프로바이더** | Claude Code, Codex, OpenCode, Cursor, **Gemini CLI**, Copilot CLI, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, **Google Antigravity**, VSCode (14종) | `graphify/__main__.py` |
| **Python 요구** | **`>=3.10,<3.14`** ← 블로킹 이슈 | pyproject.toml |
| **주요 의존성** | networkx, tree-sitter (22개 언어), Leiden(graspologic, `<3.13`만) | pyproject.toml |
| **선택 의존성** | mcp, neo4j, pdf(pypdf+html2text), watch(watchdog), office(python-docx+openpyxl), video(faster-whisper+yt-dlp) | pyproject.toml |
| **라이선스/규모** | MIT, ⭐32,604, default branch `v4` | GitHub API |
| **프라이버시** | 코드는 로컬 AST, 문서/이미지만 플랫폼 API 호출 (사용자 본인 키). 텔레메트리 없음 | README.md |
| **작동 단계** | 1) 파이썬 탐지·설치 2) 파일 타입 감지 3) 병렬 추출(AST+subagent) 4) 그래프 구성+클러스터링 5) 클러스터 라벨링 6) HTML/Obsidian/MD 출력 7) (옵션) Neo4j/SVG 8) 토큰 효율 벤치마크 9) manifest 저장 | skill.md |
| **관계 태그** | `EXTRACTED` (명시) / `INFERRED` (추론, confidence 점수) / `AMBIGUOUS` (불확실) | skill.md |

### 2-1. 주요 명령

```bash
/graphify .                               # 현재 디렉터리 그래프화
/graphify ./raw --mode deep               # 공격적 추론
/graphify ./raw --update                  # 증분 갱신
/graphify ./raw --watch                   # 파일 변경 시 자동 sync
/graphify ./raw --wiki                    # 검색 가능 wiki 생성
/graphify query "connect auth to response?"
/graphify path "DigestAuth" "Response"
/graphify explain "X"
/graphify add <url>                        # 외부 소스 병합
```

### 2-2. 플랫폼별 설치 경로 (`graphify/__main__.py` 실측)

| 플랫폼 | Graphify 설치 경로 | 영향 범위 | 커맨드 |
|--------|-------------------|----------|--------|
| **Claude Code** | `~/.claude/skills/graphify/SKILL.md` | 🌐 **사용자 전역** | `graphify install` |
| **Cursor** | `.cursor/rules/graphify.mdc` | 프로젝트 로컬 | `graphify cursor install` |
| **Copilot CLI** | `~/.copilot/skills/graphify/SKILL.md` | 사용자 전역 | `graphify install --platform copilot` |
| **Codex** | `.agents/codex/` 등 | 플랫폼별 | `graphify install --platform codex` |
| **Gemini CLI** | `~/.gemini/skills/graphify/` (`~/.agents/` on Windows) | 사용자 전역 | `graphify install --platform gemini` |
| **Google Antigravity** | 전용 커맨드 | 확인 필요 | `graphify antigravity install` |
| **OpenCode** | `.opencode/plugins/graphify.js` | 프로젝트 로컬 | `graphify install --platform opencode` |
| **Kiro** | `.kiro/steering/graphify.md` | 프로젝트 로컬 | `graphify install --platform kiro` |

### 2-3. "Always-On" 주입 대상 (설치 시 자동 수정되는 파일)

- `CLAUDE.md` — "read `graphify-out/GRAPH_REPORT.md` before answering" 섹션 append
- `AGENTS.md` — 유사 섹션 append
- `GEMINI.md` — 유사 섹션 append
- `.claude/settings.json` — **PreToolUse** hook 등록
- `.opencode/plugins/graphify.js` — `tool.execute.before` hook
- `.cursor/rules/graphify.mdc` — `alwaysApply` directive
- `.kiro/steering/graphify.md` — always-on steering

### 2-4. Git hook 동작 (`graphify/hooks.py` 실측)

- 대상: **`core.hooksPath`를 존중**하므로 agent-factory의 `.githooks/` 에 쓸 예정
- 추가 훅: `post-commit` + `post-checkout` 두 종류만
- 마커: `# graphify-hook-start` / `# graphify-hook-end` (기존 파일에 append, 제거 시 regex로 구간 삭제)
- 가드: rebase·merge·cherry-pick 중에는 실행 skip, post-checkout은 브랜치 스위치 시에만
- 파이썬 탐지: graphify shebang → `python3` → `python` 순, allowlist 검증

---

## 3. 치명적 블로킹

### 3-1. Python 3.14 미지원 🚨

- **Graphify**: `requires-python = ">=3.10,<3.14"`
- **현재 사용자**: `Python 3.14.3` (`C:\Users\HOON\AppData\Local\Python\bin\python.exe`)
- **결과**: `pip install graphifyy` 실패

**해결 옵션**:

| 옵션 | 장점 | 단점 | 추천 |
|------|------|------|------|
| A. pipx + Python 3.13 별도 | 격리, agent-factory 3.14 유지 | 3.13 수동 설치 필요 |  |
| **B. uv tool install graphifyy --python 3.13** | uv가 3.13 자동 다운로드, 격리, Windows 친화 | uv 미설치 시 1회 설치 | ⭐ |
| C. Graphify 3.14 지원 대기 | 작업 無 | 릴리스 불확실 |  |

**추천**: B. 설치 스크립트:
```bash
winget install --id=astral-sh.uv -e      # uv 설치 (1회)
uv tool install graphifyy --python 3.13  # Graphify 설치
graphify --version                        # 확인
```

---

## 4. 충돌·시너지 매트릭스 (v4 실측 기반)

### 4-1. 직접 충돌 / 주의

| agent-factory 자산 | 충돌 수준 | 원인 | 대응 |
|--------------------|----------|------|------|
| `.githooks/` (core.hooksPath) | **중간** | Graphify가 post-commit·post-checkout에 append | 마커 기반 공존. 설치 후 diff 검토 |
| `CLAUDE.md` | **중간** | 자동 섹션 append — agent-factory는 엄격히 관리 | 설치 전 백업, 설치 후 diff 수동 검토 |
| `.claude/settings.json` | **낮음** | Graphify는 PreToolUse만 추가. agent-factory는 SessionStart·UserPromptSubmit·PreCompact·Stop·SessionEnd 사용 중 (다른 이벤트) | 그대로 공존 |
| `.claude/settings.local.json` | 없음 | local 파일과 무관 | — |
| `AGENTS.md` | 낮음 | agent-factory 루트에 없음 (`.a/AGENTS.md`·`syncCompyne/AGENTS.md`만 존재) | 설치 후 신규 파일 확인 |
| `GEMINI.md` | 낮음 | 루트에 없음 (`.a/GEMINI.md`만) | 설치 후 신규 파일 확인 |

### 4-2. 기존 스킬과의 관계

| 자산 | 판정 | 근거 |
|------|------|------|
| `skills/core_memory` | **공존** | 키-값 기억 vs 코드·문서 구조 그래프 (목적 다름) |
| `skills/hound_librarian` | **시너지 (강함)** | `graphify add <url>` 로 Tavily 수집 결과 병합 가능 |
| `skills/_external_cache/` | **시너지 (강함)** | 거의 빈 디렉터리 — `graphify-out/` 을 심볼릭 링크 후보 |
| `skills/code_review_guide` | **시너지 (강함)** | `GRAPH_REPORT.md` 를 리뷰 입력으로 활용 |
| `skills/ai_funnel_routing` | **시너지** | 쿼리 복잡도에 따라 그래프 vs 원문 라우팅 |
| `skills/hash_edit`·`hashline_edit` | **시너지** | SHA256 증분 캐시 철학 공유 |
| `skills/warehouse/context-*` (7종) | **영향 없음** | 대부분 legacy, 봉인됨 |
| `af-critic` / `af-cross-review` | **시너지** | 그래프 기반 Blast Radius 분석 |
| `Master_Blueprint.md` | 영향 (문서화) | §3·§10·§12 업데이트 필요 |

### 4-3. 설치 위치 이슈

- **Claude Code skill = 사용자 전역** (`~/.claude/skills/graphify/`) → agent-factory 외 **모든 프로젝트**에서 `/graphify` 노출
- 이걸 원하는지 확정 필요 (§6 Q10)

---

## 5. 적용 계획 (11 Phase)

```
[Phase 0] 사용자 답변 확정  ← 현재 여기
  §6 Q1~Q11 응답 수집

[Phase 1] Python 3.13 환경 준비  ← Python 3.14 블로킹 해결
  winget install --id=astral-sh.uv -e
  uv tool install graphifyy --python 3.13
  graphify --version    # 0.4.27 확인

[Phase 2] 본 설계문서 갱신 + 최종본 고정
  Q 응답 반영, status: Phase 2 완료

[Phase 3] 교차검증 (af-critic + af-cross-review 2병렬)
  CLAUDE.md 규칙 필수. BLOCK 시 수정 후 재검증

[Phase 4] 설치 전 백업
  git status → clean 상태 확인 (또는 stash)
  cp CLAUDE.md CLAUDE.md.backup
  cp .claude/settings.local.json .claude/settings.local.json.backup
  ls .githooks/ > /tmp/hooks-before.txt
  tar cf /tmp/af-pre-graphify-backup.tar CLAUDE.md .claude/ .githooks/

[Phase 5] Graphify 설치 (플랫폼별, 한 개씩 diff 검토)
  graphify install                        # Claude Code (전역)
  git diff CLAUDE.md                      # 섹션 확인
  graphify install --platform codex
  graphify antigravity install
  # 각 단계 후 git diff로 변경 파일 확인

[Phase 6] 래퍼 스킬 등록 (agent-factory 내부)
  skills/graphify/
    ├── meta.yaml       # id, name, version, capabilities
    ├── skill.py        # subprocess.run(["graphify", ...])
    └── SKILL.md        # agent-factory 내부 사용 가이드
  skills/registry.yaml 에 graphify 엔트리 추가

[Phase 7] 운영 규약
  .graphifyignore 생성:
    - node_modules/
    - dist/
    - runs/
    - .a/
    - projects/global_hoon_main/data/
    - tests/_tmp/
    - build/
    - *.zip
  .gitignore 에 graphify-out/ 추가
  CLAUDE.md 변경분 최종 정리

[Phase 8] 초기 그래프 빌드 (좁은 범위 → 전체)
  /graphify skills           # skills/ 33개만 먼저
  → graph.html 시각 확인
  → GRAPH_REPORT.md 검수 (God Nodes, Surprising Connections)
  이상 없으면:
  /graphify .                # 전체 agent-factory

[Phase 9] 기존 스킬 연결 (선택)
  - code_review_guide 가 GRAPH_REPORT.md 참조하도록 수정
  - af-critic 에 "그래프 영향 범위 확인" 규칙 추가
  - hound_librarian + `graphify add <url>` 파이프 연결

[Phase 10] Master_Blueprint.md 업데이트
  §0 빠른 참조 테이블에 graphify 추가
  §3 에 graphify 서브시스템 섹션
  §10 Blast Radius에 graphify-out/ 영향 기록
  §12 변경 이력 (2026-04-22 Graphify v0.4.27 통합)

[Phase 11] 커밋
  af-test-runner → af-critic → af-cross-review 3-gate 통과
  커밋 메시지: "feat(graphify): cross-provider knowledge graph skill v0.4.27 통합"
```

---

## 6. 사용자 답변 필요 항목 (Q1~Q11)

### 6-1. 결정적 (블로킹)

- **Q1. 브랜치**: v3 vs **v4 (default, 추천)**
- **Q2. LLM 키**: 기존 Anthropic/OpenAI 키 재사용 vs 별도 `GRAPHIFY_API_KEY`
- **Q9. Python 런타임**: A/B/C (§3-1) → **B (uv + 3.13) 추천**

### 6-2. 설치 범위

- **Q3. Python 환경**: → Q9로 통합됨 (uv 격리 tool)
- **Q4. 첫 대상**: `skills/` only / 전체 / 수동 지정
- **Q10. Claude Code skill**: **사용자 전역**(`~/.claude/skills/`) 허용 vs agent-factory only 로 제한 (후자는 `.claude/skills/` 프로젝트 로컬 경로 수동 배치 필요)

### 6-3. 운영 규약

- **Q5. `graphify-out/` 위치**: 프로젝트 루트 (.gitignore) / `skills/_external_cache/graphify/` / `~/.graphify/`
- **Q6. `--watch` 모드**: 자동 / 수동 갱신만
- **Q7. 기존 스킬 연결**:
  - code_review_guide 가 GRAPH_REPORT.md 참조하도록 수정 여부
  - `_external_cache/` 전용 전환 여부
- **Q8. `.graphifyignore` 제외 경로**: 초안 — `node_modules/`, `dist/`, `runs/`, `.a/`, `projects/global_hoon_main/data/`, `tests/_tmp/`, `build/`, `*.zip`. 추가/제외?
- **Q11. CLAUDE.md/AGENTS.md/GEMINI.md 자동 주입**: 허용 / 수동 diff 검토 후 반영 (추천)

### 6-4. 제 권장 default (빠른 진행 시)

| Q | Default |
|---|---------|
| Q1 | v4 |
| Q2 | 기존 Anthropic 키 재사용 |
| Q4 | `skills/` 먼저 → 이상 없으면 전체 |
| Q5 | 프로젝트 루트, .gitignore |
| Q6 | 수동 (`--watch` 미사용) |
| Q7 | 연결 일단 No (Phase 9 에서 분리) |
| Q8 | 위 초안 그대로 |
| Q9 | B (uv + 3.13) |
| Q10 | 전역 설치 허용 |
| Q11 | 수동 diff 검토 후 반영 |

---

## 7. 영향 범위 체크리스트

- [ ] `.githooks/post-commit` / `post-checkout` — Graphify 마커 섹션 추가 (diff 필요)
- [ ] `CLAUDE.md` — "GRAPH_REPORT.md 참조" 섹션 추가 (수동 검토)
- [ ] `.claude/settings.json` — PreToolUse hook 신규 (agent-factory는 미사용이라 안전)
- [ ] `.gitignore` — `graphify-out/` 추가
- [ ] `.graphifyignore` — 신규 파일
- [ ] `skills/graphify/` — 래퍼 스킬 신규
- [ ] `skills/registry.yaml` — graphify 엔트리 추가
- [ ] `Master_Blueprint.md` — §0·§3·§10·§12 업데이트
- [ ] `docs/features/2026-04-22-graphify-integration.md` — 본 문서 (status 갱신)
- [ ] `pyproject.toml` — 영향 없음 (Graphify는 별도 uv tool 환경)
- [ ] `af` / `cdx` / `agt` / `lm` CLI — 영향 없음 (슬래시 커맨드는 각 CLI 네이티브 처리)

---

## 8. 다음 세션 재개 가이드 (집에서 작업 시)

### 8-1. 현재 상태

- **Phase 0 진행 중** — §6의 Q1~Q11 중 어느 것도 확정 안 됨
- 설계문서(본 파일)만 작성됨
- **교차검증 미실행** — af-critic + af-cross-review 2병렬 필요 (CLAUDE.md 규칙)

### 8-2. 재개 시 할 일 순서

```bash
# 1. 본 문서 읽고 Q1~Q11 답 결정
code docs/features/2026-04-22-graphify-integration.md

# 2. 교차검증 실행 (필수, 본 문서 수정 전에)
#    Claude Code에서: af-critic + af-cross-review 2병렬 실행 요청

# 3. 검증 BLOCK 없으면 Phase 1 실행
winget install --id=astral-sh.uv -e
uv tool install graphifyy --python 3.13
graphify --version

# 4. Phase 4 백업 후 Phase 5 설치
#    각 단계마다 git diff로 변경 확인

# 5. Phase 6 래퍼 스킬 작성 → Phase 7~11 진행
```

### 8-3. 주의사항 (집에서 놓치면 후회할 것)

1. **Python 3.14 문제**: agent-factory 메인 환경은 그대로 두고 uv tool 로 격리. `pip install graphifyy` 직접 실행 금지.
2. **전역 설치 경고**: `graphify install` (Claude) 는 `~/.claude/skills/` 전역 설치. 집 PC에도 동일하게 깔리면 모든 프로젝트에 `/graphify` 뜸.
3. **CLAUDE.md 자동 주입**: 설치 후 반드시 `git diff CLAUDE.md` 확인. agent-factory 규칙과 충돌 시 수동 정리.
4. **graphify-out/ 용량**: 큰 레포에서는 수백 MB ~ 수 GB 가능. `.gitignore` 잊지 말 것.
5. **토큰 절감 기대치 조정**: 소규모 프로젝트는 ~1× (절감 효과 없음). agent-factory 현 규모에서 실제 효과는 측정 필요 (`graphify` 자체 벤치마크 기능 있음).
6. **첫 `/graphify .` 비용**: 전체 agent-factory + 문서 + 이미지 포함 시 API 호출 비용 발생. 처음에는 `skills/` 만 해보고 비용 감 잡을 것.

---

## 9. 참고 링크

- GitHub: https://github.com/safishamsi/graphify (v4 default)
- PyPI: https://pypi.org/project/graphifyy/ (v0.4.27)
- README (ko): https://github.com/safishamsi/graphify/blob/v3/README.ko-KR.md (사용자 제공)
- README (en, v4): https://github.com/safishamsi/graphify/blob/v4/README.md
- 공식 사이트: https://graphify.net/kr/ (봇 차단 403, WebFetch 불가)

---

## 10. 변경 이력

| 날짜 | 버전 | 내용 | 작성자 |
|------|------|------|--------|
| 2026-04-22 | 0.1 | 초안 작성 (Phase 0). v4 실측 기반 분석, 블로킹 1건 + 충돌 3건 + 시너지 5건 도출. 사용자 답변(Q1~Q11) 대기. | HOON (via Claude Opus 4.7) |
