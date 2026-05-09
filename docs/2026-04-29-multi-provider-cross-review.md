# Multi-Provider Cross-Review 동적 fan-out — Design (v1)

<!-- created: 2026-04-29 | purpose: af-cross-review (Tier 3) 서브에이전트가 가용한 외부 CLI 프로바이더 전부에 병렬 리뷰를 요청하도록 동적 fan-out 도입. 1-provider 환경(Claude only)에서는 자동 skip, 2+ provider 환경에서는 codex+gemini 등 병렬 호출. auth_expired는 BLOCK + 우회 가이드. | author: Claude (design) -->

---

## 0. 배경 & 목표

### 현재 상태
- `.claude/agents/af-cross-review.md` Step 2가 **codex 단일 호출로 하드코딩**되어 있음 (`codex exec -s danger-full-access ...`).
- `core/providers/registry.py`는 이미 `detect_installed_cli_providers()`(60초 메모리 캐시) + `pick_review_provider()`(작성자와 다른 1개 선택)를 제공.
- 하지만 (a) 인증 만료 감지 없음, (b) 디스크 영속 캐시 없음, (c) 서브에이전트가 다중 외부 프로바이더에 병렬 fan-out하지 못함.
- 결과: gemini를 깔아도 cross-review에서 활용되지 않고, codex 인증이 만료되면 조용히 깨진 결과를 받게 됨.

### 목표
1. **동적 fan-out**: 가용한 외부 프로바이더 N개 모두에 같은 리뷰 프롬프트를 병렬 발송 → 항목별 합산 판정.
2. **3-state 감지**: `available` / `auth_expired` / `not_installed`. 인증 만료는 **블로킹**(시끄러운 실패).
3. **TTL 1h 디스크 캐시**: 매 호출마다 ping 비용 안 들도록 `~/.af/provider_cache.json`에 영속.
4. **`AF_SKIP_PROVIDER` 우회**: 인증 만료가 1회성이거나 일시적으로 무시하고 진행해야 할 때 escape hatch.

### 비목표 (out of scope)
- `core/cross_verification.py`(런타임 FSA 루프) 변경 — 이건 다른 레이어(Opus 판정 + self-evolution)이며 자체 fan-out을 이미 함.
- 새로운 프로바이더(Bard, Mistral 등) 추가 — 기존 `CLI_PROVIDER_IDS` 3종(claude/gemini/codex)만 다룸.
- Tier 1/Tier 2(af-test-runner, af-critic) 변경 — Claude 단독 동작 그대로.

---

## 1. 범위 정의

### 1.1 대상 영역
| 영역 | 변경 |
|------|------|
| `.claude/agents/af-cross-review.md` | Step 0(감지) 추가 + Step 2(동적 fan-out)로 재작성 |
| `core/provider_detect.py` (신규) | 3-state 감지 + 1h 디스크 캐시 + AF_SKIP_PROVIDER 처리 |
| `core/providers/registry.py` | 변경 없음 (재사용). 단, `detect_installed_cli_providers()`를 새 모듈에서 호출 |
| `af.spec` | `hiddenimports`에 `core.provider_detect` 추가 |
| `CLAUDE.md` | "교차검증 자동 실행" 룰 문구 변경 (Codex → 가용 외부 프로바이더 모두) |
| `tests/test_provider_detect.py` (신규) | 감지 / 캐시 / AF_SKIP_PROVIDER 단위 테스트 |

### 1.2 비대상
- `core/providers/registry.py` 기존 함수 시그니처 — 그대로 유지(역호환).
- Tier 1/Tier 2 에이전트 — 영향 없음.
- nightly autonomous pipeline — Tier 3을 어차피 호출하므로 자동으로 혜택 받음.

---

## 2. 설계 — 3-State 감지

