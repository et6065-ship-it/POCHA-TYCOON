(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;
  if (!root.TycoonEngine || typeof root.TycoonEngine.registerCartridge !== "function") {
    throw new Error("TycoonEngine must load before bungeo_theme.js");
  }

  function roundRectPath(ctx, x, y, w, h, r) {
    var rad = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + rad, y);
    ctx.arcTo(x + w, y, x + w, y + h, rad);
    ctx.arcTo(x + w, y + h, x, y + h, rad);
    ctx.arcTo(x, y + h, x, y, rad);
    ctx.arcTo(x, y, x + w, y, rad);
    ctx.closePath();
  }

  function drawFishSilhouette(ctx, cx, cy, rx, ry, fillStyle, strokeStyle) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.beginPath();
    ctx.ellipse(-rx * 0.14, 0, rx * 0.68, ry * 0.72, 0, 0, Math.PI * 2);
    ctx.moveTo(rx * 0.42, 0);
    ctx.lineTo(rx * 0.88, -ry * 0.56);
    ctx.lineTo(rx * 0.82, 0);
    ctx.lineTo(rx * 0.88, ry * 0.56);
    ctx.closePath();
    if (fillStyle) {
      ctx.fillStyle = fillStyle;
      ctx.fill();
    }
    if (strokeStyle) {
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
    ctx.restore();
  }

  function computeLayout(canvasW, canvasH, appliance, compactMode) {
    var cols = appliance.cols;
    var rows = appliance.rows;
    var outerPadX = 8;
    var outerPadY = compactMode ? 5 : 8;
    var lidRect = null;
    var bodyY = outerPadY;

    if (!compactMode) {
      var lidH = Math.min(38, Math.max(24, Math.round(canvasH * 0.16)));
      lidRect = {
        x: outerPadX,
        y: outerPadY,
        w: Math.max(40, canvasW - outerPadX * 2),
        h: lidH
      };
      bodyY = outerPadY + lidH + 6;
    }

    var frameRect = {
      x: outerPadX,
      y: bodyY,
      w: Math.max(60, canvasW - outerPadX * 2),
      h: Math.max(60, canvasH - bodyY - outerPadY)
    };

    var innerPadX = 8;
    var innerPadY = compactMode ? 5 : 7;
    var gapX = 6;
    var gapY = compactMode ? 5 : 6;

    var gridW = Math.max(30, frameRect.w - innerPadX * 2 - gapX * (cols - 1));
    var gridH = Math.max(30, frameRect.h - innerPadY * 2 - gapY * (rows - 1));
    var slotW = gridW / cols;
    var slotH = gridH / rows;

    var slotRects = [];
    var idx = 0;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        if (idx >= appliance.slots) break;
        slotRects.push({
          index: idx,
          col: c,
          row: r,
          x: frameRect.x + innerPadX + c * (slotW + gapX),
          y: frameRect.y + innerPadY + r * (slotH + gapY),
          w: slotW,
          h: slotH
        });
        idx++;
      }
    }

    return {
      frameRect: frameRect,
      lidRect: lidRect,
      slotRects: slotRects
    };
  }

  function drawAppliance(ctx, layout, appliance, renderContext) {
    var rc = renderContext || {};
    var fr = layout.frameRect;

    if (layout.lidRect) {
      var lr = layout.lidRect;
      roundRectPath(ctx, lr.x, lr.y, lr.w, lr.h, 8);
      ctx.fillStyle = "#1f2937";
      ctx.fill();
      ctx.strokeStyle = "#475569";
      ctx.lineWidth = 2;
      ctx.stroke();

      var hingeCount = Math.max(2, appliance.cols);
      for (var h = 0; h < hingeCount; h++) {
        var hx = lr.x + ((h + 0.5) * lr.w) / hingeCount - 10;
        ctx.fillStyle = "#64748b";
        ctx.fillRect(hx, lr.y + lr.h - 4, 20, 8);
      }

      ctx.fillStyle = "#94a3b8";
      ctx.font = "bold 11px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(appliance.name, lr.x + lr.w / 2, lr.y + lr.h / 2);
    }

    roundRectPath(ctx, fr.x, fr.y, fr.w, fr.h, 10);
    ctx.fillStyle = rc.feverActive ? "#291d09" : "#18202c";
    ctx.fill();
    ctx.strokeStyle = rc.feverActive ? "#facc15" : "#475569";
    ctx.lineWidth = rc.feverActive ? 2.5 : 2;
    ctx.stroke();

    if (rc.cleanLockRemainingSec > 0) {
      roundRectPath(ctx, fr.x + 2, fr.y + 2, fr.w - 4, fr.h - 4, 8);
      ctx.fillStyle = "rgba(15, 23, 42, 0.72)";
      ctx.fill();
      ctx.fillStyle = "#fca5a5";
      ctx.font = "bold 13px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(
        "🧹 단속 계도 불판 정비 중 (" + rc.cleanLockRemainingSec.toFixed(1) + "s)",
        fr.x + fr.w / 2,
        fr.y + fr.h / 2
      );
    }
  }

  function drawSlot(ctx, slotRect, slotView, recipe, nowSec) {
    var x = slotRect.x;
    var y = slotRect.y;
    var w = slotRect.w;
    var h = slotRect.h;
    var cx = x + w / 2;
    var cy = y + h / 2;
    var rx = w * 0.42;
    var ry = h * 0.36;

    roundRectPath(ctx, x, y, w, h, 8);
    if (slotView.status === "BURNT") {
      ctx.fillStyle = "#2b1414";
      ctx.strokeStyle = "#ef4444";
    } else if (slotView.requiresAction) {
      var warn = slotView.overheatRatio > 0.68;
      ctx.fillStyle = warn ? "#3b1d12" : "#282112";
      ctx.strokeStyle = warn ? "#f97316" : "#facc15";
    } else {
      ctx.fillStyle = "#0f172a";
      ctx.strokeStyle = "#334155";
    }
    ctx.lineWidth = slotView.requiresAction ? 2.2 : 1.5;
    ctx.fill();
    ctx.stroke();

    if (slotView.status === "EMPTY") {
      drawFishSilhouette(ctx, cx, cy, rx, ry, "#1e293b", "#475569");
      ctx.fillStyle = "#64748b";
      ctx.font = "bold 10px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("반죽 붓기", cx, cy);
      return;
    }

    if (slotView.status === "BURNT") {
      drawFishSilhouette(ctx, cx, cy, rx, ry, "#1c1917", "#7f1d1d");
      ctx.fillStyle = "#fca5a5";
      ctx.font = "bold 10px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("탄 찌꺼기 청소", cx, cy);
      return;
    }

    var bodyColor = "#fde68a";
    var borderColor = "#d97706";
    if (slotView.phaseId === "cook_front") {
      bodyColor = "#fef3c7";
      borderColor = "#f59e0b";
    } else if (slotView.phaseId === "wait_flip") {
      bodyColor = "#fcd34d";
      borderColor = "#ea580c";
    } else if (slotView.phaseId === "cook_back") {
      bodyColor = "#f59e0b";
      borderColor = "#b45309";
    } else if (slotView.phaseId === "wait_harvest") {
      bodyColor = "#d97706";
      borderColor = "#fef08a";
    }

    var pulse = slotView.requiresAction ? 1 + Math.sin((nowSec || 0) * 7) * 0.03 : 1;
    drawFishSilhouette(ctx, cx, cy - 2, rx * pulse, ry * pulse, bodyColor, borderColor);

    if (recipe) {
      ctx.beginPath();
      ctx.arc(cx - rx * 0.16, cy - 2, Math.max(4, Math.min(w, h) * 0.11), 0, Math.PI * 2);
      ctx.fillStyle = recipe.color;
      ctx.fill();
    }

    var barW = w - 12;
    var barX = x + 6;
    var barY = y + h - 8;
    ctx.fillStyle = "rgba(15, 23, 42, 0.75)";
    ctx.fillRect(barX, barY, barW, 4);

    if (!slotView.requiresAction) {
      ctx.fillStyle = "#38bdf8";
      ctx.fillRect(barX, barY, barW * slotView.progressRatio, 4);
    } else {
      ctx.fillStyle = slotView.overheatRatio > 0.68 ? "#ef4444" : "#22c55e";
      ctx.fillRect(barX, barY, barW * (1 - slotView.overheatRatio), 4);
    }

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 10px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(slotView.phaseLabel, cx, y + 3);
  }

  var cartridge = {
    id: "bungeo",
    prologueCutsceneId: "ep1_prologue",
    uiTokens: {
      bannerTitle: "🐟 전설의 청춘 황금 붕어빵 포차",
      accentColor: "#f59e0b",
      unitSuffix: "마리",
      shopTitle: "🏪 설비 · 메뉴편성 · 전국출장 · 5층타워",
      storyTitle: "📖 청년 역전 스토리 & 챕터 기록",
      shopTabs: [
        { id: "equip", label: "🔥 주물틀·설비" },
        { id: "menu", label: "🍽️ 메뉴·3칸편성" },
        { id: "region", label: "🚚 전국 6대 출장" },
        { id: "tower", label: "🏢 강남 5층 타워" }
      ],
      passiveBadges: {
        thermo: "🌡️ 온도센서",
        manager: "👩‍🍳 김민지"
      }
    },
    cookingPhases: [
      {
        id: "cook_front",
        label: "앞면 굽는중",
        durationSec: 3.6,
        requiresAction: false,
        actionId: null,
        overheatSec: 0,
        nextPhaseId: "wait_flip"
      },
      {
        id: "wait_flip",
        label: "뒤집기!",
        durationSec: 0,
        requiresAction: true,
        actionId: "flip",
        overheatSec: 7.0,
        nextPhaseId: "cook_back"
      },
      {
        id: "cook_back",
        label: "뒷면 굽는중",
        durationSec: 3.4,
        requiresAction: false,
        actionId: null,
        overheatSec: 0,
        nextPhaseId: "wait_harvest"
      },
      {
        id: "wait_harvest",
        label: "완성 수확!",
        durationSec: 0,
        requiresAction: true,
        actionId: "harvest",
        overheatSec: 8.0,
        nextPhaseId: null
      }
    ],
    appliances: [
      {
        id: "mold_3",
        name: "할머니의 3×1(3구) 무쇠틀",
        cols: 3,
        rows: 1,
        slots: 3,
        speedMult: 1.0,
        yieldCount: 1,
        priceMult: 1.0,
        cost: 0,
        reqChapterId: null,
        cutsceneId: null,
        desc: "옥탑방 창고에서 닦아낸 첫 3구 무쇠 주물틀"
      },
      {
        id: "mold_6",
        name: "양면 회전 3×2(6구) 기계",
        cols: 3,
        rows: 2,
        slots: 6,
        speedMult: 1.25,
        yieldCount: 1,
        priceMult: 1.15,
        cost: 12000,
        reqChapterId: "1",
        cutsceneId: "ep2_5_mold_craft",
        desc: "속도 ×1.25 · 단가 ×1.15 (제2장 정식 허가 필수 설비)"
      },
      {
        id: "mold_9",
        name: "고화력 3×3(9구) 블록틀",
        cols: 3,
        rows: 3,
        slots: 9,
        speedMult: 1.5,
        yieldCount: 1,
        priceMult: 1.3,
        cost: 32000,
        reqChapterId: "2",
        cutsceneId: null,
        desc: "9마리 동시 조리 · 속도 ×1.50 · 단가 ×1.30"
      },
      {
        id: "mold_brass9",
        name: "황동 코팅 3×3(9구) 명품틀",
        cols: 3,
        rows: 3,
        slots: 9,
        speedMult: 1.85,
        yieldCount: 2,
        priceMult: 1.55,
        cost: 75000,
        reqChapterId: "2",
        cutsceneId: null,
        desc: "수확량 2배(+2마리) · 속도 ×1.85 · 단가 ×1.55"
      },
      {
        id: "mold_croiffle9",
        name: "크로아상 붕어 프레스 3×3",
        cols: 3,
        rows: 3,
        slots: 9,
        speedMult: 2.2,
        yieldCount: 3,
        priceMult: 2.0,
        cost: 160000,
        reqChapterId: "3",
        cutsceneId: null,
        desc: "수확량 3배(+3마리) · 속도 ×2.20 · 단가 ×2.00"
      }
    ],
    recipes: [
      { id: "redbean", name: "🔴 통단팥", shortName: "통단팥", icon: "🔴", unlockCost: 0, cost: 300, price: 1500, color: "#dc2626" },
      { id: "cream", name: "🟡 슈크림", shortName: "슈크림", icon: "🟡", unlockCost: 3500, cost: 450, price: 2000, color: "#eab308" },
      { id: "sweetpotato", name: "🍠 군고구마", shortName: "군고구마", icon: "🍠", unlockCost: 9000, cost: 600, price: 2600, color: "#a855f7" },
      { id: "pizza", name: "🍕 피자치즈", shortName: "피자치즈", icon: "🍕", unlockCost: 16000, cost: 800, price: 3400, color: "#ea580c" },
      { id: "choco", name: "🍫 헤이즐초코", shortName: "헤이즐초코", icon: "🍫", unlockCost: 28000, cost: 950, price: 4000, color: "#78350f" },
      { id: "hallabong", name: "🍊 제주한라봉", shortName: "한라봉", icon: "🍊", unlockCost: 45000, cost: 1200, price: 5200, color: "#f97316" }
    ],
    facilities: [
      {
        id: "fac_batch_pour",
        name: "일괄 반죽기",
        shortLabel: "일괄 붓기",
        icon: "🥣",
        cost: 4500,
        role: "BATCH_INPUT",
        targetActionId: null,
        isActiveBar: true,
        desc: "빈 슬롯 일괄 반죽 투입 · AUTO 시 주문 맞춤형 자동 반죽"
      },
      {
        id: "fac_link_flip",
        name: "연동 회전 핸들",
        shortLabel: "일괄 뒤집기",
        icon: "🔄",
        cost: 8500,
        role: "PHASE_ACTION",
        targetActionId: "flip",
        isActiveBar: true,
        desc: "익은 슬롯 일괄 뒤집기 · AUTO 시 0.8초 주기 자동 뒤집기"
      },
      {
        id: "fac_auto_harvest",
        name: "자동 수확 트레이",
        shortLabel: "일괄 수확",
        icon: "📥",
        cost: 26000,
        role: "BATCH_HARVEST",
        targetActionId: null,
        isActiveBar: true,
        desc: "완성 슬롯 일괄 진열대 이동 · AUTO 시 0.8초 주기 자동 수확"
      },
      {
        id: "fac_thermo_guard",
        name: "정밀 온도 센서",
        shortLabel: "온도 센서",
        icon: "🌡️",
        cost: 15000,
        role: "OVERHEAT_GUARD",
        targetActionId: null,
        isActiveBar: false,
        desc: "과열 유예 시간 2.5배 연장 및 ON 상태에서 탄 빵 발생 차단"
      },
      {
        id: "fac_manager_minji",
        name: "김민지 매니저 채용",
        shortLabel: "김민지 매니저",
        icon: "👩‍🍳",
        cost: 48000,
        role: "AUTO_SERVE",
        targetActionId: null,
        isActiveBar: false,
        desc: "0.8초 주기로 진열대 재고와 대기 손님·점검·VIP 자동 포장 서빙"
      }
    ],
    regions: [
      {
        id: "region_00_station",
        name: "역전 3번 출구 포차",
        unlockCost: 0,
        mult: 1.0,
        allowVip: false,
        preferredRecipeIds: ["redbean", "cream"],
        introToast: "⛺ 지하철 3번 출구 앞 손수레 포차 영업을 시작합니다!",
        desc: "첫 출발 영업지 · 단가 ×1.00 (선호: 통단팥·슈크림)",
        customerLines: [
          { speaker: "퇴근길 직장인", text: "퇴근길에 주황색 천막 보자마자 뛰어왔어요!" },
          { speaker: "공시생 이지은", text: "사장님 붕어빵 한 입이면 오늘 하루도 위로받아요!" },
          { speaker: "야간 알바생", text: "주머니에 삼천 원 남았는데 오늘 밤 최고의 사치예요!" },
          { speaker: "동네 어르신", text: "어머니가 좋아하시던 옛날 무쇠틀 붕어빵 맛이네요." },
          { speaker: "취준생 청년", text: "면접 보고 오는 길인데 화이팅 소리 듣고 기운 얻어요!" },
          { speaker: "역전 단골", text: "꼬리 끝까지 앙금이 꽉 차 있어서 자꾸 생각나요!" }
        ]
      },
      {
        id: "region_01_seoul_office",
        name: "① 서울 강남·여의도 오피스",
        unlockCost: 15000,
        mult: 1.35,
        allowVip: true,
        preferredRecipeIds: ["cream", "pizza", "choco"],
        introToast: "🚚 강남·여의도 빌딩숲 한복판에 청춘 푸드트럭이 입성했습니다!",
        desc: "단가 ×1.35 · 최상무 VIP 등장 (선호: 슈크림·피자·초코)",
        customerLines: [
          { speaker: "야근 개발자", text: "서버 배포 전에 당 충전 급합니다! 초고속으로 부탁해요!" },
          { speaker: "여의도 증권맨", text: "오늘 코스피보다 사장님 붕어빵 주가가 더 상한가네요!" },
          { speaker: "신입사원 막내", text: "청춘 트럭 붕어빵 사 오면 팀장님이 칼퇴시켜 준대요!" },
          { speaker: "대기업 대리", text: "임원 회의 간식으로 소문나서 줄 서러 내려왔습니다!" },
          { speaker: "강남 취준생", text: "면접 끝나고 나오는데 사장님 트럭 보고 용기 얻어 가요!" }
        ]
      },
      {
        id: "region_02_hongdae_seongsu",
        name: "② 서울 홍대·성수 팝업 거리",
        unlockCost: 28000,
        mult: 1.55,
        allowVip: true,
        preferredRecipeIds: ["pizza", "choco", "sweetpotato"],
        introToast: "🚚 트렌드의 심장 홍대·성수 팝업 골목에서 오픈런이 시작됩니다!",
        desc: "단가 ×1.55 · 최상무 VIP 등장 (선호: 피자·초코·군고구마)",
        customerLines: [
          { speaker: "성수 인플루언서", text: "비주얼 실화냐고요! 치즈 늘어나는 거 릴스 바로 올릴게요!" },
          { speaker: "홍대 버스커", text: "노래 세 곡 부르고 달콤한 냄새에 기타 메고 달려왔어요!" },
          { speaker: "외국인 관광객", text: "오 마이 갓! 코리안 피쉬 브레드! 원더풀!" },
          { speaker: "팝업 방문객", text: "명품 팝업스토어 줄보다 청춘 붕어빵 트럭 줄이 더 길어요!" },
          { speaker: "미대 입시생", text: "실기 끝나고 먹는 따끈한 붕어빵이 최고의 예술 작품이에요!" }
        ]
      },
      {
        id: "region_03_gangwon_ski",
        name: "③ 강원 평창·속초 설원 스키장",
        unlockCost: 45000,
        mult: 1.8,
        allowVip: true,
        preferredRecipeIds: ["redbean", "sweetpotato", "pizza"],
        introToast: "🚚 영하 15도 평창 슬로프 하단에 뜨거운 붕어빵 김이 피어오릅니다!",
        desc: "단가 ×1.80 · 겨울 설원 특수 (선호: 통단팥·군고구마·피자)",
        customerLines: [
          { speaker: "스노보더 청년", text: "슬로프 내려오자마자 보이는 붕어빵 트럭이라니 최고예요!" },
          { speaker: "스키장 가족객", text: "애들이 스키 타다 말고 냄새 맡고 부츠 신고 뛰어왔어요!" },
          { speaker: "강원도 어르신", text: "눈길 뚫고 강원도까지 왔능가! 팥소가 할머니 손맛이구먼!" },
          { speaker: "야간 스키 커플", text: "눈 내리는 스키장에서 호호 불어 먹는 겨울 낭만 끝판왕!" },
          { speaker: "스키 패트롤", text: "철야 안전 근무 서는데 푸드트럭 불빛이 등대 같습니다!" }
        ]
      },
      {
        id: "region_04_busan_haeundae",
        name: "④ 부산 해운대·광안리 야시장",
        unlockCost: 70000,
        mult: 2.1,
        allowVip: true,
        preferredRecipeIds: ["redbean", "pizza", "cream"],
        introToast: "🚚 광안대교 야경 아래 부산 해운대 바닷가 야시장에 상륙했습니다!",
        desc: "단가 ×2.10 · 야시장 인파 (선호: 통단팥·피자·슈크림)",
        customerLines: [
          { speaker: "부산 토박이", text: "와, 꼬리까지 속이 억수로 꽉 찼네! 내 맘에 쏙 든다!" },
          { speaker: "해운대 커플", text: "광안대교 야경 보면서 먹을 따끈한 붕어빵 빨리 사자!" },
          { speaker: "자갈치 상인", text: "총각 무쇠틀 뒤집는 소리만 들어도 장인인 줄 알겠데이!" },
          { speaker: "영화제 관광객", text: "해운대 밤바다 산책하다가 고소한 냄새에 발이 묶였어요!" },
          { speaker: "부산 야구팬", text: "오늘 직관 이기고 기분 좋아서 뒤풀이 간식 사러 왔심더!" }
        ]
      },
      {
        id: "region_05_jeonju_hanok",
        name: "⑤ 전주 한옥마을 돌담길",
        unlockCost: 105000,
        mult: 2.45,
        allowVip: true,
        preferredRecipeIds: ["redbean", "sweetpotato", "choco"],
        introToast: "🚚 눈꽃 내려앉은 미식의 본고장 전주 한옥마을 돌담길에 도착했습니다!",
        desc: "단가 ×2.45 · 미식 특구 (선호: 통단팥·군고구마·초코)",
        customerLines: [
          { speaker: "한복 여행객", text: "기와지붕 아래서 황금빛 붕어빵 들고 인생샷 건졌어요!" },
          { speaker: "전주 종갓집 어른", text: "설탕 맛만 나는 게 아니라 정성껏 고아낸 진짜배기 앙금이군!" },
          { speaker: "한옥스테이 사장", text: "숙소 손님들이 이 트럭 어디 서냐고 계속 물어봐요!" },
          { speaker: "커플 여행객", text: "청춘 붕어빵 맛에 반해서 오늘 두 번째 줄 섰어요!" },
          { speaker: "골목 사진작가", text: "하얀 김 너머로 열심히 빵 굽는 사장님 표정이 참 멋집니다!" }
        ]
      },
      {
        id: "region_06_jeju_aewol",
        name: "⑥ 제주 애월 해안도로",
        unlockCost: 150000,
        mult: 2.85,
        allowVip: true,
        preferredRecipeIds: ["hallabong", "cream", "choco"],
        introToast: "🚚 에메랄드빛 제주 애월 해안도로! 전국 투어 피날레 영업 개시!",
        desc: "단가 ×2.85 · 최고급 휴양지 (선호: 제주한라봉·슈크림·초코)",
        customerLines: [
          { speaker: "제주 해녀 삼춘", text: "물질 끝나고 언 몸 녹이는 데는 이 뜨거운 붕어빵이 제일이주게!" },
          { speaker: "한달살기 청년", text: "애월 해안도로 드라이브하다가 트럭 보고 바로 차 세웠어요!" },
          { speaker: "신혼여행 부부", text: "신혼여행 길에 전설의 푸드트럭을 만나다니 행운이에요!" },
          { speaker: "제주 여행객", text: "상큼한 한라봉 향이랑 바삭한 반죽 조합이 예술이에요!" },
          { speaker: "합격생 이지은", text: "사장님! 저 공무원 최종 합격하고 제주 여행 와서 또 만났어요!" }
        ]
      }
    ],
    towerFloors: [
      {
        floor: 1,
        name: "🏢 1F 플래그십 본점 베이커리 카페",
        cost: 45000,
        desc: "강남대로 1층 본점 오픈 · 전 메뉴 판매 단가 +15%",
        completionQuote: "🎉 [1층 완공] 김민지 매니저: 따뜻한 통유리 본점 오픈 키친이 가동됩니다!"
      },
      {
        floor: 2,
        name: "🏢 2F 수제 앙금 & 반죽 R&D 연구소",
        cost: 95000,
        desc: "할머니 비법 연구소 · 가열 조리 속도 +20% 가속",
        completionQuote: "🎉 [2층 완공] 할머니의 비법 노트가 수제 앙금 R&D 연구소로 탄생했습니다!"
      },
      {
        floor: 3,
        name: "🏢 3F 전국 청년 가맹본부",
        cost: 180000,
        desc: "청년 스타터 본부 · 5초마다 가맹 로열티 +2,500원 입금",
        completionQuote: "🎉 [3층 완공] 전국 청년 창업 지원센터 & 물류 본부가 문을 열었습니다!"
      },
      {
        floor: 4,
        name: "🏢 4F VIP 스카이 테이스팅 라운지",
        cost: 320000,
        desc: "최상무 VIP 등장 주기 단축(8->6명) 및 콤보 팁 배율 +25%",
        completionQuote: "🎉 [4층 완공] 최상무: 이제 우리 그룹 임원 미팅도 다 4층 라운지에서 하네!"
      },
      {
        floor: 5,
        name: "👑 5F 루프탑 가든 & 황금 붕어 동상",
        cost: 550000,
        desc: "강남 5층 타워 최종 완공 · 등기권리증 그랜드 피날레 달성!",
        completionQuote: "👑 [5층 최종 완공] 강남 밤하늘을 밝히는 루프탑 황금 붕어 타워 완성!"
      }
    ],
    chapters: [
      {
        id: "1",
        name: "제1장: 역전 앞 첫 불씨와 단속 계고장",
        goalDesc: "누적 판매 12마리 달성",
        rewardDesc: "보상: +3,000원 & 6구 회전틀 구매 해금",
        reqTotalSold: 12,
        rewardGold: 3000,
        grantsLicense: false,
        cutsceneId: "ep1_5_crackdown",
        progressText: function (s) {
          return "판매 " + Math.min(12, s.totalSold) + " / 12마리";
        }
      },
      {
        id: "2",
        name: "제2장: 구청 정식 영업허가증 제1호 취득",
        goalDesc: "6구 회전틀 보유 + 현장 점검 2회 합격 + 누적 판매 35마리",
        rewardDesc: "보상: 정식 영업허가증 제1호(단속면역·단가+20%·인내심+15%) & 전국 출장 개방",
        reqOwnedApplianceId: "mold_6",
        reqInspectPasses: 2,
        reqTotalSold: 35,
        rewardGold: 10000,
        grantsLicense: true,
        cutsceneId: "ep1_8_permit",
        progressText: function (s) {
          var has6 = s.ownedApplianceIds.indexOf("mold_6") !== -1 ? "완료" : "미보유";
          return "6구틀(" + has6 + ") · 점검 " + Math.min(2, s.inspectPasses) + "/2 · 판매 " + Math.min(35, s.totalSold) + "/35";
        }
      },
      {
        id: "3",
        name: "제3장: 강남 대기업 빌딩 앞 통쾌한 역전극",
        goalDesc: "① 강남·여의도 개척 + 강남 현지 30마리 판매 + 최상무 VIP 1회 완수",
        rewardDesc: "보상: +25,000원 & 강남 5층 타워 증축 개방",
        reqUnlockedRegionId: "region_01_seoul_office",
        reqRegionSales: { regionId: "region_01_seoul_office", count: 30 },
        reqVipServed: 1,
        rewardGold: 25000,
        grantsLicense: false,
        cutsceneId: "ep2_gangnam",
        progressText: function (s) {
          var gSales = s.regionSales["region_01_seoul_office"] || 0;
          return "강남판매 " + Math.min(30, gSales) + "/30 · VIP " + Math.min(1, s.vipServedCount) + "/1";
        }
      },
      {
        id: "4",
        name: "제4장: 전국 6대 명소 푸드트럭 완판 신화",
        goalDesc: "전국 6대 출장지 중 4곳 이상 개척 + 누적 매출 250,000원 달성",
        rewardDesc: "보상: 유튜버 먹짱 협찬금 +60,000원",
        reqUnlockedRegionsCount: 4,
        reqTotalRevenue: 250000,
        rewardGold: 60000,
        grantsLicense: false,
        cutsceneId: "ep3_nationwide",
        progressText: function (s) {
          var tourCnt = Math.max(0, s.unlockedRegionIds.length - 1);
          return "출장개척 " + Math.min(4, tourCnt) + "/4곳 · 매출 " + Math.min(250000, s.totalRevenue).toLocaleString() + "/250,000원";
        }
      },
      {
        id: "5",
        name: "최종장: 강남 5층 『청춘 황금 붕어 타워』 완공",
        goalDesc: "강남 타워 1층 -> 5층 전 층 순차 증축 완공",
        rewardDesc: "보상: 건물주 등기권리증 엔딩 & 청년 100호점 상생 피날레",
        reqTowerFloor: 5,
        rewardGold: 100000,
        grantsLicense: false,
        cutsceneId: "ep4_ending",
        progressText: function (s) {
          return "타워 증축 " + s.towerFloor + " / 5층";
        }
      }
    ],
    cutscenes: {
      ep1_prologue: {
        id: "ep1_prologue",
        title: "❄️ 프롤로그: 100번째 불합격 문자와 할머니의 3구 무쇠틀",
        img: "./assets/story_bungeo/bungeo_ep1_prologue_cart.jpg",
        fallbackIcon: "❄️🔥",
        lines: [
          { speaker: "휴대폰 알림", text: "[안내] 금번 하반기 공개채용 최종 면접에서 모시지 못하게 되었음을 알려드립니다..." },
          { speaker: "박청춘 (27세)", text: "오늘로 딱 백 번째 불합격 문자다. 밀가루와 국산 팥을 사고 남은 영업 시재금은 삼천 원... 창고 속 할머니의 3구 무쇠틀을 밤새 닦아냈다." },
          { speaker: "할머니 (회상)", text: "청춘아, 붕어빵은 꼬리 끝까지 팥이 차 있어야 먹는 사람 마음이 안 시리단다. 추운 날 따뜻한 걸 건네주면 세상이 네 손을 잡으러 온단다." },
          { speaker: "박청춘 (27세)", text: "나를 뽑아주는 회사가 없다면 오늘 밤 지하철 3번 출구 앞에서 내 이름을 건 첫 출근을 시작하겠다!" }
        ]
      },
      ep1_5_crackdown: {
        id: "ep1_5_crackdown",
        title: "🚨 제1장 클리어: 구청 단속반의 급습과 정식 허가 심사의 길",
        img: "./assets/story_bungeo/bungeo_ep1_5_crackdown_crisis.jpg",
        fallbackIcon: "🚨📋",
        lines: [
          { speaker: "강원칙 주무관 (구청 가로정비팀)", text: "역전 보도블록 무허가 노점 민원이 접수되었습니다. 자진 철거하지 않으시면 과태료 처분 대상입니다." },
          { speaker: "공시생 단골 이지은", text: "잠깐만요 주무관님! 매일 밤 눈까지 쓸어놓으시고 학생들에게 따뜻한 붕어빵을 구워주시던 양심 포차예요! 합법 허가 방법을 알려주세요!" },
          { speaker: "강원칙 주무관", text: "손수레 밑바닥에 기름때 하나 없는 걸 보니 진심은 알겠군요. 6구 회전틀 설비와 현장 위생 점검 2회 만점을 통과하면 『구청 정식 영업허가증 제1호』를 교부하겠습니다!" }
        ]
      },
      ep2_5_mold_craft: {
        id: "ep2_5_mold_craft",
        title: "🔥 설비 진화: 황학동 3×2(6구) 양면 고속 회전틀 장착!",
        img: "./assets/story_bungeo/bungeo_ep2_5_mold_craft_upgrade.jpg",
        fallbackIcon: "⚙️🐟",
        lines: [
          { speaker: "이지은 (1호 단골)", text: "사장님! 독서실 단톡방에 소문나서 3번 출구 계단 끝까지 줄이 섰어요!" },
          { speaker: "박청춘 (27세)", text: "차곡차곡 모은 매상으로 3×2 6구 양면 회전 무쇠틀 장착 완료! 이제 두 배 든든하게 구워내서 정식 허가 심사까지 통과하자!" }
        ]
      },
      ep1_8_permit: {
        id: "ep1_8_permit",
        title: "🏅 제2장 클리어: 위생·소방 100점! 구청 정식 영업허가증 제1호!",
        img: "./assets/story_bungeo/bungeo_ep1_8_official_permit.jpg",
        fallbackIcon: "🏅✨",
        lines: [
          { speaker: "강원칙 주무관", text: "단속반 15년 만에 무쇠틀 밑바닥에서 먼지 한 톨 안 나오는 건 처음 봅니다. 위생 100점, 소방 안전 100점! 『청년 명품 거리가게 & 푸드트럭 정식 영업허가증 제1호』를 교부합니다!" },
          { speaker: "박청춘 (27세)", text: "백 번 떨어지고 내 이름으로 받은 인생 첫 합격증이다! 이제 단속 걱정 없이 전국 6대 푸드트럭 특구로 당당히 출발한다!" }
        ]
      },
      ep2_gangnam: {
        id: "ep2_gangnam",
        title: "🚚 제3장 클리어: 나를 떨어뜨렸던 강남 대기업 앞 통쾌한 역전극!",
        img: "./assets/story_bungeo/bungeo_ep2_foodtruck_gangnam.jpg",
        fallbackIcon: "🚚🏙️",
        lines: [
          { speaker: "최상무 (대기업 인사팀 임원)", text: "우리 본부 직원들이 이 트럭 붕어빵 아니면 야근을 안 하겠다고 해서 상무인 내가 직접 줄을 섰는데... 어라, 박청춘 군?!" },
          { speaker: "박청춘 (27세)", text: "면접장에서 '자네 스펙으론 우리 빌딩 문턱도 못 넘는다' 하셨던 지원자 박청춘입니다! 법인카드 단체 주문 감사드리며, 이제 그 빌딩 옆에 제 5층 타워를 세우러 갑니다!" }
        ]
      },
      ep3_nationwide: {
        id: "ep3_nationwide",
        title: "🗺️ 제4장 클리어: 홍대·평창·해운대·전주·제주 전국 투어 제패!",
        img: "./assets/story_bungeo/bungeo_ep3_nationwide_tour.jpg",
        fallbackIcon: "🗺️🎬",
        lines: [
          { speaker: "맛집 유튜버 먹짱 (구독자 180만)", text: "시청자 여러분! 서울 오피스 타운부터 강원 설원, 부산 밤바다, 전주 한옥마을, 제주 해안도로까지 대한민국을 줄 세운 청춘 붕어빵 트럭입니다!" },
          { speaker: "박청춘 (27세)", text: "전국 팔도 손님들의 응원으로 종잣돈이 모였다. 이제 최종 목표인 강남 5층 『청춘 황금 붕어 타워』를 완공할 시간이다!" }
        ]
      },
      ep4_ending: {
        id: "ep4_ending",
        title: "👑 최종장 클리어: 강남 5층 『청춘 황금 붕어 타워』 등기권리증 피날레!",
        img: "./assets/story_bungeo/bungeo_ep4_building_ending.jpg",
        fallbackIcon: "🏢👑",
        lines: [
          { speaker: "김민지 본점 매니저", text: "박청춘 대표님! 서울특별시 강남구 역삼동 『청춘 황금 붕어 타워』 전 층 건물주 등기권리증입니다!" },
          { speaker: "신임 사무관 이지은 & 최상무", text: "축하드려요 대표님! 그날 밤 꼬리 끝까지 채워주셨던 뜨거운 붕어빵 한 마리가 기적을 만들었어요!" },
          { speaker: "박청춘 (청년 건물주 대표)", text: "할머니의 녹슨 3구 무쇠틀에서 시작해 마침내 5층 타워를 세웠습니다. 이제 3층 가맹본부를 통해 전국 청년 100명에게 푸드트럭을 무상 지원하겠습니다! 오늘 밤도 힘차게 구워봅시다!" }
        ]
      }
    },
    campaignRules: {
      startingGold: 3000,
      legacyBonusGold: 1500,
      legacyBonusToast: "🎁 구버전 플레이 기록 확인! 새 시즌 개업 응원금 +1,500원이 지급되었습니다.",
      maxLoadoutSlots: 3,
      rackCapPerTray: 12,
      bailoutMultiplier: 4,
      bailoutMessages: [
        "👵 할머니의 비상 동전주머니에서 반죽 밑천을 찾았습니다!",
        "💚 1호 단골 이지은이 응원 선결제를 맡기고 갔습니다!"
      ],
      insufficientGoldToast: "💸 현금이 부족합니다! 구워진 빵을 서빙해 자금을 확보하세요.",
      insufficientStockToast: "📦 진열대에 주문 수량만큼 완성된 빵이 없습니다!",
      lockedByChapterToast: "🔒 선행 스토리 챕터를 먼저 클리어해야 해금됩니다.",
      licenseRequiredToast: "🏅 제2장 『구청 정식 영업허가증 제1호』 취득 후 전국 출장이 개방됩니다!",
      rackOverflowWholesaleToast: "📦 트레이 만석(12마리) 초과분이 포장 도매가로 즉시 정산되었습니다.",
      allChaptersClearedLabel: "👑 전 챕터 완공 달성 · 무제한 황금 타워 경영 모드",
      autoFacilityPeriodSec: 0.8,
      autoServePeriodSec: 0.8,
      overheatExtendMult: 2.5,
      preferredRecipeWeight: 3,
      normalSpawnIntervalSec: 2.8,
      feverSpawnIntervalSec: 1.6,
      normalPatienceSec: 30.0,
      normalMaxQty: 3,
      comboStepTipRate: 0.05,
      maxBaseTipRate: 0.5,
      permitPatienceBonus: 0.15,
      permitPriceBonus: 0.2,
      permitTipBonus: 0.2,
      tower1FPriceBonus: 0.15,
      tower2FSpeedMult: 1.2,
      royaltyIntervalSec: 5.0,
      royaltyAmount: 2500,
      tower4FTipBonus: 0.25,
      towerUnlockAfterChapterId: "3",
      inspectStartAfterChapterId: "1",
      inspectEveryNormals: 6,
      inspectDurationSec: 25.0,
      inspectRequiredCount: 2,
      inspectPassReward: 1000,
      inspectFine: 1000,
      inspectFailCleanLockSec: 4.0,
      inspectCleanFirstToast: "🧹 불판의 탄 슬롯을 먼저 청소해야 위생 검수를 통과할 수 있습니다!",
      inspectPassToast: "🏅 위생·정품 현장 점검 통과! (+1,000원 · 허가 심사 실적 +1)",
      inspectFailToast: "🚨 현장 점검 시간 초과! 4초간 불판 정비 및 계도 과태료가 적용됩니다.",
      inspectorVisitor: {
        name: "👮 강원칙 주무관",
        badge: "위생점검 25s",
        line: "불판 탄 찌꺼기 제거 + 완성 붕어빵 2마리 검수 제출!"
      },
      vipEveryNormals: 8,
      vipEveryNormals4F: 6,
      vipMinQty: 4,
      vipMaxQty: 8,
      vipPatienceSec: 45.0,
      vipPriceMult: 1.5,
      vipVisitor: {
        name: "💼 최상무 (VIP 단체)",
        badge: "법인카드 ×1.5",
        line: "본부 야근 간식 단체 포장일세! 전량 준비되면 일시불 결제하겠네!"
      },
      feverStartAfterChapterId: "2",
      feverEveryNormals: 10,
      feverVisitorPatienceSec: 32.0,
      feverDurationSec: 15.0,
      feverSpeedMult: 1.35,
      feverTipBonus: 0.25,
      feverStartToast: "🎬 유튜버 먹짱 라이브 피버 발동! 15초간 조리 가속 & 팁 +25%!",
      feverVisitor: {
        name: "🎬 유튜버 먹짱",
        badge: "라이브 피버",
        line: "구독자 여러분! 김이 폭발하는 붕어빵 먹방 라이브 갑니다!"
      }
    },
    computeLayout: computeLayout,
    drawAppliance: drawAppliance,
    drawSlot: drawSlot
  };

  root.TycoonEngine.registerCartridge(cartridge);
})();
