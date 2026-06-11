# 멀티 프로바이더 지침 SSOT 정합성 설계 (WI-A)

- 작성일: 2026-06-11 (Opus)
- 브랜치: `2026-06-04-right-sized-execution-slice1`
- 근거 메모리: `project_provider_instruction_parity`, `feedback_pipeline_deploy_parity`, `feedback_no_hardcode_single_type_source`
- 구현 모델: Sonnet (설계 수렴 후 — 재설계 금지)

---

## 1. 문제 (grep 확정 — 재논쟁 금지)

세 프로바이더 지침 파일이 **내용·카테고리 전부 다르다.**

| 파일 | 줄 수 | 성격 | 소비 프로바이더 | 생성 방식 |
|------|------|------|----------------|-----------|
| `CLAUDE.md` | 198 | 실무 규칙 (타입 SSOT, 하드코딩 금지, 리뷰 게이트, 커밋, Blueprint 동기화, Karpathy) | Claude Code | 수동 편집 |
| `GEMINI.md` | 149 | 정체성·철학 헌법 (페르소나, 엔진 역할분담, planning-first) | Gemini CLI | 수동 편집 |
| `AGENTS.md` | 25 | 에이전트 명단 테이블 | Codex | `generate_agents_md.py` 자동생성 |

→ **Claude 외 프로바이더로 작업하면 실무 규칙 0 전달.** Codex는 AGENTS.md(명단만), Gemini는 GEMINI.md(철학만)를 받는다.

### 1.1 핵심 모순 (코드 증거)

- `scripts/session_bridge.py:13` `NOISE_PREFIXES`에 `"# AGENTS.md instructions"` 존재 = AF는 **Codex가 AGENTS.md를 작업지침으로 읽는다는 걸 코드로 안다.**
- 그런데 `scripts/generate_agents_md.py:296` `output_path.write_text(...)`가 AGENTS.md를 **에이전트 명단으로 통째 덮어씀** → 지침 채널을 카탈로그가 점유.

### 1.2 부수 발견 (설계 영향)

`generate_agents_md.py`는 **pre-commit에서 자동 호출되지 않는다** (`.githooks/pre-commit` grep 확인 — `build_llm_wiki.py`만 staged 트리거로 자동, L70-78). AGENTS.md는 수동 재생성에 의존 → 신규 generator도 pre-commit에 물려야 sync가 유지된다.

---

## 2. 합의된 결정 (사용자 위임, Opus 확정)

| # | 결정 포인트 | 확정 | 근거 |
|---|------------|------|------|
| 1 | 공통 SSOT 위치 | **신규 `INSTRUCTIONS.md` (루트)** | CLAUDE.md엔 Claude 전용(Skill/hook)과 공통이 섞여 SSOT로 쓰면 추출 로직이 지저분. 별도 SSOT가 깨끗 + LLM Wiki 청킹 재생성과 같은 generate 패턴 |
| 2 | AGENTS.md 명단 이전처 | **AGENTS.md 내 2섹션** ([공통 지침]+[에이전트 명단]) | Codex가 한 파일에서 지침+명단 둘 다 받음. session_bridge 등 명단 참조처 재배선 불필요 |
| 3 | 합성 정책 | **공통 + 프로바이더 전용 분리** | Gemini 정체성 헌법·Claude Skill/hook 지침을 죽이지 않으면서 공통 실무 규칙만 3곳 공유 |

---

## 3. 합성 방식: marker-injection (full-generate 기각)

### 3.1 기각된 대안

- **(A) full-generate**: INSTRUCTIONS.md → CLAUDE/GEMINI 전체 자동생성. 기각 — 기존 수동 편집 워크플로를 깨고, GEMINI.md 헌법·CLAUDE.md Claude 전용 섹션을 generator가 재현해야 함(복잡·취약).
- **(B) include/reference만**: 3파일이 "INSTRUCTIONS.md를 읽어라"고 참조. 기각 — Claude Code는 `@path` import를 지원하나 Codex/Gemini의 include 메커니즘이 불확실. 실무 규칙이 실제 전달되는지 보장 불가(= 문제 재발).

### 3.2 채택: marker-injection

각 프로바이더 파일에 마커 쌍을 두고, generator가 **마커 사이만** INSTRUCTIONS.md 공통 블록으로 교체. 마커 밖은 프로바이더 전용 수동 유지.

```
<!-- AF-COMMON-START (generated from INSTRUCTIONS.md — DO NOT EDIT between markers) -->
... INSTRUCTIONS.md 공통 블록 전문 ...
<!-- AF-COMMON-END -->
```

