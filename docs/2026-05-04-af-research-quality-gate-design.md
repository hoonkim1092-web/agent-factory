# AF Research Quality Gate — 통합 설계문서

> **작성**: 2026-05-04
> **상위 진단**: `docs/2026-05-04-poker-scenario-af-vs-manus-gap-analysis.md` (§7 후속 합의)
> **codex 원본**: `docs/Minus/codex_my_의견.md`
> **작성 모델**: Opus 4.7 (설계 단계, 메모리 `feedback_model_per_phase`)
> **상태**: **신규 — 작성 직후 hook 큐 자동 발화 → af-cross-review 1회 (단일 설계문서, CLAUDE.md)**

---

## §0. 다음 세션 진입 가이드 (cold-start)

> 본 문서는 self-contained. gap-analysis 문서를 못 봐도 본 문서만으로 작업 진입 가능하게 작성됨.

**입장 순서**:

1. `git pull --ff-only` + `python start_db.py agent-factory` (PC 바뀐 경우 / 4h+ 공백 / 직전 hook 발화 후 종료된 경우)
2. 본 문서 §1·§2·§5·§6·§11 읽기 (§3·§4·§7·§8·§9·§10은 보조)
3. cross-review verdict 확인:
   - `WARN` 이하 → P0 착수 (Sonnet 모델 권장, 메모리 `feedback_model_per_phase`)
   - `BLOCK` → 본 문서 갱신 후 재발화
4. P0 완료 후 동일 포커 build prompt 재실행 → §3 정량 목표 1·2 달성 확인 후 P1 진입
5. codex 회복 시점 (2026-05-05 15:37 KST↑) 이후 본 문서에 fan-out 포함 cross-review 1회 추가 권장

**현재 상태 요약** (2026-05-04 기준):
- 진단 완료, codex 의견 통합 완료, 의사결정 9건 (D1~D9) 합의 완료
- 코드는 **아직 변경되지 않음** — 본 문서가 P0 착수의 입력
- 산출물 양식 분기 (intent-routed output formats) 폐기 — 격차의 본체는 양식이 아니라 evidence depth + 도메인 명세 강제 부재

---

## §1. 배경

### 1.1 핵심 격차 (한 문장)

**AF는 "구현하기 위해 작업을 분해"하는 쪽에 강하고, Manus는 "계획을 만들기 위해 리서치"하는 쪽에 강하다. 같은 build prompt에서 같은 양식이라도 evidence 깊이가 다르면 산출 품질 격차가 80% 발생한다.**

### 1.2 진단 변천 — gap-analysis §7 정정 흡수

초기 진단(gap-analysis §3·§4)은 **양식 분기 (intent-routed output formats)** 를 본질 처방으로 봤다. 이는 잘못된 진단:

- 사용자가 "시뮬레이션 해서 알려줘"라 입력한 건 **AF 정상 작동 테스트 메타 명령**이었음
- 진짜 의도는 처음부터 끝까지 **build** ("8인 네트워크 포커게임 만들기")
- 빌드 배포본에 build prompt를 직접 입력해도 동일한 4-doc 보일러플레이트 산출 → 양식 분기와 무관
- **격차의 본체** = build intent 안에서 evidence depth, 도메인 명세 강제, 권위 출처 우선 부재

→ 양식 분기 폐기, **codex의 Research Quality Gate가 본체 처방**.

### 1.3 codex 의견 통합

codex가 제안한 5개 컴포넌트:

| codex 컴포넌트 | 역할 |
|---|---|
| ResearchFirstPlanner | 요구사항에서 리서치 필요성 판정 (`requires_research / domain / depth`) |
| EvidenceMatrix | claim ↔ source 구조화 매핑 (`{claim, source_id, authority, confidence, applies_to}`) |
| CoverageGate | 매니페스트 필수 항목 미충족 시 계획 생성 차단 |
| RecoverySearchLoop | 부족 항목만 재수집 (max_rounds 캡) |
| SpecBeforeTasks | 도메인 명세 생성 후에만 task board 생성 허용 |

**결론**: 본 5종은 신규 거대 모듈 신설이 아니라 **AF 기존 함수들의 강도 보강 + 신규 모듈 ≤ 2개**로 80% 달성 가능 (gap-analysis §7.2 grep 검증).

---

## §2. AF 코드 매핑

### 2.1 codex 컴포넌트 vs AF 현재 (검증 완료)

| codex 컴포넌트 | AF 현재 | 코드 위치 (HEAD) | 강도 |
|---|---|---|---|
| ResearchFirstPlanner | 부분 구현 | `core/research_router.py:194 plan()` | soft (mode 분류만, `requires_research` flag 없음) |
| EvidenceMatrix | 부분 구현 | `core/researcher.py:672 collect_project_evidence()` + source_pack | soft (claim↔source 매핑 아닌 reference list) |
| CoverageGate | 부분 구현 | `core/researcher.py:550 _is_sufficient()` | soft (ref ≥ 3 / score ≥ 0.25 하드코드, 도메인 매니페스트 부재) |
| RecoverySearchLoop | **부재** | (1회 escalation만) | 부재 (loop 아님) |
| SpecBeforeTasks | **부재** | `core/project_pipeline.py:741 prepare_documents()` | 부재 (brief→role_plan→task_board→work_items 직행) |
| 권위 출처 우선 | **부재** | `core/researcher.py:311 _collect_web_references()` | 부재 (Tavily top-k만, trust_score 없음) |

### 2.2 핵심 함수 시그니처 (P0~P2 수정 대상)

