# Code Review: registry_manager

> Source: core/registry_manager.py
> Date: 2026-05-15 14:00
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

3건의 High 결함(글로벌 vs 프로젝트-로컬 registry 무차별 차단, `workflow_apply()` 가드 누락, env truthy 파싱)이 양 리뷰에서 누적 확인됐다. Critical regression(crash/data-loss)은 없어 BLOCK은 아니지만, F12 격리 의도가 실제로 완성되지 않은 상태 — 머지 전 #1/#2/#3은 정리 권고.

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] `_update_registry_status` early-return이 프로젝트-로컬 registry까지 차단
- **Critic**: docstring은 "글로벌 write skip"인데 line 263-269가 `SKILLS_DIR`+`PROJECT_SKILLS_DIR` 양쪽을 순회하므로 self-run isolated tempdir 하위 registry도 무력화됨
- **Cross**: not flagged
- **Judgment**: ACCEPT. Critic이 코드 line(254-272)과 호출 분기를 함께 인용. self-run 모드에서 `PROJECT_SKILLS_DIR`은 isolated tempdir 아래라 안전하게 쓸 수 있는데 함께 차단되는 건 caller 의도(`agent_launcher.py:18-26`)와 충돌.
- **Action Required**: env-var set 시 candidate 목록에서 `SKILLS_DIR`만 제거하고 `PROJECT_SKILLS_DIR`은 계속 진행하도록 분기. 또는 env-var 명칭을 `AF_DISABLE_GLOBAL_REGISTRY_WRITE`로 변경하고 양쪽 docstring 정정.

#### 2. [ACCEPT] [High] `workflow_apply()`는 새 가드 미적용 — 글로벌 workflow_registry.yaml 여전히 mutate
- **Critic**: not flagged
- **Cross**: `core/registry_manager.py:403` `workflow_apply()`가 `write_yaml(WORKFLOW_PATH, ...)`로 직접 쓰며 `_write_registry` 가드 우회. `core/skill_procurer.py:1149`가 빌드 후 호출.
- **Judgment**: ACCEPT. Cross가 호출 체인 + 파일/라인 인용. 격리 의도와 정확히 모순되는 silent leak.
- **Action Required**: `workflow_apply()` 진입부에 동일 가드 추가 — `if _env_flag("AF_DISABLE_REGISTRY_WRITE"): return`.

#### 3. [ACCEPT] [High] env-var 파싱이 `_env_flag` 미사용 — `=0`/`=false`가 차단을 ON으로 만듦
- **Critic**: #4 — 3곳(`registry_manager.py:49`, `skill_preflight.py:258`, `agent_launcher.py:49`)에서 raw `os.environ.get` 사용
- **Cross**: #2 — `core/file_io.py:22`의 `_env_flag()`가 이미 표준. `docs/reviews/2026-05-15-135547-skill_preflight-code-review.md:38`이 동일 flag family에 `_env_flag` 사용을 명시 요구.
- **Judgment**: ACCEPT. 양 리뷰 모두 같은 결함 지적, Cross가 프로젝트 표준 위반을 추가 입증. Critic이 Medium으로 매겼지만 Cross가 인용한 프로젝트 표준 요구로 High 승격.
- **Action Required**: 3곳 모두 `_env_flag("AF_DISABLE_REGISTRY_WRITE")`로 교체.

#### 4. [HOLD] [Medium] `_write_registry`가 `_read_only` 체크보다 먼저 silent return — lock↔registry 불일치 위험
- **Critic**: #2 — read-only 환경에서 PermissionError 시그널 silently 삼킴. `_install_skill_file:241` / `register_built:390` 등이 "성공"한 듯 반환되고 후속 `lock_skill_state` 호출과 불일치 발생.
- **Cross**: #3 — REJECT. self-run 모드에서 caller가 명시적으로 no-op을 원하므로 의도된 거동.
- **Judgment**: 두 리뷰가 contradict. Cross는 "intent 측면"에서 reject하지만 Critic의 핵심 우려(lock_skill_state 호출 후 registry 미반영 → 불일치)는 Cross가 직접 다루지 않음. 그러나 self-run 격리 환경에서 lock 파일 역시 isolated tempdir 하위이므로 실제 production 잔존물은 없을 가능성이 높음. **실제 lock↔registry skew가 어떤 흐름에서 사용자에게 노출되는지 재현 시나리오가 없음**.
- **Question for Author**: self-run isolated tempdir에서 lock 파일 경로가 어디로 가는지 확인. tempdir 내부에 머문다면 Cross의 reject가 맞음 → reject. 글로벌 lock 위치를 건드린다면 Critic의 우려가 맞음 → ACCEPT.

