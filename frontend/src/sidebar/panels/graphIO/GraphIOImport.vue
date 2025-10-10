<template>
	<ModalColumnSelector
		title="Import Graph Inputs From Configuration File"
		:left-column="leftColumn"
		:right-column="rightColumn"
		left-column-header="Configuration File"
		right-column-header="Imports"
		:buttons="buttons"
		:loading="loading"
		help="This modal can be used to import Graph Inputs from the configuration file provided to GraphEx when it was served. The left-hand column contains all the options for import and the right-hand column shows the inputs you've elected to import. Left-click the names of the inputs you wish to use in the current graph and then left-click the single arrow to choose them for import. Secrets will always be imported as Strings because their datatype is encrypted alongside the data."
		@close="onClose"
		@button-click="onButtonClick"
	/>
</template>

<script setup lang="ts">
	import type { ButtonProps } from '@/components/ButtonComponent.vue';
import ModalColumnSelector from '@/components/modalForm/ModalColumnSelector.vue';
import type { Graph } from '@/graph';
import { useEditorStore, useFileStore, useTerminalStore } from '@/stores';
import { onMounted, ref } from 'vue';

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'import', data: { lCol: Array<string>, rCol: Array<string>, configData: { [inputName: string]: any }, secretData: string[] }): void;
	}>();

	const buttons = ref<Array<ButtonProps>>([
		{
			text: 'Import',
			type: 'primary'
		},
		{
			text: 'Close',
			type: 'secondary'
		}
	]);

	async function onButtonClick(data: { buttonIndex: number; buttonName: string, lCol: Array<string>, rCol: Array<string> }) {
		if (data.buttonName == 'Import') {
			await onImport(data.lCol, data.rCol);
		}

		if (data.buttonName == 'Close') {
			await onClose();
		}
	}

	async function onImport(l: Array<string>, r: Array<string>) {
		emit('import', { lCol: l, rCol: r, configData: configFileValues.value, secretData: secretValues.value });
	}

	async function onClose() {
		emit('close');
	}

	const terminalStore = useTerminalStore();
	const editorStore = useEditorStore();
	const fileStore = useFileStore();

	/** The current values from the config file, it is updated via the function: fetchConfigData() */
	const configFileValues = ref<{ [inputName: string]: any }>({});
	const secretValues = ref<string[]>([]);

	const leftColumn = ref<Array<string>>([]);
	const rightColumn = ref<Array<string>>([]);

	/** Gets set to false when the fetch completes */
	const loading = ref<boolean>(true);

	const props = defineProps<{
		/** The graph that this input belongs to */
		graph: Graph;
	}>();

	/**
	 * Grabs the current values from the configuration file (expensive)
	 */
	async function fetchConfigData() {
		try {
			const pathOrName = editorStore.activeGraphTab!.fileId
				? fileStore.getFilePath(editorStore.activeGraphTab!.fileId)
				: editorStore.activeGraphTab!.name;
			const payloadResponse = await terminalStore.fetchGraphInputData(props.graph, pathOrName, true);
			configFileValues.value = payloadResponse['inputs'];
			secretValues.value = payloadResponse['secrets'];

			const configNames = new Set(secretValues.value);
			for (var k in configFileValues.value) {
				configNames.add(k);
			}
			leftColumn.value = Array.from(configNames).sort();
		} finally {
			loading.value = false;
		}
	}

	onMounted(async () => {
		fetchConfigData();
	});
</script>

<style scoped></style>
