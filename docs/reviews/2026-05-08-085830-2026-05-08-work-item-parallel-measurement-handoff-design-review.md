# Design Review: 2026-05-08-work-item-parallel-measurement-handoff

> Source: docs/2026-05-08-work-item-parallel-measurement-handoff.md
> Date: 2026-05-08 08:58
> Type: design
> Providers: critic=codex
> Mode: single-provider (design critic only)
> Trigger: unknown

---

## Critic Review

### Verdict: BLOCK

### Findings

1. [Critical] 측정 데이터가 조용히 유실/손상될 수 있어 budget 근거로 부적합  
Section: "`with open(f\"runtime/timing/{work_item_id}_baseline.jsonl\", \"a\") ... except Exception: pass`"  
Issue: 제안 패치는 append + `except Exception: pass` 조합이라 쓰기 실패/부분쓰기/권한 오류가 나도 탐지되지 않습니다. 이 프로젝트의 기존 위험 패턴(M10/H3)과 동일하며, 측정값 신뢰성이 깨집니다. 실제 코드에서도 텍스트 쓰기는 atomic 보장이 없습니다([core/file_io.py](/Users/hoon/workTree/agent-factory/core/file_io.py#L117)).  
Suggestion: 최소한 `file_lock` + 실패 로그 + 비0 종료를 넣고, 가능하면 `run_id/doc_type`별 개별 파일 atomic write 후 집계로 바꾸세요.

2. [High] 문서 내부 모순: “provider_id 수집 불가”와 “provider_id 변화 기록”이 동시에 존재  
Section: "`provider_id ... 수집 불가`" + "`record에 provider_id 변화 기록`"  
Issue: 본문은 provider/model/used_fallback 수집이 불가능하다고 명시하지만(§2, §3), 트러블슈팅은 provider 변화를 record로 확인하라고 지시합니다(§8). 현재 호출 체인에서도 메타는 버려집니다([core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py#L523), [core/requirement_llm.py](/Users/hoon/workTree/agent-factory/core/requirement_llm.py#L173)).  
Suggestion: 둘 중 하나를 정리하세요. provider 추적이 필요하면 `_generate_doc_with_llm` 반환 메타를 `_generate_and_refine`까지 전달하도록 설계 변경이 필요합니다.

3. [High] 파일명/식별자 가정이 실제 코드와 불일치하여 결과 해석이 흔들림  
Section: "`runtime/timing/minesweeper-baseline_baseline.jsonl 예상 출력`"  
Issue: 파일명 키로 쓰는 `work_item_id`는 `--project` 값이 아니라 brief에서 파생된 slug입니다([core/project_pipeline.py](/Users/hoon/workTree/agent-factory/core/project_pipeline.py#L900)). 같은 task라도 slug가 달라질 수 있고, 다회 측정 시 run 경계도 섞입니다(레코드에 `run_id` 없음).  
Suggestion: 출력 키를 `run_id + doc_type`로 고정하고, 저장 경로를 `runs/<run_id>/timing/`로 분리하세요.

4. [High] partial failure 시나리오 누락: 4단계 측정 보장 없음  
Section: "`4단계 elapsed_sec 표`", "`예상 출력`(4줄 고정)  
Issue: 실제 구현은 300초 deadline 초과 시 spec/design/tasks를 fallback으로 우회합니다([core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py#L766)). 이 경우 `_generate_and_refine`가 호출되지 않아 레코드가 4줄 미만이 될 수 있는데, 설계에 검출/중단 기준이 없습니다.  
Suggestion: “레코드 4개 미만이면 실험 실패”를 명시하고 재실행 규칙을 추가하세요.

5. [Medium] 브랜치 핸드오프 지시가 환경 의존적  
Section: "`git checkout 2026-05-07-memory-gitignore-cleanup`"  
Issue: 하드코딩 브랜치는 없는 환경이 많아 재현성을 떨어뜨립니다.  
Suggestion: `git switch -` 또는 “측정 시작 전 현재 브랜치명 저장 후 복귀” 절차로 바꾸세요.

### Missing from Design
- 동시 실행 시 append 충돌 방지 전략(락/파일 분리)  
- 측정 실패 판정 기준(누락 레코드, malformed jsonl, fallback 혼입)  
- frozen/Windows/다른 CWD에서의 저장 경로 규칙 (`runtime/timing` 상대경로 금지)  
- 임시 패치가 테스트/리뷰 게이트에 미치는 영향 및 복구 검증 절차 (`git restore` 이후 확인 항목)

### Positive Observations
- 실제 진입점이 `run_factory_cli.py`임을 명확히 지정한 점은 정확합니다([run_factory_cli.py](/Users/hoon/workTree/agent-factory/run_factory_cli.py#L556)).  
- 수정 범위를 `_generate_and_refine` 단일 지점으로 좁힌 접근은 구현 부담을 낮춥니다([core/work_item_generator.py](/Users/hoon/workTree/agent-factory/core/work_item_generator.py#L834)).