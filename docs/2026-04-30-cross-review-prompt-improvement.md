# Cross-Review 프롬프트 텍스트 개선 (Phase 1a)

- **작성일**: 2026-04-30
- **상태**: 설계 (검증 대기)
- **로드맵 위치**: P2 — Cross-Review 정확도·범용성 개선 / Phase 1a
- **선행 작업**: P1 Sprint B (`74dfa3c5`) — 동적 fan-out 인프라 완성

---

## 1. 배경

`af-cross-review` sub-agent는 외부 LLM(codex, gemini)에 동일한 리뷰 프롬프트를 fan-out한 뒤 결과를 dedup·판정한다. 현재 프롬프트(`.claude/agents/af-cross-review.md` line 117–136 PROMPT_EOF 블록)는 외부 비평(Codex 본인) 라운드와 내부 분석에서 다음 약점이 드러났다.

| # | 약점 | 결과 |
|---|------|------|
| 1 | **변경 의도 손실** — 전체 파일만 읽게 함, diff 강제 없음 | 외부 LLM이 "변경되지 않은 코드"에 대해 노이즈 지적 |
| 2 | **거짓 양성 방어선 없음** — "발견 없음"을 명시할 자유 없음 | 채우려고 Medium/Low 부풀림 |
| 3 | **file:line 환각** — 인용한 line이 실제로 그 코드인지 검증 단계 없음 | 잘못된 좌표로 dedup 실패 |
| 4 | **모델 가족 sycophancy 무자각** — 같은 모델 가족이 작성한 코드를 검증 중인 사실 미고지 | 자연스러워 보이는 패턴을 의심 없이 통과 |

## 2. 목표 (Phase 1a 한정)

외부 LLM에 보내는 **입력 프롬프트**를 4가지 항목 추가로 보강하고, 출력 파싱에는 **BONUS 섹션 분리 처리 1줄만** 추가한다. 호출 인터페이스(`codex exec`, `gemini -p`), 판정 체계, 항목 추출 로직 본체는 **변경하지 않는다**.

## 3. 비-목표 (다른 Phase로 분리)

| 안건 | Phase | 이번에 다루지 않는 이유 |
|------|-------|-------------------------|
| `codex review` 빌트인 교체 | Phase 1b | 출력 포맷 호환 dry-run 필요 |
| `## Tier 3 판정: BLOCK/WARN/PASS` 출력 명시화 | Phase 2 | 매핑 규칙은 1a 운영 데이터 후 결정 |
| 외부 CLI 상호 fact-check | Phase 3 | 비용·형식 강제 가능성 검증 후 |
| Provider-agnostic orchestrator | β2 | 외부 사용자 수요 ≥ 1건 후 |

## 4. 변경 대상

- **유일 파일**: `.claude/agents/af-cross-review.md`
- **변경 범위**:
  - **Step 1**: diff 추출 한 줄(`DIFF_CONTENT=...`) + `/tmp/af-diff-content.txt` 쓰기 한 줄 추가
  - **Step 2**: PROMPT_EOF heredoc 블록(line 117–136) 교체 + placeholder 치환에 `DIFF_CONTENT_PLACEHOLDER` 1줄 추가
  - **Step 3**: dedup 로직에 "No BLOCK-level findings" 라인 무시 + BONUS 카테고리 분리 처리 (총 2~3줄)
- **변경 미만**: Step 0(provider gate), Step 4(보고 형식)

## 5. 추가 항목 4가지 (상세)

### 5.1 diff 컨텍스트 임베드

**왜**: 변경되지 않은 코드에 대한 노이즈 지적을 제거하고, 변경 의도를 명시.

**어떻게**: Step 1에서 이미 만든 `git diff`를 프롬프트 안에 임베드.

```bash
# Step 1에서 추가 (또는 Step 2 진입 직전)
DIFF_CONTENT=$(git diff HEAD~1 -- $CHANGED_FILES 2>/dev/null \
  || git diff -- $CHANGED_FILES 2>/dev/null)
```

