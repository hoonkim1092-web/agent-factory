---
name: no-hardcoded-abspath
description: "/Users/, /home/, C:\\ 등 절대경로를 파일 조작 함수 인자에 하드코딩 금지"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9e3ccf5f-ac81-4fe7-a0de-c29487eeba26
---

open(), Path(), os.path.*, shutil.* 등 파일 조작 함수의 인자에 /Users/, /home/, /root/, C:\ 같은 절대경로 리터럴을 직접 쓰지 않는다.

**Why:** 하드코딩 절대경로는 다른 머신/환경에서 실행 불가. 특히 Mac/Windows 전환 시 즉시 깨진다.

**How to apply:** os.getcwd(), Path(__file__).parent, 환경변수(os.getenv), 함수 파라미터로 대체. 위반 탐지: tests/test_coding_conventions.py::test_no_hardcoded_abspath.

## 관련
- [[code/symbols]]

