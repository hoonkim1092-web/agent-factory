# Code Review — backend_dev_module_10 (build 산출물)

- **task_id**: backend_dev_module_10_code_review
- **단계**: code_review
- **리뷰어**: backend_dev_code_reviewer
- **날짜**: 2026-06-13
- **대상**: Backend Dev 소유 모듈 9종 (`app/config.py`, `app/io/session.py`,
  `app/io/recorder.py`, `app/io/transcript_writer.py`, `app/audio/devices.py`,
  `app/audio/mixer.py`, `app/audio/capture.py`, `app/stt/types.py`, `app/stt/transcriber.py`)
- **바인딩 계약**: `docs/plans/2026-06-13-backend-dev-scope-and-interfaces.md`,
  `docs/plans/2026-06-13-backend-build-handoff-and-mixer-finding.md`
- **판정**: **BLOCK**

---

## 요약

이번 build의 직접 기여(`detect_compute_device()` 추가 + 전사기 SSOT 배선 복구)는
깔끔하고 정확하다. 그러나 리뷰 대상인 backend 모듈 집합에 **확인된 기능 결함**이
포함되어 있다: `app/audio/mixer.py`가 정상 이중 스트림 경로에서 두 스트림을
**믹싱하지 않고 연결(concatenate)** 한다. 핸드오프 문서가 이를 발견·인계했으나
코드는 수정되지 않았고, 결함을 막으려던 `active_sources` 파라미터는 **죽은
파라미터**(설정만 되고 한 번도 읽히지 않음)로 남아 있다. 이는 완료 기준
("두 스트림 평균 믹싱")과 `architecture.md` 서술을 위반하므로 BLOCK로 판정한다.

---

## 보안 (OWASP/인젝션/인증)

- 네트워크 서버 없음, 외부 입력은 로컬 오디오 장치·설정 JSON뿐. 인젝션 표면 없음.
- `transcript_writer.py`가 md 출력에서 `|`를 `\|`로 이스케이프 → 표 깨짐/주입 방지. 양호.
- `config.AppSettings.load()`가 손상 JSON을 `(OSError, ValueError)`로 흡수하고 알려진
  키만 채택 → 견고. 양호.
- 절대경로 하드코딩 없음: `resolve_save_root()`·`_config_path()` 모두 `Path.home()`
  기반 파생. CLAUDE.md 규칙 준수.
- **보안 이슈 없음.**

---

## 발견 사항

### [BLOCK] B1 — `AudioMixer`가 이중 스트림을 믹싱하지 않고 연결한다 (`app/audio/mixer.py:114-131`)

**실체(실측 재현):**

```text
정상 경로: 두 CaptureThread가 서로 다른 시점에 독립적으로 push
  m.push_mic(0.5s@0.5)   # 이 순간 loop 버퍼 비어 있음
  m.push_loopback(0.5s@0.5)  # 이 순간 mic 버퍼는 이미 drain됨
  flush() → output_len = 16000  (정렬 믹싱이면 8000)   ← 타임라인 2배
            mean       = 0.5    (정렬 믹싱이면 1.0 클립) ← 믹싱 안 됨
```

**원인:** `_drain_into_pending_locked()`는 `push`마다 즉시 호출되는데, 한쪽 버퍼가
비어 있으면(`n == 0`) 다른 쪽을 **단일 소스로 간주해 그대로 flush**한다(line 117-126).
`push_mic`/`push_loopback`은 서로 다른 스레드에서 다른 시점에 호출되므로(`main.py:135-142`
두 독립 `CaptureThread`), "상대가 잠깐 뒤처짐"과 "상대가 항구 부재(mic_only)"를
구분하지 못한다. 결과적으로 mic·loop가 번갈아 단독 flush되어 믹싱 없이 연결되고,
오디오가 비동기화되며 저장 WAV·전사 타임라인이 2배가 된다.

**증거 — 죽은 파라미터:** 생성자가 `active_sources`(기본 2)를 받아
`self._active_sources`(line 88)에 저장하지만 **drain 로직 어디서도 읽지 않는다**
(`grep _active_sources` → 할당 1곳뿐). line 86-87 주석은 "이중 소스에서는 정렬
가능한 만큼만 믹싱하고 나머지는 파트너 도착까지 버퍼에 유지"라고 명시하지만 코드는
그 분기를 구현하지 않았다 — 의도된 가드가 미배선 상태로 남았다. 게다가 `main.py:129`은
`active_sources`를 아예 전달하지 않아, 설령 읽혔어도 기본값 2로만 동작했을 것이다.

**영향:** 완료 기준 "두 스트림 평균 믹싱" 및 `docs/architecture.md`(line 15/22) 서술
위반. 마이크+시스템오디오 동시 녹음이라는 앱 핵심 가치가 깨진다.

