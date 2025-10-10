<template>
	<ModalFormComponent v-bind="form" @update-value="onUpdateValue" @close="onClose" @button-click="onButtonClick" />
</template>

<script setup lang="ts">
	import ModalFormComponent, { type ModalFormProps } from '@/components/modalForm/ModalFormComponent.vue';
	import type { InputValue, ModalFormEntryProps } from '@/components/modalForm/ModalFormEntry.vue';
	import { computed, type ComputedRef, ref } from 'vue';

	export interface ModalGitCommitProps {
		title: string;
		authorNameProp: string;
		authorEmailProp: string;
	}

	const props = defineProps<ModalGitCommitProps>();
	const commitMessage = ref<string>('');
	const authorName = ref<string>(props.authorNameProp);
	const authorEmail = ref<string>(props.authorEmailProp);

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'confirmClicked', data: { commitMsg: string; authorName: string; authorEmail: string }): void;
	}>();

	function onClose() {
		emit('close');
	}

	function confirmClicked() {
		emit('confirmClicked', {
			commitMsg: commitMessage.value,
			authorName: authorName.value,
			authorEmail: authorEmail.value
		});
	}

	function onUpdateValue(data: InputValue) {
		if (data.metadata.name == 'Commit Message') onCommitMsgChange(data.value);
		if (data.metadata.name == 'Author Name') onAuthorNameChange(data.value);
		if (data.metadata.name == 'Author Email') onAuthorEmailChange(data.value);
	}

	function onCommitMsgChange(newValue: string) {
		commitMessage.value = newValue;
	}

	function onAuthorNameChange(newValue: string) {
		authorName.value = newValue;
	}

	function onAuthorEmailChange(newValue: string) {
		authorEmail.value = newValue;
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
		entries.push(
			{
				label: 'Commit Message',
				help: 'The commit message',
				field: {
					value: String(commitMessage.value),
					disabled: false,
					password: false,
					focus: true
				}
			},
			{
				label: 'Author Name',
				help: 'The name that will appear on the commit message',
				field: {
					value: String(authorName.value),
					disabled: false,
					password: false
				}
			},
			{
				label: 'Author Email',
				help: 'The email that will appear on the commit message',
				field: {
					value: String(authorEmail.value),
					disabled: false,
					password: false
				}
			}
		);

		return {
			title: props.title,
			entries: entries,
			buttons: [
				{
					text: 'Confirm',
					type: 'primary',
					disabled: commitMessage.value === '' || authorEmail.value === '' || authorName.value === ''
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
