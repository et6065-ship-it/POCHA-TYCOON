"""
전세계 길거리 음식 포차 타이쿤 (World Street Food Pocha Tycoon)
전역 설정, 레이아웃 상수, 컬러 팔레트, 한글 폰트 로더 및 밸런스 상수 모듈.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple
import pygame

# ==============================================================================
# 기본 경로 및 화면 설정 (PyInstaller .exe 단독 실행 환경 완벽 호환)
# ==============================================================================
if getattr(sys, "frozen", False):
    BASE_DIR: str = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE_PATH: str = os.path.join(BASE_DIR, "save_data.json")

# 논리(가상) 기준 해상도: 모든 씬과 UI 레이아웃은 1280 x 720 기준으로 렌더링된다.
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
SCREEN_SIZE: Tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT)
FPS: int = 60
WINDOW_TITLE: str = "전세계 길거리 음식 포차 타이쿤 (World Street Food Pocha Tycoon)"

# 실제 디스플레이 윈도우 해상도 및 전체화면 상태 (옵션에서 실시간 변경 가능)
WINDOW_WIDTH: int = 1280
WINDOW_HEIGHT: int = 720
WINDOW_SIZE: Tuple[int, int] = (WINDOW_WIDTH, WINDOW_HEIGHT)
FULLSCREEN: bool = False

# 세로(Portrait) 가상 기준 해상도: 세로 모드 시 720 x 1280 레이아웃으로 자동 재배치된다.
PORTRAIT_WIDTH: int = 720
PORTRAIT_HEIGHT: int = 1280
PORTRAIT_SIZE: Tuple[int, int] = (PORTRAIT_WIDTH, PORTRAIT_HEIGHT)

RESOLUTION_PRESETS: List[Tuple[int, int]] = [
    (1280, 720),
    (1600, 720),
    (720, 1280),
    (720, 1440),
    (1280, 800),
    (1920, 1080),
]

RESOLUTION_LABELS: Dict[Tuple[int, int], str] = {
    (1280, 720): "가로 1280×720 (16:9 표준 HD)",
    (1600, 720): "가로 1600×720 (20:9 모바일 와이드)",
    (720, 1280): "세로 720×1280 (9:16 모바일 세로)",
    (720, 1440): "세로 720×1440 (9:18 스마트폰 세로)",
    (1280, 800): "가로 1280×800 (16:10 태블릿/폴드)",
    (1920, 1080): "가로 1920×1080 (16:9 FHD 대화면)",
}


def sync_browser_display_and_fullscreen(fullscreen: Optional[bool] = None) -> None:
    """웹앱(Pygbag WebAssembly) 환경에서 다크 베젤 CSS 및 브라우저 전체화면 API를 동기화한다."""
    if sys.platform != "emscripten":
        return
    try:
        import platform

        js_code = """
        (function() {
            var doc = document;
            var body = doc.body;
            if (body) {
                body.style.backgroundColor = '#0c0a16';
                body.style.margin = '0';
                body.style.padding = '0';
                body.style.overflow = 'hidden';
            }
            var cvs = doc.getElementById('canvas');
            if (cvs) {
                cvs.style.objectFit = 'contain';
                cvs.style.maxWidth = '100vw';
                cvs.style.maxHeight = '100vh';
                cvs.style.backgroundColor = '#0c0a16';
            }
        })();
        """
        platform.window.eval(js_code)

        if fullscreen is True:
            fs_js = """
            (function() {
                var el = document.documentElement;
                var req = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen;
                if (req && !document.fullscreenElement && !document.webkitFullscreenElement) {
                    var p = req.call(el);
                    if (p && p.catch) {
                        p.catch(function() {
                            var onceFs = function() {
                                document.removeEventListener('pointerup', onceFs, true);
                                document.removeEventListener('touchend', onceFs, true);
                                document.removeEventListener('click', onceFs, true);
                                if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                                    req.call(el);
                                }
                            };
                            document.addEventListener('pointerup', onceFs, true);
                            document.addEventListener('touchend', onceFs, true);
                            document.addEventListener('click', onceFs, true);
                        });
                    }
                }
            })();
            """
            platform.window.eval(fs_js)
        elif fullscreen is False:
            exit_js = """
            (function() {
                var ex = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen;
                if (ex && (document.fullscreenElement || document.webkitFullscreenElement)) {
                    ex.call(document);
                }
            })();
            """
            platform.window.eval(exit_js)
    except Exception:
        pass


def apply_display_mode(
    width: int = 1280,
    height: int = 720,
    fullscreen: bool = False,
) -> Optional[pygame.Surface]:
    """실제 윈도우 해상도 및 전체화면 모드를 즉시 변경하고 새 디스플레이 Surface를 반환한다."""
    global WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_SIZE, FULLSCREEN
    if (int(width), int(height)) not in RESOLUTION_PRESETS:
        width, height = (720, 1280) if int(height) > int(width) else (1280, 720)
    WINDOW_WIDTH = int(width)
    WINDOW_HEIGHT = int(height)
    WINDOW_SIZE = (WINDOW_WIDTH, WINDOW_HEIGHT)
    FULLSCREEN = bool(fullscreen)

    if not pygame.get_init() or not pygame.display.get_init():
        return None

    if sys.platform == "emscripten":
        sync_browser_display_and_fullscreen(FULLSCREEN)
        try:
            return pygame.display.set_mode(WINDOW_SIZE, 0)
        except Exception:
            return pygame.display.get_surface()

    flags = pygame.FULLSCREEN if FULLSCREEN else 0
    try:
        return pygame.display.set_mode(WINDOW_SIZE, flags)
    except Exception:
        FULLSCREEN = False
        try:
            return pygame.display.set_mode(WINDOW_SIZE, 0)
        except Exception:
            return pygame.display.get_surface()


# ==============================================================================
# 화면 레이아웃 상수 (1280 x 720 기준)
# - 상단 HUD 영역: 0 ~ 65 (높이 65px)
# - 중단 손님 및 배경 영역: 65 ~ 345 (높이 280px)
# - 하단 포차 카운터 조리대 영역: 345 ~ 720 (높이 375px)
# ==============================================================================
HUD_TOP: int = 0
HUD_Y: int = 0
HUD_HEIGHT: int = 65
HUD_BOTTOM: int = 65
HUD_RECT: Tuple[int, int, int, int] = (0, HUD_TOP, SCREEN_WIDTH, HUD_HEIGHT)

CUSTOMER_AREA_TOP: int = 65
CUSTOMER_AREA_Y: int = 65
CUSTOMER_AREA_BOTTOM: int = 345
CUSTOMER_AREA_HEIGHT: int = 280  # 345 - 65
CUSTOMER_AREA_RECT: Tuple[int, int, int, int] = (
    0,
    CUSTOMER_AREA_TOP,
    SCREEN_WIDTH,
    CUSTOMER_AREA_HEIGHT,
)
# 별칭 (다른 모듈 호환용)
BG_AREA_Y: int = CUSTOMER_AREA_Y
BG_AREA_HEIGHT: int = CUSTOMER_AREA_HEIGHT
CUSTOMER_Y_TOP: int = CUSTOMER_AREA_TOP
CUSTOMER_Y_BOTTOM: int = CUSTOMER_AREA_BOTTOM

COUNTER_TOP: int = 345
COUNTER_Y: int = 345
COUNTER_BOTTOM: int = 720
COUNTER_HEIGHT: int = 375  # 720 - 345
COUNTER_RECT: Tuple[int, int, int, int] = (
    0,
    COUNTER_TOP,
    SCREEN_WIDTH,
    COUNTER_HEIGHT,
)
# 별칭 (다른 모듈 호환용)
COOKING_AREA_Y: int = COUNTER_Y
COOKING_AREA_HEIGHT: int = COUNTER_HEIGHT
STATION_AREA_Y: int = COUNTER_Y
STATION_AREA_HEIGHT: int = COUNTER_HEIGHT

# 조리대 4슬롯 및 보조 영역 권장 X 좌표 레이아웃
STATION_SLOT_TYPES: Tuple[str, ...] = ("mold", "grill", "batch_pot", "dispenser")

# ==============================================================================
# 컬러 팔레트 (RGB 튜플)
# ==============================================================================
# 기본 색상
WHITE: Tuple[int, int, int] = (255, 255, 255)
BLACK: Tuple[int, int, int] = (15, 15, 20)
PURE_BLACK: Tuple[int, int, int] = (0, 0, 0)
GRAY: Tuple[int, int, int] = (128, 130, 140)
LIGHT_GRAY: Tuple[int, int, int] = (195, 198, 208)
DARK_GRAY: Tuple[int, int, int] = (55, 58, 68)
CREAM: Tuple[int, int, int] = (255, 248, 231)
GOLD: Tuple[int, int, int] = (255, 210, 55)
YELLOW: Tuple[int, int, int] = (255, 225, 70)
ORANGE: Tuple[int, int, int] = (255, 135, 45)
RED: Tuple[int, int, int] = (230, 55, 50)
GREEN: Tuple[int, int, int] = (65, 215, 95)
BLUE: Tuple[int, int, int] = (65, 145, 245)
CYAN: Tuple[int, int, int] = (55, 225, 240)
MAGENTA: Tuple[int, int, int] = (235, 75, 175)
PURPLE: Tuple[int, int, int] = (155, 85, 235)
BROWN: Tuple[int, int, int] = (135, 85, 45)
DARK_BROWN: Tuple[int, int, int] = (70, 42, 24)

# 포장마차 감성 & 카운터 색상
POCHA_ORANGE: Tuple[int, int, int] = (242, 102, 39)
POCHA_RED: Tuple[int, int, int] = (208, 48, 42)
POCHA_WARM_LIGHT: Tuple[int, int, int] = (255, 216, 138)
POCHA_TENT_BG: Tuple[int, int, int] = (46, 26, 22)
POCHA_TENT_STRIPE: Tuple[int, int, int] = (185, 58, 36)
POCHA_WOOD: Tuple[int, int, int] = (128, 78, 42)
POCHA_WOOD_DARK: Tuple[int, int, int] = (78, 46, 26)
POCHA_COUNTER_BG: Tuple[int, int, int] = (52, 38, 32)
POCHA_STAINLESS: Tuple[int, int, int] = (176, 184, 194)
POCHA_STAINLESS_DARK: Tuple[int, int, int] = (96, 104, 116)
STEEL_GRAY: Tuple[int, int, int] = (165, 175, 185)
DARK_STEEL: Tuple[int, int, int] = (85, 92, 102)

# 야시장 밤하늘 & 네온 사인 색상
NIGHT_SKY_TOP: Tuple[int, int, int] = (18, 16, 36)
NIGHT_SKY_BOTTOM: Tuple[int, int, int] = (44, 30, 62)
NEON_PINK: Tuple[int, int, int] = (255, 68, 168)
NEON_CYAN: Tuple[int, int, int] = (42, 238, 255)
NEON_YELLOW: Tuple[int, int, int] = (255, 232, 62)
NEON_GREEN: Tuple[int, int, int] = (62, 252, 132)
NEON_ORANGE: Tuple[int, int, int] = (255, 128, 42)
NEON_PURPLE: Tuple[int, int, int] = (186, 88, 255)
NEON_BLUE: Tuple[int, int, int] = (68, 148, 255)

# UI 패널 및 텍스트 색상
UI_BG: Tuple[int, int, int] = (26, 24, 36)
UI_PANEL: Tuple[int, int, int] = (42, 38, 56)
UI_PANEL_DARK: Tuple[int, int, int] = (30, 27, 42)
UI_PANEL_LIGHT: Tuple[int, int, int] = (64, 58, 84)
UI_BORDER: Tuple[int, int, int] = (112, 98, 142)
UI_HIGHLIGHT: Tuple[int, int, int] = (255, 198, 58)
UI_BUTTON: Tuple[int, int, int] = (72, 64, 98)
UI_BUTTON_HOVER: Tuple[int, int, int] = (98, 88, 132)
UI_BUTTON_ACTIVE: Tuple[int, int, int] = (232, 108, 42)
UI_DISABLED: Tuple[int, int, int] = (68, 68, 76)

TEXT_PRIMARY: Tuple[int, int, int] = (250, 246, 238)
TEXT_SECONDARY: Tuple[int, int, int] = (196, 190, 208)
TEXT_MUTED: Tuple[int, int, int] = (132, 126, 148)
TEXT_GOLD: Tuple[int, int, int] = (255, 215, 64)
TEXT_WARNING: Tuple[int, int, int] = (255, 108, 52)
TEXT_SUCCESS: Tuple[int, int, int] = (82, 235, 118)

# 게이지 색상 (조리 진행도 / 타는 시간 / 손님 인내심)
GAUGE_BG: Tuple[int, int, int] = (34, 34, 42)
GAUGE_BORDER: Tuple[int, int, int] = (90, 90, 105)
GAUGE_COOKING: Tuple[int, int, int] = (255, 188, 42)
GAUGE_READY: Tuple[int, int, int] = (62, 228, 96)
GAUGE_WARNING: Tuple[int, int, int] = (255, 112, 38)
GAUGE_BURNT: Tuple[int, int, int] = (218, 42, 42)

PATIENCE_HIGH: Tuple[int, int, int] = (72, 224, 104)
PATIENCE_MID: Tuple[int, int, int] = (252, 192, 48)
PATIENCE_LOW: Tuple[int, int, int] = (238, 58, 54)

# 국가별 테마 대표 색상
COUNTRY_COLORS: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "KR": {
        "primary": (235, 92, 42),      # 한국 포장마차 다홍/주황
        "secondary": (48, 118, 212),   # 청사초롱 블루
        "accent": (255, 208, 68),      # 알전구 골드
        "bg_top": (22, 20, 42),
        "bg_bottom": (58, 34, 44),
    },
    "JP": {
        "primary": (218, 56, 72),      # 도톤보리 등불 레드
        "secondary": (245, 232, 208),  # 노렌 아이보리
        "accent": (255, 184, 52),      # 네온 앰버
        "bg_top": (18, 22, 46),
        "bg_bottom": (52, 28, 54),
    },
    "MX": {
        "primary": (38, 178, 96),      # 피에스타 그린
        "secondary": (238, 72, 48),    # 살사 레드
        "accent": (255, 212, 48),      # 마리골드 옐로우
        "bg_top": (28, 18, 44),
        "bg_bottom": (68, 36, 38),
    },
    "TW": {
        "primary": (232, 68, 52),      # 지우펀/스린 홍등 레드
        "secondary": (48, 212, 204),   # 네온 제이드
        "accent": (255, 218, 76),      # 황금빛 야시장
        "bg_top": (20, 18, 38),
        "bg_bottom": (62, 28, 48),
    },
}

# 딕셔너리 형태 컬러 팔레트 (키 기반 조회 호환용)
COLORS: Dict[str, Tuple[int, int, int]] = {
    "WHITE": WHITE,
    "BLACK": BLACK,
    "PURE_BLACK": PURE_BLACK,
    "GRAY": GRAY,
    "LIGHT_GRAY": LIGHT_GRAY,
    "DARK_GRAY": DARK_GRAY,
    "CREAM": CREAM,
    "GOLD": GOLD,
    "YELLOW": YELLOW,
    "ORANGE": ORANGE,
    "RED": RED,
    "GREEN": GREEN,
    "BLUE": BLUE,
    "CYAN": CYAN,
    "MAGENTA": MAGENTA,
    "PURPLE": PURPLE,
    "BROWN": BROWN,
    "DARK_BROWN": DARK_BROWN,
    "POCHA_ORANGE": POCHA_ORANGE,
    "POCHA_RED": POCHA_RED,
    "POCHA_WARM_LIGHT": POCHA_WARM_LIGHT,
    "POCHA_TENT_BG": POCHA_TENT_BG,
    "POCHA_TENT_STRIPE": POCHA_TENT_STRIPE,
    "POCHA_WOOD": POCHA_WOOD,
    "POCHA_WOOD_DARK": POCHA_WOOD_DARK,
    "POCHA_COUNTER_BG": POCHA_COUNTER_BG,
    "POCHA_STAINLESS": POCHA_STAINLESS,
    "POCHA_STAINLESS_DARK": POCHA_STAINLESS_DARK,
    "STEEL_GRAY": STEEL_GRAY,
    "DARK_STEEL": DARK_STEEL,
    "NIGHT_SKY_TOP": NIGHT_SKY_TOP,
    "NIGHT_SKY_BOTTOM": NIGHT_SKY_BOTTOM,
    "NEON_PINK": NEON_PINK,
    "NEON_CYAN": NEON_CYAN,
    "NEON_YELLOW": NEON_YELLOW,
    "NEON_GREEN": NEON_GREEN,
    "NEON_ORANGE": NEON_ORANGE,
    "NEON_PURPLE": NEON_PURPLE,
    "NEON_BLUE": NEON_BLUE,
    "UI_BG": UI_BG,
    "UI_PANEL": UI_PANEL,
    "UI_PANEL_DARK": UI_PANEL_DARK,
    "UI_PANEL_LIGHT": UI_PANEL_LIGHT,
    "UI_BORDER": UI_BORDER,
    "UI_HIGHLIGHT": UI_HIGHLIGHT,
    "UI_BUTTON": UI_BUTTON,
    "UI_BUTTON_HOVER": UI_BUTTON_HOVER,
    "UI_BUTTON_ACTIVE": UI_BUTTON_ACTIVE,
    "UI_DISABLED": UI_DISABLED,
    "TEXT_PRIMARY": TEXT_PRIMARY,
    "TEXT_SECONDARY": TEXT_SECONDARY,
    "TEXT_MUTED": TEXT_MUTED,
    "TEXT_GOLD": TEXT_GOLD,
    "TEXT_WARNING": TEXT_WARNING,
    "TEXT_SUCCESS": TEXT_SUCCESS,
    "GAUGE_BG": GAUGE_BG,
    "GAUGE_BORDER": GAUGE_BORDER,
    "GAUGE_COOKING": GAUGE_COOKING,
    "GAUGE_READY": GAUGE_READY,
    "GAUGE_WARNING": GAUGE_WARNING,
    "GAUGE_BURNT": GAUGE_BURNT,
    "PATIENCE_HIGH": PATIENCE_HIGH,
    "PATIENCE_MID": PATIENCE_MID,
    "PATIENCE_LOW": PATIENCE_LOW,
}

# ==============================================================================
# 게임 밸런스 상수
# ==============================================================================
DAY_DURATION: float = 90.0  # 하루 영업 시간(초)

# 손님 관련 상수
BASE_MAX_CUSTOMERS: int = 3
MAX_CUSTOMER_SLOTS: int = 4  # 플라스틱 의자 업그레이드 시 최대 4명
CUSTOMER_SPAWN_MIN: float = 4.0
CUSTOMER_SPAWN_MAX: float = 7.5
CUSTOMER_SPAWN_INTERVAL: Tuple[float, float] = (CUSTOMER_SPAWN_MIN, CUSTOMER_SPAWN_MAX)
BASE_CUSTOMER_PATIENCE: float = 28.0  # 기본 손님 인내심(초)
VIP_PATIENCE_MULT: float = 0.85       # VIP/관광객은 인내심이 조금 더 짧음
VIP_TIP_MULT: float = 1.60            # VIP/관광객 기본 팁 배율
BASE_VIP_CHANCE: float = 0.12         # 기본 VIP/관광객 등장 확률 (12%)

# 콤보 & 팁 상수
COMBO_WINDOW: float = 10.0            # 콤보 유지 제한 시간(초)
COMBO_TIMEOUT: float = COMBO_WINDOW
COMBO_TIP_RATE: float = 0.05          # 콤보 1스택당 기본 5% 추가 팁
MAX_COMBO_TIP_RATE: float = 0.50      # 최대 기본 콤보 팁 비율 (50%)
FAST_SERVE_PATIENCE_RATIO: float = 0.65  # 인내심 65% 이상 남았을 때 서빙 시 콤보/팁 보너스

# 조리 기구 기본 슬롯/서빙 수 상수
BASE_MOLD_SLOTS: int = 2
BASE_GRILL_SLOTS: int = 2
BASE_BATCH_SERVINGS: int = 3
BASE_DISPENSER_SLOTS: int = 2
BASE_TRAY_SLOTS: int = 2

# 1:1 네트워크 결투 모드 기본 상수
DEFAULT_DUEL_PORT: int = 15432
DEFAULT_DISCOVERY_PORT: int = 15433
DUEL_STATE_SYNC_INTERVAL: float = 0.15
DUEL_DURATION_OPTIONS: Tuple[int, ...] = (60, 90, 120)
DUEL_DEFAULT_DURATION: int = 90
DUEL_DEFAULT_STATION_LEVEL: int = 2

# ==============================================================================
# 한글 폰트 로더 (Windows 시스템 폰트 우선 탐색 및 캐싱)
# ==============================================================================
_FONT_CACHE: Dict[Tuple[int, bool], pygame.font.Font] = {}
_RESOLVED_FONT_PATH: Optional[str] = None
_RESOLVED_FONT_BOLD_PATH: Optional[str] = None
_FONT_SEARCH_DONE: bool = False

# Malgun Gothic(맑은 고딕)에서 네모 박스(.notdef)로 깨지는 유니코드 이모지/기호를
# 맑은 고딕이 100% 지원하는 KS X 1001 특수기호로 치환하는 테이블
_UNSUPPORTED_EMOJI_MAP: Dict[str, str] = {
    "\ufe0f": "",
    "\u200d": "",
    "🇰🇷": "[KR]",
    "🇯🇵": "[JP]",
    "🇲🇽": "[MX]",
    "🇹🇼": "[TW]",
    "👨‍🍳": "★",
    "➔": "→",
    "⬅": "◀",
    "⇄": "↔",
    "✓": "★",
    "✔": "★",
    "✦": "◆",
    "⚡": "★",
    "⚙": "◈",
    "⏱": "●",
    "🏮": "★",
    "🗺": "◆",
    "💰": "◈",
    "🔥": "♨",
    "🛠": "◆",
    "🔒": "[잠김]",
    "🔓": "[해금]",
    "📅": "◆",
    "🎯": "◎",
    "😊": "♥",
    "💢": "♨",
    "🏦": "◈",
    "💡": "※",
    "🎊": "★",
    "🎉": "★",
    "🌟": "★",
    "🏆": "★",
    "🎮": "◈",
    "💾": "◈",
    "🔄": "↔",
    "🏠": "◈",
    "🗑": "◈",
    "🧋": "★",
    "🌮": "★",
    "👨": "",
    "🍳": "",
    "🧙": "★",
    "♂": "",
    "⚔": "◆",
    "⏳": "●",
    "⌛": "●",
    "⚠": "※",
    "👑": "★",
    "🤝": "♥",
    "💔": "♨",
    "📡": "◈",
    "🌐": "◆",
    "🥇": "★",
    "🥈": "◆",
    "⚖": "↔",
    "🖥": "◈",
    "🏳": "◀",
    "✅": "★",
    "✕": "X",
    "🪟": "◈",
    "🔊": "♪",
    "🔇": "×",
    "🎵": "♪",
    "🔔": "♪",
    "🎚": "◈",
    "✨": "★",
}


def sanitize_font_text(text: str) -> str:
    """한글 시스템 폰트(malgun.ttf 등)에서 지원하지 않는 이모지를 안전한 기호로 변환한다."""
    if not text:
        return ""
    s = str(text)
    for k, v in _UNSUPPORTED_EMOJI_MAP.items():
        if k in s:
            s = s.replace(k, v)
    # 0x1F000 이상의 보충 평면 이모지가 남아 있으면 안전 기호로 대체
    if any(ord(ch) >= 0x1F000 for ch in s):
        s = "".join("★" if ord(ch) >= 0x1F000 else ch for ch in s)
    return s


class SafeKoreanFont(pygame.font.Font):
    """이모지/미지원 특수문자를 자동 치환하고 렌더링 결과를 캐싱하여 고속 렌더링을 보장하는 Font 서브클래스."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._render_cache: Dict[Tuple[str, bool, Tuple[int, ...], Optional[Tuple[int, ...]]], pygame.Surface] = {}
        self._size_cache: Dict[str, Tuple[int, int]] = {}

    def render(  # type: ignore[override]
        self,
        text: str,
        antialias: bool,
        color: Tuple[int, ...],
        background: Optional[Tuple[int, ...]] = None,
    ) -> pygame.Surface:
        s = str(text) if text else ""
        c_key = (int(color[0]), int(color[1]), int(color[2]))
        b_key = (int(background[0]), int(background[1]), int(background[2])) if background is not None else None
        cache_key = (s, bool(antialias), c_key, b_key)
        cached = self._render_cache.get(cache_key)
        if cached is not None:
            return cached

        clean_text = sanitize_font_text(s)
        if background is None:
            surf = super().render(clean_text, antialias, c_key)
        else:
            surf = super().render(clean_text, antialias, c_key, b_key)

        if len(self._render_cache) > 1200:
            self._render_cache.clear()
        self._render_cache[cache_key] = surf
        return surf

    def size(self, text: str) -> Tuple[int, int]:  # type: ignore[override]
        s = str(text) if text else ""
        cached = self._size_cache.get(s)
        if cached is not None:
            return cached
        res = super().size(sanitize_font_text(s))
        if len(self._size_cache) > 1200:
            self._size_cache.clear()
        self._size_cache[s] = res
        return res


