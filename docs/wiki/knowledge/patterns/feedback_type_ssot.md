---
name: type-ssot
description: "타입(dataclass, TypedDict, Protocol)은 한 파일에서만 선언, 나머지는 import"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9e3ccf5f-ac81-4fe7-a0de-c29487eeba26
---

타입은 SSOT 파일 한 곳에서만 선언하고, 다른 파일에서는 import해서 사용한다.

**Why:** 여러 파일에 같은 타입을 재정의하면 스키마 불일치 버그가 생기고 유지보수가 어려워진다.

**How to apply:** 새 dataclass/TypedDict/Protocol 작성 시 기존 코드에서 같은 이름이 있으면 import로 교체. 기존 grandfathered 예외(RouteDecision/LedgerEntry/VerificationResult/StrategyLedger)는 KNOWN_TYPE_DUPLICATES 허용 목록에만 등록. 위반 탐지: tests/test_coding_conventions.py::test_no_duplicate_type_names.
