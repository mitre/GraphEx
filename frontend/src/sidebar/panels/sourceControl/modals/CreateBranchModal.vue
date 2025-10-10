<template>
	<ModalFormComponent v-bind="form" @update-value="onUpdateValue" @close="onClose" @button-click="onButtonClick" />
</template>

<script setup lang="ts">
	import ModalFormComponent, { type ModalFormProps } from '@/components/modalForm/ModalFormComponent.vue';
	import type { InputValue, ModalFormEntryProps } from '@/components/modalForm/ModalFormEntry.vue';
	import { computed, type ComputedRef, ref } from 'vue';

	export interface ModalCreateBranchProps {
		title: string;
	}

	const props = defineProps<ModalCreateBranchProps>();
	const branchName = ref<string>('');

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'confirmClicked', data: { newBranchName: string }): void;
	}>();

	function onClose() {
		emit('close');
	}

	function confirmClicked() {
		emit('confirmClicked', {
			newBranchName: branchName.value
		});
	}

	function onBranchNameChange(newValue: string) {
		branchName.value = newValue;
	}

	function onUpdateValue(data: InputValue) {
		if (data.metadata.name == 'Branch Name') onBranchNameChange(data.value);
	}

	function onButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (data.buttonName == 'Confirm') {
			confirmClicked();
		}

		if (data.buttonName == 'Close') {
			onClose();
		}
	}

	const form: ComputedRef<ModalFormProps> = computed(() => {
		const entries: Array<ModalFormEntryProps> = [];
		entries.push({
			label: 'Branch Name',
			help: 'The name of the new branch',
			field: {
				value: String(branchName.value),
				disabled: false,
				password: false,
				focus: true
			}
		});

		return {
			title: props.title,
			entries: entries,
			buttons: [
				{
					text: 'Confirm',
					type: 'primary',
					disabled: branchName.value === ''
				},
				{
					text: 'Close',
					type: 'secondary'
				}
			]
		};
	});
</script>

<style scoped>
	:deep(.modal-popup) {
		width: 50vw;
		overflow: hidden;
	}

	.modal-form-contents-container {
		max-height: 75vh;
		display: flex;
		flex-direction: column;
		padding: 8px;
		overflow-x: hidden;
		overflow-y: auto;
	}

	.modal-form-footer {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
	}

	.modal-form-footer > *:not(:last-child) {
		margin-right: 12px;
	}
</style>
