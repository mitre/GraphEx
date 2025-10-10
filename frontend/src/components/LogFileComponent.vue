<template>
	<tr class="file-row" @click="onClicked">
		<th>{{ nameNoStamp }}</th>
		<td>{{ unixTimestamp }}</td>
		<td>{{ createdCalendarDate }}</td>
		<td>{{ createdTime }}</td>
	</tr>
	<br />
</template>

<script setup lang="ts">
	import { useTerminalStore } from '@/stores';
	import { computed } from 'vue';

	const props = defineProps<{
		name: string;
		path: string;
	}>();

	const emit = defineEmits<{
		(e: 'close'): void;
	}>();

	const terminalStore = useTerminalStore();

	async function onClicked() {
		await terminalStore.openLogFile(props.name, props.path);
		emit('close');
	}

	const lastHyphen = computed(() => {
		return props.name.lastIndexOf('-');
	});

	const nameNoStamp = computed(() => {
		const i = lastHyphen.value;
		if (!i || i < 0) return props.name;
		return props.name.substring(0, i);
	});

	const unixTimestamp = computed(() => {
		const i = lastHyphen.value;
		if (!i || i < 0) return '';
		let ts = props.name.substring(i + 1);
		if (ts.endsWith('.log')) {
			ts = ts.substring(0, ts.lastIndexOf('.log'));
		}
		return ts;
	});

	const dateObj = computed(() => {
		return new Date(Number(unixTimestamp.value) * 1000);
	});

	const createdCalendarDate = computed(() => {
		return dateObj.value.toLocaleDateString('en-US');
	});

	const createdTime = computed(() => {
		return dateObj.value.toLocaleTimeString('en-US');
	});
</script>

<style scoped>
	.file-row:hover {
		cursor: pointer;
		color: var(--color-primary);
	}

	.file-row {
		text-align: center;
	}

	td th {
		padding: 20px;
	}
</style>
