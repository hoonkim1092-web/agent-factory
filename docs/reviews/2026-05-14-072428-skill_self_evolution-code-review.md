# Code Review: skill_self_evolution

> Source: core/hooks/skill_self_evolution.py
> Date: 2026-05-14 07:24
> Type: code
> Providers: critic=claude, cross=codex, judge=claude
> Mode: cross-review (code, 2 providers)
> Trigger: unknown

---

## Final Code Review

### Verdict: WARN

두 리뷰어가 핵심 이슈에 동의하며, 기능 단절은 없으나 운영 환경에서 false positive WARNING 노이즈를 유발하는 문제가 확인됨.

---

### Aggregated Findings (2 total)

#### 1. [ACCEPT] [High] 알려진 정상 trigger가 "알 수 없는 trigger" WARNING으로 오분류됨

- **Critic**: `"manual"/"schedule"/"quality_check"`는 화이트리스트 외부지만 이미 알려진 유효한 값이다. `logger.warning("[SelfEvolution] 알 수 없는 trigger: ...")` 메시지는 사실과 다르며 운영자를 오도한다.
- **Cross**: `SkillEvolutionBus.on_skill_evolved()` 기본값이 `"manual"`이고(`core/skill_evolution_bus.py:75-86`), `HookEventBus.run_skill_evolved()` 기본값도 `"manual"`(`core/hooks/event_bus.py:105`). 야간 파이프라인의 모든 기본 발화가 WARNING을 찍게 된다.
- **Judgment**: 양측 모두 동일 파일·동일 브랜치를 지목, 증거가 구체적 caller 코드로 뒷받침됨. Cross Review가 실제 기본값 경로를 코드 레벨로 검증했으므로 수용.
- **Action Required**:
  ```python
  _GENERIC_TRIGGERS = {"manual", "schedule", "quality_check"}
  ...
  else:
      if trigger in _GENERIC_TRIGGERS:
          logger.debug("[SelfEvolution] 화이트리스트 외 trigger: %s (skill=%s)", trigger, skill_id)
      else:
          logger.warning("[SelfEvolution] 알 수 없는 trigger: %s (skill=%s)", trigger, skill_id)
  ```
  또는 `_GENERIC_TRIGGERS`를 모듈 상수로 선언 후 분기.

#### 2. [ACCEPT] [Medium] 설계 의도 주석 제거로 유지보수 문맥 소실

- **Critic**: 제거된 주석(`# "manual"/"schedule"/"quality_check" 등 화이트리스트 외 trigger는 정상 경로`)은 `else` 브랜치가 버그 경로가 아님을 명시했다. 이 정보 없이는 미래 기여자가 해당 브랜치를 잘못 판단할 수 있다.
- **Cross**: 직접 언급 없음. 단, `skill_evolution_bus.py` caller 분석에서 해당 설계 의도를 코드 레벨로 간접 확인함.
- **Judgment**: Finding 1의 수정(named constant 도입)이 이 문제를 동시에 해소한다. `_GENERIC_TRIGGERS` 상수 자체가 주석을 대체하는 코드 수준 문서화가 됨.
- **Action Required**: Finding 1 수정과 함께 자동 해소됨. 별도 추가 조치 불필요.

#### [REJECT] Controller 라우팅 영향 없음

- **Cross**: `cross_verification`, `cross_verification_orchestrator`, `fsa_failure` 등 실제 controller caller는 모두 `_CODE_EVOLUTION_TRIGGERS` 내 값을 사용 → `else` 브랜치 미진입. `50 passed` 확인.
- **Judgment**: 기능 단절 없음. 수용.

---

### Summary Table

| # | Title | Severity | Verdict | Source |
|---|-------|----------|---------|--------|
| 1 | 알려진 trigger가 WARNING으로 오분류 | High | ACCEPT | Both |
| 2 | 설계 의도 주석 소실 | Medium | ACCEPT | Critic (Cross 간접 확인) |
| 3 | Controller 라우팅 단절 우려 | Low | REJECT | Cross only |

---

### Recommendations

- `_GENERIC_TRIGGERS = {"manual", "schedule", "quality_check"}` 모듈 상수를 추가하고, `else` 브랜치를 위 상수 기반으로 두 단계 분기로 수정한다.
- `manual` trigger가 `SkillSelfEvolutionHook`을 통과할 때 WARNING이 발생하지 않는지 검증하는 회귀 테스트 1건을 추가한다 (`HookEventBus`/`SkillEvolutionBus` 바인딩 포함).
- 기능은 정상 동작하므로 긴급 BLOCK 사항은 아니나, 야간 파이프라인 운영 중 WARNING 폭탄 방지를 위해 다음 커밋 전 수정 권장.