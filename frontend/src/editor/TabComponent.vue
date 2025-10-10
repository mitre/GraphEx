<template>
	<div
		class="tab no-select"
		:active="isActive"
		:needs-save="needsSave"
		@click="onTabClick"
		ref="tabElement"
		:draggable="!editTabName"
		@dragstart="onDragStart"
		@dragenter.prevent
		@dragover.prevent
		@drop.prevent="onDrop"
	>
		<div class="tab-info">
			<div
				class="tab-name"
				:title="tabName"
				:contenteditable="editTabName"
				@dblclick="onNameDoubleClick"
				@blur="onNameBlur"
				@keydown.enter.stop="triggerNameBlur"
				@keydown.stop
				ref="tabNameElement"
			>
				{{ tabName }}
			</div>
			<div class="tab-path" :title="filePath" v-if="filePath">
				{{ filePath }}
			</div>
		</div>

		<div class="tab-close material-icons" title="Close" @click.stop="onCloseClick"></div>
	</div>
</template>

<script setup lang="ts">
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
	import { useContextmenuStore, useEditorStore, useFileStore, usePromptStore } from '@/stores';
	import { computed, nextTick, onMounted, ref } from 'vue';

	const props = defineProps<{
		tabId: string;
	}>();

	const promptStore = usePromptStore();
	const contextmenuStore = useContextmenuStore();
	const editorStore = useEditorStore();
	const fileStore = useFileStore();

	const editTabName = ref<boolean>(false);
	const tabNameElement = ref<HTMLDivElement>();
	const tabElement = ref<HTMLDivElement>();

	/** The tab object. */
	const tab = computed(() => editorStore.getTabById(props.tabId));

	/** Whether this tab is the active tab. */
	const isActive = computed(() => props.tabId == editorStore.activeTabId);

	/** Whether this tab needs saving. */
	const needsSave = computed(() => editorStore.tabHasChanges(props.tabId));

	/** The name of this tab. */
	const tabName = computed(() => tab.value?.name || '');

	/** The path to the file for this tab, if one exists. */
	const filePath = computed(() => (tab.value && tab.value.fileId ? fileStore.getFilePath(tab.value.fileId) : null));

	function onDragStart(ev: DragEvent) {
		ev.dataTransfer!.dropEffect = 'move';
		ev.dataTransfer!.effectAllowed = 'move';
		ev.dataTransfer!.setData('tabId', props.tabId);
	}

	function onDrop(ev: DragEvent) {
		if (ev.dataTransfer && ev.dataTransfer.getData('tabId')) {
			const movingTabId = ev.dataTransfer.getData('tabId');
			if (movingTabId === props.tabId) {
				return;
			}
			editorStore.reorderTabs(movingTabId, props.tabId);
		}
	}

	function onTabClick() {
		editorStore.setActiveTab(props.tabId);
		if (editorStore.isResolvingMergeConflict) {
			// Check if any nodes need to be highlighted
			if (editorStore.selectedIssueNodeId !== '') {
				try {
					const node = editorStore?.activeGraphTab?.contents.getNode(editorStore.selectedIssueNodeId);
					if (node) {
						node?.graph.ui.deHighlightAllNodes();
						node?.graph.ui.highlightNode(node);
						nextTick(() => {
							editorStore?.activeGraphTab?.contents.ui.resetZoom();
							editorStore?.activeGraphTab?.contents.ui.navigateUiToNodeLocation(node);
						});
					}
				} catch (e) {
					console.error(e);
				}
			}
		}
	}

	function onCloseClick() {
		handleClose();
	}

	function onNameDoubleClick() {
		triggerRename();
	}

	function triggerRename() {
		editTabName.value = true;
		nextTick(() => {
			tabNameElement.value?.focus();
		});
	}

	function triggerNameBlur() {
		tabNameElement.value?.blur();
	}

	async function onNameBlur() {
		editTabName.value = false;
		if (!tabNameElement.value) {
			return;
		}

		const oldName = tabName.value;
		let newName = (tabNameElement.value.textContent || '').trim();
		if (newName == oldName) {
			// Name wasn't changed
			return;
		}

		// add the gx extension if one is missing now
		if (oldName.toLowerCase().endsWith('.gx') && !newName.toLowerCase().endsWith('.gx')) {
			newName += '.gx';
		}

		if (!(await editorStore.renameTab(props.tabId, newName))) {
			// Rename failed, reset the value
			tabNameElement.value.textContent = oldName;
		}
	}

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Rename',
			description: 'Rename this file.',
			callback: triggerRename
		});

		entries.push({
			label: 'Close',
			description: 'Close this tab.',
			callback: handleClose
		});

		entries.push({
			label: 'Close all Tabs',
			description: 'Close all open graphs.',
			callback: closeAllTabs
		});

		return { items: entries };
	}

	async function handleClose() {
		if (!needsSave.value) {
			editorStore.removeTab(props.tabId);
			return;
		}

		const value = await promptStore.show({
			title: 'Unsaved Changes',
			additionalInfo: `You have unsaved changes to '${filePath.value}''.`,
			entries: [],
			buttons: [
				{
					text: 'Save and Close',
					hint: 'Save and close the file.',
					type: 'primary'
				},
				{
					text: 'Close',
					hint: 'Close the file without saving.',
					type: 'warning'
				},
				{
					text: 'Cancel',
					hint: 'Cancel closing the graph.',
					type: 'secondary'
				}
			]
		});

		if (!value || value.buttonName == 'Cancel') {
			return;
		}

		// Close
		if (value.buttonName == 'Close') {
			editorStore.removeTab(props.tabId);
			return;
		}

		// Save and Close
		if (value.buttonName == 'Save and Close') {
			const success = await editorStore.saveTab(props.tabId);
			if (success) {
				editorStore.removeTab(props.tabId);
			}
		}
	}

	async function closeAllTabs() {
		const unsavedTabNames = editorStore.tabs.filter((t) => editorStore.tabHasChanges(t.id));
		if (unsavedTabNames.length === 0) {
			for (const t of Array.from(editorStore.tabs)) {
				editorStore.removeTab(t.id);
			}
			return;
		}

		let unsavedText =
			'There are tabs with unsaved changes. Are you sure you want to close all tabs?\n\nThe unsaved tabs are: ' +
			unsavedTabNames.join(', ');

		const value = await promptStore.show({
			title: 'Unsaved Graphs',
			additionalInfo: unsavedText,
			entries: [],
			buttons: [
				{
					text: 'Save and Close Tabs',
					hint: 'Save and close all tabs.',
					type: 'primary'
				},
				{
					text: 'Close Tabs',
					hint: 'Close all tabs without saving.',
					type: 'warning'
				},
				{
					text: 'Cancel',
					hint: 'Cancel closing the tabs.',
					type: 'secondary'
				}
			]
		});

		if (!value || value.buttonName == 'Cancel') {
			return;
		}

		// Close
		if (value.buttonName == 'Close Tabs') {
			for (const t of Array.from(editorStore.tabs)) {
				editorStore.removeTab(t.id);
			}
			return;
		}

		// Save and Close
		if (value.buttonName == 'Save and Close Tabs') {
			for (const t of Array.from(editorStore.tabs)) {
				if (await editorStore.saveTab(t.id)) {
					editorStore.removeTab(t.id);
				} else {
					continue;
				}
			}
		}
	}

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(tabElement.value!, openContextMenu, false);
	});
