# AF 제품 출력 격리 — ad-hoc 새 제품 생성 경로 (`os.getcwd()` 오염 보강)

**날짜**: 2026-06-18
**상태**: Superseded — 2026-06-22 in-place 복원으로 개정 (아래 §0 개정 노트 참조)
**작성자**: Claude Opus 4.8
**연관 설계**: `docs/2026-06-18-user-perspective-qa-pipeline-design.md` (QA 파이프라인 — 이 격리의 **소비자**: 리포트·seam 산출물이 여기서 정해진 위치에 떨어짐)

---

## §0 개정 노트 (2026-06-22, 구현 시 방향 전환 — 본문보다 우선)

> ⚠️ **본문(§1~)은 "무조건 격리 + fail-closed 차단" 초기 설계다. 실제 구현은 아래대로 정반대로 개정됐다.** 본문을 그대로 재구현하지 말 것.

**왜 바뀌었나**: 본문의 INV-O1(`<cwd>/<slug>/` **무조건** 하위폴더) + fail-closed 가드(`OutputGuardError`)가 *"기존 프로젝트를 그 자리에서 수정·분석"* 이라는 정상 동작을 깨는 회귀를 냈다. AF는 ad-hoc 경로에서 사용자 cwd의 기존 프로젝트를 in-place로 다뤄야 한다.

**개정된 실제 동작** (`core/output_paths.py:resolve_product_output_dir`):
1. `--workspace`/`-w` explicit 지정 → 최우선 (INV-O5). 설계의 신규 `--out`은 **미채택**(기존 `--workspace`와 중복이라 재사용).
2. cwd가 AF 소스 repo(`BASE_DIR`) 하위 **AND** `projects/` 밖 → `<BASE_DIR>/projects/<slug>`로 **graceful 리다이렉트**(INV-O2, 에러 아님 — AF 소스 오염만 격리). `OutputGuardError`(fail-closed) **제거**.
3. 그 외(배포 사용자 일반 폴더·`projects/` 하위) → **cwd in-place** (INV-O3, 기존 프로젝트 수정·분석 의도 보존).

**후속 UX (2026-06-22)**: 대화형 세션에서 비개발자가 저장 폴더를 쉽게 지정하도록 `/output <경로>` 슬래시 명령 추가(`core/interactive_chat.py`, 커밋 `570b3258`) + 시작 배너에 현재 폴더 표시(`482f72c3`).

**근거**: NEXT_STEPS.md "3건 수정 완료" Fix 1 + Master_Blueprint.md §12(2026-06-22 output-isolation 행). 구현·테스트(16+3)·3-Tier 완료.

---

## §1 배경 및 동기

AF에는 제품을 만드는 경로가 두 개다. **한쪽(dogfood)은 격리돼 있고, 다른 쪽(ad-hoc)은 샌다.**

| 경로 | 출력 위치 | 격리 |
|---|---|---|
| **af → af 개발 (dogfood)** | `~/.af-dogfood/<run_id>/worktree` (git worktree) | ✅ 올바름 |
| **af → 새 제품 ("~만들어줘", ad-hoc)** | `os.getcwd()` 직하 | ❌ 격리 없음 |

ad-hoc 경로를 agent-factory repo 루트에서 실행하면 **제품 산출물 + AF 스캐폴딩이 AF 소스에 섞인다.** 배포 사용자에게도 작업 폴더 루트에 `agents/`·`planning/`·`.checkpoint/`가 하위폴더 없이 흩뿌려진다(같은 폴더 재실행 시 충돌).

> **공통 뿌리**: 두 경로 모두 `os.getcwd()` 기본값에서 출발했다. dogfood는 그 위에 worktree + `allow_file_edit=False` 가드를 얹어 막았다(메모리 `project_dogfood_isolation_leak`: `control_plane_llm.py:122 workspace=os.getcwd()`가 stall 복구 시 소스 누수 → RESOLVED 2026-06-03). **ad-hoc은 raw `os.getcwd()`가 그대로 남았다.** 이 설계는 dogfood가 증명한 격리 원칙의 *미적용 케이스 보강*이다(신규 메커니즘 아님).

---

## §2 현재 코드 진단 (grep 확정)

### §2.1 ad-hoc 경로 — 산출물이 cwd 직하로 (`agent_launcher.py:1206-1213`)

```python
AgentFactory().run(
    task_input=task_input,
    workspace=os.getcwd(),          # ← 산출물(제품 파일)이 여기
    runtime_workspace=PROJECT_ROOT, # ← runtime state는 분리됨(projects/<id>)
)
```
- `run()`(`:695,:698,:702`): `user_workspace = workspace or PROJECT_ROOT` = `os.getcwd()`.
- `prepare()`가 그 workspace **직하**에 디렉터리 생성: `agents/`(`project_pipeline.py:593`)·`planning/`(`:188`)·`docs/specs/`(`:239`)·`.checkpoint/`(`:195`). **프로젝트명 하위폴더 없음.**

