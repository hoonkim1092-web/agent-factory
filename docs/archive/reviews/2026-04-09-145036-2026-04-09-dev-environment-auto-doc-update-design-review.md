# Design Review: 2026-04-09-dev-environment-auto-doc-update

> Source: docs/features/2026-04-09-dev-environment-auto-doc-update.md
> Date: 2026-04-09 14:50
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 3 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

2개의 Critical 발견 사항으로 인해 구현 전 설계 수정 필수.

---

### Aggregated Findings (15 total: 11 ACCEPT, 2 REJECT, 1 HOLD, 1 Missing)

#### 1. [ACCEPT] [Critical] post-commit `--amend` 무한 재귀 + 데이터 손실
- **Critic**: `git commit --amend`가 `post-commit`을 재트리거하여 무한 루프 발생. 환경변수 가드 없음.
- **Cross**: 동일 — amend 재트리거 + `2>/dev/null`로 오류 은폐. 설계 §8에서도 미해결로 인지했으나 hook 코드에 그대로 포함.
- **Judgment**: 양쪽 모두 동일 근거로 지적. §8 "미해결 결정 사항"에서도 위험을 인지했으나 구현부에 반영되지 않은 명백한 결함.
- **Action Required**: (1) v1에서 amend 제거, 별도 커밋 방식 채택. (2) 재귀 가드(`AF_POST_COMMIT_RUNNING=1`) 필수. (3) `2>/dev/null` 제거, 실패 로그를 `.af_review_queue/failed`로 라우팅.

#### 2. [ACCEPT] [Critical] §12 마커 `content.index(marker)` 가 §11 테이블에 삽입
- **Critic**: `|------|------|----------|` 패턴이 Blueprint 내 3곳(§0, §11×2, §12)에 존재. `index()`는 첫 번째 매치(§11)를 반환.
- **Cross**: 동일 — `Master_Blueprint.md` L855, L866, L875, L878 확인. file-global `index()` 사용 불가.
- **Judgment**: 양쪽 동일 근거, Blueprint 실파일 라인번호까지 일치. 구현 시 Blueprint 손상 확실.
- **Action Required**: `section_start = content.index("## §12 변경 이력")` 후 `content.index(marker, section_start)` 2단계 검색으로 변경.

#### 3. [ACCEPT] [High] `ControlPlaneLLM` PostToolUse 내 CLI 재귀 호출
- **Critic**: `ControlPlaneLLM`은 `claude_cli` 우선 사용. PostToolUse hook 안에서 CLI를 spawn하면 세션 충돌 + 타임아웃 + 토큰 비용 발생.
- **Cross**: 아키텍처 적합성은 인정(REJECT)하였으나, hook 내 CLI spawn 문제는 별개.
- **Judgment**: Critic의 지적은 아키텍처 패턴이 아닌 **실행 컨텍스트**(hook 내부) 문제. `code_review_doc.py`가 `ControlPlaneLLM`을 쓰는 것과, PostToolUse 30초 timeout 내에서 쓰는 것은 다른 문제.
- **Action Required**: PostToolUse 경로에서는 API-only 모드 강제, 또는 LLM 리뷰를 큐잉만 하고 post-commit에서 실행.

#### 4. [ACCEPT] [High] 일일 한도 불일치 + budget 경로 이중화
- **Critic**: 설계(10회/일) vs 기존 코드 `design_review_utils.py:158`(5회/일) 불일치. 카운터 분리 여부 미정.
- **Cross**: 기존 `design_review_watcher`에 이미 debounce/budget 경로 존재. 새 설계가 제2의 경로를 만들면 single source of truth 소실.
- **Judgment**: 양쪽이 같은 영역을 다른 각도에서 지적. 한도 수치 + 제어 평면 통합 모두 미해결.
- **Action Required**: (1) 정확한 한도 값 확정(10 or 5). (2) `design_review_utils.py`에 채널별 카운터 분리 설계 추가. (3) 기존 watcher 경로와의 관계 명시.

#### 5. [ACCEPT] [High] debounce가 "기존 개선"이 아닌 신규 기능
- **Critic**: 현재 `code_review_updater.py`에 debounce 로직 없음. `_should_run()` 미존재. `.af_review_queue/` gitignore 미확인.
- **Cross**: 직접 지적 없음.
- **Judgment**: 설계 문서가 변경 범위를 과소 기술. "개선"이 아닌 "신규 추가"로 리스크 평가가 달라짐.
- **Action Required**: (1) §5 변경 목록에서 "기존 개선" → "신규 추가"로 수정. (2) `.af_review_queue/` gitignore 확인 및 문서화.

