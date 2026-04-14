# Agent Factory — Claude Code 지시사항

## 필수 규칙

### Master_Blueprint.md 참조 의무
- **코드 수정 전**: `Master_Blueprint.md`의 해당 §섹션을 먼저 읽어 의존성과 영향 범위를 파악한다
- **코드 수정 후**: 변경된 파일에 해당하는 섹션(§0~§11)과 §12 변경 이력을 **같은 커밋**에서 업데이트한다
- 전체 코드를 다시 읽지 않는다. Blueprint가 최신이면 Blueprint만으로 판단한다

### Blueprint 업데이트 트리거
| 이벤트 | 업데이트 대상 |
|--------|-------------|
| 새 `.py` 파일 생성 | §0 빠른 참조 테이블 |
| 클래스·메서드 변경 | §3 해당 서브시스템 + `last_updated` |
| 새 버그 수정 | §11 에러 코드 해설, §12 이력 |
| 배포(버전 bump) | §8 빌드, §12 이력 |
| 의존성 변경 | §10 Blast Radius 테이블 |

### 버전 및 빌드
- 버전 파일: `version.py` (`__version__`)
- 설치 스크립트: `install-af.ps1` (버전 문자열 3곳 동시 수정)
- 빌드: `python build_exe.py` → `dist/af-{version}.zip`
- 새 `core/*.py` 파일은 `af.spec` `hiddenimports`에 반드시 추가

### 문서 파일명 규칙
- **code-review.md**: 날짜 없음 (살아있는 단일 문서, in-place 갱신)
- **기타 모든 문서**: 파일명에 날짜 포함 필수 — `YYYY-MM-DD-제목.md`
  - 예: `2026-04-03-cross-cli-skill-discovery.md`
  - Feature 문서, 버그픽스 문서, 설계 문서, 플랜 등 전부 해당

### 교차검증 자동 실행
- UserPromptSubmit hook이 `[af-review-pending]` 메시지를 출력하면, **반드시** af-critic + af-cross-review 에이전트를 백그라운드로 병렬 실행한다
- 설계문서(.md) 작성 후에는 af-doc-qa + af-critic을 병렬 실행한다
- 교차검증 결과에서 BLOCK 판정 시 발견 사항을 즉시 수정한다

### 커밋 규칙
- 코드 수정 + Blueprint 업데이트는 같은 커밋
- 빌드 zip은 **GitHub Release로 배포**: `gh release create af-fsa_v{version} dist/af-{version}.zip --notes ...` (2026-04-14 정책 변경: LFS 미구성 환경에서 ~91MB zip이 GitHub 100MB 한계로 push 실패한 사례 이후. `dist/*.zip`은 `.gitignore` 처리)
- 태그 형식: `af-fsa_v{version}`

## Hook 설치 (레포 클론 후 1회)

```bash
git config core.hooksPath .githooks
```

이후 `core/*.py` 등 변경 커밋 시 `Master_Blueprint.md` 미스테이지 → 자동 차단.

## 프로젝트 개요
- **위치**: `C:\Project\agent-factory`
- **퍼블릭 레포**: `origin` = `https://github.com/hoonkim1092-web/af-fsa.git`
- **소스 레포**: `agent-factory` remote = `https://github.com/hoonkim1092-web/agent-factory.git`
- **현재 브랜치**: `2026-04-01-super-harness`
- **아키텍처 문서**: `Master_Blueprint.md` (845줄, 12섹션)
