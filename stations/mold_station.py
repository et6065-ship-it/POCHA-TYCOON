"""
stations/mold_station.py
붕어빵 틀 / 타코야키 판 / 퀘사디야 프레스 / 총좌빙 철판 등 몰드 구이형 스테이션 모듈.
- 속재료(레시피 2종) 선택 및 투입 버튼
- 2~4개의 몰드 슬롯 조리/익음/탐 판정
- 완성(READY) 슬롯 클릭 시 주문 손님에게 즉시 자동 서빙, 없으면 조립 트레이로 이동
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
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


class MoldStation(BaseStation):
    """
    몰드 구이형 스테이션 (slot_type = 'mold').
    2종의 완제품 메뉴(예: 팥 붕어빵 / 슈크림 붕어빵)를 구워내어 즉시 서빙하거나 트레이에 보관한다.
    """

    DEFAULT_RECT: Tuple[int, int, int, int] = (14, 355, 224, 352)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        station_id, rect, game_mgr = self._parse_init_args(
            default_slot_type="mold",
            default_station_id="kr_bungeoppang",
            default_rect=self.DEFAULT_RECT,
            args=args,
            kwargs=kwargs,
        )
        self.recipe_ids: List[str] = []
        self.selected_recipe_index: int = 0
        self.recipe_buttons: List[Tuple[pygame.Rect, str]] = []
        super().__init__(
            station_id=station_id,
            slot_type="mold",
            rect=rect,
            game_mgr=game_mgr,
        )

    @property
    def selected_recipe_id(self) -> str:
        """현재 선택된 속재료(레시피) ID를 반환한다."""
        if not self.recipe_ids:
            return "bungeoppang_redbean"
        idx = max(0, min(self.selected_recipe_index, len(self.recipe_ids) - 1))
        return self.recipe_ids[idx]

    @selected_recipe_id.setter
    def selected_recipe_id(self, recipe_id: str) -> None:
        if recipe_id in self.recipe_ids:
            self.selected_recipe_index = self.recipe_ids.index(recipe_id)

    def _on_station_changed(self) -> None:
        station_recipes = get_recipes_by_station(self.station_id, base_only=True)
        if not station_recipes:
            station_recipes = get_recipes_by_station("kr_bungeoppang", base_only=True)
        self.recipe_ids = [str(r["id"]) for r in station_recipes]
        if self.selected_recipe_index >= len(self.recipe_ids):
            self.selected_recipe_index = 0

    def _rebuild_layout(self) -> None:
        super()._rebuild_layout()
        r = self.rect
        slot_area_top = r.y + 42
        btn_area_h = 80
        slot_area_h = max(120, r.height - 48 - btn_area_h)

        count = len(self.slots)
        pad = 8
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

        # 하단 레시피 선택/투입 버튼 2종 배치
        self.recipe_buttons = []
        btn_cnt = max(1, len(self.recipe_ids))
        btn_w = (r.width - pad * (btn_cnt + 1)) // btn_cnt
        btn_h = 66
        btn_y = r.bottom - btn_h - 8
        for i, rid in enumerate(self.recipe_ids):
            bx = r.x + pad + i * (btn_w + pad)
            self.recipe_buttons.append((pygame.Rect(bx, btn_y, btn_w, btn_h), rid))

    def _start_slot_cooking(self, slot_idx: int, recipe_id: Optional[str] = None) -> Dict[str, Any]:
        slot = self.slots[slot_idx]
        target_recipe = recipe_id or self.selected_recipe_id
        cook_t = self.get_cook_time(target_recipe)
        burn_t = self.get_burn_time(target_recipe)
        slot.start_cooking(
            recipe_id=target_recipe,
            cook_time=cook_t,
            burn_time=burn_t,
            can_burn=True,
        )
        return {
            "action": "start_cook",
            "station": self.station_id,
            "slot_type": self.slot_type,
            "slot_index": slot_idx,
            "recipe_id": target_recipe,
        }

    def handle_click(
        self,
        pos: Tuple[int, int],
        assembly_tray: Any = None,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        몰드 스테이션 클릭 인터랙션을 처리한다.
        1) 하단 레시피 버튼 클릭: 해당 레시피 선택 + 빈 슬롯이 있으면 즉시 조리 시작.
        2) 슬롯 클릭:
           - IDLE: 투입 대상 슬롯으로 지정.
           - COOKING: 우측 상단 취소 배지(또는 버리기 모드) 시 폐기, 아니면 조리 중 피드백.
           - READY: auto_serve_cb 우선 호출하여 자동 서빙 -> 없으면 assembly_tray에 보관.
           - BURNT: 탄 음식 폐기.
        """
        self._ensure_layout()
        if not self.rect.collidepoint(pos):
            return None

        # 1. 하단 레시피 선택/투입 버튼 확인
        for idx, (btn_rect, rid) in enumerate(self.recipe_buttons):
            if btn_rect.collidepoint(pos):
                self.selected_recipe_index = idx
                sel_s = getattr(self, "selected_slot_index", None)
                if sel_s is not None and 0 <= sel_s < len(self.slots) and self.slots[sel_s].state == STATE_IDLE:
                    self.selected_slot_index = None
                    return self._start_slot_cooking(sel_s, rid)
                for s_idx, slot in enumerate(self.slots):
                    if slot.state == STATE_IDLE:
                        return self._start_slot_cooking(s_idx, rid)
                return {
                    "action": "select_recipe",
                    "station": self.station_id,
                    "recipe_id": rid,
                }

        # 2. 몰드 슬롯 클릭 확인
        for s_idx, slot in enumerate(self.slots):
            if not slot.rect.collidepoint(pos):
                continue

            if slot.state == STATE_IDLE:
                # 빈 틀을 터치했을 때 자동으로 팥(기본 맛)이 들어가지 않도록 차단하고, 해당 칸을 투입 대상 슬롯으로 지정!
                self.selected_slot_index = s_idx
                return {
                    "action": "select_target_slot",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "message": "👇 하단에서 넣을 속재료 버튼을 터치하세요!",
                }

            if slot.state == STATE_COOKING:
                cancel_badge = pygame.Rect(slot.rect.right - 28, slot.rect.y + 3, 25, 24)
                trash_active = bool(assembly_tray is not None and getattr(assembly_tray, "trash_mode", False))
                if cancel_badge.inflate(6, 6).collidepoint(pos) or trash_active:
                    old_rid = slot.recipe_id
                    slot.reset()
                    return {
                        "action": "trash_dish",
                        "station": self.station_id,
                        "slot_index": s_idx,
                        "recipe_id": old_rid,
                    }
                return {
                    "action": "cooking_in_progress",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "recipe_id": slot.recipe_id,
                    "progress": slot.progress,
                }

            if slot.state == STATE_READY and slot.recipe_id:
                ready_recipe = slot.recipe_id
                # 우선 해당 메뉴를 주문한 손님에게 즉시 자동 서빙 시도
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

                # 주문한 손님이 없으면 조립 트레이 빈 슬롯에 보관
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

                return {
                    "action": "tray_full",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "recipe_id": ready_recipe,
                    "message": "주문 손님이 없고 트레이가 가득 찼습니다!",
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
        self.draw_panel_frame(surface, subtitle=f"{len(self.slots)}구")

        for s_idx, slot in enumerate(self.slots):
            is_target = getattr(self, "selected_slot_index", None) == s_idx and slot.state == STATE_IDLE
            slot.draw_slot_box(
                surface,
                time_tick=t,
                empty_label="👇 맛 선택!" if is_target else "👇 하단 맛 선택",
            )
            if is_target:
                pygame.draw.rect(surface, config.NEON_CYAN, slot.rect, width=3, border_radius=10)
            elif slot.state == STATE_COOKING:
                cancel_badge = pygame.Rect(slot.rect.right - 25, slot.rect.y + 4, 21, 21)
                pygame.draw.rect(surface, (198, 42, 46), cancel_badge, border_radius=6)
                pygame.draw.rect(surface, config.WHITE, cancel_badge, width=1, border_radius=6)
                xt = config.get_font(12, bold=True).render("✕", True, config.WHITE)
                surface.blit(xt, xt.get_rect(center=cancel_badge.center))

        # 하단 레시피 선택/투입 버튼 렌더링
        font_btn = config.get_font(15, bold=True)
        for idx, (btn_rect, rid) in enumerate(self.recipe_buttons):
            is_sel = idx == self.selected_recipe_index
            bg_col = (235, 118, 32) if is_sel else (54, 72, 116)
            border_col = config.GOLD if is_sel else (136, 152, 198)
            pygame.draw.rect(surface, bg_col, btn_rect, border_radius=10)
            pygame.draw.rect(surface, border_col, btn_rect, width=3 if is_sel else 2, border_radius=10)

            icon_pos = (btn_rect.centerx, btn_rect.y + 22)
            draw_food_icon(surface, icon_pos, rid, size=40 if is_mobile else 38, burnt=False)

            rec = RECIPES.get(rid)
            r_name = str(rec["name"]) if rec else rid
            active_f = font_btn
            for f_sz in (14, 13, 12, 11):
                if active_f.size(r_name)[0] <= btn_rect.width - 8:
                    break
                active_f = config.get_font(f_sz, bold=True)
            sh_surf = active_f.render(r_name, True, (18, 12, 24))
            txt_surf = active_f.render(r_name, True, config.WHITE)
            tx = btn_rect.centerx - txt_surf.get_width() // 2
            ty = btn_rect.bottom - 22
            surface.blit(sh_surf, (tx + 1, ty + 1))
            surface.blit(txt_surf, (tx, ty))
