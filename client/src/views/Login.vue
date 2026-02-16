<template>
  <div class="login-page">
    <!-- Left decorative panel -->
    <div class="login-page__brand">
      <div class="login-page__brand-overlay">
        <div class="login-page__brand-content">
          <div class="login-page__logo-area">
            <img
              src="/images/bnu-logo.png"
              alt="北京师范大学校徽"
              class="login-page__logo-img"
            />
            <h1 class="login-page__school-name">北京师范大学</h1>
            <p class="login-page__school-name-en">Beijing Normal University</p>
          </div>

          <div class="login-page__motto">
            <div class="login-page__motto-divider"></div>
            <p class="login-page__motto-text">学为人师，行为世范</p>
            <p class="login-page__motto-text-en">Learn to be an Outstanding Teacher, Act as a Model for Society</p>
            <div class="login-page__motto-divider"></div>
          </div>

          <div class="login-page__brand-features">
            <div class="login-page__feature">
              <el-icon :size="20"><ChatDotRound /></el-icon>
              <span>AI 智能问答，精准解答招生疑问</span>
            </div>
            <div class="login-page__feature">
              <el-icon :size="20"><Calendar /></el-icon>
              <span>时间感知，关键节点及时提醒</span>
            </div>
            <div class="login-page__feature">
              <el-icon :size="20"><User /></el-icon>
              <span>角色定制，专属个性化服务</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right login panel -->
    <div class="login-page__main">
      <div class="login-page__main-inner">
        <div class="login-page__header">
          <h2 class="login-page__title">京师小智 · 招生智能助手</h2>
          <p class="login-page__subtitle">北京师范大学招生咨询服务平台</p>
        </div>

        <LoginForm />

        <footer class="login-page__footer">
          <p>&copy; 2026 北京师范大学招生办公室</p>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChatDotRound, Calendar, User } from '@element-plus/icons-vue'
import LoginForm from '@/components/auth/LoginForm.vue'
</script>

<style lang="scss" scoped>
.login-page {
  display: flex;
  min-height: 100%;
  background-color: var(--color-bg-primary);

  // ---------------------------------------------------------------
  // Left decorative panel (60%)
  // ---------------------------------------------------------------
  &__brand {
    position: relative;
    flex: 0 0 60%;
    overflow: hidden;

    // Abstract academic pattern with CSS gradients
    background:
      // Diagonal lines pattern
      repeating-linear-gradient(
        45deg,
        transparent,
        transparent 40px,
        rgba(255, 255, 255, 0.03) 40px,
        rgba(255, 255, 255, 0.03) 42px
      ),
      repeating-linear-gradient(
        -45deg,
        transparent,
        transparent 40px,
        rgba(255, 255, 255, 0.02) 40px,
        rgba(255, 255, 255, 0.02) 42px
      ),
      // Radial highlights
      radial-gradient(
        ellipse at 20% 50%,
        rgba(26, 95, 191, 0.5) 0%,
        transparent 60%
      ),
      radial-gradient(
        ellipse at 80% 20%,
        rgba(196, 151, 47, 0.15) 0%,
        transparent 50%
      ),
      radial-gradient(
        ellipse at 60% 80%,
        rgba(0, 45, 122, 0.3) 0%,
        transparent 50%
      ),
      // Base gradient
      linear-gradient(
        135deg,
        #002D7A 0%,
        #003DA5 40%,
        #1A5FBF 100%
      );
  }

  &__brand-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px;

    // Subtle grid pattern overlay
    &::before {
      content: '';
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
      background-size: 60px 60px;
      pointer-events: none;
    }
  }

  &__brand-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 48px;
    max-width: 480px;
    color: #ffffff;
  }

  // Logo area
  &__logo-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  &__logo-img {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    object-fit: contain;
    background: #ffffff;
    padding: 6px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
    margin-bottom: 4px;
  }

  &__school-name {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: 6px;
    text-shadow: 0 2px 16px rgba(0, 0, 0, 0.2);
  }

  &__school-name-en {
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 2px;
    opacity: 0.7;
    text-transform: uppercase;
  }

  // Motto
  &__motto {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  &__motto-divider {
    width: 60px;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(196, 151, 47, 0.8),
      transparent
    );
  }

  &__motto-text {
    font-size: 24px;
    font-weight: 600;
    letter-spacing: 8px;
    color: rgba(255, 255, 255, 0.95);
    text-shadow: 0 1px 8px rgba(0, 0, 0, 0.15);
  }

  &__motto-text-en {
    font-size: 12px;
    letter-spacing: 1px;
    opacity: 0.6;
    text-align: center;
    line-height: 1.6;
  }

  // Features
  &__brand-features {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-top: 16px;
  }

  &__feature {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);

    .el-icon {
      flex-shrink: 0;
      color: rgba(196, 151, 47, 0.9);
    }
  }

  // ---------------------------------------------------------------
  // Right login panel (40%)
  // ---------------------------------------------------------------
  &__main {
    flex: 0 0 40%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 32px;
    background-color: var(--color-bg-primary);
  }

  &__main-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    max-width: 420px;
    min-height: 560px;
    justify-content: center;
    gap: 40px;
  }

  &__header {
    text-align: center;
  }

  &__title {
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text-primary);
    margin-bottom: 8px;
    letter-spacing: 1px;
  }

  &__subtitle {
    font-size: 14px;
    color: var(--color-text-secondary);
  }

  &__footer {
    margin-top: auto;
    padding-top: 24px;
    text-align: center;

    p {
      font-size: 12px;
      color: var(--color-text-placeholder);
    }
  }
}

// ---------------------------------------------------------------
// Responsive: Tablet
// ---------------------------------------------------------------
@media (max-width: 1024px) {
  .login-page {
    &__brand {
      flex: 0 0 50%;
    }

    &__main {
      flex: 0 0 50%;
    }

    &__school-name {
      font-size: 26px;
      letter-spacing: 4px;
    }

    &__motto-text {
      font-size: 20px;
      letter-spacing: 6px;
    }
  }
}

// ---------------------------------------------------------------
// Responsive: Mobile
// ---------------------------------------------------------------
@media (max-width: 768px) {
  .login-page {
    flex-direction: column;

    &__brand {
      display: none;
    }

    &__main {
      flex: 1;
      padding: 32px 24px;
    }

    &__main-inner {
      min-height: auto;
      gap: 32px;
    }

    &__title {
      font-size: 22px;
    }

    &__header {
      &::before {
        content: '北京师范大学';
        display: block;
        font-size: 13px;
        font-weight: 500;
        color: var(--color-primary);
        letter-spacing: 3px;
        margin-bottom: 12px;
      }
    }
  }
}
</style>
