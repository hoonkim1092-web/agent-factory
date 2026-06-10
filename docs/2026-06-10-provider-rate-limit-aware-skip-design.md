# Provider Rate-Limit 인지 → cross-review 스킵 + 노티 설계

- 작성일: 2026-06-10 (KST)
- 작성 모델: Opus
- 상태: Draft (교차검증 대기 — codex limit 해소 후 또는 single-vendor)
- 작성 계기: cross-review provider(codex)가 usage limit일 때 반복 헛호출로 Claude 토큰만 소모 + 사용자 미인지
- 관련 코드: `core/provider_detect.py`, `core/review_runner.py`, `core/providers/cli.py`, `.claude/agents/af-cross-review.md`
- 관련 메모리: `feedback_design_review_mandatory`, `feedback_analysis_doc_baseline_must_be_real_code`, `project_model_routing_facts`

---

## 1. 문제

cross-review 외부 provider(codex)가 **usage limit**에 걸린 상태에서:

- `provider_detect`는 codex를 **login status로만** 감지한다 → 로그인 유효 → `AVAILABLE`로 보고 (`provider_detect.py:440` `fan_out`에 포함). **usage limit은 사전 감지 불가.**
- cross-review가 codex를 호출 → limit 응답을 받음 → single-vendor로 떨어짐. 그러나:
  1. **반복 호출**: 다음 cross-review에서도 codex가 `AVAILABLE`이라 또 호출 → 또 limit. 캐시에 limit이 기록되지 않음.
  2. **헛고생 비용**: codex 응답 생성은 0(거부)이지만, **cross-review 에이전트(Sonnet)가 매회 코드 탐색+판정에 ~65k 토큰 소모**(직전 라운드 실측 `subagent_tokens: 65305`).
  3. **노티 부재**: 사용자가 "limit이라 외부검증 못 했다"를 명시적으로 안내받지 못함(single-vendor PASS로 뭉뚱그려짐).

`execute_cli_chat`은 limit 응답을 `f"{provider_id}_failed"`로 뭉뚱그린다(`core/providers/cli.py:832`, `:909-912`) — limit 전용 분류가 없다.

## 2. 핵심 제약 (설계 전제)

**usage limit은 본질적으로 사후 감지다.** login status ping(현행)으로는 알 수 없고, 실제 메시지를 보내야 "limit" 응답이 온다. 따라서 가능한 구조는 하나:

> **1회 호출로 limit을 만남 → 캐시에 학습(rate_limited_until) → 이후 만료 전까지 fan_out에서 제외 + 노티.**

"무호출 사전 차단"은 불가능. "처음 1회 부딪힌 뒤 반복 차단"이 최선이며, 이를 받아들인다.

## 3. 설계 방향 — provider_detect를 SSOT로 (사용자 선택: A)

limit 상태를 `provider_detect` 캐시에 1급으로 기록하면 **두 호출 경로가 동시에 해결**된다:

- **에이전트 경로** (`.claude/agents/af-cross-review.md` Step 0의 `provider_detect --json`)
- **코드 경로** (`core/review_runner.py` → `execute_cli_chat`)

두 경로 모두 `provider_detect`의 판정을 신뢰하므로, limit을 provider_detect 레벨에서 처리하면 SSOT가 된다.

## 4. Baseline (실제 코드, 라인 좌표)

