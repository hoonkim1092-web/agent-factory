# Implementation Design — 오디오 엔진 (M2)

- **work-item**: `audio-engine`
- **task_id**: `frontend_dev_module_2_scope_1`
- **단계**: scope (구현 순서·내부 설계 고정)
- **상태**: frozen
- **짝 문서**: `feature-spec.md`(범위·공개 계약), `docs/plans/2026-06-13-backend-build-handoff-and-mixer-finding.md`(결함 인계)
- **문서 언어**: 한국어

이 문서는 as-built 코드의 **내부 설계·함수 단위 책임·구현 순서**를 고정한다. 공개 시그니처는 feature-spec §3에서
동결됐고 여기서 재논의하지 않는다.

---

## 1. 모듈 내부 설계

### 1.1 `capture.py` — `CaptureThread`
- **책임**: 단일 WASAPI 장치 1개를 백그라운드 스레드에서 캡처하여 16kHz mono float32 프레임을 콜백 전달.
- **흐름**(`_run`):
  1. `pyaudiowpatch.PyAudio()` → `get_device_info_by_index` 로 네이티브 `defaultSampleRate`/`maxInputChannels` 조회.
  2. `pa.open(format=paInt16, channels=native, rate=native, frames_per_buffer=1024, input=True, input_device_index=...)`.
  3. 루프: `stream.read(1024, exception_on_overflow=False)` → `np.frombuffer(int16)` →
     `to_mono_float32(pcm, channels)` → `resample_to_16k(mono, src_rate)` → `on_frames(frames)`.
  4. 모든 장치 오류는 캡처 스레드 종료로 흡수(앱 전체는 계속). `finally`에서 stream/PyAudio 정리.
- **graceful**: `device_index is None` 또는 `import pyaudiowpatch` 실패 시 `start()`가 조용히 무동작.
- **불변식**: 정규화(모노화+리샘플)를 캡처 측에서 끝내 믹서가 rate/channels를 알 필요 없게 한다.

### 1.2 `mixer.py` — 정규화 헬퍼 + `AudioMixer`
- **헬퍼(순수 함수, Qt 비의존)**:
  - `to_mono_float32`: int16→/32768, int32→/2147483648, 그 외 float 캐스팅. 다채널은 `reshape(-1,ch).mean(1)`.
  - `resample_to_16k`: `src_rate==16000`이거나 빈 배열이면 그대로. 아니면 `np.interp` 선형 리샘플.
  - `rms`: `sqrt(mean(square))`.
- **`AudioMixer(QObject)`**:
  - 상태: `_mic`/`_loop` deque(float 샘플), `_pending`(믹싱 결과 list[ndarray]), `_pending_len`,
    `_lock`(threading.Lock), `_last_level_emit`.
  - `push_*` → `_push(buf, frames)`: lock 안에서 `buf.extend` 후 `_drain_into_pending_locked()`,
    lock 밖에서 `_maybe_emit_level`(throttle).
  - `_drain_into_pending_locked()`: `n=min(len(mic),len(loop))` 만큼 정렬 평균 믹싱
    `clip((mic+loop)*0.5, -1, 1)` → `_append_pending`. **n==0일 때 단일 소스 폴백** ← §3 결함 지점.
  - `read_chunk()`: `_pending_len>=max_samples`면 컷; `use_vad`이고 `>=min_samples`면 tail 무음 검사 후 컷.
  - `flush()`: 잔여 drain 후 `_pending_len` 전량 반환.

### 1.3 `devices.py` — enumerate + compute 감지
- `enumerate_devices`: WASAPI host API의 장치를 순회, `isLoopbackDevice`면 loopbacks, `maxInputChannels>0`면 mics.
  단계별 `try/except`로 어떤 실패에서도 부분/빈 목록 반환.
- `detect_compute_device`: `ctranslate2.get_cuda_device_count()`>0 → `("cuda","float16")`, 아니면 `("cpu","int8")`.
  (M3 전사기가 소비하는 SSOT — 본 엔진 코어 흐름과는 분리.)

---

## 2. 배선 불변식 (production 호출 경로)

`app/main.py:PipelineController`가 소유. 본 엔진은 조각만 제공하고 펌프/상태머신은 M1 소유.

