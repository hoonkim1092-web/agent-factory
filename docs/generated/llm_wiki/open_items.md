---
generated_at: 2026-06-12T02:23:27+09:00
source_commit: 6e46dac6
sources:
  - "Master_Blueprint.md"
  - "docs/code_review/code-review.md"
  - "NEXT_STEPS.md"
---

# Open Items — 미완료/보류 항목

> **주의**: 마커(`🚧`/`보류`/`❌`/`⚠️`) 기반 자동 추출 — 불완전할 수 있음.
> 정확한 상태는 NEXT_STEPS.md 원본을 참조.
> Source: NEXT_STEPS.md
> 관련: [[index]] | [[review_patterns]] | [[source_refs]]

- (L8) > **▶ STEP 4-rerun (선택, 다음)**: callers 있는 함수를 pre-commit 게이트로 측정(§5 채워진 상태). 자연 발화 run으로 대체 가능.
- (L11) > **▶▶ 다음 세션 미결 2건 (RMS 3-Tier 완주 → 1건 소진, 2026-06-12)**:
- (L41) - **다음 = WI-B 또는 다른 product-value work-item.**
- (L46) - **STEP 3 (보류)**: dogfood ContextPack 주입 — 기각 이력(메타-재귀), STEP1/2 효과 확인 후 재평가.
- (L52) - **다음 = Step 0 PoC (미실행)**: 격리 임시폴더 복제 → `npx gitnexus@1.6.7 analyze` → 인덱싱시간·DB·impact정확도 측정. ⚠️ analyze가 AGENTS.md/CLAUDE.md/hook 덮어쓰기 위험 → AF 루트 직접 실행 금지.
- (L54) - **다음 = product-value work-item 신규 선정 또는 GitNexus Step 0 PoC.**
- (L58) > - **다음은 product-value work-item** — 내부 파이프라인 배관(planner/premortem/dogfood/research_*) 추가 금지(메타-재귀 함정). 다음 작업은 "AF가 사용자에게 줄 실제 가치"에서 도출.
- (L59) > - **밀린 3건(planner research_findings 본소비 / auto_apply_defaults FSA 배선 / cli_hook_bridge)은 보류** — 전부 내부 배관이고, 가치 판정은 제품 방향(Step 0) 결정 후에만 가능.
- (L94) - **B1 (복잡, 보류)**: 단순 patch task에 멀티에이전트 orchestrator 과분해 — RSE 설계 필요, 별도 세션
- (L95) - **다음 = product-value work-item 신규 선정**
- (L98) - **🎯 다음 세션 진입점 = code-review 문서 전문 mirror**:
- (L102) - 다음 작업: product-value work-item 신규 선정. LLM Wiki 쪽은 Obsidian 탐색 기본 연결 완료.
- (L108) >   - **🔬 격리 누수 원인 진단 (팩트 확정)**: worker dispatch는 **무죄** — runs/*/task.json 22개 전부 `workspace=worktree` 확인. dogfood_state worktree 경로 정상. **진짜 범인 = `core/control_plane_llm.py:122` `workspace=os.getcwd
- (L111) - **🆕 신규 발견 (leak과 별개, 미수정) — 📌 TODO 등록**: **DEVELOP phase 비수렴** — Option 2가 dogfood DEVELOP을 전체 `ProjectPipeline.run()`에 위임하는데, trivial leaf 함수(`geometric_mean`)에도 designer/qa_engineer 등 멀티에이전트 프로젝트를
- (L112) - **⚠️ 처방 제약 (사용자 지시 2026-06-03)**: **단순 캡/비활성화로 처리 금지.** `terminal_per_agent=False` + `max_cycles` 하드 캡 같은 단순 처방은 큰 task에서 정당한 멀티에이전트 작업까지 잘라버림. **지능형으로 바꿔야 함** — task 복잡도(leaf 함수 1개 vs 멀티모듈 프로젝트)를 인
- (L116) - **🎯 다음 세션 진입점**: leak 검증 종료(PASS). ① product-value work-item 선정으로 전환 또는 ② DEVELOP 비수렴 이슈(위 신규 발견) 경량화 — 단 후자는 내부배관이므로 product 방향 확정 후 우선순위 판정.
- (L117) > - **🔧 모델/Provider 라우팅 결함 4건 (2026-06-02 분석, 큐 등록 — 착수: product-value work-item 다음)**: 5턴 deliberation(Claude+Codex 교차)으로 코드 확정. **핵심 사실**: ① 단일 claude_cli 환경에선 `_should_include_model`(cli.py:647)이 `
- (L118) > - **브랜치 사실**: `2026-05-20-research-coverage-gate`가 origin/main 대비 **232 ahead / 3 behind** (dogfood stream 누적). 머지 결정 보류 — 사용자 판단.
- (L121) > 마지막 업데이트: **2026-06-07 KST (Windows)** — **LLM Wiki Obsidian 연동 2단계 완료**. 완료: AST `symbols.md` 연결 + `Master_Blueprint.md` 전문 mirror + `docs/code_review/code-review.md` 전문 mirror(`docs/generated/llm_
- (L123) > **다음 세션 최우선 진입점**: **dogfood detector 인프라 검증 완료 (2026-06-02) — 다음은 ① 실가치 work-item 선정 또는 ② 저우선 정리**. 북극성 epic("AF가 AF를 개발하는 완성 루프")의 `investigation → AI 프롬프트 → production 코드` 고리가 실제 run에서 닫힘이 직접 관측됨
- (L130) >    - **R18 detector 추가 보류**: 후보 3종 전부 부적합 — `mutable_default_arg`(repo 0건), `broad_except`(의도적 best-effort 1050건, CLAUDE.md 명문화), `unused_import`(TYPE_CHECKING/`__all__` false-positive 97건). detecto
- (L133) >    - **다음**: R18 재평가 (배선 실효성 확정 → R18 게이트 해제됨). 선택적: R15~R17을 change-relative(변경 함수 한정)로 좁힐지 설계 검토 — 단 whole-file 스캔도 "파일 수정 시 기존 복잡도 인지" 의도로는 정당, 우선순위 낮음.
- (L151) 그 다음 아래 "🚧 진행 중 work-item" 섹션부터 읽으면 됨.
- (L322) > **상태 (2026-06-02)**: 아래 A Phase 2~4 / B Research Router / §17 Step 1~20 항목은 **전부 완료**됐다. 미완료 항목이 아니라 완료 기록의 보존 로그다. 신규 진입은 상단 "다음 세션 최우선 진입점" 참조.
- (L444) 3. **R1 복합 증명** — ⚠️ 2차 실험 완료 (2026-05-25). plan 생성 달성, BLOCKED(정확). 2개 신규 구조 버그 발견.
- (L458) - **다음**: ~~R1 3차 복합 증명 실험~~ → 완료 (아래 참조)
- (L462) - ❌ VERIFY BLOCKED — verification_requirements=[] (F-VERIFY-EMPTY) → 3 bugs found & fixed:
- (L467) - **다음: R1 4차** — F-SCOPE + F-VERIFY 수정 후 end-to-end COMPLETE 검증
- (L471) - ❌ VERIFY BLOCKED — 새 버그 발견:
- (L474) - **다음: R1 5차** — `python agent_launcher.py dogfood run "core/utils.py에 median(values: list[int | float]) -> float 함수 추가. 빈 리스트이면 ValueError. tests/test_utils.py에 TestMedian 테스트 클래스 신규 작성." --non-inte
- (L502) **보류 결정 (trace 1회 run 후 재결정)**:
- (L543) - advisory 보류: scope 문자열 입력 시 문자 단위 순회 (af-cross-review Medium advisory)
- (L571) - ❌ **머지 회수 불가**: 라운드에서 작성한 `product()` + `plan_step_count()` + 10건 테스트는 Windows PC `~/.af-dogfood/1779867851-3611529e/worktree/`의 `dogfood/1779867851-3611529e` 브랜치 commit `c4c5c98b`에만 존재. origin push
- (L572) - dogfooding 검증용 dummy 함수라 production 가치 낮음 — 다음 라운드(R1 13차)에서 새 dummy로 동등 검증.
- (L580) - WARN 보류 (advisory): thread-safety 이론, fixture teardown-only 패턴
- (L604) **다음 진입점**:
- (L605) - 다음 production work-item 선정 후 dogfood run 진입 (보류 dogfood run 없음)
- (L641) **보류**: `cli_hook_bridge` 미커밋 — 현재 dirty 없음, 우선순위 낮음.
- (L667) - ⚠️ dogfood auto-merge BLOCKED (CRLF 다중 `^M` 오염 scope_violations) → 수동 cherry-pick으로 처리
- (L674) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations 동일 패턴) → 수동 cherry-pick으로 처리
- (L691) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: docs/runtime_modes.md 등) → 수동 cherry-pick으로 처리
- (L710) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: data/memory/*.json, docs/*.md) → 수동 cherry-pick으로 처리
- (L797) 1. 완료 작업 / 다음 진입점 갱신

Source: `NEXT_STEPS.md` (43건 추출)
