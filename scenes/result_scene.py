"""
scenes/result_scene.py
'전세계 길거리 음식 포차 타이쿤' 일일 마감 정산 씬 (ResultScene).
- 오늘의 총 매출, 목표 매출 달성 여부, 획득 별점(1~3성, calculate_stars) 표시
- 서빙 성공 손님 수, 놓친 손님 수, 최고 콤보, 총 보유 자산 표시
- 월드 투어 모드 클리어 및 챕터 해금 안내/별점 달성 축하 메시지 표시
- [다음 날 준비 (상점/로드아웃)], [다시 도전], [타이틀 화면으로] 버튼 제공
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
from data.chapters import CHAPTER_ORDER, CHAPTERS, calculate_stars
from data.story import get_story_cutscene


class ResultScene(BaseScene):
    """일일 영업 마감 정산 및 별점 평가 씬."""

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

        # 클리어 스토리 컷신 큐
        self.cutscene_queue: List[Any] = []
        self.active_cutscene: Optional[Any] = None
        self.cutscene_line_idx: int = 0
        self._cutscene_next_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._cutscene_skip_rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

        # 정산 데이터 추출
        self.summary: Dict[str, Any] = self._extract_summary(kwargs)

        # 하단 3개 버튼 Rect
        self.prep_btn_rect: pygame.Rect = pygame.Rect(230, 610, 290, 56)
        self.retry_btn_rect: pygame.Rect = pygame.Rect(545, 610, 240, 56)
        self.title_btn_rect: pygame.Rect = pygame.Rect(810, 610, 240, 56)

    def _queue_clear_cutscenes(self) -> None:
        self.cutscene_queue.clear()
        self.active_cutscene = None
        self.cutscene_line_idx = 0
        if self.game_mgr.mode != "WORLD_TOUR" or not self.summary.get("cleared", False):
            return
        ch = self.game_mgr.current_chapter
        day_num = int(self.summary.get("day", 1))
        clear_cs = get_story_cutscene(ch, day_num, timing="clear")
        if clear_cs:
            self.cutscene_queue.append(clear_cs)
        if ch == "KR" and day_num == 5:
            dep_cs = get_story_cutscene("world_departure")
            if dep_cs:
                self.cutscene_queue.append(dep_cs)
        elif ch == "TW" and day_num in (3, 5):
            end_cs = get_story_cutscene("ending")
            if end_cs and end_cs not in self.cutscene_queue:
                self.cutscene_queue.append(end_cs)
        if self.cutscene_queue:
            self.active_cutscene = self.cutscene_queue.pop(0)
            self.cutscene_line_idx = 0

    def _advance_cutscene(self, skip_all: bool = False) -> None:
        sound_fx.play_click()
        if skip_all or self.active_cutscene is None:
            self.cutscene_queue.clear()
            self.active_cutscene = None
            self.cutscene_line_idx = 0
            return
        lines = self.active_cutscene.get("lines", [])
        if self.cutscene_line_idx + 1 < len(lines):
            self.cutscene_line_idx += 1
        elif self.cutscene_queue:
            self.active_cutscene = self.cutscene_queue.pop(0)
            self.cutscene_line_idx = 0
        else:
            self.active_cutscene = None
            self.cutscene_line_idx = 0

    def _extract_summary(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        raw = kwargs.get("result_data") or kwargs.get("day_stats") or kwargs.get("summary")
        if isinstance(raw, dict):
            earned = int(raw.get("earned_gold", self.game_mgr.daily_gold))
            target = int(raw.get("target_gold", self.game_mgr.get_target_gold()))
            stars = int(raw.get("stars", calculate_stars(earned, target)))
            cleared = bool(raw.get("cleared", earned >= target))
            day_num = int(raw.get("day", max(1, self.game_mgr.day - 1)))
            served = int(raw.get("served_customers", self.game_mgr.served_customers))
            missed = int(raw.get("missed_customers", self.game_mgr.missed_customers))
            max_combo = int(raw.get("max_combo", self.game_mgr.max_combo))
            bonus_msg = str(raw.get("unlock_message", ""))
        else:
            earned = int(kwargs.get("earned_gold", self.game_mgr.daily_gold))
            target = int(kwargs.get("target_gold", self.game_mgr.get_target_gold()))
            stars = int(kwargs.get("stars", calculate_stars(earned, target)))
            cleared = bool(kwargs.get("cleared", earned >= target))
            day_num = int(kwargs.get("day", self.game_mgr.day))
            served = int(kwargs.get("served_customers", self.game_mgr.served_customers))
            missed = int(kwargs.get("missed_customers", self.game_mgr.missed_customers))
            max_combo = int(kwargs.get("max_combo", self.game_mgr.max_combo))
            bonus_msg = str(kwargs.get("unlock_message", ""))

        if not bonus_msg:
            bonus_msg = self._build_congrats_message(day_num, cleared, stars)

        return {
            "day": day_num,
            "earned_gold": earned,
            "target_gold": target,
            "stars": stars,
            "cleared": cleared,
            "served_customers": served,
            "missed_customers": missed,
            "max_combo": max_combo,
            "unlock_message": bonus_msg,
        }

    def _build_congrats_message(self, day_num: int, cleared: bool, stars: int) -> str:
        if not cleared:
            return "💡 팁: 상점에서 조리 기구를 강화하거나 포차 마스터 스킬[SPACE]을 적극 활용해 보세요!"

        if self.game_mgr.mode == "WORLD_TOUR":
            cur_ch = self.game_mgr.current_chapter
            if cur_ch in CHAPTER_ORDER:
                idx = CHAPTER_ORDER.index(cur_ch)
                if idx + 1 < len(CHAPTER_ORDER):
                    next_ch = CHAPTER_ORDER[idx + 1]
                    next_name = CHAPTERS[next_ch]["name"]
                    cost = CHAPTERS[next_ch]["unlock_cost"]
                    if not self.game_mgr.is_chapter_unlocked(next_ch):
                        if day_num >= 2 or self.game_mgr.gold >= cost:
                            return f"🎊 Day {day_num} 클리어! 영업 준비 화면에서 다음 챕터 [{next_name}]을 해금할 수 있습니다!"
                        return f"🌟 목표 달성 성공! 골드를 모아 다음 국가 [{next_name} ({cost:,}원)]에 도전하세요!"
        if stars >= 3:
            return "🏆 완벽한 3성(★★★) 마스터피스 영업! 손님들이 극찬하며 팁을 아끼지 않았습니다!"
        return "🎉 오늘의 목표 매출 달성 성공! 포차 명성이 더욱 높아졌습니다!"

    def on_enter(self, **kwargs: Any) -> None:
        if kwargs:
            self.summary = self._extract_summary(kwargs)
        self.game_mgr.save_game()

        if self.summary["cleared"]:
            sound_fx.play_fanfare()
            for x_pos in (360, 640, 920):
                self.particles.emit_stars(x_pos, 180, count=14)
            self._queue_clear_cutscenes()
        else:
            sound_fx.play_burn()
            self.cutscene_queue.clear()
            self.active_cutscene = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.active_cutscene is not None:
                if self._cutscene_skip_rect.collidepoint(mx, my):
                    self._advance_cutscene(skip_all=True)
                else:
                    self._advance_cutscene(skip_all=False)
                return

            if self.prep_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", show_loading=True)
            elif self.retry_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("play", show_cutscene=True, show_loading=True)
            elif self.title_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title", show_loading=True)

        elif event.type == pygame.KEYDOWN:
            if self.active_cutscene is not None:
                if event.key == pygame.K_ESCAPE:
                    self._advance_cutscene(skip_all=True)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                    self._advance_cutscene(skip_all=False)
                return

            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", show_loading=True)
            elif event.key == pygame.K_r:
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("play", show_cutscene=True, show_loading=True)
            elif event.key == pygame.K_ESCAPE:
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title", show_loading=True)

    def update(self, dt: float) -> None:
        self.time_tick += dt
        self.particles.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos
        bg_country = self.game_mgr.current_chapter or "KR"
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
            (14, 12, 24, 210),
        )

        # 중앙 정산 보드
        board_rect = pygame.Rect(180, 48, 920, 535)
        pygame.draw.rect(surface, (30, 26, 46), board_rect, border_radius=20)
        cleared = self.summary["cleared"]
        border_col = config.GOLD if cleared else config.TEXT_WARNING
        pygame.draw.rect(surface, border_col, board_rect, width=3, border_radius=20)

        # 상단 배너 타이틀
        title_f = config.get_font(36, bold=True)
        sub_f = config.get_font(18, bold=True)

        day_num = self.summary["day"]
        ch_name = CHAPTERS.get(self.game_mgr.current_chapter, CHAPTERS["KR"])["name"]
        mode_str = "글로벌 야시장 통합 모드" if self.game_mgr.mode == "GLOBAL_ENDLESS" else ch_name

        hdr_str = f"🏮 Day {day_num} 영업 마감 정산 — {'목표 달성 성공!' if cleared else '목표 매출 미달성'}"
        hdr_surf = title_f.render(hdr_str, True, config.GOLD if cleared else config.TEXT_WARNING)
        surface.blit(hdr_surf, (board_rect.centerx - hdr_surf.get_width() // 2, board_rect.y + 24))

        sub_surf = sub_f.render(f"영업 지역: {mode_str}   |   마스터: {self.game_mgr.get_selected_character_data()['name']}", True, config.TEXT_SECONDARY)
        surface.blit(sub_surf, (board_rect.centerx - sub_surf.get_width() // 2, board_rect.y + 72))

        # 획득 별점 (1~3성) 커다란 아이콘 연출
        stars = self.summary["stars"]
        star_y = board_rect.y + 135
        for i in range(3):
            sx = board_rect.centerx - 110 + i * 110
            is_lit = i < stars
            bounce = int(math.sin(self.time_tick * 4.5 + i) * 4) if is_lit else 0
            self._draw_big_star(surface, (sx, star_y + bounce), 36, is_lit)

        # 좌측 포차 마스터 아바타 & 한마디
        av_rect = pygame.Rect(board_rect.x + 42, board_rect.y + 195, 150, 150)
        art_renderer.draw_chef_avatar(
            surface,
            av_rect,
            character_id=self.game_mgr.selected_character,
            state="SKILL" if cleared else "IDLE",
            time_tick=self.time_tick,
        )

        # 우측 상세 성적표 테이블
        stat_box = pygame.Rect(board_rect.x + 220, board_rect.y + 190, 650, 250)
        pygame.draw.rect(surface, (22, 19, 34), stat_box, border_radius=14)
        pygame.draw.rect(surface, config.UI_BORDER, stat_box, width=1, border_radius=14)

        row_f = config.get_font(20, bold=True)
        val_f = config.get_font(22, bold=True)

        earned = self.summary["earned_gold"]
        target = self.summary["target_gold"]
        rows = [
            ("💰 오늘의 총 매출액", f"{earned:,}원", config.GOLD),
            ("🎯 일일 목표 매출액", f"{target:,}원", config.TEXT_PRIMARY),
            ("😊 서빙 완료한 손님", f"{self.summary['served_customers']}명", config.TEXT_SUCCESS),
            ("💢 놓친 손님 (인내심 소진)", f"{self.summary['missed_customers']}명", config.TEXT_WARNING if self.summary["missed_customers"] > 0 else config.TEXT_SECONDARY),
            ("🔥 오늘 최고 연속 콤보", f"{self.summary['max_combo']} COMBO", config.NEON_CYAN),
            ("🏦 현재 총 보유 자금", f"{self.game_mgr.gold:,}원", config.GOLD),
        ]

        for idx, (label, val_str, col) in enumerate(rows):
            ry = stat_box.y + 16 + idx * 38
            l_surf = row_f.render(label, True, config.TEXT_SECONDARY)
            v_surf = val_f.render(val_str, True, col)
            surface.blit(l_surf, (stat_box.x + 26, ry))
            surface.blit(v_surf, (stat_box.right - v_surf.get_width() - 26, ry))

        # 하단 해금/축하 메시지 배너
        msg_box = pygame.Rect(board_rect.x + 42, board_rect.bottom - 76, board_rect.width - 84, 54)
        pygame.draw.rect(surface, (42, 36, 66), msg_box, border_radius=12)
        pygame.draw.rect(surface, config.NEON_CYAN if cleared else config.UI_BORDER, msg_box, width=2, border_radius=12)
        msg_f = config.get_font(16, bold=True)
        m_surf = msg_f.render(self.summary["unlock_message"], True, config.WHITE)
        surface.blit(m_surf, (msg_box.centerx - m_surf.get_width() // 2, msg_box.centery - m_surf.get_height() // 2))

        # 하단 액션 버튼 3종
        buttons = [
            (self.prep_btn_rect, "🛠️ 다음 날 준비 (상점/로드아웃)", config.POCHA_ORANGE),
            (self.retry_btn_rect, "🔄 다시 영업하기 [R]", config.NEON_CYAN),
            (self.title_btn_rect, "🏠 타이틀 화면으로", config.UI_BUTTON),
        ]
        btn_f = config.get_font(18, bold=True)
        for rect, label, base_col in buttons:
            is_hov = rect.collidepoint(mx, my)
            bg = config.UI_BUTTON_HOVER if is_hov else base_col
            pygame.draw.rect(surface, bg, rect, border_radius=12)
            pygame.draw.rect(surface, config.GOLD if is_hov else config.WHITE, rect, width=2, border_radius=12)
            txt = btn_f.render(label, True, config.WHITE)
            surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

        self.particles.draw(surface)

        if self.active_cutscene is not None:
            self._cutscene_next_rect, self._cutscene_skip_rect = art_renderer.draw_story_cutscene_overlay(
                surface,
                self.active_cutscene,
                line_idx=self.cutscene_line_idx,
                time_tick=self.time_tick,
            )

    @staticmethod
    def _draw_big_star(surface: pygame.Surface, center: Tuple[int, int], radius: int, filled: bool) -> None:
        cx, cy = center
        pts: List[Tuple[int, int]] = []
        for i in range(10):
            ang = -math.pi / 2 + i * (math.pi / 5)
            r = radius if i % 2 == 0 else int(radius * 0.44)
            pts.append((int(cx + math.cos(ang) * r), int(cy + math.sin(ang) * r)))
        col = config.GOLD if filled else (62, 58, 78)
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, config.WHITE if filled else config.UI_BORDER, pts, width=2)
