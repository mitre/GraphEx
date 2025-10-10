<template>
	<div class="category" :key="props.name" @click="() => emit('selected')">
		<span class="category-name no-select">{{ props.name }}</span>
		<span class="material-icons arrow-icon">arrow_forward_ios</span>
	</div>
</template>

<script setup lang="ts">
	const emit = defineEmits<{
		(e: 'selected'): void;
	}>();

	const props = defineProps<{
		name: string;
	}>();
</script>

<style scoped>
	.category {
		width: 100%;
		padding: 8px;
		margin-top: 5px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		color: var(--color-text);
		background-color: var(--color-background-primary);
		transition: background-color 50ms linear;
		cursor: pointer;
	}

	.category:hover {
		background-color: var(--color-foreground-secondary);
	}

	.arrow-icon {
		color: var(--color-text);
		font-size: 0.8rem;
	}
</style>
