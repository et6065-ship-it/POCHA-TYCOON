class_name PixelSpriteGenerator
extends RefCounted
## Godot 4 전용 48x48 초고밀도 도트 스프라이트 렌더러 (Image.set_pixel -> ImageTexture)
## - 장기의 '쫄(졸/병 - SOLDIER)' 4대 중세 국가별(고려/템플러/비잔틴/맘루크) 정예 방패창보병 도트 아키텍처
## - 1px 검은색 도트 아웃라인 + 11x11 도트 한자(卒/兵 등) 팔각 장기알 페데스탈
## - 5단계 도트 프레임 애니메이션: IDLE(4), MOVE(4), ATTACK(4, 도트 찌르기 잔상), HIT(2), DEATH(4)

enum Side { CHU, HAN }
enum PieceType { KING, CHARIOT, CANNON, HORSE, ELEPHANT, GUARD, SOLDIER }
enum Faction { GORYEO, TEMPLAR, BYZANTINE, MAMLUK }
enum AnimState { IDLE, MOVE, ATTACK, HIT, DEATH }

const CANVAS_SIZE := 48
const OUTLINE_COLOR := Color("#080b12")

# 텍스처 캐시: key = "%d_%d_%d_%d_%d" % [piece_type, side, faction, anim_state, frame]
static var _tex_cache: Dictionary = {}

# 11x11 도트 한자 비트맵 (장기알 받침대 각인용)
const HANJA_11X11 := {
	"卒": [
		"00000100000",
		"01111111110",
		"00010001000",
		"00110001100",
		"01001010010",
		"00000100000",
		"11111111111",
		"00000100000",
		"00000100000",
		"00000100000",
		"00000100000"
	],
	"兵": [
		"00011111100",
		"00100000000",
		"00111111100",
		"00100100100",
		"00100100100",
		"11111111111",
		"00010001000",
		"00100000100",
		"01000000010",
		"10000000001",
		"00000000000"
	],
	"楚": [
		"00100000100",
		"11111011111",
		"00100000100",
		"01110001110",
		"00000100000",
		"01111111110",
		"00000100000",
		"00100111100",
		"00110100000",
		"01001111110",
		"10000000000"
	],
	"漢": [
		"01001111110",
		"00100010100",
		"10001111110",
		"01001001010",
		"00101111110",
		"00000010000",
		"01011111110",
		"01000010000",
		"10011111110",
		"10000101000",
		"00011000110"
	],
	"車": [
		"00000100000",
		"01111111110",
		"00100100100",
		"00111111100",
		"00100100100",
		"00111111100",
		"00000100000",
		"11111111111",
		"00000100000",
		"00000100000",
		"00000100000"
	],
	"包": [
		"00010000000",
		"00111111110",
		"01000000010",
		"10011110010",
		"00010010010",
		"00011110010",
		"00010000110",
		"00010000000",
		"00010000010",
		"00001111110",
		"00000000000"
	],
	"馬": [
		"01111111100",
		"01000100000",
		"01111111000",
		"01000100000",
		"01111111000",
		"01000000010",
		"01111111110",
		"00000000010",
		"10101010010",
		"10101010110",
		"00000000000"
	],
	"象": [
		"00011110000",
		"00100010000",
		"01111111100",
		"01001000100",
		"01111111100",
		"00011100000",
		"01101011000",
		"10010100100",
		"01100101000",
		"10001100110",
		"00000000000"
	],
	"士": [
		"00000100000",
		"00000100000",
		"00000100000",
		"11111111111",
		"00000100000",
		"00000100000",
		"00000100000",
		"00000100000",
		"01111111110",
		"00000000000",
		"00000000000"
	]
}

static func get_frame_count(anim_state: int) -> int:
	match anim_state:
		AnimState.IDLE: return 4
		AnimState.MOVE: return 4
		AnimState.ATTACK: return 4
		AnimState.HIT: return 2
		AnimState.DEATH: return 4
	return 4

static func get_sprite_texture(piece_type: int, side: int, faction: int, anim_state: int, frame: int) -> ImageTexture:
	var f_cnt := get_frame_count(anim_state)
	var f_idx := posmod(frame, f_cnt)
	var key := "%d_%d_%d_%d_%d" % [piece_type, side, faction, anim_state, f_idx]
	if _tex_cache.has(key):
		return _tex_cache[key]

	var img := Image.create(CANVAS_SIZE, CANVAS_SIZE, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))

	# 1. 팔각 장기알 도트 페데스탈 + 11x11 한자 각인 렌더링
	_draw_pedestal(img, piece_type, side)

	# 2. 기물 본체 도트 렌더링
	if piece_type == PieceType.SOLDIER:
		_draw_soldier_pixel_art(img, side, faction, anim_state, f_idx)
	else:
		_draw_other_piece_pixel_art(img, piece_type, side, faction, anim_state, f_idx)

	# 3. 1px 외곽 검은색 도트 아웃라인 적용 (투명 픽셀과 맞닿은 경계)
	_apply_pixel_outline(img)

	# 4. 공격/피격 이펙트(잔상, 스파크)는 아웃라인 위에 선명하게 덧그리기
	if piece_type == PieceType.SOLDIER:
		_draw_soldier_fx_overlay(img, side, faction, anim_state, f_idx)
	elif anim_state == AnimState.ATTACK and f_idx == 2:
		_draw_generic_attack_smear(img, side)

	var tex := ImageTexture.create_from_image(img)
	_tex_cache[key] = tex
	return tex