### §2.2 dogfood 경로 — 대조군 (이미 올바름, 본 설계가 안 건드림)

- `_default_worktree_workspace(run_id)` = `~/.af-dogfood/<run_id>/worktree`(`dogfood.py:515-516`, `:503`).
- `_cwd()`(`dogfood.py:193-196`): isolation ready면 worktree 반환 → 모든 codegen이 worktree 안에서. (초안의 `cwd_for_execution()`은 오기 — 실제 메서드명은 `_cwd`, cross-review 정정)

### §2.3 경로 상수 (`config_paths.py`)

- `BASE_DIR`(`:36-39`): 소스 모드 = repo 루트, frozen exe = exe 디렉터리.
- `PROJECTS_DIR = BASE_DIR/projects`(`:41`).
- `_boot_safe_id(text)`(`:7-11`): 소문자화 + 비영숫자 → `_`, 빈 값이면 `"default"`. **slug 헬퍼로 재사용 가능.**
- `PROJECT_ROOT`(`:48-54`): `AGENT_PROJECT_ROOT` 있으면 그것, 없으면 `PROJECTS_DIR/<PROJECT_ID|default>`.

→ **`BASE_DIR`로 "현재 cwd가 AF repo 안인가"를 정확히 판정할 수 있다**(가드 기반).

---

## §3 설계 원칙 (불변식)

**INV-O1 (전용 하위폴더)**
ad-hoc 새 제품 산출물은 **전용 프로젝트 하위폴더**에 생성한다. cwd 루트에 직접 쏟지 않는다.

**INV-O2 (AF-repo 가드)**
`os.path.abspath(os.getcwd())`가 `config_paths.BASE_DIR` 하위면 = AF 소스 repo 안 → **스캐폴딩 거부**(actionable 메시지: `--out` 지정 또는 다른 디렉터리에서 실행). 소스 오염을 fail-closed로 차단.

**INV-O3 (배포 동등성)**
배포 사용자(repo 밖)의 "현재 위치 기준 생성"을 유지한다 — `<cwd>/<slug>/`. CLAUDE.md 배포 동등성 규칙: dev만 고치고 배포를 깨지 않는다.

**INV-O4 (dogfood 불변)**
dogfood worktree 모델(`~/.af-dogfood/...`)은 **건드리지 않는다**. 이 설계는 ad-hoc 경로 한정.

---

## §4 출력 경로 결정 로직

신규 헬퍼(예: `core/output_paths.py` 또는 `config_paths`에 함수 추가, 타입/상수 SSOT 준수):

```
resolve_product_output_dir(task_input, cwd, explicit_out, base_dir=BASE_DIR) -> str:
    if explicit_out:                          # ① --out 최우선
        return abspath(explicit_out)
    if _is_within(cwd, base_dir):             # ② AF-repo 가드 (INV-O2)
        raise OutputGuardError(              #    fail-closed
            "AF 소스 repo 안에서 새 제품 생성 금지 — --out DIR 지정 또는 다른 디렉터리에서 실행. "
            "(af가 af를 개발하려면 `af dogfood`를 쓰세요.)")
    slug = _boot_safe_id(task_input)          # ③ 배포 사용자: 현재 위치 하위폴더 (INV-O1/O3)
    return os.path.join(abspath(cwd), slug)
```

- **`--out` CLI 플래그 신규**: ad-hoc 진입에 명시적 출력 디렉터리 옵션 추가(가드 우회 정식 경로).
- **slug 충돌**: `<cwd>/<slug>/`가 이미 존재하고 비어있지 않으면 `<slug>-2` 류 suffix 또는 거부(§7 결정).
- `_is_within`: **기존 `core/security_guard.py:129-135`의 `_norm` 패턴 재사용**(`os.path.normcase` + `os.path.realpath` + `os.path.abspath`) — Windows 케이스 비민감성 때문. 순수 `os.path.commonpath`만 쓰면 `C:\Tools\AF` vs `C:\tools\af`에서 가드 우회 위험(cross-review 정정). 재구현 금지, import/재사용.

### §4.1 배선 지점

- `agent_launcher.py:1211` — `workspace=os.getcwd()` → `workspace=resolve_product_output_dir(task_input, os.getcwd(), args.out)`.
- `runtime_workspace=PROJECT_ROOT`(`:1212`)는 **유지**(runtime state는 이미 분리됨).
- arg parser에 `--out` 추가.

---

## §5 구현 단계

