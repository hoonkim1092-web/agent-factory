#!/usr/bin/env bash
# ============================================================================
# Agent Factory CLI v1.2.19 — macOS/Linux 설치 스크립트
#
# 사용법:
#   curl -fsSL https://raw.githubusercontent.com/hoonkim1092-web/af-fsa/af-fsa_v1.2.19/install-af.sh | bash
#
# 설치 위치:
#   소스 트리 : $HOME/.local/share/af
#   런처      : $HOME/.local/bin/af
#   venv      : $HOME/.local/share/af/.venv
#
# 안전성(BLOCK-3 대응):
#   신규 트리는 ${INSTALL_ROOT}.new 에 먼저 전개·검증하고, 성공 시에만
#   기존 설치를 백업 후 mv로 원자적 교체. 실패하면 기존 설치가 그대로 유지됨.
#
# 기존 `.af_setup_state.json`이 schema_version 1이면 로드 시 자동 마이그레이션됨
# (별도 처리 불필요 — core/setup_wizard.py::_load_setup_state에서 처리).
# ============================================================================
set -euo pipefail

AF_VERSION="1.2.19"
AF_TAG="af-fsa_v${AF_VERSION}"
# GitHub tag tarball root는 `<repo>-<tag>/` 형식.
# 본 저장소(af-fsa) + 태그(af-fsa_v1.2.19) → 루트 디렉터리: `af-fsa-af-fsa_v1.2.19/`
# 따라서 `tar --strip-components=1`로 해당 한 겹을 벗겨낸다.
# (v1.2.18 공개 tarball에서 실증 완료 — af-cross-review Q2)
AF_REPO_ZIP="https://github.com/hoonkim1092-web/af-fsa/archive/refs/tags/${AF_TAG}.tar.gz"

INSTALL_ROOT="${AF_INSTALL_ROOT:-$HOME/.local/share/af}"
BIN_DIR="${AF_BIN_DIR:-$HOME/.local/bin}"
STAGING_ROOT="${INSTALL_ROOT}.new"
BACKUP_ROOT="${INSTALL_ROOT}.bak"
VENV_DIR="${INSTALL_ROOT}/.venv"
LAUNCHER="${BIN_DIR}/af"

c_cyan()   { printf '\033[0;36m%s\033[0m\n' "$1"; }
c_yellow() { printf '\033[0;33m%s\033[0m\n' "$1"; }
c_green()  { printf '\033[0;32m%s\033[0m\n' "$1"; }
c_red()    { printf '\033[0;31m%s\033[0m\n' "$1" >&2; }

fail() {
    c_red "✗ $1"
    # staging 찌꺼기만 정리. 기존 설치(INSTALL_ROOT)는 건드리지 않는다.
    [ -d "${STAGING_ROOT}" ] && rm -rf "${STAGING_ROOT}"
    exit 1
}

need() {
    command -v "$1" >/dev/null 2>&1 || fail "$1 미설치. 먼저 설치하세요."
}

echo ""
c_cyan "============================================================"
c_cyan "  Agent Factory CLI v${AF_VERSION} 설치 (macOS/Linux)"
c_cyan "============================================================"

# ----------------------------------------------------------------------------
# Step 1: 선결 조건 확인 (curl/wget, tar, python3 >= 3.10)
# ----------------------------------------------------------------------------
c_yellow "► 선결 조건 확인..."

# R8: curl/wget 둘 다 없으면 명시 에러
DL=""
if command -v curl >/dev/null 2>&1; then
    DL="curl"
elif command -v wget >/dev/null 2>&1; then
    DL="wget"
else
    fail "curl 또는 wget이 필요합니다. (brew install curl 또는 apt install curl)"
fi

need tar
need python3

