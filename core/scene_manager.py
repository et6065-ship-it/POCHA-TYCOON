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
        "foods": ("odeng_soup", "sikhye_cup"),
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
        "foods": ("boba_milktea", "jipai_spicy"),
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
        "foods": ("malatang_plain", "lamb_skewer_cumin"),
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
        "foods": ("tikka_masala", "bacon_burger"),
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
        "foods": ("picanha_farofa", "siberia_shashlik"),
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

        # 프로그래시브 로딩 화면 상태 (10종 멘트 & 매칭 조리 일러스트 로딩 바 + 인게임 대기 화면)
        self.loading_active: bool = False
        self.loading_progress: float = 0.0
        self.loading_duration: float = 1.10
        self.loading_theme_idx: int = 0
        self._loading_rotation_counter: int = 0
        self._loading_tick: float = 0.0
        self.loading_wait_for_tap: bool = False
        self.loading_cycle_themes: bool = False
        self._loading_theme_timer: float = 0.0

        # 모바일 세로 모드(720x1280) 1패널 확대 뷰 상태 (4분할 제거 -> 1개 대형 패널 전환)
        self.portrait_title_idx: int = 0  # 0: ①마스터 프로필, 1: ②스토리 모드, 2: ③장인 모드, 3: ④글로벌 모드
        self.portrait_prep_idx: int = 0   # 상점/준비 각 탭별 현재 보고 있는 단일 카드/패널 인덱스
        self.portrait_play_idx: int = 0   # 인게임 조리 스테이션 단일 패널 인덱스
        self._portrait_swipe_start: Optional[Tuple[int, int, int]] = None

        config.sync_browser_display_and_fullscreen(None)
        self._register_default_scenes()

        if initial_scene:
            self.change_scene(initial_scene, show_loading=False)

    def start_loading(
        self,
        duration: float = 0.95,
        theme_index: Optional[int] = None,
        wait_for_tap: bool = False,
        cycle_themes: bool = False,
    ) -> None:
        """
        10종 프로그래시브 조리 멘트와 어울리는 음식·조리기구 일러스트 로딩 바 화면을 시작한다.
        wait_for_tap=True이면 100% 완료 후 인게임 대기 화면(터치하여 시작) 상태를 유지한다.
        """
        self.loading_active = True
        self.loading_progress = 0.0
        self.loading_duration = max(0.25, float(duration))
        self.loading_wait_for_tap = bool(wait_for_tap)
        self.loading_cycle_themes = bool(cycle_themes)
        self._loading_theme_timer = 0.0
        if theme_index is not None:
            self.loading_theme_idx = int(theme_index) % len(LOADING_THEMES)
        elif getattr(self.game_mgr, "mode", "") == "SPECIALIST" and not cycle_themes:
            spec_theme_map = {"bungeo": 0, "odeng": 1, "skewer": 2, "tteokbokki": 3, "takoyaki": 4, "taco": 5, "boba": 6}
            sp_key = str(getattr(self.game_mgr, "selected_specialist", "bungeo")).lower()
            self.loading_theme_idx = spec_theme_map.get(sp_key, 0) % len(LOADING_THEMES)
        else:
            self.loading_theme_idx = self._loading_rotation_counter % len(LOADING_THEMES)
            self._loading_rotation_counter = (self._loading_rotation_counter + 1) % len(LOADING_THEMES)

    def finish_loading(self) -> None:
        """진행 중인 로딩 오버레이를 즉시 완료 처리한다."""
        self.loading_active = False
        self.loading_progress = 1.0
        self.loading_wait_for_tap = False
        self.loading_cycle_themes = False

    @property
    def is_portrait_mode(self) -> bool:
        """현재 디스플레이가 세로(Portrait, 높이 > 너비) 모드인지 여부를 반환한다."""
        disp = pygame.display.get_surface()
        win_w, win_h = disp.get_size() if disp is not None else config.WINDOW_SIZE
        return (win_h > win_w) or (config.WINDOW_HEIGHT > config.WINDOW_WIDTH)

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
        self._sync_portrait_state_on_scene_enter(key)

        ch_id = str(getattr(self.game_mgr, "current_chapter", "KR") or "KR").upper()
        play_bgm_map = {
            "KR": "play_kr",
            "JP": "play_jp",
            "MX": "play_mx",
            "TW": "play_tw",
        }
        bgm_map = {
            "title": "title",
            "prep": "prep",
            "play": play_bgm_map.get(ch_id, "play_kr"),
            "duel_lobby": "prep",
            "duel_play": "fever",
            "result": "result",
            "duel_result": "result",
        }
        if key in bgm_map:
            sound_fx.play_bgm(bgm_map[key])

        if bool(kwargs.get("show_loading", False)):
            self.start_loading(
                duration=float(kwargs.get("loading_duration", 1.05)),
                theme_index=kwargs.get("loading_theme"),
                wait_for_tap=bool(kwargs.get("loading_wait_for_tap", False)),
                cycle_themes=bool(kwargs.get("loading_cycle_themes", False)),
            )
        else:
            self.finish_loading()
        return self.current_scene

    switch_scene = change_scene
    set_scene = change_scene
    goto = change_scene

    def _sync_portrait_state_on_scene_enter(self, key: str) -> None:
        """씬 전환 시 세로 모드 단일 패널 인덱스를 현재 선택된 항목에 맞게 동기화한다."""
        if key in ("play", "duel_play"):
            self.portrait_play_idx = 0
        elif key == "prep":
            self._sync_portrait_prep_idx_to_selection()

    def _sync_portrait_prep_idx_to_selection(self) -> None:
        """PrepScene의 현재 탭 및 모드에 맞춰 세로 단일 패널 인덱스를 활성 항목으로 맞춘다."""
        sc = self.current_scene
        active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
        if active_tab == "chapter":
            mode = getattr(self.game_mgr, "mode", "WORLD_TOUR")
            if mode == "SPECIALIST":
                from data.specialist_menus import SPECIALIST_ORDER
                sp_id = getattr(self.game_mgr, "selected_specialist", "bungeo")
                self.portrait_prep_idx = SPECIALIST_ORDER.index(sp_id) if sp_id in SPECIALIST_ORDER else 0
            elif mode == "GLOBAL_ENDLESS":
                self.portrait_prep_idx = 0
            else:
                from data.chapters import CHAPTER_ORDER
                ch_id = getattr(self.game_mgr, "current_chapter", "KR")
                self.portrait_prep_idx = CHAPTER_ORDER.index(ch_id) if ch_id in CHAPTER_ORDER else 0
        else:
            self.portrait_prep_idx = 0

    def _sync_prep_logical_page_for_portrait(self) -> None:
        """세로 모드에서 1개 카드씩 넘길 때 PrepScene의 내부 페이지(chapter_page / specialist_page)를 자동 동기화한다."""
        if self.current_scene_name != "prep" or self.current_scene is None:
            return
        sc = self.current_scene
        active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
        changed = False
        if active_tab == "chapter":
            mode = getattr(self.game_mgr, "mode", "WORLD_TOUR")
            if mode == "SPECIALIST":
                from data.specialist_menus import SPECIALIST_ORDER
                idx = self.portrait_prep_idx % max(1, len(SPECIALIST_ORDER))
                new_pg = idx // 4
                if getattr(sc, "specialist_page", 0) != new_pg:
                    sc.specialist_page = new_pg
                    changed = True
            elif mode == "WORLD_TOUR":
                from data.chapters import CHAPTER_ORDER
                idx = self.portrait_prep_idx % max(1, len(CHAPTER_ORDER))
                new_pg = idx // 4
                if getattr(sc, "chapter_page", 0) != new_pg:
                    sc.chapter_page = new_pg
                    changed = True
        if changed and hasattr(sc, "_rebuild_click_targets"):
            sc._rebuild_click_targets()

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

    def _window_to_portrait_point(self, wx: float, wy: float, win_w: int, win_h: int) -> Tuple[int, int]:
        """실제 윈도우 좌표를 720x1280 세로 캔버스 좌표(px, py)로 변환한다."""
        ox, oy, vp_w, vp_h, _scale = self._compute_viewport(win_w, win_h)
        if win_h > win_w:
            px = (wx - ox) * config.PORTRAIT_WIDTH / float(max(1, vp_w))
            py = (wy - oy) * config.PORTRAIT_HEIGHT / float(max(1, vp_h))
        else:
            px = wx * config.PORTRAIT_WIDTH / float(max(1, win_w))
            py = wy * config.PORTRAIT_HEIGHT / float(max(1, win_h))
        return int(round(px)), int(round(py))

    def _get_portrait_region_mappings(self) -> List[Tuple[pygame.Rect, pygame.Rect, Tuple[int, int, int]]]:
        """
        세로 모드(720x1280)에서 기존의 4개 패널 동시 분할을 완전히 제거하고,
        현재 선택된 **단 1개의 대형 메인 패널(Single Giant Panel)**만 매핑한다.
        """
        sc = self.current_scene
        if self.options_open:
            return [
                (
                    pygame.Rect(216, 52, 848, 616),
                    pygame.Rect(12, 210, 696, 860),
                    config.GOLD,
                )
            ]
        if self.loading_active:
            return [
                (
                    pygame.Rect(106, 32, 1068, 656),
                    pygame.Rect(12, 230, 696, 820),
                    config.GOLD,
                )
            ]
        if self.current_scene_name == "result" and getattr(sc, "active_cutscene", None) is None:
            return [
                (
                    pygame.Rect(186, 36, 908, 648),
                    pygame.Rect(12, 210, 696, 860),
                    config.GOLD,
                )
            ]
        has_modal = (
            getattr(sc, "active_cutscene", None) is not None
            or bool(getattr(sc, "paused", False))
            or bool(getattr(sc, "show_roster_modal", False))
            or self.current_scene_name in ("duel_result", "duel_lobby")
        )
        if has_modal:
            return [
                (
                    pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
                    pygame.Rect(8, 280, 704, 720),
                    config.GOLD,
                )
            ]

        # ------------------------------------------------------------------
        # 1) 인게임(PlayScene / DuelPlayScene): 단 1개의 대형 조리 스테이션 패널만 표시!
        # ------------------------------------------------------------------
        if self.current_scene_name in ("play", "duel_play"):
            is_spec = (
                self.current_scene_name == "play"
                and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "SPECIALIST"
            )
            if is_spec:
                spec_srcs = [
                    (pygame.Rect(14, 355, 448, 352), config.POCHA_ORANGE),
                    (pygame.Rect(818, 355, 448, 352), config.GOLD),
                    (pygame.Rect(472, 355, 336, 352), config.NEON_CYAN),
                ]
                idx = self.portrait_play_idx % len(spec_srcs)
                station_src, st_border = spec_srcs[idx]
            else:
                norm_srcs = [
                    (pygame.Rect(14, 355, 224, 352), config.POCHA_ORANGE),
                    (pygame.Rect(246, 355, 220, 352), config.NEON_CYAN),
                    (pygame.Rect(472, 355, 336, 352), config.GOLD),
                    (pygame.Rect(814, 355, 220, 352), config.POCHA_ORANGE),
                    (pygame.Rect(1040, 355, 226, 352), config.NEON_PINK),
                ]
                idx = self.portrait_play_idx % len(norm_srcs)
                station_src, st_border = norm_srcs[idx]

            return [
                (pygame.Rect(1054, 8, 216, 48), pygame.Rect(464, 8, 248, 48), config.GOLD),
                (station_src, pygame.Rect(16, 426, 688, 752), st_border),
            ]

        # ------------------------------------------------------------------
        # 2) 타이틀 화면(TitleScene): 1:1 네이티브 고해상도 카드 렌더링 사용
        # ------------------------------------------------------------------
        if self.current_scene_name == "title":
            card_srcs = [
                (pygame.Rect(34, 212, 290, 346), config.NEON_GREEN),
                (pygame.Rect(340, 212, 290, 346), config.POCHA_ORANGE),
                (pygame.Rect(646, 212, 290, 346), config.GOLD),
                (pygame.Rect(952, 212, 294, 346), config.NEON_CYAN),
            ]
            t_idx = self.portrait_title_idx % len(card_srcs)
            active_card_src, active_card_col = card_srcs[t_idx]
            return [
                (pygame.Rect(615, 14, 635, 38), pygame.Rect(12, 12, 696, 42), config.UI_BORDER),
                (active_card_src, pygame.Rect(24, 252, 672, 728), active_card_col),
                (pygame.Rect(36, 644, 524, 54), pygame.Rect(12, 994, 696, 72), config.UI_BORDER),
                (pygame.Rect(564, 644, 360, 54), pygame.Rect(84, 1078, 552, 72), config.NEON_CYAN),
            ]

        # ------------------------------------------------------------------
        # 3) 준비/상점 화면(PrepScene): 1:1 네이티브 고해상도 단일 카드 렌더링 사용
        # ------------------------------------------------------------------
        if self.current_scene_name == "prep":
            self._sync_prep_logical_page_for_portrait()
            active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
            base_regions: List[Tuple[pygame.Rect, pygame.Rect, Tuple[int, int, int]]] = [
                (pygame.Rect(24, 10, 476, 52), pygame.Rect(8, 8, 456, 52), config.UI_BORDER),
                (pygame.Rect(988, 10, 266, 52), pygame.Rect(472, 8, 240, 52), config.GOLD),
                (pygame.Rect(24, 68, 1232, 54), pygame.Rect(8, 66, 704, 52), config.UI_BORDER),
            ]
            if active_tab == "character":
                if (self.portrait_prep_idx % 2) == 0:
                    base_regions.append(
                        (pygame.Rect(852, 178, 382, 440), pygame.Rect(16, 188, 688, 848), config.NEON_CYAN)
                    )
                else:
                    base_regions.append(
                        (pygame.Rect(28, 126, 1224, 50), pygame.Rect(12, 188, 696, 48), config.UI_BORDER)
                    )
                    base_regions.append(
                        (pygame.Rect(28, 176, 816, 452), pygame.Rect(12, 242, 696, 794), config.POCHA_ORANGE)
                    )
            elif active_tab == "chapter":
                mode = getattr(self.game_mgr, "mode", "WORLD_TOUR")
                if mode == "SPECIALIST":
                    from data.specialist_menus import SPECIALIST_ORDER
                    idx = self.portrait_prep_idx % max(1, len(SPECIALIST_ORDER))
                    col = idx % 4
                    card_src = pygame.Rect(50 + col * 300, 178, 282, 434)
                elif mode == "GLOBAL_ENDLESS":
                    col = self.portrait_prep_idx % 4
                    card_src = pygame.Rect(50 + col * 300, 176, 282, 434)
                else:
                    from data.chapters import CHAPTER_ORDER
                    idx = self.portrait_prep_idx % max(1, len(CHAPTER_ORDER))
                    col = idx % 4
                    card_src = pygame.Rect(50 + col * 300, 178, 282, 434)
                base_regions.append(
                    (card_src, pygame.Rect(16, 188, 688, 848), config.GOLD)
                )
            elif active_tab == "upgrade":
                if (self.portrait_prep_idx % 2) == 0:
                    up_src = pygame.Rect(38, 134, 610, 488)
                    up_col = config.GOLD
                else:
                    up_src = pygame.Rect(646, 134, 594, 488)
                    up_col = config.NEON_PINK
                base_regions.append(
                    (up_src, pygame.Rect(16, 188, 688, 848), up_col)
                )
            else:  # tournament
                if (self.portrait_prep_idx % 2) == 0:
                    tn_src = pygame.Rect(38, 134, 576, 488)
                    tn_col = config.POCHA_ORANGE
                else:
                    tn_src = pygame.Rect(616, 134, 624, 488)
                    tn_col = config.GOLD
                base_regions.append(
                    (tn_src, pygame.Rect(16, 188, 688, 848), tn_col)
                )

            base_regions.append(
                (pygame.Rect(900, 638, 356, 68), pygame.Rect(80, 1162, 560, 96), config.GOLD)
            )
            return base_regions

        return [
            (
                pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
                pygame.Rect(8, 280, 704, 720),
                config.GOLD,
            )
        ]

    def _step_portrait_panel(self, delta: int) -> None:
        """세로 모드에서 [◀] / [▶] 버튼 또는 좌우 스와이프 시 현재 단일 패널을 1칸씩 정확히 순서대로 전환한다."""
        self._portrait_swipe_start = None
        step = -1 if int(delta) < 0 else 1
        sound_fx.play_tab_switch()
        sc = self.current_scene
        if self.current_scene_name == "title":
            self.portrait_title_idx = (self.portrait_title_idx + step) % 4
            return

        if self.current_scene_name in ("play", "duel_play"):
            is_spec = (
                self.current_scene_name == "play"
                and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "SPECIALIST"
            )
            cnt = 3 if is_spec else 5
            self.portrait_play_idx = (self.portrait_play_idx + step) % cnt
            return

        if self.current_scene_name == "prep" and sc is not None:
            active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
            if active_tab == "character":
                if (self.portrait_prep_idx % 2) == 0 and hasattr(sc, "_get_filtered_characters"):
                    filtered = sc._get_filtered_characters()
                    if filtered:
                        cur_id = getattr(sc, "inspected_character", filtered[0])
                        cur_i = filtered.index(cur_id) if cur_id in filtered else 0
                        next_i = (cur_i + step) % len(filtered)
                        sc.inspected_character = filtered[next_i]
                        sc.char_page = next_i // 6
                else:
                    if hasattr(sc, "_handle_action"):
                        sc._handle_action("char_page_delta", step, (640, 360))
            elif active_tab == "chapter":
                mode = getattr(self.game_mgr, "mode", "WORLD_TOUR")
                if mode == "SPECIALIST":
                    from data.specialist_menus import SPECIALIST_MENUS, SPECIALIST_ORDER
                    self.portrait_prep_idx = (self.portrait_prep_idx + step) % len(SPECIALIST_ORDER)
                    sc.specialist_page = self.portrait_prep_idx // 4
                    sp_id = SPECIALIST_ORDER[self.portrait_prep_idx]
                    if SPECIALIST_MENUS.get(sp_id, {}).get("is_open", False):
                        self.game_mgr.select_specialist(sp_id)
                        self.game_mgr.save_game()
                elif mode == "GLOBAL_ENDLESS":
                    self.portrait_prep_idx = (self.portrait_prep_idx + step) % 4
                else:
                    from data.chapters import CHAPTER_ORDER
                    self.portrait_prep_idx = (self.portrait_prep_idx + step) % len(CHAPTER_ORDER)
                    sc.chapter_page = self.portrait_prep_idx // 4
                    ch_id = CHAPTER_ORDER[self.portrait_prep_idx]
                    if self.game_mgr.is_chapter_unlocked(ch_id):
                        self.game_mgr.select_chapter(ch_id)
                        self.game_mgr.save_game()
            else:
                self.portrait_prep_idx = (self.portrait_prep_idx + step) % 2
            if hasattr(sc, "_rebuild_click_targets"):
                sc._rebuild_click_targets()

    def _handle_portrait_play_station_click(self, px: int, py: int, sc: Any) -> bool:
        """
        세로 모드 인게임 대형 조리 스테이션 영역(dst_r = 16, 426, 688, 752) 클릭을
        1:1 네이티브 레이아웃 좌표 그대로 정확히 처리한다.
        """
        dst_r = pygame.Rect(16, 426, 688, 752)
        if not dst_r.collidepoint(px, py):
            return False

        is_spec = (
            self.current_scene_name == "play"
            and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "SPECIALIST"
        )
        if is_spec:
            idx = self.portrait_play_idx % 3
            if idx in (0, 1) and hasattr(sc, "specialist_station"):
                sp = sc.specialist_station
                orig_in = sp.input_rect.copy()
                orig_ap = sp.appliance_rect.copy()
                try:
                    if idx == 0:
                        sp.input_rect = dst_r.copy()
                        sp.appliance_rect = pygame.Rect(-2000, -2000, 448, 352)
                    else:
                        sp.input_rect = pygame.Rect(-2000, -2000, 448, 352)
                        sp.appliance_rect = dst_r.copy()
                        sp.rect = dst_r.copy()
                    sp._rebuild_layout()
                    res = sp.handle_click(
                        (px, py),
                        assembly_tray=getattr(sc, "assembly_tray", None),
                        auto_serve_cb=getattr(sc, "try_auto_serve", None),
                        customers=getattr(sc, "customers", []),
                    )
                finally:
                    sp.input_rect = orig_in
                    sp.appliance_rect = orig_ap
                    sp.rect = orig_ap
                    sp._rebuild_layout()
                if res:
                    self._portrait_swipe_start = None
                    if hasattr(sc, "_handle_station_feedback"):
                        sc._handle_station_feedback(res, (px, py))
                return True

            if idx == 2 and hasattr(sc, "assembly_tray"):
                tr = sc.assembly_tray
                orig_r = tr.rect.copy()
                try:
                    tr.rect = dst_r.copy()
                    if hasattr(tr, "_rebuild_layout"):
                        tr._rebuild_layout()
                    tr.start_hold((px, py))
                    res = tr.handle_click(
                        (px, py),
                        auto_serve_cb=getattr(sc, "try_auto_serve", None),
                        button=1,
                    )
                finally:
                    tr.rect = orig_r
                    if hasattr(tr, "_rebuild_layout"):
                        tr._rebuild_layout()
                if res:
                    self._portrait_swipe_start = None
                    if hasattr(sc, "_handle_station_feedback"):
                        sc._handle_station_feedback(res, (px, py))
                return True
            return True

        idx = self.portrait_play_idx % 5
        if idx == 2 and hasattr(sc, "assembly_tray"):
            tr = sc.assembly_tray
            orig_r = tr.rect.copy()
            try:
                tr.rect = dst_r.copy()
                if hasattr(tr, "_rebuild_layout"):
                    tr._rebuild_layout()
                tr.start_hold((px, py))
                res = tr.handle_click(
                    (px, py),
                    auto_serve_cb=getattr(sc, "try_auto_serve", None),
                    button=1,
                )
            finally:
                tr.rect = orig_r
                if hasattr(tr, "_rebuild_layout"):
                    tr._rebuild_layout()
            if res:
                self._portrait_swipe_start = None
                if hasattr(sc, "_handle_station_feedback"):
                    sc._handle_station_feedback(res, (px, py))
            return True

        st_map = {
            0: getattr(sc, "mold_station", None),
            1: getattr(sc, "dispenser_station", None),
            3: getattr(sc, "grill_station", None),
            4: getattr(sc, "batch_pot_station", None),
        }
        st_obj = st_map.get(idx)
        if st_obj is not None:
            if (
                hasattr(self.game_mgr, "is_slot_unlocked_in_story")
                and not self.game_mgr.is_slot_unlocked_in_story(st_obj.slot_type)
            ):
                sound_fx.play_burn()
                if hasattr(sc, "particles") and hasattr(sc, "_get_slot_unlock_hint"):
                    sc.particles.spawn_floating_text(
                        sc._get_slot_unlock_hint(st_obj.slot_type),
                        360,
                        720,
                        color=config.TEXT_WARNING,
                        size=20,
                    )
                return True

            orig_r = st_obj.rect.copy()
            try:
                st_obj.rect = dst_r.copy()
                if hasattr(st_obj, "_rebuild_layout"):
                    st_obj._rebuild_layout()
                res = st_obj.handle_click(
                    (px, py),
                    assembly_tray=getattr(sc, "assembly_tray", None),
                    auto_serve_cb=getattr(sc, "try_auto_serve", None),
                )
            finally:
                st_obj.rect = orig_r
                if hasattr(st_obj, "_rebuild_layout"):
                    st_obj._rebuild_layout()
            if res:
                self._portrait_swipe_start = None
                if hasattr(sc, "_handle_station_feedback"):
                    sc._handle_station_feedback(res, (px, py))
        return True

    def _handle_portrait_prep_card_click(self, px: int, py: int, sc: Any) -> bool:
        """세로 모드 상점/준비 화면(PrepScene)의 1:1 네이티브 대형 카드 영역(16, 188, 688, 848) 내부 클릭을 처리한다."""
        card_r = pygame.Rect(16, 188, 688, 848)
        if not card_r.collidepoint(px, py):
            return False

        from data.chapters import CHAPTER_ORDER, CHAPTERS, SLOT_TYPES, get_stations_by_slot
        from data.characters import CHARACTERS, COUNTRY_FILTER_ORDER
        from data.specialist_menus import SPECIALIST_MENUS, SPECIALIST_ORDER
        from data.upgrades import INTERIOR_UPGRADE_ORDER, STATION_UPGRADE_ORDER

        active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
        btn_r = pygame.Rect(36, 932, 648, 84)

        if active_tab == "chapter":
            mode = getattr(self.game_mgr, "mode", "WORLD_TOUR")
            if mode == "SPECIALIST":
                idx = self.portrait_prep_idx % len(SPECIALIST_ORDER)
                sp_id = SPECIALIST_ORDER[idx]
                sp_d = SPECIALIST_MENUS[sp_id]
                if btn_r.collidepoint(px, py) or pygame.Rect(36, 208, 648, 808).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if sp_d.get("is_open", False):
                        was_sel = self.game_mgr.selected_specialist == sp_id
                        self.game_mgr.select_specialist(sp_id)
                        self.game_mgr.save_game()
                        if hasattr(sc, "_rebuild_click_targets"):
                            sc._rebuild_click_targets()
                        if btn_r.collidepoint(px, py):
                            sound_fx.play_day_start()
                            self.game_mgr.ai_opponent_id = ""
                            self.game_mgr.save_game()
                            self.change_scene("play", show_cutscene=True, show_loading=True)
                        elif not was_sel and hasattr(sc, "_handle_action"):
                            sc._handle_action("select_specialist", sp_id, (360, 600))
                    elif hasattr(sc, "_handle_action"):
                        sc._handle_action("preview_coming_soon_specialist", sp_id, (360, 600))
                    return True
            elif mode == "GLOBAL_ENDLESS":
                slot_type = SLOT_TYPES[self.portrait_prep_idx % 4]
                stations = get_stations_by_slot(slot_type)
                per_page = 4
                total_pages = max(1, (len(stations) + per_page - 1) // per_page)
                pg = max(0, min(int(getattr(sc, "global_station_page", 0)), total_pages - 1))
                vis_stations = stations[pg * per_page : (pg + 1) * per_page]
                for i_idx, st_meta in enumerate(vis_stations):
                    row_r = pygame.Rect(36, 256 + i_idx * 162, 648, 148)
                    if row_r.collidepoint(px, py):
                        self._portrait_swipe_start = None
                        if hasattr(sc, "_handle_action"):
                            sc._handle_action("set_global_station", (slot_type, st_meta["id"]), (360, row_r.centery))
                            sc._rebuild_click_targets()
                        return True
                # 하단 페이지 이동 버튼
                if pygame.Rect(36, 924, 310, 88).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if hasattr(sc, "_handle_action"):
                        sc._handle_action("global_page_delta", -1, (360, 960))
                        sc._rebuild_click_targets()
                    return True
                if pygame.Rect(374, 924, 310, 88).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if hasattr(sc, "_handle_action"):
                        sc._handle_action("global_page_delta", 1, (360, 960))
                        sc._rebuild_click_targets()
                    return True
            else:  # WORLD_TOUR
                idx = self.portrait_prep_idx % len(CHAPTER_ORDER)
                ch_id = CHAPTER_ORDER[idx]
                unlocked = self.game_mgr.is_chapter_unlocked(ch_id)
                selected = (self.game_mgr.current_chapter == ch_id) and (self.game_mgr.mode == "WORLD_TOUR")
                if btn_r.collidepoint(px, py) or pygame.Rect(36, 208, 648, 808).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if unlocked:
                        if selected and btn_r.collidepoint(px, py):
                            sound_fx.play_day_start()
                            self.game_mgr.ai_opponent_id = ""
                            self.game_mgr.save_game()
                            self.change_scene("play", show_cutscene=True, show_loading=True)
                        elif not selected and hasattr(sc, "_handle_action"):
                            sc._handle_action("select_chapter", ch_id, (360, 600))
                            sc._rebuild_click_targets()
                    elif hasattr(sc, "_handle_action"):
                        sc._handle_action("unlock_chapter", ch_id, (360, 600))
                        sc._rebuild_click_targets()
                    return True
            return True

        if active_tab == "character":
            if (self.portrait_prep_idx % 2) == 0:
                insp_id = getattr(sc, "inspected_character", self.game_mgr.selected_character)
                if insp_id not in CHARACTERS:
                    insp_id = self.game_mgr.selected_character
                if btn_r.collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if self.game_mgr.is_character_unlocked(insp_id):
                        if self.game_mgr.selected_character != insp_id and hasattr(sc, "_handle_action"):
                            sc._handle_action("select_character", insp_id, (360, 960))
                        else:
                            sound_fx.play_ready()
                    elif hasattr(sc, "_handle_action"):
                        sc._handle_action("unlock_character", insp_id, (360, 960))
                    if hasattr(sc, "_rebuild_click_targets"):
                        sc._rebuild_click_targets()
                    return True
            else:
                # 국가 필터 버튼 10종 (2행 x 5열)
                for f_i, f_code in enumerate(COUNTRY_FILTER_ORDER):
                    f_col = f_i % 5
                    f_row = f_i // 5
                    fr = pygame.Rect(32 + f_col * 132, 202 + f_row * 50, 126, 44)
                    if fr.collidepoint(px, py):
                        self._portrait_swipe_start = None
                        if hasattr(sc, "_handle_action"):
                            sc._handle_action("filter_char_country", f_code, fr.center)
                            sc._rebuild_click_targets()
                        return True
                # 6개 마스터 카드 (2열 x 3행)
                filtered = sc._get_filtered_characters() if hasattr(sc, "_get_filtered_characters") else list(CHARACTERS.keys())
                per_page = 6
                total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
                c_pg = max(0, min(int(getattr(sc, "char_page", 0)), total_pages - 1))
                page_items = filtered[c_pg * per_page : (c_pg + 1) * per_page]
                for idx_c, cid in enumerate(page_items):
                    col = idx_c % 2
                    row = idx_c // 2
                    cr = pygame.Rect(32 + col * 332, 312 + row * 204, 324, 194)
                    if cr.collidepoint(px, py):
                        self._portrait_swipe_start = None
                        sc.inspected_character = cid
                        if self.game_mgr.is_character_unlocked(cid) and self.game_mgr.selected_character != cid:
                            if hasattr(sc, "_handle_action"):
                                sc._handle_action("select_character", cid, cr.center)
                        elif not self.game_mgr.is_character_unlocked(cid) and py >= cr.bottom - 54:
                            if hasattr(sc, "_handle_action"):
                                sc._handle_action("unlock_character", cid, cr.center)
                        else:
                            sound_fx.play_click()
                        self.portrait_prep_idx = 0
                        if hasattr(sc, "_rebuild_click_targets"):
                            sc._rebuild_click_targets()
                        return True
                # 하단 페이지 전환 버튼
                if pygame.Rect(32, 934, 210, 82).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if hasattr(sc, "_handle_action"):
                        sc._handle_action("char_page_delta", -1, (140, 975))
                        sc._rebuild_click_targets()
                    return True
                if pygame.Rect(478, 934, 210, 82).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if hasattr(sc, "_handle_action"):
                        sc._handle_action("char_page_delta", 1, (580, 975))
                        sc._rebuild_click_targets()
                    return True
            return True

        if active_tab == "upgrade":
            if (self.portrait_prep_idx % 2) == 0:
                for idx_u, up_key in enumerate(STATION_UPGRADE_ORDER):
                    row_r = pygame.Rect(32, 246 + idx_u * 152, 656, 138)
                    if row_r.collidepoint(px, py):
                        self._portrait_swipe_start = None
                        if self.game_mgr.get_station_upgrade_cost(up_key) is not None and hasattr(sc, "_handle_action"):
                            sc._handle_action("upgrade_station", up_key, row_r.center)
                            sc._rebuild_click_targets()
                        else:
                            sound_fx.play_ready()
                        return True
            else:
                for idx_i, in_key in enumerate(INTERIOR_UPGRADE_ORDER):
                    row_r = pygame.Rect(32, 250 + idx_i * 186, 656, 170)
                    if row_r.collidepoint(px, py):
                        self._portrait_swipe_start = None
                        if self.game_mgr.get_interior_upgrade_cost(in_key) is not None and hasattr(sc, "_handle_action"):
                            sc._handle_action("upgrade_interior", in_key, row_r.center)
                            sc._rebuild_click_targets()
                        else:
                            sound_fx.play_ready()
                        return True
            return True

        if active_tab == "tournament":
            if btn_r.collidepoint(px, py):
                self._portrait_swipe_start = None
                opp_id = sc._get_current_tournament_opponent() if hasattr(sc, "_get_current_tournament_opponent") else "chef_jp"
                if hasattr(sc, "_handle_action"):
                    sc._handle_action("start_tournament_match", opp_id, btn_r.center)
                return True
            return True

        return True

    def _handle_portrait_native_click(self, px: int, py: int) -> bool:
        """
        720x1280 세로 화면 전용 네이티브 탭 바 / [◀][▶] 전환 버튼 / 손님 주문 카드 / 대형 조리대 / 상점 카드 / 타이틀 카드 클릭을 1:1 좌표로 직접 처리한다.
        네이티브 컨트롤을 소비했으면 True를 반환한다.
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
            return False

        # ------------------------------------------------------------------
        # 1) 타이틀 화면(TitleScene) 1:1 네이티브 클릭 처리
        # ------------------------------------------------------------------
        if self.current_scene_name == "title" and sc is not None:
            from data.chapters import CHAPTER_ORDER
            # 1-A) 상단 9개국 배경 테마 미리보기 버튼 (y=12..54)
            for idx_c, cid in enumerate(CHAPTER_ORDER):
                cr = pygame.Rect(15 + idx_c * 77, 12, 72, 42)
                if cr.collidepoint(px, py):
                    self._portrait_swipe_start = None
                    sc.preview_country = cid
                    sound_fx.play_tab_switch()
                    return True

            # 1-B) 카드 전환 바 ([◀] + 4개 카드 탭 + [▶], y=182..242)
            if pygame.Rect(12, 182, 56, 60).collidepoint(px, py):
                self._step_portrait_panel(-1)
                return True
            if pygame.Rect(652, 182, 56, 60).collidepoint(px, py):
                self._step_portrait_panel(1)
                return True
            for i in range(4):
                pill_r = pygame.Rect(74 + i * 144, 182, 140, 60)
                if pill_r.collidepoint(px, py):
                    self._portrait_swipe_start = None
                    sound_fx.play_tab_switch()
                    self.portrait_title_idx = i
                    return True

            # 1-C) 중앙 초대형 카드 패널 (24, 252, 672, 728) 클릭 시 즉시 해당 모드/마스터 탭 입장
            if pygame.Rect(24, 252, 672, 728).collidepoint(px, py):
                self._portrait_swipe_start = None
                t_idx = self.portrait_title_idx % 4
                if t_idx == 0:
                    sound_fx.play_click()
                    self.change_scene("prep", initial_tab="character", show_loading=True)
                elif t_idx == 1:
                    sound_fx.play_day_start()
                    self.game_mgr.set_mode("WORLD_TOUR")
                    self.change_scene("prep", initial_tab="chapter", show_loading=True)
                elif t_idx == 2:
                    sound_fx.play_day_start()
                    self.game_mgr.set_mode("SPECIALIST")
                    self.change_scene("prep", initial_tab="chapter", show_loading=True)
                else:
                    sound_fx.play_day_start()
                    self.game_mgr.set_mode("GLOBAL_ENDLESS")
                    self.change_scene("prep", initial_tab="chapter", show_loading=True)
                return True

            # 1-D) 하단 유틸리티 버튼 1열 (세이브 로드 / 초기화 / 사운드·화면 설정)
            if pygame.Rect(16, 1000, 212, 60).collidepoint(px, py):
                self._portrait_swipe_start = None
                loaded = self.game_mgr.load_game()
                if loaded:
                    sound_fx.play_cash()
                    sc.preview_country = self.game_mgr.current_chapter or "KR"
                else:
                    sound_fx.play_burn()
                return True
            if pygame.Rect(236, 1000, 212, 60).collidepoint(px, py):
                self._portrait_swipe_start = None
                sound_fx.play_trash()
                self.game_mgr.reset_state()
                self.game_mgr.save_game()
                sc.preview_country = "KR"
                return True
            if pygame.Rect(456, 1000, 248, 60).collidepoint(px, py):
                self._portrait_swipe_start = None
                self.open_options()
                return True

            # 1-E) 하단 유틸리티 버튼 2열 (가로모드 전환 / 전체화면 전환)
            if pygame.Rect(90, 1084, 264, 60).collidepoint(px, py):
                self._portrait_swipe_start = None
                self.toggle_orientation()
                return True
            if pygame.Rect(366, 1084, 264, 60).collidepoint(px, py):
                self._portrait_swipe_start = None
                self.toggle_fullscreen()
                return True
            return False

        # ------------------------------------------------------------------
        # 2) 준비/상점 화면(PrepScene) 1:1 네이티브 클릭 처리
        # ------------------------------------------------------------------
        if self.current_scene_name == "prep" and sc is not None:
            # 2-A) 상단 네비게이션 버튼 3종 (⬅ 타이틀 / 모드 전환 / ⚙️ 옵션, y=8..60)
            if pygame.Rect(8, 8, 118, 52).collidepoint(px, py):
                self._portrait_swipe_start = None
                sound_fx.play_click()
                self.change_scene("title", show_loading=True)
                return True
            if pygame.Rect(132, 8, 214, 52).collidepoint(px, py):
                self._portrait_swipe_start = None
                sound_fx.play_tab_switch()
                mode_cycle = {"WORLD_TOUR": "SPECIALIST", "SPECIALIST": "GLOBAL_ENDLESS", "GLOBAL_ENDLESS": "WORLD_TOUR"}
                new_mode = mode_cycle.get(self.game_mgr.mode, "WORLD_TOUR")
                self.game_mgr.set_mode(new_mode)
                self._sync_portrait_prep_idx_to_selection()
                if hasattr(sc, "_rebuild_click_targets"):
                    sc._rebuild_click_targets()
                return True
            if pygame.Rect(352, 8, 112, 52).collidepoint(px, py):
                self._portrait_swipe_start = None
                self.open_options()
                return True

            # 2-B) 4대 메인 탭 버튼 바 (y=66..118)
            portrait_tabs = [
                ("character", pygame.Rect(8, 66, 172, 52)),
                ("chapter", pygame.Rect(184, 66, 176, 52)),
                ("upgrade", pygame.Rect(364, 66, 172, 52)),
                ("tournament", pygame.Rect(540, 66, 172, 52)),
            ]
            for tkey, tr in portrait_tabs:
                if tr.collidepoint(px, py):
                    self._portrait_swipe_start = None
                    sound_fx.play_tab_switch()
                    sc.active_tab = tkey
                    self._sync_portrait_prep_idx_to_selection()
                    if hasattr(sc, "_rebuild_click_targets"):
                        sc._rebuild_click_targets()
                    return True

            # 2-C) 서브 패널 전환 바 (y=124..180): [◀] / [▶] 및 서브탭
            if pygame.Rect(8, 124, 68, 56).collidepoint(px, py):
                self._step_portrait_panel(-1)
                return True
            if pygame.Rect(644, 124, 68, 56).collidepoint(px, py):
                self._step_portrait_panel(1)
                return True

            active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
            if active_tab == "character":
                if pygame.Rect(454, 128, 182, 48).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    sound_fx.play_tab_switch()
                    self.portrait_prep_idx = 0 if (self.portrait_prep_idx % 2) == 1 else 1
                    if hasattr(sc, "_rebuild_click_targets"):
                        sc._rebuild_click_targets()
                    return True
            elif active_tab == "chapter" and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "GLOBAL_ENDLESS":
                for s_i in range(4):
                    sr = pygame.Rect(82 + s_i * 102, 128, 96, 48)
                    if sr.collidepoint(px, py):
                        self._portrait_swipe_start = None
                        sound_fx.play_tab_switch()
                        self.portrait_prep_idx = s_i
                        if hasattr(sc, "_rebuild_click_targets"):
                            sc._rebuild_click_targets()
                        return True
                if pygame.Rect(494, 128, 142, 48).collidepoint(px, py):
                    self._portrait_swipe_start = None
                    if hasattr(sc, "_handle_action"):
                        sc._handle_action("global_page_delta", 1, (640, 360))
                        sc._rebuild_click_targets()
                    return True
            elif active_tab in ("upgrade", "tournament"):
                for sub_i in range(2):
                    sr = pygame.Rect(84 + sub_i * 278, 128, 270, 48)
                    if sr.collidepoint(px, py):
                        self._portrait_swipe_start = None
                        sound_fx.play_tab_switch()
                        self.portrait_prep_idx = sub_i
                        if hasattr(sc, "_rebuild_click_targets"):
                            sc._rebuild_click_targets()
                        return True

            # 2-D) 중앙 대형 단일 카드 영역 (16, 188, 688, 848) 클릭 처리
            if pygame.Rect(16, 188, 688, 848).collidepoint(px, py):
                return self._handle_portrait_prep_card_click(px, py, sc)

            # 2-E) 최하단 [🏮 오늘 영업 시작! (START) ▶] 버튼 (80, 1162, 560, 96)
            if pygame.Rect(80, 1162, 560, 96).collidepoint(px, py):
                self._portrait_swipe_start = None
                if active_tab == "chapter" and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "SPECIALIST":
                    from data.specialist_menus import SPECIALIST_MENUS, SPECIALIST_ORDER
                    sp_id = SPECIALIST_ORDER[self.portrait_prep_idx % len(SPECIALIST_ORDER)]
                    if SPECIALIST_MENUS.get(sp_id, {}).get("is_open", False):
                        self.game_mgr.select_specialist(sp_id)
                sound_fx.play_day_start()
                self.game_mgr.ai_opponent_id = ""
                self.game_mgr.save_game()
                self.change_scene("play", show_cutscene=True, show_loading=True)
                return True

            return False

        # ------------------------------------------------------------------
        # 3) 인게임(PlayScene / DuelPlayScene) 손님 카운터, 조리대 탭 바, 대형 조리대, 하단 스킬/전환 바
        # ------------------------------------------------------------------
        if self.current_scene_name in ("play", "duel_play") and sc is not None:
            # 3-0) 상단 우측 [⚙️ 옵션] (464, 8, 108, 48) & [🏪 준비/상점] (578, 8, 134, 48) 직접 처리
            if pygame.Rect(464, 8, 108, 48).collidepoint(px, py):
                self._portrait_swipe_start = None
                self.open_options()
                return True
            if pygame.Rect(578, 8, 134, 48).collidepoint(px, py):
                self._portrait_swipe_start = None
                sound_fx.play_click()
                if self.current_scene_name == "duel_play":
                    sc.paused = not bool(getattr(sc, "paused", False))
                else:
                    self.change_scene("prep", show_loading=True)
                return True

            # 3-A) 손님 주문 카운터 (y=110..346) 터치 시: 트레이에 완성 접시가 있으면 자동 서빙 시도
            if pygame.Rect(8, 110, 704, 236).collidepoint(px, py):
                self._portrait_swipe_start = None
                if hasattr(sc, "assembly_tray"):
                    tr = sc.assembly_tray
                    tr._ensure_layout()
                    for idx, sl_r in enumerate(getattr(tr, "slot_rects", [])):
                        if idx < len(tr.dishes) and tr.dishes[idx] is not None:
                            res = tr.handle_click(sl_r.center, auto_serve_cb=sc.try_auto_serve, button=1)
                            if res and res.get("action") in ("auto_served", "served"):
                                sc._handle_station_feedback(res, (px, py))
                                return True
                return True

            # 3-B) 조리 스테이션 탭 바 (y=352..420)
            if pygame.Rect(8, 352, 52, 68).collidepoint(px, py):
                self._step_portrait_panel(-1)
                return True
            if pygame.Rect(660, 352, 52, 68).collidepoint(px, py):
                self._step_portrait_panel(1)
                return True

            is_spec = (
                self.current_scene_name == "play"
                and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "SPECIALIST"
            )
            tab_cnt = 3 if is_spec else 5
            avail_w = 592
            tab_w = (avail_w - (tab_cnt - 1) * 6) // tab_cnt
            for t_i in range(tab_cnt):
                tr = pygame.Rect(64 + t_i * (tab_w + 6), 352, tab_w, 68)
                if tr.collidepoint(px, py):
                    self._portrait_swipe_start = None
                    sound_fx.play_tab_switch()
                    self.portrait_play_idx = t_i
                    return True

            # 3-C) 중앙 초대형 단일 조리 스테이션 패널 (16, 426, 688, 752) 1:1 네이티브 클릭 처리
            if pygame.Rect(16, 426, 688, 752).collidepoint(px, py):
                return self._handle_portrait_play_station_click(px, py, sc)

            # 3-D) 최하단 빠른 전환 & 마스터 스킬 & 스토리 바 (y=1186..1268)
            if pygame.Rect(8, 1186, 116, 82).collidepoint(px, py):
                self._step_portrait_panel(-1)
                return True
            if pygame.Rect(596, 1186, 116, 82).collidepoint(px, py):
                self._step_portrait_panel(1)
                return True

            show_story_btn = (
                self.current_scene_name == "play"
                and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "WORLD_TOUR"
            )
            skill_r = pygame.Rect(130, 1186, 338 if show_story_btn else 460, 82)
            if skill_r.collidepoint(px, py):
                self._portrait_swipe_start = None
                if hasattr(sc, "activate_skill"):
                    sc.activate_skill()
                return True
            if show_story_btn and pygame.Rect(474, 1186, 116, 82).collidepoint(px, py):
                self._portrait_swipe_start = None
                sound_fx.play_click()
                if hasattr(sc, "_queue_start_cutscenes"):
                    sc._queue_start_cutscenes()
                return True

        return False

    def _map_window_point_to_logical(self, wx: float, wy: float, win_w: int, win_h: int) -> Tuple[int, int]:
        """실제 윈도우 좌표(wx, wy)를 가로/세로 모드에 맞춰 1280x720 논리 좌표(lx, ly)로 변환한다."""
        ox, oy, vp_w, vp_h, _scale = self._compute_viewport(win_w, win_h)
        if win_h > win_w or self.is_portrait_mode:
            px, py = self._window_to_portrait_point(wx, wy, win_w, win_h)
            for src_r, dst_r, _bcol in self._get_portrait_region_mappings():
                if dst_r.inflate(6, 6).collidepoint(px, py):
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
            if self.loading_active:
                lx = int(round(px * config.SCREEN_WIDTH / float(max(1, config.PORTRAIT_WIDTH))))
                ly = int(round(py * config.SCREEN_HEIGHT / float(max(1, config.PORTRAIT_HEIGHT))))
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
                return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (lx, ly), "raw_pos": (fx, fy), "button": 1, "from_finger": True})
            if event.type == pygame.FINGERUP:
                return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (lx, ly), "raw_pos": (fx, fy), "button": 1, "from_finger": True})
            return pygame.event.Event(pygame.MOUSEMOTION, {"pos": (lx, ly), "raw_pos": (fx, fy), "rel": (0, 0), "buttons": (1, 0, 0), "from_finger": True})

        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return event
        pos = getattr(event, "pos", None)
        if not pos:
            return event

        if (win_w, win_h) == (config.SCREEN_WIDTH, config.SCREEN_HEIGHT) and not self.is_portrait_mode:
            return event

        lx, ly = self._map_window_point_to_logical(float(pos[0]), float(pos[1]), win_w, win_h)

        attrs: Dict[str, Any] = {"pos": (lx, ly), "raw_pos": (float(pos[0]), float(pos[1]))}
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
    # 이벤트 처리 (옵션 모달 및 세로 모드 단일 패널 전환 우선 가로채기 지원)
    # ==========================================================================
    def handle_event(self, event: pygame.event.Event) -> None:
        now_ticks = pygame.time.get_ticks()
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN, pygame.KEYDOWN):
            if hasattr(sound_fx, "unlock_audio_on_user_gesture"):
                sound_fx.unlock_audio_on_user_gesture()

        # 모바일 브라우저/SDL2에서 터치 1회에 MOUSE*(SDL_TOUCH_MOUSEID)와 FINGER* 이벤트가 양방향 중복 발생하는 현상을 대칭 차단!
        # (SDL2는 touchstart 시 MOUSEBUTTONDOWN을 먼저 큐에 넣고 FINGERDOWN을 직후에 넣으므로 양방향 차단이 필수)
        if event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            config.MOBILE_BROWSER_DETECTED = True
            last_mouse_t = int(getattr(self, "_last_mouse_event_ticks", -9999))
            if (now_ticks - last_mouse_t) < 450:
                return
            self._last_finger_event_ticks = now_ticks
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if not getattr(event, "from_finger", False):
                last_finger_t = int(getattr(self, "_last_finger_event_ticks", -9999))
                if (now_ticks - last_finger_t) < 450:
                    return
                self._last_mouse_event_ticks = now_ticks

        mapped_event = self._remap_event_to_logical(event)

        # F10 단축키: 언제든 옵션 모달 열기/닫기, F11 단축키: 전체화면 전환
        if mapped_event.type == pygame.KEYDOWN:
            if mapped_event.key == pygame.K_F10:
                self.toggle_options()
                return
            if mapped_event.key == pygame.K_F11:
                self.toggle_fullscreen()
                return

        # 전역 물리 터치 바운스(동일 위치 85ms 이내 중복 탭) 방지 (세로 네이티브 버튼 포함)
        if mapped_event.type == pygame.MOUSEBUTTONDOWN and getattr(mapped_event, "button", 1) == 1:
            rpos = getattr(mapped_event, "raw_pos", None) or getattr(mapped_event, "pos", (-999, -999))
            last_raw_t = int(getattr(self, "_last_raw_click_ticks", -9999))
            last_raw_p = getattr(self, "_last_raw_click_pos", (-999, -999))
            is_touch_ev = bool(getattr(event, "touch", False) or getattr(mapped_event, "from_finger", False))
            if (
                rpos != (-999, -999)
                and 0 <= (now_ticks - last_raw_t) < 85
                and (now_ticks > last_raw_t or is_touch_ev)
                and abs(float(rpos[0]) - float(last_raw_p[0])) < 32
                and abs(float(rpos[1]) - float(last_raw_p[1])) < 32
            ):
                return
            self._last_raw_click_ticks = now_ticks
            self._last_raw_click_pos = rpos

        if self.loading_active:
            if mapped_event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                if self.loading_wait_for_tap and self.loading_progress >= 1.0:
                    if hasattr(sound_fx, "unlock_audio_on_user_gesture"):
                        sound_fx.unlock_audio_on_user_gesture(force_bgm_restart=True)
                    sound_fx.play_fanfare()
                    self.finish_loading()
                elif not self.loading_wait_for_tap and self.loading_progress >= 0.35:
                    if hasattr(sound_fx, "unlock_audio_on_user_gesture"):
                        sound_fx.unlock_audio_on_user_gesture(force_bgm_restart=True)
                    self.finish_loading()
            return

        if self.options_open:
            self._handle_options_event(mapped_event)
            return

        # 세로 모드(Portrait) 전용 네이티브 탭/버튼 클릭 및 좌우 스와이프 처리
        disp = pygame.display.get_surface()
        win_w, win_h = disp.get_size() if disp is not None else config.WINDOW_SIZE
        if win_h > win_w or self.is_portrait_mode:
            raw_pos = getattr(mapped_event, "raw_pos", None) or getattr(event, "pos", None)
            if raw_pos is not None:
                px, py = self._window_to_portrait_point(float(raw_pos[0]), float(raw_pos[1]), win_w, win_h)
                if mapped_event.type == pygame.MOUSEBUTTONDOWN and getattr(mapped_event, "button", 1) == 1:
                    self._portrait_swipe_start = (px, py, now_ticks)
                    # 세로 네이티브 전환 바 / 버튼 / 대형 조리대 / 상점 카드 우선 처리
                    if self._handle_portrait_native_click(px, py):
                        return
                elif mapped_event.type == pygame.MOUSEBUTTONUP and getattr(mapped_event, "button", 1) == 1:
                    if self.current_scene is not None and hasattr(self.current_scene, "assembly_tray"):
                        self.current_scene.assembly_tray.end_hold()
                    if self._portrait_swipe_start is not None:
                        sx, sy, st = self._portrait_swipe_start
                        self._portrait_swipe_start = None
                        dx = px - sx
                        dy = py - sy
                        if (
                            (now_ticks - st) <= 650
                            and abs(dx) >= 90
                            and abs(dx) > abs(dy) * 1.45
                            and 180 <= sy <= 1180
                        ):
                            self._step_portrait_panel(-1 if dx > 0 else 1)
                            return

        prev_tab = getattr(self.current_scene, "active_tab", None)
        prev_mode = getattr(self.game_mgr, "mode", None)
        if self.current_scene is not None and hasattr(self.current_scene, "handle_event"):
            self.current_scene.handle_event(mapped_event)
        # PrepScene에서 탭이나 모드가 바뀐 경우 세로 단일 패널 인덱스를 활성 항목으로 동기화
        if self.current_scene_name == "prep":
            new_tab = getattr(self.current_scene, "active_tab", None)
            new_mode = getattr(self.game_mgr, "mode", None)
            if new_tab != prev_tab or new_mode != prev_mode:
                self._sync_portrait_prep_idx_to_selection()

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
            if self.loading_progress < 1.0:
                self.loading_progress += dt / max(0.25, self.loading_duration)
                if self.loading_cycle_themes:
                    self._loading_theme_timer += dt
                    if self._loading_theme_timer >= 0.45:
                        self._loading_theme_timer = 0.0
                        self.loading_theme_idx = (self.loading_theme_idx + 1) % len(LOADING_THEMES)
            if self.loading_progress >= 1.0:
                self.loading_progress = 1.0
                if not self.loading_wait_for_tap:
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
        20:9 울트라와이드 스마트폰이나 16:10/4:3 태블릿에서 남는 좌우/상하 여백에
        검은 빈 공간 대신 실제 국가별 야시장 배경과 포차 원목 조리대 카운터를 자연스럽게 확장(Background Bleed) 렌더링한다.
        """
        win_w, win_h = surface.get_size()
        surface.fill((14, 11, 24))
        bg_country = getattr(self.game_mgr, "current_chapter", "KR") or "KR"

        if ox > 4:
            left_r = pygame.Rect(0, 0, ox, win_h)
            right_r = pygame.Rect(ox + vp_w, 0, win_w - (ox + vp_w), win_h)
            split_y = oy + int(vp_h * 0.48)
            for side_r, is_left in ((left_r, True), (right_r, False)):
                top_bg = pygame.Rect(side_r.x, 0, side_r.width, split_y)
                bot_counter = pygame.Rect(side_r.x, split_y, side_r.width, win_h - split_y)
                art_renderer.draw_country_background(surface, top_bg, country_id=bg_country, time_tick=self._loading_tick)
                art_renderer.draw_alpha_overlay(surface, top_bg, (12, 10, 22, 85))
                pygame.draw.rect(surface, (36, 26, 24), bot_counter)
                pygame.draw.line(surface, config.POCHA_WOOD, (side_r.x, split_y), (side_r.right, split_y), 4)
                border_x = side_r.right - 2 if is_left else side_r.x
                pygame.draw.line(surface, config.GOLD, (border_x, 0), (border_x, win_h), 2)

        if oy > 4:
            top_r = pygame.Rect(0, 0, win_w, oy)
            bot_r = pygame.Rect(0, oy + vp_h, win_w, win_h - (oy + vp_h))
            art_renderer.draw_country_background(surface, top_r, country_id=bg_country, time_tick=self._loading_tick)
            art_renderer.draw_alpha_overlay(surface, top_r, (12, 10, 22, 95))
            pygame.draw.rect(surface, (34, 24, 22), bot_r)
            pygame.draw.line(surface, config.GOLD, (0, top_r.bottom - 1), (win_w, top_r.bottom - 1), 2)
            pygame.draw.line(surface, config.POCHA_ORANGE, (0, bot_r.y), (win_w, bot_r.y), 2)

    def _draw_portrait_play_customers(self, portrait_surf: pygame.Surface, area: pygame.Rect, sc: Any) -> None:
        """
        세로 모드 인게임에서 손님 대기열과 주문 말풍선을 가로 압축 없이 1:1 네이티브 고해상도로 렌더링한다.
        - Customer 객체의 실제 주문 리스트(initial_orders / orders / completed_orders)를 정확히 참조하여
          국가·모드별 실제 주문 메뉴(타코야키, 생맥주, 라무네, 붕어빵 등)와 필수 토핑·가격을 표시한다.
        """
        from data.recipes import RECIPES, TOPPINGS

        bg_country = getattr(self.game_mgr, "current_chapter", "KR") or "KR"
        art_renderer.draw_country_background(portrait_surf, area, country_id=bg_country, time_tick=self._loading_tick)
        art_renderer.draw_alpha_overlay(portrait_surf, area, (14, 12, 26, 125), border_radius=12)
        pygame.draw.rect(portrait_surf, config.UI_BORDER, area, width=2, border_radius=12)

        customers = getattr(sc, "customers", []) or []
        max_slots = max(1, min(4, int(getattr(sc, "max_customer_slots", len(customers) or 3))))
        gap = 8
        card_w = (area.width - 16 - (max_slots - 1) * gap) // max_slots
        card_h = area.height - 14

        name_f = config.get_font(18 if max_slots <= 3 else 15, bold=True)
        row_name_f = config.get_font(16 if max_slots <= 3 else 14, bold=True)
        top_f = config.get_font(15 if max_slots <= 3 else 13, bold=True)
        badge_f = config.get_font(14 if max_slots <= 3 else 12, bold=True)

        for idx in range(max_slots):
            cx = area.x + 8 + idx * (card_w + gap)
            cy = area.y + 7
            crect = pygame.Rect(cx, cy, card_w, card_h)
            cust = customers[idx] if idx < len(customers) else None

            if cust is None:
                pygame.draw.rect(portrait_surf, (22, 18, 36), crect, border_radius=10)
                pygame.draw.rect(portrait_surf, (58, 52, 86), crect, width=2, border_radius=10)
                empty_s = top_f.render("손님 대기석", True, config.TEXT_SECONDARY)
                portrait_surf.blit(empty_s, empty_s.get_rect(center=crect.center))
                continue

            p_ratio = max(0.0, min(1.0, float(getattr(cust, "patience_ratio", 1.0))))
            is_vip = bool(getattr(cust, "is_vip", False))
            b_col = config.GOLD if is_vip else (config.PATIENCE_LOW if p_ratio < 0.28 else config.NEON_CYAN)
            pygame.draw.rect(portrait_surf, (28, 24, 46), crect, border_radius=10)
            pygame.draw.rect(portrait_surf, b_col, crect, width=2, border_radius=10)

            # 1) 상단 주문 말풍선 카드: 고대비 다크 카드 + 큼직한 외곽선 볼드 폰트로 시인성 극대화
            init_orders = list(getattr(cust, "initial_orders", []) or getattr(cust, "orders", []) or [])
            rem_orders = list(getattr(cust, "orders", []) or [])
            done_pool = list(getattr(cust, "completed_orders", []) or [])
            if not init_orders and rem_orders:
                init_orders = list(rem_orders)

            bub_r = pygame.Rect(crect.x + 5, crect.y + 5, crect.width - 10, 140)
            pygame.draw.rect(portrait_surf, (18, 15, 32), bub_r, border_radius=10)
            pygame.draw.rect(portrait_surf, config.GOLD if is_vip else (110, 98, 156), bub_r, width=2, border_radius=10)

            if len(init_orders) <= 1:
                rec_id = str(init_orders[0]) if init_orders else "bungeoppang_redbean"
                rec_data = RECIPES.get(rec_id, {})
                rec_name = str(rec_data.get("short_name") or rec_data.get("name") or rec_id)
                toppings = list(rec_data.get("required_toppings", []) or [])
                price_val = int(rec_data.get("sell_price", rec_data.get("base_price", 1500)))

                art_renderer.draw_food_icon(portrait_surf, (bub_r.x + 32, bub_r.y + 38), rec_id, size=52)
                nm_s = name_f.render(rec_name[:11], True, config.WHITE)
                portrait_surf.blit(nm_s, (bub_r.x + 60, bub_r.y + 10))

                pr_s = top_f.render(f"💰 {price_val:,}원", True, config.GOLD)
                portrait_surf.blit(pr_s, (bub_r.x + 60, bub_r.y + 40))

                tp_pill = pygame.Rect(bub_r.x + 6, bub_r.bottom - 58, bub_r.width - 12, 32)
                if toppings:
                    t_names = [f"+{TOPPINGS.get(t, {}).get('short_name', TOPPINGS.get(t, {}).get('name', t))}" for t in toppings[:2]]
                    t_str = " ".join(t_names)
                    pygame.draw.rect(portrait_surf, (58, 36, 86), tp_pill, border_radius=7)
                    pygame.draw.rect(portrait_surf, config.NEON_YELLOW, tp_pill, width=1, border_radius=7)
                    tp_s = top_f.render(t_str[:16], True, config.NEON_YELLOW)
                    portrait_surf.blit(tp_s, tp_s.get_rect(center=tp_pill.center))
                else:
                    pygame.draw.rect(portrait_surf, (32, 52, 48), tp_pill, border_radius=7)
                    pygame.draw.rect(portrait_surf, config.NEON_GREEN, tp_pill, width=1, border_radius=7)
                    tp_s = badge_f.render("기본맛 · 즉시서빙", True, config.NEON_GREEN)
                    portrait_surf.blit(tp_s, tp_s.get_rect(center=tp_pill.center))
            else:
                # 2개 이상 주문 손님(직장인/VIP: 메인 안주 + 음료 등)
                for o_idx, r_id in enumerate(init_orders[:2]):
                    row_y = bub_r.y + 6 + o_idx * 54
                    row_r = pygame.Rect(bub_r.x + 5, row_y, bub_r.width - 10, 50)
                    is_done = False
                    if r_id in done_pool:
                        is_done = True
                        done_pool.remove(r_id)

                    row_bg = (24, 58, 38) if is_done else (34, 28, 58)
                    row_bdr = config.NEON_GREEN if is_done else (92, 82, 134)
                    pygame.draw.rect(portrait_surf, row_bg, row_r, border_radius=7)
                    pygame.draw.rect(portrait_surf, row_bdr, row_r, width=1, border_radius=7)

                    r_data = RECIPES.get(r_id, {})
                    r_name = str(r_data.get("short_name") or r_data.get("name") or r_id)
                    r_tops = list(r_data.get("required_toppings", []) or [])
                    r_price = int(r_data.get("sell_price", r_data.get("base_price", 1500)))

                    art_renderer.draw_food_icon(portrait_surf, (row_r.x + 22, row_r.centery), r_id, size=38)
                    rn_s = row_name_f.render(r_name[:11], True, config.WHITE)
                    portrait_surf.blit(rn_s, (row_r.x + 42, row_r.y + 3))

                    if is_done:
                        st_s = badge_f.render("✓ 서빙완료", True, config.NEON_GREEN)
                    elif r_tops:
                        t_short = " ".join(f"+{TOPPINGS.get(t, {}).get('short_name', TOPPINGS.get(t, {}).get('name', t))}" for t in r_tops[:2])
                        st_s = badge_f.render(t_short[:15], True, config.NEON_YELLOW)
                    else:
                        st_s = badge_f.render(f"💰 {r_price:,}원", True, config.GOLD)
                    portrait_surf.blit(st_s, (row_r.x + 42, row_r.y + 26))

            # 인내심 게이지 바
            p_bar = pygame.Rect(bub_r.x + 8, bub_r.bottom - 18, bub_r.width - 16, 11)
            pygame.draw.rect(portrait_surf, (40, 36, 52), p_bar, border_radius=5)
            p_col = config.PATIENCE_HIGH if p_ratio > 0.5 else (config.PATIENCE_MID if p_ratio > 0.25 else config.PATIENCE_LOW)
            pw = int(p_bar.width * p_ratio)
            if pw > 0:
                pygame.draw.rect(portrait_surf, p_col, (p_bar.x, p_bar.y, pw, p_bar.height), border_radius=5)

            # 2) 하단 손님 도트 캐릭터 & VIP/손님 유형 배지
            av_r = pygame.Rect(crect.centerx - 28, crect.bottom - 72, 56, 66)
            mood = cust.get_mood() if hasattr(cust, "get_mood") else getattr(cust, "mood", "NORMAL")
            c_type = getattr(cust, "customer_type", "student")
            art_renderer.draw_customer(portrait_surf, av_r, customer_type=c_type, mood=mood, time_tick=self._loading_tick)
            if is_vip:
                vip_b = pygame.Rect(crect.x + 6, crect.bottom - 28, 62, 22)
                pygame.draw.rect(portrait_surf, (218, 148, 24), vip_b, border_radius=6)
                vs = badge_f.render("👑VIP", True, config.WHITE)
                portrait_surf.blit(vs, vs.get_rect(center=vip_b.center))

    def _draw_portrait_play_active_station(
        self,
        portrait_surf: pygame.Surface,
        dst_r: pygame.Rect,
        sc: Any,
        border_col: Tuple[int, int, int],
    ) -> bool:
        """
        세로 모드 인게임(play / duel_play)에서 하단 메인 조리 패널(688x752)을
        비율 왜곡(3.02x 가로 늘림) 없이 1:1 네이티브 해상도로 직접 렌더링한다.
        """
        if dst_r.y < 300 or dst_r.height < 500:
            return False
        is_spec = (
            self.current_scene_name == "play"
            and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "SPECIALIST"
        )
        if is_spec:
            idx = self.portrait_play_idx % 3
            sp_st = getattr(sc, "specialist_station", None)
            tray = getattr(sc, "assembly_tray", None)
            if idx in (0, 1) and sp_st is not None:
                orig_r = sp_st.rect.copy()
                orig_in = sp_st.input_rect.copy()
                orig_app = sp_st.appliance_rect.copy()
                try:
                    if idx == 0:
                        sp_st.input_rect = dst_r.copy()
                        sp_st.appliance_rect = pygame.Rect(-2000, 426, 688, 752)
                    else:
                        sp_st.input_rect = pygame.Rect(-2000, 426, 688, 752)
                        sp_st.appliance_rect = dst_r.copy()
                    sp_st.rect = dst_r.copy()
                    sp_st._rebuild_layout()
                    if idx == 0:
                        sp_st._draw_input_panel(portrait_surf, self._loading_tick)
                    else:
                        sp_st._draw_appliance_panel(portrait_surf, self._loading_tick)
                    pygame.draw.rect(portrait_surf, border_col, dst_r, width=3, border_radius=12)
                    return True
                finally:
                    sp_st.rect = orig_r
                    sp_st.input_rect = orig_in
                    sp_st.appliance_rect = orig_app
                    sp_st._rebuild_layout()
            elif idx == 2 and tray is not None:
                orig_r = tray.rect.copy()
                try:
                    tray.rect = dst_r.copy()
                    tray._rebuild_layout()
                    tray.draw(portrait_surf)
                    pygame.draw.rect(portrait_surf, border_col, dst_r, width=3, border_radius=12)
                    return True
                finally:
                    tray.rect = orig_r
                    tray._rebuild_layout()
            return False

        idx = self.portrait_play_idx % 5
        station_specs = [
            (getattr(sc, "mold_station", None), "mold", "몰드 조리대", "겉바속촉 대표 길거리 간식"),
            (getattr(sc, "dispenser_station", None), "dispenser", "음료 디스펜서", "뜨끈한 국물·음료 자동 서버"),
            (getattr(sc, "assembly_tray", None), "tray", "조립·무한 적재 트레이", "토핑 조립 및 무한 적재·서빙"),
            (getattr(sc, "grill_station", None), "grill", "철판 그릴", "직화 구이 & 특제 소스 조합"),
            (getattr(sc, "batch_pot_station", None), "batch_pot", "대량 조리 팬", "한 번에 3인분 대량 조리 기구"),
        ]
        target_st, slot_key, slot_title, sub_desc = station_specs[idx]
        if target_st is None:
            return False

        orig_r = target_st.rect.copy()
        try:
            target_st.rect = dst_r.copy()
            if hasattr(target_st, "_rebuild_layout"):
                target_st._rebuild_layout()
            target_st.draw(portrait_surf)
            if (
                slot_key != "tray"
                and hasattr(self.game_mgr, "is_slot_unlocked_in_story")
                and not self.game_mgr.is_slot_unlocked_in_story(slot_key)
            ):
                st_name = str(getattr(target_st, "meta", {}).get("name", slot_title))
                if hasattr(sc, "_draw_locked_slot_cover"):
                    sc._draw_locked_slot_cover(portrait_surf, dst_r, slot_key, st_name, sub_desc)
            pygame.draw.rect(portrait_surf, border_col, dst_r, width=3, border_radius=12)
            return True
        finally:
            target_st.rect = orig_r
            if hasattr(target_st, "_rebuild_layout"):
                target_st._rebuild_layout()

    def _draw_portrait_title_card_native(
        self,
        portrait_surf: pygame.Surface,
        card_r: pygame.Rect,
        sc: Any,
    ) -> None:
        """타이틀 화면(TitleScene)의 중앙 대형 카드(24, 252, 672, 728)를 확대 블러 없이 1:1 네이티브 고해상도로 직접 렌더링한다."""
        from data.chapters import CHAPTER_ORDER, CHAPTERS
        from data.characters import CHARACTERS
        from data.specialist_menus import SPECIALIST_MENUS

        t_idx = self.portrait_title_idx % 4
        border_cols = [config.NEON_GREEN, config.POCHA_ORANGE, config.GOLD, config.NEON_CYAN]
        b_col = border_cols[t_idx]

        pygame.draw.rect(portrait_surf, (22, 18, 38), card_r, border_radius=18)
        pygame.draw.rect(portrait_surf, b_col, card_r, width=3, border_radius=18)

        title_f = config.get_font(28, bold=True)
        sec_f = config.get_font(22, bold=True)
        body_f = config.get_font(18, bold=True)
        sub_f = config.get_font(16, bold=True)
        cta_f = config.get_font(22, bold=True)

        if t_idx == 0:
            # 카드 1: 현재 출전 마스터 셰프 프로필
            char_d = self.game_mgr.get_selected_character_data()
            c_country = str(char_d.get("country", "KR"))

            stage_r = pygame.Rect(card_r.x + 20, card_r.y + 20, card_r.width - 40, 214)
            art_renderer.draw_country_background(portrait_surf, stage_r, country_id=c_country, time_tick=self._loading_tick)
            art_renderer.draw_alpha_overlay(portrait_surf, stage_r, (14, 12, 26, 155), border_radius=14)
            pygame.draw.rect(portrait_surf, config.NEON_GREEN, stage_r, width=2, border_radius=14)

            av_r = pygame.Rect(stage_r.x + 22, stage_r.y + 25, 164, 164)
            pygame.draw.rect(portrait_surf, (28, 24, 48), av_r.inflate(8, 8), border_radius=16)
            pygame.draw.rect(portrait_surf, config.GOLD, av_r.inflate(8, 8), width=2, border_radius=16)
            art_renderer.draw_chef_avatar(
                portrait_surf,
                av_r,
                character_id=self.game_mgr.selected_character,
                state="COOKING",
                time_tick=self._loading_tick,
            )

            tx = av_r.right + 24
            bdg = sub_f.render("👨‍🍳 출전 마스터 셰프 프로필 (1/4)", True, config.NEON_GREEN)
            nm = title_f.render(f"[{char_d.get('region_name', c_country)}] {char_d['name']}", True, config.WHITE)
            tt = sec_f.render(f"★ {char_d.get('title', '포차 마스터')}", True, config.GOLD)
            cnt_s = body_f.render(
                f"영입 마스터: {len(self.game_mgr.unlocked_characters)} / {len(CHARACTERS)}명",
                True,
                config.NEON_CYAN,
            )
            portrait_surf.blit(bdg, (tx, stage_r.y + 24))
            portrait_surf.blit(nm, (tx, stage_r.y + 62))
            portrait_surf.blit(tt, (tx, stage_r.y + 114))
            portrait_surf.blit(cnt_s, (tx, stage_r.y + 160))

            p_box = pygame.Rect(card_r.x + 20, card_r.y + 248, card_r.width - 40, 162)
            pygame.draw.rect(portrait_surf, (30, 26, 52), p_box, border_radius=14)
            pygame.draw.rect(portrait_surf, config.UI_BORDER, p_box, width=2, border_radius=14)
            p_hdr = sec_f.render(f"🌟 고유 패시브: {char_d.get('passive_name', '장인의 손길')}", True, config.NEON_GREEN)
            p_dsc = body_f.render(str(char_d.get("passive_desc", ""))[:36], True, config.WHITE)
            s_hdr = sec_f.render(
                f"⚡ 액티브 스킬: {char_d.get('skill_name', '')} (쿨타임 {int(char_d.get('cooldown', 35))}초)",
                True,
                config.GOLD,
            )
            s_dsc = body_f.render(str(char_d.get("skill_desc", ""))[:36], True, config.NEON_YELLOW)
            portrait_surf.blit(p_hdr, (p_box.x + 18, p_box.y + 14))
            portrait_surf.blit(p_dsc, (p_box.x + 18, p_box.y + 50))
            portrait_surf.blit(s_hdr, (p_box.x + 18, p_box.y + 88))
            portrait_surf.blit(s_dsc, (p_box.x + 18, p_box.y + 124))

            stat_box = pygame.Rect(card_r.x + 20, card_r.y + 424, card_r.width - 40, 174)
            pygame.draw.rect(portrait_surf, (28, 22, 44), stat_box, border_radius=14)
            pygame.draw.rect(portrait_surf, config.GOLD, stat_box, width=2, border_radius=14)
            rnd_names = ["32강전", "16강전", "8강전", "4강 준결승", "결승전", "챔피언"]
            r_idx = min(5, int(getattr(self.game_mgr, "tournament_round_idx", 0)))
            st_lines = [
                (f"💰 보유 자산: {self.game_mgr.gold:,}원   |   🗺️ 해금 국가: {len(self.game_mgr.unlocked_chapters)}/{len(CHAPTER_ORDER)}개국", config.GOLD),
                (f"📍 현재 투어: [{self.game_mgr.current_chapter}] Day {self.game_mgr.day}   |   🏆 월드컵: {rnd_names[r_idx]}", config.WHITE),
                ("💡 상단 9개국 국기 버튼을 눌러 야시장 배경을 미리 감상해보세요!", config.NEON_CYAN),
            ]
            for l_i, (l_txt, l_col) in enumerate(st_lines):
                ls = body_f.render(l_txt, True, l_col)
                portrait_surf.blit(ls, (stat_box.x + 18, stat_box.y + 20 + l_i * 48))

            cta_r = pygame.Rect(card_r.x + 24, card_r.bottom - 110, card_r.width - 48, 88)
            pygame.draw.rect(portrait_surf, (38, 148, 86), cta_r, border_radius=14)
            pygame.draw.rect(portrait_surf, config.GOLD, cta_r, width=3, border_radius=14)
            cs = cta_f.render("👨‍🍳 32인 마스터 셰프 선택 / 변경하기 (터치) ▶", True, config.WHITE)
            portrait_surf.blit(cs, cs.get_rect(center=cta_r.center))

        elif t_idx == 1:
            # 카드 2: 9개국 월드 스트리트 푸드 투어 (스토리 캠페인)
            ch_id = getattr(self.game_mgr, "current_chapter", "KR") or "KR"
            ch_d = CHAPTERS.get(ch_id, CHAPTERS["KR"])
            stage_r = pygame.Rect(card_r.x + 20, card_r.y + 20, card_r.width - 40, 214)
            art_renderer.draw_country_background(portrait_surf, stage_r, country_id=ch_id, time_tick=self._loading_tick)
            art_renderer.draw_alpha_overlay(portrait_surf, stage_r, (14, 10, 24, 150), border_radius=14)
            pygame.draw.rect(portrait_surf, config.POCHA_ORANGE, stage_r, width=2, border_radius=14)

            b_s = sub_f.render("🗺️ MODE 1 · 메인 스토리 캠페인 (2/4)", True, config.NEON_YELLOW)
            t_s = title_f.render("9개국 월드 스트리트 푸드 투어", True, config.WHITE)
            c_s = sec_f.render(f"📍 현재 챕터: [{ch_id}] {ch_d['name']} · Day {self.game_mgr.day}", True, config.GOLD)
            portrait_surf.blit(b_s, (stage_r.x + 22, stage_r.y + 18))
            portrait_surf.blit(t_s, (stage_r.x + 22, stage_r.y + 52))
            portrait_surf.blit(c_s, (stage_r.x + 22, stage_r.y + 100))

            for f_i, fid in enumerate(["bungeoppang_redbean", "takoyaki_mayo", "taco_salsa", "kebab_lamb", "boba_milktea"]):
                fx = stage_r.x + 76 + f_i * 120
                fy = stage_r.bottom - 38
                pygame.draw.circle(portrait_surf, (28, 22, 46), (fx, fy), 28)
                pygame.draw.circle(portrait_surf, config.GOLD, (fx, fy), 28, width=1)
                art_renderer.draw_food_icon(portrait_surf, (fx, fy), fid, size=46)

            bullets = [
                ("🇰🇷 포차 재기 스토리", "폐업한 식당을 팔고 한국 붕어빵 리어카부터 시작하는 세계 정복기", config.GOLD),
                ("🔓 일차별 기구 해금", "Day 1 몰드 ➔ Day 2 음료·트레이 ➔ Day 3 그릴 ➔ Day 4 대량팬·스킬", config.NEON_CYAN),
                ("📦 무한 적재 & 폐기 손실", "트레이에 음식을 무제한 미리 적재 가능! 단, 마감 시 잔여분은 원가 차감", config.NEON_GREEN),
                ("★ 9개국 현지 마스터 영입", "한국·일본·멕시코·대만·중국·인도·미국·러시아·브라질 챕터 클리어 보상", config.WHITE),
            ]
            for b_i, (b_head, b_desc, b_c) in enumerate(bullets):
                br = pygame.Rect(card_r.x + 20, card_r.y + 248 + b_i * 86, card_r.width - 40, 76)
                pygame.draw.rect(portrait_surf, (30, 24, 48), br, border_radius=12)
                pygame.draw.rect(portrait_surf, config.UI_BORDER, br, width=1, border_radius=12)
                hs = body_f.render(b_head, True, b_c)
                ds = sub_f.render(b_desc, True, config.TEXT_PRIMARY)
                portrait_surf.blit(hs, (br.x + 16, br.y + 10))
                portrait_surf.blit(ds, (br.x + 16, br.y + 42))

            cta_r = pygame.Rect(card_r.x + 24, card_r.bottom - 110, card_r.width - 48, 88)
            pygame.draw.rect(portrait_surf, (232, 96, 34), cta_r, border_radius=14)
            pygame.draw.rect(portrait_surf, config.GOLD, cta_r, width=3, border_radius=14)
            cs = cta_f.render("🗺️ 9개국 월드 투어 출발하기! (START) ▶", True, config.WHITE)
            portrait_surf.blit(cs, cs.get_rect(center=cta_r.center))

        elif t_idx == 2:
            # 카드 3: 8대 길거리 음식 장인 모드 (Specialist Mode)
            sp = self.game_mgr.get_selected_specialist_data() if hasattr(self.game_mgr, "get_selected_specialist_data") else SPECIALIST_MENUS["bungeo"]
            sp_id = str(sp.get("id", "bungeo"))
            sp_day = int(getattr(self.game_mgr, "specialist_days", {}).get(sp_id, 1))

            stage_r = pygame.Rect(card_r.x + 20, card_r.y + 20, card_r.width - 40, 214)
            art_renderer.draw_country_background(portrait_surf, stage_r, country_id=str(sp.get("country", "KR")), time_tick=self._loading_tick)
            art_renderer.draw_alpha_overlay(portrait_surf, stage_r, (16, 12, 28, 155), border_radius=14)
            pygame.draw.rect(portrait_surf, config.GOLD, stage_r, width=2, border_radius=14)

            b_s = sub_f.render("🎯 MODE 2 · 단일 품목 극한 장인 타이쿤 (3/4)", True, config.NEON_CYAN)
            t_s = title_f.render("8대 길거리 음식 장인 모드", True, config.GOLD)
            c_s = sec_f.render(f"{sp.get('emoji', '🐟')} 현재 선택 종목: {sp.get('name', '붕어빵 장인')} · Day {sp_day}", True, config.WHITE)
            portrait_surf.blit(b_s, (stage_r.x + 22, stage_r.y + 18))
            portrait_surf.blit(t_s, (stage_r.x + 22, stage_r.y + 52))
            portrait_surf.blit(c_s, (stage_r.x + 22, stage_r.y + 100))

            for f_i, fid in enumerate(["bungeoppang_redbean", "odeng_clean_wave", "odeng_red_spicy", "skewer_plain", "skewer_spicy"]):
                fx = stage_r.x + 76 + f_i * 120
                fy = stage_r.bottom - 38
                pygame.draw.circle(portrait_surf, (28, 22, 46), (fx, fy), 28)
                pygame.draw.circle(portrait_surf, config.GOLD, (fx, fy), 28, width=1)
                art_renderer.draw_food_icon(portrait_surf, (fx, fy), fid, size=46)

            bullets = [
                ("🔥 6구 대형 전문 화로", "오직 하나의 종목만 6구 대형 전문 화로로 승부하는 깊이 있는 손맛!", config.GOLD),
                ("🥣 3단계 장인 조리 공정", "① 속재료/육수/원육 투입 ➔ ② 6구 화로 조리 ➔ ③ 특제 토핑 조립", config.NEON_CYAN),
                ("✨ 1차 오픈 3대 인기 종목", "🐟원조 붕어빵 · 🍢심야 오뎅바 · 🔥참숯 닭꼬치 각 8종 메뉴 완비", config.NEON_GREEN),
                ("🛠️ 장인 전용 업그레이드", "반죽 숙성·육수 가마솥·참숯 화로 등 종목 특화 설비 강화 시스템", config.WHITE),
            ]
            for b_i, (b_head, b_desc, b_c) in enumerate(bullets):
                br = pygame.Rect(card_r.x + 20, card_r.y + 248 + b_i * 86, card_r.width - 40, 76)
                pygame.draw.rect(portrait_surf, (30, 24, 48), br, border_radius=12)
                pygame.draw.rect(portrait_surf, config.UI_BORDER, br, width=1, border_radius=12)
                hs = body_f.render(b_head, True, b_c)
                ds = sub_f.render(b_desc, True, config.TEXT_PRIMARY)
                portrait_surf.blit(hs, (br.x + 16, br.y + 10))
                portrait_surf.blit(ds, (br.x + 16, br.y + 42))

            cta_r = pygame.Rect(card_r.x + 24, card_r.bottom - 110, card_r.width - 48, 88)
            pygame.draw.rect(portrait_surf, (218, 134, 24), cta_r, border_radius=14)
            pygame.draw.rect(portrait_surf, config.WHITE, cta_r, width=3, border_radius=14)
            cs = cta_f.render("🎯 장인 모드 종목 선택 & 영업 시작! ▶", True, config.WHITE)
            portrait_surf.blit(cs, cs.get_rect(center=cta_r.center))

        else:
            # 카드 4: 글로벌 올스타 무한 포차 (Global Endless Mode 단독 풀사이즈 카드)
            stage_r = pygame.Rect(card_r.x + 20, card_r.y + 20, card_r.width - 40, 214)
            art_renderer.draw_country_background(portrait_surf, stage_r, country_id="TW", time_tick=self._loading_tick)
            art_renderer.draw_alpha_overlay(portrait_surf, stage_r, (14, 12, 28, 155), border_radius=14)
            pygame.draw.rect(portrait_surf, config.NEON_CYAN, stage_r, width=2, border_radius=14)

            b1 = sub_f.render("🏮 MODE 3 · 엔드게임 무한 서바이벌 (4/4)", True, config.NEON_CYAN)
            t1 = title_f.render("글로벌 올스타 무한 포차", True, config.WHITE)
            r1 = sec_f.render(
                f"🔥 최고 기록: Endless Day {getattr(self.game_mgr, 'endless_day', 1)}  |  36종 기구 자유 조합",
                True,
                config.GOLD,
            )
            portrait_surf.blit(b1, (stage_r.x + 22, stage_r.y + 18))
            portrait_surf.blit(t1, (stage_r.x + 22, stage_r.y + 52))
            portrait_surf.blit(r1, (stage_r.x + 22, stage_r.y + 100))

            for f_i, fid in enumerate(["bungeoppang_redbean", "takoyaki_mayo", "taco_salsa", "boba_milktea", "mala_tang"]):
                fx = stage_r.x + 76 + f_i * 120
                fy = stage_r.bottom - 38
                pygame.draw.circle(portrait_surf, (26, 24, 52), (fx, fy), 28)
                pygame.draw.circle(portrait_surf, config.NEON_CYAN, (fx, fy), 28, width=1)
                art_renderer.draw_food_icon(portrait_surf, (fx, fy), fid, size=46)

            bullets = [
                ("🛠️ 36종 기구 자유 조합", "몰드·그릴·대량팬·음료 4대 슬롯에 9개국 기구를 내 맘대로 장착!", config.NEON_CYAN),
                ("🌍 전 세계 올스타 단골 총출동", "9개국 현지 손님과 미식 평론가 VIP가 끝없이 방문하는 올스타 포차!", config.GOLD),
                ("📦 무한 적재 & 재고 관리", "조립 트레이 무한 적재 지원! 마감 시 남은 재고 원가 페널티 긴장감", config.NEON_GREEN),
                ("🏆 글로벌 최고 일차 도전", "스토리 제약 없이 처음부터 모든 해금 기구와 마스터 스킬로 기록 경쟁!", config.WHITE),
            ]
            for b_i, (b_head, b_desc, b_c) in enumerate(bullets):
                br = pygame.Rect(card_r.x + 20, card_r.y + 248 + b_i * 86, card_r.width - 40, 76)
                pygame.draw.rect(portrait_surf, (26, 24, 52), br, border_radius=12)
                pygame.draw.rect(portrait_surf, config.UI_BORDER, br, width=1, border_radius=12)
                hs = body_f.render(b_head, True, b_c)
                ds = sub_f.render(b_desc, True, config.TEXT_PRIMARY)
                portrait_surf.blit(hs, (br.x + 16, br.y + 10))
                portrait_surf.blit(ds, (br.x + 16, br.y + 42))

            cta1 = pygame.Rect(card_r.x + 24, card_r.bottom - 110, card_r.width - 48, 88)
            pygame.draw.rect(portrait_surf, (34, 118, 168), cta1, border_radius=14)
            pygame.draw.rect(portrait_surf, config.GOLD, cta1, width=3, border_radius=14)
            c1_s = cta_f.render("🏮 글로벌 올스타 무한 포차 입장하기! ▶", True, config.WHITE)
            portrait_surf.blit(c1_s, c1_s.get_rect(center=cta1.center))

    def _draw_portrait_prep_card_native(
        self,
        portrait_surf: pygame.Surface,
        card_r: pygame.Rect,
        sc: Any,
    ) -> None:
        """
        준비/상점 화면(PrepScene)의 중앙 대형 카드(16, 188, 688, 848)를
        가로/세로 늘림 없이 1:1 네이티브 고해상도로 직접 렌더링한다.
        (_handle_portrait_prep_card_click의 터치 영역과 100% 일치)
        """
        from data.chapters import CHAPTER_ORDER, CHAPTERS, SLOT_TYPES, get_stations_by_slot
        from data.characters import CHARACTERS, COUNTRY_FILTER_ORDER
        from data.recipes import RECIPES
        from data.specialist_menus import SPECIALIST_MENUS, SPECIALIST_ORDER
        from data.upgrades import (
            INTERIOR_UPGRADE_ORDER,
            INTERIOR_UPGRADES,
            STATION_UPGRADE_ORDER,
            STATION_UPGRADES,
        )

        active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
        pygame.draw.rect(portrait_surf, (22, 18, 38), card_r, border_radius=16)
        pygame.draw.rect(portrait_surf, config.GOLD, card_r, width=3, border_radius=16)

        title_f = config.get_font(26, bold=True)
        sec_f = config.get_font(21, bold=True)
        body_f = config.get_font(18, bold=True)
        sub_f = config.get_font(16, bold=True)
        xs_f = config.get_font(14, bold=True)
        cta_f = config.get_font(22, bold=True)
        btn_r = pygame.Rect(36, 932, 648, 84)

        if active_tab == "chapter":
            mode = getattr(self.game_mgr, "mode", "WORLD_TOUR")
            if mode == "SPECIALIST":
                idx = self.portrait_prep_idx % len(SPECIALIST_ORDER)
                sp_id = SPECIALIST_ORDER[idx]
                sp_d = SPECIALIST_MENUS[sp_id]
                is_open = bool(sp_d.get("is_open", False))
                is_sel = is_open and (self.game_mgr.selected_specialist == sp_id)
                sp_day = int(getattr(self.game_mgr, "specialist_days", {}).get(sp_id, 1))
                sp_stars = int(getattr(self.game_mgr, "specialist_stars", {}).get(sp_id, 0))

                stage_r = pygame.Rect(36, 208, 648, 210)
                art_renderer.draw_country_background(
                    portrait_surf, stage_r, country_id=str(sp_d.get("country", "KR")), time_tick=self._loading_tick
                )
                art_renderer.draw_alpha_overlay(portrait_surf, stage_r, (14, 12, 26, 155), border_radius=14)
                pygame.draw.rect(portrait_surf, config.GOLD if is_sel else config.UI_BORDER, stage_r, width=2, border_radius=14)

                recs = list(sp_d.get("all_recipes") or sp_d.get("base_recipes") or [])
                default_icon_map = {
                    "bungeo": "bungeoppang_redbean",
                    "odeng": "odeng_clean_wave",
                    "skewer": "skewer_plain",
                    "takoyaki": "takoyaki_mayo",
                    "tteokbokki": "tteokbokki_cheese",
                    "taco": "taco_salsa",
                    "boba": "boba_milktea",
                    "crepe": "crepe_berry",
                }
                main_icon_id = str(recs[0]) if recs else default_icon_map.get(sp_id, "bungeoppang_redbean")
                art_renderer.draw_food_icon(portrait_surf, (stage_r.x + 84, stage_r.centery), main_icon_id, size=88)

                tx = stage_r.x + 164
                t_s = title_f.render(f"{sp_d['emoji']} {sp_d['name']}", True, config.GOLD)
                s_s = body_f.render(str(sp_d.get("subtitle", "6구 전문 화로 장인 모드")), True, config.NEON_CYAN)
                d_s = sec_f.render(
                    f"📅 Day {sp_day}   |   ⭐ {'★' * sp_stars}{'☆' * (3 - sp_stars)}"
                    if is_open
                    else "🚧 2차 업데이트 오픈 예정 종목",
                    True,
                    config.WHITE if is_open else config.TEXT_SECONDARY,
                )
                st_b = sub_f.render(
                    "✓ 현재 선택된 장인 종목 (바로 영업 시작 가능!)"
                    if is_sel
                    else ("터치하여 이 종목으로 즉시 영업 시작!" if is_open else "1차 오픈 종목(붕어빵·오뎅바·닭꼬치)을 선택하세요"),
                    True,
                    config.NEON_GREEN if is_sel else (config.GOLD if is_open else config.TEXT_SECONDARY),
                )
                portrait_surf.blit(t_s, (tx, stage_r.y + 22))
                portrait_surf.blit(s_s, (tx, stage_r.y + 66))
                portrait_surf.blit(d_s, (tx, stage_r.y + 108))
                portrait_surf.blit(st_b, (tx, stage_r.y + 154))

                # 대표 메뉴 4종 2x2 그리드 (오픈된 종목은 실제 레시피 4종, 예정 종목은 preview_flavors 표시)
                if is_open and recs:
                    preview_rids = [recs[0], recs[1], recs[min(4, len(recs) - 1)], recs[min(5, len(recs) - 1)]] if len(recs) >= 6 else recs[:4]
                    for r_i, rid in enumerate(preview_rids[:4]):
                        c_col = r_i % 2
                        c_row = r_i // 2
                        mr = pygame.Rect(36 + c_col * 328, 432 + c_row * 116, 320, 106)
                        pygame.draw.rect(portrait_surf, (30, 26, 50), mr, border_radius=12)
                        pygame.draw.rect(portrait_surf, config.UI_BORDER, mr, width=1, border_radius=12)
                        rdata = RECIPES.get(rid, {})
                        rname = str(rdata.get("name", rid))
                        rprice = int(rdata.get("price", rdata.get("sell_price", rdata.get("base_price", 1500))))
                        art_renderer.draw_food_icon(portrait_surf, (mr.x + 42, mr.centery), rid, size=54)
                        rn_s = body_f.render(rname[:12], True, config.WHITE)
                        rp_s = sub_f.render(f"💰 판매가 {rprice:,}원", True, config.GOLD)
                        portrait_surf.blit(rn_s, (mr.x + 80, mr.y + 20))
                        portrait_surf.blit(rp_s, (mr.x + 80, mr.y + 56))
                else:
                    flavors = list(sp_d.get("preview_flavors", []))[:4]
                    for r_i, flv in enumerate(flavors):
                        c_col = r_i % 2
                        c_row = r_i // 2
                        mr = pygame.Rect(36 + c_col * 328, 432 + c_row * 116, 320, 106)
                        pygame.draw.rect(portrait_surf, (26, 22, 42), mr, border_radius=12)
                        pygame.draw.rect(portrait_surf, config.UI_BORDER, mr, width=1, border_radius=12)
                        art_renderer.draw_food_icon(portrait_surf, (mr.x + 42, mr.centery), main_icon_id, size=50)
                        rn_s = body_f.render(str(flv)[:12], True, config.TEXT_PRIMARY)
                        rp_s = sub_f.render("🚧 차후 업데이트 예정", True, config.TEXT_SECONDARY)
                        portrait_surf.blit(rn_s, (mr.x + 80, mr.y + 20))
                        portrait_surf.blit(rp_s, (mr.x + 80, mr.y + 56))

                # 장인 조리 공정 안내 박스
                wf_r = pygame.Rect(36, 672, 648, 240)
                pygame.draw.rect(portrait_surf, (28, 24, 46), wf_r, border_radius=14)
                pygame.draw.rect(portrait_surf, config.NEON_CYAN, wf_r, width=2, border_radius=14)
                wh = sec_f.render(f"🔥 {sp_d['name']} 3단계 조리 가이드", True, config.GOLD)
                portrait_surf.blit(wh, (wf_r.x + 20, wf_r.y + 16))
                if sp_id == "odeng":
                    step2_line = "② [6구 오뎅솥 탭] 육수에서 어묵이 다 익어 ✨완성되면 터치해 꺼내기!"
                elif sp_id == "skewer":
                    step2_line = "② [6구 참숯화로 탭] 참숯에서 꼬치가 노릇하게 ✨완성되면 터치해 꺼내기!"
                else:
                    step2_line = "② [6구 전문화로 탭] 앞면이 익으면 🔄뒤집기 터치 ➔ ✨완성 시 터치해 꺼내기!"
                w_steps = [
                    f"① [{sp_d.get('input_panel_title', '속재료 투입')}] 손님 주문에 맞는 베이스를 선택해 화로에 투입!",
                    step2_line,
                    "③ [조립 트레이 탭] 기본 메뉴는 즉시 서빙, 토핑 메뉴는 토핑 추가 후 서빙!",
                    "💡 마감 시 트레이나 화로에 남은 음식은 재료 원가만큼 폐기 손실이 차감됩니다.",
                ]
                for w_i, w_line in enumerate(w_steps):
                    ws = sub_f.render(w_line, True, config.NEON_YELLOW if w_i == 3 else config.WHITE)
                    portrait_surf.blit(ws, (wf_r.x + 20, wf_r.y + 62 + w_i * 42))

                if is_open:
                    pygame.draw.rect(portrait_surf, (42, 152, 86) if is_sel else (232, 98, 36), btn_r, border_radius=14)
                    pygame.draw.rect(portrait_surf, config.GOLD, btn_r, width=3, border_radius=14)
                    blbl = f"✓ [{sp_d['name']}] 즉시 영업 시작! (START) ▶"
                else:
                    pygame.draw.rect(portrait_surf, (44, 40, 62), btn_r, border_radius=14)
                    pygame.draw.rect(portrait_surf, config.UI_BORDER, btn_r, width=2, border_radius=14)
                    blbl = "🔒 차후 업데이트 오픈 예정 (◀ 이전 버튼으로 오픈 종목 선택)"
                bs = cta_f.render(blbl, True, config.WHITE if is_open else config.TEXT_SECONDARY)
                portrait_surf.blit(bs, bs.get_rect(center=btn_r.center))

            elif mode == "GLOBAL_ENDLESS":
                slot_idx = self.portrait_prep_idx % 4
                slot_type = SLOT_TYPES[slot_idx]
                slot_titles = {
                    "mold": "① 몰드 조리대",
                    "grill": "② 철판 그릴",
                    "batch_pot": "③ 대량 조리 팬",
                    "dispenser": "④ 음료 디스펜서",
                }
                stations = get_stations_by_slot(slot_type)
                per_page = 4
                total_pages = max(1, (len(stations) + per_page - 1) // per_page)
                pg = max(0, min(int(getattr(sc, "global_station_page", 0)), total_pages - 1))
                vis_stations = stations[pg * per_page : (pg + 1) * per_page]
                equipped_id = self.game_mgr.global_loadout.get(slot_type, "")

                hdr_s = sec_f.render(
                    f"🏮 {slot_titles.get(slot_type, slot_type)} 장착 선택 (페이지 {pg + 1}/{total_pages})",
                    True,
                    config.GOLD,
                )
                portrait_surf.blit(hdr_s, (36, 206))

                for i_idx, st_meta in enumerate(vis_stations):
                    row_r = pygame.Rect(36, 256 + i_idx * 162, 648, 148)
                    st_id = st_meta["id"]
                    is_eq = st_id == equipped_id
                    c_code = str(st_meta.get("country", "KR"))
                    is_unl = self.game_mgr.is_chapter_unlocked(c_code)

                    bg_c = (38, 64, 52) if is_eq else ((32, 28, 54) if is_unl else (24, 20, 36))
                    bdr_c = config.NEON_GREEN if is_eq else (config.GOLD if is_unl else config.UI_BORDER)
                    pygame.draw.rect(portrait_surf, bg_c, row_r, border_radius=12)
                    pygame.draw.rect(portrait_surf, bdr_c, row_r, width=3 if is_eq else 2, border_radius=12)

                    hw_r = pygame.Rect(row_r.x + 14, row_r.y + 18, 112, 112)
                    art_renderer.draw_station_hardware(portrait_surf, hw_r, station_type=slot_type)

                    nm_s = sec_f.render(f"[{c_code}] {st_meta['name']}", True, config.WHITE if is_unl else config.TEXT_SECONDARY)
                    portrait_surf.blit(nm_s, (hw_r.right + 18, row_r.y + 16))

                    st_recs = list(st_meta.get("recipes", []) or [])
                    rec_names = [str(RECIPES.get(r, {}).get("short_name") or RECIPES.get(r, {}).get("name") or r) for r in st_recs[:3]]
                    rn_s = sub_f.render("메뉴: " + ", ".join(rec_names), True, config.NEON_CYAN)
                    portrait_surf.blit(rn_s, (hw_r.right + 18, row_r.y + 56))

                    for f_i, rid in enumerate(st_recs[:3]):
                        art_renderer.draw_food_icon(portrait_surf, (hw_r.right + 34 + f_i * 48, row_r.bottom - 30), rid, size=36)

                    pill_r = pygame.Rect(row_r.right - 168, row_r.centery - 26, 152, 52)
                    if is_eq:
                        pygame.draw.rect(portrait_surf, (38, 148, 86), pill_r, border_radius=10)
                        ps = body_f.render("✓ 장착 중", True, config.WHITE)
                    elif is_unl:
                        pygame.draw.rect(portrait_surf, (228, 96, 36), pill_r, border_radius=10)
                        ps = body_f.render("장착하기 ▶", True, config.WHITE)
                    else:
                        pygame.draw.rect(portrait_surf, (58, 48, 72), pill_r, border_radius=10)
                        ps = sub_f.render(f"🔒 {c_code} 해금필요", True, config.TEXT_WARNING)
                    pygame.draw.rect(portrait_surf, config.GOLD, pill_r, width=1, border_radius=10)
                    portrait_surf.blit(ps, ps.get_rect(center=pill_r.center))

                prev_p = pygame.Rect(36, 924, 310, 88)
                next_p = pygame.Rect(374, 924, 310, 88)
                for pr, plbl in ((prev_p, "◀ 이전 국가 기구"), (next_p, f"다음 국가 기구 ({pg + 1}/{total_pages}) ▶")):
                    pygame.draw.rect(portrait_surf, (46, 40, 76), pr, border_radius=12)
                    pygame.draw.rect(portrait_surf, config.NEON_CYAN, pr, width=2, border_radius=12)
                    ps = body_f.render(plbl, True, config.WHITE)
                    portrait_surf.blit(ps, ps.get_rect(center=pr.center))

            else:
                # WORLD_TOUR 9개국 챕터 카드
                idx = self.portrait_prep_idx % len(CHAPTER_ORDER)
                ch_id = CHAPTER_ORDER[idx]
                ch_d = CHAPTERS[ch_id]
                unlocked = self.game_mgr.is_chapter_unlocked(ch_id)
                selected = (self.game_mgr.current_chapter == ch_id) and (self.game_mgr.mode == "WORLD_TOUR")
                ch_day = int(getattr(self.game_mgr, "chapter_days", {}).get(ch_id, 1))
                ch_stars = int(getattr(self.game_mgr, "chapter_stars", {}).get(ch_id, 0))

                stage_r = pygame.Rect(36, 208, 648, 210)
                art_renderer.draw_country_background(portrait_surf, stage_r, country_id=ch_id, time_tick=self._loading_tick)
                art_renderer.draw_alpha_overlay(portrait_surf, stage_r, (14, 12, 26, 150), border_radius=14)
                pygame.draw.rect(portrait_surf, config.GOLD if selected else config.UI_BORDER, stage_r, width=2, border_radius=14)

                t_s = title_f.render(f"🗺️ [{ch_id}] {ch_d['name']}", True, config.GOLD)
                s_s = body_f.render(str(ch_d.get("subtitle", ch_d.get("description", ""))[:34]), True, config.NEON_CYAN)
                d_s = sec_f.render(
                    f"📅 진행도: Day {ch_day}   |   ⭐ 별점: {'★' * ch_stars}{'☆' * (3 - ch_stars)}",
                    True,
                    config.WHITE,
                )
                st_s = sub_f.render(
                    "✓ 현재 영업 중인 챕터" if selected else ("🔓 해금 완료 · 선택 가능" if unlocked else f"🔒 미해금 (조기 해금 비용: {int(ch_d.get('unlock_cost', 5000)):,}원)"),
                    True,
                    config.NEON_GREEN if selected else (config.GOLD if unlocked else config.TEXT_WARNING),
                )
                portrait_surf.blit(t_s, (stage_r.x + 24, stage_r.y + 20))
                portrait_surf.blit(s_s, (stage_r.x + 24, stage_r.y + 66))
                portrait_surf.blit(d_s, (stage_r.x + 24, stage_r.y + 108))
                portrait_surf.blit(st_s, (stage_r.x + 24, stage_r.y + 154))

                # 현지 대표 메뉴 4종
                ch_recs = [r_id for r_id, r_obj in RECIPES.items() if str(r_obj.get("country", "")).upper() == ch_id][:4]
                if not ch_recs:
                    ch_recs = ["bungeoppang_redbean", "odeng_soup", "skewer_spicy", "tteokbokki_Original"]
                for r_i, rid in enumerate(ch_recs[:4]):
                    c_col = r_i % 2
                    c_row = r_i // 2
                    mr = pygame.Rect(36 + c_col * 328, 432 + c_row * 116, 320, 106)
                    pygame.draw.rect(portrait_surf, (30, 26, 50), mr, border_radius=12)
                    pygame.draw.rect(portrait_surf, config.UI_BORDER, mr, width=1, border_radius=12)
                    rdata = RECIPES.get(rid, {})
                    rname = str(rdata.get("name", rid))
                    rprice = int(rdata.get("sell_price", rdata.get("base_price", 1500)))
                    art_renderer.draw_food_icon(portrait_surf, (mr.x + 42, mr.centery), rid, size=54)
                    rn_s = body_f.render(rname[:12], True, config.WHITE)
                    rp_s = sub_f.render(f"💰 판매가 {rprice:,}원", True, config.GOLD)
                    portrait_surf.blit(rn_s, (mr.x + 80, mr.y + 20))
                    portrait_surf.blit(rp_s, (mr.x + 80, mr.y + 56))

                info_r = pygame.Rect(36, 672, 648, 240)
                pygame.draw.rect(portrait_surf, (28, 24, 46), info_r, border_radius=14)
                pygame.draw.rect(portrait_surf, config.UI_BORDER, info_r, width=2, border_radius=14)
                ih = sec_f.render("📋 챕터 해금 일정 & 야시장 특징", True, config.GOLD)
                portrait_surf.blit(ih, (info_r.x + 20, info_r.y + 16))
                i_lines = [
                    str(ch_d.get("description", "전 세계 손님들에게 현지 최고의 길거리 음식을 대접하세요!"))[:38],
                    "🔓 Day 1: 몰드 조리대 ➔ Day 2: 음료·조립 트레이 ➔ Day 3: 철판 그릴",
                    "🔓 Day 4: 대량 조리 팬 & 마스터 스킬 ➔ Day 5: 챕터 보스전 클리어!",
                    "💡 영업 종료 시 트레이/기구에 남은 음식은 원가 100% 폐기 손실 차감!",
                ]
                for l_i, l_str in enumerate(i_lines):
                    ls = sub_f.render(l_str, True, config.NEON_CYAN if l_i in (1, 2) else config.WHITE)
                    portrait_surf.blit(ls, (info_r.x + 20, info_r.y + 62 + l_i * 42))

                btn_bg = (42, 152, 86) if (unlocked and selected) else ((232, 98, 36) if unlocked else (88, 52, 128))
                pygame.draw.rect(portrait_surf, btn_bg, btn_r, border_radius=14)
                pygame.draw.rect(portrait_surf, config.GOLD, btn_r, width=3, border_radius=14)
                if unlocked and selected:
                    blbl = f"✓ [{ch_d['name']}] 즉시 영업 시작! (START) ▶"
                elif unlocked:
                    blbl = f"✈️ [{ch_d['name']}] 챕터 선택하기! (터치) ▶"
                else:
                    blbl = f"🔒 {int(ch_d.get('unlock_cost', 5000)):,}원으로 [{ch_d['name']}] 즉시 해금 ▶"
                bs = cta_f.render(blbl, True, config.WHITE)
                portrait_surf.blit(bs, bs.get_rect(center=btn_r.center))

        elif active_tab == "character":
            if (self.portrait_prep_idx % 2) == 0:
                insp_id = getattr(sc, "inspected_character", self.game_mgr.selected_character)
                if insp_id not in CHARACTERS:
                    insp_id = self.game_mgr.selected_character
                c_obj = CHARACTERS.get(insp_id, CHARACTERS["chef_kr"])
                is_unl = self.game_mgr.is_character_unlocked(insp_id)
                is_sel = self.game_mgr.selected_character == insp_id
                c_country = str(c_obj.get("country", "KR"))

                stage_r = pygame.Rect(36, 208, 648, 224)
                art_renderer.draw_country_background(portrait_surf, stage_r, country_id=c_country, time_tick=self._loading_tick)
                art_renderer.draw_alpha_overlay(portrait_surf, stage_r, (14, 12, 26, 155), border_radius=14)
                pygame.draw.rect(portrait_surf, config.GOLD if is_sel else config.NEON_CYAN, stage_r, width=2, border_radius=14)

                av_r = pygame.Rect(stage_r.x + 22, stage_r.y + 26, 172, 172)
                pygame.draw.rect(portrait_surf, (28, 24, 48), av_r.inflate(8, 8), border_radius=16)
                pygame.draw.rect(portrait_surf, config.GOLD, av_r.inflate(8, 8), width=2, border_radius=16)
                art_renderer.draw_chef_avatar(portrait_surf, av_r, character_id=insp_id, state="COOKING", time_tick=self._loading_tick)

                tx = av_r.right + 24
                r_s = sub_f.render(f"🌏 출신 지역: [{c_obj.get('region_name', c_country)}]", True, config.NEON_CYAN)
                n_s = title_f.render(str(c_obj["name"]), True, config.WHITE)
                t_s = sec_f.render(f"★ {c_obj.get('title', '포차 마스터')}", True, config.GOLD)
                u_s = body_f.render(
                    "✓ 현재 출전 중인 마스터" if is_sel else ("🔓 영입 완료 · 출전 가능" if is_unl else f"🔒 영입 비용: 💰 {int(c_obj.get('unlock_cost', 3000)):,}원"),
                    True,
                    config.NEON_GREEN if is_sel else (config.GOLD if is_unl else config.TEXT_WARNING),
                )
                portrait_surf.blit(r_s, (tx, stage_r.y + 24))
                portrait_surf.blit(n_s, (tx, stage_r.y + 62))
                portrait_surf.blit(t_s, (tx, stage_r.y + 114))
                portrait_surf.blit(u_s, (tx, stage_r.y + 162))

                p_box = pygame.Rect(36, 448, 648, 214)
                pygame.draw.rect(portrait_surf, (30, 26, 52), p_box, border_radius=14)
                pygame.draw.rect(portrait_surf, config.NEON_GREEN, p_box, width=2, border_radius=14)
                ph = sec_f.render(f"🌟 마스터 고유 패시브: {c_obj.get('passive_name', '장인의 비법')}", True, config.NEON_GREEN)
                pd = body_f.render(str(c_obj.get("passive_desc", ""))[:38], True, config.WHITE)
                pd2 = sub_f.render(str(c_obj.get("passive_desc", ""))[38:76], True, config.TEXT_PRIMARY)
                portrait_surf.blit(ph, (p_box.x + 20, p_box.y + 20))
                portrait_surf.blit(pd, (p_box.x + 20, p_box.y + 72))
                if pd2.get_width() > 0:
                    portrait_surf.blit(pd2, (p_box.x + 20, p_box.y + 112))
                tip_p = sub_f.render("💡 상단 [◀] [▶] 버튼으로 32인 마스터를 순서대로 비교할 수 있습니다.", True, config.NEON_CYAN)
                portrait_surf.blit(tip_p, (p_box.x + 20, p_box.bottom - 44))

                s_box = pygame.Rect(36, 678, 648, 236)
                pygame.draw.rect(portrait_surf, (32, 26, 48), s_box, border_radius=14)
                pygame.draw.rect(portrait_surf, config.GOLD, s_box, width=2, border_radius=14)
                sh = sec_f.render(
                    f"⚡ 액티브 스킬: {c_obj.get('skill_name', '')}  (쿨타임 {int(c_obj.get('cooldown', 35))}초)",
                    True,
                    config.GOLD,
                )
                sd1 = body_f.render(str(c_obj.get("skill_desc", ""))[:38], True, config.WHITE)
                sd2 = body_f.render(str(c_obj.get("skill_desc", ""))[38:76], True, config.NEON_YELLOW)
                portrait_surf.blit(sh, (s_box.x + 20, s_box.y + 20))
                portrait_surf.blit(sd1, (s_box.x + 20, s_box.y + 76))
                if sd2.get_width() > 0:
                    portrait_surf.blit(sd2, (s_box.x + 20, s_box.y + 118))
                ug = sub_f.render(f"🔓 해금 조건: {c_obj.get('unlock_cond_text', '골드 영입 또는 스토리 챕터 클리어')}", True, config.TEXT_SECONDARY)
                portrait_surf.blit(ug, (s_box.x + 20, s_box.bottom - 46))

                btn_bg = (42, 152, 86) if is_sel else ((232, 98, 36) if is_unl else (44, 118, 168))
                pygame.draw.rect(portrait_surf, btn_bg, btn_r, border_radius=14)
                pygame.draw.rect(portrait_surf, config.GOLD, btn_r, width=3, border_radius=14)
                if is_sel:
                    blbl = f"✓ [{c_obj['name']}] 현재 출전 중!"
                elif is_unl:
                    blbl = f"👨‍🍳 [{c_obj['name']}] 출전 마스터로 선택하기! ▶"
                else:
                    blbl = f"💰 {int(c_obj.get('unlock_cost', 3000)):,}원으로 [{c_obj['name']}] 즉시 영입! ▶"
                bs = cta_f.render(blbl, True, config.WHITE)
                portrait_surf.blit(bs, bs.get_rect(center=btn_r.center))

            else:
                # 32인 목록 & 국가 필터 (2x5 필터 + 2x3 그리드 + 하단 페이지 바)
                cur_filter = str(getattr(sc, "char_country_filter", "ALL")).upper()
                f_labels = {
                    "ALL": "전체(32)", "KR": "🇰🇷한국", "JP": "🇯🇵일본", "MX": "🇲🇽멕시코", "TW": "🇹🇼대만",
                    "CN": "[CN]중국", "IN": "[IN]인도", "US": "🇺🇸미국", "RU": "[RU]러시아", "BR": "🇧🇷브라질",
                    "TH": "🇹🇭태국", "TR": "🇹🇷터키", "FR": "🇫🇷프랑스",
                }
                for f_i, f_code in enumerate(COUNTRY_FILTER_ORDER):
                    f_col = f_i % 5
                    f_row = f_i // 5
                    fr = pygame.Rect(32 + f_col * 132, 202 + f_row * 50, 126, 44)
                    is_f = cur_filter == f_code
                    pygame.draw.rect(portrait_surf, (232, 102, 36) if is_f else (36, 32, 58), fr, border_radius=8)
                    pygame.draw.rect(portrait_surf, config.GOLD if is_f else config.UI_BORDER, fr, width=2 if is_f else 1, border_radius=8)
                    fs = sub_f.render(f_labels.get(f_code, f_code), True, config.WHITE)
                    portrait_surf.blit(fs, fs.get_rect(center=fr.center))

                filtered = sc._get_filtered_characters() if hasattr(sc, "_get_filtered_characters") else list(CHARACTERS.keys())
                per_page = 6
                total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
                c_pg = max(0, min(int(getattr(sc, "char_page", 0)), total_pages - 1))
                page_items = filtered[c_pg * per_page : (c_pg + 1) * per_page]

                for idx_c, cid in enumerate(page_items):
                    col = idx_c % 2
                    row = idx_c // 2
                    cr = pygame.Rect(32 + col * 332, 312 + row * 204, 324, 194)
                    c_d = CHARACTERS.get(cid, CHARACTERS["chef_kr"])
                    is_unl = self.game_mgr.is_character_unlocked(cid)
                    is_sel = self.game_mgr.selected_character == cid

                    bg_c = (38, 62, 54) if is_sel else ((32, 28, 54) if is_unl else (24, 20, 38))
                    bdr_c = config.NEON_GREEN if is_sel else (config.GOLD if is_unl else config.UI_BORDER)
                    pygame.draw.rect(portrait_surf, bg_c, cr, border_radius=12)
                    pygame.draw.rect(portrait_surf, bdr_c, cr, width=3 if is_sel else 2, border_radius=12)

                    av_mini = pygame.Rect(cr.x + 12, cr.y + 12, 84, 84)
                    art_renderer.draw_chef_avatar(portrait_surf, av_mini, character_id=cid, state="IDLE", time_tick=self._loading_tick)

                    reg_s = xs_f.render(f"[{c_d.get('region_name', c_d.get('country', ''))}]", True, config.NEON_CYAN)
                    nm_s = sec_f.render(str(c_d["name"])[:9], True, config.WHITE)
                    sk_s = xs_f.render(f"★ {c_d.get('skill_name', '')[:11]}", True, config.GOLD)
                    ps_s = xs_f.render(str(c_d.get("passive_desc", ""))[:20], True, config.TEXT_PRIMARY)
                    portrait_surf.blit(reg_s, (av_mini.right + 12, cr.y + 14))
                    portrait_surf.blit(nm_s, (av_mini.right + 12, cr.y + 38))
                    portrait_surf.blit(sk_s, (av_mini.right + 12, cr.y + 72))
                    portrait_surf.blit(ps_s, (cr.x + 14, cr.y + 106))

                    act_r = pygame.Rect(cr.x + 12, cr.bottom - 50, cr.width - 24, 38)
                    if is_sel:
                        pygame.draw.rect(portrait_surf, (42, 148, 86), act_r, border_radius=8)
                        as_txt = sub_f.render("✓ 출전 중 (상세보기)", True, config.WHITE)
                    elif is_unl:
                        pygame.draw.rect(portrait_surf, (228, 96, 36), act_r, border_radius=8)
                        as_txt = sub_f.render("출전 선택하기 ▶", True, config.WHITE)
                    else:
                        pygame.draw.rect(portrait_surf, (52, 88, 138), act_r, border_radius=8)
                        as_txt = sub_f.render(f"💰 {int(c_d.get('unlock_cost', 3000)):,}원 영입 ▶", True, config.GOLD)
                    portrait_surf.blit(as_txt, as_txt.get_rect(center=act_r.center))

                prev_b = pygame.Rect(32, 934, 210, 82)
                mid_b = pygame.Rect(250, 934, 220, 82)
                next_b = pygame.Rect(478, 934, 210, 82)
                for br, blbl in ((prev_b, "◀ 이전 페이지"), (next_b, "다음 페이지 ▶")):
                    pygame.draw.rect(portrait_surf, (48, 40, 78), br, border_radius=12)
                    pygame.draw.rect(portrait_surf, config.GOLD, br, width=2, border_radius=12)
                    bs = body_f.render(blbl, True, config.WHITE)
                    portrait_surf.blit(bs, bs.get_rect(center=br.center))
                pygame.draw.rect(portrait_surf, (30, 26, 48), mid_b, border_radius=12)
                pygame.draw.rect(portrait_surf, config.UI_BORDER, mid_b, width=2, border_radius=12)
                ms = sec_f.render(f"페이지 {c_pg + 1} / {total_pages}", True, config.GOLD)
                portrait_surf.blit(ms, ms.get_rect(center=mid_b.center))

        elif active_tab == "upgrade":
            if (self.portrait_prep_idx % 2) == 0:
                hdr_s = sec_f.render("🛠️ 조리 기구 & 무한 적재 트레이 강화 (터치하여 즉시 강화)", True, config.GOLD)
                portrait_surf.blit(hdr_s, (36, 206))
                hw_types = ["mold", "grill", "batch_pot", "dispenser", "mold"]
                up_short_descs = {
                    "mold_upgrade": "몰드 구이 속도 증가 & 탐 방지 시간 연장",
                    "grill_upgrade": "직화 그릴 화력 강화 & 조리 속도 단축",
                    "batch_pot_upgrade": "대량 조리 팬 화력 강화 & 회전율 상승",
                    "dispenser_upgrade": "음료 디스펜서 추출 속도 & 슬롯 강화",
                    "tray_upgrade": "서빙 트레이 보온 유지 & 조립 효율 강화",
                }
                for idx_u, up_key in enumerate(STATION_UPGRADE_ORDER):
                    row_r = pygame.Rect(32, 246 + idx_u * 152, 656, 138)
                    up_meta = STATION_UPGRADES[up_key]
                    lvl = self.game_mgr.get_station_level(up_key)
                    max_lvl = int(up_meta.get("max_level", 3))
                    cost = self.game_mgr.get_station_upgrade_cost(up_key)
                    can_buy = cost is not None and self.game_mgr.gold >= cost

                    pygame.draw.rect(portrait_surf, (32, 28, 54), row_r, border_radius=12)
                    pygame.draw.rect(portrait_surf, config.GOLD if can_buy else config.UI_BORDER, row_r, width=2, border_radius=12)

                    hw_r = pygame.Rect(row_r.x + 14, row_r.y + 18, 102, 102)
                    art_renderer.draw_station_hardware(portrait_surf, hw_r, station_type=hw_types[idx_u % len(hw_types)])

                    nm_s = sec_f.render(f"{up_meta['name']}  (Lv.{lvl}/{max_lvl})", True, config.WHITE)
                    short_d = up_short_descs.get(up_key, str(up_meta.get("description", ""))[:20])
                    ds_s = sub_f.render(short_d, True, config.NEON_CYAN)
                    lv_s = sub_f.render("★ " * lvl + "☆ " * (max_lvl - lvl), True, config.GOLD)
                    portrait_surf.blit(nm_s, (hw_r.right + 16, row_r.y + 18))
                    portrait_surf.blit(ds_s, (hw_r.right + 16, row_r.y + 56))
                    portrait_surf.blit(lv_s, (hw_r.right + 16, row_r.y + 92))

                    ubtn = pygame.Rect(row_r.right - 178, row_r.centery - 42, 162, 84)
                    if cost is None:
                        pygame.draw.rect(portrait_surf, (38, 138, 82), ubtn, border_radius=10)
                        us = body_f.render("★ MAX 완료", True, config.WHITE)
                        portrait_surf.blit(us, us.get_rect(center=ubtn.center))
                    else:
                        pygame.draw.rect(portrait_surf, (232, 98, 36) if can_buy else (52, 46, 72), ubtn, border_radius=10)
                        pygame.draw.rect(portrait_surf, config.GOLD if can_buy else config.UI_BORDER, ubtn, width=2, border_radius=10)
                        c1 = body_f.render(f"💰 {cost:,}원", True, config.GOLD if can_buy else config.TEXT_SECONDARY)
                        c2 = sub_f.render("강화하기 ▶", True, config.WHITE if can_buy else config.TEXT_SECONDARY)
                        portrait_surf.blit(c1, c1.get_rect(center=(ubtn.centerx, ubtn.y + 26)))
                        portrait_surf.blit(c2, c2.get_rect(center=(ubtn.centerx, ubtn.y + 58)))
            else:
                hdr_s = sec_f.render("🏮 포차 야시장 인테리어 & 설비 구매 (터치하여 즉시 설치)", True, config.GOLD)
                portrait_surf.blit(hdr_s, (36, 206))
                icons_food = ["bungeoppang_redbean", "takoyaki_mayo", "taco_salsa", "boba_milktea"]
                in_short_descs = {
                    "lighting": "감성 알전구 조명으로 손님 인내심 증가",
                    "signboard": "화려한 네온 간판으로 VIP 손님 방문율 상승",
                    "prop": "전통 야시장 소품으로 서빙 팁 보너스 증가",
                    "seating": "간이 테이블 확장으로 손님 대기 슬롯 증가",
                }
                for idx_i, in_key in enumerate(INTERIOR_UPGRADE_ORDER):
                    row_r = pygame.Rect(32, 250 + idx_i * 186, 656, 170)
                    in_meta = INTERIOR_UPGRADES[in_key]
                    lvl = self.game_mgr.get_interior_level(in_key)
                    max_lvl = int(in_meta.get("max_level", 3))
                    cost = self.game_mgr.get_interior_upgrade_cost(in_key)
                    can_buy = cost is not None and self.game_mgr.gold >= cost

                    pygame.draw.rect(portrait_surf, (32, 28, 54), row_r, border_radius=12)
                    pygame.draw.rect(portrait_surf, config.GOLD if can_buy else config.UI_BORDER, row_r, width=2, border_radius=12)

                    ic_r = pygame.Rect(row_r.x + 18, row_r.centery - 46, 92, 92)
                    pygame.draw.rect(portrait_surf, (44, 36, 72), ic_r, border_radius=14)
                    pygame.draw.rect(portrait_surf, config.GOLD, ic_r, width=2, border_radius=14)
                    art_renderer.draw_food_icon(portrait_surf, ic_r.center, icons_food[idx_i % len(icons_food)], size=58)

                    nm_s = sec_f.render(f"{in_meta['name']}  (Lv.{lvl}/{max_lvl})", True, config.WHITE)
                    short_in = in_short_descs.get(in_key, str(in_meta.get("description", ""))[:20])
                    ds_s = sub_f.render(short_in, True, config.NEON_CYAN)
                    lv_s = sub_f.render("★ " * lvl + "☆ " * (max_lvl - lvl), True, config.GOLD)
                    portrait_surf.blit(nm_s, (ic_r.right + 18, row_r.y + 24))
                    portrait_surf.blit(ds_s, (ic_r.right + 18, row_r.y + 68))
                    portrait_surf.blit(lv_s, (ic_r.right + 18, row_r.y + 112))

                    ubtn = pygame.Rect(row_r.right - 178, row_r.centery - 46, 162, 92)
                    if cost is None:
                        pygame.draw.rect(portrait_surf, (38, 138, 82), ubtn, border_radius=10)
                        us = body_f.render("★ 설치 완료", True, config.WHITE)
                        portrait_surf.blit(us, us.get_rect(center=ubtn.center))
                    else:
                        pygame.draw.rect(portrait_surf, (232, 98, 36) if can_buy else (52, 46, 72), ubtn, border_radius=10)
                        pygame.draw.rect(portrait_surf, config.GOLD if can_buy else config.UI_BORDER, ubtn, width=2, border_radius=10)
                        c1 = body_f.render(f"💰 {cost:,}원", True, config.GOLD if can_buy else config.TEXT_SECONDARY)
                        c2 = sub_f.render("설치하기 ▶", True, config.WHITE if can_buy else config.TEXT_SECONDARY)
                        portrait_surf.blit(c1, c1.get_rect(center=(ubtn.centerx, ubtn.y + 28)))
                        portrait_surf.blit(c2, c2.get_rect(center=(ubtn.centerx, ubtn.y + 62)))

        else:  # tournament
            rnd_labels = ["32강전", "16강전", "8강전", "4강 준결승", "대망의 결승전", "챔피언 방어전"]
            rnd_idx = min(5, int(getattr(self.game_mgr, "tournament_round_idx", 0)))
            opp_id = sc._get_current_tournament_opponent() if hasattr(sc, "_get_current_tournament_opponent") else "chef_jp_osaka"
            opp_d = CHARACTERS.get(opp_id, CHARACTERS["chef_kr"])
            my_d = self.game_mgr.get_selected_character_data()
            prize = 3000 + rnd_idx * 2000

            if (self.portrait_prep_idx % 2) == 0:
                hdr_box = pygame.Rect(36, 208, 648, 108)
                pygame.draw.rect(portrait_surf, (44, 24, 58), hdr_box, border_radius=14)
                pygame.draw.rect(portrait_surf, config.GOLD, hdr_box, width=2, border_radius=14)
                t_s = title_f.render(f"🏆 월드 포차 그랑프리 — [{rnd_labels[rnd_idx]}]", True, config.GOLD)
                p_s = sec_f.render(f"💰 승리 보상 상금: +{prize:,}원  &  다음 라운드 진출!", True, config.NEON_GREEN)
                portrait_surf.blit(t_s, t_s.get_rect(center=(hdr_box.centerx, hdr_box.y + 34)))
                portrait_surf.blit(p_s, p_s.get_rect(center=(hdr_box.centerx, hdr_box.y + 78)))

                vs_box = pygame.Rect(36, 332, 648, 360)
                pygame.draw.rect(portrait_surf, (28, 22, 46), vs_box, border_radius=16)
                pygame.draw.rect(portrait_surf, config.NEON_CYAN, vs_box, width=2, border_radius=16)

                my_av = pygame.Rect(vs_box.x + 48, vs_box.y + 36, 168, 168)
                ai_av = pygame.Rect(vs_box.right - 216, vs_box.y + 36, 168, 168)
                art_renderer.draw_chef_avatar(portrait_surf, my_av, character_id=self.game_mgr.selected_character, state="COOKING", time_tick=self._loading_tick)
                art_renderer.draw_chef_avatar(portrait_surf, ai_av, character_id=opp_id, state="SKILL", time_tick=self._loading_tick)

                vs_lbl = config.get_font(36, bold=True).render("⚔️ VS", True, config.GOLD)
                portrait_surf.blit(vs_lbl, vs_lbl.get_rect(center=(vs_box.centerx, my_av.centery)))

                m_nm = sec_f.render(f"나: {my_d['name']}", True, config.NEON_GREEN)
                m_sk = sub_f.render(f"★ {my_d.get('skill_name', '')}", True, config.WHITE)
                a_nm = sec_f.render(f"라이벌: {opp_d['name']}", True, config.TEXT_WARNING)
                a_sk = sub_f.render(f"🌏 [{opp_d.get('region_name', '')}] ★ {opp_d.get('skill_name', '')}", True, config.GOLD)
                portrait_surf.blit(m_nm, m_nm.get_rect(center=(my_av.centerx, my_av.bottom + 28)))
                portrait_surf.blit(m_sk, m_sk.get_rect(center=(my_av.centerx, my_av.bottom + 62)))
                portrait_surf.blit(a_nm, a_nm.get_rect(center=(ai_av.centerx, ai_av.bottom + 28)))
                portrait_surf.blit(a_sk, a_sk.get_rect(center=(ai_av.centerx, ai_av.bottom + 62)))

                rule_box = pygame.Rect(36, 708, 648, 204)
                pygame.draw.rect(portrait_surf, (26, 22, 42), rule_box, border_radius=14)
                pygame.draw.rect(portrait_surf, config.UI_BORDER, rule_box, width=2, border_radius=14)
                r_lines = [
                    "⚔️ [대회 규칙] 영업 종료 시 AI 라이벌보다 높은 순매출을 달성하면 승리!",
                    "📦 [주의] 마감 시 트레이/기구에 남은 음식 폐기 손실이 차감된 순매출로 판정됩니다.",
                    f"🔥 승리 시 즉시 상금 💰 {prize:,}원 지급 및 상위 라운드 진출!",
                ]
                for r_i, rl in enumerate(r_lines):
                    rs = sub_f.render(rl, True, config.GOLD if r_i == 2 else config.WHITE)
                    portrait_surf.blit(rs, (rule_box.x + 20, rule_box.y + 28 + r_i * 54))
            else:
                # 32강 전체 라운드 대진표
                hdr_s = sec_f.render("🏆 32강 월드 포차 그랑프리 라운드별 대진표", True, config.GOLD)
                portrait_surf.blit(hdr_s, (36, 206))
                all_cids = list(CHARACTERS.keys())
                for r_i in range(5):
                    rr = pygame.Rect(36, 250 + r_i * 132, 648, 120)
                    is_cur = r_i == rnd_idx
                    is_done = r_i < rnd_idx
                    bg_c = (44, 68, 52) if is_done else ((58, 32, 48) if is_cur else (28, 24, 46))
                    bdr_c = config.NEON_GREEN if is_done else (config.GOLD if is_cur else config.UI_BORDER)
                    pygame.draw.rect(portrait_surf, bg_c, rr, border_radius=12)
                    pygame.draw.rect(portrait_surf, bdr_c, rr, width=3 if is_cur else 2, border_radius=12)

                    r_opp = opp_id if is_cur else all_cids[(r_i * 5 + 3) % len(all_cids)]
                    ro_d = CHARACTERS.get(r_opp, CHARACTERS["chef_kr"])
                    av_r = pygame.Rect(rr.x + 14, rr.y + 16, 88, 88)
                    art_renderer.draw_chef_avatar(portrait_surf, av_r, character_id=r_opp, state="IDLE", time_tick=self._loading_tick)

                    rn_s = sec_f.render(f"ROUND {r_i + 1} · {rnd_labels[r_i]}", True, config.GOLD if is_cur else config.WHITE)
                    op_s = body_f.render(f"상대 마스터: [{ro_d.get('region_name', '')}] {ro_d['name']}", True, config.NEON_CYAN)
                    pr_s = sub_f.render(f"💰 승리 상금: {3000 + r_i * 2000:,}원", True, config.GOLD)
                    portrait_surf.blit(rn_s, (av_r.right + 18, rr.y + 14))
                    portrait_surf.blit(op_s, (av_r.right + 18, rr.y + 50))
                    portrait_surf.blit(pr_s, (av_r.right + 18, rr.y + 84))

                    st_txt = "✓ 승리 돌파!" if is_done else ("🔥 현재 도전!" if is_cur else "🔒 대기중")
                    st_col = config.NEON_GREEN if is_done else (config.GOLD if is_cur else config.TEXT_SECONDARY)
                    st_s = body_f.render(st_txt, True, st_col)
                    portrait_surf.blit(st_s, (rr.right - st_s.get_width() - 22, rr.centery - st_s.get_height() // 2))

            pygame.draw.rect(portrait_surf, (212, 52, 64), btn_r, border_radius=14)
            pygame.draw.rect(portrait_surf, config.GOLD, btn_r, width=3, border_radius=14)
            bs = cta_f.render(f"⚔️ [{rnd_labels[rnd_idx]}] AI 보스전 즉시 출격! (START) ▶", True, config.WHITE)
            portrait_surf.blit(bs, bs.get_rect(center=btn_r.center))

    def _compose_portrait_surface(self, logical_surf: pygame.Surface, portrait_surf: pygame.Surface) -> None:
        """
        1280x720 논리 화면을 720x1280 세로 모바일 전용 **1패널 확대 레이아웃(Single Giant Panel)**으로 합성한다.
        - 기존의 4분할/다중 분할을 없애고 현재 선택된 1개 대형 패널만 큼직하게 표시
        - 타이틀(title), 준비/상점(prep), 인게임(play/duel_play) 모두 서브서피스 확대(smoothscale 블러) 없이
          100% 1:1 네이티브 고해상도 폰트와 도트 그래픽으로 직접 렌더링한다!
        """
        portrait_surf.fill((14, 12, 24))
        mappings = self._get_portrait_region_mappings()
        bg_country = getattr(self.game_mgr, "current_chapter", "KR") or "KR"

        # 매핑된 영역 렌더링 (title / prep / play / duel_play는 100% 1:1 네이티브 렌더링 사용)
        if len(mappings) == 1 or self.current_scene_name not in ("title", "prep", "play", "duel_play"):
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
                pygame.draw.rect(portrait_surf, border_col, dst_r, width=3, border_radius=12)
        elif self.current_scene_name in ("play", "duel_play") and self.current_scene is not None:
            for _src_r, dst_r, border_col in mappings:
                if dst_r.y >= 300:
                    self._draw_portrait_play_active_station(portrait_surf, dst_r, self.current_scene, border_col)

        # 1) 모달/로딩/결과 화면 등 단일 대형 카드 배치일 때 상·하단 배너 렌더링 (상단 타이틀 텍스트 표시 제거)
        if len(mappings) == 1:
            main_dst = mappings[0][1]
            top_h = max(80, main_dst.top - 24)
            top_banner = pygame.Rect(12, 12, 696, top_h)
            art_renderer.draw_country_background(portrait_surf, top_banner, country_id=bg_country, time_tick=self._loading_tick)
            art_renderer.draw_alpha_overlay(portrait_surf, top_banner, (14, 12, 26, 135), border_radius=16)
            pygame.draw.rect(portrait_surf, config.GOLD, top_banner, width=2, border_radius=16)

            for idx, fid in enumerate(["bungeoppang_redbean", "odeng_clean_wave", "skewer_spicy", "takoyaki_mayo", "boba_milktea"]):
                fx = 120 + idx * 120
                fy = top_banner.centery + int(math.sin(self._loading_tick * 4.0 + idx) * 4)
                pygame.draw.circle(portrait_surf, (28, 22, 46), (fx, fy), 36)
                pygame.draw.circle(portrait_surf, config.GOLD, (fx, fy), 36, width=2)
                art_renderer.draw_food_icon(portrait_surf, (fx, fy), fid, size=60)

            bot_y = main_dst.bottom + 12
            bot_h = max(60, 1268 - bot_y)
            bot_banner = pygame.Rect(12, bot_y, 696, bot_h)
            pygame.draw.rect(portrait_surf, (22, 18, 38), bot_banner, border_radius=16)
            pygame.draw.rect(portrait_surf, config.UI_BORDER, bot_banner, width=2, border_radius=16)

            if self.loading_active and self.loading_wait_for_tap and self.loading_progress >= 1.0:
                pulse = 0.86 + 0.14 * math.sin(self._loading_tick * 6.5)
                tap_btn = pygame.Rect(60, bot_banner.centery - 42, 600, 84)
                pygame.draw.rect(portrait_surf, (int(238 * pulse), int(98 * pulse), 34), tap_btn, border_radius=16)
                pygame.draw.rect(portrait_surf, config.GOLD, tap_btn, width=3, border_radius=16)
                tap_lbl = config.get_font(24, bold=True).render("🏮 화면을 터치하여 포차 오픈! ▶", True, config.WHITE)
                portrait_surf.blit(tap_lbl, tap_lbl.get_rect(center=tap_btn.center))
            else:
                for s_i, s_t in enumerate(("mold", "dispenser", "grill", "batch_pot")):
                    hw_r = pygame.Rect(96 + s_i * 142, bot_banner.centery - 38, 102, 76)
                    art_renderer.draw_station_hardware(portrait_surf, hw_r, station_type=s_t)

        # 2) 타이틀 화면(TitleScene) 세로 1패널 모드: 100% 1:1 네이티브 고해상도 렌더링
        elif self.current_scene_name == "title":
            from data.chapters import CHAPTER_ORDER
            sc = self.current_scene
            prev_c = getattr(sc, "preview_country", bg_country) or bg_country
            c_short = {
                "KR": "🇰🇷한국", "JP": "🇯🇵일본", "MX": "🇲🇽멕시코", "TW": "🇹🇼대만", "CN": "[CN]중국",
                "IN": "[IN]인도", "US": "🇺🇸미국", "RU": "[RU]러시아", "BR": "🇧🇷브라질",
            }
            cf = config.get_font(14, bold=True)
            for idx_c, cid in enumerate(CHAPTER_ORDER):
                cr = pygame.Rect(15 + idx_c * 77, 12, 72, 42)
                is_c = cid == prev_c
                pygame.draw.rect(portrait_surf, (232, 102, 36) if is_c else (32, 26, 52), cr, border_radius=8)
                pygame.draw.rect(portrait_surf, config.GOLD if is_c else config.UI_BORDER, cr, width=2 if is_c else 1, border_radius=8)
                cs = cf.render(c_short.get(cid, cid), True, config.WHITE if is_c else config.TEXT_PRIMARY)
                portrait_surf.blit(cs, cs.get_rect(center=cr.center))

            hdr_r = pygame.Rect(12, 62, 696, 110)
            art_renderer.draw_country_background(portrait_surf, hdr_r, country_id=prev_c, time_tick=self._loading_tick)
            art_renderer.draw_alpha_overlay(portrait_surf, hdr_r, (20, 16, 38, 210), border_radius=16)
            pygame.draw.rect(portrait_surf, config.GOLD, hdr_r, width=2, border_radius=16)
            tf = config.get_font(26, bold=True)
            sub_f = config.get_font(16, bold=True)
            t_s = tf.render("🏮 전세계 길거리 음식 포차 타이쿤 🏮", True, (255, 238, 120))
            s_s = sub_f.render("9개국 32인 마스터 월드 스트리트 푸드 투어", True, config.NEON_CYAN)
            portrait_surf.blit(t_s, t_s.get_rect(center=(360, 96)))
            portrait_surf.blit(s_s, s_s.get_rect(center=(360, 138)))

            # 상단 카드 전환 바 ([◀] + 4개 카드 탭 + [▶])
            nav_f = config.get_font(17, bold=True)
            arrow_f = config.get_font(22, bold=True)
            for ar_rect, ar_lbl in ((pygame.Rect(12, 182, 56, 60), "◀"), (pygame.Rect(652, 182, 56, 60), "▶")):
                pygame.draw.rect(portrait_surf, (48, 40, 76), ar_rect, border_radius=10)
                pygame.draw.rect(portrait_surf, config.GOLD, ar_rect, width=2, border_radius=10)
                as_s = arrow_f.render(ar_lbl, True, config.GOLD)
                portrait_surf.blit(as_s, as_s.get_rect(center=ar_rect.center))

            t_idx = self.portrait_title_idx % 4
            card_tabs = [
                ("👨‍🍳 프로필", config.NEON_GREEN),
                ("🗺️ 스토리", config.POCHA_ORANGE),
                ("🎯 장인모드", config.GOLD),
                ("🏮 글로벌", config.NEON_CYAN),
            ]
            for i, (tlbl, tcol) in enumerate(card_tabs):
                pill_r = pygame.Rect(74 + i * 144, 182, 140, 60)
                is_sel = i == t_idx
                bg = (232, 102, 36) if is_sel else (34, 28, 54)
                pygame.draw.rect(portrait_surf, bg, pill_r, border_radius=10)
                pygame.draw.rect(portrait_surf, config.WHITE if is_sel else tcol, pill_r, width=3 if is_sel else 1, border_radius=10)
                ts = nav_f.render(tlbl, True, config.WHITE if is_sel else tcol)
                portrait_surf.blit(ts, ts.get_rect(center=pill_r.center))

            # 중앙 초대형 카드 1:1 네이티브 직접 렌더링
            self._draw_portrait_title_card_native(portrait_surf, pygame.Rect(24, 252, 672, 728), sc)

            # 하단 유틸리티 버튼 1열/2열: 선명한 한글+아이콘 버튼 오버레이
            btn_f = config.get_font(18, bold=True)
            row1_bg = pygame.Rect(12, 994, 696, 72)
            pygame.draw.rect(portrait_surf, (18, 15, 30), row1_bg, border_radius=12)
            r1_btns = [
                (pygame.Rect(16, 1000, 212, 60), "💾 세이브 로드", config.NEON_CYAN),
                (pygame.Rect(236, 1000, 212, 60), "🗑️ 초기화", config.TEXT_WARNING),
                (pygame.Rect(456, 1000, 248, 60), "⚙️ 사운드·화면 설정", config.GOLD),
            ]
            for br, blbl, bcol in r1_btns:
                pygame.draw.rect(portrait_surf, (42, 36, 64), br, border_radius=10)
                pygame.draw.rect(portrait_surf, bcol, br, width=2, border_radius=10)
                bs = btn_f.render(blbl, True, config.WHITE)
                portrait_surf.blit(bs, bs.get_rect(center=br.center))

            row2_bg = pygame.Rect(84, 1078, 552, 72)
            pygame.draw.rect(portrait_surf, (18, 15, 30), row2_bg, border_radius=12)
            r2_btns = [
                (pygame.Rect(90, 1084, 264, 60), "🔄 가로모드 전환", config.NEON_GREEN),
                (pygame.Rect(366, 1084, 264, 60), "⛶ 전체화면 전환", config.POCHA_ORANGE),
            ]
            for br, blbl, bcol in r2_btns:
                pygame.draw.rect(portrait_surf, (42, 36, 64), br, border_radius=10)
                pygame.draw.rect(portrait_surf, bcol, br, width=2, border_radius=10)
                bs = btn_f.render(blbl, True, config.WHITE)
                portrait_surf.blit(bs, bs.get_rect(center=br.center))

            guide_r = pygame.Rect(12, 1162, 696, 102)
            pygame.draw.rect(portrait_surf, (24, 20, 40), guide_r, border_radius=12)
            pygame.draw.rect(portrait_surf, config.UI_BORDER, guide_r, width=2, border_radius=12)
            g_txt = sub_f.render(
                f"◀ 상단 탭·화살표 버튼 또는 좌우 스와이프로 카드를 전환하세요 ({t_idx + 1}/4) ▶",
                True,
                config.GOLD,
            )
            portrait_surf.blit(g_txt, g_txt.get_rect(center=(360, guide_r.y + 24)))
            for idx_p, p_fid in enumerate(["bungeoppang_redbean", "odeng_soup", "tteokbokki_cheese", "takoyaki_mayo", "taco_guac", "boba_milktea"]):
                px = 110 + idx_p * 100
                art_renderer.draw_food_icon(portrait_surf, (px, guide_r.y + 68), p_fid, size=44)

        # 3) 인게임(PlayScene) 세로 1패널 모드: 상단 HUD + 네이티브 손님 카운터 + 조리대 탭 바 + 1개 대형 조리대 + 하단 스킬 바
        elif self.current_scene_name in ("play", "duel_play"):
            from stations.base_station import STATE_COOKING, STATE_READY
            sc = self.current_scene
            hf = config.get_font(20, bold=True)
            btn_f = config.get_font(18, bold=True)
            tab_f = config.get_font(16, bold=True)
            badge_f = config.get_font(13, bold=True)

            # 1열 좌측: 모드·국가·일차 & 자산
            hud_left = pygame.Rect(8, 8, 448, 48)
            pygame.draw.rect(portrait_surf, (26, 22, 44), hud_left, border_radius=10)
            pygame.draw.rect(portrait_surf, config.GOLD, hud_left, width=2, border_radius=10)
            ch_id = getattr(self.game_mgr, "current_chapter", "KR")
            day_n = getattr(self.game_mgr, "day", 1)
            if getattr(self.game_mgr, "mode", "") == "SPECIALIST" and hasattr(self.game_mgr, "get_selected_specialist_data"):
                sp = self.game_mgr.get_selected_specialist_data()
                h_str = f"{sp['emoji']} {sp['short_name']} · Day {day_n}   💰 {self.game_mgr.gold:,}원"
            else:
                h_str = f"🏮 [{ch_id}] Day {day_n}   💰 {self.game_mgr.gold:,}원"
            h_txt = hf.render(h_str, True, config.GOLD)
            portrait_surf.blit(h_txt, (hud_left.x + 14, hud_left.centery - h_txt.get_height() // 2))

            # 1열 우측: [⚙️ 옵션] & [🏪 상점]
            top_right_bg = pygame.Rect(464, 8, 248, 48)
            pygame.draw.rect(portrait_surf, (18, 15, 28), top_right_bg, border_radius=10)
            opt_r = pygame.Rect(464, 8, 108, 48)
            shop_r = pygame.Rect(578, 8, 134, 48)
            pygame.draw.rect(portrait_surf, (48, 42, 74), opt_r, border_radius=10)
            pygame.draw.rect(portrait_surf, config.GOLD, opt_r, width=2, border_radius=10)
            os_txt = btn_f.render("⚙️ 옵션", True, config.GOLD)
            portrait_surf.blit(os_txt, os_txt.get_rect(center=opt_r.center))

            pygame.draw.rect(portrait_surf, (58, 52, 88), shop_r, border_radius=10)
            pygame.draw.rect(portrait_surf, config.NEON_CYAN, shop_r, width=2, border_radius=10)
            sh_txt = btn_f.render("🏪 준비/상점", True, config.WHITE)
            portrait_surf.blit(sh_txt, sh_txt.get_rect(center=shop_r.center))

            # 2열: 타이머·매출·콤보 바
            stat_bar = pygame.Rect(8, 60, 704, 44)
            pygame.draw.rect(portrait_surf, (24, 20, 40), stat_bar, border_radius=9)
            pygame.draw.rect(portrait_surf, config.UI_BORDER, stat_bar, width=2, border_radius=9)
            t_left = int(max(0.0, float(getattr(sc, "time_left", 90.0))))
            d_gold = int(getattr(self.game_mgr, "daily_gold", 0))
            t_gold = int(self.game_mgr.get_target_gold()) if hasattr(self.game_mgr, "get_target_gold") else 10000
            cmb = int(getattr(self.game_mgr, "combo", 0))
            st_str = f"⏱️ {t_left}초    💰 매출 {d_gold:,} / 목표 {t_gold:,}원    🔥 콤보 x{cmb}"
            st_s = btn_f.render(st_str, True, config.WHITE)
            portrait_surf.blit(st_s, st_s.get_rect(center=stat_bar.center))

            # 3열: 1:1 네이티브 손님 주문 카운터 (y=110..346, 가로 찌그러짐 0%)
            self._draw_portrait_play_customers(portrait_surf, pygame.Rect(8, 110, 704, 236), sc)

            # 4열: 조리 스테이션 전환 탭 바 (y=352..420) + 실시간 조리/완성/접시 배지
            for ar_r, ar_t in ((pygame.Rect(8, 352, 52, 68), "◀"), (pygame.Rect(660, 352, 52, 68), "▶")):
                pygame.draw.rect(portrait_surf, (48, 40, 76), ar_r, border_radius=10)
                pygame.draw.rect(portrait_surf, config.GOLD, ar_r, width=2, border_radius=10)
                ar_s = hf.render(ar_t, True, config.GOLD)
                portrait_surf.blit(ar_s, ar_s.get_rect(center=ar_r.center))

            is_spec = (
                self.current_scene_name == "play"
                and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "SPECIALIST"
            )
            tray_cnt = 0
            if hasattr(sc, "assembly_tray"):
                if hasattr(sc.assembly_tray, "get_total_dish_count"):
                    tray_cnt = int(sc.assembly_tray.get_total_dish_count())
                else:
                    tray_cnt = sum(1 for sl in getattr(sc.assembly_tray, "slots", []) if sl is not None)

            if is_spec:
                sp_st = getattr(sc, "specialist_station", None)
                sp_slots = getattr(sp_st, "slots", []) if sp_st else []
                ready_n = sum(1 for s in sp_slots if getattr(s, "state", "") == STATE_READY)
                flip_n = sum(1 for s in sp_slots if getattr(s, "is_flip_ready", False))
                cook_n = sum(1 for s in sp_slots if getattr(s, "state", "") == STATE_COOKING)
                if ready_n > 0:
                    app_badge, app_col = f"✨완료 {ready_n}!", config.NEON_GREEN
                elif flip_n > 0:
                    app_badge, app_col = f"🔄뒤집기 {flip_n}!", config.GOLD
                elif cook_n > 0:
                    app_badge, app_col = f"🔥조리중 {cook_n}", config.POCHA_ORANGE
                else:
                    app_badge, app_col = "6구 화로", config.TEXT_SECONDARY

                tab_defs = [
                    ("① 속재료 투입", "재료 선택", config.NEON_CYAN),
                    ("② 6구 전문화로", app_badge, app_col),
                    ("③ 조립 트레이", f"📦 {tray_cnt}개 적재" if tray_cnt > 0 else "무한적재·서빙", config.GOLD if tray_cnt > 0 else config.TEXT_SECONDARY),
                ]
            else:
                def _st_status(st_obj: Any, slot_key: str) -> Tuple[str, Tuple[int, int, int]]:
                    if hasattr(self.game_mgr, "is_slot_unlocked_in_story") and not self.game_mgr.is_slot_unlocked_in_story(slot_key):
                        return "🔒 미해금", config.TEXT_SECONDARY
                    slots = getattr(st_obj, "slots", []) if st_obj else []
                    if any(getattr(s, "state", "") == STATE_READY for s in slots):
                        return "✨완료!", config.NEON_GREEN
                    if any(getattr(s, "is_flip_ready", False) for s in slots):
                        return "🔄뒤집기!", config.GOLD
                    if any(getattr(s, "state", "") == STATE_COOKING for s in slots):
                        return "🔥조리중", config.POCHA_ORANGE
                    return "대기중", config.TEXT_SECONDARY

                m_b, m_c = _st_status(getattr(sc, "mold_station", None), "mold")
                d_b, d_c = _st_status(getattr(sc, "dispenser_station", None), "dispenser")
                g_b, g_c = _st_status(getattr(sc, "grill_station", None), "grill")
                b_b, b_c = _st_status(getattr(sc, "batch_pot_station", None), "batch_pot")
                tr_b = f"📦 {tray_cnt}개 적재!" if tray_cnt > 0 else "무한적재·서빙"
                tr_c = config.GOLD if tray_cnt > 0 else config.TEXT_SECONDARY

                tab_defs = [
                    ("① 몰드", m_b, m_c),
                    ("② 음료", d_b, d_c),
                    ("③ 트레이", tr_b, tr_c),
                    ("④ 그릴", g_b, g_c),
                    ("⑤ 대량팬", b_b, b_c),
                ]

            tab_cnt = len(tab_defs)
            avail_w = 592
            tab_w = (avail_w - (tab_cnt - 1) * 6) // tab_cnt
            active_p_idx = self.portrait_play_idx % tab_cnt

            for t_i, (t_title, t_sub, t_scol) in enumerate(tab_defs):
                tr = pygame.Rect(64 + t_i * (tab_w + 6), 352, tab_w, 68)
                is_act = t_i == active_p_idx
                bg = (232, 102, 36) if is_act else (32, 28, 52)
                bdr = config.WHITE if is_act else (t_scol if t_scol in (config.NEON_GREEN, config.GOLD) else config.UI_BORDER)
                pygame.draw.rect(portrait_surf, bg, tr, border_radius=10)
                pygame.draw.rect(portrait_surf, bdr, tr, width=3 if is_act else 2, border_radius=10)

                tt_s = tab_f.render(t_title, True, config.WHITE if is_act else config.TEXT_PRIMARY)
                ts_s = badge_f.render(t_sub, True, config.NEON_YELLOW if is_act else t_scol)
                portrait_surf.blit(tt_s, tt_s.get_rect(center=(tr.centerx, tr.y + 22)))
                portrait_surf.blit(ts_s, ts_s.get_rect(center=(tr.centerx, tr.y + 48)))

            # 5열 최하단: [◀ 이전 기구] + [👨‍🍳 마스터 액티브 스킬 발동!] + [🎬 스토리] + [다음 기구 ▶] (y=1186..1268)
            prev_btn = pygame.Rect(8, 1186, 116, 82)
            next_btn = pygame.Rect(596, 1186, 116, 82)
            for nav_r, nav_lbl in ((prev_btn, "◀ 이전기구"), (next_btn, "다음기구 ▶")):
                pygame.draw.rect(portrait_surf, (44, 38, 70), nav_r, border_radius=12)
                pygame.draw.rect(portrait_surf, config.NEON_CYAN, nav_r, width=2, border_radius=12)
                ns = tab_f.render(nav_lbl, True, config.WHITE)
                portrait_surf.blit(ns, ns.get_rect(center=nav_r.center))

            show_story_btn = (
                self.current_scene_name == "play"
                and getattr(self.game_mgr, "mode", "WORLD_TOUR") == "WORLD_TOUR"
            )
            skill_r = pygame.Rect(130, 1186, 338 if show_story_btn else 460, 82)
            char_data = self.game_mgr.get_selected_character_data()
            sk_unlocked = not hasattr(self.game_mgr, "is_slot_unlocked_in_story") or self.game_mgr.is_slot_unlocked_in_story("skill")
            sk_active = sk_unlocked and float(getattr(self.game_mgr, "skill_active_timer", 0.0)) > 0.0
            sk_ready = sk_unlocked and float(getattr(self.game_mgr, "skill_cooldown", 0.0)) <= 0.0

            sk_bg = (238, 152, 28) if sk_active else ((218, 92, 34) if sk_ready else (38, 34, 58))
            pygame.draw.rect(portrait_surf, sk_bg, skill_r, border_radius=12)
            pygame.draw.rect(portrait_surf, config.GOLD if (sk_ready or sk_active) else config.UI_BORDER, skill_r, width=2, border_radius=12)

            av_mini = pygame.Rect(skill_r.x + 10, skill_r.y + 9, 64, 64)
            art_renderer.draw_chef_avatar(
                portrait_surf,
                av_mini,
                character_id=self.game_mgr.selected_character,
                state="SKILL" if sk_active else "COOKING",
                time_tick=self._loading_tick,
            )
            if not sk_unlocked:
                sk_t1 = "🔒 Day 4 마스터 스킬 해금"
                sk_t2 = char_data["skill_name"]
            elif sk_active:
                sk_t1 = f"⚡ 스킬 발동 중! ({self.game_mgr.skill_active_timer:.1f}초)"
                sk_t2 = char_data["skill_name"]
            elif sk_ready:
                sk_t1 = "⚡ 마스터 스킬 발동! (터치)"
                sk_t2 = f"★ {char_data['skill_name']}"
            else:
                cd_sec = int(math.ceil(float(getattr(self.game_mgr, "skill_cooldown", 0.0))))
                sk_t1 = f"⏳ 스킬 쿨타임 {cd_sec}초"
                sk_t2 = char_data["skill_name"]

            s1_surf = tab_f.render(sk_t1, True, config.WHITE)
            s2_surf = badge_f.render(sk_t2, True, config.GOLD if sk_ready else config.TEXT_PRIMARY)
            portrait_surf.blit(s1_surf, (av_mini.right + 12, skill_r.y + 16))
            portrait_surf.blit(s2_surf, (av_mini.right + 12, skill_r.y + 46))

            if show_story_btn:
                story_r = pygame.Rect(474, 1186, 116, 82)
                pygame.draw.rect(portrait_surf, (64, 42, 108), story_r, border_radius=12)
                pygame.draw.rect(portrait_surf, config.GOLD, story_r, width=2, border_radius=12)
                sr_txt = tab_f.render("🎬 스토리", True, config.GOLD)
                portrait_surf.blit(sr_txt, sr_txt.get_rect(center=story_r.center))

        # 4) 상점/준비 화면(PrepScene) 세로 1패널 모드: 100% 1:1 네이티브 고해상도 렌더링
        elif self.current_scene_name == "prep":
            from data.chapters import CHAPTER_ORDER, CHAPTERS
            from data.characters import CHARACTERS
            from data.specialist_menus import SPECIALIST_MENUS, SPECIALIST_ORDER

            sc = self.current_scene
            active_tab = str(getattr(sc, "active_tab", "chapter")).lower()
            is_global = self.game_mgr.mode == "GLOBAL_ENDLESS"
            is_spec = self.game_mgr.mode == "SPECIALIST"
            top_f = config.get_font(17, bold=True)
            gold_f = config.get_font(19, bold=True)
            tab_f = config.get_font(16, bold=True)
            sub_f = config.get_font(15, bold=True)

            # 상단 네비게이션 버튼 3종
            nav_bg = pygame.Rect(8, 8, 456, 52)
            pygame.draw.rect(portrait_surf, (16, 14, 26), nav_bg, border_radius=10)
            b_back = pygame.Rect(8, 8, 118, 52)
            b_mode = pygame.Rect(132, 8, 214, 52)
            b_opt = pygame.Rect(352, 8, 112, 52)

            pygame.draw.rect(portrait_surf, (44, 38, 66), b_back, border_radius=10)
            pygame.draw.rect(portrait_surf, config.UI_BORDER, b_back, width=2, border_radius=10)
            bk_s = top_f.render("⬅ 타이틀", True, config.WHITE)
            portrait_surf.blit(bk_s, bk_s.get_rect(center=b_back.center))

            if is_spec:
                m_col = config.GOLD
                m_lbl = "🎯 장인 모드 ⇄"
            elif is_global:
                m_col = config.NEON_CYAN
                m_lbl = "🏮 글로벌 모드 ⇄"
            else:
                m_col = config.POCHA_ORANGE
                m_lbl = "🗺️ 9개국 투어 ⇄"
            pygame.draw.rect(portrait_surf, (44, 38, 66), b_mode, border_radius=10)
            pygame.draw.rect(portrait_surf, m_col, b_mode, width=2, border_radius=10)
            ms = top_f.render(m_lbl, True, m_col)
            portrait_surf.blit(ms, ms.get_rect(center=b_mode.center))

            pygame.draw.rect(portrait_surf, (44, 38, 66), b_opt, border_radius=10)
            pygame.draw.rect(portrait_surf, config.GOLD, b_opt, width=2, border_radius=10)
            os = top_f.render("⚙️ 옵션", True, config.GOLD)
            portrait_surf.blit(os, os.get_rect(center=b_opt.center))

            # 상단 우측 보유 골드 박스
            gold_box = pygame.Rect(472, 8, 240, 52)
            pygame.draw.rect(portrait_surf, (36, 30, 52), gold_box, border_radius=10)
            pygame.draw.rect(portrait_surf, config.GOLD, gold_box, width=2, border_radius=10)
            gs = gold_f.render(f"💰 {self.game_mgr.gold:,}원", True, config.GOLD)
            portrait_surf.blit(gs, gs.get_rect(center=gold_box.center))

            # 4대 메인 탭 버튼 바
            tab_bar_bg = pygame.Rect(8, 66, 704, 52)
            pygame.draw.rect(portrait_surf, (16, 14, 26), tab_bar_bg, border_radius=10)
            if is_spec:
                tab2_lbl = "🎯 장인종목"
            elif is_global:
                tab2_lbl = "🏮 기구배치"
            else:
                tab2_lbl = f"🗺️ 챕터({len(self.game_mgr.unlocked_chapters)}/9)"
            portrait_tabs = [
                ("character", pygame.Rect(8, 66, 172, 52), f"👨‍🍳 마스터({len(self.game_mgr.unlocked_characters)}/32)"),
                ("chapter", pygame.Rect(184, 66, 176, 52), tab2_lbl),
                ("upgrade", pygame.Rect(364, 66, 172, 52), "🛠️ 강화·상점"),
                ("tournament", pygame.Rect(540, 66, 172, 52), "🏆 32강 대회"),
            ]
            for tkey, tr, tlbl in portrait_tabs:
                is_act = active_tab == tkey
                tbg = (235, 112, 38) if is_act else (36, 32, 54)
                tbdr = config.GOLD if is_act else config.UI_BORDER
                tfg = config.WHITE if is_act else (215, 210, 232)
                pygame.draw.rect(portrait_surf, tbg, tr, border_radius=10)
                pygame.draw.rect(portrait_surf, tbdr, tr, width=3 if is_act else 1, border_radius=10)
                ts = tab_f.render(tlbl, True, tfg)
                portrait_surf.blit(ts, ts.get_rect(center=tr.center))

            # 서브 패널 전환 바 (y=124..180): [◀] + 현재 단일 패널 정보/서브탭 + [▶]
            for ar_r, ar_t in ((pygame.Rect(8, 124, 68, 56), "◀"), (pygame.Rect(644, 124, 68, 56), "▶")):
                pygame.draw.rect(portrait_surf, (48, 40, 76), ar_r, border_radius=10)
                pygame.draw.rect(portrait_surf, config.GOLD, ar_r, width=2, border_radius=10)
                ar_s = gold_f.render(ar_t, True, config.GOLD)
                portrait_surf.blit(ar_s, ar_s.get_rect(center=ar_r.center))

            mid_bar = pygame.Rect(82, 124, 556, 56)
            pygame.draw.rect(portrait_surf, (26, 22, 44), mid_bar, border_radius=10)
            pygame.draw.rect(portrait_surf, config.UI_BORDER, mid_bar, width=2, border_radius=10)

            if active_tab == "character":
                filtered = sc._get_filtered_characters() if hasattr(sc, "_get_filtered_characters") else list(CHARACTERS.keys())
                insp_id = getattr(sc, "inspected_character", self.game_mgr.selected_character)
                c_obj = CHARACTERS.get(insp_id, CHARACTERS["chef_kr"])
                c_pos = (filtered.index(insp_id) + 1) if insp_id in filtered else 1
                info_lbl = f"👨‍🍳 [{c_obj.get('region_name', '')}] {c_obj['name']} ({c_pos}/{len(filtered)})"
                inf_s = tab_f.render(info_lbl, True, config.GOLD)
                portrait_surf.blit(inf_s, (mid_bar.x + 14, mid_bar.centery - inf_s.get_height() // 2))

                toggle_r = pygame.Rect(454, 128, 182, 48)
                is_grid = (self.portrait_prep_idx % 2) == 1
                pygame.draw.rect(portrait_surf, (62, 52, 98) if not is_grid else (218, 96, 36), toggle_r, border_radius=8)
                pygame.draw.rect(portrait_surf, config.NEON_CYAN, toggle_r, width=2, border_radius=8)
                tg_txt = sub_f.render("👨‍🍳 상세 카드 보기" if is_grid else "📋 32인 목록/필터", True, config.WHITE)
                portrait_surf.blit(tg_txt, tg_txt.get_rect(center=toggle_r.center))

            elif active_tab == "chapter":
                if is_spec:
                    idx = self.portrait_prep_idx % len(SPECIALIST_ORDER)
                    sp_id = SPECIALIST_ORDER[idx]
                    sp_d = SPECIALIST_MENUS[sp_id]
                    ch_txt = gold_f.render(f"{sp_d['emoji']} {sp_d['name']}  ({idx + 1}/{len(SPECIALIST_ORDER)})", True, config.GOLD)
                    portrait_surf.blit(ch_txt, ch_txt.get_rect(center=mid_bar.center))
                elif is_global:
                    slot_labels = ["① 몰드", "② 그릴", "③ 대량팬", "④ 음료"]
                    cur_s = self.portrait_prep_idx % 4
                    for s_i, sl_lbl in enumerate(slot_labels):
                        sr = pygame.Rect(82 + s_i * 102, 128, 96, 48)
                        is_sel = s_i == cur_s
                        pygame.draw.rect(portrait_surf, (232, 102, 36) if is_sel else (38, 32, 60), sr, border_radius=8)
                        pygame.draw.rect(portrait_surf, config.GOLD if is_sel else config.UI_BORDER, sr, width=2 if is_sel else 1, border_radius=8)
                        ss = sub_f.render(sl_lbl, True, config.WHITE)
                        portrait_surf.blit(ss, ss.get_rect(center=sr.center))
                    pg_btn = pygame.Rect(494, 128, 142, 48)
                    pygame.draw.rect(portrait_surf, (46, 40, 74), pg_btn, border_radius=8)
                    pygame.draw.rect(portrait_surf, config.NEON_CYAN, pg_btn, width=2, border_radius=8)
                    g_pg = int(getattr(sc, "global_station_page", 0)) + 1
                    ps = sub_f.render(f"국가전환 {g_pg}/3 ▶", True, config.NEON_CYAN)
                    portrait_surf.blit(ps, ps.get_rect(center=pg_btn.center))
                else:
                    idx = self.portrait_prep_idx % len(CHAPTER_ORDER)
                    ch_id = CHAPTER_ORDER[idx]
                    ch_d = CHAPTERS[ch_id]
                    ch_txt = gold_f.render(f"🗺️ [{ch_id}] {ch_d['name']}  ({idx + 1}/{len(CHAPTER_ORDER)})", True, config.GOLD)
                    portrait_surf.blit(ch_txt, ch_txt.get_rect(center=mid_bar.center))

            elif active_tab == "upgrade":
                sub_opts = ["🛠️ 기구·트레이 강화 (5종)", "🏮 포차 인테리어 (4종)"]
                cur_u = self.portrait_prep_idx % 2
                for u_i, u_lbl in enumerate(sub_opts):
                    sr = pygame.Rect(84 + u_i * 278, 128, 270, 48)
                    is_sel = u_i == cur_u
                    pygame.draw.rect(portrait_surf, (232, 102, 36) if is_sel else (38, 32, 60), sr, border_radius=8)
                    pygame.draw.rect(portrait_surf, config.GOLD if is_sel else config.UI_BORDER, sr, width=2 if is_sel else 1, border_radius=8)
                    us = tab_f.render(u_lbl, True, config.WHITE)
                    portrait_surf.blit(us, us.get_rect(center=sr.center))

            else:  # tournament
                sub_opts = ["⚔️ AI 보스전 출격", "🏆 32강 전체 대진표"]
                cur_t = self.portrait_prep_idx % 2
                for t_i, t_lbl in enumerate(sub_opts):
                    sr = pygame.Rect(84 + t_i * 278, 128, 270, 48)
                    is_sel = t_i == cur_t
                    pygame.draw.rect(portrait_surf, (224, 72, 46) if is_sel else (38, 32, 60), sr, border_radius=8)
                    pygame.draw.rect(portrait_surf, config.GOLD if is_sel else config.UI_BORDER, sr, width=2 if is_sel else 1, border_radius=8)
                    ts = tab_f.render(t_lbl, True, config.WHITE)
                    portrait_surf.blit(ts, ts.get_rect(center=sr.center))

            # 중앙 초대형 카드 1:1 네이티브 직접 렌더링
            self._draw_portrait_prep_card_native(portrait_surf, pygame.Rect(16, 188, 688, 848), sc)

            # 하단 요약 카드 (y=1046..1152)
            sum_bar = pygame.Rect(8, 1046, 704, 106)
            pygame.draw.rect(portrait_surf, (24, 20, 40), sum_bar, border_radius=12)
            pygame.draw.rect(portrait_surf, config.UI_BORDER, sum_bar, width=2, border_radius=12)

            av_sum = pygame.Rect(sum_bar.x + 16, sum_bar.y + 12, 82, 82)
            pygame.draw.rect(portrait_surf, (36, 30, 56), av_sum.inflate(6, 6), border_radius=12)
            pygame.draw.rect(portrait_surf, config.GOLD, av_sum.inflate(6, 6), width=2, border_radius=12)
            art_renderer.draw_chef_avatar(
                portrait_surf,
                av_sum,
                character_id=self.game_mgr.selected_character,
                state="IDLE",
                time_tick=self._loading_tick,
            )

            char_d = self.game_mgr.get_selected_character_data()
            t_gold = self.game_mgr.get_target_gold()
            s_line1 = top_f.render(f"👨‍🍳 [{char_d.get('region_name', '')}] {char_d['name']}  ·  ★ {char_d['skill_name']}", True, config.WHITE)
            s_line2 = gold_f.render(f"📅 Day {self.game_mgr.day}   |   🎯 목표 매출: {t_gold:,}원", True, config.GOLD)
            portrait_surf.blit(s_line1, (av_sum.right + 18, sum_bar.y + 18))
            portrait_surf.blit(s_line2, (av_sum.right + 18, sum_bar.y + 56))

            start_r = pygame.Rect(80, 1162, 560, 96)
            pygame.draw.rect(portrait_surf, (238, 104, 36), start_r, border_radius=16)
            pygame.draw.rect(portrait_surf, config.GOLD, start_r, width=3, border_radius=16)
            st_f = config.get_font(26, bold=True)
            st_s = st_f.render("🏮 오늘 영업 시작! (START) ▶", True, config.WHITE)
            portrait_surf.blit(st_s, st_s.get_rect(center=start_r.center))

        # 5) 플로팅 텍스트/파티클을 세로 캔버스 위에 1:1 네이티브로 표시
        if len(mappings) > 1 and self.current_scene is not None and hasattr(self.current_scene, "particles"):
            try:
                self.current_scene.particles.draw(portrait_surf)
            except Exception:
                pass

    def draw(self, surface: pygame.Surface) -> None:
        """현재 활성 씬과 전역 옵션 모달을 렌더링하며, 가로(16:9/20:9) 및 세로(9:16/9:18) 화면비로 자동 스케일링한다."""
        if self.current_scene is None or not hasattr(self.current_scene, "draw"):
            return

        target_size = surface.get_size()
        logical_size = (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        want_portrait = (target_size[1] > target_size[0]) or self.is_portrait_mode

        if want_portrait:
            self._sync_prep_logical_page_for_portrait()

        if target_size == logical_size and not want_portrait:
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

        # Emscripten(웹앱)에서 내부 SDL 버퍼가 1280x720으로 고정된 상태에서 세로 모드가 켜진 경우 즉시 720x1280으로 재전환 시도
        if want_portrait and target_size[0] >= target_size[1]:
            try:
                new_surf = pygame.display.set_mode(config.PORTRAIT_SIZE, 0)
                if new_surf is not None and new_surf.get_size()[1] > new_surf.get_size()[0]:
                    surface = new_surf
                    target_size = surface.get_size()
            except Exception:
                pass
            if target_size[0] >= target_size[1]:
                portrait_size = (config.PORTRAIT_WIDTH, config.PORTRAIT_HEIGHT)
                if self._portrait_surface is None or self._portrait_surface.get_size() != portrait_size:
                    self._portrait_surface = pygame.Surface(portrait_size)
                self._compose_portrait_surface(self._logical_surface, self._portrait_surface)
                try:
                    pygame.transform.smoothscale(self._portrait_surface, target_size, surface)
                except Exception:
                    scaled = pygame.transform.scale(self._portrait_surface, target_size)
                    surface.blit(scaled, (0, 0))
                return

        ox, oy, vp_w, vp_h, _scale = self._compute_viewport(target_size[0], target_size[1])
        if ox > 0 or oy > 0:
            self._draw_mobile_bleed_bezels(surface, ox, oy, vp_w, vp_h)

        # 세로 모드(Portrait, win_h > win_w)인 경우 720x1280 세로 레이아웃 캔버스로 재조합 후 출력
        if want_portrait:
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
        is_mob = config.is_mobile_ui()
        p_ratio = max(0.0, min(1.0, float(self.loading_progress)))
        pct = int(round(p_ratio * 100))
        theme = self.get_current_loading_theme()
        accent = theme.get("accent", config.POCHA_ORANGE)
        foods = theme.get("foods", ("bungeoppang_redbean", "bungeoppang_cream"))
        is_ready_tap = self.loading_wait_for_tap and p_ratio >= 1.0

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
        hdr_s = title_f.render("🏮 포차 영업 준비 중...", True, config.GOLD)
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
        pygame.draw.rect(surface, (38, 88, 54) if is_ready_tap else (28, 22, 46), pct_box, border_radius=18)
        pygame.draw.rect(surface, config.GOLD if is_ready_tap else accent, pct_box, width=2, border_radius=18)
        pct_label = "COMPLETE 100%" if is_ready_tap else f"LOADING {pct}%"
        pct_surf = config.get_font(13 if is_ready_tap else 15, bold=True).render(
            pct_label,
            True,
            config.NEON_GREEN if is_ready_tap else config.GOLD,
        )
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

        # 6) 하단 포차 운영 꿀팁 배너 또는 100% 완료 시 인게임 [터치하여 포차 오픈!] 대기 버튼
        tip_rect = pygame.Rect(card.x + 50, card.bottom - 58, card.width - 100, 42)
        if is_ready_tap:
            pulse = 0.86 + 0.14 * math.sin(self._loading_tick * 6.5)
            btn_bg = (int(238 * pulse), int(98 * pulse), 34)
            pygame.draw.rect(surface, btn_bg, tip_rect, border_radius=12)
            pygame.draw.rect(surface, config.GOLD, tip_rect, width=3, border_radius=12)
            tap_f = config.get_font(18, bold=True)
            tap_s = tap_f.render(
                "🏮 영업 준비 100% 완료! 화면을 터치하여 포차를 오픈하세요! [TOUCH TO START]",
                True,
                config.WHITE,
            )
            surface.blit(tap_s, tap_s.get_rect(center=tip_rect.center))
        else:
            pygame.draw.rect(surface, (30, 24, 48), tip_rect, border_radius=10)
            pygame.draw.rect(surface, config.UI_BORDER, tip_rect, width=1, border_radius=10)
            tip_s = tip_f.render(f"💡 {theme.get('tip', '')}", True, config.NEON_CYAN)
            surface.blit(tip_s, tip_s.get_rect(center=tip_rect.center))
