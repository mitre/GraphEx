<template>
	<div
		class="inv-data-tab"
		:title="dynamicTitle"
		:style="dynamicStyle"
		:draggable="dynamicIsDraggable"
		@dragstart="onDragStart"
		@dragend="dropNodeOnGraph"
		ref="valueEle"
	>
		<div class="primitive-value" v-if="valueIsPrimitive">
			<div class="inv-data-tab-body">
				<span class="inv-data-tab-body-main">
					<span class="inv-data-tab-name no-select">{{ props.value }}</span>
				</span>
			</div>
			<DropdownComponent ref="dropdown">
				<template v-slot:dropdown>
					<MenuComponent v-bind="menu" />
				</template>
			</DropdownComponent>
		</div>
		<div class="array-value" v-else-if="valueIsArray">
			<InventoryDataValue v-for="list_item, i of props.value"
				:value="list_item"
				:depth="props.depth"
				:index="i"
				:hierarchy="props.hierarchy"
				:arrayParent="true"
				:fileKey="fileKey"
				ref="invArrayItems"
			/>
		</div>
		<div class="object-value" v-else>
			<InventoryDataItem
				:keyName="indexName"
				:value="props.value"
				:depth="0"
				:hierarchy="props.hierarchy"
				:arrayParent="passOnArrayParent"
				:fileKey="fileKey"
				ref="invObjectItem"
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
		value: any;
		depth: number;
		index: number;
		hierarchy: string;
		arrayParent?: boolean;
		fileKey: string;
	}>();

	const metadataStore = useMetadataStore();
	const editorStore = useEditorStore();
	const contextmenuStore = useContextmenuStore();

	const invArrayItems = ref<(typeof InventoryDataValue)[]>();
	const invObjectItem = ref<(typeof InventoryDataItem)>();

	const valueEle = ref<HTMLDivElement>();

	const passOnArrayParent =  computed(() => {
		if (props.arrayParent) return true;
		return false;
	});

	const valueIsPrimitive = computed(() => {
		return props.value !== Object(props.value);
	});

	const valueIsString = computed(() => {
		return typeof props.value === "string";
	});

	const valueIsNumber = computed(() => {
		return typeof props.value === "number";
	});

	const valueIsBoolean = computed(() => {
		return typeof props.value === "boolean";
	});

	const valueIsArray = computed(() => {
		return props.value instanceof Array;
	});

	const ui = computed(() => {
		return editorStore.activeGraphTab!.contents.ui;
	});

	const activeGraph = computed(() => {
		return editorStore.activeGraphTab!.contents;
	});

	const dynamicIsDraggable = computed(() => {
		if (valueIsPrimitive.value) return "true";
		return "false";
	});

	const indexName = computed(() => {
		let temp = "Index#" + String(props.index);
		if (!valueIsPrimitive.value && !valueIsArray.value) {
			if ("Name" in props.value) {
				return temp + " (" + props.value["Name"] + ")";
			}
		}
		return temp;
	});

	const dynamicTitle = computed(() => {
		if (valueIsPrimitive.value) return "Drag this item into the graph to use it as data."
		return "Click to show more data about this inventory item."
	});

	const dynamicStyle = computed(() => {
		let s: any = {
			'margin-left': props.depth * 10 + 'px'
		}
		const borderTextPrefix = "1px solid ";
		if (valueIsString.value) {
			s["border"] = borderTextPrefix + metadataStore.getDataType("String").color;
		} else if (valueIsNumber.value) {
			s["border"] = borderTextPrefix + metadataStore.getDataType("Number").color;
		} else if (valueIsBoolean.value) {
			s["border"] = borderTextPrefix + metadataStore.getDataType("Boolean").color;
		}
		return s;
	});

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

	const inventoryNodeMetadata = computed(() => {
		return metadataStore.getNode(props.fileKey + '$' + props.hierarchy);
	});

	const menu: ComputedRef<MenuOptions> = computed(() => {
		const items: MenuItem[] = [];

		if (valueIsPrimitive.value) {
			items.push({
				label: 'Add Node',
				icon: 'add',
				description: `Add an inventory node to retrieve this data.`,
				callback: () => {
					addNode();
				}
			});
		}

		return { items: items };
	});

	function openContextMenu(): MenuOptions | null {
		return menu.value;
	}

	function addNode(x_coor?: number, y_coor?: number) {
		if (!valueIsPrimitive.value) return;

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

	function fold() {
		nextTick(() => {
			if (invArrayItems.value) {
				invArrayItems.value.forEach((t) => {
					t.fold();
				});
			}
			if (invObjectItem.value) {
				invObjectItem.value.fold();
			}
		});
	}

	function unfold() {
		nextTick(() => {
			if (invArrayItems.value) {
				invArrayItems.value.forEach((t) => {
					t.unfold();
				});
			}
			if (invObjectItem.value) {
				invObjectItem.value.unfold();
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
		contextmenuStore.getContextMenu('root').addHook(valueEle.value!, openContextMenu, true);
	});

	defineExpose({
		fold,
		unfold
	});
</script>

<style scoped>
	.inv-data-tab {
		margin-top: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		cursor: pointer;
		opacity: 0.8;
	}
	
	.inv-data-tab:hover {
		opacity: 1;
	}

	.inv-data-tab-body {
		padding: 0.5rem;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		overflow: hidden;
	}

	.inv-data-tab-body-main {
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
	}

	.inv-data-tab-name {
		font-size: 1rem;
		color: var(--color-text);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.primitive-value {
		background-color: var(--color-background-primary);
		width: 100%;
	}
</style>
