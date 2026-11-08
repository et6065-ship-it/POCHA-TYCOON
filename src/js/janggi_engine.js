/**
 * @fileoverview 정통 한국 장기 규칙 엔진 (Authentic Korean Janggi Rule Engine)
 * @module window.JanggiEngine
 *
 * 지원 기능:
 * - 9x10 장기판 좌표계 (열 x: 0~8, 행 y: 0~9), 초(CHU, 하단 선공) / 한(HAN, 상단 후공)
 * - 4대 상차림(내상 INNER, 외상 OUTER, 왼상 LEFT, 오른상 RIGHT) 완벽 지원
 * - 7대 기물(궁, 사, 차, 포, 마, 상, 졸/병) 정통 행마법:
 *   - 궁/사/차/포/졸의 3x3 궁성 대각선 이동
 *   - 마(1멱) 및 상(2멱) 길목 차단 판정 (UI 힌트용 막힌 멱 좌표 반환 포함)
 *   - 포(包)의 다리(Screen) 조건 및 포불넘포(포 넘기 금지)·포불장포(포 잡기 금지)
 * - 자살수(왕이 잡히는 수) 원천 차단 및 합법 착수 필터링
 * - 장군(Check) / 멍군(Check Escape) / 외통수(Checkmate) / 초완봉(Stalemate) 판정
 * - 빅장(Bikjang: 마주보는 왕 사이에 기물이 없는 상태) 감지 및 빅장 무승부/점수 판정
 * - 한수 쉼(Pass), 무르기(Undo), 기물 점수 계산(차13, 포7, 마5, 상3, 사3, 졸2, 한 덤 1.5점)
 */

