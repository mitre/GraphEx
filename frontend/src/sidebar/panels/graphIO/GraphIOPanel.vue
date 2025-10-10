<template>
	<SidebarPanel header="Configure Graph" ref="iopanel" @click="onSidebarMouseDown">
		<div class="graph-io-panel-container">
			<div class="graph-io-panel-header">
				<span
					class="graph-io-panel-title no-select"
					title="All inputs (e.g. CLI arguments) for this graph. These are determined by the 'Graph Input' nodes in the graph. Click on any tab to configure it."
				>
					Graph Inputs
				</span>
				<div class="button-bar">
					<span class="material-icons button" title="Fold All" @click="foldAll">unfold_less</span>
					<span class="material-icons button" title="Unfold All" @click="unfoldAll">unfold_more</span>
					<span class="material-icons button" title="Import From Configuration File" @click="importOpen=true">download</span>
					<span class="material-icons add-icon" title="Add New Input" @click.stop="() => addNewInput(null)">add</span>
				</div>
			</div>
			<template v-if="activeGraph && activeGraph.inputMetadata.length">
				<template v-for="(inputs, category) in groupedInputs" :key="category">
					<GraphGroupInputTabComponent
						ref="groupTabs"
						:category="!category || String(category) === '' ? 'Default' : String(category)"
						:graph="activeGraph"
						:inputs="
							inputs.map((input) => ({
								metadata: input,
								isSelected:
									selectedInputs.findIndex((i) => i.name == input.name) > -1 && graphWithSelectedInputs == activeTabId
							}))
						"
						:any-copied="anyInputCopied"
						:any-selected="anyInputSelected"
						@add-new-input="addNewInput"
						@selected="onInputSelected"
						@cancel-selection="onCancelInputSelection"
						@copy-selected="copySelectedInputs"
						@paste-clipboard="pasteSelectedInputs"
						@cut-selected="cutSelected(true)"
						@deselect-input="deselectInput"
					/>
				</template>
			</template>
			<span v-else class="graph-io-empty-text no-select">No Inputs Configured...</span>

			<div class="graph-io-panel-header" :style="{ 'margin-top': '32px' }">
				<span
					class="graph-io-panel-title no-select"
					title="All outputs for this graph (only applicable when this graph is executed by another graph). These are determined by the 'Graph Output' nodes in the graph. Click on any tab to configure it."
				>
					Graph Outputs
				</span>
				<span class="material-icons add-icon" title="Add New Output" @click.stop="() => addNewOutput(null)">add</span>
			</div>
			<template v-if="activeGraph && activeGraph.outputMetadata.length">
				<template v-for="(metadata, index) in activeGraph.outputMetadata" :key="index">
					<GraphIOTabComponent
						ref="groupTabs"
						:graph="activeGraph"
						:output="metadata"
						:selected="
							selectedOutputs.findIndex((i) => i.name == metadata.name) > -1 && graphWithSelectedOutputs == activeTabId
						"
						:any-selected="anyOutputSelected"
						:any-copied="anyOutputCopied"
						@add-new-input="addNewInput"
						@add-new-output="addNewOutput"
						@selected="onOutputSelected(metadata)"
						@cancel-selection="onCancelOutputSelection(metadata)"
						@copy-selected="copySelectedOutputs"
						@paste-clipboard="pasteSelectedOutputs"
						@cut-selected="cutSelected(false)"
					/>
				</template>
			</template>
			<span v-else class="graph-io-empty-text no-select">No Outputs Configured...</span>
			<div class="graph-io-panel-header" :style="{ 'margin-top': '32px' }">
				<span class="graph-io-panel-title no-select" title="The description for this graph."> Graph Description </span>
			</div>
			<textarea
				v-if="activeGraph"
				@keydown.stop
				class="description-input"
				placeholder="No description provided"
				tabindex="0"
				rows="4"
				v-model="activeGraph.description"
			></textarea>
		</div>

		<GraphIOImport
			v-if="importOpen && activeGraph"
			:graph="activeGraph"
			@close="closeModals"
			@import="importInputs"
		/>

		<GraphIOConfigureInputModal
			v-if="newInput && activeGraph"
			:graph="activeGraph"
			:metadata="newInput"
			@save="saveInput"
			@close="closeModals"
			is-new
		/>

		<GraphIOConfigureOutputModal
			v-if="newOutput && activeGraph"
			:graph="activeGraph"
			:metadata="newOutput"
			@save="saveOutput"
			@close="closeModals"
			is-new
		/>
	</SidebarPanel>
</template>

<script setup lang="ts">
	import type { GraphInputMetadata, GraphOutputMetadata, GroupedInputs } from '@/graph';
