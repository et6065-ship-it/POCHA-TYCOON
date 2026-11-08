/**
 * @fileoverview 정통 FIDE 서양 체스 규칙 엔진 및 AI 전략 모듈 (Authentic Western Chess Rule Engine & AI)
 * @module window.ChessEngine / window.ChessAI
 *
 * 지원 기능:
 * - 8x8 체스판 좌표계 (열 x: 0~7 = a~h파일, 행 y: 0~7 = 8~1랭크)
 * - 기존 UI/스킨 시스템과 100% 호환되는 진영 상수:
 *   - CHU('CHU'): 하단(y: 6, 7) 배치, 백(White) 선공 역할
 *   - HAN('HAN'): 상단(y: 0, 1) 배치, 흑(Black) 후공 역할
 * - 6대 기물(킹, 퀸, 룩, 비숍, 나이트, 폰) 정통 행마 및 특수 규칙 완벽 지원:
 *   - 폰(PAWN) 초기 2칸 전진, 대각선 포획, 앙파상(En Passant), 승진(Promotion)
 *   - 캐슬링(Castling: 킹사이드 O-O, 퀸사이드 O-O-O) 및 경로 공격 검증·무르기(Undo) 완벽 복원
 *   - 자살수(왕이 체크에 노출되는 수) 원천 필터링
 *   - 체크(Check), 체크메이트(Checkmate), 스테일메이트(Stalemate), 기물 부족 무승부, 50수 무승부 판정
 * - window.ChessAI: Minimax + Alpha-Beta Pruning + Quiescence(포획 연장 탐색) + 8x8 PST + 중세 지휘관 전술 코멘트
 */