- **CLAUDE.md**: 마커 사이 = 공통 블록. 마커 밖 = Claude 전용(교차검증 자동 실행 L135-142, Review-Gate 에이전트 메커니즘 L144-154, Agent Model Routing L156-178, Hook 설치 L185-191).
- **GEMINI.md**: 마커 사이 = 공통 블록. 마커 밖 = 정체성·철학 헌법(현 §1~§6 전문).
- **AGENTS.md**: 전체가 generated. 구조 = 마커 사이 공통 블록 + 에이전트 명단 테이블.

가장 surgical: 기존 워크플로 변화 최소, SSOT 1곳, drift는 테스트로 봉인.

---

## 4. 공통 블록 — 무엇을 INSTRUCTIONS.md에 넣는가

CLAUDE.md 현 섹션의 공통/전용 분류 (line 좌표 = 현재 CLAUDE.md):

### 4.1 INSTRUCTIONS.md로 이전 (공통, 프로바이더 중립)

| CLAUDE.md 현 위치 | 섹션 | 비고 |
|------|------|------|
| L3-57 | LLM 행동 원칙 (Karpathy) | KARPATHY 마커 유지 |
| L63-67 | 타입 SSOT 규칙 | |
| L69-73 | 절대경로 하드코딩 금지 | |
| L75-80 | 파이프라인 배포 동등성 | |
| L82-87 | 세션 연속성 규칙 | |
| L89-94 | Dogfood Run PC 핸드오프 | |
| L96-108 | Master_Blueprint 참조 의무 + 업데이트 트리거 | |
| L110-114 | 버전 및 빌드 | |
| L116-120 | 문서 파일명 규칙 | |
| L122-127 | ADR 명명 규칙 | |
| L129-133 | 스킬 흡수 귀속 정책 | |
| L180-183 | 커밋 규칙 | |
| L193-198 | 프로젝트 개요 | |

**Review-Gate (L144-154)는 분할**: 공통 부분 = "`.py` 수정 후 `git commit` 전 코드 리뷰 필수. `.githooks/pre-commit`의 review-gate가 이를 강제. 우회: `AF_SKIP_REVIEW_GATE=1 git commit`. 진단: `python3 scripts/review_gate.py --debug`." (프로바이더 중립 — Codex/Gemini도 git commit 시 동일 게이트 통과 필요). Tier 분류·blast_radius·max_rounds도 공통(게이트 동작).

### 4.2 마커 밖 유지 (Claude 전용)

| CLAUDE.md 현 위치 | 섹션 | 전용 이유 |
|------|------|----------|
| L135-142 | 교차검증 자동 실행 | UserPromptSubmit hook + Agent tool + `af-*` 에이전트 이름 = Claude Code 전용 메커니즘 |
| L144-154 중 에이전트 부분 | Review-Gate 에이전트 순서 (af-critic→af-cross-review→af-test-runner) | Agent tool spawn = Claude 전용 |
| L156-178 | Agent Model Routing | agent frontmatter `model:` = Claude 전용 |
| L185-191 | Hook 설치 (`git config core.hooksPath`) | 공통이나 부트스트랩 1회 — Claude 섹션에 유지(중복 회피, 향후 INSTRUCTIONS로 승격 가능) |

> ⚠️ **설계 주의**: 4.1/4.2 경계는 "프로바이더 중립으로 표현 가능한가"가 기준. Review-Gate처럼 개념(공통)과 메커니즘(전용)이 섞인 항목은 공통 블록엔 중립 요약, 전용 블록엔 Claude 에이전트 상세를 둔다. 중복 최소화하되 Codex/Gemini가 "커밋 전 리뷰가 강제된다"는 사실을 반드시 알게 한다.

---

## 5. 구현 컴포넌트

### 5.1 신규: `INSTRUCTIONS.md` (루트)

공통 블록 SSOT. §4.1 섹션 전문. 상단에 `<!-- 이 파일이 공통 실무 규칙의 SSOT입니다. 편집 후 scripts/sync_provider_instructions.py 또는 pre-commit이 CLAUDE/AGENTS/GEMINI에 전파합니다. -->`.

### 5.2 신규: `scripts/sync_provider_instructions.py`

- `INSTRUCTIONS.md` 읽기 → 공통 블록 텍스트 추출.
- CLAUDE.md / GEMINI.md: `AF-COMMON-START`/`AF-COMMON-END` 마커 사이를 공통 블록으로 교체 (마커 없으면 에러 — 최초 1회 수동 마커 삽입 필요, §7).
- AGENTS.md: `generate_agents_md.py`의 `collect_records()` + 명단 render를 import 재사용 → [마커+공통 블록] + [에이전트 명단] 합성 후 write.
- 멱등성: 재실행 시 변경 0 (drift 없을 때 write skip 또는 동일 내용).
- 마커 상수는 모듈 SSOT 1곳 정의 (`feedback_no_hardcode_single_type_source` — 매직 스트링 금지).
- 인코딩: `utf-8` write (CRLF는 .gitattributes + pre-commit renormalize가 처리).

