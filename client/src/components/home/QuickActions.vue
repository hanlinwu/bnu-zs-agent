<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ChatLineRound, Document, Place, Phone } from '@element-plus/icons-vue'
import { markRaw, type Component } from 'vue'

const router = useRouter()

interface QuickAction {
  id: number
  icon: Component
  title: string
  description: string
  route?: string
  href?: string
}

const actions: QuickAction[] = [
  {
    id: 1,
    icon: markRaw(ChatLineRound),
    title: '在线咨询',
    description: '与京师小智实时对话，解答您的招生疑问',
    route: '/chat',
  },
  {
    id: 2,
    icon: markRaw(Document),
    title: '招生简章',
    description: '查看最新本科及研究生招生简章',
    route: '/chat',
  },
  {
    id: 3,
    icon: markRaw(Place),
    title: '校园导览',
    description: '在线浏览北京师范大学校园风光',
    route: '/chat',
  },
  {
    id: 4,
    icon: markRaw(Phone),
    title: '联系我们',
    description: '获取招生办联系方式与办公时间',
    route: '/chat',
  },
]

function handleAction(action: QuickAction) {
  if (action.href) {
    window.open(action.href, '_blank')
  } else if (action.route) {
    router.push(action.route)
  }
}
</script>

<template>
  <section class="quick-actions">
    <div class="section-container">
      <h2 class="section-title">快捷服务</h2>
      <p class="section-desc">一站式招生服务入口</p>
      <div class="actions-grid">
        <div
          v-for="action in actions"
          :key="action.id"
          class="action-card"
          @click="handleAction(action)"
        >
          <div class="action-icon-wrapper">
            <el-icon :size="32"><component :is="action.icon" /></el-icon>
          </div>
          <h3 class="action-title">{{ action.title }}</h3>
          <p class="action-desc">{{ action.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.quick-actions {
  padding: 72px 24px;
  background: var(--bg-secondary, #F4F6FA);
}

.section-container {
  max-width: 1100px;
  margin: 0 auto;
}

.section-title {
  text-align: center;
  font-size: 30px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 8px;
}

.section-desc {
  text-align: center;
  font-size: 16px;
  color: var(--text-secondary, #5A5A72);
  margin: 0 0 40px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 36px 24px;
  background: var(--bg-primary, #ffffff);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid var(--border-color, #E2E6ED);

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-md, 0 8px 24px rgba(0, 61, 165, 0.12));
    border-color: var(--bnu-blue, #003DA5);

    .action-icon-wrapper {
      background: var(--bnu-blue, #003DA5);
      color: #ffffff;
    }
  }
}

.action-icon-wrapper {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: rgba(0, 61, 165, 0.08);
  color: var(--bnu-blue, #003DA5);
  margin-bottom: 20px;
  transition: all 0.3s ease;
}

.action-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 8px;
}

.action-desc {
  font-size: 14px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
  line-height: 1.5;
}

@media (max-width: 1024px) {
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .quick-actions {
    padding: 48px 16px;
  }

  .section-title {
    font-size: 24px;
  }

  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .action-card {
    padding: 24px 16px;
  }

  .action-icon-wrapper {
    width: 56px;
    height: 56px;
    margin-bottom: 16px;
  }

  .action-title {
    font-size: 16px;
  }

  .action-desc {
    font-size: 13px;
  }
}
</style>