PYTHON_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PYTHON_MAJOR=$(echo "$PYTHON_VER" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VER" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    fail "python3 >= 3.10 필요 (현재 ${PYTHON_VER})"
fi
c_green "✓ python3 ${PYTHON_VER} / ${DL} 확인"

# ----------------------------------------------------------------------------
# Step 2: 이전 staging / backup 잔존물 정리 (INSTALL_ROOT는 건드리지 않음)
# ----------------------------------------------------------------------------
c_yellow "► 이전 staging 정리..."
[ -d "${STAGING_ROOT}" ] && rm -rf "${STAGING_ROOT}"
[ -d "${BACKUP_ROOT}" ] && rm -rf "${BACKUP_ROOT}"
mkdir -p "${STAGING_ROOT}" "${BIN_DIR}"
c_green "✓ 정리 완료"

# ----------------------------------------------------------------------------
# Step 3: 소스 다운로드 & staging에 전개
# ----------------------------------------------------------------------------
c_yellow "► 소스 다운로드 중 (${AF_TAG})..."
TMP_TGZ="$(mktemp -t af-src-XXXXXX.tar.gz)"
# staging 실패 시에도 임시 파일은 정리 (INSTALL_ROOT은 보존)
trap 'rm -f "${TMP_TGZ}"; [ -d "${STAGING_ROOT}" ] && rm -rf "${STAGING_ROOT}"' EXIT

if [ "$DL" = "curl" ]; then
    curl -fsSL -o "${TMP_TGZ}" "${AF_REPO_ZIP}" || fail "다운로드 실패: ${AF_REPO_ZIP}"
else
    wget -qO "${TMP_TGZ}" "${AF_REPO_ZIP}" || fail "다운로드 실패: ${AF_REPO_ZIP}"
fi

SIZE_MB=$(du -m "${TMP_TGZ}" | cut -f1)
c_green "✓ 다운로드 완료 (${SIZE_MB} MB)"

c_yellow "► staging(${STAGING_ROOT})에 압축 해제 중..."
tar -xzf "${TMP_TGZ}" -C "${STAGING_ROOT}" --strip-components=1 \
    || fail "압축 해제 실패"
c_green "✓ 압축 해제 완료"

# 필수 파일 검증
if [ ! -f "${STAGING_ROOT}/run_factory_cli.py" ]; then
    fail "archive 구조 오류: run_factory_cli.py 미발견"
fi

# ----------------------------------------------------------------------------
# Step 4: staging 내부에 venv + 의존성 설치 (교체 전 사전 검증)
# ----------------------------------------------------------------------------
c_yellow "► Python venv 생성 & 의존성 설치 (staging)..."
STAGING_VENV="${STAGING_ROOT}/.venv"
python3 -m venv "${STAGING_VENV}" || fail "venv 생성 실패"
# shellcheck disable=SC1091
. "${STAGING_VENV}/bin/activate"
pip install --quiet --upgrade pip
if [ -f "${STAGING_ROOT}/requirements.txt" ]; then
    pip install --quiet -r "${STAGING_ROOT}/requirements.txt" \
        || { deactivate; fail "requirements.txt 설치 실패"; }
    c_green "✓ 의존성 설치 완료"
else
    c_yellow "  requirements.txt 미발견 → 최소 의존성만 설치"
    pip install --quiet notebooklm-cli tavily-python filelock typer rich \
        || { deactivate; fail "최소 의존성 설치 실패"; }
fi
deactivate

# ----------------------------------------------------------------------------
# Step 5: 원자적 교체 — 기존을 .bak으로 옮기고 staging을 INSTALL_ROOT로 승격
# ----------------------------------------------------------------------------
c_yellow "► 설치 교체 중..."
if [ -d "${INSTALL_ROOT}" ]; then
    mv "${INSTALL_ROOT}" "${BACKUP_ROOT}" \
        || fail "기존 설치 백업 실패 (복원 필요 시: mv ${BACKUP_ROOT} ${INSTALL_ROOT})"
fi
mv "${STAGING_ROOT}" "${INSTALL_ROOT}" \
    || { \
         [ -d "${BACKUP_ROOT}" ] && mv "${BACKUP_ROOT}" "${INSTALL_ROOT}"; \
         fail "신규 설치 적용 실패 → 기존 설치 복원됨"; \
       }

# 교체 성공: 이전 백업 제거 (실패 시에도 경고만)
if [ -d "${BACKUP_ROOT}" ]; then
    rm -rf "${BACKUP_ROOT}" || c_yellow "! 이전 백업 정리 실패: ${BACKUP_ROOT} (수동 제거 필요)"
fi
# staging trap 해제 — 이 시점부터 ${STAGING_ROOT}는 존재하지 않음
trap 'rm -f "${TMP_TGZ}"' EXIT
c_green "✓ 교체 완료"

# ----------------------------------------------------------------------------
# Step 6: 런처 스크립트 생성
# ----------------------------------------------------------------------------
c_yellow "► 런처 스크립트 생성: ${LAUNCHER}"
if [ -L "${LAUNCHER}" ] || [ -f "${LAUNCHER}" ]; then
    rm -f "${LAUNCHER}"
fi
cat > "${LAUNCHER}" <<EOF
#!/usr/bin/env bash
# Agent Factory CLI launcher (v${AF_VERSION})
exec "${VENV_DIR}/bin/python" "${INSTALL_ROOT}/run_factory_cli.py" "\$@"
EOF
chmod +x "${LAUNCHER}"
c_green "✓ 런처 생성 완료"

# ----------------------------------------------------------------------------
# Step 7: PATH 안내
# ----------------------------------------------------------------------------
case ":${PATH}:" in
    *":${BIN_DIR}:"*)
        c_green "✓ PATH에 ${BIN_DIR} 이미 등록됨"
        ;;
    *)
        c_yellow "! ${BIN_DIR}가 PATH에 없습니다."
        c_yellow "  다음 한 줄을 ~/.zshrc 또는 ~/.bashrc에 추가하세요:"
        echo "    export PATH=\"${BIN_DIR}:\$PATH\""
        ;;
