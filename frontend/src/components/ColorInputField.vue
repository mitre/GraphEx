<template>
	<input
		type="number"
		class="rgb-field"
		:value="props.value"
		min="0"
		max="255"
		maxlength="3"
		@input.stop="onInput"
		@keydown.stop="checkValue"
		@submit.stop="checkValue"
		@blur.stop="checkValue"
	/>
</template>

<script setup lang="ts">
	const props = defineProps<{
		value: number;
	}>();

	const emit = defineEmits<{
		(e: 'update', value: number): void;
	}>();

	function onInput(event: Event) {
		if (!event.target) {
			return;
		}

		const target = event.target as HTMLInputElement;
		emit('update', Number(target.value));
	}

	function checkValue() {
		if (props.value < 0) emit('update', 0);
		else if (props.value > 255) emit('update', 255);
	}
</script>

<style scoped>
	.rgb-field {
		width: 64px;
		padding: 4px;
		padding-right: 2px;
		outline: none;
		border: none;
		background-color: var(--color-foreground-secondary);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		color: var(--color-text);
	}
</style>
