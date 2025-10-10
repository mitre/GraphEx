<template>
	<div
		class="node-metadata-container no-select"
		title="Double click, or click-and-drag, to add this node."
		draggable="true"
		:favorited="isFavorited"
		@dblclick="addNode"
		@dragstart="onDragStart"
	>
		<div class="node-metadata-body">
			<div class="node-metadata-main">
				<div class="node-metadata-title">
					<span class="name no-select">{{ props.metadata.name }}</span>
				</div>
				<span class="description no-select">{{ props.metadata.description }}</span>
				<span class="category no-select">{{ categorySequence }}</span>
			</div>

			<div class="node-metadata-icons">
				<span
					class="star-icon material-icons"
					@click.stop.prevent="clickFavorite"
					@dblclick.stop.prevent
					title="Add to favorites."
				>
					{{ isFavorited ? 'star' : 'star_outline' }}
				</span>
			</div>
		</div>
		<span class="node-color" :style="colorStyles"></span>
	</div>
</template>

<script setup lang="ts">
	import { NodeTypes, type NodeMetadata } from '@/graph';
	import { useEditorStore, useFavoriteStore, useMetadataStore } from '@/stores';
	import { computed, nextTick } from 'vue';

	const props = defineProps<{
		metadata: NodeMetadata;
	}>();

	const editorStore = useEditorStore();
	const metadataStore = useMetadataStore();
	const favoriteStore = useFavoriteStore();

	function addNode() {
		if (!editorStore.activeGraphTab) return;

		const ui = editorStore.activeGraphTab.contents.ui;
		const viewportPositions = ui.viewportPositions();
		const width = viewportPositions.right - viewportPositions.left;
		const height = viewportPositions.bottom - viewportPositions.top;

		const x = -1 * ui.offsets.x + width / 2;
		const y = -1 * ui.offsets.y + height / 2;
		const addedNode = editorStore.activeGraphTab.contents.addNode(props.metadata, x, y);
		nextTick(() => addedNode.centerPosition());
	}

	function onDragStart(ev: DragEvent) {
		if (!ev.dataTransfer) return;
		ev.dataTransfer.setData('addNode', JSON.stringify(props.metadata));
	}

	function clickFavorite() {
		favoriteStore.clickFavorite(props.metadata.name);
	}

	const colorStyles = computed(() => {
		if (props.metadata.type == NodeTypes.CAST) {
			const inputSocket = props.metadata.sockets.find((socket) => socket.isInput)!;
			const inputDataType = metadataStore.getDataType(inputSocket.datatype!);

			const outputSocket = props.metadata.sockets.find((socket) => !socket.isInput)!;
			const outputDataType = metadataStore.getDataType(outputSocket.datatype!);

			return {
				background: `linear-gradient(90deg, ${inputDataType.color} 0%, ${inputDataType.color} 40%, ${outputDataType.color} 60%, ${outputDataType.color} 100%)`
			};
		}

		return {
			'background-color': props.metadata.color
		};
	});

	const isFavorited = computed(() => {
		return favoriteStore.isFavorited(props.metadata.name);
	});

	const packageName = computed(() => {
		return props.metadata.original_plugin.split('.')[0];
	});

	const categories = computed(() => {
		let temp = "";
		for (let i = 0; i < props.metadata.categories.length; i++) {
			const nextCategory = props.metadata.categories[i];
			if (i === 0) {
				temp = nextCategory;
			} else {
				temp += " -> " + nextCategory;
			}
		}
		return temp;
	});

	const categorySequence = computed(() => {
		return "(" + packageName.value + ") " + categories.value;
	});
</script>

<style scoped>
	.node-metadata-container {
		width: 100%;
		margin-top: 0.5rem;
		display: flex;
		flex-direction: column;
		background-color: var(--color-background-primary);
		cursor: pointer;
	}

	.node-metadata-body {
		width: 100%;
		padding: 0.5rem;
		display: flex;
		flex-direction: row;
	}

	.node-metadata-main {
		flex: 1 0;
		display: flex;
		flex-direction: column;
	}

	.node-metadata-icons {
		display: flex;
		flex-direction: column;
		align-items: center;
		margin-left: 4px;
	}

	.node-metadata-file-type-icons {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.node-metadata-file-type-icons > *:not(:last-child) {
		margin-bottom: 3px;
	}

	.node-metadata-title {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
	}

	.name {
		color: var(--color-text);
	}

	.node-metadata-icon {
		width: 0.8rem;
		height: 0.8rem;
		opacity: 0.6;
		cursor: help;
	}

	.description {
		margin-top: 4px;
		color: var(--color-text);
		opacity: 0.5;
		font-style: italic;
		font-size: 0.8rem;
		white-space: pre-wrap;
	}

	.category {
		margin-top: 2px;
		color: var(--color-primary);
		opacity: 0.8;
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

	.star-icon {
		font-size: 1rem;
		opacity: 0.4;
	}

	.node-metadata-container[favorited='true'] .star-icon {
		color: var(--color-component-sidebar-nodes-favorite-star-icon-favorited);
		opacity: 1;
	}
</style>
