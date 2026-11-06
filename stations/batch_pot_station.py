"""
stations/batch_pot_station.py
철판 떡볶이 / 야키소바 / 나초 프라이어 / 불꽃 큐브스테이크 등 대량 조리·보온 스테이션 모듈.
- 1회 조리로 game_mgr.get_batch_servings() 인분(기본 3인분, 최대 7인분)을 한꺼번에 생산
- 완성 후 타지 않고 보온 유지 (remaining_servings 표시)
- READY 상태에서 클릭 시 1인분을 덜어 조립 트레이(AssemblyTray)로 Dish 전달
  (트레이가 가득 찼을 때 기본 메뉴 주문 손님이 있으면 즉시 자동 서빙)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple
import pygame

import config
from core.art_renderer import draw_food_icon
from data.recipes import RECIPES, get_recipes_by_station
from entities.dish import Dish
from stations.base_station import (
    STATE_COOKING,
    STATE_IDLE,
    STATE_READY,
    BaseStation,
    StationSlot,
    invoke_auto_serve,
)


class BatchPotStation(BaseStation):
    """
    대량 조리 및 보온 스테이션 (slot_type = 'batch_pot').
    한 번 조리하면 N인분이 생성되며, 타지 않고 보온 상태를 유지한다.
    """

    DEFAULT_RECT: Tuple[int, int, int, int] = (818, 355, 214, 352)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        station_id, rect, game_mgr = self._parse_init_args(
            default_slot_type="batch_pot",
            default_station_id="kr_tteokbokki_pan",
            default_rect=self.DEFAULT_RECT,
            args=args,
            kwargs=kwargs,
        )
        self.base_recipe_id: str = "tteokbokki_plain"
        self.pot_rect: pygame.Rect = pygame.Rect(0, 0, 10, 10)
        self.action_button_rect: pygame.Rect = pygame.Rect(0, 0, 10, 10)
        super().__init__(
            station_id=station_id,
            slot_type="batch_pot",
            rect=rect,
            game_mgr=game_mgr,
        )

    @property
    def main_slot(self) -> StationSlot:
        if not self.slots:
            self.slots.append(StationSlot(slot_index=0, can_burn=False))
        return self.slots[0]

    @property
    def state(self) -> str:
        return self.main_slot.state

    @state.setter
    def state(self, val: str) -> None:
        self.main_slot.state = str(val)

    @property
    def remaining_servings(self) -> int:
        return int(self.main_slot.servings)

    @remaining_servings.setter
    def remaining_servings(self, val: int) -> None:
        self.main_slot.servings = max(0, int(val))
        if self.main_slot.servings <= 0 and self.main_slot.state == STATE_READY:
            self.main_slot.reset()

    @property
    def max_servings(self) -> int:
        if self.game_mgr and hasattr(self.game_mgr, "get_batch_servings"):
            return max(1, int(self.game_mgr.get_batch_servings()))
        return config.BASE_BATCH_SERVINGS

    def _on_station_changed(self) -> None:
        base_recipes = get_recipes_by_station(self.station_id, base_only=True)
        if base_recipes:
            self.base_recipe_id = str(base_recipes[0]["id"])
        else:
            self.base_recipe_id = "tteokbokki_plain"

    def _rebuild_layout(self) -> None:
        super()._rebuild_layout()
        r = self.rect
        pad = 10
        pot_top = r.y + 42
        btn_h = 62
        pot_h = max(130, r.height - 52 - btn_h - pad)

        self.pot_rect = pygame.Rect(r.x + pad, pot_top, r.width - pad * 2, pot_h)
        if self.slots:
            self.slots[0].rect = self.pot_rect.copy()
            self.slots[0].can_burn = False

        self.action_button_rect = pygame.Rect(
            r.x + pad,
            r.bottom - btn_h - 8,
            r.width - pad * 2,
            btn_h,
        )

    def start_batch_cooking(self) -> Dict[str, Any]:
        """대량 조리를 시작한다."""
        slot = self.main_slot
        total_servings = self.max_servings
        cook_t = self.get_cook_time(self.base_recipe_id)
        slot.start_cooking(
            recipe_id=self.base_recipe_id,
            cook_time=cook_t,
            burn_time=999.0,
            can_burn=False,
            servings=total_servings,
        )
        return {
            "action": "start_cook",
            "station": self.station_id,
            "slot_type": self.slot_type,
            "recipe_id": self.base_recipe_id,
            "servings": total_servings,
        }

    def instant_finish_all(self) -> int:
        """조리 중인 대량 팬을 즉시 완성하여 최대 인분을 채운다 (켄지 액티브 스킬 연동용)."""
        slot = self.main_slot
        if slot.state == STATE_COOKING:
            slot.max_servings = self.max_servings
            slot.instant_finish()
            return 1
        return 0

    def update(self, dt: float) -> None:
        slot = self.main_slot
        slot.can_burn = False
        prev_state = slot.state
        slot.update(dt)
        if prev_state == STATE_COOKING and slot.state == STATE_READY:
            slot.max_servings = self.max_servings
            slot.servings = slot.max_servings

    def handle_click(
        self,
        pos: Tuple[int, int],
        assembly_tray: Any = None,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        대량 조리 팬 클릭 인터랙션을 처리한다.
        - IDLE 상태에서 클릭 시: N인분 대량 조리 시작.
        - READY 상태에서 클릭 시:
          1) assembly_tray에 빈 자리가 있으면 1인분을 덜어 Dish(base_recipe_id)로 전달.
          2) 트레이가 꽉 찼고 기본 메뉴 주문 손님이 있으면 auto_serve_cb로 즉시 자동 서빙.
          3) remaining_servings가 0이 되면 IDLE 상태로 전환.
        """
        self._ensure_layout()
        if not self.rect.collidepoint(pos):
            return None

        if not (self.pot_rect.collidepoint(pos) or self.action_button_rect.collidepoint(pos)):
            return None

        slot = self.main_slot
        if slot.state == STATE_IDLE:
            return self.start_batch_cooking()

        if slot.state == STATE_COOKING:
            return {
                "action": "cooking_in_progress",
                "station": self.station_id,
                "recipe_id": self.base_recipe_id,
                "progress": slot.progress,
            }

        if slot.state == STATE_READY and self.remaining_servings > 0:
            # 1순위: 조립 트레이에 빈 슬롯이 있으면 1인분 전달
            if assembly_tray is not None and hasattr(assembly_tray, "add_dish"):
                dish = Dish(self.base_recipe_id)
                if assembly_tray.add_dish(dish):
                    self.remaining_servings -= 1
                    return {
                        "action": "moved_to_tray",
                        "station": self.station_id,
                        "recipe_id": self.base_recipe_id,
                        "dish": dish,
                        "remaining_servings": self.remaining_servings,
                    }

            # 2순위: 트레이가 가득 찼거나 없을 때 기본 메뉴 주문 손님에게 즉시 자동 서빙
            served, serve_res = invoke_auto_serve(
                auto_serve_cb,
                self.base_recipe_id,
                self.pot_rect.center,
            )
            if served:
                self.remaining_servings -= 1
                return {
                    "action": "auto_served",
                    "station": self.station_id,
                    "recipe_id": self.base_recipe_id,
                    "remaining_servings": self.remaining_servings,
                    "serve_result": serve_res,
                }

            return {
                "action": "tray_full",
                "station": self.station_id,
                "recipe_id": self.base_recipe_id,
                "remaining_servings": self.remaining_servings,
                "message": "조립 트레이가 가득 찼습니다!",
            }

        return None

    def draw(
        self,
        surface: pygame.Surface,
        time_tick: Any = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        t = float(time_tick) if isinstance(time_tick, (int, float)) else 0.0
        self.draw_panel_frame(surface, subtitle=f"{self.max_servings}인분 팬")

        slot = self.main_slot
        r = self.pot_rect
        if slot.state == STATE_IDLE:
            bg_col = (36, 32, 44)
            border_col = (90, 86, 110)
        elif slot.state == STATE_COOKING:
            bg_col = (62, 42, 30)
            border_col = config.GAUGE_COOKING
        else:
            bg_col = (34, 58, 42)
            border_col = config.GAUGE_READY

        pygame.draw.rect(surface, bg_col, r, border_radius=10)
        pygame.draw.rect(surface, border_col, r, width=2, border_radius=10)

        font_md = config.get_font(14, bold=True)
        font_sm = config.get_font(12, bold=True)
        font_xs = config.get_font(11, bold=False)

        if slot.state == STATE_IDLE:
            draw_food_icon(surface, (r.centerx, r.centery - 14), self.base_recipe_id, size=48, burnt=False)
            lbl = font_sm.render("비어 있음 (클릭하여 조리)", True, config.TEXT_SECONDARY)
            surface.blit(lbl, (r.centerx - lbl.get_width() // 2, r.bottom - 32))

        elif slot.state == STATE_COOKING:
            draw_food_icon(surface, (r.centerx, r.centery - 18), self.base_recipe_id, size=54, burnt=False)
            gauge_rect = pygame.Rect(r.x + 12, r.bottom - 22, r.width - 24, 12)
            pygame.draw.rect(surface, config.GAUGE_BG, gauge_rect, border_radius=6)
            fill_w = int((gauge_rect.width - 4) * slot.progress)
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    config.GAUGE_COOKING,
                    (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                    border_radius=4,
                )
            pygame.draw.rect(surface, config.GAUGE_BORDER, gauge_rect, width=1, border_radius=6)
            st_surf = font_sm.render(f"대량 조리중... ({int(slot.progress * 100)}%)", True, config.GAUGE_COOKING)
            surface.blit(st_surf, (r.centerx - st_surf.get_width() // 2, gauge_rect.top - 18))

        elif slot.state == STATE_READY:
            # 남은 인분 수에 비례해 음식 아이콘들을 풍성하게 배치
            rem = self.remaining_servings
            positions = [
                (r.centerx - 32, r.centery - 22),
                (r.centerx + 32, r.centery - 22),
                (r.centerx, r.centery - 6),
                (r.centerx - 26, r.centery + 8),
                (r.centerx + 26, r.centery + 8),
            ]
            for i in range(min(rem, len(positions))):
                draw_food_icon(surface, positions[i], self.base_recipe_id, size=44, burnt=False)

            badge_surf = font_md.render(f"보온중: {rem}/{self.max_servings} 인분", True, config.GAUGE_READY)
            surface.blit(badge_surf, (r.centerx - badge_surf.get_width() // 2, r.bottom - 38))
            sub_surf = font_xs.render("타지 않음 · 클릭 시 1인분 덜기", True, config.CREAM)
            surface.blit(sub_surf, (r.centerx - sub_surf.get_width() // 2, r.bottom - 19))

        # 하단 액션 버튼 렌더링
        rec = RECIPES.get(self.base_recipe_id)
        base_name = str(rec["name"]) if rec else self.base_recipe_id

        if slot.state == STATE_IDLE:
            btn_col = config.UI_BUTTON_ACTIVE
            btn_title = f"{base_name} {self.max_servings}인분 조리"
            btn_sub = "클릭하여 대량 조리 시작"
        elif slot.state == STATE_COOKING:
            btn_col = config.UI_DISABLED
            btn_title = "철판 조리 진행 중..."
            btn_sub = "잠시만 기다려 주세요"
        else:
            btn_col = (44, 138, 76)
            btn_title = f"1인분 덜기 (남은 {self.remaining_servings}인분)"
            btn_sub = "조립 트레이로 전달 / 즉시 서빙"

        pygame.draw.rect(surface, btn_col, self.action_button_rect, border_radius=8)
        pygame.draw.rect(surface, config.UI_HIGHLIGHT, self.action_button_rect, width=2, border_radius=8)

        t_surf = font_sm.render(btn_title, True, config.TEXT_PRIMARY)
        s_surf = font_xs.render(btn_sub, True, config.CREAM)
        surface.blit(
            t_surf,
            (self.action_button_rect.centerx - t_surf.get_width() // 2, self.action_button_rect.y + 11),
        )
        surface.blit(
            s_surf,
            (self.action_button_rect.centerx - s_surf.get_width() // 2, self.action_button_rect.y + 33),
        )
