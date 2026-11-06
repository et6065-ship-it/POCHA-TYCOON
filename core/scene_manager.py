"""
core/scene_manager.py
'전세계 길거리 음식 포차 타이쿤' 씬(Scene) 상태 전환, 가상 해상도(1280x720 -> 실제 창 크기) 자동 스케일링,
마우스 좌표 역변환, 그리고 전역 옵션 모달(사운드 볼륨 조절 & 해상도/전체화면 조절) 매니저.
지원 씬: "title", "prep", "play", "result", "duel_lobby", "duel_play", "duel_result"
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import pygame

import config
from core import art_renderer
from core.effects import sound_fx
from core.game_manager import GameManager, game_manager


class BaseScene:
    """모든 게임 씬의 공통 기반 클래스."""

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        scene_mgr: Optional["SceneManager"] = None,
        **kwargs: Any,
    ) -> None:
        self.game_mgr: GameManager = game_mgr if game_mgr is not None else game_manager
        self.scene_mgr: Optional["SceneManager"] = scene_mgr
        self.kwargs: Dict[str, Any] = kwargs

    def on_enter(self, **kwargs: Any) -> None:
        """씬 진입 시 호출되는 훅."""
        pass

    def on_exit(self) -> None:
        """씬 이탈 시 호출되는 훅."""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """Pygame 단일 이벤트를 처리한다."""
        pass

    def update(self, dt: float) -> None:
        """프레임 델타 타임(초) 기반 상태를 갱신한다."""
        pass

    def draw(self, surface: pygame.Surface) -> None:
        """화면에 현재 씬을 렌더링한다."""
        pass


class SceneManager:
    """
    게임 내 핵심 씬들을 등록·전환하고 handle_event, update(dt), draw(surface)를 라우팅한다.
    - 논리 해상도(1280x720)와 실제 창 해상도(1024x576, 1280x720, 1600x900, 1920x1080) 간
      고품질 스케일링 및 마우스 이벤트 좌표 자동 보정을 수행한다.
    - 언제든 열 수 있는 전역 [⚙️ 옵션 설정 (사운드·해상도)] 모달 오버레이를 내장한다.
    """

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        initial_scene: Optional[str] = None,
    ) -> None:
        self.game_mgr: GameManager = game_mgr if game_mgr is not None else game_manager
        self._scene_registry: Dict[str, Union[Type[Any], Callable[..., Any], Any]] = {}
        self.current_scene: Optional[Any] = None
        self.current_scene_name: str = ""
        self._logical_surface: Optional[pygame.Surface] = None

        # 전역 옵션 모달 상태
        self.options_open: bool = False
        self._opt_hover_pos: Tuple[int, int] = (0, 0)
        self._dragging_slider: Optional[str] = None
        self._opt_status_msg: str = ""
        self._opt_status_timer: float = 0.0
        self._setup_options_rects()

        self._register_default_scenes()

        if initial_scene:
            self.change_scene(initial_scene)

    def _setup_options_rects(self) -> None:
        """1280x720 기준 전역 옵션 모달 UI Rect 레이아웃을 초기화한다."""
        self.opt_panel_rect = pygame.Rect(220, 56, 840, 608)
        px, py = self.opt_panel_rect.x, self.opt_panel_rect.y

        self.opt_close_btn = pygame.Rect(self.opt_panel_rect.right - 126, py + 18, 104, 36)

        # 1) 사운드 ON/OFF & BGM ON/OFF 토글 버튼
        self.opt_sound_toggle_btn = pygame.Rect(px + 34, py + 114, 376, 42)
        self.opt_bgm_toggle_btn = pygame.Rect(px + 430, py + 114, 376, 42)

        # 2) 볼륨 슬라이더 3종 (master_volume, sfx_volume, bgm_volume)
        # 각 행: [-10%] 버튼, 슬라이더 바, 퍼센트 배지, [+10%] 버튼
        self.opt_slider_rows: Dict[str, Dict[str, pygame.Rect]] = {}
        slider_keys = ["master_volume", "sfx_volume", "bgm_volume"]
        for idx, skey in enumerate(slider_keys):
            ry = py + 174 + idx * 54
            self.opt_slider_rows[skey] = {
                "minus": pygame.Rect(px + 248, ry, 46, 36),
                "bar": pygame.Rect(px + 304, ry + 7, 286, 22),
                "pct": pygame.Rect(px + 598, ry + 3, 58, 30),
                "plus": pygame.Rect(px + 664, ry, 46, 36),
            }
        self.opt_sfx_test_btn = pygame.Rect(px + 720, py + 174 + 54, 86, 36)

        # 3) 해상도 및 모바일 화면비 프리셋 버튼 6종 (3x2 그리드)
        self.opt_res_btns: List[Tuple[Tuple[int, int], pygame.Rect]] = []
        for idx, res in enumerate(config.RESOLUTION_PRESETS):
            col = idx % 3
            row = idx // 3
            r = pygame.Rect(px + 34 + col * 258, py + 390 + row * 46, 250, 38)
            self.opt_res_btns.append((res, r))

        # 4) 창모드 / 전체화면 전환 버튼
        self.opt_windowed_btn = pygame.Rect(px + 34, py + 494, 380, 40)
        self.opt_fullscreen_btn = pygame.Rect(px + 426, py + 494, 380, 40)

        # 5) 하단 기본값 복원 & 저장 후 닫기 버튼
        self.opt_reset_default_btn = pygame.Rect(px + 34, self.opt_panel_rect.bottom - 54, 276, 40)
        self.opt_save_close_btn = pygame.Rect(self.opt_panel_rect.right - 294, self.opt_panel_rect.bottom - 54, 260, 40)

    def open_options(self) -> None:
        """옵션 모달을 연다."""
        sound_fx.play_click()
        self.options_open = True
        self._dragging_slider = None

    def close_options(self) -> None:
        """옵션 모달을 닫고 설정을 저장한다."""
        sound_fx.play_click()
        self.options_open = False
        self._dragging_slider = None
        if self.game_mgr:
            self.game_mgr.save_game()

    def toggle_options(self) -> None:
        if self.options_open:
            self.close_options()
        else:
            self.open_options()

    def _register_default_scenes(self) -> None:
        """기본 씬 클래스들을 지연 로드 가능하도록 등록한다."""
        try:
            from scenes.title_scene import TitleScene
            self._scene_registry["title"] = TitleScene
        except Exception:
            pass
        try:
            from scenes.prep_scene import PrepScene
            self._scene_registry["prep"] = PrepScene
        except Exception:
            pass
        try:
            from scenes.play_scene import PlayScene
            self._scene_registry["play"] = PlayScene
        except Exception:
            pass
        try:
            from scenes.result_scene import ResultScene
            self._scene_registry["result"] = ResultScene
        except Exception:
            pass
        try:
            from scenes.duel_lobby_scene import DuelLobbyScene
            self._scene_registry["duel_lobby"] = DuelLobbyScene
        except Exception:
            pass
        try:
            from scenes.duel_play_scene import DuelPlayScene
            self._scene_registry["duel_play"] = DuelPlayScene
        except Exception:
            pass
        try:
            from scenes.duel_result_scene import DuelResultScene
            self._scene_registry["duel_result"] = DuelResultScene
        except Exception:
            pass

    def register_scene(
        self,
        scene_name: str,
        scene_cls_or_obj: Union[Type[Any], Callable[..., Any], Any],
    ) -> None:
        """씬 이름과 씬 클래스(또는 팩토리/인스턴스)를 레지스트리에 등록한다."""
        key = scene_name.strip().lower()
        self._scene_registry[key] = scene_cls_or_obj

    def _resolve_scene_factory(self, key: str) -> Optional[Any]:
        if key not in self._scene_registry:
            self._register_default_scenes()
        return self._scene_registry.get(key)

    def _instantiate_scene(self, target: Any, **kwargs: Any) -> Any:
        if isinstance(target, type) or callable(target):
            try:
                return target(self.game_mgr, self, **kwargs)
            except TypeError:
                try:
                    return target(self.game_mgr, self)
                except TypeError:
                    try:
                        return target(self)
                    except TypeError:
                        return target()
        return target

    def change_scene(self, scene_name: str, **kwargs: Any) -> Optional[Any]:
        """지정한 이름의 씬으로 즉시 전환한다."""
        key = (scene_name or "title").strip().lower()
        alias_map = {
            "titlescene": "title",
            "main": "title",
            "menu": "title",
            "prepscene": "prep",
            "shop": "prep",
            "prepare": "prep",
            "playscene": "play",
            "game": "play",
            "cooking": "play",
            "resultscene": "result",
            "summary": "result",
            "duel": "duel_lobby",
            "duellobby": "duel_lobby",
            "duelplay": "duel_play",
            "duelresult": "duel_result",
        }
        key = alias_map.get(key, key)

        self.options_open = False
        self._dragging_slider = None

        if self.current_scene is not None and hasattr(self.current_scene, "on_exit"):
            try:
                self.current_scene.on_exit()
            except Exception:
                pass

        factory = self._resolve_scene_factory(key)
        if factory is None:
            raise ValueError(f"등록되지 않은 씬 이름입니다: {scene_name}")

        scene_obj = self._instantiate_scene(factory, **kwargs)
        if getattr(scene_obj, "game_mgr", None) is None:
            scene_obj.game_mgr = self.game_mgr
        scene_obj.scene_mgr = self

        if hasattr(scene_obj, "on_enter"):
            try:
                scene_obj.on_enter(**kwargs)
            except TypeError:
                scene_obj.on_enter()

        self.current_scene = scene_obj
        self.current_scene_name = key
        return self.current_scene

    switch_scene = change_scene
    set_scene = change_scene
    goto = change_scene

    # ==========================================================================
    # 다중 화면비(16:9 / 18:9 / 20:9 / 16:10) 등비 뷰포트 계산 및 터치·마우스 좌표 역변환
    # ==========================================================================
    @staticmethod
    def _compute_viewport(win_w: int, win_h: int) -> Tuple[int, int, int, int, float]:
        """
        실제 디스플레이 해상도(win_w, win_h) 안에서 1280x720(16:9) 코어 UI가 찌그러지지 않는
        최대 등비 뷰포트(ox, oy, vp_w, vp_h, scale)를 반환한다.
        """
        if win_w <= 0 or win_h <= 0:
            return 0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT, 1.0
        scale = min(win_w / float(config.SCREEN_WIDTH), win_h / float(config.SCREEN_HEIGHT))
        vp_w = max(1, int(round(config.SCREEN_WIDTH * scale)))
        vp_h = max(1, int(round(config.SCREEN_HEIGHT * scale)))
        ox = (win_w - vp_w) // 2
        oy = (win_h - vp_h) // 2
        return ox, oy, vp_w, vp_h, scale

    def _remap_event_to_logical(self, event: pygame.event.Event) -> pygame.event.Event:
        """
        실제 창 크기/모바일 화면비가 1280x720과 다를 때 마우스 및 모바일 터치(FINGER*) 이벤트를
        1280x720 논리 좌표계로 정확히 역변환한다.
        """
        disp = pygame.display.get_surface()
        win_w, win_h = disp.get_size() if disp is not None else config.WINDOW_SIZE
        ox, oy, vp_w, vp_h, _scale = self._compute_viewport(win_w, win_h)

        # 모바일 네이티브 터치 이벤트(FINGERDOWN / FINGERUP / FINGERMOTION) -> 마우스 호환 이벤트 변환
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            fx = float(getattr(event, "x", 0.5)) * win_w
            fy = float(getattr(event, "y", 0.5)) * win_h
            lx = int(round((fx - ox) * config.SCREEN_WIDTH / float(max(1, vp_w))))
            ly = int(round((fy - oy) * config.SCREEN_HEIGHT / float(max(1, vp_h))))
            lx = max(0, min(config.SCREEN_WIDTH - 1, lx))
            ly = max(0, min(config.SCREEN_HEIGHT - 1, ly))
            if event.type == pygame.FINGERDOWN:
                return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (lx, ly), "button": 1, "touch": True})
            if event.type == pygame.FINGERUP:
                return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (lx, ly), "button": 1, "touch": True})
            return pygame.event.Event(pygame.MOUSEMOTION, {"pos": (lx, ly), "rel": (0, 0), "buttons": (1, 0, 0), "touch": True})

        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return event
        pos = getattr(event, "pos", None)
        if not pos:
            return event

        if (win_w, win_h) == (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
            return event

        lx = int(round((pos[0] - ox) * config.SCREEN_WIDTH / float(max(1, vp_w))))
        ly = int(round((pos[1] - oy) * config.SCREEN_HEIGHT / float(max(1, vp_h))))
        lx = max(0, min(config.SCREEN_WIDTH - 1, lx))
        ly = max(0, min(config.SCREEN_HEIGHT - 1, ly))

        attrs = {"pos": (lx, ly)}
        if hasattr(event, "button"):
            attrs["button"] = event.button
        if hasattr(event, "buttons"):
            attrs["buttons"] = event.buttons
        if hasattr(event, "rel"):
            rx = int(round(event.rel[0] * config.SCREEN_WIDTH / float(max(1, vp_w))))
            ry = int(round(event.rel[1] * config.SCREEN_HEIGHT / float(max(1, vp_h))))
            attrs["rel"] = (rx, ry)
        return pygame.event.Event(event.type, attrs)

    # ==========================================================================
    # 이벤트 처리 (옵션 모달 우선 가로채기 지원)
    # ==========================================================================
    def handle_event(self, event: pygame.event.Event) -> None:
        mapped_event = self._remap_event_to_logical(event)

        # F10 단축키: 언제든 옵션 모달 열기/닫기
        if mapped_event.type == pygame.KEYDOWN and mapped_event.key == pygame.K_F10:
            self.toggle_options()
            return

        if self.options_open:
            self._handle_options_event(mapped_event)
            return

        if self.current_scene is not None and hasattr(self.current_scene, "handle_event"):
            self.current_scene.handle_event(mapped_event)

    def _set_volume_by_key(self, skey: str, value: float, play_sample: bool = False) -> None:
        clamped = round(max(0.0, min(1.0, float(value))), 2)
        if not hasattr(self.game_mgr, "settings") or not isinstance(self.game_mgr.settings, dict):
            self.game_mgr.settings = {}
        self.game_mgr.settings[skey] = clamped
        if skey == "master_volume":
            sound_fx.set_master_volume(clamped)
        elif skey == "sfx_volume":
            sound_fx.set_sfx_volume(clamped)
        elif skey == "bgm_volume":
            sound_fx.set_bgm_volume(clamped)
        if play_sample:
            sound_fx.play_ready()
        self._show_opt_status(f"볼륨 설정 반영: {int(round(clamped * 100))}%")

    def _update_slider_from_mouse(self, skey: str, mx: int, play_sample: bool = False) -> None:
        bar_rect = self.opt_slider_rows[skey]["bar"]
        ratio = (mx - bar_rect.x) / float(max(1, bar_rect.width))
        # 5% 단위 스냅으로 깔끔한 조절 지원
        snapped = round(max(0.0, min(1.0, ratio)) * 20.0) / 20.0
        self._set_volume_by_key(skey, snapped, play_sample=play_sample)

    def _apply_resolution_preset(self, width: int, height: int, fullscreen: Optional[bool] = None) -> None:
        if not hasattr(self.game_mgr, "settings") or not isinstance(self.game_mgr.settings, dict):
            self.game_mgr.settings = {}
        fs = bool(self.game_mgr.settings.get("fullscreen", config.FULLSCREEN)) if fullscreen is None else bool(fullscreen)
        self.game_mgr.settings["resolution"] = [int(width), int(height)]
        self.game_mgr.settings["fullscreen"] = fs
        config.apply_display_mode(int(width), int(height), fullscreen=fs)
        self.game_mgr.save_game()
        mode_str = "전체화면" if fs else "창모드"
        self._show_opt_status(f"해상도 적용 완료: {width} × {height} ({mode_str})")

    def _show_opt_status(self, msg: str) -> None:
        self._opt_status_msg = msg
        self._opt_status_timer = 2.2

    def _handle_options_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._opt_hover_pos = event.pos
            if self._dragging_slider in self.opt_slider_rows:
                self._update_slider_from_mouse(self._dragging_slider, event.pos[0], play_sample=False)
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_slider is not None:
                sound_fx.play_ready()
                self._dragging_slider = None
                if self.game_mgr:
                    self.game_mgr.save_game()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close_options()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # 모달 바깥 영역이나 닫기/저장 버튼 클릭 시 닫기
            if (
                not self.opt_panel_rect.collidepoint(mx, my)
                or self.opt_close_btn.collidepoint(mx, my)
                or self.opt_save_close_btn.collidepoint(mx, my)
            ):
                self.close_options()
                return

            # 1) 전체 사운드 ON/OFF 토글
            if self.opt_sound_toggle_btn.collidepoint(mx, my):
                new_flag = not sound_fx.enabled
                sound_fx.set_enabled(new_flag)
                self.game_mgr.settings["sound_enabled"] = new_flag
                self.game_mgr.save_game()
                if new_flag:
                    sound_fx.play_click()
                self._show_opt_status(f"전체 사운드: {'ON (켜짐)' if new_flag else 'OFF (음소거)'}")
                return

            # 2) 배경음악(BGM) ON/OFF 토글
            if self.opt_bgm_toggle_btn.collidepoint(mx, my):
                new_bgm = not sound_fx.bgm_enabled
                sound_fx.set_bgm_enabled(new_bgm)
                self.game_mgr.settings["bgm_enabled"] = new_bgm
                self.game_mgr.save_game()
                sound_fx.play_click()
                self._show_opt_status(f"야시장 배경음악(BGM): {'ON (켜짐)' if new_bgm else 'OFF (꺼짐)'}")
                return

            # 3) 볼륨 슬라이더 & [-10%] / [+10%] 버튼
            for skey, rmap in self.opt_slider_rows.items():
                cur_val = float(self.game_mgr.settings.get(skey, 0.80))
                if rmap["minus"].collidepoint(mx, my):
                    self._set_volume_by_key(skey, cur_val - 0.10, play_sample=True)
                    self.game_mgr.save_game()
                    return
                if rmap["plus"].collidepoint(mx, my):
                    self._set_volume_by_key(skey, cur_val + 0.10, play_sample=True)
                    self.game_mgr.save_game()
                    return
                if rmap["bar"].inflate(0, 12).collidepoint(mx, my):
                    self._dragging_slider = skey
                    self._update_slider_from_mouse(skey, mx, play_sample=True)
                    return

            if self.opt_sfx_test_btn.collidepoint(mx, my):
                sound_fx.play_fanfare()
                self._show_opt_status("🔔 효과음 테스트 재생!")
                return

            # 4) 해상도 프리셋 버튼 4종
            for (rw, rh), r_rect in self.opt_res_btns:
                if r_rect.collidepoint(mx, my):
                    sound_fx.play_click()
                    self._apply_resolution_preset(rw, rh)
                    return

            # 5) 창모드 / 전체화면 전환 버튼
            if self.opt_windowed_btn.collidepoint(mx, my):
                sound_fx.play_click()
                res = self.game_mgr.settings.get("resolution", [config.WINDOW_WIDTH, config.WINDOW_HEIGHT])
                self._apply_resolution_preset(int(res[0]), int(res[1]), fullscreen=False)
                return

            if self.opt_fullscreen_btn.collidepoint(mx, my):
                sound_fx.play_click()
                res = self.game_mgr.settings.get("resolution", [config.WINDOW_WIDTH, config.WINDOW_HEIGHT])
                self._apply_resolution_preset(int(res[0]), int(res[1]), fullscreen=True)
                return

            # 6) 기본값 복원 버튼
            if self.opt_reset_default_btn.collidepoint(mx, my):
                sound_fx.play_cash()
                self.game_mgr.settings.update(
                    {
                        "master_volume": 0.80,
                        "sfx_volume": 0.80,
                        "bgm_volume": 0.45,
                        "sound_enabled": True,
                        "bgm_enabled": True,
                        "resolution": [1280, 720],
                        "fullscreen": False,
                    }
                )
                self.game_mgr.apply_runtime_settings(apply_display=True)
                self.game_mgr.save_game()
                self._show_opt_status("사운드 및 해상도 설정이 권장 기본값으로 복원되었습니다!")
                return

    # ==========================================================================
    # 업데이트 및 렌더링 (가상 캔버스 -> 실제 윈도우 해상도 스케일링)
    # ==========================================================================
    def update(self, dt: float) -> None:
        """현재 활성 씬의 update(dt)를 호출한다. (옵션 모달이 열려 있으면 인게임 타이머 일시정지)"""
        if self._opt_status_timer > 0.0:
            self._opt_status_timer = max(0.0, self._opt_status_timer - dt)

        if self.options_open:
            return

        if self.current_scene is not None and hasattr(self.current_scene, "update"):
            self.current_scene.update(dt)

    def _draw_mobile_bleed_bezels(
        self,
        surface: pygame.Surface,
        ox: int,
        oy: int,
        vp_w: int,
        vp_h: int,
    ) -> None:
        """
        20:9 울트라와이드 스마트폰이나 16:10 태블릿에서 남는 좌우/상하 Safe Area 여백에
        검은 빈 공간 대신 야시장 네온 등불·간판 베젤(Bleed Pillar)을 렌더링한다.
        """
        win_w, win_h = surface.get_size()
        surface.fill((14, 11, 24))
        f_xs = config.get_font(12, bold=True)

        if ox > 4:
            left_r = pygame.Rect(0, 0, ox, win_h)
            right_r = pygame.Rect(ox + vp_w, 0, win_w - (ox + vp_w), win_h)
            for side_r, is_left in ((left_r, True), (right_r, False)):
                pygame.draw.rect(surface, (18, 14, 32), side_r)
                border_x = side_r.right - 2 if is_left else side_r.x
                pygame.draw.line(surface, config.POCHA_ORANGE, (border_x, 0), (border_x, win_h), 2)
                if side_r.width >= 28:
                    cx = side_r.centerx
                    for idx, ly in enumerate(range(70, win_h - 60, 110)):
                        col = config.POCHA_ORANGE if idx % 2 == 0 else config.NEON_PINK
                        pygame.draw.circle(surface, (52, 24, 38), (cx, ly), 14)
                        pygame.draw.circle(surface, col, (cx, ly), 10)
                        pygame.draw.circle(surface, config.GOLD, (cx, ly), 4)
                    lbl = f_xs.render("POCHA", True, config.GOLD)
                    surface.blit(lbl, lbl.get_rect(center=(cx, 28)))

        if oy > 4:
            top_r = pygame.Rect(0, 0, win_w, oy)
            bot_r = pygame.Rect(0, oy + vp_h, win_w, win_h - (oy + vp_h))
            pygame.draw.rect(surface, (18, 14, 32), top_r)
            pygame.draw.rect(surface, (24, 18, 30), bot_r)
            pygame.draw.line(surface, config.GOLD, (0, top_r.bottom - 1), (win_w, top_r.bottom - 1), 2)
            pygame.draw.line(surface, config.POCHA_ORANGE, (0, bot_r.y), (win_w, bot_r.y), 2)

    def draw(self, surface: pygame.Surface) -> None:
        """현재 활성 씬과 전역 옵션 모달을 렌더링하며, 다중 화면비(16:9/20:9/16:10) 등비 뷰포트로 자동 스케일링한다."""
        if self.current_scene is None or not hasattr(self.current_scene, "draw"):
            return

        target_size = surface.get_size()
        logical_size = (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)

        if target_size == logical_size:
            self.current_scene.draw(surface)
            if self.options_open:
                self._draw_options_modal(surface)
        else:
            if self._logical_surface is None or self._logical_surface.get_size() != logical_size:
                self._logical_surface = pygame.Surface(logical_size)
            self.current_scene.draw(self._logical_surface)
            if self.options_open:
                self._draw_options_modal(self._logical_surface)

            ox, oy, vp_w, vp_h, _scale = self._compute_viewport(target_size[0], target_size[1])
            if ox > 0 or oy > 0:
                self._draw_mobile_bleed_bezels(surface, ox, oy, vp_w, vp_h)

            if (vp_w, vp_h) == target_size:
                try:
                    pygame.transform.smoothscale(self._logical_surface, target_size, surface)
                except Exception:
                    scaled = pygame.transform.scale(self._logical_surface, target_size)
                    surface.blit(scaled, (0, 0))
            else:
                try:
                    scaled = pygame.transform.smoothscale(self._logical_surface, (vp_w, vp_h))
                except Exception:
                    scaled = pygame.transform.scale(self._logical_surface, (vp_w, vp_h))
                surface.blit(scaled, (ox, oy))

    # ==========================================================================
    # 전역 옵션 모달 렌더링 (1280x720 논리 캔버스 기준)
    # ==========================================================================
    def _draw_options_modal(self, surface: pygame.Surface) -> None:
        mx, my = self._opt_hover_pos
        art_renderer.draw_alpha_overlay(surface, (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT), (8, 6, 16, 205))

        p = self.opt_panel_rect
        pygame.draw.rect(surface, (24, 20, 38), p, border_radius=18)
        pygame.draw.rect(surface, config.GOLD, p, width=3, border_radius=18)

        title_f = config.get_font(24, bold=True)
        sec_f = config.get_font(17, bold=True)
        btn_f = config.get_font(15, bold=True)
        sub_f = config.get_font(13, bold=True)
        xs_f = config.get_font(12, bold=False)

        # 상단 헤더
        hdr_s = title_f.render("⚙️ 환경 설정 (사운드 조절 & 화면 해상도 설정)", True, config.GOLD)
        surface.blit(hdr_s, (p.x + 28, p.y + 18))
        sub_s = xs_f.render("모든 설정은 변경 즉시 실시간 반영되며 세이브 파일(save_data.json)에 자동 저장됩니다. [단축키: F10 / ESC]", True, config.TEXT_SECONDARY)
        surface.blit(sub_s, (p.x + 30, p.y + 52))

        c_hov = self.opt_close_btn.collidepoint(mx, my)
        pygame.draw.rect(surface, (165, 48, 58) if c_hov else (115, 34, 44), self.opt_close_btn, border_radius=9)
        pygame.draw.rect(surface, config.WHITE, self.opt_close_btn, width=1, border_radius=9)
        ct = btn_f.render("✕ 닫기 [ESC]", True, config.WHITE)
        surface.blit(ct, ct.get_rect(center=self.opt_close_btn.center))

        pygame.draw.line(surface, config.UI_BORDER, (p.x + 24, p.y + 76), (p.right - 24, p.y + 76), 1)

        # ------------------------------------------------------------------
        # 섹션 1: 사운드 조절
        # ------------------------------------------------------------------
        s1_hdr = sec_f.render("🔊 사운드 및 볼륨 설정 (Sound & Audio Mixer)", True, config.NEON_CYAN)
        surface.blit(s1_hdr, (p.x + 30, p.y + 84))

        # 전체 사운드 ON/OFF & BGM ON/OFF 버튼
        snd_on = bool(sound_fx.enabled)
        bgm_on = bool(sound_fx.bgm_enabled)
        for rect, is_on, on_lbl, off_lbl in (
            (self.opt_sound_toggle_btn, snd_on, "🔊 전체 사운드: 켜짐 (ON)", "🔇 전체 사운드: 음소거 (MUTE)"),
            (self.opt_bgm_toggle_btn, bgm_on, "🎵 야시장 배경음(BGM): 켜짐 (ON)", "🎵 야시장 배경음(BGM): 꺼짐 (OFF)"),
        ):
            hov = rect.collidepoint(mx, my)
            bg_c = (38, 112, 78) if is_on else (96, 38, 52)
            if hov:
                bg_c = (52, 138, 96) if is_on else (124, 48, 66)
            pygame.draw.rect(surface, bg_c, rect, border_radius=10)
            pygame.draw.rect(surface, config.TEXT_SUCCESS if is_on else config.TEXT_WARNING, rect, width=2, border_radius=10)
            lt = btn_f.render(on_lbl if is_on else off_lbl, True, config.WHITE)
            surface.blit(lt, lt.get_rect(center=rect.center))

        # 볼륨 슬라이더 3종
        slider_meta = [
            ("master_volume", "🎚️ 마스터 볼륨 (전체 크기)", config.GOLD, float(sound_fx.master_volume)),
            ("sfx_volume", "🔔 효과음 볼륨 (조리·서빙·골드)", config.NEON_CYAN, float(sound_fx.sfx_volume)),
            ("bgm_volume", "🏮 배경음 볼륨 (야시장 BGM)", config.POCHA_ORANGE, float(sound_fx.bgm_volume)),
        ]
        for skey, label_str, bar_col, val in slider_meta:
            rmap = self.opt_slider_rows[skey]
            minus_r = rmap["minus"]
            bar_r = rmap["bar"]
            pct_r = rmap["pct"]
            plus_r = rmap["plus"]

            lbl_s = sub_f.render(label_str, True, config.WHITE if snd_on else config.TEXT_SECONDARY)
            surface.blit(lbl_s, (p.x + 34, minus_r.centery - lbl_s.get_height() // 2))

            # [-] 버튼
            m_hov = minus_r.collidepoint(mx, my)
            pygame.draw.rect(surface, config.UI_BUTTON_HOVER if m_hov else config.UI_PANEL, minus_r, border_radius=8)
            pygame.draw.rect(surface, config.GOLD if m_hov else config.UI_BORDER, minus_r, width=1, border_radius=8)
            mt = btn_f.render("-10%", True, config.WHITE)
            surface.blit(mt, mt.get_rect(center=minus_r.center))

            # 슬라이더 게이지 바
            pygame.draw.rect(surface, (16, 14, 26), bar_r, border_radius=11)
            fill_w = int(bar_r.width * max(0.0, min(1.0, val)))
            if fill_w > 0:
                active_col = bar_col if snd_on else (95, 95, 112)
                pygame.draw.rect(surface, active_col, (bar_r.x, bar_r.y, fill_w, bar_r.height), border_radius=11)
            pygame.draw.rect(surface, config.WHITE if self._dragging_slider == skey else config.UI_BORDER, bar_r, width=2, border_radius=11)

            # 슬라이더 손잡이(Knob)
            knob_x = max(bar_r.x + 8, min(bar_r.right - 8, bar_r.x + fill_w))
            pygame.draw.circle(surface, config.WHITE, (knob_x, bar_r.centery), 10)
            pygame.draw.circle(surface, bar_col, (knob_x, bar_r.centery), 6)

            # 독립 퍼센트 배지 박스 (손잡이와 절대 겹치지 않음)
            pygame.draw.rect(surface, (20, 18, 32), pct_r, border_radius=7)
            pygame.draw.rect(surface, bar_col if snd_on else config.UI_BORDER, pct_r, width=1, border_radius=7)
            pct_s = sub_f.render(f"{int(round(val * 100))}%", True, bar_col if snd_on else config.TEXT_SECONDARY)
            surface.blit(pct_s, pct_s.get_rect(center=pct_r.center))

            # [+] 버튼
            p_hov = plus_r.collidepoint(mx, my)
            pygame.draw.rect(surface, config.UI_BUTTON_HOVER if p_hov else config.UI_PANEL, plus_r, border_radius=8)
            pygame.draw.rect(surface, config.GOLD if p_hov else config.UI_BORDER, plus_r, width=1, border_radius=8)
            pt = btn_f.render("+10%", True, config.WHITE)
            surface.blit(pt, pt.get_rect(center=plus_r.center))

        # 효과음 테스트 버튼
        t_hov = self.opt_sfx_test_btn.collidepoint(mx, my)
        pygame.draw.rect(surface, (52, 88, 138) if t_hov else (38, 62, 98), self.opt_sfx_test_btn, border_radius=8)
        pygame.draw.rect(surface, config.NEON_CYAN, self.opt_sfx_test_btn, width=1, border_radius=8)
        tt = sub_f.render("🔔 테스트", True, config.WHITE)
        surface.blit(tt, tt.get_rect(center=self.opt_sfx_test_btn.center))

        pygame.draw.line(surface, config.UI_BORDER, (p.x + 24, p.y + 346), (p.right - 24, p.y + 346), 1)

        # ------------------------------------------------------------------
        # 섹션 2: 화면 해상도 및 창모드/전체화면 설정
        # ------------------------------------------------------------------
        cur_res = (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        cur_fs = bool(config.FULLSCREEN)
        s2_hdr = sec_f.render(
            f"🖥️ 화면 해상도 및 디스플레이 모드 (현재: {cur_res[0]}×{cur_res[1]} · {'전체화면' if cur_fs else '창모드'})",
            True,
            config.GOLD,
        )
        surface.blit(s2_hdr, (p.x + 30, p.y + 356))

        res_f = config.get_font(12, bold=True)
        for (rw, rh), r_rect in self.opt_res_btns:
            is_sel = (rw, rh) == cur_res
            r_hov = r_rect.collidepoint(mx, my)
            bg_c = config.UI_BUTTON_ACTIVE if is_sel else (config.UI_BUTTON_HOVER if r_hov else config.UI_PANEL)
            border_c = config.GOLD if is_sel else (config.UI_HIGHLIGHT if r_hov else config.UI_BORDER)
            pygame.draw.rect(surface, bg_c, r_rect, border_radius=9)
            pygame.draw.rect(surface, border_c, r_rect, width=2 if is_sel else 1, border_radius=9)

            res_label = config.RESOLUTION_LABELS.get((rw, rh), f"{rw} × {rh}")
            prefix = "✅ " if is_sel else "📱 "
            rt = res_f.render(f"{prefix}{res_label}", True, config.WHITE if is_sel else config.TEXT_PRIMARY)
            surface.blit(rt, rt.get_rect(center=r_rect.center))

        # 창모드 / 전체화면 토글 버튼
        for rect, is_active, label_str in (
            (self.opt_windowed_btn, not cur_fs, "🪟 창모드 (Windowed Mode)"),
            (self.opt_fullscreen_btn, cur_fs, "🖥️ 전체화면 (Fullscreen Mode)"),
        ):
            hov = rect.collidepoint(mx, my)
            bg_c = (48, 98, 142) if is_active else (config.UI_BUTTON_HOVER if hov else config.UI_PANEL)
            pygame.draw.rect(surface, bg_c, rect, border_radius=9)
            pygame.draw.rect(surface, config.NEON_CYAN if is_active else config.UI_BORDER, rect, width=2 if is_active else 1, border_radius=9)
            ft = sub_f.render(f"{'✅ ' if is_active else ''}{label_str}", True, config.WHITE)
            surface.blit(ft, ft.get_rect(center=rect.center))

        # ------------------------------------------------------------------
        # 하단 바: 기본값 복원 / 상태 메시지 / 저장 및 닫기
        # ------------------------------------------------------------------
        d_hov = self.opt_reset_default_btn.collidepoint(mx, my)
        pygame.draw.rect(surface, config.UI_BUTTON_HOVER if d_hov else config.UI_PANEL, self.opt_reset_default_btn, border_radius=9)
        pygame.draw.rect(surface, config.TEXT_WARNING if d_hov else config.UI_BORDER, self.opt_reset_default_btn, width=1, border_radius=9)
        dt_s = sub_f.render("🔄 권장 기본값 복원 (1280×720 / 80%)", True, config.TEXT_PRIMARY)
        surface.blit(dt_s, dt_s.get_rect(center=self.opt_reset_default_btn.center))

        s_hov = self.opt_save_close_btn.collidepoint(mx, my)
        pygame.draw.rect(surface, (46, 152, 92) if s_hov else (36, 122, 74), self.opt_save_close_btn, border_radius=9)
        pygame.draw.rect(surface, config.GOLD, self.opt_save_close_btn, width=2, border_radius=9)
        st_s = btn_f.render("✅ 설정 저장 및 닫기", True, config.WHITE)
        surface.blit(st_s, st_s.get_rect(center=self.opt_save_close_btn.center))

        if self._opt_status_timer > 0.0 and self._opt_status_msg:
            msg_s = sub_f.render(f"✨ {self._opt_status_msg}", True, config.NEON_GREEN)
            surface.blit(msg_s, (p.x + 320, self.opt_save_close_btn.centery - msg_s.get_height() // 2))
