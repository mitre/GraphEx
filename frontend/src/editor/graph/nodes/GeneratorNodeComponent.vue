<template>
	<div class="generator-node">
		<div class="generator-node-foreground" :style="dataNodeStyles">
			<div class="generator-name no-select">
				{{ node.metadata.name }}

				<div class="help-icon material-icons" :title="props.node.metadata.description  + '\n\nSource: ' + props.node.metadata.original_plugin">help_outline</div>
			</div>
			<div class="field-container" v-if="props.node.metadata.field != null">
				<NodeInputComponent :node="props.node" :tab-id="tabId" :min-width="10" />
				<div class="error-icon material-icons" v-if="props.node.metadata.error" :title="props.node.metadata.error">
					warning_amber
				</div>
			</div>
			<div class="socket-column">
				<div
					class="socket-item"
					v-for="socket in node.outputSockets"
					:key="socket.metadata.name + '-' + socket.metadata.datatype + '-' + socket.metadata.isList"
				>
					<SocketComponent :socket="socket" :socket-only="socketOnly" :tab-id="tabId" />
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import NodeInputComponent from '@/editor/graph/inputs/NodeInputComponent.vue';
	import SocketComponent from '@/editor/graph/sockets/SocketComponent.vue';
	import type { GraphNode } from '@/graph';
	import Color from 'color';
	import { computed } from 'vue';

	const props = defineProps<{
		node: GraphNode;
		tabId: string;
	}>();

	const socketOnly = computed(() => {
		return props.node.outputSockets.length == 1;
	});

	const dataNodeStyles = computed(() => {
		const color = Color(props.node.metadata.color).fade(0.6);

		return {
			background: `linear-gradient(140deg, ${color.rgb()} 0%, rgba(0, 0, 0, 0) 50%, rgba(0, 0, 0, 0) 100%)`,
			'border-left': `3px solid ${props.node.metadata.color}`
		};
	});
</script>

<style scoped>
	.generator-node {
		display: flex;
		min-width: 150px;
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
		background: var(--color-editor-node-background-primary);
	}
	.generator-node-foreground {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
		padding: 10px 3px;
	}

	.generator-name {
		flex: 1 0;
		padding: 0px 10px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--color-editor-node-body-text-primary);
		font-size: 0.9rem;
	}

	.help-icon {
		margin-left: 5px;
		font-size: 0.9rem;
		color: var(--color-editor-node-title-text);
		opacity: 0.4;
		cursor: help;
	}

	.field-container {
		display: flex;
		align-items: center;
	}

	.error-icon {
		font-size: 1.2rem;
		margin-left: 6px;
		color: var(--color-editor-socket-text-error);
		cursor: help;
	}

	.socket-column {
		display: flex;
		flex-direction: column;
		margin-left: 6px;
		margin-right: 3px;
	}

	.socket-item {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.socket-item:not(:last-child) {
		margin-bottom: 8px;
	}
</style>
