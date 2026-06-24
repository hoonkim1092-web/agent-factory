---
generated_at: 2026-06-24T23:44:48+09:00
source_commit: e1912719
sources:
  - "docs/code_review/code-review.md"
---

# 2.2 Control Plane (Sidecar 유지보수)

> Source: `docs/code_review/code-review.md:55`
> 관련: [[code_review/index]] | [[review_patterns]] | [[source_refs]]

````markdown
### 2.2 Control Plane (Sidecar 유지보수)

| 파일 | 줄 | 역할 |
|------|-----|------|
| `control/supervisor.py` | 550 | RuntimeSupervisor. heartbeat 30s, stall 120s, root cause analysis |
| `control/maintenance_pipeline.py` | 456 | prepare→execute 2-phase. conflict blocking wait (max 1hr) |
| `control/run_ledger.py` | 310 | append-only JSONL 저널. LedgerEntry dataclass, thread-safe |
| `control/intake.py` | 281 | ControlPlaneIntake. work_kind 분류 → execution_policy |
| `control/change_impact.py` | 298 | 변경 영향도 분석 |
| `control/continuity_snapshot.py` | 293 | 상태 스냅샷 저장/복원 |
| `control/rollback.py` | 412 | 롤백 메커니즘 |
| `control/regression_gate.py` | 243 | 회귀 테스트 게이트 |
| `control/maintenance_state.py` | 233 | 유지보수 상태 머신 |
| `control/lifecycle_bridge.py` | 238 | 실행 라이프사이클 브릿지 |
| `control/execution_policy.py` | 184 | 실행 정책 결정 |
| `control/issue_context.py` | 197 | 이슈 컨텍스트 수집 |
| `control/work_kind.py` | 119 | 작업 종류 분류 (bugfix/feature/maintenance) |
| `control_plane_llm.py` | 173 | CLI-first, API-fallback LLM 인터페이스 |

**문제점:**
- `control_plane_llm.py:50-56`: `detect_available_cli_providers()`만 호출, `AF_CONTROL_PLANE_PROVIDERS` 환경변수 미지원 → v3에서 연동 필요
- `supervisor.py`: ISELoop 미연결 → v3 Phase 1B에서 deep_update 경로 추가
- `run_ledger.py`: 에이전트별 비용 분해 없음 → v3 Phase 2에서 cost buffer 추가
````
