/**
 * @fileoverview 중세 배틀 장기 & 중세 배틀 체스 (Medieval Battle Janggi & Chess) - 16-BIT PIXEL ART EDITION 메인 컨트롤러
 * @module window.MedievalJanggiApp
 *
 * 통합 모듈:
 * - window.JanggiEngine   (src/js/janggi_engine.js) : 정통 한국 장기 규칙/판정/점수 엔진 (9x10)
 * - window.JanggiAI       (src/js/ai_engine.js)     : 장기 Minimax + Alpha-Beta + PST 인공지능
 * - window.ChessEngine    (src/js/chess_engine.js)  : 정통 FIDE 서양 체스 규칙/캐슬링/앙파상/프로모션 엔진 (8x8)
 * - window.ChessAI        (src/js/chess_engine.js)  : 체스 Minimax + Alpha-Beta + Quiescence + PST 인공지능
 * - window.ArtRenderer    (src/js/art_renderer.js)  : v3.0 HD 도트 일러스트, 지휘관 초상화 & 배틀 컷인 렌더러
 * - window.BattleDirector (src/js/battle_director.js): 16-bit 도트 배틀체스 시네마틱 연출기
 * - window.SoundFX        (src/js/battle_director.js): 16-bit 칩튠/PCM 절차적 사운드 합성기
 */

