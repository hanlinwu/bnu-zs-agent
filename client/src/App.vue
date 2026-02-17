<script setup lang="ts">
import { useThemeStore } from './stores/theme'
import { routeLoading } from './router'

// Theme is auto-applied on store creation
useThemeStore()
</script>

<template>
  <!-- Top progress bar -->
  <div v-if="routeLoading" class="route-progress-bar" />

  <router-view v-slot="{ Component }">
    <transition name="page-fade" mode="out-in">
      <suspense>
        <template #default>
          <div class="route-page-root">
            <component :is="Component" />
          </div>
        </template>
        <template #fallback>
          <div class="page-loading">
            <div class="page-loading-spinner" />
          </div>
        </template>
      </suspense>
    </transition>
  </router-view>
</template>

<style lang="scss">
#app {
  width: 100%;
  height: 100%;
}

.route-page-root {
  width: 100%;
  height: 100%;
}

/* Route loading progress bar */
.route-progress-bar {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  z-index: 9999;
  background: linear-gradient(
    90deg,
    var(--bnu-blue, #003DA5) 0%,
    var(--color-primary-light, #4a90d9) 50%,
    var(--bnu-blue, #003DA5) 100%
  );
  background-size: 200% 100%;
  animation: progress-slide 1.2s ease-in-out infinite;
}

@keyframes progress-slide {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Page fade transition */
.page-fade-enter-active {
  transition: opacity 0.2s ease;
}

.page-fade-leave-active {
  transition: opacity 0.15s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* Suspense loading fallback */
.page-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: var(--bg-primary, #fff);
}

.page-loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-color, #e2e6ed);
  border-top-color: var(--bnu-blue, #003DA5);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
