@echo off
title POCHA-TYCOON GitHub Upload
echo ================================================================
echo  [POCHA-TYCOON] GitHub Auto Upload (Isolated Local Config)
echo ================================================================
echo.
git config --local user.name "et6065-ship-it"
git config --local user.email "et6065-ship-it@users.noreply.github.com"
git add .
git commit -m "Update POCHA-TYCOON game and WebApp"
echo.
echo Pushing to https://github.com/et6065-ship-it/POCHA-TYCOON.git ...
echo (If a login window pops up, click [Sign in with your browser])
echo.
git push -u origin main
echo.
echo ================================================================
echo  Done! Check GitHub Actions for WebApp deployment.
echo ================================================================
pause
