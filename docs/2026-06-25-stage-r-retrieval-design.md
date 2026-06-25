# STAGE R (Retrieval) 상세 설계 — `af knowledge search`

- **Status**: Draft
- **작성일**: 2026-06-25
- **모델**: Opus 4.8 (설계)
- **부모 설계**: `docs/2026-06-23-knowledge-library-evolution-design.md` §13.2 (D13 retrieval 일급화) — 본 문서는 그 스테이지의 **상세 설계**다. 부모가 동결한 원칙(결정론 우선·임베딩 보조·read-only·bounded)을 구현 수준으로 구체화한다.
- **한 줄 요약**: vault(`docs/wiki/knowledge/`)에 쌓인 증류 노트를, **task 텍스트 또는 변경 파일 집합**으로 검색해 관련 결정·교훈·정밀참조 노트를 **bounded·read-only**로 인출하는 `af knowledge search` 명령. 임베딩·외부 프로바이더 의존 0의 순수 Python 결정론 엔진.

---

## §0 이 문서가 동결하는 결정

| # | 결정 | 근거 (위치) |
|---|------|------------|
| R-D1 | **MVP = 명령어 하나** (`af knowledge search`). 세션시작 자동주입은 **연기**(별도 트랙) | §1.3 — session-start 흐름 변경은 위험·테스트 부담, 사용자 확정(2026-06-25) |
| R-D2 | **결정론 전용 MVP** — 임베딩(`document_index.py`/Gemini) 미배선, 보조 seam만 | §3.1 — 부모 §13.2 "결정론 우선", 멀티OS/프로바이더·크로스PC 재현성 |
| R-D3 | **2개 질의 모드**: `--query`(키워드) + `--files`/`--diff`(변경파일 exact-match) | §3.2 — 정밀참조 exact-match가 S2-3 100% precision 신호 |
| R-D4 | **관용적 frontmatter 파싱** — KnowledgeNote/레거시 memory/무-frontmatter 3종 모두 수용 | §3.3 — vault 117파일이 3종 혼재(실측) |
| R-D5 | **read-only·advisory** — write 경로 0. 출력 = 랭킹된 노트 셋(사람 표 + `--json`) | §3.4 — 부모 INV(원장 비오염), 토큰절약 목적 |

---

## §1 문제 정의 & 목표

### 1.1 목표
> 누적된 증류 노트를, **지금 하는 작업**(task 텍스트 또는 변경 파일)에 맞는 **작은 조각만** 꺼내, 결정·교훈·연관코드 참조를 컨텍스트에 넣을 수 있게 한다. 토큰 절약의 레버는 *축적*이 아니라 *검색*(부모 §13.2).

### 1.2 해결할 통증
- **PR1 — 죽은 아카이브**: STAGE 0~2로 노트를 **저장**만 하고 *꺼내는* 경로가 없음. 증류 노트가 써놓고 안 읽히는 고아 아카이브(NEXT_STEPS 2026-06-24 진단: "retrieval 없어 현재 고아 아카이브").
- **PR2 — 통째 주입 = 토큰 폭증**: 노트 전체를 컨텍스트에 넣으면 토큰이 *늘어남*. task에 맞는 bounded 셋만 인출해야 절약.

### 1.3 비목표 (만들지 않을 것)
- **세션시작 자동주입** (R-D1 연기). session-start hook/resume_brief 변경 = 별도 트랙.
- **임베딩 semantic 검색** (R-D2). `document_index.py` 보조 seam만, MVP 미배선.
- **노트 생성/수정/삭제** — STAGE R은 read-only. 쓰기는 STAGE 2(증류)/6(다이어트) 소관.
- **vault 재인덱싱 캐시 파일** — 117파일 규모는 매 호출 full-scan으로 충분(§3.5). 인덱스 DB 신설 = 과설계.

---

## §2 Baseline — 실제 코드 현황 (검증됨 2026-06-25)

> 추측 baseline 금지(`feedback_analysis_doc_baseline_must_be_real_code`). 전수 탐색으로 확인한 사실만.

