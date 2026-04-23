# Design Review: 2026-04-09-dev-environment-auto-doc-update

> Source: docs/features/2026-04-09-dev-environment-auto-doc-update.md
> Date: 2026-04-09 14:52
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
- **Judgment**: 양쪽 모두 동일 이슈를 독립적으로 발견. 실제 post-commit(`.githooks/post-commit`)은 현재 git-lfs만 처리하므로 구현 전 수정 가능하나, **설계 문서가 잘못된 코드를 예시로 제시**하고 있어 반드시 수정 필요.
- **Action Required**: §3.3에서 amend 블록(라인 324-328)을 완전히 제거. 대안은 두 가지 중 택일 후 명시:
  - (A) Blueprint 업데이트를 **pre-commit hook으로 이동** → 같은 커밋에 포함
  - (B) 별도 `docs: auto-update` 후속 커밋 생성 + `GIT_HOOK_RECURSION_GUARD` 환경변수 기반 재진입 방지

#### 2. [ACCEPT] [Critical] `_prepend_to_section_12()` 마커 매칭이 잘못된 섹션을 타겟

- **Critic**: `content.index(marker)`가 첫 번째 매치(§11, 라인 855)를 반환 → §11 테이블에 §12 행이 삽입됨.
- **Cross**: "동일한 구분선이 여러 섹션에 존재" — 직접 지적하지 않았으나 관련 dedupe 이슈에서 §12 매칭 불안정성 언급.
- **Judgment**: **실증 확인 완료** — `Master_Blueprint.md`에서 `|------|------|----------|` 패턴이 라인 855(§11 제약사항), 866(§11 에러코드), 878(§12 변경이력) **3곳에 존재**. `str.index()`는 855를 반환하므로 §11 테이블이 손상됨. 이것은 100% 재현 가능한 버그.
- **Action Required**: 라인 174-175를 다음으로 교체:
  ```python
  section_start = content.index("## §12 변경 이력")
  idx = content.index(marker, section_start) + len(marker)
  ```
  추가로 `try/except ValueError` 감싸기 (Finding #7과 합쳐서 처리).

#### 3. [ACCEPT] [High] post-commit 경로에 diff source 계약이 없다

- **Critic**: 직접 지적 없음.
- **Cross**: 현재 `_changed_files()`가 `git diff HEAD` + `git diff --staged`만 보기 때문에, 커밋 직후 clean tree에서는 빈 리스트를 반환 → 사실상 no-op.
- **Judgment**: **실증 확인 완료** — `code_review_updater.py:52-60`에서 `_changed_files()`는 working tree/staged diff만 수집. post-commit 시점에서는 변경이 이미 커밋된 상태이므로 빈 결과. 설계 문서의 경로 2가 실제로 동작하지 않게 됨.
- **Action Required**: 두 updater 모두에 `--rev-range HEAD~1..HEAD` 또는 `--mode {working_tree,last_commit}` 옵션을 추가. post-commit에서는 `HEAD~1..HEAD` 기반 diff를 사용하도록 명시.

#### 4. [ACCEPT] [High] 일일 한도 수치 불일치 (10회 vs 실제 5회)

- **Critic**: §4 테이블이 10회/일이지만 `design_review_utils.py:158`에서 `count < 5`로 5회 제한.
- **Cross**: 동일 지적 + increment 호출 지점 미정의까지 추가 지적.
- **Judgment**: **실증 확인 완료** — `design_review_utils.py:158`이 `return count < 5`임을 확인. 설계 문서(10회)와 코드(5회) 불일치. 또한 Blueprint용 별도 카운터 구현이 §5 변경 목록에 없음.
- **Action Required**: 
  - 10회로 올리려면 `design_review_utils.py`를 §5 변경 목록에 추가하고 limit을 파라미터화
  - 5회 유지면 §4 테이블 수정
  - Blueprint 별도 카운터 사용 시 `check_blueprint_budget()` / `increment_blueprint_count()` 설계 추가
  - LLM 호출 성공 후 `increment_*_count()` 호출 지점 명시

#### 5. [ACCEPT] [High] PostToolUse + post-commit 동시 실행 시 Blueprint 경합 조건

- **Critic**: 두 트리거가 동시에 `Master_Blueprint.md`를 수정 → 중복 기록 또는 변경 유실. `_already_logged()`가 commit hash 기반이지만 PostToolUse는 커밋 전이라 hash가 다름.
- **Cross**: commit hash 기반 dedupe가 PostToolUse 편집 흐름에 맞지 않는다고 독립적으로 지적. 같은 HEAD hash를 공유하는 후속 편집이 전부 스킵됨.
- **Judgment**: 양쪽 모두 dedupe 설계의 결함을 다른 각도에서 발견. PostToolUse에서는 아직 커밋 전이므로 commit hash가 변하지 않아 중복 방지도 안 되고, 반대로 같은 세션의 후속 편집은 같은 hash여서 전부 스킵됨 — 양방향으로 깨진 설계.
- **Action Required**: dedupe 기준을 `trigger_source + diff_digest + quiet_period`로 변경. commit hash는 post-commit 전용 dedupe에만 사용. `file_lock.py`(프로젝트에 존재)를 활용한 크로스-프로세스 락 적용.

#### 6. [ACCEPT] [High] PostToolUse 동기식 LLM 호출이 timeout 모델과 충돌

- **Critic**: 기존 hook 총합 ~33초 + blueprint_updater 30초 = 최악 63초. LLM 활성화 시 더 길어질 수 있음.
- **Cross**: control-plane LLM이 최대 120초인데 PostToolUse가 30초로 제한 → timeout-based silent failure가 기본 동작이 됨.
- **Judgment**: 양쪽 동일 이슈. 매 Edit마다 60초+ 블로킹은 사용성 파괴.
- **Action Required**: PostToolUse에서는 `.af_review_queue` + watcher 패턴으로 enqueue만 하고 즉시 반환. 동기 LLM 호출은 post-commit/CLI 경로로 제한.

#### 7. [ACCEPT] [High] "트리거 3경로" 제목이지만 실제 4경로 나열

- **Critic**: §2.1 제목이 "3경로"인데 실제 경로 1~4가 나열. 구현자가 "3개만 구현하면 된다"고 오독 가능.
- **Cross**: 직접 지적 없음.
- **Judgment**: 사소하지만 구현 명세로 사용되는 문서에서 숫자 불일치는 실수를 유발. 확인 즉시 수정 가능.
- **Action Required**: 라인 36 제목을 `### 2.1 트리거 4경로 (범용)`으로 수정.

#### 8. [ACCEPT] [Medium] `_fallback_changelog_entry`의 scope 추출이 부정확

- **Critic**: `split("/")[1]`이 `"core/fsa_loop.py"` → `"fsa_loop.py"` (파일명이 scope). 의도는 모듈 그룹인데 확장자 포함된 파일명이 됨.
- **Cross**: 직접 지적 없음.
- **Judgment**: `split("/")[1]`이 2-depth 경로에서는 파일명을, 3-depth 이상에서만 디렉토리명을 반환하는 비일관적 동작. §12 이력 품질에 직접 영향.
- **Action Required**: `split("/")[0]`(최상위 디렉토리)을 사용하거나, `Path(f).parts` 기반으로 모듈 그룹을 추출하는 로직으로 변경.

#### 9. [ACCEPT] [Medium] `content.index(marker)` 에러 핸들링 부재

- **Critic**: `str.index()`는 마커 미발견 시 `ValueError`. "항상 exit 0" 원칙과 모순.
- **Cross**: 직접 지적 없음.
- **Judgment**: Finding #2의 수정과 함께 처리. graceful degradation 원칙을 코드 예시에서도 일관되게 적용해야 함.
- **Action Required**: `try/except ValueError`로 감싸서 마커 미발견 시 로그만 남기고 exit 0 반환.

#### 10. [ACCEPT] [Medium] Blueprint LLM 호출에 대한 예산 카운터 부재

- **Critic**: §4에 "Blueprint LLM: 10회/일"이라고 명시했지만 구현에 카운터 설계 없음.
- **Cross**: Finding #2에서 동일하게 지적 — count increment 지점도 없음.
- **Judgment**: Finding #4(수치 불일치)와 연관. 예산 통제가 설계 원칙 4("기존 인프라 재사용")의 핵심인데 실제 설계가 빠져 있음.
- **Action Required**: `check_blueprint_budget()` / `increment_blueprint_count()`를 §3.1에 추가하고, §5 변경 목록에 `design_review_utils.py` 포함.

#### 11. [ACCEPT] [Medium] "범용 스크립트" 원칙과 af.exe 런타임 경로 괴리

- **Critic**: 직접 지적 없음.
- **Cross**: af.exe는 `CodeReviewDocHook`으로 별도 포맷/부수효과를 사용 중. blueprint만 스크립트로 추가하면 문서 스키마와 dedupe 정책이 갈라짐.
- **Judgment**: 설계 원칙 1("모두 동일한 스크립트")이 현실과 맞지 않는 상태에서 blueprint만 추가하면 불일치 확대. `code_review_doc.py:174`의 독자적 포맷을 확인함.
- **Action Required**: 최소한 entry schema, dedupe, side effect를 공유 모듈로 분리하는 방안을 §7(향후 확장) 또는 본문에 명시. 현재 스코프에서 해결 불가하면 §8(미해결 사항)에 기록.

#### 12. [HOLD] [Medium] `BlueprintUpdateHook` 스코프 포함 여부 불명확

- **Critic**: frozen 빌드에서 소스 파일 AST 파싱 불가 가능성 언급.
- **Cross**: 포함한다면 frozen build용 shared core, `agent_runner.py` 등록, `af.spec` 패키징까지 설계 필요. 제외한다면 경로 3 서술 축소 필요.
- **Judgment**: 이번 작업이 "개발환경 auto-doc update"만인지, af.exe 런타임까지 포함인지 범위 결정이 필요.
- **Question for Author**: 경로 3(af.exe `BlueprintUpdateHook`)을 이번 스코프에 포함하는가? 포함한다면 frozen 빌드 호환성 설계를 추가하고, 제외한다면 §2.1/§5에서 "(선택)" 표시를 "(향후)"로 변경하라.

#### 13. [REJECT] [Low] 2건 — settings.local.json 덮어쓰기 우려 + Windows shell hook 호환성

- **Source**: Cross (Finding #6, #7)
- **Original Finding**: session_adapter가 settings.local.json을 덮어쓸 수 있다 / shell hook이 Windows에서 동작 안 할 수 있다
- **Rejection Reason**: Cross 스스로 검증 후 기각함. session_adapter는 PostToolUse를 건드리지 않고(`:253-264`), `.githooks/post-commit`은 이미 shell 기반으로 운영 중(`:1`, `CLAUDE.md:39`).

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | post-commit amend 무한 재귀 | Critical | ACCEPT | Both |
| 2 | §12 마커가 §11을 타겟 | Critical | ACCEPT | Critic (Cross 부분 동의) |
| 3 | post-commit diff source 계약 부재 | High | ACCEPT | Cross |
| 4 | 일일 한도 10회 vs 5회 불일치 | High | ACCEPT | Both |
| 5 | PostToolUse + post-commit 경합/dedupe 실패 | High | ACCEPT | Both |
| 6 | PostToolUse 동기 LLM timeout 충돌 | High | ACCEPT | Both |
| 7 | "3경로" 제목에 4경로 나열 | High | ACCEPT | Critic |
| 8 | fallback scope 추출 부정확 | Medium | ACCEPT | Critic |
| 9 | content.index() 에러 핸들링 부재 | Medium | ACCEPT | Critic |
| 10 | Blueprint LLM 예산 카운터 없음 | Medium | ACCEPT | Both |
| 11 | 범용 원칙 vs af.exe 경로 괴리 | Medium | ACCEPT | Cross |
| 12 | BlueprintUpdateHook 스코프 불명확 | Medium | HOLD | Cross |
| 13 | settings 덮어쓰기 + Windows 호환 (2건) | Low | REJECT | Cross |

---

### Recommendations

구현 착수 전 **반드시** 수정해야 할 사항 (Critical):

1. **§3.3 라인 324-328**: amend 블록 완전 제거. pre-commit 방식(A) 또는 후속 커밋 + 재진입 방지(B) 중 택일하여 명시
2. **§3.1 라인 174-175**: `"## §12 변경 이력"` 헤딩을 먼저 찾은 후 marker 매칭 + `try/except ValueError` 추가

구현 착수 전 **권장** 수정 사항 (High):

3. 두 updater에 `--rev-range` / `--mode` 옵션 추가하여 post-commit diff source 명시
4. §4 일일 한도를 코드 현실(5회)에 맞추거나, 변경 시 §5 목록에 `design_review_utils.py` 추가
5. dedupe 기준을 `trigger_source + diff_digest`로 재설계 + `file_lock.py` 활용
6. PostToolUse에서 LLM 호출을 enqueue 방식으로 전환 (동기 호출 금지)
7. §2.1 제목 "3경로" → "4경로"로 수정