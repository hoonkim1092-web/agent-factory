# Optional-ID 정규화 — 설계문서

- 작성일: 2026-05-19
- work-item: `optional-id-normalization` (단일 work-item, Option a — 구조-완전)
- 라인-레벨 audit: [`2026-05-19-optional-id-normalization-audit.md`](./2026-05-19-optional-id-normalization-audit.md) (510줄, 파일별 A/B/C 표)
- 본 문서: audit를 검증·정정한 **확정 분류** + 헬퍼 spec + 마이그레이션 범위 + 테스트 계획

---

## 1. 문제 / 근본 원인

`core/utils.py:60` `safe_id()`:

```python
def safe_id(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return (t[:60] if t else "skill")     # ← 빈/None/공백 입력 → "skill"
```

마지막 줄의 `"skill"` fallback은 **skill-id 생성용**(빈 이름의 스킬을 mint할 때 디렉토리명이 필요). 그러나 `safe_id()`는 task_id·owner_role·to_role·dependency key·mailbox key·capability id 등 **optional identifier 정규화**에도 광범위하게 쓰인다.

optional id가 비었을 때 `safe_id(x)` → `"skill"`(truthy·비공백) 이 되어:
- `if not x:` truthy 가드가 **영구히 죽고**(dead guard),
- 변수 equality 비교에서 `"skill" == "skill"` **false-positive 매칭**이 발생하고,
- persisted identity(보드 task_id, mailbox 수신자, feedback skill_id)가 **가짜 `"skill"`로 오염**된다.

### 로컬 복제본 (동일 버그 형태 — `"skill"` fallback)
- `core/external_skill_source_ids.py:4` `safe_id` — char-loop 구현
- `core/install_candidate_utils.py:6` `safe_id` — char-loop 구현 (위와 동일)
- `core/memory.py:118` `_safe_id` — utils와 동일하나 호출부(line 125)가 `if agent_id` outer 가드 → **버그 미발생, 수정 불필요**

### 이미 안전한 로컬본 (`""` 반환 — 수정 불필요)
- `core/skill_creator.py:98` `_safe_id` (NO fallback)
- `scripts/project_context_git_sync.py:19` `_safe_id` (NO fallback)
- `antigravity_link.py:43` `safe_id(text, fallback="")` (parameterized fallback)
- `core/config_paths.py:7` `_boot_safe_id` (`"default"` fallback — 별도 계약, 본 work-item 밖)
- `web/api/run.py:28` `_safe_id` (`"default"`), `web/api/agents.py:58` `_safe_id` (`"agent"`) — 별도 함수, scope 밖

---

## 2. 헬퍼 spec — `safe_optional_id()`

신규 함수: 빈/None/공백 입력 → `""`, **그 외 입력은 `safe_id`와 비트-동일 출력**.

### 2.1 `core/utils.py` (regex 구현 — utils.safe_id 미러)

```python
def safe_optional_id(text: str) -> str:
    """safe_id 와 동일하나 빈/None/공백 입력에 "skill" 대신 "" 를 반환한다.
    optional identifier(task_id, owner_role 등) 정규화 전용."""
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t[:60]
```

`safe_id`의 본문과 마지막 줄만 다르다 (`t[:60] if t else "skill"` → `t[:60]`).

### 2.2 `core/external_skill_source_ids.py` (char-loop 구현 — 로컬 safe_id 미러)

```python
def safe_optional_id(text: str) -> str:
    value = (text or "").strip().lower()
    chars = []
    for ch in value:
        if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "_":
            chars.append(ch)
        else:
            chars.append("_")
    normalized = "".join(chars)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")
    return normalized          # 로컬 safe_id 는 [:60] 절단이 없음 — 미러 유지
```

> 주의: 로컬 char-loop `safe_id`는 utils와 달리 `[:60]` 절단이 **없다**. 미러도 절단 없이 둔다 (동작 변화 최소화).

### 2.3 `core/install_candidate_utils.py` — import만 추가

이미 `from core.external_skill_source_ids import legacy_external_source_ids, normalize_external_source_id` 중. 여기에 `safe_optional_id`를 추가한다. **3번째 복제본을 만들지 않는다.**

```python
from core.external_skill_source_ids import (
    legacy_external_source_ids, normalize_external_source_id, safe_optional_id,
)
```

