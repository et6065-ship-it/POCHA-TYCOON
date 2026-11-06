"""
'전세계 길거리 음식 포차 타이쿤'의 게임 상태, 진행도(골드, 일차, 콤보, 해금),
월드 투어 / 글로벌 무한 모드 로드아웃, 주인공 패시브 및 업그레이드 스탯 계산,
JSON 세이브/로드를 총괄하는 GameManager 모듈.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import config
from data.characters import AttrDict, CHARACTER_ORDER, CHARACTERS, get_character
from data.recipes import RECIPES, TOPPINGS, get_recipe, get_recipes_by_station
from data.chapters import (
    CHAPTER_ORDER,
    CHAPTERS,
    SLOT_TYPES,
    STATIONS_CATALOG,
    calculate_stars,
    calculate_target_gold,
    get_chapter,
    get_station_meta,
)
from data.upgrades import (
    INTERIOR_UPGRADE_ORDER,
    INTERIOR_UPGRADES,
    SLOT_TO_UPGRADE_KEY,
    STATION_UPGRADE_ORDER,
    STATION_UPGRADES,
    get_interior_upgrade_data,
    get_next_interior_upgrade_cost,
    get_next_station_upgrade_cost,
    get_station_level_stats,
    get_station_upgrade_data,
    normalize_station_upgrade_key,
)
from data.story import (
    get_day_progression,
    get_max_station_upgrade_level,
    get_story_cutscene,
    get_unlocked_cooking_slots,
    get_unlocked_interiors,
    get_unlocked_slots,
    is_slot_unlocked,
)
from data.specialist_menus import (
    OPEN_SPECIALIST_ORDER,
    SPECIALIST_MENUS,
    SPECIALIST_ORDER,
    get_specialist_menu,
)


class StationRef(str):
    """
    조리 기구 ID 문자열('kr_bungeoppang' 등)로도 동작하고,
    STATIONS_CATALOG 메타데이터 딕셔너리(station['name'], station.recipes 등)로도
    동시에 동작하는 하이브리드 참조 객체.
    """

    def _meta(self) -> AttrDict:
        return STATIONS_CATALOG.get(str(self), AttrDict({"id": str(self), "name": str(self)}))

    def __getitem__(self, key: Union[int, slice, str]) -> Any:  # type: ignore[override]
        if isinstance(key, (int, slice)):
            return super().__getitem__(key)
        return self._meta()[key]

    def __getattr__(self, name: str) -> Any:
        meta = self._meta()
        if name in meta:
            return meta[name]
        raise AttributeError(f"'StationRef' object has no attribute '{name}'")

    def get(self, key: str, default: Any = None) -> Any:
        return self._meta().get(key, default)

    def keys(self) -> Any:
        return self._meta().keys()

    def values(self) -> Any:
        return self._meta().values()

    def items(self) -> Any:
        return self._meta().items()

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str) and item in self._meta():
            return True
        return super().__contains__(str(item))


class StationLevelDict(dict):
    """
    'mold'와 'mold_upgrade' 두 가지 형태의 키 접근/수정을 모두 동기화하는 딕셔너리.
    """

    _SHORT_TO_LONG = {
        "mold": "mold_upgrade",
        "grill": "grill_upgrade",
        "batch_pot": "batch_pot_upgrade",
        "dispenser": "dispenser_upgrade",
        "tray": "tray_upgrade",
    }
    _LONG_TO_SHORT = {v: k for k, v in _SHORT_TO_LONG.items()}

    def __init__(self, initial: Optional[Dict[str, int]] = None) -> None:
        super().__init__()
        for long_k in STATION_UPGRADE_ORDER:
            super().__setitem__(long_k, 0)
        if initial:
            for k, v in initial.items():
                self[k] = int(v)

    def __getitem__(self, key: str) -> int:
        norm = self._SHORT_TO_LONG.get(key, key)
        return int(super().get(norm, 0))

    def __setitem__(self, key: str, value: int) -> None:
        norm = self._SHORT_TO_LONG.get(key, key)
        max_lvl = int(STATION_UPGRADES.get(norm, {}).get("max_level", 3))
        clamped = max(0, min(int(value), max_lvl))
        super().__setitem__(norm, clamped)

    def get(self, key: str, default: Any = 0) -> Any:
        norm = self._SHORT_TO_LONG.get(key, key)
        return super().get(norm, default)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            norm = self._SHORT_TO_LONG.get(key, key)
            return super().__contains__(norm)
        return False


class GameManager:
    """
    전세계 길거리 음식 포차 타이쿤의 핵심 상태 및 성장 시스템 매니저 (싱글톤/공유 객체).
    """

    _instance: Optional["GameManager"] = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "GameManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, reset: bool = False, save_path: Optional[str] = None) -> None:
        if save_path:
            self.save_path: str = save_path
        elif not hasattr(self, "save_path"):
            self.save_path = config.SAVE_FILE_PATH

        if not self._initialized or reset:
            self.reset_state()
            self._initialized = True

    @classmethod
    def get_instance(cls) -> "GameManager":
        """싱글톤 GameManager 인스턴스를 반환한다."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def create_duel_manager(
        cls,
        chapter: str = "KR",
        character: str = "chef_kr",
        station_level: int = 2,
    ) -> "GameManager":
        """
        싱글플레이 세이브 데이터를 오염시키지 않는 1:1 결투 모드 전용 독립 GameManager를 생성한다.
        - 양측 동일한 기구 업그레이드 레벨(station_level)과 인테리어 버프 적용
        - 모든 챕터 및 포차 마스터 해금 상태
        """
        inst = object.__new__(cls)
        inst.save_path = ""
        inst._initialized = True
        inst.reset_state()
        inst.mode = "DUEL_MODE"
        inst.day = 5
        inst.current_chapter = chapter.upper() if chapter.upper() in CHAPTERS else "KR"
        inst.selected_character = character if character in CHARACTERS else "chef_kr"
        inst.unlocked_characters = list(CHARACTER_ORDER)
        inst.unlocked_chapters = list(CHAPTER_ORDER)
        lvl = max(0, min(3, int(station_level)))
        for k in STATION_UPGRADE_ORDER:
            inst.station_levels[k] = lvl
        for k in INTERIOR_UPGRADE_ORDER:
            inst.interior_levels[k] = 1
        inst.start_day()
        return inst

    def reset_state(self) -> None:
        """모든 게임 진행 상태를 초기 기본값으로 리셋한다."""
        # 게임 모드: "WORLD_TOUR" 또는 "GLOBAL_ENDLESS"
        self.mode: str = "WORLD_TOUR"

        # 현재 선택된 챕터 및 주인공
        self.current_chapter: str = "KR"
        self.selected_character: str = "chef_kr"

        # 해금 목록
        self.unlocked_characters: List[str] = ["chef_kr"]
        self.unlocked_chapters: List[str] = ["KR"]

        # 글로벌 야시장 통합 모드용 슬롯별 장착 기구 로드아웃
        self.global_loadout: Dict[str, str] = {
            "mold": "kr_bungeoppang",
            "grill": "kr_skewer_grill",
            "batch_pot": "kr_tteokbokki_pan",
            "dispenser": "kr_odeng_dispenser",
        }

        # 경제 및 일차 진행 상태
        self.gold: int = 3000
        self.total_earned_gold: int = 0
        self.day: int = 1
        self.endless_day: int = 1
        self.last_played_day: int = 1
        self.last_day_cleared: bool = False
        self.chapter_days: Dict[str, int] = {cid: 1 for cid in CHAPTER_ORDER}

        # 단일 메뉴 장인 모드(SPECIALIST) 상태
        self.selected_specialist: str = "bungeo"
        self.specialist_days: Dict[str, int] = {sid: 1 for sid in SPECIALIST_ORDER}
        self.specialist_stars: Dict[str, int] = {sid: 0 for sid in SPECIALIST_ORDER}

        # 기구 업그레이드 레벨 (0 ~ 3)
        self.station_levels: StationLevelDict = StationLevelDict(
            {
                "mold_upgrade": 0,
                "grill_upgrade": 0,
                "batch_pot_upgrade": 0,
                "dispenser_upgrade": 0,
                "tray_upgrade": 0,
            }
        )

        # 인테리어 업그레이드 레벨 (0 ~ 1)
        self.interior_levels: Dict[str, int] = {
            "awning_lights": 0,
            "plastic_chairs": 0,
            "neon_signboard": 0,
            "retro_radio": 0,
        }

        # 챕터별 최고 획득 별점 (0 ~ 3)
        self.chapter_stars: Dict[str, int] = {cid: 0 for cid in CHAPTER_ORDER}

        # 32강 월드 포차 그랑프리 진행 라운드 (0:32강, 1:16강, 2:8강, 3:4강, 4:결승, 5:전세계 제패)
        self.tournament_round_idx: int = 0
        self.ai_opponent_id: str = ""

        # 사운드 및 화면 해상도 옵션 설정 (데이터 초기화 시에도 사용자 환경설정은 유지)
        if not hasattr(self, "settings") or not isinstance(getattr(self, "settings", None), dict):
            self.settings: Dict[str, Any] = {
                "master_volume": 0.80,
                "sfx_volume": 0.80,
                "bgm_volume": 0.45,
                "sound_enabled": True,
                "bgm_enabled": True,
                "resolution": [1280, 720],
                "fullscreen": False,
            }

        # 일일 영업/콤보/액티브 스킬 런타임 상태
        self.daily_gold: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.combo_timer: float = 0.0
        self.served_customers: int = 0
        self.missed_customers: int = 0
        self.skill_cooldown: float = 0.0
        self.skill_active_timer: float = 0.0

    def reset(self) -> None:
        """reset_state()의 별칭."""
        self.reset_state()

    # ==========================================================================
    # 골드 관리 헬퍼
    # ==========================================================================
    def add_gold(self, amount: int) -> int:
        """골드를 추가하고 변경된 보유 골드를 반환한다."""
        add_val = max(0, int(amount))
        self.gold += add_val
        self.total_earned_gold += add_val
        return self.gold

    def spend_gold(self, amount: int) -> bool:
        """보유 골드가 충분하면 차감하고 True를 반환한다."""
        cost = max(0, int(amount))
        if self.gold < cost:
            return False
        self.gold -= cost
        return True

    # ==========================================================================
    # 주인공(포차 마스터) 해금 및 선택
    # ==========================================================================
    def is_character_unlocked(self, char_id: str) -> bool:
        """해당 주인공이 해금되었는지 여부를 반환한다."""
        if char_id not in CHARACTERS:
            return False
        if CHARACTERS[char_id].get("unlocked_by_default", False):
            return True
        return char_id in self.unlocked_characters

    def can_unlock_character(self, char_id: str) -> bool:
        """현재 골드와 챕터 해금 조건으로 해당 주인공을 해금할 수 있는지 확인한다."""
        if char_id not in CHARACTERS:
            return False
        if self.is_character_unlocked(char_id):
            return False
        char_data = CHARACTERS[char_id]
        req_chapter = char_data.get("unlock_chapter")
        if req_chapter and req_chapter not in self.unlocked_chapters:
            return False
        cost = int(char_data.get("unlock_cost", 0))
        return self.gold >= cost

    def unlock_character(self, char_id: str, force_free: bool = False) -> bool:
        """
        주인공을 해금한다.
        force_free=False이면 해금 조건(챕터 해금 및 골드 비용)을 확인 후 골드를 차감한다.
        """
        if char_id not in CHARACTERS:
            return False
        if self.is_character_unlocked(char_id):
            return True

        char_data = CHARACTERS[char_id]
        if not force_free:
            req_chapter = char_data.get("unlock_chapter")
            if req_chapter and req_chapter not in self.unlocked_chapters:
                return False
            cost = int(char_data.get("unlock_cost", 0))
            if not self.spend_gold(cost):
                return False

        if char_id not in self.unlocked_characters:
            self.unlocked_characters.append(char_id)
        return True

    def select_character(self, char_id: str) -> bool:
        """해금된 주인공을 현재 플레이 캐릭터로 선택한다."""
        if char_id not in CHARACTERS:
            return False
        if not self.is_character_unlocked(char_id):
            return False
        self.selected_character = char_id
        return True

    def get_selected_character_data(self) -> AttrDict:
        """현재 선택된 주인공의 데이터(AttrDict)를 반환한다."""
        return get_character(self.selected_character)

    def get_character_data(self, char_id: Optional[str] = None) -> AttrDict:
        """특정 주인공(생략 시 현재 주인공)의 데이터를 반환한다."""
        return get_character(char_id or self.selected_character)

    # ==========================================================================
    # 챕터 해금, 선택 및 게임 모드 전환
    # ==========================================================================
    def is_chapter_unlocked(self, chapter_id: str) -> bool:
        """챕터 해금 여부를 반환한다."""
        cid = chapter_id.upper()
        if cid not in CHAPTERS:
            return False
        if CHAPTERS[cid].get("unlocked_by_default", False):
            return True
        return cid in self.unlocked_chapters

    def can_unlock_chapter(self, chapter_id: str) -> bool:
        """해당 챕터를 해금할 수 있는지(이전 챕터 해금 및 골드 보유) 반환한다."""
        cid = chapter_id.upper()
        if cid not in CHAPTERS or self.is_chapter_unlocked(cid):
            return False
        ch_data = CHAPTERS[cid]
        prev_ch = ch_data.get("required_prev_chapter")
        if prev_ch and prev_ch not in self.unlocked_chapters:
            return False
        cost = int(ch_data.get("unlock_cost", 0))
        return self.gold >= cost

    def unlock_chapter(self, chapter_id: str, force_free: bool = False) -> bool:
        """
        챕터를 해금한다.
        force_free=False이면 이전 챕터 해금 여부와 골드 비용을 확인하고 차감한다.
        """
        cid = chapter_id.upper()
        if cid not in CHAPTERS:
            return False
        if self.is_chapter_unlocked(cid):
            return True

        ch_data = CHAPTERS[cid]
        if not force_free:
            prev_ch = ch_data.get("required_prev_chapter")
            if prev_ch and prev_ch not in self.unlocked_chapters:
                return False
            cost = int(ch_data.get("unlock_cost", 0))
            if not self.spend_gold(cost):
                return False

        if cid not in self.unlocked_chapters:
            self.unlocked_chapters.append(cid)
        return True

    def select_chapter(self, chapter_id: str) -> bool:
        """해금된 챕터를 현재 챕터로 선택하고 월드 투어 모드로 설정한다."""
        cid = chapter_id.upper()
        if cid not in CHAPTERS:
            return False
        if not self.is_chapter_unlocked(cid):
            return False
        self.current_chapter = cid
        self.day = self.chapter_days.get(cid, 1)
        return True

    def set_mode(self, mode: str) -> bool:
        """게임 모드를 'WORLD_TOUR', 'GLOBAL_ENDLESS', 또는 'SPECIALIST'로 설정한다."""
        mode_upper = mode.upper()
        if mode_upper not in ("WORLD_TOUR", "GLOBAL_ENDLESS", "SPECIALIST"):
            return False
        self.mode = mode_upper
        if mode_upper == "SPECIALIST":
            self.day = self.specialist_days.get(self.selected_specialist, 1)
        elif mode_upper == "GLOBAL_ENDLESS":
            self.day = max(1, int(getattr(self, "endless_day", 1)))
        elif mode_upper == "WORLD_TOUR":
            self.day = self.chapter_days.get(self.current_chapter, 1)
        return True

    def select_specialist(self, spec_id: str) -> bool:
        """오픈된 단일 메뉴 장인 전문점을 선택하고 SPECIALIST 모드로 전환한다."""
        key = str(spec_id or "").lower()
        if key not in SPECIALIST_MENUS:
            return False
        if not bool(SPECIALIST_MENUS[key].get("is_open", False)):
            return False
        self.selected_specialist = key
        self.mode = "SPECIALIST"
        self.day = self.specialist_days.get(key, 1)
        return True

    def get_selected_specialist_data(self) -> AttrDict:
        """현재 선택된 단일 메뉴 장인 전문점 메타데이터를 반환한다."""
        return get_specialist_menu(getattr(self, "selected_specialist", "bungeo"))

    def set_global_loadout(
        self,
        slot_or_mapping: Union[str, Dict[str, str]],
        station_id: Optional[str] = None,
    ) -> bool:
        """
        글로벌 야시장 통합 모드용 조리대 로드아웃을 설정한다.
        - set_global_loadout("mold", "jp_takoyaki_pan") 형태 또는
        - set_global_loadout({"mold": "jp_takoyaki_pan", ...}) 형태를 모두 지원한다.
        """
        if isinstance(slot_or_mapping, dict):
            success = True
            for slt, st_id in slot_or_mapping.items():
                if not self.set_global_loadout(slt, st_id):
                    success = False
            return success

        slot_type = slot_or_mapping
        if slot_type not in SLOT_TYPES or not station_id:
            return False
        st_meta = STATIONS_CATALOG.get(station_id)
        if not st_meta or st_meta["slot_type"] != slot_type:
            return False
        self.global_loadout[slot_type] = station_id
        return True

    # ==========================================================================
    # 활성 조리 기구 4종 및 활성 레시피 목록 조회
    # ==========================================================================
    def get_active_stations(self) -> AttrDict:
        """
        현재 모드와 챕터(또는 글로벌 로드아웃)에 따라 장착된 4개 슬롯의 조리 기구 정보를 반환한다.
        반환값은 {'mold': StationRef, 'grill': StationRef, 'batch_pot': StationRef, 'dispenser': StationRef}
        형태의 AttrDict이며, 각 값(StationRef)은 기구 ID 문자열('kr_bungeoppang')과
        기구 메타데이터 딕셔너리(station['name'], station['recipes'] 등) 양쪽으로 모두 호환된다.
        """
        if self.mode == "GLOBAL_ENDLESS":
            raw_map = dict(self.global_loadout)
        else:
            chapter_data = get_chapter(self.current_chapter)
            raw_map = dict(chapter_data["default_stations"])

        result = AttrDict()
        for slot_type in SLOT_TYPES:
            st_id = raw_map.get(slot_type, CHAPTERS["KR"]["default_stations"][slot_type])
            if st_id not in STATIONS_CATALOG:
                st_id = CHAPTERS["KR"]["default_stations"][slot_type]
            result[slot_type] = StationRef(st_id)
        return result

    def get_active_station_ids(self) -> List[str]:
        """현재 활성화된 4개 조리 기구의 station_id 문자열 리스트를 순서대로 반환한다."""
        active = self.get_active_stations()
        return [str(active[slot]) for slot in SLOT_TYPES]

    def get_active_station_metas(self) -> Dict[str, AttrDict]:
        """현재 활성화된 4개 조리 기구의 슬롯별 STATIONS_CATALOG 메타데이터 딕셔너리를 반환한다."""
        active = self.get_active_stations()
        return {slot: STATIONS_CATALOG[str(active[slot])] for slot in SLOT_TYPES}

    def get_active_recipes(self, base_only: bool = False) -> List[AttrDict]:
        """
        현재 장착된 4개 조리 기구(또는 단일 메뉴 장인 전문점)에서 생산/주문 가능한 모든 레시피(AttrDict) 리스트를 반환한다.
        base_only=True이면 토핑이 올라가지 않은 베이스 레시피만 반환한다.
        """
        if str(self.mode).upper() == "SPECIALIST":
            spec = self.get_selected_specialist_data()
            rid_list = spec["base_recipes"] if base_only else spec["all_recipes"]
            return [RECIPES[rid] for rid in rid_list if rid in RECIPES]

        recipes_list: List[AttrDict] = []
        for st_id in self.get_active_station_ids():
            station_recipes = get_recipes_by_station(st_id, base_only=base_only)
            recipes_list.extend(station_recipes)
        return recipes_list

    def get_active_recipe_ids(self, base_only: bool = False) -> List[str]:
        """현재 주문 가능한 모든 레시피의 recipe_id 문자열 리스트를 반환한다."""
        return [r["id"] for r in self.get_active_recipes(base_only=base_only)]

    # ==========================================================================
    # 스토리 모드 단계별 조리기구/업그레이드 해금 조회 헬퍼
    # ==========================================================================
    def get_story_progression(self, day: Optional[int] = None) -> AttrDict:
        """현재 챕터·일차·모드의 스토리 단계별 해금 규칙(STORY_PROGRESSION)을 반환한다."""
        d = self.day if day is None else int(day)
        return get_day_progression(self.current_chapter, d, mode=self.mode)

    def is_slot_unlocked_in_story(self, slot_type: str, day: Optional[int] = None) -> bool:
        """현재 스토리 일차에서 지정 슬롯('mold', 'grill', 'batch_pot', 'dispenser', 'tray', 'skill')이 해금되었는지 반환한다."""
        d = self.day if day is None else int(day)
        return is_slot_unlocked(self.current_chapter, d, slot_type, mode=self.mode)

    def get_story_max_station_level(self, slot_type: str, day: Optional[int] = None) -> int:
        """현재 스토리 일차에서 상점 강화가 허용되는 해당 슬롯의 최대 레벨(0~3)을 반환한다."""
        d = self.day if day is None else int(day)
        return get_max_station_upgrade_level(self.current_chapter, d, slot_type, mode=self.mode)

    def is_interior_unlocked_in_story(self, interior_id: str, day: Optional[int] = None) -> bool:
        """현재 스토리 일차에서 해당 포차 인테리어 구매가 허용되는지 반환한다."""
        d = self.day if day is None else int(day)
        return str(interior_id) in get_unlocked_interiors(self.current_chapter, d, mode=self.mode)

    def get_orderable_recipes(self, base_only: bool = False) -> List[AttrDict]:
        """
        스토리 모드 단계별 해금 상태(unlocked_slots)를 반영하여
        현재 일차의 손님이 실제로 주문할 수 있는 레시피 리스트만 필터링해 반환한다.
        - 해금되지 않은 조리 기구(slot_type)의 메뉴는 제외
        - 조립 트레이('tray')가 해금되기 전(KR Day 1~2)에는 토핑 메뉴 제외
        """
        all_active = self.get_active_recipes(base_only=base_only)
        if str(self.mode).upper() != "WORLD_TOUR":
            return all_active

        unlocked_cooking = set(get_unlocked_cooking_slots(self.current_chapter, self.day, mode=self.mode))
        tray_unlocked = self.is_slot_unlocked_in_story("tray")

        filtered: List[AttrDict] = []
        for rec in all_active:
            if str(rec.get("slot_type")) not in unlocked_cooking:
                continue
            if not tray_unlocked and bool(rec.get("has_topping", False)):
                continue
            filtered.append(rec)

        return filtered if filtered else all_active

    # ==========================================================================
    # 기구 및 인테리어 업그레이드 관리
    # ==========================================================================
    def get_station_level(self, key: str) -> int:
        """지정한 기구 슬롯('mold' 또는 'mold_upgrade')의 현재 업그레이드 레벨(0~3)을 반환한다."""
        return int(self.station_levels[key])

    def get_station_upgrade_cost(self, key: str) -> Optional[int]:
        """다음 단계 기구 업그레이드 비용을 반환한다. 이미 최대 레벨(Lv.3)이면 None 반환."""
        curr = self.get_station_level(key)
        return get_next_station_upgrade_cost(key, curr)

    def can_upgrade_station(self, key: str) -> bool:
        """해당 기구를 다음 레벨로 업그레이드할 수 있는지(최대 레벨 미만 & 골드 충분) 반환한다."""
        cost = self.get_station_upgrade_cost(key)
        if cost is None:
            return False
        return self.gold >= cost

    def upgrade_station(self, key: str, force_free: bool = False) -> bool:
        """기구를 1단계 업그레이드한다."""
        norm_key = normalize_station_upgrade_key(key)
        if norm_key not in STATION_UPGRADES:
            return False
        cost = self.get_station_upgrade_cost(norm_key)
        if cost is None:
            return False
        if not force_free and not self.spend_gold(cost):
            return False
        self.station_levels[norm_key] = self.get_station_level(norm_key) + 1
        return True

    def get_interior_level(self, interior_id: str) -> int:
        """인테리어 아이템의 현재 레벨(0 또는 1)을 반환한다."""
        return int(self.interior_levels.get(interior_id, 0))

    def get_interior_upgrade_cost(self, interior_id: str) -> Optional[int]:
        """인테리어 아이템의 구매/업그레이드 비용을 반환한다. 이미 구매 완료면 None 반환."""
        curr = self.get_interior_level(interior_id)
        return get_next_interior_upgrade_cost(interior_id, curr)

    def can_upgrade_interior(self, interior_id: str) -> bool:
        """인테리어를 구매/업그레이드할 수 있는지 여부를 반환한다."""
        cost = self.get_interior_upgrade_cost(interior_id)
        if cost is None:
            return False
        return self.gold >= cost

    def upgrade_interior(self, interior_id: str, force_free: bool = False) -> bool:
        """포차 인테리어를 구매/업그레이드한다."""
        if interior_id not in INTERIOR_UPGRADES:
            return False
        cost = self.get_interior_upgrade_cost(interior_id)
        if cost is None:
            return False
        if not force_free and not self.spend_gold(cost):
            return False
        self.interior_levels[interior_id] = self.get_interior_level(interior_id) + 1
        return True

    # ==========================================================================
    # 주인공 패시브 + 기구/인테리어 업그레이드가 반영된 스탯 계산 헬퍼
    # ==========================================================================
    def _resolve_slot_type(
        self,
        slot_type: Optional[str] = None,
        station_or_recipe_id: Optional[str] = None,
    ) -> str:
        if slot_type and slot_type in ("mold", "grill", "batch_pot", "dispenser", "tray"):
            return slot_type
        if station_or_recipe_id:
            if station_or_recipe_id in STATIONS_CATALOG:
                return str(STATIONS_CATALOG[station_or_recipe_id]["slot_type"])
            if station_or_recipe_id in RECIPES:
                return str(RECIPES[station_or_recipe_id]["slot_type"])
            if station_or_recipe_id in SLOT_TO_UPGRADE_KEY:
                norm = SLOT_TO_UPGRADE_KEY[station_or_recipe_id]
                return str(STATION_UPGRADES[norm]["slot_type"])
        return "mold"

    def get_cook_speed_multiplier(
        self,
        slot_type: Optional[str] = None,
        station_id: Optional[str] = None,
    ) -> float:
        """
        슬롯 타입/기구별 최종 조리 속도 배율을 계산하여 반환한다.
        - 기구 업그레이드 배율 반영
        - 김포차(chef_kr) 패시브: 몰드/철판 등 조리 속도 +15% (1.15배)
        - 메이링(chef_tw) 패시브: 음료 디스펜서 충전 속도 +40% (1.40배)
        - 김포차 액티브 스킬(k_pocha_rush) 지속 중일 때 조리 속도 2배
        """
        resolved_slot = self._resolve_slot_type(slot_type, station_id)
        lvl = self.get_station_level(resolved_slot)
        lvl_stats = get_station_level_stats(resolved_slot, lvl)
        mult = float(lvl_stats.get("cook_speed_mult", 1.0))

        char = self.get_selected_character_data()
        passive = char["passive"]

        # 김포차 패시브: 몰드/철판(mold, grill, batch_pot) 및 기본 조리 속도 +15%
        if float(passive.get("cook_speed_mult", 1.0)) > 1.0:
            if resolved_slot in ("mold", "grill", "batch_pot"):
                mult *= float(passive["cook_speed_mult"])

        # 메이링 패시브: 음료 디스펜서 충전 속도 +40%
        if resolved_slot == "dispenser" and float(passive.get("dispenser_speed_mult", 1.0)) > 1.0:
            mult *= float(passive["dispenser_speed_mult"])

        return round(mult, 4)

    # 별칭 호환
    get_cook_speed_mult = get_cook_speed_multiplier

    def get_cook_time(
        self,
        recipe_or_station_id: str,
        slot_type: Optional[str] = None,
    ) -> float:
        """패시브와 업그레이드가 반영된 실제 조리 소요 시간(초)을 반환한다."""
        base_time = 4.5
        if recipe_or_station_id in RECIPES:
            rec = RECIPES[recipe_or_station_id]
            base_time = float(rec["cook_time"])
            slot_type = slot_type or str(rec["slot_type"])
        elif recipe_or_station_id in STATIONS_CATALOG:
            st = STATIONS_CATALOG[recipe_or_station_id]
            base_time = float(st["base_cook_time"])
            slot_type = slot_type or str(st["slot_type"])

        speed_mult = self.get_cook_speed_multiplier(slot_type=slot_type, station_id=recipe_or_station_id)
        return round(max(0.4, base_time / max(0.1, speed_mult)), 3)

    def get_burn_time_multiplier(
        self,
        slot_type: Optional[str] = None,
        station_id: Optional[str] = None,
    ) -> float:
        """
        음식이 타기까지 걸리는 시간의 지연 배율을 반환한다.
        - 기구 업그레이드 배율 및 트레이(tray) 업그레이드 보온 배율 반영
        - 켄지(chef_jp) 패시브: 음식 타는 시간 50% 지연 (1.50배)
        """
        resolved_slot = self._resolve_slot_type(slot_type, station_id)
        lvl = self.get_station_level(resolved_slot)
        lvl_stats = get_station_level_stats(resolved_slot, lvl)
        mult = float(lvl_stats.get("burn_time_mult", 1.0))

        if resolved_slot != "tray":
            tray_lvl = self.get_station_level("tray")
            if tray_lvl > 0:
                tray_stats = get_station_level_stats("tray", tray_lvl)
                mult *= float(tray_stats.get("burn_time_mult", 1.0))

        char = self.get_selected_character_data()
        passive = char["passive"]
        if float(passive.get("burn_time_mult", 1.0)) > 1.0:
            mult *= float(passive["burn_time_mult"])

        return round(mult, 4)

    # 별칭 호환
    get_burn_time_mult = get_burn_time_multiplier

    def get_burn_time(
        self,
        recipe_or_station_id: str,
        slot_type: Optional[str] = None,
    ) -> float:
        """패시브와 업그레이드가 반영된 실제 타는 시간(초)을 반환한다."""
        base_burn = 9.0
        if recipe_or_station_id in RECIPES:
            rec = RECIPES[recipe_or_station_id]
            base_burn = float(rec["burn_time"])
            slot_type = slot_type or str(rec["slot_type"])
        elif recipe_or_station_id in STATIONS_CATALOG:
            st = STATIONS_CATALOG[recipe_or_station_id]
            base_burn = float(st["base_burn_time"])
            slot_type = slot_type or str(st["slot_type"])

        if slot_type == "dispenser":
            return 999.0

        burn_mult = self.get_burn_time_multiplier(slot_type=slot_type, station_id=recipe_or_station_id)
        return round(base_burn * burn_mult, 3)

    def get_station_slot_count(self, slot_type: str) -> int:
        """
        기구 슬롯 수(또는 대량 조리 팬의 경우 1회 생산 인분 수)를 반환한다.
        - mold, grill, dispenser, tray: 기본 2칸 + 업그레이드 보너스 (최대 4~5칸)
        - batch_pot: 기본 3인분 + 업그레이드 보너스(최대 +3) + 메이링 패시브(+1인분)
        """
        if slot_type == "batch_pot":
            return self.get_batch_servings()
        lvl = self.get_station_level(slot_type)
        lvl_stats = get_station_level_stats(slot_type, lvl)
        return int(lvl_stats.get("total_slots", 2))

    # 별칭 호환
    get_slot_count = get_station_slot_count

    def get_batch_servings(self) -> int:
        """
        대량 조리 팬(batch_pot)의 1회 조리 시 생성되는 총 인분 수를 반환한다.
        - 기본 3인분 + 대량팬 업그레이드 보너스(0~3) + 메이링(chef_tw) 패시브(+1인분)
        """
        lvl = self.get_station_level("batch_pot")
        lvl_stats = get_station_level_stats("batch_pot", lvl)
        servings = int(lvl_stats.get("total_slots", config.BASE_BATCH_SERVINGS))

        char = self.get_selected_character_data()
        extra = int(char["passive"].get("batch_extra_servings", 0))
        return servings + extra

    def get_tray_slot_count(self) -> int:
        """보조 서빙 트레이의 슬롯 수를 반환한다."""
        return self.get_station_slot_count("tray")

    def get_recipe_price(self, recipe_id: str) -> int:
        """
        주인공 패시브 및 오늘의 인기 메뉴 축제 보너스가 반영된 레시피 판매 가격(원)을 계산하여 반환한다.
        - 김포차(chef_kr) 패시브: 한국(KR) 메뉴 판매가 +10%
        - 글로벌 마스터 패시브: passive_desc에 '모든 메뉴'/'전체 메뉴'가 포함된 경우 국가 제한 없이 kr_price_bonus 적용
        - 디에고(chef_mx) 패시브: 토핑 메뉴(has_topping=True) 판매가 +20%
        - 오늘의 야시장 축제 인기 메뉴(featured_id): +20% 축제 가격 보너스
        """
        rec = get_recipe(recipe_id)
        if not rec:
            return 0
        price = float(rec["price"])
        char = self.get_selected_character_data()
        passive = char["passive"]
        passive_desc = str(char.get("passive_desc", ""))

        kr_bonus = float(passive.get("kr_price_bonus", 1.0))
        if kr_bonus > 1.0:
            is_global_menu_bonus = (
                ("모든 메뉴" in passive_desc)
                or ("전체 메뉴" in passive_desc)
                or ("기본 메뉴" in passive_desc and not rec.get("has_topping", False))
            )
            if is_global_menu_bonus or rec["country"] == "KR" or rec["country"] == char.get("country"):
                price *= kr_bonus

        if rec.get("has_topping", False) and float(passive.get("topping_price_mult", 1.0)) > 1.0:
            price *= float(passive["topping_price_mult"])

        # 아성(chef_tw_kaohsiung) 액티브 스킬: 8초간 대량팬·그릴 판매가 1.5배
        if (
            self.skill_active_timer > 0.0
            and self.selected_character == "chef_tw_kaohsiung"
            and str(rec.get("slot_type", "")) in ("batch_pot", "grill")
        ):
            price *= 1.50

        # 오늘의 야시장 축제 인기 메뉴(featured_id)일 경우 +20% 축제 가격 보너스
        fest_info = self.get_daily_festival_info()
        if fest_info.get("featured_id") == recipe_id:
            price *= 1.20

        # 10원 단위 반올림
        return int(round(price / 10.0) * 10)

    # 별칭 호환
    get_menu_price = get_recipe_price

    def get_combo_tip_multiplier(self) -> float:
        """
        콤보 보너스 팁 배율을 반환한다.
        - 켄지(chef_jp) 패시브: 콤보 보너스 팁 +25% (1.25배)
        - 7080 감성 라디오(retro_radio) 인테리어: 콤보 보너스 팁 +25% (1.25배)
        - 디에고 액티브 스킬(fiesta_fever) 등 발동 중: 서빙 팁 배율 상승
        """
        mult = 1.0
        char = self.get_selected_character_data()
        passive = char["passive"]
        if float(passive.get("combo_tip_mult", 1.0)) > 1.0:
            mult *= float(passive["combo_tip_mult"])

        if self.get_interior_level("retro_radio") > 0:
            mult *= float(INTERIOR_UPGRADES["retro_radio"]["combo_tip_mult"])

        if self.skill_active_timer > 0.0:
            if self.selected_character == "chef_in_kolkata":
                mult *= 1.8
            elif (
                self.selected_character in ("chef_jp_hokkaido", "chef_cn_beijing")
                or (
                    self.selected_character not in ("chef_tw_kaohsiung", "chef_cn_shanghai")
                    and (
                        char.get("skill_id") == "fiesta_fever"
                        or str(char.get("skill_effect", "")) in ("mx_fiesta", "instant_and_tip", "heal_and_tip")
                    )
                )
            ):
                mult *= 2.0

        return round(mult, 4)

    def get_pochasta_rank(self) -> AttrDict:
        """
        [데이브 더 다이버 '쿡스타' 벤치마킹] 포차스타(Pocha-sta) 글로벌 SNS 등급 및 팔로워 정보를 반환한다.
        획득 별점 총합, 해금된 셰프 수, 누적 매출을 기반으로 산출하며 등급별 VIP 등장 확률 보너스(0%~8%)를 부여한다.
        """
        total_stars = sum(int(v) for v in self.chapter_stars.values())
        unlocked_cnt = len(self.unlocked_characters)
        score = total_stars * 120 + unlocked_cnt * 45 + int(self.total_earned_gold // 500)
        followers = max(120, score * 18)

        if score >= 3500:
            return AttrDict({"tier": "👑 다이아몬드 포차", "followers": followers, "vip_bonus": 0.08, "badge_color": (118, 232, 255), "desc": "전세계 야시장의 살아있는 전설 (VIP 확률 +8%)"})
        elif score >= 2000:
            return AttrDict({"tier": "💎 플래티넘 포차", "followers": followers, "vip_bonus": 0.06, "badge_color": (198, 152, 255), "desc": "글로벌 미식가들의 성지 (VIP 확률 +6%)"})
        elif score >= 950:
            return AttrDict({"tier": "🥇 골드 포차", "followers": followers, "vip_bonus": 0.04, "badge_color": (255, 212, 68), "desc": "전국구 웨이팅 핫플레이스 (VIP 확률 +4%)"})
        elif score >= 350:
            return AttrDict({"tier": "🥈 실버 포차", "followers": followers, "vip_bonus": 0.02, "badge_color": (205, 218, 235), "desc": "입소문 난 동네 야시장 맛집 (VIP 확률 +2%)"})
        return AttrDict({"tier": "🥉 브론즈 포차", "followers": followers, "vip_bonus": 0.0, "badge_color": (218, 142, 88), "desc": "새롭게 떠오르는 루키 포장마차"})

    def get_daily_festival_info(self) -> AttrDict:
        """
        [데이브 더 다이버 '파티/특선 메뉴' 벤치마킹] 오늘의 야시장 테마 및 시그니처 메뉴 정보를 반환한다.
        """
        active_recs = self.get_orderable_recipes(base_only=False)
        if not active_recs:
            return AttrDict({"title": "야시장 개장일", "featured_id": "", "featured_name": "전 메뉴", "bonus_desc": "콤보 팁 활성화"})
        idx = (int(self.day) * 3 + len(self.current_chapter)) % len(active_recs)
        featured = active_recs[idx]
        themes = [
            "🔥 매운맛 열풍 데이",
            "📸 유튜버 먹방 축제",
            "🌙 심야 미식회 나이트",
            "🎉 로컬 스트리트 페스티벌",
        ]
        theme_title = themes[int(self.day) % len(themes)]
        return AttrDict({
            "title": theme_title,
            "featured_id": featured["id"],
            "featured_name": featured["name"],
            "bonus_desc": f"오늘의 인기 메뉴: {featured['name']} (판매가 +20%)",
        })

    def calculate_combo_tip(
        self,
        base_price: int,
        combo_count: Optional[int] = None,
        is_vip: bool = False,
    ) -> int:
        """연속 서빙 콤보 스택 및 VIP 여부에 따른 팁 금액(원)을 계산한다."""
        c_stack = self.combo if combo_count is None else int(combo_count)
        if c_stack <= 0 and not is_vip:
            return 0

        combo_rate = min(config.MAX_COMBO_TIP_RATE, max(0, c_stack) * config.COMBO_TIP_RATE)
        tip = float(base_price) * combo_rate * self.get_combo_tip_multiplier()

        if is_vip:
            vip_extra = float(base_price) * 0.25
            if self.skill_active_timer > 0.0 and self.selected_character == "chef_mx":
                vip_extra *= 2.0
            tip += vip_extra

        return int(round(tip / 10.0) * 10)

    def get_customer_patience_multiplier(self) -> float:
        """
        손님 최대 인내심 배율을 반환한다.
        - 포차 천막 & 알전구(awning_lights) 설치 시 +15% (1.15배)
        """
        mult = 1.0
        if self.get_interior_level("awning_lights") > 0:
            mult *= float(INTERIOR_UPGRADES["awning_lights"]["patience_mult"])
        return round(mult, 4)

    def get_max_customer_slots(self) -> int:
        """
        동시 대기 가능한 최대 손님 슬롯 수를 반환한다.
        - 기본 3명, 레트로 플라스틱 의자(plastic_chairs) 설치 시 4명
        """
        slots = config.BASE_MAX_CUSTOMERS
        if self.get_interior_level("plastic_chairs") > 0:
            slots += int(INTERIOR_UPGRADES["plastic_chairs"]["extra_customer_slots"])
        return min(config.MAX_CUSTOMER_SLOTS, slots)

    def get_vip_spawn_chance(self) -> float:
        """
        관광객/VIP 손님 등장 확률(0.0 ~ 1.0)을 반환한다.
        - 챕터 기본 VIP 확률 + 디에고(chef_mx) 패시브(+0.15) + 야시장 네온 입간판(+0.12) + 포차스타 등급 보너스(+0~0.08)
        """
        ch = get_chapter(self.current_chapter)
        chance = float(ch.get("vip_chance", config.BASE_VIP_CHANCE))

        char = self.get_selected_character_data()
        chance += float(char["passive"].get("vip_spawn_bonus", 0.0))

        if self.get_interior_level("neon_signboard") > 0:
            chance += float(INTERIOR_UPGRADES["neon_signboard"]["vip_spawn_bonus"])

        pochasta = self.get_pochasta_rank()
        chance += float(pochasta.get("vip_bonus", 0.0))

        return round(min(0.65, max(0.0, chance)), 4)

    # 별칭 호환
    get_vip_chance = get_vip_spawn_chance

    def get_target_gold(self, day: Optional[int] = None) -> int:
        """현재 모드, 챕터(또는 장인 전문점), 일차에 해당하는 일일 목표 매출액을 반환한다."""
        target_day = max(1, self.day if day is None else int(day))
        if str(self.mode).upper() == "SPECIALIST":
            spec = self.get_selected_specialist_data()
            base = int(spec.get("base_target_gold", 14000))
            growth = int(spec.get("daily_target_growth", 3600))
            return base + (target_day - 1) * growth
        return calculate_target_gold(self.current_chapter, target_day, mode=self.mode)

    def get_effective_stats(self) -> AttrDict:
        """현재 주인공 패시브와 모든 기구/인테리어 업그레이드가 반영된 통합 스탯 요약 정보를 반환한다."""
        return AttrDict(
            {
                "character_id": self.selected_character,
                "character_name": self.get_selected_character_data()["name"],
                "mode": self.mode,
                "chapter": self.current_chapter,
                "day": self.day,
                "gold": self.gold,
                "target_gold": self.get_target_gold(),
                "mold_slots": self.get_station_slot_count("mold"),
                "grill_slots": self.get_station_slot_count("grill"),
                "batch_servings": self.get_batch_servings(),
                "dispenser_slots": self.get_station_slot_count("dispenser"),
                "tray_slots": self.get_tray_slot_count(),
                "mold_speed_mult": self.get_cook_speed_multiplier("mold"),
                "grill_speed_mult": self.get_cook_speed_multiplier("grill"),
                "batch_speed_mult": self.get_cook_speed_multiplier("batch_pot"),
                "dispenser_speed_mult": self.get_cook_speed_multiplier("dispenser"),
                "burn_time_mult": self.get_burn_time_multiplier("mold"),
                "combo_tip_mult": self.get_combo_tip_multiplier(),
                "patience_mult": self.get_customer_patience_multiplier(),
                "max_customer_slots": self.get_max_customer_slots(),
                "vip_spawn_chance": self.get_vip_spawn_chance(),
            }
        )

    # ==========================================================================
    # 영업일(Day) 진행 및 서빙 보상 처리
    # ==========================================================================
    def start_day(self) -> None:
        """새로운 하루 영업을 시작하기 위해 일일 런타임 카운터를 초기화한다."""
        self.daily_gold = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_timer = 0.0
        self.served_customers = 0
        self.missed_customers = 0
        self.skill_cooldown = 0.0
        self.skill_active_timer = 0.0

    def add_combo(self, amount: int = 1) -> int:
        """연속 서빙 콤보를 추가하고 콤보 타이머 및 최고 콤보를 갱신한다."""
        self.combo = max(0, self.combo) + max(1, int(amount))
        self.max_combo = max(self.max_combo, self.combo)
        self.combo_timer = config.COMBO_WINDOW
        return self.combo

    def record_serve(
        self,
        recipe_id: str,
        is_vip: bool = False,
        extra_combo: int = 1,
    ) -> AttrDict:
        """
        손님에게 메뉴를 서빙했을 때 콤보 스택을 갱신하고 판매가 + 팁을 골드에 반영한다.
        """
        self.add_combo(extra_combo)
        self.served_customers += 1

        base_price = self.get_recipe_price(recipe_id)
        tip = self.calculate_combo_tip(base_price, combo_count=self.combo, is_vip=is_vip)
        total = base_price + tip

        self.daily_gold += total
        self.add_gold(total)

        return AttrDict(
            {
                "recipe_id": recipe_id,
                "base_price": base_price,
                "tip": tip,
                "total": total,
                "combo": self.combo,
                "is_vip": is_vip,
            }
        )

    def break_combo(self) -> None:
        """손님이 화내며 떠나거나 음식을 태웠을 때 콤보를 초기화한다."""
        self.combo = 0
        self.combo_timer = 0.0

    def complete_day(self, earned_gold: Optional[int] = None) -> AttrDict:
        """
        하루 영업을 종료하고 목표 달성 여부, 획득 별점(0~3), 일차 증가를 처리한다.
        - cleared == True (또는 GLOBAL_ENDLESS 모드)일 때만 다음 일차로 진행한다.
        - GLOBAL_ENDLESS 모드에서는 chapter_days를 덮어쓰지 않고 endless_day에 별도 저장한다.
        """
        actual_earned = self.daily_gold if earned_gold is None else int(earned_gold)
        target = self.get_target_gold(self.day)
        stars = calculate_stars(actual_earned, target)
        cleared = actual_earned >= target

        if self.mode == "WORLD_TOUR":
            prev_stars = self.chapter_stars.get(self.current_chapter, 0)
            self.chapter_stars[self.current_chapter] = max(prev_stars, stars)
        elif self.mode == "SPECIALIST":
            prev_stars = self.specialist_stars.get(self.selected_specialist, 0)
            self.specialist_stars[self.selected_specialist] = max(prev_stars, stars)

        completed_day = self.day
        self.last_played_day = completed_day
        self.last_day_cleared = bool(cleared)

        if cleared or self.mode == "GLOBAL_ENDLESS":
            self.day += 1
            if self.mode == "SPECIALIST":
                self.specialist_days[self.selected_specialist] = self.day
            elif self.mode == "GLOBAL_ENDLESS":
                self.endless_day = self.day
            else:
                self.chapter_days[self.current_chapter] = self.day

        return AttrDict(
            {
                "day": completed_day,
                "next_day": self.day,
                "earned_gold": actual_earned,
                "target_gold": target,
                "stars": stars,
                "cleared": cleared,
                "served_customers": self.served_customers,
                "missed_customers": self.missed_customers,
                "max_combo": self.max_combo,
            }
        )

    # ==========================================================================
    # 사운드·해상도 옵션 동기화 및 JSON 세이브 / 로드 관리
    # ==========================================================================
    def apply_runtime_settings(self, apply_display: bool = True) -> None:
        """현재 self.settings에 저장된 사운드 볼륨 및 화면 해상도/창모드 설정을 런타임에 즉시 반영한다."""
        if not hasattr(self, "settings") or not isinstance(self.settings, dict):
            return
        try:
            from core.effects import sound_fx
            sound_fx.apply_settings(self.settings)
        except Exception:
            pass
        if apply_display:
            res = self.settings.get("resolution", [1280, 720])
            rw, rh = (int(res[0]), int(res[1])) if isinstance(res, (list, tuple)) and len(res) == 2 else (1280, 720)
            fs = bool(self.settings.get("fullscreen", False))
            config.apply_display_mode(rw, rh, fullscreen=fs)

    def to_dict(self) -> Dict[str, Any]:
        """현재 GameManager의 영구 저장 데이터를 JSON 직렬화 가능한 딕셔너리로 변환한다."""
        return {
            "mode": self.mode,
            "current_chapter": self.current_chapter,
            "selected_character": self.selected_character,
            "unlocked_characters": list(self.unlocked_characters),
            "unlocked_chapters": list(self.unlocked_chapters),
            "global_loadout": dict(self.global_loadout),
            "gold": int(self.gold),
            "total_earned_gold": int(self.total_earned_gold),
            "day": int(self.day),
            "endless_day": int(getattr(self, "endless_day", 1)),
            "last_played_day": int(getattr(self, "last_played_day", self.day)),
            "last_day_cleared": bool(getattr(self, "last_day_cleared", False)),
            "chapter_days": dict(self.chapter_days),
            "selected_specialist": getattr(self, "selected_specialist", "bungeo"),
            "specialist_days": dict(getattr(self, "specialist_days", {})),
            "specialist_stars": dict(getattr(self, "specialist_stars", {})),
            "station_levels": {k: int(self.station_levels[k]) for k in STATION_UPGRADE_ORDER},
            "interior_levels": {k: int(self.interior_levels.get(k, 0)) for k in INTERIOR_UPGRADE_ORDER},
            "chapter_stars": {k: int(self.chapter_stars.get(k, 0)) for k in CHAPTER_ORDER},
            "tournament_round_idx": int(getattr(self, "tournament_round_idx", 0)),
            "settings": dict(getattr(self, "settings", {})),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """딕셔너리로부터 GameManager 상태를 복원한다."""
        if not isinstance(data, dict):
            return

        raw_settings = data.get("settings")
        if isinstance(raw_settings, dict):
            if not hasattr(self, "settings") or not isinstance(self.settings, dict):
                self.settings = {}
            self.settings["master_volume"] = round(max(0.0, min(1.0, float(raw_settings.get("master_volume", 0.80)))), 2)
            self.settings["sfx_volume"] = round(max(0.0, min(1.0, float(raw_settings.get("sfx_volume", 0.80)))), 2)
            self.settings["bgm_volume"] = round(max(0.0, min(1.0, float(raw_settings.get("bgm_volume", 0.45)))), 2)
            self.settings["sound_enabled"] = bool(raw_settings.get("sound_enabled", True))
            self.settings["bgm_enabled"] = bool(raw_settings.get("bgm_enabled", True))
            res = raw_settings.get("resolution", [1280, 720])
            if isinstance(res, (list, tuple)) and len(res) == 2:
                rw, rh = int(res[0]), int(res[1])
                if (rw, rh) in config.RESOLUTION_PRESETS:
                    self.settings["resolution"] = [rw, rh]
                else:
                    self.settings["resolution"] = [1280, 720]
            self.settings["fullscreen"] = bool(raw_settings.get("fullscreen", False))
            self.apply_runtime_settings(apply_display=False)

        mode = str(data.get("mode", "WORLD_TOUR")).upper()
        self.mode = mode if mode in ("WORLD_TOUR", "GLOBAL_ENDLESS", "SPECIALIST") else "WORLD_TOUR"
        self.tournament_round_idx = max(0, min(5, int(data.get("tournament_round_idx", 0))))

        sel_spec = str(data.get("selected_specialist", "bungeo")).lower()
        self.selected_specialist = sel_spec if (sel_spec in SPECIALIST_MENUS and SPECIALIST_MENUS[sel_spec].get("is_open", False)) else "bungeo"
        raw_spec_days = data.get("specialist_days", {})
        if isinstance(raw_spec_days, dict):
            for sid in SPECIALIST_ORDER:
                if sid in raw_spec_days:
                    self.specialist_days[sid] = max(1, int(raw_spec_days[sid]))
        raw_spec_stars = data.get("specialist_stars", {})
        if isinstance(raw_spec_stars, dict):
            for sid in SPECIALIST_ORDER:
                if sid in raw_spec_stars:
                    self.specialist_stars[sid] = max(0, min(3, int(raw_spec_stars[sid])))

        ch = str(data.get("current_chapter", "KR")).upper()
        self.current_chapter = ch if ch in CHAPTERS else "KR"

        sel_char = str(data.get("selected_character", "chef_kr"))
        self.selected_character = sel_char if sel_char in CHARACTERS else "chef_kr"

        raw_chars = data.get("unlocked_characters", ["chef_kr"])
        self.unlocked_characters = [c for c in raw_chars if c in CHARACTERS]
        if "chef_kr" not in self.unlocked_characters:
            self.unlocked_characters.insert(0, "chef_kr")

        raw_chaps = data.get("unlocked_chapters", ["KR"])
        self.unlocked_chapters = [c.upper() for c in raw_chaps if c.upper() in CHAPTERS]
        if "KR" not in self.unlocked_chapters:
            self.unlocked_chapters.insert(0, "KR")

        raw_loadout = data.get("global_loadout", {})
        if isinstance(raw_loadout, dict):
            for slot_type in SLOT_TYPES:
                st_id = raw_loadout.get(slot_type)
                if st_id in STATIONS_CATALOG and STATIONS_CATALOG[st_id]["slot_type"] == slot_type:
                    self.global_loadout[slot_type] = st_id

        self.gold = max(0, int(data.get("gold", 3000)))
        self.total_earned_gold = max(0, int(data.get("total_earned_gold", self.gold)))
        self.day = max(1, int(data.get("day", 1)))
        self.endless_day = max(1, int(data.get("endless_day", 1)))
        self.last_played_day = max(1, int(data.get("last_played_day", self.day)))
        self.last_day_cleared = bool(data.get("last_day_cleared", False))

        raw_ch_days = data.get("chapter_days", {})
        if isinstance(raw_ch_days, dict):
            for cid in CHAPTER_ORDER:
                if cid in raw_ch_days:
                    self.chapter_days[cid] = max(1, int(raw_ch_days[cid]))

        raw_st_levels = data.get("station_levels", {})
        if isinstance(raw_st_levels, dict):
            self.station_levels = StationLevelDict(raw_st_levels)

        raw_in_levels = data.get("interior_levels", {})
        if isinstance(raw_in_levels, dict):
            for iid in INTERIOR_UPGRADE_ORDER:
                max_lvl = int(INTERIOR_UPGRADES[iid]["max_level"])
                val = int(raw_in_levels.get(iid, 0))
                self.interior_levels[iid] = max(0, min(val, max_lvl))

        raw_stars = data.get("chapter_stars", {})
        if isinstance(raw_stars, dict):
            for cid in CHAPTER_ORDER:
                val = int(raw_stars.get(cid, 0))
                self.chapter_stars[cid] = max(0, min(val, 3))

    def save_game(self, filepath: Optional[str] = None) -> bool:
        """현재 게임 진행 상태를 JSON 파일(원자적 임시 파일 교체) 또는 웹앱 브라우저 localStorage로 저장한다."""
        payload_str = json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        if sys.platform == "emscripten":
            try:
                import platform
                platform.window.localStorage.setItem("pocha_tycoon_save_v1", payload_str)
            except Exception:
                pass
        target_path = filepath or self.save_path
        if not target_path:
            return sys.platform == "emscripten"
        try:
            abs_target = os.path.abspath(target_path)
            parent_dir = os.path.dirname(abs_target)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            tmp_path = f"{abs_target}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(payload_str)
                f.flush()
            os.replace(tmp_path, abs_target)
            return True
        except Exception:
            return sys.platform == "emscripten"

    def load_game(self, filepath: Optional[str] = None) -> bool:
        """JSON 세이브 파일(또는 웹앱 브라우저 localStorage)에서 게임 진행 상태를 불러온다."""
        if sys.platform == "emscripten" and not filepath:
            try:
                import platform
                raw_ls = platform.window.localStorage.getItem("pocha_tycoon_save_v1")
                if raw_ls:
                    data = json.loads(str(raw_ls))
                    self.from_dict(data)
                    return True
            except Exception:
                pass
        target_path = filepath or self.save_path
        if not target_path or not os.path.isfile(target_path):
            return False
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.from_dict(data)
            return True
        except Exception:
            return False


# 모듈 레벨 기본 공유 인스턴스
game_manager: GameManager = GameManager()
