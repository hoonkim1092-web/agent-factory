---
name: project_dogfood_isolation_leak
description: "dogfood T3 격리 누수 진단 — 범인은 control_plane_llm.py os.getcwd(), worker dispatch 무죄"
metadata: 
  node_type: memory
  type: project
  originSessionId: d7fabc0a-82f6-4851-8858-3220874c2b0a
---

dogfood Option 2 T3 acceptance(2026-06-03) = **pipeline codegen 성공 / isolation 실패**.

**증명됨**: ProjectPipeline이 worktree에서 실제 코드 작성 (`moving_average()` + 테스트 10 PASS, run `1780453531-b63cf5fe`).

**깨짐**: merge=never인데 source repo `core/utils.py`+`tests/test_utils.py` 직접 수정됨 (커밋 `90346e95`는 격리실패 산출물 수동 회수).

**원인 진단 (팩트)**:
- worker dispatch **무죄** — runs/*/task.json 22개 전부 `workspace=worktree`
- 진짜 범인 = `core/control_plane_llm.py:122` `workspace=os.getcwd()` (=SOURCE). Lilith stall 복구 LLM 호출이 source 루트에서 claude_cli 실행(파일편집 도구 보유) → source를 worktree와 다른 구현으로 수정 (worktree 11:46 / source 12:06, 350줄 diff).
- 단정 보류: "JSON만 반환" 프롬프트인데 실제 파일 썼는지 transcript 확인 필요. 단 source 수정 가능 유일 claude_cli 경로는 이것 하나.

**다음 작업 (High)**: `control_plane_llm.py:122` os.getcwd() → 호출자 전달 target_workspace로 교체 (generate()에 workspace 인자 추가 + dynamic_orchestrator _lilith_decide_next/_intervene 경로 배선). 또는 오케스트레이터 LLM 의사결정 호출은 파일편집 도구 미장착 격리. 재검증: merge=never면 source git status 무변 단언. Tier3 → review-first.

**부수 수정 완료**: `AF_SKIP_DOMAIN_REVIEW`(`0806ca1c`), DEVELOP git status fallback(`5d0da24f`), provider_detect codex ping `login status`(`aefa8797`). provider는 CLI 세션 로그인 방식(API KEY 아님). 자세히는 NEXT_STEPS.md 상단.

관련: [[project_model_routing_facts]] (provider 라우팅 WI 큐)

## 관련
- [[code/symbols]]

