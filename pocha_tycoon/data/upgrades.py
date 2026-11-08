"""
조리 기구 업그레이드(STATION_UPGRADES) 및 포차 인테리어 업그레이드(INTERIOR_UPGRADES)
데이터 및 스탯 계산 헬퍼 모듈.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from data.characters import AttrDict

STATION_UPGRADE_ORDER: List[str] = [
    "mold_upgrade",
    "grill_upgrade",
    "batch_pot_upgrade",
    "dispenser_upgrade",
    "tray_upgrade",
]

INTERIOR_UPGRADE_ORDER: List[str] = [
    "awning_lights",
    "plastic_chairs",
    "neon_signboard",
    "retro_radio",
]

# 슬롯 타입 <-> 기구 업그레이드 키 매핑
SLOT_TO_UPGRADE_KEY: Dict[str, str] = {
    "mold": "mold_upgrade",
    "grill": "grill_upgrade",
    "batch_pot": "batch_pot_upgrade",
    "dispenser": "dispenser_upgrade",
    "tray": "tray_upgrade",
    "mold_upgrade": "mold_upgrade",
    "grill_upgrade": "grill_upgrade",
    "batch_pot_upgrade": "batch_pot_upgrade",
    "dispenser_upgrade": "dispenser_upgrade",
    "tray_upgrade": "tray_upgrade",
}


# ==============================================================================
# 조리 기구 업그레이드 (STATION_UPGRADES) - 최대 Lv.3
# Lv.0: 기본 상태 (미강화)
# Lv.1 ~ Lv.3: 단계별 강화 (가격, 슬롯/생산량 증가, 조리 속도 배율, 타는 시간 배율)
# ==============================================================================
_RAW_STATION_UPGRADES: Dict[str, Dict[str, Any]] = {
    "mold_upgrade": {
        "id": "mold_upgrade",
        "upgrade_id": "mold_upgrade",
        "slot_type": "mold",
        "target_slot": "mold",
        "name": "고화력 몰드·철판 개조",
        "short_name": "몰드 강화",
        "max_level": 3,
        "base_slots": 2,
        "costs": [3000, 6500, 12000],
        "description": "몰드 구이 기구(붕어빵·타코야키·퀘사디야·총좌빙)의 슬롯 수와 화력을 강화합니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "slot_bonus": 0,
                "total_slots": 2,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.00,
                "description": "기본 2슬롯, 기본 조리 속도",
            },
            1: {
                "level": 1,
                "cost": 3000,
                "slot_bonus": 1,
                "total_slots": 3,
                "cook_speed_mult": 1.15,
                "burn_time_mult": 1.15,
                "description": "슬롯 +1 (총 3개), 조리 속도 +15%, 타는 시간 +15% 여유",
            },
            2: {
                "level": 2,
                "cost": 6500,
                "slot_bonus": 1,
                "total_slots": 3,
                "cook_speed_mult": 1.30,
                "burn_time_mult": 1.30,
                "description": "슬롯 +1 (총 3개), 조리 속도 +30%, 타는 시간 +30% 여유",
            },
            3: {
                "level": 3,
                "cost": 12000,
                "slot_bonus": 2,
                "total_slots": 4,
                "cook_speed_mult": 1.50,
                "burn_time_mult": 1.50,
                "description": "슬롯 +2 (총 4개), 조리 속도 +50%, 타는 시간 +50% 여유",
            },
        },
    },
    "grill_upgrade": {
        "id": "grill_upgrade",
        "upgrade_id": "grill_upgrade",
        "slot_type": "grill",
        "target_slot": "grill",
        "name": "직화 그릴·튀김기 확장",
        "short_name": "그릴 강화",
        "max_level": 3,
        "base_slots": 2,
        "costs": [3500, 7500, 13500],
        "description": "그릴/튀김 기구(닭꼬치·야키토리·타코·지파이)의 슬롯 수와 조리 효율을 높입니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "slot_bonus": 0,
                "total_slots": 2,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.00,
                "description": "기본 2슬롯, 기본 조리 속도",
            },
            1: {
                "level": 1,
                "cost": 3500,
                "slot_bonus": 1,
                "total_slots": 3,
                "cook_speed_mult": 1.15,
                "burn_time_mult": 1.15,
                "description": "슬롯 +1 (총 3개), 조리 속도 +15%, 타는 시간 +15% 여유",
            },
            2: {
                "level": 2,
                "cost": 7500,
                "slot_bonus": 1,
                "total_slots": 3,
                "cook_speed_mult": 1.30,
                "burn_time_mult": 1.30,
                "description": "슬롯 +1 (총 3개), 조리 속도 +30%, 타는 시간 +30% 여유",
            },
            3: {
                "level": 3,
                "cost": 13500,
                "slot_bonus": 2,
                "total_slots": 4,
                "cook_speed_mult": 1.50,
                "burn_time_mult": 1.50,
                "description": "슬롯 +2 (총 4개), 조리 속도 +50%, 타는 시간 +50% 여유",
            },
        },
    },
    "batch_pot_upgrade": {
        "id": "batch_pot_upgrade",
        "upgrade_id": "batch_pot_upgrade",
        "slot_type": "batch_pot",
        "target_slot": "batch_pot",
        "name": "특대형 철판·프라이어 증설",
        "short_name": "대량팬 강화",
        "max_level": 3,
        "base_slots": 3,  # 대량 팬의 기본 생산 인분 수(3인분)
        "costs": [3800, 8000, 14500],
        "description": "대량 조리 팬(떡볶이·야키소바·나초·큐브스테이크)의 1회 생산량과 조리 속도를 늘립니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "slot_bonus": 0,
                "extra_servings": 0,
                "total_slots": 3,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.00,
                "description": "기본 3인분 생산, 기본 조리 속도",
            },
            1: {
                "level": 1,
                "cost": 3800,
                "slot_bonus": 1,
                "extra_servings": 1,
                "total_slots": 4,
                "cook_speed_mult": 1.15,
                "burn_time_mult": 1.20,
                "description": "생산량 +1인분 (총 4인분), 조리 속도 +15%, 보온 시간 +20%",
            },
            2: {
                "level": 2,
                "cost": 8000,
                "slot_bonus": 2,
                "extra_servings": 2,
                "total_slots": 5,
                "cook_speed_mult": 1.30,
                "burn_time_mult": 1.40,
                "description": "생산량 +2인분 (총 5인분), 조리 속도 +30%, 보온 시간 +40%",
            },
            3: {
                "level": 3,
                "cost": 14500,
                "slot_bonus": 3,
                "extra_servings": 3,
                "total_slots": 6,
                "cook_speed_mult": 1.50,
                "burn_time_mult": 1.65,
                "description": "생산량 +3인분 (총 6인분), 조리 속도 +50%, 보온 시간 +65%",
            },
        },
    },
    "dispenser_upgrade": {
        "id": "dispenser_upgrade",
        "upgrade_id": "dispenser_upgrade",
        "slot_type": "dispenser",
        "target_slot": "dispenser",
        "name": "초고속 음료 디스펜서 노즐",
        "short_name": "디스펜서 강화",
        "max_level": 3,
        "base_slots": 2,
        "costs": [2500, 5500, 10000],
        "description": "음료 디스펜서의 동시 추출 컵 슬롯 수와 자동 충전 속도를 높입니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "slot_bonus": 0,
                "total_slots": 2,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.00,
                "description": "기본 2컵 슬롯, 기본 추출 속도",
            },
            1: {
                "level": 1,
                "cost": 2500,
                "slot_bonus": 1,
                "total_slots": 3,
                "cook_speed_mult": 1.20,
                "burn_time_mult": 1.00,
                "description": "추출 슬롯 +1 (총 3컵), 음료 충전 속도 +20%",
            },
            2: {
                "level": 2,
                "cost": 5500,
                "slot_bonus": 1,
                "total_slots": 3,
                "cook_speed_mult": 1.40,
                "burn_time_mult": 1.00,
                "description": "추출 슬롯 +1 (총 3컵), 음료 충전 속도 +40%",
            },
            3: {
                "level": 3,
                "cost": 10000,
                "slot_bonus": 2,
                "total_slots": 4,
                "cook_speed_mult": 1.65,
                "burn_time_mult": 1.00,
                "description": "추출 슬롯 +2 (총 4컵), 음료 충전 속도 +65%",
            },
        },
    },
    "tray_upgrade": {
        "id": "tray_upgrade",
        "upgrade_id": "tray_upgrade",
        "slot_type": "tray",
        "target_slot": "tray",
        "name": "스테인리스 보온 서빙 트레이",
        "short_name": "트레이 확장",
        "max_level": 3,
        "base_slots": 2,
        "costs": [2800, 6000, 11000],
        "description": "완성된 음식을 올려두거나 토핑을 조합하는 보조 서빙 트레이 슬롯을 확장합니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "slot_bonus": 0,
                "total_slots": 2,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.00,
                "description": "기본 트레이 2칸",
            },
            1: {
                "level": 1,
                "cost": 2800,
                "slot_bonus": 1,
                "total_slots": 3,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.10,
                "description": "보조 트레이 +1칸 (총 3칸)",
            },
            2: {
                "level": 2,
                "cost": 6000,
                "slot_bonus": 2,
                "total_slots": 4,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.20,
                "description": "보조 트레이 +2칸 (총 4칸)",
            },
            3: {
                "level": 3,
                "cost": 11000,
                "slot_bonus": 3,
                "total_slots": 5,
                "cook_speed_mult": 1.00,
                "burn_time_mult": 1.30,
                "description": "보조 트레이 +3칸 (총 5칸)",
            },
        },
    },
}

STATION_UPGRADES: Dict[str, AttrDict] = {}
for _uid, _udata in _RAW_STATION_UPGRADES.items():
    _levels_wrapped = {
        lvl: AttrDict(ldata) for lvl, ldata in _udata["levels"].items()
    }
    _entry = AttrDict(_udata)
    _entry["levels"] = _levels_wrapped
    _entry["cost"] = _udata["costs"][0]
    _entry["slot_bonuses"] = [_levels_wrapped[i]["slot_bonus"] for i in range(4)]
    _entry["cook_speed_mults"] = [_levels_wrapped[i]["cook_speed_mult"] for i in range(4)]
    _entry["burn_time_mults"] = [_levels_wrapped[i]["burn_time_mult"] for i in range(4)]
    STATION_UPGRADES[_uid] = _entry


# ==============================================================================
# 포차 인테리어 업그레이드 (INTERIOR_UPGRADES)
# ==============================================================================
_RAW_INTERIOR_UPGRADES: Dict[str, Dict[str, Any]] = {
    "awning_lights": {
        "id": "awning_lights",
        "interior_id": "awning_lights",
        "name": "포차 천막 & 알전구",
        "short_name": "천막 & 알전구",
        "max_level": 1,
        "cost": 5500,
        "costs": [5500],
        "patience_mult": 1.15,
        "patience_bonus": 0.15,
        "effect_type": "patience_mult",
        "effect_value": 1.15,
        "description": "따뜻한 주황빛 알전구와 비닐 천막으로 손님 인내심이 +15% 증가합니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "patience_mult": 1.00,
                "patience_bonus": 0.0,
                "description": "미설치 (기본 인내심 100%)",
            },
            1: {
                "level": 1,
                "cost": 5500,
                "patience_mult": 1.15,
                "patience_bonus": 0.15,
                "description": "손님 최대 인내심 +15% 증가",
            },
        },
    },
    "plastic_chairs": {
        "id": "plastic_chairs",
        "interior_id": "plastic_chairs",
        "name": "레트로 플라스틱 의자",
        "short_name": "플라스틱 의자",
        "max_level": 1,
        "cost": 8500,
        "costs": [8500],
        "extra_customer_slots": 1,
        "max_customers": 4,
        "effect_type": "extra_customer_slots",
        "effect_value": 1,
        "description": "정겨운 빨간·파란 플라스틱 의자를 추가해 최대 손님 슬롯이 3명→4명으로 늘어납니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "extra_customer_slots": 0,
                "max_customers": 3,
                "description": "미설치 (최대 손님 3명)",
            },
            1: {
                "level": 1,
                "cost": 8500,
                "extra_customer_slots": 1,
                "max_customers": 4,
                "description": "최대 동시 대기 손님 슬롯 3명 → 4명 확장",
            },
        },
    },
    "neon_signboard": {
        "id": "neon_signboard",
        "interior_id": "neon_signboard",
        "name": "야시장 네온 입간판",
        "short_name": "네온 입간판",
        "max_level": 1,
        "cost": 7000,
        "costs": [7000],
        "vip_spawn_bonus": 0.12,
        "effect_type": "vip_spawn_bonus",
        "effect_value": 0.12,
        "description": "화려한 야시장 네온사인 입간판으로 관광객 및 VIP 손님 등장 확률이 +12% 증가합니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "vip_spawn_bonus": 0.0,
                "description": "미설치 (기본 VIP 등장 확률)",
            },
            1: {
                "level": 1,
                "cost": 7000,
                "vip_spawn_bonus": 0.12,
                "description": "관광객·VIP 손님 등장 확률 +12% 상승",
            },
        },
    },
    "retro_radio": {
        "id": "retro_radio",
        "interior_id": "retro_radio",
        "name": "7080 감성 라디오",
        "short_name": "감성 라디오",
        "max_level": 1,
        "cost": 6500,
        "costs": [6500],
        "combo_tip_mult": 1.25,
        "combo_tip_bonus": 0.25,
        "effect_type": "combo_tip_mult",
        "effect_value": 1.25,
        "description": "낭만적인 포차 음악이 흘러나와 연속 서빙 시 콤보 보너스 팁이 +25% 증가합니다.",
        "levels": {
            0: {
                "level": 0,
                "cost": 0,
                "combo_tip_mult": 1.00,
                "combo_tip_bonus": 0.0,
                "description": "미설치 (기본 콤보 팁)",
            },
            1: {
                "level": 1,
                "cost": 6500,
                "combo_tip_mult": 1.25,
                "combo_tip_bonus": 0.25,
                "description": "콤보 보너스 팁 +25% 증가",
            },
        },
    },
}

INTERIOR_UPGRADES: Dict[str, AttrDict] = {}
for _iid, _idata in _RAW_INTERIOR_UPGRADES.items():
    _ilevels_wrapped = {
        lvl: AttrDict(ldata) for lvl, ldata in _idata["levels"].items()
    }
    _ientry = AttrDict(_idata)
    _ientry["levels"] = _ilevels_wrapped
    INTERIOR_UPGRADES[_iid] = _ientry


# ==============================================================================
# 업그레이드 조회 헬퍼 함수
# ==============================================================================
def normalize_station_upgrade_key(key: str) -> str:
    """'mold' 또는 'mold_upgrade' 형태를 모두 'mold_upgrade' 표준 키로 정규화한다."""
    return SLOT_TO_UPGRADE_KEY.get(key, key)


def get_station_upgrade_data(key: str) -> Optional[AttrDict]:
    """기구 업그레이드 메타데이터를 반환한다."""
    norm_key = normalize_station_upgrade_key(key)
    return STATION_UPGRADES.get(norm_key)


def get_station_level_stats(key: str, level: int) -> AttrDict:
    """특정 기구 업그레이드의 해당 레벨(0~3) 스탯 딕셔너리를 반환한다."""
    up_data = get_station_upgrade_data(key)
    if not up_data:
        return AttrDict(
            {
                "level": 0,
                "cost": 0,
                "slot_bonus": 0,
                "total_slots": 2,
                "cook_speed_mult": 1.0,
                "burn_time_mult": 1.0,
                "description": "",
            }
        )
    clamped = max(0, min(int(level), int(up_data["max_level"])))
    return up_data["levels"][clamped]


def get_next_station_upgrade_cost(key: str, current_level: int) -> Optional[int]:
    """다음 단계 기구 업그레이드 비용을 반환한다. 최대 레벨이면 None 반환."""
    up_data = get_station_upgrade_data(key)
    if not up_data:
        return None
    next_lvl = int(current_level) + 1
    if next_lvl > int(up_data["max_level"]):
        return None
    return int(up_data["levels"][next_lvl]["cost"])


def get_interior_upgrade_data(interior_id: str) -> Optional[AttrDict]:
    """포차 인테리어 업그레이드 메타데이터를 반환한다."""
    return INTERIOR_UPGRADES.get(interior_id)


def get_next_interior_upgrade_cost(interior_id: str, current_level: int) -> Optional[int]:
    """다음 단계 인테리어 업그레이드 비용을 반환한다. 이미 최대 레벨이면 None 반환."""
    in_data = get_interior_upgrade_data(interior_id)
    if not in_data:
        return None
    next_lvl = int(current_level) + 1
    if next_lvl > int(in_data["max_level"]):
        return None
    return int(in_data["levels"][next_lvl]["cost"])
