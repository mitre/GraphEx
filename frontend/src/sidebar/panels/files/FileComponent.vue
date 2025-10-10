<template>
	<div class="file-container" :isdirectory="file.isDir" :active="isActive" :draggedover="dragEntered">
		<div
			class="file no-select"
			@click.stop.prevent="clicked"
			@dragstart="onDragStart"
			@drop.stop="onDrop"
			@dragover.prevent="onDragEnter"
			@dragenter.prevent
			@dragleave="onDragLeave"
			draggable="true"
			:style="{ 'padding-left': (props.depth || 0) * 12 + 10 + (file.isDir ? 0 : 6) + 'px' }"
			:title="filePath"
			ref="fileDiv"
		>
			<div
				v-if="fileIcon.class"
				:class="fileIcon.class"
				:style="{
					width: (fileIcon.size || 1) + 'rem',
					height: (fileIcon.size || 1) + 'rem',
					'min-width': (fileIcon.size || 1) + 'rem',
					'min-height': (fileIcon.size || 1) + 'rem'
				}"
			></div>
			<div
				v-else-if="fileIcon.icon"
				class="file-icon material-icons"
				:style="{ 'font-size': (fileIcon.size || 1) + 'rem' }"
			>
				{{ fileIcon.icon }}
			</div>
			<div class="file-name">{{ fileName }}</div>
		</div>
		<div class="directory-children" v-if="file.isDir" v-show="!collapsed">
			<template v-for="child in sortedChildren" :key="child.id">
				<FileComponent :file-id="child.id" :depth="(props.depth || 0) + 1" />
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import { Graph } from '@/graph';
import {
	GRAPH_FILE_EXTENSION,
	useContextmenuStore,
	useEditorStore,
	useFileStore,
	useMetadataStore,
	usePromptStore,
	useTerminalStore
} from '@/stores';
import { computed, nextTick, onMounted, ref } from 'vue';

	const fileStore = useFileStore();
	const editorStore = useEditorStore();
	const terminalStore = useTerminalStore();
	const contextmenuStore = useContextmenuStore();
	const metadataStore = useMetadataStore();
	const promptStore = usePromptStore();

	const props = defineProps<{
		fileId: string;
		depth?: number;
	}>();

	const fileDiv = ref<HTMLDivElement>();
	const dragEntered = ref<boolean>(false);
	const collapsed = ref<boolean>(true);

	/** The file object. */
	const file = computed(() => fileStore.findFileById(props.fileId)!);

	/** The file name for this file. */
	const fileName = computed(() => fileStore.getFileName(props.fileId));

	/** The path to the file for this tab. */
	const filePath = computed(() => fileStore.getFilePath(props.fileId));

	/** Computed value that determines the currently selected tab in the editor (top of the screen). */
	const isActive = computed(() => editorStore.activeTab && editorStore.activeTab.fileId === props.fileId);

	const sortedChildren = computed(() => [
		...file.value.children.filter((f) => f.isDir).sort((a, b) => a.name.localeCompare(b.name)),
		...file.value.children.filter((f) => !f.isDir).sort((a, b) => a.name.localeCompare(b.name))
	]);

	/**
	 * Click handler for a file.
	 * Attempts to open the graph from the file and set it as the active tab in the editor.
	 * Creates an error popup on failure by invoking the 'failedAlert' function.
	 */
	async function clicked() {
		if (file.value.isDir) {
			// Toggle 'collapsed'
			collapsed.value = !collapsed.value;
			return;
		}

		editorStore.openFileInEditor(props.fileId);
	}

	function onDragStart(ev: DragEvent) {
		ev.dataTransfer?.setData('fileId', props.fileId);
	}

	function onDragEnter() {
		dragEntered.value = true;
	}

	function onDragLeave() {
		dragEntered.value = false;
	}

	async function onDrop(ev: DragEvent) {
		onDragLeave();
		if (!file.value.isDir) {
			// Don't drop if this is a file (drop into directories only)
			return;
		}

		if (ev.dataTransfer && ev.dataTransfer.getData('fileId')) {
			const movingFileId = ev.dataTransfer.getData('fileId');
			const movingFile = fileStore.findFileById(movingFileId);
			if (!movingFile) {
				await promptStore.failedAlert('File Move Failure', 'Failed to find file (file does not exist).');
				return;
			}

			const newPath = fileStore.normalizePath(filePath.value + '/' + fileStore.getFileName(movingFile));
			if (newPath == fileStore.getFilePath(movingFile)) {
				// Don't do anything if the paths are the same
				return;
			}

			await fileStore.moveFile(movingFileId, newPath);
		}
	}

	/** Callback when the user right-clicks on the filename. Opens the custom context menu. */
	function openContextMenu(): MenuOptions | null {
		if (file.value.isDir) {
			return getDirectoryContextMenu();
		}

		return getFileContextMenu();
	}

	/**
	 * Context menu options for files.
	 */
	function getFileContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Open',
			description: 'Open and load this file into the editor.',
			callback: clicked
		});

		if (file.value.name.toLowerCase().endsWith(GRAPH_FILE_EXTENSION)) {
			entries.push({
				label: 'Open and Run',
				description: 'Open and run this file.',
				callback: async () => {
					const tabId = await editorStore.openFileInEditor(props.fileId);
					if (!tabId) {
						return;
					}

					const tab = editorStore.getTabById(tabId);
					if (tab && tab.contents instanceof Graph) {
						terminalStore.promptGraphExecution(tab.contents, fileName.value, filePath.value);
					}
				}
			});
		}

		entries.push({
			label: 'Duplicate',
			description: 'Create a copy of this file on the filesystem.',
			callback: () => fileStore.duplicateFile(props.fileId),
			divider: true
		});

		if (file.value.name.toLowerCase().endsWith(GRAPH_FILE_EXTENSION)) {
			entries.push({
				label: 'Add Execute Graph Node',
				description: 'Creates a node to execute this graph.',
				callback: () => {
					const activeGraph = editorStore.activeGraphTab?.contents;
					if (!activeGraph) return;

					const ui = activeGraph.ui;
					const viewportPositions = ui.viewportPositions();
					const width = viewportPositions.right - viewportPositions.left;
					const height = viewportPositions.bottom - viewportPositions.top;
					const x = -1 * ui.offsets.x + width / 2;
					const y = -1 * ui.offsets.y + height / 2;

					let fieldValue = filePath.value;
					if (fieldValue.toLowerCase().endsWith(GRAPH_FILE_EXTENSION))
						fieldValue = fieldValue.slice(0, fieldValue.length - GRAPH_FILE_EXTENSION.length);

					let nMetadata = metadataStore.getNode('Execute Graph');
					const addedNode = activeGraph.addNode(nMetadata, x, y, { fieldValue: fieldValue });
					nextTick(() => addedNode.centerPosition());
					addedNode.requestRefreshMetadata(0, true);
				},
				divider: true
			});
		}

		entries.push({
			label: 'Rename',
			description: 'Rename this file.',
			callback: () => fileStore.promptRename(props.fileId)
		});

		entries.push({
			label: 'Delete',
			description: 'Delete this file.',
			callback: async () => {
				const value = await promptStore.show({
					title: 'Delete File?',
					additionalInfo: "Are you sure you want to delete '" + filePath.value + "' from the source folder on disk?",
					entries: [],
					buttons: [
						{
							text: 'Delete',
							type: 'warning'
						},
						{
							text: 'Cancel',
							type: 'secondary'
						}
					]
				});

				if (!value || value.buttonName != 'Delete') {
					return;
				}

				await fileStore.deleteFile(props.fileId);
			}
		});

		return { items: entries };
	}

	/**
	 * Context menu options for files.
	 */
	function getDirectoryContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Create Subdirectory',
			description: 'Create a new directory here.',
			callback: async () => {
				collapsed.value = false;
				await fileStore.promptCreateDirectory(filePath.value + '/');
			}
		});

		entries.push({
			label: 'Create File',
			description: 'Create a new file in this directory.',
			callback: async () => {
				collapsed.value = false;
				await fileStore.promptCreateFile(filePath.value + '/');
			},
			divider: true
		});

		entries.push({
			label: 'Rename',
			description: 'Rename this folder on disk.',
			callback: () => fileStore.promptRename(props.fileId)
		});

		entries.push({
			label: 'Delete Directory',
			description: 'Delete this directory.',
			callback: async () => {
				const value = await promptStore.show({
					title: 'Delete Directory?',
					additionalInfo:
						"Are you sure you want to delete '" +
						filePath.value +
						"' from the source folder on disk? All files and directories under this directory will also be removed.",
					entries: [],
					buttons: [
						{
							text: 'Cancel',
							type: 'primary'
						},
						{
							text: 'Delete',
							type: 'warning'
						}
					]
				});

				if (!value || value.buttonName != 'Delete') {
					return;
				}

				await fileStore.deleteFile(props.fileId);
			}
		});

		return { items: entries };
	}

	/** The file icon to use for this file. 'icon' indicates a material-icon to use; 'class' indicates a class to use; 'size' indicates the size in rem (if overriding the default). */
	const fileIcon = computed(() => {
		if (file.value.isDir && collapsed.value) {
			return { icon: 'chevron_right', class: null, size: 1.2 };
		}

		if (file.value.isDir) {
			return { icon: 'expand_more', class: null, size: 1.2 };
		}

		if (file.value.name.toLowerCase().endsWith(GRAPH_FILE_EXTENSION)) {
			return { icon: null, class: 'file-logo' };
		}

		if (['.png', '.jpg', '.jpeg', '.gif', '.bmp'].some((ext) => file.value.name.toLowerCase().endsWith(ext))) {
			return { icon: 'insert_photo', class: null };
		}

		if (
			['.py', '.js', '.ts', '.html', '.css', '.vue', '.sh', '.bash', '.zsh'].some((ext) => file.value.name.toLowerCase().endsWith(ext))
		) {
			return { icon: 'code', class: null };
		}

		if (
			['.gz', '.zip', '.7z', '.xz'].some((ext) => file.value.name.toLowerCase().endsWith(ext))
		) {
			return { icon: 'folder_zip', class: null };
		}

		if (file.value.name.toLowerCase().endsWith('.md')) {
			return { icon: 'info_outline', class: null };
		}

		if (['.json', '.yml'].some((ext) => file.value.name.toLowerCase().endsWith(ext))) {
			return { icon: 'data_object', class: null };
		}

		if (['.conf', '.toml', '.in'].some((ext) => file.value.name.toLowerCase().endsWith(ext))) {
			return { icon: 'settings', class: null };
		}

		return { icon: 'description', image: null };
	});

	/** Mounts the custom context menu created when the user right clicks on the filename. */
	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(fileDiv.value!, openContextMenu, false);
	});
</script>

<style scoped>
	.file-container {
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.file {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
		cursor: pointer;
		padding: 6px 0px;
	}

	.file-container[active='true'] > .file {
		background-color: var(--color-foreground-secondary);
	}

	.file-container[active='true'] .file-name {
		color: var(--color-primary);
	}

	.file-container > .file:hover {
		background-color: var(--color-foreground-secondary);
	}

	.file-container[isdirectory='true'][draggedover='true'] > .file {
		outline: 1px solid var(--color-border);
		background-color: var(--color-foreground-secondary);
	}

	.file-icon {
		margin-right: 6px;
		color: var(--color-text-secondary);
	}

	.file-logo {
		margin-right: 6px;
		background-image: url('/logo.png');
		background-position: center;
		background-repeat: no-repeat;
		background-size: 100% 100%;
	}

	.file-name {
		color: var(--color-text);
		padding-right: 15px;
		white-space: pre;
		text-overflow: ellipsis;
		overflow: hidden;
	}

	.directory-children {
		width: 100%;
		display: flex;
		flex-direction: column;
	}
</style>
