import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 引入自動引入插件
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // 配置自動引入 Element Plus 相關函數 (如 ElMessage)
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    // 配置自動引入 Element Plus 組件 (如 <el-button>)
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  // 如果後端 API 在 8000 埠，也可以在這裡配置 Proxy 解決開發環境的跨域問題
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})