(function (global) {
  'use strict';

  const BOARD_COLS = 8;
  const BOARD_ROWS = 8;

  const SIDES = Object.freeze({
    CHU: 'CHU', // 백(White) 역할 - 하단(y: 6, 7), 선공
    HAN: 'HAN'  // 흑(Black) 역할 - 상단(y: 0, 1), 후공
  });

  const PIECE_TYPES = Object.freeze({
    KING: 'KING',     // 킹 (♔/♚)
    QUEEN: 'QUEEN',   // 퀸 (♕/♛) - 9점
    ROOK: 'ROOK',     // 룩 (♖/♜) - 5점
    BISHOP: 'BISHOP', // 비숍 (♗/♝) - 3점
    KNIGHT: 'KNIGHT', // 나이트 (♘/♞) - 3점
    PAWN: 'PAWN'      // 폰 (♙/♟) - 1점
  });

  const PIECE_SCORES = Object.freeze({
    KING: 0,
    QUEEN: 9,
    ROOK: 5,
    BISHOP: 3,
    KNIGHT: 3,
    PAWN: 1
  });

  const HAN_KOMI = 0; // 정통 서양 체스는 덤 없음

  /**
   * 기물별 기호, 한자 약칭 및 한글 표기 메타데이터
   */
  const PIECE_LABELS = Object.freeze({
    CHU: {
      KING: { hanja: '♔', symbol: '♔', kanji: '王', kr: '킹', name: '킹(백)' },
      QUEEN: { hanja: '♕', symbol: '♕', kanji: '后', kr: '퀸', name: '퀸' },
      ROOK: { hanja: '♖', symbol: '♖', kanji: '城', kr: '룩', name: '룩' },
      BISHOP: { hanja: '♗', symbol: '♗', kanji: '敎', kr: '비숍', name: '비숍' },
      KNIGHT: { hanja: '♘', symbol: '♘', kanji: '騎', kr: '나이트', name: '나이트' },
      PAWN: { hanja: '♙', symbol: '♙', kanji: '歩', kr: '폰', name: '폰' }
    },
    HAN: {
      KING: { hanja: '♚', symbol: '♚', kanji: '王', kr: '킹', name: '킹(흑)' },
      QUEEN: { hanja: '♛', symbol: '♛', kanji: '后', kr: '퀸', name: '퀸' },
      ROOK: { hanja: '♜', symbol: '♜', kanji: '城', kr: '룩', name: '룩' },
      BISHOP: { hanja: '♝', symbol: '♝', kanji: '敎', kr: '비숍', name: '비숍' },
      KNIGHT: { hanja: '♞', symbol: '♞', kanji: '騎', kr: '나이트', name: '나이트' },
      PAWN: { hanja: '♟', symbol: '♟', kanji: '歩', kr: '폰', name: '폰' }
    }
  });

  /**
   * 체스 진형(Formations) 정의
   * - UI의 상차림 드롭다운('STANDARD' 및 'INNER'|'OUTER'|'LEFT'|'RIGHT')과 100% 호환
   * - 모든 진형에서 킹(x=4)과 양쪽 룩(x=0, x=7)의 정통 위치를 보장하여 캐슬링 규칙이 완벽히 작동함
   */
  const STANDARD_BACK_RANK = Object.freeze([
    PIECE_TYPES.ROOK,
    PIECE_TYPES.KNIGHT,
    PIECE_TYPES.BISHOP,
    PIECE_TYPES.QUEEN,
    PIECE_TYPES.KING,
    PIECE_TYPES.BISHOP,
    PIECE_TYPES.KNIGHT,
    PIECE_TYPES.ROOK
  ]);

  const FORMATIONS = Object.freeze({
    STANDARD: {
      id: 'STANDARD',
      code: 'STANDARD_FIDE',
      name: '정통 FIDE 체스 (룩·나이트·비숍·퀸·킹)',
      shortName: '정통 배치',
      description: '국제체스연맹(FIDE) 공식 표준 오프닝 진형 (RNBQKBNR)',
      backRank: STANDARD_BACK_RANK,
      layout: { 1: PIECE_TYPES.KNIGHT, 2: PIECE_TYPES.BISHOP, 5: PIECE_TYPES.BISHOP, 6: PIECE_TYPES.KNIGHT }
    },
    INNER: {
      id: 'INNER',
      code: 'INNER_ELEPHANT',
      name: '정통 FIDE 표준 (나이트·비숍·비숍·나이트)',
      shortName: '정통 표준',
      description: '국제체스연맹(FIDE) 공식 표준 오프닝 진형 (RNBQKBNR)',
      backRank: STANDARD_BACK_RANK,
      layout: { 1: PIECE_TYPES.KNIGHT, 2: PIECE_TYPES.BISHOP, 5: PIECE_TYPES.BISHOP, 6: PIECE_TYPES.KNIGHT }
    },
    OUTER: {
      id: 'OUTER',
      code: 'OUTER_ELEPHANT',
      name: '기사단 선봉 (비숍·나이트·나이트·비숍)',
      shortName: '기사단 진형',
      description: '중앙 나이트 진출을 가속화한 중세 기사단 변형 배치 (RBNQKNBR)',
      backRank: Object.freeze([
        PIECE_TYPES.ROOK,
        PIECE_TYPES.BISHOP,
        PIECE_TYPES.KNIGHT,
        PIECE_TYPES.QUEEN,
        PIECE_TYPES.KING,
        PIECE_TYPES.KNIGHT,
        PIECE_TYPES.BISHOP,
        PIECE_TYPES.ROOK
      ]),
      layout: { 1: PIECE_TYPES.BISHOP, 2: PIECE_TYPES.KNIGHT, 5: PIECE_TYPES.KNIGHT, 6: PIECE_TYPES.BISHOP }
    },
    LEFT: {
      id: 'LEFT',
      code: 'LEFT_ELEPHANT',
      name: '퀸사이드 기동 (비숍·나이트·비숍·나이트)',
      shortName: '좌익 기동',
      description: '퀸사이드 대각선 개방과 킹사이드 정통 수비를 결합한 진형',
      backRank: Object.freeze([
        PIECE_TYPES.ROOK,
        PIECE_TYPES.BISHOP,
        PIECE_TYPES.KNIGHT,
        PIECE_TYPES.QUEEN,
        PIECE_TYPES.KING,
        PIECE_TYPES.BISHOP,
        PIECE_TYPES.KNIGHT,
        PIECE_TYPES.ROOK
      ]),
      layout: { 1: PIECE_TYPES.BISHOP, 2: PIECE_TYPES.KNIGHT, 5: PIECE_TYPES.BISHOP, 6: PIECE_TYPES.KNIGHT }
    },
    RIGHT: {
      id: 'RIGHT',
      code: 'RIGHT_ELEPHANT',
      name: '킹사이드 기동 (나이트·비숍·나이트·비숍)',
      shortName: '우익 기동',
      description: '킹사이드 공세와 퀸사이드 정통 전개를 결합한 진형',
      backRank: Object.freeze([
        PIECE_TYPES.ROOK,
        PIECE_TYPES.KNIGHT,
        PIECE_TYPES.BISHOP,
        PIECE_TYPES.QUEEN,
        PIECE_TYPES.KING,
        PIECE_TYPES.KNIGHT,
        PIECE_TYPES.BISHOP,
        PIECE_TYPES.ROOK
      ]),
      layout: { 1: PIECE_TYPES.KNIGHT, 2: PIECE_TYPES.BISHOP, 5: PIECE_TYPES.KNIGHT, 6: PIECE_TYPES.BISHOP }
    }
  });

  const FORMATION_ALIASES = Object.freeze({
    STANDARD: 'STANDARD',
    STANDARD_FIDE: 'STANDARD',
    FIDE: 'STANDARD',
    DEFAULT: 'STANDARD',
    INNER: 'INNER',
    INNER_ELEPHANT: 'INNER',
    OUTER: 'OUTER',
    OUTER_ELEPHANT: 'OUTER',
    LEFT: 'LEFT',
    LEFT_ELEPHANT: 'LEFT',
    RIGHT: 'RIGHT',
    RIGHT_ELEPHANT: 'RIGHT'
  });

  const PROMOTION_TYPES = Object.freeze([
    PIECE_TYPES.QUEEN,
    PIECE_TYPES.ROOK,
    PIECE_TYPES.BISHOP,
    PIECE_TYPES.KNIGHT
  ]);

  // 호환성 유지용 궁성 범위 상수 (체스에서는 중앙/왕실 영역 참고용으로만 제공)
  const PALACE_BOUNDS = Object.freeze({
    HAN: { minX: 3, maxX: 4, minY: 0, maxY: 1, centerX: 4, centerY: 0 },
    CHU: { minX: 3, maxX: 4, minY: 6, maxY: 7, centerX: 4, centerY: 7 }
  });
  const PALACE_DIAGONAL_NEIGHBORS = Object.freeze({});
  const PALACE_DIAGONAL_RAYS = Object.freeze({});

  const FILE_NAMES = Object.freeze(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']);

  // ============================================================================
  // 유틸리티 함수
  // ============================================================================

  function isInBounds(x, y) {
    return x >= 0 && x < BOARD_COLS && y >= 0 && y < BOARD_ROWS;
  }

  function isInPalace() {
    return false;
  }

  function getOpponentSide(side) {
    return side === SIDES.CHU ? SIDES.HAN : SIDES.CHU;
  }

  function normalizeFormation(formationKey) {
    const key = String(formationKey || 'STANDARD').toUpperCase();
    return FORMATION_ALIASES[key] || 'STANDARD';
  }

  function normalizePromotionType(promoteTo) {
    const key = String(promoteTo || PIECE_TYPES.QUEEN).toUpperCase();
    return PROMOTION_TYPES.includes(key) ? key : PIECE_TYPES.QUEEN;
  }

  function toAlgebraic(x, y) {
    const file = FILE_NAMES[x] || String(x + 1);
    const rank = BOARD_ROWS - y;
    return `${file}${rank}`;
  }

  function createPiece(id, side, type, x, y, extra = {}) {
    const labelInfo = (PIECE_LABELS[side] && PIECE_LABELS[side][type]) || PIECE_LABELS.CHU.PAWN;
    return {
      id,
      side,
      type,
      x,
      y,
      col: x,
      row: y,
      score: PIECE_SCORES[type] !== undefined ? PIECE_SCORES[type] : 0,
      hanja: labelInfo.hanja,
      symbol: labelInfo.symbol,
      kanji: labelInfo.kanji,
      kr: labelInfo.kr,
      name: labelInfo.name,
      moveCount: extra.moveCount || 0,
      promotedFrom: extra.promotedFrom || null
    };
  }

  function clonePiece(piece) {
    if (!piece) return null;
    return {
      id: piece.id,
      side: piece.side,
      type: piece.type,
      x: piece.x,
      y: piece.y,
      col: piece.x,
      row: piece.y,
      score: piece.score,
      hanja: piece.hanja,
      symbol: piece.symbol,
      kanji: piece.kanji,
      kr: piece.kr,
      name: piece.name,
      moveCount: piece.moveCount || 0,
      promotedFrom: piece.promotedFrom || null
    };
  }

  function cloneBoard(board) {
    const newBoard = new Array(BOARD_ROWS);
    for (let y = 0; y < BOARD_ROWS; y++) {
      newBoard[y] = new Array(BOARD_COLS);
      for (let x = 0; x < BOARD_COLS; x++) {
        newBoard[y][x] = board[y] && board[y][x] ? clonePiece(board[y][x]) : null;
      }
    }
    newBoard._enPassantTarget = (board && board._enPassantTarget) ? { ...board._enPassantTarget } : null;
    return newBoard;
  }

  function setBoardEnPassant(board, epTarget) {
    if (!board) return;
    board._enPassantTarget = epTarget ? { ...epTarget } : null;
  }

  function getBoardEnPassant(board, options = {}) {
    if (options && options.enPassantTarget !== undefined) {
      return options.enPassantTarget;
    }
    return (board && board._enPassantTarget) || null;
  }

  function applyPromotionToPiece(piece, promoteToType) {
    const targetType = normalizePromotionType(promoteToType);
    const labelInfo = PIECE_LABELS[piece.side][targetType];
    piece.promotedFrom = piece.promotedFrom || PIECE_TYPES.PAWN;
    piece.type = targetType;
    piece.score = PIECE_SCORES[targetType];
    piece.hanja = labelInfo.hanja;
    piece.symbol = labelInfo.symbol;
    piece.kanji = labelInfo.kanji;
    piece.kr = labelInfo.kr;
    piece.name = labelInfo.name;
    return piece;
  }

  function createMoveObject(fromX, fromY, toX, toY, piece, capturedPiece, extra = {}) {
    return {
      from: { x: fromX, y: fromY, col: fromX, row: fromY },
      to: { x: toX, y: toY, col: toX, row: toY },
      fromX,
      fromY,
      toX,
      toY,
      piece: clonePiece(piece),
      captured: capturedPiece ? clonePiece(capturedPiece) : null,
      isCapture: Boolean(capturedPiece) || Boolean(extra.isEnPassant),
      isEnPassant: Boolean(extra.isEnPassant),
      enPassantCapturedCoord: extra.enPassantCapturedCoord || null,
      isPawnDoubleStep: Boolean(extra.isPawnDoubleStep),
      enPassantTarget: extra.enPassantTarget || null,
      isPromotion: Boolean(extra.isPromotion),
      promoteTo: extra.isPromotion ? normalizePromotionType(extra.promoteTo) : null,
      isCastling: Boolean(extra.isCastling),
      castlingSide: extra.castlingSide || null,
      rookFromX: extra.rookFromX !== undefined ? extra.rookFromX : null,
      rookToX: extra.rookToX !== undefined ? extra.rookToX : null,
      rookY: extra.rookY !== undefined ? extra.rookY : null,
      bridge: extra.bridge || null,
      via: extra.via || null,
      isPalaceDiagonal: false,
      isPass: Boolean(extra.isPass)
    };
  }

  // ============================================================================
  // 초기 보드 생성 및 정통 체스 배치
  // ============================================================================

  /**
   * 8x8 체스 보드 2차원 배열 생성 (`board[y][x]`)
   * - HAN(흑, 상단): y=0 (RNBQKBNR), y=1 (PAWN x 8)
   * - CHU(백, 하단): y=6 (PAWN x 8), y=7 (RNBQKBNR)
   */
  function createInitialBoard(chuFormation = 'STANDARD', hanFormation = 'STANDARD') {
    const board = Array.from({ length: BOARD_ROWS }, () => Array(BOARD_COLS).fill(null));
    setBoardEnPassant(board, null);

    const chuBackRank = (FORMATIONS[normalizeFormation(chuFormation)] || FORMATIONS.STANDARD).backRank || STANDARD_BACK_RANK;
    const hanBackRank = (FORMATIONS[normalizeFormation(hanFormation)] || FORMATIONS.STANDARD).backRank || STANDARD_BACK_RANK;

    const place = (id, side, type, x, y) => {
      board[y][x] = createPiece(id, side, type, x, y);
    };

    // --- 한(HAN, 흑 Black, 상단 y=0, 1) 배치 ---
    for (let x = 0; x < BOARD_COLS; x++) {
      const pType = hanBackRank[x];
      const suffix = x === 3 || x === 4 ? '' : x < 4 ? '_Q' : '_K';
      const id = pType === PIECE_TYPES.KING
        ? 'HAN_KING'
        : pType === PIECE_TYPES.QUEEN
        ? 'HAN_QUEEN'
        : `HAN_${pType}${suffix}_${x}`;
      place(id, SIDES.HAN, pType, x, 0);
      place(`HAN_PAWN_${x + 1}`, SIDES.HAN, PIECE_TYPES.PAWN, x, 1);
    }

    // --- 초(CHU, 백 White, 하단 y=6, 7) 배치 ---
    for (let x = 0; x < BOARD_COLS; x++) {
      place(`CHU_PAWN_${x + 1}`, SIDES.CHU, PIECE_TYPES.PAWN, x, 6);
      const pType = chuBackRank[x];
      const suffix = x === 3 || x === 4 ? '' : x < 4 ? '_Q' : '_K';
      const id = pType === PIECE_TYPES.KING
        ? 'CHU_KING'
        : pType === PIECE_TYPES.QUEEN
        ? 'CHU_QUEEN'
        : `CHU_${pType}${suffix}_${x}`;
      place(id, SIDES.CHU, pType, x, 7);
    }

    return board;
  }

  // ============================================================================
  // 공격 판정 (isSquareAttacked) 및 의사 합법 착수 생성
  // ============================================================================

  /**
   * 특정 좌표 (targetX, targetY)가 attackerSide 진영의 기물에게 공격받고 있는지 고속 판정
   * - 캐슬링 경로 검증 및 체크 판정에 사용 (무한 재귀 없음)
   */
  function isSquareAttacked(board, targetX, targetY, attackerSide) {
    if (!isInBounds(targetX, targetY)) return false;

    // 1. 폰(PAWN) 공격 확인
    // attackerSide가 CHU(백)이면 아래(targetY + 1)에서 위(targetY)로 대각선 공격
    // attackerSide가 HAN(흑)이면 위(targetY - 1)에서 아래(targetY)로 대각선 공격
    const pawnSourceY = attackerSide === SIDES.CHU ? targetY + 1 : targetY - 1;
    if (isInBounds(targetX - 1, pawnSourceY)) {
      const p = board[pawnSourceY][targetX - 1];
      if (p && p.side === attackerSide && p.type === PIECE_TYPES.PAWN) return true;
    }
    if (isInBounds(targetX + 1, pawnSourceY)) {
      const p = board[pawnSourceY][targetX + 1];
      if (p && p.side === attackerSide && p.type === PIECE_TYPES.PAWN) return true;
    }

    // 2. 나이트(KNIGHT) 공격 확인
    const knightOffsets = [
      [-2, -1], [-2, 1], [-1, -2], [-1, 2],
      [1, -2], [1, 2], [2, -1], [2, 1]
    ];
    for (let i = 0; i < knightOffsets.length; i++) {
      const nx = targetX + knightOffsets[i][0];
      const ny = targetY + knightOffsets[i][1];
      if (isInBounds(nx, ny)) {
        const p = board[ny][nx];
        if (p && p.side === attackerSide && p.type === PIECE_TYPES.KNIGHT) return true;
      }
    }

    // 3. 킹(KING) 인접 8방향 공격 확인
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (dx === 0 && dy === 0) continue;
        const kx = targetX + dx;
        const ky = targetY + dy;
        if (isInBounds(kx, ky)) {
          const p = board[ky][kx];
          if (p && p.side === attackerSide && p.type === PIECE_TYPES.KING) return true;
        }
      }
    }

    // 4. 직선 슬라이딩 기물 (ROOK, QUEEN) 확인
    const orthoDirs = [
      [0, -1], [0, 1], [-1, 0], [1, 0]
    ];
    for (let i = 0; i < orthoDirs.length; i++) {
      const [dx, dy] = orthoDirs[i];
      let step = 1;
      while (true) {
        const tx = targetX + dx * step;
        const ty = targetY + dy * step;
        if (!isInBounds(tx, ty)) break;
        const p = board[ty][tx];
        if (p) {
          if (
            p.side === attackerSide &&
            (p.type === PIECE_TYPES.ROOK || p.type === PIECE_TYPES.QUEEN)
          ) {
            return true;
          }
          break;
        }
        step++;
      }
    }

    // 5. 대각선 슬라이딩 기물 (BISHOP, QUEEN) 확인
    const diagDirs = [
      [-1, -1], [1, -1], [-1, 1], [1, 1]
    ];
    for (let i = 0; i < diagDirs.length; i++) {
      const [dx, dy] = diagDirs[i];
      let step = 1;
      while (true) {
        const tx = targetX + dx * step;
        const ty = targetY + dy * step;
        if (!isInBounds(tx, ty)) break;
        const p = board[ty][tx];
        if (p) {
          if (
            p.side === attackerSide &&
            (p.type === PIECE_TYPES.BISHOP || p.type === PIECE_TYPES.QUEEN)
          ) {
            return true;
          }
          break;
        }
        step++;
      }
    }

    return false;
  }

  /**
   * 특정 기물의 의사 합법 이동(자살수 필터링 전) 및 UI 힌트용 점프/막힘 메타데이터 반환
   * @param {Array<Array<Object|null>>} board
   * @param {number} x
   * @param {number} y
   * @param {Object} [options]
   * @returns {{ moves: Array<Object>, blockedNecks: Array<Object>, bridges: Array<Object> }}
   */
  function getPseudoMovesWithMeta(board, x, y, options = {}) {
    const piece = isInBounds(x, y) ? board[y][x] : null;
    if (!piece) {
      return { moves: [], blockedNecks: [], bridges: [] };
    }

    const moves = [];
    const blockedNecks = [];
    const bridges = [];
    const bridgeSet = new Set();
    const side = piece.side;
    const opponentSide = getOpponentSide(side);
    const includeCastling = options.includeCastling !== false;
    const epTarget = getBoardEnPassant(board, options);

    const addBridgeHint = (bx, by, jumpedPiece) => {
      const key = `${bx},${by}`;
      if (!bridgeSet.has(key)) {
        bridgeSet.add(key);
        bridges.push({
          x: bx,
          y: by,
          col: bx,
          row: by,
          pieceId: jumpedPiece ? jumpedPiece.id : null
        });
      }
    };

    const slideDirections = (dirs) => {
      for (let i = 0; i < dirs.length; i++) {
        const { dx, dy } = dirs[i];
        let step = 1;
        while (true) {
          const tx = x + dx * step;
          const ty = y + dy * step;
          if (!isInBounds(tx, ty)) break;
          const occupant = board[ty][tx];
          if (!occupant) {
            moves.push(createMoveObject(x, y, tx, ty, piece, null));
          } else {
            if (occupant.side !== side) {
              moves.push(createMoveObject(x, y, tx, ty, piece, occupant));
            }
            // 아군 또는 적군 기물을 만나면 해당 방향 슬라이딩 중단
            break;
          }
          step++;
        }
      }
    };

    switch (piece.type) {
      case PIECE_TYPES.PAWN: {
        const forwardDy = side === SIDES.CHU ? -1 : 1;
        const startRankY = side === SIDES.CHU ? 6 : 1;
        const promotionRankY = side === SIDES.CHU ? 0 : 7;

        // 1. 전방 1칸 전진 (빈칸일 때만)
        const oneY = y + forwardDy;
        if (isInBounds(x, oneY) && !board[oneY][x]) {
          const isPromo = oneY === promotionRankY;
          moves.push(
            createMoveObject(x, y, x, oneY, piece, null, {
              isPromotion: isPromo,
              promoteTo: isPromo ? PIECE_TYPES.QUEEN : null
            })
          );

          // 2. 초기 위치에서 전방 2칸 전진 (앞 2칸 모두 빈칸일 때)
          const twoY = y + forwardDy * 2;
          if (y === startRankY && isInBounds(x, twoY) && !board[twoY][x]) {
            moves.push(
              createMoveObject(x, y, x, twoY, piece, null, {
                isPawnDoubleStep: true,
                enPassantTarget: {
                  x,
                  y: oneY,
                  pawnX: x,
                  pawnY: twoY,
                  pawnSide: side
                }
              })
            );
          }
        }

        // 3. 대각선 전방 1칸 적 기물 일반 포획 및 앙파상(En Passant) 포획
        const captureDxList = [-1, 1];
        for (let i = 0; i < captureDxList.length; i++) {
          const tx = x + captureDxList[i];
          const ty = y + forwardDy;
          if (!isInBounds(tx, ty)) continue;

          const occupant = board[ty][tx];
          if (occupant && occupant.side !== side) {
            const isPromo = ty === promotionRankY;
            moves.push(
              createMoveObject(x, y, tx, ty, piece, occupant, {
                isPromotion: isPromo,
                promoteTo: isPromo ? PIECE_TYPES.QUEEN : null
              })
            );
          } else if (
            !occupant &&
            epTarget &&
            epTarget.x === tx &&
            epTarget.y === ty &&
            epTarget.pawnSide === opponentSide
          ) {
            // 앙파상: 직전 턴에 2칸 전진하여 내 폰 옆(epTarget.pawnX, epTarget.pawnY)에 놓인 적 폰 포획
            const epPawn = isInBounds(epTarget.pawnX, epTarget.pawnY)
              ? board[epTarget.pawnY][epTarget.pawnX]
              : null;
            if (epPawn && epPawn.side === opponentSide && epPawn.type === PIECE_TYPES.PAWN) {
              moves.push(
                createMoveObject(x, y, tx, ty, piece, epPawn, {
                  isEnPassant: true,
                  enPassantCapturedCoord: { x: epTarget.pawnX, y: epTarget.pawnY }
                })
              );
            }
          }
        }
        break;
      }

      case PIECE_TYPES.KNIGHT: {
        // 8방향 L자 도약 (주변 기물을 뛰어넘을 때 bridges에 표시하여 점프 힌트 제공)
        const knightMoves = [
          { dx: -1, dy: -2, stepX: 0, stepY: -1 },
          { dx: 1, dy: -2, stepX: 0, stepY: -1 },
          { dx: -1, dy: 2, stepX: 0, stepY: 1 },
          { dx: 1, dy: 2, stepX: 0, stepY: 1 },
          { dx: -2, dy: -1, stepX: -1, stepY: 0 },
          { dx: -2, dy: 1, stepX: -1, stepY: 0 },
          { dx: 2, dy: -1, stepX: 1, stepY: 0 },
          { dx: 2, dy: 1, stepX: 1, stepY: 0 }
        ];

        for (let i = 0; i < knightMoves.length; i++) {
          const km = knightMoves[i];
          const tx = x + km.dx;
          const ty = y + km.dy;
          if (!isInBounds(tx, ty)) continue;

          const occupant = board[ty][tx];
          if (occupant && occupant.side === side) continue;

          const midX = x + km.stepX;
          const midY = y + km.stepY;
          const midPiece = isInBounds(midX, midY) ? board[midY][midX] : null;
          let bridgeRef = null;

          if (midPiece) {
            addBridgeHint(midX, midY, midPiece);
            bridgeRef = { x: midX, y: midY, col: midX, row: midY, pieceId: midPiece.id };
          }

          moves.push(
            createMoveObject(x, y, tx, ty, piece, occupant || null, {
              bridge: bridgeRef,
              via: [{ x: midX, y: midY }]
            })
          );
        }
        break;
      }

      case PIECE_TYPES.BISHOP: {
        slideDirections([
          { dx: -1, dy: -1 },
          { dx: 1, dy: -1 },
          { dx: -1, dy: 1 },
          { dx: 1, dy: 1 }
        ]);
        break;
      }

      case PIECE_TYPES.ROOK: {
        slideDirections([
          { dx: 0, dy: -1 },
          { dx: 0, dy: 1 },
          { dx: -1, dy: 0 },
          { dx: 1, dy: 0 }
        ]);
        break;
      }

      case PIECE_TYPES.QUEEN: {
        slideDirections([
          { dx: 0, dy: -1 },
          { dx: 0, dy: 1 },
          { dx: -1, dy: 0 },
          { dx: 1, dy: 0 },
          { dx: -1, dy: -1 },
          { dx: 1, dy: -1 },
          { dx: -1, dy: 1 },
          { dx: 1, dy: 1 }
        ]);
        break;
      }

      case PIECE_TYPES.KING: {
        // 1. 8방향 1칸 이동
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            const tx = x + dx;
            const ty = y + dy;
            if (!isInBounds(tx, ty)) continue;
            const occupant = board[ty][tx];
            if (!occupant) {
              moves.push(createMoveObject(x, y, tx, ty, piece, null));
            } else if (occupant.side !== side) {
              moves.push(createMoveObject(x, y, tx, ty, piece, occupant));
            }
          }
        }

        // 2. 캐슬링 (Castling: Kingside O-O / Queenside O-O-O)
        const homeY = side === SIDES.CHU ? 7 : 0;
        if (includeCastling && (piece.moveCount || 0) === 0 && x === 4 && y === homeY) {
          const currentlyInCheck = isSquareAttacked(board, 4, homeY, opponentSide);
          if (!currentlyInCheck) {
            // (a) 킹사이드 캐슬링 (O-O: e1->g1 / e8->g8, 룩 h->f)
            const ksRook = board[homeY][7];
            if (
              ksRook &&
              ksRook.side === side &&
              ksRook.type === PIECE_TYPES.ROOK &&
              (ksRook.moveCount || 0) === 0 &&
              board[homeY][5] === null &&
              board[homeY][6] === null &&
              !isSquareAttacked(board, 5, homeY, opponentSide) &&
              !isSquareAttacked(board, 6, homeY, opponentSide)
            ) {
              moves.push(
                createMoveObject(4, homeY, 6, homeY, piece, null, {
                  isCastling: true,
                  castlingSide: 'KINGSIDE',
                  rookFromX: 7,
                  rookToX: 5,
                  rookY: homeY,
                  via: [{ x: 5, y: homeY }]
                })
              );
            }

            // (b) 퀸사이드 캐슬링 (O-O-O: e1->c1 / e8->c8, 룩 a->d)
            const qsRook = board[homeY][0];
            if (
              qsRook &&
              qsRook.side === side &&
              qsRook.type === PIECE_TYPES.ROOK &&
              (qsRook.moveCount || 0) === 0 &&
              board[homeY][1] === null &&
              board[homeY][2] === null &&
              board[homeY][3] === null &&
              !isSquareAttacked(board, 3, homeY, opponentSide) &&
              !isSquareAttacked(board, 2, homeY, opponentSide)
            ) {
              moves.push(
                createMoveObject(4, homeY, 2, homeY, piece, null, {
                  isCastling: true,
                  castlingSide: 'QUEENSIDE',
                  rookFromX: 0,
                  rookToX: 3,
                  rookY: homeY,
                  via: [{ x: 3, y: homeY }]
                })
              );
            }
          }
        }
        break;
      }

      default:
        break;
    }

    return { moves, blockedNecks, bridges };
  }

  function getPseudoMoves(board, x, y, options = {}) {
    return getPseudoMovesWithMeta(board, x, y, options).moves;
  }

  // ============================================================================
  // 체크(Check), 자살수 방지, 보드 시뮬레이션 및 합법 착수 생성
  // ============================================================================

  function findKing(board, side) {
    for (let y = 0; y < BOARD_ROWS; y++) {
      for (let x = 0; x < BOARD_COLS; x++) {
        const p = board[y][x];
        if (p && p.side === side && p.type === PIECE_TYPES.KING) {
          return { x, y, col: x, row: y, piece: p };
        }
      }
    }
    return null;
  }

  /**
   * 장기 인터페이스 호환용 빅장 상태 함수 (체스에서는 항상 비활성)
   */
  function getBikjangState(board) {
    const chuKing = findKing(board, SIDES.CHU);
    const hanKing = findKing(board, SIDES.HAN);
    return { active: false, chuKing, hanKing };
  }

  function isBikjang() {
    return false;
  }

  /**
   * 특정 진영(side)의 왕이 체크 상태인지 확인하고 위협하는 적 기물 목록 반환
   */
  function getCheckStatus(board, side) {
    const kingInfo = findKing(board, side);
    if (!kingInfo) {
      return { inCheck: true, attackers: [], king: null };
    }

    const opponent = getOpponentSide(side);
    const attackers = [];

    for (let y = 0; y < BOARD_ROWS; y++) {
      for (let x = 0; x < BOARD_COLS; x++) {
        const p = board[y][x];
        if (!p || p.side !== opponent) continue;

        const pseudoMoves = getPseudoMoves(board, x, y, { includeCastling: false });
        for (let i = 0; i < pseudoMoves.length; i++) {
          const mv = pseudoMoves[i];
          if (mv.toX === kingInfo.x && mv.toY === kingInfo.y) {
            attackers.push({
              attacker: clonePiece(p),
              from: { x, y, col: x, row: y },
              to: { x: kingInfo.x, y: kingInfo.y, col: kingInfo.x, row: kingInfo.y },
              bridge: mv.bridge || null
            });
          }
        }
      }
    }

    return {
      inCheck: attackers.length > 0,
      attackers,
      king: kingInfo
    };
  }

  function isKingInCheck(board, side) {
    const kingInfo = findKing(board, side);
    if (!kingInfo) return true;
    return isSquareAttacked(board, kingInfo.x, kingInfo.y, getOpponentSide(side));
  }

  /**
   * 가상 보드에 착수(일반 이동, 앙파상, 캐슬링, 프로모션)를 적용한 새 보드를 반환 (원본 불변)
   */
  function simulateMoveOnBoard(board, move, promoteToOverride) {
    const nextBoard = cloneBoard(board);
    if (!move || move.isPass) {
      setBoardEnPassant(nextBoard, null);
      return nextBoard;
    }

    const movingPiece = nextBoard[move.fromY] ? nextBoard[move.fromY][move.fromX] : null;
    if (!movingPiece) return nextBoard;

    // 1. 앙파상 포획 시 지나간 자리에 있던 적 폰 제거
    if (move.isEnPassant && move.enPassantCapturedCoord) {
      const { x: capX, y: capY } = move.enPassantCapturedCoord;
      if (isInBounds(capX, capY)) {
        nextBoard[capY][capX] = null;
      }
    }

    // 2. 기물 이동
    nextBoard[move.fromY][move.fromX] = null;
    movingPiece.x = move.toX;
    movingPiece.y = move.toY;
    movingPiece.col = move.toX;
    movingPiece.row = move.toY;
    movingPiece.moveCount = (movingPiece.moveCount || 0) + 1;

    // 3. 프로모션(승진) 적용
    if (move.isPromotion) {
      const targetType = normalizePromotionType(promoteToOverride || move.promoteTo || PIECE_TYPES.QUEEN);
      applyPromotionToPiece(movingPiece, targetType);
    }

    nextBoard[move.toY][move.toX] = movingPiece;

    // 4. 캐슬링 시 해당 룩도 함께 이동
    if (move.isCastling && move.rookFromX !== null && move.rookToX !== null) {
      const rY = move.rookY !== null ? move.rookY : move.fromY;
      const rook = nextBoard[rY][move.rookFromX];
      if (rook) {
        nextBoard[rY][move.rookFromX] = null;
        rook.x = move.rookToX;
        rook.y = rY;
        rook.col = move.rookToX;
        rook.row = rY;
        rook.moveCount = (rook.moveCount || 0) + 1;
        nextBoard[rY][move.rookToX] = rook;
      }
    }

    // 5. 다음 턴을 위한 앙파상 타겟 갱신
    if (move.isPawnDoubleStep && move.enPassantTarget) {
      setBoardEnPassant(nextBoard, move.enPassantTarget);
    } else {
      setBoardEnPassant(nextBoard, null);
    }

    return nextBoard;
  }

  /**
   * 특정 좌표 기물의 합법 착수(자살수 필터링 완료) 및 메타데이터 반환
   */
  function getLegalMovesForPieceWithMeta(board, x, y, options = {}) {
    const piece = isInBounds(x, y) ? board[y][x] : null;
    if (!piece) {
      return { moves: [], blockedNecks: [], bridges: [], suicidedMoves: [] };
    }

    const { moves: pseudoMoves, blockedNecks, bridges } = getPseudoMovesWithMeta(board, x, y, options);
    const legalMoves = [];
    const suicidedMoves = [];
    const oppSide = getOpponentSide(piece.side);

    for (let i = 0; i < pseudoMoves.length; i++) {
      const mv = pseudoMoves[i];
      const nextBoard = simulateMoveOnBoard(board, mv);

      // 자살수(내 킹이 체크에 노출되는 수) 원천 차단
      if (isKingInCheck(nextBoard, piece.side)) {
        suicidedMoves.push(mv);
        continue;
      }

      mv.causesCheck = isKingInCheck(nextBoard, oppSide);
      mv.causesBikjang = false;
      legalMoves.push(mv);
    }

    return {
      moves: legalMoves,
      blockedNecks,
      bridges,
      suicidedMoves
    };
  }

  function getLegalMovesForPiece(board, x, y, options = {}) {
    return getLegalMovesForPieceWithMeta(board, x, y, options).moves;
  }

  /**
   * 특정 진영(side)의 모든 합법 착수 목록 반환
   */
  function getAllLegalMoves(board, side, options = {}) {
    const allMoves = [];
    for (let y = 0; y < BOARD_ROWS; y++) {
      for (let x = 0; x < BOARD_COLS; x++) {
        const p = board[y][x];
        if (p && p.side === side) {
          const moves = getLegalMovesForPiece(board, x, y, options);
          for (let i = 0; i < moves.length; i++) {
            allMoves.push(moves[i]);
          }
        }
      }
    }
    return allMoves;
  }

  /**
   * 기물 부족 무승부(Insufficient Material) 판정:
   * - K vs K
   * - K+B vs K
   * - K+N vs K
   * - K+B vs K+B (같은 색 칸 비숍)
   */
  function isInsufficientMaterial(board) {
    const minors = [];
    for (let y = 0; y < BOARD_ROWS; y++) {
      for (let x = 0; x < BOARD_COLS; x++) {
        const p = board[y][x];
        if (!p || p.type === PIECE_TYPES.KING) continue;
        if (
          p.type === PIECE_TYPES.PAWN ||
          p.type === PIECE_TYPES.ROOK ||
          p.type === PIECE_TYPES.QUEEN
        ) {
          return false;
        }
        minors.push({ piece: p, x, y, colorSquare: (x + y) % 2 });
      }
    }

    // K vs K
    if (minors.length === 0) return true;
    // K+B vs K 또는 K+N vs K
    if (minors.length === 1) return true;
    // K+B vs K+B (양쪽 비숍이 1개씩이고 같은 색 칸에 있는 경우)
    if (
      minors.length === 2 &&
      minors[0].piece.side !== minors[1].piece.side &&
      minors[0].piece.type === PIECE_TYPES.BISHOP &&
      minors[1].piece.type === PIECE_TYPES.BISHOP &&
      minors[0].colorSquare === minors[1].colorSquare
    ) {
      return true;
    }

    return false;
  }

  // ============================================================================
  // 기물 점수 계산 (퀸9, 룩5, 비숍3, 나이트3, 폰1)
  // ============================================================================

  function calculateScores(board) {
    let chuRaw = 0;
    let hanRaw = 0;
    const counts = {
      CHU: { KING: 0, QUEEN: 0, ROOK: 0, BISHOP: 0, KNIGHT: 0, PAWN: 0 },
      HAN: { KING: 0, QUEEN: 0, ROOK: 0, BISHOP: 0, KNIGHT: 0, PAWN: 0 }
    };

    for (let y = 0; y < BOARD_ROWS; y++) {
      for (let x = 0; x < BOARD_COLS; x++) {
        const p = board[y][x];
        if (!p) continue;
        const pts = PIECE_SCORES[p.type] || 0;
        counts[p.side][p.type] = (counts[p.side][p.type] || 0) + 1;
        if (p.side === SIDES.CHU) {
          chuRaw += pts;
        } else {
          hanRaw += pts;
        }
      }
    }

    const chuTotal = chuRaw;
    const hanTotal = hanRaw + HAN_KOMI;

    return {
      CHU: chuTotal,
      HAN: hanTotal,
      chuRaw,
      hanRaw,
      komi: HAN_KOMI,
      diff: chuTotal - hanTotal,
      leader: chuTotal > hanTotal ? SIDES.CHU : hanTotal > chuTotal ? SIDES.HAN : 'DRAW',
      counts
    };
  }

  // ============================================================================
  // 대국 상태 관리 클래스 (ChessGame)
  // ============================================================================

  class ChessGame {
    /**
     * @param {Object} config
     * @param {string} [config.chuFormation='STANDARD']
     * @param {string} [config.hanFormation='STANDARD']
     * @param {string} [config.chuSkin='GORYEO']
     * @param {string} [config.hanSkin='TEMPLAR']
     */
    constructor(config = {}) {
      this.reset(config);
    }

    reset(config = {}) {
      this.chuFormation = normalizeFormation(config.chuFormation || this.chuFormation || 'STANDARD');
      this.hanFormation = normalizeFormation(config.hanFormation || this.hanFormation || 'STANDARD');
      this.chuSkin = config.chuSkin || this.chuSkin || 'GORYEO';
      this.hanSkin = config.hanSkin || this.hanSkin || 'TEMPLAR';

      this.board = createInitialBoard(this.chuFormation, this.hanFormation);
      this.enPassantTarget = null;
      setBoardEnPassant(this.board, null);

      this.currentTurn = SIDES.CHU; // 백(CHU) 선공
      this.turnCount = 1;
      this.halfMoveClock = 0; // 50수 무승부 규칙용 반수(Ply) 카운터
      this.history = [];
      this.capturedPieces = {
        CHU: [],
        HAN: []
      };
      this.lostPieces = {
        CHU: [],
        HAN: []
      };

      this.inCheck = false;
      this.lastEvent = null;
      this.checkAttackers = [];
      this.bikjangState = { active: false };
      this.consecutivePasses = 0;

      this.isGameOver = false;
      this.winner = null; // 'CHU' | 'HAN' | 'DRAW'
      this.winReason = null; // 'CHECKMATE' | 'STALEMATE' | 'INSUFFICIENT_MATERIAL' | 'FIFTY_MOVE_RULE' | 'SCORE_DECISION' | 'RESIGN'
      this.scores = calculateScores(this.board);

      return this.getState();
    }

    getPieceAt(x, y) {
      if (!isInBounds(x, y)) return null;
      return this.board[y][x];
    }

    getLegalMovesAt(x, y) {
      if (this.isGameOver) {
        return { moves: [], blockedNecks: [], bridges: [], suicidedMoves: [] };
      }
      const piece = this.getPieceAt(x, y);
      if (!piece || piece.side !== this.currentTurn) {
        return { moves: [], blockedNecks: [], bridges: [], suicidedMoves: [] };
      }
      return getLegalMovesForPieceWithMeta(this.board, x, y, {
        enPassantTarget: this.enPassantTarget
      });
    }

    getAllLegalMovesForCurrentTurn() {
      if (this.isGameOver) return [];
      return getAllLegalMoves(this.board, this.currentTurn, {
        enPassantTarget: this.enPassantTarget
      });
    }

    _createSnapshot(moveRecord) {
      return {
        board: cloneBoard(this.board),
        enPassantTarget: this.enPassantTarget ? { ...this.enPassantTarget } : null,
        currentTurn: this.currentTurn,
        turnCount: this.turnCount,
        halfMoveClock: this.halfMoveClock,
        capturedPieces: {
          CHU: this.capturedPieces.CHU.map(clonePiece),
          HAN: this.capturedPieces.HAN.map(clonePiece)
        },
        lostPieces: {
          CHU: this.lostPieces.CHU.map(clonePiece),
          HAN: this.lostPieces.HAN.map(clonePiece)
        },
        inCheck: this.inCheck,
        lastEvent: this.lastEvent,
        checkAttackers: JSON.parse(JSON.stringify(this.checkAttackers)),
        bikjangState: JSON.parse(JSON.stringify(this.bikjangState)),
        consecutivePasses: this.consecutivePasses,
        isGameOver: this.isGameOver,
        winner: this.winner,
        winReason: this.winReason,
        scores: JSON.parse(JSON.stringify(this.scores)),
        move: moveRecord
      };
    }

    /**
     * 착수 실행 (fromX, fromY) -> (toX, toY)
     * @param {number} fromX
     * @param {number} fromY
     * @param {number} toX
     * @param {number} toY
     * @param {string} [promoteTo='QUEEN'] - 프로모션 대상 기물 ('QUEEN'|'ROOK'|'BISHOP'|'KNIGHT')
     */
    makeMove(fromX, fromY, toX, toY, promoteTo) {
      if (this.isGameOver) {
        return { ok: false, error: '이미 종료된 대국입니다.' };
      }

      const piece = this.getPieceAt(fromX, fromY);
      if (!piece) {
        return { ok: false, error: '선택한 위치에 기물이 없습니다.' };
      }
      if (piece.side !== this.currentTurn) {
        return { ok: false, error: '현재 차례의 기물이 아닙니다.' };
      }

      const { moves: legalMoves } = getLegalMovesForPieceWithMeta(this.board, fromX, fromY, {
        enPassantTarget: this.enPassantTarget
      });
      const matchedMove = legalMoves.find((m) => m.toX === toX && m.toY === toY);

      if (!matchedMove) {
        return { ok: false, error: '규칙에 어긋나는 착수이거나 왕이 위험해지는 자살수입니다.' };
      }

      const wasInCheck = this.inCheck;
      const moverSide = this.currentTurn;
      const nextSide = getOpponentSide(moverSide);
      const wasPawnMove = piece.type === PIECE_TYPES.PAWN;

      // 프로모션 기물 확정
      if (matchedMove.isPromotion) {
        matchedMove.promoteTo = normalizePromotionType(promoteTo || matchedMove.promoteTo || PIECE_TYPES.QUEEN);
      }

      // 히스토리 스냅샷 저장 (무르기 시 킹/룩/앙파상/프로모션 완벽 복원)
      this.history.push(this._createSnapshot(matchedMove));

      // 1. 포획 처리 (일반 포획 및 앙파상 포획)
      let capturedPieceObj = null;
      if (matchedMove.isEnPassant && matchedMove.enPassantCapturedCoord) {
        const { x: epX, y: epY } = matchedMove.enPassantCapturedCoord;
        capturedPieceObj = this.board[epY][epX];
        this.board[epY][epX] = null;
      } else if (this.board[toY][toX]) {
        capturedPieceObj = this.board[toY][toX];
      }

      if (capturedPieceObj) {
        const clonedCap = clonePiece(capturedPieceObj);
        matchedMove.captured = clonedCap;
        matchedMove.isCapture = true;
        this.capturedPieces[moverSide].push(clonedCap);
        this.lostPieces[clonedCap.side].push(clonedCap);
      }

      // 2. 기물 이동
      this.board[fromY][fromX] = null;
      piece.x = toX;
      piece.y = toY;
      piece.col = toX;
      piece.row = toY;
      piece.moveCount = (piece.moveCount || 0) + 1;

      // 3. 프로모션(Promotion) 승진 처리
      if (matchedMove.isPromotion) {
        applyPromotionToPiece(piece, matchedMove.promoteTo);
        matchedMove.promotedPiece = clonePiece(piece);
      }

      this.board[toY][toX] = piece;

      // 4. 캐슬링(Castling) 시 룩 동시 이동
      if (matchedMove.isCastling && matchedMove.rookFromX !== null && matchedMove.rookToX !== null) {
        const rY = matchedMove.rookY !== null ? matchedMove.rookY : fromY;
        const rook = this.board[rY][matchedMove.rookFromX];
        if (rook) {
          this.board[rY][matchedMove.rookFromX] = null;
          rook.x = matchedMove.rookToX;
          rook.y = rY;
          rook.col = matchedMove.rookToX;
          rook.row = rY;
          rook.moveCount = (rook.moveCount || 0) + 1;
          this.board[rY][matchedMove.rookToX] = rook;
        }
      }

      // 5. 앙파상 타겟 상태 갱신
      if (matchedMove.isPawnDoubleStep && matchedMove.enPassantTarget) {
        this.enPassantTarget = { ...matchedMove.enPassantTarget };
      } else {
        this.enPassantTarget = null;
      }
      setBoardEnPassant(this.board, this.enPassantTarget);

      // 6. 50수 규칙 카운터 및 턴 갱신
      if (wasPawnMove || matchedMove.isCapture) {
        this.halfMoveClock = 0;
      } else {
        this.halfMoveClock++;
      }

      this.consecutivePasses = 0;
      this.currentTurn = nextSide;
      this.turnCount++;

      // 7. 점수 및 체크 상태 계산
      this.scores = calculateScores(this.board);
      const checkInfo = getCheckStatus(this.board, nextSide);
      this.inCheck = checkInfo.inCheck;
      this.checkAttackers = checkInfo.attackers;
      this.bikjangState = { active: false };

      const isMeonggun = wasInCheck && !isKingInCheck(this.board, moverSide);

      // 8. 다음 턴 플레이어의 합법 착수 및 종국 판정
      const nextLegalMoves = getAllLegalMoves(this.board, nextSide, {
        enPassantTarget: this.enPassantTarget
      });

      let eventType = 'MOVE';
      if (matchedMove.isPromotion) {
        eventType = 'PROMOTION';
      } else if (matchedMove.isCastling) {
        eventType = 'CASTLING';
      } else if (matchedMove.isCapture) {
        eventType = 'CAPTURE';
      }

      if (nextLegalMoves.length === 0) {
        this.isGameOver = true;
        if (this.inCheck) {
          this.winner = moverSide;
          this.winReason = 'CHECKMATE';
          this.lastEvent = 'CHECKMATE';
          eventType = 'CHECKMATE';
        } else {
          // 정통 FIDE 체스 규칙: 스테일메이트는 무승부(DRAW)
          this.winner = 'DRAW';
          this.winReason = 'STALEMATE';
          this.lastEvent = 'STALEMATE';
          eventType = 'STALEMATE';
        }
      } else if (isInsufficientMaterial(this.board)) {
        this.isGameOver = true;
        this.winner = 'DRAW';
        this.winReason = 'INSUFFICIENT_MATERIAL';
        this.lastEvent = 'INSUFFICIENT_MATERIAL';
        eventType = 'INSUFFICIENT_MATERIAL';
      } else if (this.halfMoveClock >= 100) {
        this.isGameOver = true;
        this.winner = 'DRAW';
        this.winReason = 'FIFTY_MOVE_RULE';
        this.lastEvent = 'FIFTY_MOVE_RULE';
        eventType = 'FIFTY_MOVE_RULE';
      } else if (this.inCheck) {
        this.lastEvent = 'CHECK';
        eventType = 'CHECK';
      } else if (isMeonggun) {
        this.lastEvent = 'MEONGGUN';
        eventType = 'MEONGGUN';
      } else {
        this.lastEvent = eventType;
      }

      matchedMove.notation = this.formatMoveNotation(matchedMove, eventType);

      return {
        ok: true,
        move: matchedMove,
        event: eventType,
        inCheck: this.inCheck,
        checkAttackers: this.checkAttackers,
        isMeonggun,
        isBikjang: false,
        bikjangState: this.bikjangState,
        isGameOver: this.isGameOver,
        winner: this.winner,
        winReason: this.winReason,
        scores: this.scores,
        currentTurn: this.currentTurn,
        turnCount: this.turnCount
      };
    }

    /**
     * 한수 쉼 / 턴 넘김 (UI 호환용)
     */
    passTurn() {
      if (this.isGameOver) {
        return { ok: false, error: '이미 종료된 대국입니다.' };
      }
      if (this.inCheck) {
        return { ok: false, error: '체크(Check) 상태에서는 턴을 넘길 수 없습니다! 킹을 보호하세요.' };
      }

      const moverSide = this.currentTurn;
      const nextSide = getOpponentSide(moverSide);
      const kingPos = findKing(this.board, moverSide);

      const passMove = createMoveObject(
        kingPos ? kingPos.x : 4,
        kingPos ? kingPos.y : (moverSide === SIDES.CHU ? 7 : 0),
        kingPos ? kingPos.x : 4,
        kingPos ? kingPos.y : (moverSide === SIDES.CHU ? 7 : 0),
        kingPos ? kingPos.piece : createPiece('PASS', moverSide, PIECE_TYPES.KING, 4, 4),
        null,
        { isPass: true }
      );
      passMove.notation = `${moverSide === SIDES.CHU ? '백(CHU)' : '흑(HAN)'}: 대기 (Pass)`;

      this.history.push(this._createSnapshot(passMove));

      this.enPassantTarget = null;
      setBoardEnPassant(this.board, null);
      this.consecutivePasses++;
      this.currentTurn = nextSide;
      this.turnCount++;
      this.lastEvent = 'PASS';

      if (this.consecutivePasses >= 2) {
        this.isGameOver = true;
        this.scores = calculateScores(this.board);
        this.winner = this.scores.leader;
        this.winReason = 'SCORE_DECISION';
        this.lastEvent = 'SCORE_DECISION';
      }

      return {
        ok: true,
        move: passMove,
        event: this.lastEvent,
        inCheck: this.inCheck,
        isBikjang: false,
        isGameOver: this.isGameOver,
        winner: this.winner,
        winReason: this.winReason,
        scores: this.scores,
        currentTurn: this.currentTurn,
        turnCount: this.turnCount
      };
    }

    resolveBikjang() {
      return { ok: false, error: '서양 체스에서는 빅장 규칙을 사용하지 않습니다.' };
    }

    finishByScoreDecision() {
      this.isGameOver = true;
      this.scores = calculateScores(this.board);
      this.winner = this.scores.leader;
      this.winReason = 'SCORE_DECISION';
      this.lastEvent = 'SCORE_DECISION';
      return {
        ok: true,
        isGameOver: true,
        winner: this.winner,
        winReason: this.winReason,
        scores: this.scores
      };
    }

    resign(side = this.currentTurn) {
      if (this.isGameOver) {
        return { ok: false, error: '이미 종료된 대국입니다.' };
      }
      this.isGameOver = true;
      this.winner = getOpponentSide(side);
      this.winReason = 'RESIGN';
      this.lastEvent = 'RESIGN';
      return {
        ok: true,
        isGameOver: true,
        winner: this.winner,
        winReason: this.winReason,
        scores: this.scores
      };
    }

    /**
     * 무르기 (Undo Move)
     * - 캐슬링 시 이동한 킹과 룩, 앙파상 타겟, 프로모션 전 폰 상태를 100% 복원
     */
    undo(steps = 1) {
      if (this.history.length === 0) {
        return { ok: false, error: '되돌릴 이전 수가 없습니다.' };
      }

      const count = Math.min(steps, this.history.length);
      let snapshot = null;
      for (let i = 0; i < count; i++) {
        snapshot = this.history.pop();
      }

      if (snapshot) {
        this.board = cloneBoard(snapshot.board);
        this.enPassantTarget = snapshot.enPassantTarget ? { ...snapshot.enPassantTarget } : null;
        setBoardEnPassant(this.board, this.enPassantTarget);
        this.currentTurn = snapshot.currentTurn;
        this.turnCount = snapshot.turnCount;
        this.halfMoveClock = snapshot.halfMoveClock || 0;
        this.capturedPieces = {
          CHU: snapshot.capturedPieces.CHU.map(clonePiece),
          HAN: snapshot.capturedPieces.HAN.map(clonePiece)
        };
        this.lostPieces = {
          CHU: snapshot.lostPieces.CHU.map(clonePiece),
          HAN: snapshot.lostPieces.HAN.map(clonePiece)
        };
        this.inCheck = snapshot.inCheck;
        this.lastEvent = snapshot.lastEvent;
        this.checkAttackers = snapshot.checkAttackers;
        this.bikjangState = snapshot.bikjangState;
        this.consecutivePasses = snapshot.consecutivePasses;
        this.isGameOver = snapshot.isGameOver;
        this.winner = snapshot.winner;
        this.winReason = snapshot.winReason;
        this.scores = snapshot.scores;
      }

      return {
        ok: true,
        state: this.getState()
      };
    }

    /**
     * 체스 기보 표기 생성 (예: "백 나이트(♘) g1→f3", "백 킹(♔) O-O [캐슬링]", "백 폰(♙) e7→e8=♕ [체크!]")
     */
    formatMoveNotation(move, eventType) {
      if (move.isPass) {
        return `${move.piece.side === SIDES.CHU ? '백' : '흑'}: 대기`;
      }
      const sideLabel = move.piece.side === SIDES.CHU ? '백' : '흑';
      if (move.isCastling) {
        const castleStr = move.castlingSide === 'KINGSIDE' ? 'O-O (킹사이드 캐슬링)' : 'O-O-O (퀸사이드 캐슬링)';
        return `${sideLabel} ${move.piece.kr}(${move.piece.hanja}) ${castleStr}`;
      }

      const pieceLabel = `${move.piece.kr}(${move.piece.hanja})`;
      const fromSq = toAlgebraic(move.fromX, move.fromY);
      const toSq = toAlgebraic(move.toX, move.toY);
      const capText = move.captured
        ? ` × ${move.captured.kr}(${move.captured.hanja})${move.isEnPassant ? ' [앙파상]' : ''}`
        : '';
      const promoInfo = move.isPromotion && move.promoteTo
        ? `=${PIECE_LABELS[move.piece.side][move.promoteTo].hanja}(${PIECE_LABELS[move.piece.side][move.promoteTo].kr} 승진)`
        : '';

      let suffix = '';
      if (eventType === 'CHECKMATE') suffix = ' # [체크메이트!]';
      else if (eventType === 'CHECK') suffix = ' + [체크!]';
      else if (eventType === 'STALEMATE') suffix = ' [스테일메이트]';

      return `${sideLabel} ${pieceLabel} ${fromSq}→${toSq}${capText}${promoInfo}${suffix}`;
    }

    getState() {
      return {
        board: cloneBoard(this.board),
        enPassantTarget: this.enPassantTarget ? { ...this.enPassantTarget } : null,
        currentTurn: this.currentTurn,
        turnCount: this.turnCount,
        halfMoveClock: this.halfMoveClock,
        chuFormation: this.chuFormation,
        hanFormation: this.hanFormation,
        chuSkin: this.chuSkin,
        hanSkin: this.hanSkin,
        inCheck: this.inCheck,
        checkAttackers: this.checkAttackers,
        bikjangState: this.bikjangState,
        lastEvent: this.lastEvent,
        isGameOver: this.isGameOver,
        winner: this.winner,
        winReason: this.winReason,
        scores: this.scores,
        capturedPieces: this.capturedPieces,
        lostPieces: this.lostPieces,
        canUndo: this.history.length > 0,
        historyCount: this.history.length,
        lastMove: this.history.length > 0 ? this.history[this.history.length - 1].move : null
      };
    }
  }

  // ============================================================================
  // window.ChessAI — Minimax + Alpha-Beta + Quiescence + 8x8 PST + 중세 지휘관 대사
  // ============================================================================

  const DIFFICULTIES = Object.freeze({
    EASY: {
      id: 'EASY',
      code: 'NOVICE',
      level: 1,
      title: '초급 : 종자 (Squire)',
      description: '기초 행마와 단순 기물 교환 위주로 응수하는 입문용 상대',
      maxDepth: 2,
      quiescenceDepth: 0,
      randomness: 32,
      timeLimitMs: 450
    },
    NORMAL: {
      id: 'NORMAL',
      code: 'KNIGHT',
      level: 2,
      title: '중급 : 기사단장 (Knight Commander)',
      description: '중앙 장악, 캐슬링, 나이트 전초기지 활용에 능숙한 숙련 지휘관',
      maxDepth: 3,
      quiescenceDepth: 1,
      randomness: 6,
      timeLimitMs: 900
    },
    HARD: {
      id: 'HARD',
      code: 'WARLORD',
      level: 3,
      title: '상급 : 대성기사 (Grandmaster Paladin)',
      description: '깊이 4 탐색과 포획 연장 수읽기(Quiescence)로 전술 타격을 가하는 최고 난이도',
      maxDepth: 4,
      quiescenceDepth: 2,
      randomness: 0,
      timeLimitMs: 1600
    }
  });

  const DIFFICULTY_ALIASES = Object.freeze({
    EASY: 'EASY',
    NOVICE: 'EASY',
    BEGINNER: 'EASY',
    '1': 'EASY',
    NORMAL: 'NORMAL',
    MEDIUM: 'NORMAL',
    KNIGHT: 'NORMAL',
    '2': 'NORMAL',
    HARD: 'HARD',
    EXPERT: 'HARD',
    WARLORD: 'HARD',
    MASTER: 'HARD',
    '3': 'HARD'
  });

  const BASE_PIECE_VALUES = Object.freeze({
    KING: 50000,
    QUEEN: 920,
    ROOK: 510,
    BISHOP: 330,
    KNIGHT: 320,
    PAWN: 100
  });

  /**
   * 백(CHU, 하단 y=6,7 출발 -> 상단 y=0,1 진격) 기준 8x8 위치 가중치 테이블 (PST)
   * 흑(HAN)은 행(y)을 `7 - y`로 대칭 반전하여 참조
   */
  const PST_CHU = Object.freeze({
    PAWN: [
      [  0,   0,   0,   0,   0,   0,   0,   0], // y=0 (프로모션 달성 줄)
      [ 55,  60,  65,  75,  75,  65,  60,  55], // y=1 (7랭크: 프로모션 임박)
      [ 18,  22,  30,  42,  42,  30,  22,  18], // y=2 (6랭크)
      [  8,  12,  20,  32,  32,  20,  12,   8], // y=3 (5랭크 중앙 압박)
      [  4,   6,  12,  26,  26,  12,   6,   4], // y=4 (4랭크 중앙 장악)
      [  4,  -2,  -6,   8,   8,  -6,  -2,   4], // y=5 (3랭크)
      [  6,  10,  10, -18, -18,  10,  10,   6], // y=6 (초기 2랭크: 중앙 폰 전진 유도)
      [  0,   0,   0,   0,   0,   0,   0,   0]
    ],
    KNIGHT: [
      [-45, -35, -25, -20, -20, -25, -35, -45],
      [-35, -15,   5,  10,  10,   5, -15, -35],
      [-25,  10,  22,  28,  28,  22,  10, -25], // 전초기지(Outpost)
      [-20,  12,  26,  34,  34,  26,  12, -20],
      [-20,   8,  22,  30,  30,  22,   8, -20],
      [-25,   6,  16,  20,  20,  16,   6, -25],
      [-35, -15,   0,   6,   6,   0, -15, -35],
      [-45, -30, -20, -20, -20, -20, -30, -45]
    ],
    BISHOP: [
      [-20, -10, -10, -10, -10, -10, -10, -20],
      [-10,   5,   8,   8,   8,   8,   5, -10],
      [-10,  10,  14,  18,  18,  14,  10, -10],
      [-10,   8,  16,  20,  20,  16,   8, -10],
      [-10,   8,  18,  20,  20,  18,   8, -10],
      [-10,  14,  14,  16,  16,  14,  14, -10], // 피앙케토 및 주 대각선
      [-10,  12,   6,   8,   8,   6,  12, -10],
      [-20, -10, -12, -10, -10, -12, -10, -20]
    ],
    ROOK: [
      [  8,  10,  14,  18,  18,  14,  10,   8],
      [ 24,  28,  32,  36,  36,  32,  28,  24], // 7랭크 침투 보너스
      [ -4,   4,   8,  12,  12,   8,   4,  -4],
      [ -4,   2,   6,  10,  10,   6,   2,  -4],
      [ -4,   0,   6,   8,   8,   6,   0,  -4],
      [ -4,   0,   4,   8,   8,   4,   0,  -4],
      [ -4,   2,   6,  10,  10,   6,   2,  -4],
      [  0,   2,   6,  14,  14,   6,   2,   0]  // 중앙 오픈 파일(d, e열) 선호
    ],
    QUEEN: [
      [-20, -10, -10,  -5,  -5, -10, -10, -20],
      [-10,   4,   8,  10,  10,   8,   4, -10],
      [-10,   6,  10,  14,  14,  10,   6, -10],
      [ -5,   6,  12,  16,  16,  12,   6,  -5],
      [  0,   6,  12,  16,  16,  12,   6,   0],
      [-10,   8,  10,  12,  12,  10,   8, -10],
      [-10,   4,   8,   8,   8,   8,   4, -10],
      [-20, -10, -10,  -5,  -5, -10, -10, -20]
    ],
    KING: [
      [-35, -45, -45, -55, -55, -45, -45, -35],
      [-35, -45, -45, -55, -55, -45, -45, -35],
      [-35, -45, -45, -55, -55, -45, -45, -35],
      [-35, -45, -45, -55, -55, -45, -45, -35],
      [-25, -35, -35, -45, -45, -35, -35, -25],
      [-15, -25, -25, -25, -25, -25, -25, -15],
      [ 15,  18,   0,  -5,  -5,   0,  18,  15],
      [ 20,  32,  26, -12,   0,  -8,  34,  22]  // 캐슬링 안전 지대(g1/c1) 강력 선호
    ]
  });

  function normalizeDifficulty(diffKey) {
    const key = String(diffKey || 'NORMAL').toUpperCase();
    return DIFFICULTY_ALIASES[key] || 'NORMAL';
  }

  function getPSTBonus(piece) {
    const table = PST_CHU[piece.type];
    if (!table) return 0;
    const row = piece.side === SIDES.CHU ? piece.y : 7 - piece.y;
    const col = piece.x;
    return table[row] ? table[row][col] || 0 : 0;
  }

  /**
   * 정적 보드 평가 함수 (Static Board Evaluation)
   */
  function evaluateBoard(board, aiSide) {
    let chuScore = 0;
    let hanScore = 0;

    let chuKing = null;
    let hanKing = null;
    let chuBishops = 0;
    let hanBishops = 0;

    for (let y = 0; y < BOARD_ROWS; y++) {
      for (let x = 0; x < BOARD_COLS; x++) {
        const p = board[y][x];
        if (!p) continue;

        const baseVal = BASE_PIECE_VALUES[p.type] || 0;
        const pstVal = getPSTBonus(p);
        let tacticalVal = 0;

        if (p.type === PIECE_TYPES.KING) {
          if (p.side === SIDES.CHU) chuKing = p;
          else hanKing = p;
        } else if (p.type === PIECE_TYPES.BISHOP) {
          if (p.side === SIDES.CHU) chuBishops++;
          else hanBishops++;
        } else if (p.type === PIECE_TYPES.ROOK) {
          // 7랭크 침투 보너스
          if ((p.side === SIDES.CHU && y === 1) || (p.side === SIDES.HAN && y === 6)) {
            tacticalVal += 25;
          }
        }

        const totalPieceScore = baseVal + pstVal + tacticalVal;
        if (p.side === SIDES.CHU) {
          chuScore += totalPieceScore;
        } else {
          hanScore += totalPieceScore;
        }
      }
    }

    if (!chuKing) return aiSide === SIDES.HAN ? 99999 : -99999;
    if (!hanKing) return aiSide === SIDES.CHU ? 99999 : -99999;

    // 쌍비숍(Bishop Pair) 시너지 보너스
    if (chuBishops >= 2) chuScore += 35;
    if (hanBishops >= 2) hanScore += 35;

    // 체크 위협 가산점
    if (isKingInCheck(board, SIDES.CHU)) hanScore += 55;
    if (isKingInCheck(board, SIDES.HAN)) chuScore += 55;

    const netChu = chuScore - hanScore;
    return aiSide === SIDES.CHU ? netChu : -netChu;
  }

  /**
   * 착수 정렬 (MVV-LVA + 프로모션 + 캐슬링 + 체크 + PST 위치 향상도)
   */
  function scoreMoveForOrdering(move) {
    let priority = 0;
    if (move.isPromotion) {
      priority += 14000 + (BASE_PIECE_VALUES[move.promoteTo || 'QUEEN'] || 920);
    }
    if (move.isCapture && move.captured) {
      const victimVal = BASE_PIECE_VALUES[move.captured.type] || 100;
      const attackerVal = BASE_PIECE_VALUES[move.piece.type] || 100;
      priority += 10000 + victimVal * 10 - Math.floor(attackerVal / 10);
    }
    if (move.causesCheck) {
      priority += 5000;
    }
    if (move.isCastling) {
      priority += 3500;
    }
    const pstBefore = getPSTBonus(move.piece);
    const pstAfter = getPSTBonus({
      type: move.piece.type,
      side: move.piece.side,
      x: move.toX,
      y: move.toY
    });
    priority += (pstAfter - pstBefore) * 12;
    return priority;
  }

  function orderMoves(moves) {
    return moves.slice().sort((a, b) => scoreMoveForOrdering(b) - scoreMoveForOrdering(a));
  }

  /**
   * Quiescence Search (포획/프로모션 연장 탐색으로 수평선 효과 방지)
   */
  function quiescence(board, qDepth, alpha, beta, maximizingPlayer, currentSide, aiSide, deadline) {
    const standPat = evaluateBoard(board, aiSide);
    if (qDepth <= 0 || (deadline && Date.now() > deadline)) {
      return standPat;
    }

    if (maximizingPlayer) {
      if (standPat >= beta) return standPat;
      if (standPat > alpha) alpha = standPat;
    } else {
      if (standPat <= alpha) return standPat;
      if (standPat < beta) beta = standPat;
    }

    const tacticalMoves = getAllLegalMoves(board, currentSide).filter(
      (m) => m.isCapture || m.isPromotion
    );
    if (tacticalMoves.length === 0) {
      return standPat;
    }

    const ordered = orderMoves(tacticalMoves);
    const nextSide = getOpponentSide(currentSide);

    if (maximizingPlayer) {
      let maxEval = standPat;
      for (let i = 0; i < ordered.length; i++) {
        const mv = ordered[i];
        const nextBoard = simulateMoveOnBoard(board, mv);
        const score = quiescence(
          nextBoard,
          qDepth - 1,
          alpha,
          beta,
          false,
          nextSide,
          aiSide,
          deadline
        );
        if (score > maxEval) maxEval = score;
        if (score > alpha) alpha = score;
        if (beta <= alpha) break;
      }
      return maxEval;
    } else {
      let minEval = standPat;
      for (let i = 0; i < ordered.length; i++) {
        const mv = ordered[i];
        const nextBoard = simulateMoveOnBoard(board, mv);
        const score = quiescence(
          nextBoard,
          qDepth - 1,
          alpha,
          beta,
          true,
          nextSide,
          aiSide,
          deadline
        );
        if (score < minEval) minEval = score;
        if (score < beta) beta = score;
        if (beta <= alpha) break;
      }
      return minEval;
    }
  }

  /**
   * Minimax + Alpha-Beta Pruning 재귀 탐색
   */
  function alphaBeta(board, depth, qDepth, alpha, beta, maximizingPlayer, currentSide, aiSide, deadline) {
    if (deadline && Date.now() > deadline) {
      return evaluateBoard(board, aiSide);
    }

    if (depth <= 0) {
      if (qDepth > 0) {
        return quiescence(board, qDepth, alpha, beta, maximizingPlayer, currentSide, aiSide, deadline);
      }
      return evaluateBoard(board, aiSide);
    }

    const legalMoves = getAllLegalMoves(board, currentSide);

    if (legalMoves.length === 0) {
      const inCheck = isKingInCheck(board, currentSide);
      if (inCheck) {
        // 체크메이트
        const mateScore = 85000 + depth * 500;
        return currentSide === aiSide ? -mateScore : mateScore;
      }
      // 스테일메이트 (무승부 = 0)
      return 0;
    }

    const ordered = orderMoves(legalMoves);
    const nextSide = getOpponentSide(currentSide);

    if (maximizingPlayer) {
      let maxEval = -Infinity;
      for (let i = 0; i < ordered.length; i++) {
        const mv = ordered[i];
        const nextBoard = simulateMoveOnBoard(board, mv);
        const evalScore = alphaBeta(
          nextBoard,
          depth - 1,
          qDepth,
          alpha,
          beta,
          false,
          nextSide,
          aiSide,
          deadline
        );
        if (evalScore > maxEval) maxEval = evalScore;
        if (evalScore > alpha) alpha = evalScore;
        if (beta <= alpha) break;
      }
      return maxEval;
    } else {
      let minEval = Infinity;
      for (let i = 0; i < ordered.length; i++) {
        const mv = ordered[i];
        const nextBoard = simulateMoveOnBoard(board, mv);
        const evalScore = alphaBeta(
          nextBoard,
          depth - 1,
          qDepth,
          alpha,
          beta,
          true,
          nextSide,
          aiSide,
          deadline
        );
        if (evalScore < minEval) minEval = evalScore;
        if (evalScore < beta) beta = evalScore;
        if (beta <= alpha) break;
      }
      return minEval;
    }
  }

  /**
   * 중세 서양 체스 지휘관 전술 대사(commentary) 생성
   */
  function buildTacticalCommentary(move, evalScore) {
    if (!move) return '성벽을 굳게 걸어 잠그고 적의 움직임을 살핍니다.';
    if (move.isPass) return '전열을 정비하며 다음 공세를 준비합니다.';

    const pName = move.piece.kr;
    const pSym = move.piece.hanja;

    if (move.isPromotion) {
      const promoLabel = PIECE_LABELS[move.piece.side][move.promoteTo || PIECE_TYPES.QUEEN];
      return `보병(폰)이 적진 끝까지 돌파하여 ${promoLabel.kr}(${promoLabel.hanja})으로 승진 각성합니다!`;
    }
    if (move.isCastling) {
      const sideText = move.castlingSide === 'KINGSIDE' ? '킹사이드(O-O)' : '퀸사이드(O-O-O)';
      return `${sideText} 캐슬링! 국왕을 성채 안쪽으로 대피시키고 룩(♖)을 중앙 전선에 투입합니다!`;
    }
    if (move.isEnPassant) {
      return `앙파상(En Passant) 기습! 전열을 스쳐 지나가던 적 보병을 단칼에 베어 넘깁니다!`;
    }
    if (move.causesCheck && move.isCapture && move.captured) {
      return `${pName}(${pSym}) 부대가 적의 ${move.captured.kr}(${move.captured.hanja})을 격파하며 국왕에게 체크(Check)를 선포합니다!`;
    }
    if (move.causesCheck) {
      if (move.piece.type === PIECE_TYPES.KNIGHT) {
        return `나이트(♘) 기병대가 적의 방어망을 뛰어넘어 날카로운 체크 포크를 노립니다!`;
      }
      return `${pName}(${pSym}) 부대를 진격시켜 적 국왕에게 체크(Check)를 부릅니다!`;
    }
    if (move.isCapture && move.captured) {
      return `${pName}(${pSym}) 부대로 적의 ${move.captured.kr}(${move.captured.hanja})을 정밀 타격하여 섬멸합니다!`;
    }
    if (move.piece.type === PIECE_TYPES.QUEEN) {
      return `왕실 결전병기 퀸(${pSym})이 전장에 출격하여 전방위 화망을 전개합니다!`;
    }
    if (move.piece.type === PIECE_TYPES.KNIGHT) {
      return `중장기병 나이트(${pSym})가 말발굽 소리를 울리며 전초기지로 도약합니다.`;
    }
    if (move.piece.type === PIECE_TYPES.BISHOP) {
      return `비숍(${pSym})이 긴 대각선 회랑을 장악하며 적진을 겨눕니다.`;
    }
    if (move.piece.type === PIECE_TYPES.ROOK) {
      return `공성탑 룩(${pSym})이 열린 파일을 장악하여 중원 통제력을 높입니다.`;
    }
    if (evalScore > 300) {
      return `전세가 유리합니다. 전열 보병(${pName})을 밀어붙여 중앙을 장악합니다.`;
    }
    return `전열 보병(${pName})이 방패벽을 세우며 중앙 요충지로 전진합니다.`;
  }

  /**
   * 최적의 체스 착수 계산 (동기)
   */
  function getBestMove(gameOrBoard, side, difficultyKey = 'NORMAL') {
    const isGameInstance = gameOrBoard && typeof gameOrBoard.getState === 'function';
    const board = isGameInstance ? gameOrBoard.board : gameOrBoard;
    const aiSide = side || (isGameInstance ? gameOrBoard.currentTurn : SIDES.HAN);

    if (isGameInstance && gameOrBoard.enPassantTarget) {
      setBoardEnPassant(board, gameOrBoard.enPassantTarget);
    }

    const diffId = normalizeDifficulty(difficultyKey);
    const diffConfig = DIFFICULTIES[diffId];

    const legalMoves = getAllLegalMoves(board, aiSide);
    if (legalMoves.length === 0) {
      return {
        move: null,
        score: -99999,
        commentary: '더 이상 응수할 합법적인 수가 없습니다.',
        difficulty: diffConfig
      };
    }

    if (legalMoves.length === 1) {
      const onlyMove = legalMoves[0];
      return {
        move: onlyMove,
        score: 0,
        commentary: buildTacticalCommentary(onlyMove, 0),
        difficulty: diffConfig
      };
    }

    const orderedMoves = orderMoves(legalMoves);
    const nextSide = getOpponentSide(aiSide);
    const deadline = Date.now() + diffConfig.timeLimitMs;

    // 1. 1수 체크메이트 즉시 탐색
    for (let i = 0; i < orderedMoves.length; i++) {
      const mv = orderedMoves[i];
      if (mv.causesCheck) {
        const nextBoard = simulateMoveOnBoard(board, mv);
        const oppMoves = getAllLegalMoves(nextBoard, nextSide);
        if (oppMoves.length === 0) {
          return {
            move: mv,
            score: 99999,
            commentary: '체크메이트! 적 국왕의 퇴로를 완벽히 봉쇄하여 승리의 깃발을 꽂습니다!',
            difficulty: diffConfig
          };
        }
      }
    }

    // 2. Iterative Deepening + Alpha-Beta + Quiescence
    let bestMove = orderedMoves[0];
    let bestScore = -Infinity;
    const targetDepth = diffConfig.maxDepth;
    const qDepth = diffConfig.quiescenceDepth || 0;

    for (let currentDepth = 1; currentDepth <= targetDepth; currentDepth++) {
      if (currentDepth > 1 && Date.now() > deadline) break;

      let alpha = -Infinity;
      const beta = Infinity;
      let depthBestMove = orderedMoves[0];
      let depthBestScore = -Infinity;
      let timedOutInDepth = false;

      for (let i = 0; i < orderedMoves.length; i++) {
        if (currentDepth > 1 && Date.now() > deadline) {
          timedOutInDepth = true;
          break;
        }

        const mv = orderedMoves[i];
        const nextBoard = simulateMoveOnBoard(board, mv);

        const rootAlpha = diffConfig.randomness > 0 ? alpha - diffConfig.randomness * 2 : alpha;
        const rawScore = alphaBeta(
          nextBoard,
          currentDepth - 1,
          qDepth,
          rootAlpha,
          beta,
          false,
          nextSide,
          aiSide,
          deadline
        );

        if (currentDepth > 1 && Date.now() > deadline) {
          timedOutInDepth = true;
          break;
        }

        const noisyScore =
          diffConfig.randomness > 0
            ? rawScore + (Math.random() * 2 - 1) * diffConfig.randomness
            : rawScore;

        if (noisyScore > depthBestScore) {
          depthBestScore = noisyScore;
          depthBestMove = mv;
        }
        if (rawScore > alpha) {
          alpha = rawScore;
        }
      }

      if (!timedOutInDepth || currentDepth === 1) {
        bestMove = depthBestMove;
        bestScore = depthBestScore;
      }
    }

    return {
      move: bestMove,
      score: Math.round(bestScore),
      commentary: buildTacticalCommentary(bestMove, bestScore),
      difficulty: diffConfig
    };
  }

  function chooseMove(gameOrBoard, side, difficultyKey = 'NORMAL') {
    return getBestMove(gameOrBoard, side, difficultyKey);
  }

  function chooseMoveAsync(gameOrBoard, side, difficultyKey = 'NORMAL', minDelayMs = 260) {
    return new Promise((resolve) => {
      const startTime = Date.now();
      setTimeout(() => {
        const result = getBestMove(gameOrBoard, side, difficultyKey);
        const elapsed = Date.now() - startTime;
        const remain = Math.max(0, minDelayMs - elapsed);
        if (remain > 0) {
          setTimeout(() => resolve(result), remain);
        } else {
          resolve(result);
        }
      }, 30);
    });
  }

  function chooseCounterFormation() {
    return 'STANDARD';
  }

  // ============================================================================
  // 모듈 내보내기 (window.ChessEngine & window.ChessAI)
  // ============================================================================

  const ChessEngine = {
    BOARD_COLS,
    BOARD_ROWS,
    SIDES,
    PIECE_TYPES,
    PIECE_SCORES,
    HAN_KOMI,
    PIECE_LABELS,
    FORMATIONS,
    PROMOTION_TYPES,
    PALACE_BOUNDS,
    PALACE_DIAGONAL_NEIGHBORS,
    PALACE_DIAGONAL_RAYS,

    // 유틸리티 & 정적 규칙 함수
    isInBounds,
    isInPalace,
    getOpponentSide,
    normalizeFormation,
    normalizePromotionType,
    toAlgebraic,
    createPiece,
    clonePiece,
    cloneBoard,
    createInitialBoard,
    isSquareAttacked,
    getPseudoMoves,
    getPseudoMovesWithMeta,
    findKing,
    getBikjangState,
    isBikjang,
    getCheckStatus,
    isKingInCheck,
    isInsufficientMaterial,
    simulateMoveOnBoard,
    getLegalMovesForPiece,
    getLegalMovesForPieceWithMeta,
    getAllLegalMoves,
    calculateScores,

    // 대국 관리 클래스 및 팩토리 (JanggiGame 호환 별칭 포함)
    ChessGame,
    JanggiGame: ChessGame,
    createGame: (config) => new ChessGame(config)
  };

  const ChessAI = {
    DIFFICULTIES,
    BASE_PIECE_VALUES,
    normalizeDifficulty,
    evaluateBoard,
    getBestMove,
    chooseMove,
    chooseMoveAsync,
    chooseCounterFormation
  };

  global.ChessEngine = ChessEngine;
  global.ChessAI = ChessAI;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ChessEngine, ChessAI };
  }
})(typeof window !== 'undefined' ? window : globalThis);
