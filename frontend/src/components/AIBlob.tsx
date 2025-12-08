'use client';

import { useEffect, useRef } from 'react';

interface AIBlobProps {
  className?: string;
  size?: number;
}

export function AIBlob({ className = '', size = 200 }: AIBlobProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const centerX = size / 2;
    const centerY = size / 2;
    const baseRadius = size * 0.35;

    // Noise parameters (medium values)
    const speed = 0.003;
    const spikes = 0.8;
    const complexity = 6;

    // Simple noise function
    const noise = (x: number, y: number, time: number) => {
      return (
        Math.sin(x * spikes + time) * 0.3 +
        Math.sin(y * spikes + time * 1.3) * 0.3 +
        Math.sin((x + y) * spikes * 0.5 + time * 0.7) * 0.4
      );
    };

    let startTime = Date.now();

    const draw = () => {
      const elapsed = (Date.now() - startTime) * speed;

      ctx.clearRect(0, 0, size, size);

      // Create gradient
      const gradient = ctx.createRadialGradient(
        centerX - 20,
        centerY - 20,
        0,
        centerX,
        centerY,
        baseRadius * 1.5
      );
      gradient.addColorStop(0, 'rgba(168, 85, 247, 1)');    // purple-500
      gradient.addColorStop(0.4, 'rgba(139, 92, 246, 0.9)'); // violet-500
      gradient.addColorStop(0.7, 'rgba(99, 102, 241, 0.8)'); // indigo-500
      gradient.addColorStop(1, 'rgba(59, 130, 246, 0.6)');   // blue-500

      // Draw blob
      ctx.beginPath();

      const points = 64;
      for (let i = 0; i <= points; i++) {
        const angle = (i / points) * Math.PI * 2;
        const x = Math.cos(angle);
        const y = Math.sin(angle);

        // Apply noise to radius
        const noiseValue = noise(x * complexity, y * complexity, elapsed);
        const radius = baseRadius * (1 + noiseValue * 0.15);

        const px = centerX + x * radius;
        const py = centerY + y * radius;

        if (i === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }

      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      // Add glow effect
      ctx.shadowColor = 'rgba(139, 92, 246, 0.5)';
      ctx.shadowBlur = 40;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Add inner highlight
      const highlightGradient = ctx.createRadialGradient(
        centerX - 25,
        centerY - 25,
        0,
        centerX,
        centerY,
        baseRadius
      );
      highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.3)');
      highlightGradient.addColorStop(0.3, 'rgba(255, 255, 255, 0.1)');
      highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.beginPath();
      for (let i = 0; i <= points; i++) {
        const angle = (i / points) * Math.PI * 2;
        const x = Math.cos(angle);
        const y = Math.sin(angle);
        const noiseValue = noise(x * complexity, y * complexity, elapsed);
        const radius = baseRadius * 0.8 * (1 + noiseValue * 0.1);
        const px = centerX + x * radius;
        const py = centerY + y * radius;
        if (i === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.closePath();
      ctx.fillStyle = highlightGradient;
      ctx.fill();

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [size]);

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        style={{
          width: size,
          height: size,
        }}
        className="animate-float"
      />
      {/* Glow background */}
      <div
        className="absolute inset-0 rounded-full blur-3xl opacity-30"
        style={{
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.6) 0%, rgba(59, 130, 246, 0.3) 50%, transparent 70%)',
        }}
      />
    </div>
  );
}
