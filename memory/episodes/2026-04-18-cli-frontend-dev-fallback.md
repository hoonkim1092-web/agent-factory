---
episode_id: 2026-04-18-cli-frontend-dev-fallback
outcome: failure_then_success
project_id: lotto_mobile_web
date: 2026-04-18
tags: [role-misassignment, cli, frontend, backend_dev]
---

# 에피소드: CLI deliverable → frontend_dev 오배정

## 상황

lotto_mobile_web 프로젝트에서 "CLI 로또 번호 조회 기능" deliverable이
`frontend_dev` 역할에 배정됐다. frontend_dev는 웹 UI만 담당하고 CLI를 모름.

## 실패 원인

- `_pick_owner_role`의 키워드 맵에 "cli"가 없음
- deliverable 이름에 "web" 이 포함되어 있어 frontend 버킷으로 분류됨
- frontend_dev가 CLI 코드를 생성했지만 argparse/Click 사용법 오류

## 해결 방법

- qa_engineer가 오배정을 감지하고 `backend_dev`로 재배정
- `backend_dev`가 Click 기반 CLI 구현 후 성공

## Hints

- CLI, 명령행, command-line, argparse, click 키워드가 포함된 deliverable은 backend_dev 또는 general_dev에 배정한다
- "web" 키워드가 있어도 CLI 기능이면 frontend_dev가 아닌 backend_dev
- role ledger에 cli→backend_dev 매핑을 기록하여 동일 오류 방지
- 세 번째 프로젝트부터는 ledger 조회로 frontend_dev 오배정을 사전 차단한다

## 결과

재배정 후 Level 2 pivot으로 성공. lineage_id: lotto_mobile_web::frontend::cli_query
