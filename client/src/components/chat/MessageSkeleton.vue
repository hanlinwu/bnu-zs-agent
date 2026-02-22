<script setup lang="ts">
const props = defineProps<{
  index?: number
}>()
</script>

<template>
  <div class="message-skeleton" :class="{ 'is-user': (props.index ?? 0) % 2 === 1 }">
    <div class="skeleton-avatar" />
    <div class="skeleton-content">
      <div class="skeleton-line" :style="{ width: `${60 + (props.index || 0) * 15}%` }" />
      <div class="skeleton-line" :style="{ width: `${40 + (props.index || 0) * 10}%` }" />
      <div v-if="props.index === 1" class="skeleton-line" style="width: 80%" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.message-skeleton {
  --skeleton-start: #f0f0f0;
  --skeleton-mid: #f8f8f8;
  --skeleton-end: #f0f0f0;
  --skeleton-user-start: #e0e0e0;
  --skeleton-user-mid: #f0f0f0;
  --skeleton-user-end: #e0e0e0;
  display: flex;
  gap: 10px;
  padding: 8px 0;
  max-width: 80%;
  animation: pulse 2s ease-in-out infinite;

  &.is-user {
    margin-left: auto;
    flex-direction: row-reverse;

    .skeleton-content {
      align-items: flex-end;
    }

    .skeleton-line {
      background: linear-gradient(
        90deg,
        var(--skeleton-user-start) 25%,
        var(--skeleton-user-mid) 50%,
        var(--skeleton-user-end) 75%
      );
      background-size: 200% 100%;
    }
  }
}

.skeleton-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(
    90deg,
    var(--skeleton-user-start) 25%,
    var(--skeleton-user-mid) 50%,
    var(--skeleton-user-end) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  flex-shrink: 0;
}

.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 200px;
}

.skeleton-line {
  height: 16px;
  border-radius: 8px;
  background: linear-gradient(
    90deg,
    var(--skeleton-start) 25%,
    var(--skeleton-mid) 50%,
    var(--skeleton-end) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

:global([data-theme='dark']) .message-skeleton {
  --skeleton-start: #2a3241;
  --skeleton-mid: #343e50;
  --skeleton-end: #2a3241;
  --skeleton-user-start: #253041;
  --skeleton-user-mid: #30405a;
  --skeleton-user-end: #253041;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.96;
  }
  50% {
    opacity: 0.72;
  }
}
</style>
