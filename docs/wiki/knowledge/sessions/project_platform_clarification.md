---
name: agent-factory는 범용 오케스트레이션 플랫폼
description: Lilith/Himari 등 특정 에이전트는 프로젝트별 임시 존재, 릴리즈 시 제거됨
type: project
---

agent-factory는 **범용 오케스트레이션 플랫폼**이다. 특정 에이전트(Lilith, Himari 등)는 사용자가 다른 프로젝트에서 만든 것이며, 릴리즈 시 존재하지 않는다.

**Why:** 사용자가 명시적으로 밝힘 — 플랫폼 설계 시 특정 에이전트 역할에 의존하지 말 것.

**How to apply:** 코드나 아키텍처 제안 시 항상 범용적 관점 유지. researcher.py 등 에이전트별 코드는 플랫폼 핵심이 아닌 플러그인 레벨로 취급.

## 관련
- [[code/symbols]]

