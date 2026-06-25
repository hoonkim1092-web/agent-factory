# 자가진화 지식 도서관 (Knowledge Library) 설계

- **Status**: Draft — **R2 개정(2026-06-23): §12 참조** (목표 확장: 솔로 단독 → **솔로+팀 연속성**, substrate 아키텍처 확정. §0~§7의 단일-사용자 전제 중 §12가 명시한 부분은 §12가 우선)
- **작성일**: 2026-06-23
- **모델**: Opus 4.8 (설계)
- **한 줄 요약**: 단일 사용자가 여러 PC를 오가며 작업한 맥락(결정·기각·패턴·개념)을 **git 안 마크다운 vault**로 증류·연결·유지하고, Obsidian으로 시각화한다. raw가 아니라 증류본이 흐르며, 코드와 같은 git 히스토리로 묶여 PC 간 드리프트를 원천 제거한다.

---

## §0 이 문서가 동결하는 결정

이 설계는 2026-06-23 대화에서 단계적으로 좁혀진 결정의 산물이다. 재론 금지 항목:

| # | 결정 | 근거 (이 문서 내 위치) |
|---|------|----------------------|
| D1 | **단일 사용자·다중 PC** 문제다 (multi-writer 팀 아님) ⚠️ **R2: §12 D7로 팀 연속성 확장 — multi-writer 안전은 §12.4** | §1, §3.1 — 로그인·권한엔진은 여전히 비범위(§6), 단 동시쓰기 안전은 §12에서 다룸 |
| D2 | **저장소 = git** (새 DB·SaaS 신설 금지) | §3.2 — 코드와 같은 히스토리 = 드리프트 소멸 + commit핀 공짜 |
| D3 | **raw 트랜스크립트 미동기화** — 증류본 + 포인터만 | §3.3 — 189MB, 평문 노출, 노이즈. opt-in 아카이브는 비범위(§6) |
| D4 | **식별·접근제어는 seam만** (enforcement 코드 금지) | §3.4 — `author` frontmatter + `restricted/` 폴더. 실행은 git/GitHub이 나중에 공짜 제공 |
| D5 | **NEXT_STEPS.md는 다이어트, 퇴역 아님** | §3.5 — 정밀 원장(commit/line/INV)은 손실압축 불가 |
| D6 | **증류·점검·생성은 provider-neutral** (코드 레벨) | §3.6 — `control_plane_llm` SSOT. Claude/Codex/Gemini 동일 |

---

## §1 문제 정의 & 북극성

### 1.1 북극성
> 작업하면서 쌓인 맥락이 **자동으로 증류되어**, 서로 **연결되고**, **정직하게 유지되며**, **Obsidian 그래프로 보이는** 개인 지식 도서관. 어느 PC에서 어느 프로바이더(Claude/Codex/Gemini)로 재개해도 맥락이 이어진다.

### 1.2 해결할 실제 통증 (관측된 것만)
- **P1 — PC 전환 드리프트**: 지식(`memory/`, Supabase)이 코드(git)와 **따로 동기화**되어 시점이 어긋남 → "이 메모가 틀린 건가, 이 PC가 아직 안 받은 건가" 구분 불가. (관측: `project_model_routing_facts` 메모리가 실제 stale 정정당함, 2026-06-11)
- **P2 — 맥락 단절(프로바이더)**: Claude 세션 종료 후 Codex/Gemini로 재개 시 맥락 처음부터. (트랜스크립트는 PC-local, §2.4)
- **P3 — 자동 증류가 멍청함**: 현 `session_bridge`는 260자 truncate(§2.3) → 정밀 참조·"왜"가 잘려 맥락 유지 부실.
- **P4 — 지식과 코드가 한 화면에 안 보임**: 코드 wiki와 `memory/`가 **다른 폴더** → Obsidian이 하나의 그래프로 못 그림(§2.1·2.2).

### 1.3 비통증 (만들지 않을 것)
- 팀 협업(동시 편집·권한). 사용자는 혼자다(D1).
- raw 대화 영구 보관(D3). raw는 아무도 안 읽는다(컨텍스트에 안 올라감).
- "철학적 모순 탐지" 같은 비접지 기능 — 코드 레포에서 ground truth는 코드다(§3.7).

---

## §2 Baseline — 실제 코드 현황 (file:line, 검증됨 2026-06-23)

> 이 절은 추측 baseline 금지 규칙(`feedback_analysis_doc_baseline_must_be_real_code`)에 따라 전수 실측한 사실만 기록한다. 교차검증은 이 절을 1차 대조한다.

### 2.1 코드 지식 wiki — **이미 존재, Obsidian 호환**
- `docs/generated/llm_wiki/` = **41 파일**, **전부 `[[wikilink]]`** 사용. `blueprint/`·`code_review/`·`architecture.md`·`symbols.md`·`open_items.md` 등.
- 생성기 `scripts/build_llm_wiki.py` (633줄): **순수 regex/AST 파서, LLM 호출 0**. 입력 = `Master_Blueprint.md` + `docs/code_review/code-review.md` + `NEXT_STEPS.md`(`:31-33`) + AST 심볼. frontmatter에 `source_commit` 박음(`:60-64`).
- **⚠️ `build()`는 out_dir의 stale 파일을 `unlink()` 삭제**(`:590,:601`). → 내구성 지식을 같은 out_dir에 두면 지워짐 → 레이아웃 분리 필수(INV-K7).
- 진입점: pre-commit 자동 + user-facing `af project wiki --path <dir>`(`agent_launcher.py:1088`, 임의 workspace = 이미 product 표면).

