# Design Review: 2026-04-29-multi-provider-cross-review

> Source: docs/2026-04-29-multi-provider-cross-review.md
> Date: 2026-04-29 15:06
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 3 providers)
> Trigger: claude

---

## Final Design Review

### Verdict: WARN

High 5건, Medium 7건. Critical 없음. 단, High #3(AF_SKIP_PROVIDER 모순)와 High #4(어댑터 중복)는 구현 시작 전 반드시 해결해야 한다.

---

### Aggregated Findings (13 total)

#### 1. [ACCEPT] [High] AUTH_EXPIRED 과도한 오분류
- **Critic**: "rate limit, 네트워크 단절, 디스크 부족 등 모든 non-zero exit이 AUTH_EXPIRED로 분류됨. nightly CI에서 무한 재인증 요구 루프 위험."
- **Cross**: "기존 `core/providers/cli.py:112-136`이 이미 `permission_denied`, `auth_required`, `hook_failure`를 구분함. `_run_cli_auth_preflight()`도 timeout 별도 처리."
- **Judgment**: 양쪽이 동일 섹션을 독립적으로 지적. `cli.py` 내 기존 분류 로직이 증거.
- **Action Required**: `ProviderProbeResult`에 `category` 필드 추가. AUTH_EXPIRED는 stderr에 인증 관련 마커(`not authenticated`, `401`, `403`, `login required`)가 있을 때만 사용. 나머지 non-zero는 `PROBE_FAILED`로 분류하고 BLOCK 대신 WARN 처리.

#### 2. [ACCEPT] [High] CLI JSON 계약 미명세 + bash 파싱 방법 누락
- **Critic**: "`python -m core.provider_detect --json` 출력을 bash가 파싱하는 방법이 완전 생략. `jq`, 2차 Python 호출, `--export-env` 중 어느 것도 명시 안 됨."
- **Cross**: "Step 0가 `PROBE=$(... 2>&1)`로 stderr를 섞어 캡처해 JSON 파싱 불안정. stdout-only JSON + stderr 분리 + 출력 스키마(`version`, `ok`, `states`, `fan_out`, `blocked`, `skipped`) 필요."
- **Judgment**: 중복 발견. 두 리뷰어가 같은 Step 0 코드를 서로 다른 각도에서 지적.
- **Action Required**: (a) `2>&1` 제거 → stdout JSON, stderr 경고 분리. (b) `--export-env` 플래그 또는 명시적 `python -c` snippet으로 bash 파싱 방법 지정. (c) stdout JSON 필드 스키마를 §5.1에 명시.

#### 3. [ACCEPT] [High] AF_SKIP_PROVIDER 적용 시점 §2.2 vs §4.3 내부 모순
- **Critic**: "§2.2 step 1은 probe 함수 최상단에서 AF_SKIP_PROVIDER 체크, §4.3는 캐시 조회 후 마스킹. AF_SKIP_PROVIDER unset 시 즉시 복원 여부가 달라짐."
- **Cross**: not flagged (별도 NOT_INSTALLED 마스킹 이슈로 접근).
- **Judgment**: 원문 §4.3이 "캐시는 실제 상태, skip은 결과만 조정"으로 의도를 명확히 밝혔으므로 §4.3가 정답. §2.2 step 1이 문서와 불일치.
- **Action Required**: §2.2 step 1을 삭제하고, "AF_SKIP_PROVIDER 마스킹은 `detect_provider_states()` 반환 직전에 적용 (§4.3 참조)"로 교체.

#### 4. [ACCEPT] [High] 기존 provider adapter 재사용 누락 — 커맨드 매트릭스 중복
- **Critic**: not flagged.
- **Cross**: "`core/providers/cli.py:68-106`이 이미 provider별 명령, auth 명령, env override, headless 플래그를 정의. `execute_cli_chat()` (line 698)도 auth preflight, env 스트리핑, stdin 처리를 포함. `core/provider_detect.py`와 `af-cross-review.md`가 이를 중복 정의하면 유지보수 분기 발생."
- **Judgment**: Cross의 파일:라인 증거가 강력. 신규 모듈이 기존 어댑터를 우회하면 CLI 시그니처 변경 시 두 곳을 수정해야 함.
- **Action Required**: `core/provider_detect.py`의 auth ping 로직을 `cli.py`에서 `probe_cli_provider_auth()` 형태로 추출해 재사용. §2.3 Auth Ping 매트릭스를 `cli.py` 위임으로 교체.

