#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전세계 길거리 음식 포차 타이쿤 (World Street Food Pocha Tycoon) - 실행 파일 빌더
1. 네이티브 Linux ELF 실행 바이너리 생성: Pocha_Tycoon.x86_64
2. 더블클릭 즉시 실행 가능한 .desktop 아이콘 생성 (GAME_POCHA 폴더 및 바탕화면)
"""

import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

C_WRAPPER = r"""
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
        if (chdir(dir) != 0) {
            perror("chdir failed");
        }
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
"""


def build_elf(c_code: str, out_path: Path) -> None:
    tmp_c = BASE_DIR / "_tmp_pocha_launcher.c"
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


def create_desktop_shortcut(target_exe: Path, icon_path: Path, out_file: Path) -> None:
    content = f"""#!/usr/bin/env xdg-open
[Desktop Entry]
Version=1.0
Type=Application
Name=전세계 길거리 음식 포차 타이쿤
Comment=9개국 야시장 월드 투어 × 단일 메뉴 장인 × 1:1 네트워크 결투
Path={BASE_DIR}
Exec="{target_exe}"
Icon={icon_path}
Terminal=false
Categories=Game;Simulation;
StartupNotify=true
"""
    out_file.write_text(content, encoding="utf-8")
    out_file.chmod(0o755)
    print(f"[+] 바로가기 아이콘 생성 완료: {out_file}")


def main() -> None:
    elf_bin = BASE_DIR / "Pocha_Tycoon.x86_64"
    icon_svg = BASE_DIR / "assets" / "icon.svg"

    build_elf(C_WRAPPER, elf_bin)
    create_desktop_shortcut(elf_bin, icon_svg, BASE_DIR / "포차타이쿤_실행.desktop")

    desktop_dir = BASE_DIR.parent
    if desktop_dir.name == "Desktop" and desktop_dir.exists():
        create_desktop_shortcut(elf_bin, icon_svg, desktop_dir / "포차타이쿤.desktop")


if __name__ == "__main__":
    main()
