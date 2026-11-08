"""
전세계 길거리 음식 포차 타이쿤 (World Street Food Pocha Tycoon)
스토리 모드 단계별 해금 규칙(STORY_PROGRESSION), 감성 컷신 및 대사 스크립트(STORY_DIALOGUES),
32강 월드 포차 그랑프리 토너먼트 드라마(TOURNAMENT_DRAMA) 및 조회 헬퍼 모듈.

[전체 스토리 아크 요약]
- 프롤로그: 도심 프랜차이즈 공세와 임대료 폭등으로 10년지기 식당의 셔터를 내린 주인공 '김포차'.
  전 재산을 털어 고물상에서 구한 '중고 붕어빵 주물 틀 1개'를 낡은 리어카에 얹고 종로 뒷골목 겨울밤에 선다.
- 제1막 (한국 KR - 종로·광장 야시장의 부활):
  - Day 1 [붕어빵 틀]: 얼어붙은 손으로 구워낸 첫 붕어빵. 하굣길 단골 학생의 응원으로 다시 일어서다.
  - Day 2 [어묵·식혜 디스펜서 & 알전구]: 칼바람 속 손님들의 언 손을 녹여줄 뜨끈한 어묵국물과 살얼음 식혜 추가.
  - Day 3 [직화 닭꼬치 그릴 & 조립 트레이]: 퇴근길 직장인들의 발길을 붙잡는 숯불 닭꼬치와 특제 소스·파채 토핑 해금.
  - Day 4 [철판 떡볶이 대량 조리 팬 & 마스터 스킬]: 골목 전체에 퍼지는 매콤한 철판 떡볶이와 '포차 이모님의 인심' 각성.
  - Day 5 [종로 최종 테스트 & VIP 맛집 유튜버]: 구독자 200만 맛집 유튜버 '먹방킹'의 극찬 영상 폭발!
    전 세계 32개국 스트리트 셰프가 격돌하는 '월드 포차 그랑프리(World Pocha Grand Prix)' 공식 초청장 도착.
- 제2막 (일본 JP - 오사카 도톤보리 야타이 원정):
  - 타코야키 판 & 나마비루 서버(Day 1) -> 비장탄 야키토리 화로(Day 2) -> 야타이 야키소바 철판 & 장인 '켄지'와의 불꽃 승부(Day 3~5).
- 제3막 (멕시코 MX - 멕시코시티 스트리트 피에스타 원정):
  - 퀘사디야 프레스 & 마가리타(Day 1) -> 카르니타스 타코 그릴(Day 2) -> 피에스타 나초 프라이어 & '디에고'와의 살사 대결(Day 3~5).
- 제4막 (대만 TW - 타이베이 스린 야시장 & 월드 포차 그랑프리 결승):
  - 스린 총좌빙 & 흑당 버블티(Day 1) -> 대왕 지파이 튀김기(Day 2) -> 불꽃 큐브스테이크 철판 & 스린 야시장 퀸 '메이링'과의 최종 결전(Day 3~5).
- 엔딩: 32강 월드 포차 그랑프리 최종 우승! 중고 붕어빵 틀 1개로 시작해 세계인의 밤을 위로하는 전설의 월드 포차 마스터 등극.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from data.characters import AttrDict
from data.chapters import CHAPTER_ORDER, SLOT_TYPES
from data.upgrades import INTERIOR_UPGRADE_ORDER, normalize_station_upgrade_key

# ==============================================================================
# 스토리 일러스트 에셋 경로 상수
# ==============================================================================
STORY_ILLUSTRATIONS: Dict[str, str] = {
    "prologue": "assets/story/prologue_bankrupt_cart.png",
    "prologue_bankrupt_cart": "assets/story/prologue_bankrupt_cart.png",
    "act1_revival": "assets/story/act1_pocha_revival.png",
    "act1_pocha_revival": "assets/story/act1_pocha_revival.png",
    "act2_departure": "assets/story/act2_world_departure.png",
    "act2_world_departure": "assets/story/act2_world_departure.png",
    "ending": "assets/story/ending_world_champion.png",
    "ending_world_champion": "assets/story/ending_world_champion.png",
}


# ==============================================================================
# 1. 스토리 모드 단계별 해금 규칙 (STORY_PROGRESSION)
# ==============================================================================
# 슬롯 식별자 설명:
# - "mold": 몰드 구이 기구 (붕어빵 틀 / 타코야키 판 / 퀘사디야 프레스 / 총좌빙 팬)
# - "dispenser": 음료 디스펜서 (어묵·식혜 / 생맥주·라무네 / 마가리타·콜라 / 버블티·망고스무디)
# - "grill": 직화 그릴·튀김기 (닭꼬치 그릴 / 야키토리 화로 / 타코 그릴 / 대왕 지파이 튀김기)
# - "batch_pot": 대량 조리 팬 (철판 떡볶이 / 야키소바 철판 / 나초 프라이어 / 큐브스테이크 철판)
# - "tray": 중앙 조립 트레이 & 토핑 컨테이너
# - "skill": 포차 마스터 액티브 스킬 ([SPACE] 발동)
_RAW_STORY_PROGRESSION: Dict[str, Dict[int, Dict[str, Any]]] = {
    # --------------------------------------------------------------------------
    # 제1막: 한국 (KR) - 서울 종로·광장 야시장 (Day 1 ~ Day 5 단계적 리어카 부활기)
    # --------------------------------------------------------------------------
    "KR": {
        1: {
            "chapter_id": "KR",
            "day": 1,
            "title": "Day 1. 중고 붕어빵 틀 하나로 시작하는 겨울밤",
            "subtitle": "붕어빵 틀(Mold) 단독 영업 · 기본기에 집중하세요!",
            "unlocked_slots": ["mold"],
            "cooking_slots": ["mold"],
            "tray_unlocked": False,
            "toppings_unlocked": False,
            "skill_unlocked": False,
            "shop_unlocked": False,
            "max_station_levels": {
                "mold": 0,
                "dispenser": 0,
                "grill": 0,
                "batch_pot": 0,
                "tray": 0,
            },
            "unlocked_interiors": [],
            "special_vip": False,
            "unlock_banner": "[Day 1 해금] 황금 붕어빵 틀 (팥 붕어빵 · 슈크림 붕어빵)",
            "gameplay_tip": "반죽을 붓고 초록색(READY) 게이지가 되었을 때 꺼내 손님에게 서빙하세요!",
        },
        2: {
            "chapter_id": "KR",
            "day": 2,
            "title": "Day 2. 언 손을 녹이는 뜨끈한 어묵국물 한 컵",
            "subtitle": "어묵·식혜 디스펜서 오픈 & 포차 상점 첫 개방!",
            "unlocked_slots": ["mold", "dispenser"],
            "cooking_slots": ["mold", "dispenser"],
            "tray_unlocked": False,
            "toppings_unlocked": False,
            "skill_unlocked": False,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 1,
                "dispenser": 1,
                "grill": 0,
                "batch_pot": 0,
                "tray": 0,
            },
            "unlocked_interiors": ["awning_lights"],
            "special_vip": False,
            "unlock_banner": "[Day 2 해금] 어묵국물·식혜 디스펜서 + 몰드 Lv.1 개조 + 포차 천막 & 알전구",
            "gameplay_tip": "디스펜서 음료는 절대 타지 않습니다! 미리 채워두고 빠르게 서빙해 콤보를 이어가세요.",
        },
        3: {
            "chapter_id": "KR",
            "day": 3,
            "title": "Day 3. 퇴근길 발걸음을 붙잡는 숯불 닭꼬치 연기",
            "subtitle": "직화 닭꼬치 그릴 + 중앙 조립 트레이 & 토핑 오픈!",
            "unlocked_slots": ["mold", "dispenser", "grill", "tray"],
            "cooking_slots": ["mold", "grill", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": False,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 2,
                "dispenser": 2,
                "grill": 1,
                "batch_pot": 0,
                "tray": 1,
            },
            "unlocked_interiors": ["awning_lights", "plastic_chairs"],
            "special_vip": False,
            "unlock_banner": "[Day 3 해금] 직화 닭꼬치 그릴 + 조립 트레이 & 소스/파채 토핑 + 플라스틱 의자",
            "gameplay_tip": "구운 소금구이 닭꼬치를 중앙 트레이에 올린 뒤 매운양념·데리야키·파채 토핑을 조합하세요!",
        },
        4: {
            "chapter_id": "KR",
            "day": 4,
            "title": "Day 4. 골목을 물들이는 빨간 철판 떡볶이와 이모님의 인심",
            "subtitle": "철판 떡볶이 대량 조리 팬 + 마스터 스킬 [SPACE] 해금!",
            "unlocked_slots": ["mold", "dispenser", "grill", "tray", "batch_pot", "skill"],
            "cooking_slots": ["mold", "grill", "batch_pot", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 2,
                "dispenser": 2,
                "grill": 2,
                "batch_pot": 1,
                "tray": 2,
            },
            "unlocked_interiors": ["awning_lights", "plastic_chairs", "neon_signboard"],
            "special_vip": False,
            "unlock_banner": "[Day 4 해금] 포차 철판 떡볶이 팬(3인분 대량조리) + 액티브 스킬 [SPACE] + 네온 입간판",
            "gameplay_tip": "떡볶이는 한 번 조리하면 3인분이 완성됩니다! 위기 순간엔 [SPACE]로 마스터 스킬을 발동하세요.",
        },
        5: {
            "chapter_id": "KR",
            "day": 5,
            "title": "Day 5. 종로 최종 테스트: VIP 맛집 유튜버의 기습 방문!",
            "subtitle": "모든 기구 Lv.3 및 감성 라디오 해금 · 클리어 시 월드 투어 개막!",
            "unlocked_slots": ["mold", "dispenser", "grill", "tray", "batch_pot", "skill"],
            "cooking_slots": ["mold", "grill", "batch_pot", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 3,
                "batch_pot": 3,
                "tray": 3,
            },
            "unlocked_interiors": [
                "awning_lights",
                "plastic_chairs",
                "neon_signboard",
                "retro_radio",
            ],
            "special_vip": True,
            "vip_guest_name": "맛집 유튜버 먹방킹",
            "unlock_banner": "[Day 5 최종전] 전 기구 Lv.3 상한 해제 + 7080 감성 라디오 + VIP 유튜버 특별 심사",
            "gameplay_tip": "왕관 표시가 붙은 VIP 손님은 인내심이 짧은 대신 막대한 팁과 월드 투어 초청장을 안겨줍니다!",
        },
    },

    # --------------------------------------------------------------------------
    # 제2막: 일본 (JP) - 오사카 도톤보리 야타이 (현지 기구 적응 및 장인 켄지 라이벌전)
    # --------------------------------------------------------------------------
    "JP": {
        1: {
            "chapter_id": "JP",
            "day": 1,
            "title": "JP Day 1. 도톤보리 강변에 울려 퍼진 첫 타코야키 볼",
            "subtitle": "타코야키 판(Mold) + 생맥주·라무네 서버(Dispenser) 현지 적응전",
            "unlocked_slots": ["mold", "dispenser", "tray", "skill"],
            "cooking_slots": ["mold", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 2,
                "batch_pot": 2,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": "[오사카 Day 1] 도톤보리 타코야키 판 & 나마비루·라무네 서버 오픈!",
            "gameplay_tip": "오리지널 타코야키와 네기마요 타코야키를 구분해 굽고 시원한 생맥주를 곁들이세요!",
        },
        2: {
            "chapter_id": "JP",
            "day": 2,
            "title": "JP Day 2. 비장탄 숯불 연기와 비전 타레 소스의 향연",
            "subtitle": "비장탄 야키토리 화로(Grill) 추가 오픈!",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "skill"],
            "cooking_slots": ["mold", "grill", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 3,
                "batch_pot": 2,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": "[오사카 Day 2] 비장탄 야키토리 화로 & 비전 타레소스 토핑 오픈!",
            "gameplay_tip": "시오 야키토리를 트레이에 올리고 비전 타레소스를 발라 타레 야키토리를 완성하세요!",
        },
        3: {
            "chapter_id": "JP",
            "day": 3,
            "title": "JP Day 3. 도톤보리 야타이 장인 '켄지'와의 정면 승부!",
            "subtitle": "야타이 야키소바 철판(Batch Pot) 풀세트 개방 & 8강 라이벌 매치",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "batch_pot", "skill"],
            "cooking_slots": ["mold", "grill", "batch_pot", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 3,
                "batch_pot": 3,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": True,
            "rival_char_id": "chef_jp",
            "unlock_banner": "[오사카 Day 3 풀세트] 야타이 야키소바 철판 + 반숙 계란후라이 토핑 해금!",
            "gameplay_tip": "야키소바 철판 위에 반숙 계란후라이 토핑을 얹어 켄지의 콧대를 꺾어주세요!",
        },
    },

    # --------------------------------------------------------------------------
    # 제3막: 멕시코 (MX) - 멕시코시티 스트리트 피에스타 (살사 아미고 디에고 라이벌전)
    # --------------------------------------------------------------------------
    "MX": {
        1: {
            "chapter_id": "MX",
            "day": 1,
            "title": "MX Day 1. 파펠 피카도 깃발 아래 펼쳐진 퀘사디야 파티",
            "subtitle": "퀘사디야 코말 프레스(Mold) + 마가리타·콜라 디스펜서 오픈!",
            "unlocked_slots": ["mold", "dispenser", "tray", "skill"],
            "cooking_slots": ["mold", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 2,
                "batch_pot": 2,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": "[멕시코시티 Day 1] 퀘사디야 코말 프레스 & 라임 마가리타·콜라 디스펜서 오픈!",
            "gameplay_tip": "치즈 퀘사디야와 치킨 퀘사디야를 빠르게 구워 정열적인 현지 손님들을 맞이하세요!",
        },
        2: {
            "chapter_id": "MX",
            "day": 2,
            "title": "MX Day 2. 정열의 로호 살사와 크리미한 과카몰리 타코",
            "subtitle": "카르니타스 타코 그릴(Grill) & 살사·과카몰리 토핑 추가 오픈!",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "skill"],
            "cooking_slots": ["mold", "grill", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 3,
                "batch_pot": 2,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": "[멕시코시티 Day 2] 카르니타스 타코 그릴 + 로호 살사 & 아보카도 과카몰리 토핑 오픈!",
            "gameplay_tip": "카르니타스 타코에 살사 또는 과카몰리를 정확히 올려 고단가 토핑 팁을 노리세요!",
        },
        3: {
            "chapter_id": "MX",
            "day": 3,
            "title": "MX Day 3. 살사 아미고 '디에고'와의 피에스타 준결승전!",
            "subtitle": "피에스타 나초 프라이어(Batch Pot) 풀세트 개방 & 4강 라이벌 매치",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "batch_pot", "skill"],
            "cooking_slots": ["mold", "grill", "batch_pot", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 3,
                "batch_pot": 3,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": True,
            "rival_char_id": "chef_mx",
            "unlock_banner": "[멕시코시티 Day 3 풀세트] 피에스타 나초 프라이어 & 칠리치즈 나초 오픈!",
            "gameplay_tip": "바삭한 크리스피 나초에 치즈 토핑을 듬뿍 올려 피에스타의 열기를 정점으로 끌어올리세요!",
        },
    },

    # --------------------------------------------------------------------------
    # 제4막: 대만 (TW) - 타이베이 스린 야시장 (야시장 퀸 메이링과의 월드 그랑프리 결승)
    # --------------------------------------------------------------------------
    "TW": {
        1: {
            "chapter_id": "TW",
            "day": 1,
            "title": "TW Day 1. 붉은 홍등 아래 결을 살려 굽는 스린 총좌빙",
            "subtitle": "스린 총좌빙 무쇠팬(Mold) + 흑당 버블티·망고스무디 머신 오픈!",
            "unlocked_slots": ["mold", "dispenser", "tray", "skill"],
            "cooking_slots": ["mold", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 2,
                "batch_pot": 2,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": "[타이베이 Day 1] 스린 총좌빙 무쇠팬 & 흑당 버블티·망고스무디 머신 오픈!",
            "gameplay_tip": "스린 야시장은 음료 회전율이 생명입니다! 버블티와 망고스무디를 쉼 없이 추출하세요.",
        },
        2: {
            "chapter_id": "TW",
            "day": 2,
            "title": "TW Day 2. 얼굴보다 큰 대왕 지파이와 얼얼한 마라 시즈닝",
            "subtitle": "대왕 지파이 튀김기(Grill) & 사천 마라 시즈닝 토핑 추가 오픈!",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "skill"],
            "cooking_slots": ["mold", "grill", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 3,
                "batch_pot": 2,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": "[타이베이 Day 2] 대왕 지파이 튀김기 & 사천 마라 시즈닝 토핑 오픈!",
            "gameplay_tip": "갓 튀긴 대왕 지파이에 마라 시즈닝을 뿌려 야시장 최고 인기 메뉴를 완성하세요!",
        },
        3: {
            "chapter_id": "TW",
            "day": 3,
            "title": "TW Day 3. 월드 포차 그랑프리 결승전: 스린 야시장 퀸 '메이링'!",
            "subtitle": "불꽃 큐브스테이크 철판(Batch Pot) 풀세트 개방 & 세계 챔피언 결정전!",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "batch_pot", "skill"],
            "cooking_slots": ["mold", "grill", "batch_pot", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {
                "mold": 3,
                "dispenser": 3,
                "grill": 3,
                "batch_pot": 3,
                "tray": 3,
            },
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": True,
            "rival_char_id": "chef_tw",
            "unlock_banner": "[타이베이 Day 3 결승 풀세트] 불꽃 큐브스테이크 철판 & 갈릭버터 소스 토핑 오픈!",
            "gameplay_tip": "토치 불쇼로 구운 큐브스테이크에 갈릭버터 소스를 얹어 월드 포차 챔피언 왕관을 차지하세요!",
        },
    },
}

# CN, IN, US, RU, BR 신규 대륙 5개국 스토리 진행도(Day 1: 몰드+음료, Day 2: +그릴, Day 3~5: 풀세트+보스전) 자동 구성
for _new_ch, _new_label, _new_rival_id, _new_rival_name, _new_dish in (
    ("CN", "중국 사천·상하이 야시장", "chef_cn_sichuan", "사천 불꽃 메이화", "샤오롱바오·양꼬치·마라탕"),
    ("IN", "인도 올드델리·뭄바이 바자르", "chef_in_delhi", "올드델리 탄두르 비크람", "사모사·탄두리 치킨·버터치킨 커리"),
    ("US", "미국 뉴욕·텍사스 푸드트럭 파크", "chef_us_texas", "텍사스 스모크 빅 행크", "핫도그·스매시 버거·브리스킷"),
    ("RU", "러시아 모스크바·시베리아 야시장", "chef_ru_moscow", "모스크바 이반", "블리니·샤슬릭·보르시"),
    ("BR", "브라질 리우·상파울루 페이라", "chef_br_rio", "리우 카를로스", "파스텔·피카냐 슈하스코·페이조아다"),
):
    _RAW_STORY_PROGRESSION[_new_ch] = {
        1: {
            "chapter_id": _new_ch,
            "day": 1,
            "title": f"{_new_ch} Day 1. {_new_label} 첫 입성!",
            "subtitle": f"{_new_label} 몰드 기구 & 전통 음료 디스펜서 오픈!",
            "unlocked_slots": ["mold", "dispenser", "tray", "skill"],
            "cooking_slots": ["mold", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {"mold": 3, "dispenser": 3, "grill": 2, "batch_pot": 2, "tray": 3},
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": f"[{_new_label} Day 1] 현지 전통 몰드 구이 & 음료 디스펜서 오픈!",
            "gameplay_tip": f"{_new_label}의 현지 손님들에게 빠르고 정확한 첫인상을 남기세요!",
        },
        2: {
            "chapter_id": _new_ch,
            "day": 2,
            "title": f"{_new_ch} Day 2. 직화 그릴의 열기와 비법 토핑",
            "subtitle": f"{_new_label} 직화 그릴·튀김기(Grill) 추가 오픈!",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "skill"],
            "cooking_slots": ["mold", "grill", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {"mold": 3, "dispenser": 3, "grill": 3, "batch_pot": 2, "tray": 3},
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": False,
            "unlock_banner": f"[{_new_label} Day 2] 직화 그릴 스테이션 & 현지 특제 토핑 추가 개방!",
            "gameplay_tip": "조립 트레이에서 현지 특제 토핑을 얹어 고단가 메뉴로 매출을 끌어올리세요!",
        },
        3: {
            "chapter_id": _new_ch,
            "day": 3,
            "title": f"{_new_ch} Day 3. 32강 월드 그랑프리 대륙 결전: '{_new_rival_name}'!",
            "subtitle": f"대량 조리 팬(Batch Pot) 풀세트 개방 & {_new_rival_name} 타이틀전!",
            "unlocked_slots": ["mold", "dispenser", "tray", "grill", "batch_pot", "skill"],
            "cooking_slots": ["mold", "grill", "batch_pot", "dispenser"],
            "tray_unlocked": True,
            "toppings_unlocked": True,
            "skill_unlocked": True,
            "shop_unlocked": True,
            "max_station_levels": {"mold": 3, "dispenser": 3, "grill": 3, "batch_pot": 3, "tray": 3},
            "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
            "special_vip": True,
            "rival_char_id": _new_rival_id,
            "unlock_banner": f"[{_new_label} Day 3 풀세트] {_new_dish} 4대 기구 전면 가동!",
            "gameplay_tip": f"대륙 최강자 {_new_rival_name}와의 정면 승부입니다! [SPACE] 스킬과 피버 타임으로 승리를 쟁취하세요!",
        },
    }

# JP, MX, TW 및 신규 5개국의 Day 4, Day 5도 Day 3(풀세트)과 동일한 해금 규칙을 유지하되 타이틀/서브타이틀을 부여
for _ch_code, _ch_label, _rival_name in (
    ("JP", "오사카 도톤보리", "켄지"),
    ("MX", "멕시코시티 피에스타", "디에고"),
    ("TW", "타이베이 스린 야시장", "메이링"),
    ("CN", "중국 사천·상하이 야시장", "메이화"),
    ("IN", "인도 올드델리 바자르", "비크람"),
    ("US", "미국 뉴욕·텍사스 파크", "빅 행크"),
    ("RU", "러시아 모스크바 광장", "이반"),
    ("BR", "브라질 리우 해변 페이라", "카를로스"),
):
    _base_day3 = dict(_RAW_STORY_PROGRESSION[_ch_code][3])
    for _extra_day in (4, 5):
        _copied = dict(_base_day3)
        _copied["day"] = _extra_day
        _copied["max_station_levels"] = dict(_base_day3["max_station_levels"])
        _copied["unlocked_slots"] = list(_base_day3["unlocked_slots"])
        _copied["cooking_slots"] = list(_base_day3["cooking_slots"])
        _copied["unlocked_interiors"] = list(_base_day3["unlocked_interiors"])
        if _extra_day == 4:
            _copied["title"] = f"{_ch_code} Day 4. {_ch_label} 야간 피크타임 제패"
            _copied["subtitle"] = f"{_rival_name}도 감탄한 풀코스 포장마차 영업"
        else:
            _copied["title"] = f"{_ch_code} Day 5. {_ch_label} 마스터 타이틀 방어전"
            _copied["subtitle"] = "다음 월드 투어 개최지를 향한 완벽한 마무리!"
        _RAW_STORY_PROGRESSION[_ch_code][_extra_day] = _copied


STORY_PROGRESSION: Dict[str, AttrDict] = {}
for _ch_id, _days_map in _RAW_STORY_PROGRESSION.items():
    _wrapped_days = AttrDict()
    for _d_num, _d_info in _days_map.items():
        _entry = AttrDict(_d_info)
        _entry["max_station_levels"] = AttrDict(_d_info["max_station_levels"])
        _wrapped_days[_d_num] = _entry
        _wrapped_days[str(_d_num)] = _entry
    STORY_PROGRESSION[_ch_id] = _wrapped_days


# ==============================================================================
# 2. 32강 월드 포차 그랑프리 토너먼트 드라마 데이터 (TOURNAMENT_DRAMA)
# ==============================================================================
_RAW_TOURNAMENT_DRAMA: Dict[str, Dict[str, Any]] = {
    "round_32": {
        "id": "round_32",
        "round_label": "32강전 (서울 지역 대표 선발전)",
        "chapter_id": "KR",
        "day": 5,
        "opponent_name": "종로 철판왕 박씨 & VIP 심사위원 먹방킹",
        "opponent_country": "KR",
        "title": "중고 리어카에서 피어난 기적, 대한민국 대표 포차 선발!",
        "summary": "구독자 200만 유튜버 '먹방킹'의 라이브 심사 속에서 종로 뒷골목 리어카가 당당히 한국 대표로 선발되다.",
    },
    "round_16": {
        "id": "round_16",
        "round_label": "16강전 (아시아 블록 예선)",
        "chapter_id": "JP",
        "day": 1,
        "opponent_name": "홍콩 템플스트리트 웍 마스터 첸",
        "opponent_country": "HK",
        "title": "도톤보리 강변을 수놓은 한·일 스트리트 푸드의 교차",
        "summary": "아시아 각국의 포장마차 고수들이 모인 오사카 예선에서 압도적인 회전율로 8강에 진출하다.",
    },
    "quarterfinal": {
        "id": "quarterfinal",
        "round_label": "8강전 (일본 오사카 도톤보리 결전)",
        "chapter_id": "JP",
        "day": 3,
        "opponent_name": "켄지 (도톤보리 야타이 장인)",
        "opponent_char_id": "chef_jp",
        "opponent_country": "JP",
        "title": "타코야키 철판 위의 불꽃 대결! 3대째 야타이 장인 켄지",
        "summary": "1초의 오차도 허용하지 않는 켄지의 '장인의 불쇼'에 맞서, 김포차의 정성과 속도로 승리를 거두다.",
    },
    "semifinal": {
        "id": "semifinal",
        "round_label": "4강전 (멕시코시티 스트리트 피에스타 결전)",
        "chapter_id": "MX",
        "day": 3,
        "opponent_name": "디에고 (살사 아미고)",
        "opponent_char_id": "chef_mx",
        "opponent_country": "MX",
        "title": "마리아치 음악과 매콤한 살사의 폭풍! 피에스타 준결승",
        "summary": "관중을 매료시키는 디에고의 '피에스타 타임' 열기 속에서 완벽한 토핑 조합으로 결승 티켓을 거머쥐다.",
    },
    "final": {
        "id": "final",
        "round_label": "결승전 (타이베이 스린 야시장 그랜드 파이널)",
        "chapter_id": "TW",
        "day": 3,
        "opponent_name": "메이링 (스린 야시장 퀸)",
        "opponent_char_id": "chef_tw",
        "opponent_country": "TW",
        "title": "붉은 홍등 아래 펼쳐지는 세계 최강 포차 마스터 결정전!",
        "summary": "초고속 음료 추출과 대량 철판 요리의 여왕 메이링을 상대로 모든 조리 기구의 극한을 끌어내 우승 트로피를 들어 올리다.",
    },
}

TOURNAMENT_DRAMA: Dict[str, AttrDict] = {
    k: AttrDict(v) for k, v in _RAW_TOURNAMENT_DRAMA.items()
}


# ==============================================================================
# 3. 스토리 컷신 & 대사 스크립트 (STORY_DIALOGUES)
# ==============================================================================
def _line(
    speaker: str,
    text: str,
    speaker_id: str = "narrator",
    role: str = "",
    emotion: str = "normal",
    color: Tuple[int, int, int] = (255, 215, 64),
) -> AttrDict:
    """개별 대사 라인 AttrDict 생성 헬퍼."""
    return AttrDict(
        {
            "speaker": speaker,
            "name": speaker,
            "character": speaker,
            "speaker_id": speaker_id,
            "char_id": speaker_id,
            "role": role,
            "title": role,
            "text": text,
            "line": text,
            "dialogue": text,
            "message": text,
            "emotion": emotion,
            "mood": emotion,
            "color": color,
            "speaker_color": color,
        }
    )


def _cutscene(
    cutscene_id: str,
    chapter_id: str,
    day: int,
    timing: str,
    title: str,
    subtitle: str,
    illustration: str,
    unlock_notice: str,
    lines: List[AttrDict],
    unlocked_items: Optional[List[str]] = None,
) -> AttrDict:
    """컷신 데이터 블록 AttrDict 생성 헬퍼."""
    items = list(unlocked_items) if unlocked_items else ([unlock_notice] if unlock_notice else [])
    return AttrDict(
        {
            "id": cutscene_id,
            "cutscene_id": cutscene_id,
            "chapter_id": chapter_id,
            "chapter": chapter_id,
            "day": day,
            "timing": timing,
            "title": title,
            "subtitle": subtitle,
            "illustration": illustration,
            "image_path": illustration,
            "image": illustration,
            "bg_image": illustration,
            "unlock_notice": unlock_notice,
            "unlock_banner": unlock_notice,
            "unlock_summary": unlock_notice,
            "unlocked_items": items,
            "lines": lines,
            "dialogues": lines,
            "script": lines,
        }
    )


_RAW_CUTSCENES: Dict[str, AttrDict] = {
    # ==========================================================================
    # 프롤로그 (Prologue): 망해가는 식당 정리 & 중고 붕어빵 틀 리어카의 시작
    # ==========================================================================
    "prologue": _cutscene(
        cutscene_id="prologue",
        chapter_id="KR",
        day=0,
        timing="prologue",
        title="프롤로그: 셔터 내린 식당, 다시 켜진 작은 불씨",
        subtitle="서울 종로 뒷골목 · 코끝 시린 12월의 밤",
        illustration=STORY_ILLUSTRATIONS["prologue"],
        unlock_notice="[스토리 시작] 중고 붕어빵 틀 1개가 놓인 작은 리어카에서 재기가 시작됩니다!",
        unlocked_items=["황금 붕어빵 틀 (팥 붕어빵 / 슈크림 붕어빵)"],
        lines=[
            _line(
                speaker="내레이션",
                speaker_id="narrator",
                role="프롤로그",
                text="철컥— 무거운 철제 셔터가 내려앉으며, 10년간 청춘을 바쳤던 골목 식당의 마지막 불이 꺼졌다.",
                emotion="sad",
                color=(196, 190, 208),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="보증금 빼고 밀린 월세랑 재료비 정산하고 나니까... 주머니에 딱 동전 몇 닢이랑 이 낡은 리어카 한 대 남았네.",
                emotion="sad",
                color=(235, 92, 42),
            ),
            _line(
                speaker="내레이션",
                speaker_id="narrator",
                role="프롤로그",
                text="대형 프랜차이즈의 공세와 치솟은 임대료 앞에 무릎 꿇은 밤. 하지만 김포차는 황학동 고물상 구석에서 그을린 주물 붕어빵 틀 하나를 품에 안고 돌아왔다.",
                emotion="determined",
                color=(196, 190, 208),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="번듯한 간판도, 넓은 주방도 이제 없지만... 내 손끝에 익은 불 조절이랑 정성까지 압류당한 건 아니잖아!",
                emotion="determined",
                color=(235, 92, 42),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="좋아, 종로 뒷골목 이 자리에서 중고 붕어빵 틀 하나로 다시 시작하는 거야. 언젠가 전 세계 사람들이 줄 서서 먹는 최고의 포장마차를 만들고 말겠어!",
                emotion="excited",
                color=(255, 208, 68),
            ),
        ],
    ),

    # ==========================================================================
    # 제1막 한국 (KR) - Day 1 ~ Day 5 시작 전 / 클리어 후 대사
    # ==========================================================================
    "KR_1_start": _cutscene(
        cutscene_id="KR_1_start",
        chapter_id="KR",
        day=1,
        timing="start",
        title="제1막 Day 1: 중고 붕어빵 틀 하나뿐인 리어카",
        subtitle="서울 종로 뒷골목 · 첫 영업 개시",
        illustration=STORY_ILLUSTRATIONS["prologue"],
        unlock_notice="[Day 1 오픈] 황금 붕어빵 틀 (팥 붕어빵 / 슈크림 붕어빵) 단독 영업!",
        unlocked_items=["황금 붕어빵 틀 (2슬롯)"],
        lines=[
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="후우... 입김이 하얗게 얼어붙네. 아직 리어카 위엔 중고 붕어빵 틀 딱 하나뿐이지만, 단팥이랑 슈크림 반죽만큼은 새벽부터 진심으로 쑤었어.",
                emotion="determined",
                color=(235, 92, 42),
            ),
            _line(
                speaker="단골 고등학생 민수",
                speaker_id="student",
                role="종로고 3학년",
                text="어?! 사장님! 식당 문 닫으셨다길래 걱정했는데, 여기서 리어카 포차를 여셨네요! 고소한 붕어빵 냄새 맡고 달려왔어요!",
                emotion="surprised",
                color=(82, 235, 118),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="민수구나! 그래, 오늘이 내 인생 2막 첫날이다. 겉은 바삭하고 속은 꼬리까지 꽉 찬 첫 붕어빵, 지금 바로 구워줄게!",
                emotion="warm",
                color=(235, 92, 42),
            ),
        ],
    ),
    "KR_1_clear": _cutscene(
        cutscene_id="KR_1_clear",
        chapter_id="KR",
        day=1,
        timing="clear",
        title="제1막 Day 1 마감: 종이봉투에 담긴 작은 온기",
        subtitle="첫날 목표 매출 달성! · 어묵·식혜 디스펜서 해금",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[내일(Day 2) 해금] 어묵국물 & 식혜 디스펜서 + 포차 상점(몰드 Lv.1, 천막 & 알전구) 오픈!",
        unlocked_items=[
            "어묵국물 & 식혜 디스펜서",
            "포차 상점 개방 (몰드 Lv.1 개조 / 포차 천막 & 알전구)",
        ],
        lines=[
            _line(
                speaker="단골 고등학생 민수",
                speaker_id="student",
                role="종로고 3학년",
                text="와... 허기진 배에 갓 구운 붕어빵 한 입 베어 무니까 시험 스트레스가 싹 날아가요! 근데 사장님, 같이 마실 뜨끈한 국물이나 시원한 식혜도 있으면 대박이겠는데요?",
                emotion="excited",
                color=(82, 235, 118),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="맞아, 추운 밤엔 붕어빵 먹다가 목도 메고 손도 시리지! 오늘 번 첫 매상으로 무와 다시마 듬뿍 넣은 어묵국물 통이랑 살얼음 식혜 디스펜서를 들여놔야겠다!",
                emotion="proud",
                color=(235, 92, 42),
            ),
            _line(
                speaker="내레이션",
                speaker_id="narrator",
                role="해금 안내",
                text="첫 영업 수익으로 리어카 한쪽에 '어묵국물 & 식혜 디스펜서'가 설치되었고, 포차 정비 상점이 문을 열었습니다!",
                emotion="warm",
                color=(255, 215, 64),
            ),
        ],
    ),
    "KR_2_start": _cutscene(
        cutscene_id="KR_2_start",
        chapter_id="KR",
        day=2,
        timing="start",
        title="제1막 Day 2: 김이 모락모락 피어오르는 국물 한 컵",
        subtitle="어묵·식혜 디스펜서 가동 & 주황빛 알전구의 온기",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[Day 2 오픈] 어묵국물 & 식혜 디스펜서 가동! (음료는 타지 않으니 미리 준비하세요)",
        unlocked_items=["뜨끈 어묵국물", "살얼음 식혜", "고화력 몰드 Lv.1", "포차 천막 & 알전구"],
        lines=[
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="보글보글 끓는 어묵 육수 냄새가 골목에 퍼지니까 드디어 진짜 포장마차답네! 알전구까지 달아놓으니 훨씬 아늑해.",
                emotion="warm",
                color=(235, 92, 42),
            ),
            _line(
                speaker="야근 과장 박 대리",
                speaker_id="office_worker",
                role="종로 IT기업 직장인",
                text="휴... 칼바람 부는데 저 주황색 불빛 보니까 그냥 지나칠 수가 없네요. 사장님, 뜨끈한 어묵국물 한 컵이랑 달달한 슈크림 붕어빵 좀 주세요!",
                emotion="warm",
                color=(68, 148, 255),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="어서 오세요! 디스펜서에서 바로 따른 뜨끈한 국물부터 먼저 드시고 몸 녹이세요!",
                emotion="excited",
                color=(235, 92, 42),
            ),
        ],
    ),
    "KR_2_clear": _cutscene(
        cutscene_id="KR_2_clear",
        chapter_id="KR",
        day=2,
        timing="clear",
        title="제1막 Day 2 마감: 퇴근길 직장인들의 출출한 발걸음",
        subtitle="2일차 목표 달성! · 직화 닭꼬치 그릴 & 조립 트레이 해금",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[내일(Day 3) 해금] 직화 닭꼬치 그릴 + 중앙 조립 트레이 & 토핑 3종(매운양념/데리야키/파채) + 플라스틱 의자!",
        unlocked_items=[
            "직화 닭꼬치 그릴",
            "중앙 조립 트레이 & 토핑(매운양념, 데리야키, 파채)",
            "레트로 플라스틱 의자 (손님 슬롯 4칸 확장 가능)",
        ],
        lines=[
            _line(
                speaker="야근 과장 박 대리",
                speaker_id="office_worker",
                role="종로 IT기업 직장인",
                text="크으~ 국물이 끝내줍니다! 그런데 사장님, 야근 끝나고 출출할 땐 불향 확 입힌 직화 닭꼬치 하나 뜯으면 소원이 없겠어요.",
                emotion="excited",
                color=(68, 148, 255),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="직화 닭꼬치라! 그렇지, 내 특제 매운양념이랑 단짠 데리야키 소스, 거기에 아삭한 파채까지 산더미처럼 올리면 종로 직장인들 다 모이겠는걸?",
                emotion="determined",
                color=(235, 92, 42),
            ),
            _line(
                speaker="내레이션",
                speaker_id="narrator",
                role="해금 안내",
                text="리어카 중앙에 '보온 조립 트레이'와 '직화 닭꼬치 그릴'이 증설되었습니다! 이제 구운 요리에 다채로운 토핑을 얹어 서빙할 수 있습니다.",
                emotion="warm",
                color=(255, 215, 64),
            ),
        ],
    ),
    "KR_3_start": _cutscene(
        cutscene_id="KR_3_start",
        chapter_id="KR",
        day=3,
        timing="start",
        title="제1막 Day 3: 숯불 위에서 춤추는 닭꼬치와 토핑의 마법",
        subtitle="직화 닭꼬치 그릴 & 중앙 조립 트레이 본격 가동!",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[Day 3 오픈] 구운 소금구이 닭꼬치를 트레이로 옮긴 뒤 매운양념·데리야키·파채 토핑을 추가하세요!",
        unlocked_items=[
            "소금구이 닭꼬치",
            "매운양념 / 데리야키 / 파채 양념닭꼬치",
            "중앙 조립 트레이",
        ],
        lines=[
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="치이익— 소금구이 닭꼬치 익는 소리 좀 봐! 그대로 서빙해도 맛있지만, 중앙 트레이에 올려서 매운양념이나 파채를 얹으면 단가가 훨씬 높아지지!",
                emotion="excited",
                color=(235, 92, 42),
            ),
            _line(
                speaker="야근 과장 박 대리",
                speaker_id="office_worker",
                role="종로 IT기업 직장인",
                text="사장님! 오늘 팀원들 다 데리고 왔습니다! 저는 화끈한 파채 양념닭꼬치로 주시고요, 옆 대리는 달콤한 데리야키 닭꼬치 부탁해요!",
                emotion="excited",
                color=(68, 148, 255),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="주문하신 꼬치 금방 나갑니다! 트레이 조합 순서 헷갈리지 않게 정신 바짝 차려보자고!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "KR_3_clear": _cutscene(
        cutscene_id="KR_3_clear",
        chapter_id="KR",
        day=3,
        timing="clear",
        title="제1막 Day 3 마감: 골목 어귀까지 늘어선 줄",
        subtitle="3일차 목표 달성! · 철판 떡볶이 팬 & 마스터 스킬 해금",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[내일(Day 4) 해금] 포차 철판 떡볶이 팬(3인분 대량조리) + 치즈/김말이 토핑 + 마스터 액티브 스킬 [SPACE]!",
        unlocked_items=[
            "포차 철판 떡볶이 팬 (1회 조리 시 3인분 생성)",
            "모짜렐라 치즈 & 바삭 김말이 토핑",
            "마스터 스킬 [SPACE]: 포차 이모님의 인심",
            "야시장 네온 입간판",
        ],
        lines=[
            _line(
                speaker="단골 고등학생 민수",
                speaker_id="student",
                role="종로고 3학년",
                text="사장님, 이제 우리 학교 애들 사이에서 이 포차가 '종로 성지'로 소문났어요! 근데 손님이 한꺼번에 몰릴 때 대량으로 퍼 줄 수 있는 철판 떡볶이가 있으면 완벽할 것 같아요!",
                emotion="excited",
                color=(82, 235, 118),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="맞아, 한 번 판을 달궈서 3인분씩 넉넉하게 퍼 담는 철판 떡볶이! 거기에 모짜렐라 치즈랑 김말이까지 얹어주면 손님들이 아무리 몰려와도 거뜬하지!",
                emotion="proud",
                color=(235, 92, 42),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="그리고 손님들 기다리다 지칠 때 쓰는 내 비장의 무기도 드디어 봉인 해제다. '포차 이모님의 인심' 한마디면 손님들 마음도 사르르 녹을 거야!",
                emotion="excited",
                color=(255, 208, 68),
            ),
        ],
    ),
    "KR_4_start": _cutscene(
        cutscene_id="KR_4_start",
        chapter_id="KR",
        day=4,
        timing="start",
        title="제1막 Day 4: 완전체 4슬롯 포차와 마스터의 각성",
        subtitle="철판 떡볶이 대량 조리 팬 + [SPACE] 포차 이모님의 인심 개방!",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[Day 4 오픈] 4대 조리 기구 풀가동! 위기 시 [SPACE] 키로 모든 손님 인내심 회복 & 조리 속도 2배!",
        unlocked_items=[
            "철판 떡볶이 / 치즈 떡볶이 / 김말이 떡볶이",
            "마스터 스킬 [SPACE]: 포차 이모님의 인심 (인내심 +40%, 8초간 조리속도 2배)",
        ],
        lines=[
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="붕어빵 틀, 닭꼬치 그릴, 철판 떡볶이 팬, 어묵·식혜 디스펜서까지... 중고 틀 하나로 시작했던 리어카가 이제 어엿한 풀코스 포장마차가 됐어!",
                emotion="proud",
                color=(235, 92, 42),
            ),
            _line(
                speaker="단골 고등학생 민수",
                speaker_id="student",
                role="종로고 3학년",
                text="우와! 저 꾸덕꾸덕한 빨간 떡볶이 빛깔 좀 봐! 사장님, 치즈 떡볶이 하나랑 김말이 떡볶이 하나 빨리 주세요! 침 넘어간단 말이에요!",
                emotion="excited",
                color=(82, 235, 118),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="어서 와요~ 추운데 뜨끈한 국물 한 잔 먼저 해! [SPACE] 키로 인심 한 번 베풀면서 오늘 밤 종로 골목을 휩쓸어 보자!",
                emotion="excited",
                color=(255, 208, 68),
            ),
        ],
    ),
    "KR_4_clear": _cutscene(
        cutscene_id="KR_4_clear",
        chapter_id="KR",
        day=4,
        timing="clear",
        title="제1막 Day 4 마감: 심상치 않은 카메라 불빛과 소문",
        subtitle="4일차 목표 달성! · 내일 VIP 맛집 유튜버 '먹방킹' 방문 예고",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[내일(Day 5) 예고] 구독자 200만 VIP 유튜버 방문! 상점 전 기구 Lv.3 및 7080 감성 라디오 해금!",
        unlocked_items=[
            "전 조리 기구 Lv.3 마스터 개조 해금",
            "7080 감성 라디오 (콤보 보너스 팁 +25%)",
            "Day 5 VIP 유튜버 특별 테스트",
        ],
        lines=[
            _line(
                speaker="야근 과장 박 대리",
                speaker_id="office_worker",
                role="종로 IT기업 직장인",
                text="사장님, 방금 SNS 보셨어요?! 글로벌 스트리트 푸드 유튜버 '먹방킹'이 내일 밤 종로에서 가장 핫한 이 포장마차에 암행 촬영을 온대요!",
                emotion="surprised",
                color=(68, 148, 255),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="구독자 200만 먹방킹이 우리 리어카에?! 그 친구는 전 세계 길거리 음식 그랑프리 심사위원도 겸하고 있다던데...!",
                emotion="surprised",
                color=(235, 92, 42),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="물러설 수 없지. 오늘 밤 상점에서 기구들을 최고 단계까지 정비하고 7080 라디오까지 켜 둔다. 내일 대한민국 포장마차의 진짜 저력을 보여주겠어!",
                emotion="determined",
                color=(255, 208, 68),
            ),
        ],
    ),
    "KR_5_start": _cutscene(
        cutscene_id="KR_5_start",
        chapter_id="KR",
        day=5,
        timing="start",
        title="제1막 Day 5: 종로 최종 테스트 & VIP 유튜버 라이브",
        subtitle="서울 종로·광장 야시장 피날레 · 월드 투어 초청장 심사전",
        illustration=STORY_ILLUSTRATIONS["act1_pocha_revival"],
        unlock_notice="[Day 5 최종전] VIP 유튜버와 밀려드는 손님들을 만족시키고 월드 포차 초청장을 획득하세요!",
        unlocked_items=["VIP 유튜버 특별 심사", "월드 투어 초청장 도전"],
        lines=[
            _line(
                speaker="맛집 유튜버 먹방킹",
                speaker_id="youtuber_vip",
                role="구독자 200만 스트리트 푸드 유튜버",
                text="여러분 안녕하세요, 먹방킹입니다! 오늘 찾아온 곳은 중고 붕어빵 틀 하나로 시작해 일주일 만에 종로를 평정했다는 전설의 리어카 포차입니다!",
                emotion="excited",
                color=(255, 215, 64),
            ),
            _line(
                speaker="맛집 유튜버 먹방킹",
                speaker_id="youtuber_vip",
                role="구독자 200만 스트리트 푸드 유튜버",
                text="과연 소문처럼 붕어빵, 파채 닭꼬치, 치즈 떡볶이, 어묵국물까지 밀려드는 주문을 완벽한 콤보로 소화해 낼 수 있을지, 지금 실시간 라이브로 검증해 보겠습니다!",
                emotion="determined",
                color=(255, 215, 64),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="카메라 앞이라고 떨릴쏘냐! 손님 한 분 한 분께 따뜻한 정성을 대접한다는 마음으로, 내 생애 최고의 영업 피크타임을 시작한다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "KR_5_clear": _cutscene(
        cutscene_id="KR_5_clear",
        chapter_id="KR",
        day=5,
        timing="clear",
        title="제1막 클리어: 조회수 1,000만 폭발과 월드 포차 초청장!",
        subtitle="종로 야시장 완전 제패! · 제2막 일본 오사카 도톤보리 해금",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[월드 투어 개막] '32강 월드 포차 그랑프리' 초청장 획득! Chapter 2 일본 오사카(JP)가 열렸습니다!",
        unlocked_items=[
            "32강 월드 포차 그랑프리 공식 출전권",
            "Chapter 2. 오사카 도톤보리 야타이 (JP) 원정 해금",
            "도톤보리 야타이 장인 '켄지' 라이벌 매치 개방",
        ],
        lines=[
            _line(
                speaker="맛집 유튜버 먹방킹",
                speaker_id="youtuber_vip",
                role="구독자 200만 스트리트 푸드 유튜버",
                text="세상에... 바삭한 붕어빵부터 불향 가득한 파채 닭꼬치, 꾸덕한 치즈 떡볶이까지! 이건 단순한 길거리 음식이 아니라 영혼을 울리는 예술입니다! 라이브 동시접속자 50만 돌파!",
                emotion="excited",
                color=(255, 215, 64),
            ),
            _line(
                speaker="맛집 유튜버 먹방킹",
                speaker_id="youtuber_vip",
                role="구독자 200만 스트리트 푸드 유튜버",
                text="사장님, 월드 포차 협회 심사위원 자격으로 이 황금 봉투를 드립니다! 전 세계 32개국 최고 포장마차 장인들이 맞붙는 '월드 포차 그랑프리' 한국 대표 초청장입니다!",
                emotion="proud",
                color=(255, 215, 64),
            ),
            _line(
                speaker="단골 고등학생 민수",
                speaker_id="student",
                role="종로고 3학년",
                text="우와아아! 우리 동네 김포차 사장님이 세계 대회에 나가신대요! 일본 오사카의 타코야키 장인도, 멕시코의 타코 고수도, 대만 야시장 여왕도 다 이기고 오세요!",
                emotion="excited",
                color=(82, 235, 118),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="식당 망하고 중고 붕어빵 틀 하나 붙잡고 울던 게 엊그제 같은데... 고맙다 얘들아! 좋아, 첫 번째 해외 원정지 '오사카 도톤보리'로 리어카 끌고 출발한다!",
                emotion="victory",
                color=(235, 92, 42),
            ),
        ],
    ),

    # ==========================================================================
    # 월드 포차 출정식 (world_departure 별칭 컷신)
    # ==========================================================================
    "world_departure": _cutscene(
        cutscene_id="world_departure",
        chapter_id="JP",
        day=0,
        timing="world_departure",
        title="제2막 출정식: 화물선에 실린 주황빛 포장마차",
        subtitle="인천항 → 오사카 도톤보리 · 32강 월드 포차 그랑프리 개막",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[월드 투어 원정] 각 국가 진입 시 Day 1(몰드+음료) → Day 2(+그릴) → Day 3(+대량팬 풀세트) 순으로 현지 기구에 적응합니다!",
        unlocked_items=[
            "오사카 도톤보리 야타이 (JP)",
            "멕시코시티 스트리트 피에스타 (MX)",
            "타이베이 스린 야시장 (TW)",
        ],
        lines=[
            _line(
                speaker="내레이션",
                speaker_id="narrator",
                role="월드 포차 그랑프리",
                text="종로 골목을 밝혔던 주황빛 비닐 천막과 리어카가 비행기와 화물선에 실려 세계의 밤거리로 향한다.",
                emotion="excited",
                color=(196, 190, 208),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="오사카의 '켄지', 멕시코시티의 '디에고', 그리고 타이베이 스린 야시장의 여왕 '메이링'... 세계 최고의 스트리트 셰프들과 정면 승부라니 가슴이 뛴다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),

    # ==========================================================================
    # 제2막 일본 (JP) - 오사카 도톤보리 야타이 & 라이벌 켄지
    # ==========================================================================
    "JP_1_start": _cutscene(
        cutscene_id="JP_1_start",
        chapter_id="JP",
        day=1,
        timing="start",
        title="제2막 JP Day 1: 도톤보리의 붉은 등불과 야타이 장인",
        subtitle="오사카 도톤보리 강변 · 타코야키 판 & 생맥주 서버 적응전",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[오사카 Day 1 오픈] 도톤보리 타코야키 판(Mold) + 나마비루 & 라무네 서버(Dispenser) + 조립 트레이!",
        unlocked_items=["도톤보리 타코야키 판", "나마비루 & 라무네 서버", "조립 트레이"],
        lines=[
            _line(
                speaker="켄지",
                speaker_id="chef_jp",
                role="도톤보리 야타이 장인",
                text="이랏샤이마세! 네가 서울에서 온 '김포차'인가? 붕어빵 굽던 솜씨로 이 도톤보리의 무쇠 타코야키 판을 다룰 수 있을지 지켜보겠다!",
                emotion="rival",
                color=(218, 56, 72),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="반가워요 켄지 씨! 붕어빵이나 타코야키나 손님 입안에서 겉바속촉으로 터지는 행복은 똑같죠. 첫날은 타코야키와 나마비루 생맥주로 도톤보리 손님들과 인사해 볼까!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "JP_1_clear": _cutscene(
        cutscene_id="JP_1_clear",
        chapter_id="JP",
        day=1,
        timing="clear",
        title="제2막 JP Day 1 마감: 겉바속촉 타코야키 합격점!",
        subtitle="오사카 1일차 돌파! · 내일 비장탄 야키토리 화로 오픈",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[내일(JP Day 2) 해금] 비장탄 야키토리 화로(Grill) & 비전 타레소스 토핑 오픈!",
        unlocked_items=["비장탄 야키토리 화로", "시오 야키토리 / 타레 야키토리"],
        lines=[
            _line(
                speaker="켄지",
                speaker_id="chef_jp",
                role="도톤보리 야타이 장인",
                text="호오... 첫날인데도 타코야키를 굴리는 송곳 손놀림이 예사롭지 않군. 내일은 도톤보리 야타이의 자존심인 '비장탄 야키토리 화로'를 열어주마!",
                emotion="surprised",
                color=(218, 56, 72),
            ),
        ],
    ),
    "JP_2_start": _cutscene(
        cutscene_id="JP_2_start",
        chapter_id="JP",
        day=2,
        timing="start",
        title="제2막 JP Day 2: 비장탄 화로와 3대째 내려온 타레 소스",
        subtitle="오사카 도톤보리 · 비장탄 야키토리 화로(Grill) 가동!",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[오사카 Day 2 오픈] 비장탄 야키토리 화로 추가! 시오 야키토리에 비전 타레소스를 발라 서빙하세요.",
        unlocked_items=["비장탄 야키토리 화로", "비전 타레소스 토핑"],
        lines=[
            _line(
                speaker="켄지",
                speaker_id="chef_jp",
                role="도톤보리 야타이 장인",
                text="야키토리는 화력 조절이 생명이다! 소금만 뿌린 '시오 야키토리'와, 트레이에서 비전 간장 소스를 입힌 '타레 야키토리'를 정확히 구분해 내놓아라!",
                emotion="determined",
                color=(218, 56, 72),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="종로에서 닭꼬치 수천 개를 구웠던 감각이 손끝에 살아있어. 비장탄 숯불 향을 제대로 입혀주지!",
                emotion="excited",
                color=(235, 92, 42),
            ),
        ],
    ),
    "JP_2_clear": _cutscene(
        cutscene_id="JP_2_clear",
        chapter_id="JP",
        day=2,
        timing="clear",
        title="제2막 JP Day 2 마감: 내일은 8강 라이벌전 풀세트 대결!",
        subtitle="오사카 2일차 돌파! · 야타이 야키소바 철판 해금 예고",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[내일(JP Day 3) 해금] 야타이 야키소바 철판(Batch Pot) & 반숙 계란후라이 토핑 풀세트 개방!",
        unlocked_items=["야타이 야키소바 철판", "철판 야키소바 / 계란 야키소바"],
        lines=[
            _line(
                speaker="켄지",
                speaker_id="chef_jp",
                role="도톤보리 야타이 장인",
                text="인정하지 않을 수 없군! 내일은 월드 포차 그랑프리 8강전이자 내 모든 것을 건 승부다. '야타이 야키소바 철판'까지 포함한 4슬롯 풀세트로 정면 승부다!",
                emotion="rival",
                color=(218, 56, 72),
            ),
        ],
    ),
    "JP_3_start": _cutscene(
        cutscene_id="JP_3_start",
        chapter_id="JP",
        day=3,
        timing="start",
        title="제2막 JP Day 3: 도톤보리 야타이 장인 '켄지'와의 불꽃 결전!",
        subtitle="월드 포차 그랑프리 8강전 · 오사카 4대 조리 기구 풀가동!",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[오사카 Day 3 풀세트] 야타이 야키소바 철판 개방! 반숙 계란후라이 토핑으로 최고 매출을 달성하세요!",
        unlocked_items=["야타이 야키소바 철판 (3인분 대량조리)", "반숙 계란후라이 토핑"],
        lines=[
            _line(
                speaker="켄지",
                speaker_id="chef_jp",
                role="도톤보리 야타이 장인",
                text="불꽃 같은 손놀림을 보여주지! 뜨거운 철판에서 볶아낸 야키소바 위에 반숙 계란후라이를 올리는 게 내 필살기다. 과연 네가 내 속도를 따라올 수 있을까?!",
                emotion="rival",
                color=(218, 56, 72),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="불쇼라면 한국 철판 떡볶이도 지지 않죠! 오사카의 밤을 가장 뜨겁게 달궈주겠습니다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "JP_3_clear": _cutscene(
        cutscene_id="JP_3_clear",
        chapter_id="JP",
        day=3,
        timing="clear",
        title="제2막 클리어: 켄지의 인정과 멕시코시티 4강 진출!",
        subtitle="오사카 도톤보리 제패! · 제3막 멕시코시티(MX) 및 켄지 영입 해금",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[8강 돌파] 켄지가 동료 마스터로 합류 가능해졌으며, 제3막 멕시코시티(MX) 원정이 열립니다!",
        unlocked_items=[
            "포차 마스터 '켄지' 영입 가능 (장인의 불쇼 스킬)",
            "Chapter 3. 멕시코시티 스트리트 피에스타 (MX) 원정 해금",
        ],
        lines=[
            _line(
                speaker="켄지",
                speaker_id="chef_jp",
                role="도톤보리 야타이 장인",
                text="크하하! 완패다, 김포차! 네 요리에는 단순한 기술을 넘어 손님의 지친 하루를 어루만지는 따뜻한 혼(魂)이 담겨 있구나!",
                emotion="victory",
                color=(218, 56, 72),
            ),
            _line(
                speaker="켄지",
                speaker_id="chef_jp",
                role="도톤보리 야타이 장인",
                text="이제 내 '장인의 불쇼' 기술도 네 포차와 함께하겠다. 다음 4강전 무대는 정열의 나라 '멕시코시티'다! 살사 아미고 디에고에게도 본때를 보여줘라!",
                emotion="proud",
                color=(255, 184, 52),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="고마워요 켄지 씨! 이제 태평양을 건너 멕시코시티 피에스타 거리로 출동이다!",
                emotion="excited",
                color=(235, 92, 42),
            ),
        ],
    ),

    # ==========================================================================
    # 제3막 멕시코 (MX) - 멕시코시티 스트리트 피에스타 & 라이벌 디에고
    # ==========================================================================
    "MX_1_start": _cutscene(
        cutscene_id="MX_1_start",
        chapter_id="MX",
        day=1,
        timing="start",
        title="제3막 MX Day 1: 올라 아미고! 피에스타 광장의 열기",
        subtitle="멕시코시티 · 퀘사디야 코말 프레스 & 라임 마가리타 오픈",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[멕시코시티 Day 1 오픈] 퀘사디야 코말 프레스(Mold) + 마가리타 & 콜라 디스펜서(Dispenser)!",
        unlocked_items=["퀘사디야 코말 프레스", "마가리타 & 콜라 디스펜서"],
        lines=[
            _line(
                speaker="디에고",
                speaker_id="chef_mx",
                role="살사 아미고",
                text="올라 아미고! 도톤보리의 켄지를 꺾고 올라온 한국 포차 마스터가 바로 당신이군! 멕시코시티의 밤은 음악도, 손님도, 음식도 모두 정열적이지!",
                emotion="excited",
                color=(38, 178, 96),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="거리 전체가 축제 분위기네요! 첫날은 노릇하게 구운 치즈·치킨 퀘사디야와 상큼한 라임 마가리타로 멕시코 손님들의 입맛을 사로잡아 보겠습니다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "MX_1_clear": _cutscene(
        cutscene_id="MX_1_clear",
        chapter_id="MX",
        day=1,
        timing="clear",
        title="제3막 MX Day 1 마감: 코말 철판 위에 피어난 우정",
        subtitle="멕시코시티 1일차 돌파! · 내일 카르니타스 타코 그릴 오픈",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[내일(MX Day 2) 해금] 카르니타스 타코 그릴(Grill) + 로호 살사 & 과카몰리 토핑 오픈!",
        unlocked_items=["카르니타스 타코 그릴", "살사 핫타코 / 과카몰리 타코"],
        lines=[
            _line(
                speaker="디에고",
                speaker_id="chef_mx",
                role="살사 아미고",
                text="브라보! 퀘사디야 치즈가 늘어날 때마다 손님들이 춤을 추더군! 내일은 멕시코의 영혼, '카르니타스 타코 그릴'과 특제 살사·과카몰리를 꺼내 볼까!",
                emotion="excited",
                color=(38, 178, 96),
            ),
        ],
    ),
    "MX_2_start": _cutscene(
        cutscene_id="MX_2_start",
        chapter_id="MX",
        day=2,
        timing="start",
        title="제3막 MX Day 2: 매콤한 로호 살사와 아보카도 과카몰리",
        subtitle="멕시코시티 · 카르니타스 타코 그릴(Grill) 가동!",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[멕시코시티 Day 2 오픈] 카르니타스 타코를 트레이로 옮겨 살사 또는 과카몰리 토핑을 얹으세요!",
        unlocked_items=["카르니타스 타코 그릴", "로호 살사 & 아보카도 과카몰리 토핑"],
        lines=[
            _line(
                speaker="디에고",
                speaker_id="chef_mx",
                role="살사 아미고",
                text="타코는 토핑의 예술이야! 붉은 토마토로 만든 매콤한 '로호 살사'와 신선한 아보카도 '과카몰리'를 손님 주문에 맞춰 번개처럼 얹어 보라고!",
                emotion="determined",
                color=(38, 178, 96),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="매콤한 양념이라면 한국 고추장 못지않게 친숙하죠! 타코 파티, 지금 시작합니다!",
                emotion="excited",
                color=(235, 92, 42),
            ),
        ],
    ),
    "MX_2_clear": _cutscene(
        cutscene_id="MX_2_clear",
        chapter_id="MX",
        day=2,
        timing="clear",
        title="제3막 MX Day 2 마감: 준결승 피에스타 나초 풀세트 예고!",
        subtitle="멕시코시티 2일차 돌파! · 내일 4강 라이벌 매치 개막",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[내일(MX Day 3) 해금] 피에스타 나초 프라이어(Batch Pot) & 칠리치즈 나초 풀세트 개방!",
        unlocked_items=["피에스타 나초 프라이어", "크리스피 나초 / 칠리치즈 나초"],
        lines=[
            _line(
                speaker="디에고",
                speaker_id="chef_mx",
                role="살사 아미고",
                text="아미고, 정말 대단해! 내일은 대망의 월드 포차 그랑프리 4강전이다. '피에스타 나초 프라이어'까지 합류한 풀세트 승부로 누가 결승지 타이베이에 갈지 가려보자!",
                emotion="rival",
                color=(38, 178, 96),
            ),
        ],
    ),
    "MX_3_start": _cutscene(
        cutscene_id="MX_3_start",
        chapter_id="MX",
        day=3,
        timing="start",
        title="제3막 MX Day 3: 살사 아미고 '디에고'와의 피에스타 준결승!",
        subtitle="월드 포차 그랑프리 4강전 · 멕시코 4대 조리 기구 풀가동!",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[멕시코시티 Day 3 풀세트] 피에스타 나초 프라이어 개방! 치즈 토핑을 얹어 칠리치즈 나초를 완성하세요!",
        unlocked_items=["피에스타 나초 프라이어 (3인분 대량조리)", "칠리치즈 나초"],
        lines=[
            _line(
                speaker="디에고",
                speaker_id="chef_mx",
                role="살사 아미고",
                text="마리아치 밴드, 음악 큐! 바삭한 나초 위에 황금빛 치즈 폭포가 쏟아지는 이 밤, 내 '피에스타 타임'을 넘어설 수 있다면 결승 티켓은 당신 거다!",
                emotion="rival",
                color=(38, 178, 96),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="흥겨운 리듬에 손발이 절로 움직이네요! 결승전이 열리는 타이베이 스린 야시장을 향해 전력 질주하겠습니다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "MX_3_clear": _cutscene(
        cutscene_id="MX_3_clear",
        chapter_id="MX",
        day=3,
        timing="clear",
        title="제3막 클리어: 피에스타의 영웅, 결승전 타이베이로!",
        subtitle="멕시코시티 제패! · 제4막 대만 스린 야시장(TW) 및 디에고 영입 해금",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[4강 돌파] 디에고가 동료 마스터로 합류 가능해졌으며, 대망의 결승 무대 타이베이(TW)가 열립니다!",
        unlocked_items=[
            "포차 마스터 '디에고' 영입 가능 (피에스타 타임 스킬)",
            "Chapter 4. 타이베이 스린 야시장 (TW) 결승 무대 해금",
        ],
        lines=[
            _line(
                speaker="디에고",
                speaker_id="chef_mx",
                role="살사 아미고",
                text="무초 그라시아스, 아미고! 당신이 구워낸 타코와 나초는 멕시코시티 광장 전체를 하나로 만들었어! 진심으로 패배를 인정한다!",
                emotion="victory",
                color=(38, 178, 96),
            ),
            _line(
                speaker="디에고",
                speaker_id="chef_mx",
                role="살사 아미고",
                text="이제 마지막 결승전은 미식 야시장의 정점, 대만 '타이베이 스린 야시장'이다! 전년도 챔피언 '메이링'을 꺾고 꼭 세계 정상에 올라줘!",
                emotion="proud",
                color=(255, 212, 48),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="고마워요 디에고! 종로 뒷골목 중고 붕어빵 틀에서 시작한 이 꿈, 마침내 세계 결승 무대까지 왔어. 타이베이로 가자!",
                emotion="excited",
                color=(235, 92, 42),
            ),
        ],
    ),

    # ==========================================================================
    # 제4막 대만 (TW) - 타이베이 스린 야시장 & 최종 보스 메이링
    # ==========================================================================
    "TW_1_start": _cutscene(
        cutscene_id="TW_1_start",
        chapter_id="TW",
        day=1,
        timing="start",
        title="제4막 TW Day 1: 붉은 홍등이 수놓은 미식 야시장의 정점",
        subtitle="타이베이 스린 야시장 · 총좌빙 무쇠팬 & 흑당 버블티 머신 오픈",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[타이베이 Day 1 오픈] 스린 총좌빙 무쇠팬(Mold) + 버블티 & 망고스무디 머신(Dispenser)!",
        unlocked_items=["스린 총좌빙 무쇠팬", "버블티 & 망고스무디 머신"],
        lines=[
            _line(
                speaker="메이링",
                speaker_id="chef_tw",
                role="스린 야시장 퀸",
                text="환영해요, 김포차 사장님! 종로의 작은 리어카에서 출발해 켄지와 디에고를 모두 꺾고 이곳 스린 야시장까지 오시다니 소문대로 대단하네요.",
                emotion="warm",
                color=(232, 68, 52),
            ),
            _line(
                speaker="메이링",
                speaker_id="chef_tw",
                role="스린 야시장 퀸",
                text="하지만 스린 야시장의 손님들은 눈 깜짝할 사이의 속도와 완벽한 풀코스를 원하죠. 첫날은 바삭한 총좌빙과 쫀득한 흑당 버블티로 실력을 보여주세요!",
                emotion="rival",
                color=(48, 212, 204),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="드디어 최종 무대군요, 메이링 씨! 결을 살려 부쳐낸 총좌빙과 달콤한 버블티로 스린 야시장의 첫밤을 열어 보겠습니다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "TW_1_clear": _cutscene(
        cutscene_id="TW_1_clear",
        chapter_id="TW",
        day=1,
        timing="clear",
        title="제4막 TW Day 1 마감: 홍등 거리를 매료시킨 바삭한 파전병",
        subtitle="타이베이 1일차 돌파! · 내일 대왕 지파이 튀김기 오픈",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[내일(TW Day 2) 해금] 대왕 지파이 튀김기(Grill) & 사천 마라 시즈닝 토핑 오픈!",
        unlocked_items=["대왕 지파이 튀김기", "대왕 지파이 / 마라 지파이"],
        lines=[
            _line(
                speaker="메이링",
                speaker_id="chef_tw",
                role="스린 야시장 퀸",
                text="어머, 첫날부터 버블티 추출과 총좌빙 굽기 리듬이 한 치의 흔들림도 없네요! 내일은 스린 야시장의 명물 '대왕 지파이 튀김기'가 추가됩니다. 기대할게요!",
                emotion="surprised",
                color=(232, 68, 52),
            ),
        ],
    ),
    "TW_2_start": _cutscene(
        cutscene_id="TW_2_start",
        chapter_id="TW",
        day=2,
        timing="start",
        title="제4막 TW Day 2: 얼굴만 한 대왕 지파이와 얼얼한 마라의 유혹",
        subtitle="타이베이 스린 야시장 · 대왕 지파이 튀김기(Grill) 가동!",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[타이베이 Day 2 오픈] 바삭하게 튀긴 대왕 지파이에 사천 마라 시즈닝 토핑을 뿌려 서빙하세요!",
        unlocked_items=["대왕 지파이 튀김기", "사천 마라 시즈닝 토핑"],
        lines=[
            _line(
                speaker="메이링",
                speaker_id="chef_tw",
                role="스린 야시장 퀸",
                text="바삭하게 튀겨낸 대왕 지파이에 얼얼한 사천 마라 시즈닝을 솔솔 뿌리고, 시원한 망고 스무디를 곁들이는 게 이곳 최고의 인기 조합이에요!",
                emotion="excited",
                color=(232, 68, 52),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="튀김 소리가 교향곡 같네요! 바삭한 식감이 살아있을 때 가장 빠르게 서빙해 보이겠습니다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "TW_2_clear": _cutscene(
        cutscene_id="TW_2_clear",
        chapter_id="TW",
        day=2,
        timing="clear",
        title="제4막 TW Day 2 마감: 내일은 32강 월드 포차 그랑프리 결승전!",
        subtitle="타이베이 2일차 돌파! · 불꽃 큐브스테이크 철판 풀세트 예고",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[내일(TW Day 3) 결승 해금] 불꽃 큐브스테이크 철판(Batch Pot) & 갈릭버터 소스 토핑 개방!",
        unlocked_items=["불꽃 큐브스테이크 철판", "불꽃 큐브스테이크 / 갈릭버터 큐브스테이크"],
        lines=[
            _line(
                speaker="메이링",
                speaker_id="chef_tw",
                role="스린 야시장 퀸",
                text="드디어 내일 밤, 월드 포차 그랑프리 최종 결승전이 열립니다! '불꽃 큐브스테이크 철판'까지 모두 개방된 풀세트 대결로 세계 최고의 포차 마스터를 가려봐요!",
                emotion="rival",
                color=(232, 68, 52),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="종로 골목에서 응원하고 있을 단골 학생과 손님들을 위해서라도, 내일 결승전에서 내 모든 영혼을 불태우겠어!",
                emotion="determined",
                color=(255, 208, 68),
            ),
        ],
    ),
    "TW_3_start": _cutscene(
        cutscene_id="TW_3_start",
        chapter_id="TW",
        day=3,
        timing="start",
        title="제4막 TW Day 3: 32강 월드 포차 그랑프리 대망의 결승전!",
        subtitle="타이베이 스린 야시장 중앙 무대 · 김포차 vs 스린 야시장 퀸 메이링",
        illustration=STORY_ILLUSTRATIONS["act2_world_departure"],
        unlock_notice="[월드 그랑프리 결승전] 불꽃 큐브스테이크 철판 포함 전 기구 풀가동! 목표 매출을 달성해 세계 챔피언에 등극하세요!",
        unlocked_items=[
            "불꽃 큐브스테이크 철판 (3인분 대량조리)",
            "갈릭버터 소스 토핑",
            "월드 포차 챔피언 트로피 도전",
        ],
        lines=[
            _line(
                speaker="맛집 유튜버 먹방킹",
                speaker_id="youtuber_vip",
                role="그랑프리 결승 메인 중계",
                text="전 세계 시청자 여러분! 드디어 32강 월드 포차 그랑프리 대망의 결승전입니다! 한국의 '김포차' 마스터와 대만의 '메이링' 마스터가 동시에 철판에 불을 붙였습니다!",
                emotion="excited",
                color=(255, 215, 64),
            ),
            _line(
                speaker="메이링",
                speaker_id="chef_tw",
                role="스린 야시장 퀸",
                text="스린 야시장 최고의 풀코스, 눈 깜짝할 사이에 준비할게! 토치 불쇼로 육즙을 가둔 갈릭버터 큐브스테이크의 진수를 보여드리죠!",
                emotion="rival",
                color=(232, 68, 52),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="종로 포차 달인",
                text="중고 붕어빵 틀 하나로 다시 일어서던 그 겨울밤의 초심을 잊지 않는다! 세계 모든 손님들에게 가장 따뜻한 한 접시를 대접한다!",
                emotion="determined",
                color=(235, 92, 42),
            ),
        ],
    ),
    "TW_3_clear": _cutscene(
        cutscene_id="TW_3_clear",
        chapter_id="TW",
        day=3,
        timing="clear",
        title="그랜드 피날레: 전 세계의 밤을 밝히는 월드 포차 챔피언!",
        subtitle="32강 월드 포차 그랑프리 최종 우승! · 글로벌 야시장 통합 모드 해금",
        illustration=STORY_ILLUSTRATIONS["ending"],
        unlock_notice="[월드 챔피언 등극!] 4개국 모든 마스터(김포차·켄지·디에고·메이링)와 16종 조리기구 자유 조합이 완전 해금되었습니다!",
        unlocked_items=[
            "월드 포차 그랑프리 황금 트로피",
            "스린 야시장 퀸 '메이링' 영입 가능 (야시장 풀코스 스킬)",
            "글로벌 야시장 통합 무한 모드 (16종 기구 자유 커스텀)",
        ],
        lines=[
            _line(
                speaker="맛집 유튜버 먹방킹",
                speaker_id="youtuber_vip",
                role="그랑프리 결승 메인 중계",
                text="종료 벨이 울립니다!! 놀라운 연속 콤보와 완벽한 서빙! 제1회 32강 월드 포차 그랑프리 최종 우승자는... 대한민국 종로 리어카의 기적, 김포차 마스터입니다!!",
                emotion="victory",
                color=(255, 215, 64),
            ),
            _line(
                speaker="메이링",
                speaker_id="chef_tw",
                role="스린 야시장 퀸",
                text="축하해요, 김포차 사장님! 당신의 포차 앞에서는 국적도 언어도 상관없이 모든 손님이 행복한 미소를 짓네요. 저도 이제 당신의 글로벌 포차 팀에 합류할게요!",
                emotion="warm",
                color=(232, 68, 52),
            ),
            _line(
                speaker="켄지 & 디에고",
                speaker_id="chef_jp",
                role="월드 포차 동료 마스터",
                text="오메데토, 김포차! / 브라보 아미고! 이제 한국, 일본, 멕시코, 대만의 16가지 조리 기구를 한자리에 모은 '글로벌 야시장 통합 포차'를 열 시간이군!",
                emotion="excited",
                color=(255, 184, 52),
            ),
            _line(
                speaker="단골 고등학생 민수 & 박 대리",
                speaker_id="student",
                role="종로 단골 손님 대표",
                text="사장님!! 서울 종로에서도 대형 스크린으로 다 같이 응원했어요! 우리 동네 붕어빵 리어카가 진짜 세계 1등이 됐어요!!",
                emotion="excited",
                color=(82, 235, 118),
            ),
            _line(
                speaker="김포차",
                speaker_id="chef_kr",
                role="월드 포차 그랑프리 챔피언",
                text="셔터 내린 식당 앞에서 한숨 쉬던 날, 포기하지 않고 중고 붕어빵 틀 하나를 닦아 불을 지폈던 게 여기까지 왔구나... 어서 와요, 전 세계 손님 여러분! 오늘 밤도 따뜻한 포차는 활짝 열려 있습니다!",
                emotion="victory",
                color=(255, 215, 64),
            ),
        ],
    ),
}

# 엔딩("ending") 및 1막 부활("act1_revival") 별칭 등록, JP/MX/TW Day 4~5 보너스 대사 등록
_RAW_CUTSCENES["ending"] = _cutscene(
    cutscene_id="ending",
    chapter_id="TW",
    day=5,
    timing="ending",
    title=_RAW_CUTSCENES["TW_3_clear"]["title"],
    subtitle=_RAW_CUTSCENES["TW_3_clear"]["subtitle"],
    illustration=STORY_ILLUSTRATIONS["ending"],
    unlock_notice=_RAW_CUTSCENES["TW_3_clear"]["unlock_notice"],
    unlocked_items=_RAW_CUTSCENES["TW_3_clear"]["unlocked_items"],
    lines=_RAW_CUTSCENES["TW_3_clear"]["lines"],
)
_RAW_CUTSCENES["act1_revival"] = _RAW_CUTSCENES["KR_4_start"]
_RAW_CUTSCENES["act2_departure"] = _RAW_CUTSCENES["world_departure"]

for _c_code, _c_chef_id, _c_chef_name, _c_role, _c_color in (
    ("JP", "chef_jp", "켄지", "도톤보리 야타이 장인", (218, 56, 72)),
    ("MX", "chef_mx", "디에고", "살사 아미고", (38, 178, 96)),
    ("TW", "chef_tw", "메이링", "스린 야시장 퀸", (232, 68, 52)),
):
    for _d_extra in (4, 5):
        _start_id = f"{_c_code}_{_d_extra}_start"
        _clear_id = f"{_c_code}_{_d_extra}_clear"
        _RAW_CUTSCENES[_start_id] = _cutscene(
            cutscene_id=_start_id,
            chapter_id=_c_code,
            day=_d_extra,
            timing="start",
            title=f"{_c_code} Day {_d_extra}: {_c_chef_name}와 함께하는 야시장 갈라쇼",
            subtitle=f"{_c_code} 챕터 보너스 영업 Day {_d_extra}",
            illustration=STORY_ILLUSTRATIONS["act2_world_departure"] if _c_code != "TW" else STORY_ILLUSTRATIONS["ending"],
            unlock_notice=f"[{_c_code} Day {_d_extra}] 4대 조리 기구 풀세트로 최고 별점(★★★)과 추가 자금을 획득하세요!",
            lines=[
                _line(
                    speaker=_c_chef_name,
                    speaker_id=_c_chef_id,
                    role=_c_role,
                    text=f"김포차 마스터! 오늘 밤도 우리 야시장에 손님들이 구름처럼 몰려왔어. 환상의 호흡으로 최고 매출 기록을 경신해 보자고!",
                    emotion="excited",
                    color=_c_color,
                ),
                _line(
                    speaker="김포차",
                    speaker_id="chef_kr",
                    role="종로 포차 달인",
                    text="좋아요! 모든 기구 화력 최대로 올리고 오늘 밤도 신나게 달려봅시다!",
                    emotion="determined",
                    color=(235, 92, 42),
                ),
            ],
        )
        _RAW_CUTSCENES[_clear_id] = _cutscene(
            cutscene_id=_clear_id,
            chapter_id=_c_code,
            day=_d_extra,
            timing="clear",
            title=f"{_c_code} Day {_d_extra} 마감: 전설로 남을 야시장의 밤",
            subtitle=f"{_c_code} 챕터 Day {_d_extra} 목표 달성 완료!",
            illustration=STORY_ILLUSTRATIONS["ending"] if (_c_code == "TW" and _d_extra == 5) else STORY_ILLUSTRATIONS["act2_world_departure"],
            unlock_notice=f"[{_c_code} Day {_d_extra} 클리어] 현지 손님들의 열렬한 환호 속에 영업을 성공적으로 마쳤습니다!",
            lines=[
                _line(
                    speaker=_c_chef_name,
                    speaker_id=_c_chef_id,
                    role=_c_role,
                    text="역시 세계를 제패한 포차 마스터다운 솜씨야! 언제든 우리 야시장에 다시 놀러 오라고!",
                    emotion="victory",
                    color=_c_color,
                ),
            ],
        )

# CN, IN, US, RU, BR 신규 5개국 Day 1~5 컷신 등록 (32강 그랑프리 배너 삽화 활용)
for _c_code, _c_chef_id, _c_chef_name, _c_role, _c_color, _c_city in (
    ("CN", "chef_cn_sichuan", "메이화", "사천 화궈 불꽃 여제", (232, 48, 42), "중국 청두·상하이 야시장"),
    ("IN", "chef_in_delhi", "비크람", "올드델리 탄두르 황제", (245, 138, 36), "인도 올드델리·뭄바이 바자르"),
    ("US", "chef_us_texas", "빅 행크", "텍사스 스모크 피트마스터", (68, 128, 232), "미국 뉴욕·텍사스 푸드트럭 파크"),
    ("RU", "chef_ru_moscow", "이반", "모스크바 붉은광장 마스터", (98, 188, 248), "러시아 모스크바·시베리아 야시장"),
    ("BR", "chef_br_rio", "카를로스", "코파카바나 슈하스코 마스터", (42, 188, 88), "브라질 리우·상파울루 페이라"),
):
    for _d_num in range(1, 6):
        _start_id = f"{_c_code}_{_d_num}_start"
        _clear_id = f"{_c_code}_{_d_num}_clear"
        _illust = "assets/story/world_32_masters_banner.png" if _d_num >= 3 else STORY_ILLUSTRATIONS["act2_world_departure"]
        _RAW_CUTSCENES[_start_id] = _cutscene(
            cutscene_id=_start_id,
            chapter_id=_c_code,
            day=_d_num,
            timing="start",
            title=f"{_c_code} Day {_d_num}: {_c_city} — {_c_chef_name}의 도전장",
            subtitle=f"{_c_city} 영업 Day {_d_num}",
            illustration=_illust,
            unlock_notice=str(STORY_PROGRESSION[_c_code][_d_num]["unlock_banner"]),
            lines=[
                _line(
                    speaker=_c_chef_name,
                    speaker_id=_c_chef_id,
                    role=_c_role,
                    text=f"{_c_city}에 온 걸 환영한다! 우리 대륙의 광활한 미식 스케일을 제대로 보여주지. 준비됐나?",
                    emotion="excited",
                    color=_c_color,
                ),
                _line(
                    speaker="김포차",
                    speaker_id="chef_kr",
                    role="종로 포차 달인",
                    text="어떤 거대한 야시장이라도 손님을 향한 따뜻한 정성은 통하는 법이죠! 오늘 영업도 전력으로 갑니다!",
                    emotion="determined",
                    color=(235, 92, 42),
                ),
            ],
        )
        _RAW_CUTSCENES[_clear_id] = _cutscene(
            cutscene_id=_clear_id,
            chapter_id=_c_code,
            day=_d_num,
            timing="clear",
            title=f"{_c_code} Day {_d_num} 마감: {_c_city}의 열광!",
            subtitle=f"{_c_code} 챕터 Day {_d_num} 목표 달성 완료!",
            illustration=STORY_ILLUSTRATIONS["ending"] if (_c_code == "BR" and _d_num >= 3) else _illust,
            unlock_notice=f"[{_c_code} Day {_d_num} 클리어] {_c_chef_name}와 현지 미식가들의 극찬을 받았습니다!",
            lines=[
                _line(
                    speaker=_c_chef_name,
                    speaker_id=_c_chef_id,
                    role=_c_role,
                    text="대단하군! 이토록 완벽한 불 조절과 서빙 속도라니, 우리 지역 마스터들도 모두 당신을 인정했어!",
                    emotion="victory",
                    color=_c_color,
                ),
            ],
        )


# STORY_DIALOGUES 통합 딕셔너리 (플랫 키 조회 및 챕터->일차->타이밍 중첩 조회 모두 지원)
STORY_DIALOGUES: AttrDict = AttrDict()
for _k, _v in _RAW_CUTSCENES.items():
    STORY_DIALOGUES[_k] = _v

for _ch in CHAPTER_ORDER:
    _ch_nested = AttrDict()
    for _day_num in range(1, 6):
        _day_nested = AttrDict(
            {
                "start": _RAW_CUTSCENES[f"{_ch}_{_day_num}_start"],
                "clear": _RAW_CUTSCENES[f"{_ch}_{_day_num}_clear"],
                "pre": _RAW_CUTSCENES[f"{_ch}_{_day_num}_start"],
                "post": _RAW_CUTSCENES[f"{_ch}_{_day_num}_clear"],
                "end": _RAW_CUTSCENES[f"{_ch}_{_day_num}_clear"],
            }
        )
        _ch_nested[_day_num] = _day_nested
        _ch_nested[str(_day_num)] = _day_nested
    STORY_DIALOGUES[_ch] = _ch_nested


# ==============================================================================
# 4. 스토리 진행도 & 컷신 조회 헬퍼 함수
# ==============================================================================
def get_day_progression(
    chapter_id: str,
    day: int = 1,
    mode: str = "WORLD_TOUR",
) -> AttrDict:
    """
    지정된 챕터와 일차(Day)의 스토리 해금 규칙 데이터를 반환한다.
    - 글로벌 무한 모드(GLOBAL_ENDLESS) 또는 1:1 결투 모드에서는 모든 슬롯과 Lv.3 업그레이드가 개방된 상태를 반환한다.
    """
    if str(mode).upper() != "WORLD_TOUR":
        return AttrDict(
            {
                "chapter_id": str(chapter_id).upper(),
                "day": max(1, int(day)),
                "title": f"글로벌 야시장 통합 영업 Day {max(1, int(day))}",
                "subtitle": "전 세계 16종 조리 기구 자유 커스텀 모드",
                "unlocked_slots": ["mold", "dispenser", "grill", "tray", "batch_pot", "skill"],
                "cooking_slots": list(SLOT_TYPES),
                "tray_unlocked": True,
                "toppings_unlocked": True,
                "skill_unlocked": True,
                "shop_unlocked": True,
                "max_station_levels": AttrDict(
                    {
                        "mold": 3,
                        "dispenser": 3,
                        "grill": 3,
                        "batch_pot": 3,
                        "tray": 3,
                    }
                ),
                "unlocked_interiors": list(INTERIOR_UPGRADE_ORDER),
                "special_vip": True,
                "unlock_banner": "[글로벌 야시장 통합 모드] 모든 조리 기구·토핑·스킬이 개방되었습니다!",
                "gameplay_tip": "4개국 최고의 조리 기구 조합으로 최고 매출과 콤보 기록에 도전하세요!",
            }
        )

    cid = str(chapter_id).upper()
    if cid not in STORY_PROGRESSION:
        cid = "KR"
    ch_prog = STORY_PROGRESSION[cid]
    clamped_day = max(1, min(5, int(day)))
    return ch_prog[clamped_day]


def get_unlocked_slots(
    chapter_id: str,
    day: int = 1,
    mode: str = "WORLD_TOUR",
) -> List[str]:
    """
    현재 챕터와 일차에서 해금된 슬롯/기능 식별자 리스트를 반환한다.
    예:
    - KR Day 1: ["mold"]
    - KR Day 2: ["mold", "dispenser"]
    - KR Day 3: ["mold", "dispenser", "grill", "tray"]
    - KR Day 4+: ["mold", "dispenser", "grill", "tray", "batch_pot", "skill"]
    - JP/MX/TW Day 1: ["mold", "dispenser", "tray", "skill"]
    - JP/MX/TW Day 2: ["mold", "dispenser", "tray", "grill", "skill"]
    - JP/MX/TW Day 3+: ["mold", "dispenser", "tray", "grill", "batch_pot", "skill"]
    """
    prog = get_day_progression(chapter_id, day, mode=mode)
    return list(prog["unlocked_slots"])


def get_unlocked_cooking_slots(
    chapter_id: str,
    day: int = 1,
    mode: str = "WORLD_TOUR",
) -> List[str]:
    """4대 조리 기구 슬롯('mold', 'grill', 'batch_pot', 'dispenser') 중 현재 해금된 슬롯만 반환한다."""
    unlocked = set(get_unlocked_slots(chapter_id, day, mode=mode))
    return [slot for slot in SLOT_TYPES if slot in unlocked]


def is_slot_unlocked(
    chapter_id: str,
    day: int,
    slot_type: str,
    mode: str = "WORLD_TOUR",
) -> bool:
    """특정 슬롯('mold', 'grill', 'batch_pot', 'dispenser', 'tray', 'skill')의 해금 여부를 반환한다."""
    return str(slot_type) in get_unlocked_slots(chapter_id, day, mode=mode)


def get_max_station_upgrade_level(
    chapter_id: str,
    day: int,
    slot_type: str,
    mode: str = "WORLD_TOUR",
) -> int:
    """
    스토리 진행 단계에 따라 상점에서 강화 가능한 해당 기구 슬롯의 최대 레벨(0~3)을 반환한다.
    - 'mold' 또는 'mold_upgrade' 형태 모두 지원한다.
    """
    if str(mode).upper() != "WORLD_TOUR":
        return 3

    prog = get_day_progression(chapter_id, day, mode=mode)
    norm_key = normalize_station_upgrade_key(slot_type)
    short_key = norm_key.replace("_upgrade", "")
    levels_map = prog.get("max_station_levels", {})
    return int(levels_map.get(short_key, 3))


def get_unlocked_interiors(
    chapter_id: str,
    day: int = 1,
    mode: str = "WORLD_TOUR",
) -> List[str]:
    """현재 챕터와 일차에서 구매 가능한 포차 인테리어 업그레이드 ID 리스트를 반환한다."""
    prog = get_day_progression(chapter_id, day, mode=mode)
    return list(prog.get("unlocked_interiors", INTERIOR_UPGRADE_ORDER))


def get_story_cutscene(
    chapter_id: str,
    day: int = 1,
    timing: str = "start",
) -> Optional[AttrDict]:
    """
    챕터 ID, 일차(Day), 타이밍('start' | 'clear' | 'prologue' | 'ending' | 'world_departure')에 해당하는
    스토리 컷신 데이터(AttrDict)를 반환한다.
    """
    cid_raw = str(chapter_id).strip()
    cid_lower = cid_raw.lower()
    timing_lower = str(timing).strip().lower()

    # 특수 컷신 키 처리
    if cid_lower == "prologue" or timing_lower == "prologue" or (cid_raw.upper() == "KR" and int(day) <= 0):
        return STORY_DIALOGUES["prologue"]
    if cid_lower in ("ending", "grand_finale") or timing_lower == "ending":
        return STORY_DIALOGUES["ending"]
    if cid_lower in ("world_departure", "act2_departure") or timing_lower == "world_departure":
        return STORY_DIALOGUES["world_departure"]
    if cid_lower in STORY_DIALOGUES and not isinstance(STORY_DIALOGUES[cid_lower], dict):
        return STORY_DIALOGUES[cid_lower]
    if cid_raw in _RAW_CUTSCENES:
        return _RAW_CUTSCENES[cid_raw]

    # 일반 챕터 + 일차 + 타이밍 정규화
    norm_timing = "clear" if timing_lower in ("clear", "end", "after", "outro", "post", "complete", "win", "result") else "start"
    cid_upper = cid_raw.upper()
    if cid_upper not in CHAPTER_ORDER:
        return None

    clamped_day = max(1, min(5, int(day)))
    flat_key = f"{cid_upper}_{clamped_day}_{norm_timing}"
    return STORY_DIALOGUES.get(flat_key)


def get_tournament_drama(round_key: str) -> Optional[AttrDict]:
    """32강 월드 포차 그랑프리 라운드 키('round_32', 'round_16', 'quarterfinal', 'semifinal', 'final')의 드라마 데이터를 반환한다."""
    return TOURNAMENT_DRAMA.get(round_key)
