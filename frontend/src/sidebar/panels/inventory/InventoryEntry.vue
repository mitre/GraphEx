<template>
	<div
		class="inv-entry-tab"
		:title="dynamicTitle"
		@click.stop.prevent="toggleOpen"
		:style="dynamicStyle"
		ref="entryEle"
		:draggable="dynamicIsDraggable"
		@dragstart="onDragStart"
		@dragend="dropNodeOnGraph"
	>
		<div class="inv-entry-tab-body">
			<span class="inv-entry-tab-body-main">
				<template v-if="hasChildren">
					<div v-if="childrenOpen" class="group-input-left-expand-icon material-icons">expand_more</div>
					<div v-else class="group-input-left-expand-icon material-icons">chevron_right</div>
				</template>
				
				<span class="inv-entry-tab-name no-select">{{ entryName }}</span>
				<!-- <div v-if="nodeMetadata" class="data-object-icon material-icons">data_object</div> -->
			</span>

			<DropdownComponent ref="dropdown">
				<template v-slot:dropdown>
					<MenuComponent v-bind="menu" />
				</template>
			</DropdownComponent>
		</div>
	</div>
	<div class="inv-children" v-if="hasChildren && childrenOpen">
		<InventoryDataItem v-for="(k, i) in listOfPrimitiveDataContentKeys" :key="i" ref="invItems"
			:keyName="k"
			:value="primitiveDataContent[k]"
			:depth="1"
			:hierarchy="entryName"
			:fileKey="props.fileKey"
		/>
	</div>
</template>

