<template>
	<div class="variable-tab" :title="dynamicTitle" @click.stop.prevent="onClick" ref="tab" :style="errorStyle">
		<div v-if="childrenOpen" class="variable-left-expand-icon material-icons" :style="expandStyles">expand_more</div>
		<div v-else="childrenOpen" class="variable-left-expand-icon material-icons" :style="expandStyles">chevron_right</div>
		<div class="variable-tab-body">
			<span class="variable-tab-name no-select" :style="nameStyle">{{ variableName }}</span>

			<DropdownComponent ref="dropdown">
				<div class="variable-more-icon material-icons">more_vert</div>

				<template v-slot:dropdown>
					<MenuComponent v-bind="menu" />
				</template>
			</DropdownComponent>
		</div>
	</div>
	<div v-if="childrenOpen">
		<VariableChildTab v-for="(info, index) in props.variableInfo" :key="index" :variable-info="info" />
	</div>
</template>

<script setup lang="ts">
	import type { Graph } from '@/graph';
import { useContextmenuStore, useMetadataStore } from '@/stores';
import { computed, nextTick, onMounted, ref, type ComputedRef } from 'vue';

	import DropdownComponent from '@/components/DropdownComponent.vue';
import type { MenuOptions } from '@/components/MenuComponent.vue';
import MenuComponent from '@/components/MenuComponent.vue';

	import VariableChildTab from '@/sidebar/panels/variable/VariableChildTab.vue';
