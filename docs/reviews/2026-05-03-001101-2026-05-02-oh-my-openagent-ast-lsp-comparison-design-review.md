# Design Review: 2026-05-02-oh-my-openagent-ast-lsp-comparison

> Source: docs/참고/2026-05-02-oh-my-openagent-ast-lsp-comparison.md
> Date: 2026-05-03 00:11
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: WARN

분석 전용 문서이므로 구현 차단 없음. 다만 §4·§6 매트릭스 정확도 문제(High×2)와 미래 구현 단계에서 오독을 유발할 수 있는 표현 4건이 수정 권고 수준.

---

### Aggregated Findings (9 total)

#### 1. [ACCEPT] [High] §6 "정적 진단 효과 측정" 셀에 Q-D 두 sink 분포 미반영
- **Critic**: §5.4 Q-D에는 `hook_events.log` 기준 51 PASS/1 BLOCK과 `docs/reviews/*.md` 기준 16 BLOCK+25 WARN의 두 sink 불일치가 명시되어 있으나 §6 셀에서 Q-D 자체가 누락됨. "직접 인용 금지"는 단일 비율 단정 금지이지, 두 sink 불일치 사실 자체를 숨기라는 뜻이 아님.
- **Cross**: not flagged
- **Judgment**: §6이 독립 요약 매트릭스로 설계되었다면 §5.4 전체를 읽지 않고도 측정 상황을 파악할 수 있어야 한다. 라인 229 셀과 라인 199 경고 사이에 명백한 정보 단절이 존재한다.
- **Action Required**: §6 "정적 진단 효과 측정" 셀에 `"3-tier verdict: hook_events.log 기준 51 PASS/1 BLOCK / docs/reviews 기준 16 BLOCK+25 WARN — 두 sink 미통합, §5.4 Q-D 참고"` 한 줄 추가.

---

#### 2. [ACCEPT] [High] §4 비교표에 SST OpenCode "잔존 모순" caveat 누락
- **Critic**: §4 라인 90은 `"(확인됨)"`만 표기, §6 라인 227은 `"(확인됨; ... §5 잔존 모순은 별도 인계)"` caveat 포함. §4와 §6을 독립 참조하면 신뢰도 표시 불일치.
- **Cross**: not flagged
- **Judgment**: §9.2에도 동일 소스 문서의 잔존 모순이 명시되어 있으므로 §4 누락은 문서 내 일관성 위반이다.
- **Action Required**: §4 SST OpenCode "Diagnostics push" 셀을 `"edit tool 끝에서 lsp.diagnostics() 자동 호출 (확인됨, 단 소스 문서 §5 잔존 모순 있음 — §9.2 참고)"`로 수정.

---

#### 3. [ACCEPT] [Medium] oh-my-openagent "pull-only" 결론이 "없음"으로 오독 가능
- **Critic**: §6 라인 227 `"본 fetch 범위에서 확인 안 됨 (lsp_diagnostics는 pull tool로 노출)"`이 "존재하지 않음"으로 읽힐 수 있음. §2.3·§3.3의 `"미확인"` 표기보다 약한 표현.
- **Cross**: pull-only 결론이 너무 좁은 근거로 미래 계획에서 과용될 수 있다고 HOLD 판정. plugin entrypoint 구성 방식까지 검증 안 됨.
- **Judgment**: 두 리뷰어가 같은 셀에서 각각 "오독 유발"과 "미래 과용 위험"을 지적. 문서 자체는 §2.3에서 `"미확인"` 표기를 사용하므로 §6 셀 압축이 일관성을 깬다.
- **Action Required**: §6 해당 셀을 `"본 fetch 범위에서 미확인 (자동 push 코드 탐색 못 함; lsp_diagnostics는 pull tool로 노출)"` 로 수정.

---

