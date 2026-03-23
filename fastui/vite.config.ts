import { defineConfig } from 'vite';
import cssInjectedByJsPlugin from 'vite-plugin-css-injected-by-js';
import { resolve } from 'path';

export default defineConfig(({ mode }) => ({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'FastUI',
      formats: ['iife', 'es'],
      fileName: (format) => {
        const suffix = mode === 'production' ? '.min' : '';
        return format === 'es' ? `fast-ui.es${suffix}.js` : `fast-ui${suffix}.js`;
      },
    },
    outDir: 'dist',
    sourcemap: mode === 'production' ? false : true,
    minify: mode === 'production' ? 'terser' : false,
    terserOptions: mode === 'production' ? {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info'],
      },
      format: {
        comments: false,
      },
    } : undefined,
    rollupOptions: {
      output: {
        globals: {
          alpinejs: 'Alpine',
          'htmx.org': 'htmx',
          echarts: 'echarts',
        },
      },
    },
  },
  plugins: [
    cssInjectedByJsPlugin({
      styleId: 'fast-ui-styles',
      useStrictCSP: true,
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  define: {
    __DEV__: mode !== 'production',
    __VERSION__: JSON.stringify(require('./package.json').version),
  },
}));
