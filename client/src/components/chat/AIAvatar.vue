<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    mood?: 'idle' | 'thinking' | 'searching' | 'writing' | 'happy'
  }>(),
  {
    mood: 'idle',
  },
)

const mouthPath = computed(() => {
  if (props.mood === 'thinking') return 'M25 40 Q32 37 39 40'
  if (props.mood === 'searching') return 'M24 40 Q32 44 40 40'
  if (props.mood === 'writing') return 'M24 40 L40 40'
  if (props.mood === 'happy') return 'M23 38 Q32 47 41 38'
  return 'M24 39 Q32 45 40 39'
})
</script>

<template>
  <svg class="ai-avatar-svg" :class="`mood-${props.mood}`" viewBox="0 0 64 64" aria-hidden="true">
    <defs>
      <linearGradient id="aiAvatarBg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#eef5ff" />
        <stop offset="100%" stop-color="#d8e7ff" />
      </linearGradient>
    </defs>

    <rect x="8" y="10" width="48" height="44" rx="16" fill="url(#aiAvatarBg)" stroke="#4f75bd" stroke-width="2" />
    <line x1="32" y1="4" x2="32" y2="10" stroke="#2f5fb0" stroke-width="3" stroke-linecap="round" />
    <circle cx="32" cy="3.5" r="2.5" fill="#f8b84a" class="antenna-dot" />

    <g class="eye eye-left">
      <ellipse cx="24" cy="28" rx="4" ry="5" fill="#0f3678" />
    </g>
    <g class="eye eye-right">
      <ellipse cx="40" cy="28" rx="4" ry="5" fill="#0f3678" />
    </g>

    <path class="mouth" :d="mouthPath" stroke="#0f3678" stroke-width="3" stroke-linecap="round" fill="none" />
    <ellipse cx="18" cy="38" rx="3" ry="2" fill="#f1a4a4" opacity="0.6" />
    <ellipse cx="46" cy="38" rx="3" ry="2" fill="#f1a4a4" opacity="0.6" />
  </svg>
</template>

<style scoped lang="scss">
.ai-avatar-svg {
  width: 100%;
  height: 100%;
}

.eye {
  transform-origin: center;
  animation: blink 4s infinite;
}

.mouth {
  transform-origin: 32px 40px;
  animation: smile 2.8s ease-in-out infinite;
}

.antenna-dot {
  animation: pulse 2s ease-out infinite;
}

.ai-avatar-svg.mood-thinking .eye {
  animation-duration: 2.4s;
}

.ai-avatar-svg.mood-thinking .mouth {
  animation: none;
}

.ai-avatar-svg.mood-searching .eye-left {
  animation: blink 3.6s infinite, scan-left 1.1s ease-in-out infinite;
}

.ai-avatar-svg.mood-searching .eye-right {
  animation: blink 3.6s infinite, scan-right 1.1s ease-in-out infinite;
}

.ai-avatar-svg.mood-searching .antenna-dot {
  animation-duration: 1.2s;
}

.ai-avatar-svg.mood-writing .eye {
  animation-duration: 2.8s;
}

.ai-avatar-svg.mood-writing .mouth {
  animation: none;
}

.ai-avatar-svg.mood-happy .mouth {
  animation-duration: 1.9s;
}

@keyframes blink {
  0%, 44%, 48%, 100% { transform: scaleY(1); }
  46% { transform: scaleY(0.15); }
}

@keyframes smile {
  0%, 100% { transform: scaleX(1); }
  50% { transform: scaleX(1.12); }
}

@keyframes scan-left {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(-1px); }
}

@keyframes scan-right {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(1px); }
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.55; }
  100% { opacity: 1; }
}
</style>