```python
# core/researcher.py
def _collect_local_references(self, task_input: str, workspace: str, limit: int = 6) -> list[dict]: ...   # :258
def _collect_web_references(self, task_input: str, limit: int = 4) -> list[dict]: ...                       # :311
def _is_sufficient(self, local_refs: list[dict], task_input: str) -> bool: ...                              # :550
def collect_project_evidence(self, task_input: str, workspace: str | None = None, ...) -> dict: ...         # :672
def research_project_brief(self, agent: dict, task_input: str, workspace: str | None = None,                # :919
                           evidence_bundle: dict | None = None) -> dict: ...

# core/research_router.py
@dataclass
class ResearchPlan:                                                                                          # :78
    mode: str
    secondary_modes: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
    reason: str = ""
    requires_web: bool = False
    requires_tavily_extract: bool = False
    requires_notebooklm: bool = False
    requires_deep_source_pack: bool = False
    risk_level: str = "normal"
    # ↓ P0 A5에서 추가
    # requires_research: bool = False
    # domain: str = ""           # "" | "poker" | "<future>"
    # research_depth: str = "shallow"  # shallow | normal | deep

def plan(self, request: str) -> ResearchPlan: ...                                                            # :194

# core/project_pipeline.py
def prepare_documents(self, ...): ...                                                                        # :741

# core/work_item_generator.py — 4 generator (수정 불요. brief에 original_request 추가만으로 자동 흐름)
def _generate_feature_plan(...): ...                                                                         # :522
def _generate_feature_spec(...): ...                                                                         # :561
def _generate_implementation_design(...): ...                                                                # :599
def _generate_implementation_tasks(...): ...                                                                 # :635

# core/plan_verifier.py
"original_request": str(task_input or "").strip(),                                                           # :200 (이미 보존 중 — 흐름만 missing)
```

### 2.3 의외의 발견

`work_item_generator._generate_feature_plan/spec/design/tasks` 4 함수는 모두 `json.dumps(project_brief)` **전체**를 prompt에 주입한다 (gap-analysis §7.2). 즉:

> **`project_brief`에 `original_request` 필드만 추가하면 4 generator가 자동으로 prompt에 포함시킨다. 4 generator 함수 자체는 수정 불필요.**

이게 P0 A1을 1줄 수정으로 만든다.

---

## §3. 목표 (정량)

다음 3개를 모두 만족할 때 본 설계의 P0~P3 완수로 본다.

| ID | 지표 | 측정 | 목표 |
|---|---|---|---|
| **G1** | gap-analysis §2 비교표 9차원 (사용자 원본 보존, 인원수, 네트워크/서버권위, HTML5/앱웹/반응형, 룰 출처, 포커 족보·블라인드·배팅룰, 6 phase 시뮬레이션, Tech Stack, 즉시 개발 가능성) | 동일 포커 build prompt 재실행 후 plan/spec/design/tasks 4-doc 점검 | **≥ 7개 차원에서 Manus 동등 이상** |
| **G2** | poker.yaml 매니페스트 8 필수 항목 (§7) | coverage-report에서 `matched / total` 카운트 | **≥ 7/8 matched** (단일 라운드 내) |
| **G3** | assistant_score 메모리 평균 (현재 0.32~0.46) | `projects/global_hoon_main/data/memory/general/assistant_score/*` 최근 10건 평균 | **≥ 0.7** |

**검증 시점**: P3에서 일괄. P0~P2 각 단계는 **자기 검증 기준**(§5)만 통과하면 다음 phase로 진행.

---

## §4. 비목표 (Non-Goals)

본 설계가 **하지 않는 것**:

1. ~~Intent-routed 산출 양식 분기 (simulation/walkthrough/analyze 양식 신설)~~ — **폐기** (§1.2 사유)
2. ~~포커 외 도메인 매니페스트 일괄 작성~~ — D4: **poker 1개만**. 두 번째 매니페스트는 두 번째 케이스 발생 시 (Karpathy "Simplicity First")
3. ~~100% 자동화 (사용자 개입 0)~~ — Coverage Gate가 BLOCK하면 **명시적 사용자 결정** 필요. 자동 wing-it 금지
4. ~~기존 work-item 4-doc 양식 변경~~ — feature-plan/spec/design/tasks **양식 그대로** 유지. evidence 깊이만 강화
5. ~~research_router의 mode 분류 알고리즘 재설계~~ — `_compute_signal_scores` (§4.2 7개 신호) **그대로**. `requires_research / domain / depth` flag만 추가
6. ~~plan_verifier 재설계~~ — 이미 `original_request` 보존 중 (`:200`). researcher.py 흐름만 연결
7. ~~CLI provider 변경 / build/install 변경~~ — 본 설계는 코어 데이터 흐름만 다룸

---

## §5. 단계 트리 (P0~P3) — gap-analysis §7.3 흡수

> 직렬 의존성. P0 미완료 시 P1 착수 금지 (D7 사유).

### 5.1 P0 — 즉시 (1-2일, 신규 모듈 0개, 후방 호환)

#### A1. `original_request` 전문 보존 + 자동 주입

**위치**: `core/researcher.py:829 _merge_project_brief_evidence()` — 정상 경로 + fallback 경로 **모두 통과하는 공통 함수**에 override 삽입

**원칙**: verbatim 보존은 **LLM이 아니라 Python 코드가 책임진다**. LLM에게 "한국어 4줄을 JSON 문자열로 복사해라"라 시키면 escaping/truncation/reformatting 위험이 있어 한국어 verbatim 충실도가 깨진다 (gap-analysis §4 ① 원안: "researcher가 task_input 그대로 보존"). schema 안내는 단지 LLM이 다른 필드를 파괴하지 않게 하기 위한 docstring.

**반환 경로 분석** (`research_project_brief()`:997-1011):
- **정상 경로** (`:1004→1009`): `data = safe_json_load(...)` → `data = self._merge_project_brief_evidence(data, task_input, evidence)` → `return data`
- **fallback 경로** (`:1011`): `return self._merge_project_brief_evidence(self._fallback_project_brief(task_input), task_input, evidence)`
- **결론**: 두 경로 모두 `_merge_project_brief_evidence()`를 경유 → 여기에 1줄만 추가하면 100% 커버

