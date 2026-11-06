"""
core/scene_manager.py
'전세계 길거리 음식 포차 타이쿤' 씬(Scene) 상태 전환, 가상 해상도(1280x720 -> 실제 창 크기) 자동 스케일링,
마우스 좌표 역변환, 그리고 전역 옵션 모달(사운드 볼륨 조절 & 해상도/전체화면 조절) 매니저.
지원 씬: "title", "prep", "play", "result", "duel_lobby", "duel_play", "duel_result"
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
import pygame

import config
from core import art_renderer
from core.effects import sound_fx
from core.game_manager import GameManager, game_manager


# ==============================================================================
# 프로그래시브 포차 로딩 멘트 10종 & 매칭 음식/조리기구 일러스트 테마
# ==============================================================================
LOADING_THEMES: List[Dict[str, Any]] = [
    {
        "step": 1,
        "short": "붕어빵 굽는중",
        "message": "🐟 황금빛 붕어빵 굽는 중...",
        "sub": "무쇠 붕어빵 틀을 달구고 달콤한 통단팥·슈크림 반죽을 붓고 있습니다!",
        "tip": "TIP: 초록색(READY) 게이지가 떴을 때 꺼내면 바삭한 황금 붕어빵 완성!",
        "foods": ("bungeoppang_redbean", "bungeoppang_cream"),
        "country": "KR",
        "appliance": "mold_bungeo",
        "station_title": "황금 붕어빵 2구 무쇠 틀",
        "accent": (255, 168, 52),
    },
    {
        "step": 2,
        "short": "오뎅 국물 내는중",
        "message": "🍢 뜨끈한 오뎅 국물 내는 중...",
        "sub": "멸치와 다시마, 무를 푹 우려내 진한 포장마차 어묵 육수를 끓이고 있습니다!",
        "tip": "TIP: 음료·국물 디스펜서는 자동으로 충전되며 터치 즉시 서빙됩니다!",
        "foods": ("odeng_soup", "sikhye"),
        "country": "KR",
        "appliance": "pot_odeng",
        "station_title": "포차 뜨끈 어묵·식혜 온장고",
        "accent": (255, 214, 92),
    },
    {
        "step": 3,
        "short": "닭꼬치 굽는중",
        "message": "🔥 참숯 피우고 대파 닭꼬치 굽는 중...",
        "sub": "타오르는 직화 숯불 위에 닭꼬치를 올리고 특제 소스를 발라 초벌 중입니다!",
        "tip": "TIP: 구운 꼬치를 트레이에 옮긴 뒤 매운양념·데리야키·파채 토핑을 얹어보세요!",
        "foods": ("skewer_greenonion", "skewer_spicy"),
        "country": "KR",
        "appliance": "grill_skewer",
        "station_title": "직화 참숯 대파 닭꼬치 그릴",
        "accent": (255, 96, 64),
    },
    {
        "step": 4,
        "short": "떡볶이 조리는중",
        "message": "🌶️ 무쇠 철판에 매콤 떡볶이 조리는 중...",
        "sub": "고추장 비법 양념에 쫄깃한 쌀떡과 어묵을 넣고 보글보글 졸이고 있습니다!",
        "tip": "TIP: 대량 조리 팬은 한 번 조리로 3~5인분을 연속해서 덜어낼 수 있습니다!",
        "foods": ("tteokbokki_cheese", "tteokbokki_gimmari"),
        "country": "KR",
        "appliance": "pan_tteokbokki",
        "station_title": "포차 대형 무쇠 떡볶이 철판",
        "accent": (255, 68, 92),
    },
    {
        "step": 5,
        "short": "타코야키 굴리는중",
        "message": "🐙 오사카 무쇠판에 타코야키 굴리는 중...",
        "sub": "도톤보리 야타이 무쇠판에서 문어가 큼직하게 든 타코야키를 동글동글 굴리는 중!",
        "tip": "TIP: 가쓰오부시와 마요네즈 토핑을 얹으면 일본 야시장 단골손님 대만족!",
        "foods": ("takoyaki_mayo", "yakisoba_egg"),
        "country": "JP",
        "appliance": "mold_takoyaki",
        "station_title": "오사카 도톤보리 타코야키 주물판",
        "accent": (255, 112, 184),
    },
    {
        "step": 6,
        "short": "타코 또띠아 굽는중",
        "message": "🌮 멕시코 화로에 타코 또띠아 굽는 중...",
        "sub": "고소한 옥수수 또띠아를 굽고 신선한 살사 소스와 과카몰리를 다지고 있습니다!",
        "tip": "TIP: 연속 서빙 콤보(COMBO)가 높아질수록 손님들이 두둑한 팁을 남깁니다!",
        "foods": ("taco_salsa", "taco_guac"),
        "country": "MX",
        "appliance": "grill_taco",
        "station_title": "멕시코 피에스타 타코 화로 철판",
        "accent": (72, 238, 142),
    },
    {
        "step": 7,
        "short": "흑당 버블티 삶는중",
        "message": "🧋 대만 야시장 흑당 버블티 삶는 중...",
        "sub": "스린 야시장 비법 흑당 시럽에 쫀득한 타피오카 펄을 뭉근하게 졸이는 중!",
        "tip": "TIP: 맛집 유튜버(VIP) 주문을 완성하면 12초간 골드 보너스 피버 타임 발동!",
        "foods": ("boba_milktea", "jipai_mala"),
        "country": "TW",
        "appliance": "pot_boba",
        "station_title": "타이베이 스린 흑당 버블 솥",
        "accent": (245, 186, 102),
    },
    {
        "step": 8,
        "short": "마라탕 육수 끓이는중",
        "message": "🥘 사천 마라탕 육수 끓이고 양꼬치 굽는 중...",
        "sub": "얼얼한 화자오 마라 육수를 우려내고 양꼬치에 고소한 쯔란을 뿌리는 중입니다!",
        "tip": "TIP: 잘못 조합한 접시는 접시 우측 상단 [X] 배지를 터치해 즉시 비울 수 있어요!",
        "foods": ("malatang_beef", "yangchuan_cumin"),
        "country": "CN",
        "appliance": "pot_mala",
        "station_title": "청두 사천 마라 홍탕 대형 가마솥",
        "accent": (255, 78, 78),
    },
    {
        "step": 9,
        "short": "탄두리 화덕 달구는중",
        "message": "🍗 화덕 달궈 탄두리 치킨 & 버거 굽는 중...",
        "sub": "황토 화덕에서 향신료 가득 탄두리 치킨과 육즙 가득 스매시 버거를 굽는 중!",
        "tip": "TIP: 포차 마스터마다 고유 패시브와 위기 탈출 액티브 스킬을 보유하고 있습니다!",
        "foods": ("tandoori_masala", "smash_burger_bacon"),
        "country": "IN",
        "appliance": "oven_tandoor",
        "station_title": "전통 탄두르 화덕 & 스매시 그릴",
        "accent": (255, 188, 48),
    },
    {
        "step": 10,
        "short": "포장마차 전구 켜는중",
        "message": "🏮 포장마차 알전구 켜고 손님 맞이 준비 중...",
        "sub": "천막 간판에 불을 밝히고 전 세계 야시장 미식가들을 맞이할 준비를 마쳤습니다!",
        "tip": "TIP: 32강 월드 포차 그랑프리에서 전 세계 32인 마스터를 꺾고 우승에 도전하세요!",
        "foods": ("churrasco_garlic", "shashlik_onion"),
        "country": "BR",
        "appliance": "pocha_tent",
        "station_title": "월드 스트리트 나이트마켓 포차 오픈!",
        "accent": (64, 232, 255),
    },
]


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
        self._portrait_surface: Optional[pygame.Surface] = None
        self._manual_orientation_override: bool = False
        self._browser_orient_timer: float = 0.2

        # 전역 옵션 모달 상태
        self.options_open: bool = False
        self._opt_hover_pos: Tuple[int, int] = (0, 0)
        self._dragging_slider: Optional[str] = None
        self._opt_status_msg: str = ""
        self._opt_status_timer: float = 0.0
        self._setup_options_rects()

        # 프로그래시브 로딩 화면 상태 (10종 멘트 & 매칭 조리 일러스트 로딩 바)
        self.loading_active: bool = False
        self.loading_progress: float = 0.0
        self.loading_duration: float = 1.10
        self.loading_theme_idx: int = 0
        self._loading_rotation_counter: int = 0
        self._loading_tick: float = 0.0

        config.sync_browser_display_and_fullscreen(None)
        self._register_default_scenes()

        if initial_scene:
            self.change_scene(initial_scene, show_loading=False)

    def start_loading(
        self,
        duration: float = 1.10,
        theme_index: Optional[int] = None,
    ) -> None:
        """
        10종 프로그래시브 조리 멘트와 어울리는 음식·조리기구 일러스트 로딩 바 화면을 시작한다.
        로딩 화면이 나올 때마다 다음 테마로 순환하며, 진행률(0~100%)에 따라 프로그래시브 멘트가 변화한다.
        """
        self.loading_active = True
        self.loading_progress = 0.0
        self.loading_duration = max(0.25, float(duration))
        if theme_index is not None:
            self.loading_theme_idx = int(theme_index) % len(LOADING_THEMES)
        else:
            self.loading_theme_idx = self._loading_rotation_counter % len(LOADING_THEMES)
            self._loading_rotation_counter = (self._loading_rotation_counter + 1) % len(LOADING_THEMES)

    def finish_loading(self) -> None:
        """진행 중인 로딩 오버레이를 즉시 완료 처리한다."""
        self.loading_active = False
        self.loading_progress = 1.0

    @property
    def is_portrait_mode(self) -> bool:
        """현재 디스플레이가 세로(Portrait, 높이 > 너비) 모드인지 여부를 반환한다."""
        disp = pygame.display.get_surface()
        win_w, win_h = disp.get_size() if disp is not None else config.WINDOW_SIZE
        return win_h > win_w

    def toggle_orientation(self) -> None:
        """가로 모드(1280×720)와 세로 모드(720×1280)를 원터치로 즉시 전환한다."""
        sound_fx.play_click()
        self._manual_orientation_override = True
        if self.is_portrait_mode:
            self._apply_resolution_preset(1280, 720)
        else:
            self._apply_resolution_preset(720, 1280)

    def toggle_fullscreen(self) -> None:
        """전체화면(웹앱의 경우 브라우저 전체화면 API 포함)과 창모드를 즉시 전환한다."""
        sound_fx.play_click()
        new_fs = not bool(config.FULLSCREEN)
        self._apply_resolution_preset(config.WINDOW_WIDTH, config.WINDOW_HEIGHT, fullscreen=new_fs)

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

        # 4) 가로/세로 회전 & 창모드 / 브라우저 전체화면 전환 버튼
        self.opt_rotate_btn = pygame.Rect(px + 34, py + 494, 248, 40)
        self.opt_windowed_btn = pygame.Rect(px + 294, py + 494, 248, 40)
        self.opt_fullscreen_btn = pygame.Rect(px + 554, py + 494, 252, 40)

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

        had_prev_scene = self.current_scene is not None
        if had_prev_scene and hasattr(self.current_scene, "on_exit"):
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

        if bool(kwargs.get("show_loading", False)):
            self.start_loading(
                duration=float(kwargs.get("loading_duration", 1.05)),
                theme_index=kwargs.get("loading_theme"),
            )
        return self.current_scene

    switch_scene = change_scene
    set_scene = change_scene
    goto = change_scene

    # ==========================================================================
    # 다중 화면비(가로 16:9 / 20:9 & 세로 9:16 / 9:18) 등비 뷰포트 계산 및 터치·마우스 좌표 역변환
    # ==========================================================================
    @staticmethod
    def _compute_viewport(win_w: int, win_h: int) -> Tuple[int, int, int, int, float]:
        """
        실제 디스플레이 해상도(win_w, win_h) 안에서 가로 모드(1280x720) 또는 세로 모드(720x1280)가
        찌그러지지 않는 최대 등비 뷰포트(ox, oy, vp_w, vp_h, scale)를 반환한다.
        """
        if win_w <= 0 or win_h <= 0:
            return 0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT, 1.0
        base_w = config.PORTRAIT_WIDTH if win_h > win_w else config.SCREEN_WIDTH
        base_h = config.PORTRAIT_HEIGHT if win_h > win_w else config.SCREEN_HEIGHT
        scale = min(win_w / float(base_w), win_h / float(base_h))
        vp_w = max(1, int(round(base_w * scale)))
        vp_h = max(1, int(round(base_h * scale)))
        ox = (win_w - vp_w) // 2
        oy = (win_h - vp_h) // 2
        return ox, oy, vp_w, vp_h, scale

    def _get_portrait_region_mappings(self) -> List[Tuple[pygame.Rect, pygame.Rect, Tuple[int, int, int]]]:
        """
        세로 모드(720x1280)에서 1280x720 논리 화면의 핵심 구역(src_rect)을
        세로 화면(dst_rect)으로 찌그러짐이나 잘림 없이 재배치하는 매핑 목록을 반환한다.
        """
        sc = self.current_scene
        has_modal = (
            self.loading_active
            or self.options_open
            or getattr(sc, "active_cutscene", None) is not None
            or bool(getattr(sc, "paused", False))
            or bool(getattr(sc, "show_roster_modal", False))
            or self.current_scene_name in ("result", "duel_result", "duel_lobby")
        )
        if has_modal:
            return [
                (
                    pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
                    pygame.Rect(8, 250, 704, 780),
                    config.GOLD,
                )
            ]

        if self.current_scene_name in ("play", "duel_play"):
            return [
                # 1) 상단 HUD
                (pygame.Rect(0, 0, 1280, 64), pygame.Rect(8, 8, 704, 54), config.GOLD),
                # 2) 손님 대기 카운터 & 스토리 다시보기
                (pygame.Rect(190, 64, 1090, 286), pygame.Rect(8, 68, 704, 198), config.UI_BORDER),
                # 3) 좌측 조리 기구 2종 (① 몰드 구이 + ② 음료 디스펜서)
                (pygame.Rect(10, 350, 456, 362), pygame.Rect(8, 272, 348, 484), config.POCHA_ORANGE),
                # 4) 우측 조리 기구 2종 (④ 직화 그릴 + ⑤ 대량 조리 팬)
                (pygame.Rect(814, 350, 456, 362), pygame.Rect(364, 272, 348, 484), config.POCHA_ORANGE),
                # 5) 하단 좌측: 마스터 아바타 & 원터치 액티브 스킬 버튼
                (pygame.Rect(8, 70, 182, 270), pygame.Rect(8, 764, 232, 504), config.NEON_CYAN),
                # 6) 하단 우측: 중앙 조립 & 토핑 트레이 (가장 자주 터치하는 영역을 하단 엄지 존에 크게 배치)
                (pygame.Rect(468, 350, 344, 362), pygame.Rect(248, 764, 464, 504), config.GOLD),
            ]

        if self.current_scene_name == "title":
            return [
                # 1) 상단 9개국 배경 미리보기 버튼 바
                (pygame.Rect(615, 14, 635, 38), pygame.Rect(12, 12, 696, 40), config.UI_BORDER),
                # 2) 메인 타이틀 네온 배너
                (pygame.Rect(36, 52, 1208, 146), pygame.Rect(12, 58, 696, 132), config.GOLD),
                # 3) 현재 포차 마스터 프로필 카드 (정방형 비율 유지)
                (pygame.Rect(36, 210, 348, 348), pygame.Rect(150, 196, 420, 292), config.UI_BORDER),
                # 4) 게임 모드 선택 카드 2종 (월드 투어 & 글로벌 통합)
                (pygame.Rect(400, 210, 844, 348), pygame.Rect(12, 496, 696, 500), config.POCHA_ORANGE),
                # 5) 모바일 터치 조작 가이드 바
                (pygame.Rect(36, 568, 1208, 68), pygame.Rect(12, 1004, 696, 90), config.UI_BORDER),
                # 6) 하단 유틸리티 & 가로·세로/전체화면 전환 버튼 바
                (pygame.Rect(36, 644, 888, 54), pygame.Rect(12, 1102, 696, 98), config.NEON_CYAN),
            ]

        if self.current_scene_name == "prep":
            active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
            split_map = {"character": 852, "chapter": 641, "upgrade": 652, "tournament": 620}
            split_x = split_map.get(active_tab, 641)
            return [
                # 1) 상단 네비게이션 및 보유 골드 바
                (pygame.Rect(24, 10, 1232, 54), pygame.Rect(8, 8, 704, 54), config.GOLD),
                # 2) 4대 메인 탭 버튼 바
                (pygame.Rect(24, 68, 1232, 54), pygame.Rect(8, 68, 704, 56), config.UI_BORDER),
                # 3) 국가 필터 및 페이지 전환 서브 헤더
                (pygame.Rect(28, 126, 1224, 48), pygame.Rect(8, 130, 704, 48), config.UI_BORDER),
                # 4) 메인 컨텐츠 상단 (좌측 영역)
                (pygame.Rect(28, 174, split_x - 28, 456), pygame.Rect(8, 184, 704, 484), config.POCHA_ORANGE),
                # 5) 메인 컨텐츠 하단 (우측 영역)
                (pygame.Rect(split_x, 174, 1252 - split_x, 456), pygame.Rect(8, 674, 704, 466), config.NEON_CYAN),
                # 6) 하단 [오늘 영업 시작!] 액션 바
                (pygame.Rect(24, 636, 1232, 72), pygame.Rect(8, 1148, 704, 120), config.GOLD),
            ]

        return [
            (
                pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
                pygame.Rect(8, 250, 704, 780),
                config.GOLD,
            )
        ]

    def _map_window_point_to_logical(self, wx: float, wy: float, win_w: int, win_h: int) -> Tuple[int, int]:
        """실제 윈도우 좌표(wx, wy)를 가로/세로 모드에 맞춰 1280x720 논리 좌표(lx, ly)로 변환한다."""
        ox, oy, vp_w, vp_h, _scale = self._compute_viewport(win_w, win_h)
        if win_h > win_w:
            # 세로 모드(720x1280 뷰포트) -> 영역 매핑 역변환
            px = (wx - ox) * config.PORTRAIT_WIDTH / float(max(1, vp_w))
            py = (wy - oy) * config.PORTRAIT_HEIGHT / float(max(1, vp_h))
            for src_r, dst_r, _bcol in self._get_portrait_region_mappings():
                if dst_r.inflate(4, 4).collidepoint(int(round(px)), int(round(py))):
                    rx = (px - dst_r.x) / float(max(1, dst_r.width))
                    ry = (py - dst_r.y) / float(max(1, dst_r.height))
                    rx = max(0.0, min(1.0, rx))
                    ry = max(0.0, min(1.0, ry))
                    lx = int(round(src_r.x + rx * src_r.width))
                    ly = int(round(src_r.y + ry * src_r.height))
                    return (
                        max(0, min(config.SCREEN_WIDTH - 1, lx)),
                        max(0, min(config.SCREEN_HEIGHT - 1, ly)),
                    )
            return (-999, -999)

        lx = int(round((wx - ox) * config.SCREEN_WIDTH / float(max(1, vp_w))))
        ly = int(round((wy - oy) * config.SCREEN_HEIGHT / float(max(1, vp_h))))
        return (
            max(0, min(config.SCREEN_WIDTH - 1, lx)),
            max(0, min(config.SCREEN_HEIGHT - 1, ly)),
        )

    def _remap_event_to_logical(self, event: pygame.event.Event) -> pygame.event.Event:
        """
        실제 창 크기/모바일 화면비(가로·세로 포함)가 1280x720과 다를 때 마우스 및 모바일 터치(FINGER*) 이벤트를
        1280x720 논리 좌표계로 정확히 역변환한다.
        """
        disp = pygame.display.get_surface()
        win_w, win_h = disp.get_size() if disp is not None else config.WINDOW_SIZE
        ox, oy, vp_w, vp_h, _scale = self._compute_viewport(win_w, win_h)

        # 모바일 네이티브 터치 이벤트(FINGERDOWN / FINGERUP / FINGERMOTION) -> 마우스 호환 이벤트 변환
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            fx = float(getattr(event, "x", 0.5)) * win_w
            fy = float(getattr(event, "y", 0.5)) * win_h
            lx, ly = self._map_window_point_to_logical(fx, fy, win_w, win_h)
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

        lx, ly = self._map_window_point_to_logical(float(pos[0]), float(pos[1]), win_w, win_h)

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

        # F10 단축키: 언제든 옵션 모달 열기/닫기, F11 단축키: 전체화면 전환
        if mapped_event.type == pygame.KEYDOWN:
            if mapped_event.key == pygame.K_F10:
                self.toggle_options()
                return
            if mapped_event.key == pygame.K_F11:
                self.toggle_fullscreen()
                return

        if self.loading_active:
            if mapped_event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN) and self.loading_progress >= 0.35:
                self.finish_loading()
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
        orient_str = "세로 모드" if int(height) > int(width) else "가로 모드"
        mode_str = "전체화면" if fs else "창모드"
        self._show_opt_status(f"화면 적용 완료: {width}×{height} ({orient_str} · {mode_str})")

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

            # 4) 해상도 프리셋 버튼 6종 (가로 & 세로)
            for (rw, rh), r_rect in self.opt_res_btns:
                if r_rect.collidepoint(mx, my):
                    sound_fx.play_click()
                    self._manual_orientation_override = True
                    self._apply_resolution_preset(rw, rh)
                    return

            # 5) 가로/세로 방향 전환 & 창모드 / 전체화면 전환 버튼
            if self.opt_rotate_btn.collidepoint(mx, my):
                self.toggle_orientation()
                return

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
                self._manual_orientation_override = False
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
    # 업데이트 및 렌더링 (가로 1280x720 & 세로 720x1280 자동/수동 레이아웃 스케일링)
    # ==========================================================================
    def _poll_browser_viewport_orientation(self, dt: float) -> None:
        """웹앱(emscripten) 환경에서 스마트폰 가로/세로 회전 시 자동으로 레이아웃을 전환한다."""
        import sys
        if sys.platform != "emscripten" or self._manual_orientation_override:
            return
        self._browser_orient_timer -= dt
        if self._browser_orient_timer > 0.0:
            return
        self._browser_orient_timer = 0.45
        try:
            import platform
            iw = int(platform.window.innerWidth)
            ih = int(platform.window.innerHeight)
            if iw > 0 and ih > 0:
                if ih > iw * 1.06 and not self.is_portrait_mode:
                    config.apply_display_mode(720, 1280, fullscreen=config.FULLSCREEN)
                elif iw >= ih * 1.04 and self.is_portrait_mode:
                    config.apply_display_mode(1280, 720, fullscreen=config.FULLSCREEN)
        except Exception:
            pass

    def update(self, dt: float) -> None:
        """현재 활성 씬의 update(dt)를 호출한다. (옵션 모달 또는 로딩 중이면 인게임 타이머 일시정지)"""
        self._poll_browser_viewport_orientation(dt)
        if self._opt_status_timer > 0.0:
            self._opt_status_timer = max(0.0, self._opt_status_timer - dt)

        if self.loading_active:
            self._loading_tick += dt
            self.loading_progress += dt / max(0.25, self.loading_duration)
            if self.loading_progress >= 1.0:
                self.finish_loading()
            return

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
            if top_r.height >= 28:
                for idx, lx in enumerate(range(60, win_w - 50, 110)):
                    col = config.GOLD if idx % 2 == 0 else config.POCHA_ORANGE
                    pygame.draw.circle(surface, col, (lx, top_r.centery), 8)

    def _compose_portrait_surface(self, logical_surf: pygame.Surface, portrait_surf: pygame.Surface) -> None:
        """1280x720 논리 화면을 720x1280 세로 모바일 전용 레이아웃으로 합성한다."""
        portrait_surf.fill((16, 13, 28))
        mappings = self._get_portrait_region_mappings()

        # 모달/결과 화면 등 단일 중앙 배치일 때 상하단 야시장 네온 배너 장식
        if len(mappings) == 1:
            hdr_f = config.get_font(22, bold=True)
            sub_f = config.get_font(14, bold=True)
            hs = hdr_f.render("🏮 전세계 길거리 음식 포차 타이쿤 (세로 모드)", True, config.GOLD)
            ss = sub_f.render("화면을 터치하여 진행하세요 · [⚙️ 옵션]에서 가로/세로 및 전체화면 전환 가능", True, config.NEON_CYAN)
            portrait_surf.blit(hs, hs.get_rect(center=(config.PORTRAIT_WIDTH // 2, 110)))
            portrait_surf.blit(ss, ss.get_rect(center=(config.PORTRAIT_WIDTH // 2, 152)))
            for idx, lx in enumerate(range(80, config.PORTRAIT_WIDTH - 60, 110)):
                col = config.POCHA_ORANGE if idx % 2 == 0 else config.NEON_PINK
                pygame.draw.circle(portrait_surf, col, (lx, 56), 10)
                pygame.draw.circle(portrait_surf, config.GOLD, (lx, 56), 4)
                pygame.draw.circle(portrait_surf, col, (lx, 1140), 10)
                pygame.draw.circle(portrait_surf, config.GOLD, (lx, 1140), 4)

        for src_r, dst_r, border_col in mappings:
            clipped_src = src_r.clip(logical_surf.get_rect())
            if clipped_src.width <= 0 or clipped_src.height <= 0:
                continue
            sub = logical_surf.subsurface(clipped_src)
            try:
                scaled_part = pygame.transform.smoothscale(sub, dst_r.size)
            except Exception:
                scaled_part = pygame.transform.scale(sub, dst_r.size)
            portrait_surf.blit(scaled_part, dst_r.topleft)
            pygame.draw.rect(portrait_surf, border_col, dst_r, width=2, border_radius=10)

    def draw(self, surface: pygame.Surface) -> None:
        """현재 활성 씬과 전역 옵션 모달을 렌더링하며, 가로(16:9/20:9) 및 세로(9:16/9:18) 화면비로 자동 스케일링한다."""
        if self.current_scene is None or not hasattr(self.current_scene, "draw"):
            return

        target_size = surface.get_size()
        logical_size = (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)

        if target_size == logical_size:
            self.current_scene.draw(surface)
            if self.loading_active:
                self._draw_loading_overlay(surface)
            if self.options_open:
                self._draw_options_modal(surface)
            return

        if self._logical_surface is None or self._logical_surface.get_size() != logical_size:
            self._logical_surface = pygame.Surface(logical_size)
        self.current_scene.draw(self._logical_surface)
        if self.loading_active:
            self._draw_loading_overlay(self._logical_surface)
        if self.options_open:
            self._draw_options_modal(self._logical_surface)

        ox, oy, vp_w, vp_h, _scale = self._compute_viewport(target_size[0], target_size[1])
        if ox > 0 or oy > 0:
            self._draw_mobile_bleed_bezels(surface, ox, oy, vp_w, vp_h)

        # 세로 모드(Portrait, win_h > win_w)인 경우 720x1280 세로 레이아웃 캔버스로 재조합 후 출력
        if target_size[1] > target_size[0]:
            portrait_size = (config.PORTRAIT_WIDTH, config.PORTRAIT_HEIGHT)
            if self._portrait_surface is None or self._portrait_surface.get_size() != portrait_size:
                self._portrait_surface = pygame.Surface(portrait_size)
            self._compose_portrait_surface(self._logical_surface, self._portrait_surface)
            src_canvas = self._portrait_surface
        else:
            src_canvas = self._logical_surface

        if (vp_w, vp_h) == target_size and target_size == src_canvas.get_size():
            surface.blit(src_canvas, (0, 0))
        elif (vp_w, vp_h) == target_size:
            try:
                pygame.transform.smoothscale(src_canvas, target_size, surface)
            except Exception:
                scaled = pygame.transform.scale(src_canvas, target_size)
                surface.blit(scaled, (0, 0))
        else:
            try:
                scaled = pygame.transform.smoothscale(src_canvas, (vp_w, vp_h))
            except Exception:
                scaled = pygame.transform.scale(src_canvas, (vp_w, vp_h))
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
        hdr_s = title_f.render("⚙️ 환경 설정 (사운드 조절 & 가로·세로 화면 / 전체화면 설정)", True, config.GOLD)
        surface.blit(hdr_s, (p.x + 28, p.y + 18))
        sub_s = xs_f.render("모든 설정은 변경 즉시 실시간 반영되며 자동 저장됩니다. [단축키: F10 옵션 / F11 전체화면]", True, config.TEXT_SECONDARY)
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
        # 섹션 2: 화면 해상도(가로/세로) 및 창모드/브라우저 전체화면 설정
        # ------------------------------------------------------------------
        cur_res = (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        cur_fs = bool(config.FULLSCREEN)
        orient_lbl = "세로 모드" if cur_res[1] > cur_res[0] else "가로 모드"
        s2_hdr = sec_f.render(
            f"🖥️ 화면 방향 및 해상도 설정 (현재: {cur_res[0]}×{cur_res[1]} {orient_lbl} · {'전체화면' if cur_fs else '창모드'})",
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

        # 가로/세로 즉시 회전 & 창모드 / 브라우저 전체화면 토글 버튼
        rot_hov = self.opt_rotate_btn.collidepoint(mx, my)
        pygame.draw.rect(surface, (42, 116, 86) if rot_hov else (32, 88, 66), self.opt_rotate_btn, border_radius=9)
        pygame.draw.rect(surface, config.NEON_GREEN, self.opt_rotate_btn, width=2, border_radius=9)
        rot_txt = "🔄 가로모드로 전환" if self.is_portrait_mode else "🔄 세로모드로 전환"
        rt_s = sub_f.render(rot_txt, True, config.WHITE)
        surface.blit(rt_s, rt_s.get_rect(center=self.opt_rotate_btn.center))

        for rect, is_active, label_str in (
            (self.opt_windowed_btn, not cur_fs, "🪟 일반 / 창모드"),
            (self.opt_fullscreen_btn, cur_fs, "⛶ 브라우저 / 전체화면"),
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

    # ==========================================================================
    # 프로그래시브 10종 로딩 화면 & 매칭 조리기구/음식 일러스트 로딩 바 렌더링
    # ==========================================================================
    def get_current_loading_theme(self) -> Dict[str, Any]:
        """현재 로딩 화면의 테마(10종 중 1개)를 반환한다."""
        idx = int(self.loading_theme_idx) % len(LOADING_THEMES)
        return LOADING_THEMES[idx]

    def _draw_loading_appliance_illustration(
        self,
        surface: pygame.Surface,
        stage_rect: pygame.Rect,
        theme: Dict[str, Any],
        progress: float,
    ) -> None:
        """
        로딩 멘트(붕어빵 굽는중, 오뎅 국물 내는중 등 10종)에 어울리는
        조리 기구 & 음식 일러스트 장면을 렌더링한다.
        """
        t = self._loading_tick
        accent = theme.get("accent", config.POCHA_ORANGE)
        app_type = str(theme.get("appliance", "mold_bungeo"))
        country_id = str(theme.get("country", "KR"))
        foods = theme.get("foods", ("bungeoppang_redbean", "bungeoppang_cream"))

        # 1) 국가별 야시장 배경 + 따뜻한 다크 비네팅
        art_renderer.draw_country_background(
            surface,
            stage_rect,
            country_id=country_id,
            interior_levels={"lighting": 2, "signboard": 2, "prop": 2, "seating": 1},
            time_tick=t,
        )
        art_renderer.draw_alpha_overlay(surface, stage_rect, (14, 10, 26, 155), border_radius=16)
        pygame.draw.rect(surface, accent, stage_rect, width=3, border_radius=16)

        # 2) 좌측: 포차 마스터 조리 애니메이션 + 말풍선
        chef_id = getattr(self.game_mgr, "selected_character", "chef_kr") or "chef_kr"
        chef_box = pygame.Rect(stage_rect.x + 34, stage_rect.y + 62, 136, 136)
        pygame.draw.rect(surface, (28, 22, 46), chef_box.inflate(12, 12), border_radius=16)
        pygame.draw.rect(surface, config.GOLD, chef_box.inflate(12, 12), width=2, border_radius=16)
        art_renderer.draw_chef_avatar(
            surface,
            chef_box,
            character_id=chef_id,
            state="COOKING",
            time_tick=t * 1.6,
        )
        badge_f = config.get_font(13, bold=True)
        c_lbl = badge_f.render("👨‍🍳 조리 준비 중!", True, config.GOLD)
        surface.blit(c_lbl, c_lbl.get_rect(center=(chef_box.centerx, chef_box.bottom + 20)))

        # 3) 중앙~우측: 테마별 전용 조리기구 & 음식 일러스트 데스크
        counter_rect = pygame.Rect(stage_rect.x + 206, stage_rect.y + 38, stage_rect.width - 236, stage_rect.height - 58)
        pygame.draw.rect(surface, (26, 20, 38), counter_rect, border_radius=16)
        pygame.draw.rect(surface, (78, 66, 108), counter_rect, width=2, border_radius=16)

        # 상단 기구 타이틀 배지
        st_title = str(theme.get("station_title", "포차 조리 스테이션"))
        st_pill = pygame.Rect(counter_rect.centerx - 150, counter_rect.y + 10, 300, 28)
        pygame.draw.rect(surface, (42, 34, 64), st_pill, border_radius=14)
        pygame.draw.rect(surface, accent, st_pill, width=1, border_radius=14)
        st_txt = badge_f.render(f"🔥 {st_title}", True, accent)
        surface.blit(st_txt, st_txt.get_rect(center=st_pill.center))

        # 중앙 조리대 그래픽 (기구 종류별 맞춤 일러스트)
        cx, cy = counter_rect.centerx, counter_rect.centery + 18
        plate_r = pygame.Rect(cx - 175, cy - 58, 350, 118)

        if app_type in ("mold_bungeo", "mold_takoyaki"):
            # 무쇠 구이 틀 (붕어빵 2구 틀 / 타코야키 주물판)
            pygame.draw.rect(surface, (48, 44, 58), plate_r, border_radius=14)
            pygame.draw.rect(surface, (110, 104, 128), plate_r, width=3, border_radius=14)
            # 하단 불꽃 화구
            for fx in range(plate_r.x + 36, plate_r.right - 28, 34):
                flick = int(math.sin(t * 9.0 + fx) * 4)
                pygame.draw.circle(surface, (255, 92, 36), (fx, plate_r.bottom + 4), 7 + flick // 2)
                pygame.draw.circle(surface, (255, 215, 70), (fx, plate_r.bottom + 4), 4)
            if app_type == "mold_takoyaki":
                for r_i in range(2):
                    for c_i in range(5):
                        wx = plate_r.x + 45 + c_i * 64
                        wy = plate_r.y + 34 + r_i * 48
                        pygame.draw.circle(surface, (30, 26, 36), (wx, wy), 18)
                        pygame.draw.circle(surface, (218, 152, 74), (wx, wy), 13)
            else:
                for slot_i in range(2):
                    sr = pygame.Rect(plate_r.x + 22 + slot_i * 162, plate_r.y + 14, 144, 90)
                    pygame.draw.rect(surface, (32, 28, 40), sr, border_radius=12)
                    pygame.draw.rect(surface, config.GOLD, sr, width=1, border_radius=12)

        elif app_type in ("pot_odeng", "pot_boba", "pot_mala"):
            # 육수/국물 온장고 및 대형 가마솥 (오뎅 국물 / 흑당 버블 / 사천 마라탕)
            pygame.draw.rect(surface, (66, 72, 88), plate_r, border_radius=16)
            pygame.draw.rect(surface, (168, 178, 200), plate_r, width=3, border_radius=16)
            broth_col = (
                (212, 162, 78)
                if app_type == "pot_odeng"
                else ((98, 52, 32) if app_type == "pot_boba" else (196, 44, 38))
            )
            inner_r = plate_r.inflate(-22, -22)
            pygame.draw.rect(surface, broth_col, inner_r, border_radius=12)
            # 보글보글 기포 연출
            for b_i in range(7):
                bx = inner_r.x + 28 + b_i * 44
                by = inner_r.centery + int(math.sin(t * 6.0 + b_i * 1.3) * 14)
                rad = 5 + int((math.sin(t * 8.0 + b_i) + 1) * 2.5)
                pygame.draw.circle(surface, (255, 238, 188), (bx, by), rad, width=2)

        elif app_type in ("grill_skewer", "grill_taco", "oven_tandoor"):
            # 참숯 직화 그릴 & 화로 (닭꼬치 / 멕시코 타코 / 인도 탄두리)
            pygame.draw.rect(surface, (58, 32, 30), plate_r, border_radius=14)
            pygame.draw.rect(surface, (255, 118, 62), plate_r, width=3, border_radius=14)
            # 타오르는 참숯 & 석쇠 창살
            ember_r = plate_r.inflate(-18, -20)
            pygame.draw.rect(surface, (128, 32, 24), ember_r, border_radius=10)
            for e_i in range(8):
                ex = ember_r.x + 24 + e_i * 38
                ey = ember_r.centery + int(math.cos(t * 5.0 + e_i) * 12)
                pygame.draw.circle(surface, (255, 132, 42), (ex, ey), 14)
                pygame.draw.circle(surface, (255, 220, 95), (ex, ey), 7)
            for gx in range(plate_r.x + 24, plate_r.right - 20, 22):
                pygame.draw.line(surface, (190, 195, 210), (gx, plate_r.y + 8), (gx, plate_r.bottom - 8), 2)

        elif app_type == "pan_tteokbokki":
            # 포차 대형 무쇠 떡볶이 철판
            pygame.draw.rect(surface, (36, 32, 44), plate_r, border_radius=14)
            pygame.draw.rect(surface, (255, 88, 96), plate_r, width=3, border_radius=14)
            sauce_r = plate_r.inflate(-20, -20)
            pygame.draw.rect(surface, (198, 38, 42), sauce_r, border_radius=10)
            for b_i in range(6):
                bx = sauce_r.x + 34 + b_i * 48
                by = sauce_r.centery + int(math.sin(t * 7.0 + b_i) * 12)
                pygame.draw.circle(surface, (255, 192, 92), (bx, by), 8)

        else:
            # 포장마차 알전구 천막 오픈 연출 (진행률에 따라 알전구 순차 점등!)
            pygame.draw.rect(surface, (38, 28, 56), plate_r, border_radius=14)
            pygame.draw.rect(surface, config.NEON_CYAN, plate_r, width=2, border_radius=14)
            lit_bulbs = max(1, int(round(progress * 8)))
            for b_i in range(8):
                bx = plate_r.x + 28 + b_i * 42
                by = plate_r.y + 22
                is_lit = b_i < lit_bulbs
                if is_lit:
                    pygame.draw.circle(surface, (255, 210, 90), (bx, by), 13)
                    pygame.draw.circle(surface, (255, 250, 210), (bx, by), 7)
                else:
                    pygame.draw.circle(surface, (75, 70, 92), (bx, by), 8)

        # 4) 조리 기구 위에 놓인 큼직한 대표 음식 아이콘 2종 애니메이션
        for idx, fid in enumerate(foods[:2]):
            bob = int(math.sin(t * 5.5 + idx * 1.6) * 5)
            fx = cx - 78 + idx * 156
            fy = cy + bob
            art_renderer.draw_food_icon(surface, (fx, fy), str(fid), size=76)

        # 5) 모락모락 피어오르는 김(Steam) & 반짝이는 불꽃 파티클
        for s_i in range(6):
            phase = (t * 1.8 + s_i * 0.35) % 1.0
            sx = cx - 125 + s_i * 50 + int(math.sin(t * 4.0 + s_i) * 8)
            sy = int(plate_r.y + 10 - phase * 46)
            rad = max(3, int((1.0 - phase) * 11))
            pygame.draw.circle(surface, (235, 238, 248), (sx, sy), rad, width=2)

    def _draw_loading_overlay(self, surface: pygame.Surface) -> None:
        """
        1280x720 논리 화면 위에 10종 프로그래시브 조리 멘트와
        어울리는 일러스트 & 로딩 바 화면을 렌더링한다.
        """
        p_ratio = max(0.0, min(1.0, float(self.loading_progress)))
        pct = int(round(p_ratio * 100))
        theme = self.get_current_loading_theme()
        accent = theme.get("accent", config.POCHA_ORANGE)
        foods = theme.get("foods", ("bungeoppang_redbean", "bungeoppang_cream"))

        # 전체 배경 다크 나이트마켓 오버레이
        surface.fill((12, 10, 22))
        card = pygame.Rect(110, 36, 1060, 648)
        pygame.draw.rect(surface, (22, 18, 38), card, border_radius=22)
        pygame.draw.rect(surface, accent, card, width=3, border_radius=22)
        pygame.draw.rect(surface, config.GOLD, card.inflate(-10, -10), width=1, border_radius=18)

        title_f = config.get_font(28, bold=True)
        msg_f = config.get_font(24, bold=True)
        sub_f = config.get_font(15, bold=True)
        tip_f = config.get_font(14, bold=False)
        xs_f = config.get_font(12, bold=True)

        # 1) 상단 헤더
        hdr_s = title_f.render("🏮 전세계 길거리 음식 포차 타이쿤 — 영업 준비 중", True, config.GOLD)
        surface.blit(hdr_s, hdr_s.get_rect(center=(card.centerx, card.y + 34)))

        # 2) 중단: 멘트에 어울리는 맞춤 조리기구 & 음식 일러스트 스테이지
        stage_rect = pygame.Rect(card.x + 44, card.y + 66, card.width - 88, 286)
        self._draw_loading_appliance_illustration(surface, stage_rect, theme, p_ratio)

        # 3) 프로그래시브 메인 조리 멘트 & 상세 설명
        step_num = int(theme.get("step", 1))
        main_msg = str(theme.get("message", "🐟 황금빛 붕어빵 굽는 중..."))
        sub_msg = str(theme.get("sub", "맛있는 길거리 음식을 정성껏 조리하고 있습니다!"))

        msg_surf = msg_f.render(f"[{step_num}/10]  {main_msg}", True, config.WHITE)
        sub_surf = sub_f.render(sub_msg, True, accent)
        msg_rect = msg_surf.get_rect(center=(card.centerx, stage_rect.bottom + 34))
        surface.blit(msg_surf, msg_rect)
        art_renderer.draw_food_icon(surface, (msg_rect.left - 28, msg_rect.centery), str(foods[0]), size=34)
        art_renderer.draw_food_icon(surface, (msg_rect.right + 28, msg_rect.centery), str(foods[-1]), size=34)
        surface.blit(sub_surf, sub_surf.get_rect(center=(card.centerx, stage_rect.bottom + 66)))

        # 4) 테마 매칭 네온 로딩 바 (게이지 끝에 매칭 음식 아이콘이 통통 튀며 이동 + 우측 독립 퍼센트 배지)
        bar_rect = pygame.Rect(card.x + 60, stage_rect.bottom + 96, card.width - 264, 36)
        pct_box = pygame.Rect(bar_rect.right + 16, bar_rect.y, 128, 36)
        pygame.draw.rect(surface, (14, 12, 24), bar_rect, border_radius=18)

        fill_w = max(24, int(round(bar_rect.width * p_ratio)))
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height)
        pygame.draw.rect(surface, accent, fill_rect, border_radius=18)

        # 게이지 내부 사선 하이라이트 패턴
        stripe_offset = int(self._loading_tick * 60) % 28
        for sx in range(bar_rect.x + stripe_offset, fill_rect.right - 10, 28):
            pygame.draw.line(
                surface,
                (255, 255, 255),
                (sx, bar_rect.y + 5),
                (min(fill_rect.right - 6, sx + 10), bar_rect.bottom - 5),
                2,
            )

        pygame.draw.rect(surface, config.GOLD, bar_rect, width=2, border_radius=18)

        # 게이지 진행 끝부분(Tip)에 매칭 음식 아이콘 커서 렌더링!
        cursor_x = max(bar_rect.x + 20, min(bar_rect.right - 16, fill_rect.right))
        cursor_y = bar_rect.centery + int(math.sin(self._loading_tick * 10.0) * 3)
        pygame.draw.circle(surface, (28, 22, 44), (cursor_x, cursor_y), 24)
        pygame.draw.circle(surface, config.GOLD, (cursor_x, cursor_y), 24, width=2)
        art_renderer.draw_food_icon(surface, (cursor_x, cursor_y), str(foods[0]), size=34)

        # 우측 독립 퍼센트 배지 박스 (아이콘 커서와 겹치지 않음)
        pygame.draw.rect(surface, (28, 22, 46), pct_box, border_radius=18)
        pygame.draw.rect(surface, accent, pct_box, width=2, border_radius=18)
        pct_surf = sub_f.render(f"LOADING {pct}%", True, config.GOLD)
        surface.blit(pct_surf, pct_surf.get_rect(center=pct_box.center))

        # 5) 10개 프로그래시브 조리 멘트 미니 스텝 트랙 (10종 한눈에 보기)
        track_y = bar_rect.bottom + 24
        col_w = (card.width - 100) // 5
        for idx, t_item in enumerate(LOADING_THEMES):
            col = idx % 5
            row = idx // 5
            chip_r = pygame.Rect(card.x + 50 + col * col_w, track_y + row * 34, col_w - 8, 28)
            is_cur = idx == (self.loading_theme_idx % len(LOADING_THEMES))
            chip_bg = t_item["accent"] if is_cur else (34, 28, 52)
            chip_fg = (18, 14, 26) if is_cur else config.TEXT_SECONDARY
            pygame.draw.rect(surface, chip_bg, chip_r, border_radius=8)
            pygame.draw.rect(
                surface,
                config.WHITE if is_cur else config.UI_BORDER,
                chip_r,
                width=2 if is_cur else 1,
                border_radius=8,
            )
            short_txt = xs_f.render(f"{idx + 1}. {t_item['short']}", True, chip_fg)
            surface.blit(short_txt, short_txt.get_rect(center=chip_r.center))

        # 6) 하단 포차 운영 꿀팁 배너
        tip_rect = pygame.Rect(card.x + 50, card.bottom - 56, card.width - 100, 38)
        pygame.draw.rect(surface, (30, 24, 48), tip_rect, border_radius=10)
        pygame.draw.rect(surface, config.UI_BORDER, tip_rect, width=1, border_radius=10)
        tip_s = tip_f.render(f"💡 {theme.get('tip', '')}", True, config.NEON_CYAN)
        surface.blit(tip_s, tip_s.get_rect(center=tip_rect.center))
