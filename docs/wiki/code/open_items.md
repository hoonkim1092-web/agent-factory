---
generated_at: 2026-06-24T23:44:49+09:00
source_commit: e1912719
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

- (L32) > **대안**: 신규 product work-item 발굴(메인). STAGE 3은 자가진화 인프라 — product value 우선이면 보류 가능.
- (L34) > **미결(보류)**:
- (L39) > - S2-3 advisory 보류(WARN, correctness 무관): distill `gethostname()` 중복 호출(F7)·ControlPlaneLLM 첫 hook latency(F8) — 둘 다 실질 위험 없음.
- (L51) > - **3-Tier**: af-critic **PASS**(발견 0) / af-cross-review **WARN [single-vendor]** BLOCK 0(Advisory Low 2건 보류) / af-test-runner **PASS**(41).
- (L59) > - **3-Tier**: af-critic BLOCK 2(sk-proj-/sk-ant- 누락·JSON 라벨 누락 = secret 누출, 둘 다 수정)+WARN 3(hex오탐·경로prefix 수정/싱글턴 보류) / af-cross-review **BLOCK High 1**(test raw subprocess WinError 6 → `_git` stdin=
- (L68) > - **3-Tier**: af-critic BLOCK 1=오탐(`partition(":")` 첫콜론만 분리→timezone 보존, 테스트로 실증 반증)·WARN 2(gethostname 가드 적용/atomic-write 보류) / af-cross-review **PASS BLOCK 0**(single-vendor, codex rate-limit) / a
- (L79) > **다음**: STAGE 1 (`core/knowledge/note.py`) — KnowledgeNote 스키마 + frontmatter 계약 정의. 또는 새 product work-item 발굴.
- (L85) > **`/output` 슬래시 명령 신규** (`570b3258`): AF 대화형 세션에서 `/output <경로>`로 결과 저장 폴더를 한 줄로 변경, `/output`으로 현재 위치 확인. `core/interactive_chat.py` `handle_command` + `set_output_dir()`(따옴표 제거·`makedirs(exist_ok)
- (L110) > - ⚠️ **백그라운드 worktree 에이전트 사고 기록**: Fix 3 위임 에이전트가 보고 없이 `_run_provider`를 subprocess 직접호출로 통째 재작성(INV-8 깸) + agent `.md`/`.toml`을 stale 버전으로 덮어써 LLM Wiki 청킹·review_bundle·MCP fallback·Consensus Gate
- (L139) > 다음 = 신규 product work-item 발굴 또는 Review BLOCK Learning Phase 2 (자연 데이터 ≥3회 재발 대기)
- (L153) > 다음 작업 = 새 product work-item 발굴 또는 Phase 2 설계(자연 데이터 대기).
- (L172) > **다음 순서**: 설계문서(Opus) → 교차검증 → 코드+테스트(Sonnet)
- (L212) > 우선순위5 규모인지 분해(B안) 구현·검증 완료(2026-06-20). 다음은 신규 product-value work-item 선정 또는 보류 트랙.
- (L221) > - **3-Tier**: af-critic PASS / af-cross-review R1 BLOCK(F1·F2)→R2 WARN(해소, BLOCK 0; F-NEW-1 fallback QA는 INV-F1 의도대로 보류) / af-test-runner PASS(64).
- (L223) > - **보류(Part 4)**: Tier3-small → minimal 분해는 분해축≠리뷰축 분리 필요(현 B안은 Tier3=standard). gear 승격은 2번째 소비자 생기면(우선순위3 doc 재활용).
- (L238) **다음 세션 할 일 (우선순위5 = `core/bootstrap_roles.py` + `core/project_pipeline.py`, 둘 다 Tier-3)**:
- (L248) **Part 4 미결(B안에도 해당, 별개 추적)**: Tier3-small(고위험·소규모) → minimal 분해 최적화는 **분해축(규모) ≠ 리뷰축(blast Tier) 분리**가 필요해 보류. 현재 B안은 required_stages에 design 있으면(Floor2가 Tier3에 design 강제) standard 분해 → Tier3 contrac
- (L252) - `docs/2026-06-20-scale-aware-role-decomposition-design.md` — Draft, **B안 표기 완료**, 다음 세션 구현 대상
- (L274) - **▶ 다음 = 우선순위 3·5 별도 설계** (S1~S3 correctness 슬라이스 전부 닫힘). baseline 실코드 동결 완료: `docs/2026-06-20-priority-3-5-baseline-capture.md` (§6.1 right_sized_router / §6.2 bootstrap_roles 정확한 라인 인용). 두 설계는 **각
- (L279) 3. 작은 Tier-3 실행 흐름(build→존재가드→test→review→cross_review) → §6.1 별도 설계 보류
- (L281) **보류(死因 아님, 별개 트랙)**: Tier-3 파일단위 regex → AST proof-carrying(Phase1) / Floor2 주입 억제는 merge∈{never,manual} 조건부 / 과분해는 bootstrap_roles 프롬프트 규모 조건부화.
- (L342) > **선행 조사 (구현 전 필수, §6.2)**: `research_engine.py`/`researcher.py`/`research_brief.py`의 실제 진입 함수 중 "goal 텍스트 → 골/기대출력/seam 후보"를 얻는 경로를 식별하고, 그 반환 구조에서 `output_field`별 값을 뽑는 **어댑터 함수**를 명세. ⚠️ 초안의 `rese
- (L395) > - **실패 B(자기유발 진동)**: 설계문서 경로(`check_design_pending.py`)는 라운드캡·수렴가드 *부재*(코드리뷰는 `MAX_ROUNDS=5` 있음). 매 라운드 내 수정이 다음 BLOCK 유발. → §4 수렴가드+스코프게이트(설계 `MAX_DESIGN_ROUNDS=3`, HOW 모순은 advisory 강등).
- (L418) **미결 산출물**: 설계문서 2건 Draft 완료 — `docs/2026-06-18-user-perspective-qa-pipeline-design.md`(af-cross-review BLOCK 3건 수동수정 완료, **재검증 미실시**) + `docs/2026-06-18-product-output-isolation-design.md`(af-cross-r
- (L444) - **미채택(설계 결정)**: Stop hook 드레인 보류(pre-commit이 실패 케이스 `d1022ecd`를 정확히 차단하는 최소·자족 경로). 부수버그 `_is_watcher_alive` os.kill Windows WinError 87 / watcher codex CreateProcessWithLogonW:1909 단일vendor는 **미수정*
- (L481) > **▶ 다음 = product-value work-item 신규 선정.** GitNexus Step 0 PoC(미실행) 또는 외부 부착 end-to-end 라인 또는 신규 발굴.
- (L493) > - **잔여 advisory(선택)**: `af project wiki` `--out` 기본값을 외부 프로젝트엔 덜 침습적인 경로로 바꿀지(WARN, 의무 아님). **STEP 3(보류)**: dogfood ContextPack 주입은 기각 이력(메타-재귀).
- (L495) > **▶ 다음 = product-value work-item 신규 선정.** GitNexus Step 0 PoC(미실행) 또는 외부 부착 end-to-end 라인 또는 신규 발굴.
- (L504) > **▶ STEP 4-rerun (선택, 다음)**: callers 있는 함수를 pre-commit 게이트로 측정(§5 채워진 상태). 자연 발화 run으로 대체 가능.
- (L507) > **▶▶ 다음 세션 미결 (3건 전부 소진/측정 — 2026-06-12)**:
- (L512) > **▶ 다음 = product-value work-item 신규 선정** (미결 3건 소진). STEP4 side-effect benefit은 자연 dogfood/pre-commit run에서 기회 측정.
- (L539) - **다음 = WI-B 또는 다른 product-value work-item.**
- (L544) - **STEP 3 (보류)**: dogfood ContextPack 주입 — 기각 이력(메타-재귀), STEP1/2 효과 확인 후 재평가.
- (L550) - **다음 = Step 0 PoC (미실행)**: 격리 임시폴더 복제 → `npx gitnexus@1.6.7 analyze` → 인덱싱시간·DB·impact정확도 측정. ⚠️ analyze가 AGENTS.md/CLAUDE.md/hook 덮어쓰기 위험 → AF 루트 직접 실행 금지.
- (L552) - **다음 = product-value work-item 신규 선정 또는 GitNexus Step 0 PoC.**
- (L556) > - **다음은 product-value work-item** — 내부 파이프라인 배관(planner/premortem/dogfood/research_*) 추가 금지(메타-재귀 함정). 다음 작업은 "AF가 사용자에게 줄 실제 가치"에서 도출.
- (L557) > - **밀린 3건(planner research_findings 본소비 / auto_apply_defaults FSA 배선 / cli_hook_bridge)은 보류** — 전부 내부 배관이고, 가치 판정은 제품 방향(Step 0) 결정 후에만 가능.
- (L592) - **B1 (복잡, 보류)**: 단순 patch task에 멀티에이전트 orchestrator 과분해 — RSE 설계 필요, 별도 세션
- (L593) - **다음 = product-value work-item 신규 선정**
- (L596) - **🎯 다음 세션 진입점 = code-review 문서 전문 mirror**:
- (L600) - 다음 작업: product-value work-item 신규 선정. LLM Wiki 쪽은 Obsidian 탐색 기본 연결 완료.
- (L606) >   - **🔬 격리 누수 원인 진단 (팩트 확정)**: worker dispatch는 **무죄** — runs/*/task.json 22개 전부 `workspace=worktree` 확인. dogfood_state worktree 경로 정상. **진짜 범인 = `core/control_plane_llm.py:122` `workspace=os.getcwd
- (L609) - **🆕 신규 발견 (leak과 별개, 미수정) — 📌 TODO 등록**: **DEVELOP phase 비수렴** — Option 2가 dogfood DEVELOP을 전체 `ProjectPipeline.run()`에 위임하는데, trivial leaf 함수(`geometric_mean`)에도 designer/qa_engineer 등 멀티에이전트 프로젝트를
- (L610) - **⚠️ 처방 제약 (사용자 지시 2026-06-03)**: **단순 캡/비활성화로 처리 금지.** `terminal_per_agent=False` + `max_cycles` 하드 캡 같은 단순 처방은 큰 task에서 정당한 멀티에이전트 작업까지 잘라버림. **지능형으로 바꿔야 함** — task 복잡도(leaf 함수 1개 vs 멀티모듈 프로젝트)를 인
- (L614) - **🎯 다음 세션 진입점**: leak 검증 종료(PASS). ① product-value work-item 선정으로 전환 또는 ② DEVELOP 비수렴 이슈(위 신규 발견) 경량화 — 단 후자는 내부배관이므로 product 방향 확정 후 우선순위 판정.
- (L615) > - **🔧 모델/Provider 라우팅 결함 4건 (2026-06-02 분석, 큐 등록 — 착수: product-value work-item 다음)**: 5턴 deliberation(Claude+Codex 교차)으로 코드 확정. **핵심 사실**: ① 단일 claude_cli 환경에선 `_should_include_model`(cli.py:647)이 `
- (L616) > - **브랜치 사실**: `2026-05-20-research-coverage-gate`가 origin/main 대비 **232 ahead / 3 behind** (dogfood stream 누적). 머지 결정 보류 — 사용자 판단.
- (L619) > 마지막 업데이트: **2026-06-07 KST (Windows)** — **LLM Wiki Obsidian 연동 2단계 완료**. 완료: AST `symbols.md` 연결 + `Master_Blueprint.md` 전문 mirror + `docs/code_review/code-review.md` 전문 mirror(`docs/generated/llm_
- (L621) > **다음 세션 최우선 진입점**: **dogfood detector 인프라 검증 완료 (2026-06-02) — 다음은 ① 실가치 work-item 선정 또는 ② 저우선 정리**. 북극성 epic("AF가 AF를 개발하는 완성 루프")의 `investigation → AI 프롬프트 → production 코드` 고리가 실제 run에서 닫힘이 직접 관측됨
- (L628) >    - **R18 detector 추가 보류**: 후보 3종 전부 부적합 — `mutable_default_arg`(repo 0건), `broad_except`(의도적 best-effort 1050건, CLAUDE.md 명문화), `unused_import`(TYPE_CHECKING/`__all__` false-positive 97건). detecto
- (L631) >    - **다음**: R18 재평가 (배선 실효성 확정 → R18 게이트 해제됨). 선택적: R15~R17을 change-relative(변경 함수 한정)로 좁힐지 설계 검토 — 단 whole-file 스캔도 "파일 수정 시 기존 복잡도 인지" 의도로는 정당, 우선순위 낮음.
- (L649) 그 다음 아래 "🚧 진행 중 work-item" 섹션부터 읽으면 됨.
- (L820) > **상태 (2026-06-02)**: 아래 A Phase 2~4 / B Research Router / §17 Step 1~20 항목은 **전부 완료**됐다. 미완료 항목이 아니라 완료 기록의 보존 로그다. 신규 진입은 상단 "다음 세션 최우선 진입점" 참조.
- (L942) 3. **R1 복합 증명** — ⚠️ 2차 실험 완료 (2026-05-25). plan 생성 달성, BLOCKED(정확). 2개 신규 구조 버그 발견.
- (L956) - **다음**: ~~R1 3차 복합 증명 실험~~ → 완료 (아래 참조)
- (L960) - ❌ VERIFY BLOCKED — verification_requirements=[] (F-VERIFY-EMPTY) → 3 bugs found & fixed:
- (L965) - **다음: R1 4차** — F-SCOPE + F-VERIFY 수정 후 end-to-end COMPLETE 검증
- (L969) - ❌ VERIFY BLOCKED — 새 버그 발견:
- (L972) - **다음: R1 5차** — `python agent_launcher.py dogfood run "core/utils.py에 median(values: list[int | float]) -> float 함수 추가. 빈 리스트이면 ValueError. tests/test_utils.py에 TestMedian 테스트 클래스 신규 작성." --non-inte
- (L1000) **보류 결정 (trace 1회 run 후 재결정)**:
- (L1041) - advisory 보류: scope 문자열 입력 시 문자 단위 순회 (af-cross-review Medium advisory)
- (L1069) - ❌ **머지 회수 불가**: 라운드에서 작성한 `product()` + `plan_step_count()` + 10건 테스트는 Windows PC `~/.af-dogfood/1779867851-3611529e/worktree/`의 `dogfood/1779867851-3611529e` 브랜치 commit `c4c5c98b`에만 존재. origin push
- (L1070) - dogfooding 검증용 dummy 함수라 production 가치 낮음 — 다음 라운드(R1 13차)에서 새 dummy로 동등 검증.
- (L1078) - WARN 보류 (advisory): thread-safety 이론, fixture teardown-only 패턴
- (L1102) **다음 진입점**:
- (L1103) - 다음 production work-item 선정 후 dogfood run 진입 (보류 dogfood run 없음)
- (L1139) **보류**: `cli_hook_bridge` 미커밋 — 현재 dirty 없음, 우선순위 낮음.
- (L1165) - ⚠️ dogfood auto-merge BLOCKED (CRLF 다중 `^M` 오염 scope_violations) → 수동 cherry-pick으로 처리
- (L1172) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations 동일 패턴) → 수동 cherry-pick으로 처리
- (L1189) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: docs/runtime_modes.md 등) → 수동 cherry-pick으로 처리
- (L1208) - ⚠️ dogfood auto-merge BLOCKED (CRLF 오염 scope_violations: data/memory/*.json, docs/*.md) → 수동 cherry-pick으로 처리
- (L1295) 1. 완료 작업 / 다음 진입점 갱신

Source: `NEXT_STEPS.md` (72건 추출)
