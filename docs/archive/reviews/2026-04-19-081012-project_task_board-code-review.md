# Code Review: project_task_board

> Source: core/project_task_board.py
> Date: 2026-04-19 08:10
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

No Critical findings, but two High-severity issues must be addressed before the next release. Four additional Medium findings can merge with documented risks.

---

### Aggregated Findings (6 total)

#### 1. [ACCEPT] [High] `_LEDGER_CACHE` 글로벌 딕셔너리 — threading Lock 없는 check-then-act race

- **Critic**: `if base not in _LEDGER_CACHE` → `_LEDGER_CACHE[base] = ...` 사이에 두 코루틴이 동시 진입하면 StrategyLedger가 두 번 생성되고, 버려진 인스턴스로 쓰기 시 변경사항 유실
- **Cross**: flagged 안 됨
- **Judgment**: 증거가 명확한 구조적 race. `dynamic_orchestrator.py`가 복수 코루틴에서 `enrich_role_plan`을 동시 호출하는 경로가 실제 존재함. 기존 H1 패턴(asyncio.Lock 없는 shared state 수정)과 동일하며 이미 H1은 수정됐으나 신규 캐시에 미적용. `lineage_ledger.py`도 동일 버그 공유.
- **Action Required**: `_LEDGER_LOCK = threading.Lock()` 추가 후 `get_strategy_ledger` 전체를 `with _LEDGER_LOCK:` 로 감쌈. `lineage_ledger.py` 동일 패턴도 함께 수정.

---

#### 2. [ACCEPT] [High] `_pick_owner_role`이 explicit module의 `name`만 검색 — deliverable 힌트 미사용

- **Critic**: flagged 안 됨
- **Cross**: `enrich_role_plan` 루프에서 explicit module은 `raw_module["name"]`만 `_pick_owner_role()`에 넘김. planner 계약상 `module.name`은 기술 컴포넌트명이므로 deliverable 패턴 기반 lookup이 항상 miss함. workspace ledger에 `game ui -> frontend_dev` 이력이 있어도 `name="UI Main Screen"` 모듈은 해당 힌트를 사용 불가.
- **Judgment**: Cross reviewer가 로컬 재현으로 확인. diff의 `:412` 라인 — `_pick_owner_role(_clean_text(raw_module.get("name")), roles, workspace=workspace)` — 이 변경으로 workspace 전파는 됐으나 검색 텍스트가 여전히 `name`만임. 이번 PR의 핵심 기능(workspace-scoped ledger hint)이 explicit module 경로에서 무효화됨.
- **Action Required**: `:412`에서 검색 텍스트를 `deliverables → summary → name` 우선순위로 구성하거나, 세 필드 concat 문자열을 `_pick_owner_role()`에 전달. 단위 테스트 추가 필수.

---

#### 3. [ACCEPT] [Medium] `owner_role` 미정규화 저장 — display name 기록 시 workspace lookup 무효화

- **Critic**: flagged 안 됨
- **Cross**: `record_role_success/failure`가 `owner_role`를 raw string으로 저장, consumer에서 `safe_id()` 된 `valid_ids`와 raw 비교. `"Finance Dev"`로 기록된 ledger는 workspace lookup 성공해도 즉시 버려지고 fallback 발동. 로컬 재현으로 확인.
- **Judgment**: `strategy_ledger.py:154, 188` 저장/반환 경로와 `project_task_board.py:163` 비교 경로 간 정규화 불일치. 신규 workspace-scoped ledger 기능 전체를 흐리는 bug.
- **Action Required**: `record_role_success/failure`에서 `owner_role = safe_id(owner_role)` 정규화 후 저장. 또는 consumer `:163`에서 `safe_id(ledger_role)`로 비교. 회귀 테스트(display name + snake_case 둘 다) 추가.

---

#### 4. [ACCEPT] [Medium] `_search_seed_episodes` 비공개 함수 외부 직접 import

- **Critic**: `work_item_generator.py:494`에서 `_` prefix 함수를 타 모듈에서 import. 리팩터링 시 묵시적 의존 발생, 실패 시 silent swallow로 가려짐.
- **Cross**: flagged 안 됨
- **Judgment**: `_` prefix 함수의 모듈 외부 import는 Python 관례 위반. `episode_matcher.py` 변경 시 감지 불가. 강한 단독 증거.
- **Action Required**: `episode_matcher.py`에 공개 래퍼 `search_seed_episodes()` 추가 후 import 변경.

---

#### 5. [ACCEPT] [Medium] `_build_episode_hints_section` — `ImportError`/`TypeError`를 `debug` 레벨로 침묵 처리

- **Critic**: `work_item_generator.py:506-508`의 `except Exception`이 `ImportError`까지 흡수. frozen 빌드에서 `episode_matcher` hiddenimport 누락 시 항상 이 경로를 타며 hints가 항상 비어있어도 알 수 없음. Known issue M9 연관.
- **Cross**: flagged 안 됨
- **Judgment**: Critic 지적 타당. `debug` 레벨 로그는 프로덕션에서 기본적으로 보이지 않아 feature 누락 진단 불가.
- **Action Required**: `except ImportError`를 별도 절로 분리하여 `_LOGGER.warning` 처리. 또는 현재 `except Exception` 로그 레벨을 `warning`으로 격상.

---

#### 6. [ACCEPT] [Medium] `workspace=None` 폴백이 CWD 기준 경로 — worker 프로세스에서 잘못된 ledger 참조

- **Critic**: `strategy_ledger.py:249`의 `os.path.abspath(".")`. Worker 프로세스는 CWD가 부모와 다를 수 있어 다른 경로의 ledger 파일 사용. `workspace=None` 기본값이 누락 호출 시 폴백으로 남음.
- **Cross**: flagged 안 됨
- **Judgment**: 기존 code-review.md §2.1 패턴과 동일. 이번 PR에서 `workspace` 전파를 시작했으나 `None` 폴백이 여전히 위험 경로. Critic 단독이지만 기존 known issue와 명확히 연결된 증거.
- **Action Required**: `workspace=None`일 때 `_LOGGER.warning` 로그 추가, 또는 `PROJECT_ROOT` 상수를 폴백으로 사용.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_LEDGER_CACHE` threading race | High | ACCEPT | Critic |
| 2 | explicit module `name`만 검색 — deliverable hint 미사용 | High | ACCEPT | Cross |
| 3 | `owner_role` 미정규화 저장 — workspace lookup 무효화 | Medium | ACCEPT | Cross |
| 4 | `_search_seed_episodes` 비공개 함수 외부 import | Medium | ACCEPT | Critic |
| 5 | `ImportError` silent swallow @ debug 레벨 | Medium | ACCEPT | Critic |
| 6 | `workspace=None` CWD 폴백 — worker 경로 오염 | Medium | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 (High)**: `_LEDGER_LOCK` 추가로 `get_strategy_ledger` race 해소 + `lineage_ledger.py` 동일 패턴 병행 수정
- **즉시 수정 (High)**: `_pick_owner_role` 검색 텍스트를 `deliverables + summary + name` 합산으로 변경, explicit module 경로 단위 테스트 추가
- **병행 수정 (Medium)**: `record_role_success/failure`에서 `safe_id()` 정규화 저장 + 회귀 테스트
- **후속 수정 (Medium)**: `episode_matcher`에 공개 래퍼 추출, `ImportError` 로그 레벨 `warning`으로 격상
- **후속 수정 (Medium)**: `workspace=None` 폴백 경고 로그 또는 `PROJECT_ROOT` 상수 사용