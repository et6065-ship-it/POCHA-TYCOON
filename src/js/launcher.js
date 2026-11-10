/**
 * Unified Mobile WebApp Launcher Host Controller
 * Manages <iframe allow="fullscreen"> stage, 3-section options modal, and throttled procedural previews.
 */
(function () {
  'use strict';

  // 1. Legacy ?game=janggi|chess deep-link forwarder
  try {
    var initParams = new URLSearchParams(window.location.search);
    var legacyGame = (initParams.get('game') || '').toUpperCase();
    if (legacyGame === 'JANGGI') {
      window.location.replace('./janggi.html');
      return;
    }
    if (legacyGame === 'CHESS') {
      window.location.replace('./chess.html');
      return;
    }
  } catch (e) {}

  // Clear stale stage history entry on fresh reload
  try {
    if (window.history.state && window.history.state.launcherStage) {
      window.history.replaceState(null, '');
    }
  } catch (e) {}

  var bodyEl = document.body;
  var btnOptions = document.getElementById('btn-launcher-options');
  var modalBackdrop = document.getElementById('launcher-options-modal');
  var btnCloseModal = document.getElementById('btn-close-options-modal');
  var fitButtons = document.querySelectorAll('[data-fit-choice]');
  var fsContainer = document.getElementById('opt-fullscreen-area');
  var pwaContainer = document.getElementById('opt-pwa-area');
  var stageOverlay = document.getElementById('launcher-stage-overlay');
  var toastEl = document.getElementById('launcher-toast');

  var jCvs = document.getElementById('preview-canvas-janggi');
  var cCvs = document.getElementById('preview-canvas-chess');
  var bCvs = document.getElementById('preview-canvas-blockblast');
  var pCvs = document.getElementById('preview-canvas-pocha');

  var activeStageFrame = null;
  var lastFocusedLauncherEl = null;
  var deferredInstallPrompt = null;
  var toastTimer = null;
  var rafId = null;
  var lastStepTime = 0;

  function detectEnv() {
    var ua = (navigator && navigator.userAgent) || '';
    var isStandalone = false;
    try {
      isStandalone =
        (window.matchMedia && window.matchMedia('(display-mode: standalone), (display-mode: fullscreen)').matches) ||
        navigator.standalone === true;
    } catch (e) {}
    var isIOS = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    var isAndroid = /Android/i.test(ua);
    var isKakao = /KAKAOTALK/i.test(ua);
    var isInApp = isKakao || /NAVER|Instagram|FBAN|FBAV|Line|;\s*wv\)/i.test(ua);
    var docEl = document.documentElement;
    var fullscreenSupported = Boolean(
      (document.fullscreenEnabled || document.webkitFullscreenEnabled) &&
      (docEl.requestFullscreen || docEl.webkitRequestFullscreen)
    );
    return {
      isStandalone: isStandalone,
      isIOS: isIOS,
      isAndroid: isAndroid,
      isKakao: isKakao,
      isInApp: isInApp,
      fullscreenSupported: fullscreenSupported
    };
  }

  function showToast(msg, isError) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.toggle('error', Boolean(isError));
    toastEl.classList.add('visible');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.classList.remove('visible');
    }, 3400);
  }

  function isFullscreenActive() {
    return Boolean(document.fullscreenElement || document.webkitFullscreenElement);
  }

  /* =========================================================================
     <iframe allow="fullscreen"> Host Stage Lifecycle
     ========================================================================= */
  function openGameStage(gameId, rawHref, triggerEl) {
    if (activeStageFrame) {
      unmountGameStage(false);
    }
    lastFocusedLauncherEl = triggerEl || document.activeElement;
    stopPreviewLoop();

    var fitMode = window.LauncherCommon ? window.LauncherCommon.readFitMode() : 0;
    var sep = rawHref.indexOf('?') === -1 ? '?' : '&';
    var frameSrc = rawHref + sep + 'fit=' + encodeURIComponent(String(fitMode));

    var frame = document.createElement('iframe');
    frame.className = 'launcher-stage-frame';
    frame.id = 'game-stage-frame';
    frame.setAttribute('allow', 'fullscreen; autoplay');
    frame.setAttribute('title', gameId + ' 게임 화면');
    frame.src = frameSrc;

    stageOverlay.innerHTML = '';
    stageOverlay.appendChild(frame);
    stageOverlay.classList.add('active');
    stageOverlay.setAttribute('aria-hidden', 'false');
    bodyEl.classList.add('stage-open');
    activeStageFrame = frame;

    try {
      window.history.pushState({ launcherStage: gameId }, '');
    } catch (e) {}
  }

  function unmountGameStage(restoreFocus) {
    if (activeStageFrame) {
      try {
        activeStageFrame.remove();
      } catch (e) {
        if (activeStageFrame.parentNode) {
          activeStageFrame.parentNode.removeChild(activeStageFrame);
        }
      }
      activeStageFrame = null;
    }
    if (stageOverlay) {
      stageOverlay.innerHTML = '';
      stageOverlay.classList.remove('active');
      stageOverlay.setAttribute('aria-hidden', 'true');
    }
    bodyEl.classList.remove('stage-open');
    if (restoreFocus !== false && lastFocusedLauncherEl && lastFocusedLauncherEl.focus) {
      try {
        lastFocusedLauncherEl.focus();
      } catch (e) {}
    }
    syncPreviewLoopState();
  }

  document.querySelectorAll('.game-card[data-game-id]').forEach(function (card) {
    card.addEventListener('click', function (e) {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return;
      e.preventDefault();
      var gameId = card.getAttribute('data-game-id');
      var href = card.getAttribute('href');
      if (gameId && href) {
        openGameStage(gameId, href, card);
      }
    });
  });

  window.addEventListener('popstate', function () {
    if (activeStageFrame) {
      unmountGameStage(true);
    }
  });

  window.addEventListener('message', function (e) {
    if (!e || !e.data || e.data.type !== 'LAUNCHER_RETURN') return;
    if (!activeStageFrame || e.source !== activeStageFrame.contentWindow) return;
    var validOrigin = e.origin === window.location.origin || window.location.protocol === 'file:';
    if (!validOrigin) return;

    if (window.history.state && window.history.state.launcherStage) {
      window.history.back();
    } else {
      unmountGameStage(true);
    }
  });

  /* =========================================================================
     Single Options Modal (1. Fit Mode / 2. Fullscreen / 3. Home Screen App)
     ========================================================================= */
  function syncFitButtonsUI() {
    var mode = window.LauncherCommon ? window.LauncherCommon.readFitMode() : 0;
    fitButtons.forEach(function (btn) {
      var val = parseInt(btn.getAttribute('data-fit-choice'), 10);
      var isSelected = val === mode;
      btn.classList.toggle('active', isSelected);
      btn.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
    });
  }

  fitButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var choice = parseInt(btn.getAttribute('data-fit-choice'), 10) || 0;
      if (window.LauncherCommon) {
        window.LauncherCommon.writeFitMode(choice);
      }
      syncFitButtonsUI();
      var names = ['최대 (기본 화면)', '보통 (하단바 여유 확보)', '축소 (하단 여유 최대)'];
      showToast('📐 화면 크기가 [' + names[choice] + '] 단계로 적용되었습니다.');
    });
  });

  function renderFullscreenOption() {
    if (!fsContainer) return;
    fsContainer.innerHTML = '';
    var env = detectEnv();

    if (env.isStandalone) {
      var pill = document.createElement('div');
      pill.className = 'opt-status-pill';
      pill.textContent = '✔ 현재 전용앱 전체화면 모드로 실행 중입니다';
      fsContainer.appendChild(pill);
      return;
    }

    if (!env.fullscreenSupported) {
      var unsupported = document.createElement('div');
      unsupported.className = 'opt-status-pill muted';
      unsupported.textContent = '현재 브라우저(iOS Safari 등)는 탭 전체화면을 지원하지 않습니다. 아래 [홈 화면 앱 설치]로 추가하면 상·하단 바 없는 전체화면으로 실행됩니다.';
      fsContainer.appendChild(unsupported);
      return;
    }

    var fsBtn = document.createElement('button');
    fsBtn.type = 'button';
    fsBtn.className = 'opt-action-btn gold';
    var active = isFullscreenActive();
    fsBtn.textContent = active ? '⛶ 전체화면 해제' : '⛶ 전체화면 켜기';
    fsBtn.addEventListener('click', function () {
      var docEl = document.documentElement;
      if (!isFullscreenActive()) {
        var req = docEl.requestFullscreen
          ? docEl.requestFullscreen()
          : (docEl.webkitRequestFullscreen ? docEl.webkitRequestFullscreen() : null);
        if (req && typeof req.then === 'function') {
          req.then(function () {
            renderFullscreenOption();
            showToast('⛶ 전체화면 모드가 켜졌습니다. 게임을 실행해도 유지됩니다.');
          }).catch(function () {
            renderFullscreenOption();
            showToast('전체화면 전환이 브라우저에 의해 거부되었습니다.', true);
          });
        } else {
          setTimeout(renderFullscreenOption, 120);
        }
      } else {
        var exit = document.exitFullscreen
          ? document.exitFullscreen()
          : (document.webkitExitFullscreen ? document.webkitExitFullscreen() : null);
        if (exit && typeof exit.then === 'function') {
          exit.then(function () {
            renderFullscreenOption();
            showToast('⛶ 전체화면 모드를 해제했습니다.');
          }).catch(function () {
            renderFullscreenOption();
          });
        } else {
          setTimeout(renderFullscreenOption, 120);
        }
      }
    });
    fsContainer.appendChild(fsBtn);
  }

  document.addEventListener('fullscreenchange', renderFullscreenOption);
  document.addEventListener('webkitfullscreenchange', renderFullscreenOption);

  function openExternalBrowser() {
    var rootUrl = new URL('./', window.location.href).href;
    var env = detectEnv();
    if (env.isKakao) {
      window.location.href = 'kakaotalk://web/openExternal?url=' + encodeURIComponent(rootUrl);
      return;
    }
    if (env.isAndroid) {
      var noScheme = rootUrl.replace(/^https?:\/\//i, '');
      var scheme = rootUrl.indexOf('https://') === 0 ? 'https' : 'http';
      window.location.href =
        'intent://' + noScheme + '#Intent;scheme=' + scheme +
        ';S.browser_fallback_url=' + encodeURIComponent(rootUrl) + ';end';
      return;
    }
    copyRootUrl();
  }

  function copyRootUrl() {
    var rootUrl = new URL('./', window.location.href).href;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(rootUrl).then(function () {
        showToast('📋 런처 주소가 복사되었습니다. 기본 브라우저에 붙여넣어 열어주세요.');
      }).catch(function () {
        window.prompt('아래 주소를 복사해 Safari 또는 Chrome에서 열어주세요:', rootUrl);
      });
    } else {
      window.prompt('아래 주소를 복사해 Safari 또는 Chrome에서 열어주세요:', rootUrl);
    }
  }

  function renderPwaOption() {
    if (!pwaContainer) return;
    pwaContainer.innerHTML = '';
    var env = detectEnv();

    if (env.isStandalone) {
      var donePill = document.createElement('div');
      donePill.className = 'opt-status-pill';
      donePill.textContent = '✔ 홈 화면 전용앱으로 설치되어 실행 중입니다';
      pwaContainer.appendChild(donePill);
      return;
    }

    if (deferredInstallPrompt) {
      var installBtn = document.createElement('button');
      installBtn.type = 'button';
      installBtn.className = 'opt-action-btn';
      installBtn.textContent = '📲 홈 화면에 전용앱 바로 설치';
      installBtn.addEventListener('click', function () {
        var promptEvent = deferredInstallPrompt;
        deferredInstallPrompt = null;
        promptEvent.prompt();
        promptEvent.userChoice.then(function (choice) {
          renderPwaOption();
          if (choice && choice.outcome === 'accepted') {
            showToast('🎉 홈 화면에 전용 게임 앱이 추가되었습니다.');
          }
        }).catch(function () {
          renderPwaOption();
        });
      });
      pwaContainer.appendChild(installBtn);
      return;
    }

    if (env.isInApp) {
      var guide = document.createElement('p');
      guide.className = 'opt-desc';
      guide.textContent = env.isIOS && !env.isKakao
        ? '인앱 브라우저에서는 앱 설치가 제한됩니다. 주소를 복사해 Safari에서 연 뒤 [공유(↑) → 홈 화면에 추가]를 선택하세요.'
        : '인앱 브라우저에서는 상·하단 바 제거 앱 설치가 제한됩니다. 외부 브라우저로 전환한 뒤 홈 화면에 추가하세요.';
      pwaContainer.appendChild(guide);

      var row = document.createElement('div');
      row.className = 'opt-btn-row';
      if (env.isAndroid || env.isKakao) {
        var extBtn = document.createElement('button');
        extBtn.type = 'button';
        extBtn.className = 'opt-action-btn gold';
        extBtn.textContent = '🚀 외부 브라우저로 열기';
        extBtn.addEventListener('click', openExternalBrowser);
        row.appendChild(extBtn);
      }
      var copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.className = 'opt-action-btn';
      copyBtn.textContent = '📋 주소 복사';
      copyBtn.addEventListener('click', copyRootUrl);
      row.appendChild(copyBtn);
      pwaContainer.appendChild(row);
      return;
    }

    var manual = document.createElement('div');
    manual.className = 'opt-status-pill muted';
    manual.textContent = env.isIOS
      ? 'Safari 하단 [공유(↑)] 버튼 → [홈 화면에 추가]를 누르면 전용앱으로 설치됩니다.'
      : '브라우저 우측 상단 메뉴(⋮) → [앱 설치] 또는 [홈 화면에 추가]를 선택하세요.';
    pwaContainer.appendChild(manual);
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferredInstallPrompt = e;
    renderPwaOption();
  });

  window.addEventListener('appinstalled', function () {
    deferredInstallPrompt = null;
    renderPwaOption();
  });

  function openOptionsModal() {
    if (!modalBackdrop) return;
    syncFitButtonsUI();
    renderFullscreenOption();
    renderPwaOption();
    modalBackdrop.classList.add('active');
    modalBackdrop.setAttribute('aria-hidden', 'false');
    if (btnOptions) btnOptions.setAttribute('aria-expanded', 'true');
    bodyEl.classList.add('modal-open');
    syncPreviewLoopState();
    if (btnCloseModal) {
      try { btnCloseModal.focus(); } catch (e) {}
    }
  }

  function closeOptionsModal() {
    if (!modalBackdrop || !modalBackdrop.classList.contains('active')) return;
    modalBackdrop.classList.remove('active');
    modalBackdrop.setAttribute('aria-hidden', 'true');
    if (btnOptions) {
      btnOptions.setAttribute('aria-expanded', 'false');
      try { btnOptions.focus(); } catch (e) {}
    }
    bodyEl.classList.remove('modal-open');
    syncPreviewLoopState();
  }

  if (btnOptions) {
    btnOptions.addEventListener('click', openOptionsModal);
  }
  if (btnCloseModal) {
    btnCloseModal.addEventListener('click', closeOptionsModal);
  }
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', function (e) {
      if (e.target === modalBackdrop) closeOptionsModal();
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modalBackdrop && modalBackdrop.classList.contains('active')) {
      closeOptionsModal();
    }
  });

  /* =========================================================================
     Lightweight Procedural 2D Canvas Previews (Zero External Sprite Bundle)
     ========================================================================= */
  var scale = Math.min(window.devicePixelRatio || 1, 2);
  [jCvs, cCvs, bCvs, pCvs].forEach(function (cvs) {
    if (cvs) {
      cvs.width = Math.round(220 * scale);
      cvs.height = Math.round(132 * scale);
    }
  });

  function drawOctagonPiece(ctx, cx, cy, r, bg, border, label, textColor) {
    ctx.save();
    ctx.beginPath();
    for (var i = 0; i < 8; i++) {
      var ang = (Math.PI / 4) * i + Math.PI / 8;
      var px = cx + Math.cos(ang) * r;
      var py = cy + Math.sin(ang) * r;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = bg;
    ctx.fill();
    ctx.lineWidth = 2.2;
    ctx.strokeStyle = border;
    ctx.stroke();

    ctx.fillStyle = textColor;
    ctx.font = '900 ' + Math.round(r * 1.05) + 'px serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, cx, cy + 1);
    ctx.restore();
  }

  function drawJanggiPreview(ctx, now) {
    ctx.clearRect(0, 0, 220, 132);
    // Wooden palace grid
    ctx.fillStyle = '#3b2514';
    ctx.fillRect(28, 22, 164, 88);
    ctx.strokeStyle = '#d97706';
    ctx.lineWidth = 2;
    ctx.strokeRect(28, 22, 164, 88);

    ctx.strokeStyle = 'rgba(253, 224, 71, 0.32)';
    ctx.lineWidth = 1;
    for (var gx = 55; gx < 190; gx += 27) {
      ctx.beginPath();
      ctx.moveTo(gx, 22);
      ctx.lineTo(gx, 110);
      ctx.stroke();
    }
    for (var gy = 44; gy < 110; gy += 22) {
      ctx.beginPath();
      ctx.moveTo(28, gy);
      ctx.lineTo(192, gy);
      ctx.stroke();
    }
    // Palace diagonal
    ctx.beginPath();
    ctx.moveTo(82, 22);
    ctx.lineTo(136, 66);
    ctx.moveTo(136, 22);
    ctx.lineTo(82, 66);
    ctx.stroke();

    var bob = Math.sin(now * 0.006) * 2.5;
    drawOctagonPiece(ctx, 68, 68 + bob, 19, '#064e3b', '#34d399', '車', '#6ee7b7');
    drawOctagonPiece(ctx, 110, 48 - bob * 0.6, 21, '#1e293b', '#fbbf24', '將', '#fde047');
    drawOctagonPiece(ctx, 152, 68 - bob, 19, '#7f1d1d', '#f87171', '包', '#fecaca');

    ctx.fillStyle = '#fde047';
    ctx.font = '800 10.5px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('⚔️ 궁성 · 포 다리 · 4대 문명 대국', 110, 123);
  }

  function drawChessPreview(ctx, now) {
    ctx.clearRect(0, 0, 220, 132);
    var cell = 20;
    var cols = 8;
    var rows = 4;
    var sx = 30;
    var sy = 24;
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        ctx.fillStyle = (r + c) % 2 === 0 ? '#334155' : '#0f172a';
        ctx.fillRect(sx + c * cell, sy + r * cell, cell, cell);
      }
    }
    ctx.strokeStyle = '#f87171';
    ctx.lineWidth = 2;
    ctx.strokeRect(sx, sy, cols * cell, rows * cell);

    var pulse = Math.sin(now * 0.006) * 2.5;
    // White Queen crest
    ctx.fillStyle = '#1e3a8a';
    ctx.strokeStyle = '#93c5fd';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(76, 64 + pulse, 18, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#fef08a';
    ctx.font = '900 22px serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('♛', 76, 65 + pulse);

    // Black Knight crest
    ctx.fillStyle = '#4c1d95';
    ctx.strokeStyle = '#f472b6';
    ctx.beginPath();
    ctx.arc(144, 64 - pulse, 18, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#fbcfe8';
    ctx.fillText('♞', 144, 65 - pulse);

    ctx.fillStyle = '#fca5a5';
    ctx.font = '800 10.5px sans-serif';
    ctx.textBaseline = 'alphabetic';
    ctx.fillText('♛ 캐슬링 · 앙파상 · 프로모션', 110, 123);
  }

  function drawBlockBlastPreview(ctx, now) {
    ctx.clearRect(0, 0, 220, 132);
    var cell = 16;
    var cols = 6;
    var rows = 5;
    var startX = Math.floor((220 - cols * cell) * 0.5);
    var startY = 24;

    ctx.fillStyle = '#070a12';
    ctx.fillRect(startX - 4, startY - 4, cols * cell + 8, rows * cell + 8);
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2;
    ctx.strokeRect(startX - 4, startY - 4, cols * cell + 8, rows * cell + 8);

    var demoGrid = [
      [0, 0, 3, 0, 0, 0],
      [1, 1, 3, 0, 5, 5],
      [4, 4, 4, 4, 4, 4],
      [2, 2, 0, 6, 6, 6],
      [2, 0, 0, 0, 1, 1]
    ];
    var colors = {
      1: { base: '#e11d48', hi: '#fda4af' },
      2: { base: '#059669', hi: '#6ee7b7' },
      3: { base: '#2563eb', hi: '#93c5fd' },
      4: { base: '#d97706', hi: '#fef08a' },
      5: { base: '#7c3aed', hi: '#d8b4fe' },
      6: { base: '#0891b2', hi: '#a5f3fc' }
    };
    var highlight = Math.sin(now * 0.012) > 0;

    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var x = startX + c * cell;
        var y = startY + r * cell;
        ctx.fillStyle = (r + c) % 2 === 0 ? '#111728' : '#0d1322';
        ctx.fillRect(x + 1, y + 1, cell - 2, cell - 2);
        var v = demoGrid[r][c];
        if (v) {
          var pal = colors[v];
          ctx.fillStyle = r === 2 && highlight ? pal.hi : pal.base;
          ctx.fillRect(x + 1, y + 1, cell - 2, cell - 2);
        }
      }
    }

    ctx.fillStyle = '#bae6fd';
    ctx.font = '800 10.5px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('💎 8×8 보석 줄 완성 · 콤보 퍼즐', 110, 123);
  }

  function drawPochaPreview(ctx, now) {
    ctx.clearRect(0, 0, 220, 132);
    ctx.fillStyle = '#dc2626';
    ctx.fillRect(26, 20, 168, 15);
    ctx.fillStyle = '#fef08a';
    for (var i = 0; i < 8; i++) {
      if (i % 2 === 0) ctx.fillRect(26 + i * 21, 20, 21, 15);
    }

    ctx.fillStyle = '#1e293b';
    ctx.strokeStyle = '#64748b';
    ctx.lineWidth = 2;
    ctx.fillRect(34, 40, 98, 64);
    ctx.strokeRect(34, 40, 98, 64);

    var bob = Math.sin(now * 0.006) * 1.5;
    for (var r = 0; r < 2; r++) {
      for (var c = 0; c < 3; c++) {
        var fx = 52 + c * 31;
        var fy = 57 + r * 29;
        ctx.fillStyle = (r + c) % 2 === 0 ? '#f59e0b' : '#fbbf24';
        ctx.beginPath();
        ctx.ellipse(fx, fy + bob, 10.5, 6.5, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.fillStyle = '#1e3a8a';
    ctx.strokeStyle = '#fbbf24';
    ctx.fillRect(144, 38, 42, 66);
    ctx.strokeRect(144, 38, 42, 66);
    ctx.fillStyle = '#fde047';
    for (var fl = 0; fl < 5; fl++) {
      ctx.fillRect(150, 43 + fl * 12, 30, 6);
    }

    ctx.fillStyle = '#fde047';
    ctx.font = '800 10.5px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('🐟 포차 ➔ 트럭 ➔ 강남 빌딩', 110, 123);
  }

  function renderPreviewsOnce(now) {
    if (jCvs) {
      var jCtx = jCvs.getContext('2d');
      jCtx.setTransform(scale, 0, 0, scale, 0, 0);
      drawJanggiPreview(jCtx, now);
    }
    if (cCvs) {
      var cCtx = cCvs.getContext('2d');
      cCtx.setTransform(scale, 0, 0, scale, 0, 0);
      drawChessPreview(cCtx, now);
    }
    if (bCvs) {
      var bCtx = bCvs.getContext('2d');
      bCtx.setTransform(scale, 0, 0, scale, 0, 0);
      drawBlockBlastPreview(bCtx, now);
    }
    if (pCvs) {
      var pCtx = pCvs.getContext('2d');
      pCtx.setTransform(scale, 0, 0, scale, 0, 0);
      drawPochaPreview(pCtx, now);
    }
  }

  function shouldAnimatePreviews() {
    if (document.hidden) return false;
    if (activeStageFrame) return false;
    if (modalBackdrop && modalBackdrop.classList.contains('active')) return false;
    return true;
  }

  function previewTick(now) {
    rafId = null;
    if (!shouldAnimatePreviews()) return;
    if (!lastStepTime || now - lastStepTime >= 110) {
      lastStepTime = now;
      renderPreviewsOnce(now);
    }
    rafId = window.requestAnimationFrame(previewTick);
  }

  function stopPreviewLoop() {
    if (rafId !== null) {
      window.cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function syncPreviewLoopState() {
    if (shouldAnimatePreviews()) {
      if (rafId === null) {
        rafId = window.requestAnimationFrame(previewTick);
      }
    } else {
      stopPreviewLoop();
    }
  }

  document.addEventListener('visibilitychange', syncPreviewLoopState);
  renderPreviewsOnce(0);
  syncPreviewLoopState();
})();