### 5.3 수정: `scripts/generate_agents_md.py`

- `render_markdown()`을 **명단 섹션만 만드는 함수**와 분리 (예: `render_roster(records, label)`). 기존 `render_markdown`은 호환 위해 헤더+roster 조합 유지하거나, `sync_provider_instructions.py`가 roster 부분만 사용.
- **타입/함수 재선언 금지** — `collect_records`/`AgentRecord`는 import 소비만 (SSOT).
- **단독 실행 회귀 방지 (cross-review 갭2 반영 — 실재 결함)**: 현재 `python scripts/generate_agents_md.py`는 공개 CLI이고 한 번 실행하면 AGENTS.md를 roster-only로 덮어 마커+공통 블록을 삭제한다. → **`generate_agents_md.py`는 roster 라이브러리로 전환하고 AGENTS.md 최종 write 책임은 `sync_provider_instructions.py`로 단일화**(generator 이원화 방지). `generate_agents_md.py` `main()`은 AGENTS.md를 직접 write하지 않고 (a) sync로 위임하거나 (b) 마커+공통 블록 누락 산출을 방지하도록 변경. 이 회귀는 INV-8로 봉인(§6).

### 5.4 수정: `.githooks/pre-commit`

> ⚠️ **cross-review 갭1 반영 (실재 결함)**: LLM Wiki 트리거는 `|| true`로 실패를 삼킨다(wiki는 부가 인덱스 — 실패해도 검색 정확도만 저하). 그러나 provider sync는 **SSOT 정합성 보장**이 목적 — `|| true`로 실패를 삼키면 drift된 파일이 commit돼 설계 목적과 직접 모순. → **`|| true` 금지, sync 실패 시 exit code 전파(commit 차단).**

`build_llm_wiki` 트리거(L70-78) 패턴을 따르되 **실패는 차단**:

```sh
# Provider instructions: regenerate when SSOT or agent YAMLs are staged.
# SSOT sync failure MUST block commit (drift prevention) — no `|| true`.
INSTR_TRIGGER=$(echo "$STAGED" | grep -E "^(INSTRUCTIONS\.md|agents/.*\.(yaml|yml))$" | head -1)
if [ -n "$INSTR_TRIGGER" ]; then
    "$HOOK_PY" "${REPO_ROOT}/scripts/sync_provider_instructions.py" --workspace "${REPO_ROOT}"
    SYNC_EXIT=$?
    if [ $SYNC_EXIT -ne 0 ]; then
        echo ""
        echo "⛔ [pre-commit] provider instruction sync failed (exit $SYNC_EXIT)."
        echo "   Fix INSTRUCTIONS.md markers / agents YAML, then retry."
        echo "   Bypass: AF_SKIP_REVIEW_GATE=1 is NOT applicable — this is SSOT integrity."
        echo ""
        exit 1
    fi
    for f in CLAUDE.md AGENTS.md GEMINI.md; do
        if git diff --name-only 2>/dev/null | grep -q "^${f}$"; then
            git add "$f" 2>/dev/null || true
        fi
    done
fi
```

- 위치: review-gate PASS 이후, LLM Wiki 트리거 부근. (INSTRUCTIONS.md/agents YAML은 `.py`가 아니므로 review-gate 자동 통과 — L153.)
- **부트스트랩 안전**: 마커는 §7 Step 2-3에서 최초 1회 수동 삽입. 이후 항상 존재하므로 정상 경로에선 sync가 exit 0. exit≠0은 진짜 실패(마커 누락/import 오류/roster 렌더 실패)에만 발생 = 차단이 정당.
- **drift는 실패가 아님**: sync가 파일을 갱신(=drift 발견 후 정정)하는 것은 정상 — exit 0 + git add. 차단 대상은 sync 스크립트 자체 오류뿐.

---

## 6. 테스트 (test-first, 강제 불변식)

