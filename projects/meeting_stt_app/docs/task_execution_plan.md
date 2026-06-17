# Task Execution Plan

## Overview
- project_goal: 마이크와 시스템오디오(WASAPI loopback)를 동시에 녹음하면서 로컬 faster-whisper로 실시간 한국어 자막을 출력하고 종료 시 WAV와 전사 텍스트를 자동 저장하는 PySide6 Windows 데스크톱 앱을 만든다.
- execution_strategy: parallel
- role_count: 3
- module_count: 10
- task_count: 30

## Evidence
- Workspace note: existing_todo=.todo.md
- Workspace note: existing_project_board=project_board_state.json
- Workspace note: existing_work_items=3
- Local reference: docs/work-items/마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시/feature-spec.md -> ### FR-5. STT 엔진 구성 - CUDA 감지 시 `device=cuda`/`compute_type=float16`, 없으면 CPU `int8`로 모델을 로드한다. - 모델 크기는 tiny/base/small/medium 중 선택 가능하며 기본값은 `small`이다.
- Local reference: docs/work-items/마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시/feature-spec.md -> ### FR-7. WAV + 전사 영속화 (`wav_and_transcript_persistence`) - 정지 시 원본 녹음 WAV(`meetings/<session>/...wav`)와 전사 텍스트(`.txt` 및/또는 `.md`)를 자동 저장한다.
- Local reference: docs/work-items/마이크와-시스템오디오-wasapi-loopback-를-동시-녹음하면서-로컬-faster-whisper로-실시/feature-spec.md -> ### FR-6. UI 레이어 (`pyside6_gui_development`) - 녹음 시작/정지 버튼, 마이크·시스템출력 장치 선택 드롭다운, 모델 크기 선택, 언어 선택, 실시간 자막 패널(청크 단위 append), 녹음 타이머, 오디오 레벨 미터, 저장 경로 표시를 제공한다.

## Stage Order
1. 범위와 계약 정의
   objective: 기능 경계를 모듈 단위로 나누고 역할별 인터페이스를 고정한다.
   exit_criteria: 모든 작업이 owner_role과 depends_on을 가진다., 핵심 산출물이 모듈별로 정리된다.
2. 기능 슬라이스 구현
   objective: 독립 배포 가능한 작은 기능 단위로 구현을 진행한다.
   exit_criteria: 각 모듈이 최소 1개의 구현 작업을 가진다., 기능 슬라이스가 파일/산출물 기준으로 분리된다.
3. 통합과 핸드오프
   objective: 역할 간 의존성을 정리하고 결과를 다음 작업자가 이어받을 수 있게 만든다.
   exit_criteria: 의존 작업이 정리되고 handoff 기준이 명시된다., 검증 전에 필요한 연결 작업이 완료된다.
4. 검증과 마감
   objective: 기능 동작, 회귀 리스크, 남은 이슈를 명시적으로 검증한다.
   exit_criteria: 검증 작업이 존재한다., 잔여 리스크와 후속 작업이 기록된다.

