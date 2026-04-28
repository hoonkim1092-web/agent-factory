class InvalidRequestError(ValueError):
    """추천 요청 입력이 유효하지 않을 때 발생한다."""


class RuleConflictError(ValueError):
    """규칙 조합이 상호 충돌해 후보를 만들 수 없을 때 발생한다."""


class InsufficientCandidateError(RuntimeError):
    """필터를 통과한 후보가 목표 개수보다 부족할 때 발생한다."""
