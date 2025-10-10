<template>
	<SidebarPanel header="Errors and Warnings">
		<div class="item-list">
			<ErrorChildComponent v-for="(errorInfo, index) in erroredSocketInfos" :key="index" v-bind="errorInfo" />
			<ErrorChildComponent v-for="(errorInfo, index) in warningSocketInfos" :key="index" v-bind="errorInfo" :is-warning="true" />
		</div>
	</SidebarPanel>
</template>

<script setup lang="ts">
	import SidebarPanel from '@/sidebar/SidebarPanel.vue';
import type { SocketErrorInfo } from '@/sidebar/panels/ErrorChildComponent.vue';
import ErrorChildComponent from '@/sidebar/panels/ErrorChildComponent.vue';
import { useEditorStore, useErrorStore } from '@/stores';
import { computed } from 'vue';

	const editorStore = useEditorStore();
	const errorStore = useErrorStore();

	const erroredSocketInfos = computed(() => {
		const errorInfoList: Array<SocketErrorInfo> = [];
		if (!editorStore.activeGraphTab) {
			return errorInfoList;
		}

		if (!(editorStore.activeGraphTab.id in errorStore.errorMap)) {
			return errorInfoList;
		}

		const errors = errorStore.errorMap[editorStore.activeGraphTab.id];
		for (const nodeId of Object.keys(errors)) {
			for (const socketName of Object.keys(errors[nodeId])) {
				errorInfoList.push({
					socketName: socketName,
					nodeId: nodeId,
					msg: errors[nodeId][socketName]
				});
			}
		}

		return errorInfoList;
	});

	const warningSocketInfos = computed(() => {
		const warningInfoList: Array<SocketErrorInfo> = [];
		if (!editorStore.activeGraphTab) {
			return warningInfoList;
		}

		if (!(editorStore.activeGraphTab.id in errorStore.warningMap)) {
			return warningInfoList;
		}

		const warnings = errorStore.warningMap[editorStore.activeGraphTab.id];
		for (const nodeId of Object.keys(warnings)) {
			for (const socketName of Object.keys(warnings[nodeId])) {
				warningInfoList.push({
					socketName: socketName,
					nodeId: nodeId,
					msg: warnings[nodeId][socketName]
				});
			}
		}

		return warningInfoList;
	});
</script>

<style scoped>
	.item-list {
		padding: 0px 0.75rem;
		display: flex;
		flex-direction: column;
		align-items: center;
	}
</style>