**변경 (2단계, 둘 다 필수)**:

**(a) prompt JSON schema에 1줄 추가** (LLM에게 필드 존재 알림, `:963` 부근):
```python
{
  "original_request": "(will be overwritten verbatim by Python — leave empty or echo task_input)",
  "goal": "single sentence describing what to build",
  ...
}
```

**(b) `_merge_project_brief_evidence()` 첫 줄에 unconditional override** (`:830` 직후):
```python
def _merge_project_brief_evidence(self, brief: dict, task_input: str, evidence_bundle: dict | None) -> dict:
    data = dict(brief or {})
    data["original_request"] = task_input    # ← unconditional override — 정상+fallback 양 경로 커버
    ...  # 기존 나머지 코드
```

**왜 `_merge_project_brief_evidence` 내부인가**:
- `research_project_brief()`의 정상 경로와 fallback 경로 모두 이 함수를 통과
- 1곳 수정으로 두 경로 동시 커버 (중복 override 불필요)
- `if not brief.get(...)` fallback은 LLM이 잘못된 값을 채워넣은 경우 (truncated / reformatted / escaped 한국어) 무력화됨 → unconditional 필수
- task_input은 함수 인자로 이미 들어와있어 비용 0

**검증**: 동일 포커 build prompt 실행 후
- `project_brief["original_request"]` 가 한국어 4줄(38\~42자/줄) 원본과 **byte-for-byte 일치**
- LLM 응답을 mock으로 빈 문자열·축약·번역 변형 등 4종 주입한 단위 테스트에서 모두 verbatim 유지

**왜 work_item_generator 4 함수가 자동인가**: 4 함수가 `json.dumps(project_brief)` **전체**를 prompt에 주입하므로 (§2.3) brief에만 들어있으면 4-doc prompt에 자동 흐름.

> **2026-05-04 cross-review BLOCK #1 반영**: 초기 안 ("schema 1줄만 추가, fallback override")이 §4 ① post-LLM injection 원안을 약화시킨다는 비판 수용. **schema + unconditional override 2단계로 강화**.
> **2026-05-04 cross-review BLOCK #2 반영**: override 위치를 `research_project_brief()` 정상 경로 단독 → `_merge_project_brief_evidence()` 공통 함수로 이동. fallback 경로(`:1011`) 커버리지 보장.

---

#### A2. Local references 도메인 매칭 가드

**위치**: `core/researcher.py:258 _collect_local_references()`

**변경**: BM25 결과 반환 직전에 도메인 키워드 매칭 가드 1단:
```python
def _collect_local_references(self, task_input: str, workspace: str, limit: int = 6) -> list[dict]:
    refs = ...  # 기존 BM25 결과
    domain_tokens = self._extract_domain_tokens(task_input)  # 신규 helper, stopword 제거 + len ≥ 3
    if domain_tokens:
        refs = [r for r in refs if any(
            tok in (r.get("excerpt") or "").lower() + " " + (r.get("heading") or "").lower()
            for tok in domain_tokens
        )]
    return refs[:limit]
```

**helper**: `_extract_domain_tokens(text) -> set[str]` — 한국어/영문 stopword 제거 후 길이 ≥ 3인 토큰. 외부 라이브러리 의존 X.

**검증**: 포커 build prompt 실행 시 plan.md References에 `docs/architecture.md` 등 자기참조 노이즈가 더 이상 인용되지 않음.

---

#### A3. Web references — 권위 출처 trust_score + poker 화이트리스트

**위치**: `core/researcher.py:311 _collect_web_references()`

**변경**:
- 도메인 화이트리스트 정의 (모듈 상단 상수):
  ```python
  _AUTHORITY_DOMAINS_POKER = (
      "wsop.com", "pokertda.com", "pokerstars.com",
      "upswingpoker.com", "pokernews.com",
  )
  ```
- Tavily 결과 ref dict에 `trust_score`(0.0~1.0) 추가. 화이트리스트 매칭 시 `+0.4`, 그 외 `0.0` 베이스
- score 정렬 시 `score * (1 + trust_score)` 보정 후 top-k

**향후 확장**: `domain` 매개변수가 들어오면 `_AUTHORITY_DOMAINS_<DOMAIN>` 선택 (P1 B3에서 사용).

**검증**: Tavily 키 설정 환경에서 포커 build prompt 실행 시 web_references 상위 4건에 `wsop.com` 또는 `pokertda.com` 또는 `upswingpoker.com` 중 ≥ 1건 포함.

---

#### A4. `_is_sufficient` domain_checklist 옵션 매개변수 (P1 토대)

**위치**: `core/researcher.py:550 _is_sufficient()`

**변경 (후방 호환)**:
```python
def _is_sufficient(
    self,
    local_refs: list[dict],
    task_input: str,
    domain_checklist: list[str] | None = None,  # ← 추가, default None
) -> bool:
    # 기존 4 조건 (ref≥3 / avg score≥0.25 / has_content / freshness 키워드) 유지
    ...
    # P1에서 활성화: 매니페스트 필수 항목 매칭 검사
    if domain_checklist:
        joined = " ".join(
            (r.get("excerpt") or "") + " " + (r.get("heading") or "")
            for r in local_refs
        ).lower()
        matched = sum(1 for item in domain_checklist if item.lower() in joined)
        if matched < len(domain_checklist) * 0.7:  # 70% 매칭 임계
            return False
    return True
```

**P0에서는 호출자가 `domain_checklist=None`으로만 호출** → 동작 변화 없음. P1에서 활성화.