### 2.1 상태 정의
```python
# core/provider_detect.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ProviderState(str, Enum):
    AVAILABLE     = "available"      # 설치 + ping OK
    AUTH_EXPIRED  = "auth_expired"   # 설치 OK + ping 실패 (인증 또는 토큰 문제 추정)
    NOT_INSTALLED = "not_installed"  # PATH에 CLI 없음 (또는 AF_SKIP_PROVIDER에 포함)

@dataclass(frozen=True)
class ProviderProbeResult:
    provider_id: str            # "claude_cli" | "gemini_cli" | "codex_cli"
    state: ProviderState
    checked_at: str             # ISO8601 UTC
    rtt_ms: int = 0             # ping 왕복 시간 (AVAILABLE일 때만)
    stderr_excerpt: str = ""    # AUTH_EXPIRED일 때 1KB까지
```

### 2.2 감지 알고리즘 (제공자 1개당)
```
1) AF_SKIP_PROVIDER에 provider_id가 포함되면 → NOT_INSTALLED 반환 (조용히 skip)
2) registry.detect_installed_cli_providers()로 설치 여부 확인
   → 미설치: NOT_INSTALLED
3) auth ping 실행 (subprocess, timeout=5s)
   → exit code 0: AVAILABLE
   → exit code != 0 또는 timeout: AUTH_EXPIRED (stderr 1KB 캡처)
4) ProviderProbeResult 반환
```

### 2.3 Auth Ping 명령 매트릭스

| Provider | 1차: 토큰 미사용 | 2차 (1차 미지원 시): 짧은 noop |
|----------|-----------------|------------------------------|
| `claude_cli` | `claude --version` (sanity) + 별도 인증 검사 — Claude Code는 명시적 `auth status`가 없으므로 **2차로 fallthrough** | `claude -p "ok" --output-format text` (timeout 5s) |
| `gemini_cli` | `gemini --version` 후 (지원 시) `gemini auth status` | `gemini -p "ok"` (timeout 5s) |
| `codex_cli` | `codex --version` 후 `codex login --check` (지원 시) | `codex exec -s read-only "ok"` (timeout 5s) |

> **결정**: 1차(토큰 미사용 status 명령)가 CLI별로 존재 여부가 다르므로, 구현은 **사용 가능한 status 명령이 발견되면 1차, 아니면 2차로 fallback**하는 단순 분기로 한다. 명령 존재 감지는 `--help` 출력 grep으로 하지 말고 **실제 호출 후 exit code 분기**(1차 자체가 ping 역할).
>
> **비용 가드**: 2차 fallback은 토큰을 1~10토큰 정도 소모. 캐시 TTL 1h이라 사용자당 하루 ~24회 → 무시 가능. 단, 캐시 미적중일 때만 호출.

### 2.4 일괄 감지 API
```python
def detect_provider_states(
    providers: list[str] | None = None,
    *,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> dict[str, ProviderProbeResult]:
    """3-state로 프로바이더 상태를 감지한다.

    - providers=None → CLI_PROVIDER_IDS 전체 (claude/gemini/codex)
    - use_cache=True + 캐시 신선(< TTL) → ping 없이 캐시 반환
    - force_refresh=True → 캐시 무시하고 새로 ping (저장은 함)
    - 결과는 항상 캐시에 원자적으로 저장
    """
```

병렬 처리: `concurrent.futures.ThreadPoolExecutor`(max_workers=3)로 3 프로바이더 동시 ping. 최악의 경우 5s timeout * 1 = 5s.

---

## 3. 설계 — 디스크 캐시

### 3.1 위치 & 포맷
- 경로: `~/.af/provider_cache.json` (`AF_HOME`이 설정되어 있으면 `$AF_HOME/provider_cache.json`)
- 디렉토리 자동 생성 (parents=True, exist_ok=True)
- 포맷:
```json
{
  "version": 1,
  "ts": "2026-04-29T05:00:00Z",
  "ttl_sec": 3600,
  "states": {
    "claude_cli": {"state": "available", "checked_at": "2026-04-29T05:00:00Z", "rtt_ms": 320, "stderr_excerpt": ""},
    "codex_cli": {"state": "auth_expired", "checked_at": "2026-04-29T05:00:00Z", "rtt_ms": 0, "stderr_excerpt": "Error: not authenticated. Run `codex login`."},
    "gemini_cli": {"state": "not_installed", "checked_at": "2026-04-29T05:00:00Z", "rtt_ms": 0, "stderr_excerpt": ""}
  }
}
```

