#!/usr/bin/env bash
# Godot 4 에디터 실행 스크립트 (중세 도트 배틀체스 장기 프로젝트 열기)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/tools/Godot_v4.3-stable_linux.x86_64" -e --path "$DIR/godot_project" &
