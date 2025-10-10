<template>
	<div
		class="inv-item-tab"
		:title="dynamicTitle"
		@click.stop.prevent="toggleOpen"
		:style="dynamicStyle"
		:draggable="dynamicIsDraggable"
		@dragstart="onDragStart"
		@dragend="dropNodeOnGraph"
		ref="itemEle"
	>
		<div class="inv-item-tab-body">
			<span class="inv-item-tab-body-main">
				<div v-if="childrenOpen" class="group-input-left-expand-icon material-icons">expand_more</div>
				<div v-else class="group-input-left-expand-icon material-icons">chevron_right</div>
				<span class="inv-item-tab-name no-select">{{ props.keyName }}</span>
				<!-- <div v-if="valueIsArrayOfPrimitives" class="list-icon material-icons">list</div> -->
			</span>
			<DropdownComponent ref="dropdown">
				<template v-slot:dropdown>
					<MenuComponent v-bind="menu" />
				</template>
			</DropdownComponent>
		</div>
	</div>
	<div class="inv-subitems" v-if="childrenOpen">
		<div class="primitive-value" v-if="valueIsPrimitive">
			<InventoryDataValue
				:value="props.value"
				:depth="props.depth+1"
				:index="-1"
				:hierarchy="dynamicHierarchyPath"
				:fileKey="fileKey"
			/>
		</div>
		<div class="array-value" v-else-if="valueIsArray">
			<InventoryDataValue v-for="list_item, i of props.value"
				:value="list_item"
				:depth="props.depth+1"
				:index="i"
				:hierarchy="dynamicHierarchyPath + ' -> Index#' + String(i)"
				:arrayParent="true"
				:fileKey="fileKey"
				ref="invArrayItems"
			/>
		</div>
		<div class="object-value" v-else>
			<InventoryDataItem v-for="(v, k, i) of valueAsRecord" :key="i"
				:keyName="k"
				:value="v"
				:depth="props.depth+1"
				:hierarchy="dynamicHierarchyPath"
				:fileKey="fileKey"
				ref="invObjectItems"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import DropdownComponent from '@/components/DropdownComponent.vue';