# --- 픽셀 드로잉 유틸리티 ---
static func _pset(img: Image, x: int, y: int, col: Color) -> void:
	if x >= 0 and x < CANVAS_SIZE and y >= 0 and y < CANVAS_SIZE:
		img.set_pixel(x, y, col)

static func _prect(img: Image, x: int, y: int, w: int, h: int, col: Color) -> void:
	for py in range(y, y + h):
		for px in range(x, x + w):
			_pset(img, px, py, col)

static func _pline(img: Image, x0: int, y0: int, x1: int, y1: int, col: Color) -> void:
	var dx := absi(x1 - x0)
	var sx := 1 if x0 < x1 else -1
	var dy := -absi(y1 - y0)
	var sy := 1 if y0 < y1 else -1
	var err := dx + dy
	var cx := x0
	var cy := y0
	while true:
		_pset(img, cx, cy, col)
		if cx == x1 and cy == y1:
			break
		var e2 := 2 * err
		if e2 >= dy:
			err += dy
			cx += sx
		if e2 <= dx:
			err += dx
			cy += sy

# --- 1. 팔각 장기알 도트 받침대 & 11x11 도트 한자 각인 ---
static func _draw_pedestal(img: Image, piece_type: int, side: int) -> void:
	var wood_top := Color("#c28e5c")
	var wood_mid := Color("#9c6638")
	var wood_dark := Color("#694121")
	var team_rim := Color("#10b981") if side == Side.CHU else Color("#ef4444")
	var team_glow := Color("#34d399") if side == Side.CHU else Color("#f87171")

	# 장기알 상판 & 입체 측면 (y: 33 ~ 45)
	for y in range(33, 46):
		var dy := y - 33
		var half_w := 17
		if dy == 0 or dy == 12:
			half_w = 11
		elif dy == 1 or dy == 11:
			half_w = 14
		elif dy == 2 or dy == 10:
			half_w = 16

		for x in range(24 - half_w, 24 + half_w):
			if dy <= 2:
				_pset(img, x, y, wood_top if (x + y) % 5 != 0 else wood_mid)
			elif dy == 3:
				_pset(img, x, y, team_rim if x % 2 == 0 else team_glow)
			elif dy <= 9:
				# 전면 한자 각인 판 영역
				_pset(img, x, y, wood_mid if x < 30 else wood_dark)
			else:
				_pset(img, x, y, wood_dark)

	# 팔각 모서리 금장 스터드
	_pset(img, 10, 35, Color("#facc15"))
	_pset(img, 37, 35, Color("#facc15"))
	_pset(img, 10, 43, Color("#b45309"))
	_pset(img, 37, 43, Color("#b45309"))

	# 11x11 한자 글리프 선택 (우측 하단 또는 받침대 중앙 인장)
	var hanja_key := "卒"
	match piece_type:
		PieceType.SOLDIER:
			hanja_key = "卒" if side == Side.CHU else "兵"
		PieceType.KING:
			hanja_key = "楚" if side == Side.CHU else "漢"
		PieceType.CHARIOT:
			hanja_key = "車"
		PieceType.CANNON:
			hanja_key = "包"
		PieceType.HORSE:
			hanja_key = "馬"
		PieceType.ELEPHANT:
			hanja_key = "象"
		PieceType.GUARD:
			hanja_key = "士"

	# 우측 상단 미니 한자 인장 배지 (13x13 씰 + 내부 11x11 도트 한자)
	var bx := 35
	var by := 1
	_prect(img, bx, by, 11, 11, Color("#111827"))
	var glyph: Array = HANJA_11X11.get(hanja_key, HANJA_11X11["卒"])
	var ink_col := Color("#34d399") if side == Side.CHU else Color("#f87171")
	for gy in range(11):
		var row_str: String = glyph[gy]
		for gx in range(11):
			if row_str[gx] == "1":
				_pset(img, bx + gx, by + gy, ink_col)

