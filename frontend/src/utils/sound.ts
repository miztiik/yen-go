/**
 * Sound utilities for Go game audio feedback
 * @module utils/sound
 *
 * Uses Web Audio API to generate realistic stone placement sounds
 * without requiring external audio files.
 */

/** Audio context for sound generation */
let audioContext: AudioContext | null = null;

/**
 * Initialize audio context (must be called after user interaction)
 */
const initAudioContext = (): AudioContext | null => {
  if (!audioContext) {
    try {
      audioContext = new (
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      )();
    } catch {
      console.warn('Web Audio API not supported');
      return null;
    }
  }
  return audioContext;
};

/**
 * Play a stone placement sound
 * Creates a subtle "click" sound mimicking a stone being placed on a wooden board
 */
export const playStoneSound = (): void => {
  const ctx = initAudioContext();
  if (!ctx) return;

  // Resume context if suspended (browser autoplay policy)
  if (ctx.state === 'suspended') {
    void ctx.resume();
  }

  const now = ctx.currentTime;

  // Create a short noise burst for the initial "click"
  const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 0.05, ctx.sampleRate);
  const noiseData = noiseBuffer.getChannelData(0);
  for (let i = 0; i < noiseData.length; i++) {
    noiseData[i] = (Math.random() * 2 - 1) * Math.exp(-i / (ctx.sampleRate * 0.01));
  }

  const noiseSource = ctx.createBufferSource();
  noiseSource.buffer = noiseBuffer;

  // Bandpass filter to shape the click
  const filter = ctx.createBiquadFilter();
  filter.type = 'bandpass';
  filter.frequency.value = 800;
  filter.Q.value = 1.5;

  // Gain for volume control
  const gainNode = ctx.createGain();
  gainNode.gain.setValueAtTime(0.15, now);
  gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

  // Add a low "thunk" tone for the wood resonance
  const oscillator = ctx.createOscillator();
  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(180, now);
  oscillator.frequency.exponentialRampToValueAtTime(80, now + 0.1);

  const oscGain = ctx.createGain();
  oscGain.gain.setValueAtTime(0.08, now);
  oscGain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);

  // Connect noise path
  noiseSource.connect(filter);
  filter.connect(gainNode);
  gainNode.connect(ctx.destination);

  // Connect oscillator path
  oscillator.connect(oscGain);
  oscGain.connect(ctx.destination);

  // Play
  noiseSource.start(now);
  oscillator.start(now);
  oscillator.stop(now + 0.1);
  noiseSource.stop(now + 0.08);
};

/**
 * Play an error/invalid move sound
 * Subtle low tone indicating move rejection
 */
export const playErrorSound = (): void => {
  const ctx = initAudioContext();
  if (!ctx) return;

  if (ctx.state === 'suspended') {
    void ctx.resume();
  }

  const now = ctx.currentTime;

  const oscillator = ctx.createOscillator();
  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(150, now);
  oscillator.frequency.exponentialRampToValueAtTime(100, now + 0.15);

  const gainNode = ctx.createGain();
  gainNode.gain.setValueAtTime(0.08, now);
  gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.15);

  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);

  oscillator.start(now);
  oscillator.stop(now + 0.15);
};

/**
 * Play a success sound for correct moves
 * Pleasant ascending tone indicating a correct answer
 */
export const playSuccessSound = (): void => {
  const ctx = initAudioContext();
  if (!ctx) return;

  if (ctx.state === 'suspended') {
    void ctx.resume();
  }

  const now = ctx.currentTime;

  // Create two ascending tones for a pleasant "ding"
  const osc1 = ctx.createOscillator();
  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(523.25, now); // C5
  osc1.frequency.exponentialRampToValueAtTime(659.25, now + 0.1); // E5

  const osc2 = ctx.createOscillator();
  osc2.type = 'sine';
  osc2.frequency.setValueAtTime(659.25, now + 0.05); // E5
  osc2.frequency.exponentialRampToValueAtTime(783.99, now + 0.15); // G5

  const gainNode = ctx.createGain();
  gainNode.gain.setValueAtTime(0.1, now);
  gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

  osc1.connect(gainNode);
  osc2.connect(gainNode);
  gainNode.connect(ctx.destination);

  osc1.start(now);
  osc2.start(now + 0.05);
  osc1.stop(now + 0.15);
  osc2.stop(now + 0.25);
};

/**
 * Play a completion "pling" sound for puzzle completion
 * Celebratory ascending arpeggio
 */
export const playCompletionSound = (): void => {
  const ctx = initAudioContext();
  if (!ctx) return;

  if (ctx.state === 'suspended') {
    void ctx.resume();
  }

  const now = ctx.currentTime;
  const notes = [523.25, 659.25, 783.99, 1046.5]; // C5, E5, G5, C6 - Major chord arpeggio
  const spacing = 0.08;

  notes.forEach((freq, i) => {
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = freq;

    const gain = ctx.createGain();
    const startTime = now + i * spacing;
    gain.gain.setValueAtTime(0.08, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.3);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(startTime);
    osc.stop(startTime + 0.3);
  });
};

/**
 * Play a wrong move sound
 * Low descending tone indicating mistake
 */
export const playWrongSound = (): void => {
  const ctx = initAudioContext();
  if (!ctx) return;

  if (ctx.state === 'suspended') {
    void ctx.resume();
  }

  const now = ctx.currentTime;

  const osc = ctx.createOscillator();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(300, now);
  osc.frequency.exponentialRampToValueAtTime(150, now + 0.2);

  const gainNode = ctx.createGain();
  gainNode.gain.setValueAtTime(0.1, now);
  gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.2);

  osc.connect(gainNode);
  gainNode.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + 0.2);
};
