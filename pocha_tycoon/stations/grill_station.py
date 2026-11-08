"""
stations/grill_station.py
직화 닭꼬치 / 야키토리 / 타코 그릴 / 대왕 지파이 등 그릴·튀김형 스테이션 모듈.
- 2~4개의 그릴 슬롯 보유
- 빈 슬롯 또는 하단 [재료 올리기] 버튼 클릭 시 베이스 메뉴 조리 시작
- 완성(READY) 슬롯 클릭 시 조립 트레이(AssemblyTray)로 Dish 이동 우선,
  트레이가 가득 찼을 때 베이스 메뉴 자체를 주문한 손님이 있으면 즉시 자동 서빙!
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple
import pygame

import config
from core.art_renderer import draw_food_icon
from data.recipes import RECIPES, get_recipes_by_station
from entities.dish import Dish
from stations.base_station import (
    STATE_BURNT,
    STATE_COOKING,
    STATE_IDLE,
    STATE_READY,
    BaseStation,
    invoke_auto_serve,
)


class GrillStation(BaseStation):
    """
    그릴/튀김 스테이션 (slot_type = 'grill').
    베이스 메뉴를 구워 조립 트레이(AssemblyTray)로 전달하거나 즉시 서빙한다.
    """

    DEFAULT_RECT: Tuple[int, int, int, int] = (248, 355, 214, 352)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        station_id, rect, game_mgr = self._parse_init_args(
            default_slot_type="grill",
            default_station_id="kr_skewer_grill",
            default_rect=self.DEFAULT_RECT,
            args=args,
            kwargs=kwargs,
        )
        self.base_recipe_id: str = "skewer_plain"
        self.cook_button_rect: pygame.Rect = pygame.Rect(0, 0, 10, 10)
        super().__init__(
            station_id=station_id,
            slot_type="grill",
            rect=rect,
            game_mgr=game_mgr,
        )

    def _on_station_changed(self) -> None:
        base_recipes = get_recipes_by_station(self.station_id, base_only=True)
        if base_recipes:
            self.base_recipe_id = str(base_recipes[0]["id"])
        else:
            self.base_recipe_id = "skewer_plain"

    def _rebuild_layout(self) -> None:
        super()._rebuild_layout()
        r = self.rect
        is_giant = r.height >= 500
        slot_area_top = r.y + (68 if is_giant else 42)
        btn_h = 114 if is_giant else 60
        btn_area_h = (btn_h + 18) if is_giant else 74
        slot_area_h = max(120, r.height - (74 if is_giant else 48) - btn_area_h)

        count = len(self.slots)
        pad = 12 if is_giant else 8
        cols = 2
        rows = 1 if count <= 2 else 2
        cell_w = (r.width - pad * (cols + 1)) // cols
        cell_h = (slot_area_h - pad * (rows + 1)) // rows

        for idx, slot in enumerate(self.slots):
            col = idx % cols
            row = idx // cols
            sx = r.x + pad + col * (cell_w + pad)
            sy = slot_area_top + pad + row * (cell_h + pad)
            slot.rect = pygame.Rect(sx, sy, cell_w, cell_h)

        self.cook_button_rect = pygame.Rect(
            r.x + pad,
            r.bottom - btn_h - (10 if is_giant else 8),
            r.width - pad * 2,
            btn_h,
        )

    def _start_slot_cooking(self, slot_idx: int) -> Dict[str, Any]:
        slot = self.slots[slot_idx]
        cook_t = self.get_cook_time(self.base_recipe_id)
        burn_t = self.get_burn_time(self.base_recipe_id)
        slot.start_cooking(
            recipe_id=self.base_recipe_id,
            cook_time=cook_t,
            burn_time=burn_t,
            can_burn=True,
        )
        return {
            "action": "start_cook",
            "station": self.station_id,
            "slot_type": self.slot_type,
            "slot_index": slot_idx,
            "recipe_id": self.base_recipe_id,
        }

    def handle_click(
        self,
        pos: Tuple[int, int],
        assembly_tray: Any = None,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        그릴 스테이션 클릭 인터랙션을 처리한다.
        - 하단 [재료 올리기] 버튼 클릭: 첫 번째 빈 슬롯에서 조리 시작.
        - IDLE 슬롯 클릭: 해당 슬롯 조리 시작.
        - READY 슬롯 클릭:
          1) assembly_tray에 빈 자리가 있으면 Dish(base_recipe_id)를 트레이로 이동.
          2) 트레이가 가득 찼는데 베이스 메뉴 자체를 원하는 손님이 있으면 auto_serve_cb로 즉시 서빙.
        - BURNT 슬롯 클릭: 탄 음식 폐기.
        """
        self._ensure_layout()
        if not self.rect.collidepoint(pos):
            return None

        # 1. 하단 [재료 올리기] 버튼 확인
        if self.cook_button_rect.collidepoint(pos):
            for s_idx, slot in enumerate(self.slots):
                if slot.state == STATE_IDLE:
                    return self._start_slot_cooking(s_idx)
            return {
                "action": "slots_full",
                "station": self.station_id,
                "recipe_id": self.base_recipe_id,
                "message": "모든 그릴 슬롯이 조리 중입니다.",
            }

        # 2. 개별 그릴 슬롯 확인
        for s_idx, slot in enumerate(self.slots):
            if not slot.rect.collidepoint(pos):
                continue

            if slot.state == STATE_IDLE:
                return self._start_slot_cooking(s_idx)

            if slot.state == STATE_COOKING:
                return {
                    "action": "cooking_in_progress",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "recipe_id": slot.recipe_id,
                    "progress": slot.progress,
                }

            if slot.state == STATE_READY and slot.recipe_id:
                ready_recipe = slot.recipe_id
                # 1순위: 조립 트레이에 빈 자리가 있으면 트레이로 전달
                if assembly_tray is not None and hasattr(assembly_tray, "add_dish"):
                    dish = Dish(ready_recipe)
                    if assembly_tray.add_dish(dish):
                        slot.reset()
                        return {
                            "action": "moved_to_tray",
                            "station": self.station_id,
                            "slot_index": s_idx,
                            "recipe_id": ready_recipe,
                            "dish": dish,
                        }

                # 2순위: 트레이가 꽉 찼거나 없을 때 베이스 메뉴 주문 손님에게 즉시 자동 서빙
                served, serve_res = invoke_auto_serve(
                    auto_serve_cb,
                    ready_recipe,
                    slot.rect.center,
                )
                if served:
                    slot.reset()
                    return {
                        "action": "auto_served",
                        "station": self.station_id,
                        "slot_index": s_idx,
                        "recipe_id": ready_recipe,
                        "serve_result": serve_res,
                    }

                return {
                    "action": "tray_full",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "recipe_id": ready_recipe,
                    "message": "조립 트레이가 가득 찼습니다!",
                }

            if slot.state == STATE_BURNT:
                burnt_recipe = slot.recipe_id
                slot.reset()
                return {
                    "action": "trash_burnt",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "recipe_id": burnt_recipe,
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
        is_mobile = bool(
            getattr(config, "is_mobile_ui", lambda: config.WINDOW_HEIGHT > config.WINDOW_WIDTH)()
        )
        is_giant = self.rect.height >= 500
        self.draw_panel_frame(surface, subtitle=f"{len(self.slots)}구")

        for slot in self.slots:
            slot.draw_slot_box(surface, time_tick=t, empty_label="➕ 터치 조리")

        # 하단 [재료 올리기] 버튼 렌더링
        has_idle = any(s.state == STATE_IDLE for s in self.slots)
        btn_col = (235, 118, 32) if has_idle else (62, 58, 78)
        border_col = config.GOLD if has_idle else config.UI_BORDER
        pygame.draw.rect(surface, btn_col, self.cook_button_rect, border_radius=12 if is_giant else 10)
        pygame.draw.rect(surface, border_col, self.cook_button_rect, width=3 if has_idle else 2, border_radius=12 if is_giant else 10)

        rec = RECIPES.get(self.base_recipe_id)
        base_name = str(rec["name"]) if rec else self.base_recipe_id
        font_main = config.get_font(22 if is_giant else 15, bold=True)

        if is_giant:
            draw_food_icon(surface, (self.cook_button_rect.x + 56, self.cook_button_rect.centery), self.base_recipe_id, size=68, burnt=False)
            main_str = f"🔥 {base_name} 올리기"
            lbl_main = font_main.render(main_str, True, config.WHITE)
            lbl_sub = config.get_font(16, bold=True).render(
                "완성 시 조립 트레이 이동 또는 즉시 서빙",
                True,
                config.GOLD if has_idle else config.TEXT_SECONDARY,
            )
            surface.blit(lbl_main, (self.cook_button_rect.x + 104, self.cook_button_rect.y + 22))
            surface.blit(lbl_sub, (self.cook_button_rect.x + 104, self.cook_button_rect.y + 64))
            return

        if is_mobile:
            draw_food_icon(surface, (self.cook_button_rect.x + 32, self.cook_button_rect.centery), self.base_recipe_id, size=44, burnt=False)
            max_w = self.cook_button_rect.width - 62
            for f_sz in (16, 15, 14, 13):
                font_main = config.get_font(f_sz, bold=True)
                if font_main.size(base_name)[0] <= max_w:
                    break
            lbl_main = font_main.render(base_name, True, config.WHITE)
            surface.blit(
                lbl_main,
                (
                    self.cook_button_rect.x + 58,
                    self.cook_button_rect.centery - lbl_main.get_height() // 2,
                ),
            )
            return

        icon_pos = (self.cook_button_rect.x + 28, self.cook_button_rect.centery)
        draw_food_icon(surface, icon_pos, self.base_recipe_id, size=40, burnt=False)

        font_sub = config.get_font(12, bold=True)

        main_str = f"🔥 {base_name} 올리기"
        max_w = self.cook_button_rect.width - 56
        for f_sz in (15, 14, 13, 12):
            font_main = config.get_font(f_sz, bold=True)
            if font_main.size(main_str)[0] <= max_w:
                break

        lbl_main = font_main.render(main_str, True, config.WHITE)
        lbl_sub = font_sub.render("완성 후 조립 트레이로 이동", True, config.GOLD if has_idle else config.TEXT_SECONDARY)
        surface.blit(lbl_main, (self.cook_button_rect.x + 52, self.cook_button_rect.y + 8))
        surface.blit(lbl_sub, (self.cook_button_rect.x + 52, self.cook_button_rect.y + 33))
