# Design Review: 2026-05-02-oh-my-openagent-ast-lsp-comparison

> Source: docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md
> Date: 2026-05-02 23:47
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

WARN = High/Medium findings exist. 분석 문서이므로 구현 차단은 없으나, 6절 비교 매트릭스에 오해 가능한 수치가 잔존한다. 다음 spike 설계 전 High 2건 수정 권고.

---

### Aggregated Findings (12 total)

#### 1. [ACCEPT] [High] Q-D 두 sink 불일치가 §6에 미전파
- **Critic**: §5.4 Q-D에서 hook_events.log 1 BLOCK vs docs/reviews/*.md 16 BLOCK+25 WARN 불일치를 인지하면서도, §6 매트릭스의 "정적 진단 효과 측정" 셀에는 이 불일치가 병기되지 않는다. 독자가 §6만 보면 "AF는 거의 항상 PASS" 로 해석 가능.
- **Cross**: 직접 플래그 없음 (단, Q-B 재현 명령 오류에서 sink 신뢰도 문제를 별도 지적).
- **Judgment**: 문서 §5.4 자체에 "§6 매트릭스에서 직접 인용 금지" 경고가 있으나 §6에 그 경고가 반영되지 않은 상태 — 내부 모순. Critic 근거 명확.
- **Action Required**: §6 "정적 진단 효과 측정" 셀에 `"hook_events.log 기준 51 PASS/1 BLOCK / docs/reviews 기준 16 BLOCK+25 WARN — 두 sink 미통합, §5.4 Q-D 참고"` 로 분리 병기.

#### 2. [ACCEPT] [High] SST OpenCode 잔존 모순 데이터가 §4·§6에 무조건부 인용됨
- **Critic**: §9.2에서 소스 문서(`2026-05-02-opencode-lsp-architecture-analysis.md`)에 "잔존 모순"이 있다고 명시하지만, §4 비교표와 §6 매트릭스는 해당 데이터를 "(확인됨)" 권원으로 사용.
- **Cross**: 직접 플래그 없음.
- **Judgment**: §6 "LSP 노출" 셀이 이미 `"§5 잔존 모순은 별도 인계"` 주석을 포함하지만, §4 비교표의 "Diagnostics push: edit tool 끝에서 lsp.diagnostics() 자동 호출 (확인됨)" 는 모순이 해소되지 않은 항목이다. Critic 근거 명확.
- **Action Required**: §4 비교표의 해당 셀에 "소스 문서 §5 모순 미해소 — 잠정치" 조건부 표기 추가.

#### 3. [ACCEPT] [Medium] engine=ast 레이블이 파일별 grep fallback을 은폐 가능
- **Critic**: 직접 플래그 없음 (§5.2에서 engine별 risk_id 차이를 기술하나 per-file fallback은 언급 안 됨).
- **Cross**: `core/review_bundle.py:91`이 import 가용성으로 engine을 단일 결정하지만 `:79`에서 파일별 AST 예외 시 grep fallback 발생 — bundle 전체가 `engine=ast` 레이블이지만 일부 파일은 grep 결과.
- **Judgment**: §5.2의 현재 서술은 "production engine은 _ast_available() 결과에 따라" 수준. 파일별 혼합 케이스가 검출 품질에 직접 영향. Cross 코드 증거 명확.
- **Action Required**: §5.2에 "파일별 AST 예외 시 해당 파일만 grep fallback 발생 가능 → bundle이 `engine=ast` 레이블이어도 실제 혼합일 수 있음" 주석 추가.

#### 4. [ACCEPT] [Medium] post_edit_enqueue "배선 미등록 = 발화 안 됨" 동치 주장 범위 초과
- **Critic**: §5.3이 settings.local.json 단일 근거로 "미등록"을 선언하지만, hook_runner.py builtin dispatch 경로의 실제 호출 여부는 "본 범위에서 미확인"으로 처리. 두 조건이 다른데 암묵적 동치처럼 서술됨.
- **Cross**: §8 spike plan에서 "호출 경로 정확한 추적"을 권고하며 동일 gap을 간접 확인.
- **Judgment**: §5.3 표현이 오해를 유발할 수 있다는 Critic 지적 타당. §5.4 Q-C도 "현재 배선의 효과 증거 아님"으로 보완하지만 §5.3 자체 표현은 수정되지 않음.
- **Action Required**: §5.3을 "직접 등록 안 됨. hook_runner.py builtin dispatch를 통한 간접 발화 여부는 §7.2 spike에서 미측정 — 현재 발화 여부 불명"으로 수정.

#### 5. [ACCEPT] [Medium] LSPCheckHook "휴면" 결론이 가설로 표현되지 않음
- **Critic**: Q-E에서 "lsp_check.py:205-206은 _log_hook_event() 미사용 → 0건은 호출 0회가 아님"을 정확히 지적하면서도, 바로 아래 원인 후보에서 사실상 "휴면" 결론으로 수렴. 분기 로직(pyright 없을 때 어떻게 분기하는지) 인용 없이 결론 선언.
- **Cross**: `core/hooks/lsp_check.py:93`이 `os.getcwd()` 기준으로 경로 검증 — agent 실행 workspace가 다를 경우 valid 파일도 skip 될 수 있는 별도 gap. §5.1과 §7.3이 이 점을 언급하지 않음.
- **Judgment**: 두 이슈는 다른 축이나 모두 LSPCheckHook 신뢰도 관련. Critic의 표현 강도 이슈 + Cross의 workspace 불일치 누락을 모두 수용.
- **Action Required**: Q-E 결론을 가설 표현으로 완화; §5.1 또는 §7.3에 "workspace != cwd 케이스에서 LSPCheckHook이 유효 파일을 skip할 수 있음 — agent_state['workspace'] 기준 검증 필요" 주석 추가.

#### 6. [ACCEPT] [Medium] Q-B 재현 명령이 현재 log format과 불일치
- **Critic**: 직접 플래그 없음.
- **Cross**: `grep -cE 'test_gap_analyzer.*[^-]rc=0'` 명령이 사용되지만, `hook_runner.py:103`의 실제 형식은 pipe-delimited `builtin|file|exit_code|error` — `rc=0` 패턴 존재하지 않아 항상 0 반환.
- **Judgment**: 재현 명령 오류는 §5.4 Q-B 수치 신뢰도를 직접 훼손. Cross 코드 증거 명확.
- **Action Required**: §9.4 (또는 Q-B 인라인) 재현 명령을 `awk -F'|' '$2=="test_gap_analyzer" && $4=="0" && $5 !~ /^skipped/ {c++} END{print c+0}'` 형태로 교체.

#### 7. [ACCEPT] [Medium] Bundle 빌드 성공 여부가 spike plan 측정 항목에서 누락
- **Critic**: 직접 플래그 없음.
- **Cross**: `hook_runner.py:144`는 enqueue 성공을 build 전에 로그하고 `:156`은 build 실패를 삼킨다 — 552건 enqueue가 bundle 재생성 성공을 보장하지 않음. §7.2 spike는 이 경로를 측정 항목에 포함하지 않음.
- **Judgment**: §8 후속 작업 후보 1번이 이 방향을 다루지만 bundle build rc 측정은 명시되지 않음. Cross 코드 증거 명확.
- **Action Required**: §7.2 또는 §8 항목 1에 "bundle 빌드 rc 및 failure silent-swallow 경로 측정 포함" 추가.

#### 8. [ACCEPT] [Medium] AST replace wrapper의 dry-run 기본값 대비 분석 누락
- **Critic**: 직접 플래그 없음.
- **Cross**: `core/ast_engine.py:165`의 `replace_file()`이 `dry_run=False` 기본값 + workspace boundary check 없음 — oh-my-openagent의 `ast_grep_replace` "Dry-run by default" 모델 대비 안전성 차이가 §4 비교표에 반영 안 됨.
- **Judgment**: 문서가 §4에서 "oh-my-openagent는 안전한 변경에 무게"라고 결론짓는데, AF AST replace의 현재 안전 모델은 언급 없음. Cross 코드 증거 명확하고 §4 핵심 결론과 직결됨.
- **Action Required**: §4 비교표 또는 §7.3 architectural gap에 "AF `replace_file()`: dry_run=False 기본, workspace 경계 검증 없음 — oh-my-openagent dry-run 기본과 대조" 항목 추가.

#### 9. [ACCEPT] [Low] AST-Grep 25개 언어 목록에서 Python 포함 여부 미확인
- **Critic**: §3.1 "ast_grep_search: Search code by AST structure (25 languages)" — AF는 Python-only 스택이므로 Python 포함 여부가 핵심 비교 축이지만 목록 미확인.
- **Cross**: Finding 6 (REJECT) — 파이프라인 Python-only는 build_review_bundle.py 필터 때문이므로 ast_engine 범위와 구별됨. 그러나 §3.1의 25개 목록 미확인 이슈는 별개.
- **Judgment**: §3.1 주석 부재가 §4·§7.3 비교 근거를 약화시킴. Critic 지적 수용.
- **Action Required**: §3.1에 "25개 언어 목록은 tool-descriptions.ts 하드코딩 — Python 포함 여부 본 fetch 범위에서 미확인" 주석 추가.

#### 10. [ACCEPT] [Low] §9.1 관련 fork가 분석에서 전혀 사용되지 않음
- **Critic**: `opensoft/oh-my-opencode` fork가 출처 목록에 있으나 §2~§7 어디에도 인용 없음.
- **Cross**: 직접 플래그 없음.
- **Judgment**: 사용되지 않는 출처는 독자에게 혼란. Critic 지적 수용.
- **Action Required**: §9.1에 "참조 없음 — 분석 범위에서 제외" 명시, 또는 출처 목록에서 제거.

#### 11. [HOLD] [Medium] Rename-safe workflow 도입 가능성 평가
- **Critic**: 직접 플래그 없음.
- **Cross**: §7.3의 "rename safe workflow 도입 가능성 평가" 항목은 실행 plane(AgentRunner self-hosted / Claude Code hook / 외부 CLI), LSP 서버 lifecycle 소유권, 대상 언어, prepare/apply 출력 계약이 결정되지 않아 도입 비용을 판단 불가.
- **Judgment**: 문서는 "분석 전용, 권고 아님"을 §9 서두에 명시. §7.3은 gap 식별이지 도입 계획이 아니므로 cross의 우려가 이 문서의 범위를 초과함. 그러나 "도입 가능성 평가"라는 표현이 plan으로 오독될 여지가 있음.
- **Question for Author**: §7.3 항목들이 "gap 나열" 인지 "향후 spike에서 평가할 계획" 인지 명확히 할 것. 후자라면 §7.3 제목을 "architectural gap (분석 결과, 결정 보류)" 으로 변경 권고 — 현재는 이미 "§7.3 architectural gap (oh-my-openagent 모델 대비)"로 표기되어 있어 HOLD 근거가 약함.

#### 12. [REJECT] [Low] AST scope가 multi-language ast_engine과 불일치
- **Source**: Cross (finding 6, self-rejected)
- **Original Finding**: `core/ast_engine.py`가 다양한 확장자를 지원하므로 "Python-only" 서술이 과소 표현.
- **Rejection Reason**: `scripts/build_review_bundle.py:51`의 `.py` 필터가 파이프라인을 Python-only로 제한. `ast_engine.py`의 언어맵은 파이프라인 범위를 변경하지 않음. Cross가 스스로 reject. 문서의 "Python-only" 서술은 정확.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Q-D 두 sink 불일치 §6 미전파 | High | ACCEPT | Critic |
| 2 | SST OpenCode 잔존 모순 무조건부 인용 | High | ACCEPT | Critic |
| 3 | engine=ast가 파일별 grep fallback 은폐 | Medium | ACCEPT | Cross |
| 4 | post_edit_enqueue 배선 미등록=미발화 동치 | Medium | ACCEPT | Both |
| 5 | LSPCheckHook 휴면 결론 + workspace mismatch | Medium | ACCEPT | Both |
| 6 | Q-B 재현 명령 format 불일치 | Medium | ACCEPT | Cross |
| 7 | Bundle 빌드 rc spike 항목 누락 | Medium | ACCEPT | Cross |
| 8 | AST replace dry-run 대비 분석 누락 | Medium | ACCEPT | Cross |
| 9 | 25개 언어 Python 포함 여부 미확인 | Low | ACCEPT | Critic |
| 10 | §9.1 fork 미사용 표기 누락 | Low | ACCEPT | Critic |
| 11 | Rename-safe workflow 평가 범위 | Medium | HOLD | Cross |
| 12 | AST scope multi-language 불일치 | Low | REJECT | Cross |

---

### Recommendations

**High 우선 (다음 문서 갱신 전):**
- §6 "정적 진단 효과 측정" 셀에 hook_events.log 기준 vs docs/reviews 기준 수치 분리 병기
- §4 비교표에 SST OpenCode 인용 항목 "소스 문서 잔존 모순" 조건부 표기

**Medium (spike 설계 전):**
- §5.3 post_edit_enqueue 표현 완화 (직접 미등록 ≠ 발화 안 됨)
- Q-B 재현 명령을 awk field-aware 형태로 교체
- §5.1/§7.3에 LSPCheckHook workspace vs cwd 불일치 gap 추가
- §5.2에 per-file engine 혼합 케이스 주석 추가
- §4/§7.3에 AF replace_file() dry-run=False vs oh-my-openagent 대조 추가
- §7.2 또는 §8에 bundle 빌드 rc 측정 항목 포함

**Low:**
- §3.1에 "25개 언어 Python 포함 미확인" 주석
- §9.1 fork 미사용 명시 또는 제거