# --- 2. '쫄(SOLDIER)' 4대 중세 국가별 초고밀도 도트 스프라이트 ---
static func _draw_soldier_pixel_art(img: Image, _side: int, faction: int, anim_state: int, frame: int) -> void:
	# 모션 상태별 오프셋 계산
	var bob_y := 0
	var body_dx := 0
	var leg_l_dy := 0
	var leg_r_dy := 0
	var shield_dx := 0
	var shield_dy := 0
	var weapon_dx := 0
	var weapon_dy := 0
	var plume_dx := 0

	match anim_state:
		AnimState.IDLE:
			bob_y = -1 if (frame == 1 or frame == 2) else 0
			plume_dx = 1 if (frame == 2 or frame == 3) else 0
			weapon_dy = -1 if frame == 2 else 0
		AnimState.MOVE:
			bob_y = -1 if (frame % 2 == 1) else 0
			body_dx = 1 if (frame == 1 or frame == 2) else 0
			leg_l_dy = -2 if frame == 1 else (1 if frame == 3 else 0)
			leg_r_dy = -2 if frame == 3 else (1 if frame == 1 else 0)
			shield_dx = 1
			weapon_dx = 1 if (frame % 2 == 1) else 0
		AnimState.ATTACK:
			if frame == 0: # 방패 밀치기 준비 & 창 뒤로 당김
				body_dx = -2
				shield_dx = 1
				weapon_dx = -3
			elif frame == 1: # 방패 강타 (Shield Bash)
				body_dx = 1
				shield_dx = 4
				shield_dy = -1
				weapon_dx = -1
			elif frame == 2: # 전방 전력 찌르기 (Full Spear/Blade Thrust)
				body_dx = 3
				shield_dx = -1
				weapon_dx = 7
			else: # 잔심 & 회수
				body_dx = 1
				weapon_dx = 3
		AnimState.HIT:
			body_dx = -3 if frame == 0 else -2
			bob_y = 1
			shield_dx = 2
			shield_dy = -2
			weapon_dx = -2
		AnimState.DEATH:
			if frame >= 2:
				_draw_soldier_death_fragments(img, faction, frame)
				return
			body_dx = -3 * (frame + 1)
			bob_y = 3 * (frame + 1)
			shield_dx = -4 * (frame + 1)
			shield_dy = 2 * (frame + 1)
			weapon_dy = 4 * (frame + 1)

	var cx := 22 + body_dx
	var cy := 22 + bob_y

	match faction:
		Faction.GORYEO:
			_draw_goryeo_soldier(img, cx, cy, leg_l_dy, leg_r_dy, shield_dx, shield_dy, weapon_dx, weapon_dy, plume_dx, anim_state, frame)
		Faction.TEMPLAR:
			_draw_templar_soldier(img, cx, cy, leg_l_dy, leg_r_dy, shield_dx, shield_dy, weapon_dx, weapon_dy, plume_dx, anim_state, frame)
		Faction.BYZANTINE:
			_draw_byzantine_soldier(img, cx, cy, leg_l_dy, leg_r_dy, shield_dx, shield_dy, weapon_dx, weapon_dy, plume_dx, anim_state, frame)
		Faction.MAMLUK:
			_draw_mamluk_soldier(img, cx, cy, leg_l_dy, leg_r_dy, shield_dx, shield_dy, weapon_dx, weapon_dy, plume_dx, anim_state, frame)

# 2-A. 고려 천군 (GORYEO): 첨주(붉은 술 철제 투구) + 감청/흑칠 두정갑(금색 스터드) + 삼족오 팽배 + 장창
static func _draw_goryeo_soldier(img: Image, cx: int, cy: int, ll_dy: int, lr_dy: int, sh_dx: int, sh_dy: int, wp_dx: int, wp_dy: int, pl_dx: int, anim_state: int, frame: int) -> void:
	# [다리 & 군화]
	_prect(img, cx - 5, cy + 9 + ll_dy, 4, 4, Color("#1e293b"))
	_prect(img, cx - 5, cy + 11 + ll_dy, 4, 2, Color("#0f172a"))
	_prect(img, cx + 1, cy + 9 + lr_dy, 4, 4, Color("#1e293b"))
	_prect(img, cx + 1, cy + 11 + lr_dy, 4, 2, Color("#0f172a"))

	# [두정갑 몸통 (감청/흑칠 브리간딘 + 금색 징 Studs)]
	_prect(img, cx - 6, cy - 2, 12, 11, Color("#172554"))
	_prect(img, cx - 5, cy - 1, 10, 9, Color("#1e3a8a"))
	# 붉은 내의 자락
	_prect(img, cx - 6, cy + 8, 12, 1, Color("#dc2626"))
	# 금색 두정(Rivet Studs) 도트
	for sy in [cy, cy + 3, cy + 6]:
		for sx in [cx - 4, cx - 1, cx + 2, cx + 4]:
			_pset(img, sx, sy, Color("#facc15"))
	# 허리띠(전대)와 금버클
	_prect(img, cx - 6, cy + 4, 12, 2, Color("#78350f"))
	_prect(img, cx - 1, cy + 4, 2, 2, Color("#fbbf24"))

	# [투구 (고려 첨주 + 드림 + 붉은 상모 술)]
	# 붉은 말총 술 (Plume)
	_prect(img, cx - 5 + pl_dx, cy - 15, 5, 3, Color("#dc2626"))
	_prect(img, cx - 6 + pl_dx, cy - 14, 3, 4, Color("#991b1b"))
	_pset(img, cx - 2 + pl_dx, cy - 15, Color("#f87171"))
	# 첨주 꼭대기 금장 보주
	_prect(img, cx - 1, cy - 13, 2, 2, Color("#facc15"))
	# 철제 투구 본체 (3단 명암)
	_prect(img, cx - 4, cy - 11, 8, 5, Color("#475569"))
	_prect(img, cx - 3, cy - 11, 5, 4, Color("#94a3b8"))
	_prect(img, cx - 2, cy - 10, 2, 2, Color("#e2e8f0")) # 하이라이트
	# 금장 투구 챙
	_prect(img, cx - 5, cy - 7, 10, 1, Color("#f59e0b"))
	# 안면 & 드림(목가리개)
	_prect(img, cx - 3, cy - 6, 6, 4, Color("#fdba74"))
	_pset(img, cx - 2, cy - 5, Color("#0f172a")) # 눈
	_pset(img, cx + 1, cy - 5, Color("#0f172a")) # 눈
	_prect(img, cx - 3, cy - 3, 6, 1, Color("#1e293b")) # 수염/턱가드
	_prect(img, cx - 5, cy - 6, 2, 5, Color("#1e3a8a")) # 좌측 드림
	_prect(img, cx + 3, cy - 6, 2, 5, Color("#1e3a8a")) # 우측 드림
	_pset(img, cx - 4, cy - 4, Color("#facc15"))
	_pset(img, cx + 4, cy - 4, Color("#facc15"))

	# [오른손 무기: 장창 (공격 시 수평 돌격창, 평소 사선/수직)]
	var wx := cx + 6 + wp_dx
	var wy := cy + wp_dy
	if anim_state == AnimState.ATTACK and frame >= 1:
		# 수평 찌르기 자세
		_prect(img, cx - 4, wy, 16 + wp_dx, 2, Color("#92400e")) # 창대
		_prect(img, cx + 10 + wp_dx, wy - 1, 2, 4, Color("#dc2626")) # 붉은 영자(술)
		_prect(img, cx + 12 + wp_dx, wy - 1, 6, 3, Color("#cbd5e1")) # 창날
		_prect(img, cx + 14 + wp_dx, wy, 5, 1, Color("#ffffff")) # 창끝 하이라이트
	else:
		# 방진 수직/사선 파지 자세
		_prect(img, wx, wy - 12, 2, 22, Color("#92400e"))
		_pset(img, wx, wy - 6, Color("#b45309"))
		# 붉은 영자(Tassel)
		_prect(img, wx - 2, wy - 13, 4, 2, Color("#dc2626"))
		_pset(img, wx - 2, wy - 11, Color("#991b1b"))
		# 강철 창날 (3단 명암)
		_prect(img, wx - 1, wy - 18, 3, 5, Color("#94a3b8"))
		_prect(img, wx, wy - 20, 2, 7, Color("#e2e8f0"))
		_pset(img, wx, wy - 21, Color("#ffffff"))

	# [왼손 방패: 고려 팽배 (삼족오/호랑이 금빛 문양)]
	var sx := cx - 9 + sh_dx
	var sy := cy - 3 + sh_dy
	_prect(img, sx, sy, 8, 12, Color("#0f172a")) # 철제 테두리
	_prect(img, sx + 1, sy + 1, 6, 10, Color("#1e3a8a")) # 감청색 방패면
	# 네 모서리 금장 리벳
	_pset(img, sx + 1, sy + 1, Color("#facc15"))
	_pset(img, sx + 6, sy + 1, Color("#facc15"))
	_pset(img, sx + 1, sy + 10, Color("#facc15"))
	_pset(img, sx + 6, sy + 10, Color("#facc15"))
	# 중앙 황금 삼족오 엠블럼
	_prect(img, sx + 3, sy + 3, 2, 6, Color("#facc15"))
	_prect(img, sx + 2, sy + 4, 4, 3, Color("#fde047"))
	_pset(img, sx + 2, sy + 8, Color("#f59e0b"))
	_pset(img, sx + 5, sy + 8, Color("#f59e0b"))

