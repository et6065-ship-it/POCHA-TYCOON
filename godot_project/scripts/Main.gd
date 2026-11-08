extends Node2D
## 중세 정예병 16-Bit 도트 배틀체스 장기 (Godot 4 네이티브 프로젝트)
## - 한국 정통 장기 규칙 (9x10 보드, 궁성 대각선, 포 다리/포불장포, 마 1멱/상 2멱, 장군/외통수)
## - PixelSpriteGenerator 기반 48x48 초고밀도 도트 스프라이트 (Image.set_pixel -> ImageTexture)
## - 우측 HUD '[쫄(卒/兵) 도트 디자인 & 모션 뷰어]' (4x 확대 프리뷰 + 4개국 비교 + 5단계 모션 전환)

const SpriteGen = preload("res://scripts/PixelSpriteGenerator.gd")

const COLS := 9
const ROWS := 10
const CELL_SIZE := 66
const BOARD_ORIGIN := Vector2(356, 96)

enum Side { CHU, HAN }
enum PieceType { KING, CHARIOT, CANNON, HORSE, ELEPHANT, GUARD, SOLDIER }
enum Faction { GORYEO, TEMPLAR, BYZANTINE, MAMLUK }

const FACTION_NAMES := {
	Faction.GORYEO: "고려 천군 (팽배수·장창병)",
	Faction.TEMPLAR: "성전 기사단 (크루세이더 보병)",
	Faction.BYZANTINE: "비잔틴 제국군 (스쿠타토이)",
	Faction.MAMLUK: "맘루크 술탄국 (가지 방패병)"
}

const SOLDIER_DESIGN_NOTES := {
	Faction.GORYEO: [
		"• 투구: 붉은 말총 술(상모) 달린 고려 철제 첨주 & 드림",
		"• 갑옷: 감청/흑칠 두정갑(Brigandine) + 금색 스터드 징",
		"• 방패: 삼족오 황금 문양 대형 보병 방패(팽배)",
		"• 무기: 붉은 영자(술) 달린 장창 & 적색 관통 잔상"
	],
	Faction.TEMPLAR: [
		"• 투구: 황동 십자 전면 장식 & T자 눈구멍 그레이트헬름",
		"• 갑옷: 사슬갑옷(Chainmail) 위 백색 적십자 서코트",
		"• 방패: 강철 테두리 성전사 카이트 실드(Kite Shield)",
		"• 무기: 도끼날과 창끝이 결합된 중보병 할버드(Halberd)"
	],
	Faction.BYZANTINE: [
		"• 투구: 황금 볏(Crest) 비잔틴 원뿔형 철모 & 사슬 드림",
		"• 갑옷: 황금 비늘갑옷(Klivanion) & 제국 자색 망토",
		"• 방패: 황금 쌍두독수리 문양 타원형 스쿠톤(Skouton)",
		"• 무기: 황금 날개 소켓이 달린 콘타리온(Kontarion) 장창"
	],
	Faction.MAMLUK: [
		"• 투구: 백색·청록 비단 터번 감긴 뾰족한 치차크 철모",
		"• 갑옷: 다마스쿠스 금장 라멜라 찰갑 & 청록색 비단 요대",
		"• 방패: 황금 초승달 문양 둥근 강철 방패(Daraq)",
		"• 무기: 날카롭게 휘어진 다마스쿠스 언월도/시미터"
	]
}

const ANIM_STATE_NAMES := {
	SpriteGen.AnimState.IDLE: "IDLE (전열 대기 & 숨쉬기)",
	SpriteGen.AnimState.MOVE: "MOVE (방패 행군 전진)",
	SpriteGen.AnimState.ATTACK: "ATTACK (방패 밀치기 + 창 찌르기 잔상)",
	SpriteGen.AnimState.HIT: "HIT (방패 방어 & 피격 스파크)",
	SpriteGen.AnimState.DEATH: "DEATH (투구·방패 파편 붕괴)"
}

const PIECE_VALUES := {
	PieceType.KING: 1000,
	PieceType.CHARIOT: 13,
	PieceType.CANNON: 7,
	PieceType.HORSE: 5,
	PieceType.ELEPHANT: 3,
	PieceType.GUARD: 3,
	PieceType.SOLDIER: 2
}

const PIECE_LABELS := {
	PieceType.KING: "궁(將)",
	PieceType.CHARIOT: "차(車)",
	PieceType.CANNON: "포(包)",
	PieceType.HORSE: "마(馬)",
	PieceType.ELEPHANT: "상(象)",
	PieceType.GUARD: "사(士)",
	PieceType.SOLDIER: "졸/병"
}

var board := []
var turn: int = Side.CHU
var chu_faction: int = Faction.GORYEO
var han_faction: int = Faction.TEMPLAR
var vs_ai: bool = true
var selected_pos := Vector2i(-1, -1)
var legal_moves: Array[Dictionary] = []
var anim_tick: float = 0.0
var status_text: String = "초(CHU) 진영 차례입니다. 기물을 선택하세요."
var game_over: bool = false

# 쫄(SOLDIER) 전용 도트 디자인 & 모션 쇼케이스 상태
var showcase_anim_state: int = SpriteGen.AnimState.IDLE
var showcase_side: int = Side.CHU
var showcase_btn_rects: Array[Dictionary] = []

# 배틀체스 현장(On-Board) 결투 및 2.5D 뷰 상태
var view_3d_mode: bool = true
var battle_active: bool = false
var battle_timer: float = 0.0
var battle_attacker: Dictionary = {}
var battle_defender: Dictionary = {}
var pending_move: Dictionary = {}
var battle_particles: Array[Dictionary] = []
var board_ambient_fx: Array[Dictionary] = []
var battle_hit1_played: bool = false
var battle_hit2_played: bool = false

# --- 내 컴퓨터 기준 해상도 · 장기판 디자인 · 사운드 옵션 상태 ---
var options_open: bool = false
var option_btn_rects: Array[Dictionary] = []
var res_presets: Array[Dictionary] = [
	{"label": "내 모니터 자동 맞춤 (Auto Fit)", "size": Vector2i(0, 0), "fullscreen": false, "auto": true},
	{"label": "2560 x 1440 (QHD 메인 모니터)", "size": Vector2i(2560, 1440), "fullscreen": false, "auto": false},
	{"label": "2048 x 1152 (QHD+ 서브 모니터)", "size": Vector2i(2048, 1152), "fullscreen": false, "auto": false},
	{"label": "1920 x 1080 (FHD 표준 와이드)", "size": Vector2i(1920, 1080), "fullscreen": false, "auto": false},
	{"label": "1600 x 900 (HD+ 창모드)", "size": Vector2i(1600, 900), "fullscreen": false, "auto": false},
	{"label": "1360 x 880 (픽셀 원본 1:1)", "size": Vector2i(1360, 880), "fullscreen": false, "auto": false}
]
var current_res_idx: int = 0
var is_fullscreen_mode: bool = false
var board_theme_idx: int = 0
const BOARD_THEMES := [
	{"name": "왕실 참나무 & 황금", "frame": "#3b2314", "border": "#f5b700", "surface": "#7c4a27", "surface_alt": "#6b3e1f", "cliff": "#26150a", "line": "#271509"},
	{"name": "고려 비취옥 & 청자", "frame": "#0c2e2e", "border": "#34d399", "surface": "#1b4d4a", "surface_alt": "#153e3c", "cliff": "#081f1e", "line": "#071c1b"},
	{"name": "다크 흑요석 & 크림슨", "frame": "#141624", "border": "#f43f5e", "surface": "#252a40", "surface_alt": "#1e2235", "cliff": "#0d0f1a", "line": "#090b12"},
	{"name": "다마스쿠스 황금 사암", "frame": "#452c14", "border": "#fbbf24", "surface": "#9a6b3b", "surface_alt": "#875c31", "cliff": "#2e1c0b", "line": "#2d1b0a"}
]

# 사운드 & 16-Bit 칩튠 오디오 합성 상태
var sound_enabled: bool = true
var master_volume: float = 0.80
var bgm_volume: float = 0.55
var sfx_volume: float = 0.85
var battle_volume: float = 0.90
var bgm_enabled: bool = true
var sfx_player: AudioStreamPlayer
var bgm_player: AudioStreamPlayer
var bgm_timer: float = 0.0
var bgm_step: int = 0
var detected_screen_size := Vector2i(2560, 1440)

# --- 2.5D 원근 투영 좌표 변환 헬퍼 ---
func _project_board_coord(vx: float, vy: float) -> Dictionary:
	if not view_3d_mode:
		return {
			"pos": BOARD_ORIGIN + Vector2(vx * CELL_SIZE, vy * CELL_SIZE),
			"scale": 1.0
		}
	var s_top := 0.76
	var s_bot := 1.03
	var y_top := 126.0
	var y_bot := 734.0
	var base_w := 65.0
	var cx := 624.0

	var t := vy / 9.0
	var denom := s_bot - (s_bot - s_top) * t
	var u := (t * s_top) / denom if absf(denom) > 0.0001 else t
	var sc := s_top + (s_bot - s_top) * u
	var py := y_top + (y_bot - y_top) * u
	var px := cx + (vx - 4.0) * base_w * sc
	return {
		"pos": Vector2(px, py),
		"scale": sc
	}

