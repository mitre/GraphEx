<template>
	<DropdownComponent ref="dropdown" controlled :teleport="props.socket.graph.ui.viewportElement">
		<slot></slot>

		<template v-slot:dropdown>
			<div class="socket-dropdown" @mousedown.stop @dblclick.stop.prevent :moving="draggedItem !== null">
				<div
					class="socket-dropdown-item"
					v-for="(connection, index) in socket.connections"
					:key="index"
					@mouseover="() => onItemMouseOver(index)"
					@mouseleave="() => highlightEdge(null)"
					@click.stop="() => grabEdge(index)"
					:dragged="draggedItem == index"
				>
					<span class="socket-dropdown-main" title="Grab edge.">
						<span class="socket-dropdown-index no-select">{{ index }}.</span>
						<span class="socket-dropdown-name no-select">
							{{ connection.node.metadata.name }}
						</span>
						<span class="socket-dropdown-description no-select" v-if="connection.node.metadata.field !== null">
							{{ connection.node.fieldValue }}
						</span>
					</span>
					<span
						class="socket-dropdown-item-move material-icons"
						@click.stop.prevent
						@mousedown="() => dragDropdownItem(index)"
						title="Click and drag to re-order."
					>
						drag_indicator
					</span>
				</div>
				<div class="socket-dropdown-item" v-if="!props.socket.hasMaxEdges()" @click.stop="newEdge">
					<div class="socket-dropdown-name no-select">+ New Edge</div>
				</div>
			</div>
		</template>
	</DropdownComponent>
</template>

<script setup lang="ts">
	import DropdownComponent from '@/components/DropdownComponent.vue';
import type { Socket } from '@/graph';
import { ref } from 'vue';

	const props = defineProps<{
		socket: Socket;
	}>();

	const dropdown = ref<InstanceType<typeof DropdownComponent>>();
	const draggedItem = ref<number | null>(null);

	function open() {
		if (dropdown.value) {
			dropdown.value.open();
		}
	}

	function onItemMouseOver(index: number) {
		if (draggedItem.value === null) {
			highlightEdge(index);
			return;
		}

		swapDraggedDropdownItem(index);
	}

	function dragDropdownItem(index: number) {
		draggedItem.value = index;

		window.addEventListener(
			'mouseup',
			() => {
				draggedItem.value = null;
			},
			{ capture: true, once: true }
		);
	}

	function swapDraggedDropdownItem(index: number) {
		if (draggedItem.value === null || draggedItem.value === index) {
			return;
		}

		props.socket.swapConnectionOrder(draggedItem.value, index);
		draggedItem.value = index;
	}

	function grabEdge(index: number) {
		if (!dropdown.value) {
			return;
		}

		const graph = props.socket.graph;
		const targetSocket = props.socket.connections[index];
		props.socket.disconnect(targetSocket);
		graph.ui.grabSocket(targetSocket);
		dropdown.value.close();
		highlightEdge(null);
	}

	function newEdge() {
		if (!dropdown.value || props.socket.hasMaxEdges()) {
			return;
		}
		dropdown.value.close();
		const graph = props.socket.graph;
		graph.ui.grabSocket(props.socket);
	}

	function highlightEdge(index: number | null) {
		if (index === null) {
			props.socket.graph.ui.unhighlightEdge();
		} else {
			const targetSocket = props.socket.connections[index];
			props.socket.graph.ui.highlightEdge(props.socket, targetSocket);
		}
	}

	defineExpose({
		open
	});
</script>

<style scoped>
	.socket-dropdown {
		display: flex;
		flex-direction: column;
		padding: 0.5rem 0rem;
		background-color: var(--color-foreground-primary);
		box-shadow: 0px 0px 2px 2px rgba(0, 0, 0, 0.4);
	}

	.socket-dropdown[moving='true'] {
		cursor: grabbing;
	}

	.socket-dropdown-item {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		padding: 4px 8px;
		cursor: pointer;
	}

	.socket-dropdown[moving='true'] .socket-dropdown-item {
		cursor: grabbing;
	}

	.socket-dropdown-item:hover {
		background-color: var(--color-foreground-secondary);
	}

	.socket-dropdown-main {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.socket-dropdown-index {
		color: var(--color-text-secondary);
		white-space: nowrap;
		font-size: 1rem;
		margin-right: 10px;
	}

	.socket-dropdown-name {
		color: var(--color-text);
		white-space: nowrap;
		font-size: 1rem;
	}

	.socket-dropdown-item[dragged='true'] .socket-dropdown-name {
		color: var(--color-primary);
	}

	.socket-dropdown-description {
		margin-left: 10px;
		color: var(--color-text-secondary);
		font-size: 0.9rem;
		max-width: 15rem;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.socket-dropdown-item-move {
		margin-left: 20px;
		color: var(--color-text-secondary);
		font-size: 1rem;
		cursor: grab;
	}

	.socket-dropdown[moving='true'] .socket-dropdown-item-move {
		cursor: grabbing;
	}

	.socket-dropdown-item-move:hover {
		color: var(--color-text);
		background-color: var(--color-foreground-tertiary);
		border-radius: 3px;
	}
</style>