#### 5. [ACCEPT] [High] frozen 빌드에서 `python -m core.provider_detect` 동작 미정의
- **Critic** (Missing): "`dist/af/af.exe` 배포 환경에서 소스 트리 없으면 ModuleNotFoundError. 소스 트리 전제 또는 `af provider detect` CLI 서브커맨드 필요."
- **Cross** (HOLD): "`run_factory_cli.py`에 provider/cache 서브커맨드 없음. frozen 지원 여부에 따라 설계 분기."
- **Judgment**: 두 리뷰어가 동일 배포 갭을 지적. HOLD → ACCEPT 상향 (frozen 배포는 이미 사용 중인 경로).
- **Action Required**: "af-cross-review.md는 소스 트리 환경에서만 실행된다"를 §5.1에 명시하거나, `run_factory_cli.py`에 `af provider-detect` 서브커맨드 추가 후 §1.1 변경 파일 매트릭스에 포함.

#### 6. [ACCEPT] [Medium] AF_SKIP_PROVIDER → NOT_INSTALLED 관측 불가 마스킹
- **Critic**: not flagged (타이밍 모순으로 접근).
- **Cross**: "`core/providers/registry.py:277-290`의 install/auth 가이드 메시지가 skip을 not_installed로 오표시. 사용자 혼란."
- **Judgment**: Cross 단독이나 registry 파일 증거가 구체적. ACCEPT.
- **Action Required**: JSON 출력에 `"skipped": ["codex_cli"]` 최상위 필드 추가. 보고서에 "미설치" 대신 "AF_SKIP_PROVIDER로 제외됨" 표기.

#### 7. [ACCEPT] [Medium] 캐시 write에 프로세스 간 락 없음
- **Critic**: not flagged.
- **Cross**: "`core/file_lock.py:43`과 `scripts/review_gate.py:182-215`가 이미 프로세스 안전 락 패턴을 사용. concurrent hook 호출 시 read-modify-write 경쟁 발생."
- **Judgment**: Cross 단독이나 `file_lock.py` 존재 증거가 강력. ACCEPT.
- **Action Required**: 캐시 load/update/write를 `locked_file(str(cache_path))`로 감쌈. 고정 `.json.tmp` 대신 `tempfile.mkstemp()` 사용.

#### 8. [ACCEPT] [Medium] §10 R6 nightly 완화책의 존재하지 않는 wildcard 문법
- **Critic**: "`auth_expired_*` wildcard는 §4의 `AF_SKIP_PROVIDER` 시맨틱(provider_id 목록)과 다른 문법. 정의 없음. 실제 임시 해결책(AF_SKIP_PROVIDER=codex_cli)도 미명시."
- **Cross**: not flagged.
- **Judgment**: Critic 단독이나 §4와의 명백한 불일치로 ACCEPT.
- **Action Required**: R6 완화책을 `AF_SKIP_PROVIDER=codex_cli,gemini_cli`를 nightly cron 환경변수에 세팅하는 것으로 구체화.

#### 9. [ACCEPT] [Medium] Windows Git Bash `timeout` 명령 충돌
- **Critic**: "Windows Git Bash의 `timeout`은 GNU coreutils가 아닌 `C:\Windows\System32\timeout.exe`(카운트다운 딜레이 명령). bash `& + individual timeout 180s` 구현 불가."
- **Cross**: not flagged.
- **Judgment**: Critic 단독이나 Windows 환경 사실에 근거. 이미 R5에서 Windows bash 이슈를 인식한 설계가 timeout을 누락한 것은 일관성 결여. ACCEPT.
- **Action Required**: `( <cmd> ) & PID=$!; sleep 180; kill -0 $PID 2>/dev/null && kill $PID` 패턴 명시 또는 Step 0~2 전체를 Python(`subprocess.run(..., timeout=180)`)으로 이동.

#### 10. [ACCEPT] [Medium] Sprint A 신규 핵심 모듈이 단일 codex 리뷰만 받는 역설
- **Critic**: "`core/provider_detect.py`는 auth ping·캐시·AF_SKIP_PROVIDER 로직이 집중된 신규 핵심 모듈인데 Sprint A에서 단일 codex(구 fan-out)로만 검증됨."
- **Cross**: not flagged.
- **Judgment**: 프로세스 위험. ACCEPT.
- **Action Required**: Sprint A 설명에 "Sprint B 완료 후 A+B 전체를 새 fan-out으로 통합 재검증하는 Sprint C 단계"를 추가.

