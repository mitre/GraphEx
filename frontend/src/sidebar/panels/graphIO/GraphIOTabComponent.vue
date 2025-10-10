<template>
	<div
		class="graph-io-tab"
		title="Click to open configuration."
		@click.stop.prevent="onMouseDown"
		ref="tab"
		draggable="true"
		@dragstart="onDragStart"
		@dragend="dropNodeOnGraph"
		@dragover="onDragOver"
		:style="selectedStyle"
	>
		<div class="graph-io-left-border" :style="borderStyles"></div>
		<div class="graph-io-tab-body">
			<span class="graph-tab-body-main">
				<span class="graph-tab-unused-icon material-icons" v-if="!isUsed" title="Unused">priority_high</span>
				<span class="graph-io-tab-name no-select">{{ target.name }}</span>
			</span>

			<DropdownComponent ref="dropdown">
				<div class="graph-io-more-icon material-icons">more_vert</div>

				<template v-slot:dropdown>
					<MenuComponent v-bind="menu" />
				</template>
			</DropdownComponent>
		</div>
	</div>

	<GraphIOConfigureInputModal
		v-if="props.input && settingsOpen"
		:graph="props.graph"
		:metadata="props.input"
		@save="saveInput"
		@close="settingsOpen = false"
	/>

	<GraphIOConfigureOutputModal
		v-if="props.output && settingsOpen"
		:graph="props.graph"
		:metadata="props.output"
		@save="saveOutput"
		@close="settingsOpen = false"
	/>
</template>

<script setup lang="ts">
	import type { Graph, GraphInputMetadata, GraphOutputMetadata } from '@/graph';
import { useContextmenuStore, useEditorStore, useErrorStore, useMetadataStore } from '@/stores';
import { computed, nextTick, onMounted, ref, watch, type ComputedRef } from 'vue';

	import DropdownComponent from '@/components/DropdownComponent.vue';
