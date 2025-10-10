<template>
	<div class="cast-node" :title="props.node.metadata.name">
		<div class="cast-node-contents">
			<SocketComponent :socket="inputSocket" :tab-id="tabId" socket-only />
			<SocketComponent :socket="outputSocket" :tab-id="tabId" socket-only />
		</div>
		<div class="cast-node-gradient" :style="gradient"></div>
	</div>
</template>

<script setup lang="ts">
	import SocketComponent from '@/editor/graph/sockets/SocketComponent.vue';
	import type { GraphNode } from '@/graph';
	import { useMetadataStore } from '@/stores';
	import { computed } from 'vue';

	const props = defineProps<{
		node: GraphNode;
		tabId: string;
	}>();

	const metadataStore = useMetadataStore();

	const inputSocket = computed(() => {
		return props.node.inputSockets[0];
	});

	const inputDataType = computed(() => {
		return metadataStore.getDataType(inputSocket.value.metadata.datatype!);
	});

	const outputSocket = computed(() => {
		return props.node.outputSockets[0];
	});

	const outputDataType = computed(() => {
		return metadataStore.getDataType(outputSocket.value.metadata.datatype!);
	});

	const gradient = computed(() => {
		const fromColor = inputDataType.value.color;
		const toColor = outputDataType.value.color;

		return {
			background: `linear-gradient(90deg, ${fromColor} 0%, ${fromColor} 25%, ${toColor} 75%, ${toColor} 100%)`
		};
	});
</script>

<style scoped>
	.cast-node {
		display: flex;
		flex-direction: column;
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
		background: var(--color-editor-node-background-primary);
	}

	.cast-node-contents {
		display: flex;
		flex-direction: row;
		align-items: center;
		padding: 6px 3px;
	}

	.cast-node-gradient {
		width: 100%;
		height: 3px;
	}
</style>
