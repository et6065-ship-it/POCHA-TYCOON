"""
entities 패키지 초기화 모듈.
"""

from entities.dish import Dish
from entities.customer import CUSTOMER_TYPES, Customer, compute_customer_slot_rect

__all__ = [
    "Dish",
    "Customer",
    "CUSTOMER_TYPES",
    "compute_customer_slot_rect",
]
