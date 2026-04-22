---
id: graphify_guide
name: Graphify Usage Guide
version: 0.1.0
description: graphify 액션 스킬을 언제 어떻게 호출해야 하는지에 대한 가이드. 코드 구조 분석/Blast Radius/지식그래프 질의가 필요할 때 자동 검색되어 컨텍스트에 주입된다.
when_to_use: 사용자나 다른 스킬이 코드베이스 구조 이해, 함수 영향 범위 분석, 지식그래프 기반 질의를 시도할 때. 직접 grep/Read로는 큰 비용이 드는 탐색이 필요할 때.
when_NOT_to_use: 단순 키워드 grep으로 충분한 경우. graphify CLI가 환경에 설치되지 않은 경우(이때는 graphify action skill이 missing_dependency 응답을 돌려준다).
when_to_use_keywords:
  - graphify
  - knowledge_graph
  - 지식그래프
  - blast_radius
  - 코드영향범위
  - dependency_graph
  - call_graph
  - code_structure
  - 코드구조
  - 함수관계
  - 영향범위분석
category: research
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags:
  - graphify
  - knowledge_graph
  - guide
---

# Graphify 사용 가이드

## 1. 무엇인가

Graphify는 폴더(코드+문서+이미지)를 **지식그래프**로 변환하는 외부 도구다. 한 번 그래프를 빌드해두면 이후 질의는 grep/Read 반복 대신 그래프 탐색만으로 답할 수 있어 LLM 토큰을 크게 절감한다.

- 패키지: `graphifyy` (PyPI, MIT)
- CLI: `graphify`
- agent-factory 내 위치: `skills/graphify/` (action wrapper)
- 본 가이드: `skills/graphify_guide/SKILL.md` (knowledge)

## 2. 언제 쓸까

**적합 시나리오**
- 큰 변경 직후 "이 함수 바꾸면 어디까지 영향받지?" 같은 Blast Radius 질의
- 새 기능 설계 전 "관련된 기존 코드 구조" 파악
- 코드 리뷰 시 "변경된 모듈과 다른 모듈의 의존성" 확인
- 토큰 예산이 빠듯한 장기 세션에서 사전에 그래프 빌드

**부적합 시나리오**
- 파일 한두 개에서 키워드 찾기 (그냥 grep이 빠름)
- graphify CLI 미설치 환경 (action skill이 `missing_dependency`로 응답)
- 매우 작은 프로젝트(파일 6개 이하) — 토큰 절감 효과 거의 없음

## 3. 호출 방법

agent-factory 안에서는 `graphify` action skill을 통해 호출한다:

```python
# 빌드: 현재 폴더 전체를 그래프화
ctx.call_skill("graphify", command="build", target=".")

# 질의: 자연어 질문 → BFS/DFS 그래프 탐색
ctx.call_skill("graphify", command="query", target="auth와 response 어떻게 연결돼?")

# 경로: 두 노드 간 최단 경로
ctx.call_skill("graphify", command="path", target="DigestAuth", extra_args=["Response"])

# 설명: 단일 노드 + 연결 풀어쓰기
ctx.call_skill("graphify", command="explain", target="agent_runner")

# 외부 자료 병합 (URL → 그래프)
ctx.call_skill("graphify", command="add", target="https://example.com/paper.pdf")

# 증분 갱신 (변경된 파일만 재추출)
ctx.call_skill("graphify", command="update", target=".")
```

호출 결과:
- `ok: True` + `artifacts.graph_html` / `artifacts.report_md` 반환 시 정상
- `status: missing_dependency` 반환 시 사용자에게 설치 안내 (`install-af.sh --with-graphify`)

## 4. 첫 호출 비용

- 첫 빌드는 LLM(호스트 CLI 구독)으로 문서·이미지 추출 → 시간·토큰 소모
- agent-factory의 경우 `skills/` 폴더부터 좁게 시작 권장 (`target="skills"`)
- 비용 측정 후 전체로 확대

## 5. 출력 위치

- 기본: 호출 시점의 `cwd`에 `graphify-out/` 디렉토리 생성
- 권장: agent-factory에서는 `skills/_external_cache/graphify/<project_hash>/` 로 격리 (skill ctx에서 cwd 제어)
- `.gitignore`에 `graphify-out/` 추가 필수

## 6. 다른 스킬과의 연계

- **`code_review_guide`**: 리뷰 시 GRAPH_REPORT.md를 컨텍스트에 포함해 영향 범위 확인
- **`hound_librarian`**: 외부 자료 수집 후 `graphify add <url>`로 그래프에 병합
- **`af-critic` (agent)**: Blast Radius 자동 산출 가능

## 7. 주의

1. graphifyy는 Python 3.13 까지만 지원. agent-factory 메인 환경(3.14)와 분리되도록 `uv tool install --python 3.13`로 격리 설치
2. 첫 호출 시 호스트 CLI(Claude Code/Codex) 구독 사용량이 일시적으로 증가
3. `graphify install` (Graphify 공식 인스톨러)은 사용하지 말 것 — CLAUDE.md/hooks를 자동 수정하므로 agent-factory 규칙과 충돌. 우리는 wrapper만 사용
