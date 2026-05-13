---
name: af-test-runner
description: "Agent Factory 구현 완료 후 실행해야 하는 QA 절차. py_compile, diff 기반 테스트 갭 분석, pytest, 배포 빌드 경로 검증을 다룬다."
---

<overview>
AF 코드 구현 완료 후 반드시 실행해야 하는 테스트 절차를 정의한다.
구현 완료는 테스트 통과까지를 의미한다. 테스트가 없으면 작성한다.
</overview>

<when-to-use>
- 코드 구현이 완료된 직후
- PR 생성 전 최종 검증
- core/*.py 파일 추가 또는 변경
- OS 분기, subprocess, shell, shlex, packaging path 변경
</when-to-use>

<procedure>

## 4단계 테스트 절차

### Step 1: Syntax 검증

변경된 모든 Python 파일에 대해 실행한다.

```bash
python -m py_compile <changed_file.py>
```

실패하면 syntax를 수정하고 Step 1부터 다시 실행한다.

### Step 2: diff 기반 테스트 갭 분석

pytest 실행 전에 변경 diff가 대표 테스트를 요구하는 위험 패턴인지 확인한다.

```bash
cd D:/hoonProJect/worktrees/agent-factory
python scripts/test_gap_analyzer.py --workspace .
```

기준:

- `verdict=FAIL`이면 테스트를 보강하고 Step 1부터 다시 실행한다.
- subagent 완료 기록 시 `scripts/hook_runner.py`가 analyzer 결과를 다시 확인하고, FAIL이면 `review_gate.record_review_done()`에 `fail`을 강제 기록한다.
- 강제 FAIL 원인은 `.af_review_queue/test_gap_report.json`에 저장된다. pytest 출력만으로 원인이 보이지 않으면 이 파일을 먼저 읽는다.
- `subprocess`, `shell=True`, `shlex.split`, `sys.platform`, `os.name` 변경은 Windows/macOS/Linux 공백 포함 경로, quoted executable path, POSIX/Windows 분기 테스트가 필요하다.
- `sys.executable`, `__file__`, `Path(__file__)`, `sys._MEIPASS`, `sys.frozen` 변경은 source 실행과 배포/frozen 빌드에서 동일하게 동작한다는 테스트나 검증 근거가 필요하다.
- git이 아직 추적하지 않는 신규 Python 파일도 analyzer 대상이다. 신규 파일은 파일 전체를 added diff로 간주한다.
- `tests/` 아래 파일 변경은 프로덕션 리스크 게이트 대상에서 제외한다.

이 단계의 목적은 af-critic 전에 명백한 OS 분기, quoting, 배포 빌드 결함을 QA에서 차단하는 것이다.

### Step 3: 테스트 스위트 실행

```bash
cd D:/hoonProJect/worktrees/agent-factory
python -m pytest tests/ -x -q --timeout=60
```

- `-x`: 첫 실패에서 중단해 빠른 피드백을 받는다.
- `--timeout=60`: 무한 대기를 방지한다.
- 실패하면 원인 분석 후 코드를 수정하고 Step 1부터 다시 실행한다.

### Step 4: 신규 파일 배포 체크

`core/*.py` 파일이 추가됐다면 확인한다.

1. `af.spec`의 `hiddenimports`에 새 모듈이 필요한지 확인한다.
2. frozen 빌드 경로에 영향이 있으면 `sys.frozen`, `_MEIPASS`, `dist/af`, `af.exe` 기준의 동등성 테스트나 검증 근거를 남긴다.
3. import smoke를 실행한다.

```bash
python -c "from core.<module> import <symbol>; print('OK')"
```

## 테스트 없는 모듈

기존 테스트가 없는 모듈을 수정한 경우:

- 최소한의 import 테스트를 작성한다.
- 핵심 함수 호출 테스트를 작성한다.
- 파일명은 `tests/test_<module_name>.py`를 우선 사용한다.

## 주의사항

- 테스트에서 실제 LLM API를 호출하지 않는다. mock을 사용한다.
- timeout이 걸리는 테스트에는 `@pytest.mark.timeout(30)`을 붙인다.
- 테스트 실패를 우회하기 위해 테스트를 약화하지 않는다.
</procedure>
