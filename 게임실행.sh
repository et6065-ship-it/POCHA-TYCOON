#!/usr/bin/env bash
# ================================================================
#  전세계 길거리 음식 포차 타이쿤 (World Street Food Pocha Tycoon)
#  Linux / macOS 원클릭 실행 스크립트
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

# 1. 단독 실행 바이너리(포차타이쿤)가 있고 파이썬이 없는 경우 즉시 실행
if [ -z "$PYTHON_BIN" ] && [ -x "./포차타이쿤" ]; then
    exec "./포차타이쿤" "$@"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[오류] Python3가 설치되어 있지 않습니다."
    read -r -p "엔터 키를 누르면 창이 닫힙니다..."
    exit 1
fi

# 2. pygame(pygame-ce) 설치 여부 확인 및 미설치 시 자동 설치
if ! "$PYTHON_BIN" -c "import pygame" >/dev/null 2>&1; then
    if [ -x "./포차타이쿤" ]; then
        exec "./포차타이쿤" "$@"
    fi
    echo "[안내] pygame-ce 라이브러리가 없어 자동 설치를 진행합니다..."
    "$PYTHON_BIN" -m pip install --user pygame-ce || "$PYTHON_BIN" -m pip install pygame-ce
fi

# 3. 메인 게임 실행
exec "$PYTHON_BIN" main.py "$@"
