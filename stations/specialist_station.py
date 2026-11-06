"""
stations/specialist_station.py
단일 메뉴 장인 모드(SPECIALIST MODE) 전용 초대형 고시인성 워크스테이션 모듈.
- 좌측 패널 (x=14..462, 448×352): [① 속재료·육수·원육 선택대] (큼직한 2열 대형 투입 버튼)
- 우측 패널 (x=818..1266, 448×352): [② 6구 장인 전용 대형 화로] (3×2 대형 슬롯 + 전용 화로 하드웨어 그래픽)
- 중앙 패널 (x=472..808, 336×352): 기존 AssemblyTray와 유기적으로 연동하여
  * 토핑이 필요 없는 기본 맛 주문 손님이 있으면 화로 슬롯 터치 즉시 원클릭 자동 서빙!
  * 토핑 조합 주문 손님이 있거나 미리 구워둘 때는 화로 슬롯 터치 시 중앙 조립 트레이로 즉시 이동!
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
import pygame

import config
from core.art_renderer import draw_food_icon
from core.game_manager import GameManager
from data.recipes import RECIPES
from data.specialist_menus import get_specialist_menu
from entities.dish import Dish
from stations.base_station import (
    STATE_BURNT,
    STATE_COOKING,
    STATE_IDLE,
    STATE_READY,
    StationSlot,
    invoke_auto_serve,
)


class SpecialistStation:
    """
    단일 메뉴 장인 모드 전용 대형 작업대 (좌측 속재료 투입대 + 우측 6구 전문 화로 통합 컨트롤러).
    """

    DEFAULT_INPUT_RECT = (14, 355, 448, 352)
    DEFAULT_APPLIANCE_RECT = (818, 355, 448, 352)

    def __init__(
        self,
        specialist_id: str = "bungeo",
        game_mgr: Optional[GameManager] = None,
        input_rect: Optional[pygame.Rect] = None,
        appliance_rect: Optional[pygame.Rect] = None,
    ) -> None:
        self.game_mgr: GameManager = game_mgr or GameManager.get_instance()
        self.input_rect: pygame.Rect = (
            input_rect.copy() if isinstance(input_rect, pygame.Rect) else pygame.Rect(self.DEFAULT_INPUT_RECT)
        )
        self.appliance_rect: pygame.Rect = (
            appliance_rect.copy() if isinstance(appliance_rect, pygame.Rect) else pygame.Rect(self.DEFAULT_APPLIANCE_RECT)
        )
        self.rect: pygame.Rect = self.appliance_rect
        self.slots: List[StationSlot] = [StationSlot(slot_index=i, can_burn=True) for i in range(6)]
        self.recipe_buttons: List[Tuple[pygame.Rect, str]] = []
        self.specialist_id: str = "bungeo"
        self.spec_data = get_specialist_menu(specialist_id)
        self.slot_type: str = str(self.spec_data.get("slot_type", "mold"))
        self.set_specialist_id(specialist_id)

    def set_specialist_id(self, specialist_id: str) -> None:
        """장인 전문점 종목('bungeo', 'odeng', 'skewer')을 변경하고 레이아웃을 재구성한다."""
        self.specialist_id = str(specialist_id or "bungeo").lower()
        self.spec_data = get_specialist_menu(self.specialist_id)
        self.slot_type = str(self.spec_data.get("slot_type", "mold"))
        self._rebuild_layout()

    def _rebuild_layout(self) -> None:
        # 1. 좌측 패널: 베이스 속재료/육수/원육 선택 버튼 (2열 그리드)
        base_rids: List[str] = list(self.spec_data.get("base_recipes", []))
        self.recipe_buttons.clear()
        in_r = self.input_rect
        pad_x, pad_y = 10, 8
        top_y = in_r.y + 42
        avail_h = in_r.height - 50
        cnt = max(1, len(base_rids))
        cols = 2
        rows = max(1, (cnt + cols - 1) // cols)
        btn_w = (in_r.width - pad_x * (cols + 1)) // cols
        btn_h = (avail_h - pad_y * (rows + 1)) // rows

        for idx, rid in enumerate(base_rids):
            c = idx % cols
            r = idx // cols
            bx = in_r.x + pad_x + c * (btn_w + pad_x)
            by = top_y + pad_y + r * (btn_h + pad_y)
            self.recipe_buttons.append((pygame.Rect(bx, by, btn_w, btn_h), rid))

        # 2. 우측 패널: 6구 초대형 장인 전용 화로 (3열 × 2행 그리드)
        ap_r = self.appliance_rect
        s_pad_x, s_pad_y = 10, 10
        s_top_y = ap_r.y + 42
        s_avail_h = ap_r.height - 50
        s_cols, s_rows = 3, 2
        slot_w = (ap_r.width - s_pad_x * (s_cols + 1)) // s_cols
        slot_h = (s_avail_h - s_pad_y * (s_rows + 1)) // s_rows

        while len(self.slots) < 6:
            self.slots.append(StationSlot(slot_index=len(self.slots), can_burn=True))

        for idx in range(6):
            c = idx % s_cols
            r = idx // s_cols
            sx = ap_r.x + s_pad_x + c * (slot_w + s_pad_x)
            sy = s_top_y + s_pad_y + r * (slot_h + s_pad_y)
            self.slots[idx].rect = pygame.Rect(sx, sy, slot_w, slot_h)

    def reset_all(self) -> None:
        """모든 화로 슬롯을 IDLE 상태로 초기화한다."""
        for sl in self.slots:
            sl.reset()
        self._rebuild_layout()

    def instant_finish_all(self) -> int:
        """조리 중인 모든 화로 슬롯을 즉시 완성(READY) 상태로 만든다."""
        cnt = 0
        for sl in self.slots:
            if sl.instant_finish():
                cnt += 1
        return cnt

    def collide_point(self, pos: Tuple[int, int]) -> bool:
        """좌측 투입대 또는 우측 6구 화로 영역 클릭 여부를 반환한다."""
        return self.input_rect.inflate(6, 6).collidepoint(pos) or self.appliance_rect.inflate(6, 6).collidepoint(pos)

    def start_cooking_recipe(self, recipe_id: str) -> Optional[StationSlot]:
        """선택된 빈 화로 슬롯(없으면 첫 번째 빈 슬롯)을 찾아 지정한 베이스 레시피 조리를 시작한다."""
        empty_slot: Optional[StationSlot] = None
        sel_idx = getattr(self, "selected_slot_index", None)
        if sel_idx is not None and 0 <= sel_idx < len(self.slots) and self.slots[sel_idx].state == STATE_IDLE:
            empty_slot = self.slots[sel_idx]
            self.selected_slot_index = None
        if empty_slot is None:
            empty_slot = next((s for s in self.slots if s.state == STATE_IDLE), None)
        if empty_slot is None:
            return None
        cook_t = self.game_mgr.get_cook_time(recipe_id, slot_type=self.slot_type)
        burn_t = self.game_mgr.get_burn_time(recipe_id, slot_type=self.slot_type)
        empty_slot.start_cooking(recipe_id=recipe_id, cook_time=cook_t, burn_time=burn_t, can_burn=True, servings=1)
        return empty_slot

    def _should_route_to_tray_first(
        self,
        base_recipe_id: str,
        customers: Optional[Iterable[Any]],
        assembly_tray: Any,
    ) -> bool:
        """
        대기 손님 중 토핑이 올라간 파생 메뉴를 원하는 손님이 기본 메뉴 손님보다 더 급하거나,
        기본 메뉴 주문 손님이 없을 때 True를 반환하여 트레이로 우선 이동시킨다.
        """
        if assembly_tray is None or not hasattr(assembly_tray, "has_empty_slot") or not assembly_tray.has_empty_slot():
            return False
        if not customers:
            return False

        best_plain_patience = 999.0
        best_topped_patience = 999.0
        for cust in customers:
            if cust is None or getattr(cust, "state", "") != "WAITING":
                continue
            for ord_rid in getattr(cust, "orders", []):
                if ord_rid == base_recipe_id:
                    best_plain_patience = min(best_plain_patience, float(getattr(cust, "patience_ratio", 1.0)))
                else:
                    rec = RECIPES.get(ord_rid)
                    if rec and rec.get("base_recipe_id") == base_recipe_id and rec.get("has_topping", False):
                        best_topped_patience = min(best_topped_patience, float(getattr(cust, "patience_ratio", 1.0)))

        if best_topped_patience < best_plain_patience:
            return True
        return False

    def handle_click(
        self,
        pos: Tuple[int, int],
        assembly_tray: Any = None,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
        customers: Optional[Iterable[Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        좌측 속재료 버튼 또는 우측 6구 화로 슬롯 터치를 처리한다.
        """
        # 1. 좌측 속재료/육수/원육 투입 버튼 클릭 확인
        for btn_rect, rid in self.recipe_buttons:
            if btn_rect.inflate(6, 6).collidepoint(pos):
                slot = self.start_cooking_recipe(rid)
                if slot is not None:
                    return {
                        "action": "start_cook",
                        "recipe_id": rid,
                        "slot_index": slot.slot_index,
                    }
                return {
                    "action": "no_empty_slot",
                    "message": "6구 화로가 모두 조리 중입니다! 완성된 음식을 먼저 꺼내세요.",
                }

        # 2. 우측 6구 전문 화로 슬롯 클릭 확인
        for slot in self.slots:
            if not slot.rect.inflate(6, 6).collidepoint(pos):
                continue

            if slot.state == STATE_BURNT:
                old_rid = slot.recipe_id
                slot.reset()
                return {
                    "action": "trash_burnt",
                    "recipe_id": old_rid,
                    "slot_index": slot.slot_index,
                }

            if slot.state == STATE_READY and slot.recipe_id:
                rid = slot.recipe_id
                # 토핑 메뉴 주문 손님이 더 급하면 중앙 조립 트레이로 먼저 이동
                if self._should_route_to_tray_first(rid, customers, assembly_tray):
                    if assembly_tray.add_dish(Dish(rid)):
                        slot.reset()
                        return {
                            "action": "moved_to_tray",
                            "recipe_id": rid,
                            "slot_index": slot.slot_index,
                        }

                # 기본 맛 주문 손님이 있으면 즉시 자동 비행 서빙!
                served, serve_info = invoke_auto_serve(auto_serve_cb, rid, slot.rect.center)
                if served:
                    slot.reset()
                    return {
                        "action": "served",
                        "recipe_id": rid,
                        "slot_index": slot.slot_index,
                        "serve_info": serve_info,
                    }

                # 기본 맛 주문 손님이 없으면 중앙 조립 트레이로 이동하여 토핑 추가/보관 지원
                if assembly_tray is not None and hasattr(assembly_tray, "add_dish"):
                    if assembly_tray.add_dish(Dish(rid)):
                        slot.reset()
                        return {
                            "action": "moved_to_tray",
                            "recipe_id": rid,
                            "slot_index": slot.slot_index,
                        }
                    return {
                        "action": "tray_full",
                        "recipe_id": rid,
                        "slot_index": slot.slot_index,
                        "message": "서빙 트레이가 가득 찼습니다!",
                    }

                return {
                    "action": "no_customer",
                    "recipe_id": rid,
                    "slot_index": slot.slot_index,
                    "message": "해당 메뉴를 주문한 손님이 없습니다!",
                }

            if slot.state == STATE_COOKING:
                cancel_badge = pygame.Rect(slot.rect.right - 30, slot.rect.y + 3, 26, 24)
                trash_active = bool(assembly_tray is not None and getattr(assembly_tray, "trash_mode", False))
                if cancel_badge.inflate(8, 8).collidepoint(pos) or trash_active:
                    old_rid = slot.recipe_id
                    slot.reset()
                    return {
                        "action": "trash_dish",
                        "recipe_id": old_rid,
                        "slot_index": slot.slot_index,
                    }
                return None

            if slot.state == STATE_IDLE:
                # 빈 슬롯을 터치했을 때 자동으로 1번 메뉴(팥)가 들어가지 않도록 차단하고, 해당 칸을 투입 대상 슬롯으로 선택!
                self.selected_slot_index = slot.slot_index
                return {
                    "action": "select_target_slot",
                    "slot_index": slot.slot_index,
                    "message": f"화로 #{slot.slot_index + 1}번 칸 선택됨! 좌측에서 넣을 맛 버튼을 터치하세요.",
                }

        return None

    def update(self, dt: float) -> List[Tuple[int, str]]:
        """6구 화로 슬롯의 조리/탄 상태를 업데이트한다."""
        events: List[Tuple[int, str]] = []
        for sl in self.slots:
            ev = sl.update(dt)
            if ev:
                events.append((sl.slot_index, ev))
        return events

    def draw(self, surface: pygame.Surface, time_tick: float = 0.0) -> None:
        """좌측 속재료 투입대와 우측 6구 장인 전용 화로를 고시인성 UI로 렌더링한다."""
        self._draw_input_panel(surface, time_tick)
        self._draw_appliance_panel(surface, time_tick)

    def _draw_input_panel(self, surface: pygame.Surface, time_tick: float) -> None:
        r = self.input_rect
        theme_col = self.spec_data.get("theme_color", config.POCHA_ORANGE)
        accent_col = self.spec_data.get("accent_color", config.GOLD)

        pygame.draw.rect(surface, (28, 24, 42), r, border_radius=14)
        pygame.draw.rect(surface, theme_col, r, width=2, border_radius=14)

        # 상단 헤더
        hdr_rect = pygame.Rect(r.x + 6, r.y + 6, r.width - 12, 30)
        pygame.draw.rect(surface, (48, 36, 64), hdr_rect, border_radius=8)
        pygame.draw.rect(surface, accent_col, hdr_rect, width=1, border_radius=8)
        title_f = config.get_font(15, bold=True)
        raw_t = str(self.spec_data.get("input_panel_title", "① 속재료·육수 선택"))
        t_surf = title_f.render(raw_t, True, accent_col)
        if t_surf.get_width() > hdr_rect.width - 10:
            t_surf = config.get_font(13, bold=True).render(raw_t, True, accent_col)
        surface.blit(t_surf, t_surf.get_rect(center=hdr_rect.center))

        has_empty = any(s.state == STATE_IDLE for s in self.slots)
        name_f = config.get_font(15, bold=True)
        sub_f = config.get_font(13, bold=True)

        for idx, (btn_rect, rid) in enumerate(self.recipe_buttons):
            rec = RECIPES.get(rid)
            r_name = str(rec["name"]) if rec else rid
            price = self.game_mgr.get_recipe_price(rid) if hasattr(self.game_mgr, "get_recipe_price") else 3500
            r_col = rec.get("color", theme_col) if rec else theme_col

            bg_col = (44, 38, 68) if has_empty else (28, 25, 40)
            border_col = accent_col if has_empty else config.UI_BORDER
            pygame.draw.rect(surface, bg_col, btn_rect, border_radius=11)
            pygame.draw.rect(surface, border_col, btn_rect, width=2, border_radius=11)

            # 좌측 컬러 스트라이프 & 46px 대형 음식 아이콘
            stripe_r = pygame.Rect(btn_rect.x + 4, btn_rect.y + 6, 6, btn_rect.height - 12)
            pygame.draw.rect(surface, r_col, stripe_r, border_radius=3)
            icon_pos = (btn_rect.x + 36, btn_rect.centery)
            draw_food_icon(surface, icon_pos, rid, size=46, burnt=False)

            # 우측 상단 굵은 메뉴명
            max_tx_w = btn_rect.width - 68
            act_nf = name_f
            for sz in (15, 14, 13, 12):
                act_nf = config.get_font(sz, bold=True)
                if act_nf.size(r_name)[0] <= max_tx_w:
                    break
            nm_s = act_nf.render(r_name, True, config.WHITE if has_empty else config.TEXT_MUTED)
            surface.blit(nm_s, (btn_rect.x + 64, btn_rect.centery - 20))

            # 우측 하단 가격 & 터치 투입 배지
            pill_r = pygame.Rect(btn_rect.x + 64, btn_rect.centery + 4, max_tx_w - 4, 22)
            pygame.draw.rect(surface, (24, 92, 56) if has_empty else (46, 42, 58), pill_r, border_radius=6)
            lbl_str = f"💰{price:,}원 · 투입" if has_empty else "화로 만석"
            p_s = sub_f.render(lbl_str, True, (152, 255, 178) if has_empty else config.TEXT_SECONDARY)
            surface.blit(p_s, p_s.get_rect(center=pill_r.center))

    def _draw_appliance_panel(self, surface: pygame.Surface, time_tick: float) -> None:
        r = self.appliance_rect
        theme_col = self.spec_data.get("theme_color", config.POCHA_ORANGE)
        accent_col = self.spec_data.get("accent_color", config.GOLD)

        pygame.draw.rect(surface, (30, 26, 44), r, border_radius=14)
        pygame.draw.rect(surface, accent_col, r, width=2, border_radius=14)

        # 상단 헤더 (업그레이드 레벨 표시 포함)
        hdr_rect = pygame.Rect(r.x + 6, r.y + 6, r.width - 12, 30)
        pygame.draw.rect(surface, (56, 38, 34), hdr_rect, border_radius=8)
        pygame.draw.rect(surface, config.GOLD, hdr_rect, width=1, border_radius=8)
        lvl = self.game_mgr.get_station_level(self.slot_type)
        raw_t = f"{self.spec_data.get('appliance_title', '② 6구 장인 전용 화로')} (Lv.{lvl})"
        title_f = config.get_font(15, bold=True)
        t_surf = title_f.render(raw_t, True, config.GOLD)
        if t_surf.get_width() > hdr_rect.width - 10:
            t_surf = config.get_font(13, bold=True).render(raw_t, True, config.GOLD)
        surface.blit(t_surf, t_surf.get_rect(center=hdr_rect.center))

        name_f = config.get_font(13, bold=True)
        pill_f = config.get_font(13, bold=True)

        for idx, slot in enumerate(self.slots):
            sr = slot.rect
            self._draw_slot_hardware_bg(surface, sr, idx, slot, time_tick)

            if slot.state == STATE_IDLE:
                is_target = getattr(self, "selected_slot_index", None) == idx
                if is_target:
                    pygame.draw.rect(surface, config.NEON_CYAN, sr, width=3, border_radius=10)
                idle_lbl = (
                    f"붕어틀 #{idx + 1}"
                    if self.specialist_id == "bungeo"
                    else (f"오뎅칸 #{idx + 1}" if self.specialist_id == "odeng" else f"참숯구 #{idx + 1}")
                )
                s1 = name_f.render(idle_lbl, True, config.NEON_CYAN if is_target else (192, 188, 214))
                s2 = config.get_font(12, bold=True).render(
                    "👈 좌측 맛 선택!" if is_target else "좌측 메뉴 터치",
                    True,
                    config.GOLD if is_target else (138, 134, 162),
                )
                surface.blit(s1, s1.get_rect(center=(sr.centerx, sr.centery - 10)))
                surface.blit(s2, s2.get_rect(center=(sr.centerx, sr.centery + 12)))
                continue

            rec = RECIPES.get(slot.recipe_id or "")
            short_nm = str(rec["name"]) if rec else str(slot.recipe_id)
            if len(short_nm) > 7:
                short_nm = short_nm[:7]

            # 상단 메뉴명 배지 (조리 중일 때는 우측 상단 [✕] 취소 버튼과 겹치지 않게 폭 조정)
            tag_w = (sr.width - 36) if slot.state == STATE_COOKING else (sr.width - 12)
            top_tag = pygame.Rect(sr.x + 6, sr.y + 5, tag_w, 20)
            pygame.draw.rect(surface, (18, 16, 28), top_tag, border_radius=5)
            nt = config.get_font(12, bold=True).render(short_nm, True, config.WHITE)
            surface.blit(nt, nt.get_rect(center=top_tag.center))

            if slot.state == STATE_COOKING:
                cancel_badge = pygame.Rect(sr.right - 26, sr.y + 4, 22, 22)
                pygame.draw.rect(surface, (198, 42, 46), cancel_badge, border_radius=6)
                pygame.draw.rect(surface, config.WHITE, cancel_badge, width=1, border_radius=6)
                xt = config.get_font(12, bold=True).render("✕", True, config.WHITE)
                surface.blit(xt, xt.get_rect(center=cancel_badge.center))

            # 중앙 대형 음식 아이콘 (58px)
            bob = int(math.sin(time_tick * 7.0 + idx) * 3) if slot.state == STATE_READY else 0
            draw_food_icon(
                surface,
                (sr.centerx, sr.centery - 2 + bob),
                slot.recipe_id or "bungeoppang_redbean",
                size=56,
                burnt=(slot.state == STATE_BURNT),
            )

            # 하단 상태 캡슐 & 진행 바
            bot_pill = pygame.Rect(sr.x + 6, sr.bottom - 28, sr.width - 12, 22)
            if slot.state == STATE_COOKING:
                pygame.draw.rect(surface, (22, 20, 34), bot_pill, border_radius=6)
                fill_w = int((bot_pill.width - 4) * slot.progress)
                if fill_w > 0:
                    pygame.draw.rect(
                        surface,
                        (238, 142, 36),
                        (bot_pill.x + 2, bot_pill.y + 2, fill_w, bot_pill.height - 4),
                        border_radius=5,
                    )
                pygame.draw.rect(surface, config.GOLD, bot_pill, width=1, border_radius=6)
                pct = int(slot.progress * 100)
                pt = pill_f.render(f"♨ 조리 {pct}%", True, config.WHITE)
                surface.blit(pt, pt.get_rect(center=bot_pill.center))

            elif slot.state == STATE_READY:
                burn_r = slot.burn_progress
                bg_c = (218, 68, 36) if burn_r > 0.65 else (28, 158, 72)
                pygame.draw.rect(surface, bg_c, bot_pill, border_radius=6)
                pygame.draw.rect(surface, config.WHITE, bot_pill, width=1, border_radius=6)
                lbl = "⚠️ 타기 직전!" if burn_r > 0.65 else "★ 완성! 터치!"
                pt = pill_f.render(lbl, True, config.WHITE)
                surface.blit(pt, pt.get_rect(center=bot_pill.center))

            elif slot.state == STATE_BURNT:
                pygame.draw.rect(surface, (168, 32, 38), bot_pill, border_radius=6)
                pygame.draw.rect(surface, config.RED, bot_pill, width=1, border_radius=6)
                pt = pill_f.render("🗑️ 터치 폐기", True, config.WHITE)
                surface.blit(pt, pt.get_rect(center=bot_pill.center))

    def _draw_slot_hardware_bg(
        self,
        surface: pygame.Surface,
        sr: pygame.Rect,
        idx: int,
        slot: StationSlot,
        time_tick: float,
    ) -> None:
        """장인 전문점 종류(붕어빵 무쇠틀 / 2색 오뎅 육수솥 / 참숯 석쇠)에 맞는 화로 슬롯 배경을 렌더링한다."""
        if self.specialist_id == "odeng":
            # 좌측 열/우측 열 구분하여 맑은 육수 vs 얼큰 빨간 육수 사각 오뎅솥 연출
            is_spicy_vat = (idx % 3 == 2) or (slot.recipe_id == "odeng_red_spicy")
            broth_bg = (96, 34, 32) if is_spicy_vat else (78, 62, 38)
            broth_inner = (138, 44, 36) if is_spicy_vat else (112, 88, 48)
            pygame.draw.rect(surface, (148, 156, 172), sr, border_radius=10)
            inner = sr.inflate(-8, -8)
            pygame.draw.rect(surface, broth_bg, inner, border_radius=8)
            pygame.draw.rect(surface, broth_inner, inner.inflate(-8, -8), border_radius=6)
        elif self.specialist_id == "skewer":
            # 이글거리는 참숯 불꽃과 스테인리스 석쇠 격자
            pygame.draw.rect(surface, (44, 32, 32), sr, border_radius=10)
            inner = sr.inflate(-8, -8)
            glow = int(20 * math.sin(time_tick * 5.0 + idx))
            pygame.draw.rect(surface, (92 + glow, 34, 24), inner, border_radius=8)
            for gy in range(inner.y + 12, inner.bottom - 8, 16):
                pygame.draw.line(surface, (168, 174, 186), (inner.x + 4, gy), (inner.right - 4, gy), 2)
        else:
            # 황금 회전 무쇠 붕어빵 주물틀
            pygame.draw.rect(surface, (52, 46, 58), sr, border_radius=10)
            inner = sr.inflate(-8, -8)
            pygame.draw.rect(surface, (34, 30, 40), inner, border_radius=8)
            pygame.draw.ellipse(surface, (24, 22, 28), inner.inflate(-10, -18))

        # 상태별 고대비 외곽 테두리
        if slot.state == STATE_READY:
            border_c = config.NEON_GREEN if slot.burn_progress <= 0.65 else config.NEON_ORANGE
            pygame.draw.rect(surface, border_c, sr, width=3, border_radius=10)
        elif slot.state == STATE_COOKING:
            pygame.draw.rect(surface, config.GOLD, sr, width=2, border_radius=10)
        elif slot.state == STATE_BURNT:
            pygame.draw.rect(surface, config.RED, sr, width=3, border_radius=10)
        else:
            pygame.draw.rect(surface, (96, 92, 118), sr, width=2, border_radius=10)
