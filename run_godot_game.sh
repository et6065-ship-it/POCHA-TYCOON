#!/usr/bin/env bash
# Godot 4 게임 즉시 실행 스크립트
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/tools/Godot_v4.3-stable_linux.x86_64" --path "$DIR/godot_project" &
