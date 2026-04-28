# 동행복권 API 데이터 수집 모듈 — 범위 및 인터페이스 정의

## 메타데이터
- 작업 ID: `backend_dev_module_1_scope_1`
- 작성자: backend_dev
- 작성일: 2026-04-16
- 상태: 확정

---

## 1. 모듈 목적

동행복권(dhlottery.co.kr) 공개 API에서 로또 6/45 당첨번호를 회차별로 수집하여
정규화된 `DrawResult` 데이터 객체로 반환한다.

---

## 2. 범위

### 포함
| 항목 | 설명 |
|------|------|
| API 호출 | `GET https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={회차}` |
| 응답 파싱 | JSON → `DrawResult` dataclass 변환 |
| 회차 범위 계산 | 최신 회차 자동 탐지 + 최근 500회차 범위 산출 |
| 증분 수집 | 이미 캐시된 회차는 건너뛰고 미수집 회차만 요청 |
| 속도 제한 | 요청 간 딜레이(기본 0.5초)로 서버 차단 방지 |
| 재시도 | 네트워크 오류 시 최대 3회 지수 백오프 재시도 |
| 진행 표시 | 수집 진행률을 stdout으로 출력 |

### 제외
| 항목 | 사유 |
|------|------|
| SQLite 저장 | `cache_store` 모듈 책임 |
| 통계 계산 | `analysis_engine` 모듈 책임 |
| CLI 파싱 | `cli` 모듈 책임 |
| 로그인/인증 | 공개 API이므로 불필요 |

---

## 3. 외부 API 스펙

### 엔드포인트
```
GET https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={회차번호}
```

### 응답 JSON 스키마 (성공 시)
```json
{
  "returnValue": "success",
  "drwNo": 1130,
  "drwNoDate": "2024-09-28",
  "drwtNo1": 3,
  "drwtNo2": 11,
  "drwtNo3": 15,
  "drwtNo4": 29,
  "drwtNo5": 35,
  "drwtNo6": 44,
  "bnusNo": 40,
  "totSellamnt": 112656985000,
  "firstWinamnt": 2256981953,
  "firstPrzwnerCo": 13,
  "firstAccumamnt": 29340765389
}
```

### 응답 JSON (실패 시)
```json
{
  "returnValue": "fail"
}
```

### 참고
- 비공식 API이므로 응답 형식 변경 가능성이 있다.
- User-Agent 헤더를 포함해야 안정적으로 응답을 받을 수 있다.
- 과도한 요청 시 IP 차단 가능성이 있다.

---

## 4. 인터페이스 정의

### 4.1 데이터 모델

```python
# src/lotto/models.py

from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class DrawResult:
    """단일 회차 로또 당첨 결과."""
    draw_no: int                    # 회차 번호
    draw_date: date                 # 추첨일
    numbers: tuple[int, ...]        # 당첨 번호 6개 (오름차순 정렬)
    bonus: int                      # 보너스 번호
    total_sell_amount: int          # 총 판매금액
    first_prize_amount: int         # 1등 당첨금액
    first_prize_winners: int        # 1등 당첨자 수
```

### 4.2 수집기 클래스

```python
# src/lotto/fetcher.py

from typing import Callable, Optional

class LottoFetcher:
    """동행복권 API 데이터 수집기."""

    def __init__(
        self,
        request_delay: float = 0.5,
        max_retries: int = 3,
        timeout: float = 10.0,
    ) -> None: ...

    def fetch_draw(self, draw_no: int) -> DrawResult:
        """단일 회차 당첨번호를 조회한다.

        Args:
            draw_no: 회차 번호 (양의 정수)

        Returns:
            DrawResult 객체

        Raises:
            DrawNotFoundError: 존재하지 않는 회차
            FetchError: 네트워크 오류 또는 API 응답 파싱 실패
        """
        ...

    def fetch_latest_draw_no(self) -> int:
        """현재 최신 회차 번호를 탐지한다.

        이진 탐색으로 returnValue == 'success'인 가장 큰 회차를 찾는다.

        Returns:
            최신 회차 번호
        """
        ...

    def fetch_range(
        self,
        start: int,
        end: int,
        *,
        skip: Optional[set[int]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> list[DrawResult]:
        """회차 범위를 순차적으로 수집한다.

        Args:
            start: 시작 회차 (포함)
            end: 종료 회차 (포함)
            skip: 건너뛸 회차 집합 (이미 캐시된 회차)
            on_progress: 진행 콜백 (현재 인덱스, 전체 개수)

        Returns:
            수집된 DrawResult 리스트
        """
        ...
```

### 4.3 예외 클래스

```python
# src/lotto/exceptions.py

class LottoError(Exception):
    """로또 모듈 기본 예외."""
    pass

class DrawNotFoundError(LottoError):
    """존재하지 않는 회차를 조회했을 때 발생."""
    pass

class FetchError(LottoError):
    """네트워크 오류 또는 API 응답 파싱 실패 시 발생."""
    pass
```

---

## 5. 의존성

### 외부 패키지
| 패키지 | 버전 | 용도 |
|--------|------|------|
| `requests` | ≥2.31 | HTTP GET 요청 |

### 표준 라이브러리
- `json`, `time`, `dataclasses`, `datetime`, `typing`

### 내부 의존성
- 없음 (이 모듈은 최하위 계층이므로 다른 모듈에 의존하지 않음)

---

## 6. 산출물

| 파일 경로 | 설명 |
|-----------|------|
| `src/lotto/__init__.py` | 패키지 초기화 |
| `src/lotto/models.py` | `DrawResult` 데이터 모델 |
| `src/lotto/exceptions.py` | 예외 클래스 정의 |
| `src/lotto/fetcher.py` | `LottoFetcher` 수집기 구현 |
| `tests/test_fetcher.py` | 단위 테스트 (모킹 기반) |

---

## 7. 구현 순서

| 순서 | 슬라이스 | 설명 |
|------|----------|------|
| 1 | `models.py` + `exceptions.py` | 데이터 모델과 예외 정의 (의존성 없음) |
| 2 | `fetcher.py` — `fetch_draw()` | 단일 회차 조회 + JSON 파싱 + 재시도 |
| 3 | `fetcher.py` — `fetch_latest_draw_no()` | 이진 탐색 기반 최신 회차 탐지 |
| 4 | `fetcher.py` — `fetch_range()` | 범위 수집 + skip + 딜레이 + 진행 콜백 |
| 5 | `tests/test_fetcher.py` | 모킹 기반 단위 테스트 |

---

## 8. 하위 모듈 연동 계약

이 모듈의 출력(`list[DrawResult]`)을 소비하는 모듈:

| 소비 모듈 | 사용 방식 |
|-----------|-----------|
| `cache_store` (SQLite) | `DrawResult` → INSERT INTO draws 테이블 |
| `analysis_engine` | `list[DrawResult]` → 빈도/동시출현 통계 계산 |

`DrawResult`는 `frozen=True` dataclass이므로 불변이며, 소비 모듈은 이 객체를 읽기 전용으로 사용한다.

---

## 9. 리스크 및 완화 전략

| 리스크 | 영향 | 완화 |
|--------|------|------|
| API 응답 형식 변경 | 파싱 실패 | 응답 필드 검증 후 명확한 `FetchError` 발생 |
| IP 차단 | 수집 불가 | 요청 간 딜레이 0.5초, 지수 백오프 재시도 |
| 네트워크 타임아웃 | 수집 지연 | 10초 타임아웃 + 3회 재시도 |
| 최신 회차 탐지 실패 | 범위 계산 오류 | 이진 탐색 범위를 충분히 넓게 설정 (1~2000) |