(function (global) {
  'use strict';

  const BOARD_COLS = 9;
  const BOARD_ROWS = 10;

  const SIDES = Object.freeze({
    CHU: 'CHU', // 초(楚) - 하단(y: 7~9 궁성), 선공(Blue/Green)
    HAN: 'HAN'  // 한(漢) - 상단(y: 0~2 궁성), 후공(Red), 덤 1.5점
  });

  const PIECE_TYPES = Object.freeze({
    KING: 'KING',         // 궁(초/한)
    CAR: 'CHARIOT',       // 별칭 호환
    CHARIOT: 'CHARIOT',   // 차(車) - 13점
    CANNON: 'CANNON',     // 포(包) - 7점
    HORSE: 'HORSE',       // 마(馬) - 5점
    ELEPHANT: 'ELEPHANT', // 상(象) - 3점
    GUARD: 'GUARD',       // 사(士) - 3점
    SOLDIER: 'SOLDIER'    // 졸/병(卒/兵) - 2점
  });

  const PIECE_SCORES = Object.freeze({
    KING: 0,
    CHARIOT: 13,
    CANNON: 7,
    HORSE: 5,
    ELEPHANT: 3,
    GUARD: 3,
    SOLDIER: 2
  });

  const HAN_KOMI = 1.5; // 한(후공) 덤 1.5점

  /**
   * 기물별 한자 및 한글 표기 메타데이터
   */
  const PIECE_LABELS = Object.freeze({
    CHU: {
      KING: { hanja: '楚', kr: '초', name: '궁(초)' },
      CHARIOT: { hanja: '車', kr: '차', name: '차' },
      CANNON: { hanja: '包', kr: '포', name: '포' },
      HORSE: { hanja: '馬', kr: '마', name: '마' },
      ELEPHANT: { hanja: '象', kr: '상', name: '상' },
      GUARD: { hanja: '士', kr: '사', name: '사' },
      SOLDIER: { hanja: '卒', kr: '졸', name: '졸' }
    },
    HAN: {
      KING: { hanja: '漢', kr: '한', name: '궁(한)' },
      CHARIOT: { hanja: '車', kr: '차', name: '차' },
      CANNON: { hanja: '包', kr: '포', name: '포' },
      HORSE: { hanja: '馬', kr: '마', name: '마' },
      ELEPHANT: { hanja: '象', kr: '상', name: '상' },
      GUARD: { hanja: '士', kr: '사', name: '사' },
      SOLDIER: { hanja: '兵', kr: '병', name: '병' }
    }
  });

  /**
   * 4대 상차림 정의 (열 x=1, 2 및 x=6, 7에 배치될 마/상 구성)
   */
  const FORMATIONS = Object.freeze({
    INNER: {
      id: 'INNER',
      code: 'INNER_ELEPHANT',
      name: '내상 (마·상·상·마)',
      shortName: '내상',
      description: '중앙 방어력과 궁성 보호에 특화된 정석 수비형 상차림',
      layout: { 1: PIECE_TYPES.HORSE, 2: PIECE_TYPES.ELEPHANT, 6: PIECE_TYPES.ELEPHANT, 7: PIECE_TYPES.HORSE }
    },
    OUTER: {
      id: 'OUTER',
      code: 'OUTER_ELEPHANT',
      name: '외상 (상·마·마·상)',
      shortName: '외상',
      description: '양 날개 기동력과 중앙 마(馬) 진출이 빠른 공격형 상차림',
      layout: { 1: PIECE_TYPES.ELEPHANT, 2: PIECE_TYPES.HORSE, 6: PIECE_TYPES.HORSE, 7: PIECE_TYPES.ELEPHANT }
    },
    LEFT: {
      id: 'LEFT',
      code: 'LEFT_ELEPHANT',
      name: '왼상 (상·마·상·마)',
      shortName: '왼상',
      description: '좌측 상·우측 마 집중 운용에 유리한 비대칭 밸런스 상차림',
      layout: { 1: PIECE_TYPES.ELEPHANT, 2: PIECE_TYPES.HORSE, 6: PIECE_TYPES.ELEPHANT, 7: PIECE_TYPES.HORSE }
    },
    RIGHT: {
      id: 'RIGHT',
      code: 'RIGHT_ELEPHANT',
      name: '오른상 (마·상·마·상)',
      shortName: '오른상',
      description: '우측 상·좌측 마 집중 운용에 유리한 비대칭 밸런스 상차림',
      layout: { 1: PIECE_TYPES.HORSE, 2: PIECE_TYPES.ELEPHANT, 6: PIECE_TYPES.HORSE, 7: PIECE_TYPES.ELEPHANT }
    }
  });

  // 별칭 매핑 (INNER_ELEPHANT 등 긴 키로 호출해도 정상 작동)
  const FORMATION_ALIASES = Object.freeze({
    INNER: 'INNER',
    INNER_ELEPHANT: 'INNER',
    OUTER: 'OUTER',
    OUTER_ELEPHANT: 'OUTER',
    LEFT: 'LEFT',
    LEFT_ELEPHANT: 'LEFT',
    RIGHT: 'RIGHT',
    RIGHT_ELEPHANT: 'RIGHT'
  });

  /**
   * 궁성(Palace) 영역 및 대각선 그래프 정의
   * - 한(HAN): x ∈ [3, 5], y ∈ [0, 2], 중심 (4, 1)
   * - 초(CHU): x ∈ [3, 5], y ∈ [7, 9], 중심 (4, 8)
   */
  const PALACE_BOUNDS = Object.freeze({
    HAN: { minX: 3, maxX: 5, minY: 0, maxY: 2, centerX: 4, centerY: 1 },
    CHU: { minX: 3, maxX: 5, minY: 7, maxY: 9, centerX: 4, centerY: 8 }
  });

  /**
   * 궁성 내 대각선 이동이 가능한 인접 노드 맵
   * 귀퉁이 <-> 중심만 대각선으로 연결됨
   */
  const PALACE_DIAGONAL_NEIGHBORS = Object.freeze({
    // HAN 궁성
    '3,0': [{ x: 4, y: 1 }],
    '5,0': [{ x: 4, y: 1 }],
    '3,2': [{ x: 4, y: 1 }],
    '5,2': [{ x: 4, y: 1 }],
    '4,1': [
      { x: 3, y: 0 },
      { x: 5, y: 0 },
      { x: 3, y: 2 },
      { x: 5, y: 2 }
    ],
    // CHU 궁성
    '3,7': [{ x: 4, y: 8 }],
    '5,7': [{ x: 4, y: 8 }],
    '3,9': [{ x: 4, y: 8 }],
    '5,9': [{ x: 4, y: 8 }],
    '4,8': [
      { x: 3, y: 7 },
      { x: 5, y: 7 },
      { x: 3, y: 9 },
      { x: 5, y: 9 }
    ]
  });

  /**
   * 궁성 귀퉁이에서 중심을 관통하여 반대편 귀퉁이로 이어지는 직선 대각선 경로 (차/포 전용)
   */
  const PALACE_DIAGONAL_RAYS = Object.freeze({
    // HAN 궁성 귀퉁이 출발
    '3,0': [{ x: 4, y: 1 }, { x: 5, y: 2 }],
    '5,0': [{ x: 4, y: 1 }, { x: 3, y: 2 }],
    '3,2': [{ x: 4, y: 1 }, { x: 5, y: 0 }],
    '5,2': [{ x: 4, y: 1 }, { x: 3, y: 0 }],
    // CHU 궁성 귀퉁이 출발
    '3,7': [{ x: 4, y: 8 }, { x: 5, y: 9 }],
    '5,7': [{ x: 4, y: 8 }, { x: 3, y: 9 }],
    '3,9': [{ x: 4, y: 8 }, { x: 5, y: 7 }],
    '5,9': [{ x: 4, y: 8 }, { x: 3, y: 7 }]
  });

  // ============================================================================
  // 유틸리티 함수
  // ============================================================================

  function isInBounds(x, y) {
    return x >= 0 && x < BOARD_COLS && y >= 0 && y < BOARD_ROWS;
  }

  function isInPalace(x, y, side) {
    if (side === SIDES.HAN) {
      return x >= 3 && x <= 5 && y >= 0 && y <= 2;
    }
    if (side === SIDES.CHU) {
      return x >= 3 && x <= 5 && y >= 7 && y <= 9;
    }
    // side 미지정 시 양쪽 궁성 모두 확인
    return (
      (x >= 3 && x <= 5 && y >= 0 && y <= 2) ||
      (x >= 3 && x <= 5 && y >= 7 && y <= 9)
    );
  }

  function getOpponentSide(side) {
    return side === SIDES.CHU ? SIDES.HAN : SIDES.CHU;
  }

  function normalizeFormation(formationKey) {
    const key = String(formationKey || 'INNER').toUpperCase();
    return FORMATION_ALIASES[key] || 'INNER';
  }

  function createPiece(id, side, type, x, y) {
    const labelInfo = PIECE_LABELS[side][type];
    return {
      id,
      side,
      type,
      x,
      y,
      col: x,
      row: y,
      score: PIECE_SCORES[type] || 0,
      hanja: labelInfo.hanja,
      kr: labelInfo.kr,
      name: labelInfo.name,
      moveCount: 0
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
      kr: piece.kr,
      name: piece.name,
      moveCount: piece.moveCount || 0
    };
  }

  function cloneBoard(board) {
    const newBoard = new Array(BOARD_ROWS);
    for (let y = 0; y < BOARD_ROWS; y++) {
      newBoard[y] = new Array(BOARD_COLS);
      for (let x = 0; x < BOARD_COLS; x++) {
        newBoard[y][x] = board[y][x] ? clonePiece(board[y][x]) : null;
      }
    }
    return newBoard;
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
      isCapture: Boolean(capturedPiece),
      bridge: extra.bridge || null,       // 포(CANNON)가 넘어간 다리 좌표 {x, y}
      via: extra.via || null,             // 마/상/차 대각선 경유지 배열
      isPalaceDiagonal: Boolean(extra.isPalaceDiagonal),
      isPass: Boolean(extra.isPass)
    };
  }

  // ============================================================================
  // 초기 보드 생성 및 상차림 배치
  // ============================================================================

  /**
   * 지정된 초/한 상차림으로 9x10 보드 2차원 배열 생성 (`board[y][x]`)
   * @param {string} chuFormation - 초(하단) 상차림 ('INNER'|'OUTER'|'LEFT'|'RIGHT')
   * @param {string} hanFormation - 한(상단) 상차림 ('INNER'|'OUTER'|'LEFT'|'RIGHT')
   */
  function createInitialBoard(chuFormation = 'INNER', hanFormation = 'INNER') {
    const board = Array.from({ length: BOARD_ROWS }, () => Array(BOARD_COLS).fill(null));
    const chuForm = FORMATIONS[normalizeFormation(chuFormation)].layout;
    const hanForm = FORMATIONS[normalizeFormation(hanFormation)].layout;

    const place = (id, side, type, x, y) => {
      board[y][x] = createPiece(id, side, type, x, y);
    };

    // --- 한(HAN, 상단 y=0~3) 배치 ---
    place('HAN_CHARIOT_L', SIDES.HAN, PIECE_TYPES.CHARIOT, 0, 0);
    place('HAN_INNER_1', SIDES.HAN, hanForm[1], 1, 0);
    place('HAN_INNER_2', SIDES.HAN, hanForm[2], 2, 0);
    place('HAN_GUARD_L', SIDES.HAN, PIECE_TYPES.GUARD, 3, 0);
    place('HAN_GUARD_R', SIDES.HAN, PIECE_TYPES.GUARD, 5, 0);
    place('HAN_INNER_6', SIDES.HAN, hanForm[6], 6, 0);
    place('HAN_INNER_7', SIDES.HAN, hanForm[7], 7, 0);
    place('HAN_CHARIOT_R', SIDES.HAN, PIECE_TYPES.CHARIOT, 8, 0);

    place('HAN_KING', SIDES.HAN, PIECE_TYPES.KING, 4, 1);

    place('HAN_CANNON_L', SIDES.HAN, PIECE_TYPES.CANNON, 1, 2);
    place('HAN_CANNON_R', SIDES.HAN, PIECE_TYPES.CANNON, 7, 2);

    for (let i = 0; i < 5; i++) {
      const x = i * 2;
      place(`HAN_SOLDIER_${i + 1}`, SIDES.HAN, PIECE_TYPES.SOLDIER, x, 3);
    }

    // --- 초(CHU, 하단 y=6~9) 배치 ---
    place('CHU_CHARIOT_L', SIDES.CHU, PIECE_TYPES.CHARIOT, 0, 9);
    place('CHU_INNER_1', SIDES.CHU, chuForm[1], 1, 9);
    place('CHU_INNER_2', SIDES.CHU, chuForm[2], 2, 9);
    place('CHU_GUARD_L', SIDES.CHU, PIECE_TYPES.GUARD, 3, 9);
    place('CHU_GUARD_R', SIDES.CHU, PIECE_TYPES.GUARD, 5, 9);
    place('CHU_INNER_6', SIDES.CHU, chuForm[6], 6, 9);
    place('CHU_INNER_7', SIDES.CHU, chuForm[7], 7, 9);
    place('CHU_CHARIOT_R', SIDES.CHU, PIECE_TYPES.CHARIOT, 8, 9);

    place('CHU_KING', SIDES.CHU, PIECE_TYPES.KING, 4, 8);

    place('CHU_CANNON_L', SIDES.CHU, PIECE_TYPES.CANNON, 1, 7);
    place('CHU_CANNON_R', SIDES.CHU, PIECE_TYPES.CANNON, 7, 7);

    for (let i = 0; i < 5; i++) {
      const x = i * 2;
      place(`CHU_SOLDIER_${i + 1}`, SIDES.CHU, PIECE_TYPES.SOLDIER, x, 6);
    }

    return board;
  }

  // ============================================================================
  // 기물별 의사 합법 착수(Pseudo-Legal Moves) 및 막힌 멱(Blocked Necks) 계산
  // ============================================================================

  /**
   * 특정 기물의 의사 합법 이동(자살수 필터링 전) 및 UI 표시용 멱/다리 메타데이터 반환
   * @param {Array<Array<Object|null>>} board
   * @param {number} x
   * @param {number} y
   * @returns {{ moves: Array<Object>, blockedNecks: Array<Object>, bridges: Array<Object> }}
   */
  function getPseudoMovesWithMeta(board, x, y) {
    const piece = isInBounds(x, y) ? board[y][x] : null;
    if (!piece) {
      return { moves: [], blockedNecks: [], bridges: [] };
    }

    const moves = [];
    const blockedNecks = [];
    const bridges = [];
    const side = piece.side;

    const tryAddTarget = (tx, ty, extra = {}) => {
      if (!isInBounds(tx, ty)) return false;
      const occupant = board[ty][tx];
      if (!occupant) {
        moves.push(createMoveObject(x, y, tx, ty, piece, null, extra));
        return true; // 계속 진행 가능 여부(슬라이딩 기물용)
      }
      if (occupant.side !== side) {
        moves.push(createMoveObject(x, y, tx, ty, piece, occupant, extra));
      }
      return false; // 기물에 막힘
    };

    switch (piece.type) {
      case PIECE_TYPES.KING:
      case PIECE_TYPES.GUARD: {
        // 1. 자신의 3x3 궁성 내부 상하좌우 1칸
        const dirs = [
          { dx: 0, dy: -1 },
          { dx: 0, dy: 1 },
          { dx: -1, dy: 0 },
          { dx: 1, dy: 0 }
        ];
        for (const { dx, dy } of dirs) {
          const tx = x + dx;
          const ty = y + dy;
          if (isInPalace(tx, ty, side)) {
            tryAddTarget(tx, ty, { isPalaceDiagonal: false });
          }
        }
        // 2. 궁성 대각선 인접 노드 이동
        const diagNeighbors = PALACE_DIAGONAL_NEIGHBORS[`${x},${y}`];
        if (diagNeighbors) {
          for (const pt of diagNeighbors) {
            if (isInPalace(pt.x, pt.y, side)) {
              tryAddTarget(pt.x, pt.y, { isPalaceDiagonal: true });
            }
          }
        }
        break;
      }

      case PIECE_TYPES.CHARIOT: {
        // 1. 상하좌우 직선 무제한 슬라이딩
        const orthoDirs = [
          { dx: 0, dy: -1 },
          { dx: 0, dy: 1 },
          { dx: -1, dy: 0 },
          { dx: 1, dy: 0 }
        ];
        for (const { dx, dy } of orthoDirs) {
          let step = 1;
          while (true) {
            const tx = x + dx * step;
            const ty = y + dy * step;
            if (!isInBounds(tx, ty)) break;
            const canContinue = tryAddTarget(tx, ty, { isPalaceDiagonal: false });
            if (!canContinue) break;
            step++;
          }
        }

        // 2. 궁성 대각선 직선 이동
        // (a) 궁성 중심(4,1 또는 4,8)에 있을 때 네 귀퉁이로 1칸 이동
        if ((x === 4 && y === 1) || (x === 4 && y === 8)) {
          const corners = PALACE_DIAGONAL_NEIGHBORS[`${x},${y}`];
          for (const pt of corners) {
            tryAddTarget(pt.x, pt.y, { isPalaceDiagonal: true });
          }
        }
        // (b) 궁성 귀퉁이에 있을 때 중심을 거쳐 반대편 귀퉁이까지 직선 슬라이딩
        const ray = PALACE_DIAGONAL_RAYS[`${x},${y}`];
        if (ray) {
          const mid = ray[0];
          const far = ray[1];
          const canPassMid = tryAddTarget(mid.x, mid.y, { isPalaceDiagonal: true });
          if (canPassMid) {
            tryAddTarget(far.x, far.y, {
              isPalaceDiagonal: true,
              via: [{ x: mid.x, y: mid.y }]
            });
          }
        }
        break;
      }

      case PIECE_TYPES.CANNON: {
        // 1. 상하좌우 직선 다리(Screen) 점프 이동
        const orthoDirs = [
          { dx: 0, dy: -1 },
          { dx: 0, dy: 1 },
          { dx: -1, dy: 0 },
          { dx: 1, dy: 0 }
        ];
        for (const { dx, dy } of orthoDirs) {
          let step = 1;
          let bridgePiece = null;
          let bridgeCoord = null;

          while (true) {
            const tx = x + dx * step;
            const ty = y + dy * step;
            if (!isInBounds(tx, ty)) break;
            const occupant = board[ty][tx];

            if (!bridgePiece) {
              if (occupant) {
                // 포불넘포: 다리가 포(CANNON)이면 절대 넘을 수 없음
                if (occupant.type === PIECE_TYPES.CANNON) {
                  blockedNecks.push({
                    x: tx,
                    y: ty,
                    reason: 'CANNON_CANNOT_JUMP_CANNON',
                    label: '포불넘포(포 넘기 불가)'
                  });
                  break;
                }
                bridgePiece = occupant;
                bridgeCoord = { x: tx, y: ty, col: tx, row: ty, pieceId: occupant.id };
                bridges.push(bridgeCoord);
              }
            } else {
              // 이미 다리를 1개 넘은 상태
              if (!occupant) {
                moves.push(
                  createMoveObject(x, y, tx, ty, piece, null, {
                    bridge: bridgeCoord,
                    isPalaceDiagonal: false
                  })
                );
              } else {
                // 포불장포: 도착지의 기물이 적군이고 포(CANNON)가 아닐 때만 포획 가능
                if (occupant.side !== side && occupant.type !== PIECE_TYPES.CANNON) {
                  moves.push(
                    createMoveObject(x, y, tx, ty, piece, occupant, {
                      bridge: bridgeCoord,
                      isPalaceDiagonal: false
                    })
                  );
                } else if (occupant.side !== side && occupant.type === PIECE_TYPES.CANNON) {
                  blockedNecks.push({
                    x: tx,
                    y: ty,
                    reason: 'CANNON_CANNOT_CAPTURE_CANNON',
                    label: '포불장포(포 잡기 불가)'
                  });
                }
                break; // 두 번째 기물을 만나면 탐색 종료
              }
            }
            step++;
          }
        }

        // 2. 궁성 대각선 다리 점프 (귀퉁이 -> 중심(다리) -> 반대편 귀퉁이)
        const ray = PALACE_DIAGONAL_RAYS[`${x},${y}`];
        if (ray) {
          const mid = ray[0];
          const far = ray[1];
          const midPiece = board[mid.y][mid.x];
          if (midPiece) {
            if (midPiece.type === PIECE_TYPES.CANNON) {
              blockedNecks.push({
                x: mid.x,
                y: mid.y,
                reason: 'CANNON_CANNOT_JUMP_CANNON',
                label: '포불넘포(포 넘기 불가)'
              });
            } else {
              const bridgeCoord = { x: mid.x, y: mid.y, col: mid.x, row: mid.y, pieceId: midPiece.id };
              bridges.push(bridgeCoord);
              const farPiece = board[far.y][far.x];
              if (!farPiece) {
                moves.push(
                  createMoveObject(x, y, far.x, far.y, piece, null, {
                    bridge: bridgeCoord,
                    isPalaceDiagonal: true
                  })
                );
              } else if (farPiece.side !== side && farPiece.type !== PIECE_TYPES.CANNON) {
                moves.push(
                  createMoveObject(x, y, far.x, far.y, piece, farPiece, {
                    bridge: bridgeCoord,
                    isPalaceDiagonal: true
                  })
                );
              }
            }
          }
        }
        break;
      }

      case PIECE_TYPES.HORSE: {
        // 직선 1칸(멱) 확인 후 대각선 1칸 이동 (날일자)
        const horsePatterns = [
          { neckDx: 0, neckDy: -1, targets: [{ dx: -1, dy: -2 }, { dx: 1, dy: -2 }] },
          { neckDx: 0, neckDy: 1, targets: [{ dx: -1, dy: 2 }, { dx: 1, dy: 2 }] },
          { neckDx: -1, neckDy: 0, targets: [{ dx: -2, dy: -1 }, { dx: -2, dy: 1 }] },
          { neckDx: 1, neckDy: 0, targets: [{ dx: 2, dy: -1 }, { dx: 2, dy: 1 }] }
        ];

        for (const pattern of horsePatterns) {
          const nx = x + pattern.neckDx;
          const ny = y + pattern.neckDy;
          if (!isInBounds(nx, ny)) continue;

          if (board[ny][nx] !== null) {
            // 멱이 막힌 경우
            blockedNecks.push({
              x: nx,
              y: ny,
              reason: 'HORSE_NECK_BLOCKED',
              label: '마(馬) 멱 막힘'
            });
            continue;
          }

          for (const t of pattern.targets) {
            const tx = x + t.dx;
            const ty = y + t.dy;
            if (!isInBounds(tx, ty)) continue;
            tryAddTarget(tx, ty, {
              via: [{ x: nx, y: ny }]
            });
          }
        }
        break;
      }

      case PIECE_TYPES.ELEPHANT: {
        // 직선 1칸(제1멱) + 대각선 1칸(제2멱) 확인 후 대각선 2번째 칸 이동 (용일자)
        const elephantPatterns = [
          {
            neck1: { dx: 0, dy: -1 },
            branches: [
              { neck2: { dx: -1, dy: -2 }, target: { dx: -2, dy: -3 } },
              { neck2: { dx: 1, dy: -2 }, target: { dx: 2, dy: -3 } }
            ]
          },
          {
            neck1: { dx: 0, dy: 1 },
            branches: [
              { neck2: { dx: -1, dy: 2 }, target: { dx: -2, dy: 3 } },
              { neck2: { dx: 1, dy: 2 }, target: { dx: 2, dy: 3 } }
            ]
          },
          {
            neck1: { dx: -1, dy: 0 },
            branches: [
              { neck2: { dx: -2, dy: -1 }, target: { dx: -3, dy: -2 } },
              { neck2: { dx: -2, dy: 1 }, target: { dx: -3, dy: 2 } }
            ]
          },
          {
            neck1: { dx: 1, dy: 0 },
            branches: [
              { neck2: { dx: 2, dy: -1 }, target: { dx: 3, dy: -2 } },
              { neck2: { dx: 2, dy: 1 }, target: { dx: 3, dy: 2 } }
            ]
          }
        ];

        for (const pattern of elephantPatterns) {
          const n1x = x + pattern.neck1.dx;
          const n1y = y + pattern.neck1.dy;
          if (!isInBounds(n1x, n1y)) continue;

          if (board[n1y][n1x] !== null) {
            blockedNecks.push({
              x: n1x,
              y: n1y,
              reason: 'ELEPHANT_NECK1_BLOCKED',
              label: '상(象) 제1멱 막힘'
            });
            continue;
          }

          for (const branch of pattern.branches) {
            const n2x = x + branch.neck2.dx;
            const n2y = y + branch.neck2.dy;
            const tx = x + branch.target.dx;
            const ty = y + branch.target.dy;
            if (!isInBounds(tx, ty) || !isInBounds(n2x, n2y)) continue;

            if (board[n2y][n2x] !== null) {
              blockedNecks.push({
                x: n2x,
                y: n2y,
                reason: 'ELEPHANT_NECK2_BLOCKED',
                label: '상(象) 제2멱 막힘'
              });
              continue;
            }

            tryAddTarget(tx, ty, {
              via: [
                { x: n1x, y: n1y },
                { x: n2x, y: n2y }
              ]
            });
          }
        }
        break;
      }

      case PIECE_TYPES.SOLDIER: {
        // 초(CHU)는 위쪽(dy = -1), 한(HAN)은 아래쪽(dy = +1)으로만 전진 + 좌우 이동
        const forwardDy = side === SIDES.CHU ? -1 : 1;
        const orthoMoves = [
          { dx: 0, dy: forwardDy },
          { dx: -1, dy: 0 },
          { dx: 1, dy: 0 }
        ];

        for (const { dx, dy } of orthoMoves) {
          tryAddTarget(x + dx, y + dy, { isPalaceDiagonal: false });
        }

        // 궁성 내 전진 방향 대각선 이동 허용
        const diagNeighbors = PALACE_DIAGONAL_NEIGHBORS[`${x},${y}`];
        if (diagNeighbors) {
          for (const pt of diagNeighbors) {
            if (pt.y - y === forwardDy) {
              tryAddTarget(pt.x, pt.y, { isPalaceDiagonal: true });
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

  function getPseudoMoves(board, x, y) {
    return getPseudoMovesWithMeta(board, x, y).moves;
  }

  // ============================================================================
  // 장군(Check), 빅장(Bikjang), 자살수 방지 및 합법 착수 생성
  // ============================================================================

  /**
   * 특정 진영의 궁(KING) 위치를 찾아 반환
   */
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
   * 빅장(Bikjang) 상태 판정:
   * 두 왕(궁)이 같은 열(x)에 있고 사이에 기물이 하나도 없는 상태인지 확인
   */
  function getBikjangState(board) {
    const chuKing = findKing(board, SIDES.CHU);
    const hanKing = findKing(board, SIDES.HAN);
    if (!chuKing || !hanKing) {
      return { active: false, chuKing: null, hanKing: null };
    }
    if (chuKing.x !== hanKing.x) {
      return { active: false, chuKing, hanKing };
    }

    const col = chuKing.x;
    const minY = Math.min(chuKing.y, hanKing.y);
    const maxY = Math.max(chuKing.y, hanKing.y);

    for (let y = minY + 1; y < maxY; y++) {
      if (board[y][col] !== null) {
        return { active: false, chuKing, hanKing };
      }
    }

    return {
      active: true,
      col,
      chuKing,
      hanKing
    };
  }

  function isBikjang(board) {
    return getBikjangState(board).active;
  }

  /**
   * 특정 진영(side)의 왕이 적 기물에게 공격받고 있는지(장군 상태) 확인하고,
   * 왕을 위협하는 적 기물 및 공격 경로 목록을 반환
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

        const pseudoMoves = getPseudoMoves(board, x, y);
        for (const mv of pseudoMoves) {
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
    return getCheckStatus(board, side).inCheck;
  }

  /**
   * 가상 보드에 착수를 적용한 새 보드를 반환 (원본 보드 불변)
   */
  function simulateMoveOnBoard(board, move) {
    const nextBoard = cloneBoard(board);
    if (move.isPass) return nextBoard;

    const movingPiece = nextBoard[move.fromY][move.fromX];
    if (!movingPiece) return nextBoard;

    nextBoard[move.fromY][move.fromX] = null;
    movingPiece.x = move.toX;
    movingPiece.y = move.toY;
    movingPiece.col = move.toX;
    movingPiece.row = move.toY;
    movingPiece.moveCount = (movingPiece.moveCount || 0) + 1;
    nextBoard[move.toY][move.toX] = movingPiece;

    return nextBoard;
  }

  /**
   * 특정 좌표 기물의 합법 착수(자살수 제거 완료) 및 메타데이터 반환
   */
  function getLegalMovesForPieceWithMeta(board, x, y, options = {}) {
    const piece = isInBounds(x, y) ? board[y][x] : null;
    if (!piece) {
      return { moves: [], blockedNecks: [], bridges: [], suicidedMoves: [] };
    }

    const { moves: pseudoMoves, blockedNecks, bridges } = getPseudoMovesWithMeta(board, x, y);
    const legalMoves = [];
    const suicidedMoves = [];
    const forbidBikjang = options.bikjangRule === 'FORBID';

    for (const mv of pseudoMoves) {
      const nextBoard = simulateMoveOnBoard(board, mv);
      // 1. 내 왕이 잡히는 수(자살수)는 원천 차단
      if (isKingInCheck(nextBoard, piece.side)) {
        suicidedMoves.push(mv);
        continue;
      }
      // 2. 만약 옵션에서 빅장 금지를 강제한 경우(선택적) 차단
      if (forbidBikjang && isBikjang(nextBoard)) {
        suicidedMoves.push(mv);
        continue;
      }
      // 3. 이 수가 상대방에게 장군을 부르는 수인지, 빅장을 유발하는 수인지 태깅
      const oppSide = getOpponentSide(piece.side);
      mv.causesCheck = isKingInCheck(nextBoard, oppSide);
      mv.causesBikjang = isBikjang(nextBoard);
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

  // ============================================================================
  // 기물 점수 계산 (차13, 포7, 마5, 상3, 사3, 졸2, 한 덤 1.5점)
  // ============================================================================

  /**
   * 현재 보드의 양 진영 기물 점수 및 잔존 기물 통계 계산
   */
  function calculateScores(board) {
    let chuRaw = 0;
    let hanRaw = 0;
    const counts = {
      CHU: { KING: 0, CHARIOT: 0, CANNON: 0, HORSE: 0, ELEPHANT: 0, GUARD: 0, SOLDIER: 0 },
      HAN: { KING: 0, CHARIOT: 0, CANNON: 0, HORSE: 0, ELEPHANT: 0, GUARD: 0, SOLDIER: 0 }
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
      leader: chuTotal > hanTotal ? SIDES.CHU : SIDES.HAN,
      counts
    };
  }

  // ============================================================================
  // 대국 상태 관리 클래스 (JanggiGame)
  // ============================================================================

  class JanggiGame {
    /**
     * @param {Object} config
     * @param {string} [config.chuFormation='INNER'] - 초 상차림
     * @param {string} [config.hanFormation='INNER'] - 한 상차림
     * @param {string} [config.chuSkin='GORYEO'] - 초 국가 스킨 ID
     * @param {string} [config.hanSkin='TEMPLAR'] - 한 국가 스킨 ID
     * @param {string} [config.bikjangMode='DRAW_OR_CHOICE'] - 빅장 처리 옵션 ('DRAW_OR_CHOICE' | 'SCORE_DECISION')
     */
    constructor(config = {}) {
      this.reset(config);
    }

    reset(config = {}) {
      this.chuFormation = normalizeFormation(config.chuFormation || this.chuFormation || 'INNER');
      this.hanFormation = normalizeFormation(config.hanFormation || this.hanFormation || 'INNER');
      this.chuSkin = config.chuSkin || this.chuSkin || 'GORYEO';
      this.hanSkin = config.hanSkin || this.hanSkin || 'TEMPLAR';
      this.bikjangMode = config.bikjangMode || 'DRAW_OR_CHOICE';

      this.board = createInitialBoard(this.chuFormation, this.hanFormation);
      this.currentTurn = SIDES.CHU; // 정통 장기 규칙: 초(CHU) 선공
      this.turnCount = 1;
      this.history = [];
      this.capturedPieces = {
        CHU: [], // 초가 잡은 한의 기물들 (또는 한이 잃은 기물)
        HAN: []  // 한이 잡은 초의 기물들
      };
      this.lostPieces = {
        CHU: [], // 초가 잃은 기물들
        HAN: []  // 한이 잃은 기물들
      };

      this.inCheck = false;
      this.lastEvent = null; // 'CHECK'(장군), 'MEONGGUN'(멍군), 'BIKJANG'(빅장), 'CHECKMATE'(외통수), 'PASS'(한수쉼)
      this.checkAttackers = [];
      this.bikjangState = { active: false };
      this.consecutivePasses = 0;

      this.isGameOver = false;
      this.winner = null; // 'CHU' | 'HAN' | 'DRAW'
      this.winReason = null; // 'CHECKMATE' | 'STALEMATE' | 'BIKJANG_DRAW' | 'SCORE_DECISION' | 'RESIGN'
      this.scores = calculateScores(this.board);

      return this.getState();
    }

    /**
     * 현재 보드에서 특정 좌표의 기물 조회
     */
    getPieceAt(x, y) {
      if (!isInBounds(x, y)) return null;
      return this.board[y][x];
    }

    /**
     * 특정 좌표 기물의 합법 착수 및 멱/다리 메타데이터 조회
     */
    getLegalMovesAt(x, y) {
      if (this.isGameOver) {
        return { moves: [], blockedNecks: [], bridges: [], suicidedMoves: [] };
      }
      const piece = this.getPieceAt(x, y);
      if (!piece || piece.side !== this.currentTurn) {
        return { moves: [], blockedNecks: [], bridges: [], suicidedMoves: [] };
      }
      return getLegalMovesForPieceWithMeta(this.board, x, y);
    }

    /**
     * 현재 턴 진영의 전체 합법 착수 목록 반환
     */
    getAllLegalMovesForCurrentTurn() {
      if (this.isGameOver) return [];
      return getAllLegalMoves(this.board, this.currentTurn);
    }

    /**
     * 내부 스냅샷 저장 (무르기 Undo 용)
     */
    _createSnapshot(moveRecord) {
      return {
        board: cloneBoard(this.board),
        currentTurn: this.currentTurn,
        turnCount: this.turnCount,
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
     * @returns {Object} 착수 결과 객체 { ok, move, event, inCheck, isMeonggun, isBikjang, isGameOver, winner, winReason, scores }
     */
    makeMove(fromX, fromY, toX, toY) {
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

      const { moves: legalMoves } = getLegalMovesForPieceWithMeta(this.board, fromX, fromY);
      const matchedMove = legalMoves.find((m) => m.toX === toX && m.toY === toY);

      if (!matchedMove) {
        return { ok: false, error: '규칙에 어긋나는 착수이거나 왕이 위험해지는 자살수입니다.' };
      }

      // 이전 턴에 내 왕이 장군 상태였는지 기록 (멍군 판정용)
      const wasInCheck = this.inCheck;
      const moverSide = this.currentTurn;
      const nextSide = getOpponentSide(moverSide);

      // 히스토리 스냅샷 저장
      this.history.push(this._createSnapshot(matchedMove));

      // 보드 상태 업데이트
      const targetPiece = this.board[toY][toX];
      if (targetPiece) {
        this.capturedPieces[moverSide].push(clonePiece(targetPiece));
        this.lostPieces[targetPiece.side].push(clonePiece(targetPiece));
      }

      this.board[fromY][fromX] = null;
      piece.x = toX;
      piece.y = toY;
      piece.col = toX;
      piece.row = toY;
      piece.moveCount = (piece.moveCount || 0) + 1;
      this.board[toY][toX] = piece;

      this.consecutivePasses = 0;
      this.currentTurn = nextSide;
      this.turnCount++;

      // 점수 재계산
      this.scores = calculateScores(this.board);

      // 장군 / 멍군 / 빅장 / 외통수 판정
      const checkInfo = getCheckStatus(this.board, nextSide);
      this.inCheck = checkInfo.inCheck;
      this.checkAttackers = checkInfo.attackers;
      this.bikjangState = getBikjangState(this.board);

      const isMeonggun = wasInCheck && !isKingInCheck(this.board, moverSide);

      // 다음 턴 플레이어의 합법 착수 확인
      const nextLegalMoves = getAllLegalMoves(this.board, nextSide);

      let eventType = 'MOVE';
      if (matchedMove.isCapture) {
        eventType = 'CAPTURE';
      }

      if (nextLegalMoves.length === 0) {
        // 합법 수가 하나도 없는 경우 -> 외통수(Checkmate) 또는 초완봉(Stalemate)
        this.isGameOver = true;
        this.winner = moverSide;
        this.winReason = this.inCheck ? 'CHECKMATE' : 'STALEMATE';
        this.lastEvent = this.inCheck ? 'CHECKMATE' : 'STALEMATE';
        eventType = this.lastEvent;
      } else if (this.inCheck) {
        this.lastEvent = 'CHECK';
        eventType = 'CHECK';
      } else if (this.bikjangState.active) {
        this.lastEvent = 'BIKJANG';
        eventType = 'BIKJANG';
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
        isBikjang: this.bikjangState.active,
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
     * 한수 쉼 (Pass Turn)
     * - 정통 장기 규칙상 내 왕이 장군(Check) 상태일 때는 한수 쉼을 할 수 없음.
     * - 빅장 상태에서 한수 쉼을 선택하면 빅장 수용(무승부 또는 점수 판정)으로 처리 가능.
     * - 양측이 연속으로 한수 쉼(2연속 Pass)을 하면 대국 종료(기물 점수 판정 승리).
     */
    passTurn() {
      if (this.isGameOver) {
        return { ok: false, error: '이미 종료된 대국입니다.' };
      }
      if (this.inCheck) {
        return { ok: false, error: '장군(Check) 상태에서는 한수 쉼을 할 수 없습니다! 왕을 보호하세요.' };
      }

      const moverSide = this.currentTurn;
      const nextSide = getOpponentSide(moverSide);
      const kingPos = findKing(this.board, moverSide);

      const passMove = createMoveObject(
        kingPos ? kingPos.x : 4,
        kingPos ? kingPos.y : (moverSide === SIDES.CHU ? 8 : 1),
        kingPos ? kingPos.x : 4,
        kingPos ? kingPos.y : (moverSide === SIDES.CHU ? 8 : 1),
        kingPos ? kingPos.piece : createPiece('PASS', moverSide, PIECE_TYPES.KING, 4, 4),
        null,
        { isPass: true }
      );
      passMove.notation = `${moverSide === SIDES.CHU ? '초' : '한'}: 한수 쉼 (Pass)`;

      this.history.push(this._createSnapshot(passMove));

      this.consecutivePasses++;
      this.currentTurn = nextSide;
      this.turnCount++;
      this.lastEvent = 'PASS';

      // 빅장 상태에서 상대가 피하지 않고 한수 쉼을 한 경우 -> 빅장 성립
      if (this.bikjangState.active) {
        return this.resolveBikjang('BIKJANG_DRAW');
      }

      // 양 진영이 연속으로 한수 쉼을 한 경우 -> 점수 판정 종료
      if (this.consecutivePasses >= 2) {
        this.isGameOver = true;
        this.scores = calculateScores(this.board);
        this.winner = this.scores.leader; // 1.5점 덤이 있으므로 반드시 승자 결정
        this.winReason = 'SCORE_DECISION';
        this.lastEvent = 'SCORE_DECISION';
      }

      return {
        ok: true,
        move: passMove,
        event: this.lastEvent,
        inCheck: this.inCheck,
        isBikjang: this.bikjangState.active,
        isGameOver: this.isGameOver,
        winner: this.winner,
        winReason: this.winReason,
        scores: this.scores,
        currentTurn: this.currentTurn,
        turnCount: this.turnCount
      };
    }

    /**
     * 빅장(Bikjang) 선언 처리:
     * 두 왕이 마주보고 있을 때 무승부(빅) 또는 점수 판정으로 대국을 종료
     * @param {'BIKJANG_DRAW'|'SCORE_DECISION'} [resolution='BIKJANG_DRAW']
     */
    resolveBikjang(resolution = 'BIKJANG_DRAW') {
      const bj = getBikjangState(this.board);
      if (!bj.active) {
        return { ok: false, error: '현재 빅장(왕끼리 마주보는 상태) 조건이 아닙니다.' };
      }

      this.isGameOver = true;
      this.scores = calculateScores(this.board);

      if (resolution === 'SCORE_DECISION') {
        this.winner = this.scores.leader;
        this.winReason = 'SCORE_DECISION';
        this.lastEvent = 'SCORE_DECISION';
      } else {
        this.winner = 'DRAW';
        this.winReason = 'BIKJANG_DRAW';
        this.lastEvent = 'BIKJANG_DRAW';
      }

      return {
        ok: true,
        event: this.lastEvent,
        isBikjang: true,
        isGameOver: true,
        winner: this.winner,
        winReason: this.winReason,
        scores: this.scores
      };
    }

    /**
     * 점수 판정 종료 요청 (기물 점수제로 즉시 우열 판정)
     */
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

    /**
     * 기권(Resign) 처리
     */
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
     * @param {number} [steps=1] - 되돌릴 수(1P vs AI 모드에서는 2수 되돌리기 지원)
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
        this.currentTurn = snapshot.currentTurn;
        this.turnCount = snapshot.turnCount;
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
     * 한국 장기 기보 표기 생성 (예: "초 마 (2,10) → (3,8) 포획:병 [장군!]")
     */
    formatMoveNotation(move, eventType) {
      if (move.isPass) {
        return `${move.piece.side === SIDES.CHU ? '초' : '한'}: 한수 쉼`;
      }
      const sideLabel = move.piece.side === SIDES.CHU ? '초' : '한';
      const pieceLabel = `${move.piece.kr}(${move.piece.hanja})`;
      const fromCoord = `${move.fromX + 1}${10 - move.fromY}`;
      const toCoord = `${move.toX + 1}${10 - move.toY}`;
      const capText = move.captured ? ` × ${move.captured.kr}(${move.captured.hanja})` : '';
      let suffix = '';
      if (eventType === 'CHECKMATE') suffix = ' [외통수!]';
      else if (eventType === 'CHECK') suffix = ' [장군!]';
      else if (eventType === 'MEONGGUN') suffix = ' [멍군!]';
      else if (eventType === 'BIKJANG') suffix = ' [빅장!]';

      return `${sideLabel} ${pieceLabel} ${fromCoord}→${toCoord}${capText}${suffix}`;
    }

    /**
     * 현재 대국의 직렬화 가능한 상태 객체 반환
     */
    getState() {
      return {
        board: cloneBoard(this.board),
        currentTurn: this.currentTurn,
        turnCount: this.turnCount,
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
  // 모듈 내보내기 (window.JanggiEngine)
  // ============================================================================

  const JanggiEngine = {
    BOARD_COLS,
    BOARD_ROWS,
    SIDES,
    PIECE_TYPES,
    PIECE_SCORES,
    HAN_KOMI,
    PIECE_LABELS,
    FORMATIONS,
    PALACE_BOUNDS,
    PALACE_DIAGONAL_NEIGHBORS,
    PALACE_DIAGONAL_RAYS,

    // 유틸리티 & 정적 규칙 함수 (AI 엔진 및 UI에서 직접 호출 가능)
    isInBounds,
    isInPalace,
    getOpponentSide,
    normalizeFormation,
    createPiece,
    clonePiece,
    cloneBoard,
    createInitialBoard,
    getPseudoMoves,
    getPseudoMovesWithMeta,
    findKing,
    getBikjangState,
    isBikjang,
    getCheckStatus,
    isKingInCheck,
    simulateMoveOnBoard,
    getLegalMovesForPiece,
    getLegalMovesForPieceWithMeta,
    getAllLegalMoves,
    calculateScores,

    // 대국 관리 클래스 및 팩토리
    JanggiGame,
    createGame: (config) => new JanggiGame(config)
  };

  global.JanggiEngine = JanggiEngine;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = JanggiEngine;
  }
})(typeof window !== 'undefined' ? window : globalThis);