**검증**: 기존 7 PASS 테스트가 그대로 통과 (후방 호환).

---

#### A5. ResearchPlan에 `requires_research / domain / depth` 추가

**위치**: `core/research_router.py:78 ResearchPlan dataclass + :194 plan()`

**변경**:
```python
@dataclass
class ResearchPlan:
    mode: str
    # ... 기존 8 필드
    requires_research: bool = False     # ← 추가
    domain: str = ""                    # ← 추가, "" | "poker" | <future>
    research_depth: str = "shallow"     # ← 추가, shallow | normal | deep
```

`plan()` 메서드는 `_select_mode` 결과에 다음 derivation 추가:
- `requires_research = mode in ("deep_source_research", "live_project_analysis")` 또는 `external_stack_score >= 2`
- `domain = self._detect_domain(request)` — 키워드 기반 (`"포커" / "poker" / "hold'em"` 등 → `"poker"`, 그 외 `""`)
- `research_depth = "deep" if requires_research and operational_risk_score >= 3 else ("normal" if requires_research else "shallow")`

**`_detect_domain(request) -> str`**: 신규 private helper. 포커 토큰셋 1개만 정의 (D4):
```python
_POKER_TOKENS = frozenset({"포커", "poker", "hold'em", "holdem", "blind", "blinds", "all-in"})
```
다른 도메인 토큰셋은 두 번째 매니페스트가 필요해질 때 추가.

**검증**: 포커 build prompt → `plan.requires_research=True / domain="poker" / research_depth in ("normal","deep")`. 일반 build prompt (예: "make a TODO app") → `domain=""`.

---

#### A6. `project_brief.json` 파일 저장

**위치**: `core/researcher.py` `research_project_brief()` 반환 직전, 또는 `core/project_pipeline.py` `prepare_documents()` brief 수신 직후

**변경**: brief dict를 `docs/research/<slug>-project-brief.json` 으로 저장.
- slug 생성: 기존 work-item slug 로직 재활용 (`work_item_generator` 또는 `project_pipeline`에 이미 존재)
- 디렉토리 미존재 시 `mkdir(parents=True, exist_ok=True)`

**검증**: 포커 build prompt 실행 후 `docs/research/<slug>-project-brief.json` 파일 존재 + `original_request` 필드에 사용자 원본 전문 포함.

---

#### P0 자기 검증 기준 (다음 phase 진입 조건)

- [ ] A1: 동일 포커 build prompt 결과의 `project_brief["original_request"]` 에 사용자 한국어 원본 4줄 포함
- [ ] A2: plan.md References에 `docs/architecture.md` 자기참조 노이즈 없음
- [ ] A3: Tavily 환경에서 web_references 상위 4건 중 권위 도메인 ≥ 1건
- [ ] A4: 기존 researcher 테스트 (`test_g3_*`, `test_g5_*` 등) 그대로 통과
- [ ] A5: `plan(포커 prompt).domain == "poker"` 단위 테스트 1건 추가 후 PASS
- [ ] A6: `docs/research/<slug>-project-brief.json` 파일 디스크 존재 + JSON 파싱 성공
- [ ] G1 (gap-analysis §2 비교표 9차원) 중 ≥ 4개 차원이 Manus 동등으로 개선 (사용자 원본 보존, 인원수, 네트워크/서버권위, HTML5/앱웹 — 이 4개는 A1 효과로 자동 해결 예상)

---

### 5.2 P1 — Quality Gate + Evidence (3-5일, 신규 파일 1개: poker.yaml)

#### B1. `collect_project_evidence` 안에 `unmet_gaps` 루프

**위치**: `core/researcher.py:672 collect_project_evidence()`

**변경**: 현재 1회 escalation만 있는 흐름을 max_rounds 캡 루프로 변환:
```python
def collect_project_evidence(self, task_input, workspace=None, ...):
    research_plan = self._router.plan(task_input)  # P0 A5에서 domain/depth 채워짐
    domain_checklist = self._load_domain_manifest(research_plan.domain)  # 신규 helper, B3
    rounds = 0
    max_rounds = 3 if research_plan.research_depth == "deep" else 2

    local_refs = self._collect_local_references(task_input, ...)
    web_refs = []

    while rounds < max_rounds:
        sufficient = self._is_sufficient(local_refs, task_input, domain_checklist=domain_checklist)
        if sufficient:
            break
        # 부족 항목 식별 → 재수집
        unmet = self._identify_unmet_gaps(local_refs, web_refs, domain_checklist)
        if not unmet:
            break
        # 재수집: web 우선, 매니페스트 항목 query에 결합
        for gap in unmet:
            web_refs.extend(self._collect_web_references(f"{task_input} {gap}", limit=2))
        rounds += 1

    return {
        "local_references": local_refs,
        "web_references": web_refs,
        "research_plan": research_plan.to_dict(),
        "unmet_gaps": unmet if rounds == max_rounds else [],
        ...
    }
```

**helper**: `_identify_unmet_gaps(local_refs, web_refs, checklist) -> list[str]` — checklist 항목 중 refs 본문에서 매칭 안 된 항목 반환.

**비용 안전장치**: max_rounds=3 캡 (deep) / 2 (normal/shallow). 각 라운드 추가 web 호출은 `limit=2` (전체 limit 폭증 금지).

---

#### B2. `config/coverage_manifests/poker.yaml` 신규

§7에서 자세히. 8 필수 항목 정의.

---

#### B3. `domain` → 매니페스트 selector

**위치**: `core/researcher.py` 신규 helper `_load_domain_manifest(domain: str) -> list[str]`

```python
import yaml  # 기존 의존성 확인 필요. 없으면 stdlib만으로 simple parser 작성

def _load_domain_manifest(self, domain: str) -> list[str] | None:
    if not domain:
        return None
    path = Path(__file__).parent.parent / "config" / "coverage_manifests" / f"{domain}.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text())
    return data.get("required_fields", [])
```

