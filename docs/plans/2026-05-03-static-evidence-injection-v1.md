# Static Evidence Injection v1 — 구현 플랜

**버전**: v1.0  
**날짜**: 2026-05-03  
**상태**: 초안 (cross-review 대기)  
**의존**: Spike 1+2 결과 (2026-05-03), NEXT_STEPS §AST/LSP 분석 §v1 Scope

---

## §1 목적

현재 3-tier 리뷰 파이프라인에서 아래 세 가지 측정 결과가 모두 0이다:

| KPI | baseline | 목표 |
|-----|---------|------|
| review_bundle 인용률 (`docs/reviews/*.md` 기준) | ~2% (메타 리뷰 1건) | 30%+ |
| test_gap_analyzer gate 호출률 (`hook_events.log` sink) | 0건 | 100% |
| review_metrics.jsonl 작성 성공률 | 0건 | 100% |

원인은 두 가지:
1. `post_agent_record` 빌트인이 `settings.local.json` / `settings.local.template.json`에 PostToolUse Agent 매처로 미등록 → 에이전트 완료 이벤트 전혀 수신 안 됨
2. `review_bundle.save()` 출력이 `risk_id` 코드 이름만 나열 → 리뷰어가 어떤 위험인지 맥락 없이 ID만 보게 됨 → 낮은 인용률

v1은 이 두 근본 원인을 수정하고, 효과를 측정할 수 있는 schema를 확장한다.

---

## §2 배경: Spike 결과

### Spike 1 — subagent 내부 tool trace (2026-05-03 실측)

- Claude Code PostToolUse(Agent) hook payload: `tool_input`(subagent_type, prompt) + `tool_response`(최종 텍스트)만 포함
- subagent 내부 tool call traces(Read, Bash, Grep 등)는 parent에 노출되지 않음
- **결론**: v1 KPI `evidence_cited` = final output text grep 기반으로 확정. tool trace 의존 방식은 v2 이후.

### Spike 2 — review_metrics.jsonl 미작성 원인 (2026-05-03 실측)

- `settings.local.json` PostToolUse: Write|Edit 매처만 존재. Agent/Task 매처 없음.
- `settings.local.template.json` PostToolUse: 동일.
- `hook_events.log` 마지막 `post_agent_record` 호출: 2026-04-21T07:32:29 (Phase 3.5 추가 전)
- **결론**: 원인 (a) 확정 — 배선 누락. 원인 (b)(c)는 해당 없음(호출 자체가 없으므로).

---

## §3 Scope

### IN (v1)
1. **배선 복구**: `settings.local.json` + `settings.local.template.json`에 PostToolUse `Agent` 매처로 `post_agent_record` 등록
2. **review_bundle 형식 개선**: `L{line} \`{risk_id}\`` → 맥락 있는 문장 형식
3. **review_metrics.jsonl schema 확장**: `evidence_present`, `evidence_items`, `evidence_cited` 3개 필드 추가
4. **evidence_cited 측정**: `_post_agent_record()`에서 reviewer output에 `file:line` 패턴 grep
5. **test_gap_analyzer gate 호출 확인**: 배선 복구 후 hook_events.log에 기록되는지 smoke 검증

### OUT (v2 이후)
- AST tool AI 직접 노출 (read/write)
- LSPCheckHook 활성화 (pyright 의존)
- Rename safe workflow
- Capability Plane 분리 설계

---

## §4 구현 상세

### §4.1 배선 복구

**파일**: `.claude/settings.local.json`, `.claude/settings.local.template.json`

PostToolUse 배열에 추가:
```json
{
  "matcher": "Agent",
  "hooks": [
    {
      "type": "command",
      "command": "python3 /Users/hoon/workTree/agent-factory/scripts/hook_runner.py post_agent_record",
      "timeout": 60
    }
  ]
}
```

- `settings.local.template.json`은 절대경로 없이 상대 경로 형식 유지: `"command": "python3 scripts/hook_runner.py post_agent_record"`
- timeout 60s: af-test-runner가 test_gap_analyzer를 실행하므로 30s 부족 가능성 있음 (실측 후 조정)

**검증 방법**: 다음 af-* 에이전트 실행 후 `grep "post_agent_record" .af_review_queue/hook_events.log` 확인

### §4.2 review_bundle 형식 개선

**파일**: `core/review_bundle.py` → `save()` 메서드

현재 출력 (line 110–114):
```python
for r in risks:
    lines.append(f"- L{r['line']} `{r['risk_id']}`: `{r['text']}`\n")
```

변경 후:
```python
_RISK_DESC = {
    "subprocess_usage": "subprocess 호출 — 사용자 입력이 args에 직접 전달되면 command injection 위험",
    "shell_true": "shell=True — 문자열 명령어 조립 시 injection 가능, list 형태로 교체 권장",
    "shlex_split": "shlex.split — 신뢰 불가 입력에 사용 시 토큰 분리 오동작 가능",
    "os_system": "os.system — subprocess.run 으로 교체 권장, 반환값 무시됨",
    "eval_usage": "eval() — 임의 코드 실행 위험, 사용 맥락 필수 검토",
    "exec_usage": "exec() — 동일",
    "dynamic_import": "동적 import — 외부 입력 경로 주입 시 모듈 실행 위험",
}

for r in risks:
    desc = _RISK_DESC.get(r["risk_id"], r["risk_id"])
    lines.append(
        f"- L{r['line']} `{r['risk_id']}` — {desc}. "
        f"코드: `{r['text'].strip()[:120]}`\n"
    )
```

