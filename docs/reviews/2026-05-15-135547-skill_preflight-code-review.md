# Code Review: skill_preflight

> Source: core/skill_preflight.py
> Date: 2026-05-15 13:55
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

paired fix (`AF_DISABLE_REGISTRY_WRITE` env-var + early return + `agent_launcher.py` env set)의 핵심 의도는 두 리뷰어 모두 수용한다. Critical regression(security/data-loss)은 없으나, env-var scope·subprocess 상속·CLI 진입 분류에 correctness 결함이 남아 있어 WARN으로 머지 가능 (단, 추가 PR로 후속 정리 필요).

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] Registry-write disable이 project-local registry까지 차단 + docstring 불일치
- **Critic** (HIGH #1 + MEDIUM #5): early return은 글로벌(SKILLS_DIR)뿐 아니라 project-local(PROJECT_SKILLS_DIR) write까지 모두 차단함. docstring은 "글로벌 registry write skip"만 명시.
- **Cross** (ACCEPT #1): `_update_registry_status()`가 양쪽 registry를 탐색하는데(`core/skill_preflight.py:261`) early return이 둘 다 무력화. caller 의도(`agent_launcher.py:25-26`)는 글로벌만 차단하는 것.
- **Judgment**: 두 리뷰어가 같은 결함을 독립적으로 지적. 코드 evidence 명확.
- **Action Required**: (a) `_update_registry_status` 분기에서 `SKILLS_DIR` 후보만 필터링하거나, (b) env-var 이름을 `AF_DISABLE_GLOBAL_REGISTRY_WRITE`로 재명명하고 docstring 정정. 양쪽 registry 케이스를 모두 다루는 테스트 추가.

#### 2. [ACCEPT] [High] Self-run subcommand whitelist가 단일 element라 다른 subcommand가 isolation 대상이 됨
- **Critic** (HIGH #3): `argv[0] in {"project"}`만 통과시키는데, `preflight`, `chat`, `wf`, `agent`, `skill` 등 다른 subcommand 호출 시 자연어 task로 오인되어 isolated PROJECT_ROOT + registry 차단이 걸림. 특히 `preflight` subcommand는 registry 갱신이 *본 기능*인데 이번 fix가 무력화.
- **Cross**: not flagged.
- **Judgment**: 단일 리뷰어 지적이지만 evidence가 매우 구체적이고 reproducible. `run_factory_cli.py`의 라우팅 테이블과 대조하면 즉시 확인 가능.
- **Action Required**: known-subcommand allow-list를 `run_factory_cli.py` 라우팅 테이블에서 단일 source로 import. 최소한 `preflight`, `chat`, `wf`, `agent`, `skill` 포함.

#### 3. [ACCEPT] [High] AF_DISABLE_REGISTRY_WRITE flag가 모든 child subprocess에 무조건 상속
- **Critic** (HIGH #2): `os.environ.setdefault(...)`은 이후 모든 `subprocess.Popen`/`agent_worker.py` spawn에 자동 전파. Worker가 격리된 temp PROJECT_ROOT 안에서 정당하게 preflight registry를 갱신해야 하는 케이스도 함께 막힘.
- **Cross**: not flagged.
- **Judgment**: 단일 리뷰어이지만 Python `os.environ` 동작 특성상 명백한 사실. F12 paired fix의 의도가 launcher 프로세스에만 적용되어야 한다면 propagate가 부작용임.
- **Action Required**: worker spawn 직전 env에서 pop, 또는 #1 해결책처럼 env-var 자체를 글로벌-specific으로 좁히면 자동 해결.

#### 4. [ACCEPT] [Medium] env-var truthy 평가가 "0"/"false"/"no"도 disable로 해석
- **Critic** (HIGH #1 → Medium으로 조정): `os.environ.get("AF_DISABLE_REGISTRY_WRITE")` 는 비-빈 문자열이면 truthy. 사용자가 `=0` 또는 `=false`로 끄려 해도 skip이 됨. AF 코드베이스 다른 곳의 패턴과 불일치.
- **Cross**: not flagged.
- **Judgment**: code quality + 일관성 이슈. 보안 critical은 아니지만 surprise factor 있음.
- **Action Required**: `core/utils.py`에 `env_flag()` 헬퍼 추가 후 `if env_flag("AF_DISABLE_REGISTRY_WRITE"):` 패턴 사용.

#### 5. [ACCEPT] [Medium] verbose 모드에서 skip 사실이 출력되지 않음
- **Critic** (MEDIUM #4): 같은 함수의 다른 분기(`Skill 'X' not found`, `Registry update failed`)는 verbose 출력이 있는데 새 skip 분기만 silent.
- **Cross**: not flagged.
- **Judgment**: 디버깅 ergonomics. 향후 isolation 정책 변경 시 추적성 확보.
- **Action Required**: `if self.verbose: print(f"[Preflight] Registry write skipped (AF_DISABLE_REGISTRY_WRITE) for {result.skill_id}")` 추가.

#### 6. [ACCEPT] [Medium] argv dash 프리픽스(`--help`, `--version`) 미처리
- **Critic** (MEDIUM #6): `python agent_launcher.py --help` 같은 global flag도 자연어 task로 오인되어 isolation 진입.
- **Cross**: not flagged.
- **Judgment**: #2의 allow-list 도입으로 자연스럽게 해결되는 sub-case. 별도 픽스로 빠르게 막아도 됨.
- **Action Required**: `if argv[0].startswith("-"): return` 추가, 또는 #2 allow-list 해결책에 통합.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Disable flag scope (글로벌+로컬 모두 차단) + docstring 불일치 | High | ACCEPT | Both |
| 2 | Subcommand whitelist single-element (`{"project"}`) | High | ACCEPT | Critic |
| 3 | Flag가 모든 child subprocess에 상속 | High | ACCEPT | Critic |
| 4 | env-var truthy 평가 ("0"/"false" 도 skip) | Medium | ACCEPT | Critic |
| 5 | verbose 모드 skip log 누락 | Medium | ACCEPT | Critic |
| 6 | argv dash 프리픽스 미처리 | Medium | ACCEPT | Critic |

### Recommendations

1. **즉시 fix (High)**: 
   - #1 + #3 동시 해결: env-var 이름을 `AF_DISABLE_GLOBAL_REGISTRY_WRITE`로 재명명하고 `_update_registry_status` 내부에서 후보 목록 필터링 방식으로 변경 (early return 제거). docstring 동시 정정.
   - #2: `run_factory_cli.py`의 known subcommand 집합을 single source로 import하여 `if argv[0] in KNOWN_SUBCOMMANDS: return` 패턴 적용. `preflight`, `chat`, `wf`, `agent`, `skill` 누락 확인.
2. **후속 PR (Medium)**: 
   - #4: `core/utils.py`에 `env_flag()` 헬퍼 추가, 전 코드베이스 일관 적용.
   - #5: verbose 분기 추가.
   - #6: allow-list 도입 시 자동 해결됨.
3. **관련 잔존 이슈 (별건)**: `code-review.md §3.3 M10` 의 non-atomic YAML write(line 298 `with open ... yaml.dump`)가 같은 함수 안에 있다. 본 PR과 분리하여 별도 cleanup PR 권장.
4. **Cross-review의 두 REJECT** (API 시그니처 미변경, mojibake comment 무관)는 `py_compile` + 33 테스트 PASS로 검증됨 — 추가 조치 불필요.