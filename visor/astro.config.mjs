import { defineConfig } from 'astro/config';

// Visor del cerebro. Sin integraciones: HTML, CSS y un poco de JS.
// Los datos los lee src/lib/cerebro.mjs de KUMIKO_CEREBRO en tiempo de build.
export default defineConfig({ site: 'http://localhost:4321' });
