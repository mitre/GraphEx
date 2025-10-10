<template>
	<div class="file-container">
		<div class="file no-select" @click.stop.prevent="itemClicked">
			<div v-if="props.gitIcon" class="gitIcon" :title="props.gitIcon.title">{{ props.gitIcon.icon }}</div>
			<div class="file-name">{{ props.name }}</div>
			<span v-if="props.actions">
				<div class="action-buttons-group" v-for="(action, index) in props.actions" :key="index">
					<div
						class="action-button material-icons"
						:title="action.title"
						@click.stop.prevent="actionClick(action.clickAction, props.name)"
					>
						{{ action.icon }}
					</div>
				</div>
			</span>
			<DropdownComponent v-if="props.dropdownOptions && props.dropdownOptions?.length > 0" ref="dropdown">
				<div class="variable-more-icon material-icons">more_horiz</div>
				<template v-slot:dropdown>
					<MenuComponent v-bind="menuOptions" />
				</template>
			</DropdownComponent>
		</div>
	</div>
</template>

<script setup lang="ts">
	import DropdownComponent from '@/components/DropdownComponent.vue';
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
	import MenuComponent from '@/components/MenuComponent.vue';
	import { computed, type ComputedRef, ref } from 'vue';

	const props = defineProps<{
		name: string;
		actions?: Array<Actions>;
		gitIcon?: gitIcon;
		dropdownOptions?: Array<menuOptionProps>;
	}>();

	const emit = defineEmits<{
		(e: 'addChanges', value: string): void;
		(e: 'discardChanges', value: string): void;
		(e: 'undoChanges', value: string): void;
		(e: 'viewConflicts', value: string): void;
		(e: 'branchOptions', menuOption: string, branch: string): void;
		(e: 'itemClicked', itemName: string): void;
	}>();

	function actionClick(action: string, name: string) {
		switch (action) {
			case 'addChanges':
				emit('addChanges', name);
				break;
			case 'discardChanges':
				emit('discardChanges', name);
				break;
			case 'undoChanges':
				emit('undoChanges', name);
				break;
			case 'viewConflicts':
				emit('viewConflicts', name);
				break;
			default:
				break;
		}
	}

	function itemClicked() {
		emit('itemClicked', props.name);
	}

	const dropdown = ref<InstanceType<typeof DropdownComponent>>();
	const menuOptions: ComputedRef<MenuOptions> = computed(() => {
		const menuItems: MenuItem[] = [];
		props.dropdownOptions?.forEach((option) => {
			menuItems.push({
				label: option.label,
				description: option.description,
				callback: () => {
					dropdown.value?.close();
					emit('branchOptions', option.label, props.name);
				}
			});
		});
		const items = { items: menuItems };

		return items;
	});

	interface Actions {
		icon: 'add' | 'remove' | 'undo' | 'error';
		title: 'Stage Changes' | 'Discard Changes' | 'Unstage Changes' | 'View Conflicts';
		clickAction: 'addChanges' | 'discardChanges' | 'undoChanges' | 'viewConflicts';
	}

	interface gitIcon {
		icon: string;
		title: string;
	}

	interface menuOptionProps {
		label: string;
		description?: string;
	}
</script>

<style scoped>
	.file-container {
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.file {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow: hidden;
		cursor: pointer;
		padding: 6px 0px;
		padding-left: 16px;
	}

	.file-container[active='true'] > .file {
		background-color: var(--color-foreground-secondary);
	}

	.file-container[active='true'] .file-name {
		color: var(--color-primary);
		flex: 1;
		padding-left: 8px;
	}

	.gitIcon {
		opacity: 0.7;
		font-size: large;
		font-weight: bold;
		flex-basis: 1rem;
	}

	.file-container > .file:hover {
		background-color: var(--color-foreground-secondary);
	}

	.file-container[isdirectory='true'][draggedover='true'] > .file {
		outline: 1px solid var(--color-border);
		background-color: var(--color-foreground-secondary);
	}

	.file-icon {
		margin-right: 6px;
		color: var(--color-text-secondary);
	}

	.file-logo {
		margin-right: 6px;
		background-image: url('/logo.png');
		background-position: center;
		background-repeat: no-repeat;
		background-size: 100% 100%;
	}

	.file-name {
		color: var(--color-text);
		text-overflow: ellipsis;
		overflow: hidden;
		flex: 1;
		padding-left: 16px;
	}

	.directory-children {
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.action-buttons-group {
		padding-right: 16px;
		display: flex;
	}

	.action-button {
		opacity: 0.6;
	}

	.action-button:hover {
		opacity: 1;
	}

	.variable-more-icon {
		font-size: 1.2rem;
		color: var(--color-text);
		opacity: 0.5;
		border-radius: 2px;
		padding-right: 16px;
	}
</style>
