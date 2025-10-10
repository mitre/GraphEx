<template>
	<ModalFormComponent v-bind="form" @close="onClose" @update-value="onUpdateValue" @button-click="onButtonClick" />
</template>

<script setup lang="ts">
	import type { ButtonProps } from '@/components/ButtonComponent.vue';
	import type { ModalFormProps } from '@/components/modalForm/ModalFormComponent.vue';
	import ModalFormComponent from '@/components/modalForm/ModalFormComponent.vue';
	import type { InputValue, ModalFormEntryProps } from '@/components/modalForm/ModalFormEntry.vue';
	import { DYNAMIC_DATATYPE, type Graph, type GraphOutputMetadata } from '@/graph';
	import { useMetadataStore, usePromptStore } from '@/stores';
	import { computed, ref, type ComputedRef } from 'vue';

	const props = defineProps<{
		/** The graph that this output belongs to */
		graph: Graph;

		/** The output metadata to configure. */
		metadata: GraphOutputMetadata;

		/** Whether to treat this as a new output rather than configuring an existing one. */
		isNew?: boolean;
	}>();

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'save', metadata: GraphOutputMetadata): void;
	}>();

	const metadataStore = useMetadataStore();
	const promptStore = usePromptStore();

	async function onButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (data.buttonName == 'Save') {
			await onSave();
		}

		if (data.buttonName == 'Close') {
			await onClose();
		}
	}

	async function onClose() {
		if (hasChanges.value) {
			const buttons: Array<ButtonProps> = [
				{
					text: 'Discard Changes',
					type: 'warning'
				},
				{
					text: 'Cancel',
					type: 'secondary'
				}
			];

			if (!hasError.value) {
				buttons.unshift({
					text: 'Save Changes',
					type: 'primary'
				});
			}

			const value = await promptStore.show({
				title: 'Unsaved Changes',
				additionalInfo: 'You have unsaved changes to this graph output.',
				entries: [],
				buttons: buttons
			});

			if (!value || value.buttonName == 'Cancel') {
				return;
			}

			if (value.buttonName == 'Save Changes') {
				await onSave();
				return;
			}
		}

		emit('close');
	}

	async function onSave() {
		emit('save', {
			name: outputName.value,
			datatype: datatype.value,
			isList: isList.value,
			description: description.value
		});

		emit('close');
	}

	function onUpdateValue(data: InputValue) {
		//metadata will always be defined from a form.
		if (typeof data.value === 'string') {
			if (data.metadata.name == 'Output Name') updateOutputName(data.value);
			if (data.metadata.name == 'Data Type') updateDataType(data.value);
			if (data.metadata.name == 'Is List?') updateIsList(data.value);
			if (data.metadata.name == 'Description') updateDescription(data.value);
		} else {
			throw 'Recursion not implemented here';
		}
	}

	/****************
	 * Output Name
	 ****************/
	const outputName = ref<string>(props.metadata.name);
	function updateOutputName(value: string) {
		outputName.value = value;
	}

	const outputNameError = computed(() => {
		if (outputName.value.trim().length == 0) {
			return 'Name cannot be empty.';
		}

		// Ensure no duplicate name
		if (props.graph.outputMetadata.some((x) => x.name.trim() == outputName.value.trim() && x !== props.metadata)) {
			return 'Another output exists with the same name.';
		}

		// Check for name validity
		if (!/^[a-zA-Z0-9]+$/.test(outputName.value.trim())) {
			return 'Name must consist of letters and numbers only.';
		}

		return null;
	});

	/****************
	 * Data Type
	 ****************/
	const datatype = ref<string>(props.metadata.datatype);
	function updateDataType(option: string) {
		datatype.value = option;
	}

	const dataTypeOptions = computed(() => {
		return metadataStore.dataTypes
			.filter((dt) => dt.name != DYNAMIC_DATATYPE)
			.map((dt) => dt.name)
			.sort((a, b) => a.localeCompare(b));
	});

	/****************
	 * Is List
	 ****************/
	const isList = ref<boolean | undefined>(props.metadata.isList);
	function updateIsList(option: string) {
		isList.value = option === 'True' ? true : undefined;
	}

	/****************
	 * Description
	 ****************/
	const description = ref<string | undefined>(props.metadata.description);
	function updateDescription(value: string) {
		if (value.trim() == '') {
			description.value = undefined;
			return;
		}
		description.value = value;
	}

	/****************
	 * Form
	 ****************/
	const hasChanges = computed(() => {
		return (
			outputName.value.trim() !== props.metadata.name ||
			datatype.value !== props.metadata.datatype ||
			isList.value !== props.metadata.isList ||
			description.value !== props.metadata.description
		);
	});

	const hasError = computed(() => {
		return !!outputNameError.value;
	});

	const form: ComputedRef<ModalFormProps> = computed(() => {
		const entries: Array<ModalFormEntryProps> = [];

		entries.push({
			label: 'Output Name',
			help: 'The name of the output as used in the graph.',
			field: {
				value: outputName.value,
				error: outputNameError.value
			},
			focus: true
		});

		entries.push({
			label: 'Data Type',
			help: 'The data type for this graph output.',
			field: {
				value: datatype.value,
				options: dataTypeOptions.value
			}
		});

		entries.push({
			label: 'Is List?',
			help: 'Whether this output should be a list of values rather than just a single value.',
			field: {
				value: isList.value ? 'True' : 'False',
				options: ['True', 'False']
			}
		});

		entries.push({
			label: 'Description',
			help: 'The description for graph output. Meant solely for informational purposes.',
			field: {
				value: description.value || ''
			}
		});

		return {
			title: props.isNew ? 'New Graph Output' : `Graph Output Settings for '${props.metadata.name}'`,
			entries: entries,
			buttons: [
				{
					text: 'Save',
					type: 'primary',
					disabled: (!hasChanges.value && !props.isNew) || hasError.value
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