| 위치 | 현재 동작 |
|------|----------|
| `provider_detect.py:80-83` | `ProviderState` — AVAILABLE / AUTH_EXPIRED / NOT_INSTALLED 3종 |
| `provider_detect.py:86-92` | `ProviderProbeResult` (frozen) — provider_id/state/checked_at/rtt_ms/stderr_excerpt |
| `provider_detect.py:131-160` | 캐시 write/`_cache_fresh`(TTL 1h, `_DEFAULT_TTL_SEC=3600` :25) |
| `provider_detect.py:165-172` | `_result_from_dict` — 캐시 역직렬화 |
| `provider_detect.py:277-360` | `detect_provider_states` — 캐시 신선하면 ping 생략, 아니면 probe |
| `provider_detect.py:440` | `fan_out = [... if state == AVAILABLE]` |
| `provider_detect.py:441` | `blocked = [... if state == AUTH_EXPIRED]` |
| `provider_detect.py:444-449` | JSON 출력 — `states/fan_out/blocked` |
| `provider_detect.py:402-418` | CLI 인자 — `--json/--exclude-self/--invalidate/--force-refresh` |
| `review_runner.py:113-117` | `execute_cli_chat` 결과 — `ok=False`면 `(provider error: {reason})` 반환, limit 미구분 |
| `providers/cli.py:832,909-912` | limit 응답 → `{provider_id}_failed`로 뭉뚱그림 (limit 전용 reason 없음) |
| `af-cross-review.md:79-118` | Step 0 — `blocked` 있으면 BLOCK(인증만료), `fan_out` 비면 SKIP(single-vendor) |

핵심: limit을 표현할 상태(`RATE_LIMITED`)도, 기록할 필드(`rate_limited_until`)도, 감지할 reason도 **현재 없다.**

## 5. 변경 (S1: provider_detect SSOT)

### C1. `ProviderState`에 `RATE_LIMITED` 추가 (`:80-83`)

```
class ProviderState(str, Enum):
    AVAILABLE     = "available"
    AUTH_EXPIRED  = "auth_expired"
    RATE_LIMITED  = "rate_limited"   # 신규: usage limit (시간 경과 시 자동 복구)
    NOT_INSTALLED = "not_installed"
```

`AUTH_EXPIRED`(재로그인 필요 → BLOCK)와 구분: `RATE_LIMITED`는 **시간이 지나면 자동 복구** → SKIP(노티).

### C2. `ProviderProbeResult` + 캐시에 `rate_limited_until` 필드 (`:86-92`, `:165-172`)

```
@dataclass(frozen=True)
class ProviderProbeResult:
    provider_id: str
    state: ProviderState
    checked_at: str
    rtt_ms: int = 0
    stderr_excerpt: str = ""
    rate_limited_until: str = ""   # 신규: ISO8601 UTC, "" = 제한 없음
```

`_result_from_dict`(:165-172)에 `rate_limited_until=s.get("rate_limited_until", "")` 추가, 캐시 write 직렬화에도 포함. **하위호환**: 기존 캐시 항목엔 필드 없음 → `s.get(..., "")` → 빈 문자열 → "제한 없음"으로 해석 → 기존 동작.

### C3. 신규 헬퍼 `mark_rate_limited(provider_id, until_iso)`

```
def mark_rate_limited(provider_id: str, until_iso: str) -> None:
    """limit 응답을 만난 호출처가 호출. 캐시에 rate_limited_until 기록."""
    # _cache_lock 하에 기존 캐시 read → 해당 provider 항목의 rate_limited_until 갱신 → write
```

`_cache_lock`(:99) 하에 atomic. 기존 `invalidate_cache`(:374)와 동일 패턴.

### C4. `detect_provider_states`에서 limit override (`:277-360`)

probe/캐시 결과를 반환하기 전, 각 provider의 `rate_limited_until`을 검사:

```
if r.rate_limited_until:
    until = parse_iso(r.rate_limited_until)
    if until and until > now_utc():
        r = replace(r, state=ProviderState.RATE_LIMITED)   # AVAILABLE이어도 override
    # 만료됐으면 그대로 둠 → 다음 probe에서 AVAILABLE 자연 복구
```

→ `fan_out`(:440 `state == AVAILABLE`)에서 **자동 제외**(별도 수정 불필요).

### C5. CLI: `--mark-rate-limited` + JSON에 `rate_limited` (`:402-454`)

