# Backend build 핸드오프 + 믹서 결함 발견 (backend_dev_module_10_build_2)

- **task_id**: backend_dev_module_10_build_2
- **단계**: build
- **역할**: Backend Dev
- **날짜**: 2026-06-13
- **바인딩 계약**: `docs/scope/2026-06-13-runnable-pyside6-stt-app-scope.md` (§3 인터페이스, §2.3 모듈 소유)

---

## 1. 이 task에서 수행한 것 (backend-core 범위)

선행 build 증분이 backend 모듈을 이미 구현해 둔 상태였다. 본 task의 실질 기여:

1. **`app/audio/devices.py`에 `detect_compute_device()` 추가 (M11)**
   - `tuple[str, str]` 반환: CUDA 감지 시 `("cuda","float16")`, 아니면 `("cpu","int8")`.
   - ctranslate2 미설치·CUDA 미가용 등 모든 실패에서 예외 없이 CPU 기본값으로 안전 종료(헤드리스 기동 보장).
   - **배선 복구**: 병행 에이전트가 `app/stt/transcriber.py`를 리팩터링해
     `from ..audio.devices import detect_compute_device`로 소비하도록 바꿔 둔 상태였으나
     `devices.py`에 해당 export가 없어 **`ImportError`로 전사 코어가 단선**되어 있었다.
     이 함수를 추가해 compute device 감지 로직을 `devices.py` 단일 출처(SSOT)로 두고
     전사기가 import해 소비하도록 복구했다(전사기 내부 로컬 `_detect_device` 중복 제거).

2. **헤드리스 검증 수행** (장치/GUI/faster-whisper 없이):

   | 검증 항목 | 결과 |
   |-----------|------|
   | 전 backend 모듈 import (헤드리스) | PASS |
   | `enumerate_devices()` 장치 0개 → 예외 없이 `([],[])` | PASS |
   | `resolve_save_root()` 절대경로 리터럴 없는 Path 반환 | PASS |
   | `WavRecorder` → 16-bit mono 16kHz WAV 기록·헤더 검증 | PASS |
   | `TranscriptWriter` → `.txt`/`.md` flush (타임스탬프 표) | PASS |
   | `RecordingSession.save_json` 직렬화 | PASS |
   | `TranscribeWorker` enqueue→`chunk_ready` 배선(워커 스레드 경유, fake 전사기 주입) | PASS |
   | `transcriber.py` 모듈 import-safe (모델 로드는 faster-whisper 필요) | PASS |
   | 전 모듈 `py_compile` | PASS |

   > 실제 모델 전사(S2 임계 게이트)는 faster-whisper 설치 배포 머신 또는
   > QA 셀프테스트(`tests/selftest_pipeline.py`, M10)에서 검증한다. 헤드리스 CI에서는
   > 위 DSP/I/O/배선 경로가 numpy + qt_compat 스텁만으로 검증된다.

---

## 2. 발견: `app/audio/mixer.py` 믹싱 결함 (M2 오디오 엔진 work-item 핸드오프)

> **범위 주의**: M2 오디오 엔진(`capture.py`/`mixer.py`)은 바인딩 계약 §2.3에서
> **별도 work-item**으로 분리되어 있고(현재 open todos의 "캡처·믹싱 오디오 엔진"),
> 본 backend-core task의 직접 구현 대상이 아니다. 따라서 **코드를 수정하지 않고
> 근거 있는 결함만 인계**한다. M2 소유자가 수정 여부를 판단한다.

### 증상

정상 이중 스트림 사용 패턴(별도 캡처 스레드가 `push_mic`/`push_loopback`을 번갈아
호출)에서 믹서가 두 스트림을 **합성(평균 믹싱)하지 않고 연결(concatenate)** 한다.

### 재현 (실측)

```text
입력: mic 3.0s + loop 3.0s  → 정렬 믹싱 결과는 3.0s(48000 샘플)이어야 함
실제 출력 총 샘플: 96000 (6.00s)        ← 타임라인 2배

한 쌍 push(mic 0.5s @0.5, loop 0.5s @0.5) 후 flush:
  길이=16000 (정렬 믹싱이면 8000)        ← 연결됨
  평균값=0.500 (정렬 믹싱이면 0.5+0.5=1.0 클립) ← 믹싱 안 됨
```

### 원인

`AudioMixer._drain_into_pending_locked()`의 단일 소스 폴백:

```python
n = min(len(self._mic), len(self._loop))
if n == 0:
    # 한쪽만 활성이면 활성 스트림을 그대로 사용
    single = self._mic if len(self._mic) > 0 and len(self._loop) == 0 else None
    ...
```

`push_mic`/`push_loopback`은 서로 다른 시점(다른 스레드)에 호출되므로 `_push` →
`_drain` 시점에 **상대 버퍼가 일시적으로 비어 있는 순간**이 정상적으로 발생한다.
이때 "loopback이 항구적으로 부재(mic_only)"와 "loopback이 잠깐 뒤처짐"을 구분하지
못해, 한쪽을 단일 소스로 간주하고 그대로 flush한다. 결과적으로 mic·loop가 번갈아
단독 flush되어 **믹싱 없이 연결**되고 타임라인이 2배가 되며 음성이 비동기화된다.

architecture.md(line 15/22)의 "두 스트림 평균 믹싱" 서술과 실제 동작이 어긋난다.
`tests/selftest_pipeline.py`가 이를 통과시킨다면, 두 스트림을 한 drain 안에서 lockstep
push하거나 단일 스트림만 구동해 이 타이밍 경로를 건드리지 않기 때문으로 추정된다.

### 제안 (M2 소유자 판단)

- mic_only(loopback 항구 부재)를 **명시 신호**로 처리하고(예: 캡처가 설정하는 플래그,
  또는 일정 latency holdoff 초과 시에만 단일 소스 통과), 그 전까지는 정렬 overlap만
  믹싱하고 나머지는 버퍼에 유지한다. `push_mic`/`push_loopback`/`read_chunk`/
  `level_changed` 공개 시그니처(계약 §3)는 유지 가능하다.
- 회귀 테스트: mic+loop를 **번갈아** push했을 때 출력 총 길이 == 입력 길이, 정렬
  구간 값이 합산됨을 단언(본 문서 §2 재현 케이스).

---

## 3. 변경 파일

- `app/audio/devices.py` — `detect_compute_device()` 추가 (M11, 본 task).
- `docs/change_history.md` — 본 build 이력 추가.
- (인계만, 미수정) `app/audio/mixer.py` — §2 결함은 M2 work-item으로 인계.
