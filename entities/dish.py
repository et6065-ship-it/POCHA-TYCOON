"""
entities/dish.py
조리 완료 후 서빙되거나 조립 트레이(AssemblyTray)에서 토핑을 추가하는 음식(Dish) 엔티티 모듈.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Tuple, Union
import pygame

from core.art_renderer import draw_food_icon
from core.game_manager import GameManager
from data.recipes import RECIPES, can_add_topping as _recipe_can_add_topping, get_recipe, resolve_recipe


class Dish:
    """
    조리 기구에서 생성되어 조립 트레이 또는 손님에게 전달되는 음식 객체.
    베이스 레시피 ID와 추가된 토핑 목록을 기반으로 최종 레시피를 동적으로 판별한다.
    """

    def __init__(
        self,
        base_recipe_id: str,
        toppings: Optional[Iterable[str]] = None,
        burnt: bool = False,
    ) -> None:
        self.base_recipe_id: str = str(base_recipe_id)
        self.toppings: List[str] = [str(t) for t in toppings if t] if toppings else []
        self.burnt: bool = bool(burnt)

    @property
    def recipe_id(self) -> str:
        """현재 베이스 레시피와 토핑 목록이 조합된 최종 레시피 ID를 반환한다."""
        return resolve_recipe(self.base_recipe_id, self.toppings)

    @property
    def name(self) -> str:
        """현재 조합된 레시피의 한글 메뉴명을 반환한다."""
        if self.burnt:
            base_name = RECIPES.get(self.recipe_id, {}).get("name", self.recipe_id)
            return f"탄 {base_name}"
        rec = RECIPES.get(self.recipe_id)
        if rec:
            return str(rec["name"])
        return self.recipe_id

    @property
    def recipe_data(self) -> Optional[Any]:
        """현재 레시피의 RECIPES 메타데이터(AttrDict)를 반환한다."""
        return get_recipe(self.recipe_id)

    @property
    def country(self) -> str:
        """현재 레시피의 국가 코드를 반환한다."""
        rec = self.recipe_data
        return str(rec["country"]) if rec else "KR"

    @property
    def station_id(self) -> str:
        """현재 레시피의 조리 기구 ID를 반환한다."""
        rec = self.recipe_data
        return str(rec["station_id"]) if rec else ""

    @property
    def has_topping(self) -> bool:
        """토핑이 1개 이상 추가되었거나 토핑 완성형 메뉴인지 여부를 반환한다."""
        if self.toppings:
            return True
        rec = self.recipe_data
        return bool(rec.get("has_topping", False)) if rec else False

    def can_add_topping(self, topping_id: str) -> bool:
        """
        해당 토핑을 현재 음식에 추가했을 때 유효한 상위 레시피로 변환되는지 확인한다.
        탄 음식(burnt=True)이거나 이미 동일한 토핑이 들어간 경우 False를 반환한다.
        """
        if self.burnt or not topping_id:
            return False
        topping_id = str(topping_id)
        if topping_id in self.toppings:
            return False

        current_id = self.recipe_id
        candidate_toppings = self.toppings + [topping_id]
        resolved_from_base = resolve_recipe(self.base_recipe_id, candidate_toppings)
        if resolved_from_base != current_id and resolved_from_base != self.base_recipe_id:
            return True

        return _recipe_can_add_topping(current_id, topping_id)

    def add_topping(self, topping_id: str) -> bool:
        """
        유효한 토핑인 경우 토핑 리스트에 추가하고 True를 반환한다.
        유효하지 않으면 추가하지 않고 False를 반환한다.
        """
        if not self.can_add_topping(topping_id):
            return False
        self.toppings.append(str(topping_id))
        return True

    def get_price(self, game_mgr: Any = None) -> int:
        """
        주인공 패시브 등이 반영된 현재 음식의 판매 가격(원)을 반환한다.
        탄 음식은 0원을 반환한다.
        """
        if self.burnt:
            return 0
        mgr = game_mgr or GameManager.get_instance()
        if mgr and hasattr(mgr, "get_recipe_price"):
            return int(mgr.get_recipe_price(self.recipe_id))
        rec = RECIPES.get(self.recipe_id)
        return int(rec["price"]) if rec else 0

    def copy(self) -> "Dish":
        """동일한 상태를 가진 Dish 복제본을 반환한다."""
        return Dish(
            base_recipe_id=self.base_recipe_id,
            toppings=list(self.toppings),
            burnt=self.burnt,
        )

    def draw(
        self,
        surface: pygame.Surface,
        center_pos: Union[Tuple[int, int], pygame.Rect],
        size: int = 48,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """프로시저럴 음식 아이콘을 지정된 중심 좌표에 렌더링한다."""
        draw_food_icon(
            surface,
            center_pos,
            self.recipe_id,
            size=size,
            burnt=self.burnt,
        )

    def __repr__(self) -> str:
        return (
            f"Dish(base={self.base_recipe_id!r}, toppings={self.toppings!r}, "
            f"recipe_id={self.recipe_id!r}, burnt={self.burnt!r})"
        )
