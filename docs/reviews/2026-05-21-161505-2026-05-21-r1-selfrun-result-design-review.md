# Design Review: 2026-05-21-r1-selfrun-result

> Source: docs/dogfooding/2026-05-21-r1-selfrun-result.md
> Date: 2026-05-21 16:15
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

2개의 Critical 발견(허위 docstring 삽입, scope guard 부재)이 양 리뷰어에서 동시 확인됨. `r1-selfrun-exp` 브랜치를 현재 상태로 머지하면 `core/utils.py` 공개 docstring이 사실과 정반대인 주석으로 오염됨. R1 "증명됨" 선언도 후속 R7/R8/R9 의사결정 근거가 되므로 정정 후 재실행 필요.

### Aggregated Findings (10 total — ACCEPT 8 / REJECT 2)

#### 1. [ACCEPT] [Critical] 삽입된 주석이 의미적으로 거짓 — `safe_optional_id(None)`은 `""` 반환
- **Critic**: L21-22 태스크 입력의 문자열이 `core/utils.py:67-71` 동작과 정반대. `"skill"` 반환은 `safe_id()`의 동작. (Finding #1)
- **Cross**: `core/utils.py:53` `safe_optional_id(None) -> ""`, `core/utils.py:46` `safe_id("") -> "skill"`. (Finding #1)
- **Judgment**: 양 리뷰어 + 코드 직접 확인 일치. AF가 "정확히 1줄을 지시대로 삽입"한 사실이 곧 공개 docstring을 거짓으로 오염시킨 결과. 이는 R1 PASS의 본질을 무효화.
- **Action Required**: (a) 태스크 텍스트를 `safe_id(None) -> "skill"` 또는 `safe_optional_id(None) -> ""`로 정정, (b) R1 재실행, (c) 평가 기준에 "삽입 내용 ↔ 실제 동작 일치 여부" 항목 추가, (d) 현 브랜치 **머지 금지** 명시.

#### 2. [ACCEPT] [Critical] R3 "scope guard"는 가드가 아닌 사후 보고 — 격리 누수까지 포함
- **Critic**: L17 "실행 후 `git diff --name-only` 수동 확인"은 가드가 아닌 회고. 1회 trial의 우연한 결과로 PASS 셈. (Finding #2)
- **Cross**: `git diff --name-only`는 tracked working-tree만 측정 — untracked, 레포 외부 write, isolated runtime root 미관측. `agent_launcher.py:49`, `core/agent_runner.py:860,953` 참조. (Finding #2)
- **Judgment**: 양측 모두 "측정 자체가 부실"을 다른 각도로 입증. Critic은 timing(사후), Cross는 coverage(범위 누락). R3 "PASS" 라벨의 근거 자체가 성립 안 함.
- **Action Required**: L73-80 검증 표의 R3 행을 "미구현 — 1회 우연히 1파일만 modified" 또는 FAIL로 정정. R3 정의를 `git status --porcelain --untracked-files=all` + `skills/registry.yaml`/`skills/workflow_registry.yaml`/`skill-lock.yaml`/isolated runtime root 스냅샷으로 확장. multi-file 시나리오(L92) 진입 전 R3 enforce 선행 조건 명시.

#### 3. [ACCEPT] [High] 격리 계약 부분 위반 + `AF_DISABLE_REGISTRY_WRITE` 검증 범위 미정의
- **Critic**: 마찰 #3 — isolated PROJECT_ROOT인데 skills/ 탐색이 `BASE_DIR`(현재 worktree) 기반으로 동작해 57개 스킬 로드. 격리 계약이 runtime_workspace에만 적용. (Finding #3)
- **Cross**: `core/registry_manager.py:50,402`는 write gated되지만 `register_built()`가 `lock_skill_state()`를 호출(`L399`) → `SKILL_LOCK_PATH` write는 isolated PROJECT_ROOT 활성일 때만 안전. (Finding #3)
- **Judgment**: Critic은 read leak, Cross는 write surface 미정의. 둘 다 "AF_DISABLE_REGISTRY_WRITE=1 PASS" 라벨이 무엇을 보장하는지 명확하지 않음을 지적. 격리 누수가 관측된 실험을 PASS로 분류한 것은 결론과 증거 부정합.
- **Action Required**: 검증 표에 "격리 (skills/ 탐색)" 행 추가 → **FAIL**. invariant 명시: "AF_DISABLE_REGISTRY_WRITE는 global registry/workflow write만 차단; project-scoped write(lock/dashboard/trace)는 isolated AGENT_PROJECT_ROOT와 짝일 때만 안전." multi-file 시나리오 진입 전 skills/ 탐색 경로 격리 패치를 P0 차단 조건으로 명시.

#### 4. [ACCEPT] [High] 사후 검증 단계 전무 — `py_compile`/import/pytest 없음
- **Critic**: L55-61 파이프라인 관측 표에 syntactic validity 검증 없음. trivial 1줄이라 우연히 안전했을 뿐. (Finding #4)
- **Cross**: not flagged
- **Judgment**: Cross는 별도로 안 잡았으나 Critic의 evidence(표 자체에서 항목 부재 확인)가 강함. `.py` 수정 능력을 증명하려면 "수정 후 해당 모듈이 로드 가능"이 최소 검증. 본 표에 그 라인이 비어 있는 것이 직접 증거.
- **Action Required**: 실험 후 자동 실행 + 결과를 표에 기록: `python -m py_compile <수정파일>`, 해당 파일 import하는 가장 가까운 테스트 1개, review-gate Tier 1(af-test-runner). 3개 PASS여야 R1 PASS 인정.

#### 5. [ACCEPT] [High] 재현성 깨짐 — worktree 트래킹/산출물 보존 없음
- **Critic**: `git worktree list`에 `r1-selfrun-exp` 미등록. stdout 전체/FSA trace/`runs/<run_id>/` 경로/invocation 명령 미보존. (Finding #5)
- **Cross**: not flagged
- **Judgment**: Critic의 evidence(git worktree 명령 결과)가 검증 가능. R1을 "AF의 핵심 명제"로 명명한 비중 대비 증거 보존 빈약. 단독 출처지만 객관적 사실.
- **Action Required**: `docs/dogfooding/2026-05-21-r1-selfrun-result/` 하위 폴더에 stdout 전체, FSA trace JSON, runs 디렉토리, 정확한 `agent_launcher.py` invocation 1줄 보존 + 본 문서에서 링크.

#### 6. [ACCEPT] [Medium] n=1 trial에서 "증명됨" 과대주장 + promotion threshold 미정의
- **Critic**: L76 "증명됨" / L86 "핵심 명제 충족"은 1줄 주석 1회로 과적합. L96에서 자체 약화 → 내부 모순. (Finding #6)
- **Cross**: HOLD — promotion threshold(파일 수, semantic 변경 vs 주석, 필요 테스트, runtime write 허용, provider fallback 예산, rollback 기대) 미정의. (Finding #7)
- **Judgment**: Critic의 "과대주장"과 Cross의 "promotion 기준 부재"는 같은 결함의 양면. 둘을 합치면 HOLD가 ACCEPT로 격상.
- **Action Required**: L72 표 제목 "1회 trivial trial 결과"로 한정, L86 "trivial case 1회 PASS"로 다운그레이드. "핵심 명제 충족" 라벨은 (a) syntactic + semantic 변경, (b) multi-file, (c) R3 enforce 작동 3 케이스 PASS 후 부여. R7/R8/R9 진입 기준 표 추가.

#### 7. [ACCEPT] [Medium] R4 권고가 CLI 인증과 API key를 혼동
- **Critic**: gemini_cli 3초 낭비는 R1과 무관한 환경 결함. `GOOGLE_API_KEY` 없는 채로 폴백된 사실을 일반화하면 R4 추적 잠식. (Finding #7)
- **Cross**: `GOOGLE_API_KEY` 부재만으로 gemini_cli 스킵은 잘못 — CLI auth와 SDK API key는 별개 계약. `core/engine_auth.py:122`, `core/providers/cli.py:402`. (Finding #4)
- **Judgment**: Critic은 환경 노이즈 격리, Cross는 권고 자체의 기술적 오류 — 보완 관계. Cross의 코드 evidence가 결정적.
- **Action Required**: L58 row를 "환경 결함으로 인한 noise — R1 평가에서 제외"로 라벨. L90 R4 fix 권고를 "CLI preflight(auth-required/command-unavailable/timeout) 기반 reorder/skip"로 정정. 실험 절차에 `AF_PROVIDER_PRIORITY=claude_cli` 명시로 R1·R4 분리.

#### 8. [ACCEPT] [Medium] Review-gate 실행 결과 미기록
- **Critic**: `core/*.py` 변경은 Tier 2~3 — af-critic → af-cross-review → af-test-runner 3-tier 발화 여부, `AF_SKIP_REVIEW_GATE` 사용 여부 미명시. (Finding #8)
- **Cross**: not flagged
- **Judgment**: Critic 단독이나 CLAUDE.md "Review-Gate 규칙"의 직접적 dogfooding 케이스. 본 결과를 정식 코드 라이프사이클에 포함시킬 수 있는지 판단 불가.
- **Action Required**: 별도 섹션 "Review-gate 실행 결과" 추가 — (a) commit 발생 여부, (b) 게이트 발화 여부, (c) 우회 시 hook_events.log 라인 인용.

#### 9. [REJECT] [Low] `af.spec` hiddenimports 갱신 필요
- **Source**: Cross (Finding #5, 본인 REJECT)
- **Original Finding**: `core/*.py` 변경이므로 frozen-build 갱신 필요할 수 있음.
- **Rejection Reason**: 본 실험은 docstring/comment-only 편집, 신규 module/import 없음. CLAUDE.md 정책은 "새 `core/*.py` 파일"에만 적용. Cross 본인이 REJECT 처리한 결정에 동의.

#### 10. [REJECT] [Low] `AF_CONTROL_PLANE_PROVIDERS` 아키텍처 격차가 본 결과를 차단
- **Source**: Cross (Finding #6, 본인 REJECT)
- **Original Finding**: provider-policy 충돌 가능성.
- **Rejection Reason**: `core/control_plane_llm.py:52`에서 이미 `AF_CONTROL_PLANE_PROVIDERS` 읽힘. R1 관측은 worker/ad-hoc runner 경로로 별개. Cross 본인 REJECT에 동의.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 삽입 주석이 의미적으로 거짓 | Critical | ACCEPT | Both |
| 2 | R3 scope guard 부재 + 측정 범위 누락 | Critical | ACCEPT | Both |
| 3 | 격리 계약 부분 위반 + write surface 미정의 | High | ACCEPT | Both (다른 각도) |
| 4 | `py_compile`/import/pytest 검증 없음 | High | ACCEPT | Critic |
| 5 | 재현성 — worktree/artifact 미보존 | High | ACCEPT | Critic |
| 6 | n=1 "증명됨" 과대주장 + promotion threshold 미정의 | Medium | ACCEPT | Both |
| 7 | R4 권고가 CLI auth와 API key 혼동 | Medium | ACCEPT | Both |
| 8 | Review-gate 실행 결과 미기록 | Medium | ACCEPT | Critic |
| 9 | `af.spec` 갱신 필요 | Low | REJECT | Cross (self) |
| 10 | `AF_CONTROL_PLANE_PROVIDERS` 격차 | Low | REJECT | Cross (self) |

### Recommendations

구현/머지 전 필수:
1. **태스크 텍스트 정정 후 R1 재실행** — `safe_id(None) -> "skill"` 또는 `safe_optional_id(None) -> ""`. 현재 브랜치는 머지 금지.
2. **검증 표 PASS 라벨 정정** — R3, 격리, "AF가 .py 수정 가능"의 3 항목을 PARTIAL/FAIL/"1회 trivial PASS"로 다운그레이드.
3. **사후 검증 자동화** — `py_compile` + 인접 테스트 + Tier 1 게이트를 R1 PASS 정의에 포함.
4. **R3 정의 확장** — `git status --porcelain --untracked-files=all` + 전역 파일 스냅샷(registry/workflow/skill-lock) + isolated runtime root.
5. **R4 권고 재작성** — CLI preflight 기반 reorder/skip. API key 검사로 대체 금지.
6. **Promotion threshold 표 신설** — (파일 수, semantic 여부, 테스트 요구, runtime write 허용, fallback 예산, rollback). R7/R8/R9 진입 기준 명문화.
7. **재현 가능한 artifact 패키지** — `docs/dogfooding/2026-05-21-r1-selfrun-result/` 하위 폴더에 stdout/trace/runs/invocation 보존.
8. **Review-gate 섹션 추가** — commit/게이트/우회 기록.