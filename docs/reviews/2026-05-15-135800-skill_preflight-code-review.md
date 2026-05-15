# Code Review: skill_preflight

> Source: core/skill_preflight.py
> Date: 2026-05-15 13:58
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

High/Medium findings exist but no Critical. Pair fix (`AF_DISABLE_REGISTRY_WRITE` ↔ `_maybe_isolate_project_root_for_self_run`) works as intended; defects are around env-var semantics, scope/docstring drift, observability, and test coverage. Mergeable with documented follow-ups.

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] env-var truthy 평가가 AF 컨벤션을 따르지 않음
- **Critic**: `os.environ.get("AF_DISABLE_REGISTRY_WRITE")` 은 빈 문자열만 falsy. `=0`/`=false` 도 disable로 해석. AF 다른 곳은 `== "1"` 또는 `.lower() not in ("0","false","no")` 컨벤션 사용 (work_item_generator.py:958, approval_gate.py:390, review_gate.py:176, dynamic_orchestrator.py:844).
- **Cross**: not flagged
- **Judgment**: Critic만 지적했으나 증거 강함 — 동일 PR 페어 사이트(`core/registry_manager.py:49`)도 같은 패턴. AF 코드베이스 4곳 인용으로 컨벤션 위반 확정.
- **Action Required**: 페어 사이트 두 곳을 `if os.environ.get("AF_DISABLE_REGISTRY_WRITE", "").strip().lower() in {"1","true","yes","on"}:` 로 정렬. 권장: `core/utils.py` 에 `env_flag(name, default=False)` 헬퍼 1회 추가.

#### 2. [ACCEPT] [Medium] docstring "글로벌 only" 약속과 실제 "글로벌+프로젝트 로컬" 차단 불일치
- **Critic**: docstring(L254-255)은 "글로벌 registry write 만 skip" 라고 명시했지만, early-return 은 후속 `[SKILLS_DIR, PROJECT_SKILLS_DIR]` 후보를 가르지 않고 둘 다 막음.
- **Cross**: 동일 — early-return 이 `SKILLS_DIR`/`PROJECT_SKILLS_DIR` 구분 전에 발생. `agent_launcher.py:25-26` 주석도 "글로벌 write 보호"로 frame.
- **Judgment**: 두 리뷰어 동일 위치, 동일 문제 (HIGHER severity = Medium 유지). 의도 모호성이 silent 미적용 회귀 위험.
- **Action Required**: 결정 — (a) docstring 을 "모든 registry write skip" 으로 정정 (단순, 현재 동작 유지, 권장), 또는 (b) candidate 루프 내부에서 `registry_path == SKILLS_DIR/..` 일 때만 skip 하도록 분기. 미결 시 Finding 3·5 가 추가로 트리거됨.

#### 3. [ACCEPT] [Medium] env-var setdefault 가 모든 child subprocess 에 상속
- **Critic**: `agent_launcher.py:49` `os.environ.setdefault(...)` 은 이후 spawn 되는 `agent_worker.py` 등 모든 subprocess 에 자동 전파. Finding 2 의 (b) 의도(글로벌만 보호)면 isolated project-local write 까지 over-block.
- **Cross**: not flagged
- **Judgment**: Finding 2 결정에 종속. (a) 채택 시 의도된 동작이므로 docstring 에만 명시. (b) 채택 시 env var 이름 분리 (`AF_DISABLE_GLOBAL_REGISTRY_WRITE`) 필요. 증거: `os.environ` 표준 동작 + AF subprocess spawn 패턴.
- **Action Required**: Finding 2 결정 후 일치시킴. (a) → 주석 1줄 추가. (b) → env var 이름 변경 + child 차단 분리.

