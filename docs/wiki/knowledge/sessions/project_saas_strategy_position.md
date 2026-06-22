---
name: AF SaaS 포지셔닝 — AI Software Delivery OS (Manus 패턴 opt-in 흡수, 2026-05-11 갱신)
description: AF는 Claude/Codex/Manus 실행 에이전트 대체가 아니라 그들을 고용/통제하는 control+quality+memory plane이다. 단 2026-05-11부터 Manus 패턴 (auto-approve 등) opt-in 흡수 시작 — default 게이트 강제는 유지.
type: project
originSessionId: f70bd926-d96e-4d95-8760-12ae1b26f28f
---

## ⚠️ 2026-06-07 정체성 확정 (사용자 명시 — 우선)

사용자가 직접 정정: **"AF는 Manus와 같은 범용 에이전틱 시스템이다 + 기존 대규모 프로젝트에 붙여서 분석/유지보수/기능추가를 자동화하는 프로젝트"**.

- "Claude/Codex/Manus 대체 아님"의 진짜 뜻 = AF는 Claude/Codex CLI를 **백엔드 LLM으로 호출하는** 오케스트레이터(Manus가 내부에서 Claude/Codex로 코딩하는 것과 동일 포지션). 그것들과 경쟁/대체가 아니라 **그 위에서 통제**. 충돌 아님 — 정합.
- 따라서 아래 줄 33의 "Manus류 범용 autonomous worker는 비목표"는 **폐기**. 범용 에이전틱은 목표. 차별점 = (a) control/quality/memory plane 통제 (b) **기존 대규모 코드베이스 부착 분석/유지보수**.
- 함의: STT 앱 같은 신규 제품도 범위 안. 단 verify가 pytest 중심이라 실하드웨어 검증(오디오/GUI)은 자동 루프 밖 — 거긴 사람/Claude 보완. 이건 작업 종류 본질이지 AF 결함 아님(Manus도 동일).

상세: [[project_af_codebase_wiki_direction]]

## ⚠️ 2026-05-11 정책 갱신

**기존**: "Claude/Codex/Manus 대체 아님"
**신규**: "**Manus 패턴 opt-in 흡수, default 게이트 강제 유지**"

변화 근거:
- 사용자가 "Manus처럼 결과물 나오는 거" 요구 (2026-05-11 세션)
- 자율도 정량 분석: AF 50% vs Manus 90% — 큰 차이는 approval_gate에서 발생
- 결정: opt-in 옵션 추가 (default off, 명시 활성 시에만 자율 모드)

이미 적용된 변경:
- `core/approval_gate.py:approve()` `auto: bool = False` + `auto_reason: str = ""` + `AF_AUTO_APPROVE=1` 환경변수 (commit `603dd702`)
- 회귀 테스트 12 PASS, 기존 11 PASS = 23 PASS

⚠️ **알려진 결함** (commit `20e29dc1` cross-review BLOCK 6건):
- Critical 1건: auto-approve가 `verification_blocked` status도 silent 우회 — 가드 미구현
- 5/13 01:00 KST 이후 Codex cross-review 재시도 + BLOCK 흡수 v2 필요

후속 옵션 (NEXT_STEPS 등록):
- agent_runner tool input 우회 (자율도 75%, ~80 LOC)
- headless 모드 (자율도 90% Manus 수준, ~100 LOC)
- 백그라운드 실행 + 결과 알림 (~200 LOC)

---

AF의 SaaS 방향은 **AI Software Delivery OS** — 실행 에이전트(Claude Code, Codex, Manus)를 worker/adapter로 고용하고 control plane + quality plane + memory plane으로 통제하는 시스템이다. Claude Code 대체나 Manus류 범용 autonomous worker는 비목표 (단 자율 패턴은 opt-in으로 일부 흡수).

전략 분석 문서:
- 원본: `docs/참고/2026-04-25-harness-market-agent-factory-saas-strategy.md` (외부 시장 분석 + 7-phase 로드맵)
- 비평: `docs/참고/2026-04-26-harness-strategy-critique.md` (로드맵의 위험 지점 + 재구성된 Step 0~5)

**Why:** 2026-04-25 통합 결함 10건 일괄 수정 직후, 사용자가 "AF가 SaaS로 가치 있나?" 검토를 시작. 원문은 포지셔닝(§1, §4, §10)이 90% 정확하지만 7-phase 로드맵이 평탄(flat)해서 동시 실행 위험 큼. 비평 문서는 Step 0~5로 좁혔음.

**How to apply:**
- AF 신규 기능 설계 시 "control plane / quality plane / memory plane 중 어느 것인가?"를 먼저 묻는다. 셋 다 아니면 범위 밖일 가능성.
- "Phase 1 PR Factory MVP 시작"은 아직 금지. 먼저 Step 0 5건 의사결정 필요:
  1. Worker runtime: BYO local / hosted Docker / Firecracker
  2. Provider 우선순위: Codex App Server / Claude API / Claude Code CLI 중 1개
  3. 첫 ICP repo type (Python/Django? React/Next.js?)
  4. 첫 task type (bug fix? small feature? dep update?)
  5. Pricing model 가설 (seat / accepted-PR / token-passthrough)
- 그 다음 Step 1: `core/events/run_event.py` 통합 schema 스파이크 (tenant_id/project_id/repo_id/run_id/agent_id/cost_event_id 필수)
- Manus-like sandbox, Phase 6 Background Maintenance, Phase 7 Marketplace는 PMF 전 보류
