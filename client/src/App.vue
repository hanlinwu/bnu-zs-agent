<script setup lang="ts">
import { useThemeStore } from './stores/theme'

// Theme is auto-applied on store creation
useThemeStore()
</script>

<template>
  <router-view />
</template>

<style lang="scss">
#app {
  width: 100%;
  min-height: 100vh;
}
</style>
