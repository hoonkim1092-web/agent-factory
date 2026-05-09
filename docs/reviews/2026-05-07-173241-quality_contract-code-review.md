# Code Review: quality_contract

> Source: core/research/quality_contract.py
> Date: 2026-05-07 17:32
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 3 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

2 High + 4 Medium findings, no Critical. Can merge with documented risks, but the path traversal issue and silent exception failure mode should be prioritized.

---

### Aggregated Findings (7 total)

#### 1. [ACCEPT] [High] Silent `except Exception` 전체 swallow — YAML 로드 실패 무소음 소거

- **Critic**: "`quality_contract.py:136-138`의 `except Exception: return []`가 `UnicodeDecodeError`·`yaml.YAMLError`·`PermissionError` 전부를 빈 리스트로 변환. `base.yaml` 손상 시 `QualityContractBuildError`가 '어떤 팩이 왜 실패했는지' 진단 없이 발화."
- **Cross**: "직접 플래그 안 함 — Summary에서 '이미 known issue로 기록됨'이라고 명시"
- **Judgment**: Critic 단독이지만 코드 경로 명확. Cross의 비-신규 판정은 거부가 아닌 중복 회피. 사일런트 폴백은 프로덕션 진단을 불가능하게 만드는 High 패턴.
- **Action Required**:
  ```python
  except Exception as e:
      logging.getLogger(__name__).warning("Failed to load pack %s: %s", path, e)
      return []
  ```
  `base.yaml`은 필수이므로 더 강하게: `raise QualityContractBuildError(f"base pack unreadable: {path}") from e`

---

#### 2. [ACCEPT] [High] `WorkSpec` 팩 이름 경로 세그먼트 무정규화 — 경로 순회 가능

- **Critic**: "not flagged"
- **Cross**: "`quality_contract.py:99`에서 `artifact_type`·`capabilities`·`domain_hints`를 YAML 경로에 직접 보간. `WorkSpec(capabilities=['../domains/poker'])`가 의도된 `packs/` 트리 밖을 참조 가능."
- **Judgment**: Cross 단독이지만 경로 순회는 Security 이슈 → 최소 High. `WorkSpecExtractor`가 `.strip()`만 적용하므로 `..` 차단 없음.
- **Action Required**:
  ```python
  # 팩 경로 resolve 후 _PACKS_DIR 하위인지 검증
  resolved = (_PACKS_DIR / subdir / name).resolve()
  if not str(resolved).startswith(str(_PACKS_DIR.resolve())):
      raise ValueError(f"pack name traversal detected: {name}")
  ```
  또는 `core.utils.safe_id()`로 정규화 + `..` 포함 값 즉시 거부.

---

#### 3. [ACCEPT] [Medium] `keywords_for_gap_check()` — optional 항목이 필수 게이트에 참여

- **Critic**: "not flagged"
- **Cross**: "`quality_contract.py:50`에서 `self.checklist` 전체 순회. `required_items()`가 `quality_contract.py:44`에 존재하지만 미사용. `researcher.py:972-983`의 `_is_sufficient()` 70% 임계치 연산에 optional 항목 포함."
- **Judgment**: Cross 단독이지만 `required_items()` API가 존재하면서 쓰이지 않는다는 코드 증거가 명확.
- **Action Required**:
  ```python
  def keywords_for_gap_check(self, include_optional: bool = False) -> ...:
      items = self.checklist if include_optional else self.required_items()
      ...
  ```

---

#### 4. [ACCEPT] [Medium] Coverage 리포트에 keyword 리스트가 아닌 item ID 필요

- **Critic**: "not flagged"
- **Cross**: "`quality_contract.py:51`의 `keywords_for_gap_check()` 반환값(`architecture`, `royal flush`)이 `researcher.py:741-743`의 `match_keywords.get(field, ...)` 호출부에 도달. 이 코드는 checklist field ID(`hand_ranking`, `blind_structure`)를 기대하므로 coverage 리포트의 `matched`/`missing` 집합이 손상."
- **Judgment**: Cross 단독이지만 caller 코드(`researcher.py:741`)의 시그니처 불일치가 코드로 확인됨.
- **Action Required**: keyword 반환 API와 ID 반환 API를 분리하거나, coverage emission에 `QualityContract` 전체를 전달해 내부에서 ID/keyword를 독립 관리.

