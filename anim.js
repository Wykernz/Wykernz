/* ============================================================================
   BIO-CURSOR — Alien / Futuristic Bio-Interface Pointer
   Author: Senior Creative Frontend Dev
   License: MIT
   ----------------------------------------------------------------------------
   A Canvas2D, 60 FPS, encapsulated custom cursor with:
     • Glowing reticle core with organic pulse
     • Segmented trailing ring (lerp + inertia)
     • Magnetic snap on hover of .interactive elements
     • Shockwave + particle burst on click
     • Auto-disable on touch / reduced-motion
   ========================================================================== */

(() => {
  'use strict';

  /* ==========================================================================
     1. CONFIG — tweak everything here
     ========================================================================== */
  const DEFAULT_CONFIG = {
    // ---- Palette ----
    palette: {
      core:        '#e8fff7',   // bright reticle center
      accent:      '#6effc4',   // alien bio-glow green
      accentSoft:  'rgba(110, 255, 196, 0.35)',
      hover:       '#ff2d95',   // magenta on hover
      shockwave:   'rgba(110, 255, 196, 0.9)',
    },

    // ---- Motion physics ----
    lerp: {
      core:  0.85,   // 0..1 — higher = snappier core
      ring:  0.18,   // 0..1 — trailing ring lag
      trail: 0.12,   // 0..1 — outer aura lag
    },

    // ---- Geometry ----
    size: {
      coreRadius:    3.5,   // px
      ringRadius:    22,    // px (idle)
      ringRadiusHover: 42,  // px (expanded on hover)
      auraRadius:    60,    // px
      ringSegments:  32,    // segments in the trailing ring
    },

    // ---- Visual intensity ----
    glow: {
      coreBlur:  18,
      ringBlur:  10,
      auraAlpha: 0.06,
    },

    // ---- Interaction ----
    hover: {
      magneticPull: 0.35,       // 0..1 — how strongly the ring snaps to target center
      selector: '.interactive, a, button',
    },

    // ---- Effects ----
    particles: {
      burstCount:  18,     // particles per click
      burstSpeed:  6,      // px per frame initial
      burstLife:   55,     // frames
      burstSize:   2.2,    // px
    },

    // ---- Shockwave ----
    shockwave: {
      maxRadius: 140,
      growth:    5,       // px per frame
      fade:      0.035,   // alpha decay per frame
      lineWidth: 2,
    },

    // ---- Performance ----
    maxDPR: 2,            // cap devicePixelRatio to avoid 4K overdraw
    pulseHz: 0.9,         // organic breathing speed
  };

  /* ==========================================================================
     2. UTILITIES
     ========================================================================== */
  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp = (v, min, max) => Math.min(Math.max(v, min), max);
  const rand = (min, max) => min + Math.random() * (max - min);

  /* ==========================================================================
     3. BIO-CURSOR CLASS
     ========================================================================== */
  class BioCursor {
    constructor(userConfig = {}) {
      /* --- Config merge --- */
      this.cfg = this._deepMerge(DEFAULT_CONFIG, userConfig);

      /* --- Environment guards --- */
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const noHover       = window.matchMedia('(hover: none)').matches;
      if (reducedMotion || noHover) {
        this.enabled = false;
        return;
      }
      this.enabled = true;

      /* --- Canvas setup --- */
      this.canvas = document.getElementById('bio-cursor');
      if (!this.canvas) {
        console.warn('[BioCursor] #bio-cursor canvas not found.');
        this.enabled = false;
        return;
      }
      this.ctx = this.canvas.getContext('2d', { alpha: true });

      /* --- State --- */
      // Raw mouse position
      this.mouse   = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
      // Smoothed positions (each layer lerps at its own speed)
      this.core    = { x: this.mouse.x, y: this.mouse.y };
      this.ring    = { x: this.mouse.x, y: this.mouse.y };
      this.aura    = { x: this.mouse.x, y: this.mouse.y };
      // Ring size state (animated)
      this.ringRadius = this.cfg.size.ringRadius;
      // Visibility
      this.visible = false;
      // Magnet target (null = no hover)
      this.magnetTarget = null;
      // Pulse phase
      this.t = 0;
      // Click effects
      this.shockwaves = [];
      this.particles  = [];
      // Cached interactive elements (refreshed periodically)
      this._interactives = [];
      this._refreshInteractives();
      // Time tracking for delta-correct physics
      this._lastTime = performance.now();
      // Hover target cache (throttled)
      this._hitTestAccumulator = 0;

      /* --- Init --- */
      this._resize();
      this._bindEvents();
      document.body.classList.add('bio-cursor-active');

      /* --- Start loop --- */
      this._loop = this._loop.bind(this);
      requestAnimationFrame(this._loop);
    }

    /* ----------------------------------------------------------------
       Config merge (shallow-but-nested enough for our shape)
    ---------------------------------------------------------------- */
    _deepMerge(base, override) {
      const out = {};
      for (const key of Object.keys(base)) {
        if (override[key] && typeof override[key] === 'object' && !Array.isArray(override[key])) {
          out[key] = this._deepMerge(base[key], override[key]);
        } else {
          out[key] = override[key] !== undefined ? override[key] : base[key];
        }
      }
      return out;
    }

    /* ----------------------------------------------------------------
       Cached interactive elements
    ---------------------------------------------------------------- */
    _refreshInteractives() {
      this._interactives = Array.from(document.querySelectorAll(this.cfg.hover.selector))
        .filter(el => el.offsetParent !== null); // visible only
    }

    /* ----------------------------------------------------------------
       Canvas sizing with DPR cap
    ---------------------------------------------------------------- */
    _resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, this.cfg.maxDPR);
      this.dpr = dpr;
      this.width  = window.innerWidth;
      this.height = window.innerHeight;
      this.canvas.width  = Math.floor(this.width  * dpr);
      this.canvas.height = Math.floor(this.height * dpr);
      this.canvas.style.width  = this.width  + 'px';
      this.canvas.style.height = this.height + 'px';
      // Reset transform & scale for DPR
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // Refresh element cache (positions may have shifted)
      this._refreshInteractives();
    }

    /* ----------------------------------------------------------------
       Event binding
    ---------------------------------------------------------------- */
    _bindEvents() {
      // Mouse move
      this._onMove = (e) => {
        this.mouse.x = e.clientX;
        this.mouse.y = e.clientY;
        if (!this.visible) this.visible = true;
      };
      // Click
      this._onDown = (e) => {
        this._spawnShockwave(e.clientX, e.clientY);
        this._spawnParticles(e.clientX, e.clientY);
      };
      // Leave / enter window
      this._onLeave = () => { this.visible = false; };
      this._onEnter = () => { this.visible = true;  };
      // Resize (debounced via rAF)
      let resizeQueued = false;
      this._onResize = () => {
        if (resizeQueued) return;
        resizeQueued = true;
        requestAnimationFrame(() => {
          this._resize();
          resizeQueued = false;
        });
      };

      window.addEventListener('mousemove', this._onMove, { passive: true });
      window.addEventListener('mousedown', this._onDown, { passive: true });
      document.addEventListener('mouseleave', this._onLeave);
      document.addEventListener('mouseenter', this._onEnter);
      window.addEventListener('resize', this._onResize, { passive: true });

      // Refresh element cache on DOM changes (throttled)
      this._mo = new MutationObserver(() => {
        clearTimeout(this._moTimer);
        this._moTimer = setTimeout(() => this._refreshInteractives(), 250);
      });
      this._mo.observe(document.body, { childList: true, subtree: true });
    }

    /* ----------------------------------------------------------------
       Hit test — find interactive under cursor
    ---------------------------------------------------------------- */
    _hitTest(x, y) {
      // Iterate cached list; simple but fast enough for typical pages
      for (let i = 0; i < this._interactives.length; i++) {
        const r = this._interactives[i].getBoundingClientRect();
        if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) {
          return {
            el: this._interactives[i],
            cx: r.left + r.width  / 2,
            cy: r.top  + r.height / 2,
          };
        }
      }
      return null;
    }

    /* ----------------------------------------------------------------
       Effect spawners
    ---------------------------------------------------------------- */
    _spawnShockwave(x, y) {
      this.shockwaves.push({
        x, y,
        r: this.cfg.size.coreRadius,
        alpha: 1,
      });
    }

    _spawnParticles(x, y) {
      const { burstCount, burstSpeed, burstLife, burstSize } = this.cfg.particles;
      for (let i = 0; i < burstCount; i++) {
        const angle = (Math.PI * 2 * i) / burstCount + rand(-0.15, 0.15);
        const speed = rand(burstSpeed * 0.5, burstSpeed);
        this.particles.push({
          x, y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: burstLife,
          maxLife: burstLife,
          size: rand(burstSize * 0.6, burstSize),
        });
      }
    }

    /* ----------------------------------------------------------------
       The render loop
    ---------------------------------------------------------------- */
    _loop(now) {
      const dt = Math.min((now - this._lastTime) / 16.6667, 3); // normalized to 60fps units
      this._lastTime = now;
      this.t += 0.016 * this.cfg.pulseHz;

      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.width, this.height);

      if (!this.visible) {
        requestAnimationFrame(this._loop);
        return;
      }

      /* ----- Hit testing (throttled to every 3 frames) ----- */
      this._hitTestAccumulator += dt;
      if (this._hitTestAccumulator >= 3) {
        this.magnetTarget = this._hitTest(this.mouse.x, this.mouse.y);
        this._hitTestAccumulator = 0;
      }

      /* ----- Compute target position (mouse, or magnet center) ----- */
      let targetX = this.mouse.x;
      let targetY = this.mouse.y;
      if (this.magnetTarget) {
        const pull = this.cfg.hover.magneticPull;
        targetX = lerp(this.mouse.x, this.magnetTarget.cx, pull);
        targetY = lerp(this.mouse.y, this.magnetTarget.cy, pull);
      }

      /* ----- Lerp each layer ----- */
      const L = this.cfg.lerp;
      this.core.x = lerp(this.core.x, targetX, L.core * dt);
      this.core.y = lerp(this.core.y, targetY, L.core * dt);
      this.ring.x = lerp(this.ring.x, targetX, L.ring * dt);
      this.ring.y = lerp(this.ring.y, targetY, L.ring * dt);
      this.aura.x = lerp(this.aura.x, targetX, L.trail * dt);
      this.aura.y = lerp(this.aura.y, targetY, L.trail * dt);

      /* ----- Animate ring radius (grow on hover, breathe otherwise) ----- */
      const hovered = !!this.magnetTarget;
      const targetRadius = hovered
        ? this.cfg.size.ringRadiusHover
        : this.cfg.size.ringRadius;
      this.ringRadius = lerp(this.ringRadius, targetRadius, 0.15 * dt);

      const breathe = 1 + Math.sin(this.t * 2) * 0.04;
      const r = this.ringRadius * breathe;

      const P = this.cfg.palette;

      /* ----- Layer 1: Aura (soft glow halo) ----- */
      const auraGrad = ctx.createRadialGradient(
        this.aura.x, this.aura.y, 0,
        this.aura.x, this.aura.y, this.cfg.size.auraRadius
      );
      auraGrad.addColorStop(0, hovered ? P.hover : P.accent);
      auraGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.globalAlpha = this.cfg.glow.auraAlpha;
      ctx.fillStyle = auraGrad;
      ctx.beginPath();
      ctx.arc(this.aura.x, this.aura.y, this.cfg.size.auraRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;

      /* ----- Layer 2: Trailing segmented ring ----- */
      const segments = this.cfg.size.ringSegments;
      const ringColor = hovered ? P.hover : P.accent;
      ctx.strokeStyle = ringColor;
      ctx.lineWidth = 1.2;
      ctx.shadowColor = ringColor;
      ctx.shadowBlur = this.cfg.glow.ringBlur;
      ctx.beginPath();
      for (let i = 0; i < segments; i++) {
        // Rotate slowly; add a "tail" fade toward the back
        const a = (i / segments) * Math.PI * 2 + this.t * 0.4;
        // Segment length pulses — creates the "bio" feel
        const segLen = 0.06 + Math.sin(this.t * 3 + i * 0.5) * 0.02;
        ctx.moveTo(
          this.ring.x + Math.cos(a) * r,
          this.ring.y + Math.sin(a) * r
        );
        ctx.lineTo(
          this.ring.x + Math.cos(a + segLen) * r,
          this.ring.y + Math.sin(a + segLen) * r
        );
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      /* ----- Layer 3: Core reticle ----- */
      const coreR = this.cfg.size.coreRadius * breathe;
      ctx.fillStyle = P.core;
      ctx.shadowColor = hovered ? P.hover : P.accent;
      ctx.shadowBlur = this.cfg.glow.coreBlur;
      ctx.beginPath();
      ctx.arc(this.core.x, this.core.y, coreR, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Crosshair ticks
      ctx.strokeStyle = hovered ? P.hover : P.accent;
      ctx.lineWidth = 1;
      const tick = coreR + 4;
      const tickLen = 4;
      const dirs = [[1,0],[-1,0],[0,1],[0,-1]];
      ctx.beginPath();
      for (const [dx, dy] of dirs) {
        ctx.moveTo(this.core.x + dx * tick,        this.core.y + dy * tick);
        ctx.lineTo(this.core.x + dx * (tick+tickLen), this.core.y + dy * (tick+tickLen));
      }
      ctx.stroke();

      /* ----- Layer 4: Shockwaves ----- */
      for (let i = this.shockwaves.length - 1; i >= 0; i--) {
        const s = this.shockwaves[i];
        s.r += this.cfg.shockwave.growth * dt;
        s.alpha -= this.cfg.shockwave.fade * dt;
        if (s.alpha <= 0 || s.r > this.cfg.shockwave.maxRadius) {
          this.shockwaves.splice(i, 1);
          continue;
        }
        ctx.globalAlpha = s.alpha;
        ctx.strokeStyle = P.shockwave;
        ctx.lineWidth = this.cfg.shockwave.lineWidth * s.alpha;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.stroke();
        // Inner echo ring
        ctx.globalAlpha = s.alpha * 0.5;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * 0.7, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      /* ----- Layer 5: Particles ----- */
      for (let i = this.particles.length - 1; i >= 0; i--) {
        const p = this.particles[i];
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vx *= 0.94;   // friction
        p.vy *= 0.94;
        p.life -= dt;
        if (p.life <= 0) {
          this.particles.splice(i, 1);
          continue;
        }
        const lifeRatio = p.life / p.maxLife;
        ctx.globalAlpha = lifeRatio;
        ctx.fillStyle = hovered ? P.hover : P.accent;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * lifeRatio, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      requestAnimationFrame(this._loop);
    }

    /* ----------------------------------------------------------------
       Public API
    ---------------------------------------------------------------- */
    destroy() {
      window.removeEventListener('mousemove', this._onMove);
      window.removeEventListener('mousedown', this._onDown);
      document.removeEventListener('mouseleave', this._onLeave);
      document.removeEventListener('mouseenter', this._onEnter);
      window.removeEventListener('resize', this._onResize);
      if (this._mo) this._mo.disconnect();
      document.body.classList.remove('bio-cursor-active');
      if (this.ctx) this.ctx.clearRect(0, 0, this.width, this.height);
      this.enabled = false;
    }

    setConfig(partial) {
      this.cfg = this._deepMerge(this.cfg, partial);
    }

    refreshTargets() {
      this._refreshInteractives();
    }
  }

  /* ==========================================================================
     4. EXPORT
     ========================================================================== */
  window.BioCursor = BioCursor;

})();