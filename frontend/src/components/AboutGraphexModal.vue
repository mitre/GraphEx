<template>
	<ModalComponent class="graphex-modal" title="About Graphex" @close="onClose">
		<template v-slot:contents>
			<span class="plugin-name">graphex: </span>
			<span> {{ graphexInfo }} </span>
			<br />
			<br />
			<span> {{ configInfo }}</span>
			<template v-if="configInfoPath != ''">
				<br />
				<span>{{ configInfoPath }}</span>
			</template>
			<br />
			<br />
			<span>Current virtual environment: {{ venvInfo }}</span>
			<br />
			<br />
			<span>Current git branch: {{ branchInfo }}</span>
			<br />
			<br />
			<template v-if="pluginsInfos.length <= 0">
				<span class="plugins-missing"> No plugins are loaded. </span>
			</template>
			<h4 v-else class="loaded-plugins-title">Loaded Plugins</h4>
			<template v-for="(plugin, index) in pluginsInfos" :key="index">
				<span class="plugin-name">{{ plugin.name }}: </span>
				<span>{{ plugin.version }}</span>
				<br />
			</template>
		</template>
	</ModalComponent>
</template>

<script setup lang="ts">
	import { usePromptStore } from '@/stores';
	import { onMounted, ref } from 'vue';
	import ModalComponent from './ModalComponent.vue';

	interface pluginInfo {
		name: string;
		version: string;
	}

	const promptStore = usePromptStore();

	const graphexInfo = ref<string>('');
	const configInfo = ref<string>('');
	const configInfoPath = ref<string>('');
	const pluginsInfos = ref<Array<pluginInfo>>([]);
	const venvInfo = ref<string>('');
	const branchInfo = ref<string>('');

	function onClose() {
		promptStore.closeAboutGraphexModal();
	}

	onMounted(async () => {
		try {
			const response = await fetch('/api/packageInfo', { method: 'GET' });
			if (!response.ok) {
				let errorText = '';
				try {
					errorText = await response.text();
				} catch (e) {
					errorText = `Bad status code ${String(response.status)}`;
				}
				throw errorText;
			}
			const data = await response.json();
			graphexInfo.value = data['graphex'];
			for (const [key, value] of Object.entries(data['plugins'])) {
				pluginsInfos.value.push({
					name: key,
					version: String(value)
				});
			}
			configInfo.value = data['config'];
			const i = configInfo.value.indexOf('/');
			if (i >= 0) {
				configInfoPath.value = configInfo.value.substring(i);
				configInfo.value = configInfo.value.substring(0, i);
			}
			venvInfo.value = data['venv'];
			branchInfo.value = data['branch'];
		} catch (e) {
			promptStore.closeAboutGraphexModal();
			await promptStore.failedAlert(
				'Failed to Get Information',
				`Failed to get GraphEX Information (${e instanceof Error ? e.toString() : String(e)})`
			);
			return;
		}
	});
</script>

<style scoped>
	.graphex-modal {
		text-align: left;
		color: var(--color-text);
	}

	:deep(.modal-popup) {
		max-width: 800px;
		max-height: 600px;
		overflow: auto;
		white-space: nowrap;
	}

	:deep(.modal-contents) {
		padding-right: 16px;
		display: block;
	}

	.plugin-name {
		color: var(--color-primary);
	}

	.plugins-missing {
		color: var(--color-error);
	}

	.loaded-plugins-title {
		color: var(--color-text-secondary);
	}
</style>