# 2-B. 성전 기사단 (TEMPLAR): T자 바이저 그레이트헬름 + 백색 십자가 서코트 + 카이트 실드 + 할버드 창
static func _draw_templar_soldier(img: Image, cx: int, cy: int, ll_dy: int, lr_dy: int, sh_dx: int, sh_dy: int, wp_dx: int, wp_dy: int, _pl_dx: int, anim_state: int, frame: int) -> void:
	# [사슬/철갑 그리브 군화]
	_prect(img, cx - 5, cy + 9 + ll_dy, 4, 4, Color("#475569"))
	_prect(img, cx - 5, cy + 11 + ll_dy, 4, 2, Color("#94a3b8"))
	_prect(img, cx + 1, cy + 9 + lr_dy, 4, 4, Color("#475569"))
	_prect(img, cx + 1, cy + 11 + lr_dy, 4, 2, Color("#94a3b8"))

	# [사슬갑옷 + 백색 서코트(Surcoat) + 붉은 성전 십자가]
	_prect(img, cx - 6, cy - 2, 12, 11, Color("#64748b")) # 사슬 소매/밑단
	_prect(img, cx - 5, cy - 2, 10, 10, Color("#e2e8f0")) # 백색 서코트
	_prect(img, cx - 4, cy - 1, 8, 8, Color("#f8fafc"))
	# 가슴의 붉은 성전 십자가
	_prect(img, cx, cy - 1, 2, 8, Color("#dc2626"))
	_prect(img, cx - 3, cy + 1, 8, 2, Color("#dc2626"))
	# 가죽 벨트
	_prect(img, cx - 5, cy + 5, 10, 1, Color("#451a03"))
	_pset(img, cx, cy + 5, Color("#facc15"))

	# [크루세이더 그레이트 헬름 (황동 십자 마스크 + T자 눈구멍)]
	_prect(img, cx - 4, cy - 12, 8, 10, Color("#64748b"))
	_prect(img, cx - 3, cy - 12, 6, 9, Color("#94a3b8"))
	_prect(img, cx - 2, cy - 11, 3, 3, Color("#e2e8f0")) # 정수리 광택
	# 황동 십자 전면 장식
	_prect(img, cx, cy - 10, 2, 7, Color("#f59e0b"))
	_prect(img, cx - 3, cy - 8, 8, 2, Color("#facc15"))
	# 검은색 T자 아이슬릿(눈구멍)
	_prect(img, cx - 3, cy - 8, 3, 1, Color("#090d16"))
	_prect(img, cx + 1, cy - 8, 3, 1, Color("#090d16"))

	# [오른손 무기: 성전사 할버드 / 폴암]
	var wx := cx + 6 + wp_dx
	var wy := cy + wp_dy
	if anim_state == AnimState.ATTACK and frame >= 1:
		_prect(img, cx - 4, wy, 16 + wp_dx, 2, Color("#78350f"))
		_prect(img, cx + 10 + wp_dx, wy - 3, 4, 6, Color("#cbd5e1")) # 도끼날
		_prect(img, cx + 13 + wp_dx, wy - 1, 6, 3, Color("#ffffff")) # 창끝
	else:
		_prect(img, wx, wy - 12, 2, 22, Color("#78350f"))
		# 할버드 도끼날 + 상단 창날
		_prect(img, wx - 3, wy - 16, 4, 5, Color("#94a3b8"))
		_prect(img, wx - 4, wy - 17, 2, 7, Color("#e2e8f0"))
		_prect(img, wx, wy - 21, 2, 9, Color("#f8fafc"))
		_pset(img, wx + 2, wy - 15, Color("#cbd5e1")) # 후면 부리

	# [왼손 방패: 카이트 실드 (백색 바탕 + 적십자 + 강철 테두리)]
	var sx := cx - 9 + sh_dx
	var sy := cy - 3 + sh_dy
	_prect(img, sx, sy, 8, 10, Color("#64748b"))
	_prect(img, sx + 1, sy + 10, 6, 2, Color("#64748b"))
	_prect(img, sx + 2, sy + 12, 4, 1, Color("#64748b"))
	_prect(img, sx + 1, sy + 1, 6, 9, Color("#f8fafc"))
	_prect(img, sx + 2, sy + 10, 4, 2, Color("#e2e8f0"))
	# 방패 적십자
	_prect(img, sx + 3, sy + 1, 2, 10, Color("#dc2626"))
	_prect(img, sx + 1, sy + 4, 6, 2, Color("#dc2626"))