---

#### 5. [ACCEPT] [Medium] `priority` Literal 런타임 미검증 — 무효값 조용히 저장

- **Critic**: "`quality_contract.py:146`에서 YAML의 `priority: critical`·`priority: hight`가 `Literal["high","medium","low"]` 타입 필드에 조용히 저장. `__post_init__` 검증 없음. `item.priority == 'high'` 필터가 항목을 무소음으로 누락."
- **Cross**: "not flagged"
- **Judgment**: Critic 단독이지만 Python dataclass의 `Literal` 미강제가 언어 특성으로 명확히 검증됨.
- **Action Required**:
  ```python
  priority = entry.get("priority", "medium")
  if priority not in ("high", "medium", "low"):
      priority = "medium"
  ```

---

#### 6. [ACCEPT] [Medium] `id=""` 항목이 `_load_pack`을 통과해 `ChecklistMerger`에서 무소음 소거

- **Critic**: "`quality_contract.py:142`에서 `id=str(entry.get('id') or '')`로 저장. `checklist`는 비어있지 않아 line 120 가드를 통과하지만, `checklist_merger.py:19`의 `if not item.id: continue`가 전체 팩을 소거. `_is_sufficient()`가 빈 체크리스트를 유효로 처리하는 기존 버그와 결합 시 전체 품질 게이트 우회 가능."
- **Cross**: "finding #1(optional items)에서 관련 경로를 간접 언급"
- **Judgment**: Critic이 구체적 코드 경로를 제시. 이전 세션의 "빈 merged checklist" 버그와 동일 취약점 체인.
- **Action Required**:
  ```python
  # quality_contract.py _load_pack() 내부
  item_id = str(entry.get("id") or "")
  if not item_id:
      continue  # 또는 warning 로그
  ```

---

#### 7. [HOLD] [Medium] `__file__` frozen-build 미대응 — af.spec `datas` 누락

- **Critic**: "`quality_contract.py:67`의 `_PACKS_DIR = Path(__file__).parent / 'packs'`가 PyInstaller 빌드에서 `sys._MEIPASS`로 리졸브되지만, `af.spec`에 `core/research/packs` `datas` 항목 없음. 빌드 시 `QualityContractBuildError` 발화."
- **Cross**: "REJECT — '이미 prior review에 기록된 known issue, 중복 안 함'"
- **Judgment**: Cross의 REJECT는 이슈 부재가 아닌 중복 회피. 실제 결함이지만 기존 추적 채널(prior review log)에 이미 등록됨. 이번 diff에서 신규로 처리할 필요 없으나 `af.spec` 업데이트 없이 배포 시 폭발.
- **Question for Author**: `af.spec`에 `core/research/packs` datas 항목이 별도 티켓으로 추적되고 있는지 확인 후 기존 ticket에 연결하거나 이 PR에 포함.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | Silent `except Exception` swallow | High | ACCEPT | Critic |
| 2 | WorkSpec 팩 이름 경로 순회 | High | ACCEPT | Cross |
| 3 | optional 항목 필수 게이트 참여 | Medium | ACCEPT | Cross |
| 4 | Coverage 리포트 keyword/ID 혼용 | Medium | ACCEPT | Cross |
| 5 | `priority` Literal 런타임 미검증 | Medium | ACCEPT | Critic |
| 6 | `id=""` 항목 무소음 소거 | Medium | ACCEPT | Critic |
| 7 | `__file__` frozen-build 미대응 | Medium | HOLD | Critic (Cross: dup) |

---

### Recommendations

- **즉시**: Finding #2 경로 순회 가드 — 외부 입력이 파일시스템 경로로 전달되는 보안 경계
- **즉시**: Finding #1 silent exception에 최소 warning 로그 추가; `base.yaml`은 re-raise 검토
- **이번 PR**: Finding #3/#4 `keywords_for_gap_check()` API 분리 — `required_items()` 사용 전환
- **이번 PR**: Finding #5 `priority` 정규화, Finding #6 `_load_pack` 내 `id=""` 필터
- **별도 티켓 확인**: Finding #7 — `af.spec` `datas` 항목 기존 추적 여부 확인