### 2.2 결정/학습 지식 — **존재하나 분리됨**
- `memory/` (실위치 `~/.claude/projects/<enc>/memory/`) = **112 파일**, **42개가 `[[wikilink]]`**. 사실상 "왜/결정" 지식층.
- 동기화: `scripts/sync_claude_memory.py` → Supabase `claude_memory` 테이블, **평문 저장**(`:10`). 저장 키 = **`project_id`**(레포 경로 인코딩, `:70 _path_to_claude_key`, `:15 PRIMARY KEY`). **last-write 덮어쓰기**(`on_conflict=project_id` upsert, `:251` → 진짜 머지 없음 → 다중작성자 부적합, 단일 사용자엔 충분). (`global_user_key`는 sync가 아니라 **session_bridge 레코드 필드**, §2.3.)
- 문제: 코드 wiki(§2.1)와 **다른 폴더** → Obsidian이 둘을 한 그래프로 못 봄(P4).

### 2.3 트랜스크립트 → memory 브리지 — **멀티프로바이더, 그러나 기계적**
- `scripts/session_bridge.py` (565줄): `PROVIDERS`(`:213`) = codex(`rollout-*.jsonl`)·claude(`*.jsonl`)·gemini(`*.jsonl`). 이미 3-프로바이더.
- `write_memory_entries`(`:387`): **증류 아님 — truncate**. `summary=truncate(text,260)`, `details.text=truncate(text,4000)`(`:419`), `details`에 `session_file`(`:421`)·`session_line`(`:422`)은 있으나 `max_write=240`(`:445`). **commit/branch 필드 없음**(P1 근본 원인), **originating_pc/hostname 필드 없음**(D3 포인터 3요소 중 `pc` 미존재 → STAGE 2가 신규 추가).
- 배선: `core/providers/session_adapter.py:22 from scripts.session_bridge import run_bridge`, `:14 resume_brief`. CLI 세션 수명주기에 연결.

### 2.4 세션 수명주기 훅 — **훅 등록됨, 단 증류 발화점은 한정적**
- `.claude/settings.local.json`: `SessionStart`·`Stop`·`PreCompact` → `hook_runner.py cli_hook_bridge --provider --workspace --run-id --repo-root` 등록. 배포 템플릿(`settings.local.template.json`)도 동일 → 임의 workspace 작동.
- **⚠️ 그러나 `run_bridge`(증류 소스 경로)는 `Stop`에서 안 돎.** `core/providers/session_adapter.py:690`: `if event_name in {"PreCompact","PreCompress","SessionEnd"} and transcript_path: run_bridge(...)`. → **증류 배선점 = SessionEnd/PreCompact (이미 존재)**, Stop 아님. STAGE 2는 신규 Stop 분기가 아니라 **이 기존 발화점을 증류로 교체/보강**한다.
- `core/continuity/resume_brief.py` → `resume_brief.md` 생성(SessionStart 재개 브리핑, 이번 세션 시작 시 출력된 그것).

### 2.5 야간 파이프라인 — **POSIX 전용 (Windows 미작동)**
- `scripts/nightly_tick.py:24`: `if win32: raise ImportError` (fcntl/flock/launchd). → 사용자 Windows에선 안 돎. 지식 점검은 **이 경로에 의존하면 안 됨**(순수 Python 크로스OS 필요).

### 2.6 대용량 정책 — **git에서 이미 탈출한 선례**
- `.gitignore`: `dist/` 제외. 주석(`:33-36`): 91MB zip이 GitHub 100MB 한계로 push 실패 → Release로 이전. → **189MB 트랜스크립트 git 커밋은 학습된 정책 위반**(D3 근거).

### 2.7 Provider-neutral LLM SSOT — **존재**
- `core/control_plane_llm.py`: `ControlPlaneLLM`(`:39`), `generate()`(`:147`)/`generate_json()`(`:161`). → 증류기가 여기에 배선되면 자동 멀티프로바이더(INV-K4).

### 2.8 문서 규모
- `CLAUDE.md` 219줄(500줄 룰 통과 — 비이슈). `NEXT_STEPS.md` **1219줄**(다이어트 대상, D5).

---

## §3 핵심 설계 결정 (rationale)

### 3.1 (D1) 단일 사용자·다중 PC
동시 작성자가 없으므로 충돌 머지·식별엔진·접근엔진 불필요. 남는 문제는 "내 지식이 PC를 따라오기"(P1·P2) 하나.

### 3.2 (D2) 저장소 = git — 드리프트 소멸 + commit핀 공짜
지식 vault를 git 안에 두면 **지식 .md와 코드가 같은 히스토리**가 된다.
- `git pull` 한 번에 코드+지식이 **같은 커밋으로 원자적 도착** → P1(STALE vs SKEW 드리프트) **구조적 소멸**.
- 각 노트의 git 커밋이 곧 "언제 쓰였나" → **commit핀 공짜**(별도 STEP 0 불필요).
- 트레이드오프: Supabase는 커밋 없이 저장(저친화)이지만 코드와 따로 놀아 드리프트 유발. git은 커밋 필요하나 원자성 확보. 사용자는 이미 git push 규율 보유 → 순이득.
- **layering**: `memory/`(Supabase)는 **빠른 개인 스크래치**로 유지, keep할 가치가 생기면 vault로 **승격**(§5 STAGE 5).

### 3.3 (D3) raw 미동기화 — 증류본 + 포인터
- raw 189MB·평문 노출·노이즈(§2.6, §2.2). 게다가 **raw는 맥락 통로에 없음**(새 세션이 3MB JSON을 못 읽음 → 맥락은 항상 큐레이션 층으로 이어짐).
- 대신: 증류본 + `{originating_pc, session_file, line}` 포인터. 1% "원문 봐야겠다" 순간에만 그 PC에서 회수.

