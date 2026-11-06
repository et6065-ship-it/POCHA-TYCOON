"""
core/effects.py
'전세계 길거리 음식 포차 타이쿤' 비주얼 이펙트 및 프로시저럴 사운드 모듈.
- FloatingText: 화면에 떠오르며 페이드아웃되는 텍스트 (+4,500원!, COMBO x3!, 스킬 발동 등)
- FlyingDishEffect: 원클릭 자동 서빙 시 조리대/트레이에서 손님에게 포물선으로 날아가는 음식 애니메이션
- ParticleSystem: 조리 연기, 그릴 불꽃, 황금 별/하트 파티클, 스킬 오라 이펙트
- SoundFX: 외부 오디오 파일 없이 수학적 파형(사인파/화음/노이즈)으로 합성하는 프로시저럴 효과음
"""

from __future__ import annotations

import array
import math
import os
import random
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pygame

import config
from core import art_renderer


# ==============================================================================
# 1. FloatingText (떠오르는 텍스트 이펙트)
# ==============================================================================
class FloatingText:
    """
    서빙 매출, 콤보 알림, 스킬 발동, 탄 음식 폐기 등 화면에 떠올랐다가 사라지는 텍스트.
    다양한 호출 시그니처(FloatingText(text, x, y), FloatingText(text, (x, y)), FloatingText(x, y, text))를 모두 호환한다.
    """

    def __init__(
        self,
        arg1: Union[str, float, Tuple[float, float]],
        arg2: Union[float, Tuple[float, float], str] = 0.0,
        arg3: Optional[Union[float, Tuple[int, int, int]]] = None,
        color: Tuple[int, int, int] = config.GOLD,
        duration: float = 1.2,
        size: int = 22,
        vy: float = -52.0,
        bold: bool = True,
        outline_color: Tuple[int, int, int] = (18, 14, 24),
    ) -> None:
        # 유연한 인자 파싱
        if isinstance(arg1, str):
            self.text: str = arg1
            if isinstance(arg2, (tuple, list)) and len(arg2) >= 2:
                self.x: float = float(arg2[0])
                self.y: float = float(arg2[1])
                if isinstance(arg3, (tuple, list)) and len(arg3) >= 3:
                    color = (int(arg3[0]), int(arg3[1]), int(arg3[2]))
            else:
                self.x = float(arg2) if isinstance(arg2, (int, float)) else float(config.SCREEN_WIDTH // 2)
                self.y = float(arg3) if isinstance(arg3, (int, float)) else float(config.SCREEN_HEIGHT // 2)
        elif isinstance(arg1, (tuple, list)) and len(arg1) >= 2:
            self.x = float(arg1[0])
            self.y = float(arg1[1])
            self.text = str(arg2)
            if isinstance(arg3, (tuple, list)) and len(arg3) >= 3:
                color = (int(arg3[0]), int(arg3[1]), int(arg3[2]))
        else:
            # FloatingText(x, y, text) 형태 호출 대응
            self.x = float(arg1)
            self.y = float(arg2) if isinstance(arg2, (int, float)) else 0.0
            self.text = str(arg3 or "")

        self.start_x: float = self.x
        self.start_y: float = self.y
        self.color: Tuple[int, int, int] = (int(color[0]), int(color[1]), int(color[2]))
        self.outline_color: Tuple[int, int, int] = outline_color
        self.duration: float = max(0.2, float(duration))
        self.max_duration: float = self.duration
        self.elapsed: float = 0.0
        self.size: int = max(12, int(size))
        self.vy: float = float(vy)
        self.vx: float = 0.0
        self.bold: bool = bool(bold)
        self.alive: bool = True

        # 사전 렌더링 통합 서피스 캐싱 (외곽선 + 본문 1장으로 합성하여 프레임당 할당 0회)
        self._combined_surf: Optional[pygame.Surface] = None
        self._prepare_surfaces()

    def _prepare_surfaces(self) -> None:
        try:
            font = config.get_font(self.size, bold=self.bold)
            main_s = font.render(self.text, True, self.color)
            out_s = font.render(self.text, True, self.outline_color)
            w, h = main_s.get_width() + 6, main_s.get_height() + 6
            comb = pygame.Surface((w, h), pygame.SRCALPHA)
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (1, 2)):
                comb.blit(out_s, (3 + ox, 3 + oy))
            comb.blit(main_s, (3, 3))
            self._combined_surf = comb
        except Exception:
            self._combined_surf = None

    @property
    def alpha(self) -> int:
        if self.duration <= 0:
            return 0
        progress = self.elapsed / self.duration
        if progress < 0.6:
            return 255
        fade = 1.0 - (progress - 0.6) / 0.4
        return max(0, min(255, int(255 * fade)))

    def update(self, dt: float) -> bool:
        if not self.alive:
            return False
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.alive = False
            return False

        # 초반에는 빠르게 올라가고 후반에는 감속하는 이징
        progress = self.elapsed / self.duration
        damping = max(0.25, 1.0 - progress * 0.65)
        self.y += self.vy * damping * dt
        self.x += self.vx * dt
        return True

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        if self._combined_surf is None:
            self._prepare_surfaces()
        if self._combined_surf is None:
            return

        cur_alpha = self.alpha
        if cur_alpha <= 0:
            return

        self._combined_surf.set_alpha(cur_alpha)
        cx = int(self.x - self._combined_surf.get_width() // 2)
        cy = int(self.y - self._combined_surf.get_height() // 2)
        surface.blit(self._combined_surf, (cx, cy))


# ==============================================================================
# 2. FlyingDishEffect (원클릭 자동 서빙 포물선 비행 애니메이션)
# ==============================================================================
class FlyingDishEffect:
    """
    원클릭 자동 서빙 시 조리대/트레이 좌표(start_pos)에서 손님 좌표(target_pos)로
    아름다운 포물선을 그리며 날아가는 음식 아이콘 애니메이션.
    """

    def __init__(
        self,
        recipe_id: Union[str, Tuple[float, float]],
        start_pos: Union[Tuple[float, float], Tuple[int, int]],
        target_pos: Union[Tuple[float, float], Tuple[int, int], str],
        duration: float = 0.36,
        arc_height: float = 95.0,
        size: int = 50,
        on_arrive: Optional[Callable[[], Any]] = None,
        callback: Optional[Callable[[], Any]] = None,
    ) -> None:
        # 만약 (start_pos, target_pos, recipe_id) 순서로 호출된 경우 자동 보정
        if isinstance(recipe_id, (tuple, list)) and isinstance(target_pos, str):
            actual_recipe = str(target_pos)
            actual_start = (float(recipe_id[0]), float(recipe_id[1]))
            actual_target = (float(start_pos[0]), float(start_pos[1]))  # type: ignore[index]
        else:
            actual_recipe = str(recipe_id)
            actual_start = (float(start_pos[0]), float(start_pos[1]))  # type: ignore[index]
            actual_target = (float(target_pos[0]), float(target_pos[1]))  # type: ignore[index]

        self.recipe_id: str = actual_recipe
        self.start_pos: Tuple[float, float] = actual_start
        self.target_pos: Tuple[float, float] = actual_target
        self.x: float = actual_start[0]
        self.y: float = actual_start[1]
        self.duration: float = max(0.12, float(duration))
        self.arc_height: float = float(arc_height)
        self.size: int = max(24, int(size))
        self.elapsed: float = 0.0
        self.alive: bool = True
        self.on_arrive: Optional[Callable[[], Any]] = on_arrive or callback
        self._callback_fired: bool = False
        self.trail: List[Tuple[float, float]] = [actual_start]

    @property
    def progress(self) -> float:
        return max(0.0, min(1.0, self.elapsed / self.duration))

    def update(self, dt: float) -> bool:
        if not self.alive:
            return False

        self.elapsed += dt
        t = self.progress

        # 부드러운 ease-out 보간
        smooth_t = 1.0 - (1.0 - t) * (1.0 - t)
        bx = self.start_pos[0] + (self.target_pos[0] - self.start_pos[0]) * smooth_t
        by = self.start_pos[1] + (self.target_pos[1] - self.start_pos[1]) * smooth_t

        # 포물선 높이 오프셋: y_arc = -4 * H * t * (1 - t)
        parabola = -4.0 * self.arc_height * t * (1.0 - t)
        self.x = bx
        self.y = by + parabola

        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)

        if self.elapsed >= self.duration:
            self.alive = False
            if not self._callback_fired and self.on_arrive is not None:
                self._callback_fired = True
                try:
                    self.on_arrive()
                except Exception:
                    pass
            return False
        return True

    _halo_cache: Dict[int, pygame.Surface] = {}
    _trail_cache: Dict[Tuple[int, int], pygame.Surface] = {}

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return

        # 궤적 잔상 글로우 (캐싱된 원형 서피스 재사용)
        for idx, (tx, ty) in enumerate(self.trail[:-1]):
            ratio = (idx + 1) / float(len(self.trail))
            r = max(3, int(self.size * 0.22 * ratio))
            q_alpha = max(16, (int(110 * ratio) // 16) * 16)
            t_key = (r, q_alpha)
            glow = self._trail_cache.get(t_key)
            if glow is None:
                glow = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 225, 110, q_alpha), (r + 2, r + 2), r)
                if len(self._trail_cache) > 64:
                    self._trail_cache.clear()
                self._trail_cache[t_key] = glow
            surface.blit(glow, (int(tx - r - 2), int(ty - r - 2)))

        cx, cy = int(self.x), int(self.y)

        # 황금빛 후광 + 접시 받침 (고정 사이즈 캐싱으로 프레임당 메모리 할당 0회)
        plate_r = max(12, int(self.size * 0.50))
        halo = self._halo_cache.get(plate_r)
        if halo is None:
            halo = pygame.Surface((plate_r * 2 + 12, plate_r * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 215, 70, 95), (plate_r + 6, plate_r + 6), plate_r + 4)
            pygame.draw.circle(halo, (255, 250, 235, 220), (plate_r + 6, plate_r + 6), int(plate_r * 0.78))
            pygame.draw.circle(halo, (235, 195, 95, 240), (plate_r + 6, plate_r + 6), int(plate_r * 0.78), width=2)
            self._halo_cache[plate_r] = halo
        surface.blit(halo, (cx - plate_r - 6, cy - plate_r - 6))

        # 음식 아이콘 렌더링 (self.size 고정으로 ArtRenderer._food_cache 100% 적중)
        art_renderer.draw_food_icon(surface, (cx, cy), self.recipe_id, size=self.size)


# ==============================================================================
# 3. Particle & ParticleSystem (연기, 불꽃, 별, 하트, 스킬 오라 파티클)
# ==============================================================================
class Particle:
    """개별 파티클 단위 객체."""

    _surf_cache: Dict[Tuple[str, int, Tuple[int, int, int], int], pygame.Surface] = {}

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        size: float = 6.0,
        lifetime: float = 0.8,
        shape: str = "circle",
        gravity: float = 0.0,
        grow_rate: float = 0.0,
    ) -> None:
        self.x: float = float(x)
        self.y: float = float(y)
        self.vx: float = float(vx)
        self.vy: float = float(vy)
        self.color: Tuple[int, int, int] = (int(color[0]), int(color[1]), int(color[2]))
        self.size: float = max(1.5, float(size))
        self.lifetime: float = max(0.1, float(lifetime))
        self.max_lifetime: float = self.lifetime
        self.elapsed: float = 0.0
        self.shape: str = shape
        self.gravity: float = float(gravity)
        self.grow_rate: float = float(grow_rate)
        self.alive: bool = True
        self.rotation: float = random.uniform(0.0, math.pi * 2)
        self.rot_speed: float = random.uniform(-4.0, 4.0)

    def update(self, dt: float) -> bool:
        if not self.alive:
            return False
        self.elapsed += dt
        if self.elapsed >= self.lifetime:
            self.alive = False
            return False

        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.size = max(1.0, self.size + self.grow_rate * dt)
        self.rotation += self.rot_speed * dt
        return True

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        ratio = 1.0 - (self.elapsed / self.max_lifetime)
        alpha = max(0, min(255, int(255 * ratio)))
        if alpha <= 5:
            return

        r = max(1, int(self.size))
        cx, cy = int(self.x), int(self.y)

        if self.shape == "smoke":
            smoke_alpha = max(16, min(160, (int(130 * ratio) // 16) * 16))
            s_key = ("smoke", r, self.color, smoke_alpha)
            smoke_surf = self._surf_cache.get(s_key)
            if smoke_surf is None:
                smoke_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(smoke_surf, (*self.color, smoke_alpha), (r + 2, r + 2), r)
                if len(self._surf_cache) > 256:
                    self._surf_cache.clear()
                self._surf_cache[s_key] = smoke_surf
            surface.blit(smoke_surf, (cx - r - 2, cy - r - 2))

        elif self.shape == "star":
            pts: List[Tuple[int, int]] = []
            num_points = 5
            for i in range(num_points * 2):
                ang = self.rotation + i * (math.pi / num_points)
                rad = r if i % 2 == 0 else max(2, int(r * 0.45))
                pts.append((int(cx + math.cos(ang) * rad), int(cy + math.sin(ang) * rad)))
            if len(pts) >= 3:
                pygame.draw.polygon(surface, self.color, pts)
                pygame.draw.polygon(surface, (255, 255, 240), pts, width=1)

        elif self.shape == "heart":
            hr = max(2, int(r * 0.55))
            pygame.draw.circle(surface, self.color, (cx - hr // 2, cy - hr // 3), hr)
            pygame.draw.circle(surface, self.color, (cx + hr // 2, cy - hr // 3), hr)
            pygame.draw.polygon(
                surface,
                self.color,
                [(cx - hr - 1, cy - hr // 4), (cx + hr + 1, cy - hr // 4), (cx, cy + hr + 2)],
            )

        elif self.shape == "ring":
            q_alpha = max(16, (alpha // 16) * 16)
            r_key = ("ring", r, self.color, q_alpha)
            ring_surf = self._surf_cache.get(r_key)
            if ring_surf is None:
                ring_surf = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*self.color, q_alpha), (r + 3, r + 3), r, width=max(2, r // 5))
                if len(self._surf_cache) > 256:
                    self._surf_cache.clear()
                self._surf_cache[r_key] = ring_surf
            surface.blit(ring_surf, (cx - r - 3, cy - r - 3))

        else:
            # 기본 원형/불꽃 파티클
            q_alpha = max(16, (alpha // 16) * 16)
            c_key = ("circle", r, self.color, q_alpha)
            p_surf = self._surf_cache.get(c_key)
            if p_surf is None:
                p_surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*self.color, q_alpha), (r + 1, r + 1), r)
                if len(self._surf_cache) > 256:
                    self._surf_cache.clear()
                self._surf_cache[c_key] = p_surf
            surface.blit(p_surf, (cx - r - 1, cy - r - 1))


class ParticleSystem:
    """
    조리 연기, 그릴 불꽃, 서빙 성공 시 황금 별/하트, 스킬 오라 및
    FloatingText / FlyingDishEffect까지 통합 관리할 수 있는 파티클 & 이펙트 매니저.
    """

    def __init__(self) -> None:
        self.particles: List[Particle] = []
        self.floating_texts: List[FloatingText] = []
        self.flying_dishes: List[FlyingDishEffect] = []

    def clear(self) -> None:
        self.particles.clear()
        self.floating_texts.clear()
        self.flying_dishes.clear()

    # ------------------------------------------------------------------
    # 파티클 방출 메서드
    # ------------------------------------------------------------------
    def emit_smoke(
        self,
        x: float,
        y: float,
        count: int = 2,
        color: Tuple[int, int, int] = (215, 220, 230),
    ) -> None:
        """조리 중 모락모락 피어오르는 연기 파티클."""
        for _ in range(count):
            px = x + random.uniform(-12, 12)
            py = y + random.uniform(-6, 6)
            vx = random.uniform(-14, 14)
            vy = random.uniform(-45, -22)
            sz = random.uniform(5.0, 9.0)
            life = random.uniform(0.55, 0.95)
            self.particles.append(
                Particle(px, py, vx, vy, color, size=sz, lifetime=life, shape="smoke", grow_rate=8.0)
            )

    def emit_burn(self, x: float, y: float, count: int = 6) -> None:
        """음식이 탔을 때 검은 연기 & 붉은 불티 파티클."""
        for i in range(count):
            col = (55, 50, 55) if i % 2 == 0 else (225, 70, 40)
            shape = "smoke" if i % 2 == 0 else "circle"
            self.particles.append(
                Particle(
                    x + random.uniform(-14, 14),
                    y + random.uniform(-8, 8),
                    random.uniform(-28, 28),
                    random.uniform(-65, -25),
                    col,
                    size=random.uniform(6.0, 11.0),
                    lifetime=random.uniform(0.5, 0.9),
                    shape=shape,
                    grow_rate=6.0 if shape == "smoke" else -3.0,
                )
            )

    def emit_flame(self, x: float, y: float, count: int = 5) -> None:
        """직화 그릴/철판의 불꽃 스파크 파티클."""
        flame_colors = [
            (255, 220, 65),
            (255, 145, 35),
            (245, 75, 35),
            (255, 245, 150),
        ]
        for _ in range(count):
            col = random.choice(flame_colors)
            self.particles.append(
                Particle(
                    x + random.uniform(-14, 14),
                    y + random.uniform(-6, 6),
                    random.uniform(-35, 35),
                    random.uniform(-85, -35),
                    col,
                    size=random.uniform(4.0, 7.5),
                    lifetime=random.uniform(0.30, 0.60),
                    shape="circle",
                    gravity=40.0,
                    grow_rate=-5.0,
                )
            )

    # 별칭
    emit_fire = emit_flame
    emit_sparks = emit_flame

    def emit_stars(
        self,
        x: float,
        y: float,
        count: int = 10,
        color: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        """서빙 성공 시 황금 별/하트/빛망울 폭죽 파티클."""
        palette = [
            config.GOLD,
            (255, 240, 110),
            (255, 130, 185),
            (95, 235, 255),
            (110, 250, 145),
        ]
        for i in range(count):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(45, 145)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd - 35.0
            col = color if color is not None else palette[i % len(palette)]
            shp = "heart" if (i % 5 == 0 and color is None) else "star"
            self.particles.append(
                Particle(
                    x + random.uniform(-6, 6),
                    y + random.uniform(-6, 6),
                    vx,
                    vy,
                    col,
                    size=random.uniform(6.0, 10.5),
                    lifetime=random.uniform(0.45, 0.85),
                    shape=shp,
                    gravity=140.0,
                    grow_rate=-3.0,
                )
            )

    # 별칭 호환
    emit_serve_success = emit_stars
    emit_star_burst = emit_stars
    emit_gold = emit_stars

    def emit_hearts(self, x: float, y: float, count: int = 6) -> None:
        """손님 만족/인내심 회복 시 떠오르는 핑크 하트 파티클."""
        for _ in range(count):
            self.particles.append(
                Particle(
                    x + random.uniform(-18, 18),
                    y + random.uniform(-10, 10),
                    random.uniform(-22, 22),
                    random.uniform(-75, -40),
                    (255, 95, 155),
                    size=random.uniform(6.5, 10.0),
                    lifetime=random.uniform(0.6, 1.0),
                    shape="heart",
                )
            )

    def emit_skill_aura(
        self,
        x: float,
        y: float,
        color: Tuple[int, int, int] = config.NEON_YELLOW,
        count: int = 16,
    ) -> None:
        """주인공 액티브 스킬 발동 시 확장되는 오라 링 & 스타 파티클."""
        self.particles.append(
            Particle(x, y, 0.0, 0.0, color, size=14.0, lifetime=0.55, shape="ring", grow_rate=135.0)
        )
        for i in range(count):
            ang = (math.pi * 2 * i) / max(1, count) + random.uniform(-0.15, 0.15)
            spd = random.uniform(60, 160)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color if i % 2 == 0 else (255, 250, 210),
                    size=random.uniform(6.0, 10.0),
                    lifetime=random.uniform(0.45, 0.80),
                    shape="star",
                )
            )

    def emit(
        self,
        x: float,
        y: float,
        kind: str = "star",
        count: int = 8,
        color: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        """범용 파티클 방출 인터페이스."""
        k = (kind or "star").lower()
        if "smoke" in k:
            self.emit_smoke(x, y, count=count, color=color or (215, 220, 230))
        elif "burn" in k:
            self.emit_burn(x, y, count=count)
        elif "flame" in k or "fire" in k or "spark" in k:
            self.emit_flame(x, y, count=count)
        elif "heart" in k:
            self.emit_hearts(x, y, count=count)
        elif "skill" in k or "aura" in k:
            self.emit_skill_aura(x, y, color=color or config.NEON_YELLOW, count=count)
        else:
            self.emit_stars(x, y, count=count, color=color)

    # ------------------------------------------------------------------
    # 플로팅 텍스트 & 비행 디쉬 통합 관리 헬퍼
    # ------------------------------------------------------------------
    def spawn_floating_text(
        self,
        text: str,
        x: Union[float, Tuple[float, float]],
        y: Optional[float] = None,
        color: Tuple[int, int, int] = config.GOLD,
        size: int = 22,
        duration: float = 1.2,
    ) -> FloatingText:
        if isinstance(x, (tuple, list)):
            ft = FloatingText(text, float(x[0]), float(x[1]), color=color, duration=duration, size=size)
        else:
            ft = FloatingText(text, float(x), float(y or 0.0), color=color, duration=duration, size=size)
        self.floating_texts.append(ft)
        return ft

    add_floating_text = spawn_floating_text
    add_text = spawn_floating_text

    def spawn_flying_dish(
        self,
        recipe_id: str,
        start_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        duration: float = 0.36,
        on_arrive: Optional[Callable[[], Any]] = None,
    ) -> FlyingDishEffect:
        fd = FlyingDishEffect(
            recipe_id=recipe_id,
            start_pos=start_pos,
            target_pos=target_pos,
            duration=duration,
            on_arrive=on_arrive,
        )
        self.flying_dishes.append(fd)
        return fd

    add_flying_dish = spawn_flying_dish

    # ------------------------------------------------------------------
    # 업데이트 & 렌더링
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]
        self.flying_dishes = [d for d in self.flying_dishes if d.update(dt)]
        self.floating_texts = [t for t in self.floating_texts if t.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(surface)
        for d in self.flying_dishes:
            d.draw(surface)
        for t in self.floating_texts:
            t.draw(surface)


# ==============================================================================
# 4. SoundFX (프로시저럴 파형 합성 & assets/sounds/*.wav 사운드 시스템)
# ==============================================================================
class SoundFX:
    """
    메인 타이틀부터 각 조리 화구(몰드/그릴/대량팬/디스펜서/트레이), 손님 입장(일반/VIP)·불만·서빙까지
    모든 게임 사운드와 씬별 배경음악(BGM)을 합성·재생하는 사운드 매니저.
    - assets/sounds/*.wav 파일이 있으면 우선 로드하고, 없으면 즉석에서 고품질 PCM 파형을 합성 및 저장한다.
    - 오디오 장치가 없는 헤드리스(Headless) 환경에서도 절대 예외가 발생하지 않는다.
    """

    _instance: Optional["SoundFX"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "SoundFX":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized: bool = True
        self.enabled: bool = True
        self.bgm_enabled: bool = True
        self.master_volume: float = 0.85
        self.sfx_volume: float = 0.85
        self.bgm_volume: float = 0.55
        self.volume: float = 0.85
        self._cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self._bgm_cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self._bgm_sound: Optional[pygame.mixer.Sound] = None
        self._bgm_playing: bool = False
        self._current_bgm_track: str = "title"
        self._mixer_ready: bool = False
        self._web_audio_ready: bool = False
        self._user_gesture_unlocked: bool = False
        self._last_play_ticks: Dict[str, int] = {}
        self.sounds_dir: str = os.path.join(config.BASE_DIR, "assets", "sounds") if hasattr(config, "BASE_DIR") else "assets/sounds"
        self._init_mixer_safely()

    def _init_web_audio_bridge(self) -> bool:
        """웹 브라우저(Pygbag/Emscripten) 환경에서 Autoplay 차단을 우회하고 직접 사운드를 합성·재생하는 WebAudio 브릿지를 주입한다."""
        if sys.platform != "emscripten":
            return False
        if self._web_audio_ready:
            return True
        try:
            import platform
            js_code = r"""
            (function() {
                if (window.__pochaAudio) return true;
                window.__pochaAudioContexts = window.__pochaAudioContexts || [];
                var OrigAudioCtx = window.AudioContext || window.webkitAudioContext;
                if (OrigAudioCtx && !window.__pochaCtxHooked) {
                    window.__pochaCtxHooked = true;
                    var PatchedCtx = function() {
                        var instance = new (Function.prototype.bind.apply(OrigAudioCtx, [null].concat(Array.prototype.slice.call(arguments))))();
                        window.__pochaAudioContexts.push(instance);
                        return instance;
                    };
                    PatchedCtx.prototype = OrigAudioCtx.prototype;
                    window.AudioContext = PatchedCtx;
                    if (window.webkitAudioContext) window.webkitAudioContext = PatchedCtx;
                }

                window.__pochaAudio = {
                    ctx: null,
                    buffers: {},
                    bgmSource: null,
                    bgmGain: null,
                    currentTrack: "",
                    bgmVol: 0.45,
                    pendingBgm: null,

                    ensureCtx: function() {
                        if (!this.ctx && OrigAudioCtx) {
                            try {
                                this.ctx = new OrigAudioCtx();
                                window.__pochaAudioContexts.push(this.ctx);
                            } catch (e) {}
                        }
                        if (this.ctx && this.ctx.state === "suspended") {
                            try { this.ctx.resume(); } catch (e) {}
                        }
                        return this.ctx;
                    },

                    unlock: function() {
                        var ctx = this.ensureCtx();
                        for (var i = 0; i < window.__pochaAudioContexts.length; i++) {
                            var c = window.__pochaAudioContexts[i];
                            if (c && c.state === "suspended") {
                                try { c.resume(); } catch (e) {}
                            }
                        }
                        if (window.SDL2 && window.SDL2.audioContext && window.SDL2.audioContext.state === "suspended") {
                            try { window.SDL2.audioContext.resume(); } catch (e) {}
                        }
                        if (this.pendingBgm && ctx) {
                            var p = this.pendingBgm;
                            this.pendingBgm = null;
                            this.playBgm(p.track, p.notesJson, p.baseVol, p.effVol);
                        }
                    },

                    buildBuffer: function(key, notes, baseVol) {
                        if (this.buffers[key]) return this.buffers[key];
                        var ctx = this.ensureCtx();
                        if (!ctx) return null;
                        var sr = ctx.sampleRate || 44100;
                        var totalSamples = 0;
                        for (var n = 0; n < notes.length; n++) {
                            totalSamples += Math.max(1, Math.floor(sr * notes[n][1]));
                        }
                        if (totalSamples <= 0) return null;
                        var buf = ctx.createBuffer(1, totalSamples, sr);
                        var data = buf.getChannelData(0);
                        var amp = Math.max(0.05, Math.min(1.0, baseVol));
                        var offset = 0;
                        var seed = 20261106;
                        function nextRand() {
                            seed = (seed * 1664525 + 1013904223) & 0xffffffff;
                            return ((seed >>> 0) / 4294967296.0) * 2.0 - 1.0;
                        }
                        for (var n = 0; n < notes.length; n++) {
                            var freq = notes[n][0];
                            var dur = notes[n][1];
                            var wtype = notes[n][2];
                            var nSamp = Math.max(1, Math.floor(sr * dur));
                            for (var i = 0; i < nSamp; i++) {
                                var t = i / sr;
                                var prog = i / nSamp;
                                var env = 1.0;
                                if (wtype === "bell" || wtype === "metallic") {
                                    env = Math.min(1.0, prog / 0.015) * Math.exp(-3.8 * prog);
                                } else if (wtype === "sizzle" || wtype === "bubble" || wtype === "pour") {
                                    if (prog < 0.06) env = prog / 0.06;
                                    else if (prog > 0.85) env = Math.max(0.0, (1.0 - prog) / 0.15);
                                } else {
                                    if (prog < 0.08) env = prog / 0.08;
                                    else env = Math.max(0.0, 1.0 - Math.pow((prog - 0.08) / 0.92, 0.85));
                                }
                                var val = 0.0;
                                var twoPiF = 2.0 * Math.PI * freq;
                                if (wtype === "noise") {
                                    val = nextRand() * Math.sin(twoPiF * t);
                                } else if (wtype === "sizzle") {
                                    var nr = nextRand();
                                    var mod = 0.65 * Math.sin(twoPiF * t) + 0.35 * Math.sin(twoPiF * 2.3 * t);
                                    val = Math.max(-1.0, Math.min(1.0, nr * mod));
                                } else if (wtype === "bubble") {
                                    var bc = (t * 14.0) % 1.0;
                                    var bf = freq * (0.85 + 0.65 * Math.pow(bc, 1.5));
                                    val = 0.82 * Math.sin(2.0 * Math.PI * bf * t) * Math.sin(Math.PI * bc) + nextRand() * 0.18;
                                } else if (wtype === "pour") {
                                    var cf = freq * (0.78 + 0.52 * prog + 0.06 * Math.sin(2.0 * Math.PI * 18.0 * t));
                                    val = 0.78 * Math.sin(2.0 * Math.PI * cf * t) + nextRand() * 0.22;
                                } else if (wtype === "bell") {
                                    val = 0.58 * Math.sin(twoPiF * t) + 0.26 * Math.sin(twoPiF * 2.0 * t) + 0.16 * Math.sin(twoPiF * 2.756 * t);
                                } else if (wtype === "metallic") {
                                    var thud = Math.sin(twoPiF * 0.45 * t) * Math.exp(-12.0 * prog);
                                    var clank = 0.45 * Math.sin(twoPiF * t) + 0.35 * Math.sin(twoPiF * 1.62 * t) + 0.20 * nextRand();
                                    val = Math.max(-1.0, Math.min(1.0, 0.55 * thud + 0.45 * clank));
                                } else if (wtype === "square") {
                                    val = Math.sin(twoPiF * t) >= 0 ? 0.65 : -0.65;
                                } else if (wtype === "slide_up") {
                                    val = Math.sin(twoPiF * (1.0 + 0.55 * prog) * t);
                                } else if (wtype === "slide_down") {
                                    var df = freq * Math.max(0.35, 1.0 - 0.45 * prog);
                                    val = 0.70 * Math.sin(2.0 * Math.PI * df * t) + 0.30 * Math.sin(2.0 * Math.PI * df * 1.5 * t);
                                } else if (wtype === "chord") {
                                    val = 0.50 * Math.sin(twoPiF * t) + 0.30 * Math.sin(twoPiF * 1.25 * t) + 0.20 * Math.sin(twoPiF * 1.5 * t);
                                } else {
                                    val = 0.75 * Math.sin(twoPiF * t) + 0.25 * Math.sin(twoPiF * 2.0 * t);
                                }
                                data[offset + i] = Math.max(-1.0, Math.min(1.0, val * env * amp));
                            }
                            offset += nSamp;
                        }
                        this.buffers[key] = buf;
                        return buf;
                    },

                    playSfx: function(key, notesJson, baseVol, effVol) {
                        try {
                            var ctx = this.ensureCtx();
                            if (!ctx) return;
                            var notes = JSON.parse(notesJson);
                            var buf = this.buildBuffer("sfx_" + key, notes, baseVol);
                            if (!buf) return;
                            var src = ctx.createBufferSource();
                            var gain = ctx.createGain();
                            gain.gain.value = Math.max(0.0, Math.min(1.0, effVol));
                            src.buffer = buf;
                            src.connect(gain);
                            gain.connect(ctx.destination);
                            src.start(0);
                        } catch (e) {}
                    },

                    playBgm: function(track, notesJson, baseVol, effVol) {
                        try {
                            var ctx = this.ensureCtx();
                            if (!ctx || ctx.state === "suspended") {
                                this.pendingBgm = { track: track, notesJson: notesJson, baseVol: baseVol, effVol: effVol };
                            }
                            if (!ctx) return;
                            var notes = JSON.parse(notesJson);
                            var buf = this.buildBuffer("bgm_" + track, notes, baseVol);
                            if (!buf) return;
                            if (this.bgmSource) {
                                try { this.bgmSource.stop(); } catch (e) {}
                                this.bgmSource = null;
                            }
                            var src = ctx.createBufferSource();
                            var gain = ctx.createGain();
                            gain.gain.value = Math.max(0.0, Math.min(1.0, effVol));
                            src.buffer = buf;
                            src.loop = true;
                            src.connect(gain);
                            gain.connect(ctx.destination);
                            src.start(0);
                            this.bgmSource = src;
                            this.bgmGain = gain;
                            this.currentTrack = track;
                        } catch (e) {}
                    },

                    stopBgm: function() {
                        this.pendingBgm = null;
                        if (this.bgmSource) {
                            try { this.bgmSource.stop(); } catch (e) {}
                            this.bgmSource = null;
                        }
                    },

                    setBgmVolume: function(effVol) {
                        this.bgmVol = effVol;
                        if (this.bgmGain) {
                            try { this.bgmGain.gain.value = Math.max(0.0, Math.min(1.0, effVol)); } catch (e) {}
                        }
                    }
                };

                var unlockHandler = function() {
                    if (window.__pochaAudio) window.__pochaAudio.unlock();
                };
                var evs = ["pointerdown", "mousedown", "touchstart", "keydown", "click"];
                for (var i = 0; i < evs.length; i++) {
                    window.addEventListener(evs[i], unlockHandler, { capture: true, passive: true });
                    document.addEventListener(evs[i], unlockHandler, { capture: true, passive: true });
                }
                return true;
            })();
            """
            platform.window.eval(js_code)
            self._web_audio_ready = True
            return True
        except Exception:
            return False

    def _init_mixer_safely(self) -> None:
        if sys.platform == "emscripten":
            self._init_web_audio_bridge()
        try:
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
                except Exception:
                    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._mixer_ready = pygame.mixer.get_init() is not None
            if self._mixer_ready:
                try:
                    pygame.mixer.set_num_channels(24)
                except Exception:
                    pass
        except Exception:
            self._mixer_ready = False

    def unlock_audio_on_user_gesture(self, force_bgm_restart: bool = False) -> None:
        """첫 마우스 클릭/터치/키 입력 시 브라우저 WebAudio 및 SDL 오디오 잠금을 해제하고 BGM을 재생한다."""
        first_unlock = not self._user_gesture_unlocked
        self._user_gesture_unlocked = True

        if not self._mixer_ready:
            self._init_mixer_safely()

        if sys.platform == "emscripten":
            self._init_web_audio_bridge()
            try:
                import platform
                platform.window.eval("if(window.__pochaAudio) window.__pochaAudio.unlock();")
            except Exception:
                pass

        if first_unlock or force_bgm_restart or not self._bgm_playing:
            self._bgm_playing = False
            self._bgm_sound = None
            self.sync_bgm_state()

    def get_effective_sfx_volume(self) -> float:
        if not self.enabled:
            return 0.0
        return max(0.0, min(1.0, float(self.master_volume) * float(self.sfx_volume)))

    def get_effective_bgm_volume(self) -> float:
        if not self.enabled or not self.bgm_enabled:
            return 0.0
        return max(0.0, min(1.0, float(self.master_volume) * float(self.bgm_volume) * 0.90))

    def set_master_volume(self, val: float) -> None:
        self.master_volume = round(max(0.0, min(1.0, float(val))), 2)
        self.sync_bgm_state()

    def set_sfx_volume(self, val: float) -> None:
        self.sfx_volume = round(max(0.0, min(1.0, float(val))), 2)
        self.volume = self.sfx_volume

    def set_bgm_volume(self, val: float) -> None:
        self.bgm_volume = round(max(0.0, min(1.0, float(val))), 2)
        self.sync_bgm_state()

    def set_enabled(self, flag: bool) -> None:
        self.enabled = bool(flag)
        self.sync_bgm_state()

    def set_bgm_enabled(self, flag: bool) -> None:
        self.bgm_enabled = bool(flag)
        self.sync_bgm_state()

    def apply_settings(self, settings: Dict[str, Any]) -> None:
        if not isinstance(settings, dict):
            return
        if "master_volume" in settings:
            self.master_volume = round(max(0.0, min(1.0, float(settings["master_volume"]))), 2)
        if "sfx_volume" in settings:
            self.sfx_volume = round(max(0.0, min(1.0, float(settings["sfx_volume"]))), 2)
            self.volume = self.sfx_volume
        if "bgm_volume" in settings:
            self.bgm_volume = round(max(0.0, min(1.0, float(settings["bgm_volume"]))), 2)
        if "sound_enabled" in settings:
            self.enabled = bool(settings["sound_enabled"])
        if "bgm_enabled" in settings:
            self.bgm_enabled = bool(settings["bgm_enabled"])
        self.sync_bgm_state()

    # ------------------------------------------------------------------
    # 씬/국가/피버 테마별 다중 트랙 BGM 합성 및 전환
    # ------------------------------------------------------------------
    def _get_bgm_notes(self, track: str) -> List[Tuple[float, float, str]]:
        t = (track or "title").lower()
        if t == "prep":
            # 상점 & 영업 준비: 설레고 경쾌한 보사노바/재즈풍 루프
            return [
                (293.66, 0.26, "chord"), (369.99, 0.26, "sine"), (440.00, 0.26, "sine"), (587.33, 0.26, "bell"),
                (329.63, 0.26, "chord"), (415.30, 0.26, "sine"), (493.88, 0.26, "sine"), (659.25, 0.26, "sine"),
                (261.63, 0.26, "chord"), (329.63, 0.26, "sine"), (392.00, 0.26, "sine"), (523.25, 0.26, "bell"),
                (220.00, 0.26, "chord"), (293.66, 0.26, "sine"), (369.99, 0.26, "sine"), (440.00, 0.26, "chord"),
            ]
        if t in ("play_jp", "jp"):
            # 일본 도톤보리 야타이: 마츠리 펜타토닉 멜로디
            return [
                (329.63, 0.24, "chord"), (349.23, 0.24, "sine"), (440.00, 0.24, "sine"), (493.88, 0.24, "bell"),
                (523.25, 0.24, "chord"), (493.88, 0.24, "sine"), (440.00, 0.24, "sine"), (349.23, 0.24, "sine"),
                (293.66, 0.24, "chord"), (329.63, 0.24, "sine"), (349.23, 0.24, "sine"), (440.00, 0.24, "bell"),
                (329.63, 0.24, "chord"), (293.66, 0.24, "sine"), (246.94, 0.24, "sine"), (329.63, 0.24, "chord"),
            ]
        if t in ("play_mx", "mx"):
            # 멕시코 피에스타: 라틴 리듬감의 신나는 루프
            return [
                (261.63, 0.22, "chord"), (329.63, 0.22, "sine"), (392.00, 0.22, "bell"), (523.25, 0.22, "chord"),
                (349.23, 0.22, "chord"), (440.00, 0.22, "sine"), (523.25, 0.22, "sine"), (587.33, 0.22, "bell"),
                (392.00, 0.22, "chord"), (493.88, 0.22, "sine"), (587.33, 0.22, "sine"), (659.25, 0.22, "bell"),
                (329.63, 0.22, "chord"), (392.00, 0.22, "sine"), (493.88, 0.22, "sine"), (523.25, 0.22, "chord"),
            ]
        if t in ("play_tw", "tw", "global"):
            # 대만/글로벌 야시장: 화사한 동양 야시장 루프
            return [
                (293.66, 0.25, "chord"), (329.63, 0.25, "sine"), (440.00, 0.25, "bell"), (587.33, 0.25, "sine"),
                (493.88, 0.25, "chord"), (440.00, 0.25, "sine"), (392.00, 0.25, "sine"), (329.63, 0.25, "bell"),
                (261.63, 0.25, "chord"), (293.66, 0.25, "sine"), (392.00, 0.25, "sine"), (440.00, 0.25, "bell"),
                (220.00, 0.25, "chord"), (261.63, 0.25, "sine"), (329.63, 0.25, "sine"), (392.00, 0.25, "chord"),
            ]
        if t in ("fever", "duel", "boss"):
            # 피버 타임 & 1:1 결투 & 토너먼트 보스전: 하이스피드 텐션 업 루프
            return [
                (329.63, 0.16, "chord"), (392.00, 0.16, "sine"), (493.88, 0.16, "sine"), (659.25, 0.16, "bell"),
                (349.23, 0.16, "chord"), (440.00, 0.16, "sine"), (523.25, 0.16, "sine"), (698.46, 0.16, "bell"),
                (392.00, 0.16, "chord"), (493.88, 0.16, "sine"), (587.33, 0.16, "sine"), (783.99, 0.16, "bell"),
                (440.00, 0.16, "chord"), (523.25, 0.16, "sine"), (659.25, 0.16, "bell"), (783.99, 0.16, "chord"),
            ]
        if t == "result":
            # 영업 마감 정산: 따뜻한 오르골 루프
            return [
                (523.25, 0.34, "bell"), (392.00, 0.34, "sine"), (329.63, 0.34, "sine"), (261.63, 0.34, "chord"),
                (440.00, 0.34, "bell"), (349.23, 0.34, "sine"), (293.66, 0.34, "sine"), (392.00, 0.34, "chord"),
            ]
        if t in ("play_kr", "kr", "play"):
            # 한국 포장마차 영업: 정겹고 경쾌한 한국 야시장 포차 리듬
            return [
                (261.63, 0.24, "chord"), (329.63, 0.24, "sine"), (392.00, 0.24, "bell"), (523.25, 0.24, "sine"),
                (440.00, 0.24, "chord"), (392.00, 0.24, "sine"), (329.63, 0.24, "sine"), (293.66, 0.24, "bell"),
                (261.63, 0.24, "chord"), (293.66, 0.24, "sine"), (329.63, 0.24, "sine"), (392.00, 0.24, "bell"),
                (220.00, 0.24, "chord"), (261.63, 0.24, "sine"), (293.66, 0.24, "sine"), (329.63, 0.24, "chord"),
            ]
        # 기본 "title": 메인 타이틀 야시장 네온 로파이 루프
        return [
            (261.63, 0.30, "chord"), (329.63, 0.30, "sine"), (392.00, 0.30, "bell"), (329.63, 0.30, "sine"),
            (293.66, 0.30, "chord"), (349.23, 0.30, "sine"), (440.00, 0.30, "bell"), (392.00, 0.30, "sine"),
            (220.00, 0.30, "chord"), (261.63, 0.30, "sine"), (329.63, 0.30, "bell"), (392.00, 0.30, "sine"),
            (196.00, 0.30, "chord"), (246.94, 0.30, "sine"), (293.66, 0.30, "sine"), (392.00, 0.30, "chord"),
        ]

    def _build_bgm_loop(self, track: str = "title") -> Optional[pygame.mixer.Sound]:
        """지정한 테마의 배경음악(BGM) 루프 Sound 객체를 로드하거나 합성한다."""
        key = f"bgm_{track}"
        if key in self._bgm_cache and self._bgm_cache[key] is not None:
            return self._bgm_cache[key]
        snd = self._load_or_build_sound(key, self._get_bgm_notes(track), volume=0.68)
        self._bgm_cache[key] = snd
        return snd

    def play_bgm(self, track: Optional[str] = None) -> None:
        """씬 또는 상황에 맞는 BGM 트랙으로 자연스럽게 전환한다."""
        if track:
            norm_track = str(track).strip().lower()
        else:
            norm_track = self._current_bgm_track or "title"

        if norm_track != self._current_bgm_track:
            self._current_bgm_track = norm_track
            if self._bgm_sound is not None and self._bgm_playing:
                try:
                    self._bgm_sound.stop()
                except Exception:
                    pass
                self._bgm_playing = False
            self._bgm_sound = None

        self.sync_bgm_state()

    def sync_bgm_state(self) -> None:
        eff_vol = self.get_effective_bgm_volume()
        if sys.platform == "emscripten":
            self._init_web_audio_bridge()
            try:
                import json as _json
                import platform
                if eff_vol <= 0.001:
                    platform.window.eval("if(window.__pochaAudio) window.__pochaAudio.stopBgm();")
                    self._bgm_playing = False
                else:
                    if not self._bgm_playing:
                        notes_json = _json.dumps(self._get_bgm_notes(self._current_bgm_track))
                        platform.window.eval(
                            f"if(window.__pochaAudio) window.__pochaAudio.playBgm({self._current_bgm_track!r}, {notes_json!r}, 0.68, {eff_vol:.4f});"
                        )
                        self._bgm_playing = True
                    else:
                        platform.window.eval(
                            f"if(window.__pochaAudio) window.__pochaAudio.setBgmVolume({eff_vol:.4f});"
                        )
            except Exception:
                pass
            return

        if not self._mixer_ready:
            self._init_mixer_safely()
            if not self._mixer_ready:
                return
        try:
            if eff_vol <= 0.001:
                if self._bgm_sound is not None and self._bgm_playing:
                    self._bgm_sound.stop()
                    self._bgm_playing = False
                return
            if self._bgm_sound is None:
                self._bgm_sound = self._build_bgm_loop(self._current_bgm_track)
            if self._bgm_sound is not None:
                self._bgm_sound.set_volume(eff_vol)
                if not self._bgm_playing:
                    self._bgm_sound.play(loops=-1)
                    self._bgm_playing = True
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 고품질 파형 합성기 & WAV 파일 입출력
    # ------------------------------------------------------------------
    @staticmethod
    def synthesize_wav_bytes(
        notes: List[Tuple[float, float, str]],
        volume: float = 0.4,
        sample_rate: int = 44100,
        channels: int = 2,
    ) -> bytes:
        """
        (주파수 Hz, 지속시간 초, 파형 종류) 시퀀스를 16-bit RIFF WAV 바이트로 합성한다.
        지원 파형:
        - 'sine', 'square', 'chord', 'slide_up', 'slide_down'
        - 'bell' (도어벨/종소리 배음), 'metallic' (무쇠틀 철컥 타격음)
        - 'sizzle' (직화 그릴 치익/지글지글), 'bubble' (대량팬 보글보글 끓는 소리)
        - 'pour' (반죽/음료 쪼르륵 따르는 소리), 'noise' (필터링 노이즈)
        """
        import struct

        buf = array.array("h")
        amp_max = int(32767 * max(0.04, min(1.0, volume)))
        rng = random.Random(20261106)
        n_ch = max(1, int(channels))

        for freq, dur, wave_type in notes:
            n_samples = max(1, int(sample_rate * dur))
            for i in range(n_samples):
                t = i / float(sample_rate)
                progress = i / float(n_samples)

                if wave_type in ("bell", "metallic"):
                    # 타격 후 자연스러운 지수 감쇠 엔벨로프
                    env = min(1.0, progress / 0.015) * math.exp(-3.8 * progress)
                elif wave_type in ("sizzle", "bubble", "pour"):
                    if progress < 0.06:
                        env = progress / 0.06
                    elif progress > 0.85:
                        env = max(0.0, (1.0 - progress) / 0.15)
                    else:
                        env = 1.0
                else:
                    if progress < 0.08:
                        env = progress / 0.08
                    else:
                        env = max(0.0, 1.0 - ((progress - 0.08) / 0.92) ** 0.85)

                if wave_type == "noise":
                    val = (rng.random() * 2.0 - 1.0) * math.sin(2.0 * math.pi * freq * t)
                elif wave_type == "sizzle":
                    # 직화 그릴/철판 지글지글: 고주파 스파크 + 중저음 불꽃 진동
                    n_raw = rng.random() * 2.0 - 1.0
                    crackle = 1.35 if rng.random() < 0.08 else 0.75
                    mod = 0.65 * math.sin(2.0 * math.pi * freq * t) + 0.35 * math.sin(2.0 * math.pi * (freq * 2.3) * t)
                    val = max(-1.0, min(1.0, n_raw * mod * crackle))
                elif wave_type == "bubble":
                    # 대량 조리 팬/국물 보글보글: 기포가 올라오며 피치가 상승하는 공명음
                    bubble_cycle = (t * 14.0) % 1.0
                    b_freq = freq * (0.85 + 0.65 * (bubble_cycle ** 1.5))
                    b_env = math.sin(math.pi * bubble_cycle)
                    simmer = (rng.random() * 2.0 - 1.0) * 0.18
                    val = 0.82 * math.sin(2.0 * math.pi * b_freq * t) * b_env + simmer
                elif wave_type == "pour":
                    # 음료/반죽 쪼르륵 따르는 소리: 수위가 차오르며 공명 주파수가 부드럽게 상승
                    cur_f = freq * (0.78 + 0.52 * progress + 0.06 * math.sin(2.0 * math.pi * 18.0 * t))
                    splash = (rng.random() * 2.0 - 1.0) * 0.22
                    val = 0.78 * math.sin(2.0 * math.pi * cur_f * t) + splash
                elif wave_type == "bell":
                    # 맑은 황동 도어벨/차임 배음 합성
                    val = (
                        0.58 * math.sin(2.0 * math.pi * freq * t)
                        + 0.26 * math.sin(2.0 * math.pi * (freq * 2.0) * t)
                        + 0.16 * math.sin(2.0 * math.pi * (freq * 2.756) * t)
                    )
                elif wave_type == "metallic":
                    # 무쇠 붕어빵틀 철컥 뒤집는 소리
                    thud = math.sin(2.0 * math.pi * (freq * 0.45) * t) * math.exp(-12.0 * progress)
                    clank = (
                        0.45 * math.sin(2.0 * math.pi * freq * t)
                        + 0.35 * math.sin(2.0 * math.pi * (freq * 1.62) * t)
                        + 0.20 * (rng.random() * 2.0 - 1.0)
                    )
                    val = max(-1.0, min(1.0, 0.55 * thud + 0.45 * clank))
                elif wave_type == "square":
                    s = math.sin(2.0 * math.pi * freq * t)
                    val = 0.65 if s >= 0 else -0.65
                elif wave_type == "slide_up":
                    cur_f = freq * (1.0 + 0.55 * progress)
                    val = math.sin(2.0 * math.pi * cur_f * t)
                elif wave_type == "slide_down":
                    cur_f = freq * max(0.35, 1.0 - 0.45 * progress)
                    val = (
                        0.70 * math.sin(2.0 * math.pi * cur_f * t)
                        + 0.30 * math.sin(2.0 * math.pi * (cur_f * 1.5) * t)
                    )
                elif wave_type == "chord":
                    val = (
                        0.50 * math.sin(2.0 * math.pi * freq * t)
                        + 0.30 * math.sin(2.0 * math.pi * (freq * 1.25) * t)
                        + 0.20 * math.sin(2.0 * math.pi * (freq * 1.5) * t)
                    )
                else:
                    val = (
                        0.75 * math.sin(2.0 * math.pi * freq * t)
                        + 0.25 * math.sin(2.0 * math.pi * (freq * 2.0) * t)
                    )

                sample = int(max(-32767, min(32767, val * env * amp_max)))
                for _ in range(n_ch):
                    buf.append(sample)

        raw_pcm = buf.tobytes()
        byte_rate = sample_rate * n_ch * 2
        block_align = n_ch * 2
        wav_header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(raw_pcm),
            b"WAVE",
            b"fmt ",
            16,
            1,
            n_ch,
            sample_rate,
            byte_rate,
            block_align,
            16,
            b"data",
            len(raw_pcm),
        )
        return wav_header + raw_pcm

    def _build_wave_sound(
        self,
        notes: List[Tuple[float, float, str]],
        volume: float = 0.4,
    ) -> Optional[pygame.mixer.Sound]:
        if not self._mixer_ready:
            return None
        try:
            init_info = pygame.mixer.get_init()
            if not init_info:
                return None
            sample_rate, _fmt, channels = init_info
            import io
            wav_bytes = self.synthesize_wav_bytes(
                notes,
                volume=volume,
                sample_rate=sample_rate,
                channels=channels,
            )
            return pygame.mixer.Sound(file=io.BytesIO(wav_bytes))
        except Exception:
            return None

    def _load_or_build_sound(
        self,
        key: str,
        notes: List[Tuple[float, float, str]],
        volume: float = 0.4,
    ) -> Optional[pygame.mixer.Sound]:
        """현재 오디오 디바이스의 샘플레이트·채널 포맷과 일치하는 고음량 파형 합성을 우선 생성하고, 실패 시 WAV 파일을 로드한다."""
        if not self._mixer_ready:
            return None
        snd = self._build_wave_sound(notes, volume=volume)
        if snd is not None:
            return snd
        try:
            wav_path = os.path.join(self.sounds_dir, f"{key}.wav")
            if os.path.isfile(wav_path):
                return pygame.mixer.Sound(wav_path)
        except Exception:
            pass
        return None

    def _play_cached(
        self,
        key: str,
        notes: List[Tuple[float, float, str]],
        volume: float = 0.4,
        cooldown_ms: int = 0,
        vol_scale: float = 1.0,
    ) -> None:
        eff_vol = self.get_effective_sfx_volume() * max(0.05, min(1.5, float(vol_scale)))
        if eff_vol <= 0.001:
            return
        if cooldown_ms > 0:
            try:
                now_t = pygame.time.get_ticks()
                last_t = self._last_play_ticks.get(key, -99999)
                if (now_t - last_t) < cooldown_ms:
                    return
                self._last_play_ticks[key] = now_t
            except Exception:
                pass

        boosted_vol = min(0.95, float(volume) * 1.65)
        if sys.platform == "emscripten":
            self._init_web_audio_bridge()
            try:
                import json as _json
                import platform
                notes_json = _json.dumps(notes)
                platform.window.eval(
                    f"if(window.__pochaAudio) window.__pochaAudio.playSfx({key!r}, {notes_json!r}, {boosted_vol:.4f}, {min(1.0, eff_vol):.4f});"
                )
                return
            except Exception:
                pass

        if not self._mixer_ready:
            self._init_mixer_safely()
            if not self._mixer_ready:
                return
        try:
            if key not in self._cache or self._cache[key] is None:
                self._cache[key] = self._load_or_build_sound(key, notes, volume=boosted_vol)
            snd = self._cache.get(key)
            if snd is not None:
                snd.set_volume(min(1.0, eff_vol))
                snd.play()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 1) 메인 UI & 씬 전환 효과음
    # ------------------------------------------------------------------
    def play_click(self) -> None:
        """버튼 클릭 및 기본 인터랙션 경쾌한 팝 사운드."""
        self._play_cached("click", [(660.0, 0.032, "sine"), (880.0, 0.042, "sine")], volume=0.35)

    def play_hover(self) -> None:
        """메인 타이틀 카드/버튼 마우스 호버 시 부드러운 틱 사운드."""
        self._play_cached("hover", [(540.0, 0.022, "sine"), (720.0, 0.025, "sine")], volume=0.20, cooldown_ms=65)

    def play_tab_switch(self) -> None:
        """상점/준비 화면 탭 전환 및 페이지 넘김 사운드."""
        self._play_cached("tab_switch", [(480.0, 0.03, "slide_up"), (720.0, 0.045, "sine")], volume=0.32)

    def play_dialog(self) -> None:
        """스토리 컷신 대사 넘김 사운드."""
        self._play_cached("dialog", [(587.33, 0.03, "sine"), (783.99, 0.04, "bell")], volume=0.32)

    def play_day_start(self) -> None:
        """영업 시작 버튼 클릭 시 활기찬 포장마차 오픈 벨 + 팡파레."""
        self._play_cached(
            "day_start",
            [
                (523.25, 0.07, "bell"),
                (659.25, 0.07, "bell"),
                (783.99, 0.08, "chord"),
                (1046.50, 0.22, "bell"),
            ],
            volume=0.46,
        )

    def play_timer_tick(self, urgent: bool = False) -> None:
        """마감 10초 전 카운트다운 초침 사운드."""
        if urgent:
            self._play_cached("timer_urgent", [(880.0, 0.04, "bell"), (1174.66, 0.05, "sine")], volume=0.34, cooldown_ms=400)
        else:
            self._play_cached("timer_tick", [(740.0, 0.035, "sine")], volume=0.26, cooldown_ms=400)

    def play_day_end(self) -> None:
        """영업 시간 종료 마감 종소리 (땡땡땡~!)."""
        self._play_cached(
            "day_end",
            [
                (783.99, 0.11, "bell"),
                (783.99, 0.11, "bell"),
                (1046.50, 0.26, "bell"),
            ],
            volume=0.46,
        )

    # ------------------------------------------------------------------
    # 2) 손님 방문 / VIP 등장 / 인내심 경고 / 화내며 퇴장 사운드
    # ------------------------------------------------------------------
    def play_customer_arrive(self) -> None:
        """일반 손님이 포장마차에 올 때 울리는 경쾌한 입구 종소리 (딸랑~ 딸랑!)."""
        self._play_cached(
            "customer_arrive",
            [
                (987.77, 0.075, "bell"),
                (1318.51, 0.14, "bell"),
            ],
            volume=0.38,
            cooldown_ms=120,
        )

    def play_vip_arrive(self) -> None:
        """관광객 VIP / 맛집 유튜버 VIP 손님이 등장할 때 화려한 황금 차임 벨 사운드."""
        self._play_cached(
            "vip_arrive",
            [
                (783.99, 0.06, "bell"),
                (987.77, 0.06, "bell"),
                (1174.66, 0.07, "bell"),
                (1567.98, 0.18, "bell"),
            ],
            volume=0.44,
            cooldown_ms=120,
        )

    def play_customer_warn(self) -> None:
        """손님 인내심이 25% 이하로 떨어져 화내기 직전일 때 짧은 주의 알림음."""
        self._play_cached(
            "customer_warn",
            [(587.33, 0.055, "square"), (440.0, 0.075, "square")],
            volume=0.28,
            cooldown_ms=600,
        )

    def play_customer_angry(self) -> None:
        """손님이 인내심 소진으로 화내며 떠날 때 실망/불만 사운드."""
        self._play_cached(
            "customer_angry",
            [
                (311.13, 0.09, "slide_down"),
                (233.08, 0.11, "slide_down"),
                (164.81, 0.18, "square"),
            ],
            volume=0.38,
        )

    # ------------------------------------------------------------------
    # 3) 각 화구(조리 기구 4종 & 조립 트레이)별 고유 조리 사운드
    # ------------------------------------------------------------------
    def play_mold_pour(self) -> None:
        """[몰드 화구] 붕어빵 틀 / 타코야키 판에 반죽과 속재료를 붓는 소리 (쪼르륵~ 치익!)."""
        self._play_cached(
            "mold_pour",
            [
                (340.0, 0.07, "pour"),
                (460.0, 0.06, "pour"),
                (520.0, 0.08, "sizzle"),
            ],
            volume=0.36,
        )

    def play_flip_ready(self) -> None:
        """[몰드 화구] 붕어빵 앞면이 다 익어 뒤집기 타이밍이 되었을 때 알림음 (똑-딱! 딩!)."""
        self._play_cached(
            "flip_ready",
            [
                (880.0, 0.045, "metallic"),
                (1174.66, 0.09, "bell"),
            ],
            volume=0.36,
            cooldown_ms=180,
        )

    def play_mold_flip(self) -> None:
        """[몰드 화구] 무쇠 붕어빵 주물틀을 철컥! 뒤집는 타격음 + 치익 익는 소리."""
        self._play_cached(
            "mold_flip",
            [
                (320.0, 0.055, "metallic"),
                (640.0, 0.045, "metallic"),
                (480.0, 0.09, "sizzle"),
            ],
            volume=0.40,
        )

    def play_grill_sizzle(self) -> None:
        """[직화 그릴 화구] 닭꼬치 / 타코 / 야키토리 / 지파이를 불판·튀김기에 올렸을 때 강렬한 지글지글 사운드."""
        self._play_cached(
            "grill_sizzle",
            [
                (380.0, 0.08, "sizzle"),
                (540.0, 0.10, "sizzle"),
                (440.0, 0.09, "sizzle"),
            ],
            volume=0.38,
        )

    def play_pot_boil(self) -> None:
        """[대량 조리 팬 화구] 떡볶이 철판 / 마라탕 / 야키소바 대량 조리 시작 시 보글보글 끓는 사운드."""
        self._play_cached(
            "pot_boil",
            [
                (240.0, 0.09, "bubble"),
                (310.0, 0.10, "bubble"),
                (380.0, 0.11, "bubble"),
            ],
            volume=0.38,
        )

    def play_pot_scoop(self) -> None:
        """[대량 조리 팬 화구] 보온 중인 대량 팬에서 1인분을 국자로 착 덜어내는 사운드."""
        self._play_cached(
            "pot_scoop",
            [
                (360.0, 0.045, "pour"),
                (587.33, 0.055, "sine"),
                (783.99, 0.06, "bell"),
            ],
            volume=0.36,
        )

    def play_drink_pour(self) -> None:
        """[음료 디스펜서 화구] 어묵국물 / 식혜 / 생맥주 / 버블티를 컵에 시원하게 따르는 사운드."""
        self._play_cached(
            "drink_pour",
            [
                (290.0, 0.06, "pour"),
                (410.0, 0.06, "pour"),
                (560.0, 0.07, "pour"),
                (880.0, 0.06, "bell"),
            ],
            volume=0.38,
        )

    def play_drink_ready(self) -> None:
        """[음료 디스펜서 화구] 음료 노즐 자동 충전 완료 시 맑은 물방울 사운드."""
        self._play_cached(
            "drink_ready",
            [(659.25, 0.045, "pour"), (987.77, 0.08, "bell")],
            volume=0.28,
            cooldown_ms=250,
        )

    def play_move_to_tray(self) -> None:
        """[중앙 조립 트레이] 완성된 요리를 접시 트레이에 사뿐히 옮겨 담는 사운드."""
        self._play_cached(
            "move_to_tray",
            [(523.25, 0.04, "metallic"), (783.99, 0.06, "sine")],
            volume=0.35,
        )

    def play_topping(self) -> None:
        """[중앙 조립 트레이] 음식 위에 특제 소스/토핑을 챱챱 뿌리는 사운드."""
        self._play_cached(
            "topping",
            [
                (480.0, 0.04, "sizzle"),
                (659.25, 0.045, "slide_up"),
                (987.77, 0.07, "bell"),
            ],
            volume=0.38,
        )

    def play_ambient_cooking(self, slot_type: str = "grill") -> None:
        """각 화구(몰드/그릴/대량팬)가 조리 중일 때 주기적으로 재생되는 은은한 리얼 화구 배경음."""
        st = (slot_type or "grill").lower()
        if st == "grill":
            self._play_cached(
                "ambient_grill",
                [(460.0, 0.07, "sizzle"), (520.0, 0.07, "sizzle")],
                volume=0.16,
                cooldown_ms=320,
                vol_scale=0.55,
            )
        elif st == "batch_pot":
            self._play_cached(
                "ambient_pot",
                [(260.0, 0.08, "bubble"), (320.0, 0.08, "bubble")],
                volume=0.16,
                cooldown_ms=320,
                vol_scale=0.55,
            )
        elif st == "mold":
            self._play_cached(
                "ambient_mold",
                [(360.0, 0.06, "sizzle"), (440.0, 0.06, "pour")],
                volume=0.14,
                cooldown_ms=320,
                vol_scale=0.50,
            )

    def play_sizzle(self, slot_type: Optional[str] = None) -> None:
        """화구 종류에 맞춘 조리 시작 사운드 (slot_type 지정 시 화구별 전용 사운드 재생)."""
        if slot_type == "mold":
            self.play_mold_pour()
        elif slot_type == "grill":
            self.play_grill_sizzle()
        elif slot_type == "batch_pot":
            self.play_pot_boil()
        elif slot_type == "dispenser":
            self.play_drink_pour()
        else:
            self._play_cached("sizzle", [(420.0, 0.08, "sizzle"), (540.0, 0.10, "sizzle")], volume=0.32)

    def play_ready(self) -> None:
        """조리 완료(READY) 맑은 주방 벨 사운드 (딩동!)."""
        self._play_cached("ready", [(784.0, 0.07, "bell"), (1046.5, 0.15, "bell")], volume=0.42)

    def play_burn_warning(self) -> None:
        """음식이 타기 직전(경고 구간)에 진입했을 때 울리는 짧은 경고음 (삐비빅!)."""
        self._play_cached(
            "burn_warning",
            [(880.0, 0.045, "square"), (659.25, 0.045, "square"), (880.0, 0.06, "square")],
            volume=0.30,
            cooldown_ms=500,
        )

    def play_burn(self) -> None:
        """음식이 탔거나 실패했을 때 낮은 경고음."""
        self._play_cached(
            "burn",
            [(220.0, 0.10, "square"), (164.81, 0.18, "square")],
            volume=0.35,
        )

    def play_trash(self) -> None:
        """탄 음식이나 잘못 만든 접시를 휴지통에 버릴 때 폐기 사운드."""
        self._play_cached(
            "trash",
            [(300.0, 0.05, "sizzle"), (196.0, 0.09, "slide_down"), (130.81, 0.11, "metallic")],
            volume=0.35,
        )

    # ------------------------------------------------------------------
    # 4) 서빙 / 매출 / 콤보 / 스킬 / 강화 / 팡파레 사운드
    # ------------------------------------------------------------------
    def play_serve(self) -> None:
        """원클릭 서빙 출발/성공 사운드 (슈웅~ 띵!)."""
        self._play_cached("serve", [(523.25, 0.05, "slide_up"), (783.99, 0.09, "bell")], volume=0.40)

    def play_cash(self) -> None:
        """매출 획득 찰랑이는 금화/포스기 사운드 (차링~!)."""
        self._play_cached(
            "cash",
            [(987.77, 0.055, "bell"), (1318.51, 0.14, "bell")],
            volume=0.42,
        )

    def play_combo(self, combo_count: int = 1) -> None:
        """콤보 스택에 따라 피치가 올라가는 신나는 아르페지오 사운드."""
        clamped = max(1, min(10, int(combo_count)))
        base_f = 523.25 * (1.0 + (clamped - 1) * 0.06)
        self._play_cached(
            f"combo_{clamped}",
            [
                (base_f, 0.05, "sine"),
                (base_f * 1.25, 0.05, "sine"),
                (base_f * 1.5, 0.11, "bell"),
            ],
            volume=0.42,
        )

    def play_upgrade(self) -> None:
        """상점 기구/인테리어 업그레이드 구매 시 망치질 + 강화 차임 사운드."""
        self._play_cached(
            "upgrade",
            [
                (440.0, 0.05, "metallic"),
                (587.33, 0.05, "metallic"),
                (880.0, 0.07, "bell"),
                (1174.66, 0.15, "bell"),
            ],
            volume=0.44,
        )

    def play_skill(self) -> None:
        """주인공 액티브 스킬 발동 시 화려한 상승 사운드."""
        self._play_cached(
            "skill",
            [
                (440.0, 0.06, "slide_up"),
                (659.25, 0.06, "slide_up"),
                (880.0, 0.08, "chord"),
                (1174.66, 0.18, "bell"),
            ],
            volume=0.48,
        )

    def play_fanfare(self) -> None:
        """일일 마감 클리어 및 챕터/주인공 해금 축하 팡파레."""
        self._play_cached(
            "fanfare",
            [
                (523.25, 0.09, "chord"),
                (659.25, 0.09, "chord"),
                (783.99, 0.09, "chord"),
                (1046.50, 0.24, "bell"),
            ],
            volume=0.48,
        )

    def export_all_wav_assets(self, target_dir: Optional[str] = None) -> int:
        """모든 BGM 및 효과음 파형을 실제 .wav 오디오 파일로 생성하여 assets/sounds/ 디렉토리에 저장한다."""
        out_dir = target_dir or self.sounds_dir
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError:
            return 0
        specs: Dict[str, Tuple[List[Tuple[float, float, str]], float]] = {
            "bgm_title": (self._get_bgm_notes("title"), 0.68),
            "bgm_prep": (self._get_bgm_notes("prep"), 0.68),
            "bgm_play_kr": (self._get_bgm_notes("play_kr"), 0.68),
            "bgm_play_jp": (self._get_bgm_notes("play_jp"), 0.68),
            "bgm_play_mx": (self._get_bgm_notes("play_mx"), 0.68),
            "bgm_play_tw": (self._get_bgm_notes("play_tw"), 0.68),
            "bgm_fever": (self._get_bgm_notes("fever"), 0.68),
            "bgm_result": (self._get_bgm_notes("result"), 0.68),
            "click": ([(660.0, 0.032, "sine"), (880.0, 0.042, "sine")], 0.35),
            "hover": ([(540.0, 0.022, "sine"), (720.0, 0.025, "sine")], 0.20),
            "tab_switch": ([(480.0, 0.03, "slide_up"), (720.0, 0.045, "sine")], 0.32),
            "dialog": ([(587.33, 0.03, "sine"), (783.99, 0.04, "bell")], 0.32),
            "day_start": ([(523.25, 0.07, "bell"), (659.25, 0.07, "bell"), (783.99, 0.08, "chord"), (1046.50, 0.22, "bell")], 0.46),
            "timer_tick": ([(740.0, 0.035, "sine")], 0.26),
            "timer_urgent": ([(880.0, 0.04, "bell"), (1174.66, 0.05, "sine")], 0.34),
            "day_end": ([(783.99, 0.11, "bell"), (783.99, 0.11, "bell"), (1046.50, 0.26, "bell")], 0.46),
            "customer_arrive": ([(987.77, 0.075, "bell"), (1318.51, 0.14, "bell")], 0.38),
            "vip_arrive": ([(783.99, 0.06, "bell"), (987.77, 0.06, "bell"), (1174.66, 0.07, "bell"), (1567.98, 0.18, "bell")], 0.44),
            "customer_warn": ([(587.33, 0.055, "square"), (440.0, 0.075, "square")], 0.28),
            "customer_angry": ([(311.13, 0.09, "slide_down"), (233.08, 0.11, "slide_down"), (164.81, 0.18, "square")], 0.38),
            "mold_pour": ([(340.0, 0.07, "pour"), (460.0, 0.06, "pour"), (520.0, 0.08, "sizzle")], 0.36),
            "flip_ready": ([(880.0, 0.045, "metallic"), (1174.66, 0.09, "bell")], 0.36),
            "mold_flip": ([(320.0, 0.055, "metallic"), (640.0, 0.045, "metallic"), (480.0, 0.09, "sizzle")], 0.40),
            "grill_sizzle": ([(380.0, 0.08, "sizzle"), (540.0, 0.10, "sizzle"), (440.0, 0.09, "sizzle")], 0.38),
            "pot_boil": ([(240.0, 0.09, "bubble"), (310.0, 0.10, "bubble"), (380.0, 0.11, "bubble")], 0.38),
            "pot_scoop": ([(360.0, 0.045, "pour"), (587.33, 0.055, "sine"), (783.99, 0.06, "bell")], 0.36),
            "drink_pour": ([(290.0, 0.06, "pour"), (410.0, 0.06, "pour"), (560.0, 0.07, "pour"), (880.0, 0.06, "bell")], 0.38),
            "drink_ready": ([(659.25, 0.045, "pour"), (987.77, 0.08, "bell")], 0.28),
            "move_to_tray": ([(523.25, 0.04, "metallic"), (783.99, 0.06, "sine")], 0.35),
            "topping": ([(480.0, 0.04, "sizzle"), (659.25, 0.045, "slide_up"), (987.77, 0.07, "bell")], 0.38),
            "ambient_grill": ([(460.0, 0.07, "sizzle"), (520.0, 0.07, "sizzle")], 0.16),
            "ambient_pot": ([(260.0, 0.08, "bubble"), (320.0, 0.08, "bubble")], 0.16),
            "ambient_mold": ([(360.0, 0.06, "sizzle"), (440.0, 0.06, "pour")], 0.14),
            "sizzle": ([(420.0, 0.08, "sizzle"), (540.0, 0.10, "sizzle")], 0.32),
            "ready": ([(784.0, 0.07, "bell"), (1046.5, 0.15, "bell")], 0.42),
            "burn_warning": ([(880.0, 0.045, "square"), (659.25, 0.045, "square"), (880.0, 0.06, "square")], 0.30),
            "burn": ([(220.0, 0.10, "square"), (164.81, 0.18, "square")], 0.35),
            "trash": ([(300.0, 0.05, "sizzle"), (196.0, 0.09, "slide_down"), (130.81, 0.11, "metallic")], 0.35),
            "serve": ([(523.25, 0.05, "slide_up"), (783.99, 0.09, "bell")], 0.40),
            "cash": ([(987.77, 0.055, "bell"), (1318.51, 0.14, "bell")], 0.42),
            "upgrade": ([(440.0, 0.05, "metallic"), (587.33, 0.05, "metallic"), (880.0, 0.07, "bell"), (1174.66, 0.15, "bell")], 0.44),
            "skill": ([(440.0, 0.06, "slide_up"), (659.25, 0.06, "slide_up"), (880.0, 0.08, "chord"), (1174.66, 0.18, "bell")], 0.48),
            "fanfare": ([(523.25, 0.09, "chord"), (659.25, 0.09, "chord"), (783.99, 0.09, "chord"), (1046.50, 0.24, "bell")], 0.48),
        }
        count = 0
        for key, (notes, vol) in specs.items():
            eff_v = vol if key.startswith("bgm_") else min(0.95, vol * 1.65)
            wav_bytes = self.synthesize_wav_bytes(notes, volume=eff_v, sample_rate=44100, channels=2)
            try:
                with open(os.path.join(out_dir, f"{key}.wav"), "wb") as f:
                    f.write(wav_bytes)
                count += 1
            except OSError:
                continue
        return count

    # 편의 별칭
    play_unlock = play_fanfare
    play_error = play_burn
    play_fever = play_skill


# 모듈 레벨 싱글톤 및 함수 별칭
sound_fx: SoundFX = SoundFX()

play_click = sound_fx.play_click
play_hover = sound_fx.play_hover
play_sizzle = sound_fx.play_sizzle
play_mold_pour = sound_fx.play_mold_pour
play_flip_ready = sound_fx.play_flip_ready
play_mold_flip = sound_fx.play_mold_flip
play_grill_sizzle = sound_fx.play_grill_sizzle
play_pot_boil = sound_fx.play_pot_boil
play_pot_scoop = sound_fx.play_pot_scoop
play_drink_pour = sound_fx.play_drink_pour
play_drink_ready = sound_fx.play_drink_ready
play_move_to_tray = sound_fx.play_move_to_tray
play_topping = sound_fx.play_topping
play_ready = sound_fx.play_ready
play_burn_warning = sound_fx.play_burn_warning
play_burn = sound_fx.play_burn
play_trash = sound_fx.play_trash
play_customer_arrive = sound_fx.play_customer_arrive
play_vip_arrive = sound_fx.play_vip_arrive
play_customer_warn = sound_fx.play_customer_warn
play_customer_angry = sound_fx.play_customer_angry
play_serve = sound_fx.play_serve
play_cash = sound_fx.play_cash
play_combo = sound_fx.play_combo
play_upgrade = sound_fx.play_upgrade
play_skill = sound_fx.play_skill
play_fanfare = sound_fx.play_fanfare

