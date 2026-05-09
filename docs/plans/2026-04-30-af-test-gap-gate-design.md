# af-test-runner 테스트 갭 게이트 설계

작성일: 2026-04-30

목적: af-critic 이전 단계에서 명백한 테스트 커버리지 누락을 차단해, 같은 유형의 critic BLOCK 반복과 토큰 낭비를 줄인다.

## 배경

최근 `subprocess.run`, `shell=True`, `shlex.split(posix=False)` 변경에서 Windows 경로 quoting 문제가 af-critic 단계에서 반복적으로 발견됐다. pytest는 통과했지만 테스트 입력이 실제 위험 입력을 대표하지 못했다.

문제는 af-critic 범위가 넓다는 점보다, af-test-runner가 "테스트가 변경 위험을 충분히 대표하는가"를 판단하지 못한 점이다.

## 설계 판단

af-critic 입력을 줄이는 방식은 방어선의 시야를 줄이는 증상 치료에 가깝다. 대신 af-test-runner가 pytest 실행 전 diff를 분석해 위험 패턴을 찾고, 관련 테스트에 대표 케이스가 없으면 FAIL로 판정한다.

이렇게 하면 af-critic은 최종 리뷰 역할을 유지하고, 명백한 테스트 설계 누락은 더 앞 단계에서 저렴하게 잡는다.

## 구현 파일

- `scripts/test_gap_analyzer.py`
- `tests/test_test_gap_analyzer.py`
- `scripts/hook_runner.py`
- `tests/test_hook_runner_builtins.py`
- `.claude/agents/af-test-runner.md`
- `.claude/skills/af-test-runner/SKILL.md`

## analyzer 동작

실행:

```bash
python scripts/test_gap_analyzer.py --workspace .
```

입력 파일 선택:

1. `.af_review_queue/pending_agent_review.json`의 `files`를 우선 사용한다.
2. pending 파일이 없으면 `git diff HEAD`와 staged diff의 변경 Python 파일을 사용한다.
3. git이 아직 추적하지 않는 신규 Python 파일도 포함한다. 신규 파일은 `git diff HEAD`가 비어 있을 수 있으므로 파일 전체를 synthetic added diff로 만들어 분석한다.
4. `tests/` 아래 파일은 프로덕션 리스크 게이트 대상에서 제외한다. 테스트 코드 자체의 mock/subprocess 사용이 게이트를 자기 자신에게 걸지 않도록 하기 위한 규칙이다.

현재 강제 FAIL 규칙:

- `subprocess.run`, `subprocess.Popen`, `shell=True`, `shlex.split` 변경에서 관련 테스트에 Windows와 POSIX 양쪽의 공백 포함 quoted executable path 케이스가 없으면 FAIL.
- `sys.executable`, `__file__`, `Path(__file__)`, `sys._MEIPASS`, `sys.frozen` 변경에서 source 실행과 배포/frozen 빌드 경로 동등성 근거가 없으면 FAIL.

대표 테스트 예:

- Windows: `"C:\\Program Files\\Codex\\codex.cmd" --version`
- macOS: `"/Applications/Codex CLI/codex" --version`
- Linux: `"/opt/codex cli/codex" --version`
- 배포 빌드: `sys.frozen`, `sys._MEIPASS`, `PyInstaller`, `dist/af`, `af.exe` 근거

출력:

- `verdict=PASS`: 테스트 갭 없음
- `verdict=FAIL`: pytest 실행 결과와 별개로 테스트 보강 필요

## review_gate 자동 통합

질문이 있었던 부분의 결론은 "수동 지침만으로 충분하지 않다"이다. 그래서 `scripts/hook_runner.py`의 `post_agent_record` 경로에 기계적 강제를 추가했다.

흐름:

1. af-test-runner subagent가 완료된다.
2. `hook_runner._post_agent_record()`가 subagent 출력에서 verdict를 파싱한다.
3. subagent type이 `af-test-runner`이면 `_apply_test_gap_verdict()`를 호출한다.
4. `_apply_test_gap_verdict()`가 `scripts/test_gap_analyzer.py`를 실행한다.
5. analyzer verdict가 `FAIL`이면 기존 verdict가 `PASS`여도 `review_gate.record_review_done(..., "fail")`로 강제 기록한다.
6. FAIL 원인은 `.af_review_queue/test_gap_report.json`에 저장한다. Claude가 이 파일을 읽으면 gap id, 파일명, reason, expected evidence를 바로 확인할 수 있다.
7. analyzer verdict가 `PASS`이면 기존 af-test-runner verdict를 유지하고 stale `test_gap_report.json`은 제거한다.
8. analyzer 자체 오류는 hook 실패로 전파하지 않고 `skipped:<error>`로 로그에 남긴 뒤 기존 verdict를 유지한다.

## Claude 공유 메모

이 변경은 af-critic을 약화하지 않는다. af-critic은 마지막 논리 리뷰로 유지한다. 대신 af-test-runner가 테스트 설계 누락을 먼저 잡아서 critic 반복 호출을 줄인다.

특히 다음 변경은 af-test-runner 단계에서 직접 대표 케이스를 확인해야 한다.

- OS 분기, shell 실행, subprocess, shlex 변경
- 경로 quoting과 공백 포함 executable path 처리
- `sys.executable`, `__file__`, `_MEIPASS`, frozen build 경로 처리
- source 실행과 배포 빌드의 동작 동등성
- 신규 untracked Python 파일. diff가 없다고 안전한 것이 아니므로 파일 전체를 added diff로 간주한다.

강제 FAIL이 발생하면 Claude는 먼저 다음 파일을 확인한다.

```bash
cat .af_review_queue/test_gap_report.json
```

추가 확장 후보:

- 파일 삭제/원자적 쓰기 변경에는 crash 중간 상태 테스트 요구
- async/shared state 변경에는 동시성 테스트 요구
- cache/list/dict 누적 변경에는 eviction 또는 bounded growth 테스트 요구
- path handling 변경에는 Windows backslash와 POSIX slash 케이스 요구
