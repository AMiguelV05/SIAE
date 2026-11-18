import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
        configure(proxy) {
          // El navegador habla con Vite en el mismo origen; el proxy no requiere cabecera Origin para la API local.
          proxy.on('proxyReq', proxyRequest => proxyRequest.removeHeader('origin'))
        },
      },
    },
  },
})
