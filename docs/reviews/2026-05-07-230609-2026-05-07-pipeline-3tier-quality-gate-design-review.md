# Design Review: 2026-05-07-pipeline-3tier-quality-gate

> Source: docs/2026-05-07-pipeline-3tier-quality-gate.md
> Date: 2026-05-07 23:06
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

Now I have the full picture. Let me produce the aggregated verdict.

## Final Design Review

### Verdict: BLOCK

3개 Critical 이슈(양 리뷰어 공통 2건 + Critic 단독 1건)가 구현 진입을 차단. v2가 v1 BLOCK을 해소했다고 주장하나 `_refine_document` 위치 오기, `fix_instructions` 생산자 부재, SKIP 점수 모순이 여전함.

### Aggregated Findings (13 total)

#### 1. [ACCEPT] [Critical] `_refine_document` 위치 오기 — review_report.py에서 호출 안 함
- **Critic**: §3.6 line 372가 "`_refine_document`는 review_report.py 호출 흐름에 존재"라 하나, 실제 정의는 `work_item_generator.py:889`, 호출자는 `project_pipeline.py:1032`와 `doc_qa/skill.py:108` 뿐. review_report.py에 import/호출 0건.
- **Cross**: not flagged directly, but Cross Finding #4가 retry 흐름의 underspecification을 지적하며 같은 근본 원인을 건드림.
- **Judgment**: grep으로 확인 가능한 사실 오기. v1 BLOCK #1이 미해결.
- **Action Required**: §3.6을 정정 — `_refine_document`의 실제 위치(`work_item_generator.py:889`)와 호출자 2곳을 명시. T1 retry 경로가 이를 재사용하려면 호출 지점을 §3.3.3에 구체 명시.

#### 2. [ACCEPT] [Critical] `fix_instructions` 생산자 부재 — T1/T2 retry dead code
- **Critic**: `JudgeResult.fix_instructions`는 `review_report.py:50`에서 default `{}`로 선언만, 실제로 채워지는 곳 없음. `aggregated_output` → `fix_instructions` dict 파서가 §3 어디에도 없어 retry 루프가 항상 빈 dict로 진입.
- **Cross**: Finding #4 — "BLOCK confidence and retry behavior remain underspecified". `fix_instructions` defaults empty, AUTH_EXPIRED BLOCK에 fix instructions 없어 retry 무의미.
- **Judgment**: 양 리뷰어 공통. 코드 레벨에서 확인 가능. retry 설계의 핵심 결함.
- **Action Required**: ① `aggregated_output`에서 `{doc_name: feedback}` dict를 파싱하는 producer를 §3.3.2에 명시, 또는 ② T1/T2 retry를 v2 범위에서 제거하고 §7 미해결로 분리.

#### 3. [ACCEPT] [Critical] SKIP → 1.0 매핑이 §1.2 D4 "메트릭 오염" 동기와 모순
- **Critic**: `SKIP=1.0 + confidence=1.0`이면 `cv_score=1.0`으로 PASS와 동일. D4가 비판한 "미검증=통과 기록"이 그대로 유지. SKIP 도입 명분 자체가 사라짐.
- **Cross**: Finding #7 (HOLD) — "verified pass와 not verified가 수치적으로 동일. quality score가 deployability인지 verified quality인지 제품 판단 필요."
- **Judgment**: 양 리뷰어 공통. Critic이 `pipeline_quality.py:118-122`의 수식까지 추적해 PASS=SKIP 동치를 증명. Cross는 HOLD로 분류했으나 Critic의 코드 근거가 강함 — severity 상향.
- **Action Required**: 둘 중 하나 — (a) `SKIP=0.0` + `evaluate()`에서 SKIP일 때 cross 가중치를 0으로 재분배(line 134 패턴), 또는 (b) D4를 "메트릭 분리 표시"로만 한정해 SKIP=1.0 정당화 후 verified flag 추가.

#### 4. [ACCEPT] [High] T1 retry 호출 컨트랙트 미정의
- **Critic**: `run_structural_gate`는 per-document feedback 없이 단일 rubric score만 반환. `_refine_document`는 단일 문서 + 문자열 feedback 시그니처. multi-doc에 어떤 문서에 어떤 feedback을 줄지 매핑 불가. "implementation 단계로 위임"은 v1 BLOCK 사유 반복.
- **Cross**: not flagged directly.
- **Judgment**: Critic 단독이나 코드 시그니처 근거가 강함. §3.3.3 line 200의 "자세한 호출 패턴은 implementation 단계" 표현이 문제.
- **Action Required**: T1 결과 스키마를 `{"pass": bool, "fix_instructions": {filename: feedback}}`로 확장하든, T1 retry를 제거하든 §3에서 결정.

