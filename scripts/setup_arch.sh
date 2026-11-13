#!/usr/bin/env bash
# Install system and Python dependencies for Lightweight Video Renamer on Arch Linux.
#
# Usage:
#   ./scripts/setup_arch.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"

if ! command -v pacman >/dev/null 2>&1; then
    echo "Error: pacman not found. This script is intended for Arch Linux and Arch-based distributions." >&2
    exit 1
fi

SYS_PACKAGES=(
    python
    tk
    mpv
    libheif
    libraw
)

echo "==> Checking Arch Linux system dependencies (${SYS_PACKAGES[*]})..."
MISSING_PKGS="$(pacman -T "${SYS_PACKAGES[@]}" || true)"
if [[ -n "${MISSING_PKGS}" ]]; then
    # Convert newline-separated output from pacman -T into an array
    mapfile -t TO_INSTALL <<< "${MISSING_PKGS}"
    echo "==> Installing missing system packages via pacman: ${TO_INSTALL[*]}"
    sudo pacman -S --needed "${TO_INSTALL[@]}"
else
    echo "==> All required system packages are already installed."
fi

echo "==> Creating Python virtual environment at ${VENV_DIR}..."
python3 -m venv "${VENV_DIR}"

echo "==> Upgrading pip..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip

echo "==> Installing Lightweight Video Renamer and dependencies (including pytest)..."
if ! "${VENV_DIR}/bin/python" -m pip install -e "${REPO_ROOT}[dev]"; then
    echo "==> Initial pip install failed; ensuring build tools (base-devel, cmake) are present and retrying..."
    sudo pacman -S --needed base-devel cmake
    "${VENV_DIR}/bin/python" -m pip install -e "${REPO_ROOT}[dev]"
fi

echo "==> Verifying installed dependencies..."
"${VENV_DIR}/bin/python" -c '
import tkinter
import mpv
import send2trash
import PIL
import pillow_heif
import rawpy
import resvg_py
import pytest
print("All dependencies verified successfully (libmpv, tkinter, pillow, pillow-heif, rawpy, resvg-py, send2trash, pytest).")
'

cat <<EOF

Setup complete!

To run Lightweight Video Renamer:
  source .venv/bin/activate
  lightweight-video-renamer [folder]            # Video mode
  lightweight-video-renamer --images [folder]   # Image mode

To run the test suite:
  .venv/bin/pytest
EOF
