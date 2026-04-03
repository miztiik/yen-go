import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';
import { resolve, join, relative } from 'path';
import { existsSync, statSync, readFileSync } from 'fs';
import type { Plugin } from 'vite';
import type { ServerResponse, IncomingMessage } from 'http';

/**
 * Plugin to serve static files from project root
 * This includes:
 * 1. /yengo-puzzle-collections/ -> ../yengo-puzzle-collections/
 * 2. /config/ -> ../config/
 */
function serveRootStaticFiles(): Plugin {
  const mounts: Record<string, string> = {
    '/yengo-puzzle-collections/': resolve(__dirname, '../yengo-puzzle-collections'),
    '/config/': resolve(__dirname, '../config'),
  };
  
  return {
    name: 'serve-root-static-files',
    enforce: 'pre',
    configureServer(server) {
      const basePath = server.config.base?.replace(/\/$/, '') || '';

      server.middlewares.use((req: IncomingMessage, res: ServerResponse, next: () => void) => {
        const url = req.url || '';
        const urlPath = url.split('?')[0]; // Parse URL to get clean path (remove query string)

        // Strip base path prefix (e.g. '/yen-go') so mount points match.
        const cleanPath = basePath && urlPath.startsWith(basePath)
          ? urlPath.slice(basePath.length) || '/'
          : urlPath;
        
        // Find matching mount point
        const mountPoint = Object.keys(mounts).find(mount => cleanPath.startsWith(mount));
        
        // Only intercept requests for mounted paths
        if (!mountPoint) {
          return next();
        }
        
        const rootPath = mounts[mountPoint];
        const relativePath = cleanPath.replace(mountPoint, '');
        
        // Prevent directory traversal
        if (relativePath.includes('..')) {
          console.log(`[serve-root-static-files] Blocked path traversal: ${relativePath}`);
          return next();
        }
        
        const filePath = join(rootPath, relativePath);
        
        // Check if file exists
        try {
          if (!existsSync(filePath) || !statSync(filePath).isFile()) {
            console.log(`[serve-root-static-files] Not found: ${mountPoint}${relativePath}`);
            return next();
          }
        } catch {
          return next();
        }
        
        // Determine content type and encoding
        const ext = relativePath.split('.').pop()?.toLowerCase() || '';
        const textTypes: Record<string, string> = {
          'json': 'application/json; charset=utf-8',
          'sgf': 'text/plain; charset=utf-8',
        };
        const contentType = textTypes[ext] || 'application/octet-stream';
        const isText = ext in textTypes;
        
        // Read and serve file (binary for .db/.wasm, text for .json/.sgf)
        try {
          const content = isText ? readFileSync(filePath, 'utf-8') : readFileSync(filePath);
          res.writeHead(200, {
            'Content-Type': contentType,
            'Cache-Control': 'no-cache',
            'X-Served-By': 'vite-plugin-serve-root-static-files',
          });
          res.end(content);
          console.log(`[serve-root-static-files] Served: ${relativePath} from ${mountPoint}`);
        } catch (err) {
          console.error(`[serve-root-static-files] Error:`, err);
          return next();
        }
      });
      
      console.log('[serve-root-static-files] Plugin initialized');
      Object.entries(mounts).forEach(([url, rootPath]) => {
        console.log(`[serve-root-static-files] Mounting ${url} -> ${relative(process.cwd(), rootPath)}`);
      });
    },
  };
}

export default defineConfig({
  base: '/yen-go/',
  assetsInclude: ['**/*.wasm'],
  define: {
    CLIENT: JSON.stringify(true),
    SERVER: JSON.stringify(false),
  },
  plugins: [
    serveRootStaticFiles(), // Must be first to intercept before public/ serving
    tailwindcss(),
    preact(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'robots.txt'],
      manifest: {
        name: 'Yen-Go - Go Puzzles',
        short_name: 'Yen-Go',
        description: 'Offline Go (Baduk/Weiqi) puzzle platform',
        theme_color: '#3B6D96',
        background_color: '#1a1a2e',
        display: 'standalone',
        icons: [
          {
            src: '/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,wasm}'],
        runtimeCaching: [
          {
            // Cache manifest.json with stale-while-revalidate (FR-030a)
            urlPattern: /\/puzzles\/manifest\.json$/i,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'manifest-cache',
              expiration: {
                maxEntries: 1,
                maxAgeSeconds: 60 * 60 * 24, // 1 day
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            // Cache level JSON files with stale-while-revalidate (FR-030a)
            urlPattern: /\/puzzles\/levels\/.*\.json$/i,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'level-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 7, // 7 days
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            // Cache external puzzle data with network-first
            urlPattern: /^https:\/\/.*\.json$/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'external-data-cache',
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 * 24 * 7, // 7 days
              },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      'react': 'preact/compat',
      'react-dom': 'preact/compat',
      'react/jsx-runtime': 'preact/jsx-runtime',
      'react-dom/test-utils': 'preact/test-utils',
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@services': resolve(__dirname, 'src/services'),
      '@models': resolve(__dirname, 'src/models'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@styles': resolve(__dirname, 'src/styles'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@lib': resolve(__dirname, 'src/lib'),
      '@types': resolve(__dirname, 'src/types'),
      '@config': resolve(__dirname, 'src/config'),
    },
  },
  optimizeDeps: {
    include: ['sql.js'],
  },
  build: {
    target: 'es2020',
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    fs: {
      // Allow serving files from parent directory (yengo-puzzle-collections)
      allow: ['..'],
    },
  },
});
