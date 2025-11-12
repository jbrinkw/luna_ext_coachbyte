import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command, mode }) => {
  // Get port from CLI args or use default
  const port = process.env.PORT ? parseInt(process.env.PORT) : 5200;

  // Load .env file from repo root (3 levels up: ui -> extension -> extensions -> root)
  const env = loadEnv(mode, '../../../', '');
  Object.assign(process.env, env);

  const backendTarget = env.COACHBYTE_BACKEND || 'http://127.0.0.1:5301';

  // Build allowed hosts list - support all deployment modes
  const allowedHosts = [];

  // ngrok mode: TUNNEL_HOST
  if (env.TUNNEL_HOST) {
    allowedHosts.push(env.TUNNEL_HOST);
  }

  // nip_io or custom_domain mode: PUBLIC_DOMAIN
  if (env.PUBLIC_DOMAIN) {
    allowedHosts.push(env.PUBLIC_DOMAIN);
  }

  return {
    envPrefix: ['VITE_', 'DAY_'],
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
    base: '/ext/coachbyte/',
    server: {
      port: port,
      host: '127.0.0.1',
      strictPort: true,
      ...(allowedHosts.length > 0 && { allowedHosts }),  // Only add if we have hosts to allow
      proxy: {
        '/api/coachbyte': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api\/coachbyte/, '/api'),
        },
      },
    },
    preview: {
      host: '127.0.0.1'
    }
  };
});