| 단계 | 내용 | Tier / 검증 |
|---|---|---|
| **O-S1** | `resolve_product_output_dir` + `OutputGuardError` + `_is_within` 헬퍼 + 단위 테스트(가드 hit/miss·--out·slug·symlink) | Tier 2 (순수 경로 로직, subprocess 없음) → af-critic + af-test-runner |
| **O-S2** | `agent_launcher.py:1211` 배선 + `--out` arg + AF-repo에서 거부 e2e | Tier 3 (`agent_launcher.py` 진입점) → 풀 3-Tier |

> **dogfood 회귀 가드**: O-S2 후 `af dogfood` 경로가 영향 없음을 회귀 테스트로 확인(INV-O4) — dogfood는 `cwd_for_execution`/worktree를 쓰지 ad-hoc resolve를 안 탄다.

---

## §6 불변식 + 테스트 요구사항

| ID | 내용 | 테스트 |
|---|---|---|
| INV-O1 | ad-hoc 산출물은 `<cwd>/<slug>/` 하위폴더 (cwd 루트 직접 금지) | `test_output_goes_to_slug_subdir` |
| INV-O2 | cwd가 `BASE_DIR` 하위 → `OutputGuardError` (fail-closed) | `test_guard_refuses_inside_af_repo` |
| INV-O3 | repo 밖 cwd → `<cwd>/<slug>/` (배포 동등성) | `test_deployed_user_creates_in_cwd` |
| INV-O4 | dogfood 경로는 resolve를 안 타고 worktree 사용 유지 | `test_dogfood_path_unaffected` |
| INV-O5 | `--out` 지정 시 가드보다 우선(명시 의도 존중) | `test_explicit_out_overrides_guard` |

---

## §7 미결 / 의도적 제외

| 항목 | 결정 | 이유 |
|---|---|---|
| slug 충돌 시 suffix vs 거부 | O-S1 구현 시 결정 | 비어있지 않은 기존 폴더 정책. 기본은 거부(데이터 보호) 권장 |
| AF-repo 가드를 거부 대신 `projects/<slug>` 리다이렉트 | 보류 (대안) | 리다이렉트 대상이 gitignore 보장돼야 안전. 1차는 거부(단순·안전) |
| `af project` 서브커맨드 경로 | 본 설계 범위 밖 | 이 설계는 ad-hoc 자연어 진입(`:1206-1213`) 한정. project 서브커맨드는 별도 |
| runtime state 위치(`PROJECT_ROOT`) | 변경 없음 | F12에서 이미 분리. 이 설계는 deliverable workspace만 |

---

## §8 연결 지점

### §8.1 QA 파이프라인(`2026-06-18-user-perspective-qa-pipeline-design.md`) — 소비자
- QA 산출물(HTML 리포트·seam 파일·시나리오)은 제품 workspace에 떨어진다. **출력격리가 prerequisite** — 깨끗한 `<cwd>/<slug>/`가 있어야 QA 산출물도 정리된다.

### §8.2 dogfood(`core/dogfood.py`) — 증명된 대조군
- worktree 격리 모델이 정답임을 dogfood가 실증. 본 설계는 그 원칙을 ad-hoc(새 제품)에 맞는 형태(전용 하위폴더 + 가드)로 적용. dogfood는 *기존 repo 편집*이라 worktree, ad-hoc은 *새 제품 생성*이라 하위폴더 — 케이스가 달라 메커니즘도 다르다.

### §8.3 메타-재귀 점검
- 산출물 = 사용자가 AF로 만든 제품이 **깨끗한 위치에 격리 생성**. 내부 배관이 아니라 사용자 출력 안전 → product-value.

---

## §9 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-06-18 | Draft 작성 (Opus 4.8) — ad-hoc 자연어 경로(`agent_launcher.py:1211 workspace=os.getcwd()`)가 산출물을 cwd 직하(=AF repo 안에서 실행 시 소스)에 쏟는 결함. dogfood가 증명한 격리 원칙을 새 제품 생성에 맞게 적용: 전용 `<cwd>/<slug>/` 하위폴더 + AF-repo fail-closed 가드(`config_paths.BASE_DIR` 기반) + `--out` + 배포 동등성 유지. 좌표 grep 확정. |
| 2026-06-18 | af-cross-review **PASS (BLOCK 0)**. 결함 실재·dogfood 회귀·좌표 모두 코드와 일치 확인(`project_pipeline.py:708` workspace 직하 생성, dogfood는 `:1073-1119` 별도 분기로 ad-hoc resolve 미경유). Advisory 정정 2건 반영(Opus): ① §2.2 메서드명 `cwd_for_execution()`→`_cwd()` 오기 수정 ② §4 `_is_within`을 `security_guard.py:129-135` normcase 패턴 재사용으로 명시(Windows 케이스 우회 방지). 미반영 advisory(의무 아님): frozen-exe 사용자용 에러 메시지 분기(§4 ②), §4.1 `:1211`→`:672` 자동 전파 설명 보강. |
