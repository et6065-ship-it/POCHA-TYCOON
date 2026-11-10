(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;

  var SAVE_KEY = "tycoon_engine_save_v2";
  var LEGACY_KEY = "bungeo_portrait_4stage_v1";
  var SCHEMA_VERSION = 2;

  var memoryStore = Object.create(null);
  var currentMode = "OK";

  function readRaw(key) {
    try {
      if (root.localStorage) {
        var val = root.localStorage.getItem(key);
        currentMode = "OK";
        return val;
      }
    } catch (e) {
      currentMode = "MEMORY_FALLBACK";
    }
    return Object.prototype.hasOwnProperty.call(memoryStore, key) ? memoryStore[key] : null;
  }

  function writeRaw(key, value) {
    memoryStore[key] = value;
    try {
      if (root.localStorage) {
        root.localStorage.setItem(key, value);
        currentMode = "OK";
        return true;
      }
    } catch (e) {
      currentMode = "MEMORY_FALLBACK";
    }
    currentMode = "MEMORY_FALLBACK";
    return false;
  }

  function load(createDefaultState, sanitizeState) {
    var defaultState = createDefaultState();
    var legacyRaw = readRaw(LEGACY_KEY);
    var legacyDetected = Boolean(legacyRaw && String(legacyRaw).length > 2);

    var savedRaw = readRaw(SAVE_KEY);
    if (!savedRaw) {
      defaultState.schemaVersion = SCHEMA_VERSION;
      return {
        state: defaultState,
        legacyDetected: legacyDetected,
        storageMode: currentMode
      };
    }

    try {
      var parsed = JSON.parse(savedRaw);
      if (!parsed || typeof parsed !== "object" || parsed.schemaVersion !== SCHEMA_VERSION) {
        defaultState.schemaVersion = SCHEMA_VERSION;
        return {
          state: defaultState,
          legacyDetected: legacyDetected,
          storageMode: currentMode
        };
      }
      var cleanState = typeof sanitizeState === "function"
        ? sanitizeState(parsed, defaultState)
        : Object.assign(defaultState, parsed);
      cleanState.schemaVersion = SCHEMA_VERSION;
      return {
        state: cleanState,
        legacyDetected: legacyDetected,
        storageMode: currentMode
      };
    } catch (e) {
      defaultState.schemaVersion = SCHEMA_VERSION;
      return {
        state: defaultState,
        legacyDetected: legacyDetected,
        storageMode: currentMode
      };
    }
  }

  function saveNow(state) {
    if (!state || typeof state !== "object") return false;
    state.schemaVersion = SCHEMA_VERSION;
    try {
      var payload = JSON.stringify(state);
      return writeRaw(SAVE_KEY, payload);
    } catch (e) {
      currentMode = "MEMORY_FALLBACK";
      return false;
    }
  }

  function resetSave(createDefaultState, preserveFlags) {
    var fresh = createDefaultState();
    fresh.schemaVersion = SCHEMA_VERSION;
    if (preserveFlags && typeof preserveFlags === "object") {
      if (typeof preserveFlags.legacyBonusClaimed === "boolean") {
        fresh.legacyBonusClaimed = preserveFlags.legacyBonusClaimed;
      }
      if (typeof preserveFlags.muted === "boolean") {
        fresh.muted = preserveFlags.muted;
      }
    }
    saveNow(fresh);
    return fresh;
  }

  function getStorageMode() {
    return currentMode;
  }

  root.TycoonStorage = {
    SAVE_KEY: SAVE_KEY,
    LEGACY_KEY: LEGACY_KEY,
    SCHEMA_VERSION: SCHEMA_VERSION,
    load: load,
    saveNow: saveNow,
    resetSave: resetSave,
    getStorageMode: getStorageMode
  };
})();
