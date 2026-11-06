"""
entities/customer.py
손님 유형 4종(학생, 야근 직장인, 외국인 관광객 VIP, 맛집 유튜버 VIP),
다중 메뉴 주문 말풍선, 인내심 게이지, 감정 상태, 서빙 보상 및 피버 발동 판정 모듈.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import pygame

import config
from core.art_renderer import draw_customer, draw_food_icon
from core.game_manager import GameManager
from data.characters import AttrDict
from data.recipes import RECIPES


CUSTOMER_TYPES: Dict[str, Dict[str, Any]] = {
    "student": {
        "id": "student",
        "name": "학생",
        "badge": "학생",
        "base_patience": 28.0,
        "tip_mult": 1.0,
        "is_vip": False,
        "triggers_fever": False,
        "badge_color": (72, 138, 235),
        "preferred_order_count": (1, 1),
    },
    "worker": {
        "id": "worker",
        "name": "야근 직장인",
        "badge": "직장인",
        "base_patience": 21.0,
        "tip_mult": 1.8,
        "is_vip": False,
        "triggers_fever": False,
        "badge_color": (235, 132, 48),
        "preferred_order_count": (1, 2),
    },
    "tourist": {
        "id": "tourist",
        "name": "외국인 관광객",
        "badge": "관광객 VIP",
        "base_patience": 33.0,
        "tip_mult": 1.6,
        "is_vip": True,
        "triggers_fever": False,
        "badge_color": (42, 195, 185),
        "preferred_order_count": (2, 2),
    },
    "youtuber": {
        "id": "youtuber",
        "name": "맛집 유튜버 VIP",
        "badge": "유튜버 VIP",
        "base_patience": 26.0,
        "tip_mult": 2.0,
        "is_vip": True,
        "triggers_fever": True,
        "badge_color": (195, 68, 245),
        "preferred_order_count": (2, 2),
    },
}


def compute_customer_slot_rect(slot_index: int, max_slots: int = 4) -> pygame.Rect:
    """슬롯 인덱스(0~3)에 따른 기본 손님 영역 Rect를 계산한다."""
    max_slots = max(3, min(4, int(max_slots)))
    margin_x = 48
    usable_w = config.SCREEN_WIDTH - margin_x * 2
    slot_w = usable_w // max_slots
    x = margin_x + int(slot_index) * slot_w + (slot_w - 260) // 2
    y = config.CUSTOMER_AREA_TOP + 12
    return pygame.Rect(x, y, 260, config.CUSTOMER_AREA_HEIGHT - 18)


class Customer:
    """
    포장마차를 방문하는 손님 엔티티.
    - 유형: 'student', 'worker', 'tourist', 'youtuber'
    - 상태: 'WAITING' -> 'SATISFIED' 또는 'ANGRY_LEFT'
    """

    def __init__(
        self,
        slot_index: int = 0,
        customer_type: str = "student",
        orders: Optional[List[str]] = None,
        max_patience: Optional[float] = None,
        rect: Optional[Union[pygame.Rect, Tuple[int, int, int, int]]] = None,
        game_mgr: Any = None,
    ) -> None:
        self.slot_index: int = int(slot_index)
        ctype = str(customer_type).lower()
        if ctype not in CUSTOMER_TYPES:
            ctype = "student"
        self.customer_type: str = ctype

        meta = CUSTOMER_TYPES[self.customer_type]
        self.name: str = str(meta["name"])
        self.badge_text: str = str(meta["badge"])
        self.badge_color: Tuple[int, int, int] = tuple(meta["badge_color"])  # type: ignore[assignment]
        self.tip_mult: float = float(meta["tip_mult"])
        self.is_vip: bool = bool(meta["is_vip"])
        self.triggers_fever: bool = bool(meta["triggers_fever"])

        mgr = game_mgr or GameManager.get_instance()
        if orders is None:
            orders = self._generate_orders_for_type(self.customer_type, mgr)
        self.orders: List[str] = [str(r) for r in orders if r]
        if not self.orders:
            self.orders = ["bungeoppang_redbean"]

        self.initial_orders: List[str] = list(self.orders)
        self.completed_orders: List[str] = []

        if max_patience is None:
            patience_mult = (
                mgr.get_customer_patience_multiplier()
                if mgr and hasattr(mgr, "get_customer_patience_multiplier")
                else 1.0
            )
            max_patience = float(meta["base_patience"]) * float(patience_mult)

        self.max_patience: float = max(5.0, round(float(max_patience), 2))
        self.patience: float = self.max_patience

        max_slots = (
            mgr.get_max_customer_slots()
            if mgr and hasattr(mgr, "get_max_customer_slots")
            else 4
        )
        if rect is not None:
            self.rect: pygame.Rect = (
                rect.copy() if isinstance(rect, pygame.Rect) else pygame.Rect(rect)
            )
        else:
            self.rect = compute_customer_slot_rect(self.slot_index, max_slots=max_slots)

        # 상태 머신: 생성 즉시 주문을 받을 수 있도록 WAITING 상태로 시작하되, 입장 연출 타이머를 둔다.
        self.state: str = "WAITING"
        self.enter_timer: float = 0.30
        self.leave_timer: float = 0.0
        self.ready_to_remove: bool = False
        self._angry_event_emitted: bool = False

    @classmethod
    def create_random(
        cls,
        slot_index: int,
        game_mgr: Any = None,
        rect: Optional[Union[pygame.Rect, Tuple[int, int, int, int]]] = None,
        rng: Optional[Any] = None,
    ) -> "Customer":
        """
        현재 GameManager의 활성 레시피, VIP 등장 확률, 인내심 배율을 반영하여
        무작위 손님 인스턴스를 생성한다.
        """
        r = rng if rng is not None else random
        mgr = game_mgr or GameManager.get_instance()
        vip_chance = (
            float(mgr.get_vip_spawn_chance())
            if mgr and hasattr(mgr, "get_vip_spawn_chance")
            else config.BASE_VIP_CHANCE
        )

        roll = r.random()
        is_story_early_kr = (
            mgr is not None
            and getattr(mgr, "mode", "") == "WORLD_TOUR"
            and getattr(mgr, "current_chapter", "") == "KR"
            and int(getattr(mgr, "day", 1)) in (1, 2)
        )
        is_story_day5_kr = (
            mgr is not None
            and getattr(mgr, "mode", "") == "WORLD_TOUR"
            and getattr(mgr, "current_chapter", "") == "KR"
            and int(getattr(mgr, "day", 1)) == 5
        )
        if is_story_early_kr:
            customer_type = "student" if r.random() < (0.75 if int(getattr(mgr, "day", 1)) == 1 else 0.55) else "worker"
        elif roll < (max(vip_chance, 0.28) if is_story_day5_kr else vip_chance):
            # VIP 풀: 외국인 관광객(58%) vs 맛집 유튜버 VIP(42%), KR Day 5는 유튜버 비중 강화
            youtuber_prob = 0.70 if is_story_day5_kr else 0.42
            customer_type = "youtuber" if r.random() < youtuber_prob else "tourist"
        else:
            # 일반 손님 풀: 학생(55%) vs 야근 직장인(45%)
            customer_type = "student" if r.random() < 0.55 else "worker"

        orders = cls._generate_orders_for_type(customer_type, mgr, rng=r)
        patience_mult = (
            float(mgr.get_customer_patience_multiplier())
            if mgr and hasattr(mgr, "get_customer_patience_multiplier")
            else 1.0
        )
        base_pat = float(CUSTOMER_TYPES[customer_type]["base_patience"])
        max_patience = round(base_pat * patience_mult, 2)

        return cls(
            slot_index=slot_index,
            customer_type=customer_type,
            orders=orders,
            max_patience=max_patience,
            rect=rect,
            game_mgr=mgr,
        )

    @staticmethod
    def _generate_orders_for_type(
        customer_type: str,
        game_mgr: Any = None,
        rng: Optional[Any] = None,
    ) -> List[str]:
        """손님 유형별 선호도에 맞춰 1~2개의 주문 레시피 ID 리스트를 생성한다."""
        r = rng if rng is not None else random
        mgr = game_mgr or GameManager.get_instance()
        if mgr and hasattr(mgr, "get_orderable_recipes"):
            active_recipes = mgr.get_orderable_recipes(base_only=False)
        elif mgr and hasattr(mgr, "get_active_recipes"):
            active_recipes = mgr.get_active_recipes(base_only=False)
        else:
            active_recipes = list(RECIPES.values())
        if not active_recipes:
            active_recipes = list(RECIPES.values())

        all_ids = [str(rec["id"]) for rec in active_recipes]
        food_ids = [str(rec["id"]) for rec in active_recipes if rec.get("slot_type") != "dispenser"]
        drink_ids = [str(rec["id"]) for rec in active_recipes if rec.get("slot_type") == "dispenser"]
        topping_ids = [str(rec["id"]) for rec in active_recipes if rec.get("has_topping", False)]

        if not food_ids:
            food_ids = all_ids

        ctype = customer_type.lower()
        if ctype == "student":
            # 단품(1개) 주문 위주 (85% 1개, 15% 2개)
            if r.random() < 0.85 or len(all_ids) < 2:
                return [r.choice(all_ids)]
            return [r.choice(food_ids), r.choice(all_ids)]

        if ctype == "worker":
            # 1~2개 주문 (음식 + 음료 조합 선호)
            if drink_ids and food_ids and r.random() < 0.70:
                return [r.choice(food_ids), r.choice(drink_ids)]
            if r.random() < 0.50:
                return [r.choice(food_ids)]
            return [r.choice(all_ids), r.choice(all_ids)]

        if ctype == "tourist":
            # 외국인 관광객: 2개 메뉴 주문
            first = r.choice(food_ids)
            others = [rid for rid in all_ids if rid != first] or all_ids
            second = r.choice(others)
            return [first, second]

        if ctype == "youtuber":
            # 맛집 유튜버 VIP: 토핑 메뉴 포함 2개 주문 선호
            first = r.choice(topping_ids) if topping_ids else r.choice(food_ids)
            others = [rid for rid in all_ids if rid != first] or all_ids
            second = r.choice(others)
            return [first, second]

        return [r.choice(all_ids)]

    @property
    def patience_ratio(self) -> float:
        """현재 남은 인내심 비율(0.0 ~ 1.0)을 반환한다."""
        if self.max_patience <= 0:
            return 0.0
        return max(0.0, min(1.0, self.patience / self.max_patience))

    def get_mood(self) -> str:
        """현재 상태와 인내심 비율에 따른 감정 상태 문자열을 반환한다."""
        if self.state == "SATISFIED":
            return "FEVER" if self.triggers_fever else "HAPPY"
        if self.state in ("ANGRY_LEFT", "ANGRY"):
            return "ANGRY"
        ratio = self.patience_ratio
        if ratio >= 0.65:
            return "HAPPY"
        if ratio >= 0.40:
            return "NORMAL"
        if ratio >= 0.20:
            return "WARN"
        return "ANGRY"

    def wants_recipe(self, recipe_id: str) -> bool:
        """손님이 현재 대기 중('WAITING')이고 해당 메뉴를 주문했는지 여부를 반환한다."""
        return self.state == "WAITING" and (recipe_id in self.orders)

    def receive_dish(self, recipe_id: str, game_mgr: Any = None) -> AttrDict:
        """
        주문한 메뉴 1개를 서빙받는다.
        - self.orders에서 recipe_id 1개를 제거하고 self.completed_orders에 추가.
        - 남은 주문이 있으면 인내심 25% 회복, 모든 주문이 완료되면 self.state = "SATISFIED".
        - price, tip, total_gold, order_completed, triggers_fever 정보를 담은 딕셔너리(AttrDict) 반환.
        """
        if self.state != "WAITING" or recipe_id not in self.orders:
            return AttrDict(
                {
                    "served": False,
                    "recipe_id": recipe_id,
                    "price": 0,
                    "base_price": 0,
                    "tip": 0,
                    "total_gold": 0,
                    "total": 0,
                    "order_completed": False,
                    "triggers_fever": False,
                    "customer_type": self.customer_type,
                    "is_vip": self.is_vip,
                    "slot_index": self.slot_index,
                    "remaining_orders": len(self.orders),
                }
            )

        mgr = game_mgr or GameManager.get_instance()
        self.orders.remove(recipe_id)
        self.completed_orders.append(recipe_id)

        pat_ratio = self.patience_ratio
        order_completed = len(self.orders) == 0

        if not order_completed:
            # 남은 주문이 있으면 인내심 25% 회복
            self.patience = min(self.max_patience, self.patience + self.max_patience * 0.25)
        else:
            self.state = "SATISFIED"
            self.leave_timer = 0.55

        price = (
            int(mgr.get_recipe_price(recipe_id))
            if mgr and hasattr(mgr, "get_recipe_price")
            else int(RECIPES.get(recipe_id, {}).get("price", 3000))
        )

        # 손님 유형별 팁 배율 및 빠른 서빙/콤보 보너스 계산
        combo_mult = (
            float(mgr.get_combo_tip_multiplier())
            if mgr and hasattr(mgr, "get_combo_tip_multiplier")
            else 1.0
        )
        combo_stack = int(getattr(mgr, "combo", 0)) if mgr else 0
        combo_rate = min(config.MAX_COMBO_TIP_RATE, max(0, combo_stack) * config.COMBO_TIP_RATE)

        if self.customer_type == "worker":
            # 직장인은 빠른 서빙(인내심 50% 이상) 시 팁 배율 1.8배 발동
            effective_tip_mult = self.tip_mult if pat_ratio >= 0.50 else 1.05
        else:
            effective_tip_mult = self.tip_mult

        speed_tip_rate = (
            0.15
            if pat_ratio >= config.FAST_SERVE_PATIENCE_RATIO
            else (0.08 if pat_ratio >= 0.35 else 0.03)
        )
        vip_bonus_rate = 0.12 if self.is_vip else 0.0
        raw_tip = price * (speed_tip_rate + combo_rate + vip_bonus_rate) * effective_tip_mult * combo_mult
        tip = int(round(raw_tip / 10.0) * 10)
        total_gold = price + tip

        fever_triggered = bool(order_completed and self.triggers_fever)

        return AttrDict(
            {
                "served": True,
                "recipe_id": recipe_id,
                "price": price,
                "base_price": price,
                "tip": tip,
                "total_gold": total_gold,
                "total": total_gold,
                "order_completed": order_completed,
                "triggers_fever": fever_triggered,
                "customer_type": self.customer_type,
                "is_vip": self.is_vip,
                "slot_index": self.slot_index,
                "remaining_orders": len(self.orders),
            }
        )

    def heal_patience(self, ratio: float = 0.4) -> float:
        """김포차 액티브 스킬 등으로 손님의 인내심을 지정 비율만큼 즉시 회복한다."""
        if self.state == "WAITING":
            heal_amount = self.max_patience * max(0.0, float(ratio))
            self.patience = min(self.max_patience, self.patience + heal_amount)
        return self.patience

    def update(self, dt: float, patience_freeze: bool = False) -> Optional[str]:
        """
        손님의 입장/대기/퇴장 타이머 및 인내심을 업데이트한다.
        인내심이 0이 되면 'ANGRY_LEFT' 이벤트 문자열을 반환한다.
        """
        dt = max(0.0, float(dt))
        if self.enter_timer > 0.0:
            self.enter_timer = max(0.0, self.enter_timer - dt)

        if self.state == "WAITING":
            if not patience_freeze:
                self.patience = max(0.0, self.patience - dt)
            if self.patience <= 0.0:
                self.state = "ANGRY_LEFT"
                self.leave_timer = 0.45
                if not self._angry_event_emitted:
                    self._angry_event_emitted = True
                    return "ANGRY_LEFT"

        elif self.state in ("SATISFIED", "ANGRY_LEFT"):
            if self.leave_timer > 0.0:
                self.leave_timer = max(0.0, self.leave_timer - dt)
                if self.leave_timer <= 0.0:
                    self.ready_to_remove = True
            else:
                self.ready_to_remove = True

        return None

    def draw(
        self,
        surface: pygame.Surface,
        time_tick: Any = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        손님 캐릭터 반신상, 손님 유형 뱃지, 컬러 인내심 게이지 바,
        다중 메뉴 주문 말풍선(음식 아이콘 + 짧은 메뉴명 + 완료 체크 표시)을 렌더링한다.
        """
        if isinstance(time_tick, (int, float)):
            t = float(time_tick)
        else:
            t = float(kwargs.get("time_tick", pygame.time.get_ticks() * 0.001))

        # 입장 애니메이션 오프셋
        y_offset = int((self.enter_timer / 0.30) * 18) if self.enter_timer > 0 else 0

        # 좌측 하단부에 손님 캐릭터 배치, 우측/상단부에 대형 고대비 주문 말풍선 배치
        char_w = min(96, int(self.rect.width * 0.36))
        char_h = min(142, int(self.rect.height * 0.60))
        char_rect = pygame.Rect(
            self.rect.x + 4,
            self.rect.bottom - char_h - 22 + y_offset,
            char_w,
            char_h,
        )

        # VIP 후광 연출 (캐싱된 서피스 재사용)
        if self.is_vip:
            if not hasattr(Customer, "_vip_glow_cache"):
                Customer._vip_glow_cache = {}
            g_key = (char_rect.width + 24, char_rect.height + 24, self.customer_type)
            glow_surf = Customer._vip_glow_cache.get(g_key)
            if glow_surf is None:
                glow_surf = pygame.Surface((char_rect.width + 24, char_rect.height + 24), pygame.SRCALPHA)
                glow_col = (255, 195, 55, 42) if self.customer_type == "tourist" else (215, 95, 255, 48)
                pygame.draw.ellipse(glow_surf, glow_col, glow_surf.get_rect())
                Customer._vip_glow_cache[g_key] = glow_surf
            surface.blit(glow_surf, (char_rect.x - 12, char_rect.y - 12))

        draw_customer(
            surface,
            char_rect,
            customer_type=self.customer_type,
            mood=self.get_mood(),
            time_tick=t,
        )

        # 인내심 게이지 바 (캐릭터 하단 — 모바일 고시인성 14px 두께 & 네온 컬러)
        gauge_rect = pygame.Rect(char_rect.x + 2, char_rect.bottom + 3, char_rect.width - 4, 14)
        pygame.draw.rect(surface, (20, 16, 28), gauge_rect, border_radius=7)
        ratio = self.patience_ratio
        if ratio >= 0.55:
            bar_col = (48, 238, 102)
        elif ratio >= 0.25:
            bar_col = (255, 206, 42)
        else:
            bar_col = (248, 52, 52)

        fill_w = int((gauge_rect.width - 4) * ratio)
        if fill_w > 0:
            pygame.draw.rect(
                surface,
                bar_col,
                (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                border_radius=5,
            )
        pygame.draw.rect(surface, (215, 212, 232), gauge_rect, width=2, border_radius=7)

        # 손님 유형 뱃지 (캐릭터 머리 위/가슴 상단 — 13px 볼드 고대비)
        badge_font = config.get_font(13, bold=True)
        badge_surf = badge_font.render(self.badge_text, True, config.WHITE)
        badge_w = badge_surf.get_width() + 14
        badge_h = 22
        badge_rect = pygame.Rect(
            char_rect.centerx - badge_w // 2,
            char_rect.top - 20,
            badge_w,
            badge_h,
        )
        pygame.draw.rect(surface, self.badge_color, badge_rect, border_radius=7)
        pygame.draw.rect(
            surface,
            config.GOLD if self.is_vip else config.WHITE,
            badge_rect,
            width=2,
            border_radius=7,
        )
        surface.blit(
            badge_surf,
            (
                badge_rect.centerx - badge_surf.get_width() // 2,
                badge_rect.centery - badge_surf.get_height() // 2,
            ),
        )

        # 주문 말풍선 렌더링 (우측 상단 영역)
        self._draw_order_bubble(surface, char_rect, t)

    def _draw_order_bubble(
        self,
        surface: pygame.Surface,
        char_rect: pygame.Rect,
        time_tick: float,
    ) -> None:
        """주문 메뉴 아이콘(38px), 굵은 한글 메뉴명(15px), 기구/토핑 컬러 배지가 포함된 고시인성 말풍선을 그린다."""
        display_orders = self.initial_orders if self.initial_orders else self.orders
        if not display_orders:
            return

        item_count = len(display_orders)
        row_h = 52
        bubble_w = max(154, self.rect.right - char_rect.right + 14)
        bubble_h = 14 + item_count * row_h
        bubble_x = max(self.rect.x + 74, self.rect.right - bubble_w - 2)
        bubble_y = max(
            config.CUSTOMER_AREA_TOP + 4,
            char_rect.top - 14,
        )
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_w, bubble_h)

        # 말풍선 꼬리
        tail_pts = [
            (bubble_rect.left + 8, bubble_rect.centery),
            (char_rect.right - 12, char_rect.centery - 6),
            (bubble_rect.left + 8, bubble_rect.centery + 12),
        ]
        bg_col = (255, 252, 245) if not self.is_vip else (255, 248, 222)
        border_col = (
            config.GOLD
            if self.is_vip
            else (config.PATIENCE_LOW if self.patience_ratio < 0.25 else (58, 48, 78))
        )

        pygame.draw.polygon(surface, bg_col, tail_pts)
        pygame.draw.rect(surface, bg_col, bubble_rect, border_radius=11)
        pygame.draw.rect(surface, border_col, bubble_rect, width=3, border_radius=11)

        # 완료 여부 매칭을 위해 completed_orders 복사본 사용
        completed_pool = list(self.completed_orders)
        name_font = config.get_font(15, bold=True)
        sub_font = config.get_font(12, bold=True)

        short_map = {
            "갈릭버터 큐브스테이크": "갈릭 큐브스테이크",
            "오리지널 큐브스테이크": "큐브스테이크",
            "스위트 칠리 지파이": "칠리 지파이",
            "마라 시즈닝 지파이": "마라 지파이",
            "크리스피 대왕 지파이": "대왕 지파이",
            "어묵국물 (오뎅탕)": "어묵국물",
            "전통 살얼음 식혜": "살얼음 식혜",
            "구슬 사이다 (라무네)": "라무네 사이다",
            "타피오카 버블밀크티": "버블밀크티",
        }

        for idx, rid in enumerate(display_orders):
            row_y = bubble_rect.y + 7 + idx * row_h
            row_rect = pygame.Rect(bubble_rect.x + 5, row_y, bubble_rect.width - 10, row_h - 4)

            is_done = False
            if rid in completed_pool:
                completed_pool.remove(rid)
                is_done = True

            row_bg = (218, 246, 224) if is_done else (246, 240, 228)
            row_border = (52, 168, 82) if is_done else (196, 184, 168)
            pygame.draw.rect(surface, row_bg, row_rect, border_radius=8)
            pygame.draw.rect(surface, row_border, row_rect, width=1, border_radius=8)

            icon_center = (row_rect.x + 21, row_rect.centery)
            draw_food_icon(surface, icon_center, rid, size=38, burnt=False)

            rec = RECIPES.get(rid)
            full_name = str(rec["name"]) if rec else rid
            short_name = short_map.get(full_name, full_name)

            text_col = (24, 118, 48) if is_done else (18, 14, 28)
            max_txt_w = row_rect.width - 44
            active_name_font = name_font
            for f_sz in (14, 13, 12, 11):
                if active_name_font.size(short_name)[0] <= max_txt_w:
                    break
                active_name_font = config.get_font(f_sz, bold=True)
            name_surf = active_name_font.render(short_name, True, text_col)
            surface.blit(name_surf, (row_rect.x + 41, row_rect.y + 3))

            # 하단 고대비 기구/토핑 컬러 배지
            slot_type = str(rec.get("slot_type", "")) if rec else ""
            if is_done:
                tag_txt, pill_bg = "★ 서빙완료!", (34, 158, 68)
            elif rec and rec.get("has_topping", False):
                tag_txt, pill_bg = "★토핑조립", (222, 78, 28)
            elif slot_type == "dispenser":
                tag_txt, pill_bg = "🥤음료·즉시", (32, 132, 208)
            elif slot_type == "mold":
                tag_txt, pill_bg = "🐟틀구이", (188, 102, 24)
            elif slot_type == "grill":
                tag_txt, pill_bg = "🔥그릴구이", (198, 52, 44)
            elif slot_type == "batch_pot":
                tag_txt, pill_bg = "🥘대량팬", (158, 48, 132)
            else:
                tag_txt, pill_bg = "주문메뉴", (88, 78, 112)

            hint_surf = sub_font.render(tag_txt, True, config.WHITE)
            pill_rect = pygame.Rect(
                row_rect.x + 41,
                row_rect.bottom - 22,
                min(max_txt_w, hint_surf.get_width() + 12),
                19,
            )
            pygame.draw.rect(surface, pill_bg, pill_rect, border_radius=5)
            surface.blit(
                hint_surf,
                (
                    pill_rect.centerx - hint_surf.get_width() // 2,
                    pill_rect.centery - hint_surf.get_height() // 2,
                ),
            )