### 3.2 원자적 쓰기
```
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(..., indent=2), encoding="utf-8")
os.replace(tmp, path)  # POSIX/Windows 모두 atomic
```
실패 시 (디스크 full, 권한 등) → 경고 로그만 출력, 메모리 캐시로 fallback.

### 3.3 만료 / 무효화
- 정상 만료: `now - ts > ttl_sec` → 새로 ping.
- **선택적 per-provider 무효화**: AUTH_EXPIRED 항목이 있고 사용자가 재로그인한 후, `provider_detect --invalidate <id>` 또는 `--invalidate all`로 강제 갱신 가능.
- TTL은 환경변수 `AF_PROVIDER_CACHE_TTL`로 override (테스트용).

### 3.4 메모리 캐시와의 관계
- `core/providers/registry.py`의 60초 메모리 캐시(`_installed_cli_cache`)는 **install 여부만** 캐시. 그대로 두고 사용.
- `core/provider_detect.py`의 1h 디스크 캐시는 **3-state(install + auth)**를 캐시. 두 캐시는 독립 — install 캐시가 비어 있어도 detect_provider_states는 정상 동작.

---

## 4. 설계 — `AF_SKIP_PROVIDER` 우회

### 4.1 시맨틱
- 환경변수 `AF_SKIP_PROVIDER`: 콤마 구분 provider_id 목록.
- 예: `AF_SKIP_PROVIDER=codex_cli` → codex가 설치돼 있어도 NOT_INSTALLED로 보고 → cross-review에서 빠짐.
- 1회 우회: 사용자가 `AF_SKIP_PROVIDER=codex_cli git commit ...`처럼 인라인으로 사용 (review-gate hook 패턴과 동일).

### 4.2 정규화
- 입력은 대소문자 무시: `codex`, `Codex`, `CODEX_CLI` → 모두 `codex_cli`로 정규화.
- 짧은 별칭 허용: `codex` → `codex_cli`, `claude` → `claude_cli`, `gemini` → `gemini_cli`.
- 알 수 없는 ID는 무시 + 경고 stderr.

### 4.3 캐시와의 상호작용
- AF_SKIP_PROVIDER 적용은 **캐시 조회 후**에 한다 — skip된 프로바이더는 캐시 히트와 무관하게 `NOT_INSTALLED`로 마스킹됨.
- 따라서 캐시 자체는 "실제 상태"를 담고, skip은 "사용자 선언"으로 결과만 조정. AF_SKIP_PROVIDER를 unset하면 즉시 원상 복귀.

---

## 5. 설계 — `af-cross-review.md` 동적 Fan-out

### 5.1 새 Step 0: 프로바이더 감지 + 게이트
```bash
# Step 0: 외부 프로바이더 감지
PROBE=$(python -m core.provider_detect --json --exclude-self claude_cli 2>&1)
# 결과 예: {"states": {"codex_cli": "available", "gemini_cli": "auth_expired"}, "fan_out": ["codex_cli"], "blocked": ["gemini_cli"]}

# 케이스 1: blocked 비어 있지 않음 → BLOCK 보고
if [ blocked가 비어있지 않음 ]; then
  echo "## 교차 검증 BLOCK"
  echo "다음 프로바이더의 인증이 만료되었습니다:"
  echo "  - gemini_cli: gemini auth login"
  echo ""
  echo "재로그인 후 다시 시도하거나, 1회 우회: AF_SKIP_PROVIDER=gemini_cli ..."
  exit 1
fi

# 케이스 2: fan_out 비어 있음 (claude만 있음) → SKIP
if [ fan_out가 비어있음 ]; then
  echo "## 교차 검증 SKIP — 외부 프로바이더 없음"
  echo "Claude 외 가용 CLI 없음 (codex/gemini 미설치 또는 SKIP). Tier 3은 통과로 간주."
  exit 0  # PASS-THROUGH
fi

# 케이스 3: fan_out 1개 이상 → Step 2로 진행
```

