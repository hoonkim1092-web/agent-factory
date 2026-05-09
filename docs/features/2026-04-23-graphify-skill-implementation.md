---
title: Graphify 스킬 통합 (구현편)
date: 2026-04-23
status: 구현 완료 — 회귀 검증 대기
owner: HOON-KIM
parent_design: docs/features/2026-04-22-graphify-integration.md
cross_review: af-cross-review (Codex) FIX_FIRST 4건 모두 적용
---

# Graphify 스킬 통합 — 구현편

전일(2026-04-22) 작성한 분석/설계의 후속 구현 기록. Codex 교차검증에서 식별된 4개 fix를 모두 적용했고, Q5(b) action+knowledge skill_id 분리 결정으로 F6도 해소함.

## 1. 결정 요약

| Q | 답 | 근거 |
|---|----|----|
| Q1 v3/v4 | v4 | default 브랜치 |
| Q2 LLM 키 | 무관 | 호스트 CLI(Claude Code) 인증 위임. 별도 API 키 X |
| Q4 첫 빌드 범위 | `skills/`만 | 비용 측정 후 전체 확대 (정책 4) |
| Q5 SKILL.md 운영 | **(b) Knowledge skill로 별도 등록** | retrieval engine 자동 발견 → 다른 에이전트가 graphify를 자율 인지 |
| Q6 `--watch` | 미사용 | 필요 시 별도 skill mode |
| Q7 기존 skill 연결 | 후속 작업 | 본 문서에서는 base wrapper만 |
| Q8 `.graphifyignore` | 후속 (graphify 첫 호출 시 추가) | 본 문서 외 |
| Q9 Python 런타임 | uv tool + 3.13 | 격리 |
| Q10 전역 설치 | **불허** — agent-factory 내부 wrapper만 | `~/.claude/skills/` 오염 회피 |
| Q11 자동 주입 | **불허** — `graphify install` 사용 금지 | CLAUDE.md/hooks 충돌 회피 |

## 2. 적용한 Fix (Codex FIX_FIRST 동의)

| # | Fix | 위치 |
|---|-----|------|
| F1 | runtime lazy install 제거. `shutil.which("graphify")` 가드 + structured error | `skills/graphify/skill.py` |
| F2 | `--with-graphify` / `-WithGraphify` 옵션 (uv 자동 설치 + `graphifyy>=0.4.27,<0.5.0` pinned) | `install-af.sh`, `install-af.ps1` |
| F3 | meta.yaml 좁은 capability (`GRAPHIFY_BUILD`/`GRAPHIFY_QUERY`/`KNOWLEDGE_GRAPH_INDEX`) | `skills/graphify/meta.yaml` |
| F4 | `skills/registry.yaml` 두 엔트리 첫 커밋 동시 추가 | `skills/registry.yaml` |
| F5 | review-gate에 `skills/` 포함 — 정책 1번 실효화 | `scripts/enqueue_agent_review.py:26`, `.githooks/pre-commit:46` |
| F6 | action+knowledge skill_id 분리 (`graphify` + `graphify_guide`) | Q5(b) 선택으로 자동 해소 |

## 3. 신규 파일

```
skills/graphify/
├── meta.yaml          # action skill 메타 (capabilities, when_to_use_keywords, external_dependency)
└── skill.py           # GraphifySkill — propose/apply/test, shutil.which 가드, subprocess wrapper

skills/graphify_guide/
└── SKILL.md           # knowledge skill (frontmatter + retrieval keywords + 사용 시나리오)
```

## 4. 변경 파일

- `skills/registry.yaml` — graphify, graphify_guide 두 엔트리 추가
- `install-af.sh` — `--with-graphify` 옵션 + Step 10 (uv → graphifyy 설치)
- `install-af.ps1` — `-WithGraphify` 옵션 + Step 9 (winget uv → graphifyy)
- `scripts/enqueue_agent_review.py:26` — `_REVIEW_PREFIXES`에 `skills/` 추가 + 주석
- `.githooks/pre-commit:46` — 정규식에 `skills/.*\.py` 추가
- `Master_Blueprint.md` — §3.5 외부 도구 wrapper 패턴 섹션 추가, §12 변경 이력

## 5. skill.py 핵심 설계

```python
class GraphifySkill:
    __skill_id__ = "graphify"

    def propose(self, ctx, command="build", target="."):
        # shutil.which("graphify") → 없으면 missing_dependency + 친절한 install 안내
        ...

    def apply(self, ctx, command="build", target=".", extra_args=None, cwd=None, timeout_sec=1800):
        # _build_argv()로 명령별 argv 생성 (build/update/query/path/explain/add)
        # subprocess.run(check=False) + TimeoutExpired/FileNotFoundError 가드
        # 결과: returncode + stdout/stderr + artifacts(graph.html/json/REPORT.md)
        ...

    def test(self, ctx):
        # graphify --version 호출만 (10s timeout)
        ...
```

**왜 lazy install 안 함**:
- PyInstaller 환경에서 외부 `uv` 호출 시 사용자 PATH 의존
- 첫 호출 시 1~2분 지연 → UX 저하
- 오프라인 시 silent 실패
- → installer 단계에서 명시적 처리하는 게 깨끗

## 6. 알려진 한계

1. **graphify 첫 빌드 비용 미측정** — Q4에 따라 `skills/`만 한정해 측정 후 전체 확대
2. **`graphify-out/` 위치 정책 미고정** — 현재는 호출 시점의 cwd. 향후 `skills/_external_cache/graphify/<project_hash>/`로 격리 권장
3. **`.gitignore`에 `graphify-out/` 미추가** — 첫 호출 직전 추가 필요 (코드 변경 0이므로 본 PR에서는 보류)
4. **action+knowledge 동시 등록 실측** — Q5(b) 분리 패턴이지만 retrieval engine이 graphify_guide를 실제로 자동 발견하는지 회귀 테스트 필요

## 7. 회귀 검증 계획

- [ ] `python -m py_compile skills/graphify/skill.py` (✓ 완료)
- [ ] `python -c "import yaml; yaml.safe_load(open('skills/registry.yaml'))"` (✓ 완료)
- [ ] `bash -n install-af.sh` + `bash install-af.sh --help` (✓ 완료)
- [ ] `python -c "from scripts.enqueue_agent_review import _is_review_target; assert _is_review_target('skills/graphify/skill.py')"` (✓ 완료)
- [ ] af-test-runner (skill_loader가 graphify 정상 등록하는지)
- [ ] af-critic (수정된 4개 파일에 대한 코드 리뷰)
- [ ] af-cross-review (코덱스 최종 검증)

## 8. 다음 작업

1. 본 PR 커밋 + push (review-gate 정상 통과 — 정책 1)
2. Phase 1 실측: `bash install-af.sh --with-graphify` → graphifyy 설치 확인
3. 첫 호출 시험: `skills/` 폴더만 그래프화 → 비용/품질 측정
4. 결과로 Q4 (전체 확대) 결정

## 9. 참고

- 원본 분석 문서: `docs/features/2026-04-22-graphify-integration.md`
- Graphify 레포: https://github.com/safishamsi/graphify (v4)
- PyPI 패키지: `graphifyy` (이중 y, MIT)
- CLI 이름: `graphify` (단일 y) — 패키지명과 다름 주의