| ID | 검증 | 방법 |
|----|------|------|
| INV-1 | 3파일 모두 `AF-COMMON-START`/`AF-COMMON-END` 마커 존재 | 파일 read |
| INV-2 | 각 파일 마커 사이 내용 == INSTRUCTIONS.md 공통 블록 (drift 0) | sync 실행 후 비교 |
| INV-3 | `sync_provider_instructions` 멱등 (2회 실행 = 1회 결과) | 연속 실행 diff 0 |
| INV-4 | AGENTS.md에 에이전트 명단 + 공통 블록 둘 다 존재 | `agents/*.yaml` 행 ∩ 공통 마커 |
| INV-5 | 마커 누락 파일에 sync 실행 → 명시적 에러 (silent pass 금지) | 마커 제거 fixture |
| INV-6 | `AgentRecord`/`collect_records` 재선언 0 (import only) | `test_coding_conventions` 자동 + grep |
| INV-7 (배포 동등성) | pre-commit 트리거가 INSTRUCTIONS.md/agents YAML staged 시 sync 호출 **+ 실패 시 차단(`|| true` 부재)** | `.githooks/pre-commit` grep (`sync_provider_instructions` 호출 + `exit 1` 경로 존재 확인) + `tests/test_llm_wiki_precommit.py` 패턴 복제 |
| INV-8 (단독 실행 회귀) | `generate_agents_md.py`가 AGENTS.md를 직접 write하지 않거나, write 시 마커+공통 블록 보존 | roster 라이브러리화 후 `main()`이 마커 없는 산출을 만들지 않는지 검증 |

`feedback_pipeline_deploy_parity`: 테스트 픽스처만 PASS는 미완료 — pre-commit production 경로(INV-7)까지 연결 확인.

---

## 7. 구현 순서 (Sonnet)

0. **test-first**: INV-1~8 RED 작성 (`tests/test_provider_instruction_sync.py`).
1. `INSTRUCTIONS.md` 생성 — CLAUDE.md §4.1 공통 섹션 이전 (프로바이더 중립 문구로 Review-Gate 요약 작성).
2. CLAUDE.md 편집 — 공통 섹션을 마커 쌍으로 교체(마커 사이엔 INSTRUCTIONS 동일 내용), 마커 밖 = §4.2 Claude 전용만 남김.
3. GEMINI.md 편집 — 헌법 위/아래 적절 위치에 마커 쌍 삽입.
4. `scripts/sync_provider_instructions.py` 신규.
5. `scripts/generate_agents_md.py` roster 분리 리팩토링 (surgical).
6. `.githooks/pre-commit` 트리거 추가.
7. sync 1회 실행 → 3파일 동기화 → INV GREEN.
8. `af.spec` hiddenimports에 신규 스크립트 추가 여부 확인 (scripts/ 는 hiddenimports 대상 아님 — core/*.py만. 확인 후 불요면 skip).
9. 3-Tier: af-critic → af-cross-review → af-test-runner.

> **하드코딩 금지 / 타입 SSOT 강제** (`feedback_no_hardcode_single_type_source`): 마커 문자열·파일명은 명명 상수 SSOT, `AgentRecord` 등 타입은 import 소비만.

---

## 8. 비범위 (WI-B / 보류)

- **WI-B STEP1** (LLM Wiki 청킹본 우선 read 지침)은 본 WI-A 공통 블록(INSTRUCTIONS.md §Master_Blueprint 참조 의무 부근)에 **한 줄 추가**로 흡수 가능 — 단 본 설계 1차 범위에선 제외, WI-A 머지 후 별도 작은 PR로 추가(설계 단순성 유지). 별도 결정 불요.
- **WI-B STEP2** (외부 프로젝트 AST 인덱스)는 독립 기능 — 별도 설계.
- Hook 설치 섹션의 INSTRUCTIONS 승격은 향후 과제.

---

## 9. 리스크 / 트레이드오프

- **워크플로 변화**: 앞으로 공통 규칙은 CLAUDE.md가 아닌 INSTRUCTIONS.md에서 편집. CLAUDE.md 마커 사이는 "DO NOT EDIT". → INV-5 에러 + 마커 주석으로 방어.
- **중복 vs 명료성**: Review-Gate가 공통(중립 요약)+전용(Claude 상세) 양쪽에 일부 중복. 의도적 — Codex/Gemini가 게이트 존재를 알아야 함.
- **generator 이원화 위험** (cross-review 갭2): AGENTS.md를 sync와 generate_agents_md 둘이 건들면 충돌. → **확정 처방**: AGENTS.md 최종 write는 sync 단독, generate_agents_md는 roster 라이브러리로만(§5.3). INV-8로 봉인.
- **단일 벤더 cross-review 한계 (2026-06-11)**: 본 설계의 1차 cross-review에서 Codex가 Round 3 응답 없이 종료(usage/채널 문제) → Claude 단독 판정. WARN 2건(갭1·갭2)은 본 개정으로 반영 완료. 구현 후 3-Tier에서 외부 프로바이더 가용 시 재검증.
- **단일 벤더 리뷰 한계**: 본 설계 자체의 cross-review는 가용 외부 프로바이더에 fan-out (provider-0이면 SKIP=PASS).
