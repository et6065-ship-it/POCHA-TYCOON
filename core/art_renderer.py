"""
core/art_renderer.py
'전세계 길거리 음식 포차 타이쿤' 프로시저럴 픽셀/벡터 일러스트 렌더러 및 스프라이트 팩토리.
외부 이미지 파일 없이도 pygame.draw와 pygame.Surface 캐싱을 활용하여
국가별 야시장 배경, 도트(Pixel Art) 셰프 아바타, 손님 캐릭터, 메뉴/토핑 아이콘, 조리 기구 하드웨어를 렌더링합니다.
"""

import math
import os
import sys
import pygame

try:
    import config
    from config import get_font as _config_get_font
except Exception:
    config = None
    _config_get_font = None


# ==============================================================================
# 주인공 4인 24x24 레트로 도트(Pixel Art) 스프라이트 맵 & 팔레트 정의
# ==============================================================================
_CHEF_PIXEL_MAPS = {
    # 1. 한국 김포차 (주황 포차 두건 + 푸근한 눈웃음 + 포차 앞치마 + 뒤집개 & 황금 붕어빵)
    "chef_kr": [
        "........OOOOOOOO........",
        "......OOHHHHHHHHOO......",
        ".....OHHHHHHHHHHHHO.....",
        "..OOORRRRRRRRRRRRRRO....",
        ".ORWARRRRRWARRRRRWARO...",
        ".ORRROOOOOOOOOOOOOORO...",
        "..OO.OSSSSSSSSSSSSO.O...",
        ".....OSsSssssssSsSO.....",
        "....OSseeeSssSeeeSsO....",
        "....OSeppeSssSeppeSO....",
        "....OSsssssddsssssSO....",
        "....OdsSssmmmmssSsdO..OO",
        ".....OdsSssWWssSsdO..OBO",
        "......OdddssssdddO..OBbO",
        ".....OOWWWWWWWWWWO.OOBBO",
        "....OWWRRRRRRRRRRWOOCCOO",
        "...OWWWRRRRRRRRRRWWOCO..",
        "...OWssRRRRRRRRRRssWCO..",
        "...OOssRRRRWWWRRRssOO...",
        "....OOORRRRWWWRRRROO....",
        "......ORRRRRRRRRRRO.....",
        "......OrrrrrrrrrrrO.....",
        "......OOOOOOOOOOOOO.....",
        "........................",
    ],
    # 2. 일본 켄지 (하얀 하치마키 일장기 머리띠 + 장인 눈매 + 남색 핫피 + 타코야키 볼 & 송곳)
    "chef_jp": [
        ".....OO..OOOO..OO.......",
        "....OHHOOHHHHOOHHO......",
        "...OHHHHHHHHHHHHHHO.....",
        "..OOOWWWWWWRRWWWWWWO....",
        ".OWgWWWWWWWRRWWWWWWgO...",
        ".OOWWOOOOOOOOOOOOOWWO...",
        "..OO.OSSSSSSSSSSSSO.....",
        ".....OSeeSssssSeeSO.....",
        "....OSsWeSssssSWeSsO....",
        "....OSsssssddsssssSO....",
        "....OdsSssWWWWssSsdO.OO.",
        ".....OdsSshhhhssSsdOOCOO",
        "......OdddssssdddO.OBbBO",
        ".....OONNWWNWWNNNO.OBGBO",
        "....ONNNNWWNWWNNNNNOOBBO",
        "...ONNNNNWWNWWNNNNNNOOO.",
        "...ONssNNWWWWWWNNssNO...",
        "...OOssNNNNNNNNNNssOO...",
        "....OOONNNNNNNNNNNOO....",
        "......ONNNNNNNNNNNO.....",
        "......OnnnnnnnnnnnO.....",
        "......OOOOOOOOOOOOO.....",
        "........................",
        "........................",
    ],
    # 3. 멕시코 디에고 (화려한 자수 솜브레로 + 멋진 콧수염 + 세라페 판초 + 타코 & 칠리)
    "chef_mx": [
        ".......OOOOOOOOOO.......",
        ".....OOMMMMMMMMMMOO.....",
        "....OMMRRGGYYGGRRMMO....",
        ".OOOMMMMMMMMMMMMMMMMOOO.",
        "OMMMuRRGGYYRRYYGGRRuMMMO",
        "OuuuuOOOOOOOOOOOOOOuuuuO",
        ".OOOOOSSSSSSSSSSSSOOOOO.",
        ".....OSsSssssssSsSO.....",
        "....OSsWeSssssSeeSsO....",
        "....OSsssssddsssssSO.OO.",
        "....OdsSHHHHHHHHssdOOTGO",
        ".....OdSHHWWWWeeHsdOTRTO",
        "......OdddssssdddO.OOTTO",
        ".....OOGGWWYYRRGGO..ORO.",
        "....OGGGGWWYYRRGGGGOOOO.",
        "...OGGGGGWWYYRRGGGGGO...",
        "...OGssGGWWYYRRGGssGO...",
        "...OOssGGWWYYRRGGssOO...",
        "....OOOGGWWYYRRGGGOO....",
        "......ORRYYYYYYGGGO.....",
        "......OrrrrrrrrrrrO.....",
        "......OOOOOOOOOOOOO.....",
        "........................",
        "........................",
    ],
    # 4. 대만 메이링 (양갈래 만두머리 & 홍등 장식 + 초롱초롱 눈 + 차이나 카라 셰프복 + 흑당 버블티)
    "chef_tw": [
        "..OOOO....OOOO....OOOO..",
        ".OHHHHO.OOHHHHOO.OHHHHO.",
        ".OHhHHOOHHHHHHHHOOHhHHO.",
        ".OYYJJOOHHHHHHHHOOJYYYO.",
        "..ORRO.OSSSSSSSSO.ORRO..",
        "...OO.OSSSSSSSSSSO.OO...",
        ".....OSsSssssssSsSO.....",
        "....OSsWeeSssSeeWssO.OO.",
        "....OSseeeSssSeeessOOPPO",
        "....OSppsssddsssppSO.OPO",
        "....OdsSssmmmmssSsdOOWWO",
        ".....OdsSssssssSsdO.OTTO",
        "......OdddssssdddO..OTtO",
        ".....OORRYYYYYYRRO..OTtO",
        "....ORRRRRYYYYRRRRROOOOO",
        "...ORRRRRRYYYYRRRRRRO...",
        "...ORssRRRRRRRRRRssRO...",
        "...OOssRRRRYYRRRRssOO...",
        "....OOORRRRRRRRRRROO....",
        "......ORRRRRRRRRRRO.....",
        "......OrrrrrrrrrrrO.....",
        "......OOOOOOOOOOOOO.....",
        "........................",
        "........................",
    ],
}

_COMMON_PALETTE = {
    "O": (20, 16, 28),       # 외곽선 딥 블랙/네이비
    "s": (255, 218, 185),    # 기본 피부톤
    "S": (255, 236, 212),    # 피부 하이라이트
    "d": (218, 170, 136),    # 피부 그림자
    "p": (255, 138, 148),    # 볼터치 핑크
    "e": (32, 24, 36),       # 눈동자 / 눈썹
    "W": (250, 250, 255),    # 화이트 하이라이트
    "g": (195, 205, 220),    # 라이트 그레이
    "m": (215, 55, 65),      # 입술 레드
    "Y": (255, 216, 52),     # 브라이트 골드
    "y": (212, 152, 28),     # 딥 골드
}

_CHEF_PALETTES = {
    "chef_kr": {
        **_COMMON_PALETTE,
        "H": (64, 42, 32),       # 포차 이모님/아저씨 갈색 머리
        "h": (98, 68, 52),
        "R": (242, 96, 36),      # 포장마차 다홍/주황
        "r": (188, 60, 20),      # 주황 그림자
        "A": (255, 162, 78),     # 두건 하이라이트
        "B": (238, 168, 56),     # 황금 붕어빵
        "b": (132, 42, 38),      # 팥 앙금 포인트
        "C": (192, 206, 222),    # 뒤집개 스테인리스
    },
    "chef_jp": {
        **_COMMON_PALETTE,
        "H": (28, 32, 48),       # 흑발
        "h": (78, 86, 108),      # 수염/하이라이트
        "R": (228, 42, 48),      # 하치마키 일장기 레드
        "N": (34, 64, 136),      # 남색 핫피
        "n": (20, 40, 92),       # 핫피 그림자
        "B": (232, 158, 62),     # 타코야키 볼
        "b": (115, 52, 26),      # 타레 소스
        "G": (68, 192, 78),      # 파래김(아오노리)
        "C": (210, 220, 235),    # 타코야키 송곳
    },
    "chef_mx": {
        **_COMMON_PALETTE,
        "s": (238, 190, 148),    # 라틴 웜 피부톤
        "S": (252, 212, 174),
        "d": (198, 148, 108),
        "H": (54, 32, 22),       # 콧수염 다크 브라운
        "M": (242, 188, 62),     # 솜브레로 밀짚 골드
        "u": (196, 138, 34),     # 솜브레로 그림자
        "R": (228, 52, 46),      # 피에스타 레드 / 칠리
        "r": (172, 34, 30),
        "G": (42, 182, 88),      # 피에스타 그린
        "T": (245, 202, 82),     # 타코 또띠아
    },
    "chef_tw": {
        **_COMMON_PALETTE,
        "H": (36, 26, 42),       # 만두머리 흑발
        "h": (78, 56, 88),       # 머리 윤기 하이라이트
        "R": (218, 42, 58),      # 대만 홍등 크림슨
        "r": (165, 26, 40),
        "J": (56, 222, 206),     # 제이드(비취) 장식
        "T": (228, 182, 134),    # 흑당 버블티 밀크티색
        "t": (58, 30, 22),       # 타피오카 펄
        "P": (255, 102, 168),    # 핑크 빨대
    },
}

# 자물쇠(LOCKED) 9x11 도트 아이콘
_PADLOCK_PIXEL_MAP = [
    "..OOOOO..",
    ".OWWWWW0.",
    ".OWOOOgm.",
    ".OWO..Og.",
    "OOOOOOOOO",
    "OYYYYYYYO",
    "OYYyOyyYO",
    "OYYyOyyYO",
    "OyyyyyyyO",
    "OOOOOOOOO",
]


