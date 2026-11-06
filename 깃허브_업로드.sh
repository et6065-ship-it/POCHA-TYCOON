#!/usr/bin/env bash
# ================================================================
#  [POCHA-TYCOON] GitHub Auto Upload (Linux / macOS)
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "================================================================"
echo " [POCHA-TYCOON] GitHub Auto Upload"
echo "================================================================"

git config --local user.name "et6065-ship-it"
git config --local user.email "et6065-ship-it@users.noreply.github.com"
git config --local credential.helper store

git add .
git commit -m "Update POCHA-TYCOON game and WebApp" 2>/dev/null || true

echo ""
echo "Pushing to https://github.com/et6065-ship-it/POCHA-TYCOON.git ..."
echo "(처음 푸시 시 GitHub 아이디(et6065-ship-it)와 Personal Access Token을 입력하면 이후 자동 저장됩니다.)"
echo ""

git push -u origin main
