@echo off
echo [setup-dev] Agent Factory 개발 환경 설정
echo.

:: 1. Git hooks 경로 설정
git config core.hooksPath .githooks
if errorlevel 1 (
    echo [FAIL] git config core.hooksPath 설정 실패
    exit /b 1
)
echo [OK] core.hooksPath = .githooks

:: 2. 설정 확인
echo.
echo === 현재 Git hooks 설정 ===
git config --get core.hooksPath
echo.
echo [setup-dev] 완료. 이제 .githooks/ 의 pre-commit, post-merge 등이 동작합니다.