#### 6. [ACCEPT] [High] commit-hash dedupe가 PostToolUse 모드에서 오작동
- **Critic**: 직접 지적 없음.
- **Cross**: `HEAD`는 커밋 전까지 불변. PostToolUse에서 한 번 기록 후 동일 커밋 내 후속 편집이 모두 스킵됨.
- **Judgment**: 코드 레퍼런스(`code_review_updater.py:L155, L169`) 기반의 명확한 로직 결함.
- **Action Required**: PostToolUse 모드에서는 diff hash 또는 mtime 기반 dedupe 사용. commit-hash dedupe는 post-commit 전용으로 제한.

#### 7. [ACCEPT] [High] 트리거 경로 수 오류 + BlueprintUpdateHook 미설계
- **Critic**: "3경로" 제목이나 실제 4경로 나열. `BlueprintUpdateHook` 설계 없음.
- **Cross**: `HookEventBus`는 auto-discover 불가. `agent_runner.py` 등록 지점, `PRIORITY`, 실패 정책 미정.
- **Judgment**: 양쪽이 같은 경로 3/hook을 다른 관점에서 지적. 제목 오류 + 구현 계약 부재.
- **Action Required**: (1) 제목 "4경로"로 수정. (2) `BlueprintUpdateHook` 구현 여부 결정 — 포함 시 등록 코드·우선순위·실패 정책 추가, 제외 시 "향후 확장"으로 이동.

#### 8. [ACCEPT] [High] §3 업데이트 타겟팅 불안정 + 경로 매핑 부재
- **Critic**: `_detect_signature_changes()`가 `"+    def "` (4-space) 하드코딩. nested class 메서드(8-space), 데코레이터 감지 불가.
- **Cross**: 파일명 검색만으로는 `core/control/*.py`, `core/memory_system/*.py`가 §3의 어느 서브섹션에 해당하는지 결정 불가.
- **Judgment**: Critic은 감지 정확도, Cross는 타겟팅 정확도. 둘 다 §3 자동 업데이트의 신뢰성을 훼손.
- **Action Required**: (1) 시그니처 감지를 `re.match(r'^[+-]\s+(class |def )', line)` 정규식으로 변경. (2) path-to-section 매핑 테이블 추가 (예: `core/control/* → §3.10`).

#### 9. [ACCEPT] [Medium] PostToolUse hook timeout(30초) vs CLI timeout(120초) 충돌
- **Critic**: hook 30초 만료 시 CLI 강제 종료 → Blueprint 반쯤 기록된 상태 가능.
- **Cross**: 직접 지적 없음.
- **Judgment**: `control_plane_llm.py:124`의 `timeout_sec=120` 코드 레퍼런스가 명확. atomic_write가 있더라도 tmp→rename 사이에 종료 가능.
- **Action Required**: hook timeout을 150초로 상향, 또는 PostToolUse에서는 `--no-llm`만 실행.

#### 10. [ACCEPT] [Medium] diff 소스 인터페이스 미정의
- **Critic**: 직접 지적 없음.
- **Cross**: post-commit 상태에서 working-tree diff는 빈 결과. `--diff-range` 또는 `--commit` 인자 없음.
- **Judgment**: `code_review_updater.py:L52, L63` 레퍼런스 기반. 경로별 diff 소스 차이가 명확히 존재하나 CLI 인터페이스에 반영 안 됨.
- **Action Required**: 양 updater에 `--diff-range HEAD~1..HEAD` 인자 추가, 각 트리거 경로에서 명시적으로 전달.

#### 11. [ACCEPT] [Medium] code-review.md 구조적 충돌
- **Critic**: 전체 코드 리뷰 스냅샷 + hook 리뷰 로그가 동일 파일에 공존. 설계에서 미다룸.
- **Cross**: 직접 지적 없음.
- **Judgment**: 단일 출처만 확인했지만, 파일 역할 혼재는 관찰 가능한 사실.
- **Action Required**: LLM 리뷰 로그 append 대상이 스냅샷 문서와 동일 파일인지, 분리할지 명시.

#### 12. [ACCEPT] [Low] Windows shell 호환성 미검증
- **Critic**: Git for Windows `sh.exe`에서 `grep -E`, background `&`, 줄바꿈 처리 검증 필요.
- **Cross**: 직접 지적 없음.
- **Judgment**: 프로젝트가 Windows 11 환경. 위험도는 낮지만 검증 필요.
- **Action Required**: 검증 방법에 Windows 환경 post-commit hook 테스트 항목 추가.

