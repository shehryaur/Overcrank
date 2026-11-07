import { useEffect, useRef } from "react";

type Strand = { x: number; y: number; v: number; w: number };

function spawn(anywhere: boolean): Strand {
  return {
    x: Math.random(),
    y: anywhere ? 0.42 + Math.random() * 0.58 : 0.45 + Math.random() * 0.1,
    v: 0.5 + Math.random() * 1.25,
    w: 0.3 + Math.random() * 1.1,
  };
}

function field(x: number, y: number, t: number) {
  return (
    Math.sin(x * 2.4 + t) * 0.9 +
    Math.cos(y * 4.2 - t * 0.65) * 0.55 +
    Math.sin((x * 1.6 + y) * 6 + t * 1.1) * 0.35
  );
}

export default function FlowField() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const strands = Array.from({ length: 1800 }, () => spawn(true));
    let raf = 0;
    let frame = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.floor(canvas.clientWidth * dpr));
      canvas.height = Math.max(1, Math.floor(canvas.clientHeight * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = "#050505";
      ctx.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    };

    resize();
    window.addEventListener("resize", resize);

    const tick = () => {
      frame += 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.fillStyle = "rgba(5,5,5,0.22)";
      ctx.fillRect(0, 0, w, h);
      const t = frame * 0.007;

      for (const p of strands) {
        const ang = field(p.x * 2.1, p.y * 3.2, t) * Math.PI;
        const x1 = p.x * w;
        const y1 = p.y * h;
        p.x += (Math.cos(ang) * p.v) / w;
        p.y += (Math.sin(ang) * p.v * 0.2) / h;
        const depth = Math.min(1, Math.max(0, (p.y - 0.4) / 0.6));
        ctx.strokeStyle = `rgba(214,214,210,${0.03 + depth * 0.18})`;
        ctx.lineWidth = p.w * (0.28 + depth * 0.8);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(p.x * w, p.y * h);
        ctx.stroke();
        if (p.x < -0.03 || p.x > 1.03 || p.y < 0.38 || p.y > 1.04) {
          Object.assign(p, spawn(false));
        }
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={ref} className="flow-field" aria-hidden />;
}