# 2-C. 비잔틴 제국군 (BYZANTINE): 황금 볏 원뿔 철모 + 황금 비늘갑옷(Klivanion) & 자색 망토 + 쌍두독수리 스쿠톤 방패
static func _draw_byzantine_soldier(img: Image, cx: int, cy: int, ll_dy: int, lr_dy: int, sh_dx: int, sh_dy: int, wp_dx: int, wp_dy: int, pl_dx: int, anim_state: int, frame: int) -> void:
	# [자색 황실 망토 (등 뒤)]
	_prect(img, cx - 7, cy - 2, 14, 11, Color("#581c87"))
	_prect(img, cx - 6, cy - 1, 12, 9, Color("#7e22ce"))

	# [다리 & 금장 정강이받이]
	_prect(img, cx - 5, cy + 9 + ll_dy, 4, 4, Color("#b45309"))
	_prect(img, cx - 4, cy + 9 + ll_dy, 2, 3, Color("#facc15"))
	_prect(img, cx + 1, cy + 9 + lr_dy, 4, 4, Color("#b45309"))
	_prect(img, cx + 2, cy + 9 + lr_dy, 2, 3, Color("#facc15"))

	# [황금 비늘갑옷 (Klivanion - 체커보드 도트 스케일)]
	_prect(img, cx - 5, cy - 2, 10, 10, Color("#92400e"))
	for py in range(cy - 1, cy + 7):
		for px in range(cx - 4, cx + 4):
			var is_light := ((px + py) % 2 == 0)
			_pset(img, px, py, Color("#facc15") if is_light else Color("#d97706"))
	# 자색 어깨 장식
	_prect(img, cx - 6, cy - 2, 12, 2, Color("#9333ea"))

	# [비잔틴 황금 볏 원뿔형 투구]
	_prect(img, cx - 1 + pl_dx, cy - 15, 3, 4, Color("#facc15"))
	_pset(img, cx + pl_dx, cy - 15, Color("#fef08a"))
	_prect(img, cx - 4, cy - 11, 8, 5, Color("#64748b"))
	_prect(img, cx - 3, cy - 11, 6, 4, Color("#cbd5e1"))
	_prect(img, cx - 5, cy - 7, 10, 1, Color("#facc15"))
	_prect(img, cx - 3, cy - 6, 6, 4, Color("#fdba74"))
	_pset(img, cx - 2, cy - 5, Color("#0f172a"))
	_pset(img, cx + 1, cy - 5, Color("#0f172a"))
	_prect(img, cx - 5, cy - 6, 2, 4, Color("#94a3b8")) # 사슬 아벤테일
	_prect(img, cx + 3, cy - 6, 2, 4, Color("#94a3b8"))

	# [오른손 무기: 콘타리온 창]
	var wx := cx + 6 + wp_dx
	var wy := cy + wp_dy
	if anim_state == AnimState.ATTACK and frame >= 1:
		_prect(img, cx - 4, wy, 16 + wp_dx, 2, Color("#78350f"))
		_prect(img, cx + 11 + wp_dx, wy - 2, 2, 6, Color("#facc15")) # 황금 날개 소켓
		_prect(img, cx + 13 + wp_dx, wy - 1, 6, 3, Color("#f8fafc"))
	else:
		_prect(img, wx, wy - 12, 2, 22, Color("#78350f"))
		_prect(img, wx - 2, wy - 14, 6, 2, Color("#facc15"))
		_prect(img, wx, wy - 20, 2, 6, Color("#f8fafc"))
		_pset(img, wx, wy - 21, Color("#ffffff"))

	# [왼손 방패: 타원형 스쿠톤(Skouton) + 황금 쌍두독수리]
	var sx := cx - 9 + sh_dx
	var sy := cy - 3 + sh_dy
	_prect(img, sx + 1, sy, 6, 12, Color("#f59e0b"))
	_prect(img, sx, sy + 1, 8, 10, Color("#f59e0b"))
	_prect(img, sx + 1, sy + 1, 6, 10, Color("#6b21a8"))
	# 황금 쌍두독수리 도트
	_prect(img, sx + 2, sy + 3, 4, 5, Color("#facc15"))
	_pset(img, sx + 2, sy + 2, Color("#fde047")) # 좌측 머리
	_pset(img, sx + 5, sy + 2, Color("#fde047")) # 우측 머리
	_pset(img, sx + 1, sy + 4, Color("#fde047")) # 좌측 날개
	_pset(img, sx + 6, sy + 4, Color("#fde047")) # 우측 날개