#### 13. [HOLD] Runtime hook 자동 업데이트 정책 미결정
- **Critic**: 직접 지적 없음.
- **Cross**: `BlueprintUpdateHook`을 AF 런타임에서 매 실행마다 활성화하면 문서 노이즈 발생. "선택"이라 했으나 정책 없음.
- **Judgment**: 제품 결정 사항. 설계 작성자의 의도 확인 필요.
- **Question for Author**: Blueprint 자동 업데이트는 개발자 워크플로우(커밋/편집) 전용인가, AF 에이전트 실행 결과도 포함하는가?

#### 14. [REJECT] ControlPlaneLLM 아키텍처 부적합
- **Source**: Cross
- **Original Finding**: 문서 업데이터에 새 LLM 추상화가 필요할 수 있음.
- **Rejection Reason**: `CodeReviewDocHook`이 이미 `ControlPlaneLLM`을 사용 중이며(`code_review_doc.py:L110`), 이것이 현재 프로젝트의 관례. 아키텍처 적합성은 Cross 스스로도 REJECT 판정.

#### 15. [REJECT] Frozen-build 영향 누락
- **Source**: Cross
- **Original Finding**: PyInstaller 패키징을 무시했을 수 있음.
- **Rejection Reason**: 설계 §5에 `af.spec`이 관련 파일로 명시, §8·§10 빌드 섹션도 포함. Cross 스스로도 REJECT 판정.

---

### Critic "Missing from Design" 항목 평가

| # | 항목 | 판정 | 근거 |
|---|------|------|------|
| M1 | 동시 실행 보호 (PostToolUse + post-commit race) | ACCEPT | `file_lock.py` 존재하나 연결 미설계 |
| M2 | `increment_code_review_count()` 호출 누락 | ACCEPT | budget check만 있고 카운터 증가 로직 없음 |
| M3 | rollback 시 §12 잔존 행 | Low — 수동 정리 허용 가능 | |
| M4 | Blueprint 파일 잠금과 CLAUDE.md "같은 커밋" 규칙 공존 | ACCEPT | 자동 업데이트가 별도 커밋을 만들면 규칙 위반 |

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | post-commit amend 무한 재귀 | Critical | ACCEPT | Both |
| 2 | §12 marker 잘못된 테이블 삽입 | Critical | ACCEPT | Both |
| 3 | PostToolUse 내 CLI 재귀 호출 | High | ACCEPT | Critic |
| 4 | 일일 한도 불일치 + budget 이중화 | High | ACCEPT | Both |
| 5 | debounce "개선" → 실제 신규 | High | ACCEPT | Critic |
| 6 | commit-hash dedupe PostToolUse 오작동 | High | ACCEPT | Cross |
| 7 | 경로 수 오류 + hook 미설계 | High | ACCEPT | Both |
| 8 | §3 타겟팅 불안정 + 매핑 부재 | High | ACCEPT | Both |
| 9 | hook timeout vs CLI timeout 충돌 | Medium | ACCEPT | Critic |
| 10 | diff 소스 인터페이스 미정의 | Medium | ACCEPT | Cross |
| 11 | code-review.md 구조적 충돌 | Medium | ACCEPT | Critic |
| 12 | Windows shell 호환성 | Low | ACCEPT | Critic |
| 13 | Runtime hook 정책 미결정 | — | HOLD | Cross |
| 14 | ControlPlaneLLM 아키텍처 | — | REJECT | Cross |
| 15 | Frozen-build 누락 | — | REJECT | Cross |

---

### Recommendations (구현 전 필수 조치)

1. **Critical 2건 해결**: §12 marker 2단계 검색 + post-commit amend 제거/재귀 가드
2. **동시 실행 보호**: PostToolUse ↔ post-commit 간 `file_lock.py` 기반 mutex 설계 추가
3. **CLI 인터페이스 확정**: `--diff-range`, `--commit` 인자를 양 updater에 추가하고 경로별 호출 예시 명시
4. **budget 단일화**: 한도 값 확정(5 or 10), 채널별 카운터 분리, `increment_code_review_count()` 연결
5. **PostToolUse LLM 전략 결정**: API-only 강제 또는 큐잉+post-commit 실행
6. **path-to-section 매핑 테이블** 추가 (§3 타겟팅 안정화)
7. **경로 수 "3→4" 수정** + `BlueprintUpdateHook` 범위 확정
8. **CLAUDE.md "같은 커밋" 규칙**과 자동 업데이트의 공존 방식 명시