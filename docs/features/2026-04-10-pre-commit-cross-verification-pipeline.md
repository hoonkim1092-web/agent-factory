# Pre-commit 교차검증 파이프라인 설계

> 날짜: 2026-04-10
> 상태: **v3 (af-critic BLOCK + af-doc-qa WARN 반영)**
> 관련 파일: `.githooks/pre-commit`, `scripts/pre_commit_review.py` (신규), `core/design_review_utils.py`

## 변경 이력

- **v1**: pre-commit에서 `claude -p` 직접 호출 → af-critic **BLOCK** (중첩 세션 충돌)
- **v2**: 비동기 큐 + 결과 확인 분리 → af-critic **BLOCK** (diff hash 매핑 미구현, 재귀 방지 실효성 없음)
- **v3**: 파일별 결과 수집 방식으로 전환, 불필요한 가드 제거

## 배경

코드 수정 후 수행해야 할 3가지 작업(Blueprint 업데이트, 코드 리뷰 문서, 교차검증)이 수동으로 돌아간다.
PostToolUse hook으로 ①②③은 자동화되어 있지만, 교차검증은 자동 트리거가 없어 매번 사용자가 리마인드해야 한다.

## 현재 상태

```
.py 파일 Edit/Write
  → [PostToolUse Hook]
     ① py_compile (5초) ✅ 자동
     ② code_review_updater.py (30초) ✅ 자동
     ③ blueprint_updater.py (30초) ✅ 자동
     ④ design_review_trigger.py (5초) ✅ 자동
        → 코드 파일: enqueue → watcher → 비동기 리뷰
        → 결과 저장: docs/reviews/{timestamp}-{stem}-code-review.md

git commit
  → [pre-commit Hook]
     ⑤ Blueprint 스테이징 체크 ✅ 자동
     ⑥ 교차검증 ❌ 없음
```

### 기존 결과 저장 구조 (변경하지 않음)

watcher는 파일 단위로 리뷰하고 결과를 `docs/reviews/`에 마크다운으로 저장한다:
```
docs/reviews/20260410-143520-cli-code-review.md
docs/reviews/20260410-143525-registry-code-review.md
```
각 파일에는 severity별 findings가 포함되어 있다.

> **v2에서 발견된 Critical 문제**: `{diff_hash}.json` 기반 설계는 현재 watcher의
> 파일 단위 저장 구조와 호환되지 않았다. v3는 기존 저장 구조를 그대로 사용한다.

## 목표 상태

```
.py 파일 Edit/Write
  → [PostToolUse Hook] (기존 유지)
     ①②③ 동일
     ④ design_review_trigger.py → 코드 파일 enqueue → watcher → 리뷰 결과 저장

git commit (core/*.py 변경 포함 시)
  → [pre-commit Hook]
     ⑤ Blueprint 스테이징 체크 (기존)
     ⑥ 교차검증 결과 수집 (신규)
        → 스테이지된 파일별로 docs/reviews/ 에서 최신 리뷰 결과를 수집
        → severity 집계하여 종합 판정
        → PASS/WARN → 커밋 진행
        → BLOCK → 커밋 차단
        → 결과 없음 → 경고 + 커밋 진행 (비차단)
```

## 핵심 설계 결정

1. **claude CLI를 호출하지 않는다** — 중첩 세션 충돌 방지 (v1 Critical)
2. **기존 저장 구조를 변경하지 않는다** — watcher의 `docs/reviews/` 마크다운 저장을 그대로 사용 (v2 Critical)
3. **verdict를 커밋 시점에 계산한다** — watcher 저장 시점의 판정이 아니라, `pre_commit_review.py`가 환경변수 기준으로 실시간 판정 (v2 Medium)
4. **비차단 원칙** — 교차검증 인프라 장애가 커밋을 차단하면 안 된다. BLOCK은 실제 코드 문제일 때만

## 설계

### 1. `scripts/pre_commit_review.py` (신규) — 결과 수집 + 판정

pre-commit hook에서 호출되는 경량 스크립트. **claude CLI를 호출하지 않는다.**

```
입력: git diff --cached --name-only (스테이지된 파일 목록)
동작:
  1. 스테이지된 .py 파일 목록 추출
  2. 각 파일에 대해 docs/reviews/ 에서 최신 리뷰 결과 검색
     - 파일명 패턴: *-{stem}-code-review.md
     - 결과 파일의 mtime이 소스 파일의 mtime보다 오래됐으면 "stale" 처리
  3. 리뷰 결과에서 severity 파싱 (Critical/High/Medium/Low 카운트)
  4. 환경변수 AF_PRE_COMMIT_REVIEW_BLOCK_ON 기준으로 판정
  5. 결과 출력 + exit code 반환
```