<script setup lang="ts">
import DropdownComponent from '@/components/DropdownComponent.vue';
import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import MenuComponent from '@/components/MenuComponent.vue';
import type { NodeMetadata } from '@/graph';
import { useContextmenuStore, useEditorStore } from '@/stores';
import { computed, type ComputedRef, nextTick, onMounted, ref } from 'vue';
import InventoryDataItem from './InventoryDataItem.vue';

	const props = defineProps<{
		entryInfo: Record<string, any>;
		fileKey: string;
	}>();

	const dropdown = ref<InstanceType<typeof DropdownComponent>>();
	const entryEle = ref<HTMLDivElement>();
	const contextmenuStore = useContextmenuStore();
	const editorStore = useEditorStore();

	const childrenOpen = ref(false);

	const invItems = ref<(typeof InventoryDataItem)[]>();

	const entryName = computed(() => {
		return props.entryInfo.entry_name
	});

	const nodeMetadata = computed(() => {
		if (Object.keys(props.entryInfo.node).length === 0)
			return null;
		return props.entryInfo.node as NodeMetadata
	});

	const nodeInputs = computed(() => {
		return props.entryInfo.node_inputs as Record<string, any>
	});

	const primitiveDataContent = computed(() => {
		return props.entryInfo.content as Record<string, any>
	});

	const dynamicStyle = computed(() => {
		if (nodeMetadata.value != null) {
			return {
				"border": "1px solid var(--color-text)",
				"background-color": "var(--color-background-primary)"
			}
		}
		return {}
	});

	const dynamicTitle = computed(() => {
		if (!hasChildren.value) {
			return "Drag to create this object in the editor panel.";
		}
		if (nodeMetadata.value != null) {
			return "Drag to create this object in the editor panel. Left-click to expand more data related to this inventory entry.";
		}
		return "Left-click to expand data in this inventory entry.";
	});

	const dynamicIsDraggable = computed(() => {
		if (nodeMetadata.value) return "true";
		return "false";
	});

	const listOfPrimitiveDataContentKeys = computed(() => {
		const ks: string[] = [];
		for (const k in primitiveDataContent.value) {
			ks.push(k);
		}
		ks.sort();
		return ks;
	});

	const hasChildren = computed(() => {
		return listOfPrimitiveDataContentKeys.value.length > 0;
	});

	const menu: ComputedRef<MenuOptions> = computed(() => {
		const items: MenuItem[] = [];

		if (hasChildren.value) {
			items.push({
				label: 'Toggle Expand',
				icon: 'unfold_more',
				description: 'Show/Hide the data associated with this inventory item.',
				callback: () => {
					toggleOpen();
				}
			});
		}

		if (nodeMetadata.value != null) {
			items.push({
				label: 'Add Node',
				icon: 'add',
				description: `Add a '${nodeMetadata.value.name}' node to retrieve this object.`,
				callback: () => {
					addNode();
				}
			});
		}

		return { items: items };
	});

	const ui = computed(() => {
		return editorStore.activeGraphTab!.contents.ui;
	});

	const activeGraph = computed(() => {
		return editorStore.activeGraphTab!.contents;
	});

	function addNode(x_coor?: number, y_coor?: number) {
		if (nodeMetadata.value == null) return;

		const viewportPositions = ui.value.viewportPositions();
		const width = viewportPositions.right - viewportPositions.left;
		const height = viewportPositions.bottom - viewportPositions.top;

		let x = -1 * ui.value.offsets.x + width / 2;
		let y = -1 * ui.value.offsets.y + height / 2;

		if (x_coor) x = x_coor;
		if (y_coor) y = y_coor;

		ui.value.deselectAllNodes();

		const addedNode = activeGraph.value.addNode(nodeMetadata.value, x, y);
		for (const socket of addedNode.inputSockets) {
			if (socket.metadata.name in nodeInputs.value) {
				socket.fieldValue = nodeInputs.value[socket.metadata.name];
			}
		}
		
		nextTick(() => addedNode.centerPosition());
		addedNode.requestRefreshMetadata(0, true);
	}

	function toggleOpen() {
		childrenOpen.value = !childrenOpen.value;
	}

	function openContextMenu(): MenuOptions | null {
		return menu.value;
	}

	const dropNodeOnGraph = (event: DragEvent) => {
		const contentPositions = ui.value.contentPositions();
		const backdropPositions = ui.value.backdropPositions();
		const x =
			(event.clientX - backdropPositions.left - (contentPositions.left - backdropPositions.left)) /
			ui.value.scale;
		const y =
			(event.clientY - backdropPositions.top - (contentPositions.top - backdropPositions.top)) / ui.value.scale;
		addNode(x, y);
	};

	function fold() {
		childrenOpen.value = false;
		nextTick(() => {
			if (invItems.value) {
				invItems.value.forEach((t) => {
					t.fold();
				});
			}
		});
	}

	function unfold() {
		childrenOpen.value = true;
		nextTick(() => {
			if (invItems.value) {
				invItems.value.forEach((t) => {
					t.unfold();
				});
			}
		});
	}

	/**
	 * Firefox requires this data be set in order for the drop event to fire.
	 * We don't actually use the transfer data, we just want the 'dragend' event to fire
	 * @param ev the drag event
	 */
	function onDragStart(ev: DragEvent) {
		ev.dataTransfer?.setData("text/plain", "This item may be dragged");
	}

	defineExpose({
		fold,
		unfold
	});

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(entryEle.value!, openContextMenu, true);
	});
</script>

<style scoped>
	.inv-entry-tab {
		width: 100%;
		margin-top: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		cursor: pointer;
		opacity: 0.8;
	}
	
	.inv-entry-tab:hover {
		opacity: 1;
	}

	.inv-entry-tab-body {
		padding: 0.5rem;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		overflow: hidden;
	}

	.inv-entry-tab-body-main {
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
	}

	.inv-entry-tab-name {
		font-size: 1rem;
		color: var(--color-text);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.inv-entry-tab-name:first-child {
		margin-left: 8px;
	}

	.inv-entry-more-icon {
		font-size: 1.2rem;
		color: var(--color-text);
		opacity: 0;
		border-radius: 2px;
	}

	.inv-entry-tab:hover .inv-entry-more-icon:not(:hover) {
		opacity: 0.6;
	}

	.inv-entry-more-icon:hover {
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

	.data-object-icon {
		padding-left: 10px;
	}
</style>