### 5.2 새 Step 2: 병렬 fan-out
- `fan_out` 리스트(예: `["codex_cli", "gemini_cli"]`)를 받아 각 프로바이더에 **같은 리뷰 프롬프트**를 병렬 발송.
- 명령 매트릭스:

| Provider | exec 명령 | 결과 캡처 |
|----------|----------|----------|
| codex_cli | `codex exec -s danger-full-access -o /tmp/cr-codex.txt "<prompt>"` | `/tmp/cr-codex.txt` |
| gemini_cli | `gemini --yolo -p "<prompt>" > /tmp/cr-gemini.txt 2>&1` | `/tmp/cr-gemini.txt` |
| (향후) | TBD | TBD |

> 병렬 처리: bash `&` + `wait`로 단순 백그라운드 시작, 각 프로세스에 individual timeout 180초.

### 5.3 새 Step 3: 항목별 합산 판정
- 각 프로바이더 결과를 별도 섹션으로 읽어서 **항목 추출**.
- **중복 dedup**: 동일 파일:라인 + 동일 심각도 + 키워드 유사 → 1개 항목으로 합치되 `반론자: codex_cli, gemini_cli`로 출처 표기.
- 판정은 기존과 동일하게 ACCEPT/REJECT/HOLD. **하지만 중복 발견 항목은 ACCEPT 우선순위 상향** — 2개 이상 모델이 같은 지적을 했다는 신호.
- 보고 포맷에 **참여 프로바이더 헤더** 추가:
```
## 교차 검증 결과 (참여: codex_cli, gemini_cli)

### 요약
- 총 피드백: N개 (codex: X, gemini: Y, 중복 dedup: Z)
- 수용(ACCEPT): A개 (그 중 합의: B개)
- 기각(REJECT): C개
- 보류(HOLD): D개
```

### 5.4 단일 프로바이더 fallback
- `fan_out`이 1개면(예: codex만) — 기존 동작과 동일. 합의 판정은 N/A.

---

## 6. CLAUDE.md 룰 변경

### 6.1 변경 전
> 교차검증 자동 실행 ... af-test-runner → af-critic → af-cross-review 에이전트를 순서대로 실행한다

af-cross-review.md 본문에는 "Codex에게 ... 리뷰 요청" 문구가 있어 사용자가 codex 단일이라고 오해할 수 있음.

### 6.2 변경 후
- CLAUDE.md "교차검증 자동 실행" 섹션에 한 줄 추가:
  > Tier 3(af-cross-review)는 가용 외부 CLI 프로바이더 전부에 병렬 fan-out한다. 외부 프로바이더가 0개면 자동 skip(통과 간주), 1개 이상 인증 만료가 있으면 BLOCK + 재인증 안내.
- af-cross-review.md 본문 첫 단락 "Codex에게" → "가용한 외부 CLI 프로바이더(codex/gemini 등)에"로 수정.

---

## 7. 변경 파일 매트릭스

| 파일 | 변경 종류 | 분량 추정 | 비고 |
|------|----------|----------|------|
| `core/provider_detect.py` (신규) | 신규 | ~250 lines | 3-state 감지 + 캐시 + AF_SKIP_PROVIDER + CLI entry |
| `core/providers/registry.py` | 변경 없음 | 0 | 재사용. (단, 새 모듈이 install detection을 import) |
| `af.spec` hiddenimports | 1줄 추가 | +1 | `'core.provider_detect',` |
| `.claude/agents/af-cross-review.md` | 재작성 | ~80 lines diff | Step 0 추가 + Step 2 fan-out + Step 3 합의 가중치 |
| `CLAUDE.md` | 1단락 수정 | ~3 lines | "교차검증 자동 실행" 한 줄 추가 |
| `tests/test_provider_detect.py` (신규) | 신규 | ~200 lines | 단위 테스트 (subprocess mock) |
| `Master_Blueprint.md` §3, §0, §12 | 수정 | ~20 lines | 새 모듈 등록 + 변경 이력 |

---

## 8. 구현 순서 (Sprint 분할)

