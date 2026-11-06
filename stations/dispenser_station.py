"""
stations/dispenser_station.py
어묵국물&식혜 / 생맥주&라무네 / 마가리타&콜라 / 버블티&망고스무디 등
자동 충전 및 원클릭 즉시 서빙 음료 디스펜서 스테이션 모듈.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import pygame

import config
from core.art_renderer import draw_food_icon
from data.recipes import RECIPES, get_recipes_by_station
from stations.base_station import (
    STATE_COOKING,
    STATE_IDLE,
    STATE_READY,
    BaseStation,
    invoke_auto_serve,
)


class DispenserStation(BaseStation):
    """
    음료 디스펜서 스테이션 (slot_type = 'dispenser').
    - 해당 기구의 음료 2종 노즐 슬롯 보유 (업그레이드 시 2~4슬롯).
    - 비어 있으면(IDLE) 자동으로 충전(COOKING -> READY, 타지 않음).
    - READY 노즐 클릭 시 auto_serve_cb(recipe_id, slot_center)를 호출해
      해당 음료를 기다리는 손님에게 원클릭 즉시 자동 서빙 후 재충전 시작!
    - serve_all_waiting_drinks(auto_serve_cb) -> int: 메이링 액티브 스킬 연동용.
    """

    DEFAULT_RECT: Tuple[int, int, int, int] = (1042, 355, 224, 352)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        station_id, rect, game_mgr = self._parse_init_args(
            default_slot_type="dispenser",
            default_station_id="kr_odeng_dispenser",
            default_rect=self.DEFAULT_RECT,
            args=args,
            kwargs=kwargs,
        )
        self.drink_recipes: List[str] = []
        super().__init__(
            station_id=station_id,
            slot_type="dispenser",
            rect=rect,
            game_mgr=game_mgr,
        )
        self._ensure_auto_refill()

    def _on_station_changed(self) -> None:
        drinks = get_recipes_by_station(self.station_id, base_only=True)
        if not drinks:
            drinks = get_recipes_by_station("kr_odeng_dispenser", base_only=True)
        self.drink_recipes = [str(r["id"]) for r in drinks]
        # 기구 변경 시 기존 슬롯의 음료 종류도 새 기구에 맞게 갱신
        for idx, slot in enumerate(self.slots):
            slot.can_burn = False
            expected_rid = self._get_slot_drink_id(idx)
            if slot.recipe_id not in self.drink_recipes:
                slot.start_cooking(
                    recipe_id=expected_rid,
                    cook_time=self.get_cook_time(expected_rid),
                    burn_time=999.0,
                    can_burn=False,
                )

    def _get_slot_drink_id(self, slot_index: int) -> str:
        if not self.drink_recipes:
            return "odeng_soup"
        return self.drink_recipes[slot_index % len(self.drink_recipes)]

    def sync_slots_with_manager(self) -> None:
        super().sync_slots_with_manager()
        self._ensure_auto_refill()

    def _ensure_auto_refill(self) -> None:
        """비어 있는(IDLE) 노즐 슬롯이 있으면 자동으로 충전(COOKING)을 시작한다."""
        for idx, slot in enumerate(self.slots):
            slot.can_burn = False
            drink_id = self._get_slot_drink_id(idx)
            if slot.state == STATE_IDLE or slot.recipe_id is None:
                slot.start_cooking(
                    recipe_id=drink_id,
                    cook_time=self.get_cook_time(drink_id),
                    burn_time=999.0,
                    can_burn=False,
                )

    def _rebuild_layout(self) -> None:
        super()._rebuild_layout()
        r = self.rect
        pad = 8
        top_y = r.y + 42
        usable_h = r.height - 52

        count = max(1, len(self.slots))
        if count <= 2:
            cols = 2
            rows = 1
            cell_w = (r.width - pad * (cols + 1)) // cols
            cell_h = min(210, usable_h - pad * 2)
        else:
            cols = 2
            rows = 2
            cell_w = (r.width - pad * (cols + 1)) // cols
            cell_h = (usable_h - pad * (rows + 1)) // rows

        for idx, slot in enumerate(self.slots):
            col = idx % cols
            row = idx // cols
            sx = r.x + pad + col * (cell_w + pad)
            sy = top_y + pad + row * (cell_h + pad)
            slot.rect = pygame.Rect(sx, sy, cell_w, cell_h)
            slot.can_burn = False

    def update(self, dt: float) -> None:
        """노즐 충전 타이머를 진행하고 빈 슬롯은 자동으로 재충전을 시작한다."""
        self._ensure_auto_refill()
        for slot in self.slots:
            slot.can_burn = False
            slot.update(dt)

    def serve_all_waiting_drinks(
        self,
        auto_serve_cb: Optional[Callable[..., Any]],
    ) -> int:
        """
        메이링 액티브 스킬('야시장 풀코스') 발동 시 호출되어
        현재 대기 손님들이 원하는 모든 음료 주문을 즉시 서빙 처리하고 서빙 건수를 반환한다.
        """
        if auto_serve_cb is None:
            return 0

        served_total = 0
        # 모든 노즐 슬롯도 즉시 READY 상태로 충전 완료
        for slot in self.slots:
            if slot.state == STATE_COOKING:
                slot.instant_finish()

        # 현재 기구의 음료 레시피들에 대해 대기 중인 손님들에게 모두 서빙 시도
        for drink_id in self.drink_recipes:
            for _ in range(8):
                served, _ = invoke_auto_serve(auto_serve_cb, drink_id, self.rect.center)
                if served:
                    served_total += 1
                else:
                    break

        return served_total

    def handle_click(
        self,
        pos: Tuple[int, int],
        assembly_tray: Any = None,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        READY 상태인 음료 노즐 클릭 시 해당 음료를 기다리는 손님에게 원클릭 즉시 자동 서빙하고
        즉시 재충전(COOKING)을 시작한다.
        """
        self._ensure_layout()
        if not self.rect.collidepoint(pos):
            return None

        for s_idx, slot in enumerate(self.slots):
            if not slot.rect.collidepoint(pos):
                continue

            drink_id = slot.recipe_id or self._get_slot_drink_id(s_idx)

            if slot.state == STATE_COOKING:
                return {
                    "action": "refilling",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "recipe_id": drink_id,
                    "progress": slot.progress,
                }

            if slot.state == STATE_READY:
                served, serve_res = invoke_auto_serve(
                    auto_serve_cb,
                    drink_id,
                    slot.rect.center,
                )
                if served:
                    # 서빙 완료 즉시 재충전 시작
                    slot.start_cooking(
                        recipe_id=drink_id,
                        cook_time=self.get_cook_time(drink_id),
                        burn_time=999.0,
                        can_burn=False,
                    )
                    return {
                        "action": "auto_served",
                        "station": self.station_id,
                        "slot_index": s_idx,
                        "recipe_id": drink_id,
                        "serve_result": serve_res,
                    }

                return {
                    "action": "no_customer",
                    "station": self.station_id,
                    "slot_index": s_idx,
                    "recipe_id": drink_id,
                    "message": "해당 음료를 주문한 손님이 없습니다.",
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
        self.draw_panel_frame(surface, subtitle=f"{len(self.slots)}노즐")

        font_title = config.get_font(15, bold=True)
        font_status = config.get_font(14, bold=True)

        short_drink_map = {
            "어묵국물 (오뎅탕)": "어묵국물",
            "전통 살얼음 식혜": "살얼음 식혜",
            "구슬 사이다 (라무네)": "라무네 사이다",
            "타피오카 버블밀크티": "버블밀크티",
        }

        for idx, slot in enumerate(self.slots):
            r = slot.rect
            drink_id = slot.recipe_id or self._get_slot_drink_id(idx)
            rec = RECIPES.get(drink_id)
            raw_name = str(rec["name"]) if rec else drink_id
            drink_name = short_drink_map.get(raw_name, raw_name)

            is_ready = slot.state == STATE_READY
            bg_col = (28, 76, 62) if is_ready else (38, 48, 74)
            border_col = config.NEON_GREEN if is_ready else config.NEON_CYAN

            pygame.draw.rect(surface, bg_col, r, border_radius=10)
            pygame.draw.rect(surface, border_col, r, width=3 if is_ready else 2, border_radius=10)

            # 음료 메뉴명 상단 고대비 필 배지
            active_name_f = font_title
            for f_sz in (14, 13, 12, 11):
                if active_name_f.size(drink_name)[0] <= r.width - 10:
                    break
                active_name_f = config.get_font(f_sz, bold=True)
            name_pill = pygame.Rect(r.x + 4, r.y + 5, r.width - 8, 24)
            pygame.draw.rect(surface, (18, 22, 34), name_pill, border_radius=6)
            name_surf = active_name_f.render(drink_name, True, config.GOLD if is_ready else config.WHITE)
            surface.blit(
                name_surf,
                (name_pill.centerx - name_surf.get_width() // 2, name_pill.centery - name_surf.get_height() // 2),
            )

            # 음료 대형 아이콘
            icon_size = min(60, max(38, min(r.width, r.height) - 44))
            draw_food_icon(surface, (r.centerx, r.centery - 2), drink_id, size=icon_size, burnt=False)

            # 하단 14px 충전 게이지 및 고대비 상태 배지
            gauge_rect = pygame.Rect(r.x + 6, r.bottom - 18, r.width - 12, 14)
            pygame.draw.rect(surface, (18, 16, 26), gauge_rect, border_radius=6)
            fill_w = int((gauge_rect.width - 4) * slot.progress)
            bar_col = config.NEON_GREEN if is_ready else config.NEON_CYAN
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    bar_col,
                    (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                    border_radius=4,
                )
            pygame.draw.rect(surface, (205, 202, 224), gauge_rect, width=2, border_radius=6)

            status_txt = "✨ 즉시 서빙!" if is_ready else "💧 충전중..."
            status_col = config.NEON_GREEN if is_ready else config.NEON_CYAN
            st_surf = font_status.render(status_txt, True, status_col)
            if st_surf.get_width() > r.width - 8:
                st_surf = config.get_font(12, bold=True).render(status_txt, True, status_col)
            pill_w = min(r.width - 6, st_surf.get_width() + 10)
            st_pill = pygame.Rect(r.centerx - pill_w // 2, gauge_rect.top - 22, pill_w, 20)
            pygame.draw.rect(surface, (16, 28, 24) if is_ready else (18, 24, 38), st_pill, border_radius=5)
            pygame.draw.rect(surface, status_col, st_pill, width=1, border_radius=5)
            surface.blit(st_surf, (st_pill.centerx - st_surf.get_width() // 2, st_pill.centery - st_surf.get_height() // 2))
