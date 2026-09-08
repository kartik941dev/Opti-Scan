import React, { useRef, useEffect, memo } from 'react';

const TWO_PI = Math.PI * 2;
const THRESHOLD = 0.05;
const TICK_MS = 20;

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;
}

const DotField = memo(({
  dotRadius = 1.5,
  dotSpacing = 14,
  cursorRadius = 500,
  cursorForce = 0.1,
  bulgeOnly = true,
  bulgeStrength = 67,
  glowRadius = 160,
  sparkle = false,
  waveAmplitude = 0,
  gradientFrom = "rgba(96, 165, 250, 0.28)",
  gradientTo = "rgba(20, 184, 166, 0.20)",
  style = {},
  className = ''
}) => {
  const canvasRef = useRef(null);
  const svgRef = useRef(null);
  const glowCircleRef = useRef(null);
  const pointsRef = useRef([]);
  const mouseRef = useRef({ x: -9999, y: -9999, prevX: -9999, prevY: -9999, speed: 0 });
  const rafRef = useRef(null);
  const boundsRef = useRef({ w: 0, h: 0, offsetX: 0, offsetY: 0 });
  const targetOpacityRef = useRef(0);
  const currentOpacityRef = useRef(0);
  const propsRef = useRef({});

  propsRef.current = {
    dotRadius,
    dotSpacing,
    cursorRadius,
    cursorForce,
    bulgeOnly,
    bulgeStrength,
    sparkle,
    waveAmplitude,
    gradientFrom,
    gradientTo
  };

  const recomputeRef = useRef(null);
  const redrawRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const glowCircle = glowCircleRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const reducedMotion = prefersReducedMotion();
    let resizeTimer = null;
    let gradient = null;

    function handleResize() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(setupCanvas, 100);
    }

    function setupCanvas() {
      const parent = canvas.parentElement;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      const isFixed = window.getComputedStyle(parent).position === 'fixed' || canvas.style.position === 'fixed';
      const w = isFixed ? (window.innerWidth || rect.width) : rect.width;
      const h = isFixed ? (window.innerHeight || rect.height) : rect.height;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      boundsRef.current = {
        w,
        h,
        offsetX: isFixed ? 0 : (rect.left + window.scrollX),
        offsetY: isFixed ? 0 : (rect.top + window.scrollY),
        isFixed
      };
      gradient = null;
      buildGrid(w, h);
      triggerRender();
    }

    function buildGrid(w, h) {
      const p = propsRef.current;
      const step = p.dotRadius + p.dotSpacing;
      const cols = Math.floor(w / step);
      const rows = Math.floor(h / step);
      const startX = (w % step) / 2;
      const startY = (h % step) / 2;
      const total = rows * cols;
      const points = new Array(total);
      let idx = 0;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = startX + c * step + step / 2;
          const y = startY + r * step + step / 2;
          points[idx++] = {
            ax: x,
            ay: y,
            sx: x,
            sy: y,
            vx: 0,
            vy: 0,
            x: x,
            y: y
          };
        }
      }
      pointsRef.current = points;
    }

    function onMouseMove(e) {
      const b = boundsRef.current;
      if (b.isFixed) {
        mouseRef.current.x = e.clientX;
        mouseRef.current.y = e.clientY;
      } else {
        mouseRef.current.x = e.pageX - b.offsetX;
        mouseRef.current.y = e.pageY - b.offsetY;
      }
      triggerRender();
    }

    function updateMouseSpeed() {
      const m = mouseRef.current;
      const dx = m.prevX - m.x;
      const dy = m.prevY - m.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      m.speed += (dist - m.speed) * 0.5;
      if (m.speed < 0.001) m.speed = 0;
      m.prevX = m.x;
      m.prevY = m.y;
    }

    let frameCount = 0;
    let isRunning = false;
    let isSettled = false;
    let lag = 0;
    let lastTime = 0;

    function startLoop() {
      if (rafRef.current == null) {
        lastTime = performance.now();
        lag = TICK_MS;
        rafRef.current = requestAnimationFrame(render);
      }
    }

    function triggerRender() {
      isSettled = false;
      if (isRunning) startLoop();
    }

    function stopLoop() {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    }

    function render(now) {
      rafRef.current = requestAnimationFrame(render);
      frameCount++;
      const points = pointsRef.current;
      const m = mouseRef.current;
      const { w, h } = boundsRef.current;
      const p = propsRef.current;
      const len = points.length;
      const waveT = frameCount * 0.02;

      lag += Math.min(Math.max(now - lastTime, 0), 100);
      lastTime = now;
      while (lag >= TICK_MS) {
        lag -= TICK_MS;
        updateMouseSpeed();
      }

      const targetOp = reducedMotion ? 0 : Math.min(m.speed / 5, 1);
      currentOpacityRef.current += (targetOp - currentOpacityRef.current) * 0.06;
      if (currentOpacityRef.current < 0.001) currentOpacityRef.current = 0;

      const op = currentOpacityRef.current;
      targetOpacityRef.current += (op - targetOpacityRef.current) * 0.08;
      if (targetOpacityRef.current < 0.001) targetOpacityRef.current = 0;

      if (glowCircle) {
        glowCircle.setAttribute('cx', m.x);
        glowCircle.setAttribute('cy', m.y);
        glowCircle.style.opacity = targetOpacityRef.current;
      }

      ctx.clearRect(0, 0, w, h);

      if (!gradient) {
        gradient = ctx.createLinearGradient(0, 0, w, h);
        gradient.addColorStop(0, p.gradientFrom);
        gradient.addColorStop(1, p.gradientTo);
      }
      ctx.fillStyle = gradient;

      const cRadius = p.cursorRadius;
      const cRadiusSq = cRadius * cRadius;
      const halfDot = p.dotRadius / 2;
      const isBulge = p.bulgeOnly;
      const hasWave = !reducedMotion && p.waveAmplitude > 0;
      const hasSparkle = !reducedMotion && p.sparkle;
      let settled = !hasWave && !hasSparkle && op === 0 && targetOpacityRef.current === 0;

      ctx.beginPath();
      for (let i = 0; i < len; i++) {
        const pt = points[i];
        const dx = m.x - pt.ax;
        const dy = m.y - pt.ay;
        const distSq = dx * dx + dy * dy;

        if (distSq < cRadiusSq && op > 0.01) {
          const dist = Math.sqrt(distSq) || 1;
          const nx = dx / dist;
          const ny = dy / dist;
          if (isBulge) {
            const factor = 1 - dist / cRadius;
            const bulge = factor * factor * p.bulgeStrength * op;
            pt.sx += (pt.ax - nx * bulge - pt.sx) * 0.15;
            pt.sy += (pt.ay - ny * bulge - pt.sy) * 0.15;
          } else {
            const force = (500 / dist) * (m.speed * p.cursorForce);
            pt.vx -= nx * force;
            pt.vy -= ny * force;
          }
        } else if (isBulge) {
          pt.sx += (pt.ax - pt.sx) * 0.1;
          pt.sy += (pt.ay - pt.sy) * 0.1;
        }

        if (!isBulge) {
          pt.vx *= 0.9;
          pt.vy *= 0.9;
          pt.x = pt.ax + pt.vx;
          pt.y = pt.ay + pt.vy;
          pt.sx += (pt.x - pt.sx) * 0.1;
          pt.sy += (pt.y - pt.sy) * 0.1;
        }

        if (settled && (Math.abs(pt.sx - pt.ax) > THRESHOLD || Math.abs(pt.sy - pt.ay) > THRESHOLD)) {
          settled = false;
        }

        let drawX = pt.sx;
        let drawY = pt.sy;

        if (hasWave) {
          drawY += Math.sin(pt.ax * 0.03 + waveT) * p.waveAmplitude;
          drawX += Math.cos(pt.ay * 0.03 + waveT * 0.7) * (p.waveAmplitude * 0.5);
        }

        if (hasSparkle && ((i * 2654435761 ^ frameCount >> 3) >>> 0) % 100 < 3) {
          ctx.moveTo(drawX + halfDot * 1.8, drawY);
          ctx.arc(drawX, drawY, halfDot * 1.8, 0, TWO_PI);
        } else {
          ctx.moveTo(drawX + halfDot, drawY);
          ctx.arc(drawX, drawY, halfDot, 0, TWO_PI);
        }
      }
      ctx.fill();

      if (settled) {
        isSettled = true;
        stopLoop();
      }
    }

    setupCanvas();
    window.addEventListener('resize', handleResize);
    if (!reducedMotion) {
      window.addEventListener('mousemove', onMouseMove, { passive: true });
    }

    isRunning = true;
    startLoop();

    recomputeRef.current = () => {
      const { w, h } = boundsRef.current;
      if (w > 0 && h > 0) buildGrid(w, h);
      gradient = null;
      triggerRender();
    };

    redrawRef.current = () => {
      gradient = null;
      triggerRender();
    };

    return () => {
      stopLoop();
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', onMouseMove);
    };
  }, []);

  useEffect(() => {
    recomputeRef.current?.();
  }, [dotRadius, dotSpacing]);

  useEffect(() => {
    redrawRef.current?.();
  }, [gradientFrom, gradientTo, cursorRadius, cursorForce, bulgeOnly, bulgeStrength, sparkle, waveAmplitude]);

  return (
    <div
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        overflow: 'hidden',
        ...style
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%'
        }}
      />
      <svg
        ref={svgRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none'
        }}
      >
        <defs>
          <radialGradient id="dot-field-glow">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#0B1020" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle
          ref={glowCircleRef}
          cx="-9999"
          cy="-9999"
          r={glowRadius}
          fill="url(#dot-field-glow)"
          style={{ opacity: 0, willChange: 'opacity' }}
        />
      </svg>
    </div>
  );
});

DotField.displayName = 'DotField';

export default DotField;
