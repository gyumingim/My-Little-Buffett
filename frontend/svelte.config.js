import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter(),
		alias: {
			'$lib': './src/lib',
			'$shared': './src/lib/shared',
			'$features': './src/lib/features',
			'$widgets': './src/lib/widgets',
			'$entities': './src/lib/entities'
		}
	}
};

export default config;
