import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

// The dev server proxies /api to the backend (override with API_URL).
export default defineConfig({
  plugins: [svelte()],
  server: { proxy: { '/api': process.env.API_URL ?? 'http://localhost:8000' } },
  test: { include: ['src/**/*.test.ts'] },
});