`yaml` 의존성 미존재 시: 본 단계에서 add (또는 stdlib 기반 파싱).

---

#### B4. `research_evidence.json` 강화 — claim ↔ source 구조화 매핑

**위치**: `core/researcher.py` `collect_project_evidence()` 반환 직후

**변경**: source_pack에 다음 구조 추가:
```json
{
  "claims": [
    {
      "claim_id": "C001",
      "claim": "No-Limit Texas Hold'em uses small blind + big blind, 4 betting rounds",
      "source_id": "S001",
      "authority": "primary",
      "confidence": 0.9,
      "applies_to": ["betting_rules", "blind_structure"]
    }
  ],
  "sources": [
    {
      "source_id": "S001",
      "url": "https://www.wsop.com/...",
      "title": "WSOP Official Tournament Rules 2024",
      "trust_score": 0.95,
      "retrieval_method": "tavily_search",
      "fetched_at": "2026-05-04T..."
    }
  ]
}
```

**산출물**: `docs/research/<slug>-evidence.json` 으로 저장.

**LLM 호출 1회 추가**: 기존 fast_synthesis LLM 호출 결과의 `source_backed_claims`을 위 구조로 normalize. 비용 ↑ 미미 (이미 호출 중).

---

#### B5. coverage-report 자동 생성

**위치**: 신규 함수 `core/researcher.py:_emit_coverage_report()`

**변경**: 매니페스트 8 항목 vs evidence claims 매핑 결과를 두 파일로:
- `docs/research/<slug>-coverage.json` — 머신 판독용
- `docs/research/<slug>-coverage.md` — 사람 검토용 (matched/missing 표 1개)

```yaml
# coverage.json 구조
{
  "domain": "poker",
  "manifest_version": "1.0",
  "rounds": 2,
  "matched": ["hand_ranking", "blind_structure", "betting_rules", "side_pot",
              "all_in", "showdown", "server_authoritative_events"],
  "missing": ["client_hidden_state"],
  "match_rate": 0.875,
  "block": false  // 7/8 ≥ 0.7 → BLOCK 해제
}
```

**Gate 동작**: `match_rate < 0.7` 또는 `len(missing) >= 3` 시 `block=True`. project_pipeline은 block=True 시 후속 단계 진입 차단.

---

#### P1 자기 검증 기준

- [ ] B1: max_rounds 캡 동작 — 무한 루프 방지 단위 테스트 1건
- [ ] B2: `config/coverage_manifests/poker.yaml` 디스크 존재 + 8 항목 정의
- [ ] B3: `_load_domain_manifest("poker")` → 8 항목 list 반환
- [ ] B4: `docs/research/<slug>-evidence.json` 디스크 존재 + claims/sources 키 포함
- [ ] B5: `docs/research/<slug>-coverage.md` 디스크 존재 + matched/missing 표
- [ ] G2 (≥ 7/8 matched) 달성 — 동일 포커 build prompt 재실행 시

---

### 5.3 P2 — Spec Before Tasks (5-7일, 신규 모듈 1: spec_generator)

#### C1. `prepare_documents()` 게이트

**위치**: `core/project_pipeline.py:741 prepare_documents()`

**변경**: brief 생성 후 work_item 생성 전 사이에 `_verify_domain_spec()` 게이트 1건:
```python
def prepare_documents(self, ...):
    brief = self.researcher.research_project_brief(...)
    self._save_project_brief_json(brief)  # P0 A6
    # ... evidence/coverage 저장 (P1 B4·B5)

    if brief.get("research_plan", {}).get("domain"):
        spec_ok = self._verify_domain_spec(brief)
        if not spec_ok:
            specs = self.spec_generator.generate(brief)  # C2
            self._save_specs(specs)
            # 게이트: 매니페스트 BLOCK 시 work_item 생성 중단
            if self._coverage_blocked(brief):
                raise ResearchGateBlocked(...)

    # 기존 흐름 (role_plan → task_board → work_items) 진행
    ...
```

---

#### C2. `core/spec_generator.py` 신규 — 5종 도메인 명세

**신규 모듈** (≤ 200줄 목표):

```python
class SpecGenerator:
    def generate(self, brief: dict) -> dict[str, str]:
        domain = brief.get("research_plan", {}).get("domain", "")
        if domain == "poker":
            return {
                "rules": self._generate_rules_spec(brief),
                "state_machine": self._generate_state_machine(brief),
                "server_arch": self._generate_server_architecture(brief),
                "event_protocol": self._generate_event_protocol(brief),
                "client_view": self._generate_client_view(brief),
            }
        return {}
```

각 generator는 LLM 호출 1회 + 양식 템플릿. 출력 위치:
- `docs/specs/<slug>-rules-spec.md`
- `docs/specs/<slug>-state-machine.md`
- `docs/specs/<slug>-server-architecture.md`
- `docs/specs/<slug>-event-protocol.md`
- `docs/specs/<slug>-client-view.md`

**LLM 호출 5회 추가**: 비용 큼. domain != "" 일 때만 활성화 (포커 1 도메인만 → 사용자가 명시적으로 트리거).

---

#### C3. ADR (Architecture Decision Record) 자동 생성

**위치**: `core/spec_generator.py` 또는 신규 helper

**산출물**: `docs/decisions/<slug>-rule-baseline.md`