class ArtRenderer:
    """전역 캐시 및 프로시저럴 아트워크 렌더링 클래스."""

    _food_cache = {}
    _topping_cache = {}
    _hardware_cache = {}
    _chef_pixel_cache = {}
    _chef_scaled_cache = {}
    _bg_cache = {}
    _glow_cache = {}
    _overlay_cache = {}
    _neon_cache = {}
    _font_cache = {}

    @classmethod
    def draw_alpha_overlay(
        cls,
        surface: pygame.Surface,
        rect,
        rgba: tuple,
        border_radius=0,
    ) -> None:
        """반투명 오버레이 서피스를 캐싱하여 매 프레임 메모리 할당 없이 고속 블릿합니다."""
        if (
            not isinstance(rect, pygame.Rect)
            and hasattr(rect, "__len__")
            and len(rect) == 2
            and hasattr(border_radius, "__len__")
            and len(border_radius) == 2
        ):
            r = pygame.Rect(int(border_radius[0]), int(border_radius[1]), int(rect[0]), int(rect[1]))
            br = 0
        else:
            r = cls._norm_rect(rect)
            br = int(border_radius) if isinstance(border_radius, (int, float)) else 0

        w, h = max(1, r.width), max(1, r.height)
        key = (w, h, int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3]), br)
        ov = cls._overlay_cache.get(key)
        if ov is None:
            ov = pygame.Surface((w, h), pygame.SRCALPHA)
            if br > 0:
                pygame.draw.rect(ov, rgba, (0, 0, w, h), border_radius=br)
            else:
                ov.fill(rgba)
            if len(cls._overlay_cache) > 64:
                cls._overlay_cache.clear()
            cls._overlay_cache[key] = ov
        surface.blit(ov, r.topleft)

    # ------------------------------------------------------------------
    # 내부 유틸리티 & 폰트 헬퍼
    # ------------------------------------------------------------------
    @classmethod
    def _get_font(cls, size: int, bold: bool = True) -> pygame.font.Font:
        if _config_get_font is not None:
            try:
                return _config_get_font(size, bold=bold)
            except Exception:
                pass
        key = (size, bold)
        if key not in cls._font_cache:
            if not pygame.font.get_init():
                pygame.font.init()
            font_names = ["malgungothic", "malgun gothic", "applegothic", "nanumgothic", "gulim", "arial"]
            font = None
            for name in font_names:
                matched = pygame.font.match_font(name, bold=bold)
                if matched:
                    try:
                        font = pygame.font.Font(matched, size)
                        break
                    except Exception:
                        pass
            if font is None:
                font = pygame.font.SysFont(None, size, bold=bold)
            cls._font_cache[key] = font
        return cls._font_cache[key]

    @staticmethod
    def _norm_rect(rect) -> pygame.Rect:
        if isinstance(rect, pygame.Rect):
            return rect
        if hasattr(rect, "__len__") and len(rect) == 2:
            return pygame.Rect(0, 0, int(rect[0]), int(rect[1]))
        return pygame.Rect(int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))

    @staticmethod
    def _norm_center(center_pos):
        if isinstance(center_pos, pygame.Rect):
            return center_pos.center
        if hasattr(center_pos, "__len__") and len(center_pos) == 4:
            return (int(center_pos[0] + center_pos[2] / 2), int(center_pos[1] + center_pos[3] / 2))
        return (int(center_pos[0]), int(center_pos[1]))

    @staticmethod
    def _lerp_color(c1, c2, t: float):
        t = max(0.0, min(1.0, t))
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )

    @classmethod
    def _draw_vertical_gradient(cls, surface: pygame.Surface, rect: pygame.Rect, top_color, bottom_color, step: int = 4):
        h = max(1, rect.height)
        for y_off in range(0, h, step):
            t = y_off / float(h)
            col = cls._lerp_color(top_color, bottom_color, t)
            band_h = min(step, h - y_off)
            pygame.draw.rect(surface, col, (rect.x, rect.y + y_off, rect.width, band_h))

    @classmethod
    def _draw_glow_circle(cls, surface: pygame.Surface, center, radius: int, color, alpha: int = 90):
        if radius <= 0:
            return
        q_alpha = max(10, (int(alpha) // 8) * 8)
        c_key = (int(color[0]), int(color[1]), int(color[2]))
        cache_key = (int(radius), c_key, q_alpha)
        glow_surf = cls._glow_cache.get(cache_key)
        if glow_surf is None:
            diameter = radius * 2
            glow_surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
            for r in range(radius, 0, -max(1, radius // 4)):
                a = int(q_alpha * (1.0 - (r / float(radius)) ** 1.4))
                pygame.draw.circle(glow_surf, (c_key[0], c_key[1], c_key[2], max(10, a)), (radius, radius), r)
            if len(cls._glow_cache) > 256:
                cls._glow_cache.clear()
            cls._glow_cache[cache_key] = glow_surf
        surface.blit(glow_surf, (int(center[0] - radius), int(center[1] - radius)))

    @classmethod
    def _draw_neon_sign(cls, surface: pygame.Surface, rect: pygame.Rect, text: str, neon_color, bg_color=(20, 16, 32), time_tick: float = 0.0):
        rect = cls._norm_rect(rect)
        # 2단계 깜빡임(밝음/살짝 어두움)으로 양자화하여 캐시 적중률 100% 달성
        flicker_step = 1 if math.sin(time_tick * 6.0 + rect.x * 0.1) >= -0.3 else 0
        flicker = 1.0 if flicker_step == 1 else 0.86
        nc_key = (int(neon_color[0]), int(neon_color[1]), int(neon_color[2]))
        bg_key = (int(bg_color[0]), int(bg_color[1]), int(bg_color[2]))
        cache_key = (rect.width, rect.height, text, nc_key, bg_key, flicker_step)

        cached = cls._neon_cache.get(cache_key)
        if cached is None:
            glow_col = tuple(min(255, int(c * flicker)) for c in nc_key)
            cached = pygame.Surface((rect.width + 16, rect.height + 16), pygame.SRCALPHA)
            pygame.draw.rect(cached, (*glow_col, 45), (2, 2, rect.width + 12, rect.height + 12), border_radius=8)
            pygame.draw.rect(cached, (*glow_col, 90), (5, 5, rect.width + 6, rect.height + 6), border_radius=7)

            local_rect = pygame.Rect(8, 8, rect.width, rect.height)
            pygame.draw.rect(cached, bg_key, local_rect, border_radius=6)
            pygame.draw.rect(cached, glow_col, local_rect, width=2, border_radius=6)
            inner = local_rect.inflate(-6, -6)
            if inner.width > 4 and inner.height > 4:
                pygame.draw.rect(
                    cached,
                    (min(255, glow_col[0] + 50), min(255, glow_col[1] + 50), min(255, glow_col[2] + 50)),
                    inner,
                    width=1,
                    border_radius=4,
                )

            font_size = max(11, min(rect.height - 8, int(rect.width / max(2, len(text)) * 1.15)))
            font = cls._get_font(font_size, bold=True)
            txt_shadow = font.render(text, True, glow_col)
            txt_main = font.render(text, True, (255, 250, 245))
            tx = local_rect.centerx - txt_main.get_width() // 2
            ty = local_rect.centery - txt_main.get_height() // 2
            cached.blit(txt_shadow, (tx + 1, ty + 1))
            cached.blit(txt_main, (tx, ty))

            if len(cls._neon_cache) > 64:
                cls._neon_cache.clear()
            cls._neon_cache[cache_key] = cached

        surface.blit(cached, (rect.x - 8, rect.y - 8))

    @staticmethod
    def _extract_interior_level(interior_levels) -> dict:
        """다양한 형태의 interior_levels 입력을 표준 딕셔너리로 정규화합니다."""
        res = {"lighting": 0, "signboard": 0, "prop": 0, "seating": 0, "total": 0}
        if not interior_levels:
            return res
        if isinstance(interior_levels, (int, float)):
            lvl = int(interior_levels)
            return {"lighting": lvl, "signboard": lvl, "prop": lvl, "seating": lvl, "total": lvl * 3}
        if isinstance(interior_levels, dict):
            total = 0
            for k, v in interior_levels.items():
                val = int(v) if isinstance(v, (int, float, bool)) else 1
                total += val
                kl = str(k).lower()
                if any(w in kl for w in ("light", "bulb", "lantern", "lamp", "조명", "알전구")):
                    res["lighting"] = max(res["lighting"], val)
                elif any(w in kl for w in ("sign", "neon", "board", "banner", "간판", "네온")):
                    res["signboard"] = max(res["signboard"], val)
                elif any(w in kl for w in ("radio", "speaker", "music", "prop", "decor", "라디오", "소품")):
                    res["prop"] = max(res["prop"], val)
                elif any(w in kl for w in ("chair", "table", "seat", "stool", "의자", "테이블")):
                    res["seating"] = max(res["seating"], val)
            res["total"] = total
            if total > 0 and max(res["lighting"], res["signboard"], res["prop"], res["seating"]) == 0:
                res["prop"] = 1
                res["signboard"] = 1 if total >= 2 else 0
                res["seating"] = 1 if total >= 3 else 0
        elif isinstance(interior_levels, (list, tuple, set)):
            total = len(interior_levels)
            res["total"] = total
            res["prop"] = 1 if total >= 1 else 0
            res["signboard"] = 1 if total >= 2 else 0
            res["seating"] = 1 if total >= 3 else 0
        return res

    # ==================================================================
    # 1. 국가별 야시장 배경 & 포차 인테리어
    # ==================================================================
    @classmethod
    def draw_country_background(cls, surface: pygame.Surface, rect, country_id: str = "KR", interior_levels=None, time_tick: float = 0.0):
        rect = cls._norm_rect(rect)
        cid = (country_id or "KR").upper()
        levels = cls._extract_interior_level(interior_levels)

        # 애니메이션 프레임 양자화(초당 5프레임, 12프레임 순환)로 배경 서피스 캐싱하여 저사양 PC 렉 완벽 제거
        anim_step = int(time_tick * 5.0) % 12
        cache_key = (
            rect.width,
            rect.height,
            cid,
            levels["lighting"],
            levels["signboard"],
            levels["prop"],
            levels["seating"],
            anim_step,
        )
        cached_bg = cls._bg_cache.get(cache_key)
        if cached_bg is None:
            cached_bg = pygame.Surface((max(1, rect.width), max(1, rect.height)))
            local_rect = pygame.Rect(0, 0, max(1, rect.width), max(1, rect.height))
            q_tick = anim_step / 5.0
            if cid == "JP":
                cls._draw_bg_jp(cached_bg, local_rect, levels, q_tick)
            elif cid == "MX":
                cls._draw_bg_mx(cached_bg, local_rect, levels, q_tick)
            elif cid == "TW":
                cls._draw_bg_tw(cached_bg, local_rect, levels, q_tick)
            elif cid == "CN":
                cls._draw_bg_cn(cached_bg, local_rect, levels, q_tick)
            elif cid == "IN":
                cls._draw_bg_in(cached_bg, local_rect, levels, q_tick)
            elif cid == "US":
                cls._draw_bg_us(cached_bg, local_rect, levels, q_tick)
            elif cid == "RU":
                cls._draw_bg_ru(cached_bg, local_rect, levels, q_tick)
            elif cid == "BR":
                cls._draw_bg_br(cached_bg, local_rect, levels, q_tick)
            else:
                cls._draw_bg_kr(cached_bg, local_rect, levels, q_tick)
            pygame.draw.line(cached_bg, (18, 14, 24), (0, local_rect.bottom - 2), (local_rect.right, local_rect.bottom - 2), 3)
            if len(cls._bg_cache) > 96:
                cls._bg_cache.clear()
            cls._bg_cache[cache_key] = cached_bg

        surface.blit(cached_bg, rect.topleft)

    @classmethod
    def _draw_bg_kr(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """한국 야시장 포차: 밤하늘, 서울타워/빌딩 실루엣, 주황/초록 포장마차 천막, 알전구, 한글 네온사인, 인테리어 소품."""
        cls._draw_vertical_gradient(surface, rect, (15, 18, 42), (46, 32, 68))

        for i in range(18):
            sx = rect.x + (i * 73 + 29) % max(1, rect.width)
            sy = rect.y + 10 + (i * 37) % max(1, int(rect.height * 0.45))
            twinkle = 140 + int(100 * math.sin(time_tick * 2.5 + i))
            pygame.draw.circle(surface, (twinkle, twinkle, min(255, twinkle + 30)), (sx, sy), 1 if i % 3 else 2)

        tower_x = rect.x + int(rect.width * 0.72)
        horizon_y = rect.bottom - int(rect.height * 0.25)
        pygame.draw.ellipse(surface, (22, 20, 40), (tower_x - 140, horizon_y - 45, 280, 110))
        pygame.draw.rect(surface, (30, 28, 52), (tower_x - 4, horizon_y - 115, 8, 75))
        pygame.draw.polygon(surface, (42, 38, 68), [
            (tower_x - 16, horizon_y - 110),
            (tower_x + 16, horizon_y - 110),
            (tower_x + 12, horizon_y - 124),
            (tower_x - 12, horizon_y - 124),
        ])
        pygame.draw.line(surface, (255, 90, 110), (tower_x, horizon_y - 124), (tower_x, horizon_y - 148), 2)
        cls._draw_glow_circle(surface, (tower_x, horizon_y - 148), 10, (255, 70, 90), 110)
        pygame.draw.circle(surface, (255, 220, 220), (tower_x, horizon_y - 148), 3)

        b_widths = [55, 42, 68, 50, 62, 48, 70, 52, 60, 45, 65]
        bx = rect.x
        idx = 0
        while bx < rect.right:
            bw = b_widths[idx % len(b_widths)]
            bh = 55 + (idx * 29) % 85
            by = horizon_y - bh + 20
            pygame.draw.rect(surface, (24, 22, 44), (bx, by, bw - 2, bh + 60))
            for wy in range(by + 8, horizon_y + 10, 12):
                for wx in range(bx + 6, bx + bw - 10, 10):
                    if (wx + wy + idx) % 3 != 0:
                        w_col = (255, 215, 120) if (wx + wy) % 2 == 0 else (120, 210, 255)
                        pygame.draw.rect(surface, w_col, (wx, wy, 5, 6))
            bx += bw
            idx += 1

        tent_wall = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(tent_wall, (255, 190, 120, 18), (0, 36, rect.width, rect.height - 36))
        for gx in range(0, rect.width, 64):
            pygame.draw.line(tent_wall, (255, 230, 190, 28), (gx, 36), (gx, rect.height), 1)
        for gy in range(60, rect.height, 48):
            pygame.draw.line(tent_wall, (255, 230, 190, 22), (0, gy), (rect.width, gy), 1)
        surface.blit(tent_wall, rect.topleft)

        cls._draw_neon_sign(
            surface,
            pygame.Rect(rect.x + 24, rect.y + 52, 86, 42),
            "포차",
            (255, 75, 145),
            time_tick=time_tick,
        )
        cls._draw_neon_sign(
            surface,
            pygame.Rect(rect.right - 128, rect.y + 50, 104, 42),
            "야시장",
            (60, 225, 255),
            time_tick=time_tick + 1.3,
        )

        floor_y = rect.bottom - 14
        chair_positions = [rect.x + 150]
        if levels["seating"] >= 1 or levels["total"] >= 1:
            chair_positions.append(rect.right - 190)
        for cx in chair_positions:
            ch_col = (220, 50, 50) if cx < rect.centerx else (40, 110, 220)
            pygame.draw.rect(surface, ch_col, (cx, floor_y - 28, 26, 10), border_radius=3)
            pygame.draw.line(surface, ch_col, (cx + 3, floor_y - 18), (cx + 1, floor_y), 3)
            pygame.draw.line(surface, ch_col, (cx + 23, floor_y - 18), (cx + 25, floor_y), 3)
            pygame.draw.rect(surface, (180, 35, 35) if cx < rect.centerx else (25, 80, 175), (cx + 5, floor_y - 24, 16, 4))

        if levels["prop"] >= 1 or levels["total"] >= 1:
            rx, ry = rect.x + 28, rect.bottom - 68
            pygame.draw.rect(surface, (110, 68, 38), (rx - 6, ry + 34, 72, 7), border_radius=2)
            pygame.draw.rect(surface, (195, 65, 45), (rx, ry, 60, 34), border_radius=5)
            pygame.draw.rect(surface, (240, 220, 185), (rx + 4, ry + 5, 52, 10), border_radius=2)
            pygame.draw.circle(surface, (45, 42, 50), (rx + 15, ry + 24), 7)
            pygame.draw.circle(surface, (90, 88, 100), (rx + 15, ry + 24), 3)
            pygame.draw.circle(surface, (45, 42, 50), (rx + 45, ry + 24), 7)
            pygame.draw.circle(surface, (90, 88, 100), (rx + 45, ry + 24), 3)
            pygame.draw.line(surface, (210, 210, 220), (rx + 48, ry), (rx + 58, ry - 16), 2)
            note_y = ry - 8 - int(6 * abs(math.sin(time_tick * 3.0)))
            pygame.draw.circle(surface, (255, 230, 110), (rx + 32, note_y), 4)
            pygame.draw.line(surface, (255, 230, 110), (rx + 35, note_y), (rx + 35, note_y - 10), 2)

        if levels["signboard"] >= 1 or levels["total"] >= 2:
            cls._draw_neon_sign(
                surface,
                pygame.Rect(rect.right - 98, rect.bottom - 78, 76, 36),
                "영업중",
                (255, 195, 50),
                time_tick=time_tick + 0.7,
            )

        stripe_w = 36
        awning_h = 34
        idx = 0
        for ax in range(rect.x, rect.right, stripe_w):
            w = min(stripe_w, rect.right - ax)
            is_orange = (idx % 2 == 0)
            base_col = (232, 98, 34) if is_orange else (32, 122, 75)
            dark_col = (188, 72, 20) if is_orange else (20, 88, 52)
            pygame.draw.rect(surface, base_col, (ax, rect.y, w, awning_h))
            pygame.draw.polygon(surface, dark_col, [
                (ax, rect.y + awning_h),
                (ax + w, rect.y + awning_h),
                (ax + w - 4, rect.y + awning_h + 10),
                (ax + 4, rect.y + awning_h + 10),
            ])
            pygame.draw.line(surface, (255, 220, 160), (ax, rect.y + awning_h), (ax + w, rect.y + awning_h), 1)
            idx += 1

        bulb_count = 9 + (3 if levels["lighting"] >= 1 else 0)
        spacing = rect.width / float(bulb_count + 1)
        prev_pt = (rect.x, rect.y + awning_h + 4)
        for i in range(1, bulb_count + 1):
            bx = int(rect.x + i * spacing)
            sway = math.sin(time_tick * 2.4 + i * 0.7) * 3.5
            sag = 10 + int(6 * math.sin(math.pi * i / (bulb_count + 1)))
            by = int(rect.y + awning_h + sag + sway * 0.4)
            cur_pt = (bx + int(sway), by)
            pygame.draw.line(surface, (40, 35, 30), prev_pt, cur_pt, 2)
            prev_pt = cur_pt

            pulse = 0.75 + 0.25 * math.sin(time_tick * 4.2 + i * 1.1)
            glow_r = int(16 + 5 * pulse)
            cls._draw_glow_circle(surface, cur_pt, glow_r, (255, 210, 90), int(95 * pulse))
            pygame.draw.rect(surface, (70, 65, 60), (cur_pt[0] - 2, cur_pt[1] - 4, 5, 4))
            pygame.draw.circle(surface, (255, 235, 130), (cur_pt[0], cur_pt[1] + 3), 5)
            pygame.draw.circle(surface, (255, 255, 220), (cur_pt[0] - 1, cur_pt[1] + 2), 2)
        pygame.draw.line(surface, (40, 35, 30), prev_pt, (rect.right, rect.y + awning_h + 4), 2)

    @classmethod
    def _draw_bg_jp(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """일본 도톤보리 야타이: 강변 네온사인 반영, 목재 지붕, 남색 노렌(천막 커튼), 흔들리는 붉은 제등."""
        cls._draw_vertical_gradient(surface, rect, (12, 16, 38), (32, 28, 62))

        river_y = rect.bottom - 58
        pygame.draw.rect(surface, (14, 22, 46), (rect.x, river_y, rect.width, 58))
        pygame.draw.line(surface, (60, 58, 75), (rect.x, river_y), (rect.right, river_y), 3)
        for rx in range(rect.x + 15, rect.right, 35):
            pygame.draw.line(surface, (50, 48, 65), (rx, river_y - 12), (rx, river_y), 2)
        pygame.draw.line(surface, (75, 72, 92), (rect.x, river_y - 12), (rect.right, river_y - 12), 2)

        neon_cols = [(255, 70, 120), (60, 210, 255), (255, 200, 60), (180, 90, 255)]
        for i in range(16):
            wx = rect.x + ((i * 67) % max(1, rect.width - 40))
            wy = river_y + 8 + (i * 11) % 42
            shift = int(6 * math.sin(time_tick * 3.0 + i))
            ncol = neon_cols[i % len(neon_cols)]
            pygame.draw.line(surface, ncol, (wx + shift, wy), (wx + shift + 24, wy), 2)

        cls._draw_neon_sign(
            surface,
            pygame.Rect(rect.x + 30, rect.y + 68, 92, 40),
            "타코야키",
            (255, 80, 90),
            time_tick=time_tick,
        )
        cls._draw_neon_sign(
            surface,
            pygame.Rect(rect.right - 126, rect.y + 68, 96, 40),
            "도톤보리",
            (70, 215, 255),
            time_tick=time_tick + 1.0,
        )

        pygame.draw.rect(surface, (118, 74, 42), (rect.x + 8, rect.y + 20, 14, rect.height - 20))
        pygame.draw.rect(surface, (118, 74, 42), (rect.right - 22, rect.y + 20, 14, rect.height - 20))
        pygame.draw.rect(surface, (92, 54, 28), (rect.x, rect.y, rect.width, 22))
        pygame.draw.rect(surface, (138, 86, 46), (rect.x, rect.y + 18, rect.width, 8))
        for rx in range(rect.x, rect.right, 28):
            pygame.draw.line(surface, (70, 40, 20), (rx, rect.y), (rx - 6, rect.y + 24), 2)

        noren_panels = 6
        panel_w = (rect.width - 48) // noren_panels
        for i in range(noren_panels):
            px = rect.x + 24 + i * panel_w
            sway = int(2 * math.sin(time_tick * 2.0 + i * 0.6))
            n_rect = pygame.Rect(px + 3 + sway, rect.y + 26, panel_w - 6, 36)
            pygame.draw.rect(surface, (26, 44, 98), n_rect, border_radius=3)
            pygame.draw.rect(surface, (42, 68, 138), n_rect, width=1, border_radius=3)
            pygame.draw.circle(surface, (235, 240, 250), (n_rect.centerx, n_rect.centery + 2), 9, width=2)
            pygame.draw.line(surface, (235, 240, 250), (n_rect.left + 6, n_rect.bottom - 5), (n_rect.right - 6, n_rect.bottom - 5), 1)

        lantern_cnt = 5 + (2 if levels["lighting"] >= 1 else 0)
        l_space = rect.width / float(lantern_cnt + 1)
        for i in range(1, lantern_cnt + 1):
            lx = int(rect.x + i * l_space)
            sway = int(4 * math.sin(time_tick * 2.6 + i * 0.9))
            ly = rect.y + 68
            cx, cy = lx + sway, ly
            cls._draw_glow_circle(surface, (cx, cy), 22, (255, 90, 50), 95)
            pygame.draw.line(surface, (40, 30, 25), (lx, rect.y + 26), (cx, cy - 14), 2)
            l_rect = pygame.Rect(cx - 11, cy - 13, 22, 26)
            pygame.draw.ellipse(surface, (225, 42, 38), l_rect)
            pygame.draw.ellipse(surface, (255, 150, 70), l_rect.inflate(-8, -6))
            for ry_off in (-5, 0, 5):
                pygame.draw.line(surface, (160, 25, 20), (cx - 10, cy + ry_off), (cx + 10, cy + ry_off), 1)
            pygame.draw.rect(surface, (30, 25, 25), (cx - 6, cy - 15, 12, 4))
            pygame.draw.rect(surface, (30, 25, 25), (cx - 6, cy + 12, 12, 4))

    @classmethod
    def _draw_bg_mx(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """멕시코 타코 스트리트: 보랏빛 밤하늘, 타코 트럭 어닝, 알록달록한 파펠 피카도, 선인장 네온사인."""
        cls._draw_vertical_gradient(surface, rect, (28, 16, 48), (74, 34, 62))

        wall_y = rect.bottom - 95
        pygame.draw.rect(surface, (42, 24, 48), (rect.x, wall_y, rect.width, 95))
        for ax in range(rect.x + 20, rect.right - 30, 72):
            pygame.draw.circle(surface, (28, 16, 36), (ax + 22, wall_y + 42), 20)
            pygame.draw.rect(surface, (28, 16, 36), (ax + 2, wall_y + 42, 40, 53))

        cac_x, cac_y = rect.x + 56, rect.y + 92
        cls._draw_glow_circle(surface, (cac_x, cac_y), 34, (50, 255, 120), 95)
        pygame.draw.rect(surface, (22, 32, 28), (cac_x - 28, cac_y - 32, 56, 64), border_radius=8)
        pygame.draw.rect(surface, (65, 255, 130), (cac_x - 28, cac_y - 32, 56, 64), width=2, border_radius=8)
        pygame.draw.line(surface, (80, 255, 145), (cac_x, cac_y + 20), (cac_x, cac_y - 18), 5)
        pygame.draw.lines(surface, (80, 255, 145), False, [(cac_x - 13, cac_y - 10), (cac_x - 13, cac_y + 2), (cac_x, cac_y + 2)], 4)
        pygame.draw.lines(surface, (80, 255, 145), False, [(cac_x + 13, cac_y - 14), (cac_x + 13, cac_y - 2), (cac_x, cac_y - 2)], 4)

        cls._draw_neon_sign(
            surface,
            pygame.Rect(rect.right - 132, rect.y + 66, 106, 42),
            "TACOS",
            (255, 185, 45),
            time_tick=time_tick,
        )

        mx_stripes = [(28, 148, 82), (245, 240, 225), (218, 52, 48), (245, 178, 42)]
        sw = 34
        idx = 0
        for ax in range(rect.x, rect.right, sw):
            w = min(sw, rect.right - ax)
            col = mx_stripes[idx % len(mx_stripes)]
            pygame.draw.rect(surface, col, (ax, rect.y, w, 28))
            pygame.draw.circle(surface, col, (ax + w // 2, rect.y + 28), w // 2)
            idx += 1

        garland_cols = [(255, 75, 135), (55, 225, 210), (255, 210, 55), (175, 95, 255), (90, 240, 95), (255, 120, 50)]
        flag_w = 38
        pygame.draw.line(surface, (230, 220, 200), (rect.x, rect.y + 38), (rect.right, rect.y + 38), 2)
        f_idx = 0
        for fx in range(rect.x + 12, rect.right - 20, flag_w):
            col = garland_cols[f_idx % len(garland_cols)]
            sway = int(3 * math.sin(time_tick * 3.0 + f_idx * 0.7))
            pts = [
                (fx, rect.y + 38),
                (fx + flag_w - 8, rect.y + 38),
                (fx + (flag_w - 8) // 2 + sway, rect.y + 68),
            ]
            pygame.draw.polygon(surface, col, pts)
            pygame.draw.circle(surface, (38, 20, 48), (fx + (flag_w - 8) // 2 + sway // 2, rect.y + 49), 3)
            f_idx += 1

    @classmethod
    def _draw_bg_tw(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """대만 스린 야시장: 붉은 홍등 행렬과 황금빛 야시장 현판."""
        cls._draw_vertical_gradient(surface, rect, (24, 12, 32), (62, 22, 38))

        pygame.draw.rect(surface, (125, 28, 32), (rect.x + 14, rect.y + 24, 16, rect.height - 24))
        pygame.draw.rect(surface, (125, 28, 32), (rect.right - 30, rect.y + 24, 16, rect.height - 24))
        pygame.draw.rect(surface, (215, 165, 55), (rect.x + 14, rect.y + 24, 16, rect.height - 24), width=2)
        pygame.draw.rect(surface, (215, 165, 55), (rect.right - 30, rect.y + 24, 16, rect.height - 24), width=2)

        board_rect = pygame.Rect(rect.centerx - 95, rect.y + 12, 190, 42)
        cls._draw_glow_circle(surface, board_rect.center, 70, (255, 190, 60), 75)
        pygame.draw.rect(surface, (85, 18, 22), board_rect, border_radius=8)
        pygame.draw.rect(surface, (245, 195, 65), board_rect, width=3, border_radius=8)
        pygame.draw.rect(surface, (255, 225, 120), board_rect.inflate(-8, -8), width=1, border_radius=5)
        font = cls._get_font(20, bold=True)
        txt = font.render("스린 야시장", True, (255, 225, 95))
        surface.blit(txt, (board_rect.centerx - txt.get_width() // 2, board_rect.centery - txt.get_height() // 2))

        for row in range(2):
            ry = rect.y + 64 + row * 46
            pygame.draw.line(surface, (90, 50, 30), (rect.x, ry - 14), (rect.right, ry - 14), 2)
            cnt = 7 if row == 0 else 6
            sp = rect.width / float(cnt + 1)
            for i in range(1, cnt + 1):
                lx = int(rect.x + i * sp + (15 if row == 1 else 0))
                if lx > rect.right - 25:
                    continue
                sway = int(3.5 * math.sin(time_tick * 2.5 + i * 0.8 + row))
                cx = lx + sway
                cls._draw_glow_circle(surface, (cx, ry), 20, (255, 70, 40), 90)
                pygame.draw.ellipse(surface, (220, 32, 32), (cx - 12, ry - 10, 24, 20))
                pygame.draw.ellipse(surface, (255, 120, 50), (cx - 6, ry - 7, 12, 14))
                pygame.draw.rect(surface, (235, 185, 55), (cx - 5, ry - 12, 10, 3))
                pygame.draw.rect(surface, (235, 185, 55), (cx - 5, ry + 9, 10, 3))
                pygame.draw.line(surface, (245, 195, 60), (cx, ry + 12), (cx + sway // 2, ry + 20), 2)

    @classmethod
    def _draw_bg_cn(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """중국 사천·상하이 야시장: 붉은 목조 패루(牌樓), 황금 용문양 현판, 홍등과 마라 네온사인."""
        cls._draw_vertical_gradient(surface, rect, (32, 12, 18), (78, 22, 28))
        pygame.draw.rect(surface, (148, 28, 32), (rect.x + 12, rect.y + 18, 18, rect.height - 18))
        pygame.draw.rect(surface, (148, 28, 32), (rect.right - 30, rect.y + 18, 18, rect.height - 18))
        pygame.draw.rect(surface, (245, 195, 65), (rect.x, rect.y, rect.width, 20))
        pygame.draw.rect(surface, (175, 32, 36), (rect.x, rect.y + 18, rect.width, 8))
        if rect.width >= 320:
            cls._draw_neon_sign(surface, pygame.Rect(rect.x + 36, rect.y + 52, 98, 40), "마라야시장", (255, 72, 62), time_tick=time_tick)
            cls._draw_neon_sign(surface, pygame.Rect(rect.right - 134, rect.y + 52, 98, 40), "화궈·양꼬치", (255, 205, 58), time_tick=time_tick + 0.9)
        else:
            cls._draw_neon_sign(surface, pygame.Rect(rect.centerx - 54, rect.y + 52, 108, 38), "마라야시장", (255, 205, 58), time_tick=time_tick)
        for i in range(1, 7):
            lx = int(rect.x + i * (rect.width / 7.0))
            sway = int(3 * math.sin(time_tick * 2.6 + i))
            ly = rect.y + 62
            cls._draw_glow_circle(surface, (lx + sway, ly), 22, (255, 85, 45), 95)
            pygame.draw.ellipse(surface, (232, 38, 38), (lx + sway - 13, ly - 11, 26, 22))
            pygame.draw.rect(surface, (250, 205, 65), (lx + sway - 6, ly - 13, 12, 3))
            pygame.draw.rect(surface, (250, 205, 65), (lx + sway - 6, ly + 10, 12, 3))

    @classmethod
    def _draw_bg_in(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """인도 델리·뭄바이 바자르: 황금 무굴 아치돔 실루엣, 사프란 천막, 마리골드 꽃줄 장식."""
        cls._draw_vertical_gradient(surface, rect, (28, 16, 46), (82, 42, 28))
        horizon_y = rect.bottom - 38
        dome_x = rect.centerx
        pygame.draw.circle(surface, (46, 26, 58), (dome_x, horizon_y - 42), 44)
        pygame.draw.polygon(surface, (46, 26, 58), [(dome_x - 16, horizon_y - 72), (dome_x + 16, horizon_y - 72), (dome_x, horizon_y - 102)])
        for arch_x in range(rect.x + 24, rect.right - 40, 84):
            pygame.draw.arc(surface, (245, 182, 55), (arch_x, rect.y + 24, 68, 48), 0, math.pi, 3)
        if rect.width >= 320:
            cls._draw_neon_sign(surface, pygame.Rect(rect.x + 28, rect.y + 56, 98, 40), "탄두리·커리", (255, 168, 42), time_tick=time_tick)
            cls._draw_neon_sign(surface, pygame.Rect(rect.right - 128, rect.y + 56, 98, 40), "SPICE BAZAAR", (72, 232, 188), time_tick=time_tick + 1.1)
        else:
            cls._draw_neon_sign(surface, pygame.Rect(rect.centerx - 58, rect.y + 56, 116, 38), "SPICE BAZAAR", (255, 168, 42), time_tick=time_tick)
        for fx in range(rect.x + 18, rect.right - 18, 28):
            fy = rect.y + 30 + int(4 * math.sin(time_tick * 2.5 + fx * 0.05))
            col = (255, 162, 36) if (fx // 28) % 2 == 0 else (255, 218, 58)
            pygame.draw.circle(surface, col, (fx, fy), 6)

    @classmethod
    def _draw_bg_us(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """미국 뉴욕·텍사스 푸드트럭 파크: 마천루와 브루클린 브리지 실루엣, 성조기 컬러 네온사인."""
        cls._draw_vertical_gradient(surface, rect, (14, 22, 48), (38, 46, 82))
        horizon_y = rect.bottom - 42
        for bx in range(rect.x, rect.right, 52):
            bh = 55 + ((bx * 17) % 75)
            pygame.draw.rect(surface, (22, 30, 58), (bx, horizon_y - bh, 46, bh + 42))
        stripe_cols = [(212, 46, 56), (242, 244, 250), (42, 88, 188)]
        for idx, ax in enumerate(range(rect.x, rect.right, 38)):
            pygame.draw.rect(surface, stripe_cols[idx % 3], (ax, rect.y, min(38, rect.right - ax), 26))
        if rect.width >= 320:
            cls._draw_neon_sign(surface, pygame.Rect(rect.x + 28, rect.y + 52, 106, 40), "BURGER & BBQ", (255, 82, 88), time_tick=time_tick)
            cls._draw_neon_sign(surface, pygame.Rect(rect.right - 134, rect.y + 52, 106, 40), "FOOD TRUCK", (78, 196, 255), time_tick=time_tick + 0.8)
        else:
            cls._draw_neon_sign(surface, pygame.Rect(rect.centerx - 58, rect.y + 52, 116, 38), "FOOD TRUCK", (78, 196, 255), time_tick=time_tick)

    @classmethod
    def _draw_bg_ru(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """러시아 모스크바 붉은광장 윈터 마켓: 성 바실리 양파돔 실루엣, 눈송이, 따뜻한 전구 가랜드."""
        cls._draw_vertical_gradient(surface, rect, (16, 24, 52), (44, 58, 96))
        horizon_y = rect.bottom - 36
        dome_cols = [(228, 58, 62), (58, 168, 245), (248, 192, 52)]
        for i, dx in enumerate((rect.centerx - 70, rect.centerx, rect.centerx + 70)):
            dc = dome_cols[i % 3]
            pygame.draw.circle(surface, dc, (dx, horizon_y - 44), 22)
            pygame.draw.polygon(surface, dc, [(dx - 12, horizon_y - 56), (dx + 12, horizon_y - 56), (dx, horizon_y - 82)])
        for i in range(18):
            sx = rect.x + ((i * 61 + int(time_tick * 12)) % max(1, rect.width))
            sy = rect.y + 24 + ((i * 29 + int(time_tick * 18)) % max(1, rect.height - 32))
            pygame.draw.circle(surface, (235, 245, 255), (sx, sy), 2)
        if rect.width >= 320:
            cls._draw_neon_sign(surface, pygame.Rect(rect.x + 28, rect.y + 52, 102, 40), "샤슬릭·블리니", (255, 192, 68), time_tick=time_tick)
            cls._draw_neon_sign(surface, pygame.Rect(rect.right - 130, rect.y + 52, 102, 40), "WINTER FAIR", (118, 224, 255), time_tick=time_tick + 1.2)
        else:
            cls._draw_neon_sign(surface, pygame.Rect(rect.centerx - 58, rect.y + 52, 116, 38), "WINTER FAIR", (255, 192, 68), time_tick=time_tick)

    @classmethod
    def _draw_bg_br(cls, surface: pygame.Surface, rect: pygame.Rect, levels: dict, time_tick: float):
        """브라질 리우·상파울루 해변 페이라: 야자수 실루엣, 카니발 그린&골드 어닝, 슈하스코 네온사인."""
        cls._draw_vertical_gradient(surface, rect, (16, 42, 48), (38, 86, 62))
        br_cols = [(38, 168, 78), (248, 206, 48), (38, 112, 212)]
        for idx, ax in enumerate(range(rect.x, rect.right, 38)):
            pygame.draw.rect(surface, br_cols[idx % 3], (ax, rect.y, min(38, rect.right - ax), 26))
        if rect.width >= 320:
            cls._draw_neon_sign(surface, pygame.Rect(rect.x + 28, rect.y + 52, 106, 40), "CHURRASCO", (255, 212, 52), time_tick=time_tick)
            cls._draw_neon_sign(surface, pygame.Rect(rect.right - 134, rect.y + 52, 106, 40), "RIO FEIRA", (72, 242, 128), time_tick=time_tick + 0.9)
        else:
            cls._draw_neon_sign(surface, pygame.Rect(rect.centerx - 58, rect.y + 52, 116, 38), "CHURRASCO", (255, 212, 52), time_tick=time_tick)

    # ==================================================================
    # 2. 9개국 32인 지역별 셰프(포차 마스터) 레트로 도트(Pixel Art) 아바타 렌더링
    # ==================================================================
    @classmethod
    def _build_chef_pixel_canvas(cls, character_id: str, st: str, anim_frame: int, blink_frame: int) -> pygame.Surface:
        """
        28x28 네이티브 픽셀 그리드(외곽 도트 액자 2px + 내부 24x24 캐릭터 도트)를 생성합니다.
        32인 모든 지역별 셰프의 고유 스킨/헤어/모자/수염/선글라스/조리도구 도트를 개성 있게 합성합니다.
        """
        cache_key = (character_id, st, anim_frame, blink_frame)
        if cache_key in cls._chef_pixel_cache:
            return cls._chef_pixel_cache[cache_key]

        try:
            from data.characters import CHARACTERS
            spec = CHARACTERS.get(character_id) or CHARACTERS.get("chef_kr", {})
        except Exception:
            spec = {}

        archetype = str(spec.get("archetype", "") or "")
        if archetype not in _CHEF_PIXEL_MAPS:
            if "jp" in character_id:
                archetype = "chef_jp"
            elif "mx" in character_id:
                archetype = "chef_mx"
            elif "tw" in character_id:
                archetype = "chef_tw"
            else:
                archetype = "chef_kr"

        theme_col = tuple(spec.get("theme_color", (242, 122, 48)))
        accent_col = tuple(spec.get("accent_color", (255, 216, 76)))
        skin_col = tuple(spec.get("skin_color", (255, 218, 185)))
        hair_col = tuple(spec.get("hair_color", (48, 34, 28)))
        apron_col = tuple(spec.get("apron_color", theme_col))
        hat_col = tuple(spec.get("hat_color", theme_col))
        hat_style = str(spec.get("hat_style", "") or "")
        facial_style = str(spec.get("facial_style", "smile") or "smile")
        prop_style = str(spec.get("prop_style", "") or "")

        grid_w, grid_h = 28, 28
        canvas = pygame.Surface((grid_w, grid_h), pygame.SRCALPHA)

        bg_dark = (max(14, theme_col[0] // 5), max(14, theme_col[1] // 5), max(20, theme_col[2] // 5))
        bg_checker = (min(255, bg_dark[0] + 12), min(255, bg_dark[1] + 12), min(255, bg_dark[2] + 14))
        border_col = theme_col
        if st == "SKILL":
            border_col = (255, 232, 68) if anim_frame % 2 == 0 else (255, 165, 38)
        elif st == "LOCKED":
            bg_dark = (22, 22, 30)
            bg_checker = (28, 28, 38)
            border_col = (92, 96, 112)

        # 1) 도트 체크무늬 배경 & 픽셀 아케이드 액자 프레임
        for y in range(1, grid_h - 1):
            for x in range(1, grid_w - 1):
                if (x in (1, grid_w - 2)) and (y in (1, grid_h - 2)):
                    continue
                col = bg_checker if (x + y) % 2 == 0 else bg_dark
                canvas.set_at((x, y), col)

        # SKILL 상태일 때 배경 방사형 골드 도트 후광
        if st == "SKILL":
            aura_ring = (255, 208, 55) if anim_frame == 0 else (255, 138, 36)
            for y in range(3, grid_h - 3):
                for x in range(3, grid_w - 3):
                    dist_sq = (x - 13.5) ** 2 + (y - 14.0) ** 2
                    if 52 <= dist_sq <= 82 and (x + y + anim_frame) % 2 == 0:
                        canvas.set_at((x, y), aura_ring)

        # 2) 캐릭터별 커스텀 팔레트 합성
        base_pal = dict(_CHEF_PALETTES.get(archetype, _CHEF_PALETTES["chef_kr"]))
        if character_id not in ("chef_kr", "chef_jp", "chef_mx", "chef_tw"):
            skin_hi = tuple(min(255, c + 18) for c in skin_col)
            skin_sh = tuple(max(20, c - 36) for c in skin_col)
            hair_hi = tuple(min(255, c + 28) for c in hair_col)
            apron_sh = tuple(max(15, c - 42) for c in apron_col)
            hat_sh = tuple(max(15, c - 40) for c in hat_col)
            base_pal.update({
                "s": skin_col,
                "S": skin_hi,
                "d": skin_sh,
                "H": hair_col,
                "h": hair_hi,
                "R": apron_col,
                "r": apron_sh,
                "N": apron_col,
                "n": apron_sh,
                "G": apron_col,
                "M": hat_col,
                "u": hat_sh,
                "A": accent_col,
                "Y": accent_col,
                "J": accent_col,
            })

        raw_map = _CHEF_PIXEL_MAPS.get(archetype, _CHEF_PIXEL_MAPS["chef_kr"])
        body_dy = 1 if (st != "LOCKED" and anim_frame == 1) else 0
        tool_dy = -1 if (st in ("COOKING", "SKILL") and anim_frame == 1) else 0

        char_layer = pygame.Surface((24, 24), pygame.SRCALPHA)
        for ry, row_str in enumerate(raw_map):
            for rx, ch in enumerate(row_str[:24]):
                if ch == ".":
                    continue
                col = base_pal.get(ch, (255, 255, 255))
                if ry <= 5 and ch in ("R", "W", "M") and character_id not in ("chef_kr", "chef_jp", "chef_mx", "chef_tw"):
                    col = hat_col if ch != "W" else accent_col

                if 7 <= ry <= 9 and 5 <= rx <= 16 and ch in ("e", "W"):
                    if st == "SKILL":
                        col = (255, 238, 65) if ch == "e" else (255, 255, 255)
                    elif blink_frame == 1 and ry == 8:
                        col = base_pal["s"]

                dy = tool_dy if (rx >= 18 and st in ("COOKING", "SKILL")) else body_dy
                ty = ry + dy
                if 0 <= ty < 24:
                    char_layer.set_at((rx, ty), col)

        # 2-B) 32인 지역별 마스터 전용 모자/헤드기어 & 수염/선글라스 & 프롭 오버레이
        if character_id not in ("chef_kr", "chef_jp", "chef_mx", "chef_tw"):
            outline = (20, 16, 28)
            # (1) 모자 / 헤드기어 변형
            if "turban" in hat_style:
                # 인도 왕실/펀자브 터번 (풍성한 주름 + 중앙 보석 장식)
                for ty_off in range(1, 6):
                    y_pos = ty_off + body_dy
                    if 0 <= y_pos < 24:
                        for tx in range(4, 18):
                            if tx in (4, 17) or ty_off == 1:
                                char_layer.set_at((tx, y_pos), outline)
                            else:
                                c = hat_col if (tx + ty_off) % 3 != 0 else accent_col
                                char_layer.set_at((tx, y_pos), c)
                # 터번 중앙 보석 & 깃털
                for px, py, pc in ((10, 2, (255, 255, 255)), (11, 2, accent_col), (11, 1, accent_col), (10, 3, (235, 45, 65))):
                    if 0 <= py + body_dy < 24:
                        char_layer.set_at((px, py + body_dy), pc)
            elif "ushanka" in hat_style or "papakha" in hat_style:
                # 러시아 털모자 우샨카 / 코카서스 파파하 (귀달이 + 붉은 별/눈꽃 배지)
                fur_hi = tuple(min(255, c + 22) for c in hat_col)
                for ty_off in range(1, 6):
                    y_pos = ty_off + body_dy
                    if 0 <= y_pos < 24:
                        for tx in range(4, 18):
                            char_layer.set_at((tx, y_pos), hat_col if (tx + ty_off) % 2 == 0 else fur_hi)
                # 양옆 귀달이(ear flaps)
                for ty_off in range(5, 10):
                    y_pos = ty_off + body_dy
                    if 0 <= y_pos < 24:
                        for tx in (4, 5, 16, 17):
                            char_layer.set_at((tx, y_pos), hat_col)
                # 정면 붉은 별 엠블럼
                for px, py in ((10, 3), (11, 3), (10, 2)):
                    if 0 <= py + body_dy < 24:
                        char_layer.set_at((px, py + body_dy), (238, 48, 52))
            elif hat_style in ("cowboy", "fedora"):
                # 텍사스 카우보이 스테etson / 뉴올리언스 페도라
                brim_y = 4 + body_dy
                if 0 <= brim_y < 24:
                    for tx in range(1, 21):
                        char_layer.set_at((tx, brim_y), hat_col)
                for ty_off in (1, 2, 3):
                    y_pos = ty_off + body_dy
                    if 0 <= y_pos < 24:
                        for tx in range(5, 17):
                            char_layer.set_at((tx, y_pos), accent_col if ty_off == 3 else hat_col)
            elif hat_style == "chef_toque":
                # 하이엔드 화이트/골드 셰프 토크(높은 요리사 모자)
                for ty_off in range(0, 5):
                    y_pos = ty_off + body_dy
                    if 0 <= y_pos < 24:
                        for tx in range(5, 17):
                            if ty_off == 4:
                                char_layer.set_at((tx, y_pos), accent_col)
                            else:
                                char_layer.set_at((tx, y_pos), hat_col if tx % 2 == 0 else (230, 235, 245))
            elif hat_style in ("doppa_cap", "imperial_cap"):
                # 신장 위구르 도파 모자 / 베이징 전통 비단 모자
                for ty_off in range(1, 5):
                    y_pos = ty_off + body_dy
                    if 0 <= y_pos < 24:
                        for tx in range(5, 17):
                            char_layer.set_at((tx, y_pos), accent_col if (tx + ty_off) % 3 == 0 else hat_col)
            elif hat_style in ("carnival_crown", "flower_crown", "sari_crown", "jasmine_hair"):
                # 브라질 카니발 왕관 / 오악사카 꽃화관 / 인도 사리 금관
                for tx in range(5, 17):
                    y_pos = 3 + body_dy
                    if 0 <= y_pos < 24:
                        char_layer.set_at((tx, y_pos), accent_col if tx % 2 == 0 else hat_col)
                    if tx in (6, 9, 12, 15) and 0 <= 2 + body_dy < 24:
                        char_layer.set_at((tx, 2 + body_dy), (255, 95, 155) if tx % 2 == 0 else (72, 238, 148))

            # (2) 얼굴 개성 (선글라스 / 턱수염 / 콧수염 / 윙크)
            if facial_style == "sunglasses":
                sy = 8 + body_dy
                if 0 <= sy < 24 and 0 <= sy + 1 < 24:
                    for tx in range(6, 16):
                        char_layer.set_at((tx, sy), (24, 26, 36))
                        if tx in (7, 8, 9, 12, 13, 14):
                            char_layer.set_at((tx, sy + 1), (32, 38, 54))
                    char_layer.set_at((7, sy), (160, 235, 255))
                    char_layer.set_at((12, sy), (160, 235, 255))
            elif facial_style == "beard":
                by = 11 + body_dy
                for dy_b in range(0, 3):
                    if 0 <= by + dy_b < 24:
                        for tx in range(6 + dy_b, 16 - dy_b):
                            if not (dy_b == 0 and tx in (10, 11)):
                                char_layer.set_at((tx, by + dy_b), hair_col)
            elif facial_style == "mustache":
                my = 11 + body_dy
                if 0 <= my < 24:
                    for tx in (7, 8, 9, 12, 13, 14):
                        char_layer.set_at((tx, my), hair_col)
            elif facial_style == "wink":
                wy = 8 + body_dy
                if 0 <= wy < 24:
                    for tx in (7, 8, 9):
                        char_layer.set_at((tx, wy), base_pal["s"])
                    char_layer.set_at((8, wy), (32, 24, 36))

        # LOCKED 상태일 때 모든 불투명 픽셀을 다크 실루엣으로 일괄 변환
        if st == "LOCKED":
            for y in range(24):
                for x in range(24):
                    px_col = char_layer.get_at((x, y))
                    if px_col[3] > 0:
                        is_edge = (px_col[0] < 35 and px_col[1] < 35 and px_col[2] < 45)
                        char_layer.set_at((x, y), (18, 20, 30) if is_edge else (44, 48, 66))

        # SKILL 상태일 때 캐릭터 외곽 1px 황금 픽셀 오라 테두리 추가
        if st == "SKILL":
            aura_col = (255, 238, 95) if anim_frame == 0 else (255, 180, 45)
            for y in range(24):
                for x in range(24):
                    if char_layer.get_at((x, y))[3] == 0:
                        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                            if 0 <= nx < 24 and 0 <= ny < 24 and char_layer.get_at((nx, ny))[3] > 0:
                                canvas.set_at((x + 2, y + 2), aura_col)
                                break

        canvas.blit(char_layer, (2, 2))

        # 3) 상태별 도트 이펙트 오버레이 (COOKING: 도트 음표/땀방울, SKILL: 도트 십자 스파클, LOCKED: 도트 자물쇠)
        if st == "COOKING":
            ny = 4 if anim_frame == 0 else 3
            note_col = (255, 232, 85)
            for px, py in ((4, ny + 2), (5, ny + 2), (5, ny + 1), (5, ny), (6, ny)):
                canvas.set_at((px, py), note_col)
        elif st == "SKILL":
            sparkles = [(4, 4), (23, 4), (4, 22), (23, 22)] if anim_frame == 0 else [(5, 6), (22, 5), (5, 20), (22, 21)]
            for sx, sy in sparkles:
                canvas.set_at((sx, sy), (255, 255, 255))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    canvas.set_at((sx + dx, sy + dy), (255, 225, 70))
        elif st == "LOCKED":
            lock_pal = {
                "O": (15, 15, 22),
                "W": (235, 240, 250),
                "0": (180, 190, 205),
                "g": (140, 150, 168),
                "m": (110, 118, 135),
                "Y": (255, 212, 62),
                "y": (208, 152, 32),
            }
            lx0, ly0 = (grid_w - 9) // 2, (grid_h - 10) // 2 + 1
            for ry, rstr in enumerate(_PADLOCK_PIXEL_MAP):
                for rx, ch in enumerate(rstr):
                    if ch != "." and ch in lock_pal:
                        canvas.set_at((lx0 + rx, ly0 + ry), lock_pal[ch])

        # 4) 도트 아케이드 액자 외곽선 & 모서리 스터드 리벳
        outline_dark = (16, 14, 24)
        stud_light = accent_col if st != "LOCKED" else (140, 145, 165)
        for x in range(2, grid_w - 2):
            canvas.set_at((x, 0), outline_dark)
            canvas.set_at((x, 1), border_col)
            canvas.set_at((x, grid_h - 2), border_col)
            canvas.set_at((x, grid_h - 1), outline_dark)
        for y in range(2, grid_h - 2):
            canvas.set_at((0, y), outline_dark)
            canvas.set_at((1, y), border_col)
            canvas.set_at((grid_w - 2, y), border_col)
            canvas.set_at((grid_w - 1, y), outline_dark)
        for cx, cy in ((2, 2), (grid_w - 3, 2), (2, grid_h - 3), (grid_w - 3, grid_h - 3)):
            canvas.set_at((cx, cy), stud_light)

        if len(cls._chef_pixel_cache) > 512:
            cls._chef_pixel_cache.clear()
        cls._chef_pixel_cache[cache_key] = canvas
        return canvas

    @classmethod
    def draw_chef_avatar(cls, surface: pygame.Surface, rect, character_id: str = "chef_kr", state: str = "IDLE", time_tick: float = 0.0):
        rect = cls._norm_rect(rect)
        if isinstance(character_id, dict):
            character_id = str(character_id.get("id", "chef_kr"))
        cid = str(character_id or "chef_kr").lower()
        st = (state or "IDLE").upper()

        try:
            from data.characters import CHARACTERS
            if cid in CHARACTERS:
                chef_key = cid
            elif "jp" in cid or "kenji" in cid:
                chef_key = "chef_jp"
            elif "mx" in cid or "diego" in cid:
                chef_key = "chef_mx"
            elif "tw" in cid or "meiling" in cid:
                chef_key = "chef_tw"
            else:
                chef_key = "chef_kr"
        except Exception:
            chef_key = "chef_kr"

        if st == "SKILL":
            anim_frame = int(time_tick * 8.0) % 2
            blink_frame = 0
        elif st == "COOKING":
            anim_frame = int(time_tick * 6.0) % 2
            blink_frame = 0
        elif st == "LOCKED":
            anim_frame = 0
            blink_frame = 0
        else:
            anim_frame = int(time_tick * 2.5) % 2
            blink_frame = 1 if (int(time_tick * 3.0) % 11 == 0) else 0

        pixel_canvas = cls._build_chef_pixel_canvas(chef_key, st, anim_frame, blink_frame)
        w, h = max(1, rect.width), max(1, rect.height)
        scale_key = (chef_key, st, anim_frame, blink_frame, w, h)
        scaled_avatar = cls._chef_scaled_cache.get(scale_key)
        if scaled_avatar is None:
            scaled_avatar = pygame.transform.scale(pixel_canvas, (w, h))
            if len(cls._chef_scaled_cache) > 256:
                cls._chef_scaled_cache.clear()
            cls._chef_scaled_cache[scale_key] = scaled_avatar
        surface.blit(scaled_avatar, rect.topleft)

    # ==================================================================
    # 3. 손님 캐릭터 & 5단계 감정 표정 애니메이션
    # ==================================================================
    @classmethod
    def draw_customer(cls, surface: pygame.Surface, rect, customer_type: str = "student", mood="HAPPY", time_tick: float = 0.0):
        rect = cls._norm_rect(rect)
        ctype = (customer_type or "student").lower()

        if isinstance(mood, (int, float)):
            ratio = float(mood)
            if ratio >= 0.7:
                mood_str = "HAPPY"
            elif ratio >= 0.45:
                mood_str = "NORMAL"
            elif ratio >= 0.2:
                mood_str = "WARN"
            else:
                mood_str = "ANGRY"
        else:
            mood_str = str(mood or "HAPPY").upper()

        if mood_str == "ANGRY":
            shake_x = int(math.sin(time_tick * 24.0) * 2.5)
            bounce_y = int(abs(math.sin(time_tick * 8.0)) * 3.0)
        elif mood_str == "WARN":
            shake_x = int(math.sin(time_tick * 14.0) * 1.2)
            bounce_y = int(math.sin(time_tick * 5.0) * 2.0)
        elif mood_str == "FEVER":
            shake_x = 0
            bounce_y = -int(abs(math.sin(time_tick * 9.0)) * 6.0)
        else:
            shake_x = 0
            bounce_y = int(math.sin(time_tick * 3.2 + rect.x * 0.05) * 2.2)

        cx = rect.centerx + shake_x
        cy = rect.centery + 4 + bounce_y
        scale = min(rect.width, rect.height) / 105.0
        r_head = max(13, int(21 * scale))

        if mood_str == "FEVER":
            cls._draw_glow_circle(surface, (cx, cy), int(42 * scale), (255, 110, 200), 105)

        body_w = max(26, int(50 * scale))
        body_h = max(20, int(36 * scale))
        body_rect = pygame.Rect(cx - body_w // 2, cy + r_head - 4, body_w, body_h)

        if "worker" in ctype or "office" in ctype:
            pygame.draw.rect(surface, (48, 54, 68), body_rect, border_radius=8)
            pygame.draw.polygon(surface, (240, 242, 248), [
                (cx - 8, body_rect.top),
                (cx + 8, body_rect.top),
                (cx, body_rect.top + 18),
            ])
            pygame.draw.line(surface, (210, 45, 55), (cx, body_rect.top + 3), (cx, body_rect.top + 22), 4)
        elif "tourist" in ctype or "foreign" in ctype:
            pygame.draw.rect(surface, (42, 175, 195), body_rect, border_radius=8)
            pygame.draw.line(surface, (60, 50, 45), (cx - 10, body_rect.top + 2), (cx, body_rect.top + 18), 2)
            pygame.draw.line(surface, (60, 50, 45), (cx + 10, body_rect.top + 2), (cx, body_rect.top + 18), 2)
            cam_rect = pygame.Rect(cx - 9, body_rect.top + 13, 18, 13)
            pygame.draw.rect(surface, (35, 38, 45), cam_rect, border_radius=3)
            pygame.draw.circle(surface, (110, 195, 240), cam_rect.center, 4)
            pygame.draw.circle(surface, (220, 230, 240), cam_rect.center, 5, width=1)
        elif "youtuber" in ctype or "vip" in ctype:
            pygame.draw.rect(surface, (145, 60, 215), body_rect, border_radius=8)
            pygame.draw.rect(surface, (255, 205, 65), body_rect, width=2, border_radius=8)
            rx, ry = cx + r_head + int(10 * scale), cy - int(6 * scale)
            pygame.draw.line(surface, (180, 185, 195), (cx + body_w // 3, body_rect.centery), (rx, ry + 10), 3)
            cls._draw_glow_circle(surface, (rx, ry), 16, (255, 245, 200), 110)
            pygame.draw.circle(surface, (255, 255, 245), (rx, ry), 10, width=3)
            pygame.draw.rect(surface, (40, 45, 55), (rx - 3, ry - 5, 6, 10), border_radius=1)
        else:
            pygame.draw.rect(surface, (36, 56, 98), body_rect, border_radius=8)
            pygame.draw.line(surface, (240, 240, 245), (cx - 6, body_rect.top), (cx, body_rect.top + 12), 2)
            pygame.draw.line(surface, (240, 240, 245), (cx + 6, body_rect.top), (cx, body_rect.top + 12), 2)
            pygame.draw.circle(surface, (245, 195, 55), (cx, body_rect.top + 10), 4)

        skin_col = (255, 185, 175) if mood_str == "ANGRY" else (255, 224, 192)
        head_pos = (cx, cy - 4)
        pygame.draw.circle(surface, skin_col, head_pos, r_head)
        pygame.draw.circle(surface, (210, 165, 135), head_pos, r_head, width=1)

        if "worker" in ctype or "office" in ctype:
            pygame.draw.arc(surface, (35, 32, 38), (cx - r_head, cy - r_head - 5, r_head * 2, r_head * 2), 0.2, math.pi - 0.15, int(6 * scale))
            ey = cy - int(r_head * 0.18)
            pygame.draw.rect(surface, (60, 65, 80), (cx - 12, ey - 4, 9, 7), width=1, border_radius=1)
            pygame.draw.rect(surface, (60, 65, 80), (cx + 3, ey - 4, 9, 7), width=1, border_radius=1)
            pygame.draw.line(surface, (60, 65, 80), (cx - 3, ey - 1), (cx + 3, ey - 1), 1)
        elif "tourist" in ctype or "foreign" in ctype:
            pygame.draw.arc(surface, (240, 195, 75), (cx - r_head - 1, cy - r_head - 5, r_head * 2 + 2, r_head * 2), 0.1, math.pi - 0.1, int(7 * scale))
            sy = cy - r_head + 3
            pygame.draw.rect(surface, (30, 30, 40), (cx - 11, sy - 3, 9, 6), border_radius=2)
            pygame.draw.rect(surface, (30, 30, 40), (cx + 2, sy - 3, 9, 6), border_radius=2)
            pygame.draw.line(surface, (220, 180, 60), (cx - 2, sy), (cx + 2, sy), 2)
        elif "youtuber" in ctype or "vip" in ctype:
            pygame.draw.arc(surface, (255, 105, 165), (cx - r_head, cy - r_head - 5, r_head * 2, r_head * 2), 0.15, math.pi - 0.15, int(7 * scale))
            pygame.draw.arc(surface, (235, 240, 250), (cx - r_head - 3, cy - r_head - 6, r_head * 2 + 6, r_head * 2 + 4), 0.1, math.pi - 0.1, 3)
            pygame.draw.ellipse(surface, (80, 225, 245), (cx - r_head - 5, cy - 10, 7, 13))
            pygame.draw.ellipse(surface, (80, 225, 245), (cx + r_head - 2, cy - 10, 7, 13))
        else:
            pygame.draw.arc(surface, (75, 48, 35), (cx - r_head, cy - r_head - 5, r_head * 2, r_head * 2), 0.15, math.pi - 0.15, int(7 * scale))

        eye_y = cy - int(r_head * 0.15)
        eye_dx = int(r_head * 0.36)
        mouth_y = cy + int(r_head * 0.25)

        if mood_str == "FEVER":
            for ex in (cx - eye_dx, cx + eye_dx):
                pygame.draw.circle(surface, (255, 65, 125), (ex - 2, eye_y - 1), 3)
                pygame.draw.circle(surface, (255, 65, 125), (ex + 2, eye_y - 1), 3)
                pygame.draw.polygon(surface, (255, 65, 125), [(ex - 5, eye_y), (ex + 5, eye_y), (ex, eye_y + 5)])
            pygame.draw.ellipse(surface, (215, 55, 75), (cx - 6, mouth_y - 2, 12, 9))
        elif mood_str == "HAPPY":
            pygame.draw.arc(surface, (45, 32, 28), (cx - eye_dx - 4, eye_y - 3, 8, 7), 0, math.pi, 2)
            pygame.draw.arc(surface, (45, 32, 28), (cx + eye_dx - 4, eye_y - 3, 8, 7), 0, math.pi, 2)
            pygame.draw.arc(surface, (195, 60, 60), (cx - 6, mouth_y - 3, 12, 8), math.pi, 2 * math.pi, 2)
            pygame.draw.circle(surface, (255, 150, 145), (cx - int(r_head * 0.58), cy + 1), 3)
            pygame.draw.circle(surface, (255, 150, 145), (cx + int(r_head * 0.58), cy + 1), 3)
        elif mood_str == "WARN":
            for ex, sgn in ((cx - eye_dx, -1), (cx + eye_dx, 1)):
                pygame.draw.circle(surface, (40, 35, 35), (ex, eye_y), 2)
                pygame.draw.line(surface, (60, 45, 40), (ex - 4, eye_y - 4 + sgn), (ex + 4, eye_y - 4 - sgn), 2)
            pygame.draw.arc(surface, (120, 60, 60), (cx - 5, mouth_y, 10, 6), 0, math.pi, 2)
            drop_y = cy - r_head + 6 + int((time_tick * 12) % 8)
            dx = cx + r_head - 2
            pygame.draw.polygon(surface, (90, 200, 255), [(dx, drop_y - 5), (dx - 3, drop_y + 1), (dx + 3, drop_y + 1)])
            pygame.draw.circle(surface, (90, 200, 255), (dx, drop_y + 2), 3)
        elif mood_str == "ANGRY":
            for ex, sgn in ((cx - eye_dx, 1), (cx + eye_dx, -1)):
                pygame.draw.circle(surface, (40, 20, 20), (ex, eye_y), 2)
                pygame.draw.line(surface, (50, 15, 15), (ex - 4, eye_y - 5 - sgn * 2), (ex + 4, eye_y - 5 + sgn * 2), 2)
            pygame.draw.rect(surface, (245, 240, 240), (cx - 6, mouth_y - 1, 12, 6), border_radius=2)
            pygame.draw.rect(surface, (160, 30, 30), (cx - 6, mouth_y - 1, 12, 6), width=1, border_radius=2)
            vx, vy = cx + r_head - 4, cy - r_head + 2
            pygame.draw.line(surface, (255, 45, 45), (vx - 4, vy - 2), (vx + 4, vy - 2), 2)
            pygame.draw.line(surface, (255, 45, 45), (vx - 4, vy + 2), (vx + 4, vy + 2), 2)
            pygame.draw.line(surface, (255, 45, 45), (vx - 2, vy - 4), (vx - 2, vy + 4), 2)
            pygame.draw.line(surface, (255, 45, 45), (vx + 2, vy - 4), (vx + 2, vy + 4), 2)
        else:
            for ex in (cx - eye_dx, cx + eye_dx):
                pygame.draw.circle(surface, (42, 34, 32), (ex, eye_y), max(2, int(2.5 * scale)))
            pygame.draw.arc(surface, (150, 65, 60), (cx - 5, mouth_y - 2, 10, 6), math.pi, 2 * math.pi, 2)

    draw_customer_character = draw_customer

    # ==================================================================
    # 4. 길거리 음식 & 조리 단계별 고퀄리티 24x24 레트로 도트(Pixel Art) 아이콘
    # ==================================================================
    @staticmethod
    def _px(surf: pygame.Surface, x: int, y: int, col) -> None:
        w, h = surf.get_size()
        if 0 <= int(x) < w and 0 <= int(y) < h:
            surf.set_at((int(x), int(y)), col)

    @classmethod
    def _px_rect(cls, surf: pygame.Surface, x: int, y: int, rw: int, rh: int, col) -> None:
        for yy in range(int(y), int(y + rh)):
            for xx in range(int(x), int(x + rw)):
                cls._px(surf, xx, yy, col)

    @classmethod
    def _px_ellipse(cls, surf: pygame.Surface, cx: float, cy: float, rx: float, ry: float, col) -> None:
        rx = max(0.5, float(rx))
        ry = max(0.5, float(ry))
        for yy in range(int(cy - ry - 1), int(cy + ry + 2)):
            for xx in range(int(cx - rx - 1), int(cx + rx + 2)):
                if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.05:
                    cls._px(surf, xx, yy, col)

    @classmethod
    def _px_line(cls, surf: pygame.Surface, x0: int, y0: int, x1: int, y1: int, col, thick: int = 1) -> None:
        steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0))))
        for i in range(steps + 1):
            t = i / float(steps)
            xx = int(round(x0 + (x1 - x0) * t))
            yy = int(round(y0 + (y1 - y0) * t))
            if thick <= 1:
                cls._px(surf, xx, yy, col)
            else:
                cls._px_rect(surf, xx, yy, thick, thick, col)

    @classmethod
    def _finalize_pixel_sprite(cls, raw: pygame.Surface, outline_col=(24, 14, 18, 255), add_shadow: bool = True) -> pygame.Surface:
        """투명 배경 도트 캔버스에 1px 도트 외곽선과 하단 드롭섀도우를 입혀 선명한 아케이드 도트 질감을 완성한다."""
        w, h = raw.get_size()
        out = pygame.Surface((w, h), pygame.SRCALPHA)
        if add_shadow:
            cls._px_ellipse(out, w // 2, h - 3, w * 0.34, 2.0, (0, 0, 0, 72))

        opaque = set()
        for yy in range(h):
            for xx in range(w):
                if raw.get_at((xx, yy)).a > 128:
                    opaque.add((xx, yy))

        for xx, yy in opaque:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = xx + dx, yy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in opaque:
                    out.set_at((nx, ny), outline_col)

        for xx, yy in opaque:
            out.set_at((xx, yy), raw.get_at((xx, yy)))
        return out

    @classmethod
    def _apply_food_post_fx(cls, surf: pygame.Surface, rid: str, is_burnt: bool) -> None:
        """외곽선 합성 후 김(Steam), 유리잔 하이라이트, 노릇한 윤기 스파클 도트를 추가해 식감을 극대화한다."""
        if is_burnt:
            for sx, sy in ((8, 4), (9, 2), (14, 5), (15, 3)):
                cls._px(surf, sx, sy, (145, 145, 155, 175))
            return

        hot_keys = (
            "tteokbokki", "odeng", "takoyaki", "yakisoba", "shengjianbao",
            "malatang", "guobarou", "guobaorou", "butter_chicken", "curry",
            "biryani", "masala_chai", "mac_cheese", "mac_and_cheese",
            "pirozhki", "khachapuri", "borscht", "samovar_tea",
            "pao_de_queijo", "feijoada",
        )
        drink_keys = (
            "sikhye", "draft_beer", "ramune", "margarita", "cola",
            "boba", "mango_smoothie", "plum_tea", "suanmeitang", "hk_milktea",
            "mango_lassi", "lassi", "milkshake", "root_beer", "kvass",
            "acai", "guarana",
        )

        if any(k in rid for k in hot_keys):
            # 모락모락 피어오르는 반투명 픽셀 김(Steam)
            for sx, sy, alpha in ((8, 4, 165), (9, 2, 115), (15, 4, 165), (14, 2, 115), (12, 3, 140)):
                if surf.get_at((sx, sy)).a == 0:
                    cls._px(surf, sx, sy, (255, 250, 242, alpha))
        elif any(k in rid for k in drink_keys):
            # 유리잔/컵 측면 세로 반사광 & 청량한 스파클 도트
            for yy in range(10, 16):
                c = surf.get_at((8, yy))
                if c.a > 128:
                    cls._px(surf, 8, yy, (min(255, c.r + 52), min(255, c.g + 52), min(255, c.b + 52), 255))
            for sx, sy in ((5, 5), (19, 6)):
                if surf.get_at((sx, sy)).a == 0:
                    cls._px(surf, sx, sy, (228, 252, 255, 195))
        else:
            # 갓 구운/튀긴 요리의 황금빛 윤기 & 고소한 스파클 도트
            for sx, sy in ((5, 5), (18, 4)):
                if surf.get_at((sx, sy)).a == 0:
                    cls._px(surf, sx, sy, (255, 236, 132, 190))

    @classmethod
    def draw_food_icon(cls, surface: pygame.Surface, center_pos, recipe_id: str, size: int = 48, burnt: bool = False):
        cx, cy = cls._norm_center(center_pos)
        rid = (recipe_id or "bungeoppang_redbean").lower()
        is_burnt = bool(burnt) or ("burnt" in rid)
        size = max(16, int(size))
        cache_key = ("px_v3", rid, size, is_burnt)

        if cache_key not in cls._food_cache:
            pix_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
            cls._render_food_to_surface(pix_surf, rid, 24, is_burnt)
            final_pix = cls._finalize_pixel_sprite(pix_surf)
            cls._apply_food_post_fx(final_pix, rid, is_burnt)
            cls._food_cache[cache_key] = pygame.transform.scale(final_pix, (size, size))

        icon = cls._food_cache[cache_key]
        surface.blit(icon, (int(cx - size // 2), int(cy - size // 2)))

    @classmethod
    def _render_food_to_surface(cls, surf: pygame.Surface, rid: str, s: int, is_burnt: bool):
        """24x24 네이티브 픽셀 그리드에 전세계 9개국 75종 길거리 음식을 정교한 레트로 도트로 렌더링한다."""
        if is_burnt:
            cls._px_ellipse(surf, 12, 13, 7, 5, (42, 36, 38))
            cls._px_ellipse(surf, 12, 12, 5, 3.5, (24, 20, 22))
            for sx, sy in ((8, 9), (14, 10), (11, 14)):
                cls._px(surf, sx, sy, (88, 76, 78))
            for gx, gy in ((9, 5), (10, 4), (14, 6), (15, 4), (12, 3)):
                cls._px(surf, gx, gy, (168, 168, 178))
            return

        # ==================================================================
        # 1. 대한민국 (KR)
        # ==================================================================
        if "bungeoppang" in rid:
            # 꼬리 지느러미 + 통통한 붕어 몸통 + 비늘 격자 + 삐져나온 팥/슈크림 속살
            for ty in range(8, 17):
                span = abs(ty - 12) // 2 + 2
                cls._px_rect(surf, 16, ty, span + 2, 1, (192, 118, 34))
            cls._px_ellipse(surf, 10, 12, 6.5, 4.8, (214, 136, 38))
            cls._px_ellipse(surf, 10, 11.5, 5.5, 3.8, (244, 178, 62))
            cls._px_ellipse(surf, 9, 10, 3.5, 2.0, (255, 214, 108))
            # 지느러미 볏
            cls._px_rect(surf, 8, 6, 5, 2, (224, 148, 44))
            cls._px_rect(surf, 9, 16, 4, 2, (192, 118, 34))
            # 붕어 눈 & 아가미 & 비늘 도트
            cls._px_rect(surf, 6, 10, 2, 2, (48, 26, 16))
            cls._px(surf, 6, 10, (255, 248, 220))
            for sx in (10, 13):
                for sy in (9, 12, 14):
                    cls._px(surf, sx, sy, (176, 98, 24))
            # 뱃속 달콤한 팥앙금 or 바닐라 슈크림 하이라이트
            fill_dark = (196, 142, 28) if "cream" in rid else (112, 24, 32)
            fill_main = (255, 228, 82) if "cream" in rid else (156, 38, 46)
            fill_hi = (255, 250, 192) if "cream" in rid else (238, 178, 182)
            cls._px_ellipse(surf, 12, 13, 3.2, 2.4, fill_dark)
            cls._px_ellipse(surf, 12, 13, 2.3, 1.7, fill_main)
            cls._px(surf, 11, 12, fill_hi)
            cls._px(surf, 13, 13, fill_hi)

        elif "skewer" in rid and "lamb" not in rid and "picanha" not in rid:
            # 대나무 꼬치대 + 숯불 닭꼬치 4덩이 + 소스/파채 토핑
            cls._px_line(surf, 3, 20, 20, 3, (198, 158, 92), thick=2)
            cls._px_line(surf, 3, 20, 7, 16, (232, 198, 136), thick=1)
            base_dark, base_mid, base_hi = (168, 104, 48), (222, 158, 88), (248, 204, 142)
            if "spicy" in rid or "greenonion" in rid:
                base_dark, base_mid, base_hi = (148, 24, 22), (218, 46, 36), (255, 118, 82)
            elif "teriyaki" in rid:
                base_dark, base_mid, base_hi = (88, 38, 18), (146, 72, 32), (218, 138, 72)
            elif "raw" in rid:
                base_dark, base_mid, base_hi = (198, 128, 124), (242, 178, 172), (255, 218, 214)

            for cx_i, cy_i in ((8, 15), (11, 12), (14, 9), (17, 6)):
                cls._px_ellipse(surf, cx_i, cy_i, 3.2, 2.5, base_dark)
                cls._px_ellipse(surf, cx_i, cy_i - 0.5, 2.5, 1.8, base_mid)
                cls._px(surf, cx_i - 1, cy_i - 1, base_hi)
                if "raw" not in rid:
                    cls._px_line(surf, cx_i - 1, cy_i - 1, cx_i + 1, cy_i + 1, (64, 28, 16))
            if "greenonion" in rid:
                for gx, gy in ((8, 14), (9, 13), (11, 11), (12, 10), (14, 8), (15, 7), (16, 6)):
                    cls._px_rect(surf, gx - 1, gy - 1, 3, 1, (62, 198, 68))
                    cls._px(surf, gx, gy - 1, (168, 248, 142))
            else:
                for sx, sy in ((9, 14), (12, 11), (15, 8)):
                    cls._px(surf, sx, sy, (255, 244, 196))

        elif "tteokbokki" in rid:
            # 초록색 분식집 멜라민 그릇 + 빨간 고추장 국물 + 가래떡 + 치즈/김말이
            cls._px_ellipse(surf, 12, 14, 9.0, 5.5, (42, 138, 96))
            cls._px_ellipse(surf, 12, 13, 8.2, 4.8, (82, 204, 148))
            cls._px_ellipse(surf, 12, 13, 7.2, 3.8, (168, 26, 22))
            cls._px_ellipse(surf, 12, 12.5, 6.4, 3.2, (226, 52, 36))
            # 가래떡 도트
            for tx, ty in ((7, 12), (11, 10), (14, 13), (9, 14), (15, 11)):
                cls._px_rect(surf, tx, ty, 4, 2, (252, 232, 212))
                cls._px_rect(surf, tx, ty, 3, 1, (255, 168, 118))
            if "cheese" in rid:
                cls._px_ellipse(surf, 12, 12, 5.2, 2.5, (242, 188, 38))
                cls._px_ellipse(surf, 12, 11.5, 4.2, 1.8, (255, 236, 122))
                cls._px(surf, 10, 11, (255, 255, 230))
                cls._px(surf, 14, 12, (72, 188, 82))
            elif "gimmari" in rid:
                for gx, gy in ((8, 7), (13, 6)):
                    cls._px_rect(surf, gx, gy, 4, 6, (38, 44, 48))
                    cls._px_rect(surf, gx + 1, gy + 1, 2, 4, (58, 68, 72))
                    cls._px_rect(surf, gx, gy, 4, 2, (218, 162, 76))
            else:
                cls._px(surf, 11, 11, (82, 212, 88))
                cls._px(surf, 13, 12, (255, 245, 198))

        elif "odeng" in rid:
            # 종이컵 + 진한 어묵국물 + 꼬불꼬불 접힌 어묵꼬치
            cls._px_rect(surf, 7, 10, 10, 10, (226, 222, 212))
            cls._px_rect(surf, 8, 10, 8, 9, (246, 242, 234))
            cls._px_rect(surf, 7, 13, 10, 2, (218, 118, 48))
            cls._px_ellipse(surf, 12, 10, 4.8, 1.8, (208, 156, 76))
            # 대나무 꼬치와 접힌 삼각 어묵
            cls._px_line(surf, 12, 11, 16, 3, (192, 148, 82), thick=1)
            for fy, fx in ((5, 13), (7, 11), (9, 12)):
                cls._px_rect(surf, fx - 2, fy, 5, 2, (224, 168, 86))
                cls._px_rect(surf, fx - 1, fy, 3, 1, (248, 206, 128))
            cls._px(surf, 10, 10, (72, 196, 78))

        elif "sikhye" in rid:
            # 투명 컵 + 황금빛 살얼음 식혜 + 동동 띄운 밥알 & 붉은 대추
            cls._px_rect(surf, 7, 7, 10, 13, (218, 192, 132))
            cls._px_rect(surf, 8, 8, 8, 11, (242, 218, 158))
            cls._px_rect(surf, 7, 7, 10, 2, (235, 246, 255))
            for rx, ry in ((9, 9), (11, 10), (13, 9), (14, 10), (10, 11)):
                cls._px_rect(surf, rx, ry, 2, 1, (255, 255, 250))
            cls._px_rect(surf, 11, 7, 3, 2, (204, 36, 38))
            cls._px(surf, 9, 13, (255, 252, 236))
            cls._px(surf, 9, 14, (255, 252, 236))

        # ==================================================================
        # 2. 일본 (JP)
        # ==================================================================
        elif "takoyaki" in rid:
            # 나무 배 접시(후네) + 타코야키 3알 + 타레소스 + 가쓰오부시 & 마요/파
            cls._px_rect(surf, 3, 13, 18, 5, (198, 152, 92))
            cls._px_rect(surf, 5, 14, 14, 4, (226, 184, 122))
            for bx in (7, 12, 17):
                cls._px_ellipse(surf, bx, 11, 2.8, 2.8, (218, 148, 54))
                cls._px_ellipse(surf, bx, 10.5, 2.2, 2.0, (242, 182, 78))
                cls._px_ellipse(surf, bx, 9.5, 2.2, 1.3, (108, 44, 22))
                if "mayo" in rid:
                    cls._px_line(surf, bx - 2, 9, bx + 2, 11, (255, 252, 228))
                    cls._px_line(surf, bx - 2, 11, bx + 2, 9, (255, 252, 228))
                    cls._px(surf, bx, 8, (76, 208, 82))
                else:
                    cls._px(surf, bx - 1, 8, (228, 172, 118))
                    cls._px(surf, bx + 1, 8, (72, 188, 76))
            cls._px_rect(surf, 11, 7, 2, 2, (238, 56, 78))

        elif "yakitori" in rid:
            # 비장탄 네기마 야키토리 (닭다리살 + 구운 대파 교차)
            cls._px_line(surf, 3, 20, 20, 3, (192, 148, 86), thick=2)
            m_dark = (104, 44, 20) if "tare" in rid else (178, 118, 54)
            m_mid = (162, 78, 34) if "tare" in rid else (232, 174, 98)
            for idx, (cx_i, cy_i) in enumerate(((7, 16), (10, 13), (13, 10), (16, 7))):
                if idx == 1 or idx == 3:
                    # 구운 대파(네기)
                    cls._px_rect(surf, cx_i - 2, cy_i - 2, 4, 4, (142, 198, 92))
                    cls._px_rect(surf, cx_i - 1, cy_i - 2, 2, 3, (236, 248, 218))
                    cls._px(surf, cx_i, cy_i, (78, 42, 22))
                else:
                    cls._px_ellipse(surf, cx_i, cy_i, 3.0, 2.4, m_dark)
                    cls._px_ellipse(surf, cx_i, cy_i - 0.5, 2.3, 1.7, m_mid)
                    cls._px(surf, cx_i - 1, cy_i - 1, (255, 228, 168))

        elif "yakisoba" in rid:
            # 검은 철판 접시 + 볶음면 가닥 + 양배추/베니쇼가 + 반숙 계란후라이
            cls._px_ellipse(surf, 12, 14, 9.2, 5.2, (46, 44, 54))
            cls._px_ellipse(surf, 12, 13.5, 7.6, 4.0, (142, 76, 32))
            for ny in (11, 13, 15):
                cls._px_line(surf, 6, ny, 18, ny, (198, 122, 52))
                cls._px_line(surf, 7, ny - 1, 17, ny - 1, (224, 152, 74))
            for gx, gy in ((7, 12), (16, 13), (9, 15)):
                cls._px_rect(surf, gx, gy, 2, 2, (112, 212, 88))
            if "egg" in rid:
                cls._px_ellipse(surf, 12, 12, 4.2, 3.2, (248, 248, 244))
                cls._px_ellipse(surf, 12, 11.5, 2.2, 1.8, (255, 162, 28))
                cls._px(surf, 11, 11, (255, 232, 148))
            else:
                cls._px_rect(surf, 11, 10, 3, 2, (238, 48, 72))

        elif "draft_beer" in rid:
            # 생맥주 조끼 손잡이 + 황금 라거 + 풍성한 크림 거품
            cls._px_rect(surf, 16, 10, 4, 7, (215, 228, 238))
            cls._px_rect(surf, 17, 12, 2, 3, (0, 0, 0, 0))
            cls._px_rect(surf, 6, 8, 11, 12, (218, 148, 24))
            cls._px_rect(surf, 7, 9, 9, 10, (252, 196, 42))
            for rx in (8, 11, 14):
                cls._px_line(surf, rx, 10, rx, 18, (255, 224, 98))
            cls._px_ellipse(surf, 9, 7, 3.0, 2.2, (250, 250, 246))
            cls._px_ellipse(surf, 13, 7, 3.2, 2.4, (255, 255, 252))
            cls._px_ellipse(surf, 11, 6, 2.8, 2.0, (255, 255, 255))

        elif "ramune" in rid:
            # 코끼리목 라무네 유리병 + 구슬(비다마) + 탄산 기포
            cls._px_rect(surf, 8, 11, 8, 9, (68, 204, 238))
            cls._px_rect(surf, 9, 7, 6, 4, (112, 228, 252))
            cls._px_rect(surf, 8, 4, 8, 3, (52, 168, 224))
            cls._px_rect(surf, 8, 13, 8, 4, (242, 248, 255))
            cls._px_rect(surf, 9, 14, 6, 2, (232, 62, 78))
            cls._px_rect(surf, 11, 8, 2, 2, (28, 96, 198))
            cls._px(surf, 10, 11, (255, 255, 255))

        # ==================================================================
        # 3. 멕시코 (MX)
        # ==================================================================
        elif "quesadilla" in rid:
            # 반달 모양 구운 또띠아 + 그릴 자국 + 녹아내리는 치즈 & 치킨 속살
            cls._px_ellipse(surf, 12, 14, 8.2, 5.2, (218, 158, 68))
            cls._px_ellipse(surf, 12, 13.5, 7.2, 4.2, (244, 198, 106))
            cls._px_rect(surf, 3, 4, 18, 9, (0, 0, 0, 0))
            cls._px_rect(surf, 5, 12, 14, 3, (255, 206, 38))
            for gx in (8, 12, 16):
                cls._px_line(surf, gx, 14, gx - 1, 17, (138, 78, 28))
            if "chicken" in rid:
                for cx_i in (7, 11, 15):
                    cls._px_rect(surf, cx_i, 11, 2, 2, (196, 82, 42))
                    cls._px(surf, cx_i + 1, 12, (62, 188, 72))

        elif "taco" in rid:
            # U자형 옥수수 타코 쉘 + 카르니타스 고기 + 살사/과카몰리 토핑
            cls._px_ellipse(surf, 12, 13, 8.0, 5.5, (218, 156, 48))
            cls._px_ellipse(surf, 12, 13.5, 7.0, 4.5, (246, 196, 82))
            cls._px_ellipse(surf, 12, 10, 6.2, 3.0, (138, 68, 34))
            cls._px_ellipse(surf, 12, 9.5, 5.2, 2.2, (176, 98, 52))
            for gx in (7, 10, 14, 16):
                cls._px_rect(surf, gx, 8, 2, 2, (82, 204, 78))
            if "salsa" in rid:
                cls._px_ellipse(surf, 12, 8.5, 4.0, 2.0, (228, 42, 36))
                cls._px(surf, 11, 8, (255, 196, 82))
                cls._px(surf, 13, 9, (255, 245, 230))
            elif "guac" in rid:
                cls._px_ellipse(surf, 12, 8.5, 4.2, 2.2, (86, 196, 58))
                cls._px_ellipse(surf, 12, 8.0, 3.0, 1.4, (158, 238, 102))

        elif "nacho" in rid:
            # 겹겹이 쌓인 삼각 나초 칩 + 나초 치즈 소스 & 할라피뇨
            for tx, ty, col in ((4, 11, (212, 148, 42)), (11, 11, (232, 172, 54)), (7, 7, (248, 196, 72))):
                for row in range(7):
                    w = row + 1
                    cls._px_rect(surf, tx + 4 - w // 2, ty + row, w, 1, col)
            if "cheese" in rid:
                cls._px_ellipse(surf, 12, 13, 5.2, 2.6, (255, 192, 28))
                cls._px_ellipse(surf, 12, 12.5, 3.8, 1.8, (255, 228, 96))
                cls._px_rect(surf, 10, 11, 2, 2, (58, 178, 62))
                cls._px_rect(surf, 13, 13, 2, 2, (224, 48, 42))

        elif "margarita" in rid:
            # 마가리타 칵테일 잔 + 라임 그린 음료 + 라임 슬라이스
            for row in range(7):
                w = 14 - row * 2
                col = (238, 252, 245) if row == 0 else (138, 236, 86)
                cls._px_rect(surf, 12 - w // 2, 6 + row, w, 1, col)
            cls._px_rect(surf, 11, 13, 2, 6, (212, 232, 242))
            cls._px_rect(surf, 8, 19, 8, 2, (212, 232, 242))
            cls._px_ellipse(surf, 18, 6, 2.5, 2.5, (68, 188, 58))
            cls._px(surf, 18, 6, (198, 252, 152))

        elif "cola" in rid:
            # 멕시칸 유리병 콜라 + 빨간 라벨 + 빨대
            cls._px_line(surf, 13, 7, 16, 3, (242, 72, 72))
            cls._px_rect(surf, 8, 10, 8, 10, (62, 26, 22))
            cls._px_rect(surf, 9, 6, 6, 4, (82, 38, 32))
            cls._px_rect(surf, 8, 13, 8, 3, (224, 42, 38))
            cls._px_rect(surf, 9, 14, 6, 1, (255, 248, 242))
            cls._px_line(surf, 9, 10, 9, 18, (128, 68, 56))

        # ==================================================================
        # 4. 대만 (TW)
        # ==================================================================
        elif "congzuobing" in rid:
            # 회오리 결이 살아있는 대만 파전병(총좌빙) + 송송 파 & 계란치즈
            cls._px_ellipse(surf, 12, 12, 7.8, 6.2, (206, 148, 64))
            cls._px_ellipse(surf, 12, 12, 6.6, 5.2, (238, 188, 96))
            cls._px_ellipse(surf, 12, 12, 4.5, 3.4, (186, 126, 48))
            cls._px_ellipse(surf, 12, 12, 3.4, 2.4, (244, 198, 112))
            for gx, gy in ((8, 10), (15, 11), (10, 15), (14, 14), (9, 12)):
                cls._px_rect(surf, gx, gy, 2, 1, (68, 188, 72))
            if "egg" in rid:
                cls._px_ellipse(surf, 12, 12, 3.8, 2.8, (255, 232, 92))
                cls._px_ellipse(surf, 12, 12, 2.0, 1.6, (255, 148, 28))

        elif "jipai" in rid:
            # 대만 대왕 지파이: 하단 홍백 종이봉투 + 거대한 바삭 치킨 커틀릿 + 마라 파우더
            cls._px_ellipse(surf, 12, 10, 7.2, 6.2, (198, 122, 36))
            cls._px_ellipse(surf, 12, 9.5, 6.0, 5.0, (236, 162, 56))
            for tx, ty in ((9, 7), (13, 6), (8, 10), (15, 9), (11, 11)):
                cls._px_rect(surf, tx, ty, 2, 1, (255, 208, 108))
            if "spicy" in rid:
                for mx, my in ((8, 8), (11, 7), (14, 8), (10, 10), (13, 10), (15, 11)):
                    cls._px_rect(surf, mx, my, 2, 1, (218, 36, 28))
            cls._px_rect(surf, 6, 13, 12, 7, (245, 240, 228))
            cls._px_rect(surf, 6, 15, 12, 2, (224, 52, 46))

        elif "cubesteak" in rid:
            # 종이 트레이 + 그릴 마크가 선명한 큐브 스테이크 4조각 + 갈릭버터/마늘칩
            cls._px_ellipse(surf, 12, 15, 8.5, 4.5, (232, 218, 196))
            for cx_i, cy_i in ((8, 12), (14, 11), (10, 15), (15, 14)):
                cls._px_rect(surf, cx_i - 2, cy_i - 2, 5, 4, (108, 46, 32))
                cls._px_rect(surf, cx_i - 1, cy_i - 2, 3, 3, (158, 74, 52))
                cls._px(surf, cx_i, cy_i - 1, (218, 118, 92))
            cls._px_rect(surf, 6, 13, 2, 2, (68, 186, 76))
            if "garlic" in rid:
                cls._px_rect(surf, 10, 10, 4, 3, (255, 228, 88))
                cls._px_rect(surf, 13, 13, 2, 2, (255, 246, 192))

        elif "boba" in rid:
            # 타이거 흑당 버블티 컵 + 쫀득한 흑진주 타피오카 펄 + 두꺼운 빨대
            cls._px_line(surf, 12, 8, 14, 2, (46, 38, 42), thick=2)
            cls._px_rect(surf, 7, 7, 10, 13, (216, 174, 126))
            cls._px_rect(surf, 8, 8, 8, 11, (236, 198, 152))
            for sy in (11, 14):
                cls._px_line(surf, 7, sy, 16, sy + 1, (112, 56, 26))
            for bx in (8, 11, 14, 9, 13):
                cls._px_rect(surf, bx, 17, 2, 2, (36, 22, 18))
            cls._px_rect(surf, 6, 6, 12, 2, (242, 246, 250))

        elif "mango_smoothie" in rid:
            # 대만 애플망고 스무디 컵 + 망고 과육 토핑 + 민트 잎
            cls._px_line(surf, 14, 8, 16, 3, (238, 72, 92), thick=1)
            cls._px_rect(surf, 7, 8, 10, 12, (246, 168, 24))
            cls._px_rect(surf, 8, 9, 8, 10, (255, 206, 48))
            cls._px_ellipse(surf, 12, 7, 4.8, 2.4, (255, 228, 92))
            for mx in (9, 12, 14):
                cls._px_rect(surf, mx, 6, 2, 2, (255, 142, 18))
            cls._px_rect(surf, 10, 5, 2, 2, (62, 198, 78))

        # ==================================================================
        # 5. 중국 (CN)
        # ==================================================================
        elif "shengjianbao" in rid:
            # 무쇠팬 위 상하이 성젠바오 3개 (노릇한 바닥 + 흰 만두 주름 + 검은깨 & 쪽파)
            cls._px_ellipse(surf, 12, 15, 9.0, 4.8, (48, 46, 54))
            for bx, by in ((8, 12), (15, 12), (11, 14)):
                cls._px_ellipse(surf, bx, by + 1, 3.2, 2.2, (212, 138, 46))
                cls._px_ellipse(surf, bx, by - 0.5, 3.0, 2.2, (248, 244, 234))
                cls._px(surf, bx, by - 2, (218, 208, 192))
                cls._px(surf, bx - 1, by, (36, 32, 34))
                cls._px(surf, bx + 1, by, (68, 196, 78))

        elif "egg_waffle" in rid:
            # 홍콩 에그와플(가이단자이): 올록볼록 황금 구슬 와플 격자 + 종이 콘
            for wy in (6, 9, 12):
                for wx in (7, 10, 13, 16):
                    cls._px_ellipse(surf, wx, wy, 1.8, 1.8, (208, 132, 38))
                    cls._px_ellipse(surf, wx, wy - 0.3, 1.2, 1.2, (252, 196, 82))
                    cls._px(surf, wx - 1, wy - 1, (255, 238, 168))
            for row in range(6):
                w = 10 - row
                cls._px_rect(surf, 12 - w // 2, 14 + row, w, 1, (242, 232, 214))
            cls._px_rect(surf, 8, 15, 8, 2, (218, 52, 48))

        elif "lamb_skewer" in rid:
            # 쇠꼬치에 꿴 신장·사천 양꼬치 + 즈란(큐민) or 마라 고추기름
            cls._px_line(surf, 3, 20, 20, 3, (172, 182, 196), thick=1)
            m_dark, m_mid = (138, 62, 36), (198, 104, 62)
            if "mala" in rid:
                m_dark, m_mid = (156, 26, 22), (224, 52, 38)
            elif "cumin" in rid:
                m_dark, m_mid = (152, 86, 32), (216, 138, 52)
            for idx, (cx_i, cy_i) in enumerate(((7, 16), (10, 13), (13, 10), (16, 7))):
                if idx == 2:
                    cls._px_rect(surf, cx_i - 2, cy_i - 2, 4, 4, (248, 226, 186))
                else:
                    cls._px_rect(surf, cx_i - 2, cy_i - 2, 5, 4, m_dark)
                    cls._px_rect(surf, cx_i - 1, cy_i - 2, 3, 3, m_mid)
                if "cumin" in rid:
                    cls._px(surf, cx_i, cy_i - 1, (255, 218, 92))
                elif "mala" in rid:
                    cls._px(surf, cx_i, cy_i - 1, (255, 162, 52))

        elif "malatang" in rid:
            # 사천 마라탕 대접 + 빨간 마라 국물 + 청경채, 연근, 피쉬볼, 두부피
            cls._px_ellipse(surf, 12, 14, 9.0, 5.4, (238, 196, 76))
            cls._px_ellipse(surf, 12, 13, 7.6, 4.2, (198, 36, 28))
            cls._px_ellipse(surf, 12, 12.5, 6.6, 3.4, (236, 68, 42))
            cls._px_rect(surf, 7, 11, 3, 3, (72, 198, 82))
            cls._px_ellipse(surf, 12, 12, 2.2, 1.8, (248, 236, 212))
            cls._px(surf, 12, 12, (198, 36, 28))
            cls._px_ellipse(surf, 15, 11, 2.0, 2.0, (255, 224, 168))

        elif "guobarou" in rid or "guobaorou" in rid:
            # 하얼빈 꿔바로우: 접시 위 큼직한 찹쌀 탕수육 조각 + 반짝이는 탕수 소스 & 당근채
            cls._px_ellipse(surf, 12, 15, 8.8, 4.6, (242, 244, 248))
            for gx, gy in ((8, 13), (13, 11), (11, 14)):
                cls._px_ellipse(surf, gx, gy, 4.0, 2.5, (198, 92, 28))
                cls._px_ellipse(surf, gx, gy - 0.5, 3.2, 1.8, (242, 146, 46))
                cls._px(surf, gx - 1, gy - 1, (255, 224, 138))
            cls._px_line(surf, 9, 11, 14, 12, (82, 204, 88))
            cls._px_line(surf, 10, 13, 15, 13, (255, 96, 52))

        elif "plum_tea" in rid or "suanmeitang" in rid:
            # 베이징 산사자차(매실·산사 루비빛 음료 + 얼음 + 금목서 꽃잎)
            cls._px_rect(surf, 7, 7, 10, 13, (136, 24, 38))
            cls._px_rect(surf, 8, 8, 8, 11, (186, 42, 58))
            cls._px_rect(surf, 9, 9, 3, 2, (248, 222, 228))
            cls._px_rect(surf, 13, 10, 2, 2, (248, 222, 228))
            cls._px_rect(surf, 10, 7, 4, 1, (255, 214, 68))

        elif "hk_milktea" in rid:
            # 홍콩 차찬텡 흑백 에바밀크 머그잔 + 진한 동윤영 밀크티
            cls._px_rect(surf, 16, 10, 3, 6, (238, 236, 232))
            cls._px_rect(surf, 6, 8, 10, 11, (244, 242, 236))
            cls._px_rect(surf, 6, 12, 10, 3, (204, 38, 38))
            cls._px_ellipse(surf, 11, 8, 4.5, 1.8, (158, 98, 52))
            cls._px(surf, 10, 8, (238, 192, 142))

        # ==================================================================
        # 6. 인도 (IN)
        # ==================================================================
        elif "garlic_naan" in rid:
            # 물방울 모양 화덕 갈릭 난 + 탄두르 구운 자국 + 버터 & 고수 다짐
            cls._px_ellipse(surf, 12, 13, 7.2, 5.2, (208, 154, 82))
            cls._px_ellipse(surf, 14, 9, 4.5, 4.2, (208, 154, 82))
            cls._px_ellipse(surf, 12, 13, 6.0, 4.2, (244, 206, 136))
            cls._px_ellipse(surf, 14, 9.5, 3.5, 3.2, (244, 206, 136))
            for bx, by in ((9, 13), (14, 11), (12, 15)):
                cls._px_rect(surf, bx, by, 2, 2, (132, 76, 36))
            for gx, gy in ((10, 11), (13, 13), (15, 9), (11, 14)):
                cls._px(surf, gx, gy, (68, 196, 78))
                cls._px(surf, gx + 1, gy, (255, 244, 162))

        elif "samosa" in rid:
            # 황금 삼각 사모사 2개 + 민트 처트니 종지
            for tx, ty, col in ((4, 9, (204, 138, 42)), (10, 8, (238, 176, 58))):
                for row in range(9):
                    w = row + 2
                    cls._px_rect(surf, tx + 5 - w // 2, ty + row, w, 1, col)
            cls._px_rect(surf, 12, 12, 3, 2, (255, 218, 112))
            cls._px_ellipse(surf, 18, 15, 2.5, 2.0, (56, 198, 112))

        elif "tandoori" in rid or "tikka" in rid:
            # 탄두리 치킨 티카 꼬치 + 민트 처트니 or 가람마살라 시즈닝
            cls._px_line(surf, 3, 20, 20, 3, (118, 124, 136), thick=1)
            for cx_i, cy_i in ((7, 16), (11, 12), (15, 8)):
                cls._px_ellipse(surf, cx_i, cy_i, 3.2, 2.5, (168, 38, 24))
                cls._px_ellipse(surf, cx_i, cy_i - 0.5, 2.4, 1.8, (232, 82, 42))
                cls._px(surf, cx_i + 1, cy_i + 1, (72, 28, 18))
                if "mint" in rid:
                    cls._px_rect(surf, cx_i - 1, cy_i - 1, 3, 1, (68, 224, 136))
                elif "masala" in rid:
                    cls._px_rect(surf, cx_i - 1, cy_i - 1, 3, 1, (255, 212, 68))

        elif "butter_chicken" in rid or "curry" in rid:
            # 인도 황동 한디(Handi) 그릇 + 진한 오렌지 버터치킨 커리 + 생크림 스월
            cls._px_ellipse(surf, 12, 14, 8.8, 5.2, (186, 116, 46))
            cls._px_ellipse(surf, 12, 13, 7.4, 4.0, (224, 88, 32))
            cls._px_ellipse(surf, 12, 12.5, 6.2, 3.2, (246, 122, 48))
            for cx_i, cy_i in ((9, 12), (14, 13), (12, 11)):
                cls._px_rect(surf, cx_i, cy_i, 3, 2, (255, 178, 92))
            cls._px_ellipse(surf, 12, 12, 3.2, 1.5, (255, 248, 236))
            cls._px(surf, 12, 12, (68, 198, 82))

        elif "biryani" in rid:
            # 황금 비리야니 단지 + 노란 샤프란 바스마티 쌀밥 봉우리 + 양고기 & 캐슈넛
            cls._px_ellipse(surf, 12, 15, 8.6, 4.8, (208, 152, 48))
            cls._px_ellipse(surf, 12, 12, 7.2, 4.2, (246, 192, 52))
            cls._px_ellipse(surf, 12, 11, 5.4, 3.2, (255, 224, 96))
            for rx, ry in ((9, 11), (14, 12), (11, 9)):
                cls._px_rect(surf, rx, ry, 2, 2, (156, 68, 36))
            for wx, wy in ((8, 12), (13, 10), (15, 13), (10, 13)):
                cls._px(surf, wx, wy, (255, 252, 240))
            cls._px(surf, 12, 10, (72, 198, 86))

        elif "mango_lassi" in rid or "lassi" in rid:
            # 인도 토기잔(쿨하드) + 진한 망고 라씨 + 피스타치오 & 샤프란 가니시
            cls._px_rect(surf, 7, 8, 10, 12, (186, 108, 62))
            cls._px_rect(surf, 8, 8, 8, 10, (255, 198, 42))
            cls._px_ellipse(surf, 12, 8, 4.5, 2.0, (255, 236, 148))
            cls._px_rect(surf, 11, 7, 2, 2, (98, 208, 88))
            cls._px(surf, 13, 8, (228, 52, 38))

        elif "masala_chai" in rid:
            # 인도 토기잔(쿨하드) + 밀크 차이티 + 시나몬 스틱
            cls._px_line(surf, 14, 8, 17, 4, (128, 58, 28), thick=2)
            cls._px_rect(surf, 7, 9, 10, 11, (176, 96, 54))
            cls._px_rect(surf, 8, 10, 8, 9, (198, 118, 68))
            cls._px_ellipse(surf, 12, 9, 4.5, 2.0, (232, 186, 136))
            cls._px(surf, 11, 9, (255, 244, 222))

        # ==================================================================
        # 7. 미국 (US)
        # ==================================================================
        elif "hotdog" in rid:
            # 뉴욕 칠리 핫도그: 갈라진 번 + 탱글한 소시지 + 지그재그 머스타드 & 케첩
            cls._px_ellipse(surf, 12, 13, 8.5, 4.8, (226, 166, 86))
            cls._px_ellipse(surf, 12, 12, 9.2, 2.8, (188, 64, 46))
            cls._px_ellipse(surf, 12, 11.5, 8.2, 2.0, (228, 92, 68))
            for mx in range(6, 18, 2):
                my = 11 if (mx // 2) % 2 == 0 else 12
                cls._px(surf, mx, my, (255, 224, 42))
                cls._px(surf, mx + 1, my, (238, 38, 36))

        elif "beignet" in rid:
            # 뉴올리언스 베녜: 사각 도넛 3개 + 눈처럼 쌓인 하얀 슈가파우더 + 라즈베리
            for bx, by in ((6, 11), (12, 11), (9, 8)):
                cls._px_rect(surf, bx, by, 6, 5, (218, 158, 78))
                cls._px_rect(surf, bx + 1, by, 4, 3, (252, 252, 255))
            cls._px_rect(surf, 11, 7, 2, 2, (228, 42, 68))

        elif "burger" in rid:
            # 참깨 브리오슈 번 + 양상추 + 체다치즈 + 더블 스매시 패티 + 베이컨
            cls._px_ellipse(surf, 12, 16, 7.5, 2.5, (218, 152, 68))
            cls._px_rect(surf, 5, 13, 14, 3, (112, 48, 32))
            cls._px_rect(surf, 5, 12, 14, 2, (255, 198, 36))
            if "bacon" in rid:
                cls._px_rect(surf, 4, 11, 16, 2, (208, 52, 46))
                cls._px_line(surf, 5, 11, 18, 11, (248, 156, 142))
            cls._px_rect(surf, 5, 10, 14, 2, (76, 204, 78))
            cls._px_ellipse(surf, 12, 8.5, 7.2, 3.5, (232, 164, 72))
            for sx, sy in ((9, 7), (12, 6), (15, 7), (11, 8), (14, 8)):
                cls._px(surf, sx, sy, (255, 244, 204))

        elif "brisket" in rid:
            # 텍사스 훈제 브리스킷 슬라이스 (검은 바크 크러스트 + 핑크 스모크 링 + 히코리 BBQ 글레이즈)
            cls._px_ellipse(surf, 12, 15, 8.8, 4.5, (218, 186, 142))
            for sy in (9, 12, 14):
                cls._px_rect(surf, 6, sy, 12, 3, (58, 32, 26))
                cls._px_rect(surf, 7, sy + 1, 10, 2, (224, 96, 98))
                cls._px_rect(surf, 8, sy + 1, 8, 1, (168, 68, 48))
            cls._px_rect(surf, 15, 13, 3, 2, (86, 196, 72))

        elif "wings" in rid:
            # 버팔로 핫윙 & 감자튀김 바스켓
            cls._px_rect(surf, 5, 12, 14, 6, (228, 52, 48))
            for fx in range(6, 18, 2):
                cls._px_rect(surf, fx, 13, 1, 4, (255, 248, 242))
            for fx in (6, 8, 10):
                cls._px_rect(surf, fx, 7, 2, 6, (255, 212, 62))
            for wx, wy in ((12, 9), (15, 10)):
                cls._px_ellipse(surf, wx, wy, 3.2, 2.2, (208, 68, 32))
                cls._px(surf, wx - 1, wy - 1, (255, 168, 82))

        elif "mac_cheese" in rid or "mac_and_cheese" in rid:
            # 무쇠 스킬렛 가득 꾸덕한 황금 체다 맥앤치즈
            cls._px_ellipse(surf, 12, 14, 8.8, 5.2, (48, 46, 54))
            cls._px_ellipse(surf, 12, 13, 7.6, 4.0, (242, 168, 28))
            cls._px_ellipse(surf, 12, 12.5, 6.6, 3.2, (255, 212, 52))
            for mx, my in ((8, 12), (11, 11), (14, 12), (10, 13), (13, 14)):
                cls._px_rect(surf, mx, my, 3, 2, (255, 244, 148))
            cls._px(surf, 12, 12, (76, 198, 82))

        elif "milkshake" in rid:
            # 산타모니카 다이너 핑크 밀크셰이크 + 휘핑크림 탑 + 체리
            cls._px_line(surf, 14, 8, 17, 3, (238, 58, 78))
            cls._px_rect(surf, 8, 9, 8, 10, (255, 168, 198))
            cls._px_rect(surf, 9, 10, 6, 8, (255, 198, 218))
            cls._px_ellipse(surf, 12, 8, 4.5, 2.4, (255, 252, 248))
            cls._px_ellipse(surf, 12, 6, 3.0, 2.0, (255, 255, 255))
            cls._px_rect(surf, 11, 4, 2, 2, (228, 32, 48))

        elif "root_beer" in rid:
            # 루트비어 아이스 플로트 조끼 + 바닐라 아이스크림 스쿱
            cls._px_rect(surf, 16, 11, 3, 6, (212, 224, 236))
            cls._px_rect(surf, 7, 9, 9, 11, (76, 38, 26))
            cls._px_rect(surf, 8, 10, 7, 9, (112, 56, 38))
            cls._px_ellipse(surf, 11.5, 8, 4.5, 2.5, (242, 228, 198))
            cls._px_ellipse(surf, 11.5, 6.5, 3.2, 2.6, (255, 252, 238))

        # ==================================================================
        # 8. 러시아 (RU)
        # ==================================================================
        elif "pirozhki" in rid:
            # 노릇하게 구운 러시아 고기빵 피로시키 2개 + 주름 이음새
            for px, py in ((9, 11), (14, 14)):
                cls._px_ellipse(surf, px, py, 5.2, 3.2, (188, 114, 42))
                cls._px_ellipse(surf, px, py - 0.5, 4.2, 2.4, (236, 172, 78))
                cls._px_line(surf, px - 3, py - 1, px + 3, py - 1, (255, 218, 132))

        elif "khachapuri" in rid:
            # 보트 모양 코카서스 치즈 하차푸리 + 녹은 술구니 치즈 + 달걀 노른자 & 버터
            cls._px_ellipse(surf, 12, 13, 9.2, 5.0, (216, 148, 56))
            cls._px_ellipse(surf, 12, 13, 6.4, 3.2, (255, 238, 168))
            cls._px_ellipse(surf, 12, 13, 2.5, 2.2, (255, 148, 24))
            cls._px(surf, 11, 12, (255, 232, 142))
            cls._px_rect(surf, 8, 12, 2, 2, (255, 218, 68))

        elif "shashlik" in rid:
            # 시베리아 대형 쇠꼬치 샤슬릭 + 붉은 양파 링 + 딜 사워크림
            cls._px_line(surf, 3, 20, 20, 3, (186, 196, 212), thick=2)
            for cx_i, cy_i in ((7, 16), (11, 12), (15, 8)):
                cls._px_rect(surf, cx_i - 2, cy_i - 2, 5, 5, (128, 52, 34))
                cls._px_rect(surf, cx_i - 1, cy_i - 2, 3, 3, (188, 86, 56))
                cls._px(surf, cx_i + 1, cy_i - 2, (218, 92, 168))
                if "sourcream" in rid:
                    cls._px_rect(surf, cx_i - 1, cy_i - 1, 3, 2, (248, 252, 255))
                    cls._px(surf, cx_i, cy_i - 1, (68, 198, 96))

        elif "borscht" in rid:
            # 붉은광장 진홍빛 비트 보르시 스튜 + 스메타나(사워크림) & 딜 허브
            cls._px_ellipse(surf, 12, 14, 8.8, 5.2, (228, 218, 204))
            cls._px_ellipse(surf, 12, 13, 7.6, 4.0, (148, 18, 46))
            cls._px_ellipse(surf, 12, 12.5, 6.6, 3.2, (198, 32, 68))
            if "supreme" in rid or "sourcream" in rid:
                cls._px_ellipse(surf, 12, 12, 3.4, 2.2, (252, 252, 255))
                cls._px_rect(surf, 11, 11, 2, 2, (68, 204, 96))
            else:
                cls._px_rect(surf, 10, 12, 2, 2, (248, 168, 178))
                cls._px(surf, 13, 11, (76, 198, 92))

        elif "samovar_tea" in rid:
            # 황금 세공 홀더(포드스타칸니크) 유리잔 홍차 + 레몬 슬라이스
            cls._px_rect(surf, 16, 11, 3, 6, (238, 186, 52))
            cls._px_rect(surf, 7, 8, 9, 11, (196, 76, 28))
            cls._px_rect(surf, 6, 12, 11, 7, (238, 186, 52))
            cls._px_rect(surf, 8, 14, 7, 3, (168, 58, 24))
            cls._px_ellipse(surf, 14, 8, 2.4, 2.0, (255, 228, 68))

        elif "kvass" in rid:
            # 러시아 전통 호밀 크바스 목제/갈색 조끼 + 맥아 거품
            cls._px_rect(surf, 16, 10, 3, 6, (156, 98, 52))
            cls._px_rect(surf, 7, 8, 9, 12, (112, 58, 32))
            cls._px_rect(surf, 8, 9, 7, 10, (148, 82, 44))
            cls._px_ellipse(surf, 11.5, 8, 4.8, 2.2, (242, 218, 176))

        # ==================================================================
        # 9. 브라질 (BR)
        # ==================================================================
        elif "pastel" in rid:
            # 상파울루 특대 사각 튀김 파이 파스텔 + 포크 주름 테두리 + 치즈 속살
            cls._px_rect(surf, 4, 8, 16, 10, (208, 146, 48))
            cls._px_rect(surf, 5, 9, 14, 8, (246, 196, 86))
            for px in range(5, 19, 2):
                cls._px(surf, px, 8, (255, 232, 148))
                cls._px(surf, px, 17, (176, 116, 34))
            cls._px_rect(surf, 14, 9, 4, 4, (255, 224, 68))
            cls._px_rect(surf, 15, 10, 2, 2, (178, 68, 42))

        elif "pao_de_queijo" in rid:
            # 브라질 쫀득 치즈볼 팡지케이주 3알 바스켓
            cls._px_ellipse(surf, 12, 15, 8.5, 4.2, (176, 118, 64))
            for bx, by in ((8, 11), (15, 11), (11, 13)):
                cls._px_ellipse(surf, bx, by, 3.4, 3.0, (228, 168, 52))
                cls._px_ellipse(surf, bx, by - 0.5, 2.6, 2.2, (255, 218, 96))
                cls._px(surf, bx, by - 1, (255, 248, 204))

        elif "picanha" in rid:
            # 리우 피카냐 슈하스코 꼬치 (초승달 모양 등심 + 노릇한 지방층 + 카사바 파로파)
            cls._px_line(surf, 3, 20, 20, 3, (192, 202, 216), thick=2)
            for cx_i, cy_i in ((8, 15), (12, 11), (15, 8)):
                cls._px_ellipse(surf, cx_i, cy_i, 3.6, 2.8, (242, 192, 102))
                cls._px_ellipse(surf, cx_i - 0.5, cy_i + 0.5, 2.8, 2.0, (148, 48, 38))
                cls._px(surf, cx_i - 1, cy_i, (218, 88, 76))
                if "farofa" in rid:
                    for fx_off, fy_off in ((-2, -1), (0, -2), (2, 0)):
                        cls._px(surf, cx_i + fx_off, cy_i + fy_off, (255, 226, 128))

        elif "feijoada" in rid:
            # 바이아 검은콩 스튜 페이조아다 뚝배기 + 훈제 소시지 + 비나그레치 살사 & 오렌지
            cls._px_ellipse(surf, 12, 14, 9.0, 5.4, (44, 38, 42))
            cls._px_ellipse(surf, 12, 13, 7.6, 4.0, (68, 38, 36))
            for sx, sy in ((8, 12), (14, 13), (11, 14)):
                cls._px_ellipse(surf, sx, sy, 2.0, 1.5, (198, 78, 52))
            if "salsa" in rid:
                for vx, vy, vc in ((9, 11, (238, 52, 46)), (12, 11, (76, 204, 82)), (14, 11, (255, 218, 68))):
                    cls._px_rect(surf, vx, vy, 2, 2, vc)
            else:
                cls._px_ellipse(surf, 16, 11, 2.2, 1.8, (255, 168, 36))

        elif "acai" in rid:
            # 코파카바나 보랏빛 아사이볼 컵 + 바나나 슬라이스 & 그래놀라 토핑
            cls._px_line(surf, 15, 8, 17, 3, (112, 224, 102))
            cls._px_rect(surf, 6, 9, 12, 10, (82, 26, 112))
            cls._px_rect(surf, 7, 10, 10, 8, (116, 42, 152))
            cls._px_ellipse(surf, 12, 9, 5.8, 2.6, (138, 52, 176))
            for bx in (8, 11, 14):
                cls._px_ellipse(surf, bx, 8, 1.8, 1.5, (255, 232, 88))
            cls._px_rect(surf, 10, 10, 4, 1, (228, 172, 76))

        elif "guarana" in rid:
            # 브라질 초록 과라나 안타르치카 보틀 + 붉은 과라나 열매 마크
            cls._px_rect(surf, 8, 9, 8, 11, (36, 148, 68))
            cls._px_rect(surf, 9, 5, 6, 4, (52, 178, 86))
            cls._px_rect(surf, 8, 12, 8, 4, (248, 208, 48))
            cls._px_rect(surf, 11, 13, 2, 2, (224, 38, 38))
            cls._px_rect(surf, 10, 4, 4, 1, (248, 208, 48))

        else:
            cls._px_ellipse(surf, 12, 13, 7.5, 5.0, (218, 148, 56))
            cls._px_ellipse(surf, 12, 12, 6.0, 3.8, (248, 192, 88))
            cls._px(surf, 10, 11, (255, 244, 196))

    # ==================================================================
    # 5. 토핑 버튼 배지 고퀄리티 16x16 도트 아이콘 (Surface 캐싱)
    # ==================================================================
    @classmethod
    def draw_topping_badge(cls, surface: pygame.Surface, center_pos, topping_id: str, size: int = 32):
        cx, cy = cls._norm_center(center_pos)
        tid = (topping_id or "spicy_sauce").lower()
        size = max(16, int(size))
        cache_key = ("px_top_v2", tid, size)

        if cache_key not in cls._topping_cache:
            pix = pygame.Surface((16, 16), pygame.SRCALPHA)
            cls._render_topping_to_surface(pix, tid, 16)
            final_pix = cls._finalize_pixel_sprite(pix, add_shadow=False)
            cls._topping_cache[cache_key] = pygame.transform.scale(final_pix, (size, size))

        icon = cls._topping_cache[cache_key]
        surface.blit(icon, (int(cx - size // 2), int(cy - size // 2)))

    @classmethod
    def _render_topping_to_surface(cls, surf: pygame.Surface, tid: str, s: int):
        palettes = {
            "spicy_sauce": ((178, 28, 26), (238, 62, 46), (255, 168, 122)),
            "teriyaki_sauce": ((104, 46, 20), (168, 86, 38), (238, 172, 98)),
            "green_onion": ((36, 136, 52), (78, 208, 88), (192, 252, 168)),
            "cheese": ((198, 142, 24), (255, 208, 42), (255, 248, 168)),
            "gimmari": ((38, 44, 48), (68, 76, 82), (228, 176, 86)),
            "tare_sauce": ((92, 38, 18), (156, 76, 36), (228, 152, 86)),
            "fried_egg": ((212, 216, 224), (252, 252, 255), (255, 162, 28)),
            "salsa": ((178, 32, 28), (236, 58, 48), (86, 212, 82)),
            "guacamole": ((56, 148, 46), (112, 208, 78), (192, 248, 138)),
            "mala_spice": ((156, 22, 22), (224, 48, 36), (255, 168, 52)),
            "garlic_butter": ((196, 158, 48), (248, 216, 88), (255, 250, 204)),
            "cumin_spice": ((158, 92, 28), (218, 146, 52), (255, 216, 112)),
            "sweet_sour_sauce": ((186, 62, 24), (242, 108, 42), (255, 204, 112)),
            "mint_chutney": ((28, 138, 86), (62, 208, 136), (168, 252, 208)),
            "garam_masala": ((148, 56, 24), (216, 106, 42), (255, 198, 88)),
            "crispy_bacon": ((146, 34, 38), (212, 62, 58), (252, 168, 156)),
            "bbq_glaze": ((88, 28, 20), (152, 56, 36), (232, 128, 76)),
            "dill_sourcream": ((168, 196, 182), (244, 250, 248), (62, 196, 98)),
            "farofa_powder": ((178, 132, 44), (236, 188, 78), (255, 238, 158)),
        }
        dark_c, mid_c, hi_c = palettes.get(tid, ((88, 92, 112), (148, 154, 176), (224, 228, 242)))
        cls._px_ellipse(surf, 8, 8, 6.2, 6.2, dark_c)
        cls._px_ellipse(surf, 8, 7.5, 5.0, 5.0, mid_c)

        if "egg" in tid:
            cls._px_ellipse(surf, 8, 8, 2.6, 2.6, hi_c)
            cls._px(surf, 7, 7, (255, 236, 168))
        elif "onion" in tid or "mint" in tid or "dill" in tid:
            cls._px_ellipse(surf, 8, 8, 3.2, 3.2, hi_c)
            cls._px_ellipse(surf, 8, 8, 1.5, 1.5, mid_c)
        elif "cheese" in tid or "butter" in tid:
            cls._px_rect(surf, 5, 6, 6, 4, hi_c)
            cls._px(surf, 6, 7, mid_c)
        elif "bacon" in tid:
            cls._px_rect(surf, 4, 6, 8, 4, dark_c)
            cls._px_line(surf, 5, 7, 11, 7, hi_c)
            cls._px_line(surf, 5, 9, 11, 9, mid_c)
        else:
            cls._px_ellipse(surf, 8, 7.5, 2.8, 2.4, hi_c)
            cls._px(surf, 6, 5, (255, 255, 255))

    # ==================================================================
    # 6. 하단 조리대 기구 하드웨어 본체 그래픽
    # ==================================================================
    @classmethod
    def draw_station_hardware(cls, surface: pygame.Surface, rect, station_type: str = "mold", station_id: str = None):
        rect = cls._norm_rect(rect)
        stype = (station_type or "mold").lower()
        sid = (station_id or "").lower()

        if stype == "mold":
            pygame.draw.rect(surface, (42, 44, 52), rect, border_radius=10)
            pygame.draw.rect(surface, (78, 82, 95), rect, width=3, border_radius=10)
            inner = rect.inflate(-12, -12)
            pygame.draw.rect(surface, (28, 30, 36), inner, border_radius=7)
            if "takoyaki" in sid:
                for gx in (-inner.width // 4, inner.width // 4):
                    for gy in (-inner.height // 4, inner.height // 4):
                        pygame.draw.circle(surface, (18, 20, 24), (inner.centerx + gx, inner.centery + gy), min(inner.width, inner.height) // 6)
            else:
                pygame.draw.ellipse(surface, (20, 22, 28), inner.inflate(-10, -14))

        elif stype == "grill":
            pygame.draw.rect(surface, (46, 42, 44), rect, border_radius=10)
            inner = rect.inflate(-10, -10)
            pygame.draw.rect(surface, (72, 24, 18), inner, border_radius=6)
            for ex in range(inner.left + 12, inner.right - 8, 22):
                pygame.draw.circle(surface, (235, 85, 28), (ex, inner.centery), 8)
                pygame.draw.circle(surface, (255, 165, 45), (ex, inner.centery), 4)
            for gx in range(inner.left + 8, inner.right - 4, 10):
                pygame.draw.line(surface, (185, 192, 205), (gx, inner.top + 2), (gx, inner.bottom - 2), 2)
            pygame.draw.rect(surface, (130, 136, 148), rect, width=3, border_radius=10)

        elif stype == "batch_pot":
            pygame.draw.rect(surface, (145, 152, 165), rect, border_radius=12)
            pygame.draw.rect(surface, (205, 212, 225), rect, width=3, border_radius=12)
            inner = rect.inflate(-14, -14)
            pygame.draw.rect(surface, (52, 32, 32), inner, border_radius=8)
            pygame.draw.rect(surface, (95, 102, 115), inner, width=2, border_radius=8)

        elif stype == "dispenser":
            pygame.draw.rect(surface, (62, 68, 82), rect, border_radius=10)
            pygame.draw.rect(surface, (155, 165, 182), rect, width=2, border_radius=10)
            tank = pygame.Rect(rect.x + 10, rect.y + 8, rect.width - 20, int(rect.height * 0.58))
            pygame.draw.rect(surface, (195, 225, 242), tank, border_radius=6)
            pygame.draw.rect(surface, (215, 55, 55), (rect.centerx - 5, tank.bottom + 4, 10, 8), border_radius=2)
            pygame.draw.rect(surface, (38, 42, 50), (rect.x + 12, rect.bottom - 14, rect.width - 24, 8), border_radius=3)

        elif stype == "tray":
            pygame.draw.rect(surface, (168, 118, 68), rect, border_radius=9)
            pygame.draw.rect(surface, (122, 82, 42), rect, width=3, border_radius=9)
            pygame.draw.rect(surface, (142, 96, 52), rect.inflate(-10, -10), width=1, border_radius=6)
            r_plate = min(rect.width, rect.height) // 3
            pygame.draw.circle(surface, (242, 240, 235), rect.center, r_plate)
            pygame.draw.circle(surface, (210, 206, 198), rect.center, max(4, r_plate - 5), width=1)

        elif stype == "trash":
            pygame.draw.rect(surface, (72, 78, 88), rect, border_radius=10)
            pygame.draw.rect(surface, (118, 126, 140), rect, width=2, border_radius=10)
            for ly in range(rect.top + 18, rect.bottom - 10, 10):
                pygame.draw.line(surface, (55, 60, 70), (rect.left + 10, ly), (rect.right - 10, ly), 2)
            pygame.draw.rect(surface, (98, 106, 118), (rect.left + 6, rect.top + 5, rect.width - 12, 8), border_radius=3)

        else:
            pygame.draw.rect(surface, (68, 72, 82), rect, border_radius=8)
            pygame.draw.rect(surface, (120, 125, 138), rect, width=2, border_radius=8)

    draw_station_detail = draw_station_hardware

    # ==================================================================
    # 6. 스토리 모드 컷신 삽화 로더 & 대화창 오버레이 렌더러
    # ==================================================================
    _story_img_cache: dict = {}

    @classmethod
    def get_story_illustration(cls, image_path: str, size: tuple[int, int]) -> pygame.Surface | None:
        """스토리 컷신 삽화(PNG/JPG)를 로드 및 스케일링하여 캐싱 반환한다."""
        if not image_path:
            return None
        w, h = max(1, int(size[0])), max(1, int(size[1]))
        cache_key = (image_path, w, h)
        cached = cls._story_img_cache.get(cache_key)
        if cached is not None:
            return cached

        candidates = [image_path]
        if config is not None and hasattr(config, "BASE_DIR"):
            candidates.append(os.path.join(config.BASE_DIR, image_path))
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, image_path))

        loaded_surf = None
        for path in candidates:
            if os.path.isfile(path):
                try:
                    raw = pygame.image.load(path)
                    if pygame.display.get_surface() is not None:
                        raw = raw.convert()
                    loaded_surf = pygame.transform.smoothscale(raw, (w, h))
                    break
                except Exception:
                    loaded_surf = None

        cls._story_img_cache[cache_key] = loaded_surf
        return loaded_surf

    @classmethod
    def draw_story_cutscene_overlay(
        cls,
        surface: pygame.Surface,
        cutscene: dict,
        line_idx: int = 0,
        time_tick: float = 0.0,
    ) -> tuple[pygame.Rect, pygame.Rect]:
        """
        스토리 컷신(삽화 + 대사창 + 해금 알림 + 다음/스킵 버튼)을 화면 전체 오버레이로 렌더링한다.
        반환값: (next_btn_rect, skip_btn_rect)
        """
        sw, sh = surface.get_size()
        cls.draw_alpha_overlay(surface, (0, 0, sw, sh), (8, 10, 18, 228))

        lines = cutscene.get("lines", [])
        total_lines = max(1, len(lines))
        clamped_idx = max(0, min(int(line_idx), total_lines - 1))
        cur_line = lines[clamped_idx] if lines else {}

        # 상단 타이틀 바
        header_rect = pygame.Rect(140, 22, sw - 280, 48)
        pygame.draw.rect(surface, (24, 28, 44), header_rect, border_radius=12)
        pygame.draw.rect(surface, (255, 196, 68), header_rect, width=2, border_radius=12)

        f_title = cls._get_font(20)
        f_sub = cls._get_font(14)
        title_str = str(cutscene.get("title", "스토리 모드"))
        t_surf = f_title.render(f"🎬 {title_str}", True, (255, 220, 96))
        surface.blit(t_surf, (header_rect.x + 18, header_rect.y + 11))

        # 스킵 버튼 (우측 상단)
        skip_rect = pygame.Rect(header_rect.right - 138, header_rect.y + 8, 126, 32)
        pygame.draw.rect(surface, (62, 46, 58), skip_rect, border_radius=8)
        pygame.draw.rect(surface, (185, 125, 145), skip_rect, width=1, border_radius=8)
        sk_surf = f_sub.render("ESC 건너뛰기 ⏭", True, (245, 225, 232))
        surface.blit(sk_surf, sk_surf.get_rect(center=skip_rect.center))

        # 중앙 16:9 삽화 액자 영역
        illust_frame = pygame.Rect(210, 78, sw - 420, 400)
        pygame.draw.rect(surface, (16, 18, 28), illust_frame, border_radius=14)
        img_rect = illust_frame.inflate(-12, -12)
        img_path = str(cutscene.get("illustration", "") or "")
        illust_surf = cls.get_story_illustration(img_path, (img_rect.width, img_rect.height))
        if illust_surf is not None:
            surface.blit(illust_surf, img_rect.topleft)
        else:
            cls.draw_country_background(surface, img_rect, str(cutscene.get("chapter_id", "KR")), time_tick=time_tick)
        pygame.draw.rect(surface, (245, 188, 68), illust_frame, width=3, border_radius=14)

        # 삽화 하단 해금 배너 (있을 경우)
        unlock_notice = str(cutscene.get("unlock_notice", "") or "")
        if unlock_notice:
            ub_rect = pygame.Rect(230, illust_frame.bottom - 40, sw - 460, 32)
            cls.draw_alpha_overlay(surface, ub_rect, (16, 22, 36, 225), border_radius=8)
            pygame.draw.rect(surface, (82, 224, 142), ub_rect, width=2, border_radius=8)
            ub_surf = f_sub.render(f"✨ {unlock_notice}", True, (132, 255, 182))
            surface.blit(ub_surf, ub_surf.get_rect(center=ub_rect.center))

        # 하단 대사창 (Dialogue Box)
        dlg_rect = pygame.Rect(140, 490, sw - 280, 204)
        pygame.draw.rect(surface, (22, 26, 40), dlg_rect, border_radius=16)
        speaker_color = tuple(cur_line.get("color", (245, 188, 68)))
        pygame.draw.rect(surface, speaker_color, dlg_rect, width=3, border_radius=16)

        # 화자 초상화 박스 (좌측)
        portrait_rect = pygame.Rect(dlg_rect.x + 18, dlg_rect.y + 22, 132, 132)
        pygame.draw.rect(surface, (34, 40, 58), portrait_rect, border_radius=14)
        pygame.draw.rect(surface, speaker_color, portrait_rect, width=2, border_radius=14)

        speaker_id = str(cur_line.get("speaker_id", "chef_kr") or "chef_kr")
        inner_av = portrait_rect.inflate(-14, -14)
        if speaker_id.startswith("chef_"):
            cls.draw_chef_avatar(surface, inner_av, speaker_id, state="HAPPY", time_tick=time_tick)
        elif speaker_id in ("student", "worker", "tourist", "youtuber"):
            cls.draw_customer(surface, inner_av, customer_type=speaker_id, mood="HAPPY", time_tick=time_tick)
        else:
            cls.draw_chef_avatar(surface, inner_av, "chef_kr", state="HAPPY", time_tick=time_tick)

        # 화자 이름 & 직함 배지
        speaker_name = str(cur_line.get("speaker", "김포차"))
        speaker_role = str(cur_line.get("role", ""))
        name_badge = pygame.Rect(portrait_rect.right + 18, dlg_rect.y + 18, 360, 34)
        pygame.draw.rect(surface, speaker_color, name_badge, border_radius=8)
        f_speaker = cls._get_font(17)
        role_suffix = f"  |  {speaker_role}" if speaker_role else ""
        sp_surf = f_speaker.render(f"{speaker_name}{role_suffix}", True, (18, 20, 28))
        surface.blit(sp_surf, (name_badge.x + 14, name_badge.y + 6))

        # 페이지 표시 (우측 상단)
        page_surf = f_sub.render(f"대사 {clamped_idx + 1} / {total_lines}", True, (175, 185, 210))
        surface.blit(page_surf, (dlg_rect.right - page_surf.get_width() - 22, dlg_rect.y + 24))

        # 본문 대사 텍스트 (자동 줄바꿈)
        text_str = str(cur_line.get("text", ""))
        f_body = cls._get_font(19)
        max_text_w = dlg_rect.width - 195
        words = text_str.split(" ")
        wrapped_lines: list[str] = []
        current_line = ""
        for word in words:
            candidate = f"{current_line} {word}".strip() if current_line else word
            if f_body.size(candidate)[0] <= max_text_w:
                current_line = candidate
            else:
                if current_line:
                    wrapped_lines.append(current_line)
                current_line = word
        if current_line:
            wrapped_lines.append(current_line)

        ty = dlg_rect.y + 66
        for wline in wrapped_lines[:3]:
            l_surf = f_body.render(wline, True, (245, 246, 250))
            surface.blit(l_surf, (portrait_rect.right + 22, ty))
            ty += 30

        # 우측 하단 다음/시작 버튼
        is_last = (clamped_idx + 1 >= total_lines)
        next_btn_rect = pygame.Rect(dlg_rect.right - 210, dlg_rect.bottom - 48, 190, 36)
        btn_col = (44, 158, 92) if is_last else (218, 128, 38)
        pygame.draw.rect(surface, btn_col, next_btn_rect, border_radius=9)
        pygame.draw.rect(surface, (255, 232, 165), next_btn_rect, width=2, border_radius=9)
        btn_label = "영업 시작하기 ▶" if is_last else "다음 대사 (SPACE) ▶"
        nb_surf = f_sub.render(btn_label, True, (255, 255, 255))
        surface.blit(nb_surf, nb_surf.get_rect(center=next_btn_rect.center))

        return next_btn_rect, skip_rect


# 전역 싱글톤 인스턴스 및 모듈 레벨 편의 함수
art_renderer = ArtRenderer()

draw_country_background = ArtRenderer.draw_country_background
draw_chef_avatar = ArtRenderer.draw_chef_avatar
draw_customer = ArtRenderer.draw_customer
draw_customer_character = ArtRenderer.draw_customer_character
draw_food_icon = ArtRenderer.draw_food_icon
draw_topping_badge = ArtRenderer.draw_topping_badge
draw_station_hardware = ArtRenderer.draw_station_hardware
draw_station_detail = ArtRenderer.draw_station_detail
draw_alpha_overlay = ArtRenderer.draw_alpha_overlay
draw_story_cutscene_overlay = ArtRenderer.draw_story_cutscene_overlay