#### 4. [ACCEPT] [Medium] Silent skip — 진단 신호 없음
- **Critic**: `core/skill_preflight.py:258-259` 새 분기만 `self.verbose` 활용 안 함. 본문은 "matched/not found/failed" 세 분기 모두 verbose print 존재. ad-hoc self-run 디버깅 시 hook log 흔적 없음. `core/registry_manager.py:45-50` 페어 사이트 동일.
- **Cross**: not flagged
- **Judgment**: Critic만 지적했으나 증거 강함 — 같은 파일 기존 패턴(verbose print) 대비 일관성 명확 깨짐. 운영·디버깅 관점에서 실질 부담.
- **Action Required**: `if self.verbose: print(f"[Preflight] Registry write skipped (AF_DISABLE_REGISTRY_WRITE set): {result.skill_id}")` 1줄 추가. `registry_manager.py` 쪽은 logger 부재 시 최소 주석으로 의도 강화.

#### 5. [ACCEPT] [Medium] 새 가드에 직접 회귀 테스트 부재
- **Critic**: not flagged
- **Cross**: `tests/test_phase5_context_fork_preflight.py:144-284` 는 `evaluate()` 결과만 검증, `_update_registry_status()` 새 가드 미커버. `tests/test_agent_launcher_cli_dispatch.py:95-141` 는 env var set 자체만 검증, preflight 가 respect 하는지는 미검증.
- **Judgment**: Cross가 단독 지적, verification run (`33 passed`)로 기존 테스트 무회귀는 확인됐으나 가드 자체의 regression test gap 명확. AF 코드리뷰 정책상 새 behavior gate 는 회귀 테스트 동반 의무.
- **Action Required**: temp `registry.yaml` 생성 + `core.config_paths.SKILLS_DIR/PROJECT_SKILLS_DIR` monkeypatch + `AF_DISABLE_REGISTRY_WRITE=1` 설정 → `_update_registry_status()` 호출 → registry 무변화 assert. 환경변수 미설정 경로도 함께 검증.

#### 6. [HOLD] [Low] CLI 진입 분류가 좁음 — `argv[0] in {"project"}` 만 예외
- **Critic**: `agent_launcher.py:41` 페어 사이트가 `chat`, `daemon`, `--version`, `--help` 등 합법 서브커맨드를 ad-hoc 으로 분류. 본 diff 외부.
- **Cross**: 부분적 — Finding 3 (REJECT) 에서 `agent_launcher.py:52-53` 만 env var set, `run_factory_cli.py:104-108` `cli_main()` 직접 호출은 영향 없음으로 검증.
- **Judgment**: Critic이 본 PR 직접 대상 아님으로 명시. Cross 가 현재 CLI 분류 범위에서 회귀 없음을 verification 으로 확인 — 본 PR scope 외부 follow-up.
- **Question for Author**: 별도 추적 PR 로 분리할지, 본 PR 의 후속 패치에 포함할지?

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | env-var truthy 평가 컨벤션 위반 | High | ACCEPT | Critic |
| 2 | docstring vs 실제 차단 범위 불일치 | Medium | ACCEPT | Both |
| 3 | setdefault subprocess 상속 over-block | Medium | ACCEPT | Critic |
| 4 | Silent skip — verbose 미활용 | Medium | ACCEPT | Critic |
| 5 | 새 가드 회귀 테스트 부재 | Medium | ACCEPT | Cross |
| 6 | CLI 진입 분류 좁음 (외부) | Low | HOLD | Critic |

### Recommendations

1. **Finding 2 결정 먼저** — (a) "모든 write skip" docstring 정정 권장(단순). (b) 채택 시 env var 이름 분리 + candidate-loop 내부 분기 필요.
2. **Finding 1 & 2 묶음 패치** — env_flag 헬퍼 또는 explicit `in {"1","true","yes","on"}` 패턴으로 페어 사이트 2곳 정렬 + docstring 일치.
3. **Finding 4** — `self.verbose` 한 줄 추가 (저비용·고가치).
4. **Finding 5** — `tests/test_phase5_context_fork_preflight.py` 에 새 가드 regression test 추가 (set/unset 양쪽).
5. **Finding 6** — 별도 PR 추적, 본 머지 차단 아님.
6. 정책 참고: `docs/code_review/code-review.md` §3.2 H6 (env-var 채택 시 truthy 의미·다른 분기 영향 동시 점검) 교훈 재반복 — env_flag 헬퍼화로 근본 회피 권장.