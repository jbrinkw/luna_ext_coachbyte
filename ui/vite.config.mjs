import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Backend service port - this should be configured by Luna to match the actual service port
const apiPort = process.env.COACHBYTE_BACKEND_PORT || '5300';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'healthz-endpoint',
      configureServer(server) {
        // Add healthz endpoint for Luna health checks
        // Must return to prevent falling through to other middleware
        server.middlewares.use((req, res, next) => {
          if (req.url === '/healthz' || req.url === '/healthz/') {
            res.statusCode = 200;
            res.setHeader('Content-Type', 'application/json');
            res.end('{"status":"ok"}');
            return;
          }
          next();
        });
      }
    }
  ],
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': `http://127.0.0.1:${apiPort}`
    }
  },
  preview: {
    host: '127.0.0.1'
  }
});

