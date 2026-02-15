<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function startChat() {
  router.push('/chat')
}
</script>

<template>
  <section class="hero-section">
    <div class="hero-bg">
      <div class="hero-shape hero-shape--circle" />
      <div class="hero-shape hero-shape--ring" />
      <div class="hero-shape hero-shape--dots" />
    </div>
    <div class="hero-content">
      <h1 class="hero-title">欢迎来到京师小智</h1>
      <p class="hero-subtitle">
        北京师范大学招生智能助手，为您提供最权威的招生咨询服务
      </p>
      <el-button
        type="primary"
        size="large"
        round
        class="hero-cta"
        @click="startChat"
      >
        <el-icon class="cta-icon"><ChatDotRound /></el-icon>
        开始对话
      </el-button>
    </div>
  </section>
</template>

<script lang="ts">
import { ChatDotRound } from '@element-plus/icons-vue'
export default { components: { ChatDotRound } }
</script>

<style lang="scss" scoped>
.hero-section {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 520px;
  background: linear-gradient(135deg, #003DA5 0%, #002D7A 40%, #001A4D 100%);
  padding: 80px 24px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero-shape {
  position: absolute;
  border-radius: 50%;

  &--circle {
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(196, 151, 47, 0.12) 0%, transparent 70%);
    top: -100px;
    right: -80px;
  }

  &--ring {
    width: 300px;
    height: 300px;
    border: 2px solid rgba(255, 255, 255, 0.06);
    bottom: -60px;
    left: -60px;
  }

  &--dots {
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
    background-size: 20px 20px;
    top: 40%;
    left: 10%;
    border-radius: 0;
  }
}

.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 680px;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 20px;
  letter-spacing: 2px;
  line-height: 1.2;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

.hero-subtitle {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.85);
  margin: 0 0 40px;
  line-height: 1.6;
  font-weight: 400;
}

.hero-cta {
  height: 52px;
  padding: 0 40px;
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, #C4972F 0%, #D4A94A 100%);
  border: none;
  color: #ffffff;
  box-shadow: 0 4px 20px rgba(196, 151, 47, 0.4);
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 28px rgba(196, 151, 47, 0.55);
    background: linear-gradient(135deg, #D4A94A 0%, #C4972F 100%);
  }

  .cta-icon {
    margin-right: 8px;
    font-size: 20px;
  }
}

@media (max-width: 768px) {
  .hero-section {
    min-height: 400px;
    padding: 60px 20px;
  }

  .hero-title {
    font-size: 32px;
  }

  .hero-subtitle {
    font-size: 16px;
    margin-bottom: 32px;
  }

  .hero-cta {
    height: 44px;
    padding: 0 28px;
    font-size: 16px;
  }
}
</style>