esac

# ----------------------------------------------------------------------------
# Step 8: Chrome 설치 확인 (NotebookLM용)
# ----------------------------------------------------------------------------
c_yellow "► Chrome 설치 확인..."
CHROME_FOUND=0
case "$(uname -s)" in
    Darwin)
        if [ -d "/Applications/Google Chrome.app" ] \
           || [ -d "$HOME/Applications/Google Chrome.app" ]; then
            CHROME_FOUND=1
        fi
        ;;
    Linux)
        for cmd in google-chrome google-chrome-stable chromium chromium-browser; do
            if command -v "$cmd" >/dev/null 2>&1; then
                CHROME_FOUND=1
                break
            fi
        done
        ;;
esac
if [ "${CHROME_FOUND}" -eq 1 ]; then
    c_green "✓ Chrome 감지됨"
else
    c_yellow "! Chrome 미감지 → NotebookLM 로그인 시 수동 브라우저 필요"
    c_yellow "  macOS: https://www.google.com/chrome/"
    c_yellow "  Linux: sudo apt install google-chrome-stable (또는 chromium)"
fi

# ----------------------------------------------------------------------------
# Step 9: __check-nlm 검증 (nlm 의존성 확인)
# ----------------------------------------------------------------------------
c_yellow "► NotebookLM CLI (__check-nlm) 검증 중..."
NLM_OUT=$("${LAUNCHER}" __check-nlm 2>&1 || true)
NLM_RC=$?
if [ "${NLM_RC}" -eq 0 ]; then
    c_green "✓ nlm 모듈 로드 정상"
else
    c_yellow "! __check-nlm 실패 (rc=${NLM_RC}) → \`af setup\` 실행 시 자동 복구 시도"
    if [ -n "${NLM_OUT}" ]; then
        echo "  --- __check-nlm 출력 ---"
        echo "${NLM_OUT}" | sed 's/^/  /'
        echo "  ------------------------"
    fi
fi

echo ""
c_cyan "============================================================"
c_green "  설치 완료! v${AF_VERSION}"
c_cyan "============================================================"
echo ""
echo "  새 쉘을 열거나 아래 명령으로 시작:"
c_yellow "    af --help"
c_yellow "    af setup"
echo ""
