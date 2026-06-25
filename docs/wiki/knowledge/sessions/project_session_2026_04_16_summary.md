---
name: 2026-04-16 세션 요약 — CLI 안정성 + 교차검증 파이프라인
description: CLI provider 버그 수정, Codex 모델, 조기 종료, 교차검증 파이프라인 구현. 미완료 항목 포함.
type: project
originSessionId: 9bec23b4-54e8-405d-8fc1-bae170472146
---
## 완료된 작업 (15개 커밋)

### CLI 안정성
- Auth 마커 보강 (authentication_error, failed to authenticate)
- Hook failure 마커 정밀화 ("hook" → "hook_runner.py] failed")
- Codex returncode 처리 (exit 1이어도 유효 응답 성공 처리)
- cli_hook_bridge.py: spec_from_file_location으로 heavy import 우회
- Codex 기본 모델: 빈 문자열 → gpt-5.4 자동 선택
- hook_runner.py: timeout 30→120초, Popen+kill로 자식 프로세스 정리
- settings.local.json: hook timeout 30→120초, 2>/dev/null 제거

### 오케스트레이터
- Stall 임계값 5→15 (AGENT_STALL_THRESHOLD 환경변수)
- 조기 종료 버그: _completed_subtask_keys()가 board 파일도 참조
- max_cycles: 고정 multiplier → phase별 가중치 동적 계산 (scope:8, build:25, code_review:6, cross_validate:6, verify:12)

### 교차검증 파이프라인 (신규)
- Code Reviewer + Cross Validator 역할 자동 투입
- inject_review_tasks(): build 완료 시 board에 리뷰 태스크 원자적 주입
- pick_review_provider(): 작성자와 다른 CLI 선택
- Code Review / Cross Validation Contract 시스템 프롬프트
- Design Review Contract: 설계 변경 시 교차검증 필수

## 미완료 (다음 세션에서 처리)

1. **pick_review_provider() 실제 연결** — 정의만 되어있고 에이전트 dispatch에서 미사용
2. **Blueprint 업데이트** — 이번 세션 core/*.py 변경분 미반영
3. **코드 리뷰 문서** — 이번 세션 변경분 미반영
4. **AF v5 잔여물 삭제** — src/, tests/ (v5가 루트에 생성), project_board_state.json
5. **AF 재실행** — 교차검증 파이프라인 적용 후 lotto 프로젝트 완주 테스트
6. **기존 테스트 실패** — test_cli_providers.py (claude_cli stdin), test_cli_session_adapter.py (hook_runner 경로)

## AF 실행 결과 비교

| 실행 | 완료 | 결과 |
|------|------|------|
| v1 (어제) | 0/18 | 전부 실패 (401+codex_cli_failed) |
| v3 | 4/18 | 조기 종료 (board 동기화) |
| v4 | 6/18 | 조기 종료 (max_cycles) |
| v5 | 12/21 | 모듈 1~3 완료, 2305줄 코드 |

**Why:** 이번 세션에서 "빨리 고치자"에 집중하면서 교차검증/Blueprint/코드리뷰 프로세스를 반복 누락. 다음 세션에서는 코드 수정 → 교차검증 → Blueprint → 커밋 순서를 엄격히 준수해야 함.

**How to apply:** 다음 세션 시작 시 미완료 항목부터 처리. 특히 Blueprint 업데이트와 기존 테스트 수정이 우선.

## 관련
- [[code/symbols]]

