---
id: writing_skills
name: Writing Skills
version: 0.1.0
inspired_by: superpowers/writing-skills
description: AF SKILL.md 작성 가이드 — 외부 패턴·반복 절차를 재사용 가능한 knowledge skill로 변환하는 4단계 흡수 워크플로.
when_to_use: 새 SKILL.md knowledge skill 작성 시. 외부 플레이북·superpowers 패턴을 AF에 흡수할 때. 반복 절차를 triggerable skill로 만들 때.
when_NOT_to_use: skill.py action skill 구현. core/ 코드 변경. 일회성 프로젝트 노트 작성 (docs/에 저장할 것).
when_to_use_keywords:
  - skill
  - SKILL.md
  - 스킬
  - 스킬작성
  - 스킬흡수
  - skill absorption
  - knowledge skill
  - superpowers
  - 흡수
  - 외부스킬
  - writing
category: skill-authoring
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags:
  - skills
  - authoring
  - absorption
  - knowledge
---

# Writing Skills 가이드

Knowledge skill을 새로 만들거나 외부 패턴을 AF에 흡수할 때 사용한다.

## 적합성 판단 (Fit Check)

SKILL.md를 생성하기 전에 아래 5가지를 모두 확인한다. 하나라도 'NO'면 docs/에 기록하고 SKILL.md는 만들지 않는다.

| 조건 | 확인 |
|------|------|
| 여러 작업에서 반복 사용 가능한 절차인가? | YES / NO |
| 트리거 조건을 프론트매터로 명확히 표현할 수 있는가? | YES / NO |
| 관련 요청 시에만 로드해도 충분한가? (always-on 불필요) | YES / NO |
| 실행 가능한 절차이지 배경 리서치가 아닌가? | YES / NO |
| 코드 없이 글로만 동작을 바꿀 수 있는가? | YES / NO |

---

## Step 1 — 외부 소스 파악

흡수 전 확인:

1. **원본 식별** — 흡수할 패턴의 출처를 `superpowers/<id>` 또는 URL로 기록한다.
2. **AF 중복 확인** — `grep -r "키워드" skills/` 로 동일 절차가 이미 있는지 확인한다.
3. **핵심 비-자명 패턴 추출** — 모델이 이미 알 법한 일반 조언은 제외하고, AF 특화 절차만 추출한다.

---

## Step 2 — 프론트매터 작성

```yaml
---
id: <snake_case_dir_이름과_동일>
name: <사람이 읽는 이름>
version: 0.1.0        # 신규 흡수는 항상 0.1.0 시작
inspired_by: superpowers/<원본-id>   # AF-native이면 생략
description: <주제 + 트리거 조건을 한 문장으로>
when_to_use: <구체적 발화 조건>
when_NOT_to_use: <명확한 제외 조건 — false positive 방지>
when_to_use_keywords:
  - <한국어 키워드>
  - <English keyword>
  - ...
category: <도메인>
skill_type: knowledge
auto_invocable: true
user_invocable: true
planner_invocable: true
tags: [...]
---
```

**금지**: 구현하지 않은 자동화를 `description`에 약속하지 않는다.

---

## Step 3 — 본문 작성

구조 기준:

1. **목적** — 이 skill이 로드된 후 에이전트 행동이 어떻게 바뀌는지 한 문장.
2. **적합성 판단** — 언제 쓰고 언제 쓰지 않는지.
3. **절차** — 3~6단계 순서형 지침. 각 단계에 실행 명령 또는 체크 포함.
4. **출력/검증 기준** — 완료 전 무엇이 참이어야 하는지.
5. **체크리스트** — 짧고 실행 가능하고 테스트 가능한 항목들.

> **금지**: 동기부여 언어, 일반적 조언, 긴 에세이. 모델이 이미 아는 것은 쓰지 않는다.

---

## Step 4 — 검증

작성 후 확인:

```bash
# 발견 경로 확인
.venv/bin/python -c "
from core.utils import resolve_knowledge_skill_path
print(resolve_knowledge_skill_path('<skill_id>'))
"

# 관련 테스트 실행
.venv/bin/python -m pytest tests/test_skill_metadata_adapter.py \
  tests/test_cross_cli_skill_discovery.py -q
```

경로가 `None`이면 `id` 필드와 디렉토리 이름이 일치하는지 확인한다.

---

## 체크리스트

- [ ] Step 1: 원본 출처 확인, AF 중복 없음 확인
- [ ] Step 2: 프론트매터 — `id`=디렉토리명, `inspired_by` (외부소스만), `version=0.1.0`
- [ ] Step 3: 본문이 절차형 (리서치 아카이브 아님)
- [ ] Step 3: `when_NOT_to_use` 명시 (false positive 방지)
- [ ] Step 4: `resolve_knowledge_skill_path('<id>')` — None 아님
- [ ] Step 4: `test_skill_metadata_adapter` PASS