프롬프트 본문에 다음 블록 추가 (해법 c+ 채택, 2026-04-30):

```
[변경 diff]
DIFF_CONTENT_PLACEHOLDER

[리뷰 지시 — 출력 카테고리 분리]
검토 결과는 두 카테고리로 분리해서 출력한다:

[PRIMARY] — 메인 검토 대상 (BLOCK/WARN 판정 영향 O)
  (i)  diff에 나타난 변경 심볼 자체의 결함
  (ii) 그 변경이 호출자/피호출자에 미치는 직접 영향
       (시그니처/타입/예외 호환성, 호출자 가정 위반,
        상수·플래그 의미 변경, 캐시 무효화 누락 등)

[BONUS] — 변경과 무관한 발견 (advisory only, BLOCK/WARN 판정 제외)
  (iii) 호출자/피호출자 코드에서 발견된 변경 무관 결함
        — Critical/High만 보고 (Medium 이하는 노이즈로 간주, 무시)
        — 각 항목 머리에 "변경 무관" 라벨 명시 필수
        — 변경의 영향인지 무관인지 모호하면 BONUS에 둔다 (보수적 처리)
```

**임계값 정책**: diff 크기 처리는 §8 위험 테이블의 50KB 기준 단일 적용. 50KB 초과 시 `--stat`만 임베드, 본문 생략.

### 5.2 거짓 양성 방어선 — "No BLOCK-level findings" 명시 허용

**왜**: LLM은 "지적 0건"을 회피하려 Medium/Low를 부풀림. 명시적으로 "0건이 정상적인 결과"임을 알려야 함.

**어떻게**: 프롬프트 끝에 다음 한 줄 추가.

```
8. Critical/High에 해당하는 결함이 없으면 "No BLOCK-level findings" 라고 명시해라.
   채우려고 Medium/Low를 부풀리지 마라. 진짜로 발견된 것만 보고해라.
```

**부수 효과**: Phase 2에서 BLOCK/WARN 매핑할 때 "BLOCK-level finding 0건 → PASS" 결정의 근거가 됨.

### 5.3 file:line 인용 출력 직전 자기검증

**왜**: LLM은 line number를 자주 환각함. 인용이 잘못되면 dedup·합의★ 로직 모두 실패.

**어떻게**: 프롬프트 끝에 다음 한 줄 추가.

```
9. 출력 직전 자기 검증:
   각 file:line 인용에 대해 해당 라인을 다시 읽고, 인용한 코드 단편이
   실제 그 라인에 있는지 확인해라. 일치하지 않으면 그 항목을 제거해라.
```

**비용·효과**: 외부 LLM이 파일을 한 번 더 읽음 (단, provider별 보장 차이 있음).
- **codex** (`codex exec -s danger-full-access`): tool call 가능 → 실제 파일 재읽기 보장
- **gemini** (`gemini --yolo -p`): 단발 응답 모드 → 응답 생성 중 추론 내에서만 동작, 실제 재읽기 보장 X
- **결과 기대치**: 환각 일부 제거 효과 (대규모 dedup 정확도 향상은 dry-run에서 측정 후 판단). codex 결과는 신뢰 가능, gemini 결과는 효과 약할 수 있음.

### 5.4 모델 가족 sycophancy 메타지시

**왜**: 외부 LLM이 검증 중인 코드를 작성한 모델(Claude)과 자기 자신이 같은 LLM 가족일 때, 익숙한 패턴을 의심 없이 통과시킬 수 있음. 메타 인식 강제.

**어떻게**: 프롬프트 시작부에 다음 한 줄 추가.

```
[메타 인식]
이 코드는 다른 AI 모델이 작성했다. 자연스러워 보이는 패턴이라도 의심해라.
"AI가 흔히 쓰는 관용구라서 OK"는 근거가 아니다. 실제 동작·경계·예외 처리를 확인해라.
```

**결정 대기**: 정확한 워딩.
**제 권장**: 위 워딩 그대로 — "sycophancy"라는 학술 용어는 LLM이 무시할 수 있어 일상어로 표현.

