import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 注意：不要 rewrite 掉 /api 前缀。
      // Java 后端配置了 server.servlet.context-path=/api，
      // 即真实接口路径本身就是 /api/**；若在此剥离前缀，
      // 请求会变成 /health 而落到 404（与 nginx.conf 的代理行为保持一致）。
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})
