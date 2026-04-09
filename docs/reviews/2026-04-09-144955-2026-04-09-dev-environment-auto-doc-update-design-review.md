# Design Review: 2026-04-09-dev-environment-auto-doc-update

> Source: docs/features/2026-04-09-dev-environment-auto-doc-update.md
> Date: 2026-04-09 14:49
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 3 providers)
> Trigger: unknown

---

모든 근거를 확인했습니다. 최종 종합 리뷰를 작성합니다.

---

## Final Design Review

### Verdict: BLOCK

Critical 이슈 2건이 있어 이를 해결하기 전까지 구현을 시작해서는 안 됩니다.

---

### Aggregated Findings (13 total)

#### 1. [ACCEPT] [Critical] post-commit hook 내 `git commit --amend`가 무한 재귀를 유발

- **Critic**: post-commit 내 amend가 다시 post-commit을 트리거 → 무한 재귀. §8 미해결 사항에서 "위험"을 인지하면서도 §3.3 본문에 amend 코드를 그대로 포함 → 모순.
- **Cross**: 동일 지적. "본문 예시는 이미 구현안처럼 제시되어 있어 구현자가 그대로 옮기기 쉽다"
- **Judgment**: 양쪽 모두 동일 이슈를 독립적으로 발견. 실제 post-commit(`:.githooks/post-commit`)은 현재 git-lfs만 처리하므로 구현 전 수정 가능하나, **설계 문서가 잘못된 코드를 예시로 제시**하고 있어 반드시 수정 필요.
- **Action Required**: §3.3에서 amend 블록(라인 324-328)을 완전히 제거. 대안은 두 가지 중 택일 후 명시:
  - (A) Blueprint 업데이트를 **pre-commit hook으로 이동** → 같은 커밋에 포함
  - (B) 별도 `docs: auto-update` 후속 커밋 생성 + `GIT_HOOK_RECURSION_GUARD` 환경변수 기반 재진입 방지

#### 2. [ACCEPT] [Critical] `_prepend_to_section_12()` 마커 매칭이 잘못된 섹션을 타겟

- **Critic**: `content.index(marker)`가 첫 번째 매치(§11, 라인 855)를 반환 → §11 테이블에 §12 행이 삽입됨.
- **Cross**: "동일한 구분선이 여러 테이블에 있을 때 잘못된 섹션을 건드린다"
- **Judgment**: 실제 `Master_Blueprint.md`에서 `|------|------|----------|`가 **라인 855, 866, 878** 총 3곳에 등장함을 확인. `content.index(marker)`는 855를 반환하므로 §11이 손상됨. 확정적 버그.
- **Action Required**: 라인 173-175를 다음으로 수정:
  ```python
  section_start = content.index("## §12 변경 이력")
  idx = content.index(marker, section_start) + len(marker)
  ```

#### 3. [ACCEPT] [High] PostToolUse diff 범위 오류 + 트리거별 입력 계약 부재

- **Critic**: PostToolUse 시점에서 `git diff HEAD`는 미커밋 전체 변경을 포함 → 중간 상태로 Blueprint 오염 가능.
- **Cross**: CLI 인터페이스에 `--trigger`/`--diff-range`/`--file` 인자가 없어 각 경로에서 어떤 diff를 볼지 불명확.
- **Judgment**: 두 리뷰가 같은 근본 원인(diff 범위 미정의)을 다른 각도에서 지적. 현재 `code_review_updater.py:52`의 기존 동작도 이 문제를 갖고 있음.
- **Action Required**: 
  - CLI에 `--trigger {posttooluse|postcommit|manual}` 인자 추가
  - PostToolUse: `--no-llm` 모드로만 실행하거나, `--file` 인자로 방금 수정한 파일만 대상
  - post-commit: `--diff-range HEAD~1..HEAD`로 커밋 범위 명시

#### 4. [ACCEPT] [High] Blueprint 동시 쓰기 race condition — 락 전략 부재

- **Critic**: §3.3 라인 317-320에서 `blueprint_updater`와 `code_review_updater`를 `&`로 병렬 실행 → read-modify-write race. `_atomic_append()`가 실제로 atomic하지 않음.
- **Cross**: "같은 `Master_Blueprint.md`를 4개 경로가 모두 수정 가능한데 락/단일 writer 전략 없음"
- **Judgment**: 양쪽 동일 지적. `core/file_lock.py`(thread-safe + process-safe lock)가 이미 존재하는데 활용하지 않음.
- **Action Required**: 
  - post-commit에서 두 스크립트를 **순차 실행**으로 변경 (`&` 제거)
  - 또는 `core.file_lock.locked_file()`을 Blueprint read-modify-write에 적용