import SidebarPanel from '@/sidebar/SidebarPanel.vue';
import GraphIOTabComponent from '@/sidebar/panels/graphIO/GraphIOTabComponent.vue';
import { useContextmenuStore, useEditorStore, useMetadataStore, usePromptStore } from '@/stores';
import { computed, nextTick, onMounted, ref } from 'vue';

	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import GraphGroupInputTabComponent from '@/sidebar/panels/graphIO/./GraphGroupInputTabComponent.vue';
import GraphIOConfigureInputModal from '@/sidebar/panels/graphIO/GraphIOConfigureInputModal.vue';
import GraphIOConfigureOutputModal from '@/sidebar/panels/graphIO/GraphIOConfigureOutputModal.vue';
import GraphIOImport from './GraphIOImport.vue';

	const groupTabs = ref<(typeof GraphGroupInputTabComponent)[]>();

	function foldAll() {
		if (groupTabs.value) {
			groupTabs.value.forEach((t) => {
				t.closeTab();
			});
		}
	}

	function unfoldAll() {
		if (groupTabs.value) {
			groupTabs.value.forEach((t) => {
				t.openTab();
			});
		}
	}
	const editorStore = useEditorStore();
	const contextmenuStore = useContextmenuStore();
	const metadataStore = useMetadataStore();
	const promptStore = usePromptStore();

	const importOpen = ref<boolean>(false);
	const newInput = ref<GraphInputMetadata | null>();
	const newOutput = ref<GraphOutputMetadata | null>();

	const iopanel = ref<any>();

	const selectedInputs = ref<GraphInputMetadata[]>([]);
	const graphWithSelectedInputs = ref<string>('');

	const selectedOutputs = ref<GraphOutputMetadata[]>([]);
	const graphWithSelectedOutputs = ref<string>('');

	const activeTabId = computed(() => editorStore.activeTab?.id);
	const activeGraph = computed(() => (editorStore.activeGraphTab ? editorStore.activeGraphTab.contents : null));

	const anyInputSelected = computed(() => {
		return selectedInputs.value.length > 0 && graphWithSelectedInputs.value == activeTabId.value;
	});
	const anyOutputSelected = computed(() => {
		return selectedOutputs.value.length > 0 && graphWithSelectedOutputs.value == activeTabId.value;
	});
	const copiedInputs = computed(() => {
		return metadataStore.copiedInputMetadata;
	});
	const copiedOutputs = computed(() => {
		return metadataStore.copiedOutputMetadata;
	});
	const anyInputCopied = computed(() => {
		return copiedInputs.value.length > 0;
	});
	const anyOutputCopied = computed(() => {
		return copiedOutputs.value.length > 0;
	});

	async function importInputs(data: { lCol: Array<string>, rCol: Array<string>, configData: { [inputName: string]: any }, secretData: string[] }) {
		for (const n of data.rCol) {
			// handle if the graph already has an input with this name
			if (activeGraph.value!.inputMetadata.findIndex((md) => md.name == n) >= 0) {
				// input already exists, ask the user what to do now
				const value = await promptStore.show({
					title: 'Input Already Exists',
					additionalInfo: `A Graph Input already exists with the name: '${n}'! It is recommended you skip importing this entry but you can also choose to remove it and replace it with the boilerplate created by this import process.`,
					entries: [],
					buttons: [
						{
							text: 'Skip',
							hint: 'Skip this import because data already exists in the Sidebar Panel',
							type: 'primary'
						},
						{
							text: 'Delete',
							hint: 'Erase the data for this input from the Sidebar Panel and use the default data created by this import process',
							type: 'warning'
						}
					]
				});

				// If something goes wrong
				if (!value) {
					continue;
				}

				// Skip and move on to the next input
				if (value.buttonName == 'Skip') {
					continue;
				}

				// Delete and run the import
				if (value.buttonName == 'Delete') {
					activeGraph.value?.removeInputMetadata(n);
				}
			}

			if (data.secretData.includes(n)) {
				// add secret
				activeGraph.value?.updateInputMetadata(
					{
						name: n,
						datatype: "String",
						isSecret: true,
						isPassword: false,
						description: "",
						isList: false
					}
				);
			} else {
				// add normal input (we know its here because rCol was only populated with values from secrets and/or config file pairs)
				const dataObj = data.configData[n];
				activeGraph.value?.updateInputMetadata(
					{
						name: n,
						datatype: dataObj.datatype,
						isSecret: false,
						isPassword: false,
						description: "",
						isList: Array.isArray(dataObj.value)
					}
				);
			}
		}
		
		closeModals();
	}

	function onInputSelected(metadata: GraphInputMetadata) {
		if (!activeGraph.value) return;

		if (activeTabId.value && graphWithSelectedInputs.value !== activeTabId.value) {
			graphWithSelectedInputs.value = activeTabId.value;
			selectedInputs.value = [];
		} else {
			const location = selectedInputs.value.findIndex((si) => si.name == metadata.name);
			if (location > -1) {
				selectedInputs.value.splice(location);
				return;
			}
		}
		selectedInputs.value.push(metadata);
	}

	function deselectInput(metadata: GraphInputMetadata) {
		const location = selectedInputs.value.findIndex((si) => si.name === metadata.name);
		if (location > -1) {
			selectedInputs.value.splice(location, 1); // Remove the item at the found index
		}
	}

	function onCancelInputSelection(metadata: GraphInputMetadata) {
		const location = selectedInputs.value.findIndex((si) => si.name == metadata.name);
		if (location > -1) {
			selectedInputs.value.splice(location);
		}
	}

	function onOutputSelected(metadata: GraphOutputMetadata) {
		if (!activeGraph.value) return;

		if (activeTabId.value && graphWithSelectedOutputs.value !== activeTabId.value) {
			graphWithSelectedOutputs.value = activeTabId.value;
			selectedOutputs.value = [];
		} else {
			const location = selectedOutputs.value.findIndex((so) => so.name == metadata.name);
			if (location > -1) {
				selectedOutputs.value.splice(location, 1);
				return;
			}
		}
		selectedOutputs.value.push(metadata);
	}

	function onCancelOutputSelection(metadata: GraphOutputMetadata) {
		const location = selectedOutputs.value.findIndex((so) => so.name == metadata.name);
		if (location > -1) {
			selectedOutputs.value.splice(location, 1);
		}
	}

	function onSidebarMouseDown(event: MouseEvent) {
		if (event.button != 0) {
			return;
		}

		selectedInputs.value = [];
		selectedOutputs.value = [];
	}

	function addNewInput(template: GraphInputMetadata | null = null) {
		newInput.value = template || {
			name: 'MyInput',
			datatype: 'String'
		};
	}

	function addNewOutput(template: GraphOutputMetadata | null = null) {
		newOutput.value = template || {
			name: 'MyOutput',
			datatype: 'String'
		};
	}

	function saveInput(metadata: GraphInputMetadata) {
		activeGraph.value?.updateInputMetadata(metadata);
		openGroupTabFromInput(metadata);
	}

	function saveOutput(metadata: GraphOutputMetadata) {
		activeGraph.value?.updateOutputMetadata(metadata);
	}

	function closeModals() {
		newInput.value = null;
		newOutput.value = null;
		importOpen.value = false;
	}

	function copySelectedInputs() {
		if (activeGraph.value) {
			metadataStore.storeCopiedInputs(selectedInputs.value);
		}
	}

	function copySelectedOutputs() {
		if (activeGraph.value) {
			metadataStore.storeCopiedOutputs(selectedOutputs.value);
		}
	}

	function pasteSelectedInputs() {
		for (const i of copiedInputs.value) {
			if (activeGraph.value) {
				if (activeGraph.value.inputMetadata.findIndex((gi: GraphInputMetadata) => gi.name == i.name) >= 0) {
					promptStore.failedAlert(
						'Failed to Paste Graph Input',
						'An input with this name already exists in the destination graph: ' + i.name
					);
					return;
				}
				activeGraph.value.updateInputMetadata(i);
				openGroupTabFromInput(i);
			}
		}
	}

	function pasteSelectedOutputs() {
		for (const o of copiedOutputs.value) {
			if (activeGraph.value) {
				if (activeGraph.value.outputMetadata.findIndex((go: GraphOutputMetadata) => go.name == o.name) >= 0) {
					promptStore.failedAlert(
						'Failed to Paste Graph Output',
						'An output with this name already exists in the destination graph: ' + o.name
					);
					return;
				}
				activeGraph.value.updateOutputMetadata(o);
			}
		}
	}

	function cutSelected(inputs: boolean) {
		if (inputs) {
			copySelectedInputs();
			for (const i of copiedInputs.value) {
				if (activeGraph.value) {
					activeGraph.value.removeInputMetadata(i.name);
				}
			}
		} else {
			copySelectedOutputs();
			for (const o of copiedOutputs.value) {
				if (activeGraph.value) {
					activeGraph.value.removeOutputMetadata(o.name);
				}
			}
		}
	}

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Copy all Inputs',
			description: 'Adds all Graph Inputs on this graph to the clipboard',
			callback: async () => {
				if (activeGraph.value) {
					metadataStore.storeCopiedInputs(activeGraph.value.inputMetadata);
				}
			}
		});

		entries.push({
			label: 'Copy all Outputs',
			description: 'Adds all Graph Outputs on this graph to the clipboard',
			callback: async () => {
				if (activeGraph.value) {
					metadataStore.storeCopiedOutputs(activeGraph.value.outputMetadata);
				}
			},
			divider: true
		});

		if (selectedInputs.value.length && activeGraph.value && graphWithSelectedInputs.value == activeTabId.value) {
			entries.push({
				label: 'Copy Selected Inputs',
				description: 'Adds all selected Graph Inputs to the clipboard',
				callback: async () => {
					copySelectedInputs();
				}
			});
		}

		if (selectedOutputs.value.length && activeGraph.value && graphWithSelectedOutputs.value == activeTabId.value) {
			entries.push({
				label: 'Copy Selected Outputs',
				description: 'Adds all selected Graph Outputs to the clipboard',
				callback: async () => {
					copySelectedOutputs();
				}
			});
		}

		if (anyInputCopied.value) {
			entries.push({
				label: copiedInputs.value.length > 1 ? 'Paste Inputs' : 'Paste Input',
				description: copiedInputs.value.length > 1 ? `Paste all copied inputs` : `Paste copied input`,
				callback: async () => {
					pasteSelectedInputs();
				}
			});
		}
		if (anyOutputCopied.value) {
			entries.push({
				label: copiedOutputs.value.length > 1 ? 'Paste Outputs' : 'Paste Output',
				description: copiedOutputs.value.length > 1 ? `Paste all copied graph outputs` : `Paste copied graph output`,
				callback: async () => {
					pasteSelectedOutputs();
				},
				divider: true
			});
		}

		if (selectedInputs.value.length && activeGraph.value && graphWithSelectedInputs.value == activeTabId.value) {
			entries.push({
				label: 'Cut Selected Inputs',
				description: 'Copies and deletes all selected Graph Inputs',
				callback: async () => {
					cutSelected(true);
				}
			});
		}

		if (selectedOutputs.value.length && activeGraph.value && graphWithSelectedOutputs.value == activeTabId.value) {
			entries.push({
				label: 'Cut Selected Outputs',
				description: 'Copies and deletes all selected Graph Outputs',
				callback: async () => {
					cutSelected(false);
				}
			});
		}

		return { items: entries };
	}

	/**
	 * From an input, find its group tab and open it
	 * @param metadata
	 */
	function openGroupTabFromInput(metadata: GraphInputMetadata) {
		const expectedCategory = !metadata.category ? 'Default' : String(metadata.category);

		// Need to do this if new categories are created
		nextTick(() => {
			if (groupTabs.value) {
				const tab = groupTabs.value.find((item) => item.category() === expectedCategory);

				if (tab) {
					tab.openTab();
				}
			}
		});
	}

	const groupedInputs = computed<GroupedInputs>(() => {
		const categoryMap: GroupedInputs = {};

		if (activeGraph.value && activeGraph.value.inputMetadata) {
			activeGraph.value.inputMetadata.forEach((input) => {
				const category = input.category || '';
				if (!categoryMap[category]) {
					categoryMap[category] = [];
				}
				categoryMap[category].push(input);
			});
		}

		return categoryMap;
	});
	
	onMounted(async () => {
		if (iopanel.value) {
			contextmenuStore.getContextMenu('root').addHook(iopanel.value.panel, openContextMenu, false);
		}
	});
