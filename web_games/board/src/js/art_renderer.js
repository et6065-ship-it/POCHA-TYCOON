/**
 * @fileoverview Medieval Battle-Janggi & Chess HD Pixel Art Illustration Engine v3.0 (window.ArtRenderer)
 * @description
 * High-Density 16-Bit / 32-Bit Pixel Art Illustration & Frame Animation Engine
 * (Octopath Traveler / Metal Slug / Blasphemous / Vanillaware aesthetic)
 * supporting all 7 Korean Janggi classes (KING/궁, CHARIOT/차, CANNON/포, HORSE/마, ELEPHANT/상, GUARD/사, SOLDIER/졸·병)
 * AND all 6 Western Chess classes (KING/킹, QUEEN/퀸, ROOK/룩, BISHOP/비숍, KNIGHT/나이트, PAWN/폰)
 * across 4 Medieval Elite Factions (GORYEO/고려 천군, TEMPLAR/성전 기사단, BYZANTINE/비잔틴 제국군, MAMLUK/맘루크 술탄국).
 *
 * Key Technical Features:
 * - 76x76 High-Density Integer Pixel Canvas (`ctx.imageSmoothingEnabled = false`)
 * - 7-Step Hue-Shifted Color Ramps (`deepShadow`, `bounceLight`, `specHighlight`, `rimLight`)
 * - Selective Outlining (Sel-out) with Top Light-Source Tinting & Internal Corner Subpixel Anti-Aliasing (AA)
 * - NMM (Non-Metallic Metal) Specular Armor Painting, 3-Fold Cloak Drapery Shading & 3-Tone Weapon Gradients
 * - Hand-crafted 11x11 Bitmap Pixel Glyphs for Janggi Hanja & Chess Crowns/Symbols (楚, 漢, 宮, 車, 包, 馬, 象, 士, 卒, 兵, ♔, ♕, ♖, ♗, ♘, ♙, 后, 城, 主教, 騎, 歩)
 * - 48x48 HD Pixel Commander Portrait Renderer (`drawCommanderPortrait`) & SRW/Fire-Emblem Diagonal Battle Cut-In (`drawBattleCutIn`)
 */