#### 4. [ACCEPT] [Medium] §8 AST tool wrapper — 언어 확장 선행조건 미연결 + 계약 미명세
- **Critic**: §8 #4가 "AI tool wrapper 신설" 효과를 논할 때 §7.3의 Python-only 제약이 연결되지 않음. wrapper만 신설하면 oh-my-openagent 25개 언어 모델 대비 의미 있는 비교 불가.
- **Cross**: `core/ast_engine.py:203` 의 unbounded `search_dir`, 누락 시 예외(`:59`), ad hoc 반환 구조(`:165`) 등 계약이 미명세. 입출력·한도·실패 모드가 없으면 구현 시 안전성 보장 불가.
- **Judgment**: 두 리뷰어가 서로 다른 각도(선행조건 누락 / 계약 미명세)에서 같은 §8 #4를 문제로 지목. 분석 전용 문서이므로 완전한 스펙 요구는 범위 초과이나, 다음 spike가 이 항목을 과소평가하지 않도록 주석이 필요하다.
- **Action Required**: §8 #4에 `"(단, 비교 의미를 갖추려면 core/ast_engine.py 다언어 확장 선행 필요 — §7.3 참고; 구현 시 입출력 한도·실패 모드·workspace 경계 계약 별도 정의 필요)"` 추가.

---

#### 5. [ACCEPT] [Medium] LSPBridge가 구현 가능 prior art처럼 읽힘
- **Critic**: not flagged
- **Cross**: `core/lsp_bridge.py:35`는 `sys.executable -m pyright --langserver --stdio`를 사용하나 `core/hooks/lsp_check.py:54`는 CLI 바이너리 탐색 방식. `LSPBridge`에는 `prepareRename`/`rename` 메서드도 없음. 문서가 이를 설명하지 않으면 구현자가 재사용 가능한 것으로 오해할 수 있다.
- **Judgment**: §7.3 라인 252에 `"LSPBridge가 존재하나 lsp_check.py에 미연결"` 표기는 있으나 "미연결인 이유"나 "프로토타입 한계"가 없음. 미래 스파이크에서 LSPBridge를 기반으로 작업 시작할 경우 서버 디스커버리, lifecycle, smoke test를 처음부터 설계해야 한다는 사실이 묻힌다.
- **Action Required**: §7.3 LSPBridge 언급 뒤에 `"(exploratory 수준 — server discovery 방식·lifecycle 미정의, prepareRename/rename 메서드 없음; rename-safe 구현 시 재설계 필요)"` 주석 추가.

---

#### 6. [ACCEPT] [Medium] `_WRITE_TOOLS` 갭이 문서 명시보다 넓음
- **Critic**: not flagged (§5.1에 apply_edit·apply_block_edit 누락 이미 문서에 기술됨)
- **Cross**: `core/hooks/lsp_check.py:29`와 `core/hooks/design_review_hook.py:32`가 동일 하드코딩 셋을 중복. `synergy_omo_hash_edit`이 `core/synergy/bridge.py:643`을 통해 파일을 쓰지만 어느 셋에도 미포함.
- **Judgment**: §5.1의 "갭" 표기는 `apply_edit`·`apply_block_edit` 2종만 언급하나 실제 갭은 더 넓다. 분석 문서의 정확성 문제.
- **Action Required**: §5.1 `_WRITE_TOOLS` 갭 기술에 `"(hooks 간 셋 중복 + synergy_omo_hash_edit도 미포함 — cross-review 실측)"` 보충.

---

#### 7. [ACCEPT] [Medium] 효과 측정 메트릭이 AST/LSP 실사용과 미연결
- **Critic**: not flagged
- **Cross**: `scripts/review_metrics_logger.py:144`는 agent·tier·verdict·findings count·extension count만 기록. AST/LSP 호출 여부·diagnostics count·skip reason·bundle staleness가 없어 §8에서 제안하는 이벤트 추가만으론 verdict 품질 개선 상관관계 측정 불가.
- **Judgment**: §8 #5가 `lsp_check_skipped`/`lsp_check_result`/`ast_tool_search` 이벤트 추가를 제안하나, 이것만으로 "AST/LSP 사용 → verdict 개선" 인과관계를 추출할 수 없다는 점이 문서에 없다.
- **Action Required**: §8 #5에 `"(이벤트 추가만으로 verdict 상관관계 추출 불가 — review_metrics_logger.py에 ast_tool_calls, lsp_status, diagnostics_count, skip_reason, bundle_generated_at 필드 병행 확장 필요)"` 보충.