</script>

<style scoped>
	.graph-io-panel-container {
		padding: 0px 10px;
		display: flex;
		flex-direction: column;
	}

	.graph-io-panel-header {
		width: 100%;
		margin-bottom: 8px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
	}

	.graph-io-panel-title {
		color: var(--color-primary);
		letter-spacing: 1px;
		cursor: help;
	}

	.add-icon {
		padding: 1px;
		font-size: 1rem;
		color: var(--color-text-secondary);
		cursor: pointer;
		border-radius: 4px;
	}

	.add-icon:hover {
		background-color: var(--color-foreground-secondary);
	}

	.button {
		padding: 1px;
		font-size: 1rem;
		color: var(--color-text-secondary);
		cursor: pointer;
		border-radius: 4px;
	}

	.button:hover {
		background-color: var(--color-foreground-secondary);
	}

	.graph-io-empty-text {
		width: 100%;
		padding: 8px 0px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.9rem;
		color: var(--color-text-secondary);
		font-style: italic;
		opacity: 0.7;
	}

	.graph-io-section-footer {
		margin-top: 8px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
	}

	.graph-io-add-button {
		font-size: 0.9rem;
		color: var(--color-text-secondary);
		letter-spacing: 1px;
		transition: all 50ms linear;
		cursor: pointer;
	}

	.graph-io-add-button:hover {
		color: var(--color-primary);
	}

	.description-input {
		padding: 6px;
		resize: none;
		color: var(--color-text);
		background-color: var(--color-component-sidebar-searchbar);
		border: 1px solid var(--color-component-sidebar-searchbar-border);
		border-radius: 4px;
	}
</style>
