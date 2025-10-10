<template>
	<ModalComponent class="graphex-modal" title="Open Log File" @close="onClose">
		<template v-slot:contents>
			<div v-if="fileNames && fileNames.length > 0">
				<table class="log-file-table">
					<thead class="log-file-table-headers">
						<th>Graph Name</th>
						<th>Unix Timestamp</th>
						<th>Created Date</th>
						<th>Created Time</th>
					</thead>
					<tbody>
						<template v-for="(name, index) in fileNames" :key="index">
							<LogFileComponent @close="onClose" :name="name" :path="fileNamesFilePaths[name]"></LogFileComponent>
						</template>
					</tbody>
				</table>
			</div>
			<span v-else class="no-files"> No log files found! </span>
		</template>
	</ModalComponent>
</template>

<script setup lang="ts">
	import { usePromptStore } from '@/stores';
	import { onMounted, ref } from 'vue';
	import LogFileComponent from './LogFileComponent.vue';
	import ModalComponent from './ModalComponent.vue';

	const promptStore = usePromptStore();

	const fileNamesFilePaths = ref<{ [key: string]: string }>({});
	const fileNames = ref<string[]>();

	function onClose() {
		promptStore.openLogModalOpen = false;
	}

	onMounted(async () => {
		try {
			const response = await fetch('/api/logs', { method: 'GET' });
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
			fileNamesFilePaths.value = data['filename_filepath'];
			fileNames.value = Object.keys(fileNamesFilePaths.value).sort();
		} catch (e) {
			promptStore.openLogModalOpen = false;
			await promptStore.failedAlert(
				'Failed to Get Logs',
				`Failed to get logs from server (${e instanceof Error ? e.toString() : String(e)})`
			);
			return;
		}
	});
</script>

<style scoped>
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

	:deep(.modal-title) {
		width: 100%;
		text-align: center;
	}

	.no-files {
		color: var(--color-error);
	}

	.log-file-table {
		table-layout: fixed;
		width: 100%;
		border-collapse: collapse;
	}

	th,
	td {
		padding: 20px;
	}

	tbody td th {
		text-align: center;
	}

	.log-file-table-headers {
		color: var(--color-text-secondary);
	}
</style>