**수정 방향(계약 시그니처 유지 가능):** 이중 소스 모드(`_active_sources >= 2`)에서는
`n == 0`일 때 단일 소스를 통과시키지 말고 파트너 도착까지 버퍼에 유지한다. 단일 소스
폴백은 `_active_sources == 1`(또는 capture의 `mic_only` 명시 신호 / latency holdoff
초과)일 때만 적용한다. `flush()`에서만 잔여 단일 버퍼를 비운다. 회귀 테스트: mic+loop를
**번갈아** push했을 때 출력 총 길이 == 입력 길이, 정렬 구간 값이 합산됨을 단언.

> 핸드오프(§2)는 이 결함을 정확히 발견해 M2 work-item 소유자에게 인계했고, 코드를
> 건드리지 않은 것은 절차상 타당하다. 다만 **리뷰 대상 산출물 집합에 결함이 남아 있는
> 상태**이므로 게이트 판정은 BLOCK이다. 수정 주체가 M2 owner든 backend든, merge 전
> 해소가 필요하다.

### [WARN] B2 — 믹서의 샘플 단위 Python 박싱 (`app/audio/mixer.py:110, 124, 128-129`)

`deque[float]`에 `arr.tolist()`로 모든 샘플을 Python float로 박싱해 넣고, drain 시
`np.fromiter((deque.popleft() ...))`로 다시 꺼낸다. 16kHz mono라 당장은 견딜 수 있으나
실시간 오디오 경로에서 샘플당 Python 객체 생성/해제는 불필요한 O(n) 오버헤드다.
numpy 버퍼 연결(예: `np.concatenate` 누적 + 인덱스 커서)로 바꾸면 박싱이 사라진다.
advisory — B1 수정 시 자료구조를 함께 정리하면 자연 해소된다.

### [WARN] B3 — scope 계약과 구현 시그니처 불일치 (문서 정합성)

scope 문서(§3)는 `StreamMixer.push_mic(frames, src_rate, channels)` / `pull()`,
`WhisperEngine`+`RollingChunker`, `WavRecorder(wav_path).append()`,
`TranscriptWriter(txt,md).write_chunk()/finalize()`, `RecordingSession`(Optional
필드 + `chunks` 리스트), `session.py`의 `default_save_root/session_dir/new_session_id`를
명시했다. 실제 구현은 `AudioMixer.push_mic(frames)`/`read_chunk()`, `Transcriber`,
`WavRecorder().open()/write()`, `TranscriptWriter().append()/flush()`,
`RecordingSession`(전 필드 필수 str, `chunks` 없음), 저장경로는 `config.resolve_save_root()`로
구현되어 **이름·시그니처가 다르다**. 내부 호출부(`main.py`)는 실제 구현과 정합하므로
런타임 버그는 아니지만, scope 문서가 "frozen" 계약이라고 선언한 것과 어긋난다.
구현이 더 단순·일관적이므로 **scope 문서를 실제 구현에 맞춰 갱신**하거나, 차이를
명시적으로 기록할 것을 권고한다(advisory).

---

## 양호 항목 (이번 build 직접 기여)

- **`detect_compute_device()` (`devices.py:25-46`)**: ctranslate2 미설치·CUDA 미가용 등
  모든 실패를 흡수해 `("cpu","int8")`로 안전 종료. 헤드리스 기동 보장. SSOT로 적절히 배치.
- **전사기 배선 복구 (`transcriber.py:15,30`)**: 로컬 `_detect_device` 중복 제거 후
  `devices.detect_compute_device()` 단일 출처 소비 — 타입/로직 SSOT 규칙 정합.
- **import-safe 설계**: `faster_whisper`/`pyaudiowpatch`/`ctranslate2` 무거운 import를
  모두 함수/`__init__` 시점 lazy + try-guard. 헤드리스 CI에서 전 모듈 import·py_compile PASS(실측).
- **`enumerate_devices()` (`devices.py:49-95`)**: 단계별 예외를 빠짐없이 흡수, `finally`에서
  PyAudio terminate. 장치 0개/미설치에서 `([],[])` 예외 없이 반환.
- **`recorder.py`/`transcript_writer.py`**: clip→int16 변환, md 이스케이프, 부모 디렉터리
  생성 등 엣지 처리 견고.

---

## 검증 수행

- 전 backend 모듈 `py_compile` → PASS (실측).
- 믹서 결함 재현 스크립트 실행 → output_len=16000/mean=0.5로 연결 동작 확인(실측).
- `grep _active_sources` → 할당 1곳, 참조 0곳(죽은 파라미터 확인).
- `resolve_save_root`/`_config_path` 절대경로 리터럴 부재 확인.

---

## 판정

**BLOCK** — B1(이중 스트림 믹싱 결함 + 죽은 가드 파라미터)이 앱 핵심 완료 기준을 깨고
실측으로 재현되므로 merge 전 해소가 필요하다. B2·B3는 advisory(WARN)로, B1 수정과 함께
정리하면 자연 해소된다. 이번 build의 직접 기여(detect_compute_device + SSOT 배선)는
독립적으로 양호하다.