### 3.4 (D4) 식별·접근제어 = seam만
- **식별**: 노트 frontmatter `author`/`source_machine`/`created_commit`. git author가 이미 공짜 제공, frontmatter는 Obsidian 조회용 보강. (~1필드)
- **접근제어**: `knowledge/restricted/` **폴더 컨벤션만**. enforcement 코드 0줄. 팀 전환 시 GitHub CODEOWNERS·브랜치보호로 **상속**(신규 빌드 없음).
- 근거: enforcement를 지금 짜면 0명을 막는 죽은 코드(Simplicity First 위반). seam은 마이그레이션 없이 문만 열어둠.

### 3.5 (D5) NEXT_STEPS 다이어트
NEXT_STEPS는 `bf8ea506`·`agent_runner.py:1226`·`INV-O1` 같은 **고정밀 참조**의 원장. 손실압축(LLM/기계 증류 둘 다 lossy, `open_items.md` 상단 경고가 증거) 대체 불가. → 완료 이력은 vault로 이관, **활성 작업 + 정밀 참조만** 잔류.

### 3.6 (D6) provider-neutral
증류·점검·생성 로직을 코드(Python + `control_plane_llm`)에 두면 어느 프로바이더가 돌려도 같은 코드. 산문 지침은 `INSTRUCTIONS.md` SSOT→sync.

### 3.7 Dream Sequence의 접지
"모순 탐지"는 코드 레포에선 **검증 가능한 명제로 한정**한다: "노트가 named한 `file:line`/심볼/커밋이 현재 코드에 실존하나". 비접지 "철학적 모순"은 노이즈 생성기 → 비범위.

---

## §4 아키텍처

### 4.1 데이터 평면
```
RAW (수집, PC-local, 미동기화)
  ~/.{claude,codex,gemini}/sessions/*.jsonl   ← session_bridge가 읽음 (§2.3)
        │  SessionEnd/PreCompact 증류 (run_bridge 기존 발화점, §2.4) — originating PC, 떠나기 전
        ▼
SCRATCH (빠른 개인, Supabase)
  memory/*.md   ← 현행 유지 (저친화 메모)
        │  승격 (keep 가치 생기면, STAGE 5)
        ▼
VAULT (내구성, git-tracked, Obsidian root) ★ 신규 통합
  docs/wiki/
    code/        ← build_llm_wiki --out (generated, 재생성, §2.1)
    knowledge/   ← 내구성: decisions/ concepts/ patterns/ sessions/ restricted/
    MOC.md       ← Map of Content (지도)
        │  git pull
        ▼
  모든 PC에 코드+지식 원자적 도착 → Obsidian 그래프 시각화
```

### 4.2 vault 레이아웃 결정 (INV-K7 강제)
- Obsidian root = **`docs/wiki/`** (신규, git-tracked).
- `docs/wiki/code/` = `build_llm_wiki`가 `--out`으로 생성(generated). **`build()`가 stale unlink 하므로**(§2.1) 이 하위만 건드림.
- `docs/wiki/knowledge/` = 내구성. **build_llm_wiki는 절대 안 건드림**(INV-K7). 손/증류가 작성.
- 둘이 형제 폴더라 Obsidian이 한 그래프로 봄. `[[code/symbols]] ↔ [[knowledge/decisions/...]]` 교차링크.
- 크로스OS: **symlink 금지**(Windows 취약) — 실제 폴더만.
- (현 `docs/generated/llm_wiki/`는 STAGE 0에서 `docs/wiki/code/`로 이행하거나, `--out` 재지정으로 흡수. §5 STAGE 0에서 확정.)

---

## §5 단계별 구현 (메타프롬프트)

> 각 STAGE는 구현자(LLM/사람)에게 그대로 넘길 수 있는 메타프롬프트다. 형식: **목표 / 입력(baseline) / 제약 / 산출물 / 검증 / 의존**. MVP = STAGE 0~2. 순서는 "먼저 보이게(0) → 스키마(1) → 증류(2) → 점검(3) → 연결(4) → 다이어트(5)".

### STAGE 0 — Vault 통합 (먼저 보이게)
```
[목표] memory/ 지식 + 코드 wiki를 하나의 git-tracked Obsidian vault(docs/wiki/)로
       합쳐, 진화 기능 0줄 추가 없이 "내 도서관"을 Obsidian 그래프로 보이게 한다.
[입력] §2.1 build_llm_wiki(out 재지정 가능, :525 build(workspace,out_dir)),
       §2.2 memory/ 112파일(이미 wikilink), §4.2 레이아웃.
[제약] · build_llm_wiki --out=docs/wiki/code 로 코드wiki 이행 (knowledge/와 형제)
       · knowledge/ 하위는 build가 절대 안 건드림 (INV-K7) — out_dir != knowledge
       · memory→knowledge 는 '렌더/복사'이지 memory 원본 삭제 아님 (스크래치 유지, D2)
       · symlink 금지(크로스OS). 절대경로 하드코딩 금지.
[산출물] · docs/wiki/{code/, knowledge/, MOC.md} 생성
         · memory/*.md → knowledge/ 로 분류 렌더(decisions/concepts/patterns/sessions)
         · MOC.md: code↔knowledge 진입 링크 지도
[검증] · Obsidian으로 docs/wiki/ 열면 code+knowledge가 한 그래프에 뜬다(수동 확인 1회)
       · build_llm_wiki 재실행 후 knowledge/ 파일 무손실(INV-K7 테스트)
       · af project wiki --path 가 docs/wiki/code 에 생성(배포 동등성)
[의존] 없음 (substrate 존재). 이 STAGE만으로 독립 가치.
```

