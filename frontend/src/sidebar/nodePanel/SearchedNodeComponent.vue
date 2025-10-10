<template>
	<div
		class="node-metadata-container no-select"
		title="Click to focus on this node."
		@click="navigateToNode"
		@mouseover="onMouseOver"
		@mouseleave="onMouseLeave"
	>
		<div class="node-metadata-body">
			<div class="node-metadata-title no-select">
				{{ displayName }}
			</div>
			<span class="description no-select">{{ node.metadata.description }}</span>
		</div>
		<span class="node-color" :style="colorStyles"></span>
	</div>
</template>

<script setup lang="ts">
	import { NodeTypes, type GraphNode } from '@/graph';
import { useEditorStore, useMetadataStore } from '@/stores';
import { computed } from 'vue';

	const props = defineProps<{
		node: GraphNode;
	}>();

	const displayName = computed(() => {
		if (props.node.metadata.isInventoryNode) {
			return props.node.metadata.name.replace('$', '\n');
		}
		return props.node.metadata.name;
	});

	const editorStore = useEditorStore();
	const metadataStore = useMetadataStore();

	function navigateToNode() {
		if (editorStore.activeGraphTab) {
			const node = editorStore.activeGraphTab.contents.getNode(props.node.id);
			if (node) {
				const ui = editorStore.activeGraphTab.contents.ui;
				ui.deselectAllNodes();
				ui.selectNode(node);
				ui.resetZoom();
				ui.navigateUiToNodeLocation(node);
			}
		}
	}

	function onMouseOver() {
		props.node.graph.ui.highlightNode(props.node);
	}

	function onMouseLeave() {
		props.node.graph.ui.deHighlightNode(props.node);
	}

	const colorStyles = computed(() => {
		if (props.node.metadata.type == NodeTypes.CAST) {
			const inputSocket = props.node.metadata.sockets.find((socket) => socket.isInput)!;
			const inputDataType = metadataStore.getDataType(inputSocket.datatype!);

			const outputSocket = props.node.metadata.sockets.find((socket) => !socket.isInput)!;
			const outputDataType = metadataStore.getDataType(outputSocket.datatype!);

			return {
				background: `linear-gradient(90deg, ${inputDataType.color} 0%, ${inputDataType.color} 40%, ${outputDataType.color} 60%, ${outputDataType.color} 100%)`
			};
		}

		return {
			'background-color': props.node.metadata.color
		};
	});
</script>

<style scoped>
	.node-metadata-container {
		width: 100%;
		margin-top: 0.5rem;
		display: flex;
		flex-direction: column;
		background-color: var(--color-background-primary);
	}

	.node-metadata-container {
		cursor: alias;
	}

	.node-metadata-body {
		width: 100%;
		padding: 0.5rem;
		display: flex;
		flex-direction: column;
	}

	.node-metadata-title {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		color: var(--color-text);
	}

	.description {
		margin-top: 4px;
		color: var(--color-text);
		opacity: 0.5;
		font-style: italic;
		font-size: 0.8rem;
		white-space: pre-wrap;
	}

	.node-color {
		width: 100%;
		height: 3px;
		opacity: 0.4;
	}

	.node-metadata-container:hover .node-color {
		opacity: 1;
		transition: opacity 100ms linear;
	}
</style>