### 2.1 노트 스키마 & 파서 — 존재 (`core/knowledge/note.py`)
- `KnowledgeNote` dataclass(`:140`): `id, type, title, body, author, source_machine, created_commit, created_at, scope, visibility, links`. 타입 SSOT.
- `from_md(text)`(`:172`): frontmatter(`---\n…\n---\n`) 파싱, CRLF 정규화, JSON 스칼라 디코딩(비-JSON 폴백 `:190`). **단 KnowledgeNote 전용 포맷 가정** — 레거시/무-frontmatter엔 부적합 → 검색은 관용 파서 필요(§3.3).
- 헬퍼: `_git`(`:68`)·`_short_commit`·`_git_author`. `make_id`(`:122`)·`new_note`.

### 2.2 정밀참조 추출기 — 존재·재사용 핵심 (`core/knowledge/distill.py`)
- `extract_precise_refs(text)`(`:80`, 시그니처 `(text: str) -> list[str]`): 정규식 3종으로 verbatim 추출(중복제거):
  - INV명: `\bINV-[A-Za-z0-9]+\b`
  - file:line: `(?:[\w.\-]+[/\\])*[\w.\-]+\.[A-Za-z]{1,6}:\d+`
  - commit: `\b(?=[0-9a-f]*[0-9])[0-9a-f]{7,40}\b`
- `mask_secrets`(`:52`). → **검색 인덱서가 이 정규식을 재사용**해 각 노트 본문에서 참조를 추출(SSOT, 재구현 금지).

### 2.3 vault 실제 구조 — 117파일·frontmatter 3종 혼재 (실측)
- `docs/wiki/knowledge/` = **117 .md** (검증 2026-06-25): `sessions/`(61)·`patterns/`(49)·`concepts/`(2)·`session/`(5, 신규 KnowledgeNote 포맷, `DESKTOP-*` 파일명).
- **frontmatter 3종**:
  1. **신규 KnowledgeNote**(`session/`): `id/type/title/author/created_commit/created_at/...`. 본문에 `## 정밀 참조 (verbatim, INV-K5)` 섹션.
  2. **레거시 memory**(`sessions/`·`patterns/`): `name/description/metadata.{node_type,type}`.
  3. **무-frontmatter**(`concepts/` 일부): 순수 마크다운.
- `links: []`는 사실상 항상 비어 있음 → 링크 필드 의존 금지. 교차참조는 본문 `[[wikilink]]`.
- 인덱스 DB/sqlite/json **없음** — loose 마크다운만. MOC.md(`docs/wiki/MOC.md`)는 손유지 네비게이션.

### 2.4 기존 검색 인프라 — 임베딩 결합 (`core/document_index.py`)
- `DocumentIndex.search(query, top_k, filters)` → `SearchResult`(dense+sparse 하이브리드, 기본 0.6/0.4). dense=Gemini 임베딩, 미가용 시 sparse-only 폴백. `.system_generated/cache/document_index.json` 캐시.
- `core/document_chunker.py`: 마크다운 heading 인지 청커.
- **판단**: dense 경로는 Gemini 의존 → R-D2(결정론·멀티프로바이더)와 충돌. **MVP 미배선**, §3.6 보조 seam.

### 2.5 CLI dispatch 패턴
- `agent_launcher.py`: `evolution`·`sandbox`·`provider` 서브커맨드 dispatch 선례. 부모 STAGE 3은 `af knowledge doctor`를 여기 등록 예정 → **`knowledge`는 그룹**(`search` now, `doctor` 후속).
- `run_factory_cli.py` `_STAGE1_DISPATCH`/`_STAGE1_USAGE`도 동일 패턴. **배포 동등성**: 두 진입점 모두에 도달 확인 필수(`feedback_pipeline_deploy_parity`).
- `af.spec` hiddenimports에 신규 모듈 추가 필수.

---

## §3 핵심 설계 결정

