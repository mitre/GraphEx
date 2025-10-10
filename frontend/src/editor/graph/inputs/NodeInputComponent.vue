<template>
	<template v-if="inputField !== null && props.node.fieldValue !== undefined">
		<InputFieldHighlightable
			v-if="props.node.metadata.name === 'Named Format String'"
			:floating-label="inputField.floatingLabel"
			:value="String(props.node.fieldValue)"
			:label="inputField.name"
			:min-width="props.minWidth"
			:multiline="inputField.multiline"
			:error="stringInputError"
			@input="updateValue"
			@change="onChange"
		/>

		<InputField
			v-else-if="inputType === 'string'"
			:floating-label="inputField.floatingLabel"
			:value="String(props.node.fieldValue)"
			:label="inputField.name"
			:min-width="props.minWidth"
			:multiline="inputField.multiline"
			:error="stringInputError"
			@input="updateValue"
			@change="onChange"
		/>

		<InputField
			v-else-if="inputType === 'number'"
			:floating-label="inputField.floatingLabel"
			:value="String(props.node.fieldValue)"
			:label="inputField.name"
			:min-width="props.minWidth"
			:multiline="inputField.multiline"
			:error="numberInputError"
			@input="updateNumberValue"
			@change="onChangeNumber"
		/>

		<BooleanSliderInput
			v-else-if="inputType === 'boolean'"
			:field-name="fieldName"
			:value="props.node.fieldValue"
			@update="onChange"
		/>
	</template>
</template>

<script setup lang="ts">
	import InputField from '@/components/InputField.vue';
	import InputFieldHighlightable from '@/components/InputFieldHighlightable.vue';
	import BooleanSliderInput from '@/editor/graph/inputs/BooleanSliderInput.vue';
	import type { GraphNode } from '@/graph';
	import { useEditorStore, useErrorStore } from '@/stores';
	import { computed, onUnmounted, watch } from 'vue';

	const props = withDefaults(
		defineProps<{
			tabId: string;

			/** The node for this input. */
			node: GraphNode;

			/** Minimum width of text-based input fields. */
			minWidth?: number;
		}>(),
		{ minWidth: 24 }
	);

	const errorStore = useErrorStore();
	const editorStore = useEditorStore();

	const inputField = computed(() => {
		return props.node.metadata.field;
	});

	const inputType = computed(() => {
		return typeof inputField.value?.default;
	});

	const fieldName = computed(() => {
		return inputField.value?.name;
	});

	const disabled = computed(() => {
		return editorStore.isResolvingMergeConflict;
	});

	function updateValue(newValue: any) {
		if (disabled.value) {
			return;
		}
		props.node.setFieldValue(newValue);
	}

	function updateNumberValue(newValue: any) {
		if (disabled.value) {
			return;
		}
		if ((typeof newValue === 'string' && newValue.trim().length == 0) || isNaN(Number(newValue))) {
			updateValue(newValue);
		} else {
			updateValue(Number(newValue));
		}
	}

	async function onChange(newValue: any) {
		if (disabled.value) {
			return;
		}
		updateValue(newValue);
	}

	async function onChangeNumber(newValue: any) {
		if (disabled.value) {
			return;
		}
		updateNumberValue(newValue);
	}

	const stringInputError = computed(() => {
		if (inputField.value?.required && String(props.node.fieldValue).length == 0) {
			return 'Empty values are not permitted.';
		}

		return undefined;
	});

	const numberInputError = computed(() => {
		if (inputField.value?.required && String(props.node.fieldValue).length == 0) {
			return 'Empty values are not permitted.';
		}

		if (typeof props.node.fieldValue !== 'number' || isNaN(props.node.fieldValue)) {
			return 'Not a number.';
		}

		if (!isFinite(props.node.fieldValue)) {
			return 'Not finite.';
		}

		return undefined;
	});

	const error = computed(() => {
		if (inputType.value === 'string' && stringInputError.value) return stringInputError.value;
		if (inputType.value === 'number' && numberInputError.value) return numberInputError.value;
		return null;
	});

	const blankOrZeroField = computed(() => {
		if (inputType.value === 'string' && props.node.fieldValue === '') return 'Input field is empty.';
		if (inputType.value === 'number' && props.node.fieldValue === -2) return 'Input field is default number of -2.';
		return null;
	});

	onUnmounted(() => {
		errorStore.removeError(props.tabId, props.node.id, 'Input Field');
		errorStore.removeWarning(props.tabId, props.node.id, 'Input Field');
	});

	watch(
		error,
		() => {
			if (error.value === null) {
				errorStore.removeError(props.tabId, props.node.id, 'Input Field');
			} else if (error.value.trim() != '') {
				errorStore.addError(props.tabId, props.node.id, 'Input Field', error.value);
			}
		},
		{ immediate: true }
	);

	watch(
		blankOrZeroField,
		() => {
			if (blankOrZeroField.value === null) {
				errorStore.removeWarning(props.tabId, props.node.id, 'Input Field');
			} else if (blankOrZeroField.value.trim() != '') {
				errorStore.addWarning(props.tabId, props.node.id, 'Input Field', blankOrZeroField.value);
			}
		},
		{ immediate: true }
	);
</script>

<style scoped>
	.input-field-container {
		width: 100%;
		background-color: var(--color-editor-text-input-background);
		border-color: var(--color-editor-text-input-border);
		padding: 2px 2px 2px 6px;
		box-shadow: 0px 0px 6px 1px rgba(0, 0, 0, 0.3);
	}

	.input-field-container[floating-label='true'] {
		padding: 2px 2px 2px 6px;
	}

	.input-field-container[floating-label='false'] {
		padding: 6px 8px;
	}

	.input-field-container[focused='true'][error='false'] {
		border-color: var(--color-editor-text-input-border-highlight);
	}

	.input-field-container[error='true'] {
		border-color: var(--color-editor-text-input-error);
	}

	:deep(.input-field-label) {
		color: var(--color-text-secondary);
	}

	:deep(.input-field-label[label-lifted='true']) {
		color: var(--color-text-secondary);
	}

	:deep(.clear-icon) {
		margin-left: 3px;
	}

	:deep(.error-icon) {
		color: var(--color-editor-text-input-error);
	}
</style>