#### 11. [ACCEPT] [Medium] dedup "키워드 유사" 기준 미정의
- **Critic** (Missing): "§5.3의 `키워드 유사` — LLM 기반인지 Python 코드인지, threshold 없음. 재현성 없음."
- **Cross**: not flagged.
- **Judgment**: 구현 시 핵심 결정 사항. ACCEPT.
- **Action Required**: "file:line이 완전 일치하면 dedup, 나머지는 별도 항목" 등 결정론적 기준을 §5.3에 추가.

#### 12. [ACCEPT] [Medium] 캐시 최상위 `ts` vs per-provider `checked_at` TTL 판단 기준 모호
- **Critic** (Missing): "§3.1 JSON에 최상위 `ts`와 per-provider `checked_at` 두 개 존재. §3.3이 TTL 판단 기준을 명시 안 함. partial refresh 시나리오에서 `ts` 기준이 맞지 않을 수 있음."
- **Cross**: not flagged.
- **Judgment**: 구현 분기 발생. ACCEPT.
- **Action Required**: §3.3에 "TTL 만료는 최상위 `ts` 기준 (전체 재검사). per-provider 무효화는 `--invalidate <id>` 명시 호출만" 또는 반대 설계를 명확히 결정.

#### 13. [REJECT] [Low] registry.py 시그니처 동결이 충돌 발생
- **Source**: Cross (Finding #6, Self-rejected)
- **Original Finding**: "새 provider detection layer가 registry 선택 로직과 충돌할 수 있음."
- **Rejection Reason**: Cross 리뷰어 스스로 기각. `registry.py`가 `CLI_PROVIDER_IDS`와 install detection을 안정적 인터페이스로 노출하며, 신규 모듈이 기존 시그니처를 변경하지 않고 재사용하는 설계로 충돌 없음.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | AUTH_EXPIRED 과도한 오분류 | High | ACCEPT | Both |
| 2 | CLI JSON 계약 미명세 + bash 파싱 누락 | High | ACCEPT | Both |
| 3 | AF_SKIP_PROVIDER 적용 시점 §2.2 vs §4.3 모순 | High | ACCEPT | Critic |
| 4 | 기존 provider adapter 재사용 누락 | High | ACCEPT | Cross |
| 5 | frozen 빌드에서 모듈 호출 미정의 | High | ACCEPT | Both |
| 6 | AF_SKIP_PROVIDER → NOT_INSTALLED 마스킹 | Medium | ACCEPT | Cross |
| 7 | 캐시 write 프로세스 간 락 없음 | Medium | ACCEPT | Cross |
| 8 | R6 nightly 완화책 wildcard 문법 미정의 | Medium | ACCEPT | Critic |
| 9 | Windows Git Bash timeout 명령 충돌 | Medium | ACCEPT | Critic |
| 10 | Sprint A 핵심 모듈 단일 codex 리뷰 역설 | Medium | ACCEPT | Critic |
| 11 | dedup "키워드 유사" 기준 미정의 | Medium | ACCEPT | Critic |
| 12 | 캐시 ts vs checked_at TTL 기준 모호 | Medium | ACCEPT | Critic |
| 13 | registry.py 시그니처 동결이 충돌 발생 | Low | REJECT | Cross |

---

### Recommendations

구현 전 반드시:

1. **#4 먼저 해결**: `core/providers/cli.py`에서 `probe_cli_provider_auth()` 추출 여부를 결정. 이 결정이 §2.3 Auth Ping 매트릭스 전체를 바꿈.
2. **#3 해결**: §2.2 step 1 삭제 + §4.3 방식으로 단일화. 두 섹션 동시 편집.
3. **#1 + #2 묶음 해결**: `ProviderProbeResult`에 `category` 추가 + CLI stdout/stderr 분리 + `--export-env` 또는 Python snippet 명시. 이 세 항목은 같은 인터페이스 변경으로 처리 가능.
4. **#5 즉시 결정**: "소스 트리 전용" 전제 명시 vs `af provider-detect` CLI 서브커맨드 추가. 어느 쪽이든 §1.1 파일 매트릭스에 반영.
5. **#7**: `file_lock.py` + `tempfile.mkstemp()` 패턴을 §3.2에 명시.
6. **#6 + #8 + #12 + #11**: 설계 문서 텍스트 수정만 필요. 구현 전 §3~§5 일괄 개정.
7. **#9**: Windows 지원이 목표라면 Python subprocess 방식으로 이동 결정. 이것이 #1~#2 해결과도 자연스럽게 이어짐.
8. **#10**: Sprint 계획 섹션에 "Sprint C 통합 재검증" 단계 한 줄 추가.