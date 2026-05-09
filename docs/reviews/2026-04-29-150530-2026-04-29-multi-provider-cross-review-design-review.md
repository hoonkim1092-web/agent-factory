# Design Review: 2026-04-29-multi-provider-cross-review

> Source: docs/2026-04-29-multi-provider-cross-review.md
> Date: 2026-04-29 15:05
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 3 providers)
> Trigger: claude

---

두 리뷰를 읽고 중복 항목을 매핑한 후 집계합니다.

---

## Final Design Review

### Verdict: BLOCK

Critical 1건 + High 6건 포함. Critical이 해결되기 전까지 Sprint A 구현에 진입하지 않는다.

---

### Aggregated Findings (11 total)

#### 1. [ACCEPT] [Critical] Step 0 bash 조건문이 pseudocode — 미구현 의존성
- **Critic**: `if [ blocked가 비어있지 않음 ]`은 bash 조건문이 아니라 한국어 placeholder다. JSON 파싱 방법이 설계에 없으면 Sprint B 구현자가 임의로 결정한다.
- **Cross**: not flagged (watcher path 이슈로 다른 각도에서 접근)
- **Judgment**: 원문 §5.1 Lines 179-192를 보면 `if [ blocked가 비어있지 않음 ]`, `if [ fan_out가 비어있음 ]`이 실제 bash 문법이 아닌 한국어 pseudocode로 작성되어 있다. 이 상태로는 구현 불가능하다. Critic의 증거가 명확하므로 단독이어도 ACCEPT.
- **Action Required**: Step 0 출력 포맷을 bash-parseable 평문(`FAN_OUT=codex_cli,gemini_cli\nBLOCKED=gemini_cli`)으로 재정의하거나, Python wrapper가 결과를 환경변수로 export하는 방식을 명시한다. `provider_detect --json`의 출력 포맷과 bash 파싱 방법을 코드 수준으로 구체화해야 한다.

---

#### 2. [ACCEPT] [High] 자동화 watcher 경로가 설계 범위에서 누락
- **Critic**: not flagged
- **Cross**: `scripts/design_review_watcher.py:207`의 자동화 경로는 `core.review_runner.detect_providers()` + `run_critic()` + `run_cross()`를 사용한다. `.claude/agents/af-cross-review.md` 변경은 이 경로에 영향이 없다.
- **Judgment**: Cross reviewer가 실제 코드 라인(`design_review_watcher.py:214-297`, `review_runner.py:28-34`)을 참조한 강한 증거다. 설계가 수동 Claude Code 에이전트 실행만 다루면서 자동화 훅에도 효과가 있다고 암시한다면 범위 오해를 유발한다.
- **Action Required**: §1.1에 "이 설계는 수동 af-cross-review 에이전트 실행에만 적용. 자동화 watcher(`design_review_watcher.py`) 경로에는 별도 작업 필요"를 명시하거나, `core/review_runner.py`를 범위에 추가해 fan-out을 구현한다.

---

#### 3. [ACCEPT] [High] Provider ID 계약이 불일치
- **Critic**: not flagged
- **Cross**: `core/providers/registry.py:7`은 `claude_cli/gemini_cli/codex_cli`를 정의하지만, `core/review_runner.py:28-34`와 `core/review_report.py:29`는 `claude/codex/gemini` 단축 이름을 사용한다. 설계는 `claude_cli` 스타일을 쓰지만 기존 review 시스템과 계약이 다르다.
- **Judgment**: 코드 레벨 증거가 명확하다. 두 naming convention이 공존하면 review_runner에서 연결 시 버그가 발생한다.
- **Action Required**: §2.1 또는 §1.1에 ID 변환 계약을 명시한다 (`codex_cli → codex`). `review_runner`가 `CLI_PROVIDER_IDS`를 직접 소비하고 CLI 명령 생성 시에만 단축 이름으로 변환하는 방식을 권장한다.

---

#### 4. [ACCEPT] [High] shell 명령 매트릭스가 기존 provider 추상화를 우회
- **Critic**: not flagged
- **Cross**: `core/providers/cli.py:618`에 provider 명령 빌더가 있고, `execute_cli_chat()`가 stdin 처리·env stripping·session state를 관리한다. 설계의 raw `codex exec -s danger-full-access -o /tmp/...` 방식은 이를 모두 무시한다.
- **Judgment**: 기존 `CliChatRequest` + `execute_cli_chat()` 경로를 우회하면 provider별 플래그 처리, auth preflight, destructive guard가 빠진다. `tests/test_cli_providers.py`가 codex stdin 방식을 assert한다는 증거도 있다.
- **Action Required**: §5.2 명령 매트릭스를 raw shell 대신 `CliChatRequest` + `execute_cli_chat()` 재사용으로 교체한다. 출력 파일이 필요하면 `result["text"]`를 Python에서 write한다.

---