### STAGE 1 — 지식 노트 스키마 + 식별/접근 seam (SSOT)
```
[목표] 내구성 지식 노트의 단일 타입(frontmatter 계약)을 정의하고, 식별·접근
       확장 seam을 데이터 모델에 심는다 (enforcement 코드는 안 짠다).
[입력] §3.4 seam 결정, §2.7 git author, 타입 SSOT 규칙(CLAUDE.md).
[제약] · 타입은 한 파일에서만 선언 (예: core/knowledge/note.py KnowledgeNote)
       · frontmatter 필수: id, type(decision|concept|pattern|session),
         author, source_machine, created_commit, links[], created_at
       · created_commit 은 git rev-parse 로 자동 주입 (build_llm_wiki :52 _short_commit 재사용)
       · restricted/ 는 폴더 컨벤션일 뿐 — 읽기/쓰기 제한 코드 금지(INV-K6)
[산출물] · KnowledgeNote 데이터클래스 + to_md/from_md(frontmatter 직렬화)
         · 노트 작성 헬퍼(author/source_machine/created_commit 자동 스탬프)
[검증] · round-trip(to_md→from_md) 단위테스트
       · created_commit 이 현재 HEAD와 일치(주입 테스트)
       · restricted/ 에 enforcement 코드 0건(grep 검증)
[의존] STAGE 0 (vault 존재).
```

### STAGE 2 — 증류기 (truncate → LLM 증류, provider-neutral)
```
[목표] session_bridge의 260자 truncate(§2.3)를, 세션 종료 시점에 raw에서
       '결정·기각·패턴·정밀참조'를 추출하는 LLM 증류로 대체/보강한다.
[입력] §2.3 write_memory_entries, §2.7 control_plane_llm(generate_json),
       §2.4 run_bridge 발화점=SessionEnd/PreCompact(session_adapter.py:690, Stop 아님),
       §3.3 포인터, §2.3 details에 session_file/line 있으나 pc 없음.
[제약] · LLM 호출은 control_plane_llm SSOT 경유 (INV-K4 멀티프로바이더)
       · 정밀참조(commit/file:line/INV명)는 '요약 금지, verbatim 발췌'(INV-K5)
       · 산출 = KnowledgeNote(STAGE1) + raw 포인터{originating_pc,session_file,line}
       · originating PC의 세션 종료 시 실행 (떠난 뒤엔 raw 없음, D3, INV-K9)
         = session_adapter.py:690 기존 SessionEnd/PreCompact 경로 교체/보강.
         신규 Stop 분기 불필요(§2.4 정정).
       · raw 본문을 git/Supabase에 쓰지 않는다(INV-K2). 포인터만.
       · secret/token 필터 (평문 vault 보호)
[산출물] · core/knowledge/distill.py: raw rows → KnowledgeNote (LLM 1패스)
         · session_adapter.py:690 SessionEnd/PreCompact 경로의 run_bridge를 증류로
           교체/보강 (배포 동등성: production caller까지, 픽스처-only 금지)
         · session_bridge 레코드 details에 originating_pc(socket.gethostname()) 필드 추가
           (D3 포인터 3요소 완성, F3)
[검증] · ★성공기준: 과거 실제 세션 1건 증류 결과가 그날 손으로 쓴
         NEXT_STEPS 항목만큼 풍부한가 (commit·결함번호 보존율 비교, 실측)
       · 멀티프로바이더: claude/codex 두 경로 동일 코드로 산출(스냅샷 테스트)
       · secret 필터 단위테스트(가짜 토큰 주입→마스킹)
[의존] STAGE 1 (스키마).
```

### STAGE 3 — Staleness 점검기 (af knowledge doctor, 크로스OS)
```
[목표] 지식 노트가 named한 file:line/심볼/커밋이 현재 코드에 실존하는지 검증,
       STALE(코드 바뀜)와 SKEW(이 PC 미pull)를 구분해 리포트한다.
[입력] STAGE1 created_commit, §2.5(nightly_tick POSIX전용 — 의존 금지),
       §3.7 접지 원칙, scripts/blast_radius.py(심볼 추출 참고).
[제약] · 순수 Python 크로스OS (fcntl/flock/launchd 금지 — nightly_tick 경로 안 씀)
       · STALE vs SKEW 판정: created_commit 이 현재 git 히스토리에 있나?
         없음→SKEW(이 PC 미pull, 오보 차단) / 있음→git diff 로 file:line 변동 판정→STALE
       · 비접지 '의미 모순' 탐지 금지(노이즈) — 검증가능 명제만
       · advisory(리포트)만. 자동 삭제/수정 금지
[산출물] · scripts/af_knowledge_doctor.py + agent_launcher `af knowledge doctor` dispatch
         · af.spec hiddenimport
[검증] · STALE/SKEW 분기 단위테스트(가짜 노트 commit 조작)
       · 깨진 file:line 노트 주입→STALE 리포트, 미pull 커밋→SKEW 리포트
       · Windows에서 import·실행(크로스OS 회귀)
[의존] STAGE 1 (created_commit 필요).
```

