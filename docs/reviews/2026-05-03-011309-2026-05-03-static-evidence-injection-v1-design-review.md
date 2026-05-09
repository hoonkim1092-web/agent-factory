# Design Review: 2026-05-03-static-evidence-injection-v1

> Source: docs/plans/2026-05-03-static-evidence-injection-v1.md
> Date: 2026-05-03 01:13
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

Cross Review가 provider error로 실패했습니다. Critic Review 단독으로 집계합니다.

---

## Final Design Review — Static Evidence Injection v1

### Verdict: WARN

BLOCK 없음. Cross Review는 provider error로 미실행 — Critic Review 단독 기반. 구현 전 §4.3·§4.4 2건 수정 권고.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [WARN] §4.3 `append_metric()` 현재 시그니처에 기존 파라미터 3개 누락

- **Critic**: 미언급
- **Cross**: F3 WARN — `scripts/review_metrics_logger.py` L144-154 실제 시그니처에 `duration_ms`, `tokens`, `tool_calls` 이미 존재. §4.3 스니펫에 없음 (이전 round cross 확인).
- **Judgment**: 실제 파일 읽기로 확인된 회귀 위험. §4.3 스니펫을 그대로 복붙하면 기존 파라미터 3개가 삭제됨.
- **Action Required**: §4.3 시그니처 스니펫에 `duration_ms: int | None = None, tokens: int | None = None, tool_calls: int | None = None` 명시 추가. 또는 주석으로 "기존 파라미터 유지 후 3개 v1 파라미터 추가" 명시.

#### 2. [ACCEPT] [WARN] §4.4 `evidence_items` 근사치 공식 2배 오류

- **Critic**: Finding #3 — `bundle_text.count("`") // 2`는 항목당 backtick 4개(risk_id 앞뒤 2 + text 앞뒤 2)이므로 실제 항목 수의 2배 반환. 설계 본문이 정밀 regex를 병기하므로 근사치 공식은 사실상 dead code.
- **Cross**: N/A (provider error)
- **Judgment**: 설계 내부 자기모순. 두 방식이 동시 제시되어 구현자가 잘못된 줄을 선택할 가능성 높음.
- **Action Required**: §4.4 코드 스니펫에서 `evidence_items = bundle_text.count("`") // 2` 라인 삭제. `re.findall(r'- L\d+ \`[^\`]+\`', bundle_text)` 단일화.

#### 3. [ACCEPT] [WARN] §4.1 template 상대경로 cwd 보장 근거 없음

- **Critic**: Finding #1 — `settings.local.template.json` 상대경로 `python3 scripts/hook_runner.py`가 Claude Code hook 실행 cwd = repo root라는 보장이 설계에 없음.
- **Cross**: N/A (provider error)
- **Judgment**: 기존 `settings.local.json`의 다른 hook들이 절대경로를 사용하는 패턴과 불일치. cwd 보장 근거가 없으면 template 사용자가 경로 오류를 디버깅하기 어려움.
- **Action Required**: §4.1에 "Claude Code hook은 repo root를 cwd로 실행" 근거 명시. 또는 template에 `${REPO_ROOT}` placeholder 방식 안내.

#### 4. [ACCEPT] [Low] §4.4 `import re` 중복

- **Critic**: Finding #4 — `hook_runner.py` L26에 모듈 레벨 `import re` 이미 존재. 설계 스니펫 인라인 `import re` 불필요.
- **Cross**: N/A (provider error)
- **Judgment**: 무해하나 혼란 유발 가능. 스니펫 정합성 문제.
- **Action Required**: §4.4 코드 스니펫에서 `import re` 라인 삭제.

#### 5. [ACCEPT] [Low] §4.2 라인 번호 모순 (참고값만)

- **Critic**: 실제 L113–115라고 주장.
- **Cross**: 이전 round에서 L110–114라고 주장. 이번 round N/A.
- **Judgment**: 구현 영향 없음(코드 스니펫이 정확히 일치하므로). 라인 번호는 참고값.
- **Action Required**: §4.2 라인 번호 "L110–114" 삭제 또는 `circa L110` 표기로 교체.

---

### Cross Review 미실행 고지

이번 round Cross Review는 provider error(OpenAI Codex session 연결 실패)로 독립 검증 수행 불가. Finding #1(시그니처 누락)의 Cross 증거는 이전 round 결과를 인용. BLOCK급 발견 없으나 단독 Critic 기반 한계 있음.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §4.3 `append_metric()` 기존 파라미터 3개 누락 | WARN | ACCEPT | Cross (prev round) |
| 2 | §4.4 `evidence_items` 2배 오류 | WARN | ACCEPT | Critic |
| 3 | §4.1 template 상대경로 cwd 미보장 | WARN | ACCEPT | Critic |
| 4 | §4.4 `import re` 중복 | Low | ACCEPT | Critic |
| 5 | §4.2 라인 번호 모순 | Low | ACCEPT | Both (prev round) |

---

### Recommendations

1. **구현 전 필수**: §4.3 시그니처 스니펫에 기존 3개 파라미터(`duration_ms`, `tokens`, `tool_calls`) 추가 — 회귀 위험 최고.
2. **구현 전 필수**: §4.4 `evidence_items` 근사치 공식 삭제, regex 단일화.
3. **구현 전 권고**: §4.1 template 상대경로 cwd 보장 근거 한 줄 명시.
4. **스니펫 정리**: §4.4 `import re` 삭제, §4.2 라인 번호 삭제.
5. **미정의 항목**: §6 Step 5 smoke test 통과 기준("어떤 에이전트 실행 → `hook_events.log`에 어떤 패턴이 있으면 PASS")을 한 줄 추가 권고.