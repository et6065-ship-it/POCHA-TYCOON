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
from core.art_renderer import draw_bungeo_tycoon_mold_slot, draw_food_icon
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
            needs_flip=True,
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
        『붕어빵 타이쿤』 3단계 몰드 스테이션 클릭 인터랙션을 처리한다.
        1) 하단 레시피 버튼 클릭: 손에 쥘 속재료(팥/슈크림 등) 선택.
        2) 위쪽 몰드 슬롯 클릭:
           - IDLE: 현재 선택된 속재료+반죽을 그 칸에 직접 붓기(needs_flip=True).
           - COOKING: 앞면이 익었으면(can_flip_now) 반죽틀 뒤집기(flip_mold).
           - READY: auto_serve_cb 우선 호출하여 자동 서빙 -> 없으면 assembly_tray에 보관.
           - BURNT: 탄 음식 폐기.
        """
        self._ensure_layout()
        if not self.rect.collidepoint(pos):
            return None

        # 1. 하단 속재료 선택 버튼 확인
        for idx, (btn_rect, rid) in enumerate(self.recipe_buttons):
            if btn_rect.collidepoint(pos):
                self.selected_recipe_index = idx
                sel_s = getattr(self, "selected_slot_index", None)
                if sel_s is not None and 0 <= sel_s < len(self.slots) and self.slots[sel_s].state == STATE_IDLE:
                    self.selected_slot_index = None
                    return self._start_slot_cooking(sel_s, rid)
                rec = RECIPES.get(rid)
                r_name = str(rec["name"]) if rec else rid
                return {
                    "action": "select_recipe",
                    "station": self.station_id,
                    "recipe_id": rid,
                    "message": f"🥣 [{r_name}] 속 선택! 위쪽 빈 틀(1~{len(self.slots)})을 터치해 부으세요!",
                }

        # 2. 몰드 슬롯 클릭 확인
        for s_idx, slot in enumerate(self.slots):
            if not slot.rect.collidepoint(pos):
                continue

            if slot.state == STATE_IDLE:
                # 『붕어빵 타이쿤』 1단계: 빈 틀을 직접 터치하면 현재 선택한 속재료+반죽을 그 칸에 붓는다!
                return self._start_slot_cooking(s_idx, self.selected_recipe_id)

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
                # 『붕어빵 타이쿤』 2단계: 앞면이 익었을 때 터치하면 반죽틀 뒤집기!
                if getattr(slot, "needs_flip", False) and not getattr(slot, "flipped", False):
                    if slot.can_flip_now:
                        slot.flip_mold()
                        return {
                            "action": "flip_mold",
                            "station": self.station_id,
                            "slot_index": s_idx,
                            "recipe_id": slot.recipe_id,
                        }
                    return {
                        "action": "too_early_flip",
                        "station": self.station_id,
                        "slot_index": s_idx,
                        "recipe_id": slot.recipe_id,
                        "message": "🥣 아직 앞면 생반죽이 익는 중입니다! [🔄 뒤집기!]가 뜨면 터치하세요!",
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
        self.draw_panel_frame(surface, subtitle=f"{len(self.slots)}구")

        sel_rec = RECIPES.get(self.selected_recipe_id)
        sel_nm = str(sel_rec["name"]) if sel_rec else "단팥"
        for s_idx, slot in enumerate(self.slots):
            is_target = getattr(self, "selected_slot_index", None) == s_idx and slot.state == STATE_IDLE
            rec = RECIPES.get(slot.recipe_id or "")
            r_nm = str(rec["name"]) if rec else ""
            draw_bungeo_tycoon_mold_slot(
                surface,
                slot.rect,
                s_idx,
                slot,
                recipe_name=r_nm,
                selected_recipe_name=sel_nm,
                is_targeted=is_target,
                time_tick=t,
            )

        # 하단 레시피 선택/투입 버튼 렌더링 (고시인성 15px 볼드 + 3px 하이라이트 보더 + 38px 아이콘)
        font_btn = config.get_font(15, bold=True)
        for idx, (btn_rect, rid) in enumerate(self.recipe_buttons):
            is_sel = idx == self.selected_recipe_index
            bg_col = (18, 128, 152) if is_sel else (54, 72, 116)
            border_col = config.NEON_CYAN if is_sel else (136, 152, 198)
            pygame.draw.rect(surface, bg_col, btn_rect, border_radius=10)
            pygame.draw.rect(surface, border_col, btn_rect, width=3 if is_sel else 2, border_radius=10)

            icon_pos = (btn_rect.centerx, btn_rect.y + 22)
            draw_food_icon(surface, icon_pos, rid, size=38, burnt=False)

            rec = RECIPES.get(rid)
            r_name = str(rec["name"]) if rec else rid
            lbl_str = f"✔ {r_name}" if is_sel else r_name
            active_f = font_btn
            for f_sz in (14, 13, 12, 11):
                if active_f.size(lbl_str)[0] <= btn_rect.width - 8:
                    break
                active_f = config.get_font(f_sz, bold=True)
            sh_surf = active_f.render(lbl_str, True, (18, 12, 24))
            txt_surf = active_f.render(lbl_str, True, config.WHITE)
            tx = btn_rect.centerx - txt_surf.get_width() // 2
            ty = btn_rect.bottom - 22
            surface.blit(sh_surf, (tx + 1, ty + 1))
            surface.blit(txt_surf, (tx, ty))