### STAGE 4 — 지능형 연결 (auto-wikilink)
```
[목표] knowledge 노트 ↔ code wiki(symbols) 사이 연결을 자동 발견해 그래프를 키운다.
[입력] §2.1 symbols.md(AST), STAGE1 links[], 기존 wikilink 컨벤션.
[제약] · 심볼/파일명 매칭 기반(결정론). LLM은 보조(애매 케이스만)
       · 양방향 [[wikilink]] 삽입, 기존 수동 링크 보존(덮어쓰기 금지)
       · 오탐 링크 < 노탐 (보수적)
[산출물] · core/knowledge/link.py: 노트 본문의 file/symbol 언급→[[code/...]] 링크
[검증] · 알려진 노트→코드 링크 정확도 스냅샷
       · 기존 수동 wikilink 무손실
[의존] STAGE 0·1·(2).
```

### STAGE 5 — NEXT_STEPS 다이어트 + 승격 게이트
```
[목표] 완료 이력을 vault/sessions 로 이관하고 NEXT_STEPS는 활성+정밀참조만 남긴다.
       memory(scratch)→vault(durable) 승격 기준을 정의한다.
[입력] §2.8 NEXT_STEPS 1219줄, §3.2 layering, build_llm_wiki(:33 NEXT_STEPS 입력).
[제약] · 정밀참조(commit/line/INV)는 이관해도 verbatim 보존(D5, INV-K5)
       · 승격은 명시적 행위(자동 전량 이관 금지 — scratch 오염 방지)
       · NEXT_STEPS 퇴역 아님 — 원장 역할 유지
[산출물] · 완료 항목→sessions/ 아카이브 절차 + 승격 헬퍼
         · build_llm_wiki open_items 입력 경로 정합 확인
[검증] · 이관 후 NEXT_STEPS 정밀참조 grep 보존율 100%
       · 다이어트 후 줄수 감소 + 활성 항목 누락 0
[의존] STAGE 0~3.
```

---

## §6 비범위 (명시적 제외)
- **팀 enforcement**: 동시쓰기 머지·로그인·권한엔진·역할로직. (git/GitHub이 팀 전환 시 제공, D4)
- **raw 트랜스크립트 동기화/영구보관**: 기본 경로 아님. opt-in·DB전용·보관제한 아카이브는 **별도 설계**(D3).
- **크로스OS 야간 cron**: Stop-hook 증류로 충분(D3, §5 STAGE2). 스케줄러 신설은 후속 트랙(nightly_tick POSIX 한계는 본 설계가 우회).
- **비접지 의미 모순 탐지**(§3.7).
- **Obsidian Sync/유료 SaaS**: git이 동기화(D2).

---

## §7 불변식 (INV)
- **INV-K1**: 지식 vault는 git-tracked, 코드와 같은 히스토리 (PC 간 원자성).
- **INV-K2**: raw 트랜스크립트는 git/공유DB에 안 들어감 — 증류본 + 포인터만.
- **INV-K3**: 모든 내구성 노트는 frontmatter에 author/source_machine/created_commit.
- **INV-K4**: 증류·생성·점검의 LLM 호출은 `control_plane_llm` SSOT 경유 (provider-neutral).
- **INV-K5**: 증류는 정밀참조(commit/file:line/INV명)를 요약하지 않고 verbatim 발췌.
- **INV-K6**: 접근제어 enforcement 코드 금지 — `restricted/` 폴더 seam만.
- **INV-K7**: `build_llm_wiki`는 `code/`만 write, `knowledge/`는 절대 안 건드림 (stale unlink로부터 보호).
- **INV-K8**: NEXT_STEPS.md는 정밀 원장으로 유지 (퇴역 아님, 다이어트).
- **INV-K9**: 증류는 originating PC의 세션 종료 시점에 실행 (raw 휘발 전) — `session_adapter.py:690`의 기존 SessionEnd/PreCompact `run_bridge` 발화점(Stop 아님, §2.4).

---

## §8 멀티OS·멀티프로바이더 정합 (CLAUDE.md 구현규칙)
- **멀티OS**: 지식 경로는 순수 Python + pathlib. fcntl/flock/launchd(nightly_tick) **의존 금지**. symlink 금지. 절대경로 하드코딩 금지. doctor·distill은 Windows에서 import·실행 회귀 테스트.
- **멀티프로바이더**: 수집은 session_bridge PROVIDERS(이미 3종). 증류 LLM은 control_plane_llm SSOT. vault는 마크다운이라 프로바이더 무관. 산문 지침은 INSTRUCTIONS.md→sync.

---

## §9 검증 기준 (Goal-Driven)
| STAGE | 강한 성공 기준 |
|-------|--------------|
| 0 | Obsidian에서 docs/wiki/ 1폴더로 code+knowledge 그래프 표시 + build 후 knowledge 무손실 |
| 1 | KnowledgeNote round-trip + created_commit=HEAD + restricted enforcement 0건 |
| 2 | **과거 세션 증류본이 그날 손작성 NEXT_STEPS 정밀참조를 보존**(실측 비교) + 멀티프로바이더 동일산출 + secret 마스킹 |
| 3 | STALE/SKEW 분기 정확 + Windows 실행 + advisory-only |
| 4 | 자동링크 정확도 + 수동링크 무손실 |
| 5 | 정밀참조 grep 보존 100% + 활성항목 누락 0 |

---

## §10 위험 & 완화
| 위험 | 완화 |
|------|------|
| build_llm_wiki stale unlink가 knowledge 삭제 | INV-K7 + out_dir 물리 분리(§4.2) + 무손실 테스트 |
| 증류 손실로 맥락 끊김 | §9 STAGE2 성공기준=NEXT_STEPS 동등 풍부도. 미달 시 손작성 유지(fallback) |
| 평문 vault에 secret 유출 | STAGE2 secret 필터 + restricted/ seam |
| 메타-재귀 과게이트(토큰 과소비) | dev-tooling/product 경계 명시. 작은 STAGE는 표적검증, core/만 풀 3-Tier |
| 커밋 폭주(세션마다 vault 커밋) | 승격 게이트(STAGE5)로 전량 자동커밋 회피. 배치/수동 푸시 |
| Supabase scratch와 git vault 이중관리 혼선 | layering 명확화(§3.2): scratch=휘발 메모, vault=내구. 승격만 단방향 |