### 2.4 불변 사항
- `safe_id`의 `"skill"` fallback은 **변경하지 않는다** (skill-id 생성 전용으로 계속 유효).
- `core/utils.py:372` `__all__`은 동적(`[name for name in dir() if not name.startswith('_')]`) → `safe_optional_id` 자동 노출. `agent_launcher.py`의 `from core.utils import *`도 자동 수신.

### 2.5 계약 (테스트로 고정)
| 입력 | `safe_id` | `safe_optional_id` |
|------|-----------|--------------------|
| `""` / `None` / `"   "` | `"skill"` | `""` |
| `"Foo Bar"` | `"foo_bar"` | `"foo_bar"` |
| `"a@@b"` | `"a_b"` | `"a_b"` |
| 비-빈 임의 입력 | X | **X와 동일** |

---

## 3. 분류 프레임워크

`safe_id` → `safe_optional_id` 교체의 결과는 **세 가지뿐**이다:
1. **genuine-B** (입력이 비면 `"skill"`이 버그 유발) → 교체 = **버그 수정**
2. **genuine-C** (입력이 구조적으로 항상 non-empty) → 교체 = **출력 동일 no-op**
3. **path-mint** (`safe_id` 결과가 fallback 없이 파일시스템 경로로 join) → 교체 = **경로 깨짐**

→ **C 과포함은 공짜**(no-op), **path-mint 오분류만 위험**. Option (a)는 reachability("빈 값이 실제로 도달하는가" — caller 추적 필요)를 컷 기준으로 쓰지 않는다. 따라서 컷은 단순하다: **path-mint·skill-id 생성이 아니면서 downstream이 빈 값에 민감한 모든 사이트를 교체한다.**

### 분류 규칙

| 범주 | 판정 | 처리 |
|------|------|------|
| **A** (skill-id 생성) | `safe_id` 결과가 skill 디렉토리/파일/registry id. `"skill"` fallback이 의도된 "기본 skill" | `safe_id` **유지** |
| **path-mint** | `os.path.join(...)` / `f"{...}.yaml"` 에 fallback 없이 들어감 | `safe_id` **유지** (교체 시 경로 붕괴) |
| **B** (optional-id) | A·path-mint이 아니고 downstream이 빈 값에 민감 (truthy 가드 / 변수 equality / persisted identity / optional filter / 토큰 corpus) | `safe_optional_id` **교체** |
| **C** (불변) | downstream이 빈 값에 무관 — literal fallback(`or "build"`), f-string 항상 non-empty, guarded comprehension, `== "literal"` 결과동일 비교 | 변경 없음 |

> **required positional 인자도 교체 대상이다.** Python에서 `f("")` 호출은 문법상 유효하므로 "required = 절대 안 비어있음"은 보장이 아니다. required 여부로 컷하면 caller 추적(reachability)이 필요해지고 동일 계약 사이트가 갈린다 (예: `skill_feedback`의 `record_event`/`record_selection`/`summarize_skill`이 모두 `skill_id`를 받는데 가드 유무로 분류가 갈림). Option (a)는 이를 기각 — required든 optional이든 **빈 값-민감 비-path-mint 사이트는 전부 교체**한다. 교체는 최악의 경우 no-op이다. (이 규칙은 2026-05-19 cross-review BLOCK으로 확정 — §4 개정 이력.)

---

## 4. 확정 분류 — audit 대비 델타

audit raw는 **B 117곳**을 표기. 검증 결과 audit 대비 **3건의 정정**(전부 path-mint 제외)이 발생한다. 최종 교체 집합 = **114곳 / 22파일**.

