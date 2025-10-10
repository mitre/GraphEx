<template>
	<SidebarPanel
		header="Files"
		ref="sidebarPanelRef"
		@drop.stop.prevent="onDrop"
		@dragenter.stop.prevent
		@dragleave.stop.prevent
		@dragover.stop.prevent
	>
		<template v-slot:buttons>
			<span class="material-icons file-button" title="Create New Graph File" @click="() => fileStore.promptCreateFile()"
				>add</span
			>
			<span
				class="material-icons file-button"
				title="Create New Directory"
				@click="() => fileStore.promptCreateDirectory()"
			>
				create_new_folder
			</span>
			<span class="material-icons file-button" title="Refresh File Browser" @click="() => fileStore.refreshFiles()"
				>refresh</span
			>
		</template>
		<div class="file-tree-root">
			<template v-for="file in sortedFiles" :key="file.id">
				<FileComponent :file-id="file.id" />
			</template>
		</div>
	</SidebarPanel>
</template>

<script setup lang="ts">
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
	import SidebarPanel from '@/sidebar/SidebarPanel.vue';
	import FileComponent from '@/sidebar/panels/files/FileComponent.vue';
	import { useContextmenuStore, useFileStore, usePromptStore } from '@/stores';
	import { computed, onMounted, ref } from 'vue';

	const fileStore = useFileStore();
	const contextmenuStore = useContextmenuStore();
	const promptStore = usePromptStore();

	const sidebarPanelRef = ref<InstanceType<typeof SidebarPanel> | null>(null);

	const sortedFiles = computed(() => [
		...fileStore.files.filter((f) => f.isDir).sort((a, b) => a.name.localeCompare(b.name)),
		...fileStore.files.filter((f) => !f.isDir).sort((a, b) => a.name.localeCompare(b.name))
	]);

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Create Directory...',
			description: 'Create a new directory',
			callback: () => fileStore.promptCreateDirectory()
		});

		entries.push({
			label: 'Create File...',
			description: 'Create a new file',
			callback: () => fileStore.promptCreateFile()
		});

		entries.push({
			label: 'Refresh Files',
			description: 'Updates the panel for changes made outside GraphEX',
			callback: () => fileStore.refreshFiles()
		});

		return { items: entries };
	}

	async function onDrop(ev: DragEvent) {
		if (ev.dataTransfer && ev.dataTransfer.getData('fileId')) {
			const movingFileId = ev.dataTransfer.getData('fileId');
			const movingFile = fileStore.findFileById(movingFileId);
			if (!movingFile) {
				await promptStore.failedAlert('File Move Failure', 'Failed to find file (file does not exist).');
				return;
			}

			if (!movingFile.parent) {
				// Already at the top level
				return;
			}

			await fileStore.moveFile(movingFile.id, fileStore.getFileName(movingFile));
		}
	}

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(sidebarPanelRef.value!.panel!, openContextMenu, false);
	});
</script>

<style scoped>
	:deep(.header-bar) {
		margin-bottom: 0rem;
	}

	.file-button {
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.6;
	}

	.file-button:not(:last-child) {
		margin-right: 2px;
	}

	.file-button:hover {
		color: var(--color-primary);
		cursor: pointer;
		opacity: 1;
	}

	.file-tree-root {
		display: flex;
		flex-direction: column;
		margin-bottom: 8px;
	}
</style>
