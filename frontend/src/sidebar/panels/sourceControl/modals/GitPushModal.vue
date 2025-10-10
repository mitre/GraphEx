<template>
	<ModalFormComponent v-bind="form" @update-value="onUpdateValue" @close="onClose" @button-click="onButtonClick" />
</template>

<script setup lang="ts">
	import ModalFormComponent, { type ModalFormProps } from '@/components/modalForm/ModalFormComponent.vue';
	import type { InputValue, ModalFormEntryProps } from '@/components/modalForm/ModalFormEntry.vue';
	import { computed, type ComputedRef, ref } from 'vue';

	export interface ModalGitPushProps {
		title: string;
		username: string;
		password: string;
	}

	const props = defineProps<ModalGitPushProps>();
	const username = ref<string>(props.username);
	const password = ref<string>(props.password);

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'confirmClicked', data: { username: string; password: string }): void;
	}>();

	function onClose() {
		emit('close');
	}

	function confirmClicked() {
		emit('confirmClicked', {
			username: username.value,
			password: password.value
		});
	}

	function onUsernameChange(newValue: string) {
		username.value = newValue;
	}

	function onPasswordChange(newValue: string) {
		password.value = newValue;
	}

	function onUpdateValue(data: InputValue) {
		if (data.metadata.name == 'Username') onUsernameChange(data.value);
		if (data.metadata.name == 'Password') onPasswordChange(data.value);
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
				label: 'Username',
				help: 'Your git username',
				field: {
					value: String(username.value),
					disabled: false,
					password: false,
					focus: true
				}
			},
			{
				label: 'Password',
				help: 'Your git password',
				field: {
					value: String(password.value),
					disabled: false,
					password: true
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
					disabled: username.value === '' || password.value === ''
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
