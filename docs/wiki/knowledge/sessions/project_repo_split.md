---
name: agent-factory 개발·릴리즈 레포 분리 관리
description: 개발은 agent-factory 레포, 공개 릴리즈는 별도 af-fsa 레포로 분리 운영. 태그/Release는 af-fsa에서만 발행.
type: project
originSessionId: e83f86cd-cf31-48f2-93d6-7df62447cb80
---
사용자는 두 개의 GitHub 레포를 분리 운영한다:

- **개발용**: `hoonkim1092-web/agent-factory` — 모든 코드 커밋/브랜치/태그가 여기 쌓임. 현재 로컬 `origin`이 이것.
- **릴리즈용**: `hoonkim1092-web/af-fsa` — 공개 배포용. install 스크립트들(install-af.ps1/sh)이 zip 다운로드 URL로 참조하는 곳. v1.0.0, v1.2.16, v1.2.17까지 Release 발행됨.

**Why:** 개발 진행 레포의 민감한 변경 이력·브랜치·WIP를 사용자에게 공개하지 않고, 깨끗한 릴리즈 스냅샷만 배포하기 위한 분리 관리.

**How to apply:**
- 태그 `af-fsa_v{version}`을 agent-factory에 푸시한 것만으로는 **릴리즈 발행이 끝난 게 아니다**. af-fsa에도 동일 태그 + zip 업로드가 필요.
- agent-factory에는 `af-fsa` remote가 기본으로 등록되어 있지 않다(적어도 이 워크트리에는). 사용자가 수동 단계로 릴리즈를 옮기는 것으로 추정.
- install 스크립트 URL이 `github.com/hoonkim1092-web/af-fsa/...`를 가리키면 정상. `agent-factory/...`로 바뀌면 분리 원칙 위배.
- v1.2.18~v1.2.21 시점에 af-fsa Release 발행이 누락된 상태임(2026-04-15 확인) — 현재 개발 중이므로 **지금 당장 수동 배포할 필요 없음**.

**향후 계획(사용자 2026-04-15 명시)**: 개발 완료/기능 업데이트 시점에 "agent-factory → af-fsa 머지 → 빌드 → 자동 배포" 파이프라인을 구축할 예정. 그때 누락된 버전들이 한꺼번에 정리될 가능성. **중간 버전 배포 누락에 대해 걱정하거나 수동 발행을 권하지 말 것** — 의도된 상태임.
