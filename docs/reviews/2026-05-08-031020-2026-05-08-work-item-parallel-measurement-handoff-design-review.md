# Design Review: 2026-05-08-work-item-parallel-measurement-handoff

> Source: docs/2026-05-08-work-item-parallel-measurement-handoff.md
> Date: 2026-05-08 03:10
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

두 리뷰어 모두 Critical 결함을 독립적으로 발견. 핵심: 패치 위치가 측정 대상 항목의 절반에 접근 불가하고, 300s deadline이 측정 자체를 우회시킨다. 이 두 구조 결함이 해결되지 않으면 측정 데이터 신뢰도 0.

---

### Aggregated Findings (10 total)

#### 1. [ACCEPT] [Critical] 측정 위치·fallback 경로 이중 구조 결함
- **Critic**: `_generate_and_refine`은 `provider_id`, `model`, `used_fallback`, `prompt_chars` 4종에 접근 불가. 해당 메타는 `execute_document_prompt()`에서 결정되고 string만 위로 올라옴. + 300s `doc_gen_deadline` 초과 시 `_fallback_*()` 직호출 — `_generate_and_refine` 자체를 거치지 않아 dump 미발생.
- **Cross**: `generate_work_items()` 내 deadline 초과 분기(line 779/791/803)에서 spec/design/tasks가 `_generate_and_refine`을 우회하므로 단계별 elapsed 누락.
- **Judgment**: 두 리뷰어가 동일 구조 결함을 코드 라인 참조로 독립 확인. 패치 1곳 전제 자체가 무효.
- **Action Required**: 측정 위치를 `execute_document_prompt()` 내부 또는 `generate_work_items()`의 각 stage wrapper 레벨로 이동. fallback 분기에도 동일 포맷 레코드 기록 추가. 핸드오프 §3 전면 재작성.

#### 2. [ACCEPT] [High] 패치 스케치 변수 미갱신 + 스키마 불일치
- **Critic**: `provider_id_seen`, `model_seen`, `used_fallback_flag`는 선언만 있고 갱신 위치가 코드 어디에도 없음. `prompt_chars: len(content)` 는 output 길이를 prompt_chars로 라벨링.
- **Cross**: §2 측정 표 정의 필드와 예시 jsonl 레코드가 불일치. `prompt_chars` 계산식이 output을 사용.
- **Judgment**: 두 리뷰어 모두 동일 스키마 모순을 문서 라인 참조로 확인 (line 22, 68, 125).
- **Action Required**: jsonl 레코드 JSON schema를 문서에 고정(필수/선택 필드 명시). `prompt_chars`는 실제 prompt 길이로, 측정 불가 필드는 스키마에서 제거하거나 출처 명시.

#### 3. [ACCEPT] [High] `runtime/timing/` 경로·gitignore 처리 미확인
- **Critic**: 핸드오프 시점에 `git check-ignore runtime/timing/x.jsonl` 5초면 확인 가능한 사실을 다음 세션에 위임. staged 혼입 위험.
- **Cross**: 현재 `.gitignore`는 `runtime/`을 무시하지 않음(line 57). 프로젝트 런타임 컨벤션은 `.af_runtime/` 패턴.
- **Judgment**: Cross가 `.gitignore` 직접 확인으로 Critic 우려를 실증. 경로 혼입 위험 실재.
- **Action Required**: `.af_runtime/timing/` 등 기존 컨벤션 경로로 통일, 문서에 canonical 경로 고정. gitignore 상태를 문서에 명시.

#### 4. [ACCEPT] [High] 표본 수 부족·brief 선택 자기모순
- **Critic**: minesweeper(가벼움)로 refine 0건 발생 가능성을 §8 트러블슈팅으로 인정. budget 핵심 변수인 refine 발동 시 elapsed를 측정 설계가 보장 못 함.
- **Cross**: 단일 brief + 1~2회로는 timeout/failover/refine 분산 반영 불가.
- **Judgment**: 두 리뷰어 모두 1회 측정으로 p95 산정 불가를 지적. 측정 목적(budget 재산정)과 측정 계획 간 불일치.
- **Action Required**: 최소 측정 계획 명시 — brief 2종 × 회차 N회, stage별 median/p95 + refine 발생률 보고 기준. 단순 brief만으로 부족할 경우 복잡 brief 사전 지정.

#### 5. [ACCEPT] [High] `except Exception: pass` 침묵 실패
- **Critic**: 측정 실패(권한/디스크) 시 신호 0. jsonl이 비어있는 걸 보고서야 인지.
- **Cross**: 기존 코드리뷰(code-review.md:317)에 문서화된 non-atomic 쓰기 이슈를 재도입. `run_ledger.py:93`, `review_metrics_logger.py:94`의 파일락 패턴 미재사용.
- **Judgment**: 두 리뷰어 독립 확인. Cross는 기존 helper 재사용 경로까지 제시.
- **Action Required**: 최소 `_LOGGER.warning("timing dump failed: %s", exc)` 추가. §8 트러블슈팅에 "jsonl 비어있을 때 감지 방법" 행 추가.

