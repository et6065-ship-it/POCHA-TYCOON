extends Control
class_name BungeoTycoon

# ==============================================================================
# 🐟 전설의 붕어빵 타이쿤 : 포차에서 빌딩까지 (Godot 4.x 세로 9:16 수직 4단계 레이아웃 코어)
# - 기준 해상도: 1080×1920 (9:16 베이스, 9:19.5~9:21 상하 배경 V-Stretch 대응)
# - 수직 4단계 황금비율 (10% / 25% / 25% / 40%):
#   1. Zone1_HUD (0% ~ 10%): 매출, 목표 달성률, 콤보, 정적 모달 버튼
#   2. Zone2_CustomerQueue (10% ~ 35%): 손님 3명 대기, 주문 말풍선, 인내심 게이지
#   3. Zone3_ServingStackRack (35% ~ 60%): 구워진 붕어빵 스택 & 포장대 (탭/플릭 오토 타겟팅 서빙)
#   4. Zone4_ThumbCookingZone (60% ~ 100%): 블록형 그리드 주물틀(2×2, 3×2, 3×3) + 반죽/앙금 + 우측 하단 모서리 고정 쓰레기통
# ==============================================================================

const VERTICAL_STAGE_RATIOS := {
	"zone1_hud": Vector2(0.0, 0.10),           # 10%
	"zone2_customers": Vector2(0.10, 0.35),    # 25%
	"zone3_serving_rack": Vector2(0.35, 0.60), # 25%
	"zone4_thumb_cooking": Vector2(0.60, 1.00) # 40%
}

# 가로 나열(1×6) 금지 -> 엄지 터치 판정 박스(최소 48×48dp / 140px 이상)를 위한 블록형 그리드 배치
const MOLD_TIERS := [
	{"id": 0, "name": "할머니의 4구(2×2) 블록 주물틀", "slots": 4, "cols": 2, "rows": 2, "cost": 0, "cook_time": 4.0, "burn_grace": 6.8, "double_yield": false, "price_mult": 1.0},
	{"id": 1, "name": "양면 회전 6구(3×2) 블록 주물기계", "slots": 6, "cols": 3, "rows": 2, "cost": 15000, "cook_time": 3.5, "burn_grace": 7.5, "double_yield": false, "price_mult": 1.0},
	{"id": 2, "name": "정통 9구(3×3) 고화력 블록 주물틀", "slots": 9, "cols": 3, "rows": 3, "cost": 45000, "cook_time": 3.0, "burn_grace": 8.2, "double_yield": false, "price_mult": 1.0},
	{"id": 3, "name": "테플론 황동 9구(3×3) 명품틀", "slots": 9, "cols": 3, "rows": 3, "cost": 120000, "cook_time": 2.3, "burn_grace": 14.0, "double_yield": false, "price_mult": 1.15},
	{"id": 4, "name": "황금 잉어빵 2배 대량생산 9구틀", "slots": 9, "cols": 3, "rows": 3, "cost": 280000, "cook_time": 2.0, "burn_grace": 15.0, "double_yield": true, "price_mult": 1.25},
	{"id": 5, "name": "크로아상 붕어빵(크로붕) 프레스 9구틀", "slots": 9, "cols": 3, "rows": 3, "cost": 600000, "cook_time": 1.7, "burn_grace": 18.0, "double_yield": true, "price_mult": 1.60}
]

const FILLINGS := [
	{"key": "pat", "name": "통단팥", "base_price": 1000, "unlock_cost": 0, "color": Color("#7c2d12")},
	{"key": "shu", "name": "슈크림", "base_price": 1300, "unlock_cost": 5000, "color": Color("#facc15")},
	{"key": "pizza", "name": "피자치즈", "base_price": 1800, "unlock_cost": 18000, "color": Color("#ef4444")},
	{"key": "goguma", "name": "꿀고구마", "base_price": 2200, "unlock_cost": 40000, "color": Color("#a855f7")},
	{"key": "seed", "name": "씨앗흑당", "base_price": 2600, "unlock_cost": 85000, "color": Color("#b45309")},
	{"key": "hallabong", "name": "한라봉크림", "base_price": 3200, "unlock_cost": 160000, "color": Color("#fb923c")}
]

const REGIONS := [
	{"id": 0, "name": "⛺ 역전 앞 바람 부는 골목", "unlock_cost": 0, "price_mult": 1.0, "spawn_interval": 4.2, "patience": 22.0, "requires_permit": false},
	{"id": 1, "name": "🚚 서울 강남·여의도 빌딩숲", "unlock_cost": 120000, "price_mult": 1.35, "spawn_interval": 3.4, "patience": 17.0, "requires_permit": true},
	{"id": 2, "name": "🎸 서울 홍대·성수 팝업거리", "unlock_cost": 180000, "price_mult": 1.50, "spawn_interval": 3.1, "patience": 19.0, "requires_permit": true},
	{"id": 3, "name": "⛷️ 강원 평창·속초 눈꽃 스키장", "unlock_cost": 260000, "price_mult": 1.75, "spawn_interval": 3.0, "patience": 21.0, "requires_permit": true},
	{"id": 4, "name": "🌊 부산 해운대·남포동 야시장", "unlock_cost": 380000, "price_mult": 2.00, "spawn_interval": 2.7, "patience": 19.0, "requires_permit": true},
	{"id": 5, "name": "🍊 제주 애월 해안도로 노을마켓", "unlock_cost": 520000, "price_mult": 2.35, "spawn_interval": 2.5, "patience": 23.0, "requires_permit": true}
]

const BUILDING_FLOORS := [
	{"floor": 1, "name": "1F 황금붕어 플래그십 본점 오픈", "cost": 250000, "royalty_per_sec": 0},
	{"floor": 2, "name": "2F 발효 반죽 & 앙금 R&D 연구소", "cost": 450000, "royalty_per_sec": 0},
	{"floor": 3, "name": "3F 전국 가맹본부 오피스 (자동 로열티)", "cost": 750000, "royalty_per_sec": 2500},
	{"floor": 4, "name": "4F 스카이 라운지 디저트 카페", "cost": 1200000, "royalty_per_sec": 6000},
	{"floor": 5, "name": "5F 루프탑 황금 붕어 동상 완공 (최종 엔딩)", "cost": 2000000, "royalty_per_sec": 15000}
]

const STORY_IMAGES := {
	"ep1_prologue": "res://assets/story_bungeo/bungeo_ep1_prologue_cart.jpg",
	"ep1_5_crackdown": "res://assets/story_bungeo/bungeo_ep1_5_crackdown_crisis.jpg",
	"ep1_8_permit": "res://assets/story_bungeo/bungeo_ep1_8_official_permit.jpg",
	"ep2_5_mold": "res://assets/story_bungeo/bungeo_ep2_5_mold_craft_upgrade.jpg",
	"ep2_gangnam": "res://assets/story_bungeo/bungeo_ep2_foodtruck_gangnam.jpg",
	"ep3_tour": "res://assets/story_bungeo/bungeo_ep3_nationwide_tour.jpg",
	"ep4_ending": "res://assets/story_bungeo/bungeo_ep4_building_ending.jpg"
}

var cash: int = 3000
var mold_tier: int = 0
var has_permit: bool = false
var building_floor: int = 0
var trash_mode: bool = false
var warmer_stock := {"pat": 0, "shu": 0, "pizza": 0, "goguma": 0, "seed": 0, "hallabong": 0}

func _ready() -> void:
	print("[BungeoTycoon Godot 4] 세로 9:16 수직 4단계 레이아웃(10%/25%/25%/40%) 코어 로드 완료!")
