/**
 * Sound utilities using Web Audio API.
 * No external audio files needed — sounds are synthesized.
 */

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    }
    return audioCtx;
  } catch {
    return null;
  }
}

/**
 * Play a pleasant 3-note ascending chime (C5 → E5 → G5).
 * Used when a focus session timer reaches zero.
 */
export function playFocusCompleteSound(): void {
  const ctx = getAudioContext();
  if (!ctx) return;

  // Resume context if suspended (browser autoplay policy)
  if (ctx.state === 'suspended') {
    ctx.resume().catch(() => {});
  }

  const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
  const noteDuration = 0.12;
  const now = ctx.currentTime;

  notes.forEach((freq, i) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.value = freq;

    gain.gain.setValueAtTime(0.3, now + i * noteDuration);
    gain.gain.exponentialRampToValueAtTime(0.001, now + i * noteDuration + noteDuration * 2);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now + i * noteDuration);
    osc.stop(now + i * noteDuration + noteDuration * 2);
  });
}
