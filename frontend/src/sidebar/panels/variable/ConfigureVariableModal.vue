<template>
	<ModalFormComponent v-bind="form" @close="onClose" @update-value="onUpdateValue" @button-click="onButtonClick" />
</template>

<script setup lang="ts">
	import type { ModalFormProps } from '@/components/modalForm/ModalFormComponent.vue';
	import ModalFormComponent from '@/components/modalForm/ModalFormComponent.vue';
	import type { InputValue, ModalFormEntryProps } from '@/components/modalForm/ModalFormEntry.vue';
	import type { Graph } from '@/graph';
	import { useMetadataStore } from '@/stores';
	import { computed, nextTick, ref, type ComputedRef } from 'vue';

	export interface VariableMetadata {
		/** Name of the variable. */
		name: string;
	}

	const props = defineProps<{
		/** The graph that this input belongs to */
		graph: Graph;

		/** The variable metadata to configure. */
		metadata: VariableMetadata;
	}>();

	const emit = defineEmits<{
		(e: 'close'): void;
	}>();

	const metadataStore = useMetadataStore();

	function onButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (data.buttonName == 'Save') {
			onSave();
		}

		if (data.buttonName == 'Close') {
			onClose();
		}
	}

	function onClose() {
		emit('close');
	}

	function onSave() {
		const graph = props.graph;
		if (!graph) return;

		const ui = graph.ui;
		const viewportPositions = ui.viewportPositions();
		const width = viewportPositions.right - viewportPositions.left;
		const height = viewportPositions.bottom - viewportPositions.top;
		const x = -1 * ui.offsets.x + width / 2;
		const y = -1 * ui.offsets.y + height / 2;

		const metadata = metadataStore.getNode('Set Variable');
		const addedNode = graph.addNode(metadata, x, y, { fieldValue: variableName.value });
		nextTick(() => addedNode.centerPosition());
		emit('close');
	}

	function onUpdateValue(data: InputValue) {
		if (typeof data.value === 'string') {
			if (data.metadata.name == 'Variable Name') updateVariableName(data.value);
		}
	}

	function checkForDuplicateName(newName: string) {
		for (const n of props.graph.getNodes()) {
			if (n.metadata.name.includes('Set Variable ') && n.fieldValue == newName) {
				return true;
			}
		}
		return false;
	}

	const duplicateName = ref<boolean>(checkForDuplicateName(props.metadata.name));

	/****************
	 * Variable Name
	 ****************/
	const variableName = ref<string>(props.metadata.name);
	function updateVariableName(value: string) {
		duplicateName.value = checkForDuplicateName(value);
		variableName.value = value;
	}

	const variableNameError = computed(() => {
		if (variableName.value.trim().length == 0) {
			return 'Name cannot be empty.';
		}
		if (duplicateName.value) {
			return 'Variable already exists';
		}

		return null;
	});

	/****************
	 * Form
	 ****************/
	const hasError = computed(() => {
		return !!variableNameError.value;
	});

	const form: ComputedRef<ModalFormProps> = computed(() => {
		const entries: Array<ModalFormEntryProps> = [];

		entries.push({
			label: 'Variable Name',
			help: 'The name of the variable.',
			field: {
				value: variableName.value,
				error: variableNameError.value
			}
		});

		return {
			title: 'New Graph Variable',
			entries: entries,
			buttons: [
				{
					text: 'Save',
					type: 'primary',
					disabled: hasError.value
				},
				{
					text: 'Close',
					type: 'secondary'
				}
			]
		};
	});
</script>

<style scoped></style>
