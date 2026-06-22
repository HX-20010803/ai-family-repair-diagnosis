import { defineConfig } from 'vite'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const uni = require('@dcloudio/vite-plugin-uni').default

export default defineConfig({
  plugins: [uni()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
