(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;
  var cartridges = Object.create(null);
  var defaultCartridgeId = null;

  function registerCartridge(cartridge) {
    if (!cartridge || typeof cartridge.id !== "string" || !cartridge.id) {
      throw new Error("Invalid cartridge registration");
    }
    cartridges[cartridge.id] = cartridge;
    if (!defaultCartridgeId) {
      defaultCartridgeId = cartridge.id;
    }
  }

  function getCartridge(id) {
    var key = id || defaultCartridgeId;
    return key ? cartridges[key] || null : null;
  }

  function getDefaultCartridgeId() {
    return defaultCartridgeId;
  }

  function toSafeInt(val, fallback, minVal) {
    var n = Number(val);
    if (!Number.isFinite(n)) return fallback;
    var floored = Math.floor(n);
    return typeof minVal === "number" ? Math.max(minVal, floored) : floored;
  }

  function indexById(list) {
    var map = Object.create(null);
    for (var i = 0; i < list.length; i++) {
      map[list[i].id] = list[i];
    }
    return map;
  }

  function createEmptySlot() {
    return {
      status: "EMPTY",
      recipeId: null,
      phaseIdx: 0,
      elapsed: 0,
      overheatElapsed: 0
    };
  }

  function createSession(options) {
    var opts = options || {};
    var cartridge = getCartridge(opts.themeId);
    if (!cartridge) {
      throw new Error("No cooking cartridge registered");
    }

    var storage = opts.storage || root.TycoonStorage || null;
    var audio = opts.audio || root.TycoonAudio || null;
    var onCutscene = typeof opts.onCutscene === "function" ? opts.onCutscene : function () {};
    var onToast = typeof opts.onToast === "function" ? opts.onToast : function () {};
    var rand = typeof opts.rng === "function" ? opts.rng : Math.random;

    var rules = cartridge.campaignRules;
    var phases = cartridge.cookingPhases;
    var phaseIdxById = Object.create(null);
    for (var pIdx = 0; pIdx < phases.length; pIdx++) {
      phaseIdxById[phases[pIdx].id] = pIdx;
    }

    var applianceMap = indexById(cartridge.appliances);
    var recipeMap = indexById(cartridge.recipes);
    var facilityMap = indexById(cartridge.facilities);
    var regionMap = indexById(cartridge.regions);
    var chapterMap = indexById(cartridge.chapters);

    var firstAppliance = cartridge.appliances[0];
    var firstRecipe = cartridge.recipes[0];
    var firstRegion = cartridge.regions[0];

    function createDefaultState() {
      var stock = Object.create(null);
      for (var i = 0; i < cartridge.recipes.length; i++) {
        stock[cartridge.recipes[i].id] = 0;
      }
      var regSales = Object.create(null);
      for (var j = 0; j < cartridge.regions.length; j++) {
        regSales[cartridge.regions[j].id] = 0;
      }
      var autoMap = Object.create(null);
      for (var k = 0; k < cartridge.facilities.length; k++) {
        autoMap[cartridge.facilities[k].id] = false;
      }

      return {
        schemaVersion: 2,
        themeId: cartridge.id,
        gold: rules.startingGold,
        totalSold: 0,
        totalRevenue: 0,
        combo: 0,
        bailoutCount: 0,
        licensed: false,
        inspectPasses: 0,
        customersHandledSinceInspect: 0,
        normalsSinceVip: 0,
        normalsSinceFever: 0,
        equippedApplianceId: firstAppliance.id,
        ownedApplianceIds: [firstAppliance.id],
        unlockedRecipeIds: [firstRecipe.id],
        activeLoadoutIds: [firstRecipe.id],
        selectedRecipeId: firstRecipe.id,
        rackStock: stock,
        unlockedFacilityIds: [],
        facilityAutoMap: autoMap,
        currentRegionId: firstRegion.id,
        unlockedRegionIds: [firstRegion.id],
        regionSales: regSales,
        towerFloor: 0,
        vipServedCount: 0,
        clearedChapterIds: [],
        seenCutsceneIds: [],
        legacyBonusClaimed: false,
        muted: false,
        activeCookingRefundedOnLoad: 0
      };
    }

    function filterValidIds(arr, allowMap, fallbackIds) {
      if (!Array.isArray(arr)) return fallbackIds.slice();
      var seen = Object.create(null);
      var out = [];
      for (var i = 0; i < arr.length; i++) {
        var id = arr[i];
        if (typeof id === "string" && allowMap[id] && !seen[id]) {
          seen[id] = true;
          out.push(id);
        }
      }
      return out.length > 0 ? out : fallbackIds.slice();
    }

    function sanitizeState(raw, def) {
      var s = createDefaultState();
      s.gold = toSafeInt(raw.gold, def.gold, 0);
      s.totalSold = toSafeInt(raw.totalSold, 0, 0);
      s.totalRevenue = toSafeInt(raw.totalRevenue, 0, 0);
      s.combo = toSafeInt(raw.combo, 0, 0);
      s.bailoutCount = toSafeInt(raw.bailoutCount, 0, 0);
      s.licensed = Boolean(raw.licensed);
      s.inspectPasses = toSafeInt(raw.inspectPasses, 0, 0);
      s.customersHandledSinceInspect = toSafeInt(raw.customersHandledSinceInspect, 0, 0);
      s.normalsSinceVip = toSafeInt(raw.normalsSinceVip, 0, 0);
      s.normalsSinceFever = toSafeInt(raw.normalsSinceFever, 0, 0);

      s.ownedApplianceIds = filterValidIds(raw.ownedApplianceIds, applianceMap, [firstAppliance.id]);
      if (s.ownedApplianceIds.indexOf(firstAppliance.id) === -1) {
        s.ownedApplianceIds.unshift(firstAppliance.id);
      }
      s.equippedApplianceId = (typeof raw.equippedApplianceId === "string" &&
        s.ownedApplianceIds.indexOf(raw.equippedApplianceId) !== -1)
        ? raw.equippedApplianceId
        : s.ownedApplianceIds[s.ownedApplianceIds.length - 1];

      s.unlockedRecipeIds = filterValidIds(raw.unlockedRecipeIds, recipeMap, [firstRecipe.id]);
      if (s.unlockedRecipeIds.indexOf(firstRecipe.id) === -1) {
        s.unlockedRecipeIds.unshift(firstRecipe.id);
      }

      var unlockedLookup = Object.create(null);
      for (var u = 0; u < s.unlockedRecipeIds.length; u++) {
        unlockedLookup[s.unlockedRecipeIds[u]] = true;
      }
      s.activeLoadoutIds = filterValidIds(
        raw.activeLoadoutIds,
        unlockedLookup,
        s.unlockedRecipeIds.slice(0, rules.maxLoadoutSlots)
      ).slice(0, rules.maxLoadoutSlots);

      s.selectedRecipeId = (typeof raw.selectedRecipeId === "string" &&
        s.activeLoadoutIds.indexOf(raw.selectedRecipeId) !== -1)
        ? raw.selectedRecipeId
        : s.activeLoadoutIds[0];

      if (raw.rackStock && typeof raw.rackStock === "object") {
        for (var r = 0; r < cartridge.recipes.length; r++) {
          var rid = cartridge.recipes[r].id;
          var cap = s.activeLoadoutIds.indexOf(rid) !== -1 ? rules.rackCapPerTray : 0;
          s.rackStock[rid] = Math.min(cap, toSafeInt(raw.rackStock[rid], 0, 0));
        }
      }

      s.unlockedFacilityIds = [];
      if (Array.isArray(raw.unlockedFacilityIds)) {
        var validFacs = [];
        var seenFac = Object.create(null);
        for (var f = 0; f < raw.unlockedFacilityIds.length; f++) {
          var fid = raw.unlockedFacilityIds[f];
          if (typeof fid === "string" && facilityMap[fid] && !seenFac[fid]) {
            seenFac[fid] = true;
            validFacs.push(fid);
          }
        }
        s.unlockedFacilityIds = validFacs;
      }

      if (raw.facilityAutoMap && typeof raw.facilityAutoMap === "object") {
        for (var fa = 0; fa < cartridge.facilities.length; fa++) {
          var facKey = cartridge.facilities[fa].id;
          s.facilityAutoMap[facKey] = Boolean(
            s.unlockedFacilityIds.indexOf(facKey) !== -1 && raw.facilityAutoMap[facKey]
          );
        }
      }

      s.unlockedRegionIds = filterValidIds(raw.unlockedRegionIds, regionMap, [firstRegion.id]);
      if (s.unlockedRegionIds.indexOf(firstRegion.id) === -1) {
        s.unlockedRegionIds.unshift(firstRegion.id);
      }
      if (!s.licensed) {
        s.unlockedRegionIds = [firstRegion.id];
        s.currentRegionId = firstRegion.id;
      } else {
        s.currentRegionId = (typeof raw.currentRegionId === "string" &&
          s.unlockedRegionIds.indexOf(raw.currentRegionId) !== -1)
          ? raw.currentRegionId
          : firstRegion.id;
      }

      if (raw.regionSales && typeof raw.regionSales === "object") {
        for (var rs = 0; rs < cartridge.regions.length; rs++) {
          var regKey = cartridge.regions[rs].id;
          s.regionSales[regKey] = toSafeInt(raw.regionSales[regKey], 0, 0);
        }
      }

      s.towerFloor = Math.min(cartridge.towerFloors.length, toSafeInt(raw.towerFloor, 0, 0));
      s.vipServedCount = toSafeInt(raw.vipServedCount, 0, 0);

      s.clearedChapterIds = [];
      if (Array.isArray(raw.clearedChapterIds)) {
        for (var c = 0; c < raw.clearedChapterIds.length; c++) {
          var cid = String(raw.clearedChapterIds[c]);
          if (chapterMap[cid] && s.clearedChapterIds.indexOf(cid) === -1) {
            s.clearedChapterIds.push(cid);
          }
        }
      }

      s.seenCutsceneIds = [];
      if (Array.isArray(raw.seenCutsceneIds)) {
        for (var sc = 0; sc < raw.seenCutsceneIds.length; sc++) {
          var cutId = String(raw.seenCutsceneIds[sc]);
          if (cartridge.cutscenes[cutId] && s.seenCutsceneIds.indexOf(cutId) === -1) {
            s.seenCutsceneIds.push(cutId);
          }
        }
      }

      s.legacyBonusClaimed = Boolean(raw.legacyBonusClaimed);
      s.muted = Boolean(raw.muted);

      var pendingRefund = toSafeInt(raw.activeCookingRefundedOnLoad, 0, 0);
      if (pendingRefund > 0) {
        s.gold += pendingRefund;
      }
      s.activeCookingRefundedOnLoad = 0;

      return s;
    }

    var loaded = storage
      ? storage.load(createDefaultState, sanitizeState)
      : { state: createDefaultState(), legacyDetected: false, storageMode: "MEMORY_FALLBACK" };
    var state = loaded.state;

    if (audio && typeof audio.setMuted === "function") {
      audio.setMuted(state.muted);
    }

    var slots = [];
    var customers = [null, null, null];
    var pauseReasons = Object.create(null);
    var cleanLockRemainingSec = 0;
    var feverRemainingSec = 0;
    var spawnTimerSec = 0.8;
    var autoFacilityTimerSec = 0;
    var autoServeTimerSec = 0;
    var royaltyTimerSec = 0;
    var visitorSeq = 1;

    function syncSlotsForAppliance() {
      var app = applianceMap[state.equippedApplianceId] || firstAppliance;
      var targetCount = app.slots;
      if (slots.length < targetCount) {
        while (slots.length < targetCount) {
          slots.push(createEmptySlot());
        }
      } else if (slots.length > targetCount) {
        for (var i = targetCount; i < slots.length; i++) {
          if (slots[i].status === "COOKING" && slots[i].recipeId && recipeMap[slots[i].recipeId]) {
            state.gold += recipeMap[slots[i].recipeId].cost;
          }
        }
        slots.length = targetCount;
      }
      updateCookingRefundBookmark();
    }

    function updateCookingRefundBookmark() {
      var sum = 0;
      for (var i = 0; i < slots.length; i++) {
        if (slots[i].status === "COOKING" && slots[i].recipeId && recipeMap[slots[i].recipeId]) {
          sum += recipeMap[slots[i].recipeId].cost;
        }
      }
      state.activeCookingRefundedOnLoad = sum;
    }

    function persist() {
      updateCookingRefundBookmark();
      if (storage && typeof storage.saveNow === "function") {
        storage.saveNow(state);
      }
    }

    function playSound(key) {
      if (audio && typeof audio.playSfx === "function") {
        audio.playSfx(key);
      }
    }

    function triggerCutscene(cutsceneId) {
      var cut = cartridge.cutscenes[cutsceneId];
      if (!cut) return;
      if (state.seenCutsceneIds.indexOf(cutsceneId) === -1) {
        state.seenCutsceneIds.push(cutsceneId);
      }
      persist();
      onCutscene(cut);
    }

    syncSlotsForAppliance();

    if (loaded.legacyDetected && !state.legacyBonusClaimed) {
      state.gold += rules.legacyBonusGold;
      state.legacyBonusClaimed = true;
      persist();
      onToast(rules.legacyBonusToast);
    }

    if (cartridge.prologueCutsceneId && state.seenCutsceneIds.indexOf(cartridge.prologueCutsceneId) === -1) {
      triggerCutscene(cartridge.prologueCutsceneId);
    } else {
      persist();
    }

    function getMaxOwnedYield() {
      var maxY = 1;
      for (var i = 0; i < state.ownedApplianceIds.length; i++) {
        var app = applianceMap[state.ownedApplianceIds[i]];
        if (app && app.yieldCount > maxY) {
          maxY = app.yieldCount;
        }
      }
      return maxY;
    }

    function getWholesaleUnitRefund(recipeId) {
      var rec = recipeMap[recipeId];
      if (!rec) return 0;
      return Math.floor(rec.cost / getMaxOwnedYield());
    }

    function getMinActiveRecipeCost() {
      var minCost = Infinity;
      for (var i = 0; i < state.activeLoadoutIds.length; i++) {
        var rec = recipeMap[state.activeLoadoutIds[i]];
        if (rec && rec.cost < minCost) {
          minCost = rec.cost;
        }
      }
      return Number.isFinite(minCost) ? minCost : firstRecipe.cost;
    }

    function findFacilityByRole(role, targetActionId) {
      for (var i = 0; i < cartridge.facilities.length; i++) {
        var f = cartridge.facilities[i];
        if (f.role === role && (!targetActionId || f.targetActionId === targetActionId)) {
          return f;
        }
      }
      return null;
    }

    function isFacilityOwned(facId) {
      return state.unlockedFacilityIds.indexOf(facId) !== -1;
    }

    function isFacilityAutoOn(facId) {
      return Boolean(isFacilityOwned(facId) && state.facilityAutoMap[facId]);
    }

    function getCookSpeedMult() {
      var app = applianceMap[state.equippedApplianceId] || firstAppliance;
      var mult = app.speedMult;
      if (state.towerFloor >= 2) {
        mult *= rules.tower2FSpeedMult;
      }
      if (feverRemainingSec > 0) {
        mult *= rules.feverSpeedMult;
      }
      return mult;
    }

    function getOverheatLimitSec(phase) {
      var base = phase.overheatSec || 8.0;
      var guardFac = findFacilityByRole("OVERHEAT_GUARD");
      if (guardFac && isFacilityOwned(guardFac.id)) {
        return base * rules.overheatExtendMult;
      }
      return base;
    }

    function isOverheatBlocked() {
      var guardFac = findFacilityByRole("OVERHEAT_GUARD");
      return Boolean(guardFac && isFacilityAutoOn(guardFac.id));
    }

    function countBurntSlots() {
      var cnt = 0;
      for (var i = 0; i < slots.length; i++) {
        if (slots[i].status === "BURNT") cnt++;
      }
      return cnt;
    }

    function countCookingSlots() {
      var cnt = 0;
      for (var i = 0; i < slots.length; i++) {
        if (slots[i].status === "COOKING") cnt++;
      }
      return cnt;
    }

    function getTotalActiveRackStock() {
      var total = 0;
      for (var i = 0; i < state.activeLoadoutIds.length; i++) {
        total += state.rackStock[state.activeLoadoutIds[i]] || 0;
      }
      return total;
    }

    function isChapterCleared(chapterId) {
      return state.clearedChapterIds.indexOf(String(chapterId)) !== -1;
    }

    function getSlotActionType(slotIndex) {
      var slot = slots[slotIndex];
      if (!slot) return null;
      if (cleanLockRemainingSec > 0) return null;
      if (slot.status === "EMPTY") return "pour";
      if (slot.status === "BURNT") return "clean";
      var phase = phases[slot.phaseIdx];
      if (phase && phase.requiresAction) {
        return phase.actionId;
      }
      return null;
    }

    function pourIntoSlot(slotIndex, explicitRecipeId, silentToast) {
      if (cleanLockRemainingSec > 0) return false;
      var slot = slots[slotIndex];
      if (!slot || slot.status !== "EMPTY") return false;
      var rid = explicitRecipeId || state.selectedRecipeId;
      if (state.activeLoadoutIds.indexOf(rid) === -1) {
        rid = state.activeLoadoutIds[0];
      }
      var rec = recipeMap[rid];
      if (!rec) return false;
      if (state.gold < rec.cost) {
        if (!silentToast) {
          onToast(rules.insufficientGoldToast);
        }
        enforceAntiSoftlock();
        return false;
      }
      state.gold -= rec.cost;
      slot.status = "COOKING";
      slot.recipeId = rid;
      slot.phaseIdx = 0;
      slot.elapsed = 0;
      slot.overheatElapsed = 0;
      playSound("pour");
      persist();
      return true;
    }

    function harvestSlotObject(slot, silentToast) {
      var rid = slot.recipeId;
      var rec = recipeMap[rid];
      var app = applianceMap[state.equippedApplianceId] || firstAppliance;
      var yieldCount = app.yieldCount || 1;

      if (rec) {
        if (state.activeLoadoutIds.indexOf(rid) !== -1) {
          var cur = state.rackStock[rid] || 0;
          var space = Math.max(0, rules.rackCapPerTray - cur);
          var toRack = Math.min(space, yieldCount);
          var overflow = yieldCount - toRack;
          state.rackStock[rid] = cur + toRack;
          if (overflow > 0) {
            var refund = overflow * getWholesaleUnitRefund(rid);
            state.gold += refund;
            if (!silentToast && refund > 0) {
              onToast(rules.rackOverflowWholesaleToast);
            }
          }
        } else {
          state.gold += yieldCount * getWholesaleUnitRefund(rid);
        }
      }

      slot.status = "EMPTY";
      slot.recipeId = null;
      slot.phaseIdx = 0;
      slot.elapsed = 0;
      slot.overheatElapsed = 0;
      playSound("harvest");
      persist();
      return true;
    }

    function actOnSlot(slotIndex, expectedActionType) {
      if (cleanLockRemainingSec > 0) return false;
      var slot = slots[slotIndex];
      if (!slot) return false;

      var currentAction = getSlotActionType(slotIndex);
      if (!currentAction) return false;
      if (expectedActionType && currentAction !== expectedActionType) return false;

      if (slot.status === "EMPTY") {
        return pourIntoSlot(slotIndex, state.selectedRecipeId, false);
      }

      if (slot.status === "BURNT") {
        slot.status = "EMPTY";
        slot.recipeId = null;
        slot.phaseIdx = 0;
        slot.elapsed = 0;
        slot.overheatElapsed = 0;
        playSound("clean");
        persist();
        return true;
      }

      var phase = phases[slot.phaseIdx];
      if (!phase || !phase.requiresAction) return false;

      if (phase.nextPhaseId === null) {
        return harvestSlotObject(slot, false);
      }

      var nextIdx = phaseIdxById[phase.nextPhaseId];
      if (typeof nextIdx !== "number") return false;
      slot.phaseIdx = nextIdx;
      slot.elapsed = 0;
      slot.overheatElapsed = 0;
      playSound(phase.actionId);
      persist();
      return true;
    }

    function computeUnitPrice(recipeId, isVip) {
      var rec = recipeMap[recipeId];
      var app = applianceMap[state.equippedApplianceId] || firstAppliance;
      var reg = regionMap[state.currentRegionId] || firstRegion;
      var permitMult = state.licensed ? 1 + rules.permitPriceBonus : 1.0;
      var tower1Mult = state.towerFloor >= 1 ? 1 + rules.tower1FPriceBonus : 1.0;
      var vipMult = isVip ? rules.vipPriceMult : 1.0;
      return Math.round(rec.price * app.priceMult * reg.mult * permitMult * tower1Mult * vipMult);
    }

    function computeTipRate(nextCombo) {
      var baseRate = Math.min(rules.maxBaseTipRate, nextCombo * rules.comboStepTipRate);
      var permitMult = state.licensed ? 1 + rules.permitTipBonus : 1.0;
      var tower4Mult = state.towerFloor >= 4 ? 1 + rules.tower4FTipBonus : 1.0;
      var feverMult = feverRemainingSec > 0 ? 1 + rules.feverTipBonus : 1.0;
      return baseRate * permitMult * tower4Mult * feverMult;
    }

    function canFulfillVisitor(visitor) {
      if (!visitor) return false;
      if (visitor.kind === "INSPECTOR") {
        return countBurntSlots() === 0 && getTotalActiveRackStock() >= rules.inspectRequiredCount;
      }
      for (var i = 0; i < visitor.items.length; i++) {
        var item = visitor.items[i];
        if ((state.rackStock[item.recipeId] || 0) < item.qty) {
          return false;
        }
      }
      return true;
    }

    function canServeAnyWaitingCustomer() {
      for (var i = 0; i < customers.length; i++) {
        if (customers[i] && canFulfillVisitor(customers[i])) {
          return true;
        }
      }
      return false;
    }

    function getActiveWaitingCustomers() {
      var list = [];
      for (var i = 0; i < customers.length; i++) {
        if (customers[i]) list.push(customers[i]);
      }
      return list;
    }

    function serveCustomerSlot(custSlotIdx, silentToast) {
      var visitor = customers[custSlotIdx];
      if (!visitor) return false;

      if (visitor.kind === "INSPECTOR") {
        if (countBurntSlots() > 0) {
          if (!silentToast) {
            onToast(rules.inspectCleanFirstToast);
          }
          return false;
        }
        if (getTotalActiveRackStock() < rules.inspectRequiredCount) {
          if (!silentToast) {
            onToast(rules.insufficientStockToast);
          }
          return false;
        }
        var needed = rules.inspectRequiredCount;
        var sortedLoadout = state.activeLoadoutIds.slice().sort(function (a, b) {
          return (state.rackStock[b] || 0) - (state.rackStock[a] || 0);
        });
        for (var sIdx = 0; sIdx < sortedLoadout.length && needed > 0; sIdx++) {
          var rid = sortedLoadout[sIdx];
          var avail = state.rackStock[rid] || 0;
          var take = Math.min(avail, needed);
          state.rackStock[rid] = avail - take;
          needed -= take;
        }
        state.inspectPasses += 1;
        state.gold += rules.inspectPassReward;
        state.totalRevenue += rules.inspectPassReward;
        customers[custSlotIdx] = null;
        playSound("serve");
        onToast(rules.inspectPassToast);
        checkChaptersAutoClear();
        persist();
        return true;
      }

      if (!canFulfillVisitor(visitor)) {
        if (!silentToast) {
          onToast(rules.insufficientStockToast);
        }
        return false;
      }

      var isVip = visitor.kind === "VIP";
      var subtotal = 0;
      var soldQty = 0;
      for (var i = 0; i < visitor.items.length; i++) {
        var it = visitor.items[i];
        state.rackStock[it.recipeId] -= it.qty;
        subtotal += computeUnitPrice(it.recipeId, isVip) * it.qty;
        soldQty += it.qty;
      }

      state.combo += 1;
      var tipRate = computeTipRate(state.combo);
      var payout = Math.round(subtotal * (1 + tipRate));

      state.gold += payout;
      state.totalSold += soldQty;
      state.totalRevenue += payout;
      state.regionSales[state.currentRegionId] = (state.regionSales[state.currentRegionId] || 0) + soldQty;

      if (visitor.kind === "NORMAL") {
        state.customersHandledSinceInspect += 1;
        state.normalsSinceVip += 1;
        state.normalsSinceFever += 1;
      } else if (visitor.kind === "VIP") {
        state.vipServedCount += 1;
      } else if (visitor.kind === "FEVER") {
        feverRemainingSec = rules.feverDurationSec;
        playSound("fever");
        onToast(rules.feverStartToast);
      }

      customers[custSlotIdx] = null;
      playSound("serve");
      checkChaptersAutoClear();
      persist();
      return true;
    }

    function serveByRecipe(recipeId) {
      var bestIdx = -1;
      var lowestRatio = Infinity;
      for (var i = 0; i < customers.length; i++) {
        var c = customers[i];
        if (!c) continue;
        if (c.kind === "INSPECTOR") {
          if (canFulfillVisitor(c)) {
            return serveCustomerSlot(i, false);
          }
          continue;
        }
        var usesRecipe = false;
        for (var j = 0; j < c.items.length; j++) {
          if (c.items[j].recipeId === recipeId) {
            usesRecipe = true;
            break;
          }
        }
        if (usesRecipe && canFulfillVisitor(c)) {
          var ratio = c.remainingSec / c.maxSec;
          if (ratio < lowestRatio) {
            lowestRatio = ratio;
            bestIdx = i;
          }
        }
      }
      if (bestIdx !== -1) {
        return serveCustomerSlot(bestIdx, false);
      }
      return false;
    }

    function pickWeightedRecipeId(reg) {
      var pool = [];
      var prefList = reg && Array.isArray(reg.preferredRecipeIds) ? reg.preferredRecipeIds : [];
      for (var i = 0; i < state.activeLoadoutIds.length; i++) {
        var rid = state.activeLoadoutIds[i];
        var weight = prefList.indexOf(rid) !== -1 ? rules.preferredRecipeWeight : 1;
        for (var w = 0; w < weight; w++) {
          pool.push(rid);
        }
      }
      return pool[Math.floor(rand() * pool.length)] || state.activeLoadoutIds[0];
    }

    function hasVisitorKind(kind) {
      for (var i = 0; i < customers.length; i++) {
        if (customers[i] && customers[i].kind === kind) return true;
      }
      return false;
    }

    function spawnVisitorInSlot(slotIdx) {
      var reg = regionMap[state.currentRegionId] || firstRegion;

      if (!state.licensed &&
          isChapterCleared(rules.inspectStartAfterChapterId) &&
          state.customersHandledSinceInspect >= rules.inspectEveryNormals &&
          !hasVisitorKind("INSPECTOR")) {
        state.customersHandledSinceInspect = 0;
        customers[slotIdx] = {
          id: visitorSeq++,
          kind: "INSPECTOR",
          name: rules.inspectorVisitor.name,
          badge: rules.inspectorVisitor.badge,
          line: rules.inspectorVisitor.line,
          items: [],
          requiredCount: rules.inspectRequiredCount,
          maxSec: rules.inspectDurationSec,
          remainingSec: rules.inspectDurationSec
        };
        playSound("inspect");
        return;
      }

      var vipInterval = state.towerFloor >= 4 ? rules.vipEveryNormals4F : rules.vipEveryNormals;
      if (reg.allowVip &&
          state.normalsSinceVip >= vipInterval &&
          !hasVisitorKind("VIP")) {
        state.normalsSinceVip = 0;
        var totalVipQty = rules.vipMinQty + Math.floor(rand() * (rules.vipMaxQty - rules.vipMinQty + 1));
        var r1 = pickWeightedRecipeId(reg);
        var vipItems = [];
        if (state.activeLoadoutIds.length > 1 && totalVipQty >= 4) {
          var altIds = state.activeLoadoutIds.filter(function (x) { return x !== r1; });
          var r2 = altIds[Math.floor(rand() * altIds.length)];
          var q1 = Math.ceil(totalVipQty / 2);
          var q2 = totalVipQty - q1;
          vipItems.push({ recipeId: r1, qty: q1 });
          vipItems.push({ recipeId: r2, qty: q2 });
        } else {
          vipItems.push({ recipeId: r1, qty: totalVipQty });
        }
        customers[slotIdx] = {
          id: visitorSeq++,
          kind: "VIP",
          name: rules.vipVisitor.name,
          badge: rules.vipVisitor.badge,
          line: rules.vipVisitor.line,
          items: vipItems,
          maxSec: rules.vipPatienceSec,
          remainingSec: rules.vipPatienceSec
        };
        return;
      }

      if (isChapterCleared(rules.feverStartAfterChapterId) &&
          state.normalsSinceFever >= rules.feverEveryNormals &&
          !hasVisitorKind("FEVER")) {
        state.normalsSinceFever = 0;
        var fRecipe = pickWeightedRecipeId(reg);
        var fQty = 2 + Math.floor(rand() * 2);
        customers[slotIdx] = {
          id: visitorSeq++,
          kind: "FEVER",
          name: rules.feverVisitor.name,
          badge: rules.feverVisitor.badge,
          line: rules.feverVisitor.line,
          items: [{ recipeId: fRecipe, qty: fQty }],
          maxSec: rules.feverVisitorPatienceSec,
          remainingSec: rules.feverVisitorPatienceSec
        };
        return;
      }

      var quotes = Array.isArray(reg.customerLines) && reg.customerLines.length > 0
        ? reg.customerLines
        : [{ speaker: "손님", text: "..." }];
      var pickedQuote = quotes[Math.floor(rand() * quotes.length)];
      var normalRecipe = pickWeightedRecipeId(reg);
      var maxNormalQty = state.clearedChapterIds.length === 0 ? 2 : rules.normalMaxQty;
      var normalQty = 1 + Math.floor(rand() * maxNormalQty);
      var basePatience = rules.normalPatienceSec * (state.licensed ? 1 + rules.permitPatienceBonus : 1.0);

      customers[slotIdx] = {
        id: visitorSeq++,
        kind: "NORMAL",
        name: pickedQuote.speaker,
        badge: "",
        line: pickedQuote.text,
        items: [{ recipeId: normalRecipe, qty: normalQty }],
        maxSec: basePatience,
        remainingSec: basePatience
      };
    }

    function computeAutoInputRecipeId() {
      var demand = Object.create(null);
      for (var i = 0; i < state.activeLoadoutIds.length; i++) {
        demand[state.activeLoadoutIds[i]] = 0;
      }
      for (var c = 0; c < customers.length; c++) {
        var vis = customers[c];
        if (!vis || vis.kind === "INSPECTOR") continue;
        for (var j = 0; j < vis.items.length; j++) {
          var it = vis.items[j];
          if (typeof demand[it.recipeId] === "number") {
            demand[it.recipeId] += it.qty;
          }
        }
      }
      for (var s = 0; s < slots.length; s++) {
        if (slots[s].status === "COOKING" && typeof demand[slots[s].recipeId] === "number") {
          demand[slots[s].recipeId] -= 1;
        }
      }

      var bestDeficitId = null;
      var maxDeficit = 0;
      for (var k = 0; k < state.activeLoadoutIds.length; k++) {
        var rid = state.activeLoadoutIds[k];
        var stock = state.rackStock[rid] || 0;
        if (stock >= rules.rackCapPerTray) continue;
        var deficit = demand[rid] - stock;
        if (deficit > maxDeficit && state.gold >= recipeMap[rid].cost) {
          maxDeficit = deficit;
          bestDeficitId = rid;
        }
      }
      if (bestDeficitId) return bestDeficitId;

      var lowestId = null;
      var lowestStock = rules.rackCapPerTray;
      for (var m = 0; m < state.activeLoadoutIds.length; m++) {
        var cand = state.activeLoadoutIds[m];
        var st = state.rackStock[cand] || 0;
        if (st < lowestStock && state.gold >= recipeMap[cand].cost) {
          lowestStock = st;
          lowestId = cand;
        }
      }
      return lowestId;
    }

    function runFacilityManual(facId) {
      if (!isFacilityOwned(facId)) {
        return buyFacility(facId);
      }
      if (cleanLockRemainingSec > 0) return false;
      var fac = facilityMap[facId];
      if (!fac) return false;

      var acted = 0;
      if (fac.role === "BATCH_INPUT") {
        for (var i = 0; i < slots.length; i++) {
          if (slots[i].status === "EMPTY") {
            if (pourIntoSlot(i, state.selectedRecipeId, acted > 0)) {
              acted++;
            } else {
              break;
            }
          }
        }
      } else if (fac.role === "PHASE_ACTION") {
        for (var j = 0; j < slots.length; j++) {
          if (getSlotActionType(j) === fac.targetActionId) {
            if (actOnSlot(j, fac.targetActionId)) acted++;
          }
        }
      } else if (fac.role === "BATCH_HARVEST") {
        for (var k = 0; k < slots.length; k++) {
          var sl = slots[k];
          if (sl.status === "COOKING") {
            var ph = phases[sl.phaseIdx];
            if (ph && ph.requiresAction && ph.nextPhaseId === null) {
              if (harvestSlotObject(sl, acted > 0)) acted++;
            }
          }
        }
      }
      return acted > 0;
    }

    function buyFacility(facId) {
      var fac = facilityMap[facId];
      if (!fac) return false;
      if (isFacilityOwned(facId)) return false;
      if (state.gold < fac.cost) {
        onToast(rules.insufficientGoldToast);
        return false;
      }
      state.gold -= fac.cost;
      state.unlockedFacilityIds.push(facId);
      state.facilityAutoMap[facId] = true;
      playSound("serve");
      persist();
      return true;
    }

    function toggleFacilityAuto(facId) {
      if (!isFacilityOwned(facId)) {
        return buyFacility(facId);
      }
      state.facilityAutoMap[facId] = !state.facilityAutoMap[facId];
      persist();
      return true;
    }

    function runAutoFacilitiesStep() {
      if (cleanLockRemainingSec > 0) return;

      var harvestFac = findFacilityByRole("BATCH_HARVEST");
      if (harvestFac && isFacilityAutoOn(harvestFac.id)) {
        for (var h = 0; h < slots.length; h++) {
          if (slots[h].status === "COOKING") {
            var phH = phases[slots[h].phaseIdx];
            if (phH && phH.requiresAction && phH.nextPhaseId === null) {
              harvestSlotObject(slots[h], true);
            }
          }
        }
      }

      for (var f = 0; f < cartridge.facilities.length; f++) {
        var fac = cartridge.facilities[f];
        if (fac.role === "PHASE_ACTION" && isFacilityAutoOn(fac.id)) {
          for (var s = 0; s < slots.length; s++) {
            if (getSlotActionType(s) === fac.targetActionId) {
              actOnSlot(s, fac.targetActionId);
            }
          }
        }
      }

      var inputFac = findFacilityByRole("BATCH_INPUT");
      if (inputFac && isFacilityAutoOn(inputFac.id)) {
        for (var p = 0; p < slots.length; p++) {
          if (slots[p].status === "EMPTY") {
            var targetRid = computeAutoInputRecipeId();
            if (!targetRid) break;
            if (!pourIntoSlot(p, targetRid, true)) break;
          }
        }
      }
    }

    function runAutoServeStep() {
      var mgrFac = findFacilityByRole("AUTO_SERVE");
      if (!mgrFac || !isFacilityAutoOn(mgrFac.id)) return;
      for (var i = 0; i < customers.length; i++) {
        if (customers[i] && canFulfillVisitor(customers[i])) {
          serveCustomerSlot(i, true);
          break;
        }
      }
    }

    function enforceAntiSoftlock() {
      var minCost = getMinActiveRecipeCost();
      if (state.gold >= minCost) return false;
      if (countCookingSlots() > 0) return false;

      var totalRack = getTotalActiveRackStock();
      var waiting = getActiveWaitingCustomers();
      var stuckWithCustomers = waiting.length > 0 && !canServeAnyWaitingCustomer();

      if (totalRack === 0 || stuckWithCustomers) {
        var support = minCost * rules.bailoutMultiplier;
        state.gold += support;
        state.bailoutCount += 1;
        var msgList = rules.bailoutMessages;
        var msg = msgList[state.bailoutCount % msgList.length];
        playSound("bailout");
        onToast(msg + " (+" + support.toLocaleString() + "원)");
        persist();
        return true;
      }
      return false;
    }

    function evaluateChapterCondition(ch) {
      if (ch.reqTotalSold && state.totalSold < ch.reqTotalSold) return false;
      if (ch.reqOwnedApplianceId && state.ownedApplianceIds.indexOf(ch.reqOwnedApplianceId) === -1) return false;
      if (ch.reqInspectPasses && state.inspectPasses < ch.reqInspectPasses) return false;
      if (ch.reqUnlockedRegionId && state.unlockedRegionIds.indexOf(ch.reqUnlockedRegionId) === -1) return false;
      if (ch.reqRegionSales) {
        var rSales = state.regionSales[ch.reqRegionSales.regionId] || 0;
        if (rSales < ch.reqRegionSales.count) return false;
      }
      if (ch.reqVipServed && state.vipServedCount < ch.reqVipServed) return false;
      if (ch.reqUnlockedRegionsCount) {
        var tourCount = Math.max(0, state.unlockedRegionIds.length - 1);
        if (tourCount < ch.reqUnlockedRegionsCount) return false;
      }
      if (ch.reqTotalRevenue && state.totalRevenue < ch.reqTotalRevenue) return false;
      if (ch.reqTowerFloor && state.towerFloor < ch.reqTowerFloor) return false;
      return true;
    }

    function checkChaptersAutoClear() {
      for (var i = 0; i < cartridge.chapters.length; i++) {
        var ch = cartridge.chapters[i];
        if (isChapterCleared(ch.id)) continue;
        if (i > 0 && !isChapterCleared(cartridge.chapters[i - 1].id)) {
          break;
        }
        if (evaluateChapterCondition(ch)) {
          state.clearedChapterIds.push(String(ch.id));
          if (ch.rewardGold) {
            state.gold += ch.rewardGold;
            state.totalRevenue += ch.rewardGold;
          }
          if (ch.grantsLicense) {
            state.licensed = true;
            for (var c = 0; c < customers.length; c++) {
              if (customers[c] && customers[c].kind === "INSPECTOR") {
                customers[c] = null;
              }
            }
          }
          playSound("chapter_clear");
          persist();
          if (ch.cutsceneId) {
            triggerCutscene(ch.cutsceneId);
          }
          break;
        } else {
          break;
        }
      }
    }

    function selectRecipe(recipeId) {
      if (state.activeLoadoutIds.indexOf(recipeId) === -1) return false;
      state.selectedRecipeId = recipeId;
      persist();
      return true;
    }

    function unlockRecipe(recipeId) {
      var rec = recipeMap[recipeId];
      if (!rec) return false;
      if (state.unlockedRecipeIds.indexOf(recipeId) !== -1) return false;
      if (state.gold < rec.unlockCost) {
        onToast(rules.insufficientGoldToast);
        return false;
      }
      state.gold -= rec.unlockCost;
      state.unlockedRecipeIds.push(recipeId);
      if (state.activeLoadoutIds.length < rules.maxLoadoutSlots) {
        state.activeLoadoutIds.push(recipeId);
      }
      playSound("serve");
      persist();
      return true;
    }

    function setActiveLoadout(recipeIds) {
      if (!Array.isArray(recipeIds)) return false;
      var nextIds = [];
      for (var i = 0; i < recipeIds.length; i++) {
        var rid = recipeIds[i];
        if (state.unlockedRecipeIds.indexOf(rid) !== -1 && nextIds.indexOf(rid) === -1) {
          nextIds.push(rid);
        }
      }
      nextIds = nextIds.slice(0, rules.maxLoadoutSlots);
      if (nextIds.length === 0) return false;

      for (var s = 0; s < slots.length; s++) {
        var sl = slots[s];
        if (sl.status === "COOKING" && sl.recipeId && nextIds.indexOf(sl.recipeId) === -1) {
          state.gold += recipeMap[sl.recipeId].cost;
          sl.status = "EMPTY";
          sl.recipeId = null;
          sl.phaseIdx = 0;
          sl.elapsed = 0;
          sl.overheatElapsed = 0;
        }
      }

      for (var r = 0; r < cartridge.recipes.length; r++) {
        var checkRid = cartridge.recipes[r].id;
        if (nextIds.indexOf(checkRid) === -1 && (state.rackStock[checkRid] || 0) > 0) {
          state.gold += state.rackStock[checkRid] * getWholesaleUnitRefund(checkRid);
          state.rackStock[checkRid] = 0;
        }
      }

      for (var c = 0; c < customers.length; c++) {
        var vis = customers[c];
        if (!vis || vis.kind === "INSPECTOR") continue;
        var merged = Object.create(null);
        var orderKeys = [];
        for (var m = 0; m < vis.items.length; m++) {
          var item = vis.items[m];
          var mappedId = nextIds.indexOf(item.recipeId) !== -1
            ? item.recipeId
            : nextIds[m % nextIds.length];
          if (!merged[mappedId]) {
            merged[mappedId] = 0;
            orderKeys.push(mappedId);
          }
          merged[mappedId] += item.qty;
        }
        vis.items = orderKeys.map(function (k) {
          return { recipeId: k, qty: merged[k] };
        });
      }

      state.activeLoadoutIds = nextIds;
      if (nextIds.indexOf(state.selectedRecipeId) === -1) {
        state.selectedRecipeId = nextIds[0];
      }
      persist();
      enforceAntiSoftlock();
      return true;
    }

    function buyOrEquipAppliance(appId) {
      var app = applianceMap[appId];
      if (!app) return false;
      if (state.ownedApplianceIds.indexOf(appId) !== -1) {
        state.equippedApplianceId = appId;
        syncSlotsForAppliance();
        persist();
        return true;
      }
      if (app.reqChapterId && !isChapterCleared(app.reqChapterId)) {
        onToast(rules.lockedByChapterToast);
        return false;
      }
      if (state.gold < app.cost) {
        onToast(rules.insufficientGoldToast);
        return false;
      }
      state.gold -= app.cost;
      state.ownedApplianceIds.push(appId);
      state.equippedApplianceId = appId;
      syncSlotsForAppliance();
      playSound("chapter_clear");
      persist();
      if (app.cutsceneId) {
        triggerCutscene(app.cutsceneId);
      }
      checkChaptersAutoClear();
      return true;
    }

    function unlockOrTravelRegion(regionId) {
      var reg = regionMap[regionId];
      if (!reg) return false;
      if (regionId !== firstRegion.id && !state.licensed) {
        onToast(rules.licenseRequiredToast);
        return false;
      }
      if (state.unlockedRegionIds.indexOf(regionId) !== -1) {
        state.currentRegionId = regionId;
        persist();
        return true;
      }
      if (state.gold < reg.unlockCost) {
        onToast(rules.insufficientGoldToast);
        return false;
      }
      state.gold -= reg.unlockCost;
      state.unlockedRegionIds.push(regionId);
      state.currentRegionId = regionId;
      playSound("chapter_clear");
      if (reg.introToast) {
        onToast(reg.introToast);
      }
      checkChaptersAutoClear();
      persist();
      return true;
    }

    function buildNextTowerFloor() {
      if (!isChapterCleared(rules.towerUnlockAfterChapterId)) {
        onToast(rules.lockedByChapterToast);
        return false;
      }
      var nextFloorNum = state.towerFloor + 1;
      var floorSpec = cartridge.towerFloors[nextFloorNum - 1];
      if (!floorSpec) return false;
      if (state.gold < floorSpec.cost) {
        onToast(rules.insufficientGoldToast);
        return false;
      }
      state.gold -= floorSpec.cost;
      state.towerFloor = nextFloorNum;
      playSound("chapter_clear");
      if (floorSpec.completionQuote) {
        onToast(floorSpec.completionQuote);
      }
      checkChaptersAutoClear();
      persist();
      return true;
    }

    function setPaused(reason, active) {
      if (!reason) return;
      if (active) {
        pauseReasons[reason] = true;
      } else {
        delete pauseReasons[reason];
      }
    }

    function isPaused() {
      return Object.keys(pauseReasons).length > 0;
    }

    function toggleMute() {
      state.muted = !state.muted;
      if (audio && typeof audio.setMuted === "function") {
        audio.setMuted(state.muted);
      }
      persist();
      return state.muted;
    }

    function resetCampaign() {
      var keepFlags = {
        legacyBonusClaimed: state.legacyBonusClaimed,
        muted: state.muted
      };
      state = storage
        ? storage.resetSave(createDefaultState, keepFlags)
        : Object.assign(createDefaultState(), keepFlags);
      customers = [null, null, null];
      slots = [];
      cleanLockRemainingSec = 0;
      feverRemainingSec = 0;
      spawnTimerSec = 0.8;
      autoFacilityTimerSec = 0;
      autoServeTimerSec = 0;
      royaltyTimerSec = 0;
      syncSlotsForAppliance();
      if (cartridge.prologueCutsceneId) {
        triggerCutscene(cartridge.prologueCutsceneId);
      }
      return true;
    }

    function tick(rawDt) {
      if (isPaused()) return;
      var dt = Number(rawDt);
      if (!Number.isFinite(dt) || dt <= 0) return;
      dt = Math.min(dt, 0.1);

      if (cleanLockRemainingSec > 0) {
        cleanLockRemainingSec = Math.max(0, cleanLockRemainingSec - dt);
      }
      if (feverRemainingSec > 0) {
        feverRemainingSec = Math.max(0, feverRemainingSec - dt);
      }

      if (state.towerFloor >= 3) {
        royaltyTimerSec += dt;
        while (royaltyTimerSec >= rules.royaltyIntervalSec) {
          royaltyTimerSec -= rules.royaltyIntervalSec;
          state.gold += rules.royaltyAmount;
          state.totalRevenue += rules.royaltyAmount;
          persist();
        }
      }

      var speedMult = getCookSpeedMult();
      var blockOverheat = isOverheatBlocked();
      for (var i = 0; i < slots.length; i++) {
        var sl = slots[i];
        if (sl.status !== "COOKING") continue;
        var ph = phases[sl.phaseIdx];
        if (!ph) continue;

        if (!ph.requiresAction) {
          sl.elapsed += dt * speedMult;
          if (sl.elapsed >= ph.durationSec) {
            var nextIdx = phaseIdxById[ph.nextPhaseId];
            if (typeof nextIdx === "number") {
              sl.phaseIdx = nextIdx;
              sl.elapsed = 0;
              sl.overheatElapsed = 0;
            }
          }
        } else if (cleanLockRemainingSec <= 0) {
          var limitSec = getOverheatLimitSec(ph);
          sl.overheatElapsed += dt;
          if (sl.overheatElapsed >= limitSec) {
            if (blockOverheat) {
              sl.overheatElapsed = limitSec;
            } else {
              sl.status = "BURNT";
              sl.phaseIdx = 0;
              sl.elapsed = 0;
              playSound("burn");
              persist();
            }
          }
        }
      }

      autoFacilityTimerSec += dt;
      if (autoFacilityTimerSec >= rules.autoFacilityPeriodSec) {
        autoFacilityTimerSec %= rules.autoFacilityPeriodSec;
        runAutoFacilitiesStep();
      }

      autoServeTimerSec += dt;
      if (autoServeTimerSec >= rules.autoServePeriodSec) {
        autoServeTimerSec %= rules.autoServePeriodSec;
        runAutoServeStep();
      }

      for (var c = 0; c < customers.length; c++) {
        var vis = customers[c];
        if (!vis) continue;
        vis.remainingSec -= dt;
        if (vis.remainingSec <= 0) {
          if (vis.kind === "INSPECTOR") {
            cleanLockRemainingSec = rules.inspectFailCleanLockSec;
            for (var b = 0; b < slots.length; b++) {
              if (slots[b].status === "BURNT") {
                slots[b].status = "EMPTY";
                slots[b].recipeId = null;
                slots[b].phaseIdx = 0;
                slots[b].elapsed = 0;
                slots[b].overheatElapsed = 0;
              }
            }
            var floorGold = getMinActiveRecipeCost() * 2;
            state.gold = Math.min(state.gold, Math.max(floorGold, state.gold - rules.inspectFine));
            customers[c] = null;
            playSound("burn");
            onToast(rules.inspectFailToast);
            persist();
          } else {
            if (vis.kind === "NORMAL") {
              state.customersHandledSinceInspect += 1;
            }
            state.combo = 0;
            customers[c] = null;
            persist();
          }
        }
      }

      spawnTimerSec -= dt;
      if (spawnTimerSec <= 0) {
        var emptyCustIdx = -1;
        for (var e = 0; e < customers.length; e++) {
          if (!customers[e]) {
            emptyCustIdx = e;
            break;
          }
        }
        if (emptyCustIdx !== -1) {
          spawnVisitorInSlot(emptyCustIdx);
          spawnTimerSec = feverRemainingSec > 0 ? rules.feverSpawnIntervalSec : rules.normalSpawnIntervalSec;
        } else {
          spawnTimerSec = 0.5;
        }
      }

      enforceAntiSoftlock();
      checkChaptersAutoClear();
    }

    function getActiveChapterProgress() {
      for (var i = 0; i < cartridge.chapters.length; i++) {
        var ch = cartridge.chapters[i];
        if (!isChapterCleared(ch.id)) {
          return {
            chapter: ch,
            allCleared: false,
            summary: ch.progressText(state)
          };
        }
      }
      var last = cartridge.chapters[cartridge.chapters.length - 1];
      return {
        chapter: last,
        allCleared: true,
        summary: rules.allChaptersClearedLabel
      };
    }

    function getView() {
      var app = applianceMap[state.equippedApplianceId] || firstAppliance;
      var reg = regionMap[state.currentRegionId] || firstRegion;
      var slotViews = [];
      for (var i = 0; i < slots.length; i++) {
        var sl = slots[i];
        if (sl.status !== "COOKING") {
          slotViews.push({
            index: i,
            status: sl.status,
            recipeId: sl.recipeId,
            phaseId: null,
            phaseLabel: "",
            requiresAction: sl.status === "BURNT",
            actionId: sl.status === "BURNT" ? "clean" : "pour",
            progressRatio: 0,
            overheatRatio: 0
          });
        } else {
          var ph = phases[sl.phaseIdx];
          var limit = ph.requiresAction ? getOverheatLimitSec(ph) : 1;
          slotViews.push({
            index: i,
            status: "COOKING",
            recipeId: sl.recipeId,
            phaseId: ph.id,
            phaseLabel: ph.label,
            requiresAction: ph.requiresAction,
            actionId: ph.actionId || null,
            progressRatio: ph.requiresAction ? 1 : Math.min(1, sl.elapsed / ph.durationSec),
            overheatRatio: ph.requiresAction ? Math.min(1, sl.overheatElapsed / limit) : 0
          });
        }
      }

      return {
        cartridge: cartridge,
        state: state,
        appliance: app,
        region: reg,
        slots: slotViews,
        customers: customers,
        cleanLockRemainingSec: cleanLockRemainingSec,
        feverRemainingSec: feverRemainingSec,
        paused: isPaused(),
        chapterProgress: getActiveChapterProgress(),
        computeUnitPrice: computeUnitPrice,
        canFulfillVisitor: canFulfillVisitor,
        isFacilityOwned: isFacilityOwned,
        isFacilityAutoOn: isFacilityAutoOn,
        getSlotActionType: getSlotActionType
      };
    }

    return {
      tick: tick,
      actOnSlot: actOnSlot,
      getSlotActionType: getSlotActionType,
      selectRecipe: selectRecipe,
      unlockRecipe: unlockRecipe,
      setActiveLoadout: setActiveLoadout,
      runFacilityManual: runFacilityManual,
      toggleFacilityAuto: toggleFacilityAuto,
      buyFacility: buyFacility,
      serveCustomerSlot: serveCustomerSlot,
      serveByRecipe: serveByRecipe,
      buyOrEquipAppliance: buyOrEquipAppliance,
      unlockOrTravelRegion: unlockOrTravelRegion,
      buildNextTowerFloor: buildNextTowerFloor,
      setPaused: setPaused,
      isPaused: isPaused,
      toggleMute: toggleMute,
      resetCampaign: resetCampaign,
      enforceAntiSoftlock: enforceAntiSoftlock,
      getView: getView,
      _debugGrantGold: function (amount) {
        state.gold = Math.max(0, state.gold + toSafeInt(amount, 0));
        persist();
      },
      _debugJumpChapter: function (targetIdx) {
        var idx = toSafeInt(targetIdx, 1, 1);
        if (idx >= 1 && !isChapterCleared("1")) {
          state.totalSold = Math.max(state.totalSold, 12);
        }
        if (idx >= 2) {
          if (state.ownedApplianceIds.indexOf(cartridge.appliances[1].id) === -1) {
            state.ownedApplianceIds.push(cartridge.appliances[1].id);
          }
          state.equippedApplianceId = cartridge.appliances[1].id;
          syncSlotsForAppliance();
          state.inspectPasses = Math.max(state.inspectPasses, 2);
          state.totalSold = Math.max(state.totalSold, 35);
        }
        if (idx >= 3) {
          state.licensed = true;
          var r1 = cartridge.regions[1].id;
          if (state.unlockedRegionIds.indexOf(r1) === -1) state.unlockedRegionIds.push(r1);
          state.currentRegionId = r1;
          state.regionSales[r1] = Math.max(state.regionSales[r1] || 0, 30);
          state.vipServedCount = Math.max(state.vipServedCount, 1);
        }
        if (idx >= 4) {
          for (var r = 1; r <= 4 && r < cartridge.regions.length; r++) {
            var regId = cartridge.regions[r].id;
            if (state.unlockedRegionIds.indexOf(regId) === -1) state.unlockedRegionIds.push(regId);
          }
          state.totalRevenue = Math.max(state.totalRevenue, 250000);
        }
        if (idx >= 5) {
          state.towerFloor = cartridge.towerFloors.length;
        }
        for (var step = 0; step < cartridge.chapters.length; step++) {
          checkChaptersAutoClear();
        }
        persist();
      }
    };
  }

  root.TycoonEngine = {
    registerCartridge: registerCartridge,
    getCartridge: getCartridge,
    getDefaultCartridgeId: getDefaultCartridgeId,
    createSession: createSession
  };
})();
