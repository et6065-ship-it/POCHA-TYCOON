/**
 * Unified Game Launcher — Shared Bridge & Viewport Fit Contract
 * Loaded in <head> across index.html, janggi.html, chess.html, blockblast.html, pocha.html.
 */
(function () {
  'use strict';

  var FIT_STORAGE_KEY = 'BLOCK_BLAST_FIT_MODE_V1';
  var BOTTOM_RESERVE_TABLE = [12, 64, 108];
  var memoryFitFallback = null;

  var isEmbedded = false;
  try {
    isEmbedded = window.parent !== window;
  } catch (e) {
    isEmbedded = true;
  }

  if (isEmbedded) {
    document.documentElement.setAttribute('data-embedded', 'true');
  }

  function isInAppUserAgent() {
    var ua = (navigator && navigator.userAgent) || '';
    return /NAVER|KAKAOTALK|Instagram|FBAN|FBAV|Line|;\s*wv\)/i.test(ua);
  }

  function clampFitMode(val) {
    var n = parseInt(val, 10);
    if (n === 0 || n === 1 || n === 2) return n;
    return null;
  }

  function readFitMode() {
    try {
      var saved = localStorage.getItem(FIT_STORAGE_KEY);
      var parsed = clampFitMode(saved);
      if (parsed !== null) return parsed;
    } catch (e) {}

    if (memoryFitFallback !== null) return memoryFitFallback;

    try {
      var params = new URLSearchParams(window.location.search);
      var fromQuery = clampFitMode(params.get('fit'));
      if (fromQuery !== null) return fromQuery;
    } catch (e) {}

    return isInAppUserAgent() ? 1 : 0;
  }

  function applyFitTokens(mode) {
    var normalized = clampFitMode(mode);
    if (normalized === null) normalized = readFitMode();
    var reservePx = BOTTOM_RESERVE_TABLE[normalized];
    var root = document.documentElement;
    root.setAttribute('data-fit-mode', String(normalized));
    root.style.setProperty('--app-fit-bottom-reserve', reservePx + 'px');
    return normalized;
  }

  function writeFitMode(mode) {
    var normalized = clampFitMode(mode);
    if (normalized === null) normalized = 0;
    memoryFitFallback = normalized;
    try {
      localStorage.setItem(FIT_STORAGE_KEY, String(normalized));
    } catch (e) {}
    applyFitTokens(normalized);
    try {
      window.dispatchEvent(new Event('resize'));
    } catch (e) {}
    return normalized;
  }

  function getBottomReservePx(mode) {
    var normalized = clampFitMode(mode);
    if (normalized === null) normalized = readFitMode();
    return BOTTOM_RESERVE_TABLE[normalized];
  }

  function requestLauncherReturn() {
    if (isEmbedded) {
      var targetOrigin = window.location.protocol === 'file:' ? '*' : window.location.origin;
      try {
        window.parent.postMessage({ type: 'LAUNCHER_RETURN' }, targetOrigin);
        return;
      } catch (e) {}
    }
    window.location.href = './';
  }

  function setupReturnDelegation() {
    document.addEventListener('click', function (e) {
      var target = e.target && e.target.closest ? e.target.closest('[data-launcher-return="true"]') : null;
      if (!target) return;
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;
      if (isEmbedded) {
        e.preventDefault();
        requestLauncherReturn();
      }
    });
  }

  function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;
    var proto = window.location.protocol;
    var host = window.location.hostname;
    if (proto === 'https:' || host === 'localhost' || host === '127.0.0.1') {
      navigator.serviceWorker.register('./sw.js').catch(function () {});
    }
  }

  // Apply synchronously in <head> before body layout
  applyFitTokens(readFitMode());

  window.addEventListener('pageshow', function () {
    applyFitTokens(readFitMode());
    try {
      window.dispatchEvent(new Event('resize'));
    } catch (e) {}
  });

  window.addEventListener('storage', function (e) {
    if (!e || !e.key || e.key === FIT_STORAGE_KEY) {
      applyFitTokens(readFitMode());
      try {
        window.dispatchEvent(new Event('resize'));
      } catch (err) {}
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      setupReturnDelegation();
      registerServiceWorker();
    });
  } else {
    setupReturnDelegation();
    registerServiceWorker();
  }

  window.LauncherCommon = {
    FIT_STORAGE_KEY: FIT_STORAGE_KEY,
    BOTTOM_RESERVE_TABLE: BOTTOM_RESERVE_TABLE,
    isEmbedded: isEmbedded,
    readFitMode: readFitMode,
    writeFitMode: writeFitMode,
    applyFitTokens: applyFitTokens,
    getBottomReservePx: getBottomReservePx,
    requestLauncherReturn: requestLauncherReturn
  };
})();
