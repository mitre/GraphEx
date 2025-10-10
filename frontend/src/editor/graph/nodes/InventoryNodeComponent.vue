<template>
	<div class="inventory-node">
		<div class="inventory-node-foreground" :style="dataNodeStyles">
			<div class="inventory-left-container">
				<div class="inventory-node-file-key-name no-select">
					{{ fileKey }}
					<div
						class="help-icon material-icons"
						:title="props.node.metadata.description + '\n\nSource: ' + props.node.metadata.original_plugin"
					>
						storage
					</div>
				</div>
				<div class="inventory-node-name no-select">
					{{ nodeName }}
				</div>
				<div class="field-container" v-if="props.node.metadata.inventoryValue != null">
					<textarea
						class="input-field"
						:value="stringValue"
						:rows="rows"
						:cols="cols"
						ref="inputRef"
						:disabled="true"
						autocomplete="off"
						autocorrect="off"
						spellcheck="false"
					/>
					<div class="error-icon material-icons" v-if="props.node.metadata.error" :title="props.node.metadata.error">
						warning_amber
					</div>
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
	import SocketComponent from '@/editor/graph/sockets/SocketComponent.vue';
	import type { GraphNode } from '@/graph';
	import Color from 'color';
	import { computed } from 'vue';

	const props = defineProps<{
		node: GraphNode;
		tabId: string;
	}>();

	const rawName = computed(() => {
		return props.node.metadata.name;
	});

	const fileKey = computed(() => {
		return rawName.value.slice(0, rawName.value.indexOf('$'));
	});

	const nodeName = computed(() => {
		return rawName.value.slice(rawName.value.indexOf('$') + 1);
	});

	const socketOnly = computed(() => {
		return props.node.outputSockets.length == 1;
	});

	const stringValue = computed(() => {
		if (props.node.metadata.inventoryValue) {
			if (props.node.metadata.inventoryValue instanceof Array) {
				return props.node.metadata.inventoryValue.join('\n');
			}
			return String(props.node.metadata.inventoryValue);
		}
		return '';
	});

	const rows = computed(() => {
		return Math.max(stringValue.value.split('\n').length, 1);
	});

	const cols = computed(() => {
		let maxLineLength = 0;
		for (const line of String(stringValue.value).split('\n')) {
			let lineLength = line.replace(/\t/g, ' '.repeat(4)).length;
			if (lineLength > maxLineLength) {
				maxLineLength = lineLength;
			}
		}
		return maxLineLength;
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
	.inventory-node {
		display: flex;
		min-width: 150px;
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
		background: var(--color-editor-node-background-primary);
	}

	.inventory-node-foreground {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
		padding: 10px 3px;
	}

	.inventory-left-container {
		display: flex;
		flex-direction: column;
	}

	.inventory-node-name {
		flex: 1 0;
		padding: 0px 10px 5px;
		display: flex;
		align-items: center;
		color: var(--color-editor-node-body-text-primary);
		font-size: 0.9rem;
	}

	.inventory-node-file-key-name {
		flex: 1 0;
		padding: 0px 10px 5px;
		display: flex;
		align-items: center;
		color: var(--color-editor-node-body-text-primary);
		font-size: 0.9rem;
	}

	.input-field {
		width: 100%;
		padding: 5px;
		resize: none;
		white-space: pre;
		overflow: hidden;
		tab-size: 4;
		color: var(--color-text);
		background-color: var(--color-background-primary);
		font-size: 0.9rem;
		opacity: 0.6;
	}

	.help-icon {
		margin-left: 5px;
		font-size: 0.9rem;
		color: var(--color-editor-node-title-text);
		opacity: 0.4;
		cursor: help;
		margin-left: auto;
	}

	.field-container {
		display: flex;
		align-items: center;
		padding: 0 10px;
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
