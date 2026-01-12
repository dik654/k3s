import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

// API URL: docker-compose에서는 'http://backend:8000', 로컬에서는 'http://localhost:8000'
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,  // Vite 기본 포트 (로컬 개발용)
    host: '0.0.0.0',  // 외부 접속 허용 (docker, 다른 머신에서 접근)
    proxy: {
      '/api': {
        target: API_URL,
        changeOrigin: true,
        // 웹소켓 지원 (실시간 로그 등)
        ws: true,
        // 프록시 에러 시 로그
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('proxy error', err);
          });
        },
      },
    },
  },
  build: {
    outDir: 'build',
    sourcemap: false,
  },
});
