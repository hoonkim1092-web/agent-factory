---
episode_id: 2026-04-18-wrong-symbol-invention
outcome: failure_then_success
project_id: lotto_predictor_v2
date: 2026-04-18
tags: [symbol-invention, hallucination, import-error]
---

# 에피소드: 존재하지 않는 심볼 발명

## 상황

lotto_predictor_v2 프로젝트에서 backend_dev 역할이 `pandas.read_parquet_lazy()`를
호출하는 코드를 작성했다. 이 함수는 존재하지 않는다.

## 실패 원인

- LLM이 라이브러리 문서 없이 추론으로 API를 발명함
- 테스트가 mock으로만 작성되어 실제 import 실패를 잡지 못함
- Level 1 retry에서 같은 패턴 반복 (총 3회 시도)

## 해결 방법

- Level 3에서 ISE Redesigner가 "실제 pandas 문서 확인" 지시 추가
- `pd.read_parquet()` (올바른 API)로 교체 후 성공

## Hints

- 라이브러리 함수명 발명 금지: 항상 공식 문서에서 확인된 API만 사용한다
- mock 전용 테스트는 실제 import 오류를 잡지 못한다 — 최소 1개 실행 테스트 필요
- Level 1 retry에서 같은 패턴이 반복되면 pivot(Level 2)으로 즉시 에스컬레이션
- 존재하지 않는 심볼 사용 시도가 감지되면 작업 전 경고 로그를 주입한다

## 결과

Level 3 redesign 후 성공. lineage_id: lotto_predictor_v2::backend::data_pipeline
