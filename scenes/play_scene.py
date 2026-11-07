"""
scenes/play_scene.py
'전세계 길거리 음식 포차 타이쿤' 1인칭 포차 카운터 영업 씬 (PlayScene).
- 상단 HUD (y=0~65): 모드/국가/Day, 남은 영업 타이머 바, 현재/목표 매출, 콤보 & 피버 게이지, [상점으로] 버튼
- 중단 야시장 배경 & 손님 대기석 (y=65~345):
  * 국가별 야시장 배경 및 인테리어 소품 렌더링
  * 좌측 포차 마스터 아바타 & [SPACE] 액티브 스킬 패널 (쿨타임/오라 연출)
  * 3~4인 손님 대기 슬롯, 주문 말풍선 및 인내심 게이지
- 하단 1인칭 포차 조리대 (y=345~720):
  * 좌측: 몰드 스테이션(MoldStation) + 음료 디스펜서(DispenserStation)
  * 중앙: 조립 & 토핑 트레이(AssemblyTray + 휴지통)
  * 우측: 직화 그릴(GrillStation) + 대량 조리 팬(BatchPotStation)
- 원클릭 자동 서빙(try_auto_serve) & 포물선 비행 디쉬 애니메이션(FlyingDishEffect)
- 주인공 4인 고유 액티브 스킬 및 키보드 단축키([SPACE], [1~4], [Q/W/E/R/A/S]) 지원
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple
import pygame

import config
from core import art_renderer
from core.effects import FloatingText, FlyingDishEffect, ParticleSystem, sound_fx
from core.game_manager import GameManager
from core.scene_manager import BaseScene, SceneManager
from data.chapters import CHAPTERS
from data.recipes import RECIPES, TOPPINGS
from data.story import get_story_cutscene
from entities.customer import Customer
from entities.dish import Dish
from stations.assembly_tray import AssemblyTray
from stations.base_station import (
    STATE_BURNT,
    STATE_COOKING,
    STATE_IDLE,
    STATE_READY,
    BaseStation,
)
from stations.batch_pot_station import BatchPotStation
from stations.dispenser_station import DispenserStation
from stations.grill_station import GrillStation
from stations.mold_station import MoldStation
from stations.specialist_station import SpecialistStation


class PlayScene(BaseScene):
    """1인칭 포차 카운터 실시간 조리 & 서빙 영업 씬."""

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        scene_mgr: Optional[SceneManager] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(game_mgr, scene_mgr, **kwargs)
        self.time_tick: float = 0.0
        self.particles: ParticleSystem = ParticleSystem()
        self._hover_pos: Tuple[int, int] = (0, 0)

        # 영업 타이머 및 피버/스킬 상태
        self.day_duration: float = float(kwargs.get("day_duration", config.DAY_DURATION))
        self.time_left: float = self.day_duration
        self.fever_timer: float = 0.0
        self.patience_freeze_timer: float = 0.0
        self.paused: bool = False
        self._day_finished: bool = False

        # 상단 HUD 버튼 및 좌측 마스터 스킬 버튼 Rect
        self.options_btn_rect: pygame.Rect = pygame.Rect(1058, 12, 86, 40)
        self.pause_btn_rect: pygame.Rect = pygame.Rect(1150, 12, 116, 40)
        self.chef_panel_rect: pygame.Rect = pygame.Rect(12, 74, 174, 262)
        self.skill_btn_rect: pygame.Rect = pygame.Rect(20, 274, 158, 54)

        # 하단 5개 조리 구역 Rect (1280x720 중 y=355~707)
        self.mold_rect: pygame.Rect = pygame.Rect(14, 355, 224, 352)
        self.dispenser_rect: pygame.Rect = pygame.Rect(248, 355, 214, 352)
        self.tray_rect: pygame.Rect = pygame.Rect(472, 355, 336, 352)
        self.grill_rect: pygame.Rect = pygame.Rect(818, 355, 214, 352)
        self.batch_pot_rect: pygame.Rect = pygame.Rect(1042, 355, 224, 352)

        # 스테이션 인스턴스 생성
        active_st = self.game_mgr.get_active_stations()
        self.mold_station: MoldStation = MoldStation(
            station_id=str(active_st["mold"]),
            rect=self.mold_rect,
            game_mgr=self.game_mgr,
        )
        self.dispenser_station: DispenserStation = DispenserStation(
            station_id=str(active_st["dispenser"]),
            rect=self.dispenser_rect,
            game_mgr=self.game_mgr,
        )
        self.assembly_tray: AssemblyTray = AssemblyTray(
            rect=self.tray_rect,
            game_mgr=self.game_mgr,
        )
        self.grill_station: GrillStation = GrillStation(
            station_id=str(active_st["grill"]),
            rect=self.grill_rect,
            game_mgr=self.game_mgr,
        )
        self.batch_pot_station: BatchPotStation = BatchPotStation(
            station_id=str(active_st["batch_pot"]),
            rect=self.batch_pot_rect,
            game_mgr=self.game_mgr,
        )

        # 호환용 별칭
        self.batch_station: BatchPotStation = self.batch_pot_station
        self.tray: AssemblyTray = self.assembly_tray
        self.stations: Dict[str, BaseStation] = {
            "mold": self.mold_station,
            "dispenser": self.dispenser_station,
            "grill": self.grill_station,
            "batch_pot": self.batch_pot_station,
        }
        self.station_list: List[BaseStation] = [
            self.mold_station,
            self.dispenser_station,
            self.grill_station,
            self.batch_pot_station,
        ]
        self.specialist_station: SpecialistStation = SpecialistStation(
            specialist_id=getattr(self.game_mgr, "selected_specialist", "bungeo"),
            game_mgr=self.game_mgr,
        )

        # 손님 대기 슬롯 초기화
        self.max_customer_slots: int = self.game_mgr.get_max_customer_slots()
        self.customers: List[Optional[Customer]] = [None] * self.max_customer_slots
        self.spawn_timer: float = 0.8
        self._ambient_particle_timer: float = 0.0

        # 스토리 컷신 큐 및 오버레이 상태
        self.cutscene_queue: List[Any] = []
        self.active_cutscene: Optional[Any] = None
        self.cutscene_line_idx: int = 0
        self._cutscene_next_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._cutscene_skip_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.story_replay_btn_rect: pygame.Rect = pygame.Rect(194, 70, 122, 26)

        self._setup_new_day(show_cutscene=bool(kwargs.get("show_cutscene", False)))
        self._initialized_day_in_init: bool = True

    # 플로팅 텍스트 및 비행 디쉬 리스트 직접 조회 호환 프로퍼티
    @property
    def floating_texts(self) -> List[FloatingText]:
        return self.particles.floating_texts

    @property
    def flying_dishes(self) -> List[FlyingDishEffect]:
        return self.particles.flying_dishes

    def _queue_start_cutscenes(self) -> None:
        """스토리 모드(WORLD_TOUR) 영업 시작 전 해당 일차의 스토리 컷신을 큐에 등록한다."""
        self.cutscene_queue.clear()
        self.active_cutscene = None
        self.cutscene_line_idx = 0
        if self.game_mgr.mode != "WORLD_TOUR":
            return
        ch = self.game_mgr.current_chapter
        day = self.game_mgr.day
        if ch == "KR" and day == 1:
            prol = get_story_cutscene("prologue")
            if prol:
                self.cutscene_queue.append(prol)
        start_cs = get_story_cutscene(ch, day, timing="start")
        if start_cs:
            self.cutscene_queue.append(start_cs)
        if self.cutscene_queue:
            self.active_cutscene = self.cutscene_queue.pop(0)
            self.cutscene_line_idx = 0

    def _get_play_bgm_track(self) -> str:
        """현재 영업 챕터 및 피버/보스전 상태에 맞는 BGM 트랙 키를 반환한다."""
        if self.fever_timer > 0.0 or bool(getattr(self.game_mgr, "ai_opponent_id", "")):
            return "fever"
        ch = str(self.game_mgr.current_chapter or "KR").upper()
        if ch in ("JP",):
            return "play_jp"
        if ch in ("MX", "BR", "US"):
            return "play_mx"
        if ch in ("TW", "CN", "IN"):
            return "play_tw"
        return "play_kr"

    def _advance_cutscene(self, skip_all: bool = False) -> None:
        """현재 대사를 한 줄 넘기거나 컷신을 종료한다."""
        if skip_all or self.active_cutscene is None:
            sound_fx.play_click()
            self.cutscene_queue.clear()
            self.active_cutscene = None
            self.cutscene_line_idx = 0
            return
        sound_fx.play_dialog()
        lines = self.active_cutscene.get("lines", [])
        if self.cutscene_line_idx + 1 < len(lines):
            self.cutscene_line_idx += 1
        elif self.cutscene_queue:
            self.active_cutscene = self.cutscene_queue.pop(0)
            self.cutscene_line_idx = 0
        else:
            self.active_cutscene = None
            self.cutscene_line_idx = 0

    def _setup_new_day(self, show_cutscene: bool = False) -> None:
        """새로운 영업일 시작 시 런타임 카운터, 조리대, 초기 손님을 세팅한다."""
        self.game_mgr.start_day()
        self.time_left = self.day_duration
        self.fever_timer = 0.0
        self.patience_freeze_timer = 0.0
        self._day_finished = False
        self._last_timer_tick_sec: int = -1
        self.ai_rival_gold: int = 0
        self.ai_rival_timer: float = 3.2
        self.particles.clear()

        active_st = self.game_mgr.get_active_stations()
        self.mold_station.set_station_id(str(active_st["mold"]))
        self.mold_station.reset_all()
        self.dispenser_station.set_station_id(str(active_st["dispenser"]))
        self.dispenser_station.reset_all()
        if self.game_mgr.is_slot_unlocked_in_story("dispenser"):
            self.dispenser_station._ensure_auto_refill()
        self.grill_station.set_station_id(str(active_st["grill"]))
        self.grill_station.reset_all()
        self.batch_pot_station.set_station_id(str(active_st["batch_pot"]))
        self.batch_pot_station.reset_all()
        self.specialist_station.set_specialist_id(getattr(self.game_mgr, "selected_specialist", "bungeo"))
        self.specialist_station.reset_all()
        self.assembly_tray.sync_slots_with_manager()
        self.assembly_tray.clear_all()

        self.max_customer_slots = self.game_mgr.get_max_customer_slots()
        self.customers = [None] * self.max_customer_slots
        # 첫 손님 1명 즉시 입장
        self._spawn_customer_in_empty_slot()
        self.spawn_timer = 2.2

        if show_cutscene:
            self._queue_start_cutscenes()
        else:
            self.cutscene_queue.clear()
            self.active_cutscene = None
            self.cutscene_line_idx = 0
        sound_fx.play_bgm(self._get_play_bgm_track())

    def on_enter(self, **kwargs: Any) -> None:
        if "day_duration" in kwargs:
            self.day_duration = float(kwargs["day_duration"])
        if getattr(self, "_initialized_day_in_init", False):
            self._initialized_day_in_init = False
            if "day_duration" in kwargs:
                self.time_left = self.day_duration
            if kwargs.get("show_cutscene", False) and self.active_cutscene is None:
                self._queue_start_cutscenes()
            sound_fx.play_bgm(self._get_play_bgm_track())
            return
        self._setup_new_day(show_cutscene=bool(kwargs.get("show_cutscene", False)))
        sound_fx.play_bgm(self._get_play_bgm_track())

    def _compute_customer_slot_rect(self, slot_idx: int) -> pygame.Rect:
        """좌측 마스터 패널(x=12~186) 우측 공간(x=196~1268)에 손님 슬롯을 균등 배치한다."""
        left_x = 196
        usable_w = config.SCREEN_WIDTH - left_x - 12
        slot_w = usable_w // max(3, self.max_customer_slots)
        card_w = min(256, slot_w - 6)
        x = left_x + slot_idx * slot_w + (slot_w - card_w) // 2
        y = config.CUSTOMER_AREA_TOP + 12
        return pygame.Rect(x, y, card_w, config.CUSTOMER_AREA_HEIGHT - 18)

    def _spawn_customer_in_empty_slot(self) -> Optional[Customer]:
        empty_indices = [i for i, c in enumerate(self.customers) if c is None]
        if not empty_indices:
            return None
        slot_idx = empty_indices[0]
        slot_rect = self._compute_customer_slot_rect(slot_idx)
        cust = Customer.create_random(slot_index=slot_idx, game_mgr=self.game_mgr, rect=slot_rect)
        self.customers[slot_idx] = cust
        if cust.is_vip:
            sound_fx.play_vip_arrive()
        else:
            sound_fx.play_customer_arrive()
        return cust

    # ==================================================================
    # ⚡ 핵심: 원클릭 자동 서빙 (try_auto_serve)
    # ==================================================================
    def try_auto_serve(
        self,
        recipe_id: str,
        start_pos: Optional[Tuple[int, int]] = None,
    ) -> bool:
        """
        완성된 음식(recipe_id)을 현재 대기 중인 손님 중 해당 메뉴를 원하는 손님에게 자동 서빙한다.
        여러 손님이 동일한 메뉴를 원할 경우 남은 인내심 비율(patience_ratio)이 가장 낮은
        (가장 급한) 손님을 최우선으로 매칭한다.
        """
        if not recipe_id:
            return False

        candidates: List[Customer] = [
            c for c in self.customers if c is not None and c.wants_recipe(recipe_id)
        ]
        if not candidates:
            return False

        # 인내심 비율이 가장 낮은 손님 우선 정렬
        candidates.sort(key=lambda c: (c.patience_ratio, c.patience, c.slot_index))
        target_cust = candidates[0]

        # 손님 주문 수령 전에 콤보를 먼저 증가시켜 현재 콤보가 즉시 손님 팁에 반영되도록 처리
        prev_combo = self.game_mgr.combo
        prev_max_combo = self.game_mgr.max_combo
        prev_combo_timer = self.game_mgr.combo_timer
        if hasattr(self.game_mgr, "add_combo"):
            self.game_mgr.add_combo(1)
        else:
            self.game_mgr.combo = max(0, self.game_mgr.combo) + 1
            self.game_mgr.max_combo = max(self.game_mgr.max_combo, self.game_mgr.combo)
            self.game_mgr.combo_timer = config.COMBO_WINDOW

        # 손님 주문 수령 처리
        serve_info = target_cust.receive_dish(recipe_id, game_mgr=self.game_mgr)
        if not serve_info.get("served", False):
            self.game_mgr.combo = prev_combo
            self.game_mgr.max_combo = prev_max_combo
            self.game_mgr.combo_timer = prev_combo_timer
            return False

        self.game_mgr.served_customers += 1

        base_price = int(serve_info.get("price", self.game_mgr.get_recipe_price(recipe_id)))
        cust_tip = int(serve_info.get("tip", 0))
        mgr_tip = self.game_mgr.calculate_combo_tip(
            base_price,
            combo_count=self.game_mgr.combo,
            is_vip=target_cust.is_vip,
        )
        tip = max(cust_tip, mgr_tip)

        # 피버 타임 중에는 추가 25% 보너스 팁!
        if self.fever_timer > 0.0:
            tip += int(round((base_price * 0.25) / 10.0) * 10)

        total_earned = base_price + tip
        self.game_mgr.daily_gold += total_earned
        self.game_mgr.daily_gross_gold = int(getattr(self.game_mgr, "daily_gross_gold", 0)) + total_earned
        self.game_mgr.add_gold(total_earned)

        # 출발/도착 좌표 계산 및 포물선 비행 애니메이션(FlyingDishEffect) 생성
        origin = start_pos if start_pos is not None else (config.SCREEN_WIDTH // 2, 520)
        dest = (target_cust.rect.centerx, target_cust.rect.centery - 10)

        def _on_dish_arrive() -> None:
            self.particles.emit_stars(dest[0], dest[1], count=10)

        self.particles.spawn_flying_dish(
            recipe_id=recipe_id,
            start_pos=(float(origin[0]), float(origin[1])),
            target_pos=(float(dest[0]), float(dest[1])),
            duration=0.34,
            on_arrive=_on_dish_arrive,
        )

        # 사운드 및 플로팅 텍스트 연출
        sound_fx.play_serve()
        sound_fx.play_cash()
        if self.game_mgr.combo >= 2:
            sound_fx.play_combo(self.game_mgr.combo)

        rec_name = RECIPES.get(recipe_id, {}).get("name", recipe_id)
        tip_str = f" (팁 +{tip:,})" if tip > 0 else ""
        self.particles.spawn_floating_text(
            f"+{total_earned:,}원!{tip_str}",
            dest[0],
            target_cust.rect.top + 18,
            color=config.GOLD,
            size=21,
        )

        if self.game_mgr.combo >= 2:
            self.particles.spawn_floating_text(
                f"🔥 COMBO x{self.game_mgr.combo}!",
                dest[0],
                target_cust.rect.top - 8,
                color=config.NEON_ORANGE,
                size=19,
            )

        self.particles.emit_stars(dest[0], dest[1], count=8)

        # 맛집 유튜버 VIP 주문 완료 시 12초간 FEVER TIME 발동!
        if serve_info.get("triggers_fever", False):
            self.fever_timer = 12.0
            sound_fx.play_skill()
            self.particles.emit_skill_aura(dest[0], dest[1], color=config.NEON_PINK, count=20)
            self.particles.spawn_floating_text(
                "🎉 유튜버 극찬! 12초간 FEVER TIME 발동!!",
                config.SCREEN_WIDTH // 2,
                135,
                color=config.NEON_PINK,
                size=26,
                duration=2.0,
            )

        return True

    # ==================================================================
    # 🧙‍♂️ 주인공 32인 액티브 스킬 ([SPACE] 또는 스킬 버튼 클릭)
    # ==================================================================
    def _get_slot_unlock_hint(self, slot_key: str) -> str:
        """잠긴 조리 기구/기능이 어느 일차에 해금되는지 안내 문구를 반환한다."""
        ch = self.game_mgr.current_chapter
        if ch == "KR":
            hints = {
                "dispenser": "🔒 Day 2 해금: 어묵국물·식혜 디스펜서",
                "grill": "🔒 Day 3 해금: 직화 닭꼬치 그릴",
                "tray": "🔒 Day 3 해금: 중앙 조립 트레이 & 토핑",
                "batch_pot": "🔒 Day 4 해금: 철판 떡볶이 대량 조리 팬",
                "skill": "🔒 Day 4 해금: 포차 마스터 액티브 스킬 [SPACE]",
            }
            return hints.get(slot_key, "🔒 스토리 진행 시 해금")
        hints_overseas = {
            "grill": "🔒 Day 2 해금: 현지 직화 그릴/튀김기",
            "batch_pot": "🔒 Day 3 해금: 현지 대량 조리 팬 (3인분)",
        }
        return hints_overseas.get(slot_key, "🔒 스토리 진행 시 해금")

    def activate_skill(self) -> bool:
        """현재 선택된 주인공(포차 마스터)의 액티브 스킬을 발동한다 (32인 skill_desc 완벽 동기화)."""
        if not self.game_mgr.is_slot_unlocked_in_story("skill"):
            sound_fx.play_burn()
            self.particles.spawn_floating_text(
                self._get_slot_unlock_hint("skill"),
                self.skill_btn_rect.centerx + 60,
                self.skill_btn_rect.top - 12,
                color=config.TEXT_WARNING,
                size=16,
            )
            return False

        if self.game_mgr.skill_cooldown > 0.0:
            sound_fx.play_burn()
            rem = int(math.ceil(self.game_mgr.skill_cooldown))
            self.particles.spawn_floating_text(
                f"스킬 쿨타임 중 ({rem}초)",
                self.skill_btn_rect.centerx,
                self.skill_btn_rect.top - 12,
                color=config.TEXT_WARNING,
                size=18,
            )
            return False

        char_data = self.game_mgr.get_selected_character_data()
        char_id = self.game_mgr.selected_character
        cooldown = float(char_data.get("cooldown", 35.0))
        duration = float(char_data.get("duration", 8.0))

        self.game_mgr.skill_cooldown = cooldown
        self.game_mgr.skill_active_timer = max(2.5, duration)

        sound_fx.play_skill()
        self.particles.emit_skill_aura(
            self.chef_panel_rect.centerx,
            self.chef_panel_rect.centery,
            color=char_data.get("accent_color", config.GOLD),
            count=20,
        )

        skill_effect = str(char_data.get("skill_effect", "") or "")
        skill_name = str(char_data.get("skill_name", "마스터 스킬") or "마스터 스킬")
        skill_desc = str(char_data.get("skill_desc", "") or "")

        # 1) 조리 기구 즉시 완성 (instant_finish_all)
        should_instant_finish = (
            char_id in ("chef_jp", "chef_tw_kaohsiung", "chef_br_rio", "chef_cn_canton", "chef_cn_shanghai")
            or skill_effect in ("jp_instant", "instant_and_speed", "instant_and_tip", "instant_and_combo", "refill_and_heal")
        ) and char_id != "chef_jp_hokkaido"
        if should_instant_finish:
            if self.game_mgr.mode == "SPECIALIST":
                self.specialist_station.instant_finish_all()
                self.particles.emit_flame(
                    self.specialist_station.appliance_rect.centerx,
                    self.specialist_station.appliance_rect.centery,
                    count=12,
                )
                self.particles.emit_stars(
                    self.specialist_station.appliance_rect.centerx,
                    self.specialist_station.appliance_rect.centery,
                    count=10,
                )
            else:
                for st in self.station_list:
                    st.instant_finish_all()
                    self.particles.emit_flame(st.rect.centerx, st.rect.centery, count=10)
                    self.particles.emit_stars(st.rect.centerx, st.rect.centery, count=8)
            sound_fx.play_ready()

        # 2) 대기 손님 음료 즉시 자동 서빙
        should_serve_drinks = (
            char_id in (
                "chef_tw",
                "chef_br_saopaulo",
                "chef_ru_caucasus",
                "chef_us_cali",
                "chef_in_chennai",
                "chef_in_punjab",
                "chef_cn_canton",
            )
            or skill_effect == "tw_express"
        )
        if should_serve_drinks:
            for cust in list(self.customers):
                if cust is None or cust.state != "WAITING":
                    continue
                for order_rid in list(cust.orders):
                    rec = RECIPES.get(order_rid)
                    if rec and rec.get("slot_type") == "dispenser":
                        self.try_auto_serve(order_rid, self.dispenser_station.rect.center)
            self.dispenser_station.serve_all_waiting_drinks(self.try_auto_serve)

        # 3) 모든 대기 손님 인내심 회복 (40% / 50% / 60% / 100%)
        heal_ratio = 0.0
        if char_id in ("chef_jp_hokkaido", "chef_us_nola", "chef_cn_dongbei") or skill_effect == "heal_and_freeze":
            heal_ratio = 1.00
        elif char_id in ("chef_mx_oaxaca", "chef_in_punjab"):
            heal_ratio = 0.60
        elif (
            char_id in ("chef_jp_fukuoka", "chef_br_bahia", "chef_in_mumbai", "chef_cn_shanghai")
            or skill_effect in ("refill_and_heal", "heal_and_tip")
        ):
            heal_ratio = 0.50
        elif char_id in ("chef_kr", "chef_ru_caucasus") or (
            skill_effect == "kr_rush" and char_id != "chef_br_saopaulo"
        ):
            heal_ratio = 0.40

        if heal_ratio > 0.0:
            for cust in self.customers:
                if cust is not None and cust.state == "WAITING":
                    cust.heal_patience(heal_ratio)
                    self.particles.emit_hearts(cust.rect.centerx, cust.rect.centery, count=6)

        # 4) 손님 인내심 감소 정지 (patience_freeze_timer)
        if (
            char_id in ("chef_mx", "chef_jp_tokyo", "chef_ru_moscow", "chef_us_nola", "chef_in_chennai")
            or skill_effect in ("mx_fiesta", "heal_and_freeze", "speed_and_freeze")
        ):
            self.patience_freeze_timer = max(8.0, duration)
            for cust in self.customers:
                if cust is not None and cust.state == "WAITING":
                    self.particles.emit_stars(cust.rect.centerx, cust.rect.centery, count=6)

        # 5) 즉시 FEVER TIME 발동
        if (
            char_id in ("chef_br_rio", "chef_us_cali", "chef_in_mumbai", "chef_cn_beijing")
            or skill_effect == "force_fever"
        ):
            self.fever_timer = max(9.0, duration)

        # 6) 콤보 스택 즉시 추가 (+3 / +4 / +5)
        combo_add = 0
        if char_id == "chef_us_philly":
            combo_add = 5
        elif (
            char_id in ("chef_mx_jalisco", "chef_ru_caucasus", "chef_in_kolkata", "chef_cn_xinjiang")
            or skill_effect == "instant_and_combo"
        ):
            combo_add = 4
        elif char_id in ("chef_tw", "chef_cn_sichuan"):
            combo_add = 3

        if combo_add > 0:
            if hasattr(self.game_mgr, "add_combo"):
                self.game_mgr.add_combo(combo_add)
            else:
                self.game_mgr.combo = max(0, self.game_mgr.combo) + combo_add
                self.game_mgr.max_combo = max(self.game_mgr.max_combo, self.game_mgr.combo)
                self.game_mgr.combo_timer = config.COMBO_WINDOW
            sound_fx.play_combo(self.game_mgr.combo)

        # 7) 플로팅 텍스트 알림
        banner_col = char_data.get("accent_color", config.GOLD)
        summary_txt = skill_desc if skill_desc else "마스터 고유 버프 발동!"
        self.particles.spawn_floating_text(
            f"⚡ {skill_name}! ({summary_txt})",
            config.SCREEN_WIDTH // 2,
            115,
            color=banner_col,
            size=22,
            duration=1.8,
        )
        return True

    # ==================================================================
    # 이벤트 및 단축키 처리
    # ==================================================================
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_pos = event.pos
            if self.assembly_tray.hold_slot_idx is not None:
                idx = self.assembly_tray.hold_slot_idx
                if idx < len(self.assembly_tray.slot_rects) and not self.assembly_tray.slot_rects[idx].inflate(12, 12).collidepoint(event.pos):
                    self.assembly_tray.end_hold()

        elif event.type == pygame.MOUSEBUTTONUP:
            self.assembly_tray.end_hold()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if event.button == 1 and self.assembly_tray.rect.inflate(8, 8).collidepoint(mx, my):
                self.assembly_tray.start_hold((mx, my))

            # 스토리 컷신 표시 중일 때 클릭 처리
            if self.active_cutscene is not None:
                if event.button == 1:
                    if self._cutscene_skip_rect.collidepoint(mx, my):
                        self._advance_cutscene(skip_all=True)
                    else:
                        self._advance_cutscene(skip_all=False)
                return

            # 상단 [옵션] 버튼
            if event.button == 1 and self.options_btn_rect.collidepoint(mx, my):
                if self.scene_mgr:
                    self.scene_mgr.open_options()
                return

            # 상단 [상점으로/일시정지] 버튼
            if event.button == 1 and self.pause_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                self.game_mgr.save_game()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", show_loading=True)
                return

            # 스토리 모드 [🎬 스토리] 다시보기 버튼
            if (
                event.button == 1
                and self.game_mgr.mode == "WORLD_TOUR"
                and self.story_replay_btn_rect.collidepoint(mx, my)
            ):
                sound_fx.play_click()
                self._queue_start_cutscenes()
                return

            # 좌측 주인공 스킬 버튼 클릭
            if event.button == 1 and (
                self.skill_btn_rect.collidepoint(mx, my) or self.chef_panel_rect.collidepoint(mx, my)
            ):
                self.activate_skill()
                return

            # 조립 트레이 클릭 (좌클릭: 서빙/토핑/휴지통, 우클릭: 접시 폐기)
            if self.assembly_tray.rect.collidepoint(mx, my):
                res = self.assembly_tray.handle_click(
                    (mx, my),
                    auto_serve_cb=self.try_auto_serve,
                    button=event.button,
                )
                self._handle_station_feedback(res, (mx, my))
                return

            if event.button != 1:
                return

            # 단일 메뉴 장인 모드(SPECIALIST)일 때 좌측 투입대 & 우측 6구 화로 클릭
            if self.game_mgr.mode == "SPECIALIST":
                if self.specialist_station.collide_point((mx, my)):
                    res = self.specialist_station.handle_click(
                        (mx, my),
                        assembly_tray=self.assembly_tray,
                        auto_serve_cb=self.try_auto_serve,
                        customers=self.customers,
                    )
                    self._handle_station_feedback(res, (mx, my))
                    return
                return

            # 4대 조리 스테이션 클릭
            for st in self.station_list:
                if st.rect.collidepoint(mx, my):
                    if not self.game_mgr.is_slot_unlocked_in_story(st.slot_type):
                        sound_fx.play_burn()
                        self.particles.spawn_floating_text(
                            self._get_slot_unlock_hint(st.slot_type),
                            st.rect.centerx,
                            st.rect.top + 30,
                            color=config.TEXT_WARNING,
                            size=16,
                        )
                        return
                    res = st.handle_click(
                        (mx, my),
                        assembly_tray=self.assembly_tray,
                        auto_serve_cb=self.try_auto_serve,
                    )
                    self._handle_station_feedback(res, (mx, my))
                    return

        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event.key)

    def _handle_keydown(self, key: int) -> None:
        # 스토리 컷신 표시 중일 때 단축키 처리
        if self.active_cutscene is not None:
            if key == pygame.K_ESCAPE:
                self._advance_cutscene(skip_all=True)
            elif key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_RIGHT):
                self._advance_cutscene(skip_all=False)
            return

        # [SPACE]: 주인공 액티브 스킬 발동
        if key == pygame.K_SPACE:
            self.activate_skill()
            return

        # [ESC]: 준비 화면(상점)으로 이동
        if key == pygame.K_ESCAPE:
            sound_fx.play_click()
            if self.scene_mgr:
                self.scene_mgr.change_scene("prep", show_loading=True)
            return

        # [1]~[5]: 조립 트레이 접시 1~5번 빠른 자동 서빙
        tray_keys = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]
        if key in tray_keys:
            idx = tray_keys.index(key)
            if idx < len(self.assembly_tray.slot_rects):
                s_rect = self.assembly_tray.slot_rects[idx]
                res = self.assembly_tray.handle_click(
                    s_rect.center,
                    auto_serve_cb=self.try_auto_serve,
                    button=1,
                )
                self._handle_station_feedback(res, s_rect.center)
            return

        # 단일 메뉴 장인 모드일 때 [Q/W/E/R/A/S] 단축키로 6구 화로 수거 또는 1~6번 속재료 투입
        if self.game_mgr.mode == "SPECIALIST":
            spec_keys = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_a, pygame.K_s]
            if key in spec_keys:
                for slot in self.specialist_station.slots:
                    if slot.state in (STATE_READY, STATE_BURNT):
                        res = self.specialist_station.handle_click(
                            slot.rect.center,
                            assembly_tray=self.assembly_tray,
                            auto_serve_cb=self.try_auto_serve,
                            customers=self.customers,
                        )
                        self._handle_station_feedback(res, slot.rect.center)
                        return
                k_idx = spec_keys.index(key)
                if k_idx < len(self.specialist_station.recipe_buttons):
                    btn_rect, _ = self.specialist_station.recipe_buttons[k_idx]
                    res = self.specialist_station.handle_click(
                        btn_rect.center,
                        assembly_tray=self.assembly_tray,
                        auto_serve_cb=self.try_auto_serve,
                        customers=self.customers,
                    )
                    self._handle_station_feedback(res, btn_rect.center)
                return

        # [Q], [W]: 몰드 기구 레시피 1 / 2 투입 또는 완성품 수거
        if key in (pygame.K_q, pygame.K_w):
            if not self.game_mgr.is_slot_unlocked_in_story("mold"):
                return
            rec_idx = 0 if key == pygame.K_q else 1
            # 우선 READY 또는 BURNT 슬롯이 있으면 수거/폐기
            for slot in self.mold_station.slots:
                if slot.state in (STATE_READY, STATE_BURNT):
                    res = self.mold_station.handle_click(
                        slot.rect.center,
                        assembly_tray=self.assembly_tray,
                        auto_serve_cb=self.try_auto_serve,
                    )
                    self._handle_station_feedback(res, slot.rect.center)
                    return
            # 아니면 해당 레시피 버튼 클릭
            if rec_idx < len(self.mold_station.recipe_buttons):
                btn_rect, _ = self.mold_station.recipe_buttons[rec_idx]
                res = self.mold_station.handle_click(
                    btn_rect.center,
                    assembly_tray=self.assembly_tray,
                    auto_serve_cb=self.try_auto_serve,
                )
                self._handle_station_feedback(res, btn_rect.center)
            return

        # [E]: 직화 그릴 재료 투입 또는 완성품 수거
        if key == pygame.K_e:
            if not self.game_mgr.is_slot_unlocked_in_story("grill"):
                return
            for slot in self.grill_station.slots:
                if slot.state in (STATE_READY, STATE_BURNT):
                    res = self.grill_station.handle_click(
                        slot.rect.center,
                        assembly_tray=self.assembly_tray,
                        auto_serve_cb=self.try_auto_serve,
                    )
                    self._handle_station_feedback(res, slot.rect.center)
                    return
            res = self.grill_station.handle_click(
                self.grill_station.cook_button_rect.center,
                assembly_tray=self.assembly_tray,
                auto_serve_cb=self.try_auto_serve,
            )
            self._handle_station_feedback(res, self.grill_station.cook_button_rect.center)
            return

        # [R]: 대량 조리 팬 조리 시작 또는 1인분 덜어내기
        if key == pygame.K_r:
            if not self.game_mgr.is_slot_unlocked_in_story("batch_pot"):
                return
            res = self.batch_pot_station.handle_click(
                self.batch_pot_station.action_button_rect.center,
                assembly_tray=self.assembly_tray,
                auto_serve_cb=self.try_auto_serve,
            )
            self._handle_station_feedback(res, self.batch_pot_station.action_button_rect.center)
            return

        # [A], [S]: 음료 디스펜서 노즐 1 / 2 즉시 서빙 (업그레이드 시 동일 음료 READY 슬롯 우선)
        if key in (pygame.K_a, pygame.K_s):
            if not self.game_mgr.is_slot_unlocked_in_story("dispenser"):
                return
            nozzle_idx = 0 if key == pygame.K_a else 1
            drink_cnt = max(1, len(self.dispenser_station.drink_recipes))
            target_slot = None
            for idx, sl in enumerate(self.dispenser_station.slots):
                if (idx % drink_cnt) == nozzle_idx and sl.state == STATE_READY:
                    target_slot = sl
                    break
            if target_slot is None and nozzle_idx < len(self.dispenser_station.slots):
                target_slot = self.dispenser_station.slots[nozzle_idx]
            if target_slot is not None:
                res = self.dispenser_station.handle_click(
                    target_slot.rect.center,
                    assembly_tray=self.assembly_tray,
                    auto_serve_cb=self.try_auto_serve,
                )
                self._handle_station_feedback(res, target_slot.rect.center)
            return

    def _handle_station_feedback(
        self,
        res: Optional[Dict[str, Any]],
        pos: Tuple[int, int],
    ) -> None:
        if not res:
            return
        action = str(res.get("action", ""))
        slot_type = str(res.get("slot_type", ""))
        px, py = pos

        if action == "start_cook":
            sound_fx.play_sizzle(slot_type)
            self.particles.emit_smoke(px, py - 10, count=4)
            if (
                self.game_mgr.mode == "SPECIALIST"
                and self.scene_mgr is not None
                and getattr(self.scene_mgr, "is_portrait_mode", False)
                and getattr(self.scene_mgr, "portrait_play_idx", 0) == 0
                and getattr(self.specialist_station, "is_bungeoppang", False)
            ):
                self.scene_mgr.portrait_play_idx = 1
        elif action == "moved_to_tray":
            if slot_type == "batch_pot" or "remaining_servings" in res:
                sound_fx.play_pot_scoop()
            else:
                sound_fx.play_move_to_tray()
            self.particles.emit_stars(self.assembly_tray.rect.centerx, self.assembly_tray.rect.top + 80, count=5)
            moved_rid = str(res.get("recipe_id", ""))
            st_idx = self.assembly_tray.find_stack_slot(moved_rid, False)
            if st_idx is not None and st_idx < len(self.assembly_tray.dishes):
                st_dish = self.assembly_tray.dishes[st_idx]
                if st_dish is not None and st_dish.quantity >= 2:
                    self.particles.spawn_floating_text(
                        f"📦 {st_dish.name} 적재 x{st_dish.quantity}!",
                        self.assembly_tray.rect.centerx,
                        self.assembly_tray.rect.top + 28,
                        color=config.GOLD,
                        size=17,
                    )
            if self.scene_mgr is not None and getattr(self.scene_mgr, "is_portrait_mode", False):
                self.scene_mgr.portrait_play_idx = 2
        elif action in ("auto_served", "served"):
            if slot_type == "dispenser":
                sound_fx.play_drink_pour()
            elif slot_type == "batch_pot" or "remaining_servings" in res:
                sound_fx.play_pot_scoop()
        elif action == "add_topping":
            sound_fx.play_topping()
            tid = str(res.get("topping_id", ""))
            t_name = TOPPINGS.get(tid, {}).get("short_name", tid)
            self.particles.spawn_floating_text(f"+{t_name} 추가!", px, py - 15, color=config.NEON_GREEN, size=18)
        elif action in ("trash_burnt", "trash_dish"):
            sound_fx.play_trash()
            self.particles.emit_burn(px, py, count=7)
            rid = str(res.get("recipe_id", ""))
            cnt = max(1, int(res.get("discard_count", 1)))
            loss = 0
            if hasattr(self.game_mgr, "record_discard_loss"):
                loss = int(self.game_mgr.record_discard_loss(rid, count=cnt, reason=action, deduct_immediately=True))
            if loss > 0:
                self.particles.spawn_floating_text(
                    f"🗑️ 폐기 원가 손실 -{loss:,}원",
                    px,
                    py - 15,
                    color=config.RED,
                    size=18,
                )
            else:
                self.particles.spawn_floating_text("🗑️ 음식 폐기", px, py - 15, color=config.TEXT_WARNING, size=18)
        elif action == "toggle_trash_mode":
            sound_fx.play_click()
            msg = str(res.get("message", "버리기 모드 전환"))
            self.particles.spawn_floating_text(msg, px, py - 16, color=config.NEON_ORANGE, size=16)
        elif action in ("tray_full", "no_customer", "invalid_topping", "no_empty_slot"):
            sound_fx.play_burn()
            msg = str(res.get("message", "주문한 손님이 없습니다!"))
            self.particles.spawn_floating_text(msg, px, py - 15, color=config.TEXT_WARNING, size=16)
        elif action == "select_target_slot":
            sound_fx.play_click()
            msg = str(res.get("message", "넣을 속재료 버튼을 터치하세요!"))
            self.particles.spawn_floating_text(msg, px, py - 16, color=config.NEON_CYAN, size=16)
            if (
                self.game_mgr.mode == "SPECIALIST"
                and self.scene_mgr is not None
                and getattr(self.scene_mgr, "is_portrait_mode", False)
            ):
                self.scene_mgr.portrait_play_idx = 0
        elif action == "select_recipe":
            sound_fx.play_click()
            msg = str(res.get("message", "🥣 속재료 선택 완료! 빈 틀을 터치해 부으세요!"))
            self.particles.spawn_floating_text(msg, px, py - 16, color=config.NEON_CYAN, size=16)
            if (
                self.game_mgr.mode == "SPECIALIST"
                and self.scene_mgr is not None
                and getattr(self.scene_mgr, "is_portrait_mode", False)
            ):
                self.scene_mgr.portrait_play_idx = 1
        elif action == "flip_mold":
            sound_fx.play_mold_flip()
            self.particles.emit_smoke(px, py - 8, count=5)
            self.particles.emit_stars(px, py - 6, count=4)
            self.particles.spawn_floating_text("🔄 철컥! 뒤집기!", px, py - 16, color=config.GOLD, size=18)
        elif action == "too_early_flip":
            sound_fx.play_click()
            msg = str(res.get("message", "🥣 아직 앞면이 익는 중입니다!"))
            self.particles.spawn_floating_text(msg, px, py - 16, color=config.NEON_YELLOW, size=15)
        elif action == "cooking_in_progress":
            sound_fx.play_click()
            msg = str(res.get("message", "조리 중입니다! 완성되면 터치하세요."))
            self.particles.spawn_floating_text(msg, px, py - 16, color=config.NEON_YELLOW, size=15)
        elif action == "select_slot":
            # 트레이에서 접시를 클릭했는데 매칭되는 손님이 없는 경우 안내
            sound_fx.play_click()
            self.particles.spawn_floating_text(
                "토핑을 추가하거나 주문 손님을 기다리세요!",
                px,
                py - 16,
                color=config.NEON_YELLOW,
                size=16,
            )

    # ==================================================================
    # 프레임 업데이트 (update)
    # ==================================================================
    def update(self, dt: float) -> None:
        if self.paused or self._day_finished:
            return

        dt = max(0.0, float(dt))
        self.time_tick += dt

        # 스토리 컷신 표시 중에는 영업 타이머와 손님 스폰을 일시 정지
        if self.active_cutscene is not None:
            return

        # 1. 영업 시간 타이머 감소 및 마감 10초 카운트다운 틱 사운드
        self.time_left = max(0.0, self.time_left - dt)
        if 0.0 < self.time_left <= 10.0:
            cur_sec = int(math.ceil(self.time_left))
            if cur_sec != getattr(self, "_last_timer_tick_sec", -1):
                self._last_timer_tick_sec = cur_sec
                sound_fx.play_timer_tick(urgent=(cur_sec <= 5))
        if self.time_left <= 0.0:
            self._finish_day()
            return

        # 2. 스킬 쿨타임, 스킬 지속시간, 피버 타임, 콤보 타이머 감소
        if self.game_mgr.skill_cooldown > 0.0:
            self.game_mgr.skill_cooldown = max(0.0, self.game_mgr.skill_cooldown - dt)
        if self.game_mgr.skill_active_timer > 0.0:
            self.game_mgr.skill_active_timer = max(0.0, self.game_mgr.skill_active_timer - dt)
        if self.fever_timer > 0.0:
            self.fever_timer = max(0.0, self.fever_timer - dt)
        if self.patience_freeze_timer > 0.0:
            self.patience_freeze_timer = max(0.0, self.patience_freeze_timer - dt)

        # 피버 타임 시작/종료 시 BGM 트랙 동기화
        target_bgm = self._get_play_bgm_track()
        if getattr(sound_fx, "_current_bgm_track", "") != target_bgm:
            sound_fx.play_bgm(target_bgm)

        if self.game_mgr.combo > 0:
            self.game_mgr.combo_timer -= dt
            if self.game_mgr.combo_timer <= 0.0:
                self.game_mgr.break_combo()

        # 3. 손님 스폰 타이머
        self.spawn_timer -= dt * (1.65 if self.fever_timer > 0.0 else 1.0)
        if self.spawn_timer <= 0.0:
            self._spawn_customer_in_empty_slot()
            ch_data = CHAPTERS.get(self.game_mgr.current_chapter, CHAPTERS["KR"])
            sp_min, sp_max = ch_data.get("customer_spawn_interval", config.CUSTOMER_SPAWN_INTERVAL)
            self.spawn_timer = random.uniform(float(sp_min), float(sp_max))

        # 만약 대기 손님이 한 명도 없으면 빠르게 다음 손님 등장
        if all(c is None for c in self.customers) and self.spawn_timer > 1.0:
            self.spawn_timer = 0.6

        # 4. 손님 인내심 및 상태 업데이트
        is_patience_frozen = (self.patience_freeze_timer > 0.0) or (
            self.game_mgr.skill_active_timer > 0.0 and self.game_mgr.selected_character == "chef_mx"
        )
        for idx, cust in enumerate(self.customers):
            if cust is None:
                continue
            ev = cust.update(dt, patience_freeze=is_patience_frozen)
            if (
                cust.state == "WAITING"
                and cust.patience_ratio < 0.25
                and not getattr(cust, "_warn_sound_played", False)
            ):
                cust._warn_sound_played = True
                sound_fx.play_customer_warn()
            if ev == "ANGRY_LEFT":
                self.game_mgr.missed_customers += 1
                self.game_mgr.break_combo()
                sound_fx.play_customer_angry()
                self.particles.spawn_floating_text(
                    "💢 손님 이탈! (콤보 초기화)",
                    cust.rect.centerx,
                    cust.rect.top + 24,
                    color=config.RED,
                    size=19,
                )
            if cust.ready_to_remove:
                self.customers[idx] = None

        # 5. 조리 스테이션 업데이트 및 상태 전이 사운드/파티클 감지
        sel_eff = str(self.game_mgr.get_selected_character_data().get("skill_effect", "") or "")
        kr_rush_active = (
            self.game_mgr.skill_active_timer > 0.0
            and (
                self.game_mgr.selected_character in ("chef_kr", "chef_cn_xinjiang")
                or (
                    sel_eff in ("kr_rush", "instant_and_speed", "speed_and_freeze")
                    and self.game_mgr.selected_character != "chef_in_chennai"
                )
            )
        )
        if self.game_mgr.mode == "SPECIALIST":
            prev_states = [s.state for s in self.specialist_station.slots]
            if kr_rush_active:
                for s in self.specialist_station.slots:
                    if s.state == STATE_COOKING:
                        s.elapsed += dt
            self.specialist_station.update(dt)
            for s_idx, slot in enumerate(self.specialist_station.slots):
                prev_st = prev_states[s_idx] if s_idx < len(prev_states) else slot.state
                if slot.is_flip_ready and not getattr(slot, "_flip_sound_played", False):
                    slot._flip_sound_played = True
                    sound_fx.play_flip_ready()
                if prev_st == STATE_COOKING and slot.state == STATE_READY:
                    sound_fx.play_ready()
                    self.particles.emit_stars(slot.rect.centerx, slot.rect.centery, count=6)
                elif (
                    slot.state == STATE_READY
                    and slot.can_burn
                    and slot.burn_progress >= 0.65
                    and not getattr(slot, "_burn_warn_played", False)
                ):
                    slot._burn_warn_played = True
                    sound_fx.play_burn_warning()
                elif prev_st == STATE_READY and slot.state == STATE_BURNT:
                    self.game_mgr.break_combo()
                    sound_fx.play_burn()
                    self.particles.emit_burn(slot.rect.centerx, slot.rect.centery, count=8)
                    self.particles.spawn_floating_text(
                        "🔥 음식이 탔습니다!",
                        slot.rect.centerx,
                        slot.rect.top,
                        color=config.RED,
                        size=17,
                    )
        else:
            for st in self.station_list:
                if not self.game_mgr.is_slot_unlocked_in_story(st.slot_type):
                    continue
                prev_states = [s.state for s in st.slots]
                # 김포차 액티브 스킬 지속 중에는 이미 진행 중인 조리 슬롯도 2배 속도로 가속
                if kr_rush_active and st.slot_type in ("mold", "grill", "batch_pot"):
                    for s in st.slots:
                        if s.state == STATE_COOKING:
                            s.elapsed += dt
                st.update(dt)
                for s_idx, slot in enumerate(st.slots):
                    prev_st = prev_states[s_idx] if s_idx < len(prev_states) else slot.state
                    if slot.is_flip_ready and not getattr(slot, "_flip_sound_played", False):
                        slot._flip_sound_played = True
                        sound_fx.play_flip_ready()
                    if prev_st == STATE_COOKING and slot.state == STATE_READY:
                        if st.slot_type == "dispenser":
                            sound_fx.play_drink_ready()
                        else:
                            sound_fx.play_ready()
                            self.particles.emit_stars(slot.rect.centerx, slot.rect.centery, count=5)
                    elif (
                        slot.state == STATE_READY
                        and slot.can_burn
                        and slot.burn_progress >= 0.65
                        and not getattr(slot, "_burn_warn_played", False)
                    ):
                        slot._burn_warn_played = True
                        sound_fx.play_burn_warning()
                    elif prev_st == STATE_READY and slot.state == STATE_BURNT:
                        self.game_mgr.break_combo()
                        sound_fx.play_burn()
                        self.particles.emit_burn(slot.rect.centerx, slot.rect.centery, count=8)
                        self.particles.spawn_floating_text(
                            "🔥 음식이 탔습니다!",
                            slot.rect.centerx,
                            slot.rect.top,
                            color=config.RED,
                            size=17,
                        )

        # 6. 조리 중인 슬롯의 주기적 연기/불꽃 파티클 및 화구 앰비언트 조리음 방출
        self._ambient_particle_timer += dt
        if self._ambient_particle_timer >= 0.35:
            self._ambient_particle_timer = 0.0
            if self.game_mgr.mode == "SPECIALIST":
                any_cooking = False
                for slot in self.specialist_station.slots:
                    if slot.state == STATE_COOKING:
                        any_cooking = True
                        if self.specialist_station.specialist_id == "skewer":
                            self.particles.emit_flame(slot.rect.centerx, slot.rect.centery, count=2)
                        else:
                            self.particles.emit_smoke(slot.rect.centerx, slot.rect.top + 10, count=1)
                if any_cooking:
                    sound_fx.play_ambient_cooking(self.specialist_station.slot_type)
            else:
                for st in (self.mold_station, self.grill_station, self.batch_pot_station):
                    if not self.game_mgr.is_slot_unlocked_in_story(st.slot_type):
                        continue
                    st_cooking = False
                    for slot in st.slots:
                        if slot.state == STATE_COOKING:
                            st_cooking = True
                            if st.slot_type == "grill":
                                self.particles.emit_flame(slot.rect.centerx, slot.rect.centery, count=2)
                            else:
                                self.particles.emit_smoke(slot.rect.centerx, slot.rect.top + 10, count=1)
                    if st_cooking:
                        sound_fx.play_ambient_cooking(st.slot_type)

        # 6-B. 32강 토너먼트 AI 보스전 활성화 시 AI 라이벌 실시간 매출 시뮬레이션
        ai_opp = getattr(self.game_mgr, "ai_opponent_id", "")
        if ai_opp:
            self.ai_rival_timer -= dt
            if self.ai_rival_timer <= 0.0:
                rnd_idx = int(getattr(self.game_mgr, "tournament_round_idx", 0))
                self.ai_rival_timer = max(2.2, 4.2 - rnd_idx * 0.35)
                target_g = max(3000, self.game_mgr.get_target_gold())
                step_gain = int((target_g / 24.0) * (0.85 + rnd_idx * 0.08))
                self.ai_rival_gold += max(200, (step_gain // 10) * 10)

        # 7. 조립 트레이(0.35초 롱프레스 자동 폐기 포함) & 파티클 업데이트
        self.assembly_tray.update(dt)
        hold_fb = self.assembly_tray.pop_hold_feedback()
        if hold_fb is not None:
            fb_pos = hold_fb.get("pos", self.assembly_tray.rect.center)
            self._handle_station_feedback(hold_fb, fb_pos)
        self.particles.update(dt)

    def _settle_end_of_day_leftovers(self) -> int:
        """
        영업 종료(마감) 시 조립 트레이 및 조리 기구에 남아 있는 미판매 완성/탄 음식의
        재료 원가 손실(100% 원가 차감)을 일괄 정산하고 차감된 총 손실액을 반환한다.
        """
        if not hasattr(self.game_mgr, "record_discard_loss"):
            return 0
        total_leftover_loss = 0

        # 1. 중앙 조립 트레이에 남아 있는 적재 재고 정산
        for dish in self.assembly_tray.dishes:
            if dish is not None and dish.recipe_id:
                qty = max(1, int(getattr(dish, "quantity", 1)))
                total_leftover_loss += int(
                    self.game_mgr.record_discard_loss(
                        dish.recipe_id,
                        count=qty,
                        reason="leftover_tray",
                        deduct_immediately=True,
                    )
                )

        # 2. 조리 기구 슬롯에 남아 있는 완성(READY) / 탄(BURNT) 음식 정산 (음료 디스펜서 제외)
        if self.game_mgr.mode == "SPECIALIST":
            for slot in self.specialist_station.slots:
                if slot.state in (STATE_READY, STATE_BURNT) and slot.recipe_id:
                    qty = max(1, int(getattr(slot, "servings", 1)))
                    total_leftover_loss += int(
                        self.game_mgr.record_discard_loss(
                            slot.recipe_id,
                            count=qty,
                            reason="leftover_station",
                            deduct_immediately=True,
                        )
                    )
        else:
            for st in (self.mold_station, self.grill_station, self.batch_pot_station):
                if not self.game_mgr.is_slot_unlocked_in_story(st.slot_type):
                    continue
                for slot in st.slots:
                    if slot.state in (STATE_READY, STATE_BURNT) and slot.recipe_id:
                        qty = max(1, int(getattr(slot, "servings", 1)))
                        total_leftover_loss += int(
                            self.game_mgr.record_discard_loss(
                                slot.recipe_id,
                                count=qty,
                                reason="leftover_station",
                                deduct_immediately=True,
                            )
                        )
        return total_leftover_loss

    def _finish_day(self) -> None:
        if self._day_finished:
            return
        self._day_finished = True
        sound_fx.play_day_end()
        self._settle_end_of_day_leftovers()
        ai_opp = getattr(self.game_mgr, "ai_opponent_id", "")
        if ai_opp:
            if self.game_mgr.daily_gold >= self.ai_rival_gold:
                rnd_idx = int(getattr(self.game_mgr, "tournament_round_idx", 0))
                bonus = 3000 + rnd_idx * 2000
                self.game_mgr.add_gold(bonus)
                self.game_mgr.tournament_round_idx = min(5, rnd_idx + 1)
            self.game_mgr.ai_opponent_id = ""
        summary = self.game_mgr.complete_day()
        self.game_mgr.save_game()
        if self.scene_mgr:
            self.scene_mgr.change_scene("result", result_data=summary, show_loading=True)

    # ==================================================================
    # 화면 렌더링 (draw)
    # ==================================================================
    def draw(self, surface: pygame.Surface) -> None:
        # 1. 중단 야시장 배경 & 포차 인테리어 소품 (y=65~345)
        bg_country = (
            self.game_mgr.current_chapter
            if self.game_mgr.mode == "WORLD_TOUR"
            else self.game_mgr.get_selected_character_data()["country"]
        )
        art_renderer.draw_country_background(
            surface,
            config.CUSTOMER_AREA_RECT,
            country_id=bg_country,
            interior_levels=self.game_mgr.interior_levels,
            time_tick=self.time_tick,
        )

        # 피버 타임 중일 때 배경 네온 보더 연출
        if self.fever_timer > 0.0:
            pulse = max(0.4, min(1.0, 0.72 + 0.28 * math.sin(self.time_tick * 10.0)))
            art_renderer.draw_alpha_overlay(
                surface,
                config.CUSTOMER_AREA_RECT,
                (255, 70, 180, 35),
                border_radius=0,
            )
            border_col = (int(255 * pulse), int(210 * pulse), int(60 * pulse))
            pygame.draw.rect(
                surface,
                border_col,
                config.CUSTOMER_AREA_RECT,
                width=4,
            )

        # 2. 중단 손님 대기 슬롯 & 손님 렌더링
        for idx in range(self.max_customer_slots):
            s_rect = self._compute_customer_slot_rect(idx)
            cust = self.customers[idx] if idx < len(self.customers) else None
            if cust is not None:
                cust.rect = s_rect
                cust.draw(surface, time_tick=self.time_tick)
            else:
                # 빈 좌석 가이드 라인
                seat_bar = pygame.Rect(s_rect.x + 20, s_rect.bottom - 14, s_rect.width - 40, 8)
                pygame.draw.rect(surface, (42, 36, 54), seat_bar, border_radius=4)

        # 3. 중단 좌측 포차 마스터 아바타 & [SPACE] 액티브 스킬 패널
        self._draw_chef_skill_panel(surface)

        # 스토리 모드일 때 [🎬 스토리] 버튼 & 현재 일차 목표 가이드 팁 배너 (또는 32강 AI 대결 바 / 장인 모드 가이드 배너)
        if getattr(self.game_mgr, "ai_opponent_id", ""):
            self._draw_ai_tournament_hud(surface)
        elif self.game_mgr.mode == "WORLD_TOUR":
            self._draw_story_hud_helpers(surface)
        elif self.game_mgr.mode == "SPECIALIST":
            self._draw_specialist_hud_banner(surface)

        # 4. 하단 1인칭 포차 스테인리스/목재 카운터 & 5개 조리 스테이션 (y=345~720)
        self._draw_counter_and_stations(surface)

        # 5. 상단 HUD 바 (y=0~65)
        self._draw_hud(surface)

        # 6. 최상단 레이어: 비행 디쉬 애니메이션(FlyingDishEffect), 파티클, 플로팅 텍스트
        self.particles.draw(surface)

        # 7. 스토리 컷신 대화 오버레이 (활성화 시 최상단 표시)
        if self.active_cutscene is not None:
            self._cutscene_next_rect, self._cutscene_skip_rect = art_renderer.draw_story_cutscene_overlay(
                surface,
                self.active_cutscene,
                line_idx=self.cutscene_line_idx,
                time_tick=self.time_tick,
            )

    def _draw_ai_tournament_hud(self, surface: pygame.Surface) -> None:
        """32강 월드 포차 그랑프리 AI 보스전 실시간 매출 줄다리기 HUD를 표시한다."""
        from data.characters import get_character
        is_mob = config.is_mobile_ui()
        ai_id = getattr(self.game_mgr, "ai_opponent_id", "chef_cn_sichuan")
        ai_char = get_character(ai_id)
        rnd_labels = ["32강전", "16강전", "8강전", "4강 준결승", "결승전", "챔피언 방어전"]
        rnd_idx = min(5, int(getattr(self.game_mgr, "tournament_round_idx", 0)))
        bar_rect = pygame.Rect(198, 68, 1068, 30)
        art_renderer.draw_alpha_overlay(surface, bar_rect, (22, 16, 36, 228), border_radius=8)
        pygame.draw.rect(surface, config.GOLD, bar_rect, width=2, border_radius=8)

        my_g = max(0, self.game_mgr.daily_gold)
        ai_g = max(0, self.ai_rival_gold)
        tot = max(1, my_g + ai_g)
        my_ratio = my_g / float(tot) if (my_g + ai_g) > 0 else 0.5
        gauge_pad = 160 if is_mob else 290
        gauge_rect = pygame.Rect(bar_rect.x + gauge_pad, bar_rect.y + 7, bar_rect.width - gauge_pad * 2, 16)
        pygame.draw.rect(surface, (185, 48, 58), gauge_rect, border_radius=6)
        my_w = int(gauge_rect.width * my_ratio)
        if my_w > 0:
            pygame.draw.rect(surface, (52, 198, 118), (gauge_rect.x, gauge_rect.y, my_w, gauge_rect.height), border_radius=6)
        pygame.draw.rect(surface, config.WHITE, gauge_rect, width=1, border_radius=6)

        xs_f = config.get_font(13 if is_mob else 12, bold=True)
        if is_mob:
            left_s = xs_f.render(f"👨‍🍳 {my_g:,}", True, (118, 255, 168))
            right_s = xs_f.render(f"{ai_g:,} ⚔️", True, (255, 152, 152))
        else:
            left_s = xs_f.render(f"🏆 [{rnd_labels[rnd_idx]}] 나: {my_g:,}원", True, (118, 255, 168))
            reg_lbl = ai_char.get("region_name", ai_char.get("region", ""))
            right_s = xs_f.render(f"AI 라이벌 [{reg_lbl} {ai_char['name']}]: {ai_g:,}원 ⚔️", True, (255, 152, 152))
        surface.blit(left_s, (bar_rect.x + 12, bar_rect.y + 6))
        surface.blit(right_s, (bar_rect.right - right_s.get_width() - 12, bar_rect.y + 6))

    def _draw_story_hud_helpers(self, surface: pygame.Surface) -> None:
        """스토리 모드 전용 [🎬 스토리] 다시보기 버튼과 일차별 가이드 배너를 표시한다."""
        is_mob = config.is_mobile_ui()
        xs_f = config.get_font(15 if is_mob else 13, bold=True)
        mx, my = self._hover_pos
        hov = self.story_replay_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            (92, 62, 142) if hov else (62, 42, 102),
            self.story_replay_btn_rect,
            border_radius=7,
        )
        pygame.draw.rect(surface, config.GOLD, self.story_replay_btn_rect, width=2, border_radius=7)
        st_lbl = xs_f.render("🎬" if is_mob else "🎬 스토리 보기", True, config.GOLD)
        surface.blit(st_lbl, st_lbl.get_rect(center=self.story_replay_btn_rect.center))

        if is_mob:
            # 모바일 그림 중심 모드에서는 손님 머리 위 긴 줄글 배너를 숨겨 대형 음식 말풍선을 돋보이게 한다.
            return

        prog = self.game_mgr.get_story_progression()
        tip_text = str(prog.get("gameplay_tip", "") or "")
        if tip_text:
            tip_rect = pygame.Rect(324, 70, 942, 26)
            art_renderer.draw_alpha_overlay(surface, tip_rect, (18, 22, 38, 225), border_radius=7)
            pygame.draw.rect(surface, (112, 165, 238), tip_rect, width=1, border_radius=7)
            tip_surf = xs_f.render(f"💡 {tip_text}", True, (235, 245, 255))
            surface.blit(tip_surf, (tip_rect.x + 12, tip_rect.y + 3))

    def _draw_specialist_hud_banner(self, surface: pygame.Surface) -> None:
        """단일 메뉴 장인 모드 전용 상단 워크플로우 안내 배너를 표시한다."""
        if config.is_mobile_ui():
            # 모바일에서는 상단 긴 설명 문구 배너를 생략하고 손님 및 음식 그림에 집중한다.
            return
        spec = self.game_mgr.get_selected_specialist_data()
        xs_f = config.get_font(13, bold=True)
        tip_rect = pygame.Rect(198, 68, 1068, 28)
        art_renderer.draw_alpha_overlay(surface, tip_rect, (22, 20, 42, 228), border_radius=8)
        pygame.draw.rect(surface, spec.get("theme_accent", config.GOLD), tip_rect, width=2, border_radius=8)
        if spec.get("id") == "bungeo":
            msg = (
                f"🎯 [{spec['emoji']} {spec['name']}] ① 좌측 속재료 선택 후 우측 빈 틀 터치(반죽+속 붓기) → "
                "② 앞면 익으면 터치해 '뒤집기(🔄)' → ③ 황금빛 완성(✨) 시 터치해 꺼내기!"
            )
        else:
            msg = (
                f"🎯 [{spec['emoji']} {spec['name']}] ① 좌측 속재료/베이스 터치 → "
                "② 우측 6구 전문 화로 완성 터치(기본맛은 즉시 서빙 / ★토핑 주문은 중앙 트레이 이동) → ③ 특제 토핑 추가 후 서빙!"
            )
        for f_sz in (13, 12, 11):
            f_try = config.get_font(f_sz, bold=True)
            if f_try.size(msg)[0] <= tip_rect.width - 20:
                xs_f = f_try
                break
        tip_surf = xs_f.render(msg, True, (245, 248, 255))
        surface.blit(tip_surf, (tip_rect.x + 12, tip_rect.centery - tip_surf.get_height() // 2))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        is_mob = config.is_mobile_ui()
        hud_rect = pygame.Rect(config.HUD_RECT)
        pygame.draw.rect(surface, (20, 17, 32), hud_rect)
        pygame.draw.line(surface, config.GOLD, (0, hud_rect.bottom - 2), (config.SCREEN_WIDTH, hud_rect.bottom - 2), 2)

        title_f = config.get_font(18 if is_mob else 17, bold=True)
        sub_f = config.get_font(16 if is_mob else 15, bold=True)
        btn_f = config.get_font(18 if is_mob else 15, bold=True)

        # 1) 현재 모드 / 국가 / Day 배지 (x=14~268)
        if self.game_mgr.mode == "SPECIALIST":
            spec = self.game_mgr.get_selected_specialist_data()
            mode_tag = f"{spec['emoji']}" if is_mob else f"{spec['emoji']} {spec['name']}"
        elif self.game_mgr.mode == "GLOBAL_ENDLESS":
            mode_tag = "🏮" if is_mob else "🏮 글로벌 통합"
        else:
            ch_data = CHAPTERS.get(self.game_mgr.current_chapter, CHAPTERS["KR"])
            mode_tag = f"🗺️ {ch_data['id']}" if is_mob else f"🗺️ [{ch_data['id']}] {ch_data['name'][:7]}"
        day_label = f"{mode_tag} · D-{self.game_mgr.day}" if is_mob else f"{mode_tag} · Day {self.game_mgr.day}"
        day_txt = title_f.render(day_label, True, config.WHITE)
        if day_txt.get_width() > 252:
            day_txt = config.get_font(15, bold=True).render(day_label, True, config.WHITE)
        surface.blit(day_txt, (16, 8))

        total_gold_label = f"💰 {self.game_mgr.gold:,}" if is_mob else f"💰 자산: {self.game_mgr.gold:,}원"
        total_gold_txt = sub_f.render(total_gold_label, True, config.GOLD)
        surface.blit(total_gold_txt, (16, 34))

        # 2) 남은 영업 시간 타이머 바 (x=275~565)
        timer_box = pygame.Rect(275, 10, 285, 45)
        pygame.draw.rect(surface, (34, 30, 52), timer_box, border_radius=10)
        pygame.draw.rect(surface, config.UI_BORDER, timer_box, width=2, border_radius=10)

        t_ratio = max(0.0, min(1.0, self.time_left / max(1.0, self.day_duration)))
        bar_rect = pygame.Rect(timer_box.x + 10, timer_box.bottom - 14, timer_box.width - 20, 9)
        pygame.draw.rect(surface, (18, 16, 26), bar_rect, border_radius=4)
        bar_col = config.PATIENCE_HIGH if t_ratio > 0.4 else (config.PATIENCE_MID if t_ratio > 0.2 else config.PATIENCE_LOW)
        fill_w = int(bar_rect.width * t_ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, bar_col, (bar_rect.x, bar_rect.y, fill_w, bar_rect.height), border_radius=4)

        sec_left = int(math.ceil(self.time_left))
        t_str = f"⏱️ {sec_left}" if is_mob else f"⏱️ 남은 시간: {sec_left}초"
        t_lbl = sub_f.render(t_str, True, config.WHITE if sec_left > 15 else config.TEXT_WARNING)
        surface.blit(t_lbl, (timer_box.x + 12, timer_box.y + 5))

        # 3) 오늘의 매출 / 목표 매출 게이지 (x=570~874)
        rev_box = pygame.Rect(570, 10, 304, 45)
        pygame.draw.rect(surface, (34, 30, 52), rev_box, border_radius=10)
        target_gold = max(1, self.game_mgr.get_target_gold())
        daily_gold = self.game_mgr.daily_gold
        rev_ratio = min(1.0, daily_gold / float(target_gold))
        cleared = daily_gold >= target_gold

        pygame.draw.rect(surface, config.GOLD if cleared else config.UI_BORDER, rev_box, width=2, border_radius=10)
        r_str = f"💰 {daily_gold:,} / 🎯 {target_gold:,}" if is_mob else f"💰 매출 {daily_gold:,} / 목표 {target_gold:,}원"
        r_lbl = sub_f.render(
            r_str,
            True,
            config.GOLD if cleared else config.WHITE,
        )
        surface.blit(r_lbl, (rev_box.x + 12, rev_box.y + 5))

        r_bar = pygame.Rect(rev_box.x + 10, rev_box.bottom - 14, rev_box.width - 20, 9)
        pygame.draw.rect(surface, (18, 16, 26), r_bar, border_radius=4)
        r_fill = int(r_bar.width * rev_ratio)
        if r_fill > 0:
            pygame.draw.rect(
                surface,
                config.NEON_GREEN if cleared else config.GOLD,
                (r_bar.x, r_bar.y, r_fill, r_bar.height),
                border_radius=4,
            )

        # 4) 현재 콤보 & 피버 상태 배지 (x=882~1048)
        combo_box = pygame.Rect(882, 10, 168, 45)
        is_fever = self.fever_timer > 0.0
        c_bg = (96, 28, 78) if is_fever else (38, 32, 58)
        pygame.draw.rect(surface, c_bg, combo_box, border_radius=10)
        pygame.draw.rect(
            surface,
            config.NEON_PINK if is_fever else (config.NEON_ORANGE if self.game_mgr.combo >= 2 else config.UI_BORDER),
            combo_box,
            width=2,
            border_radius=10,
        )

        if is_fever:
            c_txt = sub_f.render(f"🎉 {self.fever_timer:.1f}s" if is_mob else f"🎉 FEVER {self.fever_timer:.1f}s!", True, config.NEON_YELLOW)
        elif self.game_mgr.combo > 0:
            c_txt = title_f.render(f"🔥 x{self.game_mgr.combo}" if is_mob else f"🔥 COMBO x{self.game_mgr.combo}", True, config.NEON_ORANGE)
        else:
            c_txt = sub_f.render("🔥 x0" if is_mob else "🔥 콤보 대기중", True, config.TEXT_SECONDARY)
        surface.blit(
            c_txt,
            (combo_box.centerx - c_txt.get_width() // 2, combo_box.centery - c_txt.get_height() // 2),
        )

        # 5) 우측 [옵션] 및 [상점으로] 버튼
        mx, my = self._hover_pos
        o_hov = self.options_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if o_hov else (48, 42, 72),
            self.options_btn_rect,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.GOLD if o_hov else config.UI_BORDER, self.options_btn_rect, width=2, border_radius=10)
        o_txt = btn_f.render("⚙️" if is_mob else "⚙️ 옵션", True, config.GOLD if o_hov else config.WHITE)
        surface.blit(o_txt, o_txt.get_rect(center=self.options_btn_rect.center))

        p_hov = self.pause_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if p_hov else (58, 52, 88),
            self.pause_btn_rect,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.NEON_CYAN if p_hov else config.UI_BORDER, self.pause_btn_rect, width=2, border_radius=10)
        p_txt = btn_f.render("🏪" if is_mob else "🏪 준비/상점", True, config.WHITE)
        surface.blit(
            p_txt,
            (
                self.pause_btn_rect.centerx - p_txt.get_width() // 2,
                self.pause_btn_rect.centery - p_txt.get_height() // 2,
            ),
        )

    def _draw_chef_skill_panel(self, surface: pygame.Surface) -> None:
        is_mob = config.is_mobile_ui()
        panel = self.chef_panel_rect
        char_data = self.game_mgr.get_selected_character_data()
        skill_unlocked = self.game_mgr.is_slot_unlocked_in_story("skill")
        skill_active = skill_unlocked and (self.game_mgr.skill_active_timer > 0.0)
        skill_ready = skill_unlocked and (self.game_mgr.skill_cooldown <= 0.0)

        # 반투명 패널 배경 (캐싱)
        art_renderer.draw_alpha_overlay(surface, panel, (24, 20, 38, 228), border_radius=14)

        border_col = (
            config.GOLD
            if skill_active
            else (char_data["accent_color"] if skill_ready else config.UI_BORDER)
        )
        pygame.draw.rect(surface, border_col, panel, width=2, border_radius=14)

        if self.game_mgr.mode == "SPECIALIST":
            any_cooking = any(s.state == STATE_COOKING for s in self.specialist_station.slots)
        else:
            any_cooking = any(
                s.state == STATE_COOKING for st in self.station_list for s in st.slots
            )
        av_state = "SKILL" if skill_active else ("COOKING" if any_cooking else "IDLE")

        if is_mob:
            # 모바일 그림 중심 스킬 패널: 스킬 설명 줄글을 모두 없애고 마스터 도트 아바타를 초대형(144x144)으로 확대
            av_rect = pygame.Rect(panel.centerx - 72, panel.y + 16, 144, 144)
            pygame.draw.rect(surface, (18, 15, 30), av_rect.inflate(8, 8), border_radius=14)
            pygame.draw.rect(surface, border_col, av_rect.inflate(8, 8), width=2, border_radius=14)
            art_renderer.draw_chef_avatar(
                surface,
                av_rect,
                character_id=self.game_mgr.selected_character,
                state=av_state,
                time_tick=self.time_tick,
            )

            s_rect = self.skill_btn_rect
            mx, my = self._hover_pos
            is_hov = s_rect.collidepoint(mx, my)

            if not skill_unlocked:
                bg_col = (38, 34, 54)
                icon_lbl = "🔒 D-4"
            elif skill_active:
                bg_col = (242, 168, 32)
                icon_lbl = f"⚡ {self.game_mgr.skill_active_timer:.1f}s"
            elif skill_ready:
                pulse = 0.88 + 0.12 * math.sin(self.time_tick * 6.0)
                bg_col = (245, 118, 36) if is_hov else (int(232 * pulse), int(96 * pulse), 32)
                icon_lbl = "⚡ SKILL!"
            else:
                bg_col = (54, 48, 72)
                cd = self.game_mgr.skill_cooldown
                icon_lbl = f"⏳ {int(math.ceil(cd))}s"

            pygame.draw.rect(surface, bg_col, s_rect, border_radius=12)
            pygame.draw.rect(
                surface,
                config.GOLD if (skill_ready or skill_active) else config.UI_BORDER,
                s_rect,
                width=3 if (skill_ready or skill_active) else 2,
                border_radius=12,
            )

            if skill_unlocked and not skill_ready and not skill_active:
                max_cd = max(1.0, float(char_data.get("cooldown", 35.0)))
                cd_ratio = 1.0 - min(1.0, self.game_mgr.skill_cooldown / max_cd)
                fill_w = int((s_rect.width - 6) * cd_ratio)
                if fill_w > 0:
                    pygame.draw.rect(
                        surface,
                        (82, 148, 215),
                        (s_rect.x + 3, s_rect.bottom - 9, fill_w, 6),
                        border_radius=3,
                    )

            big_btn_f = config.get_font(20, bold=True)
            t_surf = big_btn_f.render(icon_lbl, True, config.WHITE if skill_unlocked else config.GOLD)
            surface.blit(t_surf, t_surf.get_rect(center=s_rect.center))
            return

        # 마스터 아바타
        av_rect = pygame.Rect(panel.centerx - 46, panel.y + 8, 92, 92)
        art_renderer.draw_chef_avatar(
            surface,
            av_rect,
            character_id=self.game_mgr.selected_character,
            state=av_state,
            time_tick=self.time_tick,
        )

        name_f = config.get_font(16, bold=True)
        xs_f = config.get_font(13, bold=True)
        btn_f = config.get_font(16, bold=True)

        nm = name_f.render(f"{char_data['name']} ({char_data['country']})", True, config.WHITE)
        if nm.get_width() > panel.width - 10:
            nm = config.get_font(14, bold=True).render(f"{char_data['name']} ({char_data['country']})", True, config.WHITE)
        surface.blit(nm, (panel.centerx - nm.get_width() // 2, panel.y + 104))

        # 스킬 이름 & 설명 요약 (픽셀 폭 기반 줄바꿈으로 잘림 방지)
        sk_title = xs_f.render(f"★ {char_data['skill_name']}", True, config.GOLD)
        if sk_title.get_width() > panel.width - 10:
            sk_title = config.get_font(12, bold=True).render(f"★ {char_data['skill_name']}", True, config.GOLD)
        surface.blit(sk_title, (panel.centerx - sk_title.get_width() // 2, panel.y + 126))

        desc = str(char_data["skill_desc"])
        max_desc_w = panel.width - 12
        desc_f = config.get_font(11, bold=True)
        wrapped_lines: List[str] = []
        cur_line = ""
        for ch_char in desc:
            test_line = cur_line + ch_char
            if desc_f.size(test_line)[0] <= max_desc_w:
                cur_line = test_line
            else:
                if cur_line:
                    wrapped_lines.append(cur_line.strip())
                cur_line = ch_char.lstrip()
        if cur_line:
            wrapped_lines.append(cur_line.strip())

        line_y = panel.y + 146
        line_step = 15 if len(wrapped_lines) >= 3 else 17
        for ln in wrapped_lines[:3]:
            d_surf = desc_f.render(ln, True, (220, 216, 236))
            surface.blit(d_surf, (panel.centerx - d_surf.get_width() // 2, line_y))
            line_y += line_step

        # 하단 원터치 액티브 스킬 버튼 (불필요한 PC 단축키 안내 제거 & 16px 볼드 고시인성)
        s_rect = self.skill_btn_rect
        mx, my = self._hover_pos
        is_hov = s_rect.collidepoint(mx, my)

        if not skill_unlocked:
            bg_col = (38, 34, 54)
            lbl_top = "🔒 Day 4 해금"
            lbl_bot = "마스터 액티브 스킬"
        elif skill_active:
            bg_col = (242, 168, 32)
            lbl_top = "⚡ 스킬 발동 중!"
            lbl_bot = f"남은 시간 {self.game_mgr.skill_active_timer:.1f}초"
        elif skill_ready:
            pulse = 0.88 + 0.12 * math.sin(self.time_tick * 6.0)
            bg_col = (245, 118, 36) if is_hov else (int(232 * pulse), int(96 * pulse), 32)
            lbl_top = "⚡ 스킬 발동!"
            lbl_bot = char_data["skill_name"]
        else:
            bg_col = (54, 48, 72)
            cd = self.game_mgr.skill_cooldown
            lbl_top = f"⏳ 쿨타임 {int(math.ceil(cd))}초"
            lbl_bot = char_data["skill_name"]

        pygame.draw.rect(surface, bg_col, s_rect, border_radius=11)
        pygame.draw.rect(
            surface,
            config.GOLD if (skill_ready or skill_active) else config.UI_BORDER,
            s_rect,
            width=3 if (skill_ready or skill_active) else 2,
            border_radius=11,
        )

        # 쿨타임 진행 게이지
        if skill_unlocked and not skill_ready and not skill_active:
            max_cd = max(1.0, float(char_data.get("cooldown", 35.0)))
            cd_ratio = 1.0 - min(1.0, self.game_mgr.skill_cooldown / max_cd)
            fill_w = int((s_rect.width - 4) * cd_ratio)
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    (82, 148, 215),
                    (s_rect.x + 2, s_rect.bottom - 7, fill_w, 5),
                    border_radius=2,
                )

        t1 = btn_f.render(lbl_top, True, config.WHITE if skill_unlocked else config.GOLD)
        t2 = xs_f.render(lbl_bot, True, config.GOLD if skill_ready else (config.WHITE if skill_unlocked else config.TEXT_SECONDARY))
        surface.blit(t1, (s_rect.centerx - t1.get_width() // 2, s_rect.y + 6))
        surface.blit(t2, (s_rect.centerx - t2.get_width() // 2, s_rect.y + 30))

    # 별칭 호환
    _draw_character_skill_panel = _draw_chef_skill_panel

    def _draw_locked_slot_cover(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        slot_key: str,
        title: str,
        sub_desc: str,
    ) -> None:
        """아직 스토리에서 해금되지 않은 조리 기구/트레이 위에 선명한 고대비 잠금 안내 카드를 그린다."""
        art_renderer.draw_alpha_overlay(surface, rect, (18, 20, 36, 236), border_radius=14)
        pygame.draw.rect(surface, (118, 128, 172), rect, width=2, border_radius=14)

        inner_card = pygame.Rect(rect.x + 10, rect.centery - 74, rect.width - 20, 148)
        pygame.draw.rect(surface, (28, 30, 52), inner_card, border_radius=12)
        pygame.draw.rect(surface, config.GOLD, inner_card, width=2, border_radius=12)

        hint_str = self._get_slot_unlock_hint(slot_key).split(":")[0]

        badge_rect = pygame.Rect(rect.centerx - 84, inner_card.y + 14, 168, 38)
        pygame.draw.rect(surface, (62, 46, 88), badge_rect, border_radius=10)
        pygame.draw.rect(surface, config.GOLD, badge_rect, width=2, border_radius=10)

        f_lock = config.get_font(17, bold=True)
        f_title = config.get_font(17, bold=True)
        f_sub = config.get_font(13, bold=True)

        lk_s = f_lock.render(hint_str, True, config.GOLD)
        surface.blit(lk_s, lk_s.get_rect(center=badge_rect.center))

        active_tf = f_title
        for f_sz in (17, 16, 15, 14):
            active_tf = config.get_font(f_sz, bold=True)
            if active_tf.size(title)[0] <= inner_card.width - 14:
                break
        t_s = active_tf.render(title, True, config.WHITE)
        surface.blit(t_s, t_s.get_rect(center=(rect.centerx, inner_card.y + 78)))

        active_sf = f_sub
        for f_sz in (13, 12, 11):
            active_sf = config.get_font(f_sz, bold=True)
            if active_sf.size(sub_desc)[0] <= inner_card.width - 14:
                break
        sub_s = active_sf.render(sub_desc, True, config.NEON_CYAN)
        surface.blit(sub_s, sub_s.get_rect(center=(rect.centerx, inner_card.y + 114)))

    def _draw_counter_and_stations(self, surface: pygame.Surface) -> None:
        counter_rect = pygame.Rect(config.COUNTER_RECT)
        pygame.draw.rect(surface, config.POCHA_COUNTER_BG, counter_rect)
        # 카운터 상단 스테인리스 상판 엣지
        pygame.draw.rect(surface, config.POCHA_STAINLESS_DARK, (0, counter_rect.y, config.SCREEN_WIDTH, 8))
        pygame.draw.line(surface, config.POCHA_STAINLESS, (0, counter_rect.y + 1), (config.SCREEN_WIDTH, counter_rect.y + 1), 2)

        if self.game_mgr.mode == "SPECIALIST":
            self.specialist_station.draw(surface, time_tick=self.time_tick)
            self.assembly_tray.draw(surface, time_tick=self.time_tick)
            return

        # 4개 조리 스테이션 & 중앙 조립 트레이 렌더링 (모바일 시인성을 위해 상단 단축키 텍스트 오버레이 제거)
        self.mold_station.draw(surface, time_tick=self.time_tick)
        self.dispenser_station.draw(surface, time_tick=self.time_tick)
        self.assembly_tray.draw(surface, time_tick=self.time_tick)
        self.grill_station.draw(surface, time_tick=self.time_tick)
        self.batch_pot_station.draw(surface, time_tick=self.time_tick)

        # 스토리 모드에서 아직 잠겨 있는 조리 기구에 잠금 커버 표시 (트레이는 적재·서빙을 위해 상시 개방하고 내부 토핑 영역만 잠금 표시)
        if not self.game_mgr.is_slot_unlocked_in_story("dispenser"):
            self._draw_locked_slot_cover(
                surface,
                self.dispenser_rect,
                "dispenser",
                self.dispenser_station.meta["name"],
                "뜨끈한 국물·음료 자동 서버",
            )
        if not self.game_mgr.is_slot_unlocked_in_story("grill"):
            self._draw_locked_slot_cover(
                surface,
                self.grill_rect,
                "grill",
                self.grill_station.meta["name"],
                "직화 구이 & 특제 소스 조합",
            )
        if not self.game_mgr.is_slot_unlocked_in_story("batch_pot"):
            self._draw_locked_slot_cover(
                surface,
                self.batch_pot_rect,
                "batch_pot",
                self.batch_pot_station.meta["name"],
                "한 번에 3인분 대량 조리 기구",
            )
