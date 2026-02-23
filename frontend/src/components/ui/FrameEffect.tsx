'use client';

import { cn } from '@/lib/utils';

interface FrameEffectProps {
  frameId: string | null | undefined;
  type: 'card' | 'avatar';
  className?: string;
  children: React.ReactNode;
}

/**
 * FrameEffect — wraps children with animated CSS-only premium frame effects.
 * Uses layered box-shadows + animated pseudo-elements for maximum visual impact.
 * When frameId is null/undefined, renders children as-is (zero overhead).
 */
export function FrameEffect({ frameId, type, className, children }: FrameEffectProps) {
  if (!frameId) {
    return <>{children}</>;
  }

  if (type === 'card') {
    const cfg = CARD_FRAME_EFFECTS[frameId];
    if (!cfg) return <>{children}</>;

    return (
      <div className={cn('relative', className)}>
        {/* Outer animated glow — big, visible aura */}
        <div
          className={cn(
            'absolute -inset-[6px] rounded-2xl pointer-events-none z-0',
            cfg.glowClass,
          )}
        />
        {/* Animated border — thick, vivid */}
        <div
          className={cn(
            'absolute -inset-[3px] rounded-[14px] pointer-events-none z-[1]',
            cfg.borderClass,
          )}
        />
        {/* Extra effects layer (particles, scan lines, etc.) */}
        {cfg.extraClass && (
          <div
            className={cn(
              'absolute -inset-[3px] rounded-[14px] pointer-events-none z-[3] overflow-visible',
              cfg.extraClass,
            )}
          />
        )}
        <div className="relative z-[2]">{children}</div>
      </div>
    );
  }

  // type === 'avatar'
  const cfg = PROFILE_FRAME_EFFECTS[frameId];
  if (!cfg) return <>{children}</>;

  return (
    <div className={cn('relative inline-block', className)}>
      {/* Outer animated glow */}
      <div
        className={cn(
          'absolute -inset-[5px] rounded-full pointer-events-none z-0',
          cfg.glowClass,
        )}
      />
      {/* Animated ring — thick, vivid */}
      <div
        className={cn(
          'absolute -inset-[3px] rounded-full pointer-events-none z-[1]',
          cfg.ringClass,
        )}
      />
      {/* Extra sparkle/particle layer */}
      {cfg.extraClass && (
        <div
          className={cn(
            'absolute -inset-[3px] rounded-full pointer-events-none z-[3] overflow-visible',
            cfg.extraClass,
          )}
        />
      )}
      <div className="relative z-[2]">{children}</div>
    </div>
  );
}

/* ──────────────────────────────────────────────
 * Card frame effect configs
 * ────────────────────────────────────────────── */

const CARD_FRAME_EFFECTS: Record<string, {
  borderClass: string;
  glowClass: string;
  extraClass?: string;
}> = {
  card_frame_golden: {
    borderClass: 'frame-golden-border',
    glowClass: 'frame-golden-glow',
  },
  card_frame_neon: {
    borderClass: 'frame-neon-border',
    glowClass: 'frame-neon-glow',
    extraClass: 'frame-neon-scan',
  },
  card_frame_fire: {
    borderClass: 'frame-fire-border',
    glowClass: 'frame-fire-glow',
    extraClass: 'frame-fire-embers',
  },
  card_frame_cosmic: {
    borderClass: 'frame-cosmic-border',
    glowClass: 'frame-cosmic-glow',
    extraClass: 'frame-cosmic-stars',
  },
};

/* ──────────────────────────────────────────────
 * Profile frame effect configs
 * ────────────────────────────────────────────── */

const PROFILE_FRAME_EFFECTS: Record<string, {
  ringClass: string;
  glowClass: string;
  extraClass?: string;
}> = {
  profile_frame_silver: {
    ringClass: 'frame-silver-ring',
    glowClass: 'frame-silver-glow',
  },
  profile_frame_emerald: {
    ringClass: 'frame-emerald-ring',
    glowClass: 'frame-emerald-glow',
    extraClass: 'frame-emerald-shimmer',
  },
  profile_frame_ruby: {
    ringClass: 'frame-ruby-ring',
    glowClass: 'frame-ruby-glow',
    extraClass: 'frame-ruby-sparkle',
  },
  profile_frame_diamond: {
    ringClass: 'frame-diamond-ring',
    glowClass: 'frame-diamond-glow',
    extraClass: 'frame-diamond-particles',
  },
};

export default FrameEffect;
