import { useEffect, useRef } from "preact/hooks";

interface GridPoint {
  originX: number;
  originY: number;
  currentX: number;
  currentY: number;
  vx: number;
  vy: number;
}

export function ArchitecturalCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    let mouseX = -1000;
    let mouseY = -1000;
    let targetMouseX = -1000;
    let targetMouseY = -1000;
    let isMouseActive = false;

    const spacing = 40;
    let points: GridPoint[] = [];

    const initGrid = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      points = [];
      const cols = Math.ceil(width / spacing) + 1;
      const rows = Math.ceil(height / spacing) + 1;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = c * spacing;
          const y = r * spacing;
          points.push({
            originX: x,
            originY: y,
            currentX: x,
            currentY: y,
            vx: 0,
            vy: 0,
          });
        }
      }
    };

    initGrid();

    const handleResize = () => {
      initGrid();
    };

    const handlePointerMove = (e: PointerEvent) => {
      targetMouseX = e.clientX;
      targetMouseY = e.clientY;
      isMouseActive = true;
    };

    const handlePointerLeave = () => {
      isMouseActive = false;
      targetMouseX = -1000;
      targetMouseY = -1000;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("pointermove", handlePointerMove);
    document.addEventListener("pointerleave", handlePointerLeave);

    const radius = 130;
    const springStrength = 0.08;
    const damping = 0.82;

    const render = () => {
      // Smooth mouse coordinate interpolation
      mouseX += (targetMouseX - mouseX) * 0.2;
      mouseY += (targetMouseY - mouseY) * 0.2;

      ctx.clearRect(0, 0, width, height);

      // Draw subtle architectural drafting marks and points
      for (const p of points) {

        if (!prefersReducedMotion && isMouseActive) {
          const dx = mouseX - p.currentX;
          const dy = mouseY - p.currentY;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < radius && dist > 0) {
            const force = (1 - dist / radius) * 14;
            const angle = Math.atan2(dy, dx);
            p.vx -= Math.cos(angle) * force;
            p.vy -= Math.sin(angle) * force;
          }
        }

        // Spring back to origin
        p.vx += (p.originX - p.currentX) * springStrength;
        p.vy += (p.originY - p.currentY) * springStrength;
        p.vx *= damping;
        p.vy *= damping;
        p.currentX += p.vx;
        p.currentY += p.vy;

        // Proximity illumination calculation
        let alpha = 0.12;
        let pointSize = 1.0;
        let isProximity = false;

        if (isMouseActive) {
          const dx = mouseX - p.currentX;
          const dy = mouseY - p.currentY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < radius * 1.5) {
            isProximity = true;
            const proximity = 1 - dist / (radius * 1.5);
            alpha = 0.15 + proximity * 0.65;
            pointSize = 1.0 + proximity * 1.8;
          }
        }

        ctx.fillStyle = isProximity
          ? `rgba(59, 130, 246, ${alpha})`
          : `rgba(148, 163, 184, ${alpha})`;
        ctx.beginPath();
        ctx.arc(p.currentX, p.currentY, pointSize, 0, Math.PI * 2);
        ctx.fill();
      }

      // If mouse is active, render subtle precision architectural crosshairs
      if (isMouseActive && mouseX > 0 && mouseX < width && mouseY > 0 && mouseY < height) {
        ctx.strokeStyle = "rgba(59, 130, 246, 0.22)";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 6]);

        // Horizontal hairline
        ctx.beginPath();
        ctx.moveTo(0, mouseY);
        ctx.lineTo(width, mouseY);
        ctx.stroke();

        // Vertical hairline
        ctx.beginPath();
        ctx.moveTo(mouseX, 0);
        ctx.lineTo(mouseX, height);
        ctx.stroke();

        ctx.setLineDash([]);

        // Small technical coordinate readout badge near cursor
        const coordText = `ATELIER [${Math.round(mouseX)}, ${Math.round(mouseY)}]`;
        ctx.font = "9px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace";
        ctx.fillStyle = "rgba(148, 163, 184, 0.75)";
        ctx.fillText(coordText, mouseX + 12, mouseY - 10);
      }

      animationFrameId = requestAnimationFrame(render);
    };

    // Pause rendering when tab is inactive
    const handleVisibilityChange = () => {
      if (document.hidden) {
        cancelAnimationFrame(animationFrameId);
      } else {
        animationFrameId = requestAnimationFrame(render);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerleave", handlePointerLeave);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  return <canvas ref={canvasRef} className="architectural-canvas" aria-hidden="true" />;
}