```python
mixer = AudioMixer(max_chunk_sec=settings.max_chunk_sec, use_vad=settings.use_vad)   # main.py:129
mixer.level_changed.connect(self._on_level)                                          # main.py:133
mic_cap  = CaptureThread(settings.mic_device_index,  mixer.push_mic,  loopback=False) # main.py:135
loop_cap = CaptureThread(settings.loopback_device_index, mixer.push_loopback, loopback=True) # main.py:138
# 펌프 스레드: chunk = mixer.read_chunk(); if chunk: recorder.write + worker.enqueue   # main.py:159
# 정지: mic_cap.stop(); loop_cap.stop(); pump stop; remainder = mixer.flush()          # main.py:210
```

> **연결 관찰**: `main.py:129`는 `active_sources`를 전달하지 않는다(항상 기본 2). §3 결함 수정 시 이 호출부도
> 함께 검토(마이크/loopback 중 하나만 설정된 세션에서 단일 소스 의도를 믹서에 명시 전달할지 결정).

---

## 3. 구현 순서 (build 슬라이스, 고정)

코어 3파일은 구현 완료 상태이므로, build 단계는 **결함 수정 + 회귀 보강**의 작은 수직 슬라이스로 고정한다.

| 슬라이스 | 내용 | 검증(완료 게이트) |
|----------|------|-------------------|
| **B1** | as-built 회귀 테스트 작성(현 동작 캡처) | 정규화 헬퍼 A3, 청크 경계 A5, 단일 소스 A6, 캡처 생명주기 A7 PASS |
| **B2** | **믹싱 결함 재현 테스트 작성**(feature-spec §6 케이스) | 번갈아 push → 현재 FAIL을 단언으로 고정(red) |
| **B3** | `_drain_into_pending_locked` 단일 소스 폴백 수정 | B2가 GREEN: 출력 총 길이 == 입력 길이, 정렬 구간 합산. 기존 B1 테스트 전부 유지 |
| **B4** | `main.py` 호출부 정합 확인(필요 시 단일 소스 신호 전달) | 마이크 단독/loopback 단독/이중 세 경로 헤드리스 PASS, 배선 단선 없음 |

- B1→B2가 **결함을 테스트로 박제**(Karpathy: 버그 수정 = 재현 테스트 작성 후 통과)하고, B3가 최소 수정으로 통과시킨다.
- B4는 파이프라인 배포 동등성 규칙(production caller까지 정합)을 만족시키는 마무리.
- 공개 시그니처 변경 없음 — 다른 역할(M1/M4) 재작업 0.

### B3 수정 방향(권고, build에서 확정)
단일 소스 폴백을 **시간 기준 holdoff**로 게이트한다: 상대 버퍼가 비어도 일정 latency(예: `FRAMES_PER_BUFFER`
몇 배 분량) 동안은 정렬 overlap만 믹싱하고 나머지는 버퍼에 유지. 그 임계를 넘어 지속적으로 한쪽만 도착할 때만
"단일 소스(항구 부재)"로 판정해 통과시킨다. 또는 캡처가 "이 소스는 비활성"을 명시 신호(플래그)로 전달한다.
어느 쪽이든 `active_sources` dead state를 실제 사용하거나 제거해 정합시킨다(과설계 회피).

---

## 4. 가정 & 미결 결정 (조용히 고르지 않고 드러냄)

- **A1 — 믹서 Qt 의존.** `AudioMixer`는 `qt_compat.QObject`를 상속한다(`level_changed` Signal 때문).
  이는 backend_dev_module_10 scope 문서(§1 "엔진은 PySide6 import 금지")와 어긋나 보이지만, `qt_compat` 셰임이
  헤드리스에서 순수 파이썬 스텁으로 대체하므로 **헤드리스 import·셀프테스트는 보장**된다. as-built를 동결한다(이미
  배선·셀프테스트 통과). 순수 분리가 필요하면 별도 리팩터링 work-item으로 — 본 엔진 범위 밖.
- **A2 — 단일 소스 판정 정책(B3).** holdoff 임계값 vs 캡처 명시 신호 중 택1은 build에서 측정 기반 확정.
  공개 계약에 영향 없음.
- **A3 — 풀레이트 원본 WAV.** 본 엔진은 믹싱 16kHz mono만 발행. 고품질 원본 별도 트랙은 scope §D2의 선택 후속으로
  보류(과설계 회피).

---

## 5. 변경 파일(이 scope task)
- `docs/work-items/audio-engine/feature-spec.md` — 신규(범위·공개 계약 동결).
- `docs/work-items/audio-engine/implementation-design.md` — 신규(본 문서, 내부 설계·구현 순서).
- `docs/change_history.md` — scope 이력 1줄 추가.
- 코드 변경 없음(scope 단계). 코어 3파일은 동결 대상으로 참조만.