(function (global) {
  'use strict';

  const PIECE_RULE_DESCRIPTIONS = Object.freeze({
    // 한국 장기 7병종
    KING: '궁성(3×3) 내부의 직선 및 대각선 선분을 따라 1칸 이동합니다. (체스에서는 8방향 1칸 이동 및 캐슬링 가능)',
    KING_CHESS: '팔방(8방향)으로 1칸 이동하며, 룩과 함께 왕실 성루 교차 기동인 캐슬링(O-O / O-O-O)을 수행할 수 있습니다.',
    CHARIOT: '가로·세로 직선 무제한 돌파 및 궁성 대각선 직선 이동이 가능한 13점 결전병기입니다.',
    CANNON: '직선 및 궁성 대각선에서 반드시 포가 아닌 기물 1개(다리)를 넘어서 이동·타격합니다. (포불넘포·포불장포)',
    HORSE: '직선 1칸(멱)이 비어 있을 때 대각선 1칸(날일자 日)으로 기동하는 5점 기병입니다.',
    ELEPHANT: '직선 1칸(제1멱)과 대각선 1칸(제2멱)이 비어 있을 때 용일자(用)로 도약하는 3점 거수입니다.',
    GUARD: '궁성(3×3) 내부에서 직선 및 대각선 1칸 이동하며 군주를 밀착 호위하는 3점 근위대입니다.',
    SOLDIER: '전진 및 좌우 1칸 이동(후퇴 불가)하며, 적 궁성 진입 시 대각선 전진이 가능한 2점 전열보병입니다.',
    // 서양 체스 전용 병종
    QUEEN: '상하좌우 직선과 4대각선 8방향으로 무제한 기동하며 전장을 지배하는 9점 최강 결전병기입니다.',
    ROOK: '상하좌우 직선 파일을 무제한 돌파하며, 킹과 함께 캐슬링(성루 교차)을 수행하는 5점 공성 거병입니다.',
    BISHOP: '긴 대각선 회랑을 무제한 가로지르며 원거리 신벌 타격을 가하는 3점 대주교/마법사입니다.',
    KNIGHT: '주변 기물을 뛰어넘어 L자(날일자) 8방향으로 도약 기습하는 3점 중장철기병입니다.',
    PAWN: '전방 1칸(초기 2칸) 전진 및 대각선 포획을 수행하며, 끝 랭크 도달 시 퀸/룩/비숍/나이트로 승진(Promotion)합니다. (앙파상 가능)'
  });

  function detectInitialGameType() {
    if (global.INITIAL_GAME_TYPE && String(global.INITIAL_GAME_TYPE).toUpperCase() === 'CHESS') {
      return 'CHESS';
    }
    try {
      if (global.location && global.location.search) {
        const params = new URLSearchParams(global.location.search);
        const gParam = (params.get('game') || params.get('mode') || '').toUpperCase();
        if (gParam === 'CHESS') return 'CHESS';
        if (gParam === 'JANGGI') return 'JANGGI';
      }
    } catch (e) {
      // ignore URL parse error
    }
    return 'JANGGI';
  }

  class MedievalJanggiController {
    constructor() {
      this.boardGameType = detectInitialGameType(); // 'JANGGI' | 'CHESS'
      this.Engine = this.boardGameType === 'CHESS' && global.ChessEngine ? global.ChessEngine : global.JanggiEngine;
      this.AI = this.boardGameType === 'CHESS' && global.ChessAI ? global.ChessAI : global.JanggiAI;
      this.Art = global.ArtRenderer;
      this.Director = global.BattleDirector;
      this.SFX = global.SoundFX;

      // 대국 설정 상태
      this.gameMode = '1P_AI';       // '1P_AI' | '2P_LOCAL' | 'AI_VS_AI'
      this.humanSide = 'CHU';        // 1P 기본 진영: 초/백(선공)
      this.aiDifficulty = 'NORMAL';  // 'EASY' | 'NORMAL' | 'HARD'
      this.chuSkin = 'GORYEO';       // 초/백 기본 스킨: 고려 천군
      this.hanSkin = 'TEMPLAR';      // 한/흑 기본 스킨: 성전 기사단
      this.chuFormation = 'INNER';   // 초/백 상차림(진형)
      this.hanFormation = this.boardGameType === 'CHESS' ? 'INNER' : 'OUTER';
      this.boardFlipped = false;     // 시점 반전 여부

      // 게임 엔진 인스턴스 생성
      this.game = this.Engine.createGame({
        chuFormation: this.chuFormation,
        hanFormation: this.hanFormation,
        chuSkin: this.chuSkin,
        hanSkin: this.hanSkin
      });

      // 인터랙션 및 애니메이션 상태
      this.selectedCoord = null;     // { x, y }
      this.inspectedPiece = null;    // 인스펙터 프리뷰 대상 기물
      this.legalMeta = { moves: [], blockedNecks: [], bridges: [] };
      this.hoveredCoord = null;
      this.isBusy = false;           // 행군/배틀 시네마틱 또는 AI 연산 중 입력 잠금
      this.marchAnim = null;         // { piece, fromX, fromY, toX, toY, rookPiece, rookFromX, rookToX, rookY, startTime, duration }
      this.touchLoupe = { active: false, px: 0, py: 0, coord: null };
      this._pendingPromotionResolve = null;

      // 모달 상태 (정예병 도감 & 배틀 쇼케이스)
      this.codexFaction = 'GORYEO';
      this.codexGameFilter = 'ALL'; // 'ALL' | 'JANGGI' | 'CHESS'
      this.codexPose = 'IDLE';
      this.codexCanvases = [];
      this.showcaseState = {
        playing: false,
        startTime: 0,
        duration: 2100,
        atkFaction: 'GORYEO',
        atkType: this.boardGameType === 'CHESS' ? 'QUEEN' : 'CANNON',
        defFaction: 'TEMPLAR',
        defType: this.boardGameType === 'CHESS' ? 'ROOK' : 'CHARIOT'
      };

      // 보드 지오메트리 상수 (780 x 860 캔버스 기준, 4px 픽셀 그리드 정렬 & 2.5D 원근 투영)
      this.canvasWidth = 780;
      this.canvasHeight = 860;
      this.padX = 68;
      this.padY = 68;
      this.cellW = 80;
      this.cellH = 80;
      this.renderScale = 2.5; // QHD/FHD 모니터에서 240x240 HD 도트 원화가 뭉개지지 않도록 2.5~3배 슈퍼샘플링
      this._pixelBoardCache = null;
      this._pixelBoardCacheKey = '';
      this.boardFxList = []; // 보드 표면 위 실시간 충격파/파편/번개 임팩트 큐
      this._lastRenderSignature = '';
      this._forceRedraw = true;

      // 내 컴퓨터 기준 해상도 · 보드 디자인 · 사운드 옵션 상태 (뿌연 스캔라인 기본 OFF, 2.5D 기본 ON)
      this.userSettings = {
        resolutionPreset: 'AUTO_NATIVE',
        boardScalePercent: 100,
        uiScalePercent: 100,
        boardTheme: 'ROYAL_OAK',
        boardViewMode: '2.5D',
        crtScanline: 'OFF',
        soundEnabled: true,
        masterVolume: 75,
        bgmVolume: 55,
        sfxVolume: 85,
        battleVolume: 90,
        bgmTrack: 'GORYEO_MARCH'
      };
    }

    _setupHiDPICanvas(canvas, logicalW, logicalH, minScale = 2.5) {
      if (!canvas) return null;
      const dpr = (typeof global.devicePixelRatio === 'number' && global.devicePixelRatio > 0)
        ? global.devicePixelRatio
        : 1;
      const isMobileViewport = (global.innerWidth || 1920) <= 960;
      const scale = isMobileViewport
        ? Math.max(2, Math.min(2.5, dpr))
        : Math.max(minScale, Math.min(3, dpr * 2));
      canvas.width = Math.round(logicalW * scale);
      canvas.height = Math.round(logicalH * scale);
      canvas._logicalWidth = logicalW;
      canvas._logicalHeight = logicalH;
      canvas._renderScale = scale;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.setTransform(scale, 0, 0, scale, 0, 0);
      }
      return ctx;
    }

    isChessMode() {
      return this.boardGameType === 'CHESS';
    }

    getBoardCols() {
      return this.isChessMode() ? 8 : 9;
    }

    getBoardRows() {
      return this.isChessMode() ? 8 : 10;
    }

    init() {
      this.boardCanvas = document.getElementById('janggi-board-canvas');
      this.boardCtx = this._setupHiDPICanvas(this.boardCanvas, this.canvasWidth, this.canvasHeight, 2.5);
      if (this.boardCanvas && this.boardCanvas._renderScale) {
        this.renderScale = this.boardCanvas._renderScale;
      }

      this.inspectorCanvas = document.getElementById('selected-unit-canvas');
      this.inspectorCtx = this._setupHiDPICanvas(this.inspectorCanvas, 88, 88, 2.5);

      this.chuEmblemCanvas = document.getElementById('chu-emblem-canvas');
      this._setupHiDPICanvas(this.chuEmblemCanvas, 54, 54, 2.5);
      this.hanEmblemCanvas = document.getElementById('han-emblem-canvas');
      this._setupHiDPICanvas(this.hanEmblemCanvas, 54, 54, 2.5);

      this.showcaseCanvas = document.getElementById('showcase-stage-canvas');
      this.showcaseCtx = this._setupHiDPICanvas(this.showcaseCanvas, 920, 500, 2.0);

      this._loadUserSettings();
      if (!this.userSettings.boardViewMode) {
        this.userSettings.boardViewMode = '2.5D';
      }
      if (this.Director) {
        this.Director.setMode('BOARD_ZOOM');
      }

      this._bindEvents();
      this._bindSettingsEvents();
      this._bindPromotionModalEvents();
      this._initCodexGrid();
      this._applyAllUserSettings(false);
      this._sync3DViewButtonUI();
      this._syncGameTypeUI();

      // 초기 인스펙터 기본 기물 설정
      this.inspectedPiece = this.isChessMode()
        ? (this.game.getPieceAt(3, 7) || this.game.getPieceAt(4, 7))
        : (this.game.getPieceAt(0, 9) || this.game.getPieceAt(4, 8));
      this.updateHUD();
      this.updateInspectorText();

      // 60fps 메인 렌더링 루프 가동 (더티 체킹 및 도트 스텝 타이밍 포함)
      const loop = (now) => {
        this.render(now);
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    }

    // ==========================================================================
    // 장기(JANGGI) <-> 체스(CHESS) 듀얼 코어 실시간 전환
    // ==========================================================================

    switchGameType(targetType) {
      const normalized = String(targetType || 'JANGGI').toUpperCase() === 'CHESS' ? 'CHESS' : 'JANGGI';
      if (normalized === 'CHESS' && !global.ChessEngine) return;

      this.boardGameType = normalized;
      if (this.isChessMode()) {
        this.Engine = global.ChessEngine;
        this.AI = global.ChessAI;
        this.chuFormation = 'INNER';
        this.hanFormation = 'INNER';
      } else {
        this.Engine = global.JanggiEngine;
        this.AI = global.JanggiAI;
        this.chuFormation = 'INNER';
        this.hanFormation = 'OUTER';
      }

      this.game = this.Engine.createGame({
        chuFormation: this.chuFormation,
        hanFormation: this.hanFormation,
        chuSkin: this.chuSkin,
        hanSkin: this.hanSkin
      });

      this._pixelBoardCache = null;
      this._forceRedraw = true;
      this._syncGameTypeUI();
      this.startNewGame();
    }

    _syncGameTypeUI() {
      const isChess = this.isChessMode();

      const btnJanggi = document.getElementById('btn-switch-janggi');
      const btnChess = document.getElementById('btn-switch-chess');
      if (btnJanggi) btnJanggi.classList.toggle('active', !isChess);
      if (btnChess) btnChess.classList.toggle('active', isChess);

      const crest = document.getElementById('brand-crest-icon');
      const mainTitle = document.getElementById('app-main-title');
      const subTitle = document.getElementById('app-sub-title');
      if (crest) crest.textContent = isChess ? '♔' : '將';
      if (mainTitle) {
        mainTitle.textContent = isChess ? '중세 배틀 체스' : '중세 배틀체스 장기';
      }
      if (subTitle) {
        subTitle.textContent = isChess
          ? '정통 FIDE 서양체스 × 4대 중세 도트 정예병 스킨'
          : '정통 한국장기 & 서양체스 × 4대 중세 도트 정예병 스킨';
      }

      const setText = (id, text) => {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
      };

      setText('han-side-badge', isChess ? '흑(BLACK) · 상단 진영 · 후공' : '한(漢) · 상단 진영 · 후공');
      setText('chu-side-badge', isChess ? '백(WHITE) · 하단 진영 · 선공' : '초(楚) · 하단 진영 · 선공');
      setText('han-captured-label', isChess ? '⚔️ 흑(BLACK)이 포획한 백(WHITE) 기물' : '⚔️ 한(漢)이 포획한 초(楚) 기물');
      setText('chu-captured-label', isChess ? '⚔️ 백(WHITE)이 포획한 흑(BLACK) 기물' : '⚔️ 초(楚)가 포획한 한(漢) 기물');
      setText('power-chu-label', isChess ? '백(WHITE) 전력' : '초(楚) 전력');
      setText('power-han-label', isChess ? '흑(BLACK) 전력' : '한(漢) 전력');
      setText('label-chu-skin', isChess ? '🟦 백(WHITE · 하단 선공) 국가 정예병 테마' : '🟦 초(楚 · 하단 선공) 국가 정예병 테마');
      setText('label-han-skin', isChess ? '🟥 흑(BLACK · 상단 후공) 국가 정예병 테마' : '🟥 한(漢 · 상단 후공) 국가 정예병 테마');
      setText('panel-mode-title', isChess ? '⚙️ 대국 모드 · AI 난이도 · 오프닝 진형' : '⚙️ 대국 모드 · AI 난이도 · 4대 상차림');
      setText('opt-mode-1p', isChess ? '1P(백) vs AI(흑)' : '1P(초) vs AI(한)');
      setText('label-chu-formation', isChess ? '백(WHITE) 진형' : '초(楚) 상차림');
      setText('label-han-formation', isChess ? '흑(BLACK) 진형' : '한(漢) 상차림');

      // 상차림 / 체스 진형 드롭다운 옵션 갱신
      const populateFormationSelect = (selId, selectedVal) => {
        const sel = document.getElementById(selId);
        if (!sel) return;
        if (isChess) {
          sel.innerHTML = `
            <option value="INNER">정통 FIDE 표준 (RNBQKBNR)</option>
            <option value="OUTER">기사단 선봉 (RBNQKNBR)</option>
            <option value="LEFT">퀸사이드 기동 (RBNQKBNR)</option>
            <option value="RIGHT">킹사이드 기동 (RNBQKNBR)</option>
          `;
        } else {
          sel.innerHTML = `
            <option value="INNER">내상 (마·상·상·마)</option>
            <option value="OUTER">외상 (상·마·마·상)</option>
            <option value="LEFT">왼상 (상·마·상·마)</option>
            <option value="RIGHT">오른상 (마·상·마·상)</option>
          `;
        }
        sel.value = selectedVal;
      };
      populateFormationSelect('chu-formation-select', this.chuFormation);
      populateFormationSelect('han-formation-select', this.hanFormation);

      const passBtn = document.getElementById('btn-pass-turn');
      if (passBtn) {
        passBtn.style.display = isChess ? 'none' : '';
        passBtn.textContent = '⏭️ 한수 쉼';
        passBtn.title = '장군 상태가 아닐 때 차례를 한 번 넘깁니다';
      }

      const bikjangBtn = document.getElementById('btn-declare-bikjang');
      if (bikjangBtn) {
        bikjangBtn.style.display = isChess ? 'none' : '';
      }
    }

    // ==========================================================================
    // 좌표 변환 (장기 9x10 교차점 & 체스 8x8 타일 중앙 <-> 2.5D/2D 픽셀 좌표)
    // ==========================================================================

    is3DView() {
      return !this.userSettings || this.userSettings.boardViewMode !== '2D';
    }

    _sync3DViewButtonUI() {
      const btn = document.getElementById('btn-toggle-3d-view');
      if (!btn) return;
      if (this.is3DView()) {
        btn.textContent = '🧊 2.5D 입체';
        btn.className = 'btn btn-emerald';
      } else {
        btn.textContent = '🗺️ 2D 평면';
        btn.className = 'btn';
      }
    }

    /**
     * 시각적 보드 좌표 -> 캔버스 픽셀 (px, py) 및 원근 스케일(scale)
     * - 장기(JANGGI): vx ∈ [0..8], vy ∈ [0..9] (격자 교차점 기준)
     * - 체스(CHESS): vx ∈ [0..7], vy ∈ [0..7] (타일 정중앙 기준; 타일 경계는 -0.5 ~ 7.5)
     */
    _projectVisualCoord(vx, vy) {
      if (this.isChessMode()) {
        if (!this.is3DView()) {
          const originX = 70; // 70 + 8 * 80 = 710
          const originY = 110; // 110 + 8 * 80 = 750
          const tileSize = 80;
          return {
            px: Math.round((originX + (vx + 0.5) * tileSize) / 2) * 2,
            py: Math.round((originY + (vy + 0.5) * tileSize) / 2) * 2,
            scale: 1.0
          };
        }

        const S_TOP = 0.75;
        const S_BOT = 1.05;
        const Y_TOP = 124;
        const Y_BOT = 720;
        const BASE_TILE_W = 84;
        const CX = this.canvasWidth / 2; // 390

        const t = (vy + 0.5) / 8;
        const denom = S_BOT - (S_BOT - S_TOP) * t;
        const u = Math.abs(denom) > 1e-5 ? (t * S_TOP) / denom : t;
        const scale = S_TOP + (S_BOT - S_TOP) * u;
        const py = Y_TOP + (Y_BOT - Y_TOP) * u;
        const px = CX + (vx - 3.5) * BASE_TILE_W * scale;

        return {
          px: Math.round(px / 2) * 2,
          py: Math.round(py / 2) * 2,
          scale
        };
      }

      if (!this.is3DView()) {
        return {
          px: Math.round((this.padX + vx * this.cellW) / 2) * 2,
          py: Math.round((this.padY + vy * this.cellH) / 2) * 2,
          scale: 1.0
        };
      }

      const S_TOP = 0.74;
      const S_BOT = 1.04;
      const Y_TOP = 114;
      const Y_BOT = 726;
      const BASE_CELL_W = 78;
      const CX = this.canvasWidth / 2; // 390

      const t = vy / 9;
      const denom = S_BOT - (S_BOT - S_TOP) * t;
      const u = Math.abs(denom) > 1e-5 ? (t * S_TOP) / denom : t;
      const scale = S_TOP + (S_BOT - S_TOP) * u;
      const py = Y_TOP + (Y_BOT - Y_TOP) * u;
      const px = CX + (vx - 4) * BASE_CELL_W * scale;

      return {
        px: Math.round(px / 2) * 2,
        py: Math.round(py / 2) * 2,
        scale
      };
    }

    /**
     * 캔버스 픽셀 (px, py) -> 시각적 보드 연속 좌표 (vx, vy, scale) 역투영
     */
    _unprojectPixelToVisual(px, py) {
      if (this.isChessMode()) {
        if (!this.is3DView()) {
          const originX = 70;
          const originY = 110;
          const tileSize = 80;
          return {
            vx: (px - originX) / tileSize - 0.5,
            vy: (py - originY) / tileSize - 0.5,
            scale: 1.0
          };
        }

        const S_TOP = 0.75;
        const S_BOT = 1.05;
        const Y_TOP = 124;
        const Y_BOT = 720;
        const BASE_TILE_W = 84;
        const CX = this.canvasWidth / 2;

        const u = (py - Y_TOP) / (Y_BOT - Y_TOP);
        const scale = S_TOP + (S_BOT - S_TOP) * u;
        if (scale <= 0.15) {
          return { vx: -99, vy: -99, scale: 0.15 };
        }
        const vx = 3.5 + (px - CX) / (BASE_TILE_W * scale);
        const t = (u * S_BOT) / scale;
        const vy = t * 8 - 0.5;
        return { vx, vy, scale };
      }

      if (!this.is3DView()) {
        return {
          vx: (px - this.padX) / this.cellW,
          vy: (py - this.padY) / this.cellH,
          scale: 1.0
        };
      }

      const S_TOP = 0.74;
      const S_BOT = 1.04;
      const Y_TOP = 114;
      const Y_BOT = 726;
      const BASE_CELL_W = 78;
      const CX = this.canvasWidth / 2;

      const u = (py - Y_TOP) / (Y_BOT - Y_TOP);
      const scale = S_TOP + (S_BOT - S_TOP) * u;
      if (scale <= 0.15) {
        return { vx: -99, vy: -99, scale: 0.15 };
      }
      const vx = 4 + (px - CX) / (BASE_CELL_W * scale);
      const t = (u * S_BOT) / scale;
      const vy = t * 9;
      return { vx, vy, scale };
    }

    boardToPixel(bx, by) {
      const maxCol = this.getBoardCols() - 1;
      const maxRow = this.getBoardRows() - 1;
      const vx = this.boardFlipped ? maxCol - bx : bx;
      const vy = this.boardFlipped ? maxRow - by : by;
      return this._projectVisualCoord(vx, vy);
    }

    pixelToBoard(px, py) {
      const maxCol = this.getBoardCols() - 1;
      const maxRow = this.getBoardRows() - 1;

      if (!this.is3DView()) {
        const unproj = this._unprojectPixelToVisual(px, py);
        const vx = Math.round(unproj.vx);
        const vy = Math.round(unproj.vy);
        if (vx < 0 || vx > maxCol || vy < 0 || vy > maxRow) return null;

        const pt = this._projectVisualCoord(vx, vy);
        const dist = Math.hypot(px - pt.px, py - pt.py);
        if (dist > this.cellW * 0.55) return null;

        const bx = this.boardFlipped ? maxCol - vx : vx;
        const by = this.boardFlipped ? maxRow - vy : vy;
        return { x: bx, y: by };
      }

      // 1. 앞열(maxRow)부터 뒷열(0) 순으로 서 있는 HD-2D 입간판 기물 몸체 클릭 여부 우선 판정
      for (let vy = maxRow; vy >= 0; vy--) {
        for (let vx = 0; vx <= maxCol; vx++) {
          const bx = this.boardFlipped ? maxCol - vx : vx;
          const by = this.boardFlipped ? maxRow - vy : vy;
          const p = this.game.getPieceAt(bx, by);
          if (!p) continue;
          const pt = this._projectVisualCoord(vx, vy);
          const s = pt.scale;
          const dx = Math.abs(px - pt.px);
          const dy = py - pt.py;
          if (dx <= 33 * s && dy >= -54 * s && dy <= 24 * s) {
            return { x: bx, y: by };
          }
        }
      }

      // 2. 바닥 그리드/타일 원근 역투영 판정
      const unproj = this._unprojectPixelToVisual(px, py);
      const vx = Math.round(unproj.vx);
      const vy = Math.round(unproj.vy);
      if (vx < 0 || vx > maxCol || vy < 0 || vy > maxRow) return null;

      const pt = this._projectVisualCoord(vx, vy);
      const hitRadiusX = (this.isChessMode() ? 44 : 38) * pt.scale;
      const hitRadiusY = (this.isChessMode() ? 38 : 32) * pt.scale;
      const normDist = Math.hypot((px - pt.px) / hitRadiusX, (py - pt.py) / hitRadiusY);
      if (normDist > 1.15) return null;

      const bx = this.boardFlipped ? maxCol - vx : vx;
      const by = this.boardFlipped ? maxRow - vy : vy;
      return { x: bx, y: by };
    }

    /**
     * 모바일 손가락 터치(Fat-Finger) 자석 스냅 보정:
     * 터치 위치 근처에 합법 착수점이나 현재 턴 아군 기물이 있으면 반경 내 가장 가까운 칸으로 스냅
     */
    _resolveMagneticTouchCoord(px, py, isTouch = false) {
      const direct = this.pixelToBoard(px, py);
      if (!isTouch && direct) return direct;

      const snapRadius = isTouch ? 56 : 36;
      let bestCoord = direct;
      let bestDist = Infinity;

      // 1. 기물이 선택된 상태라면 합법 착수 목적지(moves)에 우선 자석 스냅
      if (this.selectedCoord && this.legalMeta && this.legalMeta.moves.length > 0) {
        for (let i = 0; i < this.legalMeta.moves.length; i++) {
          const mv = this.legalMeta.moves[i];
          const pt = this.boardToPixel(mv.toX, mv.toY);
          const d = Math.hypot(px - pt.px, py - pt.py);
          if (d <= snapRadius && d < bestDist) {
            bestDist = d;
            bestCoord = { x: mv.toX, y: mv.toY };
          }
        }
        if (bestCoord && bestDist <= snapRadius) return bestCoord;
      }

      // 2. 현재 차례 아군 기물에 자석 스냅
      const cols = this.getBoardCols();
      const rows = this.getBoardRows();
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const p = this.game.getPieceAt(x, y);
          if (!p || p.side !== this.game.currentTurn) continue;
          const pt = this.boardToPixel(x, y);
          const d = Math.hypot(px - pt.px, py - (pt.py - 12 * pt.scale));
          if (d <= snapRadius && d < bestDist) {
            bestDist = d;
            bestCoord = { x, y };
          }
        }
      }

      return bestCoord || direct;
    }

    getSkinForSide(side) {
      return side === this.Engine.SIDES.CHU ? this.chuSkin : this.hanSkin;
    }

    // ==========================================================================
    // 이벤트 바인딩 (게임 스위처, 모바일 터치 루페, 모바일 드로어 포함)
    // ==========================================================================

    _bindEvents() {
      if (this.boardCanvas) {
        this.boardCanvas.addEventListener('click', (e) => this._onBoardClick(e));
        this.boardCanvas.addEventListener('mousemove', (e) => this._onBoardHover(e));
        this.boardCanvas.addEventListener('mouseleave', () => {
          this.hoveredCoord = null;
          this._forceRedraw = true;
        });

        // 모바일 & 갤럭시 폴드 터치: 스크롤 제스처와 기물 탭(착수)을 정밀 구분하여 스크롤 먹통 방지
        this._touchGesture = null;

        this.boardCanvas.addEventListener(
          'touchstart',
          (e) => {
            if (!e.touches || e.touches.length !== 1) {
              this._touchGesture = null;
              this.touchLoupe.active = false;
              return;
            }
            const t = e.touches[0];
            const pos = this._getCanvasClientPos(t.clientX, t.clientY);
            const coord = this._resolveMagneticTouchCoord(pos.px, pos.py, true);
            this._touchGesture = {
              startX: t.clientX,
              startY: t.clientY,
              px: pos.px,
              py: pos.py,
              coord,
              isScroll: false
            };
            this.hoveredCoord = coord;
            this._forceRedraw = true;
          },
          { passive: true }
        );

        this.boardCanvas.addEventListener(
          'touchmove',
          (e) => {
            if (!this._touchGesture || !e.touches || e.touches.length !== 1) return;
            const t = e.touches[0];
            const dx = Math.abs(t.clientX - this._touchGesture.startX);
            const dy = Math.abs(t.clientY - this._touchGesture.startY);

            // 손가락이 9px 이상 움직이면 화면 스크롤 제스처로 판정 -> 루페 해제 & 브라우저 기본 스크롤 허용
            if (dx > 9 || dy > 9) {
              this._touchGesture.isScroll = true;
              if (this.touchLoupe.active) {
                this.touchLoupe.active = false;
                this._forceRedraw = true;
              }
              return;
            }

            const pos = this._getCanvasClientPos(t.clientX, t.clientY);
            const coord = this._resolveMagneticTouchCoord(pos.px, pos.py, true);
            this._touchGesture.px = pos.px;
            this._touchGesture.py = pos.py;
            this._touchGesture.coord = coord;
            this.hoveredCoord = coord;
            this._forceRedraw = true;
          },
          { passive: true }
        );

        this.boardCanvas.addEventListener('touchend', (e) => {
          const gesture = this._touchGesture;
          this._touchGesture = null;
          this.touchLoupe.active = false;
          this._forceRedraw = true;

          // 스크롤 동작이었으면 기물 클릭을 실행하지 않고 네이티브 스크롤 유지
          if (!gesture || gesture.isScroll) return;

          if (e.cancelable) e.preventDefault();
          this._handleBoardPointerAction(gesture.px, gesture.py, true);
        });

        this.boardCanvas.addEventListener('touchcancel', () => {
          this._touchGesture = null;
          this.touchLoupe.active = false;
          this._forceRedraw = true;
        });
      }

      const bindClick = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', fn);
      };

      // 장기 <-> 체스 상단 전환 버튼
      bindClick('btn-switch-janggi', () => {
        if (this.boardGameType !== 'JANGGI') {
          this.SFX.playSelect();
          this.switchGameType('JANGGI');
        }
      });
      bindClick('btn-switch-chess', () => {
        if (this.boardGameType !== 'CHESS') {
          this.SFX.playSelect();
          this.switchGameType('CHESS');
        }
      });

      // 모바일 바텀 시트 드로어 토글
      const toggleMobileDrawer = (open) => {
        const drawer = document.getElementById('right-settings-drawer');
        const backdrop = document.getElementById('mobile-drawer-backdrop');
        if (drawer) drawer.classList.toggle('open', open);
        if (backdrop) backdrop.classList.toggle('open', open);
      };
      bindClick('btn-mobile-drawer-toggle', () => {
        this.SFX.playSelect();
        const drawer = document.getElementById('right-settings-drawer');
        const isOpen = drawer ? drawer.classList.contains('open') : false;
        toggleMobileDrawer(!isOpen);
      });
      bindClick('btn-close-mobile-drawer', () => toggleMobileDrawer(false));
      bindClick('mobile-drawer-backdrop', () => toggleMobileDrawer(false));

      const chuSkinSel = document.getElementById('chu-skin-select');
      if (chuSkinSel) {
        chuSkinSel.addEventListener('change', (e) => {
          this.chuSkin = e.target.value;
          this.game.chuSkin = this.chuSkin;
          this._pixelBoardCache = null;
          this._forceRedraw = true;
          this.SFX.playSelect();
          this.updateHUD();
          this.updateInspectorText();
        });
      }

      const hanSkinSel = document.getElementById('han-skin-select');
      if (hanSkinSel) {
        hanSkinSel.addEventListener('change', (e) => {
          this.hanSkin = e.target.value;
          this.game.hanSkin = this.hanSkin;
          this._pixelBoardCache = null;
          this._forceRedraw = true;
          this.SFX.playSelect();
          this.updateHUD();
          this.updateInspectorText();
        });
      }

      const modeSel = document.getElementById('game-mode-select');
      if (modeSel) {
        modeSel.addEventListener('change', (e) => {
          this.gameMode = e.target.value;
          this.SFX.playSelect();
          this.checkAndTriggerAITurn();
        });
      }

      const diffSel = document.getElementById('ai-difficulty-select');
      if (diffSel) {
        diffSel.addEventListener('change', (e) => {
          this.aiDifficulty = e.target.value;
          this.SFX.playSelect();
        });
      }

      const chuFormSel = document.getElementById('chu-formation-select');
      if (chuFormSel) {
        chuFormSel.addEventListener('change', (e) => {
          this.chuFormation = e.target.value;
        });
      }

      const hanFormSel = document.getElementById('han-formation-select');
      if (hanFormSel) {
        hanFormSel.addEventListener('change', (e) => {
          this.hanFormation = e.target.value;
        });
      }

      const cineBtns = document.querySelectorAll('[data-cinematic-mode]');
      cineBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          cineBtns.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          const mode = btn.getAttribute('data-cinematic-mode');
          this.Director.setMode(mode);
          this.SFX.playSelect();
        });
      });

      bindClick('btn-new-game', () => {
        toggleMobileDrawer(false);
        this.startNewGame();
      });
      bindClick('btn-new-game-top', () => this.startNewGame());
      bindClick('btn-modal-rematch', () => {
        this.closeModal('gameover-modal');
        this.startNewGame();
      });

      bindClick('btn-pass-turn', () => this.handlePassTurn());
      bindClick('btn-undo-move', () => this.handleUndoMove());
      bindClick('btn-declare-bikjang', () => this.handleDeclareBikjang());
      bindClick('btn-score-decision', () => {
        toggleMobileDrawer(false);
        this.handleScoreDecision();
      });
      bindClick('btn-flip-board', () => {
        this.boardFlipped = !this.boardFlipped;
        this._pixelBoardCache = null;
        this._forceRedraw = true;
        this.SFX.playSelect();
      });
      bindClick('btn-toggle-3d-view', () => {
        this.userSettings.boardViewMode = this.is3DView() ? '2D' : '2.5D';
        this._pixelBoardCache = null;
        this._forceRedraw = true;
        this._sync3DViewButtonUI();
        this._saveUserSettings();
        this.SFX.playSelect();
        this.setBriefingText(
          this.is3DView()
            ? '🧊 [2.5D 입체 틸트 보드 + HD-2D 입간판 기물] 시점이 활성화되었습니다.'
            : '🗺️ [2D 클래식 평면 보드] 시점으로 전환되었습니다.'
        );
      });

      bindClick('btn-toggle-sound', () => {
        const enabled = this.SFX.toggleMute();
        this.userSettings.soundEnabled = enabled;
        this._syncSettingsUIFromState();
        this._saveUserSettings();
      });

      const openGuideAndCodex = () => {
        toggleMobileDrawer(false);
        this.SFX.playSelect();
        this.updateInspectorText();
        this.openModal('codex-modal');
      };

      bindClick('btn-open-codex', openGuideAndCodex);
      bindClick('btn-open-guide-bottom', openGuideAndCodex);
      bindClick('btn-open-codex-side', openGuideAndCodex);
      bindClick('btn-close-codex', () => this.closeModal('codex-modal'));

      bindClick('btn-open-showcase', () => {
        this.SFX.playSelect();
        this.openModal('showcase-modal');
        this.triggerShowcaseReplay();
      });
      bindClick('btn-open-showcase-side', () => {
        toggleMobileDrawer(false);
        this.SFX.playSelect();
        this.openModal('showcase-modal');
        this.triggerShowcaseReplay();
      });
      bindClick('btn-close-showcase', () => this.closeModal('showcase-modal'));
      bindClick('btn-close-gameover', () => this.closeModal('gameover-modal'));

      bindClick('btn-showcase-play-stage', () => this.triggerShowcaseReplay());
      bindClick('btn-showcase-play-arena', () => this.triggerFullArenaShowcase());
    }

    // ==========================================================================
    // 체스 폰 프로모션(승진 각성) 선택 모달 제어
    // ==========================================================================

    _bindPromotionModalEvents() {
      const cards = document.querySelectorAll('[data-promo-choice]');
      cards.forEach((card) => {
        card.addEventListener('click', () => {
          const choice = card.getAttribute('data-promo-choice') || 'QUEEN';
          this.closeModal('promotion-modal');
          if (typeof this._pendingPromotionResolve === 'function') {
            const resolve = this._pendingPromotionResolve;
            this._pendingPromotionResolve = null;
            resolve(choice);
          }
        });
      });
    }

    _promptPromotionChoice(side) {
      return new Promise((resolve) => {
        this._pendingPromotionResolve = resolve;
        const skinId = this.getSkinForSide(side);
        const promoCanvases = document.querySelectorAll('#promotion-card-grid canvas[data-promo-type]');
        promoCanvases.forEach((cvs) => {
          const type = cvs.getAttribute('data-promo-type');
          const logW = 88;
          const logH = 88;
          const ctx = this._setupHiDPICanvas(cvs, logW, logH, 2.5);
          ctx.clearRect(0, 0, logW, logH);
          this.Art.drawUnit(ctx, {
            x: logW / 2,
            y: logH * 0.75,
            type,
            side,
            faction: skinId,
            state: 'IDLE',
            progress: 0,
            time: 0,
            scale: 1.05,
            facing: 1,
            showPedestal: true
          });
        });
        this.SFX.playSelect();
        this.openModal('promotion-modal');
      });
    }

    // ==========================================================================
    // 내 컴퓨터 기준 해상도 · 보드 디자인 · 사운드 옵션 시스템
    // ==========================================================================

    _loadUserSettings() {
      try {
        const raw = global.localStorage ? global.localStorage.getItem('medieval_janggi_settings_v2') : null;
        if (raw) {
          const parsed = JSON.parse(raw);
          Object.assign(this.userSettings, parsed);
        }
      } catch (e) {
        // localStorage 접근 불가 시 기본값 유지
      }
    }

    _saveUserSettings() {
      try {
        if (global.localStorage) {
          global.localStorage.setItem('medieval_janggi_settings_v2', JSON.stringify(this.userSettings));
        }
      } catch (e) {
        // ignore
      }
    }

    _detectComputerResolutionInfo() {
      const sw = (global.screen && global.screen.width) ? global.screen.width : 2560;
      const sh = (global.screen && global.screen.height) ? global.screen.height : 1440;
      const dpr = global.devicePixelRatio || 1;
      const vw = global.innerWidth || sw;
      const vh = global.innerHeight || sh;

      let label = `${sw}×${sh}`;
      if (sw >= 2500) label = `${sw}×${sh} (QHD 16:9)`;
      else if (sw >= 2000) label = `${sw}×${sh} (QHD+ 16:9)`;
      else if (sw >= 1900) label = `${sw}×${sh} (FHD 16:9)`;

      return { sw, sh, vw, vh, dpr, label };
    }

    _computePresetDimensions(preset) {
      const info = this._detectComputerResolutionInfo();
      let targetW = info.sw;
      let targetH = info.sh;

      if (preset === '2560x1440') { targetW = 2560; targetH = 1440; }
      else if (preset === '2048x1152') { targetW = 2048; targetH = 1152; }
      else if (preset === '1920x1080') { targetW = 1920; targetH = 1080; }
      else if (preset === '1600x900') { targetW = 1600; targetH = 900; }
      else if (preset === '1366x768') { targetW = 1366; targetH = 768; }

      let baseBoardW = 700;
      let maxWorkspaceW = 1660;
      let leftColW = 340;
      let rightColW = 360;

      if (targetW >= 2500) {
        baseBoardW = 780;
        maxWorkspaceW = 1960;
        leftColW = 370;
        rightColW = 400;
      } else if (targetW >= 2000) {
        baseBoardW = 750;
        maxWorkspaceW = 1780;
        leftColW = 350;
        rightColW = 375;
      } else if (targetW >= 1900) {
        baseBoardW = 700;
        maxWorkspaceW = 1660;
        leftColW = 335;
        rightColW = 360;
      } else if (targetW >= 1550) {
        baseBoardW = 600;
        maxWorkspaceW = 1480;
        leftColW = 310;
        rightColW = 335;
      } else {
        baseBoardW = 520;
        maxWorkspaceW = 1320;
        leftColW = 290;
        rightColW = 310;
      }

      return { targetW, targetH, baseBoardW, maxWorkspaceW, leftColW, rightColW, info };
    }

    _applyAllUserSettings(playFeedback = false) {
      const s = this.userSettings;
      const dims = this._computePresetDimensions(s.resolutionPreset);
      const scaledBoardW = Math.round(dims.baseBoardW * (s.boardScalePercent / 100));
      const uiZoom = Number((s.uiScalePercent / 100).toFixed(2));

      const root = document.documentElement;
      root.style.setProperty('--board-display-width', `${scaledBoardW}px`);
      root.style.setProperty('--workspace-max-width', `${dims.maxWorkspaceW}px`);
      root.style.setProperty('--left-col-width', `${dims.leftColW}px`);
      root.style.setProperty('--right-col-width', `${dims.rightColW}px`);
      root.style.setProperty('--ui-zoom-factor', `${uiZoom}`);

      if (s.resolutionPreset !== 'AUTO_NATIVE' && typeof global.resizeTo === 'function') {
        try {
          if (global.outerWidth && Math.abs(global.outerWidth - dims.targetW) > 60) {
            global.resizeTo(
              Math.min(dims.targetW, dims.info.sw),
              Math.min(dims.targetH, dims.info.sh)
            );
          }
        } catch (e) {
          // 일반 브라우저 탭에서는 무시
        }
      }

      document.body.classList.remove('crt-on', 'crt-soft', 'crt-off');
      if (s.crtScanline === 'ON') document.body.classList.add('crt-on');
      else if (s.crtScanline === 'SOFT') document.body.classList.add('crt-soft');
      else document.body.classList.add('crt-off');

      this.SFX.setVolume(s.masterVolume / 100);
      this.SFX.setBgmVolume(s.bgmVolume / 100);
      this.SFX.setSfxVolume(s.sfxVolume / 100);
      this.SFX.setBattleVolume(s.battleVolume / 100);
      this.SFX.setEnabled(s.soundEnabled);
      if (s.soundEnabled && s.bgmTrack !== 'OFF') {
        if (!this.SFX._bgmPlaying || this.SFX.bgmTrack !== s.bgmTrack) {
          this.SFX.startBGM(s.bgmTrack);
        }
      } else {
        this.SFX.stopBGM();
      }

      this._pixelBoardCache = null;
      this._forceRedraw = true;

      this._syncSettingsUIFromState();
      this._saveUserSettings();

      if (playFeedback) {
        this.SFX.playSelect();
      }
    }

    _syncSettingsUIFromState() {
      const s = this.userSettings;
      const info = this._detectComputerResolutionInfo();

      const badge = document.getElementById('detected-monitor-badge');
      if (badge) badge.textContent = `내 모니터: ${info.label}`;

      const modalHw = document.getElementById('modal-hardware-info');
      if (modalHw) {
        modalHw.textContent = `감지된 내 모니터: ${info.label} · 현재 창: ${info.vw}×${info.vh}`;
      }

      const nativeSub = document.getElementById('native-res-subtext');
      if (nativeSub) {
        nativeSub.textContent = `(${info.sw}×${info.sh} 모니터 최적)`;
      }

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val;
      };
      const setText = (id, txt) => {
        const el = document.getElementById(id);
        if (el) el.textContent = txt;
      };

      setVal('quick-resolution-select', s.resolutionPreset);
      const presetBtns = document.querySelectorAll('[data-res-preset]');
      presetBtns.forEach((btn) => {
        btn.classList.toggle('active', btn.getAttribute('data-res-preset') === s.resolutionPreset);
      });

      setVal('quick-board-size-range', s.boardScalePercent);
      setText('quick-board-size-val', `${s.boardScalePercent}%`);
      setVal('opt-board-scale', s.boardScalePercent);
      setText('opt-board-scale-label', `${s.boardScalePercent}%`);

      setVal('quick-ui-scale-range', s.uiScalePercent);
      setText('quick-ui-scale-val', `${s.uiScalePercent}%`);
      setVal('opt-ui-scale', s.uiScalePercent);
      setText('opt-ui-scale-label', `${s.uiScalePercent}%`);

      setVal('opt-board-theme', s.boardTheme);
      setVal('opt-crt-scanline', s.crtScanline);

      setVal('quick-master-vol-range', s.masterVolume);
      setText('quick-master-vol-val', `${s.masterVolume}%`);
      setVal('opt-master-volume', s.masterVolume);
      setText('opt-master-volume-label', `${s.masterVolume}%`);

      setVal('quick-bgm-vol-range', s.bgmVolume);
      setText('quick-bgm-vol-val', `${s.bgmVolume}%`);
      setVal('opt-bgm-volume', s.bgmVolume);
      setText('opt-bgm-volume-label', `${s.bgmVolume}%`);

      setVal('opt-sfx-volume', s.sfxVolume);
      setText('opt-sfx-volume-label', `${s.sfxVolume}%`);

      setVal('opt-battle-volume', s.battleVolume);
      setText('opt-battle-volume-label', `${s.battleVolume}%`);

      setVal('opt-bgm-track', s.bgmTrack);

      const topSoundBtn = document.getElementById('btn-toggle-sound');
      if (topSoundBtn) {
        topSoundBtn.textContent = s.soundEnabled ? `🔊 사운드 ${s.masterVolume}%` : '🔇 사운드 OFF';
      }
      const modalMuteBtn = document.getElementById('btn-modal-mute-toggle');
      if (modalMuteBtn) {
        modalMuteBtn.textContent = s.soundEnabled ? '🔊 전체 사운드 켜짐 (ON)' : '🔇 전체 음소거됨 (MUTE)';
        modalMuteBtn.className = s.soundEnabled ? 'btn btn-emerald' : 'btn btn-crimson';
      }
    }

    _toggleFullscreen() {
      this.SFX.playSelect();
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    }

    _bindSettingsEvents() {
      const bindClick = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', fn);
      };

      const unlockAudio = () => {
        if (this.userSettings.soundEnabled && this.userSettings.bgmTrack !== 'OFF' && !this.SFX._bgmPlaying) {
          this.SFX.startBGM(this.userSettings.bgmTrack);
        }
        document.removeEventListener('click', unlockAudio);
      };
      document.addEventListener('click', unlockAudio);

      window.addEventListener('resize', () => {
        this._syncSettingsUIFromState();
        this._forceRedraw = true;
      });

      bindClick('btn-open-settings', () => {
        this.SFX.playSelect();
        this._syncSettingsUIFromState();
        this.openModal('settings-modal');
      });
      bindClick('btn-open-settings-side', () => {
        this.SFX.playSelect();
        this._syncSettingsUIFromState();
        this.openModal('settings-modal');
      });
      bindClick('btn-close-settings', () => this.closeModal('settings-modal'));
      bindClick('btn-save-close-settings', () => {
        this.SFX.playSelect();
        this.closeModal('settings-modal');
      });

      bindClick('btn-quick-fullscreen', () => this._toggleFullscreen());
      bindClick('btn-modal-fullscreen', () => this._toggleFullscreen());

      bindClick('btn-auto-fit-computer', () => {
        this.userSettings.resolutionPreset = 'AUTO_NATIVE';
        this.userSettings.boardScalePercent = 100;
        this.userSettings.uiScalePercent = 100;
        this._applyAllUserSettings(true);
        const info = this._detectComputerResolutionInfo();
        this.setBriefingText(`🖥️ 내 컴퓨터 모니터(${info.label}) 기준으로 보드와 UI 해상도를 자동 최적화했습니다.`);
      });

      const quickResSel = document.getElementById('quick-resolution-select');
      if (quickResSel) {
        quickResSel.addEventListener('change', (e) => {
          this.userSettings.resolutionPreset = e.target.value;
          this._applyAllUserSettings(true);
          this.setBriefingText(`🖥️ 디스플레이 해상도 프리셋 [${e.target.value}] 적용 완료!`);
        });
      }

      const presetBtns = document.querySelectorAll('[data-res-preset]');
      presetBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          this.userSettings.resolutionPreset = btn.getAttribute('data-res-preset');
          this._applyAllUserSettings(true);
          this.setBriefingText(`🖥️ 디스플레이 해상도 프리셋 [${this.userSettings.resolutionPreset}] 적용 완료!`);
        });
      });

      const bindRange = (id, settingKey) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('input', (e) => {
          this.userSettings[settingKey] = Number(e.target.value);
          if (settingKey.includes('Volume') && this.userSettings[settingKey] > 0) {
            this.userSettings.soundEnabled = true;
          }
          this._applyAllUserSettings(false);
        });
        el.addEventListener('change', () => {
          this.SFX.playSelect();
        });
      };

      bindRange('quick-board-size-range', 'boardScalePercent');
      bindRange('opt-board-scale', 'boardScalePercent');
      bindRange('quick-ui-scale-range', 'uiScalePercent');
      bindRange('opt-ui-scale', 'uiScalePercent');

      bindRange('quick-master-vol-range', 'masterVolume');
      bindRange('opt-master-volume', 'masterVolume');
      bindRange('quick-bgm-vol-range', 'bgmVolume');
      bindRange('opt-bgm-volume', 'bgmVolume');
      bindRange('opt-sfx-volume', 'sfxVolume');
      bindRange('opt-battle-volume', 'battleVolume');

      const boardThemeSel = document.getElementById('opt-board-theme');
      if (boardThemeSel) {
        boardThemeSel.addEventListener('change', (e) => {
          this.userSettings.boardTheme = e.target.value;
          this._applyAllUserSettings(true);
        });
      }

      const crtSel = document.getElementById('opt-crt-scanline');
      if (crtSel) {
        crtSel.addEventListener('change', (e) => {
          this.userSettings.crtScanline = e.target.value;
          this._applyAllUserSettings(true);
        });
      }

      const bgmTrackSel = document.getElementById('opt-bgm-track');
      if (bgmTrackSel) {
        bgmTrackSel.addEventListener('change', (e) => {
          this.userSettings.bgmTrack = e.target.value;
          this.SFX.startBGM(this.userSettings.bgmTrack);
          this._applyAllUserSettings(true);
        });
      }

      bindClick('btn-modal-mute-toggle', () => {
        this.userSettings.soundEnabled = !this.userSettings.soundEnabled;
        this._applyAllUserSettings(true);
      });

      bindClick('btn-test-sfx-snap', () => {
        this.userSettings.soundEnabled = true;
        this._applyAllUserSettings(false);
        this.SFX.playWoodSnap(0);
      });
      bindClick('btn-test-sfx-battle', () => {
        this.userSettings.soundEnabled = true;
        this._applyAllUserSettings(false);
        this.SFX.playHeavySlash(0);
      });
      bindClick('btn-test-sfx-fanfare', () => {
        this.userSettings.soundEnabled = true;
        this._applyAllUserSettings(false);
        this.SFX.playCheckHorn();
      });

      bindClick('btn-reset-default-settings', () => {
        this.userSettings = {
          resolutionPreset: 'AUTO_NATIVE',
          boardScalePercent: 100,
          uiScalePercent: 100,
          boardTheme: 'ROYAL_OAK',
          boardViewMode: '2.5D',
          crtScanline: 'OFF',
          soundEnabled: true,
          masterVolume: 75,
          bgmVolume: 55,
          sfxVolume: 85,
          battleVolume: 90,
          bgmTrack: 'GORYEO_MARCH'
        };
        this._applyAllUserSettings(true);
        this._sync3DViewButtonUI();
        this.setBriefingText('🔄 해상도 및 사운드 설정을 내 컴퓨터 권장 기본값으로 초기화했습니다.');
      });
    }

    openModal(id) {
      const m = document.getElementById(id);
      if (m) m.classList.add('open');
      this._forceRedraw = true;
    }

    closeModal(id) {
      const m = document.getElementById(id);
      if (m) m.classList.remove('open');
      this._forceRedraw = true;
    }

    // ==========================================================================
    // 대국 시작 / 착수 / 캐슬링 / 프로모션 / 패스 / 무르기 / 빅장 / AI 연동
    // ==========================================================================

    startNewGame() {
      this.isBusy = false;
      this.marchAnim = null;
      this.selectedCoord = null;
      this.legalMeta = { moves: [], blockedNecks: [], bridges: [] };
      this._pixelBoardCache = null;
      this._forceRedraw = true;

      this.game.reset({
        chuFormation: this.chuFormation,
        hanFormation: this.hanFormation,
        chuSkin: this.chuSkin,
        hanSkin: this.hanSkin
      });

      const isChess = this.isChessMode();
      this.inspectedPiece = isChess
        ? (this.game.getPieceAt(3, 7) || this.game.getPieceAt(4, 7))
        : (this.game.getPieceAt(0, 9) || this.game.getPieceAt(4, 8));

      this.SFX.playWoodSnap(0);
      const chuLabel = isChess ? '백' : '초';
      const hanLabel = isChess ? '흑' : '한';
      this.Director.showTacticalBanner(
        isChess ? '♟️ CHESS BATTLE START!' : '⚔️ JANGGI STAGE START!',
        `${this.Art.getFactionConfig(this.chuSkin).shortName}(${chuLabel}) VS ${this.Art.getFactionConfig(this.hanSkin).shortName}(${hanLabel})`,
        '#f5b700',
        1400
      );

      this.setBriefingText(
        isChess
          ? '백(WHITE · 하단) 선공으로 체스 대국이 시작되었습니다. 출전할 정예 기물을 선택하세요.'
          : '초(楚 · 하단) 선공으로 장기 대국이 시작되었습니다. 출전할 정예 기물을 선택하세요.'
      );
      this.updateHUD();
      this.updateInspectorText();
      this.checkAndTriggerAITurn();
    }

    _getCanvasClientPos(clientX, clientY) {
      const rect = this.boardCanvas.getBoundingClientRect();
      const scaleX = this.canvasWidth / Math.max(1, rect.width);
      const scaleY = this.canvasHeight / Math.max(1, rect.height);
      return {
        px: (clientX - rect.left) * scaleX,
        py: (clientY - rect.top) * scaleY
      };
    }

    _getCanvasMousePos(e) {
      return this._getCanvasClientPos(e.clientX, e.clientY);
    }

    _onBoardHover(e) {
      const { px, py } = this._getCanvasMousePos(e);
      const nextHover = this.pixelToBoard(px, py);
      if (
        (nextHover && !this.hoveredCoord) ||
        (!nextHover && this.hoveredCoord) ||
        (nextHover && this.hoveredCoord && (nextHover.x !== this.hoveredCoord.x || nextHover.y !== this.hoveredCoord.y))
      ) {
        this.hoveredCoord = nextHover;
        this._forceRedraw = true;
      }
    }

    _onBoardClick(e) {
      const { px, py } = this._getCanvasMousePos(e);
      this._handleBoardPointerAction(px, py, false);
    }

    async _handleBoardPointerAction(px, py, isTouch = false) {
      if (this.Director && this.Director.isPlaying) {
        this.Director.skip();
        return;
      }
      if (this.isBusy || this.game.isGameOver) return;
      if (this.isCurrentTurnAI()) return;

      const coord = this._resolveMagneticTouchCoord(px, py, isTouch);
      this._forceRedraw = true;

      if (!coord) {
        this.selectedCoord = null;
        this.legalMeta = { moves: [], blockedNecks: [], bridges: [] };
        return;
      }

      const clickedPiece = this.game.getPieceAt(coord.x, coord.y);
      if (clickedPiece) {
        this.inspectedPiece = clickedPiece;
        this.updateInspectorText();
      }

      if (this.selectedCoord) {
        const matchedMove = this.legalMeta.moves.find(
          (m) => m.toX === coord.x && m.toY === coord.y
        );
        if (matchedMove) {
          let chosenPromo = null;
          if (matchedMove.isPromotion) {
            this.isBusy = true;
            chosenPromo = await this._promptPromotionChoice(matchedMove.piece.side);
            matchedMove.promoteTo = chosenPromo;
          }
          this.executeMoveWithCinematic(matchedMove, null, chosenPromo);
          return;
        }
      }

      if (clickedPiece && clickedPiece.side === this.game.currentTurn) {
        this.selectedCoord = { x: coord.x, y: coord.y };
        this.legalMeta = this.game.getLegalMovesAt(coord.x, coord.y);
        this.SFX.playSelect();

        if (this.legalMeta.moves.length === 0) {
          this.SFX.playBlocked();
          this.setBriefingText(
            this.isChessMode()
              ? `⚠️ [${clickedPiece.kr}(${clickedPiece.hanja})]의 이동 경로가 막혀 있거나 킹이 체크에 노출되어 이동할 수 없습니다.`
              : `⚠️ [${clickedPiece.kr}(${clickedPiece.hanja})]의 진로(멱/포 다리)가 막혀 있거나 왕이 위험해져 이동할 수 없습니다.`
          );
        }
      } else {
        this.selectedCoord = null;
        this.legalMeta = { moves: [], blockedNecks: [], bridges: [] };
      }
    }

    /**
     * 보드 특정 칸(bx, by)에 즉시 착지/장군/멍군/프로모션 2.5D 충격파 & 파편 이펙트 생성
     */
    _spawnBoardTileImpact(bx, by, kind = 'LAND', color = '#fff05a') {
      const particles = [];
      const count = kind === 'CHECK' || kind === 'PROMOTION' ? 24 : 12;
      for (let i = 0; i < count; i++) {
        const ang = (i / count) * Math.PI * 2 + Math.random() * 0.3;
        const spd = (kind === 'CHECK' || kind === 'PROMOTION' ? 3.5 : 2.0) + Math.random() * 2.5;
        particles.push({
          dx: 0,
          dy: 0,
          dz: 4 + Math.random() * 8,
          vx: Math.cos(ang) * spd,
          vy: Math.sin(ang) * spd * 0.6,
          vz: 2.5 + Math.random() * 4.5,
          size: i % 2 === 0 ? 6 : 4,
          color: i % 2 === 0 ? color : '#ffffff'
        });
      }
      this.boardFxList.push({
        bx,
        by,
        kind,
        color,
        startTime: performance.now(),
        duration: kind === 'CHECK' || kind === 'PROMOTION' ? 750 : 420,
        particles
      });
      this._forceRedraw = true;
    }

    async executeMoveWithCinematic(moveObj, aiCommentary = null, promoteToOverride = null) {
      this.isBusy = true;
      this.selectedCoord = null;
      this.legalMeta = { moves: [], blockedNecks: [], bridges: [] };
      this._forceRedraw = true;

      const isOnBoardCapture =
        moveObj.isCapture &&
        moveObj.captured &&
        this.Director &&
        this.Director.getMode() !== 'ARENA_OVERLAY';

      if (isOnBoardCapture) {
        const atkSkin = this.getSkinForSide(moveObj.piece.side);
        const defSkin = this.getSkinForSide(moveObj.captured.side);
        await this.Director.playCaptureCinematic({
          move: moveObj,
          attackerSkin: atkSkin,
          defenderSkin: defSkin
        });
        this._spawnBoardTileImpact(
          moveObj.toX,
          moveObj.toY,
          'LAND',
          moveObj.piece.side === 'CHU' ? '#10b981' : '#ef4444'
        );
      } else {
        if (moveObj.isCastling && this.SFX.playCastlingSlide) {
          this.SFX.playCastlingSlide(0);
        } else {
          this.SFX.playMove(moveObj.piece.type);
        }
        await this._runMarchAnimation(moveObj, moveObj.isCastling ? 340 : 270);
        this._spawnBoardTileImpact(
          moveObj.toX,
          moveObj.toY,
          'LAND',
          moveObj.piece.side === 'CHU' ? '#34d399' : '#f87171'
        );
        if (moveObj.isCastling && moveObj.rookToX !== null && moveObj.rookToX !== undefined) {
          this._spawnBoardTileImpact(
            moveObj.rookToX,
            moveObj.rookY !== null ? moveObj.rookY : moveObj.toY,
            'LAND',
            '#fde047'
          );
        }

        if (moveObj.isCapture && moveObj.captured) {
          const atkSkin = this.getSkinForSide(moveObj.piece.side);
          const defSkin = this.getSkinForSide(moveObj.captured.side);
          await this.Director.playCaptureCinematic({
            move: moveObj,
            attackerSkin: atkSkin,
            defenderSkin: defSkin
          });
        }
      }

      const chosenPromo = promoteToOverride || moveObj.promoteTo || 'QUEEN';
      const result = this.game.makeMove(
        moveObj.fromX,
        moveObj.fromY,
        moveObj.toX,
        moveObj.toY,
        chosenPromo
      );
      this.inspectedPiece = this.game.getPieceAt(moveObj.toX, moveObj.toY);
      this.updateInspectorText();
      this.updateHUD();
      this._forceRedraw = true;

      if (result.ok) {
        const isChess = this.isChessMode();

        // 체스 프로모션 각성 연출
        if (result.move && result.move.isPromotion) {
          if (this.SFX.playPromotionFanfare) {
            this.SFX.playPromotionFanfare(0);
          }
          this._spawnBoardTileImpact(moveObj.toX, moveObj.toY, 'PROMOTION', '#fde047');
          if (this.Director && this.Director.playPromotionCinematic) {
            await this.Director.playPromotionCinematic({
              move: result.move,
              piece: this.inspectedPiece,
              promotedType: result.move.promoteTo || chosenPromo,
              skin: this.getSkinForSide(moveObj.piece.side)
            });
          } else if (this.Director) {
            this.Director.showTacticalBanner(
              '✨ PROMOTION : 전열보병 각성 승진!',
              `${this.inspectedPiece ? this.inspectedPiece.kr : '퀸'} 병종으로 승진 완료!`,
              '#f5b700',
              1650
            );
          }
        } else if (result.move && result.move.isCastling) {
          const castleTitle =
            result.move.castlingSide === 'KINGSIDE'
              ? '🏰 CASTLING (O-O) : 킹사이드 왕실 성루 교차!'
              : '🏰 CASTLING (O-O-O) : 퀸사이드 왕실 성루 교차!';
          this.Director.showTacticalBanner(
            castleTitle,
            '국왕을 성채 안쪽으로 호위하고 공성 룩(♖)을 중앙 파일에 배치했습니다!',
            '#38bdf8',
            1550
          );
        }

        if (result.isGameOver) {
          this.SFX.playVictoryFanfare();
          this.showGameOverModal();
          this.isBusy = false;
          return;
        }

        if (result.inCheck) {
          this.SFX.playCheckHorn();
          const checkedSideName = isChess
            ? (this.game.currentTurn === 'CHU' ? '백(WHITE)' : '흑(BLACK)')
            : (this.game.currentTurn === 'CHU' ? '초(楚)' : '한(漢)');
          const rows = this.getBoardRows();
          const cols = this.getBoardCols();
          for (let ky = 0; ky < rows; ky++) {
            for (let kx = 0; kx < cols; kx++) {
              const kp = this.game.getPieceAt(kx, ky);
              if (kp && kp.type === 'KING' && kp.side === this.game.currentTurn) {
                this._spawnBoardTileImpact(kx, ky, 'CHECK', '#ff3b5c');
              }
            }
          }
          this.Director.showTacticalBanner(
            isChess ? '🚨 WARNING : 체크! (CHECK!)' : '🚨 WARNING : 장군! (CHECK!)',
            `${checkedSideName}의 군주가 위협받고 있습니다! 즉시 왕을 호위하세요!`,
            '#ff3b5c',
            1650
          );
          this.setBriefingText(
            aiCommentary ||
              `🚨 ${isChess ? '체크(Check)' : '장군(Check)'}! ${checkedSideName} 진영의 군주가 공격 사거리에 노출되었습니다!`
          );
        } else if (result.isMeonggun) {
          this.SFX.playMeonggunShield();
          this._spawnBoardTileImpact(moveObj.toX, moveObj.toY, 'SHIELD', '#00e5a3');
          this.Director.showTacticalBanner(
            isChess ? '🛡️ GUARD : 체크 방어! (DEFENDED!)' : '🛡️ GUARD : 멍군! (DEFENDED!)',
            '철벽 같은 호위로 적의 위협을 분쇄했습니다!',
            '#00e5a3',
            1350
          );
          this.setBriefingText(aiCommentary || '🛡️ 군주를 향한 위협을 성공적으로 방어했습니다.');
        } else if (result.isBikjang) {
          this.SFX.playCheckHorn();
          this.Director.showTacticalBanner(
            '👑 BIKJANG : 빅장! (FACING KINGS!)',
            '두 군주가 마주보았습니다! [빅장 선언]으로 무승부를 택하거나 피할 수 있습니다.',
            '#f5b700',
            1800
          );
          this.setBriefingText(
            '👑 빅장 상태입니다! 하단 [빅장 무승부 선언] 버튼을 누르거나 다른 수를 둘 수 있습니다.'
          );
        } else {
          this.setBriefingText(
            aiCommentary || `▶ ${result.move.notation} — 다음 수를 진행하세요.`
          );
        }
      }

      this.isBusy = false;
      this.checkAndTriggerAITurn();
    }

    _runMarchAnimation(moveObj, durationMs = 260) {
      return new Promise((resolve) => {
        let rookPiece = null;
        if (moveObj.isCastling && moveObj.rookFromX !== null && moveObj.rookFromX !== undefined) {
          const rY = moveObj.rookY !== null && moveObj.rookY !== undefined ? moveObj.rookY : moveObj.fromY;
          rookPiece = this.game.getPieceAt(moveObj.rookFromX, rY);
        }

        this.marchAnim = {
          piece: moveObj.piece,
          fromX: moveObj.fromX,
          fromY: moveObj.fromY,
          toX: moveObj.toX,
          toY: moveObj.toY,
          rookPiece,
          rookFromX: moveObj.rookFromX,
          rookToX: moveObj.rookToX,
          rookY: moveObj.rookY !== null && moveObj.rookY !== undefined ? moveObj.rookY : moveObj.fromY,
          startTime: performance.now(),
          duration: durationMs
        };

        setTimeout(() => {
          this.marchAnim = null;
          this._forceRedraw = true;
          resolve();
        }, durationMs);
      });
    }

    isCurrentTurnAI() {
      if (this.game.isGameOver) return false;
      if (this.gameMode === 'AI_VS_AI') return true;
      if (this.gameMode === '1P_AI') {
        return this.game.currentTurn !== this.humanSide;
      }
      return false;
    }

    async checkAndTriggerAITurn() {
      if (this.isBusy || this.game.isGameOver) return;
      if (!this.isCurrentTurnAI()) return;

      this.isBusy = true;
      const aiSide = this.game.currentTurn;
      const isChess = this.isChessMode();
      const sideLabel = isChess
        ? (aiSide === 'CHU' ? '백(WHITE)' : '흑(BLACK)')
        : (aiSide === 'CHU' ? '초(楚)' : '한(漢)');
      const skinCfg = this.Art.getFactionConfig(this.getSkinForSide(aiSide));

      this.setBriefingText(`⏳ [${skinCfg.shortName} · ${sideLabel}] CPU 지휘관이 수를 계산 중입니다...`);

      const aiResult = await this.AI.chooseMoveAsync(
        this.game,
        aiSide,
        this.aiDifficulty,
        320
      );

      if (!aiResult || !aiResult.move) {
        this.isBusy = false;
        this.handlePassTurn();
        return;
      }

      this.isBusy = false;
      await this.executeMoveWithCinematic(
        aiResult.move,
        `🗣️ [${skinCfg.shortName} 지휘관]: "${aiResult.commentary}"`,
        aiResult.move.promoteTo || 'QUEEN'
      );
    }

    handlePassTurn() {
      if (this.isBusy || this.game.isGameOver) return;
      if (this.isChessMode()) {
        this.SFX.playSelect();
        this.Director.showTacticalBanner(
          '🏰 CASTLING & SPECIAL RULES',
          '킹과 룩 사이가 비어 있고 두 기물이 움직인 적 없을 때 킹을 선택하면 2칸 옆 캐슬링(O-O / O-O-O) 칸이 초록색으로 활성화됩니다!',
          '#38bdf8',
          2200
        );
        this.setBriefingText(
          '🏰 [체스 가이드]: 킹과 룩이 첫 이동 전이고 사이가 비어 있으면 킹을 2칸 이동하여 캐슬링할 수 있습니다. (폰 끝줄 도달 시 승진 모달 오픈)'
        );
        return;
      }

      const res = this.game.passTurn();
      if (!res.ok) {
        this.SFX.playBlocked();
        this.setBriefingText(`⚠️ ${res.error}`);
        return;
      }
      this.SFX.playWoodSnap(0);
      this.updateHUD();
      if (res.isGameOver) {
        this.SFX.playVictoryFanfare();
        this.showGameOverModal();
      } else {
        this.setBriefingText('한 수 쉼(Pass)을 선언하여 차례를 넘겼습니다.');
        this.checkAndTriggerAITurn();
      }
    }

    handleUndoMove() {
      if (this.isBusy || !this.game.history.length) return;
      const steps = this.gameMode === '1P_AI' && this.game.history.length >= 2 ? 2 : 1;
      const res = this.game.undo(steps);
      if (res.ok) {
        this.selectedCoord = null;
        this.legalMeta = { moves: [], blockedNecks: [], bridges: [] };
        this._forceRedraw = true;
        this.SFX.playSelect();
        this.setBriefingText(`⏪ 이전 ${steps}수를 물렀습니다.`);
        this.updateHUD();
      }
    }

    handleDeclareBikjang() {
      if (this.isBusy || this.game.isGameOver) return;
      const res = this.game.resolveBikjang('BIKJANG_DRAW');
      if (!res.ok) {
        this.SFX.playBlocked();
        this.setBriefingText(`⚠️ ${res.error}`);
        return;
      }
      this.SFX.playVictoryFanfare();
      this.updateHUD();
      this.showGameOverModal();
    }

    handleScoreDecision() {
      if (this.isBusy || this.game.isGameOver) return;
      this.game.finishByScoreDecision();
      this.SFX.playVictoryFanfare();
      this.updateHUD();
      this.showGameOverModal();
    }

    // ==========================================================================
    // HUD 및 모달 UI 업데이트 (지휘관 초상화 drawCommanderPortrait 연동)
    // ==========================================================================

    setBriefingText(msg) {
      const el = document.getElementById('commander-briefing-text');
      if (el) el.textContent = msg;
    }

    updateInspectorText() {
      const p = this.inspectedPiece;
      if (!p) return;

      const skinId = this.getSkinForSide(p.side);
      const unitMeta = this.Art.getUnitMeta(p.type, skinId, p.side);
      const lore = global.FACTION_COMBAT_LORE[skinId]
        ? global.FACTION_COMBAT_LORE[skinId].units[p.type]
        : null;

      const elName = document.getElementById('inspector-unit-name');
      const elRole = document.getElementById('inspector-unit-role');
      const elDesc = document.getElementById('inspector-unit-desc');

      if (elName) {
        elName.textContent = `${unitMeta.unitTitle} [${p.kr} · ${p.hanja}]`;
      }
      if (elRole) {
        const ptsText = p.type === 'KING' ? '총사령관(무가치)' : `기물 가치 ${p.score}점`;
        const weaponText = lore ? ` · 무장: ${lore.weapon}` : '';
        elRole.textContent = `${unitMeta.factionName} · ${ptsText}${weaponText}`;
      }
      if (elDesc) {
        const descKey = p.type === 'KING' && this.isChessMode() ? 'KING_CHESS' : p.type;
        elDesc.textContent = PIECE_RULE_DESCRIPTIONS[descKey] || PIECE_RULE_DESCRIPTIONS[p.type] || '';
      }
      this._forceRedraw = true;
    }

    updateHUD() {
      const state = this.game.getState();
      const isChess = this.isChessMode();
      const chuSkinCfg = this.Art.getFactionConfig(this.chuSkin);
      const hanSkinCfg = this.Art.getFactionConfig(this.hanSkin);

      const turnPill = document.getElementById('current-turn-pill');
      if (turnPill) {
        if (state.currentTurn === 'CHU') {
          turnPill.className = 'turn-pill chu-turn';
          turnPill.textContent = isChess
            ? `백(WHITE) TURN · ${state.turnCount}수`
            : `초(楚) TURN · ${state.turnCount}수`;
        } else {
          turnPill.className = 'turn-pill han-turn';
          turnPill.textContent = isChess
            ? `흑(BLACK) TURN · ${state.turnCount}수`
            : `한(漢) TURN · ${state.turnCount}수`;
        }
      }

      const hanCard = document.getElementById('han-faction-card');
      const chuCard = document.getElementById('chu-faction-card');
      if (hanCard) hanCard.classList.toggle('active-turn', state.currentTurn === 'HAN');
      if (chuCard) chuCard.classList.toggle('active-turn', state.currentTurn === 'CHU');

      const elHanName = document.getElementById('han-faction-name');
      const elHanSub = document.getElementById('han-faction-sub');
      const elChuName = document.getElementById('chu-faction-name');
      const elChuSub = document.getElementById('chu-faction-sub');

      const hanFormObj = this.Engine.FORMATIONS[this.game.hanFormation] || Object.values(this.Engine.FORMATIONS)[0];
      const chuFormObj = this.Engine.FORMATIONS[this.game.chuFormation] || Object.values(this.Engine.FORMATIONS)[0];

      if (elHanName) elHanName.textContent = hanSkinCfg.name;
      if (elHanSub) {
        elHanSub.textContent = isChess
          ? `진형: ${hanFormObj.shortName} · 후공 (흑)`
          : `상차림: ${hanFormObj.shortName} · 후공 (덤 +1.5점)`;
      }
      if (elChuName) elChuName.textContent = chuSkinCfg.name;
      if (elChuSub) {
        elChuSub.textContent = isChess
          ? `진형: ${chuFormObj.shortName} · 선공 (백)`
          : `상차림: ${chuFormObj.shortName} · 선공`;
      }

      const chuInCheck = state.inCheck && state.currentTurn === 'CHU';
      const hanInCheck = state.inCheck && state.currentTurn === 'HAN';
      this._renderEmblemCanvas(this.chuEmblemCanvas, chuSkinCfg, 'CHU', chuInCheck);
      this._renderEmblemCanvas(this.hanEmblemCanvas, hanSkinCfg, 'HAN', hanInCheck);

      const elChuScore = document.getElementById('chu-score-val');
      const elHanScore = document.getElementById('han-score-val');
      if (elChuScore) elChuScore.textContent = isChess ? `${state.scores.CHU}` : state.scores.CHU.toFixed(1);
      if (elHanScore) elHanScore.textContent = isChess ? `${state.scores.HAN}` : state.scores.HAN.toFixed(1);

      const totalScore = Math.max(1, state.scores.CHU + state.scores.HAN);
      const chuRatio = Math.min(92, Math.max(8, (state.scores.CHU / totalScore) * 100));
      const powerFill = document.getElementById('power-bar-chu-fill');
      const powerDiffLabel = document.getElementById('power-diff-label');
      if (powerFill) powerFill.style.width = `${chuRatio}%`;
      if (powerDiffLabel) {
        const diff = state.scores.diff;
        if (Math.abs(diff) < 0.05) {
          powerDiffLabel.textContent = '전력 백중세 (0.0)';
        } else if (diff > 0) {
          powerDiffLabel.textContent = `${isChess ? '백' : '초'} +${isChess ? diff : diff.toFixed(1)}점 우세`;
        } else {
          powerDiffLabel.textContent = `${isChess ? '흑' : '한'} +${isChess ? Math.abs(diff) : Math.abs(diff).toFixed(1)}점 우세`;
        }
      }

      this._renderCapturedTray('chu-captured-tray', state.capturedPieces.CHU, 'han-piece');
      this._renderCapturedTray('han-captured-tray', state.capturedPieces.HAN, 'chu-piece');

      const chuAlert = document.getElementById('chu-check-alert');
      const hanAlert = document.getElementById('han-check-alert');
      if (chuAlert) {
        chuAlert.classList.toggle('visible', chuInCheck);
        chuAlert.textContent = isChess
          ? '🚨 체크(CHECK)! 백 킹(♔)을 호위하세요!'
          : '🚨 장군(CHECK)! 초궁을 호위하세요!';
      }
      if (hanAlert) {
        hanAlert.classList.toggle('visible', hanInCheck);
        hanAlert.textContent = isChess
          ? '🚨 체크(CHECK)! 흑 킹(♚)을 호위하세요!'
          : '🚨 장군(CHECK)! 한궁을 호위하세요!';
      }

      const btnBikjang = document.getElementById('btn-declare-bikjang');
      if (btnBikjang) {
        btnBikjang.disabled = isChess || !state.bikjangState.active || state.isGameOver;
      }

      const btnUndo = document.getElementById('btn-undo-move');
      if (btnUndo) {
        btnUndo.disabled = !state.canUndo;
      }

      this._renderMoveLog();
    }

    /**
     * 좌측 진영 카드 캔버스에 고밀도 지휘관 도트 초상화(`drawCommanderPortrait`) 렌더링
     */
    _renderEmblemCanvas(canvas, skinCfg, side = 'CHU', isCheck = false) {
      if (!canvas || !this.Art) return;
      const logW = canvas._logicalWidth || 54;
      const logH = canvas._logicalHeight || 54;
      const scale = canvas._renderScale || 2.5;
      const ctx = canvas.getContext('2d');
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, logW, logH);

      if (typeof this.Art.drawCommanderPortrait === 'function') {
        this.Art.drawCommanderPortrait(ctx, 0, 0, logW, skinCfg.id, side, {
          isCheck,
          mood: isCheck ? 'CHECK' : 'NORMAL'
        });
      } else {
        this.Art.drawFactionEmblem(
          ctx,
          logW / 2,
          logH / 2,
          logW * 0.38,
          skinCfg.emblem,
          skinCfg.palette.gold,
          0.95
        );
      }
    }

    _renderCapturedTray(containerId, pieces, chipClass) {
      const el = document.getElementById(containerId);
      if (!el) return;
      if (!pieces || pieces.length === 0) {
        el.innerHTML = '<span style="font-size:11px;color:#64748b;">포획한 기물 없음</span>';
        return;
      }
      el.innerHTML = pieces
        .map((p) => `<span class="captured-chip ${chipClass}">${p.hanja} ${p.kr}</span>`)
        .join('');
    }

    _renderMoveLog() {
      const container = document.getElementById('move-history-list');
      if (!container) return;

      if (this.game.history.length === 0) {
        container.innerHTML =
          '<div style="color:#64748b;font-size:11.5px;padding:8px;">아직 착수 기록이 없습니다.</div>';
        return;
      }

      container.innerHTML = this.game.history
        .map((snap, idx) => {
          const mv = snap.move;
          const cls = mv.piece.side === 'CHU' ? 'chu-move' : 'han-move';
          const text = mv.notation || `${mv.piece.kr} 이동`;
          return `<div class="move-log-item ${cls}">
            <span><strong class="move-num">#${idx + 1}</strong>${text}</span>
          </div>`;
        })
        .join('');
      container.scrollTop = container.scrollHeight;
    }

    showGameOverModal() {
      const state = this.game.getState();
      const isChess = this.isChessMode();
      const titleEl = document.getElementById('gameover-title');
      const descEl = document.getElementById('gameover-desc');
      const scoreEl = document.getElementById('gameover-score-summary');

      let winnerName = isChess ? 'DRAW (무승부)' : 'DRAW (빅장 무승부)';
      if (state.winner === 'CHU') {
        winnerName = `${isChess ? '백(WHITE)' : '초(楚)'} · ${this.Art.getFactionConfig(this.chuSkin).name} VICTORY!`;
      } else if (state.winner === 'HAN') {
        winnerName = `${isChess ? '흑(BLACK)' : '한(漢)'} · ${this.Art.getFactionConfig(this.hanSkin).name} VICTORY!`;
      }

      const reasonMap = {
        CHECKMATE: isChess
          ? '체크메이트(Checkmate)로 적 국왕의 퇴로를 완벽히 봉쇄하여 승리했습니다!'
          : '외통수(Checkmate)로 적의 본진 궁성을 완벽히 함락했습니다!',
        STALEMATE: isChess
          ? '합법적인 착수가 남아있지 않은 스테일메이트(Stalemate) 무승부가 선언되었습니다.'
          : '적군이 더 이상 움직일 수 없는 초완봉(Stalemate) 승리를 거두었습니다!',
        INSUFFICIENT_MATERIAL: '양측 모두 체크메이트를 만들 기물이 부족하여(기물 부족) 무승부가 선언되었습니다.',
        FIFTY_MOVE_RULE: '50수 동안 폰 이동과 기물 포획이 없어 50수 무승부 규칙이 적용되었습니다.',
        BIKJANG_DRAW: '두 군주가 마주보는 빅장(Facing Kings) 합의로 무승부가 선언되었습니다.',
        SCORE_DECISION: '기물 점수 판정으로 우세한 진영이 최종 승리를 거두었습니다!',
        RESIGN: '상대 진영이 항복(기권)을 선언했습니다.'
      };

      if (titleEl) titleEl.textContent = `🏆 ${winnerName}`;
      if (descEl) descEl.textContent = reasonMap[state.winReason] || '대국이 종료되었습니다.';
      if (scoreEl) {
        scoreEl.textContent = isChess
          ? `최종 기물 점수 — 백(WHITE): ${state.scores.CHU}점  vs  흑(BLACK): ${state.scores.HAN}점`
          : `최종 기물 점수 — 초(楚): ${state.scores.CHU.toFixed(1)}점  vs  한(漢): ${state.scores.HAN.toFixed(1)}점 (덤 1.5점 포함)`;
      }

      this.openModal('gameover-modal');
    }

    // ==========================================================================
    // 16-BIT 도트 장기판(9x10) & 체스판(8x8) 오프스크린 생성 & 60FPS 렌더링
    // ==========================================================================

    _drawPixelLine(ctx, x0, y0, x1, y1, pixelSize, color) {
      ctx.fillStyle = color;
      let gx0 = Math.round(x0 / pixelSize);
      let gy0 = Math.round(y0 / pixelSize);
      const gx1 = Math.round(x1 / pixelSize);
      const gy1 = Math.round(y1 / pixelSize);

      const dx = Math.abs(gx1 - gx0);
      const dy = Math.abs(gy1 - gy0);
      const sx = gx0 < gx1 ? 1 : -1;
      const sy = gy0 < gy1 ? 1 : -1;
      let err = dx - dy;

      while (true) {
        ctx.fillRect(gx0 * pixelSize, gy0 * pixelSize, pixelSize, pixelSize);
        if (gx0 === gx1 && gy0 === gy1) break;
        const e2 = 2 * err;
        if (e2 > -dy) {
          err -= dy;
          gx0 += sx;
        }
        if (e2 < dx) {
          err += dx;
          gy0 += sy;
        }
      }
    }

    /**
     * 8x8 HD 도트 디오라마 체스판 표면 오프스크린 베이킹 (2.5D & 2D 지원)
     * - 정통 체크무늬 대리석/비취/흑요석/사암 타일 + 각 타일의 입체 도트 베벨과 석재 균열 디테일
     * - a~h 파일 및 1~8 랭크 골드 픽셀 문자 + 전면 명패 `★ 2.5D BATTLE CHESS ★`
     */
    _bakeChessBoardSurface(ctx, W, H, themeKey) {
      const CHESS_PALETTES = {
        ROYAL_OAK: {
          outer: '#0d0b10',
          lightBase: '#d6c19e', lightHi: '#eadbc0', lightLo: '#b39972',
          darkBase: '#59361f', darkHi: '#6e4529', darkLo: '#3d2312',
          cliffTop: '#311b0f', cliffMid: '#24130a', cliffBot: '#160b05',
          border: '#f5b700'
        },
        JADE_PALACE: {
          outer: '#071217',
          lightBase: '#99d5c9', lightHi: '#c2ebe2', lightLo: '#6db3a6',
          darkBase: '#134042', darkHi: '#1c5659', darkLo: '#0b292b',
          cliffTop: '#0e292a', cliffMid: '#091d1e', cliffBot: '#051011',
          border: '#34d399'
        },
        OBSIDIAN_CASTLE: {
          outer: '#07080d',
          lightBase: '#64748b', lightHi: '#94a3b8', lightLo: '#475569',
          darkBase: '#171b29', darkHi: '#23293d', darkLo: '#0d1018',
          cliffTop: '#141724', cliffMid: '#0e101a', cliffBot: '#08090f',
          border: '#f43f5e'
        },
        DESERT_SAND: {
          outer: '#140e08',
          lightBase: '#e7c996', lightHi: '#f5dfb8', lightLo: '#c4a26c',
          darkBase: '#784b23', darkHi: '#8f5b2d', darkLo: '#543316',
          cliffTop: '#4f341b', cliffMid: '#3b2613', cliffBot: '#24160a',
          border: '#fbbf24'
        }
      };

      const pal = CHESS_PALETTES[themeKey] || CHESS_PALETTES.ROYAL_OAK;
      const P = 4;
      const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];

      ctx.fillStyle = pal.outer;
      ctx.fillRect(0, 0, W, H);

      if (!this.is3DView()) {
        // --- 2D 평면 8x8 도트 체스판 ---
        const originX = 70;
        const originY = 110;
        const tileSize = 80;
        const boardSize = tileSize * 8; // 640

        // 외곽 황금/블랙 액자 몰딩
        ctx.fillStyle = '#000000';
        ctx.fillRect(originX - 24, originY - 24, boardSize + 48, boardSize + 48);
        ctx.fillStyle = pal.cliffMid;
        ctx.fillRect(originX - 20, originY - 20, boardSize + 40, boardSize + 40);
        ctx.fillStyle = pal.border;
        ctx.fillRect(originX - 8, originY - 8, boardSize + 16, boardSize + 16);
        ctx.fillStyle = '#000000';
        ctx.fillRect(originX - 4, originY - 4, boardSize + 8, boardSize + 8);

        for (let vy = 0; vy < 8; vy++) {
          for (let vx = 0; vx < 8; vx++) {
            const tx = originX + vx * tileSize;
            const ty = originY + vy * tileSize;
            const isLight = (vx + vy) % 2 === 0;
            const baseCol = isLight ? pal.lightBase : pal.darkBase;
            const hiCol = isLight ? pal.lightHi : pal.darkHi;
            const loCol = isLight ? pal.lightLo : pal.darkLo;

            ctx.fillStyle = baseCol;
            ctx.fillRect(tx, ty, tileSize, tileSize);

            // 타일 입체 도트 베벨 (상/좌 하이라이트, 하/우 쉐도우)
            ctx.fillStyle = hiCol;
            ctx.fillRect(tx, ty, tileSize, P);
            ctx.fillRect(tx, ty, P, tileSize);
            ctx.fillStyle = loCol;
            ctx.fillRect(tx, ty + tileSize - P, tileSize, P);
            ctx.fillRect(tx + tileSize - P, ty, P, tileSize);

            // 미세 석재 균열/도트 질감
            const seed = (vx * 17 + vy * 31) % 7;
            ctx.fillStyle = seed % 2 === 0 ? loCol : hiCol;
            ctx.fillRect(tx + 16 + seed * 6, ty + 20 + seed * 5, P, P);
            ctx.fillRect(tx + 48 - seed * 4, ty + 52 - seed * 3, P * 2, P);
          }
        }

        // a~h 파일 및 8~1 랭크 골드 픽셀 문자
        ctx.font = 'bold 13px "Silkscreen", "DungGeunMo", monospace';
        ctx.textAlign = 'center';
        for (let i = 0; i < 8; i++) {
          const bx = this.boardFlipped ? 7 - i : i;
          const by = this.boardFlipped ? 7 - i : i;
          const fileChar = files[bx].toUpperCase();
          const rankChar = `${8 - by}`;

          const cx = originX + (i + 0.5) * tileSize;
          const cy = originY + (i + 0.5) * tileSize;

          ctx.fillStyle = '#000000';
          ctx.fillText(fileChar, cx + 2, originY + boardSize + 18);
          ctx.fillText(rankChar, originX - 14, cy + 5);
          ctx.fillStyle = '#fff05a';
          ctx.fillText(fileChar, cx, originY + boardSize + 16);
          ctx.fillText(rankChar, originX - 16, cy + 3);
        }
        return;
      }

      // --- 2.5D 원근 틸트 8x8 디오라마 체스판 + 44px 전면 두께 단면 ---
      ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
      for (let by = 0; by < H; by += 48) {
        ctx.fillRect(0, by, W, 2);
      }

      const topL = this._projectVisualCoord(-0.88, -0.88);
      const topR = this._projectVisualCoord(7.88, -0.88);
      const botL = this._projectVisualCoord(-0.88, 7.88);
      const botR = this._projectVisualCoord(7.88, 7.88);
      const slabThickness = 44;

      // 1. 3D 다단 드롭 섀도우
      for (let sStep = 3; sStep >= 1; sStep--) {
        const padS = sStep * 8;
        const dropY = botL.py + slabThickness + sStep * 7;
        ctx.fillStyle = sStep === 1 ? 'rgba(0,0,0,0.78)' : (sStep === 2 ? 'rgba(0,0,0,0.48)' : 'rgba(0,0,0,0.24)');
        ctx.fillRect(
          Math.round((botL.px - padS + 8) / P) * P,
          Math.round((botL.py + 12) / P) * P,
          Math.round((botR.px - botL.px + padS * 2 - 16) / P) * P,
          Math.round((dropY - botL.py - 12) / P) * P
        );
      }

      // 2. 좌·우 경사면 3D 측면 두께 벽
      for (let py = topL.py; py <= botL.py; py += P) {
        const progY = (py - topL.py) / Math.max(1, botL.py - topL.py);
        const lx = Math.round((topL.px + (botL.px - topL.px) * progY) / P) * P;
        const rx = Math.round((topR.px + (botR.px - topR.px) * progY) / P) * P;
        const sideH = Math.round((20 + progY * (slabThickness - 20)) / P) * P;

        ctx.fillStyle = '#000000';
        ctx.fillRect(lx - P, py, P * 2, sideH + P);
        ctx.fillRect(rx - P, py, P * 2, sideH + P);

        ctx.fillStyle = pal.cliffMid;
        ctx.fillRect(lx, py + P, P * 2, sideH - P);
        ctx.fillRect(rx - P, py + P, P * 2, sideH - P);
      }

      // 3. 8x8 원근 체크무늬 대리석/석재 타일 + 베벨 + 균열 스캔라인 베이킹
      for (let py = topL.py; py <= botL.py; py += P) {
        for (let px = 8; px < W - 8; px += P) {
          const unproj = this._unprojectPixelToVisual(px + 2, py + 2);
          const vx = unproj.vx;
          const vy = unproj.vy;

          if (vx < -0.88 || vx > 7.88 || vy < -0.88 || vy > 7.88) continue;

          // 외곽 액자 몰딩 영역 (-0.88 ~ -0.50 및 7.50 ~ 7.88)
          const isOuterRim = vx < -0.50 || vx > 7.50 || vy < -0.50 || vy > 7.50;
          if (isOuterRim) {
            const isExtremeEdge = vx < -0.80 || vx > 7.80 || vy < -0.80 || vy > 7.80;
            const isGoldTrim =
              (vx >= -0.60 && vx <= -0.50) ||
              (vx >= 7.50 && vx <= 7.60) ||
              (vy >= -0.60 && vy <= -0.50) ||
              (vy >= 7.50 && vy <= 7.60);
            ctx.fillStyle = isExtremeEdge ? '#000000' : isGoldTrim ? pal.border : pal.cliffTop;
            ctx.fillRect(px, py, P, P);
            continue;
          }

          // 타일 인덱스 (0..7) 및 타일 내부 로컬 좌표 (0..1)
          const colIdx = Math.min(7, Math.max(0, Math.floor(vx + 0.5)));
          const rowIdx = Math.min(7, Math.max(0, Math.floor(vy + 0.5)));
          const fracX = (vx + 0.5) - colIdx;
          const fracY = (vy + 0.5) - rowIdx;

          const isLight = (colIdx + rowIdx) % 2 === 0;
          const baseCol = isLight ? pal.lightBase : pal.darkBase;
          const hiCol = isLight ? pal.lightHi : pal.darkHi;
          const loCol = isLight ? pal.lightLo : pal.darkLo;

          let col = baseCol;
          // 타일 가장자리 입체 도트 베벨
          if (fracX < 0.07 || fracY < 0.07) {
            col = hiCol;
          } else if (fracX > 0.92 || fracY > 0.92) {
            col = loCol;
          } else {
            // 석재 균열 & 도트 텍스처 디테일
            const hash = Math.abs(Math.floor((vx + 2) * 23 + (vy + 2) * 41)) % 19;
            if (hash === 0) col = hiCol;
            else if (hash === 1) col = loCol;
          }

          ctx.fillStyle = col;
          ctx.fillRect(px, py, P, P);
        }
      }

      // 중앙 왕실 문장 워터마크 (초/백 & 한/흑)
      const topCenterPt = this._projectVisualCoord(3.5, 1.5);
      const botCenterPt = this._projectVisualCoord(3.5, 5.5);
      const topSkinCfg = this.Art.getFactionConfig(this.boardFlipped ? this.chuSkin : this.hanSkin);
      const botSkinCfg = this.Art.getFactionConfig(this.boardFlipped ? this.hanSkin : this.chuSkin);
      ctx.save();
      ctx.translate(topCenterPt.px, topCenterPt.py);
      ctx.scale(topCenterPt.scale, topCenterPt.scale * 0.72);
      this.Art.drawFactionEmblem(ctx, 0, 0, 44, topSkinCfg.emblem, topSkinCfg.palette.gold, 0.16);
      ctx.restore();

      ctx.save();
      ctx.translate(botCenterPt.px, botCenterPt.py);
      ctx.scale(botCenterPt.scale, botCenterPt.scale * 0.72);
      this.Art.drawFactionEmblem(ctx, 0, 0, 44, botSkinCfg.emblem, botSkinCfg.palette.gold, 0.16);
      ctx.restore();

      // 4. 전면 3D 입체 두께 단면 (44px) + 명패 `★ 2.5D BATTLE CHESS ★`
      const cliffLeft = Math.round(botL.px / P) * P;
      const cliffRight = Math.round(botR.px / P) * P;
      const cliffTopY = Math.round(botL.py / P) * P;

      for (let dy = 0; dy < slabThickness; dy += P) {
        const cy = cliffTopY + dy;
        for (let cx = cliffLeft; cx <= cliffRight; cx += P) {
          const isLeftPillar = cx < cliffLeft + 36;
          const isRightPillar = cx > cliffRight - 40;
          const isPlaque = cx >= W / 2 - 88 && cx <= W / 2 + 88 && dy >= 8 && dy <= slabThickness - 8;

          let col = pal.cliffMid;
          if (dy === 0 || dy >= slabThickness - P) {
            col = '#000000';
          } else if (dy === P || dy === slabThickness - P * 2) {
            col = pal.border;
          } else if (dy === P * 2) {
            col = '#090604';
          } else if (isLeftPillar || isRightPillar) {
            col = ((cx + dy) / P) % 3 === 0 ? '#fde047' : pal.border;
          } else if (isPlaque) {
            const onPlaqueBorder =
              cx < W / 2 - 80 || cx > W / 2 + 80 || dy < 12 || dy > slabThickness - 12;
            col = onPlaqueBorder ? pal.border : '#0f172a';
          } else {
            const plankIdx = Math.floor((cx - cliffLeft) / 48);
            const isJoint = Math.abs((cx - cliffLeft) % 48) < P;
            if (isJoint) col = pal.cliffBot;
            else if (dy < slabThickness * 0.5) col = plankIdx % 2 === 0 ? pal.cliffTop : pal.cliffMid;
            else col = plankIdx % 2 === 0 ? pal.cliffMid : pal.cliffBot;
          }

          ctx.fillStyle = col;
          ctx.fillRect(cx, cy, P, P);
        }
      }

      ctx.font = 'bold 11px "Silkscreen", "DungGeunMo", monospace';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#000000';
      ctx.fillText('★ 2.5D BATTLE CHESS ★', W / 2 + 2, cliffTopY + 27);
      ctx.fillStyle = '#fff05a';
      ctx.fillText('★ 2.5D BATTLE CHESS ★', W / 2, cliffTopY + 25);

      // 5. a~h 파일 및 8~1 랭크 골드 픽셀 문자
      ctx.font = 'bold 11px "Silkscreen", "DungGeunMo", monospace';
      ctx.textAlign = 'center';
      for (let i = 0; i < 8; i++) {
        const bx = this.boardFlipped ? 7 - i : i;
        const by = this.boardFlipped ? 7 - i : i;
        const fileChar = files[bx].toUpperCase();
        const rankChar = `${8 - by}`;

        const ptTop = this._projectVisualCoord(i, -0.68);
        ctx.fillStyle = '#000000';
        ctx.fillText(fileChar, ptTop.px + 2, ptTop.py + 4);
        ctx.fillStyle = '#fff05a';
        ctx.fillText(fileChar, ptTop.px, ptTop.py + 2);

        const ptLeft = this._projectVisualCoord(-0.70, i);
        ctx.fillStyle = '#000000';
        ctx.fillText(rankChar, ptLeft.px + 2, ptLeft.py + 5);
        ctx.fillStyle = '#fff05a';
        ctx.fillText(rankChar, ptLeft.px, ptLeft.py + 3);
      }
    }

    /**
     * 16-BIT 도트 목재/석재 타일맵 보드 표면을 오프스크린 캔버스에 생성 및 캐싱
     */
    _ensurePixelBoardSurface() {
      const themeKey = (this.userSettings && this.userSettings.boardTheme) || 'ROYAL_OAK';
      const viewMode = this.is3DView() ? '2.5D' : '2D';
      const scale = this.renderScale || 2.5;
      const cacheKey = `${this.boardGameType}_${this.chuSkin}_${this.hanSkin}_${this.boardFlipped}_${themeKey}_${viewMode}_${scale}`;
      if (this._pixelBoardCache && this._pixelBoardCacheKey === cacheKey) {
        return this._pixelBoardCache;
      }

      const W = this.canvasWidth;
      const H = this.canvasHeight;
      const off = document.createElement('canvas');
      off.width = Math.round(W * scale);
      off.height = Math.round(H * scale);
      const ctx = off.getContext('2d');
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.imageSmoothingEnabled = false;

      if (this.isChessMode()) {
        this._bakeChessBoardSurface(ctx, W, H, themeKey);
        this._pixelBoardCache = off;
        this._pixelBoardCacheKey = cacheKey;
        return off;
      }

      const THEME_PALETTES = {
        ROYAL_OAK: {
          outer: '#0d0b10', t1: '#462a19', t2: '#3c2314', hi: '#563520', lo: '#2d1a0e',
          cliffTop: '#311b0f', cliffMid: '#24130a', cliffBot: '#160b05',
          border: '#f5b700', line: '#d9a44d', shadow: '#180d06'
        },
        JADE_PALACE: {
          outer: '#071217', t1: '#153b3c', t2: '#113032', hi: '#1d4d4f', lo: '#0b2223',
          cliffTop: '#0e292a', cliffMid: '#091d1e', cliffBot: '#051011',
          border: '#34d399', line: '#6ee7b7', shadow: '#041112'
        },
        OBSIDIAN_CASTLE: {
          outer: '#07080d', t1: '#1e2233', t2: '#181b29', hi: '#282d42', lo: '#10121c',
          cliffTop: '#141724', cliffMid: '#0e101a', cliffBot: '#08090f',
          border: '#f43f5e', line: '#94a3b8', shadow: '#05060a'
        },
        DESERT_SAND: {
          outer: '#140e08', t1: '#6b4928', t2: '#5e3f21', hi: '#7d5732', lo: '#472f17',
          cliffTop: '#4f341b', cliffMid: '#3b2613', cliffBot: '#24160a',
          border: '#fbbf24', line: '#fde68a', shadow: '#261709'
        }
      };
      const pal = THEME_PALETTES[themeKey] || THEME_PALETTES.ROYAL_OAK;

      const P = 4;

      if (!this.is3DView()) {
        ctx.fillStyle = pal.outer;
        ctx.fillRect(0, 0, W, H);

        const innerX = 28;
        const innerY = 28;
        const innerW = W - 56;
        const innerH = H - 56;

        for (let py = innerY; py < innerY + innerH; py += P) {
          for (let px = innerX; px < innerX + innerW; px += P) {
            const tileX = Math.floor(px / 40);
            const tileY = Math.floor(py / 40);
            const isAltTile = (tileX + tileY) % 2 === 0;
            const hash = ((px * 13 + py * 29) % 17);
            let col = isAltTile ? pal.t1 : pal.t2;
            if (hash === 0) col = pal.hi;
            else if (hash === 1) col = pal.lo;
            ctx.fillStyle = col;
            ctx.fillRect(px, py, P, P);
          }
        }

        ctx.fillStyle = '#000000';
        ctx.fillRect(20, 20, W - 40, 8);
        ctx.fillRect(20, H - 28, W - 40, 8);
        ctx.fillRect(20, 20, 8, H - 40);
        ctx.fillRect(W - 28, 20, 8, H - 40);

        ctx.fillStyle = pal.border;
        ctx.fillRect(24, 24, W - 48, 4);
        ctx.fillRect(24, H - 28, W - 48, 4);
        ctx.fillRect(24, 24, 4, H - 48);
        ctx.fillRect(W - 28, 24, 4, H - 48);

        this._drawPixelPalaceZone(ctx, 'HAN', 3, 0, 5, 2, this.hanSkin);
        this._drawPixelPalaceZone(ctx, 'CHU', 3, 7, 5, 9, this.chuSkin);
      } else {
        ctx.fillStyle = pal.outer;
        ctx.fillRect(0, 0, W, H);

        ctx.fillStyle = 'rgba(255, 255, 255, 0.02)';
        for (let by = 0; by < H; by += 48) {
          ctx.fillRect(0, by, W, 2);
        }

        const topL = this._projectVisualCoord(-0.52, -0.52);
        const topR = this._projectVisualCoord(8.52, -0.52);
        const botL = this._projectVisualCoord(-0.52, 9.46);
        const botR = this._projectVisualCoord(8.52, 9.46);
        const slabThickness = 44;

        for (let sStep = 3; sStep >= 1; sStep--) {
          const padS = sStep * 8;
          const dropY = botL.py + slabThickness + sStep * 7;
          ctx.fillStyle = sStep === 1 ? 'rgba(0,0,0,0.78)' : (sStep === 2 ? 'rgba(0,0,0,0.48)' : 'rgba(0,0,0,0.24)');
          ctx.fillRect(
            Math.round((botL.px - padS + 8) / P) * P,
            Math.round((botL.py + 12) / P) * P,
            Math.round((botR.px - botL.px + padS * 2 - 16) / P) * P,
            Math.round((dropY - botL.py - 12) / P) * P
          );
        }

        for (let py = topL.py; py <= botL.py; py += P) {
          const progY = (py - topL.py) / Math.max(1, botL.py - topL.py);
          const lx = Math.round((topL.px + (botL.px - topL.px) * progY) / P) * P;
          const rx = Math.round((topR.px + (botR.px - topR.px) * progY) / P) * P;
          const sideH = Math.round((20 + progY * (slabThickness - 20)) / P) * P;

          ctx.fillStyle = '#000000';
          ctx.fillRect(lx - P, py, P * 2, sideH + P);
          ctx.fillRect(rx - P, py, P * 2, sideH + P);

          ctx.fillStyle = pal.cliffMid;
          ctx.fillRect(lx, py + P, P * 2, sideH - P);
          ctx.fillRect(rx - P, py + P, P * 2, sideH - P);
        }

        const chuCarpet1 = '#08382c';
        const chuCarpet2 = '#062820';
        const hanCarpet1 = '#4a1219';
        const hanCarpet2 = '#360c11';

        for (let py = topL.py; py <= botL.py; py += P) {
          for (let px = 8; px < W - 8; px += P) {
            const unproj = this._unprojectPixelToVisual(px + 2, py + 2);
            const vx = unproj.vx;
            const vy = unproj.vy;

            if (vx < -0.52 || vx > 8.52 || vy < -0.52 || vy > 9.46) {
              continue;
            }

            const isOuterRim = vx < -0.36 || vx > 8.36 || vy < -0.36 || vy > 9.32;
            if (isOuterRim) {
              const isExtremeEdge = vx < -0.47 || vx > 8.47 || vy < -0.46 || vy > 9.40;
              const isGoldTrim =
                (vx >= -0.44 && vx <= -0.39) ||
                (vx >= 8.39 && vx <= 8.44) ||
                (vy >= -0.43 && vy <= -0.39) ||
                (vy >= 9.35 && vy <= 9.40);
              if (isExtremeEdge) {
                ctx.fillStyle = '#000000';
              } else if (isGoldTrim) {
                ctx.fillStyle = pal.border;
              } else {
                ctx.fillStyle = pal.cliffTop;
              }
              ctx.fillRect(px, py, P, P);
              continue;
            }

            const inTopPalace = vx >= 3.0 && vx <= 5.0 && vy >= 0.0 && vy <= 2.0;
            const inBotPalace = vx >= 3.0 && vx <= 5.0 && vy >= 7.0 && vy <= 9.0;

            if (inTopPalace || inBotPalace) {
              const isChuZone = this.boardFlipped ? inTopPalace : inBotPalace;
              const pTileX = Math.floor(vx * 5);
              const pTileY = Math.floor(vy * 5);
              const isEven = (pTileX + pTileY) % 2 === 0;
              ctx.fillStyle = isChuZone
                ? (isEven ? chuCarpet1 : chuCarpet2)
                : (isEven ? hanCarpet1 : hanCarpet2);
              ctx.fillRect(px, py, P, P);
              continue;
            }

            const tileX = Math.floor((vx + 0.5) * 2);
            const tileY = Math.floor((vy + 0.5) * 2);
            const isAltTile = (tileX + tileY) % 2 === 0;
            const hash = Math.abs(Math.floor(vx * 19 + vy * 37)) % 15;
            let col = isAltTile ? pal.t1 : pal.t2;
            if (hash === 0 || vy > 7.8) col = pal.hi;
            else if (hash === 1 || vy < 1.5) col = pal.lo;
            ctx.fillStyle = col;
            ctx.fillRect(px, py, P, P);
          }
        }

        const cliffLeft = Math.round(botL.px / P) * P;
        const cliffRight = Math.round(botR.px / P) * P;
        const cliffTopY = Math.round(botL.py / P) * P;

        for (let dy = 0; dy < slabThickness; dy += P) {
          const cy = cliffTopY + dy;
          for (let cx = cliffLeft; cx <= cliffRight; cx += P) {
            const isLeftPillar = cx < cliffLeft + 36;
            const isRightPillar = cx > cliffRight - 40;
            const isPlaque = cx >= W / 2 - 84 && cx <= W / 2 + 84 && dy >= 8 && dy <= slabThickness - 8;

            let col = pal.cliffMid;
            if (dy === 0 || dy >= slabThickness - P) {
              col = '#000000';
            } else if (dy === P || dy === slabThickness - P * 2) {
              col = pal.border;
            } else if (dy === P * 2) {
              col = '#090604';
            } else if (isLeftPillar || isRightPillar) {
              col = ((cx + dy) / P) % 3 === 0 ? '#fde047' : pal.border;
            } else if (isPlaque) {
              const onPlaqueBorder =
                cx < W / 2 - 76 || cx > W / 2 + 76 || dy < 12 || dy > slabThickness - 12;
              col = onPlaqueBorder ? pal.border : '#0f172a';
            } else {
              const plankIdx = Math.floor((cx - cliffLeft) / 48);
              const isJoint = Math.abs((cx - cliffLeft) % 48) < P;
              if (isJoint) col = pal.cliffBot;
              else if (dy < slabThickness * 0.5) col = plankIdx % 2 === 0 ? pal.cliffTop : pal.cliffMid;
              else col = plankIdx % 2 === 0 ? pal.cliffMid : pal.cliffBot;
            }

            ctx.fillStyle = col;
            ctx.fillRect(cx, cy, P, P);
          }
        }

        ctx.font = 'bold 11px "Silkscreen", "DungGeunMo", monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#000000';
        ctx.fillText('★ 2.5D BATTLE JANGGI ★', W / 2 + 2, cliffTopY + 27);
        ctx.fillStyle = '#fff05a';
        ctx.fillText('★ 2.5D BATTLE JANGGI ★', W / 2, cliffTopY + 25);

        const draw3DPalaceRimAndEmblem = (minY, maxY, skinId) => {
          const c00 = this._projectVisualCoord(3, minY);
          const c10 = this._projectVisualCoord(5, minY);
          const c11 = this._projectVisualCoord(5, maxY);
          const c01 = this._projectVisualCoord(3, maxY);
          this._drawPixelLine(ctx, c00.px, c00.py, c10.px, c10.py, 4, pal.border);
          this._drawPixelLine(ctx, c10.px, c10.py, c11.px, c11.py, 4, pal.border);
          this._drawPixelLine(ctx, c11.px, c11.py, c01.px, c01.py, 4, pal.border);
          this._drawPixelLine(ctx, c01.px, c01.py, c00.px, c00.py, 4, pal.border);

          const midPt = this._projectVisualCoord(4, (minY + maxY) / 2);
          const skinCfg = this.Art.getFactionConfig(skinId);
          ctx.save();
          ctx.translate(midPt.px, midPt.py);
          ctx.scale(midPt.scale, midPt.scale * 0.72);
          this.Art.drawFactionEmblem(ctx, 0, 0, 48, skinCfg.emblem, skinCfg.palette.gold, 0.25);
          ctx.restore();
        };

        draw3DPalaceRimAndEmblem(0, 2, this.boardFlipped ? this.chuSkin : this.hanSkin);
        draw3DPalaceRimAndEmblem(7, 9, this.boardFlipped ? this.hanSkin : this.chuSkin);
      }

      const diagPairs = [
        [3, 0, 5, 2], [5, 0, 3, 2],
        [3, 7, 5, 9], [5, 7, 3, 9]
      ];
      for (const [x1, y1, x2, y2] of diagPairs) {
        const a = this.boardToPixel(x1, y1);
        const b = this.boardToPixel(x2, y2);
        this._drawPixelLine(ctx, a.px, a.py + 2, b.px, b.py + 2, 4, '#000000');
        this._drawPixelLine(ctx, a.px, a.py - 2, b.px, b.py - 2, 4, pal.border);
      }

      for (let y = 0; y < 10; y++) {
        const p1 = this.boardToPixel(0, y);
        const p2 = this.boardToPixel(8, y);
        const minX = Math.min(p1.px, p2.px);
        const maxX = Math.max(p1.px, p2.px);
        ctx.fillStyle = pal.shadow;
        ctx.fillRect(minX, p1.py + 2, maxX - minX + 4, 4);
        ctx.fillStyle = pal.line;
        ctx.fillRect(minX, p1.py - 2, maxX - minX + 4, 4);
      }

      for (let x = 0; x < 9; x++) {
        const p1 = this.boardToPixel(x, 0);
        const p2 = this.boardToPixel(x, 9);
        this._drawPixelLine(ctx, p1.px + 2, p1.py, p2.px + 2, p2.py, 4, pal.shadow);
        this._drawPixelLine(ctx, p1.px - 2, p1.py, p2.px - 2, p2.py, 4, pal.line);
      }

      const starCoords = [
        [1, 2], [7, 2], [0, 3], [2, 3], [4, 3], [6, 3], [8, 3],
        [1, 7], [7, 7], [0, 6], [2, 6], [4, 6], [6, 6], [8, 6]
      ];
      for (const [sx, sy] of starCoords) {
        const pt = this.boardToPixel(sx, sy);
        const hw = this.is3DView() ? Math.max(4, Math.round(6 * pt.scale)) : 6;
        const hh = this.is3DView() ? Math.max(3, Math.round(5 * pt.scale * 0.75)) : 6;
        ctx.fillStyle = '#000000';
        ctx.fillRect(pt.px - hw, pt.py - hh, hw * 2, hh * 2);
        ctx.fillStyle = '#fff05a';
        ctx.fillRect(pt.px - hw + 2, pt.py - hh + 2, (hw - 2) * 2, (hh - 2) * 2);
      }

      ctx.font = 'bold 11px "Silkscreen", "DungGeunMo", monospace';
      ctx.textAlign = 'center';
      for (let x = 0; x < 9; x++) {
        const ptTop = this.boardToPixel(x, 0);
        const labelY = this.is3DView() ? ptTop.py - 18 : 44;
        ctx.fillStyle = '#000000';
        ctx.fillText(`${x + 1}`, ptTop.px + 2, labelY + 2);
        ctx.fillStyle = '#fff05a';
        ctx.fillText(`${x + 1}`, ptTop.px, labelY);
      }
      for (let y = 0; y < 10; y++) {
        const ptLeft = this.boardToPixel(0, y);
        const labelX = this.is3DView() ? ptLeft.px - Math.round(26 * ptLeft.scale) : 42;
        ctx.fillStyle = '#000000';
        ctx.fillText(`${10 - y}`, labelX + 2, ptLeft.py + 5);
        ctx.fillStyle = '#fff05a';
        ctx.fillText(`${10 - y}`, labelX, ptLeft.py + 3);
      }

      this._pixelBoardCache = off;
      this._pixelBoardCacheKey = cacheKey;
      return off;
    }

    _drawPixelPalaceZone(ctx, side, minX, minY, maxX, maxY, skinId) {
      const p1 = this.boardToPixel(minX, minY);
      const p2 = this.boardToPixel(maxX, maxY);
      const left = Math.min(p1.px, p2.px);
      const top = Math.min(p1.py, p2.py);
      const w = Math.abs(p2.px - p1.px);
      const h = Math.abs(p2.py - p1.py);

      const c1 = side === 'CHU' ? '#08382c' : '#4a1219';
      const c2 = side === 'CHU' ? '#062820' : '#360c11';
      for (let y = top; y < top + h; y += 8) {
        for (let x = left; x < left + w; x += 8) {
          ctx.fillStyle = ((x + y) / 8) % 2 === 0 ? c1 : c2;
          ctx.fillRect(x, y, 8, 8);
        }
      }

      ctx.fillStyle = '#f5b700';
      ctx.fillRect(left - 4, top - 4, w + 8, 4);
      ctx.fillRect(left - 4, top + h, w + 8, 4);
      ctx.fillRect(left - 4, top, 4, h);
      ctx.fillRect(left + w, top, 4, h);

      const skinCfg = this.Art.getFactionConfig(skinId);
      this.Art.drawFactionEmblem(
        ctx,
        left + w / 2,
        top + h / 2,
        46,
        skinCfg.emblem,
        skinCfg.palette.gold,
        0.22
      );
    }

    _drawPixelBracketCursor(ctx, cx, cy, halfSize, color, thickness = 4, scale = 1.0) {
      const halfW = Math.round(halfSize * scale);
      const halfH = Math.round(halfSize * scale * (this.is3DView() ? 0.68 : 1.0));
      const lenX = Math.max(8, Math.round(12 * scale));
      const lenY = Math.max(6, Math.round(10 * scale * (this.is3DView() ? 0.72 : 1.0)));
      const x0 = cx - halfW;
      const y0 = cy - halfH;
      const x1 = cx + halfW;
      const y1 = cy + halfH;

      ctx.fillStyle = '#000000';
      ctx.fillRect(x0 - 2, y0 - 2, lenX + 4, thickness + 4);
      ctx.fillRect(x0 - 2, y0 - 2, thickness + 4, lenY + 4);
      ctx.fillRect(x1 - lenX - 2, y0 - 2, lenX + 4, thickness + 4);
      ctx.fillRect(x1 - thickness - 2, y0 - 2, thickness + 4, lenY + 4);
      ctx.fillRect(x0 - 2, y1 - thickness - 2, lenX + 4, thickness + 4);
      ctx.fillRect(x0 - 2, y1 - lenY - 2, thickness + 4, lenY + 4);
      ctx.fillRect(x1 - lenX - 2, y1 - thickness - 2, lenX + 4, thickness + 4);
      ctx.fillRect(x1 - thickness - 2, y1 - lenY - 2, thickness + 4, lenY + 4);

      ctx.fillStyle = color;
      ctx.fillRect(x0, y0, lenX, thickness);
      ctx.fillRect(x0, y0, thickness, lenY);
      ctx.fillRect(x1 - lenX, y0, lenX, thickness);
      ctx.fillRect(x1 - thickness, y0, thickness, lenY);
      ctx.fillRect(x0, y1 - thickness, lenX, thickness);
      ctx.fillRect(x0, y1 - lenY, thickness, lenY);
      ctx.fillRect(x1 - lenX, y1 - thickness, lenX, thickness);
      ctx.fillRect(x1 - thickness, y1 - lenY, thickness, lenY);
    }

    _drawPerspectiveShockwaveRing(ctx, cx, cy, radius, color, thickness = 4, scale = 1.0) {
      const rx = radius * scale;
      const ry = radius * scale * (this.is3DView() ? 0.56 : 0.92);
      const steps = 28;
      const ps = Math.max(3, Math.round(thickness));
      for (let i = 0; i < steps; i++) {
        const ang = (i / steps) * Math.PI * 2;
        const px = Math.round((cx + Math.cos(ang) * rx) / 2) * 2;
        const py = Math.round((cy + Math.sin(ang) * ry) / 2) * 2;
        ctx.fillStyle = '#000000';
        ctx.fillRect(px - ps / 2 - 1, py - ps / 2 - 1, ps + 2, ps + 2);
        ctx.fillStyle = color;
        ctx.fillRect(px - ps / 2, py - ps / 2, ps, ps);
      }
    }

    _drawUnitGroundShadow(ctx, gx, gy, scale = 1.0, zLift = 0) {
      const shrink = Math.max(0.45, 1 - zLift / 110);
      const w = Math.round(52 * scale * shrink);
      const h = Math.round(20 * scale * shrink * (this.is3DView() ? 0.78 : 0.95));
      ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
      ctx.fillRect(Math.round(gx - w / 2), Math.round(gy + 4 * scale - h / 2), w, h);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.30)';
      ctx.fillRect(Math.round(gx - w * 0.36), Math.round(gy + 4 * scale - h * 0.7), Math.round(w * 0.72), Math.round(h * 1.4));
    }

    /**
     * 모바일 터치 드래그 중 손가락 아래 영역을 2배 확대해 보여주는 도트 루페(Magnifier) 렌더링
     */
    _renderTouchLoupe(ctx) {
      if (!this.touchLoupe || !this.touchLoupe.active || !this.boardCanvas) return;
      const { px, py, coord } = this.touchLoupe;
      const loupeSize = 136;
      const srcSize = 68;
      // 손가락이 왼쪽 상단에 있으면 우측 상단에, 아니면 좌측 상단에 표시
      const dstX = px < 220 && py < 220 ? this.canvasWidth - loupeSize - 16 : 16;
      const dstY = 16;

      ctx.save();
      ctx.imageSmoothingEnabled = false;

      // 외곽 황금 프레임
      ctx.fillStyle = '#000000';
      ctx.fillRect(dstX - 6, dstY - 6, loupeSize + 12, loupeSize + 30);
      ctx.fillStyle = '#f5b700';
      ctx.fillRect(dstX - 3, dstY - 3, loupeSize + 6, loupeSize + 6);
      ctx.fillStyle = '#090c15';
      ctx.fillRect(dstX, dstY, loupeSize, loupeSize);

      // 현재 보드 캔버스(HiDPI 물리 버퍼)에서 손가락 주변을 2배 확대 복사
      const scale = this.renderScale || 2.5;
      const sx = Math.max(0, Math.min(this.canvasWidth - srcSize, Math.round(px - srcSize / 2)));
      const sy = Math.max(0, Math.min(this.canvasHeight - srcSize, Math.round(py - srcSize / 2)));
      ctx.drawImage(
        this.boardCanvas,
        Math.round(sx * scale),
        Math.round(sy * scale),
        Math.round(srcSize * scale),
        Math.round(srcSize * scale),
        dstX,
        dstY,
        loupeSize,
        loupeSize
      );

      // 중앙 도트 십자선
      const midX = dstX + loupeSize / 2;
      const midY = dstY + loupeSize / 2;
      ctx.fillStyle = '#00e5a3';
      ctx.fillRect(midX - 10, midY - 1, 20, 2);
      ctx.fillRect(midX - 1, midY - 10, 2, 20);

      // 하단 좌표/기물 안내 라벨
      ctx.fillStyle = '#090c15';
      ctx.fillRect(dstX - 3, dstY + loupeSize + 3, loupeSize + 6, 18);
      ctx.font = 'bold 11px "Silkscreen", "DungGeunMo", monospace';
      ctx.textAlign = 'center';
      ctx.fillStyle = '#fff05a';
      let label = '범위 밖';
      if (coord) {
        const p = this.game.getPieceAt(coord.x, coord.y);
        const sqText = this.isChessMode() && this.Engine.toAlgebraic
          ? this.Engine.toAlgebraic(coord.x, coord.y)
          : `(${coord.x + 1},${10 - coord.y})`;
        label = p ? `${sqText} ${p.kr}(${p.hanja})` : `${sqText} 빈칸`;
      }
      ctx.fillText(label, dstX + loupeSize / 2, dstY + loupeSize + 16);
      ctx.restore();
    }

    /**
     * 60FPS 메인 렌더링 루프 (스마트폰 발열/배터리 절약을 위한 더티 체킹 최적화 포함)
     */
    render(now) {
      const steppedNow = Math.floor(now / 95) * 95;
      const duelActive = Boolean(this.Director && this.Director.boardDuel && this.Director.boardDuel.active);
      const camActive = Boolean(this.Director && this.Director.boardCamera && this.Director.boardCamera.active);
      const codexOpen = Boolean(document.getElementById('codex-modal')?.classList.contains('open'));
      const showcaseOpen = Boolean(document.getElementById('showcase-modal')?.classList.contains('open'));
      const hasActiveAnim =
        Boolean(this.marchAnim) ||
        duelActive ||
        camActive ||
        this.boardFxList.length > 0 ||
        Boolean(this.touchLoupe && this.touchLoupe.active);

      const selKey = this.selectedCoord ? `${this.selectedCoord.x},${this.selectedCoord.y}` : '-';
      const hovKey = this.hoveredCoord ? `${this.hoveredCoord.x},${this.hoveredCoord.y}` : '-';
      const inspKey = this.inspectedPiece ? `${this.inspectedPiece.id}_${this.inspectedPiece.type}` : '-';
      const signature = `${steppedNow}_${this.boardGameType}_${this.game.turnCount}_${this.boardFlipped}_${selKey}_${hovKey}_${inspKey}_${this.chuSkin}_${this.hanSkin}`;

      if (!this._forceRedraw && !hasActiveAnim && !codexOpen && !showcaseOpen && signature === this._lastRenderSignature) {
        return;
      }

      this._lastRenderSignature = signature;
      this._forceRedraw = false;

      if (this.boardCtx) {
        this._renderBoardStage(this.boardCtx, now, steppedNow);
        if (this.touchLoupe && this.touchLoupe.active) {
          this._renderTouchLoupe(this.boardCtx);
        }
      }
      if (this.inspectorCtx && this.inspectedPiece) {
        this._renderInspectorUnit(this.inspectorCtx, steppedNow);
      }
      if (codexOpen) {
        this._renderCodexModalUnits(steppedNow);
      }
      if (showcaseOpen) {
        this._renderShowcaseStage(now);
      }
    }

    _renderBoardStage(ctx, now, steppedNow) {
      const W = this.canvasWidth;
      const H = this.canvasHeight;
      const scale = this.renderScale || 2.5;
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.save();
      ctx.imageSmoothingEnabled = false;

      const cam = this.Director ? this.Director.boardCamera : null;
      const duel = this.Director && this.Director.boardDuel && this.Director.boardDuel.active
        ? this.Director.boardDuel
        : null;

      if (cam && cam.active) {
        const focusPt = this.boardToPixel(cam.focusX, cam.focusY);
        ctx.translate(W / 2 + cam.shakeX, H / 2 + cam.shakeY);
        ctx.scale(cam.zoom, cam.zoom);
        ctx.translate(-focusPt.px, -focusPt.py);
      }

      // 1. 캐싱된 2.5D/2D HiDPI 도트 보드 표면 블릿
      const boardSurface = this._ensurePixelBoardSurface();
      ctx.drawImage(boardSurface, 0, 0, W, H);

      // 2. 직전 착수(Last Move) 도트 궤적 표시
      const lastMove = this.game.history.length > 0
        ? this.game.history[this.game.history.length - 1].move
        : null;
      if (lastMove && !lastMove.isPass && !duel) {
        const fp = this.boardToPixel(lastMove.fromX, lastMove.fromY);
        const tp = this.boardToPixel(lastMove.toX, lastMove.toY);
        this._drawPixelLine(ctx, fp.px, fp.py, tp.px, tp.py, 4, '#fff05a');
        ctx.fillStyle = '#f5b700';
        ctx.fillRect(fp.px - 6, fp.py - 5, 12, 10);
        this._drawPixelBracketCursor(ctx, tp.px, tp.py, 30, '#f5b700', 4, tp.scale);
      }

      // 3. 마우스/터치 호버 도트 커서 `[ ]`
      if (this.hoveredCoord && !this.isBusy && !duel) {
        const hp = this.boardToPixel(this.hoveredCoord.x, this.hoveredCoord.y);
        const blink = Math.floor(now / 180) % 2 === 0;
        this._drawPixelBracketCursor(ctx, hp.px, hp.py, blink ? 32 : 29, '#38bdf8', 4, hp.scale);
      }

      // 4. 합법 이동 마커 (일반 이동: 에메랄드, 캐슬링: 골드/시안, 프로모션: 골드 마커)
      const blinkStep = Math.floor(now / 200) % 2 === 0;
      for (const mv of this.legalMeta.moves) {
        if (!mv.isCapture) {
          const pt = this.boardToPixel(mv.toX, mv.toY);
          const szX = Math.round((blinkStep ? 22 : 18) * pt.scale);
          const szY = Math.round(szX * (this.is3DView() ? 0.68 : 1.0));
          ctx.fillStyle = '#000000';
          ctx.fillRect(pt.px - szX / 2 - 2, pt.py - szY / 2 - 2, szX + 4, szY + 4);
          ctx.fillStyle = mv.isCastling ? '#38bdf8' : mv.isPromotion ? '#fde047' : '#00e5a3';
          ctx.fillRect(pt.px - szX / 2, pt.py - szY / 2, szX, szY);
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(pt.px - 3, pt.py - 2, 6, 4);
        }
      }

      if (duel) {
        const dstPt = this.boardToPixel(duel.move.toX, duel.move.toY);
        if (duel.flashFrame) {
          ctx.fillStyle = 'rgba(254, 240, 138, 0.28)';
          ctx.fillRect(0, 0, W, H);
        }
        for (const sw of duel.shockwaves) {
          this._drawPerspectiveShockwaveRing(ctx, dstPt.px, dstPt.py, sw.r, sw.color, sw.width, dstPt.scale);
        }
      }

      this._renderBoardAmbientFX(ctx, now);

      // 5. 보드 위 모든 기물을 Y좌표(원근 깊이) 순으로 정렬하여 HD-2D 입간판처럼 렌더링
      const rows = this.getBoardRows();
      const cols = this.getBoardCols();
      const piecesToDraw = [];
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const p = this.game.board[y] ? this.game.board[y][x] : null;
          if (!p) continue;
          if (
            this.marchAnim &&
            ((this.marchAnim.fromX === x && this.marchAnim.fromY === y) ||
              (this.marchAnim.rookPiece && this.marchAnim.rookFromX === x && this.marchAnim.rookY === y))
          ) {
            continue;
          }
          if (
            duel &&
            ((duel.move.fromX === x && duel.move.fromY === y) ||
              (duel.move.toX === x && duel.move.toY === y) ||
              (duel.move.isEnPassant &&
                duel.move.enPassantCapturedCoord &&
                duel.move.enPassantCapturedCoord.x === x &&
                duel.move.enPassantCapturedCoord.y === y))
          ) {
            continue;
          }
          const pt = this.boardToPixel(x, y);
          piecesToDraw.push({ piece: p, px: pt.px, py: pt.py, scale: pt.scale });
        }
      }

      piecesToDraw.sort((a, b) => a.py - b.py);

      const viewScaleBoost = this.is3DView() ? 1.06 : 1.0;

      for (const item of piecesToDraw) {
        const p = item.piece;
        const isSelected =
          this.selectedCoord &&
          this.selectedCoord.x === p.x &&
          this.selectedCoord.y === p.y;
        const isKingChecked =
          p.type === 'KING' &&
          this.game.inCheck &&
          p.side === this.game.currentTurn;

        const zLift = isSelected && this.is3DView()
          ? Math.round(10 + Math.sin(now / 130) * 3)
          : 0;

        if (this.is3DView()) {
          this._drawUnitGroundShadow(ctx, item.px, item.py, item.scale, zLift);
        }

        if (isSelected) {
          this._drawPixelBracketCursor(ctx, item.px, item.py, 34, '#fff05a', 4, item.scale);
          if (this.is3DView()) {
            this._drawPerspectiveShockwaveRing(ctx, item.px, item.py, 28, '#fde047', 3, item.scale);
          }
        }

        this.Art.drawUnit(ctx, {
          x: item.px,
          y: item.py - zLift,
          type: p.type,
          side: p.side,
          faction: this.getSkinForSide(p.side),
          state: isSelected ? 'MOVE' : 'IDLE',
          progress: 0,
          time: steppedNow,
          scale: item.scale * viewScaleBoost,
          facing: p.side === 'CHU' ? 1 : -1,
          showPedestal: true,
          isSelected,
          isCheck: isKingChecked
        });
      }

      // 6. 일반 행군 & 캐슬링 동시 기동 애니메이션 렌더링
      if (this.marchAnim) {
        const ma = this.marchAnim;
        const rawT = Math.min(1, Math.max(0, (now - ma.startTime) / ma.duration));
        const t = Math.floor(rawT * 8) / 8;
        const curBx = ma.fromX + (ma.toX - ma.fromX) * t;
        const curBy = ma.fromY + (ma.toY - ma.fromY) * t;
        const groundPt = this.boardToPixel(curBx, curBy);
        const fp = this.boardToPixel(ma.fromX, ma.fromY);
        const tp = this.boardToPixel(ma.toX, ma.toY);

        const isHeavyJumper =
          ma.piece.type === 'HORSE' ||
          ma.piece.type === 'KNIGHT' ||
          ma.piece.type === 'ELEPHANT' ||
          ma.piece.type === 'CANNON';
        const jumpHeight = isHeavyJumper ? 40 : (this.is3DView() ? 18 : 0);
        const zLift = Math.round((Math.sin(t * Math.PI) * jumpHeight) / 2) * 2;

        this._drawUnitGroundShadow(ctx, groundPt.px, groundPt.py, groundPt.scale, zLift);

        this.Art.drawUnit(ctx, {
          x: groundPt.px,
          y: groundPt.py - zLift,
          type: ma.piece.type,
          side: ma.piece.side,
          faction: this.getSkinForSide(ma.piece.side),
          state: 'MOVE',
          progress: t,
          time: steppedNow,
          scale: groundPt.scale * viewScaleBoost * 1.08,
          facing: tp.px >= fp.px ? 1 : -1,
          showPedestal: true,
          isSelected: true
        });

        // 캐슬링 시 룩 동시 슬라이드 렌더링
        if (ma.rookPiece && ma.rookFromX !== null && ma.rookToX !== null) {
          const curRx = ma.rookFromX + (ma.rookToX - ma.rookFromX) * t;
          const rPt = this.boardToPixel(curRx, ma.rookY);
          const rLift = Math.round(Math.sin(t * Math.PI) * 14);
          this._drawUnitGroundShadow(ctx, rPt.px, rPt.py, rPt.scale, rLift);
          this.Art.drawUnit(ctx, {
            x: rPt.px,
            y: rPt.py - rLift,
            type: ma.rookPiece.type,
            side: ma.rookPiece.side,
            faction: this.getSkinForSide(ma.rookPiece.side),
            state: 'MOVE',
            progress: t,
            time: steppedNow,
            scale: rPt.scale * viewScaleBoost * 1.06,
            facing: ma.rookToX >= ma.rookFromX ? 1 : -1,
            showPedestal: true,
            isSelected: true
          });
        }
      }

      if (duel) {
        this._renderOnBoardDuel(ctx, duel, now, steppedNow, viewScaleBoost);
      }

      // 7. 포획 가능 적 기물 도트 타겟 브래킷 (`[ATK]`), 캐슬링(`[O-O]`), 프로모션(`[UP]`) 인디케이터
      if (!duel) {
        for (const mv of this.legalMeta.moves) {
          if (mv.isCapture || mv.isCastling || mv.isPromotion) {
            const pt = this.boardToPixel(mv.toX, mv.toY);
            const half = blinkStep ? 34 : 30;
            const bCol = mv.isCapture ? '#ff3b5c' : mv.isCastling ? '#38bdf8' : '#fde047';
            const tagTxt = mv.isEnPassant ? 'E.P' : mv.isCapture ? 'ATK' : mv.isCastling ? 'O-O' : 'UP!';
            this._drawPixelBracketCursor(ctx, pt.px, pt.py, half, bCol, 4, pt.scale);

            ctx.save();
            ctx.fillStyle = '#000000';
            ctx.fillRect(pt.px + 10, pt.py - 38 * pt.scale, 30, 16);
            ctx.fillStyle = bCol;
            ctx.fillRect(pt.px + 12, pt.py - 38 * pt.scale + 2, 26, 12);
            ctx.font = 'bold 10px "Silkscreen", monospace';
            ctx.textAlign = 'center';
            ctx.fillStyle = mv.isPromotion && !mv.isCapture ? '#000000' : '#ffffff';
            ctx.fillText(tagTxt, pt.px + 25, pt.py - 38 * pt.scale + 11);
            ctx.restore();
          }
        }

        for (const br of this.legalMeta.bridges) {
          const pt = this.boardToPixel(br.x, br.y);
          this.Art.drawTacticalIndicator(ctx, 'CANNON_BRIDGE', pt.px, pt.py, { time: steppedNow });
        }

        for (const nk of this.legalMeta.blockedNecks) {
          const pt = this.boardToPixel(nk.x, nk.y);
          this.Art.drawTacticalIndicator(ctx, 'BLOCKED_MYEOK', pt.px, pt.py, { time: steppedNow });
        }

        if (this.game.inCheck && this.game.checkAttackers.length > 0) {
          for (const atk of this.game.checkAttackers) {
            const fp = this.boardToPixel(atk.from.x, atk.from.y);
            const tp = this.boardToPixel(atk.to.x, atk.to.y);
            this.Art.drawTacticalIndicator(ctx, 'THREAT_LINE', fp.px, fp.py, {
              toX: tp.px,
              toY: tp.py,
              time: steppedNow
            });
          }
        }
      }

      ctx.restore();
    }

    _renderBoardAmbientFX(ctx, now) {
      for (let i = this.boardFxList.length - 1; i >= 0; i--) {
        const fx = this.boardFxList[i];
        const elapsed = now - fx.startTime;
        if (elapsed >= fx.duration) {
          this.boardFxList.splice(i, 1);
          continue;
        }
        const prog = elapsed / fx.duration;
        const pt = this.boardToPixel(fx.bx, fx.by);

        const maxR = fx.kind === 'CHECK' || fx.kind === 'PROMOTION' ? 58 : 38;
        const curR = 10 + (maxR - 10) * prog;
        this._drawPerspectiveShockwaveRing(
          ctx,
          pt.px,
          pt.py,
          curR,
          fx.color,
          fx.kind === 'CHECK' || fx.kind === 'PROMOTION' ? 5 : 3,
          pt.scale
        );

        if ((fx.kind === 'CHECK' || fx.kind === 'PROMOTION') && prog < 0.65) {
          ctx.fillStyle = fx.kind === 'PROMOTION' ? '#f5b700' : '#ff3b5c';
          ctx.fillRect(pt.px - 6, pt.py - 160, 12, 160);
          ctx.fillStyle = '#fff05a';
          ctx.fillRect(pt.px - 2, pt.py - 160, 4, 160);
        }

        for (const p of fx.particles) {
          p.dx += p.vx * 0.45;
          p.dy += p.vy * 0.45;
          p.dz += p.vz * 0.45;
          p.vz -= 0.35;
          if (p.dz < 0) p.dz = 0;
          const rx = Math.round(pt.px + p.dx * pt.scale);
          const ry = Math.round(pt.py + (p.dy - p.dz) * pt.scale);
          ctx.fillStyle = '#000000';
          ctx.fillRect(rx - 1, ry - 1, p.size + 2, p.size + 2);
          ctx.fillStyle = p.color;
          ctx.fillRect(rx, ry, p.size, p.size);
        }
      }
    }

    _renderOnBoardDuel(ctx, duel, now, steppedNow, viewScaleBoost) {
      const mv = duel.move;
      const t = duel.t;
      const rawT = duel.rawT;
      const atkP = duel.atkPiece;
      const defP = duel.defPiece;
      const atkSkin = this.getSkinForSide(atkP.side);
      const defSkin = this.getSkinForSide(defP.side);

      const fromPt = this.boardToPixel(mv.fromX, mv.fromY);
      const toPt = this.boardToPixel(mv.toX, mv.toY);
      const dirX = toPt.px >= fromPt.px ? 1 : -1;

      let atkGroundX = fromPt.px;
      let atkGroundY = fromPt.py;
      let atkScale = fromPt.scale;
      let atkZLift = 0;
      let atkState = 'MOVE';
      let atkProg = 0;

      if (duel.isRanged) {
        if (t < 0.76) {
          atkGroundX = fromPt.px;
          atkGroundY = fromPt.py;
          atkScale = fromPt.scale;
          atkState = t < 0.62 ? 'ATTACK' : 'IDLE';
          atkProg = Math.min(1, t / 0.55);
        } else {
          const advT = (t - 0.76) / 0.24;
          const curBx = mv.fromX + (mv.toX - mv.fromX) * advT;
          const curBy = mv.fromY + (mv.toY - mv.fromY) * advT;
          const advPt = this.boardToPixel(curBx, curBy);
          atkGroundX = advPt.px;
          atkGroundY = advPt.py;
          atkScale = advPt.scale;
          atkZLift = Math.sin(advT * Math.PI) * 20;
          atkState = 'MOVE';
          atkProg = advT;
        }
      } else {
        const standoffOffset = -dirX * 34 * toPt.scale;
        if (t < 0.34) {
          const chgT = t / 0.34;
          const curBx = mv.fromX + (mv.toX - mv.fromX) * chgT;
          const curBy = mv.fromY + (mv.toY - mv.fromY) * chgT;
          const chgPt = this.boardToPixel(curBx, curBy);
          atkGroundX = chgPt.px + standoffOffset * chgT;
          atkGroundY = chgPt.py;
          atkScale = chgPt.scale;
          if (atkP.type === 'HORSE' || atkP.type === 'KNIGHT' || atkP.type === 'ELEPHANT') {
            atkZLift = Math.sin(chgT * Math.PI) * 44;
          } else {
            atkZLift = Math.sin(chgT * Math.PI) * 14;
          }
          atkState = 'MOVE';
          atkProg = chgT;

          if (atkP.type === 'CHARIOT' || atkP.type === 'ROOK' || atkP.type === 'QUEEN' || atkP.type === 'HORSE' || atkP.type === 'KNIGHT') {
            const trailPt = this.boardToPixel(
              mv.fromX + (mv.toX - mv.fromX) * Math.max(0, chgT - 0.18),
              mv.fromY + (mv.toY - mv.fromY) * Math.max(0, chgT - 0.18)
            );
            ctx.save();
            ctx.globalAlpha = 0.38;
            this.Art.drawUnit(ctx, {
              x: trailPt.px,
              y: trailPt.py,
              type: atkP.type,
              side: atkP.side,
              faction: atkSkin,
              state: 'MOVE',
              progress: chgT,
              time: steppedNow,
              scale: trailPt.scale * viewScaleBoost * 1.1,
              facing: dirX,
              showPedestal: false
            });
            ctx.restore();
          }
        } else if (t < 0.84) {
          atkGroundX = toPt.px + standoffOffset * 0.72;
          atkGroundY = toPt.py;
          atkScale = toPt.scale;
          atkState = 'ATTACK';
          atkProg = (t - 0.34) / 0.50;
        } else {
          const finT = (t - 0.84) / 0.16;
          atkGroundX = toPt.px + standoffOffset * 0.72 * (1 - finT);
          atkGroundY = toPt.py;
          atkScale = toPt.scale;
          atkState = 'IDLE';
          atkProg = 1;
        }
      }

      let defState = 'IDLE';
      let defProg = 0;
      let defKnockX = 0;
      if (t >= 0.36 && t < 0.60) {
        defState = 'HIT';
        defProg = (t - 0.36) / 0.24;
        defKnockX = dirX * (Math.floor(now / 30) % 2 === 0 ? 8 : -4);
      } else if (t >= 0.60) {
        defState = 'DEATH';
        defProg = Math.min(1, (t - 0.60) / 0.36);
        defKnockX = dirX * 10;
      }

      const renderDefenderOnBoard = () => {
        if (defState === 'DEATH' && defProg >= 0.98) return;
        this._drawUnitGroundShadow(ctx, toPt.px + defKnockX, toPt.py, toPt.scale, 0);
        this.Art.drawUnit(ctx, {
          x: toPt.px + defKnockX,
          y: toPt.py,
          type: defP.type,
          side: defP.side,
          faction: defSkin,
          state: defState,
          progress: defProg,
          time: steppedNow,
          scale: toPt.scale * viewScaleBoost * 1.12,
          facing: -dirX,
          showPedestal: defState !== 'DEATH',
          isCheck: defState === 'HIT'
        });

        if (rawT < 0.72) {
          const barW = Math.round(52 * toPt.scale);
          const barH = 8;
          const bx = Math.round(toPt.px + defKnockX - barW / 2);
          const by = Math.round(toPt.py - 68 * toPt.scale);
          ctx.fillStyle = '#000000';
          ctx.fillRect(bx - 2, by - 2, barW + 4, barH + 4);
          ctx.fillStyle = '#1e293b';
          ctx.fillRect(bx, by, barW, barH);
          ctx.fillStyle = duel.hpRatio > 0.5 ? '#10b981' : '#ef4444';
          ctx.fillRect(bx, by, Math.round(barW * duel.hpRatio), barH);
        }
      };

      const renderAttackerOnBoard = () => {
        this._drawUnitGroundShadow(ctx, atkGroundX, atkGroundY, atkScale, atkZLift);
        this.Art.drawUnit(ctx, {
          x: atkGroundX,
          y: atkGroundY - atkZLift,
          type: atkP.type,
          side: atkP.side,
          faction: atkSkin,
          state: atkState,
          progress: atkProg,
          time: steppedNow,
          scale: atkScale * viewScaleBoost * 1.16,
          facing: dirX,
          showPedestal: true,
          isSelected: true
        });
      };

      if (atkGroundY <= toPt.py) {
        renderAttackerOnBoard();
        renderDefenderOnBoard();
      } else {
        renderDefenderOnBoard();
        renderAttackerOnBoard();
      }

      if (duel.isRanged && rawT >= 0.08 && rawT <= 0.56) {
        const projT = Math.min(1, (rawT - 0.08) / 0.42);
        const curBx = mv.fromX + (mv.toX - mv.fromX) * projT;
        const curBy = mv.fromY + (mv.toY - mv.fromY) * projT;
        const gPt = this.boardToPixel(curBx, curBy);
        const arcZ = Math.sin(projT * Math.PI) * 145;

        ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
        ctx.fillRect(gPt.px - 10, gPt.py - 4, 20, 8);

        if (atkP.type === 'BISHOP') {
          const px = gPt.px;
          const py = Math.round(gPt.py - arcZ * 0.6);
          ctx.fillStyle = '#38bdf8';
          ctx.fillRect(px - 10, py - 10, 20, 20);
          ctx.fillStyle = '#fef08a';
          ctx.fillRect(px - 5, py - 5, 10, 10);
        } else if (atkSkin === 'GORYEO') {
          for (let rIdx = -2; rIdx <= 2; rIdx++) {
            const rx = Math.round(gPt.px + rIdx * 10);
            const ry = Math.round(gPt.py - arcZ + Math.abs(rIdx) * 7);
            ctx.fillStyle = '#fde047';
            ctx.fillRect(rx - dirX * 12, ry - 2, 12, 4);
            ctx.fillStyle = '#ef4444';
            ctx.fillRect(rx - 3, ry - 3, 6, 6);
          }
        } else {
          const px = gPt.px;
          const py = Math.round(gPt.py - arcZ);
          const colOuter = atkSkin === 'BYZANTINE' ? '#10b981' : '#ea580c';
          ctx.fillStyle = '#000000';
          ctx.fillRect(px - 14, py - 14, 28, 28);
          ctx.fillStyle = colOuter;
          ctx.fillRect(px - 12, py - 12, 24, 24);
          ctx.fillStyle = '#facc15';
          ctx.fillRect(px - 7, py - 7, 14, 14);
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(px - 3, py - 3, 6, 6);
        }
      }

      if (rawT >= 0.36 && rawT <= 0.76) {
        const ix = toPt.px;
        const iy = Math.round(toPt.py - 20 * toPt.scale);
        const ps = Math.max(4, Math.round(6 * toPt.scale));

        if (atkP.type === 'KING' || atkP.type === 'QUEEN') {
          ctx.fillStyle = atkP.type === 'QUEEN' ? '#e879f9' : '#f5b700';
          ctx.fillRect(ix - ps * 2, iy - 220, ps * 4, 230);
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(ix - ps, iy - 220, ps * 2, 230);
        } else if (duel.isRanged) {
          const expR = Math.round(38 * toPt.scale * Math.sin(((rawT - 0.36) / 0.4) * Math.PI));
          ctx.fillStyle = atkP.type === 'BISHOP' ? '#38bdf8' : '#ea580c';
          ctx.fillRect(ix - expR, iy - expR, expR * 2, expR * 2);
          ctx.fillStyle = '#fde047';
          ctx.fillRect(ix - expR * 0.65, iy - expR * 0.65, expR * 1.3, expR * 1.3);
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(ix - expR * 0.3, iy - expR * 0.3, expR * 0.6, expR * 0.6);
        } else {
          for (let step = -6; step <= 6; step++) {
            ctx.fillStyle = '#000000';
            ctx.fillRect(ix + step * ps - 2, iy + step * ps - 2, ps + 4, ps + 4);
            ctx.fillRect(ix + step * ps - 2, iy - step * ps - 2, ps + 4, ps + 4);
            ctx.fillStyle = step % 2 === 0 ? '#fff05a' : '#ff3b5c';
            ctx.fillRect(ix + step * ps, iy + step * ps, ps, ps);
            ctx.fillRect(ix + step * ps, iy - step * ps, ps, ps);
          }
        }
      }

      for (const pt of duel.particles) {
        const px = Math.round(toPt.px + pt.dx * toPt.scale);
        const groundPy = Math.round(toPt.py + pt.dy * toPt.scale);
        const airPy = Math.round(groundPy - pt.dz * toPt.scale);

        ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
        ctx.fillRect(px, groundPy, pt.size, Math.max(2, Math.round(pt.size * 0.5)));

        ctx.fillStyle = '#000000';
        ctx.fillRect(px - 2, airPy - 2, pt.size + 4, pt.size + 4);
        ctx.fillStyle = pt.color;
        ctx.fillRect(px, airPy, pt.size, pt.size);
      }

      for (const dp of duel.popups) {
        const floatY = Math.round(toPt.py + dp.dy * toPt.scale - Math.min(34, dp.age * 1.6));
        const floatX = Math.round(toPt.px + (dp.dx || 0));
        ctx.save();
        const fontPx = Math.round(18 * (dp.scale || 1.0));
        ctx.font = `bold ${fontPx}px "Silkscreen", "DungGeunMo", monospace`;
        ctx.textAlign = 'center';
        ctx.fillStyle = '#000000';
        ctx.fillText(dp.text, floatX + 3, floatY + 3);
        ctx.fillText(dp.text, floatX - 2, floatY - 2);
        ctx.fillStyle = dp.color;
        ctx.fillText(dp.text, floatX, floatY);
        ctx.restore();
      }
    }

    _renderInspectorUnit(ctx, steppedNow) {
      const W = this.inspectorCanvas._logicalWidth || 88;
      const H = this.inspectorCanvas._logicalHeight || 88;
      const scale = this.inspectorCanvas._renderScale || 2.5;
      ctx.setTransform(scale, 0, 0, scale, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, W, H);
      const p = this.inspectedPiece;
      if (!p) return;

      this.Art.drawUnit(ctx, {
        x: W / 2,
        y: H * 0.72,
        type: p.type,
        side: p.side,
        faction: this.getSkinForSide(p.side),
        state: 'IDLE',
        progress: 0,
        time: steppedNow,
        scale: 1.05,
        facing: 1,
        showPedestal: true
      });
    }

    // ==========================================================================
    // 정예병 도감(Unit Codex: 장기 7병종 + 체스 6병종) & 배틀 쇼케이스 모달
    // ==========================================================================

    _getCodexClassList() {
      if (this.codexGameFilter === 'JANGGI') {
        return ['KING', 'CHARIOT', 'CANNON', 'HORSE', 'ELEPHANT', 'GUARD', 'SOLDIER'];
      }
      if (this.codexGameFilter === 'CHESS') {
        return ['KING', 'QUEEN', 'ROOK', 'BISHOP', 'KNIGHT', 'PAWN'];
      }
      return [
        'KING', 'QUEEN', 'ROOK', 'BISHOP', 'KNIGHT', 'PAWN',
        'CHARIOT', 'CANNON', 'HORSE', 'ELEPHANT', 'GUARD', 'SOLDIER'
      ];
    }

    _rebuildCodexCards() {
      const grid = document.getElementById('codex-unit-grid');
      if (!grid) return;

      const classes = this._getCodexClassList();
      grid.innerHTML = '';
      this.codexCanvases = [];

      classes.forEach((type) => {
        const card = document.createElement('div');
        card.className = 'codex-unit-card';
        const descKey = type === 'KING' && this.codexGameFilter === 'CHESS' ? 'KING_CHESS' : type;
        card.innerHTML = `
          <canvas width="110" height="110" data-codex-type="${type}"></canvas>
          <div>
            <div style="font-size:14.5px;font-weight:700;color:#fff05a;text-shadow:0 1px 2px #000;" id="codex-title-${type}"></div>
            <div style="font-size:12.5px;color:#38bdf8;margin:3px 0 5px;text-shadow:0 1px 2px #000;" id="codex-sub-${type}"></div>
            <div style="font-size:12.5px;color:#e2e8f0;line-height:1.4;">${PIECE_RULE_DESCRIPTIONS[descKey] || PIECE_RULE_DESCRIPTIONS[type] || ''}</div>
          </div>
        `;
        grid.appendChild(card);
        const cvs = card.querySelector('canvas');
        const cCtx = this._setupHiDPICanvas(cvs, 110, 110, 2.5);
        this.codexCanvases.push({ type, canvas: cvs, ctx: cCtx });
      });

      this._updateCodexTitles();
    }

    _initCodexGrid() {
      this._rebuildCodexCards();

      const facBtns = document.querySelectorAll('[data-codex-faction]');
      facBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          facBtns.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          this.codexFaction = btn.getAttribute('data-codex-faction');
          this.SFX.playSelect();
          this._updateCodexTitles();
          this._forceRedraw = true;
        });
      });

      const gameBtns = document.querySelectorAll('[data-codex-game]');
      gameBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          gameBtns.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          this.codexGameFilter = btn.getAttribute('data-codex-game') || 'ALL';
          this.SFX.playSelect();
          this._rebuildCodexCards();
          this._forceRedraw = true;
        });
      });

      const poseBtns = document.querySelectorAll('[data-codex-pose]');
      poseBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          poseBtns.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');
          this.codexPose = btn.getAttribute('data-codex-pose');
          this.SFX.playSelect();
          this._forceRedraw = true;
        });
      });
    }

    _updateCodexTitles() {
      const loreFac = global.FACTION_COMBAT_LORE[this.codexFaction] || global.FACTION_COMBAT_LORE.GORYEO;
      const classes = this._getCodexClassList();
      classes.forEach((type) => {
        const uLore = loreFac.units[type];
        const meta = this.Art.getUnitMeta(type, this.codexFaction, 'CHU');
        const tEl = document.getElementById(`codex-title-${type}`);
        const sEl = document.getElementById(`codex-sub-${type}`);
        if (tEl) tEl.textContent = `${meta.unitTitle} (${meta.hanjaChar})`;
        if (sEl && uLore) {
          const scoreStr = type === 'KING' ? '총사령관' : `${meta.score}점`;
          sEl.textContent = `[${scoreStr}] 무장: ${uLore.weapon}`;
        }
      });
    }

    _renderCodexModalUnits(steppedNow) {
      const modal = document.getElementById('codex-modal');
      if (!modal || !modal.classList.contains('open')) return;

      const animProgress = Math.floor(((steppedNow % 1200) / 1200) * 8) / 8;
      for (const item of this.codexCanvases) {
        const { type, canvas, ctx } = item;
        const logW = canvas._logicalWidth || 110;
        const logH = canvas._logicalHeight || 110;
        const scale = canvas._renderScale || 2.5;
        ctx.setTransform(scale, 0, 0, scale, 0, 0);
        ctx.imageSmoothingEnabled = false;
        ctx.clearRect(0, 0, logW, logH);
        this.Art.drawUnit(ctx, {
          x: logW / 2,
          y: logH * 0.74,
          type,
          side: this.codexFaction === 'GORYEO' || this.codexFaction === 'MAMLUK' ? 'CHU' : 'HAN',
          faction: this.codexFaction,
          state: this.codexPose,
          progress: animProgress,
          time: steppedNow,
          scale: 1.15,
          facing: 1,
          showPedestal: true
        });
      }
    }

    triggerShowcaseReplay() {
      const atkFacEl = document.getElementById('sc-atk-faction');
      const atkTypeEl = document.getElementById('sc-atk-type');
      const defFacEl = document.getElementById('sc-def-faction');
      const defTypeEl = document.getElementById('sc-def-type');

      this.showcaseState.atkFaction = atkFacEl ? atkFacEl.value : 'GORYEO';
      this.showcaseState.atkType = atkTypeEl ? atkTypeEl.value : 'CANNON';
      this.showcaseState.defFaction = defFacEl ? defFacEl.value : 'TEMPLAR';
      this.showcaseState.defType = defTypeEl ? defTypeEl.value : 'CHARIOT';
      this.showcaseState.startTime = performance.now();
      this.showcaseState.playing = true;
      this._forceRedraw = true;

      if (this.showcaseState.atkType === 'CANNON') {
        this.SFX.playCannonFire(0.25);
      } else {
        this.SFX.playHorseGallop(3);
        this.SFX.playHeavySlash(0.5);
      }
    }

    triggerFullArenaShowcase() {
      this.triggerShowcaseReplay();
      const atkP = {
        id: 'SC_ATK',
        side: 'CHU',
        type: this.showcaseState.atkType,
        x: 2,
        y: 5,
        score: 9,
        kr: this.showcaseState.atkType,
        hanja: '⚔'
      };
      const defP = {
        id: 'SC_DEF',
        side: 'HAN',
        type: this.showcaseState.defType,
        x: 6,
        y: 5,
        score: 5,
        kr: this.showcaseState.defType,
        hanja: '🛡'
      };
      const dummyMove = {
        fromX: 2,
        fromY: 5,
        toX: 6,
        toY: 5,
        piece: atkP,
        captured: defP,
        isCapture: true
      };

      const prevMode = this.Director.getMode();
      this.Director.setMode('ARENA_OVERLAY');
      this.Director.playCaptureCinematic({
        move: dummyMove,
        attackerSkin: this.showcaseState.atkFaction,
        defenderSkin: this.showcaseState.defFaction,
        onComplete: () => {
          this.Director.setMode(prevMode);
        }
      });
    }

    _renderShowcaseStage(now) {
      const modal = document.getElementById('showcase-modal');
      if (!modal || !modal.classList.contains('open') || !this.showcaseCtx) return;

      const logW = this.showcaseCanvas._logicalWidth || 920;
      const logH = this.showcaseCanvas._logicalHeight || 500;
      const scale = this.showcaseCanvas._renderScale || 2.0;
      this.showcaseCtx.setTransform(scale, 0, 0, scale, 0, 0);
      this.showcaseCtx.imageSmoothingEnabled = false;
      const sc = this.showcaseState;
      const elapsed = now - sc.startTime;
      const rawProg = sc.playing ? ((elapsed % sc.duration) / sc.duration) : 0;
      const steppedProg = Math.floor(rawProg * 16) / 16;

      this.showcaseCtx.clearRect(0, 0, logW, logH);
      this.Art.drawBattleScene(this.showcaseCtx, {
        attacker: { type: sc.atkType, side: 'CHU', faction: sc.atkFaction },
        defender: { type: sc.defType, side: 'HAN', faction: sc.defFaction },
        progress: steppedProg,
        time: Math.floor(now / 90) * 90,
        width: logW,
        height: logH
      });
    }
  }

  function bootstrap() {
    const app = new MedievalJanggiController();
    app.init();
    global.MedievalJanggiApp = app;
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', bootstrap);
    } else {
      bootstrap();
    }
  }
})(typeof window !== 'undefined' ? window : globalThis);
