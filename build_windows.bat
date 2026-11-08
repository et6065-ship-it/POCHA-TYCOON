@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================================
echo   중세 배틀체스 장기 (Medieval Battle Janggi) - Windows .EXE 원클릭 빌더
echo ============================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    echo Python 3.10 이상을 설치한 후 다시 실행해 주세요.
    pause
    exit /b 1
)

echo [1/3] 필수 패키징 라이브러리(pyinstaller, pywebview) 확인 및 설치 중...
python -m pip install --upgrade pip pyinstaller pywebview
if %ERRORLEVEL% neq 0 (
    echo [경고] 패키지 자동 설치 중 일부 경고가 발생했으나 빌드를 계속 시도합니다.
)

echo.
echo [2/3] PyInstaller 단일 실행 파일(MedievalBattleJanggi.exe) 빌드 중...

set ADD_DATA_ARGS=--add-data "index.html;." --add-data "src;src"
if exist "css" (
    set ADD_DATA_ARGS=!ADD_DATA_ARGS! --add-data "css;css"
)
if exist "assets" (
    set ADD_DATA_ARGS=!ADD_DATA_ARGS! --add-data "assets;assets"
)
if exist "docs" (
    set ADD_DATA_ARGS=!ADD_DATA_ARGS! --add-data "docs;docs"
)

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "MedievalBattleJanggi" ^
    %ADD_DATA_ARGS% ^
    desktop_launcher.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [오류] EXE 빌드 중 오류가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo [3/3] 빌드 완료!
echo 생성된 실행 파일 위치: %CD%\dist\MedievalBattleJanggi.exe
echo ============================================================================
echo.
pause