#### 5. [ACCEPT] [High] AUTH_EXPIRED 분류 과잉 + auth ping 비용/신뢰성 오류
- **Critic**: `claude -p "ok"`는 full API request로 system prompt 포함 수백 토큰 소비. 인증 실패 시 exit code 1 보장 없음. "1~10 토큰" 수치는 틀렸다.
- **Cross**: exit code != 0 또는 timeout을 AUTH_EXPIRED로 일괄 처리하면 permission denied, rate limit, CLI 문법 오류, 네트워크 장애가 모두 AUTH_EXPIRED로 잘못 분류된다. `core/providers/cli.py:119`의 `_AUTH_REQUIRED_MARKERS`와 `_classify_cli_issue()`가 이미 세분화된 분류를 제공한다.
- **Judgment**: 두 리뷰어가 동일 문제의 다른 측면을 지적했다 — Critic은 ping 방법, Cross는 오류 분류. 두 문제 모두 §2.2-2.3에 영향을 준다.
- **Action Required**: (a) "1~10 토큰" 수치를 실측 기반으로 수정하거나 삭제. (b) AUTH_EXPIRED 판정을 `_classify_cli_issue()` 기반 auth marker grep으로 구체화. (c) exit code만으로 판단하지 않고 stderr 패턴 매칭 방식을 명시.

---

#### 6. [ACCEPT] [High] 동시 실행 시 고정 경로 충돌 — /tmp와 cache 두 곳
- **Critic**: 두 af-cross-review가 동시 실행되면 `/tmp/cr-codex.txt`를 두 프로세스가 덮어쓴다. Windows에서 `/tmp/` 매핑도 환경마다 다르다.
- **Cross**: `path.with_suffix('.json.tmp')` 고정 이름의 cache 임시 파일도 동일한 레이스 조건. `design_review_watcher.py`가 백그라운드 작업을 spawn하므로 동시 호출이 실제로 발생한다.
- **Judgment**: 두 리뷰어가 다른 파일(review output vs cache)에서 같은 root cause를 지적했다. 증거가 모두 강하다.
- **Action Required**: (a) §5.2: `/tmp/cr-codex-$$.txt` (PID suffix) 또는 `mktemp` 사용. (b) §3.2: `tempfile.mkstemp`로 유일한 임시 파일 경로 생성 후 `os.replace`. (c) Windows 호환성: `python -c "import tempfile; print(tempfile.mktemp())"` 방식 명시.

---

#### 7. [ACCEPT] [High] 야간 파이프라인 AUTH_EXPIRED 차단에 범위 내 완화책 없음
- **Critic**: R6의 `AF_SKIP_PROVIDER=auth_expired_*` 문법은 §4의 provider_id 목록 시맨틱과 충돌한다. `auth_expired_*`는 state 필터지 provider_id가 아니다. "후속 작업"으로 미루면 배포 즉시 nightly가 인증 만료 시 항상 중단된다.
- **Cross**: not flagged directly (AUTH_EXPIRED 분류 문제로 접근)
- **Judgment**: Critic의 §4 시맨틱 충돌 지적은 원문 대조 시 유효하다. `AF_SKIP_PROVIDER`가 콤마 구분 provider_id를 받도록 §4.1에 정의되어 있는데, R6에서는 `auth_expired_*` 와일드카드를 제안하는 일관성 오류가 있다.
- **Action Required**: Sprint A에 `detect_provider_states(skip_auth_expired: bool = False)` 파라미터 또는 `--no-block-on-auth-expired` CLI 플래그를 포함시킨다. nightly 진입점에서 이 플래그를 설정하는 것은 Sprint B에 포함한다고 §6/§8에 명시.

---

#### 8. [ACCEPT] [Medium] Step 3 dedup "키워드 유사" 알고리즘 미명시
- **Critic**: Claude가 직접 판단하는지 Python 스크립트인지 불명확. 현재 상태로는 구현자가 임의로 결정한다.
- **Cross**: not flagged
- **Judgment**: 단독 Critic 지적이지만, af-cross-review.md가 Claude 에이전트 프롬프트임을 감안하면 "Claude가 직접 판단"이라고 명시하는 것만으로 해결된다. 증거가 충분하다.
- **Action Required**: §5.3에 "dedup 판정 주체는 Claude(af-cross-review 에이전트) 자신. 두 결과 텍스트를 읽고 파일:라인+심각도 일치 + 지적 내용 의미 유사 시 합산"을 명시하거나, MVP에서는 dedup을 포기하고 "두 결과를 병렬 섹션으로 그대로 제시"로 단순화.

---

#### 9. [ACCEPT] [Medium] `--exclude-self claude_cli` 하드코딩 — 실행 주체 가정 미문서화
- **Critic**: af-cross-review가 항상 claude_cli에 의해 실행된다는 가정이 있지만 §1.1에 명시되지 않았다.
- **Cross**: not flagged
- **Judgment**: 현재는 올바른 가정이지만 문서화 없이 코드에만 남기면 미래 시나리오에서 묵시적 버그가 된다. 단기 수정 비용이 낮다.
- **Action Required**: §1.1 또는 §5.1에 "af-cross-review는 claude_cli 환경에서만 실행됨"을 명시적 가정으로 기록.

