---
generated_at: 2026-06-02T02:36:04+09:00
source_commit: 27aef166
sources:
  - Master_Blueprint.md
  - docs/code_review/code-review.md
  - NEXT_STEPS.md
---

# Open Items — 미완료/보류 항목

> **주의**: 마커(`🚧`/`보류`/`❌`/`⚠️`) 기반 자동 추출 — 불완전할 수 있음.
> 정확한 상태는 NEXT_STEPS.md 원본을 참조.
> Source: NEXT_STEPS.md
> 관련: [[index]] | [[review_patterns]] | [[source_refs]]

- (L5) > - **다음은 product-value work-item** — 내부 파이프라인 배관(planner/premortem/dogfood/research_*) 추가 금지(메타-재귀 함정). 다음 작업은 "AF가 사용자에게 줄 실제 가치"에서 도출.
- (L6) > - **밀린 3건(planner research_findings 본소비 / auto_apply_defaults FSA 배선 / cli_hook_bridge)은 보류** — 전부 내부 배관이고, 가치 판정은 제품 방향(Step 0) 결정 후에만 가능.
- (L7) > - **다음 단계**: Step 0 제품 결정 (범위 축소판: 대상 ICP + 첫 task type 2건만 확정, 나머지는 가설 1줄). 산출물 = `docs/2026-06-02-af-step0-product-decisions.md`, "결정 1줄 + 근거 1줄" 계약. analysis-paralysis 차단(4/26 정의 후 5주 미결 전례).
- (L8) > - **브랜치 사실**: `2026-05-20-research-coverage-gate`가 origin/main 대비 **232 ahead / 3 behind** (dogfood stream 누적). 머지 결정 보류 — 사용자 판단.
- (L13) > **다음 세션 최우선 진입점**: **dogfood detector 인프라 검증 완료 (2026-06-02) — 다음은 ① 실가치 work-item 선정 또는 ② 저우선 정리**. 북극성 epic("AF가 AF를 개발하는 완성 루프")의 `investigation → AI 프롬프트 → production 코드` 고리가 실제 run에서 닫힘이 직접 관측됨
- (L20) >    - **R18 detector 추가 보류**: 후보 3종 전부 부적합 — `mutable_default_arg`(repo 0건), `broad_except`(의도적 best-effort 1050건, CLAUDE.md 명문화), `unused_import`(TYPE_CHECKING/`__all__` false-positive 97건). detecto
- (L23) >    - **다음**: R18 재평가 (배선 실효성 확정 → R18 게이트 해제됨). 선택적: R15~R17을 change-relative(변경 함수 한정)로 좁힐지 설계 검토 — 단 whole-file 스캔도 "파일 수정 시 기존 복잡도 인지" 의도로는 정당, 우선순위 낮음.
- (L41) 그 다음 아래 "🚧 진행 중 work-item" 섹션부터 읽으면 됨.
- (L212) > **상태 (2026-06-02)**: 아래 A Phase 2~4 / B Research Router / §17 Step 1~20 항목은 **전부 완료**됐다. 미완료 항목이 아니라 완료 기록의 보존 로그다. 신규 진입은 상단 "다음 세션 최우선 진입점" 참조.
- (L334) 3. **R1 복합 증명** — ⚠️ 2차 실험 완료 (2026-05-25). plan 생성 달성, BLOCKED(정확). 2개 신규 구조 버그 발견.
- (L348) - **다음**: ~~R1 3차 복합 증명 실험~~ → 완료 (아래 참조)
- (L352) - ❌ VERIFY BLOCKED — verification_requirements=[] (F-VERIFY-EMPTY) → 3 bugs found & fixed:
- (L357) - **다음: R1 4차** — F-SCOPE + F-VERIFY 수정 후 end-to-end COMPLETE 검증
- (L361) - ❌ VERIFY BLOCKED — 새 버그 발견:
- (L364) - **다음: R1 5차** — `python agent_launcher.py dogfood run "core/utils.py에 median(values: list[int | float]) -> float 함수 추가. 빈 리스트이면 ValueError. tests/test_utils.py에 TestMedian 테스트 클래스 신규 작성." --non-inte
- (L392) **보류 결정 (trace 1회 run 후 재결정)**:
- (L433) - advisory 보류: scope 문자열 입력 시 문자 단위 순회 (af-cross-review Medium advisory)
- (L461) - ❌ **머지 회수 불가**: 라운드에서 작성한 `product()` + `plan_step_count()` + 10건 테스트는 Windows PC `~/.af-dogfood/1779867851-3611529e/worktree/`의 `dogfood/1779867851-3611529e` 브랜치 commit `c4c5c98b`에만 존재. origin push
- (L462) - dogfooding 검증용 dummy 함수라 production 가치 낮음 — 다음 라운드(R1 13차)에서 새 dummy로 동등 검증.
- (L470) - WARN 보류 (advisory): thread-safety 이론, fixture teardown-only 패턴
- (L494) **다음 진입점**:
- (L495) - 다음 production work-item 선정 후 dogfood run 진입 (보류 dogfood run 없음)
- (L531) **보류**: `cli_hook_bridge` 미커밋 — 현재 dirty 없음, 우선순위 낮음.
- (L557) - ⚠️ dogfood auto-merge BLOCKED (CRLF 다중 `^M` 오염 scope_violations) → 수동 cherry-pick으로 처리
- (L564) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations 동일 패턴) → 수동 cherry-pick으로 처리
- (L581) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: docs/runtime_modes.md 등) → 수동 cherry-pick으로 처리
- (L600) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: data/memory/*.json, docs/*.md) → 수동 cherry-pick으로 처리
- (L687) 1. 완료 작업 / 다음 진입점 갱신

Source: `NEXT_STEPS.md` (28건 추출)
