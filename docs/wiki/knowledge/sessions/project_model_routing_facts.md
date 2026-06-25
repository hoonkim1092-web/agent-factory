---
name: provider-4
description: 단일 claude_cli 환경에서 모델 티어링·cross-review가 죽는 코드 메커니즘. /model이 유일 레버. 결함 4건 큐 등록(WI-1~4).
metadata: 
  node_type: memory
  type: project
  originSessionId: 9bc11c07-c498-4c6c-a088-8bce35645c87
---

5턴 deliberation(Claude+Codex 교차, 2026-06-02)으로 코드 확정한 AF 모델/provider 라우팅 메커니즘과 결함.

**코드 사실 (단일 claude_cli 기준):**
- `cli.py:647` `_should_include_model`이 `"claude"` alias를 `--model`에서 제거 → claude CLI default(=사용자 `/model` 설정) 상속. 모델 티어링 死코드.
- `agent_runner.py:1143` `agent.get("preferred_model") or self.mr.pick(...)` — preferred_model이 truthy면 mr.pick 미호출. agents/*.yaml 7/8이 `preferred_model: gemini-3.1-pro-preview` → `AGENT_CHAT_MODEL`/`--model`이 **대부분 agent에서 무력화**. deadbyte만 주석처리라 env override 먹힘.
- `_model_family`(agent_runner.py:274)는 `startswith("claude")`만 인식 → `opus`/`sonnet`/`haiku` 짧은 별칭은 family 실패 → "claude" fallback. `claude-opus-4-8` 같은 full ID만 `--model` 전달됨.
- **유일하게 신뢰 가능한 모델 레버 = claude CLI `/model` 설정** (모든 경로가 거기로 수렴).

**cross-review 이중 단선:**
- 경로 A (pipeline 내부 cross_validate): `available>=2`만 생성(board:1136) + `review_provider` dead metadata(소비처 0, board:1151) + provider_id 입력 누락(dyn_orch:233, `{task_id,owner_role,phase}`만 재구성).
- 경로 B (af-cross-review Tier3 / review_report): 단일이면 critic 1회만(review_report:298,308 `len>=2`). review_runner는 자체 subprocess+--model 없음(:99).
- **단일 provider → vendor 다양성 구조적 불가 → 모델 escalation이 유일 품질 레버**인데 P4.5b 사전강제 미연결(hook_runner:418은 사후 advisory만).

**결함 큐 상태 (WI-1~4 전부 완료 — 2026-06-11 코드 grep 재확인):**
- ✅ WI-1 완료 (`9f4bb071`, 2026-06-04): provider_id 보존
- ✅ WI-2 완료 (2026-06-05): review_provider runtime enforcement. `agent_runner.py:1101-1107` force_provider 처리(미가용 시 `{ok:False}` 명시 실패) + `agent_specializer.py:58-59` review_provider→force_provider 주입. dead metadata 활성화 완료.
- ✅ WI-3 완료 (`7a1a6061`, 2026-06-05): P4.5b 사전강제 + tier 매핑 (resolve_model_id + _inject_model_override + CLAUDE.md 업데이트)
- ✅ WI-4 완료 (2026-06-05): review_runner._run_provider() subprocess.run() 직접호출 → execute_cli_chat(CliChatRequest) 경유 통합. allow_file_edit=False(review-only).
- 공통 제약: "claude" alias는 default 상속 유지, 구체 모델명일 때만 --model.
- ⚠️ **큐 소진**: WI-1~4 전부 완료 → "모델 라우팅 work-item"은 더 이상 미완료 작업이 아니다. 다음 세션에서 이걸 "남은 큐"로 제시하지 말 것.

**운영 (즉시·코드0):** 구현/dogfood 대량호출=`/model sonnet`, 설계/정책/dogfood acceptance=`/model opus`, Tier3 [single-vendor]면 "외부검증 없음"으로 신뢰도↓.

**Why:** 정책(escalation 매트릭스)·의도(provider 다양성)는 코드에 조각으로 존재하나 runtime 연결이 끊김 = "정책 있음, 실행 보장 약함". 단일 provider가 배포 다수면 두 품질 레버 모두 죽은 게 기본 경험 → 배포 동등성 위험([[feedback_pipeline_deploy_parity]]).

**How to apply:** 구현 시점에만 재개(추가 재분석은 메타-재귀, [[project_dev_workflow_paradigm_shift]]). 모델 단계 전환은 [[feedback_model_per_phase]] 따름. NEXT_STEPS 상단 STREAM 블록에 동일 큐 등록됨.
