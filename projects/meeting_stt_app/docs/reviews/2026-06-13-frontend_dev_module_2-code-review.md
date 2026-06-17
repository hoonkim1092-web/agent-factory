# Code Review: frontend_dev_module_2 (M2 오디오 엔진 — 마이크+시스템오디오 동시 캡처·믹싱)

- **task_id**: frontend_dev_module_2_code_review
- **단계**: code_review
- **역할**: backend_dev_code_reviewer
- **날짜**: 2026-06-13
- **판정**: **PASS** (비차단 advisory 3건)

## 리뷰 대상

| 파일 | 역할 |
|------|------|
| `app/audio/mixer.py` | 두 16kHz mono 스트림 평균 믹싱 + 청크 경계 결정 (리뷰 본체) |
| `tests/test_audio_mixer.py` | 믹싱 정합·청크 경계·단일 소스 회귀 테스트 |
| `app/main.py` (L129~152) | 믹서 배선 + `active_sources` 산출 + 청크 펌프 |
| `app/audio/capture.py` | 캡처 스레드(정규화·리샘플 → push) — 인터페이스 정합 확인용 |

## 핵심 결론 — 인계 결함 수정 검증

선행 핸드오프(`docs/plans/2026-06-13-backend-build-handoff-and-mixer-finding.md` §2)가 인계한
**"두 스트림을 합성하지 않고 연결(concatenate)해 타임라인이 2배가 되고 음성이 비동기화"** 결함이
실제로 수정되었음을 확인했다.

- `_drain_into_pending_locked()`가 `min(len(mic), len(loop))` overlap만 평균 믹싱하고,
  잔여는 파트너 도착을 기다리며 버퍼에 유지한다. 단일 소스(`active_sources<=1`)·`force`(정지 flush)·
  파트너 holdoff(`MIXER_HOLDOFF_SEC=0.5s`) 초과 시에만 단독 통과한다.
- 정상 번갈아 push 패턴(별도 캡처 스레드 교차)에서는 매 pair마다 overlap이 믹싱되며 `_last_sync`가
  갱신되어 holdoff가 발화하지 않는다 → 연결 결함 미발생.
- `app/main.py`가 설정된 device index 개수로 `active_sources`를 산출해 믹서에 주입(prod 배선 end-to-end 연결 확인).

### 테스트가 실제 게이트인지 검증 (mock 아님)

- `test_믹싱_번갈아_push_정렬`: 1024 단위 mic→loop 교차 push 후 길이(==입력 N)·결합값((0.6+0.2)/2=0.4) 동시 단언.
  결함(연결)이면 길이 2N으로 즉시 FAIL.
- `test_믹싱_bulk_push_정렬`: 핸드오프 §2 재현 케이스(3.0s 통째 push) 그대로 게이트.
- `test_믹싱_부분_겹침`: 겹침 평균 믹싱 + 잔여 단독 보존 분리 단언.
- `test_2소스_파트너_영구부재_holdoff_통과`: `_holdoff_sec=0`로 결정성 확보해 holdoff 단독 통과 경로 검증.

→ 픽스처가 직접 답을 주입하는 형태가 아니라 타이밍 분기를 실제로 통과시키는 회귀 테스트다.

## 검토 항목별 결과

1. **보안 취약점**: 해당 없음. 로컬 오디오 DSP로 외부 입력·인증·경로 주입·역직렬화 표면 없음.
   절대경로 하드코딩 없음(`config.py`는 `Path.home()` 파생). 타입 SSOT 준수(`AppSettings`/`TARGET_SAMPLE_RATE` 단일 출처).
2. **버그·엣지케이스**: 청크 경계 off-by-one 없음(`min(n, buf.size)` 가드). 빈 버퍼(`size==0`) early-return.
   `flush`의 `force` drain 후 `min()` 불변식상 한쪽만 잔여 → `_flush_single_locked` 정확. 단일/이중 소스 분기 정합.
3. **설계 품질**: 공개 시그니처(`push_mic`/`push_loopback`/`read_chunk`/`level_changed`, 계약 §3) 유지.
   캡처(정규화·리샘플) ↔ 믹서(16kHz mono 가정) 책임 분리 명확. `_lock` 단일·`_locked` 네이밍 규율로
   재진입/데드락 없음(중첩 락 획득 경로 없음).
4. **에러 처리**: 캡처 스레드 장치 오류를 캡처 중단으로 격리(앱 전체 계속). 헤드리스 기동 보장
   (pyaudiowpatch 미설치 시 무동작). 믹서는 순수 numpy로 예외 표면 작음.
5. **성능**: 16kHz·1024프레임(~16 push/s/stream) 대상에서 현 구조 충분. (advisory #2 참조)

## 비차단 발견 사항 (advisory — 수정 의무 없음)

### A1. 레벨 미터가 믹싱 레벨이 아닌 "마지막 push 스트림" RMS를 방출 + 경미한 데이터 레이스 (LOW)
- `mixer.py:170 _maybe_emit_level(arr)`는 push된 단일 스트림 `arr`의 RMS를 방출한다. 이중 소스에서는
  mic·loop가 번갈아 push되므로 미터 값이 두 스트림 레벨 사이를 오간다(믹싱 결과 레벨이 아님).
- `_last_level_emit`을 락 밖에서 두 캡처 스레드가 읽기/쓰기 → 드물게 throttle 통과가 중복돼 두 번 emit 가능.
  값 손상 없음(미터 갱신이 가끔 한 번 더 될 뿐). 기능 영향 미미.
- **판단**: UX/표시 정밀도 이슈. 계약 위반 아님. M2 소유자 재량.

### A2. `deque[float]` + 요소별 `np.fromiter(popleft)` 패턴의 미세 비효율 (LOW)
- 오디오 샘플을 Python float 객체 deque로 보관하고 drain 시 요소 단위로 popleft.
  16kHz·1024프레임에서는 부하 무시 가능하나, 더 높은 레이트/긴 holdoff 버퍼링에선 비효율.
- **판단**: 현 타깃 레이트에서 비차단. 필요 시 "np 배열 청크 리스트 + 인덱스 커서" 구조로 개선 여지.

### A3. `to_mono_float32`의 다채널 reshape 분할 가능성 미가드 (LOW)
- `mixer.py:52 arr.reshape(-1, channels)`는 버퍼 길이가 channels 배수가 아니면 `ValueError`.
  정상 캡처(`frames_per_buffer*channels` 정수배)에서는 발생 안 함. 부분 read 등 비정상 경로에서만 가능하며,
  발생 시 캡처 `_run`의 except로 흡수되어 캡처만 중단(앱 유지) — fail-safe.
- **판단**: 저확률 엣지. 방어 가드(잘림 처리) 추가는 선택.

## 최종 판정

**PASS** — 인계된 임계 믹싱 결함이 정확히 수정되었고, 타이밍 분기를 실제로 통과시키는 회귀 테스트로 게이트된다.
보안·설계·에러 처리 결함 없음. 발견 3건은 모두 LOW 비차단 advisory로 계약 위반이나 기능 차단이 아니다.
M2 소유자가 advisory 반영 여부를 판단한다.
