import { defineConfig } from 'vitest/config';
import preact from '@preact/preset-vite';
import { resolve } from 'path';

export default defineConfig({
  plugins: [preact()],
  test: {
    // Environment
    environment: 'jsdom',
    
    // Global setup
    globals: true,
    
    // Test file patterns
    include: ['tests/**/*.{test,spec}.{ts,tsx}', 'src/**/*.{test,spec}.{ts,tsx}'],
    exclude: [
      'node_modules',
      'dist',
      '.idea',
      '.git',
      '.cache',
      // Playwright tests (E2E, visual, performance, audit) - run with `npx playwright test`
      'tests/e2e/**',
      'tests/visual/**',
      'tests/performance/**',
      'tests/audit/**',
    ],
    
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/main.tsx',
        'src/vite-env.d.ts',
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 70,
        statements: 80,
      },
    },
    
    // Setup files
    setupFiles: ['./tests/setup.ts'],
    
    // Reporters
    reporters: ['verbose'],
    
    // Performance
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
      },
    },

    // Force teardown even if async operations are pending (prevents hang)
    teardownTimeout: 5000,
    
    // Mock cleanup settings (ensure test isolation)
    restoreMocks: true,
    clearMocks: true,
    unstubGlobals: true,
    
    // Timeout settings
    testTimeout: 10000,    // 10s per individual test
    hookTimeout: 10000,    // 10s per setup/teardown hook
    
    // Bail out on first failure if too many tests fail (helps catch infinite loops)
    bail: 5,
    
    // Fail fast on unhandled errors
    dangerouslyIgnoreUnhandledErrors: false,
  },
  
  // Path aliases (must match tsconfig.json)
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@components': resolve(__dirname, './src/components'),
      '@services': resolve(__dirname, './src/services'),
      '@models': resolve(__dirname, './src/models'),
      '@hooks': resolve(__dirname, './src/hooks'),
      '@styles': resolve(__dirname, './src/styles'),
      '@utils': resolve(__dirname, './src/utils'),
      '@lib': resolve(__dirname, './src/lib'),
      '@types': resolve(__dirname, './src/types'),
    },
  },
});