**양식**:
```markdown
# Decision: Rule baseline selection for <slug>

- **Date**: 2026-05-04
- **Status**: Accepted

## Decision
Use WSOP 2024 Tournament Rules as the rule baseline.

## Alternatives Considered
1. Poker TDA Rules — pro tournament focus, less recreational
2. Bicycle Cards house rules — popular but informal
3. Upswing Poker training rules — strategy focus, not authoritative

## Rationale
- WSOP is most globally recognized (referenced in 4/4 sources)
- Has explicit 8-player table provisions
- Side pot policy is clearly defined

## Evidence References
- claim_id: C001 (source_id: S001)
- claim_id: C003 (source_id: S001)
```

생성 트리거: `decision-record`에 해당하는 LLM 호출 1회. evidence.json의 claims를 입력.

---

#### C4. traceability.md 자동 생성

**산출물**: `docs/research/<slug>-traceability.md`

**양식**: MD 표 1개 (D9):

```markdown
# Traceability — <slug>

| claim_id | source_id | spec_section | task_id |
|----------|-----------|--------------|---------|
| C001 | S001 | rules-spec.md#betting-rounds | T001 |
| C002 | S001 | state-machine.md#preflop | T003 |
| ... | ... | ... | ... |
```

생성 트리거: spec/tasks 생성 후 후처리. evidence.json의 claims와 task_board의 task_id를 매핑. heuristic (claim의 `applies_to` ↔ task description 키워드 매칭).

---

#### P2 자기 검증 기준

- [ ] C1: 포커 build prompt 시 `_verify_domain_spec` 게이트 발화 + spec 5종 생성
- [ ] C2: `docs/specs/<slug>-*.md` 5건 디스크 존재
- [ ] C3: `docs/decisions/<slug>-rule-baseline.md` 디스크 존재 + Alternatives 표
- [ ] C4: `docs/research/<slug>-traceability.md` 디스크 존재 + claim_id ↔ task_id 매핑
- [ ] 매니페스트 BLOCK 시 work_item 생성 차단 (`ResearchGateBlocked` raise) 단위 테스트 1건

---

### 5.4 P3 — 평가 (1-2주)

#### D1. 종합 검증 — 동일 포커 build prompt 재실행

- §3 G1: gap-analysis §2 비교표 9차원 중 ≥ 7 Manus 동등
- §3 G2: poker.yaml 8 항목 ≥ 7/8 matched
- §3 G3: assistant_score ≥ 0.7

#### D2. traceability 추적성 검증

- plan.md References에 인용된 source_id가 evidence.json에서 발견되는지
- spec-section이 실제 docs/specs/ 파일의 헤더와 일치하는지
- task_id가 implementation-tasks.md에 존재하는지

#### D3. 실제 코드 빌드 가능성 (선택)

- spec 5종 + work-item 4-doc 인풋으로 단순한 코드 스켈레톤 1차 생성 후 컴파일 가능 여부

---

## §6. 산출물 5종 schema

### 6.1 project-brief.json (P0 A6)

**위치**: `docs/research/<slug>-project-brief.json`

```json
{
  "original_request": "<verbatim user input, 한국어 그대로>",
  "goal": "...",
  "background_context": "...",
  "problem_statement": "...",
  "target_path": "",
  "constraints": [],
  "required_skills": [],
  "role_hints": [],
  "deliverables": [],
  "risks": [],
  "research_notes": [],
  "tech_stack": [],
  "research_plan": {
    "mode": "fast_synthesis",
    "requires_research": true,
    "domain": "poker",
    "research_depth": "deep"
  }
}
```

### 6.2 evidence.json (P1 B4)

**위치**: `docs/research/<slug>-evidence.json`

```json
{
  "claims": [
    {"claim_id": "C001", "claim": "...", "source_id": "S001",
     "authority": "primary", "confidence": 0.9, "applies_to": ["betting_rules"]}
  ],
  "sources": [
    {"source_id": "S001", "url": "...", "title": "...",
     "trust_score": 0.95, "retrieval_method": "tavily_search",
     "fetched_at": "ISO8601"}
  ],
  "rounds": 2,
  "domain": "poker"
}
```

`authority`: `"primary"` (공식 룰북) | `"secondary"` (전략 사이트) | `"tertiary"` (블로그/위키)

### 6.3 coverage.json + coverage.md (P1 B5)

§5.2 B5 참조.

### 6.4 decision-record (P2 C3)

§5.3 C3 참조. `docs/decisions/<slug>-<topic>.md` (포커 외 도메인 향후 확장 시 `<topic>` 다양화).

### 6.5 traceability.md (P2 C4)

§5.3 C4 참조. MD 표 1개 (D9).

---

## §7. poker.yaml 매니페스트 설계

**위치**: `config/coverage_manifests/poker.yaml`

**의도**: codex 의견 §"포커게임 케이스 전용으로는 이렇게 강제해야 함" 항목을 8개로 압축. 각 항목은 evidence/spec 어느 한 곳에라도 매칭되면 matched.

```yaml
# config/coverage_manifests/poker.yaml
domain: poker
version: "1.0"
description: |
  Poker (Texas Hold'em variants) build prompt에서 evidence/spec 둘 중 한 곳에라도
  다음 8개 항목이 매칭되어야 work-item 생성 게이트 통과.
  매칭 임계: 7/8 (87.5%) — 1개 미만족 허용.

required_fields:
  - hand_ranking            # 족보 (Royal Flush ~ High Card)
  - blind_structure         # SB/BB, button rotation, 토너먼트 시 blind 증가
  - betting_rules           # No-Limit / Pot-Limit / Fixed-Limit, 4 betting rounds
  - side_pot                # all-in 발생 시 사이드팟 처리
  - all_in                  # all-in 시점 검증, 콜 가능액 계산
  - showdown                # 동률 처리, kicker 비교
  - server_authoritative_events  # 서버가 검증해야 할 이벤트 목록 (deal/raise/fold/showdown 등)
  - client_hidden_state     # 클라이언트에 노출 금지 정보 (다른 플레이어의 hole cards 등)

match_keywords:
  hand_ranking: ["hand ranking", "족보", "royal flush", "straight flush", "kicker"]
  blind_structure: ["blind", "small blind", "big blind", "button", "blinds increase"]
  betting_rules: ["no-limit", "pot-limit", "fixed-limit", "betting round", "preflop", "flop", "turn", "river"]
  side_pot: ["side pot", "사이드팟", "main pot"]
  all_in: ["all-in", "all in", "올인"]
  showdown: ["showdown", "쇼다운", "tie", "split pot"]
  server_authoritative_events: ["server authoritative", "server-side validation", "권위 서버", "deal event", "betting event"]
  client_hidden_state: ["hidden state", "private state", "hole cards", "client-side hidden", "정보 비대칭"]

# 매니페스트 활성 조건
trigger:
  domain: poker
  min_research_depth: normal  # shallow일 때는 매니페스트 미적용
```

