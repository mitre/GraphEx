<template>
	<span class="breadcrumbs no-select">
		<span class="breadcrumbs-home material-icons" @click="() => emit('returnToIndex', 0)">home</span>
		<template v-for="(item, index) in props.items" :key="index">
			<span class="breadcrumbs-separator material-icons">chevron_right</span>
			<span class="breadcrumbs-text" @click="() => emit('returnToIndex', index + 1)">{{ item }}</span>
		</template>
	</span>
</template>

<script setup lang="ts">
	const emit = defineEmits<{
		(e: 'returnToIndex', index: number): void;
	}>();

	const props = defineProps<{
		items: Array<string>;
	}>();
</script>

<style scoped>
	.breadcrumbs {
		width: 100%;
		margin-bottom: 1rem;
		display: flex;
		flex-wrap: wrap;
		row-gap: 6px;
		flex-direction: row;
		align-items: center;
	}

	.breadcrumbs-home {
		font-size: 1rem;
		color: var(--color-text);
		cursor: pointer;
	}

	.breadcrumbs-home:hover {
		color: var(--color-primary);
		transition: color 50ms linear;
	}

	.breadcrumbs-separator {
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.8;
	}

	.breadcrumbs-text {
		font-size: 0.9rem;
		cursor: pointer;
	}

	.breadcrumbs-text:hover {
		color: var(--color-primary);
		transition: color 50ms linear;
	}
</style>
