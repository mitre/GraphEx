<template>
	<div class="socket-field-container" v-if="fieldEnabled">
		<div class="socket-input-field" v-if="props.socket.fieldValue !== undefined && !props.socket.metadata.isList">
			<SocketInputComponent :socket="props.socket" :disabled="editorStore.isResolvingMergeConflict" />
		</div>

		<div class="socket-input-field" v-if="props.socket.fieldValue !== undefined && props.socket.metadata.isList">
			<ListSocketInputComponent :socket="props.socket" :disabled="editorStore.isResolvingMergeConflict" />
		</div>

		<div
			class="socket-source-field no-select"
			v-if="props.socket.variableName"
			:style="variableFieldStyles"
			:title="'Use variable value from: ' + props.socket.variableName"
		>
			<span class="socket-source-label">var</span> {{ props.socket.variableName }}
		</div>

		<div
			class="socket-source-field no-select"
			v-if="props.socket.graphInputName"
			:style="graphInputFieldStyles"
			:title="'Use graph input value from: ' + props.socket.graphInputName"
		>
			<span class="socket-source-label">input</span> {{ props.socket.graphInputName }}
		</div>

		<DropdownComponent
			:teleport="props.socket.graph.ui.viewportElement"
			:translate-y="2"
			:translate-x="8"
			ref="dropdown"
		>
			<div class="socket-input-source-icon material-icons" title="Set alternative input source">more_vert</div>

			<template v-slot:dropdown>
				<MenuComponent v-bind="menu" @select="selectMenuItem" :child-max-height="200" />
			</template>
		</DropdownComponent>
	</div>
</template>

<script setup lang="ts">
	import DropdownComponent from '@/components/DropdownComponent.vue';
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
	import MenuComponent from '@/components/MenuComponent.vue';
	import ListSocketInputComponent from '@/editor/graph/inputs/ListSocketInputComponent.vue';
	import SocketInputComponent from '@/editor/graph/inputs/SocketInputComponent.vue';
	import { DYNAMIC_DATATYPE, type Socket } from '@/graph';
	import { useEditorStore, useMetadataStore } from '@/stores';
	import Color from 'color';
	import { computed, ref, type ComputedRef } from 'vue';

	const props = defineProps<{
		socket: Socket;
		availableVariables: Array<string>;
	}>();

	const metadataStore = useMetadataStore();
	const editorStore = useEditorStore();
	const dropdown = ref<InstanceType<typeof DropdownComponent>>();

	const menu: ComputedRef<MenuOptions> = computed(() => {
		return {
			items: [
				{
					label: 'Input Field',
					disabled: disableInputFieldOption.value,
					icon: 'drive_file_rename_outline',
					description: 'Input a value manually for this socket.'
				},
				{
					label: 'Variable',
					disabled: disableVariableOption.value,
					icon: 'workspaces_outline',
					description: 'Use the value of a variable.',
					submenu: {
						items: props.availableVariables.map((varName) => {
							return { id: varName, label: varName };
						}),
						maxHeight: 500
					}
				},
				{
					label: 'Graph Input',
					disabled: disableGraphInputOption.value,
					icon: 'settings_input_component',
					description: 'Use a graph input value.',
					submenu: {
						items: availableGraphInputs.value.map((x) => {
							return { id: x.name, label: x.name, description: x.description };
						}),
						maxHeight: 500
					}
				},
				{
					label: 'Connection',
					disabled: disableConnectionOption.value,
					icon: 'device_hub',
					description: 'Use a connection from another node.'
				}
			]
		};
	});

	function selectMenuItem(items: Array<MenuItem>) {
		if (items.length == 1 && items[0].label == 'Input Field') {
			enableInputField();
			return;
		}

		if (items.length == 2 && items[0].label == 'Variable') {
			enableVariable(items[1].label);
			return;
		}

		if (items.length == 2 && items[0].label == 'Graph Input') {
			enableGraphInput(items[1].label);
			return;
		}

		if (items.length == 1 && items[0].label == 'Connection') {
			enableConnection();
			return;
		}
	}

	function enableInputField() {
		if (disableInputFieldOption.value) return;
		dropdown.value?.close();
		props.socket.setInputFieldDefault();
	}

	function enableVariable(varName: string) {
		if (disableVariableOption.value) return;
		dropdown.value?.close();
		props.socket.setVariableName(varName);
	}

	function enableGraphInput(inputName: string) {
		if (disableGraphInputOption.value) return;
		dropdown.value?.close();
		props.socket.setGraphInputName(inputName);
	}

	function enableConnection() {
		if (disableConnectionOption.value) return;
		dropdown.value?.close();
		props.socket.clearInputSources();
	}

	/** Whether this socket can have *any* fields. */
	const fieldEnabled = computed(() => {
		return props.socket.metadata.datatype && !props.socket.metadata.isLink && props.socket.metadata.isInput;
	});

	/** Whether to disable the input field option in the dropdown */
	const disableInputFieldOption = computed(() => {
		return props.socket.fieldValue !== undefined || !props.socket.metadata.canHaveField;
	});

	/** Whether to disable the variable option in the dropdown */
	const disableVariableOption = computed(() => {
		return props.availableVariables.length == 0;
	});

	/** All available graph inputs that apply to this socket. */
	const availableGraphInputs = computed(() => {
		const m = props.socket.metadata;
		return props.socket.graph.inputMetadata.filter(
			(x) => (m.datatype == DYNAMIC_DATATYPE || x.datatype == m.datatype) && !!x.isList == m.isList
		);
	});

	/** Whether to disable the graph input option in the dropdown */
	const disableGraphInputOption = computed(() => {
		return availableGraphInputs.value.length == 0;
	});

	/** Whether to disable the connection option in the dropdown */
	const disableConnectionOption = computed(() => {
		return (
			editorStore.isResolvingMergeConflict ||
			(props.socket.fieldValue === undefined &&
				props.socket.variableName === undefined &&
				props.socket.graphInputName === undefined)
		);
	});

	/** Styles for the 'variable' field */
	const variableFieldStyles = computed(() => {
		const datatypeColor = metadataStore.getDataType(props.socket.metadata.datatype!).color;
		const backgroundColor = Color(datatypeColor).fade(0.75);

		return {
			backgroundColor: String(backgroundColor.rgb())
		};
	});

	/** Styles for the 'graph_input' field */
	const graphInputFieldStyles = computed(() => {
		const datatypeColor = metadataStore.getDataType(props.socket.metadata.datatype!).color;
		const backgroundColor = Color(datatypeColor).fade(0.75);

		return {
			backgroundColor: String(backgroundColor.rgb())
		};
	});
</script>

<style scoped>
	.socket-field-container {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.socket-input-field {
		margin-left: 8px;
	}

	.socket-source-field {
		margin-left: 8px;
		padding: 4px 10px;
		font-size: 0.8rem;
		border-radius: 12px;
		cursor: help;
		color: var(--color-text);
		box-shadow: 0px 0px 6px 1px rgba(0, 0, 0, 0.3);
	}

	.socket-source-label {
		margin-right: 2px;
		opacity: 0.7;
		font-style: italic;
		font-family: monospace;
	}

	.socket-input-source-icon {
		margin-left: 2px;
		color: var(--color-editor-socket-text);
		font-size: 1rem;
		display: flex;
		align-items: center;
		justify-content: center;
		opacity: 0.6;
	}

	.socket-input-source-icon:hover {
		opacity: 1;
	}

	:deep(.menu-item-icon[for='Connection']) {
		transform: rotate(90deg);
	}

	:deep(.menu-item-description) {
		max-width: 300px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
