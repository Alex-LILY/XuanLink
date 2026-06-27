import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8022',
        changeOrigin: true,
      },
      '/session': { target: 'http://127.0.0.1:8022', changeOrigin: true },
      '/settings': { target: 'http://127.0.0.1:8022', changeOrigin: true },
      '/http_proxies': { target: 'http://127.0.0.1:8022', changeOrigin: true },
      '/utils': { target: 'http://127.0.0.1:8022', changeOrigin: true },
      '/connectors': { target: 'http://127.0.0.1:8022', changeOrigin: true },
    }
  }
})
