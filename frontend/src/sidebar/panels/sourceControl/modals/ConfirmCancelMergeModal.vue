<template>
	<ModalComponent :title="props.title" @close="onClose">
		<template v-slot:contents>
			<div class="modal-form-contents-container custom-scrollbar">
				The merge will be undone. Any uncommitted changes to the branch will be preserved.
			</div>
		</template>
		<template v-slot:footer>
			<div class="modal-form-footer">
				<template v-for="(button, index) in props.buttons" :key="index">
					<ButtonComponent v-bind="button" @click="buttonClick(index, button.text)" />
				</template>
			</div>
		</template>
	</ModalComponent>
</template>

<script setup lang="ts">
	import type { ButtonProps } from '@/components/ButtonComponent.vue';
	import ButtonComponent from '@/components/ButtonComponent.vue';
	import ModalComponent from '@/components/ModalComponent.vue';
	import { defineEmits, defineProps } from 'vue';

	export interface ConfirmCancelMergeModalProps {
		title: string;
		buttons: ButtonProps[];
	}

	const props = defineProps<ConfirmCancelMergeModalProps>();

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'buttonClick', data: { buttonIndex: number; buttonName: string }): void;
	}>();

	function onClose() {
		emit('close');
	}

	function buttonClick(buttonIndex: number, name: string) {
		emit('buttonClick', { buttonIndex, buttonName: name });
	}
</script>

<style scoped>
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
