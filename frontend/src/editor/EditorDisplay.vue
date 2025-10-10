<template>
	<div class="editor-display">
		<div class="tabs-container custom-scrollbar">
			<TabComponent v-for="tab in editorStore.tabs" :key="tab.id" :tab-id="tab.id" />
			<div class="add-tab material-icons" :title="newTabTitle" @click.stop.prevent="addNewGraph">add</div>
		</div>

		<template v-for="tab in editorStore.tabs" :key="tab.id">
			<GraphComponent
				v-if="!!(tab.contents instanceof Graph)"
				v-show="tab.id === editorStore.activeTabId"
				:tab-id="tab.id"
				:graph="tab.contents"
				:ref="(el) => setTabRef(tab, el)"
			/>
			<TextEditorComponent
				v-if="typeof tab.contents === 'string'"
				v-show="tab.id === editorStore.activeTabId"
				:tab-id="tab.id"
				:ref="(el) => setTabRef(tab, el)"
			/>
		</template>
	</div>
</template>

<script setup lang="ts">
	import TabComponent from '@/editor/TabComponent.vue';
	import GraphComponent from '@/editor/graph/GraphComponent.vue';
	import TextEditorComponent from '@/editor/text/TextEditorComponent.vue';
	import { Graph } from '@/graph';
	import { useEditorStore, type EditorTab } from '@/stores';
	import { computed } from 'vue';

	const editorStore = useEditorStore();

	const newTabTitle = computed(() => {
		if (editorStore.isResolvingMergeConflict) {
			return 'Cannot open new tab while resolving merge conflicts';
		} else {
			return 'New graph (Ctrl+Shift+N)';
		}
	});

	function addNewGraph() {
		if (editorStore.isResolvingMergeConflict) return;
		editorStore.newDefaultGraphTab();
	}

	function setTabRef(tab: EditorTab, component: any) {
		if (typeof tab.contents === 'string') {
			editorStore.setTextComponent(tab.id, component);
		}

		if (tab.contents instanceof Graph) {
			editorStore.setGraphComponent(tab.id, component);
		}
	}
</script>

<style scoped>
	.editor-display {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.tabs-container {
		width: 100%;
		padding-bottom: 8px;
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow-y: hidden;
		overflow-x: auto;
	}

	.add-tab {
		margin-right: 16px;
		padding: 3px;
		font-size: 1.5rem;
		color: var(--color-text-secondary);
		border-radius: 5px;
		cursor: pointer;
	}

	.add-tab:hover {
		color: var(--color-text);
		background-color: var(--color-foreground-primary);
	}
</style>