### Sprint A — `core/provider_detect.py` 코어 (1커밋)
1. ProviderState enum, ProviderProbeResult dataclass.
2. Auth ping 매트릭스(claude/gemini/codex), 5s timeout, stderr 1KB 캡처.
3. 디스크 캐시 (read/write/원자성/TTL).
4. `detect_provider_states()` 일괄 API.
5. `python -m core.provider_detect --json` CLI 진입점.
6. `tests/test_provider_detect.py` — subprocess.run을 mock으로 교체하여 3-state 시나리오 + 캐시 hit/miss + AF_SKIP_PROVIDER 검증.
7. 3-Tier 검증 (af-test-runner → af-critic → af-cross-review). 이때 cross-review는 **아직 단일 codex** — 자기 자신을 변경하기 전이라 OK.

### Sprint B — `af-cross-review.md` 동적 fan-out (1커밋)
1. Step 0 추가 — `python -m core.provider_detect --json --exclude-self claude_cli` 호출, BLOCK/SKIP/CONTINUE 분기.
2. Step 2 재작성 — bash 백그라운드 + wait로 병렬 fan-out, 결과를 각 파일에 저장.
3. Step 3 — dedup + 합의 가중치.
4. CLAUDE.md 1단락 수정.
5. af.spec에 `core.provider_detect` 추가.
6. **이번 변경부터** Tier 3은 새 fan-out으로 동작.
7. Master_Blueprint §3·§0·§12 동기화.

### Sprint C — 운영 (필요 시)
- `af cache clear` 또는 `af provider invalidate <id>` CLI 명령(편의용, 선택). MVP에서는 캐시 파일 직접 삭제로 충분.

---

## 9. 테스트 계획

### 9.1 단위 테스트 (`tests/test_provider_detect.py`)
| ID | 시나리오 | 검증 |
|----|---------|------|
| T01 | 미설치(`shutil.which`=None) | `state == NOT_INSTALLED`, ping 호출 없음 |
| T02 | 설치 + ping exit 0 | `state == AVAILABLE`, rtt_ms > 0 |
| T03 | 설치 + ping exit 1 + stderr "not authenticated" | `state == AUTH_EXPIRED`, stderr_excerpt 포함 |
| T04 | 설치 + ping timeout | `state == AUTH_EXPIRED`, stderr_excerpt에 "timeout" |
| T05 | 캐시 신선 + use_cache=True | ping 호출 0회, 캐시 그대로 반환 |
| T06 | 캐시 만료 (ts > TTL) | ping 재호출, 캐시 갱신 |
| T07 | force_refresh=True | 캐시 신선해도 ping 호출 |
| T08 | AF_SKIP_PROVIDER=codex | codex_cli=NOT_INSTALLED 마스킹, claude/gemini는 정상 |
| T09 | AF_SKIP_PROVIDER 별칭 | `codex`, `CODEX`, `Codex_CLI` 모두 codex_cli로 정규화 |
| T10 | 캐시 파일 손상(JSON 깨짐) | 무시하고 새로 ping, 다시 저장 |
| T11 | 캐시 디렉토리 권한 없음 | 메모리 fallback, 경고 stderr |
| T12 | 동시 호출(2 스레드) | 마지막 쓴 값이 살아남고 깨지지 않음 (원자 rename) |

### 9.2 통합 테스트 (수동)
- 시나리오 1: claude만 설치 — `python -m core.provider_detect --json` → fan_out=[], blocked=[]. af-cross-review SKIP 확인.
- 시나리오 2: claude + codex 설치, codex 인증 OK — fan_out=["codex_cli"]. 단일 fan-out.
- 시나리오 3: claude + codex + gemini 설치, gemini 인증 만료 — blocked=["gemini_cli"]. BLOCK 메시지 확인.
- 시나리오 4: 시나리오 3에서 `AF_SKIP_PROVIDER=gemini_cli` — fan_out=["codex_cli"], blocked=[]. CONTINUE 확인.

### 9.3 회귀 테스트
- `tests/test_cli_providers.py` 기존 통과 그대로 유지.
- `core/cross_verification.py` 영향 없음 — 기존 통합 테스트 통과 확인.

---

## 10. 위험 & 완화

