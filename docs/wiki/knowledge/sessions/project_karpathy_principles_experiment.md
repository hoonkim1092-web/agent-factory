---
name: Karpathy 4원칙 실험 (2026-05-04 시작)
description: agent-factory CLAUDE.md에 Karpathy LLM 행동 원칙 4개 추가, 1주일 체감 후 결정
type: project
originSessionId: 25bd853b-0179-4231-9c18-b1a26e6bdbae
---
# Karpathy 4원칙 실험

**시작일**: 2026-05-04
**결정일 목표**: 2026-05-11 (1주일 후)
**적용 위치**: `agent-factory/CLAUDE.md` 최상단 (HTML 주석 마커로 감싸짐)
**커밋**: `a8814fd0 docs(claude.md): Karpathy LLM 행동 원칙 4개 추가 (실험)`

## 배경

**Why**: Karpathy 4원칙(Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution)의 효과를 직접 측정 데이터 없이 추측하지 말고, 1주일 체감으로 검증 후 결정. 다른 AI는 "65줄 복붙으로 충분"이라고 했지만 측정 데이터 없는 추측이라 결론 보류.

**How to apply**: 다음 1주일간 모델 행동 변화를 체감 관찰하고, 결정일에 다음 중 선택:
- 효과 체감 → Phase 2 (채팅 UI 3곳 Karpathy 30줄 등록)
- 효과 없음 → 제거
- 모름 → 그대로 유지 (downside 56줄)

## 관찰 포인트

| 원칙 | 신호 |
|------|------|
| Think Before Coding | 모호한 요청 시 모델이 묻고 시작하는 빈도 ↑ |
| Simplicity First | 30줄 충분한데 100줄 만드는 빈도 ↓ |
| Surgical Changes | 요청 안 한 인접 코드 리팩토링 빈도 ↓ |
| Goal-Driven Execution | 다단계 작업 시 검증 계획 제시 빈도 ↑ |

## 쉽게 제거하는 방법

CLAUDE.md에 `<!-- KARPATHY-PRINCIPLES-START -->` ~ `<!-- KARPATHY-PRINCIPLES-END -->` 마커로 감쌈.

**제거 명령 (Git Bash)**:
```bash
python -c "
import re, pathlib
p = pathlib.Path('CLAUDE.md')
t = p.read_text(encoding='utf-8')
t = re.sub(r'<!-- KARPATHY-PRINCIPLES-START.*?<!-- KARPATHY-PRINCIPLES-END -->\n*', '', t, flags=re.DOTALL)
p.write_text(t, encoding='utf-8')
"
```

또는 수동: 두 마커 사이 모든 줄 삭제.

## 향후 결정 시점에 확인할 것

- agent-factory CLAUDE.md의 KARPATHY 섹션이 여전히 있는지 (`grep KARPATHY-PRINCIPLES-START CLAUDE.md`)
- 1주일 사이 작업 빈도 (체감할 만큼 코딩했는지)
- 모델 행동 인상 (정성적 — 정량 측정 없음)