func _screen_to_board_cell(mpos: Vector2) -> Vector2i:
	if not view_3d_mode:
		var c := int(round((mpos.x - BOARD_ORIGIN.x) / CELL_SIZE))
		var r := int(round((mpos.y - BOARD_ORIGIN.y) / CELL_SIZE))
		if c >= 0 and c < COLS and r >= 0 and r < ROWS:
			return Vector2i(c, r)
		return Vector2i(-1, -1)

	# 1. 앞열(r=9)부터 뒷열(r=0) 순으로 서 있는 HD-2D 입간판 기물 몸체 클릭 여부 판정
	for r in range(ROWS - 1, -1, -1):
		for c in range(COLS):
			if board[r][c] == null:
				continue
			var proj := _project_board_coord(float(c), float(r))
			var pt: Vector2 = proj["pos"]
			var sc: float = proj["scale"]
			if absf(mpos.x - pt.x) <= 28.0 * sc and (mpos.y - pt.y) >= -48.0 * sc and (mpos.y - pt.y) <= 20.0 * sc:
				return Vector2i(c, r)

	# 2. 2.5D 바닥 그리드 역투영 판정
	var s_top := 0.76
	var s_bot := 1.03
	var y_top := 126.0
	var y_bot := 734.0
	var base_w := 65.0
	var cx := 624.0

	var u := (mpos.y - y_top) / (y_bot - y_top)
	var sc := s_top + (s_bot - s_top) * u
	if sc <= 0.15:
		return Vector2i(-1, -1)
	var vx := 4.0 + (mpos.x - cx) / (base_w * sc)
	var t := (u * s_bot) / sc
	var vy := t * 9.0
	var ic := int(round(vx))
	var ir := int(round(vy))
	if ic >= 0 and ic < COLS and ir >= 0 and ir < ROWS:
		var cell_pt: Vector2 = _project_board_coord(float(ic), float(ir))["pos"]
		if mpos.distance_to(cell_pt) <= 36.0 * sc:
			return Vector2i(ic, ir)
	return Vector2i(-1, -1)

func _spawn_battle_particles(count: int, col1: Color, col2: Color, speed_mul: float = 1.0) -> void:
	for i in range(count):
		var ang := (float(i) / float(count)) * TAU + randf_range(-0.25, 0.25)
		var spd := randf_range(2.2, 6.2) * speed_mul
		battle_particles.append({
			"dx": randf_range(-8.0, 8.0),
			"dy": randf_range(-5.0, 5.0),
			"dz": randf_range(6.0, 18.0),
			"vx": cos(ang) * spd,
			"vy": sin(ang) * spd * 0.6,
			"vz": randf_range(4.0, 8.0),
			"size": 7.0 if i % 3 == 0 else 5.0,
			"color": Color("#ffffff") if i % 4 == 0 else (col1 if i % 2 == 0 else col2),
			"life": randf_range(0.35, 0.75)
		})

func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	detected_screen_size = DisplayServer.screen_get_size()
	_setup_audio_players()
	_apply_resolution_preset(0)

	# 4대 국가별 쫄(SOLDIER) 5단 모션 도트 텍스처 프리워밍 검증
	for fac in [Faction.GORYEO, Faction.TEMPLAR, Faction.BYZANTINE, Faction.MAMLUK]:
		for st in [SpriteGen.AnimState.IDLE, SpriteGen.AnimState.MOVE, SpriteGen.AnimState.ATTACK, SpriteGen.AnimState.HIT, SpriteGen.AnimState.DEATH]:
			for f in range(SpriteGen.get_frame_count(st)):
				SpriteGen.get_sprite_texture(PieceType.SOLDIER, Side.CHU, fac, st, f)
				SpriteGen.get_sprite_texture(PieceType.SOLDIER, Side.HAN, fac, st, f)
	reset_game()

func _setup_audio_players() -> void:
	sfx_player = AudioStreamPlayer.new()
	add_child(sfx_player)
	bgm_player = AudioStreamPlayer.new()
	add_child(bgm_player)

func _play_tone(freq_start: float, freq_end: float, duration: float, vol_channel: float, is_noise: bool = false) -> void:
	if not sound_enabled or master_volume <= 0.01 or vol_channel <= 0.01:
		return
	var mix_rate := 22050
	var samples := int(mix_rate * duration)
	if samples <= 0:
		return
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_8_BITS
	wav.mix_rate = mix_rate
	wav.stereo = false
	var data := PackedByteArray()
	data.resize(samples)
	var amp := clampf(master_volume * vol_channel * 0.75, 0.0, 0.95)
	var phase := 0.0
	for i in range(samples):
		var t := float(i) / float(samples)
		var env := 1.0 - t
		var freq := lerpf(freq_start, freq_end, t)
		phase += freq / float(mix_rate)
		var wave := 1.0 if fmod(phase, 1.0) < 0.5 else -1.0
		if is_noise:
			wave = ( wave * 0.5 ) + ( randf_range(-1.0, 1.0) * 0.5 )
		var val := int(clampf(wave * amp * env * 127.0, -127.0, 127.0))
		data[i] = (val + 256) if val < 0 else val
	wav.data = data
	sfx_player.stream = wav
	sfx_player.play()

func _play_bgm_note(freq: float, duration: float) -> void:
	if not sound_enabled or not bgm_enabled or master_volume <= 0.01 or bgm_volume <= 0.01:
		return
	var mix_rate := 22050
	var samples := int(mix_rate * duration)
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_8_BITS
	wav.mix_rate = mix_rate
	wav.stereo = false
	var data := PackedByteArray()
	data.resize(samples)
	var amp := clampf(master_volume * bgm_volume * 0.25, 0.0, 0.6)
	var phase := 0.0
	for i in range(samples):
		var t := float(i) / float(samples)
		var env := (1.0 - t * 0.85)
		phase += freq / float(mix_rate)
		var wave := 1.0 if fmod(phase, 1.0) < 0.5 else -1.0
		var val := int(clampf(wave * amp * env * 127.0, -127.0, 127.0))
		data[i] = (val + 256) if val < 0 else val
	wav.data = data
	bgm_player.stream = wav
	bgm_player.play()

func _apply_resolution_preset(idx: int) -> void:
	current_res_idx = clampi(idx, 0, res_presets.size() - 1)
	detected_screen_size = DisplayServer.screen_get_size()
	var preset: Dictionary = res_presets[current_res_idx]
	if is_fullscreen_mode:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
		status_text = "🖥️ 전체화면 모드 적용됨 (" + str(detected_screen_size.x) + "x" + str(detected_screen_size.y) + ")"
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
		var target_sz: Vector2i = preset["size"]
		if preset["auto"]:
			var fit_w := int(min(detected_screen_size.x * 0.88, 2240))
			var fit_h := int(min(detected_screen_size.y * 0.86, 1320))
			target_sz = Vector2i(max(1360, fit_w), max(880, fit_h))
		else:
			target_sz = Vector2i(min(target_sz.x, detected_screen_size.x), min(target_sz.y, detected_screen_size.y))
		DisplayServer.window_set_size(target_sz)
		var center_pos := (detected_screen_size - target_sz) / 2
		DisplayServer.window_set_position(Vector2i(max(0, center_pos.x), max(0, center_pos.y)))
		status_text = "🖥️ 해상도 적용: " + str(target_sz.x) + "x" + str(target_sz.y) + " (내 모니터 " + str(detected_screen_size.x) + "x" + str(detected_screen_size.y) + " 기준)"
	queue_redraw()

func reset_game() -> void:
	board.clear()
	for r in range(ROWS):
		var row := []
		for c in range(COLS):
			row.append(null)
		board.append(row)

	# 한(HAN, 상단 0~3행) 배치
	_setup_back_rank(0, Side.HAN)
	board[1][4] = {"type": PieceType.KING, "side": Side.HAN}
	board[2][1] = {"type": PieceType.CANNON, "side": Side.HAN}
	board[2][7] = {"type": PieceType.CANNON, "side": Side.HAN}
	for c in [0, 2, 4, 6, 8]:
		board[3][c] = {"type": PieceType.SOLDIER, "side": Side.HAN}

	# 초(CHU, 하단 6~9행) 배치
	_setup_back_rank(9, Side.CHU)
	board[8][4] = {"type": PieceType.KING, "side": Side.CHU}
	board[7][1] = {"type": PieceType.CANNON, "side": Side.CHU}
	board[7][7] = {"type": PieceType.CANNON, "side": Side.CHU}
	for c in [0, 2, 4, 6, 8]:
		board[6][c] = {"type": PieceType.SOLDIER, "side": Side.CHU}

	turn = Side.CHU
	selected_pos = Vector2i(-1, -1)
	legal_moves.clear()
	game_over = false
	battle_active = false
	battle_particles.clear()
	board_ambient_fx.clear()
	status_text = "새 대국 시작! [2.5D 입체 보드 + 현장 배틀 임팩트 ON] 초(CHU) 선공입니다."
	_play_tone(320.0, 140.0, 0.08, sfx_volume, true)
	queue_redraw()

func _setup_back_rank(r: int, side: int) -> void:
	board[r][0] = {"type": PieceType.CHARIOT, "side": side}
	board[r][1] = {"type": PieceType.ELEPHANT, "side": side}
	board[r][2] = {"type": PieceType.HORSE, "side": side}
	board[r][3] = {"type": PieceType.GUARD, "side": side}
	board[r][5] = {"type": PieceType.GUARD, "side": side}
	board[r][6] = {"type": PieceType.ELEPHANT, "side": side}
	board[r][7] = {"type": PieceType.HORSE, "side": side}
	board[r][8] = {"type": PieceType.CHARIOT, "side": side}