#### 6. [ACCEPT] [High] Budget 산식 미정의
- **Critic**: 측정 후 어떤 통계(평균? p50? p95?)로 Stage budget 산정할지 공식 없음. budget 재산정이 본 측정의 유일한 목적인데 산식 미정.
- **Cross**: (직접 플래그 없음)
- **Judgment**: Critic 단독이나 증거 명확. 측정 목적(§1)과 산정 방법 사이 공백이 Opus 세션 재결정 비용 유발.
- **Action Required**: §5 또는 §6에 산정 공식 명시 — 예: `stage_budget = doc_type별 p95_elapsed × 1.2 마진`. 회차 임계치(N회 이상 필요) 정당화 추가.

#### 7. [ACCEPT] [Medium] 진입 명령 미완성
- **Critic**: 말줄임표 + "NEXT_STEPS.md에서 확인"으로 실행 명령 위임.
- **Cross**: `python3 -m core.project_pipeline`은 실제 동작하지 않음(line 1458 확인). 실제 진입점은 `run_factory_cli.py` 또는 `af` CLI.
- **Judgment**: Cross가 코드 확인으로 Critic 우려를 실증. 잘못된 entry로 빈 측정 실행 위험.
- **Action Required**: commit `dfa3f7e9`의 실제 명령을 그대로 인용하거나, `run_factory_cli.py` 기반 실동작 명령 1개로 고정.

#### 8. [HOLD] [Medium] `used_fallback`·provider 계약 미정의
- **Critic**: 코드에 fallback 종류 3가지(`_fallback_feature_*`, provider failover, placeholder refine) — 어떤 것인지 정의 없음. `deadline_fallback` / `provider_failover` / `placeholder_refine_attempts` 3개 분리 제안.
- **Cross**: provider/model을 단일값 vs failover 체인 중 어떤 계약으로 기록할지 미정. 결과 소비자(설계 v2)가 요구하는 계약 결정 필요.
- **Judgment**: 두 리뷰어 모두 계약 미정의를 지적하나 해결 방향(분리 vs 단일+체인)이 다름. 설계 v2의 소비 요건을 먼저 결정해야 판단 가능.
- **Question for Author**: 설계 v2 Stage budget 산정 시 fallback 종류별 분리 통계가 필요한가, 아니면 fallback 발생 여부(boolean)만으로 충분한가?

#### 9. [ACCEPT] [Low] 로컬 `import time, json, os` 중복
- **Critic**: `core/work_item_generator.py:6,8,11`에 모듈 레벨 import 이미 존재. 함수 내 재import 무용 + alias 스타일 충돌.
- **Cross**: (직접 플래그 없음)
- **Judgment**: Critic 단독이나 증거 명확(라인 참조 있음).
- **Action Required**: 패치 스케치에서 로컬 import 제거.

#### 10. [ACCEPT] [Low] 다중 회차 실행 시 run_id 부재
- **Critic**: 같은 brief 2회 돌리면 jsonl 누적(append), 회차 구분 컬럼(`run_id` 또는 `attempt_no`) 없음.
- **Cross**: (직접 플래그 없음)
- **Judgment**: Critic 단독이나 §4에서 "1회 추가" 실행을 명시하므로 실제 발생 가능한 케이스.
- **Action Required**: 레코드에 `run_id` 또는 `ts` 기반 회차 식별자 추가.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 측정 위치·fallback 경로 이중 구조 결함 | Critical | ACCEPT | Both |
| 2 | 패치 스케치 변수 미갱신 + 스키마 불일치 | High | ACCEPT | Both |
| 3 | `runtime/timing/` 경로·gitignore 미확인 | High | ACCEPT | Both |
| 4 | 표본 수 부족·brief 선택 자기모순 | High | ACCEPT | Both |
| 5 | `except Exception: pass` 침묵 실패 | High | ACCEPT | Both |
| 6 | Budget 산식 미정의 | High | ACCEPT | Critic |
| 7 | 진입 명령 미완성 | Medium | ACCEPT | Both |
| 8 | `used_fallback`·provider 계약 미정의 | Medium | HOLD | Both |
| 9 | 로컬 `import` 중복 | Low | ACCEPT | Critic |
| 10 | 다중 회차 `run_id` 부재 | Low | ACCEPT | Critic |

---

### Recommendations

구현 진입 전 핸드오프 문서(`docs/2026-05-08-work-item-parallel-measurement-handoff.md`)에서 반드시 수정:

1. **§3 패치 위치 재결정**: `execute_document_prompt()` 내부 또는 `generate_work_items()` stage wrapper로 이동. fallback 분기 커버리지 포함.
2. **300s deadline 무력화 명시**: 측정용 패치에 `doc_gen_deadline = time.time() + 99999` 또는 fallback 경로에도 dump 추가.
3. **jsonl 스키마 고정**: 필드 정의와 예시 레코드를 일치시키고, 측정 불가 필드 제거. `run_id` 추가.
4. **경로 canonical 지정**: `.af_runtime/timing/` 등 기존 컨벤션으로 통일, gitignore 상태 문서에 명기.
5. **최소 측정 계획 명시**: brief 2종 × N회, stage별 median/p95 기준. budget 산정 공식 추가.
6. **except 침묵 제거**: `_LOGGER.warning` 또는 stderr 출력으로 교체.
7. **진입 명령 고정**: `run_factory_cli.py` 기반 실동작 명령 1개 인용.
8. **HOLD 해소**: `used_fallback` / provider 계약을 설계 v2 소비 요건 기준으로 결정 후 스키마에 반영.