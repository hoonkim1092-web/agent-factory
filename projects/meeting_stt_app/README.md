# 회의록 STT 데스크톱 앱 (Meeting STT)

마이크와 시스템오디오(WASAPI loopback)를 **동시에** 녹음하면서 로컬
faster-whisper로 **실시간 한국어 자막**을 출력하고, 종료 시 원본 WAV·전사
텍스트(.txt/.md)·세션 메타데이터(JSON)를 `meetings/<session_id>/`에 자동
저장하는 **PySide6 Windows 데스크톱 앱**.

> 클라우드 STT가 아니라 **로컬 추론**이다. 인터넷 없이 동작하며(모델 최초
> 다운로드 제외) 회의 음성이 외부로 나가지 않는다.

---

## 주요 기능
- 마이크 + 시스템오디오 동시 캡처 후 16kHz mono로 믹싱
- faster-whisper 로컬 전사(CUDA 자동 감지, 미감지 시 CPU int8)
- 실시간 자막 패널, 장치/모델/언어 선택, 경과 타이머, 입력 레벨 미터
- 정지 시 `recording.wav` · `transcript.txt` · `transcript.md` · `session.json` 자동 저장
- UI 비블로킹: 전사는 전용 워커 스레드(QThread)에서 수행

## 요구 사항
- **Windows 10/11** (WASAPI loopback 전용 — macOS/Linux 미지원)
- Python 3.10+ (개발/소스 실행 시)
- (선택) NVIDIA GPU + CUDA — 없으면 CPU로 동작

## 설치 (소스 실행)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 실행
```powershell
python -m app.main
```
1. **마이크**와 **시스템오디오** 장치를 드롭다운에서 선택한다.
2. **모델**(tiny/base/small/medium)과 **언어**(한국어/자동)를 고른다.
3. **녹음 시작** → 실시간 자막이 패널에 출력된다.
4. **정지 및 저장** → 산출물이 `meetings/<session_id>/`에 저장된다.

> 모델 최초 사용 시 가중치가 자동 다운로드된다(이후 캐시).

### 시스템오디오(loopback) 주의
- 시스템오디오 캡처는 **WASAPI loopback** 장치를 사용한다. 드롭다운의
  `[Loopback]` 표기 장치(스피커/헤드폰의 loopback)를 선택해야 상대방 목소리
  (회의 상대 출력)가 녹음된다.
- 출력 장치를 음소거하면 loopback 캡처도 무음이 된다. 회의 중에는 음소거를
  해제한다.

## 저장 경로
- 기본: `<사용자 문서>/meetings/<session_id>/` (문서 폴더 없으면 홈 하위).
- 설정에서 `save_root`를 지정하면 그 경로 하위에 저장된다.
- 설정 파일: `<홈>/.meeting_stt_app/settings.json`

## 헤드리스 셀프테스트
오디오 장치·PySide6·faster-whisper 없이도 파이프라인 배선을 검증한다.
```powershell
python -m tests.selftest_pipeline
```
실제 faster-whisper 전사까지 확인하려면:
```powershell
$env:MEETING_STT_RUN_WHISPER=1; python -m tests.selftest_pipeline
```

## 배포 빌드 (PyInstaller onedir)
```powershell
python build.py
# 또는 직접:
pyinstaller meeting_stt.spec
```
- 산출: `dist/MeetingSTT/MeetingSTT.exe`
- 스펙은 ctranslate2 네이티브 DLL(`binaries`), faster-whisper 데이터(`datas`),
  동적 import 모듈(`hiddenimports`)을 번들에 포함한다.
- CUDA 빌드 시 ctranslate2용 cuBLAS/cuDNN DLL이 추가로 필요할 수 있다.

## 아키텍처
- 설계·인터페이스 계약: `docs/architecture.md`,
  `docs/scope/2026-06-13-runnable-pyside6-stt-app-scope.md`
- 데이터 흐름: 캡처 스레드 → `AudioMixer`(16kHz mono 믹싱) →
  `[WavRecorder]` + `[청크 펌프 → TranscribeWorker(QThread, faster-whisper)]`
  → `chunk_ready` → 자막 패널 + `TranscriptWriter`
- 모듈 구조:
  - `app/main.py` — 앱 셸 + 통합 배선 + 상태 머신(`PipelineController`)
  - `app/audio/` — `devices.py`(열거) · `capture.py`(캡처) · `mixer.py`(믹싱)
  - `app/stt/` — `types.py`(SSOT) · `transcriber.py` · `worker.py`
  - `app/io/` — `recorder.py` · `transcript_writer.py` · `session.py`(SSOT)
  - `app/ui/` — `main_window.py` · `widgets.py`
  - `app/config.py` — `AppSettings`(SSOT) · `resolve_save_root`

## 제약
- Windows WASAPI 전용. 화자 분리·요약·번역은 범위 밖.
- 저장 경로 절대경로 하드코딩 금지(`meetings/` 상대 기반).
