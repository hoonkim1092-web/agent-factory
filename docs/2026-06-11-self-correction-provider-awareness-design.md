# 자가수정 brain Provider-Awareness — gemini API 하드와이어 제거 설계

- 작성일: 2026-06-11
- 작성자: Claude (Opus 4.8)
- 상태: Draft → af-cross-review 대기
- 관련 메모리: `project_model_routing_facts`, `project_router_research_decoupling`, `feedback_design_review_mandatory`
- Blueprint 영향: §3 자가수정 서브시스템(ISE/FSA), §12 변경 이력

---

## 0. 한 줄 요약

FSA/ISE 자가수정의 "두뇌" 3개(`ISEAnalyzer`·`ISERedesigner`·`StrategyEvaluator`)가 **gemini API 키 전용 `LLMEngine`에 하드와이어**돼 있어, CLI-로그인 환경(claude만 로그인)에서는 `engine_api_keys_disabled()` 마스킹에 걸려 **영구히 휴리스틱으로 눈을 감고 작동**한다. 이 3개를 이미 존재하는 provider-aware `ControlPlaneLLM`(claude>gemini>codex 자동 선택+fallback)으로 교체한다.

---

## 1. 문제 (실제 코드 baseline — grep 확정)

### 1.1 현상

- `ISEAnalyzer.__init__` (`core/ise_analyzer.py:67-68`): `self.llm = LLMEngine(model_name="gemini-1.5-pro-latest")`
- `ISERedesigner.__init__` (`core/ise_redesigner.py:48-49`): 동일
- `StrategyEvaluator.__init__` (`core/evaluator.py:15-16`): 동일

세 클래스가 LLM에 부르는 메서드는 `generate(prompt)`와 `generate_json(prompt)` **둘뿐**이다 (`ise_analyzer.py:208`, `ise_redesigner.py:101/162/220`, `evaluator.py:51/56`).

### 1.2 왜 눈을 감는가 — 마스킹 메커니즘

`LLMEngine`은 gemini API 키(`GOOGLE_API_KEY`/`GEMINI_API_KEY`) 기반이다 (`core/llm_engine.py:136-143`). 키가 없으면 `self._client = None` → `_execute_with_retry`가 `"No GOOGLE_API_KEY configured"` 발생 → `generate()`는 `""`, `generate_json()`은 `{}` 반환.

그런데 키 로딩은 `get_engine_api_key("google")`(`llm_engine.py:31`)를 거치고, 이 함수는 `engine_api_keys_disabled()`가 True면 **무조건 ""를 반환**한다 (`core/providers/registry.py:104-105`). 그리고:

```python
# registry.py:96-100
def engine_api_keys_disabled(raw_provider=None) -> bool:
    override = os.getenv("AGENT_DISABLE_ENGINE_API_KEYS")
    if override is not None:
        return _env_truthy(override, default=False)
    return supports_cli_bootstrap(raw_provider)   # CLI 부트스트랩 가능하면 True
```

즉 **CLI 부트스트랩이 가능한 환경(=CLI 로그인이 정상 경로)에서는 gemini API 키가 강제 마스킹**된다. 결과:

```
CLI-로그인 환경 (claude_cli 로그인, GOOGLE_API_KEY 없음/마스킹)
  → LLMEngine._client = None
  → ISEAnalyzer._llm_analyze() → generate() → ""
  → analyze_failure()가 휴리스틱 기본값으로 폴백 (ise_analyzer.py:91-92 `if llm_analysis:`)
  → FSA/ISE는 죽지 않지만 LLM 판단 없이 5 cycle을 헛돈다
```

**확인된 현재 환경 사실**: `GOOGLE_API_KEY`/`GEMINI_API_KEY` 환경변수 = **NONE** (이 PC). → 자가수정 brain이 **지금 이 순간 full/야간 파이프라인에서 이미 눈을 감고 작동 중**이다. 이건 light를 위한 가상의 미래 문제가 아니라 **현재 실재하는 degradation**이다.

### 1.3 왜 "고쳤는데 또 나오는가" (사용자 관찰의 정체)

시스템 전체 방향은 "engine API 키 → CLI 로그인 이전"이었다:

