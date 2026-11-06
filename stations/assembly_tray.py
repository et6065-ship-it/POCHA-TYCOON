"""
stations/assembly_tray.py
중앙 조립 & 토핑 작업대(AssemblyTray) 및 손님 자동 매칭(인내심 최소 손님 우선) 모듈.
- game_mgr.get_tray_slot_count()(2~5개)의 접시 슬롯
- 현재 장착된 그릴/대량팬 레시피에 맞는 토핑 버튼들
- 휴지통 버튼(🗑️ 폐기)
- 접시 클릭 시 해당 메뉴를 기다리는 손님(인내심이 가장 낮은 손님 우선)에게 원클릭 즉시 자동 서빙!
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union
import pygame

import config
from core.art_renderer import draw_station_hardware, draw_topping_badge
from core.game_manager import GameManager
from data.recipes import TOPPINGS, get_station_toppings
from entities.customer import Customer
from entities.dish import Dish
from stations.base_station import invoke_auto_serve


def find_best_customer_for_recipe(
    customers: Iterable[Optional[Customer]],
    recipe_id: str,
) -> Optional[Customer]:
    """
    대기 중인 손님 목록 중 해당 레시피(recipe_id)를 주문한 손님을 탐색하여,
    남은 인내심(patience)이 가장 낮은 손님을 우선 반환한다.
    """
    candidates: List[Customer] = []
    for cust in customers:
        if cust is not None and cust.wants_recipe(recipe_id):
            candidates.append(cust)
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c.patience, c.slot_index))
    return candidates[0]


def serve_recipe_to_customers(
    customers: Iterable[Optional[Customer]],
    recipe_id: str,
    game_mgr: Any = None,
) -> Optional[Dict[str, Any]]:
    """
    해당 메뉴를 기다리는(인내심이 가장 낮은) 손님에게 음식을 서빙하고
    보상 결과 딕셔너리를 반환한다. 매칭되는 손님이 없으면 None을 반환한다.
    """
    target = find_best_customer_for_recipe(customers, recipe_id)
    if target is None:
        return None
    result = target.receive_dish(recipe_id, game_mgr=game_mgr)
    result["customer"] = target
    return result


class AssemblyTray:
    """
    중앙 소스/토핑 조합 작업대 및 원클릭 자동 서빙 트레이.
    """

    DEFAULT_RECT: Tuple[int, int, int, int] = (472, 355, 336, 352)

    def __init__(
        self,
        rect: Optional[Union[pygame.Rect, Tuple[int, int, int, int]]] = None,
        game_mgr: Any = None,
    ) -> None:
        if rect is not None and hasattr(rect, "get_tray_slot_count") and game_mgr is None:
            # AssemblyTray(game_mgr) 형태로 호출된 경우 호환
            game_mgr = rect
            rect = None

        self.game_mgr: Any = game_mgr or GameManager.get_instance()
        self.rect: pygame.Rect = (
            rect.copy()
            if isinstance(rect, pygame.Rect)
            else pygame.Rect(rect if rect is not None else self.DEFAULT_RECT)
        )
        self._last_layout_rect: pygame.Rect = self.rect.copy()

        self.dishes: List[Optional[Dish]] = []
        self.slot_rects: List[pygame.Rect] = []
        self.selected_slot: int = 0

        self.available_topping_ids: List[str] = []
        self.topping_buttons: List[Tuple[pygame.Rect, str]] = []
        self.trash_rect: pygame.Rect = pygame.Rect(0, 0, 10, 10)
        self.trash_mode_rect: pygame.Rect = pygame.Rect(0, 0, 10, 10)
        self.trash_mode: bool = False

        # 모바일 0.35초 롱프레스(길게 누르기) 즉시 폐기 상태
        self.hold_slot_idx: Optional[int] = None
        self.hold_timer: float = 0.0
        self.LONG_PRESS_DURATION: float = 0.35
        self._pending_hold_feedback: Optional[Dict[str, Any]] = None
        self._suppress_next_click: bool = False

        self.sync_slots_with_manager()

    @property
    def slots(self) -> List[Optional[Dish]]:
        """dishes 리스트의 별칭."""
        return self.dishes

    def _get_desired_slot_count(self) -> int:
        if self.game_mgr and str(getattr(self.game_mgr, "mode", "")).upper() == "SPECIALIST":
            base_cnt = int(self.game_mgr.get_tray_slot_count()) if hasattr(self.game_mgr, "get_tray_slot_count") else 3
            return max(3, base_cnt)
        if self.game_mgr and hasattr(self.game_mgr, "get_tray_slot_count"):
            return max(2, int(self.game_mgr.get_tray_slot_count()))
        return config.BASE_TRAY_SLOTS

    def sync_slots_with_manager(self) -> None:
        """
        GameManager의 트레이 업그레이드 레벨 및 현재 장착된 그릴/대량팬(또는 단일 메뉴 장인 전문점)의
        토핑 목록에 맞춰 슬롯과 토핑 버튼 레이아웃을 동기화한다.
        """
        desired = self._get_desired_slot_count()
        while len(self.dishes) < desired:
            self.dishes.append(None)
        if len(self.dishes) > desired:
            # 뒤쪽 빈 슬롯부터 축소하되 이미 음식이 있으면 보존
            trimmed = self.dishes[:desired]
            self.dishes = trimmed

        if self.selected_slot >= len(self.dishes):
            self.selected_slot = max(0, len(self.dishes) - 1)

        # 활성 스테이션의 토핑 목록 수집 (단일 메뉴 장인 모드일 때는 해당 전문점 전용 토핑 사용)
        topping_ids: List[str] = []
        if self.game_mgr and str(getattr(self.game_mgr, "mode", "")).upper() == "SPECIALIST":
            spec = self.game_mgr.get_selected_specialist_data()
            for tid in spec.get("topping_ids", []):
                if tid in TOPPINGS and tid not in topping_ids:
                    topping_ids.append(str(tid))
        elif self.game_mgr and hasattr(self.game_mgr, "get_active_station_ids"):
            for st_id in self.game_mgr.get_active_station_ids():
                for t_meta in get_station_toppings(st_id):
                    tid = str(t_meta["id"])
                    if tid not in topping_ids:
                        topping_ids.append(tid)

        if not topping_ids:
            # 기본 한국 토핑 폴백
            topping_ids = ["spicy_sauce", "teriyaki_sauce", "green_onion", "cheese", "gimmari"]

        self.available_topping_ids = topping_ids
        self._rebuild_layout()

    def _ensure_layout(self) -> None:
        if self.rect != self._last_layout_rect:
            self._last_layout_rect = self.rect.copy()
            self._rebuild_layout()

    def _rebuild_layout(self) -> None:
        self._last_layout_rect = self.rect.copy()
        r = self.rect
        pad = 6

        # 1. 상단 접시 슬롯 영역
        slot_count = max(2, len(self.dishes))
        plate_area_top = r.y + 36
        plate_area_h = 132

        self.slot_rects = []
        cols = slot_count if slot_count <= 3 else ((slot_count + 1) // 2)
        rows = 1 if slot_count <= 3 else 2
        cell_w = (r.width - pad * (cols + 1)) // cols
        cell_h = (plate_area_h - pad * (rows + 1)) // rows

        for idx in range(slot_count):
            col = idx % cols
            row = idx // cols
            sx = r.x + pad + col * (cell_w + pad)
            sy = plate_area_top + pad + row * (cell_h + pad)
            self.slot_rects.append(pygame.Rect(sx, sy, cell_w, cell_h))

        # 2. 중단 토핑 버튼 영역 (최소 56x44px 이상 대형 터치 버튼 보장)
        topping_top = plate_area_top + plate_area_h + 4
        trash_h = 44
        topping_area_h = max(96, r.bottom - topping_top - trash_h - 10)

        self.topping_buttons = []
        t_cnt = max(1, len(self.available_topping_ids))
        t_cols = min(3, t_cnt)
        t_rows = (t_cnt + t_cols - 1) // t_cols
        t_w = max(56, (r.width - pad * (t_cols + 1)) // t_cols)
        t_h = max(44, (topping_area_h - pad * (t_rows + 1)) // max(1, t_rows))

        for idx, tid in enumerate(self.available_topping_ids):
            c = idx % t_cols
            rw = idx // t_cols
            bx = r.x + pad + c * (t_w + pad)
            by = topping_top + pad + rw * (t_h + pad)
            self.topping_buttons.append((pygame.Rect(bx, by, t_w, t_h), tid))

        # 3. 하단 휴지통(즉시 폐기) & [🗑️ 버리기 모드] 토글 버튼
        total_w = r.width - pad * 2
        left_w = int(total_w * 0.56)
        right_w = total_w - left_w - 6
        by_trash = r.bottom - trash_h - 6
        self.trash_rect = pygame.Rect(r.x + pad, by_trash, left_w, trash_h)
        self.trash_mode_rect = pygame.Rect(self.trash_rect.right + 6, by_trash, right_w, trash_h)

    def has_empty_slot(self) -> bool:
        """비어 있는 접시 슬롯이 있는지 여부를 반환한다."""
        return any(d is None for d in self.dishes)

    def get_empty_slot_index(self) -> Optional[int]:
        """첫 번째 빈 접시 슬롯의 인덱스를 반환한다. 가득 찼으면 None 반환."""
        for idx, d in enumerate(self.dishes):
            if d is None:
                return idx
        return None

    def add_dish(self, dish: Union[Dish, str]) -> bool:
        """
        빈 접시 슬롯에 Dish 객체를 올리고, 해당 슬롯을 선택 상태로 만든다.
        성공 시 True, 빈 슬롯이 없으면 False를 반환한다.
        """
        idx = self.get_empty_slot_index()
        if idx is None:
            return False
        dish_obj = dish if isinstance(dish, Dish) else Dish(str(dish))
        self.dishes[idx] = dish_obj
        self.selected_slot = idx
        return True

    def remove_dish(self, slot_index: int) -> Optional[Dish]:
        """지정된 슬롯의 음식을 제거하고 반환한다."""
        if 0 <= slot_index < len(self.dishes):
            dish = self.dishes[slot_index]
            self.dishes[slot_index] = None
            return dish
        return None

    def clear_all(self) -> None:
        """모든 접시 슬롯을 비운다."""
        for i in range(len(self.dishes)):
            self.dishes[i] = None
        self.selected_slot = 0

    def apply_topping(self, topping_id: str) -> Optional[Dict[str, Any]]:
        """
        현재 트레이에 놓인 음식 중 해당 토핑을 추가할 수 있는 음식(선택된 슬롯 우선,
        없으면 첫 번째 가능 슬롯)에 토핑을 즉시 추가한다.
        """
        if not self.dishes:
            return None

        # 탐색 순서: selected_slot 우선 -> 나머지 슬롯 순서대로
        order = [self.selected_slot] + [
            i for i in range(len(self.dishes)) if i != self.selected_slot
        ]
        for idx in order:
            if 0 <= idx < len(self.dishes):
                dish = self.dishes[idx]
                if dish is not None and dish.can_add_topping(topping_id):
                    dish.add_topping(topping_id)
                    self.selected_slot = idx
                    return {
                        "action": "add_topping",
                        "topping_id": topping_id,
                        "recipe_id": dish.recipe_id,
                        "slot_index": idx,
                        "dish": dish,
                    }

        return {
            "action": "invalid_topping",
            "topping_id": topping_id,
            "message": "해당 토핑을 추가할 수 있는 음식이 없습니다.",
        }

    def trash_selected_or_first(self) -> Optional[Dict[str, Any]]:
        """선택된 슬롯(우선) 또는 음식이 놓인 첫 번째 슬롯의 음식을 폐기한다."""
        order = [self.selected_slot] + [
            i for i in range(len(self.dishes)) if i != self.selected_slot
        ]
        for idx in order:
            if 0 <= idx < len(self.dishes) and self.dishes[idx] is not None:
                removed = self.dishes[idx]
                self.dishes[idx] = None
                return {
                    "action": "trash_dish",
                    "slot_index": idx,
                    "recipe_id": removed.recipe_id if removed else "",
                    "dish": removed,
                }
        return {
            "action": "trash_empty",
            "message": "폐기할 음식이 없습니다.",
        }

    def start_hold(self, pos: Tuple[int, int]) -> None:
        """모바일 0.35초 롱프레스(길게 누르기) 감지를 시작한다."""
        self._ensure_layout()
        self.hold_slot_idx = None
        self.hold_timer = 0.0
        for idx, s_rect in enumerate(self.slot_rects):
            if s_rect.inflate(8, 8).collidepoint(pos) and idx < len(self.dishes) and self.dishes[idx] is not None:
                self.hold_slot_idx = idx
                self.hold_timer = 0.0
                break

    def end_hold(self) -> None:
        """터치/마우스 해제 시 롱프레스 타이머를 초기화한다."""
        self.hold_slot_idx = None
        self.hold_timer = 0.0

    def pop_hold_feedback(self) -> Optional[Dict[str, Any]]:
        """롱프레스로 자동 폐기된 결과가 있으면 반환하고 비운다."""
        fb = self._pending_hold_feedback
        self._pending_hold_feedback = None
        return fb

    def update(self, dt: float) -> None:
        """0.35초 롱프레스 유지 시 접시 음식을 즉시 폐기한다."""
        if self.hold_slot_idx is not None:
            idx = self.hold_slot_idx
            if 0 <= idx < len(self.dishes) and self.dishes[idx] is not None:
                self.hold_timer += max(0.0, float(dt))
                if self.hold_timer >= self.LONG_PRESS_DURATION:
                    removed = self.dishes[idx]
                    self.dishes[idx] = None
                    self.hold_slot_idx = None
                    self.hold_timer = 0.0
                    self._suppress_next_click = True
                    s_rect = self.slot_rects[idx] if idx < len(self.slot_rects) else self.rect
                    self._pending_hold_feedback = {
                        "action": "trash_dish",
                        "slot_index": idx,
                        "recipe_id": removed.recipe_id if removed else "",
                        "dish": removed,
                        "pos": s_rect.center,
                    }
            else:
                self.hold_slot_idx = None
                self.hold_timer = 0.0

    def handle_click(
        self,
        pos: Tuple[int, int],
        auto_serve_cb: Optional[Callable[..., Any]] = None,
        button: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        조립 트레이 클릭 인터랙션을 처리한다.
        - 접시 슬롯 클릭:
          * 우클릭(button == 3), [X] 배지 클릭, 또는 [🗑️ 버리기 모드] 활성 상태: 해당 접시 음식 즉시 폐기.
          * 좌클릭(button == 1): auto_serve_cb(dish.recipe_id, slot_center)를 호출해
            해당 메뉴를 기다리는 손님에게 즉시 자동 서빙!
        - 토핑 버튼 클릭(inflate(8, 8)): 선택된 슬롯(우선) 또는 첫 번째 가능 슬롯의 음식에 토핑 추가.
        - 휴지통 버튼 클릭: 선택된/첫 번째 접시 음식 폐기 또는 [🗑️ 버리기 모드] 토글.
        """
        self._ensure_layout()
        if self._suppress_next_click:
            self._suppress_next_click = False
            return None
        if not self.rect.inflate(8, 8).collidepoint(pos):
            return None

        # 1. 접시 슬롯 클릭 확인 (우측 상단 30x30 [X] 배지 + 버리기 모드 + 슬롯 터치 판정 여유 확보)
        for idx, s_rect in enumerate(self.slot_rects):
            if not s_rect.inflate(8, 8).collidepoint(pos):
                continue

            dish = self.dishes[idx]
            self.selected_slot = idx

            if dish is None:
                return {
                    "action": "select_empty_slot",
                    "slot_index": idx,
                }

            # 모바일 원터치 폐기: 접시 우측 상단 [X] 배지(30x30) 터치, 버리기 모드 ON, 또는 우클릭(button == 3) 시 즉시 폐기
            del_badge_rect = pygame.Rect(s_rect.right - 30, s_rect.y + 2, 28, 28)
            if button == 3 or self.trash_mode or del_badge_rect.inflate(8, 8).collidepoint(pos):
                self.dishes[idx] = None
                self.trash_mode = False
                return {
                    "action": "trash_dish",
                    "slot_index": idx,
                    "recipe_id": dish.recipe_id,
                    "dish": dish,
                }

            # 좌클릭/터치 시 원터치 자동 서빙 시도
            served, serve_res = invoke_auto_serve(
                auto_serve_cb,
                dish.recipe_id,
                s_rect.center,
            )
            if served:
                self.dishes[idx] = None
                return {
                    "action": "auto_served",
                    "slot_index": idx,
                    "recipe_id": dish.recipe_id,
                    "dish": dish,
                    "serve_result": serve_res,
                }

            return {
                "action": "select_slot",
                "slot_index": idx,
                "recipe_id": dish.recipe_id,
                "dish": dish,
            }

        # 2. 토핑 버튼 터치 확인 (엄지손가락 오터치 방지 inflate(8, 8))
        for btn_rect, tid in self.topping_buttons:
            if btn_rect.inflate(8, 8).collidepoint(pos):
                return self.apply_topping(tid)

        # 3. [🗑️ 버리기 모드] 토글 버튼 터치 확인
        if self.trash_mode_rect.inflate(6, 6).collidepoint(pos):
            self.trash_mode = not self.trash_mode
            return {
                "action": "toggle_trash_mode",
                "trash_mode": self.trash_mode,
                "message": "🗑️ 버리기 모드 ON: 폐기할 접시를 터치하세요!" if self.trash_mode else "버리기 모드 해제",
            }

        # 4. 휴지통 즉시 비우기 버튼 터치 확인
        if self.trash_rect.inflate(8, 8).collidepoint(pos):
            self.trash_mode = False
            return self.trash_selected_or_first()

        return None

    def draw(
        self,
        surface: pygame.Surface,
        time_tick: Any = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._ensure_layout()
        pygame.draw.rect(surface, config.UI_PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surface, config.UI_HIGHLIGHT, self.rect, width=2, border_radius=12)

        # 상단 헤더 (단축키 텍스트 없이 정중앙 고대비 15px 볼드 타이틀)
        header_rect = pygame.Rect(self.rect.x + 4, self.rect.y + 4, self.rect.width - 8, 30)
        pygame.draw.rect(surface, (62, 42, 32), header_rect, border_radius=8)
        pygame.draw.rect(surface, config.GOLD, header_rect, width=1, border_radius=8)
        title_font = config.get_font(15, bold=True)
        if self.game_mgr and str(getattr(self.game_mgr, "mode", "")).upper() == "SPECIALIST":
            spec_title = str(self.game_mgr.get_selected_specialist_data().get("tray_title", "③ 토핑·소스 & 포장 서빙대"))
            raw_title = f"{spec_title} ({len(self.dishes)}칸)"
        else:
            raw_title = f"🍱 조립 & 서빙 트레이 ({len(self.dishes)}칸 · 터치 자동서빙)"
        title_surf = title_font.render(raw_title, True, config.GOLD)
        if title_surf.get_width() > header_rect.width - 10:
            title_surf = config.get_font(13, bold=True).render(raw_title, True, config.GOLD)
        surface.blit(
            title_surf,
            (
                header_rect.centerx - title_surf.get_width() // 2,
                header_rect.centery - title_surf.get_height() // 2,
            ),
        )

        font_sm = config.get_font(14, bold=True)
        font_xs = config.get_font(14, bold=True)

        # 1. 접시 슬롯 렌더링
        for idx, s_rect in enumerate(self.slot_rects):
            is_sel = idx == self.selected_slot
            draw_station_hardware(surface, s_rect, station_type="tray")
            border_col = config.NEON_YELLOW if is_sel else (112, 92, 74)
            pygame.draw.rect(surface, border_col, s_rect, width=3 if is_sel else 2, border_radius=9)

            dish = self.dishes[idx] if idx < len(self.dishes) else None
            if dish is not None:
                icon_size = min(56, max(38, min(s_rect.width, s_rect.height) - 20))
                dish.draw(surface, (s_rect.centerx, s_rect.centery - 9), size=icon_size)

                # 우측 상단 모바일 원터치 폐기 [✕] 배지 (28x28 대형 고시인성)
                del_badge = pygame.Rect(s_rect.right - 30, s_rect.y + 2, 28, 28)
                pygame.draw.rect(surface, (228, 42, 52) if self.trash_mode else (196, 36, 46), del_badge, border_radius=7)
                pygame.draw.rect(surface, config.GOLD if self.trash_mode else config.WHITE, del_badge, width=2, border_radius=7)
                x_s = config.get_font(15, bold=True).render("✕", True, config.WHITE)
                surface.blit(x_s, x_s.get_rect(center=del_badge.center))

                # 0.35초 롱프레스 진행 중일 때 게이지 표시
                if self.hold_slot_idx == idx and self.hold_timer > 0.04:
                    hold_ratio = min(1.0, self.hold_timer / max(0.1, self.LONG_PRESS_DURATION))
                    hbar = pygame.Rect(s_rect.x + 6, s_rect.y + 6, s_rect.width - 38, 12)
                    pygame.draw.rect(surface, (24, 18, 28), hbar, border_radius=6)
                    pygame.draw.rect(surface, config.RED, (hbar.x, hbar.y, int(hbar.width * hold_ratio), hbar.height), border_radius=6)
                    pygame.draw.rect(surface, config.WHITE, hbar, width=2, border_radius=6)

                name_txt = (
                    dish.name.replace("갈릭버터 큐브스테이크", "갈릭 큐브스테이크")
                    .replace("오리지널 큐브스테이크", "큐브스테이크")
                    .replace("스위트 칠리 지파이", "칠리 지파이")
                    .replace("마라 시즈닝 지파이", "마라 지파이")
                    .replace("크리스피 대왕 지파이", "대왕 지파이")
                )
                lbl_bg = pygame.Rect(s_rect.x + 3, s_rect.bottom - 24, s_rect.width - 6, 22)
                pygame.draw.rect(surface, (18, 14, 26), lbl_bg, border_radius=6)
                pygame.draw.rect(surface, config.GOLD if dish.has_topping else config.UI_BORDER, lbl_bg, width=1, border_radius=6)
                dish_font = font_xs
                for f_sz in (14, 13, 12, 11):
                    dish_font = config.get_font(f_sz, bold=True)
                    if dish_font.size(name_txt)[0] <= lbl_bg.width - 6:
                        break
                lbl_surf = dish_font.render(name_txt, True, config.GOLD if dish.has_topping else config.WHITE)
                surface.blit(
                    lbl_surf,
                    (lbl_bg.centerx - lbl_surf.get_width() // 2, lbl_bg.centery - lbl_surf.get_height() // 2),
                )
            else:
                empty_pill = pygame.Rect(s_rect.centerx - 42, s_rect.centery - 13, 84, 26)
                pygame.draw.rect(surface, (34, 28, 44), empty_pill, border_radius=7)
                empty_surf = font_xs.render(f"빈 접시 {idx + 1}", True, (210, 198, 226))
                surface.blit(
                    empty_surf,
                    (empty_pill.centerx - empty_surf.get_width() // 2, empty_pill.centery - empty_surf.get_height() // 2),
                )

        # 2. 토핑 버튼 렌더링 (큼직한 터치 버튼 >= 56x44px, 볼드 15px + 네온 그린 3px 보더)
        top_font = config.get_font(15, bold=True)
        for btn_rect, tid in self.topping_buttons:
            t_meta = TOPPINGS.get(tid)
            t_name = str(t_meta["short_name"]) if t_meta else tid

            can_apply = any(
                d is not None and d.can_add_topping(tid) for d in self.dishes
            )
            bg_col = (42, 118, 82) if can_apply else (58, 52, 80)
            b_col = config.NEON_GREEN if can_apply else (112, 102, 144)

            pygame.draw.rect(surface, bg_col, btn_rect, border_radius=10)
            pygame.draw.rect(surface, b_col, btn_rect, width=3 if can_apply else 2, border_radius=10)

            badge_size = min(28, max(22, btn_rect.height - 14))
            draw_topping_badge(
                surface,
                (btn_rect.x + badge_size // 2 + 6, btn_rect.centery),
                tid,
                size=badge_size,
            )
            lbl_str = f"+{t_name}"
            active_t_font = top_font
            max_tw = btn_rect.width - badge_size - 10
            for f_sz in (15, 14, 13, 12):
                active_t_font = config.get_font(f_sz, bold=True)
                if active_t_font.size(lbl_str)[0] <= max_tw:
                    break
            t_surf = active_t_font.render(lbl_str, True, config.WHITE if can_apply else (232, 228, 246))
            surface.blit(
                t_surf,
                (
                    btn_rect.x + badge_size + 8,
                    btn_rect.centery - t_surf.get_height() // 2,
                ),
            )

        # 3. 하단 휴지통 즉시 비우기 & [🗑️ 버리기 모드] 토글 버튼 렌더링
        has_any_dish = any(d is not None for d in self.dishes)
        trash_bg = (168, 44, 52) if has_any_dish else (56, 52, 68)
        pygame.draw.rect(surface, trash_bg, self.trash_rect, border_radius=10)
        pygame.draw.rect(surface, config.RED if has_any_dish else config.UI_BORDER, self.trash_rect, width=2, border_radius=10)
        trash_lbl = font_sm.render("🗑️ 선택 접시 폐기", True, config.WHITE if has_any_dish else config.TEXT_SECONDARY)
        surface.blit(trash_lbl, trash_lbl.get_rect(center=self.trash_rect.center))

        mode_bg = (224, 52, 58) if self.trash_mode else (82, 46, 62)
        pygame.draw.rect(surface, mode_bg, self.trash_mode_rect, border_radius=10)
        pygame.draw.rect(surface, config.GOLD if self.trash_mode else config.UI_BORDER, self.trash_mode_rect, width=2, border_radius=10)
        mode_lbl = font_xs.render("🗑️ 버리기모드 ON" if self.trash_mode else "🗑️ 버리기 모드", True, config.WHITE)
        surface.blit(mode_lbl, mode_lbl.get_rect(center=self.trash_mode_rect.center))
