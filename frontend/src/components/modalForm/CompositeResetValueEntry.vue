<template>
	<div>
		<div v-for="(value, index) in values" :key="index" :style="{ marginLeft: `${level * 20}px` }">
			<div v-if="value.isModified">
				<b>{{ value.name }}: </b>
				<template v-if="value.children.length > 0">
					<CompositeResetValueEntry :values="value.children" :level="level + 1" />
				</template>
				<template v-else>
					<span>{{ value.presetValue }}</span>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import type { CompositeValue } from '@/graph';
	import { defineProps } from 'vue';

	const props = defineProps<{
		values: CompositeValue[];
		level?: number;
	}>();

	const level = props.level ?? 0;
</script>

<style scoped>
	/* Add any specific styles for the recursive component here if needed */
</style>
