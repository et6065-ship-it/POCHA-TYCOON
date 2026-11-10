(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;

  function boot() {
    if (!root.document || !root.TycoonEngine) return;

    var doc = root.document;
    var params = new URLSearchParams(root.location ? root.location.search : "");
    var requestedTheme = params.get("theme") || root.TycoonEngine.getDefaultCartridgeId();
    var isDebug = params.get("debug") === "1";

    var dom = {
      bannerTop: doc.getElementById("banner-top"),
      bannerBottom: doc.getElementById("banner-bottom"),
      hudGold: doc.getElementById("hud-gold"),
      hudCombo: doc.getElementById("hud-combo"),
      hudRegion: doc.getElementById("hud-region"),
      hudMission: doc.getElementById("hud-mission"),
      badgeThermo: doc.getElementById("badge-thermo"),
      badgeManager: doc.getElementById("badge-manager"),
      btnStory: doc.getElementById("btn-open-story"),
      btnMenu: doc.getElementById("btn-open-menu"),
      btnShop: doc.getElementById("btn-open-shop"),
      btnMute: doc.getElementById("btn-mute"),
      customerZone: doc.getElementById("customer-zone"),
      custSlots: Array.prototype.slice.call(doc.querySelectorAll(".cust-slot")),
      rackZone: doc.getElementById("rack-zone"),
      rackTrays: Array.prototype.slice.call(doc.querySelectorAll(".rack-tray")),
      canvasWrap: doc.getElementById("mold-canvas-wrap"),
      canvas: doc.getElementById("mold-canvas"),
      facilityBar: doc.getElementById("facility-bar"),
      facCards: Array.prototype.slice.call(doc.querySelectorAll(".fac-card")),
      loadoutBar: doc.getElementById("loadout-bar"),
      ingBtns: Array.prototype.slice.call(doc.querySelectorAll(".ing-btn")),
      toast: doc.getElementById("toast-banner"),
      shopModal: doc.getElementById("shop-modal"),
      shopTitle: doc.getElementById("shop-modal-title"),
      shopTabsWrap: doc.getElementById("shop-modal-tabs"),
      shopBody: doc.getElementById("shop-modal-body"),
      btnCloseShop: doc.getElementById("btn-close-shop"),
      storyModal: doc.getElementById("story-modal"),
      storyTitle: doc.getElementById("story-modal-title"),
      storyBody: doc.getElementById("story-modal-body"),
      btnCloseStory: doc.getElementById("btn-close-story")
    };

    var toastHideTimer = null;
    var modalOpenedAtMs = 0;
    var activeShopTab = "equip";
    var queuedCutscene = null;

    function showToast(msg) {
      if (!dom.toast || !msg) return;
      dom.toast.textContent = msg;
      dom.toast.dataset.visible = "true";
      if (toastHideTimer) clearTimeout(toastHideTimer);
      toastHideTimer = setTimeout(function () {
        dom.toast.dataset.visible = "false";
      }, 2400);
    }

    var strokesByPointerId = Object.create(null);

    function clearAllStrokes() {
      strokesByPointerId = Object.create(null);
    }

    var session = root.TycoonEngine.createSession({
      themeId: requestedTheme,
      storage: root.TycoonStorage,
      audio: root.TycoonAudio,
      onCutscene: function (cutscene) {
        queuedCutscene = cutscene;
        openStoryModal(cutscene);
      },
      onToast: showToast
    });

    var initialView = session.getView();
    var cartridge = initialView.cartridge;
    var recipeMap = Object.create(null);
    for (var r = 0; r < cartridge.recipes.length; r++) {
      recipeMap[cartridge.recipes[r].id] = cartridge.recipes[r];
    }

    var activeBarFacilities = cartridge.facilities.filter(function (f) {
      return f.isActiveBar;
    }).slice(0, 3);

    doc.documentElement.style.setProperty("--theme-accent", cartridge.uiTokens.accentColor);
    doc.documentElement.style.setProperty("--rack-cols", String(cartridge.campaignRules.maxLoadoutSlots));
    if (dom.bannerTop) dom.bannerTop.textContent = cartridge.uiTokens.bannerTitle;
    if (dom.bannerBottom) dom.bannerBottom.textContent = cartridge.uiTokens.bannerTitle;
    if (dom.shopTitle) dom.shopTitle.textContent = cartridge.uiTokens.shopTitle;
    if (dom.storyTitle) dom.storyTitle.textContent = cartridge.uiTokens.storyTitle;

    function syncModalPauseState() {
      var shopOpen = dom.shopModal && dom.shopModal.dataset.open === "true";
      var storyOpen = dom.storyModal && dom.storyModal.dataset.open === "true";
      if (shopOpen || storyOpen) {
        clearAllStrokes();
        session.setPaused("modal", true);
      } else {
        session.setPaused("modal", false);
      }
    }

    function canDismissModalNow() {
      return (root.performance ? root.performance.now() : Date.now()) - modalOpenedAtMs >= 250;
    }

    function openShopModal(tabId) {
      if (!dom.shopModal) return;
      activeShopTab = tabId || activeShopTab || "equip";
      modalOpenedAtMs = root.performance ? root.performance.now() : Date.now();
      dom.shopModal.dataset.open = "true";
      syncModalPauseState();
      renderShopModal();
    }

    function closeShopModal() {
      if (!canDismissModalNow()) return;
      if (dom.shopModal) dom.shopModal.dataset.open = "false";
      syncModalPauseState();
    }

    function openStoryModal(cutsceneToView) {
      if (!dom.storyModal) return;
      modalOpenedAtMs = root.performance ? root.performance.now() : Date.now();
      dom.storyModal.dataset.open = "true";
      syncModalPauseState();
      renderStoryModal(cutsceneToView || null);
    }

    function closeStoryModal() {
      if (!canDismissModalNow()) return;
      queuedCutscene = null;
      if (dom.storyModal) dom.storyModal.dataset.open = "false";
      syncModalPauseState();
    }

    function makeEl(tag, className, text) {
      var el = doc.createElement(tag);
      if (className) el.className = className;
      if (typeof text === "string") el.textContent = text;
      return el;
    }

    function renderShopTabs() {
      if (!dom.shopTabsWrap) return;
      var tabs = cartridge.uiTokens.shopTabs;
      var nodes = [];
      for (var i = 0; i < tabs.length; i++) {
        (function (tab) {
          var btn = makeEl("button", "modal-tab", tab.label);
          btn.type = "button";
          btn.dataset.active = String(activeShopTab === tab.id);
          btn.addEventListener("click", function () {
            activeShopTab = tab.id;
            renderShopModal();
          });
          nodes.push(btn);
        })(tabs[i]);
      }
      dom.shopTabsWrap.replaceChildren.apply(dom.shopTabsWrap, nodes);
    }

    function renderShopModal() {
      if (!dom.shopBody) return;
      renderShopTabs();
      var view = session.getView();
      var s = view.state;
      var items = [];

      if (activeShopTab === "equip") {
        for (var a = 0; a < cartridge.appliances.length; a++) {
          (function (app) {
            var owned = s.ownedApplianceIds.indexOf(app.id) !== -1;
            var equipped = s.equippedApplianceId === app.id;
            var card = makeEl("div", "shop-card");
            var main = makeEl("div", "shop-card-main");
            main.appendChild(makeEl("div", "shop-card-title", app.name));
            main.appendChild(makeEl("div", "shop-card-desc", app.desc));
            var btn = makeEl(
              "button",
              "shop-action-btn",
              equipped ? "장착 중" : owned ? "장착하기" : app.cost.toLocaleString() + "원 구매"
            );
            btn.type = "button";
            if (owned) btn.dataset.secondary = "true";
            btn.disabled = equipped;
            btn.addEventListener("click", function () {
              if (session.buyOrEquipAppliance(app.id)) {
                renderShopModal();
              }
            });
            card.appendChild(main);
            card.appendChild(btn);
            items.push(card);
          })(cartridge.appliances[a]);
        }

        for (var f = 0; f < cartridge.facilities.length; f++) {
          (function (fac) {
            var owned = view.isFacilityOwned(fac.id);
            var autoOn = view.isFacilityAutoOn(fac.id);
            var card = makeEl("div", "shop-card");
            var main = makeEl("div", "shop-card-main");
            main.appendChild(makeEl("div", "shop-card-title", fac.icon + " " + fac.name));
            main.appendChild(makeEl("div", "shop-card-desc", fac.desc));
            var btn = makeEl(
              "button",
              "shop-action-btn",
              !owned
                ? fac.cost.toLocaleString() + "원 해금"
                : autoOn
                  ? "AUTO ON (끄기)"
                  : "AUTO OFF (켜기)"
            );
            btn.type = "button";
            if (owned && autoOn) btn.dataset.secondary = "true";
            btn.addEventListener("click", function () {
              if (!owned) {
                session.buyFacility(fac.id);
              } else {
                session.toggleFacilityAuto(fac.id);
              }
              renderShopModal();
            });
            card.appendChild(main);
            card.appendChild(btn);
            items.push(card);
          })(cartridge.facilities[f]);
        }

        var resetBtn = makeEl("button", "danger-reset-btn", "🗑️ 현재 캠페인 세이브 초기화");
        resetBtn.type = "button";
        resetBtn.addEventListener("click", function () {
          if (root.confirm && !root.confirm("진행 중인 캠페인 데이터를 초기화하고 처음부터 다시 시작할까요?")) {
            return;
          }
          dom.shopModal.dataset.open = "false";
          session.resetCampaign();
        });
        items.push(resetBtn);
      } else if (activeShopTab === "menu") {
        var guide = makeEl(
          "div",
          "shop-card-desc",
          "영업 화면에는 최대 3종의 주력 메뉴만 배치됩니다. 제외된 메뉴의 조리 슬롯과 잔여 진열대 재고는 도매 원가로 자동 정산됩니다."
        );
        items.push(guide);

        for (var rc = 0; rc < cartridge.recipes.length; rc++) {
          (function (rec) {
            var unlocked = s.unlockedRecipeIds.indexOf(rec.id) !== -1;
            var inLoadout = s.activeLoadoutIds.indexOf(rec.id) !== -1;
            var card = makeEl("div", "shop-card");
            var main = makeEl("div", "shop-card-main");
            main.appendChild(
              makeEl(
                "div",
                "shop-card-title",
                rec.name + " (원가 " + rec.cost.toLocaleString() + "원 · 기본단가 " + rec.price.toLocaleString() + "원)"
              )
            );
            main.appendChild(
              makeEl(
                "div",
                "shop-card-desc",
                inLoadout ? "✅ 현재 3칸 영업 트레이 배치 중" : unlocked ? "보유 중 (터치하여 3칸 트레이 편성)" : "미해금 레시피"
              )
            );

            var btn = makeEl(
              "button",
              "shop-action-btn",
              !unlocked
                ? rec.unlockCost.toLocaleString() + "원 해금"
                : inLoadout
                  ? (s.activeLoadoutIds.length <= 1 ? "필수 1종 유지" : "편성 해제")
                  : "영업 배치"
            );
            btn.type = "button";
            if (inLoadout) btn.dataset.secondary = "true";
            btn.disabled = unlocked && inLoadout && s.activeLoadoutIds.length <= 1;

            btn.addEventListener("click", function () {
              if (!unlocked) {
                session.unlockRecipe(rec.id);
              } else if (inLoadout) {
                var removed = s.activeLoadoutIds.filter(function (id) { return id !== rec.id; });
                session.setActiveLoadout(removed);
              } else {
                var next = s.activeLoadoutIds.slice();
                if (next.length >= cartridge.campaignRules.maxLoadoutSlots) {
                  next.shift();
                }
                next.push(rec.id);
                session.setActiveLoadout(next);
              }
              renderShopModal();
            });
            card.appendChild(main);
            card.appendChild(btn);
            items.push(card);
          })(cartridge.recipes[rc]);
        }
      } else if (activeShopTab === "region") {
        for (var rg = 0; rg < cartridge.regions.length; rg++) {
          (function (reg, idx) {
            var unlocked = s.unlockedRegionIds.indexOf(reg.id) !== -1;
            var isCur = s.currentRegionId === reg.id;
            var card = makeEl("div", "shop-card");
            var main = makeEl("div", "shop-card-main");
            main.appendChild(makeEl("div", "shop-card-title", reg.name));
            main.appendChild(makeEl("div", "shop-card-desc", reg.desc));

            var label = isCur
              ? "현재 영업지"
              : unlocked
                ? "무료 이동"
                : !s.licensed && idx > 0
                  ? "허가증 필요"
                  : reg.unlockCost.toLocaleString() + "원 개척";
            var btn = makeEl("button", "shop-action-btn", label);
            btn.type = "button";
            if (unlocked) btn.dataset.secondary = "true";
            btn.disabled = isCur;
            btn.addEventListener("click", function () {
              if (session.unlockOrTravelRegion(reg.id)) {
                renderShopModal();
              }
            });
            card.appendChild(main);
            card.appendChild(btn);
            items.push(card);
          })(cartridge.regions[rg], rg);
        }
      } else if (activeShopTab === "tower") {
        for (var tf = 0; tf < cartridge.towerFloors.length; tf++) {
          (function (fl) {
            var built = s.towerFloor >= fl.floor;
            var isNext = s.towerFloor + 1 === fl.floor;
            var card = makeEl("div", "shop-card");
            var main = makeEl("div", "shop-card-main");
            main.appendChild(makeEl("div", "shop-card-title", fl.name));
            main.appendChild(makeEl("div", "shop-card-desc", fl.desc));
            var btn = makeEl(
              "button",
              "shop-action-btn",
              built ? "완공됨" : isNext ? fl.cost.toLocaleString() + "원 증축" : (fl.floor - 1) + "층 선행 필요"
            );
            btn.type = "button";
            if (built) btn.dataset.secondary = "true";
            btn.disabled = !isNext;
            btn.addEventListener("click", function () {
              if (session.buildNextTowerFloor()) {
                renderShopModal();
              }
            });
            card.appendChild(main);
            card.appendChild(btn);
            items.push(card);
          })(cartridge.towerFloors[tf]);
        }
      }

      dom.shopBody.replaceChildren.apply(dom.shopBody, items);
    }

    function buildCutsceneViewNodes(cut) {
      var wrap = [];
      var titleEl = makeEl("div", "shop-card-title", cut.title);
      wrap.push(titleEl);

      var mediaHolder = makeEl("div", "");
      var img = doc.createElement("img");
      img.className = "cutscene-illust";
      img.alt = cut.title;
      img.onerror = function () {
        var fallback = makeEl("div", "cutscene-fallback-card");
        fallback.appendChild(makeEl("div", "cutscene-fallback-icon", cut.fallbackIcon || "🎬"));
        fallback.appendChild(makeEl("div", "shop-card-title", cut.title));
        mediaHolder.replaceChildren(fallback);
      };
      img.src = cut.img;
      mediaHolder.appendChild(img);
      wrap.push(mediaHolder);

      for (var i = 0; i < cut.lines.length; i++) {
        var ln = cut.lines[i];
        var row = makeEl("div", "cutscene-line-item");
        row.appendChild(makeEl("div", "cutscene-speaker", ln.speaker));
        row.appendChild(makeEl("div", "cutscene-text", ln.text));
        wrap.push(row);
      }
      return wrap;
    }

    function renderStoryModal(cutsceneToView) {
      if (!dom.storyBody) return;
      var view = session.getView();
      var s = view.state;
      var nodes = [];

      if (cutsceneToView) {
        var cutNodes = buildCutsceneViewNodes(cutsceneToView);
        for (var i = 0; i < cutNodes.length; i++) nodes.push(cutNodes[i]);

        var confirmBtn = makeEl("button", "shop-action-btn", "확인 · 영업 계속하기");
        confirmBtn.type = "button";
        confirmBtn.addEventListener("click", function () {
          closeStoryModal();
        });
        nodes.push(confirmBtn);
        dom.storyBody.replaceChildren.apply(dom.storyBody, nodes);
        return;
      }

      for (var c = 0; c < cartridge.chapters.length; c++) {
        (function (ch) {
          var cleared = s.clearedChapterIds.indexOf(String(ch.id)) !== -1;
          var card = makeEl("div", "shop-card");
          var main = makeEl("div", "shop-card-main");
          main.appendChild(makeEl("div", "shop-card-title", (cleared ? "✅ " : "🎯 ") + ch.name));
          main.appendChild(makeEl("div", "shop-card-desc", ch.goalDesc + " (" + ch.progressText(s) + ")"));
          main.appendChild(makeEl("div", "shop-card-desc", ch.rewardDesc));
          card.appendChild(main);

          if (cleared && cartridge.cutscenes[ch.cutsceneId]) {
            var replayBtn = makeEl("button", "shop-action-btn", "컷신 다시보기");
            replayBtn.type = "button";
            replayBtn.dataset.secondary = "true";
            replayBtn.addEventListener("click", function () {
              renderStoryModal(cartridge.cutscenes[ch.cutsceneId]);
            });
            card.appendChild(replayBtn);
          }
          nodes.push(card);
        })(cartridge.chapters[c]);
      }

      var seenKeys = s.seenCutsceneIds;
      for (var sk = 0; sk < seenKeys.length; sk++) {
        (function (cutKey) {
          var isChapterLinked = cartridge.chapters.some(function (x) { return x.cutsceneId === cutKey; });
          if (isChapterLinked || !cartridge.cutscenes[cutKey]) return;
          var extraCard = makeEl("div", "shop-card");
          var main = makeEl("div", "shop-card-main");
          main.appendChild(makeEl("div", "shop-card-title", "🎬 " + cartridge.cutscenes[cutKey].title));
          extraCard.appendChild(main);
          var btn = makeEl("button", "shop-action-btn", "다시보기");
          btn.type = "button";
          btn.dataset.secondary = "true";
          btn.addEventListener("click", function () {
            renderStoryModal(cartridge.cutscenes[cutKey]);
          });
          extraCard.appendChild(btn);
          nodes.push(extraCard);
        })(seenKeys[sk]);
      }

      dom.storyBody.replaceChildren.apply(dom.storyBody, nodes);
    }

    // Dirty-checked DOM cache
    var prevDomCache = Object.create(null);
    function patchText(key, el, val) {
      if (!el) return;
      if (prevDomCache[key] !== val) {
        prevDomCache[key] = val;
        el.textContent = val;
      }
    }
    function patchAttr(key, el, attrName, val) {
      if (!el) return;
      if (prevDomCache[key] !== val) {
        prevDomCache[key] = val;
        el.dataset[attrName] = val;
      }
    }

    var custRefs = dom.custSlots.map(function (slotEl) {
      return {
        root: slotEl,
        name: slotEl.querySelector(".cust-name"),
        tag: slotEl.querySelector(".cust-tag"),
        order: slotEl.querySelector(".cust-order"),
        line: slotEl.querySelector(".cust-line"),
        barFill: slotEl.querySelector(".cust-bar-fill")
      };
    });

    var rackRefs = dom.rackTrays.map(function (trayEl) {
      return {
        root: trayEl,
        name: trayEl.querySelector(".rack-tray-name"),
        price: trayEl.querySelector(".rack-tray-price"),
        count: trayEl.querySelector(".rack-tray-count")
      };
    });

    var facRefs = dom.facCards.map(function (cardEl) {
      return {
        root: cardEl,
        manualBtn: cardEl.querySelector(".fac-manual-btn"),
        title: cardEl.querySelector(".fac-title"),
        sub: cardEl.querySelector(".fac-sub"),
        autoBtn: cardEl.querySelector(".fac-auto-btn")
      };
    });

    var ingRefs = dom.ingBtns.map(function (btnEl) {
      return {
        root: btnEl,
        name: btnEl.querySelector(".ing-name"),
        cost: btnEl.querySelector(".ing-cost")
      };
    });

    function patchGameplayDom(view) {
      var s = view.state;
      patchText("gold", dom.hudGold, "💰 " + s.gold.toLocaleString() + "원");

      var feverOn = view.feverRemainingSec > 0;
      var comboStr = feverOn
        ? "🔥 피버 " + view.feverRemainingSec.toFixed(0) + "s · " + s.combo + "콤보"
        : "⚡ " + s.combo + "콤보";
      patchText("combo", dom.hudCombo, comboStr);
      patchAttr("comboFever", dom.hudCombo, "fever", String(feverOn));

      var permitMark = s.licensed ? "🏅허가1호 · " : "⚠️무허가 · ";
      patchText("region", dom.hudRegion, permitMark + view.region.name);
      patchText("mission", dom.hudMission, "🎯 " + view.chapterProgress.summary);
      patchText("mute", dom.btnMute, s.muted ? "🔇" : "🔊");

      var thermoFac = cartridge.facilities.find(function (f) { return f.role === "OVERHEAT_GUARD"; });
      var mgrFac = cartridge.facilities.find(function (f) { return f.role === "AUTO_SERVE"; });
      if (thermoFac && dom.badgeThermo) {
        patchText("bThermoT", dom.badgeThermo, cartridge.uiTokens.passiveBadges.thermo);
        patchAttr("bThermoOn", dom.badgeThermo, "on", String(view.isFacilityAutoOn(thermoFac.id)));
      }
      if (mgrFac && dom.badgeManager) {
        patchText("bMgrT", dom.badgeManager, cartridge.uiTokens.passiveBadges.manager);
        patchAttr("bMgrOn", dom.badgeManager, "on", String(view.isFacilityAutoOn(mgrFac.id)));
      }

      for (var c = 0; c < custRefs.length; c++) {
        var cref = custRefs[c];
        var vis = view.customers[c];
        if (!vis) {
          patchAttr("cEmpty" + c, cref.root, "empty", "true");
          patchAttr("cKind" + c, cref.root, "visitorKind", "NONE");
          patchAttr("cFul" + c, cref.root, "fulfillable", "false");
          patchText("cName" + c, cref.name, "손님 대기 중");
          patchText("cTag" + c, cref.tag, "");
          patchText("cOrd" + c, cref.order, "—");
          patchText("cLine" + c, cref.line, "곧 따뜻한 냄새를 맡고 찾아옵니다");
          if (cref.barFill) cref.barFill.style.width = "0%";
        } else {
          var canServe = view.canFulfillVisitor(vis);
          patchAttr("cEmpty" + c, cref.root, "empty", "false");
          patchAttr("cKind" + c, cref.root, "visitorKind", vis.kind);
          patchAttr("cFul" + c, cref.root, "fulfillable", String(canServe));
          patchText("cName" + c, cref.name, vis.name);
          patchText("cTag" + c, cref.tag, vis.badge || "");

          var orderLabel = "";
          if (vis.kind === "INSPECTOR") {
            orderLabel = "위생검수 " + vis.requiredCount + cartridge.uiTokens.unitSuffix +
              " (" + Math.ceil(vis.remainingSec) + "s)";
          } else {
            orderLabel = vis.items.map(function (it) {
              var rObj = recipeMap[it.recipeId];
              return (rObj ? rObj.icon + rObj.shortName : it.recipeId) + "×" + it.qty;
            }).join(" + ");
          }
          patchText("cOrd" + c, cref.order, orderLabel);
          patchText("cLine" + c, cref.line, vis.line);

          if (cref.barFill) {
            var pct = Math.max(0, Math.min(100, (vis.remainingSec / vis.maxSec) * 100));
            cref.barFill.style.width = pct.toFixed(1) + "%";
            patchAttr("cLow" + c, cref.barFill, "low", String(pct < 30));
          }
        }
      }

      for (var t = 0; t < rackRefs.length; t++) {
        var rref = rackRefs[t];
        var loadId = s.activeLoadoutIds[t] || null;
        if (!loadId || !recipeMap[loadId]) {
          patchAttr("rLock" + t, rref.root, "locked", "true");
          rref.root.dataset.recipeId = "";
          patchText("rName" + t, rref.name, "➕ 빈 메뉴 트레이");
          patchText("rPrice" + t, rref.price, "상점·메뉴에서 해금");
          patchText("rCnt" + t, rref.count, "-");
        } else {
          var recObj = recipeMap[loadId];
          var unitP = view.computeUnitPrice(loadId, false);
          var stCnt = s.rackStock[loadId] || 0;
          patchAttr("rLock" + t, rref.root, "locked", "false");
          rref.root.dataset.recipeId = loadId;
          patchText("rName" + t, rref.name, recObj.icon + " " + recObj.shortName);
          patchText("rPrice" + t, rref.price, unitP.toLocaleString() + "원");
          patchText("rCnt" + t, rref.count, stCnt + "/" + cartridge.campaignRules.rackCapPerTray);
        }
      }

      for (var f = 0; f < facRefs.length; f++) {
        var fref = facRefs[f];
        var facSpec = activeBarFacilities[f];
        if (!facSpec) continue;
        fref.root.dataset.facId = facSpec.id;
        var owned = view.isFacilityOwned(facSpec.id);
        var autoOn = view.isFacilityAutoOn(facSpec.id);

        if (!owned) {
          patchAttr("fState" + f, fref.root, "facState", "locked");
          patchText("fTitle" + f, fref.title, "🔒 " + facSpec.shortLabel);
          patchText("fSub" + f, fref.sub, facSpec.cost.toLocaleString() + "원 해금");
          patchAttr("fAutoHid" + f, fref.autoBtn, "hidden", "true");
        } else {
          var eligible = 0;
          for (var slIdx = 0; slIdx < view.slots.length; slIdx++) {
            var slAct = view.getSlotActionType(slIdx);
            if (facSpec.role === "BATCH_INPUT" && slAct === "pour") eligible++;
            else if (facSpec.role === "PHASE_ACTION" && slAct === facSpec.targetActionId) eligible++;
            else if (facSpec.role === "BATCH_HARVEST" && view.slots[slIdx].requiresAction &&
                     view.slots[slIdx].actionId !== facSpec.targetActionId &&
                     view.slots[slIdx].status === "COOKING" && slAct === "harvest") eligible++;
          }
          var stMode = autoOn ? "auto" : eligible > 0 ? "ready" : "idle";
          patchAttr("fState" + f, fref.root, "facState", stMode);
          patchText("fTitle" + f, fref.title, facSpec.icon + " " + facSpec.shortLabel);

          var subLabel = "대기 (" + eligible + ")";
          if (facSpec.role === "BATCH_INPUT" && eligible > 0) {
            var selRec = recipeMap[s.selectedRecipeId];
            var estCost = (selRec ? selRec.cost : 0) * eligible;
            subLabel = "-" + estCost.toLocaleString() + "원 (" + eligible + ")";
          } else if (eligible > 0) {
            subLabel = "실행 (" + eligible + ")";
          }
          patchText("fSub" + f, fref.sub, subLabel);
          patchAttr("fAutoHid" + f, fref.autoBtn, "hidden", "false");
          patchAttr("fAutoOn" + f, fref.autoBtn, "auto", String(autoOn));
          patchText("fAutoTxt" + f, fref.autoBtn, autoOn ? "AUTO\nON" : "AUTO\nOFF");
        }
      }

      for (var g = 0; g < ingRefs.length; g++) {
        var iref = ingRefs[g];
        var lid = s.activeLoadoutIds[g] || null;
        if (!lid || !recipeMap[lid]) {
          iref.root.dataset.recipeId = "";
          patchAttr("iSel" + g, iref.root, "selected", "false");
          patchAttr("iEmp" + g, iref.root, "emptySlot", "true");
          patchText("iName" + g, iref.name, "🍽️ 메뉴 추가");
          patchText("iCost" + g, iref.cost, "탭하여 해금·편성");
        } else {
          var rSpec = recipeMap[lid];
          iref.root.dataset.recipeId = lid;
          patchAttr("iSel" + g, iref.root, "selected", String(s.selectedRecipeId === lid));
          patchAttr("iEmp" + g, iref.root, "emptySlot", "false");
          patchText("iName" + g, iref.name, rSpec.name);
          patchText("iCost" + g, iref.cost, "투입 -" + rSpec.cost.toLocaleString() + "원");
        }
      }
    }

    // Canvas ResizeObserver & Rendering
    var ctx = dom.canvas ? dom.canvas.getContext("2d") : null;
    var canvasCssW = 320;
    var canvasCssH = 200;
    var dpr = 1;
    var compactMode = false;
    var currentLayout = null;

    function syncCanvasSize() {
      if (!dom.canvasWrap || !dom.canvas || !ctx) return;
      var rect = dom.canvasWrap.getBoundingClientRect();
      var w = Math.max(120, Math.floor(rect.width));
      var h = Math.max(120, Math.floor(rect.height));
      var nextDpr = Math.min(root.devicePixelRatio || 1, 2);
      if (w === canvasCssW && h === canvasCssH && nextDpr === dpr && currentLayout) return;
      canvasCssW = w;
      canvasCssH = h;
      dpr = nextDpr;
      compactMode = canvasCssH < 190;
      dom.canvas.width = Math.round(canvasCssW * dpr);
      dom.canvas.height = Math.round(canvasCssH * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      currentLayout = cartridge.computeLayout(canvasCssW, canvasCssH, session.getView().appliance, compactMode);
    }

    if (typeof root.ResizeObserver === "function" && dom.canvasWrap) {
      var ro = new root.ResizeObserver(function () {
        currentLayout = null;
        syncCanvasSize();
      });
      ro.observe(dom.canvasWrap);
    }
    root.addEventListener("resize", function () {
      currentLayout = null;
      syncCanvasSize();
    });

    var lastApplianceId = null;
    function renderCanvas(view, nowSec) {
      if (!ctx) return;
      if (!currentLayout || lastApplianceId !== view.appliance.id) {
        lastApplianceId = view.appliance.id;
        currentLayout = cartridge.computeLayout(canvasCssW, canvasCssH, view.appliance, compactMode);
      }
      ctx.clearRect(0, 0, canvasCssW, canvasCssH);
      cartridge.drawAppliance(ctx, currentLayout, view.appliance, {
        compactMode: compactMode,
        feverActive: view.feverRemainingSec > 0,
        cleanLockRemainingSec: view.cleanLockRemainingSec
      });

      for (var i = 0; i < currentLayout.slotRects.length; i++) {
        var sRect = currentLayout.slotRects[i];
        var sView = view.slots[i];
        if (!sView) continue;
        var rec = sView.recipeId ? recipeMap[sView.recipeId] : null;
        cartridge.drawSlot(ctx, sRect, sView, rec, nowSec);
      }
    }

    // Lazy First-Slot Lock Brush-Swipe Pointer Tracker
    function hitTestSlotIndex(clientX, clientY, insetPx) {
      if (!dom.canvas || !currentLayout) return -1;
      var bounds = dom.canvas.getBoundingClientRect();
      var x = clientX - bounds.left;
      var y = clientY - bounds.top;
      var pad = insetPx || 0;
      for (var i = 0; i < currentLayout.slotRects.length; i++) {
        var r = currentLayout.slotRects[i];
        if (x >= r.x + pad && x <= r.x + r.w - pad && y >= r.y + pad && y <= r.y + r.h - pad) {
          return r.index;
        }
      }
      return -1;
    }

    function handleCanvasStrokePoint(pointerId, clientX, clientY, isInitialDown) {
      var stroke = strokesByPointerId[pointerId];
      if (!stroke || session.isPaused()) return;
      var hitIdx = hitTestSlotIndex(clientX, clientY, isInitialDown ? 0 : 2);
      if (hitIdx < 0 || stroke.visited[hitIdx]) return;

      var slotAction = session.getSlotActionType(hitIdx);
      if (!slotAction) return;

      if (stroke.actionType === null) {
        stroke.actionType = slotAction;
      }
      if (slotAction === stroke.actionType) {
        stroke.visited[hitIdx] = true;
        session.actOnSlot(hitIdx, stroke.actionType);
      }
    }

    if (dom.canvas) {
      dom.canvas.addEventListener("pointerdown", function (e) {
        if (session.isPaused()) return;
        strokesByPointerId[e.pointerId] = {
          actionType: null,
          visited: Object.create(null)
        };
        try {
          dom.canvas.setPointerCapture(e.pointerId);
        } catch (err) {}
        handleCanvasStrokePoint(e.pointerId, e.clientX, e.clientY, true);
      });

      dom.canvas.addEventListener("pointermove", function (e) {
        if (!strokesByPointerId[e.pointerId]) return;
        handleCanvasStrokePoint(e.pointerId, e.clientX, e.clientY, false);
      });

      var endStroke = function (e) {
        delete strokesByPointerId[e.pointerId];
      };
      dom.canvas.addEventListener("pointerup", endStroke);
      dom.canvas.addEventListener("pointercancel", endStroke);
      dom.canvas.addEventListener("lostpointercapture", endStroke);
    }

    // Event Delegation on Persistent Zones
    if (dom.customerZone) {
      dom.customerZone.addEventListener("pointerdown", function (e) {
        var slotEl = e.target.closest(".cust-slot");
        if (!slotEl) return;
        var idx = Number(slotEl.dataset.slot);
        if (Number.isFinite(idx)) {
          session.serveCustomerSlot(idx, false);
        }
      });
    }

    if (dom.rackZone) {
      dom.rackZone.addEventListener("pointerdown", function (e) {
        var trayEl = e.target.closest(".rack-tray");
        if (!trayEl) return;
        var rid = trayEl.dataset.recipeId;
        if (!rid) {
          openShopModal("menu");
          return;
        }
        session.serveByRecipe(rid);
      });
    }

    if (dom.facilityBar) {
      dom.facilityBar.addEventListener("pointerdown", function (e) {
        var autoBtn = e.target.closest(".fac-auto-btn");
        var cardEl = e.target.closest(".fac-card");
        if (!cardEl || !cardEl.dataset.facId) return;
        var fid = cardEl.dataset.facId;
        if (autoBtn) {
          session.toggleFacilityAuto(fid);
        } else {
          session.runFacilityManual(fid);
        }
      });
    }

    if (dom.loadoutBar) {
      dom.loadoutBar.addEventListener("pointerdown", function (e) {
        var btnEl = e.target.closest(".ing-btn");
        if (!btnEl) return;
        var rid = btnEl.dataset.recipeId;
        if (!rid) {
          openShopModal("menu");
          return;
        }
        session.selectRecipe(rid);
      });
    }

    // Top HUD & Modal Bindings
    if (dom.btnShop) {
      dom.btnShop.addEventListener("click", function () { openShopModal("equip"); });
    }
    if (dom.btnMenu) {
      dom.btnMenu.addEventListener("click", function () { openShopModal("menu"); });
    }
    if (dom.btnStory) {
      dom.btnStory.addEventListener("click", function () { openStoryModal(null); });
    }
    if (dom.btnMute) {
      dom.btnMute.addEventListener("click", function () { session.toggleMute(); });
    }
    if (dom.badgeThermo || dom.badgeManager) {
      var openEquipTab = function () { openShopModal("equip"); };
      if (dom.badgeThermo) dom.badgeThermo.addEventListener("click", openEquipTab);
      if (dom.badgeManager) dom.badgeManager.addEventListener("click", openEquipTab);
    }
    if (dom.btnCloseShop) {
      dom.btnCloseShop.addEventListener("click", closeShopModal);
    }
    if (dom.btnCloseStory) {
      dom.btnCloseStory.addEventListener("click", closeStoryModal);
    }
    if (dom.shopModal) {
      dom.shopModal.addEventListener("click", function (e) {
        if (e.target === dom.shopModal) closeShopModal();
      });
    }
    if (dom.storyModal) {
      dom.storyModal.addEventListener("click", function (e) {
        if (e.target === dom.storyModal) closeStoryModal();
      });
    }

    doc.addEventListener("visibilitychange", function () {
      clearAllStrokes();
      session.setPaused("hidden", doc.hidden);
    });

    if (isDebug) {
      root.__TYCOON_DEBUG__ = {
        getState: function () { return session.getView().state; },
        grantGold: function (n) { session._debugGrantGold(n); },
        jumpChapter: function (n) { session._debugJumpChapter(n); },
        resetSave: function () { session.resetCampaign(); }
      };
    }

    if (queuedCutscene) {
      openStoryModal(queuedCutscene);
    }

    syncCanvasSize();
    var lastFrameMs = root.performance ? root.performance.now() : Date.now();

    function frame(nowMs) {
      var rawDt = (nowMs - lastFrameMs) / 1000;
      lastFrameMs = nowMs;
      var clampedDt = Math.min(Math.max(0, rawDt), 0.05);
      session.tick(clampedDt);

      var view = session.getView();
      patchGameplayDom(view);
      renderCanvas(view, nowMs / 1000);
      root.requestAnimationFrame(frame);
    }

    root.requestAnimationFrame(frame);
  }

  if (root.document) {
    if (root.document.readyState === "loading") {
      root.document.addEventListener("DOMContentLoaded", boot);
    } else {
      boot();
    }
  }

  root.TycoonUI = {
    boot: boot
  };
})();
