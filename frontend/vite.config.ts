import { fileURLToPath, URL } from 'node:url';

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// https://vitejs.dev/config/
export default defineConfig({
	root: __dirname,
	plugins: [vue()],
	resolve: {
		alias: {
			'@': fileURLToPath(new URL('./src', import.meta.url))
		}
	},
	server: {
		watch: {
			usePolling: true
		},
		proxy: {
			'/api': 'http://localhost:8080'
		}
	},
	build: {
		outDir: '../graphex/website',
		emptyOutDir: true
	}
});
