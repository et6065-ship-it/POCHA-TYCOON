"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");

var ROOT = path.resolve(__dirname, "..");

require(path.join(ROOT, "src/js/tycoon/storage.js"));
require(path.join(ROOT, "src/js/tycoon/engine.js"));
require(path.join(ROOT, "src/js/tycoon/themes/bungeo_theme.js"));

var Engine = globalThis.TycoonEngine;
var Storage = globalThis.TycoonStorage;

function runCartridgeIntegrityChecks() {
  var cartridge = Engine.getCartridge("bungeo");
  assert(cartridge, "bungeo cartridge must be registered");
  assert.strictEqual(cartridge.appliances.length, 5, "5 appliances expected");
  assert.strictEqual(cartridge.recipes.length, 6, "6 recipes expected");
  assert.strictEqual(cartridge.facilities.length, 5, "5 facilities expected");
  assert.strictEqual(cartridge.regions.length, 7, "station + 6 tour regions expected");
  assert.strictEqual(cartridge.towerFloors.length, 5, "5 tower floors expected");

  var referencedCutscenes = new Set();
  if (cartridge.prologueCutsceneId) {
    referencedCutscenes.add(cartridge.prologueCutsceneId);
  }
  cartridge.appliances.forEach(function (app) {
    if (app.cutsceneId) referencedCutscenes.add(app.cutsceneId);
  });
  cartridge.chapters.forEach(function (ch) {
    assert(ch.cutsceneId, "chapter " + ch.id + " must reference cutsceneId");
    referencedCutscenes.add(ch.cutsceneId);
  });

  var cutsceneKeys = Object.keys(cartridge.cutscenes);
  assert.strictEqual(cutsceneKeys.length, 7, "all 7 cutscenes must be present");
  cutsceneKeys.forEach(function (cid) {
    assert(referencedCutscenes.has(cid), "orphan cutscene detected: " + cid);
    var relImg = cartridge.cutscenes[cid].img.replace(/^\.\//, "");
    var diskPath = path.join(ROOT, relImg);
    assert(fs.existsSync(diskPath), "missing illustration asset on disk: " + diskPath);
    assert(fs.statSync(diskPath).size > 1000, "empty illustration asset: " + diskPath);
  });

  var mold9 = cartridge.appliances.find(function (a) { return a.id === "mold_9"; });
  var compactLayout = cartridge.computeLayout(360, 156, mold9, true);
  assert.strictEqual(compactLayout.lidRect, null, "compactMode must omit decorative lid");
  assert.strictEqual(compactLayout.slotRects.length, 9, "3x3 layout must yield 9 slots");
  compactLayout.slotRects.forEach(function (rect) {
    assert(rect.h >= 42, "3x3 compact slot height must be >= 42px, got " + rect.h);
  });
}

function createFreshSession(cutsceneLog, toastLog) {
  Storage.resetSave(function () { return {}; }, {});
  return Engine.createSession({
    themeId: "bungeo",
    storage: {
      load: function (defFn) {
        return { state: defFn(), legacyDetected: false, storageMode: "MEMORY_FALLBACK" };
      },
      saveNow: function () { return true; },
      resetSave: function (defFn, keep) {
        return Object.assign(defFn(), keep || {});
      }
    },
    onCutscene: function (c) { if (cutsceneLog) cutsceneLog.push(c.id); },
    onToast: function (t) { if (toastLog) toastLog.push(t); },
    rng: function () { return 0.1; }
  });
}

function runSimulationInvariantChecks() {
  var cutscenes = [];
  var toasts = [];
  var session = createFreshSession(cutscenes, toasts);

  assert(cutscenes.includes("ep1_prologue"), "prologue must trigger on fresh boot");
  var view = session.getView();
  assert.strictEqual(view.state.gold, 3000, "starting gold must be 3,000");
  assert.strictEqual(view.slots.length, 3, "starting mold must be 3x1 (3 slots)");

  // 1. Manual pour, cook front, flip, cook back, harvest
  assert.strictEqual(session.actOnSlot(0, "pour"), true);
  assert.strictEqual(session.getView().state.gold, 2700, "pouring redbean deducts 300");

  for (var t = 0; t < 40; t++) session.tick(0.1);
  assert.strictEqual(session.getSlotActionType(0), "flip", "slot must reach wait_flip");
  assert.strictEqual(session.actOnSlot(0, "flip"), true);

  for (var t2 = 0; t2 < 38; t2++) session.tick(0.1);
  assert.strictEqual(session.getSlotActionType(0), "harvest", "slot must reach wait_harvest");
  assert.strictEqual(session.actOnSlot(0, "harvest"), true);
  assert.strictEqual(session.getView().state.rackStock.redbean, 1, "harvest adds 1 to rack");

  // 2. Modal pause invariant: overheat must NOT advance while paused
  session.actOnSlot(0, "pour");
  for (var t3 = 0; t3 < 40; t3++) session.tick(0.1);
  var beforeOverheat = session.getView().slots[0].overheatRatio;
  session.setPaused("modal_story", true);
  for (var p = 0; p < 100; p++) session.tick(0.1);
  assert.strictEqual(session.getView().slots[0].overheatRatio, beforeOverheat, "paused tick must freeze overheat");
  session.setPaused("modal_story", false);

  // Let it burn & clean
  for (var b = 0; b < 80; b++) session.tick(0.1);
  assert.strictEqual(session.getView().slots[0].status, "BURNT", "unattended slot must burn");
  assert.strictEqual(session.actOnSlot(0, "clean"), true, "burnt slot cleans immediately");
  assert.strictEqual(session.getView().slots[0].status, "EMPTY");

  // 3. Anti-softlock bailout when gold < minCost & rack === 0 & cooking === 0
  var bailSession = createFreshSession([], []);
  bailSession._debugGrantGold(-2800); // gold = 200 (< 300)
  bailSession.tick(0.1);
  assert(bailSession.getView().state.gold >= 1200, "anti-softlock must grant emergency bailout");
  assert.strictEqual(bailSession.getView().state.bailoutCount, 1);

  // 4. Zero 300% money duplication on yield=3 mold + loadout swap
  var dupSession = createFreshSession([], []);
  dupSession._debugJumpChapter(3);
  dupSession._debugGrantGold(300000);
  assert.strictEqual(dupSession.buyOrEquipAppliance("mold_croiffle9"), true);
  assert.strictEqual(dupSession.unlockRecipe("hallabong"), true);
  assert.strictEqual(dupSession.setActiveLoadout(["redbean", "hallabong"]), true);
  assert.strictEqual(dupSession.selectRecipe("hallabong"), true);

  var goldBeforePour = dupSession.getView().state.gold;
  assert.strictEqual(dupSession.actOnSlot(0, "pour"), true);
  assert.strictEqual(dupSession.getView().state.gold, goldBeforePour - 1200, "1 pour costs 1200");
  for (var c1 = 0; c1 < 25; c1++) dupSession.tick(0.1);
  assert.strictEqual(dupSession.actOnSlot(0, "flip"), true);
  for (var c2 = 0; c2 < 25; c2++) dupSession.tick(0.1);
  assert.strictEqual(dupSession.actOnSlot(0, "harvest"), true);
  assert.strictEqual(dupSession.getView().state.rackStock.hallabong, 3, "yield=3 adds 3 items");

  // Swap hallabong out of loadout -> must refund at most 1200 (never 3600!)
  assert.strictEqual(dupSession.setActiveLoadout(["redbean"]), true);
  assert.strictEqual(dupSession.getView().state.rackStock.hallabong, 0);
  assert.strictEqual(
    dupSession.getView().state.gold,
    goldBeforePour,
    "loadout wholesale refund must equal invested 1200, zero duplication!"
  );

  // 5. Full rack (12/12) + thermo_guard ON must NOT deadlock slot harvest
  assert.strictEqual(dupSession.buyFacility("fac_thermo_guard"), true);
  dupSession.selectRecipe("redbean");
  for (var fill = 0; fill < 5; fill++) {
    dupSession.actOnSlot(0, "pour");
    for (var k1 = 0; k1 < 25; k1++) dupSession.tick(0.1);
    dupSession.actOnSlot(0, "flip");
    for (var k2 = 0; k2 < 25; k2++) dupSession.tick(0.1);
    dupSession.actOnSlot(0, "harvest");
  }
  assert.strictEqual(dupSession.getView().state.rackStock.redbean, 12, "rack capped at 12");
  assert.strictEqual(dupSession.getView().slots[0].status, "EMPTY", "overflow harvest must empty slot cleanly");

  // 6. Inspector fail fine at low gold (200원) must NOT generate free cash
  var inspCutscenes = [];
  var inspSession = createFreshSession(inspCutscenes, []);
  inspSession._debugJumpChapter(1);
  assert(inspCutscenes.includes("ep1_5_crackdown"), "ch1 cutscene triggered");
  // Buy mold_6 -> triggers ep2_5_mold_craft
  inspSession._debugGrantGold(20000);
  assert.strictEqual(inspSession.buyOrEquipAppliance("mold_6"), true);
  assert(inspCutscenes.includes("ep2_5_mold_craft"), "buying mold_6 must trigger ep2_5_mold_craft");

  // Force 6 normal customer expirations to spawn inspector, then drain gold to 200
  inspSession.getView().state.customersHandledSinceInspect = 6;
  inspSession.getView().customers[0] = null;
  inspSession.getView().customers[1] = null;
  inspSession.getView().customers[2] = null;
  for (var sp = 0; sp < 35; sp++) inspSession.tick(0.1);
  var hasInspector = inspSession.getView().customers.some(function (c) {
    return c && c.kind === "INSPECTOR";
  });
  assert(hasInspector, "inspector must spawn after 6 normals in unlicensed state");

  // Put 1 item on rack so anti-softlock does not fire, set gold = 200, expire 25s inspection
  inspSession.getView().state.rackStock.redbean = 5;
  var curGold = inspSession.getView().state.gold;
  inspSession._debugGrantGold(-(curGold - 200));
  assert.strictEqual(inspSession.getView().state.gold, 200);
  for (var ex = 0; ex < 260; ex++) inspSession.tick(0.1);
  assert.strictEqual(
    inspSession.getView().state.gold,
    200,
    "failing inspection at 200 gold must NEVER increase gold to 600!"
  );

  // 7. Chapter 5 requires sequential tower floors 1..5 (not totalSold)
  var endCutscenes = [];
  var endSession = createFreshSession(endCutscenes, []);
  endSession._debugJumpChapter(4);
  endSession.getView().state.totalSold = 999;
  endSession.tick(0.1);
  assert(!endCutscenes.includes("ep4_ending"), "high totalSold alone must NOT clear Chapter 5");
  endSession._debugGrantGold(2000000);
  for (var fl = 1; fl <= 5; fl++) {
    assert.strictEqual(endSession.buildNextTowerFloor(), true, "floor " + fl + " must build sequentially");
  }
  assert(endCutscenes.includes("ep4_ending"), "completing 5th floor must trigger ep4_ending");
}

function runStaticBoundaryChecksIfPresent() {
  var uiPath = path.join(ROOT, "src/js/tycoon/ui.js");
  var audioPath = path.join(ROOT, "src/js/tycoon/audio.js");
  var cssPath = path.join(ROOT, "src/css/tycoon.css");
  var htmlPath = path.join(ROOT, "pocha.html");

  if (!fs.existsSync(uiPath) || !fs.existsSync(cssPath)) {
    console.log("[Phase 1] Core & Cartridge simulation invariants PASSED.");
    return;
  }

  var forbiddenWords = [
    "bungeo", "redbean", "sweetpotato", "hallabong",
    "mold_3", "mold_6", "붕어", "단팥", "강원칙", "최상무", "먹짱"
  ];

  ["src/js/tycoon/engine.js", "src/js/tycoon/ui.js"].forEach(function (rel) {
    var src = fs.readFileSync(path.join(ROOT, rel), "utf8");
    forbiddenWords.forEach(function (word) {
      assert(
        !src.toLowerCase().includes(word.toLowerCase()),
        rel + " must not contain theme-specific token: " + word
      );
    });
    assert(!src.includes(".innerHTML"), rel + " must not use .innerHTML");
  });

  var html = fs.readFileSync(htmlPath, "utf8");
  if (!html.includes("src/js/tycoon/engine.js")) {
    console.log("[Phase 2] Core, Cartridge & UI static checks PASSED (pocha.html pending Phase 3).");
    return;
  }

  var idxEngine = html.indexOf("src/js/tycoon/engine.js");
  var idxTheme = html.indexOf("src/js/tycoon/themes/bungeo_theme.js");
  var idxUi = html.indexOf("src/js/tycoon/ui.js");
  assert(idxEngine !== -1 && idxTheme !== -1 && idxUi !== -1, "all defer scripts must exist in pocha.html");
  assert(idxEngine < idxTheme && idxTheme < idxUi, "script load order must be engine.js -> bungeo_theme.js -> ui.js");
  assert(html.includes('data-launcher-return="true"'), "launcher return attribute required");
  assert(/<a\b[^>]*data-launcher-return="true"/.test(html), "launcher return must be an <a> element");
  assert(!html.includes("즉시 클리어"), "production cheat button must be removed");

  var bundleFiles = [
    "src/css/tycoon.css",
    "src/js/tycoon/audio.js",
    "src/js/tycoon/storage.js",
    "src/js/tycoon/engine.js",
    "src/js/tycoon/themes/bungeo_theme.js",
    "src/js/tycoon/ui.js"
  ];
  var totalBytes = bundleFiles.reduce(function (acc, rel) {
    return acc + fs.statSync(path.join(ROOT, rel)).size;
  }, 0);
  assert(totalBytes <= 160 * 1024, "bundle size must be <= 160KB, got " + totalBytes + "B");
  console.log(
    "[Phase 3] ALL static, contract & simulation invariants PASSED! Bundle size: " +
    (totalBytes / 1024).toFixed(2) + " KB"
  );
}

runCartridgeIntegrityChecks();
runSimulationInvariantChecks();
runStaticBoundaryChecksIfPresent();
