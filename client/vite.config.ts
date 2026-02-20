import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import path from 'node:path'

function safeGit(command: string): string | null {
  try {
    return execSync(command, {
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
  } catch {
    return null
  }
}

const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8')) as {
  version?: string
}

const appVersion =
  process.env.APP_VERSION
  || pkg.version
  || '0.0.0'
const gitCommit =
  process.env.GIT_COMMIT?.slice(0, 7)
  || process.env.GITHUB_SHA?.slice(0, 7)
  || process.env.CI_COMMIT_SHA?.slice(0, 7)
  || safeGit('git rev-parse --short HEAD')
  || 'unknown'
const gitCommitDate =
  process.env.GIT_COMMIT_DATE
  || process.env.BUILD_TIME
  || safeGit("git log -1 --format=%cd --date=format:'%Y-%m-%d %H:%M'")
  || 'unknown'

// https://vite.dev/config/
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __GIT_COMMIT__: JSON.stringify(gitCommit),
    __GIT_COMMIT_DATE__: JSON.stringify(gitCommitDate),
  },

  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [
        ElementPlusResolver({
          importStyle: 'sass',
        }),
      ],
      dts: 'src/components.d.ts',
    }),
  ],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },

  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables" as *;\n`,
      },
    },
  },

  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://127.0.0.1:8001',
        ws: true,
        changeOrigin: true,
      },
    },
  },

  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined

          if (id.includes('@element-plus/icons-vue')) {
            return 'element-icons'
          }

          if (id.includes('element-plus')) {
            return 'element-plus'
          }

          if (id.includes('axios') || id.includes('marked') || id.includes('dompurify')) {
            return 'utils'
          }

          return 'vendor'
        },
      },
    },
  },
})
