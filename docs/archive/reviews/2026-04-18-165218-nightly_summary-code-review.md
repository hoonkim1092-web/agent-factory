# Code Review: nightly_summary

> Source: scripts/nightly_summary.py
> Date: 2026-04-18 16:52
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

`save_state()` 직렬화 충돌(Finding #1)이 Critical에 해당한다. 매 틱마다 상태 저장이 실패하므로 나이틀리 파이프라인 전체가 무력화된다.

---

### Aggregated Findings (4 total)

#### 1. [ACCEPT] [Critical] `_VALID_LEVELS` frozenset → JSON 직렬화 충돌로 `save_state()` 매번 크래시

- **Critic**: not flagged
- **Cross**: `WatchdogState.to_dict()`가 `dataclasses.asdict()`를 사용하는데 `_VALID_LEVELS`가 dataclass 필드로 포함되어 직렬화 시 `TypeError: Object of type frozenset is not JSON serializable` 발생. `write_summary()`는 도달 불가.
- **Judgment**: Cross에서만 제기됐지만 `dataclasses.asdict()`는 모든 annotated 필드를 재귀 직렬화하고 frozenset은 JSON 비호환이므로 코드 증거가 명확하다. Critical로 격상.
- **Action Required**: `_VALID_LEVELS: ClassVar[frozenset[str]] = frozenset(...)` 로 변경하거나 dataclass 외부로 이동. 이후 `save_state(NightlyState(), tmpdir)` 스모크 테스트 추가.

#### 2. [ACCEPT] [Medium] `nightly-stop` / 예외 경로에서 `write_summary()` 미호출 → 요약 파일 stale

- **Critic**: not flagged
- **Cross**: `nightly-stop`, `nightly-start`, `tick_once()` 예외 경로가 `save_state()` 호출 후 `write_summary()`를 건너뜀. 마지막 동작이 `nightly-stop`이면 요약이 영구 stale.
- **Judgment**: `run_factory_cli.py:197`, `run_factory_cli.py:226`, `scripts/nightly_tick.py:233` 세 경로 모두 확인됨. 단독 제기지만 증거 충분.
- **Action Required**: `persist_nightly_state(state, path)` 헬퍼로 `save_state()` + `write_summary()` 묶음 원자화, 또는 `save_state()` 내부에서 요약 렌더링 호출.

#### 3. [ACCEPT] [Medium] `nightly_summary.md` 비원자 쓰기 — 기존 추적 패턴 재도입

- **Critic**: not flagged (이전 세션 리뷰에서 동일 패턴 BLOCK 판정 이력 있음)
- **Cross**: `Path.write_text()`는 중단 시 truncated 파일 가능. `code-review.md`의 C2/H5a/M10 패턴과 동일 클래스.
- **Judgment**: `save_state()`는 `tempfile + os.replace` 사용하는데 `write_summary()`만 예외. 코드베이스 내 이미 해결된 패턴이 재도입됨.
- **Action Required**: `core/file_io.py`에 `write_text_atomic()` 추가 후 `nightly_summary.py:75`에 적용.

#### 4. [ACCEPT] [Low] 나이틀리 요약 흐름 테스트 전무

- **Critic**: not flagged
- **Cross**: `rg "nightly_summary|write_summary|render_summary" tests` 결과 없음.
- **Judgment**: Finding #1, #2가 테스트 없이 실제 운영 전까지 발견되지 않은 직접 원인.
- **Action Required**: `render_summary()` 단위 테스트 1건, `save_state` + `write_summary` 스모크 테스트 1건, `tick_once()` 실패 경로 통합 테스트 1건.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `_VALID_LEVELS` frozenset → JSON 크래시 | Critical | ACCEPT | Cross |
| 2 | `write_summary()` 미호출 경로 존재 | Medium | ACCEPT | Cross |
| 3 | `nightly_summary.md` 비원자 쓰기 | Medium | ACCEPT | Cross |
| 4 | 요약 흐름 테스트 없음 | Low | ACCEPT | Cross |

---

### Recommendations

- **즉시 수정 (BLOCK 해제 조건)**: `_VALID_LEVELS`를 `ClassVar`로 변경 → `save_state()` 정상 동작 복원
- **같은 PR**: `persist_nightly_state()` 헬퍼로 save + summary를 하나의 호출로 묶기
- **같은 PR**: `write_text_atomic()` 추출 후 `nightly_summary.py`에 적용
- **후속 PR 가능**: 스모크/단위 테스트 3건 추가 (BLOCK 해제 후 별도 커밋 허용)

> **Critic 리뷰 비고**: 제출된 Critic 출력이 파일 편집 권한 요청 형태로, 독립적 버그 소견이 누락되었다. 이번 집계는 Cross Review 4건 전량 채택으로 진행했으며, 향후 Critic 에이전트 실행 환경(파일 권한) 점검이 필요하다.