| 커밋 | 이전시킨 모듈 |
|------|--------------|
| `ebb9a0ba` | engine_api_keys_disabled 도입 (CLI providers용 마스킹) |
| `039e55f1` | `provider_detect.py` — API 키 없는 gemini/codex → NOT_INSTALLED |
| `aefa8797` | `provider_detect.py` — 잘못된 API KEY 체크 제거, codex 실로그인 확인 |

`provider_detect.py`(=메인 에이전트 실행 경로의 CLI 감지)는 이전됐다. **그러나 `ise_analyzer.py`/`ise_redesigner.py`/`evaluator.py`는 위 어느 커밋에도 포함되지 않았다** (`git log -- core/ise_analyzer.py` 확인 — 마지막 변경은 `6b53412c` ISE 배선 복구로 LLM 백엔드 무관).

→ 사용자가 이전 세션에 고친 것은 **CLI 감지 경로(provider_detect)**였고, gemini API 키가 다시 나오는 곳은 **그것과 별개인 자가수정 brain(LLMEngine)**이다. 같은 히드라의 다른 머리.

---

## 2. 해법 — 이미 존재하는 provider-aware 부품으로 교체

사용자가 원한 "로그인된 프로바이더 중 지능형 선택 + gemini 만료 시 다른 프로바이더 fallback"은 **신규 구현이 아니라 `core/control_plane_llm.py`로 이미 존재**한다:

```
ControlPlaneLLM (control_plane_llm.py)
  _init_providers():
    - AF_CONTROL_PLANE_PROVIDERS env 우선
    - 없으면 detect_available_cli_providers()로 자동 감지
    - CLI 0개 + gemini 키 있을 때만 LLMEngine(API) 폴백 준비
  _generate_via_cli():
    - 우선순위 claude_cli > gemini_cli > codex_cli (_PREFERENCE)
    - INFRA 실패 시 다음 provider로 자동 fallback (exclude set 순회)
  generate(prompt) -> str           # 헤더 주석: "Public API (LLMEngine 호환)"
  generate_json(prompt, schema) -> dict
```

### 2.1 인터페이스 일치 (drop-in 확인)

| 메서드 | LLMEngine | ControlPlaneLLM | ISE 3개가 호출? |
|--------|-----------|-----------------|-----------------|
| `generate(prompt)` | ✅ | ✅ | ✅ |
| `generate_json(prompt, schema)` | ✅ | ✅ | ✅ (evaluator만) |

세 클래스가 부르는 메서드가 정확히 이 둘뿐이므로 **생성자 1줄 교체로 drop-in** 가능.

### 2.2 변경 (3곳, 각 1줄)

```python
# ise_analyzer.py:68
- self.llm = LLMEngine(model_name=model_name)
+ self.llm = ControlPlaneLLM(model_name=model_name)

# ise_redesigner.py:49 — 동일
# evaluator.py:16 — 동일
```

+ import 교체 (`from core.control_plane_llm import ControlPlaneLLM`).

### 2.3 default model_name 처리 (결정 필요)

세 `__init__`의 default `model_name="gemini-1.5-pro-latest"`는 `ControlPlaneLLM`에 넘어가도 **CLI 경로에선 무시**된다(`_generate_via_cli`는 `default_chat_model_for_provider(provider_id)` 사용, `control_plane_llm.py:111`). gemini 모델명은 오직 API 폴백(`_api_engine`)에서만 의미. 따라서 harmless이나 **혼란 방지를 위해 default를 `None`으로 변경 권장** (provider가 자기 default 모델 선택).

- **결정 D1**: default `"gemini-1.5-pro-latest"` → `None`. (단, `fsa_loop.py:87-89`가 `runner.mr.pick("evaluator")` 결과를 넘기는 경로는 유지 — 그쪽은 명시 model 지정이므로 보존.)

---

## 3. Blast Radius (정직한 범위)

세 클래스는 light 전용이 아니라 **자가수정 시스템 전체가 공유**한다 (`grep -rln`).

### 3.1 수정은 클래스 내부 1줄 — 모든 소비처 자동 커버 (cross-review #1 정정)