# 2-D. 맘루크 술탄국 (MAMLUK): 청록/백색 비단 터번 투구 + 금장 라멜라 아머 + 초승달 원형 방패 + 다마스쿠스 언월도/시미터
static func _draw_mamluk_soldier(img: Image, cx: int, cy: int, ll_dy: int, lr_dy: int, sh_dx: int, sh_dy: int, wp_dx: int, wp_dy: int, _pl_dx: int, anim_state: int, frame: int) -> void:
	# [다리 & 사막 가죽 군화]
	_prect(img, cx - 5, cy + 9 + ll_dy, 4, 4, Color("#78350f"))
	_prect(img, cx + 1, cy + 9 + lr_dy, 4, 4, Color("#78350f"))

	# [다마스쿠스 금장 라멜라 갑옷 & 청록색 비단 요대]
	_prect(img, cx - 6, cy - 2, 12, 11, Color("#0f766e"))
	_prect(img, cx - 5, cy - 1, 10, 8, Color("#d97706"))
	for sy in [cy, cy + 2, cy + 4]:
		_prect(img, cx - 4, sy, 8, 1, Color("#facc15"))
	# 청록색 비단 허리띠
	_prect(img, cx - 6, cy + 4, 12, 2, Color("#14b8a6"))
	_prect(img, cx - 1, cy + 4, 2, 2, Color("#fde047"))

	# [뾰족한 치차크 강철 투구 + 백색/청록색 비단 터번]
	_prect(img, cx - 1, cy - 15, 2, 3, Color("#e2e8f0")) # 첨탑 꼭대기
	_prect(img, cx - 3, cy - 12, 6, 3, Color("#94a3b8"))
	# 비단 터번 (백색 + 청록색 교차 주름)
	_prect(img, cx - 6, cy - 10, 12, 4, Color("#f8fafc"))
	_prect(img, cx - 5, cy - 9, 4, 2, Color("#14b8a6"))
	_prect(img, cx + 1, cy - 9, 4, 2, Color("#14b8a6"))
	_prect(img, cx - 1, cy - 10, 2, 2, Color("#facc15")) # 터번 중앙 보석
	# 얼굴 & 검은 수염 & 코가리개(Nasal bar)
	_prect(img, cx - 3, cy - 6, 6, 4, Color("#d97706"))
	_pset(img, cx - 2, cy - 5, Color("#090d16"))
	_pset(img, cx + 1, cy - 5, Color("#090d16"))
	_prect(img, cx, cy - 7, 1, 3, Color("#e2e8f0")) # 코가리개
	_prect(img, cx - 3, cy - 3, 6, 2, Color("#0f172a")) # 짙은 수염

	# [오른손 무기: 다마스쿠스 언월도/시미터]
	var wx := cx + 6 + wp_dx
	var wy := cy + wp_dy
	if anim_state == AnimState.ATTACK and frame >= 1:
		_prect(img, cx + 3, wy, 4, 2, Color("#facc15")) # 금장 코등이
		_prect(img, cx + 7, wy, 11 + wp_dx, 2, Color("#e2e8f0"))
		_prect(img, cx + 10, wy - 1, 9 + wp_dx, 2, Color("#ffffff")) # 곡도 날끝
	else:
		_prect(img, wx - 1, wy + 1, 4, 2, Color("#facc15")) # 코등이
		# 초승달처럼 휘어지는 곡도(Scimitar) 도트 라인
		_prect(img, wx, wy - 6, 2, 7, Color("#cbd5e1"))
		_prect(img, wx + 1, wy - 12, 2, 7, Color("#e2e8f0"))
		_prect(img, wx + 2, wy - 16, 2, 5, Color("#ffffff"))
		_pset(img, wx + 3, wy - 17, Color("#ffffff"))

	# [왼손 방패: 둥근 다라크(Daraq) 강철 방패 + 황금 초승달]
	var sx := cx - 9 + sh_dx
	var sy := cy - 2 + sh_dy
	_prect(img, sx + 1, sy, 8, 10, Color("#475569"))
	_prect(img, sx, sy + 1, 10, 8, Color("#475569"))
	_prect(img, sx + 1, sy + 1, 8, 8, Color("#64748b"))
	# 황금 초승달 도트 문양
	_prect(img, sx + 3, sy + 2, 3, 6, Color("#facc15"))
	_prect(img, sx + 4, sy + 3, 3, 4, Color("#64748b")) # 파낸 안쪽
	_pset(img, sx + 5, sy + 2, Color("#fde047"))
	_pset(img, sx + 5, sy + 7, Color("#fde047"))