### 3.1 (R-D2) 결정론 전용 엔진 — 임베딩 0
부모 §13.2가 "결정론 우선, 임베딩 보조"를 동결. 추가로 이 프로젝트의 강한 제약:
- **멀티OS/멀티프로바이더**(CLAUDE.md): Gemini 인증은 환경별로 깨짐(실측, gemini auth 실패 사례 다수). 검색이 임베딩에 의존하면 인증 안 된 PC에서 무용.
- **크로스PC 재현성**: 방금 symbols.md 비결정성 버그(`1c0201a3`)로 학습 — 산출은 커밋된 소스의 결정적 함수여야 PC-무관. 임베딩 점수는 모델/버전 의존 → 비결정.
- 117파일 규모는 임베딩 없이도 충분히 빠르고 정확.
→ **MVP = 순수 Python sparse 점수(용어 빈도 + 정밀참조 exact-match). 외부 호출 0.**

### 3.2 (R-D3) 2개 질의 모드 — 변경파일 exact-match가 1급 신호
1. **`--query "<텍스트>"`** (키워드): 노트의 title/description/본문/정밀참조에 대한 용어 매칭 점수.
2. **`--files a.py,b.py`** 또는 **`--diff`**(현재 git diff `--name-only` 자동): 각 노트의 **정밀참조 file 경로**와 변경 파일을 exact/basename 매칭. S2-3 감사로 정밀참조 = 100% precision 검증 → 이 매칭은 **고정밀·결정론**. "이 파일 건드릴 때 과거에 뭘 결정했나"를 정확히 인출.
- 두 모드 동시 지정 시 점수 합산(파일 매칭 가중 ↑).

### 3.3 (R-D4) 관용적 frontmatter 파싱
`KnowledgeNote.from_md`는 신규 포맷 전용 → 검색엔 **별도 관용 파서**:
- frontmatter 블록이 있으면 key:value를 best-effort 추출(`id|type|title|name|description|author|created_at|metadata.type`), 없으면 본문만.
- 파싱 실패해도 **본문 전문은 항상 검색 대상**(노트를 누락시키지 않음 — 검색은 recall 우선).
- `title` 없으면 `name` → 첫 `# 헤딩` → 파일 stem 순 폴백.

### 3.4 (R-D5) read-only·advisory + bounded 출력
- write/create/delete 경로 **물리적 0**(grep 테스트로 강제, INV-R4).
- 출력: 기본 사람용 표(순위·점수·type·제목·매칭이유·경로), `--json`은 에이전트 소비용(노트 경로 + 발췌 + 점수). `--limit`(기본 8) bounded.
- 발췌 = 매칭 줄 주변 컨텍스트(정밀참조 섹션 우선) — 통째 본문 금지(토큰절약 목적 자기정합).

### 3.5 캐시 없음 — 매 호출 full-scan
117파일 full-scan은 ms 단위. 인덱스 캐시는 (i) staleness 관리 (ii) 크로스PC 캐시 드리프트 (iii) 신설 복잡성 → 규모 대비 과설계. **glob + 읽기 + 점수**를 매번. 규모가 1000+로 커지면 그때 캐시 도입(seam: 점수 함수 분리).

### 3.6 임베딩 = 보조 seam (연기)
`document_index.py` dense 경로는 **연기**. 엔진 인터페이스를 `score_notes(query, notes) -> ranked` 로 분리해, 미래에 sparse 점수에 dense 점수를 가산하는 자리만 남긴다(0코드 문). MVP는 sparse만.

---

## §4 아키텍처 / 모듈