## Module Breakdown By Role
### 실행 가능한 PySide6 회의록 STT 데스크톱 앱
- owner_role: Frontend Dev
- objective: 실행 가능한 PySide6 회의록 STT 데스크톱 앱을(를) 구현한다.
- feature_slices: 실행 가능한 PySide6 회의록 STT 데스크톱 앱을(를) 구현한다.
- deliverables: 실행 가능한 PySide6 회의록 STT 데스크톱 앱
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 실행 가능한 PySide6 회의록 STT 데스크톱 앱 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 실행 가능한 PySide6 회의록 STT 데스크톱 앱 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 실행 가능한 PySide6 회의록 STT 데스크톱 앱을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 실행 가능한 PySide6 회의록 STT 데스크톱 앱의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 실행 가능한 PySide6 회의록 STT 데스크톱 앱 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진
- owner_role: Frontend Dev
- objective: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진을(를) 구현한다.
- feature_slices: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진을(를) 구현한다.
- deliverables: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 마이크+시스템오디오 동시 캡처·믹싱 오디오 엔진 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### faster-whisper 실시간 청크 전사 워커
- owner_role: Frontend Dev
- objective: faster-whisper 실시간 청크 전사 워커을(를) 구현한다.
- feature_slices: faster-whisper 실시간 청크 전사 워커을(를) 구현한다.
- deliverables: faster-whisper 실시간 청크 전사 워커
- depends_on: -
- tasks:
  - [scope] Frontend Dev: faster-whisper 실시간 청크 전사 워커 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: faster-whisper 실시간 청크 전사 워커 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: faster-whisper 실시간 청크 전사 워커을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: faster-whisper 실시간 청크 전사 워커의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: faster-whisper 실시간 청크 전사 워커 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### 실시간 자막 패널·장치 선택·레벨 미터 UI
- owner_role: Frontend Dev
- objective: 실시간 자막 패널·장치 선택·레벨 미터 UI을(를) 구현한다.
- feature_slices: 실시간 자막 패널·장치 선택·레벨 미터 UI을(를) 구현한다.
- deliverables: 실시간 자막 패널·장치 선택·레벨 미터 UI
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 실시간 자막 패널·장치 선택·레벨 미터 UI 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 실시간 자막 패널·장치 선택·레벨 미터 UI 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 실시간 자막 패널·장치 선택·레벨 미터 UI을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 실시간 자막 패널·장치 선택·레벨 미터 UI의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 실시간 자막 패널·장치 선택·레벨 미터 UI 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### WAV + 전사 텍스트 + 세션 메타데이터 영속화 모듈
- owner_role: Frontend Dev
- objective: WAV + 전사 텍스트(.txt/.md) + 세션 메타데이터 영속화 모듈을(를) 구현한다.
- feature_slices: WAV + 전사 텍스트(.txt/.md) + 세션 메타데이터 영속화 모듈을(를) 구현한다.
- deliverables: WAV + 전사 텍스트(.txt/.md) + 세션 메타데이터 영속화 모듈
- depends_on: -
- tasks:
  - [scope] Frontend Dev: WAV + 전사 텍스트 + 세션 메타데이터 영속화 모듈 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: WAV + 전사 텍스트 + 세션 메타데이터 영속화 모듈 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: WAV + 전사 텍스트(.txt/.md) + 세션 메타데이터 영속화 모듈을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: WAV + 전사 텍스트 + 세션 메타데이터 영속화 모듈의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: WAV + 전사 텍스트 + 세션 메타데이터 영속화 모듈 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### 합성 오디오 헤드리스 셀프테스트 스크립트
- owner_role: QA Engineer
- objective: 합성 오디오 헤드리스 셀프테스트 스크립트을(를) 구현한다.
- feature_slices: 합성 오디오 헤드리스 셀프테스트 스크립트을(를) 구현한다.
- deliverables: 합성 오디오 헤드리스 셀프테스트 스크립트
- depends_on: -
- tasks:
  - [scope] QA Engineer: 합성 오디오 헤드리스 셀프테스트 스크립트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 합성 오디오 헤드리스 셀프테스트 스크립트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] QA Engineer: 합성 오디오 헤드리스 셀프테스트 스크립트을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 합성 오디오 헤드리스 셀프테스트 스크립트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] QA Engineer: 합성 오디오 헤드리스 셀프테스트 스크립트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### requirements.txt 의존성 명세
- owner_role: Frontend Dev
- objective: requirements.txt 의존성 명세을(를) 구현한다.
- feature_slices: requirements.txt 의존성 명세을(를) 구현한다.
- deliverables: requirements.txt 의존성 명세
- depends_on: -
- tasks:
  - [scope] Frontend Dev: requirements.txt 의존성 명세 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: requirements.txt 의존성 명세 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: requirements.txt 의존성 명세을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: requirements.txt 의존성 명세의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: requirements.txt 의존성 명세 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### 스크립트