**확장성**: 두 번째 도메인 (예: `realtime-streaming.yaml`)이 필요하면 같은 구조로 추가. 코드 수정 0 (D2).

---

## §8. 의사결정 D1~D9 — gap-analysis §7.5 흡수

| ID | 결정 | 근거 |
|----|------|------|
| D1 | P0에 A4 (`_is_sufficient` `domain_checklist` 매개변수) 포함 | 1줄 추가 + 후방 호환. P1 매니페스트 활성화 토대를 P0에서 미리 깔아두는 게 cheap |
| D2 | 매니페스트 = YAML 외부 파일 (`config/coverage_manifests/<domain>.yaml`) | 도메인 추가 시 코드 수정 0. 하드코딩 시 매번 import/dispatch 수정 필요 |
| D3 | Spec/Evidence 산출물 git 추적 | References에서 ID 인용, 사용자 검증 가능. `.gitignore` 미추가 |
| D4 | 첫 매니페스트 = poker 1개만 | Karpathy "Simplicity First". 두 번째 매니페스트는 두 번째 케이스 발생 시 |
| D5 | EvidenceMatrix structured 매핑 → P1 B4로 상승 | research_evidence.json 강화 결정과 동일 작업. 분리 무의미 |
| D6 | gap-analysis 문서 처리 = **Supersede** (in-place 정정 X) | 진단 변천사 = 학습 자산. 헤더와 §7로 정정 사유 흡수 |
| D7 | 통합 설계문서 = **단일 문서** (P0~P3 합본) | phase 간 의존성 직렬·강함 — 분할 시 cross-review가 phase 정합성 못 보고 BLOCK 빈발 |
| D8 | `docs/decisions/` 디렉토리 신설 | ADR 저장 위치, 기존 `docs/specs/`와 분리 (의도 명확) |
| D9 | traceability 양식 = **MD 표 1개** | JSON은 evidence.json이 이미 가짐, 중복 회피 |

---

## §9. 위험 + 완화

| 위험 | 시나리오 | 완화 |
|---|---|---|
| **R1**: RecoverySearchLoop 무한 루프 | unmet_gaps가 매 라운드 동일하게 식별돼 termination 실패 | max_rounds 캡 (deep=3, normal=2) + unmet 변화 없으면 즉시 break (B1) |
| **R2**: LLM 비용 폭증 | P2 spec 5종 + ADR + traceability LLM 호출 6회 추가 | `domain != ""` 조건으로만 활성화. 일반 build prompt에서는 P0 흐름만 작동 |
| **R3**: 매니페스트 confused matching | "poker"라는 단어가 들어간 무관한 프로젝트가 매니페스트 트리거 | A5 `_detect_domain` 토큰셋 강화 — `"poker" + ("game" or "card" or "hold'em")` 등 multi-token 조합 (P1 B3 단계에서 보강) |
| **R4**: Tavily 키 미설정 환경에서 권위 출처 0 | A3 화이트리스트 동작 안 함 | 기존 `_collect_llm_prior_knowledge` fallback 유지 (deprecation 미정책). 매니페스트 BLOCK 시 사용자에게 "Tavily 설정 필요" 메시지 출력 |
| **R5**: `original_request`가 거대해 prompt token 폭증 | 사용자가 1만자 짜리 요청 입력 | brief 저장 시 원본 그대로, prompt 주입 시 `original_request[:2000]` truncation. 양식 항상 trade-off 허용 |
| **R6**: yaml 의존성 미존재 | `config/coverage_manifests/poker.yaml` 로딩 실패 | B3에서 `requirements.txt`에 `PyYAML` 추가. 기존 사용 여부 grep 검증 후 결정 |
| **R7**: Coverage Gate가 모든 build prompt를 BLOCK | 매니페스트 매칭 7/8 임계가 너무 높음 | 트리거 조건 `domain != "" + min_research_depth >= normal` 로 좁힘. 일반 prompt는 매니페스트 미적용 |
| **R8**: P0 A6에서 slug 충돌 | 동일 slug 두 번째 실행 시 brief 덮어쓰기 | 기존 work-item slug 로직 그대로 (이미 timestamp 포함 또는 dedup 처리 중) — 신규 생성 X |

---

## §10. 일정 + 의존성

