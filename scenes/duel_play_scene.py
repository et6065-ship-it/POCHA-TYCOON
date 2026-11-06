"""
scenes/duel_play_scene.py
'전세계 길거리 음식 포차 타이쿤' 1:1 실시간 네트워크 매출 타임어택 결투 씬 (DuelPlayScene).
- PlayScene을 상속하여 1인칭 5개 조리 구역, 원클릭 자동 서빙, 마스터 스킬, 단축키를 100% 동일하게 지원
- GameManager.create_duel_manager()를 통해 싱글플레이 세이브와 분리된 공정한 스펙(동일 기구 레벨) 적용
- 동일 시드(match_seed) 기반 결정론적 손님 생성으로 양측에 공정한 주문 흐름 제공
- 상단 HUD에 실시간 1:1 매출 줄다리기 게이지(Tug-of-War), 격차 표시, 상대방 실시간 매출/콤보/스킬 상태 렌더링
"""

from __future__ import annotations

import math
import random
import time
from typing import Any, Dict, Optional, Tuple
import pygame

import config
from core import art_renderer
from core.effects import sound_fx
from core.game_manager import GameManager
from core.network_manager import DuelNetworkManager, duel_network
from core.scene_manager import SceneManager
from data.chapters import CHAPTERS
from data.characters import CHARACTERS
from entities.customer import Customer
from scenes.play_scene import PlayScene