**판정 로직 (커밋 시점에 계산):**
```python
block_on = os.getenv("AF_PRE_COMMIT_REVIEW_BLOCK_ON", "high")
if block_on == "critical":
    blocked = total_critical > 0
elif block_on == "high":
    blocked = total_critical > 0 or total_high > 0
```

**결과 파일 검색:**
```python
# stem = "cli" (from "core/providers/cli.py")
# 패턴: docs/reviews/*-cli-code-review.md
# 가장 최신(mtime 기준) 파일을 선택
# 소스 파일보다 오래됐으면 stale → "결과 없음"으로 처리
```

> **v2 문제 해결**: diff hash 대신 파일명 stem 기반 매칭.
> 1:N 매핑 문제 없음 — 파일별로 개별 수집 후 종합 집계.

### 2. `.githooks/pre-commit` 수정

기존 Blueprint 체크 후 결과 확인 스크립트를 호출한다.

```sh
#!/bin/sh
# pre-commit hook: Blueprint 체크 + 교차검증 결과 확인

BLUEPRINT="Master_Blueprint.md"
STAGED=$(git diff --cached --name-only)

# ── 기존: Blueprint 스테이징 체크 ──
CODE_CHANGED=$(echo "$STAGED" | grep -E "^(core/|model_utils\.py|run_factory_cli\.py|version\.py|af\.spec|install-af\.ps1)" | head -1)

if [ -n "$CODE_CHANGED" ]; then
    BLUEPRINT_STAGED=$(echo "$STAGED" | grep "^$BLUEPRINT$")
    if [ -z "$BLUEPRINT_STAGED" ]; then
        echo ""
        echo "⚠️  [pre-commit] 코드 변경 감지: $CODE_CHANGED"
        echo "   Master_Blueprint.md 가 스테이지되지 않았습니다."
        echo ""
        echo "   git add Master_Blueprint.md && git commit"
        echo "   또는: git commit --no-verify"
        echo ""
        exit 1
    fi
fi

# ── 신규: 교차검증 결과 확인 ──
if [ "${AF_PRE_COMMIT_REVIEW:-1}" != "0" ]; then
    REVIEW_TARGET=$(echo "$STAGED" | grep -E "^(core/.*\.py|model_utils\.py|run_factory_cli\.py)$" | head -1)
    if [ -n "$REVIEW_TARGET" ]; then
        # venv python 사용 (시스템 python에 yaml 등 의존성 없을 수 있음)
        VENV_PYTHON="$(git rev-parse --show-toplevel)/.venv/bin/python3"
        if [ -x "$VENV_PYTHON" ]; then
            "$VENV_PYTHON" scripts/pre_commit_review.py 2>&1
            REVIEW_EXIT=$?
        else
            python3 scripts/pre_commit_review.py 2>&1
            REVIEW_EXIT=$?
        fi
        if [ $REVIEW_EXIT -ne 0 ]; then
            echo ""
            echo "⚠️  교차검증 BLOCK. 발견 사항을 수정 후 다시 커밋하세요."
            echo "   건너뛰려면: git commit --no-verify"
            echo ""
            exit 1
        fi
    fi
fi

exit 0
```

> **트리거 범위 설계 근거**: Blueprint 체크는 `version.py`, `af.spec` 등도 포함하지만,
> 교차검증은 코드 로직 변경(`core/*.py`, `model_utils.py`, `run_factory_cli.py`)만 대상.
> 설정 파일 변경은 교차검증 불필요.

### 3. 재귀 호출 분석

> **v2에서 제안한 `AF_IN_PRE_COMMIT` 환경변수는 제거한다.**
>
> 이유: pre-commit hook은 git이 실행하는 셸 프로세스이고,
> `pre_commit_review.py`는 claude CLI를 호출하지 않는다.
> PostToolUse hook은 Claude Code가 별도 프로세스로 실행하므로
> pre-commit 셸의 환경변수가 전파되지 않는다.
> 재귀 호출이 발생하는 경로 자체가 없으므로 가드가 불필요하다.

### 4. 출력 예시

**PASS:**
```
  ✅ [교차검증] PASS — 5 파일 검증, 0 Critical, 0 High, 1 Medium, 2 Low
```

**WARN (결과 없음):**
```
  ⚠️ [교차검증] 리뷰 결과 없음 — 3/5 파일 미검증 (watcher 실행 대기 중일 수 있음)
     커밋을 진행합니다. 리뷰 완료 후 확인하려면: python3 scripts/pre_commit_review.py --status
```

**BLOCK:**
```
  ❌ [교차검증] BLOCK — 1 High 발견
     → core/providers/cli.py: nvm 버전 정렬이 최신 버전을 선택하지 못함
     건너뛰려면: git commit --no-verify
```

### 5. 환경변수 제어

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `AF_PRE_COMMIT_REVIEW` | `1` | `0`으로 비활성화 |
| `AF_PRE_COMMIT_REVIEW_BLOCK_ON` | `high` | `critical`=Critical만 차단, `high`=High 이상 차단 |

