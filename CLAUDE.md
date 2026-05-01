# Agent Factory — Claude Code 지시사항

## 필수 규칙

### 세션 연속성 규칙 (2026-04-23 추가)
- **세션 시작 시**: `NEXT_STEPS.md`를 먼저 읽어 현재 진행 중인 작업과 우선순위를 파악한다
- **작업 완료 또는 세션 종료 전**: `NEXT_STEPS.md` 상태 업데이트 → `git commit` → `git push` → `python end_db.py agent-factory` (메모리 Supabase 동기화)
- **다른 PC에서 재개 시**: `git pull` → `python start_db.py agent-factory` (Supabase → 로컬 메모리 pull)
- Claude Code 메모리(`memory/`)는 PC별 로컬 저장 — `sync_claude_memory.py`가 Supabase `claude_memory` 테이블을 통해 동기화
- Supabase 미설정 시 `start_db`/`end_db` 실패하지 않고 경고만 출력하고 진행

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

### 교차검증 자동 실행
- UserPromptSubmit hook이 `[af-review-pending]` 메시지를 출력하면, **메시지의 `실행 에이전트:` 라인에 명시된 에이전트만** 실행한다 (Phase 0 — Tier 1은 af-test-runner 1개, Tier 2~3은 3-tier 순서)
- UserPromptSubmit hook이 `[af-design-review-pending]` 메시지를 출력하면, **반드시** af-cross-review **1개만** 실행한다 (설계문서 큐 자동 발화, scripts/check_design_pending.py)
- **단일 설계문서** (docs/YYYY-MM-DD-*.md) 작성 후에는 **af-cross-review만** 실행한다 (2026-05-01 변경: af-critic은 설계문서에서 소스 중복 탐색 비용만 발생, 효과 없음)
- **Work-item 문서 세트** (docs/work-items/<slug>/ 4개 문서) 작성·수정 후에는 af-doc-qa + af-cross-review **2개를 병렬 실행**한다
- 교차검증 결과에서 **BLOCK 판정 시에만** 발견 사항을 수정한다. **WARN은 advisory** — 자동 수정 의무 없음 (Phase 0 정책, 2026-04-30: 무한루프 방지)
- **Tier 3(af-cross-review)는 가용 외부 CLI 프로바이더 전부에 병렬 fan-out한다.** 외부 프로바이더 0개면 자동 SKIP(통과 간주), 1개 이상 인증 만료가 있으면 BLOCK + 재인증 안내. (`core/provider_detect.py` Step 0 감지)

### Review-Gate 규칙 (Phase 0 갱신 2026-04-30)
- `.py` 파일 수정 후 `git commit` 전 필수 tier 완주:
  - **Tier 1 파일** (docs/, README, 단순 설정): af-test-runner만
  - **Tier 2~3 파일** (core/, scripts/, 일반 코드): af-test-runner → af-critic → af-cross-review 순서
  - 분류는 `scripts/blast_radius.py`가 결정 (`subprocess`, `shell=True`, hook launcher 등은 자동 Tier 3)
- **max_rounds=2 캡** — 같은 큐는 최대 2라운드까지만 자동 발화. 이후엔 사용자가 수동 결정 (재리뷰 vs 우회)
- **WARN-only no-fire** — 직전 라운드가 BLOCK 없이 완료됐다면 (전부 WARN/PASS) 재편집해도 자동 재발화 안 함
- **게이트 우회** (긴급·부트스트랩 시): `AF_SKIP_REVIEW_GATE=1 git commit ...` (hook_events.log에 기록)
- `.py` 없는 커밋(문서·설정만)은 게이트 자동 통과
- 진단: `python3 scripts/review_gate.py --debug`

### 커밋 규칙
- 코드 수정 + Blueprint 업데이트는 같은 커밋
- 빌드 zip은 **GitHub Release로 배포**: `gh release create af-fsa_v{version} dist/af-{version}.zip --notes ...` (2026-04-14 정책 변경: LFS 미구성 환경에서 ~91MB zip이 GitHub 100MB 한계로 push 실패한 사례 이후. `dist/*.zip`은 `.gitignore` 처리)
- 태그 형식: `af-fsa_v{version}`

## Hook 설치 (레포 클론 후 1회)

```bash
git config core.hooksPath .githooks
```

이후 `core/*.py` 등 변경 커밋 시 `Master_Blueprint.md` 미스테이지 → 자동 차단.

## 프로젝트 개요
- **위치**: `C:\Project\agent-factory`
- **퍼블릭 레포**: `origin` = `https://github.com/hoonkim1092-web/af-fsa.git`
- **소스 레포**: `agent-factory` remote = `https://github.com/hoonkim1092-web/agent-factory.git`
- **현재 브랜치**: `2026-04-01-super-harness`
- **아키텍처 문서**: `Master_Blueprint.md` (845줄, 12섹션)
