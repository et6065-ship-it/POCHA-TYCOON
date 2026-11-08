"""
main.py
'전세계 길거리 음식 포차 타이쿤 (World Street Food Pocha Tycoon)' 메인 진입점.
- 데스크톱(Windows/macOS/Linux) 및 모바일/PC 웹앱(Pygbag WebAssembly) 100% 호환 비동기 메인 루프
- Pygame 초기화 및 1280x720 윈도우 생성
- GameManager 싱글톤 세이브 데이터(로컬 JSON + 웹 브라우저 localStorage) 로드
- SceneManager를 통해 "title" 씬 시작 및 60FPS 메인 루프 실행
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
import pygame

import config
import core
import data
import entities
import scenes
import stations
from core.game_manager import GameManager
from core.network_manager import duel_network
from core.scene_manager import SceneManager


def create_app(initial_scene: str = "title") -> tuple[pygame.Surface, pygame.time.Clock, GameManager, SceneManager]:
    """Pygame 디스플레이, 클럭, GameManager, SceneManager를 초기화하여 반환한다."""
    try:
        pygame.mixer.pre_init(44100, -16, 2, 1024)
    except Exception:
        pass
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        from core.effects import sound_fx
        sound_fx._init_mixer_safely()
    except Exception:
        pass

    init_size = config.SCREEN_SIZE
    if sys.platform == "emscripten":
        try:
            import platform
            iw = int(platform.window.innerWidth or 1280)
            ih = int(platform.window.innerHeight or 720)
            if ih > iw:
                init_size = config.PORTRAIT_SIZE
                config.WINDOW_WIDTH, config.WINDOW_HEIGHT = init_size
                config.WINDOW_SIZE = init_size
        except Exception:
            pass

    screen = pygame.display.set_mode(init_size)
    pygame.display.set_caption(config.WINDOW_TITLE)
    clock = pygame.time.Clock()

    game_mgr = GameManager.get_instance()
    game_mgr.load_game()
    if sys.platform != "emscripten":
        game_mgr.apply_runtime_settings(apply_display=True)
    else:
        game_mgr.apply_runtime_settings(apply_display=False)
        if init_size == config.PORTRAIT_SIZE:
            config.apply_display_mode(config.PORTRAIT_WIDTH, config.PORTRAIT_HEIGHT, fullscreen=config.FULLSCREEN)
        else:
            config.sync_browser_display_and_fullscreen(config.FULLSCREEN)
    screen = pygame.display.get_surface() or screen

    scene_mgr = SceneManager(game_mgr=game_mgr, initial_scene=initial_scene)
    return screen, clock, game_mgr, scene_mgr


async def main(max_frames: int = 0) -> None:
    """데스크톱 및 웹앱(Pygbag WebAssembly) 통합 메인 게임 루프."""
    is_duel_client = "--duel-client" in sys.argv
    initial_scene = "duel_lobby" if is_duel_client else "title"
    screen, clock, game_mgr, scene_mgr = create_app(initial_scene=initial_scene)

    if is_duel_client:
        idx = sys.argv.index("--duel-client")
        target_ip = sys.argv[idx + 1] if (idx + 1) < len(sys.argv) else f"127.0.0.1:{config.DEFAULT_DUEL_PORT}"
        pygame.display.set_caption(f"{config.WINDOW_TITLE} - [2P 결투 클라이언트]")
        scene_mgr.change_scene("duel_lobby", auto_join_ip=target_ip)
    elif max_frames == 0:
        scene_mgr.start_loading(duration=1.8, wait_for_tap=True, cycle_themes=True)

    running = True
    frame_count = 0

    try:
        while running:
            dt = clock.tick(config.FPS) / 1000.0
            dt = min(dt, 0.1)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                try:
                    scene_mgr.handle_event(event)
                except Exception:
                    if sys.platform != "emscripten":
                        try:
                            with open(os.path.join(config.BASE_DIR, "crash_log.txt"), "a", encoding="utf-8") as f:
                                f.write(traceback.format_exc() + "\n")
                        except Exception:
                            pass

            try:
                scene_mgr.update(dt)
                active_surface = pygame.display.get_surface() or screen
                scene_mgr.draw(active_surface)
                pygame.display.flip()
                if frame_count <= 2 and sys.platform == "emscripten":
                    try:
                        import platform
                        platform.window.eval(
                            "window.__pocha_first_frame_drawn = true; "
                            "if (window.__dismissPochaBootLoader) { window.__dismissPochaBootLoader(); }"
                        )
                    except Exception:
                        pass
            except Exception:
                if sys.platform != "emscripten":
                    try:
                        with open(os.path.join(config.BASE_DIR, "crash_log.txt"), "a", encoding="utf-8") as f:
                            f.write(traceback.format_exc() + "\n")
                    except Exception:
                        pass

            await asyncio.sleep(0)

            frame_count += 1
            if max_frames > 0 and frame_count >= max_frames:
                running = False
    except KeyboardInterrupt:
        pass
    finally:
        duel_network.close()
        if not is_duel_client:
            game_mgr.save_game()
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
