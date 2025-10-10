<template>
	<div
		class="button no-select"
		:type="props.type"
		:title="props.hint"
		:disabled="props.disabled"
		@mousedown.stop
		@mouseup.stop
		@click.stop.prevent="onClick"
		ref="button"
	>
		{{ props.text }}
	</div>
</template>

<script setup lang="ts">
	import { ref } from 'vue';

	export interface ButtonProps {
		text: string;
		hint?: string;
		type: 'primary' | 'secondary' | 'warning';
		disabled?: boolean;
	}

	const props = defineProps<ButtonProps>();

	const emit = defineEmits<{
		(e: 'click'): void;
	}>();

	const button = ref<HTMLDivElement>();

	function onClick(event: MouseEvent) {
		if (!button.value || props.disabled) {
			return;
		}

		const diameter = Math.max(button.value.clientWidth, button.value.clientHeight);
		const circle = document.createElement('span');
		circle.style.width = `${diameter}px`;
		circle.style.height = `${diameter}px`;
		circle.style.left = `${event.offsetX - diameter / 2}px`;
		circle.style.top = `${event.offsetY - diameter / 2}px`;
		circle.classList.add('ripple');

		const ripple = button.value.getElementsByClassName('ripple')[0];
		if (ripple) {
			ripple.remove();
		}

		button.value.appendChild(circle);

		emit('click');
	}
</script>

<style scoped>
	.button {
		min-width: 4rem;
		padding: 8px 16px;
		display: flex;
		align-items: center;
		justify-content: center;
		text-transform: uppercase;
		font-size: 0.9rem;
		cursor: pointer;
		box-shadow: 0 0 4px 0px rgba(0, 0, 0, 0.2);
		transition: background-color 50ms linear;
		position: relative;
		overflow: hidden;
	}

	.button[type='primary'] {
		color: var(--color-button-text);
		background-color: var(--color-button-primary);
	}

	.button[type='primary']:hover {
		background-color: var(--color-button-primary-hover);
	}

	.button[type='secondary'] {
		color: var(--color-button-text);
		background-color: var(--color-button-secondary);
	}

	.button[type='secondary']:hover {
		background-color: var(--color-button-secondary-hover);
	}

	.button[type='warning'] {
		color: var(--color-button-text);
		background-color: var(--color-button-warning);
	}

	.button[type='warning']:hover {
		background-color: var(--color-button-warning-hover);
	}

	.button[disabled='true'] {
		color: var(--color-button-disabled-text);
		background-color: var(--color-button-disabled);
		cursor: default;
	}

	.button[disabled='true']:hover {
		color: var(--color-button-disabled-text);
		background-color: var(--color-button-disabled);
	}

	:deep(.ripple) {
		position: absolute;
		border-radius: 50%;
		transform: scale(0);
		animation: ripple 600ms linear;
		background-color: rgba(255, 255, 255, 0.2);
		pointer-events: none;
	}

	@keyframes ripple {
		to {
			transform: scale(4);
			opacity: 0;
		}
	}
</style>
