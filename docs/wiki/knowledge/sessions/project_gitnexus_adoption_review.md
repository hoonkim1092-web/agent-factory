---
name: project_gitnexus_adoption_review
description: GitNexus(코드 그래프 도구) 도입 검토 — 사실 동결 + 다음 단계 Step 0 PoC
metadata: 
  node_type: memory
  type: project
  originSessionId: 6fe92d3f-2d85-4d55-b6a6-4f89866b490a
---

GitNexus = 코드베이스를 쿼리 가능한 지식 그래프로 만드는 도구. **2026-06-11 분석 완료, 도입 미실행.**

**확정 사실 (실측):**
- npm 패키지명은 **`gitnexus`** (v1.6.7) — 이전 논의 문서(`docs/codex_논의/2026-05-12-*`)의 `git-nexus`는 오기, 404 원인이었음.
- **Node.js** 기반(Tree-sitter + LadybugDB) → **Python 3.14 차단 무관**. Node v24.13.1 설치 확인, 즉시 실행 가능.
- 코드를 진짜 방향 그래프로 파싱: import/호출/상속/타입추론/교차파일 참조(신뢰도 점수). 14개 언어(Python 포함).
- 16개 MCP 도구. 핵심: impact(blast radius), context, query(BM25+시맨틱+RRF), detect_changes, rename, cypher.

**중복 분석 결론 (4개 AF 자산 대비):**
- `scripts/blast_radius.py` — 🟡 목표 중복이나 regex/path 룰 기반(死코드 아님, review-gate 핵심 안전게이트). GitNexus impact는 그 위 정밀 보강층, 대체 불가.
- `scripts/codebase_symbols.py` — 🟡 부분 중복. AST 평면 나열 → GitNexus가 상위호환(그래프 쿼리).
- `core/memory_system/graph_*` — 🟢 무중복. 런타임 episode(Problem-Cause-Solution) 그래프, wire-up 작동 중. 코드 구조 아님.
- `skills/graphify/` — 🔴 직접 대체. graphify는 死상태(미설치+Python 3.14 4중 차단+last_test_ok:false). GitNexus가 Node로 같은 일 수행.

**LLM Wiki/Obsidian과 관계**: 대체 아님, 보완. LLM Wiki 구성 중 `symbols.md`만 겹침(GitNexus 상위호환). blueprint/code-review mirror·open_items는 사람 서사라 GitNexus 불가. 레이어: L1 코드구조=GitNexus / L2 설계서사·L3 결정교훈=LLM Wiki / UI=Obsidian.

**다음 단계 = Step 0 PoC (미실행)**: 격리 임시폴더 복제 → `npx gitnexus@1.6.7 analyze` → 인덱싱 시간·DB생성·impact정확도 측정. ⚠️ analyze가 AGENTS.md/CLAUDE.md/hook 자동 덮어쓰기 위험 → AF 루트 직접 실행 금지, 격리 필수. 이후 Step1(wrapper)→Step2(opt-in env 통합)→Step3(graphify 폐기 결정)→Step4(MCP 사용자채널).

**산출물**: 회사 회의 논의용 문서 `docs/2026-06-11-gitnexus-code-intelligence-도입검토.md`(`1eed96ee`, AF 용어 제거한 일반 독자용). 사용자가 회사 RAG 논의와 합쳐 사용 예정. 관련: [[project_af_codebase_wiki_direction]].

## 관련
- [[code/symbols]]

