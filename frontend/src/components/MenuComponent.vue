<template>
	<div
		class="menu-container"
		ref="container"
		@mouseleave.stop.prevent="hoverItem($event.currentTarget as HTMLDivElement, null)"
	>
		<div class="menu-body custom-scrollbar" :style="listStyles" ref="menuBody" @wheel.stop>
			<template v-for="(item, index) in props.items" :key="item.label">
				<div
					class="menu-item no-select"
					:for="item.label"
					:disabled="!!item.disabled"
					:hovered="item.label == hoveredItem?.label"
					@click.stop.prevent="selectOption([item])"
					@contextmenu.stop.prevent
					@dblclick.stop.prevent
					@mousedown.stop.prevent
					@mouseover.stop.prevent="hoverItem($event.currentTarget as HTMLDivElement, item)"
				>
					<span class="menu-item-icon material-icons" v-if="item.icon" :for="item.label" :disabled="!!item.disabled">
						{{ item.icon }}
					</span>
					<span class="menu-item-label" :for="item.label" :disabled="!!item.disabled">
						{{ item.label }}
					</span>
					<span
						class="menu-item-description"
						v-if="anyDescriptionExists"
						:for="item.label"
						:disabled="!!item.disabled"
						:title="item.description"
					>
						{{ item.description }}
					</span>

					<span class="menu-item-more-icon material-icons" v-if="item.submenu && !item.disabled">chevron_right</span>
				</div>

				<div class="menu-item-divider" v-if="item.divider && index != props.items.length - 1"></div>
			</template>
		</div>

		<template v-for="item in props.items" :key="item.label">
			<div
				class="submenu-container"
				v-if="item.submenu && !item.disabled && hoveredItem?.label == item.label"
				:style="{ top: hoveredItemOffsetY + 'px' }"
			>
				<MenuComponent
					v-bind="item.submenu"
					@select="(items) => selectOption([item, ...items])"
					:max-height="childMaxHeight || 600"
				/>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
	import { computed, ref } from 'vue';

	export interface MenuOptions {
		items: Array<MenuItem>;
		maxHeight?: number;
		childMaxHeight?: number;
	}

	export interface MenuItem {
		/** Label to use for this menu item. */
		label: string;

		/** Whether this item is disabled. */
		disabled?: boolean;

		/** The material UI icon name to use for this item. */
		icon?: string;

		/** Description for this menu item. */
		description?: string;

		/** Whether a divider should be added *after* this menu item. */
		divider?: boolean;

		/** Whether this menu item has a submenu that should show on hover. */
		submenu?: MenuOptions;

		/** Optional callback to call when this menu item is clicked. */
		callback?: () => void;
	}

	const props = defineProps<MenuOptions>();
	const container = ref<HTMLDivElement>();
	const menuBody = ref<HTMLDivElement>();
	const hoveredItem = ref<MenuItem | null>(null);
	const hoveredItemOffsetY = ref<number>(0);

	const emit = defineEmits<{
		/** Triggered when a menu item is selected. The last item in the array will be the item clicked; previous items will be any parents (if this is a submenu). */
		(e: 'select', items: Array<MenuItem>): void;
	}>();

	function selectOption(items: Array<MenuItem>) {
		const lastItem = items[items.length - 1];
		if (lastItem.disabled || lastItem.submenu) {
			return;
		}

		emit('select', items);
		if (items.length == 1 && lastItem.callback) {
			lastItem.callback();
		}
	}

	function hoverItem(el: HTMLDivElement, item: MenuItem | null) {
		hoveredItem.value = item;
		if (item === null) {
			return;
		}

		if (container.value) {
			const containerRect = container.value.getBoundingClientRect();
			const elementRect = el.getBoundingClientRect();
			hoveredItemOffsetY.value = elementRect.top - containerRect.top;
		}
	}

	const listStyles = computed(() => {
		const styles: { [name: string]: string } = {};

		if (props.maxHeight) {
			styles['max-height'] = props.maxHeight + 'px';
		}

		return styles;
	});

	const anyDescriptionExists = computed(() => {
		return !!props.items.find((item) => !!item.description);
	});

	defineExpose({
		menuBody
	});
</script>

<style scoped>
	.menu-container {
		position: relative;
	}

	.menu-body {
		min-width: 50px;
		display: flex;
		flex-direction: column;
		padding: 6px 0px;
		background-color: var(--color-foreground-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 0px 0px 8px 4px rgba(0, 0, 0, 0.4);
		border-radius: 4px;
		overflow-x: hidden;
		overflow-y: auto;
	}

	.menu-item {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		border-radius: 4px;
		padding: 6px 12px;
		margin: 0px 6px;
		cursor: pointer;
		z-index: 20;
	}

	.menu-item[disabled='false'][hovered='true'] {
		background-color: var(--color-foreground-secondary);
	}

	.menu-item[disabled='true'] {
		cursor: default;
		opacity: 0.5;
	}

	.menu-item-icon {
		margin-right: 10px;
		color: var(--color-text);
		font-size: 1em;
		opacity: 0.6;
	}

	.menu-item-label {
		flex: 1 0;
		color: var(--color-text);
		white-space: pre;
	}

	.menu-item-description {
		margin-left: 32px;
		font-size: 0.9em;
		color: var(--color-text);
		opacity: 0.5;
		white-space: pre;
	}

	.menu-item-more-icon {
		margin-left: 6px;
		font-size: 1.2em;
		color: var(--color-text);
	}

	.menu-item-divider {
		border-top: 1px solid var(--color-foreground-tertiary);
		margin-top: 6px;
		padding-top: 6px;
	}

	.submenu-container {
		position: absolute;
		right: 0px;
	}

	.submenu-container > .menu-container {
		right: -100%;
	}
</style>
