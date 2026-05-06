# Code Review: researcher

> Source: core/researcher.py
> Date: 2026-05-05 00:21
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: BLOCK

**Cross Review 상태**: 프로바이더 오류로 완료 실패 (OpenAI Codex 세션 초기화 중 중단). 따라서 모든 판정은 Critic 단독 소스 기반이나, 각 발견은 diff에서 직접 검증되었다.

---

### Aggregated Findings (5 total)

#### 1. [ACCEPT] [High] `break`이 내부 루프만 탈출 — 원래 `return`과 동작이 다름

- **Critic**: `break`으로 교체 시 외부 `for root in roots` 루프가 계속 진행, limit 초과 수집 발생
- **Cross**: not flagged (오류로 미완료)
- **Judgment**: Diff에서 직접 확인됨. 원래 코드의 두 `return refs` 모두 제거되고 단일 `break`으로 대체됨. `break`은 `for result in results` 내부 루프만 탈출하므로 외부 루프는 다음 root를 계속 순회한다. 명확한 동작 회귀.
- **Action Required**: `break` 후 외부 루프도 탈출하도록 수정. `if len(refs) >= limit: break` 이후 `if len(refs) >= limit: break`를 외부 루프에도 추가하거나, 로직을 별도 헬퍼 함수로 분리해 `return`으로 직접 탈출.

---

#### 2. [ACCEPT] [High] 도메인 화이트리스트 서브스트링 매칭 — 스푸핑 가능

- **Critic**: `d in url_host` 서브스트링 매칭으로 `fakepokerstars.com`이 `pokerstars.com` 화이트리스트 통과
- **Cross**: not flagged (오류로 미완료)
- **Judgment**: Diff 확인됨: `trust_score = 0.4 if any(d in url_host for d in _AUTHORITY_DOMAINS_POKER) else 0.0`. Python `in` 연산자는 서브스트링 매칭이므로 공격 가능. trust_score가 정렬 키(`raw_score * (1 + trust_score)`)에 직접 영향을 미쳐 결과 순서가 조작됨.
- **Action Required**:
  ```python
  trust_score = 0.4 if any(
      url_host == d or url_host.endswith("." + d)
      for d in _AUTHORITY_DOMAINS_POKER
  ) else 0.0
  ```

---

#### 3. [ACCEPT] [High] A2 도메인 가드 — 매칭 없을 시 refs 전체 소멸

- **Critic**: 토큰 매칭 실패 시 필터 후 `refs`가 빈 리스트, 웹 fallback 강제 발동으로 불필요한 API 비용 발생
- **Cross**: not flagged (오류로 미완료)
- **Judgment**: Diff 확인됨. `if domain_tokens:` 분기 내 list comprehension이 매칭 실패 시 빈 리스트를 반환하고 안전망 없음. 이전 코드는 항상 최대 `limit`개를 반환했다. 운영 환경에서 API 비용 회귀.
- **Action Required**: 필터 후 빈 리스트면 원본 `refs[:limit]` 반환:
  ```python
  if domain_tokens:
      filtered = [r for r in refs if any(...)]
      if filtered:
          refs = filtered
  return refs[:limit]
  ```

---

#### 4. [ACCEPT] [Medium] `domain_checklist` 70% 임계값 — float 비교 오류

- **Critic**: `matched < len(domain_checklist) * 0.7` 에서 3항목 기준 `2 < 2.1 → True` → 사실상 100% 요구
- **Cross**: not flagged (오류로 미완료)
- **Judgment**: Diff 확인됨: `if matched < len(domain_checklist) * 0.7`. P0에서는 `domain_checklist=None`으로만 호출되므로 현재 런타임 영향은 없으나, P1 활성화 시 즉시 버그로 발현.
- **Action Required**:
  ```python
  if matched / len(domain_checklist) < 0.7:
      return False
  ```

---

#### 5. [ACCEPT] [Low] `import re` 메서드 내부 위치

- **Critic**: 메서드 호출마다 `import re` 실행, 파일 상단 컨벤션과 불일치
- **Cross**: not flagged (오류로 미완료)
- **Judgment**: `_extract_domain_tokens` 메서드 내 `import re` 확인됨. 성능 영향은 Python 캐싱으로 미미하지만 기존 파일 스타일과 불일치.
- **Action Required**: 파일 상단 import 블록에 `import re` 추가, 메서드 내 제거.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | `break` 내부 루프만 탈출 | High | ACCEPT | Critic |
| 2 | 도메인 서브스트링 스푸핑 | High | ACCEPT | Critic |
| 3 | A2 가드 silent empty | High | ACCEPT | Critic |
| 4 | 70% float 비교 오류 | Medium | ACCEPT | Critic |
| 5 | `import re` 위치 | Low | ACCEPT | Critic |

---

### Recommendations

- **즉시 수정 (merge 전 필수)**: Finding 1(`break` → 이중 루프 탈출), Finding 2(서브스트링 → suffix 매칭), Finding 3(empty refs 안전망)
- **수정 권장**: Finding 4(`matched / len(...)` 비율 비교) — P0에서는 dead code지만 P1 진입 전 선수 수정
- **정리**: Finding 5(`import re` 파일 상단 이동)
- **Cross Review 재실행**: 프로바이더 오류로 교차검증 미완료. 수정 후 재커밋 시 Cross Review도 재실행 필요