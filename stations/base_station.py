"""
stations/base_station.py
모든 조리 기구의 공통 슬롯(StationSlot) 상태 머신 및 기본 스테이션(BaseStation) 추상 인터페이스 모듈.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import pygame

import config
from core.art_renderer import draw_food_icon, draw_station_hardware
from core.game_manager import GameManager
from data.chapters import STATIONS_CATALOG
from data.recipes import RECIPES

STATE_IDLE: str = "IDLE"
STATE_COOKING: str = "COOKING"
STATE_READY: str = "READY"
STATE_BURNT: str = "BURNT"


def invoke_auto_serve(
    auto_serve_cb: Optional[Callable[..., Any]],
    recipe_id: str,
    center_pos: Tuple[int, int],
) -> Tuple[bool, Any]:
    """
    auto_serve_cb 콜백을 안전하게 호출한다.
    콜백이 (recipe_id, pos) 2개 인자를 받거나 (recipe_id) 1개 인자를 받는 경우를 모두 지원하며,
    반환값이 bool이거나 dict({'served': bool, ...})인 경우를 모두 처리한다.
    """
    if auto_serve_cb is None:
        return False, None
    try:
        res = auto_serve_cb(recipe_id, center_pos)
    except TypeError:
        res = auto_serve_cb(recipe_id)

    if res is None or res is False:
        return False, res
    if isinstance(res, dict):
        return bool(res.get("served", True)), res
    return bool(res), res


class StationSlot:
    """
    조리 기구 내의 개별 조리 슬롯 상태 머신.
    상태 전이: IDLE -> COOKING -> READY -> BURNT
    """

    def __init__(
        self,
        slot_index: int = 0,
        rect: Optional[Union[pygame.Rect, Tuple[int, int, int, int]]] = None,
        can_burn: bool = True,
    ) -> None:
        self.slot_index: int = int(slot_index)
        self.rect: pygame.Rect = (
            rect.copy()
            if isinstance(rect, pygame.Rect)
            else pygame.Rect(rect or (0, 0, 72, 72))
        )
        self.state: str = STATE_IDLE
        self.recipe_id: Optional[str] = None
        self.elapsed: float = 0.0
        self.cook_time: float = 4.5
        self.burn_time: float = 9.0
        self.can_burn: bool = bool(can_burn)
        self.servings: int = 0
        self.max_servings: int = 1

    @property
    def timer(self) -> float:
        """elapsed의 별칭."""
        return self.elapsed

    @timer.setter
    def timer(self, value: float) -> None:
        self.elapsed = float(value)

    @property
    def is_idle(self) -> bool:
        return self.state == STATE_IDLE

    @property
    def is_cooking(self) -> bool:
        return self.state == STATE_COOKING

    @property
    def is_ready(self) -> bool:
        return self.state == STATE_READY

    @property
    def is_burnt(self) -> bool:
        return self.state == STATE_BURNT

    @property
    def progress(self) -> float:
        """조리 진행률(0.0 ~ 1.0)을 반환한다."""
        if self.state == STATE_IDLE:
            return 0.0
        if self.state == STATE_COOKING:
            return max(0.0, min(1.0, self.elapsed / max(0.05, self.cook_time)))
        return 1.0

    @property
    def burn_progress(self) -> float:
        """완성 후 타기까지의 진행률(0.0 ~ 1.0)을 반환한다."""
        if self.state == STATE_BURNT:
            return 1.0
        if self.state == STATE_READY and self.can_burn:
            return max(0.0, min(1.0, self.elapsed / max(0.05, self.burn_time)))
        return 0.0

    def start_cooking(
        self,
        recipe_id: str,
        cook_time: float,
        burn_time: float = 9.0,
        can_burn: Optional[bool] = None,
        servings: int = 1,
    ) -> None:
        """슬롯에서 지정된 레시피의 조리를 시작한다."""
        self.recipe_id = str(recipe_id)
        self.cook_time = max(0.2, float(cook_time))
        self.burn_time = max(1.0, float(burn_time))
        if can_burn is not None:
            self.can_burn = bool(can_burn)
        self.max_servings = max(1, int(servings))
        self.servings = self.max_servings
        self.elapsed = 0.0
        self.state = STATE_COOKING

    def instant_finish(self) -> bool:
        """조리 중인 슬롯을 즉시 완성(READY) 상태로 전환한다."""
        if self.state == STATE_COOKING and self.recipe_id:
            self.state = STATE_READY
            self.elapsed = 0.0
            self.servings = max(1, self.max_servings)
            return True
        return False

    def reset(self) -> None:
        """슬롯을 빈 상태(IDLE)로 초기화한다."""
        self.state = STATE_IDLE
        self.recipe_id = None
        self.elapsed = 0.0
        self.servings = 0

    clear = reset

    def update(self, dt: float) -> Optional[str]:
        """
        시간 경과(dt)에 따라 조리 및 탄 상태를 업데이트한다.
        상태 전이가 발생하면 새로운 상태 문자열(STATE_READY, STATE_BURNT)을 반환한다.
        """
        dt = max(0.0, float(dt))
        if self.state == STATE_COOKING:
            self.elapsed += dt
            if self.elapsed >= self.cook_time:
                self.state = STATE_READY
                self.elapsed = 0.0
                self.servings = max(1, self.max_servings)
                return STATE_READY

        elif self.state == STATE_READY and self.can_burn:
            self.elapsed += dt
            if self.elapsed >= self.burn_time:
                self.state = STATE_BURNT
                self.elapsed = 0.0
                return STATE_BURNT

        return None

    def draw_slot_box(
        self,
        surface: pygame.Surface,
        time_tick: float = 0.0,
        empty_label: str = "클릭 조리",
    ) -> None:
        """개별 슬롯 박스, 음식 아이콘, 상태 텍스트 및 진행률 게이지 바를 렌더링한다."""
        r = self.rect
        if self.state == STATE_IDLE:
            bg_col = (34, 32, 44)
            border_col = (88, 84, 108)
        elif self.state == STATE_COOKING:
            bg_col = (54, 42, 32)
            border_col = config.GAUGE_COOKING
        elif self.state == STATE_READY:
            if self.can_burn and self.burn_progress >= 0.65:
                bg_col = (68, 36, 28)
                border_col = config.GAUGE_WARNING
            else:
                bg_col = (32, 58, 42)
                border_col = config.GAUGE_READY
        else:  # STATE_BURNT
            bg_col = (48, 24, 26)
            border_col = config.GAUGE_BURNT

        pygame.draw.rect(surface, bg_col, r, border_radius=8)
        pygame.draw.rect(surface, border_col, r, width=2, border_radius=8)

        font_sm = config.get_font(13, bold=True)
        font_xs = config.get_font(12, bold=True)

        if self.state == STATE_IDLE:
            lbl = font_xs.render(empty_label.replace("클릭", "터치"), True, config.TEXT_SECONDARY)
            surface.blit(lbl, (r.centerx - lbl.get_width() // 2, r.centery - lbl.get_height() // 2))
            return

        icon_size = min(48, max(30, min(r.width, r.height) - 20))
        icon_center = (r.centerx, r.y + icon_size // 2 + 5)
        if self.recipe_id:
            draw_food_icon(
                surface,
                icon_center,
                self.recipe_id,
                size=icon_size,
                burnt=(self.state == STATE_BURNT),
            )

        # 하단 게이지 바 및 상태 라벨 (모바일 시인성 강화: 게이지 두께 10px)
        gauge_rect = pygame.Rect(r.x + 6, r.bottom - 15, r.width - 12, 10)
        pygame.draw.rect(surface, config.GAUGE_BG, gauge_rect, border_radius=5)

        if self.state == STATE_COOKING:
            fill_w = int((gauge_rect.width - 2) * self.progress)
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    config.GAUGE_COOKING,
                    (gauge_rect.x + 1, gauge_rect.y + 1, fill_w, gauge_rect.height - 2),
                    border_radius=4,
                )
            st_surf = font_xs.render("조리중...", True, config.GAUGE_COOKING)
            surface.blit(st_surf, (r.centerx - st_surf.get_width() // 2, gauge_rect.top - 17))

        elif self.state == STATE_READY:
            if self.can_burn:
                rem_ratio = 1.0 - self.burn_progress
                bar_col = config.GAUGE_WARNING if self.burn_progress >= 0.60 else config.GAUGE_READY
                fill_w = int((gauge_rect.width - 2) * rem_ratio)
            else:
                bar_col = config.GAUGE_READY
                fill_w = gauge_rect.width - 2
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    bar_col,
                    (gauge_rect.x + 1, gauge_rect.y + 1, fill_w, gauge_rect.height - 2),
                    border_radius=4,
                )
            label_txt = "주의! 곧 탐" if (self.can_burn and self.burn_progress >= 0.65) else "완성! 터치"
            label_col = config.GAUGE_WARNING if (self.can_burn and self.burn_progress >= 0.65) else config.GAUGE_READY
            st_surf = font_sm.render(label_txt, True, label_col)
            surface.blit(st_surf, (r.centerx - st_surf.get_width() // 2, gauge_rect.top - 17))

        elif self.state == STATE_BURNT:
            pygame.draw.rect(
                surface,
                config.GAUGE_BURNT,
                (gauge_rect.x + 1, gauge_rect.y + 1, gauge_rect.width - 2, gauge_rect.height - 2),
                border_radius=4,
            )
            st_surf = font_sm.render("탄 음식 비우기", True, config.GAUGE_BURNT)
            surface.blit(st_surf, (r.centerx - st_surf.get_width() // 2, gauge_rect.top - 17))

        pygame.draw.rect(surface, config.GAUGE_BORDER, gauge_rect, width=1, border_radius=4)


class BaseStation:
    """
    모든 조리 스테이션(MoldStation, GrillStation, BatchPotStation, DispenserStation)의 공통 부모 클래스.
    """

    def __init__(
        self,
        station_id: str,
        slot_type: str,
        rect: Union[pygame.Rect, Tuple[int, int, int, int]],
        game_mgr: Any = None,
    ) -> None:
        self.slot_type: str = str(slot_type)
        self.game_mgr: Any = game_mgr or GameManager.get_instance()
        self.rect: pygame.Rect = (
            rect.copy() if isinstance(rect, pygame.Rect) else pygame.Rect(rect)
        )
        self._last_layout_rect: pygame.Rect = self.rect.copy()
        self.slots: List[StationSlot] = []

        self.station_id: str = ""
        self.meta: Dict[str, Any] = {}
        self.name: str = ""
        self.short_name: str = ""
        self.country: str = "KR"
        self.set_station_id(station_id)

    @staticmethod
    def _parse_init_args(
        default_slot_type: str,
        default_station_id: str,
        default_rect: Tuple[int, int, int, int],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> Tuple[str, pygame.Rect, Any]:
        """
        다양한 생성자 호출 시그니처(rect 우선, station_id 우선, game_mgr 우선 등)를
        모두 호환하도록 파싱하는 헬퍼.
        """
        game_mgr = kwargs.get("game_mgr") or kwargs.get("manager")
        station_id = kwargs.get("station_id")
        rect = kwargs.get("rect")

        for arg in args:
            if isinstance(arg, str):
                station_id = station_id or arg
            elif isinstance(arg, pygame.Rect) or (
                isinstance(arg, (tuple, list)) and len(arg) == 4
            ):
                rect = rect or arg
            elif hasattr(arg, "get_active_stations"):
                game_mgr = game_mgr or arg

        mgr = game_mgr or GameManager.get_instance()
        if not station_id:
            if mgr and hasattr(mgr, "get_active_stations"):
                active = mgr.get_active_stations()
                station_id = str(active.get(default_slot_type, default_station_id))
            else:
                station_id = default_station_id

        final_rect = (
            rect.copy()
            if isinstance(rect, pygame.Rect)
            else pygame.Rect(rect if rect is not None else default_rect)
        )
        return str(station_id), final_rect, mgr

    def set_station_id(self, station_id: str) -> None:
        """장착된 조리 기구 ID를 설정하고 메타데이터 및 슬롯 구성을 갱신한다."""
        if station_id not in STATIONS_CATALOG:
            # 해당 슬롯 타입의 기본 한국 기구로 폴백
            defaults = {
                "mold": "kr_bungeoppang",
                "grill": "kr_skewer_grill",
                "batch_pot": "kr_tteokbokki_pan",
                "dispenser": "kr_odeng_dispenser",
            }
            station_id = defaults.get(self.slot_type, "kr_bungeoppang")

        self.station_id = str(station_id)
        self.meta = STATIONS_CATALOG[self.station_id]
        self.name = str(self.meta["name"])
        self.short_name = str(self.meta["short_name"])
        self.country = str(self.meta["country"])
        self._on_station_changed()
        self.sync_slots_with_manager()

    def _on_station_changed(self) -> None:
        """하위 클래스에서 기구 변경 시 레시피 목록 등을 갱신하기 위한 훅."""
        pass

    def _get_desired_slot_count(self) -> int:
        if self.slot_type == "batch_pot":
            return 1
        if self.game_mgr and hasattr(self.game_mgr, "get_station_slot_count"):
            return max(1, int(self.game_mgr.get_station_slot_count(self.slot_type)))
        return 2

    def sync_slots_with_manager(self) -> None:
        """
        GameManager의 활성 기구 및 업그레이드 레벨에 맞춰 슬롯 수를 동적으로 동기화한다.
        기존 슬롯의 조리 상태는 그대로 보존한다.
        """
        if self.game_mgr and hasattr(self.game_mgr, "get_active_stations"):
            active_id = str(self.game_mgr.get_active_stations().get(self.slot_type, self.station_id))
            if active_id in STATIONS_CATALOG and active_id != self.station_id:
                self.station_id = active_id
                self.meta = STATIONS_CATALOG[self.station_id]
                self.name = str(self.meta["name"])
                self.short_name = str(self.meta["short_name"])
                self.country = str(self.meta["country"])
                self._on_station_changed()

        desired = self._get_desired_slot_count()
        can_burn = self.slot_type not in ("dispenser", "batch_pot")

        while len(self.slots) < desired:
            idx = len(self.slots)
            self.slots.append(StationSlot(slot_index=idx, can_burn=can_burn))
        if len(self.slots) > desired:
            self.slots = self.slots[:desired]

        self._rebuild_layout()

    def _ensure_layout(self) -> None:
        if self.rect != self._last_layout_rect:
            self._last_layout_rect = self.rect.copy()
            self._rebuild_layout()

    def _rebuild_layout(self) -> None:
        """슬롯 및 버튼 좌표를 self.rect 기준으로 재계산한다."""
        self._last_layout_rect = self.rect.copy()

    def get_cook_time(self, recipe_id: str) -> float:
        """패시브 및 기구 업그레이드가 적용된 조리 시간을 반환한다."""
        if self.game_mgr and hasattr(self.game_mgr, "get_cook_time"):
            return float(self.game_mgr.get_cook_time(recipe_id, self.slot_type))
        rec = RECIPES.get(recipe_id)
        return float(rec["cook_time"]) if rec else 4.5

    def get_burn_time(self, recipe_id: str) -> float:
        """패시브 및 기구 업그레이드가 적용된 타는 시간을 반환한다."""
        if self.game_mgr and hasattr(self.game_mgr, "get_burn_time"):
            return float(self.game_mgr.get_burn_time(recipe_id, self.slot_type))
        rec = RECIPES.get(recipe_id)
        return float(rec["burn_time"]) if rec else 9.0

    def instant_finish_all(self) -> int:
        """
        현재 COOKING 상태인 모든 슬롯을 즉시 READY 상태로 완성한다 (켄지 액티브 스킬 연동용).
        완성된 슬롯의 개수를 반환한다.
        """
        finished_count = 0
        for slot in self.slots:
            if slot.instant_finish():
                finished_count += 1
        return finished_count

    def reset_all(self) -> None:
        """모든 슬롯을 초기 상태(IDLE)로 리셋한다."""
        for slot in self.slots:
            slot.reset()

    def update(self, dt: float) -> None:
        """모든 슬롯의 타이머를 업데이트한다."""
        for slot in self.slots:
            slot.update(dt)

    def draw_panel_frame(self, surface: pygame.Surface, subtitle: str = "") -> None:
        """조리대 패널 배경, 하드웨어 텍스처, 상단 기구 이름 헤더를 렌더링한다."""
        self._ensure_layout()
        pygame.draw.rect(surface, config.UI_PANEL_DARK, self.rect, border_radius=12)
        hw_rect = pygame.Rect(
            self.rect.x + 6,
            self.rect.y + 36,
            self.rect.width - 12,
            self.rect.height - 42,
        )
        draw_station_hardware(
            surface,
            hw_rect,
            station_type=self.slot_type,
            station_id=self.station_id,
        )
        pygame.draw.rect(surface, config.UI_BORDER, self.rect, width=2, border_radius=12)

        # 상단 타이틀 바
        header_rect = pygame.Rect(self.rect.x + 4, self.rect.y + 4, self.rect.width - 8, 28)
        header_col = self.meta.get("color", config.UI_PANEL_LIGHT)
        dark_header = (
            max(20, int(header_col[0] * 0.45)),
            max(20, int(header_col[1] * 0.45)),
            max(25, int(header_col[2] * 0.45)),
        )
        pygame.draw.rect(surface, dark_header, header_rect, border_radius=8)

        title_font = config.get_font(13, bold=True)
        title_txt = self.short_name or self.name
        if subtitle:
            title_txt = f"{title_txt} ({subtitle})"
        title_surf = title_font.render(title_txt, True, config.TEXT_PRIMARY)
        tx = max(header_rect.x + 40, header_rect.centerx - title_surf.get_width() // 2)
        surface.blit(
            title_surf,
            (
                tx,
                header_rect.centery - title_surf.get_height() // 2,
            ),
        )

    def draw(
        self,
        surface: pygame.Surface,
        time_tick: Any = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """스테이션과 슬롯들을 화면에 렌더링한다."""
        t = float(time_tick) if isinstance(time_tick, (int, float)) else 0.0
        self.draw_panel_frame(surface)
        for slot in self.slots:
            slot.draw_slot_box(surface, time_tick=t)

    def handle_click(
        self,
        pos: Tuple[int, int],
        assembly_tray: Any = None,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """마우스 클릭 입력을 처리한다. 하위 클래스에서 구체적으로 구현한다."""
        return None
