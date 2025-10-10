<template>
	<SidebarPanel header="Variables">
		<template v-slot:buttons>
			<div class="button-bar">
				<span class="material-icons button" title="Fold All" @click="foldAll">unfold_less</span>
				<span class="material-icons button" title="Unfold All" @click="unfoldAll">unfold_more</span>
				<DropdownComponent ref="dropdown">
					<div class="button material-icons">add</div>

					<template v-slot:dropdown>
						<MenuComponent v-bind="menu" />
					</template>
				</DropdownComponent>
			</div>
		</template>
		<div class="variable-panel-container">
			<template v-if="activeGraph && variableNodes.size > 0">
				<template v-for="sortedVariableName in sortedNames" :key="variableName">
					<VariableTabComponent ref="tabs" :graph="activeGraph" :variableInfo="variableNodes.get(sortedVariableName)!" :variableNameWithDatatype="sortedVariableName" />
				</template>
			</template>
			<span v-else class="variable-empty-text no-select">No Variables Found...</span>
		</div>
	</SidebarPanel>
</template>

<script setup lang="ts">
	import type { GraphNode } from '@/graph';
import SidebarPanel from '@/sidebar/SidebarPanel.vue';
import { useEditorStore, useMetadataStore } from '@/stores';
import { computed, nextTick, ref, type ComputedRef } from 'vue';

