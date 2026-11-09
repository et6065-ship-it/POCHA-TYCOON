@echo off
chcp 65001 > nul
title 전세계 길거리 음식 포차 타이쿤 (World Street Food Pocha Tycoon)
cd /d "%~dp0"

REM 1. 파이썬 및 pygame 설치 여부 확인 후 최신 코드 우선 실행
python -c "import pygame" >nul 2>&1
if %errorlevel% equ 0 (
    python main.py %*
    if errorlevel 1 pause
    exit /b 0
)

py -3 -c "import pygame" >nul 2>&1
if %errorlevel% equ 0 (
    py -3 main.py %*
    if errorlevel 1 pause
    exit /b 0
)

REM 2. 파이썬이 없을 때만 포차타이쿤.exe 단독 실행
if exist "포차타이쿤.exe" (
    start "" "포차타이쿤.exe" %*
    exit /b 0
)

echo [오류] 파이썬(Python) 또는 포차타이쿤.exe 파일을 찾을 수 없습니다.
pause