func _process(delta: float) -> void:
	anim_tick += delta
	if sound_enabled and bgm_enabled:
		bgm_timer += delta
		if bgm_timer >= 0.28:
			bgm_timer = 0.0
			var melody := [293.66, 0.0, 349.23, 392.00, 440.00, 0.0, 523.25, 440.00, 392.00, 349.23, 293.66, 0.0, 349.23, 293.66, 261.63, 293.66]
			var note: float = melody[bgm_step % melody.size()]
			bgm_step += 1
			if note > 0.0:
				_play_bgm_note(note, 0.22)

	# 상시 착지/장군 충격파 이펙트 타이머 업데이트
	for i in range(board_ambient_fx.size() - 1, -1, -1):
		board_ambient_fx[i]["timer"] += delta
		if board_ambient_fx[i]["timer"] >= board_ambient_fx[i]["duration"]:
			board_ambient_fx.remove_at(i)

	if battle_active:
		battle_timer += delta
		var p := battle_timer / 1.35
		if p >= 0.36 and not battle_hit1_played:
			battle_hit1_played = true
			_play_tone(620.0, 120.0, 0.14, battle_volume, true)
			_spawn_battle_particles(24, Color("#fde047"), Color("#ef4444"), 1.0)
		if p >= 0.58 and not battle_hit2_played:
			battle_hit2_played = true
			_play_tone(480.0, 65.0, 0.26, battle_volume, true)
			_spawn_battle_particles(36, Color("#f5b700"), Color("#ff3b5c"), 1.35)

		for i in range(battle_particles.size() - 1, -1, -1):
			var pt: Dictionary = battle_particles[i]
			pt["dx"] += pt["vx"] * delta * 60.0
			pt["dy"] += pt["vy"] * delta * 60.0
			pt["dz"] += pt["vz"] * delta * 60.0
			pt["vz"] -= 0.65 * delta * 60.0
			if pt["dz"] < 0.0:
				pt["dz"] = 0.0
				pt["vz"] = -pt["vz"] * 0.45
				pt["vx"] *= 0.75
				pt["vy"] *= 0.75
			pt["life"] -= delta
			if pt["life"] <= 0.0:
				battle_particles.remove_at(i)

		if battle_timer >= 1.35:
			_finish_battle_capture()
	queue_redraw()

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_O or event.keycode == KEY_ESCAPE:
			options_open = not options_open
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
			queue_redraw()
			return
		elif event.keycode == KEY_V:
			view_3d_mode = not view_3d_mode
			status_text = "🧊 2.5D 입체 틸트 장기판 활성화!" if view_3d_mode else "🗺️ 2D 평면 장기판 시점으로 전환됨"
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
			queue_redraw()
			return
		elif event.keycode == KEY_F11:
			is_fullscreen_mode = not is_fullscreen_mode
			_apply_resolution_preset(current_res_idx)
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
			return
		elif event.keycode == KEY_M:
			sound_enabled = not sound_enabled
			status_text = "🔊 사운드 켜짐" if sound_enabled else "🔇 사운드 음소거됨"
			queue_redraw()
			return
		elif event.keycode == KEY_R:
			reset_game()
			return
		elif event.keycode == KEY_1:
			chu_faction = (chu_faction + 1) % 4
			showcase_side = Side.CHU
			status_text = "초(CHU) 스킨 변경: " + FACTION_NAMES[chu_faction]
			_play_tone(580.0, 880.0, 0.06, sfx_volume)
			queue_redraw()
		elif event.keycode == KEY_2:
			han_faction = (han_faction + 1) % 4
			showcase_side = Side.HAN
			status_text = "한(HAN) 스킨 변경: " + FACTION_NAMES[han_faction]
			_play_tone(580.0, 880.0, 0.06, sfx_volume)
			queue_redraw()
		elif event.keycode == KEY_3:
			showcase_anim_state = (showcase_anim_state + 1) % 5
			status_text = "🛡️ 쫄(SOLDIER) 모션 프리뷰 전환: " + ANIM_STATE_NAMES[showcase_anim_state]
			_play_tone(580.0, 880.0, 0.06, sfx_volume)
			queue_redraw()
		elif event.keycode == KEY_4:
			showcase_side = Side.HAN if showcase_side == Side.CHU else Side.CHU
			status_text = "🛡️ 쫄(SOLDIER) 프리뷰 진영 전환: " + ("초(卒)" if showcase_side == Side.CHU else "한(兵)")
			_play_tone(580.0, 880.0, 0.06, sfx_volume)
			queue_redraw()
		elif event.keycode == KEY_SPACE and battle_active:
			_finish_battle_capture()
			return

	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var mpos: Vector2 = get_local_mouse_position()

		# 옵션 버튼 또는 옵션 모달 내부 클릭 처리
		for ob in option_btn_rects:
			var r_opt: Rect2 = ob["rect"]
			if r_opt.has_point(mpos):
				_handle_option_button(ob["action"], ob["value"])
				return

		if options_open:
			return

		if battle_active:
			_finish_battle_capture()
			return

		# 우측 쫄(SOLDIER) 쇼케이스 버튼 클릭 체크
		for btn in showcase_btn_rects:
			var r_box: Rect2 = btn["rect"]
			if r_box.has_point(mpos):
				_play_tone(660.0, 990.0, 0.06, sfx_volume)
				if btn["action"] == "anim":
					showcase_anim_state = btn["value"]
					status_text = "🛡️ 쫄(SOLDIER) 모션 선택: " + ANIM_STATE_NAMES[showcase_anim_state]
				elif btn["action"] == "faction":
					if showcase_side == Side.CHU:
						chu_faction = btn["value"]
					else:
						han_faction = btn["value"]
					status_text = "🛡️ 쫄(SOLDIER) 국가 변경: " + FACTION_NAMES[btn["value"]]
				elif btn["action"] == "side":
					showcase_side = Side.HAN if showcase_side == Side.CHU else Side.CHU
				queue_redraw()
				return

		if game_over or (vs_ai and turn == Side.HAN):
			return

		var clicked_cell := _screen_to_board_cell(mpos)
		if clicked_cell.x >= 0 and clicked_cell.y >= 0:
			_on_cell_clicked(clicked_cell)

func _handle_option_button(action: String, val) -> void:
	match action:
		"toggle_options":
			options_open = not options_open
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"toggle_3d":
			view_3d_mode = not view_3d_mode
			status_text = "🧊 2.5D 입체 틸트 장기판 활성화!" if view_3d_mode else "🗺️ 2D 평면 장기판 시점으로 전환됨"
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"set_res":
			is_fullscreen_mode = false
			_apply_resolution_preset(int(val))
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"toggle_fullscreen":
			is_fullscreen_mode = not is_fullscreen_mode
			_apply_resolution_preset(current_res_idx)
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"set_board_theme":
			board_theme_idx = int(val) % BOARD_THEMES.size()
			status_text = "🎨 장기판 디자인 변경: " + BOARD_THEMES[board_theme_idx]["name"]
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"toggle_sound":
			sound_enabled = not sound_enabled
			if sound_enabled:
				_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"toggle_bgm":
			bgm_enabled = not bgm_enabled
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"master_vol":
			master_volume = clampf(master_volume + float(val), 0.0, 1.0)
			sound_enabled = true
			_play_tone(660.0, 990.0, 0.06, sfx_volume)
		"bgm_vol":
			bgm_volume = clampf(bgm_volume + float(val), 0.0, 1.0)
			sound_enabled = true
			_play_bgm_note(440.0, 0.12)
		"sfx_vol":
			sfx_volume = clampf(sfx_volume + float(val), 0.0, 1.0)
			sound_enabled = true
			_play_tone(360.0, 110.0, 0.08, sfx_volume, true)
		"battle_vol":
			battle_volume = clampf(battle_volume + float(val), 0.0, 1.0)
			sound_enabled = true
			_play_tone(520.0, 95.0, 0.16, battle_volume, true)
	queue_redraw()

func _on_cell_clicked(cell: Vector2i) -> void:
	for mv in legal_moves:
		if mv["to"] == cell:
			_execute_move(mv)
			return

	var p = board[cell.y][cell.x]
	if p != null and p["side"] == turn:
		selected_pos = cell
		legal_moves = get_legal_moves_for(board, cell)
		_play_tone(660.0, 990.0, 0.06, sfx_volume)
		if p["type"] == PieceType.SOLDIER:
			showcase_side = p["side"]
			showcase_anim_state = SpriteGen.AnimState.MOVE
		status_text = PIECE_LABELS[p["type"]] + " 선택됨 (이동 가능: " + str(legal_moves.size()) + "곳)"
	else:
		selected_pos = Vector2i(-1, -1)
		legal_moves.clear()

func _execute_move(mv: Dictionary) -> void:
	var from_p: Vector2i = mv["from"]
	var to_p: Vector2i = mv["to"]
	var attacker = board[from_p.y][from_p.x]
	var defender = board[to_p.y][to_p.x]

	selected_pos = Vector2i(-1, -1)
	legal_moves.clear()

	if defender != null:
		battle_active = true
		battle_timer = 0.0
		battle_hit1_played = false
		battle_hit2_played = false
		battle_particles.clear()
		battle_attacker = attacker.duplicate()
		battle_defender = defender.duplicate()
		pending_move = mv
		if attacker["type"] == PieceType.SOLDIER:
			showcase_anim_state = SpriteGen.AnimState.ATTACK
		_play_tone(540.0, 90.0, 0.22, battle_volume, true)
		status_text = "💥 장기판 현장 처형 돌입! " + PIECE_LABELS[attacker["type"]] + " ➔ " + PIECE_LABELS[defender["type"]] + " 격파 중!"
	else:
		_play_tone(360.0, 110.0, 0.08, sfx_volume, true)
		board_ambient_fx.append({
			"cell": to_p,
			"color": Color("#10b981") if attacker["side"] == Side.CHU else Color("#ef4444"),
			"timer": 0.0,
			"duration": 0.42,
			"is_check": false
		})
		_apply_move_to_board(mv)

func _finish_battle_capture() -> void:
	battle_active = false
	battle_particles.clear()
	board_ambient_fx.append({
		"cell": pending_move["to"],
		"color": Color("#facc15"),
		"timer": 0.0,
		"duration": 0.48,
		"is_check": false
	})
	_apply_move_to_board(pending_move)

