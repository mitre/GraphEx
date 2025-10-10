<template>
	<div class="action-node">
		<div class="action-node-foreground" :style="nodeStyles">
			<div class="title">
				<div
					class="error-icon material-icons"
					v-if="props.node.metadata.error && !props.node.isLoading"
					:title="props.node.metadata.error"
				>
					warning_amber
				</div>
				<div class="title-name no-select">{{ nodeDisplayName }}</div>
				<div class="node-help" @dblclick.stop.prevent>
					<div
						class="help-icon material-icons"
						@click="clickShowPopup"
						title="Left-click to show information about this node"
					>
						help_outline
					</div>
					<Teleport :to="props.node.graph.ui.contentElement" :disabled="!props.node.graph.ui.contentElement">
						<NodeHelpPopup
							v-if="showHelpPopup"
							:node="props.node"
							:categories="categories"
							:packageName="packageName"
							@close="clickShowPopup"
						/>
					</Teleport>
				</div>
			</div>

			<div class="node-body">
				<div class="socket-column input-column">
					<div class="socket-item" v-if="props.node.hasInputSocket('_backward')">
						<SocketComponent :socket="props.node.getInputSocket('_backward')" :tab-id="tabId" socket-only />
					</div>
					<template
						v-for="socket in node.inputSockets"
						:key="socket.metadata.name + '-' + socket.metadata.datatype + '-' + socket.metadata.isList"
					>
						<div v-if="socket.metadata.name != '_backward'" class="socket-item">
							<SocketComponent :socket="socket" :tab-id="tabId" />
						</div>
					</template>
					<div v-if="node.metadata.allowsNewInputs && !props.disabled" class="addable-inputs-button-bar">
						<div
							class="input-add no-select"
							@click.stop="addNewEntry"
							title="Left-click to add another list to this node."
						>
							+ Add
						</div>
						<div
							v-if="lengthOfDataInputs > 0"
							class="input-add no-select"
							@click.stop="removeLastEntry"
							title="Left-click to remove the most recently added list on this node."
						>
							- Remove
						</div>
					</div>
				</div>

				<div class="socket-column output-column">
					<div class="socket-item" v-if="props.node.hasOutputSocket('_forward')">
						<SocketComponent :socket="props.node.getOutputSocket('_forward')" :tab-id="tabId" socket-only />
					</div>
					<template
						v-for="socket in node.outputSockets"
						:key="socket.metadata.name + '-' + socket.metadata.datatype + '-' + socket.metadata.isList"
					>
						<div v-if="socket.metadata.name != '_forward'" class="socket-item">
							<SocketComponent
								v-if="props.node.metadata.name === 'List Compression Loop'"
								:socket="socket"
								:tab-id="tabId"
								:frontend-override-name="computeCompressionName(socket)"
							/>
							<SocketComponent v-else :socket="socket" :tab-id="tabId" />
						</div>
					</template>
				</div>
			</div>

			<div class="node-field-container" v-if="props.node.metadata.field !== null">
				<NodeInputComponent :node="props.node" :tab-id="tabId" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import NodeHelpPopup from '@/components/NodeHelpPopup.vue';
	import NodeInputComponent from '@/editor/graph/inputs/NodeInputComponent.vue';
	import SocketComponent from '@/editor/graph/sockets/SocketComponent.vue';
	import type { GraphNode, SocketMetadata } from '@/graph';
	import { DYNAMIC_DATATYPE, Socket } from '@/graph';
	import Color from 'color';
	import { computed, ref } from 'vue';

	const props = defineProps<{
		node: GraphNode;
		tabId: string;
		disabled: boolean;
	}>();

	const showHelpPopup = ref<boolean>(false);

	function clickShowPopup() {
		showHelpPopup.value = !showHelpPopup.value;
	}

	function addNewEntry() {
		const newSocketMetadata: SocketMetadata = {
			isInput: true,
			isOptional: false,
			isList: true,
			isLink: false,
			name: 'List #' + String(lengthOfDataInputs.value + 1),
			datatype: DYNAMIC_DATATYPE,
			description: 'auto generated',
			canHaveField: false,
			enumOptions: [],
			field: null
		};
		props.node.inputSockets.push(new Socket(props.node, newSocketMetadata));
	}

	const socketsNotBackward = computed(() => {
		return props.node.inputSockets.filter((s) => s.metadata.name != '_backward');
	});

	const lengthOfDataInputs = computed(() => {
		return socketsNotBackward.value.length;
	});

	function removeLastEntry() {
		if (lengthOfDataInputs.value <= 0) return;
		const lastSocketName: string = socketsNotBackward.value[lengthOfDataInputs.value - 1].metadata.name;
		const arrayIndex: number = props.node.inputSockets.findIndex((s) => s.metadata.name === lastSocketName);
		const socketToRemove: Socket = props.node.inputSockets[arrayIndex];
		for (const c of socketToRemove.connections) {
			c.disconnect(socketToRemove);
		}
		props.node.inputSockets.splice(arrayIndex, 1);
	}

	/** This function is used to create the custom output socket names for compression lists */
	function computeCompressionName(outputSocket: Socket) {
		const outputName = outputSocket.metadata.name;
		const valueIndex = outputName.lastIndexOf(' Value');
		const inputName = outputName.slice(0, valueIndex);
		const inputSocket = props.node.inputSockets.find((s) => s.metadata.name === inputName);
		if (!inputSocket || inputSocket.connections.length <= 0) return outputName;
		/** else: The input socket exists, it has at least one connection to another node */
		const firstInputNode = inputSocket.connections[0].node;
		if (firstInputNode.metadata.isInventoryNode) {
			const fullNodeName = firstInputNode.metadata.name;
			const hierarchyAfterEntryName = fullNodeName.slice(fullNodeName.indexOf('-> ') + 2).trim();
			const hierarchyWithoutIndexNames = hierarchyAfterEntryName.replace(/ -> Index#\d+/gm, '');
			return outputName + ' (' + hierarchyWithoutIndexNames + ')';
		} else if (firstInputNode.metadata.name == 'Get Variable' || firstInputNode.metadata.name == 'Get Graph Input') {
			return outputName + ' (' + String(firstInputNode.fieldValue) + ')';
		} else if (inputSocket.connections.length === 1 && inputSocket.connections[0].metadata.isList) {
			return outputName + ' (' + String(inputSocket.connections[0].metadata.name) + ')';
		}
		return outputName;
	}

	const nodeDisplayName = computed(() => {
		let n = props.node.metadata.name;
		if (props.node.metadata.name === 'For Each' && lengthOfDataInputs.value > 0) {
			const firstSocket = props.node.inputSockets[0];
			if (firstSocket.metadata.datatype && firstSocket.metadata.datatype != 'Dynamic') {
				n += ' (' + firstSocket.metadata.datatype + ')';
			}
		}
		return n;
	});

	const nodeStyles = computed(() => {
		const color = Color(props.node.metadata.color).fade(0.65);
		const color2 = Color(props.node.metadata.color).fade(0.95);

		return {
			background: `linear-gradient(170deg, ${color.rgb()} 0%, ${color2.rgb()} 50%, rgba(0, 0, 0, 0) 100%)`
		};
	});

	const packageName = computed(() => {
		return props.node.metadata.original_plugin.split('.')[0];
	});

	const categories = computed(() => {
		let temp = '';
		for (let i = 0; i < props.node.metadata.categories.length; i++) {
			const nextCategory = props.node.metadata.categories[i];
			if (i === 0) {
				temp = nextCategory;
			} else {
				temp += ' -> ' + nextCategory;
			}
		}
		return temp;
	});
</script>

<style scoped>
	.action-node {
		display: flex;
		flex-direction: column;
		min-width: 150px;
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
		background: var(--color-editor-node-background-primary);
	}

	.action-node-foreground {
		flex: 1 0;
		display: flex;
		flex-direction: column;
	}

	.title {
		width: 100%;
		margin-top: 2px;
		padding: 2px 0px;
		display: flex;
		align-items: center;
		justify-content: center;
		position: relative;
	}

	.title-name {
		margin: 0px 3rem;
		font-weight: bold;
		color: var(--color-editor-node-title-text);
		white-space: pre;
		font-size: 1rem;
		display: flex;
		flex: 1;
		justify-content: center;
	}

	.error-icon {
		font-size: 1.3rem;
		color: var(--color-editor-socket-text-error);
		cursor: help;
		position: absolute;
		left: 4px;
	}

	.node-help {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.help-icon {
		font-size: 1rem;
		color: var(--color-editor-node-title-text);
		opacity: 0.6;
		position: absolute;
		right: 4px;
	}

	.help-icon:hover {
		opacity: 1;
	}

	.node-body {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		justify-content: space-between;
		padding: 12px 5px;
	}

	.socket-column {
		display: flex;
		flex-direction: column;
	}

	.input-column {
		align-items: flex-start;
	}

	.output-column {
		align-items: flex-end;
		margin-left: 20px;
	}

	.socket-item {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.socket-item:not(:last-child) {
		margin-bottom: 8px;
	}

	.node-field-container {
		margin-top: 10px;
		width: 100%;
		padding: 0px 10px 10px 10px;
		display: flex;
		flex-direction: row;
		justify-content: center;
	}

	.addable-inputs-button-bar {
		display: flex;
		flex-direction: row;
	}

	.input-add {
		padding: 2px 6px;
		font-size: 0.9rem;
		color: var(--color-text);
		opacity: 0.8;
		border-radius: 3px;
		cursor: pointer;
	}

	.input-add:hover {
		opacity: 1;
		background-color: var(--color-foreground-secondary);
	}
</style>
