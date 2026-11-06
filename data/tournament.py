"""
32강 월드 포차 그랑프리(TOURNAMENT_32_ROSTER) 땅덩어리 비례 9개국·32인 지역별 마스터 로스터 및
토너먼트 매치 생성 모듈.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional
from data.characters import AttrDict, CHARACTER_ORDER, CHARACTERS


COUNTRY_FLAGS: Dict[str, str] = {
    "KR": "🇰🇷",
    "TW": "🇹🇼",
    "JP": "🇯🇵",
    "MX": "🇲🇽",
    "BR": "🇧🇷",
    "RU": "🇷🇺",
    "US": "🇺🇸",
    "IN": "🇮🇳",
    "CN": "🇨🇳",
}

#國家별 요약 정보 (토너먼트 & 도감 표시용)
CANDIDATE_COUNTRIES: Dict[str, AttrDict] = {
    "CN": AttrDict({
        "id": "CN", "code": "CN", "name": "중국 (6대 미식권 · 6인)", "subtitle": "사천·광동·베이징·상하이·신장·동북",
        "flag": "🇨🇳", "theme_color": (218, 46, 42), "accent_color": (255, 208, 58),
        "master_chef_id": "chef_cn_sichuan", "master_name": "웨이 외 5인 (중국 6대 지역 대표)",
        "stations": {
            "mold": {"id": "cn_dumpling_pan", "name": "성젠바오·에그와플 틀", "recipes": ["shengjianbao_plain", "egg_waffle_plain"]},
            "grill": {"id": "cn_lamb_grill", "name": "실크로드 양꼬치 화로", "recipes": ["lamb_skewer_plain", "lamb_skewer_cumin", "lamb_skewer_mala"]},
            "batch_pot": {"id": "cn_mala_wok", "name": "사천 마라탕·꿔바로우 웍", "recipes": ["malatang_plain", "guobarou_sweet"]},
            "dispenser": {"id": "cn_drink_dispenser", "name": "산사자차·홍콩 밀크티", "recipes": ["plum_tea", "hk_milktea"]},
        },
    }),
    "IN": AttrDict({
        "id": "IN", "code": "IN", "name": "인도 (6대 아대륙권 · 6인)", "subtitle": "델리·뭄바이·첸나이·콜카타·펀자브·하이데라바드",
        "flag": "🇮🇳", "theme_color": (242, 138, 36), "accent_color": (196, 62, 168),
        "master_chef_id": "chef_in_delhi", "master_name": "라지 외 5인 (인도 6대 지역 대표)",
        "stations": {
            "mold": {"id": "in_naan_tandoor", "name": "화덕 갈릭난·사모사", "recipes": ["garlic_naan", "golden_samosa"]},
            "grill": {"id": "in_tikka_grill", "name": "올드델리 탄두리 그릴", "recipes": ["tandoori_tikka", "tikka_mint", "tikka_masala"]},
            "batch_pot": {"id": "in_curry_pot", "name": "버터치킨·황금 비리야니 솥", "recipes": ["butter_chicken", "dum_biryani"]},
            "dispenser": {"id": "in_drink_dispenser", "name": "망고 라씨·마살라 차이", "recipes": ["mango_lassi", "masala_chai"]},
        },
    }),
    "US": AttrDict({
        "id": "US", "code": "US", "name": "미국 (5대 권역 · 5인)", "subtitle": "뉴욕·텍사스·캘리포니아·뉴올리언스·필라델피아",
        "flag": "🇺🇸", "theme_color": (56, 112, 218), "accent_color": (238, 68, 58),
        "master_chef_id": "chef_us_ny", "master_name": "잭슨 외 4인 (미국 5대 지역 대표)",
        "stations": {
            "mold": {"id": "us_hotdog_roller", "name": "뉴욕 핫도그·베녜 틀", "recipes": ["ny_hotdog", "nola_beignet"]},
            "grill": {"id": "us_smash_grill", "name": "스매시버거·텍사스 BBQ", "recipes": ["smash_burger", "bacon_burger", "texas_brisket"]},
            "batch_pot": {"id": "us_fryer_pot", "name": "버팔로 윙·맥앤치즈 팬", "recipes": ["buffalo_wings", "loaded_mac_cheese"]},
            "dispenser": {"id": "us_drink_dispenser", "name": "밀크셰이크·루트비어", "recipes": ["cali_milkshake", "root_beer_float"]},
        },
    }),
    "RU": AttrDict({
        "id": "RU", "code": "RU", "name": "러시아 (3대 권역 · 3인)", "subtitle": "모스크바·시베리아·코카서스",
        "flag": "🇷🇺", "theme_color": (72, 128, 208), "accent_color": (255, 204, 68),
        "master_chef_id": "chef_ru_siberia", "master_name": "보리스 외 2인 (러시아 3대 지역 대표)",
        "stations": {
            "mold": {"id": "ru_pirozhki_oven", "name": "피로시키·하차푸리 화덕", "recipes": ["meat_pirozhki", "cheese_khachapuri"]},
            "grill": {"id": "ru_shashlik_grill", "name": "시베리아 샤슬릭 화로", "recipes": ["siberia_shashlik", "shashlik_sourcream"]},
            "batch_pot": {"id": "ru_borscht_pot", "name": "붉은광장 비트 보르시 솥", "recipes": ["hot_borscht", "borscht_supreme"]},
            "dispenser": {"id": "ru_drink_dispenser", "name": "황금 사모바르 홍차·크바스", "recipes": ["samovar_tea", "russian_kvass"]},
        },
    }),
    "BR": AttrDict({
        "id": "BR", "code": "BR", "name": "브라질 (3대 권역 · 3인)", "subtitle": "리우데자네이루·상파울루·바이아",
        "flag": "🇧🇷", "theme_color": (42, 184, 86), "accent_color": (252, 214, 42),
        "master_chef_id": "chef_br_rio", "master_name": "카를로스 외 2인 (브라질 3대 지역 대표)",
        "stations": {
            "mold": {"id": "br_pastel_press", "name": "상파울루 파스텔·치즈볼", "recipes": ["crispy_pastel", "pao_de_queijo"]},
            "grill": {"id": "br_churrasco_grill", "name": "리우 피카냐 슈하스코 그릴", "recipes": ["picanha_skewer", "picanha_farofa"]},
            "batch_pot": {"id": "br_feijoada_pot", "name": "바이아 페이조아다 가마솥", "recipes": ["bahia_feijoada", "feijoada_salsa"]},
            "dispenser": {"id": "br_drink_dispenser", "name": "코파카바나 아사이·과라나", "recipes": ["acai_smoothie", "guarana_soda"]},
        },
    }),
    "MX": AttrDict({
        "id": "MX", "code": "MX", "name": "멕시코 (3대 권역 · 3인)", "subtitle": "멕시코시티·오악사카·과달라하라",
        "flag": "🇲🇽", "theme_color": (38, 178, 96), "accent_color": (255, 212, 48),
        "master_chef_id": "chef_mx", "master_name": "디에고 외 2인 (멕시코 3대 지역 대표)",
        "stations": {
            "mold": {"id": "mx_quesadilla_press", "name": "퀘사디야 코말 프레스", "recipes": ["quesadilla_cheese", "quesadilla_chicken"]},
            "grill": {"id": "mx_taco_grill", "name": "카르니타스 타코 그릴", "recipes": ["taco_plain", "taco_salsa", "taco_guacamole"]},
            "batch_pot": {"id": "mx_nacho_fryer", "name": "피에스타 나초 프라이어", "recipes": ["nacho_plain", "nacho_cheese"]},
            "dispenser": {"id": "mx_drink_dispenser", "name": "마가리타·멕시칸 콜라", "recipes": ["lime_margarita", "mexican_cola"]},
        },
    }),
    "JP": AttrDict({
        "id": "JP", "code": "JP", "name": "일본 (3대 권역 · 3인)", "subtitle": "오사카·도쿄 아사쿠사·후쿠오카 나카스",
        "flag": "🇯🇵", "theme_color": (218, 56, 72), "accent_color": (255, 184, 52),
        "master_chef_id": "chef_jp", "master_name": "켄지 외 2인 (일본 3대 지역 대표)",
        "stations": {
            "mold": {"id": "jp_takoyaki_pan", "name": "도톤보리 타코야키 판", "recipes": ["takoyaki_plain", "takoyaki_mayo"]},
            "grill": {"id": "jp_yakitori_grill", "name": "비장탄 야키토리 화로", "recipes": ["yakitori_plain", "yakitori_tare"]},
            "batch_pot": {"id": "jp_yakisoba_pan", "name": "야타이 야키소바 철판", "recipes": ["yakisoba_plain", "yakisoba_egg"]},
            "dispenser": {"id": "jp_drink_dispenser", "name": "나마비루·라무네 서버", "recipes": ["draft_beer", "ramune_soda"]},
        },
    }),
    "TW": AttrDict({
        "id": "TW", "code": "TW", "name": "대만 (남·북 야시장 · 2인)", "subtitle": "타이베이 스린·가오슝 리우허",
        "flag": "🇹🇼", "theme_color": (232, 68, 52), "accent_color": (48, 212, 204),
        "master_chef_id": "chef_tw", "master_name": "메이링·아성 (대만 남북 대표)",
        "stations": {
            "mold": {"id": "tw_scallion_pan", "name": "스린 총좌빙 무쇠팬", "recipes": ["congzuobing_plain", "congzuobing_egg"]},
            "grill": {"id": "tw_jipai_fryer", "name": "대왕 지파이 튀김기", "recipes": ["jipai_plain", "jipai_spicy"]},
            "batch_pot": {"id": "tw_cubesteak_pan", "name": "불꽃 큐브스테이크 철판", "recipes": ["cubesteak_plain", "cubesteak_garlic"]},
            "dispenser": {"id": "tw_drink_dispenser", "name": "흑당 버블티·망고스무디", "recipes": ["boba_milktea", "mango_smoothie"]},
        },
    }),
}

TOURNAMENT_TIERS: Dict[int, AttrDict] = {
    1: AttrDict({
        "tier": 1,
        "round_name": "32강 (R32)",
        "label": "지역 예선 강호",
        "cook_interval_sec": 4.0,
        "mistake_rate": 0.10,
        "skill_cooldown": 45.0,
        "expected_gold_per_min": 14000,
        "match_duration": 75,
    }),
    2: AttrDict({
        "tier": 2,
        "round_name": "16강 (R16)",
        "label": "권역 베테랑 마스터",
        "cook_interval_sec": 3.1,
        "mistake_rate": 0.06,
        "skill_cooldown": 38.0,
        "expected_gold_per_min": 18500,
        "match_duration": 80,
    }),
    3: AttrDict({
        "tier": 3,
        "round_name": "8강 (QF)",
        "label": "대륙 대표 챔피언",
        "cook_interval_sec": 2.5,
        "mistake_rate": 0.03,
        "skill_cooldown": 32.0,
        "expected_gold_per_min": 23000,
        "match_duration": 90,
    }),
    4: AttrDict({
        "tier": 4,
        "round_name": "4강 (SF)",
        "label": "월드 투어 사천왕",
        "cook_interval_sec": 2.1,
        "mistake_rate": 0.01,
        "skill_cooldown": 28.0,
        "expected_gold_per_min": 28000,
        "match_duration": 90,
    }),
    5: AttrDict({
        "tier": 5,
        "round_name": "결승 (FINAL)",
        "label": "월드 야시장 최강자",
        "cook_interval_sec": 1.8,
        "mistake_rate": 0.0,
        "skill_cooldown": 24.0,
        "expected_gold_per_min": 33000,
        "match_duration": 90,
    }),
}

# 32인 캐릭터별 시드 티어 배정
_TIER_BY_CHEF: Dict[str, int] = {
    "chef_kr": 5,
    "chef_tw": 5,
    "chef_cn_sichuan": 5,
    "chef_in_delhi": 5,
    "chef_mx": 4,
    "chef_jp": 4,
    "chef_us_ny": 4,
    "chef_us_texas": 4,
    "chef_ru_siberia": 4,
    "chef_br_rio": 4,
    "chef_cn_beijing": 3,
    "chef_cn_canton": 3,
    "chef_in_mumbai": 3,
    "chef_in_hyderabad": 3,
    "chef_us_cali": 3,
    "chef_us_philly": 3,
    "chef_ru_moscow": 3,
    "chef_jp_tokyo": 3,
    "chef_cn_shanghai": 2,
    "chef_cn_xinjiang": 2,
    "chef_in_chennai": 2,
    "chef_in_punjab": 2,
    "chef_us_nola": 2,
    "chef_mx_oaxaca": 2,
    "chef_br_bahia": 2,
    "chef_tw_kaohsiung": 2,
    "chef_cn_dongbei": 1,
    "chef_in_kolkata": 1,
    "chef_mx_jalisco": 1,
    "chef_jp_fukuoka": 1,
    "chef_br_saopaulo": 1,
    "chef_ru_caucasus": 1,
}

TOURNAMENT_32_ROSTER: Dict[str, AttrDict] = {}
for _cid in CHARACTER_ORDER:
    _ch = CHARACTERS[_cid]
    _tier = _TIER_BY_CHEF.get(_cid, 2)
    TOURNAMENT_32_ROSTER[_cid] = AttrDict({
        "id": _cid,
        "name": _ch["name"],
        "country": _ch["country"],
        "region": _ch["region"],
        "region_name": _ch["region"],
        "flag": COUNTRY_FLAGS.get(_ch["country"], "🏮"),
        "title": _ch["title"],
        "signature": f"{_ch['region']} · {_ch['skill_name']}",
        "style": _ch["specialty_tag"],
        "tier": _tier,
    })


def get_tournament_chef(chef_id: str) -> Optional[AttrDict]:
    return TOURNAMENT_32_ROSTER.get(chef_id)


def get_candidate_country(country_code: str) -> Optional[AttrDict]:
    return CANDIDATE_COUNTRIES.get(country_code.upper())


def generate_tournament_opponents(player_char_id: str = "chef_kr", seed: Optional[int] = None) -> List[AttrDict]:
    """플레이어가 32강 -> 16강 -> 8강 -> 4강 -> 결승에서 맞붙을 5명의 지역 마스터 리스트를 반환한다."""
    rng = random.Random(seed)
    opponents: List[AttrDict] = []
    for tier in (1, 2, 3, 4, 5):
        pool = [
            c for c in TOURNAMENT_32_ROSTER.values()
            if c["tier"] == tier and c["id"] != player_char_id
        ]
        if not pool:
            pool = [c for c in TOURNAMENT_32_ROSTER.values() if c["id"] != player_char_id]
        opponents.append(rng.choice(pool))
    return opponents
