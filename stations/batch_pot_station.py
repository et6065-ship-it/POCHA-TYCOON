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
        is_mobile = bool(
            getattr(config, "is_mobile_ui", lambda: config.WINDOW_HEIGHT > config.WINDOW_WIDTH)()
        )
        self.draw_panel_frame(surface, subtitle=f"{self.max_servings}인분 팬")

        slot = self.main_slot
        r = self.pot_rect
        if slot.state == STATE_IDLE:
            bg_col = (40, 36, 56)
            border_col = (108, 100, 146)
            b_w = 2
        elif slot.state == STATE_COOKING:
            bg_col = (66, 44, 30)
            border_col = config.GAUGE_COOKING
            b_w = 3
        else:
            bg_col = (28, 68, 46)
            border_col = config.NEON_GREEN
            b_w = 3

        pygame.draw.rect(surface, bg_col, r, border_radius=12)
        pygame.draw.rect(surface, border_col, r, width=b_w, border_radius=12)

        if is_mobile:
            if slot.state == STATE_IDLE:
                draw_food_icon(surface, (r.centerx, r.centery - 10), self.base_recipe_id, size=56, burnt=False)
                plus_c = (r.centerx, r.bottom - 22)
                pygame.draw.circle(surface, (26, 22, 38), plus_c, 13)
                pygame.draw.circle(surface, config.GOLD, plus_c, 13, width=2)
                pygame.draw.line(surface, config.GOLD, (plus_c[0] - 6, plus_c[1]), (plus_c[0] + 6, plus_c[1]), 3)
                pygame.draw.line(surface, config.GOLD, (plus_c[0], plus_c[1] - 6), (plus_c[0], plus_c[1] + 6), 3)
            elif slot.state == STATE_COOKING:
                draw_food_icon(surface, (r.centerx, r.centery - 10), self.base_recipe_id, size=58, burnt=False)
                gauge_rect = pygame.Rect(r.x + 10, r.bottom - 20, r.width - 20, 14)
                pygame.draw.rect(surface, (18, 16, 26), gauge_rect, border_radius=7)
                fill_w = int((gauge_rect.width - 4) * slot.progress)
                if fill_w > 0:
                    pygame.draw.rect(
                        surface,
                        config.GAUGE_COOKING,
                        (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                        border_radius=5,
                    )
                pygame.draw.rect(surface, (205, 202, 224), gauge_rect, width=2, border_radius=7)
            else:
                rem = self.remaining_servings
                positions = [
                    (r.centerx - 34, r.centery - 20),
                    (r.centerx + 34, r.centery - 20),
                    (r.centerx, r.centery - 4),
                    (r.centerx - 28, r.centery + 12),
                    (r.centerx + 28, r.centery + 12),
                ]
                for i in range(min(rem, len(positions))):
                    draw_food_icon(surface, positions[i], self.base_recipe_id, size=48, burnt=False)

                # 하단 인분 수 그래픽 도트 표시 (문구 생략)
                tot = max(1, self.max_servings)
                dot_spacing = min(22, (r.width - 24) // max(1, tot))
                start_x = r.centerx - ((tot - 1) * dot_spacing) // 2
                dot_y = r.bottom - 16
                for i in range(tot):
                    dx = start_x + i * dot_spacing
                    filled = i < rem
                    pygame.draw.circle(surface, config.NEON_GREEN if filled else (24, 34, 28), (dx, dot_y), 6)
                    pygame.draw.circle(surface, config.WHITE if filled else (92, 112, 98), (dx, dot_y), 6, width=1)

            # 모바일 하단 대형 아이콘 버튼 (문구 생략)
            if slot.state == STATE_IDLE:
                btn_col = (235, 118, 32)
            elif slot.state == STATE_COOKING:
                btn_col = (64, 58, 78)
            else:
                btn_col = (42, 152, 82)
            pygame.draw.rect(surface, btn_col, self.action_button_rect, border_radius=10)
            pygame.draw.rect(surface, config.GOLD, self.action_button_rect, width=3, border_radius=10)
            btn_icon_sz = min(54, max(46, min(self.action_button_rect.width, self.action_button_rect.height) - 8))
            draw_food_icon(surface, self.action_button_rect.center, self.base_recipe_id, size=btn_icon_sz, burnt=False)
            return

        font_lg = config.get_font(15, bold=True)
        font_md = config.get_font(14, bold=True)
        font_sm = config.get_font(12, bold=True)

        if slot.state == STATE_IDLE:
            draw_food_icon(surface, (r.centerx, r.centery - 18), self.base_recipe_id, size=56, burnt=False)
            lbl = font_md.render("➕ 터치하여 대량 조리", True, config.GOLD)
            pill_r = pygame.Rect(r.x + 8, r.bottom - 38, r.width - 16, 28)
            pygame.draw.rect(surface, (24, 20, 36), pill_r, border_radius=8)
            pygame.draw.rect(surface, config.GOLD, pill_r, width=1, border_radius=8)
            surface.blit(lbl, (pill_r.centerx - lbl.get_width() // 2, pill_r.centery - lbl.get_height() // 2))

        elif slot.state == STATE_COOKING:
            draw_food_icon(surface, (r.centerx, r.centery - 22), self.base_recipe_id, size=62, burnt=False)
            gauge_rect = pygame.Rect(r.x + 10, r.bottom - 22, r.width - 20, 15)
            pygame.draw.rect(surface, (18, 16, 26), gauge_rect, border_radius=7)
            fill_w = int((gauge_rect.width - 4) * slot.progress)
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    config.GAUGE_COOKING,
                    (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                    border_radius=5,
                )
            pygame.draw.rect(surface, (205, 202, 224), gauge_rect, width=2, border_radius=7)
            st_surf = font_md.render(f"🔥 조리중 ({int(slot.progress * 100)}%)", True, config.GAUGE_COOKING)
            pill_r = pygame.Rect(r.x + 10, gauge_rect.top - 25, r.width - 20, 22)
            pygame.draw.rect(surface, (34, 24, 16), pill_r, border_radius=6)
            pygame.draw.rect(surface, config.GAUGE_COOKING, pill_r, width=1, border_radius=6)
            surface.blit(st_surf, (pill_r.centerx - st_surf.get_width() // 2, pill_r.centery - st_surf.get_height() // 2))

        elif slot.state == STATE_READY:
            # 남은 인분 수에 비례해 음식 아이콘들을 풍성하게 배치
            rem = self.remaining_servings
            positions = [
                (r.centerx - 34, r.centery - 26),
                (r.centerx + 34, r.centery - 26),
                (r.centerx, r.centery - 8),
                (r.centerx - 28, r.centery + 8),
                (r.centerx + 28, r.centery + 8),
            ]
            for i in range(min(rem, len(positions))):
                draw_food_icon(surface, positions[i], self.base_recipe_id, size=48, burnt=False)

            pill_r = pygame.Rect(r.x + 6, r.bottom - 44, r.width - 12, 38)
            pygame.draw.rect(surface, (16, 38, 26), pill_r, border_radius=8)
            pygame.draw.rect(surface, config.NEON_GREEN, pill_r, width=2, border_radius=8)
            badge_surf = font_md.render(f"✨ 보온중: {rem}/{self.max_servings}인분", True, config.NEON_GREEN)
            sub_surf = font_sm.render("타지 않음 · 터치 시 1인분 덜기", True, config.WHITE)
            surface.blit(badge_surf, (pill_r.centerx - badge_surf.get_width() // 2, pill_r.y + 2))
            surface.blit(sub_surf, (pill_r.centerx - sub_surf.get_width() // 2, pill_r.y + 20))

        # 하단 액션 버튼 렌더링 (고시인성 15px 볼드 + 3px 보더)
        rec = RECIPES.get(self.base_recipe_id)
        base_name = str(rec["name"]) if rec else self.base_recipe_id
        short_base = base_name.replace("오리지널 큐브스테이크", "큐브스테이크")

        if slot.state == STATE_IDLE:
            btn_col = (235, 118, 32)
            btn_title = f"🥘 {short_base} {self.max_servings}인분 조리"
            btn_sub = "터치하여 대량 조리 시작"
        elif slot.state == STATE_COOKING:
            btn_col = (64, 58, 78)
            btn_title = "🔥 대량 조리 진행중..."
            btn_sub = "잠시만 기다려 주세요"
        else:
            btn_col = (42, 152, 82)
            btn_title = f"✨ 1인분 덜기 ({self.remaining_servings}인분)"
            btn_sub = "트레이로 전달 / 즉시 서빙"

        pygame.draw.rect(surface, btn_col, self.action_button_rect, border_radius=10)
        pygame.draw.rect(surface, config.GOLD, self.action_button_rect, width=3, border_radius=10)

        active_tf = font_lg
        for f_sz in (15, 14, 13, 12):
            active_tf = config.get_font(f_sz, bold=True)
            if active_tf.size(btn_title)[0] <= self.action_button_rect.width - 10:
                break
        t_surf = active_tf.render(btn_title, True, config.WHITE)
        s_surf = font_sm.render(btn_sub, True, config.GOLD if slot.state != STATE_COOKING else config.TEXT_SECONDARY)
        surface.blit(
            t_surf,
            (self.action_button_rect.centerx - t_surf.get_width() // 2, self.action_button_rect.y + 8),
        )
        surface.blit(
            s_surf,
            (self.action_button_rect.centerx - s_surf.get_width() // 2, self.action_button_rect.y + 33),
        )
