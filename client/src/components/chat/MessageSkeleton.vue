<script setup lang="ts">
defineProps<{
  index?: number
}>()
</script>

<template>
  <div class="message-skeleton" :class="{ 'is-user': index % 2 === 1 }">
    <div class="skeleton-avatar" />
    <div class="skeleton-content">
      <div class="skeleton-line" :style="{ width: `${60 + (index || 0) * 15}%` }" />
      <div class="skeleton-line" :style="{ width: `${40 + (index || 0) * 10}%` }" />
      <div v-if="index === 1" class="skeleton-line" style="width: 80%" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.message-skeleton {
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
      background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
      background-size: 200% 100%;
    }
  }
}

.skeleton-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
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
  background: linear-gradient(90deg, #f0f0f0 25%, #f8f8f8 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
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
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>
