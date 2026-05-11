# Design Review: 2026-05-11-astengine-revival-impact-analysis

> Source: docs/2026-05-11-astengine-revival-impact-analysis.md
> Date: 2026-05-11 13:25
> Type: design
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (design, 2 providers)
> Trigger: unknown

---

## Final Design Review

### Verdict: BLOCK

**Note on inputs**: Cross review failed at provider level (`model: gpt-5.5` 잘못된 모델 ID로 Codex CLI가 stdin에서 멈춤 — 실제 리뷰 본문 0건). 따라서 본 집계는 **critic 단독 근거**로 진행하되, 단독 출처 finding은 "evidence 강도"로만 판단(룰 2). Critic이 코드 라인까지 인용한 발견 위주로 ACCEPT.

2건의 Critical(F1, F2)이 모두 "스니펫이 현재 코드에서 실행 불가"라는 **검증 가능한 구조적 차단**이라 BLOCK 외 선택지 없음.

### Aggregated Findings (9 total)

#### 1. [ACCEPT] [Critical] §2.1 `git_manager.diff_files_since()` 미존재 API
- **Critic**: `core/git_manager.py` 95줄 전체에 해당 메서드 없음 (5개 메서드만 존재). `snapshot_sha` 보관 위치도 미정의.
- **Cross**: not flagged (provider error)
- **Judgment**: critic이 파일 라인 수·메서드명까지 인용. 즉시 검증 가능한 사실. LOC 50줄 추정은 헬퍼 신설(20~30LOC) + SHA 캡처 + non-git fallback 누락분만 따져도 2~3배 과소.
- **Action Required**: §2.1에 (a) `GitManager.diff_files_since(sha)` 헬퍼 신규 명세, (b) task 시작 SHA 캡처 위치(orchestrator state), (c) non-git 워크스페이스 fallback 코드까지 포함하고 LOC 재추정.

#### 2. [ACCEPT] [Critical] §3.1 `AgentSpecializer.subscribe()` 구조적 작동 불가
- **Critic**: 3중 결함 — (a) `AgentSpecializer.__init__` 없음·`_memory_hub` 속성 없음 → `AttributeError`, (b) `specialize()`는 dict 팩토리지 long-lived subscriber 아님, (c) `agent_worker.py`는 task.json/result.json 파일 IPC 별도 프로세스 → in-process pub/sub과 메모리 공유 불가.
- **Cross**: not flagged (provider error)
- **Judgment**: critic이 클래스 line 범위(L23-58), worker 라인 수(109), hub singleton 라인(L22-27)까지 인용. (c)는 work-item 승격의 결정타 — IPC 신설(~300LOC) 없이는 pub/sub 자체가 환상.
- **Action Required**: §3 전체를 "orchestrator 측 `hub.get_summary()` → `task_meta['peer_changes']` 인젝션" 패턴으로 재설계. 진짜 in-process pub/sub이 필요하면 별도 work-item으로 분리하고 IPC LOC 명시.

#### 3. [ACCEPT] [High] §6.2 LOC 추정에 consumer·헬퍼 누락 (자기모순)
- **Critic**: §6.1 본인이 "consumer 없으면 dead code" 진단했으나 §6.2는 consumer LOC 0줄. F1 신규 헬퍼도 미반영. 실제 400~600LOC / 3~5일이 현실적.
- **Cross**: not flagged (provider error)
- **Judgment**: critic 진단 §6.1과 §6.2 자체가 같은 문서 내 모순 — 외부 검증 없이도 문서 내적 일관성 결함 확인 가능.
- **Action Required**: §6.2를 `[Core 4건]` / `[Consumer/IPC/Helpers 부속]` 두 표로 분리. 후자 LOC가 더 크면 §6.3 우선순위를 `implementation unit` 단위로 재정의.

#### 4. [ACCEPT] [High] §4.1 인코딩 누락 — Windows 회귀
- **Critic**: `open(filepath)`가 OS default(Windows cp949) → 비-ASCII identifier 만나면 `UnicodeDecodeError`로 후처리 abort.
- **Cross**: not flagged (provider error)
- **Judgment**: 본 프로젝트가 Windows 11 호스트(`gitStatus` 환경에서 명시). 회귀 가능성 명확.
- **Action Required**: §4.1 코드를 `open(filepath, "rb")` + `ast.parse(data)` 또는 `tokenize.open(filepath)`로 교체. except 절에 `UnicodeDecodeError`·`OSError` 추가. §4.5 위험표에 한 줄 추가.

#### 5. [ACCEPT] [High] `AstMemoryHub.reset()` silent unsubscribe 위험
- **Critic**: `reset()`(L42-48)이 `subscribers = {}`로 통째 비움 → subscribe 시점이 reset보다 빠르면 콜백 손실. 문서 §3.5 위험 항목 없음.
- **Cross**: not flagged (provider error)
- **Judgment**: 라인 인용으로 즉시 검증 가능. Finding #2(F2)를 dict 인젝션 패턴으로 재설계하면 자동 회피되므로 #2 해결로 연쇄 close 가능.
- **Action Required**: §3.5 위험 항목 추가. 완화책은 F2 재설계와 묶어 처리.

