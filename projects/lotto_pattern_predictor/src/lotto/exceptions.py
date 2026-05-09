"""로또 모듈 예외 계층."""


class LottoError(Exception):
    """로또 모듈 최상위 예외."""


class FetchError(LottoError):
    """API 호출 또는 응답 처리 실패."""


class DrawNotFoundError(FetchError):
    """요청한 회차가 존재하지 않음."""

    def __init__(self, draw_no: int) -> None:
        self.draw_no = draw_no
        super().__init__(f"회차 {draw_no}번 데이터를 찾을 수 없습니다")


class CacheError(LottoError):
    """캐시 저장소 읽기/쓰기 오류."""


class AnalysisError(LottoError):
    """통계 분석 처리 오류."""
