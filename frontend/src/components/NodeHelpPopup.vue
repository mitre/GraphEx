<template>
	<div class="help-popup" :style="dynamicStyle">
		<div class="node-info">
			<div class="help-entry">Description: {{ props.node.metadata.description }}</div>
			<div class="help-entry">Node ID: {{ props.node.id }}</div>
			<div class="help-entry">Package: {{ props.packageName }}</div>
			<div class="help-entry">Category: {{ props.categories }}</div>
			<div v-if="props.node.metadata.hyperlink && props.node.metadata.hyperlink.length > 0">
				<div
					v-for="(link, index) in props.node.metadata.hyperlink"
					:key="index"
					@click="linkClick(link)"
					class="link"
					:title="link"
				>
					{{ link }}
				</div>
			</div>
		</div>
		<div class="close-btn material-icons" @click="closeClick">close</div>
	</div>
</template>

<script setup lang="ts">
	import type { GraphNode } from '@/graph';
	import { computed } from 'vue';

	const props = defineProps<{
		node: GraphNode;
		categories: string;
		packageName: string;
	}>();

	const dynamicStyle = computed(() => {
		let x = props.node.x + props.node.width() - 2;
		let h = props.node.height();
		let y = props.node.y - ( h / ( Math.log(h) / Math.log(4) ) );
		const transform = `translate(${x}px, ${y}px)`;
		return {
			transform: transform
		};
	});

	const emit = defineEmits<{
		(e: 'close'): void;
	}>();

	function linkClick(link: string | undefined) {
		window.open(link, '_blank');
	}

	function closeClick() {
		emit('close');
	}
</script>

<style scoped>
	.help-popup {
		position: absolute;
		min-width: 300px;
		max-width: 500px;
		padding: 5px 10px;
		z-index: 99;
		background-color: var(--color-foreground-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 0 0 8px 4px #0006;
		border-radius: 4px;
		display: flex;
		cursor: default;
	}

	.node-info {
		display: flex;
		flex-direction: column;
		flex: 1;
	}

	.link {
		text-decoration: underline;
		cursor: pointer;
		word-wrap: break-word;
		max-width: 300px;
	}

	.help-entry {
		padding-bottom: 2px;
	}

	.close-btn {
		cursor: pointer;
		opacity: 0.6;
	}

	.close-btn:hover {
		opacity: 1;
	}
</style>