import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import MenuComponent from '@/components/MenuComponent.vue';
import { useContextmenuStore, useEditorStore, useMetadataStore } from '@/stores';
import { computed, type ComputedRef, nextTick, onMounted, ref } from 'vue';
import InventoryDataItem from './InventoryDataItem.vue';
import InventoryDataValue from './InventoryDataValue.vue';

	const props = defineProps<{
		keyName: string;
		value: any;
		depth: number;
		hierarchy: string;
		arrayParent?: boolean;
		fileKey: string;
	}>();

	const metadataStore = useMetadataStore();
	const editorStore = useEditorStore();
	const contextmenuStore = useContextmenuStore();

	const invArrayItems = ref<(typeof InventoryDataValue)[]>();
	const invObjectItems = ref<(typeof InventoryDataItem)[]>();

	const itemEle = ref<HTMLDivElement>();

	const childrenOpen = ref(false);

	const dynamicHierarchyPath = computed(() => {
		if (props.arrayParent) {
			// The array index should already be tacked on here
			return props.hierarchy;
		}
		return props.hierarchy + ' -> ' + props.keyName;
	});

	const valueIsPrimitive = computed(() => {
		return isPrimitive(props.value);
	});

	const valueIsArray = computed(() => {
		return props.value instanceof Array;
	});

	const valueIsArrayOfPrimitives = computed(() => {
		if (!valueIsArray.value) return false;
		for (const li of props.value) {
			if (!isPrimitive(li)) return false;
		}
		return true;
	});

	const valueDatatype = computed(() => {
		let temp: unknown = null;

		if (valueIsPrimitive.value) {
			temp = props.value;
		} else if (valueIsArrayOfPrimitives.value) {
			temp = props.value[0];
		}
		if (!temp) return null;

		if (typeof temp == "string") {
			return metadataStore.getDataType("String");
		}
		if (typeof temp == "number") {
			return metadataStore.getDataType("Number");
		}
		if (typeof temp == "boolean") {
			return metadataStore.getDataType("Boolean");
		}
		return null;
	});

	const dynamicStyle = computed(() => {
		let s: any = {
			'margin-left': props.depth * 10 + 'px'
		}
		if (valueIsArrayOfPrimitives.value) {
			const borderTextPrefix = "1px solid ";
			if (valueDatatype.value) {
				s["border"] = borderTextPrefix + valueDatatype.value.color;
				s["background-color"] = "var(--color-background-primary)";
			}
		}
		return s;
	});

	const valueAsRecord = computed(() => {
		return props.value as Record<string, any>;
	});

	const dynamicIsDraggable = computed(() => {
		if (valueIsArrayOfPrimitives.value) return "true";
		return "false";
	});

	const ui = computed(() => {
		return editorStore.activeGraphTab!.contents.ui;
	});

	const activeGraph = computed(() => {
		return editorStore.activeGraphTab!.contents;
	});

	const dropNodeOnGraph = (event: DragEvent) => {
		const contentPositions = ui.value.contentPositions();
		const backdropPositions = ui.value.backdropPositions();
		const x =
			(event.clientX - backdropPositions.left - (contentPositions.left - backdropPositions.left)) /
			ui.value.scale;
		const y =
			(event.clientY - backdropPositions.top - (contentPositions.top - backdropPositions.top)) / ui.value.scale;
		addListNode(x, y);
	};

	const inventoryNodeMetadata = computed(() => {
		return metadataStore.getNode(props.fileKey + '$' + dynamicHierarchyPath.value);
	});

	const dynamicTitle = computed(() => {
		if (valueIsArrayOfPrimitives.value != null) {
			return "Drag to create this list in the editor panel. Left-click to expand more data related to this inventory sub-entry."
		}
		return "Left-click to expand data in this inventory sub-entry."
	});

	const menu: ComputedRef<MenuOptions> = computed(() => {
		const items: MenuItem[] = [];

		if (valueIsArrayOfPrimitives.value) {
			items.push({
				label: 'Add List Node',
				icon: 'add',
				description: `Add an inventory node to retrieve this list.`,
				callback: () => {
					addListNode();
				}
			});
		}

		return { items: items };
	});

	function openContextMenu(): MenuOptions | null {
		return menu.value;
	}

	function addListNode(x_coor?: number, y_coor?: number) {
		if (!valueIsArrayOfPrimitives.value) return;

		const viewportPositions = ui.value.viewportPositions();
		const width = viewportPositions.right - viewportPositions.left;
		const height = viewportPositions.bottom - viewportPositions.top;

		let x = -1 * ui.value.offsets.x + width / 2;
		let y = -1 * ui.value.offsets.y + height / 2;

		if (x_coor) x = x_coor;
		if (y_coor) y = y_coor;

		ui.value.deselectAllNodes();

		const addedNode = activeGraph.value.addNode(inventoryNodeMetadata.value, x, y);
		addedNode.fieldValue = props.value;
			
		nextTick(() => addedNode.centerPosition());
		addedNode.requestRefreshMetadata(0, true);
	}

	function toggleOpen() {
		childrenOpen.value = !childrenOpen.value;
	}

	function isPrimitive(v: any) {
		return v !== Object(v);
	}

	function fold() {
		childrenOpen.value = false;
		nextTick(() => {
			if (invArrayItems.value) {
				invArrayItems.value.forEach((t) => {
					t.fold();
				});
			}
			if (invObjectItems.value) {
				invObjectItems.value.forEach((t) => {
					t.fold();
				});
			}
		});
	}

	function unfold() {
		childrenOpen.value = true;
		nextTick(() => {
			if (invArrayItems.value) {
				invArrayItems.value.forEach((t) => {
					t.unfold();
				});
			}
			if (invObjectItems.value) {
				invObjectItems.value.forEach((t) => {
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

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(itemEle.value!, openContextMenu, true);
	});

	defineExpose({
		fold,
		unfold
	});
</script>

<style scoped>
	.inv-item-tab {
		margin-top: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		cursor: pointer;
		opacity: 0.8;
	}
	
	.inv-item-tab:hover {
		opacity: 1;
	}

	.inv-item-tab-body {
		padding: 0.5rem;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		overflow: hidden;
	}

	.inv-item-tab-body-main {
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
	}

	.inv-item-tab-name {
		font-size: 1rem;
		color: var(--color-text);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.inv-item-tab-name:first-child {
		margin-left: 8px;
	}

	.list-icon {
		padding-left: 5px;
	}
</style>
