"""
stations/base_station.py
모든 조리 기구의 공통 슬롯(StationSlot) 상태 머신 및 기본 스테이션(BaseStation) 추상 인터페이스 모듈.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import pygame

import config
from core.art_renderer import draw_food_icon, draw_station_hardware
from core.game_manager import GameManager
from data.chapters import STATIONS_CATALOG
from data.recipes import RECIPES

STATE_IDLE: str = "IDLE"
STATE_COOKING: str = "COOKING"
STATE_READY: str = "READY"
STATE_BURNT: str = "BURNT"


def invoke_auto_serve(
    auto_serve_cb: Optional[Callable[..., Any]],
    recipe_id: str,
    center_pos: Tuple[int, int],
) -> Tuple[bool, Any]:
    """
    auto_serve_cb 콜백을 안전하게 호출한다.
    콜백이 (recipe_id, pos) 2개 인자를 받거나 (recipe_id) 1개 인자를 받는 경우를 모두 지원하며,
    반환값이 bool이거나 dict({'served': bool, ...})인 경우를 모두 처리한다.
    """
    if auto_serve_cb is None:
        return False, None
    try:
        res = auto_serve_cb(recipe_id, center_pos)
    except TypeError:
        res = auto_serve_cb(recipe_id)

    if res is None or res is False:
        return False, res
    if isinstance(res, dict):
        return bool(res.get("served", True)), res
    return bool(res), res


class StationSlot:
    """
    조리 기구 내의 개별 조리 슬롯 상태 머신.
    상태 전이: IDLE -> COOKING -> READY -> BURNT
    """

    def __init__(
        self,
        slot_index: int = 0,
        rect: Optional[Union[pygame.Rect, Tuple[int, int, int, int]]] = None,
        can_burn: bool = True,
    ) -> None:
        self.slot_index: int = int(slot_index)
        self.rect: pygame.Rect = (
            rect.copy()
            if isinstance(rect, pygame.Rect)
            else pygame.Rect(rect or (0, 0, 72, 72))
        )
        self.state: str = STATE_IDLE
        self.recipe_id: Optional[str] = None
        self.elapsed: float = 0.0
        self.cook_time: float = 4.5
        self.burn_time: float = 9.0
        self.can_burn: bool = bool(can_burn)
        self.servings: int = 0
        self.max_servings: int = 1
        self.needs_flip: bool = False
        self.flipped: bool = False
        self.flip_burn_elapsed: float = 0.0
        self._flip_sound_played: bool = False
        self._burn_warn_played: bool = False

    @property
    def timer(self) -> float:
        """elapsed의 별칭."""
        return self.elapsed

    @timer.setter
    def timer(self, value: float) -> None:
        self.elapsed = float(value)

    @property
    def is_idle(self) -> bool:
        return self.state == STATE_IDLE

    @property
    def is_cooking(self) -> bool:
        return self.state == STATE_COOKING

    @property
    def is_ready(self) -> bool:
        return self.state == STATE_READY

    @property
    def is_burnt(self) -> bool:
        return self.state == STATE_BURNT

    @property
    def progress(self) -> float:
        """조리 진행률(0.0 ~ 1.0)을 반환한다."""
        if self.state == STATE_IDLE:
            return 0.0
        if self.state == STATE_COOKING:
            return max(0.0, min(1.0, self.elapsed / max(0.05, self.cook_time)))
        return 1.0

    @property
    def is_flip_ready(self) -> bool:
        """반죽틀(needs_flip=True)에서 앞면이 다 익어 터치해 뒤집어야 하는 타이밍인지 반환한다."""
        return (
            self.state == STATE_COOKING
            and self.needs_flip
            and not self.flipped
            and self.elapsed >= (self.cook_time * 0.5 - 0.01)
        )

    @property
    def can_flip_now(self) -> bool:
        """반죽틀에서 앞면이 어느 정도(30% 이상) 익어 뒤집기 터치가 가능한지 반환한다."""
        return (
            self.state == STATE_COOKING
            and self.needs_flip
            and not self.flipped
            and self.elapsed >= (self.cook_time * 0.30)
        )

    def flip_mold(self) -> bool:
        """반죽틀을 뒤집어 뒷면 굽기 단계(50% -> 100%)로 진입한다."""
        if self.state == STATE_COOKING and self.needs_flip and not self.flipped:
            self.flipped = True
            self.elapsed = max(self.elapsed, self.cook_time * 0.5)
            self.flip_burn_elapsed = 0.0
            self._burn_warn_played = False
            return True
        return False

    @property
    def burn_progress(self) -> float:
        """뒤집기 지연 또는 완성 후 타기까지의 진행률(0.0 ~ 1.0)을 반환한다."""
        if self.state == STATE_BURNT:
            return 1.0
        if self.is_flip_ready and self.can_burn:
            return max(0.0, min(1.0, self.flip_burn_elapsed / max(0.05, self.burn_time)))
        if self.state == STATE_READY and self.can_burn:
            return max(0.0, min(1.0, self.elapsed / max(0.05, self.burn_time)))
        return 0.0

    def start_cooking(
        self,
        recipe_id: str,
        cook_time: float,
        burn_time: float = 9.0,
        can_burn: Optional[bool] = None,
        servings: int = 1,
        needs_flip: bool = False,
    ) -> None:
        """슬롯에서 지정된 레시피의 조리를 시작한다."""
        self.recipe_id = str(recipe_id)
        self.cook_time = max(0.2, float(cook_time))
        self.burn_time = max(1.0, float(burn_time))
        if can_burn is not None:
            self.can_burn = bool(can_burn)
        self.max_servings = max(1, int(servings))
        self.servings = self.max_servings
        self.elapsed = 0.0
        self.needs_flip = bool(needs_flip)
        self.flipped = False
        self.flip_burn_elapsed = 0.0
        self._flip_sound_played = False
        self._burn_warn_played = False
        self.state = STATE_COOKING

    def instant_finish(self) -> bool:
        """조리 중인 슬롯을 즉시 완성(READY) 상태로 전환한다."""
        if self.state == STATE_COOKING and self.recipe_id:
            self.flipped = True
            self.flip_burn_elapsed = 0.0
            self._flip_sound_played = True
            self._burn_warn_played = False
            self.state = STATE_READY
            self.elapsed = 0.0
            self.servings = max(1, self.max_servings)
            return True
        return False

    def reset(self) -> None:
        """슬롯을 빈 상태(IDLE)로 초기화한다."""
        self.state = STATE_IDLE
        self.recipe_id = None
        self.elapsed = 0.0
        self.servings = 0
        self.flipped = False
        self.flip_burn_elapsed = 0.0
        self._flip_sound_played = False
        self._burn_warn_played = False

    clear = reset

    def update(self, dt: float) -> Optional[str]:
        """
        시간 경과(dt)에 따라 조리 및 탄 상태를 업데이트한다.
        - needs_flip=True이고 아직 뒤집지 않은 경우(not flipped):
          앞면(50%)까지 익은 뒤 뒤집기 대기 상태(is_flip_ready)가 되며, 제때 안 뒤집으면 타버린다(STATE_BURNT).
        - 뒤집은 후(flipped=True)에는 100%까지 익어 황금빛 완성(STATE_READY)이 된다.
        """
        dt = max(0.0, float(dt))
        if self.state == STATE_COOKING:
            if self.needs_flip and not self.flipped:
                half_t = self.cook_time * 0.5
                if self.elapsed < half_t:
                    self.elapsed = min(half_t, self.elapsed + dt)
                else:
                    self.elapsed = half_t
                    if self.can_burn:
                        self.flip_burn_elapsed += dt
                        if self.flip_burn_elapsed >= self.burn_time:
                            self.state = STATE_BURNT
                            self.elapsed = 0.0
                            return STATE_BURNT
                return None

            self.elapsed += dt
            if self.elapsed >= self.cook_time:
                self.state = STATE_READY
                self.elapsed = 0.0
                self.servings = max(1, self.max_servings)
                return STATE_READY

        elif self.state == STATE_READY and self.can_burn:
            self.elapsed += dt
            if self.elapsed >= self.burn_time:
                self.state = STATE_BURNT
                self.elapsed = 0.0
                return STATE_BURNT

        return None

    def draw_slot_box(
        self,
        surface: pygame.Surface,
        time_tick: float = 0.0,
        empty_label: str = "➕ 터치 조리",
    ) -> None:
        """개별 슬롯 박스, 대형 음식 아이콘(48~60px), 고대비 상태 배지 및 14px 진행률 게이지 바를 렌더링한다."""
        r = self.rect
        is_mobile = bool(
            getattr(config, "is_mobile_ui", lambda: config.WINDOW_HEIGHT > config.WINDOW_WIDTH)()
        )
        if self.state == STATE_IDLE:
            bg_col = (40, 36, 56)
            border_col = (106, 98, 142)
            b_width = 2
        elif self.state == STATE_COOKING:
            bg_col = (64, 46, 32)
            border_col = config.GAUGE_COOKING
            b_width = 2
        elif self.state == STATE_READY:
            if self.can_burn and self.burn_progress >= 0.65:
                bg_col = (78, 36, 28)
                border_col = config.GAUGE_WARNING
            else:
                bg_col = (28, 68, 46)
                border_col = config.NEON_GREEN
            b_width = 3
        else:  # STATE_BURNT
            bg_col = (58, 22, 26)
            border_col = config.GAUGE_BURNT
            b_width = 3

        pygame.draw.rect(surface, bg_col, r, border_radius=12 if r.height >= 160 else 10)
        pygame.draw.rect(surface, border_col, r, width=b_width, border_radius=12 if r.height >= 160 else 10)

        is_giant_slot = r.width >= 180 and r.height >= 160
        if is_giant_slot:
            if self.state == STATE_IDLE:
                plus_rad = min(38, max(24, min(r.width, r.height) // 5))
                circle_c = (r.centerx, r.centery - 18)
                pygame.draw.circle(surface, (28, 24, 42), circle_c, plus_rad)
                pygame.draw.circle(surface, (148, 138, 196), circle_c, plus_rad, width=3)
                arm = max(10, plus_rad - 12)
                pygame.draw.line(surface, config.WHITE, (circle_c[0] - arm, circle_c[1]), (circle_c[0] + arm, circle_c[1]), 4)
                pygame.draw.line(surface, config.WHITE, (circle_c[0], circle_c[1] - arm), (circle_c[0], circle_c[1] + arm), 4)

                clean_lbl = empty_label.replace("클릭", "터치")
                f_idle = config.get_font(17, bold=True)
                lbl_s = f_idle.render(clean_lbl, True, (238, 234, 252))
                if lbl_s.get_width() > r.width - 16:
                    lbl_s = config.get_font(15, bold=True).render(clean_lbl, True, (238, 234, 252))
                pill_w = min(r.width - 12, lbl_s.get_width() + 24)
                pill_r = pygame.Rect(r.centerx - pill_w // 2, circle_c[1] + plus_rad + 14, pill_w, 36)
                pygame.draw.rect(surface, (26, 22, 38), pill_r, border_radius=10)
                pygame.draw.rect(surface, (124, 114, 168), pill_r, width=2, border_radius=10)
                surface.blit(lbl_s, lbl_s.get_rect(center=pill_r.center))
                return

            if self.recipe_id:
                rec = RECIPES.get(self.recipe_id)
                r_nm = str(rec.get("name", self.recipe_id)) if rec else str(self.recipe_id)
                tag_w = (r.width - 56) if self.state == STATE_COOKING else (r.width - 16)
                name_tag = pygame.Rect(r.x + 8, r.y + 8, max(60, tag_w), 34)
                pygame.draw.rect(surface, (18, 15, 28), name_tag, border_radius=8)
                pygame.draw.rect(surface, config.GOLD if self.state == STATE_READY else config.UI_BORDER, name_tag, width=1, border_radius=8)
                nf = config.get_font(18, bold=True)
                for f_sz in (18, 17, 16, 15, 14):
                    nf = config.get_font(f_sz, bold=True)
                    if nf.size(r_nm)[0] <= name_tag.width - 10:
                        break
                ns = nf.render(r_nm, True, config.GOLD if self.state == STATE_READY else config.WHITE)
                surface.blit(ns, ns.get_rect(center=name_tag.center))

            icon_size = min(104, max(64, min(r.width, r.height) - 96))
            icon_center = (r.centerx, r.centery - 8)
            if self.state == STATE_READY:
                glow_col = config.GAUGE_WARNING if (self.can_burn and self.burn_progress >= 0.65) else config.GOLD
                pygame.draw.circle(surface, glow_col, icon_center, icon_size // 2 + 8, width=4)
            if self.recipe_id:
                draw_food_icon(surface, icon_center, self.recipe_id, size=icon_size, burnt=(self.state == STATE_BURNT))

            gauge_rect = pygame.Rect(r.x + 10, r.bottom - 26, r.width - 20, 18)
            pygame.draw.rect(surface, (18, 16, 26), gauge_rect, border_radius=8)
            if self.state == STATE_COOKING:
                fill_w = int((gauge_rect.width - 4) * self.progress)
                if fill_w > 0:
                    pygame.draw.rect(surface, config.GAUGE_COOKING, (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4), border_radius=6)
                label_txt = "🔄 지금 터치해 뒤집기!" if self.is_flip_ready else f"🔥 조리 중 ({int(self.progress * 100)}%)"
                label_col = config.GOLD if self.is_flip_ready else config.GAUGE_COOKING
                pill_bg = (52, 38, 18) if self.is_flip_ready else (34, 24, 16)
            elif self.state == STATE_READY:
                if self.can_burn:
                    rem_ratio = 1.0 - self.burn_progress
                    bar_col = config.GAUGE_WARNING if self.burn_progress >= 0.60 else config.NEON_GREEN
                    fill_w = int((gauge_rect.width - 4) * rem_ratio)
                else:
                    bar_col = config.NEON_GREEN
                    fill_w = gauge_rect.width - 4
                if fill_w > 0:
                    pygame.draw.rect(surface, bar_col, (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4), border_radius=6)
                is_warn = self.can_burn and self.burn_progress >= 0.65
                label_txt = "⚠️ 곧 탐! 즉시 터치!" if is_warn else "✨ 완성! 터치하여 서빙"
                label_col = config.GAUGE_WARNING if is_warn else config.NEON_GREEN
                pill_bg = (48, 20, 16) if is_warn else (16, 44, 28)
            else:
                pygame.draw.rect(surface, config.GAUGE_BURNT, (gauge_rect.x + 2, gauge_rect.y + 2, gauge_rect.width - 4, gauge_rect.height - 4), border_radius=6)
                label_txt = "💀 탔음! 터치하여 폐기"
                label_col = (255, 118, 118)
                pill_bg = (46, 16, 20)

            pygame.draw.rect(surface, (205, 202, 224), gauge_rect, width=2, border_radius=8)
            st_f = config.get_font(17, bold=True)
            st_surf = st_f.render(label_txt, True, label_col)
            if st_surf.get_width() > r.width - 16:
                st_surf = config.get_font(15, bold=True).render(label_txt, True, label_col)
            pill_w = min(r.width - 12, st_surf.get_width() + 20)
            st_pill = pygame.Rect(r.centerx - pill_w // 2, gauge_rect.top - 38, pill_w, 32)
            pygame.draw.rect(surface, pill_bg, st_pill, border_radius=8)
            pygame.draw.rect(surface, label_col, st_pill, width=2, border_radius=8)
            surface.blit(st_surf, st_surf.get_rect(center=st_pill.center))
            return

        if is_mobile:
            if self.state == STATE_IDLE:
                # 모바일: 안내 문구 없이 반투명 + 그래픽 아이콘만 표시
                plus_rad = min(20, max(14, min(r.width, r.height) // 4))
                pygame.draw.circle(surface, (28, 24, 42), r.center, plus_rad)
                pygame.draw.circle(surface, (132, 122, 174), r.center, plus_rad, width=2)
                arm = max(6, plus_rad - 6)
                pygame.draw.line(
                    surface,
                    (196, 188, 232),
                    (r.centerx - arm, r.centery),
                    (r.centerx + arm, r.centery),
                    3,
                )
                pygame.draw.line(
                    surface,
                    (196, 188, 232),
                    (r.centerx, r.centery - arm),
                    (r.centerx, r.centery + arm),
                    3,
                )
                return

            icon_size = min(54, max(44, min(r.width, r.height) - 24))
            icon_center = (r.centerx, r.centery + 2)

            if self.state == STATE_READY:
                # 완성: 황금빛 후광(Glow) + 체크/반짝임 그래픽
                glow_col = config.GAUGE_WARNING if (self.can_burn and self.burn_progress >= 0.65) else config.GOLD
                pygame.draw.circle(surface, glow_col, icon_center, icon_size // 2 + 4, width=3)

            if self.recipe_id:
                draw_food_icon(
                    surface,
                    icon_center,
                    self.recipe_id,
                    size=icon_size,
                    burnt=(self.state == STATE_BURNT),
                )
                rec = RECIPES.get(self.recipe_id)
                if rec:
                    r_nm = str(rec.get("name", self.recipe_id))
                    tag_w = (r.width - 34) if self.state == STATE_COOKING else (r.width - 10)
                    name_tag = pygame.Rect(r.x + 5, r.y + 4, max(36, tag_w), 18)
                    pygame.draw.rect(surface, (18, 15, 28), name_tag, border_radius=5)
                    nf = config.get_font(12, bold=True)
                    for f_sz in (12, 11, 10):
                        nf = config.get_font(f_sz, bold=True)
                        if nf.size(r_nm)[0] <= name_tag.width - 4:
                            break
                    ns = nf.render(r_nm, True, config.GOLD if self.state == STATE_READY else config.WHITE)
                    surface.blit(ns, ns.get_rect(center=name_tag.center))

            if self.state == STATE_READY:
                chk_center = (r.right - 14, r.y + 14)
                pygame.draw.circle(surface, (28, 168, 84), chk_center, 9)
                pygame.draw.circle(surface, config.WHITE, chk_center, 9, width=2)
                pygame.draw.lines(
                    surface,
                    config.WHITE,
                    False,
                    [
                        (chk_center[0] - 4, chk_center[1]),
                        (chk_center[0] - 1, chk_center[1] + 3),
                        (chk_center[0] + 5, chk_center[1] - 3),
                    ],
                    2,
                )
            elif self.state == STATE_BURNT:
                # 탄 상태: 해골/X 그래픽 표시
                x_center = (r.right - 14, r.y + 14)
                pygame.draw.circle(surface, (198, 36, 42), x_center, 9)
                pygame.draw.circle(surface, config.WHITE, x_center, 9, width=2)
                pygame.draw.line(
                    surface,
                    config.WHITE,
                    (x_center[0] - 4, x_center[1] - 4),
                    (x_center[0] + 4, x_center[1] + 4),
                    2,
                )
                pygame.draw.line(
                    surface,
                    config.WHITE,
                    (x_center[0] + 4, x_center[1] - 4),
                    (x_center[0] - 4, x_center[1] + 4),
                    2,
                )

            # 하단 두꺼운 컬러 게이지 바만 표시 (문구 생략)
            gauge_rect = pygame.Rect(r.x + 6, r.bottom - 16, r.width - 12, 12)
            pygame.draw.rect(surface, (18, 16, 26), gauge_rect, border_radius=6)
            if self.state == STATE_COOKING:
                fill_w = int((gauge_rect.width - 4) * self.progress)
                if fill_w > 0:
                    pygame.draw.rect(
                        surface,
                        config.GAUGE_COOKING,
                        (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                        border_radius=4,
                    )
            elif self.state == STATE_READY:
                if self.can_burn:
                    rem_ratio = 1.0 - self.burn_progress
                    bar_col = config.GAUGE_WARNING if self.burn_progress >= 0.60 else config.NEON_GREEN
                    fill_w = int((gauge_rect.width - 4) * rem_ratio)
                else:
                    bar_col = config.NEON_GREEN
                    fill_w = gauge_rect.width - 4
                if fill_w > 0:
                    pygame.draw.rect(
                        surface,
                        bar_col,
                        (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                        border_radius=4,
                    )
            else:
                pygame.draw.rect(
                    surface,
                    config.GAUGE_BURNT,
                    (gauge_rect.x + 2, gauge_rect.y + 2, gauge_rect.width - 4, gauge_rect.height - 4),
                    border_radius=4,
                )
            pygame.draw.rect(surface, (205, 202, 224), gauge_rect, width=2, border_radius=6)
            return

        font_md = config.get_font(14, bold=True)

        if self.state == STATE_IDLE:
            clean_lbl = empty_label.replace("클릭", "터치")
            if "➕" not in clean_lbl and "빈" in clean_lbl:
                clean_lbl = f"➕ {clean_lbl}"
            lbl = font_md.render(clean_lbl, True, (238, 234, 252))
            if lbl.get_width() > r.width - 8:
                lbl = config.get_font(13, bold=True).render(clean_lbl, True, (238, 234, 252))
            pill_w = min(r.width - 6, lbl.get_width() + 14)
            pill_r = pygame.Rect(r.centerx - pill_w // 2, r.centery - 14, pill_w, 28)
            pygame.draw.rect(surface, (26, 22, 38), pill_r, border_radius=8)
            pygame.draw.rect(surface, (118, 108, 156), pill_r, width=1, border_radius=8)
            surface.blit(lbl, (r.centerx - lbl.get_width() // 2, pill_r.centery - lbl.get_height() // 2))
            return

        icon_size = min(60, max(38, min(r.width, r.height) - 22))
        icon_center = (r.centerx, r.y + icon_size // 2 + 4)
        if self.recipe_id:
            draw_food_icon(
                surface,
                icon_center,
                self.recipe_id,
                size=icon_size,
                burnt=(self.state == STATE_BURNT),
            )

        # 하단 게이지 바 및 고대비 상태 필 배지 (모바일 시인성 강화: 게이지 두께 14px)
        gauge_rect = pygame.Rect(r.x + 6, r.bottom - 18, r.width - 12, 14)
        pygame.draw.rect(surface, (18, 16, 26), gauge_rect, border_radius=6)

        if self.state == STATE_COOKING:
            fill_w = int((gauge_rect.width - 4) * self.progress)
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    config.GAUGE_COOKING,
                    (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                    border_radius=4,
                )
            label_txt = "🔥 조리중..."
            label_col = config.GAUGE_COOKING
            pill_bg = (34, 24, 16)

        elif self.state == STATE_READY:
            if self.can_burn:
                rem_ratio = 1.0 - self.burn_progress
                bar_col = config.GAUGE_WARNING if self.burn_progress >= 0.60 else config.NEON_GREEN
                fill_w = int((gauge_rect.width - 4) * rem_ratio)
            else:
                bar_col = config.NEON_GREEN
                fill_w = gauge_rect.width - 4
            if fill_w > 0:
                pygame.draw.rect(
                    surface,
                    bar_col,
                    (gauge_rect.x + 2, gauge_rect.y + 2, fill_w, gauge_rect.height - 4),
                    border_radius=4,
                )
            is_warn = self.can_burn and self.burn_progress >= 0.65
            label_txt = "⚠️ 곧 탐! 터치!" if is_warn else "✨ 완성! 터치!"
            label_col = config.GAUGE_WARNING if is_warn else config.NEON_GREEN
            pill_bg = (48, 20, 16) if is_warn else (16, 44, 28)

        else:  # STATE_BURNT
            pygame.draw.rect(
                surface,
                config.GAUGE_BURNT,
                (gauge_rect.x + 2, gauge_rect.y + 2, gauge_rect.width - 4, gauge_rect.height - 4),
                border_radius=4,
            )
            label_txt = "💀 탔음! 폐기"
            label_col = (255, 118, 118)
            pill_bg = (46, 16, 20)

        pygame.draw.rect(surface, (205, 202, 224), gauge_rect, width=2, border_radius=6)

        st_surf = font_md.render(label_txt, True, label_col)
        if st_surf.get_width() > r.width - 8:
            st_surf = config.get_font(13, bold=True).render(label_txt, True, label_col)
        pill_w = min(r.width - 6, st_surf.get_width() + 12)
        st_pill = pygame.Rect(r.centerx - pill_w // 2, gauge_rect.top - 23, pill_w, 21)
        pygame.draw.rect(surface, pill_bg, st_pill, border_radius=6)
        pygame.draw.rect(surface, label_col, st_pill, width=1, border_radius=6)
        surface.blit(st_surf, (st_pill.centerx - st_surf.get_width() // 2, st_pill.centery - st_surf.get_height() // 2))


class BaseStation:
    """
    모든 조리 스테이션(MoldStation, GrillStation, BatchPotStation, DispenserStation)의 공통 부모 클래스.
    """

    def __init__(
        self,
        station_id: str,
        slot_type: str,
        rect: Union[pygame.Rect, Tuple[int, int, int, int]],
        game_mgr: Any = None,
    ) -> None:
        self.slot_type: str = str(slot_type)
        self.game_mgr: Any = game_mgr or GameManager.get_instance()
        self.rect: pygame.Rect = (
            rect.copy() if isinstance(rect, pygame.Rect) else pygame.Rect(rect)
        )
        self._last_layout_rect: pygame.Rect = self.rect.copy()
        self.slots: List[StationSlot] = []

        self.station_id: str = ""
        self.meta: Dict[str, Any] = {}
        self.name: str = ""
        self.short_name: str = ""
        self.country: str = "KR"
        self.set_station_id(station_id)

    @staticmethod
    def _parse_init_args(
        default_slot_type: str,
        default_station_id: str,
        default_rect: Tuple[int, int, int, int],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> Tuple[str, pygame.Rect, Any]:
        """
        다양한 생성자 호출 시그니처(rect 우선, station_id 우선, game_mgr 우선 등)를
        모두 호환하도록 파싱하는 헬퍼.
        """
        game_mgr = kwargs.get("game_mgr") or kwargs.get("manager")
        station_id = kwargs.get("station_id")
        rect = kwargs.get("rect")

        for arg in args:
            if isinstance(arg, str):
                station_id = station_id or arg
            elif isinstance(arg, pygame.Rect) or (
                isinstance(arg, (tuple, list)) and len(arg) == 4
            ):
                rect = rect or arg
            elif hasattr(arg, "get_active_stations"):
                game_mgr = game_mgr or arg

        mgr = game_mgr or GameManager.get_instance()
        if not station_id:
            if mgr and hasattr(mgr, "get_active_stations"):
                active = mgr.get_active_stations()
                station_id = str(active.get(default_slot_type, default_station_id))
            else:
                station_id = default_station_id

        final_rect = (
            rect.copy()
            if isinstance(rect, pygame.Rect)
            else pygame.Rect(rect if rect is not None else default_rect)
        )
        return str(station_id), final_rect, mgr

    def set_station_id(self, station_id: str) -> None:
        """장착된 조리 기구 ID를 설정하고 메타데이터 및 슬롯 구성을 갱신한다."""
        if station_id not in STATIONS_CATALOG:
            # 해당 슬롯 타입의 기본 한국 기구로 폴백
            defaults = {
                "mold": "kr_bungeoppang",
                "grill": "kr_skewer_grill",
                "batch_pot": "kr_tteokbokki_pan",
                "dispenser": "kr_odeng_dispenser",
            }
            station_id = defaults.get(self.slot_type, "kr_bungeoppang")

        self.station_id = str(station_id)
        self.meta = STATIONS_CATALOG[self.station_id]
        self.name = str(self.meta["name"])
        self.short_name = str(self.meta["short_name"])
        self.country = str(self.meta["country"])
        self._on_station_changed()
        self.sync_slots_with_manager()

    def _on_station_changed(self) -> None:
        """하위 클래스에서 기구 변경 시 레시피 목록 등을 갱신하기 위한 훅."""
        pass

    def _get_desired_slot_count(self) -> int:
        if self.slot_type == "batch_pot":
            return 1
        if self.game_mgr and hasattr(self.game_mgr, "get_station_slot_count"):
            return max(1, int(self.game_mgr.get_station_slot_count(self.slot_type)))
        return 2

    def sync_slots_with_manager(self) -> None:
        """
        GameManager의 활성 기구 및 업그레이드 레벨에 맞춰 슬롯 수를 동적으로 동기화한다.
        기존 슬롯의 조리 상태는 그대로 보존한다.
        """
        if self.game_mgr and hasattr(self.game_mgr, "get_active_stations"):
            active_id = str(self.game_mgr.get_active_stations().get(self.slot_type, self.station_id))
            if active_id in STATIONS_CATALOG and active_id != self.station_id:
                self.station_id = active_id
                self.meta = STATIONS_CATALOG[self.station_id]
                self.name = str(self.meta["name"])
                self.short_name = str(self.meta["short_name"])
                self.country = str(self.meta["country"])
                self._on_station_changed()

        desired = self._get_desired_slot_count()
        can_burn = self.slot_type not in ("dispenser", "batch_pot")

        while len(self.slots) < desired:
            idx = len(self.slots)
            self.slots.append(StationSlot(slot_index=idx, can_burn=can_burn))
        if len(self.slots) > desired:
            self.slots = self.slots[:desired]

        self._rebuild_layout()

    def _ensure_layout(self) -> None:
        if self.rect != self._last_layout_rect:
            self._last_layout_rect = self.rect.copy()
            self._rebuild_layout()

    def _rebuild_layout(self) -> None:
        """슬롯 및 버튼 좌표를 self.rect 기준으로 재계산한다."""
        self._last_layout_rect = self.rect.copy()

    def get_cook_time(self, recipe_id: str) -> float:
        """패시브 및 기구 업그레이드가 적용된 조리 시간을 반환한다."""
        if self.game_mgr and hasattr(self.game_mgr, "get_cook_time"):
            return float(self.game_mgr.get_cook_time(recipe_id, self.slot_type))
        rec = RECIPES.get(recipe_id)
        return float(rec["cook_time"]) if rec else 4.5

    def get_burn_time(self, recipe_id: str) -> float:
        """패시브 및 기구 업그레이드가 적용된 타는 시간을 반환한다."""
        if self.game_mgr and hasattr(self.game_mgr, "get_burn_time"):
            return float(self.game_mgr.get_burn_time(recipe_id, self.slot_type))
        rec = RECIPES.get(recipe_id)
        return float(rec["burn_time"]) if rec else 9.0

    def instant_finish_all(self) -> int:
        """
        현재 COOKING 상태인 모든 슬롯을 즉시 READY 상태로 완성한다 (켄지 액티브 스킬 연동용).
        완성된 슬롯의 개수를 반환한다.
        """
        finished_count = 0
        for slot in self.slots:
            if slot.instant_finish():
                finished_count += 1
        return finished_count

    def reset_all(self) -> None:
        """모든 슬롯을 초기 상태(IDLE)로 리셋한다."""
        for slot in self.slots:
            slot.reset()

    def update(self, dt: float) -> None:
        """모든 슬롯의 타이머를 업데이트한다."""
        for slot in self.slots:
            slot.update(dt)

    def draw_panel_frame(self, surface: pygame.Surface, subtitle: str = "") -> None:
        """조리대 패널 배경, 하드웨어 텍스처, 상단 기구 이름 헤더를 렌더링한다."""
        self._ensure_layout()
        is_giant = self.rect.height >= 500
        hdr_h = 54 if is_giant else 30
        pygame.draw.rect(surface, config.UI_PANEL_DARK, self.rect, border_radius=14 if is_giant else 12)
        hw_rect = pygame.Rect(
            self.rect.x + (8 if is_giant else 6),
            self.rect.y + hdr_h + (8 if is_giant else 6),
            self.rect.width - (16 if is_giant else 12),
            self.rect.height - hdr_h - (14 if is_giant else 12),
        )
        draw_station_hardware(
            surface,
            hw_rect,
            station_type=self.slot_type,
            station_id=self.station_id,
        )
        pygame.draw.rect(surface, config.UI_BORDER, self.rect, width=3 if is_giant else 2, border_radius=14 if is_giant else 12)

        # 상단 타이틀 바 (PC 단축키 접두어 없이 정중앙 15px 볼드 고대비, 모바일은 대표 음식 아이콘 + Lv 배지)
        header_rect = pygame.Rect(self.rect.x + (6 if is_giant else 4), self.rect.y + (6 if is_giant else 4), self.rect.width - (12 if is_giant else 8), hdr_h)
        header_col = self.meta.get("color", config.UI_PANEL_LIGHT)
        dark_header = (
            max(22, int(header_col[0] * 0.42)),
            max(22, int(header_col[1] * 0.42)),
            max(30, int(header_col[2] * 0.42)),
        )
        pygame.draw.rect(surface, dark_header, header_rect, border_radius=10 if is_giant else 8)
        pygame.draw.rect(surface, header_col, header_rect, width=2 if is_giant else 1, border_radius=10 if is_giant else 8)

        is_mobile = bool(
            getattr(config, "is_mobile_ui", lambda: config.WINDOW_HEIGHT > config.WINDOW_WIDTH)()
        )
        if is_giant or is_mobile:
            rep_rid = (
                getattr(self, "base_recipe_id", None)
                or getattr(self, "selected_recipe_id", None)
                or (getattr(self, "drink_recipes", [None])[0] if getattr(self, "drink_recipes", None) else None)
                or (self.slots[0].recipe_id if self.slots and self.slots[0].recipe_id else None)
                or {
                    "mold": "bungeoppang_redbean",
                    "grill": "skewer_plain",
                    "batch_pot": "tteokbokki_plain",
                    "dispenser": "odeng_soup",
                }.get(self.slot_type, "bungeoppang_redbean")
            )
            lvl = (
                int(self.game_mgr.get_station_level(self.slot_type))
                if (self.game_mgr and hasattr(self.game_mgr, "get_station_level"))
                else 1
            )
            if is_giant:
                draw_food_icon(surface, (header_rect.x + 32, header_rect.centery), str(rep_rid), size=44, burnt=False)
                full_nm = self.name or self.short_name
                if subtitle:
                    full_nm = f"{full_nm} ({subtitle})"
                nm_s = config.get_font(22, bold=True).render(full_nm, True, config.GOLD)
                surface.blit(nm_s, (header_rect.x + 62, header_rect.centery - nm_s.get_height() // 2))
                lv_badge = pygame.Rect(header_rect.right - 88, header_rect.y + 8, 78, 38)
                pygame.draw.rect(surface, (18, 16, 28), lv_badge, border_radius=8)
                pygame.draw.rect(surface, config.GOLD, lv_badge, width=2, border_radius=8)
                lv_s = config.get_font(18, bold=True).render(f"Lv.{lvl}", True, config.GOLD)
                surface.blit(lv_s, lv_s.get_rect(center=lv_badge.center))
                return

            draw_food_icon(surface, (header_rect.x + 18, header_rect.centery), str(rep_rid), size=24, burnt=False)
            short_nm = self.short_name or self.name
            nm_s = config.get_font(13, bold=True).render(short_nm, True, config.GOLD)
            surface.blit(nm_s, (header_rect.x + 34, header_rect.centery - nm_s.get_height() // 2))
            lv_badge = pygame.Rect(header_rect.right - 46, header_rect.y + 4, 40, 22)
            pygame.draw.rect(surface, (18, 16, 28), lv_badge, border_radius=6)
            pygame.draw.rect(surface, config.GOLD, lv_badge, width=1, border_radius=6)
            lv_s = config.get_font(12, bold=True).render(f"Lv.{lvl}", True, config.GOLD)
            surface.blit(lv_s, lv_s.get_rect(center=lv_badge.center))
            return

        title_font = config.get_font(15, bold=True)
        title_txt = self.short_name or self.name
        if subtitle:
            title_txt = f"{title_txt} ({subtitle})"
        for f_sz in (15, 14, 13):
            title_font = config.get_font(f_sz, bold=True)
            if title_font.size(title_txt)[0] <= header_rect.width - 10:
                break
        sh_surf = title_font.render(title_txt, True, (12, 10, 18))
        title_surf = title_font.render(title_txt, True, config.GOLD)
        tx = header_rect.centerx - title_surf.get_width() // 2
        ty = header_rect.centery - title_surf.get_height() // 2
        surface.blit(sh_surf, (tx + 1, ty + 1))
        surface.blit(title_surf, (tx, ty))

    def draw(
        self,
        surface: pygame.Surface,
        time_tick: Any = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """스테이션과 슬롯들을 화면에 렌더링한다."""
        t = float(time_tick) if isinstance(time_tick, (int, float)) else 0.0
        self.draw_panel_frame(surface)
        for slot in self.slots:
            slot.draw_slot_box(surface, time_tick=t)

    def handle_click(
        self,
        pos: Tuple[int, int],
        assembly_tray: Any = None,
        auto_serve_cb: Optional[Callable[..., Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """마우스 클릭 입력을 처리한다. 하위 클래스에서 구체적으로 구현한다."""
        return None
