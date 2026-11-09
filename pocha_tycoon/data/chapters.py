"""
월드 투어 모드 4개국 챕터(CHAPTERS) 및 글로벌 야시장 통합 모드용
16개 조리 기구 카탈로그(STATIONS_CATALOG) 정의 모듈.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from data.characters import AttrDict
from data.recipes import RECIPES, get_recipes_by_station, get_station_toppings

SLOT_TYPES: List[str] = ["mold", "grill", "batch_pot", "dispenser"]
CHAPTER_ORDER: List[str] = ["KR", "JP", "MX", "TW", "CN", "IN", "US", "RU", "BR"]


# ==============================================================================
# 16개 조리 기구 카탈로그 (STATIONS_CATALOG)
# 4개국(KR, JP, MX, TW) x 4슬롯 타입(mold, grill, batch_pot, dispenser)
# ==============================================================================
_RAW_STATIONS_CATALOG: Dict[str, Dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # 한국 (KR) 조리 기구 4종
    # --------------------------------------------------------------------------
    "kr_bungeoppang": {
        "id": "kr_bungeoppang",
        "station_id": "kr_bungeoppang",
        "name": "황금 붕어빵 틀",
        "short_name": "붕어빵 틀",
        "country": "KR",
        "slot_type": "mold",
        "base_cook_time": 2.2,
        "base_burn_time": 18.0,
        "base_slots": 6,
        "base_servings": 1,
        "color": (195, 142, 68),
        "accent_color": (255, 198, 72),
        "description": "팥 붕어빵과 슈크림 붕어빵을 바삭하게 구워내는 주물 틀",
    },
    "kr_skewer_grill": {
        "id": "kr_skewer_grill",
        "station_id": "kr_skewer_grill",
        "name": "직화 닭꼬치 그릴",
        "short_name": "닭꼬치 그릴",
        "country": "KR",
        "slot_type": "grill",
        "base_cook_time": 5.0,
        "base_burn_time": 8.5,
        "base_slots": 2,
        "base_servings": 1,
        "color": (162, 72, 48),
        "accent_color": (245, 118, 52),
        "description": "소금구이 닭꼬치를 굽고 매운양념·데리야키·파채 토핑을 올리는 그릴",
    },
    "kr_tteokbokki_pan": {
        "id": "kr_tteokbokki_pan",
        "station_id": "kr_tteokbokki_pan",
        "name": "포차 철판 떡볶이 팬",
        "short_name": "떡볶이 철판",
        "country": "KR",
        "slot_type": "batch_pot",
        "base_cook_time": 5.5,
        "base_burn_time": 11.0,
        "base_slots": 1,
        "base_servings": 3,
        "color": (212, 54, 42),
        "accent_color": (255, 168, 62),
        "description": "한 번 조리해 여러 인분을 퍼 담고 치즈·김말이 토핑을 얹는 대량 조리 팬",
    },
    "kr_odeng_dispenser": {
        "id": "kr_odeng_dispenser",
        "station_id": "kr_odeng_dispenser",
        "name": "어묵국물 & 식혜 디스펜서",
        "short_name": "어묵·식혜 통",
        "country": "KR",
        "slot_type": "dispenser",
        "base_cook_time": 2.2,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (168, 176, 188),
        "accent_color": (238, 198, 122),
        "description": "뜨끈한 어묵국물과 살얼음 식혜를 자동으로 채워주는 음료 디스펜서",
    },

    # --------------------------------------------------------------------------
    # 일본 (JP) 조리 기구 4종
    # --------------------------------------------------------------------------
    "jp_takoyaki_pan": {
        "id": "jp_takoyaki_pan",
        "station_id": "jp_takoyaki_pan",
        "name": "도톤보리 타코야키 판",
        "short_name": "타코야키 판",
        "country": "JP",
        "slot_type": "mold",
        "base_cook_time": 4.8,
        "base_burn_time": 9.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (182, 92, 58),
        "accent_color": (242, 162, 74),
        "description": "오리지널 타코야키와 네기마요 타코야키를 동글동글하게 굽는 무쇠 판",
    },
    "jp_yakitori_grill": {
        "id": "jp_yakitori_grill",
        "station_id": "jp_yakitori_grill",
        "name": "비장탄 야키토리 화로",
        "short_name": "야키토리 화로",
        "country": "JP",
        "slot_type": "grill",
        "base_cook_time": 5.0,
        "base_burn_time": 8.5,
        "base_slots": 2,
        "base_servings": 1,
        "color": (138, 66, 46),
        "accent_color": (228, 118, 56),
        "description": "시오 야키토리를 구워 비전 타레 소스를 발라 완성하는 숯불 화로",
    },
    "jp_yakisoba_pan": {
        "id": "jp_yakisoba_pan",
        "station_id": "jp_yakisoba_pan",
        "name": "야타이 야키소바 철판",
        "short_name": "야키소바 철판",
        "country": "JP",
        "slot_type": "batch_pot",
        "base_cook_time": 5.5,
        "base_burn_time": 10.5,
        "base_slots": 1,
        "base_servings": 3,
        "color": (148, 86, 48),
        "accent_color": (252, 198, 52),
        "description": "야키소바를 대량으로 볶아내고 반숙 계란후라이 토핑을 올리는 철판",
    },
    "jp_drink_dispenser": {
        "id": "jp_drink_dispenser",
        "station_id": "jp_drink_dispenser",
        "name": "나마비루 & 라무네 서버",
        "short_name": "생맥주·라무네",
        "country": "JP",
        "slot_type": "dispenser",
        "base_cook_time": 2.3,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (218, 172, 64),
        "accent_color": (82, 212, 248),
        "description": "시원한 나마비루 생맥주와 청량한 라무네 소다를 따라주는 서버",
    },

    # --------------------------------------------------------------------------
    # 멕시코 (MX) 조리 기구 4종
    # --------------------------------------------------------------------------
    "mx_quesadilla_press": {
        "id": "mx_quesadilla_press",
        "station_id": "mx_quesadilla_press",
        "name": "퀘사디야 코말 프레스",
        "short_name": "퀘사디야 프레스",
        "country": "MX",
        "slot_type": "mold",
        "base_cook_time": 4.8,
        "base_burn_time": 9.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (196, 136, 62),
        "accent_color": (255, 212, 64),
        "description": "치즈 퀘사디야와 치킨 퀘사디야를 노릇하게 눌러 굽는 프레스",
    },
    "mx_taco_grill": {
        "id": "mx_taco_grill",
        "station_id": "mx_taco_grill",
        "name": "카르니타스 타코 그릴",
        "short_name": "타코 그릴",
        "country": "MX",
        "slot_type": "grill",
        "base_cook_time": 5.0,
        "base_burn_time": 8.5,
        "base_slots": 2,
        "base_servings": 1,
        "color": (48, 156, 88),
        "accent_color": (232, 72, 52),
        "description": "카르니타스 타코를 구워 살사나 과카몰리 토핑을 얹는 멕시칸 그릴",
    },
    "mx_nacho_fryer": {
        "id": "mx_nacho_fryer",
        "station_id": "mx_nacho_fryer",
        "name": "피에스타 나초 프라이어",
        "short_name": "나초 프라이어",
        "country": "MX",
        "slot_type": "batch_pot",
        "base_cook_time": 5.2,
        "base_burn_time": 10.5,
        "base_slots": 1,
        "base_servings": 3,
        "color": (218, 152, 48),
        "accent_color": (255, 216, 66),
        "description": "바삭한 크리스피 나초를 대량으로 튀겨 치즈 소스를 듬뿍 올리는 기구",
    },
    "mx_drink_dispenser": {
        "id": "mx_drink_dispenser",
        "station_id": "mx_drink_dispenser",
        "name": "마가리타 & 콜라 디스펜서",
        "short_name": "마가리타·콜라",
        "country": "MX",
        "slot_type": "dispenser",
        "base_cook_time": 2.3,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (98, 198, 78),
        "accent_color": (222, 56, 48),
        "description": "상큼한 라임 마가리타와 톡 쏘는 멕시칸 콜라를 준비하는 디스펜서",
    },

    # --------------------------------------------------------------------------
    # 대만 (TW) 조리 기구 4종
    # --------------------------------------------------------------------------
    "tw_scallion_pan": {
        "id": "tw_scallion_pan",
        "station_id": "tw_scallion_pan",
        "name": "스린 총좌빙 무쇠팬",
        "short_name": "총좌빙 팬",
        "country": "TW",
        "slot_type": "mold",
        "base_cook_time": 4.8,
        "base_burn_time": 9.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (188, 142, 74),
        "accent_color": (96, 196, 88),
        "description": "바삭한 오리지널 총좌빙과 계란치즈 총좌빙을 구워내는 무쇠팬",
    },
    "tw_jipai_fryer": {
        "id": "tw_jipai_fryer",
        "station_id": "tw_jipai_fryer",
        "name": "대왕 지파이 튀김기",
        "short_name": "지파이 튀김기",
        "country": "TW",
        "slot_type": "grill",
        "base_cook_time": 5.2,
        "base_burn_time": 9.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (212, 122, 46),
        "accent_color": (232, 62, 48),
        "description": "대왕 지파이를 바삭하게 튀겨내고 마라 시즈닝을 뿌리는 튀김기",
    },
    "tw_cubesteak_pan": {
        "id": "tw_cubesteak_pan",
        "station_id": "tw_cubesteak_pan",
        "name": "불꽃 큐브스테이크 철판",
        "short_name": "큐브스테이크 팬",
        "country": "TW",
        "slot_type": "batch_pot",
        "base_cook_time": 5.5,
        "base_burn_time": 10.5,
        "base_slots": 1,
        "base_servings": 3,
        "color": (136, 68, 48),
        "accent_color": (248, 218, 102),
        "description": "토치 불쇼로 큐브스테이크를 대량 조리하고 갈릭버터 소스를 얹는 철판",
    },
    "tw_drink_dispenser": {
        "id": "tw_drink_dispenser",
        "station_id": "tw_drink_dispenser",
        "name": "버블티 & 망고스무디 머신",
        "short_name": "버블티·스무디",
        "country": "TW",
        "slot_type": "dispenser",
        "base_cook_time": 2.4,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (198, 146, 98),
        "accent_color": (255, 198, 42),
        "description": "쫀득한 흑당 버블티와 달콤한 망고 스무디를 제조하는 머신",
    },

    # --------------------------------------------------------------------------
    # 중국 (CN) 조리 기구 4종 (사천·광동·베이징·상하이·신장·동북)
    # --------------------------------------------------------------------------
    "cn_dumpling_pan": {
        "id": "cn_dumpling_pan",
        "station_id": "cn_dumpling_pan",
        "name": "상하이 성젠바오 & 에그와플 틀",
        "short_name": "성젠바오·와플",
        "country": "CN",
        "slot_type": "mold",
        "base_cook_time": 4.6,
        "base_burn_time": 9.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (186, 62, 46),
        "accent_color": (255, 208, 64),
        "description": "육즙 가득 상하이 성젠바오와 바삭한 홍콩 에그와플을 구워내는 팬",
    },
    "cn_lamb_grill": {
        "id": "cn_lamb_grill",
        "station_id": "cn_lamb_grill",
        "name": "실크로드 숯불 양꼬치 화로",
        "short_name": "양꼬치 화로",
        "country": "CN",
        "slot_type": "grill",
        "base_cook_time": 4.8,
        "base_burn_time": 8.8,
        "base_slots": 2,
        "base_servings": 1,
        "color": (204, 52, 42),
        "accent_color": (255, 186, 58),
        "description": "숯불 양꼬치를 굽고 즈란 파우더나 사천 마라 시즈닝을 올리는 화로",
    },
    "cn_mala_wok": {
        "id": "cn_mala_wok",
        "station_id": "cn_mala_wok",
        "name": "사천 마라탕 & 꿔바로우 대형 웍",
        "short_name": "중화 대형 웍",
        "country": "CN",
        "slot_type": "batch_pot",
        "base_cook_time": 5.2,
        "base_burn_time": 10.5,
        "base_slots": 1,
        "base_servings": 3,
        "color": (168, 42, 36),
        "accent_color": (255, 162, 52),
        "description": "얼얼한 사천 마라탕과 북방 탕수 소스를 입힌 꿔바로우를 조리하는 대형 웍",
    },
    "cn_drink_dispenser": {
        "id": "cn_drink_dispenser",
        "station_id": "cn_drink_dispenser",
        "name": "산사자차 & 홍콩 밀크티 서버",
        "short_name": "산사차·동윤영",
        "country": "CN",
        "slot_type": "dispenser",
        "base_cook_time": 2.2,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (182, 52, 58),
        "accent_color": (245, 202, 92),
        "description": "상큼한 베이징 산사자차와 진한 홍콩 동윤영 밀크티를 추출하는 서버",
    },

    # --------------------------------------------------------------------------
    # 인도 (IN) 조리 기구 4종 (델리·뭄바이·첸나이·콜카타·펀자브·하이데라바드)
    # --------------------------------------------------------------------------
    "in_naan_tandoor": {
        "id": "in_naan_tandoor",
        "station_id": "in_naan_tandoor",
        "name": "갈릭 난 & 사모사 화덕",
        "short_name": "난·사모사 화덕",
        "country": "IN",
        "slot_type": "mold",
        "base_cook_time": 4.5,
        "base_burn_time": 9.2,
        "base_slots": 2,
        "base_servings": 1,
        "color": (212, 126, 46),
        "accent_color": (255, 212, 68),
        "description": "화덕 갈릭버터 난과 바삭한 황금 카레 사모사를 구워내는 탄두르",
    },
    "in_tikka_grill": {
        "id": "in_tikka_grill",
        "station_id": "in_tikka_grill",
        "name": "올드델리 탄두리 티카 그릴",
        "short_name": "탄두리 그릴",
        "country": "IN",
        "slot_type": "grill",
        "base_cook_time": 4.9,
        "base_burn_time": 8.8,
        "base_slots": 2,
        "base_servings": 1,
        "color": (218, 82, 38),
        "accent_color": (72, 212, 132),
        "description": "탄두리 치킨 티카를 굽고 민트 처트니·가람마살라를 더하는 그릴",
    },
    "in_curry_pot": {
        "id": "in_curry_pot",
        "station_id": "in_curry_pot",
        "name": "버터치킨 & 황금 비리야니 솥",
        "short_name": "커리·비리야니 솥",
        "country": "IN",
        "slot_type": "batch_pot",
        "base_cook_time": 5.2,
        "base_burn_time": 10.8,
        "base_slots": 1,
        "base_servings": 3,
        "color": (228, 142, 42),
        "accent_color": (255, 218, 88),
        "description": "진한 버터 치킨 커리와 하이데라바드 황금솥 둠 비리야니를 쪄내는 솥",
    },
    "in_drink_dispenser": {
        "id": "in_drink_dispenser",
        "station_id": "in_drink_dispenser",
        "name": "망고 라씨 & 마살라 차이 항아리",
        "short_name": "라씨·차이 포트",
        "country": "IN",
        "slot_type": "dispenser",
        "base_cook_time": 2.2,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (238, 168, 48),
        "accent_color": (196, 62, 148),
        "description": "펀자브 특대형 망고 라씨와 향긋한 마살라 차이를 따라주는 포트",
    },

    # --------------------------------------------------------------------------
    # 미국 (US) 조리 기구 4종 (뉴욕·텍사스·캘리포니아·뉴올리언스·필라델피아)
    # --------------------------------------------------------------------------
    "us_hotdog_roller": {
        "id": "us_hotdog_roller",
        "station_id": "us_hotdog_roller",
        "name": "뉴욕 핫도그 & 베녜 베이커",
        "short_name": "핫도그·베녜 틀",
        "country": "US",
        "slot_type": "mold",
        "base_cook_time": 4.5,
        "base_burn_time": 9.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (56, 108, 204),
        "accent_color": (238, 68, 58),
        "description": "맨해튼 칠리 핫도그와 뉴올리언스 슈가 베녜 도넛을 구워내는 기구",
    },
    "us_smash_grill": {
        "id": "us_smash_grill",
        "station_id": "us_smash_grill",
        "name": "스매시 치즈버거 & 텍사스 스모커",
        "short_name": "버거·BBQ 그릴",
        "country": "US",
        "slot_type": "grill",
        "base_cook_time": 4.8,
        "base_burn_time": 8.8,
        "base_slots": 2,
        "base_servings": 1,
        "color": (182, 58, 48),
        "accent_color": (255, 202, 56),
        "description": "LA 스매시 치즈버거에 베이컨을 얹거나 텍사스 훈제 브리스킷을 굽는 그릴",
    },
    "us_fryer_pot": {
        "id": "us_fryer_pot",
        "station_id": "us_fryer_pot",
        "name": "버팔로 윙 & 맥앤치즈 프라이어",
        "short_name": "윙·맥앤치즈 팬",
        "country": "US",
        "slot_type": "batch_pot",
        "base_cook_time": 5.2,
        "base_burn_time": 10.5,
        "base_slots": 1,
        "base_servings": 3,
        "color": (218, 128, 42),
        "accent_color": (255, 212, 64),
        "description": "매콤한 버팔로 윙과 치즈 폭탄 맥앤치즈를 대량 조리하는 프라이어",
    },
    "us_drink_dispenser": {
        "id": "us_drink_dispenser",
        "station_id": "us_drink_dispenser",
        "name": "밀크셰이크 & 루트비어 파운틴",
        "short_name": "셰이크·루트비어",
        "country": "US",
        "slot_type": "dispenser",
        "base_cook_time": 2.2,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (232, 76, 98),
        "accent_color": (86, 198, 248),
        "description": "산타모니카 바닐라 밀크셰이크와 루트비어 플로트를 뽑아내는 파운틴",
    },

    # --------------------------------------------------------------------------
    # 러시아 (RU) 조리 기구 4종 (모스크바·시베리아·코카서스)
    # --------------------------------------------------------------------------
    "ru_pirozhki_oven": {
        "id": "ru_pirozhki_oven",
        "station_id": "ru_pirozhki_oven",
        "name": "피로시키 & 하차푸리 화덕",
        "short_name": "피로시키 화덕",
        "country": "RU",
        "slot_type": "mold",
        "base_cook_time": 4.6,
        "base_burn_time": 9.5,
        "base_slots": 2,
        "base_servings": 1,
        "color": (168, 92, 54),
        "accent_color": (248, 204, 78),
        "description": "모스크바 고기 피로시키와 코카서스 치즈 보트빵 하차푸리를 굽는 화덕",
    },
    "ru_shashlik_grill": {
        "id": "ru_shashlik_grill",
        "station_id": "ru_shashlik_grill",
        "name": "시베리아 자작나무 샤슬릭 화로",
        "short_name": "샤슬릭 화로",
        "country": "RU",
        "slot_type": "grill",
        "base_cook_time": 4.8,
        "base_burn_time": 9.5,
        "base_slots": 2,
        "base_servings": 1,
        "color": (72, 118, 178),
        "accent_color": (238, 86, 62),
        "description": "시베리아 장작 샤슬릭을 구워 딜 사워크림 토핑을 얹는 방한 화로",
    },
    "ru_borscht_pot": {
        "id": "ru_borscht_pot",
        "station_id": "ru_borscht_pot",
        "name": "붉은광장 비트 보르시 보온솥",
        "short_name": "보르시 스튜솥",
        "country": "RU",
        "slot_type": "batch_pot",
        "base_cook_time": 5.2,
        "base_burn_time": 11.0,
        "base_slots": 1,
        "base_servings": 3,
        "color": (176, 38, 62),
        "accent_color": (245, 212, 112),
        "description": "영하의 추위를 녹이는 비트 소고기 보르시 스튜를 푹 끓여내는 대형 솥",
    },
    "ru_drink_dispenser": {
        "id": "ru_drink_dispenser",
        "station_id": "ru_drink_dispenser",
        "name": "황금 사모바르 홍차 & 크바스 통",
        "short_name": "사모바르·크바스",
        "country": "RU",
        "slot_type": "dispenser",
        "base_cook_time": 2.2,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (218, 168, 54),
        "accent_color": (212, 58, 52),
        "description": "황금 사모바르 홍차와 시원 구수한 호밀 크바스를 따라주는 디스펜서",
    },

    # --------------------------------------------------------------------------
    # 브라질 (BR) 조리 기구 4종 (리우데자네이루·상파울루·바이아)
    # --------------------------------------------------------------------------
    "br_pastel_press": {
        "id": "br_pastel_press",
        "station_id": "br_pastel_press",
        "name": "상파울루 파스텔 & 치즈볼 틀",
        "short_name": "파스텔·치즈볼",
        "country": "BR",
        "slot_type": "mold",
        "base_cook_time": 4.6,
        "base_burn_time": 9.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (46, 172, 86),
        "accent_color": (252, 214, 48),
        "description": "바삭한 상파울루 특대 파스텔과 쫀득한 팡지케이주 치즈볼을 굽는 기구",
    },
    "br_churrasco_grill": {
        "id": "br_churrasco_grill",
        "station_id": "br_churrasco_grill",
        "name": "리우 피카냐 슈하스코 그릴",
        "short_name": "슈하스코 그릴",
        "country": "BR",
        "slot_type": "grill",
        "base_cook_time": 4.9,
        "base_burn_time": 8.8,
        "base_slots": 2,
        "base_servings": 1,
        "color": (196, 78, 46),
        "accent_color": (52, 198, 96),
        "description": "피카냐 슈하스코 꼬치를 숯불에 구워 고소한 파로파 가루를 올리는 그릴",
    },
    "br_feijoada_pot": {
        "id": "br_feijoada_pot",
        "station_id": "br_feijoada_pot",
        "name": "바이아 페이조아다 스튜 가마솥",
        "short_name": "페이조아다 솥",
        "country": "BR",
        "slot_type": "batch_pot",
        "base_cook_time": 5.3,
        "base_burn_time": 10.8,
        "base_slots": 1,
        "base_servings": 3,
        "color": (86, 56, 48),
        "accent_color": (248, 196, 52),
        "description": "검은콩과 바비큐 고기를 푹 끓여 비나그레치 살사를 얹는 브라질 전통 솥",
    },
    "br_drink_dispenser": {
        "id": "br_drink_dispenser",
        "station_id": "br_drink_dispenser",
        "name": "코파카바나 아사이 & 과라나 서버",
        "short_name": "아사이·과라나",
        "country": "BR",
        "slot_type": "dispenser",
        "base_cook_time": 2.2,
        "base_burn_time": 999.0,
        "base_slots": 2,
        "base_servings": 1,
        "color": (112, 42, 148),
        "accent_color": (62, 212, 92),
        "description": "상큼한 코파카바나 아사이 스무디와 브라질 과라나 소다를 따르는 서버",
    },
}

STATIONS_CATALOG: Dict[str, AttrDict] = {}
for _sid, _sdata in _RAW_STATIONS_CATALOG.items():
    _all_station_recipes = [r["id"] for r in get_recipes_by_station(_sid, base_only=False)]
    _base_station_recipes = [r["id"] for r in get_recipes_by_station(_sid, base_only=True)]
    _station_toppings = [t["id"] for t in get_station_toppings(_sid)]

    _entry = AttrDict(_sdata)
    _entry["station_type"] = _sdata["slot_type"]
    _entry["type"] = _sdata["slot_type"]
    _entry["cook_time"] = _sdata["base_cook_time"]
    _entry["burn_time"] = _sdata["base_burn_time"]
    _entry["can_burn"] = _sdata["slot_type"] != "dispenser"
    _entry["recipes"] = _all_station_recipes
    _entry["recipe_ids"] = _all_station_recipes
    _entry["base_recipes"] = _base_station_recipes
    _entry["base_recipe_ids"] = _base_station_recipes
    _entry["toppings"] = _station_toppings
    _entry["available_toppings"] = _station_toppings
    STATIONS_CATALOG[_sid] = _entry


# ==============================================================================
# 월드 투어 4개국 챕터 데이터 (CHAPTERS)
# ==============================================================================
_RAW_CHAPTERS: Dict[str, Dict[str, Any]] = {
    "KR": {
        "id": "KR",
        "chapter_id": "KR",
        "order": 1,
        "country": "KR",
        "name": "서울 종로·광장 야시장",
        "title": "Chapter 1. 서울 종로·광장 야시장",
        "subtitle": "정겨운 주황빛 포장마차의 시작",
        "flag": "KR",
        "flag_emoji": "🇰🇷",
        "unlocked_by_default": True,
        "unlock_cost": 0,
        "required_prev_chapter": None,
        "recommended_character": "chef_kr",
        "default_stations": {
            "mold": "kr_bungeoppang",
            "grill": "kr_skewer_grill",
            "batch_pot": "kr_tteokbokki_pan",
            "dispenser": "kr_odeng_dispenser",
        },
        "stations": [
            "kr_bungeoppang",
            "kr_skewer_grill",
            "kr_tteokbokki_pan",
            "kr_odeng_dispenser",
        ],
        "base_target_gold": 4500,
        "daily_target_growth": 1500,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (2.5, 4.2),
        "base_patience": 30.0,
        "vip_chance": 0.12,
        "theme_color": (235, 92, 42),
        "accent_color": (255, 208, 68),
        "bg_style": "seoul_pocha",
        "description": "붕어빵, 직화 닭꼬치, 철판 떡볶이, 뜨끈한 어묵국물로 손님들의 추위를 녹여주세요!",
    },
    "JP": {
        "id": "JP",
        "chapter_id": "JP",
        "order": 2,
        "country": "JP",
        "name": "오사카 도톤보리 야타이",
        "title": "Chapter 2. 오사카 도톤보리 야타이",
        "subtitle": "화려한 강변 네온사인과 철판 불쇼",
        "flag": "JP",
        "flag_emoji": "🇯🇵",
        "unlocked_by_default": False,
        "unlock_cost": 15000,
        "required_prev_chapter": "KR",
        "recommended_character": "chef_jp",
        "default_stations": {
            "mold": "jp_takoyaki_pan",
            "grill": "jp_yakitori_grill",
            "batch_pot": "jp_yakisoba_pan",
            "dispenser": "jp_drink_dispenser",
        },
        "stations": [
            "jp_takoyaki_pan",
            "jp_yakitori_grill",
            "jp_yakisoba_pan",
            "jp_drink_dispenser",
        ],
        "base_target_gold": 22000,
        "daily_target_growth": 5500,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (4.2, 7.0),
        "base_patience": 28.0,
        "vip_chance": 0.15,
        "theme_color": (218, 56, 72),
        "accent_color": (255, 184, 52),
        "bg_style": "osaka_yatai",
        "description": "타코야키, 비장탄 야키토리, 철판 야키소바와 시원한 나마비루로 도톤보리를 사로잡으세요!",
    },
    "MX": {
        "id": "MX",
        "chapter_id": "MX",
        "order": 3,
        "country": "MX",
        "name": "멕시코시티 스트리트 피에스타",
        "title": "Chapter 3. 멕시코시티 스트리트 피에스타",
        "subtitle": "파펠 피카도 깃발 아래 정열의 타코 파티",
        "flag": "MX",
        "flag_emoji": "🇲🇽",
        "unlocked_by_default": False,
        "unlock_cost": 30000,
        "required_prev_chapter": "JP",
        "recommended_character": "chef_mx",
        "default_stations": {
            "mold": "mx_quesadilla_press",
            "grill": "mx_taco_grill",
            "batch_pot": "mx_nacho_fryer",
            "dispenser": "mx_drink_dispenser",
        },
        "stations": [
            "mx_quesadilla_press",
            "mx_taco_grill",
            "mx_nacho_fryer",
            "mx_drink_dispenser",
        ],
        "base_target_gold": 30000,
        "daily_target_growth": 6500,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (3.8, 6.5),
        "base_patience": 26.5,
        "vip_chance": 0.18,
        "theme_color": (38, 178, 96),
        "accent_color": (255, 212, 48),
        "bg_style": "mexico_fiesta",
        "description": "치즈 퀘사디야, 살사·과카몰리 타코, 칠리치즈 나초와 라임 마가리타의 흥겨운 축제!",
    },
    "TW": {
        "id": "TW",
        "chapter_id": "TW",
        "order": 4,
        "country": "TW",
        "name": "타이베이 스린 야시장",
        "title": "Chapter 4. 타이베이 스린 야시장",
        "subtitle": "붉은 홍등이 빛나는 미식 야시장의 정점",
        "flag": "TW",
        "flag_emoji": "🇹🇼",
        "unlocked_by_default": False,
        "unlock_cost": 45000,
        "required_prev_chapter": "MX",
        "recommended_character": "chef_tw",
        "default_stations": {
            "mold": "tw_scallion_pan",
            "grill": "tw_jipai_fryer",
            "batch_pot": "tw_cubesteak_pan",
            "dispenser": "tw_drink_dispenser",
        },
        "stations": [
            "tw_scallion_pan",
            "tw_jipai_fryer",
            "tw_cubesteak_pan",
            "tw_drink_dispenser",
        ],
        "base_target_gold": 38000,
        "daily_target_growth": 8000,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (3.5, 6.0),
        "base_patience": 25.0,
        "vip_chance": 0.22,
        "theme_color": (232, 68, 52),
        "accent_color": (48, 212, 204),
        "bg_style": "taipei_shilin",
        "description": "총좌빙, 대왕 마라 지파이, 불꽃 큐브스테이크, 흑당 버블티로 야시장 퀸에 등극하세요!",
    },
    "CN": {
        "id": "CN",
        "chapter_id": "CN",
        "order": 5,
        "country": "CN",
        "name": "중화 6대 권역 야시장",
        "title": "Chapter 5. 중화 6대 권역 야시장",
        "subtitle": "사천·광동·베이징·상하이·신장·동북 대륙의 불맛",
        "flag": "CN",
        "flag_emoji": "🇨🇳",
        "unlocked_by_default": False,
        "unlock_cost": 45000,
        "required_prev_chapter": "TW",
        "recommended_character": "chef_cn_sichuan",
        "default_stations": {
            "mold": "cn_dumpling_pan",
            "grill": "cn_lamb_grill",
            "batch_pot": "cn_mala_wok",
            "dispenser": "cn_drink_dispenser",
        },
        "stations": [
            "cn_dumpling_pan",
            "cn_lamb_grill",
            "cn_mala_wok",
            "cn_drink_dispenser",
        ],
        "base_target_gold": 40000,
        "daily_target_growth": 8000,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (3.5, 5.8),
        "base_patience": 25.0,
        "vip_chance": 0.22,
        "theme_color": (218, 46, 42),
        "accent_color": (255, 208, 58),
        "bg_style": "china_nightmarket",
        "description": "성젠바오·에그와플, 실크로드 양꼬치, 사천 마라탕·꿔바로우, 홍콩 밀크티가 펼쳐지는 대륙의 밤!",
    },
    "IN": {
        "id": "IN",
        "chapter_id": "IN",
        "order": 6,
        "country": "IN",
        "name": "인도 6대 스파이스 바자르",
        "title": "Chapter 6. 인도 6대 스파이스 바자르",
        "subtitle": "델리·뭄바이·첸나이·콜카타·펀자브·하이데라바드 향신료 축제",
        "flag": "IN",
        "flag_emoji": "🇮🇳",
        "unlocked_by_default": False,
        "unlock_cost": 50000,
        "required_prev_chapter": "CN",
        "recommended_character": "chef_in_delhi",
        "default_stations": {
            "mold": "in_naan_tandoor",
            "grill": "in_tikka_grill",
            "batch_pot": "in_curry_pot",
            "dispenser": "in_drink_dispenser",
        },
        "stations": [
            "in_naan_tandoor",
            "in_tikka_grill",
            "in_curry_pot",
            "in_drink_dispenser",
        ],
        "base_target_gold": 43000,
        "daily_target_growth": 8500,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (3.4, 5.6),
        "base_patience": 24.5,
        "vip_chance": 0.24,
        "theme_color": (242, 138, 36),
        "accent_color": (196, 62, 168),
        "bg_style": "india_bazaar",
        "description": "화덕 갈릭난·사모사, 탄두리 치킨 티카, 버터치킨·비리야니, 망고 라씨로 바자르를 제패하세요!",
    },
    "US": {
        "id": "US",
        "chapter_id": "US",
        "order": 7,
        "country": "US",
        "name": "아메리칸 5대 푸드트럭 파크",
        "title": "Chapter 7. 아메리칸 5대 푸드트럭 파크",
        "subtitle": "뉴욕·텍사스·캘리포니아·뉴올리언스·필라델피아 올스타",
        "flag": "US",
        "flag_emoji": "🇺🇸",
        "unlocked_by_default": False,
        "unlock_cost": 55000,
        "required_prev_chapter": "IN",
        "recommended_character": "chef_us_ny",
        "default_stations": {
            "mold": "us_hotdog_roller",
            "grill": "us_smash_grill",
            "batch_pot": "us_fryer_pot",
            "dispenser": "us_drink_dispenser",
        },
        "stations": [
            "us_hotdog_roller",
            "us_smash_grill",
            "us_fryer_pot",
            "us_drink_dispenser",
        ],
        "base_target_gold": 46000,
        "daily_target_growth": 9000,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (3.3, 5.5),
        "base_patience": 24.5,
        "vip_chance": 0.25,
        "theme_color": (56, 112, 218),
        "accent_color": (238, 68, 58),
        "bg_style": "usa_foodtruck",
        "description": "뉴욕 핫도그·베녜, 스매시 치즈버거·텍사스 브리스킷, 버팔로윙·맥앤치즈와 밀크셰이크!",
    },
    "RU": {
        "id": "RU",
        "chapter_id": "RU",
        "order": 8,
        "country": "RU",
        "name": "모스크바 & 시베리아 설원 화로",
        "title": "Chapter 8. 모스크바 & 시베리아 설원 화로",
        "subtitle": "붉은광장·시베리아·코카서스 영하의 장작불 야시장",
        "flag": "RU",
        "flag_emoji": "🇷🇺",
        "unlocked_by_default": False,
        "unlock_cost": 60000,
        "required_prev_chapter": "US",
        "recommended_character": "chef_ru_siberia",
        "default_stations": {
            "mold": "ru_pirozhki_oven",
            "grill": "ru_shashlik_grill",
            "batch_pot": "ru_borscht_pot",
            "dispenser": "ru_drink_dispenser",
        },
        "stations": [
            "ru_pirozhki_oven",
            "ru_shashlik_grill",
            "ru_borscht_pot",
            "ru_drink_dispenser",
        ],
        "base_target_gold": 48000,
        "daily_target_growth": 9500,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (3.3, 5.4),
        "base_patience": 24.0,
        "vip_chance": 0.25,
        "theme_color": (72, 128, 208),
        "accent_color": (255, 204, 68),
        "bg_style": "russia_winter",
        "description": "피로시키·하차푸리, 시베리아 샤슬릭 꼬치, 뜨끈한 비트 보르시와 황금 사모바르 홍차!",
    },
    "BR": {
        "id": "BR",
        "chapter_id": "BR",
        "order": 9,
        "country": "BR",
        "name": "리우 코파카바나 카니발 포차",
        "title": "Chapter 9. 리우 코파카바나 카니발 포차",
        "subtitle": "리우·상파울루·바이아 삼바 리듬과 슈하스코 불꽃",
        "flag": "BR",
        "flag_emoji": "🇧🇷",
        "unlocked_by_default": False,
        "unlock_cost": 65000,
        "required_prev_chapter": "RU",
        "recommended_character": "chef_br_rio",
        "default_stations": {
            "mold": "br_pastel_press",
            "grill": "br_churrasco_grill",
            "batch_pot": "br_feijoada_pot",
            "dispenser": "br_drink_dispenser",
        },
        "stations": [
            "br_pastel_press",
            "br_churrasco_grill",
            "br_feijoada_pot",
            "br_drink_dispenser",
        ],
        "base_target_gold": 50000,
        "daily_target_growth": 10000,
        "star_thresholds": (1.0, 1.30, 1.65),
        "customer_spawn_interval": (3.2, 5.2),
        "base_patience": 24.0,
        "vip_chance": 0.26,
        "theme_color": (42, 184, 86),
        "accent_color": (252, 214, 42),
        "bg_style": "brazil_carnival",
        "description": "상파울루 특대 파스텔·치즈볼, 피카냐 슈하스코, 페이조아다 스튜와 아사이볼 파티!",
    },
}

CHAPTERS: Dict[str, AttrDict] = {}
for _chid, _chdata in _RAW_CHAPTERS.items():
    _wrapped_ch = AttrDict(_chdata)
    _wrapped_ch["default_stations"] = AttrDict(_chdata["default_stations"])
    _wrapped_ch["station_loadout"] = AttrDict(_chdata["default_stations"])
    # 챕터에 속한 전체 레시피 목록
    _ch_recipes: List[str] = []
    for _st_id in _chdata["stations"]:
        _ch_recipes.extend(STATIONS_CATALOG[_st_id]["recipes"])
    _wrapped_ch["recipes"] = _ch_recipes
    CHAPTERS[_chid] = _wrapped_ch


# ==============================================================================
# 챕터 & 조리 기구 카탈로그 헬퍼 함수
# ==============================================================================
def get_chapter(chapter_id: str) -> AttrDict:
    """챕터 ID('KR', 'JP', 'MX', 'TW' 등)로 챕터 데이터를 반환한다."""
    return CHAPTERS.get(str(chapter_id or "KR").upper(), CHAPTERS["KR"])


def get_station_meta(station_id: str) -> Optional[AttrDict]:
    """조리 기구 ID로 STATIONS_CATALOG 메타데이터를 반환한다."""
    return STATIONS_CATALOG.get(station_id)


def get_stations_by_slot(slot_type: str) -> List[AttrDict]:
    """슬롯 타입('mold', 'grill', 'batch_pot', 'dispenser')에 해당하는 4개국 기구 리스트를 반환한다."""
    return [
        st for st in STATIONS_CATALOG.values() if st["slot_type"] == slot_type
    ]


def get_stations_by_country(country: str) -> Dict[str, AttrDict]:
    """특정 국가의 4슬롯 조리 기구 딕셔너리({slot_type: station_meta})를 반환한다."""
    c_upper = country.upper()
    return {
        st["slot_type"]: st
        for st in STATIONS_CATALOG.values()
        if st["country"] == c_upper
    }


def calculate_target_gold(
    chapter_id: str,
    day: int = 1,
    mode: str = "WORLD_TOUR",
) -> int:
    """
    챕터와 일차(Day)에 따른 일일 목표 매출액(원)을 계산하여 반환한다.
    글로벌 무한 모드(GLOBAL_ENDLESS)의 경우 일차에 따라 점진적으로 상승한다.
    """
    day = max(1, int(day))
    if mode == "GLOBAL_ENDLESS":
        base = 25000
        growth = 6000
        return base + (day - 1) * growth

    ch = get_chapter(chapter_id)
    base = int(ch["base_target_gold"])
    growth = int(ch["daily_target_growth"])
    return base + (day - 1) * growth


def calculate_stars(
    earned_gold: int,
    target_gold: int,
    chapter_id: Optional[str] = None,
) -> int:
    """달성 매출액과 목표 매출액을 챕터별 star_thresholds 기준으로 비교하여 획득 별 개수(0~3)를 반환한다."""
    if target_gold <= 0:
        return 3
    ch = get_chapter(chapter_id) if chapter_id else CHAPTERS.get("KR")
    thresholds = ch.get("star_thresholds", (1.0, 1.30, 1.65)) if ch else (1.0, 1.30, 1.65)
    t1 = float(thresholds[0]) if len(thresholds) > 0 else 1.00
    t2 = float(thresholds[1]) if len(thresholds) > 1 else 1.30
    t3 = float(thresholds[2]) if len(thresholds) > 2 else 1.65
    ratio = earned_gold / float(target_gold)
    if ratio >= t3:
        return 3
    if ratio >= t2:
        return 2
    if ratio >= t1:
        return 1
    return 0