func _apply_move_to_board(mv: Dictionary) -> void:
	var from_p: Vector2i = mv["from"]
	var to_p: Vector2i = mv["to"]
	var piece = board[from_p.y][from_p.x]
	var captured = board[to_p.y][to_p.x]
	board[to_p.y][to_p.x] = piece
	board[from_p.y][from_p.x] = null

	if captured != null and captured["type"] == PieceType.KING:
		game_over = true
		_play_tone(440.0, 880.0, 0.35, sfx_volume)
		status_text = ("초(CHU) 승리!" if turn == Side.CHU else "한(HAN) 승리!") + " [R키: 새 대국]"
		return

	turn = Side.HAN if turn == Side.CHU else Side.CHU
	if is_in_check(board, turn):
		_play_tone(280.0, 560.0, 0.25, battle_volume)
		for kr in range(ROWS):
			for kc in range(COLS):
				var kp = board[kr][kc]
				if kp != null and kp["side"] == turn and kp["type"] == PieceType.KING:
					board_ambient_fx.append({
						"cell": Vector2i(kc, kr),
						"color": Color("#ef4444"),
						"timer": 0.0,
						"duration": 0.75,
						"is_check": true
					})
		status_text = "🔥 장군(CHECK)! " + ("초(CHU)" if turn == Side.CHU else "한(HAN)") + " 궁성이 위협받고 있습니다!"
	else:
		status_text = ("초(CHU)" if turn == Side.CHU else "한(HAN)") + " 차례입니다."

	if vs_ai and turn == Side.HAN and not game_over:
		get_tree().create_timer(0.35).timeout.connect(_run_ai_turn)

func _run_ai_turn() -> void:
	if game_over or turn != Side.HAN or battle_active:
		return
	var all_moves: Array[Dictionary] = []
	for r in range(ROWS):
		for c in range(COLS):
			var p = board[r][c]
			if p != null and p["side"] == Side.HAN:
				all_moves.append_array(get_legal_moves_for(board, Vector2i(c, r)))
	if all_moves.is_empty():
		game_over = true
		status_text = "외통수! 초(CHU) 승리! [R키: 새 대국]"
		return

	var best_mv: Dictionary = all_moves[0]
	var best_score: float = -99999.0
	for mv in all_moves:
		var sc: float = randf() * 0.4
		var target = board[mv["to"].y][mv["to"].x]
		if target != null:
			sc += PIECE_VALUES[target["type"]] * 12.0
		sc += (mv["to"].y - mv["from"].y) * 0.5
		if sc > best_score:
			best_score = sc
			best_mv = mv
	_execute_move(best_mv)

# --- 한국 장기 규칙 행마 생성 ---
func get_legal_moves_for(b: Array, pos: Vector2i) -> Array[Dictionary]:
	var pseudo := get_pseudo_moves(b, pos)
	var valid: Array[Dictionary] = []
	var my_side: int = b[pos.y][pos.x]["side"]
	for mv in pseudo:
		var sim := _clone_board(b)
		sim[mv["to"].y][mv["to"].x] = sim[mv["from"].y][mv["from"].x]
		sim[mv["from"].y][mv["from"].x] = null
		if not is_in_check(sim, my_side):
			valid.append(mv)
	return valid

func get_pseudo_moves(b: Array, pos: Vector2i) -> Array[Dictionary]:
	var moves: Array[Dictionary] = []
	var p = b[pos.y][pos.x]
	if p == null:
		return moves
	var side: int = p["side"]
	var pt: int = p["type"]

	match pt:
		PieceType.KING, PieceType.GUARD:
			for d: Vector2i in [Vector2i(1,0), Vector2i(-1,0), Vector2i(0,1), Vector2i(0,-1), Vector2i(1,1), Vector2i(1,-1), Vector2i(-1,1), Vector2i(-1,-1)]:
				if abs(d.x) + abs(d.y) == 2 and not _can_use_palace_diag(pos, pos + d):
					continue
				var np: Vector2i = pos + d
				if _in_palace(np, side) and _can_land(b, np, side):
					moves.append({"from": pos, "to": np})
		PieceType.CHARIOT:
			for d: Vector2i in [Vector2i(1,0), Vector2i(-1,0), Vector2i(0,1), Vector2i(0,-1)]:
				var cur: Vector2i = pos + d
				while _in_bounds(cur):
					if b[cur.y][cur.x] == null:
						moves.append({"from": pos, "to": cur})
					else:
						if b[cur.y][cur.x]["side"] != side:
							moves.append({"from": pos, "to": cur})
						break
					cur += d
		PieceType.CANNON:
			for d: Vector2i in [Vector2i(1,0), Vector2i(-1,0), Vector2i(0,1), Vector2i(0,-1)]:
				var cur: Vector2i = pos + d
				var bridged := false
				while _in_bounds(cur):
					var cell_p = b[cur.y][cur.x]
					if not bridged:
						if cell_p != null:
							if cell_p["type"] == PieceType.CANNON:
								break
							bridged = true
					else:
						if cell_p == null:
							moves.append({"from": pos, "to": cur})
						else:
							if cell_p["side"] != side and cell_p["type"] != PieceType.CANNON:
								moves.append({"from": pos, "to": cur})
							break
					cur += d
		PieceType.HORSE:
			var steps := [
				[Vector2i(0,-1), Vector2i(-1,-2)], [Vector2i(0,-1), Vector2i(1,-2)],
				[Vector2i(0,1), Vector2i(-1,2)], [Vector2i(0,1), Vector2i(1,2)],
				[Vector2i(-1,0), Vector2i(-2,-1)], [Vector2i(-1,0), Vector2i(-2,1)],
				[Vector2i(1,0), Vector2i(2,-1)], [Vector2i(1,0), Vector2i(2,1)]
			]
			for st in steps:
				var neck: Vector2i = pos + st[0]
				var dst: Vector2i = pos + st[1]
				if _in_bounds(dst) and b[neck.y][neck.x] == null and _can_land(b, dst, side):
					moves.append({"from": pos, "to": dst})
		PieceType.ELEPHANT:
			var steps := [
				[Vector2i(0,-1), Vector2i(-1,-2), Vector2i(-2,-3)],
				[Vector2i(0,-1), Vector2i(1,-2), Vector2i(2,-3)],
				[Vector2i(0,1), Vector2i(-1,2), Vector2i(-2,3)],
				[Vector2i(0,1), Vector2i(1,2), Vector2i(2,3)],
				[Vector2i(-1,0), Vector2i(-2,-1), Vector2i(-3,-2)],
				[Vector2i(-1,0), Vector2i(-2,1), Vector2i(-3,2)],
				[Vector2i(1,0), Vector2i(2,-1), Vector2i(3,-2)],
				[Vector2i(1,0), Vector2i(2,1), Vector2i(3,2)]
			]
			for st in steps:
				var n1: Vector2i = pos + st[0]
				var n2: Vector2i = pos + st[1]
				var dst: Vector2i = pos + st[2]
				if _in_bounds(dst) and b[n1.y][n1.x] == null and b[n2.y][n2.x] == null and _can_land(b, dst, side):
					moves.append({"from": pos, "to": dst})
		PieceType.SOLDIER:
			var fwd := -1 if side == Side.CHU else 1
			for d: Vector2i in [Vector2i(0, fwd), Vector2i(-1, 0), Vector2i(1, 0)]:
				var np: Vector2i = pos + d
				if _in_bounds(np) and _can_land(b, np, side):
					moves.append({"from": pos, "to": np})
	return moves

func is_in_check(b: Array, side: int) -> bool:
	var king_pos := Vector2i(-1, -1)
	for r in range(ROWS):
		for c in range(COLS):
			var p = b[r][c]
			if p != null and p["side"] == side and p["type"] == PieceType.KING:
				king_pos = Vector2i(c, r)
				break
	if king_pos.x == -1:
		return true
	var enemy := Side.HAN if side == Side.CHU else Side.CHU
	for r in range(ROWS):
		for c in range(COLS):
			var p = b[r][c]
			if p != null and p["side"] == enemy:
				for mv in get_pseudo_moves(b, Vector2i(c, r)):
					if mv["to"] == king_pos:
						return true
	return false

func _in_bounds(p: Vector2i) -> bool:
	return p.x >= 0 and p.x < COLS and p.y >= 0 and p.y < ROWS

func _in_palace(p: Vector2i, side: int) -> bool:
	if p.x < 3 or p.x > 5:
		return false
	return (p.y >= 7 and p.y <= 9) if side == Side.CHU else (p.y >= 0 and p.y <= 2)

func _can_use_palace_diag(a: Vector2i, b_pos: Vector2i) -> bool:
	var centers := [Vector2i(4, 1), Vector2i(4, 8)]
	return (a in centers) or (b_pos in centers)

func _can_land(b: Array, p: Vector2i, side: int) -> bool:
	return b[p.y][p.x] == null or b[p.y][p.x]["side"] != side

func _clone_board(b: Array) -> Array:
	var cp := []
	for r in range(ROWS):
		var row := []
		for c in range(COLS):
			row.append(b[r][c].duplicate() if b[r][c] != null else null)
		cp.append(row)
	return cp