---

#### 10. [HOLD] [Medium] Sprint A/B 배포 의존성 + 버전 bump 요건 불명확
- **Critic**: Sprint B의 `af-cross-review.md`는 Sprint A에서 새로 생성되는 `core/provider_detect`를 호출한다. Sprint A frozen build가 먼저 릴리즈되지 않으면 Sprint B 배포 직후 즉시 실패한다.
- **Cross**: `version.py`, `install-af.ps1`, `install-af.sh` 업데이트 필요 여부가 불명확. exe 릴리즈로 즉시 배포하는지 source-only로 유지하는지 설계에 없다.
- **Judgment**: 두 리뷰어 모두 배포/릴리즈 흐름을 문제로 봤다. 단, 이 결정은 저자(사용자)의 릴리즈 계획에 따라 달라진다 — 판단에 필요한 정보가 없어 HOLD.
- **Question for Author**: Sprint A 완료 후 즉시 `af.exe` 릴리즈(`gh release create`)를 하는가, 아니면 source-only로 두고 Sprint B와 묶어서 릴리즈하는가? exe 배포 예정이라면 `version.py`와 `install-af.ps1` 버전 bump를 §7 변경 매트릭스에 추가해야 한다.

---

#### 11. [REJECT] [Low] `af.spec` hiddenimport 누락
- **Source**: Cross #6
- **Original Finding**: 새 `core/*.py`를 PyInstaller hiddenimports에 추가해야 한다.
- **Rejection Reason**: 원문 §1.1 변경 파일 매트릭스에 `af.spec — hiddenimports에 core.provider_detect 추가`가 명시되어 있다. `CLAUDE.md` 규칙과 정합하며, Cross 리뷰어도 이를 인지하고 REJECT했다.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Step 0 bash parsing is pseudocode | Critical | ACCEPT | Critic |
| 2 | Automated watcher path out of scope | High | ACCEPT | Cross |
| 3 | Provider ID contracts inconsistent | High | ACCEPT | Cross |
| 4 | Shell command matrix bypasses provider abstraction | High | ACCEPT | Cross |
| 5 | AUTH_EXPIRED overclassification + ping cost/reliability | High | ACCEPT | Both |
| 6 | Concurrent /tmp + cache temp file path collision | High | ACCEPT | Both |
| 7 | Nightly pipeline has no in-scope auth_expired workaround | High | ACCEPT | Critic |
| 8 | Step 3 dedup algorithm owner unspecified | Medium | ACCEPT | Critic |
| 9 | `--exclude-self` hardcoded assumption undocumented | Medium | ACCEPT | Critic |
| 10 | Sprint A/B deployment ordering + version bump unclear | Medium | HOLD | Both |
| 11 | af.spec hiddenimport forgotten | Low | REJECT | Cross |

---

### Recommendations

구현 전 설계문서에서 수정해야 할 항목 (우선순위 순):

1. **[#1 — Critical, 즉시]** §5.1 Step 0 bash 코드를 실제 실행 가능한 형태로 교체. `provider_detect` 출력 포맷을 bash-parseable 평문으로 재정의하거나 Python wrapper export 방식을 코드 수준으로 명시.
2. **[#2 — High]** §1.1 범위에 "수동 af-cross-review 에이전트 전용. 자동화 watcher 경로(`review_runner.py`, `design_review_watcher.py`)는 별도 작업"을 명시하거나 scope를 확장.
3. **[#3 — High]** §2.1에 ID 변환 계약(`claude_cli → claude` 등) 명시. `review_runner` 연결 지점 특정.
4. **[#4 — High]** §5.2 raw shell 명령을 `CliChatRequest` + `execute_cli_chat()` 재사용으로 교체.
5. **[#5 — High]** §2.2-2.3에서 AUTH_EXPIRED 판정을 exit code 단독이 아닌 `_classify_cli_issue()` 패턴 기반으로 교체. "1~10 토큰" 수치 삭제.
6. **[#6 — High]** §3.2 임시 파일을 `tempfile.mkstemp`로 교체. §5.2 `/tmp/cr-{provider}-$$.txt` (PID suffix) 방식 명시.
7. **[#7 — High]** Sprint A 범위에 `skip_auth_expired` 파라미터 또는 `--no-block-on-auth-expired` 플래그를 추가. nightly 연결은 Sprint B로 위임하되 §8에 명시.
8. **[#8 — Medium]** §5.3 dedup 판정 주체를 "Claude 에이전트 자신"으로 명시하거나 MVP에서 dedup 제거.
9. **[#9 — Medium]** §1.1 또는 §5.1에 "af-cross-review 실행 주체 = claude_cli" 가정을 명시적 제약으로 기록.
10. **[#10 — HOLD]** 저자가 릴리즈 계획을 확정 후 §7 변경 매트릭스에 `version.py` / `install-af.ps1` 포함 여부와 Sprint A→B 배포 순서 의존성을 추가.