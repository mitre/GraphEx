<template>
	<div
		:style="borderStyle"
		class="child-tab"
		@click.stop.prevent="onClick"
		@mouseover="onMouseOver"
		@mouseleave="onMouseLeave"
	>
		<div class="left-box boxes">
			<span class="display-name" :title="dynamicTitle">{{ leftBoxDisplayName }}</span>
		</div>
		<div :style="borderStyle" class="divider"></div>
		<div class="right-box boxes">
			<span :style="errorStyle" :title="dynamicTitle">{{ rightBoxVariableInfo }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
	import Color from 'color';
import { computed } from 'vue';
import type { VariableInformation } from './VariablePanel.vue';

	const props = defineProps<{
		variableInfo: VariableInformation;
	}>();

	function onMouseOver() {
		node.value.graph.ui.highlightNode(node.value);
	}

	function onMouseLeave() {
		node.value.graph.ui.deHighlightNode(node.value);
	}

	const node = computed(() => {
		return props.variableInfo.node;
	})

	const isGetVariableNode = computed(() => {
		return props.variableInfo.origin === "GET";
	});

	const isInlineGet = computed(() => {
		return props.variableInfo.origin === "INLINE";
	});

	const isSetVariableNode = computed(() => {
		return props.variableInfo.origin === "SET";
	})

	const isVariableOutputSocketName = computed(() => {
		return props.variableInfo.origin === "CHECKBOX";
	});

	const leftBoxDisplayName = computed(() => {
		if (props.variableInfo.origin === "GET" || props.variableInfo.origin === "SET") {
			return props.variableInfo.origin + " Node";
		}
		if (props.variableInfo.origin === "CHECKBOX") {
			return "SET via: " + node.value.metadata.name;
		}
		if (props.variableInfo.origin === "INLINE") {
			return "GET via: " + node.value.metadata.name;
		}
		return props.variableInfo.origin;
	});

	const rightBoxVariableInfo = computed(() => {
		if (isGetVariableNode.value) {
			const oSockets = node.value.outputSockets;
			if (oSockets.length && oSockets[0].connections.length > 0) return 'Connected';
			return 'NOT CONNECTED';
		}

		if (isSetVariableNode.value) {
			const iSockets = node.value.inputSockets;
			if (!iSockets.length) {
				return 'NOT CONNECTED';
			}

			const valueSocket = iSockets[0];
			let valueInfo = 'NOT CONNECTED';

			if (valueSocket.fieldValue !== undefined) {
				if (valueSocket.fieldValue === '') valueInfo = 'EMPTY STRING';
				else if (Array.isArray(valueSocket.fieldValue) && valueSocket.fieldValue.length == 0) valueInfo = 'EMPTY LIST';
				else valueInfo = String(valueSocket.fieldValue);
			} else if (valueSocket.variableName) {
				valueInfo = valueSocket.variableName;
			} else if (valueSocket.graphInputName) {
				valueInfo = valueSocket.graphInputName;
			} else if (valueSocket.connections.length > 0) {
				valueInfo = 'Connected';
			}

			return valueInfo;
		}

		if (isVariableOutputSocketName.value) {
			return "Checkbox Enabled"
		}

		if (isInlineGet.value) {
			return props.variableInfo.inputSocketName || "Input Socket";
		}

		return '';
	});

	const errorStyle = computed(() => {
		if (rightBoxVariableInfo.value.includes('NO INPUT') || rightBoxVariableInfo.value.includes('NOT CONNECTED')) {
			return {
				color: 'var(--color-component-sidebar-variables-no-setter)'
			};
		}

		if (
			rightBoxVariableInfo.value.includes('EMPTY STRING') ||
			rightBoxVariableInfo.value.includes('EMPTY LIST') ||
			rightBoxVariableInfo.value === '0'
		) {
			return {
				color: 'var(--color-component-sidebar-variables-empty-setter)'
			};
		}

		if (rightBoxVariableInfo.value.toLowerCase() == 'connected' || rightBoxVariableInfo.value.toLowerCase() == 'checkbox enabled') {
			return {
				color: 'var(--color-component-sidebar-variables-connected)'
			};
		}

		if (isSetVariableNode.value) {
			const iSockets = node.value.inputSockets;
			if (iSockets.length && (iSockets[0].variableName || iSockets[0].graphInputName)) {
				return {
					color: 'var(--color-text-secondary)'
				};
			}
		}

		if (isInlineGet.value) {
			return {
				color: 'var(--color-component-sidebar-variables-connected)'
			};
		}
		
		return {
			color: 'var(--color-text)'
		};
	});

	const dynamicTitle = computed(() => {
		if (rightBoxVariableInfo.value.includes('NO INPUT')) {
			return 'This setter node is MISSING a value to save.';
		}
		if (rightBoxVariableInfo.value.includes('NOT CONNECTED')) {
			return 'This getter node is MISSING a connection to another node.';
		}
		return 'This node is properly configured.';
	});

	const borderStyle = computed(() => {
		const color = Color(node.value.metadata.color);
		return {
			'border-color': String(color.rgb())
		};
	});

	function onClick() {
		if (node.value) {
			const ui = node.value.graph.ui;
			ui.deselectAllNodes();
			ui.selectNode(node.value);
			ui.resetZoom();
			ui.navigateUiToNodeLocation(node.value);
		}
	}
</script>

<style scoped>
	.child-tab {
		margin-left: 20px;
		margin-top: 3px;
		opacity: 0.8;
		cursor: pointer;
		background-color: var(--color-background-primary);
		padding-left: 4px;
		padding-right: 4px;
		border: 1px solid;
		display: flex;
	}

	.child-tab:hover {
		opacity: 1;
	}

	.right-box {
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.divider {
		border-left: 1px solid;
		padding-right: 4px;
		margin-left: 4px;
	}

	.boxes {
		padding-top: 4px;
		padding-bottom: 4px;
	}

	.display-name {
		color: var(--color-text);
	}
</style>