# 2-E. 쫄(SOLDIER) 사망 파편 모션 (DEATH frame 2, 3)
static func _draw_soldier_death_fragments(img: Image, faction: int, frame: int) -> void:
	var armor_c := Color("#1e3a8a")
	match faction:
		Faction.TEMPLAR: armor_c = Color("#e2e8f0")
		Faction.BYZANTINE: armor_c = Color("#d97706")
		Faction.MAMLUK: armor_c = Color("#14b8a6")

	var spread := (frame - 1) * 4
	# 바닥에 떨어진 투구와 방패, 흩어지는 도트 파편
	_prect(img, 14 - spread, 27, 6, 5, Color("#64748b")) # 튕겨나간 투구
	_prect(img, 10 - spread, 29, 7, 5, armor_c) # 쓰러진 방패
	_pline(img, 24, 31, 35 + spread, 28, Color("#cbd5e1")) # 떨어진 창/칼
	# 영혼/스파크 파편 도트
	for i in range(6):
		var px := 16 + i * 3 + (spread if i % 2 == 0 else -spread)
		var py := 20 - (frame * 3) + (i % 3) * 4
		_prect(img, px, py, 2, 2, Color("#facc15") if i % 2 == 0 else armor_c)

# --- 3. 쫄(SOLDIER) 공격 찌르기 잔상(Pixel Thrust Smear) & 피격 스파크 오버레이 ---
static func _draw_soldier_fx_overlay(img: Image, _side: int, faction: int, anim_state: int, frame: int) -> void:
	if anim_state == AnimState.ATTACK:
		if frame == 1:
			# 방패 밀치기 충격파 (Shield Bash Wave)
			_pline(img, 12, 17, 10, 22, Color("#e2e8f0"))
			_pline(img, 10, 22, 12, 27, Color("#e2e8f0"))
		elif frame == 2:
			# 하얀색/청색/금색 3중 도트 찌르기 잔상 (Pixel Thrust Smear)
			var accent := Color("#38bdf8")
			if faction == Faction.GORYEO:
				accent = Color("#ef4444")
			elif faction == Faction.TEMPLAR:
				accent = Color("#facc15")
			elif faction == Faction.BYZANTINE:
				accent = Color("#c084fc")
			elif faction == Faction.MAMLUK:
				accent = Color("#2dd4bf")

			# 상/중/하 스피드 라인과 관통 코어
			_prect(img, 20, 20, 26, 4, accent)
			_prect(img, 24, 21, 23, 2, Color("#ffffff"))
			_pline(img, 18, 18, 44, 21, Color("#fde047"))
			_pline(img, 18, 25, 44, 22, Color("#fde047"))
			# 창끝 크리티컬 십자 섬광
			_prect(img, 43, 17, 2, 9, Color("#ffffff"))
			_prect(img, 40, 20, 7, 3, Color("#ffffff"))
		elif frame == 3:
			# 잔상 여운 파티클
			_pset(img, 38, 19, Color("#fde047"))
			_pset(img, 42, 21, Color("#ffffff"))
			_pset(img, 40, 24, Color("#38bdf8"))
	elif anim_state == AnimState.HIT:
		# 방패 방어 스파크
		var sp_col := Color("#ffffff") if frame == 0 else Color("#facc15")
		_prect(img, 12, 18, 2, 2, sp_col)
		_prect(img, 9, 22, 2, 2, Color("#ef4444"))
		_prect(img, 14, 25, 2, 2, Color("#facc15"))

static func _draw_generic_attack_smear(img: Image, side: int) -> void:
	var c := Color("#34d399") if side == Side.CHU else Color("#f87171")
	_prect(img, 22, 18, 24, 3, c)
	_prect(img, 26, 19, 20, 1, Color("#ffffff"))

