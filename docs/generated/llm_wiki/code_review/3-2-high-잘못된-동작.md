---
generated_at: 2026-06-12T22:50:10+09:00
source_commit: 7570cdf6
sources:
  - "docs/code_review/code-review.md"
---

# 3.2 High — 잘못된 동작

> Source: `docs/code_review/code-review.md:274`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 3.2 High — 잘못된 동작

| ID | 파일 | 라인 | 문제 | 상태 |
|----|------|------|------|------|
| H1 | `dynamic_orchestrator.py` | 609,722 | state_board 비동기 업데이트에 asyncio.Lock 없음. race condition | ✅ 수정됨 |
| H2 | `agent_runner.py` | 589-637 | `_skill_module_cache` 무한 증가. 폐기 메커니즘 없음 | ✅ 수정됨 |
| H3 | `ise_redesigner.py` | 111,171 | JSON 파싱 실패 시 silent fallback → 무한 retry 루프 가능 | ✅ 수정됨 |
| H4 | `control/intake.py` | 112 | `continuity_snapshot.get("overall_health")` vs 실제 키 "recovery_health" | ✅ 수정됨 |
| H5 | `dashboard.py` | 17 | 글로벌 `_DASHBOARD_CACHE` 스레드 안전하지 않음 | ✅ 수정됨 |
| H6 | `control_plane_llm.py` | 50-56 | `AF_CONTROL_PLANE_PROVIDERS` 환경변수 미지원 | ✅ 수정됨 |

### 3.2.1 검증 중 추가 발견 (2026-04-03)

수정 검증 과정에서 발견된 추가 버그 및 개선:

| ID | 파일 | 문제 | 상태 |
|----|------|------|------|
| H6a | `control_plane_llm.py:55` | H6 수정에서 `return`이 API 엔진 초기화를 건너뜀 → CLI+API 동시 사용 불가 | ✅ 수정됨 |
| H2a | `agent_runner.py:640` | H2 캐시 퇴거 시 `sys.modules` 엔트리 미정리 → 메모리 누수 | ✅ 수정됨 |
| H5a | `dashboard.py:95,106` | H5는 Lock만 추가. 파일 쓰기 자체가 non-atomic (C2와 동일 유형) | ✅ 수정됨 |
| C4a | `issue_tracker.py:88` | C4에서 `list_issues`의 `labels` 파라미터 미검증 | ✅ 수정됨 |
| C4b | `issue_tracker.py:70` | `_sanitize_arg`가 `\n`을 허용 — issue_id/title에 부적절 | ✅ 수정됨 |

### 3.2.2 Forge 품질 파이프라인 구현 중 발견 (2026-04-07)

| ID | 파일 | 문제 | 상태 |
|----|------|------|------|
| C5 | `skill_procurer.py:380` | `SkillMetadata(path=..., source=...)` — 존재하지 않는 필드명으로 TypeError. `source_path`, `distribution_source`가 올바른 필드명 | ✅ 수정됨 |
| H7 | `skill_procurer.py:124` | `read_skill_lock()` 키 조회 시 `safe_id()` 미적용. `lock_skill_state()`는 `safe_id()`로 키 저장하므로 대문자/특수문자 포함 시 lock 키 불일치 | ✅ 수정됨 |

### 3.2.3 optional-id 정규화 work-item (2026-05-19)

| ID | 파일 | 문제 | 상태 |
|----|------|------|------|
| H8 | `core/utils.py` | `safe_id("")` = `"skill"` 계약 버그 — task_id·owner_role·candidate_id 등 optional 식별자 22개 파일 114곳에서 빈 값→`"skill"` 오염. `if not id` 가드 무력화·유령 수신자·잘못된 중복 제거 발생 | ✅ 수정됨 (`safe_optional_id()` 신설, 114개 B-site 교체) |
````
