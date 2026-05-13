# Code Review: approval_gate

> Source: core/approval_gate.py
> Date: 2026-05-13 18:17
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

> **Note**: Cross Review는 프로바이더 오류로 결과가 없음 (`provider error: Reading prompt from stdin...`). 판정은 Critic Review + diff 직접 분석 기반.

---

### Aggregated Findings (3 total)

#### 1. [ACCEPT] [High] 초기 gate 파일 미존재 시 `work_kind`/`blast_radius` 영구 미기록

- **Critic**: "gate 파일이 없으면 `_parse()` → `{}` → `current.get("work_kind")` → `None` → `_clean(None)` → `""` → `if work_kind:` 분기가 False → `extra_meta` 미출력. 최초 `approve()` 시 값을 기록할 루트가 없다."
- **Cross**: 응답 없음
- **Judgment**: Diff를 확인하면 세 호출부(approve, invalidate, block) 전부 `current.get("work_kind")` 방식으로 읽어서 전달한다. `current`는 `_parse(self.gate_path)`의 결과인데, 파일이 없으면 빈 dict를 반환한다. 즉 이 변경은 **기존 값 보존**에는 동작하지만 **최초 기록 경로가 없다**. `work_kind`/`blast_radius`를 처음 주입할 API(caller parameter, initial write 등)가 diff 어디에도 없다.
- **Action Required**: `approve()` 시그니처에 `work_kind: str = ""`, `blast_radius: str = ""` 파라미터를 추가하고 `current.get("work_kind") or work_kind`로 fallback 처리. 또는 gate 초기화 경로에서 첫 기록을 보장.

#### 2. [ACCEPT] [Medium] `extra_meta` 조건부 출력으로 게이트 파일 포맷 불일치

- **Critic**: "`work_kind`/`blast_radius` 유무에 따라 `## Metadata` ~ `## Snapshot` 사이 줄 수가 달라진다. `extra_meta` 빈 문자열이면 `last_updated` 줄 직후 빈 줄 하나가 추가되는 형식 차이가 발생한다."
- **Cross**: 응답 없음
- **Judgment**: 현재 `meta_block` 파서가 `\n##` 또는 `\Z` 까지 전부 수집하므로 파싱은 깨지지 않는다. 그러나 포맷 분기가 파서 취약성을 높이는 것은 사실이다. Finding 1이 수정되면(항상 값이 있거나 빈 문자열 고정) 이 문제는 동시에 해결된다.
- **Action Required**: `if work_kind:` 조건 제거 → 두 키를 항상 출력 (`- work_kind: {work_kind}\n- blast_radius: {blast_radius}\n`). 빈 값이면 빈 줄이 출력되지만 파서·포맷 모두 일관성 확보.

#### 3. [ACCEPT] [Medium] `_clean`이 내장 줄바꿈 미제거 — 파일 오염 경로

- **Critic**: "`_clean`의 `strip()`은 선행·후행 공백만 제거. 값 중간에 `\n`이 있으면 게이트 파일에 가짜 메타데이터 라인이 삽입된다. 현재 값 출처(`blast_radius.py`)가 내부이므로 즉각 위험은 낮지만 향후 외부 입력 경로 추가 시 취약해진다."
- **Cross**: 응답 없음
- **Judgment**: `blast_radius`와 `work_kind`는 현재 내부 생성값이므로 즉각 위험은 없다. 하지만 `_clean`은 범용 함수로 다른 곳에서도 쓰이므로 방어적 수정이 타당하다.
- **Action Required**:
  ```python
  def _clean(value: Any) -> str:
      return str(value or "").replace("\n", " ").replace("\r", " ").strip()
  ```

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 초기 gate 파일 미존재 시 `work_kind`/`blast_radius` 영구 미기록 | High | ACCEPT | Critic |
| 2 | `extra_meta` 조건부 출력으로 포맷 불일치 | Medium | ACCEPT | Critic |
| 3 | `_clean` 줄바꿈 미제거 — 파일 오염 경로 | Medium | ACCEPT | Critic |

---

### Recommendations

1. **Finding 1 우선 수정**: `approve(work_kind="", blast_radius="")` 파라미터 추가 + `current.get("work_kind") or work_kind` fallback. Finding 2는 이 수정으로 동시 해결 가능.
2. **Finding 2 통합**: Finding 1 수정 시 `extra_meta` 조건부 분기를 제거하고 두 키를 항상 출력하는 방식으로 통합.
3. **Finding 3 독립 수정**: `_clean` 한 줄 수정. 기존 사용처에 영향 없음.
4. **Cross Review 재실행 권고**: 이번 판정은 Critic 단독이므로 `mcp__codex__codex` 프로바이더 상태 확인 후 재실행하면 신뢰도가 높아짐.