```
af knowledge search --query "..." [--files a.py,b.py | --diff] [--type T] [--limit N] [--json]
        │
        ▼
run_factory_cli._STAGE1_DISPATCH["knowledge"]  +  agent_launcher knowledge dispatch
        │  (배포 동등성: 두 진입점)
        ▼
core/knowledge/retrieve.py  (신규, 순수 Python·테스트 가능)
  ├ load_notes(vault_root) -> list[NoteDoc]      # glob docs/wiki/knowledge/**/*.md, 관용 파싱
  │     NoteDoc = {path, type, title, body, refs:set[str]}  # refs = extract_precise_refs(body) 재사용
  ├ score_notes(query, files, notes) -> list[(NoteDoc, score, reasons)]   # 결정론 sparse
  └ format_results(ranked, as_json) -> str
```
- **NoteDoc**는 retrieve.py 내부 경량 타입(검색 전용). KnowledgeNote(durable 계약)와 별개 — 검색은 3종 포맷·무-frontmatter까지 수용해야 하므로 durable 스키마에 가두지 않음(타입 SSOT 위반 아님: 다른 목적·다른 필드집합).
- vault_root = `<repo_root>/docs/wiki/knowledge` (절대경로 하드코딩 금지 — `Path(__file__)`/인자로 도출).
- **결정론 tie-break**: 동점 시 `created_at` 내림차순 → `path` 사전순. (크로스PC 동일 출력.)

### 4.1 점수 모델 (결정론 sparse)
- 쿼리 용어 t에 대해 노트별: `title/name`(가중 3) + `description`(2) + `정밀참조 섹션`(2) + `본문`(1)의 대소문자 무시 출현 횟수 합.
- 파일 모드: 노트 refs ∩ 변경파일(전체경로 일치=가중 5, basename 일치=가중 3)당 가산.
- 한국어 토큰화 한계: 공백분할 + 부분문자열 매칭(자모 분석 안 함). 정밀참조(영문 경로·커밋)는 언어무관 강신호 → 한글 semantic 검색의 마지막 1마일은 임베딩(연기)에 위임. MVP는 키워드/파일 매칭으로 충분(통증 PR1·PR2 해소).

---

## §5 산출물
- `core/knowledge/retrieve.py` (신규) — `load_notes`·`score_notes`·`format_results` + CLI `main(argv)`.
- `run_factory_cli.py` — `_STAGE1_DISPATCH["knowledge"]` + `_STAGE1_USAGE` 엔트리(`knowledge` 그룹: `search`).
- `agent_launcher.py` — `knowledge` 서브커맨드 dispatch(배포 동등성, STAGE 3 `doctor`와 그룹 공유). **`_KNOWN_SUBCOMMANDS`(`:31`)에 `"knowledge"` 추가 필수** — 누락 시 `knowledge`가 일반 task로 분류돼 격리 PROJECT_ROOT에서 실행→vault 탐색 실패(`af-cross-review` F3).
- `af.spec` — hiddenimport `core.knowledge.retrieve`.
- `tests/test_knowledge_retrieve.py` — 신규.
- Blueprint §0(파일표)·§12(이력).

## §6 비범위 (명시적 제외)
- 세션시작 자동주입 (R-D1). 임베딩 semantic (R-D2). 노트 쓰기/생성 (read-only). 인덱스 캐시 DB (§3.5). 한글 자모 형태소 분석.

## §7 불변식 (INV-R)
- **INV-R1**: STAGE R 엔진은 외부 LLM/임베딩/네트워크 호출 0 — 순수 Python·결정론(크로스PC 동일입력→동일출력).
- **INV-R2**: 정밀참조 추출은 `distill.extract_precise_refs` SSOT 재사용 (정규식 재구현 금지).
- **INV-R3**: 검색은 3종 frontmatter(KnowledgeNote/레거시/무) + 파싱실패 노트도 **본문 전문**으로 인덱싱(누락 0, recall 우선).
- **INV-R4**: write/create/delete 경로 0 (grep 테스트 강제). vault·원장 비오염.
- **INV-R5**: 출력 bounded(`--limit`, 기본 8) + 발췌만(통째 본문 금지). 결정론 tie-break(created_at desc→path).

## §8 멀티OS·멀티프로바이더 (CLAUDE.md 구현규칙)
- **멀티OS**: pathlib·glob 순수 Python. fcntl/flock/launchd·symlink·절대경로 하드코딩 금지. Windows에서 import·실행·한글 경로 회귀 테스트. `--diff`의 git 호출은 `_git`(stdin=DEVNULL 선례) 재사용.
- **멀티프로바이더**: 엔진이 LLM 무관(결정론) → 프로바이더 자동 동등. 임베딩 미배선이라 Gemini 인증 의존 없음.

