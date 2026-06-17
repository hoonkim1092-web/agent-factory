# Escalation Decision — 마이크와-시스템오디오-wasapi-loopback-를-동시에-녹음하면서-로컬-faster-whisper로-실

- last_updated: 2026-06-13T07:06:52
- activate_phase: P4
- block: false
- blocking_rules: (없음)
- reason: no_active_blocks_in_run

## 평가된 모든 규칙

| rule_id | block | severity | reason |
|---------|-------|----------|--------|
| e2e_command_missing | false | warn | false_positive_override |

## 부록: summary 스냅샷

```json
{
  "project_slug": "마이크와-시스템오디오-wasapi-loopback-를-동시에-녹음하면서-로컬-faster-whisper로-실",
  "last_updated": "2026-06-13T07:06:52",
  "by_rule": {
    "e2e_command_missing": {
      "count": 30,
      "first_ts": "2026-06-13T07:04:59",
      "last_ts": "2026-06-13T07:04:59",
      "severity": "warn",
      "by_phase": {
        "scope": 10,
        "build": 10,
        "verify": 10
      },
      "repeat_count_max": 3,
      "any_override": true
    }
  },
  "by_severity": {
    "warn": 30,
    "block_candidate": 0,
    "block": 0
  },
  "escalation_phase": "P4"
}
```