#### 5. [ACCEPT] [High] 일일 LLM 한도 불일치: 설계 "10회" vs 코드 "5회"

- **Critic**: 설계 라인 254/393에서 "최대 10회/일"이나 `design_review_utils.py:158`은 `return count < 5`.
- **Cross**: 미지적
- **Judgment**: 코드를 직접 확인 — `check_code_review_budget()`은 실제로 5회 한도. 설계가 "design_review_utils 연동"이라고 하면서 한도를 다르게 적는 것은 구현 시 혼란 유발.
- **Action Required**: 설계 문서의 "10회"를 "5회"로 수정하고, Blueprint 전용 별도 카운터가 필요하면 §8 미해결 사항 #3의 결론을 확정하여 반영.

#### 6. [ACCEPT] [High] debounce/budget 통합 누락 — `increment_code_review_count()` 호출 없음

- **Critic**: `_should_run()` 함수가 기존 `update_code_review_doc()` 어디에 삽입되는지 미명시. `increment_code_review_count()` 호출이 기존 코드에도, 설계에도 없어 한도가 영원히 차지 않음.
- **Cross**: 미지적
- **Judgment**: `code_review_updater.py`에서 `increment_code_review_count`를 grep한 결과 **매치 없음** 확인. budget을 체크만 하고 증가시키지 않으면 한도 제어가 동작하지 않음.
- **Action Required**: 
  - `_should_run()` 호출 위치를 `update_code_review_doc()` 진입부에 명시
  - LLM 호출 성공 후 `increment_code_review_count()` 호출 추가
  - before/after 형식으로 기존 함수 수정 계획 제시

#### 7. [ACCEPT] [High] 기존 review queue/watcher 인프라와 중복 경로