# --- 4. 나머지 6대 기물(궁, 차, 포, 마, 상, 사) 48x48 도트 스프라이트 렌더러 ---
static func _draw_other_piece_pixel_art(img: Image, pt: int, side: int, faction: int, anim_state: int, frame: int) -> void:
	var bob := -1 if (frame % 2 == 1) else 0
	var dx := 3 if (anim_state == AnimState.ATTACK and frame == 2) else (-2 if anim_state == AnimState.HIT else 0)
	var cx := 23 + dx
	var cy := 21 + bob

	var primary := Color("#1e3a8a")
	var secondary := Color("#facc15")
	match faction:
		Faction.GORYEO:
			primary = Color("#1e3a8a")
			secondary = Color("#dc2626")
		Faction.TEMPLAR:
			primary = Color("#e2e8f0")
			secondary = Color("#dc2626")
		Faction.BYZANTINE:
			primary = Color("#6b21a8")
			secondary = Color("#facc15")
		Faction.MAMLUK:
			primary = Color("#0f766e")
			secondary = Color("#f59e0b")

	var team_c := Color("#10b981") if side == Side.CHU else Color("#ef4444")

	match pt:
		PieceType.KING:
			# 황제/대장군: 화려한 날개 왕관 + 망토 + 황금 갑주 + 쌍검/국새
			_prect(img, cx - 8, cy - 3, 16, 14, secondary) # 대망토
			_prect(img, cx - 6, cy - 2, 12, 12, primary)
			_prect(img, cx - 4, cy - 1, 8, 9, Color("#facc15")) # 황금 흉갑
			_prect(img, cx - 4, cy - 9, 8, 7, Color("#fdba74"))
			_prect(img, cx - 6, cy - 14, 12, 5, Color("#facc15")) # 황제 면류관/왕관
			_pset(img, cx - 4, cy - 15, Color("#ffffff"))
			_pset(img, cx, cy - 16, Color("#ef4444"))
			_pset(img, cx + 4, cy - 15, Color("#ffffff"))
			# 지휘 성검
			_prect(img, cx + 7, cy - 14, 3, 18, Color("#38bdf8"))
			_prect(img, cx + 8, cy - 14, 1, 16, Color("#ffffff"))
		PieceType.CHARIOT:
			# 중장갑 전차/개마무사 돌격기병
			_prect(img, cx - 10, cy + 2, 20, 9, Color("#475569")) # 철갑마/전차 바디
			_prect(img, cx - 9, cy + 3, 18, 6, primary)
			_prect(img, cx - 5, cy - 7, 10, 9, primary) # 탑승 중기병
			_prect(img, cx - 3, cy - 12, 6, 5, Color("#94a3b8"))
			# 전면 대형 랜스(Lance)
			_prect(img, cx + 2, cy - 4, 16, 3, Color("#e2e8f0"))
			_prect(img, cx + 4, cy - 3, 14, 1, Color("#ffffff"))
		PieceType.CANNON:
			# 화차(신기전) / 공성 발석차
			_prect(img, cx - 9, cy + 4, 18, 6, Color("#78350f")) # 목재 차체
			_prect(img, cx - 6, cy + 6, 6, 6, Color("#451a03")) # 바퀴
			_prect(img, cx + 2, cy + 6, 6, 6, Color("#451a03"))
			_prect(img, cx - 6, cy - 5, 12, 9, Color("#334155")) # 화포 포신/신기전 틀
			_prect(img, cx - 4, cy - 4, 10, 6, secondary)
			_prect(img, cx + 5, cy - 6, 4, 4, Color("#f97316")) # 점화 불꽃
			_pset(img, cx + 7, cy - 5, Color("#fde047"))
		PieceType.HORSE:
			# 기마병 (군마 + 창기병)
			_prect(img, cx - 8, cy + 2, 15, 8, Color("#92400e")) # 군마 몸통
			_prect(img, cx + 4, cy - 5, 5, 9, Color("#78350f")) # 말 목/머리
			_prect(img, cx + 6, cy - 6, 4, 4, Color("#b45309"))
			_prect(img, cx - 4, cy - 7, 7, 9, primary) # 기수
			_prect(img, cx - 3, cy - 11, 5, 4, Color("#cbd5e1"))
			_pline(img, cx - 6, cy - 2, cx + 10, cy - 10, Color("#e2e8f0"))
		PieceType.ELEPHANT:
			# 전투 코끼리 (워 엘리펀트 + 상아 + 망루)
			_prect(img, cx - 10, cy - 2, 18, 13, Color("#64748b")) # 코끼리 거구
			_prect(img, cx - 8, cy - 1, 14, 10, Color("#94a3b8"))
			_prect(img, cx + 6, cy - 1, 5, 10, Color("#64748b")) # 코(Trunk)
			_prect(img, cx + 8, cy + 3, 5, 2, Color("#ffffff")) # 상아(Tusk)
			_prect(img, cx - 6, cy - 10, 11, 8, secondary) # 등 위의 전투 망루(Howdah)
			_prect(img, cx - 4, cy - 8, 7, 5, primary)
		PieceType.GUARD:
			# 궁성 근위대(사 - GUARD): 쌍검/대방패 황실 호위무사
			_prect(img, cx - 6, cy - 2, 12, 12, primary)
			_prect(img, cx - 4, cy - 1, 8, 9, Color("#eab308"))
			_prect(img, cx - 4, cy - 10, 8, 8, Color("#cbd5e1"))
			_prect(img, cx - 2, cy - 13, 4, 3, team_c)
			_prect(img, cx - 9, cy - 2, 5, 11, team_c) # 근위 방패
			_prect(img, cx - 8, cy - 1, 3, 9, Color("#facc15"))
			_prect(img, cx + 6, cy - 11, 2, 14, Color("#f8fafc"))

# --- 5. 1px 검은색 도트 아웃라인 패스 ---
static func _apply_pixel_outline(img: Image) -> void:
	var outline_pts: Array[Vector2i] = []
	for y in range(CANVAS_SIZE):
		for x in range(CANVAS_SIZE):
			if img.get_pixel(x, y).a == 0.0:
				# 우측 상단 한자 배지 영역(34..47, 0..12)은 자체 사각 테두리를 유지
				if x >= 34 and y <= 12:
					continue
				var has_neighbor := false
				for offset in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
					var nx: int = x + offset.x
					var ny: int = y + offset.y
					if nx >= 0 and nx < CANVAS_SIZE and ny >= 0 and ny < CANVAS_SIZE:
						if not (nx >= 34 and ny <= 12) and img.get_pixel(nx, ny).a > 0.5:
							has_neighbor = true
							break
				if has_neighbor:
					outline_pts.append(Vector2i(x, y))

	for pt in outline_pts:
		img.set_pixel(pt.x, pt.y, OUTLINE_COLOR)