> **개정 이력 (2026-05-19 cross-review)**: 본 문서 초안은 추가로 "required positional → C" 규칙으로 6곳(`bootstrap_roles:105`, `skill_retrieval_engine:153`, `skill_feedback:93·121·195·196`)을 제외했다. cross-review가 이 규칙의 비일관성을 **BLOCK**으로 지적 — `skill_feedback:93`은 audit firm-B인데 제외됐고, 동일 계약(`skill_id`를 받는) `record_selection`/`summarize_skill`과 분류가 갈렸다. → §3 규칙에서 "required→C" carve-out 제거, 6곳 전부 B로 환원 (108 → 114). path-mint 제외 3건(§4.3)은 cross-review가 코드로 검증·확정(finding #3·#4).

### 4.1 A 분류 — audit 17곳 (메모리 "15"는 오집계 → 17로 정정)

audit가 A로 표기한 17곳을 실제 코드로 확인: 전부 skill-id 도메인 — `safe_id` 결과가 skill 디렉토리/파일/registry id로 쓰이며 `"skill"` fallback이 "기본 skill"이라는 의도된 계약. `safe_id` 유지 확정.

`utils.py` 158·233·319 · `agent_runner.py` 648·719·723 · `builder.py` 320 · `capability_intent.py` 33 · `external_skill_sources.py` 150 · `external_skill_candidate_importer.py` 196·211 · `registry_manager.py` 184·379 · `skill_registry.py` 545 · `skill_eval_harness.py` 693 · `skill_procurer.py` 182·381.

이 중 `builder.py:320`은 `os.path.join(SKILLS_DIR, safe_id(skill_name))` 후 `os.makedirs`+`skill.py` 작성 → path-mint이기도 하다 (교체 시 `SKILLS_DIR` 루트에 `skill.py`를 씀). A·path-mint 양쪽 근거로 `safe_id` 유지.

### 4.2 B → C 정정 — 없음 (초안 6건 환원)

초안의 "required positional → C" 6건 제외(`bootstrap_roles:105`, `skill_retrieval_engine:153`, `skill_feedback:93·121·195·196`)는 §3 규칙 개정으로 **철회**됐다. 6곳 모두 **B (교체)**:
- 전부 비-path-mint (persisted identity / equality filter — 경로 아님)
- caller가 실제로 빈 값을 안 넘기면 교체는 no-op, 넘기면 버그 수정 ("C 과포함은 공짜")
- `skill_feedback:93`은 audit가 **firm-B**로 분류한 것 — 초안이 근거 없이 번복했던 것을 원복

> audit의 firm-B/doubt 라벨 자체에 비일관(`from_stage`195=doubt vs `to_stage`196=firm — 동일 계약)이 있었으나, §3 개정 규칙상 **비-path-mint B는 라벨 무관 전부 교체**되므로 firm/doubt 구분은 더 이상 분류에 영향이 없다.

### 4.3 path-mint 제외 (3건) — cross-review 2026-05-19 검증 완료

| 사이트 | audit | 정정 | 근거 |
|--------|-------|------|------|
| `run_factory_cli.py:194` | B(doubt) | **제외** | `os.path.join(projects_root, safe_id(args.project))` — fallback 없는 workspace 경로 mint. 교체 시 빈 입력→`projects_root` 자체가 workspace. 추가로 `if args.project:` (line 189) 상류 가드로 빈 값 도달 불가 |
| `manager.py:37` | B(doubt) | **제외** | `f"{safe_id(role_spec)}.yaml"` — fallback 없는 agent 파일명 mint. 교체 시 `skill.yaml`→`.yaml`(숨김 파일) = 개선 아님 |
| `manager.py:45` | B(doubt) | **제외** | 37과 동일 |

> cross-review가 세 사이트의 코드를 직접 열어 path-mint 판정을 확인 (finding #3·#4 REJECTED = 설계문서 맞음). `manager.py:37/45`의 정답은 상류 `role_spec` 정규화 — **별도 work-item**. 본 work-item 밖.

### 4.4 doubt 확정

audit가 B(doubt)로 표시한 16곳은 §3 개정 규칙상 전부 **B** — 비-path-mint이고 빈 값-민감 downstream(persisted identity / 변수 equality / 토큰 corpus / optional filter)을 가진다. 정정 없음.

라인-레벨 좌표·사이트별 계약(`.get()`/`or ""`/iteration/공백-only `.strip()` 등)은 **audit 문서의 rationale 열이 권위 소스**. 본 §4.4는 doubt 해소만 명시하며 전체 B 목록을 열거하지 않는다.

참고:
- `researcher.py:112`는 `[safe_id(item.get("id","")), safe_id(item.get("name",""))]` 2개 호출 — audit는 `id` 호출을 도달성 기반 C로 봤으나 Option (a)는 도달성 컷 기각 → **라인 전체(2개 호출) 교체**.
- `skill_feedback.py` audit-B 10곳 = 93·121·195·196·226·247·260·285·355·356 — §5 집계가 10건 전부 반영.

### 4.5 최종 카운트

```
audit B-marked              117
 − path-mint 제외 (§4.3)      -3
 ─────────────────────────────
 최종 교체 집합              114  (22 파일)
```

> 메모리의 "예상 ~75~95"는 reachability 기반 축소를 가정한 추정. Option (a)가 reachability 컷을 기각 → 실제 구조-완전 집합은 **114**로 더 크다. 정상이며, C 과포함은 공짜(no-op)이므로 위험 없음.

---

## 5. 마이그레이션 범위 — 파일별

라인-레벨 좌표는 audit 문서가 권위 소스. 아래는 파일별 교체 건수 (§4 정정 반영).

| 파일 | 교체 | safe_id 출처 |
|------|------|--------------|
| `core/agent_specializer.py` | 5 | `core.utils` |
| `core/bootstrap_roles.py` | 7 | `core.utils` |
| `core/agent_runner.py` | 5 | `core.utils` |
| `core/builder.py` | 1 | `core.utils` |
| `core/dynamic_orchestrator.py` | 6 | `core.utils` |
| `core/capability_intent.py` | 5 | `core.utils` |
| `core/external_skill_source_ids.py` | 1 | **로컬** (line 52) |
| `core/external_skill_sources.py` | 6 | `core.utils` |
| `core/external_skill_candidate_importer.py` | 3 | `core.utils` |
| `core/install_candidate_utils.py` | 6 | **로컬 → import 전환** |
| `core/interactive_chat.py` | 1 | `core.utils` |
| `core/project_task_board.py` | 15 | `core.utils` |
| `core/registry_manager.py` | 5 | `core.utils` |
| `core/researcher.py` | 8 | `core.utils` |
| `core/project_mailbox.py` | 8 | `core.utils` |
| `core/skill_spec_synthesizer.py` | 2 | `core.utils` |
| `core/skill_promotion.py` | 3 | `core.utils` |
| `core/skill_retrieval_engine.py` | 7 | `core.utils` |
| `core/skill_feedback.py` | 10 | `core.utils` |
| `core/skill_procurer.py` | 3 | `core.utils` |
| `core/work_item_parser.py` | 5 | `core.utils` |
| `agent_launcher.py` | 2 | `from core.utils import *` |
| **합계** | **114** | |

### 헬퍼 도입 (3 파일)
- `core/utils.py` — `safe_optional_id` 신규 정의 (§2.1)
- `core/external_skill_source_ids.py` — `safe_optional_id` 신규 정의 (§2.2) + line 52 자체 교체
- `core/install_candidate_utils.py` — import 추가 (§2.3) + 6곳 교체

### import 라인 변경
`core.utils`에서 `safe_id`를 명시 import하는 파일은 `safe_optional_id`도 추가 import. `import *` 파일(`agent_launcher.py`)은 변경 불필요. 각 파일에서 **A 사이트는 `safe_id` 유지** → 두 함수가 한 파일에 공존.

---

## 6. 테스트 계획

> Karpathy 원칙: "버그 수정 → 버그 재현 테스트 작성 후 통과".

### 6.1 헬퍼 단위 테스트 — `tests/test_safe_optional_id.py` (신규)
- `safe_optional_id("")`/`(None)`/`("   ")` → `""`
- `safe_optional_id("Foo Bar")` → `"foo_bar"`, 비-빈 임의 입력에서 `safe_id`와 동일
- `core.utils` 버전 ↔ `core.external_skill_source_ids` 버전: 비-빈 입력에서 동일 출력 (단, `[:60]` 절단 차이는 60자 초과 입력에서만)

### 6.2 CALIB 회귀 테스트 (재현 → 통과)
실제 코드 확인으로 재현된 결함 클러스터. 각각 "수정 전 fail → 수정 후 pass":

| # | 사이트 | 재현 | 기대 (수정 후) |
|---|--------|------|----------------|
| C1 | `project_mailbox.py:152/153` | `send(..., to_role="")` | `if not recipient: raise` 발화 (현재: `"skill"` 메일박스로 무음 발송) |
| C2 | `install_candidate_utils.py:24/68/85` | `infer_source_id_from_candidate_key("","")` 등 | 빈 입력 → `""`/`None` 반환 (현재: `"skill"` 처리) |
| C3 | `project_task_board.py:748/755` `_dependency_satisfied` | 빈 dependency | `if not dependency: return True` 발화 = "충족" (현재: `"skill"`로 미발화) |
| C4 | `dynamic_orchestrator.py:186/198` | task_id 누락 board task | completed-key 집합에 `"skill"` 미진입 |
| C5 | `work_item_parser.py:133` | 공백-only 제목 work-item | task_id `""` (현재: `"skill"`) |

### 6.3 회귀 안전망
- 기존 `tests/` 전체 통과 (특히 skill registry / mailbox / task board 관련)
- A 사이트 미변경 확인: `builder.py:320` 등 skill-mint 경로 회귀 테스트 통과

---

## 7. 배포 동등성 (CLAUDE.md 파이프라인 규칙)

production 호출 경로 확인 — `safe_optional_id`가 테스트 픽스처가 아닌 실제 실행 경로까지 도달하는지:
- `agent_launcher.py` (184·605) — production CLI 진입점. `from core.utils import *` → `safe_optional_id` 자동 수신. 별도 배선 불필요.
- `project_pipeline.py` — audit 결과 교체 사이트 **0개** (전부 C — `role_id`가 `_materialize_roles`의 `or "role"`로 구조적 non-empty). 변경 없음.
- `core/*.py` 22개 파일은 전부 라이브러리 모듈 — caller가 production 경로에서 import. 헬퍼는 순수 함수, 별도 파라미터 배선 없음 → 배포/개발 환경 동작 동일.
- `af.spec` `hiddenimports` — 신규 `.py` 파일 없음(기존 파일에 함수 추가) → 변경 불필요.

---

## 8. 구현 순서

```
1. 헬퍼 정의 2곳 (utils.py, external_skill_source_ids.py) + install_candidate_utils.py import
   → 검증: tests/test_safe_optional_id.py 작성·통과 (§6.1)
2. CALIB 재현 테스트 5건 작성 (현재 fail 확인)
   → 검증: 5건 모두 fail (버그 재현 확인)
3. 108 사이트 교체 (파일별, A 사이트는 safe_id 유지)
   → 검증: CALIB 5건 pass + 헬퍼 테스트 pass
4. 전체 회귀 — pytest tests/
   → 검증: 기존 테스트 0 regression
5. 3-Tier 코드리뷰 (af-critic → af-cross-review → af-test-runner)
   → Master_Blueprint.md 동기화 → 단일 커밋
```

- **브랜치**: 현재 `main`. 첫 커밋 전 feature 브랜치 분기. 미커밋 캐리오버(`.claude/settings.json`, `projects/agent_factory/*`)와 섞지 않는다.
- **단일 PR**: 108 사이트는 기계적이나 sed 일괄 금지 — 같은 파일에 A 사이트(`safe_id` 유지)가 공존하므로 사이트별 수동 교체.

---

## 9. 미해소 / 설계 결정

- **stash WIP** (`stash@{0}: P1C-rv-safe_id-wip`): root cause의 일부 조각. `safe_optional_id` 도입 후 `_resolve_task_meta`의 raw-empty 가드는 **불필요**(헬퍼가 처리). `_lilith_decide_next`의 board-task_id 화이트리스트는 *다른* 문제(LLM이 빈 값 아닌 *틀린* non-empty task_id를 echo) → **유지**. 이중 구현 금지 — stash는 본 work-item 완료 후 drop.
- **`manager.py:37/45`** (path-mint 제외): 상류 `role_spec` 정규화가 정답 — 별도 work-item으로 분리.
- **`install_candidate_utils.py` `canonical_install_candidate_key` 43·44행**: audit-C로 `safe_id` 유지. line 40(`sid`) 교체 후 외부 caller가 `skill_id`·`raw_key`를 모두 빈 값으로 넘기면 line 43이 `safe_id("")="skill"`을 mint할 수 있으나, 같은 모듈 `normalize_install_candidate_item`의 line 68·82·85 `if not skill_id: return None` 가드(교체로 live화)가 빈 `skill_id`를 차단 → 모듈 계약 내 도달 불가. 외부 all-empty 호출은 계약 위반으로 scope 밖. (cross-review 1차 라운드 지적 — 검증 후 §9에 기록.)
- **`memory.py:118` `_safe_id`**: 호출부가 outer 가드라 버그 미발생 → 본 work-item에서 손대지 않음 (Karpathy surgical — 깨지지 않은 것 미수정).
- **`config_paths.py:7` `_boot_safe_id`** (`"default"` fallback): 별도 계약, scope 밖.
- **A 사이트 16곳** (`builder.py:320` 제외): 교체해도 no-op이나 이득 없음 → audit대로 `safe_id` 유지. 향후 "전면 정규화"를 원하면 별도 검토.