- **Critic**: 미지적 (af.exe 경로 중복은 #8에서 부분 언급)
- **Cross**: "PostToolUse에서 직접 호출하면 기존 queue/quiet period/watcher 소비자 구조를 우회 → 비용 제어와 출력 포맷 이중화"
- **Judgment**: `design_review_watcher.py`, `design_review_trigger.py`, `design_review_utils.py`에 이미 queue→watcher 소비자 패턴이 있으므로 동일 아키텍처를 따라야 일관성 유지.
- **Action Required**: PostToolUse에서는 **enqueue만** 하고, 실제 LLM 실행 + 문서 쓰기는 기존 watcher 소비자에서 처리하는 방안을 설계에 반영. 또는 의도적으로 watcher를 우회하는 이유를 명시.

#### 8. [ACCEPT] [Medium] af.exe 런타임 훅 등록 방식 미반영

- **Critic**: 기존 `CodeReviewDocHook`과 PostToolUse hook 동시 활성화 시 중복 기록 문제.
- **Cross**: `HookEventBus`는 자동 발견이 아니라 `bus.register()` 수동 등록 방식. `AgentRunner` 등록과 `af.spec` 반영 미명시.
- **Judgment**: `agent_runner.py:947-982`에서 모든 훅이 수동 등록됨을 확인. 설계에 "선택"이라고만 적으면 구현 시 누락 확실.
- **Action Required**: 
  - `AgentRunner`에서 `BlueprintUpdateHook` 등록 코드 위치 명시
  - CLI provider 세션 시 `CodeReviewDocHook.post_execute()` 스킵 조건 추가
  - `af.spec` hiddenimports에 `core.hooks.blueprint_update_hook` 추가

#### 9. [ACCEPT] [Medium] §0 테이블 형식 미검증 + 파일 삭제/이동 미처리

- **Critic**: §0에 여러 서브테이블(루트, core/control/, core/hooks/ 등)이 있는데 새 파일이 어느 테이블에 들어가는지 판정 로직 없음.
- **Cross**: "설계는 신규 파일만 다루며 삭제/이름변경/이동(D/R)을 정의하지 않음"
- **Judgment**: 두 리뷰가 같은 §0 업데이트 로직의 다른 측면을 지적. §0는 서브디렉토리별로 테이블이 분리되어 있어 단순 append가 불가.
- **Action Required**: 
  - 실제 §0 테이블 형식과 서브테이블 목록을 설계에 첨부
  - `git diff --name-status`로 A/M/D/R 각각의 반영 규칙 정의
  - 서브테이블 선택 로직(디렉토리 기반) 명시

#### 10. [ACCEPT] [Medium] PostToolUse timeout 30초는 LLM 호출에 부족 가능

- **Critic**: `ControlPlaneLLM` CLI subprocess는 네트워크 상태에 따라 30초 초과 가능. timeout 강제종료 시 Blueprint 중간 상태.
- **Cross**: 미지적
- **Judgment**: LLM 기반 업데이트를 PostToolUse에서 실행한다면 합리적 우려. 기존 `--no-llm` hook은 timeout 15초.
- **Action Required**: timeout을 45-60초로 늘리거나, 스크립트 내부에서 자체 타임아웃(25초) + no-llm 폴백 전환 로직 추가.

#### 11. [HOLD] [Medium] Blueprint 헤더 version 진실의 원천 미정

- **Critic**: 미지적
- **Cross**: "현재 문서와 코드의 버전이 이미 어긋나 있어서 updater가 무엇을 canonical source로 삼아야 하는지 결정 불가"
- **Judgment**: `_update_header_metadata()`에서 version을 어디서 가져오는지 설계에 미명시. `version.py`인지, Blueprint 자체 버전인지 정책 필요.
- **Question for Author**: `version.py.__version__`을 유일한 진실의 원천으로 사용할 것인가? Blueprint가 독립 버전을 가질 필요가 있는가?

#### 12. [ACCEPT] [Low] `_detect_signature_changes()` 패턴 매칭이 너무 단순

- **Critic**: `"+    def "`는 spaces 4칸만 매칭. 탭, 8칸, 중첩 클래스, `async def` 등 누락.
- **Cross**: 미지적
- **Judgment**: 기능적 누락이나 §7 "향후 확장"으로 분류 가능. 초기 버전에서는 수용 가능하나 알려진 한계로 명시해야 함.
- **Action Required**: 정규식 기반으로 전환 — `re.match(r'^[+-]\s*(async\s+)?(def|class)\s+', line)`, 또는 §8에 알려진 한계로 문서화.

#### 13. [REJECT] [Low] `scripts/blueprint_updater.py`에 대한 `af.spec` 변경 필요성

- **Source**: Cross (#7)
- **Original Finding**: standalone 스크립트가 빌드에 빠져 frozen 환경에서 깨질 수 있다는 우려.
- **Rejection Reason**: Cross 스스로 REJECT함. `scripts/*.py`는 hook/CLI에서 직접 Python으로 실행되므로 `af.spec` hiddenimport 대상이 아님. 문서도 이를 구분하고 있음 (`core/hooks/blueprint_update_hook.py`만 af.spec 대상).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | post-commit amend 무한 재귀 | Critical | ACCEPT | Both |
| 2 | §12 마커 패턴 충돌 (잘못된 섹션 타겟) | Critical | ACCEPT | Both |
| 3 | PostToolUse diff 범위 + 입력 계약 부재 | High | ACCEPT | Both |
| 4 | Blueprint 동시 쓰기 race condition | High | ACCEPT | Both |
| 5 | 일일 한도 10회 vs 5회 불일치 | High | ACCEPT | Critic |
| 6 | debounce/increment 통합 누락 | High | ACCEPT | Critic |
| 7 | 기존 queue/watcher 인프라 중복 | High | ACCEPT | Cross |
| 8 | af.exe 훅 등록 방식 미반영 | Medium | ACCEPT | Both |
| 9 | §0 테이블 형식 미검증 + D/R 미처리 | Medium | ACCEPT | Both |
| 10 | PostToolUse timeout 30초 부족 | Medium | ACCEPT | Critic |
| 11 | Blueprint version 진실의 원천 미정 | Medium | HOLD | Cross |
| 12 | signature 감지 패턴 단순 | Low | ACCEPT | Critic |
| 13 | scripts/ af.spec 변경 필요성 | Low | REJECT | Cross |

---

### Recommendations

구현 전 반드시 설계 문서에서 수정해야 할 사항:

1. **§3.3 amend 코드 제거** — pre-commit 이동 또는 후속 커밋 방식 중 택일하여 명시
2. **§3.1 `_prepend_to_section_12`** — `"## §12 변경 이력"` 헤딩 기반 2단계 매칭으로 수정
3. **트리거별 CLI 계약 정의** — `--trigger`, `--diff-range`, `--file` 인자 추가하고 각 경로별 기본값 명시
4. **병렬 실행 제거** — post-commit에서 `&` 제거하고 순차 실행, 또는 `file_lock` 적용
5. **일일 한도를 5회로 통일** — 별도 카운터가 필요하면 §8 #3 결론 확정
6. **`increment_code_review_count()` 호출 추가** — LLM 호출 성공 후 위치 명시
7. **watcher 아키텍처와의 관계 정리** — 직접 호출 vs enqueue 중 택일
8. **"3경로" → "4경로"** 제목 수정 (사소하지만 신뢰도에 영향)