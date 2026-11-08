"""
data/specialist_menus.py
단일 메뉴 장인 모드(SPECIALIST MODE) 전용 전문점 카탈로그 및 레시피·토핑 매핑 모듈.
- 1차 오픈 전문점 (즉시 플레이 가능 · 각 8가지 맛 변주):
  1) bungeo  : 🐟 황금 붕어빵 장인 (6종 속재료 + 2종 토핑 = 8가지 메뉴)
  2) odeng   : 🍢 심야 오뎅바 장인 (6종 수제어묵·2색육수 + 2종 고명·간장 = 8가지 메뉴)
  3) skewer  : 🔥 참숯 직화 닭꼬치 장인 (4종 원육 꼬치 + 4종 특제소스·토핑 = 8가지 메뉴)
- 차후 순차 오픈 예정 전문점 (COMING SOON 로비 프리뷰 제공):
  4) tteokbokki : 🌶️ 무쇠 철판 떡볶이 장인
  5) takoyaki   : 🐙 오사카 타코야키 장인
  6) taco       : 🌮 멕시코 타코 피에스타 장인
  7) taiwan     : 🧋 대만 야시장 지파이·버블티 장인
  8) mala       : 🌶️ 사천 마라탕 & 양꼬치 장인
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from data.characters import AttrDict

SPECIALIST_ORDER: List[str] = [
    "bungeo",
    "odeng",
    "skewer",
    "tteokbokki",
    "takoyaki",
    "taco",
    "taiwan",
    "mala",
]

OPEN_SPECIALIST_ORDER: List[str] = [
    "bungeo",
    "odeng",
    "skewer",
]


_RAW_SPECIALIST_MENUS: Dict[str, Dict[str, Any]] = {
    # ==========================================================================
    # 1. [OPEN] 🐟 황금 붕어빵 장인 (8종 맛 완비)
    # ==========================================================================
    "bungeo": {
        "id": "bungeo",
        "name": "황금 붕어빵 장인",
        "short_name": "붕어빵 장인",
        "emoji": "🐟",
        "country": "KR",
        "is_open": True,
        "slot_type": "mold",
        "station_id": "spec_bungeo",
        "theme_color": (218, 138, 38),
        "accent_color": (255, 214, 78),
        "subtitle": "6종 속재료 × 6구 회전 무쇠틀 × 슈가·아이스크림 토핑",
        "description": "통단팥·슈크림·피자치즈·꿀고구마·초코·김치만두 속재료를 넣어 굽고 슈가파우더와 아이스크림을 올리는 붕어빵 전문점!",
        "input_panel_title": "🐟 ① 반죽 & 6종 속재료 선택 (터치 투입)",
        "appliance_title": "🔥 ② 6구 회전 황금 붕어빵 무쇠틀",
        "tray_title": "✨ ③ 슈가·아이스크림 토핑 & 서빙대",
        "base_recipes": [
            "bungeoppang_redbean",
            "bungeoppang_cream",
            "bungeoppang_pizza",
            "bungeoppang_sweetpotato",
            "bungeoppang_choco",
            "bungeoppang_kimchi",
        ],
        "all_recipes": [
            "bungeoppang_redbean",
            "bungeoppang_cream",
            "bungeoppang_pizza",
            "bungeoppang_sweetpotato",
            "bungeoppang_choco",
            "bungeoppang_kimchi",
            "bungeoppang_sugar",
            "bungeoppang_icecream",
        ],
        "topping_ids": [
            "sugar_powder",
            "vanilla_icecream",
        ],
        "preview_flavors": [
            "팥 붕어빵",
            "슈크림 붕어빵",
            "피자치즈 붕어빵",
            "꿀고구마 붕어빵",
            "초코누텔라 붕어빵",
            "김치만두 붕어빵",
            "슈가파우더 붕어빵",
            "아이스크림 붕어빵",
        ],
        "base_target_gold": 14000,
        "daily_target_growth": 3600,
    },

    # ==========================================================================
    # 2. [OPEN] 🍢 심야 오뎅바 장인 (8종 맛 완비)
    # ==========================================================================
    "odeng": {
        "id": "odeng",
        "name": "심야 오뎅바 장인",
        "short_name": "오뎅바 장인",
        "emoji": "🍢",
        "country": "KR",
        "is_open": True,
        "slot_type": "batch_pot",
        "station_id": "spec_odeng",
        "theme_color": (198, 128, 52),
        "accent_color": (118, 224, 152),
        "subtitle": "맑은육수·빨간육수 6구 사각솥 × 6종 수제어묵 × 특제간장",
        "description": "꼬불이오뎅·부산물떡·얼큰매운오뎅·통모짜치즈바·유부주머니·문어새우볼을 끓여 대파송송과 와사비간장을 곁들이는 심야 오뎅바!",
        "input_panel_title": "🍢 ① 6종 수제어묵 & 육수 선택 (터치 입수)",
        "appliance_title": "♨️ ② 6구 2색육수 심야 사각 오뎅솥",
        "tray_title": "🥢 ③ 대파고명·와사비간장 & 서빙대",
        "base_recipes": [
            "odeng_clean_wave",
            "odeng_clean_tteok",
            "odeng_red_spicy",
            "odeng_cheese_bar",
            "odeng_yubu_pouch",
            "odeng_seafood_ball",
        ],
        "all_recipes": [
            "odeng_clean_wave",
            "odeng_clean_tteok",
            "odeng_red_spicy",
            "odeng_cheese_bar",
            "odeng_yubu_pouch",
            "odeng_seafood_ball",
            "odeng_scallion_soup",
            "odeng_wasabi_tteok",
        ],
        "topping_ids": [
            "odeng_scallion",
            "wasabi_soy",
        ],
        "preview_flavors": [
            "맑은 꼬불이오뎅",
            "부산 가래떡 물떡",
            "얼큰 빨간오뎅",
            "통모짜 치즈어묵바",
            "당면 유부주머니",
            "문어새우 어묵볼",
            "대파송송 꼬불이오뎅",
            "와사비간장 부산물떡",
        ],
        "base_target_gold": 13500,
        "daily_target_growth": 3500,
    },

    # ==========================================================================
    # 3. [OPEN] 🔥 참숯 직화 닭꼬치 장인 (8종 맛 완비)
    # ==========================================================================
    "skewer": {
        "id": "skewer",
        "name": "참숯 닭꼬치 장인",
        "short_name": "닭꼬치 장인",
        "emoji": "🔥",
        "country": "KR",
        "is_open": True,
        "slot_type": "grill",
        "station_id": "spec_skewer",
        "theme_color": (212, 64, 42),
        "accent_color": (255, 148, 62),
        "subtitle": "4종 생꼬치 원육 × 6구 참숯 와이드 석쇠 × 4종 특제소스",
        "description": "대파닭꼬치·통마늘닭꼬치·염통꼬치·삼겹떡말이를 참숯에 초벌하고 매운양념·데리야키·파채·눈꽃치즈를 올리는 직화 꼬치 전문점!",
        "input_panel_title": "🔥 ① 4종 생꼬치 원육 선택 (터치 석쇠 투입)",
        "appliance_title": "🔥 ② 6구 참숯 와이드 직화 석쇠 그릴",
        "tray_title": "🌶️ ③ 4종 특제소스·토핑 & 서빙대",
        "base_recipes": [
            "skewer_plain",
            "skewer_garlic_base",
            "skewer_heart_base",
            "skewer_pork_tteok",
        ],
        "all_recipes": [
            "skewer_plain",
            "skewer_garlic_base",
            "skewer_heart_base",
            "skewer_pork_tteok",
            "skewer_spicy",
            "skewer_teriyaki",
            "skewer_greenonion",
            "skewer_cheese_pork",
        ],
        "topping_ids": [
            "spicy_sauce",
            "teriyaki_sauce",
            "green_onion",
            "cheese",
        ],
        "preview_flavors": [
            "소금구이 닭꼬치",
            "통마늘 닭꼬치",
            "참숯 염통꼬치",
            "삼겹 떡말이꼬치",
            "매운양념 닭꼬치",
            "데리야키 닭꼬치",
            "파채 양념닭꼬치",
            "눈꽃치즈 떡말이꼬치",
        ],
        "base_target_gold": 15000,
        "daily_target_growth": 3800,
    },

    # ==========================================================================
    # 4~8. [COMING SOON] 차후 순차 업데이트 예정 장인 전문점 5종
    # ==========================================================================
    "tteokbokki": {
        "id": "tteokbokki",
        "name": "무쇠 철판 떡볶이 장인",
        "short_name": "떡볶이 장인",
        "emoji": "🌶️",
        "country": "KR",
        "is_open": False,
        "slot_type": "batch_pot",
        "station_id": "spec_tteokbokki",
        "theme_color": (218, 48, 48),
        "accent_color": (255, 198, 68),
        "subtitle": "밀떡·쌀떡·분모자 × 고추장·로제·짜장 × 튀김·치즈 토핑",
        "description": "[차후 업데이트 예정] 쫄깃 밀떡, 부산 가래떡, 분모자를 고추장·로제·짜장 양념으로 조리하고 김말이·치즈·삶은계란을 얹는 분식 장인 모드!",
        "input_panel_title": "🌶️ ① 떡 종류 & 양념장 선택",
        "appliance_title": "🥘 ② 대형 무쇠 떡볶이 철판",
        "tray_title": "🧀 ③ 사리·튀김 토핑 & 서빙대",
        "base_recipes": ["tteokbokki_plain"],
        "all_recipes": ["tteokbokki_plain", "tteokbokki_cheese", "tteokbokki_gimmari"],
        "topping_ids": ["cheese", "gimmari"],
        "preview_flavors": [
            "정통 고추장 밀떡볶이",
            "부산 가래떡 쌀떡볶이",
            "투움바 로제 분모자",
            "달콤 고소 짜장떡볶이",
            "눈꽃 모짜렐라 치즈떡볶이",
            "김말이 범벅 모둠떡볶이",
            "삶은계란 폭탄 떡볶이",
            "로제 치즈 김말이 스페셜",
        ],
        "base_target_gold": 16000,
        "daily_target_growth": 4000,
    },
    "takoyaki": {
        "id": "takoyaki",
        "name": "오사카 타코야키 장인",
        "short_name": "타코야키 장인",
        "emoji": "🐙",
        "country": "JP",
        "is_open": False,
        "slot_type": "mold",
        "station_id": "spec_takoyaki",
        "theme_color": (198, 92, 54),
        "accent_color": (255, 184, 76),
        "subtitle": "대왕문어·통새우·치즈큐브 × 도톤보리 무쇠판 × 가쓰오부시·네기마요",
        "description": "[차후 업데이트 예정] 문어·새우·치즈·콘옥수수 반죽을 동글동글 굴려 굽고 가쓰오부시·명란마요·네기를 듬뿍 올리는 도톤보리 장인 모드!",
        "input_panel_title": "🐙 ① 반죽 & 속재료 선택",
        "appliance_title": "🔥 ② 도톤보리 대형 타코야키 주물판",
        "tray_title": "🥢 ③ 오사카 토핑 바 & 서빙대",
        "base_recipes": ["takoyaki_plain", "takoyaki_mayo"],
        "all_recipes": ["takoyaki_plain", "takoyaki_mayo"],
        "topping_ids": ["tare_sauce"],
        "preview_flavors": [
            "오리지널 문어 타코야키",
            "네기마요 파듬뿍 타코야키",
            "통새우 에비 타코야키",
            "명란마요 타코야키",
            "더블 체다치즈 타코야키",
            "매콤 칠리 타코야키",
            "베이컨 콘치즈 타코야키",
            "갈릭칩 블랙 타코야키",
        ],
        "base_target_gold": 16500,
        "daily_target_growth": 4000,
    },
    "taco": {
        "id": "taco",
        "name": "멕시코 타코 피에스타 장인",
        "short_name": "타코 장인",
        "emoji": "🌮",
        "country": "MX",
        "is_open": False,
        "slot_type": "grill",
        "station_id": "spec_taco",
        "theme_color": (56, 178, 88),
        "accent_color": (255, 198, 64),
        "subtitle": "카르니타스·비프·쉬림프 × 코말 철판 × 과카몰리·살사·사워크림",
        "description": "[차후 업데이트 예정] 갓 구운 옥수수 또띠아 위에 카르니타스·비프·쉬림프를 얹고 신선한 과카몰리와 로호 살사를 조합하는 타코 장인 모드!",
        "input_panel_title": "🌮 ① 또띠아 & 메인 미트 선택",
        "appliance_title": "🔥 ② 멕시칸 코말 철판 그릴",
        "tray_title": "🥑 ③ 살사·과카몰리 바 & 서빙대",
        "base_recipes": ["taco_plain"],
        "all_recipes": ["taco_plain", "taco_salsa", "taco_guac"],
        "topping_ids": ["salsa", "guacamole"],
        "preview_flavors": [
            "포크 카르니타스 타코",
            "로호 살사 핫타코",
            "아보카도 과카몰리 타코",
            "차콜 비프스테이크 타코",
            "칠리 갈릭쉬림프 타코",
            "크리스피 치킨 타코",
            "사워크림 치즈 퀘사타코",
            "할라피뇨 파이어 타코",
        ],
        "base_target_gold": 17000,
        "daily_target_growth": 4200,
    },
    "taiwan": {
        "id": "taiwan",
        "name": "대만 지파이 & 버블티 장인",
        "short_name": "지파이·버블티",
        "emoji": "🧋",
        "country": "TW",
        "is_open": False,
        "slot_type": "grill",
        "station_id": "spec_taiwan",
        "theme_color": (168, 86, 208),
        "accent_color": (255, 208, 82),
        "subtitle": "스린 야시장 대왕 지파이 & 쫀득 흑당 타피오카 버블티 전문점",
        "description": "[차후 업데이트 예정] 바삭한 대왕 지파이에 마라·치즈·매실 시즈닝을 뿌리고 흑당 버블밀크티와 망고 스무디를 블렌딩하는 스린 야시장 장인 모드!",
        "input_panel_title": "🧋 ① 지파이 원육 & 티 베이스 선택",
        "appliance_title": "🔥 ② 스린 야시장 대형 튀김기 & 쉐이커",
        "tray_title": "✨ ③ 시즈닝·타피오카 펄 & 서빙대",
        "base_recipes": ["jipai_plain", "boba_milktea"],
        "all_recipes": ["jipai_plain", "jipai_spicy", "boba_milktea", "mango_smoothie"],
        "topping_ids": ["mala_spice"],
        "preview_flavors": [
            "오리지널 대왕 지파이",
            "사천 마라 지파이",
            "눈꽃 치즈 시즈닝 지파이",
            "단짠 간장갈릭 지파이",
            "타이베이 흑당 버블밀크티",
            "타로 폼 버블밀크티",
            "애플망고 스무디",
            "우롱 치즈폼 밀크티",
        ],
        "base_target_gold": 17500,
        "daily_target_growth": 4200,
    },
    "mala": {
        "id": "mala",
        "name": "사천 마라탕 & 양꼬치 장인",
        "short_name": "마라·양꼬치",
        "emoji": "🌶️",
        "country": "CN",
        "is_open": False,
        "slot_type": "batch_pot",
        "station_id": "spec_mala",
        "theme_color": (208, 42, 42),
        "accent_color": (255, 186, 62),
        "subtitle": "사천 홍유 마라탕 가마솥 & 실크로드 즈란 양꼬치 전문점",
        "description": "[차후 업데이트 예정] 사천 홍유·백탕 육수에 다채로운 재료를 담아 끓이고 즈란 양꼬치와 꿔바로우를 함께 내는 마라 장인 모드!",
        "input_panel_title": "🌶️ ① 마라 육수 & 꼬치 재료 선택",
        "appliance_title": "🍲 ② 사천 대형 마라 화구 & 회전 꼬치구이기",
        "tray_title": "✨ ③ 즈란·마유·땅콩소스 & 서빙대",
        "base_recipes": ["malatang_plain", "lamb_skewer_plain"],
        "all_recipes": ["malatang_plain", "lamb_skewer_plain", "lamb_skewer_cumin"],
        "topping_ids": ["cumin_spice", "mala_spice"],
        "preview_flavors": [
            "사천 홍유 마라탕",
            "고소 땅콩백탕 마라탕",
            "차돌박이 폭탄 마라탕",
            "마라샹궈 볶음",
            "실크로드 즈란 양꼬치",
            "화끈 마라 양꼬치",
            "북방 찹쌀 꿔바로우",
            "상하이 육즙 성젠바오",
        ],
        "base_target_gold": 18000,
        "daily_target_growth": 4500,
    },
}

SPECIALIST_MENUS: Dict[str, AttrDict] = {
    sid: AttrDict(sdata) for sid, sdata in _RAW_SPECIALIST_MENUS.items()
}


def get_specialist_menu(spec_id: Optional[str] = None) -> AttrDict:
    """전문점 ID로 전문가 모드 메타데이터(AttrDict)를 반환한다. 기본값은 'bungeo'."""
    key = str(spec_id or "bungeo").lower()
    if key not in SPECIALIST_MENUS:
        key = "bungeo"
    return SPECIALIST_MENUS[key]


def get_open_specialist_ids() -> List[str]:
    """현재 플레이 가능한(is_open=True) 전문가 모드 ID 리스트를 반환한다."""
    return [sid for sid in SPECIALIST_ORDER if bool(SPECIALIST_MENUS[sid].get("is_open", False))]