</script>

<style scoped>
	.tab {
		height: 38px;
		min-height: 38px;
		margin-right: 8px;
		padding-left: 12px;
		padding-right: 6px;
		display: flex;
		flex-direction: row;
		align-items: center;
		background-color: var(--color-foreground-primary);
		border-radius: 5px;
		cursor: pointer;
	}

	.tab[active='true'] {
		background-color: var(--color-foreground-secondary);
	}

	.tab-name {
		outline: none;
		border: none;
		white-space: pre;
		color: var(--color-text-secondary);
	}

	.tab-path {
		max-width: 150px;
		outline: none;
		border: none;
		white-space: nowrap;
		text-overflow: ellipsis;
		color: var(--color-text-secondary);
		opacity: 0.6;
		overflow: hidden;
		font-size: 0.8rem;
		margin-left: 8px;
	}

	.tab-info {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.tab-name[contenteditable='true'] {
		border-bottom: 1px dotted var(--color-text);
		padding: 0px 1rem;
		cursor: text;
	}

	.tab-name[contenteditable='false'] {
		max-width: 15rem;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.tab[active='true'] .tab-name {
		color: var(--color-text);
	}

	.tab-close {
		width: 18px;
		height: 18px;
		margin-left: 6px;
		border-radius: 5px;
		color: var(--color-text);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.tab[active='true'][needs-save='false'] .tab-close::before {
		content: 'close';
		font-size: 16px;
	}

	.tab:hover .tab-close::before {
		content: 'close';
		font-size: 16px;
	}

	.tab[needs-save='true'] .tab-close::before {
		content: 'circle';
		font-size: 12px;
	}

	.tab-close:hover {
		background-color: var(--color-foreground-tertiary);
	}

	.tab-close:hover.tab-close::before {
		content: 'close';
		font-size: 16px;
	}

	/* .tab[active='true'] .tab-close {
		opacity: 1;
	}

	.tab[active='false']:hover .tab-close {
		opacity: 0.7;
	} */

	/* .tab-close[needs-save='true'] .tab-close:not(:hover) .tab-needs-save-icon {
		display: inline;
	}

	.tab-close .tab-close:hover .tab-close-icon {
		display: inline;
	} */
</style>
