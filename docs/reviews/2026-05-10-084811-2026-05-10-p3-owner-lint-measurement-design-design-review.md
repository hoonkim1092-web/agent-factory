# Design Review: 2026-05-10-p3-owner-lint-measurement-design

> Source: docs/2026-05-10-p3-owner-lint-measurement-design.md
> Date: 2026-05-10 08:48
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

총 14개 finding 중 ACCEPT 12 (Critical 1 / High 7 / Medium 3 / Low 1) + HOLD 1 + REJECT 1. 보안 (path traversal), 빌드 검증 경로 오류, 데이터 흐름 자기모순이 누적되어 그대로 구현 진입 시 PR 회귀 또는 false-pass 위험 다수.

---

### Aggregated Findings (14 total)

#### 1. [ACCEPT] [High] `warning-export --phase` 시그니처/계약 불일치
- **Critic #4**: §5.1 시그니처/인자 표에 `--phase` 누락이지만 §5.4는 forward 단언. records vs summary 모드 적용 범위 미정.
- **Cross #1**: 동일 — `collect_workspace_stats(... phase=...)` 받지만 export parser arg 미등록.
- **Judgment**: 두 리뷰 동일 지적. §8.2 case 12 fixture를 작성할 수 없음.
- **Action Required**: §5.1 시그니처에 `[--phase PHASE]` 추가 + 인자 표 row 1줄 추가. records 모드 동작 결정 (argparse 거부 또는 post-filter 또는 `iter_warning_records`에 phase 인자 추가) — 셋 중 하나 명시.

#### 2. [ACCEPT] [High] `--slug` path traversal 미명세 — 보안 결함
- **Critic**: not flagged
- **Cross #3**: `os.path.join(warnings_root, slug)`로 구현 시 `../../outside` 탈출 가능. P3 read-only지만 export가 임의 jsonl 노출.
- **Judgment**: read-only 도구라도 정보 노출. 기존 `core/utils.py:60 safe_id()` 가용한데 명시 안 됨.
- **Action Required**: §3.3/§5.1에 slug 검증 명시 (`slug != safe_id(slug) → reject` 또는 `os.path.commonpath` 검사). §8.1에 `--slug ../../x` 거부 케이스 추가.

#### 3. [ACCEPT] [High] Frozen smoke 검증 경로 오류 — `dist/af-1.2.26/...` 미존재
- **Critic**: not flagged (반대로 §6.6에서 같은 wrong path를 제안함)
- **Cross #4**: `build_exe.py:20 DIST_DIR = dist/af`. 버전 디렉토리는 zip 파일명일 뿐 onedir 디렉토리 이름 아님.
- **Judgment**: Cross 측 evidence (`build_exe.py:82`) 결정적. §8.4 sanity check 자체가 항상 실패.
- **Action Required**: §6.6/§8.4 경로를 `dist/af/_internal/config/warning_registry_index.json` + 실행 파일은 `dist/af/af` 또는 `dist/af/af.exe`로 정정. zip 존재는 별도 확인.

#### 4. [ACCEPT] [High] `iter_warning_records()` 단일 iterator로 `scanned_slug_count` 산출 불가
- **Critic**: not flagged
- **Cross #2**: iterator는 parsed records만 yield → "slug dir scanned, jsonl missing" vs "slug dir not scanned" 구분 불가. 그러나 stats/export 둘 다 `scanned_slug_count` 필요.
- **Judgment**: 강한 구조적 결함. v2에서 흡수했다는 "단일 iterator" 결정과 v3 §3.5 `scanned_slug_count` 계약 자체가 양립 불가.
- **Action Required**: `_iter_slug_dirs(workspace, slug=None) -> tuple[list[str], warnings]` 별도 헬퍼 명시. `scanned_slug_count`는 record 순회 전 계산.

#### 5. [ACCEPT] [High] `_load_index()` 헬퍼가 `core.config_paths`를 import → 19곳 디렉토리 부작용
- **Critic #2**: `core/config_paths.py:91-109`가 module load 시 15개 디렉토리 강제 생성. read-only 분석 도구 보장 위반.
- **Cross**: not flagged
- **Judgment**: 실측 evidence 결정적. P3 §3.5 read 안전성 단언과 직접 충돌.
- **Action Required**: `_load_index()`는 `core.config_paths` 직접 import 금지. frozen은 `sys.executable` 기반, 소스는 `__file__` 상위 직접 계산. tests에 `BASE_DIR` 격리 명시 (tmp_path/monkeypatch).

#### 6. [ACCEPT] [High] CSV `\;` escape 표준 처방 아님 — round-trip 불가
- **Critic #3**: Python `csv` 모듈 `QUOTE_MINIMAL`은 backslash escape 미처리. RFC 4180에 backslash escape 없음. pandas/Excel 복원 불가.
- **Cross**: not flagged
- **Judgment**: 사실 검증 가능한 기술적 오류. "CSV 표준 처방" 표현이 거짓.
- **Action Required**: 분리자 `;` → `|` 또는 `affected_ids`를 `json.dumps()`로 박기. 두 옵션 중 택일 후 §5.2 재작성. 기존 처방 유지 시 표준 csv round-trip 불가 명시.

