<template>
	<template v-if="props.socket.metadata.canHaveField">
		<InputField
			v-if="props.socket.metadata.datatype == 'String' && !('enumOptions' in props.socket.metadata)"
			:value="String(props.socket.fieldValue)"
			:min-width="4"
			@input="updateValue"
			@change="onChange"
		/>

		<InputField
			v-if="props.socket.metadata.datatype == 'Number' && !('enumOptions' in props.socket.metadata)"
			:value="String(props.socket.fieldValue)"
			:min-width="4"
			:error="numberInputError"
			@input="updateNumberValue"
			@change="onChangeNumber"
		/>

		<BooleanCheckboxInput
			v-if="props.socket.metadata.datatype == 'Boolean' && !('enumOptions' in props.socket.metadata)"
			:value="props.socket.fieldValue"
			@update="updateValue"
		/>

		<EnumeratedDropdownInput
			v-if="'enumOptions' in props.socket.metadata"
			:value="String(props.socket.fieldValue)"
			:enumOptions="props.socket.metadata.enumOptions"
			@update="updateValue"
		/>
	</template>
</template>

<script setup lang="ts">
	import InputField from '@/components/InputField.vue';
	import BooleanCheckboxInput from '@/editor/graph/inputs/BooleanCheckboxInput.vue';
	import EnumeratedDropdownInput from '@/editor/graph/inputs/EnumeratedDropdownInput.vue';
	import type { Socket } from '@/graph';
	import { computed } from 'vue';

	const props = defineProps<{
		/** The socket for this input. */
		socket: Socket;
		disabled?: boolean;
	}>();

	function updateValue(newValue: any) {
		if (props.disabled) {
			return;
		}
		props.socket.setFieldValue(newValue);
	}

	function updateNumberValue(newValue: any) {
		if ((typeof newValue === 'string' && newValue.trim().length == 0) || isNaN(Number(newValue))) {
			updateValue(newValue);
		} else {
			updateValue(Number(newValue));
		}
	}

	async function onChange(newValue: any) {
		updateValue(newValue);
	}

	async function onChangeNumber(newValue: any) {
		updateNumberValue(newValue);
	}

	const numberInputError = computed(() => {
		if (String(props.socket.fieldValue).length == 0) {
			return 'Empty values are not permitted.';
		}

		if (typeof props.socket.fieldValue !== 'number' || isNaN(props.socket.fieldValue)) {
			return 'Not a number.';
		}

		if (!isFinite(props.socket.fieldValue)) {
			return 'Not finite.';
		}

		return undefined;
	});
</script>

<style scoped>
	.input-field-container {
		background-color: var(--color-editor-text-input-background);
		border-color: var(--color-editor-text-input-border);
		padding: 1px 1px 1px 4px;
		box-shadow: 0px 0px 6px 1px rgba(0, 0, 0, 0.3);
	}

	.input-field-container[focused='true'][error='false'] {
		border-color: var(--color-editor-text-input-border-highlight);
	}

	.input-field-container[error='true'] {
		border-color: var(--color-editor-text-input-error);
	}

	:deep(.clear-icon) {
		margin-left: 3px;
	}

	:deep(.error-icon) {
		color: var(--color-editor-text-input-error);
	}

	:deep(.boolean-input-text) {
		min-width: 2.8em;
		font-size: 0.9rem;
	}

	:deep(.boolean-input-icon) {
		font-size: 1.1rem;
	}
</style>