#### 5. [ACCEPT] [Medium] `_KNOWN_SUBCOMMANDS` 화이트리스트가 2곳에 하드코드
- **Critic**: #3 — `agent_launcher.py:41` (isolation skip)와 `:767` (`_detect_mode`)가 동일 의도지만 별도 리터럴 set. 신규 subcommand 추가 시 한쪽만 갱신되면 silent regression.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 단순 DRY 위반이고 미래 confusion 비용 명확.
- **Action Required**: 모듈 상단 상수로 추출, 양쪽에서 동일 상수 참조.

#### 6. [ACCEPT] [Medium] `if __name__ == "__main__":` 가드 — import 진입 시 isolation 미적용
- **Critic**: #5 — `python -m`이나 import 경로에서 isolation 안 됨. 함수 docstring 전제와 fragile하게 결합.
- **Cross**: not flagged
- **Judgment**: ACCEPT. 현재 main 진입만 보장한다는 사실은 docstring에서 명시되지 않아 misuse 가능.
- **Action Required**: 모듈 상단 주석으로 "직접 실행 전용" 명시, 또는 `af.cli.bootstrap()` 헬퍼로 추출해 다른 진입점도 호출 가능하게.

#### 7. [ACCEPT] [Low] isolated tempdir cleanup hook 부재
- **Critic**: #6 — `tempfile.gettempdir()` 하위 `af_self_run_*` 누적. Windows는 자동 정리 안 됨.
- **Cross**: not flagged
- **Judgment**: ACCEPT, 단 본 PR 범위 밖 후속 처리 가능.
- **Action Required**: 별도 PR로 `atexit.register(shutil.rmtree, isolated, ignore_errors=True)` 또는 `runs/_self_run/` 보존 위치 + 정책.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_update_registry_status` scope over-block | High | ACCEPT | Critic |
| 2 | `workflow_apply()` 가드 누락 | High | ACCEPT | Cross |
| 3 | env-var truthy 파싱 — `_env_flag` 미사용 | High | ACCEPT | Both |
| 4 | `_write_registry` read-only 체크 우회 | Medium | HOLD | Contradict |
| 5 | `_KNOWN_SUBCOMMANDS` 중복 | Medium | ACCEPT | Critic |
| 6 | `__main__` guard로 import 진입 미보호 | Medium | ACCEPT | Critic |
| 7 | tempdir cleanup 부재 | Low | ACCEPT | Critic |

### Recommendations

1. **머지 전 필수 (3건)**:
   - `core/skill_preflight.py:258` — early return을 `SKILLS_DIR` 후보 필터링으로 교체 (Finding #1)
   - `core/registry_manager.py:403` — `workflow_apply()` 진입부에 동일 가드 추가 (Finding #2)
   - 3곳 raw `os.environ.get` → `_env_flag()` 교체 (Finding #3)

2. **HOLD 해소 (1건)**:
   - self-run 모드의 lock 파일 경로가 isolated tempdir 하위에 머무는지 확인. 머문다면 Finding #4는 reject로 종결. 아니라면 `_write_registry`가 boolean 반환하도록 변경하고 caller가 `lock_skill_state` 분기.

3. **후속 정리 (3건)**:
   - `_KNOWN_SUBCOMMANDS` 상수 단일화 (Finding #5)
   - bootstrap helper 추출 및 docstring 명시 (Finding #6)
   - tempdir cleanup hook 별도 PR (Finding #7)