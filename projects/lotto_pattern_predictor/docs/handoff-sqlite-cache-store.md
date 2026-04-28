---
모듈: SQLite 기반 당첨번호 캐시 저장소
작성일: 2026-04-16
작성자: backend_dev
상태: 검증 완료
---

# Handoff — SQLite 기반 당첨번호 캐시 저장소

## 검증 결과 요약

| 항목 | 결과 |
|------|------|
| `py_compile` | 통과 |
| 단위 테스트 (16건) | 전체 통과 (0.13s) |
| 모듈 임포트 | 정상 |
| 공개 인터페이스 (8 메서드) | 전부 존재 |
| 데이터 왕복 무결성 | 통과 |
| fetcher 모듈 연동 가능성 | 임포트 정상 확인 |

## 산출물

| 파일 | 역할 |
|------|------|
| `src/lotto/cache_store.py` | SQLite 캐시 저장소 구현 (184줄) |
| `src/lotto/exceptions.py` | `CacheError` 예외 클래스 |
| `tests/test_cache_store.py` | 단위 테스트 16건 |

## 공개 인터페이스

```python
class CacheStore:
    def __init__(db_path: Path | str | None = None) -> None  # 기본: data/lotto_cache.db
    def save(result: DrawResult) -> None              # 단건 저장 (중복 무시)
    def save_many(results: list[DrawResult]) -> int   # 일괄 저장, 신규 건수 반환
    def get(draw_no: int) -> DrawResult | None        # 단건 조회
    def get_range(start: int, end: int) -> list[DrawResult]  # 범위 조회
    def get_all() -> list[DrawResult]                 # 전체 조회 (오름차순)
    def get_cached_draw_numbers() -> set[int]         # 캐시된 회차 번호 집합
    def count() -> int                                # 총 레코드 수
    def close() -> None                               # 연결 닫기 (with 구문 지원)
```

## 설계 특징

- **INSERT OR IGNORE**: 중복 회차 저장 시도 시 예외 없이 무시
- **WAL 모드**: 읽기/쓰기 동시성 향상
- **`DrawResult` ↔ SQLite Row 양방향 변환**: `_result_to_row()` / `_row_to_result()` 헬퍼
- **컨텍스트 매니저**: `with CacheStore(...) as store:` 패턴 지원
- **부모 디렉터리 자동 생성**: 파일 기반 DB 사용 시 경로가 없으면 자동 생성

## 잔여 리스크

1. **동시 프로세스 접근**: WAL 모드가 있으나, 다중 프로세스 동시 쓰기 시나리오는 테스트하지 않음. 현재 CLI 단일 실행이므로 실질적 위험 낮음.
2. **대량 데이터 성능**: 500회차 수준에서는 문제 없으나, 인덱스 추가 전략은 미구현 (`draw_no`는 PK이므로 자동 인덱스).
3. **마이그레이션**: 스키마 변경 시 마이그레이션 전략 미구현. 필요 시 추후 별도 구현.

## 후속 작업자 안내

- **통계 분석 엔진 구현 시**: `CacheStore.get_all()` 또는 `get_range()`로 당첨번호를 읽어 분석 데이터로 사용.
- **fetcher ↔ cache 연동**: `LottoFetcher`가 가져온 `DrawResult` 리스트를 `CacheStore.save_many()`로 일괄 저장.
- **캐시 갱신 전략**: `get_cached_draw_numbers()`로 이미 저장된 회차를 확인한 뒤, 미저장 회차만 API 호출하여 효율적으로 갱신 가능.
