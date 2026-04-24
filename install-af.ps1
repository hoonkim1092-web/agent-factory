<#
.SYNOPSIS
Agent Factory CLI v1.2.22 설치 스크립트

.EXAMPLE
irm https://raw.githubusercontent.com/hoonkim1092-web/af-fsa/af-fsa_v1.2.22/install-af.ps1 | iex
#>

param(
    [string]$InstallPath = "C:\tools",
    [switch]$WithGraphify
)

# 관리자 권한 없으면 자동으로 관리자로 재실행
# (af-critic BLOCK#2 fix + Codex P2/P3 fix 2026-04-23):
#   - -WithGraphify/-InstallPath 스위치를 UAC 재실행 ArgumentList에 동적 전달
#   - InstallPath 작은따옴표 escape (예: C:\hoon's_dir 안전 처리)
#   - try/finally로 임시 스크립트 cleanup 보장
#   - -NoExit 제거 (자식 스크립트 끝에 Read-Host로 이미 대기)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    $extraArgs = if ($WithGraphify) { " -WithGraphify" } else { "" }
    if ($InstallPath -ne "C:\tools") {
        $escapedPath = $InstallPath.Replace("'", "''")
        $extraArgs += " -InstallPath '$escapedPath'"
    }
    $cmdline = "-ExecutionPolicy Bypass -Command `"& { `$tmp = [IO.Path]::GetTempFileName() + '.ps1'; try { irm https://raw.githubusercontent.com/hoonkim1092-web/af-fsa/af-fsa_v1.2.22/install-af.ps1 -OutFile `$tmp; & `$tmp${extraArgs} } finally { Remove-Item `$tmp -ErrorAction SilentlyContinue } }`""
    Start-Process powershell -ArgumentList $cmdline -Verb RunAs
    exit
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Agent Factory CLI v1.2.22 설치" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Step 1: 기존 설치 탐지 및 제거
Write-Host "`n► 기존 설치 확인 중..." -ForegroundColor Yellow

# PATH에서 af.exe 위치 모두 탐색
$oldPaths = @()
$envPaths = ($env:Path + ";" + [Environment]::GetEnvironmentVariable("Path","User") + ";" + [Environment]::GetEnvironmentVariable("Path","Machine")) -split ";" | Select-Object -Unique
foreach ($p in $envPaths) {
    $candidate = Join-Path $p "af.exe"
    if (Test-Path $candidate) {
        $dir = Split-Path $candidate -Parent
        if ($dir -ne "$InstallPath\af") {
            $oldPaths += $dir
        }
    }
}

# 알려진 구버전 설치 경로도 추가 확인
$knownOldPaths = @(
    "$env:LOCALAPPDATA\AgentFactory",
    "$env:LOCALAPPDATA\af",
    "C:\tools\af",
    "C:\af"
)
foreach ($p in $knownOldPaths) {
    if ((Test-Path "$p\af.exe") -and ($p -ne "$InstallPath\af") -and ($oldPaths -notcontains $p)) {
        $oldPaths += $p
    }
}