import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import MenuComponent from '@/components/MenuComponent.vue';
import GraphIOConfigureInputModal from '@/sidebar/panels/graphIO/GraphIOConfigureInputModal.vue';
import GraphIOConfigureOutputModal from '@/sidebar/panels/graphIO/GraphIOConfigureOutputModal.vue';

	const props = defineProps<{
		graph: Graph;
		selected: boolean;
		anySelected: boolean;
		anyCopied: boolean;
		input?: GraphInputMetadata;
		output?: GraphOutputMetadata;
	}>();

	const emit = defineEmits<{
		(e: 'addNewInput', template: GraphInputMetadata): void;
		(e: 'addNewOutput', template: GraphOutputMetadata): void;
		(e: 'selected'): void;
		(e: 'cancelSelection'): void;
		(e: 'copySelected'): void;
		(e: 'pasteClipboard'): void;
		(e: 'cutSelected'): void;
	}>();

	const metadataStore = useMetadataStore();
	const contextmenuStore = useContextmenuStore();
	const errorStore = useErrorStore();
	const editorStore = useEditorStore();
	const settingsOpen = ref(false);
	const tab = ref<HTMLDivElement>();
	const dropdown = ref<InstanceType<typeof DropdownComponent>>();

	function saveInput(metadata: GraphInputMetadata) {
		props.graph.updateInputMetadata(metadata, props.input!.name);
	}

	function saveOutput(metadata: GraphOutputMetadata) {
		props.graph.updateOutputMetadata(metadata, props.output!.name);
	}

	function onDragStart(ev: DragEvent) {
		if (props.input) {
			const formatAsData = 'graphinput_' + props.input.name;
			ev.dataTransfer?.setData(formatAsData, props.input.name);
		} else if (props.output) {
			const formatAsData = 'graphoutput_' + props.output.name;
			ev.dataTransfer?.setData(formatAsData, props.output.name);
		}
	}

	function onDragOver(ev: DragEvent) {
		if (props.input && ev.dataTransfer && ev.dataTransfer.types) {
			const formatAsData = ev.dataTransfer.types[0];
			const otherName = formatAsData.split('_')[1];
			const otherIndex = props.graph.inputMetadata.findIndex((x) => x.name.toLowerCase() == otherName);
			const thisIndex = props.graph.inputMetadata.findIndex((x) => x == props.input);
			if (otherIndex == -1 || thisIndex == -1 || thisIndex == otherIndex) {
				return;
			}

			const thisCategory = props.input.category;

			const otherCategory = props.graph.inputMetadata[otherIndex].category;

			if (otherCategory === thisCategory) {
				props.graph.reorderInputMetadata(otherIndex, thisIndex);
			}
			return;
		}

		if (props.output && ev.dataTransfer) {
			const formatAsData = ev.dataTransfer.types[0];
			const otherName = formatAsData.split('_')[1];
			const otherIndex = props.graph.outputMetadata.findIndex((x) => x.name.toLowerCase() == otherName);
			const thisIndex = props.graph.outputMetadata.findIndex((x) => x == props.output);
			if (otherIndex == -1 || thisIndex == -1 || thisIndex == otherIndex) {
				return;
			}

			props.graph.reorderOutputMetadata(otherIndex, thisIndex);
			return;
		}
	}

	const dropNodeOnGraph = (event: DragEvent) => {
		// Prevents nodes from dropping on the graph when we drag to reorder
		if (event.dataTransfer?.dropEffect === 'move') {
			const contentPositions = props.graph.ui.contentPositions();
			const backdropPositions = props.graph.ui.backdropPositions();
			const x =
				(event.clientX - backdropPositions.left - (contentPositions.left - backdropPositions.left)) /
				props.graph.ui.scale;
			const y =
				(event.clientY - backdropPositions.top - (contentPositions.top - backdropPositions.top)) / props.graph.ui.scale;

			if (props.input) {
				const nodeMetadata = metadataStore.getNode('Get Graph Input');
				const addedNode = props.graph.addNode(nodeMetadata, x, y, { fieldValue: props.input.name });
				nextTick(() => addedNode.centerPosition());
				addedNode.requestRefreshMetadata(0, true);
				return;
			}

			if (props.output) {
				const nodeMetadata = metadataStore.getNode('Set Graph Output');
				const addedNode = props.graph.addNode(nodeMetadata, x, y, { fieldValue: props.output.name });
				nextTick(() => addedNode.centerPosition());
				addedNode.requestRefreshMetadata(0, true);
				return;
			}
		}
	};

	const target: ComputedRef<GraphInputMetadata | GraphOutputMetadata> = computed(() => {
		return props.input ? props.input : props.output!;
	});

	const menu: ComputedRef<MenuOptions> = computed(() => {
		const items: MenuItem[] = [];
		const inputIndex = props.graph.inputMetadata.findIndex((x) => x == props.input);
		const outputIndex = props.graph.outputMetadata.findIndex((x) => x == props.output);

		if (!props.anySelected) {
			items.push(
				...[
					{
						label: 'Edit',
						icon: 'edit',
						description: 'Edit this entry.',
						callback: () => {
							dropdown.value?.close();
							settingsOpen.value = true;
						}
					},
					{
						label: 'Add Node',
						icon: 'add',
						description: 'Add the relevant node to the graph.',
						callback: () => {
							dropdown.value?.close();

							const ui = props.graph.ui;
							const viewportPositions = ui.viewportPositions();
							const width = viewportPositions.right - viewportPositions.left;
							const height = viewportPositions.bottom - viewportPositions.top;

							const x = -1 * ui.offsets.x + width / 2;
							const y = -1 * ui.offsets.y + height / 2;

							if (props.input) {
								const nodeMetadata = metadataStore.getNode('Get Graph Input');
								const addedNode = props.graph.addNode(nodeMetadata, x, y, { fieldValue: props.input.name });
								nextTick(() => addedNode.centerPosition());
								addedNode.requestRefreshMetadata(0, true);
								return;
							}

							if (props.output) {
								const nodeMetadata = metadataStore.getNode('Set Graph Output');
								const addedNode = props.graph.addNode(nodeMetadata, x, y, { fieldValue: props.output.name });
								nextTick(() => addedNode.centerPosition());
								addedNode.requestRefreshMetadata(0, true);
								return;
							}
						}
					},
					{
						label: 'Duplicate',
						icon: 'content_copy',
						description: 'Create a new copy of this entry (on this graph).',
						callback: () => {
							dropdown.value?.close();
							if (props.input) {
								emit('addNewInput', JSON.parse(JSON.stringify(props.input)));
							} else if (props.output) {
								emit('addNewOutput', JSON.parse(JSON.stringify(props.output)));
							}
						}
					},
					{
						label: 'Copy',
						icon: 'file_copy',
						description: 'Copy this entry to the clipboard.',
						callback: () => {
							dropdown.value?.close();
							if (props.input) {
								metadataStore.storeCopiedInputs([props.input]);
							} else if (props.output) {
								metadataStore.storeCopiedOutputs([props.output]);
							}
						}
					},
					{
						label: 'Delete',
						icon: 'delete_outline',
						description: 'Delete this entry.',
						divider: true,
						callback: () => {
							dropdown.value?.close();
							if (props.input) {
								props.graph.removeInputMetadata(props.input.name);
							} else if (props.output) {
								props.graph.removeOutputMetadata(props.output.name);
							}
							if (editorStore.activeGraphTab)
								errorStore.removeGraphInputWarning(editorStore.activeGraphTab.id, target.value.name);
							emit('cancelSelection');
						}
					},
					{
						label: 'Select',
						icon: 'highlight_alt',
						description: 'Select this entry (Shift+Click).',
						divider: true,
						callback: () => {
							dropdown.value?.close();
							emit('selected');
						}
					},
					{
						label: 'Move Up',
						icon: 'arrow_upward',
						description: 'Reorder this entry upward.',
						disabled: !(inputIndex > 0 || outputIndex > 0),
						callback: () => {
							dropdown.value?.close();
							if (inputIndex > 0) {
								props.graph.reorderInputMetadata(inputIndex, inputIndex - 1);
							} else if (outputIndex > 0) {
								props.graph.reorderOutputMetadata(outputIndex, outputIndex - 1);
							}
						}
					},
					{
						label: 'Move Down',
						icon: 'arrow_downward',
						description: 'Reorder this entry downward.',
						disabled:
							inputIndex != -1
								? inputIndex == props.graph.inputMetadata.length - 1
								: outputIndex == props.graph.outputMetadata.length - 1,
						callback: () => {
							dropdown.value?.close();
							if (inputIndex != -1 && inputIndex != props.graph.inputMetadata.length - 1) {
								props.graph.reorderInputMetadata(inputIndex, inputIndex + 1);
							} else if (outputIndex != -1 && outputIndex != props.graph.outputMetadata.length - 1) {
								props.graph.reorderOutputMetadata(outputIndex, outputIndex + 1);
							}
						},
						divider: true
					}
				]
			);
		}

		if (props.anySelected) {
			items.push({
				label: props.input ? 'Copy Selected Inputs' : 'Copy Selected Outputs',
				description: props.input
					? 'Adds all selected Graph Inputs to the clipboard'
					: 'Adds all selected Graph Outputs to the clipboard',
				callback: async () => {
					emit('copySelected');
				},
				divider: true
			});

			items.push({
				label: props.input ? 'Cut Selected Inputs' : 'Cut Selected Outputs',
				description: props.input
					? 'Copies and deletes all selected Graph Inputs'
					: 'Copies and deletes all selected Graph Outputs',
				callback: async () => {
					// should also copy all selected before it deletes them
					emit('cutSelected');
				},
				divider: true
			});
		}

		if (props.anyCopied) {
			items.push({
				label: props.input ? 'Paste Inputs' : 'Paste Outputs',
				description: props.input
					? 'Paste all copied (or deleted) graph inputs'
					: 'Paste all copied (or deleted) graph outputs',
				callback: async () => {
					emit('pasteClipboard');
				},
				divider: true
			});
		}

		return { items: items };
	});

	function openContextMenu(): MenuOptions | null {
		return menu.value;
	}

	function propsIsUsed() {
		if (props.input) {
			return props.graph.inputIsUsed(props.input);
		} else if (props.output) {
			return props.graph.outputIsUsed(props.output);
		}
		return false;
	}

	/** Whether this input/output is actually used within the graph. */
	const isUsed = computed(() => {
		if (props.input) {
			return props.graph.inputIsUsed(props.input);
		} else if (props.output) {
			return props.graph.outputIsUsed(props.output);
		}
		return false;
	});

	const datatype = computed(() => {
		return metadataStore.getDataType(target.value.datatype);
	});

	const borderStyles = computed(() => {
		return {
			background: datatype.value.color
		};
	});

	function onMouseDown(event: MouseEvent) {
		if (event.button != 0) {
			return;
		}

		if (event.shiftKey) {
			emit('selected');
		} else {
			settingsOpen.value = true;
		}
	}

	const selectedStyle = computed(() => {
		if (props.selected) {
			return {
				outline: '1px dashed var(--color-editor-node-selected)'
			};
		}
		return {
			outline: 'none'
		};
	});

	watch(
		settingsOpen,
		() => {
			
			if (editorStore.activeGraphTab) {
				if (settingsOpen.value === true)
					// just opened with current name
					errorStore.removeGraphInputWarning(editorStore.activeGraphTab.id, target.value.name);
				else {
					// just closed, name could be different
					nextTick(() => {
						if (!propsIsUsed()) {
							errorStore.addGraphInputWarning(editorStore.activeGraphTab!.id, target.value.name);
						}
					})
				}
			}
		},
		{ immediate: true }
	);

	watch(
		isUsed,
		() => {
			if (editorStore.activeGraphTab) {
				if (isUsed.value == true) {
					errorStore.removeGraphInputWarning(editorStore.activeGraphTab.id, target.value.name);
				} else {
					errorStore.addGraphInputWarning(editorStore.activeGraphTab.id, target.value.name);
				}
			}
		},
		{ immediate: true }
	);

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(tab.value!, openContextMenu, true);
		// We need to account for graphs that have not been created with this in mind
		//props.graph.orderInputMetadataByCategory()
	});
