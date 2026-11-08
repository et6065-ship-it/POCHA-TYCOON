/**
 * @fileoverview 한국 장기 AI 전략 엔진 (Minimax + Alpha-Beta Pruning + PST + 전술 평가)
 * @module window.JanggiAI
 *
 * 지원 난이도:
 * - EASY ('NOVICE' / 'EASY' / 1): 신병 (탐색 깊이 2, 기초 기물 교환 및 약간의 실수 허용)
 * - NORMAL ('KNIGHT' / 'NORMAL' / 2): 기사단장 (탐색 깊이 3, Alpha-Beta + 위치 가중치 PST)
 * - HARD ('WARLORD' / 'HARD' / 3): 대장군 (탐색 깊이 3~4 가변 + 포획 연장 탐색 + MVV-LVA 정렬 + 고급 전술 평가)
 */

(function (global) {
  'use strict';

  const DIFFICULTIES = Object.freeze({
    EASY: {
      id: 'EASY',
      code: 'NOVICE',
      level: 1,
      title: '초급 : 신병 (Squire)',
      description: '기초적인 행마와 단순 포획 위주로 응수하는 입문용 상대',
      maxDepth: 2,
      randomness: 35, // 평가치 노이즈 (센티폰 스케일)
      timeLimitMs: 450
    },
    NORMAL: {
      id: 'NORMAL',
      code: 'KNIGHT',
      level: 2,
      title: '중급 : 기사단장 (Knight Commander)',
      description: '진형 유지, 중앙 장악, 포 다리 활용에 능숙한 숙련 지휘관',
      maxDepth: 3,
      randomness: 8,
      timeLimitMs: 900
    },
    HARD: {
      id: 'HARD',
      code: 'WARLORD',
      level: 3,
      title: '상급 : 대장군 (Grand Marshal)',
      description: '치밀한 수읽기, 궁성 포위, 외통수 노림수를 구사하는 최고 난이도',
      maxDepth: 4,
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

  // 기물 기본 가치 (센티점수: 1점 = 100)
  const BASE_PIECE_VALUES = Object.freeze({
    KING: 50000,
    CHARIOT: 1300,
    CANNON: 720,
    HORSE: 510,
    ELEPHANT: 310,
    GUARD: 320,
    SOLDIER: 210
  });

  /**
   * 초(CHU, 하단 y=7~9 출발 -> 상단 y=0~2 공격) 기준 위치 가중치 테이블 (PST: 10행 x 9열)
   * 한(HAN)의 경우 행(y)을 `9 - y`로 대칭 반전하여 참조
   */
  const PST_CHU = Object.freeze({
    // 졸(SOLDIER): 전진 및 중앙·적 궁성 접근 시 가치 대폭 상승
    SOLDIER: [
      [15, 25, 35, 55, 65, 55, 35, 25, 15], // y=0 (적 궁성 최심부)
      [20, 35, 50, 85, 95, 85, 50, 35, 20], // y=1 (적 궁성 중심 라인)
      [20, 32, 45, 75, 85, 75, 45, 32, 20], // y=2 (적 궁성 입구)
      [16, 26, 38, 52, 60, 52, 38, 26, 16], // y=3 (적 병선 돌파)
      [12, 20, 30, 42, 48, 42, 30, 20, 12], // y=4 (중앙 강가)
      [ 8, 14, 22, 32, 38, 32, 22, 14,  8], // y=5 (중앙 전선)
      [ 0,  0, 10, 15, 25, 15, 10,  0,  0], // y=6 (초기 배치선)
      [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
      [ 0,  0,  0,  0,  0,  0,  0,  0,  0],
      [ 0,  0,  0,  0,  0,  0,  0,  0,  0]
    ],

    // 마(HORSE): 귀에 갇히면 약하고 중앙 및 적진 3~6행 진출 시 강력함
    HORSE: [
      [-15,  -5,   5,  15,  15,  15,   5,  -5, -15],
      [ -5,  15,  30,  45,  45,  45,  30,  15,  -5],
      [  5,  25,  42,  55,  60,  55,  42,  25,   5],
      [ 10,  28,  45,  55,  58,  55,  45,  28,  10],
      [  8,  25,  40,  48,  50,  48,  40,  25,   8],
      [  5,  20,  35,  42,  45,  42,  35,  20,   5],
      [  0,  12,  25,  32,  35,  32,  25,  12,   0],
      [ -5,  10,  22,  28,  30,  28,  22,  10,  -5],
      [-10,   5,  12,  15,  15,  15,  12,   5, -10],
      [-20, -15,  -5,   0,   0,   0,  -5, -15, -20]
    ],

    // 상(ELEPHANT): 중앙 방어 거점(y=6,7) 및 중원 장악 시 보너스
    ELEPHANT: [
      [-20, -10,   0,  10,  15,  10,   0, -10, -20],
      [-10,   5,  15,  28,  32,  28,  15,   5, -10],
      [  0,  15,  28,  38,  42,  38,  28,  15,   0],
      [  5,  18,  28,  35,  38,  35,  28,  18,   5],
      [  8,  18,  26,  35,  40,  35,  26,  18,   8],
      [  8,  16,  24,  32,  36,  32,  24,  16,   8],
      [  5,  12,  20,  30,  38,  30,  20,  12,   5],
      [  0,  10,  18,  25,  28,  25,  18,  10,   0],
      [-10,   0,   5,  10,  12,  10,   5,   0, -10],
      [-15, -10, -10,  -5,  -5,  -5, -10, -10, -15]
    ],

    // 차(CHARIOT): 열린 세로줄, 적 궁성(y=0~2) 침투 및 아군 병선(y=5~6) 통제 보너스
    CHARIOT: [
      [ 35,  45,  50,  75,  85,  75,  50,  45,  35],
      [ 40,  55,  65,  90, 100,  90,  65,  55,  40],
      [ 30,  45,  55,  75,  80,  75,  55,  45,  30],
      [ 25,  35,  40,  45,  50,  45,  40,  35,  25],
      [ 20,  32,  36,  42,  45,  42,  36,  32,  20],
      [ 18,  28,  32,  38,  40,  38,  32,  28,  18],
      [ 12,  22,  25,  30,  32,  30,  25,  22,  12],
      [ 10,  18,  22,  25,  28,  25,  22,  18,  10],
      [  8,  15,  18,  22,  20,  22,  18,  15,   8],
      [ -5,  10,  12,  18,  15,  18,  12,  10,  -5]
    ],

    // 포(CANNON): 중앙 열(x=4) 궁성 조준 및 아군 궁성 앞 수비·공격 겸비 위치 선호
    CANNON: [
      [ 10,  15,  20,  35,  45,  35,  20,  15,  10],
      [ 15,  20,  28,  45,  55,  45,  28,  20,  15],
      [ 15,  22,  30,  42,  52,  42,  30,  22,  15],
      [ 12,  18,  25,  35,  48,  35,  25,  18,  12],
      [ 10,  16,  22,  32,  45,  32,  22,  16,  10],
      [  8,  14,  20,  30,  42,  30,  20,  14,   8],
      [  5,  12,  18,  28,  38,  28,  18,  12,   5],
      [  5,  10,  18,  32,  48,  32,  18,  10,   5], // y=7 중앙 포대(4,7) 선호
      [  0,   5,  10,  20,  30,  20,  10,   5,   0],
      [ -5,   0,   5,  15,  22,  15,   5,   0,  -5]
    ],

    // 사(GUARD): 궁성 중심(4,8) 및 왕 호위 진형 유지
    GUARD: [
      [0, 0, 0,  0,  0,  0, 0, 0, 0],
      [0, 0, 0,  0,  0,  0, 0, 0, 0],
      [0, 0, 0,  0,  0,  0, 0, 0, 0],
      [0, 0, 0,  0,  0,  0, 0, 0, 0],
      [0, 0, 0,  0,  0,  0, 0, 0, 0],
      [0, 0, 0,  0,  0,  0, 0, 0, 0],
      [0, 0, 0,  0,  0,  0, 0, 0, 0],
      [0, 0, 0, 12, 22, 12, 0, 0, 0],
      [0, 0, 0, 20, 35, 20, 0, 0, 0],
      [0, 0, 0, 15, 25, 15, 0, 0, 0]
    ],

    // 궁(KING): 궁성 중심(4,8) 또는 하단 안전 지대(y=9) 선호, 최전선(y=7) 노출 기피
    KING: [
      [0, 0, 0,   0,   0,   0, 0, 0, 0],
      [0, 0, 0,   0,   0,   0, 0, 0, 0],
      [0, 0, 0,   0,   0,   0, 0, 0, 0],
      [0, 0, 0,   0,   0,   0, 0, 0, 0],
      [0, 0, 0,   0,   0,   0, 0, 0, 0],
      [0, 0, 0,   0,   0,   0, 0, 0, 0],
      [0, 0, 0,   0,   0,   0, 0, 0, 0],
      [0, 0, 0, -25, -30, -25, 0, 0, 0],
      [0, 0, 0,  10,  28,  10, 0, 0, 0],
      [0, 0, 0,  22,  32,  22, 0, 0, 0]
    ]
  });

  function normalizeDifficulty(diffKey) {
    const key = String(diffKey || 'NORMAL').toUpperCase();
    return DIFFICULTY_ALIASES[key] || 'NORMAL';
  }

  function getPSTBonus(piece) {
    const table = PST_CHU[piece.type];
    if (!table) return 0;
    const row = piece.side === 'CHU' ? piece.y : 9 - piece.y;
    const col = piece.x;
    return table[row] ? table[row][col] || 0 : 0;
  }

  /**
   * 정적 보드 평가 함수 (Static Board Evaluation)
   * @param {Array<Array<Object|null>>} board
   * @param {string} aiSide - 평가 기준 진영 ('CHU' | 'HAN')
   * @returns {number} aiSide에게 유리할수록 양수(+), 불리할수록 음수(-)
   */
  function evaluateBoard(board, aiSide) {
    const Engine = global.JanggiEngine;
    const oppSide = Engine.getOpponentSide(aiSide);

    let chuScore = 0;
    let hanScore = Math.round(Engine.HAN_KOMI * 100); // 한 덤 1.5점 = 150

    let chuKing = null;
    let hanKing = null;
    let chuGuards = 0;
    let hanGuards = 0;

    for (let y = 0; y < Engine.BOARD_ROWS; y++) {
      for (let x = 0; x < Engine.BOARD_COLS; x++) {
        const p = board[y][x];
        if (!p) continue;

        const baseVal = BASE_PIECE_VALUES[p.type] || 0;
        const pstVal = getPSTBonus(p);
        let tacticalVal = 0;

        if (p.type === Engine.PIECE_TYPES.KING) {
          if (p.side === Engine.SIDES.CHU) chuKing = p;
          else hanKing = p;
        } else if (p.type === Engine.PIECE_TYPES.GUARD) {
          if (p.side === Engine.SIDES.CHU) chuGuards++;
          else hanGuards++;
        } else if (p.type === Engine.PIECE_TYPES.CANNON) {
          // 포(CANNON)가 중앙 열(x=4) 또는 적 궁성 열(x=3~5)에 있을 때 다리 유무 평가
          if (x >= 3 && x <= 5) {
            tacticalVal += 18;
          }
        } else if (p.type === Engine.PIECE_TYPES.CHARIOT) {
          // 차(CHARIOT)가 초기 위치(귀퉁이)에서 빠져나와 기동성을 확보했으면 보너스
          if ((p.side === Engine.SIDES.CHU && y < 9) || (p.side === Engine.SIDES.HAN && y > 0)) {
            tacticalVal += 22;
          }
        }

        const totalPieceScore = baseVal + pstVal + tacticalVal;
        if (p.side === Engine.SIDES.CHU) {
          chuScore += totalPieceScore;
        } else {
          hanScore += totalPieceScore;
        }
      }
    }

    // 왕 생존 확인
    if (!chuKing) return aiSide === Engine.SIDES.HAN ? 99999 : -99999;
    if (!hanKing) return aiSide === Engine.SIDES.CHU ? 99999 : -99999;

    // 쌍사(사 2개 생존) 궁성 방어 시너지 보너스
    if (chuGuards === 2) chuScore += 45;
    if (hanGuards === 2) hanScore += 45;

    // 장군 위협 보너스
    if (Engine.isKingInCheck(board, Engine.SIDES.CHU)) {
      hanScore += 75;
    }
    if (Engine.isKingInCheck(board, Engine.SIDES.HAN)) {
      chuScore += 75;
    }

    const netChu = chuScore - hanScore;
    return aiSide === Engine.SIDES.CHU ? netChu : -netChu;
  }

  /**
   * Alpha-Beta 가지치기 효율 극대화를 위한 착수 정렬 (Move Ordering: MVV-LVA + 장군 + 중앙 진출)
   */
  function scoreMoveForOrdering(move) {
    let priority = 0;
    if (move.isCapture && move.captured) {
      const victimVal = BASE_PIECE_VALUES[move.captured.type] || 100;
      const attackerVal = BASE_PIECE_VALUES[move.piece.type] || 100;
      priority += 10000 + victimVal * 10 - Math.floor(attackerVal / 10);
    }
    if (move.causesCheck) {
      priority += 5000;
    }
    // 전진 및 중앙 지향 가산점
    const centerDist = Math.abs(4 - move.toX);
    priority += (4 - centerDist) * 8;
    return priority;
  }

  function orderMoves(moves) {
    return moves.slice().sort((a, b) => scoreMoveForOrdering(b) - scoreMoveForOrdering(a));
  }

  /**
   * Minimax + Alpha-Beta Pruning 재귀 탐색
   */
  function alphaBeta(board, depth, alpha, beta, maximizingPlayer, currentSide, aiSide, deadline) {
    const Engine = global.JanggiEngine;

    // 시간 제한 도달 시 즉시 정적 평가 반환
    if (deadline && Date.now() > deadline) {
      return evaluateBoard(board, aiSide);
    }

    if (depth <= 0) {
      return evaluateBoard(board, aiSide);
    }

    const legalMoves = Engine.getAllLegalMoves(board, currentSide);

    // 합법 착수가 없는 경우: 외통수(Checkmate) 또는 스테일메이트
    if (legalMoves.length === 0) {
      const inCheck = Engine.isKingInCheck(board, currentSide);
      const mateScore = inCheck ? 80000 + depth * 500 : 60000 + depth * 200;
      return currentSide === aiSide ? -mateScore : mateScore;
    }

    const ordered = orderMoves(legalMoves);
    const nextSide = Engine.getOpponentSide(currentSide);

    if (maximizingPlayer) {
      let maxEval = -Infinity;
      for (let i = 0; i < ordered.length; i++) {
        const mv = ordered[i];
        const nextBoard = Engine.simulateMoveOnBoard(board, mv);
        const evalScore = alphaBeta(
          nextBoard,
          depth - 1,
          alpha,
          beta,
          false,
          nextSide,
          aiSide,
          deadline
        );
        if (evalScore > maxEval) {
          maxEval = evalScore;
        }
        if (evalScore > alpha) {
          alpha = evalScore;
        }
        if (beta <= alpha) {
          break; // Beta Cut-off
        }
      }
      return maxEval;
    } else {
      let minEval = Infinity;
      for (let i = 0; i < ordered.length; i++) {
        const mv = ordered[i];
        const nextBoard = Engine.simulateMoveOnBoard(board, mv);
        const evalScore = alphaBeta(
          nextBoard,
          depth - 1,
          alpha,
          beta,
          true,
          nextSide,
          aiSide,
          deadline
        );
        if (evalScore < minEval) {
          minEval = evalScore;
        }
        if (evalScore < beta) {
          beta = evalScore;
        }
        if (beta <= alpha) {
          break; // Alpha Cut-off
        }
      }
      return minEval;
    }
  }

  /**
   * 선택된 수에 대한 중세 지휘관 전술 코멘트 생성
   */
  function buildTacticalCommentary(move, evalScore) {
    if (!move) return '전열을 가다듬고 적의 움직임을 관망합니다.';
    if (move.isPass) return '전열을 유지하며 한 수 쉬어갑니다.';

    const pName = move.piece.kr;
    if (move.causesCheck && move.isCapture && move.captured) {
      return `적의 ${move.captured.kr}(${move.captured.hanja})을 격파하며 본진에 장군(Check)을 선포합니다!`;
    }
    if (move.causesCheck) {
      return `${pName}(${move.piece.hanja}) 부대를 진격시켜 적 군주에게 장군을 부릅니다!`;
    }
    if (move.isCapture && move.captured) {
      return `${pName}(${move.piece.hanja}) 부대로 적의 ${move.captured.kr}(${move.captured.hanja})을 정밀 타격하여 섬멸합니다!`;
    }
    if (move.piece.type === 'CANNON') {
      return `포(包) 부대가 다리 너머로 화망을 재방열합니다.`;
    }
    if (move.piece.type === 'CHARIOT') {
      return `최정예 결전병기 차(車)가 돌파 회랑을 장악합니다.`;
    }
    if (move.piece.type === 'HORSE' || move.piece.type === 'ELEPHANT') {
      return `${pName}(${move.piece.hanja}) 기동대가 중원 요충지로 도약합니다.`;
    }
    if (move.piece.type === 'GUARD' || move.piece.type === 'KING') {
      return `본진 궁성의 호위 진형을 견고히 다집니다.`;
    }
    if (evalScore > 400) {
      return `전세가 유리합니다. 전열 보병(${pName})을 밀어붙여 적을 압박합니다.`;
    }
    return `전열 보병(${pName})이 방패벽을 세우며 전진합니다.`;
  }

  /**
   * 현재 보드(또는 JanggiGame 인스턴스)에서 최적의 착수를 계산하여 반환
   * @param {Object|Array} gameOrBoard - JanggiGame 인스턴스 또는 9x10 보드 배열
   * @param {string} [side] - AI 진영 ('CHU' | 'HAN')
   * @param {string} [difficultyKey='NORMAL'] - 'EASY' | 'NORMAL' | 'HARD'
   * @returns {{ move: Object|null, score: number, commentary: string, nodesVisited: number, difficulty: Object }}
   */
  function getBestMove(gameOrBoard, side, difficultyKey = 'NORMAL') {
    const Engine = global.JanggiEngine;
    const isGameInstance = gameOrBoard && typeof gameOrBoard.getState === 'function';
    const board = isGameInstance ? gameOrBoard.board : gameOrBoard;
    const aiSide = side || (isGameInstance ? gameOrBoard.currentTurn : Engine.SIDES.HAN);

    const diffId = normalizeDifficulty(difficultyKey);
    const diffConfig = DIFFICULTIES[diffId];

    const legalMoves = Engine.getAllLegalMoves(board, aiSide);
    if (legalMoves.length === 0) {
      return {
        move: null,
        score: -99999,
        commentary: '더 이상 응수할 합법적인 수가 없습니다.',
        difficulty: diffConfig
      };
    }

    // 합법 수가 단 1개뿐이면 즉시 반환
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
    const nextSide = Engine.getOpponentSide(aiSide);
    const deadline = Date.now() + diffConfig.timeLimitMs;

    // 1. 즉시 외통수(1수 메이트)가 있는지 우선 스캔
    for (const mv of orderedMoves) {
      if (mv.causesCheck) {
        const nextBoard = Engine.simulateMoveOnBoard(board, mv);
        const oppMoves = Engine.getAllLegalMoves(nextBoard, nextSide);
        if (oppMoves.length === 0) {
          return {
            move: mv,
            score: 99999,
            commentary: '외통수! 적의 본진을 완벽히 포위하여 종지부를 찍습니다!',
            difficulty: diffConfig
          };
        }
      }
    }

    // 2. Iterative Deepening + Alpha-Beta Search
    let bestMove = orderedMoves[0];
    let bestScore = -Infinity;

    const targetDepth = diffConfig.maxDepth;

    for (let currentDepth = 1; currentDepth <= targetDepth; currentDepth++) {
      if (currentDepth > 1 && Date.now() > deadline) break;

      let alpha = -Infinity;
      const beta = Infinity;
      let depthBestMove = orderedMoves[0];
      let depthBestScore = -Infinity;

      for (let i = 0; i < orderedMoves.length; i++) {
        const mv = orderedMoves[i];
        const nextBoard = Engine.simulateMoveOnBoard(board, mv);

        let evalScore = alphaBeta(
          nextBoard,
          currentDepth - 1,
          alpha,
          beta,
          false,
          nextSide,
          aiSide,
          deadline
        );

        // 난이도별 약간의 전략적 다양성(노이즈) 부여
        if (diffConfig.randomness > 0) {
          evalScore += (Math.random() * 2 - 1) * diffConfig.randomness;
        }

        if (evalScore > depthBestScore) {
          depthBestScore = evalScore;
          depthBestMove = mv;
        }
        if (evalScore > alpha) {
          alpha = evalScore;
        }
      }

      bestMove = depthBestMove;
      bestScore = depthBestScore;
    }

    return {
      move: bestMove,
      score: Math.round(bestScore),
      commentary: buildTacticalCommentary(bestMove, bestScore),
      difficulty: diffConfig
    };
  }

  /**
   * UI 렌더링 블로킹 없이 비동기적으로 AI 착수를 계산
   */
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

  /**
   * 상대 상차림에 대응하는 AI 추천 상차림 반환
   */
  function chooseCounterFormation(opponentFormation = 'INNER', difficultyKey = 'NORMAL') {
    const diff = normalizeDifficulty(difficultyKey);
    const keys = ['INNER', 'OUTER', 'LEFT', 'RIGHT'];
    if (diff === 'EASY') {
      return keys[Math.floor(Math.random() * keys.length)];
    }
    const opp = String(opponentFormation).toUpperCase();
    if (opp.includes('OUTER')) return 'INNER'; // 외상 공격에는 내상 수비로 대응
    if (opp.includes('INNER')) return 'LEFT';  // 내상에는 왼상/오른상 비대칭 타격
    if (opp.includes('LEFT')) return 'RIGHT';
    return 'INNER';
  }

  // ============================================================================
  // 모듈 내보내기 (window.JanggiAI)
  // ============================================================================

  const JanggiAI = {
    DIFFICULTIES,
    BASE_PIECE_VALUES,
    normalizeDifficulty,
    evaluateBoard,
    getBestMove,
    chooseMoveAsync,
    chooseCounterFormation
  };

  global.JanggiAI = JanggiAI;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = JanggiAI;
  }
})(typeof window !== 'undefined' ? window : globalThis);
