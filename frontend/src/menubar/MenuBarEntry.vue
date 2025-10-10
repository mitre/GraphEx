<template>
	<DropdownComponent ref="dropdown" class="dropdown-comp" :translateY="4">
		<span class="menu-item-name no-select">{{ props.name }}</span>

		<template v-slot:dropdown>
			<MenuComponent v-bind="options" @select="onEntryClick" />
		</template>
	</DropdownComponent>
</template>

<script setup lang="ts">
	import { ref, computed, type ComputedRef } from 'vue';
	import DropdownComponent from '@/components/DropdownComponent.vue';
	import MenuComponent from '@/components/MenuComponent.vue';
	import type { MenuOptions, MenuItem } from '@/components/MenuComponent.vue';

	export interface MenuItemProps {
		/** Name of this menu item. */
		name: string;

		/** Items under this menu bar entry. */
		items: Array<MenuItem>;
	}

	const props = defineProps<MenuItemProps>();
	const dropdown = ref<InstanceType<typeof DropdownComponent>>();

	const options: ComputedRef<MenuOptions> = computed(() => {
		return {
			items: props.items
		};
	});

	function onEntryClick() {
		if (dropdown.value) {
			dropdown.value.close();
		}
	}
</script>

<style scoped>
	.menu-item-name {
		color: var(--color-text-secondary);
		white-space: pre;
	}
</style>
