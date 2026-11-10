(function () {
  "use strict";

  var root = typeof window !== "undefined" ? window : globalThis;
  var audioCtx = null;
  var muted = false;

  function ensureContext() {
    if (muted) return null;
    try {
      var Ctx = root.AudioContext || root.webkitAudioContext;
      if (!Ctx) return null;
      if (!audioCtx) {
        audioCtx = new Ctx();
      }
      if (audioCtx.state === "suspended" || audioCtx.state === "interrupted") {
        var p = audioCtx.resume();
        if (p && typeof p.catch === "function") {
          p.catch(function () {});
        }
      }
      return audioCtx;
    } catch (e) {
      return null;
    }
  }

  function playTone(freqStart, freqEnd, durationSec, waveType, gainPeak, delaySec) {
    var ctx = ensureContext();
    if (!ctx) return;
    try {
      var startAt = ctx.currentTime + (delaySec || 0);
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.type = waveType || "triangle";
      osc.frequency.setValueAtTime(freqStart, startAt);
      if (freqEnd && freqEnd !== freqStart) {
        osc.frequency.exponentialRampToValueAtTime(Math.max(20, freqEnd), startAt + durationSec);
      }
      gain.gain.setValueAtTime(0.0001, startAt);
      gain.gain.linearRampToValueAtTime(gainPeak || 0.08, startAt + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, startAt + durationSec);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(startAt);
      osc.stop(startAt + durationSec + 0.02);
    } catch (e) {
      // Ignore WebView audio errors safely
    }
  }

  function playSfx(key) {
    if (muted) return;
    switch (key) {
      case "pour":
        playTone(320, 480, 0.08, "sine", 0.07, 0);
        break;
      case "flip":
        playTone(440, 620, 0.07, "triangle", 0.08, 0);
        break;
      case "harvest":
        playTone(580, 860, 0.1, "triangle", 0.09, 0);
        break;
      case "clean":
        playTone(240, 180, 0.08, "sawtooth", 0.05, 0);
        break;
      case "serve":
        playTone(660, 880, 0.09, "triangle", 0.09, 0);
        playTone(880, 1180, 0.12, "triangle", 0.08, 0.07);
        break;
      case "burn":
        playTone(190, 95, 0.2, "sawtooth", 0.08, 0);
        break;
      case "inspect":
        playTone(740, 740, 0.1, "square", 0.06, 0);
        playTone(560, 560, 0.12, "square", 0.06, 0.11);
        break;
      case "chapter_clear":
        playTone(523, 659, 0.12, "triangle", 0.09, 0);
        playTone(659, 784, 0.12, "triangle", 0.09, 0.11);
        playTone(784, 1046, 0.22, "triangle", 0.1, 0.22);
        break;
      case "bailout":
        playTone(440, 660, 0.14, "sine", 0.08, 0);
        playTone(660, 880, 0.16, "sine", 0.08, 0.12);
        break;
      case "fever":
        playTone(587, 880, 0.11, "triangle", 0.09, 0);
        playTone(880, 1174, 0.16, "triangle", 0.1, 0.1);
        break;
      default:
        playTone(500, 680, 0.07, "triangle", 0.07, 0);
        break;
    }
  }

  function setMuted(nextMuted) {
    muted = Boolean(nextMuted);
  }

  function isMuted() {
    return muted;
  }

  if (root.document && typeof root.document.addEventListener === "function") {
    root.document.addEventListener("pointerdown", function () {
      ensureContext();
    }, { passive: true });
  }

  root.TycoonAudio = {
    playSfx: playSfx,
    setMuted: setMuted,
    isMuted: isMuted
  };
})();