```
# 인자 추가
parser.add_argument("--mark-rate-limited", metavar="PROVIDER")
parser.add_argument("--until", default="", help="ISO8601 또는 빈값(고정 TTL)")

# 처리 (invalidate 분기 옆)
if args.mark_rate_limited:
    until = args.until or (now + _RATE_LIMIT_FALLBACK_TTL)  # 파싱 실패/미지정 fallback
    mark_rate_limited(_normalize(args.mark_rate_limited), until)
    return

# JSON 출력 (:441 옆)
rate_limited = [pid for pid in target_ids if states[pid].state == ProviderState.RATE_LIMITED]
out = {"states": ..., "fan_out": fan_out, "blocked": blocked, "rate_limited": rate_limited}
```

## 6. 변경 (S2: limit 감지 → mark, 코드 경로)

### C6. 공통 감지 헬퍼 `detect_rate_limit_signal(text) -> str | None`

limit 시그널을 SSOT로 판정(두 경로 공유). provider-agnostic:

```
_RATE_LIMIT_PATTERNS = ("usage limit", "hit your usage", "rate limit",
                        "too many requests", "429", "resource exhausted")

def detect_rate_limit_signal(text: str) -> str | None:
    """limit 텍스트면 reset ISO8601 반환(파싱 실패 시 now+fallback TTL), 아니면 None."""
```

- reset 시각 파싱은 **best-effort** (예: "Try again at Jun 11th, 2026 10:31 AM"). 파싱 실패해도 안전 — `now + _RATE_LIMIT_FALLBACK_TTL`로 fallback.
- `_RATE_LIMIT_FALLBACK_TTL` 초기값 제안: **1시간** (보수적 — 실제로 풀렸는데 과도하게 오래 막지 않도록. reset 파싱 성공 시 그 값 우선).

### C7. `review_runner._run_provider` 배선 (`:113-117`)

```
result = execute_cli_chat(request)
if not result.get("ok"):
    reason = result.get("reason") or "unknown_error"
    until = detect_rate_limit_signal(f"{reason} {result.get('text','')}")
    if until:
        from core.provider_detect import mark_rate_limited
        mark_rate_limited(provider_id, until)
    return f"(provider error: {reason})"
```

## 7. 변경 (S3: 에이전트 경로 노티)

### C8. `af-cross-review.md` Step 0 — `rate_limited` 케이스 추가

probe JSON에 `rate_limited`가 추가됨. Step 0(`:72-118`)에 분기 추가:

- **`fan_out` 비어있고 `rate_limited` 있음**: SKIP + **명확한 노티**
  ```
  ## 교차 검증 SKIP — 외부 프로바이더 usage limit
  codex_cli: usage limit (재시도 가능: <until>). 반복 호출을 피하기 위해 cross-review를 건너뜁니다.
  <!-- final-verdict-start -->
  ## Tier 3 판정: PASS [rate-limited]
  사유: 외부 프로바이더 usage limit — SKIP (재시도: <until>)
  <!-- final-verdict-end -->
  ```
- **`fan_out`에 다른 provider 있음**: 그 provider로 진행 + limit provider는 노티만.

### C9. 에이전트가 MCP codex 응답에서 limit 만나면 mark (Step 2b 보강)

`mcp__codex__codex` 응답에 limit 시그널이 있으면, Bash로 캐시에 기록:
```bash
python -m core.provider_detect --mark-rate-limited codex_cli --until "<parsed-or-empty>"
```
→ 다음 cross-review의 Step 0이 자동으로 SKIP(C8). 반복 헛호출 차단.

## 8. 하위호환 / 안전

- **자동 복구**: `rate_limited_until` 만료 → 다음 probe에서 override 안 함 → AVAILABLE 자연 복구. 영구 차단 없음.
- **기존 캐시 호환**: 필드 없는 항목 → `""` → 제한 없음(C2).
- **AUTH_EXPIRED와 분리**: limit은 BLOCK이 아니라 SKIP(PASS [rate-limited]) — CLAUDE.md "외부 0개 SKIP 통과 간주"와 일관. 단 노티로 사용자 인지.
- **동시성**: `mark_rate_limited`는 `_cache_lock` 하 atomic.
- **`--force-refresh`**: limit override는 캐시의 `rate_limited_until` 기반이므로 force-refresh(재ping)와 독립 — ping이 AVAILABLE을 줘도 until이 미래면 RATE_LIMITED 유지(C4). limit은 ping으로 못 푸는 게 맞다(시간 경과만이 해소).