if ($oldPaths.Count -gt 0) {
    Write-Host "  발견된 기존 설치:" -ForegroundColor Yellow
    foreach ($p in $oldPaths) { Write-Host "    - $p" -ForegroundColor Gray }

    foreach ($p in $oldPaths) {
        try {
            Remove-Item -Path $p -Recurse -Force
            Write-Host "✓ 제거 완료: $p" -ForegroundColor Green
        } catch {
            Write-Host "✗ 제거 실패: $p ($_)" -ForegroundColor Red
        }
    }

    # PATH에서 구버전 경로 제거
    foreach ($scope in @("User", "Machine")) {
        $currentPath = [Environment]::GetEnvironmentVariable("Path", $scope)
        if (-not $currentPath) { continue }
        $newPath = ($currentPath -split ";" | Where-Object { $oldPaths -notcontains $_.TrimEnd("\") }) -join ";"
        if ($newPath -ne $currentPath) {
            [Environment]::SetEnvironmentVariable("Path", $newPath, $scope)
            Write-Host "✓ PATH 정리 완료 ($scope)" -ForegroundColor Green
        }
    }
} else {
    Write-Host "✓ 기존 설치 없음" -ForegroundColor Green
}

# Step 2: 설치 폴더 생성
Write-Host "`n► 설치 폴더 생성 ($InstallPath\af)" -ForegroundColor Yellow
try {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Write-Host "✓ 폴더 생성 완료" -ForegroundColor Green
} catch {
    Write-Host "✗ 폴더 생성 실패: $_" -ForegroundColor Red
    Read-Host "엔터를 눌러 종료"
    exit 1
}

# Step 3: 다운로드
$zipFile = "$InstallPath\af-1.2.22.zip"
Write-Host "`n► af-1.2.22.zip 다운로드 중..." -ForegroundColor Yellow
try {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest `
        -Uri "https://github.com/hoonkim1092-web/af-fsa/raw/af-fsa_v1.2.22/dist/af-1.2.22.zip" `
        -OutFile $zipFile `
        -UseBasicParsing
    $ProgressPreference = 'Continue'

    $sizeMB = [math]::Round((Get-Item $zipFile).Length / 1MB, 1)
    Write-Host "✓ 다운로드 완료 ($sizeMB MB)" -ForegroundColor Green
} catch {
    Write-Host "✗ 다운로드 실패: $_" -ForegroundColor Red
    Read-Host "엔터를 눌러 종료"
    exit 1
}

# Step 4: 압축 해제
Write-Host "`n► 압축 해제 중..." -ForegroundColor Yellow
try {
    Expand-Archive -Path $zipFile -DestinationPath $InstallPath -Force
    Remove-Item $zipFile -Force
    Write-Host "✓ 압축 해제 완료" -ForegroundColor Green
} catch {
    Write-Host "✗ 압축 해제 실패: $_" -ForegroundColor Red
    Read-Host "엔터를 눌러 종료"
    exit 1
}

# Step 5: 설치 확인
$exePath = "$InstallPath\af\af.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "✗ af.exe를 찾을 수 없습니다" -ForegroundColor Red
    Read-Host "엔터를 눌러 종료"
    exit 1
}
Write-Host "✓ af.exe 확인" -ForegroundColor Green

# Step 6: PATH 등록
Write-Host "`n► PATH 등록 중..." -ForegroundColor Yellow
$afPath = "$InstallPath\af"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$afPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$afPath", "User")
    Write-Host "✓ PATH 등록 완료" -ForegroundColor Green
} else {
    Write-Host "✓ 이미 PATH에 등록됨" -ForegroundColor Green
}
# 현재 세션에도 즉시 반영
if ($env:Path -notlike "*$afPath*") {
    $env:Path += ";$afPath"
}

# Step 7: Chrome 설치 확인 (NotebookLM용, 레지스트리 기반)
Write-Host "`n► Chrome 설치 확인 중..." -ForegroundColor Yellow
$chromeKeys = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
)
$chromeFound = $false
foreach ($key in $chromeKeys) {
    try {
        $entry = Get-ItemProperty -Path $key -ErrorAction Stop
        $chromePath = $entry.'(Default)'
        if ($chromePath -and (Test-Path $chromePath)) {
            Write-Host "✓ Chrome 감지됨: $chromePath" -ForegroundColor Green
            $chromeFound = $true
            break
        }
    } catch {}
}
if (-not $chromeFound) {
    Write-Host "! Chrome 미감지 → NotebookLM 로그인 시 수동 브라우저 필요" -ForegroundColor Yellow
    Write-Host "  https://www.google.com/chrome/ 에서 설치하세요." -ForegroundColor Yellow
}

# Step 8: __check-nlm 검증 (nlm 의존성 확인)
Write-Host "`n► NotebookLM CLI (__check-nlm) 검증 중..." -ForegroundColor Yellow
try {
    $nlmCheck = & $exePath "__check-nlm" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ nlm 모듈 로드 정상" -ForegroundColor Green
    } else {
        Write-Host "! __check-nlm 실패 (exit $LASTEXITCODE) → 'af setup' 실행 시 자동 복구 시도" -ForegroundColor Yellow
        if ($nlmCheck) {
            Write-Host "  --- __check-nlm 출력 ---" -ForegroundColor Gray
            $nlmCheck | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
            Write-Host "  ------------------------" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "! __check-nlm 실행 오류: $_" -ForegroundColor Yellow
    Write-Host "  'af setup'으로 진단 가능" -ForegroundColor Yellow
}

# Step 9 (옵션): graphify 외부 도구 설치 (-WithGraphify)
if ($WithGraphify) {
    Write-Host "`n► graphify 외부 도구 설치 (-WithGraphify)..." -ForegroundColor Yellow

    # uv 자동 설치 (없으면)
    $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvCmd) {
        Write-Host "  uv 미설치 → winget으로 설치 시도..." -ForegroundColor Yellow
        try {
            winget install --id=astral-sh.uv -e --accept-source-agreements --accept-package-agreements
            $env:Path = [Environment]::GetEnvironmentVariable("Path","User") + ";" + [Environment]::GetEnvironmentVariable("Path","Machine")
            $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
        } catch {
            Write-Host "! uv 자동 설치 실패: $_" -ForegroundColor Yellow
            Write-Host "  수동 설치: https://docs.astral.sh/uv/" -ForegroundColor Yellow
        }
    }

    if ($uvCmd) {
        try {
            & uv tool install 'graphifyy>=0.4.27,<0.5.0' --python 3.13
            # P1 + af-critic round 3 issue #3 fix:
            # install-af.sh와 대칭으로 uv tool bin 경로를 현재 세션 PATH에 추가.
            # uv tool bin이 실패하면 USERPROFILE\.local\bin로 fallback (sh와 동일).
            # Codex round 4 권장: 멀티라인 출력 시 PATH 오염 방어 (`| Select-Object -First 1`).
            $uvBinDir = (& uv tool bin 2>$null) | Select-Object -First 1
            if (-not $uvBinDir) {
                $uvBinDir = "$env:USERPROFILE\.local\bin"
                Write-Host "  uv tool bin 실패 → fallback: $uvBinDir" -ForegroundColor Gray
            }
            $env:Path = "$uvBinDir;$env:Path"
            Write-Host "  uv tool bin PATH 추가: $uvBinDir" -ForegroundColor Gray
            $graphifyCmd = Get-Command graphify -ErrorAction SilentlyContinue
            if ($graphifyCmd) {
                $gver = & graphify --version 2>&1 | Select-Object -First 1
                Write-Host "✓ graphify 설치 완료: $gver" -ForegroundColor Green
                Write-Host "  PATH 영구 등록 권장: '$uvBinDir' 를 사용자 환경변수 Path에 추가" -ForegroundColor Yellow
            } else {
                Write-Host "! graphify CLI 미감지 → PATH 확인 필요 (예상: $uvBinDir)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "! graphifyy 설치 실패: $_" -ForegroundColor Yellow
            Write-Host "  수동 실행: uv tool install 'graphifyy>=0.4.27,<0.5.0' --python 3.13" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  설치 완료! v1.2.22" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  PowerShell을 재시작한 후:" -ForegroundColor White
Write-Host "  af --help" -ForegroundColor Yellow
Write-Host ""
Write-Host "  또는 즉시 실행:"
Write-Host "  & '$exePath' --help" -ForegroundColor Yellow
if (-not $WithGraphify) {
    Write-Host ""
    Write-Host "  graphify 외부 도구도 설치하려면:" -ForegroundColor White
    Write-Host "  irm <url>/install-af.ps1 | iex; install-af.ps1 -WithGraphify" -ForegroundColor Yellow
}
Write-Host ""
Read-Host "엔터를 눌러 종료"
