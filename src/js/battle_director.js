/**
 * @fileoverview 16-BIT 레트로 칩튠/아케이드 사운드 합성기(window.SoundFX) 및
 *               도트 배틀체스 시네마틱 디렉터(window.BattleDirector)
 * @module window.BattleDirector, window.SoundFX
 *
 * 주요 기능:
 * 1. window.SoundFX (16-Bit Retro Chiptune + Arcade PCM Synth):
 *    - 사각파(Square)/삼각파(Triangle)/계단식 피치 아르페지오 및 비트크러시 노이즈 합성
 *    - 도트 커서음, 장기알 착수 스냅음, 16-bit 말발굽 질주, 코끼리 쿵쾅음,
 *      아케이드 검/창 크리티컬 타격음, 방패 파쇄음, 화포/신기전 8-bit/16-bit 발사 및 대폭발음,
 *      칩튠 브라스 장군(Check) 팡파르, 멍군 방패음, 레트로 아케이드 승리 팡파르
 * 2. window.BattleDirector (16-Bit Pixel SRPG Battle Duel Director):
 *    - 기물 포획 시 발동하는 '16-Bit 도트 배틀체스 시네마틱 전투 연출'
 *    - 'ARENA_OVERLAY' / 'BOARD_ZOOM' / 'FAST' 3가지 연출 모드 완벽 지원
 *    - ctx.imageSmoothingEnabled = false 강제, 12-FPS 스텝 프레임 양자화, 히트스톱(Hit-Stop),
 *      사각형 도트 파티클 폭발, 레트로 데미지 숫자 팝업("-999 CRITICAL!", "KO!!"),
 *      칸칸이 나뉜 아케이드 도트 체력 게이지
 */