## 9. 비목표

- **사전 무호출 감지** — 기술적으로 불가능(§2). 1회 호출 후 학습만.
- **자동 재시도/대기** — limit 동안 sleep 후 retry 같은 능동 대기는 안 함(토큰·시간 낭비). SKIP + 노티만.
- **gemini/기타 provider 전용 처리** — 감지 패턴은 provider-agnostic(C6). 단 reset 파싱은 codex 형식 우선, 나머지는 fallback TTL.

## 10. 기각한 대안

- **에이전트 경로만 수정 (B)**: 코드 경로(doc cross-review)에 limit 누수 잔존. 사용자가 A(SSOT) 선택 → 기각.
- **고정 TTL만 (reset 파싱 없음)**: 단순하나 풀린 뒤에도 계속 스킵하거나 너무 일찍 재시도. reset 파싱 우선 + fallback이 균형(C6).
- **limit을 AUTH_EXPIRED로 재사용**: 의미 충돌 — AUTH_EXPIRED는 재로그인 BLOCK, limit은 시간 SKIP. 별도 상태 필요(C1).

## 11. 테스트 불변식 (RED-first)

| ID | 불변식 |
|----|--------|
| INV-1 | `mark_rate_limited(p, 미래)` 후 `detect_provider_states` → p가 RATE_LIMITED, `fan_out` 제외 |
| INV-2 | `rate_limited_until` 과거 → RATE_LIMITED override 안 함, AVAILABLE 복구 (자동 만료) |
| INV-3 | CLI `--json` 출력에 `rate_limited` 목록 포함 |
| INV-4 | `detect_rate_limit_signal("...usage limit...Try again at <X>")` → X 파싱(또는 fallback) 반환 |
| INV-5 | `detect_rate_limit_signal(정상 텍스트)` → None |
| INV-6 | reset 파싱 실패 → `now + _RATE_LIMIT_FALLBACK_TTL` fallback (None 아님) |
| INV-7 | 캐시에 `rate_limited_until` 없는 기존 항목 → 하위호환(AVAILABLE), 예외 없음 |
| INV-8 | `_run_provider`가 limit reason 응답 시 `mark_rate_limited` 호출 (배선; mock으로 검증) |
| INV-9 | `force_refresh=True`여도 until이 미래면 RATE_LIMITED 유지 (limit은 ping으로 안 풀림) |

## 12. 슬라이싱

| 슬라이스 | 내용 | 비고 |
|---------|------|------|
| **S1** | C1~C5 — provider_detect SSOT (enum/필드/mark/override/CLI) | 코어, 단독 머지 가능 |
| **S2** | C6~C7 — 감지 헬퍼 + review_runner 배선 (코드 경로) | S1 의존 |
| **S3** | C8~C9 — af-cross-review.md 노티 + MCP mark (에이전트 경로) | S1 의존, 마크다운 위주 |

S1+S2는 core/ 코드(test-first + 3-Tier). S3는 에이전트 정의(.md) — 코드 게이트 대상 아니나 동작 검증 필요.

## 13. 영향 범위

- 수정 파일: `core/provider_detect.py`(enum/dataclass/캐시/detect/CLI/mark 헬퍼), `core/review_runner.py`(_run_provider 배선), `.claude/agents/af-cross-review.md`(Step 0 노티 + Step 2b mark)
- 신규 타입 없음 (기존 enum/dataclass 확장)
- `af.spec` 영향 없음 (신규 모듈 없음)
- Blueprint §6(모델 라우팅)/§7(안전장치) 또는 §11(알려진 제약) 갱신 — provider 상태에 RATE_LIMITED 추가
