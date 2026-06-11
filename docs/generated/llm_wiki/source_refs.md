---
generated_at: 2026-06-11T15:49:58+09:00
source_commit: c37eff2a
sources:
  - "Master_Blueprint.md"
  - "docs/code_review/code-review.md"
  - "NEXT_STEPS.md"
---

# Source References — 섹션 ↔ 원본 경로 매핑

> source_commit: `c37eff2a`
> 관련: [[index]] | [[architecture]] | [[review_patterns]]

## Master_Blueprint.md

| 항목 | 원본 경로 |
|------|----------|
| §0 루트 파일 테이블 | `Master_Blueprint.md:§0 루트 파일` |
| §0 core/ 파일 테이블 | `Master_Blueprint.md:§0 core/ 파일` |
| 섹션별 전문 mirror | `blueprint/*.md` |
| 개요 | `Master_Blueprint.md:1` / [[blueprint/overview]] |
| 목차 | `Master_Blueprint.md:9` / [[blueprint/toc]] |
| §0 빠른 참조 테이블 | `Master_Blueprint.md:27` / [[blueprint/0-빠른-참조-테이블]] |
| §1 아키텍처 개요 | `Master_Blueprint.md:240` / [[blueprint/1-아키텍처-개요]] |
| §2 실행 흐름 | `Master_Blueprint.md:276` / [[blueprint/2-실행-흐름]] |
| §3 핵심 서브시스템 | `Master_Blueprint.md:431` / [[blueprint/3-핵심-서브시스템]] |
| §4 자가진화 루프 | `Master_Blueprint.md:1150` / [[blueprint/4-자가진화-루프]] |
| §5 에이전트 간 통신 | `Master_Blueprint.md:1212` / [[blueprint/5-에이전트-간-통신]] |
| §6 모델 라우팅 | `Master_Blueprint.md:1243` / [[blueprint/6-모델-라우팅]] |
| §7 안전장치 | `Master_Blueprint.md:1279` / [[blueprint/7-안전장치]] |
| §8 빌드 & 배포 | `Master_Blueprint.md:1428` / [[blueprint/8-빌드-배포]] |
| §9 설정 레퍼런스 | `Master_Blueprint.md:1547` / [[blueprint/9-설정-레퍼런스]] |
| §10 의존성 그래프 & 영향 매트릭스 | `Master_Blueprint.md:1603` / [[blueprint/10-의존성-그래프-영향-매트릭스]] |
| §11 알려진 제약·이슈 | `Master_Blueprint.md:1657` / [[blueprint/11-알려진-제약-이슈]] |
| §12 변경 이력 | `Master_Blueprint.md:1689` / [[blueprint/12-변경-이력]] |
| 유지보수 가이드 | `Master_Blueprint.md:2863` / [[blueprint/maintenance-guide]] |
| §3.1 ProjectPipeline | `Master_Blueprint.md:§3.1` |
| §3.2 DynamicOrchestrator | `Master_Blueprint.md:§3.2` |
| §3.3 AgentRunner | `Master_Blueprint.md:§3.3` |
| §3.4 AgentSpecializer | `Master_Blueprint.md:§3.4` |
| §3.5 스킬 시스템 | `Master_Blueprint.md:§3.5` |
| §3.6 메모리 시스템 | `Master_Blueprint.md:§3.6` |
| §3.7 CrossVerification | `Master_Blueprint.md:§3.7` |
| §3.8 Warning Registry & Stats (`core/warning_registry.py`, `core/escalation_evaluator.py`, `core/escalation_decision_report.py`, `core/warning_overrides.py`, `core/warning_stats.py`) | `Master_Blueprint.md:§3.8` |
| §3.9 Evaluator | `Master_Blueprint.md:§3.9` |
| §3.8.1 ControlPlaneLLM | `Master_Blueprint.md:§3.8.1` |
| §3.8.2 FailureClassifier | `Master_Blueprint.md:§3.8.2` |
| §3.8.3 RunBudget | `Master_Blueprint.md:§3.8.3` |
| §3.8.4 SkillPackBootstrapper | `Master_Blueprint.md:§3.8.4` |
| §3.9 Continuity | `Master_Blueprint.md:§3.9` |
| §3.10 Control 서브시스템 | `Master_Blueprint.md:§3.10` |
| §3.11 Setup Wizard + External Research (`core/setup_wizard.py`, `core/research_engine.py`) | `Master_Blueprint.md:§3.11` |
| §3.13 Dogfood Pipeline | `Master_Blueprint.md:§3.13` |
| §3.12 자동 Core 변경 요약 | `Master_Blueprint.md:§3.12` |

