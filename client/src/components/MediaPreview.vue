<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Close, VideoPlay, Picture } from '@element-plus/icons-vue'

interface Props {
  visible: boolean
  type: 'image' | 'video'
  src: string
  title?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
}>()

const isLoading = ref(true)
const isError = ref(false)
const videoRef = ref<HTMLVideoElement | null>(null)

const isVisible = computed(() => props.visible)

watch(() => props.src, () => {
  isLoading.value = true
  isError.value = false
})

watch(() => props.visible, (val) => {
  if (val) {
    isLoading.value = true
    isError.value = false
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
    if (videoRef.value) {
      videoRef.value.pause()
    }
  }
})

onMounted(() => {
  if (props.visible) {
    document.body.style.overflow = 'hidden'
  }
})

onUnmounted(() => {
  document.body.style.overflow = ''
})

function handleClose() {
  emit('close')
}

function handleImageLoad() {
  isLoading.value = false
}

function handleImageError() {
  isLoading.value = false
  isError.value = true
}

function handleVideoLoad() {
  isLoading.value = false
}

function handleVideoError() {
  isLoading.value = false
  isError.value = true
}

function handleBackdropClick(e: MouseEvent) {
  if (e.target === e.currentTarget) {
    handleClose()
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.visible) {
    handleClose()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="preview-fade">
      <div
        v-if="isVisible"
        class="media-preview-overlay"
        @click="handleBackdropClick"
      >
        <!-- Close button -->
        <button class="preview-close" @click="handleClose">
          <el-icon :size="24"><Close /></el-icon>
        </button>

        <!-- Loading state -->
        <div v-if="isLoading" class="preview-loading">
          <el-icon class="loading-icon" :size="48"><Picture /></el-icon>
          <p>加载中...</p>
        </div>

        <!-- Error state -->
        <div v-else-if="isError" class="preview-error">
          <el-icon :size="48"><VideoPlay /></el-icon>
          <p>加载失败</p>
        </div>

        <!-- Image preview -->
        <div v-else-if="type === 'image'" class="preview-content image-content">
          <img
            :src="src"
            :alt="title || '图片预览'"
            class="preview-image"
            @load="handleImageLoad"
            @error="handleImageError"
          />
        </div>

        <!-- Video preview -->
        <div v-else class="preview-content video-content">
          <video
            ref="videoRef"
            :src="src"
            controls
            autoplay
            class="preview-video"
            @loadeddata="handleVideoLoad"
            @error="handleVideoError"
          ></video>
        </div>

        <!-- Title -->
        <div v-if="title" class="preview-title">
          {{ title }}
        </div>

        <!-- Tips -->
        <div class="preview-tips">
          按 ESC 或点击空白处关闭
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
.media-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.92);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 20px 80px;
}

.preview-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  cursor: pointer;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 10;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: scale(1.05);
  }
}

.preview-content {
  max-width: 100%;
  max-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;

  &.image-content {
    img {
      max-width: 100%;
      max-height: calc(100vh - 140px);
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
  }

  &.video-content {
    width: 100%;
    max-width: 1200px;

    video {
      width: 100%;
      max-height: calc(100vh - 140px);
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
  }
}

.preview-image {
  max-width: 100%;
  max-height: calc(100vh - 140px);
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.preview-video {
  width: 100%;
  max-height: calc(100vh - 140px);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.preview-title {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  color: #fff;
  font-size: 14px;
  text-align: center;
  max-width: 80%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 20px;
}

.preview-tips {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.preview-loading,
.preview-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: rgba(255, 255, 255, 0.7);

  p {
    margin: 0;
    font-size: 14px;
  }
}

.loading-icon {
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// Transition animations
.preview-fade-enter-active,
.preview-fade-leave-active {
  transition: opacity 0.3s ease;
}

.preview-fade-enter-from,
.preview-fade-leave-to {
  opacity: 0;
}

.preview-fade-enter-active .preview-content,
.preview-fade-leave-active .preview-content {
  transition: transform 0.3s ease;
}

.preview-fade-enter-from .preview-content,
.preview-fade-leave-to .preview-content {
  transform: scale(0.95);
}
</style>
