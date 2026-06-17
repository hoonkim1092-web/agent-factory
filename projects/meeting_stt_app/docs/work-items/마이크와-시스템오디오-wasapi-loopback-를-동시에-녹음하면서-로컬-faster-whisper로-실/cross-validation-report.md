# 교차검증 보고서: qa_engineer_module_6 (합성 오디오 헤드리스 셀프테스트)

> 단계: cross_validate
> task_id: qa_engineer_module_6_cross_validate
> 일시: 2026-06-13
> 검증자: qa_engineer_cross_validator
> 선행: scope_1 / build_2 / code_review 모두 completed

---

## 최종 판정: WARN

모듈의 기능 의도(마이크·GUI·네트워크·모델 없이 STT 파이프라인의 헤드리스 검증)는
충족되었고 두 셀프테스트 모두 녹색이다. 다만 scope 문서의 계약과 실제 산출물 사이에
파일명·CLI·종료코드·JSON schema 수준의 괴리가 있으며, 기본 실행 경로에 실제 STT
전사 텍스트 매칭 검증이 없다. 두 사항 모두 문서로 해명된 트레이드오프이므로 BLOCK이
아닌 advisory(WARN)로 판정한다. CLAUDE.md 정책상 WARN은 자동 수정 의무가 없다.

---

## 실측 근거

- `python -m tests.selftest_pipeline` → `5/5 통과`, exit 0
  - S0 전 모듈 import / S1 resolve_save_root / S3 믹서 16kHz mono 청크 /
    S7 컨트롤러 start→stop·SAVED 전이 / S8 산출물(WAV·txt·md·json) 생성·전사 반영
  - S2(실제 faster-whisper)는 `MEETING_STT_RUN_WHISPER=1`일 때만 실행 — 기본 SKIP
- `python scripts/synthetic_audio_headless_selftest.py` → `PASS`, exit 0
  - WAV 컨테이너·채널·샘플폭·샘플레이트·길이·RMS·주파수 검증, JSON 리포트 생성

---

## 검토 항목별 결과

### 1. 모듈 간 인터페이스 일관성 — PASS
`tests/selftest_pipeline.py`가 실제 인터페이스(`AppSettings`, `resolve_save_root`,
`RecordingSession`, `TranscriptChunk`, `AudioMixer(max_chunk_sec, use_vad)`,
`PipelineController.start(transcriber=)`/`chunk_ready`/`mixer`/`state`/`stop()`,
`STATE_SAVED`)를 직접 호출하며 실행이 통과 — 계약 일치 확인.

### 2. 설계 문서와 구현의 괴리 — WARN
- scope 문서(`docs/plans/2026-06-13-synthetic-audio-headless-selftest-scope.md`)는
  `scripts/headless_synthetic_audio_selftest.py`(파일명 어순 다름), `--fixture`/
  `--expected-text`/`--stt-backend` 옵션, 종료코드 0~4, `selftest_result.json`의
  `checks.audio_ready/stt_completed/transcript_non_empty/expected_text_matched`
  schema를 명시했다.
- 실제 산출물 `scripts/synthetic_audio_headless_selftest.py`는 STT를 호출하지 않고
  `--fixture`/`--expected-text`/`--stt-backend`가 없으며 종료코드 0/1/2,
  schema도 `spec/metadata/checks`로 상이하다.
- STT 파이프라인 배선 검증은 별도 파일 `tests/selftest_pipeline.py`(M10 build)로
  전달되었다.
- 완화 요소: `docs/architecture.md`가 두 셀프테스트를 모두 기재하고 역할 분리를
  명시("앱 파이프라인 배선=`tests/selftest_pipeline.py`, scripts=오디오 아티팩트
  스모크")하여 정합성을 회복했다. 즉 scope 계약은 문자 그대로 미충족이나 의도는
  두 파일에 분산 충족.

### 3. 테스트 커버리지 갭 — WARN
- scope가 요구한 "기대 문구와 실제 결과 최소 매칭"(`expected_text_matched`)이
  기본 실행 경로에 없다. scripts 버전은 신호(RMS·주파수) 검증만, pipeline 버전은
  `FakeTranscriber`로 합성 자막을 주입하므로 실제 한국어 전사 텍스트를 검증하지 않는다.
- 실제 whisper 전사(S2)는 기본 SKIP(`MEETING_STT_RUN_WHISPER=1` 게이트).
- 완화 요소: 모델 다운로드·중연산이 CI/헤드리스에 부적합하다는 명시적·문서화된
  트레이드오프이며 환경변수로 활성화 가능. 침묵 누락 아님.

### 4. 의존성 그래프 정합성 — PASS
- `tests/selftest_pipeline.py`는 numpy 사용 → `requirements.txt`에 `numpy>=1.24` 선언됨.
- `scripts/synthetic_audio_headless_selftest.py`는 표준 라이브러리만 사용 → 명시대로 무의존.
- 실행 통과로 import 그래프 정상 확인.

### 5. 문서 업데이트 누락 — PASS(부분 WARN)
- `docs/architecture.md`·`docs/change_history.md` 모두 갱신되어 두 셀프테스트를 반영.
- 잔여: scope 문서가 실제 산출물(파일명·CLI·schema) 대비 stale. 정본
  architecture 문서는 정확하므로 BLOCK 아님.

---

## 후속 권고 (advisory, 차기 작업자용)

1. scope 문서를 실제 산출물에 맞춰 동기화하거나, scope를 "기준 의도"로 두고
   괴리 사유를 scope 하단에 1줄 추가.
2. 실제 STT 텍스트 매칭(`expected_text`)을 옵트인 CI 잡으로 추가해 회귀 안전망 확보
   (모델 캐시 가능한 환경 한정).
