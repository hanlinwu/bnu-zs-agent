<script setup lang="ts">
import HeroSection from '@/components/home/HeroSection.vue'
import HotQuestions from '@/components/home/HotQuestions.vue'
import QuickActions from '@/components/home/QuickActions.vue'
</script>

<template>
  <div class="home-page">
    <HeroSection />
    <HotQuestions />
    <QuickActions />

    <footer class="home-footer">
      <div class="footer-content">
        <div class="footer-links">
          <a href="https://www.bnu.edu.cn" target="_blank" rel="noopener">学校官网</a>
          <span class="footer-divider">|</span>
          <a href="https://admission.bnu.edu.cn" target="_blank" rel="noopener">招生网</a>
          <span class="footer-divider">|</span>
          <a href="https://yz.bnu.edu.cn" target="_blank" rel="noopener">研究生招生</a>
          <span class="footer-divider">|</span>
          <a href="/admin/login">管理后台</a>
        </div>
        <p class="footer-copyright">
          &copy; {{ new Date().getFullYear() }} 北京师范大学招生办公室 &mdash; 京师小智智能招生助手
        </p>
        <p class="footer-address">
          地址：北京市海淀区新街口外大街19号 &nbsp;|&nbsp; 邮编：100875 &nbsp;|&nbsp; 电话：010-58807962
        </p>
      </div>
    </footer>
  </div>
</template>

<style lang="scss" scoped>
.home-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #ffffff);
  overflow-y: auto;
}

.home-footer {
  margin-top: auto;
  background: #0A1628;
  padding: 40px 24px;
}

.footer-content {
  max-width: 1100px;
  margin: 0 auto;
  text-align: center;
}

.footer-links {
  margin-bottom: 16px;

  a {
    color: rgba(255, 255, 255, 0.7);
    text-decoration: none;
    font-size: 14px;
    transition: color 0.2s;

    &:hover {
      color: #C4972F;
    }
  }
}

.footer-divider {
  margin: 0 12px;
  color: rgba(255, 255, 255, 0.25);
}

.footer-copyright {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  margin: 0 0 8px;
}

.footer-address {
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
  margin: 0;
}

@media (max-width: 768px) {
  .home-footer {
    padding: 32px 16px;
  }

  .footer-links a {
    font-size: 13px;
  }

  .footer-divider {
    margin: 0 8px;
  }
}
</style>