**핵심**: 교체는 호출처가 아니라 **클래스 `__init__` 내부**(`self.llm = LLMEngine(...)` → `ControlPlaneLLM(...)`)에서 일어난다. 따라서 그 클래스를 생성하는 **모든 소비처가 수정 없이 자동으로 ControlPlaneLLM을 쓴다.** 호출처 수정 0건.

`StrategyEvaluator` 생성처 전수 (`grep -rn "StrategyEvaluator(" core/ --include=*.py`, test 제외):

| 생성처 | 호출 형태 | 교체 후 |
|--------|----------|--------|
| `core/control/supervisor.py:399` | `StrategyEvaluator()` | 클래스 내부 변경으로 **자동 커버** (호출처 수정 불필요) |
| `core/dynamic_orchestrator.py:78` | `StrategyEvaluator(model_name=engine_id)` | **자동 커버** (model_name은 API폴백 전용, CLI경로 무시) |
| `core/fsa_loop.py:95` | `StrategyEvaluator(model_name=model_name)` | **자동 커버** |

→ cross-review가 supervisor:399/dynamic_orchestrator:78을 "교체 범위 밖이라 여전히 LLMEngine 사용"으로 본 것은 오독이다. 셋 다 `StrategyEvaluator`를 생성할 뿐 `LLMEngine`을 직접 만들지 않으므로, `evaluator.py:16` 한 줄 수정이 세 생성처를 동시에 커버한다. ISEAnalyzer/ISERedesigner도 동일 — 생성처가 어디든 클래스 내부 교체로 자동 적용.

### 3.2 소비 경로 (직접 수혜자)

| 소비처 | 역할 | 두뇌 |
|--------|------|------|
| `fsa_loop.py` | FSA (full dogfood + 야간) | ISEAnalyzer·ISERedesigner·StrategyEvaluator 전부 |
| `dynamic_orchestrator.py` | full 오케스트레이션 | StrategyEvaluator |
| `core/control/supervisor.py` | 감독 루프 | StrategyEvaluator |

→ **core/ Tier 3 변경**. light는 이 brain을 (아직) 호출조차 안 하므로, 이 설계의 직접 수혜자는 **오늘 돌고 있는 full/야간 FSA·ISE**다. 즉 light-FSA 배선과 **독립**이며 그보다 **우선**한다(두뇌를 먼저 켜야 light가 불러도 의미 있음).

---

## 4. 불변식 (테스트로 강제)

- **INV-1 (provider-aware)**: CLI provider 1개 이상 감지되면 ISEAnalyzer/Redesigner/Evaluator의 LLM 호출이 `LLMEngine`(gemini API)가 아니라 CLI 경로를 탄다. (mock `detect_available_cli_providers`→`["claude_cli"]`, `execute_cli_chat` spy로 호출 검증)
- **INV-2 (fallback)**: 우선순위 provider가 INFRA 실패면 다음 provider로 자동 이행. (claude_cli INFRA → codex_cli 성공 → 결과 반환)
- **INV-3 (graceful degrade 보존)**: CLI 0개 + API 키 0개여도 **예외 없이** `generate()→""`, `generate_json()→{}` 반환, ISEAnalyzer는 휴리스틱 폴백 (현행 동작 회귀 보호).
- **INV-4 (인터페이스 불변)**: `generate`/`generate_json` 시그니처·반환타입 무변. 실제 호출 현황 — `generate`: ISEAnalyzer(`:208`)·ISERedesigner(`:101/162/220`)·StrategyEvaluator(`:51`) / `generate_json`: StrategyEvaluator(`:56`)만. 호출부 수정 0.
- **INV-5 (하드코딩 금지)**: 교체 후 세 모듈에 `LLMEngine(` 직접 생성 0건 (단 `fsa_loop.py:87` evaluator model pick 경로는 model_name 전달만, LLMEngine 생성 아님).
- **INV-6 (생성처 자동 커버)**: `StrategyEvaluator()`를 생성하는 3곳(`supervisor.py:399`·`dynamic_orchestrator.py:78`·`fsa_loop.py:95`) 인스턴스의 `.llm`이 교체 후 전부 `ControlPlaneLLM` 타입. (호출처 수정 없이 클래스 내부 교체로 커버됨을 isinstance로 검증)