(function (global) {
  'use strict';

  // ============================================================================
  // 1. 국가/진영 및 병종별 전투 로어 & 대사 레지스트리
  // ============================================================================

  const FACTION_COMBAT_LORE = Object.freeze({
    GORYEO: {
      id: 'GORYEO',
      name: '고려·조선 천군 (Celestial Dynasty)',
      shortName: '천군(고려·조선)',
      primaryColor: '#1e3a8a',
      accentColor: '#f5b700',
      secondaryColor: '#dc2626',
      arenaBgTop: '#0b1021',
      arenaBgBottom: '#172554',
      groundColor: '#1e293b',
      units: {
        KING: {
          title: '태조 대장군',
          weapon: '사인참사검(四寅斬邪劍)',
          hp: 999,
          atk: 250,
          cry: '천명을 받들어 불의를 베어라!',
          skillName: '제왕의 천벌 일섬'
        },
        QUEEN: {
          title: '천군 여제 무신',
          weapon: '일월쌍검(日月雙劍) & 봉황신궁',
          hp: 850,
          atk: 230,
          cry: '하늘의 봉황이여, 적진을 불살라라!',
          skillName: '봉황강림 일월검무'
        },
        ROOK: {
          title: '철갑 성루 거병',
          weapon: '현무 중장갑 & 파성 철퇴',
          hp: 620,
          atk: 190,
          cry: '강철 성벽이 전진한다! 모두 비켜라!',
          skillName: '현무 성벽 파쇄격'
        },
        BISHOP: {
          title: '왕실 태일 도술사',
          weapon: '태을 천문령 & 뇌화부',
          hp: 400,
          atk: 165,
          cry: '천문의 궤적을 따라 뇌화를 내려라!',
          skillName: '태일 천뢰 저격술'
        },
        KNIGHT: {
          title: '별무반 비호 철기병',
          weapon: '마상 철편곤 & 비호창',
          hp: 410,
          atk: 155,
          cry: '적의 머리 위를 뛰어넘어 급소를 쳐라!',
          skillName: '비호 공중 도약 강습'
        },
        PAWN: {
          title: '팽배 결사 창보병',
          weapon: '팽배 방패 & 장창',
          hp: 260,
          atk: 95,
          cry: '끝까지 전진하면 장수의 영예가 기다린다!',
          skillName: '팽배 전진 돌격'
        },
        CHARIOT: {
          title: '개마무사 중장돌격대',
          weapon: '5m 철갑 장창(槊) & 검차',
          hp: 650,
          atk: 195,
          cry: '철갑 기마대, 전속력 돌파하라!',
          skillName: '개마무사 파성 유린'
        },
        CANNON: {
          title: '문종 신기전 화차대',
          weapon: '대신기전 다연장 화차 & 총통',
          hp: 420,
          atk: 175,
          cry: '화차 방열 완료! 신기전 일제 점화!',
          skillName: '신기전 백발 화망 폭격'
        },
        HORSE: {
          title: '별무반 신기군',
          weapon: '마상편곤(Flail) & 환도',
          hp: 380,
          atk: 140,
          cry: '적의 측면을 파고들어 편곤으로 후려쳐라!',
          skillName: '신기군 날일자 기습 타격'
        },
        ELEPHANT: {
          title: '착호갑사 중장갑 코끼리',
          weapon: '강철 상아 & 거대 언월도',
          hp: 580,
          atk: 130,
          cry: '거대한 발걸음으로 적진을 짓뭉개라!',
          skillName: '태산압정(泰山壓頂) 짓밟기'
        },
        GUARD: {
          title: '내금위 금군 호위무사',
          weapon: '황금 협도(언월도) & 원방패',
          hp: 400,
          atk: 120,
          cry: '어전을 더럽히는 자, 살아서 돌아가지 못한다!',
          skillName: '금군 비연 일도양단'
        },
        SOLDIER: {
          title: '팽배수 장창 전열병',
          weapon: '팽배 대방패 & 장창',
          hp: 260,
          atk: 95,
          cry: '물러서지 마라! 방패를 세우고 찔러라!',
          skillName: '팽배 결사 돌격'
        }
      }
    },

    TEMPLAR: {
      id: 'TEMPLAR',
      name: '성전 기사단 (Royal Crusaders)',
      shortName: '성전 기사단',
      primaryColor: '#991b1b',
      accentColor: '#f5b700',
      secondaryColor: '#f8fafc',
      arenaBgTop: '#181115',
      arenaBgBottom: '#3b0a14',
      groundColor: '#292524',
      units: {
        KING: {
          title: '그랜드 마스터 사자심왕',
          weapon: '축성된 정의의 대검(Greatsword)',
          hp: 999,
          atk: 250,
          cry: '신의 뜻이 이곳에 있다! 성검의 심판을 받아라!',
          skillName: '성십자 심판의 대검'
        },
        QUEEN: {
          title: '성녀 아크엔젤 발키리',
          weapon: '성광의 쌍검 & 세라핌의 날개창',
          hp: 850,
          atk: 230,
          cry: '대천사의 날개 아래, 모든 악을 정화하리라!',
          skillName: '세라핌 성광 폭격검무'
        },
        ROOK: {
          title: '성채 골렘 시즈 타워',
          weapon: '움직이는 화강암 요새 & 거대 파성추',
          hp: 620,
          atk: 190,
          cry: '성전 기사단의 철벽 성채가 전열을 짓뭉갠다!',
          skillName: '시즈 타워 대지 분쇄'
        },
        BISHOP: {
          title: '대주교 인퀴지터 사제',
          weapon: '황금 성배 홀(Crozier) & 신벌의 성서',
          hp: 400,
          atk: 165,
          cry: '이단자들에게 하늘의 성스러운 징벌을 내려라!',
          skillName: '홀리 라이트 신벌 광선'
        },
        KNIGHT: {
          title: '페가수스 성전 중기병',
          weapon: '성기사의 은빛 랜스 & 날개 투구',
          hp: 410,
          atk: 155,
          cry: '전열을 뛰어넘어 적의 심장부에 성창을 꽂아라!',
          skillName: '페가수스 천공 도약 강습'
        },
        PAWN: {
          title: '크루세이더 성전 순례병',
          weapon: '십자가 카이트 실드 & 숏소드',
          hp: 260,
          atk: 95,
          cry: '성지를 향한 발걸음은 결코 멈추지 않는다!',
          skillName: '성전 순례자 결사 전진'
        },
        CHARIOT: {
          title: '그랜드 랜서 챔피언',
          weapon: '헤비 자우스팅 랜스 & 풀플레이트 마갑',
          hp: 650,
          atk: 195,
          cry: '랜스를 고정하라! 일직선으로 적진을 꿰뚫는다!',
          skillName: '쿠치드 랜스 풀차지(Full Charge)'
        },
        CANNON: {
          title: '로열 트레뷰셋 포병대',
          weapon: '거대 평형추 투석기 & 화염 사석포',
          hp: 420,
          atk: 175,
          cry: '방패벽 너머 목표 조준! 불타는 암석을 날려라!',
          skillName: '성벽 파괴 화염 투석'
        },
        HORSE: {
          title: '템플러 나이트 에란트',
          weapon: '크루세이더 브로드소드 & 카이트 실드',
          hp: 380,
          atk: 140,
          cry: '성전의 이름으로! 사각지대를 베어라!',
          skillName: '템플러 회전 기마 참격'
        },
        ELEPHANT: {
          title: '고딕 저거너트 워 엘리펀트',
          weapon: '공성 파성추 & 중장갑 코끼리',
          hp: 580,
          atk: 130,
          cry: '강철의 거수여, 이교도의 대열을 분쇄하라!',
          skillName: '고딕 베히모스 대지 강타'
        },
        GUARD: {
          title: '팔라딘 로열 가드',
          weapon: '타워 실드 & 축성된 할버드',
          hp: 400,
          atk: 120,
          cry: '주군을 수호하라! 방패로 쳐내고 할버드로 찍어라!',
          skillName: '팔라딘 카운터 처형'
        },
        SOLDIER: {
          title: '맨앳암즈 중보병',
          weapon: '히터 실드 & 브로드 스피어',
          hp: 260,
          atk: 95,
          cry: '대열을 유지하라! 방패로 밀어붙여라!',
          skillName: '실드 배시 & 스피어 스러스트'
        }
      }
    },

    BYZANTINE: {
      id: 'BYZANTINE',
      name: '비잔틴 제국군 (Golden Empire)',
      shortName: '비잔틴 제국',
      primaryColor: '#581c87',
      accentColor: '#f5b700',
      secondaryColor: '#a855f7',
      arenaBgTop: '#160d29',
      arenaBgBottom: '#3b0764',
      groundColor: '#2e1065',
      units: {
        KING: {
          title: '바실레우스 황제',
          weapon: '쌍두독수리 황금 홀 & 제국 보검',
          hp: 999,
          atk: 250,
          cry: '로마 제국의 영광 앞에 무릎을 꿇어라!',
          skillName: '임페리얼 퍼플 심판'
        },
        QUEEN: {
          title: '아우구스타 여제 테오도라',
          weapon: '자수정 제국 쌍검 & 오리할콘 마법보주',
          hp: 850,
          atk: 230,
          cry: '제국의 지혜와 분노로 적들을 재로 만들어라!',
          skillName: '아우구스타 황실 비전검무'
        },
        ROOK: {
          title: '테오도시우스 성벽 거병',
          weapon: '삼중 성벽 타워 실드 & 제국 파성퇴',
          hp: 620,
          atk: 190,
          cry: '난공불락의 성벽이 움직인다! 모두 파쇄하라!',
          skillName: '테오도시우스 성벽 압살'
        },
        BISHOP: {
          title: '콘스탄티노플 총대주교',
          weapon: '비잔틴 황금 성화상 & 성광 지팡이',
          hp: 400,
          atk: 165,
          cry: '하기아 소피아의 성스러운 빛이여, 적을 꿰뚫어라!',
          skillName: '총대주교 성광 대각 심판'
        },
        KNIGHT: {
          title: '스콜라이 황실 충격기병',
          weapon: '도금 기병창 & 비잔틴 철갑마',
          hp: 410,
          atk: 155,
          cry: '방패벽을 훌쩍 넘어 적의 후방을 유린하라!',
          skillName: '스콜라이 섬광 도약 베기'
        },
        PAWN: {
          title: '리미타네이 국경 수비병',
          weapon: '제국 둥근 방패 & 단창(Spiculum)',
          hp: 260,
          atk: 95,
          cry: '한 걸음씩 전진하여 제국의 영광을 되찾으리라!',
          skillName: '리미타네이 전열 돌파'
        },
        CHARIOT: {
          title: '클리바나리 카타프락토이',
          weapon: '황금 비늘갑옷 & 콘토스(Kontos) 장창',
          hp: 650,
          atk: 195,
          cry: '카타프락토이 쐐기 진형! 전열을 완벽히 분쇄하라!',
          skillName: '클리바나리 강철 쐐기 돌파'
        },
        CANNON: {
          title: '그리스의 불 사이펀 투사대',
          weapon: '청동 압축 사이펀 & 그리스의 불(Greek Fire)',
          hp: 420,
          atk: 175,
          cry: '압축 펌프 가동! 물로도 꺼지지 않는 지옥불을 퍼부어라!',
          skillName: '그리스의 불 폭염 세례'
        },
        HORSE: {
          title: '타그마타 프로노이아 기병',
          weapon: '스파시온 기병도 & 복합궁',
          hp: 380,
          atk: 140,
          cry: '제국의 기동대여, 날렵하게 목을 베어라!',
          skillName: '타그마타 섬광 기습'
        },
        ELEPHANT: {
          title: '임페리얼 워 엘리펀트',
          weapon: '비잔틴 황금 갑주 코끼리 & 망루 장창',
          hp: 580,
          atk: 130,
          cry: '제국의 거대한 위용으로 적을 짓밟아라!',
          skillName: '콘스탄티노플의 분노'
        },
        GUARD: {
          title: '바랑기안 가드',
          weapon: '양손 데인 액스(Dane Axe) & 노르만 실드',
          hp: 400,
          atk: 120,
          cry: '황제 폐하를 위하여! 투구째로 반으로 쪼개주마!',
          skillName: '바랑기안 데인액스 수직 처형'
        },
        SOLDIER: {
          title: '스쿠타토이 방패보병',
          weapon: '타원형 스쿠톤 방패 & 콘타리온 창',
          hp: 260,
          atk: 95,
          cry: '방패벽(Fulcum) 결성! 빈틈없이 찔러라!',
          skillName: '로마 군단 방패벽 연격'
        }
      }
    },

    MAMLUK: {
      id: 'MAMLUK',
      name: '맘루크 술탄국 (Mamluk Sultanate)',
      shortName: '맘루크 술탄국',
      primaryColor: '#065f46',
      accentColor: '#f5b700',
      secondaryColor: '#10b981',
      arenaBgTop: '#0c1917',
      arenaBgBottom: '#064e3b',
      groundColor: '#134e4a',
      units: {
        KING: {
          title: '위대한 술탄 살라딘',
          weapon: '다마스쿠스 보석 샴시르(Shamshir)',
          hp: 999,
          atk: 250,
          cry: '사막의 폭풍이여, 침략자들을 단숨에 베어 넘겨라!',
          skillName: '술탄의 초승달 비검'
        },
        QUEEN: {
          title: '사막의 여제 샤자르 알두르',
          weapon: '진주의 쌍곡도(Dual Scimitars) & 신기루 비수',
          hp: 850,
          atk: 230,
          cry: '찬란한 진주의 폭풍이여, 적진을 집어삼켜라!',
          skillName: '사막여제 신기루 초승달검무'
        },
        ROOK: {
          title: '카이로 알카히라 성탑병',
          weapon: '사암 요새 장갑 & 강철 파성 해머',
          hp: 620,
          atk: 190,
          cry: '카이로 성탑의 위용으로 적의 진형을 무너뜨려라!',
          skillName: '알카히라 성탑 대지분쇄'
        },
        BISHOP: {
          title: '알아즈하르 신비 학자',
          weapon: '별자리 아스트롤라베 & 사막 태양경',
          hp: 400,
          atk: 165,
          cry: '별들의 궤도가 가리키는 곳에 태양의 불꽃을 쏘아라!',
          skillName: '아스트롤라베 태양열선 저격'
        },
        KNIGHT: {
          title: '바흐리 아라비안 비마기병',
          weapon: '다마스쿠스 곡창 & 사막 질풍마',
          hp: 410,
          atk: 155,
          cry: '모래언덕을 뛰어넘는 바람처럼 적의 목을 쳐라!',
          skillName: '아라비안 질풍 공중 도약격'
        },
        PAWN: {
          title: '무타위아 성전 의용병',
          weapon: '사막 원형 방패 & 반월 단검',
          hp: 260,
          atk: 95,
          cry: '끝까지 전진하는 자에게 술탄의 축복이 내리리라!',
          skillName: '무타위아 열사의 전진'
        },
        CHARIOT: {
          title: '맘루크 로열 카스(Khass) 중장기병',
          weapon: '다마스쿠스 양날 장창 & 아라비안 중장갑마',
          hp: 650,
          atk: 195,
          cry: '아라비안 명마의 질주! 적의 심장을 관통하라!',
          skillName: '아인잘루트의 돌풍 돌격'
        },
        CANNON: {
          title: '만자니크 & 나프트 화염포병',
          weapon: '대형 만자니크 투석기 & 나프트(석유 화염탄)',
          hp: 420,
          atk: 175,
          cry: '나프트 화염탄 장전! 적의 머리 위에 불바다를 내려라!',
          skillName: '만자니크 나프트 화염 폭격'
        },
        HORSE: {
          title: '파리스(Faris) 사막 기병',
          weapon: '초승달 시미터(Scimitar) & 사막 복합궁',
          hp: 380,
          atk: 140,
          cry: '모래바람처럼 파고들어 시미터로 베어라!',
          skillName: '파리스 초승달 회전 베기'
        },
        ELEPHANT: {
          title: '사라센 워 엘리펀트',
          weapon: '강철 칼날 상아(Tusk Blades) 전투 코끼리',
          hp: 580,
          atk: 130,
          cry: '상아의 칼날로 적을 하늘 높이 띄워버려라!',
          skillName: '사라센 상아 격돌 & 짓밟기'
        },
        GUARD: {
          title: '할카(Halqa) 술탄 친위대',
          weapon: '다마스쿠스 쌍곡도(Dual Scimitars) & 미러 아머',
          hp: 400,
          atk: 120,
          cry: '술탄의 막사에 발을 들인 대가는 죽음뿐이다!',
          skillName: '할카 쌍검 폭풍 난무'
        },
        SOLDIER: {
          title: '가지(Ghazi) 창보병',
          weapon: '원형 철방패 & 하르바 단창/반월도',
          hp: 260,
          atk: 95,
          cry: '후퇴는 없다! 사막의 검으로 적을 처단하라!',
          skillName: '가지 모래폭풍 돌격'
        }
      }
    }
  });

  const SKIN_ALIASES = Object.freeze({
    GORYEO: 'GORYEO',
    JOSEON: 'GORYEO',
    CELESTIAL: 'GORYEO',
    KOREA: 'GORYEO',
    TEMPLAR: 'TEMPLAR',
    CRUSADER: 'TEMPLAR',
    CRUSADERS: 'TEMPLAR',
    KNIGHT: 'TEMPLAR',
    BYZANTINE: 'BYZANTINE',
    EMPIRE: 'BYZANTINE',
    ROME: 'BYZANTINE',
    MAMLUK: 'MAMLUK',
    SARACEN: 'MAMLUK',
    SULTANATE: 'MAMLUK'
  });

  function resolveFactionLore(skinKey, fallbackSide = 'CHU') {
    const normalized = SKIN_ALIASES[String(skinKey || '').toUpperCase()];
    if (normalized && FACTION_COMBAT_LORE[normalized]) {
      return FACTION_COMBAT_LORE[normalized];
    }
    return fallbackSide === 'CHU' ? FACTION_COMBAT_LORE.GORYEO : FACTION_COMBAT_LORE.TEMPLAR;
  }

  // ============================================================================
  // 2. 16-BIT 레트로 칩튠 & 아케이드 PCM 사운드 엔진 (window.SoundFX)
  // ============================================================================

  class SoundFXEngine {
    constructor() {
      this.ctx = null;
      this.enabled = true;
      this.masterVolume = 0.75;
      this.bgmVolume = 0.55;
      this.sfxVolume = 0.85;
      this.battleVolume = 0.90;
      this.bgmTrack = 'GORYEO_MARCH'; // 'OFF' | 'GORYEO_MARCH' | 'CRUSADER_HYMN' | 'TACTICAL_TENSION'
      this._bgmTimer = null;
      this._bgmStep = 0;
      this._bgmPlaying = false;
      this._noiseBuffer = null;
    }

    _ensureContext() {
      if (!this.enabled) return null;
      if (!this.ctx) {
        const AudioCtx = global.AudioContext || global.webkitAudioContext;
        if (!AudioCtx) return null;
        this.ctx = new AudioCtx();
      }
      if (this.ctx.state === 'suspended') {
        this.ctx.resume().catch(() => {});
      }
      if (!this._noiseBuffer && this.ctx) {
        // 8-bit/16-bit LFSR 느낌의 계단식 비트크러시 노이즈 버퍼 생성
        const sampleRate = this.ctx.sampleRate;
        const length = sampleRate * 1.5;
        const buffer = this.ctx.createBuffer(1, length, sampleRate);
        const data = buffer.getChannelData(0);
        let held = 0;
        for (let i = 0; i < length; i++) {
          if (i % 6 === 0) {
            held = Math.round((Math.random() * 2 - 1) * 8) / 8;
          }
          data[i] = held;
        }
        this._noiseBuffer = buffer;
      }
      return this.ctx;
    }

    setEnabled(flag) {
      this.enabled = Boolean(flag);
      if (!this.enabled) {
        this.stopBGM();
      } else if (this.bgmTrack !== 'OFF') {
        this.startBGM(this.bgmTrack);
      }
      return this.enabled;
    }

    toggleMute() {
      return this.setEnabled(!this.enabled);
    }

    setVolume(vol) {
      this.masterVolume = Math.max(0, Math.min(1, Number(vol)));
    }

    setSfxVolume(vol) {
      this.sfxVolume = Math.max(0, Math.min(1, Number(vol)));
    }

    setBattleVolume(vol) {
      this.battleVolume = Math.max(0, Math.min(1, Number(vol)));
    }

    setBgmVolume(vol) {
      this.bgmVolume = Math.max(0, Math.min(1, Number(vol)));
    }

    get _effSfx() {
      return this.masterVolume * this.sfxVolume;
    }

    get _effBattle() {
      return this.masterVolume * this.battleVolume;
    }

    get _effBgm() {
      return this.masterVolume * this.bgmVolume;
    }

    /**
     * 16-Bit 중세 칩튠 배경음악(BGM) 시퀀서 시작/변경
     */
    startBGM(trackName = this.bgmTrack) {
      this.bgmTrack = trackName;
      if (this._bgmTimer) {
        clearInterval(this._bgmTimer);
        this._bgmTimer = null;
      }
      if (!this.enabled || this.bgmTrack === 'OFF') {
        this._bgmPlaying = false;
        return;
      }

      const tracks = {
        // 고려 천군의 행군 (오음계 국악 펜타토닉 16-bit 행진곡: D - F - G - A - C)
        GORYEO_MARCH: {
          tempoMs: 220,
          lead: [293.66, 0, 349.23, 392.00, 440.00, 0, 523.25, 440.00, 392.00, 349.23, 293.66, 0, 349.23, 293.66, 261.63, 293.66],
          bass: [146.83, 146.83, 174.61, 196.00, 220.00, 220.00, 196.00, 174.61, 146.83, 146.83, 130.81, 130.81, 146.83, 110.00, 130.81, 146.83]
        },
        // 성전 기사단의 진격 (고딕 단조 오르간 아르페지오)
        CRUSADER_HYMN: {
          tempoMs: 210,
          lead: [329.63, 392.00, 493.88, 659.25, 587.33, 493.88, 392.00, 493.88, 349.23, 440.00, 523.25, 440.00, 329.63, 311.13, 329.63, 0],
          bass: [164.81, 164.81, 196.00, 196.00, 146.83, 146.83, 196.00, 196.00, 174.61, 174.61, 130.81, 130.81, 164.81, 123.47, 164.81, 164.81]
        },
        // 왕실 전략 작전실 (SRPG 전술 텐션 테마)
        TACTICAL_TENSION: {
          tempoMs: 250,
          lead: [220.00, 0, 261.63, 0, 293.66, 329.63, 261.63, 0, 196.00, 0, 246.94, 0, 220.00, 0, 164.81, 0],
          bass: [110.00, 110.00, 110.00, 130.81, 146.83, 146.83, 130.81, 110.00, 98.00, 98.00, 123.47, 123.47, 110.00, 82.41, 110.00, 110.00]
        }
      };

      const seq = tracks[this.bgmTrack] || tracks.GORYEO_MARCH;
      this._bgmStep = 0;
      this._bgmPlaying = true;

      this._bgmTimer = setInterval(() => {
        if (!this.enabled || this.bgmTrack === 'OFF' || this._effBgm <= 0.005) return;
        const ctx = this._ensureContext();
        if (!ctx || ctx.state !== 'running') return;

        const idx = this._bgmStep % seq.lead.length;
        const leadFreq = seq.lead[idx];
        const bassFreq = seq.bass[idx];
        const now = ctx.currentTime;
        const vol = this._effBgm;

        if (leadFreq > 0) {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = 'square';
          osc.frequency.setValueAtTime(leadFreq, now);
          gain.gain.setValueAtTime(0.055 * vol, now);
          gain.gain.exponentialRampToValueAtTime(0.0008, now + (seq.tempoMs * 0.85) / 1000);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(now);
          osc.stop(now + (seq.tempoMs * 0.9) / 1000);
        }

        if (bassFreq > 0) {
          const bOsc = ctx.createOscillator();
          const bGain = ctx.createGain();
          bOsc.type = 'triangle';
          bOsc.frequency.setValueAtTime(bassFreq, now);
          bGain.gain.setValueAtTime(0.08 * vol, now);
          bGain.gain.exponentialRampToValueAtTime(0.001, now + (seq.tempoMs * 0.9) / 1000);
          bOsc.connect(bGain);
          bGain.connect(ctx.destination);
          bOsc.start(now);
          bOsc.stop(now + (seq.tempoMs * 0.95) / 1000);
        }

        this._bgmStep++;
      }, seq.tempoMs);
    }

    stopBGM() {
      if (this._bgmTimer) {
        clearInterval(this._bgmTimer);
        this._bgmTimer = null;
      }
      this._bgmPlaying = false;
    }

    /**
     * 16-bit RPG 도트 커서/기물 선택음 (2-step Square Blip)
     */
    playSelect() {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.setValueAtTime(660, now);
      osc.frequency.setValueAtTime(990, now + 0.032);

      gain.gain.setValueAtTime(0.16 * this._effSfx, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.075);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.08);
    }

    /**
     * 도트 장기알 착수 스냅음 (16-bit Punchy Wood/Stone Impact)
     */
    playWoodSnap(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(380, now);
      osc.frequency.setValueAtTime(210, now + 0.02);
      osc.frequency.setValueAtTime(95, now + 0.045);

      gain.gain.setValueAtTime(0.5 * this._effSfx, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.085);

      if (this._noiseBuffer) {
        const noise = ctx.createBufferSource();
        noise.buffer = this._noiseBuffer;
        const filter = ctx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(1400, now);
        filter.Q.setValueAtTime(2.5, now);

        const nGain = ctx.createGain();
        nGain.gain.setValueAtTime(0.32 * this._effSfx, now);
        nGain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);

        noise.connect(filter);
        filter.connect(nGain);
        nGain.connect(ctx.destination);
        noise.start(now);
        noise.stop(now + 0.04);
      }
    }

    /**
     * 16-bit 말발굽 질주음
     */
    playHorseGallop(steps = 3) {
      const ctx = this._ensureContext();
      if (!ctx || !this._noiseBuffer) return;

      for (let i = 0; i < steps; i++) {
        const offset = i * 0.07;
        const now = ctx.currentTime + offset;
        const noise = ctx.createBufferSource();
        noise.buffer = this._noiseBuffer;

        const filter = ctx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(i % 2 === 0 ? 820 : 620, now);
        filter.Q.setValueAtTime(3.5, now);

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(0.28 * this._effSfx, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);
        noise.start(now);
        noise.stop(now + 0.055);
      }
    }

    /**
     * 16-bit 코끼리/공성거수 대지 강타음
     */
    playElephantStomp(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.setValueAtTime(130, now);
      osc.frequency.setValueAtTime(85, now + 0.06);
      osc.frequency.setValueAtTime(42, now + 0.14);

      gain.gain.setValueAtTime(0.45 * this._effBattle, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.34);

      if (this._noiseBuffer) {
        const noise = ctx.createBufferSource();
        noise.buffer = this._noiseBuffer;
        const filter = ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(320, now);

        const nGain = ctx.createGain();
        nGain.gain.setValueAtTime(0.42 * this._effBattle, now);
        nGain.gain.exponentialRampToValueAtTime(0.001, now + 0.24);

        noise.connect(filter);
        filter.connect(nGain);
        nGain.connect(ctx.destination);
        noise.start(now);
        noise.stop(now + 0.26);
      }
    }

    /**
     * 병종별 일반 착수/행군 사운드 통합 재생
     */
    playMove(pieceType = 'SOLDIER') {
      this.playWoodSnap(0);
      switch (pieceType) {
        case 'HORSE':
        case 'KNIGHT':
          this.playHorseGallop(3);
          break;
        case 'CHARIOT':
          this.playHorseGallop(4);
          this.playSwordClash(0.07);
          break;
        case 'ROOK':
          this.playElephantStomp(0.03);
          this.playShieldBash(0.05);
          break;
        case 'ELEPHANT':
          this.playElephantStomp(0.04);
          break;
        case 'CANNON':
          this.playShieldBash(0.04);
          break;
        case 'QUEEN':
          this.playSelect();
          this.playSwordClash(0.05);
          break;
        case 'BISHOP':
          this.playSelect();
          break;
        default:
          break;
      }
    }

    /**
     * 폰(PAWN) 승진(Promotion) 16-Bit 황금 각성 아르페지오 & 성스러운 벨 팡파르
     */
    playPromotionFanfare(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const baseNow = ctx.currentTime + delay;

      // 1. 16-Bit 황금 각성 상승 아르페지오 (C5 - E5 - G5 - B5 - C6 - E6 - G6 - C7)
      const arpNotes = [
        { f: 523.25, t: 0.00, d: 0.09 },
        { f: 659.25, t: 0.06, d: 0.09 },
        { f: 783.99, t: 0.12, d: 0.09 },
        { f: 987.77, t: 0.18, d: 0.09 },
        { f: 1046.50, t: 0.24, d: 0.12 },
        { f: 1318.51, t: 0.31, d: 0.12 },
        { f: 1567.98, t: 0.38, d: 0.16 },
        { f: 2093.00, t: 0.46, d: 0.48 }
      ];

      arpNotes.forEach((n) => {
        const now = baseNow + n.t;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'square';
        osc.frequency.setValueAtTime(n.f, now);

        gain.gain.setValueAtTime(0.20 * this._effBattle, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + n.d);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + n.d + 0.02);
      });

      // 2. 성스러운 벨(Sacred Chime Bell) 배음 화음 (Triangle + Sine)
      const bellChord = [
        { f: 1046.50, t: 0.46, d: 0.65 },
        { f: 1318.51, t: 0.48, d: 0.65 },
        { f: 1567.98, t: 0.50, d: 0.70 },
        { f: 2637.02, t: 0.52, d: 0.55 }
      ];

      bellChord.forEach((b, idx) => {
        const now = baseNow + b.t;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = idx % 2 === 0 ? 'triangle' : 'sine';
        osc.frequency.setValueAtTime(b.f, now);

        gain.gain.setValueAtTime(0.24 * this._effBattle, now);
        gain.gain.exponentialRampToValueAtTime(0.0008, now + b.d);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + b.d + 0.03);
      });
    }

    /**
     * 캐슬링(Castling) 성문 개방 & 킹·룩 교차 중후한 석재 슬라이드 + 철갑 착수음
     */
    playCastlingSlide(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      // 1. 중후한 성문/석재 슬라이드 저음 럼블
      const stoneOsc = ctx.createOscillator();
      const stoneGain = ctx.createGain();
      stoneOsc.type = 'triangle';
      stoneOsc.frequency.setValueAtTime(115, now);
      stoneOsc.frequency.linearRampToValueAtTime(82, now + 0.16);
      stoneOsc.frequency.linearRampToValueAtTime(104, now + 0.30);

      stoneGain.gain.setValueAtTime(0.42 * this._effSfx, now);
      stoneGain.gain.exponentialRampToValueAtTime(0.001, now + 0.34);

      stoneOsc.connect(stoneGain);
      stoneGain.connect(ctx.destination);
      stoneOsc.start(now);
      stoneOsc.stop(now + 0.36);

      // 2. 석재 마찰 노이즈 스윕
      if (this._noiseBuffer) {
        const noise = ctx.createBufferSource();
        noise.buffer = this._noiseBuffer;
        const filter = ctx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.setValueAtTime(520, now);
        filter.frequency.linearRampToValueAtTime(980, now + 0.16);
        filter.frequency.linearRampToValueAtTime(460, now + 0.30);
        filter.Q.setValueAtTime(2.8, now);

        const nGain = ctx.createGain();
        nGain.gain.setValueAtTime(0.32 * this._effSfx, now);
        nGain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);

        noise.connect(filter);
        filter.connect(nGain);
        nGain.connect(ctx.destination);
        noise.start(now);
        noise.stop(now + 0.33);
      }

      // 3. 킹 & 룩 연속 철갑 착수 스냅음
      this.playWoodSnap(delay + 0.14);
      this.playShieldBash(delay + 0.16);
      this.playWoodSnap(delay + 0.28);
      this.playSwordClash(delay + 0.30);
    }

    /**
     * 퀸(QUEEN) / 비숍(BISHOP) 공격 시 비전 마법 충전음 + 다중 검기 슬래시 사운드
     */
    playQueenMagicSlash(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      // 1. 비전 마법 충전(Arcane Charge) 고속 크리스탈 스윕
      const magicFreqs = [440, 587.33, 783.99, 1046.50, 1396.91, 1760, 2349.32, 2960];
      const chargeOsc = ctx.createOscillator();
      const chargeGain = ctx.createGain();
      chargeOsc.type = 'square';
      magicFreqs.forEach((f, idx) => {
        chargeOsc.frequency.setValueAtTime(f, now + idx * 0.02);
      });

      chargeGain.gain.setValueAtTime(0.22 * this._effBattle, now);
      chargeGain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

      chargeOsc.connect(chargeGain);
      chargeGain.connect(ctx.destination);
      chargeOsc.start(now);
      chargeOsc.stop(now + 0.23);

      // 2. 성광 공명(Sub-Harmonic Beam)
      const beamOsc = ctx.createOscillator();
      const beamGain = ctx.createGain();
      beamOsc.type = 'sawtooth';
      beamOsc.frequency.setValueAtTime(880, now + 0.12);
      beamOsc.frequency.exponentialRampToValueAtTime(220, now + 0.36);

      beamGain.gain.setValueAtTime(0.26 * this._effBattle, now + 0.12);
      beamGain.gain.exponentialRampToValueAtTime(0.001, now + 0.38);

      beamOsc.connect(beamGain);
      beamGain.connect(ctx.destination);
      beamOsc.start(now + 0.12);
      beamOsc.stop(now + 0.39);

      // 3. 다중 검기 슬래시(Triple Arcane Blade Slash)
      this.playSwordClash(delay + 0.10);
      this.playSwordClash(delay + 0.18);
      this.playSwordClash(delay + 0.26);
    }

    /**
     * 아케이드 도트 검/창 금속 격돌음 (16-bit Metallic Arpeggio + Noise Slash)
     */
    playSwordClash(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      const arp = [1480, 2217, 1760, 2960];
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      arp.forEach((f, idx) => {
        osc.frequency.setValueAtTime(f, now + idx * 0.022);
      });

      gain.gain.setValueAtTime(0.24 * this._effBattle, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.17);

      if (this._noiseBuffer) {
        const noise = ctx.createBufferSource();
        noise.buffer = this._noiseBuffer;
        const filter = ctx.createBiquadFilter();
        filter.type = 'highpass';
        filter.frequency.setValueAtTime(1800, now);

        const nGain = ctx.createGain();
        nGain.gain.setValueAtTime(0.34 * this._effBattle, now);
        nGain.gain.exponentialRampToValueAtTime(0.001, now + 0.11);

        noise.connect(filter);
        filter.connect(nGain);
        nGain.connect(ctx.destination);
        noise.start(now);
        noise.stop(now + 0.12);
      }
    }

    /**
     * 아케이드 방패 강타 / 갑옷 파쇄음
     */
    playShieldBash(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(260, now);
      osc.frequency.setValueAtTime(140, now + 0.04);
      osc.frequency.setValueAtTime(65, now + 0.09);

      gain.gain.setValueAtTime(0.45 * this._effBattle, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.17);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.18);
    }

    /**
     * 결정타 크리티컬 처형 참격음 (16-Bit Critical Hit Finisher)
     */
    playHeavySlash(delay = 0) {
      this.playSwordClash(delay);
      this.playShieldBash(delay + 0.02);
      this.playElephantStomp(delay + 0.04);
    }

    /**
     * 16-bit 화포/신기전 발사 및 착탄 폭발음
     */
    playCannonFire(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      // 계단식 하강 휘슬음
      const whistle = ctx.createOscillator();
      const wGain = ctx.createGain();
      whistle.type = 'square';
      const steps = 8;
      for (let i = 0; i < steps; i++) {
        whistle.frequency.setValueAtTime(920 - i * 85, now + i * 0.03);
      }

      wGain.gain.setValueAtTime(0.18 * this._effBattle, now);
      wGain.gain.exponentialRampToValueAtTime(0.001, now + 0.26);

      whistle.connect(wGain);
      wGain.connect(ctx.destination);
      whistle.start(now);
      whistle.stop(now + 0.27);

      this.playExplosion(delay + 0.23);
    }

    /**
     * 8-bit/16-bit 도트 화약 대폭발음
     */
    playExplosion(delay = 0) {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime + delay;

      const sub = ctx.createOscillator();
      const sGain = ctx.createGain();
      sub.type = 'triangle';
      sub.frequency.setValueAtTime(140, now);
      sub.frequency.setValueAtTime(75, now + 0.08);
      sub.frequency.setValueAtTime(36, now + 0.2);

      sGain.gain.setValueAtTime(0.62 * this._effBattle, now);
      sGain.gain.exponentialRampToValueAtTime(0.001, now + 0.48);

      sub.connect(sGain);
      sGain.connect(ctx.destination);
      sub.start(now);
      sub.stop(now + 0.5);

      if (this._noiseBuffer) {
        const noise = ctx.createBufferSource();
        noise.buffer = this._noiseBuffer;
        const filter = ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(1100, now);
        filter.frequency.setValueAtTime(420, now + 0.18);
        filter.frequency.setValueAtTime(160, now + 0.35);

        const nGain = ctx.createGain();
        nGain.gain.setValueAtTime(0.58 * this._effBattle, now);
        nGain.gain.exponentialRampToValueAtTime(0.001, now + 0.48);

        noise.connect(filter);
        filter.connect(nGain);
        nGain.connect(ctx.destination);
        noise.start(now);
        noise.stop(now + 0.5);
      }
    }

    /**
     * 장군(Check)! 16-bit 칩튠 브라스 경보 팡파르
     */
    playCheckHorn() {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime;

      const notes = [
        { f: 220, t: 0.0, d: 0.09 },
        { f: 330, t: 0.09, d: 0.09 },
        { f: 440, t: 0.18, d: 0.35 }
      ];
      notes.forEach((n) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'square';
        osc.frequency.setValueAtTime(n.f, now + n.t);

        gain.gain.setValueAtTime(0.22 * this._effBattle, now + n.t);
        gain.gain.exponentialRampToValueAtTime(0.001, now + n.t + n.d);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + n.t);
        osc.stop(now + n.t + n.d + 0.01);
      });

      this.playElephantStomp(0);
    }

    /**
     * 멍군! 방패 패링 사운드
     */
    playMeonggunShield() {
      this.playShieldBash(0);
      this.playSwordClash(0.04);
    }

    /**
     * 외통수 / 승리! 16-bit 아케이드 클리어 팡파르
     */
    playVictoryFanfare() {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const notes = [
        { f: 261.63, t: 0.0, d: 0.12 },
        { f: 329.63, t: 0.12, d: 0.12 },
        { f: 392.00, t: 0.24, d: 0.12 },
        { f: 523.25, t: 0.36, d: 0.18 },
        { f: 392.00, t: 0.54, d: 0.12 },
        { f: 523.25, t: 0.66, d: 0.45 }
      ];
      notes.forEach((n) => {
        const now = ctx.currentTime + n.t;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'square';
        osc.frequency.setValueAtTime(n.f, now);

        gain.gain.setValueAtTime(0.24 * this._effSfx, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + n.d);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + n.d + 0.02);
      });
    }

    /**
     * 멱 막힘 / 착수 불가 8-bit 버저음
     */
    playBlocked() {
      const ctx = this._ensureContext();
      if (!ctx) return;
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(140, now);
      osc.frequency.setValueAtTime(98, now + 0.06);

      gain.gain.setValueAtTime(0.25 * this._effSfx, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.15);
    }
  }

  const SoundFX = new SoundFXEngine();

  // ============================================================================
  // 3. 16-BIT 도트 배틀체스 시네마틱 디렉터 (window.BattleDirector)
  // ============================================================================

  class BattleDirectorController {
    constructor() {
      this.mode = 'BOARD_ZOOM';
      this.isPlaying = false;
      this._skipRequested = false;
      this._overlayEl = null;
      this._arenaCanvas = null;
      this._arenaCtx = null;
      this._bannerEl = null;

      this.boardCamera = {
        active: false,
        focusX: 0,
        focusY: 0,
        zoom: 1.0,
        shakeX: 0,
        shakeY: 0,
        progress: 0
      };
      this.boardDuel = null;
      this.boardEffects = [];
    }

    setMode(modeKey) {
      const m = String(modeKey || 'BOARD_ZOOM').toUpperCase();
      if (m.includes('BOARD') || m.includes('ZOOM') || m.includes('IMPACT')) {
        this.mode = 'BOARD_ZOOM';
      } else if (m.includes('FAST') || m.includes('INSTANT') || m.includes('OFF')) {
        this.mode = 'FAST';
      } else {
        this.mode = 'ARENA_OVERLAY';
      }
      return this.mode;
    }

    getMode() {
      return this.mode;
    }

    skip() {
      if (this.isPlaying) {
        this._skipRequested = true;
      }
    }

    /**
     * 16-BIT 도트 아케이드 결투장 DOM 오버레이 및 전술 배너 생성
     */
    _ensureArenaDOM() {
      if (typeof document === 'undefined') return;
      if (this._overlayEl && document.body.contains(this._overlayEl)) return;

      if (!document.getElementById('battle-director-styles')) {
        const style = document.createElement('style');
        style.id = 'battle-director-styles';
        style.textContent = `
          .bd-arena-backdrop {
            position: fixed;
            inset: 0;
            z-index: 9500;
            background: rgba(6, 8, 15, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            pointer-events: none;
            font-family: 'DungGeunMo', 'DotGothic16', monospace;
          }
          .bd-arena-backdrop.bd-active {
            opacity: 1;
            pointer-events: auto;
          }
          .bd-arena-card {
            width: min(880px, 95vw);
            background: #111625;
            border: 4px solid #000000;
            box-shadow:
              inset 0 0 0 4px #f5b700,
              inset 0 0 0 8px #090c15,
              12px 12px 0 #000000;
            overflow: hidden;
            position: relative;
          }
          .bd-arena-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 18px;
            background: #090c15;
            border-bottom: 4px solid #f5b700;
          }
          .bd-combatant-info {
            display: flex;
            flex-direction: column;
            gap: 5px;
            width: 39%;
          }
          .bd-combatant-info.bd-right {
            align-items: flex-end;
            text-align: right;
          }
          .bd-faction-tag {
            font-size: 11.5px;
            color: #fff05a;
            text-shadow: 2px 2px 0 #000000;
          }
          .bd-unit-title {
            font-size: 16px;
            color: #ffffff;
            text-shadow: 2px 2px 0 #000000;
          }
          .bd-hp-bar-wrap {
            width: 100%;
            height: 16px;
            background: #1e293b;
            border: 3px solid #000000;
            box-shadow: 2px 2px 0 #000000;
            position: relative;
            overflow: hidden;
          }
          .bd-hp-bar-wrap::after {
            content: "";
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(
              90deg,
              transparent 0px,
              transparent 10px,
              rgba(0, 0, 0, 0.65) 10px,
              rgba(0, 0, 0, 0.65) 12px
            );
            pointer-events: none;
          }
          .bd-hp-bar-fill {
            height: 100%;
            width: 100%;
            transition: width 0.1s steps(5);
          }
          .bd-vs-badge {
            font-family: 'Silkscreen', 'DungGeunMo', monospace;
            font-size: 15px;
            color: #000000;
            padding: 6px 12px;
            background: #f5b700;
            border: 3px solid #000000;
            box-shadow:
              inset -2px -2px 0 #8c5a08,
              inset 2px 2px 0 #fff05a,
              3px 3px 0 #000000;
          }
          .bd-arena-canvas-wrap {
            position: relative;
            width: 100%;
            aspect-ratio: 16 / 8.2;
            background: #070a12;
          }
          .bd-arena-canvas {
            width: 100%;
            height: 100%;
            display: block;
            image-rendering: pixelated;
            image-rendering: crisp-edges;
          }
          .bd-arena-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 18px;
            background: #090c15;
            border-top: 4px solid #f5b700;
          }
          .bd-dialogue-box {
            color: #fef08a;
            font-size: 14px;
            text-shadow: 2px 2px 0 #000000;
            display: flex;
            align-items: center;
            gap: 8px;
          }
          .bd-skip-btn {
            background: #334155;
            color: #fff05a;
            border: 3px solid #000000;
            box-shadow: inset -2px -2px 0 #0f172a, inset 2px 2px 0 #64748b, 3px 3px 0 #000000;
            padding: 5px 12px;
            font-family: 'DungGeunMo', monospace;
            font-size: 12px;
            cursor: pointer;
          }
          .bd-tactical-banner {
            position: fixed;
            top: 66px;
            left: 50%;
            transform: translate(-50%, 0);
            z-index: 9600;
            padding: 9px 24px;
            background: rgba(9, 12, 21, 0.92);
            border: 4px solid #000000;
            box-shadow:
              inset 0 0 0 3px #f5b700,
              6px 6px 0 #000000;
            color: #fff05a;
            font-family: 'DungGeunMo', 'DotGothic16', monospace;
            font-size: 20px;
            text-align: center;
            text-shadow: 2px 2px 0 #000000;
            opacity: 0;
            pointer-events: none;
          }
          .bd-tactical-banner.bd-show {
            opacity: 1;
          }
          .bd-tactical-banner-sub {
            display: block;
            font-size: 12.5px;
            color: #ffffff;
            margin-top: 4px;
            text-shadow: 2px 2px 0 #000000;
          }
        `;
        document.head.appendChild(style);
      }

      const overlay = document.createElement('div');
      overlay.className = 'bd-arena-backdrop';
      overlay.innerHTML = `
        <div class="bd-arena-card">
          <div class="bd-arena-header">
            <div class="bd-combatant-info bd-left">
              <span class="bd-faction-tag" id="bd-atk-faction">ATK FACTION</span>
              <span class="bd-unit-title" id="bd-atk-title">ATTACKER</span>
              <div class="bd-hp-bar-wrap">
                <div class="bd-hp-bar-fill" id="bd-atk-hp" style="background: #10b981;"></div>
              </div>
            </div>
            <div class="bd-vs-badge" id="bd-skill-badge">16-BIT DUEL</div>
            <div class="bd-combatant-info bd-right">
              <span class="bd-faction-tag" id="bd-def-faction">DEF FACTION</span>
              <span class="bd-unit-title" id="bd-def-title">DEFENDER</span>
              <div class="bd-hp-bar-wrap">
                <div class="bd-hp-bar-fill" id="bd-def-hp" style="background: #ef4444;"></div>
              </div>
            </div>
          </div>
          <div class="bd-arena-canvas-wrap">
            <canvas class="bd-arena-canvas" width="840" height="430"></canvas>
          </div>
          <div class="bd-arena-footer">
            <div class="bd-dialogue-box" id="bd-dialogue-text">⚔️ BATTLE START!</div>
            <button type="button" class="bd-skip-btn" id="bd-skip-btn">[ESC / CLICK] 스킵</button>
          </div>
        </div>
      `;

      overlay.addEventListener('click', () => this.skip());
      document.body.appendChild(overlay);

      this._overlayEl = overlay;
      this._arenaCanvas = overlay.querySelector('.bd-arena-canvas');
      this._arenaCtx = this._arenaCanvas.getContext('2d');
      this._arenaCtx.imageSmoothingEnabled = false;

      const skipBtn = overlay.querySelector('#bd-skip-btn');
      if (skipBtn) {
        skipBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.skip();
        });
      }

      window.addEventListener('keydown', (e) => {
        if ((e.key === 'Escape' || e.key === ' ') && this.isPlaying) {
          this.skip();
        }
      });

      const banner = document.createElement('div');
      banner.className = 'bd-tactical-banner';
      document.body.appendChild(banner);
      this._bannerEl = banner;
    }

    showTacticalBanner(title, subtitle = '', color = '#f5b700', durationMs = 1450) {
      if (typeof document === 'undefined') return;
      this._ensureArenaDOM();
      if (!this._bannerEl) return;

      this._bannerEl.style.boxShadow = `inset 0 0 0 3px ${color}, 6px 6px 0 #000000`;
      this._bannerEl.innerHTML = `${title}${subtitle ? `<span class="bd-tactical-banner-sub">${subtitle}</span>` : ''}`;
      this._bannerEl.classList.add('bd-show');

      if (this._bannerTimer) clearTimeout(this._bannerTimer);
      this._bannerTimer = setTimeout(() => {
        if (this._bannerEl) this._bannerEl.classList.remove('bd-show');
      }, durationMs);
    }

    /**
     * window.ArtRenderer 연동 및 도트 폴백 드로잉
     */
    _drawUnitSafe(ctx, unitSpec, x, y, scale, facingRight, animState) {
      ctx.save();
      ctx.imageSmoothingEnabled = false;
      const snapX = Math.round(x / 4) * 4;
      const snapY = Math.round(y / 4) * 4;
      ctx.translate(snapX, snapY);

      const art = global.ArtRenderer;
      let drawnByExternal = false;

      // 도트 애니메이션 특유의 10-FPS 스텝 양자화
      const steppedProg = Math.floor((animState.progress || 0) * 10) / 10;
      const steppedTime = Math.floor((animState.time || Date.now()) / 90) * 90;

      if (art) {
        try {
          if (typeof art.drawUnit === 'function') {
            let mappedState = 'IDLE';
            if (animState.pose === 'APPROACH') mappedState = 'MOVE';
            else if (animState.pose === 'WINDUP' || animState.pose === 'ATTACK') mappedState = 'ATTACK';
            else if (animState.pose === 'HIT') mappedState = 'HIT';
            else if (animState.pose === 'DEAD' || animState.pose === 'DEATH') mappedState = 'DEATH';

            art.drawUnit(ctx, {
              x: 0,
              y: 18,
              type: unitSpec.type,
              side: unitSpec.side,
              faction: unitSpec.skinId,
              state: mappedState,
              progress: steppedProg,
              time: steppedTime,
              scale: scale * 1.55,
              facing: facingRight ? 1 : -1,
              showPedestal: true,
              showLabel: false
            });
            drawnByExternal = true;
          }
        } catch (_err) {
          drawnByExternal = false;
        }
      }

      if (!drawnByExternal) {
        this._drawProceduralMedievalWarrior(ctx, unitSpec, scale, facingRight, animState);
      }

      ctx.restore();
    }

    /**
     * 내장 16-BIT 도트 스프라이트 폴백 렌더러 (순수 정수 픽셀 블록 드로잉 - 장기 7병종 & 체스 6병종 지원)
     */
    _drawProceduralMedievalWarrior(ctx, unitSpec, scale, facingRight, animState) {
      ctx.save();
      const pxSize = Math.max(2, Math.round(scale * 3));
      ctx.scale(facingRight ? 1 : -1, 1);

      const lore = unitSpec.lore;
      const p = animState.progress || 0;
      const pose = animState.pose || 'IDLE';
      const uType = unitSpec.type || 'SOLDIER';

      const drawPx = (gx, gy, gw, gh, color) => {
        ctx.fillStyle = color;
        ctx.fillRect(gx * pxSize, gy * pxSize, gw * pxSize, gh * pxSize);
      };

      // 도트 그림자
      drawPx(-10, 10, 20, 3, 'rgba(0,0,0,0.55)');

      // 기마병(HORSE, KNIGHT, CHARIOT) 하단 군마 도트 블록
      if (uType === 'HORSE' || uType === 'KNIGHT' || uType === 'CHARIOT') {
        drawPx(-9, 0, 18, 6, '#475569');
        drawPx(5, -5, 5, 7, '#64748b');
        drawPx(7, -6, 4, 3, lore.accentColor);
      }

      // 몸통/갑주 도트 블록
      drawPx(-5, -6, 10, 11, lore.primaryColor);
      drawPx(-6, -7, 12, 2, lore.accentColor);

      // 머리/투구 도트 블록
      drawPx(-4, -13, 8, 6, '#94a3b8');
      drawPx(0, -11, 4, 2, '#000000');

      // 병종별 왕관/성관/성루 특징 도트
      if (uType === 'KING' || uType === 'QUEEN') {
        drawPx(-4, -17, 8, 4, '#facc15');
        drawPx(-2, -19, 4, 2, '#ffffff');
      } else if (uType === 'BISHOP') {
        drawPx(-3, -18, 6, 5, lore.accentColor);
        drawPx(-1, -20, 2, 2, '#ffffff');
      } else if (uType === 'ROOK') {
        drawPx(-6, -16, 12, 3, '#64748b');
        drawPx(-6, -18, 3, 2, '#94a3b8');
        drawPx(-1, -18, 3, 2, '#94a3b8');
        drawPx(3, -18, 3, 2, '#94a3b8');
      } else {
        drawPx(-2, -16, 4, 3, lore.accentColor);
      }

      // 다리 도트 블록
      const stride = pose === 'APPROACH' ? (Math.floor(animState.time / 100) % 2 === 0 ? 2 : -2) : 0;
      drawPx(-4 + stride, 5, 3, 6, '#334155');
      drawPx(1 - stride, 5, 3, 6, '#334155');

      // 병종별 무기 도트 블록
      const thrust = pose === 'ATTACK' ? Math.round(Math.sin(p * Math.PI) * 6) : 0;
      if (uType === 'QUEEN') {
        // 일월쌍검 & 성광 오라
        drawPx(3 + thrust, -7, 14, 2, '#fde047');
        drawPx(2 + thrust, -3, 13, 2, '#f8fafc');
        drawPx(15 + thrust, -8, 4, 6, '#e879f9');
      } else if (uType === 'BISHOP') {
        // 황금 성배 홀 / 천문령 지팡이
        drawPx(4 + thrust, -12, 2, 18, '#facc15');
        drawPx(2 + thrust, -15, 6, 4, '#38bdf8');
      } else if (uType === 'ROOK') {
        // 거대 성루 방패 & 파성 철퇴
        drawPx(2 + thrust, -9, 6, 15, '#64748b');
        drawPx(3 + thrust, -8, 4, 13, lore.accentColor);
        drawPx(8 + thrust, -6, 9, 5, '#cbd5e1');
      } else {
        drawPx(3 + thrust, -5, 12, 2, '#f8fafc');
        drawPx(14 + thrust, -6, 4, 4, lore.accentColor);
      }

      ctx.restore();
    }

    /**
     * HD 도트 일러스트 컷인(Cut-in) 연출 연동 (global.ArtRenderer.drawBattleCutIn 우선 호출 + 내장 16-Bit 컷인 폴백)
     */
    _drawCutInOverlay(ctx, W, H, atkPiece, defPiece, atkLore, defLore, atkUnit, defUnit, rawT, elapsed) {
      if (rawT < 0.03 || rawT > 0.72) return;

      // 진입(0.03~0.14) -> 유지(0.14~0.58) -> 퇴장(0.58~0.72)
      let slideRatio = 1;
      if (rawT < 0.14) {
        slideRatio = (rawT - 0.03) / 0.11;
      } else if (rawT > 0.58) {
        slideRatio = 1 - (rawT - 0.58) / 0.14;
      }
      slideRatio = Math.max(0, Math.min(1, slideRatio));
      const cutInProg = Math.min(1, Math.max(0, (rawT - 0.03) / 0.69));

      const cutInW = Math.round((W * 0.92) / 4) * 4;
      const cutInH = 76;
      const cutInX = Math.round(((W - cutInW) * 0.5 - (1 - slideRatio) * W * 0.6) / 4) * 4;
      const cutInY = 14;

      const art = global.ArtRenderer;
      let drawnByExternal = false;

      if (art && typeof art.drawBattleCutIn === 'function') {
        try {
          const payload = {
            x: cutInX,
            y: cutInY,
            w: cutInW,
            h: cutInH,
            width: cutInW,
            height: cutInH,
            canvasWidth: W,
            canvasHeight: H,
            type: atkPiece.type,
            unitType: atkPiece.type,
            pieceType: atkPiece.type,
            side: atkPiece.side,
            faction: atkLore.id,
            skin: atkLore.id,
            title: atkUnit.title,
            skillName: atkUnit.skillName,
            cry: atkUnit.cry,
            weapon: atkUnit.weapon,
            progress: cutInProg,
            slideRatio,
            time: elapsed,
            attacker: {
              type: atkPiece.type,
              side: atkPiece.side,
              faction: atkLore.id,
              title: atkUnit.title,
              skillName: atkUnit.skillName,
              cry: atkUnit.cry
            },
            defender: {
              type: defPiece.type,
              side: defPiece.side,
              faction: defLore.id,
              title: defUnit.title
            }
          };

          if (art.drawBattleCutIn.length >= 5) {
            art.drawBattleCutIn(ctx, cutInX, cutInY, cutInW, cutInH, payload);
          } else {
            art.drawBattleCutIn(ctx, payload);
          }
          drawnByExternal = true;
        } catch (_err) {
          drawnByExternal = false;
        }
      }

      if (!drawnByExternal) {
        ctx.save();
        ctx.imageSmoothingEnabled = false;

        // 16-Bit HD 도트 컷인 배경 바 & 스피드라인
        ctx.fillStyle = '#000000';
        ctx.fillRect(cutInX - 4, cutInY - 4, cutInW + 8, cutInH + 8);
        ctx.fillStyle = atkLore.primaryColor;
        ctx.fillRect(cutInX, cutInY, cutInW, cutInH);

        // 계단식 도트 스피드라인
        ctx.fillStyle = atkLore.accentColor;
        const speedOffset = Math.floor(elapsed / 25) % 48;
        for (let sy = cutInY + 8; sy < cutInY + cutInH - 6; sy += 12) {
          const lx = cutInX + ((sy * 17 + speedOffset * 12) % (cutInW - 90));
          ctx.fillRect(lx, sy, 68, 4);
        }

        // 골드 이중 픽셀 테두리
        ctx.fillStyle = '#f5b700';
        ctx.fillRect(cutInX, cutInY, cutInW, 4);
        ctx.fillRect(cutInX, cutInY + cutInH - 4, cutInW, 4);
        ctx.fillRect(cutInX, cutInY, 6, cutInH);
        ctx.fillRect(cutInX + cutInW - 6, cutInY, 6, cutInH);

        // 좌측 도트 초상화 프레임 & 미니 유닛 클로즈업
        ctx.fillStyle = '#090c15';
        ctx.fillRect(cutInX + 12, cutInY + 8, 84, cutInH - 16);
        this._drawUnitSafe(
          ctx,
          { type: atkPiece.type, side: atkPiece.side, skinId: atkLore.id, lore: atkLore },
          cutInX + 54,
          cutInY + cutInH - 14,
          0.95,
          true,
          { pose: 'ATTACK', progress: 0.5, time: elapsed }
        );

        // 우측 스킬명 & 컷인 대사 텍스트
        ctx.textAlign = 'left';
        ctx.font = 'bold 18px "Silkscreen", "DungGeunMo", monospace';
        ctx.fillStyle = '#000000';
        ctx.fillText(`⚡ ${atkUnit.skillName}!!`, cutInX + 114, cutInY + 32);
        ctx.fillStyle = '#fff05a';
        ctx.fillText(`⚡ ${atkUnit.skillName}!!`, cutInX + 112, cutInY + 30);

        ctx.font = 'bold 13px "DungGeunMo", monospace';
        ctx.fillStyle = '#ffffff';
        ctx.fillText(`[${atkUnit.title}] "${atkUnit.cry}"`, cutInX + 112, cutInY + 56);

        ctx.restore();
      }
    }

    /**
     * 폰(PAWN) 프로모션 황금 각성 시네마틱 연출 (사운드 + 전술 각성 배너)
     */
    playPromotionCinematic(params = {}) {
      const move = params.move || {};
      const piece = move.piece || params.piece || { type: 'QUEEN', side: 'CHU' };
      const promotedType = String(move.promotedType || move.promotion || params.promotedType || 'QUEEN').toUpperCase();
      const lore = resolveFactionLore(params.skin || params.attackerSkin, piece.side);
      const promoUnit = lore.units[promotedType] || lore.units.QUEEN || lore.units.KING;

      SoundFX.playPromotionFanfare(0);
      this.showTacticalBanner(
        `✨ PROMOTION AWAKENING : ${promoUnit.title}!`,
        `${lore.shortName} 각성 승진 완료! ➔ [${promoUnit.skillName}] ("${promoUnit.cry}")`,
        '#f5b700',
        1850
      );

      if (typeof params.onComplete === 'function') {
        setTimeout(() => params.onComplete(), 450);
      }
      return Promise.resolve();
    }

    playCaptureCinematic(params = {}) {
      const move = params.move;
      if (!move || !move.captured) {
        if (move && (move.promoted || move.promotion)) {
          return this.playPromotionCinematic(params);
        }
        if (typeof params.onComplete === 'function') params.onComplete();
        return Promise.resolve();
      }

      const attackerPiece = move.piece;
      const defenderPiece = move.captured;
      const atkLore = resolveFactionLore(params.attackerSkin, attackerPiece.side);
      const defLore = resolveFactionLore(params.defenderSkin, defenderPiece.side);

      const isGiantKilling =
        (attackerPiece.type === 'SOLDIER' || attackerPiece.type === 'PAWN') &&
        (defenderPiece.score >= 5 || ['CHARIOT', 'ROOK', 'QUEEN', 'KING'].includes(defenderPiece.type));

      if (move.promoted || move.promotion) {
        SoundFX.playPromotionFanfare(0.18);
      }

      if (this.mode === 'FAST') {
        return this._playBoardZoomSequence(move, atkLore, defLore, true, isGiantKilling, params.onComplete);
      }

      if (this.mode === 'BOARD_ZOOM') {
        return this._playBoardZoomSequence(move, atkLore, defLore, false, isGiantKilling, params.onComplete);
      }

      return this._playArenaOverlaySequence(move, atkLore, defLore, isGiantKilling, params.onComplete);
    }

    /**
     * 별도 이미지 씬 없이 2.5D 보드판 위에서 직접 돌격·화포/신벌 포격·마법검무·공중도약·대지분쇄가 터지는 현장 타격 연출
     */
    _playBoardZoomSequence(move, atkLore, defLore, isFast, isGiantKilling, onComplete) {
      return new Promise((resolve) => {
        this._ensureArenaDOM();
        this.isPlaying = true;
        this._skipRequested = false;

        const duration = isFast ? 650 : 1380;
        const startTime = performance.now();

        const atkPiece = move.piece;
        const defPiece = move.captured;
        const atkUnit = atkLore.units[atkPiece.type] || atkLore.units.SOLDIER;
        const defUnit = defLore.units[defPiece.type] || defLore.units.SOLDIER;

        const isQueen = atkPiece.type === 'QUEEN';
        const isBishop = atkPiece.type === 'BISHOP';
        const isKnight = atkPiece.type === 'KNIGHT';
        const isRook = atkPiece.type === 'ROOK';
        const isRanged = atkPiece.type === 'CANNON' || isBishop;
        const isPromoted = Boolean(move.promoted || move.promotion);

        const atkLabel = atkPiece.kr || atkPiece.name || atkUnit.title || atkPiece.type;
        const defLabel = defPiece.kr || defPiece.name || defUnit.title || defPiece.type;

        this.showTacticalBanner(
          isPromoted
            ? `✨ PROMOTION & ${atkUnit.skillName}!`
            : (isGiantKilling ? `★ GIANT KILL : ${atkUnit.skillName}!` : `⚔️ ${atkUnit.skillName}!`),
          `${atkLore.shortName} [${atkLabel}] ➔ ${defLore.shortName} [${defLabel}] 현장 격파! ("${atkUnit.cry}")`,
          atkLore.accentColor,
          duration + 180
        );

        if (atkPiece.type === 'CANNON') {
          SoundFX.playCannonFire(0.05);
        } else if (isQueen || isBishop) {
          SoundFX.playQueenMagicSlash(0.02);
        } else if (atkPiece.type === 'ELEPHANT' || isRook) {
          SoundFX.playElephantStomp(0);
        } else if (atkPiece.type === 'HORSE' || atkPiece.type === 'CHARIOT' || isKnight) {
          SoundFX.playHorseGallop(3);
        } else {
          SoundFX.playWoodSnap(0);
        }

        let impact1Played = false;
        let impact2Played = false;
        const particles = [];
        const shockwaves = [];
        const popups = [];

        const spawnBoardParticles = (color1, color2, count, speedMul = 1.0) => {
          for (let i = 0; i < count; i++) {
            const angle = (i / count) * Math.PI * 2 + (Math.random() * 0.35);
            const spd = (2.5 + Math.random() * 6.5) * speedMul;
            particles.push({
              dx: (Math.random() - 0.5) * 14,
              dy: (Math.random() - 0.5) * 8,
              dz: 8 + Math.random() * 18,
              vx: Math.cos(angle) * spd,
              vy: Math.sin(angle) * spd * 0.58,
              vz: 4.5 + Math.random() * 7.5,
              size: i % 3 === 0 ? 8 : (i % 2 === 0 ? 6 : 4),
              color: i % 3 === 0 ? '#ffffff' : (i % 2 === 0 ? color1 : color2),
              life: 22 + Math.floor(Math.random() * 14)
            });
          }
        };

        const finishOnBoardDuel = () => {
          this.boardCamera.active = false;
          this.boardCamera.zoom = 1.0;
          this.boardCamera.shakeX = 0;
          this.boardCamera.shakeY = 0;
          this.boardDuel = null;
          this.isPlaying = false;
          this._skipRequested = false;
          if (typeof onComplete === 'function') onComplete();
          resolve();
        };

        const step = (now) => {
          if (this._skipRequested) {
            finishOnBoardDuel();
            return;
          }

          const elapsed = now - startTime;
          const rawT = Math.min(1, elapsed / duration);

          // 히트스톱(Hit-Stop): 타격 순간 프레임을 짧게 홀드하여 묵직한 타격감 부여
          let t = rawT;
          if (!isFast) {
            if (rawT > 0.38 && rawT < 0.43) t = 0.38;
            else if (rawT > 0.58 && rawT < 0.64) t = 0.58;
          }

          // 1차 타격 (무기 격돌 / 포탄·신벌 광선 초탄 착탄 / 퀸 다중 마법검무)
          if (rawT >= 0.36 && !impact1Played) {
            impact1Played = true;
            if (atkPiece.type === 'CANNON') {
              SoundFX.playExplosion(0);
            } else if (isQueen || isBishop) {
              SoundFX.playQueenMagicSlash(0);
            } else if (isRook) {
              SoundFX.playElephantStomp(0);
              SoundFX.playShieldBash(0.02);
            } else {
              SoundFX.playSwordClash(0);
              SoundFX.playShieldBash(0.03);
            }

            if (isQueen) {
              spawnBoardParticles('#fde047', '#e879f9', 42, 1.25);
              shockwaves.push({ r: 8, maxR: 96, color: '#e879f9', width: 5, life: 18, maxLife: 18 });
              shockwaves.push({ r: 4, maxR: 74, color: '#fff05a', width: 4, life: 16, maxLife: 16 });
            } else if (isBishop) {
              spawnBoardParticles('#38bdf8', '#fde047', 34, 1.15);
              shockwaves.push({ r: 8, maxR: 84, color: '#38bdf8', width: 5, life: 17, maxLife: 17 });
            } else {
              spawnBoardParticles('#fff05a', '#ef4444', 28, 1.0);
              shockwaves.push({ r: 8, maxR: 72, color: '#fff05a', width: 4, life: 16, maxLife: 16 });
            }

            popups.push({
              text: isQueen
                ? `⚔️ -425 ARCANE SLASH!`
                : (isBishop ? `⚡ -${Math.round(defUnit.hp * 0.45)} DIVINE RAY!` : `-${Math.round(defUnit.hp * 0.45)}`),
              dx: -18,
              dy: -54,
              color: isBishop ? '#38bdf8' : '#fde047',
              scale: isQueen ? 1.08 : 0.95,
              age: 0
            });
          }

          // 2차 결정타 크리티컬 피니시 (처형 참격 / 퀸 성광 폭격 / 룩 대지분쇄 / 나이트 급강하)
          if (rawT >= 0.56 && !impact2Played) {
            impact2Played = true;
            SoundFX.playHeavySlash(0);
            if (isQueen) {
              SoundFX.playExplosion(0.02);
            } else if (atkPiece.type === 'ELEPHANT' || atkPiece.type === 'KING' || isRook || isRanged) {
              SoundFX.playElephantStomp(0.02);
            }

            if (isQueen) {
              spawnBoardParticles('#f5b700', '#e879f9', 64, 1.65);
              shockwaves.push({ r: 14, maxR: 138, color: '#ff3b5c', width: 7, life: 24, maxLife: 24 });
              shockwaves.push({ r: 8, maxR: 112, color: '#f5b700', width: 5, life: 21, maxLife: 21 });
              shockwaves.push({ r: 4, maxR: 88, color: '#e879f9', width: 4, life: 18, maxLife: 18 });
            } else if (isRook) {
              spawnBoardParticles('#f5b700', '#94a3b8', 52, 1.45);
              shockwaves.push({ r: 12, maxR: 124, color: '#f5b700', width: 7, life: 22, maxLife: 22 });
              shockwaves.push({ r: 6, maxR: 92, color: '#ff3b5c', width: 5, life: 19, maxLife: 19 });
            } else {
              spawnBoardParticles(atkLore.accentColor, '#ff3b5c', 42, 1.35);
              shockwaves.push({ r: 12, maxR: 108, color: '#ff3b5c', width: 6, life: 20, maxLife: 20 });
              shockwaves.push({ r: 4, maxR: 84, color: atkLore.accentColor, width: 4, life: 18, maxLife: 18 });
            }

            let finisherText = `💥 -${defUnit.hp} CRITICAL!!`;
            if (isQueen) {
              finisherText = `💥 -850 EMPRESS OBLITERATION!!`;
            } else if (isGiantKilling) {
              finisherText = `★ GIANT KILL -999!!`;
            } else if (isBishop) {
              finisherText = `⚡ -${defUnit.hp} DIVINE SMITE!!`;
            } else if (isRook) {
              finisherText = `🪨 -${defUnit.hp} EARTH SHATTER!!`;
            } else if (isKnight) {
              finisherText = `🐎 -${defUnit.hp} SKY LEAP STRIKE!!`;
            }

            popups.push({
              text: finisherText,
              dx: 0,
              dy: isQueen ? -86 : -76,
              color: isQueen ? '#fde047' : '#ff3b5c',
              scale: isQueen ? 1.32 : 1.15,
              age: 0
            });
          }

          // 파티클 물리 업데이트 (3D Z축 중력 및 보드판 표면 바운스!)
          for (let i = particles.length - 1; i >= 0; i--) {
            const pt = particles[i];
            pt.dx += pt.vx;
            pt.dy += pt.vy;
            pt.dz += pt.vz;
            pt.vz -= 0.72;
            if (pt.dz < 0) {
              pt.dz = 0;
              pt.vz = -pt.vz * 0.45;
              pt.vx *= 0.75;
              pt.vy *= 0.75;
            }
            pt.life -= 1;
            if (pt.life <= 0) {
              particles.splice(i, 1);
            }
          }

          // 2.5D 충격파 링 업데이트
          for (let i = shockwaves.length - 1; i >= 0; i--) {
            const sw = shockwaves[i];
            sw.life -= 1;
            const prog = 1 - sw.life / sw.maxLife;
            sw.r = 10 + (sw.maxR - 10) * prog;
            if (sw.life <= 0) {
              shockwaves.splice(i, 1);
            }
          }

          // 데미지 팝업 업데이트
          for (let i = 0; i < popups.length; i++) {
            popups[i].age += 1;
          }

          // 부드럽고 묵직한 보드 줌 & 타격 진동 (퀸/룩은 더 강력한 진동)
          const zoomPeak = isFast ? 1.08 : (isQueen ? 1.24 : 1.18);
          const zoomCurve = 1 + Math.sin(rawT * Math.PI) * (zoomPeak - 1);
          const isShaking = rawT >= 0.36 && rawT <= 0.80;
          const maxShake = isQueen || isRook ? 14 : 10;
          const shakeAmp = rawT >= 0.56 && rawT <= 0.74 ? maxShake : (isShaking ? 6 : 0);

          this.boardCamera = {
            active: rawT < 1,
            focusX: move.toX,
            focusY: move.toY,
            fromX: move.fromX,
            fromY: move.fromY,
            zoom: zoomCurve,
            shakeX: shakeAmp ? (Math.floor(now / 28) % 2 === 0 ? shakeAmp : -shakeAmp) : 0,
            shakeY: shakeAmp ? (Math.floor(now / 36) % 2 === 0 ? -shakeAmp * 0.75 : shakeAmp * 0.75) : 0,
            progress: rawT,
            attackerColor: atkLore.accentColor
          };

          const hpRatio = rawT < 0.36 ? 1.0 : (rawT < 0.56 ? 0.42 : 0.0);
          const flashFrame = (rawT >= 0.36 && rawT <= 0.40) || (rawT >= 0.56 && rawT <= 0.61);

          // 나이트(KNIGHT) / 마(HORSE) 공중 도약 고도 계산
          const jumpOffsetZ =
            (isKnight || atkPiece.type === 'HORSE') && rawT < 0.42
              ? Math.sin((rawT / 0.42) * Math.PI) * (isKnight ? 96 : 64)
              : 0;

          // 비숍(BISHOP) 대각선 신벌 광선 및 퀸(QUEEN) 다중 검무 궤적 상태
          const divineRayProgress =
            (isBishop || isQueen) && rawT >= 0.16 && rawT <= 0.66
              ? Math.min(1, (rawT - 0.16) / 0.45)
              : 0;

          this.boardDuel = {
            active: rawT < 1,
            move,
            atkPiece,
            defPiece,
            atkLore,
            defLore,
            atkUnit,
            defUnit,
            isRanged,
            isBishop,
            isQueen,
            isKnight,
            isRook,
            isPromoted,
            isGiantKilling,
            jumpOffsetZ,
            divineRayProgress,
            cutInActive: rawT >= 0.04 && rawT <= 0.68,
            cutInProgress: Math.min(1, Math.max(0, (rawT - 0.04) / 0.64)),
            rawT,
            t,
            hpRatio,
            flashFrame,
            particles,
            shockwaves,
            popups
          };

          if (rawT < 1) {
            requestAnimationFrame(step);
          } else {
            finishOnBoardDuel();
          }
        };

        requestAnimationFrame(step);
      });
    }

    /**
     * 16-BIT 도트 배틀 아레나 시네마틱 시퀀스 ('ARENA_OVERLAY' 모드)
     */
    _playArenaOverlaySequence(move, atkLore, defLore, isGiantKilling, onComplete) {
      this._ensureArenaDOM();
      if (!this._overlayEl || !this._arenaCtx) {
        if (typeof onComplete === 'function') onComplete();
        return Promise.resolve();
      }

      return new Promise((resolve) => {
        this.isPlaying = true;
        this._skipRequested = false;

        const atkPiece = move.piece;
        const defPiece = move.captured;
        const atkUnit = atkLore.units[atkPiece.type] || atkLore.units.SOLDIER;
        const defUnit = defLore.units[defPiece.type] || defLore.units.SOLDIER;

        const isQueen = atkPiece.type === 'QUEEN';
        const isBishop = atkPiece.type === 'BISHOP';
        const isKnight = atkPiece.type === 'KNIGHT';
        const isRook = atkPiece.type === 'ROOK';
        const isRanged = atkPiece.type === 'CANNON' || isBishop;

        const atkHanja = atkPiece.hanja || atkPiece.symbol || atkPiece.kr || atkPiece.type;
        const defHanja = defPiece.hanja || defPiece.symbol || defPiece.kr || defPiece.type;

        const elAtkFaction = this._overlayEl.querySelector('#bd-atk-faction');
        const elAtkTitle = this._overlayEl.querySelector('#bd-atk-title');
        const elAtkHp = this._overlayEl.querySelector('#bd-atk-hp');
        const elDefFaction = this._overlayEl.querySelector('#bd-def-faction');
        const elDefTitle = this._overlayEl.querySelector('#bd-def-title');
        const elDefHp = this._overlayEl.querySelector('#bd-def-hp');
        const elBadge = this._overlayEl.querySelector('#bd-skill-badge');
        const elDialogue = this._overlayEl.querySelector('#bd-dialogue-text');

        if (elAtkFaction) elAtkFaction.textContent = `${atkLore.shortName} · ATK ${atkUnit.atk}`;
        if (elAtkTitle) elAtkTitle.textContent = `${atkUnit.title} [${atkHanja}]`;
        if (elAtkHp) elAtkHp.style.width = '100%';

        if (elDefFaction) elDefFaction.textContent = `${defLore.shortName} · HP ${defUnit.hp}`;
        if (elDefTitle) elDefTitle.textContent = `${defUnit.title} [${defHanja}]`;
        if (elDefHp) elDefHp.style.width = '100%';

        if (elBadge) {
          elBadge.textContent = isGiantKilling ? '★ GIANT KILL! ★' : `⚔️ ${atkUnit.skillName}`;
        }
        if (elDialogue) {
          elDialogue.textContent = `▶ "${atkUnit.cry}"`;
        }

        this._overlayEl.classList.add('bd-active');

        if (atkPiece.type === 'CANNON') {
          SoundFX.playCannonFire(0.28);
        } else if (isQueen || isBishop) {
          SoundFX.playQueenMagicSlash(0.18);
        } else if (atkPiece.type === 'ELEPHANT' || isRook) {
          SoundFX.playElephantStomp(0.15);
        } else {
          SoundFX.playHorseGallop(3);
        }

        let impactSoundPlayed = false;
        let finishSoundPlayed = false;

        // 사각형 도트 파티클, 충격파 링 및 도트 데미지 팝업 배열
        const pixelParticles = [];
        const arenaShockwaves = [];
        const damagePopups = [];

        const spawnPixelParticles = (cx, cy, color1, color2, count = 36) => {
          for (let i = 0; i < count; i++) {
            const angle = (Math.floor(Math.random() * 16) / 16) * Math.PI * 2;
            const speed = 4 + Math.floor(Math.random() * 10);
            pixelParticles.push({
              x: cx,
              y: cy,
              vx: Math.cos(angle) * speed,
              vy: Math.sin(angle) * speed - 4,
              size: i % 3 === 0 ? 8 : 6,
              color: i % 2 === 0 ? color1 : color2,
              life: 18 + Math.floor(Math.random() * 10)
            });
          }
        };

        const totalDuration = 1680;
        const startTime = performance.now();

        const renderFrame = (now) => {
          if (this._skipRequested) {
            this._finishArena(onComplete, resolve);
            return;
          }

          const elapsed = now - startTime;
          const rawT = Math.min(1, elapsed / totalDuration);
          // 히트스톱(Hit-Stop): 타격 순간(0.42~0.47, 0.62~0.67) 프레임을 잠깐 홀드하여 도트 타격감 극대화
          let t = rawT;
          if (rawT > 0.42 && rawT < 0.47) t = 0.42;
          else if (rawT > 0.62 && rawT < 0.67) t = 0.62;

          const ctx = this._arenaCtx;
          ctx.imageSmoothingEnabled = false;
          const W = this._arenaCanvas.width;
          const H = this._arenaCanvas.height;

          let shakeX = 0;
          let shakeY = 0;

          if (rawT >= 0.42 && !impactSoundPlayed) {
            impactSoundPlayed = true;
            if (isQueen || isBishop) {
              SoundFX.playQueenMagicSlash(0);
            } else if (!isRanged) {
              SoundFX.playSwordClash(0);
              SoundFX.playShieldBash(0.03);
            }
            spawnPixelParticles(
              W * 0.66,
              H * 0.56,
              isBishop ? '#38bdf8' : '#fff05a',
              isQueen ? '#e879f9' : '#ef4444',
              isQueen ? 46 : 34
            );
            arenaShockwaves.push({
              x: W * 0.68,
              y: H * 0.56,
              r: 12,
              maxR: isQueen ? 130 : 92,
              color: isBishop ? '#38bdf8' : (isQueen ? '#e879f9' : '#fff05a'),
              life: 16,
              maxLife: 16
            });
            damagePopups.push({
              text: isQueen
                ? `⚔️ -425 SWORD DANCE!`
                : (isBishop ? `⚡ -${Math.round(defUnit.hp * 0.45)} DIVINE RAY!` : `-${Math.round(defUnit.hp * 0.45)}`),
              x: W * 0.66,
              y: H * 0.36,
              color: isBishop ? '#38bdf8' : '#fff05a',
              age: 0
            });
            if (elDefHp) elDefHp.style.width = '40%';
          }

          if (rawT >= 0.62 && !finishSoundPlayed) {
            finishSoundPlayed = true;
            SoundFX.playHeavySlash(0);
            if (isQueen) {
              SoundFX.playExplosion(0.03);
            } else if (isRook) {
              SoundFX.playElephantStomp(0.02);
            }
            spawnPixelParticles(W * 0.68, H * 0.54, atkLore.accentColor, '#ffffff', isQueen ? 68 : 48);
            arenaShockwaves.push({
              x: W * 0.68,
              y: H * 0.54,
              r: 16,
              maxR: isQueen ? 175 : 128,
              color: '#ff3b5c',
              life: 20,
              maxLife: 20
            });
            if (isQueen) {
              arenaShockwaves.push({
                x: W * 0.68,
                y: H * 0.54,
                r: 8,
                maxR: 140,
                color: '#fde047',
                life: 18,
                maxLife: 18
              });
            }

            let koPopupText = `-${defUnit.hp} CRITICAL!!`;
            if (isQueen) {
              koPopupText = `💥 -850 EMPRESS OBLITERATION!!`;
            } else if (isGiantKilling) {
              koPopupText = `-999 GIANT KILL!!`;
            } else if (isBishop) {
              koPopupText = `⚡ -${defUnit.hp} DIVINE SMITE!!`;
            } else if (isRook) {
              koPopupText = `🪨 -${defUnit.hp} EARTH SHATTER!!`;
            } else if (isKnight) {
              koPopupText = `🐎 -${defUnit.hp} SKY LEAP KO!!`;
            }

            damagePopups.push({
              text: koPopupText,
              x: W * 0.64,
              y: H * 0.27,
              color: isQueen ? '#fde047' : '#ff3b5c',
              age: 0
            });
            if (elDefHp) elDefHp.style.width = '0%';
            if (elDialogue) {
              elDialogue.textContent = `💥 [${atkUnit.title}] 부대가 적 [${defUnit.title}] 부대를 격파! (KO!!)`;
            }
          }

          if (rawT > 0.42 && rawT < 0.78) {
            const amp = isQueen || isRook ? 12 : 8;
            shakeX = (Math.floor(now / 30) % 2 === 0 ? 1 : -1) * amp;
            shakeY = (Math.floor(now / 40) % 2 === 0 ? -1 : 1) * (amp * 0.75);
          }

          ctx.save();
          ctx.translate(shakeX, shakeY);

          // 1. 16-BIT 도트 배틀 배경 (계단식 픽셀 밤하늘 + 도트 성벽 + 도트 타일 바닥)
          this._drawPixelArenaBackdrop(ctx, W, H, atkLore, defLore, rawT);

          // 2. 공격자 & 방어자 위치/포즈 계산 (4px 그리드 스냅 + 나이트 공중도약 Y오프셋)
          let atkX = W * 0.24;
          let atkY = H * 0.66;
          let atkPose = 'APPROACH';
          let atkProg = 0;

          if (!isRanged) {
            if (t < 0.36) {
              const p1 = t / 0.36;
              atkX = W * (0.18 + p1 * 0.36);
              if (isKnight) {
                // 나이트(KNIGHT) 천공 포물선 공중도약!
                atkY = H * 0.66 - Math.sin(p1 * Math.PI) * 136;
              }
              atkPose = p1 > 0.65 ? 'WINDUP' : 'APPROACH';
              atkProg = (p1 - 0.65) / 0.35;
            } else if (t < 0.72) {
              atkX = W * 0.54;
              atkPose = 'ATTACK';
              atkProg = (t - 0.36) / 0.36;
            } else {
              atkX = W * 0.56;
              atkPose = 'IDLE';
              atkProg = 1;
            }
          } else {
            atkX = W * 0.22;
            atkPose = t > 0.20 && t < 0.64 ? 'ATTACK' : 'IDLE';
            atkProg = Math.min(1, Math.max(0, (t - 0.20) / 0.38));
          }

          let defX = W * 0.70;
          let defPose = 'IDLE';
          let defProg = 0;
          if (t >= 0.42 && t < 0.64) {
            defPose = 'HIT';
            defProg = (t - 0.42) / 0.22;
          } else if (t >= 0.64) {
            defPose = 'DEAD';
            defProg = Math.min(1, (t - 0.64) / 0.32);
          }

          // 3A. 포(CANNON)일 경우 16-bit 도트 포물선 포탄/신기전 렌더링
          if (atkPiece.type === 'CANNON' && t > 0.18 && t < 0.60) {
            const projT = Math.min(1, (t - 0.18) / 0.34);
            const px = Math.round((atkX + 44 + (defX - atkX - 44) * projT) / 4) * 4;
            const py = Math.round((H * 0.56 - Math.sin(projT * Math.PI) * 160) / 4) * 4;

            ctx.fillStyle = '#ea580c';
            ctx.fillRect(px - 16, py - 16, 32, 32);
            ctx.fillStyle = '#facc15';
            ctx.fillRect(px - 10, py - 10, 20, 20);
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(px - 4, py - 4, 8, 8);
          }

          // 3B. 비숍(BISHOP)일 경우 대각선 성광/천뢰 신벌 광선(Divine Ray) & 마법 탄환 궤적
          if (isBishop && t > 0.20 && t < 0.68) {
            const rayT = Math.min(1, (t - 0.20) / 0.28);
            const targetX = Math.round(defX / 4) * 4;
            const targetY = Math.round((H * 0.56) / 4) * 4;

            // 공격자 지팡이 -> 방어자 마법 궤적 + 천공 대각선 신벌 광선
            const steps = 20;
            for (let i = 0; i <= Math.floor(steps * rayT); i++) {
              const rProg = i / steps;
              const bx = Math.round((atkX + 48 + (targetX - atkX - 48) * rProg) / 4) * 4;
              const by = Math.round((H * 0.48 - Math.sin(rProg * Math.PI) * 64) / 4) * 4;
              ctx.fillStyle = '#38bdf8';
              ctx.fillRect(bx - 6, by - 6, 12, 12);
              ctx.fillStyle = '#fef08a';
              ctx.fillRect(bx - 3, by - 3, 6, 6);
            }

            if (t >= 0.38) {
              // 하늘에서 대각선으로 꽂히는 신벌 성광 기둥
              for (let s = 0; s < 18; s++) {
                const lx = targetX - (18 - s) * 10;
                const ly = s * 18;
                ctx.fillStyle = 'rgba(56, 189, 248, 0.75)';
                ctx.fillRect(lx - 14, ly, 28, 20);
                ctx.fillStyle = '#fef08a';
                ctx.fillRect(lx - 6, ly, 12, 20);
              }
            }
          }

          // 3C. 룩(ROOK) 대지분쇄 지진 암석 기둥 연출
          if (isRook && rawT > 0.40 && rawT < 0.78) {
            const rockCount = 6;
            for (let r = 0; r < rockCount; r++) {
              const rx = Math.round((W * 0.56 + r * 34) / 4) * 4;
              const rh = 24 + (r % 3) * 18;
              ctx.fillStyle = '#475569';
              ctx.fillRect(rx, H * 0.70 - rh, 20, rh);
              ctx.fillStyle = '#f5b700';
              ctx.fillRect(rx + 4, H * 0.70 - rh, 4, rh);
            }
          }

          // 3D. 퀸(QUEEN) 초고속 잔상 & 성광 폭격 기둥 연출
          if (isQueen && t > 0.16 && t < 0.68) {
            // 퀸 마법검무 잔상
            this._drawUnitSafe(
              ctx,
              { type: atkPiece.type, side: atkPiece.side, skinId: atkLore.id, lore: atkLore },
              atkX - 48,
              atkY,
              1.42,
              true,
              { pose: 'ATTACK', progress: 0.4, time: elapsed }
            );
            if (rawT >= 0.54) {
              // 성광 폭격(Empress Obliteration) 수직 빛기둥
              const pillarX = Math.round(defX / 4) * 4;
              ctx.fillStyle = 'rgba(232, 121, 249, 0.55)';
              ctx.fillRect(pillarX - 44, 0, 88, H * 0.72);
              ctx.fillStyle = 'rgba(253, 224, 71, 0.85)';
              ctx.fillRect(pillarX - 20, 0, 40, H * 0.72);
              ctx.fillStyle = '#ffffff';
              ctx.fillRect(pillarX - 8, 0, 16, H * 0.72);
            }
          }

          // 4. 캐릭터 도트 유닛 드로잉
          this._drawUnitSafe(
            ctx,
            { type: defPiece.type, side: defPiece.side, skinId: defLore.id, lore: defLore },
            defX,
            H * 0.66,
            1.45,
            false,
            { pose: defPose, progress: defProg, time: elapsed }
          );

          this._drawUnitSafe(
            ctx,
            { type: atkPiece.type, side: atkPiece.side, skinId: atkLore.id, lore: atkLore },
            atkX,
            atkY,
            1.52,
            true,
            { pose: atkPose, progress: atkProg, time: elapsed }
          );

          // 5. 타격 순간 도트 크로스 슬래시 & 퀸 다중 마법검무 슬래시 이펙트
          if (rawT > 0.42 && rawT < 0.74) {
            const sx = Math.round(defX / 4) * 4;
            const sy = Math.round((H * 0.54) / 4) * 4;
            ctx.fillStyle = '#fff05a';
            for (let step = -7; step <= 7; step++) {
              ctx.fillRect(sx + step * 8, sy + step * 8, 8, 8);
              ctx.fillRect(sx + step * 8, sy - step * 8, 8, 8);
            }
            if (isQueen) {
              // 퀸 전용 8방향 성광 다중 도트 슬래시
              ctx.fillStyle = '#e879f9';
              for (let step = -9; step <= 9; step++) {
                ctx.fillRect(sx + step * 10, sy, 8, 8);
                ctx.fillRect(sx, sy + step * 8, 8, 8);
                ctx.fillRect(sx + step * 8 - 20, sy - step * 6, 6, 6);
              }
            }
          }

          // 5B. 도트 충격파 링 업데이트 및 렌더링
          for (let i = arenaShockwaves.length - 1; i >= 0; i--) {
            const sw = arenaShockwaves[i];
            sw.life -= 1;
            if (sw.life <= 0) {
              arenaShockwaves.splice(i, 1);
              continue;
            }
            const prog = 1 - sw.life / sw.maxLife;
            const curR = Math.round((sw.r + (sw.maxR - sw.r) * prog) / 4) * 4;
            ctx.strokeStyle = sw.color;
            ctx.lineWidth = 4;
            ctx.strokeRect(sw.x - curR, sw.y - curR * 0.55, curR * 2, curR * 1.1);
          }

          // 6. 사각형 도트 파티클 업데이트 및 렌더링
          for (let i = pixelParticles.length - 1; i >= 0; i--) {
            const pt = pixelParticles[i];
            pt.x += pt.vx;
            pt.y += pt.vy;
            pt.vy += 0.45;
            pt.life -= 1;
            if (pt.life <= 0) {
              pixelParticles.splice(i, 1);
              continue;
            }
            const rx = Math.round(pt.x / 4) * 4;
            const ry = Math.round(pt.y / 4) * 4;
            ctx.fillStyle = '#000000';
            ctx.fillRect(rx - 2, ry - 2, pt.size + 4, pt.size + 4);
            ctx.fillStyle = pt.color;
            ctx.fillRect(rx, ry, pt.size, pt.size);
          }

          // 7. 상단 HD 도트 일러스트 컷인(Cut-in) 연동 렌더링
          this._drawCutInOverlay(ctx, W, H, atkPiece, defPiece, atkLore, defLore, atkUnit, defUnit, rawT, elapsed);

          // 8. 도트 데미지 숫자 팝업 ("💥 -850 EMPRESS OBLITERATION!!", "-999 CRITICAL!!")
          for (let i = 0; i < damagePopups.length; i++) {
            const dp = damagePopups[i];
            dp.age += 1;
            const dy = dp.y - Math.min(32, dp.age * 1.4);
            ctx.save();
            const isEmpressPopup = dp.text.includes('EMPRESS OBLITERATION');
            ctx.font = isEmpressPopup
              ? 'bold 28px "Silkscreen", "DungGeunMo", monospace'
              : 'bold 24px "Silkscreen", "DungGeunMo", monospace';
            ctx.textAlign = 'center';
            ctx.fillStyle = '#000000';
            ctx.fillText(dp.text, dp.x + 3, dy + 3);
            ctx.fillStyle = dp.color;
            ctx.fillText(dp.text, dp.x, dy);
            ctx.restore();
          }

          ctx.restore();

          if (rawT < 1) {
            requestAnimationFrame(renderFrame);
          } else {
            this._finishArena(onComplete, resolve);
          }
        };

        requestAnimationFrame(renderFrame);
      });
    }

    /**
     * 16-bit 도트 결투장 배경(계단식 하늘 밴드 + 도트 보름달 + 도트 성벽 + 도트 석재 바닥) 렌더링
     */
    _drawPixelArenaBackdrop(ctx, W, H, atkLore, defLore, rawT) {
      // 타격 순간 역전 플래시
      if ((rawT > 0.42 && rawT < 0.45) || (rawT > 0.62 && rawT < 0.65)) {
        ctx.fillStyle = '#fef08a';
        ctx.fillRect(-20, -20, W + 40, H + 40);
        return;
      }

      // 1. 계단식 4밴드 픽셀 밤하늘
      const skyBands = ['#070a14', atkLore.arenaBgTop, defLore.arenaBgBottom, '#1e1b4b'];
      const bandH = Math.ceil((H * 0.70) / skyBands.length);
      for (let i = 0; i < skyBands.length; i++) {
        ctx.fillStyle = skyBands[i];
        ctx.fillRect(-20, i * bandH, W + 40, bandH + 2);
      }

      // 도트 별 & 픽셀 보름달
      ctx.fillStyle = '#fef08a';
      ctx.fillRect(W * 0.5 - 24, 36, 48, 48);
      ctx.fillStyle = '#fde047';
      ctx.fillRect(W * 0.5 - 32, 44, 64, 32);

      // 2. 원경 도트 성벽 실루엣 (Battlements)
      const wallY = Math.round((H * 0.48) / 8) * 8;
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, wallY, W, H * 0.24);
      for (let cx = 0; cx < W; cx += 48) {
        ctx.fillRect(cx, wallY - 20, 28, 20);
      }

      // 3. 도트 석재 타일 결투장 바닥
      const floorY = Math.round((H * 0.70) / 8) * 8;
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(-20, floorY, W + 40, H - floorY + 20);

      // 도트 벽돌 그리드 라인
      ctx.fillStyle = '#0f172a';
      for (let y = floorY; y < H; y += 24) {
        ctx.fillRect(0, y, W, 4);
        const offset = ((y - floorY) / 24) % 2 === 0 ? 0 : 32;
        for (let x = offset; x < W; x += 64) {
          ctx.fillRect(x, y, 4, 24);
        }
      }

      // 상단 골드 픽셀 경계선
      ctx.fillStyle = '#f5b700';
      ctx.fillRect(0, floorY, W, 4);
    }

    _finishArena(onComplete, resolve) {
      if (this._overlayEl) {
        this._overlayEl.classList.remove('bd-active');
      }
      this.isPlaying = false;
      this._skipRequested = false;
      if (typeof onComplete === 'function') onComplete();
      if (typeof resolve === 'function') resolve();
    }
  }

  const BattleDirector = new BattleDirectorController();

  // ============================================================================
  // 모듈 내보내기 (window.BattleDirector, window.SoundFX)
  // ============================================================================

  global.SoundFX = SoundFX;
  global.BattleDirector = BattleDirector;
  global.FACTION_COMBAT_LORE = FACTION_COMBAT_LORE;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SoundFX, BattleDirector, FACTION_COMBAT_LORE };
  }
})(typeof window !== 'undefined' ? window : globalThis);