- `_RISK_DESC` 길이 제한: 각 설명 120자 이내
- text 길이 제한: 120자 clip (긴 라인 대응)
- 기존 테스트 `tests/test_review_bundle.py`: 출력 형식 assertion 수정 필요

### §4.3 review_metrics.jsonl schema 확장

**파일**: `scripts/review_metrics_logger.py` → `append_metric()`

추가 파라미터:
```python
def append_metric(
    workspace: str,
    agent: str,
    tier: int,
    verdict: str,
    findings_count: int = 0,
    extension_log_count: int = 0,
    # v1 추가
    evidence_present: bool = False,   # review_bundle.md 존재 여부
    evidence_items: int = 0,          # bundle 내 risk 항목 수
    evidence_cited: int = 0,          # reviewer output에서 grep된 file:line 인용 수
) -> None:
```

JSONL row 추가 필드:
```json
{
  "evidence_present": true,
  "evidence_items": 5,
  "evidence_cited": 2
}
```

기존 row에 없는 필드는 `compute_report()` 에서 `r.get("evidence_cited", 0)` 방식으로 backward-compatible 읽기.

### §4.4 evidence_cited 측정

**파일**: `scripts/hook_runner.py` → `_post_agent_record()`

```python
# Phase 3.5 호출 직전에 evidence 정보 수집
evidence_present = False
evidence_items = 0
evidence_cited = 0

bundle_path = Path(workspace) / ".af_review_queue" / "review_bundle.md"
if bundle_path.exists():
    evidence_present = True
    bundle_text = bundle_path.read_text(encoding="utf-8")
    # L{n} `{risk_id}` 패턴 카운트 = items
    evidence_items = bundle_text.count("`") // 2  # 근사치 — 정확 카운트는 regex
    # reviewer output에서 "file.py:숫자" 패턴 grep
    import re
    evidence_cited = len(re.findall(r'\b\w[\w/.-]+\.py:\d+', content))
```

- `evidence_items` 정밀 카운트: `re.findall(r'- L\d+ `[^`]+`', bundle_text)` 길이
- `evidence_cited`: reviewer output(`content`)에서 `\b\w[\w/.-]+\.py:\d+` 패턴 매치 수
  - false positive 허용 (v1은 측정 시작이 목적, precision 튜닝은 v2)
- Phase 3.5 `append_metric()` 호출 시 3개 파라미터 전달

---

## §5 파일별 변경 목록

| 파일 | 변경 종류 | 주요 내용 |
|------|---------|---------|
| `.claude/settings.local.json` | 추가 | PostToolUse Agent 매처 + post_agent_record |
| `.claude/settings.local.template.json` | 추가 | 동일 (상대경로) |
| `core/review_bundle.py` | 수정 | `save()` 출력 형식, `_RISK_DESC` dict 추가 |
| `scripts/review_metrics_logger.py` | 수정 | `append_metric()` 파라미터 3개 추가, JSONL row 확장 |
| `scripts/hook_runner.py` | 수정 | `_post_agent_record()` evidence 수집 + 전달 |
| `tests/test_review_bundle.py` | 수정 | 출력 형식 assertion 갱신 |
| `tests/test_review_metrics_logger.py` | 수정 | 신규 파라미터 커버리지 추가 |

---

## §6 구현 순서

1. **settings 배선 복구** (15분) — 가장 리스크 낮음, 즉시 효과 확인 가능
2. **review_metrics schema 확장** (30분) — append_metric 파라미터 추가 + 테스트
3. **review_bundle 형식 개선** (30분) — `_RISK_DESC` + save() 수정 + 테스트
4. **evidence_cited 측정** (30분) — `_post_agent_record()` evidence 수집 로직
5. **통합 smoke test** (20분) — af-test-runner 1회 실행 후 metrics 기록 확인
6. **3-Tier 검증**

총 예상: 2.5시간

---

## §7 미결 결정 사항

| # | 결정 | 옵션 A | 옵션 B | 현재 판단 |
|---|------|--------|--------|---------|
| D1 | `evidence_cited` 측정 방식 | file:line grep (v1) | prompt 강제 인용 (v2) | v1은 A |
| D2 | PostToolUse timeout | 60s | 30s | 60s 사용, 실측 후 조정 |
| D3 | `_RISK_DESC` 위치 | review_bundle.py 인라인 | 별도 JSON/config | 인라인 (7종 고정, 변경 드묾) |

---

## §8 KPI 재측정 시점

v1 배포 후 3-Tier 검증 1회 완료 시:
- `grep "evidence_present" .af_review_queue/review_metrics.jsonl` → 값 확인
- `grep "evidence_cited" .af_review_queue/review_metrics.jsonl` → 인용률 계산
- 목표 30% 미달 시 → D1 prompt 강제 인용 (v2) 진입 결정