def _find_korean_font_paths() -> Tuple[Optional[str], Optional[str]]:
    """Windows 시스템 폰트 디렉토리에서 한글 지원 폰트 파일 경로를 탐색한다."""
    global _RESOLVED_FONT_PATH, _RESOLVED_FONT_BOLD_PATH, _FONT_SEARCH_DONE
    if _FONT_SEARCH_DONE:
        return _RESOLVED_FONT_PATH, _RESOLVED_FONT_BOLD_PATH

    bundled_fonts_dir = os.path.join(BASE_DIR, "assets", "fonts")
    rel_fonts_dir = os.path.join("assets", "fonts")
    win_dir = os.environ.get("WINDIR", r"C:\Windows")
    fonts_dir = os.path.join(win_dir, "Fonts")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    user_fonts_dir = (
        os.path.join(local_app_data, "Microsoft", "Windows", "Fonts")
        if local_app_data
        else ""
    )

    regular_candidates = [
        "NanumGothic.ttf",
        "malgun.ttf",
        "gulim.ttc",
        "batang.ttc",
        "msgothic.ttc",
    ]
    bold_candidates = [
        "NanumGothicBold.ttf",
        "malgunbd.ttf",
        "NanumGothic.ttf",
        "malgun.ttf",
        "gulim.ttc",
    ]

    search_dirs = [d for d in (bundled_fonts_dir, rel_fonts_dir, fonts_dir, user_fonts_dir) if d and os.path.isdir(d)]

    for directory in search_dirs:
        if _RESOLVED_FONT_PATH is None:
            for fname in regular_candidates:
                candidate = os.path.join(directory, fname)
                if os.path.isfile(candidate):
                    _RESOLVED_FONT_PATH = candidate
                    break
        if _RESOLVED_FONT_BOLD_PATH is None:
            for fname in bold_candidates:
                candidate = os.path.join(directory, fname)
                if os.path.isfile(candidate):
                    _RESOLVED_FONT_BOLD_PATH = candidate
                    break

    if _RESOLVED_FONT_PATH is None:
        matched = pygame.font.match_font(
            ["malgungothic", "malgun gothic", "맑은 고딕", "nanumgothic", "gulim", "dotum"]
        )
        if matched and os.path.isfile(matched):
            _RESOLVED_FONT_PATH = matched

    if _RESOLVED_FONT_BOLD_PATH is None:
        matched_bold = pygame.font.match_font(
            ["malgungothic", "malgun gothic", "맑은 고딕", "nanumgothic", "gulim"],
            bold=True,
        )
        if matched_bold and os.path.isfile(matched_bold):
            _RESOLVED_FONT_BOLD_PATH = matched_bold
        else:
            _RESOLVED_FONT_BOLD_PATH = _RESOLVED_FONT_PATH

    _FONT_SEARCH_DONE = True
    return _RESOLVED_FONT_PATH, _RESOLVED_FONT_BOLD_PATH


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """
    지정된 크기와 굵기의 한글 지원 Pygame Font 객체를 캐싱하여 반환한다.
    Windows 시스템 폰트(malgunbd.ttf, malgun.ttf, gulim.ttc, SysFont('malgungothic'))를
    우선 탐색하여 한글 및 특수기호가 절대 깨지지 않도록 보장한다.
    """
    if not pygame.font.get_init():
        pygame.font.init()

    size = max(8, int(size))
    cache_key = (size, bool(bold))
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    reg_path, bold_path = _find_korean_font_paths()
    target_path = bold_path if bold else reg_path

    font_obj: Optional[pygame.font.Font] = None
    if target_path and os.path.isfile(target_path):
        try:
            font_obj = SafeKoreanFont(target_path, size)
            if bold and target_path == reg_path and not target_path.lower().endswith("bd.ttf"):
                font_obj.set_bold(True)
        except Exception:
            font_obj = None

    if font_obj is None:
        try:
            font_obj = pygame.font.SysFont(
                ["malgungothic", "malgun gothic", "맑은 고딕", "gulim", "arial"],
                size,
                bold=bold,
            )
        except Exception:
            font_obj = SafeKoreanFont(None, size)

    _FONT_CACHE[cache_key] = font_obj
    return font_obj
