<template>
	<div class="data-node" :style="dataNodeStyles">
		<div class="title no-select" :style="titleStyles">
			{{ datatype.name }}
		</div>
		<div class="body">
			<div class="contents">
				<NodeInputComponent :node="props.node" :tab-id="tabId" :min-width="12" />
			</div>
			<div class="socket-column">
				<SocketComponent :socket="socket" :tab-id="tabId" :socket-only="socketOnly" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import NodeInputComponent from '@/editor/graph/inputs/NodeInputComponent.vue';
	import SocketComponent from '@/editor/graph/sockets/SocketComponent.vue';
	import type { GraphNode } from '@/graph';
	import { useMetadataStore } from '@/stores';
	import { computed } from 'vue';

	const props = defineProps<{
		node: GraphNode;
		tabId: string;
	}>();

	const metadataStore = useMetadataStore();

	const socket = computed(() => {
		return props.node.outputSockets[0];
	});

	const datatype = computed(() => {
		return metadataStore.getDataType(socket.value.metadata.datatype!);
	});

	const dataNodeStyles = computed(() => {
		return {
			'border-bottom': `2px solid ${datatype.value.color}`
		};
	});

	const socketOnly = computed(() => {
		return props.node.outputSockets.length == 1;
	});

	const titleStyles = computed(() => {
		return {
			color: datatype.value.color
		};
	});
</script>

<style scoped>
	.data-node {
		min-width: 150px;
		min-height: 60px;
		display: flex;
		flex-direction: column;
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
		background: var(--color-editor-node-background-primary);
	}

	.title {
		width: 100%;
		margin-top: 5px;
		margin-left: 5px;
		font-weight: bold;
		font-size: 0.8rem;
		font-style: italic;
		color: var(--color-editor-node-title-text);
	}

	.body {
		display: flex;
		flex-direction: row;
		flex: 1 0;
	}

	.contents {
		flex: 1 0;
		padding: 8px;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	.socket-column {
		padding: 3px;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}
</style>
