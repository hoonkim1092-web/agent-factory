---
name: memory push payload 폭주 결함 (2026-05-07 발견)
description: project_context_sync.collect_global_snapshot()이 chat 폴더 무한 누적을 거르지 않아 매 세션 payload 증가
type: project
originSessionId: 9027e693-3036-4b9e-a3f7-20643cf194f0
---
`scripts/project_context_sync.py`의 `collect_global_snapshot()`이 모든 메모리 파일을 단일 JSON 페이로드에 직렬화해서 Supabase POST. 하지만 `data/memory/general/claude_chat/` + `codex_chat/` 폴더에 chat history가 자동 누적 + 정리 로직 없음 → 매 세션마다 페이로드 증가.

**Why**: 2026-05-07 세션에서 `python end_db.py agent-factory`가 `HTTP Error 502/522/524 Bad Gateway`를 반복적으로 반환 → Supabase 장애로 오인. 실제 원인 추적 결과 페이로드 96.17 MB. Cloudflare가 upstream timeout으로 5xx 반환. Supabase 자체는 정상 (직접 curl로 HTTP 200/201 확인).

페이로드 구성:
- `data/memory/general/claude_chat/`: 13,987 files / 75 MB (JSON 직렬화 후)
- `data/memory/general/codex_chat/`: 5,780 files / 18 MB
- 기타: 0.001 MB

임시 우회 (24h 이상 chat 삭제): 16,679 files / 57 MB 정리 → payload 17 MB → push 성공.

**How to apply**:
- 다음 세션 NEXT_STEPS 우선순위 #1: 근본 fix
- 권장 fix:
  1. `collect_global_snapshot()`에 max-size cap (예: 25MB) — 초과 시 큰 폴더 우선 제외
  2. chat 폴더 자동 TTL (cron 또는 사이즈 기반)
  3. chat 폴더를 collector에서 통째로 제외 (PC-local로 유지)
- 진단 명령어 (페이로드 크기 확인):
  ```python
  from scripts.project_context_sync import collect_global_snapshot, resolve_global_root
  _, root = resolve_global_root(Path.cwd(), 'hoon_main')
  snap = collect_global_snapshot(global_root=root, user_key='hoon_main', run_limit=200)
  print(f'{len(json.dumps(snap))/1024/1024:.2f} MB')
  ```
- 5xx 에러 떴을 때 첫 의심 항목으로 페이로드 크기 체크 (Supabase 장애로 단정 금지)
