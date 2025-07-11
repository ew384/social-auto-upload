import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  build: {
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue'],
          elementPlus: ['element-plus']
        },
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js'
      }
    },
    reportCompressedSize: true,
    chunkSizeWarningLimit: 1000,
    outDir: 'dist',
    assetsDir: 'assets'
  },
  define: {
    __VUE_PROD_DEVTOOLS__: false,
  }
})