import type { VariableInformation } from './VariablePanel.vue';

	const props = defineProps<{
		graph: Graph;
		variableInfo: Array<VariableInformation>;
		variableNameWithDatatype: string;
	}>();

	const contextmenuStore = useContextmenuStore();
	const metadataStore = useMetadataStore();
	const childrenOpen = ref(false);
	const tab = ref<HTMLDivElement>();
	const dropdown = ref<InstanceType<typeof DropdownComponent>>();

	const menu: ComputedRef<MenuOptions> = computed(() => {
		const items = {
			items: [
				{
					label: 'Add: "Get Variable" Node',
					icon: 'add',
					description: "Add a 'Getter' for this variable.",
					callback: () => {
						addNode('Get Variable');
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				}
			]
		};
		if (props.variableInfo[0].isList) {
			items.items.push({
				label: 'Add: "Set List Variable" Node',
				icon: 'add',
				description: "Add a list 'Setter' node for this variable.",
				callback: () => {
					if (firstInfo.value.datatype === 'String') {
						addNode('Set List Variable (String)');
					} else if (firstInfo.value.datatype === 'Number') {
						addNode('Set List Variable (Number)');
					} else if (firstInfo.value.datatype === 'Boolean') {
						addNode('Set List Variable (Boolean)');
					} else {
						addNode('Set List Variable')
					}
					if (dropdown.value) {
						dropdown.value.close();
					}
				}
			});
			items.items.push({
				label: 'Add: "Append to List Variable" Node',
				icon: 'add',
				description: 'Add an append node for this variable.',
				callback: () => {
					if (firstInfo.value.datatype === 'String') {
						addNode('Append To List Variable (String)');
					} else if (firstInfo.value.datatype === 'Number') {
						addNode('Append To List Variable (Number)');
					} else if (firstInfo.value.datatype === 'Boolean') {
						addNode('Append To List Variable (Boolean)');
					} else {
						addNode('Append To List Variable');
					}
					if (dropdown.value) {
						dropdown.value.close();
					}
				}
			});
		} else {
			items.items.push({
					label: 'Add: "Set Variable" Node',
					icon: 'add',
					description: "Add a 'Setter' for this variable.",
					callback: () => {
						if (firstInfo.value.datatype === 'String') {
							addNode('Set Variable (String)');
						} else if (firstInfo.value.datatype === 'Number') {
							addNode('Set Variable (Number)');
						} else if (firstInfo.value.datatype === 'Boolean') {
							addNode('Set Variable (Boolean)');
						} else {
							addNode('Set Variable');
						}
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				});
		}
		return items;
	});

	const firstNode = computed(() => {
		return firstInfo.value.node;
	});
	
	const firstInfo = computed(() => {
		return props.variableInfo[0];
	})

	async function addNode(name: string) {
		const graph = props.graph;
		if (!graph) return;

		const pos = metadataStore.getNodeStartPositions(graph.ui);

		const nMetadata = metadataStore.getNode(name);
		const addedNode = graph.addNode(nMetadata, pos.x, pos.y, { fieldValue: variableName.value });
		await nextTick();
		addedNode.centerPosition();
		await addedNode.requestRefreshMetadata(0, true);
	}

	function openContextMenu(): MenuOptions | null {
		return menu.value;
	}

	const expandStyles = computed(() => {
		return {
			color: varNameColor.value
		};
	});

	const hasSetters = computed(() => {
		return props.variableInfo.find((e) =>
			e.origin == "SET" || e.origin == "CHECKBOX"
		);
	});

	const missingDatype = computed(() => {
		if (firstInfo.value) {
			return firstInfo.value.datatype.toLowerCase() == 'dynamic';
		}
		return false;
	});

	const duplicateVariableName = computed(() => {
		if (firstInfo.value) {
			return firstInfo.value.duplicateVariableName;
		}
		return false;
	});

	const varNameColor = computed(() => {
		if (firstInfo.value && firstInfo.value.datatype) {
			return metadataStore.getDataType(firstInfo.value.datatype).color;
		}
		for (const e of props.variableInfo) {
			if (e.origin == "SET" || e.origin == "CHECKBOX") {
				return e.node.metadata.color;
			}
		}
		return firstNode.value.metadata.color;
	});

	const nameStyle = computed(() => {
		let style: any = {};
		style['color'] = varNameColor.value;
		return style;
	});

	const errorStyle = computed(() => {
		let style: any = {};
		if (!hasSetters.value || missingDatype.value || duplicateVariableName.value) {
			style['border'] = '1px solid var(--color-component-sidebar-variables-no-setter)'
		}
		return style;
	});

	const dynamicTitle = computed(() => {
		if (!hasSetters.value) {
			return 'This variable has no setter nodes in this graph. The graph will fail to get this variable.';
		}

		if (missingDatype.value) {
			return "This variable is missing data assignment. Connect the data that you want to save to the 'Value To Save' socket";
		}

		if (duplicateVariableName.value) {
			return "There is already another variable with this name in your graph. You will be unable to use the 'Get Variable' node to retrieve this value."
		}

		let shownText = "Left-click to toggle showing all places where the variable: '" + variableName.value + "' is referenced. ";

		if (firstInfo.value) {
			if (firstInfo.value.datatype) {
				if (firstInfo.value.datatype !== 'Dynamic') shownText += "This variable is has the datatype: '" + firstInfo.value.datatype + "'. ";
			} 
			if (firstInfo.value.isList) shownText += "This variable is a reference to a list of values.";
		}

		return shownText;
	});

	const variableName = computed(() => {
		const varNameWithDatatype = props.variableNameWithDatatype;
		return varNameWithDatatype.substring(0, varNameWithDatatype.lastIndexOf(firstInfo.value.datatype))
	});

	function onClick() {
		childrenOpen.value = !childrenOpen.value;
	}

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(tab.value!, openContextMenu, true);
	});

	function closeTab() {
		childrenOpen.value = false;
	}

	function openTab() {
		childrenOpen.value = true;
	}

	defineExpose({
		openTab,
		closeTab
	});
</script>

<style scoped>
	.variable-tab {
		width: 100%;
		margin-top: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		background-color: var(--color-background-primary);
		cursor: pointer;
		overflow: hidden;
	}

	.variable-left-expand-icon {
		opacity: 0.5;
		transition: opacity 50ms linear;
	}

	.variable-tab:hover .variable-left-expand-icon {
		opacity: 1;
	}

	.variable-tab-body {
		flex: 1 0;
		padding: 8px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		overflow: hidden;
	}

	.variable-tab-name {
		font-size: 1rem;
		color: var(--color-text);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		opacity: 0.8;
	}

	.variable-tab:hover .variable-tab-name {
		opacity: 1;
	}

	.variable-more-icon {
		font-size: 1.2rem;
		color: var(--color-text);
		opacity: 0;
		border-radius: 2px;
	}

	.variable-tab:hover .variable-more-icon:not(:hover) {
		opacity: 0.6;
	}

	.variable-more-icon:hover {
		opacity: 1;
	}

	:deep(.dropdown-target-container) {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	:deep(.scroll-container) {
		width: auto;
		height: auto;
	}

	:deep(.scroll-contents) {
		padding-bottom: 0px;
	}
</style>
