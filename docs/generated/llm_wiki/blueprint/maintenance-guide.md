---
generated_at: 2026-06-12T22:50:52+09:00
source_commit: 5a16df39
sources:
  - "Master_Blueprint.md"
---

# 유지보수 가이드

> Source: `Master_Blueprint.md:2866`
> 관련: [[blueprint/index]] | [[index]] | [[source_refs]]

````markdown
## 유지보수 가이드

### Blueprint 업데이트 규칙

1. **새 파일 추가** → §0 테이블에 추가
2. **클래스/메서드 변경** → §3 해당 서브시스템 `last_updated` 갱신
3. **의존성 변경** → §10 영향 매트릭스 업데이트
4. **버그 수정** → §11 에러 테이블에서 제거 또는 업데이트
5. **버전 릴리스** → §12 변경 이력에 한 줄 추가
6. **af.spec 변경** → §8 hiddenimports 설명 업데이트

### 효율적 검색법

```
기능 수정    → §3 해당 서브시스템 → 파일:라인 참조로 이동
에러 디버그  → §11 에러 코드 테이블
라우팅 변경  → §6 모델 라우팅 → model_utils.py 직접 수정
빌드 문제    → §8 빌드 & 배포
의존성 파악  → §10 Blast Radius 테이블
신규 기능    → §1 아키텍처 → §2 플로우 → §3 관련 서브시스템
```

### Self-Hosting 가능 범위

```
가능 ✅:
  - skills/ 스킬 코드 수정·진화
  - agents/*.yaml 에이전트 정의 수정
  - policy.yaml 정책 변경
  - docs/ 문서 생성·수정

소스 모드에서만 가능 ⚠️:
  - core/*.py 소스 코드 수정
    → python run_factory_cli.py로 실행 필요

불가 ❌:
  - af.exe → 자기 자신 리빌드
  - 빌드 중 빌드 (python build_exe.py는 소스 환경 필요)
```
````
