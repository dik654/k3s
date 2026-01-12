import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,  // Vite 기본 포트 (로컬 개발용)
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
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