#### 7. [ACCEPT] [High] malformed-line 경고 채널 자기모순 (§3.5/§4.4/§8.1)
- **Critic #5**: §4.4 "모든 휴먼 경고는 `warnings:`에 담는다" + §3.5 "stderr 1줄, stdout 미오염" + §8.1 case 6 "warnings 비어도 OK" 세 곳이 양립 불가.
- **Cross**: not flagged (Cross #7과 부분 겹침)
- **Judgment**: 동일 워딩의 직접 충돌. 구현자가 어느 쪽 따라야 할지 결정 불가.
- **Action Required**: 한쪽 통일 — (a) malformed도 `warnings:`에 추가 + stderr 미러, 또는 (b) §4.4를 "단 per-line malformed는 stderr-only" 단서 추가 + §8.1 case 6 expected에 `len(warnings) == 0` 명시.

#### 8. [ACCEPT] [Medium] `af.spec datas` 추가 row는 wholesale 번들과 중복
- **Critic #1** (High): `af.spec:27-32` 이미 `('config', 'config')` wholesale. 추가 row는 PyInstaller 중복 dest 경고 + frozen smoke false-negative.
- **Cross #6** (REJECT initially): 같은 사실 인정하되 "harmless but redundant".
- **Judgment**: 사실 합의. severity는 중복 등록의 실제 위험(빌드 경고)이 검증 false-pass보다 작아 Medium. 본질은 "추가하지 말고 기존 wholesale에 포함됨을 확인"으로 검증 재작성.
- **Action Required**: §3.2/§6.6/§7의 `datas` 추가 제거. §6.6 packaging 검증을 "기존 wholesale 항목이 새 파일 포함" 으로 재작성. P3 PR scope `af.spec` 변경은 `hiddenimports`에 `core.warning_stats` 1줄만.

#### 9. [ACCEPT] [Medium] `_load_index()` snippet에 `import sys` 누락
- **Critic**: not flagged
- **Cross #5**: §3.3 import block은 `json/math/os`만, §6.6 snippet은 `sys._MEIPASS` 사용 → `NameError`.
- **Judgment**: 1라인 evidence로 자명.
- **Action Required**: §3.3 import block에 `import sys` 추가. `getattr(sys, "_MEIPASS", None)` 조건부 가드 명시.

#### 10. [ACCEPT] [Medium] `install-af.ps1` line 110 이중 등장 — `grep -c` false-pass
- **Critic #6**: line count 8 vs occurrence count 9. line 110에 `af-fsa_v1.2.25` + `af-1.2.25.zip` 두 번. 사후 검증 `grep -c`가 false-pass 가능.
- **Cross**: not flagged
- **Judgment**: 실측 evidence 결정적.
- **Action Required**: §8.4 사후 검증을 `grep -o '...' | wc -l` 또는 `sed -i 's/.../g'` 전역 치환으로 변경. §3.2에 "line 110 이중 등장" 메모 1줄.

#### 11. [ACCEPT] [Medium] `_PHASE_ORDER` underscore-private import — fragile
- **Critic #7**: `core/warning_registry.py:21` underscore prefix. 외부 import는 컨벤션 위반 + future phase 추가 시 silent skew.
- **Cross**: not flagged
- **Judgment**: 코드 컨벤션 위반 명백.
- **Action Required**: (a) `_PHASE_ORDER` → `PHASE_ORDER` rename + `__all__` 등록, 또는 (b) `core/warning_stats.py`에 `_VALID_PHASES` 직접 정의. 택일 명시.

#### 12. [ACCEPT] [Medium] `os.scandir(missing_dir)` FileNotFoundError 가드 미명시
- **Critic #8**: §3.5는 결과는 약속하나 코드 가드 패턴 미제시. §8.1 case 1이 두 sub-case (디렉토리 부재/빈 디렉토리) 미분리.
- **Cross**: not flagged
- **Action Required**: §3.3 docstring에 `if not os.path.isdir(warnings_root): return iter(())` 명시. §8.1 case 1을 1a/1b로 분리.

#### 13. [ACCEPT] [Low] `runtime/warnings/_index.json` 삭제 — `git rm` 누락
- **Critic #10**: `.gitignore` 화이트리스트 제거만으로 tracked 파일 untrack 안 됨.
- **Cross**: not flagged
- **Action Required**: §7 row 7에 `git rm runtime/warnings/_index.json` 명시. §11 자기검증에 `git ls-files runtime/warnings/_index.json` empty 확인.

#### 14. [HOLD] [Low] `core.warning_stats` 로깅 계약 미정의
- **Critic**: not flagged
- **Cross #7**: stdout/stderr는 정의되나 `logging.getLogger()` 사용 여부 미정. CLI-only 영구냐 reusable library냐에 따라 결정 변동.
- **Question for Author**: P3 stats/export 모듈을 (a) CLI-only로만 쓸지, (b) 향후 tests/scripts/frozen automation에서 reusable 라이브러리로 쓸지 결정. (b)면 logger name/levels + warnings 필드의 logging mirror 여부 명시.

#### REJECTED. [Low] schema_version 1 → 2 bump의 reader 부재
- **Source**: Critic #9
- **Original Finding**: reader 없는 bump는 KISS 위반. P4까지 미루는 게 정합.
- **Rejection Reason**: v3 §6.5에서 이미 "P3에서 reader 없음 — P4가 도입 시점"으로 처리됨 (이력 v3-#10 HOLD ACCEPT). 추가 변경 없음. 단, P4 진입 시 schema_version 1 입력 처리 정책을 P4 설계로 위임한다는 단서를 §6.5에 한 줄 보강하면 더 안전.

#### REJECTED. [Low] records 모드 CSV `record_count == 0` 미정의
- **Source**: Critic #11
- **Original Finding**: pandas `EmptyDataError` 가능.
- **Rejection Reason**: trivial한 edge case이며 standard 처리(헤더 1줄)가 자명. §5.2에 1줄 추가는 권장하나 BLOCK 사유 아님 → "Recommendations"로 이관.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|-------|
| 1 | `--phase` 시그니처/계약 불일치 | High | ACCEPT | Both |
| 2 | `--slug` path traversal 미명세 | High | ACCEPT | Cross |
| 3 | Frozen smoke 경로 오류 (`dist/af-1.2.26/...`) | High | ACCEPT | Cross |
| 4 | `iter_warning_records()`로 `scanned_slug_count` 불가 | High | ACCEPT | Cross |
| 5 | `_load_index()` → `config_paths` 부작용 19곳 | High | ACCEPT | Critic |
| 6 | CSV `\;` escape 표준 아님 | High | ACCEPT | Critic |
| 7 | malformed-line 채널 자기모순 (§3.5/§4.4/§8.1) | High | ACCEPT | Critic |
| 8 | `af.spec datas` 추가 row 중복 등록 | Medium | ACCEPT | Both (severity diverged) |
| 9 | `_load_index()` snippet `import sys` 누락 | Medium | ACCEPT | Cross |
| 10 | `install-af.ps1` line 110 이중 등장 | Medium | ACCEPT | Critic |
| 11 | `_PHASE_ORDER` private import fragile | Medium | ACCEPT | Critic |
| 12 | `os.scandir` FileNotFoundError 가드 누락 | Medium | ACCEPT | Critic |
| 13 | `runtime/warnings/_index.json` `git rm` 누락 | Low | ACCEPT | Critic |
| 14 | 로깅 계약 미정의 | Low | HOLD | Cross |
| — | schema_version bump reader 부재 | Low | REJECT | Critic |
| — | CSV `record_count == 0` 미정의 | Low | REJECT | Critic |

---

### Recommendations

구현 진입 전 v4 개정에서 다음을 한 번에 처리:

1. **§5.1 + §3.3 시그니처 재정렬** — `--phase` 등록 + records 모드 거부 정책 결정 + `iter_warning_records(slug, phase)` 인자 통일.
2. **§3.3 보안 가드** — slug 검증 (`safe_id`) + `--slug ../../x` 거부 테스트 추가.
3. **§6.6 + §8.4 frozen 경로 정정** — `dist/af/_internal/config/warning_registry_index.json` + host OS 분기 실행 파일 경로.
4. **§3.3 헬퍼 분리** — `_iter_slug_dirs()` 별도 정의해 `scanned_slug_count`를 record 순회 전 계산.
5. **§3.3 import 격리** — `core.config_paths` 미사용. `sys.executable`/`__file__` 직접 계산 + `import sys` 추가.
6. **§5.2 CSV 처방 재작성** — `affected_ids`를 `json.dumps`로 박거나 분리자 `|`로 변경.
7. **§3.5/§4.4/§8.1 통일** — malformed-line을 `warnings:`에 담을지 stderr-only로 둘지 결정 후 세 곳 동시 정정.
8. **§3.2/§6.6/§7 `af.spec` 정정** — `datas` 추가 제거, 기존 wholesale 항목이 새 파일 포함함을 §6.6 검증으로. `hiddenimports`에 `core.warning_stats` 1줄만.
9. **§8.4 검증 명령 변경** — `grep -c` → `grep -o ... | wc -l` 또는 `sed -i 's/.../g'` 전역 치환.
10. **§4.5 `PHASE_ORDER` 결정** — registry rename(+`__all__`) 또는 `warning_stats.py` 자체 정의 택일.
11. **§3.3 디렉토리 가드 명시** — `if not os.path.isdir(...): return iter(())` + §8.1 case 1을 1a/1b 분리.
12. **§7 `git rm` 명시** — `runtime/warnings/_index.json` 명시 삭제 + §11 자기검증에 `git ls-files` 0 확인.
13. **§3.3 logger 정책 결정** — CLI-only/library 중 택일 후 명시 (HOLD 해소).
14. **(권장)** §6.5 "P4가 schema_version 1 입력 처리 정책을 결정" 단서 1줄. §5.2 "`record_count == 0`이면 헤더 row만 출력" 1줄.