## docs/code_review/code-review.md

| 섹션 | 원본 경로 |
|------|----------|
| 섹션 mirror | `code_review/*.md` |
| §2.1 실행 엔진 (Runtime Engine) | `docs/code_review/code-review.md:37` / [[code_review/2-1-실행-엔진-runtime-engine]] |
| §2.2 Control Plane (Sidecar 유지보수) | `docs/code_review/code-review.md:55` / [[code_review/2-2-control-plane-sidecar-유지보수]] |
| §2.3 Provider 레이어 | `docs/code_review/code-review.md:79` / [[code_review/2-3-provider-레이어]] |
| §2.4 Hook 시스템 | `docs/code_review/code-review.md:93` / [[code_review/2-4-hook-시스템]] |
| §2.5 메모리 시스템 | `docs/code_review/code-review.md:113` / [[code_review/2-5-메모리-시스템]] |
| §2.6 ISE (Iterative Self-Enhancement) | `docs/code_review/code-review.md:136` / [[code_review/2-6-ise-iterative-self-enhancement]] |
| §2.7 스킬 시스템 | `docs/code_review/code-review.md:151` / [[code_review/2-7-스킬-시스템]] |
| §2.8 대화/연구 엔진 | `docs/code_review/code-review.md:188` / [[code_review/2-8-대화-연구-엔진]] |
| §2.9 파이프라인/보드 | `docs/code_review/code-review.md:204` / [[code_review/2-9-파이프라인-보드]] |
| §2.10 인프라/유틸리티 | `docs/code_review/code-review.md:214` / [[code_review/2-10-인프라-유틸리티]] |
| §2.11 기타 | `docs/code_review/code-review.md:234` / [[code_review/2-11-기타]] |
| §2.12 진입점 및 빌드 | `docs/code_review/code-review.md:252` / [[code_review/2-12-진입점-및-빌드]] |
| §3.1 Critical — 크래시 또는 데이터 손실 가능 | `docs/code_review/code-review.md:265` / [[code_review/3-1-critical-크래시-또는-데이터-손실-가능]] |
| §3.2 High — 잘못된 동작 | `docs/code_review/code-review.md:274` / [[code_review/3-2-high-잘못된-동작]] |
| §3.3 Medium — 성능/유지보수 | `docs/code_review/code-review.md:310` / [[code_review/3-3-medium-성능-유지보수]] |
| §3.4 이미 수정된 버그 (control/ 영역) | `docs/code_review/code-review.md:335` / [[code_review/3-4-이미-수정된-버그-control-영역]] |
| §3.5 신규 기능 추가 (2026-04-03) | `docs/code_review/code-review.md:348` / [[code_review/3-5-신규-기능-추가-2026-04-03]] |

## NEXT_STEPS.md

| 항목 | 원본 경로 |
|------|----------|
| 미완료/보류 항목 | `NEXT_STEPS.md` (마커 기반 추출) |
| 세션 재개 가이드 | `NEXT_STEPS.md:1` |

## Codebase Symbols

| 항목 | 원본 경로 |
|------|----------|
| AST 심볼 추출기 | `scripts/codebase_symbols.py` |
| Python top-level classes/functions | `**/*.py` (runtime/cache/vendor 디렉터리 제외) |