## 6. 변경 전·후 프롬프트 (Step 2 PROMPT_EOF 블록)

### Before (현재, 16줄)

```
이 프로젝트는 Agent Factory (AI 에이전트 팩토리)이다.

[지시사항]
1. 먼저 REVIEW_DOC_PLACEHOLDER 를 읽어라. ...
2. 다음 변경된 파일들을 직접 읽어라: CHANGED_FILES_PLACEHOLDER
3. 각 변경 파일의 호출자/피호출자도 찾아서 읽어라.
4. 코드 리뷰 문서의 기존 지적 사항과 비교 ...
5. 아래 관점에서 리뷰해라: 버그 / 안전성 / 성능 / 설계 결함 / 누락된 엣지 케이스
6. 각 항목에 심각도(Critical/High/Medium/Low), 파일명:라인번호, 코드 인용을 포함해라.
7. 일반적인 조언은 하지 마. 이 프로젝트 코드에 특화된 지적만 해라.
```

### After (제안, 약 35줄 — c+ 카테고리 분리 반영)

```
이 프로젝트는 Agent Factory (AI 에이전트 팩토리)이다.

[메타 인식]
이 코드는 다른 AI 모델이 작성했다. 자연스러워 보이는 패턴이라도 의심해라.
"AI가 흔히 쓰는 관용구라서 OK"는 근거가 아니다. 실제 동작·경계·예외 처리를 확인해라.

[변경 diff]
DIFF_CONTENT_PLACEHOLDER

[지시사항]
1. 먼저 REVIEW_DOC_PLACEHOLDER 를 읽어라. ... (기존 유지)
2. 검토 대상 카테고리 분리:
   [PRIMARY] (BLOCK/WARN 판정 영향 O)
     (i)  diff 변경 심볼 자체의 결함
     (ii) 변경이 호출자/피호출자에 미치는 직접 영향
          (시그니처/타입/예외 호환성, 호출자 가정 위반,
           상수·플래그 의미 변경, 캐시 무효화 누락 등)
   [BONUS] (advisory only, BLOCK/WARN 판정 제외)
     (iii) 호출자/피호출자에서 발견된 변경 무관 결함 — Critical/High만 보고
          ("변경 무관" 라벨 필수, 모호하면 BONUS에 둔다)
3. 다음 변경된 파일들을 직접 읽어라: CHANGED_FILES_PLACEHOLDER
4. 각 변경 파일의 호출자/피호출자도 읽어라 — 목적 (i) 변경 의도 파악,
   (ii) 변경의 영향 범위 검증, (iii) 명백한 무관 결함(BONUS) 식별
5. 코드 리뷰 문서의 기존 지적 사항과 비교 ... (기존 유지)
6. 아래 관점에서 리뷰해라: 버그 / 안전성 / 성능 / 설계 결함 / 누락된 엣지 케이스
7. 각 항목에 심각도(Critical/High/Medium/Low), 파일명:라인번호, 코드 인용을 포함해라.
8. 일반적인 조언은 하지 마. 이 프로젝트 코드에 특화된 지적만 해라.
9. PRIMARY 카테고리에 Critical/High 결함이 없으면 "No BLOCK-level findings"
   라고 명시해라. 채우려고 Medium/Low를 부풀리지 마라. (BONUS는 별도 집계)
10. 출력 직전 자기 검증: 각 file:line 인용에 대해 해당 라인을 다시 읽고,
    인용한 코드 단편이 실제 그 라인에 있는지 확인해라. 일치하지 않으면 항목 제거.

[출력 형식]
## [PRIMARY]
- ... (변경 영향 결함들)

## [BONUS] — 변경 무관 (advisory only)
- [변경 무관] ... (Critical/High만)
```

## 7. Step 1 변경 (diff 추출)

