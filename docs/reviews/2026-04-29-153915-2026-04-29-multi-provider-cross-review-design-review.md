# Design Review: 2026-04-29-multi-provider-cross-review

> Source: docs/2026-04-29-multi-provider-cross-review.md
> Date: 2026-04-29 15:39
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 3 providers)
> Trigger: claude

---

## Final Design Review

### Verdict: BLOCK

Critic가 Critical 2건을 제기했고, 그 중 1건(`codex login status` 오탐)은 프로젝트 메모리에 *재현 사례가 이미 기록*되어 있는 실측 결함입니다. Cross도 같은 영역(인증 분류·프로세스 동시성·BLOCK 메시지·캐시 schema)에서 7건 ACCEPT로 합세했습니다. Sprint A에 들어가기 전에 ping 분류 로직과 진입점(frozen/shell), `Verdict:` 출력 규약을 먼저 잠그지 않으면 nightly pipeline 전체가 false-BLOCK로 멈출 위험이 큽니다.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [Critical] Ping 실패를 무조건 AUTH_EXPIRED로 단정해 false-BLOCK 발생
- **Critic** (#1): `codex login status`가 `auth.json` 살아 있어도 "Not logged in"을 반환하는 사례가 프로젝트 메모리(`...login_status_still_reports_not_logged_in...`)에 기록됨. 그대로 BLOCK 게이트로 쓰면 정상 인증 환경에서도 Tier 3 차단.
- **Cross** (#2): exit≠0은 permission denied / hook failure / rate limit / bad flag 등 다수 원인이 있는데 전부 auth로 분류하면 잘못된 처방을 안내.
- **Judgment**: 두 리뷰가 같은 결함(분류 정밀도 부족)을 다른 각도에서 검증. `core/providers/cli.py:110-134, 377-383`에 이미 `permission_denied / auth_required / hook_failure` 분류기가 있는데 새 모듈이 이를 무시함.
- **Action Required**: §2.1에 `reason` 필드(`auth_expired / probe_failed / permission_denied / timeout`) 추가. §2.3은 ① 1차 status가 비-제로면 즉시 단정 금지 → 2차 noop ping으로 검증, ② stderr를 `_AUTH_REQUIRED_MARKERS`로 매칭해서 진짜 auth 실패만 AUTH_EXPIRED. 프로젝트 메모리 케이스를 §9 회귀 테스트에 케이스로 추가.

#### 2. [ACCEPT] [Critical] Shell 진입점 `python -m core.provider_detect`가 frozen/hook 환경에서 깨짐
- **Critic** (#2 + Missing "Frozen 빌드"): `af-cross-review.md` Step 0이 `python -m core.provider_detect`를 호출하는데, frozen `dist/af-{version}.zip`에는 `core/` 소스가 없으므로 import error. review-gate hook 환경에서도 PATH/venv mismatch.
- **Cross** (#8): 단, `af.spec` hiddenimports만으로 패키징은 충분 — PyInstaller가 `core.providers` 의존을 자동 추적함.
- **Judgment**: 두 리뷰는 모순이 아니라 다른 레이어. Cross #8(패키징)은 맞지만 Critic이 지적하는 건 *진입점 호출 방식*. frozen `af.exe`는 `python -m`을 못 받음.
- **Action Required**: 둘 중 하나 — (a) `run_factory_cli.py`에 `af provider-detect --json` subcommand 추가하고 af-cross-review.md는 `af` → fallback `python -m`, 또는 (b) §0 비목표에 *"dev 환경(소스 + 시스템 python) 전용, frozen af.exe 사용자 미노출"*을 명시. (a)가 nightly pipeline 정합성에 안전.

#### 3. [ACCEPT] [High] Probe CLI JSON / exit-code 계약 미정의
- **Critic**: 부분적으로만 언급(§2.4 비대칭).
- **Cross** (#4): Python API는 `dict[str, ProviderProbeResult]`인데 Step 0은 `states / fan_out / blocked` 키를 가정. `--exclude-self`, `--invalidate`, warnings, exit code 미정의.
- **Judgment**: Cross의 증거가 강함 — 설계서가 examples만 있고 schema가 없음.
- **Action Required**: §2.4 또는 신규 §2.5에 정규 JSON schema 박기 — `{version, checked_at, states, fan_out, blocked, skipped, warnings}`. probe 자체가 크래시할 때만 exit≠0, 분류 결과는 항상 exit 0 + JSON.

#### 4. [ACCEPT] [High] BLOCK/SKIP 출력이 Review-Gate에서 `pass`로 오인됨
- **Critic**: 미언급.
- **Cross** (#5): `scripts/hook_runner.py:325-331` + `scripts/review_gate.py:25-32`는 `Verdict: BLOCK` 또는 `## BLOCK` 헤더만 인식. 설계서의 `## 교차 검증 BLOCK`는 매칭 실패.
- **Judgment**: 코드 레퍼런스로 검증된 결정타. 그대로 두면 BLOCK이 silently PASS.
- **Action Required**: §5.1 BLOCK/SKIP 출력 마지막 줄에 정확히 `Verdict: BLOCK` / `Verdict: PASS` 추가. §9에 hook 매칭 케이스 테스트 2건(auth-block, skip).

#### 5. [ACCEPT] [High] Per-job timeout이 fan-out에서 실제로 강제되지 않음
- **Critic** (#4): §5.2 예시 `codex exec ... &`에 `timeout 180`이 없음. bash `wait`는 시간 제한 없음.
- **Cross**: 미언급.
- **Judgment**: Critic 단독이지만 코드 예시를 직접 인용한 강한 증거. R5(Windows bash) + Q4(`gemini --yolo` hang) mitigation과 정면 충돌.
- **Action Required**: §5.2를 `timeout 180 codex exec ... > /tmp/cr-codex.txt 2>&1 &` 형태로 정정하거나, fan-out도 §2.4처럼 Python `ThreadPoolExecutor`로 통일.

#### 6. [ACCEPT] [High] `AF_SKIP_PROVIDER`가 NOT_INSTALLED로 마스킹되어 관찰성 손실
- **Critic** (#5): SKIPPED와 미설치를 합치면 디버깅 불가. 캐시에 SKIPPED 정보 누락.
- **Cross** (#7): 같은 결함. 보고서 헤더에서도 skipped 가시화 필요.
- **Judgment**: 두 리뷰 합의. §4.3은 의도가 옳으나 §2.1 enum과 §3.1 schema가 이를 강제 못 함.
- **Action Required**: ① `ProviderState.SKIPPED` 추가, ② 캐시는 *실상태(SKIPPED 미적용)*만 저장하고 응답 직전 마스킹, ③ §5.3 보고 헤더에 `skipped: [...]` 노출, ④ fan-out 게이트는 `state in (NOT_INSTALLED, SKIPPED)` 모두 제외.

#### 7. [ACCEPT] [High] §2.3 매트릭스가 `_CLI_SPECS.auth_status_command`와 중복
- **Critic** (#3): `core/providers/cli.py:78,105`에 spec dataclass로 이미 박혀 있음. 새 모듈이 별도 dict면 드리프트.
- **Cross**: 미언급.
- **Judgment**: Critic 단독이지만 코드 위치 인용 강함. R2(매트릭스 변경) 위험을 자동 완화하는 명확한 단일화 기회.
- **Action Required**: §2.3을 `_CLI_SPECS[provider_id].auth_status_command` 재사용으로 명시. 빈 tuple일 때만 2차 noop fallback 호출.

#### 8. [ACCEPT] [Medium] 캐시 read-modify-write에 process-level lock 없음
- **Critic** (#6): `core/file_lock.py` 이미 존재. T12는 thread만 검증.
- **Cross** (#6): 추가로 `tmp = path.with_suffix(".json.tmp")` 공유 경로 race. `tempfile.mkstemp` + `os.replace` + `locked_file` 권장.
- **Judgment**: 합의. 두 결함을 한 항목으로 통합.
- **Action Required**: ① 캐시 read/write 구간을 `core.file_lock.locked_file(cache_path)`로 감싸기, ② tmp 파일은 `tempfile.mkstemp(dir=cache_dir)`, ③ T12에 `subprocess.Popen` 2개 fixture 추가.

#### 9. [ACCEPT] [Medium] 재로그인 후 1h 캐시로 인해 BLOCK이 풀리지 않음 + `--invalidate` 안내 누락
- **Critic** (#9): BLOCK 메시지가 캐시 무효화 명령을 안내하지 않음.
- **Cross** (#3): `--invalidate`를 Sprint C(선택)로 미루지 말고 Sprint A 필수로. 또는 `auth_expired`만 짧은 TTL.
- **Judgment**: 합의. UX와 캐시 schema 양쪽에 영향.
- **Action Required**: ① `--invalidate <id> | all`을 Sprint A 범위로 끌어오기, ② §5.1 BLOCK 메시지에 *"`python -m core.provider_detect --invalidate gemini_cli` (또는 `af provider-detect --invalidate ...`)"* 한 줄 추가, ③ 또는 `auth_expired` TTL을 60초로 단축.

#### 10. [ACCEPT] [Medium] `force_refresh`가 registry 60s install 캐시를 우회하지 못함
- **Critic**: 미언급.
- **Cross** (#1): `core/providers/registry.py:203-242`의 `_installed_cli_cache`는 별개. `invalidate_installed_cli_cache()` 미호출 시 새로 깐 CLI가 60초 동안 not_installed.
- **Judgment**: Cross 단독이나 코드 라인 인용 강함. §3.4가 "두 캐시는 독립"이라 적었는데 force_refresh 시맨틱이 깨짐.
- **Action Required**: `detect_provider_states(force_refresh=True)`가 진입 시 `invalidate_installed_cli_cache()` 호출.

#### 11. [ACCEPT] [Medium] §5.3 dedup "키워드 유사" 미정의 + stderr 토큰 leak + /tmp 정리 누락
- **Critic** (#8 + #10 + Missing "/tmp 정리"): 세 결함을 한 항목으로 묶음 — 모두 §5 fan-out 위생 이슈.
- **Cross**: 미언급.
- **Judgment**: 단일 출처지만 모두 구체적이고 작은 수정으로 해소 가능.
- **Action Required**: ① §5.3 dedup을 *"동일 파일:라인이면 합치고 심각도는 max"*로 단순화(키워드 유사 P1 밖), ② §2.1 stderr 캡처에 `[A-Za-z0-9_\-]{20,}` 토큰 패턴 redaction + auth marker 라인만 보존, ③ §5.2 마지막에 `rm -f /tmp/cr-*.txt` trap.

#### 12. [HOLD] [Low] `pick_review_provider()` 호출자 영향 + Sprint A 부트스트랩 데드락 + PASS-THROUGH 정책
- **Critic** (#7, #11, Missing "PASS-THROUGH"): (a) `pick_review_provider()` dead code 여부 미확인, (b) codex 만료 상태에서 Sprint A 자체가 BLOCK, (c) "외부 0개 → PASS"가 CLAUDE.md "Tier 3 의무"와 정책 충돌.
- **Cross**: 미언급.
- **Judgment**: 셋 다 단독 출처 + 정책/조사 질문이라 구현 전 답이 필요.
- **Question for Author**:
  1. `Grep "pick_review_provider"` 호출자 0개인가? 있다면 fan-out으로 같이 옮길지?
  2. Sprint A를 `AF_SKIP_REVIEW_GATE=1`로 부트스트랩할지, 아니면 codex 인증 사전 확인을 절차화할지?
  3. "외부 0개 PASS"가 진짜 commit 허용인지, 아니면 "경고 후 통과"인지? CLAUDE.md 룰과의 정합 어떻게 표현?

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Ping 실패 → AUTH_EXPIRED 단정 (codex login status 오탐) | Critical | ACCEPT | Both |
| 2 | `python -m core.X` frozen/hook 진입점 | Critical | ACCEPT | Critic |
| 3 | Probe CLI JSON / exit-code 계약 미정의 | High | ACCEPT | Cross |
| 4 | BLOCK/SKIP `Verdict:` 헤더 미준수 → hook이 PASS로 오인 | High | ACCEPT | Cross |
| 5 | Fan-out per-job timeout 미적용 | High | ACCEPT | Critic |
| 6 | AF_SKIP_PROVIDER → NOT_INSTALLED 마스킹 | High | ACCEPT | Both |
| 7 | §2.3 매트릭스가 `_CLI_SPECS`와 중복 | High | ACCEPT | Critic |
| 8 | 캐시 process-level lock + tmp 경로 race | Medium | ACCEPT | Both |
| 9 | 1h 캐시로 BLOCK 잔존 + `--invalidate` 안내 누락 | Medium | ACCEPT | Both |
| 10 | `force_refresh`가 registry install 캐시 미무효화 | Medium | ACCEPT | Cross |
| 11 | §5.3 dedup 미정의 + stderr 토큰 leak + /tmp 정리 | Medium | ACCEPT | Critic |
| 12 | `pick_review_provider` 영향 + 부트스트랩 + PASS 정책 | Low | HOLD | Critic |

---

### Recommendations

구현 전 설계서에 다음을 박을 것:

1. **§2.1/§2.3**: `reason` 필드 추가 + `_CLI_SPECS.auth_status_command` 재사용 + 1차 실패 시 2차 noop 검증 + `_AUTH_REQUIRED_MARKERS` 매칭 (Findings 1, 7)
2. **§2.4/§2.5**: 정규 JSON schema(`states/fan_out/blocked/skipped/warnings/checked_at`) + exit code 규약 (Finding 3)
3. **§1.1**: `af provider-detect` subcommand 신설 → af-cross-review.md는 `af` → fallback `python -m` (Finding 2)
4. **§5.1**: BLOCK/SKIP 출력 마지막 줄 `Verdict: BLOCK|PASS` + `--invalidate` 명령 안내 (Findings 4, 9)
5. **§5.2**: `timeout 180` 강제 또는 ThreadPoolExecutor로 전환 + `/tmp/cr-*` cleanup trap (Findings 5, 11)
6. **§2.1/§3.1/§4.3**: `ProviderState.SKIPPED` enum + 캐시는 실상태만 저장 + 보고서 헤더 노출 (Finding 6)
7. **§3.2/§9**: `core.file_lock.locked_file` + `tempfile.mkstemp` + multi-process T12 케이스 (Finding 8)
8. **§2.4 구현**: `force_refresh=True` 진입 시 `invalidate_installed_cli_cache()` 호출 (Finding 10)
9. **§5.3**: dedup 정의 단순화 ("동일 file:line 합치고 severity는 max"), 키워드 유사 P1 밖으로 명시 (Finding 11)
10. **§8 Sprint A**: `--invalidate` CLI를 Sprint A로 끌어옴 (Finding 9) + 부트스트랩 우회 절차 명시 (Finding 12-b)
11. **§0 비목표 또는 §5.1**: "외부 프로바이더 0개" PASS의 정책적 의미를 CLAUDE.md 룰과 정렬 (Finding 12-c)
12. **§1.1 메모**: `Grep "pick_review_provider"` 호출자 조사 결과 기재 (Finding 12-a)