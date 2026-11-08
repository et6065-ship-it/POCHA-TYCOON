#!/usr/bin/env bash
# ================================================================
#  [GAME LAUNCHER] 통합 게임 프로젝트 (/Desktop/GAME) GitHub 원클릭 배포
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "================================================================"
echo " [GAME LAUNCHER] 통합 게임 프로젝트 GitHub 업로드 및 배포"
echo " 워크스페이스: $SCRIPT_DIR"
echo "================================================================"

git config --local user.name "et6065-ship-it"
git config --local user.email "et6065-ship-it@users.noreply.github.com"
git config --local credential.helper store

git add .
git commit -m "Unified GAME Launcher: Battle Janggi + Battle Chess + Block Blast Classic" 2>/dev/null || true

echo ""
echo "Pushing to https://github.com/et6065-ship-it/POCHA-TYCOON.git ..."
echo "배포 완료 후 접속 주소:"
echo "  🎮 통합 게임 런처 포털   : https://et6065-ship-it.github.io/POCHA-TYCOON/arcade/"
echo "  💎 블록 블라스트 클래식  : https://et6065-ship-it.github.io/POCHA-TYCOON/blockblast/"
echo "  ⚔️ 메인 (장기·체스 통합) : https://et6065-ship-it.github.io/POCHA-TYCOON/"
echo "  🇰🇷 중세 배틀 장기       : https://et6065-ship-it.github.io/POCHA-TYCOON/janggi/"
echo "  ♛ 중세 배틀 체스       : https://et6065-ship-it.github.io/POCHA-TYCOON/chess/"
echo ""

git push -u origin main