## §9 검증 기준 (Goal-Driven)
| # | 강한 성공 기준 |
|---|--------------|
| 1 | **키워드 모드**: 알려진 노트를 가리키는 쿼리(예: "router research decoupling")가 그 노트를 top-3에 인출 (스냅샷 테스트) |
| 2 | **파일 모드**: `--files core/right_sized_router.py` 가 그 파일을 정밀참조한 노트만 정확 인출(refs exact-match), 무관 노트 0 (S2-3 precision 계승). **전제(F2b)**: 이 테스트가 유의미하려면 해당 file:line을 정밀참조한 **신규 KnowledgeNote 합성 fixture 1건**을 테스트에 포함해야 함(레거시 노트엔 `정밀 참조` 섹션 부재 — §10 위험) |
| 3 | **3종 포맷 수용**: KnowledgeNote·레거시 memory·무-frontmatter 각 1건이 모두 인덱싱·검색됨(INV-R3) |
| 4 | **결정론**: 동일 vault·쿼리 2회 실행 = 바이트 동일 출력(INV-R1/R5 tie-break) |
| 5 | **read-only**: retrieve.py에 open(...,'w')/write/unlink/mkdir 0건 grep(INV-R4) |
| 6 | **배포 동등성**: `af knowledge search` 가 `agent_launcher.py`·`run_factory_cli.py` 두 진입점에서 동일 동작(grep + 실행) |
| 7 | **크로스OS**: Windows에서 import·실행·한글 경로 노트 검색 회귀 |

## §10 위험 & 완화
| 위험 | 완화 |
|------|------|
| 한글 키워드 검색 약함(토큰화) | 정밀참조·파일 모드가 강신호. semantic은 임베딩(연기) seam. MVP 통증은 키워드/파일로 해소 |
| frontmatter 3종 파싱 깨짐 | 관용 파서 + 실패해도 본문 인덱싱(INV-R3). 누락 0 우선 |
| vault 성장 시 full-scan 느려짐 | score 함수 분리(seam) → 1000+ 시 캐시 도입. 117파일 현재 무문제 |
| 진입점 1곳만 배선(stale) | §9#6 두 진입점 grep+실행 강제(`feedback_workflow_agent_review_gate_gap`) |
| **레거시 노트 파일 모드 recall 0**(F2b) — 레거시 memory 포맷(`sessions/`·`patterns/`)엔 `## 정밀 참조` 섹션이 없어 `--files` 매칭이 안 잡힘 | 본문 전문에서도 `extract_precise_refs`로 file:line 추출 시도(INV-R3) + 레거시는 `--query` 병용 권장(문서화). 신규 증류 노트는 정밀참조 섹션 보유 → 시간이 지나며 recall 자연 상승 |

---

## §11 변경 이력
| 날짜 | 변경 |
|------|------|
| 2026-06-25 | 초안. 부모 §13.2(D13) STAGE R 상세화. baseline 실측(§2, 117파일·3종 frontmatter·extract_precise_refs 재사용). MVP=명령어-only(사용자 확정). 결정론 전용·임베딩 연기. Status=Draft. |
| 2026-06-25 | **af-cross-review WARN[single-vendor] 흡수**(codex usage-limit·gemini 인증만료→Claude 단독, BLOCK 0): F1(session/ 4→5·총 116→117 grep 정정)·F2(`extract_precise_refs` 시그니처 `(events)`→`(text)`)·F3(§5 `agent_launcher._KNOWN_SUBCOMMANDS:31`에 `"knowledge"` 추가 명시 — 격리 PROJECT_ROOT 오실행 방지)·F2b(§9#2 합성 fixture 전제 + §10 레거시 노트 파일모드 recall 위험·완화). 5건 전부 사실 grep 확인 후 반영. ⚠️ codex 재검증은 usage-limit 해제 후 cross-vendor 필요. |
