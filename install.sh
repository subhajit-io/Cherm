#!/usr/bin/env bash
# Cherm Universal Installer for Linux & macOS
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/subhajit-io/Cherm/main/install.sh | bash

set -e

REPO="subhajit-io/Cherm"
INSTALL_DIR="${HOME}/.cherm"
BIN_DIR="${HOME}/.local/bin"

echo "=========================================================="
echo "  Cherm Universal Installer (Linux & macOS)"
echo "  Static Architecture & Code Inspection Suite"
echo "=========================================================="

OS="$(uname -s)"
ARCH="$(uname -m)"

echo "[*] Detected System: ${OS} (${ARCH})"

# Create directories
mkdir -p "${INSTALL_DIR}"
mkdir -p "${BIN_DIR}"

# Check for python3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[!] Warning: python3 is not detected in your PATH."
    echo "    Please install Python 3.8+ (e.g. brew install python3 or apt install python3)."
fi

# Try downloading prebuilt binary if available, else download repository package
RELEASE_URL="https://github.com/${REPO}/releases/latest/download"
BINARY_NAME=""

if [ "${OS}" = "Linux" ]; then
    if [ "${ARCH}" = "x86_64" ]; then
        BINARY_NAME="cherm-linux-x86_64"
    elif [ "${ARCH}" = "aarch64" ] || [ "${ARCH}" = "arm64" ]; then
        BINARY_NAME="cherm-linux-arm64"
    fi
elif [ "${OS}" = "Darwin" ]; then
    if [ "${ARCH}" = "arm64" ]; then
        BINARY_NAME="cherm-macos-arm64"
    else
        BINARY_NAME="cherm-macos-x86_64"
    fi
fi

INSTALLED_STANDALONE=false

if [ -n "${BINARY_NAME}" ]; then
    echo "[*] Checking for precompiled standalone binary: ${BINARY_NAME}..."
    if curl -fsSL "${RELEASE_URL}/${BINARY_NAME}" -o "${BIN_DIR}/cherm" 2>/dev/null; then
        chmod +x "${BIN_DIR}/cherm"
        INSTALLED_STANDALONE=true
        echo "[+] Successfully installed standalone binary to ${BIN_DIR}/cherm"
    fi
fi

if [ "${INSTALLED_STANDALONE}" = false ]; then
    echo "[*] Setting up Cherm distribution package in ${INSTALL_DIR}..."
    RAW_BASE="https://raw.githubusercontent.com/${REPO}/main/check-in-terminal"
    
    # Download core scripts
    FILES=("cherm.py" "cherm_cli.py" "cherm_gui.py" "cherm_bridge.py" "ml_scanner.py" "cherm_mcp.py" "cherm_commands.json" "cherm_mindmap.html")
    for file in "${FILES[@]}"; do
        echo "    -> Fetching ${file}..."
        curl -fsSL "${RAW_BASE}/${file}" -o "${INSTALL_DIR}/${file}"
    done

    # Create wrapper executable in ~/.local/bin/cherm
    cat << 'EOF' > "${BIN_DIR}/cherm"
#!/usr/bin/env bash
CHERM_HOME="${HOME}/.cherm"
exec python3 "${CHERM_HOME}/cherm.py" "$@"
EOF
    chmod +x "${BIN_DIR}/cherm"
    echo "[+] Created Cherm launcher at ${BIN_DIR}/cherm"
fi

# Ensure ~/.local/bin is in PATH in user shell profile files
add_to_path() {
    local rc_file="$1"
    if [ -f "${rc_file}" ]; then
        if ! grep -q 'export PATH=.*\.local/bin' "${rc_file}"; then
            echo '' >> "${rc_file}"
            echo '# Cherm binary PATH' >> "${rc_file}"
            echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "${rc_file}"
            echo "[+] Added ~/.local/bin to ${rc_file}"
        fi
    fi
}

add_to_path "${HOME}/.bashrc"
add_to_path "${HOME}/.zshrc"
add_to_path "${HOME}/.profile"

echo ""
echo "=========================================================="
echo "  Cherm installation complete!"
echo "  Run: cherm --help"
echo "  Or start the interactive terminal companion: cherm gui"
echo "  Or start the browser dashboard: cherm web"
echo "=========================================================="
