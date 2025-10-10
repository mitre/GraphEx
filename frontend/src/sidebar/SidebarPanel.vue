<template>
	<div class="container" ref="panel">
		<div class="header-bar">
			<span class="header no-select">{{ props.header.toUpperCase() }}</span>
			<div class="buttons-bar">
				<slot name="buttons"></slot>
			</div>
		</div>
		<div class="sidebar-panel-contents custom-scrollbar">
			<slot></slot>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { ref } from 'vue';

	const panel = ref<HTMLDivElement>();

	defineExpose({ panel });

	const props = defineProps<{
		header: string;
	}>();
</script>

<style scoped>
	.container {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.buttons-bar {
		float: right;
	}

	.header-bar {
		padding: 0.5rem 1rem;
		margin-bottom: 1rem;
	}

	.header {
		color: var(--color-primary);
		font-weight: bold;
		font-size: 0.9rem;
		letter-spacing: 1px;
		float: left;
	}

	.sidebar-panel-contents {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
		padding-bottom: 40px;
		overflow-x: hidden;
		overflow-y: auto;
	}
</style>
