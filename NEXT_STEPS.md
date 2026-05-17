# NEXT_STEPS — 세션 재개 가이드

> **PC 바꿔서 시작했을 때 여기부터 읽을 것.**
> 마지막 업데이트: **2026-05-17 KST** — 다음 진입점: **Research Router Phase 1a 구현** (`core/research_router.py` 신규 + 관련 8개 파일).

---

## 🏠 Mac PC 재개 절차

```bash
cd <repo>/agent-factory     # 본 repo (main 브랜치)
git pull
python start_db.py agent-factory   # Supabase → 로컬 메모리 pull
git status -sb
```

그 다음 이 파일 "🔥 다음 진입점" 섹션부터 읽으면 됨.

---

## 🔥 다음 진입점

### Research Router Phase 1a 구현 (미구현)

설계 v1.4.1이 cross-review 5라운드 통과 완료. **코드를 아직 안 짰다.**

- 설계 문서: `docs/` 내 Research Router v1.4.1 설계 문서 (grep으로 찾을 것)
- 신규 파일: `core/research_router.py`
- 수정 파일: 관련 8개 파일 (설계 문서 §7 참조)

**진입 전 확인 사항**:
1. 설계 문서 경로 확인: `find docs/ -name "*research*router*" -o -name "*router*research*"`
2. Blueprint §7 확인 (Research Router 섹션)
3. `python -m pytest tests/ -x -q` 베이스라인 확인 (현재: 1687 PASSED)

---

## ✅ 완료된 작업 목록 (2026-05-17 기준)

### 인프라 Fix (F-series)
| 항목 | 완료일 | 내용 |
|------|--------|------|
| F1~F17 전체 | 2026-05-15 | CLI 디스패치, schema, 격리, workspace 분리 등 |
| F15 workspace/runtime_workspace | 2026-05-17 | project pipeline/orchestrator/FSA 전체 분리 |
| F16 test isolation | 2026-05-15 | conftest AF_DISABLE 가드 |

### Registry Write Guard (F9 시리즈)
| 항목 | 완료일 | 내용 |
|------|--------|------|
| `_write_registry()` | 2026-05-15 | F12 hardening — 최초 가드 |
| `workflow_apply()` | 2026-05-17 | WARN #2/#3 해소 |
| `_install_skill_file()` | 2026-05-17 | os.makedirs/shutil/meta.yaml/lock 전체 차단 |
| `register_built()` | 2026-05-17 | lock_skill_state 미보호 BONUS High 해소 |

### Cross-review 비용 감축
| Phase | 상태 | 내용 |
|-------|------|------|
| Phase 1 | ✅ 완료 (2026-05-01) | blast_tier/verdict/routing_state 분리, `downgrade_blast_tier` → NotImplementedError |
| Phase 2 | 미구현 | review_bundle 생성기 (ast-grep-py 의존성, 복잡) |
| Phase 3 | 미구현 | 에이전트 프롬프트 최적화 |
| Phase 4 | 미구현 | 스마트 라우팅 (Tier 3 skip 조건) |

### 기타
- F8 ContextSchema — Round 4b에서 fix 확인됨. **재현 없으면 패스.**
- F3 CLI argparse — 완료
- test flaky 해소 — 완료
- 전역 싱글톤 storage workspace isolation — 완료
- Blueprint §0~§12 동기화 — 최신

---

## 📜 과거 이력 참조

- 세션별 누적 이력: [docs/session-log/2026-05-15-rounds-1-2-3.md](docs/session-log/2026-05-15-rounds-1-2-3.md)
- dogfooding 마찰 F0~F17: [docs/dogfooding/round4-af-cli-friction.md](docs/dogfooding/round4-af-cli-friction.md)

---

## 세션 종료 체크리스트

1. 완료 작업 / 다음 진입점 갱신
2. `git commit` → `git push`
3. `python end_db.py agent-factory`
