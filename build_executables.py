#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAME 통합 런처 & 실행 파일 빌더 (build_executables.py)
======================================================
1. 네이티브 Linux ELF 실행 파일 생성:
   - Game_Launcher.x86_64 (통합 게임 런처: 중세 배틀 장기 · 중세 배틀 체스 · 포차 타이쿤 통합 관리)
   - Medieval_Battle_Janggi.x86_64 (하위 호환 실행 바이너리)
   - pocha_tycoon/Pocha_Tycoon.x86_64 (포차 타이쿤 전용 실행 바이너리)
2. 더블클릭 즉시 실행 가능한 통합 런처 아이콘 생성:
   - /home/janginwoo/Desktop/GAME/통합_게임_런처.desktop
   - /home/janginwoo/Desktop/통합_게임_런처.desktop
"""

import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

C_WRAPPER_LAUNCHER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <limits.h>
#include <libgen.h>
#include <string.h>

int main(int argc, char *argv[]) {
    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len != -1) {
        exe_path[len] = '\0';
        char *dir = dirname(exe_path);
        chdir(dir);
    }
    char **new_argv = malloc(sizeof(char *) * (argc + 2));
    if (!new_argv) return 1;
    new_argv[0] = "/usr/bin/python3";
    new_argv[1] = "desktop_launcher.py";
    for (int i = 1; i < argc; i++) {
        new_argv[i + 1] = argv[i];
    }
    new_argv[argc + 1] = NULL;
    execv("/usr/bin/python3", new_argv);
    perror("execv failed");
    return 1;
}
'''

C_WRAPPER_POCHA = r'''
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <limits.h>
#include <libgen.h>
#include <string.h>

int main(int argc, char *argv[]) {
    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len != -1) {
        exe_path[len] = '\0';
        char *dir = dirname(exe_path);
        chdir(dir);
    }
    char **new_argv = malloc(sizeof(char *) * (argc + 2));
    if (!new_argv) return 1;
    new_argv[0] = "/usr/bin/python3";
    new_argv[1] = "main.py";
    for (int i = 1; i < argc; i++) {
        new_argv[i + 1] = argv[i];
    }
    new_argv[argc + 1] = NULL;
    execv("/usr/bin/python3", new_argv);
    perror("execv failed");
    return 1;
}
'''


def build_elf(c_code: str, out_path: Path) -> None:
    tmp_c = BASE_DIR / "_tmp_launcher.c"
    tmp_c.write_text(c_code, encoding="utf-8")
    try:
        subprocess.run(
            ["gcc", "-O2", "-s", str(tmp_c), "-o", str(out_path)],
            check=True,
        )
        out_path.chmod(0o755)
        print(f"[+] ELF 실행 파일 생성 완료: {out_path}")
    finally:
        if tmp_c.exists():
            tmp_c.unlink()


def create_desktop_shortcut(
    target_exe: Path,
    work_dir: Path,
    icon_path: Path,
    name: str,
    comment: str,
    out_file: Path,
) -> None:
    content = f"""#!/usr/bin/env xdg-open
[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment={comment}
Path={work_dir}
Exec="{target_exe}"
Icon={icon_path}
Terminal=false
Categories=Game;StrategyGame;BoardGame;
StartupNotify=true
"""
    out_file.write_text(content, encoding="utf-8")
    out_file.chmod(0o755)
    print(f"[+] 바로가기 아이콘 생성 완료: {out_file}")


def main() -> None:
    launcher_bin = BASE_DIR / "Game_Launcher.x86_64"
    janggi_bin = BASE_DIR / "Medieval_Battle_Janggi.x86_64"
    pocha_dir = BASE_DIR / "pocha_tycoon"
    pocha_bin = pocha_dir / "Pocha_Tycoon.x86_64"
    icon_svg = BASE_DIR / "godot_project" / "icon.svg"

    build_elf(C_WRAPPER_LAUNCHER, launcher_bin)
    build_elf(C_WRAPPER_LAUNCHER, janggi_bin)
    if pocha_dir.exists():
        build_elf(C_WRAPPER_POCHA, pocha_bin)

    # GAME 폴더 내 통합 런처 .desktop
    create_desktop_shortcut(
        launcher_bin,
        BASE_DIR,
        icon_svg,
        "🎮 GAME 통합 런처 (장기 · 체스 · 타이쿤)",
        "중세 배틀 장기 & 중세 배틀 체스 & 포차 타이쿤 통합 게임 런처",
        BASE_DIR / "통합_게임_런처.desktop",
    )

    # 바탕화면(Desktop)에도 단일 통합 런처 아이콘 배치 및 구형 개별 아이콘 정리
    desktop_dir = BASE_DIR.parent
    if desktop_dir.name == "Desktop" and desktop_dir.exists():
        create_desktop_shortcut(
            launcher_bin,
            BASE_DIR,
            icon_svg,
            "🎮 GAME 통합 런처 (장기 · 체스)",
            "중세 배틀 장기 & 중세 배틀 체스 & 포차 타이쿤 통합 게임 런처",
            desktop_dir / "통합_게임_런처.desktop",
        )
        for old_shortcut in ("포차타이쿤.desktop", "중세_배틀체스_장기.desktop"):
            old_p = desktop_dir / old_shortcut
            if old_p.exists():
                old_p.unlink()
                print(f"[-] 바탕화면 구형 개별 바로가기 정리 완료: {old_p}")


if __name__ == "__main__":
    main()
