#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAME 통합 런처 (Unified Game Launcher — 중세 배틀 장기 · 중세 배틀 체스 · 포차 타이쿤)
======================================================================================
- /home/janginwoo/Desktop/GAME 통합 프로젝트를 관리하고 실행하는 메인 런처입니다.
- 기본 실행 시 통합 런처 허브(arcade.html)를 열며, 옵션(--janggi, --chess, --pocha)을 지원합니다.
- 로컬 런처 전용 API(/api/status, /api/launch-pocha, /api/git-push)를 내장하여
  웹 런처 UI에서 네이티브 포차 타이쿤 실행 및 원클릭 GitHub 배포를 수행합니다.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


APP_TITLE = "🎮 GAME LAUNCHER — 중세 배틀 장기 · 체스 통합 런처"
DEFAULT_WIDTH = 1600
DEFAULT_HEIGHT = 980


def get_base_dir() -> Path:
    """PyInstaller 번들 실행 환경(_MEIPASS) 또는 일반 스크립트 경로 반환."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent


def find_free_port(preferred: int = 8765) -> int:
    """사용 가능한 로컬 포트 탐색."""
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class UnifiedLauncherHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """정적 웹 게임 서빙 + 로컬 통합 런처 제어 API 핸들러."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/status"):
            base_dir = get_base_dir()
            self._send_json(
                {
                    "ok": True,
                    "mode": "LOCAL_PC_LAUNCHER",
                    "workspace": str(base_dir),
                    "hasPocha": (base_dir / "pocha_tycoon" / "main.py").exists(),
                }
            )
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        base_dir = get_base_dir()

        if self.path.startswith("/api/launch-pocha"):
            pocha_dir = base_dir / "pocha_tycoon"
            pocha_main = pocha_dir / "main.py"
            if not pocha_main.exists():
                self._send_json({"ok": False, "error": "pocha_tycoon/main.py 파일이 없습니다."}, 404)
                return
            try:
                py_bin = sys.executable or shutil.which("python3") or "python3"
                subprocess.Popen(
                    [py_bin, str(pocha_main)],
                    cwd=str(pocha_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._send_json({"ok": True})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, 500)
            return

        if self.path.startswith("/api/git-push"):
            upload_sh = base_dir / "깃허브_업로드.sh"
            if not upload_sh.exists():
                self._send_json({"ok": False, "output": "깃허브_업로드.sh 스크립트가 없습니다."}, 404)
                return
            try:
                proc = subprocess.run(
                    ["bash", str(upload_sh)],
                    cwd=str(base_dir),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self._send_json(
                    {
                        "ok": proc.returncode == 0,
                        "output": (proc.stdout or "") + "\n" + (proc.stderr or ""),
                    }
                )
            except Exception as exc:
                self._send_json({"ok": False, "output": str(exc)}, 500)
            return

        self._send_json({"ok": False, "error": "Unknown API endpoint"}, 404)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


def start_local_server(root_dir: Path, port: int) -> http.server.ThreadingHTTPServer:
    """지정된 루트 디렉토리를 서빙하는 백그라운드 HTTP 서버 시작."""
    handler = functools.partial(UnifiedLauncherHTTPHandler, directory=str(root_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, name="UnifiedLauncherServer", daemon=True)
    thread.start()
    return server


def launch_browser_app_mode(url: str) -> subprocess.Popen | None:
    """Chrome / Edge의 데스크톱 앱 모드(--app)로 네이티브 창처럼 실행 시도."""
    candidates = []
    if sys.platform.startswith("win"):
        prog_files = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        for base in prog_files:
            if not base:
                continue
            candidates.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))
            candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
    else:
        for bin_name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            found = shutil.which(bin_name)
            if found:
                candidates.append(found)

    for exe in candidates:
        if exe and os.path.exists(exe):
            try:
                return subprocess.Popen(
                    [
                        exe,
                        f"--app={url}",
                        f"--window-size={DEFAULT_WIDTH},{DEFAULT_HEIGHT}",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                continue
    return None


def main() -> int:
    base_dir = get_base_dir()

    # --pocha 인자 전달 시 포차 타이쿤 직접 실행
    if "--pocha" in sys.argv:
        pocha_dir = base_dir / "pocha_tycoon"
        os.chdir(pocha_dir)
        os.execv(sys.executable, [sys.executable, str(pocha_dir / "main.py")])

    entry_page = "arcade.html"
    if "--janggi" in sys.argv:
        entry_page = "index.html?game=janggi"
    elif "--chess" in sys.argv:
        entry_page = "chess.html"

    port = find_free_port(8765)
    server = start_local_server(base_dir, port)
    url = f"http://127.0.0.1:{port}/{entry_page}"

    print(f"[*] {APP_TITLE}")
    print(f"[*] 통합 런처 로컬 서버 구동 완료: {url}")

    # 1순위: pywebview 네이티브 데스크톱 창 실행
    try:
        import webview  # type: ignore

        print("[*] PyWebView 네이티브 데스크톱 모드로 실행합니다...")
        webview.create_window(
            APP_TITLE,
            url,
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            min_size=(960, 680),
            background_color="#0b0f19",
        )
        webview.start()
        server.shutdown()
        return 0
    except ImportError:
        pass

    # 2순위: Edge / Chrome 프레임리스 앱(--app) 모드 실행
    proc = launch_browser_app_mode(url)
    if proc is not None:
        print("[*] 브라우저 데스크톱 앱 모드(--app)로 창을 열었습니다. 종료하려면 창을 닫거나 Ctrl+C를 누르세요.")
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
        return 0

    # 3순위: 시스템 기본 웹 브라우저 실행
    print("[*] 기본 웹 브라우저로 통합 런처를 엽니다. 종료하려면 터미널에서 Ctrl+C를 누르세요.")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[*] 서버를 종료합니다.")
    finally:
        server.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
