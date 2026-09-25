import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({
  plugins: [vue()],
  // Library mode otherwise leaves Vue's Node environment check in browser JS.
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: { outDir: '../app/static', emptyOutDir: true, lib: { entry: 'main.js', formats: ['es'], fileName: () => 'site.js', cssFileName: 'site' } }
});
