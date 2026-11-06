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
import random
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
# 4. SoundFX (외부 파일 없는 프로시저럴 사운드 합성기)
# ==============================================================================
class SoundFX:
    """
    외부 오디오 파일(.wav/.ogg) 없이 pygame.mixer와 수학적 파형(사인파, 삼각파, 화음, 노이즈)을
    조합하여 즉석 생성·캐싱하는 아케이드 효과음 합성기.
    오디오 장치가 없는 헤드리스(Headless) 환경에서도 절대 예외가 발생하지 않는다.
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
        self.master_volume: float = 0.80
        self.sfx_volume: float = 0.80
        self.bgm_volume: float = 0.45
        self.volume: float = 0.80
        self._cache: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self._bgm_sound: Optional[pygame.mixer.Sound] = None
        self._bgm_playing: bool = False
        self._mixer_ready: bool = False
        self._init_mixer_safely()

    def _init_mixer_safely(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._mixer_ready = pygame.mixer.get_init() is not None
        except Exception:
            self._mixer_ready = False

    def get_effective_sfx_volume(self) -> float:
        if not self.enabled:
            return 0.0
        return max(0.0, min(1.0, float(self.master_volume) * float(self.sfx_volume)))

    def get_effective_bgm_volume(self) -> float:
        if not self.enabled or not self.bgm_enabled:
            return 0.0
        return max(0.0, min(1.0, float(self.master_volume) * float(self.bgm_volume) * 0.55))

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

    def _build_bgm_loop(self) -> Optional[pygame.mixer.Sound]:
        """야시장 감성의 따뜻한 로파이 아케이드 배경음악(BGM) 루프를 합성한다."""
        melody: List[Tuple[float, float, str]] = [
            (261.63, 0.32, "chord"),
            (329.63, 0.32, "sine"),
            (392.00, 0.32, "sine"),
            (329.63, 0.32, "sine"),
            (293.66, 0.32, "chord"),
            (349.23, 0.32, "sine"),
            (440.00, 0.32, "sine"),
            (392.00, 0.32, "sine"),
            (220.00, 0.32, "chord"),
            (261.63, 0.32, "sine"),
            (329.63, 0.32, "sine"),
            (392.00, 0.32, "sine"),
            (196.00, 0.32, "chord"),
            (246.94, 0.32, "sine"),
            (293.66, 0.32, "sine"),
            (392.00, 0.32, "chord"),
        ]
        return self._build_wave_sound(melody, volume=0.28)

    def sync_bgm_state(self) -> None:
        if not self._mixer_ready:
            self._init_mixer_safely()
            if not self._mixer_ready:
                return
        eff_vol = self.get_effective_bgm_volume()
        try:
            if eff_vol <= 0.001:
                if self._bgm_sound is not None and self._bgm_playing:
                    self._bgm_sound.stop()
                    self._bgm_playing = False
                return
            if self._bgm_sound is None:
                self._bgm_sound = self._build_bgm_loop()
            if self._bgm_sound is not None:
                self._bgm_sound.set_volume(eff_vol)
                if not self._bgm_playing:
                    self._bgm_sound.play(loops=-1)
                    self._bgm_playing = True
        except Exception:
            pass

    def _build_wave_sound(
        self,
        notes: List[Tuple[float, float, str]],
        volume: float = 0.4,
    ) -> Optional[pygame.mixer.Sound]:
        """
        (주파수 Hz, 지속시간 초, 파형 종류['sine'|'square'|'noise'|'slide_up']) 시퀀스를
        16-bit PCM 버퍼로 합성하여 pygame.mixer.Sound 객체를 생성한다.
        """
        if not self._mixer_ready:
            return None
        try:
            init_info = pygame.mixer.get_init()
            if not init_info:
                return None
            sample_rate, _fmt, channels = init_info
            buf = array.array("h")
            amp_max = int(32767 * max(0.05, min(1.0, volume)))

            for freq, dur, wave_type in notes:
                n_samples = max(1, int(sample_rate * dur))
                for i in range(n_samples):
                    t = i / float(sample_rate)
                    progress = i / float(n_samples)
                    # ADSR 유사 엔벨로프 (클릭 노이즈 방지)
                    if progress < 0.08:
                        env = progress / 0.08
                    else:
                        env = max(0.0, 1.0 - ((progress - 0.08) / 0.92) ** 0.85)

                    if wave_type == "noise":
                        # 지글지글 소리용 필터링 노이즈
                        val = (random.random() * 2.0 - 1.0) * math.sin(2.0 * math.pi * freq * t)
                    elif wave_type == "square":
                        s = math.sin(2.0 * math.pi * freq * t)
                        val = 0.65 if s >= 0 else -0.65
                    elif wave_type == "slide_up":
                        cur_f = freq * (1.0 + 0.55 * progress)
                        val = math.sin(2.0 * math.pi * cur_f * t)
                    elif wave_type == "chord":
                        val = (
                            0.5 * math.sin(2.0 * math.pi * freq * t)
                            + 0.3 * math.sin(2.0 * math.pi * (freq * 1.25) * t)
                            + 0.2 * math.sin(2.0 * math.pi * (freq * 1.5) * t)
                        )
                    else:
                        val = (
                            0.75 * math.sin(2.0 * math.pi * freq * t)
                            + 0.25 * math.sin(2.0 * math.pi * (freq * 2.0) * t)
                        )

                    sample = int(max(-32767, min(32767, val * env * amp_max)))
                    buf.append(sample)
                    if channels == 2:
                        buf.append(sample)

            raw_pcm = buf.tobytes()
            import io
            import struct
            byte_rate = sample_rate * channels * 2
            block_align = channels * 2
            wav_header = struct.pack(
                "<4sI4s4sIHHIIHH4sI",
                b"RIFF",
                36 + len(raw_pcm),
                b"WAVE",
                b"fmt ",
                16,
                1,
                channels,
                sample_rate,
                byte_rate,
                block_align,
                16,
                b"data",
                len(raw_pcm),
            )
            return pygame.mixer.Sound(file=io.BytesIO(wav_header + raw_pcm))
        except Exception:
            return None

    def _play_cached(
        self,
        key: str,
        notes: List[Tuple[float, float, str]],
        volume: float = 0.4,
    ) -> None:
        eff_vol = self.get_effective_sfx_volume()
        if eff_vol <= 0.001:
            return
        if not self._mixer_ready:
            self._init_mixer_safely()
            if not self._mixer_ready:
                return
        try:
            if key not in self._cache:
                self._cache[key] = self._build_wave_sound(notes, volume=volume)
            snd = self._cache.get(key)
            if snd is not None:
                snd.set_volume(eff_vol)
                snd.play()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 게임 내 주요 프로시저럴 사운드 메서드
    # ------------------------------------------------------------------
    def play_click(self) -> None:
        """버튼 클릭 및 재료 투입 경쾌한 팝 사운드."""
        self._play_cached("click", [(660.0, 0.035, "sine"), (880.0, 0.045, "sine")], volume=0.35)

    def play_sizzle(self) -> None:
        """철판/그릴에 재료를 올렸을 때 지글지글 사운드."""
        self._play_cached("sizzle", [(420.0, 0.08, "noise"), (540.0, 0.10, "noise")], volume=0.30)

    def play_ready(self) -> None:
        """조리 완료(READY) 맑은 벨 사운드 (딩동!)."""
        self._play_cached("ready", [(784.0, 0.07, "sine"), (1046.5, 0.14, "chord")], volume=0.40)

    def play_serve(self) -> None:
        """원클릭 서빙 출발/성공 사운드."""
        self._play_cached("serve", [(523.25, 0.05, "slide_up"), (783.99, 0.09, "chord")], volume=0.40)

    def play_cash(self) -> None:
        """매출 획득 찰랑이는 금화/포스기 사운드 (차링~!)."""
        self._play_cached(
            "cash",
            [(987.77, 0.055, "sine"), (1318.51, 0.13, "chord")],
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
                (base_f * 1.5, 0.11, "chord"),
            ],
            volume=0.42,
        )

    def play_burn(self) -> None:
        """음식이 탔거나 손님이 떠났을 때 낮은 경고음."""
        self._play_cached(
            "burn",
            [(220.0, 0.10, "square"), (164.81, 0.18, "square")],
            volume=0.35,
        )

    def play_skill(self) -> None:
        """주인공 액티브 스킬 발동 시 화려한 상승 사운드."""
        self._play_cached(
            "skill",
            [
                (440.0, 0.06, "slide_up"),
                (659.25, 0.06, "slide_up"),
                (880.0, 0.08, "chord"),
                (1174.66, 0.18, "chord"),
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
                (1046.50, 0.24, "chord"),
            ],
            volume=0.48,
        )

    # 편의 별칭
    play_upgrade = play_cash
    play_unlock = play_fanfare
    play_error = play_burn
    play_trash = play_burn
    play_fever = play_skill


# 모듈 레벨 싱글톤 및 함수 별칭
sound_fx: SoundFX = SoundFX()

play_click = sound_fx.play_click
play_sizzle = sound_fx.play_sizzle
play_ready = sound_fx.play_ready
play_serve = sound_fx.play_serve
play_cash = sound_fx.play_cash
play_combo = sound_fx.play_combo
play_burn = sound_fx.play_burn
play_skill = sound_fx.play_skill
play_fanfare = sound_fx.play_fanfare
