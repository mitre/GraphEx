<template>
	<div class="boolean-checkbox-input" :title="fieldName" @click.stop="onClick">
		<div class="boolean-check-icon material-icons" :checked="!!props.value">check</div>
	</div>
</template>

<script setup lang="ts">
	const props = defineProps<{
		fieldName?: string;
		value: any;
	}>();

	const emit = defineEmits<{
		(e: 'update', newValue: any): void;
	}>();

	function onClick() {
		emit('update', !props.value);
	}
</script>

<style scoped>
	.boolean-checkbox-input {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
		background-color: var(--color-editor-text-input-background);
		border: 1px solid rgb(100, 100, 100);
		border-radius: 5px;
		padding: 2px;
	}

	.boolean-check-icon {
		font-size: 14px;
		opacity: 0;
	}

	.boolean-check-icon[checked='true'] {
		opacity: 1;
	}
</style>