### 6. 에러 처리

| 실패 모드 | 동작 |
|-----------|------|
| watcher 미실행 (결과 파일 없음) | `⚠️ 리뷰 결과 없음` 경고 + 커밋 진행 |
| watcher 실행 중 (리뷰 미완료) | 동일 — 결과 없음으로 처리. 출력에 "watcher 실행 대기 중일 수 있음" 안내 |
| 결과 파일은 있으나 소스보다 오래됨 (stale) | stale 파일 무시, "결과 없음"으로 처리 |
| 결과 파일 파싱 실패 | WARN + 파싱 실패 파일 경로 출력 + 커밋 진행 |
| venv python 없음 | fallback으로 `python3` 사용, 그래도 실패하면 커밋 진행 |
| 일일 리뷰 한도 도달로 watcher가 스킵 | 결과 없음으로 처리 + 커밋 진행 |
| staged diff와 리뷰 시점의 diff가 다름 | mtime 비교로 stale 감지 → 결과 없음으로 처리 |

> **원칙: 교차검증 인프라 장애가 커밋을 차단하면 안 된다.**

### 7. 기존 시스템과의 관계

| 시스템 | 역할 | 이 설계와의 관계 |
|--------|------|-----------------|
| `CrossVerificationLoop` (§3.7) | FSA 런타임 태스크 검증 | 재사용하지 않음. 별도 경량 시스템 |
| `design_review_trigger.py` | PostToolUse 큐 트리거 | 기존 그대로 사용. 코드 파일 enqueue가 교차검증의 입구 |
| `design_review_utils.py` | enqueue/watcher 큐 인프라 | 기존 그대로 사용 |
| `design_review_watcher.py` | 큐 소비 + 리뷰 실행 + 결과 저장 | 기존 그대로 사용. `docs/reviews/` 저장 구조 변경 없음 |
| `code_review_updater.py` | 코드 리뷰 문서 업데이트 | 별개 역할. `docs/code_review/`와 `docs/reviews/`는 별도 |

### 8. 비용 제어

- watcher의 리뷰는 `check_code_review_budget()`의 일일 한도 내에서만 수행
- mtime 기반 stale 감지로 이미 검증된 파일의 재검증 방지
- `AF_PRE_COMMIT_REVIEW=0`으로 완전 비활성화 가능

## 파일 변경 목록

| 파일 | 변경 유형 | 비고 |
|------|----------|------|
| `scripts/pre_commit_review.py` | 신규 | 결과 수집 + 판정 (경량, claude 미호출) |
| `.githooks/pre-commit` | 수정 | 결과 확인 호출 추가 |
| `Master_Blueprint.md` | 수정 | §7 안전장치에 pre-commit 교차검증 하위 섹션 신설 |

> 기존 `design_review_utils.py`, `design_review_watcher.py`, `design_review_trigger.py`는 **변경하지 않는다.**

## 구현 순서

1. `scripts/pre_commit_review.py` 작성 (결과 수집 + severity 파싱 + 판정)
2. `.githooks/pre-commit` 수정 (결과 확인 호출)
3. Blueprint §7 업데이트
4. 테스트

## 테스트 시나리오

| # | 시나리오 | 기대 결과 |
|---|---------|----------|
| 1 | `core/*.py` 변경 + 리뷰 결과 있음 + High 0건 | PASS, exit 0 |
| 2 | `core/*.py` 변경 + 리뷰 결과 있음 + High 1건 | BLOCK, exit 1 |
| 3 | `core/*.py` 변경 + 리뷰 결과 없음 | WARN "결과 없음", exit 0 |
| 4 | `core/*.py` 변경 + 리뷰 결과 stale | WARN "결과 없음", exit 0 |
| 5 | `core/*.py` 미변경 (설정 파일만) | 교차검증 스킵, exit 0 |
| 6 | `AF_PRE_COMMIT_REVIEW=0` 설정 | 교차검증 스킵, exit 0 |
| 7 | `AF_PRE_COMMIT_REVIEW_BLOCK_ON=critical` + High 1건 | WARN, exit 0 |
| 8 | venv python 없음 + 시스템 python3 없음 | 에러 출력 + exit 0 (비차단) |

## 수락 기준

1. `core/*.py` 수정 후 커밋 시, `pre_commit_review.py`가 exit 0으로 종료하고 stdout에 `[교차검증]` 문자열이 포함된다
2. High 이상 발견 시 `pre_commit_review.py`가 exit 1로 종료하고 발견 사항이 출력된다
3. 결과 없음 시 stdout에 `리뷰 결과 없음` 경고가 출력되고 exit 0이다
4. `--no-verify`로 전체 스킵 가능하다 (git 기본 동작)
5. 테스트 시나리오 8개 모두 통과한다
