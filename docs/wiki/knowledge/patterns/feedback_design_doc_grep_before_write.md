---
name: feedback-design-doc-grep-before-write
description: design doc/spec에 식별자·호출자·클래스 명을 적기 전 반드시 grep으로 코드 실측. 추측 금지.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b3efd65c-90b1-4321-a7b9-332028d7c2c6
---

**규칙**: design doc / 설계문서 / 코드 명세 / 호출 스택 다이어그램에 다음을 적을 때 **반드시 grep으로 코드 실측 후 적는다**:
- 문자열 리터럴 / enum 값 (예: `"system_wide"`, `"isolated"`)
- 함수명 / 메서드명 (호출 시그니처 + 호출자 존재 여부)
- 클래스명 (정의 위치 + import 경로)
- 환경변수 / 상수명
- 파일 경로 / 모듈 경로

**Why**: 식별자 회귀 실수 3회 반복 (2026-05-11 ~ 2026-05-13):
1. 5/11 design doc: `NON_TRIVIAL_KINDS = {"feature", ...}` — 실제 `WorkKindClassifier`는 `"feature_update"` 산출. `"feature"` 미존재 → 게이트 영원히 False
2. 5/13 1차 정정: `blast_radius == "system"` — 실제 `change_impact.py:35`는 `"system_wide"` 산출. 또 같은 부류
3. 5/13 2차 정정: enum을 `{"local", ...}`로 기록 — 실제는 `"isolated"`. 세 번째 동일 패턴

추가로 데이터 흐름 다이어그램도 같은 실수:
- 5/13 2차: `ControlPlaneIntake.normalize() → project_pipeline.py:963` 흐름 적었으나 `normalize()` **호출자 0건**. `prepare_brief()`는 `_recall_from_memory()`만 호출. 즉 그림에 적은 흐름이 코드에 존재하지 않음

이런 류 실수는 cross-review에서 즉시 BLOCK 회귀 사유로 잡힌다. 비용: 매 라운드 평균 5~12 findings × 정정 사이클.

**How to apply**:
- design doc / spec / 정정 작업 / 호출 스택 도식화 진입 직전 — **사전 grep 체크리스트** 수행:
  - 등장하는 모든 식별자 → `Grep` 또는 `rg`로 1회씩 확인, 결과 0건이면 적지 않음
  - 다이어그램의 각 화살표 → 시작 함수와 도착 함수의 grep 결과 첨부 (호출자 / 호출되는지)
  - 새 예외 클래스, 새 상수, 새 메서드 — "이미 존재한다"고 적기 전 grep 0건 검증
- 정정 응답에 grep 명령 + 결과를 첨부하면 cross-review가 즉시 evidence로 인정
- 식별자 grep 단계를 건너뛰면 같은 BLOCK이 또 발생함 — 시간 절약 ❌, 시간 손해 ✅
- 관련: [[feedback-test-mock-vs-defect]] (production 흐름 먼저 확인 원칙과 같은 정신)