```bash
# 기존
git diff HEAD~1 --stat
git diff HEAD~1 --name-only
# 또는 작업 중: git diff --stat / git diff --name-only

# 추가 (DIFF_CONTENT 변수 + 임시파일 쓰기)
DIFF_CONTENT=$(git diff HEAD~1 -- $CHANGED_FILES 2>/dev/null || git diff -- $CHANGED_FILES)
printf '%s' "$DIFF_CONTENT" > /tmp/af-diff-content.txt    # B1 — placeholder 치환이 읽을 수 있도록 임시파일에 저장

# 50KB 초과 시 본문 생략, --stat만 임베드 (§8 위험 표 정책)
if [ $(wc -c < /tmp/af-diff-content.txt) -gt 51200 ]; then
  git diff HEAD~1 --stat -- $CHANGED_FILES > /tmp/af-diff-content.txt 2>/dev/null \
    || git diff --stat -- $CHANGED_FILES > /tmp/af-diff-content.txt
  echo "(본문 생략 — 50KB 초과로 --stat만 임베드됨)" >> /tmp/af-diff-content.txt
fi

# Step 2의 placeholder 치환에 추가
python3 - << PYEOF
txt = open('/tmp/af-review-prompt.txt').read()
txt = txt.replace('REVIEW_DOC_PLACEHOLDER', '${REVIEW_DOC}')
txt = txt.replace('CHANGED_FILES_PLACEHOLDER', '${CHANGED_FILES}')
txt = txt.replace('DIFF_CONTENT_PLACEHOLDER', open('/tmp/af-diff-content.txt').read())
open('/tmp/af-review-prompt.txt', 'w').write(txt)
PYEOF
```

## 8. 위험 및 완화

| 위험 | 가능성 | 영향 | 완화 |
|------|--------|------|------|
| diff가 너무 커서 토큰 한도 초과 | 中 | 호출 실패 | Step 1에서 diff 크기 측정, 50KB 초과 시 `--stat`만 임베드하고 본문 생략 (구현됨) |
| 외부 LLM이 메타 인식 지시를 무시 | 中 | 메타지시 효과 0 | dry-run에서 sycophancy 패턴 변화 측정. 효과 없으면 다음 라운드에 워딩 보강 |
| "No BLOCK-level findings" 출력이 dedup 로직과 충돌 | 低 | Step 3 파싱 실패 | dedup 로직에서 "No BLOCK-level" 문구 무시 처리 1줄 추가 |
| BONUS 카테고리가 dedup·합의★ 로직과 충돌 | 中 | Step 3 파싱 실패 | dedup 로직에서 BONUS 섹션은 dedup·합의★ 미적용 1줄 추가, advisory로만 표시 |
| file:line 자기검증 단계가 외부 LLM의 timeout 한도(180s) 초과 | 低 | 결과 누락 | 현재 timeout 여유 있음. 측정 후 필요 시 240s로 확대 |
| **gemini의 자기검증·BONUS 분류 효과 미보장** (단발 응답 모드) | 中 | 환각 제거 효과 ½로 감소, BONUS/PRIMARY 분류 부정확 가능 | dry-run에서 provider별 측정. codex 결과를 우선 신뢰. gemini 한정 효과 검증 후 필요 시 프롬프트 워딩 보강 |
| 프롬프트 길이 증가로 비용 ↑ | 中 | 토큰 비용 약 40% 증가 추정 (c+ 카테고리 분리 포함) | cross-review 1회당 미미. 무시 가능 |
| LLM이 PRIMARY/BONUS 경계를 모호하게 분류 | 中 | 결함이 잘못된 카테고리에 가서 BLOCK 판정 오류 | 프롬프트의 "모호하면 BONUS에 둔다" 보수 규칙으로 BLOCK 오인은 차단. PRIMARY 누락은 dry-run에서 측정 |

## 9. 롤백 전략

- 변경 위치는 **단일 파일** (`.claude/agents/af-cross-review.md`).
- 롤백 = `git revert <커밋>` 1회.
- 부수 영향: `core/*.py` 변경 없음, 테스트 변경 없음, Master_Blueprint.md 본문 변경 없음(§12 이력만 추가).