# --- 16-Bit 2.5D 입체 도트 그래픽 & 현장 배틀 타격 렌더링 ---
func _draw() -> void:
	var font := ThemeDB.fallback_font
	showcase_btn_rects.clear()
	option_btn_rects.clear()

	# 1. 좌측 HUD 패널
	draw_rect(Rect2(16, 20, 294, 840), Color("#111625"), true)
	draw_rect(Rect2(16, 20, 294, 840), Color("#f5b700"), false, 3.0)
	draw_string(font, Vector2(32, 54), "MEDIEVAL PIXEL JANGGI", HORIZONTAL_ALIGNMENT_LEFT, -1, 19, Color("#facc15"))
	draw_string(font, Vector2(32, 76), "내 모니터: %dx%d | 2.5D Battle" % [detected_screen_size.x, detected_screen_size.y], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#34d399"))

	# 좌측 상단: [🖥️ 해상도 · 🔊 사운드 옵션 열기 (O키)] 버튼
	var opt_open_btn := Rect2(28, 90, 270, 30)
	draw_rect(opt_open_btn, Color("#b45309") if options_open else Color("#1e3a8a"), true)
	draw_rect(opt_open_btn, Color("#facc15"), false, 2.0)
	draw_string(font, Vector2(40, 110), "🖥️ 해상도 · 🔊 사운드 옵션 [O키]", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#fef08a"))
	option_btn_rects.append({"rect": opt_open_btn, "action": "toggle_options", "value": 0})

	# [🧊 2.5D 입체 장기판 ON/OFF (V키)] 버튼
	var view3d_btn := Rect2(28, 126, 270, 30)
	draw_rect(view3d_btn, Color("#065f46") if view_3d_mode else Color("#1e293b"), true)
	draw_rect(view3d_btn, Color("#34d399") if view_3d_mode else Color("#64748b"), false, 2.0)
	draw_string(font, Vector2(40, 146), ("🧊 2.5D 입체판 + 현장타격 ON [V]" if view_3d_mode else "📐 2D 평면판 + 현장타격 [V]"), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#ffffff"))
	option_btn_rects.append({"rect": view3d_btn, "action": "toggle_3d", "value": 0})

	draw_string(font, Vector2(32, 180), "[한(HAN) 진영 - 후공 (兵)]", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("#ef4444"))
	draw_string(font, Vector2(32, 200), FACTION_NAMES[han_faction], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#f8fafc"))

	draw_string(font, Vector2(32, 230), "[초(CHU) 진영 - 선공 (卒)]", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("#10b981"))
	draw_string(font, Vector2(32, 250), FACTION_NAMES[chu_faction], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#f8fafc"))

	draw_string(font, Vector2(32, 284), "[조작 및 옵션 단축키]", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("#facc15"))
	draw_string(font, Vector2(32, 306), "• [V] 키: 2.5D 입체판 / 2D 평면 전환", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#34d399"))
	draw_string(font, Vector2(32, 326), "• [O] 키: 해상도 · 사운드 옵션 창", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#fde047"))
	draw_string(font, Vector2(32, 346), "• [F11] 키: 전체화면 / [M] 키: 음소거", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#fde047"))
	draw_string(font, Vector2(32, 366), "• [1]/[2] 키: 초/한 국가 스킨 변경", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#cbd5e1"))
	draw_string(font, Vector2(32, 386), "• [3]/[4] 키: 쫄 5단 모션/진영 전환", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#38bdf8"))
	draw_string(font, Vector2(32, 406), "• [R] 키: 새 대국 초기화", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#cbd5e1"))

	# 좌측 중간: 빠른 사운드 & 테마 상태 표시 바
	var quick_snd_btn := Rect2(28, 418, 130, 28)
	draw_rect(quick_snd_btn, Color("#065f46") if sound_enabled else Color("#7f1d1d"), true)
	draw_rect(quick_snd_btn, Color("#34d399") if sound_enabled else Color("#f87171"), false, 1.5)
	draw_string(font, Vector2(36, 437), ("🔊 사운드 %d%%" % int(master_volume * 100)) if sound_enabled else "🔇 음소거됨", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#ffffff"))
	option_btn_rects.append({"rect": quick_snd_btn, "action": "toggle_sound", "value": 0})

	var quick_theme_btn := Rect2(166, 418, 132, 28)
	draw_rect(quick_theme_btn, Color("#1e293b"), true)
	draw_rect(quick_theme_btn, Color("#facc15"), false, 1.5)
	draw_string(font, Vector2(174, 437), "🎨 판 테마 변경", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#fef08a"))
	option_btn_rects.append({"rect": quick_theme_btn, "action": "set_board_theme", "value": board_theme_idx + 1})

	# 좌측 하단: 쫄(SOLDIER) 전술 특징 요약
	draw_rect(Rect2(28, 460, 270, 380), Color("#0b0f19"), true)
	draw_rect(Rect2(28, 460, 270, 380), Color("#334155"), false, 2.0)
	draw_string(font, Vector2(40, 488), "🛡️ 2.5D 입간판 기물 & 현장 타격", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color("#facc15"))
	draw_string(font, Vector2(40, 514), "• 원근 투영: 사다리꼴 3D 기울임 보드", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#34d399"))
	draw_string(font, Vector2(40, 536), "• 두께 단면: 전면 40px 입체 목재/석재 절벽", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#e2e8f0"))
	draw_string(font, Vector2(40, 558), "• 입간판 기물: 바닥 그림자 + 3D 받침대", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#e2e8f0"))
	draw_string(font, Vector2(40, 580), "• 현장 타격: 별도 팝업 없이 장기판 위에서", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#facc15"))
	draw_string(font, Vector2(40, 602), "  돌진·도약·포격·번개·3D 파편 폭발 직격!", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#f87171"))
	draw_string(font, Vector2(40, 622), "• 한자 인장: 11x11 도트 '卒' / '兵'", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#38bdf8"))

	# 좌측 하단 미니 2x 프리뷰 (초나라 졸 vs 한나라 병)
	var f_idle := int(floor(anim_tick * 5.0)) % 4
	var chu_sol_tex := SpriteGen.get_sprite_texture(PieceType.SOLDIER, Side.CHU, chu_faction, SpriteGen.AnimState.IDLE, f_idle)
	var han_sol_tex := SpriteGen.get_sprite_texture(PieceType.SOLDIER, Side.HAN, han_faction, SpriteGen.AnimState.ATTACK, f_idle)
	draw_texture_rect(chu_sol_tex, Rect2(48, 690, 96, 96), false)
	draw_texture_rect(han_sol_tex, Rect2(172, 690, 96, 96), false)
	draw_string(font, Vector2(60, 810), "초 진영 졸(卒)", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#10b981"))
	draw_string(font, Vector2(184, 810), "한 진영 병(兵)", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#ef4444"))

	# 상단 전황 메시지 바
	draw_rect(Rect2(326, 20, 596, 46), Color("#111625"), true)
	draw_rect(Rect2(326, 20, 596, 46), Color("#f5b700"), false, 2.0)
	draw_string(font, Vector2(342, 49), status_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color("#fef08a"))

	# 2. 16-Bit 2.5D 입체 도트 장기판 렌더링 (사다리꼴 원근 투영 + 전면 3D 두께 단면)
	var b_theme: Dictionary = BOARD_THEMES[board_theme_idx]
	var pad := 0.48
	var f_tl: Vector2 = _project_board_coord(-pad, -pad)["pos"]
	var f_tr: Vector2 = _project_board_coord((COLS - 1) + pad, -pad)["pos"]
	var f_br: Vector2 = _project_board_coord((COLS - 1) + pad, (ROWS - 1) + pad)["pos"]
	var f_bl: Vector2 = _project_board_coord(-pad, (ROWS - 1) + pad)["pos"]
	var slab_h := 38.0 if view_3d_mode else 10.0

	# 2-1. 3D 바닥 그림자 (Drop Shadow)
	var sh_pts := PackedVector2Array([
		f_tl + Vector2(-10, 18),
		f_tr + Vector2(10, 18),
		f_br + Vector2(18, slab_h + 24),
		f_bl + Vector2(-18, slab_h + 24)
	])
	draw_colored_polygon(sh_pts, Color(0, 0, 0, 0.62))

	# 2-2. 전면 3D 두께 절벽(Front Extrusion Slab)
	var slab_pts := PackedVector2Array([
		f_bl,
		f_br,
		f_br + Vector2(0, slab_h),
		f_bl + Vector2(0, slab_h)
	])
	draw_colored_polygon(slab_pts, Color(b_theme["frame"]).darkened(0.35))
	draw_polyline(PackedVector2Array([f_bl, f_br, f_br + Vector2(0, slab_h), f_bl + Vector2(0, slab_h), f_bl]), Color(b_theme["border"]).darkened(0.15), 2.5)

	if view_3d_mode:
		# 전면 두께 단면 황동 기둥 및 명패
		draw_rect(Rect2(f_bl.x, f_bl.y + 2, 18, slab_h - 4), Color("#b45309"), true)
		draw_rect(Rect2(f_br.x - 18, f_br.y + 2, 18, slab_h - 4), Color("#b45309"), true)
		draw_line(f_bl + Vector2(18, slab_h * 0.5), f_br + Vector2(-18, slab_h * 0.5), Color("#f5b700"), 1.5)
		var plaque_c := (f_bl + f_br) * 0.5 + Vector2(0, slab_h * 0.5)
		draw_rect(Rect2(plaque_c.x - 95, plaque_c.y - 10, 190, 20), Color("#090d16"), true)
		draw_rect(Rect2(plaque_c.x - 95, plaque_c.y - 10, 190, 20), Color("#facc15"), false, 1.5)
		draw_string(font, plaque_c + Vector2(-78, 5), "★ 2.5D BATTLE JANGGI ★", HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color("#fef08a"))

	# 2-3. 상판 외곽 프레임 & 내부 표면 사다리꼴
	var frame_pts := PackedVector2Array([f_tl, f_tr, f_br, f_bl])
	draw_colored_polygon(frame_pts, Color(b_theme["frame"]))
	draw_polyline(PackedVector2Array([f_tl, f_tr, f_br, f_bl, f_tl]), Color(b_theme["border"]), 3.5)

	var s_tl: Vector2 = _project_board_coord(0.0, 0.0)["pos"]
	var s_tr: Vector2 = _project_board_coord(float(COLS - 1), 0.0)["pos"]
	var s_br: Vector2 = _project_board_coord(float(COLS - 1), float(ROWS - 1))["pos"]
	var s_bl: Vector2 = _project_board_coord(0.0, float(ROWS - 1))["pos"]
	draw_colored_polygon(PackedVector2Array([s_tl, s_tr, s_br, s_bl]), Color(b_theme["surface"]))

	# 2-4. 원근 궁성 영역 하이라이트
	var hp_tl: Vector2 = _project_board_coord(3.0, 0.0)["pos"]
	var hp_tr: Vector2 = _project_board_coord(5.0, 0.0)["pos"]
	var hp_br: Vector2 = _project_board_coord(5.0, 2.0)["pos"]
	var hp_bl: Vector2 = _project_board_coord(3.0, 2.0)["pos"]
	draw_colored_polygon(PackedVector2Array([hp_tl, hp_tr, hp_br, hp_bl]), Color(0.45, 0.12, 0.15, 0.55))

	var cp_tl: Vector2 = _project_board_coord(3.0, 7.0)["pos"]
	var cp_tr: Vector2 = _project_board_coord(5.0, 7.0)["pos"]
	var cp_br: Vector2 = _project_board_coord(5.0, 9.0)["pos"]
	var cp_bl: Vector2 = _project_board_coord(3.0, 9.0)["pos"]
	draw_colored_polygon(PackedVector2Array([cp_tl, cp_tr, cp_br, cp_bl]), Color(0.06, 0.35, 0.25, 0.55))

	# 2-5. 원근 격자선 & 궁성 대각선
	var line_col := Color(b_theme["line"])
	for r in range(ROWS):
		var p_left: Vector2 = _project_board_coord(0.0, float(r))["pos"]
		var p_right: Vector2 = _project_board_coord(float(COLS - 1), float(r))["pos"]
		draw_line(p_left, p_right, line_col, 2.0)
	for c in range(COLS):
		var p_top: Vector2 = _project_board_coord(float(c), 0.0)["pos"]
		var p_bot: Vector2 = _project_board_coord(float(c), float(ROWS - 1))["pos"]
		draw_line(p_top, p_bot, line_col, 2.0)

	draw_line(hp_tl, hp_br, line_col, 2.0)
	draw_line(hp_tr, hp_bl, line_col, 2.0)
	draw_line(cp_tl, cp_br, line_col, 2.0)
	draw_line(cp_tr, cp_bl, line_col, 2.0)

	# 2-6. 착수/장군 바닥 충격파 링 (board_ambient_fx)
	for fx in board_ambient_fx:
		var prog := clampf(float(fx["timer"]) / float(fx["duration"]), 0.0, 1.0)
		var cell_v: Vector2i = fx["cell"]
		var proj_fx := _project_board_coord(float(cell_v.x), float(cell_v.y))
		var fpos: Vector2 = proj_fx["pos"]
		var fsc: float = proj_fx["scale"]
		var rx := lerpf(10.0, 46.0, prog) * fsc
		var ry := rx * (0.62 if view_3d_mode else 1.0)
		var col_fx: Color = fx["color"]
		col_fx.a = (1.0 - prog) * 0.85
		_draw_perspective_ellipse_outline(fpos, rx, ry, col_fx, 3.0)

	# 3. 합법 이동 타겟 표시 (원근 타원 마커)
	for mv in legal_moves:
		var tp: Vector2i = mv["to"]
		var proj_t := _project_board_coord(float(tp.x), float(tp.y))
		var center: Vector2 = proj_t["pos"]
		var tsc: float = proj_t["scale"]
		if board[tp.y][tp.x] != null:
			_draw_perspective_ellipse_outline(center, 27.0 * tsc, (18.0 if view_3d_mode else 27.0) * tsc, Color("#ef4444"), 3.0)
		else:
			_draw_perspective_ellipse_filled(center, 9.0 * tsc, (6.0 if view_3d_mode else 9.0) * tsc, Color("#10b981"))

	# 4. 보드 위 모든 기물을 뒷줄(r=0)부터 앞줄(r=9) 순서로 2.5D 입간판 렌더링
	var board_frame := int(floor(anim_tick * 5.0))
	for r in range(ROWS):
		for c in range(COLS):
			if battle_active:
				var bf: Vector2i = pending_move["from"]
				var bt: Vector2i = pending_move["to"]
				if (c == bf.x and r == bf.y) or (c == bt.x and r == bt.y):
					continue
			var p = board[r][c]
			if p != null:
				var proj_u := _project_board_coord(float(c), float(r))
				var pos: Vector2 = proj_u["pos"]
				var usc: float = proj_u["scale"]
				var is_sel := (selected_pos == Vector2i(c, r))
				var u_anim := SpriteGen.AnimState.MOVE if is_sel else SpriteGen.AnimState.IDLE
				var z_lift := (7.0 + sin(anim_tick * 7.0) * 3.0) if is_sel else 0.0
				_draw_pixel_unit(pos, p["type"], p["side"], u_anim, board_frame + c, 1.28 * usc, is_sel, z_lift)

	# 5. 장기판 현장(On-Board) 배틀 타격 연출 (별도 아레나 창 없이 보드 위에서 직접 타격!)
	if battle_active:
		_draw_on_board_battle_duel(font)

	# 6. 우측 '[쫄(卒/兵) 도트 디자인 & 모션 뷰어]' 패널 렌더링
	_draw_soldier_showcase_panel(font)

	# 7. 내 컴퓨터 해상도 · 장기판 디자인 · 사운드 옵션 오버레이
	if options_open:
		_draw_options_modal_overlay(font)

func _draw_perspective_ellipse_filled(center: Vector2, rx: float, ry: float, col: Color) -> void:
	var pts := PackedVector2Array()
	for i in range(20):
		var ang := TAU * float(i) / 20.0
		pts.append(center + Vector2(cos(ang) * rx, sin(ang) * ry))
	draw_colored_polygon(pts, col)

func _draw_perspective_ellipse_outline(center: Vector2, rx: float, ry: float, col: Color, width: float) -> void:
	var pts := PackedVector2Array()
	for i in range(25):
		var ang := TAU * float(i) / 24.0
		pts.append(center + Vector2(cos(ang) * rx, sin(ang) * ry))
	draw_polyline(pts, col, width)

func _draw_pixel_unit(pos: Vector2, pt: int, side: int, anim_state: int, frame: int, scale_mul: float, is_sel: bool, z_lift: float = 0.0) -> void:
	var fac := chu_faction if side == Side.CHU else han_faction
	var tex := SpriteGen.get_sprite_texture(pt, side, fac, anim_state, frame)
	var draw_sz := 48.0 * scale_mul

	# 2.5D 바닥 그림자 & 3D 원반 받침대(Pedestal)
	var sh_rx := draw_sz * (0.36 if z_lift <= 0.1 else 0.28)
	var sh_ry := sh_rx * (0.52 if view_3d_mode else 0.75)
	_draw_perspective_ellipse_filled(pos + Vector2(0, 4.0), sh_rx, sh_ry, Color(0, 0, 0, 0.52))

	if view_3d_mode:
		var base_y := pos.y - z_lift
		var ped_col := Color("#065f46") if side == Side.CHU else Color("#7f1d1d")
		var rim_col := Color("#34d399") if side == Side.CHU else Color("#f87171")
		_draw_perspective_ellipse_filled(Vector2(pos.x, base_y + 4.0), draw_sz * 0.31, draw_sz * 0.16, ped_col.darkened(0.45))
		_draw_perspective_ellipse_filled(Vector2(pos.x, base_y), draw_sz * 0.31, draw_sz * 0.16, ped_col)
		_draw_perspective_ellipse_outline(Vector2(pos.x, base_y), draw_sz * 0.31, draw_sz * 0.16, Color("#facc15") if is_sel else rim_col, 2.0 if is_sel else 1.3)

	# 기물을 입간판(Standing Billboard)처럼 발끝이 격자 교차점에 서도록 배치
	var anchor_y := 0.80 if view_3d_mode else 0.54
	var top_left := Vector2(pos.x - draw_sz * 0.5, pos.y - z_lift - draw_sz * anchor_y)

	if is_sel:
		_draw_perspective_ellipse_outline(pos, draw_sz * 0.44, draw_sz * (0.25 if view_3d_mode else 0.44), Color("#facc15"), 2.5)

	draw_texture_rect(tex, Rect2(top_left, Vector2(draw_sz, draw_sz)), false)

# --- 우측 '[쫄(卒/兵) 도트 디자인 & 모션 뷰어]' ---
func _draw_soldier_showcase_panel(font: Font) -> void:
	var px := 938.0
	var pw := 406.0
	draw_rect(Rect2(px, 20, pw, 840), Color("#111625"), true)
	draw_rect(Rect2(px, 20, pw, 840), Color("#f5b700"), false, 3.0)

	draw_string(font, Vector2(px + 18, 54), "🛡️ [쫄(卒/兵) 도트 디자인 & 모션 뷰어]", HORIZONTAL_ALIGNMENT_LEFT, -1, 17, Color("#facc15"))
	draw_string(font, Vector2(px + 18, 78), "48x48 도트 스프라이트 4배(4x) 확대 인스펙터", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#94a3b8"))

	# 4x 확대 도트 스테이지 박스 (192x192 스프라이트)
	var stage_rect := Rect2(px + 20, 92, 216, 216)
	draw_rect(stage_rect, Color("#090d16"), true)
	# 도트 격자 배경선
	for gx in range(1, 9):
		var lx := stage_rect.position.x + gx * 24
		draw_line(Vector2(lx, stage_rect.position.y), Vector2(lx, stage_rect.end.y), Color(1, 1, 1, 0.05), 1.0)
	for gy in range(1, 9):
		var ly := stage_rect.position.y + gy * 24
		draw_line(Vector2(stage_rect.position.x, ly), Vector2(stage_rect.end.x, ly), Color(1, 1, 1, 0.05), 1.0)
	draw_rect(stage_rect, Color("#38bdf8"), false, 2.0)

	var active_fac := chu_faction if showcase_side == Side.CHU else han_faction
	var f_cnt := SpriteGen.get_frame_count(showcase_anim_state)
	var cur_frame := int(floor(anim_tick * 5.5)) % f_cnt
	var sol_tex := SpriteGen.get_sprite_texture(PieceType.SOLDIER, showcase_side, active_fac, showcase_anim_state, cur_frame)

	# 4배(4x = 192x192) 확대 도트 렌더링!
	draw_texture_rect(sol_tex, Rect2(stage_rect.position + Vector2(12, 12), Vector2(192, 192)), false)
	draw_string(font, Vector2(stage_rect.position.x + 10, stage_rect.end.y - 8), "4X ZOOM (48x48px) | Frame %d/%d" % [cur_frame + 1, f_cnt], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#38bdf8"))

	# 스테이지 우측: 5단계 모션 전환 클릭 버튼들 ([3]번 키와 연동)
	draw_string(font, Vector2(px + 246, 108), "[5단 모션 선택 / 3키]", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#facc15"))
	var anim_labels := ["1. IDLE (숨쉬기)", "2. MOVE (행군)", "3. ATTACK (찌르기)", "4. HIT (방어)", "5. DEATH (파편)"]
	for i in range(5):
		var btn_r := Rect2(px + 246, 118 + i * 32, 142, 26)
		var is_cur := (showcase_anim_state == i)
		draw_rect(btn_r, Color("#1e3a8a") if is_cur else Color("#1e293b"), true)
		draw_rect(btn_r, Color("#facc15") if is_cur else Color("#475569"), false, 1.5)
		draw_string(font, Vector2(btn_r.position.x + 8, btn_r.position.y + 18), anim_labels[i], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#ffffff") if is_cur else Color("#cbd5e1"))
		showcase_btn_rects.append({"rect": btn_r, "action": "anim", "value": i})

	# 초(卒) / 한(兵) 전환 버튼
	var side_btn := Rect2(px + 246, 282, 142, 26)
	draw_rect(side_btn, Color("#065f46") if showcase_side == Side.CHU else Color("#7f1d1d"), true)
	draw_rect(side_btn, Color("#34d399") if showcase_side == Side.CHU else Color("#f87171"), false, 1.5)
	var side_str := "진영: 초나라 졸(卒)" if showcase_side == Side.CHU else "진영: 한나라 병(兵)"
	draw_string(font, Vector2(side_btn.position.x + 8, side_btn.position.y + 18), side_str, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#ffffff"))
	showcase_btn_rects.append({"rect": side_btn, "action": "side", "value": 0})

	# 현재 선택된 국가 쫄(SOLDIER) 부위별 도트 디자인 해설
	draw_rect(Rect2(px + 20, 322, 368, 155), Color("#0b0f19"), true)
	draw_rect(Rect2(px + 20, 322, 368, 155), Color("#334155"), false, 1.5)
	draw_string(font, Vector2(px + 30, 346), "🎨 " + FACTION_NAMES[active_fac], HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("#facc15"))
	var notes: Array = SOLDIER_DESIGN_NOTES[active_fac]
	for idx in range(notes.size()):
		draw_string(font, Vector2(px + 30, 372 + idx * 24), notes[idx], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#e2e8f0"))

	# 4대 중세 국가별 쫄(SOLDIER) 2x 도트 비교 갤러리 (클릭 시 즉시 스킨 적용)
	draw_string(font, Vector2(px + 20, 504), "⚔️ 4대 국가별 쫄(SOLDIER) 도트 비교 (클릭하여 변경)", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("#facc15"))
	var fac_short := ["고려 팽배수", "성전 기사단", "비잔틴 스쿠타토이", "맘루크 가지"]
	for f_idx in range(4):
		var col_i := f_idx % 2
		var row_i := f_idx / 2
		var card_r := Rect2(px + 20 + col_i * 188, 518 + row_i * 156, 180, 146)
		var is_sel_fac := (active_fac == f_idx)
		draw_rect(card_r, Color("#172554") if is_sel_fac else Color("#0b0f19"), true)
		draw_rect(card_r, Color("#facc15") if is_sel_fac else Color("#334155"), false, 2.0 if is_sel_fac else 1.0)

		var cmp_tex := SpriteGen.get_sprite_texture(PieceType.SOLDIER, showcase_side, f_idx, showcase_anim_state, cur_frame)
		draw_texture_rect(cmp_tex, Rect2(card_r.position + Vector2(42, 8), Vector2(96, 96)), false)
		draw_string(font, Vector2(card_r.position.x + 12, card_r.end.y - 14), fac_short[f_idx], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#fef08a") if is_sel_fac else Color("#cbd5e1"))
		showcase_btn_rects.append({"rect": card_r, "action": "faction", "value": f_idx})

# --- 장기판 현장(On-Board) 배틀 타격 연출 (별도 팝업 씬 없이 보드 위에서 직접 타격!) ---
func _draw_on_board_battle_duel(font: Font) -> void:
	var from_c: Vector2i = pending_move["from"]
	var to_c: Vector2i = pending_move["to"]
	var proj_from := _project_board_coord(float(from_c.x), float(from_c.y))
	var proj_to := _project_board_coord(float(to_c.x), float(to_c.y))
	var p_from: Vector2 = proj_from["pos"]
	var p_to: Vector2 = proj_to["pos"]
	var sc_from: float = proj_from["scale"]
	var sc_to: float = proj_to["scale"]

	var p := clampf(battle_timer / 0.92, 0.0, 1.0)
	var atk_type: int = battle_attacker["type"]

	# 1. 타격 지점 원근 마법진 & 다중 충격파 링
	var ring_r := lerpf(16.0, 62.0, p) * sc_to
	_draw_perspective_ellipse_outline(p_to, ring_r, ring_r * (0.62 if view_3d_mode else 1.0), Color(0.98, 0.8, 0.08, 1.0 - p * 0.75), 3.0)
	if p >= 0.34:
		var shock_p := clampf((p - 0.34) / 0.66, 0.0, 1.0)
		var sr := lerpf(12.0, 82.0, shock_p) * sc_to
		_draw_perspective_ellipse_outline(p_to, sr, sr * (0.62 if view_3d_mode else 1.0), Color(0.94, 0.27, 0.27, 1.0 - shock_p), 4.0)

	# 2. 방어 기물 피격 진동 · HP 게이지 · 격파 연출
	var def_pos := p_to
	var def_state := SpriteGen.AnimState.IDLE
	if p >= 0.62:
		def_state = SpriteGen.AnimState.DEATH
		def_pos += Vector2(sin(p * 85.0) * 8.0, 0.0)
	elif p >= 0.34:
		def_state = SpriteGen.AnimState.HIT
		def_pos += Vector2(sin(p * 65.0) * 6.0, 0.0)

	_draw_pixel_unit(def_pos, battle_defender["type"], battle_defender["side"], def_state, int(p * 10.0), 1.42 * sc_to, false, 0.0)

	# 방어 기물 머리 위 HP 게이지 바
	var hp_ratio := clampf(1.0 - maxf(0.0, (p - 0.32) / 0.42), 0.0, 1.0)
	var hp_rect := Rect2(p_to.x - 28.0, p_to.y - 68.0 * sc_to, 56.0, 8.0)
	draw_rect(hp_rect, Color("#090d16"), true)
	draw_rect(Rect2(hp_rect.position + Vector2(1, 1), Vector2((hp_rect.size.x - 2.0) * hp_ratio, hp_rect.size.y - 2.0)), Color("#ef4444") if hp_ratio < 0.4 else Color("#10b981"), true)
	draw_rect(hp_rect, Color("#facc15"), false, 1.2)

	# 3. 공격 기물 2.5D 돌진 / 3D 점프 찍기 / 포(包) 포물선 화포 폭격
	var atk_pos := p_from
	var atk_sc := sc_from
	var atk_z := 0.0
	var atk_state := SpriteGen.AnimState.MOVE if p < 0.30 else SpriteGen.AnimState.ATTACK

	if atk_type == PieceType.CANNON:
		# 포(包)는 제자리에서 반동과 함께 포물선 화포탄 발사!
		var recoil := -8.0 * sin(clampf(p * 3.0, 0.0, 1.0) * PI)
		atk_pos = p_from + Vector2(0, recoil)
		_draw_pixel_unit(atk_pos, atk_type, battle_attacker["side"], atk_state, int(p * 12.0) % 4, 1.40 * atk_sc, true, 4.0)
		if p < 0.58:
			var proj_t := clampf(p / 0.52, 0.0, 1.0)
			var shell_pos := p_from.lerp(p_to, proj_t) - Vector2(0, sin(proj_t * PI) * 115.0)
			draw_circle(shell_pos, 11.0, Color("#f97316"))
			draw_circle(shell_pos, 6.0, Color("#fef08a"))
	else:
		var dash_t := clampf(p / 0.56, 0.0, 1.0)
		var eased := 1.0 - pow(1.0 - dash_t, 3.0)
		atk_pos = p_from.lerp(p_to, eased)
		atk_sc = lerpf(sc_from, sc_to, eased)
		if atk_type == PieceType.HORSE or atk_type == PieceType.ELEPHANT:
			atk_z = sin(dash_t * PI) * 58.0
		else:
			atk_z = sin(dash_t * PI) * 22.0
		_draw_pixel_unit(atk_pos, atk_type, battle_attacker["side"], atk_state, int(p * 12.0) % 4, 1.46 * atk_sc, true, atk_z)

	# 4. 타격 순간 번개 · X자 참격 · 화염 폭발 이펙트 (장기판 위 현장 발생!)
	if p >= 0.34 and p <= 0.85:
		var slash_len := 36.0 * sc_to
		draw_line(p_to + Vector2(-slash_len, -slash_len), p_to + Vector2(slash_len, slash_len), Color("#fef08a"), 4.0)
		draw_line(p_to + Vector2(slash_len, -slash_len), p_to + Vector2(-slash_len, slash_len), Color("#f97316"), 3.5)
		if atk_type == PieceType.KING or atk_type == PieceType.ELEPHANT or atk_type == PieceType.CANNON:
			# 상단에서 떨어지는 뇌전/폭격 기둥
			draw_line(p_to + Vector2(0, -140), p_to + Vector2(-8, -65), Color("#fef08a"), 4.5)
			draw_line(p_to + Vector2(-8, -65), p_to + Vector2(10, -32), Color("#38bdf8"), 4.0)
			draw_line(p_to + Vector2(10, -32), p_to, Color("#ffffff"), 5.0)

	# 5. 3D 중력·바운스 도트 파편 파티클 렌더링
	for pt in battle_particles:
		var pos_pt: Vector2 = pt["pos"]
		var z_pt: float = pt["z"]
		var sz_pt: float = pt["size"]
		var col_pt: Color = pt["color"]
		draw_rect(Rect2(pos_pt.x - sz_pt * 0.5, pos_pt.y - z_pt - sz_pt * 0.5, sz_pt, sz_pt), col_pt, true)

	# 6. 플로팅 타격 텍스트 팝업
	if p >= 0.34:
		var pop_y := p_to.y - 78.0 * sc_to - (p - 0.34) * 38.0
		draw_string(font, Vector2(p_to.x - 84.0, pop_y), "💥 CRITICAL STRIKE!!", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color("#fef08a"))


# --- 내 컴퓨터 해상도 · 장기판 디자인 · 사운드 환경설정 모달 오버레이 ---
func _draw_options_modal_overlay(font: Font) -> void:
	draw_rect(Rect2(0, 0, 1360, 880), Color(0, 0, 0, 0.85), true)
	var box := Rect2(210, 70, 940, 740)
	draw_rect(box, Color("#111625"), true)
	draw_rect(box, Color("#f5b700"), false, 4.0)

	draw_string(font, Vector2(242, 118), "🖥️ 내 컴퓨터 기준 해상도 · 장기판 디자인 · 🔊 사운드 환경설정", HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color("#facc15"))
	var win_sz := DisplayServer.window_get_size()
	draw_string(font, Vector2(242, 144), "감지된 내 컴퓨터 모니터: %dx%d  |  현재 게임 창 해상도: %dx%d" % [detected_screen_size.x, detected_screen_size.y, win_sz.x, win_sz.y], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#34d399"))

	var close_btn := Rect2(1030, 88, 96, 36)
	draw_rect(close_btn, Color("#7f1d1d"), true)
	draw_rect(close_btn, Color("#f87171"), false, 2.0)
	draw_string(font, Vector2(1048, 112), "✖ 닫기 [O]", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#ffffff"))
	option_btn_rects.append({"rect": close_btn, "action": "toggle_options", "value": 0})

	# 1. 내 컴퓨터 디스플레이 해상도 선택 섹션
	draw_string(font, Vector2(242, 184), "1. 디스플레이 해상도 선택 (내 컴퓨터 모니터 기준)", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color("#fef08a"))
	for i in range(res_presets.size()):
		var col_i := i % 2
		var row_i := i / 2
		var r_btn := Rect2(242 + col_i * 444, 198 + row_i * 46, 428, 38)
		var is_sel := (not is_fullscreen_mode and current_res_idx == i)
		draw_rect(r_btn, Color("#1e3a8a") if is_sel else Color("#1e293b"), true)
		draw_rect(r_btn, Color("#facc15") if is_sel else Color("#475569"), false, 2.0 if is_sel else 1.5)
		draw_string(font, Vector2(r_btn.position.x + 14, r_btn.position.y + 24), ("✔ " if is_sel else "   ") + res_presets[i]["label"], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#ffffff") if is_sel else Color("#cbd5e1"))
		option_btn_rects.append({"rect": r_btn, "action": "set_res", "value": i})

	# 전체화면 전환 버튼
	var fs_btn := Rect2(242, 340, 428, 38)
	draw_rect(fs_btn, Color("#065f46") if is_fullscreen_mode else Color("#1e293b"), true)
	draw_rect(fs_btn, Color("#34d399") if is_fullscreen_mode else Color("#475569"), false, 2.0)
	draw_string(font, Vector2(fs_btn.position.x + 14, fs_btn.position.y + 24), "⛶ 전체화면 모드 (Fullscreen) [F11] : " + ("켜짐 (ON)" if is_fullscreen_mode else "창모드 (Windowed)"), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#ffffff"))
	option_btn_rects.append({"rect": fs_btn, "action": "toggle_fullscreen", "value": 0})

	# 2. 장기판 도트 디자인 테마 선택
	draw_string(font, Vector2(242, 412), "2. 장기판 도트 디자인 테마 선택", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color("#fef08a"))
	for t_i in range(BOARD_THEMES.size()):
		var t_btn := Rect2(242 + t_i * 222, 426, 210, 40)
		var t_sel := (board_theme_idx == t_i)
		draw_rect(t_btn, Color(BOARD_THEMES[t_i]["surface"]), true)
		draw_rect(t_btn, Color("#facc15") if t_sel else Color(BOARD_THEMES[t_i]["border"]), false, 3.0 if t_sel else 1.5)
		draw_string(font, Vector2(t_btn.position.x + 10, t_btn.position.y + 25), ("★ " if t_sel else "") + BOARD_THEMES[t_i]["name"], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#ffffff"))
		option_btn_rects.append({"rect": t_btn, "action": "set_board_theme", "value": t_i})

	# 3. 16-Bit 칩튠 사운드 & 채널별 볼륨 조절
	draw_string(font, Vector2(242, 502), "3. 16-BIT 칩튠 사운드 & 볼륨 믹서 조절", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color("#fef08a"))

	var snd_toggle_btn := Rect2(242, 518, 280, 38)
	draw_rect(snd_toggle_btn, Color("#065f46") if sound_enabled else Color("#7f1d1d"), true)
	draw_rect(snd_toggle_btn, Color("#34d399") if sound_enabled else Color("#f87171"), false, 2.0)
	draw_string(font, Vector2(snd_toggle_btn.position.x + 14, snd_toggle_btn.position.y + 24), "🔊 전체 사운드: " + ("켜짐 (ON)" if sound_enabled else "음소거 (OFF)"), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#ffffff"))
	option_btn_rects.append({"rect": snd_toggle_btn, "action": "toggle_sound", "value": 0})

	var bgm_toggle_btn := Rect2(540, 518, 280, 38)
	draw_rect(bgm_toggle_btn, Color("#1e3a8a") if bgm_enabled else Color("#1e293b"), true)
	draw_rect(bgm_toggle_btn, Color("#38bdf8") if bgm_enabled else Color("#475569"), false, 2.0)
	draw_string(font, Vector2(bgm_toggle_btn.position.x + 14, bgm_toggle_btn.position.y + 24), "🎵 고려 행군 칩튠 BGM: " + ("켜짐 (ON)" if bgm_enabled else "꺼짐 (OFF)"), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#ffffff"))
	option_btn_rects.append({"rect": bgm_toggle_btn, "action": "toggle_bgm", "value": 0})

	var channels := [
		{"label": "마스터 볼륨 (Master)", "val": master_volume, "act": "master_vol"},
		{"label": "배경음악 볼륨 (BGM)", "val": bgm_volume, "act": "bgm_vol"},
		{"label": "착수·이동 효과음 (SFX)", "val": sfx_volume, "act": "sfx_vol"},
		{"label": "배틀체스 처형 타격음", "val": battle_volume, "act": "battle_vol"}
	]
	for c_i in range(channels.size()):
		var ch: Dictionary = channels[c_i]
		var cy := 580 + c_i * 48
		draw_string(font, Vector2(242, cy + 22), ch["label"], HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color("#e2e8f0"))

		var minus_btn := Rect2(480, cy, 44, 34)
		draw_rect(minus_btn, Color("#1e293b"), true)
		draw_rect(minus_btn, Color("#facc15"), false, 1.5)
		draw_string(font, Vector2(495, cy + 23), " - ", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color("#ffffff"))
		option_btn_rects.append({"rect": minus_btn, "action": ch["act"], "value": -0.1})

		# 도트 게이지 바
		var bar_bg := Rect2(536, cy + 5, 320, 24)
		draw_rect(bar_bg, Color("#090d16"), true)
		draw_rect(bar_bg, Color("#475569"), false, 1.5)
		var fill_w := clampf(float(ch["val"]), 0.0, 1.0) * 312.0
		draw_rect(Rect2(540, cy + 9, fill_w, 16), Color("#10b981") if sound_enabled else Color("#64748b"), true)
		draw_string(font, Vector2(675, cy + 22), "%d%%" % int(round(float(ch["val"]) * 100.0)), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color("#fef08a"))

		var plus_btn := Rect2(868, cy, 44, 34)
		draw_rect(plus_btn, Color("#1e293b"), true)
		draw_rect(plus_btn, Color("#facc15"), false, 1.5)
		draw_string(font, Vector2(883, cy + 23), " + ", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color("#ffffff"))
		option_btn_rects.append({"rect": plus_btn, "action": ch["act"], "value": 0.1})

