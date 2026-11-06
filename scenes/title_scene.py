"""
scenes/title_scene.py
'전세계 길거리 음식 포차 타이쿤' 메인 타이틀 및 게임 모드 선택 씬.
- 야시장 네온사인 감성 배경 (art_renderer.draw_country_background 활용)
- 모드 선택 카드 2종:
  1) 월드 투어 모드 (WORLD_TOUR): 한국 → 일본 → 멕시코 → 대만 챕터 스테이지 진행
  2) 글로벌 야시장 통합 모드 (GLOBAL_ENDLESS): 전 세계 조리 기구 4슬롯 자유 조합 경영
- 현재 선택된 포차 마스터 아바타 미리보기, 보유 골드, 세이브 불러오기/초기화, 조작 가이드 제공
"""

from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple
import pygame

import config
from core import art_renderer
from core.effects import FloatingText, ParticleSystem, sound_fx
from core.game_manager import GameManager, game_manager
from core.scene_manager import BaseScene, SceneManager
from data.chapters import CHAPTER_ORDER, CHAPTERS


class TitleScene(BaseScene):
    """야시장 네온사인 감성 메인 타이틀 씬."""

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        scene_mgr: Optional[SceneManager] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(game_mgr, scene_mgr, **kwargs)
        self.time_tick: float = 0.0
        self.particles: ParticleSystem = ParticleSystem()
        self.hovered_card: Optional[str] = None
        self.hovered_btn: Optional[str] = None
        self.preview_country: str = self.game_mgr.current_chapter or "KR"

        # UI 영역 Rect 정의 (1280 x 720) — 프로필 카드 + 2대 메인 게임 모드 카드 (1:1 대전 카드 숨김)
        self.profile_card_rect: pygame.Rect = pygame.Rect(40, 215, 340, 340)
        self.world_tour_rect: pygame.Rect = pygame.Rect(404, 215, 406, 340)
        self.global_mode_rect: pygame.Rect = pygame.Rect(834, 215, 406, 340)
        self.duel_mode_rect: pygame.Rect = pygame.Rect(-9999, -9999, 0, 0)

        # 하단 유틸리티 버튼 Rect 및 상단 9개국 배경 테마 프리뷰 버튼
        self.load_btn_rect: pygame.Rect = pygame.Rect(40, 648, 156, 46)
        self.reset_btn_rect: pygame.Rect = pygame.Rect(204, 648, 156, 46)
        self.options_btn_rect: pygame.Rect = pygame.Rect(368, 648, 186, 46)
        self.rotate_btn_rect: pygame.Rect = pygame.Rect(562, 648, 172, 46)
        self.fullscreen_btn_rect: pygame.Rect = pygame.Rect(742, 648, 178, 46)
        self.country_btn_rects: List[Tuple[str, pygame.Rect]] = [
            (cid, pygame.Rect(796 + idx * 49, 20, 44, 28))
            for idx, cid in enumerate(CHAPTER_ORDER)
        ]

    def on_enter(self, **kwargs: Any) -> None:
        self.preview_country = self.game_mgr.current_chapter or "KR"

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.hovered_card = None
            self.hovered_btn = None
            if self.world_tour_rect.collidepoint(mx, my):
                self.hovered_card = "WORLD_TOUR"
            elif self.global_mode_rect.collidepoint(mx, my):
                self.hovered_card = "GLOBAL_ENDLESS"
            elif self.profile_card_rect.collidepoint(mx, my):
                self.hovered_card = "PROFILE"

            if self.load_btn_rect.collidepoint(mx, my):
                self.hovered_btn = "LOAD"
            elif self.reset_btn_rect.collidepoint(mx, my):
                self.hovered_btn = "RESET"
            elif self.options_btn_rect.collidepoint(mx, my):
                self.hovered_btn = "OPTIONS"
            elif self.rotate_btn_rect.collidepoint(mx, my):
                self.hovered_btn = "ROTATE"
            elif self.fullscreen_btn_rect.collidepoint(mx, my):
                self.hovered_btn = "FULLSCREEN"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # 배경 국가 테마 미리보기 전환 버튼
            for cid, crect in self.country_btn_rects:
                if crect.collidepoint(mx, my):
                    self.preview_country = cid
                    sound_fx.play_click()
                    return

            # 1) 월드 투어 모드 카드 클릭
            if self.world_tour_rect.collidepoint(mx, my):
                sound_fx.play_click()
                self.game_mgr.set_mode("WORLD_TOUR")
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", initial_tab="chapter", show_loading=True)
                return

            # 2) 글로벌 야시장 통합 모드 카드 클릭
            if self.global_mode_rect.collidepoint(mx, my):
                sound_fx.play_click()
                self.game_mgr.set_mode("GLOBAL_ENDLESS")
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", initial_tab="chapter", show_loading=True)
                return

            # 프로필 카드 클릭 시 주인공 선택 탭으로 이동
            if self.profile_card_rect.collidepoint(mx, my):
                sound_fx.play_click()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", initial_tab="character", show_loading=True)
                return

            # 세이브 불러오기 버튼
            if self.load_btn_rect.collidepoint(mx, my):
                loaded = self.game_mgr.load_game()
                if loaded:
                    sound_fx.play_cash()
                    self.preview_country = self.game_mgr.current_chapter or "KR"
                    self.particles.spawn_floating_text(
                        "세이브 데이터를 불러왔습니다!",
                        self.load_btn_rect.centerx + 40,
                        self.load_btn_rect.top - 12,
                        color=config.TEXT_SUCCESS,
                        size=20,
                    )
                else:
                    sound_fx.play_burn()
                    self.particles.spawn_floating_text(
                        "저장된 세이브 파일이 없습니다.",
                        self.load_btn_rect.centerx + 40,
                        self.load_btn_rect.top - 12,
                        color=config.TEXT_WARNING,
                        size=20,
                    )
                return

            # 세이브 초기화 버튼
            if self.reset_btn_rect.collidepoint(mx, my):
                sound_fx.play_burn()
                self.game_mgr.reset_state()
                self.game_mgr.save_game()
                self.preview_country = "KR"
                self.particles.spawn_floating_text(
                    "진행 데이터가 초기화되었습니다!",
                    self.reset_btn_rect.centerx,
                    self.reset_btn_rect.top - 12,
                    color=config.NEON_YELLOW,
                    size=20,
                )
                return

            # 옵션 (사운드·해상도) 설정 버튼
            if self.options_btn_rect.collidepoint(mx, my):
                if self.scene_mgr:
                    self.scene_mgr.open_options()
                return

            # 가로/세로 방향 즉시 전환 버튼
            if self.rotate_btn_rect.collidepoint(mx, my):
                if self.scene_mgr and hasattr(self.scene_mgr, "toggle_orientation"):
                    self.scene_mgr.toggle_orientation()
                return

            # 전체화면 (브라우저 전체화면 포함) 즉시 전환 버튼
            if self.fullscreen_btn_rect.collidepoint(mx, my):
                if self.scene_mgr and hasattr(self.scene_mgr, "toggle_fullscreen"):
                    self.scene_mgr.toggle_fullscreen()
                return

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_o):
                if self.scene_mgr:
                    self.scene_mgr.open_options()
            elif event.key in (pygame.K_1, pygame.K_RETURN, pygame.K_SPACE):
                sound_fx.play_click()
                self.game_mgr.set_mode("WORLD_TOUR")
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", initial_tab="chapter", show_loading=True)
            elif event.key == pygame.K_2:
                sound_fx.play_click()
                self.game_mgr.set_mode("GLOBAL_ENDLESS")
                if self.scene_mgr:
                    self.scene_mgr.change_scene("prep", initial_tab="chapter", show_loading=True)

    def update(self, dt: float) -> None:
        self.time_tick += dt
        self.particles.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # 1. 화려한 국가별 야시장 배경 렌더링
        bg_rect = pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        art_renderer.draw_country_background(
            surface,
            bg_rect,
            country_id=self.preview_country,
            interior_levels={"lighting": 1, "signboard": 1, "prop": 1, "seating": 1},
            time_tick=self.time_tick,
        )

        # 가독성을 위한 반투명 다크 오버레이 (캐싱)
        art_renderer.draw_alpha_overlay(surface, bg_rect, (14, 12, 26, 145))

        # 2. 상단 네온 타이틀 배너
        self._draw_title_header(surface)

        # 3. 좌측 현재 주인공 & 진행도 요약 카드
        self._draw_profile_card(surface)

        # 4. 중앙/우측 게임 모드 선택 카드 2종 (스토리 모드 & 글로벌 통합 모드)
        self._draw_mode_card(
            surface,
            rect=self.world_tour_rect,
            mode_key="WORLD_TOUR",
            badge_text="MODE 1 · STORY & WORLD TOUR",
            title_text="월드 투어 스토리",
            subtitle_text="Pocha Revival Story Mode",
            desc_lines=[
                "폐업 식당 팔고 붕어빵 리어카부터 재기!",
                "일차별 조리기구·토핑·스킬 단계적 해금",
                "삽화 컷신 & 32강 월드 포차 그랑프리",
            ],
            food_icons=["bungeoppang_redbean", "takoyaki_mayo", "taco_salsa", "congzuobing_egg"],
            accent_color=config.POCHA_ORANGE,
            button_label="스토리 모드 입장 [1]",
        )

        self._draw_mode_card(
            surface,
            rect=self.global_mode_rect,
            mode_key="GLOBAL_ENDLESS",
            badge_text="MODE 2 · CUSTOM LOADOUT",
            title_text="글로벌 통합 모드",
            subtitle_text="Global Night Market Endless",
            desc_lines=[
                "전 세계 9개국 36종 기구 자유 조합!",
                "붕어빵 틀 + 타코 그릴 + 마라탕·탄두리까지",
                "32인 지역별 마스터로 최고 매출 도전!",
            ],
            food_icons=["skewer_greenonion", "yakisoba_egg", "nacho_cheese", "boba_milktea"],
            accent_color=config.NEON_CYAN,
            button_label="글로벌 통합 입장 [2]",
        )

        # 5. 하단 조작 가이드 및 세이브/화면 전환 버튼
        self._draw_bottom_bar(surface)

        # 6. 파티클 & 플로팅 텍스트
        self.particles.draw(surface)

    def _draw_title_header(self, surface: pygame.Surface) -> None:
        header_rect = pygame.Rect(40, 56, 1200, 138)
        art_renderer.draw_alpha_overlay(surface, header_rect, (24, 18, 40, 225), border_radius=18)

        # 네온 테두리 점멸 효과
        pulse = 0.8 + 0.2 * math.sin(self.time_tick * 4.0)
        border_col = (
            int(255 * pulse),
            int(165 * pulse + 30),
            int(55 * pulse),
        )
        pygame.draw.rect(surface, border_col, header_rect, width=3, border_radius=18)
        pygame.draw.rect(surface, (255, 235, 145), header_rect.inflate(-8, -8), width=1, border_radius=14)

        # 좌우 대표 음식 아이콘 장식
        left_foods = ["bungeoppang_redbean", "skewer_spicy", "tteokbokki_cheese"]
        right_foods = ["takoyaki_mayo", "taco_guac", "boba_milktea"]
        for i, fid in enumerate(left_foods):
            bob = int(math.sin(self.time_tick * 3.5 + i) * 4)
            art_renderer.draw_food_icon(surface, (105 + i * 64, header_rect.centery + bob), fid, size=54)
        for i, fid in enumerate(right_foods):
            bob = int(math.sin(self.time_tick * 3.5 + i + 1.5) * 4)
            art_renderer.draw_food_icon(
                surface,
                (header_rect.right - 235 + i * 64, header_rect.centery + bob),
                fid,
                size=54,
            )

        # 메인 타이틀 텍스트
        title_font = config.get_font(42, bold=True)
        sub_font = config.get_font(16, bold=True)
        tag_font = config.get_font(14, bold=True)

        title_str = "전세계 길거리 음식 포차 타이쿤"
        shadow_surf = title_font.render(title_str, True, (225, 65, 35))
        main_surf = title_font.render(title_str, True, (255, 238, 120))
        cx = header_rect.centerx
        surface.blit(shadow_surf, (cx - main_surf.get_width() // 2 + 3, header_rect.y + 24))
        surface.blit(main_surf, (cx - main_surf.get_width() // 2, header_rect.y + 21))

        sub_str = "WORLD STREET FOOD POCHA TYCOON · 9개국(KR·JP·MX·TW·CN·IN·US·RU·BR) 32인 지역 마스터"
        sub_surf = sub_font.render(sub_str, True, config.TEXT_PRIMARY)
        surface.blit(sub_surf, (cx - sub_surf.get_width() // 2, header_rect.y + 82))

        tag_str = "★ 1인칭 포차 조리 & 원클릭 자동 비행 서빙 · 32강 월드 포차 그랑프리 ★"
        tag_surf = tag_font.render(tag_str, True, config.NEON_CYAN)
        surface.blit(tag_surf, (cx - tag_surf.get_width() // 2, header_rect.y + 109))

        # 우측 상단 배경 테마 미리보기 버튼
        lbl_font = config.get_font(12, bold=True)
        lbl = lbl_font.render("9개국 야시장 배경 미리보기:", True, config.TEXT_SECONDARY)
        surface.blit(lbl, (625, 26))
        for cid, crect in self.country_btn_rects:
            is_sel = self.preview_country == cid
            bg_c = config.UI_BUTTON_ACTIVE if is_sel else config.UI_PANEL
            pygame.draw.rect(surface, bg_c, crect, border_radius=6)
            pygame.draw.rect(
                surface,
                config.GOLD if is_sel else config.UI_BORDER,
                crect,
                width=2 if is_sel else 1,
                border_radius=6,
            )
            c_txt = lbl_font.render(cid, True, config.WHITE if is_sel else config.TEXT_SECONDARY)
            surface.blit(c_txt, (crect.centerx - c_txt.get_width() // 2, crect.centery - c_txt.get_height() // 2))

    def _draw_profile_card(self, surface: pygame.Surface) -> None:
        rect = self.profile_card_rect
        is_hover = self.hovered_card == "PROFILE"
        bg_col = (48, 42, 68) if is_hover else (34, 30, 50)
        pygame.draw.rect(surface, bg_col, rect, border_radius=16)
        pygame.draw.rect(
            surface,
            config.GOLD if is_hover else config.UI_BORDER,
            rect,
            width=2,
            border_radius=16,
        )

        char_data = self.game_mgr.get_selected_character_data()
        header_font = config.get_font(16, bold=True)
        name_font = config.get_font(22, bold=True)
        small_font = config.get_font(14, bold=False)
        bold_small = config.get_font(14, bold=True)

        hdr = header_font.render("👨‍🍳 현재 포차 마스터", True, config.TEXT_GOLD)
        surface.blit(hdr, (rect.centerx - hdr.get_width() // 2, rect.y + 14))

        # 셰프 아바타
        avatar_rect = pygame.Rect(rect.centerx - 52, rect.y + 44, 104, 104)
        art_renderer.draw_chef_avatar(
            surface,
            avatar_rect,
            character_id=self.game_mgr.selected_character,
            state="COOKING" if is_hover else "IDLE",
            time_tick=self.time_tick,
        )

        # 이름 & 칭호
        name_s = name_font.render(f"{char_data['name']} ({char_data['country']})", True, config.WHITE)
        title_s = small_font.render(char_data["title"], True, config.NEON_CYAN)
        surface.blit(name_s, (rect.centerx - name_s.get_width() // 2, rect.y + 156))
        surface.blit(title_s, (rect.centerx - title_s.get_width() // 2, rect.y + 184))

        # 구분선
        pygame.draw.line(surface, config.UI_BORDER, (rect.x + 18, rect.y + 210), (rect.right - 18, rect.y + 210), 1)

        # 보유 골드 & 해금 현황
        gold_s = bold_small.render(f"💰 보유 자금: {self.game_mgr.gold:,}원", True, config.GOLD)
        surface.blit(gold_s, (rect.x + 22, rect.y + 220))

        ch_list = ", ".join(self.game_mgr.unlocked_chapters)
        ch_s = small_font.render(f"🗺️ 해금 챕터: {ch_list}", True, config.TEXT_PRIMARY)
        surface.blit(ch_s, (rect.x + 22, rect.y + 244))

        skill_s = small_font.render(f"⚡ 스킬: {char_data['skill_name']}", True, config. POCHA_WARM_LIGHT)
        surface.blit(skill_s, (rect.x + 22, rect.y + 268))

        # 마스터 변경 안내 버튼
        btn_rect = pygame.Rect(rect.x + 20, rect.bottom - 44, rect.width - 40, 32)
        pygame.draw.rect(surface, config.UI_BUTTON_HOVER if is_hover else config.UI_BUTTON, btn_rect, border_radius=8)
        pygame.draw.rect(surface, config.UI_HIGHLIGHT if is_hover else config.UI_BORDER, btn_rect, width=1, border_radius=8)
        b_txt = bold_small.render("마스터 선택 / 상점 이동 ▶", True, config.WHITE)
        surface.blit(b_txt, (btn_rect.centerx - b_txt.get_width() // 2, btn_rect.centery - b_txt.get_height() // 2))

    def _draw_mode_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        mode_key: str,
        badge_text: str,
        title_text: str,
        subtitle_text: str,
        desc_lines: List[str],
        food_icons: List[str],
        accent_color: Tuple[int, int, int],
        button_label: str,
    ) -> None:
        is_hover = self.hovered_card == mode_key
        draw_rect = rect.move(0, -4) if is_hover else rect

        # 카드 배경
        bg_col = (46, 40, 68) if is_hover else (34, 30, 50)
        pygame.draw.rect(surface, bg_col, draw_rect, border_radius=18)
        pygame.draw.rect(
            surface,
            accent_color if is_hover else config.UI_BORDER,
            draw_rect,
            width=3 if is_hover else 2,
            border_radius=18,
        )

        # 상단 배지
        badge_rect = pygame.Rect(draw_rect.x + 18, draw_rect.y + 16, 196, 24)
        pygame.draw.rect(surface, accent_color, badge_rect, border_radius=12)
        badge_font = config.get_font(12, bold=True)
        b_surf = badge_font.render(badge_text, True, (20, 16, 28))
        surface.blit(b_surf, (badge_rect.centerx - b_surf.get_width() // 2, badge_rect.centery - b_surf.get_height() // 2))

        # 타이틀 & 서브타이틀
        title_font = config.get_font(23, bold=True)
        sub_font = config.get_font(13, bold=True)
        desc_font = config.get_font(13, bold=False)

        t_surf = title_font.render(title_text, True, config.WHITE)
        s_surf = sub_font.render(subtitle_text, True, accent_color)
        surface.blit(t_surf, (draw_rect.x + 18, draw_rect.y + 48))
        surface.blit(s_surf, (draw_rect.x + 18, draw_rect.y + 82))

        # 음식 아이콘 프리뷰 쇼케이스 박스
        showcase_rect = pygame.Rect(draw_rect.x + 18, draw_rect.y + 110, draw_rect.width - 36, 72)
        pygame.draw.rect(surface, (24, 20, 36), showcase_rect, border_radius=12)
        pygame.draw.rect(surface, (72, 64, 98), showcase_rect, width=1, border_radius=12)

        spacing = showcase_rect.width // (len(food_icons) + 1)
        for i, fid in enumerate(food_icons):
            ix = showcase_rect.x + spacing * (i + 1)
            iy = showcase_rect.centery + (int(math.sin(self.time_tick * 4.0 + i) * 3) if is_hover else 0)
            art_renderer.draw_food_icon(surface, (ix, iy), fid, size=44)

        # 설명 텍스트 라인
        for idx, line in enumerate(desc_lines):
            d_surf = desc_font.render(f"• {line}", True, config.TEXT_PRIMARY if idx == 0 else config.TEXT_SECONDARY)
            surface.blit(d_surf, (draw_rect.x + 18, draw_rect.y + 196 + idx * 24))

        # 하단 액션 버튼
        btn_rect = pygame.Rect(draw_rect.x + 18, draw_rect.bottom - 54, draw_rect.width - 36, 40)
        btn_bg = accent_color if is_hover else (64, 58, 88)
        btn_fg = (20, 16, 26) if is_hover else config.WHITE
        pygame.draw.rect(surface, btn_bg, btn_rect, border_radius=10)
        pygame.draw.rect(surface, config.WHITE if is_hover else accent_color, btn_rect, width=2, border_radius=10)

        btn_font = config.get_font(15, bold=True)
        btn_txt = btn_font.render(button_label, True, btn_fg)
        surface.blit(btn_txt, (btn_rect.centerx - btn_txt.get_width() // 2, btn_rect.centery - btn_txt.get_height() // 2))

    def _draw_bottom_bar(self, surface: pygame.Surface) -> None:
        # 조작 방법 가이드 바
        guide_rect = pygame.Rect(40, 572, 1200, 62)
        pygame.draw.rect(surface, (28, 24, 42), guide_rect, border_radius=12)
        pygame.draw.rect(surface, config.UI_BORDER, guide_rect, width=1, border_radius=12)

        title_f = config.get_font(15, bold=True)
        body_f = config.get_font(14, bold=False)

        g1 = title_f.render("📱 모바일 터치 & PC 마우스 원터치 완벽 지원 (다중 화면비 16:9 · 20:9 · 태블릿 호환)", True, config.GOLD)
        g2 = body_f.render(
            "• [원터치 조작]: 기구 터치 조리 → 트레이 토핑 추가 → 완성 메뉴 터치 시 가장 급한 손님에게 포물선 자동 비행 서빙!",
            True,
            config.TEXT_PRIMARY,
        )
        surface.blit(g1, (guide_rect.x + 18, guide_rect.y + 10))
        surface.blit(g2, (guide_rect.x + 18, guide_rect.y + 34))

        # 세이브 불러오기 / 초기화 / 옵션 / 가로·세로 회전 / 브라우저 전체화면 버튼
        is_portrait = bool(getattr(self.scene_mgr, "is_portrait_mode", False))
        rot_label = "🔄 가로모드 전환" if is_portrait else "🔄 세로모드 전환"
        for key, rect, label, col in (
            ("LOAD", self.load_btn_rect, "💾 세이브 로드", config.NEON_CYAN),
            ("RESET", self.reset_btn_rect, "🗑️ 초기화", config.TEXT_WARNING),
            ("OPTIONS", self.options_btn_rect, "⚙️ 사운드·화면 설정", config.GOLD),
            ("ROTATE", self.rotate_btn_rect, rot_label, config.NEON_GREEN),
            ("FULLSCREEN", self.fullscreen_btn_rect, "⛶ 전체화면 전환", config.POCHA_ORANGE),
        ):
            is_hov = self.hovered_btn == key
            pygame.draw.rect(
                surface,
                config.UI_BUTTON_HOVER if is_hov else config.UI_PANEL,
                rect,
                border_radius=10,
            )
            pygame.draw.rect(surface, col if is_hov else config.UI_BORDER, rect, width=2 if is_hov else 1, border_radius=10)
            bf = config.get_font(14, bold=True)
            bt = bf.render(label, True, config.WHITE if is_hov else col)
            surface.blit(bt, (rect.centerx - bt.get_width() // 2, rect.centery - bt.get_height() // 2))

        # 우측 하단 단축키 요약 (하단 버튼 우측 영역 x=935~1240 배치)
        key_f = config.get_font(12, bold=True)
        k_txt = key_f.render(
            "단축키: [Q/W/E/R/A/S] 조리 · [SPACE] 스킬 · [F10] 옵션",
            True,
            config.TEXT_SECONDARY,
        )
        surface.blit(k_txt, (1240 - k_txt.get_width(), 664))