---

## §11 변경 이력
| 날짜 | 변경 |
|------|------|
| 2026-06-23 | 초안. 2026-06-23 대화 결정(D1~D6) + baseline 실측(§2) 동결. Status=Draft. |
| 2026-06-23 | af-cross-review R1 BLOCK 흡수: F1(High, Stop hook 자기모순)→§2.4·STAGE2·INV-K9 정정(증류 발화점=SessionEnd/PreCompact, session_adapter.py:690, Stop 아님). F2(§2.2 global_user_key 귀속오류→project_id 정정). F3(originating_pc 필드 미존재→STAGE2 산출물 명시). |
| 2026-06-23 | **R2 개정(§12)**: 목표 확장 솔로→**솔로+팀 연속성**(공개 퍼블리싱 명시 제외). D7~D11 추가, substrate 아키텍처 확정(git 단일·Supabase durable 제거·id-네임스페이스 멀티작성자 안전·브랜치 모델). STAGE 재배치(연속성 substrate 신규). 멀티PC·멀티작성자 코드 재검증(`sync_claude_memory.py:251` last-write-wins 실증). |
| 2026-06-23 | **R3 범위 확정(§13)**: D12((a) 프로젝트 vault 우선, 개인 cross-project vault 연기=seam만) + D13(retrieval 일급 스테이지 추가 — 토큰절약 레버는 축적 아닌 검색). 출처 hype(밸런스/자가병합/10x) 기각 유지(§3.7). 두 트랙(A=연속성, B=저비용구현) 공유 토대=STAGE 1+2, 첫 빌드=STAGE 1. |
| 2026-06-23 | **R2 cross-review BLOCK[single-vendor] 흡수** (codex rate-limited→Claude 단독): High#1(§12.4 파일명 무충돌 단언→마이크로초+rand suffix, "절대" 완화) / High#2(INV-K11 silent유실금지 불변식 과장→git 비폐기 보장+동일hunk surface로 범위 제한, "유실금지"는 운용지침 강등) / Med#3(§12.3 D8 P2 경로=세션종료 commit/push or 승격, STAGE3 배선) / ADV#4(§0 D1에 §12 확장 주석) / ADV#5(§12.7 MVP=솔로연속성+무충돌, 팀 교차공유는 연기). baseline 5주장 코드 대조 전부 확인. ⚠️ codex 재검증은 rate-limit(2026-06-25)까지 불가 — 현재 single-vendor. |

---

## §12 R2 개정 (2026-06-23) — 솔로+팀 연속성 아키텍처

> 이 섹션은 §0~§11의 **단일-사용자 전제를 확장**한다. 충돌 시 §12가 우선. 목표가 "솔로 단독"에서 "솔로 멀티PC + 팀 협업 연속성"으로 바뀌면서 substrate·멀티작성자·브랜치 결정이 §3.2 각주에서 일급 아키텍처로 승격됐다.

### 12.0 이 개정이 동결하는 추가 결정
| # | 결정 | 근거 (위치) |
|---|------|------------|
| D7 | 목표 = **솔로 멀티PC 연속성 + 팀 협업 연속성** (D1 확장) | §12.1 — 공개 퍼블리싱·팀 enforcement 엔진은 비범위 |
| D8 | **git 단일 durable** — Supabase를 지식 영구경로에서 제거 | §12.3 — 이중관리(§10) 소멸 + 팀에서 git이 충돌 surface |
| D9 | **멀티작성자 안전 = 2계층 + id-네임스페이스** | §12.4 — scratch append-only 무충돌 / durable git-surface |
| D10 | **브랜치 모델 = working-branch now, 전용 knowledge 브랜치 연기** | §12.5 — Simplicity First, worktree 복잡성 회피 |
| D11 | **`visibility`(기본 private) seam** 채택 (Allen 사례 흡수) | §12.6 — 미래 선택공개 0코드 문, enforcement 금지(INV-K6) |

### 12.1 목표 변경 + 새 통증
- **P5 — 팀 맥락 단절**: 팀원이 같은 repo로 일할 때 결정·교훈이 공유 안 되거나, 현 Supabase 동기화가 같은 노트 동시편집을 **silent 유실**시킨다(검증: §12.2). 솔로 통증 P1~P4는 그대로 유효.
- **비통증(추가)**: 공개 웹 퍼블리싱(Quartz/GitHub Pages)은 목표 아님 — `visibility` seam만 유지. 팀 enforcement 엔진(로그인/RBAC/동시편집 머지UI)도 아님 — git/GitHub CODEOWNERS·private repo로 상속(D4 유지).

### 12.2 재검증된 제약 (멀티PC·멀티작성자, file:line)
- **Supabase `claude_memory` = last-write-wins** (`scripts/sync_claude_memory.py:251` `on_conflict=project_id`). 파일머지(`:237 merged={**remote,**local}`)는 **다른 파일명만** 보호 → 같은 노트 두 PC/사용자 동시편집 시 **silent 유실**. = **팀 부적합**.
- **지식 2채널 분리**: `~/.claude/.../memory/*.md ↔ Supabase`(git 독립) + `docs/wiki/ ↔ git`(브랜치 종속, 154파일 tracked). = §10 이중관리 + P1 드리프트 근원.
- `scripts/session_bridge.py:408` truncate(260/4000)만, **commit/branch/hostname 필드 없음**. `core/knowledge/` 없음(STAGE 1 백지).

