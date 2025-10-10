<template>
	<ModalFormComponent
		v-if="form"
		v-bind="form"
		@close="onClose"
		@toggled="onToggle"
		@update-value="onUpdateValue"
		@remove-list-entry="onRemoveListEntry"
		@add-list-entry="onAddListEntry"
		@update-list-value="onUpdateListEntry"
		@button-click="onButtonClick"
	/>
</template>

<script setup lang="ts">
	import { usePromptStore } from '@/stores';
	import { computed, type ComputedRef } from 'vue';
	import ModalFormComponent, { type ModalFormProps } from './modalForm/ModalFormComponent.vue';
	import type {
		CompositeEntryMetadata,
		InputValue,
		ListIndexValue,
		ListInputValue,
		ToggleValue
	} from './modalForm/ModalFormEntry.vue';

	const promptStore = usePromptStore();

	function onClose() {
		promptStore.complete(null);
	}

	function onToggle(data: ToggleValue) {
		if (!data.metadata.subMetadata) {
			const currentForm = form.value;
			if (!currentForm) return;
			currentForm.entries[data.metadata.index].isToggled = !currentForm.entries[data.metadata.index].isToggled;
			promptStore.update(currentForm);
		} else {
			throw 'Recursion not implemented yet';
		}
	}

	function onUpdateValue(data: InputValue) {
		if (!data.metadata.subMetadata) {
			const currentForm = form.value;
			if (!currentForm) return;
			const field = currentForm.entries[data.metadata.index].field;
			if (!field) return;
			field.value = data.value;
			promptStore.update(currentForm);
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onRemoveListEntry(data: ListIndexValue) {
		if (!data.metadata.subMetadata) {
			const currentForm = form.value;
			if (!currentForm) return;
			const fieldList = currentForm.entries[data.metadata.index].fieldList;
			if (fieldList === null || fieldList === undefined) return;
			fieldList.splice(data.index, 1);
			promptStore.update(currentForm);
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onAddListEntry(data: CompositeEntryMetadata) {
		if (!data.subMetadata) {
			const currentForm = form.value;
			if (!currentForm) return;
			const fieldList = currentForm.entries[data.index].fieldList;
			if (fieldList === null || fieldList === undefined) return;
			fieldList.push({ value: '' });
			promptStore.update(currentForm);
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onUpdateListEntry(data: ListInputValue) {
		if (!data.metadata.subMetadata) {
			const currentForm = form.value;
			if (!currentForm) return;
			const fieldList = currentForm.entries[data.metadata.index].fieldList;
			if (fieldList === null || fieldList === undefined) return;
			fieldList[data.index].value = data.value;
			promptStore.update(currentForm);
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (!form.value) return;
		promptStore.complete({ buttonName: data.buttonName, form: form.value });
	}

	const form: ComputedRef<ModalFormProps | null> = computed(() => {
		if (promptStore.prompts.length == 0) {
			return null;
		}
		return JSON.parse(JSON.stringify(promptStore.prompts[promptStore.prompts.length - 1]));
	});
</script>

<style scoped>
	.modal-container {
		z-index: 1000;
	}

	:deep(.modal-popup) {
		min-width: 20vw;
		max-width: 40vw;
	}
</style>