import DropdownComponent from '@/components/DropdownComponent.vue';
import type { MenuOptions } from '@/components/MenuComponent.vue';
import MenuComponent from '@/components/MenuComponent.vue';
import VariableTabComponent from '@/sidebar/panels/variable/VariableTabComponent.vue';

	export interface VariableInformation {
		/** The node object reference itself */
		node: GraphNode;

		/** How the variable was set or get. Current one of: GET, SET, CHECKBOX, INLINE */
		origin: string;

		/** Whether or not this variable is for a list */
		isList: boolean;

		/** If INLINE, the name of the input socket being assigned to */
		inputSocketName?: string;

		/** The name of the type of the data */
		datatype: string;

		/** Gets set to true if another datatype already has this variable name in the graph somewhere  */
		duplicateVariableName: boolean
	}

	const editorStore = useEditorStore();
	const metadataStore = useMetadataStore();
	const tabs = ref<(typeof VariableTabComponent)[]>();
	const dropdown = ref<InstanceType<typeof DropdownComponent>>();

	const activeGraph = computed(() => (editorStore.activeGraphTab ? editorStore.activeGraphTab.contents : null));

	function foldAll() {
		if (tabs.value) {
			tabs.value.forEach((t) => {
				t.closeTab();
			});
		}
	}

	function unfoldAll() {
		if (tabs.value) {
			tabs.value.forEach((t) => {
				t.openTab();
			});
		}
	}

	function addToMap(tempMap: Map<string, Array<VariableInformation>>, varNameWithDatatype: string, varName: string, infoObjToAdd: VariableInformation) {
		// check if this variable name already exists in our references
		for (const key of tempMap.keys()) {
			const vi = tempMap.get(key)![0];
			if (key != varNameWithDatatype && key.substring(0, key.lastIndexOf(vi.datatype)) == varName ) {
				infoObjToAdd.duplicateVariableName = true;
			}
		}
		if (!tempMap.has(varNameWithDatatype)) {
			tempMap.set(varNameWithDatatype, [infoObjToAdd]);
		} else {
			tempMap.get(varNameWithDatatype)?.push(infoObjToAdd);
		}
		return tempMap;
	}

	const variableNodes = computed(() => {
		const tempMap = new Map<string, Array<VariableInformation>>();
		if (!activeGraph.value) {
			return tempMap;
		}

		for (let node of activeGraph.value.getNodes()) {
			if (
				metadataStore.VARIABLES_NODE_NAMES.includes(node.metadata.name) &&
				node.fieldValue
			) {
				const infoObj = {
					node: node,
					origin: "SET",
					isList: false,
					datatype: 'null',
					duplicateVariableName: false
				}
				if (node.metadata.name.toLowerCase().includes('list')) {
					infoObj.isList = true;
				}
				if (node.inputSockets && node.inputSockets.length > 0)
					infoObj.datatype = String(node.inputSockets[0].metadata.datatype)
				if (node.metadata.name === 'Get Variable') {
					infoObj.origin = "GET";
					if (node.outputSockets && node.outputSockets.length > 0 && node.outputSockets[0].metadata.isList) {
						infoObj.isList = true;
					}
				}
				if (infoObj.datatype === 'null') {
					try {
						infoObj.datatype = metadataStore.getDataTypeByColor(node.metadata.color).name;
					} catch {};
				}
				const varName = String(node.fieldValue) + String(infoObj.datatype);
				// add this variable to all our references
				addToMap(tempMap, varName, String(node.fieldValue), infoObj);
			} else {
				// check for VariableOutputSockets
				node.outputSockets.forEach((outputSocket) => {
					const infoObj = {
						node: node,
						origin: "CHECKBOX",
						isList: false,
						datatype: String(outputSocket.metadata.datatype),
						duplicateVariableName: false
					}
					if (outputSocket.metadata.allowsVariable && !outputSocket.disabledVariableOutput) {
						if (outputSocket.metadata.isList) infoObj.isList = true;
						let varName = outputSocket.metadata.name + String(infoObj.datatype);
						// add this variable to all our references
						addToMap(tempMap, varName, outputSocket.metadata.name, infoObj);
					}
				});
			}
			// check for input sockets using a variable input
			node.inputSockets.forEach((inputSocket) => {
				const infoObj = {
					node: node,
					origin: "INLINE",
					isList: false,
					inputSocketName: "",
					datatype: String(inputSocket.metadata.datatype),
					duplicateVariableName: false
				}
				if (inputSocket.variableName) {
					if (inputSocket.metadata.isList) infoObj.isList = true;
					infoObj.inputSocketName = inputSocket.metadata.name;
					let varName = inputSocket.variableName + String(infoObj.datatype);
					// add this variable to all our references
					addToMap(tempMap, varName, inputSocket.variableName, infoObj);
				}
			});
		}

		return tempMap;
	});

	const sortedNames = computed(() => {
		return Array.from(variableNodes.value.keys()).sort();
	});

	const menu: ComputedRef<MenuOptions> = computed(() => {
		const items = {
			items: [
				{
					label: 'New: "Set Variable" (String)',
					icon: 'add',
					description: "Add a variable setter for String data.",
					callback: () => {
						addNode('Set Variable (String)');
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: 'New: "Set Variable" (Number)',
					icon: 'add',
					description: "Add a variable setter for Number data.",
					callback: () => {
						addNode('Set Variable (Number)');
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: 'New: "Set Variable" (Boolean)',
					icon: 'add',
					description: "Add a variable setter for Boolean data.",
					callback: () => {
						addNode('Set Variable (Boolean)');
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: 'New: "Set Variable" (Dynamic)',
					icon: 'add',
					description: "Add a variable setter for any type of data.",
					callback: () => {
						addNode('Set Variable');
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: 'New: "Set List Variable" (String)',
					icon: 'add',
					description: "Add a list variable setter for String data.",
					callback: () => {
						addNode('Set List Variable (String)')
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: 'New: "Set List Variable" (Number)',
					icon: 'add',
					description: "Add a list variable setter for Number data.",
					callback: () => {
						addNode('Set List Variable (Number)')
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: 'New: "Set List Variable" (Boolean)',
					icon: 'add',
					description: "Add a list variable setter for Boolean data.",
					callback: () => {
						addNode('Set List Variable (Boolean)')
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: 'New: "Set List Variable" (Dynamic)',
					icon: 'add',
					description: "Add a list variable setter for any type of data.",
					callback: () => {
						addNode('Set List Variable')
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				}
			]
		};
		return items;
	});

	async function addNode(name: string) {
		const graph = activeGraph.value;
		if (!graph) return;

		const pos = metadataStore.getNodeStartPositions(graph.ui);

		const nMetadata = metadataStore.getNode(name);
		const addedNode = graph.addNode(nMetadata, pos.x, pos.y);
		await nextTick();
		addedNode.centerPosition();
		await addedNode.requestRefreshMetadata(0, true);
	}
</script>

<style scoped>
	.variable-panel-container {
		padding: 0px 10px;
		display: flex;
		flex-direction: column;
	}

	.button-bar {
		display: flex;
		flex-direction: row;
	}

	.button {
		font-size: 1.1rem;
		opacity: 0.6;
	}

	.button:hover {
		color: var(--color-primary);
		cursor: pointer;
	}

	.variable-empty-text {
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

	:deep(.header-bar) {
		margin-bottom: 0rem;
	}
</style>
