# Escalation Decision — 마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시

- last_updated: 2026-06-13T06:47:01
- activate_phase: P4
- block: true
- blocking_rules: e2e_command_missing
- reason: blocked_by:e2e_command_missing

## 차단 근거

### e2e_command_missing
- 매칭 phase: scope (11건), scope (11건)
- exempt phase: scope

**해소 방법** (택 1):
1. 각 task의 `e2e_command` 필드를 채운 후 work-item 문서 재생성
2. `af warning-override --workspace . --slug 마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시 --rule e2e_command_missing --reason "<이유>"` 로 false-positive 표시
3. `config/escalation_policy.yaml` 에서 `activate_at` 을 `never` 로 변경 (전역 비활성, 권장하지 않음)

## 평가된 모든 규칙

| rule_id | block | severity | reason |
|---------|-------|----------|--------|
| e2e_command_missing | false | warn | exempt_phase:scope |
| e2e_command_missing | true | block | threshold_met |

## 부록: summary 스냅샷

```json
{
  "project_slug": "마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시",
  "last_updated": "2026-06-13T06:47:01",
  "by_rule": {
    "e2e_command_missing": {
      "count": 33,
      "first_ts": "2026-06-13T06:47:01",
      "last_ts": "2026-06-13T06:47:01",
      "severity": "warn",
      "by_phase": {
        "scope": 11,
        "build": 11,
        "verify": 11
      },
      "repeat_count_max": 3,
      "any_override": false
    }
  },
  "by_severity": {
    "warn": 33,
    "block_candidate": 0,
    "block": 0
  },
  "escalation_phase": "P4"
}
```