#### 6. [ACCEPT] [Medium] §4.1 `ast.dump(...)[:5000]` 토큰 boundary 무시 + 문서 모순
- **Critic**: §4.5는 "tree 전체 저장 X, 시그니처만"이라 결론지었으나 §4.1 코드는 여전히 5000자 슬라이스 — 같은 문서 내부 모순.
- **Cross**: not flagged (provider error)
- **Judgment**: 문서 자체 모순. 외부 검증 불필요.
- **Action Required**: §4.1에서 ast.dump 슬라이스 옵션 제거. ast-grep-py 옵션 또는 `ast.walk`로 FunctionDef/ClassDef만 추출하는 30LOC 헬퍼로 단일화.

#### 7. [ACCEPT] [Medium] §6.3 우선순위 권고가 §6.1과 순환 모순
- **Critic**: §6.1 "consumer 없으면 무용" vs §6.3 "수정 2 단독 1순위" — 자기부정.
- **Cross**: not flagged (provider error)
- **Judgment**: 문서 내 자기모순 — 외부 근거 불필요.
- **Action Required**: §6.3을 "수정 2 + Lilith prompt consumer 묶음을 1순위"로 재기술. 단독 수정 단위 권고 폐기.

#### 8. [ACCEPT] [Medium] §1.5 ast-grep-py 휠 검증 문구 — 사실 오인
- **Critic**: `requirements.txt:12` + `af.spec:281` 이미 등록·통합. "검증 필요" 문구는 부정확.
- **Cross**: not flagged (provider error)
- **Judgment**: critic이 파일·라인 인용. 즉시 확인 가능.
- **Action Required**: §1.5 문구를 "이미 등록(af.spec:281, requirements.txt:12). 신규 OS/ARCH 추가 시 휠 가용성 확인 필요"로 수정.

#### 9. [HOLD] [Medium] subscribers dict race condition
- **Critic**: subscribe/unsubscribe에 락 없음. publish의 list comprehension rebind(L67)는 원자성 없음 → 일관성 깨질 수 있음.
- **Cross**: not flagged (provider error)
- **Judgment**: 이론적으로는 맞으나, F2(§3 재설계)가 ACCEPT되면 in-process subscribe 자체가 사라져 본 finding 의미 없어짐. F2 처리 후 잔존 여부 판단.
- **Question for Author**: F2를 dict 인젝션 패턴으로 재설계 후에도 외부에서 subscribe하는 caller가 남는가? 남으면 `subscribe()`/`unsubscribe()`도 락 추가 필요.

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | §2.1 diff_files_since 미존재 API | Critical | ACCEPT | Critic |
| 2 | §3.1 subscribe 구조적 작동 불가 (3중) | Critical | ACCEPT | Critic |
| 3 | §6.2 LOC consumer/헬퍼 누락 | High | ACCEPT | Critic |
| 4 | §4.1 인코딩 누락 (Windows) | High | ACCEPT | Critic |
| 5 | reset() silent unsubscribe | High | ACCEPT | Critic |
| 6 | §4.1 ast.dump 슬라이스 + 문서 모순 | Medium | ACCEPT | Critic |
| 7 | §6.3 우선순위 자기모순 | Medium | ACCEPT | Critic |
| 8 | §1.5 ast-grep-py 휠 사실 오인 | Medium | ACCEPT | Critic |
| 9 | subscribers race condition | Medium | HOLD | Critic |

### Recommendations
- **선차단**: Finding 1, 2를 해소하지 않으면 work-item 승격 의미 없음. (1) `GitManager.diff_files_since` 헬퍼 + SHA 캡처 + non-git fallback 3종 명세화. (2) §3을 "orchestrator-side `task_meta['peer_changes']` 인젝션" 패턴으로 전면 재설계 — pub/sub 환상 폐기.
- **문서 자기일관성 복구**: Finding 6, 7은 critic 검증 없이도 문서 내 모순. §4.1 단일화 + §6.3 bundled implementation unit 재정의.
- **§6.2 재추정**: Finding 3에 따라 `[Core]` / `[Consumer/IPC/Helpers]` 두 표로 분리. 실제 작업량 400~600LOC / 3~5일 기준 work-item 분할 판단.
- **§4.1 인코딩 픽스**: `tokenize.open()` 또는 binary read + `ast.parse(bytes)`. Windows 호스트 회귀 차단 필수.
- **Cross review 재실행**: 본 집계는 critic 단독 — 가능하면 codex provider 모델 ID 수정(`gpt-5.5` → 실제 가용 모델) 후 cross review 재수행해 single-source 리스크 해소.
- **v2 재제출 후 재리뷰**: 위 5건 반영한 v2 작성 후 af-cross-review 재발화.