#### 5. [ACCEPT] [High] dynamic max_rounds=1 — §3.5 매트릭스와 충돌
- **Critic**: `review_report.py:238`에서 dynamic은 항상 `max_rounds=1` → T2 BLOCK은 retry 없이 즉시 WARN 강등. §3.5 매트릭스의 "T2 BLOCK → retry → 여전히 BLOCK" 행과 충돌.
- **Cross**: not flagged.
- **Judgment**: 코드 하드코딩 확인 가능. §3.5 표가 실제 동작과 불일치.
- **Action Required**: §3.5 매트릭스에 dynamic/enterprise 분리 행 추가, 또는 `max_rounds` 로직 변경을 명시.

#### 6. [ACCEPT] [High] AUTH_EXPIRED 1개 → 전체 BLOCK이 G2와 충돌
- **Critic**: codex+gemini 정상 + claude 만료 시, AVAILABLE 2개로 G2 충족하지만 G5가 즉시 BLOCK. 가용 provider로 cross 가능한데 검증 자체를 거부.
- **Cross**: Finding #5 — Codex auth probe가 `--version`만 확인, 실제 인증 검증 안 됨.
- **Judgment**: Critic이 G2/G5 충돌의 논리적 모순을 지적. Cross가 probe 자체의 신뢰성 문제를 추가로 제기. 둘 다 유효.
- **Action Required**: BLOCK 조건을 `len(AVAILABLE) < 2 and len(AUTH_EXPIRED) >= 1`로 좁힘. Codex auth probe는 §7 미해결로 분리하거나 G5 보장 대상에서 제외 명시.

#### 7. [ACCEPT] [High] `detect_providers` 시맨틱 변경 — 기존 호출자 영향 미분석
- **Critic**: 변경 전 `shutil.which`(설치 여부만) → 변경 후 인증까지 확인. 기존 호출자 영향 분석 없음. auth ping subprocess 3개 실행으로 latency 수백 ms 증가.
- **Cross**: not flagged.
- **Judgment**: Critic 단독이나 시맨틱 변경의 영향 분석 부재는 실질적 위험.
- **Action Required**: `detect_providers` 호출자 grep 결과를 §4 Blast Radius에 첨부. 캐시 첫 호출 latency를 §3.8에 추가.

#### 8. [ACCEPT] [High] Canonical work-item 문서 세트 불일치
- **Critic**: not flagged.
- **Cross**: Finding #1 — 설계는 4종이나 `generate_work_items()`는 5종 생성(`implementation-design.md` 포함). `project_pipeline.py`는 `approval-gate.md` 제외. `DocQASkill`은 `implementation-design.md` 로드.
- **Judgment**: Cross가 코드 3곳 인용으로 입증. rubric yaml과 실제 생성 문서가 불일치하면 T1 gate가 false negative/positive 발생.
- **Action Required**: canonical 문서 세트를 5종(generator 출력 전체)으로 확정하고, rubric yaml + `_load_doc_contents` + `DocQASkill._load_documents()`를 동일 리스트로 통일.

#### 9. [ACCEPT] [High] Cross-review 결과가 pipeline에서 버려짐
- **Critic**: not flagged.
- **Cross**: Finding #3 — `cross_review_result`는 `prepare_documents()`에서 local 변수로 print 후 drop. `PreparedProject`에 quality-gate 필드 없음. `pipeline_quality` SKIP 매핑이 이 경로에서 실질 효과 없음.
- **Judgment**: Cross가 코드 3곳(`project_pipeline.py:984,1064,1100`) 인용으로 입증. SKIP/PASS 매핑을 설계해도 결과를 저장·전달 안 하면 무의미.
- **Action Required**: `PreparedProject`에 `cross_review_result` 필드 추가, checkpoint metadata에 포함, `AggregatedVerdict.evaluate()`로 라우팅.

