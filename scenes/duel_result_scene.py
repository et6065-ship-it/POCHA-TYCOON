"""
scenes/duel_result_scene.py
'전세계 길거리 음식 포차 타이쿤' 1:1 네트워크 결투 최종 성적 비교 및 승패 결과 씬 (DuelResultScene).
- 내 최종 매출과 상대방의 최종 매출, 서빙 성공 손님 수, 놓친 손님 수, 최고 콤보를 나란히 비교
- 승리(VICTORY) / 패배(DEFEAT) / 무승부(DRAW) 연출 및 매출 격차 표시
- TCP 연결을 유지한 채 대기실로 돌아가 즉시 재대결할 수 있는 [대기실 복귀 & 재대결] 버튼 지원
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple
import pygame

import config
from core import art_renderer
from core.effects import ParticleSystem, sound_fx
from core.game_manager import GameManager
from core.network_manager import DuelNetworkManager, duel_network
from core.scene_manager import BaseScene, SceneManager
from data.chapters import CHAPTERS
from data.characters import CHARACTERS


class DuelResultScene(BaseScene):
    """1:1 네트워크 결투 결과 및 성적 비교 씬."""

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        scene_mgr: Optional[SceneManager] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(game_mgr, scene_mgr, **kwargs)
        self.net: DuelNetworkManager = duel_network
        self.time_tick: float = 0.0
        self.particles: ParticleSystem = ParticleSystem()
        self._hover_pos: Tuple[int, int] = (0, 0)

        self.chapter: str = str(kwargs.get("chapter", "KR")).upper()
        self.duration: int = int(kwargs.get("duration", config.DUEL_DEFAULT_DURATION))
        self.station_level: int = int(kwargs.get("station_level", config.DUEL_DEFAULT_STATION_LEVEL))

        self.my_summary: Dict[str, Any] = dict(
            kwargs.get(
                "my_summary",
                {
                    "name": "나 (ME)",
                    "char": "chef_kr",
                    "gold": 0,
                    "served": 0,
                    "missed": 0,
                    "max_combo": 0,
                },
            )
        )
        self.opp_summary: Dict[str, Any] = dict(
            kwargs.get(
                "opp_summary",
                {
                    "name": "상대 (RIVAL)",
                    "char": "chef_jp",
                    "gold": 0,
                    "served": 0,
                    "missed": 0,
                    "max_combo": 0,
                    "forfeited": False,
                    "disconnected": False,
                },
            )
        )

        self.rematch_btn_rect: pygame.Rect = pygame.Rect(340, 618, 320, 56)
        self.title_btn_rect: pygame.Rect = pygame.Rect(685, 618, 255, 56)

    def on_enter(self, **kwargs: Any) -> None:
        if "my_summary" in kwargs:
            self.my_summary = dict(kwargs["my_summary"])
        if "opp_summary" in kwargs:
            self.opp_summary = dict(kwargs["opp_summary"])
        if "chapter" in kwargs:
            self.chapter = str(kwargs["chapter"]).upper()
        if "duration" in kwargs:
            self.duration = int(kwargs["duration"])

        outcome = self._get_outcome()
        if outcome == "WIN":
            sound_fx.play_fanfare()
            for x_pos in (320, 640, 960):
                self.particles.emit_stars(x_pos, 140, count=16)
        elif outcome == "DRAW":
            sound_fx.play_ready()
        else:
            sound_fx.play_burn()

    def _get_outcome(self) -> str:
        if self.opp_summary.get("forfeited"):
            return "WIN"
        my_g = int(self.my_summary.get("gold", 0))
        opp_g = int(self.opp_summary.get("gold", 0))
        if my_g > opp_g:
            return "WIN"
        if my_g < opp_g:
            return "LOSE"
        # 매출 동점일 경우 서빙 손님 수 -> 최고 콤보 비교
        my_s = int(self.my_summary.get("served", 0))
        opp_s = int(self.opp_summary.get("served", 0))
        if my_s > opp_s:
            return "WIN"
        if my_s < opp_s:
            return "LOSE"
        return "DRAW"

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.rematch_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("duel_lobby", rematch=True)
            elif self.title_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                self.net.close()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title")

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("duel_lobby", rematch=True)
            elif event.key == pygame.K_ESCAPE:
                sound_fx.play_click()
                self.net.close()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title")

    def update(self, dt: float) -> None:
        self.time_tick += dt
        self.particles.update(dt)

        # 상대방의 마지막 MATCH_FINISH 패킷이 조금 늦게 도착한 경우에도 실시간 반영
        for msg in self.net.poll_messages():
            mtype = msg.get("type")
            if mtype in ("MATCH_FINISH", "STATE_SYNC"):
                self.opp_summary["gold"] = max(int(self.opp_summary.get("gold", 0)), int(msg.get("gold", 0)))
                self.opp_summary["served"] = max(int(self.opp_summary.get("served", 0)), int(msg.get("served", 0)))
                self.opp_summary["missed"] = int(msg.get("missed", self.opp_summary.get("missed", 0)))
                self.opp_summary["max_combo"] = max(
                    int(self.opp_summary.get("max_combo", 0)),
                    int(msg.get("max_combo", 0)),
                )

    def draw(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos
        art_renderer.draw_country_background(
            surface,
            (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            country_id=self.chapter if self.chapter in CHAPTERS else "KR",
            interior_levels={"lighting": 1, "signboard": 1, "prop": 1, "seating": 1},
            time_tick=self.time_tick,
        )

        art_renderer.draw_alpha_overlay(
            surface,
            (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            (12, 10, 22, 215),
        )

        outcome = self._get_outcome()
        my_gold = int(self.my_summary.get("gold", 0))
        opp_gold = int(self.opp_summary.get("gold", 0))
        diff = abs(my_gold - opp_gold)

        # 상단 메인 결과 배너
        banner_rect = pygame.Rect(140, 34, 1000, 128)
        pygame.draw.rect(surface, (28, 24, 46), banner_rect, border_radius=20)

        if outcome == "WIN":
            border_col = config.GOLD
            title_str = "🏆 VICTORY! — 1:1 포차 매출 결투 승리!!"
            if self.opp_summary.get("forfeited"):
                sub_str = f"상대방 기권으로 승리!  (내 최종 매출: {my_gold:,}원)"
            else:
                sub_str = f"상대보다 +{diff:,}원 더 높은 매출을 달성하여 야시장 최강자에 등극했습니다!"
        elif outcome == "LOSE":
            border_col = config.TEXT_WARNING
            title_str = "💔 DEFEAT — 1:1 포차 매출 결투 패배..."
            sub_str = f"상대에게 {diff:,}원 차이로 아쉽게 패배했습니다. 재대결로 설욕해 보세요!"
        else:
            border_col = config.NEON_CYAN
            title_str = "🤝 DRAW — 1:1 포차 매출 결투 무승부!"
            sub_str = f"양측 모두 {my_gold:,}원으로 치열한 명승부를 펼쳤습니다!"

        pygame.draw.rect(surface, border_col, banner_rect, width=3, border_radius=20)

        title_f = config.get_font(36, bold=True)
        sub_f = config.get_font(17, bold=True)
        meta_f = config.get_font(14, bold=False)

        t_surf = title_f.render(title_str, True, border_col)
        s_surf = sub_f.render(sub_str, True, config.WHITE)
        ch_name = CHAPTERS.get(self.chapter, CHAPTERS["KR"])["name"]
        m_surf = meta_f.render(
            f"결투 지역: {ch_name}   ·   제한 시간: {self.duration}초   ·   공정 기구 레벨: Lv.{self.station_level}",
            True,
            config.TEXT_SECONDARY,
        )

        surface.blit(t_surf, (banner_rect.centerx - t_surf.get_width() // 2, banner_rect.y + 18))
        surface.blit(s_surf, (banner_rect.centerx - s_surf.get_width() // 2, banner_rect.y + 68))
        surface.blit(m_surf, (banner_rect.centerx - m_surf.get_width() // 2, banner_rect.y + 98))

        # 좌측(나) vs 우측(상대) 성적 비교 카드
        left_rect = pygame.Rect(140, 184, 470, 408)
        right_rect = pygame.Rect(670, 184, 470, 408)

        self._draw_comparison_card(
            surface,
            rect=left_rect,
            tag="👑 나 (MY POCHA)",
            summary=self.my_summary,
            is_winner=(outcome == "WIN"),
            accent_color=config.POCHA_ORANGE,
        )
        self._draw_comparison_card(
            surface,
            rect=right_rect,
            tag="⚔ 상대 (RIVAL POCHA)",
            summary=self.opp_summary,
            is_winner=(outcome == "LOSE"),
            accent_color=config.NEON_CYAN,
        )

        # 중앙 VS 원형 배지
        vs_center = (config.SCREEN_WIDTH // 2, 388)
        pygame.draw.circle(surface, (42, 34, 68), vs_center, 32)
        pygame.draw.circle(surface, config.GOLD, vs_center, 32, width=3)
        vs_f = config.get_font(22, bold=True)
        vs_s = vs_f.render("VS", True, config.GOLD)
        surface.blit(vs_s, (vs_center[0] - vs_s.get_width() // 2, vs_center[1] - vs_s.get_height() // 2))

        # 하단 액션 버튼
        btn_f = config.get_font(18, bold=True)
        buttons = [
            (self.rematch_btn_rect, "🔄 대기실 복귀 & 재대결 [SPACE]", config.POCHA_ORANGE),
            (self.title_btn_rect, "🏠 연결 종료 & 타이틀로 [ESC]", config.UI_BUTTON),
        ]
        for rect, label, col in buttons:
            hov = rect.collidepoint(mx, my)
            pygame.draw.rect(surface, config.UI_BUTTON_HOVER if hov else col, rect, border_radius=12)
            pygame.draw.rect(surface, config.GOLD if hov else config.WHITE, rect, width=2, border_radius=12)
            bt = btn_f.render(label, True, config.WHITE)
            surface.blit(bt, (rect.centerx - bt.get_width() // 2, rect.centery - bt.get_height() // 2))

        self.particles.draw(surface)

    def _draw_comparison_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        tag: str,
        summary: Dict[str, Any],
        is_winner: bool,
        accent_color: Tuple[int, int, int],
    ) -> None:
        bg_col = (38, 32, 60) if is_winner else (26, 22, 42)
        pygame.draw.rect(surface, bg_col, rect, border_radius=18)
        pygame.draw.rect(
            surface,
            config.GOLD if is_winner else accent_color,
            rect,
            width=3 if is_winner else 2,
            border_radius=18,
        )

        hdr_f = config.get_font(18, bold=True)
        name_f = config.get_font(22, bold=True)
        row_f = config.get_font(18, bold=True)
        val_f = config.get_font(22, bold=True)

        h_surf = hdr_f.render(tag, True, config.GOLD if is_winner else accent_color)
        surface.blit(h_surf, (rect.x + 24, rect.y + 18))

        if is_winner:
            win_badge = pygame.Rect(rect.right - 126, rect.y + 14, 104, 28)
            pygame.draw.rect(surface, config.GOLD, win_badge, border_radius=14)
            wb_f = config.get_font(14, bold=True)
            wb_s = wb_f.render("★ WINNER!", True, (20, 16, 24))
            surface.blit(wb_s, (win_badge.centerx - wb_s.get_width() // 2, win_badge.centery - wb_s.get_height() // 2))

        char_id = str(summary.get("char", "chef_kr"))
        char_data = CHARACTERS.get(char_id, CHARACTERS["chef_kr"])

        av_rect = pygame.Rect(rect.x + 28, rect.y + 58, 96, 96)
        art_renderer.draw_chef_avatar(
            surface,
            av_rect,
            character_id=char_id,
            state="SKILL" if is_winner else "IDLE",
            time_tick=self.time_tick,
        )

        p_name = str(summary.get("name", char_data["name"]))
        n_surf = name_f.render(f"{char_data['name']} ({char_data['country']})", True, config.WHITE)
        sub_s = config.get_font(14, bold=False).render(f"{p_name} · {char_data['title']}", True, config.TEXT_SECONDARY)
        surface.blit(n_surf, (rect.x + 142, rect.y + 74))
        surface.blit(sub_s, (rect.x + 142, rect.y + 108))

        # 성적 테이블
        table_rect = pygame.Rect(rect.x + 22, rect.y + 172, rect.width - 44, 214)
        pygame.draw.rect(surface, (18, 16, 30), table_rect, border_radius=12)
        pygame.draw.rect(surface, config.UI_BORDER, table_rect, width=1, border_radius=12)

        gold = int(summary.get("gold", 0))
        served = int(summary.get("served", 0))
        missed = int(summary.get("missed", 0))
        max_combo = int(summary.get("max_combo", 0))

        rows = [
            ("💰 최종 달성 매출", f"{gold:,}원", config.GOLD),
            ("😊 서빙 성공 손님", f"{served}명", config.TEXT_SUCCESS),
            ("🔥 최고 연속 콤보", f"{max_combo} COMBO", config.NEON_CYAN),
            ("💢 놓친 손님 수", f"{missed}명", config.TEXT_WARNING if missed > 0 else config.TEXT_SECONDARY),
        ]

        for idx, (lbl, val, col) in enumerate(rows):
            ry = table_rect.y + 18 + idx * 46
            ls = row_f.render(lbl, True, config.TEXT_SECONDARY)
            vs = val_f.render(val, True, col)
            surface.blit(ls, (table_rect.x + 20, ry))
            surface.blit(vs, (table_rect.right - vs.get_width() - 20, ry))
