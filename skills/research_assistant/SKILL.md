---
id: research_assistant
name: Research Assistant
version: 1.0.0
description: 주어진 기술 주제를 NotebookLM 아카이브에 쿼리해 마크다운 리서치 보고서를 생성합니다. Executive Summary · Key Technology Analysis · Recommendation 3섹션 구조 고정.
when_to_use: 특정 기술 주제에 대한 체계적인 분석 보고서가 필요할 때. NotebookLM 아카이브가 구성된 환경에서만 동작.
when_NOT_to_use: NotebookLM archive가 미설정일 때 (af setup 필요). 단순 Q&A나 빠른 사실 확인. 실시간 웹 검색이 필요한 경우.
when_to_use_keywords:
  - 리서치
  - research
  - 보고서
  - report
  - 기술분석
  - 조사
  - 분석
  - NotebookLM
  - 아카이브
  - 기술주제
  - 문서생성
category: research
skill_type: action
auto_invocable: false
user_invocable: true
planner_invocable: true
tags:
  - research
  - notebooklm
  - report
  - analysis
  - markdown
---

# Research Assistant 스킬

## 개요

NotebookLM 아카이브 노트북을 쿼리해 기술 주제 리서치 보고서를 자동 생성한다.
출력은 `artifacts_dir`에 `research_YYYYMMDD_HHMMSS.md` 형식으로 저장된다.

## 전제조건

`af setup`으로 NotebookLM 아카이브 노트북 ID가 구성되어 있어야 한다. 미구성 시 `archive_not_configured` 오류로 즉시 반환.

진단:
```bash
af __check-nlm
```

---

## 입력 스펙

`propose()` 반환 기준:

| 키 | 필수 | 설명 |
|---|---|---|
| `topic` | 필수 | 리서치할 기술 주제 (예: "LLM Agent Patterns") |
| `depth` | 선택 | 분석 깊이 (현재 미구현, 예약 필드) |
| `output_format` | 선택 | 출력 형식 (현재 미구현, 예약 필드) |
| `artifacts_dir` | 선택 | 보고서 저장 경로 (기본값: `.`) |

---

## 출력 스펙

성공 시:
```json
{
  "ok": true,
  "message": "Research report generated for '<topic>'",
  "report_path": "<artifacts_dir>/research_YYYYMMDD_HHMMSS.md",
  "content_preview": "<보고서 첫 2000자>"
}
```

실패 시:
```json
{
  "ok": false,
  "error": "notebooklm_query_failed: <reason>",
  "hint": "<사람이 읽을 수 있는 해결 방법>",
  "topic": "<요청된 주제>"
}
```

`error` 코드 종류: `archive_not_configured`, `empty_response`, `connection_error:<msg>`

---

## 보고서 구조

```markdown
# Research Report: <topic>
Date: YYYY-MM-DD HH:MM:SS
Author: Himari (Super Research Architect)

## 1. Executive Summary
## 2. Key Technology Analysis
   <NotebookLM 쿼리 결과>
## 3. Recommendation
```

---

## AF 파이프라인 호출 예시

```yaml
- skill: research_assistant
  ctx:
    topic: "LangGraph Human-in-the-Loop Patterns"
    artifacts_dir: "docs/research"
```

또는 직접 파이프라인 컨텍스트:
```python
ctx = {"topic": "AI Agent Memory Architecture", "artifacts_dir": "./output"}
result = skill.apply(ctx)
if result["ok"]:
    print(result["report_path"])
```

---

## 오류 처리 체크리스트

- `archive_not_configured` -> `af setup` 재실행 -> NotebookLM 아카이브 노트북 연결
- `empty_response` -> `af __check-nlm` -> nlm CLI 인증 상태 확인
- `connection_error` -> 네트워크 / VPN 확인
