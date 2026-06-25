---
name: Phase 7 완료
description: Phase 7 - 의존성 그래프 위상 정렬 + FSALoop 스킬 자동 진화 구현 완료
type: project
---

Phase 7: 의존성 그래프 위상 정렬 + FSALoop ↔ evolve_skill 자동 연결 완료 (2026-03-15)

**Why:** 분석 문서(Agent_Factory_스킬_시스템_리팩토링_심층_분석.md)에서 지적된 2대 약점 해결
- dependencies 필드가 선언만 되고 실제 사용 안 됨 → 위상 정렬 도입
- FSALoop와 evolve_skill이 분리되어 자율 진화 불가 → 자동 연결

**구현 내용:**

### 단계 1: SkillDependencyGraph (core/skill_loader.py)
- DAG 구축: dependencies 필드 기반 인접/역방향 리스트
- 순환 감지: DFS 3-color 알고리즘
- 위상 정렬: Kahn's algorithm (순환 스킬 자동 제외)
- 누락 의존성 자동 주입: get_required_deps() → _inject_missing_deps()
- DynamicSkillLoader에 통합: 충돌 해결 → 의존성 주입 → 위상 정렬 → 12-Cap

### 단계 2: FSALoop 스킬 자동 진화 (core/fsa_loop.py)
- _try_evolve_failed_skill(): 오케스트레이터 (감지→진화→검증→핫리로딩)
- _detect_failed_skill_dir(): 에러 메시지에서 스킬 디렉토리 매칭
- _verify_evolved_skill(): AST 보안검사 + run_isolated() 샌드박스 검증
- _rollback_skill(): .bak 파일 복원
- _hot_reload_registry(): auto_load_from_directories(force=True)

### 테스트: 20개 전체 통과
- tests/test_phase7_dep_graph_evolve.py
  - TestSkillDependencyGraph: 10개
  - TestDynamicSkillLoaderDeps: 4개
  - TestFSALoopSkillEvolve: 6개

**How to apply:** 스킬 의존성 관련 작업 시 SkillDependencyGraph 참조. FSALoop 디버깅 시 진화 파이프라인 흐름 참조.

## 관련
- [[code/symbols]]

