"""
scenes/prep_scene.py
'전세계 길거리 음식 포차 타이쿤' 영업 준비 / 9개국 32인 지역별 마스터 선택 / 9개국 월드 투어 & 36종 글로벌 로드아웃 / 업그레이드 / 32강 그랑프리 씬.
- 탭 1 (character): 영토 면적·지역 식문화 비례 9개국 32인 지역별 포차 마스터 국가 필터 + 페이지 그리드 + 우측 상세 인스펙터
- 탭 2 (chapter):
  * 월드 투어 모드일 때: 9개국(KR, JP, MX, TW, CN, IN, US, RU, BR) 챕터 페이지네이션 & 포차스타(Pocha-sta) SNS 랭크 표시
  * 글로벌 야시장 통합 모드일 때: 4개 조리 슬롯별 9개국 기구(총 36종) 깔끔한 페이지 전환 커스텀 장착
- 탭 3 (upgrade): 조리 기구 5종(Lv.0~3) & 포차 인테리어 4종 업그레이드 상점
- 탭 4 (tournament): 32강 월드 포차 그랑프리 일러스트 배너 + 국가별 시드 배정 + 실시간 AI 보스전 출격
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import pygame

import config
from core import art_renderer
from core.effects import ParticleSystem, sound_fx
from core.game_manager import GameManager
from core.scene_manager import BaseScene, SceneManager
from data.chapters import (
    CHAPTER_ORDER,
    CHAPTERS,
    SLOT_TYPES,
    STATIONS_CATALOG,
    get_stations_by_slot,
)
from data.characters import (
    CHARACTER_ORDER,
    CHARACTERS,
    COUNTRY_FILTER_ORDER,
    COUNTRY_LABELS,
    get_characters_by_country,
)
from data.recipes import RECIPES
from data.tournament import TOURNAMENT_32_ROSTER, TOURNAMENT_TIERS
from data.upgrades import (
    INTERIOR_UPGRADE_ORDER,
    INTERIOR_UPGRADES,
    STATION_UPGRADE_ORDER,
    STATION_UPGRADES,
)


SLOT_KOR_NAMES: Dict[str, str] = {
    "mold": "① 몰드 구이 기구",
    "grill": "② 직화 그릴 · 튀김기",
    "batch_pot": "③ 대량 조리 팬",
    "dispenser": "④ 음료 디스펜서",
}


class PrepScene(BaseScene):
    """영업 준비, 32인 포차 마스터 선택, 9개국 챕터/글로벌 36기구 배치, 상점 및 32강 토너먼트 씬."""

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        scene_mgr: Optional[SceneManager] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(game_mgr, scene_mgr, **kwargs)
        self.time_tick: float = 0.0
        self.particles: ParticleSystem = ParticleSystem()

        # 현재 활성 탭: "character", "chapter", "upgrade", "tournament"
        initial_tab = str(kwargs.get("initial_tab", "chapter")).lower()
        if initial_tab not in ("character", "chapter", "upgrade", "tournament"):
            initial_tab = "chapter"
        self.active_tab: str = initial_tab

        # 탭 1 (32인 캐릭터) 필터 & 페이지 & 상세 인스펙터 상태
        self.char_country_filter: str = "ALL"
        self.char_page: int = 0
        self.inspected_character: str = self.game_mgr.selected_character

        # 탭 2 (9개국 월드투어 챕터 / 36종 글로벌 기구) 페이지 상태
        self.chapter_page: int = 0
        self.global_station_page: int = 0

        # 상단 네비게이션 버튼 Rect
        self.back_btn_rect: pygame.Rect = pygame.Rect(28, 16, 122, 42)
        self.mode_toggle_rect: pygame.Rect = pygame.Rect(158, 16, 224, 42)
        self.options_btn_rect: pygame.Rect = pygame.Rect(390, 16, 104, 42)

        # 4개 탭 버튼 Rect
        self.tab_rects: Dict[str, pygame.Rect] = {
            "character": pygame.Rect(28, 72, 294, 48),
            "chapter": pygame.Rect(334, 72, 314, 48),
            "upgrade": pygame.Rect(660, 72, 294, 48),
            "tournament": pygame.Rect(966, 72, 286, 48),
        }

        # 우측 하단 영업 시작 버튼 Rect
        self.start_day_btn_rect: pygame.Rect = pygame.Rect(900, 642, 352, 60)

        # 동적 클릭 판정 리스트: (rect, action_type, payload)
        self._click_targets: List[Tuple[pygame.Rect, str, Any]] = []
        self._hover_pos: Tuple[int, int] = (0, 0)
        self._sync_chapter_page_to_current()
        self._rebuild_click_targets()

    def _sync_chapter_page_to_current(self) -> None:
        if self.game_mgr.current_chapter in CHAPTER_ORDER:
            idx = CHAPTER_ORDER.index(self.game_mgr.current_chapter)
            self.chapter_page = idx // 4

    def on_enter(self, **kwargs: Any) -> None:
        if "initial_tab" in kwargs:
            tab = str(kwargs["initial_tab"]).lower()
            if tab in ("character", "chapter", "upgrade", "tournament"):
                self.active_tab = tab
        self.inspected_character = self.game_mgr.selected_character
        self._sync_chapter_page_to_current()
        self._rebuild_click_targets()

    def _get_filtered_characters(self) -> List[str]:
        return [str(c["id"]) if isinstance(c, dict) else str(c) for c in get_characters_by_country(self.char_country_filter)]

    def _get_current_tournament_opponent(self) -> str:
        rnd_idx = min(4, max(0, int(getattr(self.game_mgr, "tournament_round_idx", 0))))
        target_tier = rnd_idx + 1
        candidates = [
            cid
            for cid, c in TOURNAMENT_32_ROSTER.items()
            if int(c.get("tier", 1)) == target_tier and cid != self.game_mgr.selected_character
        ]
        if not candidates:
            candidates = [cid for cid in CHARACTER_ORDER if cid != self.game_mgr.selected_character]
        pick_idx = (self.game_mgr.day + rnd_idx * 3) % len(candidates)
        return candidates[pick_idx]

    def _rebuild_click_targets(self) -> None:
        """draw() 호출 전이라도 클릭 이벤트가 즉시 동작하도록 현재 탭의 클릭 영역을 사전 구성한다."""
        self._click_targets.clear()
        area = pygame.Rect(28, 126, 1224, 504)

        if self.active_tab == "character":
            # 국가 필터 탭 버튼 (10개)
            fx = area.x + 18
            fy = area.y + 12
            for f_code in COUNTRY_FILTER_ORDER:
                cnt = len(get_characters_by_country(f_code))
                lbl = COUNTRY_LABELS.get(f_code, f"{f_code} ({cnt})")
                fw = max(76, len(lbl) * 12 + 18)
                frect = pygame.Rect(fx, fy, fw, 30)
                self._click_targets.append((frect, "filter_char_country", f_code))
                fx += fw + 6

            filtered = self._get_filtered_characters()
            per_page = 6
            total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
            self.char_page = max(0, min(self.char_page, total_pages - 1))
            page_items = filtered[self.char_page * per_page : (self.char_page + 1) * per_page]

            if total_pages > 1:
                prev_r = pygame.Rect(area.x + 620, area.y + 462, 68, 30)
                next_r = pygame.Rect(area.x + 754, area.y + 462, 68, 30)
                self._click_targets.append((prev_r, "char_page_delta", -1))
                self._click_targets.append((next_r, "char_page_delta", 1))

            card_w, card_h, gap_x, gap_y = 258, 196, 14, 12
            start_x, start_y = area.x + 18, area.y + 52
            for idx, cid in enumerate(page_items):
                col = idx % 3
                row = idx // 3
                crect = pygame.Rect(start_x + col * (card_w + gap_x), start_y + row * (card_h + gap_y), card_w, card_h)
                btn_rect = pygame.Rect(crect.x + 10, crect.bottom - 38, crect.width - 20, 30)
                unlocked = self.game_mgr.is_character_unlocked(cid)
                selected = self.game_mgr.selected_character == cid
                if unlocked and not selected:
                    self._click_targets.append((btn_rect, "select_character", cid))
                elif not unlocked:
                    self._click_targets.append((btn_rect, "unlock_character", cid))
                self._click_targets.append((crect, "inspect_character", cid))

            # 우측 인스펙터 하단 액션 버튼
            insp_id = self.inspected_character if self.inspected_character in CHARACTERS else self.game_mgr.selected_character
            insp_btn = pygame.Rect(area.x + 836, area.bottom - 62, 368, 44)
            if self.game_mgr.is_character_unlocked(insp_id):
                if self.game_mgr.selected_character != insp_id:
                    self._click_targets.append((insp_btn, "select_character", insp_id))
            else:
                self._click_targets.append((insp_btn, "unlock_character", insp_id))

        elif self.active_tab == "chapter":
            if self.game_mgr.mode == "GLOBAL_ENDLESS":
                prev_r = pygame.Rect(area.right - 220, area.y + 12, 82, 30)
                next_r = pygame.Rect(area.right - 102, area.y + 12, 82, 30)
                self._click_targets.append((prev_r, "global_page_delta", -1))
                self._click_targets.append((next_r, "global_page_delta", 1))

                col_w, col_h, gap = 282, 434, 18
                start_x, col_y = area.x + 22, area.y + 50
                item_h = 90
                per_page = 4
                for s_idx, slot_type in enumerate(SLOT_TYPES):
                    col_rect = pygame.Rect(start_x + s_idx * (col_w + gap), col_y, col_w, col_h)
                    stations = get_stations_by_slot(slot_type)
                    total_pages = max(1, (len(stations) + per_page - 1) // per_page)
                    pg = max(0, min(self.global_station_page, total_pages - 1))
                    vis_stations = stations[pg * per_page : (pg + 1) * per_page]
                    for i_idx, st_meta in enumerate(vis_stations):
                        irect = pygame.Rect(
                            col_rect.x + 10,
                            col_rect.y + 50 + i_idx * (item_h + 7),
                            col_rect.width - 20,
                            item_h,
                        )
                        self._click_targets.append((irect, "set_global_station", (slot_type, st_meta["id"])))
            else:
                prev_r = pygame.Rect(area.right - 220, area.y + 12, 82, 30)
                next_r = pygame.Rect(area.right - 102, area.y + 12, 82, 30)
                self._click_targets.append((prev_r, "chapter_page_delta", -1))
                self._click_targets.append((next_r, "chapter_page_delta", 1))

                per_page = 4
                total_pages = max(1, (len(CHAPTER_ORDER) + per_page - 1) // per_page)
                self.chapter_page = max(0, min(self.chapter_page, total_pages - 1))
                vis_chapters = CHAPTER_ORDER[self.chapter_page * per_page : (self.chapter_page + 1) * per_page]

                card_w, card_h, gap = 282, 434, 18
                start_x, card_y = area.x + 22, area.y + 52
                for idx, ch_id in enumerate(vis_chapters):
                    crect = pygame.Rect(start_x + idx * (card_w + gap), card_y, card_w, card_h)
                    btn_rect = pygame.Rect(crect.x + 14, crect.bottom - 52, crect.width - 28, 40)
                    unlocked = self.game_mgr.is_chapter_unlocked(ch_id)
                    selected = (self.game_mgr.current_chapter == ch_id) and (self.game_mgr.mode == "WORLD_TOUR")
                    if unlocked and not selected:
                        self._click_targets.append((btn_rect, "select_chapter", ch_id))
                    elif not unlocked:
                        self._click_targets.append((btn_rect, "unlock_chapter", ch_id))

        elif self.active_tab == "upgrade":
            left_x = area.x + 20
            row_w, row_h = 595, 82
            for idx, up_key in enumerate(STATION_UPGRADE_ORDER):
                rrect = pygame.Rect(left_x, area.y + 48 + idx * (row_h + 7), row_w, row_h)
                btn_rect = pygame.Rect(rrect.right - 148, rrect.centery - 22, 134, 44)
                if self.game_mgr.get_station_upgrade_cost(up_key) is not None:
                    self._click_targets.append((btn_rect, "upgrade_station", up_key))
            right_x = area.x + 632
            i_row_w, i_row_h = 572, 104
            for idx, in_key in enumerate(INTERIOR_UPGRADE_ORDER):
                irect = pygame.Rect(right_x, area.y + 48 + idx * (i_row_h + 9), i_row_w, i_row_h)
                btn_rect = pygame.Rect(irect.right - 146, irect.centery - 22, 132, 44)
                if self.game_mgr.get_interior_upgrade_cost(in_key) is not None:
                    self._click_targets.append((btn_rect, "upgrade_interior", in_key))

        elif self.active_tab == "tournament":
            match_btn = pygame.Rect(area.x + 22, area.bottom - 62, 560, 46)
            self._click_targets.append((match_btn, "start_tournament_match", self._get_current_tournament_opponent()))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            swipe_start = getattr(self, "_swipe_start_pos", None)
            self._swipe_start_pos = None
            if swipe_start is not None:
                dx = event.pos[0] - swipe_start[0]
                dy = event.pos[1] - swipe_start[1]
                if abs(dx) >= 55 and abs(dx) > abs(dy) * 1.3 and 126 <= swipe_start[1] <= 630:
                    delta = -1 if dx > 0 else 1
                    if self.active_tab == "character":
                        self._handle_action("char_page_delta", delta, (640, 360))
                        self._rebuild_click_targets()
                        return
                    elif self.active_tab == "chapter":
                        act = "global_page_delta" if self.game_mgr.mode == "GLOBAL_ENDLESS" else "chapter_page_delta"
                        self._handle_action(act, delta, (640, 360))
                        self._rebuild_click_targets()
                        return

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            self._swipe_start_pos = (mx, my)

            # 1) 좌측 상단 타이틀로 돌아가기
            if self.back_btn_rect.inflate(6, 6).collidepoint(mx, my):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title")
                return

            # 1-B) 옵션 설정 버튼
            if self.options_btn_rect.inflate(6, 6).collidepoint(mx, my):
                if self.scene_mgr:
                    self.scene_mgr.open_options()
                return

            # 2) 모드 전환 토글 버튼 (월드 투어 <-> 글로벌 야시장)
            if self.mode_toggle_rect.inflate(6, 6).collidepoint(mx, my):
                sound_fx.play_click()
                new_mode = "GLOBAL_ENDLESS" if self.game_mgr.mode == "WORLD_TOUR" else "WORLD_TOUR"
                self.game_mgr.set_mode(new_mode)
                self._rebuild_click_targets()
                self.particles.spawn_floating_text(
                    "글로벌 야시장 통합 모드 전환!" if new_mode == "GLOBAL_ENDLESS" else "월드 투어 모드 전환!",
                    self.mode_toggle_rect.centerx,
                    self.mode_toggle_rect.bottom + 10,
                    color=config.NEON_CYAN if new_mode == "GLOBAL_ENDLESS" else config.POCHA_ORANGE,
                    size=18,
                )
                return

            # 3) 상단 4개 탭 전환
            for tab_key, trect in self.tab_rects.items():
                if trect.inflate(4, 6).collidepoint(mx, my):
                    if self.active_tab != tab_key:
                        sound_fx.play_click()
                        self.active_tab = tab_key
                        self._rebuild_click_targets()
                    return

            # 4) 우측 하단 [오늘 영업 시작! (START DAY)] 버튼
            if self.start_day_btn_rect.inflate(6, 6).collidepoint(mx, my):
                sound_fx.play_fanfare()
                self.game_mgr.ai_opponent_id = ""
                self.game_mgr.save_game()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("play", show_cutscene=True)
                return

            # 5) 탭 내부 동적 버튼 처리 (모바일 터치 여유 판정)
            if not self._click_targets:
                self._rebuild_click_targets()
            for rect, action_type, payload in list(self._click_targets):
                if rect.inflate(4, 4).collidepoint(mx, my):
                    self._handle_action(action_type, payload, rect.center)
                    self._rebuild_click_targets()
                    return

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title")
            elif event.key == pygame.K_RETURN:
                sound_fx.play_fanfare()
                self.game_mgr.ai_opponent_id = ""
                self.game_mgr.save_game()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("play", show_cutscene=True)
            elif event.key == pygame.K_TAB:
                sound_fx.play_click()
                order = ["character", "chapter", "upgrade", "tournament"]
                idx = (order.index(self.active_tab) + 1) % len(order)
                self.active_tab = order[idx]
                self._rebuild_click_targets()
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                delta = -1 if event.key == pygame.K_LEFT else 1
                if self.active_tab == "character":
                    self._handle_action("char_page_delta", delta, (640, 360))
                elif self.active_tab == "chapter":
                    act = "global_page_delta" if self.game_mgr.mode == "GLOBAL_ENDLESS" else "chapter_page_delta"
                    self._handle_action(act, delta, (640, 360))

    def _handle_action(self, action_type: str, payload: Any, center_pos: Tuple[int, int]) -> None:
        cx, cy = center_pos

        if action_type == "filter_char_country":
            sound_fx.play_click()
            self.char_country_filter = str(payload)
            self.char_page = 0
            filtered = self._get_filtered_characters()
            if filtered and self.inspected_character not in filtered:
                self.inspected_character = filtered[0]

        elif action_type == "char_page_delta":
            sound_fx.play_click()
            filtered = self._get_filtered_characters()
            total_pages = max(1, (len(filtered) + 5) // 6)
            self.char_page = (self.char_page + int(payload)) % total_pages

        elif action_type == "inspect_character":
            cid = str(payload)
            if cid in CHARACTERS:
                sound_fx.play_click()
                self.inspected_character = cid

        elif action_type == "chapter_page_delta":
            sound_fx.play_click()
            total_pages = max(1, (len(CHAPTER_ORDER) + 3) // 4)
            self.chapter_page = (self.chapter_page + int(payload)) % total_pages

        elif action_type == "global_page_delta":
            sound_fx.play_click()
            total_pages = max(1, (len(CHAPTER_ORDER) + 3) // 4)
            self.global_station_page = (self.global_station_page + int(payload)) % total_pages

        elif action_type == "select_character":
            char_id = str(payload)
            self.inspected_character = char_id
            if self.game_mgr.select_character(char_id):
                sound_fx.play_click()
                self.game_mgr.save_game()
                cname = CHARACTERS[char_id]["name"]
                rname = CHARACTERS[char_id].get("region_name", "")
                self.particles.emit_stars(cx, cy, count=8)
                self.particles.spawn_floating_text(f"👨‍🍳 [{rname}] {cname} 출전 선택!", cx, cy - 15, color=config.TEXT_SUCCESS)

        elif action_type == "unlock_character":
            char_id = str(payload)
            self.inspected_character = char_id
            cdata = CHARACTERS[char_id]
            req_ch = cdata.get("unlock_chapter", "KR")
            if not self.game_mgr.is_chapter_unlocked(req_ch):
                sound_fx.play_burn()
                self.particles.spawn_floating_text(
                    f"먼저 [{req_ch}] 챕터를 해금해야 합니다!",
                    cx,
                    cy - 15,
                    color=config.TEXT_WARNING,
                    size=18,
                )
                return
            if self.game_mgr.unlock_character(char_id):
                self.game_mgr.select_character(char_id)
                self.game_mgr.save_game()
                sound_fx.play_fanfare()
                self.particles.emit_stars(cx, cy, count=14)
                self.particles.spawn_floating_text(
                    f"🎉 [{cdata.get('region_name', '')}] {cdata['name']} 영입 및 장착!",
                    cx,
                    cy - 20,
                    color=config.GOLD,
                    size=21,
                )
            else:
                sound_fx.play_burn()
                self.particles.spawn_floating_text("보유 골드가 부족합니다!", cx, cy - 15, color=config.TEXT_WARNING)

        elif action_type == "select_chapter":
            ch_id = str(payload)
            if self.game_mgr.select_chapter(ch_id):
                sound_fx.play_click()
                self.game_mgr.save_game()
                ch_name = CHAPTERS[ch_id]["name"]
                self.particles.emit_stars(cx, cy, count=8)
                self.particles.spawn_floating_text(f"🗺️ {ch_name} 선택!", cx, cy - 15, color=config.TEXT_SUCCESS)

        elif action_type == "unlock_chapter":
            ch_id = str(payload)
            ch_data = CHAPTERS[ch_id]
            prev_ch = ch_data.get("required_prev_chapter")
            if prev_ch and not self.game_mgr.is_chapter_unlocked(prev_ch):
                sound_fx.play_burn()
                self.particles.spawn_floating_text(
                    f"이전 챕터({prev_ch})를 먼저 해금하세요!",
                    cx,
                    cy - 15,
                    color=config.TEXT_WARNING,
                    size=18,
                )
                return
            if self.game_mgr.unlock_chapter(ch_id):
                self.game_mgr.select_chapter(ch_id)
                self.game_mgr.save_game()
                sound_fx.play_fanfare()
                self.particles.emit_stars(cx, cy, count=16)
                self.particles.spawn_floating_text(
                    f"🎊 {ch_data['name']} 해금 완료!",
                    cx,
                    cy - 20,
                    color=config.GOLD,
                    size=22,
                )
            else:
                sound_fx.play_burn()
                self.particles.spawn_floating_text("보유 골드가 부족합니다!", cx, cy - 15, color=config.TEXT_WARNING)

        elif action_type == "set_global_station":
            slot_type, station_id = payload
            if self.game_mgr.set_global_loadout(slot_type, station_id):
                sound_fx.play_click()
                self.game_mgr.save_game()
                st_name = STATIONS_CATALOG[station_id]["short_name"]
                self.particles.emit_stars(cx, cy, count=6)
                self.particles.spawn_floating_text(
                    f"🏮 [{st_name}] 장착!",
                    cx,
                    cy - 15,
                    color=config.NEON_CYAN,
                    size=19,
                )

        elif action_type == "upgrade_station":
            up_key = str(payload)
            curr_lvl = self.game_mgr.get_station_level(up_key)
            story_max = self.game_mgr.get_story_max_station_level(up_key)
            if curr_lvl >= story_max:
                sound_fx.play_burn()
                self.particles.spawn_floating_text(
                    "🔒 스토리 진행(다음 일차) 후 상위 강화가 해금됩니다!",
                    cx,
                    cy - 15,
                    color=config.TEXT_WARNING,
                    size=17,
                )
                return
            if self.game_mgr.upgrade_station(up_key):
                sound_fx.play_cash()
                self.game_mgr.save_game()
                lvl = self.game_mgr.get_station_level(up_key)
                up_name = STATION_UPGRADES[up_key]["short_name"]
                self.particles.emit_stars(cx, cy, count=12)
                self.particles.spawn_floating_text(
                    f"🛠️ {up_name} Lv.{lvl} 달성!",
                    cx,
                    cy - 18,
                    color=config.GOLD,
                    size=21,
                )
            else:
                sound_fx.play_burn()
                self.particles.spawn_floating_text("골드가 부족하거나 최대 레벨입니다!", cx, cy - 15, color=config.TEXT_WARNING, size=18)

        elif action_type == "upgrade_interior":
            in_key = str(payload)
            if not self.game_mgr.is_interior_unlocked_in_story(in_key):
                sound_fx.play_burn()
                self.particles.spawn_floating_text(
                    "🔒 스토리 진행(다음 일차) 후 인테리어가 해금됩니다!",
                    cx,
                    cy - 15,
                    color=config.TEXT_WARNING,
                    size=17,
                )
                return
            if self.game_mgr.upgrade_interior(in_key):
                sound_fx.play_cash()
                self.game_mgr.save_game()
                in_name = INTERIOR_UPGRADES[in_key]["short_name"]
                self.particles.emit_stars(cx, cy, count=12)
                self.particles.spawn_floating_text(
                    f"🏮 {in_name} 설치 완료!",
                    cx,
                    cy - 18,
                    color=config.TEXT_SUCCESS,
                    size=21,
                )
            else:
                sound_fx.play_burn()
                self.particles.spawn_floating_text("골드가 부족하거나 이미 설치되었습니다!", cx, cy - 15, color=config.TEXT_WARNING, size=18)

        elif action_type == "start_tournament_match":
            opp_id = str(payload)
            sound_fx.play_fanfare()
            self.game_mgr.ai_opponent_id = opp_id
            self.game_mgr.save_game()
            if self.scene_mgr:
                self.scene_mgr.change_scene("play", show_cutscene=False)

    def update(self, dt: float) -> None:
        self.time_tick += dt
        self.particles.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self._click_targets.clear()

        # 배경 그리기
        bg_country = self.game_mgr.current_chapter if self.game_mgr.mode == "WORLD_TOUR" else self.game_mgr.get_selected_character_data()["country"]
        art_renderer.draw_country_background(
            surface,
            (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            country_id=bg_country,
            interior_levels=self.game_mgr.interior_levels,
            time_tick=self.time_tick,
        )
        art_renderer.draw_alpha_overlay(
            surface,
            (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            (16, 14, 28, 212),
        )

        # 1. 상단 헤더 & 탭 바
        self._draw_top_bar(surface)
        self._draw_tabs(surface)

        # 2. 메인 컨텐츠 영역 (y=126 ~ 630)
        content_rect = pygame.Rect(28, 126, 1224, 504)
        pygame.draw.rect(surface, (28, 25, 42), content_rect, border_radius=16)
        pygame.draw.rect(surface, config.UI_BORDER, content_rect, width=2, border_radius=16)

        if self.active_tab == "character":
            self._draw_character_tab(surface, content_rect)
        elif self.active_tab == "chapter":
            if self.game_mgr.mode == "GLOBAL_ENDLESS":
                self._draw_global_loadout_tab(surface, content_rect)
            else:
                self._draw_world_tour_chapter_tab(surface, content_rect)
        elif self.active_tab == "tournament":
            self._draw_tournament_tab(surface, content_rect)
        else:
            self._draw_upgrade_tab(surface, content_rect)

        # 3. 하단 요약 바 & [오늘 영업 시작!] 버튼
        self._draw_bottom_summary(surface)

        # 4. 파티클 & 플로팅 텍스트
        self.particles.draw(surface)

    # ------------------------------------------------------------------
    # 상단 바 & 탭 렌더링 (포차스타 SNS 등급 배지 포함)
    # ------------------------------------------------------------------
    def _draw_top_bar(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos
        btn_f = config.get_font(15, bold=True)
        title_f = config.get_font(18, bold=True)
        gold_f = config.get_font(20, bold=True)
        xs_f = config.get_font(12, bold=True)

        # 타이틀로 버튼
        b_hov = self.back_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if b_hov else config.UI_PANEL,
            self.back_btn_rect,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.UI_BORDER, self.back_btn_rect, width=2, border_radius=10)
        b_txt = btn_f.render("⬅ 타이틀로", True, config.WHITE)
        surface.blit(b_txt, b_txt.get_rect(center=self.back_btn_rect.center))

        # 모드 토글 버튼
        m_hov = self.mode_toggle_rect.collidepoint(mx, my)
        is_global = self.game_mgr.mode == "GLOBAL_ENDLESS"
        m_col = config.NEON_CYAN if is_global else config.POCHA_ORANGE
        pygame.draw.rect(surface, (42, 38, 62) if not m_hov else (58, 52, 84), self.mode_toggle_rect, border_radius=10)
        pygame.draw.rect(surface, m_col, self.mode_toggle_rect, width=2, border_radius=10)
        m_label = "🏮 글로벌 통합 (⇄)" if is_global else "🗺️ 9개국 투어 (⇄)"
        m_txt = config.get_font(14, bold=True).render(m_label, True, m_col)
        surface.blit(m_txt, m_txt.get_rect(center=self.mode_toggle_rect.center))

        # 옵션 설정 버튼
        o_hov = self.options_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if o_hov else config.UI_PANEL,
            self.options_btn_rect,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.GOLD if o_hov else config.UI_BORDER, self.options_btn_rect, width=2, border_radius=10)
        o_txt = config.get_font(14, bold=True).render("⚙️ 옵션", True, config.GOLD if o_hov else config.WHITE)
        surface.blit(o_txt, o_txt.get_rect(center=self.options_btn_rect.center))

        # 중앙 씬 제목
        hdr_str = "포차 영업 준비 · 9개국 32인"
        hdr_surf = title_f.render(hdr_str, True, config.WHITE)
        surface.blit(hdr_surf, hdr_surf.get_rect(center=(612, 37)))

        # [데이브 더 다이버 '쿡스타' 감성] 포차스타(Pocha-sta) SNS 랭크 배지
        p_rank = self.game_mgr.get_pochasta_rank()
        sns_rect = pygame.Rect(732, 14, 246, 46)
        pygame.draw.rect(surface, (32, 28, 48), sns_rect, border_radius=11)
        pygame.draw.rect(surface, p_rank["badge_color"], sns_rect, width=2, border_radius=11)
        r_t1 = xs_f.render(f"📱 포차스타: {p_rank['tier']}", True, p_rank["badge_color"])
        r_t2 = xs_f.render(f"팔로워 {p_rank['followers']:,}명 · 해금 {len(self.game_mgr.unlocked_characters)}/32명", True, config.TEXT_PRIMARY)
        surface.blit(r_t1, (sns_rect.x + 12, sns_rect.y + 6))
        surface.blit(r_t2, (sns_rect.x + 12, sns_rect.y + 24))

        # 우측 보유 골드 패널
        gold_rect = pygame.Rect(988, 14, 264, 46)
        pygame.draw.rect(surface, (36, 30, 48), gold_rect, border_radius=12)
        pygame.draw.rect(surface, config.GOLD, gold_rect, width=2, border_radius=12)
        g_txt = gold_f.render(f"💰 {self.game_mgr.gold:,}원", True, config.GOLD)
        surface.blit(g_txt, g_txt.get_rect(center=gold_rect.center))

    def _draw_tabs(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos
        tab_f = config.get_font(15, bold=True)

        tab_labels = {
            "character": f"👨‍🍳 1. 32인 마스터 ({len(self.game_mgr.unlocked_characters)}/32)",
            "chapter": (
                "🏮 2. 글로벌 36종 기구 배치"
                if self.game_mgr.mode == "GLOBAL_ENDLESS"
                else f"🗺️ 2. 9개국 월드 투어 ({len(self.game_mgr.unlocked_chapters)}/9)"
            ),
            "upgrade": "🛠️ 3. 기구·인테리어 상점",
            "tournament": "🏆 4. 32강 월드 그랑프리",
        }

        for key, rect in self.tab_rects.items():
            is_active = self.active_tab == key
            is_hov = rect.collidepoint(mx, my)
            if is_active:
                bg = config.UI_BUTTON_ACTIVE
                border = config.GOLD
                fg = config.WHITE
            elif is_hov:
                bg = config.UI_BUTTON_HOVER
                border = config.UI_HIGHLIGHT
                fg = config.WHITE
            else:
                bg = config.UI_PANEL_DARK
                border = config.UI_BORDER
                fg = config.TEXT_SECONDARY

            pygame.draw.rect(surface, bg, rect, border_radius=12)
            pygame.draw.rect(surface, border, rect, width=2 if is_active else 1, border_radius=12)
            txt = tab_f.render(tab_labels[key], True, fg)
            surface.blit(txt, txt.get_rect(center=rect.center))

    # ------------------------------------------------------------------
    # 탭 1: 9개국 32인 지역별 마스터 선택 (국가 필터 + 3x2 그리드 + 우측 상세 쇼케이스)
    # ------------------------------------------------------------------
    def _draw_character_tab(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        mx, my = self._hover_pos
        sub_f = config.get_font(13, bold=True)
        xs_f = config.get_font(12, bold=False)
        card_name_f = config.get_font(16, bold=True)

        # 1) 상단 국가별 필터 바 (전체 32명 / 한국 1 / 대만 2 / 일본 3 / 멕시코 3 / 브라질 3 / 러시아 3 / 미국 5 / 인도 6 / 중국 6)
        fx = area.x + 18
        fy = area.y + 12
        for f_code in COUNTRY_FILTER_ORDER:
            cnt = len(get_characters_by_country(f_code))
            lbl = COUNTRY_LABELS.get(f_code, f"{f_code} ({cnt})")
            fw = max(76, sub_f.size(lbl)[0] + 20)
            frect = pygame.Rect(fx, fy, fw, 30)
            is_sel = self.char_country_filter == f_code
            is_hov = frect.collidepoint(mx, my)
            bg = (228, 108, 38) if is_sel else ((58, 52, 84) if is_hov else (38, 34, 56))
            border = config.GOLD if is_sel else config.UI_BORDER
            pygame.draw.rect(surface, bg, frect, border_radius=8)
            pygame.draw.rect(surface, border, frect, width=2 if is_sel else 1, border_radius=8)
            ftxt = sub_f.render(lbl, True, config.WHITE if is_sel else config.TEXT_PRIMARY)
            surface.blit(ftxt, ftxt.get_rect(center=frect.center))
            self._click_targets.append((frect, "filter_char_country", f_code))
            fx += fw + 6

        # 2) 좌측 3x2 지역별 마스터 카드 그리드 (최대 6개씩 깔끔하게 표시)
        filtered = self._get_filtered_characters()
        per_page = 6
        total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
        self.char_page = max(0, min(self.char_page, total_pages - 1))
        page_items = filtered[self.char_page * per_page : (self.char_page + 1) * per_page]

        card_w, card_h, gap_x, gap_y = 258, 196, 14, 12
        start_x, start_y = area.x + 18, area.y + 52

        for idx, cid in enumerate(page_items):
            cdata = CHARACTERS[cid]
            col = idx % 3
            row = idx // 3
            crect = pygame.Rect(start_x + col * (card_w + gap_x), start_y + row * (card_h + gap_y), card_w, card_h)
            unlocked = self.game_mgr.is_character_unlocked(cid)
            selected = self.game_mgr.selected_character == cid
            inspected = self.inspected_character == cid
            theme_col = cdata["theme_color"]

            bg_col = (52, 44, 78) if selected else ((44, 38, 66) if inspected else ((34, 30, 48) if unlocked else (22, 20, 32)))
            pygame.draw.rect(surface, bg_col, crect, border_radius=12)
            border_c = config.GOLD if selected else (config.NEON_CYAN if inspected else (theme_col if unlocked else config.UI_BORDER))
            pygame.draw.rect(surface, border_c, crect, width=3 if (selected or inspected) else 1, border_radius=12)

            # 국가·지역 배지
            reg_str = f"[{cdata['country']}] {cdata.get('region_name', cdata['country_name'])}"
            r_badge = pygame.Rect(crect.x + 10, crect.y + 8, min(148, xs_f.size(reg_str)[0] + 14), 22)
            pygame.draw.rect(surface, theme_col, r_badge, border_radius=6)
            rb_s = xs_f.render(reg_str, True, config.WHITE)
            surface.blit(rb_s, rb_s.get_rect(center=r_badge.center))

            # 시드 번호 또는 출전 배지
            tag_str = "★ 출전 중" if selected else f"#{cdata.get('seed_rank', 1)} 시드"
            tag_col = config.GOLD if selected else config.TEXT_SECONDARY
            tag_s = xs_f.render(tag_str, True, tag_col)
            surface.blit(tag_s, (crect.right - tag_s.get_width() - 10, crect.y + 10))

            # 좌측 도트 아바타 (68x68)
            av_rect = pygame.Rect(crect.x + 12, crect.y + 36, 68, 68)
            av_state = "SKILL" if selected else ("COOKING" if inspected and unlocked else ("IDLE" if unlocked else "LOCKED"))
            art_renderer.draw_chef_avatar(surface, av_rect, character_id=cid, state=av_state, time_tick=self.time_tick)

            # 우측 이름, 직함, 특기 메뉴
            nm_s = card_name_f.render(cdata["name"], True, config.WHITE if unlocked else config.TEXT_MUTED)
            tt_s = xs_f.render(cdata["title"][:15], True, cdata["accent_color"])
            sp_s = xs_f.render(f"특기: {cdata.get('specialty_tag', '')[:14]}", True, config.TEXT_PRIMARY)
            surface.blit(nm_s, (crect.x + 88, crect.y + 38))
            surface.blit(tt_s, (crect.x + 88, crect.y + 62))
            surface.blit(sp_s, (crect.x + 88, crect.y + 82))

            # 한 줄 스킬 요약
            sk_line = f"⚡ {cdata['skill_name']} (쿨 {int(cdata['cooldown'])}초)"
            sk_s = xs_f.render(sk_line, True, config.GOLD if unlocked else config.TEXT_SECONDARY)
            surface.blit(sk_s, (crect.x + 12, crect.y + 114))

            p_line = cdata["passive_desc"][:22] + ("..." if len(cdata["passive_desc"]) > 22 else "")
            p_s = xs_f.render(f"✦ {p_line}", True, config.NEON_GREEN if unlocked else config.TEXT_MUTED)
            surface.blit(p_s, (crect.x + 12, crect.y + 134))

            # 카드 하단 빠른 선택/영입 버튼
            btn_rect = pygame.Rect(crect.x + 10, crect.bottom - 36, crect.width - 20, 28)
            b_hov = btn_rect.collidepoint(mx, my)
            if unlocked:
                if selected:
                    pygame.draw.rect(surface, (46, 112, 68), btn_rect, border_radius=7)
                    b_lbl = sub_f.render("✔ 현재 출전 마스터", True, config.WHITE)
                else:
                    pygame.draw.rect(surface, config.UI_BUTTON_HOVER if b_hov else config.UI_BUTTON, btn_rect, border_radius=7)
                    pygame.draw.rect(surface, theme_col, btn_rect, width=1, border_radius=7)
                    b_lbl = sub_f.render("이 마스터 선택", True, config.WHITE)
                    self._click_targets.append((btn_rect, "select_character", cid))
            else:
                req_ch = cdata.get("unlock_chapter", "KR")
                cost = int(cdata.get("unlock_cost", 0))
                can_un = self.game_mgr.can_unlock_character(cid)
                pygame.draw.rect(surface, (212, 122, 32) if can_un else config.UI_DISABLED, btn_rect, border_radius=7)
                lbl_s = f"🔓 영입 ({cost:,}원)" if self.game_mgr.is_chapter_unlocked(req_ch) else f"🔒 [{req_ch}] 해금 필요"
                b_lbl = sub_f.render(lbl_s, True, config.WHITE if can_un else config.TEXT_SECONDARY)
                self._click_targets.append((btn_rect, "unlock_character", cid))
            surface.blit(b_lbl, b_lbl.get_rect(center=btn_rect.center))
            self._click_targets.append((crect, "inspect_character", cid))

        # 하단 좌측 안내 및 페이지네이션 컨트롤 (전체 32명 보기 시 활성화)
        hint_s = sub_f.render(
            f"💡 영토 면적·인구 비례 9개국 32인 지역 마스터 로스터  |  현재 필터: {COUNTRY_LABELS.get(self.char_country_filter, '전체')}",
            True,
            config.TEXT_SECONDARY,
        )
        surface.blit(hint_s, (area.x + 20, area.y + 467))

        if total_pages > 1:
            prev_r = pygame.Rect(area.x + 612, area.y + 460, 72, 32)
            next_r = pygame.Rect(area.x + 750, area.y + 460, 72, 32)
            for r_btn, lbl_t, d_val in ((prev_r, "◀ 이전", -1), (next_r, "다음 ▶", 1)):
                bh = r_btn.collidepoint(mx, my)
                pygame.draw.rect(surface, (62, 54, 92) if bh else (42, 36, 64), r_btn, border_radius=8)
                pygame.draw.rect(surface, config.GOLD, r_btn, width=1, border_radius=8)
                bs = sub_f.render(lbl_t, True, config.WHITE)
                surface.blit(bs, bs.get_rect(center=r_btn.center))
                self._click_targets.append((r_btn, "char_page_delta", d_val))
            pg_s = sub_f.render(f"{self.char_page + 1} / {total_pages}", True, config.GOLD)
            surface.blit(pg_s, pg_s.get_rect(center=(area.x + 717, area.y + 476)))

        # 3) 우측: 선택/포커스된 마스터 대형 일러스트 & 상세 도감 패널 (x = area.x + 830)
        insp_id = self.inspected_character if self.inspected_character in CHARACTERS else self.game_mgr.selected_character
        ic = CHARACTERS[insp_id]
        insp_rect = pygame.Rect(area.x + 824, area.y + 52, 382, 440)
        pygame.draw.rect(surface, (22, 19, 34), insp_rect, border_radius=14)
        pygame.draw.rect(surface, ic["theme_color"], insp_rect, width=2, border_radius=14)

        # 상단 야시장 미니 배경 + 대형 118x118 도트 일러스트 초상화
        bg_banner = pygame.Rect(insp_rect.x + 12, insp_rect.y + 12, insp_rect.width - 24, 134)
        art_renderer.draw_country_background(surface, bg_banner, country_id=ic["country"], time_tick=self.time_tick)
        art_renderer.draw_alpha_overlay(surface, bg_banner, (12, 10, 22, 110), border_radius=10)
        pygame.draw.rect(surface, ic["accent_color"], bg_banner, width=2, border_radius=10)

        big_av = pygame.Rect(bg_banner.x + 12, bg_banner.y + 8, 118, 118)
        i_unlocked = self.game_mgr.is_character_unlocked(insp_id)
        art_renderer.draw_chef_avatar(
            surface,
            big_av,
            character_id=insp_id,
            state="SKILL" if i_unlocked else "LOCKED",
            time_tick=self.time_tick,
        )

        # 우측 상단 프로필 텍스트
        big_name_f = config.get_font(22, bold=True)
        surface.blit(
            sub_f.render(f"{ic['country_name']} · {ic.get('region_name', '')}", True, ic["accent_color"]),
            (big_av.right + 14, bg_banner.y + 14),
        )
        surface.blit(
            big_name_f.render(ic["name"], True, config.WHITE),
            (big_av.right + 14, bg_banner.y + 38),
        )
        surface.blit(
            sub_f.render(ic["title"], True, config.GOLD),
            (big_av.right + 14, bg_banner.y + 70),
        )
        surface.blit(
            xs_f.render(f"대표 요리: {ic.get('specialty_tag', '')}", True, config.NEON_CYAN),
            (big_av.right + 14, bg_banner.y + 96),
        )

        # 캐릭터 대사(Quote) 박스
        q_box = pygame.Rect(insp_rect.x + 12, insp_rect.y + 154, insp_rect.width - 24, 48)
        pygame.draw.rect(surface, (32, 28, 48), q_box, border_radius=8)
        quote_str = f"💬 \"{ic.get('quote', ic.get('description', ''))}\""
        self._draw_wrapped_text(surface, quote_str, xs_f, (235, 228, 250), q_box.x + 10, q_box.y + 7, q_box.width - 20, line_spacing=17)

        # 고유 패시브 상세 박스
        p_box = pygame.Rect(insp_rect.x + 12, insp_rect.y + 210, insp_rect.width - 24, 74)
        pygame.draw.rect(surface, (28, 24, 42), p_box, border_radius=8)
        pygame.draw.rect(surface, (72, 168, 112), p_box, width=1, border_radius=8)
        surface.blit(sub_f.render("✦ 지역 마스터 고유 패시브", True, config.NEON_GREEN), (p_box.x + 10, p_box.y + 7))
        self._draw_wrapped_text(surface, ic["passive_desc"], xs_f, config.TEXT_PRIMARY, p_box.x + 10, p_box.y + 30, p_box.width - 20)

        # 액티브 스킬 상세 박스
        s_box = pygame.Rect(insp_rect.x + 12, insp_rect.y + 292, insp_rect.width - 24, 82)
        pygame.draw.rect(surface, (28, 24, 42), s_box, border_radius=8)
        pygame.draw.rect(surface, (188, 148, 56), s_box, width=1, border_radius=8)
        surface.blit(
            sub_f.render(f"⚡ [SPACE] {ic['skill_name']} (쿨타임 {int(ic['cooldown'])}초)", True, config.GOLD),
            (s_box.x + 10, s_box.y + 7),
        )
        self._draw_wrapped_text(surface, ic["skill_desc"], xs_f, config.TEXT_PRIMARY, s_box.x + 10, s_box.y + 30, s_box.width - 20)

        # 하단 대형 선택/영입 버튼
        insp_btn = pygame.Rect(insp_rect.x + 12, insp_rect.bottom - 54, insp_rect.width - 24, 42)
        ib_hov = insp_btn.collidepoint(mx, my)
        if i_unlocked:
            if self.game_mgr.selected_character == insp_id:
                pygame.draw.rect(surface, (46, 118, 72), insp_btn, border_radius=10)
                pygame.draw.rect(surface, config.TEXT_SUCCESS, insp_btn, width=2, border_radius=10)
                ib_lbl = sub_f.render("✔ 현재 출전 중인 포차 마스터", True, config.WHITE)
            else:
                pygame.draw.rect(surface, config.UI_BUTTON_HOVER if ib_hov else config.UI_BUTTON, insp_btn, border_radius=10)
                pygame.draw.rect(surface, config.GOLD, insp_btn, width=2, border_radius=10)
                ib_lbl = sub_f.render(f"👨‍🍳 [{ic.get('region_name', '')}] {ic['name']} 출전하기", True, config.WHITE)
                self._click_targets.append((insp_btn, "select_character", insp_id))
        else:
            req_ch = ic.get("unlock_chapter", "KR")
            cost = int(ic.get("unlock_cost", 0))
            can_un = self.game_mgr.can_unlock_character(insp_id)
            pygame.draw.rect(surface, (218, 128, 32) if can_un else config.UI_DISABLED, insp_btn, border_radius=10)
            pygame.draw.rect(surface, config.GOLD if can_un else config.UI_BORDER, insp_btn, width=2, border_radius=10)
            lbl_s = f"🔓 마스터 영입하기 ({cost:,}원)" if self.game_mgr.is_chapter_unlocked(req_ch) else f"🔒 [{req_ch}] 챕터 해금 후 영입 가능 ({cost:,}원)"
            ib_lbl = sub_f.render(lbl_s, True, config.WHITE if can_un else config.TEXT_SECONDARY)
            self._click_targets.append((insp_btn, "unlock_character", insp_id))
        surface.blit(ib_lbl, ib_lbl.get_rect(center=insp_btn.center))

    # ------------------------------------------------------------------
    # 탭 2-A: 9개국 월드 투어 챕터 선택 & 해금 (4카드 페이지네이션 + 오늘의 축제 배너)
    # ------------------------------------------------------------------
    def _draw_world_tour_chapter_tab(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        mx, my = self._hover_pos
        title_f = config.get_font(17, bold=True)
        name_f = config.get_font(20, bold=True)
        sub_f = config.get_font(13, bold=True)
        body_f = config.get_font(12, bold=False)

        prog = self.game_mgr.get_story_progression()
        fest = self.game_mgr.get_daily_festival_info()
        unlock_banner = str(prog.get("unlock_banner", ""))
        guide = title_f.render(
            f"🗺️ {unlock_banner}   |   {fest['title']} ({fest['bonus_desc']})",
            True,
            config.TEXT_GOLD,
        )
        surface.blit(guide, (area.x + 22, area.y + 15))

        # 우측 상단 대륙/챕터 페이지 전환 버튼 (1/3 ~ 3/3)
        per_page = 4
        total_pages = max(1, (len(CHAPTER_ORDER) + per_page - 1) // per_page)
        self.chapter_page = max(0, min(self.chapter_page, total_pages - 1))
        vis_chapters = CHAPTER_ORDER[self.chapter_page * per_page : (self.chapter_page + 1) * per_page]

        prev_r = pygame.Rect(area.right - 236, area.y + 10, 78, 32)
        next_r = pygame.Rect(area.right - 98, area.y + 10, 78, 32)
        for r_btn, lbl_t, d_val in ((prev_r, "◀ 이전", -1), (next_r, "다음 ▶", 1)):
            bh = r_btn.collidepoint(mx, my)
            pygame.draw.rect(surface, (62, 54, 92) if bh else (42, 36, 64), r_btn, border_radius=8)
            pygame.draw.rect(surface, config.GOLD, r_btn, width=1, border_radius=8)
            bs = sub_f.render(lbl_t, True, config.WHITE)
            surface.blit(bs, bs.get_rect(center=r_btn.center))
            self._click_targets.append((r_btn, "chapter_page_delta", d_val))
        pg_s = sub_f.render(f"{self.chapter_page + 1}/{total_pages}", True, config.GOLD)
        surface.blit(pg_s, pg_s.get_rect(center=(area.right - 128, area.y + 26)))

        card_w = 282
        card_h = 434
        gap = 18
        start_x = area.x + 22
        card_y = area.y + 52

        for idx, ch_id in enumerate(vis_chapters):
            ch_data = CHAPTERS[ch_id]
            crect = pygame.Rect(start_x + idx * (card_w + gap), card_y, card_w, card_h)
            unlocked = self.game_mgr.is_chapter_unlocked(ch_id)
            selected = (self.game_mgr.current_chapter == ch_id) and (self.game_mgr.mode == "WORLD_TOUR")
            theme_col = ch_data["theme_color"]

            bg_col = (46, 40, 68) if selected else ((36, 32, 52) if unlocked else (24, 22, 34))
            pygame.draw.rect(surface, bg_col, crect, border_radius=14)
            pygame.draw.rect(
                surface,
                config.GOLD if selected else (theme_col if unlocked else config.UI_BORDER),
                crect,
                width=3 if selected else 2,
                border_radius=14,
            )

            # 미니 야시장 배경 프리뷰
            preview_rect = pygame.Rect(crect.x + 12, crect.y + 12, crect.width - 24, 110)
            art_renderer.draw_country_background(surface, preview_rect, country_id=ch_id, time_tick=self.time_tick)
            pygame.draw.rect(surface, theme_col, preview_rect, width=2, border_radius=8)

            # 별점 표시 & 해당 국가 마스터 수 배지
            stars = self.game_mgr.chapter_stars.get(ch_id, 0)
            star_str = "★" * stars + "☆" * (3 - stars)
            star_badge = pygame.Rect(preview_rect.right - 74, preview_rect.y + 6, 68, 24)
            pygame.draw.rect(surface, (20, 16, 30), star_badge, border_radius=6)
            st_surf = sub_f.render(star_str, True, config.GOLD)
            surface.blit(st_surf, st_surf.get_rect(center=star_badge.center))

            chef_cnt = len(get_characters_by_country(ch_id))
            cnt_badge = pygame.Rect(preview_rect.x + 6, preview_rect.y + 6, 94, 24)
            pygame.draw.rect(surface, (20, 16, 30), cnt_badge, border_radius=6)
            cb_surf = body_f.render(f"👨‍🍳 마스터 {chef_cnt}명", True, config.NEON_CYAN)
            surface.blit(cb_surf, cb_surf.get_rect(center=cnt_badge.center))

            # 챕터명 & 부제
            ch_title_str = f"[{ch_id}] {ch_data['name']}"
            active_name_f = name_f
            max_ch_w = crect.width - 28
            for f_sz in (18, 16, 15, 14):
                if active_name_f.size(ch_title_str)[0] <= max_ch_w:
                    break
                active_name_f = config.get_font(f_sz, bold=True)
            nm = active_name_f.render(ch_title_str, True, config.WHITE if unlocked else config.TEXT_MUTED)
            sub_str = str(ch_data["subtitle"])
            active_sub_f = body_f
            if active_sub_f.size(sub_str)[0] > max_ch_w:
                active_sub_f = config.get_font(11, bold=False)
                while len(sub_str) > 10 and active_sub_f.size(sub_str)[0] > max_ch_w:
                    sub_str = sub_str[:-2] + "…"
            sb = active_sub_f.render(sub_str, True, ch_data["accent_color"])
            surface.blit(nm, (crect.x + 14, crect.y + 130))
            surface.blit(sb, (crect.x + 14, crect.y + 158))

            # 일차 & 목표 매출 정보
            ch_day = self.game_mgr.chapter_days.get(ch_id, 1)
            target_gold = ch_data["base_target_gold"] + (ch_day - 1) * ch_data["daily_target_growth"]
            info_s = sub_f.render(f"📅 Day {ch_day}  |  🎯 목표: {target_gold:,}원", True, config.NEON_CYAN)
            surface.blit(info_s, (crect.x + 14, crect.y + 182))

            # 챕터 전용 조리 기구 4종 목록 박스
            st_box = pygame.Rect(crect.x + 12, crect.y + 210, crect.width - 24, 154)
            pygame.draw.rect(surface, (22, 19, 34), st_box, border_radius=10)
            pygame.draw.rect(surface, (68, 62, 92), st_box, width=1, border_radius=10)

            for s_idx, st_id in enumerate(ch_data["stations"]):
                st_meta = STATIONS_CATALOG[st_id]
                ry = st_box.y + 10 + s_idx * 35
                first_rec = st_meta["recipes"][0] if st_meta["recipes"] else "bungeoppang_redbean"
                slot_type = str(st_meta["slot_type"])
                slot_open = True
                if selected and self.game_mgr.mode == "WORLD_TOUR":
                    slot_open = self.game_mgr.is_slot_unlocked_in_story(slot_type, day=ch_day)
                art_renderer.draw_food_icon(surface, (st_box.x + 24, ry + 14), first_rec, size=28)
                label_prefix = "" if slot_open else "🔒 "
                st_txt = body_f.render(
                    f"{label_prefix}{st_meta['name']}",
                    True,
                    config.TEXT_PRIMARY if slot_open else config.TEXT_SECONDARY,
                )
                surface.blit(st_txt, (st_box.x + 44, ry + 5))

            # 하단 선택 / 해금 버튼
            btn_rect = pygame.Rect(crect.x + 14, crect.bottom - 52, crect.width - 28, 40)
            is_hov = btn_rect.collidepoint(mx, my)

            if unlocked:
                if selected:
                    pygame.draw.rect(surface, (52, 118, 72), btn_rect, border_radius=10)
                    pygame.draw.rect(surface, config.TEXT_SUCCESS, btn_rect, width=2, border_radius=10)
                    b_lbl = sub_f.render("✔ 현재 영업 지역", True, config.WHITE)
                else:
                    pygame.draw.rect(surface, config.UI_BUTTON_HOVER if is_hov else config.UI_BUTTON, btn_rect, border_radius=10)
                    pygame.draw.rect(surface, config.WHITE if is_hov else theme_col, btn_rect, width=2, border_radius=10)
                    b_lbl = sub_f.render("이 챕터에서 영업하기", True, config.WHITE)
                    self._click_targets.append((btn_rect, "select_chapter", ch_id))
            else:
                cost = int(ch_data.get("unlock_cost", 0))
                prev_ch = ch_data.get("required_prev_chapter")
                can_unlock = self.game_mgr.can_unlock_chapter(ch_id)
                btn_col = (218, 128, 32) if can_unlock else config.UI_DISABLED
                pygame.draw.rect(surface, btn_col, btn_rect, border_radius=10)
                pygame.draw.rect(surface, config.GOLD if can_unlock else config.UI_BORDER, btn_rect, width=2, border_radius=10)
                if prev_ch and not self.game_mgr.is_chapter_unlocked(prev_ch):
                    lbl_str = f"🔒 {prev_ch} 해금 필요 ({cost:,}원)"
                else:
                    lbl_str = f"🔓 챕터 해금 ({cost:,}원)"
                b_lbl = sub_f.render(lbl_str, True, config.WHITE if can_unlock else config.TEXT_SECONDARY)
                self._click_targets.append((btn_rect, "unlock_chapter", ch_id))

            surface.blit(b_lbl, b_lbl.get_rect(center=btn_rect.center))

    # ------------------------------------------------------------------
    # 탭 2-B: 글로벌 야시장 모드 — 4슬롯 × 9개국(36종) 조리 기구 커스텀 배치
    # ------------------------------------------------------------------
    def _draw_global_loadout_tab(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        mx, my = self._hover_pos
        title_f = config.get_font(17, bold=True)
        slot_f = config.get_font(15, bold=True)
        card_f = config.get_font(14, bold=True)
        small_f = config.get_font(12, bold=False)
        sub_f = config.get_font(13, bold=True)

        guide = title_f.render(
            "🏮 글로벌 야시장 36종 커스텀 포차 — 4개 조리 구역마다 9개국 기구 중 원하는 기구를 자유 장착하세요!",
            True,
            config.NEON_CYAN,
        )
        surface.blit(guide, (area.x + 22, area.y + 15))

        per_page = 4
        total_pages = max(1, (len(CHAPTER_ORDER) + per_page - 1) // per_page)
        self.global_station_page = max(0, min(self.global_station_page, total_pages - 1))

        prev_r = pygame.Rect(area.right - 236, area.y + 10, 78, 32)
        next_r = pygame.Rect(area.right - 98, area.y + 10, 78, 32)
        for r_btn, lbl_t, d_val in ((prev_r, "◀ 이전", -1), (next_r, "다음 ▶", 1)):
            bh = r_btn.collidepoint(mx, my)
            pygame.draw.rect(surface, (62, 54, 92) if bh else (42, 36, 64), r_btn, border_radius=8)
            pygame.draw.rect(surface, config.NEON_CYAN, r_btn, width=1, border_radius=8)
            bs = sub_f.render(lbl_t, True, config.WHITE)
            surface.blit(bs, bs.get_rect(center=r_btn.center))
            self._click_targets.append((r_btn, "global_page_delta", d_val))
        pg_s = sub_f.render(f"{self.global_station_page + 1}/{total_pages}", True, config.NEON_CYAN)
        surface.blit(pg_s, pg_s.get_rect(center=(area.right - 128, area.y + 26)))

        col_w = 282
        col_h = 434
        gap = 18
        start_x = area.x + 22
        col_y = area.y + 50

        for s_idx, slot_type in enumerate(SLOT_TYPES):
            col_rect = pygame.Rect(start_x + s_idx * (col_w + gap), col_y, col_w, col_h)
            pygame.draw.rect(surface, (22, 19, 34), col_rect, border_radius=14)
            pygame.draw.rect(surface, config.UI_BORDER, col_rect, width=1, border_radius=14)

            hdr_rect = pygame.Rect(col_rect.x + 8, col_rect.y + 8, col_rect.width - 16, 34)
            pygame.draw.rect(surface, (44, 38, 66), hdr_rect, border_radius=8)
            h_txt = slot_f.render(SLOT_KOR_NAMES[slot_type], True, config.GOLD)
            surface.blit(h_txt, h_txt.get_rect(center=hdr_rect.center))

            all_stations = get_stations_by_slot(slot_type)
            vis_stations = all_stations[self.global_station_page * per_page : (self.global_station_page + 1) * per_page]
            equipped_id = self.game_mgr.global_loadout.get(slot_type)

            item_h = 90
            for i_idx, st_meta in enumerate(vis_stations):
                st_id = st_meta["id"]
                irect = pygame.Rect(col_rect.x + 10, col_rect.y + 50 + i_idx * (item_h + 7), col_rect.width - 20, item_h)
                is_eq = st_id == equipped_id
                is_hov = irect.collidepoint(mx, my)

                bg = (52, 46, 80) if is_eq else ((40, 36, 60) if is_hov else (30, 27, 44))
                border = config.NEON_CYAN if is_eq else (config.GOLD if is_hov else config.UI_BORDER)
                pygame.draw.rect(surface, bg, irect, border_radius=10)
                pygame.draw.rect(surface, border, irect, width=3 if is_eq else 1, border_radius=10)

                rec_ids = st_meta["recipes"]
                first_rec = rec_ids[0] if rec_ids else "bungeoppang_redbean"
                art_renderer.draw_food_icon(surface, (irect.x + 32, irect.centery), first_rec, size=44)

                c_tag = f"[{st_meta['country']}] {st_meta['short_name']}"
                nm_surf = card_f.render(c_tag, True, config.WHITE if is_eq else config.TEXT_PRIMARY)
                surface.blit(nm_surf, (irect.x + 62, irect.y + 10))

                rec_names = [RECIPES[r]["name"] for r in rec_ids[:2] if r in RECIPES]
                menu_str = ", ".join(rec_names)
                if len(rec_ids) > 2:
                    menu_str += f" 외 {len(rec_ids) - 2}종"
                active_menu_f = small_f
                max_menu_w = irect.width - 68
                for f_sz in (11, 10, 9):
                    if active_menu_f.size(menu_str)[0] <= max_menu_w:
                        break
                    active_menu_f = config.get_font(f_sz, bold=False)
                m_surf = active_menu_f.render(menu_str, True, config.TEXT_SECONDARY)
                surface.blit(m_surf, (irect.x + 62, irect.y + 34))

                status_str = "✔ 현재 장착됨" if is_eq else "클릭하여 장착"
                st_col = config.NEON_CYAN if is_eq else config.TEXT_GOLD
                st_surf = small_f.render(status_str, True, st_col)
                surface.blit(st_surf, (irect.x + 62, irect.y + 58))

                self._click_targets.append((irect, "set_global_station", (slot_type, st_id)))

    # ------------------------------------------------------------------
    # 탭 3: 기구 업그레이드 5종 & 포차 인테리어 4종 상점
    # ------------------------------------------------------------------
    def _draw_upgrade_tab(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        mx, my = self._hover_pos
        sec_f = config.get_font(19, bold=True)
        name_f = config.get_font(16, bold=True)
        body_f = config.get_font(13, bold=False)
        btn_f = config.get_font(14, bold=True)

        left_x = area.x + 20
        s_hdr = sec_f.render("🛠️ 조리 기구 & 트레이 강화 (최대 Lv.3)", True, config.GOLD)
        surface.blit(s_hdr, (left_x, area.y + 14))

        row_w = 595
        row_h = 82
        for idx, up_key in enumerate(STATION_UPGRADE_ORDER):
            up_data = STATION_UPGRADES[up_key]
            lvl = self.game_mgr.get_station_level(up_key)
            max_lvl = int(up_data["max_level"])
            cost = self.game_mgr.get_station_upgrade_cost(up_key)

            rrect = pygame.Rect(left_x, area.y + 48 + idx * (row_h + 7), row_w, row_h)
            pygame.draw.rect(surface, (34, 30, 50), rrect, border_radius=12)
            pygame.draw.rect(surface, config.UI_BORDER, rrect, width=1, border_radius=12)

            hw_rect = pygame.Rect(rrect.x + 10, rrect.y + 11, 60, 60)
            art_renderer.draw_station_hardware(surface, hw_rect, station_type=up_data["slot_type"])

            nm = name_f.render(f"{up_data['name']}  (Lv.{lvl}/{max_lvl})", True, config.WHITE)
            surface.blit(nm, (rrect.x + 82, rrect.y + 10))

            next_lvl = min(max_lvl, lvl + 1)
            desc_str = up_data["levels"][next_lvl]["description"]
            active_desc_f = body_f if body_f.size(desc_str)[0] <= 350 else config.get_font(12, bold=False)
            ds = active_desc_f.render(desc_str, True, config.NEON_CYAN if lvl < max_lvl else config.TEXT_SUCCESS)
            surface.blit(ds, (rrect.x + 82, rrect.y + 35))

            for l_i in range(max_lvl):
                dot_rect = pygame.Rect(rrect.x + 82 + l_i * 28, rrect.y + 58, 22, 10)
                pygame.draw.rect(
                    surface,
                    config.GOLD if l_i < lvl else (60, 56, 78),
                    dot_rect,
                    border_radius=4,
                )

            btn_rect = pygame.Rect(rrect.right - 148, rrect.centery - 22, 134, 44)
            is_hov = btn_rect.collidepoint(mx, my)
            story_max = self.game_mgr.get_story_max_station_level(up_key)
            if cost is None:
                pygame.draw.rect(surface, (46, 105, 68), btn_rect, border_radius=10)
                bt = btn_f.render("MAX 완료", True, config.WHITE)
            elif lvl >= story_max:
                pygame.draw.rect(surface, (44, 40, 62), btn_rect, border_radius=10)
                pygame.draw.rect(surface, config.UI_BORDER, btn_rect, width=1, border_radius=10)
                bt = config.get_font(12, bold=True).render("🔒 스토리 해금 대기", True, config.TEXT_SECONDARY)
                self._click_targets.append((btn_rect, "upgrade_station", up_key))
            else:
                can_buy = self.game_mgr.can_upgrade_station(up_key)
                bg = (225, 118, 38) if (can_buy and is_hov) else ((195, 95, 32) if can_buy else config.UI_DISABLED)
                pygame.draw.rect(surface, bg, btn_rect, border_radius=10)
                pygame.draw.rect(surface, config.GOLD if can_buy else config.UI_BORDER, btn_rect, width=2 if can_buy else 1, border_radius=10)
                bt = btn_f.render(f"강화 {cost:,}원", True, config.WHITE if can_buy else config.TEXT_SECONDARY)
                self._click_targets.append((btn_rect, "upgrade_station", up_key))
            surface.blit(bt, bt.get_rect(center=btn_rect.center))

        right_x = area.x + 632
        i_hdr = sec_f.render("🏮 포차 감성 인테리어 소품 (영구 패시브 보너스)", True, config.NEON_PINK)
        surface.blit(i_hdr, (right_x, area.y + 14))

        i_row_w = 572
        i_row_h = 104
        for idx, in_key in enumerate(INTERIOR_UPGRADE_ORDER):
            in_data = INTERIOR_UPGRADES[in_key]
            lvl = self.game_mgr.get_interior_level(in_key)
            cost = self.game_mgr.get_interior_upgrade_cost(in_key)

            irect = pygame.Rect(right_x, area.y + 48 + idx * (i_row_h + 9), i_row_w, i_row_h)
            pygame.draw.rect(surface, (38, 32, 56) if lvl > 0 else (32, 28, 46), irect, border_radius=12)
            pygame.draw.rect(
                surface,
                config.TEXT_SUCCESS if lvl > 0 else config.UI_BORDER,
                irect,
                width=2 if lvl > 0 else 1,
                border_radius=12,
            )

            nm = name_f.render(in_data["name"], True, config.GOLD if lvl > 0 else config.WHITE)
            surface.blit(nm, (irect.x + 18, irect.y + 14))

            self._draw_wrapped_text(
                surface,
                in_data["description"],
                body_f,
                config.TEXT_PRIMARY,
                irect.x + 18,
                irect.y + 42,
                irect.width - 178,
            )

            btn_rect = pygame.Rect(irect.right - 146, irect.centery - 22, 132, 44)
            is_hov = btn_rect.collidepoint(mx, my)
            in_unlocked = self.game_mgr.is_interior_unlocked_in_story(in_key)
            if cost is None or lvl >= 1:
                pygame.draw.rect(surface, (46, 105, 68), btn_rect, border_radius=10)
                bt = btn_f.render("✔ 설치 완료", True, config.WHITE)
            elif not in_unlocked:
                pygame.draw.rect(surface, (44, 40, 62), btn_rect, border_radius=10)
                pygame.draw.rect(surface, config.UI_BORDER, btn_rect, width=1, border_radius=10)
                bt = config.get_font(12, bold=True).render("🔒 스토리 해금 대기", True, config.TEXT_SECONDARY)
                self._click_targets.append((btn_rect, "upgrade_interior", in_key))
            else:
                can_buy = self.game_mgr.can_upgrade_interior(in_key)
                bg = (225, 118, 38) if (can_buy and is_hov) else ((195, 95, 32) if can_buy else config.UI_DISABLED)
                pygame.draw.rect(surface, bg, btn_rect, border_radius=10)
                pygame.draw.rect(surface, config.GOLD if can_buy else config.UI_BORDER, btn_rect, width=2 if can_buy else 1, border_radius=10)
                bt = btn_f.render(f"구매 {cost:,}원", True, config.WHITE if can_buy else config.TEXT_SECONDARY)
                self._click_targets.append((btn_rect, "upgrade_interior", in_key))
            surface.blit(bt, bt.get_rect(center=btn_rect.center))

    # ------------------------------------------------------------------
    # 탭 4: 32강 월드 포차 그랑프리 (배너 일러스트 + 9개국 32시드 + AI 보스 대결 출격)
    # ------------------------------------------------------------------
    def _draw_tournament_tab(self, surface: pygame.Surface, area: pygame.Rect) -> None:
        mx, my = self._hover_pos
        sec_f = config.get_font(17, bold=True)
        name_f = config.get_font(14, bold=True)
        xs_f = config.get_font(12, bold=False)

        # 좌측: 32강 월드 그랑프리 메인 일러스트 배너 + 영토 비례 시드 배정 + AI 보스전 출격 카드
        left_x = area.x + 20
        l_hdr = sec_f.render("🌍 9개국 32인 월드 포차 그랑프리 (영토 면적·식문화 비례 시드)", True, config.NEON_CYAN)
        surface.blit(l_hdr, (left_x, area.y + 12))

        banner_frame = pygame.Rect(left_x, area.y + 42, 560, 212)
        pygame.draw.rect(surface, (18, 16, 28), banner_frame, border_radius=12)
        banner_img = art_renderer.get_story_illustration(
            "assets/story/world_32_masters_banner.png",
            (banner_frame.width - 8, banner_frame.height - 8),
        )
        if banner_img is not None:
            surface.blit(banner_img, (banner_frame.x + 4, banner_frame.y + 4))
        else:
            art_renderer.draw_country_background(surface, banner_frame.inflate(-8, -8), country_id="CN", time_tick=self.time_tick)
        pygame.draw.rect(surface, config.GOLD, banner_frame, width=2, border_radius=12)

        # 배너 하단 오버레이 캡션
        cap_r = pygame.Rect(banner_frame.x + 8, banner_frame.bottom - 34, banner_frame.width - 16, 26)
        art_renderer.draw_alpha_overlay(surface, cap_r, (14, 12, 24, 215), border_radius=6)
        cap_f = config.get_font(11, bold=True)
        cap_s = cap_f.render("중국(6) · 인도(6) · 미국(5) · 러시아(3) · 브라질(3) · 멕시코(3) · 일본(3) · 대만(2) · 한국(1) = 총 32명", True, config.GOLD)
        surface.blit(cap_s, cap_s.get_rect(center=cap_r.center))

        # 현재 토너먼트 라운드 AI 라이벌 매치업 박스
        opp_id = self._get_current_tournament_opponent()
        opp_char = CHARACTERS.get(opp_id, CHARACTERS["chef_cn_sichuan"])
        rnd_idx = min(5, int(getattr(self.game_mgr, "tournament_round_idx", 0)))
        rnd_names = ["32강전 (Round of 32)", "16강전 (Round of 16)", "8강전 (Quarterfinal)", "4강 준결승 (Semifinal)", "결승전 (Grand Final)", "전세계 챔피언 타이틀 방어전"]

        vs_box = pygame.Rect(left_x, area.y + 264, 560, 166)
        pygame.draw.rect(surface, (34, 28, 52), vs_box, border_radius=12)
        pygame.draw.rect(surface, config.NEON_ORANGE, vs_box, width=2, border_radius=12)

        surface.blit(
            name_f.render(f"🔥 현재 출전 라운드: {rnd_names[rnd_idx]}   |   승리 보상: +{3000 + min(4, rnd_idx) * 2000:,}원", True, config.GOLD),
            (vs_box.x + 14, vs_box.y + 10),
        )

        # 나 vs AI 보스 아바타 대결 구도
        my_char = self.game_mgr.get_selected_character_data()
        my_av = pygame.Rect(vs_box.x + 20, vs_box.y + 42, 82, 82)
        opp_av = pygame.Rect(vs_box.right - 102, vs_box.y + 42, 82, 82)
        art_renderer.draw_chef_avatar(surface, my_av, character_id=self.game_mgr.selected_character, state="SKILL", time_tick=self.time_tick)
        art_renderer.draw_chef_avatar(surface, opp_av, character_id=opp_id, state="SKILL", time_tick=self.time_tick)

        surface.blit(name_f.render(f"나: {my_char['name']}", True, config.NEON_GREEN), (my_av.right + 10, vs_box.y + 44))
        surface.blit(xs_f.render(f"[{my_char.get('region_name', '')}]", True, config.GOLD), (my_av.right + 10, vs_box.y + 68))
        surface.blit(xs_f.render(f"{my_char['skill_name'][:11]}", True, config.TEXT_PRIMARY), (my_av.right + 10, vs_box.y + 88))

        vs_f = config.get_font(20, bold=True)
        vs_s = vs_f.render("⚡ VS ⚡", True, config.GOLD)
        surface.blit(vs_s, vs_s.get_rect(center=(vs_box.centerx, vs_box.y + 82)))

        opp_lbl = name_f.render(f"AI: {opp_char['name']}", True, (255, 138, 138))
        opp_reg = xs_f.render(f"[{opp_char.get('region_name', '')}]", True, config.GOLD)
        opp_sub = xs_f.render(f"{opp_char.get('specialty_tag', '')[:11]}", True, config.TEXT_PRIMARY)
        surface.blit(opp_lbl, (opp_av.left - opp_lbl.get_width() - 10, vs_box.y + 44))
        surface.blit(opp_reg, (opp_av.left - opp_reg.get_width() - 10, vs_box.y + 68))
        surface.blit(opp_sub, (opp_av.left - opp_sub.get_width() - 10, vs_box.y + 88))

        surface.blit(
            xs_f.render("※ 출격 시 영업 화면 상단에 실시간 [나 vs AI 라이벌] 매출 줄다리기 게이지가 가동됩니다!", True, config.NEON_CYAN),
            (vs_box.x + 14, vs_box.bottom - 26),
        )

        # 좌측 하단 [⚔️ 32강 토너먼트 AI 보스전 출격!] 버튼
        match_btn = pygame.Rect(left_x, area.bottom - 62, 560, 46)
        m_hov = match_btn.collidepoint(mx, my)
        pygame.draw.rect(surface, (228, 72, 48) if m_hov else (188, 52, 38), match_btn, border_radius=12)
        pygame.draw.rect(surface, config.GOLD, match_btn, width=2, border_radius=12)
        m_txt = sec_f.render(f"⚔️ {rnd_names[rnd_idx].split(' ')[0]} AI 보스전 즉시 출격! (VS {opp_char['name']})", True, config.WHITE)
        surface.blit(m_txt, m_txt.get_rect(center=match_btn.center))
        self._click_targets.append((match_btn, "start_tournament_match", opp_id))

        # 우측: 32강 월드 포차 그랑프리 5라운드 & 32인 셰프 시드 일람
        right_x = area.x + 602
        r_hdr = sec_f.render("🏆 32강 월드 포차 그랑프리 대진표 (32인 지역 마스터 시드)", True, config.GOLD)
        surface.blit(r_hdr, (right_x, area.y + 12))

        r_w = 602
        row_y = area.y + 42
        for tier_num in (5, 4, 3, 2, 1):
            t_meta = TOURNAMENT_TIERS[tier_num]
            chefs = [c for c in TOURNAMENT_32_ROSTER.values() if c["tier"] == tier_num]
            box_h = 82
            t_rect = pygame.Rect(right_x, row_y, r_w, box_h)
            is_curr_round = (rnd_idx + 1) == tier_num
            is_cleared_round = (rnd_idx + 1) > tier_num
            pygame.draw.rect(surface, (46, 38, 68) if is_curr_round else (32, 28, 46), t_rect, border_radius=10)
            b_col = config.NEON_GREEN if is_cleared_round else (config.GOLD if (tier_num == 5 or is_curr_round) else config.UI_BORDER)
            pygame.draw.rect(surface, b_col, t_rect, width=2 if (is_curr_round or tier_num >= 4) else 1, border_radius=10)

            status_prefix = "✔ [돌파] " if is_cleared_round else ("🔥 [현재 라운드] " if is_curr_round else "★ ")
            hdr_txt = name_f.render(
                f"{status_prefix}{t_meta['round_name']} [{t_meta['label']} · {len(chefs)}명] — 목표 분당 {t_meta['expected_gold_per_min']:,}원",
                True,
                config.NEON_GREEN if is_cleared_round else (config.GOLD if tier_num >= 4 or is_curr_round else config.NEON_CYAN),
            )
            surface.blit(hdr_txt, (t_rect.x + 12, t_rect.y + 7))

            chef_tags = [f"[{c['country']}·{c.get('region_name', '')[:3]}]{c['name']}" for c in chefs]
            per_line = 4
            for ln_i in range(0, len(chef_tags), per_line):
                chunk = "  ·  ".join(chef_tags[ln_i : ln_i + per_line])
                c_surf = xs_f.render(chunk, True, config.TEXT_PRIMARY)
                surface.blit(c_surf, (t_rect.x + 14, t_rect.y + 32 + (ln_i // per_line) * 21))

            row_y += box_h + 9

    # ------------------------------------------------------------------
    # 하단 현재 로드아웃 요약 & [오늘 영업 시작!] 버튼
    # ------------------------------------------------------------------
    def _draw_bottom_summary(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos
        sum_rect = pygame.Rect(28, 642, 856, 60)
        pygame.draw.rect(surface, (26, 22, 38), sum_rect, border_radius=14)
        pygame.draw.rect(surface, config.UI_BORDER, sum_rect, width=1, border_radius=14)

        bold_f = config.get_font(15, bold=True)
        sub_f = config.get_font(13, bold=False)

        char_data = self.game_mgr.get_selected_character_data()
        active_sts = self.game_mgr.get_active_station_metas()
        unlocked_sts = [
            active_sts[s]["short_name"]
            for s in SLOT_TYPES
            if self.game_mgr.is_slot_unlocked_in_story(s)
        ]
        st_names = " / ".join(unlocked_sts) if unlocked_sts else "붕어빵 틀"
        target = self.game_mgr.get_target_gold()
        reg_tag = char_data.get("region_name", char_data.get("country_name", "한국"))

        line1 = f"👨‍🍳 출전 마스터: [{reg_tag}] {char_data['name']} ({char_data['skill_name']})   |   📅 Day {self.game_mgr.day} 목표 매출: {target:,}원"
        line2 = f"🔥 오늘 가동 기구: {st_names}   (영업을 클리어하면 다음 조리 기구 및 세계 챕터가 해금됩니다!)"

        s1 = bold_f.render(line1, True, config.GOLD)
        s2 = sub_f.render(line2, True, config.TEXT_PRIMARY)
        surface.blit(s1, (sum_rect.x + 18, sum_rect.y + 9))
        surface.blit(s2, (sum_rect.x + 18, sum_rect.y + 34))

        # 우측 하단 [🏮 오늘 영업 시작! (START DAY)] 버튼
        is_hov = self.start_day_btn_rect.collidepoint(mx, my)
        pulse = 0.88 + 0.12 * math.sin(self.time_tick * 5.0)
        btn_col = (248, 122, 42) if is_hov else (int(232 * pulse), int(92 * pulse), 34)
        pygame.draw.rect(surface, btn_col, self.start_day_btn_rect, border_radius=14)
        pygame.draw.rect(surface, config.GOLD, self.start_day_btn_rect, width=3, border_radius=14)

        start_f = config.get_font(22, bold=True)
        st_txt = start_f.render("🏮 오늘 영업 시작! (START)", True, config.WHITE)
        surface.blit(st_txt, st_txt.get_rect(center=self.start_day_btn_rect.center))

    @staticmethod
    def _draw_wrapped_text(
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
        line_spacing: int = 19,
    ) -> None:
        words = text.split(" ")
        lines: List[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip() if current else w
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

        for i, line in enumerate(lines[:2]):
            surf = font.render(line, True, color)
            surface.blit(surf, (x, y + i * line_spacing))