| ID | 위험 | 영향 | 완화 |
|----|------|------|------|
| R1 | Auth ping이 토큰을 소비 (2차 fallback) | 비용 ~수십 토큰/시간 | 1h TTL로 호출 빈도 제한. 1차 status 명령 우선. 향후 측정해서 TTL 조정 |
| R2 | gemini/codex CLI 인터페이스가 변경 | ping 명령 깨짐 | 매트릭스를 모듈 상단 dict로 분리. 변경 시 1곳만 수정 |
| R3 | 캐시 stale (실제 인증 만료됐는데 AVAILABLE로 캐시) | 1h간 잘못된 결과 | 사용자가 fan-out 호출 자체가 실패하면 즉시 재감지(force_refresh) — Step 2 명령 실패 hook |
| R4 | 병렬 fan-out 비용 (codex+gemini 동시 호출) | 2배 토큰 사용 | 1라운드만 호출(추가 라운드 없음). 사용자가 비용 민감하면 AF_SKIP_PROVIDER로 1개만 사용 가능 |
| R5 | bash 병렬 처리가 Windows에서 다르게 동작 | af-cross-review가 Windows에서 깨짐 | af-cross-review는 git bash 가정(이미 그러함). PowerShell에서는 `Start-Job`로 별도 분기는 비목표 |
| R6 | AUTH_EXPIRED 블로킹이 자율 nightly 파이프라인을 멈춤 | 야간 파이프라인 정지 | nightly에서는 `AF_SKIP_PROVIDER=auth_expired_*` 환경변수 자동 설정 옵션을 후속 작업으로 (이번 P1 범위 밖) |
| R7 | Claude Code 자체에는 "auth status" 명령이 없음 | claude_cli ping이 항상 2차(토큰 사용)로 가야 함 | `--exclude-self claude_cli`가 기본 — Tier 3에서는 claude_cli를 ping할 필요 자체가 없음. 비-claude 진입점에서만 ping |

---

## 11. 롤백 전략

- Sprint A 롤백: `core/provider_detect.py` 단독 모듈이라 삭제만 해도 끝. af.spec 한 줄 되돌리기. 다른 코드는 의존 안 함.
- Sprint B 롤백: `.claude/agents/af-cross-review.md`를 직전 커밋으로 되돌리기. CLAUDE.md 한 단락 되돌리기.
- 캐시 파일(`~/.af/provider_cache.json`)은 버전 미일치 시 무시되도록 `version` 필드를 둠 — 향후 v2 도입 시 v1 캐시는 자동 폐기.

---

## 12. 미결 결정 (Open Questions)

1. **Q1**: Auth ping에서 1차(토큰 미사용 status)와 2차(짧은 noop)를 모두 시도할지, 아니면 "1차가 없으면 바로 2차"로 단순화할지?
   - **잠정 결정**: 단순화. 매트릭스에 1차/2차 중 하나만 명시(2차가 없는 CLI는 1차만, 2차가 보장된 CLI는 그것만). 구현 시 결정.
2. **Q2**: `AF_SKIP_PROVIDER` 환경변수가 commit hook(review-gate)에서도 동작해야 할지?
   - **잠정 결정**: 미적용. review-gate는 Tier 3 verdict만 보고 차단 여부를 결정. fan-out 내부의 skip은 verdict에 영향 없음. 별도 작업 불필요.
3. **Q3**: 합의 가중치(2+ 모델이 같은 지적) 항목을 자동 ACCEPT 처리할지, 표시만 할지?
   - **잠정 결정**: 표시만. 자동 적용은 P1 범위 밖. ACCEPT 우선순위만 시각적으로 강조.
4. **Q4**: gemini가 `--yolo` 없이 인터랙티브 프롬프트를 띄우는 경우 hang?
   - **잠정 결정**: gemini 호출 시 `--yolo` 또는 동등 플래그 항상 추가. timeout 180s로 hang 방지. 구현 시 확인.

---

## 13. 변경 이력

- v1 (2026-04-29): 초안 작성. Sprint A/B 분할, 12 시나리오 단위 테스트, 7 위험 항목.