---

## 5. 동작 변화 (의도된 — 명시 의무)

- **이전**: CLI 환경에서 분석/재설계가 "공짜 휴리스틱" (LLM 미호출).
- **이후**: 동일 상황에서 **실제 claude_cli LLM 호출** 발생 → 분석 품질↑, **단 cycle당 LLM 호출 비용 발생**.
- FSA는 cycle당 analyze + redesign + retry이므로, brain이 켜지면 cycle당 LLM 호출이 늘어난다. `max_cycles=5` 캡은 그대로라 상한은 유지. RunBudget 가드(`fsa_loop.py:166-172`)도 그대로 동작.

→ 이건 결함이 아니라 **자가수정이 실제로 일하게 되는 것**. 다만 비용 프로파일이 바뀌므로 리뷰·릴리즈 노트에 명시.

---

## 6. 비-목표 (이번 설계 범위 밖)

- light → FSA 인계 배선 (별도 작업, 이 설계 머지 후 게이트 재평가).
- `LLMEngine` 자체 제거/리팩토링 (다른 13개 소비처 존재 — `bootstrap_roles`, `consensus_engine`, `role_decomposer`, `skill_*` 등. 범위 폭발 방지로 **이번엔 ISE 3개만**).
- `engine_api_keys_disabled` 마스킹 정책 변경 (의도된 정책이므로 유지 — 우리는 brain을 CLI 경로로 옮길 뿐).

---

## 7. 구현 순서 (test-first, 재설계 금지)

```
1. RED: tests/test_ise_provider_awareness.py 신규
   - INV-1: detect_available_cli_providers mock=["claude_cli"], execute_cli_chat spy
            → ISEAnalyzer.analyze_failure가 CLI 경로 호출 검증
   - INV-2: claude_cli INFRA → codex_cli 성공 fallback
   - INV-3: CLI 0 + key 0 → 예외 없음, 휴리스틱 폴백
   - INV-5: ise_analyzer/redesigner/evaluator에 LLMEngine( 직접생성 0건 (소스 스캔)
   → 현재 RED

2. GREEN: ise_analyzer.py:68 / ise_redesigner.py:49 / evaluator.py:16
   LLMEngine → ControlPlaneLLM 교체 + import + default None (D1)

3. 회귀: 기존 ISE/FSA 테스트 전체 PASS 확인
   (tests/test_fsa_*.py, tests/test_ise_*.py, test_dynamic_orchestrator*)

4. test_coding_conventions 통과 확인

5. 3-Tier: af-critic → af-cross-review → af-test-runner

6. Blueprint §3(자가수정 brain LLM 백엔드)+§12 같은 커밋
```

---

## 8. 미해결 결정 (cross-review 전 사용자 확인)

- **D1**: default model_name `"gemini-1.5-pro-latest"` → `None` 교체 동의? (권장: Yes — 혼란 제거)
- **D2**: 범위를 ISE 3개로 한정 동의? (다른 10개 LLMEngine 소비처는 별도 평가) — 권장: Yes (blast radius 통제)
- **D3**: 동작 변화(휴리스틱→실제 LLM 호출, 비용↑)를 수용? — 권장: Yes (자가수정 본래 목적)

---

## 9. 검증된 baseline (cross-review용 — stale 방지)

- `core/ise_analyzer.py:67-68`, `core/ise_redesigner.py:48-49`, `core/evaluator.py:15-16` = `LLMEngine(model_name="gemini-1.5-pro-latest")` 3건.
- `core/llm_engine.py:31,136-143` = gemini API 키 기반, 키 없으면 `_client=None`.
- `core/providers/registry.py:96-100,104-105` = `engine_api_keys_disabled()` True 시 키 마스킹.
- `core/control_plane_llm.py:50-78,147-179` = CLI 자동감지+우선순위+fallback, `generate`/`generate_json` LLMEngine 호환.
- 현재 환경: `GOOGLE_API_KEY`/`GEMINI_API_KEY` = NONE (grep 확인).
- 이전 fix 커밋 `aefa8797`/`039e55f1` = `provider_detect.py`만 변경, ISE/LLMEngine 미포함 (`git show --stat` 확인).
