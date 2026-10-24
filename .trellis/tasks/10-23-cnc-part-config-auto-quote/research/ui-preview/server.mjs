import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../../../../..');
const frontend = path.join(repo, 'frontend/web');
const require = createRequire(path.join(frontend, 'package.json'));
const { createServer } = await import(require.resolve('vite'));
const { default: vue } = await import(require.resolve('@vitejs/plugin-vue'));
const server = await createServer({
  configFile: false,
  root: here,
  plugins: [vue()],
  resolve: {
    alias: [
      { find: /^vue$/, replacement: require.resolve('vue/dist/vue.esm-bundler.js') },
      { find: /^element-plus$/, replacement: require.resolve('element-plus') },
      { find: '@element-css', replacement: require.resolve('element-plus/dist/index.css') },
      { find: '@utils', replacement: path.join(here, 'stub.ts') },
      { find: '@quote-ui', replacement: path.join(frontend, 'src/views/module_cnc/cnc_part_config') },
      { find: '@', replacement: path.join(frontend, 'src') },
    ],
  },
  server: { host: '127.0.0.1', port: 5189, strictPort: true, open: false, fs: { allow: [repo] } },
});
await server.listen();
console.log('LOCAL_SYNTHETIC_QUOTE_PREVIEW http://127.0.0.1:5189');
