# AF 개발방식 전환 결정 (2026-05-14)

## 배경 / 문제 진단

### 사용자 불만 (트리거)
"개발이 느리고 토큰 소모가 크다. Harness / Hermes / Oh My OpenAgent 같은 외부 도구를 쓸까?"

### AF 메타-재귀 함정
AF는 "에이전트가 에이전트를 만드는 시스템"이라는 비전인데, 정작 자기 자신은 **사람 1명 + Claude Code 1세션**이 손으로 만들고 있다.
그 결과:
- Phase A/B/C + ADR + 3-tier review-gate 등 **governance 레이어만 누적 증가**
- 손 개발 속도는 governance 복잡도에 비례해 **더 느려짐**
- AF의 자동화 인프라가 AF 자신의 개발에는 적용되지 않는 아이러니

### Codex 제안 분석
외부 검토(Codex)에서 받은 제안의 **80%가 AF에 이미 존재**:
- `scripts/blast_radius.py`: Tier 1/2/3 자동 분류 (`.githooks/`, `.codex/hooks.json`, `subprocess`, `shell=True` 자동 Tier 3)
- `CLAUDE.md` L126-127: Tier 1=af-test-runner만, Tier 2~3=3-tier review-first 순서
- WARN-only no-fire (L131), max_rounds=5 cap (L129), AF_SKIP_REVIEW_GATE 우회 (L132)

---

## 채택 결정 (우선순위 순)

### 1. Hook 부산물 → review-gate 오탐 버그 fix (최우선)
**증상**: 사용자가 3파일만 수정했는데 `[review-gate] BLOCK: new-files-added` 차단 발생.

**원인**: hook(af-critic/af-cross-review)이 `git commit` 실행 도중 `docs/reviews/2026-05-14-*.md`를 자동 생성 → review-gate가 이를 "사용자가 추가한 새 파일"로 잘못 감지 → BLOCK.

**결과**: 매번 `AF_SKIP_REVIEW_GATE=1` 우회 강제 → review-gate 안전장치 사실상 무효화.

**fix 방향**: review-gate에서 hook 실행 도중 생성된 파일(`docs/reviews/`, `docs/work-items/` 자동 산출물)을 new-files-added 검사에서 제외.

### 2. Worktree 병렬 개발
- `skills/git_worktrees/` 이미 흡수 완료
- **목표**: 2~3개 worktree를 동시에 운영해 직렬 개발 병목 해소
- **셋업 계획**: `wt-fast-cleanup` (빠른 정리 작업용) + `wt-dogfood` (dogfooding 전용) 두 개로 분리
- 각 worktree에서 독립적인 Claude Code 세션 운영

### 3. AF dogfooding
- `project_pipeline.py`를 AF 자신에게 dry-run 적용
- **목표**: 마찰/실패 지점 발견 → 기록 → 우선순위 반영
- 큰 아키텍처 변경 X — 관찰과 기록이 목적

### 4. af-critic HIGH+ → cross-review 자동 승격
- Codex 제안 중 유일하게 AF에 없는 새로운 알맹이
- af-critic 결과가 HIGH 이상일 때 자동으로 Tier 3(af-cross-review) 진입
- 현재는 수동 판단 → 자동화로 review-gate 결정 지연 제거

---

## 거절 결정 (over-engineering)

### 특화 에이전트 6명 팀
제안 내용: Core Architect, Hook Engineer, Skill Engineer, Memory Engineer, QA Engineer, Docs Maintainer 분리 운영.

**거절 근거 (데이터)**:
최근 10개 커밋 중 5~6개가 cross-cutting (multi-domain):
- `053efbe0`: 7파일, 4도메인 교차
- `4851c305`, `a6c08d56`, `f69ff076`: 각각 4도메인 교차

specialist를 분리하면 hand-off 비용 > 효과. 현재 AF 작업 패턴에 맞지 않음.

### Phase D specialist team
위와 동일한 이유로 거절.

### 외부 도구 본격 도입 (Harness / Hermes / Oh My OpenAgent)
- 내부적으로는 **동일한 모델 API 호출** → 토큰 절약 없음
- AF의 governance (3-tier review, blast_radius.py, review-gate) 우회됨 → 안전성 손실
- 시범 사용은 가능하나 본격 마이그레이션 ROI 음수

---

## 부채 목록 (후순위)

| 항목 | 규모 | 우선순위 |
|------|------|---------|
| NEXT_STEPS.md slim down | 1680줄, ~30k 토큰/세션 | 낮음 |
| docs/reviews/ 자동 정리 | hook 부산물 누적 | hook 버그 fix 이후 |
| AF dogfooding 결과 반영 | dry-run 이후 결정 | dogfooding 이후 |

---

## 다음 실행 순서

1. **hook 부산물 버그 fix** (`scripts/review_gate.py` 또는 `.githooks/pre-commit` 수정)
2. **worktree 셋업** — `wt-fast-cleanup`, `wt-dogfood` 생성
3. **dogfooding** — `project_pipeline.py` dry-run, 마찰 지점 기록
4. **af-critic HIGH 승격 로직** 구현