---

#### 8. [ACCEPT] [Low] Q-B 재현 명령의 `[^-]rc=0` 패턴 의도 불명확
- **Critic**: `[^-]rc=0`이 실제 log event 형식 없이 검증 불가. 의도한 "정상 완료"만 카운트하는지 불분명.
- **Cross**: not flagged
- **Judgment**: 단일 리뷰어지만 §9.4의 재현 명령은 다음 세션 비교 기준점이 되므로 패턴 오류가 있으면 baseline 자체가 틀린 수치를 반환한다.
- **Action Required**: §9.4에 log event 형식 예시(`# 예: "test_gap_analyzer rc=0 ..."`) 1줄 추가 또는 패턴을 `'test_gap_analyzer.*\brc=0'`으로 명시 + 의도 주석.

---

#### 9. [REJECT] [Low] af.spec 배포 설정에 기존 AST/LSP 모듈 누락 우려
- **Source**: Cross
- **Original Finding**: 신규 wrapper 구현 시 af.spec 업데이트가 필요할 수 있다는 우려.
- **Rejection Reason**: Cross 리뷰어 본인이 코드를 확인하고 REJECT 판정. `af.spec:38`에 `core.ast_engine`, `:88`에 `core.lsp_bridge`, `:154`에 `core.hooks.lsp_check`가 이미 포함되어 있고 `requirements.txt:12`에 `ast-grep-py`도 있음. 신규 wrapper는 별도 검토가 필요하나 현 분석 문서의 범위 밖.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §6 Q-D 두 sink 분포 미반영 | High | ACCEPT | Critic |
| 2 | §4 SST OpenCode 잔존 모순 caveat 누락 | High | ACCEPT | Critic |
| 3 | oh-my-openagent pull-only 오독 가능 | Medium | ACCEPT | Both |
| 4 | AST wrapper 선행조건 + 계약 미명세 | Medium | ACCEPT | Both |
| 5 | LSPBridge 구현 가능 prior art 오해 | Medium | ACCEPT | Cross |
| 6 | `_WRITE_TOOLS` 갭 범위 과소 기술 | Medium | ACCEPT | Cross |
| 7 | 효과 메트릭 AST/LSP 상관관계 미연결 | Medium | ACCEPT | Cross |
| 8 | Q-B grep 패턴 의도 불명확 | Low | ACCEPT | Critic |
| 9 | af.spec 기존 모듈 누락 우려 | Low | REJECT | Cross |

---

### Recommendations

분석 전용 문서이므로 구현 차단은 없음. 다음 spike 착수 전에 아래 순서로 처리 권고:

1. **§4 + §6 정확도 수정 (High×2)**: 독자가 §6·§4만 읽고 잘못된 수치/신뢰도를 가져가지 않도록 즉시 수정 — 5분 이하 작업.
2. **§6 "미확인" 표현 통일 (Medium, finding #3)**: §2.3·§3.3과 동일한 `"미확인"` 어휘로 §6 셀 통일.
3. **§7.3 LSPBridge 한계 주석 (Medium, finding #5)**: rename-safe 스파이크 착수 전에 재설계 필요 범위를 명시.
4. **§5.1 `_WRITE_TOOLS` 갭 범위 보정 (Medium, finding #6)**: `synergy_omo_hash_edit` 추가 + hooks 간 중복 사실 기재.
5. **§8 #4·#5 주석 추가 (Medium, finding #4·#7)**: 다언어 확장 선행조건 + 메트릭 필드 확장 필요성 — 계획 오해 방지.
6. **§9.4 grep 패턴 명세 (Low, finding #8)**: baseline 재현 명령 신뢰성 확보.