#### 10. [ACCEPT] [Medium] Rubric field dot-path가 파일명 dot과 충돌
- **Critic**: Finding #8 — `_run_check`는 if-elif 체인(dispatch table 아님). `documents.feature-spec.md` 같은 dot-path는 `artifact.get(field_name)`으로 resolve 불가.
- **Cross**: Finding #2 — 동일 문제. dot resolver가 md 파일명의 dot과 충돌.
- **Judgment**: 양 리뷰어 공통. 구현 시 즉시 부딪힐 문제.
- **Action Required**: rule handler가 full `artifact` + `check` dict를 받아 `artifact["documents"]["feature-spec.md"]`를 직접 접근하도록 §3.4 수정. generic dot-path 파싱 금지 명시.

#### 11. [ACCEPT] [Medium] Rubric 임계값 스케일 검증 부재
- **Critic**: Finding #9 — `RubricResult.total_score` 정규화 여부 미확인. 기존 rubric yaml의 `thresholds.pass` 값 비교 없음.
- **Cross**: not flagged.
- **Judgment**: 기존 yaml 2개의 threshold를 1줄 인용하면 해결. 낮은 비용, 높은 가치.
- **Action Required**: §3.4.2 footnote에 기존 rubric (`architecture_plan.yaml`, `research_report.yaml`)의 `thresholds.pass` 값 직접 인용.

#### 12. [REJECT] [Low] `af.spec` hiddenimport 즉시 패치 필요
- **Source**: Cross Finding #6
- **Original Finding**: `core.provider_detect` import가 frozen build에서 깨질 수 있음.
- **Rejection Reason**: Cross 자체가 REJECT. `af.spec:71,166`에 이미 등록 확인됨.

#### 13. [ACCEPT] [Medium] 테스트 계획 — 핵심 컨트랙트 미포함
- **Critic**: Finding #10 — T1 per-doc feedback 생산, T2 `fix_instructions` 파서에 대한 단위 테스트 누락.
- **Cross**: not flagged.
- **Judgment**: Finding #2, #4의 직접적 파생. 컨트랙트가 정의되면 테스트도 따라와야 함.
- **Action Required**: (a) `run_structural_gate` 결과 → `fix_instructions` dict 변환 단위 테스트, (b) `aggregated_output` → `fix_instructions` 파서 단위 테스트를 §5에 추가.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_refine_document` 위치 오기 | Critical | ACCEPT | Critic |
| 2 | `fix_instructions` 생산자 부재 | Critical | ACCEPT | Both |
| 3 | SKIP→1.0 vs D4 메트릭 오염 모순 | Critical | ACCEPT | Both |
| 4 | T1 retry 호출 컨트랙트 미정의 | High | ACCEPT | Critic |
| 5 | dynamic max_rounds=1 vs §3.5 충돌 | High | ACCEPT | Critic |
| 6 | AUTH_EXPIRED 전체 BLOCK vs G2 | High | ACCEPT | Both |
| 7 | detect_providers 호출자 영향 미분석 | High | ACCEPT | Critic |
| 8 | Canonical 문서 세트 불일치 (4종 vs 5종) | High | ACCEPT | Cross |
| 9 | cross_review_result 파이프라인에서 소실 | High | ACCEPT | Cross |
| 10 | Rubric dot-path vs 파일명 dot 충돌 | Medium | ACCEPT | Both |
| 11 | Rubric 임계값 스케일 미검증 | Medium | ACCEPT | Critic |
| 12 | af.spec hiddenimport | Low | REJECT | Cross |
| 13 | 테스트 계획 핵심 누락 | Medium | ACCEPT | Critic |

### Recommendations

v3 작성 시 우선 해결 순서:

1. **Critical 3건 먼저 해소** — Finding #1~#3 없이는 구현 진입 불가
   - `_refine_document` 실제 위치·호출자 정정 (또는 T1/T2 retry 제거)
   - `fix_instructions` producer 명시 (또는 retry 전체 §7 분리)
   - SKIP 점수 정책 결정: `SKIP=0.0 + 가중치 재분배` vs `verified flag 분리`
2. **문서 세트 canonical 확정** — 5종으로 통일, rubric yaml 수정 (#8)
3. **G5 AUTH_EXPIRED 정책 완화** — AVAILABLE ≥ 2이면 expired provider 무시 (#6)
4. **cross_review_result 영속화** — PreparedProject 필드 추가 (#9)
5. **§3.5 매트릭스를 dynamic/enterprise 분리** (#5)
6. **dot-path 대신 rule handler 직접 접근** (#10)
7. 나머지 Medium 이하는 위 수정과 병행 가능