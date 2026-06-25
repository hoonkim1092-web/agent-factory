---
name: Research 시스템 결함 발견 (2026-05-04, v2 정정)
description: 8인 포커게임 시뮬레이션 vs 실제 코드 검증으로 발견. v2에서 5/6건 정확/부분-정확, 1건은 거짓으로 정정.
type: project
originSessionId: 25bd853b-0179-4231-9c18-b1a26e6bdbae
---
# Research 시스템 결함 발견 — 2026-05-04 (v2)

## v2 정정 (2026-05-04 후속 검증)

v1 6건을 코드 대조 재검증 후 5건으로 축소·재번호. **HIGH-3는 거짓 — 호출됨 (researcher.py:784)**, **MED-6는 테스트 4건 존재**.

## 발견 경위

**Why**: "8인 네트워크 포커게임 만들어줘" 요청에 대한 AF Research 단계 시뮬레이션을 작성한 뒤, 실제 코드(`core/research_router.py`, `core/researcher.py`, `core/research_verifier.py`)와 대조 검증.

**How to apply**: 다음 세션에서 개선 설계 문서를 만들 때 이 5개 결함을 우선순위 순으로 다룬다.

## 정정된 5개 결함

### G1 (구 HIGH-1) — 토큰 셋 한국어 일부 누락
- **위치**: `core/research_router.py:132-169` (7개 frozenset)
- **검증**: "동시접속"은 `_OPERATIONAL_RISK_TOKENS`에 존재. **누락 확인된 토큰**: "최근"(FRESHNESS는 "최신"만), "8인", "공신력". 한국어 자연어 표현 미매칭 우려.
- **개선안**: 누락 토큰 추가 + 띄어쓰기 변형 처리(예: "동시 접속" vs "동시접속") 또는 임베딩 기반 분류 검토.

### G2 (구 HIGH-2) — fast_synthesis가 secondary modes 무시 (실 버그)
- **위치**: `core/researcher.py:690-692`
- **증상**: `if mode == "fast_synthesis": pass` → secondary `requires_web=True`여도 `elif research_plan.requires_web:` 분기 진입 불가
- **개선안**: `if mode == "fast_synthesis" and not research_plan.requires_web: pass` 또는 secondary 모드 직접 체크.

### G3 (구 HIGH-4) — 외부 API 강한 의존성
- **위치**: `core/researcher.py:311, 695, 701` (3개소 `os.getenv("TAVILY_API_KEY")`)
- **증상**: 키 없으면 외부 검색 SKIP → LLM prior 또는 빈 결과
- **개선안**: WebSearch tool(Claude Code/Codex 내장) fallback 추가, 또는 다중 provider 추상화.

### G4 (구 MED-5) — 직렬 실행
- **위치**: `core/researcher.py:654` (collect_project_evidence)
- **증상**: local → web → notebook → synthesize 순차. asyncio/concurrent 미사용
- **개선안**: `concurrent.futures.ThreadPoolExecutor`로 web/local 병렬화 (notebook은 web 결과 의존성 검토).

### G5 (구 MED-6 정정) — structured_evidence claim 최소 개수 보장 부재
- **위치**: `core/researcher.py:406-485` (_synthesize_structured_evidence), `tests/test_research_router_phase1b.py:140-211`
- **검증**: 테스트 4건 **존재** (success/llm_failure/bad_json/research_mode_default). 단 claim 0개일 수 있고 fallback도 빈 배열.
- **개선안**: source 0개 시 fallback empty 유지, source ≥3개일 때 claim ≥N개 보장 retry 또는 LLM prompt 강화.

## v1 → v2 제거 항목

### 제거-A. (구 HIGH-3) "detect_complexity_gaps 미호출 (dead code)" — **거짓**
- 실제: `core/researcher.py:784`에서 호출. `hint_gaps is None` 시 first call이며 max 1 retry. 정상 작동.
- 메모리 v1 주장 위치 (`project_pipeline.py`)에는 없으나 `researcher.py`에서 호출됨.
- 별도 결함 후보: "max retry=1이 의도적 한계 — multi-stage escalation 미지원"은 **결함 아님**, 설계 의도. 추후 필요 시 별도 spec 논의.

## 권장 작업 순서 (v2)

1. **G2 (실버그)** — 가장 작은 변경, secondary modes 무시 픽스
2. **G1 (토큰 보강)** — 즉각 효과, 안전 (테스트만 추가)
3. **G3 (WebSearch fallback)** — 외부 의존성 완화
4. **G5 (claim 최소 개수)** — 신뢰성
5. **G4 (병렬화)** — 응답성, 가장 큰 변경 (last)

## 다음 세션 시작점

**문서 작성**: `docs/plans/2026-05-04-research-system-improvement.md` (오늘 진행)
- 위 5개 결함을 Phase 분할
- 각 Phase별 acceptance criteria
- 8인 포커게임 시나리오 회귀 테스트 명시

**참고 문서**:
- `docs/2026-04-29-research-router-structured-evidence-design.md` (Static Evidence Injection v1)
- `docs/2026-05-03-phase2-verdict-label-spec.md` (Phase 2 verdict)
- `docs/plans/2026-05-03-static-evidence-injection-v1.md`

## 검증 방식

각 개선 작업 후:
- 8인 포커게임 입력 → mode가 deep_source_research/live_project_diagnosis로 분류
- detect_complexity_gaps escalation이 실제 발동하는지 단위 테스트
- evidence_bundle의 web_references 비어있지 않은지 통합 테스트
- TAVILY_API_KEY 미설정 환경에서도 fallback path 검증
