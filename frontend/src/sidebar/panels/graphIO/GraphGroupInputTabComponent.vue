<template>
	<div class="group-input-tab" @click.stop.prevent="onClick" ref="tab">
		<div v-if="childrenOpen" class="group-input-left-expand-icon material-icons">expand_more</div>
		<div v-else class="group-input-left-expand-icon material-icons">chevron_right</div>
		<div class="group-input-tab-body">
			<div class="group-input-name">
				<span class="graph-tab-unused-icon material-icons" v-if="unusedMessage" :title="unusedMessage">
					priority_high
				</span>
				<span class="group-input-tab-name no-select">{{ props.category }}</span>
			</div>
			<DropdownComponent ref="dropdown">
				<div class="group-input-more-icon material-icons">more_vert</div>

				<template v-slot:dropdown>
					<MenuComponent v-bind="menu" />
				</template>
			</DropdownComponent>
		</div>
	</div>
	<template v-if="childrenOpen">
		<template v-for="(inputData, index) in props.inputs" :key="index">
			<GraphIOTabComponent
				:graph="props.graph"
				:input="inputData.metadata"
				:selected="inputData.isSelected"
				:any-copied="props.anyCopied"
				:any-selected="props.anySelected"
				@add-new-input="emit('addNewInput', $event)"
				@selected="emit('selected', inputData.metadata)"
				@cancel-selection="emit('cancelSelection', inputData.metadata)"
				@copy-selected="emit('copySelected', inputData.metadata)"
				@paste-clipboard="emit('pasteClipboard', inputData.metadata)"
				@cut-selected="emit('cutSelected')"
			/>
		</template>
	</template>
</template>

<script setup lang="ts">
	import type { Graph, GraphInputMetadata, GraphInputMetadataWithState } from '@/graph';
import { useContextmenuStore, useMetadataStore } from '@/stores';
import { computed, onMounted, ref, type ComputedRef } from 'vue';

	import DropdownComponent from '@/components/DropdownComponent.vue';
import type { MenuOptions } from '@/components/MenuComponent.vue';
import MenuComponent from '@/components/MenuComponent.vue';
import GraphIOTabComponent from '@/sidebar/panels/graphIO/GraphIOTabComponent.vue';

	const props = defineProps<{
		graph: Graph;
		inputs: Array<GraphInputMetadataWithState>;
		anySelected: boolean;
		anyCopied: boolean;
		category: String;
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
					label: `Add: '${props.category}' input `,
					icon: 'add',
					description: `Add a new input with category '${props.category}'.`,
					callback: () => {
						emit('addNewInput', {
							name: 'MyInput',
							datatype: 'String',
							category: props.category === 'Default' ? undefined : String(props.category)
						});

						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				},
				{
					label: `Copy all '${props.category}' inputs `,
					icon: 'file_copy',
					description: `Copy all inputs with category '${props.category}'.`,
					callback: () => {
						metadataStore.storeCopiedInputs(props.inputs.map((input) => JSON.parse(JSON.stringify(input.metadata))));
						if (dropdown.value) {
							dropdown.value.close();
						}
					}
				}
			]
		};

		return items;
	});

	const unusedMessage = computed(() => {
		let numberUnused: number = 0;
		for (const inputData of props.inputs) {
			if (!props.graph.inputIsUsed(inputData.metadata)) {
				numberUnused++;
			}
		}

		if (numberUnused === 0) {
			return undefined;
		}

		return numberUnused === 1
			? `unused graph inputs for category '${props.category}'.`
			: `${numberUnused} unused inputs for category '${props.category}'.`;
	});

	const emit = defineEmits<{
		(e: 'addNewInput', template: GraphInputMetadata): void;
		(e: 'selected', template: GraphInputMetadata): void;
		(e: 'cancelSelection', template: GraphInputMetadata): void;
		(e: 'copySelected', template: GraphInputMetadata): void;
		(e: 'pasteClipboard', template: GraphInputMetadata): void;
		(e: 'cutSelected'): void;
		(e: 'deselectInput', template: GraphInputMetadata): void;
	}>();

	function openContextMenu(): MenuOptions | null {
		return menu.value;
	}

	function onClick() {
		if (childrenOpen.value) {
			closeTab();
		} else {
			openTab();
		}
	}

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(tab.value!, openContextMenu, true);
	});

	function closeTab() {
		//We want to deselect items if we close a tab
		for (const inputData of props.inputs) {
			emit('deselectInput', inputData.metadata);
		}
		childrenOpen.value = false;
	}

	function openTab() {
		childrenOpen.value = true;
	}

	function category(): String {
		return props.category;
	}

	defineExpose({
		openTab,
		closeTab,
		category
	});
</script>

<style scoped>
	.group-input-tab {
		width: 100%;
		margin-top: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		background-color: var(--color-background-primary);
		cursor: pointer;
		overflow: hidden;
	}

	.group-input-left-expand-icon {
		opacity: 0.5;
		transition: opacity 50ms linear;
	}

	.group-input-tab:hover .group-input-left-expand-icon {
		opacity: 1;
	}

	.group-input-tab-body {
		flex: 1 0;
		padding: 8px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		overflow: hidden;
	}

	.group-input-tab-name {
		font-size: larger;
		color: var(--color-text);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		font-weight: 600;
		opacity: 0.8;
	}

	.group-input-tab:hover .group-input-tab-name {
		opacity: 1;
	}

	.group-input-more-icon {
		font-size: 1.2rem;
		color: var(--color-text);
		opacity: 0;
		border-radius: 2px;
	}

	.group-input-tab:hover .group-input-more-icon:not(:hover) {
		opacity: 0.6;
	}

	.group-input-more-icon:hover {
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
</style>