class DuelPlayScene(PlayScene):
    """1:1 네트워크 실시간 매출 타임어택 결투 플레이 씬."""

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        scene_mgr: Optional[SceneManager] = None,
        **kwargs: Any,
    ) -> None:
        self.persistent_game_mgr: Optional[GameManager] = game_mgr
        self.net: DuelNetworkManager = duel_network

        # 결투 설정 파라미터 추출
        self.duel_chapter: str = str(kwargs.get("chapter", "KR")).upper()
        if self.duel_chapter not in CHAPTERS:
            self.duel_chapter = "KR"
        self.station_level: int = int(kwargs.get("station_level", config.DUEL_DEFAULT_STATION_LEVEL))
        self.my_char: str = str(kwargs.get("my_char", "chef_kr"))
        self.opp_char: str = str(kwargs.get("opp_char", "chef_jp"))
        self.my_name: str = str(kwargs.get("my_name", "나 (ME)"))
        self.opp_name: str = str(kwargs.get("opp_name", "상대 (RIVAL)"))
        self.match_seed: int = int(kwargs.get("match_seed", 20261030))

        # 결정론적 손님 스폰 RNG (양측 동일한 손님/주문 등장 보장)
        self.duel_rng: random.Random = random.Random(self.match_seed)

        # 싱글플레이 세이브 데이터를 건드리지 않는 공정 결투용 독립 GameManager 생성
        duel_mgr = GameManager.create_duel_manager(
            chapter=self.duel_chapter,
            character=self.my_char,
            station_level=self.station_level,
        )

        # 상대방 실시간 동기화 상태
        self.opp_stats: Dict[str, Any] = {
            "gold": 0,
            "combo": 0,
            "max_combo": 0,
            "served": 0,
            "missed": 0,
            "fever": False,
            "skill": False,
            "finished": False,
            "char": self.opp_char,
            "name": self.opp_name,
        }
        self._sync_timer: float = 0.0
        self._finish_wait_timer: float = 0.0
        self._waiting_opp_finish: bool = False
        self._opponent_disconnected: bool = False
        self._match_start_wall: float = time.perf_counter()
        self._last_wall_tick: float = self._match_start_wall

        super().__init__(game_mgr=duel_mgr, scene_mgr=scene_mgr, **kwargs)
        self._match_start_wall = time.perf_counter()
        self._last_wall_tick = self._match_start_wall

    def on_enter(self, **kwargs: Any) -> None:
        # SceneManager가 scene_obj.game_mgr = self.game_mgr로 덮어쓰는 것을 방지하고 독립 결투 매니저 유지
        self.duel_chapter = str(kwargs.get("chapter", self.duel_chapter)).upper()
        self.station_level = int(kwargs.get("station_level", self.station_level))
        self.my_char = str(kwargs.get("my_char", self.my_char))
        self.opp_char = str(kwargs.get("opp_char", self.opp_char))
        self.my_name = str(kwargs.get("my_name", self.my_name))
        self.opp_name = str(kwargs.get("opp_name", self.opp_name))
        self.match_seed = int(kwargs.get("match_seed", self.match_seed))
        if "day_duration" in kwargs:
            self.day_duration = float(kwargs["day_duration"])

        self.duel_rng = random.Random(self.match_seed)
        self.game_mgr = GameManager.create_duel_manager(
            chapter=self.duel_chapter,
            character=self.my_char,
            station_level=self.station_level,
        )
        for st in self.station_list:
            st.game_mgr = self.game_mgr
        if hasattr(self, "specialist_station") and self.specialist_station is not None:
            self.specialist_station.game_mgr = self.game_mgr
        self.assembly_tray.game_mgr = self.game_mgr

        self._setup_new_day()
        self._match_start_wall = time.perf_counter()
        self._last_wall_tick = self._match_start_wall
        self._send_state_sync()

    def _spawn_customer_in_empty_slot(self) -> Optional[Customer]:
        """양측 동일한 시드(self.duel_rng)를 사용하여 결정론적으로 손님을 생성한다."""
        empty_indices = [i for i, c in enumerate(self.customers) if c is None]
        if not empty_indices:
            return None
        slot_idx = empty_indices[0]
        slot_rect = self._compute_customer_slot_rect(slot_idx)
        cust = Customer.create_random(
            slot_index=slot_idx,
            game_mgr=self.game_mgr,
            rect=slot_rect,
            rng=self.duel_rng,
        )
        self.customers[slot_idx] = cust
        if cust.is_vip:
            sound_fx.play_vip_arrive()
        else:
            sound_fx.play_customer_arrive()
        return cust

    def try_auto_serve(
        self,
        recipe_id: str,
        start_pos: Optional[Tuple[int, int]] = None,
    ) -> bool:
        prev_fever = self.fever_timer
        served = super().try_auto_serve(recipe_id, start_pos=start_pos)
        if served:
            self._send_state_sync()
            if prev_fever <= 0.0 and self.fever_timer > 0.0:
                self.net.send(
                    {
                        "type": "EVENT_NOTIFY",
                        "event": "FEVER",
                        "text": f"🎉 상대방({self.my_name})이 FEVER TIME에 돌입했습니다!",
                    }
                )
        return served

    def activate_skill(self) -> bool:
        activated = super().activate_skill()
        if activated:
            char_data = self.game_mgr.get_selected_character_data()
            self._send_state_sync()
            self.net.send(
                {
                    "type": "EVENT_NOTIFY",
                    "event": "SKILL",
                    "text": f"⚡ 상대방이 [{char_data['skill_name']}] 스킬을 발동했습니다!",
                }
            )
        return activated

    def _send_state_sync(self, finished: bool = False) -> None:
        if not self.net.connected:
            return
        self.net.send(
            {
                "type": "MATCH_FINISH" if finished else "STATE_SYNC",
                "gold": int(self.game_mgr.daily_gold),
                "combo": int(self.game_mgr.combo),
                "max_combo": int(self.game_mgr.max_combo),
                "served": int(self.game_mgr.served_customers),
                "missed": int(self.game_mgr.missed_customers),
                "fever": bool(self.fever_timer > 0.0),
                "skill": bool(self.game_mgr.skill_active_timer > 0.0),
                "time_left": round(float(self.time_left), 2),
                "char": self.my_char,
                "name": self.my_name,
                "finished": bool(finished),
            }
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # 우측 상단 [대기실로/기권] 버튼 클릭
            if self.pause_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                self._forfeit_and_return_to_lobby()
                return
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            sound_fx.play_click()
            self._forfeit_and_return_to_lobby()
            return

        super().handle_event(event)

    def _forfeit_and_return_to_lobby(self) -> None:
        if self.net.connected:
            self.net.send({"type": "PLAYER_FORFEIT", "name": self.my_name})
        if self.scene_mgr:
            self.scene_mgr.change_scene("duel_lobby", rematch=True)

    def update(self, dt: float) -> None:
        now_wall = time.perf_counter()
        wall_step = max(0.0, now_wall - self._last_wall_tick)
        self._last_wall_tick = now_wall
        # 저사양 PC에서 main.py가 dt를 0.1초로 클램핑하더라도 실제 경과 시간(최대 0.5초)으로 조리·타이머 진행
        sim_dt = max(0.0, float(dt), min(0.5, wall_step))

        # 네트워크 패킷 수신 처리
        self.net.send_ping_if_needed(interval=2.0)
        for msg in self.net.poll_messages():
            mtype = msg.get("type")
            if mtype in ("STATE_SYNC", "MATCH_FINISH"):
                self.opp_stats["gold"] = int(msg.get("gold", self.opp_stats["gold"]))
                self.opp_stats["combo"] = int(msg.get("combo", self.opp_stats["combo"]))
                self.opp_stats["max_combo"] = int(msg.get("max_combo", self.opp_stats["max_combo"]))
                self.opp_stats["served"] = int(msg.get("served", self.opp_stats["served"]))
                self.opp_stats["missed"] = int(msg.get("missed", self.opp_stats["missed"]))
                self.opp_stats["fever"] = bool(msg.get("fever", False))
                self.opp_stats["skill"] = bool(msg.get("skill", False))
                # 호스트 기준 남은 시간 동기화 (프레임 드랍으로 인한 양측 타이머 격차 원천 차단)
                if not getattr(self.net, "is_host", self.net.role == "HOST") and "time_left" in msg and not self._day_finished:
                    host_tl = max(0.0, float(msg["time_left"]))
                    local_tl = max(0.0, self.day_duration - (now_wall - self._match_start_wall))
                    if abs(local_tl - host_tl) > 0.5:
                        self._match_start_wall = now_wall - (self.day_duration - host_tl)
                        self.time_left = host_tl
                if mtype == "MATCH_FINISH" or msg.get("finished"):
                    self.opp_stats["finished"] = True
                    # 상대방이 정상 종료했고 내 타이머도 2.5초 이하라면 동시에 종료 처리
                    if not self._day_finished and self.time_left <= 2.5:
                        self.time_left = 0.0
                        self._finish_day()
                        return

            elif mtype == "EVENT_NOTIFY":
                ev_txt = str(msg.get("text", "상대방 스킬 발동!"))
                self.particles.spawn_floating_text(
                    ev_txt,
                    config.SCREEN_WIDTH // 2,
                    92,
                    color=config.NEON_CYAN,
                    size=19,
                    duration=1.8,
                )

            elif mtype == "PLAYER_FORFEIT":
                self.opp_stats["finished"] = True
                self.particles.spawn_floating_text(
                    "🏳️ 상대방이 기권하여 대기실로 이동했습니다!",
                    config.SCREEN_WIDTH // 2,
                    120,
                    color=config.GOLD,
                    size=22,
                )
                self._transition_to_duel_result(opponent_forfeited=True)
                return

            elif mtype == "NET_DISCONNECTED":
                self._opponent_disconnected = True
                self.opp_stats["finished"] = True
                self.particles.spawn_floating_text(
                    "⚠ 상대방과의 네트워크 연결이 끊어졌습니다!",
                    config.SCREEN_WIDTH // 2,
                    120,
                    color=config.TEXT_WARNING,
                    size=21,
                )

        # 내 영업 시간이 끝나 상대방의 최종 패킷을 잠시 기다리는 중인 경우
        if self._waiting_opp_finish:
            self.particles.update(sim_dt)
            self._finish_wait_timer -= sim_dt
            if self.opp_stats.get("finished", False) or not self.net.connected or self._finish_wait_timer <= 0.0:
                self._transition_to_duel_result()
            return

        if self.paused or self._day_finished:
            return

        # 실제 벽시계(Wall-clock) 기준으로 남은 영업 시간 계산 -> 저사양 PC 5FPS 환경에서도 30초 밀림 현상 0%
        self.time_tick += sim_dt
        real_elapsed = now_wall - self._match_start_wall
        self.time_left = max(0.0, self.day_duration - real_elapsed)
        if 0.0 < self.time_left <= 10.0:
            cur_sec = int(math.ceil(self.time_left))
            if cur_sec != getattr(self, "_last_timer_tick_sec", -1):
                self._last_timer_tick_sec = cur_sec
                sound_fx.play_timer_tick(urgent=(cur_sec <= 5))
        if self.time_left <= 0.0:
            self._finish_day()
            return

        if self.game_mgr.skill_cooldown > 0.0:
            self.game_mgr.skill_cooldown = max(0.0, self.game_mgr.skill_cooldown - sim_dt)
        if self.game_mgr.skill_active_timer > 0.0:
            self.game_mgr.skill_active_timer = max(0.0, self.game_mgr.skill_active_timer - sim_dt)
        if self.fever_timer > 0.0:
            self.fever_timer = max(0.0, self.fever_timer - sim_dt)
        if self.patience_freeze_timer > 0.0:
            self.patience_freeze_timer = max(0.0, self.patience_freeze_timer - sim_dt)

        if self.game_mgr.combo > 0:
            self.game_mgr.combo_timer -= sim_dt
            if self.game_mgr.combo_timer <= 0.0:
                self.game_mgr.break_combo()

        # 결정론적 손님 스폰 타이머
        self.spawn_timer -= sim_dt * (1.65 if self.fever_timer > 0.0 else 1.0)
        if self.spawn_timer <= 0.0:
            self._spawn_customer_in_empty_slot()
            ch_data = CHAPTERS.get(self.game_mgr.current_chapter, CHAPTERS["KR"])
            sp_min, sp_max = ch_data.get("customer_spawn_interval", config.CUSTOMER_SPAWN_INTERVAL)
            self.spawn_timer = self.duel_rng.uniform(float(sp_min), float(sp_max))

        if all(c is None for c in self.customers) and self.spawn_timer > 1.0:
            self.spawn_timer = 0.6

        is_patience_frozen = (self.patience_freeze_timer > 0.0) or (
            self.game_mgr.skill_active_timer > 0.0 and self.game_mgr.selected_character == "chef_mx"
        )
        for idx, cust in enumerate(self.customers):
            if cust is None:
                continue
            ev = cust.update(sim_dt, patience_freeze=is_patience_frozen)
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

        sel_eff = str(self.game_mgr.get_selected_character_data().get("skill_effect", "") or "")
        kr_rush_active = (
            self.game_mgr.skill_active_timer > 0.0
            and (
                self.game_mgr.selected_character == "chef_kr"
                or sel_eff in ("kr_rush", "instant_and_speed", "speed_and_freeze")
            )
        )
        for st in self.station_list:
            prev_states = [s.state for s in st.slots]
            if kr_rush_active and st.slot_type in ("mold", "grill", "batch_pot"):
                for s in st.slots:
                    if s.state == "COOKING":
                        s.elapsed += sim_dt
            st.update(sim_dt)
            for s_idx, slot in enumerate(st.slots):
                prev_st = prev_states[s_idx] if s_idx < len(prev_states) else slot.state
                if slot.is_flip_ready and not getattr(slot, "_flip_sound_played", False):
                    slot._flip_sound_played = True
                    sound_fx.play_flip_ready()
                if prev_st == "COOKING" and slot.state == "READY":
                    if st.slot_type == "dispenser":
                        sound_fx.play_drink_ready()
                    else:
                        sound_fx.play_ready()
                        self.particles.emit_stars(slot.rect.centerx, slot.rect.centery, count=5)
                elif (
                    slot.state == "READY"
                    and slot.can_burn
                    and slot.burn_progress >= 0.65
                    and not getattr(slot, "_burn_warn_played", False)
                ):
                    slot._burn_warn_played = True
                    sound_fx.play_burn_warning()
                elif prev_st == "READY" and slot.state == "BURNT":
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

        self._ambient_particle_timer += sim_dt
        if self._ambient_particle_timer >= 0.35:
            self._ambient_particle_timer = 0.0
            for st in (self.mold_station, self.grill_station, self.batch_pot_station):
                st_cooking = False
                for slot in st.slots:
                    if slot.state == "COOKING":
                        st_cooking = True
                        if st.slot_type == "grill":
                            self.particles.emit_flame(slot.rect.centerx, slot.rect.centery, count=2)
                        else:
                            self.particles.emit_smoke(slot.rect.centerx, slot.rect.top + 10, count=1)
                if st_cooking:
                    sound_fx.play_ambient_cooking(st.slot_type)

        self.assembly_tray.update(sim_dt)
        hold_fb = self.assembly_tray.pop_hold_feedback()
        if hold_fb is not None:
            fb_pos = hold_fb.get("pos", self.assembly_tray.rect.center)
            self._handle_station_feedback(hold_fb, fb_pos)
        self.particles.update(sim_dt)

        # 주기적 네트워크 상태 동기화
        self._sync_timer += sim_dt
        if self._sync_timer >= config.DUEL_STATE_SYNC_INTERVAL:
            self._sync_timer = 0.0
            self._send_state_sync(finished=False)

    def _finish_day(self) -> None:
        if self._day_finished:
            return
        self._day_finished = True
        sound_fx.play_day_end()
        self._send_state_sync(finished=True)

        if self.opp_stats.get("finished", False) or not self.net.connected:
            self._transition_to_duel_result()
        else:
            self._waiting_opp_finish = True
            self._finish_wait_timer = 2.5

    def _transition_to_duel_result(self, opponent_forfeited: bool = False) -> None:
        self._waiting_opp_finish = False
        my_summary = {
            "name": self.my_name,
            "char": self.my_char,
            "gold": int(self.game_mgr.daily_gold),
            "served": int(self.game_mgr.served_customers),
            "missed": int(self.game_mgr.missed_customers),
            "max_combo": int(self.game_mgr.max_combo),
        }
        opp_summary = {
            "name": self.opp_name,
            "char": self.opp_char,
            "gold": int(self.opp_stats.get("gold", 0)),
            "served": int(self.opp_stats.get("served", 0)),
            "missed": int(self.opp_stats.get("missed", 0)),
            "max_combo": int(self.opp_stats.get("max_combo", 0)),
            "forfeited": opponent_forfeited,
            "disconnected": self._opponent_disconnected,
        }
        if self.scene_mgr:
            self.scene_mgr.change_scene(
                "duel_result",
                my_summary=my_summary,
                opp_summary=opp_summary,
                chapter=self.duel_chapter,
                duration=int(self.day_duration),
                station_level=self.station_level,
            )

    # ==========================================================================
    # 1:1 결투 전용 상단 실시간 줄다리기 스코어보드 HUD
    # ==========================================================================
    def _draw_hud(self, surface: pygame.Surface) -> None:
        hud_rect = pygame.Rect(config.HUD_RECT)
        pygame.draw.rect(surface, (18, 15, 30), hud_rect)
        pygame.draw.line(surface, config.GOLD, (0, hud_rect.bottom - 2), (config.SCREEN_WIDTH, hud_rect.bottom - 2), 2)

        title_f = config.get_font(17, bold=True)
        sub_f = config.get_font(12, bold=True)
        num_f = config.get_font(20, bold=True)

        my_gold = int(self.game_mgr.daily_gold)
        opp_gold = int(self.opp_stats.get("gold", 0))
        diff = my_gold - opp_gold

        # 1) 좌측: 내 실시간 매출 & 콤보 박스 (x=12~362)
        my_box = pygame.Rect(12, 8, 350, 49)
        pygame.draw.rect(surface, (36, 28, 52), my_box, border_radius=10)
        pygame.draw.rect(surface, config.POCHA_ORANGE, my_box, width=2, border_radius=10)

        my_char_name = CHARACTERS.get(self.my_char, CHARACTERS["chef_kr"])["name"]
        m_lbl = sub_f.render(f"👑 나 ({my_char_name}) · 서빙 {self.game_mgr.served_customers}명", True, config.POCHA_WARM_LIGHT)
        m_val = num_f.render(f"💰 {my_gold:,}원", True, config.GOLD)
        surface.blit(m_lbl, (my_box.x + 12, my_box.y + 5))
        surface.blit(m_val, (my_box.x + 12, my_box.y + 22))

        if self.fever_timer > 0.0:
            c_str = f"🎉 FEVER {self.fever_timer:.1f}s"
            c_col = config.NEON_PINK
        elif self.game_mgr.combo >= 2:
            c_str = f"🔥 {self.game_mgr.combo} COMBO"
            c_col = config.NEON_ORANGE
        else:
            c_str = f"최고 {self.game_mgr.max_combo}콤보"
            c_col = config.TEXT_SECONDARY
        mc_surf = sub_f.render(c_str, True, c_col)
        surface.blit(mc_surf, (my_box.right - mc_surf.get_width() - 12, my_box.y + 18))

        # 2) 중앙: 실시간 매출 줄다리기 게이지 & 타이머 & 우위 배지 (x=372~778)
        center_box = pygame.Rect(372, 8, 406, 49)
        pygame.draw.rect(surface, (28, 24, 44), center_box, border_radius=10)
        pygame.draw.rect(surface, config.GOLD if diff >= 0 else config.NEON_CYAN, center_box, width=1, border_radius=10)

        sec_left = int(math.ceil(self.time_left))
        t_col = config.WHITE if sec_left > 15 else config.TEXT_WARNING

        if diff > 0:
            lead_str = f"🔥 +{diff:,}원 리드 중!"
            lead_col = config.TEXT_SUCCESS
        elif diff < 0:
            lead_str = f"⚡ {diff:,}원 추격 중!"
            lead_col = config.NEON_CYAN
        else:
            lead_str = "⚖️ 팽팽한 동점!"
            lead_col = config.GOLD

        top_line = sub_f.render(f"⏱️ 남은 시간 {sec_left}초   |   {lead_str}", True, t_col if sec_left <= 10 else lead_col)
        surface.blit(top_line, (center_box.centerx - top_line.get_width() // 2, center_box.y + 6))

        # 줄다리기 바 (내 매출 비율 vs 상대 매출 비율)
        tug_rect = pygame.Rect(center_box.x + 14, center_box.bottom - 16, center_box.width - 28, 10)
        pygame.draw.rect(surface, (42, 165, 225), tug_rect, border_radius=5)  # 우측(상대) 기본 색상
        total_g = my_gold + opp_gold
        my_ratio = 0.5 if total_g <= 0 else max(0.08, min(0.92, my_gold / float(total_g)))
        my_w = int(tug_rect.width * my_ratio)
        pygame.draw.rect(
            surface,
            config.POCHA_ORANGE,
            (tug_rect.x, tug_rect.y, my_w, tug_rect.height),
            border_radius=5,
        )
        # 중앙선 및 현재 경계 마커
        pygame.draw.line(
            surface,
            config.WHITE,
            (tug_rect.x + my_w, tug_rect.y - 2),
            (tug_rect.x + my_w, tug_rect.bottom + 2),
            3,
        )

        # 3) 우측: 상대방 실시간 매출 & 콤보/스킬 상태 박스 (x=788~1138)
        opp_box = pygame.Rect(788, 8, 350, 49)
        pygame.draw.rect(surface, (28, 34, 54), opp_box, border_radius=10)
        pygame.draw.rect(surface, config.NEON_CYAN, opp_box, width=2, border_radius=10)

        opp_char_name = CHARACTERS.get(self.opp_char, CHARACTERS["chef_jp"])["name"]
        ping_tag = f" ({self.net.latency_ms}ms)" if self.net.connected and self.net.latency_ms > 0 else ""
        o_lbl = sub_f.render(
            f"⚔ 상대 ({opp_char_name}) · 서빙 {self.opp_stats['served']}명{ping_tag}",
            True,
            config.NEON_CYAN,
        )
        o_val = num_f.render(f"💰 {opp_gold:,}원", True, config.WHITE)
        surface.blit(o_lbl, (opp_box.x + 12, opp_box.y + 5))
        surface.blit(o_val, (opp_box.x + 12, opp_box.y + 22))

        opp_combo = int(self.opp_stats.get("combo", 0))
        if self.opp_stats.get("fever"):
            oc_str = "🎉 상대 FEVER!"
            oc_col = config.NEON_PINK
        elif self.opp_stats.get("skill"):
            oc_str = "⚡ 상대 스킬중!"
            oc_col = config.GOLD
        elif opp_combo >= 2:
            oc_str = f"🔥 {opp_combo} COMBO"
            oc_col = config.NEON_ORANGE
        else:
            oc_str = f"최고 {self.opp_stats['max_combo']}콤보"
            oc_col = config.TEXT_SECONDARY
        oc_surf = sub_f.render(oc_str, True, oc_col)
        surface.blit(oc_surf, (opp_box.right - oc_surf.get_width() - 12, opp_box.y + 18))

        # 4) 우측 끝 [대기실로/기권] 버튼
        mx, my = self._hover_pos
        p_hov = self.pause_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if p_hov else config.UI_BUTTON,
            self.pause_btn_rect,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.UI_BORDER, self.pause_btn_rect, width=1, border_radius=10)
        p_txt = sub_f.render("🏳️ 대기실로", True, config.WHITE)
        surface.blit(
            p_txt,
            (
                self.pause_btn_rect.centerx - p_txt.get_width() // 2,
                self.pause_btn_rect.centery - p_txt.get_height() // 2,
            ),
        )
