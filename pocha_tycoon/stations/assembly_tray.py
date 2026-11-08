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
            base_cnt = int(self.game_mgr.get_tray_slot_count()) if hasattr(self.game_mgr, "get_tray_slot_count") else 4
            return max(4, base_cnt)
        if self.game_mgr and hasattr(self.game_mgr, "get_tray_slot_count"):
            return max(4, int(self.game_mgr.get_tray_slot_count()))
        return max(4, config.BASE_TRAY_SLOTS)

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
            non_empty = [d for d in self.dishes if d is not None]
            target_len = max(desired, len(non_empty))
            self.dishes = non_empty + [None] * (target_len - len(non_empty))

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
        is_giant = r.height >= 500
        is_wide = r.width >= 520
        pad = 10 if is_giant else 5

        # 1. 상단 접시 슬롯 영역 (4종~12종 이상 다품종 대기 시에도 전종류가 한눈에 보이도록 그리드 최적화)
        slot_count = max(2, len(self.dishes))
        if is_wide:
            if slot_count <= 4:
                cols = slot_count
                rows = 1
            elif slot_count <= 8:
                cols = 4
                rows = 2
            else:
                cols = 4
                rows = (slot_count + 3) // 4
        else:
            if slot_count <= 3:
                cols = slot_count
                rows = 1
            elif slot_count == 4:
                cols = 2
                rows = 2
            elif slot_count <= 6:
                cols = 3
                rows = 2
            elif slot_count <= 8:
                cols = 4
                rows = 2
            else:
                cols = 4
                rows = (slot_count + 3) // 4

        plate_area_top = r.y + (60 if is_giant else 34)
        t_cnt = max(1, len(self.available_topping_ids))
        t_cols = min(4 if is_wide else 3, t_cnt)
        t_rows = (t_cnt + t_cols - 1) // t_cols

        if is_giant:
            trash_h = 72 if rows >= 2 else 82
            min_top_h = 74 if t_rows == 1 else 132
            plate_area_h = max(220, r.bottom - plate_area_top - min_top_h - trash_h - 24)
        else:
            trash_h = 36 if rows >= 2 else 40
            min_top_h = (48 if t_rows == 1 else 86) if rows >= 2 else (56 if t_rows == 1 else 96)
            plate_area_h = max(124, r.bottom - plate_area_top - min_top_h - trash_h - 14)

        self.slot_rects = []
        cell_w = max(48, (r.width - pad * (cols + 1)) // cols)
        cell_h = max(44, (plate_area_h - pad * (rows + 1)) // rows)

        for idx in range(slot_count):
            col = idx % cols
            row = idx // cols
            sx = r.x + pad + col * (cell_w + pad)
            sy = plate_area_top + pad + row * (cell_h + pad)
            self.slot_rects.append(pygame.Rect(sx, sy, cell_w, cell_h))

        # 2. 중단 토핑 버튼 영역
        topping_top = plate_area_top + plate_area_h + (6 if is_giant else 3)
        topping_area_h = max(44, r.bottom - topping_top - trash_h - (12 if is_giant else 8))

        self.topping_buttons = []
        t_w = max(56, (r.width - pad * (t_cols + 1)) // t_cols)
        t_h = max(38, (topping_area_h - pad * (t_rows + 1)) // max(1, t_rows))

        for idx, tid in enumerate(self.available_topping_ids):
            c = idx % t_cols
            rw = idx // t_cols
            bx = r.x + pad + c * (t_w + pad)
            by = topping_top + pad + rw * (t_h + pad)
            self.topping_buttons.append((pygame.Rect(bx, by, t_w, t_h), tid))

        # 3. 하단 휴지통(즉시 폐기) & [🗑️ 버리기 모드] 토글 버튼
        total_w = r.width - pad * 2
        left_w = int(total_w * 0.56)
        right_w = total_w - left_w - (10 if is_giant else 6)
        by_trash = r.bottom - trash_h - (8 if is_giant else 4)
        self.trash_rect = pygame.Rect(r.x + pad, by_trash, left_w, trash_h)
        self.trash_mode_rect = pygame.Rect(self.trash_rect.right + (10 if is_giant else 6), by_trash, right_w, trash_h)

    def has_empty_slot(self) -> bool:
        """
        무한 적재(Infinite Stocking) 시스템에 따라 동일 메뉴는 중첩되고
        신규 메뉴는 동적 슬롯에 적재되므로 항상 True를 반환한다.
        """
        return True

    def get_empty_slot_index(self) -> Optional[int]:
        """첫 번째 빈 접시 슬롯의 인덱스를 반환한다. 가득 찼으면 None 반환."""
        for idx, d in enumerate(self.dishes):
            if d is None:
                return idx
        return None

    def find_stack_slot(self, recipe_id: str, burnt: bool = False) -> Optional[int]:
        """동일한 recipe_id와 탄 상태(burnt)를 가진 접시 슬롯 인덱스를 반환한다."""
        if not recipe_id:
            return None
        for idx, d in enumerate(self.dishes):
            if d is not None and d.recipe_id == recipe_id and d.burnt == bool(burnt):
                return idx
        return None

    def _compact_overflow_slots(self) -> None:
        """기본 슬롯 수를 초과해 동적으로 늘어났던 빈 오버플로 슬롯을 정리한다."""
        desired = self._get_desired_slot_count()
        if len(self.dishes) <= desired:
            return
        non_empty = [d for d in self.dishes if d is not None]
        target_len = max(desired, len(non_empty))
        if target_len < len(self.dishes):
            self.dishes = non_empty + [None] * (target_len - len(non_empty))
            if self.selected_slot >= len(self.dishes):
                self.selected_slot = max(0, len(self.dishes) - 1)
            self._rebuild_layout()

    def get_total_dish_count(self) -> int:
        """현재 트레이에 적재된 모든 음식의 총 수량(스택 합계)을 반환한다."""
        return sum(max(1, int(d.quantity)) for d in self.dishes if d is not None)

    def get_total_stock_cost(self) -> int:
        """현재 트레이에 적재된 모든 음식의 재료 원가(마감 미판매 시 예상 폐기 손실) 합계를 반환한다."""
        return sum(d.get_total_cost(self.game_mgr) for d in self.dishes if d is not None)

    def add_dish(self, dish: Union[Dish, str]) -> bool:
        """
        트레이에 Dish 객체를 적재한다.
        1) 이미 동일한 메뉴(recipe_id, burnt 동일)가 놓인 슬롯이 있으면 해당 슬롯에 수량(+quantity)을 무한 중첩한다.
        2) 동일한 메뉴가 없으면 첫 번째 빈 슬롯에 올린다.
        3) 모든 기본 슬롯이 서로 다른 메뉴로 차 있으면 오버플로 슬롯을 동적 생성해 적재한다.
        """
        dish_obj = dish if isinstance(dish, Dish) else Dish(str(dish))
        add_qty = max(1, int(getattr(dish_obj, "quantity", 1)))

        # 1순위: 동일 메뉴가 이미 있으면 무한 스택 중첩
        stack_idx = self.find_stack_slot(dish_obj.recipe_id, dish_obj.burnt)
        if stack_idx is not None and self.dishes[stack_idx] is not None:
            self.dishes[stack_idx].quantity += add_qty
            self.selected_slot = stack_idx
            return True

        # 2순위: 비어 있는 기본 슬롯에 배치
        idx = self.get_empty_slot_index()
        if idx is not None:
            self.dishes[idx] = dish_obj
            self.selected_slot = idx
            return True

        # 3순위: 모든 슬롯이 서로 다른 메뉴로 차 있을 경우 동적 슬롯 확장
        self.dishes.append(dish_obj)
        self.selected_slot = len(self.dishes) - 1
        self._rebuild_layout()
        return True

    def remove_dish(self, slot_index: int, all_stack: bool = False) -> Optional[Dish]:
        """지정된 슬롯의 음식을 1개(또는 all_stack=True 시 전체 스택) 제거하고 반환한다."""
        if 0 <= slot_index < len(self.dishes):
            dish = self.dishes[slot_index]
            if dish is None:
                return None
            if not all_stack and dish.quantity > 1:
                dish.quantity -= 1
                return dish.copy(quantity=1)
            self.dishes[slot_index] = None
            self._compact_overflow_slots()
            return dish
        return None

    def clear_all(self) -> None:
        """모든 접시 슬롯을 비우고 기본 슬롯 수로 초기화한다."""
        desired = self._get_desired_slot_count()
        self.dishes = [None] * desired
        self.selected_slot = 0
        self._rebuild_layout()

    def _try_pull_ready_base_for_topping(
        self,
        topping_id: str,
        source_stations: Optional[Iterable[Any]] = None,
        customers: Optional[Iterable[Any]] = None,
    ) -> bool:
        """
        트레이에 해당 토핑을 얹을 베이스 음식이 없을 때,
        화로(SpecialistStation 등)에 완성(STATE_READY)된 호환 베이스 음식이 있으면 1개를 자동으로 트레이로 가져온다.
        """
        if not source_stations:
            return False
        from stations.base_station import STATE_READY

        wanted_rids = set()
        if customers:
            for c in customers:
                if c is not None and getattr(c, "state", "") == "WAITING":
                    for r_id in getattr(c, "orders", []):
                        wanted_rids.add(str(r_id))

        candidate_slots: List[Tuple[int, Any]] = []
        for st in source_stations:
            if st is None:
                continue
            for slot in getattr(st, "slots", []):
                if getattr(slot, "state", "") == STATE_READY and getattr(slot, "recipe_id", None):
                    probe = Dish(str(slot.recipe_id))
                    if probe.can_add_topping(topping_id):
                        probe_copy = probe.copy()
                        probe_copy.add_topping(topping_id)
                        priority = 0 if probe_copy.recipe_id in wanted_rids else 1
                        candidate_slots.append((priority, slot))

        if not candidate_slots:
            return False

        candidate_slots.sort(key=lambda item: item[0])
        chosen_slot = candidate_slots[0][1]
        pulled_rid = str(chosen_slot.recipe_id)
        if getattr(chosen_slot, "servings", 1) > 1:
            chosen_slot.servings -= 1
        else:
            chosen_slot.reset()
        self.add_dish(Dish(pulled_rid))
        return True

    def apply_topping(
        self,
        topping_id: str,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
        customers: Optional[Iterable[Any]] = None,
        source_stations: Optional[Iterable[Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        현재 트레이에 놓인 음식 중 해당 토핑을 추가할 수 있는 음식(손님 주문 매칭 슬롯 또는 선택된 슬롯 우선)에 토핑을 추가한다.
        - 만약 트레이에 호환 음식이 없고 조리 화로(source_stations)에 완성된 베이스 음식이 있으면 자동으로 1개를 가져와 토핑을 얹는다.
        - 토핑 적용 직후 대기 손님이 해당 완성 메뉴를 원하면 원터치로 즉시 자동 서빙한다!
        """
        if not self.dishes:
            return None

        if (
            self.game_mgr
            and hasattr(self.game_mgr, "is_slot_unlocked_in_story")
            and not self.game_mgr.is_slot_unlocked_in_story("tray")
        ):
            return {
                "action": "invalid_topping",
                "topping_id": topping_id,
                "message": "🔒 Day 3 해금: 직화 그릴 & 특제 토핑 추가",
            }

        has_compatible_on_tray = any(
            d is not None and d.can_add_topping(topping_id) for d in self.dishes
        )
        if not has_compatible_on_tray and source_stations:
            self._try_pull_ready_base_for_topping(topping_id, source_stations=source_stations, customers=customers)

        wanted_rids = set()
        if customers:
            for c in customers:
                if c is not None and getattr(c, "state", "") == "WAITING":
                    for r_id in getattr(c, "orders", []):
                        wanted_rids.add(str(r_id))

        base_order = [self.selected_slot] + [
            i for i in range(len(self.dishes)) if i != self.selected_slot
        ]
        # 손님이 현재 주문한 완성 메뉴가 되는 베이스 접시를 최우선 선택
        if wanted_rids:
            def _slot_priority(s_idx: int) -> int:
                if not (0 <= s_idx < len(self.dishes)):
                    return 99
                d_obj = self.dishes[s_idx]
                if d_obj is None or not d_obj.can_add_topping(topping_id):
                    return 99
                pr_copy = d_obj.copy(quantity=1)
                pr_copy.add_topping(topping_id)
                if pr_copy.recipe_id in wanted_rids:
                    return 0 if s_idx == self.selected_slot else 1
                return 2 if s_idx == self.selected_slot else 3

            order = sorted(base_order, key=_slot_priority)
        else:
            order = base_order

        for idx in order:
            if not (0 <= idx < len(self.dishes)):
                continue
            dish = self.dishes[idx]
            if dish is None or not dish.can_add_topping(topping_id):
                continue

            if dish.quantity > 1:
                # 스택에서 1개만 분리하여 토핑 적용
                dish.quantity -= 1
                single_topped = dish.copy(quantity=1)
                single_topped.add_topping(topping_id)

                merge_idx = self.find_stack_slot(single_topped.recipe_id, single_topped.burnt)
                if merge_idx is not None and self.dishes[merge_idx] is not None:
                    self.dishes[merge_idx].quantity += 1
                    target_idx = merge_idx
                    target_dish = self.dishes[merge_idx]
                else:
                    empty_idx = self.get_empty_slot_index()
                    if empty_idx is not None:
                        self.dishes[empty_idx] = single_topped
                        target_idx = empty_idx
                    else:
                        self.dishes.append(single_topped)
                        target_idx = len(self.dishes) - 1
                        self._rebuild_layout()
                    target_dish = single_topped
            else:
                # 단일 접시(x1)에 토핑 적용 후 기존 동일 메뉴 스택이 있으면 자동 병합
                dish.add_topping(topping_id)
                target_idx = idx
                target_dish = dish
                for other_idx, other_d in enumerate(self.dishes):
                    if (
                        other_idx != idx
                        and other_d is not None
                        and other_d.recipe_id == dish.recipe_id
                        and other_d.burnt == dish.burnt
                    ):
                        other_d.quantity += 1
                        self.dishes[idx] = None
                        self._compact_overflow_slots()
                        found_idx = self.find_stack_slot(other_d.recipe_id, other_d.burnt)
                        target_idx = found_idx if found_idx is not None else 0
                        target_dish = other_d
                        break

            self.selected_slot = target_idx
            # 원터치 편의성 강화: 토핑 적용 즉시 해당 완성 메뉴를 기다리는 손님이 있으면 바로 자동 서빙!
            if auto_serve_cb is not None and 0 <= target_idx < len(self.dishes) and self.dishes[target_idx] is not None:
                s_center = (
                    self.slot_rects[target_idx].center
                    if target_idx < len(self.slot_rects)
                    else self.rect.center
                )
                served, serve_res = invoke_auto_serve(
                    auto_serve_cb,
                    target_dish.recipe_id,
                    s_center,
                )
                if served:
                    served_unit = target_dish.copy(quantity=1)
                    if target_dish.quantity > 1:
                        target_dish.quantity -= 1
                    else:
                        self.dishes[target_idx] = None
                        self._compact_overflow_slots()
                    return {
                        "action": "auto_served",
                        "topping_id": topping_id,
                        "slot_index": target_idx,
                        "recipe_id": served_unit.recipe_id,
                        "dish": served_unit,
                        "serve_result": serve_res,
                    }

            return {
                "action": "add_topping",
                "topping_id": topping_id,
                "recipe_id": target_dish.recipe_id,
                "slot_index": target_idx,
                "dish": target_dish,
            }

        # 만약 완성된 베이스 음식이 아직 없을 때 장인 화로(source_stations)에 해당 베이스가 조리 중이지 않다면
        # 필요한 베이스 레시피를 빈 화로 칸에 자동으로 조리 시작해 준다!
        from data.recipes import RECIPES

        req_base_rid: Optional[str] = None
        for r_id, r_data in RECIPES.items():
            if topping_id in r_data.get("required_toppings", []):
                req_base_rid = str(r_data.get("base_recipe_id", ""))
                break

        if req_base_rid and source_stations:
            base_rec = RECIPES.get(req_base_rid)
            base_name = str(base_rec["name"]) if base_rec else req_base_rid
            for st in source_stations:
                if st is not None and hasattr(st, "start_cooking_recipe") and hasattr(st, "spec_data"):
                    allowed_bases = list(st.spec_data.get("base_recipes", []))
                    if req_base_rid in allowed_bases:
                        already_cooking = any(
                            getattr(sl, "recipe_id", None) == req_base_rid and getattr(sl, "state", "") != "IDLE"
                            for sl in getattr(st, "slots", [])
                        )
                        if not already_cooking:
                            started_slot = st.start_cooking_recipe(req_base_rid)
                            if started_slot is not None:
                                return {
                                    "action": "invalid_topping",
                                    "topping_id": topping_id,
                                    "message": f"🔥 [{base_name}] #{started_slot.slot_index + 1}번 칸 자동 조리 시작! 완성 후 토핑하세요!",
                                }
                        return {
                            "action": "invalid_topping",
                            "topping_id": topping_id,
                            "message": f"⏳ [{base_name}] 조리 중! 완성 후 터치하면 즉시 토핑·서빙됩니다!",
                        }

        return {
            "action": "invalid_topping",
            "topping_id": topping_id,
            "message": "해당 토핑을 추가할 수 있는 음식이 없습니다.",
        }

    def _trash_one_from_slot(self, idx: int) -> Optional[Dict[str, Any]]:
        """지정한 슬롯에서 음식 1개를 폐기하고 폐기 손실 메타데이터를 반환한다."""
        if not (0 <= idx < len(self.dishes)) or self.dishes[idx] is None:
            return None
        dish = self.dishes[idx]
        assert dish is not None
        removed_unit = dish.copy(quantity=1)
        if dish.quantity > 1:
            dish.quantity -= 1
        else:
            self.dishes[idx] = None
            self._compact_overflow_slots()
        return {
            "action": "trash_dish",
            "slot_index": idx,
            "recipe_id": removed_unit.recipe_id,
            "dish": removed_unit,
            "discard_count": 1,
            "cost": removed_unit.get_cost(self.game_mgr),
        }

    def trash_selected_or_first(self) -> Optional[Dict[str, Any]]:
        """선택된 슬롯(우선) 또는 음식이 놓인 첫 번째 슬롯의 음식을 1개 폐기한다."""
        order = [self.selected_slot] + [
            i for i in range(len(self.dishes)) if i != self.selected_slot
        ]
        for idx in order:
            if 0 <= idx < len(self.dishes) and self.dishes[idx] is not None:
                res = self._trash_one_from_slot(idx)
                if res is not None:
                    return res
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
        """0.35초 롱프레스 유지 시 접시 음식을 1개 즉시 폐기한다."""
        if self.hold_slot_idx is not None:
            idx = self.hold_slot_idx
            if 0 <= idx < len(self.dishes) and self.dishes[idx] is not None:
                self.hold_timer += max(0.0, float(dt))
                if self.hold_timer >= self.LONG_PRESS_DURATION:
                    s_rect = self.slot_rects[idx] if idx < len(self.slot_rects) else self.rect
                    center_pos = s_rect.center
                    trash_res = self._trash_one_from_slot(idx)
                    self.hold_slot_idx = None
                    self.hold_timer = 0.0
                    self._suppress_next_click = True
                    if trash_res is not None:
                        trash_res["pos"] = center_pos
                        self._pending_hold_feedback = trash_res
            else:
                self.hold_slot_idx = None
                self.hold_timer = 0.0

    def handle_click(
        self,
        pos: Tuple[int, int],
        auto_serve_cb: Optional[Callable[..., Any]] = None,
        button: int = 1,
        customers: Optional[Iterable[Any]] = None,
        source_stations: Optional[Iterable[Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        조립 트레이 클릭 인터랙션을 처리한다.
        - 접시 슬롯 클릭:
          * 우클릭(button == 3), [X] 배지 클릭, 또는 [🗑️ 버리기 모드] 활성 상태: 해당 접시 음식 1개 즉시 폐기(원가 손실 발생).
          * 좌클릭(button == 1): auto_serve_cb(dish.recipe_id, slot_center)를 호출해
            해당 메뉴를 기다리는 손님에게 스택에서 1개 즉시 자동 서빙!
        - 토핑 버튼 클릭(inflate(8, 8)): 선택된 슬롯(우선) 또는 화로 완성 슬롯의 음식 1개에 토핑을 얹고,
          주문 손님이 있으면 원터치로 즉시 자동 서빙!
        - 휴지통 버튼 클릭: 선택된/첫 번째 접시 음식 1개 폐기 또는 [🗑️ 버리기 모드] 토글.
        """
        self._ensure_layout()
        if self._suppress_next_click:
            self._suppress_next_click = False
            return None
        if not self.rect.inflate(8, 8).collidepoint(pos):
            return None

        # 1. 접시 슬롯 클릭 확인 (우측 상단 [X] 배지 + 버리기 모드 + 슬롯 터치 판정 여유 확보)
        for idx, s_rect in enumerate(self.slot_rects):
            if not s_rect.inflate(6, 6).collidepoint(pos):
                continue

            dish = self.dishes[idx] if idx < len(self.dishes) else None
            self.selected_slot = idx

            if dish is None:
                return {
                    "action": "select_empty_slot",
                    "slot_index": idx,
                }

            is_compact = s_rect.height < 88 or s_rect.width < 115
            del_w = 36 if self.rect.height >= 500 else (22 if is_compact else 28)
            del_badge_rect = pygame.Rect(s_rect.right - del_w - 3, s_rect.y + 3, del_w, del_w)
            if button == 3 or self.trash_mode or del_badge_rect.inflate(6, 6).collidepoint(pos):
                self.trash_mode = False
                return self._trash_one_from_slot(idx)

            # 좌클릭/터치 시 원터치 자동 서빙 시도 (스택에서 1개만 차감)
            served, serve_res = invoke_auto_serve(
                auto_serve_cb,
                dish.recipe_id,
                s_rect.center,
            )
            if served:
                served_unit = dish.copy(quantity=1)
                if dish.quantity > 1:
                    dish.quantity -= 1
                else:
                    self.dishes[idx] = None
                    self._compact_overflow_slots()
                return {
                    "action": "auto_served",
                    "slot_index": idx,
                    "recipe_id": served_unit.recipe_id,
                    "dish": served_unit,
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
                return self.apply_topping(
                    tid,
                    auto_serve_cb=auto_serve_cb,
                    customers=customers,
                    source_stations=source_stations,
                )

        # 3. [🗑️ 버리기 모드] 토글 버튼 터치 확인
        if self.trash_mode_rect.inflate(6, 6).collidepoint(pos):
            self.trash_mode = not self.trash_mode
            return {
                "action": "toggle_trash_mode",
                "trash_mode": self.trash_mode,
                "message": "🗑️ 버리기 모드 ON: 폐기할 접시를 터치하세요! (원가 손실 발생)" if self.trash_mode else "버리기 모드 해제",
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
        is_mobile = bool(
            getattr(config, "is_mobile_ui", lambda: config.WINDOW_HEIGHT > config.WINDOW_WIDTH)()
        )
        is_giant = self.rect.height >= 500
        pygame.draw.rect(surface, config.UI_PANEL, self.rect, border_radius=14 if is_giant else 12)
        pygame.draw.rect(surface, config.UI_HIGHLIGHT, self.rect, width=3 if is_giant else 2, border_radius=14 if is_giant else 12)

        total_cnt = self.get_total_dish_count()
        total_cost = self.get_total_stock_cost()
        occupied_types = sum(1 for d in self.dishes if d is not None)

        # 상단 헤더 (재고 수량, 종류 수 및 마감 시 예상 원가 손실 실시간 표시)
        header_rect = pygame.Rect(
            self.rect.x + (6 if is_giant else 4),
            self.rect.y + (6 if is_giant else 4),
            self.rect.width - (12 if is_giant else 8),
            50 if is_giant else 28,
        )
        pygame.draw.rect(surface, (62, 42, 32), header_rect, border_radius=10 if is_giant else 8)
        pygame.draw.rect(surface, config.GOLD, header_rect, width=2 if is_giant else 1, border_radius=10 if is_giant else 8)
        if is_giant:
            lvl = (
                int(self.game_mgr.get_station_level("tray"))
                if (self.game_mgr and hasattr(self.game_mgr, "get_station_level"))
                else 1
            )
            if total_cnt > 0:
                hdr_txt = f"🍱 Lv.{lvl} 음식 대기 {occupied_types}종 ({total_cnt}개) · 미판매 원가 -{total_cost:,}원"
                hdr_col = (255, 162, 128) if total_cnt >= 4 else config.GOLD
            else:
                hdr_txt = f"🍱 Lv.{lvl} 조립 & 음식 대기 트레이 (다품종 4~8종+ 무한 적재)"
                hdr_col = config.GOLD
            m_font = config.get_font(18, bold=True)
            if m_font.size(hdr_txt)[0] > header_rect.width - 16:
                m_font = config.get_font(15, bold=True)
            m_surf = m_font.render(hdr_txt, True, hdr_col)
            surface.blit(m_surf, m_surf.get_rect(center=header_rect.center))
        elif is_mobile or self.rect.width >= 520:
            lvl = (
                int(self.game_mgr.get_station_level("tray"))
                if (self.game_mgr and hasattr(self.game_mgr, "get_station_level"))
                else 1
            )
            if total_cnt > 0:
                hdr_txt = f"🍱 음식 대기 {occupied_types}종 · 총 {total_cnt}개 (미판매 시 -{total_cost:,}원) · 터치 즉시서빙"
                hdr_col = (255, 162, 128) if total_cnt >= 4 else config.GOLD
            else:
                hdr_txt = f"🍱 ③ 원터치 토핑 & 음식 대기 트레이 (Lv.{lvl} · 토핑 터치 시 즉시 조립·서빙!)"
                hdr_col = config.GOLD
            m_font = config.get_font(13, bold=True)
            if m_font.size(hdr_txt)[0] > header_rect.width - 12:
                m_font = config.get_font(12, bold=True)
            m_surf = m_font.render(hdr_txt, True, hdr_col)
            surface.blit(m_surf, m_surf.get_rect(center=header_rect.center))
        else:
            title_font = config.get_font(13, bold=True)
            if total_cnt > 0:
                raw_title = f"🍱 대기 {occupied_types}종/{total_cnt}개 (미판매 시 -{total_cost:,}원)"
                hdr_col = (255, 162, 128) if total_cnt >= 4 else config.GOLD
            elif self.game_mgr and str(getattr(self.game_mgr, "mode", "")).upper() == "SPECIALIST":
                spec_title = str(self.game_mgr.get_selected_specialist_data().get("tray_title", "③ 토핑·소스 & 포장 서빙대"))
                raw_title = f"{spec_title} (다품종 적재)"
                hdr_col = config.GOLD
            else:
                raw_title = "🍱 조립 & 서빙 트레이 (다품종 무한 적재)"
                hdr_col = config.GOLD
            title_surf = title_font.render(raw_title, True, hdr_col)
            if title_surf.get_width() > header_rect.width - 10:
                title_surf = config.get_font(11, bold=True).render(raw_title, True, hdr_col)
            surface.blit(
                title_surf,
                (
                    header_rect.centerx - title_surf.get_width() // 2,
                    header_rect.centery - title_surf.get_height() // 2,
                ),
            )

        font_xs = config.get_font(15 if is_giant else 12, bold=True)

        # 1. 접시 슬롯 렌더링 (4종~12종 이상 다품종 대기 시에도 아이콘·수량·메뉴명이 겹치지 않도록 자동 스케일링)
        for idx, s_rect in enumerate(self.slot_rects):
            is_sel = idx == self.selected_slot
            is_compact = s_rect.height < 88 or s_rect.width < 115
            draw_station_hardware(surface, s_rect, station_type="tray")
            border_col = config.NEON_YELLOW if is_sel else (112, 92, 74)
            pygame.draw.rect(surface, border_col, s_rect, width=2 if is_sel else 1, border_radius=10 if is_giant else 8)

            dish = self.dishes[idx] if idx < len(self.dishes) else None
            if dish is not None:
                lbl_h = 28 if is_giant else (17 if is_compact else 21)
                badge_h = 28 if is_giant else (18 if is_compact else 22)
                del_w = 32 if is_giant else (20 if is_compact else 24)
                avail_icon_h = max(22, s_rect.height - lbl_h - 6)
                icon_size = min(
                    84 if is_giant else (38 if is_compact else 52),
                    max(24, min(s_rect.width - 10, avail_icon_h)),
                )
                icon_cy = s_rect.y + avail_icon_h // 2 + (2 if is_compact else 0)

                # 다중 스택(x2 이상)일 때 접시 겹침 연출
                if dish.quantity > 1:
                    stack_layers = min(2 if is_compact else 3, dish.quantity - 1)
                    for s_lv in range(stack_layers, 0, -1):
                        pygame.draw.circle(
                            surface,
                            (218, 206, 188),
                            (s_rect.centerx - s_lv * 3, icon_cy + s_lv * 2),
                            icon_size // 2 + 2,
                            width=2,
                        )
                if dish.has_topping:
                    pygame.draw.circle(surface, config.GOLD, (s_rect.centerx, icon_cy), icon_size // 2 + 3, width=2)
                dish.draw(surface, (s_rect.centerx, icon_cy), size=icon_size)

                # 좌측 상단 무한 스택 수량 배지 (x1, x2, x5...)
                qty = max(1, int(dish.quantity))
                qty_str = f"x{qty}"
                qty_f = config.get_font(
                    (16 if qty < 10 else 14) if is_giant else ((11 if is_compact else 13) if qty < 10 else 10),
                    bold=True,
                )
                qty_w = max(28 if is_giant else (22 if is_compact else 28), qty_f.size(qty_str)[0] + (10 if is_giant else 6))
                qty_badge = pygame.Rect(s_rect.x + 3, s_rect.y + 3, qty_w, badge_h)
                qty_bg = (228, 72, 32) if qty >= 4 else ((218, 126, 28) if qty >= 2 else (44, 58, 86))
                pygame.draw.rect(surface, qty_bg, qty_badge, border_radius=6)
                pygame.draw.rect(
                    surface,
                    config.GOLD if qty >= 2 else config.NEON_CYAN,
                    qty_badge,
                    width=1,
                    border_radius=6,
                )
                qty_surf = qty_f.render(qty_str, True, config.WHITE)
                surface.blit(qty_surf, qty_surf.get_rect(center=qty_badge.center))

                # 우측 상단 모바일 원터치 폐기 [✕] 배지
                del_badge = pygame.Rect(s_rect.right - del_w - 3, s_rect.y + 3, del_w, badge_h)
                pygame.draw.rect(surface, (228, 42, 52) if self.trash_mode else (196, 36, 46), del_badge, border_radius=6)
                pygame.draw.rect(surface, config.GOLD if self.trash_mode else config.WHITE, del_badge, width=1, border_radius=6)
                x_s = config.get_font(16 if is_giant else (11 if is_compact else 13), bold=True).render("✕", True, config.WHITE)
                surface.blit(x_s, x_s.get_rect(center=del_badge.center))

                # 0.35초 롱프레스 진행 중일 때 게이지 표시
                if self.hold_slot_idx == idx and self.hold_timer > 0.04:
                    hold_ratio = min(1.0, self.hold_timer / max(0.1, self.LONG_PRESS_DURATION))
                    hbar = pygame.Rect(s_rect.x + 4, s_rect.y + 4, max(20, s_rect.width - del_w - 10), 10)
                    pygame.draw.rect(surface, (24, 18, 28), hbar, border_radius=5)
                    pygame.draw.rect(surface, config.RED, (hbar.x, hbar.y, int(hbar.width * hold_ratio), hbar.height), border_radius=5)
                    pygame.draw.rect(surface, config.WHITE, hbar, width=1, border_radius=5)

                name_txt = (
                    dish.name.replace("갈릭버터 큐브스테이크", "갈릭스테이크")
                    .replace("오리지널 큐브스테이크", "큐브스테이크")
                    .replace("스위트 칠리 지파이", "칠리지파이")
                    .replace("마라 시즈닝 지파이", "마라지파이")
                    .replace("크리스피 대왕 지파이", "대왕지파이")
                    .replace(" 붕어빵", "붕어")
                    .replace(" 어묵", "어묵")
                ) if is_compact else (
                    dish.name.replace("갈릭버터 큐브스테이크", "갈릭 큐브스테이크")
                    .replace("오리지널 큐브스테이크", "큐브스테이크")
                    .replace("스위트 칠리 지파이", "칠리 지파이")
                    .replace("마라 시즈닝 지파이", "마라 지파이")
                    .replace("크리스피 대왕 지파이", "대왕 지파이")
                )
                lbl_bg = pygame.Rect(s_rect.x + 3, s_rect.bottom - lbl_h - 2, s_rect.width - 6, lbl_h)
                pygame.draw.rect(surface, (18, 14, 26), lbl_bg, border_radius=6)
                pygame.draw.rect(surface, config.GOLD if dish.has_topping else config.UI_BORDER, lbl_bg, width=1, border_radius=6)
                dish_font = font_xs
                sz_list = (16, 15, 14, 13, 12) if is_giant else ((12, 11, 10) if is_compact else (13, 12, 11, 10))
                for f_sz in sz_list:
                    dish_font = config.get_font(f_sz, bold=True)
                    if dish_font.size(name_txt)[0] <= lbl_bg.width - 6:
                        break
                if dish_font.size(name_txt)[0] > lbl_bg.width - 4:
                    while len(name_txt) > 3 and dish_font.size(name_txt)[0] > lbl_bg.width - 6:
                        name_txt = name_txt[:-1]
                lbl_surf = dish_font.render(name_txt, True, config.GOLD if dish.has_topping else config.WHITE)
                surface.blit(
                    lbl_surf,
                    (lbl_bg.centerx - lbl_surf.get_width() // 2, lbl_bg.centery - lbl_surf.get_height() // 2),
                )
            else:
                pw = min(s_rect.width - 10, 110 if is_giant else (64 if is_compact else 80))
                ph = 30 if is_giant else (20 if is_compact else 24)
                empty_pill = pygame.Rect(s_rect.centerx - pw // 2, s_rect.centery - ph // 2, pw, ph)
                pygame.draw.rect(surface, (34, 28, 44), empty_pill, border_radius=6)
                e_font = config.get_font(14 if is_giant else (11 if is_compact else 12), bold=True)
                empty_surf = e_font.render(f"대기칸 {idx + 1}", True, (192, 182, 212))
                surface.blit(
                    empty_surf,
                    (empty_pill.centerx - empty_surf.get_width() // 2, empty_pill.centery - empty_surf.get_height() // 2),
                )

        # 2. 토핑 버튼 렌더링 (스토리 모드 Day 1~2에서 토핑 미해금 시 안내 배너 표시)
        toppings_unlocked = not (
            self.game_mgr
            and hasattr(self.game_mgr, "is_slot_unlocked_in_story")
            and not self.game_mgr.is_slot_unlocked_in_story("tray")
        )
        if not toppings_unlocked and self.topping_buttons:
            first_r = self.topping_buttons[0][0]
            last_r = self.topping_buttons[-1][0]
            lock_area = pygame.Rect(
                self.rect.x + 8,
                first_r.y,
                self.rect.width - 16,
                last_r.bottom - first_r.y,
            )
            pygame.draw.rect(surface, (28, 26, 46), lock_area, border_radius=12)
            pygame.draw.rect(surface, (112, 102, 152), lock_area, width=2, border_radius=12)
            lk_f1 = config.get_font(20 if is_giant else 15, bold=True)
            lk_f2 = config.get_font(16 if is_giant else 13, bold=True)
            s1 = lk_f1.render("🔒 Day 3 해금: 특제 소스·토핑 조립", True, config.GOLD)
            s2 = lk_f2.render("현재는 구운 음식을 무한 적재하고 터치해 서빙할 수 있습니다!", True, config.NEON_CYAN)
            if s2.get_width() > lock_area.width - 12:
                s2 = config.get_font(13 if is_giant else 11, bold=True).render("구운 음식을 무한 적재하고 터치해 즉시 서빙하세요!", True, config.NEON_CYAN)
            surface.blit(s1, s1.get_rect(center=(lock_area.centerx, lock_area.centery - (18 if is_giant else 12))))
            surface.blit(s2, s2.get_rect(center=(lock_area.centerx, lock_area.centery + (18 if is_giant else 14))))
        else:
            top_font = config.get_font(19 if is_giant else 15, bold=True)
            for btn_rect, tid in self.topping_buttons:
                t_meta = TOPPINGS.get(tid)
                t_name = str(t_meta["short_name"]) if t_meta else tid

                can_apply = any(
                    d is not None and d.can_add_topping(tid) for d in self.dishes
                )
                bg_col = (42, 118, 82) if can_apply else (58, 52, 80)
                b_col = config.NEON_GREEN if can_apply else (112, 102, 144)

                pygame.draw.rect(surface, bg_col, btn_rect, border_radius=12 if is_giant else 10)
                pygame.draw.rect(surface, b_col, btn_rect, width=3 if can_apply else 2, border_radius=12 if is_giant else 10)

                badge_size = min(44 if is_giant else 28, max(22, btn_rect.height - 14))
                draw_topping_badge(
                    surface,
                    (btn_rect.x + badge_size // 2 + (10 if is_giant else 6), btn_rect.centery),
                    tid,
                    size=badge_size,
                )
                lbl_str = f"+{t_name}"
                active_t_font = top_font
                max_tw = btn_rect.width - badge_size - (16 if is_giant else 10)
                for f_sz in ((19, 18, 17, 16, 15) if is_giant else (15, 14, 13, 12)):
                    active_t_font = config.get_font(f_sz, bold=True)
                    if active_t_font.size(lbl_str)[0] <= max_tw:
                        break
                t_surf = active_t_font.render(lbl_str, True, config.WHITE if can_apply else (232, 228, 246))
                surface.blit(
                    t_surf,
                    (
                        btn_rect.x + badge_size + (14 if is_giant else 8),
                        btn_rect.centery - t_surf.get_height() // 2,
                    ),
                )

        # 3. 하단 휴지통 즉시 비우기(1개 폐기 시 원가 표시) & [🗑️ 버리기 모드] 토글 버튼 렌더링
        has_any_dish = any(d is not None for d in self.dishes)
        sel_dish = (
            self.dishes[self.selected_slot]
            if (0 <= self.selected_slot < len(self.dishes) and self.dishes[self.selected_slot] is not None)
            else next((d for d in self.dishes if d is not None), None)
        )
        sel_unit_cost = sel_dish.get_cost(self.game_mgr) if sel_dish is not None else 0

        trash_bg = (168, 44, 52) if has_any_dish else (56, 52, 68)
        pygame.draw.rect(surface, trash_bg, self.trash_rect, border_radius=12 if is_giant else 10)
        pygame.draw.rect(surface, config.RED if has_any_dish else config.UI_BORDER, self.trash_rect, width=2, border_radius=12 if is_giant else 10)

        mode_bg = (224, 52, 58) if self.trash_mode else (82, 46, 62)
        pygame.draw.rect(surface, mode_bg, self.trash_mode_rect, border_radius=12 if is_giant else 10)
        pygame.draw.rect(surface, config.GOLD if self.trash_mode else config.UI_BORDER, self.trash_mode_rect, width=2, border_radius=12 if is_giant else 10)

        if has_any_dish and sel_unit_cost > 0:
            trash_txt_str = f"🗑️ 1개 폐기 (-{sel_unit_cost:,}원)"
        else:
            trash_txt_str = "🗑️ 선택 접시 폐기"
        t_font = config.get_font(18 if is_giant else (13 if len(trash_txt_str) > 12 else 14), bold=True)
        trash_lbl = t_font.render(trash_txt_str, True, config.WHITE if has_any_dish else config.TEXT_SECONDARY)
        surface.blit(trash_lbl, trash_lbl.get_rect(center=self.trash_rect.center))

        mode_lbl = config.get_font(18 if is_giant else 13, bold=True).render(
            "🗑️ 버리기모드 ON" if self.trash_mode else "🗑️ 버리기 모드",
            True,
            config.WHITE,
        )
        surface.blit(mode_lbl, mode_lbl.get_rect(center=self.trash_mode_rect.center))