(function (global) {
  'use strict';

  // ============================================================================
  // 1. CONSTANTS, ALIASES (JANGGI 7 + CHESS 6) & FACTION 7-STEP PIXEL PALETTES
  // ============================================================================

  const PIECE_ALIASES = {
    // Shared Monarch (Janggi Gung / Chess King)
    KING: 'KING', GUNG: 'KING', JANG: 'KING', K: 'KING',
    '궁': 'KING', '장': 'KING', '초': 'KING', '한': 'KING', '왕': 'KING', '킹': 'KING',
    '楚': 'KING', '漢': 'KING', '宮': 'KING', '王': 'KING', '♔': 'KING', '♚': 'KING',

    // Chess Dedicated Classes (5 + King = 6)
    QUEEN: 'QUEEN', Q: 'QUEEN', '퀸': 'QUEEN', '여왕': 'QUEEN', '여제': 'QUEEN', '♕': 'QUEEN', '♛': 'QUEEN', '后': 'QUEEN',
    ROOK: 'ROOK', '룩': 'ROOK', '성루': 'ROOK', '성탑': 'ROOK', '♖': 'ROOK', '♜': 'ROOK', '城': 'ROOK',
    BISHOP: 'BISHOP', B: 'BISHOP', '비숍': 'BISHOP', '주교': 'BISHOP', '대주교': 'BISHOP', '♗': 'BISHOP', '♝': 'BISHOP', '主教': 'BISHOP',
    KNIGHT: 'KNIGHT', N: 'KNIGHT', '나이트': 'KNIGHT', '기사': 'KNIGHT', '철기병': 'KNIGHT', '♘': 'KNIGHT', '♞': 'KNIGHT', '騎': 'KNIGHT',
    PAWN: 'PAWN', P: 'PAWN', '폰': 'PAWN', '보병': 'PAWN', '♙': 'PAWN', '♟': 'PAWN', '歩': 'PAWN',

    // Janggi Dedicated Classes (7)
    CHARIOT: 'CHARIOT', CAR: 'CHARIOT', CHA: 'CHARIOT', R: 'CHARIOT', '차': 'CHARIOT', '車': 'CHARIOT',
    CANNON: 'CANNON', PO: 'CANNON', C: 'CANNON', '포': 'CANNON', '包': 'CANNON',
    HORSE: 'HORSE', MA: 'HORSE', H: 'HORSE', '마': 'HORSE', '馬': 'HORSE',
    ELEPHANT: 'ELEPHANT', SANG: 'ELEPHANT', E: 'ELEPHANT', '상': 'ELEPHANT', '象': 'ELEPHANT',
    GUARD: 'GUARD', SA: 'GUARD', ADVISOR: 'GUARD', G: 'GUARD', A: 'GUARD', '사': 'GUARD', '士': 'GUARD',
    SOLDIER: 'SOLDIER', JOL: 'SOLDIER', BYEONG: 'SOLDIER', S: 'SOLDIER', '졸': 'SOLDIER', '병': 'SOLDIER', '卒': 'SOLDIER', '兵': 'SOLDIER'
  };

  const SIDE_ALIASES = {
    CHU: 'CHU', CHO: 'CHU', BLUE: 'CHU', GREEN: 'CHU', WHITE: 'CHU', W: 'CHU', PLAYER: 'CHU', P1: 'CHU',
    '초': 'CHU', '楚': 'CHU', '백': 'CHU', '白': 'CHU',
    HAN: 'HAN', RED: 'HAN', CRIMSON: 'HAN', BLACK: 'HAN', B: 'HAN', AI: 'HAN', ENEMY: 'HAN', P2: 'HAN',
    '한': 'HAN', '漢': 'HAN', '흑': 'HAN', '黑': 'HAN'
  };

  const PIECE_META = {
    // --- JANGGI 7 CLASSES ---
    KING: {
      id: 'KING',
      score: 0,
      scaleMultiplier: 1.18,
      pedestalScale: 1.14,
      hanja: { CHU: '楚', HAN: '漢', CHESS: '♔', DEFAULT: '宮' },
      korName: { CHU: '초궁(楚宮)', HAN: '한궁(漢宮)', DEFAULT: '군주(王)' },
      archetype: 'MONARCH'
    },
    CHARIOT: {
      id: 'CHARIOT',
      score: 13,
      scaleMultiplier: 1.12,
      pedestalScale: 1.06,
      hanja: { CHU: '車', HAN: '車', CHESS: '♖', DEFAULT: '車' },
      korName: { CHU: '차(車)', HAN: '차(車)', DEFAULT: '차(車)' },
      archetype: 'HEAVY_SHOCK'
    },
    CANNON: {
      id: 'CANNON',
      score: 7,
      scaleMultiplier: 1.08,
      pedestalScale: 1.04,
      hanja: { CHU: '包', HAN: '包', DEFAULT: '包' },
      korName: { CHU: '포(包)', HAN: '포(包)', DEFAULT: '포(包)' },
      archetype: 'SIEGE_ARTILLERY'
    },
    HORSE: {
      id: 'HORSE',
      score: 5,
      scaleMultiplier: 1.05,
      pedestalScale: 1.00,
      hanja: { CHU: '馬', HAN: '馬', CHESS: '♘', DEFAULT: '馬' },
      korName: { CHU: '마(馬)', HAN: '마(馬)', DEFAULT: '마(馬)' },
      archetype: 'CAVALRY'
    },
    ELEPHANT: {
      id: 'ELEPHANT',
      score: 3,
      scaleMultiplier: 1.18,
      pedestalScale: 1.08,
      hanja: { CHU: '象', HAN: '象', CHESS: '♗', DEFAULT: '象' },
      korName: { CHU: '상(象)', HAN: '상(象)', DEFAULT: '상(象)' },
      archetype: 'WAR_ELEPHANT'
    },
    GUARD: {
      id: 'GUARD',
      score: 3,
      scaleMultiplier: 0.98,
      pedestalScale: 0.94,
      hanja: { CHU: '士', HAN: '士', DEFAULT: '士' },
      korName: { CHU: '사(士)', HAN: '사(士)', DEFAULT: '사(士)' },
      archetype: 'ROYAL_GUARD'
    },
    SOLDIER: {
      id: 'SOLDIER',
      score: 2,
      scaleMultiplier: 0.92,
      pedestalScale: 0.88,
      hanja: { CHU: '卒', HAN: '兵', CHESS: '♙', DEFAULT: '卒' },
      korName: { CHU: '졸(卒)', HAN: '병(兵)', DEFAULT: '졸(卒)' },
      archetype: 'VANGUARD_INFANTRY'
    },

    // --- CHESS DEDICATED CLASSES ---
    QUEEN: {
      id: 'QUEEN',
      score: 9,
      scaleMultiplier: 1.16,
      pedestalScale: 1.12,
      hanja: { CHU: '♕', HAN: '♕', CHESS: '♕', KANJI: '后', DEFAULT: '♕' },
      korName: { CHU: '퀸(♕)', HAN: '퀸(♕)', DEFAULT: '여왕(♕)' },
      archetype: 'EMPRESS_VALKYRIE',
      isChessPiece: true
    },
    ROOK: {
      id: 'ROOK',
      score: 5,
      scaleMultiplier: 1.14,
      pedestalScale: 1.08,
      hanja: { CHU: '♖', HAN: '♖', CHESS: '♖', KANJI: '城', DEFAULT: '♖' },
      korName: { CHU: '룩(♖)', HAN: '룩(♖)', DEFAULT: '성루(♖)' },
      archetype: 'SIEGE_CITADEL',
      isChessPiece: true
    },
    BISHOP: {
      id: 'BISHOP',
      score: 3,
      scaleMultiplier: 1.06,
      pedestalScale: 1.02,
      hanja: { CHU: '♗', HAN: '♗', CHESS: '♗', KANJI: '主教', DEFAULT: '♗' },
      korName: { CHU: '비숍(♗)', HAN: '비숍(♗)', DEFAULT: '대주교(♗)' },
      archetype: 'HIGH_INQUISITOR',
      isChessPiece: true
    },
    KNIGHT: {
      id: 'KNIGHT',
      score: 3,
      scaleMultiplier: 1.08,
      pedestalScale: 1.02,
      hanja: { CHU: '♘', HAN: '♘', CHESS: '♘', KANJI: '騎', DEFAULT: '♘' },
      korName: { CHU: '나이트(♘)', HAN: '나이트(♘)', DEFAULT: '철기병(♘)' },
      archetype: 'HEAVY_CAVALRY',
      isChessPiece: true
    },
    PAWN: {
      id: 'PAWN',
      score: 1,
      scaleMultiplier: 0.94,
      pedestalScale: 0.90,
      hanja: { CHU: '♙', HAN: '♙', CHESS: '♙', KANJI: '歩', DEFAULT: '♙' },
      korName: { CHU: '폰(♙)', HAN: '폰(♙)', DEFAULT: '보병(♙)' },
      archetype: 'SHIELD_INFANTRY',
      isChessPiece: true
    }
  };

  const UNIT_ROSTER = PIECE_META;

  const TEAM_THEMES = {
    CHU: {
      id: 'CHU',
      name: '초(楚)',
      neon: '#10b981',
      neonBright: '#6ee7b7',
      accent: '#0284c7',
      accentDark: '#064e3b',
      pedestalTop: '#0d2622',
      pedestalDither: '#11332d',
      pedestalSide: '#061412',
      pedestalRim: '#34d399',
      hanjaColor: '#a7f3d0',
      hanjaShade: '#10b981',
      hanjaStroke: '#042f2e',
      capeTint: '#0284c7',
      capeMid: '#0369a1',
      capeShade: '#0c4a6e',
      capeDeep: '#082f49',
      capeHighlight: '#38bdf8',
      bannerTint: '#059669'
    },
    HAN: {
      id: 'HAN',
      name: '한(漢)',
      neon: '#ef4444',
      neonBright: '#fca5a5',
      accent: '#dc2626',
      accentDark: '#450a0a',
      pedestalTop: '#2b1114',
      pedestalDither: '#3b161a',
      pedestalSide: '#170709',
      pedestalRim: '#f87171',
      hanjaColor: '#fecaca',
      hanjaShade: '#f87171',
      hanjaStroke: '#450a0a',
      capeTint: '#dc2626',
      capeMid: '#b91c1c',
      capeShade: '#7f1d1d',
      capeDeep: '#450a0a',
      capeHighlight: '#f87171',
      bannerTint: '#b91c1c'
    }
  };

  const FACTION_SKINS = {
    GORYEO: {
      id: 'GORYEO',
      name: '고려 천군 (Goryeo Celestial Iron Army)',
      shortName: '고려 철갑군',
      commanderTitle: '고려 상장군 강감찬',
      subtitle: '개마무사 중장기병과 문종 신기전 화차로 무장한 동방의 도트 철갑 군단',
      emblem: 'SAMJOKOH',
      palette: {
        outline: '#070a14',
        deepShadow: '#0f172a',
        bounceLight: '#1e3a8a',
        specHighlight: '#f8fafc',
        rimLight: '#7dd3fc',
        armorDark: '#0f172a',
        armorPrimary: '#1e293b',
        armorMid: '#334155',
        armorLight: '#64748b',
        armorSecondary: '#1d4ed8',
        armorSecDark: '#1e3a8a',
        armorSecLight: '#3b82f6',
        clothDark: '#7f1d1d',
        cloth: '#b91c1c',
        clothLight: '#ef4444',
        metal: '#cbd5e1',
        metalLight: '#f8fafc',
        metalDark: '#334155',
        gold: '#f59e0b',
        goldLight: '#fde047',
        goldDark: '#92400e',
        goldSpec: '#fef9c3',
        wood: '#78350f',
        woodLight: '#b45309',
        woodDark: '#451a03',
        skin: '#fcd34d',
        skinLight: '#fef08a',
        skinShade: '#d97706',
        skinShadow: '#92400e',
        fxPrimary: '#38bdf8',
        fxSecondary: '#f97316'
      },
      units: {
        KING:     { name: '태조 어가 대장군', weapon: 'SAINGEOM', helm: 'IKSEONGWAN', shield: 'DRAGON_BUCKLER' },
        QUEEN:    { name: '천추태후 신궁 여제', weapon: 'TWIN_PHOENIX_SWORDS', helm: 'PHOENIX_BOGWAN', shield: 'CELESTIAL_ORBS' },
        ROOK:     { name: '철옹성 공성 거병', weapon: 'IRON_CASTLE_MAUL', helm: 'FORTRESS_IRON_HELM', shield: 'CITADEL_TOWER_SHIELD' },
        BISHOP:   { name: '국사 대선사 도술사', weapon: 'LOTUS_CROZIER', helm: 'GOLDEN_DOGWAN', shield: 'TALISMAN_SCROLL' },
        KNIGHT:   { name: '중갑 개마 돌격기병', weapon: 'GAEMA_HEAVY_LANCE', helm: 'HORNED_IRON_MASK', mount: 'ARMORED_WARHORSE' },
        PAWN:     { name: '중갑 방패창병', weapon: 'SPEAR_AND_DAGGER', helm: 'CHOMJU_INFANTRY', shield: 'IRON_PAENGBAE' },
        CHARIOT:  { name: '개마무사 중장전차', weapon: 'GAEMA_LANCE', helm: 'IRON_MASK_CONE', mount: 'IRON_CHARGER' },
        CANNON:   { name: '문종 신기전 화차', weapon: 'HWACHA', helm: 'CHOMJU', artillery: 'HWACHA_CART' },
        HORSE:    { name: '별무반 신기군', weapon: 'FLAIL_AND_BOW', helm: 'CHOMJU_PLUME', mount: 'STEPPE_STEED' },
        ELEPHANT: { name: '착호갑사 전투코끼리', weapon: 'TUSK_GLAIVE', helm: 'TIGER_PELT_HELM', mount: 'EASTERN_ELEPHANT' },
        GUARD:    { name: '내금위 금군 무사', weapon: 'HYEOPDO_GLAIVE', helm: 'PEACOCK_HELM', shield: 'ROUND_BONGHWANG' },
        SOLDIER:  { name: '팽배수 방패창보병', weapon: 'LONG_SPEAR', helm: 'CHOMJU', shield: 'PAENGBAE_SHIELD' }
      }
    },

    TEMPLAR: {
      id: 'TEMPLAR',
      name: '성전 기사단 (The Royal Crusaders)',
      shortName: '성전 기사단',
      commanderTitle: '사자심왕 그랜드마스터',
      subtitle: '풀 플레이트 랜서와 공성 트레뷰셋을 앞세운 서유럽 성기사 도트 군단',
      emblem: 'CROSS',
      palette: {
        outline: '#070a14',
        deepShadow: '#1e1b4b',
        bounceLight: '#7c2d12',
        specHighlight: '#ffffff',
        rimLight: '#fef08a',
        armorDark: '#475569',
        armorPrimary: '#94a3b8',
        armorMid: '#cbd5e1',
        armorLight: '#e2e8f0',
        armorSecondary: '#f1f5f9',
        armorSecDark: '#94a3b8',
        armorSecLight: '#ffffff',
        clothDark: '#7f1d1d',
        cloth: '#dc2626',
        clothLight: '#f87171',
        metal: '#e2e8f0',
        metalLight: '#ffffff',
        metalDark: '#475569',
        gold: '#eab308',
        goldLight: '#fef08a',
        goldDark: '#a16207',
        goldSpec: '#ffffff',
        wood: '#5c4033',
        woodLight: '#854d0e',
        woodDark: '#3b2314',
        skin: '#fed7aa',
        skinLight: '#ffedd5',
        skinShade: '#ea580c',
        skinShadow: '#9a3412',
        fxPrimary: '#fde047',
        fxSecondary: '#ef4444'
      },
      units: {
        KING:     { name: '성전 기사단장 (사자심왕)', weapon: 'TEMPLAR_GREATSWORD', helm: 'CROWN_GREATHELM', shield: 'LION_SHIELD' },
        QUEEN:    { name: '성녀 잔 다르크 발키리', weapon: 'HALO_TWIN_BLADES', helm: 'VALKYRIE_WING_TIARA', shield: 'SERAPHIM_WINGS' },
        ROOK:     { name: '시타델 바스티온 거병', weapon: 'SIEGE_WARHAMMER', helm: 'CASTLE_CROWN_HELM', shield: 'BASTION_WALL_SHIELD' },
        BISHOP:   { name: '대주교 하이 인퀴지터', weapon: 'RELIQUARY_CROZIER', helm: 'PAPAL_MITRE', shield: 'HOLY_SCRIPTURE' },
        KNIGHT:   { name: '중갑 데미랜서 기사', weapon: 'DEMI_LANCE', helm: 'PLUMED_GREATHELM', mount: 'PLATE_DESTRIER' },
        PAWN:     { name: '템플러 성전 보병', weapon: 'ARMING_SPEAR', helm: 'SALLET_HELM', shield: 'CRUSADER_KITE_SHIELD' },
        CHARIOT:  { name: '그랜드 랜서 챔피언', weapon: 'JOUSTING_LANCE', helm: 'WINGED_GREATHELM', mount: 'BARDED_DESTRIER' },
        CANNON:   { name: '왕립 공성 트레뷰셋', weapon: 'TREBUCHET', helm: 'MAIL_COIF', artillery: 'TREBUCHET_RIG' },
        HORSE:    { name: '템플러 나이트 에란트', weapon: 'BROADSWORD', helm: 'SUGARLOAF_HELM', mount: 'CRUSADER_STEED' },
        ELEPHANT: { name: '크루세이더 공성 베히모스', weapon: 'POLEAXE_TOWER', helm: 'ARMET', mount: 'GOTHIC_ELEPHANT' },
        GUARD:    { name: '팔라딘 로열 가드', weapon: 'HALBERD', helm: 'PLUMED_ARMET', shield: 'TOWER_PAVISE' },
        SOLDIER:  { name: '맨앳암즈 중보병', weapon: 'SPEAR_SWORD', helm: 'KETTLE_HAT', shield: 'HEATER_SHIELD' }
      }
    },

    BYZANTINE: {
      id: 'BYZANTINE',
      name: '비잔틴 제국군 (The Golden Empire)',
      shortName: '비잔틴 제국군',
      commanderTitle: '바실레우스 황제',
      subtitle: '황금 비늘갑주 카타프락토이와 그리스의 불로 무장한 동로마 제국 도트 군단',
      emblem: 'DOUBLE_EAGLE',
      palette: {
        outline: '#070a14',
        deepShadow: '#2e1065',
        bounceLight: '#701a75',
        specHighlight: '#ffffff',
        rimLight: '#f0abfc',
        armorDark: '#92400e',
        armorPrimary: '#d97706',
        armorMid: '#f59e0b',
        armorLight: '#fbbf24',
        armorSecondary: '#6b21a8',
        armorSecDark: '#4c1d95',
        armorSecLight: '#a855f7',
        clothDark: '#581c87',
        cloth: '#9333ea',
        clothLight: '#c084fc',
        metal: '#fcd34d',
        metalLight: '#fef9c3',
        metalDark: '#78350f',
        gold: '#fde047',
        goldLight: '#ffffff',
        goldDark: '#b45309',
        goldSpec: '#ffffff',
        wood: '#451a03',
        woodLight: '#78350f',
        woodDark: '#270e02',
        skin: '#fde68a',
        skinLight: '#fef9c3',
        skinShade: '#b45309',
        skinShadow: '#78350f',
        fxPrimary: '#c084fc',
        fxSecondary: '#10b981'
      },
      units: {
        KING:     { name: '바실레우스 황제', weapon: 'IMPERIAL_SPATHA', helm: 'STEMMATOGYRION', shield: 'EAGLE_AEGIS' },
        QUEEN:    { name: '테오도라 아우구스타 황후', weapon: 'IMPERIAL_SCEPTER_BLADES', helm: 'AUGUSTA_DIADEM', shield: 'PURPLE_AURA_ORBS' },
        ROOK:     { name: '테오도시우스 성벽 거병', weapon: 'IMPERIAL_BATTERING_MACE', helm: 'TURRET_CREST_HELM', shield: 'THEODOSIAN_TOWER_SHIELD' },
        BISHOP:   { name: '콘스탄티노플 총대주교', weapon: 'GREEK_FIRE_CROZIER', helm: 'PATRIARCH_MITRE', shield: 'ORTHODOX_CHALICE' },
        KNIGHT:   { name: '클리바나리 철갑기병', weapon: 'CATAPHRACT_KONTOS', helm: 'GILDED_VISOR_HELM', mount: 'LORICA_WARHORSE' },
        PAWN:     { name: '바랑기안 중장보병', weapon: 'VARANGIAN_SPEAR_AXE', helm: 'SPECTACLE_HELM', shield: 'IMPERIAL_SKOUTON' },
        CHARIOT:  { name: '클리바나리 카타프락토이', weapon: 'KONTOS_LANCE', helm: 'GOLDEN_FACEMASK', mount: 'SCALE_CATAPHRACT' },
        CANNON:   { name: '그리스의 불 사이펀 포대', weapon: 'GREEK_FIRE_SIPHON', helm: 'BRONZE_MASK', artillery: 'SIPHON_CART' },
        HORSE:    { name: '타그마타 프로노이아 기병', weapon: 'SPATHION', helm: 'CONICAL_PTERUGES', mount: 'IMPERIAL_COURSER' },
        ELEPHANT: { name: '임페리얼 워 엘리펀트', weapon: 'IMPERIAL_SPEAR', helm: 'CRESTED_HELM', mount: 'BYZANTINE_ELEPHANT' },
        GUARD:    { name: '바랑기안 가드', weapon: 'DANE_AXE', helm: 'NORMAN_SPECTACLE', shield: 'ROUND_RUNE_SHIELD' },
        SOLDIER:  { name: '스쿠타토이 중보병', weapon: 'KONTARION', helm: 'BYZANTINE_KETTLE', shield: 'OVAL_SKOUTON' }
      }
    },

    MAMLUK: {
      id: 'MAMLUK',
      name: '맘루크 술탄국 (The Mamluk Sultanate)',
      shortName: '맘루크 술탄국',
      commanderTitle: '술탄 살라딘 대왕',
      subtitle: '다마스쿠스 강철 시미터와 만자니크 화염포를 다루는 사막의 도트 정예군',
      emblem: 'CRESCENT',
      palette: {
        outline: '#070a14',
        deepShadow: '#042f2e',
        bounceLight: '#78350f',
        specHighlight: '#ffffff',
        rimLight: '#5eead4',
        armorDark: '#1e293b',
        armorPrimary: '#334155',
        armorMid: '#475569',
        armorLight: '#94a3b8',
        armorSecondary: '#0d9488',
        armorSecDark: '#115e59',
        armorSecLight: '#2dd4bf',
        clothDark: '#92400e',
        cloth: '#d97706',
        clothLight: '#fbbf24',
        metal: '#e2e8f0',
        metalLight: '#ffffff',
        metalDark: '#1e293b',
        gold: '#fbbf24',
        goldLight: '#fef08a',
        goldDark: '#92400e',
        goldSpec: '#ffffff',
        wood: '#713f12',
        woodLight: '#a16207',
        woodDark: '#422006',
        skin: '#d97706',
        skinLight: '#fbbf24',
        skinShade: '#92400e',
        skinShadow: '#451a03',
        fxPrimary: '#2dd4bf',
        fxSecondary: '#f59e0b'
      },
      units: {
        KING:     { name: '술탄 살라딘 대왕', weapon: 'ROYAL_SHAMSHIR', helm: 'SULTAN_TURBAN_HELM', shield: 'MIRROR_DHAL' },
        QUEEN:    { name: '샤자르 알두르 여술탄', weapon: 'DJINN_TWIN_SHAMSHIRS', helm: 'SULTANA_CROWN_VEIL', shield: 'ASTRAL_DJINN_ORBS' },
        ROOK:     { name: '알카히라 성채 수호거병', weapon: 'OBELISK_CRUSHER_MACE', helm: 'MINARET_TURBAN_HELM', shield: 'CITADEL_BRASS_SHIELD' },
        BISHOP:   { name: '사막 화염 대주술사', weapon: 'SOLAR_FLAME_STAFF', helm: 'GRAND_MUFTI_TURBAN', shield: 'BLAZING_INCENSE' },
        KNIGHT:   { name: '파리스 왕실 중장기병', weapon: 'ROYAL_FARIS_LANCE', helm: 'SPIKED_TURBAN_MASK', mount: 'GILDED_ARABIAN_STEED' },
        PAWN:     { name: '굴람 방패 산병', weapon: 'GHULAM_SPEAR', helm: 'STEEL_KEFFIYEH', shield: 'BRASS_DHAL_SHIELD' },
        CHARIOT:  { name: '맘루크 카스 중장돌격병', weapon: 'DOUBLE_LANCE', helm: 'GILDED_TURBAN_MASK', mount: 'ARABIAN_BARDED' },
        CANNON:   { name: '만자니크 & 나프트 화염포', weapon: 'MANJANIQ', helm: 'KEFFIYEH_HELM', artillery: 'MANJANIQ_RIG' },
        HORSE:    { name: '파리스 사막 기병', weapon: 'SCIMITAR', helm: 'TURBAN_CONE', mount: 'ARABIAN_STEED' },
        ELEPHANT: { name: '사라센 전투 코끼리', weapon: 'TUSK_SWORDS', helm: 'CRESCENT_SPIKE', mount: 'SARACEN_ELEPHANT' },
        GUARD:    { name: '할카 쌍곡도 근위대', weapon: 'DUAL_SCIMITARS', helm: 'FACE_VEIL_HELM', shield: 'SMALL_BUCKLER' },
        SOLDIER:  { name: '가지 방패 창보병', weapon: 'HARBA_SPEAR', helm: 'DESERT_TURBAN', shield: 'ROUND_DHAL' }
      }
    }
  };

  // ============================================================================
  // 2. BITMAP PIXEL HANJA & CHESS GLYPHS (11x11 HIGH-DENSITY PIXEL GRIDS)
  // ============================================================================

  const PIXEL_HANJA_FONT = {
    // --- JANGGI HANJA ---
    '楚': [
      '..1..1..1..',
      '.11111.111.',
      '..1.1..1.1.',
      '.11.1..1.1.',
      '....1111111',
      '.111111111.',
      '...1..1..1.',
      '..1.1111...',
      '.1..1..1...',
      '1..1...111.',
      '..111111111'
    ],
    '漢': [
      '1...111111.',
      '.1...1..1..',
      '..1.111111.',
      '1...1.11.1.',
      '.1..111111.',
      '.......1...',
      '.1.1111111.',
      '.1....1....',
      '1...111111.',
      '1....1..1..',
      '...11....11'
    ],
    '宮': [
      '.....1.....',
      '.111111111.',
      '.1.......1.',
      '..1111111..',
      '..1.....1..',
      '..1111111..',
      '.....1.....',
      '.111111111.',
      '.1.......1.',
      '.1.......1.',
      '.111111111.'
    ],
    '車': [
      '.....1.....',
      '.111111111.',
      '.....1.....',
      '..1111111..',
      '..1..1..1..',
      '..1111111..',
      '..1..1..1..',
      '..1111111..',
      '.....1.....',
      '11111111111',
      '.....1.....'
    ],
    '包': [
      '...1.......',
      '..11111111.',
      '.1.......1.',
      '1..11111.1.',
      '...1...1.1.',
      '...11111.1.',
      '...1.....1.',
      '...1...11..',
      '...1.......',
      '...1......1',
      '....111111.'
    ],
    '馬': [
      '..1111111..',
      '..1..1.....',
      '..1111111..',
      '..1..1.....',
      '..1111111..',
      '..1..1.....',
      '..111111111',
      '.........1.',
      '.1.1.1.1.1.',
      '1.1.1.1..1.',
      '.......111.'
    ],
    '象': [
      '....111....',
      '..11...11..',
      '.111111111.',
      '.1...1...1.',
      '.111111111.',
      '....11.....',
      '..11.1111..',
      '.1..11..11.',
      '...1.1.1...',
      '..1..1..11.',
      '.1..11.....'
    ],
    '士': [
      '.....1.....',
      '.....1.....',
      '.....1.....',
      '11111111111',
      '.....1.....',
      '.....1.....',
      '.....1.....',
      '.....1.....',
      '.....1.....',
      '.111111111.',
      '...........'
    ],
    '卒': [
      '.....1.....',
      '.111111111.',
      '...1...1...',
      '..11...11..',
      '.1..1.1..1.',
      '.....1.....',
      '.....1.....',
      '11111111111',
      '.....1.....',
      '.....1.....',
      '.....1.....'
    ],
    '兵': [
      '......111..',
      '..1111.....',
      '..1........',
      '..1111111..',
      '..1....1...',
      '..1....1...',
      '11111111111',
      '....1..1...',
      '...1....1..',
      '..1......1.',
      '.1........1'
    ],

    // --- CHESS CROWN / TURRET / MITRE / KNIGHT / PAWN SYMBOLS ---
    '♔': [
      '.....1.....',
      '...11111...',
      '.....1.....',
      '.1..111..1.',
      '111.111.111',
      '11111111111',
      '.11.111.11.',
      '.111111111.',
      '..1111111..',
      '.111111111.',
      '11111111111'
    ],
    '♕': [
      '1..1.1.1..1',
      '1..1.1.1..1',
      '.1.1.1.1.1.',
      '.111111111.',
      '.11.111.11.',
      '..1111111..',
      '..1.1.1.1..',
      '..1111111..',
      '.111111111.',
      '..1111111..',
      '11111111111'
    ],
    '♖': [
      '.11.111.11.',
      '.11.111.11.',
      '.111111111.',
      '..1111111..',
      '...11111...',
      '...11.11...',
      '...11.11...',
      '..1111111..',
      '.111111111.',
      '.111111111.',
      '11111111111'
    ],
    '♗': [
      '.....1.....',
      '....111....',
      '...11111...',
      '..111.111..',
      '.111...111.',
      '.1111.1111.',
      '..1111111..',
      '...11111...',
      '..1111111..',
      '.111111111.',
      '11111111111'
    ],
    '♘': [
      '...11..11..',
      '..1111111..',
      '.111.11111.',
      '1111111111.',
      '1111..1111.',
      '...1111111.',
      '....111111.',
      '...111111..',
      '..1111111..',
      '.111111111.',
      '11111111111'
    ],
    '♙': [
      '....111....',
      '...11111...',
      '...11111...',
      '....111....',
      '..1111111..',
      '...11111...',
      '...11111...',
      '..1111111..',
      '.111111111.',
      '.111111111.',
      '11111111111'
    ],

    // --- CHESS KANJI SYMBOLS ---
    '后': [
      '..11111111.',
      '..1........',
      '..1........',
      '..111111111',
      '..1........',
      '..1.111111.',
      '..1.1....1.',
      '.1..1....1.',
      '.1..111111.',
      '1...1....1.',
      '....1....1.'
    ],
    '城': [
      '.1...11111.',
      '.1...1..1.1',
      '111..11111.',
      '.1...1..1..',
      '.1...11.1.1',
      '.1..1.1.11.',
      '.11.1.1..1.',
      '11..11...1.',
      '....1...11.',
      '...1...1..1',
      '..1...1...1'
    ],
    '主教': [
      '..1....1.1.',
      '11111.11111',
      '..1....1.1.',
      '.111..11111',
      '..1...1.1.1',
      '11111..111.',
      '.......1.1.',
      '.1111..1.1.',
      '..1...1...1',
      '..1..1....1',
      '111111.....'
    ],
    '騎': [
      '1111..11111',
      '1..1....1..',
      '1111..11111',
      '1..1...1.1.',
      '11111.11111',
      '...1..1...1',
      '1.1.1.111.1',
      '1.1.1.1.1.1',
      '...1..111.1',
      '......1...1',
      '..11.....11'
    ],
    '歩': [
      '.....1.....',
      '.....1.111.',
      '..1..1.....',
      '..1..1.....',
      '11111111111',
      '.....1.....',
      '..1..1..1..',
      '.1...1...1.',
      '....1..1...',
      '...1..1....',
      '.11.11.....'
    ]
  };

  // ============================================================================
  // 3. NORMALIZATION & 7-STEP HUE-SHIFTED RAMP HELPERS
  // ============================================================================

  function normalizePieceType(type) {
    if (!type) return 'SOLDIER';
    const raw = String(type).trim();
    const key = raw.toUpperCase();
    return PIECE_ALIASES[key] || PIECE_ALIASES[raw] || 'SOLDIER';
  }

  const normalizeType = normalizePieceType;

  function normalizeSide(side) {
    if (!side) return 'CHU';
    const raw = String(side).trim();
    const key = raw.toUpperCase();
    return SIDE_ALIASES[key] || SIDE_ALIASES[raw] || 'CHU';
  }

  function normalizeFaction(faction, side) {
    if (faction) {
      const key = String(faction).trim().toUpperCase();
      if (FACTION_SKINS[key]) return key;
      if (key.includes('GORYEO') || key.includes('JOSEON') || key.includes('KOREA') || key.includes('고려') || key.includes('천군')) return 'GORYEO';
      if (key.includes('TEMPLAR') || key.includes('CRUSADE') || key.includes('EUROPE') || key.includes('성전') || key.includes('기사')) return 'TEMPLAR';
      if (key.includes('BYZANT') || key.includes('ROME') || key.includes('EMPIRE') || key.includes('비잔틴')) return 'BYZANTINE';
      if (key.includes('MAMLUK') || key.includes('SARACEN') || key.includes('ARAB') || key.includes('맘루크')) return 'MAMLUK';
    }
    return normalizeSide(side) === 'CHU' ? 'GORYEO' : 'TEMPLAR';
  }

  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }

  /**
   * Builds a 7-Step Hue-Shifted Color Ramp for NMM armor, gold, cloth, or steel:
   * [0: deepShadow, 1: darkTone, 2: midShadow, 3: baseTone, 4: midHighlight, 5: brightHighlight, 6: specHighlight]
   */
  function buildHueShiftedRamp(skin, team, material) {
    const p = skin.palette;
    if (material === 'GOLD') {
      return [
        p.deepShadow || '#0f172a',
        p.woodDark || '#451a03',
        p.goldDark,
        p.gold,
        p.goldLight,
        p.goldSpec || '#fef9c3',
        '#ffffff'
      ];
    }
    if (material === 'SECONDARY') {
      return [
        p.deepShadow || '#0f172a',
        p.armorSecDark,
        p.armorSecDark,
        p.armorSecondary,
        p.armorSecLight || p.armorLight,
        p.rimLight || p.metalLight,
        p.specHighlight || '#ffffff'
      ];
    }
    if (material === 'CLOTH' || material === 'CAPE') {
      return [
        p.deepShadow || '#090c15',
        team ? team.capeDeep : (p.clothDark || '#450a0a'),
        team ? team.capeShade : (p.clothDark || '#7f1d1d'),
        team ? team.capeMid : p.cloth,
        team ? team.capeTint : p.cloth,
        team ? team.capeHighlight : (p.clothLight || '#f87171'),
        team ? team.neonBright : '#ffffff'
      ];
    }
    if (material === 'STEEL') {
      return [
        p.deepShadow || '#0f172a',
        p.metalDark,
        p.armorPrimary,
        p.metal,
        p.metalLight,
        '#ffffff',
        '#ffffff'
      ];
    }
    // Default 'ARMOR' 7-step NMM ramp
    return [
      p.deepShadow || '#0f172a',
      p.armorDark || p.metalDark,
      p.armorPrimary,
      p.armorMid || p.armorPrimary,
      p.armorLight,
      p.metalLight,
      p.specHighlight || '#ffffff'
    ];
  }

  // ============================================================================
  // 4. HD PIXEL GRID SURFACE (NMM SHADING, DRAPERY FOLDS & SEL-OUT AA)
  // ============================================================================

  const _spriteCache = new Map();
  const MAX_CACHE_ENTRIES = 650;

  /**
   * High-Density Virtual Pixel Grid Surface (76x76 for Units, 48x48 for Portraits)
   * with NMM Specular Clustering, 3-Fold Cloak Shading, Selective Outlining (Sel-out),
   * and Internal Corner Subpixel Anti-Aliasing.
   */
  class PixelGridSurface {
    constructor(width, height) {
      this.w = width | 0;
      this.h = height | 0;
      this.grid = new Array(this.w * this.h).fill(null);
    }

    setPixel(x, y, color) {
      const ix = Math.round(x);
      const iy = Math.round(y);
      if (ix < 0 || ix >= this.w || iy < 0 || iy >= this.h || !color) return;
      this.grid[iy * this.w + ix] = color;
    }

    getPixel(x, y) {
      const ix = Math.round(x);
      const iy = Math.round(y);
      if (ix < 0 || ix >= this.w || iy < 0 || iy >= this.h) return null;
      return this.grid[iy * this.w + ix];
    }

    fillRect(x, y, w, h, color) {
      if (!color) return;
      const x0 = Math.round(x);
      const y0 = Math.round(y);
      const x1 = x0 + Math.round(w);
      const y1 = y0 + Math.round(h);
      for (let py = y0; py < y1; py++) {
        for (let px = x0; px < x1; px++) {
          this.setPixel(px, py, color);
        }
      }
    }

    fillDitherRect(x, y, w, h, colorA, colorB) {
      const x0 = Math.round(x);
      const y0 = Math.round(y);
      const x1 = x0 + Math.round(w);
      const y1 = y0 + Math.round(h);
      for (let py = y0; py < y1; py++) {
        for (let px = x0; px < x1; px++) {
          this.setPixel(px, py, ((px + py) & 1) === 0 ? colorA : colorB);
        }
      }
    }

    /**
     * Paints a Non-Metallic Metal (NMM) armor plate using a 7-step Hue-Shifted Color Ramp,
     * complete with top-left specular hotspot, diagonal metallic sheen, dark crevice, and bottom bounce light.
     */
    fillNMMPlate(x, y, w, h, ramp, bounceColor) {
      const x0 = Math.round(x);
      const y0 = Math.round(y);
      const iw = Math.max(1, Math.round(w));
      const ih = Math.max(1, Math.round(h));
      for (let dy = 0; dy < ih; dy++) {
        const ny = dy / Math.max(1, ih - 1);
        for (let dx = 0; dx < iw; dx++) {
          const nx = dx / Math.max(1, iw - 1);
          // Cylindrical + diagonal NMM light curve (light from top-right/front)
          let col = ramp[3];
          if (dy === 0) {
            col = dx > iw * 0.25 && dx < iw * 0.8 ? ramp[5] : ramp[4];
          } else if (dy === ih - 1 && bounceColor) {
            col = ((dx + dy) & 1) === 0 ? bounceColor : ramp[1];
          } else if (nx + (1 - ny) * 0.65 > 1.18) {
            col = ramp[5];
          } else if (nx + (1 - ny) * 0.5 > 0.82) {
            col = ramp[4];
          } else if (nx < 0.22 || ny > 0.82) {
            col = ramp[1];
          } else if (nx < 0.38) {
            col = ramp[2];
          }
          // Diagonal NMM Specular Glint cluster
          if (dy >= 1 && dy <= 2 && dx === Math.max(1, Math.floor(iw * 0.65))) {
            col = ramp[6];
          }
          this.setPixel(x0 + dx, y0 + dy, col);
        }
      }
    }

    /**
     * Paints a curved 3D NMM Dome (for Helmets, Pauldrons, Breastplates, Orbs)
     */
    fillNMMDome(cx, cy, rx, ry, ramp, halfTopOnly) {
      const icx = Math.round(cx);
      const icy = Math.round(cy);
      const irx = Math.max(1, Math.round(rx));
      const iry = Math.max(1, Math.round(ry));
      const maxDy = halfTopOnly ? 0 : iry;
      for (let dy = -iry; dy <= maxDy; dy++) {
        for (let dx = -irx; dx <= irx; dx++) {
          const ndx = dx / irx;
          const ndy = dy / iry;
          const dist2 = ndx * ndx + ndy * ndy;
          if (dist2 <= 1.05) {
            // Light source at (0.32, -0.45)
            const lx = ndx - 0.32;
            const ly = ndy + 0.45;
            const lDist = Math.sqrt(lx * lx + ly * ly);
            let col = ramp[3];
            if (lDist < 0.28) col = ramp[6];
            else if (lDist < 0.52) col = ramp[5];
            else if (lDist < 0.78) col = ramp[4];
            else if (lDist < 1.05) col = ramp[3];
            else if (lDist < 1.32) col = ramp[2];
            else col = ramp[1];
            this.setPixel(icx + dx, icy + dy, col);
          }
        }
      }
    }

    /**
     * Paints a 3-Fold Flowing Cloak / Robe with deep creases, highlight ridges, and gold trim.
     */
    fillFoldedCloak(x, y, w, h, wave, ramp, trimColor) {
      const x0 = Math.round(x);
      const y0 = Math.round(y);
      const iw = Math.max(2, Math.round(w));
      const ih = Math.max(2, Math.round(h));
      for (let dy = 0; dy < ih; dy++) {
        const flare = Math.floor((dy / ih) * (2 + wave));
        const rowX = x0 - flare;
        const rowW = iw + flare;
        for (let dx = 0; dx < rowW; dx++) {
          // Create 3 distinct vertical/diagonal cloth folds
          const foldPhase = (dx + Math.floor(dy * 0.35) + wave) % 5;
          let col = ramp[3];
          if (foldPhase === 0) col = ramp[1]; // Deep fold crease
          else if (foldPhase === 1) col = ramp[2]; // Shadow side of fold
          else if (foldPhase === 2) col = ramp[4]; // Lit cloth body
          else if (foldPhase === 3) col = ramp[5]; // Highlight ridge of fold
          else col = ramp[3];

          if (dy === ih - 1 && trimColor) {
            col = trimColor;
          } else if (dy === ih - 2 && trimColor && (dx & 1) === 0) {
            col = trimColor;
          }
          this.setPixel(rowX + dx, y0 + dy, col);
        }
      }
    }

    drawLine(x0, y0, x1, y1, color, thickness) {
      let ix0 = Math.round(x0);
      let iy0 = Math.round(y0);
      const ix1 = Math.round(x1);
      const iy1 = Math.round(y1);
      const dx = Math.abs(ix1 - ix0);
      const dy = Math.abs(iy1 - iy0);
      const sx = ix0 < ix1 ? 1 : -1;
      const sy = iy0 < iy1 ? 1 : -1;
      let err = dx - dy;
      const th = thickness || 1;

      while (true) {
        if (th <= 1) {
          this.setPixel(ix0, iy0, color);
        } else {
          this.fillRect(ix0 - (th >> 1), iy0 - (th >> 1), th, th, color);
        }
        if (ix0 === ix1 && iy0 === iy1) break;
        const e2 = 2 * err;
        if (e2 > -dy) { err -= dy; ix0 += sx; }
        if (e2 < dx)  { err += dx; iy0 += sy; }
      }
    }

    /**
     * Draws a 3-tone NMM Gradient Weapon Blade (Core Dark Fuller + Mid Steel + Pure White Specular Edge)
     */
    drawNMMBlade(x0, y0, x1, y1, edgeColor, midColor, shadowColor) {
      this.drawLine(x0, y0 + 1, x1, y1 + 1, shadowColor || '#334155', 1);
      this.drawLine(x0, y0, x1, y1, midColor || '#cbd5e1', 2);
      this.drawLine(x0, y0 - 1, x1, y1 - 1, edgeColor || '#ffffff', 1);
    }

    fillCircle(cx, cy, r, color, ditherColor) {
      const icx = Math.round(cx);
      const icy = Math.round(cy);
      const ir = Math.round(r);
      const r2 = ir * ir;
      for (let dy = -ir; dy <= ir; dy++) {
        for (let dx = -ir; dx <= ir; dx++) {
          if (dx * dx + dy * dy <= r2) {
            const c = (ditherColor && ((icx + dx + icy + dy) & 1) === 1) ? ditherColor : color;
            this.setPixel(icx + dx, icy + dy, c);
          }
        }
      }
    }

    fillOctagon(cx, cy, rx, ry, colorA, colorB) {
      const icx = Math.round(cx);
      const icy = Math.round(cy);
      const irx = Math.max(1, Math.round(rx));
      const iry = Math.max(1, Math.round(ry));
      for (let dy = -iry; dy <= iry; dy++) {
        for (let dx = -irx; dx <= irx; dx++) {
          const nx = Math.abs(dx) / irx;
          const ny = Math.abs(dy) / iry;
          if (nx <= 1 && ny <= 1 && (nx + ny) <= 1.38) {
            const c = (colorB && ((icx + dx + icy + dy) & 1) === 1) ? colorB : colorA;
            this.setPixel(icx + dx, icy + dy, c);
          }
        }
      }
    }

    drawBitmapPattern(x, y, rows, paletteMap) {
      const x0 = Math.round(x);
      const y0 = Math.round(y);
      for (let r = 0; r < rows.length; r++) {
        const row = rows[r];
        for (let c = 0; c < row.length; c++) {
          const ch = row[c];
          if (ch !== '.' && ch !== ' ' && paletteMap[ch]) {
            this.setPixel(x0 + c, y0 + r, paletteMap[ch]);
          }
        }
      }
    }

    /**
     * Selective Outlining (Sel-out) & Subpixel Anti-Aliasing:
     * - Top/Light-facing edges receive a dark faction metallic/gold tone (`topOutline`).
     * - Mid edges receive `deepShadow` (`#0f172a`).
     * - Lower/Shadow edges receive deep obsidian (`#070a14`).
     * - Internal concave L-corners receive subtle subpixel anti-aliasing pixels.
     */
    applyPixelOutline(outlineColor, outerGlowColor, selOutConfig) {
      const copy = this.grid.slice();
      const dirs = [[-1, 0], [1, 0], [0, -1], [0, 1]];
      const bottomOutline = outlineColor || '#070a14';
      const topOutline = (selOutConfig && selOutConfig.topOutline) || '#1e293b';
      const midOutline = (selOutConfig && selOutConfig.midOutline) || '#0f172a';
      const aaColor = (selOutConfig && selOutConfig.aaColor) || '#334155';

      for (let y = 1; y < this.h - 1; y++) {
        for (let x = 1; x < this.w - 1; x++) {
          const idx = y * this.w + x;
          if (!copy[idx]) {
            let hasBelow = false;
            let hasAbove = false;
            let neighborCount = 0;
            for (let d = 0; d < 4; d++) {
              const nx = x + dirs[d][0];
              const ny = y + dirs[d][1];
              if (copy[ny * this.w + nx]) {
                neighborCount++;
                if (dirs[d][1] === 1) hasBelow = true;
                if (dirs[d][1] === -1) hasAbove = true;
              }
            }
            if (neighborCount > 0) {
              if (y < this.h * 0.36 && hasBelow && !hasAbove) {
                this.grid[idx] = topOutline;
              } else if (y < this.h * 0.62 && !hasAbove) {
                this.grid[idx] = midOutline;
              } else {
                this.grid[idx] = bottomOutline;
              }
            }
          }
        }
      }

      // Internal Corner Subpixel Anti-Aliasing (softens jagged staircase interior corners)
      const outlinedCopy = this.grid.slice();
      for (let y = 2; y < this.h - 2; y++) {
        for (let x = 2; x < this.w - 2; x++) {
          const idx = y * this.w + x;
          if (!outlinedCopy[idx]) {
            const nUp = outlinedCopy[(y - 1) * this.w + x];
            const nDown = outlinedCopy[(y + 1) * this.w + x];
            const nLeft = outlinedCopy[y * this.w + (x - 1)];
            const nRight = outlinedCopy[y * this.w + (x + 1)];
            const isOutline = (c) => c === bottomOutline || c === topOutline || c === midOutline;
            if ((isOutline(nUp) && isOutline(nLeft) && copy[(y - 1) * this.w + (x - 1)]) ||
                (isOutline(nUp) && isOutline(nRight) && copy[(y - 1) * this.w + (x + 1)])) {
              this.grid[idx] = aaColor;
            } else if (isOutline(nDown) && (isOutline(nLeft) || isOutline(nRight)) && y > this.h * 0.5) {
              this.grid[idx] = bottomOutline;
            }
          }
        }
      }

      if (outerGlowColor) {
        const copy2 = this.grid.slice();
        for (let y = 1; y < this.h - 1; y++) {
          for (let x = 1; x < this.w - 1; x++) {
            const idx = y * this.w + x;
            if (!copy2[idx]) {
              for (let d = 0; d < 4; d++) {
                const nx = x + dirs[d][0];
                const ny = y + dirs[d][1];
                const nc = copy2[ny * this.w + nx];
                if (nc === bottomOutline || nc === topOutline || nc === midOutline) {
                  this.grid[idx] = outerGlowColor;
                  break;
                }
              }
            }
          }
        }
      }
    }

    toCanvas() {
      if (typeof document === 'undefined') return null;
      const cvs = document.createElement('canvas');
      cvs.width = this.w;
      cvs.height = this.h;
      const c = cvs.getContext('2d');
      c.imageSmoothingEnabled = false;
      for (let y = 0; y < this.h; y++) {
        let x = 0;
        while (x < this.w) {
          const col = this.grid[y * this.w + x];
          if (!col) {
            x++;
            continue;
          }
          let run = 1;
          while (x + run < this.w && this.grid[y * this.w + x + run] === col) {
            run++;
          }
          c.fillStyle = col;
          c.fillRect(x, y, run, 1);
          x += run;
        }
      }
      return cvs;
    }

    renderDirect(ctx, destX, destY, pixelSize, flipX, tintColor) {
      const ps = Math.max(1, Math.round(pixelSize));
      const ox = Math.round(destX - (this.w * ps) / 2);
      const oy = Math.round(destY - (this.h * ps) / 2);
      for (let y = 0; y < this.h; y++) {
        for (let x = 0; x < this.w; x++) {
          const col = this.grid[y * this.w + x];
          if (!col) continue;
          const rx = flipX ? (this.w - 1 - x) : x;
          ctx.fillStyle = tintColor || col;
          ctx.fillRect(ox + rx * ps, oy + y * ps, ps, ps);
        }
      }
    }
  }

  // ============================================================================
  // 5. PIXEL ART FACTION EMBLEM & OCTAGONAL JANGGI / CHESS PEDESTAL
  // ============================================================================

  const PIXEL_EMBLEMS = {
    CROSS: [
      '..11111..',
      '...111...',
      '11.111.11',
      '111111111',
      '111111111',
      '11.111.11',
      '...111...',
      '..11111..'
    ],
    SAMJOKOH: [
      '.1..1..1.',
      '1.11111.1',
      '.11.1.11.',
      '11.111.11',
      '11.111.11',
      '.11.1.11.',
      '..11111..',
      '...1.1...'
    ],
    DOUBLE_EAGLE: [
      '.11...11.',
      '1..1.1..1',
      '.1.111.1.',
      '111111111',
      '.1111111.',
      '..11111..',
      '.1.111.1.',
      '1...1...1'
    ],
    CRESCENT: [
      '...1111..',
      '.1111....',
      '111..11..',
      '11..1111.',
      '11...11..',
      '111......',
      '.1111....',
      '...1111..'
    ]
  };

  function drawFactionEmblem(ctx, x, y, size, emblemType, color, alpha) {
    const pattern = PIXEL_EMBLEMS[emblemType] || PIXEL_EMBLEMS.CROSS;
    const rows = pattern.length;
    const cols = pattern[0].length;
    const ps = Math.max(2, Math.round(size / cols));
    const startX = Math.round(x - (cols * ps) / 2);
    const startY = Math.round(y - (rows * ps) / 2);

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.globalAlpha = alpha !== undefined ? alpha : 0.35;
    ctx.fillStyle = color || '#f59e0b';
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (pattern[r][c] === '1') {
          ctx.fillRect(startX + c * ps, startY + r * ps, ps, ps);
        }
      }
    }
    ctx.restore();
  }

  /**
   * Renders a 100% Pixel-Art Octagonal Janggi / Chess Pedestal with NMM Gold Rim,
   * Bayer dithering, and an 11x11 Bitmap Hanja or Chess Crown/Symbol Plaque.
   */
  function drawBoardPedestal(ctx, x, y, radius, sideInput, typeInput, factionInput, options) {
    const opts = options || {};
    const side = normalizeSide(sideInput);
    const type = normalizePieceType(typeInput);
    const factionKey = normalizeFaction(factionInput, side);

    const pMeta = PIECE_META[type];
    const team = TEAM_THEMES[side];
    const skin = FACTION_SKINS[factionKey];

    let hanjaChar = (pMeta.hanja && pMeta.hanja[side]) || pMeta.hanja.DEFAULT;
    if (opts.glyph && PIXEL_HANJA_FONT[opts.glyph]) {
      hanjaChar = opts.glyph;
    } else if ((opts.isChess || opts.gameMode === 'CHESS' || String(typeInput).trim() === '♔') && pMeta.hanja.CHESS) {
      hanjaChar = pMeta.hanja.CHESS;
    }

    const rx = radius * pMeta.pedestalScale;
    const ps = Math.max(2, Math.round(rx / 14));
    const cacheKey = `PED3_${side}_${type}_${hanjaChar}_${factionKey}_${opts.isSelected ? 1 : 0}_${opts.isCheck ? 1 : 0}_${opts.unitStanding !== false ? 1 : 0}`;

    let pedCanvas = _spriteCache.get(cacheKey);
    if (!pedCanvas) {
      const gw = 38;
      const gh = 30;
      const surf = new PixelGridSurface(gw, gh);
      const cx = 19;
      const cy = 12;

      // 1. Pixelated Drop Shadow
      surf.fillOctagon(cx, cy + 5, 16, 9, 'rgba(0,0,0,0.60)', 'rgba(0,0,0,0.35)');

      // 2. Selection / Check Pixel Aura Ring
      if (opts.isSelected || opts.isCheck) {
        const ringCol = opts.isCheck ? '#ef4444' : '#facc15';
        surf.fillOctagon(cx, cy + 2, 17, 11, ringCol, '#ffffff');
      }

      // 3. 3D Extruded Octagonal Pedestal Base Wall with NMM Gold Corner Ribs
      for (let dy = 4; dy >= 1; dy--) {
        surf.fillOctagon(cx, cy + dy, 15, 8, team.pedestalSide, skin.palette.deepShadow);
      }
      surf.fillRect(cx - 15, cy, 1, 4, skin.palette.goldDark);
      surf.fillRect(cx + 15, cy, 1, 4, skin.palette.goldDark);
      surf.fillRect(cx - 7, cy + 8, 2, 4, skin.palette.gold);
      surf.fillRect(cx + 6, cy + 8, 2, 4, skin.palette.gold);
      surf.setPixel(cx - 6, cy + 8, skin.palette.goldLight);
      surf.setPixel(cx + 6, cy + 8, skin.palette.goldLight);

      // 4. Outer NMM Gold Rim & Team Neon Ring
      surf.fillOctagon(cx, cy, 15, 8, skin.palette.gold, skin.palette.goldDark);
      surf.fillRect(cx - 6, cy - 8, 12, 1, skin.palette.goldLight);
      surf.fillOctagon(cx, cy, 14, 7, team.neon, team.accentDark);
      surf.fillOctagon(cx, cy, 12, 6, team.pedestalTop, team.pedestalDither);

      // 5. Bitmap Hanja / Chess Emblem Plaque
      const glyph = PIXEL_HANJA_FONT[hanjaChar] || PIXEL_HANJA_FONT['卒'];
      const gy = opts.unitStanding !== false ? cy + 1 : cy - 5;

      if (opts.unitStanding !== false) {
        surf.fillRect(cx - 7, gy - 1, 15, 13, '#070a14');
        surf.fillRect(cx - 6, gy, 13, 11, skin.palette.gold);
        surf.fillRect(cx - 6, gy, 13, 1, skin.palette.goldLight);
        surf.fillRect(cx - 5, gy + 1, 11, 9, team.pedestalSide);
      }

      const gx = cx - 5;
      const glyphTop = opts.unitStanding !== false ? gy : cy - 5;
      for (let r = 0; r < glyph.length; r++) {
        const row = glyph[r];
        for (let c = 0; c < row.length; c++) {
          if (row[c] === '1') {
            surf.setPixel(gx + c + 1, glyphTop + r + 1, '#070a14');
            surf.setPixel(gx + c, glyphTop + r, r < 3 ? '#ffffff' : (r < 6 ? skin.palette.goldLight : team.hanjaColor));
          }
        }
      }

      pedCanvas = surf.toCanvas();
      if (pedCanvas) {
        if (_spriteCache.size > MAX_CACHE_ENTRIES) _spriteCache.clear();
        _spriteCache.set(cacheKey, pedCanvas);
      }
    }

    if (pedCanvas) {
      ctx.save();
      ctx.imageSmoothingEnabled = false;
      const dw = pedCanvas.width * ps;
      const dh = pedCanvas.height * ps;
      ctx.drawImage(pedCanvas, Math.round(x - dw / 2), Math.round(y - dh * 0.44), dw, dh);
      ctx.restore();
    }
  }

  // ============================================================================
  // 6. HD 76x76 PIXEL ART ILLUSTRATION BUILDERS (4 FACTIONS × 12 CLASSES)
  // ============================================================================

  function getSteppedFrameState(type, stateInput, progressInput, timeInput) {
    const st = String(stateInput || 'IDLE').toUpperCase();
    const p = clamp(progressInput || 0, 0, 1);
    const t = timeInput !== undefined ? timeInput : Date.now();

    let frameIdx = 0;
    if (st === 'IDLE') {
      frameIdx = Math.floor(t / 220) % 4;
    } else if (st === 'MOVE') {
      frameIdx = Math.floor(t / 110) % 4;
    } else {
      frameIdx = Math.min(5, Math.floor(p * 6));
    }

    const bobTable = [0, -1, -2, -1];
    const strideTable = [-3, 0, 3, 0];

    const info = {
      state: st,
      frameIdx,
      bobY: 0,
      shiftX: 0,
      shiftY: 0,
      legStep: 0,
      armPose: 'NEUTRAL',
      capeFrame: frameIdx % 3,
      showSmear: false,
      flashMode: null,
      shatterProgress: 0
    };

    if (st === 'IDLE') {
      info.bobY = bobTable[frameIdx];
      info.legStep = 0;
    } else if (st === 'MOVE') {
      info.bobY = (frameIdx % 2 === 1) ? -2 : 0;
      info.legStep = strideTable[frameIdx];
      info.shiftX = 2;
    } else if (st === 'ATTACK') {
      if (frameIdx <= 1) {
        info.shiftX = -4;
        info.bobY = -1;
        info.armPose = 'RAISED';
        info.legStep = -2;
      } else if (frameIdx <= 3) {
        info.shiftX = 6;
        info.bobY = 0;
        info.armPose = 'STRIKE';
        info.legStep = 3;
        info.showSmear = true;
      } else {
        info.shiftX = 2;
        info.armPose = 'NEUTRAL';
      }
    } else if (st === 'HIT') {
      info.shiftX = -5;
      info.bobY = -1;
      info.armPose = 'GUARD';
      info.flashMode = (frameIdx % 2 === 0) ? 'WHITE' : 'RED';
    } else if (st === 'DEATH') {
      info.shatterProgress = Math.max(0.1, p);
      info.flashMode = frameIdx === 0 ? 'WHITE' : null;
    }

    return info;
  }

  /**
   * Draws a 3-Fold Draped Cloak, Royal Mantle, Valkyrie Wings & Floating Orbs, or Back-Banners
   */
  function drawPixelCapeAndBanner(surf, cx, cy, factionKey, skin, team, type, frameInfo) {
    const p = skin.palette;
    const wave = frameInfo.capeFrame;
    const capeRamp = buildHueShiftedRamp(skin, team, 'CAPE');
    const goldRamp = buildHueShiftedRamp(skin, team, 'GOLD');

    // Special Queen Radiant Valkyrie / Phoenix Wings & Floating Arcane Orbs
    if (type === 'QUEEN') {
      const wingLift = frameInfo.armPose === 'STRIKE' ? -3 : -wave;
      // Left & Right Unfurled Radiant Feather Wings behind shoulders
      for (let f = 0; f < 5; f++) {
        const wy = cy - 26 + f * 3 + wingLift;
        const wLen = 18 - f * 2 + wave;
        const featherCol = f === 0 ? '#ffffff' : (f < 3 ? p.goldLight : p.fxPrimary);
        surf.fillRect(cx - 6 - wLen, wy, wLen, 2, featherCol);
        surf.fillRect(cx - 5 - wLen, wy + 2, wLen - 2, 1, p.gold);
        // Forward wingtip feathers
        surf.fillRect(cx + 4, wy - 2, Math.max(4, wLen - 7), 2, featherCol);
      }
      // 3 Floating Celestial / Arcane Orbs orbiting above Queen
      const orbOffsets = [
        [-14 - wave, -32 + wingLift],
        [0, -37 - wingLift],
        [13 + wave, -31 + wingLift]
      ];
      for (let i = 0; i < orbOffsets.length; i++) {
        const ox = cx + orbOffsets[i][0];
        const oy = cy + orbOffsets[i][1];
        surf.fillCircle(ox, oy, 3, p.fxPrimary, team.neon);
        surf.fillRect(ox - 1, oy - 1, 2, 2, '#ffffff');
        surf.setPixel(ox, oy - 5, p.goldLight);
      }
    }

    // Flowing 3-Fold Draped Cloak
    const cloakH = (type === 'KING' || type === 'QUEEN' || type === 'BISHOP') ? 18 : 15;
    surf.fillFoldedCloak(cx - 10, cy - 18, 10, cloakH, wave, capeRamp, p.gold);

    // Royal Ermine Collar for KING
    if (type === 'KING') {
      surf.fillRect(cx - 9, cy - 19, 14, 3, '#f8fafc');
      for (let ex = cx - 8; ex <= cx + 4; ex += 3) {
        surf.setPixel(ex, cy - 18, '#070a14');
      }
    }

    // Towering War-Banner (Sashimono / Royal Standard) for KING, CHARIOT, GUARD, ROOK
    if (type === 'KING' || type === 'CHARIOT' || type === 'GUARD' || type === 'ROOK') {
      const bx = cx - 8;
      const by = cy - 36;
      // NMM Gold Banner Pole + Finial Spearhead
      surf.fillRect(bx, by, 2, 24, p.goldDark);
      surf.fillRect(bx, by, 1, 24, p.goldLight);
      surf.fillRect(bx - 1, by - 2, 4, 2, p.goldSpec);
      // Fluttering 3-Fold Pennant Flag
      surf.fillFoldedCloak(bx - 11, by + 2, 11, 10, wave, capeRamp, p.goldLight);
      // Mini Faction Emblem on Banner
      surf.fillRect(bx - 7 - wave, by + 5, 4, 4, goldRamp[5]);
      surf.setPixel(bx - 6 - wave, by + 6, '#ffffff');
    }
  }

  /**
   * Draws HD NMM Helmet, Crown, Tiara, Mitre, or Crenellated Fortress Helm
   */
  function drawPixelHelmet(surf, hx, hy, factionKey, type, skin, team) {
    const p = skin.palette;
    const armorRamp = buildHueShiftedRamp(skin, team, 'ARMOR');
    const goldRamp = buildHueShiftedRamp(skin, team, 'GOLD');
    const secRamp = buildHueShiftedRamp(skin, team, 'SECONDARY');

    // 1. Sculpted Face with 4-Tone Shading & Gleaming Eyes
    surf.fillRect(hx - 4, hy - 6, 9, 7, p.skin);
    surf.fillRect(hx - 4, hy - 2, 9, 3, p.skinShade);
    surf.fillRect(hx - 4, hy, 9, 1, p.skinShadow);
    surf.fillRect(hx + 1, hy - 5, 3, 2, p.skinLight);
    // Fierce Pixel Eyes with White Specular Spark
    surf.fillRect(hx - 2, hy - 4, 2, 2, '#070a14');
    surf.setPixel(hx - 1, hy - 4, '#ffffff');
    surf.fillRect(hx + 2, hy - 4, 2, 2, '#070a14');
    surf.setPixel(hx + 3, hy - 4, type === 'KING' || type === 'QUEEN' ? team.neonBright : '#ffffff');

    // 2. Specialized Chess & Janggi Class Headgear
    if (type === 'QUEEN') {
      // Flowing Empress Hair / Silk Veil behind head
      const hairCol = factionKey === 'TEMPLAR' ? '#fde047' : (factionKey === 'BYZANTINE' ? '#581c87' : '#1e293b');
      surf.fillRect(hx - 7, hy - 7, 4, 11, hairCol);
      // Tall Phoenix Bogwan / Valkyrie Winged Tiara / Imperial Augusta Diadem
      surf.fillNMMPlate(hx - 5, hy - 11, 11, 4, goldRamp, p.bounceLight);
      // 5 Jeweled Crown Spires
      surf.fillRect(hx - 5, hy - 14, 2, 3, p.goldLight);
      surf.fillRect(hx - 2, hy - 15, 2, 4, p.goldSpec);
      surf.fillRect(hx, hy - 17, 2, 6, '#ffffff');
      surf.fillRect(hx + 3, hy - 15, 2, 4, p.goldSpec);
      surf.fillRect(hx + 5, hy - 13, 2, 2, p.goldLight);
      // Center Tiara Gem & Valkyrie Wing Ears
      surf.fillRect(hx, hy - 10, 2, 2, team.neonBright);
      surf.fillRect(hx - 8, hy - 13, 3, 4, '#ffffff');
      surf.fillRect(hx + 6, hy - 13, 3, 4, '#ffffff');
      return;
    }

    if (type === 'BISHOP') {
      // High Inquisitor Mitre / Golden Lotus Dogwan / Patriarch Crown / Grand Mufti Turban
      if (factionKey === 'MAMLUK') {
        surf.fillNMMDome(hx, hy - 10, 7, 5, secRamp, false);
        surf.fillNMMPlate(hx - 3, hy - 16, 7, 5, goldRamp);
        surf.fillRect(hx - 1, hy - 19, 3, 3, p.fxPrimary);
      } else {
        // Tall Cloven Mitre Hat with Gold Cross / Lotus Inlay
        surf.fillNMMPlate(hx - 5, hy - 12, 11, 6, secRamp, p.bounceLight);
        surf.fillNMMPlate(hx - 4, hy - 16, 9, 4, secRamp);
        surf.fillRect(hx - 2, hy - 19, 5, 3, p.goldLight);
        // Gold vertical & horizontal band on Mitre
        surf.fillRect(hx, hy - 18, 2, 12, p.goldLight);
        surf.fillRect(hx - 5, hy - 8, 11, 2, p.gold);
        surf.setPixel(hx + 1, hy - 13, '#ffffff');
      }
      // Floating Sacred Halo behind Bishop's head
      for (let a = -6; a <= 6; a += 2) {
        surf.setPixel(hx + a, hy - 21 + Math.abs(Math.floor(a / 3)), p.goldLight);
      }
      return;
    }

    if (type === 'ROOK') {
      // Colossal Crenellated Castle-Fortress Greathelm
      surf.fillNMMPlate(hx - 6, hy - 12, 13, 12, armorRamp, p.bounceLight);
      // Dark T-Visor with glowing eyes
      surf.fillRect(hx - 4, hy - 6, 9, 2, '#070a14');
      surf.fillRect(hx, hy - 6, 2, 6, '#070a14');
      surf.setPixel(hx + 2, hy - 6, team.neonBright);
      surf.setPixel(hx - 2, hy - 6, team.neonBright);
      // Castle Battlement Crenellations on Crown of Helmet!
      surf.fillRect(hx - 6, hy - 13, 13, 2, p.gold);
      surf.fillRect(hx - 6, hy - 16, 3, 3, p.goldLight);
      surf.fillRect(hx - 1, hy - 16, 3, 3, p.goldSpec);
      surf.fillRect(hx + 4, hy - 16, 3, 3, p.goldLight);
      return;
    }

    // 3. Faction-Specific NMM Helmets for KING, CHARIOT, CANNON, HORSE, ELEPHANT, GUARD, SOLDIER, KNIGHT, PAWN
    if (factionKey === 'GORYEO') {
      // Studded Brigandine Neck-Guard Flaps (드림)
      surf.fillNMMPlate(hx - 6, hy - 6, 4, 8, secRamp, p.bounceLight);
      surf.setPixel(hx - 5, hy - 4, p.goldLight);
      surf.setPixel(hx - 5, hy - 1, p.goldLight);

      const helmRamp = type === 'KING' ? goldRamp : armorRamp;
      surf.fillNMMDome(hx, hy - 7, 6, 5, helmRamp, true);
      surf.fillRect(hx - 6, hy - 6, 13, 2, p.gold);

      // Iron Demon/Mask Visor for CHARIOT / KNIGHT / HORSE
      if (type === 'CHARIOT' || type === 'KNIGHT' || type === 'HORSE') {
        surf.fillNMMPlate(hx - 3, hy - 5, 8, 6, armorRamp);
        surf.fillRect(hx + 1, hy - 4, 3, 1, team.neonBright);
        if (type === 'KNIGHT') {
          // Horned Gaema Crest
          surf.fillRect(hx - 6, hy - 14, 2, 5, p.goldLight);
          surf.fillRect(hx + 4, hy - 14, 2, 5, p.goldLight);
        }
      }

      // Towering Spire & Flowing Red/Neon Horsehair Plume (상모)
      surf.fillRect(hx, hy - 15, 2, 4, p.goldLight);
      surf.fillRect(hx - 6, hy - 17, 7, 3, team.neon);
      surf.fillRect(hx - 9, hy - 15, 5, 3, p.clothLight);
    } else if (factionKey === 'TEMPLAR') {
      if (type === 'SOLDIER' || type === 'PAWN') {
        // NMM Sallet / Wide Kettle Hat
        surf.fillNMMDome(hx, hy - 7, 6, 5, armorRamp, true);
        surf.fillRect(hx - 8, hy - 6, 17, 2, p.metalLight);
        surf.fillRect(hx - 7, hy - 5, 15, 1, p.gold);
      } else {
        // Crusader Flat-Top / Sugarloaf Greathelm with NMM Specular Sheen
        surf.fillNMMPlate(hx - 5, hy - 12, 11, 12, armorRamp, p.bounceLight);
        // Golden Jerusalem Cross on Faceplate
        surf.fillRect(hx + 1, hy - 11, 2, 10, p.gold);
        surf.fillRect(hx - 4, hy - 7, 10, 2, p.goldLight);
        // Dark Eye Slits with glowing knightly resolve
        surf.fillRect(hx - 3, hy - 7, 9, 1, '#070a14');
        surf.setPixel(hx + 3, hy - 7, team.neonBright);
      }
      if (type === 'KING') {
        // Lionheart Royal Crown atop Greathelm
        surf.fillNMMPlate(hx - 5, hy - 15, 11, 3, goldRamp);
        surf.fillRect(hx - 5, hy - 17, 2, 2, p.goldSpec);
        surf.fillRect(hx, hy - 18, 2, 3, '#ffffff');
        surf.fillRect(hx + 4, hy - 17, 2, 2, p.goldSpec);
      } else if (type === 'KNIGHT' || type === 'CHARIOT' || type === 'GUARD') {
        // Sweeping Crusader Feather Plume
        surf.fillRect(hx - 7, hy - 16, 8, 3, team.neonBright);
        surf.fillRect(hx - 10, hy - 14, 5, 3, p.cloth);
      }
    } else if (factionKey === 'BYZANTINE') {
      // Golden Imperial Conical Helm / Stemmatogyrion Crown
      surf.fillNMMDome(hx, hy - 7, 6, 5, goldRamp, true);
      surf.fillRect(hx - 1, hy - 15, 3, 3, p.goldSpec);
      // Chainmail Aventail & Pearl Pendilia Chains
      surf.fillDitherRect(hx - 5, hy - 5, 4, 6, p.metal, p.metalDark);
      if (type === 'KING') {
        // Imperial Pearl Pendilia hanging beside cheeks
        surf.fillRect(hx - 5, hy - 5, 1, 6, '#ffffff');
        surf.fillRect(hx + 5, hy - 5, 1, 6, '#ffffff');
      }
      // Imperial Tyrian Purple Plume Crest
      surf.fillRect(hx - 5, hy - 16, 9, 3, p.clothLight);
      surf.fillRect(hx - 7, hy - 14, 5, 2, team.neon);
    } else if (factionKey === 'MAMLUK') {
      // Pointed Damascus Dome + Wound Emerald/Teal Silk Turban
      surf.fillNMMPlate(hx - 2, hy - 16, 5, 4, goldRamp);
      surf.setPixel(hx, hy - 18, '#ffffff');
      surf.fillNMMDome(hx, hy - 8, 7, 4, secRamp, false);
      surf.fillRect(hx - 5, hy - 9, 11, 1, p.goldLight);
      // Damascus Steel Nasal Bar & Mail Veil
      surf.fillDitherRect(hx - 4, hy - 4, 9, 5, p.armorPrimary, p.armorLight);
      surf.fillRect(hx + 2, hy - 7, 1, 5, p.goldLight);
    }
  }

  /**
   * Draws Sculpted NMM Cuirass, Pauldrons, Tassets, and Multi-Jointed Legs
   */
  function drawPixelTorsoAndLegs(surf, cx, cy, factionKey, type, skin, team, frameInfo, isMounted) {
    const p = skin.palette;
    const armorRamp = buildHueShiftedRamp(skin, team, 'ARMOR');
    const secRamp = buildHueShiftedRamp(skin, team, 'SECONDARY');
    const goldRamp = buildHueShiftedRamp(skin, team, 'GOLD');

    if (!isMounted) {
      const step = frameInfo.legStep;
      // Multi-jointed Greaves & Sabatons (Left & Right Legs)
      surf.fillNMMPlate(cx - 5 - step, cy - 1, 4, 8, armorRamp, p.bounceLight);
      surf.fillRect(cx - 5 - step, cy + 5, 5, 2, p.goldDark);
      surf.fillNMMPlate(cx + 1 + step, cy - 1, 4, 8, armorRamp, p.bounceLight);
      surf.fillRect(cx + 1 + step, cy + 5, 5, 2, p.gold);
      // Knee Poleyn Guards
      surf.fillRect(cx - 5 - step, cy + 1, 4, 2, p.goldLight);
      surf.fillRect(cx + 1 + step, cy + 1, 4, 2, p.goldLight);
    }

    // Specialized Queen Battle-Skirt & Sculpted Valkyrie Cuirass
    if (type === 'QUEEN') {
      if (!isMounted) {
        surf.fillFoldedCloak(cx - 6, cy - 6, 13, 12, frameInfo.capeFrame, secRamp, p.goldLight);
      }
      surf.fillNMMPlate(cx - 6, cy - 17, 13, 11, goldRamp, p.bounceLight);
      // Glowing Celestial Heart Gem on Breastplate
      surf.fillRect(cx - 1, cy - 14, 4, 4, team.neonBright);
      surf.setPixel(cx, cy - 13, '#ffffff');
      // Ornate Winged Pauldrons
      surf.fillNMMDome(cx - 7, cy - 15, 3, 3, goldRamp, false);
      surf.fillNMMDome(cx + 7, cy - 15, 3, 3, goldRamp, false);
      return;
    }

    // Specialized Bishop Ecclesiastical Vestment Robes & Golden Stola
    if (type === 'BISHOP') {
      surf.fillFoldedCloak(cx - 7, cy - 16, 15, 22, frameInfo.capeFrame, secRamp, p.goldLight);
      // Ornate Golden Stola Ribbons hanging down chest
      surf.fillRect(cx - 3, cy - 16, 2, 19, p.goldLight);
      surf.fillRect(cx + 2, cy - 16, 2, 19, p.goldLight);
      surf.fillRect(cx - 2, cy - 12, 6, 2, p.goldSpec);
      return;
    }

    // Armored Tassets / Lamellar Skirt
    surf.fillNMMPlate(cx - 6, cy - 6, 13, 7, secRamp, p.bounceLight);
    surf.fillRect(cx - 6, cy, 13, 1, p.gold);

    // Sculpted NMM Chest Cuirass
    const chestRamp = (type === 'KING' || type === 'ROOK') ? goldRamp : armorRamp;
    surf.fillNMMPlate(cx - 6, cy - 17, 13, 11, chestRamp, p.bounceLight);

    if (factionKey === 'TEMPLAR' && type !== 'ROOK') {
      // Crusader White Tabard + Crimson Cross
      surf.fillRect(cx - 5, cy - 16, 11, 10, p.armorSecondary);
      surf.fillRect(cx, cy - 16, 2, 10, p.cloth);
      surf.fillRect(cx - 4, cy - 12, 10, 2, p.cloth);
    } else {
      // NMM Golden Mirror Breastplate (원형 호심경) & Gem Core
      surf.fillRect(cx - 2, cy - 14, 5, 5, p.gold);
      surf.fillRect(cx - 1, cy - 13, 3, 3, team.neonBright);
      surf.setPixel(cx, cy - 13, '#ffffff');
    }

    // Shoulder Pauldrons (ROOK gets Crenellated Castle Battlement Pauldrons!)
    if (type === 'ROOK') {
      surf.fillNMMPlate(cx - 10, cy - 19, 5, 7, armorRamp, p.bounceLight);
      surf.fillNMMPlate(cx + 6, cy - 19, 5, 7, armorRamp, p.bounceLight);
      // Crenellations on shoulders
      surf.fillRect(cx - 10, cy - 21, 2, 2, p.goldLight);
      surf.fillRect(cx - 7, cy - 21, 2, 2, p.goldLight);
      surf.fillRect(cx + 6, cy - 21, 2, 2, p.goldLight);
      surf.fillRect(cx + 9, cy - 21, 2, 2, p.goldLight);
    } else {
      const pRamp = (type === 'KING' || type === 'GUARD') ? goldRamp : armorRamp;
      surf.fillNMMDome(cx - 7, cy - 14, 3, 3, pRamp, false);
      surf.fillNMMDome(cx + 7, cy - 14, 3, 3, pRamp, false);
      surf.fillRect(cx - 9, cy - 11, 5, 1, p.gold);
      surf.fillRect(cx + 5, cy - 11, 5, 1, p.gold);
    }
  }

  /**
   * Draws HD NMM Weapons, Dual Blades, Croziers, Siege Hammers, Tower Shields & 3-Tone Slash Smears
   */
  function drawPixelWeaponAndShield(surf, cx, cy, factionKey, type, skin, team, frameInfo) {
    const p = skin.palette;
    const armPose = frameInfo.armPose;
    const armorRamp = buildHueShiftedRamp(skin, team, 'ARMOR');
    const goldRamp = buildHueShiftedRamp(skin, team, 'GOLD');
    const secRamp = buildHueShiftedRamp(skin, team, 'SECONDARY');

    let wx = cx + 7;
    let wy = cy - 11;
    if (armPose === 'RAISED') { wx -= 4; wy -= 6; }
    else if (armPose === 'STRIKE') { wx += 5; wy += 1; }

    // Armored Gauntlet & Vambrace
    surf.fillNMMPlate(wx - 2, wy, 5, 4, armorRamp);
    surf.fillRect(wx + 1, wy, 2, 3, p.goldLight);

    // --- 1. CLASS-SPECIFIC MAIN WEAPONS ---
    if (type === 'KING') {
      // Blazing Royal Greatsword / Four-Tiger Saingeom
      if (armPose === 'STRIKE') {
        surf.fillRect(wx + 2, wy - 3, 22, 5, team.neon);
        surf.fillRect(wx + 2, wy - 2, 21, 3, team.neonBright);
        surf.fillRect(wx + 2, wy - 1, 20, 1, '#ffffff');
        surf.fillRect(wx + 1, wy - 5, 2, 10, p.goldLight);
      } else {
        surf.fillRect(wx + 1, wy - 24, 5, 23, team.neon);
        surf.fillRect(wx + 2, wy - 23, 3, 22, team.neonBright);
        surf.fillRect(wx + 3, wy - 22, 1, 21, '#ffffff');
        surf.fillRect(wx - 1, wy - 2, 9, 2, p.goldLight);
        surf.setPixel(wx + 3, wy - 2, '#ffffff');
      }
    } else if (type === 'QUEEN') {
      // Left Hand Secondary Blade / Astral Scepter
      const lx = cx - 9;
      const ly = cy - 12;
      surf.drawNMMBlade(lx, ly, lx - 11, ly - 14, '#ffffff', p.fxPrimary, team.neon);
      surf.fillRect(lx - 2, ly - 2, 4, 2, p.goldLight);
      // Right Hand Primary Radiant Phoenix / Valkyrie Longblade
      if (armPose === 'STRIKE') {
        surf.drawNMMBlade(wx + 2, wy, wx + 24, wy - 4, '#ffffff', p.goldLight, p.fxPrimary);
        surf.drawNMMBlade(wx + 2, wy + 2, wx + 22, wy + 7, '#ffffff', team.neonBright, team.neon);
      } else {
        surf.drawNMMBlade(wx + 2, wy - 1, wx + 16, wy - 22, '#ffffff', p.fxPrimary, team.neon);
        surf.fillRect(wx, wy - 3, 6, 2, p.goldSpec);
      }
    } else if (type === 'ROOK') {
      // Colossal Siege Warhammer / Battering Maul
      const hx = armPose === 'STRIKE' ? wx + 5 : wx + 2;
      surf.fillRect(hx, wy - 22, 3, 26, p.woodLight);
      surf.fillRect(hx, wy - 22, 1, 26, p.gold);
      // Giant Crenellated NMM Hammer Head
      surf.fillNMMPlate(hx - 5, wy - 26, 14, 8, armorRamp, p.bounceLight);
      surf.fillRect(hx - 5, wy - 26, 14, 2, p.goldLight);
      // Impact Spikes on front of Warhammer
      surf.fillRect(hx + 9, wy - 25, 4, 2, '#ffffff');
      surf.fillRect(hx + 9, wy - 21, 4, 2, '#ffffff');
    } else if (type === 'BISHOP') {
      // Towering Ornate Crozier / Sacred Flame Staff
      const sx = wx + 3;
      surf.fillRect(sx, wy - 24, 2, 30, p.gold);
      surf.fillRect(sx, wy - 24, 1, 30, p.goldLight);
      // Curled Golden Crosier Hook / Lotus / Chalice Top
      surf.fillNMMDome(sx + 1, wy - 27, 5, 4, goldRamp, false);
      surf.fillCircle(sx + 1, wy - 28, 3, p.fxPrimary, '#ffffff');
      // Floating Sacred Rune Pixels around Staff
      surf.fillRect(sx + 7, wy - 26, 2, 2, team.neonBright);
      surf.fillRect(sx - 5, wy - 31, 2, 2, p.goldSpec);
      // Left hand Illuminated Scripture Tome / Scroll
      surf.fillRect(cx - 9, cy - 11, 5, 6, p.cloth);
      surf.fillRect(cx - 8, cy - 10, 4, 4, '#fef9c3');
    } else if (type === 'CHARIOT' || type === 'KNIGHT') {
      // Giant Couched Heavy Jousting / Gaema Lance with Spiral Gold Bands
      const lx = armPose === 'STRIKE' ? wx + 4 : wx - 4;
      surf.fillRect(lx - 10, wy - 1, 12, 3, p.wood);
      surf.fillNMMPlate(lx + 1, wy - 4, 4, 8, goldRamp);
      // Tapered 3-Tone NMM Lance Blade
      surf.fillRect(lx + 5, wy - 3, 14, 6, p.metalDark);
      surf.fillRect(lx + 5, wy - 2, 21, 4, p.metal);
      surf.fillRect(lx + 5, wy - 1, 26, 2, p.metalLight);
      surf.fillRect(lx + 24, wy, 7, 1, '#ffffff');
      // Spiral gold lance ribs
      for (let gx = lx + 7; gx < lx + 20; gx += 4) {
        surf.fillRect(gx, wy - 2, 2, 3, p.goldLight);
      }
      // Fluttering Lance Pennant
      surf.fillRect(lx + 10, wy + 3, 7, 3, team.neon);
    } else if (type === 'HORSE') {
      if (factionKey === 'GORYEO') {
        // Cavalry Iron Flail (마상편곤)
        surf.fillRect(wx + 1, wy - 18, 2, 18, p.woodLight);
        surf.fillRect(wx + 3, wy - 19, 4, 2, p.goldLight);
        surf.fillNMMPlate(wx + 7, wy - 17, 4, 11, armorRamp);
      } else {
        // Curved Damascus Scimitar / Cavalry Broadsword
        surf.drawNMMBlade(wx + 1, wy, wx + 15, wy - 17, '#ffffff', p.metalLight, p.metalDark);
        surf.fillRect(wx, wy - 2, 5, 2, p.goldLight);
      }
    } else if (type === 'GUARD') {
      // Royal Polearm: Halberd / Hyeopdo Glaive / Dane Axe
      surf.fillRect(wx + 1, wy - 22, 2, 30, p.woodLight);
      surf.fillRect(wx + 1, wy - 28, 2, 6, '#ffffff');
      surf.fillNMMPlate(wx + 3, wy - 24, 8, 10, armorRamp);
      surf.fillRect(wx + 10, wy - 23, 2, 8, '#ffffff');
      surf.fillRect(wx + 3, wy - 24, 8, 2, p.goldLight);
    } else if (type === 'SOLDIER' || type === 'PAWN') {
      // Infantry Long Spear / Arming Spear
      const sx = armPose === 'STRIKE' ? wx + 5 : wx;
      surf.drawLine(sx - 7, wy + 4, sx + 17, wy - 11, p.woodLight, 2);
      surf.drawNMMBlade(sx + 14, wy - 10, sx + 22, wy - 15, '#ffffff', p.metalLight, p.metalDark);
      surf.fillRect(sx + 13, wy - 11, 2, 3, p.gold);
    }

    // --- 2. SHIELDS (ROOK Citadel Wall Shield, PAWN/SOLDIER/GUARD/KING/KNIGHT Shields) ---
    if (type === 'ROOK') {
      // Colossal Citadel Bastion Tower Shield (Left Front)
      const shX = cx - 3;
      const shY = cy - 16;
      surf.fillNMMPlate(shX, shY, 12, 19, secRamp, p.bounceLight);
      // Crenellated Castle Battlement Top on Shield
      surf.fillRect(shX, shY - 2, 3, 2, p.goldLight);
      surf.fillRect(shX + 4, shY - 2, 4, 2, p.goldSpec);
      surf.fillRect(shX + 9, shY - 2, 3, 2, p.goldLight);
      // Gold Border & Faction Boss
      surf.fillRect(shX, shY, 12, 1, p.gold);
      surf.fillRect(shX, shY + 18, 12, 1, p.gold);
      surf.fillRect(shX + 4, shY + 5, 4, 7, p.goldLight);
      surf.setPixel(shX + 5, shY + 7, '#ffffff');
    } else if (type === 'SOLDIER' || type === 'PAWN' || type === 'GUARD' || type === 'KING' || type === 'HORSE' || type === 'KNIGHT') {
      const shX = cx + 1;
      const shY = cy - 12;
      if (factionKey === 'TEMPLAR') {
        // White Heater / Crusader Kite Shield with Red Cross & Gold Rim
        const shH = (type === 'PAWN' || type === 'GUARD') ? 14 : 12;
        surf.fillNMMPlate(shX, shY, 10, shH, secRamp);
        surf.fillRect(shX, shY, 10, 1, p.goldLight);
        surf.fillRect(shX + 4, shY + 1, 2, shH - 2, p.cloth);
        surf.fillRect(shX + 1, shY + 5, 8, 2, p.cloth);
      } else if (factionKey === 'GORYEO' && (type === 'SOLDIER' || type === 'PAWN')) {
        // Rectangular Paengbae Shield (팽배 대방패) with Triple Gold Boss
        surf.fillNMMPlate(shX, shY - 1, 10, 14, secRamp, p.bounceLight);
        surf.fillRect(shX, shY - 1, 10, 1, p.goldLight);
        surf.fillRect(shX, shY + 12, 10, 1, p.gold);
        surf.fillRect(shX + 3, shY + 4, 4, 4, p.goldLight);
        surf.setPixel(shX + 4, shY + 5, '#ffffff');
      } else {
        // Ornate Round Shield (Skouton / Mirror Dhal / Bonghwang Buckler)
        surf.fillCircle(shX + 5, shY + 6, 6, p.armorSecondary, p.armorSecDark);
        surf.fillCircle(shX + 5, shY + 6, 4, p.gold, p.armorSecondary);
        surf.fillRect(shX + 4, shY + 5, 3, 3, p.goldSpec);
      }
    }

    // --- 3. 3-TONE ARCADE PIXEL WEAPON SMEAR ARC DURING ATTACK ---
    if (frameInfo.showSmear) {
      surf.drawLine(cx + 16, cy - 28, cx + 30, cy - 12, '#ffffff', 3);
      surf.drawLine(cx + 30, cy - 12, cx + 20, cy + 4, p.fxPrimary, 2);
      surf.drawLine(cx + 14, cy - 25, cx + 26, cy - 12, p.fxSecondary, 2);
    }
  }

  /**
   * Draws HD NMM Warhorses (HORSE, KNIGHT, CHARIOT), War Elephants (ELEPHANT), and Siege Artillery (CANNON)
   */
  function drawPixelMountAndArtillery(surf, cx, cy, factionKey, type, skin, team, frameInfo) {
    const p = skin.palette;
    const step = frameInfo.legStep;
    const armorRamp = buildHueShiftedRamp(skin, team, 'ARMOR');
    const secRamp = buildHueShiftedRamp(skin, team, 'SECONDARY');
    const goldRamp = buildHueShiftedRamp(skin, team, 'GOLD');

    if (type === 'HORSE' || type === 'KNIGHT' || type === 'CHARIOT') {
      const isHeavyBarded = (type === 'CHARIOT' || type === 'KNIGHT');
      const rearLift = (type === 'KNIGHT' && frameInfo.armPose === 'STRIKE') ? -3 : 0;

      // 4-Frame Galloping Horse Legs with Golden Hooves
      surf.fillRect(cx - 13 - step, cy - 1, 3, 8, p.woodDark);
      surf.fillRect(cx - 13 - step, cy + 5, 3, 2, p.gold);
      surf.fillRect(cx - 7 + step, cy - 1, 3, 8, p.wood);
      surf.fillRect(cx + 7 + step, cy - 1 + rearLift, 3, 8, p.woodDark);
      surf.fillRect(cx + 12 - step, cy - 2 + rearLift, 3, 8, p.wood);
      surf.fillRect(cx + 12 - step, cy + 4 + rearLift, 3, 2, p.goldLight);

      // Horse Body & NMM Plate/Scale Barding (개마 / 데미랜서 마갑)
      if (isHeavyBarded) {
        surf.fillNMMPlate(cx - 15, cy - 12, 30, 12, armorRamp, p.bounceLight);
      } else {
        surf.fillDitherRect(cx - 14, cy - 11, 28, 11, p.woodLight, p.wood);
      }

      // Flowing Caparison Barding Skirt with Gold Hem
      surf.fillFoldedCloak(cx - 13, cy - 5, 26, 6, frameInfo.capeFrame, secRamp, p.goldLight);

      // High-Crested Warhorse Neck & Armored Chanfron Head (Iconic Chess Knight Silhouette for KNIGHT!)
      const headLift = type === 'KNIGHT' ? -3 : 0;
      surf.fillNMMPlate(cx + 9, cy - 22 + headLift, 9, 13, isHeavyBarded ? armorRamp : secRamp);
      surf.fillNMMPlate(cx + 13, cy - 23 + headLift, 8, 6, isHeavyBarded ? goldRamp : armorRamp);
      // Flowing Horse Mane
      surf.fillRect(cx + 7, cy - 21 + headLift, 3, 10, team.neon);
      // Glowing Destrier Eye & Unicorn Spike
      surf.setPixel(cx + 16, cy - 21 + headLift, team.neonBright);
      surf.fillRect(cx + 18, cy - 26 + headLift, 3, 3, '#ffffff');

      // Chariot Spoked Bronze/Gold Wheel
      if (type === 'CHARIOT') {
        surf.fillCircle(cx - 7, cy + 2, 7, p.metalDark, p.armorPrimary);
        surf.fillCircle(cx - 7, cy + 2, 5, p.gold, p.woodDark);
        surf.fillRect(cx - 8, cy + 1, 3, 3, '#ffffff');
      }
    } else if (type === 'ELEPHANT') {
      // Colossal HD War Elephant with NMM Tusks & Crenellated Howdah Battle-Tower
      surf.fillDitherRect(cx - 15 - step, cy - 6, 8, 13, '#64748b', '#334155');
      surf.fillRect(cx - 15 - step, cy + 5, 8, 2, p.goldLight);
      surf.fillDitherRect(cx + 5 + step, cy - 6, 8, 13, '#64748b', '#334155');
      surf.fillRect(cx + 5 + step, cy + 5, 8, 2, p.goldLight);

      // Massive Sculpted Elephant Body & Royal Caparison Tapestry
      surf.fillDitherRect(cx - 18, cy - 23, 34, 19, '#64748b', '#475569');
      surf.fillFoldedCloak(cx - 12, cy - 21, 21, 14, frameInfo.capeFrame, secRamp, p.goldLight);

      // Crenellated Fortress Howdah Tower on Back
      surf.fillNMMPlate(cx - 11, cy - 33, 18, 12, goldRamp, p.bounceLight);
      surf.fillRect(cx - 12, cy - 36, 4, 3, p.goldSpec);
      surf.fillRect(cx - 4, cy - 36, 4, 3, p.goldSpec);
      surf.fillRect(cx + 4, cy - 36, 4, 3, p.goldSpec);

      // Armored Elephant Head, Crown Crest, Swinging Trunk & Twin Steel-Tipped Tusks
      surf.fillDitherRect(cx + 11, cy - 23, 12, 15, '#64748b', '#475569');
      surf.fillNMMPlate(cx + 14, cy - 23, 8, 9, goldRamp);
      surf.setPixel(cx + 17, cy - 18, team.neonBright);

      const trunkLift = frameInfo.armPose === 'STRIKE' ? -6 : 0;
      surf.fillRect(cx + 20, cy - 15 + trunkLift, 5, 13, '#64748b');
      surf.fillRect(cx + 22, cy - 5 + trunkLift, 5, 4, '#475569');

      // Dual Ivory Tusks + NMM Steel Tusk Blades
      surf.fillRect(cx + 16, cy - 11, 11, 3, '#fef9c3');
      surf.fillRect(cx + 24, cy - 13, 7, 3, '#ffffff');
    } else if (type === 'CANNON') {
      // Master Artillery Engineer behind siege engine
      drawPixelTorsoAndLegs(surf, cx - 14, cy, factionKey, 'SOLDIER', skin, team, frameInfo, false);
      drawPixelHelmet(surf, cx - 14, cy - 17, factionKey, 'SOLDIER', skin, team);

      // Heavy Iron-Bound Timber Carriage
      surf.fillDitherRect(cx - 10, cy - 7, 28, 6, p.woodLight, p.wood);
      surf.fillRect(cx - 10, cy - 7, 28, 1, p.goldLight);

      if (factionKey === 'GORYEO') {
        // Munjong Singijeon Hwacha (문종 신기전 다연장 화차)
        surf.fillNMMPlate(cx - 3, cy - 22, 16, 15, armorRamp, p.bounceLight);
        surf.fillRect(cx - 3, cy - 22, 16, 2, p.goldLight);
        for (let ry = cy - 20; ry <= cy - 10; ry += 3) {
          surf.fillRect(cx + 12, ry, 8, 2, p.goldLight);
          surf.fillRect(cx + 18, ry, 4, 2, '#ef4444');
        }
        if (frameInfo.showSmear) {
          surf.fillCircle(cx + 24, cy - 15, 6, '#fde047', '#f97316');
          surf.fillCircle(cx + 24, cy - 15, 3, '#ffffff', '#fde047');
        }
      } else if (factionKey === 'BYZANTINE') {
        // Imperial Bronze Greek-Fire Siphon
        surf.fillNMMPlate(cx - 4, cy - 18, 22, 10, goldRamp, p.bounceLight);
        surf.fillRect(cx + 17, cy - 19, 6, 12, p.goldSpec);
        if (frameInfo.showSmear) {
          surf.fillDitherRect(cx + 23, cy - 18, 11, 10, '#10b981', '#fde047');
        }
      } else {
        // Royal Counterweight Trebuchet / Manjaniq
        surf.drawLine(cx - 5, cy - 7, cx + 5, cy - 28, p.woodLight, 3);
        surf.drawLine(cx + 13, cy - 7, cx + 5, cy - 28, p.wood, 3);
        if (frameInfo.armPose === 'STRIKE') {
          surf.drawLine(cx - 5, cy - 17, cx + 18, cy - 34, p.woodLight, 2);
          surf.fillCircle(cx + 20, cy - 35, 5, '#f97316', '#fde047');
        } else {
          surf.drawLine(cx - 15, cy - 14, cx + 13, cy - 29, p.woodLight, 2);
          surf.fillCircle(cx - 15, cy - 12, 5, '#f97316', '#ef4444');
        }
      }

      // Spoked Artillery Wheels
      surf.fillCircle(cx - 4, cy + 1, 6, p.wood, p.metalDark);
      surf.fillRect(cx - 5, cy, 3, 3, p.goldLight);
      surf.fillCircle(cx + 12, cy + 1, 6, p.wood, p.metalDark);
      surf.fillRect(cx + 11, cy, 3, 3, p.goldLight);
    }
  }

  /**
   * Builds (or retrieves from cache) the complete 76x76 HD Pixel Art Sprite Canvas for a unit frame.
   */
  function getOrBuildUnitSpriteCanvas(type, side, factionKey, frameInfo, isSelected, isCheck) {
    const cacheKey = `UNIT3_${factionKey}_${type}_${side}_${frameInfo.state}_${frameInfo.frameIdx}_${isSelected ? 1 : 0}_${isCheck ? 1 : 0}`;
    let cached = _spriteCache.get(cacheKey);
    if (cached) return cached;

    const skin = FACTION_SKINS[factionKey];
    const team = TEAM_THEMES[side];
    const gw = 76;
    const gh = 76;
    const surf = new PixelGridSurface(gw, gh);

    const cx = 36 + frameInfo.shiftX;
    const cy = 60 + frameInfo.bobY + frameInfo.shiftY;

    if (type === 'CANNON') {
      drawPixelMountAndArtillery(surf, cx, cy, factionKey, type, skin, team, frameInfo);
    } else if (type === 'ELEPHANT') {
      drawPixelMountAndArtillery(surf, cx, cy, factionKey, type, skin, team, frameInfo);
      drawPixelTorsoAndLegs(surf, cx - 2, cy - 28, factionKey, type, skin, team, frameInfo, true);
      drawPixelHelmet(surf, cx - 2, cy - 44, factionKey, type, skin, team);
    } else if (type === 'HORSE' || type === 'KNIGHT' || type === 'CHARIOT') {
      drawPixelMountAndArtillery(surf, cx, cy, factionKey, type, skin, team, frameInfo);
      drawPixelCapeAndBanner(surf, cx - 1, cy - 10, factionKey, skin, team, type, frameInfo);
      drawPixelTorsoAndLegs(surf, cx - 1, cy - 10, factionKey, type, skin, team, frameInfo, true);
      drawPixelHelmet(surf, cx - 1, cy - 27, factionKey, type, skin, team);
      drawPixelWeaponAndShield(surf, cx - 1, cy - 10, factionKey, type, skin, team, frameInfo);
    } else {
      // Foot Infantry / Monarch / Queen / Rook / Bishop / Guard / Pawn / Soldier
      drawPixelCapeAndBanner(surf, cx, cy, factionKey, skin, team, type, frameInfo);
      drawPixelTorsoAndLegs(surf, cx, cy, factionKey, type, skin, team, frameInfo, false);
      drawPixelHelmet(surf, cx, cy - 17, factionKey, type, skin, team);
      drawPixelWeaponAndShield(surf, cx, cy, factionKey, type, skin, team, frameInfo);
    }

    // Selective Outlining (Sel-out) + Subpixel AA + Optional Selection/Check Glow
    const outerGlow = isCheck ? '#ef4444' : (isSelected ? '#facc15' : null);
    surf.applyPixelOutline(skin.palette.outline, outerGlow, {
      topOutline: skin.palette.armorDark || '#1e293b',
      midOutline: skin.palette.deepShadow || '#0f172a',
      aaColor: skin.palette.metalDark || '#334155'
    });

    // Apply HIT palette flash if active
    if (frameInfo.flashMode === 'WHITE' || frameInfo.flashMode === 'RED') {
      const flashCol = frameInfo.flashMode === 'WHITE' ? '#ffffff' : '#ef4444';
      for (let i = 0; i < surf.grid.length; i++) {
        if (surf.grid[i] && surf.grid[i] !== skin.palette.outline) {
          surf.grid[i] = flashCol;
        }
      }
    }

    cached = surf.toCanvas();
    if (cached) {
      if (_spriteCache.size > MAX_CACHE_ENTRIES) _spriteCache.clear();
      _spriteCache.set(cacheKey, cached);
    }
    return cached;
  }

  // ============================================================================
  // 7. HD 48x48 COMMANDER PORTRAIT & SRW/FE BATTLE CUT-IN ILLUSTRATION API
  // ============================================================================

  function getOrBuildCommanderPortraitCanvas(factionKey, side, mood) {
    const cacheKey = `PORTRAIT3_${factionKey}_${side}_${mood || 'NORMAL'}`;
    let cached = _spriteCache.get(cacheKey);
    if (cached) return cached;

    const skin = FACTION_SKINS[factionKey] || FACTION_SKINS.GORYEO;
    const team = TEAM_THEMES[side] || TEAM_THEMES.CHU;
    const p = skin.palette;
    const goldRamp = buildHueShiftedRamp(skin, team, 'GOLD');
    const armorRamp = buildHueShiftedRamp(skin, team, 'ARMOR');
    const secRamp = buildHueShiftedRamp(skin, team, 'SECONDARY');
    const capeRamp = buildHueShiftedRamp(skin, team, 'CAPE');

    const surf = new PixelGridSurface(48, 48);

    // 1. Hue-Shifted Tapestry Backdrop & Diagonal Rays
    for (let y = 2; y < 46; y++) {
      for (let x = 2; x < 46; x++) {
        const diag = (x + y) % 10;
        let bgCol = p.deepShadow || '#0f172a';
        if (y < 16) bgCol = ((x + y) & 1) === 0 ? team.accentDark : (p.deepShadow || '#0f172a');
        else if (diag === 0) bgCol = team.pedestalDither;
        surf.setPixel(x, y, bgCol);
      }
    }

    // 2. Commander Shoulders, Cloak & NMM Breastplate (y: 30..45)
    surf.fillFoldedCloak(6, 31, 36, 15, 1, capeRamp, p.gold);
    surf.fillNMMPlate(12, 32, 24, 14, armorRamp, p.bounceLight);
    surf.fillNMMDome(10, 36, 6, 5, goldRamp, false);
    surf.fillNMMDome(38, 36, 6, 5, goldRamp, false);
    // Chest Mirror Plate / Cross
    if (factionKey === 'TEMPLAR') {
      surf.fillRect(15, 33, 18, 12, p.armorSecondary);
      surf.fillRect(23, 33, 3, 12, p.cloth);
      surf.fillRect(18, 37, 13, 3, p.cloth);
    } else {
      surf.fillCircle(24, 39, 4, p.goldLight, p.gold);
      surf.fillRect(23, 38, 3, 3, team.neonBright);
    }

    // 3. Sculpted 16/32-Bit Commander Face (y: 16..32)
    surf.fillRect(16, 16, 16, 15, p.skin);
    surf.fillRect(16, 25, 16, 6, p.skinShade);
    surf.fillRect(18, 17, 6, 4, p.skinLight);
    // Nose bridge & cheekbone highlight
    surf.fillRect(24, 20, 2, 5, p.skinLight);
    surf.fillRect(23, 24, 3, 1, p.skinShadow);

    // Expressive Commander Beard / Mustache / Jaw
    if (factionKey === 'GORYEO' || factionKey === 'BYZANTINE' || factionKey === 'MAMLUK') {
      const beardCol = factionKey === 'BYZANTINE' ? '#451a03' : '#1e293b';
      surf.fillRect(16, 26, 16, 2, beardCol);
      surf.fillRect(18, 28, 12, 4, beardCol);
      surf.fillRect(22, 27, 4, 1, p.skinShade);
    } else {
      // Scarred Crusader jawline
      surf.drawLine(18, 21, 20, 26, p.skinShadow, 1);
      surf.fillRect(22, 27, 5, 1, p.skinShadow);
    }

    // Fierce Glowing Eyes & Angled Eyebrows
    surf.fillRect(17, 19, 6, 2, '#070a14');
    surf.fillRect(26, 19, 6, 2, '#070a14');
    surf.fillRect(18, 21, 4, 2, '#070a14');
    surf.fillRect(27, 21, 4, 2, '#070a14');
    const eyeGlow = (mood === 'ATTACK' || mood === 'CHECK') ? team.neonBright : '#ffffff';
    surf.fillRect(19, 21, 2, 2, eyeGlow);
    surf.fillRect(28, 21, 2, 2, eyeGlow);
    if (mood === 'ATTACK' || mood === 'CHECK') {
      // Dramatic anime eye-glint flare
      surf.drawLine(25, 21, 35, 19, team.neonBright, 1);
      surf.setPixel(29, 21, '#ffffff');
    }

    // 4. Faction-Specific Grand Commander Helmet / Crown (y: 4..18)
    if (factionKey === 'GORYEO') {
      // Winged Golden Ikseongwan / Dragon General Helm + Red Plume
      surf.fillNMMDome(24, 15, 11, 8, goldRamp, true);
      surf.fillRect(13, 15, 22, 3, p.goldLight);
      surf.fillRect(22, 13, 5, 4, team.neonBright);
      // Brigandine Ear Guards (드림)
      surf.fillNMMPlate(11, 16, 5, 13, secRamp);
      surf.fillNMMPlate(33, 16, 5, 13, secRamp);
      surf.setPixel(13, 20, p.goldLight);
      surf.setPixel(35, 20, p.goldLight);
      // Top Plume
      surf.fillRect(23, 4, 3, 4, p.goldSpec);
      surf.fillRect(15, 3, 12, 3, p.clothLight);
    } else if (factionKey === 'TEMPLAR') {
      // Crowned Crusader Greathelm (Raised Visor + Royal Crown)
      surf.fillNMMPlate(14, 9, 20, 9, armorRamp);
      surf.fillNMMPlate(14, 6, 20, 4, goldRamp);
      surf.fillRect(15, 4, 3, 3, '#ffffff');
      surf.fillRect(23, 3, 3, 4, '#ffffff');
      surf.fillRect(31, 4, 3, 3, '#ffffff');
      // Chainmail Coif framing face
      surf.fillDitherRect(12, 17, 4, 13, p.metal, p.metalDark);
      surf.fillDitherRect(33, 17, 4, 13, p.metal, p.metalDark);
      // Golden Cross Brow
      surf.fillRect(23, 8, 3, 9, p.goldLight);
    } else if (factionKey === 'BYZANTINE') {
      // Imperial Stemmatogyrion Jeweled Crown + Pearl Pendilia
      surf.fillNMMDome(24, 14, 11, 8, goldRamp, true);
      surf.fillRect(13, 13, 22, 4, p.goldLight);
      surf.fillRect(17, 14, 3, 2, p.clothLight);
      surf.fillRect(23, 13, 3, 3, team.neonBright);
      surf.fillRect(29, 14, 3, 2, p.clothLight);
      // Hanging Pearl Pendilia Chains
      for (let py = 17; py <= 28; py += 2) {
        surf.fillRect(13, py, 2, 2, '#ffffff');
        surf.fillRect(34, py, 2, 2, '#ffffff');
      }
    } else if (factionKey === 'MAMLUK') {
      // Royal Sultan Spiked Turban Crown + Damascus Mail Veil
      surf.fillNMMPlate(21, 4, 7, 6, goldRamp);
      surf.fillNMMDome(24, 14, 12, 6, secRamp, false);
      surf.fillRect(13, 14, 22, 2, p.goldLight);
      surf.fillRect(23, 11, 3, 4, '#ffffff');
      // Mail Aventail & Nasal Guard
      surf.fillDitherRect(12, 18, 4, 12, p.armorPrimary, p.armorLight);
      surf.fillDitherRect(33, 18, 4, 12, p.armorPrimary, p.armorLight);
    }

    // 5. Beveled NMM Gold & Team-Neon Portrait Frame Border
    surf.fillRect(0, 0, 48, 2, '#070a14');
    surf.fillRect(0, 46, 48, 2, '#070a14');
    surf.fillRect(0, 0, 2, 48, '#070a14');
    surf.fillRect(46, 0, 2, 48, '#070a14');
    surf.fillRect(2, 2, 44, 2, p.goldLight);
    surf.fillRect(2, 44, 44, 2, p.goldDark);
    surf.fillRect(2, 2, 2, 44, p.gold);
    surf.fillRect(44, 2, 2, 44, p.gold);
    // Corner Neon Gems
    surf.fillRect(3, 3, 3, 3, team.neonBright);
    surf.fillRect(42, 3, 3, 3, team.neonBright);
    surf.fillRect(3, 42, 3, 3, team.neon);
    surf.fillRect(42, 42, 3, 3, team.neon);

    cached = surf.toCanvas();
    if (cached) {
      if (_spriteCache.size > MAX_CACHE_ENTRIES) _spriteCache.clear();
      _spriteCache.set(cacheKey, cached);
    }
    return cached;
  }

  /**
   * Renders an HD 48x48 Pixel Art Commander Portrait for HUD cards, dialogs, and battle cut-ins.
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} x
   * @param {number} y
   * @param {number} size
   * @param {string} factionId
   * @param {string} side
   * @param {Object} [options]
   */
  function drawCommanderPortrait(ctx, x, y, size, factionId, side, options) {
    if (!ctx) return;
    const opts = options || {};
    const normSide = normalizeSide(side);
    const normFac = normalizeFaction(factionId, normSide);
    const mood = opts.mood || opts.expression || (opts.isCheck ? 'CHECK' : 'NORMAL');
    const portraitSize = Math.max(24, Math.round(size || 48));

    const cvs = getOrBuildCommanderPortraitCanvas(normFac, normSide, mood);
    if (!cvs) return;

    // Determine whether (x, y) is top-left or center
    let drawX = x;
    let drawY = y;
    if (opts.centered === true) {
      drawX = Math.round(x - portraitSize / 2);
      drawY = Math.round(y - portraitSize / 2);
    } else if (opts.centered === false || opts.topLeft === true) {
      drawX = Math.round(x);
      drawY = Math.round(y);
    } else if (x >= portraitSize * 0.45 && y >= portraitSize * 0.45) {
      drawX = Math.round(x - portraitSize / 2);
      drawY = Math.round(y - portraitSize / 2);
    }

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    if (opts.alpha !== undefined) ctx.globalAlpha = opts.alpha;

    if (opts.flipX) {
      ctx.translate(drawX + portraitSize / 2, drawY + portraitSize / 2);
      ctx.scale(-1, 1);
      ctx.drawImage(cvs, -portraitSize / 2, -portraitSize / 2, portraitSize, portraitSize);
    } else {
      ctx.drawImage(cvs, drawX, drawY, portraitSize, portraitSize);
    }

    // Overlay 32-Bit HD Pixel Art Illustration Commander Bust if HDSpriteAtlas is loaded
    if (global.HDSpriteAtlas && global.HDSpriteAtlas.isReady(normFac)) {
      const atlasImg = global.HDSpriteAtlas.getImage(normFac);
      const cell = global.HDSpriteAtlas.getCellRect(opts.unitType || 'KING');
      const pad = Math.max(3, Math.round(portraitSize * 0.08));
      const innerW = portraitSize - pad * 2;
      const innerH = portraitSize - pad * 2;
      ctx.save();
      ctx.beginPath();
      ctx.rect(drawX + pad, drawY + pad, innerW, innerH);
      ctx.clip();
      ctx.fillStyle = normSide === 'CHU' ? '#091e26' : '#260b12';
      ctx.fillRect(drawX + pad, drawY + pad, innerW, innerH);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      // Crop upper head & torso bust of the HD Pixel Commander
      ctx.drawImage(
        atlasImg,
        cell.sx + Math.round(cell.sw * 0.12),
        cell.sy + Math.round(cell.sh * 0.02),
        Math.round(cell.sw * 0.76),
        Math.round(cell.sh * 0.62),
        drawX + pad,
        drawY + pad,
        innerW,
        innerH
      );
      ctx.restore();
    }
    ctx.restore();
  }

  /**
   * Renders a Super Robot Wars / Fire Emblem style Diagonal Pixel Art Battle Cut-In Banner!
   * @param {CanvasRenderingContext2D} ctx
   * @param {Object} duelInfo
   */
  function drawBattleCutIn(ctx, duelInfo) {
    if (!ctx || !duelInfo) return;
    const W = duelInfo.width || (ctx.canvas && ctx.canvas.width) || 960;
    const H = duelInfo.height || (ctx.canvas && ctx.canvas.height) || 720;

    const atk = duelInfo.attacker || duelInfo;
    const atkType = normalizePieceType(atk.type || duelInfo.type || 'KING');
    const atkSide = normalizeSide(atk.side || duelInfo.side || 'CHU');
    const atkFaction = normalizeFaction(atk.faction || duelInfo.faction, atkSide);
    const skin = FACTION_SKINS[atkFaction];
    const team = TEAM_THEMES[atkSide];
    const unitInfo = (skin.units && skin.units[atkType]) || { name: skin.commanderTitle };

    const rawP = duelInfo.cutInProgress !== undefined
      ? clamp(duelInfo.cutInProgress, 0, 1)
      : clamp(((duelInfo.progress !== undefined ? duelInfo.progress : 0.35) - 0.25) / 0.27, 0, 1);

    // Slide-in -> Hold -> Slide-out envelope
    let slideFactor = 1.0;
    if (rawP < 0.18) slideFactor = rawP / 0.18;
    else if (rawP > 0.85) slideFactor = (1 - rawP) / 0.15;
    slideFactor = clamp(slideFactor, 0, 1);
    if (slideFactor <= 0.01) return;

    const bannerW = Math.min(W * 0.86, 680);
    const bannerH = duelInfo.bannerHeight || 64;
    const cx = (duelInfo.x !== undefined ? duelInfo.x : W / 2) + Math.round((1 - slideFactor) * -140);
    const cy = duelInfo.y !== undefined ? duelInfo.y : Math.round(H * 0.22);
    const leftX = Math.round(cx - bannerW / 2);
    const topY = Math.round(cy - bannerH / 2);
    const slant = 22;

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.globalAlpha = clamp(slideFactor * 1.15, 0, 0.96);

    // 1. Slanted Parallelogram Cut-In Track with Gold & Neon Borders
    ctx.beginPath();
    ctx.moveTo(leftX + slant, topY);
    ctx.lineTo(leftX + bannerW, topY);
    ctx.lineTo(leftX + bannerW - slant, topY + bannerH);
    ctx.lineTo(leftX, topY + bannerH);
    ctx.closePath();
    ctx.fillStyle = '#070a14';
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = skin.palette.goldLight;
    ctx.stroke();

    ctx.save();
    ctx.clip();

    // 2. High-Speed Anime Pixel Speedlines inside Cut-In
    ctx.fillStyle = skin.palette.deepShadow || '#0f172a';
    ctx.fillRect(leftX, topY, bannerW, bannerH);
    for (let sy = topY + 4; sy < topY + bannerH - 4; sy += 6) {
      const lineLen = 90 + ((sy * 37) % 180);
      const lineX = leftX + ((sy * 53 + Math.floor((duelInfo.time || Date.now()) / 20) * 18) % Math.max(120, bannerW));
      ctx.fillStyle = (sy % 12 === 0) ? team.neon : skin.palette.armorSecDark;
      ctx.fillRect(lineX, sy, lineLen, 2);
    }

    // 3. Commander HD Pixel Portrait + Glowing Eye Glint Slash on Left
    const portSize = bannerH - 8;
    drawCommanderPortrait(ctx, leftX + slant + 6, topY + 4, portSize, atkFaction, atkSide, {
      topLeft: true,
      mood: 'ATTACK',
      unitType: atkType
    });

    // Eye-glint horizontal laser flare across portrait
    ctx.fillStyle = team.neonBright;
    ctx.fillRect(leftX + slant + 18, topY + Math.round(bannerH * 0.42), 54, 2);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(leftX + slant + 28, topY + Math.round(bannerH * 0.42) - 2, 6, 6);

    // 4. Action Unit Sprite Cut-In on Right Side of Banner
    if (global.HDSpriteAtlas && global.HDSpriteAtlas.isReady(atkFaction)) {
      const atlasImg = global.HDSpriteAtlas.getImage(atkFaction);
      const cell = global.HDSpriteAtlas.getCellRect(atkType);
      const uSize = Math.round(bannerH * 1.45);
      ctx.save();
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(
        atlasImg,
        cell.sx,
        cell.sy,
        cell.sw,
        cell.sh,
        Math.round(leftX + bannerW - slant - uSize - 6),
        Math.round(topY - bannerH * 0.25),
        uSize,
        uSize
      );
      ctx.restore();
    } else {
      const frameInfo = getSteppedFrameState(atkType, 'ATTACK', 0.5, duelInfo.time || Date.now());
      const unitCvs = getOrBuildUnitSpriteCanvas(atkType, atkSide, atkFaction, frameInfo, true, false);
      if (unitCvs) {
        const uSize = Math.round(bannerH * 1.35);
        ctx.drawImage(unitCvs, Math.round(leftX + bannerW - slant - uSize - 8), Math.round(topY - bannerH * 0.22), uSize, uSize);
      }
    }

    // 5. Cut-In Callout Typography
    const textX = leftX + slant + portSize + 18;
    ctx.font = '900 12px "Pretendard", "Noto Sans KR", monospace';
    ctx.textAlign = 'left';
    ctx.fillStyle = team.neonBright;
    ctx.fillText(`⚡ [${skin.shortName}] ${unitInfo.name}`, textX, topY + 23);

    const skillText = duelInfo.skillName || duelInfo.text || `필살 무장: ${unitInfo.weapon} 개방!!`;
    ctx.font = '900 16px "Noto Serif KR", "Malgun Gothic", monospace';
    ctx.fillStyle = '#070a14';
    ctx.fillText(skillText, textX + 2, topY + 48);
    ctx.fillStyle = '#fef08a';
    ctx.fillText(skillText, textX, topY + 46);

    ctx.restore();
    ctx.restore();
  }

  // ============================================================================
  // 8. MASTER PIXEL UNIT RENDERER (`ArtRenderer.drawUnit`)
  // ============================================================================

  function drawFrontPieceBadge(ctx, x, y, scale, side, rawType, type, factionKey, options) {
    const opts = options || {};
    const pMeta = PIECE_META[type] || PIECE_META.SOLDIER;
    const team = TEAM_THEMES[side] || TEAM_THEMES.CHU;
    const skin = FACTION_SKINS[factionKey] || FACTION_SKINS.GORYEO;

    let badgeChar = (pMeta.hanja && pMeta.hanja[side]) || pMeta.hanja.DEFAULT;
    if (opts.glyph) {
      badgeChar = opts.glyph;
    } else if ((opts.isChess || opts.gameMode === 'CHESS' || String(rawType).trim() === '♔') && pMeta.hanja.CHESS) {
      badgeChar = pMeta.hanja.CHESS;
    }

    const s = Math.max(0.75, scale || 1.0);
    const bw = Math.round(24 * s);
    const bh = Math.round(19 * s);
    const bx = Math.round(x - bw / 2);
    const by = Math.round(y + 4 * s);

    ctx.save();
    // Outer dark obsidian border
    ctx.fillStyle = '#05070e';
    ctx.fillRect(bx - 2, by - 2, bw + 4, bh + 4);
    // Gold bevel frame
    ctx.fillStyle = opts.isCheck ? '#ef4444' : (opts.isSelected ? '#fde047' : skin.palette.goldLight);
    ctx.fillRect(bx - 1, by - 1, bw + 2, bh + 2);
    // Inner dark faction plate
    ctx.fillStyle = side === 'CHU' ? '#062c24' : '#3b0a14';
    ctx.fillRect(bx + 1, by + 1, bw - 2, bh - 2);

    // High-contrast crisp Hanja / Chess symbol
    const fontPx = Math.max(11, Math.round(13.5 * s));
    ctx.font = `900 ${fontPx}px "Noto Serif KR", "Malgun Gothic", "Apple SD Gothic Neo", serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#000000';
    ctx.fillText(badgeChar, x + 1, by + bh / 2 + 1.5);
    ctx.fillStyle = side === 'CHU' ? '#6ee7b7' : '#fda4af';
    if (type === 'KING' || type === 'QUEEN') {
      ctx.fillStyle = '#fef08a';
    }
    ctx.fillText(badgeChar, x, by + bh / 2 + 0.5);
    ctx.restore();
  }

  function drawUnit(ctx, options) {
    if (!ctx || !options) return;
    const x = Math.round(options.x || 0);
    const y = Math.round(options.y || 0);
    const rawType = options.type || options.pieceType || options.role;
    const type = normalizePieceType(rawType);
    const side = normalizeSide(options.side || options.team || options.color);
    const factionKey = normalizeFaction(options.faction || options.skin, side);

    const pMeta = PIECE_META[type];
    const team = TEAM_THEMES[side];
    const skin = FACTION_SKINS[factionKey];

    const baseScale = (options.scale || 1.0) * pMeta.scaleMultiplier;
    const pedestalRadius = (options.pedestalRadius || 26) * (options.scale || 1.0);
    const facingDir = (options.facing === -1 || options.facing === 'LEFT') ? -1 : 1;
    const time = options.time !== undefined ? options.time : Date.now();
    const frameInfo = getSteppedFrameState(type, options.state, options.progress, time);

    ctx.save();
    ctx.imageSmoothingEnabled = false;

    // 1. Draw Pixelated Octagonal Janggi / Chess Pedestal
    if (options.showPedestal !== false) {
      drawBoardPedestal(ctx, x, y, pedestalRadius, side, rawType || type, factionKey, {
        time,
        isSelected: options.isSelected,
        isCheck: options.isCheck,
        isHighlighted: options.isHighlighted,
        isChess: options.isChess || options.gameMode === 'CHESS',
        glyph: options.glyph,
        unitStanding: true
      });
    }

    // 2. High-Density 76x76 Pixel Size Calculation (matched to original visual footprint)
    const pixelSize = Math.max(1.25, Math.round(baseScale * 1.38 * 4) / 4);
    const spriteW = Math.round(76 * pixelSize);
    const spriteH = Math.round(76 * pixelSize);

    // 3. Handle DEATH Pixel Shatter & 8-Bit Soul Ascension
    if (frameInfo.state === 'DEATH' && frameInfo.shatterProgress > 0) {
      const sp = frameInfo.shatterProgress;
      const blockPs = Math.max(3, Math.round(pixelSize * 2.2));
      for (let i = 0; i < 22; i++) {
        const seed = (i * 73) % 29;
        const vx = ((seed % 9) - 4) * 7.5 * sp * baseScale;
        const vy = -Math.sin(sp * Math.PI) * (15 + (seed % 12)) + sp * sp * 30 * baseScale;
        ctx.fillStyle = (i % 3 === 0) ? skin.palette.goldLight : ((i % 2 === 0) ? skin.palette.armorPrimary : team.neon);
        ctx.fillRect(
          Math.round(x + vx - blockPs / 2),
          Math.round(y - 16 * baseScale + vy),
          blockPs,
          blockPs
        );
      }
      const soulY = Math.round(y - 24 * baseScale - sp * 48 * baseScale);
      const sPs = Math.max(2, Math.round(pixelSize * 1.8));
      ctx.fillStyle = team.neon;
      ctx.fillRect(x - sPs * 2, soulY - sPs, sPs * 4, sPs * 3);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(x - sPs, soulY, sPs * 2, sPs * 2);
      ctx.restore();
      return;
    }

    // 4. Blit 32-Bit HD Pixel Art Illustration Sprite from HDSpriteAtlas (with HiDPI crisp sampling)
    if (global.HDSpriteAtlas && global.HDSpriteAtlas.isReady(factionKey)) {
      const atlasImg = global.HDSpriteAtlas.getImage(factionKey);
      const cell = global.HDSpriteAtlas.getCellRect(type);
      const hdSize = Math.round(92 * baseScale);
      const animDx = Math.round(frameInfo.shiftX * baseScale * 1.35);
      const animDy = Math.round((frameInfo.bobY + frameInfo.shiftY) * baseScale * 1.4);

      let stretchX = 1.0;
      let stretchY = 1.0;
      let tiltRad = 0;
      if (frameInfo.state === 'IDLE') {
        stretchY = (frameInfo.frameIdx % 2 === 1) ? 1.024 : 1.0;
        stretchX = (frameInfo.frameIdx % 2 === 1) ? 0.988 : 1.0;
      } else if (frameInfo.state === 'MOVE') {
        tiltRad = (frameInfo.frameIdx % 2 === 1) ? 0.06 : -0.03;
        stretchY = 1.03;
      } else if (frameInfo.state === 'ATTACK') {
        if (frameInfo.armPose === 'RAISED') {
          tiltRad = -0.10;
          stretchY = 1.05;
        } else if (frameInfo.armPose === 'STRIKE') {
          tiltRad = 0.12;
          stretchX = 1.08;
        }
      } else if (frameInfo.state === 'HIT') {
        tiltRad = -0.15;
      }

      ctx.save();
      ctx.translate(x + facingDir * animDx, Math.round(y - 2 * baseScale + animDy));
      ctx.scale(facingDir * stretchX, stretchY);
      if (tiltRad !== 0) ctx.rotate(tiltRad);
      // Enable high-quality downsampling so 240x240 HD Pixel Art retains 100% crisp outlines without nearest-neighbor decimation
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      // Strike speed-afterimage ghost
      if (frameInfo.state === 'ATTACK' && frameInfo.showSmear) {
        ctx.save();
        ctx.globalAlpha = 0.42;
        ctx.drawImage(
          atlasImg,
          cell.sx,
          cell.sy,
          cell.sw,
          cell.sh,
          Math.round(-hdSize / 2 - 10 * baseScale),
          Math.round(-hdSize * 0.86),
          hdSize,
          hdSize
        );
        ctx.restore();
      }

      // Main 32-Bit HD Pixel Art Sprite with crisp drop-shadow separation from board lines
      ctx.save();
      ctx.shadowColor = 'rgba(0, 0, 0, 0.85)';
      ctx.shadowBlur = Math.max(2, Math.round(4 * baseScale));
      ctx.shadowOffsetY = Math.max(1, Math.round(2 * baseScale));
      ctx.drawImage(
        atlasImg,
        cell.sx,
        cell.sy,
        cell.sw,
        cell.sh,
        Math.round(-hdSize / 2),
        Math.round(-hdSize * 0.86),
        hdSize,
        hdSize
      );
      ctx.restore();

      // Team Indicator Crest & Weapon Smear Arc on Strike
      if (frameInfo.showSmear) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = Math.max(2, Math.round(3 * baseScale));
        ctx.beginPath();
        ctx.arc(Math.round(hdSize * 0.12), Math.round(-hdSize * 0.45), Math.round(hdSize * 0.42), -0.8, 0.9);
        ctx.stroke();
        ctx.strokeStyle = skin.palette.fxPrimary || team.neonBright;
        ctx.lineWidth = Math.max(1, Math.round(2 * baseScale));
        ctx.beginPath();
        ctx.arc(Math.round(hdSize * 0.15), Math.round(-hdSize * 0.45), Math.round(hdSize * 0.46), -0.9, 1.0);
        ctx.stroke();
      }

      ctx.restore();

      // Draw unobstructed high-contrast front emblem plaque on pedestal rim
      if (options.showPedestal !== false) {
        drawFrontPieceBadge(ctx, x, y, options.scale || 1.0, side, rawType || type, type, factionKey, options);
      }
    } else {
      const spriteCanvas = getOrBuildUnitSpriteCanvas(
        type,
        side,
        factionKey,
        frameInfo,
        options.isSelected,
        options.isCheck
      );

      if (spriteCanvas) {
        ctx.save();
        ctx.translate(x, Math.round(y - 4 * baseScale));
        ctx.scale(facingDir, 1);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(
          spriteCanvas,
          Math.round(-spriteW / 2),
          Math.round(-spriteH * 0.84),
          spriteW,
          spriteH
        );
        ctx.restore();
      }
    }

    // 5. Stepped Pixel Attack Impact FX (King Lightning / Queen Seraphim Burst / Bishop Sacred Pillar / Rook Quake)
    if (frameInfo.state === 'ATTACK' && frameInfo.showSmear) {
      const fxX = Math.round(x + facingDir * 24 * baseScale);
      const fxY = Math.round(y - 10 * baseScale);
      const ps = Math.max(2, Math.round(pixelSize * 1.35));

      if (type === 'KING' || type === 'QUEEN') {
        ctx.fillStyle = type === 'QUEEN' ? skin.palette.fxPrimary : skin.palette.goldLight;
        ctx.fillRect(fxX - ps, fxY - ps * 18, ps * 3, ps * 20);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(fxX, fxY - ps * 18, ps, ps * 20);
      } else if (type === 'BISHOP') {
        ctx.fillStyle = skin.palette.fxPrimary;
        ctx.fillRect(fxX - ps * 2, fxY - ps * 14, ps * 4, ps * 16);
        ctx.fillStyle = '#fef08a';
        ctx.fillRect(fxX - ps, fxY - ps * 14, ps * 2, ps * 16);
      } else if (type === 'ROOK') {
        // Seismic Citadel Hammer Ground Spikes
        ctx.fillStyle = skin.palette.gold;
        ctx.fillRect(fxX - ps * 3, fxY - ps * 4, ps * 2, ps * 6);
        ctx.fillRect(fxX + ps * 2, fxY - ps * 7, ps * 2, ps * 9);
      }

      ctx.fillStyle = '#fde047';
      ctx.fillRect(fxX - ps * 4, fxY - ps, ps * 8, ps * 2);
      ctx.fillRect(fxX - ps, fxY - ps * 4, ps * 2, ps * 8);
    }

    // 6. Optional Retro Pixel Label
    if (options.showLabel) {
      const unitInfo = (skin.units && skin.units[type]) || { name: pMeta.korName[side] || pMeta.korName.DEFAULT };
      ctx.save();
      ctx.font = 'bold 11px "Pretendard", "Malgun Gothic", monospace';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#070a14';
      ctx.fillRect(Math.round(x - 58), Math.round(y + pedestalRadius * 0.72), 116, 16);
      ctx.strokeStyle = skin.palette.gold;
      ctx.lineWidth = 1;
      ctx.strokeRect(Math.round(x - 58), Math.round(y + pedestalRadius * 0.72), 116, 16);
      ctx.fillStyle = '#fef08a';
      ctx.fillText(unitInfo.name, x, Math.round(y + pedestalRadius * 0.72 + 12));
      ctx.restore();
    }

    ctx.restore();
  }

  function drawDuelUnit(ctx, options) {
    if (!options) return;
    drawUnit(ctx, {
      x: options.x || 0,
      y: options.y || 0,
      type: options.type,
      side: options.side,
      faction: options.faction,
      state: options.pose || options.state || 'IDLE',
      progress: options.progress || 0,
      time: options.time || Date.now(),
      scale: (options.scale || 1.0) * 1.4,
      facing: options.facing,
      showPedestal: true
    });
  }

  // ============================================================================
  // 9. PIXEL-ART BATTLE-CHESS DUEL STAGE (`ArtRenderer.drawBattleScene`)
  // ============================================================================

  function drawBattleScene(ctx, duel) {
    if (!ctx || !duel || !duel.attacker || !duel.defender) return;
    const W = duel.width || ctx.canvas.width || 960;
    const H = duel.height || ctx.canvas.height || 720;
    const p = clamp(duel.progress || 0, 0, 1);
    const now = duel.time || Date.now();

    const atkType = normalizePieceType(duel.attacker.type);
    const atkSide = normalizeSide(duel.attacker.side);
    const atkFaction = normalizeFaction(duel.attacker.faction, atkSide);
    const atkSkin = FACTION_SKINS[atkFaction];
    const atkTeam = TEAM_THEMES[atkSide];

    const defType = normalizePieceType(duel.defender.type);
    const defSide = normalizeSide(duel.defender.side);
    const defFaction = normalizeFaction(duel.defender.faction, defSide);
    const defSkin = FACTION_SKINS[defFaction];
    const defTeam = TEAM_THEMES[defSide];

    // Stepped Pixel Screen Shake during Impact (p between 0.46 and 0.70)
    let shakeX = 0;
    let shakeY = 0;
    if (p > 0.46 && p < 0.70) {
      const stepShake = (Math.floor(now / 35) % 2 === 0) ? 6 : -6;
      shakeX = stepShake;
      shakeY = (Math.floor(now / 50) % 2 === 0) ? 4 : -4;
    }

    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.translate(shakeX, shakeY);

    // 1. Dark Retro Arcade Backdrop
    ctx.fillStyle = 'rgba(6, 9, 18, 0.86)';
    ctx.fillRect(-16, -16, W + 32, H + 32);

    // 2. Pixel-Art Castle Cathedral Diorama Arena Frame
    const stageW = Math.floor(Math.min(W * 0.88, 760) / 4) * 4;
    const stageH = Math.floor(Math.min(H * 0.58, 380) / 4) * 4;
    const stageX = Math.floor((W - stageW) / 2);
    const stageY = Math.floor((H - stageH) / 2);

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(stageX, stageY, stageW, stageH);

    const brickW = 32;
    const brickH = 16;
    ctx.fillStyle = '#1e293b';
    for (let by = stageY + 8; by < stageY + stageH * 0.72; by += brickH) {
      const rowOffset = ((by / brickH) & 1) * (brickW / 2);
      for (let bx = stageX + 8 + rowOffset; bx < stageX + stageW - 24; bx += brickW) {
        ctx.fillRect(bx, by, brickW - 4, brickH - 4);
      }
    }

    // Dithered Stone Floor
    const floorY = Math.floor(stageY + stageH * 0.75);
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(stageX + 4, floorY, stageW - 8, stageY + stageH - floorY - 4);
    ctx.fillStyle = '#334155';
    for (let fx = stageX + 8; fx < stageX + stageW - 12; fx += 16) {
      ctx.fillRect(fx, floorY, 12, 4);
    }

    // Double Pixel Gold Frame Border
    ctx.strokeStyle = '#eab308';
    ctx.lineWidth = 4;
    ctx.strokeRect(stageX, stageY, stageW, stageH);
    ctx.strokeStyle = '#070a14';
    ctx.lineWidth = 2;
    ctx.strokeRect(stageX + 4, stageY + 4, stageW - 8, stageH - 8);

    // Faction Pixel Emblems on Wall
    drawFactionEmblem(ctx, stageX + stageW * 0.22, stageY + stageH * 0.42, 64, atkSkin.emblem, atkTeam.neon, 0.20);
    drawFactionEmblem(ctx, stageX + stageW * 0.78, stageY + stageH * 0.42, 64, defSkin.emblem, defTeam.neon, 0.20);

    // 3. Stepped Timeline Positions
    const startLeftX = Math.floor(stageX + stageW * 0.25);
    const rightDefX = Math.floor(stageX + stageW * 0.74);
    let atkX = startLeftX;
    let atkState = 'IDLE';
    let atkProgress = 0;
    let defState = 'IDLE';
    let defProgress = 0;
    const isRangedUnit = (atkType === 'CANNON' || atkType === 'BISHOP');

    if (p < 0.30) {
      const t1 = Math.floor((p / 0.30) * 8) / 8;
      atkState = isRangedUnit ? 'ATTACK' : 'MOVE';
      atkProgress = isRangedUnit ? t1 * 0.3 : t1;
      if (!isRangedUnit) {
        atkX = Math.floor(startLeftX + (rightDefX - 116 - startLeftX) * t1);
      }
    } else if (p < 0.66) {
      const t2 = (p - 0.30) / 0.36;
      atkX = isRangedUnit ? startLeftX : rightDefX - 116;
      atkState = 'ATTACK';
      atkProgress = isRangedUnit ? (0.3 + t2 * 0.65) : t2;
      if (t2 > 0.35) {
        defState = 'HIT';
        defProgress = (t2 - 0.35) / 0.65;
      }
    } else {
      const t3 = (p - 0.66) / 0.34;
      atkX = isRangedUnit ? startLeftX : rightDefX - 108;
      atkState = 'IDLE';
      defState = 'DEATH';
      defProgress = t3;
    }

    // 4. Render Pixel Defender & Attacker at Arena Scale
    drawUnit(ctx, {
      x: rightDefX,
      y: floorY + 12,
      type: defType,
      side: defSide,
      faction: defFaction,
      state: defState,
      progress: defProgress,
      time: now,
      scale: 2.2,
      facing: -1,
      showPedestal: true,
      showLabel: true
    });

    drawUnit(ctx, {
      x: atkX,
      y: floorY + 12,
      type: atkType,
      side: atkSide,
      faction: atkFaction,
      state: atkState,
      progress: atkProgress,
      time: now,
      scale: 2.3,
      facing: 1,
      showPedestal: true,
      showLabel: true
    });

    // 5. Stepped Pixel Projectile for CANNON / BISHOP
    if (isRangedUnit && p >= 0.25 && p <= 0.70) {
      const projT = Math.floor(clamp((p - 0.25) / 0.36, 0, 1) * 12) / 12;
      const px = Math.floor(startLeftX + 40 + (rightDefX - startLeftX - 40) * projT);
      const py = Math.floor(floorY - 48 - Math.sin(projT * Math.PI) * (atkType === 'BISHOP' ? 60 : 110));

      if (atkType === 'BISHOP') {
        ctx.fillStyle = atkSkin.palette.fxPrimary;
        ctx.fillRect(px - 12, py - 12, 24, 24);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(px - 6, py - 6, 12, 12);
      } else if (atkFaction === 'GORYEO') {
        for (let i = -2; i <= 2; i++) {
          const rx = px + i * 12;
          const ry = py + Math.abs(i) * 8;
          ctx.fillStyle = '#fde047';
          ctx.fillRect(rx - 12, ry - 2, 12, 4);
          ctx.fillStyle = '#ef4444';
          ctx.fillRect(rx, ry - 3, 6, 6);
        }
      } else {
        const orbCol = atkFaction === 'BYZANTINE' ? '#10b981' : '#f97316';
        ctx.fillStyle = orbCol;
        ctx.fillRect(px - 10, py - 10, 20, 20);
        ctx.fillStyle = '#fde047';
        ctx.fillRect(px - 6, py - 6, 12, 12);
      }
    }

    // 6. SRW / Fire Emblem Diagonal Battle Cut-In Banner during Strike Window (progress 0.25 ~ 0.52)
    if (p >= 0.25 && p <= 0.52) {
      drawBattleCutIn(ctx, {
        attacker: { type: atkType, side: atkSide, faction: atkFaction },
        defender: { type: defType, side: defSide, faction: defFaction },
        progress: p,
        cutInProgress: (p - 0.25) / 0.27,
        time: now,
        x: stageX + stageW / 2,
        y: stageY + 76,
        width: stageW,
        height: stageH,
        bannerHeight: 56
      });
    }

    // 7. Retro Arcade VS Header Banner
    ctx.fillStyle = '#070a14';
    ctx.fillRect(stageX + stageW / 2 - 220, stageY + 10, 440, 28);
    ctx.strokeStyle = '#eab308';
    ctx.lineWidth = 2;
    ctx.strokeRect(stageX + stageW / 2 - 220, stageY + 10, 440, 28);

    ctx.font = '900 15px "Noto Serif KR", "Malgun Gothic", monospace';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#fde047';
    const atkUnitName = atkSkin.units[atkType].name;
    const defUnitName = defSkin.units[defType].name;
    ctx.fillText(`⚔ ${atkUnitName}  VS  ${defUnitName} ⚔`, stageX + stageW / 2, stageY + 29);

    ctx.restore();
  }

  // ============================================================================
  // 10. PIXEL BOARD TACTICAL OVERLAYS (`ArtRenderer.drawTacticalIndicator`)
  // ============================================================================

  function drawTacticalIndicator(ctx, type, x, y, options) {
    const opts = options || {};
    const ix = Math.round(x);
    const iy = Math.round(y);
    const stepPulse = (Math.floor((opts.time || Date.now()) / 200) % 2) * 2;

    ctx.save();
    ctx.imageSmoothingEnabled = false;

    if (type === 'BLOCKED_MYEOK') {
      const s = 12 + stepPulse;
      ctx.fillStyle = '#070a14';
      ctx.fillRect(ix - s - 2, iy - s - 2, s * 2 + 4, s * 2 + 4);
      ctx.fillStyle = '#991b1b';
      ctx.fillRect(ix - s, iy - s, s * 2, s * 2);
      ctx.fillStyle = '#fca5a5';
      for (let d = -s + 3; d <= s - 3; d += 3) {
        ctx.fillRect(ix + d - 1, iy + d - 1, 3, 3);
        ctx.fillRect(ix + d - 1, iy - d - 1, 3, 3);
      }
    } else if (type === 'CANNON_BRIDGE') {
      const r = 24 + stepPulse;
      ctx.fillStyle = '#38bdf8';
      ctx.fillRect(ix - r, iy - r, 8, 3);
      ctx.fillRect(ix - r, iy - r, 3, 8);
      ctx.fillRect(ix + r - 8, iy - r, 8, 3);
      ctx.fillRect(ix + r - 3, iy - r, 3, 8);
      ctx.fillRect(ix - r, iy + r - 3, 8, 3);
      ctx.fillRect(ix - r, iy + r - 8, 3, 8);
      ctx.fillRect(ix + r - 8, iy + r - 3, 8, 3);
      ctx.fillRect(ix + r - 3, iy + r - 8, 3, 8);
    } else if (type === 'THREAT_LINE' && opts.toX !== undefined && opts.toY !== undefined) {
      const tx = Math.round(opts.toX);
      const ty = Math.round(opts.toY);
      const steps = 24;
      for (let i = 0; i <= steps; i++) {
        if ((i + stepPulse / 2) % 2 === 0) {
          const px = Math.round(ix + (tx - ix) * (i / steps));
          const py = Math.round(iy + (ty - iy) * (i / steps));
          ctx.fillStyle = '#070a14';
          ctx.fillRect(px - 3, py - 3, 6, 6);
          ctx.fillStyle = '#ef4444';
          ctx.fillRect(px - 2, py - 2, 4, 4);
        }
      }
    }

    ctx.restore();
  }

  // ============================================================================
  // 11. STATEFUL UNIT ANIMATOR & PUBLIC API EXPORT
  // ============================================================================

  function createUnitAnimator(config) {
    const cfg = Object.assign({
      type: 'SOLDIER',
      side: 'CHU',
      faction: 'GORYEO',
      state: 'IDLE',
      progress: 0,
      duration: 600,
      facing: 1,
      scale: 1.0
    }, config || {});

    return {
      config: cfg,
      setState(newState, durationMs) {
        cfg.state = String(newState || 'IDLE').toUpperCase();
        cfg.progress = 0;
        if (durationMs) cfg.duration = durationMs;
      },
      update(dtMs) {
        if (cfg.state !== 'IDLE') {
          cfg.progress = clamp(cfg.progress + (dtMs / (cfg.duration || 600)), 0, 1);
          if (cfg.progress >= 1 && (cfg.state === 'ATTACK' || cfg.state === 'HIT' || cfg.state === 'MOVE')) {
            cfg.state = 'IDLE';
            cfg.progress = 0;
          }
        }
      },
      draw(ctx, x, y, extraOptions) {
        drawUnit(ctx, Object.assign({}, cfg, extraOptions || {}, { x, y }));
      }
    };
  }

  const ArtRenderer = {
    version: '3.0.0-HD-PIXEL',
    isPixelArt: true,
    FACTION_SKINS,
    UNIT_ROSTER,
    PIECE_META,
    TEAM_THEMES,
    PIXEL_HANJA_FONT,
    normalizePieceType,
    normalizeType,
    normalizeSide,
    normalizeFaction,
    buildHueShiftedRamp,
    getFactionList() {
      return Object.keys(FACTION_SKINS).map((k) => ({
        id: k,
        name: FACTION_SKINS[k].name,
        shortName: FACTION_SKINS[k].shortName,
        commanderTitle: FACTION_SKINS[k].commanderTitle,
        subtitle: FACTION_SKINS[k].subtitle,
        palette: FACTION_SKINS[k].palette
      }));
    },
    getFactionConfig(factionId) {
      return FACTION_SKINS[normalizeFaction(factionId)] || FACTION_SKINS.GORYEO;
    },
    getUnitMeta(type, factionId, side) {
      const normType = normalizePieceType(type);
      const normSide = normalizeSide(side);
      const normFac = normalizeFaction(factionId, normSide);
      const skin = FACTION_SKINS[normFac];
      const pMeta = PIECE_META[normType] || PIECE_META.SOLDIER;
      const unitEntry = (skin.units && skin.units[normType]) || { name: pMeta.korName[normSide] || pMeta.korName.DEFAULT };
      return {
        ...pMeta,
        unitTitle: unitEntry.name,
        factionName: skin.shortName,
        hanjaChar: (pMeta.hanja && pMeta.hanja[normSide]) || pMeta.hanja.DEFAULT
      };
    },
    drawBoardPedestal,
    drawFactionEmblem,
    drawCommanderPortrait,
    drawBattleCutIn,
    drawUnit,
    drawDuelUnit,
    drawBattleScene,
    drawTacticalIndicator,
    createUnitAnimator
  };

  global.ArtRenderer = ArtRenderer;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = ArtRenderer;
  }
})(typeof window !== 'undefined' ? window : globalThis);
