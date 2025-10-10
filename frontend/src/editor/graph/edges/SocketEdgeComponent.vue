<template>
	<FreeformEdgeComponent v-bind="edge" />
</template>

<script setup lang="ts">
	import type { GraphEdge } from '@/editor/graph/edges/FreeformEdgeComponent.vue';
	import FreeformEdgeComponent from '@/editor/graph/edges/FreeformEdgeComponent.vue';
	import type { Socket } from '@/graph';
	import { useMetadataStore } from '@/stores';
	import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';

	export interface SocketEdgeProps {
		input: Socket;
		output: Socket;
	}

	const props = defineProps<SocketEdgeProps>();
	const metadataStore = useMetadataStore();

	/*
	 * This is a safe-guard mechanism to ensure that all relevant sockets are in the DOM before we draw an edge.
	 * When this is false, no edge will be drawn. When this component is mounted, we use a short timeout before setting this
	 * to true, triggering the edge-draw.
	 * Generally, this is not needed during normal operation. However, this is still done as a fail-safe as it
	 * has no significant impact and helps avoid potential graphical issues.
	 */
	const drawEdge = ref<boolean>(false);
	onMounted(async () => {
		setTimeout(() => {
			drawEdge.value = true;
		}, 10);
	});

	const color = computed(() => {
		const datatype = props.output.metadata.datatype;
		if (!datatype) {
			// Link socket
			return 'var(--color-editor-link-socket-edge)';
		}
		return metadataStore.getDataType(datatype).color;
	});

	const edge = reactive<GraphEdge>({
		startX: 0,
		startY: 0,
		endX: 0,
		endY: 0,
		color: color.value,
		highlight: false
	});

	/**
	 * All sockets contained on the nodes at both ends of this connection.
	 */
	const allSockets = computed(() => {
		const inputNode = props.input.node;
		const outputNode = props.output.node;
		return [
			...inputNode.inputSockets,
			...inputNode.outputSockets,
			...outputNode.inputSockets,
			...outputNode.outputSockets
		];
	});

	/**
	 * Dependencies we need to watch that may affect the positions of this edge.
	 * We need to treat anything that can change the "shape" or position of the node as a dependency.
	 */
	const edgeDependencies = computed(() => {
		if (!drawEdge.value) {
			return [];
		}

		const inputNode = props.input.node;
		const outputNode = props.output.node;

		const deps: Array<any> = [
			inputNode.x,
			inputNode.y,
			outputNode.x,
			outputNode.y,
			inputNode.fieldValue,
			outputNode.fieldValue
		];
		for (const socket of allSockets.value) {
			deps.push(socket.element);
			deps.push(socket.fieldValue);
			deps.push(socket.variableName);
			deps.push(socket.graphInputName);
			deps.push(socket.connections.length);
		}

		return deps;
	});

	watch(
		edgeDependencies,
		async () => {
			await nextTick();
			if (!props.input.element || !props.output.element || !drawEdge.value) {
				return;
			}

			const ui = props.input.graph.ui;
			ui.requestScaleFrame(() => {
				const { top: startTop, right: startRight, bottom: startBottom } = props.output.getPositions();
				const { top: endTop, bottom: endBottom, left: endLeft } = props.input.getPositions();

				edge.startX = startRight;
				edge.startY = startTop + (startBottom - startTop) / 2;
				edge.endX = endLeft;
				edge.endY = endTop + (endBottom - endTop) / 2;
				edge.highlight = ui.isEdgeHighlighted(props.input, props.output);
			});
		},
		{ deep: true }
	);

	/**
	 * Watch the highlighted edge separately do we don't need to perform the
	 * expensive watch computation above whenever the highlighted edge changes.
	 */
	const edgeIsHighlighted = computed(() => {
		return props.input.graph.ui.isEdgeHighlighted(props.input, props.output);
	});

	watch(edgeIsHighlighted, () => {
		edge.highlight = edgeIsHighlighted.value;
	});
</script>

<style scoped>
	svg {
		overflow: visible !important;
		position: absolute;
		z-index: 20;
		pointer-events: none;
	}

	path {
		fill: none;
		stroke-width: 2px;
	}
</style>
