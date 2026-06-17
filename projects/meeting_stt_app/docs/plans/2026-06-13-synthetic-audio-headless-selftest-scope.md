# 합성 오디오 헤드리스 셀프테스트 범위

## 목적

합성 오디오 헤드리스 셀프테스트는 실제 마이크, GUI 조작, 외부 회의 앱 없이 회의 STT 파이프라인의 최소 동작 가능성을 검증하는 QA 스크립트다. 이 단계에서는 구현을 시작하지 않고, 스크립트가 책임질 범위와 호출 인터페이스, 의존성, 산출물, 구현 순서를 고정한다.

## 범위

포함 범위:

- 합성 오디오 파일을 생성하거나 고정 fixture에서 로드한다.
- 헤드리스 모드로 STT 처리 경로를 실행한다.
- 생성된 transcript 또는 segment 결과가 비어 있지 않은지 검증한다.
- 기대 문구와 실제 결과의 최소 매칭 기준을 검증한다.
- 실행 로그, 결과 JSON, 실패 원인 요약을 산출한다.
- CI와 로컬에서 동일한 명령으로 실행 가능해야 한다.

제외 범위:

- 실제 마이크 입력 검증.
- GUI 자동화 검증.
- 회의 앱 연결 검증.
- 장시간 성능 벤치마크.
- 모델 정확도 평가용 대규모 음성 평가.
- 네트워크 의존 STT 제공자의 품질 비교.

## 스크립트 인터페이스

권장 진입점:

```powershell
python scripts/headless_synthetic_audio_selftest.py --output-dir artifacts/selftest --fixture synthetic_ko_short
```

필수 옵션:

- `--output-dir`: 테스트 산출물을 저장할 디렉터리.
- `--fixture`: 사용할 합성 오디오 fixture 이름.

선택 옵션:

- `--stt-backend`: 사용할 STT 백엔드 식별자. 기본값은 프로젝트 기본 로컬 또는 테스트 백엔드.
- `--sample-rate`: 합성 오디오 sample rate. 기본값은 `16000`.
- `--duration-sec`: 합성 오디오 길이. 기본값은 fixture 정의를 따른다.
- `--expected-text`: transcript에 포함되어야 하는 최소 기대 문구.
- `--timeout-sec`: 전체 실행 제한 시간.
- `--keep-audio`: 생성된 wav 파일 보존 여부.
- `--json`: 콘솔 요약을 JSON으로 출력한다.

종료 코드:

- `0`: 셀프테스트 통과.
- `1`: 입력, 설정, fixture 오류.
- `2`: STT 실행 실패.
- `3`: 결과 검증 실패.
- `4`: timeout.

## 의존성

런타임 의존성:

- Python 실행 환경.
- 프로젝트의 STT 처리 모듈.
- WAV 파일 생성 또는 로드 기능.
- 로컬 테스트에서 사용 가능한 STT backend 또는 mock backend.

테스트 데이터 의존성:

- 짧은 한국어 합성 오디오 fixture 1개 이상.
- fixture별 기대 문구 metadata.
- sample rate, channel count, duration metadata.

환경 의존성:

- GUI display 불필요.
- 마이크 장치 불필요.
- 기본 모드는 네트워크 불필요.
- 네트워크 STT backend는 명시적으로 선택한 경우에만 허용한다.

## 산출물

`--output-dir` 아래에 다음 파일을 남긴다.

- `selftest_result.json`: 실행 설정, 경과 시간, 통과 여부, 실패 단계, transcript 요약.
- `selftest.log`: 실행 로그.
- `synthetic.wav`: `--keep-audio`가 켜진 경우 생성 또는 사용한 wav 파일.
- `transcript.txt`: 최종 transcript 텍스트.

`selftest_result.json` 최소 schema:

```json
{
  "ok": true,
  "fixture": "synthetic_ko_short",
  "stt_backend": "local_test",
  "audio": {
    "sample_rate": 16000,
    "channels": 1,
    "duration_sec": 3.0
  },
  "checks": {
    "audio_ready": true,
    "stt_completed": true,
    "transcript_non_empty": true,
    "expected_text_matched": true
  },
  "transcript": {
    "text": "..."
  },
  "error": null
}
```

## 구현 순서

1. fixture metadata와 결과 JSON schema를 먼저 추가한다.
   검증: fixture 이름으로 기대 문구와 오디오 속성을 조회할 수 있다.

2. 합성 wav 생성 또는 fixture 로드 유틸리티를 추가한다.
   검증: 헤드리스 환경에서 wav 파일이 생성되고 metadata와 일치한다.

3. STT backend adapter 호출부를 연결한다.
   검증: mock 또는 local test backend로 transcript가 반환된다.

4. 결과 검증 로직과 종료 코드를 구현한다.
   검증: 정상 케이스는 `0`, 빈 transcript는 `3`을 반환한다.

5. 산출물 저장과 콘솔 요약을 구현한다.
   검증: `selftest_result.json`, `selftest.log`, `transcript.txt`가 생성된다.

6. CI 또는 QA 명령 문서에 단일 실행 명령을 추가한다.
   검증: 로컬 headless 실행 명령과 CI 실행 명령이 동일하다.

## 영향 범위

직접 영향:

- `scripts/headless_synthetic_audio_selftest.py`
- 합성 오디오 fixture 또는 metadata 파일
- QA 문서와 실행 절차

간접 영향:

- STT backend adapter의 테스트 가능성
- CI에서 GUI와 마이크 없이 수행하는 smoke test

## 대안

대안 1: 실제 녹음 파일 fixture만 사용한다.
판단: 재현성은 높지만 fixture 저작권과 저장 용량 문제가 생길 수 있어 기본안에서 제외한다.

대안 2: STT backend를 완전히 mock 처리한다.
판단: 파이프라인 배선 검증에는 유용하지만 실제 오디오 처리 회귀를 놓칠 수 있어 기본 backend는 local test backend로 둔다.

대안 3: GUI 자동화까지 포함한다.
판단: 이 작업의 목표인 헤드리스 셀프테스트 범위를 벗어나므로 제외한다.