- owner_role: Frontend Dev
- objective: PyInstaller onedir 빌드 스펙/스크립트을(를) 구현한다.
- feature_slices: PyInstaller onedir 빌드 스펙/스크립트을(를) 구현한다.
- deliverables: PyInstaller onedir 빌드 스펙/스크립트
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 스크립트 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 스크립트 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: PyInstaller onedir 빌드 스펙/스크립트을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 스크립트의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 스크립트 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### 설치·실행·시스템오디오 캡처 주의사항 README
- owner_role: Frontend Dev
- objective: 설치·실행·시스템오디오 캡처 주의사항 README을(를) 구현한다.
- feature_slices: 설치·실행·시스템오디오 캡처 주의사항 README을(를) 구현한다.
- deliverables: 설치·실행·시스템오디오 캡처 주의사항 README
- depends_on: -
- tasks:
  - [scope] Frontend Dev: 설치·실행·시스템오디오 캡처 주의사항 README 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: 설치·실행·시스템오디오 캡처 주의사항 README 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Frontend Dev: 설치·실행·시스템오디오 캡처 주의사항 README을(를) 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: 설치·실행·시스템오디오 캡처 주의사항 README의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Frontend Dev: 설치·실행·시스템오디오 캡처 주의사항 README 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

### Backend Dev 구현
- owner_role: Backend Dev
- objective: 서버, 데이터, 외부 연동 레이어를 구현한다.
- feature_slices: 서버, 데이터, 외부 연동 레이어를 구현한다.
- deliverables: 실행 가능한 PySide6 회의록 STT 데스크톱 앱
- depends_on: -
- tasks:
  - [scope] Backend Dev: Backend Dev 구현 범위와 인터페이스를 정의하고 구현 순서를 고정한다.
    acceptance: Backend Dev 구현 범위가 명확히 정리된다., 의존성과 산출물이 명시된다.
  - [build] Backend Dev: 서버, 데이터, 외부 연동 레이어를 구현한다. 기능을 작은 슬라이스로 나눠 구현한다.
    acceptance: Backend Dev 구현의 핵심 기능이 구현된다., 관련 파일과 산출물이 갱신된다.
  - [verify] Backend Dev: Backend Dev 구현 결과를 검증하고 다음 작업자가 이어받을 handoff 메모를 남긴다.
    acceptance: 검증 결과가 정리된다., 잔여 리스크와 후속 작업이 기록된다., 검증 초점: 모듈 import가 오류 없이 성공하는지 (헤드리스 기동), 검증 초점: 오디오 장치 enumerate가 예외 없이 동작하는지, 검증 초점: 합성 사인파/샘플 WAV가 STT 파이프라인을 1회 통과해 전사 텍스트를 반환하는지, 검증 초점: 녹음 시작→청크 전사→정지→WAV+전사 파일 저장 흐름이 코드상 end-to-end 연결되어 있는지, 검증 초점: 저장 경로에 절대경로 하드코딩이 없는지 (meetings/ 상대 경로 사용), 검증 초점: PyInstaller 스펙이 ctranslate2 DLL·모델을 포함하도록 구성되어 있는지

## Execution Rules
- Each task should finish as a small, independent slice of work.
- Resolve dependencies using `depends_on` before parallelizing the next step.
- Define scope and file boundaries before implementation begins.
- Keep verification work as separate tasks instead of burying it inside build tasks.

## Handoff Rules
- Agents should communicate using task_id-scoped handoff, blocker, decision_request, decision_response, review_request, review_result, and result messages.
- Include relevant file paths and acceptance criteria in each handoff or review request.
- Every blocker should state what is blocked, why, and what decision or input is required.
- Each receiving agent should check the inbox and acknowledge required messages before starting work.
