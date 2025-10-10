<template>
	<div :style="errorStyle" class="tab no-select" ref="tabElement" @click="onClick" :active="active">
		{{ realTabName }}
	</div>
</template>

<script setup lang="ts">
	import { computed } from 'vue';

	const props = defineProps<{
		tabName: string;
		active: boolean;
		error?: boolean;
	}>();

	const emit = defineEmits<{
		(e: 'clicked'): void;
	}>();

	function onClick() {
		emit('clicked');
	}

	const realTabName = computed(() => {
		if (props.tabName == '') return 'Default';
		return props.tabName;
	});

	const errorStyle = computed(() => {
		if (props.error) {
			return {
				color: 'var(--color-error)',
				'border-bottom': 'solid 1px var(--color-error)'
			};
		}
		return {};
	});
</script>

<style scoped>
	.tab {
		margin-right: 8px;
		display: flex;
		flex-direction: row;
		align-items: center;
		height: 100%;
		cursor: pointer;
		opacity: 0.6;
		max-height: 17px;
	}

	.tab:hover {
		opacity: 1;
		border-bottom: solid 1px var(--color-primary);
	}

	.tab[active='true'] {
		opacity: 1;
		color: var(--color-primary);
	}
</style>
