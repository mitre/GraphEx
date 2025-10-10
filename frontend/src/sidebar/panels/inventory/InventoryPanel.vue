<template>
	<SidebarPanel header="Inventory">
		<template v-slot:buttons>
			<div class="button-bar">
				<span class="material-icons button" title="Fold All" @click="foldAll">unfold_less</span>
				<span class="material-icons button" title="Unfold All" @click="unfoldAll">unfold_more</span>
			</div>
		</template>
		<div class="inventory-panel-container" v-if="individualEntriesForCurrentFile.length">
			<div class="inventory-dropdown-wrapper">
				<DropdownComponent ref="dropdown" auto-width>
					<span class="dropdown-value no-select">{{ selectedInventoryFilename || '&nbsp;' }}</span>
					<div class="dropdown-icon material-icons">expand_more</div>

					<template v-slot:dropdown>
						<div class="dropdown-contents-container custom-scrollbar">
							<span
								v-for="option in inventoryFileNames"
								:key="option"
								class="dropdown-option no-select"
								@click.stop="selectOption(option)"
							>
								{{ option }}
							</span>
						</div>
					</template>
				</DropdownComponent>
			</div>
			<div class="inventory-entries-container">
				<InventoryEntry 
					v-for="entry in individualEntriesForCurrentFile"
					:key="entry.entry_name"
					:entry-info="entry"
					:file-key="selectedInventoryFilename"
					ref="entries"/>
			</div>
		</div>
		<div class="inventory-panel-no-inventory" v-else>
			A directory containing yml inventory files was not provided to the GraphEx server when it was created (with argument -inv).
			This panel has no functionality without such files provided to it. Please refer to the documentation for more information.
		</div>
	</SidebarPanel>
</template>

<script setup lang="ts">
import SidebarPanel from '@/sidebar/SidebarPanel.vue';
import { useMetadataStore } from '@/stores';
import { computed, ref, watch } from 'vue';

import DropdownComponent from '@/components/DropdownComponent.vue';
import InventoryEntry from './InventoryEntry.vue';

	const metadataStore = useMetadataStore();
	const dropdown = ref<InstanceType<typeof DropdownComponent>>();
	const selectedInventoryFilename = ref<string>("");

	const entries = ref<(typeof InventoryEntry)[]>();

	function foldAll() {
		if (entries.value) {
			entries.value.forEach((t) => {
				t.fold();
			});
		}
	}

	function unfoldAll() {
		if (entries.value) {
			entries.value.forEach((t) => {
				t.unfold();
			});
		}
	}

	function selectOption(option: string) {
		selectedInventoryFilename.value = option;
		dropdown.value?.close();
	}

	/** A dictionary type object containing the keys as dir/filename and the values being subdicts */
	const inventoryFileObjects = computed(() => {
		return metadataStore.inventoryFiles;
	});

	/** The names (keys) of the individual inventory files to be displayed in the dropdown */
	const inventoryFileNames = computed(() =>  {
		if (!inventoryFileObjects.value) return [];
		let filenames: string[] = [];
		
		for (const filenameKey in inventoryFileObjects.value) {
			filenames.push(filenameKey);
		};
		return filenames.sort();
	});

	/** 
	 * The individual entries to start being populated in the sidebar panel.
	 * Valid keys are: content (dict), entry_name (str), name_of_node (str), node (dict==NodeMetadata), node_inputs (dict)
	 *  */
	const individualEntriesForCurrentFile = computed(() => {
		let entries: Array<Record<string, any>> = [];
		if (inventoryFileObjects.value && selectedInventoryFilename.value && selectedInventoryFilename.value != "") {
			const entriesObj: Record<string, any> = inventoryFileObjects.value[selectedInventoryFilename.value].inventoryEntries;
			for (const k in entriesObj) {
				entries.push(entriesObj[k]);
			}
			entries.sort((a, b) => a.entry_name < b.entry_name ? -1 : 1 );
		}
		return entries;
	});

	/** Just the names of each entry in the inventory file */
	const entryNamesForCurrentFile = computed(() =>  {
		return individualEntriesForCurrentFile.value.map(e => e.entry_name);
	});

	watch(
		inventoryFileNames,
		() => {
			if (selectedInventoryFilename.value == "" && inventoryFileNames.value.length) {
				selectedInventoryFilename.value = inventoryFileNames.value[0];
			}
		},
		{ immediate: true }
	);
</script>

<style scoped>
	.inventory-panel-container {
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

	:deep(.header-bar) {
		margin-bottom: 0rem;
	}

	.inventory-dropdown-wrapper {
		background-color: var(--color-background-primary);
		margin-bottom: 12px;
		padding: 0.5rem;
	}

	.dropdown-value {
		flex: 1 0;
		padding: 8px;
		font-size: 1rem;
		text-transform: inherit;
	}

	.dropdown-icon {
		margin: 0px 8px;
		font-size: 1.4rem;
		color: var(--color-text);
		opacity: 0.7;
	}

	.dropdown-contents-container {
		max-height: 400px;
		flex: 1 0;
		display: flex;
		flex-direction: column;
		padding: 6px 0px;
		background-color: var(--color-background-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 0px 0px 8px 4px rgba(0, 0, 0, 0.4);
		border-radius: 4px;
		overflow: auto;
	}

	.dropdown-option {
		flex: 1 0;
		padding: 8px;
		cursor: pointer;
	}

	.dropdown-option:hover {
		background-color: var(--color-foreground-secondary);
	}

	:deep(.dropdown-wrapper) {
		flex: 1 0;
	}

	:deep(.dropdown-target-container) {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	:deep(.dropdown) {
		width: 100%;
	}

	.inventory-panel-no-inventory {
		color: var(--color-error);
		text-align: center;
		padding: 0.5rem;
	}
</style>