```
P0 (1-2일, blocker free)
  ├─ A1 original_request 보존 ──────────────────────────┐
  ├─ A2 local refs 도메인 가드                            │
  ├─ A3 web refs 권위 화이트리스트                        ├──→ P0 자기 검증 (G1 ≥ 4 차원)
  ├─ A4 _is_sufficient domain_checklist 매개변수 (idle)  │
  ├─ A5 ResearchPlan flag 3종                             │
  └─ A6 project-brief.json 저장                          ─┘

P1 (3-5일, P0 A4·A5·A6 의존)
  ├─ B1 unmet_gaps 루프 ──┐
  ├─ B2 poker.yaml         │
  ├─ B3 매니페스트 selector ├──→ P1 자기 검증 (G2 ≥ 7/8)
  ├─ B4 evidence.json      │
  └─ B5 coverage-report   ─┘

P2 (5-7일, P1 B4·B5 의존)
  ├─ C1 prepare_documents 게이트 ──┐
  ├─ C2 spec_generator (5종)        │
  ├─ C3 decision-record (ADR)       ├──→ P2 자기 검증 (게이트 BLOCK 동작)
  └─ C4 traceability.md            ─┘

P3 (1-2주, 평가)
  ├─ D1 종합 검증 (G1+G2+G3) ──┐
  ├─ D2 추적성 검증              ├──→ 본 설계 완수
  └─ D3 코드 스켈레톤 (선택)    ─┘
```

**총 예상 기간**: 1.5 ~ 3 주 (P0 제외 시 P1+P2+P3 = 1.5~3주)
**병렬화 가능**: P0 내부는 6개 병렬 가능. P1 내부는 B1과 B2/B3가 병렬, B4/B5는 B1 후. P2는 C1→C2→C3→C4 직렬.

---

## §11. cold-start 진입 체크리스트

다음 세션이 본 문서를 처음 보고 작업 진입할 때:

### 11.1 진입 전 확인

- [ ] `git pull --ff-only` 성공 (origin과 동기화)
- [ ] `python start_db.py agent-factory` 실행 (Supabase 메모리 pull)
- [ ] 본 문서 §1·§2·§5 P0·§6·§11 읽음
- [ ] `docs/2026-05-04-poker-scenario-af-vs-manus-gap-analysis.md` §7 정정 인지
- [ ] `docs/Minus/codex_my_의견.md` 코드 매핑 부분 인지
- [ ] hook 큐 상태 확인: `python3 scripts/check_design_pending.py` (cross-review pending 있으면 그 verdict 먼저 확인)

### 11.2 cross-review verdict 분기

- **PASS** 또는 **WARN**: §11.3로 진행
- **BLOCK**: 본 문서 갱신 후 재발화 (BLOCK 사유에 따라 §5 수정 / §6 schema 수정 / §7 매니페스트 항목 수정)

### 11.3 P0 착수 (Sonnet 모델 권장)

순서:

1. **A1** — `core/researcher.py:919` 2단계 (schema 1줄 + LLM 직후 **unconditional override** 1줄). §5.1 A1 BLOCK #1 반영 후 강화안 그대로
2. **A6** — brief 저장 helper 1개 신설 (`docs/research/<slug>-project-brief.json`)
3. 동일 포커 build prompt 1회 실행 → A1·A6 검증 (`project_brief["original_request"]` 한국어 원본 byte-for-byte 일치 + json 파일 디스크 존재 + LLM mock 4종 테스트)
4. **A2** — `_collect_local_references` 도메인 가드 + `_extract_domain_tokens` helper 신설
5. **A5** — `ResearchPlan` flag 3종 추가 + `_detect_domain` helper
6. **A3** — web refs 권위 화이트리스트 + trust_score
7. **A4** — `_is_sufficient` `domain_checklist=None` 매개변수 (P1 토대, 동작 변화 없음)
8. 기존 researcher 테스트 전체 PASS 확인
9. P0 자기 검증 기준 (§5.1) 모두 체크
10. 동일 포커 build prompt 재실행 → G1 ≥ 4 차원 개선 확인
11. P0 commit + Blueprint §3·§12 동기화 + 3-tier review 완주 (CLAUDE.md Review-Gate 규칙)
12. P1 진입

### 11.4 핵심 코드 진입점 (자주 봐야 할 파일)

| 파일 | 역할 | P0 라인 |
|---|---|---|
| `core/researcher.py` | Himari 리서치 에이전트 | 258 / 311 / 550 / 672 / 919 |
| `core/research_router.py` | mode + flag 분류 | 78 (dataclass) / 194 (plan) |
| `core/project_pipeline.py` | document 흐름 오케스트레이터 | 741 (prepare_documents) |
| `core/work_item_generator.py` | 4-doc 생성 (수정 불요) | 522 / 561 / 599 / 635 |
| `core/plan_verifier.py` | original_request 보존 (이미 존재) | 200 |

### 11.5 P0~P3 phase 전환 신호

- **P0 → P1**: G1 ≥ 4 차원 + A1·A6 산출물 디스크 존재
- **P1 → P2**: G2 ≥ 7/8 + evidence.json/coverage.md 디스크 존재
- **P2 → P3**: spec 5종 + ADR + traceability 디스크 존재
- **P3 종료**: G1 ≥ 7 + G2 ≥ 7/8 + G3 ≥ 0.7

---

## 부록 A — 본 설계와 메모리/CLAUDE.md 정합

- `feedback_post_edit_checklist`: P0~P2 각 phase 종료 시 Blueprint §3 (researcher / research_router / project_pipeline / spec_generator) + §12 변경 이력 동기화
- `feedback_design_review_mandatory`: 본 문서 자체가 설계문서이므로 작성 직후 af-cross-review 1회 필수 (CLAUDE.md 규칙)
- `feedback_model_per_phase`: 본 문서 작성은 Opus, P0~P2 코드 구현은 Sonnet
- `feedback_analysis_doc_baseline_must_be_real_code`: 본 문서 §2 라인번호는 HEAD 코드 grep 검증 완료 (작성 시점)
- `project_3tier_cost_reduction_plan`: P0~P2 commit은 3-tier review 통과 (Tier 2~3 자동 발화)
- `feedback_reverse_sycophancy_balance`: codex 의견 통합 시 균형 인상용 가짜 흠 끼우지 않음. §1.3은 원본 그대로 흡수

---

**끝.**