### 12.3 결정 D8 — git 단일 durable, Supabase durable 제거
- 영구 지식 = `docs/wiki/knowledge/` (git) **단일**. Supabase `claude_memory`를 지식 영구 저장에서 제거 → **이중관리(§10) 소멸 + 팀 안전**(git은 충돌을 silent 덮어쓰기 대신 **surface**).
- scratch는 **PC-local 미동기화**. keep 가치 생기면 vault로 **승격**(§3.2 layering 유지).
- 트레이드오프(인지함, **cross-review Medium #3 반영**): Supabase push 제거 후 솔로 **P2(맥락 단절)** 경로 = 세션 종료 시 scratch를 **git commit+push**(working 브랜치)하거나 durable로 **수동 승격**해야 다른 PC가 받음. 즉 "git pull만으로 도착"은 commit된 것에 한함 — 미commit scratch는 PC간 안 따라옴. **이 배선(세션종료→commit/push or 승격)은 STAGE 3에 포함.** Supabase의 **비-지식 scope**(project/global)는 본 설계 밖(별도 트랙, 제거 아님).

### 12.4 결정 D9 — 멀티작성자 안전: 2계층 + id-네임스페이스 (팀 연속성의 심장)
Supabase가 깨지는 이유 = 같은 키 silent 덮어쓰기. 해결은 **노트 입자성**으로:
- **scratch 캡처(세션 증류)**: 노트 = 단일작성자·id-네임스페이스 파일·**append-only**. id 스키마 = `{type}/{source_machine}-{created_at}-{rand}-{slug}.md` 여기서 `created_at`은 **마이크로초 해상도**(`20260623T141530-482193Z`)이고 `{rand}` = 짧은 무작위/내용해시 suffix(6자). **(cross-review High #1 반영)** 마이크로초만으로 충돌은 사실상 불가능하나, 만약의 동일-키 충돌 시 `{rand}`로 회피 → 두 작성자가 같은 파일을 만들 확률 **무시가능**, 충돌 시 자동 회피. 결과: **git 머지 무충돌**(서로 다른 파일).
- **durable 큐레이션 노트**: 주제별 **안정명(stable-name)**, 토픽당 1노트. 팀 공동편집 시 git이 충돌을 **surface**(Supabase처럼 silent 유실 아님) → 사용자가 머지 해소. durable 노트는 적고 토픽-소유라 충돌 드뭄.
- **폭증 방지**(사용자 우려 반영): append-only는 **scratch에만**. durable은 topic-merge(중복 시 갱신). scratch는 prunable + 승격 게이트가 durable 성장 통제(§3.2 / STAGE 다이어트).

### 12.5 결정 D10 — 브랜치 모델 (working-branch now, 전용 브랜치 연기)
- **지금**: 노트는 working 브랜치의 `docs/wiki/knowledge/`에 기록 → 일반 머지로 main 흐름. append-only id-네임스페이스라 머지 무충돌. 솔로 연속성(같은 브랜치 재개) 충족. 단순.
- **알려진 한계**: 교차 패턴(pattern/feedback)이 feature 브랜치에 갇혀 머지 전까지 타 브랜치/PC에 안 보임.
- **연기(enhancement)**: 전용 `af-knowledge` 브랜치(git worktree)로 교차 노트를 브랜치 독립 공유 — **필요 실증되면**. 지금 안 지음(Simplicity First; AF가 워킹트리 안 깨고 타 브랜치 커밋 = worktree/plumbing 크로스OS 복잡).
- type별 분기 자리(미래): session/decision=브랜치로컬, pattern/concept=교차(연기된 전용 브랜치 후보).

### 12.6 결정 D11 — 식별·접근 seam (D4 유지·강화)
- frontmatter `author`/`source_machine`/`created_commit`는 이제 **팀에서 load-bearing**(누가·어느 PC·어느 커밋). git author가 진짜 attribution.
- **`visibility`(기본 private)** 필드 — Allen 사례에서 흡수한 seam. 미래 선택 공개/`restricted/` 0코드 문. **enforcement 코드 금지**(INV-K6 유지).
- 팀 접근제어 = private repo + CODEOWNERS 상속(빌드 0).

### 12.7 STAGE 재배치
| STAGE | 내용 | 비고 |
|-------|------|------|
| 0 ✅ | vault 통합(`docs/wiki/`) | 완료 |
| 1 | KnowledgeNote 스키마 + seam | **+ id-네임스페이스 규칙 + `visibility` 필드** |
| 2 | 증류기(truncate→LLM, provider-neutral) | **+ commit/branch/source_machine 필드(F3) + secret 필터(팀 공유 repo 격상)** |
| **3 ★신규** | **연속성 substrate** | git-single 배선 + Supabase durable 제거 + scratch/durable 2계층 + `af knowledge on/off/status` + 멀티작성자 무충돌 실증 |
| 4 | Staleness/SKEW doctor (크로스OS) | (구 STAGE 3) 팀: 팀원 노트가 가리킨 미보유 커밋도 SKEW |
| 5 | 자동 링크(knowledge↔code) | (구 STAGE 4) |
| 6 | NEXT_STEPS 다이어트 + 승격 게이트 | (구 STAGE 5) 폭증 방지 핵심 |

**MVP = STAGE 1+2+3.** ⚠️ **(cross-review Medium #5 반영)** MVP는 **솔로 멀티PC 연속성 + 멀티작성자 안전(무충돌 캡처)**을 달성한다. 단 **팀의 교차패턴 브랜치-독립 공유**(feature 브랜치에 갇힌 pattern/feedback을 즉시 공유)는 D10에서 **연기된 전용 `af-knowledge` 브랜치**에 달려 있어 MVP 범위 밖 — 팀은 일반 git 머지(main 흐름)로 공유되며, 즉시-교차 공유가 필요하면 STAGE 3 이후 전용 브랜치 enhancement 필요.

### 12.8 추가 불변식
- **INV-K10**: 영구 지식 durable 저장은 **git vault 단일**. Supabase는 지식 영구 저장소 아님(이중관리 금지).
- **INV-K11**: 멀티작성자 안전 — scratch 노트는 **단일작성자·id-네임스페이스·append-only**(서로 다른 파일이라 동시쓰기 충돌 불가). **(cross-review High #2 반영)** durable 노트: git은 committed 변경을 **silent 폐기하지 않는다**(Supabase last-write-wins와의 핵심 차이) — **같은 region(hunk) 동시수정은 충돌로 surface**, 비중첩 수정은 자동머지(폐기 아님, 단 결합 결과는 미검토). "silent 유실 금지"는 불변식이 아니라 **운용 지침**(durable 공동편집은 PR 리뷰 규율)으로 강등. 자동머지된 노트의 의미 정합성은 STAGE 4 doctor + PR 리뷰가 잡음.
- **INV-K12**: 브랜치 모델 = working-branch(현재). 전용 knowledge 브랜치는 연기 — 채택 시 크로스OS worktree·워킹트리 비파괴.

### 12.9 검증 (R2 추가, Goal-Driven)
- **멀티작성자**: 두 PC가 (a) 다른 노트 (b) 같은 토픽 노트 동시 생성 → scratch는 무충돌, durable은 git이 충돌 **surface**(silent 유실 **0**) 실증 테스트.
- **git-single**: Supabase 미사용 경로에서 솔로 멀티PC 재개가 **`git pull`만으로** 맥락 도착.
- **크로스OS**: 노트 id/경로가 Windows 파일명 제약 통과 — ⚠️ `created_at` ISO의 `:`는 Windows 파일명 부적합 → **안전 인코딩 필수**(예: `20260623T141530Z`, 기존 `sync_claude_memory.py:70` `_path_to_claude_key`가 `:` 치환하는 선례). STAGE 1 설계 포인트.
- 기존 §9 표 + 위.

---

## §13 R3 범위 확정 (2026-06-23) — (a) 프로젝트 vault 우선 + retrieval 일급화

### 13.0 추가 결정
| # | 결정 | 근거 |
|---|------|------|
| D12 | **(a) 프로젝트별 vault 먼저** — 개인(범프로젝트) cross-project vault는 **연기**(seam만) | §13.1 — 메타-재귀 비용 회피, 프로젝트 vault+retrieval로 가치 실측 후 확장 |
| D13 | **retrieval(꺼내기)을 일급 스테이지로 추가** | §13.2 — 토큰 절약의 레버는 *축적*이 아니라 *검색*. 현 설계는 캡처만 있고 retrieval 부재 |

### 13.1 D12 — 프로젝트 vault 우선, 개인 서재 연기
- **지금**: 지식 vault = 각 프로젝트 repo의 `docs/wiki/` (STAGE 0 기반). 팀 공유·자동 증류.
- **개인 vault seam**: STAGE 1 스키마에 `scope: project|personal` 필드 자리만(기본 `project`). **라우팅·promote-to-personal·별도 personal repo·Obsidian 상위폴더 통합 = 연기**(0코드 문만 열어둠).
- **연기 근거**: 개인 서재는 (i) 별도 repo + (ii) 두 번 sync + (iii) Obsidian 교차링크 한계(한 vault만 링크) + (iv) project/personal 분류·승격 머신 = 관리 2배. 프로젝트 vault로 가치 실증 후 얹는다.

### 13.2 D13 — retrieval을 일급 스테이지로
- **문제**: 지식을 쌓아 컨텍스트에 통째 넣으면 토큰이 **늘어남**. 절약은 **검색**(task에 맞는 작은 조각만 인출)에서만 발생. 현 설계는 캡처(증류/저장/링크/점검)만 있고 *꺼내기*가 비어 있음.
- **신규 스테이지 R — Retrieval**: "task/변경파일 → 관련 결정·교훈·연관코드 노트 인출". **결정론 우선**(grep + 심볼/파일명 매칭, 기존 `af project symbols`·청킹 규칙 재사용), 임베딩은 보조(애매 케이스). 산출 = 컨텍스트에 넣을 bounded 노트 셋.
- 상세 설계는 스테이지 도달 시 별도(STAGE 2 이후). 본 R3는 **스테이지 존재·위치·원칙만 동결**.

### 13.3 기각 유지 (출처 hype 회귀 금지)
- 지식 밸런스("윤리 관점 부족" 등)·자동 자가병합·월간 풀스캔·"10x/100일/자가진화" = **비범위 유지**(§3.7 접지 원칙). 자동병합은 INV-K11 멀티작성자 안전과 정면충돌이라 특히 배제.

### 13.4 두 가치 트랙 (공유 토대)
- **트랙 A** (멀티PC+팀 연속성): STAGE 1 → 2 → 3(substrate).
- **트랙 B** (저비용 맥락인지 구현 = 주 목표): STAGE 1 → 2 → **R(retrieval)**.
- **공유 토대 = STAGE 1(스키마) + 2(증류).** → **첫 빌드 = STAGE 1.**
- 갱신 단계 순서: 0✅ / 1 스키마(+`scope` seam) / 2 증류 / 3 substrate / **R retrieval** / 4 doctor / 5 링크 / 6 다이어트.
