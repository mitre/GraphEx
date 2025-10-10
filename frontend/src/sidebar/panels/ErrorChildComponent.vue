<template>
	<div
		class="error-container no-select"
		title="Click to focus on this node."
		@click="navigateToNode"
		@mouseover="onMouseOver"
		@mouseleave="onMouseLeave"
	>
		<div class="error-body">
			<div class="error-node-name no-select">
				{{ node ? node.metadata.name : 'N/A' }}
			</div>
			<div class="error-socket-name no-select">
				{{ errorLocationName }}
			</div>
			<span class="error-description no-select" :style="computedColor">{{ props.msg }}</span>
		</div>
		<span class="node-color" :style="colorStyles"></span>
	</div>
</template>

<script setup lang="ts">
	import { NodeTypes } from '@/graph';
import { useEditorStore, useMetadataStore } from '@/stores';
import { computed } from 'vue';

	export interface SocketErrorInfo {
		msg: string;
		nodeId: string;
		socketName: string;
		isWarning?: boolean;
	}

	const props = defineProps<SocketErrorInfo>();

	const editorStore = useEditorStore();
	const metadataStore = useMetadataStore();

	function navigateToNode() {
		if (editorStore.activeGraphTab && node.value) {
			const ui = editorStore.activeGraphTab.contents.ui;
			ui.deselectAllNodes();
			ui.selectNode(node.value);
			ui.resetZoom();
			ui.navigateUiToNodeLocation(node.value);
		}
	}

	function onMouseOver() {
		if (node.value) node.value.graph.ui.highlightNode(node.value);
	}

	function onMouseLeave() {
		if (node.value) node.value.graph.ui.deHighlightNode(node.value);
	}

	const computedColor = computed(() => {
		if (props.isWarning) {
			return {
				'color': "rgb(255, 185, 15)"
			};
		}
		return {
			'color': "rgb(189, 47, 28)"
		};
	});

	const errorLocationName = computed(() => {
		const socketName = props.socketName;
		if (socketName === '_forward') return 'Forward Link';
		if (socketName === '_backward') return 'Backward Link';
		return socketName;
	});

	const node = computed(() => {
		if (!editorStore.activeGraphTab) {
			return undefined;
		}

		try {
			return editorStore.activeGraphTab.contents.getNode(props.nodeId);
		} catch {
			return undefined;
		}
	});

	const colorStyles = computed(() => {
		if (node.value) {
			if (node.value.metadata.type == NodeTypes.CAST) {
				const inputSocket = node.value.metadata.sockets.find((socket) => socket.isInput)!;
				const inputDataType = metadataStore.getDataType(inputSocket.datatype!);

				const outputSocket = node.value.metadata.sockets.find((socket) => !socket.isInput)!;
				const outputDataType = metadataStore.getDataType(outputSocket.datatype!);

				return {
					background: `linear-gradient(90deg, ${inputDataType.color} 0%, ${inputDataType.color} 40%, ${outputDataType.color} 60%, ${outputDataType.color} 100%)`
				};
			}

			return {
				'background-color': node.value.metadata.color
			};
		}
		return {
			'background-color': 'red'
		};
	});
</script>

<style scoped>
	.error-container {
		width: 100%;
		margin-top: 0.5rem;
		display: flex;
		flex-direction: column;
		background-color: var(--color-background-primary);
	}

	.error-container {
		cursor: alias;
	}

	.error-body {
		width: 100%;
		padding: 0.5rem;
		display: flex;
		flex-direction: column;
	}

	.error-node-name {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		color: var(--color-text);
	}

	.error-socket-name {
		margin-top: 4px;
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		color: var(--color-text);
		opacity: 0.7;
	}

	.error-description {
		margin-top: 4px;
		opacity: 1;
		font-style: italic;
		font-size: 0.8rem;
	}

	.node-color {
		width: 100%;
		height: 3px;
		opacity: 0.4;
	}

	.error-container:hover .node-color {
		opacity: 1;
		transition: opacity 100ms linear;
	}
</style>
