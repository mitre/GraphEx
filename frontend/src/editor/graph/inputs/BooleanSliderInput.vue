<template>
	<div class="boolean-slider-input" :title="fieldName" @click.stop>
		<div class="boolean-slider-input-icon material-icons" @click.stop="onClick" @dblclick.stop.prevent>
			chevron_left
		</div>
		<div class="boolean-slider-input-text no-select">{{ value }}</div>
		<div class="boolean-slider-input-icon material-icons" @click.stop="onClick" @dblclick.stop.prevent>
			chevron_right
		</div>
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
	.boolean-slider-input {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
		padding: 2px 4px;
	}

	.boolean-slider-input-text {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 3em;
		font-size: 1rem;
		color: var(--color-editor-node-body-text-primary);
		text-transform: capitalize;
	}

	.boolean-slider-input-icon {
		font-size: 1.4rem;
		color: var(--color-editor-node-body-text-secondary);
		border-radius: 5px;
	}

	.boolean-slider-input-icon:hover {
		background-color: var(--color-editor-node-background-secondary);
	}
</style>
