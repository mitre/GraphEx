<template>
	<div
		class="context-menu"
		ref="container"
		v-if="isOpen && options"
		:style="contextMenuStyles"
		@contextmenu.stop.prevent
	>
		<MenuComponent v-bind="options" @select="close" ref="menu" />
	</div>
</template>

<script setup lang="ts">
	import type { MenuOptions } from '@/components/MenuComponent.vue';
	import MenuComponent from '@/components/MenuComponent.vue';
	import { useEditorStore } from '@/stores';
	import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue';

	const container = ref<HTMLDivElement>();
	const menu = ref<InstanceType<typeof MenuComponent>>();
	const isOpen = ref<boolean>(false);
	const positions = reactive({ x: 0, y: 0 });
	const options = ref<MenuOptions | null>(null);

	const editorStore = useEditorStore();

	/**
	 * Listen for a context menu event on an element and show a custom context menu instead.
	 *
	 * @param element The element to listen to context menu events on.
	 * @param optionsCallback A callback that returns the context menu options.
	 * @param capture Listen to context menu events using this 'capture' value.
	 */
	function addHook(element: HTMLElement, optionsCallback: () => MenuOptions | null, capture?: boolean) {
		if (editorStore.isResolvingMergeConflict) {
			return;
		}
		const callback = (event: MouseEvent) => {
			event.stopPropagation();

			if (event.ctrlKey && event.altKey) {
				// Allow for normal context menu when ctrl+alt is held down
				return;
			}

			event.preventDefault();

			const menuOptions = optionsCallback();
			if (!menuOptions || !menuOptions.items.length) {
				return;
			}

			isOpen.value = true;
			positions.x = event.clientX;
			positions.y = event.clientY;
			options.value = menuOptions;

			window.addEventListener('mousedown', onMouseClick, { capture: true });

			// Adjust the x and y positions after the context menu is available to ensure it does not overflow the screen
			nextTick(() => {
				if (!menu.value || !menu.value.menuBody) return;
				const rect = menu.value.menuBody.getBoundingClientRect();

				if (rect.bottom >= window.innerHeight) {
					positions.y -= rect.height;
				}

				if (rect.right >= window.innerWidth) {
					positions.x -= rect.width;
				}
			});
		};

		element.addEventListener('contextmenu', callback, { capture: capture });
	}

	function close() {
		isOpen.value = false;
		window.removeEventListener('mousedown', onMouseClick, { capture: true });
	}

	function onMouseClick(event: MouseEvent) {
		const target = event.target;
		if (target && target instanceof Node && container.value && container.value.contains(target)) {
			// Click is within the context menu
			// Handle in onEntryClick
			return;
		}

		close();
	}

	const contextMenuStyles = computed(() => {
		return {
			top: positions.y + 'px',
			left: positions.x + 'px'
		};
	});

	onBeforeUnmount(() => {
		close();
	});

	defineExpose({
		addHook
	});
</script>

<style scoped>
	.context-menu {
		position: fixed;
		z-index: 999;
	}
</style>