</script>

<style scoped>
	.graph-io-tab {
		width: 100%;
		margin-top: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		background-color: var(--color-background-primary);
		cursor: pointer;
	}

	.graph-io-left-border {
		width: 6px;
		height: 100%;
		opacity: 0.3;
		transition: opacity 50ms linear;
	}

	.graph-io-tab:hover .graph-io-left-border {
		opacity: 1;
	}

	.graph-io-tab-body {
		flex: 1 0;
		padding: 8px 8px 8px 0px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		overflow: hidden;
	}

	.graph-tab-body-main {
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
	}

	.graph-tab-unused-icon {
		font-size: 1rem;
		color: var(--color-warning);
		opacity: 0.7;
		margin-left: 2px;
		margin-right: 2px;
		animation: fade 2s linear infinite;
		cursor: help;
	}

	@keyframes fade {
		0%,
		100% {
			opacity: 0.25;
		}
		50% {
			opacity: 1;
		}
	}

	.graph-io-tab-name {
		font-size: 1rem;
		color: var(--color-text);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.graph-io-tab-name:first-child {
		margin-left: 8px;
	}

	.graph-io-more-icon {
		font-size: 1.2rem;
		color: var(--color-text);
		opacity: 0;
		border-radius: 2px;
	}

	.graph-io-tab:hover .graph-io-more-icon:not(:hover) {
		opacity: 0.6;
	}

	.graph-io-more-icon:hover {
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
