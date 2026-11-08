#!/usr/bin/env bash
# ================================================================
#  [POCHA-TYCOON + BATTLE JANGGI & CHESS] GitHub Auto Upload (Linux / macOS)
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME_DIR="/home/janginwoo/Desktop/GAME"
cd "$SCRIPT_DIR" || exit 1

echo "================================================================"
echo " [MULTI-GAME] POCHA-TYCOON + 중세 배틀 장기 & 체스 통합 GitHub 업로드"
echo "================================================================"

if [ -d "$GAME_DIR" ]; then
  mkdir -p "$SCRIPT_DIR/web_games/board"
  cp -f "$GAME_DIR/index.html" "$SCRIPT_DIR/web_games/board/"
  cp -f "$GAME_DIR/chess.html" "$SCRIPT_DIR/web_games/board/" 2>/dev/null || true
  cp -f "$GAME_DIR/arcade.html" "$SCRIPT_DIR/web_games/board/" 2>/dev/null || true
  rm -rf "$SCRIPT_DIR/web_games/board/src" "$SCRIPT_DIR/web_games/board/assets"
  cp -r "$GAME_DIR/src" "$SCRIPT_DIR/web_games/board/src"
  cp -r "$GAME_DIR/assets" "$SCRIPT_DIR/web_games/board/assets"
  echo "✔ 중세 배틀 장기 & 체스 HD 도트 웹앱이 함께 패키징되었습니다."
fi

git config --local user.name "et6065-ship-it"
git config --local user.email "et6065-ship-it@users.noreply.github.com"
git config --local credential.helper store

git add .
git commit -m "Update Multi-Game WebApp: Pocha Tycoon + HD Pixel Battle Janggi & Chess" 2>/dev/null || true

echo ""
echo "Pushing to https://github.com/et6065-ship-it/POCHA-TYCOON.git ..."
echo "배포 완료 후 접속 주소:"
echo "  🍢 포차 타이쿤 : https://et6065-ship-it.github.io/POCHA-TYCOON/"
echo "  🇰🇷 중세 배틀 장기 : https://et6065-ship-it.github.io/POCHA-TYCOON/janggi/"
echo "  ♛ 중세 배틀 체스 : https://et6065-ship-it.github.io/POCHA-TYCOON/chess/"
echo "  🎮 통합 오락실 포털 : https://et6065-ship-it.github.io/POCHA-TYCOON/arcade/"
echo ""

git push -u origin main