## 10. 검증 계획

### 10.1 사전 검증 (이 설계문서)

- CLAUDE.md 규칙: "단일 설계문서 작성 후 af-critic + af-cross-review 2개 병렬 실행" → `scripts/check_design_pending.py`가 자동 큐잉.

### 10.2 구현 후 dry-run

1. 최근 커밋(`b76a6652` ensure_watcher TOCTOU 수정) 또는 sample 변경에 대해 새 프롬프트로 cross-review 1회 실행.
2. **필수 측정 항목 (4개)**:
   - ① PRIMARY 섹션에 "No BLOCK-level findings" 또는 합리적 BLOCK 항목 존재
   - ② 모든 file:line 인용이 실제 코드와 일치
   - ③ PRIMARY 섹션에 diff 무관 코드 지적 0건
   - ④ BONUS 섹션 정상 분류 — 각 항목 "변경 무관" 라벨 + Critical/High만, Medium 이하 0건
3. **선택 측정 항목 (메타 인식 효과)**: 같은 코드에 대해 메타 인식 지시 있음/없음 두 번 실행 후 패턴 의심 깊이 비교 — A/B 비교가 필요하므로 통과 기준에서는 제외, 별도 보고서로 기록.

### 10.3 통과 기준

- ① 외부 LLM 호출이 정상 종료(180s 이내)
- ② 결과 파싱 정상(PRIMARY/BONUS 분리 + dedup 로직 동작)
- ③ §10.2 필수 측정 4항목 중 **≥ 3개 충족** (BONUS 분류는 codex만 신뢰, gemini는 부정확 허용)

통과 시 → 커밋 + Master_Blueprint.md §12 갱신.
미통과 시 → 항목별 보강 후 재시도 (max 2회, CLAUDE.md max_rounds 정책 준수).

## 11. 결정 사항 (2026-04-30 1라운드 검증 후 확정)

| # | 항목 | 결정 |
|---|------|------|
| 1 | 메타 인식 워딩 | §5.4 워딩 그대로 채택 |
| 2 | diff 임베드 범위 | 그대로 임베드, 50KB 초과 시만 `--stat`만 — §7에 구현 반영 |
| 3 | "No BLOCK-level findings" 문구 | 영문 그대로 |
| 4 | 자기검증 단계 위치 | 출력 직전 (지시사항 끝) |
| 5 | B3 해법 (호출자 처리) | **(c+) 채택** — PRIMARY/BONUS 분리 보고 |
| 6 | gemini 재인증 | Phase 1b 시작 시 선행 조건으로 처리 (NEXT_STEPS에 명시) |
| 7 | provider_detect.py ThreadPool 버그 | 별도 BLOCK work-item으로 분리 (NEXT_STEPS에 등록) |

## 12. 다음 단계 (이 문서 승인 후)

1. ~~af-critic + af-cross-review 2-agent 병렬 검증~~ ✅ 완료 (2026-04-30 1라운드)
2. ~~검증 결과의 BLOCK 4건 반영 (c+ 채택, gemini 한계 명시 등)~~ ✅ 본 문서에 반영 완료
3. `.claude/agents/af-cross-review.md` Step 1 + Step 2 + Step 3 dedup 1줄 수정 — **별도 라운드** (사용자 GO 신호 후)
4. **선행 차단**: `core/provider_detect.py` ThreadPool 버그 수정 (NEXT_STEPS의 별도 BLOCK 항목)
5. dry-run 1회 (§10.2)
6. 통과 시 커밋 + Master_Blueprint.md §12 갱신
7. 1주일 운영 데이터 관찰 후 Phase 2 매핑 규칙 결정으로 진행

---

**참조 파일**:
- `.claude/agents/af-cross-review.md` (변경 대상)
- `core/provider_detect.py` (Step 0 의존, 변경 없음)
- `scripts/check_design_pending.py` (이 문서를 자동 큐잉)
- `NEXT_STEPS.md` P2 섹션 (Phase 1a 체크박스)
