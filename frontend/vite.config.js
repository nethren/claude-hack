import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// `vite build --mode static` produces the hosted copy: it replays the recorded
// runs in public/data/runs instead of calling the Python backend.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_STATIC_DEMO': JSON.stringify(mode === 'static' ? '1' : ''),
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.BACKEND_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
}));
